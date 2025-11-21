# Claude MPM Dashboard 2.0

Modern Svelte 5-based dashboard for Claude Multi-Agent Project Manager with real-time event monitoring via Socket.IO.

## Features

- **Svelte 5 Runes API**: Modern reactive state management with `$state`, `$derived`, and `$effect`
- **Real-time Events**: Socket.IO integration for live Claude Code hook events
- **Event Timeline**: Display and inspect incoming events with expandable details
- **Connection Status**: Visual connection indicator with auto-reconnect
- **Responsive Layout**: Clean two-column layout with navigation sidebar
- **Dark Theme**: Modern dark UI optimized for long-term use

## Technology Stack

- **Svelte 5** - Modern reactive UI framework with Runes API
- **Vite** - Fast build tool and dev server
- **Socket.IO Client v4.7.5** - Real-time WebSocket communication
- **Modern CSS** - Grid/Flexbox layout with smooth transitions

## Prerequisites

- Node.js 18+ and npm
- Claude MPM monitor server running on port 8765

## Setup

1. **Install dependencies**:
   ```bash
   cd src/claude_mpm/dashboard2
   npm install
   ```

2. **Start development server**:
   ```bash
   npm run dev
   ```
   The dev server will start at `http://localhost:5173`

3. **Build for production**:
   ```bash
   npm run build
   ```
   Output will be in `dist/` directory

## Configuration

### Socket.IO Connection

By default, the dashboard connects to `http://localhost:8765`. To change this, edit:

```javascript
// src/stores/socket.svelte.js
const DEFAULT_PORT = 8765;
const DEFAULT_HOST = 'localhost';
```

### Event Buffer Size

Events are limited to the last 1000 events. To adjust:

```javascript
// src/stores/events.svelte.js
const MAX_EVENTS = 1000;
```

## Project Structure

```
dashboard2/
├── package.json              # Dependencies and scripts
├── vite.config.js           # Vite build configuration
├── public/
│   └── index.html           # HTML template
├── src/
│   ├── main.js              # Entry point
│   ├── App.svelte           # Main app component
│   ├── components/
│   │   ├── Header.svelte    # Top header with connection status
│   │   ├── Sidebar.svelte   # Navigation sidebar
│   │   ├── MainContent.svelte  # Content area switcher
│   │   └── tabs/
│   │       └── EventsTab.svelte  # Events timeline tab
│   ├── stores/
│   │   ├── socket.svelte.js  # Socket.IO connection store
│   │   └── events.svelte.js  # Events buffer store
│   └── lib/
│       └── socketio.js      # Socket.IO client wrapper
└── dist/                    # Build output (generated)
```

## Architecture

### Svelte 5 Runes

This dashboard uses Svelte 5's modern Runes API:

- **`$state()`**: Reactive local state
- **`$derived()`**: Computed values that update automatically
- **`$effect()`**: Side effects with automatic cleanup
- **`$bindable()`**: Two-way binding for component props

### Socket.IO Events

The dashboard listens for these Socket.IO events:

- **`claude_event`**: Main event channel for Claude Code hook events
- **`heartbeat`**: Server heartbeat every 3 minutes
- **Connection events**: `connect`, `disconnect`, `reconnect_attempt`, etc.

### Event Format

Events received from Socket.IO have this structure:

```javascript
{
  "source": "hook" | "system" | "api",
  "type": "hook" | "session" | "agent" | "tool",
  "subtype": "user_prompt" | "pre_tool" | "post_tool" | "subagent_start" | "subagent_stop",
  "timestamp": "2025-11-20T12:34:56.789Z",
  "session_id": "session-uuid-here",
  "data": {
    // Event-specific data
  }
}
```

## Development

### Running Dev Server

```bash
npm run dev
```

Features:
- Hot Module Replacement (HMR)
- Instant updates on file changes
- Source maps for debugging

### Building for Production

```bash
npm run build
```

Outputs optimized, minified bundle to `dist/`:
- `index.html` - Main HTML file
- `assets/*.js` - Bundled JavaScript
- `assets/*.css` - Bundled CSS

### Preview Production Build

```bash
npm run preview
```

Serves the production build locally for testing.

## Integration with Flask

The Flask server will serve the built Svelte app from the `dist/` directory:

```python
@app.route('/dashboard2')
def dashboard2():
    return send_from_directory('dashboard2/dist', 'index.html')

@app.route('/dashboard2/<path:path>')
def dashboard2_assets(path):
    return send_from_directory('dashboard2/dist', path)
```

## Future Enhancements

### Implemented
- ✅ Events tab with real-time display
- ✅ Socket.IO connection management
- ✅ Event filtering and clearing
- ✅ Connection status indicator
- ✅ Auto-scroll to newest events

### Planned
- 🔲 Agents tab - Monitor active agents
- 🔲 Files tab - Track file operations
- 🔲 Tools tab - View tool executions
- 🔲 Activity tab - System metrics and analytics
- 🔲 Event search and advanced filtering
- 🔲 Export events to JSON/CSV
- 🔲 Customizable event notifications
- 🔲 Dark/light theme toggle
- 🔲 Configurable Socket.IO connection settings

## Troubleshooting

### Socket.IO Connection Fails

1. **Check server is running**:
   ```bash
   curl http://localhost:8765/health
   ```

2. **Check port availability**:
   ```bash
   lsof -i :8765
   ```

3. **Check browser console** for connection errors

### Events Not Appearing

1. **Verify Socket.IO connection status** in header (should show "Connected")
2. **Check browser console** for incoming events
3. **Trigger a Claude Code event** to generate test data
4. **Check Socket.IO server logs** for event emissions

### Build Errors

1. **Clear node_modules and reinstall**:
   ```bash
   rm -rf node_modules package-lock.json
   npm install
   ```

2. **Check Node.js version** (requires 18+):
   ```bash
   node --version
   ```

## License

Part of Claude MPM project.
