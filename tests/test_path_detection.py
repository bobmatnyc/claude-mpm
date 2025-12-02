#!/usr/bin/env python3
"""
Test script to verify path detection works correctly with pipx and development installations.
"""

import os
import sys


def test_path_detection():
    """Test the enhanced path detection logic."""

    print("=" * 70)
    print("PATH DETECTION TEST")
    print("=" * 70)

    # Show current environment
    print("\n1. Environment Information:")
    print("-" * 40)
    print(f"Python executable: {sys.executable}")
    print("Python path entries:")
    for i, p in enumerate(sys.path[:5]):
        print(f"  [{i}] {p}")
    print(f"Working directory: {os.getcwd()}")
    print(f"CLAUDE_MPM_DEV_MODE: {os.environ.get('CLAUDE_MPM_DEV_MODE', 'not set')}")

    # Import and test the path manager
    print("\n2. Path Manager Detection:")
    print("-" * 40)

    try:
        from claude_mpm.core.unified_paths import (
            DeploymentContext,
            PathContext,
            get_path_manager,
        )

        # Clear cache to get fresh detection
        PathContext.detect_deployment_context.cache_clear()

        # Get deployment context
        context = PathContext.detect_deployment_context()
        print(f"Deployment context: {context.value}")

        # Check if editable install was detected
        is_editable = PathContext._is_editable_install()
        print(f"Is editable install: {is_editable}")

        # Get path manager instance
        pm = get_path_manager()
        pm.clear_cache()  # Clear cache for fresh detection

        # Show detected paths
        print("\nDetected paths:")
        print(f"  Framework root: {pm.framework_root}")
        print(f"  Package root: {pm.package_root}")
        print(f"  Project root: {pm.project_root}")
        print(f"  Agents dir: {pm.get_agents_dir()}")
        print(f"  Scripts dir: {pm.get_scripts_dir()}")

        # Verify paths exist
        print("\nPath verification:")
        print(f"  Framework root exists: {pm.framework_root.exists()}")
        print(f"  Package root exists: {pm.package_root.exists()}")
        print(f"  Agents dir exists: {pm.get_agents_dir().exists()}")

        # Check for pyproject.toml
        pyproject_path = pm.framework_root / "pyproject.toml"
        print(f"  pyproject.toml exists: {pyproject_path.exists()}")

        # Check if we're using development paths
        is_dev_paths = "/Users/masa/Projects/claude-mpm" in str(pm.framework_root)
        print(f"\nUsing development paths: {is_dev_paths}")

        if not is_dev_paths and context != DeploymentContext.PIPX_INSTALL:
            print(
                "⚠️  WARNING: Not using development paths but not in pipx install mode!"
            )
            print("    This might indicate the detection is not working correctly.")

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback

        traceback.print_exc()

    # Test with environment variable
    print("\n3. Testing with CLAUDE_MPM_DEV_MODE environment variable:")
    print("-" * 40)

    os.environ["CLAUDE_MPM_DEV_MODE"] = "1"

    try:
        # Clear cache and re-detect
        PathContext.detect_deployment_context.cache_clear()
        context = PathContext.detect_deployment_context()
        print(f"Deployment context with DEV_MODE=1: {context.value}")

        # Clear path manager cache
        pm.clear_cache()
        pm._deployment_context = context

        print(f"Framework root with DEV_MODE=1: {pm.framework_root}")

    except Exception as e:
        print(f"ERROR: {e}")
    finally:
        # Clean up environment
        del os.environ["CLAUDE_MPM_DEV_MODE"]

    print("\n" + "=" * 70)
    print("TEST COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    test_path_detection()
