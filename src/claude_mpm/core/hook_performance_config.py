"""Hook performance configuration for Claude MPM.

This module provides configuration options to optimize hook performance
and enable/disable hooks based on performance requirements.
"""

import os
from typing import Dict, Optional


class HookPerformanceConfig:
    """Configuration for hook performance optimization."""

    def __init__(self):
        """Initialize hook performance configuration from environment."""
        self._load_config()

    def _load_config(self):
        """Load configuration from environment variables."""
        # Performance mode - disables all hooks for maximum speed
        self.performance_mode = (
            os.getenv("CLAUDE_MPM_PERFORMANCE_MODE", "false").lower() == "true"
        )

        # Individual hook type controls
        self.enable_pre_tool_hooks = (
            os.getenv("CLAUDE_MPM_HOOKS_PRE_TOOL", "true").lower() == "true"
        )
        self.enable_post_tool_hooks = (
            os.getenv("CLAUDE_MPM_HOOKS_POST_TOOL", "true").lower() == "true"
        )
        self.enable_user_prompt_hooks = (
            os.getenv("CLAUDE_MPM_HOOKS_USER_PROMPT", "true").lower() == "true"
        )
        self.enable_delegation_hooks = (
            os.getenv("CLAUDE_MPM_HOOKS_DELEGATION", "true").lower() == "true"
        )

        # Background processing settings
        self.queue_size = int(os.getenv("CLAUDE_MPM_HOOK_QUEUE_SIZE", "1000"))
        self.background_timeout = float(os.getenv("CLAUDE_MPM_HOOK_BG_TIMEOUT", "2.0"))

        # Batching settings (for future implementation)
        self.enable_batching = (
            os.getenv("CLAUDE_MPM_HOOK_BATCHING", "false").lower() == "true"
        )
        self.batch_size = int(os.getenv("CLAUDE_MPM_HOOK_BATCH_SIZE", "10"))
        self.batch_timeout_ms = int(
            os.getenv("CLAUDE_MPM_HOOK_BATCH_TIMEOUT_MS", "100")
        )

    def is_hook_enabled(self, hook_type: str) -> bool:
        """Check if a specific hook type is enabled.

        Args:
            hook_type: Type of hook (PreToolUse, PostToolUse, UserPromptSubmit, etc.)

        Returns:
            bool: True if hook should be processed
        """
        if self.performance_mode:
            return False

        hook_type_lower = hook_type.lower()

        if "pretool" in hook_type_lower or "pre_tool" in hook_type_lower:
            return self.enable_pre_tool_hooks
        if "posttool" in hook_type_lower or "post_tool" in hook_type_lower:
            return self.enable_post_tool_hooks
        if "userprompt" in hook_type_lower or "user_prompt" in hook_type_lower:
            return self.enable_user_prompt_hooks
        if "delegation" in hook_type_lower:
            return self.enable_delegation_hooks

        # Default to enabled for unknown hook types
        return True

    def get_queue_config(self) -> Dict[str, int]:
        """Get queue configuration for background processing."""
        return {"maxsize": self.queue_size, "timeout": self.background_timeout}

    def get_batch_config(self) -> Dict[str, any]:
        """Get batching configuration (for future use)."""
        return {
            "enabled": self.enable_batching,
            "batch_size": self.batch_size,
            "timeout_ms": self.batch_timeout_ms,
        }

    def print_config(self) -> str:
        """Return a string representation of current configuration."""
        config_lines = [
            "Hook Performance Configuration:",
            f"  Performance Mode: {self.performance_mode}",
            f"  Pre-tool Hooks: {self.enable_pre_tool_hooks}",
            f"  Post-tool Hooks: {self.enable_post_tool_hooks}",
            f"  User Prompt Hooks: {self.enable_user_prompt_hooks}",
            f"  Delegation Hooks: {self.enable_delegation_hooks}",
            f"  Queue Size: {self.queue_size}",
            f"  Background Timeout: {self.background_timeout}s",
            f"  Batching Enabled: {self.enable_batching}",
        ]
        return "\n".join(config_lines)


# Global configuration instance
_hook_config: Optional[HookPerformanceConfig] = None


def get_hook_performance_config() -> HookPerformanceConfig:
    """Get the global hook performance configuration instance."""
    global _hook_config
    if _hook_config is None:
        _hook_config = HookPerformanceConfig()
    return _hook_config


def set_performance_mode(enabled: bool):
    """Enable or disable performance mode programmatically.

    Args:
        enabled: True to enable performance mode (disable all hooks)
    """
    os.environ["CLAUDE_MPM_PERFORMANCE_MODE"] = "true" if enabled else "false"
    # Reload configuration
    global _hook_config
    _hook_config = None


def is_performance_mode() -> bool:
    """Check if performance mode is currently enabled."""
    return get_hook_performance_config().performance_mode


# Environment variable documentation for users
ENVIRONMENT_VARIABLES = {
    "CLAUDE_MPM_PERFORMANCE_MODE": 'Set to "true" to disable all hooks for maximum performance',
    "CLAUDE_MPM_HOOKS_PRE_TOOL": 'Set to "false" to disable pre-tool hooks',
    "CLAUDE_MPM_HOOKS_POST_TOOL": 'Set to "false" to disable post-tool hooks',
    "CLAUDE_MPM_HOOKS_USER_PROMPT": 'Set to "false" to disable user prompt hooks',
    "CLAUDE_MPM_HOOKS_DELEGATION": 'Set to "false" to disable delegation hooks',
    "CLAUDE_MPM_HOOK_QUEUE_SIZE": "Maximum number of hooks in background queue (default: 1000)",
    "CLAUDE_MPM_HOOK_BG_TIMEOUT": "Timeout for background hook processing in seconds (default: 2.0)",
    "CLAUDE_MPM_HOOK_BATCHING": 'Set to "true" to enable hook batching (experimental)',
    "CLAUDE_MPM_HOOK_BATCH_SIZE": "Number of hooks to batch together (default: 10)",
    "CLAUDE_MPM_HOOK_BATCH_TIMEOUT_MS": "Batch timeout in milliseconds (default: 100)",
}
