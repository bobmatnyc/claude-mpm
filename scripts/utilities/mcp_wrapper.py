#!/usr/bin/env python3
"""
DEPRECATED: Use src/claude_mpm/mcp/wrapper.py instead.

This script has been moved to: src/claude_mpm/mcp/wrapper.py
"""

import warnings

warnings.warn(
    "scripts/utilities/mcp_wrapper.py is deprecated. "
    "Use src/claude_mpm/mcp/wrapper.py or the console script 'claude-mpm-mcp-wrapper'.",
    DeprecationWarning,
    stacklevel=2,
)

from claude_mpm.mcp.wrapper import *
from claude_mpm.mcp.wrapper import main

if __name__ == "__main__":
    main()
