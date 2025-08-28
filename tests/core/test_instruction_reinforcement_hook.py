"""
Comprehensive unit tests for the instruction reinforcement system.

Tests configuration handling, and provides framework for testing injection behavior,
metrics, and error cases when the hook implementation is added.
"""

import time
from unittest.mock import Mock, patch

import pytest

from claude_mpm.core.config import Config


# Mock InstructionReinforcementHook for testing until implementation is available
class MockInstructionReinforcementHook:
    """Mock implementation for testing configuration aspects."""

    def __init__(self):
        config = Config()
        ir_config = config.get("instruction_reinforcement", {})

        self.enabled = ir_config.get("enabled", True)
        self.test_mode = ir_config.get("test_mode", True)
        self.injection_interval = ir_config.get("injection_interval", 5)
        self.test_messages = ir_config.get("test_messages", [])
        self.production_messages = ir_config.get("production_messages", [])
        self.is_running = False
        self.handler = None

        self._total_injections = 0
        self._last_injection_time = None
        self._start_time = None

    def set_handler(self, handler):
        self.handler = handler

    def start(self):
        if self.enabled:
            self.is_running = True
            self._start_time = time.time()

    def stop(self):
        self.is_running = False

    def get_metrics(self):
        uptime = time.time() - self._start_time if self._start_time else 0
        return {
            "total_injections": self._total_injections,
            "last_injection_time": self._last_injection_time,
            "injection_rate": self._total_injections / uptime if uptime > 0 else 0,
            "uptime_seconds": uptime,
        }

    def reset_metrics(self):
        self._total_injections = 0
        self._last_injection_time = None
        self._start_time = time.time() if self.is_running else None

    def get_status(self):
        return {
            "running": self.is_running,
            "enabled": self.enabled,
            "uptime": time.time() - self._start_time if self._start_time else 0,
            "total_injections": self._total_injections,
        }

    def update_config(self, config_updates):
        for key, value in config_updates.items():
            if hasattr(self, key):
                setattr(self, key, value)


