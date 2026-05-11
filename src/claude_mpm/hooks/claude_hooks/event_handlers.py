#!/usr/bin/env python3
"""Thin facade for Claude Code hook event handlers.

This module previously contained a single ~1,870-line ``EventHandlers`` god
class that owned every hook event type. As part of issue #509 the logic was
decomposed into focused handler classes living in the
:mod:`claude_mpm.hooks.claude_hooks.handlers` package.

``EventHandlers`` now composes those handler classes and forwards each
``handle_*`` call through. The public method surface, dependency-injection
constructor, lazy-loaded properties, and module-level helpers are preserved
so ``hook_handler.py`` and existing tests continue to work without changes.
"""

from typing import Any

from .handlers import (
    AssistantResponseHandler,
    PassthroughHandlers,
    StopHandler,
    SubagentHandler,
    ToolHandler,
    UserPromptHandler,
)

# Re-export the module-level helpers and DEBUG flag from the base module so
# any consumer that previously imported them from ``event_handlers`` (e.g.
# ``from claude_mpm.hooks.claude_hooks.event_handlers import _log_manager``)
# keeps working unchanged.
from .handlers.base import (  # noqa: F401
    DEBUG,
    BaseEventHandler,
    TimeoutConfig,
    _get_config,
    _get_delegation_detector_service,
    _get_event_log_service,
    _get_log_manager,
    _log,
)


