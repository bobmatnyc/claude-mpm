"""
Unit tests for RestartPolicy
==============================

Tests exponential backoff calculation, circuit breaker logic,
and restart history management.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from claude_mpm.services.core.models.restart import (CircuitBreakerState,
                                                     RestartConfig,
                                                     RestartHistory)
from claude_mpm.services.local_ops.restart_policy import RestartPolicy


class TestRestartPolicy:
    """Test suite for RestartPolicy."""

    @pytest.fixture
    def config(self):
        """Create default restart configuration."""
        return RestartConfig(
            max_attempts=5,
            initial_backoff_seconds=2.0,
            max_backoff_seconds=60.0,
            backoff_multiplier=2.0,
            circuit_breaker_threshold=3,
            circuit_breaker_window_seconds=300,
            circuit_breaker_reset_seconds=600,
        )

    @pytest.fixture
    def policy(self, config):
        """Create RestartPolicy instance."""
        policy = RestartPolicy(config)
        policy.initialize()
        return policy

    def test_initialization(self, policy, config):
        """Test restart policy initializes correctly."""
        assert policy.config == config
        assert isinstance(policy._history, dict)

    def test_should_restart_first_attempt(self, policy):
        """Test that first restart attempt is allowed."""
        deployment_id = "test-deployment"
        assert policy.should_restart(deployment_id) is True

    def test_should_restart_within_max_attempts(self, policy):
        """Test restart allowed when below max attempts."""
        deployment_id = "test-deployment"

        # Record 2 failed attempts (below max of 5, and below circuit breaker threshold of 3)
        for _ in range(2):
            policy.record_restart_attempt(deployment_id, success=False)

        # Should still allow restart
        assert policy.should_restart(deployment_id) is True

    def test_should_restart_blocked_at_max_attempts(self, policy):
        """Test restart blocked when max attempts reached."""
        deployment_id = "test-deployment"

        # Record 5 failed attempts (reaching max)
        for _ in range(5):
            policy.record_restart_attempt(deployment_id, success=False)

        # Should block restart
        assert policy.should_restart(deployment_id) is False

    def test_should_restart_blocked_circuit_breaker_open(self, policy):
        """Test restart blocked when circuit breaker is OPEN."""
        deployment_id = "test-deployment"

        # Create history with open circuit breaker
        history = policy._get_or_create_history(deployment_id)
        history.circuit_breaker_state = CircuitBreakerState.OPEN

        # Should block restart
        assert policy.should_restart(deployment_id) is False

    def test_should_restart_allowed_circuit_breaker_half_open(self, policy):
        """Test restart allowed when circuit breaker is HALF_OPEN."""
        deployment_id = "test-deployment"

        # Create history with half-open circuit breaker
        history = policy._get_or_create_history(deployment_id)
        history.circuit_breaker_state = CircuitBreakerState.HALF_OPEN

        # Should allow restart
        assert policy.should_restart(deployment_id) is True

    def test_calculate_backoff_first_attempt(self, policy):
        """Test backoff is 0 for first attempt."""
        deployment_id = "test-deployment"
        backoff = policy.calculate_backoff(deployment_id)
        assert backoff == 0.0

    def test_calculate_backoff_exponential(self, policy):
        """Test exponential backoff calculation."""
        deployment_id = "test-deployment"

        # Backoff is calculated BEFORE recording attempt, so:
        # - Before attempt 1: backoff = 0
        # - Before attempt 2: backoff = 2.0 * (2^0) = 2.0
        # - Before attempt 3: backoff = 2.0 * (2^1) = 4.0
        # - etc.
        expected_backoffs = [0.0, 2.0, 4.0, 8.0, 16.0, 32.0, 60.0]  # Capped at max

        for i, expected in enumerate(expected_backoffs):
            backoff = policy.calculate_backoff(deployment_id)
            assert (
                backoff == expected
            ), f"Attempt {i + 1}: expected {expected}, got {backoff}"

            # Record attempt to increment count
            policy.record_restart_attempt(deployment_id, success=False)

    def test_calculate_backoff_respects_max(self, policy):
        """Test backoff is capped at max_backoff_seconds."""
        deployment_id = "test-deployment"

        # Record many attempts
        for _ in range(10):
            policy.record_restart_attempt(deployment_id, success=False)

        # Backoff should be capped at max
        backoff = policy.calculate_backoff(deployment_id)
        assert backoff == policy.config.max_backoff_seconds

    def test_record_restart_attempt_success(self, policy):
        """Test recording successful restart attempt."""
        deployment_id = "test-deployment"

        # Record successful attempt
        policy.record_restart_attempt(deployment_id, success=True)

        # Verify attempt was recorded
        history = policy.get_history(deployment_id)
        assert history is not None
        assert history.get_attempt_count() == 1
        assert history.get_latest_attempt().success is True

    def test_record_restart_attempt_failure(self, policy):
        """Test recording failed restart attempt."""
        deployment_id = "test-deployment"
        failure_reason = "Health check failed"

        # Record failed attempt
        policy.record_restart_attempt(
            deployment_id, success=False, failure_reason=failure_reason
        )

        # Verify attempt was recorded
        history = policy.get_history(deployment_id)
        assert history.get_attempt_count() == 1
        assert history.get_latest_attempt().success is False
        assert history.get_latest_attempt().failure_reason == failure_reason

    def test_circuit_breaker_trips_after_threshold(self, policy):
        """Test circuit breaker trips after threshold failures."""
        deployment_id = "test-deployment"

        # Record failures to trip circuit breaker (threshold = 3)
        for _ in range(3):
            policy.record_restart_attempt(deployment_id, success=False)

        # Verify circuit breaker is OPEN
        state = policy.get_circuit_breaker_state(deployment_id)
        assert state == CircuitBreakerState.OPEN.value

    def test_circuit_breaker_resets_on_success(self, policy):
        """Test circuit breaker resets to CLOSED on successful restart."""
        deployment_id = "test-deployment"

        # Create history with half-open circuit breaker
        history = policy._get_or_create_history(deployment_id)
        history.circuit_breaker_state = CircuitBreakerState.HALF_OPEN

        # Record successful attempt
        policy.record_restart_attempt(deployment_id, success=True)

        # Verify circuit breaker is CLOSED
        state = policy.get_circuit_breaker_state(deployment_id)
        assert state == CircuitBreakerState.CLOSED.value

    def test_circuit_breaker_window_tracking(self, policy):
        """Test circuit breaker tracks failures within time window."""
        deployment_id = "test-deployment"

        # Record three failures quickly (within window)
        # This should trip the circuit breaker
        for _ in range(3):
            policy.record_restart_attempt(deployment_id, success=False)

        # Verify circuit breaker tripped
        state = policy.get_circuit_breaker_state(deployment_id)
        assert state == CircuitBreakerState.OPEN.value

    def test_circuit_breaker_window_expired(self, policy):
        """Test circuit breaker window expiration resets failure count."""
        deployment_id = "test-deployment"
        import time

        # Record first failure
        policy.record_restart_attempt(deployment_id, success=False)

        # Get history and manually expire the window
        history = policy._get_or_create_history(deployment_id)
        # Set window start to far in the past (window is 300s)
        history.last_failure_window_start = datetime.now(timezone.utc) - timedelta(
            seconds=400
        )

        # Record second failure (should start new window)
        policy.record_restart_attempt(deployment_id, success=False)

        # Verify circuit breaker is still CLOSED (window reset, only 1 failure in new window)
        state = policy.get_circuit_breaker_state(deployment_id)
        assert state == CircuitBreakerState.CLOSED.value

    def test_reset_restart_history(self, policy):
        """Test resetting restart history."""
        deployment_id = "test-deployment"

        # Record some attempts
        for _ in range(3):
            policy.record_restart_attempt(deployment_id, success=False)

        # Verify history exists
        assert policy.get_restart_attempt_count(deployment_id) == 3

        # Reset history
        policy.reset_restart_history(deployment_id)

        # Verify history is cleared
        assert policy.get_history(deployment_id) is None
        assert policy.get_restart_attempt_count(deployment_id) == 0

    def test_get_circuit_breaker_state(self, policy):
        """Test getting circuit breaker state."""
        deployment_id = "test-deployment"

        # Initially CLOSED
        assert (
            policy.get_circuit_breaker_state(deployment_id)
            == CircuitBreakerState.CLOSED.value
        )

        # Trip circuit breaker
        for _ in range(3):
            policy.record_restart_attempt(deployment_id, success=False)

        # Should be OPEN
        assert (
            policy.get_circuit_breaker_state(deployment_id)
            == CircuitBreakerState.OPEN.value
        )

    def test_get_restart_attempt_count(self, policy):
        """Test getting restart attempt count."""
        deployment_id = "test-deployment"

        # Initially 0
        assert policy.get_restart_attempt_count(deployment_id) == 0

        # Record attempts
        for i in range(5):
            policy.record_restart_attempt(deployment_id, success=False)
            assert policy.get_restart_attempt_count(deployment_id) == i + 1

    def test_get_history(self, policy):
        """Test getting restart history."""
        deployment_id = "test-deployment"

        # Initially None
        assert policy.get_history(deployment_id) is None

        # Record attempt
        policy.record_restart_attempt(deployment_id, success=False)

        # Should have history
        history = policy.get_history(deployment_id)
        assert history is not None
        assert isinstance(history, RestartHistory)
        assert history.deployment_id == deployment_id

    def test_consecutive_failures(self, policy):
        """Test tracking consecutive failures."""
        deployment_id = "test-deployment"

        # Record failures
        for _ in range(3):
            policy.record_restart_attempt(deployment_id, success=False)

        # Record success
        policy.record_restart_attempt(deployment_id, success=True)

        # Record more failures
        for _ in range(2):
            policy.record_restart_attempt(deployment_id, success=False)

        # Verify consecutive failures (should be 2)
        history = policy.get_history(deployment_id)
        assert history.get_consecutive_failures() == 2

    def test_thread_safety(self, policy):
        """Test that restart policy operations are thread-safe."""
        import threading

        deployment_id = "test-deployment"

        # Simulate concurrent restart attempts from multiple threads
        def record_attempt():
            policy.record_restart_attempt(deployment_id, success=False)

        threads = [threading.Thread(target=record_attempt) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Verify all attempts were counted
        assert policy.get_restart_attempt_count(deployment_id) == 10

    def test_backoff_multiplier(self):
        """Test custom backoff multiplier."""
        config = RestartConfig(
            max_attempts=10,
            initial_backoff_seconds=1.0,
            max_backoff_seconds=100.0,
            backoff_multiplier=3.0,  # Triple each time
            circuit_breaker_threshold=10,  # Prevent breaker from tripping
        )
        policy = RestartPolicy(config)
        policy.initialize()

        deployment_id = "test-deployment"

        # Test backoff with multiplier of 3
        expected_backoffs = [0.0, 1.0, 3.0, 9.0, 27.0, 81.0]

        for i, expected in enumerate(expected_backoffs):
            backoff = policy.calculate_backoff(deployment_id)
            assert backoff == expected

            policy.record_restart_attempt(deployment_id, success=False)

    def test_circuit_breaker_half_open_transition(self, policy):
        """Test circuit breaker transitions to HALF_OPEN after cooldown."""
        deployment_id = "test-deployment"

        # Trip circuit breaker
        for _ in range(3):
            policy.record_restart_attempt(deployment_id, success=False)

        # Verify OPEN
        assert (
            policy.get_circuit_breaker_state(deployment_id)
            == CircuitBreakerState.OPEN.value
        )

        # Get history and manually set window start to far in the past (reset period is 600s)
        history = policy._get_or_create_history(deployment_id)
        history.last_failure_window_start = datetime.now(timezone.utc) - timedelta(
            seconds=700
        )

        # Check if circuit breaker should reset
        policy._check_circuit_breaker_reset(history, datetime.now(timezone.utc))

        # Verify HALF_OPEN
        assert history.circuit_breaker_state == CircuitBreakerState.HALF_OPEN
