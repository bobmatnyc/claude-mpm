"""Configuration for hook service integration."""

import os
from pathlib import Path


class HookConfig:
    """Hook service configuration."""
    
    # Service settings
    DEFAULT_PORT = 8080
    PORT_RANGE_START = 8080
    PORT_RANGE_END = 8090
    
    # Timeouts
    SERVICE_START_TIMEOUT = 3.0  # seconds
    REQUEST_TIMEOUT = 30  # seconds
    HEALTH_CHECK_TIMEOUT = 2.0  # seconds
    
    # Paths
    HOOK_SERVICE_LOG_DIR = Path.home() / ".claude-mpm" / "logs"
    HOOK_SERVICE_PID_DIR = Path.home() / ".claude-mpm" / "run"
    
    # Enable/disable hooks by default
    HOOKS_ENABLED_BY_DEFAULT = True
    
    # Hook service endpoints
    HEALTH_ENDPOINT = "/health"
    SUBMIT_HOOK_ENDPOINT = "/hooks/submit"
    PRE_DELEGATION_HOOK_ENDPOINT = "/hooks/pre-delegation"
    POST_DELEGATION_HOOK_ENDPOINT = "/hooks/post-delegation"
    TICKET_EXTRACTION_HOOK_ENDPOINT = "/hooks/ticket-extraction"
    
    @classmethod
    def get_hook_service_url(cls, port: int) -> str:
        """Get the hook service URL for a given port."""
        return f"http://localhost:{port}"
    
    @classmethod
    def is_hooks_enabled(cls) -> bool:
        """Check if hooks are enabled via environment variable."""
        return os.environ.get("CLAUDE_MPM_HOOKS_ENABLED", str(cls.HOOKS_ENABLED_BY_DEFAULT)).lower() in ("true", "1", "yes")