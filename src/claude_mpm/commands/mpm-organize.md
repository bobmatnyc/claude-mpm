---
namespace: mpm/system
command: organize
aliases: [mpm-organize]
migration_target: /mpm/system:organize
category: system
description: Organize project files with intelligent consolidation
---
# /mpm-organize

Organize ALL project files with intelligent detection, consolidation, and pruning.

## Usage
```
/mpm-organize [--dry-run] [--force] [options]
```

**Delegates to Project Organizer agent** for comprehensive file organization.

## Scope

**Default:** Organizes ALL project files
- Documentation (.md, .rst, .txt)
- Source code (proper module structure)
- Tests (organized test suites)
- Scripts (scripts/ directory)
- Configuration (appropriate locations)

**Protected files (never moved):** README.md, package.json, pyproject.toml, Makefile, .gitignore, etc.

## Key Options

**Safety:**
- `--dry-run`: Preview without changes (recommended first run)
- `--force`: Proceed with uncommitted changes
- `--no-backup`: Skip backup (not recommended)

**Scope:**
- `--docs-only`: Only documentation (legacy behavior)
- `--code-only` / `--tests-only` / `--scripts-only`: Specific file types

**Operations:**
- `--consolidate-only`: Merge duplicates only
- `--prune-only`: Remove stale files only
- `--no-prune`: Keep all files (no deletions)

## What It Does

1. **Pattern Detection:** Scans for existing organization (PROJECT_ORGANIZATION.md, framework conventions)
2. **Consolidation:** Merges duplicates (READMEs, guides, utilities)
3. **Pruning:** Archives/removes stale content (>6 months old, empty files)
4. **Categorization:** Sorts docs into research/user/developer
5. **Safe Movement:** Uses `git mv` to preserve history
6. **Backup:** Creates backup_project_YYYYMMDD_HHMMSS.tar.gz

## Standard Structure

```
docs/
├── research/        # Spikes, analysis, notes
├── user/            # Guides, tutorials, FAQs
└── developer/       # API docs, architecture, contributing

src/<package>/       # Proper module structure
tests/               # Mirrored source structure
scripts/             # Automation tools
config/              # Configuration (if needed)
```

## Examples

```bash
# Preview changes (recommended first)
/mpm-organize --dry-run

# Organize everything with backup
/mpm-organize

# Documentation only
/mpm-organize --docs-only --dry-run

# Consolidate without pruning
/mpm-organize --consolidate-only --no-prune

# Save report
/mpm-organize --report /tmp/organize-report.md
```

## Expected Output

```
🔍 Analyzing project structure...
✓ Detected PROJECT_ORGANIZATION.md - using project standards
✓ Found 23 documentation files, 15 test files, 8 scripts

📁 Proposed Changes:

  Consolidate:
    → Merge README_OLD.md + README_BACKUP.md → docs/user/README.md

  Organize:
    docs/research/ ← spike-oauth.md (from root)
    tests/unit/ ← test_auth.py (from root)
    scripts/ ← deploy.sh (from root)

  Prune:
    ✂ Remove TODO_2023.md (stale 18 months)

📊 Summary: 8 to move, 2 to merge, 3 to prune
```

## Safety Features

- Full project backup before changes
- Git integration (preserves history)
- Import validation (ensures moves won't break code)
- Protected files never touched
- Conservative pruning (archive when unsure)

See docs/commands/organize.md for full documentation.
