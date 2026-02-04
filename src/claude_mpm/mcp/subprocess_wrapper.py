"""Async subprocess wrapper for claude-mpm headless mode.

This module provides an async interface for running claude-mpm in headless
mode, enabling the MCP Session Server to manage Claude Code sessions
programmatically.
"""

import asyncio
import os
import uuid
from pathlib import Path
from typing import Any, AsyncIterator

from claude_mpm.mcp.errors import SessionError
from claude_mpm.mcp.models import SessionResult
from claude_mpm.mcp.ndjson_parser import (
    NDJSONStreamParser,
    extract_session_id_from_stream,
)


class ClaudeMPMSubprocess:
    """Async subprocess wrapper for claude-mpm headless mode.

    This class manages the lifecycle of claude-mpm subprocess invocations,
    providing methods to start, continue, and stop sessions.
    """

    def __init__(
        self,
        working_directory: str | None = None,
        env_overrides: dict[str, str] | None = None,
    ):
        self.working_directory = working_directory or str(Path.cwd())
        self.env = self._prepare_environment(env_overrides)
        self.process: asyncio.subprocess.Process | None = None
        self.parser = NDJSONStreamParser()
        self._session_id: str | None = None

    def _prepare_environment(
        self,
        overrides: dict[str, str] | None = None,
    ) -> dict[str, str]:
        env = os.environ.copy()
        env["DISABLE_TELEMETRY"] = "1"
        env["CI"] = "true"
        env["CLAUDE_MPM_USER_PWD"] = self.working_directory
        if overrides:
            env.update(overrides)
        return env

    def _build_command(
        self,
        prompt: str,
        resume_session: str | None = None,
        fork: bool = False,
        no_hooks: bool = False,
        no_tickets: bool = False,
    ) -> list[str]:
        cmd = [
            "claude-mpm",
            "run",
            "--headless",
            "--non-interactive",
        ]

        if no_hooks:
            cmd.append("--no-hooks")
        if no_tickets:
            cmd.append("--no-tickets")

        if resume_session:
            cmd.extend(["--resume", resume_session])
            if fork:
                cmd.append("--fork-session")

        cmd.extend(["-i", prompt])

        return cmd

    async def start_session(
        self,
        prompt: str,
        no_hooks: bool = False,
        no_tickets: bool = False,
    ) -> tuple[str, asyncio.subprocess.Process]:
        cmd = self._build_command(
            prompt=prompt,
            no_hooks=no_hooks,
            no_tickets=no_tickets,
        )

        self.process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=self.working_directory,
            env=self.env,
        )

        self._session_id = await self._extract_session_id()
        return self._session_id, self.process

    async def continue_session(
        self,
        session_id: str,
        prompt: str,
        fork: bool = False,
    ) -> asyncio.subprocess.Process:
        cmd = self._build_command(
            prompt=prompt,
            resume_session=session_id,
            fork=fork,
        )

        self.process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=self.working_directory,
            env=self.env,
        )

        self._session_id = session_id
        return self.process

    async def _extract_session_id(self) -> str:
        if not self.process or not self.process.stdout:
            raise SessionError("Process not started or stdout not available")

        session_id = await extract_session_id_from_stream(self.process.stdout)
        if not session_id:
            session_id = f"mpm-{uuid.uuid4().hex[:8]}"

        self.parser.session_id = session_id
        return session_id

    @property
    def session_id(self) -> str | None:
        return self._session_id

    async def stream_output(self) -> AsyncIterator[dict[str, Any]]:
        if not self.process or not self.process.stdout:
            raise SessionError("Process not started or stdout not available")

        async for message in self.parser.parse_stream(self.process.stdout):
            yield message

    async def wait_for_completion(
        self,
        timeout: float | None = None,
    ) -> SessionResult:
        if not self.process:
            raise SessionError("Process not started")

        try:
            messages = []
            async for message in self.stream_output():
                messages.append(message)

            if timeout:
                returncode = await asyncio.wait_for(
                    self.process.wait(),
                    timeout=timeout,
                )
            else:
                returncode = await self.process.wait()

            stderr_output = ""
            if self.process.stderr:
                stderr_data = await self.process.stderr.read()
                stderr_output = stderr_data.decode() if stderr_data else ""

            return SessionResult(
                success=self.parser.is_success() or returncode == 0,
                session_id=self.parser.session_id or self._session_id,
                output=self._format_assistant_output(),
                error=self.parser.get_error()
                or (stderr_output if returncode != 0 else None),
                messages=messages,
            )

        except asyncio.TimeoutError as err:
            await self.terminate()
            raise SessionError(
                f"Session timed out after {timeout}s",
                session_id=self.parser.session_id or self._session_id,
            ) from err

    def _format_assistant_output(self) -> str:
        assistant_msgs = self.parser.get_assistant_messages()
        outputs = []
        for msg in assistant_msgs:
            content = msg.get("message", {}).get("content", "")
            if content:
                outputs.append(content)
        return "\n".join(outputs)

    async def terminate(self, force: bool = False) -> None:
        if not self.process:
            return

        try:
            self.process.terminate()
            await asyncio.wait_for(self.process.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            if force:
                self.process.kill()
                await self.process.wait()
