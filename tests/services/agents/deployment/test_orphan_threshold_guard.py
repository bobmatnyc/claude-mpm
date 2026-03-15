"""Tests for the orphan detection threshold guard (Phase 2a / F11).

The threshold guard prevents mass deletion when an unusually high percentage
of deployed agents would be removed, which suggests a partial cache sync or
bug rather than actual orphans.

The guard triggers ONLY when BOTH conditions are true:
  1. orphan_ratio > 20% of total deployed agents
  2. more than 3 orphan candidates (absolute floor)

When the guard triggers, ALL deletions are skipped and an empty list is returned.
"""

import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from claude_mpm.services.agents.deployment.deployment_reconciler import DeploymentResult

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PROVENANCE_MODULE = "claude_mpm.utils.agent_provenance"
GET_PATH_MANAGER_TARGET = "claude_mpm.core.unified_paths.get_path_manager"

MPM_AGENT_CONTENT = """\
---
author: claude-mpm
description: Test agent managed by MPM
version: 1.0.0
---

# Test Agent

This agent is managed by claude-mpm.
"""

USER_AGENT_CONTENT = """\
---
author: my-custom-tool
description: User-created agent
---

# User Agent

This is a user-created agent, not managed by MPM.
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_config(
    *,
    enabled: list[str] | None = None,
    required: list[str] | None = None,
) -> MagicMock:
    """Create a minimal UnifiedConfig mock with agent sub-config."""
    config = MagicMock()
    config.agents.enabled = enabled if enabled is not None else []
    config.agents.required = required if required is not None else []
    return config


def _make_deployment_result() -> DeploymentResult:
    """Create an empty DeploymentResult."""
    return DeploymentResult(deployed=[], removed=[], unchanged=[], errors=[])


def _make_path_manager_mock(cache_agents_dir: Path) -> MagicMock:
    """Return a mock path_manager wired to *cache_agents_dir*."""
    pm = MagicMock()
    pm.get_cache_dir.return_value = cache_agents_dir.parent
    return pm


def _write_mpm_agent(path: Path, name: str) -> None:
    """Write a mock MPM-managed agent file with frontmatter."""
    path.write_text(
        f"---\nname: {name}\nauthor: claude-mpm\nversion: 1.0.0\n---\n"
        f"# {name}\n\nInstructions here."
    )


def _call_detect(
    tmp_path: Path,
    cache_dir: Path,
    config: MagicMock,
) -> list[str]:
    """Invoke _detect_and_remove_orphaned_agents with standard mocks."""

    def provenance_side_effect(content: str) -> bool:
        return "author: claude-mpm" in content

    with patch(GET_PATH_MANAGER_TARGET) as mock_gpm:
        mock_gpm.return_value = _make_path_manager_mock(cache_dir)
        with patch(
            f"{PROVENANCE_MODULE}.is_mpm_managed_agent",
            side_effect=provenance_side_effect,
        ):
            from claude_mpm.services.agents.deployment.startup_reconciliation import (
                _detect_and_remove_orphaned_agents,
            )

            return _detect_and_remove_orphaned_agents(
                tmp_path, config, _make_deployment_result()
            )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestOrphanThresholdGuard:
    """Tests for the threshold guard that prevents mass deletion."""

    # ------------------------------------------------------------------
    # test 1: threshold guard prevents mass deletion
    # 7 expected + 4 orphans = 11 total, 4/11 = 36% > 20%, 4 > 3
    # ------------------------------------------------------------------

    def test_threshold_guard_prevents_mass_deletion(self, tmp_path: Path) -> None:
        """When orphan ratio > 20% AND count > 3, all orphans are preserved."""
        deploy_dir = tmp_path / ".claude" / "agents"
        deploy_dir.mkdir(parents=True)
        cache_dir = tmp_path / "cache" / "agents"
        cache_dir.mkdir(parents=True)

        # 7 expected agents (in cache and deployed)
        for i in range(7):
            name = f"expected-agent-{i}"
            _write_mpm_agent(cache_dir / f"{name}.md", name)
            _write_mpm_agent(deploy_dir / f"{name}.md", name)

        # 4 orphaned agents (deployed but NOT in cache)
        orphan_files = []
        for i in range(4):
            name = f"orphan-agent-{i}"
            orphan_file = deploy_dir / f"{name}.md"
            _write_mpm_agent(orphan_file, name)
            orphan_files.append(orphan_file)

        config = _make_config()
        removed = _call_detect(tmp_path, cache_dir, config)

        # Guard should trigger: 4/11 = 36% > 20% AND 4 > 3
        assert removed == [], (
            "Threshold guard should prevent all deletions when ratio > 20% and count > 3"
        )
        for orphan_file in orphan_files:
            assert orphan_file.exists(), (
                f"Orphan {orphan_file.name} must be preserved when threshold guard triggers"
            )

    # ------------------------------------------------------------------
    # test 2: small deployment not blocked (absolute floor not met)
    # 4 expected + 1 orphan = 5 total, 1/5 = 20%, 1 <= 3
    # ------------------------------------------------------------------

    def test_small_deployment_not_blocked(self, tmp_path: Path) -> None:
        """When orphan count <= 3 (absolute floor), guard does NOT trigger."""
        deploy_dir = tmp_path / ".claude" / "agents"
        deploy_dir.mkdir(parents=True)
        cache_dir = tmp_path / "cache" / "agents"
        cache_dir.mkdir(parents=True)

        # 4 expected agents
        for i in range(4):
            name = f"expected-agent-{i}"
            _write_mpm_agent(cache_dir / f"{name}.md", name)
            _write_mpm_agent(deploy_dir / f"{name}.md", name)

        # 1 orphan (1/5 = 20%, but only 1 <= 3 absolute floor)
        orphan_file = deploy_dir / "orphan-single.md"
        _write_mpm_agent(orphan_file, "orphan-single")

        config = _make_config()
        removed = _call_detect(tmp_path, cache_dir, config)

        # Guard should NOT trigger: 1 <= 3 (absolute floor not exceeded)
        assert "orphan-single" in removed, (
            "Single orphan should be removed (absolute floor not met)"
        )
        assert not orphan_file.exists(), "Orphan file should be deleted"

    # ------------------------------------------------------------------
    # test 3: threshold not triggered below percentage
    # 20 expected + 2 orphans = 22 total, 2/22 = 9% < 20%, 2 <= 3
    # ------------------------------------------------------------------

    def test_threshold_not_triggered_below_percentage(self, tmp_path: Path) -> None:
        """When both ratio < 20% and count <= 3, orphans are removed normally."""
        deploy_dir = tmp_path / ".claude" / "agents"
        deploy_dir.mkdir(parents=True)
        cache_dir = tmp_path / "cache" / "agents"
        cache_dir.mkdir(parents=True)

        # 20 expected agents
        for i in range(20):
            name = f"expected-agent-{i}"
            _write_mpm_agent(cache_dir / f"{name}.md", name)
            _write_mpm_agent(deploy_dir / f"{name}.md", name)

        # 2 orphans (2/22 = 9% < 20%, 2 <= 3)
        orphan_files = []
        for i in range(2):
            name = f"orphan-agent-{i}"
            orphan_file = deploy_dir / f"{name}.md"
            _write_mpm_agent(orphan_file, name)
            orphan_files.append((orphan_file, name))

        config = _make_config()
        removed = _call_detect(tmp_path, cache_dir, config)

        # Guard should NOT trigger: neither condition met
        for orphan_file, name in orphan_files:
            assert name in removed, f"Orphan {name} should be removed normally"
            assert not orphan_file.exists(), f"Orphan {name} file should be deleted"

    # ------------------------------------------------------------------
    # test 4: threshold not triggered at boundary (count == 3, not > 3)
    # 10 expected + 3 orphans = 13 total, 3/13 = 23% > 20%, but 3 <= 3
    # ------------------------------------------------------------------

    def test_threshold_not_triggered_at_boundary(self, tmp_path: Path) -> None:
        """When count is exactly 3 (not > 3), guard does NOT trigger even if ratio > 20%."""
        deploy_dir = tmp_path / ".claude" / "agents"
        deploy_dir.mkdir(parents=True)
        cache_dir = tmp_path / "cache" / "agents"
        cache_dir.mkdir(parents=True)

        # 10 expected agents
        for i in range(10):
            name = f"expected-agent-{i}"
            _write_mpm_agent(cache_dir / f"{name}.md", name)
            _write_mpm_agent(deploy_dir / f"{name}.md", name)

        # 3 orphans (3/13 = 23% > 20%, but 3 is NOT > 3)
        orphan_files = []
        for i in range(3):
            name = f"orphan-agent-{i}"
            orphan_file = deploy_dir / f"{name}.md"
            _write_mpm_agent(orphan_file, name)
            orphan_files.append((orphan_file, name))

        config = _make_config()
        removed = _call_detect(tmp_path, cache_dir, config)

        # Guard should NOT trigger: 3 is not > 3 (absolute floor not exceeded)
        for orphan_file, name in orphan_files:
            assert name in removed, (
                f"Orphan {name} should be removed (count=3 does not exceed absolute floor of 3)"
            )
            assert not orphan_file.exists(), f"Orphan {name} file should be deleted"

    # ------------------------------------------------------------------
    # test 5: threshold triggered logs warning
    # ------------------------------------------------------------------

    def test_threshold_triggered_logs_warning(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """When threshold guard triggers, a warning is logged with ratio and count."""
        deploy_dir = tmp_path / ".claude" / "agents"
        deploy_dir.mkdir(parents=True)
        cache_dir = tmp_path / "cache" / "agents"
        cache_dir.mkdir(parents=True)

        # 6 expected agents
        for i in range(6):
            name = f"expected-agent-{i}"
            _write_mpm_agent(cache_dir / f"{name}.md", name)
            _write_mpm_agent(deploy_dir / f"{name}.md", name)

        # 5 orphans (5/11 = 45% > 20%, 5 > 3)
        for i in range(5):
            name = f"orphan-agent-{i}"
            _write_mpm_agent(deploy_dir / f"{name}.md", name)

        config = _make_config()

        with caplog.at_level(logging.WARNING):
            removed = _call_detect(tmp_path, cache_dir, config)

        assert removed == [], "All deletions should be skipped"

        # Check that warning was logged
        warning_messages = [
            record.message
            for record in caplog.records
            if record.levelno == logging.WARNING
        ]
        assert any("threshold exceeded" in msg.lower() for msg in warning_messages), (
            f"Expected warning about threshold exceeded. "
            f"Got warnings: {warning_messages}"
        )
        # Verify the warning includes the count
        assert any("5/11" in msg for msg in warning_messages), (
            f"Expected warning to contain '5/11' ratio. "
            f"Got warnings: {warning_messages}"
        )
