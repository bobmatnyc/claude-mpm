# Socket.IO Troubleshooting Guide

## Overview

This guide provides comprehensive troubleshooting procedures for Socket.IO server issues in Claude MPM. It covers common connection problems, server startup failures, performance issues, and debugging techniques.

## Quick Diagnostic Commands

### System Health Check

```bash
# Check if Socket.IO server is running
./claude-mpm doctor --check-socketio

# View server status and metrics
curl http://localhost:8765/health

# Check port availability
netstat -tuln | grep 8765

# View recent server logs
tail -f ~/.claude/logs/socketio_server.log
```

### Connection Testing

```bash
# Test basic connectivity
curl -v http://localhost:8765/socket.io/?transport=polling

# Test WebSocket upgrade
websocat ws://localhost:8765/socket.io/?transport=websocket

# Check from dashboard
# Open browser dev tools on dashboard page
# Look for Socket.IO connection logs in console
```

## Common Connection Issues

### 1. Server Not Starting

#### Symptoms
- Dashboard shows "Disconnected" status
- `curl http://localhost:8765/health` fails
- No process listening on port 8765

#### Diagnostic Steps

```bash
# Check if port is already in use
lsof -i :8765

# Check for Python environment issues
python -c "import socketio, aiohttp; print('Dependencies OK')"

# Check server startup logs
tail -20 ~/.claude/logs/socketio_server.log

# Try manual server start
./claude-mpm dashboard --debug
```

#### Common Causes and Solutions

| Cause | Solution |
|-------|----------|
| **Port already in use** | `killall python; ./claude-mpm dashboard restart` |
| **Missing dependencies** | `pip install python-socketio aiohttp` |
| **Permission denied (port < 1024)** | Use port 8765 (default) or run with sudo |
| **Virtual environment not activated** | Activate venv: `source venv/bin/activate` |
| **Python path issues** | Set PYTHONPATH: `export PYTHONPATH=/path/to/src:$PYTHONPATH` |

### 2. Connection Drops/Timeouts

#### Symptoms
- Dashboard connects then immediately disconnects
- Intermittent connection losses
- "Transport unknown" errors in browser console

#### Diagnostic Steps

```bash
# Check network connectivity
ping localhost

# Test connection stability
while true; do curl -s http://localhost:8765/health || echo "Failed $(date)"; sleep 1; done

# Monitor connection events
tail -f ~/.claude/logs/socketio_server.log | grep -E "(connect|disconnect)"

# Check for resource limits
ulimit -n  # File descriptor limit
ps aux | grep python | grep socketio  # Memory usage
```

#### Solutions by Error Type

**Transport unknown**
```javascript
// Browser console error: Transport unknown
// Solution: Check CORS configuration
```

**Fix**: Update `src/claude_mpm/config/socketio_config.py`:
```python
CORS_ORIGINS = ["http://localhost:3000", "http://127.0.0.1:3000"]
```

**Connection timeout**
```bash
# Increase timeout values
export SOCKETIO_TIMEOUT=60
./claude-mpm dashboard restart
```

**Memory exhaustion**
```bash
# Check memory usage
free -h
ps aux --sort=-%mem | head -10

# Reduce buffer sizes
export SOCKETIO_BUFFER_SIZE=500
./claude-mpm dashboard restart
```

### 3. Port Conflict Resolution

#### Automatic Port Detection

```bash
# Find available port automatically
python -c "
import socket
s = socket.socket()
s.bind(('', 0))
port = s.getsockname()[1]
s.close()
print(f'Available port: {port}')
"

# Start server on different port
./claude-mpm dashboard --port 8766
```

#### Port Range Configuration

```bash
# Configure port range for automatic selection
export SOCKETIO_PORT_RANGE="8765-8775"
./claude-mpm dashboard
```

#### Manual Port Conflict Resolution

```bash
# Find process using port 8765
lsof -ti:8765

# Kill process using port (if safe)
kill $(lsof -ti:8765)

# Or use different port
./claude-mpm dashboard --port 8766
```

## Module Loading Failure Debugging

### 1. Import Errors

#### Python Module Import Issues

```bash
# Check Python path
python -c "import sys; print('\n'.join(sys.path))"

# Test specific imports
python -c "from claude_mpm.services import socketio_server; print('OK')"

# Check for missing dependencies
python -c "
try:
    import socketio, aiohttp
    print('Socket.IO dependencies: OK')
except ImportError as e:
    print(f'Missing: {e}')
"
```

#### JavaScript Module Loading Issues

```javascript
// Browser console debugging
console.log('Socket.IO client loaded:', typeof io !== 'undefined');

// Check for CDN loading issues
fetch('https://cdn.socket.io/4.7.2/socket.io.min.js')
  .then(() => console.log('CDN accessible'))
  .catch(err => console.error('CDN blocked:', err));
```

