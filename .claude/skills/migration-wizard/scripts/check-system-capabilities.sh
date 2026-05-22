#!/usr/bin/env bash
# Check generic host capabilities (RAM and free disk space).
#
# Usage:
#     check-system-capabilities.sh [--min-ram-gb N] [--min-disk-gb N]
#
# Defaults: --min-ram-gb 4, --min-disk-gb 2.
#
# Exit codes:
#     0  All checks pass.
#     1  One or more checks failed (explanation printed to stderr).
#     2  Internal error (could not determine RAM or disk).
#
# Portable across macOS (BSD tools) and Linux (GNU tools).

set -uo pipefail

MIN_RAM_GB=4
MIN_DISK_GB=2

while [[ $# -gt 0 ]]; do
    case "$1" in
        --min-ram-gb)
            MIN_RAM_GB="$2"
            shift 2
            ;;
        --min-disk-gb)
            MIN_DISK_GB="$2"
            shift 2
            ;;
        --help|-h)
            grep '^#' "$0" | sed 's/^# \{0,1\}//'
            exit 0
            ;;
        *)
            echo "error: unknown option: $1" >&2
            exit 2
            ;;
    esac
done

# --- RAM detection ---
RAM_BYTES=""
case "$(uname -s)" in
    Darwin)
        RAM_BYTES="$(sysctl -n hw.memsize 2>/dev/null || true)"
        ;;
    Linux)
        if [[ -r /proc/meminfo ]]; then
            # MemTotal is in kB
            kb="$(awk '/^MemTotal:/ {print $2}' /proc/meminfo)"
            if [[ -n "${kb}" ]]; then
                RAM_BYTES=$((kb * 1024))
            fi
        fi
        ;;
esac

if [[ -z "${RAM_BYTES}" || "${RAM_BYTES}" -eq 0 ]]; then
    echo "error: could not determine system RAM" >&2
    exit 2
fi

RAM_GB=$((RAM_BYTES / 1024 / 1024 / 1024))

# --- Disk detection (free space in $HOME) ---
# df -k prints kilobytes; the "Available" column is 4 on macOS/Linux.
# Use $HOME as the target since that's where most installs land.
DISK_KB="$(df -k "${HOME}" 2>/dev/null | awk 'NR==2 {print $4}')"
if [[ -z "${DISK_KB}" ]]; then
    echo "error: could not determine free disk space in ${HOME}" >&2
    exit 2
fi
DISK_GB=$((DISK_KB / 1024 / 1024))

FAILED=0

if [[ "${RAM_GB}" -lt "${MIN_RAM_GB}" ]]; then
    echo "RAM check FAILED: have ${RAM_GB}GB, need ${MIN_RAM_GB}GB" >&2
    FAILED=1
fi

if [[ "${DISK_GB}" -lt "${MIN_DISK_GB}" ]]; then
    echo "Disk check FAILED: have ${DISK_GB}GB free in ${HOME}, need ${MIN_DISK_GB}GB" >&2
    FAILED=1
fi

if [[ "${FAILED}" -eq 0 ]]; then
    echo "OK: RAM=${RAM_GB}GB (>=${MIN_RAM_GB}GB), Disk=${DISK_GB}GB free (>=${MIN_DISK_GB}GB)"
    exit 0
fi
exit 1
