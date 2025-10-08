# /mpm-organize

Organize your project files into proper directories using intelligent pattern detection and framework-aware structure management.

## Usage

```
/mpm-organize                       # Interactive mode with preview
/mpm-organize --dry-run             # Preview changes without applying
/mpm-organize --force               # Proceed even with uncommitted changes
/mpm-organize --no-backup           # Skip backup creation (not recommended)
```

## Description

This slash command delegates to the **Project Organizer agent** to perform thorough project housekeeping. The agent analyzes your project structure, detects existing patterns and framework conventions, then organizes files into proper directories following best practices.

**Smart Organization**: The agent follows the official [Project Organization Standard](../../../docs/reference/PROJECT_ORGANIZATION.md), which defines comprehensive organization rules for Claude MPM projects. It also checks CLAUDE.md for project-specific guidelines and respects framework-specific conventions.

**Standard Documentation**: After organizing, this command ensures the organization standard is documented and accessible at `docs/reference/PROJECT_ORGANIZATION.md` with proper linking from CLAUDE.md.

## Features

- **📁 Intelligent Pattern Detection**: Analyzes existing directory structure and naming conventions
- **🎯 Framework-Aware**: Respects Next.js, React, Django, Rails, and other framework patterns
- **🔍 CLAUDE.md Integration**: Follows project-specific guidelines when available
- **✅ Safe Operations**: Uses `git mv` for tracked files to preserve history
- **💾 Automatic Backups**: Creates backups before major reorganizations
- **🔄 Import Path Updates**: Updates import statements after file moves
- **📊 Organization Report**: Detailed summary of changes and recommendations

## Options

### Safety Options
- `--dry-run`: Preview all changes without making them (recommended first run)
- `--no-backup`: Skip backup creation before reorganization (not recommended)
- `--force`: Proceed even with uncommitted changes (use with caution)

### Organization Options
- `--docs-only`: Only organize documentation files
- `--tests-only`: Only organize test files
- `--scripts-only`: Only organize script files
- `--skip-imports`: Don't update import paths after moves

### Output Options
- `--verbose`: Show detailed analysis and reasoning
- `--quiet`: Minimal output, errors only
- `--report [path]`: Save organization report to file

## What This Command Does

### 1. Organization Standard Verification
- Ensures `docs/reference/PROJECT_ORGANIZATION.md` exists and is current
- Creates or updates the standard if needed
- Links the standard from CLAUDE.md for easy reference

### 2. CLAUDE.md Analysis
- Checks for existing organization guidelines
- Extracts project-specific rules and conventions
- Identifies priority areas for organization

### 3. Project Structure Detection
- Scans directory hierarchy and patterns
- Identifies naming conventions (camelCase, kebab-case, snake_case)
- Maps current file type locations
- Detects framework-specific conventions (Next.js, Django, Rails, etc.)
- Determines organization type (feature/type/domain-based)

### 4. File Organization Strategy

The agent organizes files into standard directories per [PROJECT_ORGANIZATION.md](../../../docs/reference/PROJECT_ORGANIZATION.md):

```
docs/           # All documentation files (*.md, guides, architecture)
tests/          # All test files and test utilities
tmp/            # Temporary and ephemeral files
scripts/        # Ad-hoc scripts and utilities
src/            # Source code following framework conventions
.claude/        # Claude MPM configuration and agents
```

### 5. Framework-Specific Handling

**Next.js Projects**:
- Respects `pages/`, `app/`, `public/`, API routes
- Organizes components by feature or domain
- Maintains Next.js conventions

**Django Projects**:
- Maintains app structure
- Organizes migrations, templates, static files
- Preserves Django conventions

**React Projects**:
- Organizes components, hooks, utils
- Maintains component hierarchy
- Groups related files

**Other Frameworks**:
- Detects and respects framework conventions
- Applies appropriate organizational patterns

### 6. Safe File Movement

For each file to be moved:
1. Analyzes file purpose and dependencies
2. Determines optimal location based on patterns
3. Uses `git mv` for version-controlled files
4. Updates import paths in affected files
5. Validates build still works

### 7. Backup Creation

Before major reorganization:
```bash
backup_YYYYMMDD_HHMMSS.tar.gz  # Complete project backup
```

### 8. Import Path Updates

Automatically updates:
- Python imports (`from old.path import X` → `from new.path import X`)
- JavaScript/TypeScript imports (`import X from './old/path'` → `import X from './new/path'`)
- Relative path references
- Configuration file paths

### 9. Organization Report

Generates detailed report including:
- Files moved and their new locations
- Pattern analysis and detected conventions
- Import paths updated
- Recommendations for further improvements
- Violations of best practices (if any)

