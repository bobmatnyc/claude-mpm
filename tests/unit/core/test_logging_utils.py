"""Comprehensive test coverage for logging_utils module.

Tests the current behavior to ensure compatibility when implementing optimizations.
"""

import json
import logging
import tempfile
import time
from pathlib import Path
from unittest import mock

import pytest

from claude_mpm.core.logging_utils import (
    LoggerFactory,
    LoggingConfig,
    PerformanceLogger,
    StructuredLogger,
    get_component_logger,
    get_logger,
    get_performance_logger,
    get_structured_logger,
    initialize_logging,
    set_log_level,
)


class TestLoggingConfig:
    """Test LoggingConfig class constants and configuration."""

    def test_log_levels(self):
        """Test that all log levels are correctly mapped."""
        assert LoggingConfig.LEVELS["DEBUG"] == logging.DEBUG
        assert LoggingConfig.LEVELS["INFO"] == logging.INFO
        assert LoggingConfig.LEVELS["WARNING"] == logging.WARNING
        assert LoggingConfig.LEVELS["ERROR"] == logging.ERROR
        assert LoggingConfig.LEVELS["CRITICAL"] == logging.CRITICAL

    def test_formats_defined(self):
        """Test that all format strings are defined."""
        assert LoggingConfig.DEFAULT_FORMAT
        assert LoggingConfig.SIMPLE_FORMAT
        assert LoggingConfig.DETAILED_FORMAT
        assert LoggingConfig.JSON_FORMAT
        assert LoggingConfig.DATE_FORMAT
        assert LoggingConfig.ISO_DATE_FORMAT

    def test_file_settings(self):
        """Test file rotation settings."""
        assert LoggingConfig.MAX_BYTES == 5 * 1024 * 1024  # 5MB
        assert LoggingConfig.BACKUP_COUNT == 5
        assert LoggingConfig.ROTATION_INTERVAL == "midnight"
        assert LoggingConfig.ROTATION_BACKUP_COUNT == 7

    def test_component_names(self):
        """Test component namespace mappings."""
        expected_components = {
            "agent",
            "service",
            "core",
            "cli",
            "hooks",
            "monitor",
            "socketio",
            "memory",
            "config",
            "utils",
        }
        assert set(LoggingConfig.COMPONENT_NAMES.keys()) == expected_components


