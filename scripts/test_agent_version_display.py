#!/usr/bin/env python3
"""Test agent version display"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from claude_mpm.cli import _list_agent_versions_at_startup

# Test the function
print("Testing agent version display:")
_list_agent_versions_at_startup()