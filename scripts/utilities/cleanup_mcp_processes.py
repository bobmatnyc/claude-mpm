#!/usr/bin/env python3
"""
DEPRECATED: Use src/claude_mpm/mcp/process_manager.py instead.

This script has been merged into: src/claude_mpm/mcp/process_manager.py
"""

import warnings

warnings.warn(
    "scripts/utilities/cleanup_mcp_processes.py is deprecated. "
    "Use src/claude_mpm/mcp/process_manager.py or the console script 'claude-mpm-mcp-processes'.",
    DeprecationWarning,
    stacklevel=2,
)

from claude_mpm.mcp.process_manager import MCPProcessManager, main

if __name__ == "__main__":
    import sys

    sys.exit(main())
