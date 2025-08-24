"""
Argument parser for claude-mpm CLI.

WHY: This module provides backward compatibility and delegates to the new modular
parser structure. The massive create_parser function has been split into focused
modules in the parsers/ package.

DESIGN DECISION: We maintain this file for backward compatibility while the actual
parser logic has been moved to parsers/ modules for better maintainability.

REFACTORING NOTE: The original 961-line create_parser function has been split into:
- parsers/base_parser.py: Common arguments and main parser setup
- parsers/run_parser.py: Run command arguments
- parsers/agents_parser.py: Agent management commands
- parsers/memory_parser.py: Memory management commands
- parsers/tickets_parser.py: Ticket management commands
- parsers/config_parser.py: Configuration commands
- parsers/monitor_parser.py: Monitoring commands
- parsers/mcp_parser.py: MCP Gateway commands
"""

# Import from the new modular structure
from .parsers import add_common_arguments, create_parser, preprocess_args

# Re-export for backward compatibility
__all__ = ["add_common_arguments", "create_parser", "preprocess_args"]

# Legacy functions removed - all functionality moved to parsers/ modules
# The original parser.py file contained a massive 961-line create_parser function
# that has been split into focused modules for better maintainability.
