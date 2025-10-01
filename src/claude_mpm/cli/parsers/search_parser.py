"""
Search command parser for mcp-vector-search integration.

This module provides argument parsing for the /mpm-search command.
"""

import argparse
from typing import Optional


def add_search_subparser(
    subparsers: argparse._SubParsersAction,
) -> argparse.ArgumentParser:
    """
    Add the search command parser.

    Args:
        subparsers: The subparsers action to add the search parser to.

    Returns:
        The created search parser.
    """
    search_parser = subparsers.add_parser(
        "mpm-search",
        aliases=["search"],
        help="Search codebase using semantic search",
        description=(
            "Search the codebase using semantic search powered by mcp-vector-search. "
            "Can search by query, find similar code, search by context, or manage the search index."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Search for code by query
  claude-mpm mpm-search "authentication logic"

  # Find code similar to a file
  claude-mpm mpm-search --similar src/auth.py

  # Search by contextual description
  claude-mpm mpm-search --context "find all API endpoints"

  # Index the project (required before searching)
  claude-mpm mpm-search --index

  # Force reindex the project
  claude-mpm mpm-search --index --force

  # Check index status
  claude-mpm mpm-search --status

  # Search with filters
  claude-mpm mpm-search "database" --language python --limit 20

  # Search with multiple file extensions
  claude-mpm mpm-search "test" --extensions .py --extensions .js

  # Find similar code to a specific function
  claude-mpm mpm-search --similar src/auth.py --function authenticate_user

  # Search with context and focus areas
  claude-mpm mpm-search --context "security vulnerabilities" --focus authentication --focus encryption

  # Output as JSON for processing
  claude-mpm mpm-search "api" --json
""",
    )

    # Primary search modes (mutually exclusive)
    search_mode = search_parser.add_mutually_exclusive_group()

    search_mode.add_argument(
        "query",
        nargs="?",
        help="Search query for semantic code search",
    )

    search_mode.add_argument(
        "--similar",
        "-s",
        metavar="FILE",
        help="Find code similar to the specified file",
    )

    search_mode.add_argument(
        "--context",
        "-c",
        metavar="DESCRIPTION",
        help="Search by contextual description of what you're looking for",
    )

    # Index management options
    search_parser.add_argument(
        "--index",
        action="store_true",
        help="Index or reindex the project codebase",
    )

    search_parser.add_argument(
        "--status",
        action="store_true",
        help="Check project indexing status and statistics",
    )

    # Search filters and options
    search_parser.add_argument(
        "--limit",
        "-l",
        type=int,
        default=10,
        metavar="N",
        help="Maximum number of results to return (default: 10, max: 50)",
    )

    search_parser.add_argument(
        "--threshold",
        "-t",
        type=float,
        default=0.3,
        metavar="SCORE",
        help="Similarity threshold between 0.0 and 1.0 (default: 0.3)",
    )

    search_parser.add_argument(
        "--language",
        metavar="LANG",
        help="Filter by programming language (e.g., python, javascript, go)",
    )

    search_parser.add_argument(
        "--extensions",
        action="append",
        metavar="EXT",
        help="Filter by file extensions (e.g., .py, .js). Can be specified multiple times",
    )

    # Options for --similar mode
    search_parser.add_argument(
        "--function",
        "-f",
        metavar="NAME",
        help="Function name within the file (used with --similar)",
    )

    # Options for --context mode
    search_parser.add_argument(
        "--focus",
        action="append",
        metavar="AREA",
        help="Focus areas for contextual search (e.g., security, performance). Can be specified multiple times",
    )

    # Options for --index mode
    search_parser.add_argument(
        "--force",
        action="store_true",
        help="Force reindexing even if index already exists (used with --index)",
    )

    # Output options
    search_parser.add_argument(
        "--json",
        action="store_true",
        dest="output_json",
        help="Output results as JSON instead of formatted text",
    )

    # Additional filters
    search_parser.add_argument(
        "--class",
        dest="class_name",
        metavar="NAME",
        help="Filter by class name",
    )

    search_parser.add_argument(
        "--files",
        metavar="PATTERN",
        help="Filter by file patterns (e.g., '*.py' or 'src/*.js')",
    )

    # Verbose output
    search_parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose output with additional details",
    )

    return search_parser


def validate_search_args(args: argparse.Namespace) -> Optional[str]:
    """
    Validate search command arguments.

    Args:
        args: Parsed command line arguments.

    Returns:
        Error message if validation fails, None otherwise.
    """
    # Check threshold is in valid range
    if hasattr(args, "threshold") and args.threshold is not None:
        if not 0.0 <= args.threshold <= 1.0:
            return "Similarity threshold must be between 0.0 and 1.0"

    # Check limit is reasonable
    if hasattr(args, "limit") and args.limit is not None:
        if args.limit < 1:
            return "Limit must be at least 1"
        if args.limit > 50:
            return "Limit cannot exceed 50"

    # Check that function is only used with --similar
    if (
        hasattr(args, "function")
        and args.function
        and not getattr(args, "similar", None)
    ):
        return "--function can only be used with --similar"

    # Check that focus is only used with --context
    if hasattr(args, "focus") and args.focus and not getattr(args, "context", None):
        return "--focus can only be used with --context"

    # Check that force is only used with --index
    if hasattr(args, "force") and args.force and not getattr(args, "index", False):
        return "--force can only be used with --index"

    # Ensure at least one operation is specified
    if hasattr(args, "command") and args.command in ["mpm-search", "search"]:
        has_operation = any(
            [
                getattr(args, "query", None),
                getattr(args, "similar", None),
                getattr(args, "context", None),
                getattr(args, "index", False),
                getattr(args, "status", False),
            ]
        )
        if not has_operation:
            return "No search operation specified. Use --help for options."

    return None
