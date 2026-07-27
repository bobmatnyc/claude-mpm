#!/usr/bin/env bash
#
# find_release_ci_run.sh — Correlate a GitHub Actions workflow run with the
# exact commit/tag that should have triggered it.
#
# Why: `gh run list --workflow=<file> --limit=1` returns the most recently
#   *created* run for that workflow, not the run triggered by a specific
#   push. Immediately after `git push origin vX.Y.Z`, GitHub Actions has not
#   necessarily materialised the new run record yet (it can take several
#   seconds), so `--limit=1` silently returns a stale run from a PREVIOUS
#   release that happens to already be complete and green. Watching that run
#   with `gh run watch --exit-status` then reports success immediately even
#   though the real release CI is still running (or has failed), masking
#   publish failures. See GitHub issue #946 for the incident this fixes
#   (v6.5.82: watched the v6.5.81 run instead of v6.5.82's).
#
# What: Polls `gh api repos/<repo>/actions/workflows/<workflow>/runs?head_sha=<sha>`
#   — a server-side filter, not a client-side guess — until a run whose
#   head_sha matches the given commit appears, then prints its databaseId to
#   stdout and exits 0. If no matching run appears within the timeout, it
#   prints a clear error to stderr and exits 1. It never guesses at a run ID
#   and never silently reports success for the wrong run.
#
# Usage:
#   find_release_ci_run.sh --repo <owner/repo> --workflow <file.yml> --sha <commit-sha> \
#       [--timeout <seconds>] [--interval <seconds>]
#
#   Prints the matching run's databaseId to stdout on success.
#
# Test: tests/test_find_release_ci_run.py exercises this script against a
#   fake `gh` binary on PATH that returns canned JSON, verifying that (a) a
#   run matching the requested head_sha is selected even when a newer,
#   unrelated run exists, (b) polling retries until the run appears, and
#   (c) the script fails loudly (non-zero exit, stderr message) when no
#   matching run ever appears before the timeout.

set -euo pipefail

usage() {
    echo "Usage: $0 --repo <owner/repo> --workflow <file.yml> --sha <commit-sha> [--timeout <seconds>] [--interval <seconds>]" >&2
    exit 2
}

REPO=""
WORKFLOW=""
SHA=""
TIMEOUT=180
INTERVAL=5

while [ $# -gt 0 ]; do
    case "$1" in
        --repo)
            REPO="$2"
            shift 2
            ;;
        --workflow)
            WORKFLOW="$2"
            shift 2
            ;;
        --sha)
            SHA="$2"
            shift 2
            ;;
        --timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        --interval)
            INTERVAL="$2"
            shift 2
            ;;
        -h | --help)
            usage
            ;;
        *)
            echo "Unknown argument: $1" >&2
            usage
            ;;
    esac
done

[ -n "$REPO" ] || usage
[ -n "$WORKFLOW" ] || usage
[ -n "$SHA" ] || usage

ELAPSED=0

while [ "$ELAPSED" -lt "$TIMEOUT" ]; do
    # Server-side filter by head_sha: only runs actually triggered by this
    # commit are ever returned, so we never have to guess or correlate
    # client-side. Sort defensively in case the API ever returns more than
    # one match (e.g. a manual workflow_dispatch re-run against the same SHA)
    # and pick the most recently created one.
    RESPONSE=$(gh api "repos/${REPO}/actions/workflows/${WORKFLOW}/runs?head_sha=${SHA}" 2>/dev/null || true)

    if [ -n "$RESPONSE" ]; then
        RUN_ID=$(printf '%s' "$RESPONSE" | jq -r '[.workflow_runs[]] | sort_by(.created_at) | reverse | .[0].id // empty')

        if [ -n "$RUN_ID" ] && [ "$RUN_ID" != "null" ]; then
            echo "$RUN_ID"
            exit 0
        fi
    fi

    sleep "$INTERVAL"
    ELAPSED=$((ELAPSED + INTERVAL))
done

echo "ERROR: no run of workflow '${WORKFLOW}' in ${REPO} matched commit ${SHA} within ${TIMEOUT}s" >&2
echo "  This usually means GitHub Actions has not started the run yet, or the tag/commit was never pushed." >&2
exit 1
