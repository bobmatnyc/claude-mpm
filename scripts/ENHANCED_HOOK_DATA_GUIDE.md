# Enhanced Claude Hook Data - User Guide

The Claude MPM hook handler has been significantly enhanced to capture comprehensive, meaningful data from Claude Code hooks instead of just basic event notifications.

## What's New

### Enhanced Data Capture

The hook handler now captures detailed information for each hook event:

#### 📝 User Prompt Events
- **Full prompt text** and preview (truncated for display)
- **Prompt characteristics**: length, contains code, urgency level
- **Context**: session ID, working directory
- **Classification**: command vs. regular prompt, code detection

#### 🔧 Pre-Tool Use Events  
- **Tool details**: name, operation type (read/write/execute/network)
- **Parameters**: extracted key parameters specific to each tool type
- **Security analysis**: risk assessment (low/medium/high)
- **Context**: file paths, command previews, parameter counts

#### ✅ Post-Tool Use Events
- **Execution results**: success/failure status, exit codes
- **Output data**: presence of output/errors, size metrics, previews
- **Performance**: duration (when available)
- **Status classification**: success/blocked/error

## Enhanced Dashboard Display

The Socket.IO dashboard now shows rich, meaningful information instead of raw JSON:

### User Prompts
```
📝 "Please help me debug this urgent error..." (162 chars)
🚨 📝 "Fix this broken authentication bug..." (89 chars)  // High urgency
```

### Tool Operations
```
⚠️ 💻 Bash → execute (sudo rm -rf /tmp/files)  // High risk
📝 Write → write (/Users/project/auth.py)      // Low risk  
✅ 📖 Read completed (success)                  // Success
❌ 💻 Bash completed (error)                    // Failed
```

## Security Risk Assessment

The hook handler now automatically assesses security risk:

- **🚨 HIGH RISK**: `sudo`, `rm -rf`, `curl | bash`, system file modifications
- **⚡ MEDIUM RISK**: Installation commands, absolute paths outside project
- **✅ LOW RISK**: Read operations, relative paths, safe commands

## Using the Enhanced Dashboard

1. **Connect to Socket.IO server** (default port 8765)
2. **View real-time events** with meaningful descriptions
3. **Click any event** to see full details in modal
4. **Filter by type** or search for specific patterns
5. **Export data** for analysis or debugging

## Testing the Enhancement

Run the demo scripts to see the enhancement in action:

```bash
# Test the enhanced hook handler
python scripts/test_enhanced_hook_handler.py

# See data extraction examples  
python scripts/demo_enhanced_hook_data.py
```

## What Changed

### Before (Limited Data)
```json
{
  "tool_name": "Write",
  "session_id": "abc123",
  "timestamp": "2025-01-01T12:00:00"
}
```

### After (Rich Data)
```json
{
  "event_type": "pre_tool",
  "tool_name": "Write", 
  "operation_type": "write",
  "tool_parameters": {
    "file_path": "/Users/project/auth.py",
    "content_length": 124,
    "is_create": true
  },
  "security_risk": "low",
  "is_file_operation": true,
  "session_id": "abc123",
  "working_directory": "/Users/project",
  "timestamp": "2025-01-01T12:00:00Z"
}
```

## Impact

- **Better Debugging**: See exactly what Claude is doing and why
- **Security Monitoring**: Identify risky operations before they execute  
- **Performance Analysis**: Track tool usage patterns and success rates
- **Context Awareness**: Understand session flow and working directory context
- **Meaningful Alerts**: Get actionable information instead of generic notifications

The dashboard now provides a comprehensive view of Claude Code's operations with the context needed to understand, debug, and monitor AI-assisted development workflows.