"""
Run command implementation for claude-mpm.

WHY: This module handles the main 'run' command which starts Claude sessions.
It's the most commonly used command and handles both interactive and non-interactive modes.
"""

import os
import subprocess
import sys
import time
import webbrowser
import logging
from pathlib import Path
from datetime import datetime

from ...core.logger import get_logger
from ...core.config import Config
from ...constants import LogLevel
from ..utils import get_user_input, list_agent_versions_at_startup
from ...utils.dependency_manager import ensure_socketio_dependencies
from ...deployment_paths import get_scripts_dir, get_package_root


def filter_claude_mpm_args(claude_args):
    """
    Filter out claude-mpm specific arguments from claude_args before passing to Claude CLI.
    
    WHY: The argparse.REMAINDER captures ALL remaining arguments, including claude-mpm
    specific flags like --monitor, etc. Claude CLI doesn't understand these
    flags and will error if they're passed through.
    
    DESIGN DECISION: We maintain a list of known claude-mpm flags to filter out,
    ensuring only genuine Claude CLI arguments are passed through.
    
    Args:
        claude_args: List of arguments captured by argparse.REMAINDER
        
    Returns:
        Filtered list of arguments safe to pass to Claude CLI
    """
    if not claude_args:
        return []
    
    # Known claude-mpm specific flags that should NOT be passed to Claude CLI
    # This includes all MPM-specific arguments from the parser
    mpm_flags = {
        # Run-specific flags
        '--monitor',
        '--websocket-port',
        '--no-hooks',
        '--no-tickets',
        '--intercept-commands',
        '--no-native-agents',
        '--launch-method',
        '--resume',
        # Dependency checking flags (MPM-specific)
        '--no-check-dependencies',
        '--force-check-dependencies',
        '--no-prompt',
        '--force-prompt',
        # Input/output flags (these are MPM-specific, not Claude CLI flags)
        '--input',
        '--non-interactive',
        # Common logging flags (these are MPM-specific, not Claude CLI flags)
        '--debug',
        '--logging',
        '--log-dir',
        # Framework flags (these are MPM-specific)
        '--framework-path',
        '--agents-dir',
        # Version flag (handled by MPM)
        '--version',
        # Short flags (MPM-specific equivalents)
        '-i',  # --input (MPM-specific, not Claude CLI)
        '-d'   # --debug (MPM-specific, not Claude CLI)
    }
    
    filtered_args = []
    i = 0
    while i < len(claude_args):
        arg = claude_args[i]
        
        # Check if this is a claude-mpm flag
        if arg in mpm_flags:
            # Skip this flag
            i += 1
            # Also skip the next argument if this flag expects a value
            value_expecting_flags = {
                '--websocket-port', '--launch-method', '--logging', '--log-dir', 
                '--framework-path', '--agents-dir', '-i', '--input'
            }
            optional_value_flags = {
                '--resume'  # These flags can have optional values (nargs="?")
            }
            
            if arg in value_expecting_flags and i < len(claude_args):
                i += 1  # Skip the value too
            elif arg in optional_value_flags and i < len(claude_args):
                # For optional value flags, only skip next arg if it doesn't start with --
                next_arg = claude_args[i]
                if not next_arg.startswith('--'):
                    i += 1  # Skip the value
        else:
            # This is not a claude-mpm flag, keep it
            filtered_args.append(arg)
            i += 1
    
    return filtered_args


