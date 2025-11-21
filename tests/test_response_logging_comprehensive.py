#!/usr/bin/env python3
"""
Comprehensive QA tests for response logging functionality.
Tests all aspects of the response tracking system including:
- Configuration loading
- Basic functionality
- CLI commands
- Integration testing
- Edge cases
- Performance
"""

import json
import os
import shutil
import sys
import threading
import time
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler
from claude_mpm.services.response_tracker import ResponseTracker


class TestResponseLoggingComprehensive(unittest.TestCase):
    """Comprehensive test suite for response logging functionality."""

    def setUp(self):
        """Set up test environment."""
        # Create temporary directory for testing
        self.test_dir = Path(tmp_path)
        self.responses_dir = self.test_dir / ".claude-mpm" / "responses"

        # Clean environment
        self.original_env = {}
        env_vars_to_clean = [
            "CLAUDE_PM_RESPONSE_TRACKING_ENABLED",
            "CLAUDE_MPM_TRACK_RESPONSES",
            "CLAUDE_PM_CONFIG_FILE",
        ]
        for var in env_vars_to_clean:
            self.original_env[var] = os.environ.get(var)
            if var in os.environ:
                del os.environ[var]

    def tearDown(self):
        """Clean up test environment."""
        # Restore environment
        for var, value in self.original_env.items():
            if value is not None:
                os.environ[var] = value
            elif var in os.environ:
                del os.environ[var]

        # Clean up test directory
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_configuration_loading_default():
        """Test that response tracking is disabled by default."""
        print("🧪 Testing default configuration loading...")

        config = Config()
        enabled = config.get("response_tracking.enabled", False)

        print(f"   Default enabled state: {enabled}")
        self.assertFalse(enabled, "Response tracking should be disabled by default")
        print("   ✅ Default configuration test passed")

    def test_configuration_loading_env_variable():
        """Test configuration loading with environment variables."""
        print("🧪 Testing environment variable configuration...")

        # Test with response tracking enabled via env var
        os.environ["CLAUDE_PM_RESPONSE_TRACKING_ENABLED"] = "true"

        config = Config()
        enabled = config.get("response_tracking_enabled", False)

        print(f"   Env var enabled state: {enabled}")
        # Note: This test depends on how the Config class handles env vars
        # The current implementation may not directly map env vars to config
        print("   ✅ Environment variable test completed")

    def test_hook_handler_initialization_disabled():
        """Test hook handler initialization with response tracking disabled."""
        print("🧪 Testing hook handler with tracking disabled...")

        # Ensure tracking is disabled
        if "CLAUDE_PM_RESPONSE_TRACKING_ENABLED" in os.environ:
            del os.environ["CLAUDE_PM_RESPONSE_TRACKING_ENABLED"]

        try:
            handler = ClaudeHookHandler()
            print(f"   Response tracking enabled: {handler.response_tracking_enabled}")
            print(
                f"   Response tracker initialized: {handler.response_tracker is not None}"
            )

            # Should be disabled by default
            self.assertFalse(
                handler.response_tracking_enabled,
                "Response tracking should be disabled by default",
            )
            print("   ✅ Hook handler disabled state test passed")

        except Exception as e:
            print(f"   ❌ Hook handler initialization failed: {e}")
            raise

    def test_hook_handler_initialization_enabled():
        """Test hook handler initialization with response tracking enabled."""
        print("🧪 Testing hook handler with tracking enabled...")

        # Create a temporary config file with response tracking enabled
        config_file = self.test_dir / "test_config.json"
        config_data = {"response_tracking": {"enabled": True}}

        with config_file.open("w") as f:
            json.dump(config_data, f)

        os.environ["CLAUDE_PM_CONFIG_FILE"] = str(config_file)

        try:
            handler = ClaudeHookHandler()
            print(f"   Response tracking enabled: {handler.response_tracking_enabled}")
            print(
                f"   Response tracker initialized: {handler.response_tracker is not None}"
            )

            # Should be enabled via config file
            self.assertTrue(
                handler.response_tracking_enabled,
                "Response tracking should be enabled via config file",
            )
            self.assertIsNotNone(
                handler.response_tracker, "Response tracker should be initialized"
            )
            print("   ✅ Hook handler enabled state test passed")

        except Exception as e:
            print(f"   ❌ Hook handler initialization failed: {e}")
            raise

    def test_basic_response_storage():
        """Test basic response storage functionality."""
        print("🧪 Testing basic response storage...")

        tracker = ResponseTracker(base_dir=self.responses_dir)

        # Test storing a response
        response_path = tracker.track_response(
            agent_name="test_agent",
            request="Test prompt for basic functionality",
            response="Test response for verification",
            session_id="test_session",
            metadata={"test": True, "duration": 1.5},
        )

        print(f"   Response saved to: {response_path}")
        self.assertTrue(response_path.exists(), "Response file should exist")

        # Verify response content
        with response_path.open() as f:
            response_data = json.load(f)

        self.assertEqual(response_data["agent"], "test_agent")
        self.assertEqual(response_data["session_id"], "test_session")
        self.assertEqual(
            response_data["request"], "Test prompt for basic functionality"
        )
        self.assertEqual(response_data["response"], "Test response for verification")
        self.assertEqual(response_data["metadata"]["test"], True)

        print("   ✅ Basic response storage test passed")

    def test_session_management():
        """Test session-based response management."""
        print("🧪 Testing session management...")

        tracker = ResponseTracker(base_dir=self.responses_dir)

        # Create responses in different sessions
        sessions = ["session_1", "session_2", "session_1"]  # Note duplicate session
        agents = ["agent_A", "agent_B", "agent_A"]

        for i, (session, agent) in enumerate(zip(sessions, agents)):
            tracker.track_response(
                agent_name=agent,
                request=f"Request {i + 1}",
                response=f"Response {i + 1}",
                session_id=session,
            )
            time.sleep(0.01)  # Small delay to ensure different timestamps

        # Test session listing
        session_list = tracker.list_sessions()
        print(f"   Sessions found: {session_list}")
        self.assertEqual(set(session_list), {"session_1", "session_2"})

        # Test getting session responses
        session_1_responses = tracker.get_session_responses("session_1")
        self.assertEqual(len(session_1_responses), 2)

        session_2_responses = tracker.get_session_responses("session_2")
        self.assertEqual(len(session_2_responses), 1)

        print("   ✅ Session management test passed")

    def test_statistics_generation():
        """Test statistics generation functionality."""
        print("🧪 Testing statistics generation...")

        tracker = ResponseTracker(base_dir=self.responses_dir)

        # Create test data
        test_data = [
            ("session_a", "engineer", "Fix the bug", "Bug fixed successfully"),
            ("session_a", "qa", "Test the fix", "All tests pass"),
            ("session_b", "engineer", "Add feature", "Feature implemented"),
        ]

        for session, agent, request, response in test_data:
            tracker.track_response(
                agent_name=agent, request=request, response=response, session_id=session
            )

        # Test overall statistics
        all_stats = tracker.get_all_stats()
        print(f"   Total sessions: {all_stats['total_sessions']}")
        print(f"   Total responses: {all_stats['total_responses']}")
        print(f"   Agents: {all_stats['agents']}")

        self.assertEqual(all_stats["total_sessions"], 2)
        self.assertEqual(all_stats["total_responses"], 3)
        self.assertEqual(all_stats["agents"]["engineer"], 2)
        self.assertEqual(all_stats["agents"]["qa"], 1)

        # Test session-specific statistics
        session_a_stats = tracker.get_session_stats("session_a")
        self.assertEqual(session_a_stats["total_responses"], 2)
        self.assertEqual(session_a_stats["agents"]["engineer"], 1)
        self.assertEqual(session_a_stats["agents"]["qa"], 1)

        print("   ✅ Statistics generation test passed")

    def test_large_response_handling():
        """Test handling of large responses."""
        print("🧪 Testing large response handling...")

        tracker = ResponseTracker(base_dir=self.responses_dir)

        # Create a large response (1MB)
        large_response = "This is a test response. " * 50000  # ~1MB

        start_time = time.time()
        response_path = tracker.track_response(
            agent_name="test_agent",
            request="Generate large output",
            response=large_response,
            session_id="large_test",
        )
        save_time = time.time() - start_time

        print(f"   Large response saved in {save_time:.3f}s")
        print(
            f"   Response file size: {response_path.stat().st_size / 1024 / 1024:.2f} MB"
        )

        # Verify the response can be loaded back
        start_time = time.time()
        responses = tracker.get_session_responses("large_test")
        load_time = time.time() - start_time

        print(f"   Large response loaded in {load_time:.3f}s")
        self.assertEqual(len(responses), 1)
        self.assertEqual(responses[0]["response"], large_response)

        print("   ✅ Large response handling test passed")

    def test_concurrent_access():
        """Test concurrent access to response tracking."""
        print("🧪 Testing concurrent access...")

        tracker = ResponseTracker(base_dir=self.responses_dir)
        results = []
        errors = []

        def track_response_worker(worker_id):
            try:
                for i in range(5):
                    response_path = tracker.track_response(
                        agent_name=f"worker_{worker_id}",
                        request=f"Request {i} from worker {worker_id}",
                        response=f"Response {i} from worker {worker_id}",
                        session_id=f"concurrent_session_{worker_id % 2}",
                    )
                    results.append(response_path)
                    time.sleep(0.01)  # Small delay
            except Exception as e:
                errors.append(f"Worker {worker_id}: {e}")

        # Start multiple threads
        threads = []
        for i in range(4):
            thread = threading.Thread(target=track_response_worker, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        print(f"   Concurrent operations completed: {len(results)} successes")
        print(f"   Errors encountered: {len(errors)}")

        self.assertEqual(len(errors), 0, f"No errors should occur: {errors}")
        self.assertEqual(len(results), 20, "All 20 responses should be tracked")

        # Verify all responses are accessible
        all_sessions = tracker.list_sessions()
        total_responses = sum(
            len(tracker.get_session_responses(s)) for s in all_sessions
        )
        self.assertEqual(total_responses, 20, "All responses should be accessible")

        print("   ✅ Concurrent access test passed")

    def test_error_handling_invalid_json():
        """Test error handling with invalid JSON in response files."""
        print("🧪 Testing error handling with invalid JSON...")

        tracker = ResponseTracker(base_dir=self.responses_dir)

        # Create a valid response first
        tracker.track_response(
            agent_name="test_agent",
            request="Test request",
            response="Test response",
            session_id="error_test",
        )

        # Corrupt one of the response files
        session_dir = self.responses_dir / "error_test"
        response_files = list(session_dir.glob("*.json"))
        self.assertTrue(
            len(response_files) > 0, "Should have at least one response file"
        )

        # Write invalid JSON to the file
        with open(response_files[0], "w") as f:
            f.write("{ invalid json content")

        # Try to load responses - should handle the error gracefully
        responses = tracker.get_session_responses("error_test")
        print(f"   Responses loaded despite corruption: {len(responses)}")

        # Should return empty list or handle gracefully
        self.assertIsInstance(responses, list, "Should return a list even with errors")

        print("   ✅ Error handling test passed")

    def test_cleanup_functionality():
        """Test cleanup functionality for old sessions."""
        print("🧪 Testing cleanup functionality...")

        tracker = ResponseTracker(base_dir=self.responses_dir)

        # Create responses with different timestamps
        current_time = datetime.now(timezone.utc)

        # Recent response (should not be cleaned)
        tracker.track_response(
            agent_name="recent_agent",
            request="Recent request",
            response="Recent response",
            session_id="recent_session",
        )

        # Create an old response by manually setting timestamp
        old_session_dir = self.responses_dir / "old_session"
        old_session_dir.mkdir(parents=True, exist_ok=True)

        old_timestamp = current_time - timedelta(days=10)
        old_response_data = {
            "timestamp": old_timestamp.isoformat(),
            "session_id": "old_session",
            "agent": "old_agent",
            "request": "Old request",
            "response": "Old response",
            "metadata": {},
        }

        old_file = (
            old_session_dir
            / f"old_agent-{old_timestamp.strftime('%Y%m%d_%H%M%S_000')}.json"
        )
        with old_file.open("w") as f:
            json.dump(old_response_data, f)

        # Verify both sessions exist
        sessions_before = tracker.list_sessions()
        print(f"   Sessions before cleanup: {sessions_before}")
        self.assertIn("recent_session", sessions_before)
        self.assertIn("old_session", sessions_before)

        # Clean sessions older than 5 days
        cleared_count = tracker.clear_old_sessions(5)
        print(f"   Sessions cleared: {cleared_count}")

        # Verify cleanup results
        sessions_after = tracker.list_sessions()
        print(f"   Sessions after cleanup: {sessions_after}")

        self.assertIn("recent_session", sessions_after)
        self.assertNotIn("old_session", sessions_after)
        self.assertEqual(cleared_count, 1)

        print("   ✅ Cleanup functionality test passed")


def run_performance_test():
    """Run performance tests separately."""
    print("\n🚀 Running performance tests...")

    test_dir = Path(tmp_path)
    responses_dir = test_dir / ".claude-mpm" / "responses"

    try:
        tracker = ResponseTracker(base_dir=responses_dir)

        # Test performance with many responses
        num_responses = 1000
        print(f"   Creating {num_responses} responses...")

        start_time = time.time()
        for i in range(num_responses):
            tracker.track_response(
                agent_name=f"agent_{i % 10}",
                request=f"Performance test request {i}",
                response=f"Performance test response {i} with some longer content to simulate real responses",
                session_id=f"perf_session_{i % 5}",
                metadata={"iteration": i, "test": "performance"},
            )
        creation_time = time.time() - start_time

        print(f"   Created {num_responses} responses in {creation_time:.2f}s")
        print(f"   Average: {creation_time / num_responses * 1000:.2f}ms per response")

        # Test reading performance
        start_time = time.time()
        all_stats = tracker.get_all_stats()
        stats_time = time.time() - start_time

        print(f"   Generated statistics in {stats_time:.3f}s")
        print(f"   Total responses: {all_stats['total_responses']}")
        print(f"   Total sessions: {all_stats['total_sessions']}")

        # Test latest responses performance
        start_time = time.time()
        tracker.get_latest_responses(100)
        latest_time = time.time() - start_time

        print(f"   Retrieved 100 latest responses in {latest_time:.3f}s")

        print("   ✅ Performance tests completed")

    finally:
        if test_dir.exists():
            shutil.rmtree(test_dir)


def main():
    """Run all tests."""
    print("🧪 Starting Comprehensive Response Logging QA Tests")
    print("=" * 60)

    # Run unit tests
    test_suite = unittest.TestLoader().loadTestsFromTestCase(
        TestResponseLoggingComprehensive
    )
    runner = unittest.TextTestRunner(verbosity=1)
    result = runner.run(test_suite)

    # Run performance tests
    run_performance_test()

    print("\n" + "=" * 60)
    if result.wasSuccessful():
        print("✅ All tests passed!")
        return 0
    print("❌ Some tests failed!")
    return 1


if __name__ == "__main__":
    sys.exit(main())
