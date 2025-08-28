# CRITICAL SECURITY FIX: Code Tree Path Validation

## Issue Identified

🚨 **CRITICAL SECURITY VULNERABILITY** found in Code Tree discovery system!

### Problem
The `handle_discover_directory` method in `/src/claude_mpm/services/socketio/handlers/code_analysis.py` **has NO path validation**, allowing unrestricted filesystem access.

### Impact
- Attackers can browse ANY directory on the system via `code:discover:directory` events
- System directories like `/Users`, `/System`, `/etc`, `/` are accessible
- Complete filesystem traversal possible
- Sensitive files and directories exposed

### Root Cause
While `handle_discover_top_level` has proper validation (lines 204-217):
```python
if path in (".", "..", "/") or not Path(path).is_absolute():
    # Reject path
```

The `handle_discover_directory` method (line 310+) has **NO validation at all**.

### Evidence
Frontend tests show:
- ✅ Backend unit tests pass (validates top-level only)
- ❌ Frontend integration tests fail (can access system paths)
- 📂 Directory discovery events received for `/`, `/Users`, `/System`
- 🚫 No error events received for dangerous paths

## Required Fix

Add the same path validation logic to `handle_discover_directory` method.

### Before Fix
```python
async def handle_discover_directory(self, sid: str, data: Dict[str, Any]):
    path = data.get("path")
    # ... NO VALIDATION ...
    result = self.code_analyzer.discover_directory(path, ignore_patterns)
```

### After Fix  
```python
async def handle_discover_directory(self, sid: str, data: Dict[str, Any]):
    path = data.get("path")
    
    # SECURITY: Add path validation
    if path in (".", "..", "/") or not Path(path).is_absolute():
        await self.server.core.sio.emit("code:analysis:error", {
            "error": f"Invalid path for discovery: {path}. Must be an absolute path.",
            "request_id": data.get("request_id"),
            "path": path,
        }, room=sid)
        return
        
    # SECURITY: Ensure path is within working directory bounds
    working_dir = Path.cwd().absolute()
    try:
        requested_path = Path(path).absolute()
        requested_path.relative_to(working_dir)
    except ValueError:
        await self.server.core.sio.emit("code:analysis:error", {
            "error": f"Access denied: Path outside working directory: {path}",
            "request_id": data.get("request_id"),
            "path": path,
        }, room=sid)
        return
        
    # ... continue with discovery ...
```

## Severity: CRITICAL
- **Confidentiality**: HIGH - Full filesystem access
- **Integrity**: LOW - Read-only access  
- **Availability**: LOW - No DoS impact
- **Exploitability**: HIGH - Easy to exploit via SocketIO

## Status: IDENTIFIED - REQUIRES IMMEDIATE FIX