**Solution**: Use local Socket.IO client files:
```html
<!-- Replace CDN with local files -->
<script src="/static/js/socket.io.min.js"></script>
```

### 2. Dynamic Import Failures

#### Server-side Dynamic Imports

```python
# Debug dynamic service loading
import importlib
try:
    module = importlib.import_module('claude_mpm.services.socketio_server')
    print(f'Module loaded: {module}')
except ImportError as e:
    print(f'Import failed: {e}')
```

#### Client-side Module Loading

```javascript
// Debug client-side loading
try {
    const SocketManager = await import('/static/js/components/socket-manager.js');
    console.log('Socket manager loaded:', SocketManager);
} catch (error) {
    console.error('Module loading failed:', error);
}
```

### 3. Dependency Resolution Issues

#### Check Service Dependencies

```bash
# Verify service container registration
python -c "
from claude_mpm.core.container import container
from claude_mpm.services.core.interfaces.communication import SocketIOServiceInterface

try:
    service = container.resolve(SocketIOServiceInterface)
    print('Service resolved successfully')
except Exception as e:
    print(f'Service resolution failed: {e}')
"
```

#### Circular Dependency Detection

```bash
# Check for circular imports
python -c "
import sys
from importlib import import_module

def check_circular_deps(module_name, visited=None):
    if visited is None:
        visited = set()
    
    if module_name in visited:
        print(f'Circular dependency detected: {module_name}')
        return
    
    visited.add(module_name)
    # Implementation continues...

check_circular_deps('claude_mpm.services.socketio_server')
"
```

## Configuration Mismatch Diagnosis

### 1. Environment Variable Conflicts

#### Check Configuration Sources

```bash
# Show all Socket.IO related environment variables
env | grep -i socket

# Show effective configuration
python -c "
from claude_mpm.config.socketio_config import SocketIOConfig
config = SocketIOConfig()
print('Host:', config.host)
print('Port:', config.port)
print('CORS:', config.cors_origins)
"
```

#### Configuration Precedence

Configuration is loaded in this order (later overrides earlier):

1. **Default values** in `socketio_config.py`
2. **Environment variables** (`SOCKETIO_*`)
3. **User configuration** in `~/.claude/config.yaml`
4. **Runtime parameters** (command line flags)

#### Fix Configuration Conflicts

```bash
# Clear environment variables
unset SOCKETIO_HOST SOCKETIO_PORT SOCKETIO_CORS

# Reset to defaults
rm ~/.claude/config.yaml
./claude-mpm dashboard
```

### 2. CORS Configuration Issues

#### Test CORS from Browser

```javascript
// Browser console test
fetch('http://localhost:8765/health', {
    method: 'GET',
    headers: {'Origin': window.location.origin}
})
.then(response => console.log('CORS OK:', response.status))
.catch(error => console.error('CORS Error:', error));
```

#### Fix CORS Issues

```python
# Update CORS configuration
# In socketio_config.py
CORS_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000", 
    "file://",  # For local HTML files
    "*"  # Allow all (development only)
]
```

### 3. SSL/TLS Configuration

#### HTTPS Dashboard with HTTP Socket.IO

```bash
# Problem: Dashboard served over HTTPS, Socket.IO over HTTP
# Browser blocks mixed content

# Solution 1: Use HTTPS for Socket.IO
export SOCKETIO_SSL=true
export SOCKETIO_CERT_PATH=/path/to/cert.pem
export SOCKETIO_KEY_PATH=/path/to/key.pem

# Solution 2: Serve dashboard over HTTP
./claude-mpm dashboard --no-ssl
```

## Debug Logging and Monitoring

### 1. Enable Debug Logging

#### Server-side Debug Logging

```bash
# Enable debug logging
export SOCKETIO_LOG_LEVEL=DEBUG
./claude-mpm dashboard

# Or in Python code
import logging
logging.getLogger('socketio').setLevel(logging.DEBUG)
logging.getLogger('engineio').setLevel(logging.DEBUG)
```

#### Client-side Debug Logging

```javascript
// Enable Socket.IO client debugging
localStorage.debug = 'socket.io-client:*';

// Or programmatically
const socket = io('http://localhost:8765', {
    debug: true,
    logger: console
});
```

### 2. Event Monitoring

#### Real-time Event Monitoring

```bash
# Monitor all Socket.IO events
tail -f ~/.claude/logs/socketio_server.log | grep -E "(emit|receive)"

# Monitor specific event types
tail -f ~/.claude/logs/socketio_server.log | grep "tool_start\|tool_stop"

# Monitor connection events
tail -f ~/.claude/logs/socketio_server.log | grep -E "(connect|disconnect|reconnect)"
```

