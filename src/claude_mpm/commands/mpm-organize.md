---
namespace: mpm/system
command: organize
aliases: [mpm-organize]
migration_target: /mpm/system:organize
category: system
description: Consolidate, prune, triage, and organize documentation files
---
# /mpm-organize

Consolidate, prune, triage, and organize your project's documentation files into a clean, structured format.

## Usage

```
/mpm-organize                       # Interactive mode with preview
/mpm-organize --dry-run             # Preview changes without applying
/mpm-organize --force               # Proceed even with uncommitted changes
/mpm-organize --no-backup           # Skip backup creation (not recommended)
```

## Description

This slash command delegates to the **Project Organizer agent** to perform intelligent documentation organization. The agent analyzes your documentation files, detects existing structure patterns, consolidates duplicates, removes stale content, and organizes everything into a clean, logical structure.

**Documentation Focus**: This command ONLY touches documentation files (.md, .rst, .txt docs). Source code, configuration files, tests, and build artifacts are never modified.

**Smart Detection**: The agent first looks for existing documentation organization patterns in your project. If found, it respects and extends those patterns. If not found, it organizes into a standard structure: `docs/research/`, `docs/user/`, `docs/developer/`.

## Features

- **📁 Pattern Detection**: Analyzes existing documentation structure and conventions
- **🔄 Consolidation**: Merges duplicate or related documentation files
- **✂️ Pruning**: Identifies and removes outdated, stale, or redundant docs
- **📋 Triage**: Categorizes docs into appropriate directories (research/user/developer)
- **✅ Safe Operations**: Uses `git mv` for tracked files to preserve history
- **💾 Automatic Backups**: Creates backups before major reorganizations
- **📊 Organization Report**: Detailed summary of changes and recommendations
- **🎯 Documentation Only**: Never touches code, config, tests, or build files

## Options

### Safety Options
- `--dry-run`: Preview all changes without making them (recommended first run)
- `--no-backup`: Skip backup creation before reorganization (not recommended)
- `--force`: Proceed even with uncommitted changes (use with caution)

### Organization Options
- `--consolidate-only`: Only consolidate duplicate docs, skip reorganization
- `--prune-only`: Only identify and remove stale docs
- `--triage-only`: Only categorize docs without moving them
- `--no-prune`: Skip pruning phase (keep all existing docs)

### Output Options
- `--verbose`: Show detailed analysis and reasoning
- `--quiet`: Minimal output, errors only
- `--report [path]`: Save organization report to file

## What This Command Does

### 1. Pattern Detection
- Scans existing documentation structure
- Identifies documentation organization conventions
- Detects if project uses custom docs structure
- Falls back to standard structure if no pattern found

### 2. Standard Documentation Structure

If no existing pattern is detected, organizes into:

```
docs/
├── research/     # Research findings, analysis, investigations
│   ├── spikes/   # Technical spikes and experiments
│   └── notes/    # Development notes and brainstorming
├── user/         # User-facing documentation
│   ├── guides/   # How-to guides and tutorials
│   ├── faq/      # Frequently asked questions
│   └── examples/ # Usage examples
└── developer/    # Developer documentation
    ├── api/      # API documentation
    ├── architecture/ # Architecture decisions and diagrams
    └── contributing/ # Contribution guidelines
```

### 3. Documentation Consolidation

Identifies and merges:
- Duplicate README files
- Similar guide documents
- Redundant architecture notes
- Multiple versions of same doc
- Scattered meeting notes

### 4. Documentation Pruning

Removes or archives:
- Outdated documentation (based on last modified date)
- Stale TODO lists and notes
- Obsolete architecture documents
- Deprecated API documentation
- Empty or placeholder files

### 5. Documentation Triage

Categorizes documentation by content:
- **Research**: Analysis, spikes, investigations, experiments
- **User**: Guides, tutorials, FAQs, how-tos
- **Developer**: API docs, architecture, contributing guides

### 6. Safe File Movement

For each documentation file:
1. Analyzes content and purpose
2. Determines optimal location based on patterns
3. Uses `git mv` for version-controlled files
4. Preserves git history
5. Creates backup before changes

### 7. Backup Creation

Before reorganization:
```bash
backup_docs_YYYYMMDD_HHMMSS.tar.gz  # Documentation backup
```

### 8. Files That Are NEVER Touched

This command explicitly ignores:
- Source code files (.py, .js, .ts, .java, etc.)
- Configuration files (.json, .yaml, .toml, etc.)
- Test files (*_test.*, test_*.*, *.test.*, *.spec.*)
- Build artifacts (dist/, build/, node_modules/, etc.)
- Package files (package.json, pyproject.toml, etc.)

### 9. Organization Report

Generates detailed report including:
- Documentation files moved and new locations
- Files consolidated (merged)
- Files pruned (removed or archived)
- Pattern analysis and detected conventions
- Recommendations for documentation improvements

## Examples

### Preview Documentation Organization (Recommended First Run)
```bash
/mpm-organize --dry-run
```
Shows what documentation changes would be made without applying them.

### Full Documentation Organization with Backup
```bash
/mpm-organize
```
Interactive mode with automatic backup before changes.

### Consolidate Duplicate Docs Only
```bash
/mpm-organize --consolidate-only --dry-run
```
Preview which duplicate documentation files would be merged.

### Identify Stale Documentation
```bash
/mpm-organize --prune-only --dry-run
```
See which outdated documentation files would be removed or archived.

### Triage Documentation by Category
```bash
/mpm-organize --triage-only --verbose
```
Categorize documentation into research/user/developer without moving files.