def create_session_context(session_id, session_manager):
    """
    Create enhanced context for resumed sessions.
    
    WHY: When resuming a session, we want to provide Claude with context about
    the previous session including what agents were used and when it was created.
    This helps maintain continuity across session boundaries.
    
    Args:
        session_id: Session ID being resumed
        session_manager: SessionManager instance
        
    Returns:
        Enhanced context string with session information
    """
    try:
        from ...core.claude_runner import create_simple_context
    except ImportError:
        from claude_mpm.core.claude_runner import create_simple_context
    
    base_context = create_simple_context()
    
    session_data = session_manager.get_session_by_id(session_id)
    if not session_data:
        return base_context
    
    # Add session resumption information
    session_info = f"""

# Session Resumption

You are resuming session {session_id[:8]}... which was:
- Created: {session_data.get('created_at', 'unknown')}
- Last used: {session_data.get('last_used', 'unknown')}
- Context: {session_data.get('context', 'default')}
- Use count: {session_data.get('use_count', 0)}
"""
    
    # Add information about agents previously run in this session
    agents_run = session_data.get('agents_run', [])
    if agents_run:
        session_info += "\n- Previous agent activity:\n"
        for agent_info in agents_run[-5:]:  # Show last 5 agents
            session_info += f"  • {agent_info.get('agent', 'unknown')}: {agent_info.get('task', 'no description')[:50]}...\n"
        if len(agents_run) > 5:
            session_info += f"  (and {len(agents_run) - 5} other agent interactions)\n"
    
    session_info += "\nContinue from where you left off in this session."
    
    return base_context + session_info


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
    
    # Perform startup configuration check
    _check_configuration_health(logger)
    
    # Check for memory usage issues with .claude.json
    _check_claude_json_memory(args, logger)
    
    try:
        from ...core.claude_runner import ClaudeRunner, create_simple_context
        from ...core.session_manager import SessionManager
    except ImportError:
        from claude_mpm.core.claude_runner import ClaudeRunner, create_simple_context
        from claude_mpm.core.session_manager import SessionManager
    
    # Handle session resumption
    session_manager = SessionManager()
    resume_session_id = None
    resume_context = None
    
    if hasattr(args, 'resume') and args.resume:
        if args.resume == "last":
            # Resume the last interactive session
            resume_session_id = session_manager.get_last_interactive_session()
            if resume_session_id:
                session_data = session_manager.get_session_by_id(resume_session_id)
                if session_data:
                    resume_context = session_data.get("context", "default")
                    logger.info(f"Resuming session {resume_session_id} (context: {resume_context})")
                    print(f"🔄 Resuming session {resume_session_id[:8]}... (created: {session_data.get('created_at', 'unknown')})")
                else:
                    logger.warning(f"Session {resume_session_id} not found")
            else:
                logger.info("No recent interactive sessions found")
                print("ℹ️  No recent interactive sessions found to resume")
        else:
            # Resume specific session by ID
            resume_session_id = args.resume
            session_data = session_manager.get_session_by_id(resume_session_id)
            if session_data:
                resume_context = session_data.get("context", "default")
                logger.info(f"Resuming session {resume_session_id} (context: {resume_context})")
                print(f"🔄 Resuming session {resume_session_id[:8]}... (context: {resume_context})")
            else:
                logger.error(f"Session {resume_session_id} not found")
                print(f"❌ Session {resume_session_id} not found")
                print("💡 Use 'claude-mpm sessions' to list available sessions")
                return
    
    # Skip native agents if disabled
    if getattr(args, 'no_native_agents', False):
        print("Native agents disabled")
    else:
        # List deployed agent versions at startup
        list_agent_versions_at_startup()
        
        # Smart dependency checking - only when needed
        if getattr(args, 'check_dependencies', True):  # Default to checking
            try:
                from ...utils.agent_dependency_loader import AgentDependencyLoader
                from ...utils.dependency_cache import SmartDependencyChecker
                from ...utils.environment_context import should_prompt_for_dependencies
                
                # Initialize smart checker
                smart_checker = SmartDependencyChecker()
                loader = AgentDependencyLoader(auto_install=False)
                
                # Check if agents have changed
                has_changed, deployment_hash = loader.has_agents_changed()
                
                # Determine if we should check dependencies
                should_check, check_reason = smart_checker.should_check_dependencies(
                    force_check=getattr(args, 'force_check_dependencies', False),
                    deployment_hash=deployment_hash
                )
                
                if should_check:
                    # Check if we're in an environment where prompting makes sense
                    can_prompt, prompt_reason = should_prompt_for_dependencies(
                        force_prompt=getattr(args, 'force_prompt', False),
                        force_skip=getattr(args, 'no_prompt', False)
                    )
                    
                    logger.debug(f"Dependency check needed: {check_reason}")
                    logger.debug(f"Interactive prompting: {can_prompt} ({prompt_reason})")
                    
                    # Get or check dependencies
                    results, was_cached = smart_checker.get_or_check_dependencies(
                        loader=loader,
                        force_check=getattr(args, 'force_check_dependencies', False)
                    )
                    
                    # Show summary if there are missing dependencies
                    if results['summary']['missing_python']:
                        missing_count = len(results['summary']['missing_python'])
                        print(f"⚠️  {missing_count} agent dependencies missing")
                        
                        if can_prompt and missing_count > 0:
                            # Interactive prompt for installation
                            print(f"\n📦 Missing dependencies detected:")
                            for dep in results['summary']['missing_python'][:5]:
                                print(f"   - {dep}")
                            if missing_count > 5:
                                print(f"   ... and {missing_count - 5} more")
                            
                            print("\nWould you like to install them now?")
                            print("  [y] Yes, install missing dependencies")
                            print("  [n] No, continue without installing")
                            print("  [q] Quit")
                            
                            try:
                                response = input("\nChoice [y/n/q]: ").strip().lower()
                                if response == 'y':
                                    print("\n🔧 Installing missing dependencies...")
                                    loader.auto_install = True
                                    success, error = loader.install_missing_dependencies(
                                        results['summary']['missing_python']
                                    )
                                    if success:
                                        print("✅ Dependencies installed successfully")
                                        # Invalidate cache after installation
                                        smart_checker.cache.invalidate(deployment_hash)
                                    else:
                                        print(f"❌ Installation failed: {error}")
                                elif response == 'q':
                                    print("👋 Exiting...")
                                    return
                                else:
                                    print("⏩ Continuing without installing dependencies")
                            except (EOFError, KeyboardInterrupt):
                                print("\n⏩ Continuing without installing dependencies")
                        else:
                            # Non-interactive environment or prompting disabled
                            print("   Run 'pip install \"claude-mpm[agents]\"' to install all agent dependencies")
                            if not can_prompt:
                                logger.debug(f"Not prompting for installation: {prompt_reason}")
                    elif was_cached:
                        logger.debug("Dependencies satisfied (cached result)")
                    else:
                        logger.debug("All dependencies satisfied")
                else:
                    logger.debug(f"Skipping dependency check: {check_reason}")
                        
            except Exception as e:
                if args.logging != LogLevel.OFF.value:
                    logger.debug(f"Could not check agent dependencies: {e}")
                # Continue anyway - don't block execution
    
    # Create simple runner
    enable_tickets = not args.no_tickets
    raw_claude_args = getattr(args, 'claude_args', []) or []
    # Filter out claude-mpm specific flags before passing to Claude CLI
    claude_args = filter_claude_mpm_args(raw_claude_args)
    monitor_mode = getattr(args, 'monitor', False)
    
    # Debug logging for argument filtering
    if raw_claude_args != claude_args:
        logger.debug(f"Filtered claude-mpm args: {set(raw_claude_args) - set(claude_args)}")
        logger.debug(f"Passing to Claude CLI: {claude_args}")
    
    # Use the specified launch method (default: exec)
    launch_method = getattr(args, 'launch_method', 'exec')
    
    enable_websocket = getattr(args, 'monitor', False) or monitor_mode
    websocket_port = getattr(args, 'websocket_port', 8765)
    
    # Display Socket.IO server info if enabled
    if enable_websocket:
        # Auto-install Socket.IO dependencies if needed
        print("🔧 Checking Socket.IO dependencies...")
        dependencies_ok, error_msg = ensure_socketio_dependencies(logger)
        
        if not dependencies_ok:
            print(f"❌ Failed to install Socket.IO dependencies: {error_msg}")
            print("  Please install manually: pip install python-socketio aiohttp python-engineio")
            print("  Or install with extras: pip install claude-mpm[monitor]")
            # Continue anyway - some functionality might still work
        else:
            print("✓ Socket.IO dependencies ready")
        
        try:
            import socketio
            print(f"✓ Socket.IO server enabled at http://localhost:{websocket_port}")
            if launch_method == "exec":
                print("  Note: Socket.IO monitoring using exec mode with Claude Code hooks")
            
            # Launch Socket.IO dashboard if in monitor mode
            if monitor_mode:
                success, browser_opened = launch_socketio_monitor(websocket_port, logger)
                if not success:
                    print(f"⚠️  Failed to launch Socket.IO monitor")
                    print(f"  You can manually run: python scripts/launch_socketio_dashboard.py --port {websocket_port}")
                # Store whether browser was opened by CLI for coordination with ClaudeRunner
                args._browser_opened_by_cli = browser_opened
        except ImportError as e:
            print(f"⚠️  Socket.IO still not available after installation attempt: {e}")
            print("  This might be a virtual environment issue.")
            print("  Try: pip install python-socketio aiohttp python-engineio")
            print("  Or: pip install claude-mpm[monitor]")
    
    runner = ClaudeRunner(
        enable_tickets=enable_tickets,
        log_level=args.logging,
        claude_args=claude_args,
        launch_method=launch_method,
        enable_websocket=enable_websocket,
        websocket_port=websocket_port
    )
    
    # Agent deployment is handled by ClaudeRunner.setup_agents() and 
    # ClaudeRunner.deploy_project_agents_to_claude() which are called
    # in both run_interactive() and run_oneshot() methods.
    # No need for redundant deployment here.
    
    # Set browser opening flag for monitor mode
    if monitor_mode:
        runner._should_open_monitor_browser = True
        # Pass information about whether we already opened the browser in run.py
        runner._browser_opened_by_cli = getattr(args, '_browser_opened_by_cli', False)
    
    # Create context - use resumed session context if available
    if resume_session_id and resume_context:
        # For resumed sessions, create enhanced context with session information
        context = create_session_context(resume_session_id, session_manager)
        # Update session usage
        session_manager.active_sessions[resume_session_id]["last_used"] = datetime.now().isoformat()
        session_manager.active_sessions[resume_session_id]["use_count"] += 1
        session_manager._save_sessions()
    else:
        # Create a new session for tracking
        new_session_id = session_manager.create_session("default")
        context = create_simple_context()
        logger.info(f"Created new session {new_session_id}")
    
    # For monitor mode, we handled everything in launch_socketio_monitor
    # No need for ClaudeRunner browser delegation
    if monitor_mode:
        # Clear any browser opening flags since we handled it completely
        runner._should_open_monitor_browser = False
        runner._browser_opened_by_cli = True  # Prevent duplicate opening
    
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
            wrapper_path = get_scripts_dir() / "interactive_wrapper.py"
            if wrapper_path.exists():
                print("Starting interactive session with command interception...")
                subprocess.run([sys.executable, str(wrapper_path)])
            else:
                logger.warning("Interactive wrapper not found, falling back to normal mode")
                runner.run_interactive(context)
        else:
            runner.run_interactive(context)


