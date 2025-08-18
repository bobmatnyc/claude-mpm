# Experimental Features Architecture

## Overview

This document describes the architecture for experimental features in Claude MPM. The design ensures clean separation between stable and experimental code, allowing features to be tested and refined before becoming part of the stable codebase.

## Architecture Principles

### 1. Complete Separation

```
┌─────────────────────────────────────────────────────────┐
│                    Stable Code                          │
├─────────────────────────────────────────────────────────┤
│  Core Services                                          │
│  ├── No dependencies on experimental code               │
│  ├── No imports of experimental modules                 │
│  └── Works independently                                │
│                                                          │
│  Standard Commands                                      │
│  ├── Use stable services directly                       │
│  ├── No awareness of experimental features              │
│  └── Completely stable                                  │
└─────────────────────────────────────────────────────────┘
                            ↑
                   No direct dependency
                            ↓
┌─────────────────────────────────────────────────────────┐
│                  Experimental Code                      │
├─────────────────────────────────────────────────────────┤
│  Experimental Services                                  │
│  ├── Extend or enhance stable services                  │
│  ├── Add new capabilities                               │
│  └── Do not modify base classes                         │
│                                                          │
│  Experimental Commands                                  │
│  ├── Use experimental services                          │
│  ├── Show experimental warnings                         │
│  └── Completely isolated                                │
└─────────────────────────────────────────────────────────┘
```

### 2. Lazy Loading

Experimental code is only loaded when explicitly requested:

```python
# In cli/__init__.py
def _execute_command(command: str, args) -> int:
    # Handle experimental commands separately with lazy import
    if command in EXPERIMENTAL_COMMANDS:
        # Lazy import to avoid loading experimental code unless needed
        if command == 'mcp':
            from .commands.mcp import execute_mcp
            return execute_mcp(args)
    
    # Stable commands use direct imports
    command_map = {
        CLICommands.RUN.value: run_session,
        # ... other stable commands
    }
```

### 3. Feature Flags

All experimental features are controlled through a centralized configuration:

```python
# config/experimental_features.py
class ExperimentalFeatures:
    DEFAULTS = {
        'enable_mcp_gateway': False,  # Disabled by default
        'show_experimental_warnings': True,
        'require_experimental_acceptance': True,
    }
```

### 4. User Warnings

Experimental features always show clear warnings unless explicitly suppressed:

```bash
# First time use shows warning
$ claude-mpm mcp

⚠️  EXPERIMENTAL FEATURE: MCP Gateway is in beta.
   This feature may change or have issues. Use with caution in production.
   Report issues at: https://github.com/bluescreen10/claude-mpm/issues

Continue? [y/N]: 

# Suppress warning with flag
$ claude-mpm mcp --accept-experimental
```

## Implementation Guidelines

### Adding New Experimental Features

1. **Create Separate Command Module**
   ```
   src/claude_mpm/cli/commands/my_experimental.py
   ```

2. **Add Feature Flag**
   ```python
   # In experimental_features.py
   DEFAULTS = {
       'enable_my_feature': False,
       # ...
   }
   ```

3. **Implement Warning System**
   ```python
   def execute_my_experimental(args):
       experimental = get_experimental_features()
       
       if not experimental.is_enabled('my_feature'):
           print("Feature is disabled...")
           return 1
       
       if experimental.should_show_warning('my_feature'):
           # Show warning and get acceptance
   ```

4. **Use Lazy Imports**
   ```python
   # In cli/__init__.py
   if command == 'my-experimental':
       from .commands.my_experimental import execute_my_experimental
       return execute_my_experimental(args)
   ```

5. **Mark in Documentation**
   - Add "EXPERIMENTAL" or "BETA" badges
   - Include warnings in user guides
   - Document in README with clear marking

### Testing Requirements

All experimental features must have:

1. **Separation Tests**: Verify no dependencies from stable code
2. **Feature Flag Tests**: Ensure flags control availability
3. **Warning Tests**: Verify warnings are shown appropriately
4. **Integration Tests**: Test feature in isolation

Example test:
```python
def test_stable_code_has_no_experimental_imports():
    """Ensure stable commands don't import experimental code."""
    with open('src/claude_mpm/cli/commands/run.py', 'r') as f:
        source = f.read()
    
    # Parse AST and check imports
    tree = ast.parse(source)
    # ... verify no experimental imports
```

## Configuration

### Environment Variables

Control experimental features via environment:
```bash
export CLAUDE_MPM_EXPERIMENTAL_ENABLE_MCP_GATEWAY=true
export CLAUDE_MPM_EXPERIMENTAL_SHOW_WARNINGS=false
```

### Configuration File

```json
{
  "experimental_features": {
    "enable_mcp_gateway": true,
    "show_experimental_warnings": false
  }
}
```

Location: `~/.claude-mpm/experimental.json`

## Graduation Process

When an experimental feature becomes stable:

1. **Remove Experimental Warnings**: Update documentation and code
2. **Move to Stable Imports**: Remove lazy loading if appropriate
3. **Update Feature Flags**: Change default to enabled
4. **Merge Documentation**: Move from experimental to main docs
5. **Announce in Release Notes**: Clearly communicate stability

## Current Experimental Features

### MCP Gateway (Model Context Protocol)
- **Status**: Beta
- **Command**: `claude-mpm mcp`
- **Flag**: `enable_mcp_gateway`
- **Since**: v4.0.0
- **Description**: Enables integration with external tools and services through the Model Context Protocol
- **Documentation**: [MCP Gateway Guide](../13-mcp-gateway/README.md)

## Deprecated Features

### Memory Guardian (Removed in v4.1.0)
- **Status**: Removed
- **Replacement**: Use `cleanup-memory` command for memory management
- **Migration**: The Memory Manager agent now handles memory-related tasks

## Benefits of This Architecture

1. **Stability**: Experimental code cannot break stable features
2. **Performance**: Experimental code is only loaded when needed
3. **Clear Communication**: Users always know when using beta features
4. **Easy Rollback**: Features can be disabled without code changes
5. **Gradual Rollout**: Features can be tested by opt-in users first
6. **Clean Codebase**: No experimental code pollution in stable modules

## Best Practices

1. **Never Import Experimental Code in Stable Modules**
2. **Always Show Warnings for Beta Features**
3. **Use Feature Flags for All Experimental Features**
4. **Document Experimental Status Prominently**
5. **Test Separation Regularly**
6. **Provide Opt-Out Mechanisms**
7. **Track Usage and Issues Separately**