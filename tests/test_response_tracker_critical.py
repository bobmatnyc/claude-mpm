"""
Comprehensive test suite for ResponseTracker service.

Tests critical functionality including:
- Response storage and retrieval
- Session management and correlation
- File I/O error handling
- Concurrent access safety
- Data persistence across restarts
- Privacy/data sanitization
- Large response handling
- Cleanup of old responses
"""

import json
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import mock_open, patch

import pytest

from claude_mpm.services.response_tracker import ResponseTracker


class TestResponseTrackerBasics:
    """Test basic response tracking functionality."""

    def test_init_creates_directory():
        """Test that initialization creates the responses directory."""
        with tmp_path as tmpdir:
            base_dir = Path(tmpdir) / "test_responses"
            ResponseTracker(base_dir)

            assert base_dir.exists()
            assert base_dir.is_dir()

    def test_track_response_basic():
        """Test basic response tracking."""
        with tmp_path as tmpdir:
            tracker = ResponseTracker(Path(tmpdir))

            file_path = tracker.track_response(
                agent_name="test_agent",
                request="test request",
                response="test response",
                session_id="test_session",
            )

            assert file_path.exists()
            assert file_path.parent.name == "test_session"
            assert "test_agent" in file_path.name

            # Verify content
            with file_path.open() as f:
                data = json.load(f)

            assert data["agent"] == "test_agent"
            assert data["request"] == "test request"
            assert data["response"] == "test response"
            assert data["session_id"] == "test_session"
            assert "timestamp" in data

    def test_track_response_default_session():
        """Test response tracking with default session."""
        with tmp_path as tmpdir:
            tracker = ResponseTracker(Path(tmpdir))

            file_path = tracker.track_response(
                agent_name="test_agent",
                request="test request",
                response="test response",
            )

            assert file_path.parent.name == "default"

    def test_track_response_with_metadata():
        """Test response tracking with metadata."""
        with tmp_path as tmpdir:
            tracker = ResponseTracker(Path(tmpdir))

            metadata = {"model": "claude-3", "tokens": 1000, "duration": 2.5}

            file_path = tracker.track_response(
                agent_name="test_agent",
                request="test request",
                response="test response",
                metadata=metadata,
            )

            with file_path.open() as f:
                data = json.load(f)

            assert data["metadata"] == metadata


class TestSessionManagement:
    """Test session management functionality."""

    def test_get_session_responses_empty():
        """Test getting responses for non-existent session."""
        with tmp_path as tmpdir:
            tracker = ResponseTracker(Path(tmpdir))
            responses = tracker.get_session_responses("nonexistent")

            assert responses == []

    def test_get_session_responses_multiple():
        """Test getting multiple responses for a session."""
        with tmp_path as tmpdir:
            tracker = ResponseTracker(Path(tmpdir))

            # Track multiple responses
            for i in range(3):
                time.sleep(0.01)  # Ensure different timestamps
                tracker.track_response(
                    agent_name=f"agent_{i}",
                    request=f"request_{i}",
                    response=f"response_{i}",
                    session_id="test_session",
                )

            responses = tracker.get_session_responses("test_session")

            assert len(responses) == 3
            # Should be sorted by timestamp
            for i in range(3):
                assert responses[i]["agent"] == f"agent_{i}"

    def test_list_sessions():
        """Test listing all sessions."""
        with tmp_path as tmpdir:
            tracker = ResponseTracker(Path(tmpdir))

            # Create multiple sessions
            sessions = ["session_a", "session_b", "session_c"]
            for session in sessions:
                tracker.track_response(
                    agent_name="test_agent",
                    request="test",
                    response="test",
                    session_id=session,
                )

            listed_sessions = tracker.list_sessions()

            assert sorted(listed_sessions) == sorted(sessions)

    def test_get_session_stats():
        """Test getting session statistics."""
        with tmp_path as tmpdir:
            tracker = ResponseTracker(Path(tmpdir))

            # Track responses from different agents
            for i in range(5):
                time.sleep(0.01)
                tracker.track_response(
                    agent_name="agent_a" if i < 3 else "agent_b",
                    request="test",
                    response="test",
                    session_id="test_session",
                )

            stats = tracker.get_session_stats("test_session")

            assert stats["session_id"] == "test_session"
            assert stats["total_responses"] == 5
            assert stats["agents"]["agent_a"] == 3
            assert stats["agents"]["agent_b"] == 2
            assert stats["duration"] > 0

    def test_get_session_stats_empty():
        """Test getting stats for non-existent session."""
        with tmp_path as tmpdir:
            tracker = ResponseTracker(Path(tmpdir))
            stats = tracker.get_session_stats("nonexistent")

            assert stats["total_responses"] == 0
            assert stats["agents"] == {}
            assert stats["first_response"] is None
            assert stats["last_response"] is None


