#!/usr/bin/env python3
"""Comprehensive test suite for output style installer fix.

Tests that the deploy_output_style method:
1. Always activates the claude-mpm style regardless of existing state
2. Replaces any user customizations with system version
3. Always sets activeOutputStyle to "claude-mpm" in settings.json
4. Works correctly in all scenarios (fresh, existing, corrupted)
"""

import json
import logging
import os
import shutil
import sys
from pathlib import Path
from unittest.mock import patch

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.core.output_style_manager import OutputStyleManager

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class OutputStyleTester:
    """Comprehensive tester for output style installer functionality."""

    def __init__(self):
        """Initialize the tester."""
        self.test_results = []
        self.failed_tests = []
        self.temp_dir = None
        self.original_home = Path.home()

    def setup_test_environment(self):
        """Set up isolated test environment."""
        # Create temporary directory for testing
        self.temp_dir = Path(tmp_path)
        logger.info(f"Created test environment: {self.temp_dir}")

        # Mock Path.home() to point to our temp directory
        self.home_patcher = patch("pathlib.Path.home")
        mock_home = self.home_patcher.start()
        mock_home.return_value = self.temp_dir

        return self.temp_dir

    def cleanup_test_environment(self):
        """Clean up test environment."""
        if hasattr(self, "home_patcher"):
            self.home_patcher.stop()

        if self.temp_dir and self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
            logger.info(f"Cleaned up test environment: {self.temp_dir}")

    def create_manager_with_mock_version(
        self, version: str = "1.0.85"
    ) -> OutputStyleManager:
        """Create output style manager with mocked Claude version."""
        manager = OutputStyleManager()
        manager.claude_version = version
        return manager

    def run_test(self, test_name: str, test_func):
        """Run a single test and record results."""
        logger.info(f"\n{'=' * 60}")
        logger.info(f"Running Test: {test_name}")
        logger.info(f"{'=' * 60}")

        try:
            result = test_func()
            if result:
                logger.info(f"✓ PASS: {test_name}")
                self.test_results.append((test_name, "PASS", ""))
            else:
                logger.error(f"✗ FAIL: {test_name}")
                self.test_results.append((test_name, "FAIL", "Test returned False"))
                self.failed_tests.append(test_name)
        except Exception as e:
            logger.error(f"✗ ERROR: {test_name} - {e!s}")
            self.test_results.append((test_name, "ERROR", str(e)))
            self.failed_tests.append(test_name)

    def test_fresh_installation(self) -> bool:
        """Test scenario 1: Fresh installation with no existing style."""
        logger.info("Testing fresh installation (no existing files)")

        manager = self.create_manager_with_mock_version("1.0.85")
        test_content = "---\nname: Claude MPM Test\n---\nTest content"

        # Verify no existing files
        claude_dir = self.temp_dir / ".claude"
        output_styles_dir = claude_dir / "output-styles"
        style_file = output_styles_dir / "claude-mpm.md"
        settings_file = claude_dir / "settings.json"

        assert not claude_dir.exists(), "Claude directory should not exist initially"

        # Deploy output style
        result = manager.deploy_output_style(test_content)

        # Verify deployment
        assert result, "Deployment should succeed"
        assert style_file.exists(), "claude-mpm.md should be created"
        assert style_file.read_text() == test_content, "Style file content should match"
        assert settings_file.exists(), "settings.json should be created"

        # Check settings content
        settings = json.loads(settings_file.read_text())
        assert settings.get("activeOutputStyle") == "claude-mpm", (
            "activeOutputStyle should be set to claude-mpm"
        )

        logger.info("  ✓ Style file created successfully")
        logger.info("  ✓ Settings file created with correct activeOutputStyle")
        return True

    def test_existing_style_replacement(self) -> bool:
        """Test scenario 2: Replace existing claude-mpm.md file."""
        logger.info("Testing replacement of existing style file")

        manager = self.create_manager_with_mock_version("1.0.85")

        # Create existing files
        claude_dir = self.temp_dir / ".claude"
        output_styles_dir = claude_dir / "output-styles"
        style_file = output_styles_dir / "claude-mpm.md"
        settings_file = claude_dir / "settings.json"

        output_styles_dir.mkdir(parents=True, exist_ok=True)

        # Create existing style file with different content
        old_content = "---\nname: Old Style\n---\nOld content"
        style_file.write_text(old_content)

        # Create existing settings with different active style
        old_settings = {"activeOutputStyle": "some-other-style"}
        settings_file.write_text(json.dumps(old_settings))

        # Deploy new content
        new_content = "---\nname: Claude MPM New\n---\nNew content"
        result = manager.deploy_output_style(new_content)

        # Verify replacement
        assert result, "Deployment should succeed"
        assert style_file.exists(), "claude-mpm.md should still exist"

        actual_content = style_file.read_text()
        assert actual_content == new_content, (
            f"Content should be replaced. Expected: {new_content}, Got: {actual_content}"
        )

        # Check settings were updated
        settings = json.loads(settings_file.read_text())
        assert settings.get("activeOutputStyle") == "claude-mpm", (
            "activeOutputStyle should be updated to claude-mpm"
        )

        logger.info("  ✓ Existing style file replaced successfully")
        logger.info("  ✓ Settings updated to activate claude-mpm style")
        return True

    def test_settings_activation_from_different_style(self) -> bool:
        """Test scenario 3: Change activeOutputStyle from different value."""
        logger.info("Testing activation when different style is currently active")

        manager = self.create_manager_with_mock_version("1.0.85")

        # Create settings with different active style
        claude_dir = self.temp_dir / ".claude"
        settings_file = claude_dir / "settings.json"
        claude_dir.mkdir(parents=True, exist_ok=True)

        existing_settings = {
            "activeOutputStyle": "user-custom-style",
            "otherSetting": "preserve-me",
            "theme": "dark",
        }
        settings_file.write_text(json.dumps(existing_settings, indent=2))

        # Deploy output style
        test_content = "---\nname: Claude MPM\n---\nTest content"
        result = manager.deploy_output_style(test_content)

        # Verify deployment and settings update
        assert result, "Deployment should succeed"

        settings = json.loads(settings_file.read_text())
        assert settings.get("activeOutputStyle") == "claude-mpm", (
            "activeOutputStyle should be changed to claude-mpm"
        )
        assert settings.get("otherSetting") == "preserve-me", (
            "Other settings should be preserved"
        )
        assert settings.get("theme") == "dark", "Existing settings should be preserved"

        logger.info(
            "  ✓ activeOutputStyle changed from user-custom-style to claude-mpm"
        )
        logger.info("  ✓ Other settings preserved correctly")
        return True

    def test_missing_settings_file(self) -> bool:
        """Test scenario 4: No existing settings.json file."""
        logger.info("Testing creation of settings.json when missing")

        manager = self.create_manager_with_mock_version("1.0.85")

        # Ensure settings file doesn't exist
        claude_dir = self.temp_dir / ".claude"
        settings_file = claude_dir / "settings.json"

        assert not settings_file.exists(), "Settings file should not exist initially"

        # Deploy output style
        test_content = "---\nname: Claude MPM\n---\nTest content"
        result = manager.deploy_output_style(test_content)

        # Verify settings file creation
        assert result, "Deployment should succeed"
        assert settings_file.exists(), "settings.json should be created"

        settings = json.loads(settings_file.read_text())
        assert settings.get("activeOutputStyle") == "claude-mpm", (
            "activeOutputStyle should be set"
        )

        logger.info("  ✓ settings.json created successfully")
        logger.info("  ✓ activeOutputStyle set correctly in new file")
        return True

    def test_multiple_runs_idempotent(self) -> bool:
        """Test scenario 5: Multiple runs should be idempotent."""
        logger.info("Testing idempotent behavior across multiple runs")

        manager = self.create_manager_with_mock_version("1.0.85")
        test_content = "---\nname: Claude MPM\n---\nTest content"

        # First deployment
        result1 = manager.deploy_output_style(test_content)
        assert result1, "First deployment should succeed"

        # Get initial state
        style_file = self.temp_dir / ".claude" / "output-styles" / "claude-mpm.md"
        settings_file = self.temp_dir / ".claude" / "settings.json"

        initial_content = style_file.read_text()
        initial_settings = json.loads(settings_file.read_text())
        style_file.stat().st_mtime

        # Second deployment (should be idempotent)
        result2 = manager.deploy_output_style(test_content)
        assert result2, "Second deployment should succeed"

        # Verify content is the same
        second_content = style_file.read_text()
        second_settings = json.loads(settings_file.read_text())

        assert second_content == initial_content, "Content should remain the same"
        assert second_settings == initial_settings, "Settings should remain the same"
        assert second_settings.get("activeOutputStyle") == "claude-mpm", (
            "activeOutputStyle should still be claude-mpm"
        )

        # Third deployment with different content
        new_content = "---\nname: Claude MPM Updated\n---\nUpdated content"
        result3 = manager.deploy_output_style(new_content)
        assert result3, "Third deployment should succeed"

        # Verify content was updated but settings remain correct
        third_content = style_file.read_text()
        third_settings = json.loads(settings_file.read_text())

        assert third_content == new_content, "Content should be updated"
        assert third_settings.get("activeOutputStyle") == "claude-mpm", (
            "activeOutputStyle should still be claude-mpm"
        )

        logger.info("  ✓ Multiple deployments work correctly")
        logger.info("  ✓ Content updates properly on subsequent runs")
        logger.info("  ✓ Settings remain consistent across runs")
        return True

    def test_corrupted_settings_file(self) -> bool:
        """Test scenario 6: Corrupted settings.json file."""
        logger.info("Testing handling of corrupted settings.json")

        manager = self.create_manager_with_mock_version("1.0.85")

        # Create corrupted settings file
        claude_dir = self.temp_dir / ".claude"
        settings_file = claude_dir / "settings.json"
        claude_dir.mkdir(parents=True, exist_ok=True)

        # Write invalid JSON
        settings_file.write_text("{ invalid json content }")

        # Deploy output style
        test_content = "---\nname: Claude MPM\n---\nTest content"
        result = manager.deploy_output_style(test_content)

        # Verify deployment still succeeds
        assert result, "Deployment should succeed despite corrupted settings"

        # Verify settings were recreated correctly
        assert settings_file.exists(), "settings.json should exist"

        settings = json.loads(settings_file.read_text())
        assert settings.get("activeOutputStyle") == "claude-mpm", (
            "activeOutputStyle should be set correctly"
        )

        logger.info("  ✓ Corrupted settings.json handled gracefully")
        logger.info("  ✓ New valid settings.json created")
        return True

    def test_version_support_check(self) -> bool:
        """Test version support checking logic."""
        logger.info("Testing Claude version support detection")

        # Test supported version
        manager = self.create_manager_with_mock_version("1.0.85")
        assert manager.supports_output_styles(), (
            "Version 1.0.85 should support output styles"
        )

        # Test minimum supported version
        manager = self.create_manager_with_mock_version("1.0.83")
        assert manager.supports_output_styles(), (
            "Version 1.0.83 should support output styles"
        )

        # Test unsupported version
        manager = self.create_manager_with_mock_version("1.0.82")
        assert not manager.supports_output_styles(), (
            "Version 1.0.82 should not support output styles"
        )

        # Test no version detected
        manager = self.create_manager_with_mock_version(None)
        assert not manager.supports_output_styles(), (
            "No version should not support output styles"
        )

        # Test deployment rejection for unsupported version
        manager = self.create_manager_with_mock_version("1.0.82")
        result = manager.deploy_output_style("test content")
        assert not result, "Deployment should fail for unsupported version"

        logger.info("  ✓ Version support detection works correctly")
        logger.info("  ✓ Deployment properly rejected for unsupported versions")
        return True

    def test_directory_creation(self) -> bool:
        """Test that required directories are created."""
        logger.info("Testing directory creation during deployment")

        manager = self.create_manager_with_mock_version("1.0.85")

        # Ensure directories don't exist
        claude_dir = self.temp_dir / ".claude"
        output_styles_dir = claude_dir / "output-styles"

        assert not claude_dir.exists(), "Claude directory should not exist initially"

        # Deploy output style
        test_content = "---\nname: Claude MPM\n---\nTest content"
        result = manager.deploy_output_style(test_content)

        # Verify directories were created
        assert result, "Deployment should succeed"
        assert claude_dir.exists(), ".claude directory should be created"
        assert claude_dir.is_dir(), ".claude should be a directory"
        assert output_styles_dir.exists(), "output-styles directory should be created"
        assert output_styles_dir.is_dir(), "output-styles should be a directory"

        # Verify file permissions (should be readable/writable)
        style_file = output_styles_dir / "claude-mpm.md"
        assert style_file.exists(), "Style file should exist"
        assert os.access(style_file, os.R_OK), "Style file should be readable"
        assert os.access(style_file, os.W_OK), "Style file should be writable"

        logger.info("  ✓ Required directories created successfully")
        logger.info("  ✓ File permissions set correctly")
        return True

    def run_all_tests(self) -> bool:
        """Run all test scenarios."""
        logger.info("\n" + "=" * 80)
        logger.info("COMPREHENSIVE OUTPUT STYLE INSTALLER TEST SUITE")
        logger.info("Testing the fix for always setting claude-mpm style")
        logger.info("=" * 80)

        try:
            # Set up test environment
            self.setup_test_environment()

            # Run all tests
            test_cases = [
                ("Fresh Installation", self.test_fresh_installation),
                ("Existing Style Replacement", self.test_existing_style_replacement),
                (
                    "Settings Activation from Different Style",
                    self.test_settings_activation_from_different_style,
                ),
                ("Missing Settings File", self.test_missing_settings_file),
                ("Multiple Runs (Idempotent)", self.test_multiple_runs_idempotent),
                ("Corrupted Settings File", self.test_corrupted_settings_file),
                ("Version Support Check", self.test_version_support_check),
                ("Directory Creation", self.test_directory_creation),
            ]

            for test_name, test_func in test_cases:
                # Clean the temp directory between tests
                claude_dir = self.temp_dir / ".claude"
                if claude_dir.exists():
                    shutil.rmtree(claude_dir)

                self.run_test(test_name, test_func)

        finally:
            # Always clean up
            self.cleanup_test_environment()

        # Print summary
        self.print_test_summary()

        # Return True if all tests passed
        return len(self.failed_tests) == 0

    def print_test_summary(self):
        """Print comprehensive test results summary."""
        logger.info("\n" + "=" * 80)
        logger.info("TEST RESULTS SUMMARY")
        logger.info("=" * 80)

        total_tests = len(self.test_results)
        passed_tests = sum(1 for _, status, _ in self.test_results if status == "PASS")
        failed_tests = sum(
            1 for _, status, _ in self.test_results if status in ["FAIL", "ERROR"]
        )

        logger.info(f"Total Tests: {total_tests}")
        logger.info(f"Passed: {passed_tests}")
        logger.info(f"Failed: {failed_tests}")
        logger.info(f"Success Rate: {(passed_tests / total_tests) * 100:.1f}%")

        if self.failed_tests:
            logger.info("\nFAILED TESTS:")
            for test_name in self.failed_tests:
                logger.info(f"  ✗ {test_name}")
        else:
            logger.info("\n🎉 ALL TESTS PASSED! 🎉")

        logger.info("\nDETAILED RESULTS:")
        for test_name, status, error in self.test_results:
            if status == "PASS":
                logger.info(f"  ✓ {test_name}")
            else:
                logger.info(f"  ✗ {test_name} ({status})")
                if error:
                    logger.info(f"    Error: {error}")

        logger.info("=" * 80)


def main():
    """Main test execution."""
    tester = OutputStyleTester()
    success = tester.run_all_tests()

    if success:
        logger.info("\n🔴 QA SIGN-OFF: PASS 🔴")
        logger.info(
            "The output style installer fix works correctly in all tested scenarios:"
        )
        logger.info("- Always sets activeOutputStyle to 'claude-mpm'")
        logger.info("- Replaces existing user customizations with system version")
        logger.info(
            "- Handles fresh installations, existing files, and corrupted settings"
        )
        logger.info("- Works idempotently across multiple runs")
        logger.info("- Creates required directories and files with proper permissions")
        logger.info("- Correctly rejects deployment for unsupported Claude versions")
        sys.exit(0)
    else:
        logger.error("\n🔴 QA SIGN-OFF: FAIL 🔴")
        logger.error("The output style installer has issues that need to be addressed.")
        logger.error("See test results above for specific failures.")
        sys.exit(1)


if __name__ == "__main__":
    main()
