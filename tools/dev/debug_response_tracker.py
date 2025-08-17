#!/usr/bin/env python3
"""Debug Response Tracker Configuration"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.services.response_tracker import ResponseTracker
from claude_mpm.core.config import Config

# Test with disabled config
config_data = {
    'response_tracking': {
        'enabled': False,
        'base_dir': '/tmp/test/responses'
    },
    'response_logging': {
        'enabled': False,
        'session_directory': '/tmp/test/responses'
    }
}

config = Config(config=config_data)
print(f"Config response_tracking: {config.get('response_tracking')}")
print(f"Config response_logging: {config.get('response_logging')}")

tracker = ResponseTracker(config=config)
print(f"Tracker enabled: {tracker.enabled}")
print(f"Tracker is_enabled(): {tracker.is_enabled()}")
print(f"Tracker session_logger: {tracker.session_logger}")