# Centralized Path Management System

## Overview

Claude-MPM now uses a centralized path management system to eliminate fragile `Path(__file__).parent.parent.parent` patterns throughout the codebase. This provides a consistent, reliable way to access project paths.

## Quick Start

### Basic Usage

```python
from claude_mpm.config.paths import paths

# Access common paths
project_root = paths.project_root
agents_dir = paths.agents_dir
config_file = paths.config_dir / "some_config.yaml"

# Get project version
version = paths.get_version()

# Ensure src is in Python path
paths.ensure_in_path()
```

### Convenience Functions

```python
from claude_mpm.config.paths import (
    get_project_root,
    get_src_dir,
    get_claude_mpm_dir,
    get_agents_dir,
    get_services_dir,
    get_config_dir,
    get_version,
    ensure_src_in_path
)

# Direct function calls
project_root = get_project_root()
version = get_version()
ensure_src_in_path()
```

## Migration Guide

### Before (Fragile Pattern)

```python
# Old pattern - fragile and error-prone
from pathlib import Path

# 4-parent traversal
project_root = Path(__file__).parent.parent.parent.parent
version_file = project_root / "VERSION"

# Adding src to path
import sys
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

# Finding agents directory
agents_dir = Path(__file__).parent.parent.parent.parent / "src" / "claude_mpm" / "agents"
```

### After (Centralized Paths)

```python
# New pattern - clean and reliable
from claude_mpm.config.paths import paths

# Direct property access
project_root = paths.project_root
version_file = paths.version_file

# Automatic path management
paths.ensure_in_path()

# Clean directory access
agents_dir = paths.agents_dir
```

## Available Properties

### Project Structure
- `paths.project_root` - Project root directory
- `paths.src_dir` - Source directory (/src)
- `paths.claude_mpm_dir` - Main package directory (/src/claude_mpm)

### Core Directories
- `paths.agents_dir` - Agent templates and configurations
- `paths.services_dir` - Service implementations
- `paths.hooks_dir` - Hook system components
- `paths.config_dir` - Configuration files
- `paths.cli_dir` - CLI components
- `paths.core_dir` - Core framework code
- `paths.schemas_dir` - JSON schemas

### Project Directories
- `paths.scripts_dir` - Script files
- `paths.tests_dir` - Test files
- `paths.docs_dir` - Documentation
- `paths.logs_dir` - Log files (auto-created)
- `paths.temp_dir` - Temporary files (auto-created)
- `paths.claude_mpm_dir_hidden` - Hidden .claude-mpm directory (auto-created)

### Special Files
- `paths.version_file` - VERSION file
- `paths.pyproject_file` - pyproject.toml
- `paths.package_json_file` - package.json
- `paths.claude_md_file` - CLAUDE.md

## Advanced Features

### Path Resolution

```python
# Get path relative to project root
relative = paths.relative_to_project("/absolute/path/to/file")

# Resolve config file (checks multiple locations)
config_path = paths.resolve_config_path("my_config.yaml")
```

### Version Management

```python
# Get version from multiple sources (VERSION file, package metadata, etc.)
version = paths.get_version()
```

### Singleton Pattern

The `ClaudeMPMPaths` class uses a singleton pattern for efficiency:

```python
from claude_mpm.config.paths import paths, ClaudeMPMPaths

# Both refer to the same instance
paths1 = paths
paths2 = ClaudeMPMPaths()
assert paths1 is paths2  # True
```

## Migration Examples

### Example 1: Agent Deployment Service

**Before:**
```python
# From /services/agents/deployment/ - 4 levels up
claude_mpm_root = Path(__file__).parent.parent.parent.parent
self.templates_dir = claude_mpm_root / "agents" / "templates"
self.base_agent_path = claude_mpm_root / "agents" / "base_agent.json"
```

**After:**
```python
from claude_mpm.config.paths import paths

self.templates_dir = paths.agents_dir / "templates"
self.base_agent_path = paths.agents_dir / "base_agent.json"
```

### Example 2: Version Detection

**Before:**
```python
version_file = Path(__file__).parent.parent.parent.parent / "VERSION"
if version_file.exists():
    version = version_file.read_text().strip()
```

**After:**
```python
from claude_mpm.config.paths import paths

if paths.version_file.exists():
    version = paths.version_file.read_text().strip()
# Or simply:
version = paths.get_version()
```

### Example 3: Script Path Setup

**Before:**
```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
```

**After:**
```python
from claude_mpm.config.paths import paths
paths.ensure_in_path()
```

## Best Practices

1. **Import at module level**: Import paths at the top of your module for clarity
2. **Use properties directly**: Access paths via properties rather than constructing paths
3. **Leverage convenience functions**: Use the provided functions for common operations
4. **Avoid hardcoding**: Let the path manager handle all path resolution
5. **Use relative_to_project**: When displaying paths to users, make them relative

## Testing

Test the path management system:

```bash
# Run the test script
python scripts/test_path_management.py

# Verify in Python REPL
python -c "from claude_mpm.config.paths import paths; print(paths)"
```

## Troubleshooting

### Import Errors

If you get import errors:

```python
# Fallback pattern for scripts
try:
    from claude_mpm.config.paths import paths
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
    from claude_mpm.config.paths import paths
```

### Project Root Detection

The system uses multiple strategies to detect the project root:
1. Looks for `pyproject.toml`, `setup.py`, `VERSION`, or `.git`
2. Falls back to calculated path from module location
3. Logs warnings if fallback is used

## Performance

The path management system is optimized for performance:
- Singleton pattern ensures single instance
- Cached properties for frequently accessed paths
- Lazy initialization for optional directories
- Minimal overhead compared to direct path construction

## Future Enhancements

Potential future improvements:
- Configuration file for custom path overrides
- Environment variable support for path customization
- Path validation and existence checking
- Integration with package installation paths
- Support for multiple project layouts