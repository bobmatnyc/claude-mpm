"""Tests for Notifier."""

import logging

import pytest

from claude_mpm.commander.events.manager import EventManager
from claude_mpm.commander.models.events import EventPriority, EventType
from claude_mpm.commander.workflow.notifier import Notifier, NotifierConfig


class TestNotifier:
    """Test Notifier notification delivery."""

    @pytest.fixture
    def event_manager(self):
        """Create an event manager."""
        return EventManager()

    @pytest.fixture
    def event(self, event_manager):
        """Create a test event."""
        return event_manager.create(
            project_id="proj_test",
            event_type=EventType.DECISION_NEEDED,
            title="Choose deployment target",
            options=["staging", "production"],
            priority=EventPriority.HIGH,
        )

    def test_init_default_config(self):
        """Test Notifier initialization with default config."""
        notifier = Notifier()
        assert notifier.config.log_level == "INFO"
        assert notifier._log_level == logging.INFO

    def test_init_custom_config(self):
        """Test Notifier initialization with custom config."""
        config = NotifierConfig(log_level="DEBUG")
        notifier = Notifier(config)
        assert notifier.config.log_level == "DEBUG"
        assert notifier._log_level == logging.DEBUG

    def test_init_log_level_mapping(self):
        """Test log level string mapping."""
        # Test all valid log levels
        levels = [
            ("DEBUG", logging.DEBUG),
            ("INFO", logging.INFO),
            ("WARNING", logging.WARNING),
            ("ERROR", logging.ERROR),
            ("CRITICAL", logging.CRITICAL),
        ]

        for level_str, expected_level in levels:
            config = NotifierConfig(log_level=level_str)
            notifier = Notifier(config)
            assert notifier._log_level == expected_level

    def test_init_invalid_log_level(self):
        """Test invalid log level defaults to INFO."""
        config = NotifierConfig(log_level="INVALID")
        notifier = Notifier(config)
        assert notifier._log_level == logging.INFO

    @pytest.mark.asyncio
    async def test_notify(self, event, caplog):
        """Test notify logs event."""
        notifier = Notifier(NotifierConfig(log_level="INFO"))

        with caplog.at_level(logging.INFO):
            await notifier.notify(event)

        # Should have logged notification
        assert len(caplog.records) > 0
        log_message = caplog.records[0].message
        assert "Event notification" in log_message
        assert event.id in log_message
        assert event.title in log_message

    @pytest.mark.asyncio
    async def test_notify_resolution(self, event, caplog):
        """Test notify_resolution logs resolution."""
        notifier = Notifier(NotifierConfig(log_level="INFO"))
        response = "Deploy to staging"

        with caplog.at_level(logging.INFO):
            await notifier.notify_resolution(event, response)

        # Should have logged resolution
        assert len(caplog.records) > 0
        log_message = caplog.records[0].message
        assert "Event resolution" in log_message
        assert event.id in log_message
        assert response in log_message

    @pytest.mark.asyncio
    async def test_notify_respects_log_level(self, event, caplog):
        """Test notify respects configured log level."""
        # Set log level to WARNING
        notifier = Notifier(NotifierConfig(log_level="WARNING"))

        # Notifier will log at WARNING level
        with caplog.at_level(logging.INFO):
            await notifier.notify(event)

        # Should have logged at WARNING level
        assert len(caplog.records) > 0
        assert caplog.records[0].levelno == logging.WARNING

    def test_format_event(self, event):
        """Test event formatting."""
        notifier = Notifier()
        formatted = notifier._format_event(event)

        # Should include priority, ID, project, title
        assert "HIGH" in formatted
        assert event.id in formatted
        assert event.project_id in formatted
        assert event.title in formatted

    def test_format_event_with_options(self, event):
        """Test event formatting includes options."""
        notifier = Notifier()
        formatted = notifier._format_event(event)

        # Should include options
        assert "Options:" in formatted
        assert "staging" in formatted
        assert "production" in formatted

    def test_format_event_without_options(self, event_manager):
        """Test event formatting without options."""
        event = event_manager.create(
            project_id="proj_test",
            event_type=EventType.ERROR,
            title="Something failed",
        )

        notifier = Notifier()
        formatted = notifier._format_event(event)

        # Should not include options
        assert "Options:" not in formatted

    @pytest.mark.asyncio
    async def test_notify_truncates_long_response(self, event, caplog):
        """Test notify_resolution truncates long responses."""
        notifier = Notifier(NotifierConfig(log_level="INFO"))
        long_response = "x" * 200  # 200 characters

        with caplog.at_level(logging.INFO):
            await notifier.notify_resolution(event, long_response)

        # Should truncate to 100 characters
        log_message = caplog.records[0].message
        # Check that the full 200 chars are NOT in the message
        assert long_response not in log_message
        # Check that 100 chars are present
        assert long_response[:100] in log_message
