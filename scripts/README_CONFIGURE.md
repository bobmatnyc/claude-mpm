# Configure Command Test Scripts

This directory contains test and demo scripts for the `claude-mpm configure` command.

## Test Scripts

### test_configure.py
Basic functionality tests for the configure command:
- Help display
- List agents (non-interactive)
- Enable/disable agents
- Version information
- Export/import configuration

Usage:
```bash
python scripts/test_configure.py
```

### test_configure_interactive.py
Interactive TUI testing script. Launches the interactive interface for manual testing.

Usage:
```bash
python scripts/test_configure_interactive.py
```

### demo_configure.sh
Comprehensive demo script showing all configure command capabilities.

Usage:
```bash
bash scripts/demo_configure.sh
```

## Quick Test Commands

Test individual features:

```bash
# Help
claude-mpm configure --help

# List agents
claude-mpm configure --list-agents

# Enable/disable agents
claude-mpm configure --enable-agent engineer
claude-mpm configure --disable-agent designer

# Export/import
claude-mpm configure --export-config config.json
claude-mpm configure --import-config config.json

# Version info
claude-mpm configure --version-info

# Interactive TUI
claude-mpm configure
```