# Logging Improvements Implementation Summary

## Date: 2025-08-24

### Overview
Implemented comprehensive logging improvements for the claude-mpm project based on research findings, including prompt logging, unified log management, and time-based retention.

## Components Implemented

### 1. LogManager Class (`/src/claude_mpm/core/log_manager.py`)

A unified log management system with the following features:

#### Key Features:
- **Async Fire-and-Forget Operations**: Non-blocking log writes using queue-based processing
- **Time-Based Retention**: 48-hour default retention (configurable)
- **Prompt Logging**: Captures system and agent prompts with metadata
- **Consolidated Cleanup**: Single source of truth for log pruning
- **Thread-Safe Operations**: Background threads for write and cleanup operations
- **Graceful Degradation**: Fallback mechanisms for all operations

#### Configuration:
```yaml
logging:
  retention_hours: 48          # Default retention
  startup_retention_hours: 48  # Startup logs
  mpm_retention_hours: 48      # MPM logs
  prompt_retention_hours: 168  # 7 days for prompts
  base_directory: ".claude-mpm/logs"

response_logging:
  session_retention_hours: 168  # 7 days for sessions
```

#### Methods:
- `setup_logging(log_type)`: Initialize logging directories
- `cleanup_old_logs(directory, pattern, retention_hours)`: Time-based cleanup
- `log_prompt(prompt_type, content, metadata)`: Save prompts with metadata
- `write_log_async(message, level)`: Async fire-and-forget logging
- `cleanup_old_startup_logs()`: Backward-compatible wrapper
- `cleanup_old_mpm_logs()`: Backward-compatible wrapper

### 2. Prompt Logging Integration

#### System Prompt Logging (`framework_loader.py`)
- Hooks into `get_framework_instructions()` method
- Captures full system prompt with metadata
- Saves to `.claude-mpm/logs/prompts/system_prompt_{timestamp}.md`
- Includes session ID, framework version, and prompt length

#### Agent Prompt Logging (`event_handlers.py`)
- Hooks into `SubagentStart` events
- Captures agent delegation prompts
- Saves to `.claude-mpm/logs/prompts/agent_{agent_type}_{timestamp}.md`
- Includes agent type, session ID, and delegation context

### 3. Migration of Existing Functions

#### Updated Files:
1. **`startup_logging.py`**: 
   - `cleanup_old_startup_logs()` now delegates to LogManager
   - Maintains backward compatibility with fallback

2. **`logger.py`**:
   - `cleanup_old_mpm_logs()` now delegates to LogManager
   - Maintains backward compatibility with fallback

## Directory Structure

```
.claude-mpm/
└── logs/
    ├── prompts/           # NEW: System and agent prompts
    │   ├── system_prompt_*.md
    │   └── agent_*.md
    ├── startup/           # Startup logs
    ├── sessions/          # Session logs
    ├── agents/            # Agent-specific logs
    └── mpm_*.log         # Main MPM logs
```

## Prompt File Format

### Markdown Format (`.md`)
```markdown
---
timestamp: 2025-08-24T11:17:44.725902
type: system_prompt
session_id: abc123
metadata: {...}
---

[Prompt content here]
```

### JSON Format (`.json`)
```json
{
  "timestamp": "2025-08-24T11:17:44.725902",
  "type": "agent_research",
  "content": "...",
  "metadata": {
    "agent_type": "research",
    "session_id": "abc123"
  }
}
```

## Benefits

### 1. Performance Improvements
- **Non-blocking Operations**: Async queue-based writing prevents I/O blocking
- **Reduced Overhead**: Fire-and-forget pattern for logging operations
- **Efficient Cleanup**: Time-based retention is more efficient than count-based

### 2. Better Debugging
- **Prompt Capture**: Full visibility into system and agent prompts
- **Session Correlation**: Session IDs link prompts to responses
- **Rich Metadata**: Context and timestamps for all logged data

### 3. Unified Management
- **Single Source of Truth**: All log operations through LogManager
- **Consistent Retention**: Unified time-based retention policy
- **Centralized Configuration**: All settings in one place

### 4. Backward Compatibility
- **Wrapper Functions**: Old functions delegate to LogManager
- **Fallback Logic**: Graceful degradation if LogManager unavailable
- **No Breaking Changes**: Existing code continues to work

## Testing

Created comprehensive test coverage:
- Directory creation and setup
- Prompt logging (system and agent)
- Async log writing
- Time-based cleanup
- Thread safety

## Configuration Options

Users can customize retention in `.claude-mpm/configuration.yaml`:

```yaml
logging:
  retention_hours: 72           # Keep logs for 3 days
  prompt_retention_hours: 336   # Keep prompts for 14 days
  
response_logging:
  session_retention_hours: 720  # Keep sessions for 30 days
```

## Future Enhancements

1. **Compression**: Add optional gzip compression for old logs
2. **Archiving**: Move old logs to archive directory instead of deletion
3. **Search**: Add search functionality for prompts
4. **Analytics**: Generate statistics from logged prompts
5. **Export**: Export prompts for training or analysis

## Migration Notes

For existing installations:
1. LogManager will be automatically initialized on first use
2. Old count-based retention functions still work but use time-based internally
3. Prompts directory will be created automatically
4. No manual migration required

## Monitoring

To verify the logging improvements are working:

```bash
# Check if prompts are being logged
ls -la .claude-mpm/logs/prompts/

# Monitor log manager activity
tail -f .claude-mpm/logs/mpm_*.log | grep -i "log"

# Check retention is working
find .claude-mpm/logs -type f -mtime +2 -name "*.log"
```

## Summary

This implementation provides a robust, scalable logging infrastructure with:
- ✅ Comprehensive prompt logging for debugging and analysis
- ✅ Unified log management with async operations
- ✅ Time-based retention (48-hour default)
- ✅ Backward compatibility maintained
- ✅ Performance optimizations through async/queue patterns
- ✅ Rich metadata capture for correlation

The system is production-ready and can handle high-frequency logging without performance impact.