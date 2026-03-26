"""Central hub coordinating all channel adapters and session workers."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .channel_config import load_channels_config
from .session_registry import SessionRegistry
from .session_worker import SessionWorker
from .terminal_adapter import TerminalAdapter
from .vector_search_probe import probe_vector_search

if TYPE_CHECKING:
    from .channel_config import ChannelsConfig
    from .models import ChannelMessage, ChannelSession

logger = logging.getLogger(__name__)

# Path for hub state file used by CLI IPC
_HUB_STATE_PATH = Path.home() / ".claude-mpm" / "channels" / "hub-state.json"


def read_hub_state() -> dict | None:
    """Read hub state file; return None if not present or unreadable."""
    try:
        if _HUB_STATE_PATH.exists():
            return json.loads(_HUB_STATE_PATH.read_text())
    except Exception:
        pass
    return None


class ChannelHub:
    """Central hub: manages sessions, routes messages, owns channel adapters."""

    def __init__(
        self,
        runner: Any,
        config: ChannelsConfig | None = None,
    ) -> None:
        self.runner = runner
        self.config = config or load_channels_config()
        self.registry = SessionRegistry()
        self._workers: dict[str, SessionWorker] = {}
        self._adapters: list[Any] = []
        self._running = False
        self._started_at: float = 0.0
        try:
            from claude_mpm.services.github.identity_manager import (
                GitHubIdentityManager,
            )

            self._identity_manager = GitHubIdentityManager()
        except Exception:
            self._identity_manager = None

    def _write_hub_state(self) -> None:
        """Write hub state to disk for CLI IPC."""
        try:
            _HUB_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
            sessions = []
            for sess in self.registry._sessions.values():
                sessions.append(
                    {
                        "id": sess.session_id or "",
                        "name": sess.name,
                        "cwd": sess.cwd,
                        "state": sess.state.value,
                        "created_at": sess.created_at,
                    }
                )
            state = {
                "pid": os.getpid(),
                "started_at": self._started_at,
                "version": self._get_version(),
                "sessions": sessions,
            }
            _HUB_STATE_PATH.write_text(json.dumps(state, indent=2))
        except Exception:
            logger.debug("Failed to write hub state", exc_info=True)

    def _clear_hub_state(self) -> None:
        """Remove hub state file on clean shutdown."""
        try:
            if _HUB_STATE_PATH.exists():
                _HUB_STATE_PATH.unlink()
        except Exception:
            logger.debug("Failed to clear hub state", exc_info=True)

    @staticmethod
    def _get_version() -> str:
        try:
            from claude_mpm import __version__

            return __version__
        except Exception:
            return "unknown"

    async def start(self) -> None:
        """Start the hub and all enabled adapters."""
        self._running = True
        self._started_at = time.time()
        # Terminal adapter is always enabled in SDK+channels mode
        terminal = TerminalAdapter(self)
        self._adapters.append(terminal)
        await terminal.start()
        self._write_hub_state()
        logger.info("ChannelHub started")

    async def stop(self) -> None:
        """Gracefully stop all workers and adapters."""
        self._running = False
        for adapter in self._adapters:
            try:
                await adapter.stop()
            except Exception:
                logger.exception("Error stopping adapter %s", adapter.channel_name)
        for name, worker in list(self._workers.items()):
            try:
                await worker.stop()
            except Exception:
                logger.exception("Error stopping worker for session '%s'", name)
        self._workers.clear()
        self._clear_hub_state()
        logger.info("ChannelHub stopped")

    async def create_session(
        self,
        name: str,
        cwd: str,
        channel: str,
        user_id: str,
        user_display: str = "",
    ) -> ChannelSession:
        """Create a new named session and start its worker."""
        session = await self.registry.create(
            name=name,
            cwd=cwd,
            channel=channel,
            user_id=user_id,
        )
        # Probe vector search availability
        vector_ok = False
        if self.config.vector_search.auto_probe:
            vector_ok = await probe_vector_search(
                cwd, self.config.vector_search.probe_timeout_ms
            )
            if vector_ok:
                logger.info("mcp-vector-search available for session '%s'", name)

        # Probe GitHub context and MCP availability
        github_ctx = None
        github_mcp_cfg = None
        try:
            from claude_mpm.services.github.mcp_probe import probe_github_mcp
            from claude_mpm.services.github.repo_context import GitHubRepoContext

            results = await asyncio.gather(
                GitHubRepoContext.detect(cwd, timeout_ms=3000),
                probe_github_mcp(
                    cwd, getattr(self, "_identity_manager", None), timeout_ms=2000
                ),
                return_exceptions=True,
            )
            github_ctx = (
                results[0] if not isinstance(results[0], BaseException) else None
            )
            github_mcp_cfg = (
                results[1] if not isinstance(results[1], BaseException) else None
            )
        except Exception:
            pass

        # Store GitHub context on session
        if github_ctx is not None:
            session.github_context = github_ctx

        worker = SessionWorker(
            session=session,
            registry=self.registry,
            runner=self.runner,
            vector_search_ok=vector_ok,
            github_context=github_ctx,
            github_mcp_config=github_mcp_cfg,
        )
        self._workers[name] = worker
        await worker.start()
        self._write_hub_state()
        return session

    async def join_session(
        self,
        name: str,
        channel: str,
        user_id: str,
    ) -> ChannelSession:
        """Join an existing session."""
        return await self.registry.join(name, channel, user_id)

    async def route_message(self, message: ChannelMessage) -> None:
        """Route an incoming message to the appropriate session worker."""
        worker = self._workers.get(message.session_name)
        if worker is None:
            logger.warning("No worker for session '%s'", message.session_name)
            if message.reply_fn:
                await message.reply_fn(
                    f"Session '{message.session_name}' not found. "
                    f"Use /new {message.session_name} to create it."
                )
            return
        await worker.send(message)

    async def run_until_stopped(self) -> None:
        """Block until hub is stopped."""
        while self._running:
            await asyncio.sleep(0.1)
