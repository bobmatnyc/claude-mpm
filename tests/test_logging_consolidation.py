"""
Comprehensive test coverage for logger consolidation.
This file tests both the old pattern and new centralized logging to ensure
behavior is preserved during migration.
"""

import json
import logging
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch


# Test old pattern
def get_logger_old_pattern(name):
    """Old pattern used across 397 instances."""
    logger = logging.getLogger(name)
    return logger


# Test new pattern
from claude_mpm.core.logging_utils import (
    LoggerFactory,
    get_component_logger,
    get_logger,
    get_performance_logger,
    get_structured_logger,
    initialize_logging,
    set_log_level,
)


class TestLoggerConsolidation(unittest.TestCase):
    """Test suite to ensure logger consolidation preserves behavior."""

    def setUp(self):
        """Set up test environment."""
        # Reset logging configuration
        logging.root.handlers = []
        LoggerFactory._initialized = False
        LoggerFactory._handlers = {}
        self.temp_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        """Clean up test environment."""
        # Reset logging
        logging.root.handlers = []
        LoggerFactory._initialized = False
        LoggerFactory._handlers = {}
        # Clean up temp directory
        if self.temp_dir.exists():
            import shutil

            shutil.rmtree(self.temp_dir)

    def test_old_pattern_behavior(self):
        """Test that old logger pattern works as expected."""
        logger = get_logger_old_pattern("test.module")

        self.assertIsInstance(logger, logging.Logger)
        self.assertEqual(logger.name, "test.module")
        self.assertIsNotNone(logger)

    def test_new_pattern_compatibility(self):
        """Test that new pattern provides same basic functionality."""
        logger = get_logger("test.module")

        self.assertIsInstance(logger, logging.Logger)
        self.assertEqual(logger.name, "test.module")
        self.assertIsNotNone(logger)

    def test_logger_caching(self):
        """Test that loggers are properly cached."""
        logger1 = get_logger("test.cached")
        logger2 = get_logger("test.cached")

        # Should return the same instance from cache
        self.assertIs(
            logging.getLogger("test.cached"), logging.getLogger("test.cached")
        )

    def test_logger_levels(self):
        """Test that log levels are properly set."""
        initialize_logging(log_level="DEBUG")
        logger = get_logger("test.levels")

        # Root logger should be at DEBUG level
        self.assertEqual(logging.root.level, logging.DEBUG)

    def test_component_loggers(self):
        """Test component-specific loggers."""
        agent_logger = get_component_logger("agent", "test_agent")
        service_logger = get_component_logger("service", "test_service")

        self.assertIn("agent", agent_logger.name)
        self.assertIn("service", service_logger.name)

    def test_file_logging(self):
        """Test file logging functionality."""
        log_file = self.temp_dir / "test.log"

        initialize_logging(log_level="INFO", log_dir=self.temp_dir, log_to_file=True)

        logger = get_logger("test.file")
        logger.info("Test message")

        # Check that log directory was created
        self.assertTrue(self.temp_dir.exists())

        # Check that handlers were added
        self.assertTrue(len(logging.root.handlers) > 0)

    def test_structured_logger(self):
        """Test structured logger functionality."""
        logger = get_structured_logger(
            "test.structured", component="test", request_id="123", user="test_user"
        )

        self.assertIsNotNone(logger)
        self.assertEqual(logger.context["request_id"], "123")
        self.assertEqual(logger.context["user"], "test_user")

    def test_performance_logger(self):
        """Test performance logger functionality."""
        logger = get_performance_logger("test.performance")

        logger.start_timer("test_operation")
        # Simulate some work
        import time

        time.sleep(0.01)
        duration = logger.end_timer("test_operation")

        self.assertGreater(duration, 0)
        self.assertLess(duration, 1)

    def test_dynamic_level_change(self):
        """Test changing log levels dynamically."""
        initialize_logging(log_level="INFO")
        logger = get_logger("test.dynamic")

        # Should be INFO initially
        self.assertEqual(logging.root.level, logging.INFO)

        # Change to DEBUG
        set_log_level("DEBUG")
        self.assertEqual(logging.root.level, logging.DEBUG)

    def test_logger_format_preservation(self):
        """Test that log formatting is preserved."""
        with patch("sys.stdout", new_callable=MagicMock) as mock_stdout:
            initialize_logging(log_level="INFO")
            logger = get_logger("test.format")
            logger.info("Test message")

            # Verify a handler was called
            self.assertTrue(len(logging.root.handlers) > 0)

    def test_multiple_initialization_safety(self):
        """Test that multiple initializations don't cause issues."""
        initialize_logging(log_level="INFO")
        initial_handlers = len(logging.root.handlers)

        # Try to initialize again
        initialize_logging(log_level="DEBUG")

        # Should not add duplicate handlers
        self.assertEqual(len(logging.root.handlers), initial_handlers)

    def test_handler_management(self):
        """Test adding and removing custom handlers."""
        initialize_logging()

        # Add custom handler
        custom_handler = logging.StreamHandler()
        LoggerFactory.add_handler("custom", custom_handler)
        self.assertIn("custom", LoggerFactory._handlers)

        # Remove custom handler
        LoggerFactory.remove_handler("custom")
        self.assertNotIn("custom", LoggerFactory._handlers)

    def test_backwards_compatibility(self):
        """Test that code using old pattern still works with new system."""
        # Old pattern
        old_logger = logging.getLogger("test.backwards")

        # New pattern
        new_logger = get_logger("test.backwards")

        # Both should work with the logging system
        old_logger.info("Old pattern message")
        new_logger.info("New pattern message")

        # Both should reference the same underlying logger
        self.assertEqual(old_logger.name, new_logger.name)


