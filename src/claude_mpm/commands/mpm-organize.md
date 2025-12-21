---
namespace: mpm/system
command: organize
aliases: [mpm-organize]
migration_target: /mpm/system:organize
category: system
description: Organize all project files including documentation, source code, tests, scripts, and configuration with intelligent consolidation and pruning
---
# /mpm-organize

Organize ALL project files into a clean, structured format with intelligent detection of existing patterns. Includes special handling for documentation consolidation, pruning, and triage into research/user/developer categories.

## Usage

```
/mpm-organize                       # Interactive mode with preview
/mpm-organize --dry-run             # Preview changes without applying
/mpm-organize --force               # Proceed even with uncommitted changes
/mpm-organize --no-backup           # Skip backup creation (not recommended)
/mpm-organize --docs-only           # Only organize documentation files
```

## Description

This slash command delegates to the **Project Organizer agent** to perform intelligent project organization across ALL file types. The agent analyzes your project structure, detects existing patterns, consolidates duplicates, removes stale content, and organizes everything into a clean, logical structure.

**Comprehensive Scope**: This command organizes ALL project files including:
- **Documentation** (.md, .rst, .txt) - consolidate, prune, triage into research/user/developer
- **Source code** - proper module structure and organization
- **Tests** - organized test suites
- **Scripts** - automation tools and utilities
- **Configuration** - project config files

**Smart Detection**: The agent first looks for existing organization patterns in your project (e.g., PROJECT_ORGANIZATION.md, CONTRIBUTING.md). If found, it respects and extends those patterns. If not found, it applies framework-appropriate defaults.

## Features

- **📁 Pattern Detection**: Analyzes existing project structure and detects organization conventions
- **🔄 Consolidation**: Merges duplicate or related files (especially documentation)
- **✂️ Pruning**: Identifies and removes outdated, stale, or redundant content
- **📋 Triage**: Categorizes documentation into research/user/developer directories
- **🏗️ Code Organization**: Ensures proper module structure and file placement
- **🧪 Test Organization**: Organizes test suites into proper directories
- **📜 Script Organization**: Moves scripts to dedicated scripts/ directory
- **✅ Safe Operations**: Uses `git mv` for tracked files to preserve history
- **💾 Automatic Backups**: Creates backups before major reorganizations
- **📊 Organization Report**: Detailed summary of changes and recommendations
- **🎯 Smart Scope**: Full project or documentation-only mode (--docs-only)

## Options

### Safety Options
- `--dry-run`: Preview all changes without making them (recommended first run)
- `--no-backup`: Skip backup creation before reorganization (not recommended)
- `--force`: Proceed even with uncommitted changes (use with caution)

### Scope Options
- `--docs-only`: Only organize documentation files (legacy behavior)
- `--code-only`: Only organize source code files
- `--tests-only`: Only organize test files
- `--scripts-only`: Only organize script files

### Organization Options
- `--consolidate-only`: Only consolidate duplicate files, skip reorganization
- `--prune-only`: Only identify and remove stale files
- `--triage-only`: Only categorize files without moving them
- `--no-prune`: Skip pruning phase (keep all existing files)

### Output Options
- `--verbose`: Show detailed analysis and reasoning
- `--quiet`: Minimal output, errors only
- `--report [path]`: Save organization report to file

## What This Command Does

### 1. Pattern Detection
- Scans existing project structure across all file types
- Identifies organization conventions (PROJECT_ORGANIZATION.md, CONTRIBUTING.md)
- Detects framework-specific patterns (Next.js, Django, Flask, etc.)
- Detects existing documentation organization
- Falls back to framework-appropriate defaults if no pattern found

### 2. Standard Project Structure

If no existing pattern is detected, organizes according to project type:

**Documentation** (all project types):
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

**Source Code** (framework-specific):
- Python: `src/package_name/` structure
- JavaScript/TypeScript: Framework conventions (Next.js, React, etc.)
- Other: Language-appropriate module structure

**Tests**: `tests/` with mirrored source structure

**Scripts**: `scripts/` for automation tools

**Configuration**: Root or `config/` depending on project size

### 3. File Consolidation

