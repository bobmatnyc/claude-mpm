# Dashboard Implementation

This document details the implementation of the Claude MPM Dashboard web interface.

## Overview

The dashboard is a single-page web application that provides real-time monitoring of Claude Code sessions through WebSocket connections.

**Location**: `scripts/claude_mpm_dashboard.html`

## Architecture

### Technology Stack

- **Frontend**: Vanilla JavaScript (no framework dependencies)
- **Styling**: Inline CSS with dark theme
- **Communication**: WebSocket API
- **Charts**: Chart.js for visualizations

### Component Structure

```
Dashboard
├── Header (Title, Status, Controls)
├── Main Content
│   ├── Session Info Panel
│   ├── Event Stream
│   ├── Statistics
│   └── Tool Usage Chart
└── Event History Modal
```

## Key Features

### 1. Real-time Event Stream

```javascript
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    
    switch(data.type) {
        case 'hook.user_prompt':
            handleUserPrompt(data.data);
            break;
        case 'hook.pre_tool_use':
            handlePreToolUse(data.data);
            break;
        case 'hook.post_tool_use':
            handlePostToolUse(data.data);
            break;
        // ... other event types
    }
};
```

### 2. Session Management

```javascript
// Extract session ID from URL
const urlParams = new URLSearchParams(window.location.search);
const sessionId = urlParams.get('session') || 'global';

// Register with server
ws.send(JSON.stringify({
    type: 'register',
    session_id: sessionId
}));
```

### 3. Auto-reconnection

```javascript
function connect() {
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.close();
    }
    
    ws = new WebSocket(`ws://127.0.0.1:${wsPort}`);
    
    ws.onclose = () => {
        // Auto-reconnect after 2 seconds
        setTimeout(connect, 2000);
    };
}
```

## Event Handling

### Event Types

1. **Hook Events**
   - `hook.user_prompt` - User input
   - `hook.pre_tool_use` - Before tool execution
   - `hook.post_tool_use` - After tool execution

2. **System Events**
   - `system.status` - Server status
   - `system.heartbeat` - Keep-alive
   - `session.start` - New session
   - `session.end` - Session ended

3. **Claude Events**
   - `claude.status` - Claude process status
   - `claude.output` - Console output
   - `agent.delegation` - Agent tasks
   - `todo.update` - Todo list changes

### Event Display

```javascript
function addEventToStream(type, message, details = {}) {
    const eventEl = document.createElement('div');
    eventEl.className = `event event-${type}`;
    
    const timeEl = document.createElement('span');
    timeEl.className = 'event-time';
    timeEl.textContent = new Date().toLocaleTimeString();
    
    const messageEl = document.createElement('span');
    messageEl.className = 'event-message';
    messageEl.textContent = message;
    
    eventEl.appendChild(timeEl);
    eventEl.appendChild(messageEl);
    
    eventStream.insertBefore(eventEl, eventStream.firstChild);
}
```

## UI Components

### Status Indicator

```javascript
const statusEl = document.getElementById('status');
const indicatorEl = document.getElementById('indicator');

// Update connection status
if (connected) {
    statusEl.textContent = 'Connected';
    indicatorEl.classList.add('connected');
} else {
    statusEl.textContent = 'Disconnected';
    indicatorEl.classList.remove('connected');
}
```

### Statistics Panel

```javascript
const stats = {
    totalEvents: 0,
    promptCount: 0,
    toolUseCount: 0,
    errorCount: 0
};

