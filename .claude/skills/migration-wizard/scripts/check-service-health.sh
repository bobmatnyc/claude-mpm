#!/usr/bin/env bash
# Probe a service's HTTP health endpoint.
#
# Usage: check-service-health.sh <url> [timeout_seconds]
#
# Exits 0 if the endpoint returns any 2xx response within the timeout
# (default 3 seconds), 1 otherwise. Output is suppressed; use exit codes.
#
# Examples:
#     check-service-health.sh http://localhost:3038/health
#     check-service-health.sh http://localhost:7878/health 5

set -uo pipefail

if [[ $# -lt 1 ]]; then
    echo "Usage: $0 <url> [timeout_seconds]" >&2
    exit 2
fi

URL="$1"
TIMEOUT="${2:-3}"

if ! command -v curl >/dev/null 2>&1; then
    echo "error: curl not installed" >&2
    exit 2
fi

# -f: fail on HTTP >=400, -s: silent, -o /dev/null: discard body,
# --max-time: hard cap on total request time.
if curl -fs -o /dev/null --max-time "${TIMEOUT}" "${URL}"; then
    exit 0
fi
exit 1