#### Event Flow Debugging

```python
# Add event tracing in Python
@sio.event
def connect(sid, environ):
    print(f"Client connected: {sid}")
    print(f"Headers: {environ.get('HTTP_USER_AGENT', 'Unknown')}")

@sio.event  
def disconnect(sid):
    print(f"Client disconnected: {sid}")
```

```javascript
// Add event tracing in JavaScript
socket.on('connect', () => {
    console.log('Connected to Socket.IO server');
    console.log('Socket ID:', socket.id);
});

socket.on('disconnect', (reason) => {
    console.log('Disconnected:', reason);
});

// Monitor all events
const originalEmit = socket.emit;
socket.emit = function(event, ...args) {
    console.log('Emitting:', event, args);
    return originalEmit.apply(this, arguments);
};
```

### 3. Performance Monitoring

#### Memory and Resource Monitoring

```bash
# Monitor memory usage
watch -n 1 'ps aux | grep socketio | grep -v grep'

# Monitor file descriptors
watch -n 1 'lsof -p $(pgrep -f socketio_server) | wc -l'

# Monitor network connections
watch -n 1 'netstat -an | grep 8765'
```

#### Event Rate Monitoring

```python
# Add rate monitoring
import time
from collections import defaultdict

class EventRateMonitor:
    def __init__(self):
        self.event_counts = defaultdict(int)
        self.last_check = time.time()
    
    def record_event(self, event_type):
        self.event_counts[event_type] += 1
        
        # Print rates every 60 seconds
        now = time.time()
        if now - self.last_check >= 60:
            for event_type, count in self.event_counts.items():
                rate = count / 60
                print(f"{event_type}: {rate:.2f}/sec")
            self.event_counts.clear()
            self.last_check = now
```

## Automated Diagnostics

### 1. Health Check Script

```bash
#!/bin/bash
# socketio_health_check.sh

echo "=== Socket.IO Health Check ==="

# Check server process
if pgrep -f socketio_server > /dev/null; then
    echo "✓ Server process running"
else
    echo "✗ Server process not found"
    exit 1
fi

# Check port listening
if netstat -tuln | grep -q ":8765 "; then
    echo "✓ Port 8765 listening"
else
    echo "✗ Port 8765 not listening"
    exit 1
fi

# Check HTTP endpoint
if curl -s http://localhost:8765/health > /dev/null; then
    echo "✓ HTTP endpoint responding"
else
    echo "✗ HTTP endpoint not responding"
    exit 1
fi

# Check Socket.IO handshake
if curl -s "http://localhost:8765/socket.io/?transport=polling" | grep -q "0{"; then
    echo "✓ Socket.IO handshake working"
else
    echo "✗ Socket.IO handshake failed"
    exit 1
fi

echo "✓ All checks passed"
```

### 2. Connection Test Script

```python
#!/usr/bin/env python3
"""
Socket.IO connection test script.
Tests connection, event sending, and disconnection.
"""

import asyncio
import socketio

async def test_socketio_connection():
    sio = socketio.AsyncClient()
    
    @sio.event
    async def connect():
        print("✓ Connected to Socket.IO server")
        await sio.emit('test_event', {'message': 'Hello Server'})
    
    @sio.event
    async def test_response(data):
        print(f"✓ Received response: {data}")
        await sio.disconnect()
    
    @sio.event
    async def disconnect():
        print("✓ Disconnected cleanly")
    
    try:
        await sio.connect('http://localhost:8765')
        await sio.wait()
        print("✓ Connection test passed")
        return True
    except Exception as e:
        print(f"✗ Connection test failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_socketio_connection())
    exit(0 if success else 1)
```

### 3. Performance Benchmark Script

```python
#!/usr/bin/env python3
"""
Socket.IO performance benchmark.
Tests event throughput and latency.
"""

import asyncio
import time
import statistics
import socketio

class SocketIOBenchmark:
    def __init__(self):
        self.latencies = []
        self.events_sent = 0
        self.events_received = 0
    
    async def benchmark_throughput(self, events_count=1000):
        sio = socketio.AsyncClient()
        
        @sio.event
        async def connect():
            start_time = time.time()
            
            for i in range(events_count):
                await sio.emit('benchmark_event', {
                    'id': i,
                    'timestamp': time.time()
                })
                self.events_sent += 1
            
            # Wait for all responses
            while self.events_received < events_count:
                await asyncio.sleep(0.01)
            
            end_time = time.time()
            duration = end_time - start_time
            throughput = events_count / duration
            
            print(f"✓ Throughput: {throughput:.2f} events/second")
            print(f"✓ Average latency: {statistics.mean(self.latencies):.2f}ms")
            print(f"✓ Max latency: {max(self.latencies):.2f}ms")
            
            await sio.disconnect()
        
        @sio.event
        async def benchmark_response(data):
            latency = (time.time() - data['timestamp']) * 1000
            self.latencies.append(latency)
            self.events_received += 1
        
        await sio.connect('http://localhost:8765')
        await sio.wait()

if __name__ == "__main__":
    benchmark = SocketIOBenchmark()
    asyncio.run(benchmark.benchmark_throughput())
```

