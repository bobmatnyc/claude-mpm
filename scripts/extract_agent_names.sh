#!/usr/bin/env bash
# extract_agent_names.sh — Regenerate AGENT_NAME_MAP from deployed agents.
#
# Reads the name: frontmatter field from every .md file in .claude/agents/
# (excluding BASE_AGENT.md and README.md) and outputs Python dict entries
# suitable for pasting into agent_name_registry.py.
#
# Usage:
#   ./scripts/extract_agent_names.sh
#
# To verify the registry is in sync:
#   ./scripts/extract_agent_names.sh | sort > /tmp/extracted.txt
#   grep '^\s*"' src/claude_mpm/core/agent_name_registry.py | \
#       grep -v '^\s*#' | sed 's/^ *//' | sort > /tmp/coded.txt
#   diff /tmp/extracted.txt /tmp/coded.txt

set -euo pipefail

AGENTS_DIR="${1:-.claude/agents}"

if [[ ! -d "$AGENTS_DIR" ]]; then
    echo "ERROR: agents directory not found: $AGENTS_DIR" >&2
    exit 1
fi

for f in "$AGENTS_DIR"/*.md; do
    [[ "$(basename "$f")" == BASE_AGENT.md ]] && continue
    [[ "$(basename "$f")" == README.md ]] && continue

    stem="$(basename "$f" .md)"
    name="$(grep '^name:' "$f" | head -1 | sed 's/^name: *//')"

    if [[ -z "$name" ]]; then
        echo "# WARNING: no name: field in $f" >&2
        continue
    fi

    printf '    "%s": "%s",\n' "$stem" "$name"
done
