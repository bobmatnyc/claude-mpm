# Response Tracking User Guide

This guide provides step-by-step instructions for using Claude MPM's response tracking system to monitor, analyze, and manage agent interactions.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Enabling Response Tracking](#enabling-response-tracking)  
3. [CLI Commands](#cli-commands)
4. [Understanding Response Files](#understanding-response-files)
5. [Session Management](#session-management)
6. [Common Use Cases](#common-use-cases)
7. [Troubleshooting](#troubleshooting)

## Getting Started

Response tracking captures and stores all agent interactions for analysis and debugging. It's designed with privacy in mind - **disabled by default** and requiring explicit activation.

### Prerequisites

- Claude MPM installed and functional
- Write permissions to `.claude-mpm/responses/` directory
- Basic familiarity with CLI commands

### Quick Enable and Test

```bash
# Enable response tracking
export CLAUDE_MPM_RESPONSE_TRACKING_ENABLED=true

# Run a simple command to generate tracked responses
./claude-mpm run -i "Hello, what can you help me with?"

# View the tracked responses
claude-mpm responses list
```

## Enabling Response Tracking

Response tracking is **disabled by default** for privacy protection. You have several options to enable it:

### Option 1: Environment Variable (Temporary)

```bash
# Enable for current terminal session
export CLAUDE_MPM_RESPONSE_TRACKING_ENABLED=true

# Enable permanently (add to ~/.bashrc or ~/.zshrc)
echo 'export CLAUDE_MPM_RESPONSE_TRACKING_ENABLED=true' >> ~/.bashrc
```

### Option 2: Configuration File (Permanent)

Create or edit `~/.claude-mpm/config.yaml`:

```yaml
response_tracking:
  enabled: true
```

### Option 3: Advanced Configuration

For more control, use the complete configuration:

```yaml
response_tracking:
  enabled: true
  storage_dir: "/custom/path/responses"  # Optional custom directory
  track_all_agents: true                 # Track all agents (default)
  excluded_agents: []                    # List of agents to exclude
  min_response_length: 0                 # Minimum response length to track
  auto_cleanup_days: 30                  # Auto-cleanup after 30 days
  max_sessions: 100                      # Maximum sessions to retain
```

### Verification

Verify response tracking is enabled:

```bash
# Run a command and check if responses are being tracked
./claude-mpm run -i "Test response tracking"

# Check if response files are created
ls -la .claude-mpm/responses/
```

## CLI Commands

The `claude-mpm responses` command provides comprehensive response management capabilities.

### List Responses

Display tracked responses with various filtering options:

```bash
# List 10 most recent responses (default)
claude-mpm responses list

# List specific number of responses
claude-mpm responses list --limit 20

# Filter by agent type
claude-mpm responses list --agent engineer

# Filter by session
claude-mpm responses list --session my-session-id

# Combine filters
claude-mpm responses list --agent qa --limit 5
```

**Example Output:**
```
📂 Latest 10 Responses
--------------------------------------------------------------------------------
1. 2024-01-10 14:30:52
   Agent: engineer
   Session: session-abc123
   Request: Create a Python script to analyze CSV data...
   Tokens: 1250
   Duration: 2.3s
--------------------------------------------------------------------------------
2. 2024-01-10 14:28:15
   Agent: qa
   Session: session-abc123
   Request: Review the generated Python script for best practices...
   Tokens: 890
   Duration: 1.8s
--------------------------------------------------------------------------------
```

### View Statistics

Get comprehensive statistics about tracked responses:

```bash
# Show overall statistics
claude-mpm responses stats
```

**Example Output:**
```
📊 Response Tracking Statistics
==================================================
Total Sessions: 15
Total Responses: 127

🤖 Responses by Agent:
  engineer: 45
  qa: 32
  documentation: 28
  research: 22

📁 Recent Sessions:
  session-abc123: 8 responses
    Last activity: 2024-01-10 14:30:52
  session-def456: 12 responses  
    Last activity: 2024-01-10 12:15:30
  session-ghi789: 6 responses
    Last activity: 2024-01-09 16:45:00
==================================================
```

### Clear Responses

Manage storage by clearing old or specific responses:

```bash
# Clear responses older than 7 days
claude-mpm responses clear --older-than 7 --confirm

# Clear specific session
claude-mpm responses clear --session session-abc123 --confirm

# Clear all tracked responses (use with caution!)
claude-mpm responses clear --confirm
```

**Safety Note:** The `--confirm` flag is required for all clear operations to prevent accidental data loss.

## Understanding Response Files

Response files use a structured JSON format for easy parsing and analysis.

### File Location and Naming

```
.claude-mpm/responses/
├── <session-id>/
│   ├── <agent>-<timestamp>.json
│   ├── <agent>-<timestamp>.json
│   └── ...
├── default/                    # Default session for unspecified sessions
│   └── <agent>-<timestamp>.json
└── ...
```

### JSON Structure

Each response file contains:

```json
{
  "timestamp": "2024-01-10T14:30:52.123456",
  "session_id": "session-abc123", 
  "agent": "engineer",
  "request": "Create a Python script to analyze CSV data...",
  "response": "I'll help you create a Python script for CSV analysis...",
  "metadata": {
    "model": "claude-3-sonnet-20240229",
    "tokens": 1250,
    "duration": 2.3,
    "tools_used": ["Write", "Read"],
    "confidence": 0.95,
    "response_format": "text"
  }
}
```

### Field Descriptions

| Field | Description | Type |
|-------|-------------|------|
| `timestamp` | ISO format timestamp with microseconds | string |
| `session_id` | Session identifier for grouping | string |
| `agent` | Name of the agent that generated response | string |
| `request` | Original prompt/request sent to agent | string |
| `response` | Complete agent response (not truncated) | string |
| `metadata` | Additional information about the interaction | object |

### Metadata Fields

| Metadata Field | Description | Optional |
|----------------|-------------|----------|
| `model` | Claude model used for response | Yes |
| `tokens` | Token count for request/response | Yes |
| `duration` | Response time in seconds | Yes |
| `tools_used` | List of tools used during response | Yes |
| `confidence` | Agent confidence score | Yes |
| `response_format` | Format of response (text, json, etc.) | Yes |

## Session Management

Sessions provide logical grouping of related interactions, making it easier to analyze workflows and debug issues.

### Understanding Sessions

- **Default Session**: Used when no session ID is specified
- **Named Sessions**: Custom sessions for organizing related work
- **Auto-Generated**: Sessions created automatically by framework
- **Chronological**: Responses within sessions are time-ordered

### Working with Sessions

```bash
# List all available sessions
claude-mpm responses list | grep "Session:" | sort | uniq

# View specific session
claude-mpm responses list --session my-project-session

# Get session statistics
claude-mpm responses stats
```

### Session Lifecycle

1. **Creation**: Sessions created automatically when first response is tracked
2. **Population**: Additional responses added as interactions occur
3. **Analysis**: Use CLI commands to review session contents
4. **Cleanup**: Sessions removed manually or via auto-cleanup

### Best Practices for Sessions

- Use descriptive session names for easier identification
- Group related work (e.g., feature development, bug fixes) in same session
- Regularly review and clean up old sessions
- Consider session duration when analyzing performance

## Common Use Cases

### Debugging Agent Issues

When an agent produces unexpected results:

```bash
# 1. Find recent responses from the problematic agent
claude-mpm responses list --agent engineer --limit 20

# 2. Review the specific session where issues occurred
claude-mpm responses list --session problem-session-id

# 3. Analyze request/response patterns for debugging
```

### Performance Analysis

Monitor agent performance over time:

```bash
# View statistics to identify slow agents
claude-mpm responses stats

# Review recent responses for duration patterns  
claude-mpm responses list --limit 50
```

Look for:
- High token usage indicating complex interactions
- Long duration times suggesting performance issues
- Patterns in tool usage for optimization opportunities

### Auditing and Compliance

Maintain complete records of agent activities:

```bash
# Generate comprehensive activity report
claude-mpm responses stats > monthly-activity-report.txt

# Review specific time periods by filtering sessions
claude-mpm responses list --session production-deploy-jan2024
```

### Quality Assurance

Review agent responses for quality and consistency:

```bash
# Check recent QA agent responses
claude-mpm responses list --agent qa --limit 30

# Compare responses across different agents for same requests
claude-mpm responses list --session cross-agent-comparison
```

### Learning and Training

Analyze successful interactions for training purposes:

```bash
# Review successful workflow sessions
claude-mpm responses list --session successful-deployment-v2

# Extract patterns from high-performing sessions
claude-mpm responses stats
```

## Troubleshooting

### Common Issues and Solutions

#### Response Tracking Not Working

**Symptoms**: No response files created, CLI commands show empty results

**Solutions**:
```bash
# 1. Verify tracking is enabled
echo $CLAUDE_MPM_RESPONSE_TRACKING_ENABLED

# 2. Check configuration file
cat ~/.claude-mpm/config.yaml | grep response_tracking

# 3. Verify directory permissions
ls -la .claude-mpm/
mkdir -p .claude-mpm/responses
chmod 755 .claude-mpm/responses

# 4. Test with verbose logging
CLAUDE_MPM_DEBUG=true ./claude-mpm run -i "test"
```

#### CLI Commands Show "No responses found"

**Symptoms**: Commands execute but return no results

**Solutions**:
```bash
# 1. Check if response files exist
find .claude-mpm/responses -name "*.json" -type f

# 2. Verify file permissions
ls -la .claude-mpm/responses/*/

# 3. Test JSON file integrity
python -m json.tool .claude-mpm/responses/default/*.json
```

#### High Disk Usage

**Symptoms**: Response directory consuming excessive disk space

**Solutions**:
```bash
# 1. Check directory size
du -sh .claude-mpm/responses/

# 2. Clean old responses
claude-mpm responses clear --older-than 7 --confirm

# 3. Configure auto-cleanup
echo "response_tracking.auto_cleanup_days: 14" >> ~/.claude-mpm/config.yaml

# 4. Identify large files
find .claude-mpm/responses -name "*.json" -size +1M -ls
```

#### Corrupted Response Files

**Symptoms**: JSON parsing errors, CLI commands fail

**Solutions**:
```bash
# 1. Find and identify corrupted files
find .claude-mpm/responses -name "*.json" -exec python -m json.tool {} \; 2>&1 | grep -B1 "Expecting"

# 2. Remove corrupted files (after backup)
# Backup first!
cp -r .claude-mpm/responses .claude-mpm/responses.backup

# Remove specific corrupted file
rm .claude-mpm/responses/session-id/corrupted-file.json

# 3. Reset if heavily corrupted
claude-mpm responses clear --confirm
```

#### Permission Errors

**Symptoms**: Cannot write response files, permission denied errors

**Solutions**:
```bash
# 1. Fix directory permissions
chmod -R 755 .claude-mpm/responses

# 2. Check ownership
ls -la .claude-mpm/

# 3. Create with proper permissions
mkdir -p .claude-mpm/responses
chmod 755 .claude-mpm/responses
```

### Performance Issues

#### Slow Response Tracking

**Symptoms**: Noticeable delays when tracking is enabled

**Solutions**:
- Increase `min_response_length` to filter small responses
- Exclude verbose agents using `excluded_agents` configuration
- Implement regular cleanup to prevent large directories

#### Memory Usage

**Symptoms**: High memory usage during tracking

**Solutions**:
- Reduce `max_sessions` in configuration
- Enable `auto_cleanup_days` for automatic maintenance
- Monitor and manually clean large sessions

### Getting Help

If issues persist:

1. **Check Logs**: Enable debug mode with `CLAUDE_MPM_DEBUG=true`
2. **Verify Installation**: Ensure Claude MPM is properly installed
3. **Test Minimal Case**: Try tracking with a simple, short interaction
4. **File Issues**: Report bugs with detailed error messages and configuration

### Configuration Validation

Use this checklist to verify your setup:

- [ ] Response tracking enabled via environment variable or config file
- [ ] `.claude-mpm/responses/` directory exists and is writable  
- [ ] Configuration syntax is valid YAML (if using config file)
- [ ] No conflicting configurations between environment and file
- [ ] Sufficient disk space available for response storage
- [ ] File permissions allow reading/writing response files

---

*For technical details about the response tracking system, see [TECHNICAL_REFERENCE.md](TECHNICAL_REFERENCE.md). For development and extension information, see [DEVELOPMENT.md](DEVELOPMENT.md).*