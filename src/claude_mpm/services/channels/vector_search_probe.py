"""Non-blocking probe for mcp-vector-search availability."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


async def probe_vector_search(cwd: str, timeout_ms: int = 2000) -> bool:
    """Return True if mcp-vector-search appears to be indexed for this directory."""
    try:
        async with asyncio.timeout(timeout_ms / 1000):
            index_candidates = [
                Path(cwd) / ".mcp-vector-index",
                Path(cwd) / ".vector-index",
                Path(cwd) / ".mcp_vector_search",
            ]
            if any(p.exists() for p in index_candidates):
                return True
            # Also check if the MCP service path is discoverable
            try:
                from claude_mpm.services.mcp_config_manager import MCPConfigManager

                manager = MCPConfigManager()
                if hasattr(manager, "detect_service_path"):
                    path = manager.detect_service_path("mcp-vector-search")
                    return path is not None
            except Exception:
                pass
            return False
    except (TimeoutError, Exception):
        logger.debug("vector-search probe timed out or failed", exc_info=True)
        return False
