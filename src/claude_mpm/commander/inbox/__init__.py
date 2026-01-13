"""Inbox system for MPM Commander.

Provides centralized event aggregation and display.
"""

from .dedup import DedupEntry, EventDeduplicator
from .inbox import Inbox, InboxCounts
from .models import InboxItem

__all__ = [
    "DedupEntry",
    "EventDeduplicator",
    "Inbox",
    "InboxCounts",
    "InboxItem",
]
