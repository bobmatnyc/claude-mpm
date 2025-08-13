# Testing & Debugging Procedures

This guide provides comprehensive testing procedures and debugging techniques for the Socket.IO dashboard system.

## Testing Overview

The Socket.IO dashboard requires testing at multiple levels to ensure proper functionality:

1. **Unit Testing**: Individual component verification
2. **Integration Testing**: End-to-end event flow validation  
3. **Performance Testing**: Load and latency verification
4. **Browser Compatibility**: Cross-browser functionality
5. **Real-world Testing**: Actual Claude Code integration

## Test Scripts

### Primary Test Script: test_dashboard_file_viewer.py

**Location**: `/scripts/test_dashboard_file_viewer.py`

**Purpose**: Comprehensive file viewer testing that validates the file-tool-tracker.js implementation.

#### Usage

```bash
# Start dashboard
./claude-mpm --monitor

# Open browser to http://localhost:8765

# Run test script
python scripts/test_dashboard_file_viewer.py

# Expected output:
# ✅ Connected to Socket.IO server
# 🔍 Generating file operation events...
# 1️⃣ Testing Read operation...
# 2️⃣ Testing Write operation...
# [... continues for 8 operations]
# ✅ Test events sent to dashboard!
```

#### Test Coverage

The script validates:

1. **Read Operation**: `/test/example.txt`
2. **Write Operation**: `/test/output.py`
3. **Edit Operation**: `/test/config.json`
4. **Grep Operation**: `/test/src` (search)
5. **Glob Operation**: `*.py` pattern
6. **LS Operation**: `/test/directory` (listing)
7. **MultiEdit Operation**: `/test/multi.js`
8. **Lowercase Tools**: `read` vs `Read` (case sensitivity fix)

#### Expected Results

**Files Tab Should Show**:
- 8 distinct file operations
- Correct operation types (read, write, edit, search, list)
- Proper file paths
- Timestamps within last few seconds

**Tools Tab Should Show**:
- 8 tool calls with pre/post event pairs
- Successful completion status
- Agent attribution (likely "PM")

### Browser Console Testing

#### Socket.IO Connection Verification

```javascript
// Open browser developer console on dashboard
// Check connection status
console.log('Socket.IO connected:', socket.connected);

// Monitor connection events
socket.on('connect', () => {
    console.log('✅ Connected to Socket.IO server');
});

socket.on('disconnect', (reason) => {
    console.log('❌ Disconnected:', reason);
});

// Monitor incoming events
socket.on('claude_event', (data) => {
    console.log('📨 Received event:', data.type, data.subtype);
});
```

#### Event Flow Testing

```javascript
// Test event reception
let eventCount = 0;
socket.on('claude_event', (data) => {
    eventCount++;
    console.log(`Event ${eventCount}:`, {
        type: data.type,
        subtype: data.subtype,
        tool_name: data.tool_name,
        timestamp: data.timestamp
    });
});

// After running test script, check:
console.log('Total events received:', eventCount);
// Should be 16 (8 pre_tool + 8 post_tool events)
```

#### File Tool Tracker Testing

```javascript
// Access the file tracker instance (if exposed globally)
if (window.fileToolTracker) {
    const stats = window.fileToolTracker.getStatistics();
    console.log('File tracker stats:', stats);
    
    // Should show:
    // fileOperations: 8
    // toolCalls: 8
    // uniqueFiles: 8
    
    // Check specific file operations
    const fileOps = window.fileToolTracker.getFileOperations();
    console.log('File operations:', Array.from(fileOps.entries()));
}
```

## Debugging Techniques

### Server-Side Debugging

#### Enable Debug Logging

```bash
# Enable detailed Socket.IO logging
export CLAUDE_MPM_HOOK_DEBUG=true
export SOCKETIO_DEBUG=true

# Start with debug output
./claude-mpm --monitor 2>&1 | tee debug.log
```

#### Monitor Server Events

```bash
# Watch for specific patterns in real-time
tail -f debug.log | grep -E "(socket|connection|event)"

# Look for:
# - "Socket.IO server started on port 8765"
# - "Client connected: <client_id>"
# - "Event forwarded to dashboard"
# - "Broadcasting event to N clients"
```

#### Socket.IO Server Health Check

```python
# Quick server health test
import requests
import socketio

# Test HTTP endpoint
try:
    response = requests.get('http://localhost:8765/')
    print(f"HTTP Status: {response.status_code}")
except Exception as e:
    print(f"HTTP Error: {e}")

# Test Socket.IO connection
try:
    sio = socketio.Client()
    sio.connect('http://localhost:8765')
    print("Socket.IO Connection: ✅ Success")
    sio.disconnect()
except Exception as e:
    print(f"Socket.IO Error: {e}")
```

### Client-Side Debugging

#### Browser Network Analysis

**Steps**:
1. Open Developer Tools (F12)
2. Go to Network tab
3. Filter by "WS" (WebSocket) or "socket.io"
4. Reload dashboard page
5. Monitor connection attempts

