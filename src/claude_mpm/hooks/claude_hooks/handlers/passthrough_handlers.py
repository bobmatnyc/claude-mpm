#!/usr/bin/env python3
"""Passthrough event handlers for events with simple emit-only behavior.

Extracted from ``event_handlers.EventHandlers`` as part of the #509 refactor.
Behavior is preserved verbatim; only the surrounding structure has changed.

Includes:
- Notification
- SessionStart
- WorktreeCreate / WorktreeRemove
- ConfigChange
- TeammateIdle
- TaskCompleted
- PermissionRequest
"""

from datetime import UTC, datetime

from .base import BaseEventHandler, _log


class PassthroughHandlers:
    """Bundle of straightforward Socket.IO-emitting hook handlers."""

    def __init__(self, base: BaseEventHandler):
        self.base = base
        self.hook_handler = base.hook_handler

    def handle_notification_fast(self, event):
        """Handle notification events from Claude.

        WHY enhanced notification capture:
        - Provides visibility into Claude's status and communication flow
        - Captures notification type, content, and context for monitoring
        - Enables pattern analysis of Claude's notification behavior
        - Useful for debugging communication issues and user experience
        """
        notification_type = event.get("notification_type", "unknown")
        message = event.get("message", "")

        # Get working directory and git branch
        working_dir = event.get("cwd", "")
        git_branch = (
            self.base._get_git_branch(working_dir) if working_dir else "Unknown"
        )

        notification_data = {
            "notification_type": notification_type,
            "message": message,
            "message_preview": message[:200] if len(message) > 200 else message,
            "message_length": len(message),
            "session_id": event.get("session_id", ""),
            "working_directory": working_dir,
            "git_branch": git_branch,
            "timestamp": datetime.now(UTC).isoformat(),
            "is_user_input_request": "input" in message.lower()
            or "waiting" in message.lower(),
            "is_error_notification": "error" in message.lower()
            or "failed" in message.lower(),
            "is_status_update": any(
                word in message.lower()
                for word in ["processing", "analyzing", "working", "thinking"]
            ),
        }

        # Emit normalized event
        self.hook_handler._emit_socketio_event("", "notification", notification_data)

    def handle_session_start_fast(self, event):
        """Handle session start events for tracking conversation sessions.

        WHY track session starts:
        - Provides visibility into new conversation sessions
        - Enables tracking of session lifecycle and duration
        - Useful for monitoring concurrent sessions and resource usage

        NOTE: This handler is intentionally lightweight - only event monitoring.
        All initialization/deployment logic runs in MPM CLI startup, not here.
        """
        session_id = event.get("session_id", "")
        working_dir = event.get("cwd", "")
        git_branch = (
            self.base._get_git_branch(working_dir) if working_dir else "Unknown"
        )

        session_start_data = {
            "session_id": session_id,
            "working_directory": working_dir,
            "git_branch": git_branch,
            "timestamp": datetime.now(UTC).isoformat(),
            "hook_event_name": "SessionStart",
            "has_pending_tasks": False,
            "pending_task_count": 0,
        }

        # Check for paused sessions with pending tasks
        if working_dir:
            session_start_data.update(
                self.base._check_paused_session_tasks(working_dir)
            )

        # Debug logging
        _log(
            f"Hook handler: Processing SessionStart - session: '{session_id}', pending_tasks: {session_start_data.get('pending_task_count', 0)}"
        )

        # Emit normalized event
        self.hook_handler._emit_socketio_event("", "session_start", session_start_data)

    def handle_worktree_create_fast(self, event):
        """Handle WorktreeCreate hook event (Claude Code v2.1.47+).

        Fires when `claude --worktree` creates a new git worktree, indicating
        a new parallel work session is starting. This is useful for the
        dashboard to show concurrent work happening in isolated branches.

        Key fields from Claude Code:
        - worktree_name: Human-readable name for the worktree
        - worktree_path: Absolute filesystem path to the new worktree
        - branch: Git branch name checked out in the worktree
        - session_id: The session that triggered the worktree creation
        """
        session_id = event.get("session_id", "")
        working_dir = event.get("cwd", "")

        # Extract worktree-specific fields
        worktree_name = event.get("worktree_name", "")
        worktree_path = event.get("worktree_path", event.get("path", ""))
        branch = event.get("branch", event.get("worktree_branch", ""))

        worktree_data = {
            "session_id": session_id,
            "working_directory": working_dir,
            "worktree_name": worktree_name,
            "worktree_path": worktree_path,
            "branch": branch,
            "timestamp": datetime.now(UTC).isoformat(),
            "hook_event_name": "WorktreeCreate",
        }

        _log(
            f"Hook handler: WorktreeCreate - worktree='{worktree_name}', "
            f"path='{worktree_path}', branch='{branch}', session='{session_id[:16]}...'"
        )

        self.hook_handler._emit_socketio_event("", "worktree_create", worktree_data)

    def handle_worktree_remove_fast(self, event):
        """Handle WorktreeRemove hook event (Claude Code v2.1.47+).

        Fires when a git worktree created by `claude --worktree` is removed,
        indicating a parallel work session has ended.

        Key fields from Claude Code:
        - worktree_name: Human-readable name of the removed worktree
        - worktree_path: Absolute filesystem path of the removed worktree
        - branch: Git branch that was checked out in the removed worktree
        - session_id: The session that triggered the worktree removal
        """
        session_id = event.get("session_id", "")
        working_dir = event.get("cwd", "")

        # Extract worktree-specific fields
        worktree_name = event.get("worktree_name", "")
        worktree_path = event.get("worktree_path", event.get("path", ""))
        branch = event.get("branch", event.get("worktree_branch", ""))

        worktree_data = {
            "session_id": session_id,
            "working_directory": working_dir,
            "worktree_name": worktree_name,
            "worktree_path": worktree_path,
            "branch": branch,
            "timestamp": datetime.now(UTC).isoformat(),
            "hook_event_name": "WorktreeRemove",
        }

        _log(
            f"Hook handler: WorktreeRemove - worktree='{worktree_name}', "
            f"path='{worktree_path}', branch='{branch}', session='{session_id[:16]}...'"
        )

        self.hook_handler._emit_socketio_event("", "worktree_remove", worktree_data)

    def handle_config_change_fast(self, event):
        """Handle ConfigChange hook event (Claude Code v2.1.47+).

        Fires when `.claude/` settings or skills files change mid-session.
        Subtypes include: user_settings, project_settings, local_settings,
        policy_settings, skills.

        This allows mpm to react when users modify their Claude Code
        configuration without restarting (e.g., adding a new skill or
        changing a project-level setting).
        """
        session_id = event.get("session_id", "")
        working_dir = event.get("cwd", "")

        # Extract config change details
        # The subtype identifies which settings file changed
        subtype = event.get("subtype", event.get("config_type", "unknown"))
        changed_file = event.get("file", event.get("config_file", ""))
        change_type = event.get("change_type", "modified")  # created/modified/deleted

        config_change_data = {
            "session_id": session_id,
            "working_directory": working_dir,
            "subtype": subtype,
            "changed_file": changed_file,
            "change_type": change_type,
            "timestamp": datetime.now(UTC).isoformat(),
            "hook_event_name": "ConfigChange",
        }

        _log(
            f"Hook handler: ConfigChange - subtype='{subtype}', "
            f"file='{changed_file}', change_type='{change_type}'"
        )

        self.hook_handler._emit_socketio_event("", "config_change", config_change_data)

    def handle_teammate_idle_fast(self, event):
        """Handle TeammateIdle hook event (Claude Code v2.1.47+ Agent Teams).

        Fires when an agent team teammate goes idle (experimental agent teams
        feature). This allows mpm to track when members of a coordinated
        agent team pause, enabling visibility into team-level work patterns
        in the dashboard.

        Note: This is an experimental feature and the event schema may
        evolve as Claude Code's agent teams feature matures.
        """
        session_id = event.get("session_id", "")
        working_dir = event.get("cwd", "")

        # Extract teammate information
        teammate_id = event.get("teammate_id", event.get("agent_id", ""))
        teammate_type = event.get("teammate_type", event.get("agent_type", "unknown"))
        idle_reason = event.get("reason", event.get("idle_reason", "unknown"))

        teammate_idle_data = {
            "session_id": session_id,
            "working_directory": working_dir,
            "teammate_id": teammate_id,
            "teammate_type": teammate_type,
            "idle_reason": idle_reason,
            "timestamp": datetime.now(UTC).isoformat(),
            "hook_event_name": "TeammateIdle",
        }

        _log(
            f"Hook handler: TeammateIdle - teammate_id='{teammate_id}', "
            f"type='{teammate_type}', reason='{idle_reason}'"
        )

        self.hook_handler._emit_socketio_event("", "teammate_idle", teammate_idle_data)

    def handle_task_completed_fast(self, event):
        """Handle TaskCompleted hook event (Claude Code v2.1.47+ Agent Teams).

        Fires when a task is marked complete in agent teams. Enables tracking
        task completion progress across coordinated agent team workflows.
        Provides visibility into which agents are completing work and at what
        rate, even if the user is not actively using mpm's PM features.

        Note: This is an experimental feature and the event schema may
        evolve as Claude Code's agent teams feature matures.
        """
        session_id = event.get("session_id", "")
        working_dir = event.get("cwd", "")

        # Extract task completion details
        task_id = event.get("task_id", "")
        task_title = event.get("task_title", event.get("title", ""))
        completed_by = event.get("completed_by", event.get("agent_id", ""))
        completion_status = event.get("status", "completed")

        task_completed_data = {
            "session_id": session_id,
            "working_directory": working_dir,
            "task_id": task_id,
            "task_title": task_title,
            "completed_by": completed_by,
            "completion_status": completion_status,
            "timestamp": datetime.now(UTC).isoformat(),
            "hook_event_name": "TaskCompleted",
        }

        _log(
            f"Hook handler: TaskCompleted - task_id='{task_id}', "
            f"title='{task_title}', completed_by='{completed_by}'"
        )

        self.hook_handler._emit_socketio_event(
            "", "task_completed", task_completed_data
        )

    def handle_permission_request_fast(self, event):
        """Handle PermissionRequest events.

        WHY this exists:
        - Surface tool-permission decisions on the dashboard for auditing.
        - Provide a single source of truth for the policy decision so the
          dashboard reflects what ``permission_policy.evaluate`` returned.
        - Wire ``PermissionRequest`` into the hook dispatch table (#421); the
          actual allow/deny decision is rendered by ``model_tier_hook.py`` and
          consumed by Claude Code.

        The handler does NOT modify the harness's permission decision — that
        contract belongs to ``model_tier_hook.py`` so the response can be
        emitted before the dashboard event is dispatched. Returning ``None``
        here keeps the dispatcher happy.
        """
        # Lazy import to keep startup paths cheap and avoid circular imports
        # (hook_handler imports event_handlers which would otherwise pull in
        # the policy engine on every hook invocation).
        try:
            from claude_mpm.hooks import permission_policy
        except Exception as exc:  # pragma: no cover - defensive
            _log(f"PermissionRequest: failed to import permission_policy: {exc}")
            return

        decision = permission_policy.evaluate(event)
        tool_name = event.get("tool_name", "")
        tool_input = event.get("tool_input", {}) or {}

        permission_data = {
            "session_id": event.get("session_id", ""),
            "working_directory": event.get("cwd", ""),
            "tool_name": tool_name,
            "decision": decision.decision,
            "reason": decision.reason,
            "agent_id": event.get("agent_id")
            or event.get("subagent_type")
            or event.get("agent_type", ""),
            "timestamp": datetime.now(UTC).isoformat(),
            "hook_event_name": "PermissionRequest",
            # Truncate tool input to keep dashboard payload bounded.
            "tool_input_preview": str(tool_input)[:500],
        }

        _log(
            f"Hook handler: PermissionRequest - tool='{tool_name}', "
            f"decision='{decision.decision}', reason='{decision.reason}'"
        )

        self.hook_handler._emit_socketio_event(
            "", "permission_request", permission_data
        )
        return
