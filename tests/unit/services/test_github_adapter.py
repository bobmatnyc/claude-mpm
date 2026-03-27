"""Unit tests for GitHub channel adapter (Issue #385).

Coverage targets:
- GitHubSessionMapper: register, get, remove, persist/load round-trip, is_handled
- GitHubChannelConfig: default values, env var overrides
- GitHubAdapter._check_permission: mock httpx, write=True, read=False, 404=False, cache hit
- GitHubAdapter._poll_issues: labeled=session, non-labeled=skip, already-handled=skip
- GitHubAdapter._post_comment: mock httpx POST, verify comment_id captured
- GitHubAdapter._update_comment: mock httpx PATCH
- Webhook signature verification: valid HMAC passes, invalid fails
- GitHubAdapter start/stop lifecycle: polling task created, tasks cancelled on stop
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import os
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from claude_mpm.services.channels.channel_config import (
    GitHubChannelConfig,  # type: ignore[import-not-found]
)
from claude_mpm.services.channels.github_adapter import (  # type: ignore[import-not-found]
    GitHubAdapter,
    _entity_key,
    _session_name,
    _strip_markdown,
)
from claude_mpm.services.channels.github_session_mapper import (  # type: ignore[import-not-found]
    GitHubSessionMapper,
)

# ============================================================================
# HELPERS
# ============================================================================


def _make_config(**kwargs: object) -> GitHubChannelConfig:
    """Build a GitHubChannelConfig with sensible test defaults."""
    defaults: dict[str, object] = {
        "enabled": True,
        "owner": "testowner",
        "repo": "testrepo",
        "label_gate": "mpm:run",
        "mode": "polling",
        "poll_interval_seconds": 30,
        "pat_env": "GITHUB_TOKEN",
        "output_mode": "streaming",
        "comment_debounce_seconds": 5.0,
        "max_prompt_chars": 2000,
    }
    defaults.update(kwargs)
    return GitHubChannelConfig(**defaults)  # type: ignore[arg-type]


def _make_hub_mock() -> MagicMock:
    """Return a mock ChannelHub with the minimum interface needed."""
    hub = MagicMock()
    hub.registry = MagicMock()
    hub.registry.subscribe = AsyncMock()
    hub.registry.unsubscribe = AsyncMock()
    hub.create_session = AsyncMock()
    hub.route_message = AsyncMock()
    return hub


# ============================================================================
# _entity_key / _session_name helpers
# ============================================================================


class TestHelperFunctions:
    def test_entity_key_issue(self) -> None:
        assert _entity_key("owner", "repo", "issues", 42) == "owner/repo/issues/42"

    def test_entity_key_pull(self) -> None:
        assert _entity_key("owner", "repo", "pulls", 7) == "owner/repo/pulls/7"

    def test_session_name_issue(self) -> None:
        assert (
            _session_name("owner", "repo", "issues", 42) == "github-owner-repo-issue-42"
        )

    def test_session_name_pull(self) -> None:
        assert _session_name("owner", "repo", "pulls", 7) == "github-owner-repo-pr-7"

    def test_strip_markdown_removes_code_fence(self) -> None:
        text = "Hello ```python\ncode\n``` World"
        result = _strip_markdown(text)
        assert "```" not in result
        assert "Hello" in result

    def test_strip_markdown_truncates(self) -> None:
        text = "x" * 3000
        result = _strip_markdown(text, max_chars=100)
        assert len(result) <= 100


# ============================================================================
# GitHubSessionMapper
# ============================================================================


class TestGitHubSessionMapper:
    @pytest.fixture()
    def tmp_mapper(self, tmp_path: Path) -> GitHubSessionMapper:
        """Mapper backed by a temp file."""
        return GitHubSessionMapper(persist_path=tmp_path / "sessions.json")

    def test_register_and_get_session_name(
        self, tmp_mapper: GitHubSessionMapper
    ) -> None:
        tmp_mapper.register("owner/repo/issues/1", "session-1")
        assert tmp_mapper.get_session_name("owner/repo/issues/1") == "session-1"

    def test_register_with_comment_id(self, tmp_mapper: GitHubSessionMapper) -> None:
        tmp_mapper.register("owner/repo/issues/2", "session-2", comment_id=999)
        assert tmp_mapper.get_comment_id("owner/repo/issues/2") == 999

    def test_is_handled_true_after_register(
        self, tmp_mapper: GitHubSessionMapper
    ) -> None:
        tmp_mapper.register("owner/repo/issues/3", "session-3")
        assert tmp_mapper.is_handled("owner/repo/issues/3") is True

    def test_is_handled_false_for_unknown(
        self, tmp_mapper: GitHubSessionMapper
    ) -> None:
        assert tmp_mapper.is_handled("owner/repo/issues/999") is False

    def test_remove(self, tmp_mapper: GitHubSessionMapper) -> None:
        tmp_mapper.register("owner/repo/issues/4", "session-4", comment_id=42)
        tmp_mapper.remove("owner/repo/issues/4")
        assert tmp_mapper.is_handled("owner/repo/issues/4") is False
        assert tmp_mapper.get_comment_id("owner/repo/issues/4") is None

    def test_update_comment_id(self, tmp_mapper: GitHubSessionMapper) -> None:
        tmp_mapper.register("owner/repo/issues/5", "session-5", comment_id=1)
        tmp_mapper.update_comment_id("owner/repo/issues/5", 2)
        assert tmp_mapper.get_comment_id("owner/repo/issues/5") == 2

    def test_update_comment_id_noop_for_unregistered(
        self, tmp_mapper: GitHubSessionMapper
    ) -> None:
        """update_comment_id on unknown key should not raise."""
        tmp_mapper.update_comment_id("owner/repo/issues/999", 42)
        assert tmp_mapper.get_comment_id("owner/repo/issues/999") is None

    def test_all_entity_keys(self, tmp_mapper: GitHubSessionMapper) -> None:
        tmp_mapper.register("k1", "s1")
        tmp_mapper.register("k2", "s2")
        keys = tmp_mapper.all_entity_keys()
        assert "k1" in keys
        assert "k2" in keys

    def test_persist_and_load_round_trip(self, tmp_path: Path) -> None:
        persist_path = tmp_path / "sessions.json"
        mapper1 = GitHubSessionMapper(persist_path=persist_path)
        mapper1.register("owner/repo/issues/10", "session-10", comment_id=100)

        # New mapper loads from same file
        mapper2 = GitHubSessionMapper(persist_path=persist_path)
        assert mapper2.get_session_name("owner/repo/issues/10") == "session-10"
        assert mapper2.get_comment_id("owner/repo/issues/10") == 100

    def test_load_missing_file_is_noop(self, tmp_path: Path) -> None:
        """Loading from a non-existent file should return empty state."""
        mapper = GitHubSessionMapper(persist_path=tmp_path / "nonexistent.json")
        assert mapper.all_entity_keys() == []

    def test_load_corrupt_file_is_noop(self, tmp_path: Path) -> None:
        """Loading from a corrupt JSON file should not raise."""
        corrupt = tmp_path / "corrupt.json"
        corrupt.write_text("NOT JSON")
        mapper = GitHubSessionMapper(persist_path=corrupt)
        assert mapper.all_entity_keys() == []


# ============================================================================
# GitHubChannelConfig defaults and env var overrides
# ============================================================================


class TestGitHubChannelConfig:
    def test_default_values(self) -> None:
        cfg = GitHubChannelConfig()
        assert cfg.enabled is False
        assert cfg.pat_env == "GITHUB_TOKEN"
        assert cfg.label_gate == "mpm:run"
        assert cfg.mode == "polling"
        assert cfg.poll_interval_seconds == 30
        assert cfg.webhook_port == 9876
        assert cfg.output_mode == "streaming"
        assert cfg.comment_debounce_seconds == 5.0
        assert cfg.max_prompt_chars == 2000
        assert cfg.owner is None
        assert cfg.repo is None

    def test_env_var_overrides(self) -> None:
        from claude_mpm.services.channels.channel_config import (  # type: ignore[import-not-found]
            _parse_github_config_from_env,
        )

        cfg = GitHubChannelConfig()
        env_vars = {
            "CLAUDE_MPM_GITHUB_OWNER": "newowner",
            "CLAUDE_MPM_GITHUB_REPO": "newrepo",
            "CLAUDE_MPM_GITHUB_LABEL": "mpm:custom",
            "CLAUDE_MPM_GITHUB_MODE": "webhook",
            "CLAUDE_MPM_GITHUB_POLL_INTERVAL": "60",
        }
        with patch.dict(os.environ, env_vars, clear=False):
            result = _parse_github_config_from_env(cfg)
        assert result.owner == "newowner"
        assert result.repo == "newrepo"
        assert result.label_gate == "mpm:custom"
        assert result.mode == "webhook"
        assert result.poll_interval_seconds == 60

    def test_env_var_invalid_poll_interval_ignored(self) -> None:
        from claude_mpm.services.channels.channel_config import (  # type: ignore[import-not-found]
            _parse_github_config_from_env,
        )

        cfg = GitHubChannelConfig()
        with patch.dict(
            os.environ, {"CLAUDE_MPM_GITHUB_POLL_INTERVAL": "abc"}, clear=False
        ):
            result = _parse_github_config_from_env(cfg)
        # Invalid int → original default kept
        assert result.poll_interval_seconds == 30

    def test_allowed_user_types_defaults(self) -> None:
        cfg = GitHubChannelConfig()
        assert "member" in cfg.allowed_user_types
        assert "owner" in cfg.allowed_user_types
        assert "collaborator" in cfg.allowed_user_types


# ============================================================================
# GitHubAdapter._check_permission
# ============================================================================


class TestCheckPermission:
    def _adapter(self) -> GitHubAdapter:
        hub = _make_hub_mock()
        cfg = _make_config()
        adapter = GitHubAdapter(hub=hub, config=cfg)
        # Use an in-memory-only mapper path that doesn't exist (safe isolation)
        adapter._mapper = GitHubSessionMapper(
            persist_path=Path("/nonexistent/test-perm.json")
        )
        return adapter

    @pytest.mark.asyncio
    async def test_write_permission_returns_true(self) -> None:
        adapter = self._adapter()
        with patch.object(
            adapter,
            "_gh_get",
            AsyncMock(return_value={"permission": "write"}),
        ):
            result = await adapter._check_permission("alice")
        assert result is True

    @pytest.mark.asyncio
    async def test_admin_permission_returns_true(self) -> None:
        adapter = self._adapter()
        with patch.object(
            adapter,
            "_gh_get",
            AsyncMock(return_value={"permission": "admin"}),
        ):
            result = await adapter._check_permission("alice")
        assert result is True

    @pytest.mark.asyncio
    async def test_read_permission_returns_false(self) -> None:
        adapter = self._adapter()
        with patch.object(
            adapter,
            "_gh_get",
            AsyncMock(return_value={"permission": "read"}),
        ):
            result = await adapter._check_permission("bob")
        assert result is False

    @pytest.mark.asyncio
    async def test_404_returns_false(self) -> None:
        """Empty dict from _gh_get (404) → not a collaborator → False."""
        adapter = self._adapter()
        with patch.object(adapter, "_gh_get", AsyncMock(return_value={})):
            result = await adapter._check_permission("outsider")
        assert result is False

    @pytest.mark.asyncio
    async def test_exception_returns_false(self) -> None:
        """Any exception during API call → fail-safe False."""
        adapter = self._adapter()
        with patch.object(
            adapter, "_gh_get", AsyncMock(side_effect=RuntimeError("network"))
        ):
            result = await adapter._check_permission("error_user")
        assert result is False

    @pytest.mark.asyncio
    async def test_cache_hit_avoids_second_api_call(self) -> None:
        """Second call for same username within TTL uses cache."""
        adapter = self._adapter()
        mock_get = AsyncMock(return_value={"permission": "write"})
        with patch.object(adapter, "_gh_get", mock_get):
            first = await adapter._check_permission("cached_user")
            second = await adapter._check_permission("cached_user")
        assert first is True
        assert second is True
        mock_get.assert_awaited_once()  # Only called once

    @pytest.mark.asyncio
    async def test_expired_cache_triggers_new_api_call(self) -> None:
        """Expired cache entry triggers a fresh API call."""
        adapter = self._adapter()
        # Manually insert an expired cache entry
        adapter._permission_cache["stale_user"] = (True, time.time() - 1.0)
        mock_get = AsyncMock(return_value={"permission": "read"})
        with patch.object(adapter, "_gh_get", mock_get):
            result = await adapter._check_permission("stale_user")
        assert result is False  # New call returned read → False
        mock_get.assert_awaited_once()


# ============================================================================
# GitHubAdapter._poll_issues
# ============================================================================


class TestPollIssues:
    def _adapter(self, tmp_path: Path | None = None) -> GitHubAdapter:
        hub = _make_hub_mock()
        cfg = _make_config()
        adapter = GitHubAdapter(hub=hub, config=cfg)
        # Always use an isolated mapper to avoid loading persisted real state
        adapter._mapper = GitHubSessionMapper(
            persist_path=(tmp_path or Path("/tmp")) / "gh-test-sessions.json"
        )
        return adapter

    def _issue_fixture(
        self, number: int, labels: list[str], has_pr: bool = False
    ) -> dict:
        item: dict = {
            "number": number,
            "title": f"Issue #{number}",
            "body": "Issue body text",
            "user": {"login": "alice"},
            "labels": [{"name": lbl} for lbl in labels],
        }
        if has_pr:
            item["pull_request"] = {"url": "https://example.com/pr"}
        return item

    @pytest.mark.asyncio
    async def test_labeled_issue_creates_session(self, tmp_path: Path) -> None:
        adapter = self._adapter(tmp_path)
        issues = [self._issue_fixture(1, ["mpm:run"])]
        with (
            patch.object(adapter, "_gh_get_list", AsyncMock(return_value=issues)),
            patch.object(adapter, "_check_permission", AsyncMock(return_value=True)),
            patch.object(adapter, "_post_comment", AsyncMock(return_value=101)),
            patch.object(adapter, "route_message", AsyncMock()),
        ):
            await adapter._poll_issues()

        adapter.hub.create_session.assert_awaited_once()
        call_kwargs = adapter.hub.create_session.call_args
        assert call_kwargs.kwargs["name"] == "github-testowner-testrepo-issue-1"

    @pytest.mark.asyncio
    async def test_non_labeled_issue_skipped(self, tmp_path: Path) -> None:
        """Issues without the label gate should not create sessions."""
        adapter = self._adapter(tmp_path)
        # Note: the label filter happens at the API level via ?labels= param,
        # so any item returned from _gh_get_list is assumed to have the label.
        # But PRs returned via issues endpoint should be skipped.
        pr_item = self._issue_fixture(2, ["mpm:run"], has_pr=True)
        with (
            patch.object(adapter, "_gh_get_list", AsyncMock(return_value=[pr_item])),
            patch.object(adapter, "_maybe_create_session", AsyncMock()) as mock_create,
        ):
            await adapter._poll_issues()
        mock_create.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_already_handled_issue_skipped(self, tmp_path: Path) -> None:
        adapter = self._adapter(tmp_path)
        issues = [self._issue_fixture(3, ["mpm:run"])]
        entity_key = _entity_key("testowner", "testrepo", "issues", 3)
        adapter._mapper.register(entity_key, "existing-session")

        with (
            patch.object(adapter, "_gh_get_list", AsyncMock(return_value=issues)),
            patch.object(adapter, "_check_permission", AsyncMock(return_value=True)),
        ):
            await adapter._poll_issues()

        adapter.hub.create_session.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_no_owner_configured_skips_poll(self, tmp_path: Path) -> None:
        hub = _make_hub_mock()
        cfg = _make_config(owner=None)
        adapter = GitHubAdapter(hub=hub, config=cfg)
        adapter._mapper = GitHubSessionMapper(persist_path=tmp_path / "sessions.json")
        mock_get = AsyncMock()
        with patch.object(adapter, "_gh_get_list", mock_get):
            await adapter._poll_issues()
        mock_get.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_poll_issues_api_error_logged_not_raised(
        self, tmp_path: Path
    ) -> None:
        adapter = self._adapter(tmp_path)
        with patch.object(
            adapter,
            "_gh_get_list",
            AsyncMock(side_effect=RuntimeError("network error")),
        ):
            # Should not raise
            await adapter._poll_issues()


# ============================================================================
# GitHubAdapter._poll_pulls
# ============================================================================


class TestPollPulls:
    def _adapter(self, tmp_path: Path | None = None) -> GitHubAdapter:
        hub = _make_hub_mock()
        cfg = _make_config()
        adapter = GitHubAdapter(hub=hub, config=cfg)
        adapter._mapper = GitHubSessionMapper(
            persist_path=(tmp_path or Path("/tmp")) / "gh-pull-sessions.json"
        )
        return adapter

    def _pr_fixture(self, number: int, labels: list[str]) -> dict:
        return {
            "number": number,
            "title": f"PR #{number}",
            "body": "PR body",
            "user": {"login": "bob"},
            "labels": [{"name": lbl} for lbl in labels],
        }

    @pytest.mark.asyncio
    async def test_labeled_pr_creates_session(self, tmp_path: Path) -> None:
        adapter = self._adapter(tmp_path)
        prs = [self._pr_fixture(10, ["mpm:run"])]
        with (
            patch.object(adapter, "_gh_get_list", AsyncMock(return_value=prs)),
            patch.object(adapter, "_check_permission", AsyncMock(return_value=True)),
            patch.object(adapter, "_post_comment", AsyncMock(return_value=200)),
            patch.object(adapter, "route_message", AsyncMock()),
        ):
            await adapter._poll_pulls()

        adapter.hub.create_session.assert_awaited_once()
        assert (
            adapter.hub.create_session.call_args.kwargs["name"]
            == "github-testowner-testrepo-pr-10"
        )

    @pytest.mark.asyncio
    async def test_unlabeled_pr_skipped(self, tmp_path: Path) -> None:
        adapter = self._adapter(tmp_path)
        prs = [self._pr_fixture(11, ["other-label"])]
        with (
            patch.object(adapter, "_gh_get_list", AsyncMock(return_value=prs)),
        ):
            await adapter._poll_pulls()
        adapter.hub.create_session.assert_not_awaited()


# ============================================================================
# GitHubAdapter._post_comment
# ============================================================================


class TestPostComment:
    def _adapter(self) -> GitHubAdapter:
        hub = _make_hub_mock()
        cfg = _make_config()
        adapter = GitHubAdapter(hub=hub, config=cfg)
        adapter._mapper = GitHubSessionMapper(
            persist_path=Path("/nonexistent/test-post.json")
        )
        return adapter

    @pytest.mark.asyncio
    async def test_post_comment_returns_comment_id(self) -> None:
        adapter = self._adapter()
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": 12345}

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch.object(adapter, "_make_client", return_value=mock_client):
            result = await adapter._post_comment(42, "issues", "Hello from MPM")

        assert result == 12345
        mock_client.post.assert_awaited_once()
        call_args = mock_client.post.call_args
        assert call_args.kwargs["json"]["body"] == "Hello from MPM"

    @pytest.mark.asyncio
    async def test_post_comment_http_error_returns_none(self) -> None:
        adapter = self._adapter()
        mock_response = MagicMock()
        mock_response.status_code = 422

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch.object(adapter, "_make_client", return_value=mock_client):
            result = await adapter._post_comment(42, "issues", "body")

        assert result is None

    @pytest.mark.asyncio
    async def test_post_comment_exception_returns_none(self) -> None:
        adapter = self._adapter()
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(side_effect=RuntimeError("network"))

        with patch.object(adapter, "_make_client", return_value=mock_client):
            result = await adapter._post_comment(42, "issues", "body")

        assert result is None


# ============================================================================
# GitHubAdapter._update_comment
# ============================================================================


class TestUpdateComment:
    def _adapter(self) -> GitHubAdapter:
        hub = _make_hub_mock()
        cfg = _make_config()
        adapter = GitHubAdapter(hub=hub, config=cfg)
        adapter._mapper = GitHubSessionMapper(
            persist_path=Path("/nonexistent/test-update.json")
        )
        return adapter

    @pytest.mark.asyncio
    async def test_update_comment_success(self) -> None:
        adapter = self._adapter()
        mock_response = MagicMock()
        mock_response.status_code = 200

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.patch = AsyncMock(return_value=mock_response)

        with patch.object(adapter, "_make_client", return_value=mock_client):
            result = await adapter._update_comment(999, "Updated body")

        assert result is True
        mock_client.patch.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_update_comment_non_200_returns_false(self) -> None:
        adapter = self._adapter()
        mock_response = MagicMock()
        mock_response.status_code = 404

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.patch = AsyncMock(return_value=mock_response)

        with patch.object(adapter, "_make_client", return_value=mock_client):
            result = await adapter._update_comment(999, "body")

        assert result is False

    @pytest.mark.asyncio
    async def test_update_comment_exception_returns_false(self) -> None:
        adapter = self._adapter()
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.patch = AsyncMock(side_effect=RuntimeError("timeout"))

        with patch.object(adapter, "_make_client", return_value=mock_client):
            result = await adapter._update_comment(999, "body")

        assert result is False


# ============================================================================
# Webhook signature verification
# ============================================================================


class TestVerifySignature:
    def test_valid_signature_passes(self) -> None:
        secret = "mysecret"  # pragma: allowlist secret
        body = b'{"action": "opened"}'
        expected_hex = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        signature = f"sha256={expected_hex}"

        result = GitHubAdapter._verify_signature(body, signature, secret)
        assert result is True

    def test_invalid_signature_fails(self) -> None:
        body = b'{"action": "opened"}'
        result = GitHubAdapter._verify_signature(body, "sha256=deadbeef", "mysecret")
        assert result is False

    def test_empty_signature_fails(self) -> None:
        body = b'{"action": "opened"}'
        result = GitHubAdapter._verify_signature(body, "", "mysecret")
        assert result is False

    def test_tampered_body_fails(self) -> None:
        secret = "mysecret"  # pragma: allowlist secret
        original_body = b'{"action": "opened"}'
        hex_sig = hmac.new(secret.encode(), original_body, hashlib.sha256).hexdigest()
        signature = f"sha256={hex_sig}"

        tampered_body = b'{"action": "closed"}'
        result = GitHubAdapter._verify_signature(tampered_body, signature, secret)
        assert result is False


# ============================================================================
# GitHubAdapter start/stop lifecycle
# ============================================================================


class TestGitHubAdapterLifecycle:
    def _adapter(self, mode: str = "polling") -> GitHubAdapter:
        hub = _make_hub_mock()
        cfg = _make_config(mode=mode)
        adapter = GitHubAdapter(hub=hub, config=cfg)
        adapter._mapper = GitHubSessionMapper(
            persist_path=Path("/nonexistent/test-lifecycle.json")
        )
        return adapter

    @pytest.mark.asyncio
    async def test_start_polling_creates_poll_task(self) -> None:
        adapter = self._adapter(mode="polling")
        try:
            await adapter.start()
            assert adapter._poll_task is not None
            assert not adapter._poll_task.done()
            assert adapter._webhook_task is None
        finally:
            await adapter.stop()

    @pytest.mark.asyncio
    async def test_start_webhook_creates_webhook_task(self) -> None:
        adapter = self._adapter(mode="webhook")
        try:
            await adapter.start()
            assert adapter._webhook_task is not None
            assert adapter._poll_task is None
        finally:
            await adapter.stop()

    @pytest.mark.asyncio
    async def test_start_both_creates_both_tasks(self) -> None:
        adapter = self._adapter(mode="both")
        try:
            await adapter.start()
            assert adapter._poll_task is not None
            assert adapter._webhook_task is not None
        finally:
            await adapter.stop()

    @pytest.mark.asyncio
    async def test_stop_cancels_poll_task(self) -> None:
        adapter = self._adapter(mode="polling")
        await adapter.start()
        poll_task = adapter._poll_task
        await adapter.stop()
        # Give the event loop a turn so CancelledError propagates
        await asyncio.sleep(0)

        assert poll_task is not None
        assert poll_task.cancelled() or poll_task.done()

    @pytest.mark.asyncio
    async def test_stop_unsubscribes_from_registry(self) -> None:
        adapter = self._adapter()
        await adapter.start()
        await adapter.stop()
        adapter.hub.registry.unsubscribe.assert_awaited_once_with(adapter.on_event)

    @pytest.mark.asyncio
    async def test_start_subscribes_to_registry(self) -> None:
        adapter = self._adapter()
        try:
            await adapter.start()
            adapter.hub.registry.subscribe.assert_awaited_once_with(adapter.on_event)
        finally:
            await adapter.stop()

    @pytest.mark.asyncio
    async def test_stop_clears_debounce_tasks(self) -> None:
        adapter = self._adapter()
        # Inject a fake pending debounce task
        fake_task = asyncio.create_task(asyncio.sleep(100))
        adapter._debounce_tasks["session-x"] = fake_task
        await adapter.start()
        await adapter.stop()
        # Give the event loop a turn so CancelledError propagates
        await asyncio.sleep(0)
        assert len(adapter._debounce_tasks) == 0
        assert fake_task.cancelled()


# ============================================================================
# GitHubAdapter._dispatch_webhook_event
# ============================================================================


class TestDispatchWebhookEvent:
    def _adapter(self) -> GitHubAdapter:
        hub = _make_hub_mock()
        cfg = _make_config()
        adapter = GitHubAdapter(hub=hub, config=cfg)
        adapter._mapper = GitHubSessionMapper(
            persist_path=Path("/nonexistent/test-webhook.json")
        )
        return adapter

    @pytest.mark.asyncio
    async def test_issues_opened_with_label_dispatches(self) -> None:
        adapter = self._adapter()
        payload = {
            "action": "opened",
            "issue": {
                "number": 5,
                "title": "Test",
                "body": "body",
                "user": {"login": "alice"},
                "labels": [{"name": "mpm:run"}],
            },
        }
        with patch.object(adapter, "_maybe_create_session", AsyncMock()) as mock_create:
            await adapter._dispatch_webhook_event("issues", payload)
        mock_create.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_issues_opened_without_label_skipped(self) -> None:
        adapter = self._adapter()
        payload = {
            "action": "opened",
            "issue": {
                "number": 6,
                "title": "No label",
                "body": "body",
                "user": {"login": "alice"},
                "labels": [],
            },
        }
        with patch.object(adapter, "_maybe_create_session", AsyncMock()) as mock_create:
            await adapter._dispatch_webhook_event("issues", payload)
        mock_create.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_pull_request_labeled_dispatches(self) -> None:
        adapter = self._adapter()
        payload = {
            "action": "labeled",
            "pull_request": {
                "number": 7,
                "title": "PR",
                "body": "body",
                "user": {"login": "bob"},
                "labels": [{"name": "mpm:run"}],
            },
        }
        with patch.object(adapter, "_maybe_create_session", AsyncMock()) as mock_create:
            await adapter._dispatch_webhook_event("pull_request", payload)
        mock_create.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_issue_comment_with_at_mpm_dispatches(self) -> None:
        adapter = self._adapter()
        payload = {
            "action": "created",
            "comment": {"body": "Hey @mpm please review this"},
            "issue": {
                "number": 8,
                "title": "Issue",
                "body": "body",
                "user": {"login": "carol"},
                "labels": [],
            },
        }
        with patch.object(adapter, "_maybe_create_session", AsyncMock()) as mock_create:
            await adapter._dispatch_webhook_event("issue_comment", payload)
        mock_create.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_issue_comment_without_at_mpm_skipped(self) -> None:
        adapter = self._adapter()
        payload = {
            "action": "created",
            "comment": {"body": "Just a regular comment"},
            "issue": {
                "number": 9,
                "title": "Issue",
                "body": "",
                "user": {"login": "dave"},
                "labels": [],
            },
        }
        with patch.object(adapter, "_maybe_create_session", AsyncMock()) as mock_create:
            await adapter._dispatch_webhook_event("issue_comment", payload)
        mock_create.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_unknown_event_type_ignored(self) -> None:
        adapter = self._adapter()
        with patch.object(adapter, "_maybe_create_session", AsyncMock()) as mock_create:
            await adapter._dispatch_webhook_event("push", {"action": "created"})
        mock_create.assert_not_awaited()


# ============================================================================
# GitHubAdapter._find_entity_key_by_session
# ============================================================================


class TestFindEntityKeyBySession:
    def _adapter(self) -> GitHubAdapter:
        hub = _make_hub_mock()
        cfg = _make_config()
        adapter = GitHubAdapter(hub=hub, config=cfg)
        adapter._mapper = GitHubSessionMapper(
            persist_path=Path("/nonexistent/test-find.json")
        )
        return adapter

    def test_returns_entity_key_for_known_session(self) -> None:
        adapter = self._adapter()
        adapter._mapper.register("owner/repo/issues/1", "session-abc")
        result = adapter._find_entity_key_by_session("session-abc")
        assert result == "owner/repo/issues/1"

    def test_returns_none_for_unknown_session(self) -> None:
        adapter = self._adapter()
        result = adapter._find_entity_key_by_session("unknown-session")
        assert result is None


# ============================================================================
# ChannelHub wiring (Issue #383)
# ============================================================================


class TestChannelHubGitHubWiring:
    @pytest.mark.asyncio
    async def test_github_adapter_started_when_enabled(self) -> None:
        """When config.github.enabled=True, hub.start() should start a GitHubAdapter."""
        from claude_mpm.services.channels.channel_config import (  # type: ignore[import-not-found]
            ChannelsConfig,
        )
        from claude_mpm.services.channels.channel_hub import (  # type: ignore[import-not-found]
            ChannelHub,
        )

        cfg = ChannelsConfig()
        cfg.github.enabled = True
        cfg.github.owner = "owner"
        cfg.github.repo = "repo"
        cfg.github.mode = "polling"

        runner = MagicMock()
        hub = ChannelHub(runner=runner, config=cfg)

        # Stub out TerminalAdapter and GitHubAdapter so no real I/O happens
        with (
            patch(
                "claude_mpm.services.channels.channel_hub.TerminalAdapter"
            ) as MockTerminal,
            patch(
                "claude_mpm.services.channels.github_adapter.GitHubAdapter"
            ) as MockGitHub,
        ):
            mock_terminal_instance = AsyncMock()
            mock_terminal_instance.channel_name = "terminal"
            MockTerminal.return_value = mock_terminal_instance

            mock_github_instance = AsyncMock()
            mock_github_instance.channel_name = "github"
            MockGitHub.return_value = mock_github_instance

            await hub.start()

        mock_github_instance.start.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_github_adapter_not_started_when_disabled(self) -> None:
        """When config.github.enabled=False, hub.start() should NOT start GitHubAdapter."""
        from claude_mpm.services.channels.channel_config import (  # type: ignore[import-not-found]
            ChannelsConfig,
        )
        from claude_mpm.services.channels.channel_hub import (  # type: ignore[import-not-found]
            ChannelHub,
        )

        cfg = ChannelsConfig()
        cfg.github.enabled = False

        runner = MagicMock()
        hub = ChannelHub(runner=runner, config=cfg)

        with (
            patch(
                "claude_mpm.services.channels.channel_hub.TerminalAdapter"
            ) as MockTerminal,
            patch(
                "claude_mpm.services.channels.channel_hub.GitHubAdapter",
                create=True,
            ) as MockGitHub,
        ):
            mock_terminal_instance = AsyncMock()
            mock_terminal_instance.channel_name = "terminal"
            MockTerminal.return_value = mock_terminal_instance

            await hub.start()

        MockGitHub.assert_not_called()
