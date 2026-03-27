"""Comprehensive tests for the unified permission model (Issues #393-#396).

Tests cover:
- BotPermission / RateLimitConfig dataclass defaults and custom values
- PermissionManager: loading, matching, role checks, project patterns
- Rate limiting: sliding window, concurrent sessions
- GitRequirementsChecker: branch patterns, clean-state enforcement
- ChannelHub integration: permission denial raises PermissionError
"""

from __future__ import annotations

import subprocess
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from claude_mpm.services.channels.git_requirements import GitRequirementsChecker
from claude_mpm.services.channels.permissions import (
    BotPermission,
    GitRequirements,
    PermissionManager,
    RateLimitConfig,
)

# ── BotPermission dataclass ──────────────────────────────────────────────────


class TestBotPermission:
    def test_default_values(self) -> None:
        perm = BotPermission(platform="github", identity="octocat")
        assert perm.role == "user"
        assert perm.project_patterns == ["*"]
        assert perm.rate_limit is None
        assert perm.git is None

    def test_custom_values(self) -> None:
        rl = RateLimitConfig(max_sessions_per_hour=5, max_concurrent_sessions=1)
        git = GitRequirements(branch_pattern="main|dev", require_clean="block")
        perm = BotPermission(
            platform="telegram",
            identity="12345",
            role="admin",
            project_patterns=["~/projects/*"],
            rate_limit=rl,
            git=git,
        )
        assert perm.role == "admin"
        assert perm.rate_limit is not None
        assert perm.rate_limit.max_sessions_per_hour == 5
        assert perm.git is not None
        assert perm.git.require_clean == "block"


class TestRateLimitConfig:
    def test_default_values(self) -> None:
        rl = RateLimitConfig()
        assert rl.max_sessions_per_hour == 10
        assert rl.max_concurrent_sessions == 2

    def test_custom_values(self) -> None:
        rl = RateLimitConfig(max_sessions_per_hour=3, max_concurrent_sessions=1)
        assert rl.max_sessions_per_hour == 3
        assert rl.max_concurrent_sessions == 1


# ── PermissionManager ────────────────────────────────────────────────────────