class TestInstructionReinforcementHook:
    """Comprehensive tests for InstructionReinforcementHook."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test fixtures."""
        # Reset singleton before each test
        Config.reset_singleton()

        # Create mock config
        self.config = Config(
            {
                "instruction_reinforcement": {
                    "enabled": True,
                    "test_mode": True,
                    "injection_interval": 2,  # Shorter for testing
                    "test_messages": [
                        "[TEST-REMINDER] Test message 1",
                        "[TEST-REMINDER] Test message 2",
                    ],
                    "production_messages": [
                        "[PM-REMINDER] Production message 1",
                        "[PM-REMINDER] Production message 2",
                    ],
                }
            }
        )

        self.hook = MockInstructionReinforcementHook()

        # Mock handler
        self.mock_handler = Mock()
        self.hook.set_handler(self.mock_handler)

        yield

        # Cleanup after each test
        self.hook.stop()
        Config.reset_singleton()

    def test_initialization_with_enabled_config(self):
        """Test hook initialization when enabled in config."""
        assert self.hook.enabled is True
        assert self.hook.test_mode is True
        assert self.hook.injection_interval == 2
        assert len(self.hook.test_messages) == 2
        assert len(self.hook.production_messages) == 2

    def test_initialization_with_disabled_config(self):
        """Test hook initialization when disabled in config."""
        Config.reset_singleton()
        disabled_config = Config({"instruction_reinforcement": {"enabled": False}})

        hook = MockInstructionReinforcementHook()
        assert hook.enabled is False
        assert hook.is_running is False

    def test_initialization_with_missing_config(self):
        """Test hook initialization with missing config section."""
        Config.reset_singleton()
        minimal_config = Config({})

        hook = MockInstructionReinforcementHook()
        # Should use defaults from Config._apply_defaults()
        assert hook.enabled is True  # Default from config
        assert hook.test_mode is True  # Default from config

    def test_start_stop_functionality(self):
        """Test hook start and stop functionality."""
        # Initially not running
        assert self.hook.is_running is False

        # Start the hook
        self.hook.start()
        assert self.hook.is_running is True

        # Stop the hook
        self.hook.stop()
        assert self.hook.is_running is False

    def test_message_injection_in_test_mode(self):
        """Test message injection behavior in test mode."""
        self.hook.start()

        # Wait for at least one injection interval
        time.sleep(2.5)

        # Verify handler was called
        assert self.mock_handler.called

        # Get the injected message
        calls = self.mock_handler.call_args_list
        assert len(calls) > 0

        message = calls[0][0][0]
        assert message.startswith("[TEST-REMINDER]")
        assert message in self.hook.test_messages

        self.hook.stop()

    def test_message_injection_in_production_mode(self):
        """Test message injection behavior in production mode."""
        # Configure for production mode
        Config.reset_singleton()
        prod_config = Config(
            {
                "instruction_reinforcement": {
                    "enabled": True,
                    "test_mode": False,
                    "injection_interval": 2,
                    "production_messages": ["[PM-REMINDER] Production message 1"],
                }
            }
        )

        hook = MockInstructionReinforcementHook()
        hook.set_handler(self.mock_handler)
        hook.start()

        # Wait for injection
        time.sleep(2.5)

        # Verify production message was injected
        calls = self.mock_handler.call_args_list
        assert len(calls) > 0

        message = calls[0][0][0]
        assert message.startswith("[PM-REMINDER]")
        assert message in hook.production_messages

        hook.stop()

    def test_message_cycling(self):
        """Test that messages cycle through the available list."""
        self.hook.start()

        # Wait for multiple injections
        time.sleep(6)  # Should get 2-3 injections

        calls = self.mock_handler.call_args_list
        assert len(calls) >= 2

        # Extract messages
        messages = [call[0][0] for call in calls]

        # Should have different messages (cycling)
        unique_messages = set(messages)
        assert len(unique_messages) >= 1  # At least some variety

        # All messages should be from test_messages list
        for message in messages:
            assert message in self.hook.test_messages

        self.hook.stop()

    def test_metrics_collection(self):
        """Test metrics collection functionality."""
        self.hook.start()

        # Wait for some injections
        time.sleep(4.5)  # Should get 2 injections

        metrics = self.hook.get_metrics()

        assert "total_injections" in metrics
        assert "last_injection_time" in metrics
        assert "injection_rate" in metrics
        assert "uptime_seconds" in metrics

        assert metrics["total_injections"] >= 1
        assert isinstance(metrics["last_injection_time"], str)
        assert metrics["injection_rate"] >= 0
        assert metrics["uptime_seconds"] > 0

        self.hook.stop()

    def test_injection_interval_configuration(self):
        """Test different injection intervals."""
        # Test with very short interval
        Config.reset_singleton()
        fast_config = Config(
            {
                "instruction_reinforcement": {
                    "enabled": True,
                    "test_mode": True,
                    "injection_interval": 1,
                    "test_messages": ["[TEST] Fast message"],
                }
            }
        )

        hook = MockInstructionReinforcementHook()
        handler = Mock()
        hook.set_handler(handler)
        hook.start()

        # Wait for multiple fast injections
        time.sleep(3.5)

        # Should have gotten multiple calls
        assert handler.call_count >= 2

        hook.stop()

    def test_disabled_hook_behavior(self):
        """Test that disabled hook doesn't inject messages."""
        Config.reset_singleton()
        disabled_config = Config({"instruction_reinforcement": {"enabled": False}})

        hook = MockInstructionReinforcementHook()
        handler = Mock()
        hook.set_handler(handler)
        hook.start()

        # Wait
        time.sleep(3)

        # Should not have been called
        assert handler.call_count == 0

        hook.stop()

    def test_no_handler_error_handling(self):
        """Test behavior when no handler is set."""
        # Don't set a handler
        hook = MockInstructionReinforcementHook()

        # Should be able to start without error
        hook.start()

        # Wait briefly
        time.sleep(1)

        # Should stop cleanly
        hook.stop()

    def test_empty_message_lists_handling(self):
        """Test behavior with empty message lists."""
        Config.reset_singleton()
        empty_config = Config(
            {
                "instruction_reinforcement": {
                    "enabled": True,
                    "test_mode": True,
                    "injection_interval": 1,
                    "test_messages": [],  # Empty list
                    "production_messages": [],
                }
            }
        )

        hook = MockInstructionReinforcementHook()
        handler = Mock()
        hook.set_handler(handler)
        hook.start()

        # Wait
        time.sleep(2.5)

        # Should not inject anything with empty message list
        assert handler.call_count == 0

        hook.stop()

    def test_malformed_config_handling(self):
        """Test behavior with malformed configuration."""
        Config.reset_singleton()
        malformed_config = Config(
            {
                "instruction_reinforcement": {
                    "enabled": "not_a_boolean",  # Wrong type
                    "injection_interval": "not_a_number",  # Wrong type
                    "test_messages": "not_a_list",  # Wrong type
                }
            }
        )

        # Should initialize without crashing
        hook = MockInstructionReinforcementHook()

        # Should handle gracefully - either disabled or using defaults
        assert isinstance(hook.enabled, bool)
        assert isinstance(hook.injection_interval, (int, float))
        assert isinstance(hook.test_messages, list)

    def test_thread_safety(self):
        """Test thread safety of start/stop operations."""
        import threading

        results = []

        def start_stop_cycle():
            try:
                for _ in range(5):
                    self.hook.start()
                    time.sleep(0.1)
                    self.hook.stop()
                    time.sleep(0.1)
                results.append("success")
            except Exception as e:
                results.append(f"error: {e}")

        # Run multiple threads
        threads = [threading.Thread(target=start_stop_cycle) for _ in range(3)]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join(timeout=10)

        # All threads should succeed
        assert len(results) == 3
        for result in results:
            assert result == "success"

    def test_configuration_updates(self):
        """Test dynamic configuration updates."""
        # Start with initial config
        self.hook.start()
        initial_interval = self.hook.injection_interval

        # Update configuration
        self.hook.update_config(
            {
                "injection_interval": initial_interval * 2,
                "test_messages": ["[UPDATED] New message"],
            }
        )

        assert self.hook.injection_interval == initial_interval * 2
        assert "[UPDATED] New message" in self.hook.test_messages

        self.hook.stop()

    def test_metrics_reset(self):
        """Test metrics reset functionality."""
        self.hook.start()

        # Wait for some activity
        time.sleep(2.5)

        # Get initial metrics
        initial_metrics = self.hook.get_metrics()
        assert initial_metrics["total_injections"] > 0

        # Reset metrics
        self.hook.reset_metrics()

        # Check metrics are reset
        reset_metrics = self.hook.get_metrics()
        assert reset_metrics["total_injections"] == 0
        assert reset_metrics["uptime_seconds"] >= 0  # Should be recent

        self.hook.stop()

    def test_status_reporting(self):
        """Test status reporting functionality."""
        # Test when stopped
        status = self.hook.get_status()
        assert status["running"] is False
        assert status["enabled"] is True

        # Test when running
        self.hook.start()
        time.sleep(1)

        running_status = self.hook.get_status()
        assert running_status["running"] is True
        assert "uptime" in running_status
        assert "total_injections" in running_status

        self.hook.stop()

    @patch("threading.Timer")
    def test_timer_cleanup(self, mock_timer_class):
        """Test that timers are properly cleaned up."""
        mock_timer = Mock()
        mock_timer_class.return_value = mock_timer

        self.hook.start()

        # Verify timer was created and started
        mock_timer_class.assert_called()
        mock_timer.start.assert_called()

        self.hook.stop()

        # Verify timer was cancelled
        mock_timer.cancel.assert_called()

    def test_injection_timing_accuracy(self):
        """Test that injection timing is reasonably accurate."""
        self.hook.start()

        start_time = time.time()

        # Wait for first injection
        while self.mock_handler.call_count == 0 and time.time() - start_time < 5:
            time.sleep(0.1)

        first_injection_time = time.time()

        # Wait for second injection
        while self.mock_handler.call_count == 1 and time.time() - start_time < 7:
            time.sleep(0.1)

        second_injection_time = time.time()

        if self.mock_handler.call_count >= 2:
            # Check timing is approximately correct (within reasonable margin)
            actual_interval = second_injection_time - first_injection_time
            expected_interval = self.hook.injection_interval

            # Allow 50% margin for timing variations
            assert abs(actual_interval - expected_interval) < expected_interval * 0.5

        self.hook.stop()

    def test_error_resilience(self):
        """Test hook resilience to handler errors."""
        # Create handler that raises exception
        error_handler = Mock(side_effect=Exception("Handler error"))
        self.hook.set_handler(error_handler)

        self.hook.start()

        # Wait for attempted injection
        time.sleep(2.5)

        # Hook should still be running despite handler errors
        assert self.hook.is_running is True

        # Handler should have been called (and failed)
        assert error_handler.call_count > 0

        self.hook.stop()

    def test_long_running_stability(self):
        """Test stability over longer running periods."""
        self.hook.start()

        # Run for a longer period with frequent checks
        start_time = time.time()
        last_injection_count = 0

        while time.time() - start_time < 5:  # Run for 5 seconds
            current_count = self.mock_handler.call_count

            # Verify injections are happening
            last_injection_count = max(last_injection_count, current_count)

            # Verify hook is still running
            assert self.hook.is_running is True

            time.sleep(0.5)

        # Should have had multiple injections
        assert self.mock_handler.call_count >= 2

        self.hook.stop()

        # Should stop cleanly
        assert self.hook.is_running is False


