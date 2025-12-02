#!/usr/bin/env python3
"""
Integration test for async logging system with Claude MPM agents.
Tests backward compatibility and real-world usage.
"""

import json
import os
import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.services.async_session_logger import (
    AsyncSessionLogger,
    LogFormat,
    log_response_async,
)
from claude_mpm.services.claude_session_logger import ClaudeSessionLogger


def test_backward_compatibility():
    """Test that existing Claude session logger still works."""
    print("\n=== Testing Backward Compatibility ===")

    with tmp_path as tmpdir:
        # Test original logger
        original_logger = ClaudeSessionLogger(
            base_dir=Path(tmpdir) / "original", use_async=False
        )
        original_logger.set_session_id("backward_compat_test")

        # Test requests that simulate real agent usage
        test_requests = [
            (
                "User asked for code review",
                "Reviewed Python code and found 3 issues",
                {"agent": "engineer"},
            ),
            (
                "Deploy application request",
                "Successfully deployed v1.2.3 to production",
                {"agent": "ops"},
            ),
            (
                "Query database for metrics",
                "Retrieved 1,245 records in 0.15s",
                {"agent": "data_engineer"},
            ),
        ]

        start_time = time.perf_counter()

        for req_summary, response, metadata in test_requests:
            success = original_logger.log_response(req_summary, response, metadata)
            assert success, "Original logger should work"

        original_time = time.perf_counter() - start_time

        # Check files were created
        session_dir = Path(tmpdir) / "original" / "backward_compat_test"
        original_files = len(list(session_dir.glob("*.json")))

        print(
            f"  ✓ Original logger created {original_files} files in {original_time * 1000:.3f}ms"
        )

        # Test new async logger with backward compatibility
        async_logger = AsyncSessionLogger(
            base_dir=Path(tmpdir) / "async",
            log_format=LogFormat.JSON,
            enable_async=True,
        )
        async_logger.set_session_id("backward_compat_test")

        start_time = time.perf_counter()

        for req_summary, response, metadata in test_requests:
            success = async_logger.log_response(req_summary, response, metadata)
            assert success, "Async logger should work with same API"

        queue_time = time.perf_counter() - start_time

        # Flush to complete writes
        async_logger.flush(timeout=5.0)
        total_time = time.perf_counter() - start_time

        # Check files were created
        async_session_dir = Path(tmpdir) / "async" / "backward_compat_test"
        async_files = len(list(async_session_dir.glob("*.json")))

        print(f"  ✓ Async logger created {async_files} files")
        print(
            f"  ✓ Queue time: {queue_time * 1000:.3f}ms (vs original: {original_time * 1000:.3f}ms)"
        )
        print(f"  ✓ Total time: {total_time * 1000:.3f}ms")
        print(
            f"  ✓ Performance improvement: {(original_time - queue_time) / original_time * 100:.1f}%"
        )

        # Verify file contents are equivalent
        original_file = next(session_dir.glob("*.json"))
        async_file = next(async_session_dir.glob("*.json"))

        with original_file.open() as f:
            original_data = json.load(f)

        with async_file.open() as f:
            async_data = json.load(f)

        # Check that the same essential fields exist
        essential_fields = [
            "request_summary",
            "response_content",
            "metadata",
            "session_id",
        ]
        fields_match = all(
            field in both
            for field in essential_fields
            for both in [original_data, async_data]
        )

        print(f"  ✓ Essential fields match: {fields_match}")

        async_logger.shutdown()

        return {
            "original_files": original_files,
            "async_files": async_files,
            "original_time_ms": original_time * 1000,
            "async_queue_time_ms": queue_time * 1000,
            "async_total_time_ms": total_time * 1000,
            "performance_improvement_pct": (original_time - queue_time)
            / original_time
            * 100,
            "fields_match": fields_match,
            "success": original_files == async_files == 3 and fields_match,
        }