Identifies and merges duplicate/similar files:

**Documentation**:
- Duplicate README files
- Similar guide documents
- Redundant architecture notes
- Multiple versions of same doc
- Scattered meeting notes

**Code**:
- Duplicate utility functions
- Similar helper modules
- Redundant configuration files

### 4. Content Pruning

Removes or archives stale/obsolete content:

**Documentation**:
- Outdated documentation (last modified >6 months)
- Stale TODO lists and notes
- Obsolete architecture documents
- Deprecated API documentation
- Empty or placeholder files

**Code**:
- Commented-out code blocks
- Unused imports and dependencies
- Dead code (unreferenced functions/classes)

### 5. File Categorization & Triage

Categorizes and organizes files by purpose:

**Documentation**:
- **Research**: Analysis, spikes, investigations, experiments
- **User**: Guides, tutorials, FAQs, how-tos
- **Developer**: API docs, architecture, contributing guides

**Code**:
- Source code to proper module structure
- Tests to organized test suites
- Scripts to scripts/ directory
- Configuration to appropriate locations

### 6. Safe File Movement

For each file being organized:
1. Analyzes file type, content, and purpose
2. Determines optimal location based on detected patterns
3. Uses `git mv` for version-controlled files
4. Preserves git history
5. Creates backup before major changes
6. Validates move doesn't break imports or references

### 7. Backup Creation

Before reorganization:
```bash
backup_project_YYYYMMDD_HHMMSS.tar.gz  # Full project backup (or docs-only)
```

### 8. Protected Files (Never Moved)

These files remain in project root:
- `README.md`, `CHANGELOG.md`, `LICENSE.md`
- `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`
- `CLAUDE.md`, `CODE.md`, `DEVELOPER.md`
- Package files: `package.json`, `pyproject.toml`, `Cargo.toml`, etc.
- Build configs: `Makefile`, `Dockerfile`, `docker-compose.yml`
- Git files: `.gitignore`, `.gitattributes`
- Environment templates: `.env.example`, `.env.sample`

### 9. Files Excluded from Organization

Never touched:
- Build artifacts: `dist/`, `build/`, `node_modules/`, `__pycache__/`
- Version control: `.git/`, `.svn/`, `.hg/`
- Virtual environments: `venv/`, `.venv/`, `env/`
- IDE configs: `.vscode/`, `.idea/` (unless --config-only)

### 10. Organization Report

Generates detailed report including:
- All files moved with before/after locations
- Files consolidated (merged) with change summary
- Files pruned (removed or archived) with reasoning
- Pattern analysis and detected conventions
- Import/reference validation results
- Recommendations for further improvements

## Examples

### Preview Full Project Organization (Recommended First Run)
```bash
/mpm-organize --dry-run
```
Shows what changes would be made across ALL project files without applying them.

### Preview Documentation Organization Only
```bash
/mpm-organize --docs-only --dry-run
```
Shows what documentation changes would be made (legacy behavior).

### Full Project Organization with Backup
```bash
/mpm-organize
```
Interactive mode with automatic backup before organizing all project files.

### Organize Tests and Scripts Only
```bash
/mpm-organize --tests-only --scripts-only
```
Focus on organizing test files and scripts, leave everything else untouched.

### Consolidate Duplicate Files Only
```bash
/mpm-organize --consolidate-only --dry-run
```
Preview which duplicate files would be merged across the project.

### Identify Stale Files (All Types)
```bash
/mpm-organize --prune-only --dry-run
```
See which outdated files would be removed or archived.

### Triage Documentation by Category
```bash
/mpm-organize --docs-only --triage-only --verbose
```
Categorize documentation into research/user/developer without moving files.

### Full Organization Without Pruning
```bash
/mpm-organize --no-prune
```
Organize and consolidate all files but keep everything (no deletions).

### Save Organization Report
```bash
/mpm-organize --report /tmp/project-organize-report.md
```
Save detailed organization report to file for review.

## Implementation

This slash command delegates to the **Project Organizer agent** (`project-organizer`), which performs intelligent project organization based on detected patterns and content analysis across all file types.

