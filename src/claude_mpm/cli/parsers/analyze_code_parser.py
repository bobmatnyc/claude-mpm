#!/usr/bin/env python3
"""
Analyze Code Parser
===================

WHY: Provides argument parsing for the analyze-code command,
defining available options and their validation.

DESIGN DECISIONS:
- Support multiple output formats for flexibility
- Enable Socket.IO event emission for dashboard integration
- Allow language and pattern filtering
- Include caching control options
"""

import argparse
from pathlib import Path
from typing import Optional


class AnalyzeCodeParser:
    """Parser for analyze-code command arguments.

    WHY: Centralizes argument definition and validation for the
    code analysis command, ensuring consistent interface.
    """

    def __init__(self):
        self.command_name = "analyze-code"
        self.help_text = "Analyze code structure and generate AST tree with metrics"

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Add analyze-code specific arguments.

        Args:
            parser: Argument parser to configure
        """
        # Required arguments
        parser.add_argument(
            "path",
            type=str,
            default=".",
            nargs="?",
            help="Path to analyze (default: current directory)",
        )

        # Output options
        output_group = parser.add_argument_group("output options")
        output_group.add_argument(
            "-o",
            "--output",
            choices=["json", "tree", "stats"],
            help="Output format (default: summary)",
        )
        output_group.add_argument(
            "--save", type=str, metavar="PATH", help="Save analysis results to file"
        )
        output_group.add_argument(
            "--emit-events",
            action="store_true",
            help="Emit real-time events to dashboard via Socket.IO",
        )

        # Filter options
        filter_group = parser.add_argument_group("filter options")
        filter_group.add_argument(
            "-l",
            "--languages",
            type=str,
            metavar="LANGS",
            help="Comma-separated list of languages to analyze (e.g., python,javascript)",
        )
        filter_group.add_argument(
            "-i",
            "--ignore",
            type=str,
            metavar="PATTERNS",
            help="Comma-separated list of patterns to ignore",
        )
        filter_group.add_argument(
            "--max-depth",
            type=int,
            metavar="N",
            help="Maximum directory depth to traverse",
        )
        filter_group.add_argument(
            "--no-tree", action="store_true", help="Skip file tree building phase"
        )

        # Performance options
        perf_group = parser.add_argument_group("performance options")
        perf_group.add_argument(
            "--no-cache",
            action="store_true",
            help="Disable caching of analysis results",
        )
        perf_group.add_argument(
            "--parallel",
            action="store_true",
            help="Use parallel processing for large codebases",
        )

        # Metric options
        metric_group = parser.add_argument_group("metric options")
        metric_group.add_argument(
            "--complexity-threshold",
            type=int,
            default=10,
            metavar="N",
            help="Complexity threshold for warnings (default: 10)",
        )
        metric_group.add_argument(
            "--include-metrics",
            action="store_true",
            help="Include detailed metrics in output",
        )

        # Note: --verbose and --debug are already defined in base_parser
        # so we don't add them here to avoid conflicts

    def validate_args(self, args: argparse.Namespace) -> Optional[str]:
        """Validate parsed arguments.

        Args:
            args: Parsed arguments

        Returns:
            Error message if validation fails, None otherwise
        """
        # Validate path
        path = Path(args.path)
        if not path.exists():
            return f"Path does not exist: {path}"

        if not path.is_dir():
            return f"Path is not a directory: {path}"

        # Validate save path if provided
        if args.save:
            save_path = Path(args.save)
            save_dir = save_path.parent
            if not save_dir.exists():
                return f"Save directory does not exist: {save_dir}"

        # Validate max depth
        if args.max_depth is not None and args.max_depth < 0:
            return "Max depth must be non-negative"

        # Validate complexity threshold
        if args.complexity_threshold < 1:
            return "Complexity threshold must be at least 1"

        return None

    def get_examples(self) -> list:
        """Get usage examples.

        Returns:
            List of example command strings
        """
        return [
            "claude-mpm analyze-code",
            "claude-mpm analyze-code /path/to/project",
            "claude-mpm analyze-code -l python,javascript",
            "claude-mpm analyze-code --output json --save analysis.json",
            "claude-mpm analyze-code --emit-events",
            "claude-mpm analyze-code --ignore test,vendor --max-depth 3",
            "claude-mpm analyze-code -o tree",
            "claude-mpm analyze-code -o stats --include-metrics",
        ]
