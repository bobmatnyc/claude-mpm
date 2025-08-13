# File Viewer Implementation

This document provides comprehensive technical details for the Socket.IO dashboard file viewer implementation, including the file-tool-tracker.js component and its integration with Claude Code events.

## Overview

The file viewer tracks file operations in real-time by correlating pre/post tool events from Claude Code hooks. It provides detailed file operation history and tool execution tracking across the dashboard's Files and Tools tabs.

## Core Implementation: file-tool-tracker.js

### Purpose and Design

The `FileToolTracker` class (`/src/claude_mpm/dashboard/static/js/components/file-tool-tracker.js`) serves as the central component for:

- **Event Correlation**: Pairs pre_tool and post_tool events into complete operations
- **File Path Extraction**: Extracts file paths from various parameter formats
- **Tool Operation Tracking**: Maintains comprehensive tool execution history
- **Agent Inference Integration**: Associates operations with specific agents

### Key Design Decisions

1. **Intelligent Event Pairing**: Uses temporal proximity and parameter similarity to match pre/post events
2. **Case-Insensitive Tool Handling**: Supports both "Read" and "read" tool names
3. **Multiple Parameter Formats**: Handles various ways file paths are specified
4. **Orphaned Event Support**: Gracefully handles unpaired events (still running or failed operations)

## Supported File Tools

The file viewer supports case-insensitive tracking of these Claude Code tools:

### Primary File Tools

| Tool Name | Operation Type | Parameters | Description |
|-----------|---------------|------------|-------------|
| `Read` | read | `file_path`, `path` | Read file contents |
| `Write` | write | `file_path`, `content` | Write file contents |
| `Edit` | edit | `file_path`, `old_string`, `new_string` | Edit file with replacements |
| `MultiEdit` | edit | `file_path`, `edits[]` | Multiple edits in one operation |
| `NotebookEdit` | edit | `notebook_path`, `edits[]` | Jupyter notebook editing |

### Search and Discovery Tools

| Tool Name | Operation Type | Parameters | Description |
|-----------|---------------|------------|-------------|
| `Grep` | search | `pattern`, `path` | Search for patterns in files |
| `Glob` | search | `pattern`, `path` | File pattern matching |
| `LS` | list | `path` | Directory listing |

### System Tools

| Tool Name | Operation Type | Parameters | Description |
|-----------|---------------|------------|-------------|
| `Bash` | bash | `command` | Shell commands (auto-detects file operations) |

### Case-Insensitive Tool Name Handling

**Critical Feature**: The implementation handles tool names case-insensitively to support both:

- **Claude Desktop**: Sends capitalized tool names ("Read", "Write", "Edit")
- **Claude Code**: Sends lowercase tool names ("read", "write", "edit")

```javascript
// Case-insensitive comparison
isFileOperation(event) {
    const fileTools = ['read', 'write', 'edit', 'grep', 'multiedit', 'glob', 'ls', 'bash', 'notebookedit'];
    const toolName = event.tool_name ? event.tool_name.toLowerCase() : '';
    return toolName && fileTools.includes(toolName);
}
```

## File Path Extraction

### Multiple Parameter Formats

The file viewer extracts file paths from various parameter locations:

```javascript
extractFilePath(event) {
    // Primary locations
    if (event.tool_parameters?.file_path) return event.tool_parameters.file_path;
    if (event.tool_parameters?.path) return event.tool_parameters.path;
    if (event.tool_parameters?.notebook_path) return event.tool_parameters.notebook_path;
    
    // Nested data locations
    if (event.data?.tool_parameters?.file_path) return event.data.tool_parameters.file_path;
    if (event.data?.tool_parameters?.path) return event.data.tool_parameters.path;
    
    // Direct event properties
    if (event.file_path) return event.file_path;
    if (event.path) return event.path;
    
    // Special cases
    if (event.tool_name?.toLowerCase() === 'glob' && event.tool_parameters?.pattern) {
        return `[glob] ${event.tool_parameters.pattern}`;
    }
    
    // Bash command file extraction
    if (event.tool_name?.toLowerCase() === 'bash') {
        return this.extractFileFromBashCommand(event.tool_parameters?.command);
    }
    
    return null;
}
```

### Bash Command File Extraction

For Bash tool operations, the file viewer attempts to extract file paths from common command patterns:

```javascript
// Extract file paths from bash commands
const fileMatch = command.match(/(?:cat|less|more|head|tail|touch|mv|cp|rm|mkdir|ls|find|echo.*>|sed|awk|grep)\s+([^\s;|&]+)/);
if (fileMatch && fileMatch[1]) {
    return fileMatch[1];
}
```

