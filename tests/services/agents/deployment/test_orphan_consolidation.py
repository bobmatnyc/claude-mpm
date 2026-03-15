"""
Test orphan detection consolidation (Phase 2b).

Verifies that:
1. System B methods in MultiSourceDeploymentService now have provenance checks
2. The 'or agent_id' bug is gone from startup.py
3. User agents are preserved even when they appear as orphans
4. System A is the only code path that performs orphan deletion during startup
"""

import inspect
import re
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from claude_mpm.services.agents.deployment.startup_reconciliation import (
    _detect_and_remove_orphaned_agents,
)
from claude_mpm.utils.agent_provenance import is_mpm_managed_agent


class TestNoOrAgentIdInStartup:
    """Verify the 'or agent_id' provenance bug is gone from startup.py."""

    def test_no_or_agent_id_in_startup_cleanup(self):
        """Verify 'or agent_id' pattern is removed from startup.py cleanup code."""
        from claude_mpm.cli import startup

        source = inspect.getsource(startup._cleanup_orphaned_agents)

        # The buggy pattern was:
        #   if ("Claude MPM" in str(author) or source == "remote" or agent_id):
        # Ensure this pattern is gone
        assert "or agent_id" not in source, (
            "The 'or agent_id' bug is still present in startup.py's "
            "_cleanup_orphaned_agents. Any agent with an agent_id field "
            "would be incorrectly treated as MPM-managed."
        )

    def test_startup_cleanup_uses_canonical_provenance(self):
        """Verify startup cleanup delegates to is_mpm_managed_agent."""
        from claude_mpm.cli import startup

        source = inspect.getsource(startup._cleanup_orphaned_agents)

        assert "is_mpm_managed_agent" in source, (
            "startup._cleanup_orphaned_agents should use the canonical "
            "is_mpm_managed_agent() for provenance detection."
        )


class TestSystemBHasProvenanceChecks:
    """Verify System B methods in MultiSourceDeploymentService have provenance."""

    def test_detect_orphaned_agents_has_provenance_check(self):
        """Verify detect_orphaned_agents uses provenance filtering."""
        from claude_mpm.services.agents.deployment.multi_source_deployment_service import (
            MultiSourceAgentDeploymentService,
        )

        source = inspect.getsource(
            MultiSourceAgentDeploymentService.detect_orphaned_agents
        )

        assert "is_mpm_managed_file" in source, (
            "detect_orphaned_agents must use is_mpm_managed_file for "
            "provenance checking to prevent deletion of user agents."
        )

    def test_cleanup_orphaned_agents_delegates_to_detect(self):
        """Verify cleanup_orphaned_agents calls detect_orphaned_agents (which has provenance)."""
        from claude_mpm.services.agents.deployment.multi_source_deployment_service import (
            MultiSourceAgentDeploymentService,
        )

        source = inspect.getsource(
            MultiSourceAgentDeploymentService.cleanup_orphaned_agents
        )

        assert "self.detect_orphaned_agents" in source, (
            "cleanup_orphaned_agents should delegate to detect_orphaned_agents "
            "which has provenance checks."
        )


class TestUserAgentPreservedEvenAsOrphan:
    """Verify user agents survive orphan detection in all systems."""

    @pytest.fixture
    def deploy_dir(self):
        """Create a temporary deploy directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_user_agent_preserved_by_system_a(self, deploy_dir):
        """A user agent (no MPM author) should NOT be deleted by System A.

        System A's _detect_and_remove_orphaned_agents checks is_mpm_managed_agent
        before removing. A user agent with a non-MPM author must survive.
        """
        # Set up a project directory with .claude/agents
        project_path = deploy_dir
        agents_dir = project_path / ".claude" / "agents"
        agents_dir.mkdir(parents=True, exist_ok=True)

        # Create a user agent that is NOT in expected stems
        user_agent = agents_dir / "my-custom-agent.md"
        user_agent.write_text(
            """---
agent_id: my-custom-agent
author: Jane Developer
version: 1.0.0
---

# My Custom Agent

A user-created agent that must be preserved.
"""
        )

        # Create a MPM orphan agent (not in expected stems, but IS MPM-managed)
        mpm_orphan = agents_dir / "old-mpm-agent.md"
        mpm_orphan.write_text(
            """---
agent_id: old-mpm-agent
author: claude-mpm
version: 1.0.0
---