class TestLoggerFactory:
    """Test LoggerFactory singleton and functionality."""

    def setup_method(self):
        """Reset LoggerFactory state before each test."""
        LoggerFactory._initialized = False
        LoggerFactory._log_dir = None
        LoggerFactory._log_level = "INFO"
        LoggerFactory._handlers = {}

    def test_singleton_initialization(self):
        """Test that LoggerFactory initializes only once."""
        LoggerFactory.initialize(log_level="DEBUG")
        assert LoggerFactory._initialized is True
        assert LoggerFactory._log_level == "DEBUG"

        # Second initialization should be ignored
        LoggerFactory.initialize(log_level="ERROR")
        assert LoggerFactory._log_level == "DEBUG"  # Should not change

    def test_get_logger_auto_initializes(self):
        """Test that get_logger auto-initializes if needed."""
        assert LoggerFactory._initialized is False
        logger = LoggerFactory.get_logger("test")
        assert LoggerFactory._initialized is True
        assert logger.name == "test"

    def test_get_logger_with_component(self):
        """Test logger creation with component namespace."""
        logger = LoggerFactory.get_logger("test_module", component="agent")
        assert "claude_mpm.agent" in logger.name

    def test_get_logger_with_level(self):
        """Test logger creation with specific level."""
        logger = LoggerFactory.get_logger("test", level="DEBUG")
        assert logger.level == logging.DEBUG or logger.level == logging.NOTSET

    def test_set_level(self):
        """Test dynamic log level changes."""
        LoggerFactory.initialize(log_level="INFO")
        LoggerFactory.set_level("DEBUG")
        assert LoggerFactory._log_level == "DEBUG"

        # Test invalid level is ignored
        LoggerFactory.set_level("INVALID")
        assert LoggerFactory._log_level == "DEBUG"

    def test_file_handler_creation(self):
        """Test file handler creation with log directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_dir = Path(tmpdir)
            LoggerFactory.initialize(log_dir=log_dir, log_to_file=True)

            # Check that log directory was created
            assert log_dir.exists()

            # Check that handlers were added
            assert "file" in LoggerFactory._handlers
            assert "file_daily" in LoggerFactory._handlers

    def test_add_remove_handler(self):
        """Test adding and removing custom handlers."""
        LoggerFactory.initialize()

        # Add custom handler
        custom_handler = logging.StreamHandler()
        LoggerFactory.add_handler("custom", custom_handler)
        assert "custom" in LoggerFactory._handlers

        # Remove handler
        LoggerFactory.remove_handler("custom")
        assert "custom" not in LoggerFactory._handlers


class TestConvenienceFunctions:
    """Test module-level convenience functions."""

    def setup_method(self):
        """Reset LoggerFactory state before each test."""
        LoggerFactory._initialized = False
        LoggerFactory._handlers = {}
        # Clear the cache
        get_logger.cache_clear()

    def test_get_logger_caching(self):
        """Test that get_logger uses caching."""
        logger1 = get_logger("test_cache")
        logger2 = get_logger("test_cache")
        assert logger1 is logger2  # Should be the same instance due to caching

        # Different parameters should create different instances
        logger3 = get_logger("test_cache", component="agent")
        assert logger3 is not logger1

    def test_initialize_logging(self):
        """Test initialize_logging convenience function."""
        with tempfile.TemporaryDirectory() as tmpdir:
            initialize_logging(
                log_level="DEBUG",
                log_dir=Path(tmpdir),
                log_to_file=True,
                log_format=LoggingConfig.SIMPLE_FORMAT,
            )
            assert LoggerFactory._initialized is True
            assert LoggerFactory._log_level == "DEBUG"

    def test_set_log_level_convenience(self):
        """Test set_log_level convenience function."""
        initialize_logging(log_level="INFO")
        set_log_level("WARNING")
        assert LoggerFactory._log_level == "WARNING"

    def test_get_component_logger(self):
        """Test component logger creation."""
        logger = get_component_logger("agent", "test_agent")
        assert "claude_mpm.agent" in logger.name


class TestStructuredLogger:
    """Test StructuredLogger functionality."""

    def test_context_management(self):
        """Test adding and clearing context."""
        base_logger = get_logger("test_structured")
        structured = StructuredLogger(base_logger)

        # Add context
        structured.with_context(user="test", operation="create")
        assert structured.context == {"user": "test", "operation": "create"}

        # Chain context additions
        structured.with_context(status="success")
        assert len(structured.context) == 3

        # Clear context
        structured.clear_context()
        assert structured.context == {}

    def test_formatted_messages(self, caplog):
        """Test that messages are formatted with context."""
        base_logger = get_logger("test_structured")
        structured = StructuredLogger(base_logger)
        structured.with_context(user="alice", action="login")

        with caplog.at_level(logging.INFO):
            structured.info("User authenticated")

        assert "User authenticated" in caplog.text
        assert "user=alice" in caplog.text
        assert "action=login" in caplog.text

    def test_all_log_levels(self, caplog):
        """Test all log level methods."""
        structured = get_structured_logger("test", component="test")

        with caplog.at_level(logging.DEBUG):
            structured.debug("Debug message")
            structured.info("Info message")
            structured.warning("Warning message")
            structured.error("Error message")
            structured.critical("Critical message")

        assert "Debug message" in caplog.text
        assert "Info message" in caplog.text
        assert "Warning message" in caplog.text
        assert "Error message" in caplog.text
        assert "Critical message" in caplog.text


class TestPerformanceLogger:
    """Test PerformanceLogger functionality."""

    def test_timer_operations(self, caplog):
        """Test timer start and end operations."""
        perf_logger = get_performance_logger("test_perf")

        perf_logger.start_timer("test_op")
        time.sleep(0.01)  # Small delay

        with caplog.at_level(logging.INFO):
            duration = perf_logger.end_timer("test_op")

        assert duration > 0
        assert "test_op" in caplog.text
        assert "completed in" in caplog.text

    def test_timer_not_started(self):
        """Test ending a timer that wasn't started."""
        perf_logger = get_performance_logger("test_perf")
        duration = perf_logger.end_timer("nonexistent")
        assert duration == 0.0

    @mock.patch("psutil.Process")
    def test_log_memory_usage(self, mock_process, caplog):
        """Test memory usage logging."""
        # Mock memory info
        mock_memory = mock.Mock()
        mock_memory.rss = 100 * 1024 * 1024  # 100 MB
        mock_process.return_value.memory_info.return_value = mock_memory

        perf_logger = get_performance_logger("test_perf")

        with caplog.at_level(logging.INFO):
            perf_logger.log_memory_usage("test_context")

        assert "Memory usage" in caplog.text
        assert "test_context" in caplog.text
        assert "100" in caplog.text  # Should show ~100 MB

    def test_log_metrics(self, caplog):
        """Test metrics logging."""
        perf_logger = get_performance_logger("test_perf")

        metrics = {"requests": 100, "errors": 2, "latency_ms": 45.5}

        with caplog.at_level(logging.INFO):
            perf_logger.log_metrics(metrics, "api_endpoint")

        assert "Performance metrics" in caplog.text
        assert "api_endpoint" in caplog.text
        assert "requests=100" in caplog.text
        assert "errors=2" in caplog.text
        assert "latency_ms=45.5" in caplog.text


