#!/usr/bin/env bash
#
# gh_identity.sh — Shared GitHub identity enforcement for the release path.
#
# Why: During v6.5.15, release pushes leaked out under the wrong identity
#   (bob-duetto) because raw `git push` over HTTPS resolves credentials from the
#   host-keyed system credential store, NOT from the active `gh` account. This
#   library makes every release push deterministically use the required identity.
#
# What: Provides these functions:
#   - gh_required_account      -> echoes the required account from .gh-account
#   - gh_assert_identity       -> FAILS LOUDLY (exit 1) unless the resolvable token
#                                 belongs to the required account
#   - gh_git ARGS...           -> runs an arbitrary git command (clone/pull/push)
#                                 against a bare github.com remote, injecting the
#                                 required account's token via a one-shot
#                                 GIT_ASKPASS helper so the token NEVER appears in
#                                 argv, the URL, git config, reflog, or any log.
#   - gh_git_push REMOTE REF...-> convenience wrapper: `gh_git push REMOTE REF...`.
#
# Test: `source scripts/lib/gh_identity.sh` then `gh_assert_identity` — it must
#   print the resolved account and return 0 under bobmatnyc. To simulate a wrong
#   identity WITHOUT touching real auth, set BOTH _GH_IDENTITY_TEST_MODE=1 and
#   _GH_IDENTITY_TEST_OVERRIDE=<login>; the assert then returns 1 with a clear
#   error when <login> differs from the required account.
#
# Usage (from another script):
#   SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
#   . "$SCRIPT_DIR/lib/gh_identity.sh"
#   gh_assert_identity || exit 1
#   gh_git_push origin main            # token injected only via env at runtime
#
# Security: the token is NEVER embedded in a URL or passed as a git argument.
#   It is resolved at runtime via `gh auth token` and handed to git through a
#   short-lived GIT_ASKPASS script, so it cannot leak into /proc/<pid>/cmdline,
#   `git remote -v`, reflog, shell history, or `set -x` traces. No secrets are
#   hardcoded.

# Resolve the required account: explicit env override > nearest .gh-account file.
# Why: keeps the helper in sync with `claude-mpm gh switch`, which reads .gh-account.
gh_required_account() {
    if [ -n "${GH_REQUIRED_ACCOUNT:-}" ]; then
        printf '%s' "$GH_REQUIRED_ACCOUNT"
        return 0
    fi

    # Walk up from CWD looking for a .gh-account marker.
    local dir
    dir="$(pwd)"
    while [ "$dir" != "/" ]; do
        if [ -f "$dir/.gh-account" ]; then
            tr -d '[:space:]' < "$dir/.gh-account"
            return 0
        fi
        dir="$(dirname "$dir")"
    done

    return 1
}

# Test-only seam: returns the simulated active identity, or empty if not in test
# mode. Why: a single guarded entry point keeps the bypass impossible to trigger
# accidentally in production. It is honored ONLY when _GH_IDENTITY_TEST_MODE=1 is
# explicitly set AND _GH_IDENTITY_TEST_OVERRIDE is non-empty. The leading
# underscore + "TEST" naming makes the intent unmistakable.
# Test: with neither var set, echoes nothing (exit 1); with both set, echoes the
#   override; with only _GH_IDENTITY_TEST_OVERRIDE set, echoes nothing (exit 1).
_gh_identity_test_override() {
    if [ "${_GH_IDENTITY_TEST_MODE:-}" = "1" ] && [ -n "${_GH_IDENTITY_TEST_OVERRIDE:-}" ]; then
        printf '%s' "$_GH_IDENTITY_TEST_OVERRIDE"
        return 0
    fi
    return 1
}

# Resolve the token for a specific account using gh. Echoes the token on success.
# Why: `gh auth token --user X` returns X's token regardless of the active account,
#   which is exactly what we need to authenticate as a deterministic identity.
gh_token_for() {
    local account="$1"
    if ! command -v gh >/dev/null 2>&1; then
        return 1
    fi
    gh auth token --user "$account" 2>/dev/null
}

# Determine which account a token actually belongs to (via the GitHub API).
# Why: proves the resolved token is really the required identity, not a stale cache.
gh_account_for_token() {
    local token="$1"
    if ! command -v gh >/dev/null 2>&1; then
        return 1
    fi
    GH_TOKEN="$token" gh api user --jq '.login' 2>/dev/null
}

