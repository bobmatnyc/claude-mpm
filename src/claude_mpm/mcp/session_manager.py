"""Session manager for MCP Session Server.

This module provides the SessionManager class that orchestrates session
lifecycle, concurrency control, and state management for claude-mpm
headless sessions.
"""

import asyncio
from datetime import UTC, datetime

from claude_mpm.mcp.errors import SessionError
from claude_mpm.mcp.models import SessionInfo, SessionResult, SessionStatus
from claude_mpm.mcp.subprocess_wrapper import ClaudeMPMSubprocess


class SessionManager:
    """Manages lifecycle of claude-mpm headless sessions.

    This class provides:
    - Session tracking with status transitions
    - Concurrency control via asyncio.Semaphore
    - Thread-safe session dictionary modifications via asyncio.Lock
    - Start, continue, stop operations on sessions

    Example:
        manager = SessionManager(max_concurrent=5)
        result = await manager.start_session(
            prompt="Hello",
            working_directory="/path/to/project"
        )
        print(f"Session {result.session_id} started")
    """

    def __init__(
        self,
        max_concurrent: int = 5,
        default_timeout: float | None = None,
    ) -> None:
        """Initialize SessionManager.

        Args:
            max_concurrent: Maximum number of concurrent sessions (default: 5)
            default_timeout: Default timeout for session operations in seconds
        """
        self._sessions: dict[str, SessionInfo] = {}
        self._processes: dict[str, ClaudeMPMSubprocess] = {}
        self._lock = asyncio.Lock()
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._default_timeout = default_timeout

    def _now_iso(self) -> str:
        """Return current UTC time in ISO format."""
        return datetime.now(UTC).isoformat()

    async def _update_session_status(
        self,
        session_id: str,
        status: SessionStatus,
        last_output: str | None = None,
        increment_messages: bool = False,
    ) -> None:
        """Update session status and metadata.

        Args:
            session_id: The session ID to update
            status: New status for the session
            last_output: Optional output to store
            increment_messages: Whether to increment message count
        """
        async with self._lock:
            if session_id not in self._sessions:
                return

            session = self._sessions[session_id]
            # Create new SessionInfo with updated fields (dataclass is immutable-ish)
            self._sessions[session_id] = SessionInfo(
                session_id=session.session_id,
                status=status,
                start_time=session.start_time,
                working_directory=session.working_directory,
                last_activity=self._now_iso(),
                message_count=session.message_count + (1 if increment_messages else 0),
                last_output=last_output
                if last_output is not None
                else session.last_output,
            )

    async def start_session(
        self,
        prompt: str,
        working_directory: str | None = None,
        no_hooks: bool = False,
        no_tickets: bool = False,
        timeout: float | None = None,
        env_overrides: dict[str, str] | None = None,
    ) -> SessionResult:
        """Start a new claude-mpm session.

        Args:
            prompt: The prompt to send to claude-mpm
            working_directory: Working directory for the session
            no_hooks: Disable hooks in claude-mpm
            no_tickets: Disable ticket tracking
            timeout: Timeout in seconds (uses default if not specified)
            env_overrides: Environment variable overrides

        Returns:
            SessionResult with session_id and output

        Raises:
            SessionError: If session fails to start or times out
        """
        async with self._semaphore:
            subprocess = ClaudeMPMSubprocess(
                working_directory=working_directory,
                env_overrides=env_overrides,
            )

            session_id: str | None = None
            try:
                # Start the subprocess and get session ID
                session_id, _ = await subprocess.start_session(
                    prompt=prompt,
                    no_hooks=no_hooks,
                    no_tickets=no_tickets,
                )

                # Create initial session info
                session_info = SessionInfo(
                    session_id=session_id,
                    status=SessionStatus.STARTING,
                    start_time=self._now_iso(),
                    working_directory=subprocess.working_directory,
                    last_activity=self._now_iso(),
                    message_count=0,
                )

                # Register session
                async with self._lock:
                    self._sessions[session_id] = session_info
                    self._processes[session_id] = subprocess

                # Update to ACTIVE status
                await self._update_session_status(session_id, SessionStatus.ACTIVE)

                # Wait for completion
                effective_timeout = timeout or self._default_timeout
                result = await subprocess.wait_for_completion(timeout=effective_timeout)

                # Update final status
                final_status = (
                    SessionStatus.COMPLETED if result.success else SessionStatus.ERROR
                )
                await self._update_session_status(
                    session_id,
                    final_status,
                    last_output=result.output,
                    increment_messages=True,
                )

                return result

            except SessionError:
                if session_id:
                    await self._update_session_status(session_id, SessionStatus.ERROR)
                raise

            except Exception as e:
                if session_id:
                    await self._update_session_status(session_id, SessionStatus.ERROR)
                raise SessionError(
                    f"Failed to start session: {e}",
                    session_id=session_id,
                ) from e

    async def continue_session(
        self,
        session_id: str,
        prompt: str,
        fork: bool = False,
        timeout: float | None = None,
    ) -> SessionResult:
        """Continue an existing session with a new prompt.

        Args:
            session_id: The session ID to continue
            prompt: The prompt to send
            fork: Whether to fork the session (creates a new branch)
            timeout: Timeout in seconds (uses default if not specified)

        Returns:
            SessionResult with output

        Raises:
            SessionError: If session not found or operation fails
        """
        async with self._semaphore:
            # Get or create subprocess for this session
            async with self._lock:
                if session_id in self._processes:
                    subprocess = self._processes[session_id]
                    working_dir = self._sessions[session_id].working_directory
                else:
                    # Session exists in claude-mpm but not tracked here
                    working_dir = None
                    subprocess = ClaudeMPMSubprocess(working_directory=working_dir)

            try:
                # Continue the session
                await subprocess.continue_session(
                    session_id=session_id,
                    prompt=prompt,
                    fork=fork,
                )

                # Update or create session tracking
                async with self._lock:
                    if session_id not in self._sessions:
                        self._sessions[session_id] = SessionInfo(
                            session_id=session_id,
                            status=SessionStatus.ACTIVE,
                            start_time=self._now_iso(),
                            working_directory=subprocess.working_directory,
                            last_activity=self._now_iso(),
                            message_count=0,
                        )
                    self._processes[session_id] = subprocess

                await self._update_session_status(session_id, SessionStatus.ACTIVE)

                # Wait for completion
                effective_timeout = timeout or self._default_timeout
                result = await subprocess.wait_for_completion(timeout=effective_timeout)

                # Update final status
                final_status = (
                    SessionStatus.COMPLETED if result.success else SessionStatus.ERROR
                )
                await self._update_session_status(
                    session_id,
                    final_status,
                    last_output=result.output,
                    increment_messages=True,
                )

                return result

            except SessionError:
                await self._update_session_status(session_id, SessionStatus.ERROR)
                raise

            except Exception as e:
                await self._update_session_status(session_id, SessionStatus.ERROR)
                raise SessionError(
                    f"Failed to continue session: {e}",
                    session_id=session_id,
                ) from e

    async def get_session_status(self, session_id: str) -> SessionInfo | None:
        """Get the current status of a session.

        Args:
            session_id: The session ID to query

        Returns:
            SessionInfo if found, None otherwise
        """
        async with self._lock:
            return self._sessions.get(session_id)

    async def list_sessions(
        self,
        status: SessionStatus | None = None,
    ) -> list[SessionInfo]:
        """List all tracked sessions.

        Args:
            status: Optional filter by status

        Returns:
            List of SessionInfo objects
        """
        async with self._lock:
            sessions = list(self._sessions.values())

        if status is not None:
            sessions = [s for s in sessions if s.status == status]

        return sessions

    async def stop_session(
        self,
        session_id: str,
        force: bool = False,
    ) -> bool:
        """Stop a running session.

        Args:
            session_id: The session ID to stop
            force: Whether to forcefully kill the process

        Returns:
            True if session was stopped, False if not found
        """
        async with self._lock:
            if session_id not in self._sessions:
                return False

            subprocess = self._processes.get(session_id)

        if subprocess:
            await subprocess.terminate(force=force)

        await self._update_session_status(session_id, SessionStatus.STOPPED)
        return True

    async def cleanup_session(self, session_id: str) -> bool:
        """Remove a session from tracking.

        This should be called after a session is no longer needed.

        Args:
            session_id: The session ID to remove

        Returns:
            True if session was removed, False if not found
        """
        async with self._lock:
            if session_id not in self._sessions:
                return False

            # Stop the process if still running
            subprocess = self._processes.pop(session_id, None)
            if subprocess and subprocess.process:
                await subprocess.terminate(force=True)

            del self._sessions[session_id]
            return True

    async def get_active_count(self) -> int:
        """Get the number of currently active sessions.

        Returns:
            Count of sessions with ACTIVE or STARTING status
        """
        async with self._lock:
            return sum(
                1
                for s in self._sessions.values()
                if s.status in (SessionStatus.ACTIVE, SessionStatus.STARTING)
            )

    async def shutdown(self) -> None:
        """Shutdown all active sessions.

        This should be called when the server is shutting down.
        """
        async with self._lock:
            session_ids = list(self._sessions.keys())

        for session_id in session_ids:
            await self.stop_session(session_id, force=True)

        async with self._lock:
            self._sessions.clear()
            self._processes.clear()
