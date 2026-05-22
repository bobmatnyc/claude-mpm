#!/usr/bin/env bash
# Quick status check for trusty services.
#
# Usage: check-trusty-status.sh
#
# Prints one of:
#   installed  - both binaries on PATH AND both daemons healthy
#   partial    - some components present, others missing
#   missing    - neither binary on PATH
#
# Always exits 0 so callers can capture the status string.

set -uo pipefail

have_memory=0
have_search=0
healthy_memory=0
healthy_search=0

command -v trusty-memory >/dev/null 2>&1 && have_memory=1
command -v trusty-search >/dev/null 2>&1 && have_search=1

if command -v curl >/dev/null 2>&1; then
    curl -fs -o /dev/null --max-time 2 "http://localhost:3038/health" \
        && healthy_memory=1 || true
    curl -fs -o /dev/null --max-time 2 "http://localhost:7878/health" \
        && healthy_search=1 || true
fi

if [[ "${have_memory}" -eq 1 && "${have_search}" -eq 1 \
    && "${healthy_memory}" -eq 1 && "${healthy_search}" -eq 1 ]]; then
    echo "installed"
elif [[ "${have_memory}" -eq 0 && "${have_search}" -eq 0 ]]; then
    echo "missing"
else
    echo "partial"
fi