### Full Organization Without Pruning
```bash
/mpm-organize --no-prune
```
Organize and consolidate docs but keep all existing files.

### Save Organization Report
```bash
/mpm-organize --report /tmp/docs-organize-report.md
```
Save detailed documentation organization report to file for review.

## Implementation

This slash command delegates to the **Project Organizer agent** (`project-organizer`), which performs intelligent documentation organization based on detected patterns and content analysis.

The agent receives the command options as context and then:
1. Scans for documentation files (.md, .rst, .txt)
2. Detects existing documentation structure patterns
3. Analyzes content to categorize by type (research/user/developer)
4. Identifies duplicate and stale documentation
5. Creates safe reorganization plan
6. Executes file moves with git integration (preserves history)
7. Generates detailed organization report

When you invoke `/mpm-organize [options]`, Claude MPM:
- Passes the options to the Project Organizer agent as task context
- The agent executes the documentation organization workflow
- Results are returned to you through the agent's structured output

**Important**: This command explicitly filters to documentation files only and never touches source code, configuration, tests, or build artifacts.

## Expected Output

### Dry Run Mode
```
🔍 Analyzing documentation structure...
✓ Detected existing pattern: docs/guides/ and docs/reference/
✓ Found 23 documentation files
✓ Identified 3 duplicate READMEs
✓ Found 5 stale documentation files

📁 Proposed Changes:

  Consolidate:
    → Merge README_OLD.md + README_BACKUP.md → docs/user/README.md
    → Merge architecture-v1.md + architecture-v2.md → docs/developer/architecture/decisions.md

  Prune:
    ✂ Remove TODO_2023.md (last modified 18 months ago)
    ✂ Archive deprecated-api.md → docs/archive/
    ✂ Remove empty placeholder.md

  Organize:
    docs/research/
      ← spike-oauth.md (from root)
      ← performance-analysis.md (from root)

    docs/user/guides/
      ← getting-started.md (from root)
      ← installation.md (from docs/)

    docs/developer/api/
      ← api-reference.md (from root)

📊 Summary:
  - 8 documentation files to move
  - 4 files to consolidate (2 merged files)
  - 5 files to prune (3 removed, 2 archived)
  - 0 code files touched

Run without --dry-run to apply changes.
```

### Actual Organization
```
🔍 Analyzing documentation structure...
✓ Detected existing pattern: docs/guides/ and docs/reference/
✓ Created backup: backup_docs_20250102_143022.tar.gz

📁 Organizing documentation...
  ✓ Consolidated README_OLD.md + README_BACKUP.md → docs/user/README.md
  ✓ Moved spike-oauth.md → docs/research/
  ✓ Moved getting-started.md → docs/user/guides/
  ✓ Pruned TODO_2023.md (stale)
  ✓ Archived deprecated-api.md

✅ Documentation organization complete!

📊 Report saved to: /tmp/docs-organization-report.md
```

## Safety Guarantees

- **Documentation Backup**: Backup of all documentation files before changes (unless --no-backup)
- **Git Integration**: Uses `git mv` to preserve file history for tracked files
- **Dry Run Available**: Preview all changes before applying
- **Code Never Touched**: Source code, configs, tests, and builds are explicitly excluded
- **Rollback Support**: Backup enables full rollback if needed
- **Conservative Pruning**: Stale files are archived rather than deleted when in doubt

## When to Use This Command

Use `/mpm-organize` when:
- Documentation has become scattered or disorganized
- You have duplicate README files or guides
- Documentation is outdated and needs cleanup
- Starting a new project and establishing docs structure
- Before a major release (clean up docs)
- When onboarding new team members (clear documentation)
- After accumulating research notes and spikes

## Best Practices

1. **Always Start with Dry Run**: Use `--dry-run` first to preview documentation changes
2. **Commit First**: Commit your work before organizing (or use --force)
3. **Review Proposed Consolidations**: Check merged files to ensure no information loss
4. **Verify Pruning Decisions**: Review stale files before removal, some may still be valuable
5. **Update Links**: After reorganization, check that internal documentation links still work
6. **Document New Structure**: Update README or docs index to reflect new organization

## Notes

- This slash command delegates to the **Project Organizer agent** (`project-organizer`)
- The agent performs intelligent documentation organization based on content analysis
- **Only touches documentation files**: .md, .rst, .txt documentation files
- **Never modifies**: Source code, tests, configs, or build artifacts
- Integrates with git to preserve file history
- Creates comprehensive reports for audit trails
- Can be run repeatedly safely (idempotent)
- Detects existing documentation patterns and respects them
- Falls back to standard docs structure if no pattern detected

## What Gets Organized

**Documentation files that ARE organized:**
- Markdown files (*.md)
- reStructuredText files (*.rst)
- Text documentation (*.txt in docs/ or with doc-like names)
- README files in various locations
- Guide and tutorial files
- Architecture and design documents

**Files that are NEVER touched:**
- Source code (.py, .js, .ts, .java, .go, .rs, etc.)
- Configuration files (.json, .yaml, .toml, .ini, etc.)
- Test files (*_test.*, test_*.*, *.test.*, *.spec.*)
- Package files (package.json, pyproject.toml, Cargo.toml, etc.)
- Build artifacts (dist/, build/, target/, node_modules/, etc.)
- Git files (.git/, .gitignore, .gitattributes)
- CI/CD files (.github/, .gitlab-ci.yml, etc.)

## Related Commands

- `/mpm-init`: Initialize or update project documentation and structure
- `/mpm-doctor`: Diagnose project health and issues (includes documentation checks)
- `/mpm-status`: Check current project state
