"""Process manager for claude subprocess sessions.

Manages one claude CLI subprocess per UI session, handling stdin/stdout
communication in stream-json format.
"""

import asyncio
import json
import logging
import signal
import uuid
from asyncio.subprocess import PIPE
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from claude_mpm.services.ui_service.models.message import StreamEvent
from claude_mpm.services.ui_service.models.session import (
    ManagedSessionState,
    SessionCreate,
    SessionStatus,
)

logger = logging.getLogger(__name__)


@dataclass
class ManagedSession:
    """Internal state for a single managed claude subprocess session.

    Attributes:
        id: UI service session UUID.
        claude_session_id: --resume token captured from stream-json system event.
        process: asyncio subprocess handle (None when stubbed).
        status: Current lifecycle status.
        model: Active model identifier.
        cwd: Working directory of the subprocess.
        created_at: Session creation time.
        last_activity: Time of last input/output.
        context_tokens_used: Tokens consumed in context window.
        context_tokens_total: Context window capacity.
        permission_mode: Active permission mode string.
        message_history: Ordered list of user/assistant message dicts.
        output_queue: Parsed stream-json events for current turn.
        _stdin_lock: Serialises writes to process stdin.
    """

    id: str
    claude_session_id: str | None
    process: asyncio.subprocess.Process | None
    status: SessionStatus
    model: str
    cwd: str
    created_at: datetime
    last_activity: datetime
    context_tokens_used: int
    context_tokens_total: int
    permission_mode: str
    message_history: list[dict] = field(default_factory=list)
    output_queue: asyncio.Queue = field(default_factory=asyncio.Queue)
    _stdin_lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    def to_state(self) -> ManagedSessionState:
        """Convert to the public-facing Pydantic state model."""
        pct = (
            (self.context_tokens_used / self.context_tokens_total * 100)
            if self.context_tokens_total > 0
            else 0.0
        )
        return ManagedSessionState(
            id=self.id,
            claude_session_id=self.claude_session_id,
            status=self.status,
            model=self.model,
            cwd=self.cwd,
            created_at=self.created_at,
            last_activity=self.last_activity,
            context_tokens_used=self.context_tokens_used,
            context_tokens_total=self.context_tokens_total,
            context_percent_used=round(pct, 2),
            permission_mode=self.permission_mode,
        )


