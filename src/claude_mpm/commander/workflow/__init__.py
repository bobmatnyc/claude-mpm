"""Event resolution workflow for MPM Commander.

This package provides event handling and notification capabilities for
managing blocking events that require user input.

Modules:
    event_handler: Handles blocking events and session pause/resume
    notifier: Sends notifications for events and resolutions

Classes:
    EventHandler: Main event resolution coordinator
    Notifier: Notification delivery system
    NotifierConfig: Configuration for notification channels

Example:
    >>> from claude_mpm.commander.workflow import EventHandler, Notifier
    >>> from claude_mpm.commander.workflow import NotifierConfig
    >>>
    >>> notifier = Notifier(NotifierConfig(log_level="INFO"))
    >>> handler = EventHandler(inbox, sessions)
    >>> await handler.process_event(event)
"""

from .event_handler import EventHandler
from .notifier import Notifier, NotifierConfig

__all__ = ["EventHandler", "Notifier", "NotifierConfig"]