def launch_socketio_monitor(port, logger):
    """
    Launch the Socket.IO monitoring dashboard using static HTML file.
    
    WHY: This function opens a static HTML file that connects to the Socket.IO server.
    This approach is simpler and more reliable than serving the dashboard from the server.
    The HTML file connects to whatever Socket.IO server is running on the specified port.
    
    DESIGN DECISION: Use file:// protocol to open static HTML file directly from filesystem.
    Pass the server port as a URL parameter so the dashboard knows which port to connect to.
    This decouples the dashboard from the server serving and makes it more robust.
    
    Args:
        port: Port number for the Socket.IO server
        logger: Logger instance for output
        
    Returns:
        tuple: (success: bool, browser_opened: bool) - success status and whether browser was opened
    """
    try:
        # Verify Socket.IO dependencies are available
        try:
            import socketio
            import aiohttp
            import engineio
            logger.debug("Socket.IO dependencies verified")
        except ImportError as e:
            logger.error(f"Socket.IO dependencies not available: {e}")
            print(f"❌ Socket.IO dependencies missing: {e}")
            print("  This is unexpected - dependency installation may have failed.")
            return False, False
        
        print(f"🚀 Setting up Socket.IO monitor on port {port}...")
        logger.info(f"Launching Socket.IO monitor on port {port}")
        
        socketio_port = port
        
        # Use HTTP URL to access dashboard from Socket.IO server
        dashboard_url = f'http://localhost:{socketio_port}'
        
        # Check if Socket.IO server is already running
        server_running = _check_socketio_server_running(socketio_port, logger)
        
        if server_running:
            print(f"✅ Socket.IO server already running on port {socketio_port}")
            
            # Check if it's managed by our daemon
            daemon_script = get_package_root() / "scripts" / "socketio_daemon.py"
            if daemon_script.exists():
                status_result = subprocess.run(
                    [sys.executable, str(daemon_script), "status"],
                    capture_output=True,
                    text=True
                )
                if "is running" in status_result.stdout:
                    print(f"   (Managed by Python daemon)")
            
            print(f"📊 Dashboard: {dashboard_url}")
            
            # Open browser with static HTML file
            try:
                # Check if we should suppress browser opening (for tests)
                if os.environ.get('CLAUDE_MPM_NO_BROWSER') != '1':
                    print(f"🌐 Opening dashboard in browser...")
                    open_in_browser_tab(dashboard_url, logger)
                    logger.info(f"Socket.IO dashboard opened: {dashboard_url}")
                else:
                    print(f"🌐 Browser opening suppressed (CLAUDE_MPM_NO_BROWSER=1)")
                    logger.info(f"Browser opening suppressed by environment variable")
                return True, True
            except Exception as e:
                logger.warning(f"Failed to open browser: {e}")
                print(f"⚠️  Could not open browser automatically")
                print(f"📊 Please open manually: {dashboard_url}")
                return True, False
        else:
            # Start standalone Socket.IO server
            print(f"🔧 Starting Socket.IO server on port {socketio_port}...")
            server_started = _start_standalone_socketio_server(socketio_port, logger)
            
            if server_started:
                print(f"✅ Socket.IO server started successfully")
                print(f"📊 Dashboard: {dashboard_url}")
                
                # Final verification that server is responsive using event-based checking
                final_check_passed = False
                check_start = time.time()
                max_wait = 3  # Maximum 3 seconds
                
                while time.time() - check_start < max_wait:
                    if _check_socketio_server_running(socketio_port, logger):
                        final_check_passed = True
                        break
                    # Use a very short sleep just to yield CPU
                    time.sleep(0.1)  # 100ms polling interval
                
                if not final_check_passed:
                    logger.warning("Server started but final connectivity check failed")
                    print(f"⚠️  Server may still be initializing. Dashboard should work once fully ready.")
                
                # Open browser with static HTML file
                try:
                    # Check if we should suppress browser opening (for tests)
                    if os.environ.get('CLAUDE_MPM_NO_BROWSER') != '1':
                        print(f"🌐 Opening dashboard in browser...")
                        open_in_browser_tab(dashboard_url, logger)
                        logger.info(f"Socket.IO dashboard opened: {dashboard_url}")
                    else:
                        print(f"🌐 Browser opening suppressed (CLAUDE_MPM_NO_BROWSER=1)")
                        logger.info(f"Browser opening suppressed by environment variable")
                    return True, True
                except Exception as e:
                    logger.warning(f"Failed to open browser: {e}")
                    print(f"⚠️  Could not open browser automatically")
                    print(f"📊 Please open manually: {dashboard_url}")
                    return True, False
            else:
                print(f"❌ Failed to start Socket.IO server")
                print(f"💡 Troubleshooting tips:")
                print(f"   - Check if port {socketio_port} is already in use")
                print(f"   - Verify Socket.IO dependencies: pip install python-socketio aiohttp")
                print(f"   - Try a different port with --websocket-port")
                return False, False
        
    except Exception as e:
        logger.error(f"Failed to launch Socket.IO monitor: {e}")
        print(f"❌ Failed to launch Socket.IO monitor: {e}")
        return False, False


