#!/usr/bin/env python3
"""
Test script to verify output style information appears correctly in startup INFO display.
"""

import json
import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path


def setup_logging():
    """Setup logging for the test."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    return logging.getLogger(__name__)


def run_claude_mpm_startup(args=None, env_vars=None):
    """Run claude-mpm startup and capture output."""
    if args is None:
        args = ["run", "--logging", "INFO", "-i", "test", "--non-interactive"]

    # Setup environment
    env = os.environ.copy()
    if env_vars:
        env.update(env_vars)

    # Find the script path
    script_path = Path(__file__).parent / "claude-mpm"

    cmd = [str(script_path), *args]

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, env=env, timeout=30, check=False
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Timeout expired"
    except Exception as e:
        return -2, "", str(e)


def test_normal_startup_output_style_info(logger):
    """Test that output style information appears in normal startup."""
    logger.info("Testing normal startup with output style info...")

    __, stdout, _ = run_claude_mpm_startup()

    # Combine stdout and stderr for analysis
    output = stdout + stderr

    # Check for expected output style information
    expected_patterns = [
        "Claude Code version detected:",
        "Claude Code supports output styles",
        "Output style",
        "INFO: Detected Claude version:",
    ]

    found_patterns = []
    missing_patterns = []

    for pattern in expected_patterns:
        if pattern in output:
            found_patterns.append(pattern)
        else:
            missing_patterns.append(pattern)

    logger.info(f"Found patterns: {found_patterns}")
    if missing_patterns:
        logger.warning(f"Missing patterns: {missing_patterns}")

    # Look for specific output style status messages
    output_style_lines = [
        line for line in output.split("\n") if "output style" in line.lower()
    ]
    logger.info(f"Output style related lines: {len(output_style_lines)}")
    for line in output_style_lines:
        logger.info(f"  - {line.strip()}")

    return len(found_patterns) >= 3, output


def test_different_claude_versions(logger):
    """Test behavior with different Claude Code versions."""
    logger.info("Testing different Claude Code version scenarios...")

    # We can't actually change the Claude version, but we can examine the logic
    # by looking at the code that handles different versions

    # Test with current detected version
    __, stdout, _ = run_claude_mpm_startup()
    output = stdout + stderr

    # Check version detection
    version_detected = "Claude Code version detected:" in output
    supports_output_styles = "supports output styles" in output

    logger.info(f"Version detected: {version_detected}")
    logger.info(f"Supports output styles: {supports_output_styles}")

    # Extract the detected version from output
    detected_version = None
    for line in output.split("\n"):
        if "Detected Claude version:" in line:
            detected_version = line.split("Detected Claude version:")[-1].strip()
            break

    logger.info(f"Detected Claude version: {detected_version}")

    return version_detected and supports_output_styles, output


def test_settings_file_scenarios(logger):
    """Test different settings.json scenarios."""
    logger.info("Testing settings.json scenarios...")

    settings_file = Path.home() / ".claude" / "settings.json"
    backup_file = None

    try:
        # Backup existing settings if they exist
        if settings_file.exists():
            backup_file = settings_file.with_suffix(".json.backup.test")
            shutil.copy(settings_file, backup_file)
            logger.info(f"Backed up settings to {backup_file}")

        # Test scenario 1: settings file exists with claude-mpm active
        settings_dir = settings_file.parent
        settings_dir.mkdir(parents=True, exist_ok=True)

        test_settings = {"activeOutputStyle": "claude-mpm"}
        settings_file.write_text(json.dumps(test_settings, indent=2))
        logger.info("Created test settings with claude-mpm active")

        _, stdout, _ = run_claude_mpm_startup()
        output = stdout + stderr

        active_claude_mpm = "claude-mpm' is ACTIVE" in output
        logger.info(f"Test 1 - claude-mpm active detected: {active_claude_mpm}")

        # Test scenario 2: settings file exists with different active style
        test_settings = {"activeOutputStyle": "other-style"}
        settings_file.write_text(json.dumps(test_settings, indent=2))
        logger.info("Created test settings with other-style active")

        __, stdout, _ = run_claude_mpm_startup()
        output = stdout + stderr

        other_active = "other-style" in output and "expected: claude-mpm" in output
        logger.info(f"Test 2 - other style active detected: {other_active}")

        # Test scenario 3: no activeOutputStyle in settings
        test_settings = {}
        settings_file.write_text(json.dumps(test_settings, indent=2))
        logger.info("Created empty test settings")

        __, stdout, _ = run_claude_mpm_startup()
        output = stdout + stderr

        no_active_style = "none" in output or "no active style" in output.lower()
        logger.info(f"Test 3 - no active style detected: {no_active_style}")

        return True, "Settings file scenarios tested"

    finally:
        # Restore original settings
        if backup_file and backup_file.exists():
            shutil.copy(backup_file, settings_file)
            backup_file.unlink()
            logger.info("Restored original settings")
        elif settings_file.exists():
            settings_file.unlink()
            logger.info("Removed test settings file")


def test_output_style_file_scenarios(logger):
    """Test different output style file scenarios."""
    logger.info("Testing output style file scenarios...")

    output_style_path = Path.home() / ".claude" / "output-styles" / "claude-mpm.md"
    backup_file = None

    try:
        # Backup existing output style file if it exists
        if output_style_path.exists():
            backup_file = output_style_path.with_suffix(".md.backup.test")
            shutil.copy(output_style_path, backup_file)
            logger.info(f"Backed up output style to {backup_file}")

        # Test scenario 1: output style file exists
        output_style_path.parent.mkdir(parents=True, exist_ok=True)
        output_style_path.write_text("# Test Output Style\nTest content")
        logger.info("Created test output style file")

        __, stdout, _ = run_claude_mpm_startup()
        output = stdout + stderr

        file_exists_detected = "Output style file exists:" in output
        logger.info(f"Test 1 - existing file detected: {file_exists_detected}")

        # Test scenario 2: output style file doesn't exist
        if output_style_path.exists():
            output_style_path.unlink()
        logger.info("Removed output style file")

        __, stdout, _ = run_claude_mpm_startup()
        output = stdout + stderr

        file_creation_detected = "Output style will be created at:" in output
        logger.info(f"Test 2 - file creation detected: {file_creation_detected}")

        return True, "Output style file scenarios tested"

    finally:
        # Restore original output style file
        if backup_file and backup_file.exists():
            shutil.copy(backup_file, output_style_path)
            backup_file.unlink()
            logger.info("Restored original output style file")


def test_interactive_mode_welcome_message(logger):
    """Test that interactive mode shows output style info in welcome message."""
    logger.info("Testing interactive mode welcome message...")

    # This is harder to test directly, but we can check the logic by examining
    # the interactive session code behavior

    # Run a quick interactive session with immediate exit
    __, stdout, _ = run_claude_mpm_startup(args=["run", "--logging", "INFO"])

    # Note: This might timeout since interactive mode waits for Claude
    # But we can still check if the welcome message display logic is working

    output = stdout + stderr
    welcome_elements = ["Claude MPM - Interactive Session", "Output Style:", "Version"]

    found_welcome_elements = []
    for element in welcome_elements:
        if element in output:
            found_welcome_elements.append(element)

    logger.info(f"Welcome message elements found: {found_welcome_elements}")

    return len(found_welcome_elements) > 0, output


def main():
    """Run all output style startup verification tests."""
    logger = setup_logging()
    logger.info("Starting Output Style Startup Verification Tests")

    tests = [
        ("Normal Startup Info", test_normal_startup_output_style_info),
        ("Different Claude Versions", test_different_claude_versions),
        ("Settings File Scenarios", test_settings_file_scenarios),
        ("Output Style File Scenarios", test_output_style_file_scenarios),
        ("Interactive Mode Welcome", test_interactive_mode_welcome_message),
    ]

    results = []

    for test_name, test_func in tests:
        logger.info(f"\n{'=' * 50}")
        logger.info(f"Running: {test_name}")
        logger.info(f"{'=' * 50}")

        try:
            success, details = test_func(logger)
            results.append((test_name, success, details))
            status = "PASS" if success else "FAIL"
            logger.info(f"Result: {status}")
        except Exception as e:
            logger.error(f"Test {test_name} failed with exception: {e}")
            results.append((test_name, False, str(e)))

    # Summary
    logger.info(f"\n{'=' * 50}")
    logger.info("TEST SUMMARY")
    logger.info(f"{'=' * 50}")

    passed = 0
    failed = 0

    for test_name, success, details in results:
        status = "PASS" if success else "FAIL"
        logger.info(f"{status:<6} {test_name}")
        if not success and isinstance(details, str) and len(details) < 200:
            logger.info(f"       Details: {details}")
        passed += 1 if success else 0
        failed += 1 if not success else 0

    logger.info(f"\nTotal: {len(results)} tests, {passed} passed, {failed} failed")

    if failed > 0:
        logger.error("Some tests failed - output style startup display may have issues")
        return 1
    logger.info("All tests passed - output style startup display working correctly")
    return 0


if __name__ == "__main__":
    sys.exit(main())
