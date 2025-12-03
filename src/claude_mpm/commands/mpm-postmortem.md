---
namespace: mpm/analysis
command: postmortem
aliases: [mpm-postmortem]
migration_target: /mpm/analysis:postmortem
category: analysis
deprecated_aliases: []
description: Analyze session errors and suggest improvements
---
# Analyze session errors and suggest improvements

Perform a comprehensive analysis of errors encountered during the current or previous session and generate actionable improvement suggestions.

## Usage

```
/mpm-postmortem [options]
```

## Description

The postmortem command analyzes errors from:
- Script execution failures
- Skill execution issues
- Agent instruction problems
- User code errors (analysis only)

It categorizes errors, identifies root causes, and generates actionable improvements:
- **Scripts**: Tests and fixes in place
- **Skills**: Updates skill files with improvements
- **MPM Agents**: Prepares PRs with rationale for remote agent repository
- **User Code**: Provides suggestions without modification

## Options

- `--dry-run`: Preview analysis without making changes (default for destructive operations)
- `--auto-fix`: Automatically apply fixes to scripts and skills
- `--create-prs`: Create pull requests for agent improvements
- `--session-id <id>`: Analyze specific session (default: current session)
- `--format <format>`: Output format: terminal, json, markdown (default: terminal)
- `--output <file>`: Save report to file
- `--verbose`: Include detailed error traces and analysis

## Examples

```bash
# Analyze current session
/mpm-postmortem

# Preview changes without applying
/mpm-postmortem --dry-run

# Auto-fix scripts and skills
/mpm-postmortem --auto-fix

# Create PRs for agent improvements
/mpm-postmortem --create-prs

# Analyze specific session
/mpm-postmortem --session-id 2025-12-03-143000

# Save detailed report
/mpm-postmortem --verbose --output postmortem-report.md
```

## Expected Output

```
📊 Session Postmortem Analysis
═══════════════════════════════

Session: 2025-12-03-143000
Duration: 45 minutes
Errors Found: 3

🔧 Script Errors (1)
─────────────────────
• manage_version.py line 42: KeyError 'version'
  Root Cause: Missing default value handling for optional configuration
  Fix: Add fallback to default value when key not present
  Status: Fixed ✓

📚 Skill Errors (0)
──────────────────
No skill errors detected

🤖 Agent Improvements (2)
──────────────────────────
• ticketing agent: Timeout on large ticket lists
  Issue: Default timeout too short for projects with 500+ tickets
  Improvement: Add pagination support and increase timeout threshold
  PR: Created #123 (awaiting review)

• engineer agent: Type validation missing for tool parameters
  Issue: Invalid parameters passed to Edit tool causing failures
  Improvement: Add parameter validation before tool invocation
  Status: Ready to create PR (use --create-prs)

💡 User Code Suggestions (0)
────────────────────────────
No user code issues detected

📈 Summary
──────────
Total Errors: 3
Fixed: 1
PRs Created: 1
Suggestions: 1
```

## Safety Features

- **Dry-run by default**: Preview changes before applying
- **Confirmation prompts**: Verify before creating PRs
- **Backup before modifications**: Automatic backup of modified files
- **Rollback capability**: Restore previous versions if needed
- **Git integration**: Check for uncommitted changes before modifications

## Related Commands

- `/mpm-doctor`: Diagnose installation and configuration issues
- `/mpm-session-resume`: Resume previous session with context
- `/mpm-status`: View current system status
