#!/usr/bin/env bash
#
# gh_identity.sh — Shared GitHub identity enforcement for the release path.
#
# Why: During v6.5.15, release pushes leaked out under the wrong identity
#   (bob-duetto) because raw `git push` over HTTPS resolves credentials from the
#   host-keyed system credential store, NOT from the active `gh` account. This
#   library makes every release push deterministically use the required identity.
#
# What: Provides three functions:
#   - gh_required_account     -> echoes the required account from .gh-account
#   - gh_assert_identity       -> FAILS LOUDLY (exit 1) unless the resolvable token
#                                 belongs to the required account
#   - gh_authenticated_url URL -> rewrites an https://github.com/... remote to embed
#                                 the required account's token (x-access-token)
#
# Test: `source scripts/lib/gh_identity.sh` then `gh_assert_identity` — it must
#   print the resolved account and return 0 under bobmatnyc, and return 1 with a
#   clear error when GH_IDENTITY_OVERRIDE_USER is set to a different value.
#
# Usage (from another script):
#   SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
#   . "$SCRIPT_DIR/lib/gh_identity.sh"
#   gh_assert_identity || exit 1
#   url="$(gh_authenticated_url "https://github.com/bobmatnyc/repo.git")"
#   git push "$url" main
#
# No secrets are hardcoded: the token is resolved at runtime via `gh auth token`.

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

# Resolve the token for a specific account using gh. Echoes the token on success.
# Why: `gh auth token --user X` returns X's token regardless of the active account,
#   which is exactly what we need to build a deterministic push URL.
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
    if [ -n "${GH_IDENTITY_OVERRIDE_USER:-}" ]; then
        resolved="$GH_IDENTITY_OVERRIDE_USER"
        if [ "$resolved" != "$required" ]; then
            echo "ERROR: GitHub identity mismatch — refusing to push." >&2
            echo "  required (.gh-account): $required" >&2
            echo "  active identity:        $resolved" >&2
            echo "  Fix: claude-mpm gh switch   (or: gh auth switch --user $required)" >&2
            return 1
        fi
        echo "✓ GitHub identity verified (override): $resolved"
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

# Rewrite an https://github.com/... URL to embed the required account's token.
# Why: forces git to authenticate as the required identity instead of consulting
#   the host-keyed credential store (which may hold the wrong account).
# Echoes the original URL unchanged if it is not an https github.com URL.
gh_authenticated_url() {
    local url="$1" required token

    case "$url" in
        https://github.com/*) ;;
        *)
            # Non-HTTPS or non-github remote: pass through untouched.
            printf '%s' "$url"
            return 0
            ;;
    esac

    required="$(gh_required_account)" || {
        echo "ERROR: cannot build authenticated URL — required account unknown." >&2
        return 1
    }

    # Override path: caller is simulating; don't leak/require a real token.
    if [ -n "${GH_IDENTITY_OVERRIDE_USER:-}" ]; then
        printf '%s' "$url"
        return 0
    fi

    token="$(gh_token_for "$required")"
    if [ -z "$token" ]; then
        echo "ERROR: cannot build authenticated URL — no token for '$required'." >&2
        return 1
    fi

    # x-access-token is the GitHub-recommended username for token-based HTTPS auth.
    # The token is a runtime variable, not a hardcoded secret.
    printf 'https://x-access-token:%s@github.com/%s' "$token" "${url#https://github.com/}"  # pragma: allowlist secret
}