class ProcessManager:
    """Manages the lifecycle of claude CLI subprocesses.

    Each UI session maps to one persistent claude subprocess that is
    communicated with via stdin/stdout using the stream-json output format.

    NOTE: Subprocess creation is stubbed when the claude CLI is not installed,
    allowing the service to start and respond without a live claude binary.
    All logic paths that would use a real process gracefully degrade.

    Attributes:
        max_sessions: Maximum concurrent sessions.
        session_timeout_minutes: Inactivity timeout for cleanup.
        _sessions: Mapping of session id -> ManagedSession.
        _cleanup_task: Background task for periodic cleanup.
    """

    def __init__(self, max_sessions: int = 10, session_timeout_minutes: int = 60):
        self.max_sessions = max_sessions
        self.session_timeout_minutes = session_timeout_minutes
        self._sessions: dict[str, ManagedSession] = {}
        self._cleanup_task: asyncio.Task | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Start the process manager and background cleanup task."""
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("ProcessManager started")

    async def stop(self) -> None:
        """Stop all sessions and cancel background tasks."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        for session_id in list(self._sessions.keys()):
            await self.terminate(session_id)
        logger.info("ProcessManager stopped")

    # ------------------------------------------------------------------
    # Session CRUD
    # ------------------------------------------------------------------

    async def create_session(self, config: SessionCreate) -> ManagedSession:
        """Spawn a new claude subprocess and return a ManagedSession.

        Args:
            config: Parameters for the new session.

        Returns:
            The created ManagedSession.

        Raises:
            RuntimeError: If the maximum number of sessions has been reached.
        """
        if len(self._sessions) >= self.max_sessions:
            raise RuntimeError(
                f"Maximum sessions ({self.max_sessions}) reached. "
                "Terminate an existing session first."
            )

        session_id = str(uuid.uuid4())
        now = datetime.now(tz=UTC)
        cwd = config.cwd or str(Path.cwd())
        model = config.model or "claude-opus-4-5"

        # Build subprocess command
        cmd = ["claude", "--output-format", "stream-json", "--print"]
        if config.resume_id:
            cmd += ["--resume", config.resume_id]
        if config.bare:
            cmd += ["--bare"]
        if config.model:
            cmd += ["--model", config.model]

        process: asyncio.subprocess.Process | None = None
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=PIPE,
                stdout=PIPE,
                stderr=PIPE,
                cwd=cwd,
            )
            logger.info(
                "Spawned claude subprocess pid=%s session=%s", process.pid, session_id
            )
        except FileNotFoundError:
            # claude CLI not installed — operate in stub mode
            logger.warning(
                "claude CLI not found; session %s will operate in stub mode", session_id
            )
        except Exception as exc:
            logger.error("Failed to spawn claude process: %s", exc)

        session = ManagedSession(
            id=session_id,
            claude_session_id=config.resume_id,
            process=process,
            status=SessionStatus.idle if process else SessionStatus.starting,
            model=model,
            cwd=cwd,
            created_at=now,
            last_activity=now,
            context_tokens_used=0,
            context_tokens_total=200000,
            permission_mode=config.permission_mode,
        )

        self._sessions[session_id] = session

        if process:
            # Start background stdout reader
            asyncio.create_task(
                self._read_stdout(session),
                name=f"stdout-reader-{session_id}",
            )

        return session

    def get_session(self, session_id: str) -> ManagedSession:
        """Retrieve a session by ID.

        Args:
            session_id: The UI service session UUID.

        Returns:
            The ManagedSession.

        Raises:
            KeyError: If no session with that ID exists.
        """
        if session_id not in self._sessions:
            raise KeyError(f"Session {session_id} not found")
        return self._sessions[session_id]

    def list_sessions(self) -> list[ManagedSession]:
        """Return all active sessions."""
        return list(self._sessions.values())

    async def terminate(self, session_id: str) -> None:
        """Terminate a session's subprocess with SIGTERM.

        Args:
            session_id: The UI service session UUID.
        """
        session = self._sessions.get(session_id)
        if not session:
            return

        session.status = SessionStatus.terminated

        if session.process and session.process.returncode is None:
            try:
                session.process.terminate()
                await asyncio.wait_for(session.process.wait(), timeout=5.0)
            except TimeoutError:
                session.process.kill()
            except ProcessLookupError:
                pass

        del self._sessions[session_id]
        logger.info("Terminated session %s", session_id)

    # ------------------------------------------------------------------
    # Messaging
    # ------------------------------------------------------------------

    async def send_message(
        self, session_id: str, content: str
    ) -> AsyncIterator[StreamEvent]:
        """Send a message to a session and stream back parsed events.

        Writes the message to the subprocess stdin then yields StreamEvent
        objects as they arrive on stdout. Falls back to a stub response when
        no live process is available.

        Args:
            session_id: The UI service session UUID.
            content: The user message text.

        Yields:
            StreamEvent objects parsed from the claude stream-json output.
        """
        session = self.get_session(session_id)
        session.last_activity = datetime.now(tz=UTC)

        # Record in history
        session.message_history.append({"role": "user", "content": content})

        if not session.process or session.process.returncode is not None:
            # Stub mode: yield a synthetic response
            async for event in self._stub_response(session, content):
                yield event
            return

        async with session._stdin_lock:
            session.status = SessionStatus.busy
            try:
                payload = json.dumps({"type": "user", "message": content}) + "\n"
                session.process.stdin.write(payload.encode())
                await session.process.stdin.drain()
            except (BrokenPipeError, ConnectionResetError) as exc:
                logger.error("Stdin write failed for session %s: %s", session_id, exc)
                session.status = SessionStatus.terminated
                yield StreamEvent(type="error", data={"message": str(exc)})
                return

        # Drain the output queue until a result event signals completion
        while True:
            try:
                event: StreamEvent = await asyncio.wait_for(
                    session.output_queue.get(), timeout=120.0
                )
            except TimeoutError:
                session.status = SessionStatus.idle
                yield StreamEvent(
                    type="timeout", data={"message": "Response timed out"}
                )
                return

            yield event

            if event.type in ("result", "error"):
                session.status = SessionStatus.idle
                session.last_activity = datetime.now(tz=UTC)
                break

    async def send_command(self, session_id: str, command: str) -> None:
        """Write a slash command directly to the session's stdin.

        Args:
            session_id: The UI service session UUID.
            command: The command string, e.g. '/compact', '/clear'.
        """
        session = self.get_session(session_id)
        if not session.process or session.process.returncode is not None:
            logger.warning("Cannot send command to stub/dead session %s", session_id)
            return

        async with session._stdin_lock:
            session.process.stdin.write((command + "\n").encode())
            await session.process.stdin.drain()
        session.last_activity = datetime.now(tz=UTC)

    async def interrupt(self, session_id: str) -> None:
        """Send SIGINT to the session's subprocess.

        Args:
            session_id: The UI service session UUID.
        """
        session = self.get_session(session_id)
        if session.process and session.process.returncode is None:
            try:
                session.process.send_signal(signal.SIGINT)
                session.status = SessionStatus.idle
            except ProcessLookupError:
                pass

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _read_stdout(self, session: ManagedSession) -> None:
        """Background task: read stream-json lines from subprocess stdout.

        Parses each newline-delimited JSON object and enqueues it as a
        StreamEvent. Also updates session metadata (claude_session_id,
        context tokens) as events arrive.

        Args:
            session: The session whose stdout to consume.
        """
        if not session.process or not session.process.stdout:
            return

        try:
            async for raw_line in session.process.stdout:
                line = raw_line.decode("utf-8", errors="replace").strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    logger.debug("Non-JSON stdout line: %s", line[:200])
                    continue

                event = self._parse_stream_event(session, data)
                await session.output_queue.put(event)

        except Exception as exc:
            logger.error("stdout reader error for session %s: %s", session.id, exc)
        finally:
            session.status = SessionStatus.terminated

    def _parse_stream_event(self, session: ManagedSession, data: dict) -> StreamEvent:
        """Parse a raw stream-json dict into a StreamEvent, updating session state.

        Args:
            session: The session to update.
            data: Parsed JSON dict from a single stdout line.

        Returns:
            A StreamEvent instance.
        """
        event_type = data.get("type", "unknown")

        # Capture Claude session ID from system init event
        if event_type == "system":
            session_id_val = data.get("session_id") or data.get("sessionId")
            if session_id_val and not session.claude_session_id:
                session.claude_session_id = session_id_val
                logger.debug(
                    "Captured claude_session_id=%s for session %s",
                    session_id_val,
                    session.id,
                )

        # Update token counts from assistant usage events
        if event_type == "assistant" and "usage" in data:
            usage = data["usage"]
            if isinstance(usage, dict):
                session.context_tokens_used = usage.get(
                    "input_tokens", session.context_tokens_used
                )
                total = (
                    usage.get("cache_creation_input_tokens", 0)
                    + usage.get("cache_read_input_tokens", 0)
                    + usage.get("input_tokens", 0)
                )
                if total:
                    session.context_tokens_used = total

        # Capture assistant content
        content = None
        if event_type == "assistant":
            msg = data.get("message", {})
            if isinstance(msg, dict):
                content_list = msg.get("content", [])
                if isinstance(content_list, list):
                    texts = [
                        c.get("text", "")
                        for c in content_list
                        if isinstance(c, dict) and c.get("type") == "text"
                    ]
                    content = "".join(texts) or None
                elif isinstance(content_list, str):
                    content = content_list

        # When result arrives, record assistant turn
        if event_type == "result":
            result_text = data.get("result", "")
            if result_text:
                session.message_history.append(
                    {"role": "assistant", "content": result_text}
                )
            session.status = SessionStatus.idle

        return StreamEvent(
            type=event_type,
            session_id=data.get("session_id") or data.get("sessionId"),
            content=content,
            usage=data.get("usage"),
            data=data,
        )

    async def _stub_response(
        self, session: ManagedSession, content: str
    ) -> AsyncIterator[StreamEvent]:
        """Yield synthetic events when no live process is available.

        Args:
            session: The session in stub mode.
            content: The user message (echoed back in stub).

        Yields:
            StreamEvent objects simulating a minimal response.
        """
        session.status = SessionStatus.busy
        stub_text = (
            f"[UI Service stub mode — claude CLI not available. Echo: {content[:80]}]"
        )
        session.message_history.append({"role": "assistant", "content": stub_text})

        yield StreamEvent(
            type="assistant",
            content=stub_text,
            data={"type": "assistant", "message": {"content": stub_text}},
        )
        yield StreamEvent(
            type="result",
            data={"type": "result", "result": stub_text, "stop_reason": "end_turn"},
        )
        session.status = SessionStatus.idle
        session.last_activity = datetime.now(tz=UTC)

    async def _cleanup_loop(self) -> None:
        """Periodically remove sessions that have exceeded the timeout."""
        import asyncio as _asyncio

        while True:
            await _asyncio.sleep(60)
            cutoff = datetime.now(tz=UTC)
            for session_id, session in list(self._sessions.items()):
                idle_seconds = (cutoff - session.last_activity).total_seconds()
                if idle_seconds > self.session_timeout_minutes * 60:
                    logger.info(
                        "Cleaning up idle session %s (idle %.0fs)",
                        session_id,
                        idle_seconds,
                    )
                    await self.terminate(session_id)