**Expected Network Activity**:
```
# Initial requests:
GET http://localhost:8765/ (200 OK)
GET http://localhost:8765/socket.io/ (200 OK)
GET http://localhost:8765/static/js/dashboard.js (200 OK)

# WebSocket upgrade:
GET http://localhost:8765/socket.io/?transport=websocket (101 Switching Protocols)
```

#### JavaScript Error Monitoring

```javascript
// Catch all JavaScript errors
window.addEventListener('error', (e) => {
    console.error('JavaScript Error:', {
        message: e.message,
        source: e.filename,
        line: e.lineno,
        column: e.colno
    });
});

// Monitor Socket.IO specific errors
socket.on('connect_error', (error) => {
    console.error('Socket.IO Connection Error:', error);
});

socket.on('error', (error) => {
    console.error('Socket.IO Error:', error);
});
```

#### Event Processing Debug

```javascript
// Monitor event processing performance
let processingTimes = [];

socket.on('claude_event', (data) => {
    const startTime = performance.now();
    
    // Event processing happens here
    // (dashboard processes the event)
    
    requestAnimationFrame(() => {
        const endTime = performance.now();
        const processingTime = endTime - startTime;
        processingTimes.push(processingTime);
        
        if (processingTimes.length % 10 === 0) {
            const avgTime = processingTimes.slice(-10).reduce((a, b) => a + b) / 10;
            console.log(`Avg processing time (last 10): ${avgTime.toFixed(2)}ms`);
        }
    });
});
```

### Integration Testing

#### Real Claude Code Integration

**Test with Actual Claude Session**:

```bash
# Step 1: Start dashboard
./claude-mpm --monitor

# Step 2: Open dashboard in browser
open http://localhost:8765

# Step 3: Start Claude session with monitoring
./claude-mpm run -i "Read the file README.md" --monitor

# Step 4: Verify events appear in dashboard
# Should see:
# - UserPromptSubmit event
# - pre_tool Read event  
# - post_tool Read event
# - SubagentStop event
```

#### Multi-Session Testing

```bash
# Terminal 1: Start persistent server
./scripts/socketio_server_manager.py

# Terminal 2: Start first Claude session  
./claude-mpm run -i "List files in current directory" --exec

# Terminal 3: Start second Claude session
./claude-mpm run -i "Read package.json file" --exec

# Verify dashboard shows events from both sessions
# Each should have unique session IDs
```

### Performance Testing

#### Load Testing

**High Event Volume Test**:

```python
# scripts/dashboard_load_test.py
import asyncio
import socketio
import time
from datetime import datetime

async def generate_load(num_events=1000):
    sio = socketio.AsyncClient()
    await sio.connect('http://localhost:8765')
    
    start_time = time.time()
    
    for i in range(num_events):
        await sio.emit('claude_event', {
            "type": "hook",
            "timestamp": datetime.now().isoformat(),
            "data": {
                "type": "hook",
                "subtype": "pre_tool",
                "tool_name": "Read",
                "tool_parameters": {"file_path": f"/test/file_{i}.txt"},
                "session_id": f"load-test-{i % 10}",  # 10 concurrent sessions
                "timestamp": time.time()
            }
        })
        
        if i % 100 == 0:
            print(f"Sent {i} events...")
    
    end_time = time.time()
    print(f"Sent {num_events} events in {end_time - start_time:.2f} seconds")
    
    await sio.disconnect()

# Run load test
asyncio.run(generate_load(1000))
```

#### Memory Usage Testing

**Monitor Dashboard Memory**:

```javascript
// Run in browser console during high event load
function monitorMemory() {
    if (performance.memory) {
        setInterval(() => {
            const memory = performance.memory;
            console.log({
                used: Math.round(memory.usedJSHeapSize / 1024 / 1024) + ' MB',
                total: Math.round(memory.totalJSHeapSize / 1024 / 1024) + ' MB',
                limit: Math.round(memory.jsHeapSizeLimit / 1024 / 1024) + ' MB'
            });
        }, 5000);
    }
}

monitorMemory();
```

#### Latency Testing

**Event Round-Trip Time**:

```javascript
// Measure end-to-end latency
socket.emit('ping_test', { timestamp: Date.now() });

socket.on('pong_test', (data) => {
    const latency = Date.now() - data.timestamp;
    console.log(`Round-trip latency: ${latency}ms`);
});
```

### Browser Compatibility Testing

#### Cross-Browser Test Matrix

| Browser | Version | Socket.IO | File Viewer | Real-time Updates |
|---------|---------|-----------|-------------|-------------------|
| Chrome | 120+ | ✅ | ✅ | ✅ |
| Firefox | 115+ | ✅ | ✅ | ✅ |
| Safari | 16+ | ✅ | ✅ | ✅ |
| Edge | 120+ | ✅ | ✅ | ✅ |

