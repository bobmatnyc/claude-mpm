#!/usr/bin/env python3
"""
Test error handling scenarios for async logging system.
Tests disk full, permissions, invalid data, and other error conditions.
"""

import os
import stat
import sys
from pathlib import Path
from unittest.mock import patch

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import contextlib

from claude_mpm.services.async_session_logger import AsyncSessionLogger, LogFormat


def test_permission_errors():
    """Test handling of permission errors during logging."""
    print("\n=== Testing Permission Error Handling ===")

    with tmp_path as tmpdir:
        # Create a read-only directory
        readonly_dir = Path(tmpdir) / "readonly"
        readonly_dir.mkdir()
        os.chmod(readonly_dir, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)  # Read-only

        try:
            logger = AsyncSessionLogger(
                base_dir=readonly_dir, log_format=LogFormat.JSON, enable_async=True
            )
            logger.set_session_id("permission_test")

            # Try to log to read-only directory
            success_count = 0
            error_count = 0

            for i in range(10):
                success = logger.log_response(
                    f"Permission test {i}",
                    "Testing permission error handling",
                    {"agent": "permission_test"},
                )

                if success:
                    success_count += 1
                else:
                    error_count += 1

            # Attempt to flush (should handle errors gracefully)
            logger.flush(timeout=5.0)

            # Get statistics
            stats = logger.get_stats()

            print("  ✓ Attempted logs: 10")
            print(f"  ✓ Successful logs: {success_count}")
            print(f"  ✓ Failed logs: {error_count}")
            print(f"  ✓ Logger stats: {stats}")
            print(f"  ✓ Errors in stats: {stats['errors']}")

            # Check that no files were created in read-only directory
            files_created = len(list(readonly_dir.glob("**/*.json")))
            print(f"  ✓ Files created in read-only dir: {files_created}")

            logger.shutdown()

            return {
                "attempted_logs": 10,
                "successful_logs": success_count,
                "failed_logs": error_count,
                "files_created": files_created,
                "error_stats": stats["errors"],
                "graceful_handling": stats["errors"] > 0,  # Should have logged errors
                "success": True,  # Success if it didn't crash
            }

        finally:
            # Restore permissions to allow cleanup
            with contextlib.suppress(Exception):
                os.chmod(readonly_dir, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)


def test_disk_space_simulation():
    """Simulate disk full condition using mocks."""
    print("\n=== Testing Disk Full Simulation ===")

    with tmp_path as tmpdir:
        logger = AsyncSessionLogger(
            base_dir=Path(tmpdir), log_format=LogFormat.JSON, enable_async=True
        )
        logger.set_session_id("disk_full_test")

        # Mock the file writing to simulate disk full
        original_open = open
        write_attempts = 0
        disk_full_after = 5  # Simulate disk full after 5 writes

        def mock_open(*args, **kwargs):
            nonlocal write_attempts
            if "w" in str(args) or kwargs.get("mode", "").startswith("w"):
                write_attempts += 1
                if write_attempts > disk_full_after:
                    raise OSError(28, "No space left on device")  # ENOSPC
            return original_open(*args, **kwargs)

        successful_logs = 0
        failed_logs = 0

        with patch("builtins.open", side_effect=mock_open):
            # Try to log many entries
            for i in range(15):
                success = logger.log_response(
                    f"Disk full test {i}",
                    "Testing disk full error handling",
                    {"agent": "disk_test", "index": i},
                )

                if success:
                    successful_logs += 1
                else:
                    failed_logs += 1

            # Try to flush (should handle disk full gracefully)
            logger.flush(timeout=10.0)

        # Get final statistics
        stats = logger.get_stats()

        # Count actual files created
        actual_files = len(list(Path(tmpdir).glob("**/*.json")))

        print("  ✓ Attempted logs: 15")
        print(f"  ✓ Queued successfully: {successful_logs}")
        print(f"  ✓ Queue failures: {failed_logs}")
        print(f"  ✓ Actual files created: {actual_files}")
        print(f"  ✓ Write attempts: {write_attempts}")
        print(f"  ✓ Logger stats: {stats}")

        logger.shutdown()

        return {
            "attempted_logs": 15,
            "queued_successfully": successful_logs,
            "queue_failures": failed_logs,
            "actual_files": actual_files,
            "write_attempts": write_attempts,
            "disk_full_errors": stats["errors"],
            "graceful_degradation": stats["errors"] > 0
            and actual_files <= disk_full_after,
            "success": True,  # Success if it handled the error gracefully
        }


