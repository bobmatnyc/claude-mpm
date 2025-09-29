#!/usr/bin/env python3
"""
MPM Doctor operational script.

WHY: This script provides the core functionality for the /mpm-doctor slash command.
All operational logic is contained here, while the CLI integration remains in the
command parser and interactive session handler.

DESIGN DECISIONS:
- Centralized diagnostic execution
- Support for multiple output formats
- Configurable check selection
- Lightweight wrapper around DiagnosticRunner
"""

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..services.diagnostics import DiagnosticRunner, DoctorReporter


def run_diagnostics(
    verbose: bool = False,
    fix: bool = False,
    checks: Optional[List[str]] = None,
    parallel: bool = False,
    output_format: str = "terminal",
    no_color: bool = False,
) -> Dict[str, Any]:
    """
    Execute MPM diagnostics with the specified configuration.

    WHY: Provides a single entry point for all diagnostic operations,
    whether called from CLI, interactive mode, or programmatically.

    Args:
        verbose: Show detailed diagnostic information
        fix: Attempt to fix issues automatically
        checks: List of specific checks to run (None for all)
        parallel: Run checks in parallel for faster execution
        output_format: Output format ("terminal", "json", "markdown")
        no_color: Disable colored output

    Returns:
        Dictionary containing:
        - success: bool - whether diagnostics completed successfully
        - summary: DiagnosticSummary object
        - error_count: int - number of errors found
        - warning_count: int - number of warnings found
        - message: str - optional error message if failed
    """
    from claude_mpm.core.logging_utils import get_logger

    logger = get_logger(__name__)

    # Create diagnostic runner
    runner = DiagnosticRunner(verbose=verbose, fix=fix)

    # Run diagnostics
    try:
        if checks:
            logger.info(f"Running specific checks: {', '.join(checks)}")
            summary = runner.run_specific_checks(checks)
        elif parallel:
            logger.info("Running diagnostics in parallel mode")
            summary = runner.run_diagnostics_parallel()
        else:
            logger.info("Running comprehensive diagnostics")
            summary = runner.run_diagnostics()

    except KeyboardInterrupt:
        return {
            "success": False,
            "summary": None,
            "error_count": 0,
            "warning_count": 0,
            "message": "Diagnostics interrupted by user",
        }
    except Exception as e:
        logger.error(f"Diagnostic failed: {e}")
        return {
            "success": False,
            "summary": None,
            "error_count": 1,
            "warning_count": 0,
            "message": f"Diagnostic failed: {e!s}",
        }

    # Return success with summary
    return {
        "success": True,
        "summary": summary,
        "error_count": summary.error_count,
        "warning_count": summary.warning_count,
        "message": None,
    }


def format_output(
    summary,
    output_format: str = "terminal",
    verbose: bool = False,
    no_color: bool = False,
) -> str:
    """
    Format diagnostic summary for output.

    Args:
        summary: DiagnosticSummary object
        output_format: Output format ("terminal", "json", "markdown")
        verbose: Show detailed information
        no_color: Disable colored output

    Returns:
        Formatted output string
    """
    # Create reporter
    reporter = DoctorReporter(use_color=not no_color, verbose=verbose)

    # Capture output as string for non-terminal formats
    if output_format != "terminal":
        import io
        import sys

        # Capture stdout
        old_stdout = sys.stdout
        sys.stdout = buffer = io.StringIO()

        try:
            reporter.report(summary, format=output_format)
            output = buffer.getvalue()
        finally:
            sys.stdout = old_stdout

        return output
    # For terminal format, just report directly
    reporter.report(summary, format=output_format)
    return ""


def run_doctor_slash_command(args: List[str]) -> bool:
    """
    Execute the /mpm-doctor slash command.

    WHY: Provides a simplified interface for the interactive mode slash command,
    parsing basic arguments and returning a simple success/failure result.

    Args:
        args: Command arguments (e.g., ['--verbose', '--no-color'])

    Returns:
        bool: True if successful, False otherwise
    """
    # Parse arguments
    verbose = "--verbose" in args or "-v" in args
    no_color = "--no-color" in args
    fix = "--fix" in args
    parallel = "--parallel" in args

    # Extract specific checks if provided
    checks = None
    if "--checks" in args:
        try:
            idx = args.index("--checks")
            if idx + 1 < len(args):
                # Get all arguments after --checks until next flag
                checks = []
                for i in range(idx + 1, len(args)):
                    if args[i].startswith("-"):
                        break
                    checks.append(args[i])
        except (ValueError, IndexError):
            pass

    # Print header
    print("\n" + "=" * 60)
    print("Claude MPM Doctor Report")
    print("=" * 60)

    # Run diagnostics
    result = run_diagnostics(
        verbose=verbose,
        fix=fix,
        checks=checks,
        parallel=parallel,
        output_format="terminal",
        no_color=no_color,
    )

    # Handle results
    if not result["success"]:
        print(f"\n❌ {result['message']}")
        if verbose and result.get("message", "").startswith("Diagnostic failed"):
            import traceback

            traceback.print_exc()
        return False

    # Format and display output
    format_output(
        result["summary"], output_format="terminal", verbose=verbose, no_color=no_color
    )

    # Return based on status
    return result["error_count"] == 0


def main():
    """
    Main entry point for standalone execution.

    WHY: Allows the script to be run directly for testing or debugging.
    """
    parser = argparse.ArgumentParser(
        description="Claude MPM Doctor - Diagnostic Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show detailed diagnostic information",
    )

    parser.add_argument(
        "--json", action="store_true", help="Output results in JSON format"
    )

    parser.add_argument(
        "--markdown", action="store_true", help="Output results in Markdown format"
    )

    parser.add_argument(
        "--fix",
        action="store_true",
        help="Attempt to fix issues automatically (experimental)",
    )

    parser.add_argument(
        "--checks",
        nargs="+",
        choices=[
            "installation",
            "configuration",
            "filesystem",
            "claude",
            "agents",
            "mcp",
            "monitor",
            "common",
        ],
        help="Run only specific checks",
    )

    parser.add_argument(
        "--parallel",
        action="store_true",
        help="Run checks in parallel for faster execution",
    )

    parser.add_argument(
        "--no-color", action="store_true", help="Disable colored output"
    )

    parser.add_argument("--output", "-o", type=Path, help="Save output to file")

    args = parser.parse_args()

    # Determine output format
    if args.json:
        output_format = "json"
    elif args.markdown:
        output_format = "markdown"
    else:
        output_format = "terminal"

    # Run diagnostics
    result = run_diagnostics(
        verbose=args.verbose,
        fix=args.fix,
        checks=args.checks,
        parallel=args.parallel,
        output_format=output_format,
        no_color=args.no_color,
    )

    # Handle failure
    if not result["success"]:
        print(f"\n❌ {result['message']}")
        sys.exit(2)

    # Format output
    output = format_output(
        result["summary"],
        output_format=output_format,
        verbose=args.verbose,
        no_color=args.no_color,
    )

    # Save to file if requested
    if args.output:
        try:
            args.output.write_text(output)
            print(f"Report saved to: {args.output}")
        except Exception as e:
            print(f"❌ Failed to save report: {e!s}")
            sys.exit(2)

    # Determine exit code
    if result["error_count"] > 0:
        sys.exit(2)  # Errors found
    elif result["warning_count"] > 0:
        sys.exit(1)  # Warnings found
    else:
        sys.exit(0)  # All OK


if __name__ == "__main__":
    main()
