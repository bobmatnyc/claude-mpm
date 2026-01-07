# Monitoring Guide

Real-time monitoring and observability for Claude MPM sessions.

## Quick Start

```bash
# Start with monitoring dashboard
claude-mpm run --monitor

# Dashboard opens automatically at http://localhost:5000
```

## Overview

The monitoring dashboard provides real-time insights into:

- 📊 **Agent Activity**: Live tracking of agent invocations and collaboration
- 📁 **File Operations**: Monitor file reads, writes, and modifications
- 🔄 **Session Management**: Track session state and context usage
- ⚡ **Performance Metrics**: Response times, token usage, and throughput

## Dashboard Features

### Agent Activity View

Real-time visualization of agent interactions:

- Current active agents
- Agent invocation history
- Task delegation patterns
- Agent collaboration graph

### File Operations View

Track all file system operations:

- Files read and written
- Modification timestamps
- Operation types (read/write/delete)
- File size changes

### Session State View

Monitor session health and context:

- Current session ID
- Active agent count
- Token usage and limits
- Context window percentage
- Resume log triggers

### Performance Metrics

System performance indicators:

- Average response time
- Request throughput
- Memory usage
- CPU utilization
- API call rates

## WebSocket Events

The dashboard uses WebSocket for real-time updates:

### Event Types

```javascript
// Agent activity
socket.on('agent_activity', (data) => {
  // data.agent: Agent name
  // data.action: Agent action
  // data.timestamp: Event timestamp
});

// File operations
socket.on('file_operation', (data) => {
  // data.file: File path
  // data.operation: read/write/delete
  // data.size: File size
});

// Session updates
socket.on('session_update', (data) => {
  // data.session_id: Current session
  // data.token_usage: Token count
  // data.context_percentage: Usage percentage
});

// Health status
socket.on('health_status', (data) => {
  // data.status: healthy/degraded/unhealthy
  // data.services: Service statuses
});
```

See [../developer/11-dashboard/README.md](../developer/11-dashboard/README.md) for technical details.

## Configuration

Configure monitoring in `configuration.yaml`:

```yaml
monitoring:
  enabled: true
  port: 5000
  host: "localhost"
  websocket:
    enabled: true
    max_connections: 10
  metrics:
    enabled: true
    interval: 5  # seconds
```

## Health Checks

### Dashboard Health

```bash
# Check dashboard status
curl http://localhost:5000/health

# Response:
# {
#   "status": "healthy",
#   "uptime": 3600,
#   "connections": 2
# }
```

### Service Health

```bash
# Check all services
curl http://localhost:5000/status

# Response:
# {
#   "agents": "healthy",
#   "mcp_gateway": "healthy",
#   "websocket": "healthy"
# }
```

## Performance Monitoring

### Response Time Tracking

Monitor agent response times:

- Average response time per agent
- 95th percentile latency
- Slowest operations
- Response time trends

### Token Usage Tracking

Monitor context window usage:

- Current token count
- Usage percentage
- Thresholds (70%/85%/95%)
- Resume log triggers

### Resource Monitoring

Track system resources:

- Memory usage (process)
- CPU utilization
- File descriptor count
- Network connections

## Alerts and Notifications

### Context Window Alerts

Graduated warnings at threshold levels:

- **70% (Caution)**: Plan for session wrap-up (60k token buffer)
- **85% (Warning)**: Strong warning to wrap up (30k token buffer)
- **95% (Critical)**: Stop new work, generate resume log (10k token buffer)

### Health Alerts

Monitor service health:

- Agent failures
- MCP service degradation
- WebSocket connection issues
- Resource exhaustion

## Logging

### Log Levels

Configure logging verbosity:

```yaml
logging:
  level: INFO  # DEBUG, INFO, WARNING, ERROR, CRITICAL
  file: ~/.claude-mpm/logs/mpm.log
  max_size: 10485760  # 10MB
  backup_count: 5
```

### Log Categories

- `agent`: Agent activity logs
- `mcp`: MCP gateway logs
- `websocket`: WebSocket connection logs
- `session`: Session management logs
- `performance`: Performance metrics logs

## Troubleshooting Monitoring

### Dashboard Won't Start

```bash
# Check port availability
lsof -i :5000

# Try different port
claude-mpm run --monitor --port 5001

# Check logs
tail -f ~/.claude-mpm/logs/mpm.log
```

### WebSocket Connection Issues

```bash
# Verify WebSocket is enabled
grep websocket ~/.claude-mpm/configuration.yaml

# Check firewall rules
sudo ufw status

# Test connection
wscat -c ws://localhost:5000/socket.io
```

### Missing Metrics

```bash
# Enable metrics in configuration
cat >> ~/.claude-mpm/configuration.yaml << EOF
monitoring:
  metrics:
    enabled: true
    interval: 5
EOF

# Restart with monitoring
claude-mpm run --monitor
```

See [../user/troubleshooting.md](../user/troubleshooting.md) for more solutions.

## Advanced Monitoring

### Custom Metrics

Add custom metrics via hook system:

```python
from claude_mpm.hooks import HookManager

@hook_manager.register("post_tool_use")
def track_custom_metric(context):
    # Track custom metric
    metric_tracker.record("custom_metric", value)
    return HookResult(success=True)
```

### Integration with External Tools

Export metrics to external monitoring:

- Prometheus (metrics export)
- Grafana (visualization)
- Datadog (APM)
- New Relic (tracing)

### Distributed Tracing

Enable distributed tracing:

```yaml
monitoring:
  tracing:
    enabled: true
    exporter: jaeger
    endpoint: http://localhost:14268/api/traces
```

## Security Considerations

### Dashboard Access

- Bind to localhost only (default)
- Use reverse proxy for remote access
- Enable authentication if exposed
- Use HTTPS for production

### Data Privacy

- Sensitive data not logged
- File contents not transmitted
- Token limits respected
- User data encrypted at rest

## See Also

- **[Dashboard Technical Guide](../developer/11-dashboard/README.md)** - Implementation details
- **[User Guide](../user/user-guide.md)** - End-user features
- **[Resume Logs](../user/resume-logs.md)** - Context management
- **[Troubleshooting](../user/troubleshooting.md)** - Common issues
- **[Configuration](../configuration/reference.md)** - Configuration options

---

**For technical dashboard documentation**: See [../developer/11-dashboard/README.md](../developer/11-dashboard/README.md)
