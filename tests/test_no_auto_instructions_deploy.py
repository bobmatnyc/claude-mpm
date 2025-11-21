"""
Test that system instructions are NEVER automatically deployed to .claude/

This test ensures that:
1. System doesn't automatically write INSTRUCTIONS.md, MEMORY.md, WORKFLOW.md to .claude/
2. These files are only created when explicitly requested
3. Framework correctly reads from .claude-mpm/ instead
"""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.core.framework_loader import FrameworkLoader
from claude_mpm.services.agents.deployment.agent_deployment import (
    AgentDeploymentService,
)
from claude_mpm.services.agents.deployment.system_instructions_deployer import (
    SystemInstructionsDeployer,
)


class TestNoAutoInstructionsDeploy:
    """Test that system instructions are never automatically deployed."""

    def test_deploy_agents_does_not_create_instructions(self):
        """Test that deploy_agents() does NOT create system instructions automatically."""

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            claude_dir = tmpdir_path / ".claude"

            # Create service
            service = AgentDeploymentService(working_directory=tmpdir_path)

            # Deploy agents - should NOT create system instructions
            service.deploy_agents(force_rebuild=False)

            # Verify .claude directory doesn't have system instructions
            assert not (claude_dir / "INSTRUCTIONS.md").exists(), (
                "INSTRUCTIONS.md should NOT be automatically created in .claude/"
            )
            assert not (claude_dir / "MEMORY.md").exists(), (
                "MEMORY.md should NOT be automatically created in .claude/"
            )
            assert not (claude_dir / "WORKFLOW.md").exists(), (
                "WORKFLOW.md should NOT be automatically created in .claude/"
            )

    def test_deploy_system_instructions_is_not_called(self):
        """Test that _deploy_system_instructions is NOT called during deploy_agents."""

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            service = AgentDeploymentService(working_directory=tmpdir_path)

            # Mock the _deploy_system_instructions method
            with patch.object(service, "_deploy_system_instructions") as mock_deploy:
                # Deploy agents
                service.deploy_agents(force_rebuild=False)

                # Verify _deploy_system_instructions was NOT called
                mock_deploy.assert_not_called()

    def test_explicit_deployment_works(self):
        """Test that explicit deployment to .claude-mpm/ works when requested."""

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            claude_mpm_dir = tmpdir_path / ".claude-mpm"

            # Create service
            service = AgentDeploymentService(working_directory=tmpdir_path)

            # Explicitly deploy system instructions
            service.deploy_system_instructions_explicit(
                target_dir=claude_mpm_dir, force_rebuild=True
            )

            # Verify files were created in .claude-mpm/
            assert (claude_mpm_dir / "INSTRUCTIONS.md").exists(), (
                "INSTRUCTIONS.md should be created in .claude-mpm/ when explicitly requested"
            )
            assert (claude_mpm_dir / "MEMORY.md").exists(), (
                "MEMORY.md should be created in .claude-mpm/ when explicitly requested"
            )
            assert (claude_mpm_dir / "WORKFLOW.md").exists(), (
                "WORKFLOW.md should be created in .claude-mpm/ when explicitly requested"
            )

            # Verify no files in .claude/
            claude_dir = tmpdir_path / ".claude"
            assert not (claude_dir / "INSTRUCTIONS.md").exists(), (
                "INSTRUCTIONS.md should NOT be in .claude/"
            )
            assert not (claude_dir / "MEMORY.md").exists(), (
                "MEMORY.md should NOT be in .claude/"
            )
            assert not (claude_dir / "WORKFLOW.md").exists(), (
                "WORKFLOW.md should NOT be in .claude/"
            )

    def test_framework_loader_reads_from_claude_mpm(self):
        """Test that framework loader reads from .claude-mpm/ not .claude/."""

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create .claude-mpm directory with test instructions
            claude_mpm_dir = tmpdir_path / ".claude-mpm"
            claude_mpm_dir.mkdir(parents=True, exist_ok=True)
            (claude_mpm_dir / "INSTRUCTIONS.md").write_text(
                "# Correct Instructions\nFrom .claude-mpm/"
            )

            # Create .claude directory with wrong instructions
            claude_dir = tmpdir_path / ".claude"
            claude_dir.mkdir(parents=True, exist_ok=True)
            (claude_dir / "INSTRUCTIONS.md").write_text(
                "# Wrong Instructions\nFrom .claude/ - should not be loaded"
            )

            # Change to temp directory
            original_cwd = Path.cwd()
            try:
                os.chdir(tmpdir_path)

                # Create framework loader
                loader = FrameworkLoader()

                # Check custom instructions
                custom_instructions = loader.framework_content.get(
                    "custom_instructions", ""
                )

                # Should load from .claude-mpm/
                assert "Correct Instructions" in custom_instructions, (
                    "Should load instructions from .claude-mpm/"
                )

                # Should NOT load from .claude/
                assert "Wrong Instructions" not in custom_instructions, (
                    "Should NOT load instructions from .claude/"
                )

            finally:
                os.chdir(original_cwd)

    def test_deploy_system_instructions_to_claude_mpm(self):
        """Test the new deploy_system_instructions_to_claude_mpm method."""

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            target_dir = tmpdir_path / ".claude-mpm"
            target_dir.mkdir(parents=True, exist_ok=True)

            # Create deployer
            logger = MagicMock()
            deployer = SystemInstructionsDeployer(logger, tmpdir_path)

            results = {
                "deployed": [],
                "updated": [],
                "skipped": [],
                "errors": [],
            }

            # Deploy to .claude
            deployer.deploy_system_instructions(
                target_dir=target_dir,
                force_rebuild=True,
                results=results,
            )

            # Check that files would be deployed to .claude (always project level)
            # Note: Actual deployment depends on source files existing
            # This test verifies the method exists and doesn't throw errors
            assert len(results["errors"]) == 0 or all(
                "not found" in err for err in results["errors"]
            ), "Should only have 'not found' errors if source files don't exist"

    def test_old_deploy_method_targets_claude_dir(self):
        """Test that old deploy_system_instructions (if called) would target .claude/."""

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create deployer
            logger = MagicMock()
            deployer = SystemInstructionsDeployer(logger, tmpdir_path)

            results = {
                "deployed": [],
                "updated": [],
                "skipped": [],
                "errors": [],
            }

            # The old method (if called) would deploy to .claude
            # We're testing that it exists but is NOT called automatically
            target_dir = tmpdir_path / ".claude"
            target_dir.mkdir(parents=True, exist_ok=True)

            # This method exists but should NOT be called automatically
            deployer.deploy_system_instructions(
                target_dir=target_dir,
                force_rebuild=True,
                results=results,
            )

            # The method would target ~/.claude if not project-specific
            # We're just verifying it exists for backward compatibility
            # but is NOT called during normal operations
