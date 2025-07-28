# Claude MPM Hook System Analysis

## Executive Summary

The claude-mpm hook system is an event-driven architecture that enables integration between Claude Code and the MPM framework. It allows intercepting and modifying Claude Code behavior through a well-designed hook mechanism that follows established software design patterns.

## 1. Hook System Architecture

### Overview

The hook system consists of three main layers:

1. **Event Layer** (Claude Code)
   - Emits events for various user actions
   - Passes events to registered hooks via stdin/stdout

2. **Integration Layer** (Hook Wrapper & Handler)
   - `hook_wrapper.sh`: Environment setup and Python invocation
   - `hook_handler.py`: Main event processing logic

3. **Response Layer**
   - Returns actions to Claude Code (continue/block)
   - Can modify behavior or provide custom responses

### Architecture Diagram

```
┌─────────────────┐     JSON Event      ┌──────────────────┐
│  Claude Code    │ ─────────────────►  │ hook_wrapper.sh  │
│                 │                      │                  │
│  - User types   │                      │ - Setup env      │
│  - Tool usage   │                      │ - Run Python     │
│  - Session end  │                      └────────┬─────────┘
└─────────────────┘                               │
         ▲                                        │
         │                                        ▼
         │                              ┌──────────────────┐
    Response                            │ hook_handler.py  │
  (continue/block)                      │                  │
         │                              │ - Parse event    │
         └──────────────────────────────┤ - Route to       │
                                        │   handler        │
                                        │ - Return action  │
                                        └──────────────────┘
```

## 2. Design Patterns Used

### Chain of Responsibility Pattern
- Each event type has its dedicated handler method
- Events are routed based on `hook_event_name`
- Unknown events fall through to default handler

### Template Method Pattern
- `handle()` method defines the overall algorithm
- Specific steps delegated to specialized methods
- Consistent error handling and logging across all handlers

### Strategy Pattern
- Different handling strategies for different event types
- Each handler implements its own logic
- Easy to add new event handlers

### Command Pattern
- MPM commands (`/mpm status`, `/mpm agents`) encapsulated as registry entries
- Commands can be easily added or modified
- Decouples command definition from execution

### Singleton-like Behavior
- Each hook invocation creates a new handler instance
- No state maintained between invocations
- Ensures reliability and prevents side effects

## 3. Hook Registration and Management

### Installation Process

1. **Hook Installation** (`scripts/install_hooks.py`)
   ```bash
   python scripts/install_hooks.py
   ```
   - Creates/updates `~/.claude/settings.json`
   - Registers hook wrapper path
   - Sets up logging directories

2. **Hook Configuration** (`~/.claude/settings.json`)
   ```json
   {
     "hooks": {
       "UserPromptSubmit": "/path/to/hook_wrapper.sh",
       "PreToolUse": "/path/to/hook_wrapper.sh",
       "PostToolUse": "/path/to/hook_wrapper.sh",
       "Stop": "/path/to/hook_wrapper.sh",
       "SubagentStop": "/path/to/hook_wrapper.sh"
     }
   }
   ```

### Hook Types

1. **UserPromptSubmit**
   - Triggered when user submits a prompt
   - Can intercept `/mpm` commands
   - Can modify or block prompts

2. **PreToolUse**
   - Triggered before tool execution
   - Implements security policies
   - Can block dangerous operations

3. **PostToolUse**
   - Triggered after tool execution
   - Used for logging and monitoring
   - Cannot modify results (observation only)

4. **Stop**
   - Triggered when session ends
   - Used for cleanup and final logging

5. **SubagentStop**
   - Triggered when subagent completes
   - Provides agent tracking information

## 4. Hook Execution Lifecycle

### Event Flow

1. **Event Generation**
   - User action in Claude Code triggers event
   - Event serialized as JSON with context

2. **Hook Invocation**
   - Claude Code calls hook wrapper with event on stdin
   - Wrapper sets up environment (venv, PYTHONPATH)
   - Python handler invoked

3. **Event Processing**
   ```python
   # 1. Read and parse event
   event_data = sys.stdin.read()
   event = json.loads(event_data)
   
   # 2. Setup project-specific logging
   log_dir = project_dir / '.claude-mpm' / 'logs'
   
   # 3. Route to handler
   if hook_type == 'UserPromptSubmit':
       return self._handle_user_prompt_submit()
   
   # 4. Return action
   response = {"action": "continue"}
   print(json.dumps(response))
   ```

