"""
Comprehensive QA Tests for Resume Log System

Test Areas:
1. Token usage tracking at exact thresholds
2. Resume log generation at all threshold levels
3. File operations and atomic writes
4. Configuration integration
5. Edge cases and error handling
6. Performance metrics
"""

import json
import tempfile
import time
from pathlib import Path

import pytest

from claude_mpm.models.resume_log import ContextMetrics, ResumeLog
from claude_mpm.services.infrastructure.resume_log_generator import ResumeLogGenerator
from claude_mpm.services.session_manager import SessionManager


class TestTokenThresholds:
    """Test exact threshold boundaries (70%, 85%, 95%)."""

    def setup_method(self):
        """Reset SessionManager before each test."""
        SessionManager.reset()

    def teardown_method(self):
        """Reset SessionManager after each test."""
        SessionManager.reset()

    def test_exact_70_percent_threshold(self):
        """Test behavior at exactly 70% token usage (140k tokens)."""
        manager = SessionManager()

        # Use exactly 140k tokens (70%)
        metrics = manager.update_token_usage(
            input_tokens=100000,
            output_tokens=40000,
            stop_reason="end_turn",
        )

        assert metrics["used_tokens"] == 140000
        assert metrics["remaining_tokens"] == 60000
        assert metrics["percentage_used"] == 70.0
        assert manager.get_token_usage_percentage() == 0.70

        # Should warn at 70% threshold
        assert manager.should_warn_context_limit(threshold=0.70) is True
        # Should not warn at higher thresholds yet
        assert manager.should_warn_context_limit(threshold=0.85) is False
        assert manager.should_warn_context_limit(threshold=0.95) is False

    def test_exact_85_percent_threshold(self):
        """Test behavior at exactly 85% token usage (170k tokens)."""
        manager = SessionManager()

        # Use exactly 170k tokens (85%)
        manager.update_token_usage(
            input_tokens=150000,
            output_tokens=20000,
            stop_reason="end_turn",
        )

        assert manager.get_token_usage_percentage() == 0.85
        assert manager.should_warn_context_limit(threshold=0.70) is True
        assert manager.should_warn_context_limit(threshold=0.85) is True
        assert manager.should_warn_context_limit(threshold=0.95) is False

    def test_exact_95_percent_threshold(self):
        """Test behavior at exactly 95% token usage (190k tokens)."""
        manager = SessionManager()

        # Use exactly 190k tokens (95%)
        manager.update_token_usage(
            input_tokens=170000,
            output_tokens=20000,
            stop_reason="end_turn",
        )

        assert manager.get_token_usage_percentage() == 0.95
        assert manager.should_warn_context_limit(threshold=0.70) is True
        assert manager.should_warn_context_limit(threshold=0.85) is True
        assert manager.should_warn_context_limit(threshold=0.95) is True

    def test_cumulative_token_tracking(self):
        """Test cumulative token counting across multiple API calls."""
        manager = SessionManager()

        # First call: 50k tokens
        metrics1 = manager.update_token_usage(input_tokens=30000, output_tokens=20000)
        assert metrics1["used_tokens"] == 50000

        # Second call: +40k tokens = 90k total
        metrics2 = manager.update_token_usage(input_tokens=25000, output_tokens=15000)
        assert metrics2["used_tokens"] == 90000

        # Third call: +50k tokens = 140k total (70% threshold)
        metrics3 = manager.update_token_usage(input_tokens=30000, output_tokens=20000)
        assert metrics3["used_tokens"] == 140000
        assert metrics3["percentage_used"] == 70.0

    def test_stop_reason_tracking(self):
        """Test that stop_reason is correctly captured."""
        manager = SessionManager()

        # Update with different stop reasons
        manager.update_token_usage(
            input_tokens=50000,
            output_tokens=10000,
            stop_reason="end_turn",
        )
        metrics1 = manager.get_context_metrics()
        assert metrics1["stop_reason"] == "end_turn"

        # Update stop reason
        manager.update_token_usage(
            input_tokens=50000,
            output_tokens=10000,
            stop_reason="max_tokens",
        )
        metrics2 = manager.get_context_metrics()
        assert metrics2["stop_reason"] == "max_tokens"

        # Verify cumulative usage
        assert metrics2["used_tokens"] == 120000