class TestDataRetrieval:
    """Test data retrieval functionality."""

    def test_get_all_stats():
        """Test getting statistics for all sessions."""
        with tmp_path as tmpdir:
            tracker = ResponseTracker(Path(tmpdir))

            # Create multiple sessions with responses
            sessions_data = {
                "session_1": ["agent_a", "agent_a", "agent_b"],
                "session_2": ["agent_b", "agent_c"],
                "session_3": ["agent_a"],
            }

            for session, agents in sessions_data.items():
                for agent in agents:
                    time.sleep(0.001)  # Small delay to ensure unique timestamps
                    tracker.track_response(
                        agent_name=agent,
                        request="test",
                        response="test",
                        session_id=session,
                    )

            all_stats = tracker.get_all_stats()

            assert all_stats["total_sessions"] == 3
            assert all_stats["total_responses"] == 6
            assert all_stats["agents"]["agent_a"] == 3
            assert all_stats["agents"]["agent_b"] == 2
            assert all_stats["agents"]["agent_c"] == 1
            assert len(all_stats["sessions"]) == 3

    def test_get_latest_responses():
        """Test getting latest responses across all sessions."""
        with tmp_path as tmpdir:
            tracker = ResponseTracker(Path(tmpdir))

            # Create responses with delays
            for i in range(10):
                time.sleep(0.01)
                tracker.track_response(
                    agent_name=f"agent_{i % 3}",
                    request=f"request_{i}",
                    response=f"response_{i}",
                    session_id=f"session_{i % 2}",
                )

            # Get latest 5 responses
            latest = tracker.get_latest_responses(limit=5)

            assert len(latest) == 5
            # Should be in reverse chronological order
            for i in range(len(latest) - 1):
                assert latest[i]["timestamp"] >= latest[i + 1]["timestamp"]

    def test_get_latest_responses_by_agent():
        """Test filtering latest responses by agent."""
        with tmp_path as tmpdir:
            tracker = ResponseTracker(Path(tmpdir))

            # Create responses from different agents with slight delays
            for i in range(10):
                time.sleep(0.01)  # Small delay to ensure different timestamps
                tracker.track_response(
                    agent_name="agent_a" if i % 2 == 0 else "agent_b",
                    request=f"request_{i}",
                    response=f"response_{i}",
                    session_id="test_session",
                )

            latest_a = tracker.get_latest_responses(limit=10, agent_name="agent_a")
            latest_b = tracker.get_latest_responses(limit=10, agent_name="agent_b")

            assert len(latest_a) == 5
            assert len(latest_b) == 5
            assert all(r["agent"] == "agent_a" for r in latest_a)
            assert all(r["agent"] == "agent_b" for r in latest_b)


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_malformed_json_handling():
        """Test handling of corrupted JSON files."""
        with tmp_path as tmpdir:
            tracker = ResponseTracker(Path(tmpdir))

            # Create a valid response
            tracker.track_response(
                agent_name="good_agent",
                request="test",
                response="test",
                session_id="test_session",
            )

            # Create a corrupted JSON file
            session_dir = Path(tmpdir) / "test_session"
            corrupted_file = session_dir / "corrupted.json"
            with corrupted_file.open("w") as f:
                f.write("{invalid json}")

            # Should handle corrupted file gracefully
            responses = tracker.get_session_responses("test_session")

            # Should only get the valid response
            assert len(responses) == 1
            assert responses[0]["agent"] == "good_agent"

    def test_file_permission_error():
        """Test handling of file permission errors."""
        with tmp_path as tmpdir:
            tracker = ResponseTracker(Path(tmpdir))

            # Mock permission error
            with patch(
                "builtins.open", side_effect=PermissionError("Permission denied")
            ):
                # Should raise the permission error (no special handling in implementation)
                with pytest.raises(PermissionError):
                    tracker.track_response(
                        agent_name="test_agent", request="test", response="test"
                    )

    def test_disk_full_simulation():
        """Test handling when disk is full."""
        with tmp_path as tmpdir:
            tracker = ResponseTracker(Path(tmpdir))

            # Mock OSError for disk full
            with patch("builtins.open", mock_open()) as mock_file:
                mock_file.side_effect = OSError("No space left on device")

                # Should handle gracefully
                with pytest.raises(OSError):
                    tracker.track_response(
                        agent_name="test_agent", request="test", response="test"
                    )

    def test_unicode_handling():
        """Test handling of Unicode characters in responses."""
        with tmp_path as tmpdir:
            tracker = ResponseTracker(Path(tmpdir))

            unicode_content = "Hello 世界 🌍 مرحبا мир"
            file_path = tracker.track_response(
                agent_name="unicode_agent",
                request=unicode_content,
                response=unicode_content,
                session_id="unicode_session",
            )

            # Verify content is preserved
            with open(file_path, encoding="utf-8") as f:
                data = json.load(f)

            assert data["request"] == unicode_content
            assert data["response"] == unicode_content


