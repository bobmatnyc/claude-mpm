# Ticket Management with AI Trackdown

Claude MPM uses `ai-trackdown-pytools` for comprehensive ticket management. This guide explains how to use the ticket system properly.

## Overview

AI Trackdown provides a complete ticket hierarchy:
- **Epics** - Large features or projects
- **Issues** - Medium-sized work items
- **Tasks** - Specific implementation items
- **Comments** - Discussion on any ticket type

## Installation

AI Trackdown is automatically installed with Claude MPM:

```bash
# Already included in requirements
pip install ai-trackdown-pytools
```

## Commands

### Using the ticket wrapper

Claude MPM provides a `ticket` wrapper for common operations:

```bash
# Create a task (default)
./ticket create "Fix login bug" -p high -d "Users cannot log in"

# Create an issue
./ticket create "Authentication system" -t issue -d "Implement OAuth2"

# Create an epic
./ticket create "Q1 Roadmap" -t epic

# List tasks
./ticket list

# View a specific ticket
./ticket view TSK-0001

# Update a ticket
./ticket update TSK-0001 -p critical

# Close a ticket
./ticket close TSK-0001
```

### Using aitrackdown directly

For full functionality, use `aitrackdown` directly:

```bash
# Task operations
aitrackdown task create "New feature" -p medium
aitrackdown task list
aitrackdown task show TSK-0001
aitrackdown task update TSK-0001 --assignee "John"
aitrackdown task complete TSK-0001

# Issue operations
aitrackdown issue create "Bug in payment system"
aitrackdown issue list --status open
aitrackdown issue link ISS-0001 TSK-0001

# Epic operations
aitrackdown epic create "Version 2.0"
aitrackdown epic add-issue EP-0001 ISS-0001
aitrackdown epic status EP-0001

# Comments
aitrackdown comment add TSK-0001 "Started working on this"
aitrackdown comment list TSK-0001
```

## Ticket Hierarchy

### Creating linked tickets

```bash
# Create an epic
aitrackdown epic create "Authentication System"
# Returns: EP-0001

# Create issues under the epic
aitrackdown issue create "OAuth2 Implementation" --epic EP-0001
# Returns: ISS-0001

# Create tasks under the issue
aitrackdown task create "Setup OAuth2 provider" --parent ISS-0001
# Returns: TSK-0001
```

### Viewing hierarchy

```bash
# View epic with all children
aitrackdown epic show EP-0001 --tree

# View issue with tasks
aitrackdown issue show ISS-0001 --with-tasks
```

## Configuration

AI Trackdown configuration is in `.ai-trackdown/config.yaml`:

```yaml
version: 0.9.0
project:
  name: claude-mpm
  
tasks:
  directory: tickets/tasks
  auto_id: true
  id_format: TSK-{counter:04d}
  
issues:
  directory: tickets/issues
  auto_id: true
  id_format: ISS-{counter:04d}
  
epics:
  directory: tickets/epics
  auto_id: true
  id_format: EP-{counter:04d}
```

## Automatic Ticket Creation

Claude MPM automatically creates tickets from Claude's output when it detects patterns like:
- `TODO: <description>`
- `BUG: <description>`
- `FEATURE: <description>`
- `ISSUE: <description>`
- `TASK: <description>`

These are automatically converted to appropriate ticket types.

## Best Practices

1. **Use the hierarchy**: Create epics for large features, issues for work items, and tasks for specific implementation
2. **Link related items**: Use `--epic` and `--parent` to maintain relationships
3. **Update status**: Keep tickets updated as work progresses
4. **Add comments**: Document progress and decisions with comments
5. **Use consistent priorities**: low, medium, high, critical

## Troubleshooting

### Command not found

If `aitrackdown` is not found:
```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Or reinstall
pip install --upgrade ai-trackdown-pytools
```

### Wrong directory

If tickets are created in the wrong location, check `.ai-trackdown/config.yaml` and ensure the paths are correct.

### Missing tickets

If you have existing tickets that don't show up:
```bash
# Re-index tickets
aitrackdown doctor --fix
```

## Integration with Claude MPM

The ticket system integrates with Claude MPM's automatic extraction:

1. Claude detects ticket patterns in output
2. Tickets are automatically created using aitrackdown
3. Proper hierarchy is maintained (epics → issues → tasks)
4. All tickets are stored in the `tickets/` directory

For more information, see the [AI Trackdown documentation](https://github.com/ai-trackdown/ai-trackdown-pytools).