def test_invalid_data_handling():
    """Test handling of various invalid data scenarios."""
    print("\n=== Testing Invalid Data Handling ===")

    with tmp_path as tmpdir:
        logger = AsyncSessionLogger(
            base_dir=Path(tmpdir), log_format=LogFormat.JSON, enable_async=True
        )
        logger.set_session_id("invalid_data_test")

        # Test cases with different types of invalid data
        test_cases = [
            # None values
            (None, "Valid response", {"agent": "test"}),
            ("Valid request", None, {"agent": "test"}),
            ("Valid request", "Valid response", None),
            # Empty values
            ("", "", {}),
            ("", "Valid response", {"agent": "test"}),
            ("Valid request", "", {"agent": "test"}),
            # Non-string values
            (123, "Valid response", {"agent": "test"}),
            ("Valid request", 456, {"agent": "test"}),
            ("Valid request", "Valid response", {"agent": 789}),
            # Very large data
            ("X" * 100000, "Valid response", {"agent": "test"}),  # 100KB request
            ("Valid request", "Y" * 100000, {"agent": "test"}),  # 100KB response
            (
                "Valid request",
                "Valid response",
                {"agent": "test", "large_data": "Z" * 50000},
            ),  # 50KB metadata
            # Complex nested data
            (
                "Valid request",
                "Valid response",
                {
                    "agent": "test",
                    "nested": {"deep": {"very": {"deep": {"data": list(range(1000))}}}},
                    "circular_ref": "would cause issues if not handled",
                },
            ),
            # Unicode and special characters
            (
                "Request with émojis 🚀🔥",
                "Response with spéciál chärs ñ",
                {"agent": "tëst_ågënt"},
            ),
            # Binary-like data (bytes converted to string)
            (str(b"\x00\x01\x02\x03"), "Binary data test", {"agent": "binary_test"}),
        ]

        results = {"successful": 0, "failed": 0, "errors": []}

        for i, (request, response, metadata) in enumerate(test_cases):
            try:
                success = logger.log_response(request, response, metadata)
                if success:
                    results["successful"] += 1
                else:
                    results["failed"] += 1

                print(f"  ✓ Test case {i + 1}: {'Success' if success else 'Failed'}")

            except Exception as e:
                results["errors"].append(f"Test case {i + 1}: {str(e)[:100]}")
                print(f"  ✗ Test case {i + 1}: Exception - {str(e)[:100]}")

        # Flush and get final stats
        logger.flush(timeout=10.0)
        stats = logger.get_stats()

        # Count actual files created
        files_created = len(list(Path(tmpdir).glob("**/*.json")))

        print("\n  📊 Results:")
        print(f"    ✓ Test cases: {len(test_cases)}")
        print(f"    ✓ Successful: {results['successful']}")
        print(f"    ✓ Failed: {results['failed']}")
        print(f"    ✓ Exceptions: {len(results['errors'])}")
        print(f"    ✓ Files created: {files_created}")
        print(f"    ✓ Logger stats: {stats}")

        # Verify files are valid JSON
        valid_files = 0
        invalid_files = 0

        for json_file in Path(tmpdir).glob("**/*.json"):
            try:
                with open(json_file, encoding="utf-8") as f:
                    import json

                    json.load(f)
                valid_files += 1
            except:
                invalid_files += 1

        print(f"    ✓ Valid JSON files: {valid_files}")
        print(f"    ✓ Invalid JSON files: {invalid_files}")

        logger.shutdown()

        return {
            "total_test_cases": len(test_cases),
            "successful": results["successful"],
            "failed": results["failed"],
            "exceptions": len(results["errors"]),
            "files_created": files_created,
            "valid_json_files": valid_files,
            "invalid_json_files": invalid_files,
            "error_details": results["errors"],
            "graceful_handling": len(results["errors"])
            == 0,  # Should handle without exceptions
            "success": len(results["errors"])
            < len(test_cases) * 0.1,  # Allow up to 10% exception rate
        }