The agent receives the command options as context and then:
1. **Scans** for all project files (or scope-specific with --docs-only, --tests-only, etc.)
2. **Detects** existing organization patterns (PROJECT_ORGANIZATION.md, CONTRIBUTING.md, framework conventions)
3. **Analyzes** file content, purpose, and relationships
4. **Categorizes** files by type and purpose (documentation by audience, code by module, tests by coverage)
5. **Identifies** duplicates, stale content, and misplaced files
6. **Validates** that moves won't break imports or references
7. **Creates** safe reorganization plan with detailed reasoning
8. **Executes** file moves with git integration (preserves history)
9. **Generates** comprehensive organization report

When you invoke `/mpm-organize [options]`, Claude MPM:
- Passes the options to the Project Organizer agent as task context
- The agent executes the comprehensive organization workflow
- Results are returned through structured output with detailed change log

**Scope Control**:
- Default: Organizes ALL project files (comprehensive)
- `--docs-only`: Only documentation files (legacy behavior)
- `--code-only`, `--tests-only`, `--scripts-only`: Specific file types

## Expected Output

### Dry Run Mode (Full Project)
```
🔍 Analyzing project structure...
✓ Detected PROJECT_ORGANIZATION.md - using project standards
✓ Found Python Flask project with standard structure
✓ Found 23 documentation files
✓ Found 15 misplaced test files
✓ Found 8 scripts in root directory
✓ Identified 3 duplicate READMEs
✓ Found 5 stale files

📁 Proposed Changes:

  Documentation:
    Consolidate:
      → Merge README_OLD.md + README_BACKUP.md → docs/user/README.md
      → Merge architecture-v1.md + architecture-v2.md → docs/developer/architecture/decisions.md

    Organize:
      docs/research/
        ← spike-oauth.md (from root)
        ← performance-analysis.md (from root)
      docs/user/guides/
        ← getting-started.md (from root)
        ← installation.md (from docs/)

    Prune:
      ✂ Remove TODO_2023.md (last modified 18 months ago)
      ✂ Archive deprecated-api.md → docs/_archive/

  Tests:
    tests/unit/
      ← test_auth.py (from root)
      ← test_utils.py (from src/)
    tests/integration/
      ← test_api_integration.py (from root)

  Scripts:
    scripts/
      ← deploy.sh (from root)
      ← run_tests.py (from root)
      ← backup_db.sh (from utils/)

  Source Code:
    src/myapp/utils/
      → Consolidate helpers.py + utility_functions.py → utils.py

📊 Summary:
  - 8 documentation files to move
  - 4 files to consolidate (2 merged)
  - 5 files to prune (3 removed, 2 archived)
  - 15 test files to organize
  - 8 scripts to move
  - 2 code files to consolidate

Run without --dry-run to apply changes.
```

### Dry Run Mode (Documentation Only)
```bash
/mpm-organize --docs-only --dry-run
```
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
    ✂ Archive deprecated-api.md → docs/_archive/
    ✂ Remove empty placeholder.md

  Organize:
    docs/research/
      ← spike-oauth.md (from root)
      ← performance-analysis.md (from root)
    docs/user/guides/
      ← getting-started.md (from root)
      ← installation.md (from docs/)

📊 Summary:
  - 8 documentation files to move
  - 4 files to consolidate (2 merged files)
  - 5 files to prune (3 removed, 2 archived)

Run without --dry-run to apply changes.
```

### Actual Organization
```
🔍 Analyzing project structure...
✓ Detected PROJECT_ORGANIZATION.md - using project standards
✓ Created backup: backup_project_20250102_143022.tar.gz

📁 Organizing project files...
  ✓ Consolidated README_OLD.md + README_BACKUP.md → docs/user/README.md
  ✓ Moved spike-oauth.md → docs/research/
  ✓ Moved test_auth.py → tests/unit/
  ✓ Moved deploy.sh → scripts/
  ✓ Consolidated helpers.py + utility_functions.py → src/myapp/utils/utils.py
  ✓ Pruned TODO_2023.md (stale)
  ✓ Archived deprecated-api.md

✅ Project organization complete!

