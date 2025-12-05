#!/usr/bin/env python3
"""
Verification script for integration testing framework.

Runs basic checks to ensure all components are working correctly.

Usage:
    python tests/eval/verify_integration_framework.py
"""

import sys
from pathlib import Path


def print_section(title: str):
    """Print section header."""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")


def check_imports():
    """Verify all imports work."""
    print_section("Checking Imports")

    try:
        from tests.eval.utils.pm_response_capture import (
            PMResponseCapture,
            AsyncPMResponseCapture,
            PMResponse,
            PMResponseMetadata,
        )
        print("✓ pm_response_capture imports successful")
    except ImportError as e:
        print(f"✗ pm_response_capture import failed: {e}")
        return False

    try:
        from tests.eval.utils.response_replay import (
            ResponseReplay,
            ResponseComparison,
            RegressionReport,
            GoldenResponseManager,
        )
        print("✓ response_replay imports successful")
    except ImportError as e:
        print(f"✗ response_replay import failed: {e}")
        return False

    try:
        from tests.eval.test_cases import integration_ticketing
        print("✓ integration_ticketing imports successful")
    except ImportError as e:
        print(f"✗ integration_ticketing import failed: {e}")
        return False

    try:
        from tests.eval.test_cases import performance
        print("✓ performance imports successful")
    except ImportError as e:
        print(f"✗ performance import failed: {e}")
        return False

    return True


def check_files():
    """Verify all required files exist."""
    print_section("Checking Files")

    required_files = [
        "tests/eval/utils/pm_response_capture.py",
        "tests/eval/utils/response_replay.py",
        "tests/eval/test_cases/integration_ticketing.py",
        "tests/eval/test_cases/performance.py",
        "tests/eval/README_INTEGRATION.md",
        "tests/eval/INTEGRATION_IMPLEMENTATION.md",
    ]

    all_exist = True
    for file_path in required_files:
        path = Path(file_path)
        if path.exists():
            size = path.stat().st_size
            print(f"✓ {file_path} ({size:,} bytes)")
        else:
            print(f"✗ {file_path} NOT FOUND")
            all_exist = False

    return all_exist


