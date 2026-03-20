#!/usr/bin/env python3
"""
Test script to verify that system instructions are NOT automatically deployed to .claude/

This script verifies that:
1. System doesn't automatically create INSTRUCTIONS.md, MEMORY.md, WORKFLOW.md in .claude/
2. Framework correctly loads from .claude-mpm/ if files exist there
3. Explicit deployment method works when called
"""

import os
import sys
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import logging

from claude_mpm.core.framework_loader import FrameworkLoader
from claude_mpm.services.agents.deployment.agent_deployment import (
    AgentDeploymentService,
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_no_auto_deploy")


def test_no_automatic_deployment():
    """Test that deploy_agents does NOT automatically create system instructions."""

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        claude_dir = tmpdir_path / ".claude"
        claude_mpm_dir = tmpdir_path / ".claude-mpm"

        # Create service
        service = AgentDeploymentService(working_directory=tmpdir_path)

        # Deploy agents (should NOT create system instructions)
        logger.info(
            "Testing deploy_agents() - should NOT create system instructions..."
        )
        service.deploy_agents(force_rebuild=False)

        # Check that .claude directory doesn't have system instructions
        instructions_in_claude = [
            claude_dir / "INSTRUCTIONS.md",
            claude_dir / "MEMORY.md",
            claude_dir / "WORKFLOW.md",
        ]

        for file_path in instructions_in_claude:
            if file_path.exists():
                logger.error(
                    f"❌ FAILED: {file_path} was created automatically (should NOT happen)"
                )
                return False

        logger.info(
            "✅ PASS: No system instructions were automatically created in .claude/"
        )

        # Test explicit deployment
        logger.info("\nTesting explicit deployment to .claude-mpm/...")
        service.deploy_system_instructions_explicit(
            target_dir=claude_mpm_dir, force_rebuild=True
        )

        # Check that files were created in .claude-mpm/
        instructions_in_mpm = [
            claude_mpm_dir / "INSTRUCTIONS.md",
            claude_mpm_dir / "MEMORY.md",
            claude_mpm_dir / "WORKFLOW.md",
        ]

        for file_path in instructions_in_mpm:
            if not file_path.exists():
                logger.error(
                    f"❌ FAILED: {file_path} was NOT created by explicit deployment"
                )
                return False

        logger.info(
            "✅ PASS: System instructions were deployed to .claude-mpm/ when explicitly requested"
        )

        # Verify framework loader reads from .claude-mpm/
        logger.info("\nTesting framework loader reads from .claude-mpm/...")
        loader = FrameworkLoader(framework_path=tmpdir_path)

        # The loader should find the custom instructions
        if loader.framework_content.get("custom_instructions"):
            logger.info(
                "✅ PASS: Framework loader found custom instructions in .claude-mpm/"
            )
        else:
            logger.warning(
                "⚠️  Framework loader didn't find custom instructions (may be expected if not in test dir)"
            )

        return True


def test_framework_loader_paths():
    """Test that framework loader looks in correct directories."""

    logger.info("\nTesting framework loader search paths...")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # Create .claude-mpm directory with test instructions
        claude_mpm_dir = tmpdir_path / ".claude-mpm"
        claude_mpm_dir.mkdir(parents=True, exist_ok=True)

        test_instructions = "# Test Instructions\nThis is a test."
        (claude_mpm_dir / "INSTRUCTIONS.md").write_text(test_instructions)

        # Create .claude directory (should be ignored)
        claude_dir = tmpdir_path / ".claude"
        claude_dir.mkdir(parents=True, exist_ok=True)
        (claude_dir / "INSTRUCTIONS.md").write_text(
            "# Wrong Instructions\nShould not be loaded."
        )

        # Change to temp directory for testing
        original_cwd = Path.cwd()
        try:
            os.chdir(tmpdir_path)

            # Create framework loader
            loader = FrameworkLoader()

            # Check if it loaded from .claude-mpm (correct) and not .claude (wrong)
            custom_instructions = loader.framework_content.get(
                "custom_instructions", ""
            )

            if "Test Instructions" in custom_instructions:
                logger.info(
                    "✅ PASS: Framework loader correctly reads from .claude-mpm/"
                )
                if "Wrong Instructions" in custom_instructions:
                    logger.error(
                        "❌ FAILED: Framework loader also read from .claude/ (should NOT)"
                    )
                    return False
                return True
            logger.warning(
                "⚠️  Framework loader didn't find instructions in .claude-mpm/"
            )
            return False

        finally:
            os.chdir(original_cwd)


def main():
    """Run all tests."""

    logger.info("=" * 60)
    logger.info("Testing: No Automatic System Instructions Deployment")
    logger.info("=" * 60)

    all_passed = True

    # Test 1: No automatic deployment
    if not test_no_automatic_deployment():
        all_passed = False

    # Test 2: Framework loader paths
    if not test_framework_loader_paths():
        all_passed = False

    logger.info("\n" + "=" * 60)
    if all_passed:
        logger.info("✅ ALL TESTS PASSED")
        logger.info("System correctly prevents automatic deployment to .claude/")
        logger.info("System correctly uses .claude-mpm/ for custom instructions")
    else:
        logger.error("❌ SOME TESTS FAILED")
        logger.error("Please review the errors above")
        sys.exit(1)

    logger.info("=" * 60)


if __name__ == "__main__":
    main()