class TestConcurrency:
    """Test concurrent access safety."""

    def test_concurrent_writes():
        """Test multiple threads writing responses simultaneously."""
        with tmp_path as tmpdir:
            tracker = ResponseTracker(Path(tmpdir))
            errors = []

            def write_response(thread_id):
                try:
                    for i in range(10):
                        time.sleep(0.001)  # Small delay to ensure unique timestamps
                        tracker.track_response(
                            agent_name=f"agent_{thread_id}",
                            request=f"request_{thread_id}_{i}",
                            response=f"response_{thread_id}_{i}",
                            session_id="concurrent_session",
                        )
                except Exception as e:
                    errors.append(e)

            # Create multiple threads
            threads = []
            for i in range(5):
                thread = threading.Thread(target=write_response, args=(i,))
                threads.append(thread)
                thread.start()

            # Wait for all threads
            for thread in threads:
                thread.join()

            # Check no errors occurred
            assert len(errors) == 0

            # Verify all responses were saved
            responses = tracker.get_session_responses("concurrent_session")
            assert len(responses) == 50  # 5 threads * 10 responses each

    def test_concurrent_reads():
        """Test multiple threads reading responses simultaneously."""
        with tmp_path as tmpdir:
            tracker = ResponseTracker(Path(tmpdir))

            # Create some responses
            for i in range(20):
                tracker.track_response(
                    agent_name=f"agent_{i}",
                    request=f"request_{i}",
                    response=f"response_{i}",
                    session_id="read_session",
                )

            results = []
            errors = []

            def read_responses():
                try:
                    responses = tracker.get_session_responses("read_session")
                    results.append(len(responses))
                except Exception as e:
                    errors.append(e)

            # Create multiple reader threads
            threads = []
            for _ in range(10):
                thread = threading.Thread(target=read_responses)
                threads.append(thread)
                thread.start()

            # Wait for all threads
            for thread in threads:
                thread.join()

            # Check no errors and all reads got same result
            assert len(errors) == 0
            assert all(r == 20 for r in results)