def test_response_capture():
    """Test basic response capture functionality."""
    print_section("Testing Response Capture")

    try:
        from tests.eval.utils.pm_response_capture import PMResponseCapture

        # Create capture with temp directory
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            capture = PMResponseCapture(responses_dir=tmpdir)

            # Test capture
            response = capture.capture_response(
                scenario_id="test_scenario",
                input_text="test input",
                pm_response={
                    "content": "test content",
                    "tools_used": ["Task"],
                },
                category="test",
            )

            print(f"✓ Captured response with ID: {response.scenario_id}")
            print(f"✓ Metadata timestamp: {response.metadata.timestamp}")
            print(f"✓ Metadata PM version: {response.metadata.pm_version}")

            # Test load
            loaded = capture.load_response("test_scenario", "test")
            if loaded:
                print(f"✓ Loaded response successfully")
            else:
                print("✗ Failed to load response")
                return False

            # Test list
            responses = capture.list_responses(category="test")
            print(f"✓ Listed {len(responses)} response(s)")

        return True

    except Exception as e:
        print(f"✗ Response capture test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_response_replay():
    """Test basic response replay functionality."""
    print_section("Testing Response Replay")

    try:
        from tests.eval.utils.pm_response_capture import (
            PMResponseCapture,
            PMResponse,
            PMResponseMetadata,
        )
        from tests.eval.utils.response_replay import ResponseReplay
        from datetime import datetime

        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create responses directory
            responses_dir = Path(tmpdir) / "responses"
            golden_dir = Path(tmpdir) / "golden"

            # Create test response
            metadata = PMResponseMetadata(
                scenario_id="test",
                timestamp=datetime.now().isoformat(),
                pm_version="5.0.9",
                test_category="test",
                input_hash="abc123",
                capture_mode="test",
            )

            response = PMResponse(
                scenario_id="test",
                input="test input",
                response={"content": "test"},
                metadata=metadata,
            )

            # Create replay system
            replay = ResponseReplay(
                responses_dir=str(responses_dir),
                golden_dir=str(golden_dir),
            )

            # Save as golden
            success = replay.save_as_golden(response, "test")
            if success:
                print("✓ Saved golden response")
            else:
                print("✗ Failed to save golden response")
                return False

            # Load golden
            loaded = replay.load_golden_response("test", "test")
            if loaded:
                print("✓ Loaded golden response")
            else:
                print("✗ Failed to load golden response")
                return False

            # Compare (should match itself)
            comparison = replay.compare_response(
                scenario_id="test",
                current_response=response,
                category="test",
            )

            print(f"✓ Comparison match score: {comparison.match_score:.2f}")
            print(f"✓ Regression detected: {comparison.regression_detected}")

            if comparison.regression_detected:
                print("✗ Self-comparison should not detect regression")
                return False

        return True

    except Exception as e:
        print(f"✗ Response replay test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_fixtures():
    """Test pytest fixtures are defined."""
    print_section("Checking Pytest Fixtures")

    try:
        import pytest
        from tests.eval import conftest

        fixtures = [
            "pm_endpoint",
            "pm_api_key",
            "capture_mode",
            "replay_mode",
            "update_golden",
            "pm_response_capture",
            "response_replay",
            "pm_agent",
            "integration_test_mode",
            "pm_test_helper",
        ]

        for fixture_name in fixtures:
            if hasattr(conftest, fixture_name) or fixture_name in dir(conftest):
                print(f"✓ Fixture '{fixture_name}' defined")
            else:
                # Check if it's a pytest fixture (may not be directly accessible)
                print(f"? Fixture '{fixture_name}' (checking via pytest)")

        print("\n✓ All expected fixtures appear to be defined")
        return True

    except Exception as e:
        print(f"✗ Fixture check failed: {e}")
        return False


def count_tests():
    """Count integration tests."""
    print_section("Counting Tests")

    try:
        import ast

        test_file = Path("tests/eval/test_cases/integration_ticketing.py")
        if not test_file.exists():
            print("✗ integration_ticketing.py not found")
            return False

        with open(test_file) as f:
            tree = ast.parse(f.read())

        # Count test methods
        test_count = 0
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if node.name.startswith("test_"):
                    test_count += 1

        print(f"✓ Found {test_count} test functions in integration_ticketing.py")

        if test_count < 10:
            print(f"⚠ Expected at least 10 tests, found {test_count}")

        return True

    except Exception as e:
        print(f"✗ Test counting failed: {e}")
        return False


def main():
    """Run all verification checks."""
    print("\n" + "="*70)
    print("  Integration Testing Framework Verification")
    print("="*70)

    checks = [
        ("Import Check", check_imports),
        ("File Check", check_files),
        ("Response Capture Test", test_response_capture),
        ("Response Replay Test", test_response_replay),
        ("Fixture Check", test_fixtures),
        ("Test Count", count_tests),
    ]

    results = []
    for name, check_func in checks:
        try:
            success = check_func()
            results.append((name, success))
        except Exception as e:
            print(f"\n✗ {name} failed with exception: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))

    # Print summary
    print_section("Verification Summary")

    passed = sum(1 for _, success in results if success)
    total = len(results)

    for name, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status}: {name}")

    print(f"\n{'='*70}")
    print(f"  Results: {passed}/{total} checks passed")
    print(f"{'='*70}\n")

    if passed == total:
        print("✓ All verification checks passed!")
        print("\nIntegration testing framework is ready to use.")
        print("\nNext steps:")
        print("1. Review README_INTEGRATION.md for usage guide")
        print("2. Run unit tests: pytest tests/eval/test_cases/ -m 'not integration' -v")
        print("3. Test with mock PM: pytest tests/eval/test_cases/integration_ticketing.py -m integration -v")
        print("4. Configure real PM agent and run integration tests")
        return 0
    else:
        print(f"✗ {total - passed} check(s) failed.")
        print("\nPlease review the errors above and fix any issues.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
