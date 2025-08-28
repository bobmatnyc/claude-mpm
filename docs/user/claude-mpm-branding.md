# Claude MPM Git Branding Customization

This guide explains how to customize git commit and PR messages to use Claude MPM branding instead of Claude Code.

## Overview

Claude MPM provides custom branding for git operations through:
- A git hook that automatically modifies commit messages
- Wrapper scripts for git and GitHub CLI commands
- Custom emoji (🤖👥) representing AI orchestrating a team

## Automatic Setup

The prepare-commit-msg hook at `.git/hooks/prepare-commit-msg` automatically:
- Replaces "🤖 Generated with [Claude Code]" with "🤖👥 Generated with [Claude MPM]"
- Updates the URL from claude.ai/code to github.com/bobmatnyc/claude-mpm
- Maintains Co-Authored-By attribution

## Manual Usage

### For Git Commits

Use the wrapper script for immediate customization:
```bash
./scripts/git-claude-mpm commit -m "Your message"
```

Or create an alias:
```bash
alias git-mpm="/path/to/claude-mpm/scripts/git-claude-mpm"
```

### For GitHub PRs

Use the GitHub CLI wrapper:
```bash
./scripts/gh-claude-mpm pr create --title "Title" --body "Body"
```

Or create an alias:
```bash
alias gh-mpm="/path/to/claude-mpm/scripts/gh-claude-mpm"
```

## Default Message Format

### Commit Messages
```
Your commit message

🤖👥 Generated with [Claude MPM](https://github.com/bobmatnyc/claude-mpm)

Co-Authored-By: Claude <noreply@anthropic.com>
```

### PR Bodies
```
## Summary
- Your changes

## Test plan
- Your tests

🤖👥 Generated with [Claude MPM](https://github.com/bobmatnyc/claude-mpm)
```

## Emoji Reference

- 🤖👥 - AI orchestrating a team (Claude MPM)
- 🤖🤖 - Multiple robots (alternative)
- 🤖 - Single robot (Claude Code)
- 🫂🤖 - Collaboration with AI (alternative)
- 🤝🤖 - Partnership with AI (alternative)

## Integration with Claude Code

These customizations work seamlessly when Claude Code creates commits or PRs in the claude-mpm project. The hooks and wrappers automatically apply the branding without requiring manual intervention.

## Testing

To test the customization:
```bash
# Test commit message modification
echo "test" > test.txt
git add test.txt
git commit -m "Test commit

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>"

# Check the commit message
git log -1 --pretty=format:"%B"
# Should show: 🤖👥 Generated with [Claude MPM](https://github.com/bobmatnyc/claude-mpm)
```

## Troubleshooting

If customization isn't working:
1. Ensure hooks are executable: `chmod +x .git/hooks/prepare-commit-msg`
2. Check wrapper scripts are executable: `chmod +x scripts/git-claude-mpm scripts/gh-claude-mpm`
3. Verify sed is available: `which sed`

## Contributing

To improve the branding customization:
1. Edit `.git/hooks/prepare-commit-msg` for commit messages
2. Update `scripts/git-claude-mpm` for git operations
3. Modify `scripts/gh-claude-mpm` for GitHub operations