## Examples

### Preview Organization (Recommended First Run)
```bash
/mpm-organize --dry-run
```
Shows what would be changed without making any modifications.

### Full Organization with Backup
```bash
/mpm-organize
```
Interactive mode with automatic backup before changes.

### Force Organization (With Uncommitted Changes)
```bash
/mpm-organize --force --verbose
```
Organizes project even with uncommitted changes, shows detailed output.

### Organize Documentation Only
```bash
/mpm-organize --docs-only --dry-run
```
Preview how documentation files would be organized.

### Quick Organization Without Backup
```bash
/mpm-organize --no-backup
```
Skip backup creation for small changes (use with caution).

### Save Organization Report
```bash
/mpm-organize --report /tmp/organize-report.md
```
Save detailed report to file for review.

## Implementation

This slash command delegates to the **Project Organizer agent** (`project-organizer`), which performs intelligent file organization based on detected patterns and framework conventions.

The agent receives the command options as context and then:
1. Analyzes CLAUDE.md for organization guidelines
2. Detects project framework and patterns
3. Identifies misplaced files
4. Creates safe reorganization plan
5. Executes file moves with git integration
6. Updates import paths across codebase
7. Validates build integrity
8. Generates organization report

When you invoke `/mpm-organize [options]`, Claude MPM:
- Passes the options to the Project Organizer agent as task context
- The agent executes the organization workflow
- Results are returned to you through the agent's structured output

## Expected Output

### Dry Run Mode
```
🔍 Analyzing project structure...
✓ Detected framework: Next.js
✓ Organization pattern: Feature-based
✓ Found CLAUDE.md guidelines

📁 Proposed Changes:

  docs/
    ← README_OLD.md (from root)
    ← architecture-notes.txt (from root)

  tests/
    ← test_helper.py (from src/)
    ← api.test.js (from src/api/)

  tmp/
    ← debug_output.log (from root)
    ← scratch.py (from root)

  scripts/
    ← migrate.sh (from root)
    ← deploy_helper.py (from root)

📊 Summary:
  - 8 files to move
  - 12 import paths to update
  - 0 conflicts detected

Run without --dry-run to apply changes.
```

### Actual Organization
```
🔍 Analyzing project structure...
✓ Detected framework: Next.js
✓ Organization pattern: Feature-based
✓ Created backup: backup_20250102_143022.tar.gz

📁 Organizing files...
  ✓ Moved README_OLD.md → docs/
  ✓ Moved architecture-notes.txt → docs/
  ✓ Updated 5 import statements

✅ Organization complete!

📊 Report saved to: /tmp/organization-report.md
```

## Safety Guarantees

- **Backup Created**: Full project backup before changes (unless --no-backup)
- **Git Integration**: Uses `git mv` to preserve file history
- **Dry Run Available**: Preview all changes before applying
- **Import Updates**: Automatically fixes broken imports
- **Build Validation**: Verifies build still works after changes
- **Rollback Support**: Backup enables full rollback if needed

## When to Use This Command

Use `/mpm-organize` when:
- Starting a new project and establishing structure
- Project has accumulated misplaced files
- After major feature additions
- Before major refactoring
- When onboarding new team members
- To enforce organization standards

## Best Practices

1. **Always Start with Dry Run**: Use `--dry-run` first to preview changes
2. **Commit First**: Commit your work before organizing (or use --force)
3. **Review CLAUDE.md**: Ensure guidelines are current before organizing
4. **Test After**: Run tests after organization to verify nothing broke
5. **Update Documentation**: Document any new organizational patterns

## Notes

- This slash command delegates to the **Project Organizer agent** (`project-organizer`)
- The agent performs intelligent file placement based on learned patterns
- Respects framework-specific conventions automatically
- Integrates with git to preserve file history
- Updates import paths to prevent build breakage
- Creates comprehensive reports for audit trails
- Can be run repeatedly safely (idempotent)
- Follows guidelines in CLAUDE.md when available
- Falls back to framework conventions and best practices

## Related Documentation

- **[Project Organization Standard](../../../docs/reference/PROJECT_ORGANIZATION.md)**: Comprehensive organization rules and guidelines
- **[Project Structure](../../../docs/developer/STRUCTURE.md)**: Authoritative file organization reference
- **[CLAUDE.md](../../../CLAUDE.md)**: Development guidelines with organization quick reference

## Related Commands

- `/mpm-init`: Initialize or update project documentation and structure
- `/mpm-doctor`: Diagnose project health and issues
- `/mpm-status`: Check current project state
- `/mpm-config`: Configure organization rules and preferences
