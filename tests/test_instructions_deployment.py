#!/usr/bin/env python3
"""Test script to verify INSTRUCTIONS.md deployment (not CLAUDE.md)."""

import sys
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import logging

from claude_mpm.services.agents.deployment.system_instructions_deployer import (
    SystemInstructionsDeployer,
)


def test_deployment():
    """Test that INSTRUCTIONS.md is deployed correctly without creating CLAUDE.md."""
    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Set up test logger
        logger = logging.getLogger("test")
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
        logger.addHandler(handler)

        # Create deployer
        deployer = SystemInstructionsDeployer(logger, temp_path)

        # Create test target directory
        target_dir = temp_path / "test_target"
        target_dir.mkdir(parents=True, exist_ok=True)

        # Prepare results dict
        results = {
            "deployed": [],
            "updated": [],
            "skipped": [],
            "errors": [],
        }

        # Run deployment
        print("\n=== Testing SystemInstructionsDeployer ===")
        print(f"Target directory: {target_dir}")

        try:
            deployer.deploy_system_instructions(
                target_dir=target_dir,
                force_rebuild=True,
                results=results,
            )

            # Check what files were created in .claude directory
            claude_dir = temp_path / ".claude"
            if claude_dir.exists():
                print(f"\nFiles created in {claude_dir}:")
                for file_path in claude_dir.iterdir():
                    print(f"  - {file_path.name}")

                # Verify CLAUDE.md was NOT created
                claude_md_path = claude_dir / "CLAUDE.md"
                instructions_md_path = claude_dir / "INSTRUCTIONS.md"

                if claude_md_path.exists():
                    print("\n❌ ERROR: CLAUDE.md was created (this should not happen!)")
                    raise AssertionError("CLAUDE.md should not be created")
                print("\n✓ CLAUDE.md was NOT created (correct)")

                if instructions_md_path.exists():
                    print("✓ INSTRUCTIONS.md was created (correct)")
                else:
                    print("⚠ INSTRUCTIONS.md was not created (check if source exists)")

            else:
                print(f"\n.claude directory was not created at {claude_dir}")

            print("\nDeployment results:")
            print(f"  Deployed: {len(results['deployed'])} files")
            print(f"  Updated: {len(results['updated'])} files")
            print(f"  Skipped: {len(results['skipped'])} files")
            print(f"  Errors: {len(results['errors'])} errors")

            if results["errors"]:
                print("\nErrors encountered:")
                for error in results["errors"]:
                    print(f"  - {error}")

        except Exception as e:
            print(f"\n❌ Test failed with error: {e}")
            import traceback

            traceback.print_exc()
            raise AssertionError(f"Test failed with error: {e}") from e


if __name__ == "__main__":
    success = test_deployment()
    if success:
        print("\n✅ Test completed successfully!")
        print("INSTRUCTIONS.md deployment is working correctly (no CLAUDE.md created)")
        sys.exit(0)
    else:
        print("\n❌ Test failed!")
        sys.exit(1)
