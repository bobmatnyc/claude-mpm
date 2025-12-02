#!/usr/bin/env python3
"""
Analyze Code Command
====================

WHY: Provides a CLI interface for analyzing codebases and generating
code trees with real-time visualization support.

DESIGN DECISIONS:
- Support multiple output formats (JSON, tree, dashboard)
- Show progress bar for terminal output
- Support filtering by language and patterns
- Enable real-time event streaming to dashboard
"""

import json
import sys
import time
from pathlib import Path
from typing import Any, List, Optional

try:
    from rich.console import Console
    from rich.progress import (
        BarColumn,
        Progress,
        SpinnerColumn,
        TaskProgressColumn,
        TextColumn,
        TimeRemainingColumn,
    )
    from rich.table import Table
    from rich.tree import Tree

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    Console = None

from ...core.enums import OutputFormat
from ...core.logging_config import get_logger
from ...tools.code_tree_analyzer import CodeTreeAnalyzer
from ...tools.code_tree_builder import CodeTreeBuilder
from ..shared import BaseCommand, CommandResult


class AnalyzeCodeCommand(BaseCommand):
    """Command for analyzing code structure and metrics.

    WHY: Provides users with insights into their codebase structure,
    complexity, and organization through various visualization options.
    """

    def __init__(self):
        super().__init__("analyze-code")
        self.logger = get_logger(__name__)
        self.console = Console() if RICH_AVAILABLE else None

    def validate_args(self, args) -> Optional[str]:
        """Validate command arguments.

        Args:
            args: Command arguments

        Returns:
            Error message if validation fails, None otherwise
        """
        # Validate path exists
        path = Path(args.path)
        if not path.exists():
            return f"Path does not exist: {path}"

        if not path.is_dir():
            return f"Path is not a directory: {path}"

        # Validate output format
        if args.output and str(args.output).lower() not in (
            OutputFormat.JSON,
            "tree",
            "stats",
        ):
            return f"Invalid output format: {args.output}"

        return None

    def run(self, args) -> CommandResult:
        """Execute the analyze-code command.

        Args:
            args: Command arguments

        Returns:
            Command execution result
        """
        path = Path(args.path).resolve()

        # Parse languages filter
        languages = None
        if args.languages:
            languages = [lang.strip().lower() for lang in args.languages.split(",")]

        # Parse ignore patterns
        ignore_patterns = None
        if args.ignore:
            ignore_patterns = [pattern.strip() for pattern in args.ignore.split(",")]

        try:
            # Phase 1: Build file tree
            if not args.no_tree:
                tree_result = self._build_file_tree(
                    path, ignore_patterns, args.max_depth
                )

                if args.output == "tree":
                    self._display_tree(tree_result)
                    return CommandResult(
                        success=True, message="File tree analysis complete"
                    )

            # Phase 2: Analyze code structure
            analysis_result = self._analyze_code(
                path,
                languages,
                ignore_patterns,
                args.max_depth,
                args.emit_events,
                args.no_cache,
            )

            # Handle output format
            if str(args.output).lower() == OutputFormat.JSON:
                # Output JSON to stdout
                json.dump(analysis_result, sys.stdout, indent=2, default=str)
                sys.stdout.write("\n")
            elif args.output == "stats":
                self._display_stats(analysis_result["stats"])
            else:
                # Default: display summary
                self._display_summary(analysis_result)

            # Save to file if specified
            if args.save:
                save_path = Path(args.save)
                with save_path.open("w") as f:
                    json.dump(analysis_result, f, indent=2, default=str)
                self.logger.info(f"Analysis saved to {save_path}")

            return CommandResult(
                success=True,
                message="Code analysis complete",
                data=analysis_result["stats"],
            )

        except Exception as e:
            self.logger.error(f"Analysis failed: {e}", exc_info=True)
            return CommandResult(success=False, message=f"Analysis failed: {e!s}")

    def _build_file_tree(
        self, path: Path, ignore_patterns: Optional[List[str]], max_depth: Optional[int]
    ) -> dict:
        """Build file tree structure.

        Args:
            path: Root path to analyze
            ignore_patterns: Patterns to ignore
            max_depth: Maximum depth to traverse

        Returns:
            Tree structure dictionary
        """
        if RICH_AVAILABLE and self.console:
            self.console.print(
                f"\n[bold blue]Building file tree for:[/bold blue] {path}"
            )

        builder = CodeTreeBuilder()

        # Progress tracking
        def progress_callback(file_path: Path, stats: dict):
            if RICH_AVAILABLE and self.console:
                # Update progress (simplified without progress bar for file tree)
                if stats["files_found"] % 100 == 0:
                    self.console.print(
                        f"  Scanned {stats['directories_scanned']} directories, "
                        f"found {stats['files_found']} files"
                    )

        start_time = time.time()
        tree = builder.build_tree(
            path,
            ignore_patterns=ignore_patterns,
            max_depth=max_depth,
            use_gitignore=True,
            calculate_hashes=False,
            progress_callback=progress_callback if not self.console else None,
        )

        duration = time.time() - start_time
        stats = builder.get_stats()
        stats["duration"] = duration

        if RICH_AVAILABLE and self.console:
            self.console.print(
                f"[green]✓[/green] Tree built in {duration:.2f}s - "
                f"{stats['files_found']} files in {stats['directories_scanned']} directories"
            )

        return {"tree": tree.to_dict(), "stats": stats}

    def _analyze_code(
        self,
        path: Path,
        languages: Optional[List[str]],
        ignore_patterns: Optional[List[str]],
        max_depth: Optional[int],
        emit_events: bool,
        no_cache: bool,
    ) -> dict:
        """Analyze code structure and metrics.

        Args:
            path: Root path to analyze
            languages: Languages to include
            ignore_patterns: Patterns to ignore
            max_depth: Maximum depth
            emit_events: Whether to emit Socket.IO events
            no_cache: Whether to skip cache

        Returns:
            Analysis results dictionary
        """
        if RICH_AVAILABLE and self.console:
            self.console.print("\n[bold blue]Analyzing code structure...[/bold blue]")

            if emit_events:
                self.console.print(
                    "[yellow]→ Emitting real-time events to dashboard[/yellow]"
                )

        # Create analyzer
        cache_dir = None if no_cache else Path.home() / ".claude-mpm" / "code-cache"
        analyzer = CodeTreeAnalyzer(emit_events=emit_events, cache_dir=cache_dir)

        # Show progress
        if RICH_AVAILABLE and self.console and not emit_events:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                TimeRemainingColumn(),
                console=self.console,
            ) as progress:
                task = progress.add_task("Analyzing files...", total=None)

                # Run analysis
                result = analyzer.analyze_directory(
                    path,
                    languages=languages,
                    ignore_patterns=ignore_patterns,
                    max_depth=max_depth,
                )

                progress.update(task, completed=100)
        else:
            # Run without progress bar
            result = analyzer.analyze_directory(
                path,
                languages=languages,
                ignore_patterns=ignore_patterns,
                max_depth=max_depth,
            )

        return result

    def _display_tree(self, tree_result: dict):
        """Display file tree in terminal.

        Args:
            tree_result: Tree structure dictionary
        """
        if not RICH_AVAILABLE or not self.console:
            # Fallback to simple text output
            self._print_tree_text(tree_result["tree"])
            return

        # Create rich tree
        tree = Tree(f"📁 {tree_result['tree']['name']}")
        self._build_rich_tree(tree, tree_result["tree"])

        self.console.print(tree)

        # Show stats
        stats = tree_result["stats"]
        self.console.print(
            f"\n[dim]Files: {stats['files_found']} | "
            f"Directories: {stats['directories_scanned']} | "
            f"Languages: {len(stats['languages'])}[/dim]"
        )

    def _build_rich_tree(
        self, rich_tree: Tree, node: dict, depth: int = 0, max_depth: int = 10
    ):
        """Recursively build rich tree display.

        Args:
            rich_tree: Rich Tree object
            node: Tree node dictionary
            depth: Current depth
            max_depth: Maximum depth to display
        """
        if depth >= max_depth:
            if node.get("children"):
                rich_tree.add("[dim]...[/dim]")
            return

        for child in node.get("children", []):
            if child["type"] == "directory":
                icon = "📁"
                style = "blue"
            else:
                # Get file icon based on language
                lang = child.get("metadata", {}).get("language", "")
                icon = self._get_file_icon(lang)
                style = "white"

            label = f"{icon} {child['name']}"

            if child["type"] == "directory" and child.get("children"):
                subtree = rich_tree.add(f"[{style}]{label}[/{style}]")
                self._build_rich_tree(subtree, child, depth + 1, max_depth)
            else:
                rich_tree.add(f"[{style}]{label}[/{style}]")

    def _get_file_icon(self, language: str) -> str:
        """Get icon for file based on language.

        Args:
            language: Programming language

        Returns:
            Icon string
        """
        icons = {
            "python": "🐍",
            "javascript": "📜",
            "typescript": "📘",
            "java": "☕",
            "go": "🐹",
            "rust": "🦀",
            "ruby": "💎",
            "php": "🐘",
            "cpp": "⚡",
            "c": "🔧",
            "csharp": "🔷",
            "swift": "🦉",
            "kotlin": "🟣",
            "html": "🌐",
            "css": "🎨",
            "json": "📋",
            "yaml": "📄",
            "markdown": "📝",
            "dockerfile": "🐋",
            "sql": "🗃️",
        }
        return icons.get(language, "📄")

    def _print_tree_text(self, node: dict, prefix: str = "", is_last: bool = True):
        """Print tree in simple text format.

        Args:
            node: Tree node
            prefix: Line prefix
            is_last: Whether this is the last child
        """
        if node["type"] == "directory":
            connector = "└── " if is_last else "├── "
            print(f"{prefix}{connector}{node['name']}/")

            children = node.get("children", [])
            for i, child in enumerate(children):
                extension = "    " if is_last else "│   "
                self._print_tree_text(child, prefix + extension, i == len(children) - 1)
        else:
            connector = "└── " if is_last else "├── "
            print(f"{prefix}{connector}{node['name']}")

    def _display_stats(self, stats: dict):
        """Display analysis statistics.

        Args:
            stats: Statistics dictionary
        """
        if not RICH_AVAILABLE or not self.console:
            # Simple text output
            print("\nCode Analysis Statistics:")
            print("-" * 40)
            for key, value in stats.items():
                print(f"{key}: {value}")
            return

        # Create rich table
        table = Table(title="Code Analysis Statistics", show_header=True)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="yellow")

        table.add_row("Files Processed", str(stats.get("files_processed", 0)))
        table.add_row("Total Nodes", str(stats.get("total_nodes", 0)))
        table.add_row("Classes", str(stats.get("classes", 0)))
        table.add_row("Functions/Methods", str(stats.get("functions", 0)))
        table.add_row("Imports", str(stats.get("imports", 0)))
        table.add_row("Average Complexity", f"{stats.get('avg_complexity', 0):.2f}")
        table.add_row("Duration", f"{stats.get('duration', 0):.2f}s")

        if stats.get("languages"):
            languages = ", ".join(stats["languages"])
            table.add_row("Languages", languages)

        self.console.print(table)

    def _display_summary(self, result: dict):
        """Display analysis summary.

        Args:
            result: Analysis result dictionary
        """
        stats = result.get("stats", {})

        if not RICH_AVAILABLE or not self.console:
            # Simple text output
            print("\n=== Code Analysis Summary ===")
            self._display_stats(stats)

            if result.get("nodes"):
                print(f"\nFound {len(result['nodes'])} code elements")

                # Show top complex functions
                complex_nodes = sorted(
                    [n for n in result["nodes"] if n.complexity > 5],
                    key=lambda x: x.complexity,
                    reverse=True,
                )[:5]

                if complex_nodes:
                    print("\nMost Complex Functions:")
                    for node in complex_nodes:
                        print(f"  - {node.name} (complexity: {node.complexity})")
            return

        # Rich output
        self.console.print("\n[bold green]Code Analysis Complete[/bold green]\n")

        # Display stats table
        self._display_stats(stats)

        # Display tree structure summary
        if result.get("tree"):
            tree_data = result["tree"]
            self.console.print(f"\n[bold]Project Structure:[/bold] {tree_data['name']}")

            # Count immediate children by type
            dirs = sum(
                1 for c in tree_data.get("children", []) if c["type"] == "directory"
            )
            files = sum(1 for c in tree_data.get("children", []) if c["type"] == "file")

            self.console.print(f"  Root contains: {dirs} directories, {files} files")

        # Show complexity insights
        if result.get("nodes"):
            nodes = result["nodes"]

            # Find most complex elements
            complex_nodes = sorted(
                [n for n in nodes if hasattr(n, "complexity") and n.complexity > 5],
                key=lambda x: x.complexity,
                reverse=True,
            )[:5]

            if complex_nodes:
                self.console.print("\n[bold]High Complexity Elements:[/bold]")
                for node in complex_nodes:
                    self.console.print(
                        f"  [red]⚠[/red] {node.name} "
                        f"([yellow]complexity: {node.complexity}[/yellow]) "
                        f"in {Path(node.file_path).name}"
                    )

            # Show files without docstrings
            no_docs = [
                n
                for n in nodes
                if n.node_type in ("class", "function", "method")
                and not n.has_docstring
            ]

            if no_docs:
                self.console.print(
                    f"\n[dim]{len(no_docs)} elements missing docstrings[/dim]"
                )


def manage_analyze_code(args: Any) -> int:
    """
    Entry point for the analyze-code command.

    WHY: Provides a consistent interface for CLI command execution,
    matching the pattern used by other commands in the CLI.

    Args:
        args: Parsed command line arguments

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    command = AnalyzeCodeCommand()

    # Validate arguments
    error = command.validate_args(args)
    if error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    # Execute command
    result = command.run(args)

    # Return appropriate exit code
    return 0 if result.success else 1
