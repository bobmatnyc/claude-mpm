"""
Postmortem command implementation for claude-mpm.

WHY: Provide a comprehensive analysis tool to help users identify, categorize,
and fix errors encountered during their session, with automated improvements
for framework code and suggestions for user code.

DESIGN DECISIONS:
- Leverages existing FailureTracker for error data
- Categorizes errors by source (script/skill/agent/user)
- Provides action-specific handling (auto-fix/update/PR/suggest)
- Supports dry-run mode for safety
"""

import sys
from pathlib import Path

from claude_mpm.core.logging_utils import get_logger
from claude_mpm.services.analysis import get_postmortem_service
from claude_mpm.services.analysis.postmortem_reporter import PostmortemReporter

logger = get_logger(__name__)


def add_postmortem_parser(subparsers):
    """Add postmortem command parser.

    WHY: This command helps users analyze session errors and generate
    actionable improvement suggestions based on error source.
    """
    parser = subparsers.add_parser(
        "postmortem",
        aliases=["pm-analysis"],
        help="Analyze session errors and suggest improvements",
        description="Perform comprehensive analysis of errors encountered during the session",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview analysis without making changes (default for destructive operations)",
    )

    parser.add_argument(
        "--auto-fix",
        action="store_true",
        help="Automatically apply fixes to scripts and skills",
    )

    parser.add_argument(
        "--create-prs",
        action="store_true",
        help="Create pull requests for agent improvements",
    )

    parser.add_argument(
        "--session-id",
        type=str,
        help="Analyze specific session (default: current session)",
    )

    parser.add_argument(
        "--format",
        choices=["terminal", "json", "markdown"],
        default="terminal",
        help="Output format (default: terminal)",
    )

    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        help="Save report to file",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Include detailed error traces and analysis",
    )

    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable colored output",
    )

    parser.set_defaults(func=postmortem_command)


def run_postmortem(args):
    """Main entry point for postmortem command (used by CLI).

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, 1 for warnings, 2 for errors)
    """
    return postmortem_command(args)


def postmortem_command(args):
    """Execute the postmortem command.

    WHY: Provides comprehensive error analysis with categorization and
    actionable improvements, helping users understand and fix issues
    encountered during their session.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, 1 for warnings, 2 for errors)
    """
    logger.info("Starting postmortem analysis")

    # Get postmortem service
    service = get_postmortem_service()

    try:
        # Analyze session
        report = service.analyze_session(session_id=args.session_id)

        # Handle output file
        output_file = args.output
        if output_file:
            # Ensure file extension matches format
            if args.format == "json" and not str(output_file).endswith(".json"):
                output_file = Path(str(output_file) + ".json")
            elif args.format == "markdown" and not str(output_file).endswith(".md"):
                output_file = Path(str(output_file) + ".md")

            # Create parent directories
            output_file = output_file.absolute()
            output_file.parent.mkdir(parents=True, exist_ok=True)

        # Determine output format
        output_format = args.format

        # Create reporter
        reporter = PostmortemReporter(
            use_color=not args.no_color,
            verbose=args.verbose,
        )

        # Output results
        if output_file:
            # Save to file
            try:
                with output_file.open("w") as f:
                    original_output = reporter.output
                    reporter.output = f
                    reporter.report(report, format=output_format)
                    reporter.output = original_output

                print(f"✅ Report saved to: {output_file}")

                # Print brief summary to terminal
                if report.total_errors > 0:
                    print(f"\n{report.total_errors} error(s) analyzed")
                    print(
                        f"{report.stats['total_actions']} improvement action(s) generated"
                    )
                else:
                    print("\n✅ No errors detected in session!")

            except Exception as e:
                logger.error(f"Failed to save report: {e}")
                print(f"❌ Failed to save report: {e!s}")
                # Still output to terminal
                reporter.report(report, format="terminal")
        else:
            # Output to terminal
            reporter.report(report, format=output_format)

        # Apply fixes if requested
        if args.auto_fix and not args.dry_run:
            exit_code = _apply_auto_fixes(report, args.verbose)
            if exit_code != 0:
                return exit_code

        # Create PRs if requested
        if args.create_prs and not args.dry_run:
            exit_code = _create_prs(report, args.verbose)
            if exit_code != 0:
                return exit_code

        # Dry-run message
        if args.dry_run and (args.auto_fix or args.create_prs):
            print("\n🔍 Dry-run mode: No changes applied")
            print("   Remove --dry-run to apply changes")

        # Determine exit code
        if report.total_errors == 0:
            return 0  # No errors

        if report.stats.get("critical_priority", 0) > 0:
            return 2  # Critical errors found

        return 1  # Non-critical errors found

    except KeyboardInterrupt:
        print("\nPostmortem analysis interrupted by user")
        return 130

    except Exception as e:
        logger.error(f"Postmortem analysis failed: {e}", exc_info=True)
        print(f"\n❌ Postmortem analysis failed: {e!s}")
        if args.verbose:
            import traceback

            traceback.print_exc()
        return 2


