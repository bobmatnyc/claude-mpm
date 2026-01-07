# Dashboard Server API Error Investigation

**Date**: 2025-12-23
**Investigator**: Research Agent
**Status**: ✅ ROOT CAUSES IDENTIFIED

## Executive Summary

Investigation into three failing dashboard API endpoints revealed that the **UnifiedMonitorServer is successfully running** but has implementation issues:

1. ✅ `/api/working-directory` - **500 Internal Server Error** (JSON serialization issue)
2. ✅ `/api/file/read` - **200 OK** (Working correctly!)
3. ❌ `/favicon.svg` - **404 Not Found** (Route not registered)

## Test Results

### Server Status
```bash
$ curl http://localhost:8765/health
{
  "status": "running",
  "service": "claude-mpm-monitor",
  "version": "5.4.25",
  "port": 8765,
  "pid": 75347,
  "uptime": 648
}
```

**✅ UnifiedMonitorServer is running correctly on port 8765**

### Endpoint Test Results

#### 1. `/api/working-directory` - 500 Error ❌

```bash
$ curl http://localhost:8765/api/working-directory
500 Internal Server Error

Server got itself in trouble
```

**Root Cause**: Line 837 in `server.py`

```python
# Line 837 - PROBLEMATIC CODE
return web.json_response(
    {"working_directory": Path.cwd(), "success": True}  # ❌ Path object not JSON serializable
)
```

**Fix Required**:
```python
# CORRECTED VERSION
return web.json_response(
    {"working_directory": str(Path.cwd()), "success": True}  # ✅ Convert to string
)
```

**Impact**: Dashboard cannot determine working directory, affecting file operations UI

#### 2. `/api/file/read` - Working ✅

```bash
$ curl "http://localhost:8765/api/file/read?path=/Users/masa/Projects/claude-mpm/README.md"
{
  "success": true,
  "path": "/Users/masa/Projects/claude-mpm/README.md",
  "content": "# Claude MPM - Multi-Agent Project Manager...",
  "lines": 1015,
  "size": 48392,
  "type": "md"
}
```

**Status**: ✅ This endpoint is working correctly!

#### 3. `/favicon.svg` - 404 Error ❌

```bash
$ curl http://localhost:8765/favicon.svg
404: Not Found
```

**Root Cause**: Route is registered (line 1085) but file path resolution fails

```python
# Line 1085 - Route registered
self.app.router.add_get("/favicon.svg", favicon_handler)

# Line 761-770 - Handler implementation
async def favicon_handler(request):
    """Serve favicon.svg from static directory."""
    from aiohttp.web_fileresponse import FileResponse

    favicon_path = static_dir / "favicon.svg"  # ❌ static_dir may be wrong path
    if favicon_path.exists():
        return FileResponse(
            favicon_path, headers={"Content-Type": "image/svg+xml"}
        )
    raise web.HTTPNotFound()
```

**Investigation**:

```bash
$ ls -la /Users/masa/Projects/claude-mpm/src/claude_mpm/dashboard/static/svelte-build/
total 16
drwxr-xr-x@ 5 masa  staff   160 Dec 23 10:06 _app
drwxr-xr-x@ 5 masa  staff   160 Dec 23 10:06 .
drwxr-xr-x@ 3 masa  staff    96 Dec 23 10:06 ..
-rw-------@ 1 masa  staff   395 Dec 23 10:06 favicon.svg  ✅ File exists!
-rw-r--r--@ 1 masa  staff  1175 Dec 23 10:06 index.html
```

**The file exists at**: `static/svelte-build/favicon.svg`
**But handler looks at**: `static/favicon.svg` (wrong path!)

**Fix Required**:
```python
# Line 765 - CORRECTED VERSION
favicon_path = static_dir / "svelte-build" / "favicon.svg"  # ✅ Include svelte-build directory
```

**Impact**: Browser shows missing favicon icon

## Route Registration Analysis

All three routes ARE registered in `_setup_http_routes()`:

```python
# Lines 1084-1091
self.app.router.add_get("/", dashboard_index)
self.app.router.add_get("/favicon.svg", favicon_handler)           # ✅ Registered
self.app.router.add_get("/health", health_check)
self.app.router.add_get("/version.json", version_handler)
self.app.router.add_get("/api/config", config_handler)
self.app.router.add_get("/api/working-directory", working_directory_handler)  # ✅ Registered
self.app.router.add_get("/api/files", api_files_handler)
self.app.router.add_get("/api/file/read", api_file_read_handler)  # ✅ Registered
```

**Conclusion**: Routes are registered correctly. Implementation bugs are the issue.

## Code Location Summary

**File**: `/Users/masa/Projects/claude-mpm/src/claude_mpm/services/monitor/server.py`

