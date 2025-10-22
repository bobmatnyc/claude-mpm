# Response Logging Configuration Guide

This document explains how to configure response logging in Claude MPM using the `.claude-mpm/configuration.yaml` file.

## Overview

Response logging in Claude MPM uses a **hook-based architecture** that integrates with Claude Code's hook system. The system captures agent responses through `SubagentStop` and `Stop` hook events, not through subprocess control. 

Response logging can be configured via the `.claude-mpm/configuration.yaml` file instead of environment variables. This provides a more centralized and maintainable configuration approach.

## Architecture

### Hook-Based Response Capture

Claude MPM's response logging works through Claude Code's hook system:

1. **SubagentStop Events**: Triggered when a subagent (delegated agent) completes execution
2. **Stop Events**: Triggered when a main session or task stops  
3. **Hook Handler Processing**: Events are processed by the hook handler which extracts structured response data
4. **Response Logging**: Processed responses are logged to configured storage

**Important**: Response logging does NOT work through subprocess mode switching. It relies entirely on Claude Code hooks being properly configured and firing.

### Structured Response Format

Agents must return responses in a structured JSON format for proper logging. The hook handler looks for JSON blocks in agent responses with fields like:

- `task_completed`: Boolean indicating task completion
- `instructions`: Task completion summary
- `results`: Specific results or findings
- `files_modified`: List of files changed
- `tools_used`: Tools utilized during execution
- `remember`: Information to store in agent memory

## Configuration Structure

Add the following section to your `.claude-mpm/configuration.yaml` file:

```yaml
# Response logging configuration (for async session logger)
response_logging:
  # Enable response logging
  enabled: true
  
  # Use async logging for better performance
  use_async: true
  
  # Logging format: json, syslog, or journald
  format: json
  
  # Directory to store session responses
  session_directory: ".claude-mpm/responses"
  
  # Timestamp format for filenames
  timestamp_format: "{agent}_{timestamp}"
  
  # Force synchronous mode for debugging (overrides use_async)
  debug_sync: false
  
  # Maximum queue size for async writes
  max_queue_size: 10000
  
  # Enable compression for JSON logs (reduces disk usage)
  enable_compression: false
```

## Configuration Options

### `enabled`
- **Type**: boolean
- **Default**: `true`
- **Description**: Master switch to enable/disable response logging

### `use_async`
- **Type**: boolean
- **Default**: `true`
- **Description**: Use asynchronous logging for better performance. When enabled, responses are queued and written in the background.

### `format`
- **Type**: string
- **Options**: `json`, `syslog`, `journald`
- **Default**: `json`
- **Description**: Output format for response logs
  - `json`: Structured JSON files with full metadata
  - `syslog`: System log integration (macOS/Linux)
  - `journald`: systemd journal integration (Linux)

### `session_directory`
- **Type**: string
- **Default**: `".claude-mpm/responses"`
- **Description**: Base directory where response logs are stored. Each session gets its own subdirectory.

### `debug_sync`
- **Type**: boolean
- **Default**: `false`
- **Description**: Forces synchronous logging mode for debugging. Useful when troubleshooting logging issues.

### `max_queue_size`
- **Type**: integer
- **Default**: `10000`
- **Description**: Maximum number of log entries that can be queued for async writing. If the queue fills up, new entries will be dropped (fire-and-forget pattern).

### `enable_compression`
- **Type**: boolean
- **Default**: `false`
- **Description**: Enable gzip compression for JSON log files to reduce disk usage.

## Backward Compatibility

The system maintains backward compatibility with environment variables. If you have existing environment variables set, they will override the configuration file settings:

- `CLAUDE_USE_ASYNC_LOG`: Controls async mode (deprecated)
- `CLAUDE_LOG_FORMAT`: Sets log format (deprecated)
- `CLAUDE_LOG_SYNC`: Forces sync mode for debugging (deprecated)

**Note**: Environment variables are deprecated and will be removed in a future version. Please migrate to using the configuration file.

## Examples

### High-Performance Configuration

```yaml
response_logging:
  enabled: true
  use_async: true
  format: json
  session_directory: "/fast-ssd/claude-responses"
  max_queue_size: 50000
  enable_compression: true
```

### Debug Configuration

```yaml
response_logging:
  enabled: true
  use_async: false  # Or use debug_sync: true
  format: json
  session_directory: "./debug-responses"
  enable_compression: false
```

### System Log Integration

```yaml
response_logging:
  enabled: true
  use_async: true
  format: syslog  # Or journald on Linux
  # session_directory not used with syslog/journald
```

## Migration from Environment Variables

To migrate from environment variables to configuration file:

1. Check your current environment variables:
   ```bash
   env | grep CLAUDE_
   ```

2. Add the equivalent settings to `.claude-mpm/configuration.yaml`:
   - `CLAUDE_USE_ASYNC_LOG=true` → `use_async: true`
   - `CLAUDE_LOG_FORMAT=json` → `format: json`
   - `CLAUDE_LOG_SYNC=true` → `debug_sync: true`

3. Remove or unset the environment variables:
   ```bash
   unset CLAUDE_USE_ASYNC_LOG
   unset CLAUDE_LOG_FORMAT
   unset CLAUDE_LOG_SYNC
   ```

## Testing Your Configuration

You can test your configuration using the provided test script:

```bash
python scripts/test_config_based_logging.py
```

This will verify that your configuration is being loaded and applied correctly.

## Performance Considerations

- **Async mode** (`use_async: true`) provides near-zero performance overhead by queuing writes
- **Compression** (`enable_compression: true`) reduces disk usage but adds CPU overhead
- **System logs** (`format: syslog` or `journald`) offer OS-level performance but less structured data
- **Queue size** affects memory usage - larger queues can handle bigger bursts but use more RAM

## Troubleshooting

### Configuration Issues
1. **Logs not being created**: Check that `enabled: true` and verify the `session_directory` exists and is writable
2. **Performance issues**: Ensure `use_async: true` unless debugging
3. **Disk space issues**: Enable compression with `enable_compression: true`
4. **Missing logs during high load**: Increase `max_queue_size` to handle bursts

### Hook-Related Issues

**Response logging depends on Claude Code hooks working properly:**

1. **No response logs captured**: 
   - Verify Claude Code hooks are installed and active
   - Check that `.claude/hooks/` directory exists with hook scripts
   - Ensure hook handler is receiving `SubagentStop` and `Stop` events

2. **Incomplete response data**:
   - Agents must return structured JSON responses for full logging
   - Check agent templates include proper response format
   - Verify hook handler can parse agent response JSON

3. **Missing agent identification**:
   - Agent responses must include identifiable agent type information
   - Check that `agent_type` is properly passed through hook events
   - Ensure agent names are properly normalized in hook processing

4. **Hook system debugging**:
   ```bash
   # Check if hooks are firing
   tail -f .claude-mpm/logs/latest.log | grep -i hook
   
   # Verify hook handler connectivity
   python -c "from claude_mpm.hooks.claude_hooks.hook_handler import HookHandler; print('Hook handler available')"
   ```

**Important**: If Claude Code hooks are not working, response logging will not capture any data, regardless of configuration settings.