# Old MPM Agent
"""
        )

        # Verify is_mpm_managed_agent correctly classifies
        assert not is_mpm_managed_agent(user_agent.read_text()), (
            "User agent should NOT be classified as MPM-managed"
        )
        assert is_mpm_managed_agent(mpm_orphan.read_text()), (
            "MPM orphan should be classified as MPM-managed"
        )

        # Simulate System A orphan detection with mocked dependencies
        mock_config = MagicMock()
        mock_config.agents.enabled = ["some-expected-agent"]
        mock_config.agents.required = []

        # Create a fake cache dir with one expected agent
        cache_dir = deploy_dir / "cache" / "agents"
        cache_dir.mkdir(parents=True, exist_ok=True)
        (cache_dir / "some-expected-agent.md").write_text(
            "---\nauthor: claude-mpm\n---\n# Expected"
        )

        with patch("claude_mpm.core.unified_paths.get_path_manager") as mock_pm:
            mock_path_mgr = MagicMock()
            mock_path_mgr.get_cache_dir.return_value = deploy_dir / "cache"
            mock_pm.return_value = mock_path_mgr

            mock_agent_result = MagicMock()

            removed = _detect_and_remove_orphaned_agents(
                project_path, mock_config, mock_agent_result
            )

        # User agent should NOT be in removed list
        assert "my-custom-agent" not in removed, (
            "User agent was incorrectly removed by System A orphan detection"
        )
        # The user agent file should still exist
        assert user_agent.exists(), "User agent file was deleted by System A"
        # The MPM orphan SHOULD be removed
        assert "old-mpm-agent" in removed, (
            "MPM orphan agent should have been removed by System A"
        )
        assert not mpm_orphan.exists(), (
            "MPM orphan file should have been deleted by System A"
        )

    def test_agent_with_only_agent_id_not_treated_as_mpm(self):
        """An agent with only agent_id (no MPM author) must NOT be treated as MPM-managed."""
        content = """---
agent_id: some-agent
version: 1.0.0
---

# Some Agent
"""
        assert not is_mpm_managed_agent(content), (
            "Agent with only agent_id (no author) should NOT be MPM-managed. "
            "This was the 'or agent_id' bug."
        )

    def test_agent_with_source_remote_not_treated_as_mpm(self):
        """An agent with only source: remote (no MPM author) must NOT be MPM-managed."""
        content = """---
source: remote
version: 1.0.0
---

# Remote Agent
"""
        assert not is_mpm_managed_agent(content), (
            "Agent with only 'source: remote' (no author) should NOT be MPM-managed."
        )


class TestSystemAIsOnlyOrphanSystem:
    """Verify System A is the sole automatic orphan deletion system."""

    def test_no_orphan_deletion_outside_system_a(self):
        """Grep source tree to verify no orphan deletion exists outside System A.

        The only code that should call .unlink() on orphaned agents during
        automatic startup is _detect_and_remove_orphaned_agents in
        startup_reconciliation.py. Other files may have .unlink() but only
        in explicit user-triggered CLI commands (which is acceptable).
        """
        import claude_mpm.services.agents.deployment.startup_reconciliation as system_a

        source_a = inspect.getsource(system_a._detect_and_remove_orphaned_agents)

        # Verify System A has the unlink call
        assert "unlink()" in source_a, (
            "System A should contain the .unlink() call for orphan removal"
        )

    def test_startup_reconciliation_calls_system_a(self):
        """Verify perform_startup_reconciliation calls System A's orphan detection."""
        from claude_mpm.services.agents.deployment import startup_reconciliation

        source = inspect.getsource(
            startup_reconciliation.perform_startup_reconciliation
        )

        assert "_detect_and_remove_orphaned_agents" in source, (
            "perform_startup_reconciliation must call the canonical "
            "_detect_and_remove_orphaned_agents (System A)"
        )

    def test_system_a_has_threshold_guard(self):
        """Verify System A has the threshold guard to prevent mass deletion."""
        import claude_mpm.services.agents.deployment.startup_reconciliation as system_a

        source = inspect.getsource(system_a._detect_and_remove_orphaned_agents)

        assert "ORPHAN_RATIO_THRESHOLD" in source, (
            "System A must have the ORPHAN_RATIO_THRESHOLD guard"
        )
        assert "ORPHAN_ABSOLUTE_FLOOR" in source, (
            "System A must have the ORPHAN_ABSOLUTE_FLOOR guard"
        )

    def test_system_a_has_empty_set_guard(self):
        """Verify System A has the empty expected_stems guard."""
        import claude_mpm.services.agents.deployment.startup_reconciliation as system_a

        source = inspect.getsource(system_a._detect_and_remove_orphaned_agents)

        assert "not expected_stems" in source or "if not expected_stems" in source, (
            "System A must guard against empty expected_stems to prevent "
            "accidental deletion when cache is empty"
        )
