#!/usr/bin/env bash
# Print the list of pending migration skill state_keys to stdout, one per line.
#
# Usage: list-pending-migrations.sh
#
# Reads ~/.claude-mpm/pending-migrations.json (produced by the
# check_migration_skills startup migration). If the file is missing or
# malformed, prints nothing and exits 0 — a missing file is normal during
# fresh installs.

set -uo pipefail

PENDING_FILE="${HOME}/.claude-mpm/pending-migrations.json"

if [[ ! -f "${PENDING_FILE}" ]]; then
    exit 0
fi

# Prefer python3 (always available on this codebase). Fall back to a
# best-effort grep-based parser if Python is missing.
if command -v python3 >/dev/null 2>&1; then
    python3 -c "
import json
import sys
try:
    with open('${PENDING_FILE}') as f:
        data = json.load(f)
    for key in data.get('pending', []) or []:
        if isinstance(key, str):
            print(key)
except (json.JSONDecodeError, OSError):
    sys.exit(0)
"
    exit 0
fi

# Python-less fallback: extract values from a flat "pending" array.
grep -o '"[a-zA-Z0-9_-]\+"' "${PENDING_FILE}" 2>/dev/null \
    | tr -d '"' \
    | grep -v '^pending$\|^checked_at$' \
    || true