function updateStatistics() {
    document.getElementById('totalEvents').textContent = stats.totalEvents;
    document.getElementById('promptCount').textContent = stats.promptCount;
    document.getElementById('toolCount').textContent = stats.toolUseCount;
    document.getElementById('errorCount').textContent = stats.errorCount;
}
```

### Tool Usage Chart

```javascript
const toolChart = new Chart(ctx, {
    type: 'bar',
    data: {
        labels: Object.keys(toolUsage),
        datasets: [{
            label: 'Tool Usage',
            data: Object.values(toolUsage),
            backgroundColor: 'rgba(75, 192, 192, 0.6)'
        }]
    },
    options: {
        responsive: true,
        maintainAspectRatio: false
    }
});
```

## Styling

### Dark Theme

```css
:root {
    --bg-primary: #1a1a1a;
    --bg-secondary: #2d2d2d;
    --text-primary: #e0e0e0;
    --text-secondary: #b0b0b0;
    --accent: #61dafb;
    --success: #4caf50;
    --error: #f44336;
    --warning: #ff9800;
}

body {
    background-color: var(--bg-primary);
    color: var(--text-primary);
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}
```

### Responsive Design

```css
@media (max-width: 768px) {
    .dashboard {
        grid-template-columns: 1fr;
    }
    
    .stats-grid {
        grid-template-columns: 1fr 1fr;
    }
}
```

## Performance Optimizations

### 1. Event Throttling

```javascript
let eventBuffer = [];
let flushTimeout;

function bufferEvent(event) {
    eventBuffer.push(event);
    
    if (!flushTimeout) {
        flushTimeout = setTimeout(flushEvents, 100);
    }
}

function flushEvents() {
    // Process all buffered events
    eventBuffer.forEach(processEvent);
    eventBuffer = [];
    flushTimeout = null;
}
```

### 2. DOM Optimization

```javascript
// Limit event history
const MAX_EVENTS = 1000;

function pruneEventHistory() {
    while (eventStream.children.length > MAX_EVENTS) {
        eventStream.removeChild(eventStream.lastChild);
    }
}
```

### 3. Memory Management

```javascript
// Clear old data periodically
setInterval(() => {
    // Prune event history
    pruneEventHistory();
    
    // Clear old chart data
    if (chartData.labels.length > 100) {
        chartData.labels = chartData.labels.slice(-50);
        chartData.datasets[0].data = chartData.datasets[0].data.slice(-50);
        chart.update();
    }
}, 60000); // Every minute
```

## URL Parameters

### Supported Parameters

1. **port** - WebSocket server port (default: 8765)
   ```
   ?port=8766
   ```

2. **session** - Session ID for filtering
   ```
   ?session=abc123
   ```

3. **theme** - Color theme (future)
   ```
   ?theme=light
   ```

### Example URLs

```
# Default connection
file:///path/to/dashboard.html

# Custom port
file:///path/to/dashboard.html?port=8766

# Session filtering
file:///path/to/dashboard.html?session=7988f55b

# Multiple parameters
file:///path/to/dashboard.html?port=8765&session=abc123
```

## Error Handling

### Connection Errors

```javascript
ws.onerror = (error) => {
    console.error('WebSocket error:', error);
    addSystemMessage('WebSocket connection error', 'error');
    
    // Update UI
    statusEl.textContent = 'Error';
    indicatorEl.classList.add('error');
};
```

### Invalid Messages

```javascript
ws.onmessage = (event) => {
    try {
        const data = JSON.parse(event.data);
        handleMessage(data);
    } catch (e) {
        console.error('Invalid message:', event.data);
        stats.errorCount++;
    }
};
```

## Debugging

### Console Logging

```javascript
// Enable debug mode
const DEBUG = localStorage.getItem('debug') === 'true';

function debug(...args) {
    if (DEBUG) {
        console.log('[Dashboard]', ...args);
    }
}
```

### Event Inspector

```javascript
// Right-click on event to inspect
eventEl.addEventListener('contextmenu', (e) => {
    e.preventDefault();
    console.log('Event details:', eventData);
});
```

## Future Enhancements

1. **Filtering Options**
   - Filter by event type
   - Search in event history
   - Time range selection

2. **Export Features**
   - Export event history
   - Save session transcript
   - Generate reports

3. **Advanced Visualizations**
   - Timeline view
   - Dependency graphs
   - Performance metrics

4. **Multi-session Support**
   - Tab interface
   - Session comparison
   - Aggregate statistics