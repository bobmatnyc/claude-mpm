# Claude MPM Web Dashboard

This directory contains the modular web dashboard for Claude MPM monitoring and management.

## Structure

```
src/claude_mpm/web/
├── static/
│   ├── css/
│   │   └── dashboard.css          # Main stylesheet
│   └── js/
│       ├── socket-client.js       # Socket.IO connection management
│       ├── dashboard.js          # Main dashboard application
│       └── components/
│           ├── event-viewer.js    # Event display and filtering
│           ├── module-viewer.js   # Event detail viewer
│           └── session-manager.js # Session management
├── templates/
│   └── index.html               # Main dashboard HTML
├── index.html                   # Root index with redirect
├── test_dashboard.html          # Test version for verification
└── README.md                    # This file
```

## Components

### SocketClient (`socket-client.js`)
- Manages WebSocket connections to the Claude MPM server
- Handles event reception and processing
- Provides callbacks for connection state changes
- Maintains event history and session tracking

### EventViewer (`components/event-viewer.js`)
- Displays events in a filterable list
- Supports search, type filtering, and session filtering
- Handles event selection and keyboard navigation
- Updates metrics display (total events, events per minute, etc.)

### ModuleViewer (`components/module-viewer.js`)
- Shows detailed information about selected events
- Provides structured views for different event types
- Displays raw JSON data for debugging
- Organizes events by class/category

### SessionManager (`components/session-manager.js`)
- Manages session selection and filtering
- Updates session dropdown with available sessions
- Tracks current active session
- Updates footer information

### Dashboard (`dashboard.js`)
- Main application coordinator
- Handles tab switching between Events, Agents, Tools, and Files
- Manages component interactions
- Provides global functions for backward compatibility

## Features

### File-Centric Files Tab
The Files tab now shows a file-centric view where:
- Each file appears only once in the list
- Files show read/write icons based on operations performed
- Most recently accessed files appear at the bottom
- Clicking a file shows all operations performed on it with timestamps and agent information

### Tab Organization
- **Events**: All events with filtering and search
- **Agents**: Agent-specific events and operations
- **Tools**: Tool usage and parameters
- **Files**: File operations organized by file path

### Enhanced Event Details
- Structured views for different event types
- Todo checklists with status indicators
- Agent and tool information
- Session tracking and filtering

## Usage

### Development
For development and testing, use `test_dashboard.html` which includes module verification.

### Production
Use `templates/dashboard.html` as the main template, ensuring all static files are served correctly.

### Integration
The dashboard can be integrated into a Flask/FastAPI application by serving the static files and using the template.

## Migration from Original

The original monolithic `claude_mpm_socketio_dashboard.html` has been replaced with a modular structure:

1. **CSS**: Extracted to `static/css/dashboard.css`
2. **JavaScript**: Split into logical modules in `static/js/`
3. **HTML**: Clean template in `templates/dashboard.html`

All original functionality has been preserved while improving:
- Code organization and maintainability
- Module reusability
- Easier debugging and development
- Better separation of concerns

## Backward Compatibility

Global functions are maintained for compatibility:
- `connectSocket()`
- `disconnectSocket()`
- `clearEvents()`
- `exportEvents()`
- `clearSelection()`
- `switchTab(tabName)`

## Browser Support

Requires modern browsers with support for:
- ES6 Classes
- Fetch API
- Custom Events
- CSS Grid/Flexbox
- Socket.IO 4.x