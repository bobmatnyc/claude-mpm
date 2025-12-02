"""
Unit Tests for Hello World MCP Tool
====================================

Comprehensive test suite for the Hello World tool implementation.
Tests all greeting modes, error handling, and edge cases.

Part of ISS-0036: Hello World Tool - Testing and Validation Tool
"""

import asyncio
import platform
import sys
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch

import pytest

# Add src to path for imports
sys.path.insert(0, "/Users/masa/Projects/claude-mpm/src")

from claude_mpm.services.mcp_gateway.core.interfaces import MCPToolInvocation
from claude_mpm.services.mcp_gateway.tools.hello_world import HelloWorldTool


class TestHelloWorldTool:
    """Test suite for HelloWorldTool class."""

    @pytest.fixture
    async def tool(self):
        """Create and initialize a HelloWorldTool instance."""
        tool = HelloWorldTool()
        await tool.initialize()
        return tool

    @pytest.fixture
    def mock_invocation(self):
        """Create a mock MCPToolInvocation."""

        def _create_invocation(**params):
            invocation = Mock(spec=MCPToolInvocation)
            invocation.parameters = params
            return invocation

        return _create_invocation

    # ============= Initialization Tests =============

    @pytest.mark.asyncio
    async def test_tool_initialization():
        """Test that tool initializes correctly."""
        tool = HelloWorldTool()
        assert not tool._initialized

        result = await tool.initialize()
        assert result is True
        assert tool._initialized
        assert tool.version == "1.0.0"
        assert len(tool.greeting_history) == 0

    @pytest.mark.asyncio
    async def test_tool_definition():
        """Test that tool definition is properly configured."""
        tool = HelloWorldTool()
        definition = tool.get_definition()

        assert definition.name == "hello_world"
        assert "Hello World tool" in definition.description
        assert "mode" in definition.input_schema["properties"]
        assert "simple" in definition.input_schema["properties"]["mode"]["enum"]
        assert definition.input_schema["required"] == ["mode"]

    # ============= Simple Greeting Tests =============

    @pytest.mark.asyncio
    async def test_simple_greeting(self, mock_invocation):
        """Test simple greeting mode."""
        invocation = mock_invocation(mode="simple")
        result = await self.invoke(invocation)

        assert result.success is True
        assert result.data["greeting"] == "Hello World!"
        assert result.data["mode"] == "simple"
        assert "timestamp" in result.data

    @pytest.mark.asyncio
    async def test_simple_greeting_uppercase(self, mock_invocation):
        """Test simple greeting with uppercase transformation."""
        invocation = mock_invocation(mode="simple", uppercase=True)
        result = await self.invoke(invocation)

        assert result.success is True
        assert result.data["greeting"] == "HELLO WORLD!"

    @pytest.mark.asyncio
    async def test_simple_greeting_repeat(self, mock_invocation):
        """Test simple greeting with repetition."""
        invocation = mock_invocation(mode="simple", repeat=3)
        result = await self.invoke(invocation)

        assert result.success is True
        assert result.data["greeting"] == "Hello World! Hello World! Hello World!"

    # ============= Personalized Greeting Tests =============

    @pytest.mark.asyncio
    async def test_personalized_greeting(self, mock_invocation):
        """Test personalized greeting mode."""
        invocation = mock_invocation(mode="personalized", name="Alice")
        result = await self.invoke(invocation)

        assert result.success is True
        assert "Alice" in result.data["greeting"]
        assert "Welcome to the MCP Gateway" in result.data["greeting"]

    @pytest.mark.asyncio
    async def test_personalized_greeting_missing_name(self, mock_invocation):
        """Test personalized greeting without name parameter."""
        invocation = mock_invocation(mode="personalized")
        result = await self.invoke(invocation)

        assert result.success is False
        assert "validation failed" in result.error

    @pytest.mark.asyncio
    async def test_personalized_greeting_invalid_name(self, mock_invocation):
        """Test personalized greeting with invalid name format."""
        invocation = mock_invocation(mode="personalized", name="@#$%^")
        result = await self.invoke(invocation)

        assert result.success is False
        assert "validation failed" in result.error

    @pytest.mark.asyncio
    async def test_personalized_greeting_valid_names(self, mock_invocation):
        """Test personalized greeting with various valid name formats."""
        valid_names = [
            "John",
            "Mary-Jane",
            "O'Brien",
            "Dr. Smith",
            "Jean-Claude",
            "Mary Ann",
        ]

        for name in valid_names:
            invocation = mock_invocation(mode="personalized", name=name)
            result = await self.invoke(invocation)
            assert result.success is True
            assert name in result.data["greeting"]

    # ============= Time-Based Greeting Tests =============

    @pytest.mark.parametrize(
        "hour,expected_greeting",
        [
            (2, "Good night"),
            (7, "Good morning"),
            (14, "Good afternoon"),
            (19, "Good evening"),
            (23, "Good night"),
        ],
    )
    @pytest.mark.asyncio
    async def test_time_based_greeting(
        self, tool, mock_invocation, hour, expected_greeting
    ):
        """Test time-based greeting for different hours."""
        with patch(
            "claude_mpm.services.mcp_gateway.tools.hello_world.datetime"
        ) as mock_datetime:
            mock_now = Mock()
            mock_now.hour = hour
            mock_now.strftime.return_value = "12:00 PM"
            mock_datetime.now.return_value = mock_now

            invocation = mock_invocation(mode="time_based")
            result = await tool.invoke(invocation)

            assert result.success is True
            assert expected_greeting in result.data["greeting"]

    # ============= Multi-Language Greeting Tests =============

    @pytest.mark.parametrize(
        "language,expected",
        [
            ("english", "Hello"),
            ("spanish", "Hola"),
            ("french", "Bonjour"),
            ("japanese", "こんにちは"),
            ("chinese", "你好"),
            ("arabic", "مرحبا"),
            ("russian", "Привет"),
        ],
    )
    @pytest.mark.asyncio
    async def test_multi_language_greeting(
        self, tool, mock_invocation, language, expected
    ):
        """Test multi-language greetings."""
        invocation = mock_invocation(mode="multi_language", language=language)
        result = await tool.invoke(invocation)

        assert result.success is True
        assert expected in result.data["greeting"]
        assert "World" in result.data["greeting"]

    @pytest.mark.asyncio
    async def test_multi_language_greeting_with_name(self, mock_invocation):
        """Test multi-language greeting with personalized name."""
        invocation = mock_invocation(
            mode="multi_language", language="spanish", name="Carlos"
        )
        result = await self.invoke(invocation)

        assert result.success is True
        assert "Hola" in result.data["greeting"]
        assert "Carlos" in result.data["greeting"]

    @pytest.mark.asyncio
    async def test_multi_language_default(self, mock_invocation):
        """Test multi-language greeting defaults to English."""
        invocation = mock_invocation(mode="multi_language")
        result = await self.invoke(invocation)

        assert result.success is True
        assert "Hello" in result.data["greeting"]

    # ============= System Info Greeting Tests =============

    @pytest.mark.asyncio
    async def test_system_info_greeting(self, mock_invocation):
        """Test system info greeting mode."""
        invocation = mock_invocation(mode="system_info")
        result = await self.invoke(invocation)

        assert result.success is True
        greeting = result.data["greeting"]
        assert platform.system() in greeting
        assert "Python" in greeting
        assert "MCP Gateway" in greeting

    # ============= Async Greeting Tests =============

    @pytest.mark.asyncio
    async def test_async_greeting_default_delay(self, mock_invocation):
        """Test async greeting with default delay."""
        invocation = mock_invocation(mode="async_test")

        start = datetime.now(timezone.utc)
        result = await self.invoke(invocation)
        duration = (datetime.now(timezone.utc) - start).total_seconds()

        assert result.success is True
        assert "1000ms" in result.data["greeting"]
        assert duration >= 1.0  # Should take at least 1 second

    @pytest.mark.asyncio
    async def test_async_greeting_custom_delay(self, mock_invocation):
        """Test async greeting with custom delay."""
        invocation = mock_invocation(mode="async_test", delay_ms=500)

        start = datetime.now(timezone.utc)
        result = await self.invoke(invocation)
        duration = (datetime.now(timezone.utc) - start).total_seconds()

        assert result.success is True
        assert "500ms" in result.data["greeting"]
        assert duration >= 0.5  # Should take at least 0.5 seconds
        assert duration < 1.0  # But less than 1 second

    @pytest.mark.asyncio
    async def test_async_greeting_invalid_delay(self, mock_invocation):
        """Test async greeting with invalid delay."""
        invocation = mock_invocation(mode="async_test", delay_ms=10000)
        result = await self.invoke(invocation)

        assert result.success is False
        assert "validation failed" in result.error

    # ============= Error Testing Mode Tests =============

    @pytest.mark.asyncio
    async def test_error_test_validation(self, mock_invocation):
        """Test error simulation for validation errors."""
        invocation = mock_invocation(mode="error_test", error_type="validation")
        result = await self.invoke(invocation)

        assert result.success is False
        assert "validation error" in result.error.lower()

    @pytest.mark.asyncio
    async def test_error_test_runtime(self, mock_invocation):
        """Test error simulation for runtime errors."""
        invocation = mock_invocation(mode="error_test", error_type="runtime")
        result = await self.invoke(invocation)

        assert result.success is False
        assert "runtime error" in result.error.lower()

    @pytest.mark.timeout(2)  # Ensure test doesn't hang
    @pytest.mark.asyncio
    async def test_error_test_timeout(self, mock_invocation):
        """Test error simulation for timeout errors."""
        invocation = mock_invocation(mode="error_test", error_type="timeout")

        # This should timeout, but we'll mock it to avoid actual long wait
        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            mock_sleep.side_effect = asyncio.TimeoutError()

            # The tool will catch this and return an error
            with pytest.raises(asyncio.TimeoutError):
                await self.invoke(invocation)

    # ============= Metadata Tests =============

    @pytest.mark.asyncio
    async def test_metadata_included(self, mock_invocation):
        """Test that metadata is included when requested."""
        invocation = mock_invocation(mode="simple", include_metadata=True)
        result = await self.invoke(invocation)

        assert result.success is True
        assert "metadata" in result.data
        metadata = result.data["metadata"]
        assert "tool_version" in metadata
        assert "execution_environment" in metadata
        assert "parameters_used" in metadata
        assert metadata["tool_version"] == "1.0.0"

    @pytest.mark.asyncio
    async def test_metadata_excluded(self, mock_invocation):
        """Test that metadata is excluded when not requested."""
        invocation = mock_invocation(mode="simple", include_metadata=False)
        result = await self.invoke(invocation)

        assert result.success is True
        assert "metadata" not in result.data

    # ============= Parameter Validation Tests =============

    @pytest.mark.asyncio
    async def test_invalid_mode(self, mock_invocation):
        """Test handling of invalid mode parameter."""
        invocation = mock_invocation(mode="invalid_mode")
        result = await self.invoke(invocation)

        assert result.success is False

    @pytest.mark.asyncio
    async def test_invalid_repeat_value(self, mock_invocation):
        """Test handling of invalid repeat parameter."""
        invocation = mock_invocation(mode="simple", repeat=20)
        result = await self.invoke(invocation)

        assert result.success is False
        assert "validation failed" in result.error

    @pytest.mark.asyncio
    async def test_negative_repeat_value(self, mock_invocation):
        """Test handling of negative repeat parameter."""
        invocation = mock_invocation(mode="simple", repeat=-1)
        result = await self.invoke(invocation)

        assert result.success is False

    # ============= Analytics and History Tests =============

    @pytest.mark.asyncio
    async def test_greeting_history_tracking(self, mock_invocation):
        """Test that greeting history is tracked correctly."""
        # Generate several greetings
        modes = ["simple", "simple", "personalized", "multi_language"]
        for _i, mode in enumerate(modes):
            params = {"mode": mode}
            if mode == "personalized":
                params["name"] = "Test"
            invocation = mock_invocation(**params)
            await self.invoke(invocation)

        # Check history
        assert len(self.greeting_history) == 4
        analytics = self.get_analytics()
        assert analytics["total_greetings"] == 4
        assert analytics["modes_used"]["simple"] == 2
        assert analytics["modes_used"]["personalized"] == 1
        assert analytics["modes_used"]["multi_language"] == 1

    @pytest.mark.asyncio
    async def test_history_size_limit(self, mock_invocation):
        """Test that greeting history respects size limit."""
        self.max_history_size = 5

        # Generate more greetings than the limit
        for _i in range(10):
            invocation = mock_invocation(mode="simple")
            await self.invoke(invocation)

        # History should be capped at max_history_size
        assert len(self.greeting_history) <= self.max_history_size

    # ============= Metrics Tests =============

    @pytest.mark.asyncio
    async def test_metrics_tracking(self, mock_invocation):
        """Test that metrics are tracked correctly."""
        # Generate successful invocation
        invocation = mock_invocation(mode="simple")
        await self.invoke(invocation)

        metrics = self.get_metrics()
        assert metrics["invocations"] == 1
        assert metrics["successes"] == 1
        assert metrics["failures"] == 0
        assert metrics["average_execution_time"] > 0

    @pytest.mark.asyncio
    async def test_metrics_with_failures(self, mock_invocation):
        """Test metrics tracking with failures."""
        # Generate successful invocation
        invocation = mock_invocation(mode="simple")
        await self.invoke(invocation)

        # Generate failed invocation
        invocation = mock_invocation(mode="personalized")  # Missing name
        await self.invoke(invocation)

        metrics = self.get_metrics()
        assert metrics["invocations"] == 2
        assert metrics["successes"] == 1
        assert metrics["failures"] == 1

    # ============= Shutdown Tests =============

    @pytest.mark.asyncio
    async def test_tool_shutdown(self, mock_invocation):
        """Test tool shutdown and cleanup."""
        # Generate some greetings
        invocation = mock_invocation(mode="simple")
        await self.invoke(invocation)

        assert len(self.greeting_history) > 0
        assert self._initialized is True

        # Shutdown
        await self.shutdown()

        assert len(self.greeting_history) == 0
        assert self._initialized is False

    # ============= Integration Tests =============

    @pytest.mark.asyncio
    async def test_full_workflow(self):
        """Test complete workflow from initialization to shutdown."""
        tool = HelloWorldTool()

        # Initialize
        assert await tool.initialize() is True

        # Test various modes
        test_cases = [
            {"mode": "simple"},
            {"mode": "personalized", "name": "Alice"},
            {"mode": "time_based"},
            {"mode": "multi_language", "language": "spanish"},
            {"mode": "system_info"},
            {"mode": "async_test", "delay_ms": 100},
        ]

        for params in test_cases:
            invocation = self(**params)
            result = await tool.invoke(invocation)
            assert result.success is True

        # Check analytics
        analytics = tool.get_analytics()
        assert analytics["total_greetings"] == len(test_cases)

        # Shutdown
        await tool.shutdown()
        assert tool._initialized is False


