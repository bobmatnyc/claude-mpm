# MCP Auto-Configuration Removal Summary

## Overview

As of v4.15.0+, MCP services are **user-controlled**. Claude MPM should NO LONGER auto-modify `~/.claude.json` to add/fix MCP server configurations.

This document summarizes the changes made to enforce this architectural principle.

## Changes Made

### 1. Removed: `startup.py` Auto-Configuration (Lines 791-817)
**Status**: ✅ COMPLETED

**What was removed**:
```python
# Also ensure MCP services are properly configured in ~/.claude.json
# This fixes incorrect paths and adds missing services
try:
    mcp_manager = MCPConfigManager()
    _fix_success, fix_message = mcp_manager.fix_mcp_service_issues()
    _config_success, config_message = mcp_manager.ensure_mcp_services_configured()
    # ... auto-configuration logic
except Exception as e:
    # ... error handling
```

**Why**: This was auto-modifying user's `~/.claude.json` on every CLI startup.

---

### 2. Removed: `run.py` Auto-Configuration Function
**Status**: ✅ COMPLETED

**What was removed**:
- Function `_ensure_mcp_services_configured(logger)` (lines 572-605)
- Call to this function (line 742)

**Why**: This was auto-configuring MCP services before every `claude-mpm run` session.

---

### 3. Deprecated: `MCPConfigManager.ensure_mcp_services_configured()`
**Status**: ✅ COMPLETED

**What changed**:
```python
# OLD (Lines 701-920): Auto-modified ~/.claude.json
def ensure_mcp_services_configured(self) -> Tuple[bool, str]:
    # ... 140+ lines of auto-configuration logic
    # Modified ~/.claude.json across ALL projects
    # Added missing services
    # Fixed incorrect configurations

# NEW (Lines 753-778): Deprecated wrapper
def ensure_mcp_services_configured(self) -> Tuple[bool, str]:
    """DEPRECATED: Auto-configuring ~/.claude.json is no longer supported."""
    warnings.warn("...deprecated...", DeprecationWarning)
    return self.check_mcp_services_available()  # READ-ONLY check
```

**New Method Added**:
```python
def check_mcp_services_available(self) -> Tuple[bool, str]:
    """Check if required MCP services are available (READ-ONLY)."""
    # Reads ~/.claude.json
    # Checks if expected services exist
    # DOES NOT MODIFY anything
    # Returns (success, message) with installation instructions
```

---

## Architectural Principles

### ❌ OLD (Wrong) Approach
```
Claude MPM Responsibility:
- Auto-detect missing MCP services
- Auto-add service configurations to ~/.claude.json
- Auto-fix incorrect service configurations
- Manage user's MCP server settings

User Responsibility:
- Just install Claude MPM
- Everything else is automatic
```

### ✅ NEW (Correct) Approach
```
User Responsibility:
1. Install MCP servers: pip install mcp-ticketer, npx @modelcontextprotocol/...
2. Configure ~/.claude.json (or let Claude Desktop do it)

Claude MPM Responsibility:
1. Provide commands to CHECK if MCP servers are available
2. Allow users to configure which services MPM should USE
3. Store MPM preferences in ~/.claude-mpm/config/
4. NEVER touch ~/.claude.json's mcpServers section
```

---

## Callers That Still Need Updating

### 🔍 Files Calling `ensure_mcp_services_configured()`:

1. **`src/claude_mpm/services/mcp_config_manager.py:869`**
   - Context: `update_mcp_config()` delegates to `ensure_mcp_services_configured()`
   - Status: Now calls deprecated wrapper (shows warning)
   - Action Needed: Update `update_mcp_config()` to use `check_mcp_services_available()`

2. **`src/claude_mpm/services/mcp_service_verifier.py:627`**
   - Context: Auto-fix attempts to configure services
   - Status: Now calls deprecated wrapper (shows warning)
   - Action Needed: Update to use `check_mcp_services_available()` and guide user to manual installation

3. **`src/claude_mpm/services/mcp_gateway/core/process_pool.py:446`**
   - Context: After installing mcp-vector-search, updates Claude config
   - Status: Now calls deprecated wrapper (shows warning)
   - Action Needed: Remove auto-configuration, just verify installation succeeded

