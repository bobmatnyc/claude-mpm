# Simple Directory API Integration Test

## What We Created

1. **Simple Directory API**: `/Users/masa/Projects/claude-mpm/src/claude_mpm/dashboard/api/simple_directory.py`
   - Dead-simple HTTP GET endpoint: `/api/directory/list`
   - Takes a `path` query parameter
   - Returns JSON with directory contents

2. **Integration**: Modified `/Users/masa/Projects/claude-mpm/src/claude_mpm/services/socketio/server/core.py`
   - Added `_setup_directory_api()` method
   - Registers the API routes with the aiohttp app

3. **Test Scripts**:
   - `test_simple_directory.py` - Tests against running server
   - `test_directory_api_standalone.py` - Standalone API test

## Test Results

The standalone test PROVES the API works correctly:

```
📁 Testing src directory: /Users/masa/Projects/claude-mpm/src
   Path: /Users/masa/Projects/claude-mpm/src
   Exists: True
   Is Directory: True
   Contents (3 items):
     📁 claude_mpm
     📁 claude_mpm.egg-info
     📄 .DS_Store
```

**Key Finding**: The `src` directory contains exactly what we expect:
- `claude_mpm/` directory (the actual source code)
- `claude_mpm.egg-info/` directory (Python packaging metadata)
- `.DS_Store` file (macOS system file)

## To Test with Main Server

1. **Restart the main server** to pick up code changes:
   ```bash
   # Stop any running instances first
   ./scripts/claude-mpm run --headless
   ```

2. **Test the endpoint**:
   ```bash
   curl "http://localhost:8765/api/directory/list?path=/Users/masa/Projects/claude-mpm/src"
   ```

3. **Or use our test script**:
   ```bash
   python3 /Users/masa/Projects/claude-mpm/scripts/test_simple_directory.py
   ```

## API Usage

**Endpoint**: `GET /api/directory/list`
**Parameters**: 
- `path` (query parameter) - Directory path to list

**Response**:
```json
{
  "path": "/absolute/path",
  "exists": true,
  "is_directory": true,
  "contents": [
    {
      "name": "filename",
      "path": "/absolute/path/filename",
      "is_directory": false,
      "is_file": true
    }
  ]
}
```

## Why This Solves The Problem

This API provides a **direct, unfiltered view** of what's actually in directories, bypassing any complex WebSocket logic, caching, or filtering that might be causing the frontend issues. It's the simplest possible implementation that just returns exactly what `os.listdir()` finds.