| Endpoint | Line Numbers | Status | Issue |
|----------|--------------|--------|-------|
| `/api/working-directory` | 833-838 | ❌ 500 Error | Path object not JSON serializable |
| `/api/file/read` | 702-758 | ✅ Working | None |
| `/favicon.svg` | 761-770 | ❌ 404 Error | Wrong file path (missing svelte-build/) |

## Required Fixes

### Fix 1: `/api/working-directory` (Line 837)

**Before**:
```python
return web.json_response(
    {"working_directory": Path.cwd(), "success": True}
)
```

**After**:
```python
return web.json_response(
    {"working_directory": str(Path.cwd()), "success": True}
)
```

### Fix 2: `/favicon.svg` (Line 765)

**Before**:
```python
favicon_path = static_dir / "favicon.svg"
```

**After**:
```python
favicon_path = static_dir / "svelte-build" / "favicon.svg"
```

## Additional Context

### Server Architecture

The project uses **UnifiedMonitorServer** (not the old SocketIOServerCore):

- **Primary Server**: `UnifiedMonitorServer` (server.py) - Running on port 8765 ✅
- **Legacy Server**: `SocketIOServerCore` (core.py) - Not used for dashboard

**Why Two Files?**

From code comments in `server.py`:
> "Unified server that combines HTTP dashboard and Socket.IO functionality. Replaces multiple competing server implementations with one stable solution."

The `core.py` file contains similar routes but is legacy code. The active server is in `server.py`.

### File Structure

```
src/claude_mpm/dashboard/
├── static/
│   └── svelte-build/          ← Actual location
│       ├── _app/
│       ├── favicon.svg        ← File is here
│       └── index.html
└── ...
```

### Working Directory Endpoint Comparison

**UnifiedMonitorServer** (server.py, line 837) - BROKEN:
```python
return web.json_response(
    {"working_directory": Path.cwd(), "success": True}  # ❌ Path object
)
```

**SocketIOServerCore** (core.py, line 547) - CORRECT:
```python
return web.json_response(
    {
        "working_directory": str(Path.cwd()),  # ✅ String conversion
        "home_directory": str(Path.home()),
        "process_cwd": working_dir,
        "session_id": getattr(self, "session_id", None),
    }
)
```

**Observation**: The legacy server has the correct implementation! Copy this pattern.

## Testing Commands

After applying fixes, verify with:

```bash
# Test working-directory endpoint
curl -s http://localhost:8765/api/working-directory | jq .

# Expected output:
# {
#   "working_directory": "/Users/masa/Projects/claude-mpm",
#   "success": true
# }

# Test favicon endpoint
curl -s -w "\nStatus: %{http_code}\n" http://localhost:8765/favicon.svg | head -5

# Expected: SVG content with Status: 200

# Test file read (already working)
curl -s "http://localhost:8765/api/file/read?path=/Users/masa/Projects/claude-mpm/README.md" | jq '.success'

# Expected: true
```

## Impact Assessment

### High Impact (User-Facing)
- ❌ `/api/working-directory` - Dashboard cannot show current directory
- ❌ `/favicon.svg` - Browser tab shows generic icon instead of MPM branding

### Low Impact (Already Working)
- ✅ `/api/file/read` - File viewer works correctly

## Recommendations

### Immediate Actions (Priority 1)
1. **Fix working-directory endpoint** - One-line change (add `str()` conversion)
2. **Fix favicon path** - One-line change (add `svelte-build/` to path)

### Code Quality Improvements (Priority 2)
3. **Add type hints** - `async def working_directory_handler(request: web.Request) -> web.Response:`
4. **Add unit tests** - Verify JSON serialization of all API responses
5. **Consolidate implementations** - Remove duplicate code between server.py and core.py

### Testing Improvements (Priority 3)
6. **Add integration tests** - Test all dashboard API endpoints
7. **Add CI checks** - Automated API endpoint validation
8. **Add response validation** - JSON schema validation for all endpoints

## Files Modified

This investigation does not modify any files. Implementation changes required:

- `/Users/masa/Projects/claude-mpm/src/claude_mpm/services/monitor/server.py`
  - Line 837: Add `str()` conversion for Path.cwd()
  - Line 765: Add `svelte-build/` to favicon path

## Verification Steps

After fixes are applied:

1. ✅ Restart monitor server: `claude-mpm monitor restart`
2. ✅ Test all three endpoints with curl commands above
3. ✅ Open dashboard in browser: http://localhost:8765/
4. ✅ Verify working directory is displayed correctly
5. ✅ Verify favicon appears in browser tab
6. ✅ Test file viewer functionality

## Conclusion

**Problem**: Two trivial implementation bugs in UnifiedMonitorServer
**Solution**: Two one-line fixes (add type conversions)
**Complexity**: Low (5-minute fix)
**Testing**: Simple (curl commands verify fixes)

The server architecture is sound. These are minor implementation oversights that can be quickly resolved.

---

**Next Steps**: Apply fixes to `server.py` and verify with integration tests.
