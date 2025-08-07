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
from pathlib import Path
from datetime import datetime

from ...core.logger import get_logger
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
                
                # Final verification that server is responsive
                final_check_passed = False
                for i in range(3):
                    if _check_socketio_server_running(socketio_port, logger):
                        final_check_passed = True
                        break
                    time.sleep(1)
                
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
                        time.sleep(0.5)  # Brief pause before retry
                    
            except urllib.error.HTTPError as e:
                logger.debug(f"⚠️ HTTP error {e.code} from server on port {port} (attempt {retry + 1})")
                if retry < max_retries - 1 and e.code in [404, 503]:  # Server starting but not ready
                    logger.debug("Server appears to be starting, retrying...")
                    time.sleep(0.5)
                    continue
                return False
            except urllib.error.URLError as e:
                logger.debug(f"⚠️ URL error connecting to port {port} (attempt {retry + 1}): {e.reason}")
                if retry < max_retries - 1:
                    logger.debug("Connection refused - server may still be initializing, retrying...")
                    time.sleep(0.5)
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
        
        # Wait for server to be ready with longer timeouts and progressive delays
        # WHY: Socket.IO server startup involves complex async initialization:
        # 1. Thread creation (~0.1s)
        # 2. Event loop setup (~1s) 
        # 3. aiohttp server binding (~2-5s)
        # 4. Socket.IO service initialization (~1-3s)
        # Total: up to 15+ seconds for full readiness (especially on Python 3.13)
        max_attempts = 30  # Increased from 20 to handle Python 3.13 slower initialization
        initial_delay = 1.0  # Increased from 0.5s to give daemon more time to fork
        max_delay = 3.0  # Increased from 2.0s for slower systems
        
        logger.info(f"Waiting up to {max_attempts * max_delay} seconds for server to be fully ready...")
        
        # Give the daemon initial time to fork and start before checking
        logger.debug("Allowing initial daemon startup time...")
        time.sleep(0.5)
        
        for attempt in range(max_attempts):
            # Progressive delay - start fast, then slow down for socket binding
            if attempt < 5:
                delay = initial_delay
            else:
                delay = min(max_delay, initial_delay + (attempt - 5) * 0.2)
            
            logger.debug(f"Checking server readiness (attempt {attempt + 1}/{max_attempts}, waiting {delay}s)")
            
            # Give the daemon process time to initialize and bind to the socket
            time.sleep(delay)
            
            # Check if the daemon server is accepting connections
            if _check_socketio_server_running(port, logger):
                logger.info(f"✅ Standalone Socket.IO server started successfully on port {port}")
                logger.info(f"🕐 Server ready after {attempt + 1} attempts ({(attempt + 1) * delay:.1f}s)")
                return True
            else:
                logger.debug(f"Server not yet accepting connections on attempt {attempt + 1}")
        
        logger.error(f"❌ Socket.IO server health check failed after {max_attempts} attempts ({max_attempts * max_delay:.1f}s)")
        logger.warning(f"⏱️  Server may still be starting - initialization can take 15+ seconds on some systems")
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