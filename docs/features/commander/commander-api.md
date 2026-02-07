# MPM Commander REST API

The MPM Commander REST API provides programmatic access to project and session management.

## Installation

FastAPI and uvicorn are now included in the main dependencies:

```bash
pip install claude-mpm
```

## Running the API

Start the API server with uvicorn:

```bash
uvicorn claude_mpm.commander.api.app:app --host 127.0.0.1 --port 8000
```

The API will be available at `http://127.0.0.1:8000`

## API Documentation

Interactive API documentation is automatically generated:

- **Swagger UI**: http://127.0.0.1:8000/docs
- **ReDoc**: http://127.0.0.1:8000/redoc
- **OpenAPI JSON**: http://127.0.0.1:8000/openapi.json

## Quick Start

### Register a Project

```bash
curl -X POST http://127.0.0.1:8000/api/projects \
  -H "Content-Type: application/json" \
  -d '{
    "path": "/Users/user/projects/my-app",
    "name": "My App"
  }'
```

Response:
```json
{
  "id": "abc-123",
  "path": "/Users/user/projects/my-app",
  "name": "My App",
  "state": "idle",
  "state_reason": null,
  "sessions": [],
  "pending_events_count": 0,
  "last_activity": "2025-01-12T10:00:00Z",
  "created_at": "2025-01-12T10:00:00Z"
}
```

### List All Projects

```bash
curl http://127.0.0.1:8000/api/projects
```

### Create a Session

```bash
curl -X POST http://127.0.0.1:8000/api/projects/abc-123/sessions \
  -H "Content-Type: application/json" \
  -d '{
    "runtime": "claude-code"
  }'
```

### Send a Message

```bash
curl -X POST http://127.0.0.1:8000/api/projects/abc-123/messages \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Fix the login bug"
  }'
```

### Get Conversation Thread

```bash
curl http://127.0.0.1:8000/api/projects/abc-123/thread
```

## Endpoints

### Health Check
- `GET /api/health` - Check API status

### Projects
- `GET /api/projects` - List all projects
- `POST /api/projects` - Register a new project
- `GET /api/projects/{project_id}` - Get project details
- `DELETE /api/projects/{project_id}` - Unregister project
- `POST /api/projects/{project_id}/pause` - Pause project
- `POST /api/projects/{project_id}/resume` - Resume project

### Sessions
- `GET /api/projects/{project_id}/sessions` - List sessions
- `POST /api/projects/{project_id}/sessions` - Create session
- `DELETE /api/sessions/{session_id}` - Stop session

### Messages
- `GET /api/projects/{project_id}/thread` - Get conversation thread
- `POST /api/projects/{project_id}/messages` - Send message

## Error Handling

All errors return JSON with structured error information:

```json
{
  "detail": {
    "error": {
      "code": "PROJECT_NOT_FOUND",
      "message": "Project not found: abc-123"
    }
  }
}
```

Error codes:
- `PROJECT_NOT_FOUND` (404)
- `PROJECT_ALREADY_EXISTS` (409)
- `INVALID_PATH` (400)
- `SESSION_NOT_FOUND` (404)
- `INVALID_RUNTIME` (400)

## Security

- The API binds to `127.0.0.1` (localhost only) by default
- CORS is enabled for localhost origins only
- No authentication in Phase 1 (add in Phase 2+)

## Development

Run tests:

```bash
pytest tests/commander/test_api.py -v
```

Run with auto-reload for development:

```bash
uvicorn claude_mpm.commander.api.app:app --host 127.0.0.1 --port 8000 --reload
```

## Phase 1 Limitations

- Sessions remain in "initializing" state (runtime adapter integration in Phase 2)
- Messages are stored but not sent to runtimes (Phase 2)
- No authentication or rate limiting (Phase 2+)
- Single node only (no distributed support)

## Next Steps

See [Commander Implementation Plan](commander-implementation-plan.md) for roadmap.
