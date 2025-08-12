# Event Aggregator Usage Guide

## Starting the Aggregator

### Method 1: CLI Command (Recommended)

```bash
# Start the aggregator
claude-mpm aggregate start

# The service will:
# 1. Connect to Socket.IO dashboard on port 8765
# 2. Create .claude-mpm/activity/ directory if needed
# 3. Begin capturing events
# 4. Show status updates every 30 seconds
```

### Method 2: Python Module

```bash
# Run as Python module
python -m claude_mpm.scripts.start_activity_logging
```

### Method 3: Direct Script

```bash
# Run the startup script directly
python src/claude_mpm/scripts/start_activity_logging.py
```

## Managing the Aggregator

### Check Status

```bash
# View aggregator status
claude-mpm aggregate status

# Example output:
Event Aggregator Status:
  Status: Running
  Connected: Yes
  Active Sessions: 3
  Total Events: 247
  Activity Directory: .claude-mpm/activity/
  Dashboard Port: 8765
```

### Stop the Aggregator

```bash
# Gracefully stop the service
claude-mpm aggregate stop

# Or use Ctrl+C when running interactively
```

## Viewing Captured Sessions

### List All Sessions

```bash
# List captured sessions
claude-mpm aggregate sessions

# Example output:
Captured Sessions:
  
  Session: 5283b66c-2b29-4ee0-9698-f410f3a393fd
    Start: 2025-08-12 14:15:30
    Duration: 3m 25s
    Events: 74
    File: session_5283b66c_20250812_141530.json
    
  Session: 7a91d44e-8c12-4f3b-ae56-9b2c1e0f8d35
    Start: 2025-08-12 14:20:15
    Duration: 5m 12s
    Events: 152
    File: session_7a91d44e_20250812_142015.json
```

### View Session Details

```bash
# View specific session
claude-mpm aggregate view 5283b66c-2b29-4ee0-9698-f410f3a393fd

# Example output:
Session Details:
  ID: 5283b66c-2b29-4ee0-9698-f410f3a393fd
  Start Time: 2025-08-12 14:15:30
  End Time: 2025-08-12 14:18:55
  Duration: 3m 25s
  
Events Summary:
  Total Events: 74
  User Prompts: 1
  Agent Delegations: 2
  Tool Operations: 45
  File Operations: 12
  Todo Updates: 3
  Responses: 2
  
Agents Used:
  - research (1 delegation)
  - engineer (1 delegation)
  
Files Modified:
  - src/services/aggregator.py
  - docs/README.md
  - tests/test_aggregator.py
```

### Export Session Data

```bash
# Export to JSON file
claude-mpm aggregate export 5283b66c --output my_session.json

# Export format options
claude-mpm aggregate export 5283b66c --format summary  # Summary only
claude-mpm aggregate export 5283b66c --format full     # Complete data
claude-mpm aggregate export 5283b66c --format events   # Events only
```

## Analyzing Session Data

### Using Python

```python
import json
from pathlib import Path

# Load session file
session_file = Path(".claude-mpm/activity/session_5283b66c_20250812_141530.json")
with open(session_file) as f:
    session_data = json.load(f)

# Analyze the session
print(f"Session ID: {session_data['session_id']}")
print(f"Total Events: {len(session_data['events'])}")
print(f"Duration: {session_data['metrics']['session_duration_ms']/1000:.1f}s")

# Extract agent delegations
delegations = session_data.get('delegations', [])
for delegation in delegations:
    print(f"Agent: {delegation['agent_type']}")
    print(f"  Instructions: {delegation['instructions'][:100]}...")
    print(f"  Events: {delegation['event_count']}")
```

### Using jq

```bash
# Get session summary
jq '.metrics' .claude-mpm/activity/session_*.json

# List all agent delegations
jq '.delegations[].agent_type' .claude-mpm/activity/session_*.json

# Find files modified
jq '.events[] | select(.category == "file") | .data.file_path' \
   .claude-mpm/activity/session_*.json | sort -u

# Get user prompts
jq '.events[] | select(.event_type == "UserPromptSubmit") | .data.prompt' \
   .claude-mpm/activity/session_*.json
```

## Real-time Monitoring

### Watch Active Sessions

```bash
# Monitor aggregator status
watch -n 5 'claude-mpm aggregate status'

# Tail aggregator logs
tail -f .claude-mpm/logs/aggregator.log
```

### Debug Mode

```bash
# Enable debug output
export CLAUDE_MPM_AGGREGATOR_DEBUG=true
claude-mpm aggregate start

# Debug output shows:
# - Every event received
# - Session creation/updates
# - File saves
# - Connection status
```

