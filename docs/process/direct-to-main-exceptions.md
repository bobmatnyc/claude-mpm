# Direct-to-main Push Exceptions

This file records every commit that bypassed the standard branch → PR → review workflow
and was pushed directly to `main`, along with the reason and disposition. Each entry
should be created at the time of the push (or immediately after) so the exception is
auditable.

---

## Exception log

### 2024: `83e01fae8` — macOS keychain credential hijack fix

| Field      | Value |
|------------|-------|
| Commit     | `83e01fae8` |
| Title      | `fix(release): bypass macOS keychain credential hijack in gh_git` |
| File       | `scripts/lib/gh_identity.sh` |
| Pushed by  | bobmatnyc |
| Date       | 2024 (during v6.5.19 release) |
| Issue      | #664 |

**What changed.** `gh_git()` in `scripts/lib/gh_identity.sh` was modified to isolate the
git subprocess's `HOME` to a clean `mktemp -d` temp directory and to set
`GIT_CONFIG_NOSYSTEM=1` + `GIT_CONFIG_GLOBAL=/dev/null`. This prevents Apple's system
libcurl (which integrates with `NSURLCredentialStorage` / `~/Library/Keychains`) from
selecting a cached credential for the wrong GitHub account (`bob-duetto` instead of
`bobmatnyc`) regardless of `credential.helper=` settings on the git invocation. Also
present in that commit: the `GIT_ASKPASS` one-shot helper (token in env, never in script
body), `GIT_TERMINAL_PROMPT=0`, and the `credential.helper=` override — all working
together so `GIT_ASKPASS` is the sole credential source for the child process.

**Why it was pushed directly.** The change was authored inline during a release run:
commit `83e01fae0` (#663) had just fixed a Homebrew-tap dirty-clone failure when the
underlying macOS keychain hijack surfaced as a 403 on the tap push. The fix was minimal,
self-contained, and immediately needed to unblock the release.

**Disposition.** Keep on `main`. The commit was retroactively reviewed (trusty-review
verdict: APPROVE, B+; no correctness bugs). Follow-up hardening applied via PR #665:
signal-safe `INT`/`TERM` traps that clean up both the askpass temp file and the temp
`HOME` dir and re-raise the signal so callers observe a correct 128+signo exit instead
of a silent success.

---

## Rule

Security-sensitive credential-handling changes — files under `scripts/lib/` that touch
token resolution, `GIT_ASKPASS` helpers, identity enforcement, or ambient credential
bypass — **must go through PR review** and must not be pushed directly to `main`. This
matches the existing `.githooks/pre-push` guard (installed via
`scripts/setup-git-hooks.sh`) and the CI backstop in
`.github/workflows/guard-sensitive-paths.yml`.

Direct-to-main is acceptable only under these conditions (all must apply):

1. The change is a live hotfix that blocks an active release or deployment.
2. No destructive rewrite (no history rewrite, no force-push of another author's work).
3. The commit is logged here within 24 hours of the push.
4. A follow-up PR is opened promptly to apply any advisory hardenings and close the
   tracking issue.
