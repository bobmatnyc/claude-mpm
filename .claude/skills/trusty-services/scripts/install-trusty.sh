#!/usr/bin/env bash
# Install trusty-memory and trusty-search.
#
# Prefers the consolidated `claude-mpm setup` command (handles cargo install,
# launchd plist creation, and .mcp.json wiring atomically). Falls back to
# cargo + per-binary setup if the consolidated command is not available.
#
# Usage: install-trusty.sh
#
# Exit 0 on success, non-zero on any installation failure.

set -euo pipefail

echo "==> Installing trusty-memory and trusty-search"

if command -v claude-mpm >/dev/null 2>&1; then
    # Probe whether the multi-arg setup form exists in this version.
    if claude-mpm setup --help 2>&1 | grep -qE 'trusty-memory|trusty-search'; then
        echo "==> Using consolidated 'claude-mpm setup' command"
        claude-mpm setup trusty-memory trusty-search
        exit $?
    fi

    # Fall back to per-binary setup (older claude-mpm versions).
    echo "==> Using per-binary 'claude-mpm setup <name>'"
    claude-mpm setup trusty-memory
    claude-mpm setup trusty-search
    exit $?
fi

# No claude-mpm CLI available — fall back to raw cargo install. The user
# will need to start the daemons manually.
if ! command -v cargo >/dev/null 2>&1; then
    echo "error: neither 'claude-mpm' nor 'cargo' are on PATH" >&2
    echo "  install Rust first: https://rustup.rs/" >&2
    exit 1
fi

echo "==> Fallback: cargo install trusty-memory trusty-search"
echo "    Note: daemon startup and .mcp.json wiring must be done manually."
cargo install trusty-memory trusty-search
