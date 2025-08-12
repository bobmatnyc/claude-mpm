# Claude MPM Response Tracking System

> **Navigation**: [Developer Guide](../README.md) → **Response System**

A comprehensive system for capturing, storing, and analyzing agent responses within the Claude MPM (Multi-Agent Project Manager) framework.

## Introduction

Response tracking enables automatic capture and storage of all agent interactions for debugging, auditing, and analysis purposes. The system provides a complete audit trail of agent activities, helping developers understand agent behavior patterns, debug issues, and analyze performance metrics.

**Key Benefits:**
- **Complete Audit Trail**: Full record of all agent interactions
- **Privacy by Design**: Disabled by default, user-controlled activation  
- **Debugging Support**: Detailed error tracking and resolution
- **Performance Analysis**: Response time and token usage metrics
- **Session Organization**: Logical grouping of related interactions

## Architecture Overview

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Hook System   │───▶│  Response Tracker │───▶│   File Storage  │
│                 │    │                  │    │                 │
│ • Pre-tool      │    │ • Correlation    │    │ • Session dirs  │
│ • Post-tool     │    │ • Metadata       │    │ • JSON files    │
│ • Event capture │    │ • Storage mgmt   │    │ • UTF-8 support │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                        │                        │
         ▼                        ▼                        ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   CLI Commands  │    │ Manager UI (TUI) │    │ Analysis Tools  │
│                 │    │                  │    │                 │
│ • List          │    │ • Real-time view │    │ • Statistics    │
│ • Stats         │    │ • Session mgmt   │    │ • Export (TBD)  │
│ • Clear         │    │ • Monitoring     │    │ • Reporting     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

### Component Interaction Flow

1. **Hook Capture**: Hook system intercepts agent requests and responses
2. **Request Correlation**: Original requests stored with unique session IDs
3. **Response Processing**: Responses captured with metadata and timing
4. **File Storage**: Data persisted in organized session directories
5. **CLI Access**: Commands provide query and management capabilities
6. **Real-time Monitoring**: Manager UI displays live activity

## Key Features

### Automatic Response Capture
- **Full Response Storage**: Complete agent responses without truncation
- **Request Correlation**: Links responses to original prompts
- **Metadata Collection**: Captures model info, tokens, duration, tools used
- **Unicode Support**: Proper handling of international characters

### Session Management
- **Logical Organization**: Responses grouped by session ID
- **Chronological Ordering**: Timestamped entries with millisecond precision
- **Multi-Agent Support**: Track responses from different agents in same session
- **Session Statistics**: Aggregate metrics per session

### Privacy and Security
- **Disabled by Default**: Must be explicitly enabled for privacy protection
- **Local Storage Only**: All data stored locally in `.claude-mpm/responses/`
- **User Control**: Complete control over what gets tracked
- **Secure Cleanup**: Built-in cleanup commands for data management

### Performance Optimization
- **Thread-Safe Operations**: Concurrent response tracking without conflicts  
- **Minimal Overhead**: Asynchronous processing doesn't block operations
- **Efficient Storage**: Optimized JSON format with compression
- **Smart Cleanup**: Automatic cleanup of stale correlation data

### Error Handling
- **Graceful Degradation**: Tracking failures never block Claude operations
- **Comprehensive Logging**: Detailed error reporting for troubleshooting
- **Recovery Mechanisms**: Automatic retry and fallback behaviors
- **Data Integrity**: Validation and consistency checks

## Quick Start

### 1. Enable Response Tracking

Response tracking is **disabled by default** for privacy. To enable it:

```bash
# Set environment variable
export CLAUDE_MPM_RESPONSE_TRACKING_ENABLED=true

# Or configure via config file
echo "response_tracking.enabled: true" >> ~/.claude-mpm/config.yaml
```

### 2. Use Claude MPM Normally

Once enabled, response tracking happens automatically:

```bash
# Run any Claude MPM command
./claude-mpm run -i "Create a Python script to analyze data"

# Responses are automatically tracked in background
```