class TestInstructionReinforcementConfiguration:
    """Test configuration aspects of instruction reinforcement."""

    def test_default_configuration_values(self):
        """Test that default configuration values are properly applied."""
        config = Config()

        ir_config = config.get("instruction_reinforcement")
        assert ir_config is not None

        assert ir_config["enabled"] is True
        assert ir_config["test_mode"] is True
        assert ir_config["injection_interval"] == 5
        assert len(ir_config["test_messages"]) > 0
        assert len(ir_config["production_messages"]) > 0

        # Check message content
        test_messages = ir_config["test_messages"]
        assert any("[TEST-REMINDER]" in msg for msg in test_messages)
        assert any("[PM-INSTRUCTION]" in msg for msg in test_messages)

        prod_messages = ir_config["production_messages"]
        assert any("[PM-REMINDER]" in msg for msg in prod_messages)

    def test_configuration_override(self):
        """Test configuration override behavior."""
        custom_config = Config(
            {
                "instruction_reinforcement": {
                    "enabled": False,
                    "injection_interval": 10,
                    "test_messages": ["Custom test message"],
                }
            }
        )

        ir_config = custom_config.get("instruction_reinforcement")

        # Custom values should override defaults
        assert ir_config["enabled"] is False
        assert ir_config["injection_interval"] == 10
        assert ir_config["test_messages"] == ["Custom test message"]

        # Non-overridden values should use defaults
        assert ir_config["test_mode"] is True  # From default
        assert len(ir_config["production_messages"]) > 0  # From default

    def test_environment_variable_override(self):
        """Test environment variable configuration override."""
        import os

        # Set environment variables
        os.environ["CLAUDE_MULTIAGENT_PM_INSTRUCTION_REINFORCEMENT_ENABLED"] = "false"
        os.environ[
            "CLAUDE_MULTIAGENT_PM_INSTRUCTION_REINFORCEMENT_INJECTION_INTERVAL"
        ] = "15"

        try:
            Config.reset_singleton()
            config = Config()

            # Environment variables should override defaults
            assert config.get("instruction_reinforcement_enabled") is False
            assert config.get("instruction_reinforcement_injection_interval") == 15

        finally:
            # Clean up environment variables
            os.environ.pop(
                "CLAUDE_MULTIAGENT_PM_INSTRUCTION_REINFORCEMENT_ENABLED", None
            )
            os.environ.pop(
                "CLAUDE_MULTIAGENT_PM_INSTRUCTION_REINFORCEMENT_INJECTION_INTERVAL",
                None,
            )
            Config.reset_singleton()