class EventHandlers:
    """Facade composing decomposed handler classes.

    Public surface is identical to the previous god class:

    - Constructor accepts ``hook_handler`` plus optional DI services.
    - ``log_manager`` / ``config`` / ``delegation_detector`` / ``event_log``
      properties read through to the shared :class:`BaseEventHandler` so
      lazy-loading semantics are preserved.
    - Every ``handle_*`` method delegates to the appropriate sub-handler.
    """

    def __init__(
        self,
        hook_handler,
        *,
        log_manager: Any | None = None,
        config: Any | None = None,
        delegation_detector: Any | None = None,
        event_log: Any | None = None,
    ):
        """Compose handler classes sharing a single :class:`BaseEventHandler`.

        Args:
            hook_handler: The main ClaudeHookHandler instance.
            log_manager: Optional LogManager for agent prompt logging.
            config: Optional Config for autotodos configuration.
            delegation_detector: Optional DelegationDetector for anti-pattern detection.
            event_log: Optional EventLog for PM violation logging.
        """
        # Single shared base — owns hook_handler back-reference, DI state,
        # git branch cache helpers, and the paused-session task helper.
        self._base = BaseEventHandler(
            hook_handler,
            log_manager=log_manager,
            config=config,
            delegation_detector=delegation_detector,
            event_log=event_log,
        )

        # Compose focused handlers. They all share the same base instance so
        # injected services and the git-branch cache stay consistent.
        self._user_prompt = UserPromptHandler(self._base)
        self._tool = ToolHandler(self._base)
        self._stop = StopHandler(self._base)
        self._subagent = SubagentHandler(self._base)
        self._assistant = AssistantResponseHandler(self._base)
        self._passthrough = PassthroughHandlers(self._base)

    # ------------------------------------------------------------------
    # Backwards-compatible attributes
    # ------------------------------------------------------------------
    @property
    def hook_handler(self):
        """Expose the underlying hook handler (legacy attribute)."""
        return self._base.hook_handler

    # Backwards-compatible passthroughs to the shared base's DI storage. Tests
    # and external code inspect these private-looking attributes directly.
    @property
    def _log_manager(self) -> Any | None:
        return self._base._log_manager

    @property
    def _config(self) -> Any | None:
        return self._base._config

    @property
    def _delegation_detector(self) -> Any | None:
        return self._base._delegation_detector

    @property
    def _event_log(self) -> Any | None:
        return self._base._event_log

    @property
    def log_manager(self) -> Any | None:
        """Get log manager (injected or lazy loaded)."""
        return self._base.log_manager

    @property
    def config(self) -> Any | None:
        """Get config (injected or lazy loaded)."""
        return self._base.config

    @property
    def delegation_detector(self) -> Any | None:
        """Get delegation detector (injected or lazy loaded)."""
        return self._base.delegation_detector

    @property
    def event_log(self) -> Any | None:
        """Get event log (injected or lazy loaded)."""
        return self._base.event_log

    # ------------------------------------------------------------------
    # Hook dispatch surface (preserved verbatim from the god-class API)
    # ------------------------------------------------------------------
    def handle_user_prompt_fast(self, event):
        return self._user_prompt.handle_user_prompt_fast(event)

    def handle_pre_tool_fast(self, event):
        return self._tool.handle_pre_tool_fast(event)

    def handle_post_tool_fast(self, event):
        return self._tool.handle_post_tool_fast(event)

    def handle_stop_fast(self, event):
        return self._stop.handle_stop_fast(event)

    def handle_subagent_stop_fast(self, event):
        return self._subagent.handle_subagent_stop_fast(event)

    def handle_assistant_response(self, event):
        return self._assistant.handle_assistant_response(event)

    def handle_notification_fast(self, event):
        return self._passthrough.handle_notification_fast(event)

    def handle_session_start_fast(self, event):
        return self._passthrough.handle_session_start_fast(event)

    def handle_subagent_start_fast(self, event):
        return self._subagent.handle_subagent_start_fast(event)

    def handle_worktree_create_fast(self, event):
        return self._passthrough.handle_worktree_create_fast(event)

    def handle_worktree_remove_fast(self, event):
        return self._passthrough.handle_worktree_remove_fast(event)

    def handle_config_change_fast(self, event):
        return self._passthrough.handle_config_change_fast(event)

    def handle_teammate_idle_fast(self, event):
        return self._passthrough.handle_teammate_idle_fast(event)

    def handle_task_completed_fast(self, event):
        return self._passthrough.handle_task_completed_fast(event)

    def handle_permission_request_fast(self, event):
        return self._passthrough.handle_permission_request_fast(event)

    # ------------------------------------------------------------------
    # Legacy private helper passthroughs (kept for test/back-compat use)
    # ------------------------------------------------------------------
    def _get_git_branch(self, working_dir: str | None = None) -> str:
        return self._base._get_git_branch(working_dir)

    def _check_paused_session_tasks(self, working_dir: str) -> dict:
        return self._base._check_paused_session_tasks(working_dir)

    def _save_project_alias_if_present(self, prompt: str) -> None:
        return self._user_prompt._save_project_alias_if_present(prompt)

    def _capture_pm_directive(self, prompt: str, project: str | None = None) -> None:
        return self._user_prompt._capture_pm_directive(prompt, project)

    def _handle_task_delegation(
        self, tool_input: dict, pre_tool_data: dict, session_id: str
    ):
        return self._tool._handle_task_delegation(tool_input, pre_tool_data, session_id)

    def _generate_resume_log_on_stop(
        self, event: dict, session_id: str, metadata: dict
    ) -> None:
        return self._stop._generate_resume_log_on_stop(event, session_id, metadata)

    def _extract_stop_metadata(self, event: dict) -> dict:
        return self._stop._extract_stop_metadata(event)

    def _log_stop_event_debug(
        self, _event: dict, session_id: str, metadata: dict
    ) -> None:
        return self._stop._log_stop_event_debug(_event, session_id, metadata)

    def _emit_stop_event(self, event: dict, session_id: str, metadata: dict) -> None:
        return self._stop._emit_stop_event(event, session_id, metadata)

    def _handle_subagent_response_tracking(
        self,
        session_id: str,
        agent_type: str,
        reason: str,
        output: str,
        structured_response: dict,
        working_dir: str,
        git_branch: str,
    ):
        return self._subagent._handle_subagent_response_tracking(
            session_id,
            agent_type,
            reason,
            output,
            structured_response,
            working_dir,
            git_branch,
        )

    def _scan_for_delegation_patterns(self, event):
        return self._assistant._scan_for_delegation_patterns(event)