### 3. View Tracked Responses

```bash
# List recent responses
claude-mpm responses list

# View session-specific responses  
claude-mpm responses list --session my-session-id

# Show statistics
claude-mpm responses stats
```

### 4. Manage Storage

```bash
# Clear old responses (7+ days)
claude-mpm responses clear --older-than 7 --confirm

# Clear specific session
claude-mpm responses clear --session my-session-id --confirm

# Clear all responses
claude-mpm responses clear --confirm
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `CLAUDE_MPM_RESPONSE_TRACKING_ENABLED` | Enable response tracking | `false` |
| `CLAUDE_MPM_RESPONSE_TRACKING_DIR` | Custom storage directory | `.claude-mpm/responses/` |

### Configuration File Options

Add to `~/.claude-mpm/config.yaml`:

```yaml
response_tracking:
  enabled: true
  storage_dir: "/custom/path/responses"
  track_all_agents: true
  excluded_agents: ["test", "debug"]
  min_response_length: 50
  auto_cleanup_days: 30
  max_sessions: 100
```

### Configuration Parameters

- **enabled**: Master switch for response tracking
- **storage_dir**: Custom directory for response files
- **track_all_agents**: Track responses from all agents (default: true)
- **excluded_agents**: List of agent names to never track
- **min_response_length**: Minimum response length to track (characters)
- **auto_cleanup_days**: Automatically delete sessions older than N days
- **max_sessions**: Maximum number of sessions to retain

## Security Considerations

### Data Privacy

- **Local Storage Only**: All response data stays on your machine
- **No Network Transmission**: Responses never sent to external services
- **User Control**: You decide what gets tracked and for how long
- **Explicit Activation**: Must be deliberately enabled, never automatic

### Storage Security

- **File Permissions**: Response files created with appropriate permissions
- **Secure Deletion**: Cleanup operations securely remove files
- **Path Validation**: All file paths validated to prevent directory traversal
- **Content Filtering**: Sensitive data patterns can be excluded (future feature)

### Best Practices

1. **Regular Cleanup**: Periodically clean old responses to manage disk usage
2. **Backup Considerations**: Include response data in backup strategies if needed
3. **Access Control**: Ensure only authorized users can access response files
4. **Monitoring**: Monitor disk usage in response tracking directories
5. **Configuration Review**: Regularly review tracking configuration for appropriateness

### Compliance Notes

- Response tracking may capture sensitive information from prompts and responses
- Organizations should review data retention policies
- Consider privacy implications when enabling tracking in shared environments
- Response data may be subject to data protection regulations

## File Structure

Response files are organized in a hierarchical structure:

```
.claude-mpm/responses/
├── session-1/
│   ├── engineer-20240110_143052_123.json
│   ├── qa-20240110_143125_456.json
│   └── documentation-20240110_143200_789.json
├── session-2/
│   ├── research-20240110_150030_001.json
│   └── engineer-20240110_150145_002.json
└── default/
    └── pm-20240110_160000_999.json
```

## Next Steps

- **User Guide**: See [USER_GUIDE.md](USER_GUIDE.md) for detailed usage instructions
- **Technical Reference**: See [TECHNICAL_REFERENCE.md](TECHNICAL_REFERENCE.md) for system internals
- **Development**: See [DEVELOPMENT.md](DEVELOPMENT.md) for extending the system

## Support

For issues and questions:

1. Check the [troubleshooting guide](USER_GUIDE.md#troubleshooting)
2. Review system logs for error messages
3. Verify configuration settings
4. Test with minimal examples to isolate issues

## Version History

- **v1.0**: Initial response tracking implementation
- **v1.1**: Added session-based organization and CLI commands
- **v1.2**: Enhanced error handling and performance optimizations
- **v1.3**: Added configuration options and cleanup features

---

*Response tracking is part of Claude MPM's extensible architecture. For more information about the overall system, see the main [project documentation](../README.md).*