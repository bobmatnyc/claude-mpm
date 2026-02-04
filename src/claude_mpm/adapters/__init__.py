"""CLI Adapters for alternative AI coding assistants."""

from .cli_adapters import (
    ADAPTERS,
    AuggieAdapter,
    ClaudeAdapter,
    CLIAdapter,
    CodexAdapter,
    GeminiAdapter,
    get_adapter,
    get_available_adapters,
)

__all__ = [
    "ADAPTERS",
    "AuggieAdapter",
    "CLIAdapter",
    "ClaudeAdapter",
    "CodexAdapter",
    "GeminiAdapter",
    "get_adapter",
    "get_available_adapters",
]
