#!/usr/bin/env bash
# Verify trusty-memory and trusty-search installation.
#
# Checks performed:
#   1. Both binaries on PATH.
#   2. Both daemons responding to /health.
#   3. .mcp.json contains trusty server entries (if a .mcp.json exists in CWD).
#   4. On macOS, launchd plists exist.
#
# Usage: verify-trusty.sh
#
# Exits 0 if every applicable check passes, 1 otherwise (each failure printed
# to stderr).

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HEALTH_SCRIPT="${SCRIPT_DIR}/../../migration-wizard/scripts/check-service-health.sh"

ERRORS=0

note_failure() {
    echo "FAIL: $1" >&2
    ERRORS=$((ERRORS + 1))
}

# 1. Binaries on PATH
if ! command -v trusty-memory >/dev/null 2>&1; then
    note_failure "trusty-memory binary not on PATH"
fi
if ! command -v trusty-search >/dev/null 2>&1; then
    note_failure "trusty-search binary not on PATH"
fi

# 2. Daemon health (default ports)
if [[ -x "${HEALTH_SCRIPT}" ]]; then
    if ! bash "${HEALTH_SCRIPT}" "http://localhost:3038/health" 3 2>/dev/null; then
        note_failure "trusty-memory daemon not healthy on :3038"
    fi
    if ! bash "${HEALTH_SCRIPT}" "http://localhost:7878/health" 3 2>/dev/null; then
        note_failure "trusty-search daemon not healthy on :7878"
    fi
else
    # Inline fallback if the shared script isn't reachable.
    if ! curl -fs -o /dev/null --max-time 3 "http://localhost:3038/health"; then
        note_failure "trusty-memory daemon not healthy on :3038"
    fi
    if ! curl -fs -o /dev/null --max-time 3 "http://localhost:7878/health"; then
        note_failure "trusty-search daemon not healthy on :7878"
    fi
fi

# 3. .mcp.json wiring (only check when a .mcp.json exists in CWD)
if [[ -f ".mcp.json" ]] && command -v python3 >/dev/null 2>&1; then
    if ! python3 - <<'PYEOF'
import json
import sys

try:
    with open(".mcp.json") as f:
        data = json.load(f)
except (OSError, json.JSONDecodeError) as e:
    print(f"could not parse .mcp.json: {e}", file=sys.stderr)
    sys.exit(1)

servers = data.get("mcpServers", {})
expected = ("trusty-memory", "trusty-search")
missing = [name for name in expected if not any(name in key for key in servers)]
if missing:
    print(f"missing MCP entries: {missing}", file=sys.stderr)
    sys.exit(1)
PYEOF
    then
        note_failure ".mcp.json does not reference trusty-memory and trusty-search"
    fi
fi

# 4. macOS launchd plists
if [[ "$(uname -s)" == "Darwin" ]]; then
    PLIST_DIR="${HOME}/Library/LaunchAgents"
    if ! ls "${PLIST_DIR}"/com.bobmatnyc.trusty-memory.plist >/dev/null 2>&1; then
        note_failure "missing launchd plist: com.bobmatnyc.trusty-memory.plist"
    fi
    if ! ls "${PLIST_DIR}"/com.bobmatnyc.trusty-search.plist >/dev/null 2>&1; then
        note_failure "missing launchd plist: com.bobmatnyc.trusty-search.plist"
    fi
fi

if [[ "${ERRORS}" -eq 0 ]]; then
    echo "OK: trusty-memory and trusty-search verified"
    exit 0
fi
echo "verification failed with ${ERRORS} error(s)" >&2
exit 1