class TestPermissionManager:
    def test_no_config_allows_all(self) -> None:
        """When no yaml files exist, everything is allowed."""
        mgr = PermissionManager()
        # Don't call load() — no files
        allowed, _reason = mgr.check("github", "anyone")
        assert allowed is True
        assert _reason == ""

    def test_load_global_config(self, tmp_path: Path) -> None:
        """Write a temp yaml and verify permissions loaded."""
        config_dir = tmp_path / ".claude-mpm"
        config_dir.mkdir()
        yaml_content = """\
version: "1.0"
permissions:
  - platform: github
    identity: "octocat"
    role: admin
    project_patterns: ["*"]
"""
        (config_dir / "bot-permissions.yaml").write_text(yaml_content)

        mgr = PermissionManager()
        # Patch Path.home to use tmp_path
        with patch.object(Path, "home", return_value=tmp_path):
            mgr.load()

        assert len(mgr._permissions) == 1
        assert mgr._permissions[0].identity == "octocat"
        assert mgr._permissions[0].role == "admin"

    def test_load_project_config_overrides_global(self, tmp_path: Path) -> None:
        """Project config overrides global for same identity."""
        # Global config
        global_dir = tmp_path / "home" / ".claude-mpm"
        global_dir.mkdir(parents=True)
        (global_dir / "bot-permissions.yaml").write_text(
            """\
permissions:
  - platform: github
    identity: "dev1"
    role: user
"""
        )

        # Project config — same identity, different role
        project_dir = tmp_path / "project" / ".claude-mpm"
        project_dir.mkdir(parents=True)
        (project_dir / "bot-permissions.yaml").write_text(
            """\
permissions:
  - platform: github
    identity: "dev1"
    role: admin
"""
        )

        mgr = PermissionManager()
        with patch.object(Path, "home", return_value=tmp_path / "home"):
            mgr.load(project_root=tmp_path / "project")

        # Should have project override (admin), not global (user)
        perm = mgr._find_permission("github", "dev1")
        assert perm is not None
        assert perm.role == "admin"

    def test_check_matching_permission(self) -> None:
        """Correct platform+identity returns True."""
        mgr = PermissionManager()
        mgr._permissions = [
            BotPermission(platform="github", identity="octocat", role="user"),
        ]
        allowed, _reason = mgr.check("github", "octocat")
        assert allowed is True
        assert _reason == ""

    def test_check_no_matching_permission_denies(self) -> None:
        """When permissions are configured, unknown identity is denied."""
        mgr = PermissionManager()
        mgr._permissions = [
            BotPermission(platform="github", identity="octocat", role="user"),
        ]
        allowed, _reason = mgr.check("github", "unknown_user")
        assert allowed is False
        assert "No permission entry" in _reason

    def test_check_readonly_role_blocks_run(self) -> None:
        """Readonly role returns (False, reason)."""
        mgr = PermissionManager()
        mgr._permissions = [
            BotPermission(platform="slack", identity="U999", role="readonly"),
        ]
        allowed, _reason = mgr.check("slack", "U999")
        assert allowed is False
        assert "readonly" in _reason

    def test_check_project_pattern_match(self) -> None:
        """project_patterns glob matching."""
        mgr = PermissionManager()
        mgr._permissions = [
            BotPermission(
                platform="github",
                identity="dev1",
                role="user",
                project_patterns=["/home/*/projects/*"],
            ),
        ]
        allowed, _reason = mgr.check(
            "github", "dev1", project_root="/home/user/projects/myapp"
        )
        assert allowed is True

    def test_check_project_pattern_no_match(self) -> None:
        """Non-matching project returns False."""
        mgr = PermissionManager()
        mgr._permissions = [
            BotPermission(
                platform="github",
                identity="dev1",
                role="user",
                project_patterns=["/allowed/*"],
            ),
        ]
        allowed, _reason = mgr.check(
            "github", "dev1", project_root="/forbidden/project"
        )
        assert allowed is False
        assert "does not match" in _reason

    def test_rate_limit_within_limit(self) -> None:
        """Under the limit returns True."""
        mgr = PermissionManager()
        mgr._permissions = [
            BotPermission(
                platform="github",
                identity="dev1",
                rate_limit=RateLimitConfig(
                    max_sessions_per_hour=5, max_concurrent_sessions=3
                ),
            ),
        ]
        allowed, _reason = mgr.check_rate_limit("github", "dev1")
        assert allowed is True

    def test_rate_limit_exceeded(self) -> None:
        """Over the hourly limit returns (False, reason)."""
        mgr = PermissionManager()
        mgr._permissions = [
            BotPermission(
                platform="github",
                identity="dev1",
                rate_limit=RateLimitConfig(
                    max_sessions_per_hour=2, max_concurrent_sessions=10
                ),
            ),
        ]
        # Record 2 session starts
        mgr.record_session_start("github", "dev1")
        mgr.record_session_start("github", "dev1")

        allowed, _reason = mgr.check_rate_limit("github", "dev1")
        assert allowed is False
        assert "Rate limit exceeded" in _reason

    def test_concurrent_sessions_limit(self) -> None:
        """Max concurrent returns (False, reason)."""
        mgr = PermissionManager()
        mgr._permissions = [
            BotPermission(
                platform="github",
                identity="dev1",
                rate_limit=RateLimitConfig(
                    max_sessions_per_hour=100, max_concurrent_sessions=1
                ),
            ),
        ]
        mgr.record_session_start("github", "dev1")

        allowed, _reason = mgr.check_rate_limit("github", "dev1")
        assert allowed is False
        assert "Concurrent session limit" in _reason

    def test_record_session_start_and_end(self) -> None:
        """Concurrent tracker increments and decrements."""
        mgr = PermissionManager()
        key = "github:dev1"
        assert mgr._concurrent_tracker.get(key, 0) == 0

        mgr.record_session_start("github", "dev1")
        assert mgr._concurrent_tracker[key] == 1

        mgr.record_session_start("github", "dev1")
        assert mgr._concurrent_tracker[key] == 2

        mgr.record_session_end("github", "dev1")
        assert mgr._concurrent_tracker[key] == 1

        mgr.record_session_end("github", "dev1")
        assert mgr._concurrent_tracker[key] == 0

        # Decrementing below 0 stays at 0
        mgr.record_session_end("github", "dev1")
        assert mgr._concurrent_tracker[key] == 0

    def test_sliding_window_expiry(self) -> None:
        """Old timestamps are cleaned up from the sliding window."""
        mgr = PermissionManager()
        mgr._permissions = [
            BotPermission(
                platform="github",
                identity="dev1",
                rate_limit=RateLimitConfig(
                    max_sessions_per_hour=2, max_concurrent_sessions=10
                ),
            ),
        ]
        key = "github:dev1"
        # Insert timestamps older than 1 hour
        old_time = time.time() - 3700  # more than 1 hour ago
        mgr._rate_tracker[key] = [old_time, old_time]

        # Should be allowed because old entries are pruned
        allowed, _reason = mgr.check_rate_limit("github", "dev1")
        assert allowed is True
        # Old entries should have been removed
        assert len(mgr._rate_tracker[key]) == 0

    def test_get_role_returns_default_for_unknown(self) -> None:
        """get_role returns user role for unknown identity."""
        mgr = PermissionManager()
        role = mgr.get_role("github", "unknown")
        assert role.can_run is True
        assert role.can_kill_others is False

    def test_load_with_custom_roles(self, tmp_path: Path) -> None:
        """Custom roles in YAML are loaded correctly."""
        config_dir = tmp_path / ".claude-mpm"
        config_dir.mkdir()
        yaml_content = """\
roles:
  deployer:
    can_run: true
    can_kill_others: true
    max_concurrent_sessions: 5
permissions:
  - platform: github
    identity: "ci-bot"
    role: deployer
"""
        (config_dir / "bot-permissions.yaml").write_text(yaml_content)

        mgr = PermissionManager()
        with patch.object(Path, "home", return_value=tmp_path):
            mgr.load()

        assert "deployer" in mgr._roles
        assert mgr._roles["deployer"].can_kill_others is True
        role = mgr.get_role("github", "ci-bot")
        assert role.max_concurrent_sessions == 5