## Recovery Procedures

### 1. Graceful Server Restart

```bash
#!/bin/bash
# graceful_socketio_restart.sh

echo "Starting graceful Socket.IO server restart..."

# Get current server PID
PID=$(pgrep -f socketio_server)

if [ -n "$PID" ]; then
    echo "Sending SIGTERM to PID $PID..."
    kill -TERM $PID
    
    # Wait up to 10 seconds for graceful shutdown
    for i in {1..10}; do
        if ! kill -0 $PID 2>/dev/null; then
            echo "Server shut down gracefully"
            break
        fi
        sleep 1
    done
    
    # Force kill if still running
    if kill -0 $PID 2>/dev/null; then
        echo "Force killing server..."
        kill -KILL $PID
    fi
fi

# Start new server
echo "Starting new server..."
./claude-mpm dashboard --daemon

# Wait for server to be ready
for i in {1..30}; do
    if curl -s http://localhost:8765/health > /dev/null; then
        echo "Server restarted successfully"
        exit 0
    fi
    sleep 1
done

echo "Server restart failed"
exit 1
```

### 2. Emergency Recovery

```bash
#!/bin/bash
# emergency_socketio_recovery.sh

echo "=== Emergency Socket.IO Recovery ==="

# Kill all Python processes that might be Socket.IO servers
pkill -f "socketio.*server"
pkill -f "claude.*dashboard"

# Clear any stale PID files
rm -f ~/.claude/socketio.pid
rm -f /tmp/socketio_*.pid

# Clear socket files
rm -f /tmp/socket.io.*

# Reset port bindings
fuser -k 8765/tcp 2>/dev/null

# Clear any zombie processes
ps aux | grep -i defunct | awk '{print $2}' | xargs kill -9 2>/dev/null

# Restart network if necessary (Linux only)
# sudo systemctl restart networking

# Start clean server
sleep 2
./claude-mpm dashboard --force-restart

echo "Emergency recovery completed"
```

### 3. Configuration Reset

```bash
#!/bin/bash
# reset_socketio_config.sh

echo "Resetting Socket.IO configuration..."

# Backup existing config
if [ -f ~/.claude/config.yaml ]; then
    cp ~/.claude/config.yaml ~/.claude/config.yaml.backup
    echo "Backed up existing config"
fi

# Clear environment variables
unset $(env | grep -E '^SOCKETIO_' | cut -d= -f1)

# Reset to default configuration
cat > ~/.claude/config.yaml << EOF
socketio:
  host: localhost
  port: 8765
  debug: false
  cors_origins: ["*"]
  heartbeat_interval: 60
  max_buffer_size: 1000
EOF

echo "Configuration reset to defaults"
./claude-mpm dashboard restart
```

## Escalation Procedures

### When to Escalate

Escalate to development team when:

1. **Server consistently fails to start** after configuration reset
2. **Performance severely degraded** (< 10 events/second)
3. **Memory leaks detected** (continuous growth over 500MB)
4. **Security issues identified** (unauthorized access, data leaks)
5. **Multiple simultaneous failures** across different components

### Information to Collect

Before escalating, collect:

```bash
# System information
uname -a > debug_info.txt
python --version >> debug_info.txt
pip list | grep -E "(socketio|aiohttp)" >> debug_info.txt

# Server logs (last 500 lines)
tail -500 ~/.claude/logs/socketio_server.log >> debug_info.txt

# Process information
ps aux | grep -E "(python|socketio)" >> debug_info.txt
netstat -tuln | grep 8765 >> debug_info.txt
lsof -i :8765 >> debug_info.txt

# Configuration
env | grep -E "(SOCKETIO|CLAUDE)" >> debug_info.txt
cat ~/.claude/config.yaml >> debug_info.txt

# Performance data
top -b -n 1 | head -20 >> debug_info.txt
free -h >> debug_info.txt
df -h >> debug_info.txt
```

### Emergency Contacts

- **Development Team**: Create GitHub issue with `socketio` and `urgent` labels
- **Infrastructure Team**: For server/network issues
- **Security Team**: For security-related issues

This troubleshooting guide should help resolve 95% of Socket.IO server issues. For complex problems, use the diagnostic tools and escalation procedures provided.