📊 Report saved to: /tmp/project-organization-report.md
```

## Safety Guarantees

- **Full Project Backup**: Backup of all affected files before changes (unless --no-backup)
- **Git Integration**: Uses `git mv` to preserve file history for tracked files
- **Dry Run Available**: Preview all changes before applying (--dry-run)
- **Import Validation**: Validates that code moves won't break imports/references
- **Protected Files**: Critical root files never moved (README.md, package.json, etc.)
- **Rollback Support**: Backup enables full rollback if needed
- **Conservative Pruning**: Stale files are archived rather than deleted when in doubt
- **Scope Control**: Limit changes to specific file types (--docs-only, --tests-only, etc.)

## When to Use This Command

Use `/mpm-organize` when:
- **Project has grown organically** and structure has become messy
- **Test files are scattered** across the codebase
- **Scripts are in root** instead of scripts/ directory
- **Documentation is disorganized** with duplicates and stale content
- **Code has duplicated utilities** that should be consolidated
- **Starting a new project** and establishing clean structure
- **Before a major release** (clean up everything)
- **After a major refactor** (reorganize changed files)
- **When onboarding new team members** (clear, organized structure)
- **After accumulating research notes** and experimental code

## Best Practices

1. **Always Start with Dry Run**: Use `--dry-run` first to preview ALL changes
2. **Commit First**: Commit your work before organizing (or use --force, but not recommended)
3. **Start Small**: Use `--docs-only` first, then expand to full project organization
4. **Review Proposed Changes**: Carefully review consolidations and moves
5. **Verify Pruning Decisions**: Review stale files before removal, some may still be valuable
6. **Test After Organization**: Run tests after organizing to ensure imports still work
7. **Update Links**: Check that documentation links and imports still work
8. **Document Structure**: Update README or PROJECT_ORGANIZATION.md to reflect new structure
9. **Use Scope Flags**: Limit scope with `--docs-only`, `--tests-only`, etc. for focused changes
10. **Review Report**: Always check the organization report for detailed change log

## Notes

- This slash command delegates to the **Project Organizer agent** (`project-organizer`)
- The agent performs intelligent organization across **all project file types**
- **Default behavior**: Organizes ALL files (comprehensive project organization)
- **Legacy behavior**: Use `--docs-only` to only organize documentation (old default)
- Integrates with git to preserve file history
- Creates comprehensive reports for audit trails
- Can be run repeatedly safely (idempotent within scope)
- Detects existing patterns and respects them (PROJECT_ORGANIZATION.md, CONTRIBUTING.md)
- Falls back to framework-appropriate defaults if no pattern detected

## What Gets Organized (by Default)

**ALL project files by default**, including:

**Documentation**:
- Markdown files (*.md)
- reStructuredText files (*.rst)
- Text documentation (*.txt in docs/ or with doc-like names)
- README files in various locations (except root README.md)
- Guide and tutorial files
- Architecture and design documents

**Source Code**:
- Python files (*.py) - organized into proper module structure
- JavaScript/TypeScript (*.js, *.ts, *.jsx, *.tsx)
- Other language source files
- Utilities and helper modules

**Tests**:
- Unit tests (*_test.*, test_*.*)
- Integration tests
- Test fixtures and utilities

**Scripts**:
- Shell scripts (*.sh, *.bash)
- Python scripts (identified by patterns)
- Build and deployment scripts

**Configuration** (with caution):
- Project-specific configs (not package.json, pyproject.toml, etc.)
- Environment config templates

**Files NEVER touched (protected)**:
- Root README.md, CHANGELOG.md, LICENSE.md
- Package files (package.json, pyproject.toml, Cargo.toml, etc.)
- Build artifacts (dist/, build/, target/, node_modules/, __pycache__/)
- Git files (.git/, .gitignore, .gitattributes)
- CI/CD files (.github/, .gitlab-ci.yml, etc.)
- Virtual environments (venv/, .venv/, env/)

## Related Commands

- `/mpm-init`: Initialize or update project documentation and structure
- `/mpm-doctor`: Diagnose project health and issues (includes documentation checks)
- `/mpm-status`: Check current project state