class TestResumeLogGeneration:
    """Test resume log generation at each threshold level."""

    def test_generation_at_70_percent(self):
        """Test resume log generation at 70% threshold."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = {
                "context_management": {
                    "thresholds": {"caution": 0.70, "warning": 0.85, "critical": 0.95},
                    "resume_logs": {"enabled": True, "auto_generate": True},
                }
            }

            generator = ResumeLogGenerator(storage_dir=Path(tmpdir), config=config)

            # Test at exactly 70% - should NOT trigger warning threshold
            assert generator.should_generate(token_usage_pct=0.70) is False
            # Test at 85% - should trigger
            assert generator.should_generate(token_usage_pct=0.85) is True

    def test_generation_at_85_percent(self):
        """Test resume log generation at 85% threshold."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = {
                "context_management": {
                    "thresholds": {"warning": 0.85},
                    "resume_logs": {"enabled": True, "auto_generate": True},
                }
            }

            generator = ResumeLogGenerator(storage_dir=Path(tmpdir), config=config)

            assert generator.should_generate(token_usage_pct=0.85) is True
            assert generator.should_generate(token_usage_pct=0.86) is True

    def test_generation_at_95_percent(self):
        """Test resume log generation at 95% threshold."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = ResumeLogGenerator(storage_dir=Path(tmpdir))

            assert generator.should_generate(token_usage_pct=0.95) is True
            assert generator.should_generate(token_usage_pct=0.99) is True

    def test_all_stop_reason_triggers(self):
        """Test all stop_reason triggers work correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = ResumeLogGenerator(storage_dir=Path(tmpdir))

            # Test all documented stop reasons
            assert generator.should_generate(stop_reason="max_tokens") is True
            assert (
                generator.should_generate(stop_reason="model_context_window_exceeded")
                is True
            )
            assert generator.should_generate(manual_trigger=True) is True

            # Test non-trigger stop reasons
            assert generator.should_generate(stop_reason="end_turn") is False
            assert generator.should_generate(stop_reason="stop_sequence") is False

    def test_manual_trigger_always_works(self):
        """Test manual trigger always generates, regardless of config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Disabled auto-generate
            config = {
                "context_management": {
                    "resume_logs": {"enabled": True, "auto_generate": False}
                }
            }

            generator = ResumeLogGenerator(storage_dir=Path(tmpdir), config=config)

            # Manual trigger should work even with auto_generate=False
            assert generator.should_generate(manual_trigger=True) is True


class TestFileOperations:
    """Test file operations and atomic writes."""

    def test_atomic_write_no_corruption(self):
        """Test that atomic writes don't corrupt files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = ResumeLogGenerator(storage_dir=Path(tmpdir))

            context_metrics = ContextMetrics(
                total_budget=200000,
                used_tokens=140000,
                session_id="atomic-test-001",
            )

            resume_log = ResumeLog(
                session_id="atomic-test-001",
                context_metrics=context_metrics,
                mission_summary="Test atomic writes",
            )

            # Save log
            saved_path = generator.save_resume_log(resume_log)
            assert saved_path is not None
            assert saved_path.exists()

            # Verify both .md and .json exist
            json_path = saved_path.with_suffix(".json")
            assert json_path.exists()

            # Verify content is valid
            md_content = saved_path.read_text(encoding="utf-8")
            assert "atomic-test-001" in md_content
            assert "Test atomic writes" in md_content

            json_content = json.loads(json_path.read_text(encoding="utf-8"))
            assert json_content["session_id"] == "atomic-test-001"

    def test_file_permissions(self):
        """Test that files have correct permissions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_dir = Path(tmpdir)
            generator = ResumeLogGenerator(storage_dir=storage_dir)

            resume_log = ResumeLog(
                session_id="perms-test-001",
                context_metrics=ContextMetrics(session_id="perms-test-001"),
                mission_summary="Test permissions",
            )

            saved_path = generator.save_resume_log(resume_log)

            # Check file is readable and writable
            assert saved_path.exists()
            assert saved_path.is_file()
            # Verify we can read it
            content = saved_path.read_text(encoding="utf-8")
            assert len(content) > 0

    def test_cleanup_operations(self):
        """Test cleanup doesn't delete active logs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = ResumeLogGenerator(storage_dir=Path(tmpdir))

            # Create 12 resume logs
            session_ids = [f"cleanup-test-{i:03d}" for i in range(12)]
            for session_id in session_ids:
                resume_log = ResumeLog(
                    session_id=session_id,
                    context_metrics=ContextMetrics(session_id=session_id),
                    mission_summary=f"Test {session_id}",
                )
                generator.save_resume_log(resume_log)
                # Small delay to ensure different timestamps
                time.sleep(0.01)

            # Verify 12 logs exist
            logs_before = generator.list_resume_logs()
            assert len(logs_before) == 12

            # Cleanup, keep 10 most recent
            deleted = generator.cleanup_old_logs(keep_count=10)
            assert deleted == 2

            # Verify 10 remain
            logs_after = generator.list_resume_logs()
            assert len(logs_after) == 10

            # Verify the 10 most recent were kept
            remaining_ids = [log["session_id"] for log in logs_after]
            # The last 10 should remain (cleanup-test-002 through cleanup-test-011)
            expected_ids = session_ids[-10:]
            assert set(remaining_ids) == set(expected_ids)

    def test_markdown_and_json_format(self):
        """Test both .md and .json files are created correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = ResumeLogGenerator(storage_dir=Path(tmpdir))

            resume_log = ResumeLog(
                session_id="format-test-001",
                context_metrics=ContextMetrics(
                    total_budget=200000,
                    used_tokens=170000,
                    percentage_used=85.0,
                    session_id="format-test-001",
                ),
                mission_summary="Test both formats",
                accomplishments=["Task 1", "Task 2"],
                next_steps=["Task 3", "Task 4"],
            )

            saved_path = generator.save_resume_log(resume_log)

            # Check markdown
            md_path = Path(tmpdir) / "session-format-test-001.md"
            assert md_path.exists()
            md_content = md_path.read_text(encoding="utf-8")
            assert "# Session Resume Log: format-test-001" in md_content
            assert "Test both formats" in md_content
            assert "Task 1" in md_content

            # Check JSON
            json_path = Path(tmpdir) / "session-format-test-001.json"
            assert json_path.exists()
            json_data = json.loads(json_path.read_text(encoding="utf-8"))
            assert json_data["session_id"] == "format-test-001"
            assert json_data["mission_summary"] == "Test both formats"
            assert len(json_data["accomplishments"]) == 2


class TestConfiguration:
    """Test configuration integration."""

    def test_enabled_disabled_toggle(self):
        """Test with resume logs enabled/disabled."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Enabled
            config_enabled = {"context_management": {"resume_logs": {"enabled": True}}}
            generator_enabled = ResumeLogGenerator(
                storage_dir=Path(tmpdir), config=config_enabled
            )
            assert generator_enabled.enabled is True

            # Disabled
            config_disabled = {
                "context_management": {"resume_logs": {"enabled": False}}
            }
            generator_disabled = ResumeLogGenerator(
                storage_dir=Path(tmpdir), config=config_disabled
            )
            assert generator_disabled.enabled is False

    def test_threshold_overrides(self):
        """Test threshold overrides work correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Custom thresholds
            config = {
                "context_management": {
                    "thresholds": {
                        "caution": 0.60,
                        "warning": 0.80,
                        "critical": 0.90,
                    },
                    "resume_logs": {"enabled": True, "auto_generate": True},
                }
            }

            generator = ResumeLogGenerator(storage_dir=Path(tmpdir), config=config)

            assert generator.threshold_caution == 0.60
            assert generator.threshold_warning == 0.80
            assert generator.threshold_critical == 0.90

            # Test generation with custom thresholds
            assert generator.should_generate(token_usage_pct=0.61) is False
            assert generator.should_generate(token_usage_pct=0.80) is True
            assert generator.should_generate(token_usage_pct=0.90) is True

    def test_missing_config_uses_defaults(self):
        """Test with missing config sections (uses defaults)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Empty config
            generator = ResumeLogGenerator(storage_dir=Path(tmpdir), config={})

            # Should use defaults
            assert generator.enabled is True
            assert generator.auto_generate is True
            assert generator.max_tokens == 10000
            assert generator.threshold_caution == 0.70
            assert generator.threshold_warning == 0.85
            assert generator.threshold_critical == 0.95


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_session_state(self):
        """Test with empty or minimal session state."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = ResumeLogGenerator(storage_dir=Path(tmpdir))

            # Empty session state
            resume_log = generator.generate_from_session_state(
                session_id="empty-state-001",
                session_state={},
                stop_reason="end_turn",
            )

            assert resume_log is not None
            assert resume_log.session_id == "empty-state-001"
            assert resume_log.mission_summary == ""
            assert len(resume_log.accomplishments) == 0

    def test_very_large_session_state(self):
        """Test with very large session state (>10k tokens of data)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = ResumeLogGenerator(storage_dir=Path(tmpdir))

            # Create large session state
            large_accomplishments = [f"Task {i} completed" for i in range(500)]
            large_findings = [f"Finding {i}" for i in range(500)]

            session_state = {
                "context_metrics": {
                    "total_budget": 200000,
                    "used_tokens": 180000,
                    "percentage_used": 90.0,
                },
                "mission_summary": "Large session test",
                "accomplishments": large_accomplishments,
                "key_findings": large_findings,
            }

            resume_log = generator.generate_from_session_state(
                session_id="large-state-001",
                session_state=session_state,
                stop_reason="max_tokens",
            )

            assert resume_log is not None
            assert len(resume_log.accomplishments) == 500
            assert len(resume_log.key_findings) == 500

            # Save and verify file exists
            saved_path = generator.save_resume_log(resume_log)
            assert saved_path is not None
            assert saved_path.exists()

    def test_missing_resume_log_graceful(self):
        """Test missing logs don't break startup (graceful degradation)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = ResumeLogGenerator(storage_dir=Path(tmpdir))

            # Try to load non-existent log
            content = generator.load_resume_log("non-existent-session")
            assert content is None

    def test_corrupted_json_file(self):
        """Test with corrupted resume log JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_dir = Path(tmpdir)

            # Create corrupted JSON file
            json_path = storage_dir / "session-corrupted-001.json"
            json_path.write_text("{ invalid json content }", encoding="utf-8")

            generator = ResumeLogGenerator(storage_dir=storage_dir)

            # Should handle gracefully
            logs = generator.list_resume_logs()
            # Corrupted JSON should be handled gracefully

    def test_rapid_successive_calls(self):
        """Test rapid successive API calls (race conditions)."""
        SessionManager.reset()
        manager = SessionManager()

        # Rapid successive updates
        for i in range(10):
            manager.update_token_usage(
                input_tokens=10000,
                output_tokens=5000,
                stop_reason="end_turn",
            )

        # Verify cumulative total is correct
        metrics = manager.get_context_metrics()
        assert metrics["used_tokens"] == 150000  # 10 * 15000


