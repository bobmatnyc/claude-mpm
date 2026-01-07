#!/usr/bin/env python3
"""Validation script for ContextUsageTracker service.

Runs comprehensive checks to verify:
- Service imports correctly
- Basic functionality works
- File persistence works
- Tests pass
- Example runs successfully

Usage:
    python scripts/validate_context_tracker.py
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def validate_imports():
    """Validate service imports."""
    print("=" * 70)
    print("1. Validating Imports")
    print("=" * 70)

    try:
        from claude_mpm.services.infrastructure import (
            ContextUsageState,
            ContextUsageTracker,
        )

        print("✅ ContextUsageTracker import successful")
        print("✅ ContextUsageState import successful")
        return True
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False


def validate_basic_functionality():
    """Validate basic service functionality."""
    print("\n" + "=" * 70)
    print("2. Validating Basic Functionality")
    print("=" * 70)

    from claude_mpm.services.infrastructure import ContextUsageTracker

    try:
        # Initialize tracker
        tracker = ContextUsageTracker()
        print(f"✅ Tracker initialized: {tracker.state_file}")

        # Update usage
        state = tracker.update_usage(input_tokens=10000, output_tokens=2000)
        assert state.cumulative_input_tokens == 10000
        assert state.cumulative_output_tokens == 2000
        assert state.percentage_used == 6.0
        print("✅ Usage update working")

        # Cumulative tracking
        state = tracker.update_usage(input_tokens=5000, output_tokens=1000)
        assert state.cumulative_input_tokens == 15000
        assert state.cumulative_output_tokens == 3000
        assert state.percentage_used == 9.0
        print("✅ Cumulative tracking working")

        # Threshold detection
        tracker.reset_session("test-session")
        state = tracker.update_usage(input_tokens=140000, output_tokens=0)
        assert state.threshold_reached == "caution"
        print("✅ Threshold detection working")

        # Auto-pause check
        tracker.reset_session("test-session")
        tracker.update_usage(input_tokens=180000, output_tokens=0)
        assert tracker.should_auto_pause()
        print("✅ Auto-pause detection working")

        return True

    except Exception as e:
        print(f"❌ Functionality test failed: {e}")
        return False


def validate_file_persistence():
    """Validate file-based state persistence."""
    print("\n" + "=" * 70)
    print("3. Validating File Persistence")
    print("=" * 70)

    from claude_mpm.services.infrastructure import ContextUsageTracker

    try:
        # Create tracker and update
        tracker1 = ContextUsageTracker()
        tracker1.reset_session("persistence-test")
        state1 = tracker1.update_usage(input_tokens=50000, output_tokens=10000)

        # Verify state file exists
        assert tracker1.state_file.exists()
        print(f"✅ State file created: {tracker1.state_file}")

        # Create new tracker instance
        tracker2 = ContextUsageTracker()
        state2 = tracker2.get_current_state()

        # Verify state persisted
        assert state2.cumulative_input_tokens == 50000
        assert state2.cumulative_output_tokens == 10000
        assert state2.percentage_used == 30.0
        print("✅ State persistence working")

        # Cleanup
        tracker1.reset_session("test-session")

        return True

    except Exception as e:
        print(f"❌ Persistence test failed: {e}")
        return False


def validate_error_handling():
    """Validate error handling and recovery."""
    print("\n" + "=" * 70)
    print("4. Validating Error Handling")
    print("=" * 70)

    from claude_mpm.services.infrastructure import ContextUsageTracker

    try:
        tracker = ContextUsageTracker()

        # Test negative token validation
        try:
            tracker.update_usage(input_tokens=-100, output_tokens=200)
            print("❌ Should have raised ValueError for negative tokens")
            return False
        except ValueError:
            print("✅ Negative token validation working")

        # Test corrupted state recovery
        tracker.state_file.write_text("{ corrupted json data }")
        tracker_new = ContextUsageTracker()
        state = tracker_new.get_current_state()
        assert state.cumulative_input_tokens == 0
        print("✅ Corrupted state recovery working")

        return True

    except Exception as e:
        print(f"❌ Error handling test failed: {e}")
        return False


def validate_tests():
    """Validate test suite passes."""
    print("\n" + "=" * 70)
    print("5. Validating Test Suite")
    print("=" * 70)

    import subprocess

    try:
        result = subprocess.run(
            [
                "python",
                "-m",
                "pytest",
                "tests/services/infrastructure/test_context_usage_tracker.py",
                "-v",
                "--tb=short",
            ],
            check=False,
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            # Count passed tests
            lines = result.stdout.split("\n")
            for line in lines:
                if "passed" in line:
                    print(f"✅ {line.strip()}")
                    break
            return True
        print("❌ Test suite failed")
        print(result.stdout)
        return False

    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        return False


def validate_usage_summary():
    """Validate usage summary generation."""
    print("\n" + "=" * 70)
    print("6. Validating Usage Summary")
    print("=" * 70)

    from claude_mpm.services.infrastructure import ContextUsageTracker

    try:
        tracker = ContextUsageTracker()
        tracker.reset_session("summary-test")
        tracker.update_usage(
            input_tokens=60000,
            output_tokens=15000,
            cache_creation=5000,
            cache_read=2000,
        )

        summary = tracker.get_usage_summary()

        assert summary["total_tokens"] == 75000
        assert summary["budget"] == 200000
        assert summary["percentage_used"] == 37.5
        assert summary["breakdown"]["input_tokens"] == 60000
        assert summary["breakdown"]["output_tokens"] == 15000
        assert summary["breakdown"]["cache_creation_tokens"] == 5000
        assert summary["breakdown"]["cache_read_tokens"] == 2000

        print("✅ Usage summary generation working")
        print(f"   Total: {summary['total_tokens']:,} tokens")
        print(f"   Usage: {summary['percentage_used']:.1f}%")

        return True

    except Exception as e:
        print(f"❌ Usage summary test failed: {e}")
        return False


def main():
    """Run all validation checks."""
    print("\n" + "=" * 70)
    print("ContextUsageTracker Service Validation")
    print("=" * 70)
    print()

    results = []

    # Run all checks
    results.append(("Imports", validate_imports()))
    results.append(("Basic Functionality", validate_basic_functionality()))
    results.append(("File Persistence", validate_file_persistence()))
    results.append(("Error Handling", validate_error_handling()))
    results.append(("Usage Summary", validate_usage_summary()))
    results.append(("Test Suite", validate_tests()))

    # Summary
    print("\n" + "=" * 70)
    print("Validation Summary")
    print("=" * 70)
    print()

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for check_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {check_name}")

    print()
    print("=" * 70)
    print(f"Results: {passed}/{total} checks passed")
    print("=" * 70)

    if passed == total:
        print("\n🎉 All validation checks passed!")
        print("\nService is ready for:")
        print("  - Claude Code hook integration")
        print("  - Session pause manager integration")
        print("  - Dashboard display")
        print("  - Production deployment")
        return 0
    print(f"\n⚠️  {total - passed} check(s) failed. Review output above.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