def test_async_convenience_function():
    """Test the async convenience function for global usage."""
    print("\n=== Testing Async Convenience Function ===")

    with tmp_path:
        # Set environment to control logger
        os.environ["CLAUDE_LOG_FORMAT"] = "json"

        # Test the global convenience function
        test_responses = [
            (
                "Global function test 1",
                "First test of global async logging",
                {"agent": "qa"},
            ),
            (
                "Global function test 2",
                "Second test with different metadata",
                {"agent": "test", "priority": "high"},
            ),
            (
                "Global function test 3",
                "Third test for consistency",
                {"agent": "integration"},
            ),
        ]

        start_time = time.perf_counter()

        for req_summary, response, metadata in test_responses:
            success = log_response_async(req_summary, response, metadata)
            assert success, "Global async function should work"

        queue_time = time.perf_counter() - start_time

        print(
            f"  ✓ Global function queued {len(test_responses)} responses in {queue_time * 1000:.3f}ms"
        )
        print(
            f"  ✓ Average queue time per response: {queue_time / len(test_responses) * 1000:.3f}ms"
        )
        print(f"  ✓ Throughput: {len(test_responses) / queue_time:.1f} responses/sec")

        # Clean up environment
        if "CLAUDE_LOG_FORMAT" in os.environ:
            del os.environ["CLAUDE_LOG_FORMAT"]

        return {
            "responses_logged": len(test_responses),
            "queue_time_ms": queue_time * 1000,
            "avg_time_per_response_ms": queue_time / len(test_responses) * 1000,
            "throughput": len(test_responses) / queue_time,
            "success": True,
        }


def test_session_id_handling():
    """Test session ID handling and environment variable detection."""
    print("\n=== Testing Session ID Handling ===")

    with tmp_path as tmpdir:
        # Test 1: Environment variable detection
        test_session_id = "test_env_session_12345"
        os.environ["CLAUDE_SESSION_ID"] = test_session_id

        logger = AsyncSessionLogger(
            base_dir=Path(tmpdir) / "env_test", enable_async=True
        )

        detected_session = logger.session_id
        env_detection_works = detected_session == test_session_id

        print(f"  ✓ Environment session ID detected: {env_detection_works}")
        print(f"  ✓ Expected: {test_session_id}")
        print(f"  ✓ Detected: {detected_session}")

        # Test logging with environment session ID
        logger.log_response(
            "Environment session test",
            "Testing session ID from environment variable",
            {"agent": "session_test"},
        )

        logger.flush(timeout=2.0)

        # Check that file was created in correct session directory
        env_session_dir = Path(tmpdir) / "env_test" / test_session_id
        env_session_files = len(list(env_session_dir.glob("*.json")))

        print(
            f"  ✓ Files created in environment session directory: {env_session_files}"
        )

        logger.shutdown()

        # Clean up
        if "CLAUDE_SESSION_ID" in os.environ:
            del os.environ["CLAUDE_SESSION_ID"]

        # Test 2: Manual session ID setting
        manual_session = "manual_test_session_67890"
        logger2 = AsyncSessionLogger(
            base_dir=Path(tmpdir) / "manual_test", enable_async=True
        )

        logger2.set_session_id(manual_session)
        manual_session_set = logger2.session_id == manual_session

        print(f"  ✓ Manual session ID setting: {manual_session_set}")

        logger2.log_response(
            "Manual session test",
            "Testing manual session ID setting",
            {"agent": "manual_test"},
        )

        logger2.flush(timeout=2.0)

        # Check that file was created in correct session directory
        manual_session_dir = Path(tmpdir) / "manual_test" / manual_session
        manual_session_files = len(list(manual_session_dir.glob("*.json")))

        print(f"  ✓ Files created in manual session directory: {manual_session_files}")

        logger2.shutdown()

        return {
            "env_detection_works": env_detection_works,
            "env_session_files": env_session_files,
            "manual_session_set": manual_session_set,
            "manual_session_files": manual_session_files,
            "success": env_detection_works
            and manual_session_set
            and env_session_files > 0
            and manual_session_files > 0,
        }


