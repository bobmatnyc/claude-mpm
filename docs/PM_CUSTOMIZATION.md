# PM Customization Guide

This guide explains how to customize PM (Project Manager) instructions in Claude MPM.

## Overview

Claude MPM allows you to customize PM behavior by creating custom `INSTRUCTIONS.md` files in `.claude-mpm` directories. These instructions extend or override the default framework PM instructions.

## Important: DO NOT Use CLAUDE.md

**NEVER** create or modify `CLAUDE.md` files for PM customization. Claude Code automatically reads CLAUDE.md files, and duplicating instructions would cause conflicts. The framework is designed to use `INSTRUCTIONS.md` files in `.claude-mpm` directories instead.

## Customization Levels

PM instructions can be customized at two levels:

1. **User Level** (`~/.claude-mpm/INSTRUCTIONS.md`)
   - Applies to all projects for the current user
   - Located in your home directory
   
2. **Project Level** (`./.claude-mpm/INSTRUCTIONS.md`)
   - Applies only to the current project
   - Located in the project root directory
   - Takes precedence over user-level instructions

## Using the customize-pm Command

The `agent-manager customize-pm` command helps you create and manage custom PM instructions:

```bash
# Customize at user level (default)
claude-mpm agent-manager customize-pm

# Customize at project level
claude-mpm agent-manager customize-pm --level project

# Use with custom patterns
claude-mpm agent-manager customize-pm --patterns "Pattern 1" "Pattern 2"

# Add custom rules
claude-mpm agent-manager customize-pm --rules "Rule 1" "Rule 2"
```

## Manual Customization

You can also manually create the `INSTRUCTIONS.md` file:

```bash
# For project-level customization
mkdir -p .claude-mpm
echo "# Custom PM Instructions" > .claude-mpm/INSTRUCTIONS.md

# For user-level customization
mkdir -p ~/.claude-mpm
echo "# Custom PM Instructions" > ~/.claude-mpm/INSTRUCTIONS.md
```

## Example Custom Instructions

Here's an example of what you might put in your custom `INSTRUCTIONS.md`:

```markdown
# Custom PM Instructions

## Project-Specific Delegation Patterns

- Always delegate database work to the Data Engineer agent
- Use the Security agent for any authentication-related tasks
- Prioritize the QA agent for all testing requests

## Additional Rules

- Never allow direct database access without Security agent review
- Always create comprehensive test coverage for new features
- Document all architectural decisions in ADR format

## Workflow Overrides

### Feature Development
1. Research agent analyzes requirements
2. Engineer implements with Security review
3. QA validates implementation
4. Documentation agent updates docs
```

## How It Works

1. When Claude MPM starts, the framework loader looks for custom instructions
2. It checks for `.claude-mpm/INSTRUCTIONS.md` in the following order:
   - Current project directory (highest priority)
   - User home directory
3. If found, these instructions are loaded and integrated with the framework
4. The custom instructions appear in the PM's context, extending or overriding defaults

## Best Practices

1. **Keep instructions focused** - Only include project-specific or user-specific customizations
2. **Don't duplicate framework instructions** - Only add what's different or additional
3. **Use clear section headers** - Organize your instructions for readability
4. **Version control project instructions** - Include `.claude-mpm/INSTRUCTIONS.md` in your repository
5. **Don't create CLAUDE.md files** - The framework handles PM instructions separately

## Troubleshooting

### Instructions not being loaded?

1. Check file location: `.claude-mpm/INSTRUCTIONS.md` (not `CLAUDE.md`)
2. Verify the directory structure is correct
3. Look for typos in the filename
4. Check the framework loader logs for any errors

### Conflicts with CLAUDE.md?

If you have old `CLAUDE.md` files from previous versions:
1. Move any PM-specific content to `.claude-mpm/INSTRUCTIONS.md`
2. Keep project-specific development guidelines in `CLAUDE.md` (for Claude Code)
3. Remove any PM delegation instructions from `CLAUDE.md`

## Migration from Old System

If you were previously using CLAUDE.md for PM customization:

```bash
# Backup old file
cp CLAUDE.md CLAUDE.md.backup

# Create new structure
mkdir -p .claude-mpm

# Move PM instructions to new location
# (manually copy relevant sections)
vim .claude-mpm/INSTRUCTIONS.md

# Remove PM instructions from CLAUDE.md
# (keep only development guidelines)
```

## Summary

- Use `.claude-mpm/INSTRUCTIONS.md` for PM customization
- Never create or modify `CLAUDE.md` for PM instructions
- Project-level instructions override user-level
- Use the `customize-pm` command for easy management