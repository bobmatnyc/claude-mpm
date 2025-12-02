"""
CLI parsers package for claude-mpm.

This package contains modular parser components that were extracted from the
monolithic parser.py file to improve maintainability and organization.

WHY: The original parser.py was 1,166 lines with a single 961-line function.
Breaking it into focused modules makes it easier to maintain and test.

DESIGN DECISION: Each parser module handles a specific command domain:
- base_parser.py: Common arguments and main parser setup
- run_parser.py: Run command arguments
- agent_parser.py: Agent management commands
- memory_parser.py: Memory management commands
- tickets_parser.py: Ticket management commands
- config_parser.py: Configuration commands
- monitor_parser.py: Monitoring commands
- mcp_parser.py: MCP Gateway commands
"""

from .base_parser import (
    SuggestingArgumentParser,
    add_common_arguments,
    create_parser,
    preprocess_args,
)
from .run_parser import add_run_arguments

__all__ = [
    "SuggestingArgumentParser",
    "add_common_arguments",
    "add_run_arguments",
    "create_parser",
    "preprocess_args",
]
