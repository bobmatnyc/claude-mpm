# Monitoring Dashboard

Technical documentation for the real-time monitoring dashboard.

For user-facing monitoring documentation, see **[Monitoring Guide](../../guides/monitoring.md)**.

## Overview

The monitoring dashboard provides real-time observability through:

- WebSocket-based event streaming
- Live agent activity tracking
- File operation monitoring
- Session state synchronization
- Performance metrics

## Architecture

### Components

**Backend:**
- Flask web server
- Socket.IO for WebSocket communication
- Event broadcasting system
- Metrics collection

**Frontend:**
- Real-time dashboard UI
- WebSocket client
- Live data visualization
- Performance graphs

### Technology Stack

- **Flask**: Web framework
- **Socket.IO**: Real-time communication
- **WebSocket**: Bidirectional communication
- **JavaScript**: Frontend interactivity

## Starting the Dashboard

```bash
# Start with monitoring
claude-mpm run --monitor

# Custom port
claude-mpm run --monitor --port 5001

# Dashboard opens at http://localhost:5000
```

## WebSocket Protocol

### Events

**Outgoing (Server → Client):**
```javascript
// Agent activity
{
  "event": "agent_activity",
  "data": {
    "agent": "python-engineer",
    "action": "invoked",
    "timestamp": "2025-11-15T10:30:00Z"
  }
}

// File operations
{
  "event": "file_operation",
  "data": {
    "file": "/path/to/file.py",
    "operation": "write",
    "size": 1024
  }
}

// Session updates
{
  "event": "session_update",
  "data": {
    "session_id": "abc123",
    "token_usage": 45000,
    "context_percentage": 0.225
  }
}
```

**Incoming (Client → Server):**
```javascript
// Subscribe to events
{
  "event": "subscribe",
  "data": {
    "events": ["agent_activity", "file_operation"]
  }
}

// Request current state
{
  "event": "get_state",
  "data": {}
}
```

## API Endpoints

### Health Check

```
GET /health

Response:
{
  "status": "healthy",
  "uptime": 3600,
  "connections": 2
}
```

### Status

```
GET /status

Response:
{
  "agents": "healthy",
  "mcp_gateway": "healthy",
  "websocket": "healthy",
  "metrics": {
    "active_agents": 5,
    "total_requests": 150
  }
}
```

### Agents

```
GET /agents

Response:
{
  "agents": [
    {
      "name": "pm",
      "status": "active",
      "invocations": 25
    }
  ]
}
```

## Configuration

```yaml
# In configuration.yaml
monitoring:
  enabled: true
  port: 5000
  host: "localhost"
  websocket:
    enabled: true
    max_connections: 10
  metrics:
    enabled: true
    interval: 5
  logging:
    level: INFO
```

## Development

### Running Locally

```bash
# Install with dev dependencies
pip install -e ".[dev,monitor]"

# Start dashboard
python -m claude_mpm.services.communication.dashboard

# Or via make
make run-dashboard
```

### Testing

```bash
# Test dashboard endpoints
pytest tests/test_dashboard.py

# Test WebSocket
pytest tests/test_websocket.py

# Manual testing
curl http://localhost:5000/health
```

### Adding Custom Events

```python
from claude_mpm.services.communication import DashboardService

# Get dashboard service
dashboard = container.get(DashboardService)

# Emit custom event
dashboard.emit('custom_event', {
    'message': 'Custom data',
    'timestamp': datetime.now().isoformat()
})
```

## Security

### Access Control

- Binds to localhost by default (not exposed externally)
- Use reverse proxy for remote access
- Enable authentication if exposed
- Use HTTPS in production

### Data Privacy

- No sensitive data in logs
- File contents not transmitted
- Token usage tracked, not content
- User data encrypted at rest

## Performance

### Optimization

- Connection pooling for WebSocket
- Event batching for high throughput
- Metric aggregation
- Automatic reconnection

### Resource Usage

- Minimal CPU overhead (< 5%)
- Memory: ~50MB for dashboard
- Network: ~10KB/s for typical usage

## Troubleshooting

### Dashboard Won't Start

```bash
# Check port availability
lsof -i :5000

# Try different port
claude-mpm run --monitor --port 5001

# Check logs
tail -f ~/.claude-mpm/logs/mpm.log
```

### WebSocket Connection Failed

```bash
# Check WebSocket enabled
grep websocket ~/.claude-mpm/configuration.yaml

# Test connection
wscat -c ws://localhost:5000/socket.io
```

## See Also

- **[Monitoring Guide](../../guides/monitoring.md)** - User-facing documentation
- **[Architecture](../ARCHITECTURE.md)** - System architecture
- **[API Reference](../api-reference.md)** - API documentation
- **[User Guide](../../user/user-guide.md)** - End-user features

---

**For user-facing monitoring documentation**: See [../../guides/monitoring.md](../../guides/monitoring.md)
