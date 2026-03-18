#!/usr/bin/env python3
"""
DEPRECATED: Use src/claude_mpm/mcp/diagnostics.py instead.

This script has been moved to: src/claude_mpm/mcp/diagnostics.py
"""

import warnings

warnings.warn(
    "scripts/utilities/mcp_diagnostics.py is deprecated. "
    "Use src/claude_mpm/mcp/diagnostics.py or the console script 'claude-mpm-mcp-diagnostics'.",
    DeprecationWarning,
    stacklevel=2,
)

from claude_mpm.mcp.diagnostics import *
from claude_mpm.mcp.diagnostics import main

if __name__ == "__main__":
    main()
