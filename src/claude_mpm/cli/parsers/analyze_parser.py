"""
Parser configuration for analyze command.

WHY: This module adds the analyze subcommand to the CLI for code analysis
with mermaid diagram generation capabilities.

DESIGN DECISIONS:
- Support mermaid diagram generation via flags
- Allow specification of diagram types
- Enable target directory/file selection
- Follow existing parser patterns
"""

from pathlib import Path

from .base_parser import add_common_arguments


def add_analyze_subparser(subparsers):
    """Add analyze command parser.

    WHY: Provides CLI interface for code analysis with mermaid diagram
    generation, allowing users to visualize their codebase architecture.

    Args:
        subparsers: The subparsers object from argparse
    """
    parser = subparsers.add_parser(
        "analyze",
        aliases=["analysis", "code-analyze"],
        help="Analyze code and generate mermaid diagrams",
        description="Run code analysis with optional mermaid diagram generation",
    )

    # Add common arguments
    add_common_arguments(parser)

    # Analysis target options
    parser.add_argument(
        "--target",
        type=Path,
        default=Path.cwd(),
        help="Directory or file to analyze (default: current directory)",
    )

    parser.add_argument(
        "--recursive",
        action="store_true",
        default=True,
        help="Recursively analyze subdirectories (default: True)",
    )

    # Mermaid diagram options
    mermaid_group = parser.add_argument_group("mermaid diagram options")
    mermaid_group.add_argument(
        "--mermaid", action="store_true", help="Enable mermaid diagram generation"
    )

    mermaid_group.add_argument(
        "--mermaid-types",
        nargs="+",
        choices=[
            "entry_points",
            "class_diagram",
            "sequence",
            "flowchart",
            "state",
            "entity_relationship",
            "component",
            "dependency_graph",
            "call_graph",
            "architecture",
        ],
        default=["entry_points"],
        help="Types of mermaid diagrams to generate (default: entry_points)",
    )

    mermaid_group.add_argument(
        "--save-diagrams", action="store_true", help="Save generated diagrams to files"
    )

    mermaid_group.add_argument(
        "--diagram-output",
        type=Path,
        help="Directory to save diagrams (default: ./diagrams/)",
    )

    # Analysis options
    analysis_group = parser.add_argument_group("analysis options")
    analysis_group.add_argument(
        "--agent",
        default="code-analyzer",
        help="Agent to use for analysis (default: code-analyzer)",
    )

    analysis_group.add_argument(
        "--prompt", type=str, help="Additional prompt/instructions for the analysis"
    )

    analysis_group.add_argument(
        "--focus",
        nargs="+",
        choices=["security", "performance", "architecture", "quality", "documentation"],
        help="Focus areas for analysis",
    )

    # Session options
    session_group = parser.add_argument_group("session options")
    session_group.add_argument(
        "--session-id", type=str, help="Use specific session ID for analysis"
    )

    session_group.add_argument(
        "--no-session", action="store_true", help="Run without session management"
    )

    # Output options
    output_group = parser.add_argument_group("output options")
    output_group.add_argument(
        "--format",
        choices=["text", "json", "markdown"],
        default="text",
        help="Output format (default: text)",
    )

    output_group.add_argument(
        "--output", "-o", type=Path, help="Save analysis output to file"
    )

    # Note: --verbose/-v is already defined in base_parser, so removed to avoid conflict

    # Import the command function
    from ..commands.analyze import analyze_command

    parser.set_defaults(func=analyze_command)
