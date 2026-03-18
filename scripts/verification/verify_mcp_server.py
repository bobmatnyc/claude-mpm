#!/usr/bin/env python3
"""
DEPRECATED: Use src/claude_mpm/mcp/verify_server.py instead.

This script has been moved to: src/claude_mpm/mcp/verify_server.py
"""

import asyncio
import sys
import warnings

warnings.warn(
    "scripts/verification/verify_mcp_server.py is deprecated. "
    "Use src/claude_mpm/mcp/verify_server.py directly.",
    DeprecationWarning,
    stacklevel=2,
)

from claude_mpm.mcp.verify_server import main

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
