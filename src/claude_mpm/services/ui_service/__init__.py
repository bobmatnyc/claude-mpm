"""UI Service for claude-mpm.

Exposes Claude Code REPL features as a REST + SSE + WebSocket API
for consumption by a web UI frontend.
"""

from claude_mpm.services.ui_service.app import create_app
from claude_mpm.services.ui_service.config import UIServiceConfig

__all__ = ["UIServiceConfig", "create_app"]
