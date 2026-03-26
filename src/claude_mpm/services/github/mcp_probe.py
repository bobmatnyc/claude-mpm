"""Non-blocking probe for GitHub MCP server availability."""

from __future__ import annotations

import asyncio
import logging
import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .identity_manager import GitHubIdentityManager

logger = logging.getLogger(__name__)


@dataclass
class GitHubMCPConfig:
    """Ready-to-use mcp_servers entry for ClaudeAgentOptions."""

    server_name: str = "github"
    config: dict = field(default_factory=dict)


async def probe_github_mcp(
    cwd: str,
    identity_manager: GitHubIdentityManager | None = None,
    timeout_ms: int = 2000,
) -> GitHubMCPConfig | None:
    """
    Return GitHubMCPConfig if:
    - cwd contains a .git directory
    - npx is available on PATH
    - A GITHUB_TOKEN can be resolved

    Returns None gracefully on any failure.
    """
    try:
        async with asyncio.timeout(timeout_ms / 1000):
            return await _probe_impl(cwd, identity_manager)
    except (TimeoutError, Exception) as e:
        logger.debug("GitHub MCP probe failed: %s", e)
        return None


async def _probe_impl(
    cwd: str,
    identity_manager: GitHubIdentityManager | None,
) -> GitHubMCPConfig | None:
    # Must be a git repo
    if not (Path(cwd) / ".git").exists():
        return None

    # npx must be available
    if not shutil.which("npx"):
        logger.debug("npx not found; GitHub MCP server unavailable")
        return None

    # Resolve token
    token: str | None = None
    if identity_manager is not None:
        token = identity_manager.get_token()
    if not token:
        token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        # Try gh auth token
        try:
            proc = await asyncio.create_subprocess_exec(
                "gh",
                "auth",
                "token",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )
            stdout, _ = await proc.communicate()
            token = stdout.decode().strip() or None
        except Exception:
            pass
    if not token:
        logger.debug("No GITHUB_TOKEN available; GitHub MCP server unavailable")
        return None

    return GitHubMCPConfig(
        server_name="github",
        config={
            "type": "stdio",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-github"],
            "env": {"GITHUB_TOKEN": token},
        },
    )