Supported bash file operations:
- **Read**: `cat`, `less`, `more`, `head`, `tail`
- **Write**: `touch`, `echo >`, `tee`
- **Edit**: `sed`, `awk`
- **Search**: `grep`, `find`
- **List**: `ls`, `dir`
- **Manage**: `mv`, `cp`, `rm`, `mkdir`

## Event Correlation System

### Pre/Post Event Pairing

The file viewer correlates related events using sophisticated matching logic:

#### 1. Temporal Grouping

Events are initially grouped by session, tool name, and timestamp (rounded to nearest second):

```javascript
const eventKey = `${sessionId}_${toolName}_${Math.floor(new Date(event.timestamp).getTime() / 1000)}`;
```

#### 2. Event Type Classification

Events are classified as pre_tool or post_tool based on:

```javascript
if (event.subtype === 'pre_tool' || (event.type === 'hook' && !event.subtype.includes('post'))) {
    // Pre-tool event
} else if (event.subtype === 'post_tool' || event.subtype.includes('post')) {
    // Post-tool event
}
```

#### 3. Intelligent Correlation

For tool calls, the system uses a scoring algorithm to match pre/post events:

```javascript
// Correlation scoring (higher is better)
let score = 1000 - (timeDiff / 1000); // Prefer closer timestamps

// Parameter similarity boost
if (this.compareToolParameters(preEvent, postEvent)) {
    score += 500;
}

// Working directory match boost
if (preEvent.working_directory === postEvent.working_directory) {
    score += 100;
}
```

### Parameter Comparison

The correlation system compares important parameters between pre/post events:

```javascript
compareToolParameters(preEvent, postEvent) {
    const importantParams = ['file_path', 'path', 'pattern', 'command', 'notebook_path'];
    let matchedParams = 0;
    let totalComparableParams = 0;
    
    importantParams.forEach(param => {
        const preValue = preParams[param];
        const postValue = postParams[param];
        
        if (preValue !== undefined || postValue !== undefined) {
            totalComparableParams++;
            if (preValue === postValue) {
                matchedParams++;
            }
        }
    });
    
    // Require 80% parameter match
    return (matchedParams / totalComparableParams) >= 0.8;
}
```

## Data Structures

### File Operations Map

The file viewer maintains a Map of file paths to operation data:

```javascript
this.fileOperations = new Map(); // Key: file path, Value: file data

// File data structure:
{
    path: "/path/to/file.txt",
    operations: [
        {
            operation: "read",
            timestamp: "2024-01-01T12:00:00Z",
            agent: "Engineer",
            confidence: "high",
            sessionId: "session-123",
            details: {
                parameters: {...},
                result: "...",
                success: true,
                duration_ms: 45
            },
            workingDirectory: "/project/root"
        }
    ],
    lastOperation: "2024-01-01T12:00:00Z"
}
```

### Tool Calls Map

Tool execution tracking uses a separate Map:

```javascript
this.toolCalls = new Map(); // Key: unique call ID, Value: paired call data

// Tool call structure:
{
    pre_event: {...},           // Original pre_tool event
    post_event: {...},          // Matched post_tool event (or null)
    tool_name: "Read",
    session_id: "session-123",
    operation_type: "tool_execution",
    timestamp: "2024-01-01T12:00:00Z",
    duration_ms: 45,
    success: true,
    exit_code: 0,
    result_summary: "File read successfully",
    agent_type: "Engineer",
    agent_confidence: "high"
}
```

## Operation Type Classification

File operations are classified into semantic categories:

```javascript
getFileOperation(event) {
    const toolName = event.tool_name.toLowerCase();
    switch (toolName) {
        case 'read': return 'read';
        case 'write': return 'write';
        case 'edit': 
        case 'multiedit': 
        case 'notebookedit': return 'edit';
        case 'grep': 
        case 'glob': return 'search';
        case 'ls': return 'list';
        case 'bash': return this.classifyBashOperation(command);
        default: return toolName;
    }
}
```

### Bash Operation Classification

For Bash commands, operations are classified by analyzing the command:

- **Read**: `cat`, `less`, `more`, `head`, `tail`
- **Write**: `touch`, `echo >`, `tee`
- **Edit**: `sed`, `awk`
- **Search**: `grep`, `find`
- **List**: `ls`, `dir`
- **Copy/Move**: `mv`, `cp`
- **Delete**: `rm`, `rmdir`
- **Create**: `mkdir`