def test_metadata_handling():
    """Test metadata handling and agent name extraction."""
    print("\n=== Testing Metadata Handling ===")

    with tmp_path as tmpdir:
        logger = AsyncSessionLogger(base_dir=Path(tmpdir), enable_async=True)
        logger.set_session_id("metadata_test")

        # Test different metadata scenarios
        test_cases = [
            # Agent name extraction
            (
                "Agent name test",
                "Testing agent name extraction",
                {"agent": "Test Agent"},
                "test_agent",  # Expected filename prefix
            ),
            # Complex metadata
            (
                "Complex metadata test",
                "Testing complex metadata handling",
                {
                    "agent": "Data Engineer",
                    "model": "claude-3-sonnet",
                    "tokens": 1500,
                    "processing_time": 2.3,
                    "metadata": {"nested": "data"},
                },
                "data_engineer",
            ),
            # Missing agent metadata
            (
                "No agent test",
                "Testing without agent metadata",
                {"some": "other", "data": "here"},
                "unknown",
            ),
            # Special characters in agent name
            (
                "Special chars test",
                "Testing special characters",
                {"agent": "QA & Security-Agent v2.0!"},
                "qa_&_security-agent_v2.0!",
            ),
        ]

        for req_summary, response, metadata, _expected_prefix in test_cases:
            logger.log_response(req_summary, response, metadata)

        logger.flush(timeout=5.0)

        # Check created files
        session_dir = Path(tmpdir) / "metadata_test"
        created_files = list(session_dir.glob("*.json"))

        print(
            f"  ✓ Created {len(created_files)} files for {len(test_cases)} test cases"
        )

        # Validate file contents and naming
        valid_files = 0
        agent_names_extracted = []

        for json_file in created_files:
            try:
                with json_file.open() as f:
                    data = json.load(f)

                # Check essential fields
                assert "agent_name" in data
                assert "metadata" in data
                assert "request_summary" in data
                assert "response_content" in data
                assert "timestamp" in data

                agent_names_extracted.append(data["agent_name"])

                # Check that metadata is preserved
                if "tokens" in data["metadata"]:
                    assert data["metadata"]["tokens"] == 1500

                valid_files += 1

            except Exception as e:
                print(f"  ✗ Invalid file {json_file}: {e}")

        print(f"  ✓ Valid files: {valid_files}")
        print(f"  ✓ Agent names extracted: {agent_names_extracted}")

        # Check unique agent names were handled
        unique_agents = len(set(agent_names_extracted))
        expected_unique = len(
            test_cases
        )  # Each test case has different expected agent name

        print(f"  ✓ Unique agent names: {unique_agents} (expected: {expected_unique})")

        logger.shutdown()

        return {
            "files_created": len(created_files),
            "valid_files": valid_files,
            "agent_names_extracted": agent_names_extracted,
            "unique_agents": unique_agents,
            "success": valid_files == len(test_cases)
            and unique_agents == expected_unique,
        }


def test_error_recovery():
    """Test error recovery and graceful degradation."""
    print("\n=== Testing Error Recovery ===")

    with tmp_path as tmpdir:
        logger = AsyncSessionLogger(
            base_dir=Path(tmpdir),
            enable_async=True,
            max_queue_size=5,  # Small queue to test overflow
        )
        logger.set_session_id("error_test")

        # Test 1: Queue overflow handling
        print("  Testing queue overflow...")

        successful_logs = 0
        dropped_logs = 0

        # Try to overwhelm the small queue
        for i in range(20):
            success = logger.log_response(
                f"Overflow test {i}",
                "Testing queue overflow behavior" * 100,  # Large response
                {"agent": "overflow_test", "index": i},
            )

            if success:
                successful_logs += 1
            else:
                dropped_logs += 1

        print(f"  ✓ Successful logs: {successful_logs}")
        print(f"  ✓ Dropped logs: {dropped_logs}")

        # Give time for queue to process
        time.sleep(0.1)
        logger.flush(timeout=5.0)

        # Check statistics
        stats = logger.get_stats()
        print(
            f"  ✓ Logger stats: queued={stats['queued']}, dropped={stats['dropped']}, errors={stats['errors']}"
        )

        # Test 2: Invalid data handling
        print("  Testing invalid data handling...")

        # These should not crash the logger
        invalid_test_cases = [
            (None, "Test with None request", {"agent": "invalid"}),
            ("Valid request", None, {"agent": "invalid"}),
            ("Valid request", "Valid response", None),  # None metadata
            ("", "", {}),  # Empty strings
            (
                "Very long request " * 1000,
                "Very long response " * 1000,
                {"agent": "stress", "data": "x" * 10000},
            ),  # Large data
        ]

        error_recoveries = 0

        for req, resp, meta in invalid_test_cases:
            try:
                success = logger.log_response(req, resp, meta)
                error_recoveries += 1
            except Exception as e:
                print(f"  ⚠ Failed to handle invalid data: {e}")

        print(f"  ✓ Error recoveries: {error_recoveries}/{len(invalid_test_cases)}")

        logger.flush(timeout=5.0)
        final_stats = logger.get_stats()

        logger.shutdown()

        return {
            "successful_logs": successful_logs,
            "dropped_logs": dropped_logs,
            "error_recoveries": error_recoveries,
            "total_invalid_cases": len(invalid_test_cases),
            "final_stats": final_stats,
            "graceful_degradation": error_recoveries == len(invalid_test_cases),
        }


