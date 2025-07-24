# PathResolver Migration Guide

This guide shows how to replace duplicate path discovery logic with the new `PathResolver` utility.

## Import PathResolver

```python
from claude_mpm.utils.paths import PathResolver
# or for specific functions:
from claude_mpm.utils.paths import get_framework_root, get_project_root, find_file_upwards
```

## Common Migration Patterns

### 1. Finding Framework Root

**Before:**
```python
# In framework_loader.py
def _detect_framework_path(self) -> Optional[Path]:
    current_file = Path(__file__)
    if "claude-mpm" in str(current_file):
        for parent in current_file.parents:
            if parent.name == "claude-mpm":
                if (parent / "src" / "claude_mpm" / "agents").exists():
                    return parent
    # ... more complex logic
```

**After:**
```python
def _detect_framework_path(self) -> Optional[Path]:
    try:
        return PathResolver.get_framework_root()
    except FileNotFoundError:
        self.logger.warning("Framework not found")
        return None
```

### 2. Finding Agents Directory

**Before:**
```python
# In agent_loader.py
def _get_framework_agent_roles_dir() -> Path:
    try:
        import claude_pm
        package_path = Path(claude_pm.__file__).parent
        # Complex logic for installed vs dev mode
        # ...
    except:
        pass
    # Fallback logic
```

**After:**
```python
def _get_framework_agent_roles_dir() -> Path:
    agents_dir = PathResolver.get_agents_dir()
    # If you need the framework/agent-roles specifically:
    framework_root = PathResolver.get_framework_root()
    return framework_root / "framework" / "agent-roles"
```

### 3. Finding Project Root

**Before:**
```python
# Manual search for .git, pyproject.toml, etc.
current = Path.cwd()
while current != current.parent:
    if (current / '.git').exists():
        return current
    current = current.parent
```

**After:**
```python
project_root = PathResolver.get_project_root()
```

### 4. Finding .claude-pm Directory

**Before:**
```python
# In agent_management_service.py
self.project_dir = Path.cwd() / ".claude-pm" / "agents" / "project-specific"
```

**After:**
```python
claude_pm_dir = PathResolver.get_claude_pm_dir()
if claude_pm_dir:
    self.project_dir = claude_pm_dir / "agents" / "project-specific"
else:
    # Create if needed
    self.project_dir = PathResolver.ensure_directory(
        PathResolver.get_project_root() / ".claude-pm" / "agents" / "project-specific"
    )
```

### 5. Config Directory Management

**Before:**
```python
# Hardcoded paths
user_config = Path.home() / ".config" / "claude-pm"
project_config = Path.cwd() / ".claude-pm"
```

**After:**
```python
user_config = PathResolver.get_config_dir('user')
project_config = PathResolver.get_config_dir('project')
framework_config = PathResolver.get_config_dir('framework')
```

## Advanced Features

### File Search
```python
# Find file in parent directories
config_file = PathResolver.find_file_upwards('claude-pm.toml')

# Find all Python files in project
py_files = PathResolver.find_files_by_pattern('**/*.py')
```

### Directory Creation
```python
# Ensure directory exists (creates if needed)
cache_dir = PathResolver.ensure_directory(
    PathResolver.get_config_dir('user') / 'cache'
)
```

### Relative Path Resolution
```python
# Get path relative to project root
src_file = PathResolver.get_relative_to_root('src/main.py', 'project')

# Get path relative to framework
agents_file = PathResolver.get_relative_to_root('agents/qa.md', 'framework')
```

## Performance Considerations

The PathResolver uses `@lru_cache` for all discovery methods, so repeated calls are very fast:

```python
# First call does the discovery
root1 = PathResolver.get_framework_root()  # ~1ms

# Subsequent calls use cache
root2 = PathResolver.get_framework_root()  # <0.01ms
```

To clear the cache (useful in tests or when file system changes):

```python
PathResolver.clear_cache()
```

## Benefits

1. **Consistency**: All path discovery uses the same logic
2. **Performance**: Built-in caching for repeated lookups
3. **Reliability**: Comprehensive error handling and edge cases
4. **Testability**: Easy to mock in tests
5. **Maintainability**: Single source of truth for path logic