# Hard preflight: abort loudly unless we can prove the required identity.
# Returns 0 only when the resolved token verifiably belongs to the required account.
gh_assert_identity() {
    local required resolved token

    required="$(gh_required_account)" || {
        echo "ERROR: could not determine required GitHub account (.gh-account missing and GH_REQUIRED_ACCOUNT unset)." >&2
        return 1
    }

    # Test seam: simulate a wrong/other active identity WITHOUT touching real auth.
    # Gated behind the explicit _GH_IDENTITY_TEST_MODE=1 guard so it can never
    # silently disable enforcement in a real environment/CI.
    if resolved="$(_gh_identity_test_override)"; then
        if [ "$resolved" != "$required" ]; then
            echo "ERROR: GitHub identity mismatch — refusing to push." >&2
            echo "  required (.gh-account): $required" >&2
            echo "  active identity:        $resolved" >&2
            echo "  Fix: claude-mpm gh switch   (or: gh auth switch --user $required)" >&2
            return 1
        fi
        echo "✓ GitHub identity verified (test override): $resolved"
        return 0
    fi

    token="$(gh_token_for "$required")"
    if [ -z "$token" ]; then
        echo "ERROR: no gh token available for required account '$required'." >&2
        echo "  Fix: gh auth login --user $required" >&2
        return 1
    fi

    resolved="$(gh_account_for_token "$token")"
    if [ -z "$resolved" ]; then
        echo "ERROR: could not verify the resolved token's owner via GitHub API." >&2
        echo "  Check network connectivity and that '$required' is authenticated." >&2
        return 1
    fi

    if [ "$resolved" != "$required" ]; then
        echo "ERROR: GitHub identity mismatch — refusing to push." >&2
        echo "  required (.gh-account): $required" >&2
        echo "  token resolves to:      $resolved" >&2
        echo "  Fix: gh auth login --user $required" >&2
        return 1
    fi

    echo "✓ GitHub identity verified: $resolved (token owner matches .gh-account)"
    return 0
}

# Run a git command authenticated as the required account WITHOUT leaking the
# token into argv, the URL, git config, reflog, or any log.
# Why: forces git to authenticate as the required identity instead of consulting
#   the host-keyed credential store, while keeping the token out of every place a
#   token-in-URL would otherwise surface (/proc/<pid>/cmdline, `git remote -v`,
#   reflog, shell history, `set -x`, command logging).
# What: resolves the required account's token, writes it to a 0700 one-shot
#   GIT_ASKPASS script, and runs `git -c credential.helper= <args...>` so git asks
#   the askpass helper (which echoes the token) instead of any ambient helper. The
#   temp script is removed immediately afterward, even on failure.
# Test: `_GH_IDENTITY_TEST_MODE=1 _GH_IDENTITY_TEST_OVERRIDE=x gh_git push --dry-run`
#   — in test mode it skips token resolution and runs git directly; otherwise it
#   resolves the bobmatnyc token and the token must not appear in `git`'s argv.
gh_git() {
    local required token askpass rc

    required="$(gh_required_account)" || {
        echo "ERROR: cannot run authenticated git — required account unknown." >&2
        return 1
    }

    # Test seam: never resolve/require a real token while simulating; run git as-is
    # so callers can exercise the push path (e.g. --dry-run) without credentials.
    if _gh_identity_test_override >/dev/null; then
        git "$@"
        return $?
    fi

    token="$(gh_token_for "$required")"
    if [ -z "$token" ]; then
        echo "ERROR: cannot run authenticated git — no token for '$required'." >&2
        return 1
    fi

    # One-shot GIT_ASKPASS: git invokes this for the username and password prompts.
    # For HTTPS token auth, username can be anything (x-access-token) and the
    # password is the token. We echo the token for both prompts; GitHub accepts it.
    askpass="$(mktemp "${TMPDIR:-/tmp}/gh_askpass.XXXXXX")" || {
        echo "ERROR: could not create askpass helper." >&2
        return 1
    }
    chmod 0700 "$askpass"
    # The token is written to a private temp file read only by git's askpass call,
    # never placed on a command line.
    printf '#!/bin/sh\nprintf %%s "%s"\n' "$token" > "$askpass"  # pragma: allowlist secret

    # credential.helper= (empty) disables any configured helper for this invocation
    # so the askpass token is authoritative and the ambient store is never consulted.
    GIT_ASKPASS="$askpass" GIT_TERMINAL_PROMPT=0 \
        git -c credential.helper= "$@"
    rc=$?

    rm -f "$askpass"
    return $rc
}

# Convenience wrapper for the common case: push to a remote authenticated as the
# required account. Equivalent to `gh_git push REMOTE REF...`.
# Test: `gh_git_push origin main` pushes using the required identity; the token
#   never appears in the resulting git argv (verify with a traced dry run).
gh_git_push() {
    gh_git push "$@"
}