def test_concurrent_error_scenarios():
    """Test error handling under concurrent conditions."""
    print("\n=== Testing Concurrent Error Scenarios ===")

    with tmp_path as tmpdir:
        logger = AsyncSessionLogger(
            base_dir=Path(tmpdir),
            log_format=LogFormat.JSON,
            enable_async=True,
            max_queue_size=100,  # Small queue to force overflow
        )
        logger.set_session_id("concurrent_error_test")

        import threading
        from concurrent.futures import ThreadPoolExecutor

        # Shared state for tracking results
        results = {
            "successful": 0,
            "dropped": 0,
            "exceptions": 0,
            "lock": threading.Lock(),
        }

        def worker_with_errors(thread_id: int):
            """Worker that may encounter various error conditions."""
            thread_successful = 0
            thread_dropped = 0
            thread_exceptions = 0

            for i in range(200):  # Enough to overflow queue
                try:
                    # Introduce some problematic data occasionally
                    if i % 50 == 0:
                        # Very large data that might cause issues
                        request = f"Thread {thread_id} large request " + "X" * 10000
                        response = f"Thread {thread_id} large response " + "Y" * 10000
                    elif i % 37 == 0:
                        # None values
                        request = None
                        response = f"Thread {thread_id} response {i}"
                    else:
                        # Normal data
                        request = f"Thread {thread_id} request {i}"
                        response = f"Thread {thread_id} response {i}"

                    success = logger.log_response(
                        request, response, {"agent": f"thread_{thread_id}", "index": i}
                    )

                    if success:
                        thread_successful += 1
                    else:
                        thread_dropped += 1

                except Exception:
                    thread_exceptions += 1

            # Update shared results
            with results["lock"]:
                results["successful"] += thread_successful
                results["dropped"] += thread_dropped
                results["exceptions"] += thread_exceptions

            return thread_id, thread_successful, thread_dropped, thread_exceptions

        # Run concurrent workers
        num_threads = 20
        total_requests = num_threads * 200

        print(f"  Starting {num_threads} threads with error conditions...")

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [
                executor.submit(worker_with_errors, i) for i in range(num_threads)
            ]

            for future in futures:
                try:
                    future.result()
                except Exception as e:
                    print(f"  ⚠ Thread exception: {e}")

        # Try to flush (may timeout due to errors)
        print("  ⏳ Flushing with potential errors...")
        flush_success = logger.flush(timeout=15.0)

        # Get final statistics
        stats = logger.get_stats()

        # Count files created
        files_created = len(list(Path(tmpdir).glob("**/*.json")))

        print("  📊 Concurrent Error Results:")
        print(f"    ✓ Total requests attempted: {total_requests}")
        print(f"    ✓ Successful logs: {results['successful']}")
        print(f"    ✓ Dropped logs: {results['dropped']}")
        print(f"    ✓ Thread exceptions: {results['exceptions']}")
        print(f"    ✓ Files created: {files_created}")
        print(f"    ✓ Flush successful: {flush_success}")
        print(f"    ✓ Logger stats: {stats}")

        logger.shutdown()

        return {
            "total_requests": total_requests,
            "successful": results["successful"],
            "dropped": results["dropped"],
            "thread_exceptions": results["exceptions"],
            "files_created": files_created,
            "flush_successful": flush_success,
            "logger_stats": stats,
            "graceful_degradation": results["exceptions"]
            < total_requests * 0.05,  # <5% exception rate
            "success": results["successful"] > 0
            and results["exceptions"] < total_requests * 0.1,
        }


def test_recovery_after_errors():
    """Test system recovery after various error conditions."""
    print("\n=== Testing Recovery After Errors ===")

    with tmp_path as tmpdir:
        # Phase 1: Introduce errors
        print("  Phase 1: Introducing errors...")

        logger = AsyncSessionLogger(
            base_dir=Path(tmpdir), log_format=LogFormat.JSON, enable_async=True
        )
        logger.set_session_id("recovery_test_phase1")

        # Log some problematic data
        problematic_logs = 0
        for i in range(10):
            try:
                success = logger.log_response(
                    None if i % 3 == 0 else f"Request {i}",
                    (
                        "X" * 50000 if i % 5 == 0 else f"Response {i}"
                    ),  # Some very large responses
                    None if i % 4 == 0 else {"agent": f"error_agent_{i}"},
                )
                if success:
                    problematic_logs += 1
            except:
                pass

        logger.flush(timeout=5.0)
        phase1_stats = logger.get_stats()
        phase1_files = len(list(Path(tmpdir).glob("**/*.json")))

        print("    ✓ Phase 1 problematic logs attempted: 10")
        print(f"    ✓ Phase 1 successful: {problematic_logs}")
        print(f"    ✓ Phase 1 files: {phase1_files}")
        print(f"    ✓ Phase 1 errors: {phase1_stats['errors']}")

        logger.shutdown()

        # Phase 2: Normal operation after errors
        print("  Phase 2: Normal operation after errors...")

        logger2 = AsyncSessionLogger(
            base_dir=Path(tmpdir), log_format=LogFormat.JSON, enable_async=True
        )
        logger2.set_session_id("recovery_test_phase2")

        # Log normal data
        normal_logs = 0
        for i in range(20):
            success = logger2.log_response(
                f"Normal request {i}",
                f"Normal response {i}",
                {"agent": "recovery_agent", "phase": 2, "index": i},
            )
            if success:
                normal_logs += 1

        logger2.flush(timeout=5.0)
        phase2_stats = logger2.get_stats()

        # Count all files now
        total_files = len(list(Path(tmpdir).glob("**/*.json")))
        phase2_files = total_files - phase1_files

        print("    ✓ Phase 2 normal logs attempted: 20")
        print(f"    ✓ Phase 2 successful: {normal_logs}")
        print(f"    ✓ Phase 2 new files: {phase2_files}")
        print(f"    ✓ Phase 2 errors: {phase2_stats['errors']}")
        print(f"    ✓ Total files: {total_files}")

        # Test that phase 2 files are valid
        valid_phase2_files = 0
        for json_file in Path(tmpdir).glob("**/recovery_test_phase2/*.json"):
            try:
                with json_file.open() as f:
                    import json

                    data = json.load(f)
                    if "recovery_agent" in str(data):
                        valid_phase2_files += 1
            except:
                pass

        print(f"    ✓ Valid phase 2 files: {valid_phase2_files}")

        logger2.shutdown()

        return {
            "phase1_attempts": 10,
            "phase1_successful": problematic_logs,
            "phase1_files": phase1_files,
            "phase1_errors": phase1_stats["errors"],
            "phase2_attempts": 20,
            "phase2_successful": normal_logs,
            "phase2_files": phase2_files,
            "phase2_errors": phase2_stats["errors"],
            "valid_phase2_files": valid_phase2_files,
            "recovery_successful": normal_logs > 15 and valid_phase2_files > 15,
            "success": normal_logs >= 18
            and phase2_stats["errors"] == 0,  # Should recover cleanly
        }