4. **Response Handling**
   - Exit code 0: Continue with response action
   - Exit code 2: Block LLM processing (for commands)
   - Other: Error occurred

### Security Implementation

The PreToolUse handler implements security policies:

```python
# Check for path traversal
if '..' in str(file_path):
    return {
        "action": "block",
        "error": "Security Policy: Path traversal attempts not allowed"
    }

# Ensure operations within working directory
target_path.relative_to(working_dir)  # Raises if outside
```

## 5. Key Files and Relationships

### Core Hook Files

1. **`hook_wrapper.sh`**
   - Entry point from Claude Code
   - Handles environment detection (dev/npm/pip)
   - Sets up Python environment
   - Invokes Python handler

2. **`hook_handler.py`**
   - Main hook processing logic
   - Event routing and handling
   - Command implementation
   - Security policy enforcement

3. **`base_hook.py`**
   - Abstract base classes for hooks
   - Defines HookType enum
   - HookContext and HookResult dataclasses
   - Template for custom hooks

### Supporting Files

1. **`validation_hooks.py`**
   - Validation hook implementations
   - Pre/post load validation
   - Security constraint checking

2. **`builtin/` directory** (Legacy)
   - Example hook implementations
   - Submit, delegation, extraction hooks
   - Deprecated in favor of Claude Code hooks

### Integration Examples

1. **`hook_enabled_orchestrator.py`**
   - Shows how to integrate hooks into orchestrators
   - Uses hook client for event processing
   - Demonstrates all hook types

2. **`hook_integration_example.py`**
   - Code examples for hook integration
   - Shows modification of prompts and results
   - Template for implementing hooks

## 6. Logging and Monitoring

### Logging Strategy

1. **Project-Specific Logs**
   - Each project has its own log directory
   - Logs stored in `.claude-mpm/logs/`
   - Daily rotation with date-based filenames

2. **Log Levels**
   - INFO: Basic event occurrence
   - DEBUG: Full event details
   - ERROR: Hook failures
   - WARNING: Security events

3. **Debug Mode**
   ```bash
   export CLAUDE_MPM_LOG_LEVEL=DEBUG
   ```

### Monitoring Capabilities

- Event frequency tracking
- Tool usage patterns
- Security policy violations
- Command usage statistics
- Agent delegation tracking

## 7. Extensibility

### Adding New Commands

1. Add to command registry:
   ```python
   self.mpm_args = {
       'status': 'Show system status',
       'agents': 'Show agent versions',
       'newcmd': 'Description of new command'  # Add here
   }
   ```

2. Implement handler method:
   ```python
   def _handle_mpm_newcmd(self):
       # Implementation
       print(output, file=sys.stderr)
       sys.exit(2)  # Block LLM
   ```

3. Update router in `_handle_user_prompt_submit()`

### Adding New Hook Types

1. Define in `HookType` enum
2. Add handler method
3. Update event router
4. Register in settings.json

## 8. Best Practices

### Error Handling
- Always fail-safe (continue on error)
- Log errors for debugging
- Provide helpful error messages

### Performance
- Quick responses to avoid UI delays
- Minimal processing in handlers
- Async operations avoided

### Security
- Validate all file paths
- Check for path traversal
- Log security events
- Fail-secure (block suspicious operations)

### Maintainability
- Clear documentation
- Consistent naming conventions
- Modular design
- Comprehensive logging

## 9. Future Enhancements

### Planned Features
- More MPM commands (config, debug, logs)
- Hook metrics and analytics
- Dynamic hook registration
- Hook chaining and priorities

### Architecture Evolution
- Move to async handlers for better performance
- Plugin system for custom hooks
- Web-based hook configuration
- Real-time hook monitoring dashboard

## 10. Conclusion

The claude-mpm hook system provides a robust, secure, and extensible mechanism for integrating with Claude Code. Its event-driven architecture, combined with well-established design patterns, makes it easy to maintain and extend. The system successfully balances functionality with security, providing powerful capabilities while protecting against misuse.

The hook system serves as the foundation for claude-mpm's IDE integration, enabling seamless command execution and system monitoring directly within the Claude Code environment.