## Integration Points

### Agent Inference Integration

The file viewer integrates with the agent inference system to determine which agent performed operations:

```javascript
extractAgentFromPair(pair) {
    const event = pair.pre_event || pair.post_event;
    if (this.agentInference) {
        const inference = this.agentInference.getInferredAgentForEvent(event);
        if (inference) {
            return {
                name: inference.agentName || 'Unknown',
                confidence: inference.confidence || 'unknown'
            };
        }
    }
    
    // Fallback to direct event properties
    const agentName = event?.agent_type || event?.subagent_type || 'PM';
    return { name: agentName, confidence: 'direct' };
}
```

### Working Directory Manager Integration

File operations include working directory context:

```javascript
const workingDirectory = this.workingDirectoryManager.extractWorkingDirectoryFromPair(pair);
```

## Performance Considerations

### Efficient Data Structures

- **Map Usage**: O(1) lookup for file operations and tool calls
- **Temporal Grouping**: Reduces correlation complexity
- **Event Deduplication**: Prevents duplicate entries

### Memory Management

- **Event Clearing**: Clear operations when dashboard resets
- **Size Limits**: Implement limits for long-running sessions
- **Garbage Collection**: Clean up orphaned event references

### Processing Optimization

```javascript
// Batch processing for large event sets
updateFileOperations(events) {
    console.log(`Processing ${events.length} events...`);
    
    // Process in chunks to avoid blocking UI
    if (events.length > 1000) {
        // Implement chunked processing
    }
}
```

## Testing and Verification

### Test Script Usage

Use the provided test script to verify file viewer functionality:

```bash
# Start dashboard
./claude-mpm --monitor

# Open browser to http://localhost:8765

# Run test script
python scripts/test_dashboard_file_viewer.py

# Verify results in Files tab
```

### Expected Test Results

The test script should produce 8 file operations in the Files tab:

1. `/test/example.txt` (Read)
2. `/test/output.py` (Write)
3. `/test/config.json` (Edit)
4. `/test/src` (Grep search)
5. `[glob] *.py` (Glob search)
6. `/test/directory` (LS listing)
7. `/test/multi.js` (MultiEdit)
8. `/test/lowercase.txt` (read - lowercase tool name)

### Debugging File Operations

Enable debug logging to troubleshoot file operation tracking:

```javascript
// Console debug output
console.log('File operation detected for:', filePath, 'from pair:', key);
console.log('updateFileOperations - final result:', this.fileOperations.size, 'file operations');
```

## Common Implementation Patterns

### Handling Missing Events

```javascript
// Graceful handling of orphaned events
if (bestMatchIndex >= 0 && bestMatchScore > 0) {
    // Successful pairing
    pair.post_event = postEvent;
} else {
    // Orphaned pre_tool (still running or failed)
    console.log(`No matching post_tool found for ${toolName} (still running or orphaned)`);
}
```

### Parameter Normalization

```javascript
// Normalize parameter access across event formats
const params = pair.pre_event.tool_parameters || 
               pair.pre_event.data?.tool_parameters || {};
```

### Error Recovery

```javascript
// Safe file path extraction with fallbacks
extractFilePathFromPair(pair) {
    let filePath = null;
    
    if (pair.pre_event) {
        filePath = this.extractFilePath(pair.pre_event);
    }
    
    if (!filePath && pair.post_event) {
        filePath = this.extractFilePath(pair.post_event);
    }
    
    return filePath;
}
```

## Cache Management

### Browser Caching

The dashboard includes cache-busting for JavaScript files:

```html
<!-- Force browser to load updated versions -->
<script src="/static/js/components/file-tool-tracker.js?v=1.1"></script>
```

### Event Data Caching

```javascript
// Clear tracking data when needed
clear() {
    this.fileOperations.clear();
    this.toolCalls.clear();
    console.log('File-tool tracker cleared');
}
```

## Statistics and Analytics

### Operation Statistics

```javascript
getStatistics() {
    return {
        fileOperations: this.fileOperations.size,
        toolCalls: this.toolCalls.size,
        uniqueFiles: this.fileOperations.size,
        totalFileOperations: Array.from(this.fileOperations.values())
            .reduce((sum, data) => sum + data.operations.length, 0)
    };
}
```

This provides insight into:
- Number of unique files accessed
- Total tool calls executed
- File operation frequency per file
- Tool usage patterns