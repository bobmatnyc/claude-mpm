# Tools Directory

This directory contains utility scripts and tools that are not part of the main packaged codebase but are useful for development, maintenance, and operations.

## Purpose

The `/tools` directory is designed to hold:

- **Development utilities**: Scripts for code analysis, migration, and maintenance
- **Build and deployment helpers**: Tools for packaging, releasing, and deployment
- **Administrative scripts**: Database migrations, cleanup utilities, monitoring tools
- **One-off utilities**: Scripts for specific tasks that don't belong in the main codebase

## Organization

Tools should be organized into subdirectories by category:

- `tools/dev/` - Development and maintenance utilities
- `tools/build/` - Build and deployment scripts
- `tools/admin/` - Administrative and operational tools
- `tools/migration/` - Data and code migration scripts

## Guidelines

1. **Non-packaged**: Tools in this directory are NOT included in the main package distribution
2. **Self-contained**: Each tool should be as self-contained as possible
3. **Documented**: Include docstrings and usage examples in each script
4. **Executable**: Make scripts executable with proper shebang lines
5. **Dependencies**: Document any external dependencies in comments or separate requirements files

## Examples

```bash
# Development utilities
tools/dev/analyze_imports.py
tools/dev/check_code_quality.py

# Build tools
tools/build/package_release.py
tools/build/update_version.py

# Administrative tools
tools/admin/cleanup_logs.py
tools/admin/backup_config.py
```

## Migration from /scripts

This directory replaces the misuse of `/scripts` for utility storage. As part of the structural reorganization:

### What was moved:
- **129 utility scripts** moved from `/scripts` to `/tools` subdirectories
- **42 test files** moved from `/scripts` to `/tests/integration`
- **Core application logic** (socketio_daemon.py) moved to proper service modules

### What remains in /scripts:
The `/scripts` directory now only contains legitimate build/deployment scripts:
- Build scripts (install.sh, deploy_local.sh, etc.)
- CI/CD pipeline scripts (pre-commit-build.sh, publish.sh)
- Test runner scripts (run_all_tests.sh, run_e2e_tests.sh)
- Package management files (package-lock.json, postinstall.js)

### Service Layer Cleanup:
- **Removed duplicate structure**: Eliminated `services/agent/` in favor of `services/agents/`
- **Consolidated functionality**: All agent services now in hierarchical `services/agents/` structure
- **Updated references**: All imports and documentation updated to reflect new structure
