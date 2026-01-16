# MPM Commander Web UI

Minimal web interface for MPM Commander Phase 1.

## Overview

Simple HTML/CSS/JS web client served by FastAPI to validate the Commander system works.

## Features

- **Project Management**: Register and view projects
- **State Visualization**: View project states with icons (🟢 working, 🟡 blocked, ⚪ idle, etc.)
- **Session Management**: Create and monitor Claude sessions
- **Message Interface**: Send messages to projects
- **Session Output**: View session output (placeholder in Phase 1)
- **Polling Updates**: Auto-refresh every 2-5 seconds

## Technology Stack

- **HTML/CSS/JS**: No framework complexity for Phase 1
- **Tailwind CSS**: Styling via CDN
- **Polling-based**: Simple HTTP polling for updates
- **FastAPI Static Files**: Served by FastAPI

## Running the Web UI

1. Start the FastAPI server:
```bash
uvicorn claude_mpm.commander.api.app:app --host 127.0.0.1 --port 8000
```

2. Open browser:
```bash
open http://127.0.0.1:8000
```

## File Structure

```
web/
├── __init__.py
├── README.md
└── static/
    ├── index.html        # Main SPA shell
    ├── app.js            # Application logic
    └── styles.css        # Custom styles (minimal)
```

## UI Flow

1. **Project List View** (default)
   - Shows all registered projects
   - Click project to view details
   - Register new project via modal

2. **Project Detail View**
   - Shows project state and info
   - Lists active sessions
   - Send messages to project
   - Create new sessions

3. **Session Output View**
   - Shows session output (placeholder in Phase 1)
   - Auto-refreshes every 2 seconds
   - Will connect to tmux in future phases

## State Icons

- 🟢 **working**: Project actively processing
- 🟡 **blocked**: Project waiting for input/resolution
- ⚪ **idle**: Project inactive
- ⏸️ **paused**: Project paused
- 🔴 **error**: Project encountered error

## Polling Behavior

- **Project List**: Refreshes every 5 seconds
- **Session Output**: Refreshes every 2 seconds
- **Manual Refresh**: Click navigation buttons

## Phase 1 Limitations

- Session output is placeholder text (no tmux integration yet)
- Basic error handling (alert dialogs)
- No authentication or authorization
- No real-time updates (polling only)

## Future Enhancements (Phase 2+)

- WebSocket for real-time updates
- Actual tmux session output streaming
- Authentication and authorization
- Enhanced error handling
- Advanced filtering and search
- Analytics dashboard
