"""CON-1: Behavioral equivalence tests for deploy_agent_file().

Both the startup reconciliation pipeline (DeploymentReconciler._deploy_agent)
and the git-source pipeline (GitSourceSyncService.deploy_agents_to_project)
call deploy_agent_file() from deployment_utils.  These tests verify that
identical inputs produce identical outputs regardless of which caller invoked
the function, capturing current behavior as a safety net.

Key behaviors captured:
- Same source file + deployment dir => identical output file on disk
- Frontmatter injection produces identical results for both pipelines
"""

from pathlib import Path

import pytest

from claude_mpm.services.agents.deployment_utils import deploy_agent_file

# ---------------------------------------------------------------------------
# CON-1 Tests
# ---------------------------------------------------------------------------


class TestBehavioralEquivalenceDeploy:
    """CON-1: Verify deploy_agent_file() is deterministic across callers."""

    def test_con1_same_input_produces_identical_files(self, tmp_path):
        """Calling deploy_agent_file() twice with the same source file
        produces byte-identical deployed files in different target dirs.

        This confirms that the two deployment pipelines (reconciler vs
        git-source) produce the same result when they call deploy_agent_file().
        """
        # Create a source file (simulating a cache entry)
        source = tmp_path / "cache" / "engineer.md"
        source.parent.mkdir(parents=True)
        source.write_text(
            "---\nname: Engineer\n---\n# Engineer\nImplementation agent.\n",
            encoding="utf-8",
        )

        # Deploy to two separate target directories (simulating two pipelines)
        target_a = tmp_path / "pipeline_a" / ".claude" / "agents"
        target_b = tmp_path / "pipeline_b" / ".claude" / "agents"

        result_a = deploy_agent_file(
            source_file=source,
            deployment_dir=target_a,
            cleanup_legacy=True,
            ensure_frontmatter=True,
            force=True,
        )

        result_b = deploy_agent_file(
            source_file=source,
            deployment_dir=target_b,
            cleanup_legacy=True,
            ensure_frontmatter=True,
            force=True,
        )

        # Both should succeed
        assert result_a.success, f"Pipeline A failed: {result_a.error}"
        assert result_b.success, f"Pipeline B failed: {result_b.error}"

        # Both should be "deployed" (new files)
        assert result_a.action == "deployed"
        assert result_b.action == "deployed"

        # Output files should be byte-identical
        content_a = result_a.deployed_path.read_text(encoding="utf-8")
        content_b = result_b.deployed_path.read_text(encoding="utf-8")
        assert content_a == content_b, (
            "deploy_agent_file() produced different content for identical inputs"
        )

        # Filenames should be identical (both normalized)
        assert result_a.deployed_path.name == result_b.deployed_path.name

    def test_con1_frontmatter_injection_is_identical(self, tmp_path):
        """When a source file lacks agent_id in frontmatter, both
        deployment paths inject identical agent_id values.

        This captures the current ensure_agent_id_in_frontmatter() behavior
        called by deploy_agent_file().
        """
        # Source file WITHOUT agent_id
        source = tmp_path / "cache" / "python-engineer.md"
        source.parent.mkdir(parents=True)
        source.write_text(
            "---\nname: Python Engineer\nauthor: claude-mpm\n---\n# Python\nContent.\n",
            encoding="utf-8",
        )

        # Deploy via two "pipelines"
        target_reconciler = tmp_path / "reconciler" / ".claude" / "agents"
        target_gitsync = tmp_path / "gitsync" / ".claude" / "agents"

        result_reconciler = deploy_agent_file(
            source_file=source,
            deployment_dir=target_reconciler,
            cleanup_legacy=True,
            ensure_frontmatter=True,
            force=True,
        )

        result_gitsync = deploy_agent_file(
            source_file=source,
            deployment_dir=target_gitsync,
            cleanup_legacy=True,
            ensure_frontmatter=True,
            force=True,
        )

        assert result_reconciler.success
        assert result_gitsync.success

        content_r = result_reconciler.deployed_path.read_text(encoding="utf-8")
        content_g = result_gitsync.deployed_path.read_text(encoding="utf-8")

        # Both should have agent_id injected
        assert "agent_id: python-engineer" in content_r
        assert "agent_id: python-engineer" in content_g

        # Content should be identical
        assert content_r == content_g, (
            "Frontmatter injection produced different results for identical inputs"
        )

        # Deployed filename should be normalized identically
        assert result_reconciler.deployed_path.name == "python-engineer.md"
        assert result_gitsync.deployed_path.name == "python-engineer.md"

    def test_con1_underscore_source_normalized_to_dashes(self, tmp_path):
        """When a source file uses underscores (python_engineer.md), the
        deployed filename is normalized to dashes (python-engineer.md) and
        the injected agent_id uses dashes (python-engineer).

        This captures the normalize_deployment_filename() behavior that
        converts underscores to dashes for consistent deployment naming.
        """
        # Source file with underscores in filename
        source = tmp_path / "cache" / "python_engineer.md"
        source.parent.mkdir(parents=True)
        source.write_text(
            "---\nname: Python Engineer\n---\n# Python Engineer\nImplementation agent.\n",
            encoding="utf-8",
        )

        target = tmp_path / "deploy" / ".claude" / "agents"

        result = deploy_agent_file(
            source_file=source,
            deployment_dir=target,
            cleanup_legacy=True,
            ensure_frontmatter=True,
            force=True,
        )

        assert result.success, f"Deployment failed: {result.error}"

        # Deployed filename should use dashes, not underscores
        assert result.deployed_path.name == "python-engineer.md"

        # Injected agent_id should also use dashes
        content = result.deployed_path.read_text(encoding="utf-8")
        assert "agent_id: python-engineer" in content
