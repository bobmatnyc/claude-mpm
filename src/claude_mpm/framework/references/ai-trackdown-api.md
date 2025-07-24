# AI Trackdown Tools API Reference

## Overview
Complete API reference for AI Trackdown Tools CLI - the primary ticketing interface for Claude PM Framework.

## Hierarchical Structure
```
Epics → Issues → Tasks → PRs (Pull Requests)
Each level tracks tokens, progress, and relationships
```

## Epic Management

### Create Epic
```bash
aitrackdown epic create "Title" [options]
  --description "Description"
  --priority high|medium|low
  --assignee username
  --estimated-tokens 5000
  --story-points 13
```

### Epic Operations
```bash
aitrackdown epic list [--status active] [--show-progress]
aitrackdown epic show EP-0001 [--with-issues]
aitrackdown epic update EP-0001 --status active --priority critical
aitrackdown epic complete EP-0001 --actual-tokens 1500
```

## Issue Management

### Create Issue
```bash
aitrackdown issue create "Title" --epic EP-0001 [options]
  --priority high|medium|low|urgent|critical
  --assignee username
  --estimated-tokens 800
  --tags security,backend
```

### Issue Operations
```bash
aitrackdown issue list [--epic EP-0001] [--status active]
aitrackdown issue show ISS-0001 [--with-tasks]
aitrackdown issue update ISS-0001 --status in_progress
aitrackdown issue complete ISS-0001 --actual-tokens 500
```

## Task Management

### Task Operations
```bash
aitrackdown task create "Title" --issue ISS-0001
aitrackdown task list --issue ISS-0001
aitrackdown task update TSK-0001 --status active
aitrackdown task complete TSK-0001 --time-spent 2h
```

## Pull Request Management

```bash
aitrackdown pr create "Title" --issue ISS-0001
aitrackdown pr update PR-0001 --status review
aitrackdown pr merge PR-0001 --delete-branch
```

## State Management

### Resolution Commands
```bash
aitrackdown resolve engineering ISS-0001
aitrackdown resolve qa ISS-0001 --assignee john
aitrackdown resolve deployment ISS-0001
aitrackdown resolve done ISS-0001
```

## AI-Specific Features

```bash
aitrackdown ai track-tokens --report
aitrackdown ai generate-llms-txt --format detailed
aitrackdown ai context --item-id EP-0001 --add "paths"
```

## GitHub Integration

```bash
aitrackdown sync setup --repository owner/repo
aitrackdown sync bidirectional
aitrackdown sync status --verbose
```

## Project Status

```bash
aitrackdown status
aitrackdown status-enhanced --verbose
aitrackdown backlog --with-issues
aitrackdown portfolio --health
aitrackdown health --verbose
```

## Data Management

```bash
aitrackdown export --format json --output file.json
aitrackdown migrate --dry-run --verbose
aitrackdown backlog-enhanced --rebuild-index
```

## Global Options

```bash
--project-dir <path>    # Target any project directory
--verbose              # Detailed output
--dry-run             # Preview without changes
--format json|yaml    # Output format
```

## Status Values
- `todo`
- `in_progress`
- `blocked`
- `review`
- `testing`
- `done`
- `cancelled`

## Priority Values
- `low`
- `medium`
- `high`
- `urgent`
- `critical`

---

**API Version**: 1.0.0  
**CLI**: AI Trackdown Tools  
**Primary Usage**: Claude PM Framework ticketing