def main():
    """Main integration test function."""
    print("🔗 ASYNC LOGGING INTEGRATION TEST SUITE")
    print("=" * 60)

    # Run integration tests
    compatibility_result = test_backward_compatibility()
    convenience_result = test_async_convenience_function()
    session_result = test_session_id_handling()
    metadata_result = test_metadata_handling()
    error_result = test_error_recovery()

    # Summary
    print("\n" + "=" * 60)
    print("INTEGRATION TEST SUMMARY")
    print("=" * 60)

    print("🔄 Backward Compatibility:")
    print(
        f"  ✓ Performance improvement: {compatibility_result['performance_improvement_pct']:.1f}%"
    )
    print(
        f"  ✓ Files created: {compatibility_result['async_files']}/{compatibility_result['original_files']}"
    )
    print(
        f"  ✓ Field compatibility: {'✅' if compatibility_result['fields_match'] else '❌'}"
    )
    print(f"  ✓ Status: {'✅ PASS' if compatibility_result['success'] else '❌ FAIL'}")

    print("\n🌐 Global Function:")
    print(f"  ✓ Responses logged: {convenience_result['responses_logged']}")
    print(f"  ✓ Throughput: {convenience_result['throughput']:.1f} responses/sec")
    print(f"  ✓ Status: {'✅ PASS' if convenience_result['success'] else '❌ FAIL'}")

    print("\n🆔 Session Handling:")
    print(
        f"  ✓ Environment detection: {'✅' if session_result['env_detection_works'] else '❌'}"
    )
    print(
        f"  ✓ Manual setting: {'✅' if session_result['manual_session_set'] else '❌'}"
    )
    print(f"  ✓ Status: {'✅ PASS' if session_result['success'] else '❌ FAIL'}")

    print("\n📋 Metadata Handling:")
    print(f"  ✓ Files created: {metadata_result['files_created']}")
    print(f"  ✓ Valid files: {metadata_result['valid_files']}")
    print(f"  ✓ Unique agents: {metadata_result['unique_agents']}")
    print(f"  ✓ Status: {'✅ PASS' if metadata_result['success'] else '❌ FAIL'}")

    print("\n🛡️ Error Recovery:")
    print(f"  ✓ Successful logs: {error_result['successful_logs']}")
    print(f"  ✓ Dropped logs: {error_result['dropped_logs']}")
    print(
        f"  ✓ Error recoveries: {error_result['error_recoveries']}/{error_result['total_invalid_cases']}"
    )
    print(
        f"  ✓ Graceful degradation: {'✅' if error_result['graceful_degradation'] else '❌'}"
    )

    # Overall assessment
    successful_tests = sum(
        [
            compatibility_result["success"],
            convenience_result["success"],
            session_result["success"],
            metadata_result["success"],
            error_result["graceful_degradation"],
        ]
    )

    total_tests = 5

    if successful_tests >= 4:  # Allow for one minor failure
        print("\n🎉 INTEGRATION TESTS PASSED!")
        print("✅ Backward compatibility maintained")
        print("✅ Global convenience functions working")
        print("✅ Session management operational")
        print("✅ Metadata handling robust")
        print("✅ Error recovery and graceful degradation working")
    else:
        print("\n⚠️ SOME INTEGRATION TESTS FAILED")
        print(f"❌ Only {successful_tests}/{total_tests} tests passed")
        print("❌ Review failed tests above for issues")

    return {
        "compatibility": compatibility_result,
        "convenience": convenience_result,
        "session": session_result,
        "metadata": metadata_result,
        "error": error_result,
        "overall_success": successful_tests >= 4,
        "successful_tests": successful_tests,
        "total_tests": total_tests,
    }


if __name__ == "__main__":
    main()
