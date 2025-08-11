# Response Logging Configuration Guide

This document explains how to configure response logging in Claude MPM using the `.claude-mpm/configuration.yaml` file.

## Overview

Response logging can now be configured via the `.claude-mpm/configuration.yaml` file instead of environment variables. This provides a more centralized and maintainable configuration approach.

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

1. **Logs not being created**: Check that `enabled: true` and verify the `session_directory` exists and is writable
2. **Performance issues**: Ensure `use_async: true` unless debugging
3. **Disk space issues**: Enable compression with `enable_compression: true`
4. **Missing logs during high load**: Increase `max_queue_size` to handle bursts