"""Slack MPM Client - Slack integration for Claude Multi-Agent Project Manager."""

from .app import app, start_socket_mode
from .config import settings

__all__ = ["app", "settings", "start_socket_mode"]
