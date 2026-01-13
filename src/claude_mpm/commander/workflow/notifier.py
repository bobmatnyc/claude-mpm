"""Basic notification delivery for events.

This module provides Notifier which sends notifications for events.
Currently supports logging, with extensibility for future channels
(Slack, email, webhooks).
"""

import logging
from dataclasses import dataclass

from ..models.events import Event

logger = logging.getLogger(__name__)


@dataclass
class NotifierConfig:
    """Configuration for notifier.

    Attributes:
        log_level: Logging level for notifications (default: INFO)

    Future attributes:
        slack_webhook: URL for Slack webhook notifications
        email_config: SMTP configuration for email notifications
        webhook_urls: List of webhook URLs for custom integrations
    """

    log_level: str = "INFO"
    # Future: slack_webhook, email_config, webhook_urls


class Notifier:
    """Sends notifications for events.

    Currently implements logging-based notifications with configurable
    log levels. Designed for extensibility to support future notification
    channels like Slack, email, and webhooks.

    Attributes:
        config: Notifier configuration

    Example:
        >>> config = NotifierConfig(log_level="INFO")
        >>> notifier = Notifier(config)
        >>> await notifier.notify(event)
        >>> await notifier.notify_resolution(event, "User responded")
    """

    def __init__(self, config: NotifierConfig | None = None) -> None:
        """Initialize notifier.

        Args:
            config: Optional NotifierConfig (uses defaults if not provided)
        """
        self.config = config or NotifierConfig()

        # Map log level string to logging level
        level_map = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL,
        }
        self._log_level = level_map.get(self.config.log_level.upper(), logging.INFO)

        logger.debug("Notifier initialized with log level: %s", self.config.log_level)

    async def notify(self, event: Event) -> None:
        """Send notification for an event.

        Currently logs the event at the configured log level. Future versions
        will support additional notification channels.

        Args:
            event: Event to notify about

        Example:
            >>> await notifier.notify(event)
            # Logs: [HIGH] Event evt_123: Choose deployment target
        """
        # Format notification message
        message = self._format_event(event)

        # Log notification
        logger.log(
            self._log_level,
            "Event notification: %s",
            message,
        )

        # Future: Send to Slack, email, webhooks
        # if self.config.slack_webhook:
        #     await self._send_slack(event)
        # if self.config.email_config:
        #     await self._send_email(event)

    async def notify_resolution(self, event: Event, response: str) -> None:
        """Notify that an event was resolved.

        Logs the resolution with the user's response. Future versions will
        send resolution notifications to configured channels.

        Args:
            event: Event that was resolved
            response: User's response to the event

        Example:
            >>> await notifier.notify_resolution(event, "Deploy to staging")
            # Logs: Event evt_123 resolved: Deploy to staging
        """
        message = f"Event {event.id} resolved: {response[:100]}"

        logger.log(
            self._log_level,
            "Event resolution: %s",
            message,
        )

        # Future: Send resolution notifications to channels

    def _format_event(self, event: Event) -> str:
        """Format event for notification display.

        Args:
            event: Event to format

        Returns:
            Formatted notification string

        Example:
            >>> msg = notifier._format_event(event)
            '[HIGH] evt_123 (proj_456): Choose deployment target'
        """
        parts = [
            f"[{event.priority.value.upper()}]",
            f"{event.id}",
            f"({event.project_id})",
            f"{event.title}",
        ]

        if event.options:
            parts.append(f"Options: {', '.join(event.options)}")

        return " ".join(parts)
