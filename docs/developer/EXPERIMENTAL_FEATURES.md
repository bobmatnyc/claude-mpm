# Experimental Features Architecture

## Overview

This document describes the architecture for experimental features in Claude MPM, using the Memory Guardian as the primary example. The design ensures clean separation between stable and experimental code.

## Architecture Principles

### 1. Complete Separation

```
┌─────────────────────────────────────────────────────────┐
│                    Stable Code                          │
├─────────────────────────────────────────────────────────┤
│  ClaudeRunner (base class)                              │
│  ├── No dependencies on experimental code               │
│  ├── No imports of memory guardian modules              │
│  └── Works independently                                │
│                                                          │
│  run.py command                                         │
│  ├── Uses ClaudeRunner directly                         │
│  ├── No awareness of memory features                    │
│  └── Completely stable                                  │
└─────────────────────────────────────────────────────────┘
                            ↑
                   No direct dependency
                            ↓
┌─────────────────────────────────────────────────────────┐
│                  Experimental Code                      │
├─────────────────────────────────────────────────────────┤
│  MemoryAwareClaudeRunner                                │
│  ├── Extends ClaudeRunner                               │
│  ├── Adds memory monitoring                             │
│  └── Does not modify base class                         │
│                                                          │
│  run_guarded.py command                                 │
│  ├── Uses MemoryAwareClaudeRunner                       │
│  ├── Shows experimental warnings                        │
│  └── Completely isolated                                │
└─────────────────────────────────────────────────────────┘
```

### 2. Lazy Loading

Experimental code is only loaded when explicitly requested:

```python
# In cli/__init__.py
def _execute_command(command: str, args) -> int:
    # Handle experimental run-guarded command separately with lazy import
    if command == 'run-guarded':
        # Lazy import to avoid loading experimental code unless needed
        from .commands.run_guarded import execute_run_guarded
        return execute_run_guarded(args)
    
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
        'enable_memory_guardian': False,  # Disabled by default
        'show_experimental_warnings': True,
        'require_experimental_acceptance': True,
    }
```

### 4. User Warnings

Experimental features always show clear warnings unless explicitly suppressed:

```bash
# First time use shows warning
$ claude-mpm run-guarded

⚠️  EXPERIMENTAL FEATURE: Memory Guardian is in beta.
   This feature may change or have issues. Use with caution in production.
   Report issues at: https://github.com/bluescreen10/claude-mpm/issues

Continue? [y/N]: 

# Suppress warning with flag
$ claude-mpm run-guarded --accept-experimental
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
export CLAUDE_MPM_EXPERIMENTAL_ENABLE_MEMORY_GUARDIAN=true
export CLAUDE_MPM_EXPERIMENTAL_SHOW_WARNINGS=false
```

### Configuration File

```json
{
  "experimental_features": {
    "enable_memory_guardian": true,
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

### Memory Guardian (run-guarded)
- **Status**: Beta
- **Command**: `claude-mpm run-guarded`
- **Flag**: `enable_memory_guardian`
- **Since**: v3.9.x

### MCP Gateway
- **Status**: Early Access
- **Command**: `claude-mpm mcp`
- **Flag**: `enable_mcp_gateway`
- **Since**: v3.10.x (planned)

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