"""
Unit tests for the actual InstructionReinforcementHook implementation.

These tests verify the real functionality of the instruction reinforcement system.
"""

import time
from datetime import datetime
from unittest.mock import patch

import pytest

from claude_mpm.core.instruction_reinforcement_hook import (
    InstructionReinforcementHook,
    get_instruction_reinforcement_hook,
    reset_instruction_reinforcement_hook,
)


class TestInstructionReinforcementHookReal:
    """Tests for the real InstructionReinforcementHook implementation."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test fixtures."""
        # Reset singleton before each test
        reset_instruction_reinforcement_hook()
        yield
        # Clean up after test
        reset_instruction_reinforcement_hook()

    def test_initialization_with_config(self):
        """Test hook initialization with custom config."""
        config = {
            "enabled": True,
            "test_mode": True,
            "injection_interval": 3,
            "test_messages": ["Custom test message"],
        }

        hook = InstructionReinforcementHook(config)

        assert hook.enabled is True
        assert hook.test_mode is True
        assert hook.injection_interval == 3
        assert hook.test_messages == ["Custom test message"]

    def test_initialization_with_defaults(self):
        """Test hook initialization with default values."""
        hook = InstructionReinforcementHook()

        assert hook.enabled is True
        assert hook.test_mode is True
        assert hook.injection_interval == 5
        assert len(hook.test_messages) == 4  # Default test messages
        assert len(hook.production_messages) == 4  # Default production messages

    def test_basic_injection_behavior(self):
        """Test basic injection at configured intervals."""
        config = {
            "enabled": True,
            "test_mode": True,
            "injection_interval": 2,
            "test_messages": ["[TEST] Custom message"],
        }

        hook = InstructionReinforcementHook(config)

        # Call 1 - should not inject
        params1 = {
            "todos": [
                {
                    "content": "Task 1",
                    "status": "pending",
                    "activeForm": "Working on task 1",
                }
            ]
        }
        result1 = hook.intercept_todowrite(params1)
        assert len(result1["todos"]) == 1  # No injection

        # Call 2 - should inject
        params2 = {
            "todos": [
                {
                    "content": "Task 2",
                    "status": "pending",
                    "activeForm": "Working on task 2",
                }
            ]
        }
        result2 = hook.intercept_todowrite(params2)
        assert len(result2["todos"]) == 2  # Injection occurred
        assert result2["todos"][0]["content"] == "[TEST] Custom message"
        assert result2["todos"][1]["content"] == "Task 2"

    def test_message_rotation(self):
        """Test message rotation through multiple injections."""
        config = {
            "enabled": True,
            "test_mode": True,
            "injection_interval": 1,  # Inject every call
            "test_messages": ["Message A", "Message B", "Message C"],
        }

        hook = InstructionReinforcementHook(config)

        injected_messages = []
        for i in range(5):
            params = {
                "todos": [
                    {
                        "content": f"Task {i+1}",
                        "status": "pending",
                        "activeForm": f"Working on task {i+1}",
                    }
                ]
            }
            result = hook.intercept_todowrite(params)
            injected_messages.append(result["todos"][0]["content"])

        expected = ["Message A", "Message B", "Message C", "Message A", "Message B"]
        assert injected_messages == expected

    def test_disabled_hook(self):
        """Test that disabled hook doesn't inject messages."""
        config = {
            "enabled": False,
            "test_mode": True,
            "injection_interval": 1,
            "test_messages": ["Should not appear"],
        }

        hook = InstructionReinforcementHook(config)

        params = {
            "todos": [
                {
                    "content": "Task 1",
                    "status": "pending",
                    "activeForm": "Working on task 1",
                }
            ]
        }
        result = hook.intercept_todowrite(params)

        assert len(result["todos"]) == 1  # No injection
        assert result["todos"][0]["content"] == "Task 1"

    def test_metrics_collection(self):
        """Test metrics collection functionality."""
        config = {"enabled": True, "test_mode": True, "injection_interval": 2}

        hook = InstructionReinforcementHook(config)

        # Make some calls
        for i in range(3):
            params = {
                "todos": [
                    {
                        "content": f"Task {i+1}",
                        "status": "pending",
                        "activeForm": f"Working on task {i+1}",
                    }
                ]
            }
            hook.intercept_todowrite(params)

        metrics = hook.get_metrics()

        assert metrics["call_count"] == 3
        assert metrics["injection_count"] == 1  # Should inject on call 2
        assert metrics["injection_rate"] == 1 / 3
        assert metrics["enabled"] is True
        assert metrics["test_mode"] is True
        assert metrics["injection_interval"] == 2
        assert "timestamp" in metrics

    def test_counter_reset(self):
        """Test counter reset functionality."""
        hook = InstructionReinforcementHook()

        # Make some calls to generate metrics
        for i in range(6):
            params = {
                "todos": [
                    {
                        "content": f"Task {i+1}",
                        "status": "pending",
                        "activeForm": f"Working on task {i+1}",
                    }
                ]
            }
            hook.intercept_todowrite(params)

        # Verify we have non-zero metrics
        metrics_before = hook.get_metrics()
        assert metrics_before["call_count"] > 0
        assert metrics_before["injection_count"] > 0

        # Reset counters
        hook.reset_counters()

        # Verify counters are reset
        metrics_after = hook.get_metrics()
        assert metrics_after["call_count"] == 0
        assert metrics_after["injection_count"] == 0
        assert metrics_after["injection_rate"] == 0

    def test_config_update(self):
        """Test configuration update functionality."""
        hook = InstructionReinforcementHook()

        # Update configuration
        new_config = {
            "enabled": False,
            "test_mode": False,
            "injection_interval": 10,
            "test_messages": ["New test message"],
        }

        hook.update_config(new_config)

        assert hook.enabled is False
        assert hook.test_mode is False
        assert hook.injection_interval == 10
        assert hook.test_messages == ["New test message"]

    def test_invalid_todos_handling(self):
        """Test handling of invalid todos parameter."""
        hook = InstructionReinforcementHook()

        # Test with invalid todos format
        params = {"todos": "not a list"}
        result = hook.intercept_todowrite(params)
        assert result == params  # Should return unchanged

        # Test with missing todos
        params = {}
        result = hook.intercept_todowrite(params)
        assert result == params  # Should return unchanged

        # Test with None todos
        params = {"todos": None}
        result = hook.intercept_todowrite(params)
        assert result == params  # Should return unchanged

    def test_error_resilience(self):
        """Test that hook handles errors gracefully."""
        hook = InstructionReinforcementHook()

        # Test with malformed todo structure that could cause exceptions
        params = {"todos": [{"incomplete": "todo"}]}  # Missing required fields
        result = hook.intercept_todowrite(params)

        # Should still work and potentially inject
        assert "todos" in result
        assert isinstance(result["todos"], list)

    def test_production_vs_test_messages(self):
        """Test difference between production and test mode messages."""
        # Test mode
        test_config = {"enabled": True, "test_mode": True, "injection_interval": 1}
        test_hook = InstructionReinforcementHook(test_config)

        test_params = {
            "todos": [{"content": "Task", "status": "pending", "activeForm": "Working"}]
        }
        test_result = test_hook.intercept_todowrite(test_params)
        test_message = test_result["todos"][0]["content"]

        # Production mode
        prod_config = {"enabled": True, "test_mode": False, "injection_interval": 1}
        prod_hook = InstructionReinforcementHook(prod_config)

        prod_params = {
            "todos": [{"content": "Task", "status": "pending", "activeForm": "Working"}]
        }
        prod_result = prod_hook.intercept_todowrite(prod_params)
        prod_message = prod_result["todos"][0]["content"]

        # Should be different message sets
        assert test_message != prod_message
        assert "[TEST-REMINDER]" in test_message or "[PM-INSTRUCTION]" in test_message
        assert "[PM-REMINDER]" in prod_message or "[PM-INSTRUCTION]" in prod_message


class TestInstructionReinforcementHookSingleton:
    """Tests for the singleton pattern functions."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test fixtures."""
        reset_instruction_reinforcement_hook()
        yield
        reset_instruction_reinforcement_hook()

    def test_singleton_pattern(self):
        """Test that get_instruction_reinforcement_hook returns same instance."""
        hook1 = get_instruction_reinforcement_hook()
        hook2 = get_instruction_reinforcement_hook()

        assert hook1 is hook2

    def test_singleton_reset(self):
        """Test that reset creates new instance."""
        hook1 = get_instruction_reinforcement_hook()
        reset_instruction_reinforcement_hook()
        hook2 = get_instruction_reinforcement_hook()

        assert hook1 is not hook2

    def test_singleton_with_config(self):
        """Test singleton initialization with config."""
        config = {"enabled": False, "injection_interval": 10}
        hook = get_instruction_reinforcement_hook(config)

        assert hook.enabled is False
        assert hook.injection_interval == 10

        # Second call should return same instance (config ignored)
        hook2 = get_instruction_reinforcement_hook({"enabled": True})
        assert hook is hook2
        assert hook2.enabled is False  # Config not applied to existing instance
