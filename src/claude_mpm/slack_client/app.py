"""Slack Bolt application initialization."""

import logging

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from .config import settings

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Initialize Bolt app
app = App(
    token=settings.slack_bot_token,
    signing_secret=settings.slack_signing_secret,
)


def register_handlers() -> None:
    """Register all command and event handlers."""
    from .handlers import commands  # noqa: F401

    logger.info("Handlers registered successfully")


def start_socket_mode() -> None:
    """Start the app in Socket Mode."""
    register_handlers()
    handler = SocketModeHandler(app, settings.slack_app_token)
    logger.info("Starting Slack MPM client in Socket Mode...")
    handler.start()


if __name__ == "__main__":
    start_socket_mode()