# ── GitRequirementsChecker ───────────────────────────────────────────────────


class TestGitRequirementsChecker:
    @pytest.mark.asyncio
    async def test_not_a_git_repo_allows(self, tmp_path: Path) -> None:
        """No .git dir -> (True, "")."""
        checker = GitRequirementsChecker()
        allowed, _reason = await checker.check(str(tmp_path))
        assert allowed is True
        assert _reason == ""

    @pytest.mark.asyncio
    async def test_matching_branch_allows(self, tmp_path: Path) -> None:
        """Branch matches pattern -> (True, "")."""
        (tmp_path / ".git").mkdir()
        checker = GitRequirementsChecker()

        with patch.object(
            GitRequirementsChecker,
            "_get_current_branch",
            return_value="main",
        ):
            allowed, _reason = await checker.check(
                str(tmp_path), branch_pattern="main|develop"
            )
        assert allowed is True

    @pytest.mark.asyncio
    async def test_non_matching_branch_blocks(self, tmp_path: Path) -> None:
        """Branch doesn't match -> (False, reason)."""
        (tmp_path / ".git").mkdir()
        checker = GitRequirementsChecker()

        with patch.object(
            GitRequirementsChecker,
            "_get_current_branch",
            return_value="feature/wip",
        ):
            allowed, _reason = await checker.check(
                str(tmp_path), branch_pattern="^(main|develop)$"
            )
        assert allowed is False
        assert "does not match" in _reason

    @pytest.mark.asyncio
    async def test_require_clean_ignore(self, tmp_path: Path) -> None:
        """Dirty working tree + ignore -> (True, "")."""
        (tmp_path / ".git").mkdir()
        checker = GitRequirementsChecker()

        with (
            patch.object(
                GitRequirementsChecker, "_get_current_branch", return_value="main"
            ),
            patch.object(GitRequirementsChecker, "_is_clean", return_value=False),
        ):
            allowed, _reason = await checker.check(
                str(tmp_path), require_clean="ignore"
            )
        assert allowed is True

    @pytest.mark.asyncio
    async def test_require_clean_warn(self, tmp_path: Path) -> None:
        """Dirty + warn -> (True, "") but logs warning."""
        (tmp_path / ".git").mkdir()
        checker = GitRequirementsChecker()

        with (
            patch.object(
                GitRequirementsChecker, "_get_current_branch", return_value="main"
            ),
            patch.object(GitRequirementsChecker, "_is_clean", return_value=False),
            patch(
                "claude_mpm.services.channels.git_requirements.logger"
            ) as mock_logger,
        ):
            allowed, _reason = await checker.check(str(tmp_path), require_clean="warn")
        assert allowed is True
        mock_logger.warning.assert_called_once()

    @pytest.mark.asyncio
    async def test_require_clean_block(self, tmp_path: Path) -> None:
        """Dirty + block -> (False, "uncommitted changes")."""
        (tmp_path / ".git").mkdir()
        checker = GitRequirementsChecker()

        with (
            patch.object(
                GitRequirementsChecker, "_get_current_branch", return_value="main"
            ),
            patch.object(GitRequirementsChecker, "_is_clean", return_value=False),
        ):
            allowed, _reason = await checker.check(str(tmp_path), require_clean="block")
        assert allowed is False
        assert "uncommitted changes" in _reason

    @pytest.mark.asyncio
    async def test_clean_working_tree_allows(self, tmp_path: Path) -> None:
        """Clean + block -> (True, "")."""
        (tmp_path / ".git").mkdir()
        checker = GitRequirementsChecker()

        with (
            patch.object(
                GitRequirementsChecker, "_get_current_branch", return_value="main"
            ),
            patch.object(GitRequirementsChecker, "_is_clean", return_value=True),
        ):
            allowed, _reason = await checker.check(str(tmp_path), require_clean="block")
        assert allowed is True

    @pytest.mark.asyncio
    async def test_git_command_failure_fails_open(self, tmp_path: Path) -> None:
        """Subprocess error -> (True, "") — fail open."""
        (tmp_path / ".git").mkdir()
        checker = GitRequirementsChecker()

        with (
            patch.object(
                GitRequirementsChecker,
                "_get_current_branch",
                return_value=None,
            ),
            patch.object(
                GitRequirementsChecker,
                "_is_clean",
                return_value=True,
            ),
        ):
            allowed, _reason = await checker.check(
                str(tmp_path), branch_pattern="main", require_clean="block"
            )
        # Branch is None so re.match returns None which means branch
        # check is skipped (None branch = can't determine, fail open)
        assert allowed is True

    def test_get_current_branch_subprocess_failure(self, tmp_path: Path) -> None:
        """Subprocess error returns None."""
        with patch(
            "claude_mpm.services.channels.git_requirements.subprocess.run",
            side_effect=FileNotFoundError("git not found"),
        ):
            result = GitRequirementsChecker._get_current_branch(tmp_path)
        assert result is None

    def test_is_clean_subprocess_failure(self, tmp_path: Path) -> None:
        """Subprocess error returns True (fail-open)."""
        with patch(
            "claude_mpm.services.channels.git_requirements.subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="git", timeout=5),
        ):
            result = GitRequirementsChecker._is_clean(tmp_path)
        assert result is True


