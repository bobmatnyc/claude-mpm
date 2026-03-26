"""GitHubRepoContext — detect GitHub context from a working directory."""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class OpenPR:
    number: int
    title: str
    url: str
    state: str  # "OPEN" | "DRAFT"
    head_branch: str


@dataclass
class GitHubRepoContext:
    """Snapshot of GitHub context for a working directory."""

    owner: str
    repo: str
    full_name: str  # "owner/repo"
    remote_url: str
    current_branch: str
    default_branch: str
    open_prs: list[OpenPR] = field(default_factory=list)
    active_account: str | None = None
    detected_at: float = field(default_factory=time.time)

    @classmethod
    async def detect(
        cls,
        cwd: str | Path,
        timeout_ms: int = 3000,
    ) -> GitHubRepoContext | None:
        """Detect GitHub repo context. Returns None if not a GitHub git repo."""
        cwd = str(cwd)
        try:
            async with asyncio.timeout(timeout_ms / 1000):
                return await cls._detect_impl(cwd)
        except (TimeoutError, Exception) as e:
            logger.debug("GitHub repo detection failed: %s", e)
            return None

    @classmethod
    async def _detect_impl(cls, cwd: str) -> GitHubRepoContext | None:
        # 1. Is this a git repo?
        rc, _, _ = await _run(["git", "rev-parse", "--git-dir"], cwd)
        if rc != 0:
            return None

        # 2. Get remote URL
        rc, remote_url, _ = await _run(["git", "remote", "get-url", "origin"], cwd)
        if rc != 0 or not remote_url:
            return None
        remote_url = remote_url.strip()

        parsed = cls._parse_remote_url(remote_url)
        if not parsed:
            return None  # not a GitHub remote
        owner, repo = parsed

        # 3. Current branch
        rc, branch, _ = await _run(["git", "branch", "--show-current"], cwd)
        current_branch = branch.strip() if rc == 0 and branch.strip() else "HEAD"

        # 4. Default branch (best-effort)
        rc, default_ref, _ = await _run(
            ["git", "symbolic-ref", "refs/remotes/origin/HEAD"], cwd
        )
        if rc == 0 and default_ref.strip():
            default_branch = default_ref.strip().split("/")[-1]
        else:
            default_branch = "main"

        # 5. Open PRs for current branch (best-effort, skip if gh not found)
        open_prs: list[OpenPR] = []
        try:
            rc, pr_output, _ = await _run(
                [
                    "gh",
                    "pr",
                    "list",
                    "--head",
                    current_branch,
                    "--json",
                    "number,title,url,state,headRefName",
                    "--limit",
                    "5",
                ],
                cwd,
            )
            if rc == 0 and pr_output.strip():
                for pr_data in json.loads(pr_output):
                    open_prs.append(
                        OpenPR(
                            number=pr_data["number"],
                            title=pr_data["title"],
                            url=pr_data["url"],
                            state=pr_data["state"],
                            head_branch=pr_data["headRefName"],
                        )
                    )
        except Exception:
            pass

        # 6. Active account (best-effort)
        active_account: str | None = None
        try:
            from claude_mpm.services.github.identity_manager import (
                GitHubIdentityManager,
            )

            mgr = GitHubIdentityManager()
            active_account = mgr.get_active_account(Path(cwd))
        except Exception:
            pass

        return cls(
            owner=owner,
            repo=repo,
            full_name=f"{owner}/{repo}",
            remote_url=remote_url,
            current_branch=current_branch,
            default_branch=default_branch,
            open_prs=open_prs,
            active_account=active_account,
        )

    @staticmethod
    def _parse_remote_url(url: str) -> tuple[str, str] | None:
        """Parse (owner, repo) from GitHub remote URL."""
        # HTTPS: https://github.com/owner/repo.git
        m = re.match(r"https://github\.com/([^/]+)/([^/]+?)(?:\.git)?$", url)
        if m:
            return m.group(1), m.group(2)
        # SSH: git@github.com:owner/repo.git
        m = re.match(r"git@github\.com:([^/]+)/([^/]+?)(?:\.git)?$", url)
        if m:
            return m.group(1), m.group(2)
        return None


async def _run(cmd: list[str], cwd: str) -> tuple[int, str, str]:
    """Run a subprocess and return (returncode, stdout, stderr)."""
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        return proc.returncode or 0, stdout.decode(), stderr.decode()
    except FileNotFoundError:
        return 1, "", "command not found"
    except Exception as e:
        return 1, "", str(e)