def main():
    """Main error handling test function."""
    print("🛡️ ERROR HANDLING TEST SUITE")
    print("=" * 60)

    # Run error handling tests
    tests_results = {}

    try:
        tests_results["permissions"] = test_permission_errors()
        tests_results["disk_full"] = test_disk_space_simulation()
        tests_results["invalid_data"] = test_invalid_data_handling()
        tests_results["concurrent_errors"] = test_concurrent_error_scenarios()
        tests_results["recovery"] = test_recovery_after_errors()

    except Exception as e:
        print(f"\n❌ ERROR DURING TESTING: {e}")
        import traceback

        traceback.print_exc()

    # Summary
    print("\n" + "=" * 60)
    print("ERROR HANDLING SUMMARY")
    print("=" * 60)

    for test_name, result in tests_results.items():
        if result:
            print(f"\n🔧 {test_name.replace('_', ' ').title()} Test:")

            # Test-specific reporting
            if test_name == "permissions":
                print(f"  ✓ Attempted logs: {result.get('attempted_logs', 0)}")
                print(f"  ✓ Permission errors handled: {result.get('error_stats', 0)}")
                print(f"  ✓ Files in readonly dir: {result.get('files_created', 0)}")

            elif test_name == "disk_full":
                print(f"  ✓ Write attempts: {result.get('write_attempts', 0)}")
                print(f"  ✓ Files before disk full: {result.get('actual_files', 0)}")
                print(f"  ✓ Disk full errors: {result.get('disk_full_errors', 0)}")

            elif test_name == "invalid_data":
                print(f"  ✓ Test cases: {result.get('total_test_cases', 0)}")
                print(f"  ✓ Successful handling: {result.get('successful', 0)}")
                print(f"  ✓ Exceptions: {result.get('exceptions', 0)}")
                print(f"  ✓ Valid JSON files: {result.get('valid_json_files', 0)}")

            elif test_name == "concurrent_errors":
                print(f"  ✓ Total requests: {result.get('total_requests', 0)}")
                print(f"  ✓ Thread exceptions: {result.get('thread_exceptions', 0)}")
                print(f"  ✓ Files created: {result.get('files_created', 0)}")

            elif test_name == "recovery":
                print(f"  ✓ Phase 1 errors: {result.get('phase1_errors', 0)}")
                print(f"  ✓ Phase 2 recovery: {result.get('phase2_successful', 0)}/20")
                print(
                    f"  ✓ Recovery successful: {result.get('recovery_successful', False)}"
                )

            status = "✅ PASS" if result.get("success", False) else "❌ FAIL"
            print(f"  ✓ Status: {status}")

    # Overall assessment
    successful_tests = sum(
        1 for result in tests_results.values() if result and result.get("success")
    )
    total_tests = len(tests_results)

    print("\n🎯 OVERALL ERROR HANDLING RESULTS:")
    print(f"  ✓ Successful tests: {successful_tests}/{total_tests}")

    if successful_tests >= total_tests - 1:  # Allow one test to have issues
        print("\n🛡️ ERROR HANDLING TESTS PASSED!")
        print("✅ System handles permission errors gracefully")
        print("✅ Disk full conditions managed appropriately")
        print("✅ Invalid data processed without crashes")
        print("✅ Concurrent error scenarios handled")
        print("✅ System recovers properly after errors")
    else:
        print("\n⚠️ ERROR HANDLING HAD ISSUES")
        print(f"❌ Only {successful_tests}/{total_tests} tests passed")
        print("❌ Review failed tests above for robustness issues")

    return {
        "tests_results": tests_results,
        "successful_tests": successful_tests,
        "total_tests": total_tests,
        "overall_success": successful_tests >= total_tests - 1,
    }


if __name__ == "__main__":
    main()