## Common Use Cases

### 1. Debugging Agent Delegations

```bash
# Start aggregator before running task
claude-mpm aggregate start

# In another terminal, run your task
claude-mpm run -i "implement new feature"

# After completion, view the session
claude-mpm aggregate sessions
claude-mpm aggregate view <session_id>
```

### 2. Analyzing Tool Usage

```python
# Load all sessions and analyze tool usage
import json
from pathlib import Path
from collections import Counter

activity_dir = Path(".claude-mpm/activity")
tool_usage = Counter()

for session_file in activity_dir.glob("session_*.json"):
    with open(session_file) as f:
        data = json.load(f)
    
    for event in data.get('events', []):
        if event.get('category') == 'tool':
            tool_name = event.get('data', {}).get('tool_name')
            if tool_name:
                tool_usage[tool_name] += 1

print("Tool Usage Statistics:")
for tool, count in tool_usage.most_common():
    print(f"  {tool}: {count}")
```

### 3. Session Replay

```python
# Replay a session's events
import json
import time
from datetime import datetime

def replay_session(session_file):
    """Replay session events with timing."""
    with open(session_file) as f:
        data = json.load(f)
    
    events = data.get('events', [])
    start_time = None
    
    for event in events:
        timestamp = datetime.fromisoformat(event['timestamp'])
        
        if start_time is None:
            start_time = timestamp
        else:
            # Wait for appropriate time
            elapsed = (timestamp - start_time).total_seconds()
            time.sleep(min(elapsed, 1))  # Cap at 1 second
        
        # Display event
        event_type = event.get('event_type', 'Unknown')
        category = event.get('category', '')
        print(f"[{elapsed:.1f}s] {event_type} ({category})")
        
        if category == 'prompt':
            print(f"  User: {event['data'].get('prompt', '')[:100]}...")
        elif category == 'delegation':
            print(f"  Agent: {event['data'].get('agent_type', 'unknown')}")

# Usage
replay_session(".claude-mpm/activity/session_5283b66c_20250812_141530.json")
```

## Troubleshooting

### Aggregator Won't Start

```bash
# Check if Socket.IO dashboard is running
curl http://localhost:8765/socket.io/ -v

# Check configuration
claude-mpm config view --section event_aggregator

# Check permissions
ls -la .claude-mpm/activity/
```

### No Sessions Captured

```bash
# Verify aggregator is running
claude-mpm aggregate status

# Check capture settings
grep -A 10 "capture:" .claude-mpm/configuration.yaml

# Enable debug mode
export CLAUDE_MPM_AGGREGATOR_DEBUG=true
claude-mpm aggregate start
```

### Sessions Never Complete

```bash
# Check timeout setting
grep session_timeout_minutes .claude-mpm/configuration.yaml

# Manually save active sessions
claude-mpm aggregate stop  # This saves all active sessions
```

## Best Practices

1. **Start Before Work**: Always start aggregator before beginning agent work
2. **Regular Exports**: Export important sessions for backup
3. **Clean Old Sessions**: Use auto-cleanup or manually remove old files
4. **Monitor Disk Usage**: Activity files can accumulate quickly
5. **Use Debug Sparingly**: Debug mode generates verbose output
6. **Session Naming**: Export with descriptive names for important sessions

## Integration Examples

### CI/CD Pipeline

```yaml
# .github/workflows/test.yml
steps:
  - name: Start aggregator
    run: |
      claude-mpm aggregate start &
      sleep 5
      
  - name: Run tests with Claude
    run: claude-mpm run -i "run all tests"
    
  - name: Save session
    if: always()
    run: |
      claude-mpm aggregate stop
      claude-mpm aggregate export --output test_session.json
      
  - name: Upload session artifact
    uses: actions/upload-artifact@v2
    with:
      name: test-session
      path: test_session.json
```

### Shell Script Integration

```bash
#!/bin/bash
# capture_session.sh

# Start aggregator in background
claude-mpm aggregate start &
AGGREGATOR_PID=$!

# Ensure aggregator stops on exit
trap "kill $AGGREGATOR_PID 2>/dev/null" EXIT

# Wait for aggregator to start
sleep 2

# Run your Claude MPM task
claude-mpm run -i "$1"

# Stop aggregator (saves sessions)
kill $AGGREGATOR_PID 2>/dev/null
wait $AGGREGATOR_PID 2>/dev/null

# List captured sessions
claude-mpm aggregate sessions
```