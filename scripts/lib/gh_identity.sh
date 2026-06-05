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
#   short-lived GIT_ASKPASS script. The token reaches git via an env-var prefix
#   scoped only to the git child process (never exported to the parent shell, never
#   inherited by hooks or subshells). The only residual vector is
#   /proc/<pid>/environ of the git child while it runs, which is acceptable. The
#   token cannot leak into /proc/<pid>/cmdline, `git remote -v`, reflog, shell
#   history, or `set -x` traces. No secrets are hardcoded.

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
# What: resolves the required account's token, writes a 0700 one-shot GIT_ASKPASS
#   script that echoes $GH_ASKPASS_TOKEN, and runs `git -c credential.helper=
#   <args...>` with GH_ASKPASS_TOKEN scoped ONLY to the git child process via an
#   env-var prefix (never exported to the parent shell, never inherited by hooks or
#   subshells, no unset needed), so git asks the askpass helper (which echoes the
#   env token) instead of any ambient helper. The token is never written into the
#   script body or any argv. xtrace (`set -x`) is suppressed across the entire
#   token-handling region and restored afterward, so the secret cannot leak into CI
#   debug traces via the assignment, guard, or env prefix. The temp script is
#   removed even on failure.
# macOS keychain bypass: on macOS, git uses Apple's system libcurl
#   (/usr/lib/libcurl.4.dylib) which integrates with NSURLCredentialStorage /
#   ~/Library/Keychains regardless of git credential helper settings. When multiple
#   GitHub accounts are stored in the keychain (e.g. bobmatnyc + bob-duetto), the
#   OS-level lookup may return the wrong one even when -c credential.helper= is set.
#   Setting HOME to a clean temporary directory for the git subprocess prevents
#   libcurl from reaching ~/Library/Keychains, forcing it to fall back to
#   GIT_ASKPASS. The temp HOME dir is created with restrictive permissions and
#   removed after every invocation (success or failure). GIT_CONFIG_NOSYSTEM=1
#   is also set to prevent the system gitconfig from re-introducing helpers.
# Test: `_GH_IDENTITY_TEST_MODE=1 _GH_IDENTITY_TEST_OVERRIDE=x gh_git push --dry-run`
#   — in test mode it skips token resolution and runs git directly; otherwise it
#   resolves the bobmatnyc token and the token must not appear in `git`'s argv.
gh_git() {
    local required token askpass git_home rc

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

    # Suppress xtrace around ALL token handling. Even with the token kept out of
    # argv, `set -x` would otherwise echo the `token=...` assignment, the `[ -z ]`
    # guard, and the `GH_ASKPASS_TOKEN=...` env prefix — re-leaking the secret into
    # CI debug logs. We record whether xtrace was on, disable it for the sensitive
    # region, and restore it (only if it was on) at every exit path. This works on
    # macOS bash 3.2 too — no reliance on `local -`/BASH-only option scoping.
    local _xtrace_was_on=0
    case "$-" in *x*) _xtrace_was_on=1 ;; esac
    set +x

    token="$(gh_token_for "$required")"
    if [ -z "$token" ]; then
        [ "$_xtrace_was_on" = 1 ] && set -x
        echo "ERROR: cannot run authenticated git — no token for '$required'." >&2
        return 1
    fi

    # One-shot GIT_ASKPASS: git invokes this for the username and password prompts.
    # For HTTPS token auth, username can be anything (x-access-token) and the
    # password is the token. We echo the token for both prompts; GitHub accepts it.
    #
    # Create the helper atomically under a restrictive umask so there is no
    # world-readable window between mktemp and a follow-up chmod (TOCTOU).
    askpass="$( umask 077 && mktemp "${TMPDIR:-/tmp}/gh_askpass.XXXXXX" )" || {
        [ "$_xtrace_was_on" = 1 ] && set -x
        echo "ERROR: could not create askpass helper." >&2
        return 1
    }
    # The askpass script body NEVER contains the token; it reads GH_ASKPASS_TOKEN
    # from the environment at git-run time. This keeps the token out of the script
    # contents AND out of any command argv, so it cannot surface in the helper file,
    # /proc/<pid>/cmdline, `git remote -v`, reflog, or shell history.
    # SC2016: the single quotes are intentional — we want the literal text
    # ${GH_ASKPASS_TOKEN} written into the helper, expanded by /bin/sh at git-run
    # time, NOT expanded here (which would re-embed the token in the script body).
    # shellcheck disable=SC2016
    printf '#!/bin/sh\nprintf %%s "${GH_ASKPASS_TOKEN}"\n' > "$askpass"
    chmod 0700 "$askpass"

    # Create a clean temporary HOME dir to prevent Apple's system libcurl from
    # reading ~/Library/Keychains and returning a cached credential for the wrong
    # GitHub account. The dir is scoped only to the git child process via an
    # env-var prefix. GIT_CONFIG_NOSYSTEM=1 prevents system gitconfig from
    # re-introducing credential helpers. GIT_CONFIG_GLOBAL=/dev/null prevents
    # user gitconfig helpers (e.g. osxkeychain, gh auth git-credential) from
    # running alongside our askpass, which would cause the wrong helper to win
    # when multiple GitHub accounts exist. Together these three env vars make
    # GIT_ASKPASS the sole credential source for the child process.
    git_home="$( umask 077 && mktemp -d "${TMPDIR:-/tmp}/gh_git_home.XXXXXX" )" || {
        rm -f "$askpass"
        [ "$_xtrace_was_on" = 1 ] && set -x
        echo "ERROR: could not create temp HOME for git subprocess." >&2
        return 1
    }

    # Signal-safe cleanup: if the git child is interrupted (SIGINT/SIGTERM), the
    # explicit `rm` lines below the git call would be skipped, leaking BOTH the
    # askpass helper and the temp HOME dir. Install an INT/TERM trap that removes
    # both (with ${var:-} guards so it is safe under `set -u` and a no-op if a var
    # is unset). We deliberately do NOT use a RETURN or EXIT trap: this is a sourced
    # library, so a RETURN trap can bleed into the caller's return semantics (we hit
    # exactly that bug in update_homebrew_tap.sh) and an EXIT trap would fire for the
    # whole script. The trap is reset (`trap - INT TERM`) right before the normal
    # return, after the explicit cleanup, so nothing lingers in the caller.
    trap 'rm -f "${askpass:-}"; rm -rf "${git_home:-}"' INT TERM

    # credential.helper= (empty) disables any configured helper for this invocation
    # so the askpass token is authoritative and the ambient store is never consulted.
    # The token is passed to git ONLY via an env-var prefix on the child process —
    # it is never exported into the parent shell's environment and never inherited by
    # any sibling process, git hook, or subshell. The only residual vector is
    # /proc/<pid>/environ of the git child while it runs, which is acceptable.
    # xtrace is still off here, so the prefix assignment is not echoed.
    # NOTE: gh_git is only ever used for clone/push/fetch (never `commit`), so the
    # GIT_CONFIG_GLOBAL=/dev/null below does NOT affect git author/committer identity
    # for any current caller — it only suppresses ambient credential helpers.
    GH_ASKPASS_TOKEN="$token" GIT_ASKPASS="$askpass" GIT_TERMINAL_PROMPT=0 \
        GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null \
        HOME="$git_home" \
        git -c credential.helper= "$@"
    rc=$?

    rm -f "$askpass"
    rm -rf "$git_home"
    # Reset the signal trap now that cleanup is done and we are returning normally,
    # so it never lingers in the caller's trap table for INT/TERM.
    trap - INT TERM
    [ "$_xtrace_was_on" = 1 ] && set -x
    return $rc
}

# Convenience wrapper for the common case: push to a remote authenticated as the
# required account. Equivalent to `gh_git push REMOTE REF...`.
# Test: `gh_git_push origin main` pushes using the required identity; the token
#   never appears in the resulting git argv (verify with a traced dry run).
gh_git_push() {
    gh_git push "$@"
}
