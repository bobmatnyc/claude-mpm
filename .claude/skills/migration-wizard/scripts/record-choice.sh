#!/usr/bin/env bash
# Record a migration skill user choice via the Python CLI module.
#
# Usage: record-choice.sh <state_key> <action> [reason]
#
# Actions: complete | decline | defer | status | reset
#
# This is a thin wrapper around `python3 -m claude_mpm.migrations.user_choices_cli`
# so that other shell scripts in the migration-wizard system have a stable
# command to call without needing to know the Python module path.
#
# Exits with the underlying CLI's exit code.

set -euo pipefail

if [[ $# -lt 2 ]]; then
    echo "Usage: $0 <state_key> <complete|decline|defer|status|reset> [reason]" >&2
    exit 1
fi

# Resolve a usable python interpreter. Prefer python3, fall back to python.
PYTHON_BIN="${PYTHON:-}"
if [[ -z "${PYTHON_BIN}" ]]; then
    if command -v python3 >/dev/null 2>&1; then
        PYTHON_BIN="python3"
    elif command -v python >/dev/null 2>&1; then
        PYTHON_BIN="python"
    else
        echo "error: no python3 or python on PATH" >&2
        exit 2
    fi
fi

exec "${PYTHON_BIN}" -m claude_mpm.migrations.user_choices_cli "$@"
