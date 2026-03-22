"""Runtime selection configuration.

Determines which AgentRuntime backend to use based on:
1. Environment variable: ``CLAUDE_MPM_RUNTIME=sdk|cli``
2. Default: ``"sdk"`` if ``claude_agent_sdk`` is available, else ``"cli"``

The config-file path (``configuration.yaml``) is intentionally omitted for now
since the unified config system can layer this on top later.
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from claude_mpm.services.agents.agent_runtime import AgentConfig, AgentRuntime

logger = logging.getLogger(__name__)


def get_runtime_type() -> str:
    """Determine the active runtime type.

    Resolution order:

    1. ``CLAUDE_MPM_RUNTIME`` environment variable (``"sdk"`` or ``"cli"``).
    2. Auto-detect: ``"sdk"`` if ``claude_agent_sdk`` is importable,
       otherwise ``"cli"``.
    """
    env_runtime = os.environ.get("CLAUDE_MPM_RUNTIME", "").strip().lower()
    if env_runtime in ("sdk", "cli"):
        logger.debug("Runtime from env: %s", env_runtime)
        return env_runtime

    # Auto-detect SDK availability
    try:
        import claude_agent_sdk  # noqa: F401

        logger.debug("SDK detected, using 'sdk' runtime")
        return "sdk"
    except ImportError:
        logger.debug("SDK not available, falling back to 'cli' runtime")
        return "cli"


def get_runtime(config: AgentConfig | None = None) -> AgentRuntime:
    """Get the configured runtime instance.

    Convenience wrapper that resolves the runtime type and creates the
    appropriate :class:`AgentRuntime` via the factory.
    """
    from claude_mpm.services.agents.agent_runtime import (
        AgentConfig as DefaultConfig,
        create_runtime,
    )

    runtime_type = get_runtime_type()
    return create_runtime(runtime_type, config or DefaultConfig())
