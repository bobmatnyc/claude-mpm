#!/usr/bin/env bash
# check_clean_workspace.sh — fail-fast dirty-workspace guard for CI
#
# WHAT: Exits with a non-zero status and a human-readable error message if any
#       tracked source file is modified at the start of a CI job.
# WHY:  mutmut (mutation testing) mutates source files in-place.  If a prior
#       job or a local developer run left a mutated file behind — e.g. because
#       the restore step was skipped on an aborted run — the pytest job would
#       silently import a mutant instead of the real source.  The symptom is a
#       shifted-line-number TypeError like the one seen on PR #885 (TypeError:
#       unsupported operand type(s) for |: 'frozenset' and 'NoneType' in
#       trusty_search_allowlist.py — issue #887).  An early, explicit failure
#       here turns silent contamination into an obvious, actionable error.
#
# NOTE: CI does NOT currently run mutmut in any workflow (the mutation-test
#       Makefile target is explicitly "on-demand only").  This guard is
#       defence-in-depth: it also catches any other source of dirty-workspace
#       contamination (e.g. a stale .pyc-level patch, a botched merge, or a
#       future CI job that does run mutmut).
#
# Usage (in workflow):
#   - name: Guard — fail if tracked source files are dirty at job start
#     run: bash scripts/check_clean_workspace.sh
#
# Local dry-run (should PASS on a clean checkout):
#   bash scripts/check_clean_workspace.sh
#
# Local failure test — simulate a mutant, then revert:
#   echo "# mutant" >> src/claude_mpm/services/trusty_search_allowlist.py
#   bash scripts/check_clean_workspace.sh   # exits 1
#   git checkout -- src/claude_mpm/services/trusty_search_allowlist.py

set -euo pipefail

# git diff --name-only lists tracked files that differ from HEAD.
# We include both working-tree changes (unstaged) and index changes (staged)
# to catch any path by which a mutated file could end up in the workspace.
dirty_files=$(git diff --name-only HEAD 2>/dev/null || true)
staged_files=$(git diff --name-only --cached HEAD 2>/dev/null || true)

combined=$(printf '%s\n%s' "$dirty_files" "$staged_files" \
    | sort -u \
    | grep -v '^[[:space:]]*$' \
    || true)

if [ -n "$combined" ]; then
    # GitHub Actions annotation (no-op outside GHA)
    echo "::error::DIRTY WORKSPACE DETECTED — possible mutation-test contamination (issue #887)"
    echo ""
    echo "ERROR: tracked source files are modified at job start — possible"
    echo "       mutation-test contamination (issue #887)"
    echo ""
    echo "Modified tracked files:"
    echo "$combined" | sed 's/^/  /'
    echo ""
    echo "This can happen when mutmut leaves a mutated file on disk after an"
    echo "aborted run.  On PR #885 this caused a shifted-line TypeError at"
    echo "import of trusty_search_allowlist.py."
    echo ""
    echo "Fix options:"
    echo "  CI:    check whether a prior job left mutated files;"
    echo "         run:  git checkout -- .  then re-trigger the job."
    echo "  Local: run   git checkout -- .  to restore all tracked files."
    echo "         If .mutmut-cache exists, a prior mutmut run is the likely cause."
    exit 1
fi

echo "clean-workspace-check: OK — no tracked source files modified at job start."
