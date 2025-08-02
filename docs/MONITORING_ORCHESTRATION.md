# Claude MPM Monitoring Orchestration Guide

## Overview

This guide orchestrates the ongoing development and maintenance of the Claude MPM monitoring system, including the Socket.IO dashboard, WebSocket server, and hook integration.

## Current Architecture

### Components
1. **WebSocket Server** (`src/claude_mpm/services/websocket_server.py`)
   - Handles real-time event broadcasting
   - Manages session lifecycle
   - Provides git branch detection

2. **Socket.IO Server** (`src/claude_mpm/services/socketio_server.py`)
   - Enhanced monitoring with namespace support
   - Dashboard integration
   - Event history management

3. **Hook Handler** (`src/claude_mpm/hooks/claude_hooks/hook_handler.py`)
   - Captures Claude events
   - Enriches event data with context
   - Broadcasts to monitoring servers

4. **Dashboard** (`src/claude_mpm/web/templates/index.html`, served at `/dashboard`)
   - Real-time event visualization
   - Multi-tab interface (Events, Agents, Tools, Files)
   - Module viewer for detailed analysis
   - Session management

## Development Workflow

### 1. Testing Changes
```bash
# Set environment to prevent multiple browser windows
export CLAUDE_MPM_NO_BROWSER=1

# Test specific features
python scripts/test_footer.py
python scripts/test_all_agents_hello.py
python scripts/test_browser_control.py

# Full integration test
python scripts/run_all_socketio_tests.py
```

### 2. Manual Testing
```bash
# Start monitor with auto-connect
claude-mpm run --monitor -i "test prompt"

# Open dashboard manually
open http://localhost:8765/dashboard?autoconnect=true&port=8765
```

### 3. Debugging
```bash
# Enable verbose logging
export CLAUDE_MPM_LOG_LEVEL=DEBUG

# Test specific components
python scripts/diagnostic_socketio_server_monitor.py
python scripts/test_complete_socketio_flow.py
```

## Key Features Status

### ✅ Completed
- Compact header with 3-row layout
- Session selection dropdown
- Split view with module viewer
- Tabbed interface (Events, Agents, Tools, Files)
- Event-driven data derivation
- Tool operation consolidation with duration
- Full JSON display for debugging
- Browser control via environment variable
- Footer with session info, directory, and git branch

### 🚧 In Progress
- Performance optimization for large event volumes
- Event filtering improvements
- Enhanced search capabilities

### 📋 Planned
- Data persistence and export
- Custom view extensions
- Event replay functionality
- Multi-session comparison
- Performance metrics dashboard

## Common Tasks

### Adding New Event Types

1. Update hook handler to capture new event:
```python
# In hook_handler.py
if hook_type == "new_hook_type":
    enriched_data = {
        "hook_type": hook_type,
        "new_field": data.get("new_field"),
        # ... additional fields
    }
```

2. Add event handling in dashboard:
```javascript
// In dashboard template (src/claude_mpm/web/templates/index.html)
if (eventData.type === 'hook.new_type') {
    // Custom handling
}
```

3. Update event classification:
```javascript
const eventClass = getEventClass(eventData.type);
// Add new classification if needed
```

### Modifying Dashboard Layout

1. Update HTML structure in appropriate section
2. Adjust CSS for new elements
3. Update JavaScript event handlers
4. Test responsive behavior

### Performance Optimization

1. **Event Batching**: Group rapid events before rendering
2. **Virtual Scrolling**: Implement for large event lists
3. **Debouncing**: Add for search and filter operations
4. **Memory Management**: Limit event history size

## Monitoring Best Practices

### 1. Event Design
- Keep event payloads concise
- Include essential context (session_id, timestamp, agent)
- Use consistent naming conventions
- Avoid sensitive data in events

### 2. Dashboard Usage
- Use filters to focus on specific event types
- Leverage module viewer for deep analysis
- Monitor performance impact
- Export important sessions

### 3. Debugging
- Check Socket.IO connection status
- Verify event flow with test scripts
- Use browser DevTools for dashboard issues
- Enable debug logging when needed

## Troubleshooting

### Common Issues

1. **No events appearing**
   - Check Socket.IO server is running
   - Verify port configuration
   - Check browser console for errors

2. **Performance degradation**
   - Clear old events
   - Reduce event history limit
   - Check for memory leaks

3. **Connection issues**
   - Verify firewall settings
   - Check port availability
   - Test with diagnostic scripts

## Extension Points

### Custom Event Handlers
Add to dashboard JavaScript:
```javascript
socket.on('custom_event', (data) => {
    // Handle custom event
    addEvent({
        type: 'custom.event',
        timestamp: new Date().toISOString(),
        data: data
    });
});
```

### Custom Tabs
1. Add tab button in HTML
2. Create content container
3. Add render function
4. Update tab switching logic

### Custom Filters
Extend the filtering system:
```javascript
function customFilter(event) {
    // Return true to include event
    return event.data?.customField === 'value';
}
```

## Maintenance Schedule

### Daily
- Monitor error rates
- Check connection stability
- Review performance metrics

### Weekly
- Clean up old test data
- Update documentation
- Review and optimize slow queries

### Monthly
- Performance audit
- Security review
- Feature planning

## Next Steps

1. **Immediate**: Implement event export functionality
2. **Short-term**: Add performance monitoring dashboard
3. **Long-term**: Build plugin system for custom analyzers

## Resources

- [Socket.IO Documentation](https://socket.io/docs/)
- [WebSocket API](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket)
- [Claude MPM Hook System](../hooks/README.md)
- [Dashboard Design Patterns](https://www.nngroup.com/articles/dashboard-design/)