def _check_socketio_server_running(port, logger):
    """
    Check if a Socket.IO server is running on the specified port.
    
    WHY: We need to detect existing servers to avoid conflicts and provide
    seamless experience regardless of whether server is already running.
    
    DESIGN DECISION: We try multiple endpoints and connection methods to ensure
    robust detection. Some servers may be starting up and only partially ready.
    Added retry logic to handle race conditions during server initialization.
    
    Args:
        port: Port number to check
        logger: Logger instance for output
        
    Returns:
        bool: True if server is running and responding, False otherwise
    """
    try:
        import urllib.request
        import urllib.error
        import socket
        
        # First, do a basic TCP connection check
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(2.0)  # Increased from 1.0s for slower connections
                result = s.connect_ex(('127.0.0.1', port))
                if result != 0:
                    logger.debug(f"TCP connection to port {port} failed (server not started yet)")
                    return False
        except Exception as e:
            logger.debug(f"TCP socket check failed for port {port}: {e}")
            return False
        
        # If TCP connection succeeds, try HTTP health check with retries
        # WHY: Even when TCP is accepting connections, the HTTP handler may not be ready
        max_retries = 3
        for retry in range(max_retries):
            try:
                response = urllib.request.urlopen(f'http://localhost:{port}/status', timeout=10)  # Increased from 5s to 10s
                
                if response.getcode() == 200:
                    content = response.read().decode()
                    logger.debug(f"✅ Socket.IO server health check passed on port {port} (attempt {retry + 1})")
                    logger.debug(f"📄 Server response: {content[:100]}...")
                    return True
                else:
                    logger.debug(f"⚠️ HTTP response code {response.getcode()} from port {port} (attempt {retry + 1})")
                    if retry < max_retries - 1:
                        # Use exponential backoff with shorter initial delay
                        backoff = min(0.1 * (2 ** retry), 1.0)  # 0.1s, 0.2s, 0.4s...
                        time.sleep(backoff)
                    
            except urllib.error.HTTPError as e:
                logger.debug(f"⚠️ HTTP error {e.code} from server on port {port} (attempt {retry + 1})")
                if retry < max_retries - 1 and e.code in [404, 503]:  # Server starting but not ready
                    logger.debug("Server appears to be starting, retrying...")
                    # Use exponential backoff for retries
                    backoff = min(0.1 * (2 ** retry), 1.0)
                    time.sleep(backoff)
                    continue
                return False
            except urllib.error.URLError as e:
                logger.debug(f"⚠️ URL error connecting to port {port} (attempt {retry + 1}): {e.reason}")
                if retry < max_retries - 1:
                    logger.debug("Connection refused - server may still be initializing, retrying...")
                    # Use exponential backoff for retries
                    backoff = min(0.1 * (2 ** retry), 1.0)
                    time.sleep(backoff)
                    continue
                return False
        
        # All retries exhausted
        logger.debug(f"Health check failed after {max_retries} attempts - server not fully ready")
        return False
            
    except (ConnectionError, OSError) as e:
        logger.debug(f"🔌 Connection error checking port {port}: {e}")
    except Exception as e:
        logger.debug(f"❌ Unexpected error checking Socket.IO server on port {port}: {e}")
    
    return False