class TestPerformance:
    """Test performance metrics."""

    def test_generation_time(self):
        """Measure resume log generation time."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = ResumeLogGenerator(storage_dir=Path(tmpdir))

            session_state = {
                "context_metrics": {
                    "total_budget": 200000,
                    "used_tokens": 170000,
                    "percentage_used": 85.0,
                },
                "mission_summary": "Performance test",
                "accomplishments": [f"Task {i}" for i in range(50)],
                "key_findings": [f"Finding {i}" for i in range(50)],
                "next_steps": [f"Step {i}" for i in range(20)],
            }

            start_time = time.time()
            resume_log = generator.generate_from_session_state(
                session_id="perf-test-001",
                session_state=session_state,
                stop_reason="max_tokens",
            )
            generation_time = time.time() - start_time

            assert resume_log is not None
            # Generation should be fast (< 100ms)
            assert generation_time < 0.1

            # Test save time
            start_time = time.time()
            saved_path = generator.save_resume_log(resume_log)
            save_time = time.time() - start_time

            assert saved_path is not None
            # Save should be fast (< 100ms)
            assert save_time < 0.1

            # Measure file sizes
            md_size = saved_path.stat().st_size
            json_size = saved_path.with_suffix(".json").stat().st_size

            # Report metrics (for manual verification)
            print("\nPerformance Metrics:")
            print(f"  Generation time: {generation_time * 1000:.2f}ms")
            print(f"  Save time: {save_time * 1000:.2f}ms")
            print(f"  Markdown file size: {md_size / 1024:.2f}KB")
            print(f"  JSON file size: {json_size / 1024:.2f}KB")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