#### Mobile Browser Testing

```javascript
// Mobile-specific debug info
console.log('User Agent:', navigator.userAgent);
console.log('Screen:', screen.width + 'x' + screen.height);
console.log('Viewport:', window.innerWidth + 'x' + window.innerHeight);

// Test touch events (for mobile debugging)
document.addEventListener('touchstart', (e) => {
    console.log('Touch detected:', e.touches.length, 'fingers');
});
```

## Automated Testing

### Test Suite Structure

```bash
# Test organization
tests/
├── test_socketio_server.py          # Server unit tests
├── test_dashboard_connection.py     # Connection tests
├── test_file_tool_tracker.py        # File viewer tests
├── test_event_correlation.py        # Event pairing tests
├── test_browser_compatibility.py    # Cross-browser tests
└── integration/
    ├── test_real_claude_integration.py
    └── test_multi_session.py
```

### Running Automated Tests

```bash
# Run all dashboard tests
python -m pytest tests/test_dashboard* -v

# Run specific test categories
python -m pytest tests/test_socketio* -v  # Server tests
python -m pytest tests/test_file_tool* -v  # File viewer tests

# Run with coverage
python -m pytest tests/test_dashboard* --cov=claude_mpm.services.socketio_server
```

### Continuous Integration Testing

```yaml
# .github/workflows/dashboard-tests.yml
name: Dashboard Tests
on: [push, pull_request]

jobs:
  test-dashboard:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Setup Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      
      - name: Install dependencies
        run: |
          pip install -e .[monitor,test]
          
      - name: Start Socket.IO server
        run: |
          python scripts/socketio_server_manager.py &
          sleep 5  # Wait for server to start
          
      - name: Run dashboard tests
        run: |
          python scripts/test_dashboard_file_viewer.py
          python -m pytest tests/test_dashboard* -v
          
      - name: Check browser compatibility
        run: |
          # Use headless browser testing
          python tests/test_browser_compatibility.py --headless
```

## Test Data and Fixtures

### Event Fixtures

```python
# tests/fixtures/events.py
SAMPLE_FILE_READ_EVENT = {
    "type": "hook",
    "timestamp": "2024-01-01T12:00:00Z",
    "data": {
        "type": "hook",
        "subtype": "pre_tool",
        "tool_name": "Read",
        "tool_parameters": {
            "file_path": "/test/sample.txt"
        },
        "session_id": "test-session",
        "timestamp": 1704110400
    }
}

SAMPLE_FILE_WRITE_POST_EVENT = {
    "type": "hook",
    "timestamp": "2024-01-01T12:00:01Z",
    "data": {
        "type": "hook",
        "subtype": "post_tool",
        "tool_name": "Write",
        "tool_parameters": {
            "file_path": "/test/output.txt"
        },
        "result": "File written successfully",
        "success": True,
        "session_id": "test-session",
        "timestamp": 1704110401
    }
}
```

### Mock Objects

```python
# tests/mocks/socketio_mock.py
class MockSocketIOServer:
    def __init__(self):
        self.events = []
        self.clients = set()
    
    async def emit(self, event, data, room=None):
        self.events.append({'event': event, 'data': data, 'room': room})
    
    def get_emitted_events(self):
        return self.events
    
    def clear_events(self):
        self.events.clear()
```

## Verification Procedures

### Post-Test Verification

**After Running Tests**:

1. **Check Dashboard State**:
   ```javascript
   // Browser console verification
   console.log('Dashboard state after tests:', {
       connected: socket.connected,
       events_received: eventCount,
       file_operations: window.fileToolTracker?.getStatistics(),
       memory_usage: performance.memory?.usedJSHeapSize
   });
   ```

2. **Server State Check**:
   ```bash
   # Check server logs for errors
   grep -i error debug.log
   grep -i warning debug.log
   
   # Verify clean shutdown
   grep -i "server stopped" debug.log
   ```

3. **Resource Cleanup**:
   ```bash
   # Check for leaked processes
   ps aux | grep claude-mpm
   
   # Check for open sockets
   netstat -an | grep 8765
   
   # Verify temp files cleaned up
   ls /tmp/claude-mpm-* 2>/dev/null || echo "No temp files"
   ```

### Test Results Analysis

**Success Criteria**:
- ✅ All 8 test file operations appear in Files tab
- ✅ Socket.IO connection established without errors
- ✅ Events processed within 10ms of receipt
- ✅ No JavaScript errors in browser console
- ✅ Memory usage remains stable during test
- ✅ Server gracefully handles connection/disconnection

**Failure Indicators**:
- ❌ Missing file operations in Files tab
- ❌ Connection errors or timeouts
- ❌ JavaScript exceptions in console
- ❌ Events taking >100ms to process
- ❌ Memory usage growing continuously
- ❌ Server crashes or hangs

This comprehensive testing approach ensures the Socket.IO dashboard functions reliably across different environments and usage patterns.