def _start_standalone_socketio_server(port, logger):
    """
    Start a standalone Socket.IO server using the Python daemon.
    
    WHY: For monitor mode, we want a persistent server that runs independently
    of the Claude session. This allows users to monitor multiple sessions and
    keeps the dashboard available even when Claude isn't running.
    
    DESIGN DECISION: We use a pure Python daemon script to manage the server
    process. This avoids Node.js dependencies (like PM2) and provides proper
    process management with PID tracking.
    
    Args:
        port: Port number for the server
        logger: Logger instance for output
        
    Returns:
        bool: True if server started successfully, False otherwise
    """
    try:
        from ...deployment_paths import get_scripts_dir
        import subprocess
        
        # Get path to daemon script in package
        daemon_script = get_package_root() / "scripts" / "socketio_daemon.py"
        
        if not daemon_script.exists():
            logger.error(f"Socket.IO daemon script not found: {daemon_script}")
            return False
        
        logger.info(f"Starting Socket.IO server daemon on port {port}")
        
        # Start the daemon
        result = subprocess.run(
            [sys.executable, str(daemon_script), "start"],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            logger.error(f"Failed to start Socket.IO daemon: {result.stderr}")
            return False
        
        # Wait for server using event-based polling instead of fixed delays
        # WHY: Replace fixed sleep delays with active polling for faster startup detection
        max_wait_time = 15  # Maximum 15 seconds
        poll_interval = 0.1  # Start with 100ms polling
        
        logger.info(f"Waiting up to {max_wait_time} seconds for server to be ready...")
        
        # Give daemon minimal time to fork
        time.sleep(0.2)  # Reduced from 0.5s
        
        start_time = time.time()
        attempt = 0
        
        while time.time() - start_time < max_wait_time:
            attempt += 1
            elapsed = time.time() - start_time
            
            logger.debug(f"Checking server readiness (attempt {attempt}, elapsed {elapsed:.1f}s)")
            
            # Adaptive polling - start fast, slow down over time
            if elapsed < 2:
                poll_interval = 0.1  # 100ms for first 2 seconds
            elif elapsed < 5:
                poll_interval = 0.25  # 250ms for next 3 seconds
            else:
                poll_interval = 0.5  # 500ms after 5 seconds
            
            time.sleep(poll_interval)
            
            # Check if the daemon server is accepting connections
            if _check_socketio_server_running(port, logger):
                logger.info(f"✅ Standalone Socket.IO server started successfully on port {port}")
                logger.info(f"🕐 Server ready after {attempt} attempts ({elapsed:.1f}s)")
                return True
            else:
                logger.debug(f"Server not yet accepting connections on attempt {attempt}")
        
        # Timeout reached
        elapsed_total = time.time() - start_time
        logger.error(f"❌ Socket.IO server health check failed after {max_wait_time}s timeout ({attempt} attempts)")
        logger.warning(f"⏱️  Server may still be starting - try waiting a few more seconds")
        logger.warning(f"💡 The daemon process might be running but not yet accepting HTTP connections")
        logger.error(f"🔧 Troubleshooting steps:")
        logger.error(f"   - Wait a few more seconds and try again")
        logger.error(f"   - Check for port conflicts: lsof -i :{port}")
        logger.error(f"   - Try a different port with --websocket-port")
        logger.error(f"   - Verify dependencies: pip install python-socketio aiohttp")
        return False
            
    except Exception as e:
        logger.error(f"❌ Failed to start standalone Socket.IO server: {e}")
        import traceback
        logger.error(f"📋 Stack trace: {traceback.format_exc()}")
        logger.error(f"💡 This may be a dependency issue - try: pip install python-socketio aiohttp")
        return False



def open_in_browser_tab(url, logger):
    """
    Open URL in browser, attempting to reuse existing tabs when possible.
    
    WHY: Users prefer reusing browser tabs instead of opening new ones constantly.
    This function attempts platform-specific solutions for tab reuse.
    
    DESIGN DECISION: We try different methods based on platform capabilities,
    falling back to standard webbrowser.open() if needed.
    
    Args:
        url: URL to open
        logger: Logger instance for output
    """
    try:
        # Platform-specific optimizations for tab reuse
        import platform
        system = platform.system().lower()
        
        if system == "darwin":  # macOS
            # Just use the standard webbrowser module on macOS
            # The AppleScript approach is too unreliable
            webbrowser.open(url, new=0, autoraise=True)  # new=0 tries to reuse window
            logger.info("Opened browser on macOS")
                
        elif system == "linux":
            # On Linux, try to use existing browser session
            try:
                # This is a best-effort approach for common browsers
                webbrowser.get().open(url, new=0)  # new=0 tries to reuse existing window
                logger.info("Attempted Linux browser tab reuse")
            except Exception:
                webbrowser.open(url, autoraise=True)
                
        elif system == "windows":
            # On Windows, try to use existing browser
            try:
                webbrowser.get().open(url, new=0)  # new=0 tries to reuse existing window
                logger.info("Attempted Windows browser tab reuse")
            except Exception:
                webbrowser.open(url, autoraise=True)
        else:
            # Unknown platform, use standard opening
            webbrowser.open(url, autoraise=True)
            
    except Exception as e:
        logger.warning(f"Browser opening failed: {e}")
        # Final fallback
        webbrowser.open(url)


def _check_claude_json_memory(args, logger):
    """Check .claude.json file size and warn about memory issues.
    
    WHY: Large .claude.json files (>500KB) cause significant memory issues when
    using --resume. Claude Desktop loads the entire conversation history into
    memory, leading to 2GB+ memory consumption.
    
    DESIGN DECISIONS:
    - Warn at 500KB (conservative threshold)
    - Suggest cleanup command for remediation
    - Allow bypass with --force flag
    - Only check when using --resume
    
    Args:
        args: Parsed command line arguments
        logger: Logger instance for output
    """
    # Only check if using --resume
    if not hasattr(args, 'resume') or not args.resume:
        return
    
    claude_json_path = Path.home() / ".claude.json"
    
    # Check if file exists
    if not claude_json_path.exists():
        logger.debug("No .claude.json file found")
        return
    
    # Check file size
    file_size = claude_json_path.stat().st_size
    
    # Format size for display
    def format_size(size_bytes):
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f}{unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f}TB"
    
    # Get thresholds from configuration
    try:
        from ...core.config import Config
        config = Config()
        memory_config = config.get('memory_management', {})
        warning_threshold = memory_config.get('claude_json_warning_threshold_kb', 500) * 1024
        critical_threshold = memory_config.get('claude_json_critical_threshold_kb', 1024) * 1024
    except Exception as e:
        logger.debug(f"Could not load memory configuration: {e}")
        # Fall back to defaults
        warning_threshold = 500 * 1024  # 500KB
        critical_threshold = 1024 * 1024  # 1MB
    
    if file_size > critical_threshold:
        print(f"\n⚠️  CRITICAL: Large .claude.json file detected ({format_size(file_size)})")
        print(f"   This WILL cause memory issues when using --resume")
        print(f"   Claude Desktop may consume 2GB+ of memory\n")
        
        if not getattr(args, 'force', False):
            print("   Recommended actions:")
            print("   1. Run 'claude-mpm cleanup-memory' to archive old conversations")
            print("   2. Use --force to bypass this warning (not recommended)")
            print("\n   Would you like to continue anyway? [y/N]: ", end="")
            
            try:
                response = input().strip().lower()
                if response != 'y':
                    print("\n✅ Session cancelled. Run 'claude-mpm cleanup-memory' to fix this issue.")
                    import sys
                    sys.exit(0)
            except (EOFError, KeyboardInterrupt):
                print("\n✅ Session cancelled.")
                import sys
                sys.exit(0)
    
    elif file_size > warning_threshold:
        print(f"\n⚠️  Warning: .claude.json file is getting large ({format_size(file_size)})")
        print("   This may cause memory issues when using --resume")
        print("   💡 Consider running 'claude-mpm cleanup-memory' to archive old conversations\n")
        # Just warn, don't block execution
    
    logger.info(f".claude.json size: {format_size(file_size)}")


