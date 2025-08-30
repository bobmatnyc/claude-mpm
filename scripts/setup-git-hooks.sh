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

# Replace if someone uses wrong emoji but right text
MODIFIED_MSG=$(echo "$MODIFIED_MSG" | sed 's/🤖 Generated with \[Claude MPM\]/🤖👥 Generated with [Claude MPM]/')

# Replace URLs
MODIFIED_MSG=$(echo "$MODIFIED_MSG" | sed 's/https:\/\/claude\.ai\/code/https:\/\/github.com\/bobmatnyc\/claude-mpm/g')

# Write the modified message back
echo "$MODIFIED_MSG" > "$COMMIT_MSG_FILE"
EOF

# Make the hook executable
chmod +x "$HOOKS_DIR/prepare-commit-msg"

echo -e "${GREEN}✅ Git hooks installed successfully!${NC}"
echo -e "${YELLOW}The prepare-commit-msg hook will automatically convert:${NC}"
echo "  '🤖 Generated with [Claude Code]' → '🤖👥 Generated with [Claude MPM]'"
echo ""
echo -e "${GREEN}Claude MPM branding will be applied to all commits automatically.${NC}"