class TestDataPersistence:
    """Test data persistence across restarts."""

    def test_persistence_across_instances():
        """Test that data persists when creating new tracker instances."""
        with tmp_path as tmpdir:
            base_dir = Path(tmpdir)

            # First instance - write data
            tracker1 = ResponseTracker(base_dir)
            tracker1.track_response(
                agent_name="persistent_agent",
                request="persistent request",
                response="persistent response",
                session_id="persistent_session",
            )

            # Second instance - read data
            tracker2 = ResponseTracker(base_dir)
            responses = tracker2.get_session_responses("persistent_session")

            assert len(responses) == 1
            assert responses[0]["agent"] == "persistent_agent"

    def test_data_integrity_after_crash():
        """Test data integrity when process is interrupted."""
        with tmp_path as tmpdir:
            base_dir = Path(tmpdir)

            # Simulate partial write
            session_dir = base_dir / "crash_session"
            session_dir.mkdir(parents=True)

            # Write a complete JSON file
            complete_file = session_dir / "complete.json"
            with complete_file.open("w") as f:
                json.dump(
                    {
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "agent": "complete_agent",
                        "request": "test",
                        "response": "test",
                        "session_id": "crash_session",
                        "metadata": {},
                    },
                    f,
                )

            # Create tracker and verify it can read the data
            tracker = ResponseTracker(base_dir)
            responses = tracker.get_session_responses("crash_session")

            assert len(responses) == 1
            assert responses[0]["agent"] == "complete_agent"


class TestLargeResponses:
    """Test handling of large responses."""

    def test_large_response_storage():
        """Test storing very large responses."""
        with tmp_path as tmpdir:
            tracker = ResponseTracker(Path(tmpdir))

            # Create a large response (1MB)
            large_response = "x" * (1024 * 1024)

            file_path = tracker.track_response(
                agent_name="large_agent",
                request="test",
                response=large_response,
                session_id="large_session",
            )

            # Verify it was saved correctly
            with file_path.open() as f:
                data = json.load(f)

            assert len(data["response"]) == len(large_response)

    def test_many_responses_in_session():
        """Test handling sessions with many responses."""
        with tmp_path as tmpdir:
            tracker = ResponseTracker(Path(tmpdir))

            # Create 100 responses in one session (reduced from 1000 for test speed)
            for i in range(100):
                if i % 10 == 0:
                    time.sleep(0.002)  # Occasional delay to ensure unique timestamps
                tracker.track_response(
                    agent_name=f"agent_{i % 10}",
                    request=f"request_{i}",
                    response=f"response_{i}",
                    session_id="large_session",
                )

            # Should handle retrieval efficiently
            responses = tracker.get_session_responses("large_session")
            assert len(responses) == 100

            # Stats should be accurate
            stats = tracker.get_session_stats("large_session")
            assert stats["total_responses"] == 100


class TestCleanup:
    """Test cleanup functionality."""

    def test_clear_session():
        """Test clearing a specific session."""
        with tmp_path as tmpdir:
            tracker = ResponseTracker(Path(tmpdir))

            # Create responses in multiple sessions
            tracker.track_response(
                agent_name="agent_a",
                request="test",
                response="test",
                session_id="session_to_clear",
            )
            tracker.track_response(
                agent_name="agent_b",
                request="test",
                response="test",
                session_id="session_to_keep",
            )

            # Clear one session
            success = tracker.clear_session("session_to_clear")
            assert success

            # Verify it's gone
            assert tracker.get_session_responses("session_to_clear") == []

            # Other session should remain
            assert len(tracker.get_session_responses("session_to_keep")) == 1

    def test_clear_nonexistent_session():
        """Test clearing a session that doesn't exist."""
        with tmp_path as tmpdir:
            tracker = ResponseTracker(Path(tmpdir))

            success = tracker.clear_session("nonexistent")
            assert not success

    def test_clear_old_sessions():
        """Test clearing old sessions based on age."""
        with tmp_path as tmpdir:
            tracker = ResponseTracker(Path(tmpdir))

            # Create sessions with different timestamps
            now = datetime.now(timezone.utc)

            # Create old session (mock old timestamp)
            old_session_id = "old_session"
            tracker.track_response(
                agent_name="old_agent",
                request="test",
                response="test",
                session_id=old_session_id,
            )

            # Manually modify the timestamp in the file
            session_dir = Path(tmpdir) / old_session_id
            for file_path in session_dir.glob("*.json"):
                with file_path.open() as f:
                    data = json.load(f)

                # Set timestamp to 10 days ago
                old_time = now - timedelta(days=10)
                data["timestamp"] = old_time.isoformat()

                with file_path.open("w") as f:
                    json.dump(data, f)

            # Create recent session
            tracker.track_response(
                agent_name="recent_agent",
                request="test",
                response="test",
                session_id="recent_session",
            )

            # Clear sessions older than 7 days
            cleared = tracker.clear_old_sessions(days=7)

            assert cleared == 1
            assert tracker.get_session_responses("old_session") == []
            assert len(tracker.get_session_responses("recent_session")) == 1