def _check_configuration_health(logger):
    """Check configuration health at startup and warn about issues.
    
    WHY: Configuration errors can cause silent failures, especially for response
    logging. This function proactively checks configuration at startup and warns
    users about any issues, providing actionable guidance.
    
    DESIGN DECISIONS:
    - Non-blocking: Issues are logged as warnings, not errors
    - Actionable: Provides specific commands to fix issues
    - Focused: Only checks critical configuration that affects runtime
    
    Args:
        logger: Logger instance for output
    """
    try:
        # Load configuration
        config = Config()
        
        # Validate configuration
        is_valid, errors, warnings = config.validate_configuration()
        
        # Get configuration status for additional context
        status = config.get_configuration_status()
        
        # Report critical errors that will affect functionality
        if errors:
            logger.warning("⚠️  Configuration issues detected:")
            for error in errors[:3]:  # Show first 3 errors
                logger.warning(f"  • {error}")
            if len(errors) > 3:
                logger.warning(f"  • ... and {len(errors) - 3} more")
            logger.info("💡 Run 'claude-mpm config validate' to see all issues and fixes")
            
        # Check response logging specifically since it's commonly misconfigured
        response_logging_enabled = config.get('response_logging.enabled', False)
        if not response_logging_enabled:
            logger.debug("Response logging is disabled (response_logging.enabled=false)")
        else:
            # Check if session directory is writable
            session_dir = Path(config.get('response_logging.session_directory', '.claude-mpm/responses'))
            if not session_dir.is_absolute():
                session_dir = Path.cwd() / session_dir
                
            if not session_dir.exists():
                try:
                    session_dir.mkdir(parents=True, exist_ok=True)
                    logger.debug(f"Created response logging directory: {session_dir}")
                except Exception as e:
                    logger.warning(f"Cannot create response logging directory {session_dir}: {e}")
                    logger.info("💡 Fix with: mkdir -p " + str(session_dir))
            elif not os.access(session_dir, os.W_OK):
                logger.warning(f"Response logging directory is not writable: {session_dir}")
                logger.info("💡 Fix with: chmod 755 " + str(session_dir))
                
        # Report non-critical warnings (only in debug mode)
        if warnings and logger.isEnabledFor(logging.DEBUG):
            logger.debug("Configuration warnings:")
            for warning in warnings:
                logger.debug(f"  • {warning}")
                
        # Log loaded configuration source for debugging
        if status.get('loaded_from') and status['loaded_from'] != 'defaults':
            logger.debug(f"Configuration loaded from: {status['loaded_from']}")
            
    except Exception as e:
        # Don't let configuration check errors prevent startup
        logger.debug(f"Configuration check failed (non-critical): {e}")
        # Only show user-facing message if it's likely to affect them
        if "yaml" in str(e).lower():
            logger.warning("⚠️  Configuration file may have YAML syntax errors")
            logger.info("💡 Validate with: claude-mpm config validate")