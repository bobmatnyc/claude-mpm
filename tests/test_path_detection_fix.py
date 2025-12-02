#!/usr/bin/env python3
"""
Test suite for the pipx path detection fix.
Tests the enhanced deployment context detection in unified_paths.py
"""

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.core.unified_paths import (
    DeploymentContext,
    PathContext,
    UnifiedPathManager,
)


class TestPipxPathDetectionFix(unittest.TestCase):
    """Test the pipx path detection fix."""

    def setUp(self):
        """Set up test environment."""
        # Clear any cached values
        PathContext.detect_deployment_context.cache_clear()
        # Clear environment variable if set
        os.environ.pop("CLAUDE_MPM_DEV_MODE", None)

    def tearDown(self):
        """Clean up after tests."""
        # Clear cache
        PathContext.detect_deployment_context.cache_clear()
        # Clear environment variable
        os.environ.pop("CLAUDE_MPM_DEV_MODE", None)

    def test_environment_variable_override():
        """Test that CLAUDE_MPM_DEV_MODE environment variable forces development mode."""
        # Set environment variable
        os.environ["CLAUDE_MPM_DEV_MODE"] = "1"

        # Get deployment context
        context = PathContext.detect_deployment_context()

        # Should be development mode
        self.assertEqual(context, DeploymentContext.DEVELOPMENT)

        # Test with different values
        for value in ["true", "True", "TRUE", "yes", "Yes", "YES"]:
            PathContext.detect_deployment_context.cache_clear()
            os.environ["CLAUDE_MPM_DEV_MODE"] = value
            context = PathContext.detect_deployment_context()
            self.assertEqual(
                context,
                DeploymentContext.DEVELOPMENT,
                f"Failed for CLAUDE_MPM_DEV_MODE={value}",
            )

    def test_environment_variable_false_values():
        """Test that invalid CLAUDE_MPM_DEV_MODE values don't force development mode."""
        # Test various false values
        for value in ["0", "false", "False", "no", "No", ""]:
            PathContext.detect_deployment_context.cache_clear()
            os.environ["CLAUDE_MPM_DEV_MODE"] = value

            with patch("claude_mpm.core.unified_paths.Path"):
                # Mock a pipx installation
                mock_module = MagicMock()
                mock_module.__file__ = "/Users/masa/.local/pipx/venvs/claude-mpm/lib/python3.13/site-packages/claude_mpm/__init__.py"

                with patch.dict("sys.modules", {"claude_mpm": mock_module}):
                    context = PathContext.detect_deployment_context()
                    # Should not be development mode
                    self.assertNotEqual(
                        context,
                        DeploymentContext.DEVELOPMENT,
                        f"Should not be development for CLAUDE_MPM_DEV_MODE={value}",
                    )

    def test_editable_install_detection():
        """Test that editable installations are properly detected."""
        # Test the _is_editable_install method

        # Mock current working directory in development project
        with patch("claude_mpm.core.unified_paths.Path.cwd") as mock_cwd:
            mock_cwd.return_value = Path("/Users/masa/Projects/claude-mpm")

            # Mock the project structure
            with patch.object(Path, "exists") as mock_exists:

                def exists_side_effect(self):
                    path_str = str(self)
                    if "pyproject.toml" in path_str and "claude-mpm" in path_str:
                        return True
                    if "src/claude_mpm" in path_str and "claude-mpm" in path_str:
                        return True
                    return "scripts/claude-mpm" in path_str

                mock_exists.side_effect = exists_side_effect

                # Mock reading pyproject.toml
                with patch.object(Path, "read_text") as mock_read:
                    mock_read.return_value = 'name = "claude-mpm"\nversion = "4.0.19"'

                    # Should detect as editable install
                    is_editable = PathContext._is_editable_install()
                    self.assertTrue(is_editable)

    def test_development_detection_from_cwd():
        """Test that running from development directory is detected."""
        # Clear cache
        PathContext.detect_deployment_context.cache_clear()

        # Mock being in a pipx installation but running from dev directory
        mock_module = MagicMock()
        mock_module.__file__ = "/Users/masa/.local/pipx/venvs/claude-mpm/lib/python3.13/site-packages/claude_mpm/__init__.py"

        with patch.dict("sys.modules", {"claude_mpm": mock_module}):
            with patch("claude_mpm.core.unified_paths.Path.cwd") as mock_cwd:
                mock_cwd.return_value = Path("/Users/masa/Projects/claude-mpm")

                with patch.object(Path, "exists") as mock_exists:

                    def exists_side_effect(self):
                        path_str = str(self)
                        # Return True for project structure files
                        if path_str.endswith("pyproject.toml"):
                            return "/Users/masa/Projects/claude-mpm" in path_str
                        if path_str.endswith("src/claude_mpm"):
                            return "/Users/masa/Projects/claude-mpm" in path_str
                        if path_str.endswith("scripts/claude-mpm"):
                            return "/Users/masa/Projects/claude-mpm" in path_str
                        return False

                    mock_exists.side_effect = exists_side_effect

                    with patch.object(Path, "read_text") as mock_read:
                        mock_read.return_value = 'name = "claude-mpm"'

                        # Should detect development even though module is from pipx
                        context = PathContext.detect_deployment_context()
                        self.assertEqual(context, DeploymentContext.DEVELOPMENT)

    def test_framework_root_in_development_mode():
        """Test that framework_root returns development path in development mode."""
        # Create a path manager
        pm = UnifiedPathManager()

        # Force development context
        pm._deployment_context = DeploymentContext.DEVELOPMENT

        # Mock the current working directory
        with patch("claude_mpm.core.unified_paths.Path.cwd") as mock_cwd:
            mock_cwd.return_value = Path("/Users/masa/Projects/claude-mpm")

            with patch.object(Path, "exists") as mock_exists:

                def exists_side_effect(self):
                    path_str = str(self)
                    if "claude-mpm/src/claude_mpm" in path_str:
                        return True
                    return "claude-mpm/pyproject.toml" in path_str

                mock_exists.side_effect = exists_side_effect

                with patch.object(Path, "read_text") as mock_read:
                    mock_read.return_value = 'name = "claude-mpm"'

                    # Clear cache to force re-evaluation
                    if hasattr(type(pm).framework_root, "fget"):
                        type(pm).framework_root.fget.cache_clear()

                    # Should return development root
                    root = pm.framework_root
                    self.assertIn("Projects/claude-mpm", str(root))
                    self.assertNotIn("pipx", str(root))

    def test_package_root_in_development_mode():
        """Test that package_root returns src directory in development mode."""
        # Create a path manager
        pm = UnifiedPathManager()

        # Force development context
        pm._deployment_context = DeploymentContext.DEVELOPMENT

        # Mock framework root
        with patch.object(
            pm,
            "framework_root",
            new_callable=lambda: MagicMock(
                return_value=Path("/Users/masa/Projects/claude-mpm")
            ),
        ), patch.object(Path, "exists", return_value=True):
            # Should return src/claude_mpm
            pkg_root = pm.package_root
            self.assertEqual(
                pkg_root, Path("/Users/masa/Projects/claude-mpm/src/claude_mpm")
            )


if __name__ == "__main__":
    unittest.main()