4. **`src/claude_mpm/services/mcp_gateway/core/process_pool.py:664`**
   - Context: Similar to above
   - Status: Now calls deprecated wrapper (shows warning)
   - Action Needed: Same as above

5. **`src/claude_mpm/services/diagnostics/checks/mcp_services_check.py:131`**
   - Context: Diagnostic check attempts auto-fix
   - Status: Now calls deprecated wrapper (shows warning)
   - Action Needed: Update to use `check_mcp_services_available()` and provide manual fix instructions

---

## Configuration Types Clarification

### Type A: User's MCP Server Installation (User-Controlled)
- **Location**: `~/.claude.json` under `mcpServers`
- **Examples**: `mcp-ticketer`, `mcp-browser`, `mcp-vector-search`, `kuzu-memory`
- **Installed by**: Users via `pip install`, `npx`, or Claude Desktop UI
- **Claude MPM Role**: READ-ONLY checks, NEVER modify

### Type B: Claude MPM Internal Config (MPM-Controlled)
- **Location**: `~/.claude-mpm/config/startup.yaml` under `enabled_mcp_services`
- **Purpose**: Which MCP services Claude MPM should **expect/use** (not install)
- **Configured by**: `claude-mpm configure` command
- **Claude MPM Role**: Full control, user configures via interactive UI

---

## Migration Guide for Code

### Before (Wrong):
```python
from claude_mpm.services.mcp_config_manager import MCPConfigManager

manager = MCPConfigManager()
success, message = manager.ensure_mcp_services_configured()
if success:
    print(f"✅ {message}")  # "Added MCP services..."
```

### After (Correct):
```python
from claude_mpm.services.mcp_config_manager import MCPConfigManager

manager = MCPConfigManager()
available, message = manager.check_mcp_services_available()
if not available:
    print(f"⚠️  {message}")  # "Missing MCP services: ... Install via: pip install ..."
    print("Run: pip install mcp-ticketer mcp-browser mcp-vector-search")
else:
    print(f"✅ {message}")  # "All required MCP services available"
```

---

## User-Facing Changes

### Before:
- MCP services auto-configured on startup
- Users saw messages like:
  - "✅ Added MCP services: mcp-ticketer, mcp-browser"
  - "✅ Fixed MCP services: mcp-vector-search"
  - "✓ MCP services configured"

### After:
- Users install MCP services themselves
- Claude MPM only checks availability
- If services missing, users see:
  - "⚠️ Missing MCP services: mcp-ticketer. Install via: pip install mcp-ticketer"
  - Clear installation instructions
  - No automatic modifications to ~/.claude.json

---

## Testing Checklist

- [ ] Verify `claude-mpm run` no longer auto-configures services
- [ ] Verify startup doesn't show "✅ MCP services configured" messages
- [ ] Verify `check_mcp_services_available()` returns correct status
- [ ] Verify deprecation warnings appear when old callers run
- [ ] Verify `claude-mpm configure` still manages internal enabled_mcp_services list
- [ ] Test with missing services - should show installation instructions
- [ ] Test with all services present - should work normally

---

## Removal Timeline

- **v5.1.0**: Deprecation warnings added (current version)
- **v6.0.0**: Remove `ensure_mcp_services_configured()` entirely
- **v6.0.0**: Update all remaining callers to use `check_mcp_services_available()`

---

## Related Files

- `src/claude_mpm/cli/startup.py` - Removed auto-config (lines 791-817)
- `src/claude_mpm/cli/commands/run.py` - Removed `_ensure_mcp_services_configured()`
- `src/claude_mpm/services/mcp_config_manager.py` - Deprecated method, added read-only check
- `src/claude_mpm/cli/commands/configure_startup_manager.py` - **OK, manages internal config**

---

## Documentation Updates Needed

- [ ] Update README.md with MCP service installation instructions
- [ ] Update user guide with MCP service management section
- [ ] Add troubleshooting guide for "Missing MCP services" errors
- [ ] Update CHANGELOG.md with breaking changes note
- [ ] Add migration guide for users upgrading from < v5.1.0