class TestLoggerPerformance:
    """Performance benchmarks for logger operations."""

    def test_logger_creation_performance(self, benchmark):
        """Benchmark logger creation."""
        # Clear cache for fair testing
        get_logger.cache_clear()

        def create_logger():
            return get_logger(f"test_logger_{time.time()}")

        result = benchmark(create_logger)
        assert result is not None

    def test_cached_logger_performance(self, benchmark):
        """Benchmark cached logger retrieval."""
        # Pre-populate cache
        get_logger("cached_test")

        def get_cached():
            return get_logger("cached_test")

        result = benchmark(get_cached)
        assert result is not None

    def test_structured_logging_performance(self, benchmark):
        """Benchmark structured logging with context."""
        logger = get_structured_logger("perf_test")
        logger.with_context(user="test", session="abc123")

        def log_with_context():
            logger.info("Performance test message")

        benchmark(log_with_context)


class TestBackwardCompatibility:
    """Test backward compatibility with existing code patterns."""

    def test_standard_logging_pattern(self):
        """Test that standard logging.getLogger pattern still works."""
        # This simulates existing code pattern
        logger = logging.getLogger("backward_compat_test")
        assert logger is not None
        assert logger.name == "backward_compat_test"

    def test_mixed_logger_usage(self, caplog):
        """Test mixing LoggerFactory with standard logging."""
        # Initialize through LoggerFactory
        initialize_logging(log_level="INFO")

        # Use standard logging
        std_logger = logging.getLogger("mixed_test")

        # Use LoggerFactory
        factory_logger = get_logger("mixed_test")

        with caplog.at_level(logging.INFO):
            std_logger.info("Standard logger")
            factory_logger.info("Factory logger")

        assert "Standard logger" in caplog.text
        assert "Factory logger" in caplog.text


@pytest.fixture
def clean_logger_state():
    """Fixture to ensure clean logger state for each test."""
    # Store original state
    original_initialized = LoggerFactory._initialized
    original_handlers = LoggerFactory._handlers.copy()
    original_level = LoggerFactory._log_level

    # Reset state
    LoggerFactory._initialized = False
    LoggerFactory._handlers = {}
    LoggerFactory._log_level = "INFO"
    get_logger.cache_clear()

    yield

    # Restore original state
    LoggerFactory._initialized = original_initialized
    LoggerFactory._handlers = original_handlers
    LoggerFactory._log_level = original_level
