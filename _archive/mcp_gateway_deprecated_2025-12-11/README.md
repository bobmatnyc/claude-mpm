# MCP Gateway - Archived (2025-12-11)

## Why Archived

The MCP Gateway service has been archived to reduce maintenance burden. The MCP server functionality is now handled by external MCP services and direct integration patterns.

## What Was Archived

### Services
- `src/claude_mpm/services/mcp_gateway/` - Full MCP gateway service
  - Core gateway logic
  - Tool adapters (hello_world, document_summarizer, kuzu_memory_service, etc.)
  - Configuration system
  - Server implementation
  - Registry and process pool management

### Scripts
- `src/claude_mpm/scripts/mcp_wrapper.py` - MCP wrapper entry point
- `src/claude_mpm/scripts/mcp_server.py` - MCP server launcher

### Entry Points (Commented in pyproject.toml)
- `claude-mpm-mcp` - Main MCP server entry point
- `claude-mpm-mcp-wrapper` - MCP wrapper entry point

## How to Restore

If you need to restore this functionality:

1. **Move files back**:
   ```bash
   # Restore gateway service
   mv _archive/mcp_gateway_deprecated_2025-12-11/mcp_gateway \
      src/claude_mpm/services/

   # Restore scripts
   mv _archive/mcp_gateway_deprecated_2025-12-11/mcp_wrapper.py \
      src/claude_mpm/scripts/
   mv _archive/mcp_gateway_deprecated_2025-12-11/mcp_server.py \
      src/claude_mpm/scripts/
   ```

2. **Restore pyproject.toml entry points**:
   ```toml
   [project.scripts]
   claude-mpm-mcp = "claude_mpm.services.mcp_gateway.server.stdio_server:main_sync"
   claude-mpm-mcp-wrapper = "claude_mpm.scripts.mcp_wrapper:entry_point"
   ```

3. **Reinstall**:
   ```bash
   pip install -e .
   ```

## Alternative Approaches

Instead of the MCP Gateway, consider:

1. **Direct MCP Server Integration**: Use MCP servers directly via Claude Desktop configuration
2. **External MCP Services**: Leverage standalone MCP services (mcp-ticketer, mcp-vector-search, etc.)
3. **Native Tool Integration**: Integrate tools directly into Claude MPM without the gateway layer

## Archive Date

Archived on: 2025-12-11

## Related Files

- MCP configuration remains in: `src/claude_mpm/services/mcp_config_manager.py`
- MCP verification remains in: `src/claude_mpm/services/mcp_service_verifier.py`
- Optional dependencies remain in: `pyproject.toml` under `[project.optional-dependencies] mcp`

## Notes

The MCP optional dependencies in pyproject.toml are marked as deprecated but left intact to avoid breaking existing installations that may depend on them. They can be removed in a future major version update.
