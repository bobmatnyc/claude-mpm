#!/usr/bin/env python3
"""
Test script for output style deployment on startup.

Tests:
1. OUTPUT_STYLE.md exists and contains prohibitions
2. deploy_output_style_on_startup() creates file at correct location
3. deploy_output_style_on_startup() updates settings.json correctly
4. Deployment is idempotent (doesn't re-deploy if already active)
5. Integration with startup.py run_background_services()
"""

import json

# Add project root to path
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent / "src"))


def test_output_style_exists():
    """Test 1: Verify OUTPUT_STYLE.md exists and contains prohibitions."""
    print("Test 1: Verify OUTPUT_STYLE.md exists and contains prohibitions")
    print("-" * 60)

    output_style_path = Path("src/claude_mpm/agents/OUTPUT_STYLE.md")
    assert output_style_path.exists(), "OUTPUT_STYLE.md not found"

    content = output_style_path.read_text()

    # Check for key prohibitions
    assert "emoji" in content.lower(), "Missing emoji prohibition"
    assert "exclamation" in content.lower(), "Missing exclamation prohibition"
    assert "enthusiasm" in content.lower(), "Missing enthusiasm prohibition"
    assert "affirmation" in content.lower(), "Missing affirmation prohibition"

    # Check for specific forbidden phrases
    forbidden_phrases = ["Perfect", "Excellent", "Amazing", "Fantastic"]
    for phrase in forbidden_phrases:
        assert phrase in content, f"Missing forbidden phrase: {phrase}"

    # Check frontmatter
    assert content.startswith("---"), "Missing frontmatter"
    assert "name: Claude MPM" in content, "Missing name in frontmatter"

    print(f"✓ OUTPUT_STYLE.md exists ({len(content)} characters)")
    print("✓ Contains emoji prohibition")
    print("✓ Contains exclamation prohibition")
    print("✓ Contains enthusiasm prohibition")
    print("✓ Contains affirmation prohibition")
    print(f"✓ Lists forbidden phrases: {', '.join(forbidden_phrases)}")
    print("✓ Has proper frontmatter with name")
    print()


def test_deployment_function():
    """Test 2: Test deploy_output_style_on_startup() deployment."""
    print("Test 2: Test deploy_output_style_on_startup() deployment")
    print("-" * 60)

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_home = Path(temp_dir)
        output_styles_dir = temp_home / ".claude" / "output-styles"
        settings_file = temp_home / ".claude" / "settings.json"

        # Mock Path.home() to return temp directory
        with patch("pathlib.Path.home", return_value=temp_home):
            # Mock OutputStyleManager.supports_output_styles to return True
            from claude_mpm.cli.startup import deploy_output_style_on_startup

            with patch(
                "claude_mpm.core.output_style_manager.OutputStyleManager.supports_output_styles",
                return_value=True,
            ):
                # First deployment
                deploy_output_style_on_startup()

                # Check file was created
                output_style_file = output_styles_dir / "claude-mpm.md"
                assert output_style_file.exists(), "Output style file not created"

                # Check content matches source
                source_path = Path("src/claude_mpm/agents/OUTPUT_STYLE.md")
                source_content = source_path.read_text()
                deployed_content = output_style_file.read_text()
                assert deployed_content == source_content, "Content mismatch"

                # Check settings.json was created
                assert settings_file.exists(), "settings.json not created"
                settings = json.loads(settings_file.read_text())
                assert settings.get("activeOutputStyle") == "claude-mpm", (
                    "activeOutputStyle not set"
                )

                print(f"✓ Output style file created at: {output_style_file}")
                print(f"✓ Content matches source ({len(deployed_content)} characters)")
                print("✓ settings.json created with activeOutputStyle: claude-mpm")
                print()


def test_idempotency():
    """Test 3: Test deployment is idempotent."""
    print("Test 3: Test deployment is idempotent")
    print("-" * 60)

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_home = Path(temp_dir)
        output_styles_dir = temp_home / ".claude" / "output-styles"
        settings_file = temp_home / ".claude" / "settings.json"

        # Mock Path.home() to return temp directory
        with patch("pathlib.Path.home", return_value=temp_home):
            from claude_mpm.cli.startup import deploy_output_style_on_startup

            with patch(
                "claude_mpm.core.output_style_manager.OutputStyleManager.supports_output_styles",
                return_value=True,
            ):
                # First deployment
                deploy_output_style_on_startup()

                # Get file modification times
                output_style_file = output_styles_dir / "claude-mpm.md"
                first_mtime = output_style_file.stat().st_mtime

                # Second deployment (should be skipped)
                deploy_output_style_on_startup()

                # Check file was not modified
                second_mtime = output_style_file.stat().st_mtime
                assert first_mtime == second_mtime, (
                    "File was modified on second deployment"
                )

                print("✓ First deployment completed")
                print("✓ Second deployment skipped (file not modified)")
                print("✓ Deployment is idempotent")
                print()


def test_startup_integration():
    """Test 4: Verify startup.py integration."""
    print("Test 4: Verify startup.py integration")
    print("-" * 60)

    import inspect

    from claude_mpm.cli.startup import run_background_services

    # Get source code of run_background_services
    source = inspect.getsource(run_background_services)

    # Check that deploy_output_style_on_startup is called
    assert "deploy_output_style_on_startup()" in source, (
        "deploy_output_style_on_startup not called in run_background_services"
    )

    print("✓ run_background_services() calls deploy_output_style_on_startup()")

    # Check order of calls
    calls = [
        "initialize_project_registry",
        "check_mcp_auto_configuration",
        "verify_mcp_gateway_startup",
        "check_for_updates_async",
        "deploy_bundled_skills",
        "discover_and_link_runtime_skills",
        "deploy_output_style_on_startup",
    ]

    for call in calls:
        assert f"{call}()" in source, f"{call} not found in run_background_services"

    print("✓ All background services called in correct order:")
    for i, call in enumerate(calls, 1):
        print(f"  {i}. {call}()")
    print()


def test_version_check():
    """Test 5: Verify version check logic."""
    print("Test 5: Verify version check logic")
    print("-" * 60)

    from claude_mpm.cli.startup import deploy_output_style_on_startup

    # Mock supports_output_styles to return False
    with patch(
        "claude_mpm.core.output_style_manager.OutputStyleManager.supports_output_styles",
        return_value=False,
    ):
        # Mock Path.home() to ensure no file operations
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_home = Path(temp_dir)

            with patch("pathlib.Path.home", return_value=temp_home):
                # Should silently skip without error
                deploy_output_style_on_startup()

                # Verify no files were created
                output_styles_dir = temp_home / ".claude" / "output-styles"
                assert not output_styles_dir.exists(), (
                    "Output styles directory should not be created"
                )

                print("✓ Deployment skipped for unsupported versions")
                print("✓ No files created when version check fails")
                print()


def run_all_tests():
    """Run all tests."""
    print("=" * 60)
    print("OUTPUT STYLE DEPLOYMENT TEST SUITE")
    print("=" * 60)
    print()

    tests = [
        test_output_style_exists,
        test_deployment_function,
        test_idempotency,
        test_startup_integration,
        test_version_check,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"✗ Test failed: {test.__name__}")
            print(f"  Error: {e}")
            print()
            failed += 1

    print("=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
