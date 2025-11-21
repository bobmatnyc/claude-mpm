#!/usr/bin/env python3
"""
Code Tree Analyzer CLI Module
==============================

WHY: Provides command-line interface for the code tree analyzer,
allowing it to be run as a subprocess from the dashboard.

DESIGN DECISIONS:
- Support JSON streaming output for real-time event processing
- Provide both file output and stdout streaming modes
- Include comprehensive error handling and logging
"""

import argparse
import json
import sys
from pathlib import Path

from .code_tree_analyzer import CodeTreeAnalyzer


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Analyze code structure and emit events"
    )

    parser.add_argument(
        "--path", type=str, required=True, help="Directory path to analyze"
    )

    parser.add_argument(
        "--languages",
        type=str,
        help="Comma-separated list of languages to include (e.g., python,javascript)",
    )

    parser.add_argument(
        "--max-depth", type=int, help="Maximum directory depth to traverse"
    )

    parser.add_argument(
        "--ignore",
        action="append",
        help="Patterns to ignore (can be specified multiple times)",
    )

    parser.add_argument(
        "--emit-events", action="store_true", help="Enable Socket.IO event emission"
    )

    parser.add_argument(
        "--output-format",
        choices=["json", "json-stream", "summary"],
        default="summary",
        help="Output format (default: summary)",
    )

    parser.add_argument(
        "--output-file", type=str, help="Output file path (stdout if not specified)"
    )

    parser.add_argument(
        "--cache-dir", type=str, help="Directory for caching analysis results"
    )

    return parser.parse_args()


def emit_json_event(event_type: str, data: dict, file=None):
    """Emit a JSON event to stdout or file.

    Args:
        event_type: Type of event
        data: Event data
        file: Output file handle (stdout if None)
    """
    event = {"type": event_type, "data": data}

    output = json.dumps(event)
    if file:
        file.write(output + "\n")
        file.flush()
    else:
        print(output, flush=True)


def main():
    """Main entry point for the analyzer CLI."""
    args = parse_arguments()

    # Parse path
    path = Path(args.path).resolve()
    if not path.exists():
        emit_json_event(
            "code:analysis:error", {"message": f"Path does not exist: {args.path}"}
        )
        sys.exit(1)

    if not path.is_dir():
        emit_json_event(
            "code:analysis:error", {"message": f"Path is not a directory: {args.path}"}
        )
        sys.exit(1)

    # Parse languages
    languages = None
    if args.languages:
        languages = [lang.strip() for lang in args.languages.split(",")]

    # Parse cache directory
    cache_dir = None
    if args.cache_dir:
        cache_dir = Path(args.cache_dir)

    # Open output file if specified
    output_file = None
    if args.output_file:
        try:
            output_file = Path(args.output_file).open("w")
        except Exception as e:
            emit_json_event(
                "code:analysis:error", {"message": f"Failed to open output file: {e}"}
            )
            sys.exit(1)

    try:
        # Create analyzer
        analyzer = CodeTreeAnalyzer(emit_events=args.emit_events, cache_dir=cache_dir)

        # Emit start event for JSON stream format
        if args.output_format == "json-stream":
            emit_json_event(
                "code:analysis:start",
                {
                    "path": str(path),
                    "languages": languages,
                    "max_depth": args.max_depth,
                },
                output_file,
            )

        # Run analysis
        result = analyzer.analyze_directory(
            directory=path,
            languages=languages,
            ignore_patterns=args.ignore,
            max_depth=args.max_depth,
        )

        # Output results based on format
        if args.output_format == "json":
            # Full JSON output
            output = json.dumps(result, indent=2, default=str)
            if output_file:
                output_file.write(output)
            else:
                print(output)

        elif args.output_format == "json-stream":
            # Streaming JSON events (already emitted during analysis)
            emit_json_event(
                "code:analysis:complete",
                {"path": str(path), "stats": result.get("stats", {})},
                output_file,
            )

        else:  # summary
            # Human-readable summary
            stats = result.get("stats", {})
            summary = f"""
Code Analysis Summary
=====================
Path: {path}
Files processed: {stats.get("files_processed", 0)}
Total nodes: {stats.get("total_nodes", 0)}
Classes: {stats.get("classes", 0)}
Functions: {stats.get("functions", 0)}
Imports: {stats.get("imports", 0)}
Languages: {", ".join(stats.get("languages", []))}
Average complexity: {stats.get("avg_complexity", 0):.2f}
Duration: {stats.get("duration", 0):.2f}s
"""
            if output_file:
                output_file.write(summary)
            else:
                print(summary)

    except KeyboardInterrupt:
        emit_json_event(
            "code:analysis:cancelled",
            {"message": "Analysis cancelled by user"},
            output_file,
        )
        sys.exit(130)

    except Exception as e:
        emit_json_event("code:analysis:error", {"message": str(e)}, output_file)
        sys.exit(1)

    finally:
        if output_file:
            output_file.close()


if __name__ == "__main__":
    main()
