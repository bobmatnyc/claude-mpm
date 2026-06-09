#!/bin/bash
# Setup Git Hooks for Claude MPM
# Ensures Claude MPM branding is always used in commit messages

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Setting up Claude MPM git hooks...${NC}"

# Get the project root directory
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOOKS_DIR="$PROJECT_ROOT/.git/hooks"

# Create hooks directory if it doesn't exist
mkdir -p "$HOOKS_DIR"

# Create the prepare-commit-msg hook
cat > "$HOOKS_DIR/prepare-commit-msg" << 'EOF'
#!/bin/bash
# Claude MPM Custom Commit Message Hook
# This hook modifies commit messages to use Claude MPM branding

# Force a UTF-8 locale for the emoji sed substitutions below. Under a non-UTF-8
# locale (LANG=C / POSIX) some seds mis-parse the multi-byte 🤖👥 patterns and
# silently skip the substitution. Probe for a UTF-8 locale that actually exists
# (C.UTF-8/C.utf8 on Linux, en_US.UTF-8 on macOS) and fall back gracefully.
_mpm_avail="$(locale -a 2>/dev/null)"
for _mpm_locale in C.UTF-8 C.utf8 en_US.UTF-8 en_US.utf8; do
    if printf '%s\n' "$_mpm_avail" | grep -qix "$_mpm_locale"; then
        export LC_ALL="$_mpm_locale"
        break
    fi
done
unset _mpm_locale _mpm_avail

COMMIT_MSG_FILE=$1
COMMIT_SOURCE=$2
SHA1=$3

# Read the original commit message
ORIGINAL_MSG=$(cat "$COMMIT_MSG_FILE")

# Replace various Claude Code references with Claude MPM
# Using 🤖👥 (AI + Team) representing multi-agent orchestration
MODIFIED_MSG="$ORIGINAL_MSG"

# Replace standard Claude Code format
MODIFIED_MSG=$(echo "$MODIFIED_MSG" | sed 's/🤖 Generated with \[Claude Code\](https:\/\/claude\.ai\/code)/🤖👥 Generated with [Claude MPM](https:\/\/github.com\/bobmatnyc\/claude-mpm)/')

# Replace without emoji
MODIFIED_MSG=$(echo "$MODIFIED_MSG" | sed 's/Generated with \[Claude Code\](https:\/\/claude\.ai\/code)/🤖👥 Generated with [Claude MPM](https:\/\/github.com\/bobmatnyc\/claude-mpm)/')

# Replace text-only format
MODIFIED_MSG=$(echo "$MODIFIED_MSG" | sed 's/Generated with \[Claude Code\]/Generated with [Claude MPM]/')
MODIFIED_MSG=$(echo "$MODIFIED_MSG" | sed 's/Generated with Claude Code/Generated with Claude MPM/')

# Normalize the icon to the canonical 🤖👥 (multi-agent) for any MPM footer
# variant: bare (no icon), single 🤖, or doubled 🤖🤖.
MODIFIED_MSG=$(echo "$MODIFIED_MSG" | sed 's/🤖🤖 Generated with \[Claude MPM\]/🤖👥 Generated with [Claude MPM]/')
MODIFIED_MSG=$(echo "$MODIFIED_MSG" | sed 's/🤖 Generated with \[Claude MPM\]/🤖👥 Generated with [Claude MPM]/')
# Only prefix the canonical icon onto a *bare* footer: the line must be the
# full footer (text + URL) with no preceding emoji, so we don't accidentally
# decorate an unrelated line that merely starts with "Generated with [Claude MPM]".
MODIFIED_MSG=$(echo "$MODIFIED_MSG" | sed 's#^Generated with \[Claude MPM\](https://github.com/bobmatnyc/claude-mpm)$#🤖👥 Generated with [Claude MPM](https://github.com/bobmatnyc/claude-mpm)#')

# Replace URLs
MODIFIED_MSG=$(echo "$MODIFIED_MSG" | sed 's/https:\/\/claude\.ai\/code/https:\/\/github.com\/bobmatnyc\/claude-mpm/g')

# Write the modified message back
echo "$MODIFIED_MSG" > "$COMMIT_MSG_FILE"
EOF

# Make the hook executable
chmod +x "$HOOKS_DIR/prepare-commit-msg"

# Install the pre-push guard that blocks direct pushes of credential/security-
# sensitive files (e.g. scripts/lib/gh_identity.sh) to main. The canonical
# source lives in .githooks/pre-push (checked into the repo); copy it in.
PRE_PUSH_SRC="$PROJECT_ROOT/.githooks/pre-push"
if [ -f "$PRE_PUSH_SRC" ]; then
    cp "$PRE_PUSH_SRC" "$HOOKS_DIR/pre-push"
    chmod +x "$HOOKS_DIR/pre-push"
else
    echo -e "${YELLOW}⚠️  .githooks/pre-push not found — skipping credential-push guard install.${NC}"
fi

echo -e "${GREEN}✅ Git hooks installed successfully!${NC}"
echo -e "${YELLOW}The prepare-commit-msg hook will automatically convert:${NC}"
echo "  '🤖 Generated with [Claude Code]' → '🤖👥 Generated with [Claude MPM]'"
echo ""
echo -e "${GREEN}The pre-push hook guards against direct pushes of credential/security-sensitive${NC}"
echo -e "${GREEN}files (e.g. scripts/lib/gh_identity.sh) to main — those must go through a PR.${NC}"
echo ""
echo -e "${GREEN}Claude MPM branding will be applied to all commits automatically.${NC}"