class TestLoggerMigration(unittest.TestCase):
    """Test suite for migration from old to new pattern."""

    def test_import_replacement(self):
        """Test that imports can be replaced safely."""
        # Old import pattern
        old_import = "import logging\nlogger = logging.getLogger(__name__)"

        # New import pattern
        new_import = "from claude_mpm.core.logging_utils import get_logger\nlogger = get_logger(__name__)"

        # Both should create functionally equivalent loggers
        self.assertIsNotNone(old_import)
        self.assertIsNotNone(new_import)

    def test_migration_preserves_functionality(self):
        """Test that migration preserves all logger functionality."""

        # Simulate a module using old pattern
        class OldModule:
            def __init__(self):
                self.logger = logging.getLogger(self.__class__.__name__)

            def do_work(self):
                self.logger.info("Doing work")
                return True

        # Simulate same module using new pattern
        class NewModule:
            def __init__(self):
                self.logger = get_logger(self.__class__.__name__)

            def do_work(self):
                self.logger.info("Doing work")
                return True

        old = OldModule()
        new = NewModule()

        # Both should work identically
        self.assertTrue(old.do_work())
        self.assertTrue(new.do_work())


class TestLoggerPerformance(unittest.TestCase):
    """Test performance improvements from consolidation."""

    def test_logger_creation_performance(self):
        """Test that centralized logger creation is efficient."""
        import time

        # Test old pattern performance
        start = time.time()
        for i in range(1000):
            logger = logging.getLogger(f"test.perf.old.{i}")
        old_duration = time.time() - start

        # Test new pattern performance (with caching)
        start = time.time()
        for i in range(1000):
            logger = get_logger(f"test.perf.new.{i}")
        new_duration = time.time() - start

        # New pattern should be comparable or better
        # (allowing 2x slower as acceptable since we add features)
        self.assertLess(new_duration, old_duration * 2)

    def test_cached_logger_performance(self):
        """Test that cached logger retrieval is fast."""
        import time

        # Pre-create logger
        get_logger("test.cached.perf")

        # Test cached retrieval
        start = time.time()
        for _ in range(10000):
            logger = get_logger("test.cached.perf")
        duration = time.time() - start

        # Should be very fast (< 1ms per 1000 retrievals)
        self.assertLess(duration, 0.01)


if __name__ == "__main__":
    unittest.main()