@pytest.mark.asyncio
class TestHelloWorldToolAsync:
    """Async-specific tests for HelloWorldTool."""

    @pytest.mark.asyncio
    async def test_concurrent_invocations():
        """Test that tool handles concurrent invocations correctly."""
        tool = HelloWorldTool()
        await tool.initialize()

        # Create multiple invocations
        invocations = []
        for i in range(5):
            inv = Mock(spec=MCPToolInvocation)
            inv.parameters = {"mode": "simple", "repeat": i + 1}
            invocations.append(inv)

        # Run concurrently
        results = await asyncio.gather(*[tool.invoke(inv) for inv in invocations])

        # All should succeed
        assert all(r.success for r in results)
        assert len(tool.greeting_history) == 5

        await tool.shutdown()

    @pytest.mark.asyncio
    async def test_async_delay_accuracy():
        """Test that async delays are accurate."""
        tool = HelloWorldTool()
        await tool.initialize()

        delays = [100, 200, 300]
        for delay_ms in delays:
            inv = Mock(spec=MCPToolInvocation)
            inv.parameters = {"mode": "async_test", "delay_ms": delay_ms}

            start = datetime.now(timezone.utc)
            result = await tool.invoke(inv)
            duration_ms = (datetime.now(timezone.utc) - start).total_seconds() * 1000

            assert result.success is True
            # Allow 50ms tolerance
            assert abs(duration_ms - delay_ms) < 50

        await tool.shutdown()


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])
