"""
Run command implementation for claude-mpm.

WHY: This module handles the main 'run' command which starts Claude sessions.
It's the most commonly used command and handles both interactive and non-interactive modes.
"""

import subprocess
import sys
from pathlib import Path

from ...core.logger import get_logger
from ...constants import LogLevel
from ..utils import get_user_input, list_agent_versions_at_startup


def run_session(args):
    """
    Run a simplified Claude session.
    
    WHY: This is the primary command that users interact with. It sets up the
    environment, optionally deploys agents, and launches Claude with the MPM framework.
    
    DESIGN DECISION: We use ClaudeRunner to handle the complexity of
    subprocess management and hook integration, keeping this function focused
    on high-level orchestration.
    
    Args:
        args: Parsed command line arguments
    """
    logger = get_logger("cli")
    if args.logging != LogLevel.OFF.value:
        logger.info("Starting Claude MPM session")
    
    try:
        from ...core.claude_runner import ClaudeRunner, create_simple_context
    except ImportError:
        from claude_mpm.core.claude_runner import ClaudeRunner, create_simple_context
    
    # Skip native agents if disabled
    if getattr(args, 'no_native_agents', False):
        print("Native agents disabled")
    else:
        # List deployed agent versions at startup
        list_agent_versions_at_startup()
    
    # Create simple runner
    enable_tickets = not args.no_tickets
    claude_args = getattr(args, 'claude_args', []) or []
    launch_method = getattr(args, 'launch_method', 'exec')
    enable_websocket = getattr(args, 'websocket', False)
    
    # Display WebSocket info if enabled
    if enable_websocket:
        try:
            import websockets
            print("✓ WebSocket server enabled at ws://localhost:8765")
            if launch_method == "exec":
                print("  Note: WebSocket monitoring limited in exec mode (use --launch-method subprocess for full features)")
        except ImportError:
            print("⚠️  WebSocket server requested but 'websockets' package not installed")
            print("  Install with: pip install websockets")
    
    runner = ClaudeRunner(
        enable_tickets=enable_tickets,
        log_level=args.logging,
        claude_args=claude_args,
        launch_method=launch_method,
        enable_websocket=enable_websocket
    )
    
    # Create basic context
    context = create_simple_context()
    
    # Run session based on mode
    if args.non_interactive or args.input:
        # Non-interactive mode
        user_input = get_user_input(args.input, logger)
        success = runner.run_oneshot(user_input, context)
        if not success:
            logger.error("Session failed")
    else:
        # Interactive mode
        if getattr(args, 'intercept_commands', False):
            # Use the interactive wrapper for command interception
            # WHY: Command interception requires special handling of stdin/stdout
            # which is better done in a separate Python script
            wrapper_path = Path(__file__).parent.parent.parent.parent.parent / "scripts" / "interactive_wrapper.py"
            if wrapper_path.exists():
                print("Starting interactive session with command interception...")
                subprocess.run([sys.executable, str(wrapper_path)])
            else:
                logger.warning("Interactive wrapper not found, falling back to normal mode")
                runner.run_interactive(context)
        else:
            runner.run_interactive(context)