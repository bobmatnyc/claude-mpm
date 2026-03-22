"""Abstract base class for agent runtime adapters.

Allows MPM to swap between CLI subprocess and SDK-based agent execution.
The ``AgentRuntime`` ABC defines a runtime-agnostic interface that both the
existing CLI adapter and the new ``SDKAgentRunner`` can implement, enabling
seamless runtime selection via a factory function.

Usage::

    from claude_mpm.services.agents.agent_runtime import create_runtime, AgentConfig

    runtime = create_runtime("sdk", AgentConfig(system_prompt="You are helpful."))
    result = await runtime.run("Explain dependency injection.")
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine


# ---------------------------------------------------------------------------
# Runtime-agnostic data classes
# ---------------------------------------------------------------------------


@dataclass
class AgentResult:
    """Runtime-agnostic result from an agent execution."""

    text: str
    session_id: str | None = None
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    cost_usd: float | None = None
    num_turns: int | None = None
    duration_ms: int | None = None
    is_error: bool = False


@dataclass
class AgentConfig:
    """Runtime-agnostic agent configuration."""

    system_prompt: str | None = None
    model: str | None = None
    allowed_tools: list[str] | None = None
    permission_mode: str | None = None
    cwd: str | None = None
    max_turns: int | None = None
    max_budget_usd: float | None = None
    mcp_servers: dict[str, Any] | None = None


# ---------------------------------------------------------------------------
# Model mapping helpers
# ---------------------------------------------------------------------------

# MPM short names -> SDK / API model identifiers
_MPM_TO_SDK_MODEL: dict[str, str] = {
    "sonnet": "claude-sonnet-4-20250514",
    "opus": "claude-opus-4-20250514",
    "haiku": "claude-haiku-3-20250307",
}

# Reverse mapping: long API names -> MPM short names
_SDK_TO_MPM_MODEL: dict[str, str] = {
    "claude-sonnet-4-20250514": "sonnet",
    "claude-opus-4-20250514": "opus",
    "claude-haiku-3-20250307": "haiku",
    "claude-4-sonnet-20250514": "sonnet",
    "claude-3-5-sonnet-20241022": "sonnet",
    "claude-3-5-sonnet": "sonnet",
    "claude-3-sonnet": "sonnet",
    "claude-3-haiku": "haiku",
    "claude-3-opus": "opus",
    "claude-3-opus-20240229": "opus",
    "claude-3-haiku-20240307": "haiku",
}


def resolve_model_to_sdk(model: str) -> str:
    """Map an MPM short model name to the SDK model identifier.

    If *model* is already a full SDK identifier it is returned as-is.
    """
    return _MPM_TO_SDK_MODEL.get(model, model)


def resolve_model_to_mpm(model: str) -> str:
    """Map a full SDK model identifier to an MPM short name.

    Falls back to extracting ``opus``/``sonnet``/``haiku`` from the string.
    """
    if model in _SDK_TO_MPM_MODEL:
        return _SDK_TO_MPM_MODEL[model]
    lowered = model.lower()
    for short in ("opus", "sonnet", "haiku"):
        if short in lowered:
            return short
    return model


# ---------------------------------------------------------------------------
# Abstract base class
# ---------------------------------------------------------------------------


class AgentRuntime(ABC):
    """Abstract interface for agent execution backends.

    Every concrete runtime (CLI subprocess, SDK in-process, etc.) must
    implement these methods so that higher-level MPM orchestration code
    can remain backend-agnostic.
    """

    @abstractmethod
    async def run(
        self,
        prompt: str,
        config: AgentConfig | None = None,
    ) -> AgentResult:
        """Execute a one-shot prompt."""
        ...

    @abstractmethod
    async def run_with_hooks(
        self,
        prompt: str,
        tool_guard: Callable[[str, dict[str, Any]], Coroutine[Any, Any, bool]]
        | None = None,
        blocked_tools: set[str] | None = None,
        config: AgentConfig | None = None,
    ) -> AgentResult:
        """Execute with tool interception."""
        ...

    @abstractmethod
    async def resume(
        self,
        session_id: str,
        prompt: str,
        config: AgentConfig | None = None,
    ) -> AgentResult:
        """Resume a previous session."""
        ...

    @abstractmethod
    async def fork(
        self,
        session_id: str,
        prompt: str,
        config: AgentConfig | None = None,
    ) -> AgentResult:
        """Fork from a previous session."""
        ...

    @property
    @abstractmethod
    def runtime_name(self) -> str:
        """Return the runtime identifier (e.g., ``'cli'``, ``'sdk'``)."""
        ...


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def create_runtime(
    runtime_type: str = "sdk",
    config: AgentConfig | None = None,
) -> AgentRuntime:
    """Factory to create the appropriate runtime.

    Args:
        runtime_type: ``"sdk"`` (default) for the in-process SDK runtime.
        config: Optional ``AgentConfig`` to pre-configure the runtime.

    Returns:
        A concrete ``AgentRuntime`` instance.

    Raises:
        ValueError: If *runtime_type* is unknown.
    """
    if runtime_type == "sdk":
        # Import here to avoid circular imports and keep SDK optional
        from claude_mpm.services.agents.sdk_runtime import SDKAgentRunner

        return SDKAgentRunner.from_config(config or AgentConfig())
    raise ValueError(f"Unknown runtime type: {runtime_type!r}")
