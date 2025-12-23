# Agent Repository Sync Script

## Overview

The `push_to_agents_repo.sh` script syncs agent template files from the main `claude-mpm` repository to the separate `claude-mpm-agents` repository.

## Purpose

This script automates the process of keeping agent templates synchronized between:
- **Source**: `bobmatnyc/claude-mpm` (main development repository)
- **Destination**: `bobmatnyc/claude-mpm-agents` (agent templates repository)

## File Mappings

The script syncs the following files:

| Source File | Destination File |
|------------|------------------|
| `src/claude_mpm/agents/BASE_AGENT.md` | `agents/BASE-AGENT.md` |
| `src/claude_mpm/agents/PM_INSTRUCTIONS.md` | `templates/PM-INSTRUCTIONS.md` |
| `src/claude_mpm/agents/BASE_ENGINEER.md` | `templates/BASE-ENGINEER.md` |
| `src/claude_mpm/agents/CLAUDE_MPM_TEACHER_OUTPUT_STYLE.md` | `templates/CLAUDE_MPM_TEACHER_OUTPUT_STYLE.md` |

## Usage

### Basic Usage

```bash
# Sync files using version from pyproject.toml
./scripts/push_to_agents_repo.sh

# Sync files with specific version
./scripts/push_to_agents_repo.sh 5.4.23
```

### Options

- `--dry-run`: Preview changes without committing or pushing
- `--yes` or `-y`: Skip confirmation prompt (auto-confirm)
- `--repo-path <path>`: Use existing local clone instead of creating temp clone

### Examples

```bash
# Preview changes without pushing
./scripts/push_to_agents_repo.sh --dry-run

# Sync with auto-confirmation (useful for CI/CD)
./scripts/push_to_agents_repo.sh --yes

# Sync specific version with dry-run
./scripts/push_to_agents_repo.sh 5.4.24 --dry-run

# Use existing local repository clone
./scripts/push_to_agents_repo.sh --repo-path /path/to/claude-mpm-agents
```

## Features

### 1. Version Management
- Automatically extracts version from `pyproject.toml`
- Validates version format (X.Y.Z)
- Allows manual version override

### 2. Safety Features
- Verifies all source files exist before proceeding
- Shows git diff of changes before committing
- Requires user confirmation (unless `--yes` flag used)
- Dry-run mode for safe preview
- Automatic cleanup of temporary directories

### 3. Error Handling
- Validates source files existence
- Checks git repository validity
- Provides clear error messages
- Proper exit codes for scripting

### 4. Output
- Color-coded messages (INFO, SUCCESS, WARNING, ERROR)
- Progress indicators for each step
- Full git diff display
- Commit message preview

## Workflow

1. **Validation Phase**
   - Extract/validate version
   - Verify all source files exist

2. **Repository Setup**
   - Clone agents repository to temp location
   - Or use existing repository if `--repo-path` provided

3. **File Sync**
   - Copy files to destination paths
   - Track which files changed

4. **Review Phase**
   - Display git diff
   - Show git status
   - Exit if dry-run mode

5. **Commit Phase**
   - Prompt for confirmation (unless `--yes`)
   - Stage all changes
   - Create descriptive commit message
   - Push to remote

6. **Cleanup**
   - Remove temporary directories
   - Display success message

## Commit Message Format

```
Sync agent files from claude-mpm v{VERSION}

Updated files:
- agents/BASE-AGENT.md
- templates/PM-INSTRUCTIONS.md
- templates/BASE-ENGINEER.md
- templates/CLAUDE_MPM_TEACHER_OUTPUT_STYLE.md

Source: https://github.com/bobmatnyc/claude-mpm/releases/tag/v{VERSION}
```

## Requirements

- Bash 3.2+ (compatible with macOS default bash)
- Git installed and configured
- Write access to `bobmatnyc/claude-mpm-agents` repository
- Network connectivity to GitHub

## Compatibility

- **macOS**: Tested on macOS with Bash 3.2
- **Linux**: Compatible with Bash 3.2+
- **Windows**: Should work with Git Bash or WSL

## Typical Use Cases

### 1. Release Process
After bumping version and before creating a release:
```bash
./scripts/push_to_agents_repo.sh --yes
```

### 2. Development Testing
Test changes before committing:
```bash
./scripts/push_to_agents_repo.sh --dry-run
```

### 3. Manual Sync
Sync specific version:
```bash
./scripts/push_to_agents_repo.sh 5.4.23
```

### 4. CI/CD Pipeline
Automated sync in GitHub Actions:
```bash
./scripts/push_to_agents_repo.sh --yes
```

## Troubleshooting

### Permission Denied
```bash
chmod +x scripts/push_to_agents_repo.sh
```

### Git Authentication
Ensure Git credentials are configured:
```bash
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
```

### Version Not Found
Check `pyproject.toml` has correct format:
```toml
[project]
version = "5.4.23"
```

## Integration with Release Process

This script should be run as part of the release process:

1. Update version in `pyproject.toml`
2. Update agent template files in `src/claude_mpm/agents/`
3. Run this sync script: `./scripts/push_to_agents_repo.sh --yes`
4. Create release tag in main repository
5. Publish release

## Security Considerations

- Script uses HTTPS for git operations
- No credentials stored in script
- Relies on system git authentication
- Automatic cleanup prevents credential leaks

## Maintenance

When adding new agent files:
1. Add source path to `SOURCE_FILES` array
2. Add destination path to `DEST_FILES` array
3. Test with `--dry-run` flag

## Exit Codes

- `0`: Success
- `1`: Error (invalid arguments, missing files, git errors, etc.)

## Support

For issues or questions:
- GitHub Issues: https://github.com/bobmatnyc/claude-mpm/issues
- Agents Repo: https://github.com/bobmatnyc/claude-mpm-agents
