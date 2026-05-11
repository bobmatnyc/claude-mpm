"""Decomposed handler modules for Claude Code hook events.

This package contains focused handler classes extracted from the original
``event_handlers.EventHandlers`` god class as part of issue #509. The public
:class:`EventHandlers` facade in ``event_handlers.py`` composes these handlers
and preserves the existing call surface used by ``hook_handler.py``.
"""

from .assistant_response_handler import AssistantResponseHandler
from .base import BaseEventHandler
from .passthrough_handlers import PassthroughHandlers
from .stop_handler import StopHandler
from .subagent_handler import SubagentHandler
from .tool_handler import ToolHandler
from .user_prompt_handler import UserPromptHandler

__all__ = [
    "AssistantResponseHandler",
    "BaseEventHandler",
    "PassthroughHandlers",
    "StopHandler",
    "SubagentHandler",
    "ToolHandler",
    "UserPromptHandler",
]