def _apply_auto_fixes(report, verbose: bool) -> int:
    """Apply auto-fix actions from report.

    Args:
        report: Postmortem report
        verbose: Show detailed output

    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    from claude_mpm.services.analysis import ActionType

    auto_fix_actions = report.get_actions_by_type(ActionType.AUTO_FIX)

    if not auto_fix_actions:
        print("\n✅ No auto-fixable errors found")
        return 0

    print(f"\n🔧 Applying {len(auto_fix_actions)} auto-fix action(s)...")

    import subprocess

    success_count = 0
    fail_count = 0

    for i, action in enumerate(auto_fix_actions, 1):
        print(f"\n[{i}/{len(auto_fix_actions)}] {action.description}")

        # Run each command
        for cmd in action.commands:
            if verbose:
                print(f"  Running: {cmd}")

            try:
                result = subprocess.run(
                    cmd,
                    check=False,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )

                if result.returncode == 0:
                    action.status = "completed"
                    if verbose:
                        print(f"  ✅ Success: {cmd}")
                else:
                    action.status = "failed"
                    action.error_message = result.stderr or result.stdout
                    print(f"  ❌ Failed: {cmd}")
                    if verbose and result.stderr:
                        print(f"     {result.stderr}")
                    fail_count += 1
                    break  # Stop on first failure for this action

            except subprocess.TimeoutExpired:
                action.status = "failed"
                action.error_message = "Command timed out"
                print(f"  ❌ Timeout: {cmd}")
                fail_count += 1
                break

            except Exception as e:
                action.status = "failed"
                action.error_message = str(e)
                print(f"  ❌ Error: {e}")
                fail_count += 1
                break

        if action.status == "completed":
            success_count += 1

    # Summary
    print("\n📊 Auto-fix Results:")
    print(f"  ✅ Successful: {success_count}")
    print(f"  ❌ Failed: {fail_count}")

    return 0 if fail_count == 0 else 1


def _create_prs(report, verbose: bool) -> int:
    """Create PRs for agent improvements.

    Args:
        report: Postmortem report
        verbose: Show detailed output

    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    from claude_mpm.services.analysis import ActionType

    pr_actions = report.get_actions_by_type(ActionType.CREATE_PR)

    if not pr_actions:
        print("\n✅ No PR actions needed")
        return 0

    print(f"\n🤖 Creating {len(pr_actions)} PR(s) for agent improvements...")

    # Check if we're in the agent cache git repo
    agent_cache_path = Path.home() / ".claude-mpm" / "cache" / "agents"

    if not agent_cache_path.exists():
        print(f"❌ Agent cache not found at: {agent_cache_path}")
        print("   Run 'claude-mpm agents sync' first")
        return 2

    success_count = 0
    fail_count = 0

    for i, action in enumerate(pr_actions, 1):
        print(f"\n[{i}/{len(pr_actions)}] {action.description}")

        try:
            # Check if file is in agent cache
            analysis = action.error_analysis
            if not analysis.affected_file:
                print("  ⚠️  Cannot determine affected file, skipping")
                action.status = "failed"
                action.error_message = "No affected file identified"
                fail_count += 1
                continue

            # For MVP, print PR template instead of actually creating
            # Full implementation would use GitHub CLI or API
            print("  📝 PR Template Generated:")
            print(f"     Branch: {action.pr_branch}")
            print(f"     Title: {action.pr_title}")

            if verbose:
                print("\n--- PR Body ---")
                print(action.pr_body)
                print("--- End PR Body ---\n")

            print("\n  ℹ️  To create PR manually:")
            print(f"     cd {agent_cache_path}")
            print(f"     git checkout -b {action.pr_branch}")
            print(f"     # Make your changes to {analysis.affected_file}")
            print(f"     git add {analysis.affected_file}")
            print(f'     git commit -m "{action.pr_title}"')
            print(f"     git push origin {action.pr_branch}")
            print(
                f'     gh pr create --title "{action.pr_title}" --body-file pr_body.md'
            )

            action.status = "completed"
            success_count += 1

        except Exception as e:
            logger.error(f"Failed to create PR: {e}")
            print(f"  ❌ Error: {e}")
            action.status = "failed"
            action.error_message = str(e)
            fail_count += 1

    # Summary
    print("\n📊 PR Creation Results:")
    print(f"  ✅ Templates generated: {success_count}")
    print(f"  ❌ Failed: {fail_count}")

    return 0 if fail_count == 0 else 1


# Optional: Standalone execution for testing
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Claude MPM Postmortem Analysis")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--auto-fix", action="store_true")
    parser.add_argument("--create-prs", action="store_true")
    parser.add_argument("--session-id", type=str)
    parser.add_argument(
        "--format", choices=["terminal", "json", "markdown"], default="terminal"
    )
    parser.add_argument("--output", "-o", type=Path)
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--no-color", action="store_true")

    args = parser.parse_args()

    sys.exit(postmortem_command(args))
