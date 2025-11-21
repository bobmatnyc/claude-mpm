#!/usr/bin/env python3
"""Comprehensive tests for the output style system."""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.core.framework_loader import FrameworkLoader
from claude_mpm.core.output_style_manager import OutputStyleManager


class TestOutputStyleManager:
    """Test suite for OutputStyleManager."""

    def test_version_detection_success():
        """Test successful Claude version detection."""
        with patch("subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = "Claude 1.0.83"
            mock_run.return_value = mock_result

            manager = OutputStyleManager()
            assert manager.claude_version == "1.0.83"

    def test_version_detection_not_found():
        """Test when Claude is not found."""
        with patch("subprocess.run", side_effect=FileNotFoundError):
            manager = OutputStyleManager()
            assert manager.claude_version is None

    def test_version_comparison():
        """Test version comparison logic."""
        manager = OutputStyleManager()

        # Test equal versions
        assert manager._compare_versions("1.0.83", "1.0.83") == 0

        # Test less than
        assert manager._compare_versions("1.0.82", "1.0.83") == -1
        assert manager._compare_versions("1.0.0", "1.0.83") == -1
        assert manager._compare_versions("0.9.99", "1.0.0") == -1

        # Test greater than
        assert manager._compare_versions("1.0.84", "1.0.83") == 1
        assert manager._compare_versions("1.1.0", "1.0.83") == 1
        assert manager._compare_versions("2.0.0", "1.0.83") == 1

    def test_supports_output_styles():
        """Test output style support detection."""
        with patch("subprocess.run") as mock_run:
            # Test version >= 1.0.83
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = "Claude 1.0.83"
            mock_run.return_value = mock_result

            manager = OutputStyleManager()
            assert manager.supports_output_styles() is True
            assert manager.should_inject_content() is False

        with patch("subprocess.run") as mock_run:
            # Test version < 1.0.83
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = "Claude 1.0.82"
            mock_run.return_value = mock_result

            manager = OutputStyleManager()
            assert manager.supports_output_styles() is False
            assert manager.should_inject_content() is True

    def test_extract_output_style_content():
        """Test extraction of output style content."""
        with patch("subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = "Claude 1.0.83"
            mock_run.return_value = mock_result

            manager = OutputStyleManager()
            content = manager.extract_output_style_content()

            # Check for required sections
            assert "---" in content  # YAML frontmatter
            assert "name: Claude MPM" in content
            assert "description:" in content
            assert "PRIMARY DIRECTIVE" in content
            assert "MANDATORY DELEGATION" in content
            assert "Communication Standards" in content
            assert "TodoWrite Requirements" in content

    def test_get_injectable_content():
        """Test getting injectable content without YAML frontmatter."""
        with patch("subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = "Claude 1.0.82"
            mock_run.return_value = mock_result

            manager = OutputStyleManager()
            injectable = manager.get_injectable_content()

            # Check that YAML frontmatter is removed
            assert not injectable.startswith("---")
            assert "name: Claude MPM" not in injectable

            # Check that core content is preserved
            assert "PRIMARY DIRECTIVE" in injectable
            assert "MANDATORY DELEGATION" in injectable

    def test_save_output_style():
        """Test saving output style to file."""
        with tmp_path as tmpdir, patch("subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = "Claude 1.0.83"
            mock_run.return_value = mock_result

            manager = OutputStyleManager()
            # Override the path to use temp directory
            manager.mpm_output_style_path = Path(tmpdir) / "OUTPUT_STYLE.md"

            content = "Test output style content"
            saved_path = manager.save_output_style(content)

            assert saved_path.exists()
            assert saved_path.read_text() == content

    def test_deploy_output_style_success():
        """Test successful deployment to Claude Code."""
        with tmp_path as tmpdir, patch("subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = "Claude 1.0.83"
            mock_run.return_value = mock_result

            manager = OutputStyleManager()
            # Override paths to use temp directory
            manager.output_style_dir = Path(tmpdir) / "output-styles"
            manager.output_style_path = manager.output_style_dir / "claude-mpm.md"
            manager.settings_file = Path(tmpdir) / "settings.json"

            content = "Test output style content"
            deployed = manager.deploy_output_style(content)

            assert deployed is True
            assert manager.output_style_path.exists()
            assert manager.output_style_path.read_text() == content

            # Check settings were updated
            assert manager.settings_file.exists()
            settings = json.loads(manager.settings_file.read_text())
            assert settings["activeOutputStyle"] == "claude-mpm"

    def test_deploy_output_style_unsupported_version():
        """Test deployment fails for older Claude versions."""
        with patch("subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = "Claude 1.0.82"
            mock_run.return_value = mock_result

            manager = OutputStyleManager()
            content = "Test output style content"
            deployed = manager.deploy_output_style(content)

            assert deployed is False


class TestFrameworkLoaderIntegration:
    """Test integration with FrameworkLoader."""

    def test_output_style_initialization_new_version():
        """Test output style initialization for Claude >= 1.0.83."""
        with patch("subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = "Claude 1.0.83"
            mock_run.return_value = mock_result

            # Patch file operations
            with patch("pathlib.Path.exists", return_value=True), patch(
                "pathlib.Path.read_text", return_value="Test content"
            ), patch("pathlib.Path.write_text"), patch("pathlib.Path.mkdir"):
                loader = FrameworkLoader()
                # Force initialization
                loader._initialize_output_style()

                assert loader.output_style_manager is not None
                assert loader.output_style_manager.supports_output_styles() is True

    def test_output_style_injection_old_version():
        """Test output style injection for Claude < 1.0.83."""
        with patch("subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = "Claude 1.0.82"
            mock_run.return_value = mock_result

            # Patch file operations to provide test content
            test_instructions = "# Test Instructions\n\nTest content"
            test_base_pm = "# Base PM\n\nBase PM content"

            with patch("pathlib.Path.exists", return_value=True), patch(
                "pathlib.Path.read_text",
                side_effect=[
                    test_instructions,  # INSTRUCTIONS.md
                    test_base_pm,  # BASE_PM.md
                    "# WORKFLOW",  # WORKFLOW.md
                    "# MEMORY",  # MEMORY.md
                ],
            ), patch("pathlib.Path.glob", return_value=[]):
                loader = FrameworkLoader()
                loader.framework_content["framework_instructions"] = test_instructions
                loader.framework_content["base_pm_instructions"] = test_base_pm
                loader.framework_content["loaded"] = True

                # Get framework instructions
                full_instructions = loader.get_framework_instructions()

                # Check that output style was injected
                if (
                    loader.output_style_manager
                    and loader.output_style_manager.should_inject_content()
                ):
                    assert "Output Style Configuration" in full_instructions

    def test_output_style_not_injected_new_version():
        """Test output style NOT injected for Claude >= 1.0.83."""
        with patch("subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = "Claude 1.0.84"
            mock_run.return_value = mock_result

            # Patch file operations
            test_instructions = "# Test Instructions\n\nTest content"

            with patch("pathlib.Path.exists", return_value=True), patch(
                "pathlib.Path.read_text", return_value=test_instructions
            ), patch("pathlib.Path.glob", return_value=[]), patch(
                "pathlib.Path.write_text"
            ), patch("pathlib.Path.mkdir"):
                loader = FrameworkLoader()
                loader.framework_content["framework_instructions"] = test_instructions
                loader.framework_content["loaded"] = True

                # Get framework instructions
                full_instructions = loader.get_framework_instructions()

                # Check that output style was NOT injected
                assert "Output Style Configuration" not in full_instructions


if __name__ == "__main__":
    # Run tests with pytest if available, otherwise run directly
    try:
        import pytest

        pytest.main([__file__, "-v"])
    except ImportError:
        # Run tests directly
        print("Running tests without pytest...")

        # Test OutputStyleManager
        test_manager = TestOutputStyleManager()
        test_manager.test_version_detection_success()
        print("✓ test_version_detection_success")

        test_manager.test_version_detection_not_found()
        print("✓ test_version_detection_not_found")

        test_manager.test_version_comparison()
        print("✓ test_version_comparison")

        test_manager.test_supports_output_styles()
        print("✓ test_supports_output_styles")

        test_manager.test_extract_output_style_content()
        print("✓ test_extract_output_style_content")

        test_manager.test_get_injectable_content()
        print("✓ test_get_injectable_content")

        test_manager.test_save_output_style()
        print("✓ test_save_output_style")

        test_manager.test_deploy_output_style_success()
        print("✓ test_deploy_output_style_success")

        test_manager.test_deploy_output_style_unsupported_version()
        print("✓ test_deploy_output_style_unsupported_version")

        # Test FrameworkLoader integration
        test_loader = TestFrameworkLoaderIntegration()
        test_loader.test_output_style_initialization_new_version()
        print("✓ test_output_style_initialization_new_version")

        test_loader.test_output_style_injection_old_version()
        print("✓ test_output_style_injection_old_version")

        test_loader.test_output_style_not_injected_new_version()
        print("✓ test_output_style_not_injected_new_version")

        print("\nAll tests passed!")
