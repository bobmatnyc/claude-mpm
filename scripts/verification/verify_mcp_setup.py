#!/usr/bin/env python3
"""
DEPRECATED: Use src/claude_mpm/mcp/verify_setup.py instead.

This script has been moved to: src/claude_mpm/mcp/verify_setup.py
"""

import sys
import warnings

warnings.warn(
    "scripts/verification/verify_mcp_setup.py is deprecated. "
    "Use src/claude_mpm/mcp/verify_setup.py directly.",
    DeprecationWarning,
    stacklevel=2,
)

from claude_mpm.mcp.verify_setup import main

if __name__ == "__main__":
    sys.exit(main())
