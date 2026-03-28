"""GitHub channel adapter — polls Issues/PRs and routes them as MPM sessions."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import logging
import os
import re
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

import httpx

from .base_adapter import BaseAdapter, BufferedOutputMixin
from .github_session_mapper import GitHubSessionMapper
from .models import ChannelMessage

if TYPE_CHECKING:
    from .channel_config import GitHubChannelConfig
    from .channel_hub import ChannelHub
    from .models import SessionEvent

logger = logging.getLogger(__name__)

_GITHUB_API = "https://api.github.com"
_ACCEPT_HEADER = "application/vnd.github+json"


def _entity_key(owner: str, repo: str, kind: str, number: int) -> str:
    """Build the canonical entity key for a GitHub issue or pull request."""
    return f"{owner}/{repo}/{kind}/{number}"


def _session_name(owner: str, repo: str, kind: str, number: int) -> str:
    """Build the MPM session name for a GitHub issue or pull request."""
    kind_short = "issue" if kind == "issues" else "pr"
    return f"github-{owner}-{repo}-{kind_short}-{number}"


def _strip_markdown(text: str, max_chars: int = 2000) -> str:
    """Remove common markdown syntax and truncate to max_chars."""
    # Remove code fences
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    # Remove inline code
    text = re.sub(r"`[^`]+`", "", text)
    # Remove headings markup
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    # Remove bold/italic
    text = re.sub(r"[*_]{1,3}([^*_]+)[*_]{1,3}", r"\1", text)
    # Remove links but keep text
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    # Collapse whitespace
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()[:max_chars]


class GitHubAdapter(BaseAdapter, BufferedOutputMixin):
    """GitHub channel adapter.

    Polling mode (default):
    - Polls GET /repos/{owner}/{repo}/issues?labels={label}&state=open every N seconds
    - Also polls pull requests with the same label gate
    - Creates MPM sessions for new labeled items
    - Posts a "starting" comment, then streams output back via PATCH (debounced)

    Webhook mode (optional, requires aiohttp):
    - Listens on configurable port for GitHub webhook events
    - Verifies X-Hub-Signature-256 using HMAC-SHA256
    - Handles: issues.opened, issues.labeled, pull_request.opened,
               pull_request.labeled, issue_comment.created (body contains @mpm)
    """

    channel_name = "github"

    def __init__(self, hub: ChannelHub, config: GitHubChannelConfig) -> None:
        super().__init__(hub)
        self._init_buffered_output()
        self.config = config
        self._mapper = GitHubSessionMapper()
        self._running = False
        self._poll_task: asyncio.Task | None = None
        self._webhook_task: asyncio.Task | None = None
        self._webhook_runner: Any = None  # aiohttp AppRunner
        # GitHub-specific: chunk-based buffer for incremental PATCH
        self._output_chunk_buffers: dict[str, list[str]] = {}
        # Accumulated text: session_name -> str (full text for the comment)
        self._accumulated_text: dict[str, str] = {}
        # Last PATCH time: session_name -> float
        self._last_patch: dict[str, float] = {}
        # Persistent HTTP client (lazy-initialized)
        self._client: httpx.AsyncClient | None = None
        # Permission cache: username -> (allowed, expires_at)
        self._permission_cache: dict[str, tuple[bool, float]] = {}
        self._permission_cache_ttl = 300.0  # 5 minutes

    # ── Lifecycle ──────────────────────────────────────────────────────────

    async def start(self) -> None:
        """Start polling and/or webhook server."""
        self._running = True
        await self.hub.registry.subscribe(self.on_event)

        if self.config.mode in ("polling", "both"):
            self._poll_task = asyncio.create_task(self._poll_loop(), name="github-poll")
            logger.info(
                "GitHubAdapter polling started (interval=%ds, label=%s)",
                self.config.poll_interval_seconds,
                self.config.label_gate,
            )

        if self.config.mode in ("webhook", "both"):
            self._webhook_task = asyncio.create_task(
                self._start_webhook_server(), name="github-webhook"
            )
            logger.info(
                "GitHubAdapter webhook server starting on port %d",
                self.config.webhook_port,
            )

    async def stop(self) -> None:
        """Stop the adapter cleanly."""
        self._running = False
        await self.hub.registry.unsubscribe(self.on_event)

        if self._poll_task and not self._poll_task.done():
            self._poll_task.cancel()
        if self._webhook_task and not self._webhook_task.done():
            self._webhook_task.cancel()
        if self._webhook_runner is not None:
            try:
                await self._webhook_runner.cleanup()
            except Exception:
                pass

        # Close persistent HTTP client
        if self._client is not None:
            try:
                await self._client.aclose()
            except Exception:
                pass
            self._client = None

        self._cancel_all_debounce_tasks()

    # ── Event handler ──────────────────────────────────────────────────────

    async def on_event(self, event: SessionEvent) -> None:
        """Handle session events and stream output back to GitHub comments."""
        session_name = event.session_name
        # Only handle sessions we own
        entity_key = self._find_entity_key_by_session(session_name)
        if entity_key is None:
            return

        if event.event_type == "assistant_message":
            text = event.data.get("text", "")
            if text:
                self._output_chunk_buffers.setdefault(session_name, []).append(text)
                await self._schedule_debounced_patch(entity_key, session_name)

        elif event.event_type == "state_change":
            state = event.data.get("state", "")
            if state in ("idle", "completed", "stopped"):
                # Final flush
                await self._flush_output(entity_key, session_name, final=True)
                self._mapper.remove(entity_key)

    def _find_entity_key_by_session(self, session_name: str) -> str | None:
        """Reverse lookup: find the entity key for a session name."""
        for key in self._mapper.all_entity_keys():
            if self._mapper.get_session_name(key) == session_name:
                return key
        return None

    # ── Polling ────────────────────────────────────────────────────────────

    async def _poll_loop(self) -> None:
        """Main polling loop: runs every poll_interval_seconds."""
        while self._running:
            try:
                await self._poll_issues()
                await self._poll_pulls()
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Error in GitHub poll loop")
            await asyncio.sleep(self.config.poll_interval_seconds)

    async def _poll_issues(self) -> None:
        """Poll open issues with the label gate and start sessions for new ones."""
        if not self.config.owner or not self.config.repo:
            return
        url = (
            f"{_GITHUB_API}/repos/{self.config.owner}/{self.config.repo}/issues"
            f"?labels={self.config.label_gate}&state=open&per_page=50"
        )
        try:
            items = await self._gh_get_list(url)
        except Exception:
            logger.warning("Failed to poll GitHub issues", exc_info=True)
            return

        for item in items:
            # GitHub returns PRs in the issues endpoint; skip them here
            if item.get("pull_request"):
                continue
            await self._maybe_create_session(item, kind="issues")

    async def _poll_pulls(self) -> None:
        """Poll open pull requests with the label gate."""
        if not self.config.owner or not self.config.repo:
            return
        url = (
            f"{_GITHUB_API}/repos/{self.config.owner}/{self.config.repo}/pulls"
            f"?state=open&per_page=50"
        )
        try:
            items = await self._gh_get_list(url)
        except Exception:
            logger.warning("Failed to poll GitHub PRs", exc_info=True)
            return

        for item in items:
            item_labels = {lbl.get("name", "") for lbl in item.get("labels", [])}
            if self.config.label_gate not in item_labels:
                continue
            await self._maybe_create_session(item, kind="pulls")

    async def _maybe_create_session(self, item: dict[str, Any], kind: str) -> None:
        """Create a session for a labeled GitHub item if not already handled."""
        owner = self.config.owner or ""
        repo = self.config.repo or ""
        number = item.get("number")
        if number is None:
            return

        entity_key = _entity_key(owner, repo, kind, number)
        if self._mapper.is_handled(entity_key):
            return  # Already triggered

        # Permission check
        user = item.get("user", {})
        username = user.get("login", "")
        if username and not await self._check_permission(username):
            logger.info(
                "GitHub: skipping %s/%s#%d — user '%s' lacks write/admin permission",
                owner,
                repo,
                number,
                username,
            )
            return

        # Build prompt from issue/PR body
        title = item.get("title", "")
        body = item.get("body") or ""
        prompt = f"{title}\n\n{_strip_markdown(body, self.config.max_prompt_chars)}"

        session_name = _session_name(owner, repo, kind, number)
        cwd = str(Path.cwd())  # Default to current directory

        # Post "starting" comment
        comment_id = await self._post_comment(number, kind, "🤖 MPM session starting…")

        # Register mapping BEFORE creating session (prevents race)
        self._mapper.register(entity_key, session_name, comment_id)

        # Create session
        try:
            await self.hub.create_session(
                name=session_name,
                cwd=cwd,
                channel=self.channel_name,
                user_id=f"github:{username}",
                user_display=username,
            )
        except ValueError:
            # Session already exists (e.g. restarted daemon)
            logger.debug("Session '%s' already exists, skipping creation", session_name)
            return

        # Send the initial prompt to the session
        async def _noop_reply(_text: str) -> None:
            pass

        msg = ChannelMessage(
            text=prompt,
            session_name=session_name,
            channel=self.channel_name,
            user_id=f"github:{username}",
            user_display=username,
            reply_fn=_noop_reply,
        )
        await self.route_message(msg)
        logger.info(
            "GitHubAdapter: created session '%s' for %s/%s#%d",
            session_name,
            owner,
            repo,
            number,
        )

    # ── Webhook mode ───────────────────────────────────────────────────────

    async def _start_webhook_server(self) -> None:
        """Start an aiohttp webhook server on the configured port."""
        secret_env = self.config.webhook_secret_env
        secret = os.environ.get(secret_env, "")
        if not secret:
            logger.error(
                "GitHubAdapter: webhook mode requires %s to be set. "
                "Refusing to start webhook server without signature verification.",
                secret_env,
            )
            return

        try:
            from aiohttp import web

            app = web.Application()
            app.router.add_post("/webhook", self._handle_webhook)
            runner = web.AppRunner(app)
            self._webhook_runner = runner
            await runner.setup()
            site = web.TCPSite(runner, "0.0.0.0", self.config.webhook_port)  # nosec B104
            await site.start()
            logger.info(
                "GitHubAdapter webhook listening on port %d", self.config.webhook_port
            )
            # Keep running until stopped
            while self._running:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass
        except Exception:
            logger.exception("Failed to start GitHub webhook server")

    async def _handle_webhook(self, request: Any) -> Any:
        """Handle incoming GitHub webhook events."""
        from aiohttp import web

        body = await request.read()

        # Always verify signature (webhook server refuses to start without secret)
        secret = os.environ.get(self.config.webhook_secret_env, "")
        signature = request.headers.get("X-Hub-Signature-256", "")
        if not self._verify_signature(body, signature, secret):
            logger.warning("GitHub webhook signature verification failed")
            return web.Response(status=403, text="Forbidden")

        event_type = request.headers.get("X-GitHub-Event", "")
        try:
            import json as _json

            payload = _json.loads(body)
        except Exception:
            return web.Response(status=400, text="Bad JSON")

        await self._dispatch_webhook_event(event_type, payload)
        return web.Response(status=200, text="OK")

    @staticmethod
    def _verify_signature(body: bytes, signature: str, secret: str) -> bool:
        """Verify X-Hub-Signature-256 using HMAC-SHA256."""
        expected = (
            "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        )
        return hmac.compare_digest(expected, signature)

    async def _dispatch_webhook_event(
        self, event_type: str, payload: dict[str, Any]
    ) -> None:
        """Dispatch GitHub webhook events to appropriate handlers."""
        action = payload.get("action", "")
        if event_type == "issues" and action in ("opened", "labeled"):
            issue = payload.get("issue", {})
            labels = {lbl.get("name", "") for lbl in issue.get("labels", [])}
            if self.config.label_gate in labels:
                await self._maybe_create_session(issue, kind="issues")
        elif event_type == "pull_request" and action in ("opened", "labeled"):
            pr = payload.get("pull_request", {})
            labels = {lbl.get("name", "") for lbl in pr.get("labels", [])}
            if self.config.label_gate in labels:
                await self._maybe_create_session(pr, kind="pulls")
        elif event_type == "issue_comment" and action == "created":
            comment = payload.get("comment", {})
            body = comment.get("body", "")
            if "@mpm" in body:
                issue = payload.get("issue", {})
                await self._maybe_create_session(issue, kind="issues")

    # ── GitHub API helpers ─────────────────────────────────────────────────

    def _get_client(self) -> httpx.AsyncClient:
        """Return a persistent httpx async client, creating one lazily."""
        if self._client is None or self._client.is_closed:
            pat = os.environ.get(self.config.pat_env, "")
            self._client = httpx.AsyncClient(
                headers={
                    "Authorization": f"token {pat}",
                    "Accept": _ACCEPT_HEADER,
                    "X-GitHub-Api-Version": "2022-11-28",
                },
                timeout=30.0,
            )
        return self._client

    async def _gh_get_list(self, url: str) -> list[dict[str, Any]]:
        """Perform a GitHub GET request returning a JSON list with exponential backoff on 429."""
        backoff = 1.0
        for _ in range(5):
            client = self._get_client()
            resp = await client.get(url)
            if resp.status_code == 429:
                logger.warning("GitHub rate limit hit, waiting %.1fs", backoff)
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 60)
                continue
            resp.raise_for_status()
            data = resp.json()
            return data if isinstance(data, list) else []
        return []

    async def _gh_get(self, url: str) -> dict[str, Any]:
        """Perform a GitHub GET request returning a JSON object."""
        backoff = 1.0
        for _ in range(5):
            client = self._get_client()
            resp = await client.get(url)
            if resp.status_code == 429:
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 60)
                continue
            if resp.status_code == 404:
                return {}
            resp.raise_for_status()
            return resp.json()
        return {}

    # ── Comment management ─────────────────────────────────────────────────

    async def _post_comment(self, number: int, _kind: str, body: str) -> int | None:
        """POST a new comment on an issue/PR. Returns comment_id or None on failure."""
        owner = self.config.owner or ""
        repo = self.config.repo or ""
        # Both issues and PRs use the issues comments endpoint
        url = f"{_GITHUB_API}/repos/{owner}/{repo}/issues/{number}/comments"
        try:
            client = self._get_client()
            resp = await client.post(url, json={"body": body})
            if resp.status_code in (201, 200):
                data = resp.json()
                comment_id = data.get("id")
                logger.debug("Posted comment %s on #%d", comment_id, number)
                return int(comment_id) if comment_id else None
            logger.warning(
                "Failed to post GitHub comment on #%d: HTTP %d",
                number,
                resp.status_code,
            )
        except Exception:
            logger.warning(
                "Exception posting GitHub comment on #%d", number, exc_info=True
            )
        return None

    async def _update_comment(self, comment_id: int, body: str) -> bool:
        """PATCH an existing comment. Returns True on success."""
        owner = self.config.owner or ""
        repo = self.config.repo or ""
        url = f"{_GITHUB_API}/repos/{owner}/{repo}/issues/comments/{comment_id}"
        try:
            client = self._get_client()
            resp = await client.patch(url, json={"body": body})
            return resp.status_code == 200
        except Exception:
            logger.warning(
                "Exception updating GitHub comment %d", comment_id, exc_info=True
            )
            return False

    # ── Output streaming / debounce ────────────────────────────────────────

    async def _schedule_debounced_patch(
        self, entity_key: str, session_name: str
    ) -> None:
        """Schedule a debounced PATCH update. Max 1 patch per debounce_seconds per session."""
        debounce = self.config.comment_debounce_seconds
        existing = self._debounce_tasks.get(session_name)
        if existing and not existing.done():
            return  # Already scheduled

        async def _debounced() -> None:
            await asyncio.sleep(debounce)
            await self._flush_output(entity_key, session_name, final=False)

        task = asyncio.create_task(_debounced(), name=f"gh-debounce-{session_name}")
        self._debounce_tasks[session_name] = task

    async def _flush_output(
        self, entity_key: str, session_name: str, final: bool = False
    ) -> None:
        """Flush buffered output to the GitHub comment via PATCH.

        Accumulates all text across flushes so the PATCH always contains the
        full conversation output.  Only clears accumulated text on final flush.
        """
        comment_id = self._mapper.get_comment_id(entity_key)
        if comment_id is None:
            # No comment to update (initial POST failed); skip streaming
            return

        # Drain new chunks and append to accumulated text
        new_chunks = self._output_chunk_buffers.pop(session_name, [])
        if new_chunks:
            self._accumulated_text[session_name] = self._accumulated_text.get(
                session_name, ""
            ) + "".join(new_chunks)

        combined = self._accumulated_text.get(session_name, "")
        if not combined and not final:
            return

        if final:
            body = f"🤖 MPM session output:\n\n```\n{combined}\n```\n\n✅ Session complete."
        else:
            body = f"🤖 MPM session output (in progress):\n\n```\n{combined}\n```"

        success = await self._update_comment(comment_id, body)
        if success:
            self._last_patch[session_name] = time.time()

        # Only clear accumulated text when session is done
        if final:
            self._accumulated_text.pop(session_name, None)

        # Clean up debounce task reference
        self._debounce_tasks.pop(session_name, None)

    # ── Permission check ───────────────────────────────────────────────────

    async def _check_permission(self, username: str) -> bool:
        """Return True if the user has write or admin access to the configured repo.

        Results are cached for 5 minutes. Returns False on errors (fail-safe).
        """
        now = time.time()
        cached = self._permission_cache.get(username)
        if cached is not None:
            allowed, expires_at = cached
            if now < expires_at:
                return allowed

        owner = self.config.owner or ""
        repo = self.config.repo or ""
        url = f"{_GITHUB_API}/repos/{owner}/{repo}/collaborators/{username}/permission"
        try:
            data = await self._gh_get(url)
            if not data:
                # 404 means not a collaborator
                allowed = False
            else:
                permission = data.get("permission", "none")
                allowed = permission in ("admin", "write")
        except Exception:
            logger.warning(
                "Exception checking GitHub permission for '%s'", username, exc_info=True
            )
            allowed = False

        self._permission_cache[username] = (allowed, now + self._permission_cache_ttl)
        return allowed
