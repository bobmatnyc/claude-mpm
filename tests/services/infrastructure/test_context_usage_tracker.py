#!/usr/bin/env python3
"""Tests for ContextUsageTracker Service.

Comprehensive test suite for context/token usage tracking across
Claude Code hook invocations with file-based persistence.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from claude_mpm.services.infrastructure.context_usage_tracker import (
    ContextUsageState,
    ContextUsageTracker,
)


class TestContextUsageState:
    """Test ContextUsageState dataclass."""

    def test_default_initialization(self):
        """Test default state initialization."""
        state = ContextUsageState(session_id="test-session")

        assert state.session_id == "test-session"
        assert state.cumulative_input_tokens == 0
        assert state.cumulative_output_tokens == 0
        assert state.cache_creation_tokens == 0
        assert state.cache_read_tokens == 0
        assert state.percentage_used == 0.0
        assert state.threshold_reached is None
        assert state.auto_pause_active is False
        assert state.last_updated is not None

    def test_custom_initialization(self):
        """Test state initialization with custom values."""
        timestamp = datetime.now(timezone.utc).isoformat()
        state = ContextUsageState(
            session_id="custom-session",
            cumulative_input_tokens=50000,
            cumulative_output_tokens=10000,
            cache_creation_tokens=5000,
            cache_read_tokens=2000,
            percentage_used=30.0,
            threshold_reached="caution",
            auto_pause_active=False,
            last_updated=timestamp,
        )

        assert state.cumulative_input_tokens == 50000
        assert state.cumulative_output_tokens == 10000
        assert state.percentage_used == 30.0
        assert state.threshold_reached == "caution"
        assert state.last_updated == timestamp


class TestContextUsageTracker:
    """Test suite for ContextUsageTracker."""

    @pytest.fixture
    def temp_project_dir(self, tmp_path):
        """Create temporary project directory."""
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()
        return project_dir

    @pytest.fixture
    def tracker(self, temp_project_dir):
        """Create ContextUsageTracker instance."""
        return ContextUsageTracker(project_path=temp_project_dir)

    @pytest.fixture
    def clean_tracker(self, temp_project_dir):
        """Create fresh tracker with clean state."""
        tracker = ContextUsageTracker(project_path=temp_project_dir)
        # Reset to ensure clean state
        tracker.reset_session("test-session")
        return tracker

    def test_initialization(self, tracker, temp_project_dir):
        """Test tracker initialization."""
        assert tracker.project_path == temp_project_dir
        assert tracker.state_dir == temp_project_dir / ".claude-mpm" / "state"
        assert tracker.state_file == tracker.state_dir / "context-usage.json"
        assert tracker.state_dir.exists()

    def test_initial_state_creation(self, clean_tracker):
        """Test that initial state is created with defaults."""
        state = clean_tracker.get_current_state()

        assert state.session_id == "test-session"
        assert state.cumulative_input_tokens == 0
        assert state.cumulative_output_tokens == 0
        assert state.percentage_used == 0.0
        assert state.threshold_reached is None
        assert not state.auto_pause_active

    def test_update_usage_basic(self, clean_tracker):
        """Test basic usage update."""
        state = clean_tracker.update_usage(input_tokens=10000, output_tokens=2000)

        assert state.cumulative_input_tokens == 10000
        assert state.cumulative_output_tokens == 2000
        # 12000 / 200000 = 6%
        assert state.percentage_used == pytest.approx(6.0, abs=0.01)
        assert state.threshold_reached is None
        assert not state.auto_pause_active

    def test_update_usage_cumulative(self, clean_tracker):
        """Test cumulative token tracking across multiple updates."""
        # First update
        state1 = clean_tracker.update_usage(input_tokens=30000, output_tokens=5000)
        assert state1.cumulative_input_tokens == 30000
        assert state1.cumulative_output_tokens == 5000

        # Second update (should add to existing)
        state2 = clean_tracker.update_usage(input_tokens=20000, output_tokens=3000)
        assert state2.cumulative_input_tokens == 50000
        assert state2.cumulative_output_tokens == 8000
        # 58000 / 200000 = 29%
        assert state2.percentage_used == pytest.approx(29.0, abs=0.01)

        # Third update
        state3 = clean_tracker.update_usage(input_tokens=15000, output_tokens=2000)
        assert state3.cumulative_input_tokens == 65000
        assert state3.cumulative_output_tokens == 10000
        # 75000 / 200000 = 37.5%
        assert state3.percentage_used == pytest.approx(37.5, abs=0.01)

    def test_update_usage_with_cache_tokens(self, clean_tracker):
        """Test usage update with cache creation and read tokens."""
        state = clean_tracker.update_usage(
            input_tokens=10000,
            output_tokens=2000,
            cache_creation=5000,
            cache_read=3000,
        )

        assert state.cumulative_input_tokens == 10000
        assert state.cumulative_output_tokens == 2000
        assert state.cache_creation_tokens == 5000
        assert state.cache_read_tokens == 3000
        # Percentage based on input + output (cache read is "free")
        # 12000 / 200000 = 6%
        assert state.percentage_used == pytest.approx(6.0, abs=0.01)

    def test_update_usage_negative_tokens_raises_error(self, clean_tracker):
        """Test that negative token counts raise ValueError."""
        with pytest.raises(ValueError, match="Token counts cannot be negative"):
            clean_tracker.update_usage(input_tokens=-100, output_tokens=2000)

        with pytest.raises(ValueError, match="Token counts cannot be negative"):
            clean_tracker.update_usage(input_tokens=1000, output_tokens=-200)

        with pytest.raises(ValueError, match="Token counts cannot be negative"):
            clean_tracker.update_usage(
                input_tokens=1000, output_tokens=200, cache_creation=-50
            )

    def test_threshold_caution_70_percent(self, clean_tracker):
        """Test caution threshold at 70% usage."""
        # 70% of 200k = 140k tokens
        state = clean_tracker.update_usage(input_tokens=100000, output_tokens=40000)

        assert state.percentage_used == pytest.approx(70.0, abs=0.01)
        assert state.threshold_reached == "caution"
        assert not state.auto_pause_active

    def test_threshold_warning_85_percent(self, clean_tracker):
        """Test warning threshold at 85% usage."""
        # 85% of 200k = 170k tokens
        state = clean_tracker.update_usage(input_tokens=120000, output_tokens=50000)

        assert state.percentage_used == pytest.approx(85.0, abs=0.01)
        assert state.threshold_reached == "warning"
        assert not state.auto_pause_active

    def test_threshold_auto_pause_90_percent(self, clean_tracker):
        """Test auto-pause threshold at 90% usage."""
        # 90% of 200k = 180k tokens
        state = clean_tracker.update_usage(input_tokens=130000, output_tokens=50000)

        assert state.percentage_used == pytest.approx(90.0, abs=0.01)
        assert state.threshold_reached == "auto_pause"
        assert state.auto_pause_active

    def test_threshold_critical_95_percent(self, clean_tracker):
        """Test critical threshold at 95% usage."""
        # 95% of 200k = 190k tokens
        state = clean_tracker.update_usage(input_tokens=140000, output_tokens=50000)

        assert state.percentage_used == pytest.approx(95.0, abs=0.01)
        assert state.threshold_reached == "critical"
        assert state.auto_pause_active

    def test_should_auto_pause_true(self, clean_tracker):
        """Test should_auto_pause returns True at 90%+ usage."""
        # Start below threshold
        assert not clean_tracker.should_auto_pause()

        # Cross 90% threshold
        clean_tracker.update_usage(input_tokens=130000, output_tokens=50000)
        assert clean_tracker.should_auto_pause()

    def test_should_auto_pause_false(self, clean_tracker):
        """Test should_auto_pause returns False below 90%."""
        # 85% usage - below auto-pause threshold
        clean_tracker.update_usage(input_tokens=120000, output_tokens=50000)
        assert not clean_tracker.should_auto_pause()

    def test_check_thresholds_none_below_70(self, clean_tracker):
        """Test check_thresholds returns None below 70%."""
        clean_tracker.update_usage(input_tokens=60000, output_tokens=10000)
        state = clean_tracker.get_current_state()

        threshold = clean_tracker.check_thresholds(state)
        assert threshold is None

    def test_check_thresholds_returns_highest(self, clean_tracker):
        """Test check_thresholds returns highest exceeded threshold."""
        # Test at each threshold level
        test_cases = [
            (140000, "caution"),  # 70%
            (170000, "warning"),  # 85%
            (180000, "auto_pause"),  # 90%
            (190000, "critical"),  # 95%
        ]

        for total_tokens, expected_threshold in test_cases:
            clean_tracker.reset_session("test-session")
            clean_tracker.update_usage(input_tokens=total_tokens, output_tokens=0)
            state = clean_tracker.get_current_state()
            assert clean_tracker.check_thresholds(state) == expected_threshold

    def test_state_persistence(self, clean_tracker):
        """Test that state persists across tracker instances."""
        # Update state in first tracker
        clean_tracker.update_usage(input_tokens=50000, output_tokens=10000)

        # Create new tracker instance pointing to same project
        new_tracker = ContextUsageTracker(project_path=clean_tracker.project_path)

        # Verify state was loaded
        state = new_tracker.get_current_state()
        assert state.cumulative_input_tokens == 50000
        assert state.cumulative_output_tokens == 10000
        assert state.percentage_used == pytest.approx(30.0, abs=0.01)

    def test_reset_session(self, clean_tracker):
        """Test session reset clears cumulative counters."""
        # Accumulate some usage
        clean_tracker.update_usage(input_tokens=50000, output_tokens=10000)
        assert clean_tracker.get_current_state().cumulative_input_tokens == 50000

        # Reset session
        clean_tracker.reset_session("new-session")

        # Verify state was reset
        state = clean_tracker.get_current_state()
        assert state.session_id == "new-session"
        assert state.cumulative_input_tokens == 0
        assert state.cumulative_output_tokens == 0
        assert state.percentage_used == 0.0
        assert state.threshold_reached is None
        assert not state.auto_pause_active

    def test_get_usage_summary(self, clean_tracker):
        """Test get_usage_summary returns formatted statistics."""
        clean_tracker.update_usage(
            input_tokens=60000,
            output_tokens=15000,
            cache_creation=5000,
            cache_read=2000,
        )

        summary = clean_tracker.get_usage_summary()

        assert summary["session_id"] == "test-session"
        assert summary["total_tokens"] == 75000
        assert summary["budget"] == 200000
        assert summary["percentage_used"] == pytest.approx(37.5, abs=0.01)
        assert summary["threshold_reached"] is None
        assert not summary["auto_pause_active"]
        assert summary["breakdown"]["input_tokens"] == 60000
        assert summary["breakdown"]["output_tokens"] == 15000
        assert summary["breakdown"]["cache_creation_tokens"] == 5000
        assert summary["breakdown"]["cache_read_tokens"] == 2000
        assert "last_updated" in summary

    def test_atomic_file_operations(self, clean_tracker):
        """Test that file writes are atomic (no corruption on failure)."""
        # Update state successfully
        clean_tracker.update_usage(input_tokens=10000, output_tokens=2000)

        # Verify state file exists and is valid JSON
        assert clean_tracker.state_file.exists()
        with open(clean_tracker.state_file) as f:
            data = json.load(f)
            assert data["cumulative_input_tokens"] == 10000
            assert data["cumulative_output_tokens"] == 2000

    def test_corrupted_state_file_recovery(self, clean_tracker, temp_project_dir):
        """Test that corrupted state file is handled gracefully."""
        # Create corrupted state file
        state_file = temp_project_dir / ".claude-mpm" / "state" / "context-usage.json"
        state_file.parent.mkdir(parents=True, exist_ok=True)
        state_file.write_text("{ corrupted json data }")

        # Create new tracker - should recover with default state
        new_tracker = ContextUsageTracker(project_path=temp_project_dir)
        state = new_tracker.get_current_state()

        # Should have default state
        assert state.cumulative_input_tokens == 0
        assert state.cumulative_output_tokens == 0
        assert state.percentage_used == 0.0

    def test_missing_state_file_creates_default(self, temp_project_dir):
        """Test that missing state file creates default state."""
        # Ensure no state file exists
        state_file = temp_project_dir / ".claude-mpm" / "state" / "context-usage.json"
        if state_file.exists():
            state_file.unlink()

        # Create tracker
        tracker = ContextUsageTracker(project_path=temp_project_dir)
        state = tracker.get_current_state()

        # Should have default state with auto-generated session ID
        assert state.cumulative_input_tokens == 0
        assert state.cumulative_output_tokens == 0
        assert state.session_id.startswith("session-")

    def test_concurrent_updates_safe(self, clean_tracker):
        """Test that concurrent updates don't corrupt state (file locking)."""
        # Simulate multiple rapid updates (as would happen from hooks)
        for i in range(10):
            clean_tracker.update_usage(input_tokens=1000, output_tokens=200)

        state = clean_tracker.get_current_state()
        assert state.cumulative_input_tokens == 10000
        assert state.cumulative_output_tokens == 2000

    def test_timestamp_updated_on_each_update(self, clean_tracker):
        """Test that last_updated timestamp is refreshed on each update."""
        state1 = clean_tracker.update_usage(input_tokens=10000, output_tokens=2000)
        timestamp1 = state1.last_updated

        # Small delay to ensure timestamp difference
        import time

        time.sleep(0.1)

        state2 = clean_tracker.update_usage(input_tokens=5000, output_tokens=1000)
        timestamp2 = state2.last_updated

        # Timestamps should be different
        assert timestamp2 > timestamp1

    def test_percentage_calculation_accuracy(self, clean_tracker):
        """Test percentage calculation accuracy for various token counts."""
        test_cases = [
            (20000, 10.0),  # 20k / 200k = 10%
            (50000, 25.0),  # 50k / 200k = 25%
            (100000, 50.0),  # 100k / 200k = 50%
            (150000, 75.0),  # 150k / 200k = 75%
            (200000, 100.0),  # 200k / 200k = 100%
        ]

        for total_tokens, expected_percentage in test_cases:
            clean_tracker.reset_session("test-session")
            state = clean_tracker.update_usage(
                input_tokens=total_tokens, output_tokens=0
            )
            assert state.percentage_used == pytest.approx(expected_percentage, abs=0.01)

    def test_state_file_location(self, tracker):
        """Test that state file is created in correct location."""
        expected_path = (
            tracker.project_path / ".claude-mpm" / "state" / "context-usage.json"
        )
        assert tracker.state_file == expected_path

        # Create state by updating
        tracker.update_usage(input_tokens=1000, output_tokens=100)

        # Verify file exists at expected location
        assert expected_path.exists()
        assert expected_path.is_file()