# ── ChannelHub integration ───────────────────────────────────────────────────


class TestChannelHubPermissionIntegration:
    @pytest.mark.asyncio
    async def test_permission_denied_raises(self) -> None:
        """PermissionError raised when check returns False."""
        from claude_mpm.services.channels.channel_hub import ChannelHub

        hub = ChannelHub(runner=MagicMock())

        with patch(
            "claude_mpm.services.channels.permissions.PermissionManager"
        ) as MockPM:
            instance = MockPM.return_value
            instance.load = MagicMock()
            instance.check.return_value = (False, "denied for testing")

            with pytest.raises(PermissionError, match="Permission denied"):
                await hub.create_session(
                    name="test-sess",
                    cwd="/tmp/test",
                    channel="github",
                    user_id="baduser",
                )

    @pytest.mark.asyncio
    async def test_rate_limit_denied_raises(self) -> None:
        """PermissionError raised on rate limit exceeded."""
        from claude_mpm.services.channels.channel_hub import ChannelHub

        hub = ChannelHub(runner=MagicMock())

        with patch(
            "claude_mpm.services.channels.permissions.PermissionManager"
        ) as MockPM:
            instance = MockPM.return_value
            instance.load = MagicMock()
            instance.check.return_value = (True, "")
            instance.check_rate_limit.return_value = (
                False,
                "Rate limit exceeded",
            )

            with pytest.raises(PermissionError, match="Rate limit"):
                await hub.create_session(
                    name="test-sess",
                    cwd="/tmp/test",
                    channel="github",
                    user_id="ratelimited",
                )

    @pytest.mark.asyncio
    async def test_git_requirements_denied_raises(self) -> None:
        """PermissionError on git check failure."""
        from claude_mpm.services.channels.channel_hub import ChannelHub

        hub = ChannelHub(runner=MagicMock())

        git_req = GitRequirements(branch_pattern="main", require_clean="block")
        perm = BotPermission(platform="github", identity="dev1", git=git_req)

        with (
            patch(
                "claude_mpm.services.channels.permissions.PermissionManager"
            ) as MockPM,
            patch(
                "claude_mpm.services.channels.git_requirements.GitRequirementsChecker"
            ) as MockGRC,
        ):
            pm_instance = MockPM.return_value
            pm_instance.load = MagicMock()
            pm_instance.check.return_value = (True, "")
            pm_instance.check_rate_limit.return_value = (True, "")
            pm_instance._find_permission.return_value = perm

            grc_instance = MockGRC.return_value
            grc_instance.check = AsyncMock(return_value=(False, "dirty working tree"))

            with pytest.raises(PermissionError, match="Git requirements"):
                await hub.create_session(
                    name="test-sess",
                    cwd="/tmp/test",
                    channel="github",
                    user_id="dev1",
                )

    @pytest.mark.asyncio
    async def test_no_config_allows_session_creation(self) -> None:
        """Without any config, session creation succeeds (no PermissionError)."""
        from claude_mpm.services.channels.channel_hub import ChannelHub

        hub = ChannelHub(runner=MagicMock())

        with patch(
            "claude_mpm.services.channels.permissions.PermissionManager"
        ) as MockPM:
            pm_instance = MockPM.return_value
            pm_instance.load = MagicMock()
            # No permissions loaded -> allow all
            pm_instance.check.return_value = (True, "")
            pm_instance.check_rate_limit.return_value = (True, "")
            pm_instance._find_permission.return_value = None
            pm_instance.record_session_start = MagicMock()

            # Mock registry.create to avoid real session creation
            hub.registry.create = AsyncMock(
                return_value=MagicMock(
                    session_id="sess-1",
                    name="test-sess",
                    cwd="/tmp/test",
                    state=MagicMock(value="idle"),
                    created_at=0.0,
                    github_context=None,
                )
            )

            # Mock the rest of the session setup
            with (
                patch.object(hub, "_write_hub_state"),
                patch(
                    "claude_mpm.services.channels.channel_hub.probe_vector_search",
                    new_callable=AsyncMock,
                    return_value=False,
                ),
                patch(
                    "claude_mpm.services.channels.channel_hub.SessionWorker"
                ) as MockWorker,
            ):
                worker_instance = MockWorker.return_value
                worker_instance.start = AsyncMock()

                session = await hub.create_session(
                    name="test-sess",
                    cwd="/tmp/test",
                    channel="github",
                    user_id="anyuser",
                )
                assert session is not None
