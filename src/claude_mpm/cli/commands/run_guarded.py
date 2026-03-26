"""
Run-guarded command implementation for claude-mpm.

WHY: This module handles the 'run-guarded' experimental command which runs
Claude sessions with additional safety guardrails and constraints.

DESIGN DECISIONS:
- Delegates to the main run_session handler with guarded mode enabled
- Kept separate from run.py to isolate experimental features
- Lazy-imported to avoid loading unless explicitly requested
"""


def execute_run_guarded(args) -> int:
    """
    Execute the run-guarded command.

    Args:
        args: Parsed command line arguments

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    from .run import run_session

    # Enable guarded mode by setting the flag on args
    args.guarded = getattr(args, "guarded", True)

    result = run_session(args)
    return result if result is not None else 0