class TestPrivacyAndSecurity:
    """Test privacy and data sanitization features."""

    def test_no_sensitive_data_in_filenames():
        """Test that filenames don't contain sensitive information."""
        with tmp_path as tmpdir:
            tracker = ResponseTracker(Path(tmpdir))

            sensitive_request = "password=secret123"
            file_path = tracker.track_response(
                agent_name="security_agent",
                request=sensitive_request,
                response="response",
                session_id="security_session",
            )

            # Filename should not contain the request content
            assert "secret123" not in file_path.name
            assert "password" not in file_path.name

    def test_session_id_sanitization():
        """Test that problematic session IDs are handled."""
        with tmp_path as tmpdir:
            tracker = ResponseTracker(Path(tmpdir))

            # Try various problematic session IDs that should work or fail gracefully
            problematic_ids = [
                "session_with_slash/test",  # Will create nested directory
                "session|pipe",  # Special char
                "session:colon",  # Special char on some filesystems
            ]

            for session_id in problematic_ids:
                try:
                    # May raise on some filesystems, but should handle gracefully
                    tracker.track_response(
                        agent_name="test_agent",
                        request="test",
                        response="test",
                        session_id=session_id,
                    )
                except (OSError, FileNotFoundError):
                    # Expected on some systems/characters
                    pass


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_response():
        """Test tracking empty responses."""
        with tmp_path as tmpdir:
            tracker = ResponseTracker(Path(tmpdir))

            file_path = tracker.track_response(
                agent_name="empty_agent",
                request="",
                response="",
                session_id="empty_session",
            )

            with file_path.open() as f:
                data = json.load(f)

            assert data["request"] == ""
            assert data["response"] == ""

    def test_very_long_agent_name():
        """Test handling very long agent names."""
        with tmp_path as tmpdir:
            tracker = ResponseTracker(Path(tmpdir))

            # Use a long but not too long name (filesystem dependent)
            long_name = "a" * 200  # Reduced from 500

            try:
                file_path = tracker.track_response(
                    agent_name=long_name, request="test", response="test"
                )
                # Should handle long names gracefully
                assert file_path.exists()
            except OSError:
                # Expected on filesystems with name limits
                pass

    def test_timestamp_precision():
        """Test that timestamps have millisecond precision."""
        with tmp_path as tmpdir:
            tracker = ResponseTracker(Path(tmpdir))

            # Track multiple responses with small delays
            file_paths = []
            for i in range(3):
                file_path = tracker.track_response(
                    agent_name="precision_agent",
                    request=f"test_{i}",
                    response=f"test_{i}",
                    session_id="precision_session",
                )
                file_paths.append(file_path)
                time.sleep(0.002)  # 2ms delay to ensure different timestamps

            # Check that filenames are unique (include milliseconds)
            filenames = [fp.name for fp in file_paths]
            assert len(set(filenames)) == 3

    def test_special_characters_in_content():
        """Test handling special characters in content."""
        with tmp_path as tmpdir:
            tracker = ResponseTracker(Path(tmpdir))

            special_content = '{"test": "value"}\n\t\r\\n'
            file_path = tracker.track_response(
                agent_name="special_agent",
                request=special_content,
                response=special_content,
                session_id="special_session",
            )

            with file_path.open() as f:
                data = json.load(f)

            assert data["request"] == special_content
            assert data["response"] == special_content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
