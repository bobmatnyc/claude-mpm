#!/usr/bin/env python3
"""Unified hook handler for Claude Code integration.

This script is called by hook_wrapper.sh, which is the shell script
that gets installed in ~/.claude/settings.json. The wrapper handles
environment setup and then executes this Python handler.

## Hook System Architecture:

The claude-mpm hook system follows an event-driven architecture where Claude Code
emits events that are intercepted by this handler. The system consists of:

1. **Event Source (Claude Code)**: Emits hook events for various actions
2. **Hook Wrapper (hook_wrapper.sh)**: Shell script that sets up the environment
3. **Hook Handler (this file)**: Python script that processes events
4. **Response Actions**: Continue, block, or modify Claude Code behavior

## Design Patterns Used:

1. **Chain of Responsibility**: Each hook type has its own handler method
2. **Strategy Pattern**: Different handling strategies for different event types
3. **Template Method**: Base handling logic with hook-specific implementations

## Event Flow:

1. User types in Claude Code -> Claude Code emits event
2. Event is passed to hook_wrapper.sh via stdin as JSON
3. Wrapper sets up Python environment and calls this handler
4. Handler reads event, logs it, and routes to appropriate method
5. Handler returns action response (continue/block) via stdout
6. Claude Code acts based on the response
"""

import json
import sys
import os
import re
import logging
from datetime import datetime
from pathlib import Path

# Add src to path for imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / 'src'))

from claude_mpm.core.logger import get_logger, setup_logging, LogLevel

# Don't initialize global logging here - we'll do it per-project
logger = None


class ClaudeHookHandler:
    """Handler for all Claude Code hook events.
    
    This is the main service class that implements the hook system logic.
    It acts as a central dispatcher for all hook events from Claude Code.
    
    The handler follows these principles:
    - **Fail-safe**: Always returns a continue action on errors
    - **Non-blocking**: Quick responses to avoid UI delays
    - **Project-aware**: Maintains separate logs per project
    - **Extensible**: Easy to add new commands and event handlers
    """
    
    def __init__(self):
        """Initialize the hook handler.
        
        Sets up the handler state and defines available MPM commands.
        The handler is stateless between invocations - each hook event
        creates a new instance.
        """
        self.event = None  # The current event being processed
        self.hook_type = None  # Type of hook event (UserPromptSubmit, etc.)
        
        # Registry of available MPM commands
        # This acts as a command registry pattern for extensibility
        self.mpm_args = {
            'status': 'Show claude-mpm system status',
            'agents': 'Show deployed agent versions',
            # Future commands can be added here:
            # 'config': 'Configure claude-mpm settings',
            # 'debug': 'Toggle debug mode',
            # 'logs': 'Show recent hook logs',
            # 'reload': 'Reload agent configurations',
        }
        
    def handle(self):
        """Main entry point for hook handling.
        
        This is the core method that:
        1. Reads the event from stdin (passed by Claude Code)
        2. Sets up project-specific logging
        3. Routes the event to the appropriate handler
        4. Returns the action response
        
        The method implements the Template Method pattern where the overall
        algorithm is defined here, but specific steps are delegated to
        specialized methods.
        
        Error Handling:
        - All exceptions are caught to ensure fail-safe behavior
        - Errors result in a 'continue' action to avoid blocking Claude Code
        - Debug logs are written to /tmp for troubleshooting
        """
        global logger
        try:
            # Quick debug log to file for troubleshooting
            # This is separate from the main logger for bootstrap debugging
            with open('/tmp/claude-mpm-hook.log', 'a') as f:
                f.write(f"[{datetime.now().isoformat()}] Hook called\n")
            
            # Read event from stdin
            # Claude Code passes the event as JSON on stdin
            # Format: {"hook_event_name": "...", "prompt": "...", ...}
            event_data = sys.stdin.read()
            self.event = json.loads(event_data)
            self.hook_type = self.event.get('hook_event_name', 'unknown')
            
            # Get the working directory from the event
            # This ensures logs are written to the correct project directory
            cwd = self.event.get('cwd', os.getcwd())
            project_dir = Path(cwd)
            
            # Initialize project-specific logging
            # Each project gets its own log directory to avoid conflicts
            # Logs are rotated daily by using date in filename
            log_dir = project_dir / '.claude-mpm' / 'logs'
            log_dir.mkdir(parents=True, exist_ok=True)
            
            # Set up logging for this specific project
            # Design decisions:
            # - One log file per day for easy rotation and cleanup
            # - Project-specific logger names to avoid cross-contamination
            # - Environment variable for log level control
            log_level = os.environ.get('CLAUDE_MPM_LOG_LEVEL', 'INFO')
            log_file = log_dir / f"hooks_{datetime.now().strftime('%Y%m%d')}.log"
            
            # Only set up logging if we haven't already for this project
            # This avoids duplicate handlers when multiple hooks fire quickly
            logger_name = f"claude_mpm_hooks_{project_dir.name}"
            if not logging.getLogger(logger_name).handlers:
                logger = setup_logging(
                    name=logger_name,
                    level=log_level,
                    log_dir=log_dir,
                    log_file=log_file
                )
            else:
                logger = logging.getLogger(logger_name)
            
            # Log more details about the hook type
            with open('/tmp/claude-mpm-hook.log', 'a') as f:
                f.write(f"[{datetime.now().isoformat()}] Hook type: {self.hook_type}\n")
                f.write(f"[{datetime.now().isoformat()}] Project: {project_dir}\n")
            
            # Log the prompt if it's UserPromptSubmit
            if self.hook_type == 'UserPromptSubmit':
                prompt = self.event.get('prompt', '')
                with open('/tmp/claude-mpm-hook.log', 'a') as f:
                    f.write(f"[{datetime.now().isoformat()}] Prompt: {prompt}\n")
            
            # Log the event if DEBUG logging is enabled
            self._log_event()
            
            # Route to appropriate handler based on event type
            # This implements the Chain of Responsibility pattern
            # Each handler method is responsible for its specific event type
            #
            # Available hook types:
            # - UserPromptSubmit: User submits a prompt (can intercept /mpm commands)
            # - PreToolUse: Before Claude uses a tool (can block/modify)
            # - PostToolUse: After tool execution (for logging/monitoring)
            # - Stop: Session or task ends
            # - SubagentStop: Subagent completes its task
            if self.hook_type == 'UserPromptSubmit':
                with open('/tmp/claude-mpm-hook.log', 'a') as f:
                    f.write(f"[{datetime.now().isoformat()}] About to call _handle_user_prompt_submit\n")
                return self._handle_user_prompt_submit()
            elif self.hook_type == 'PreToolUse':
                return self._handle_pre_tool_use()
            elif self.hook_type == 'PostToolUse':
                return self._handle_post_tool_use()
            elif self.hook_type == 'Stop':
                return self._handle_stop()
            elif self.hook_type == 'SubagentStop':
                return self._handle_subagent_stop()
            else:
                logger.debug(f"Unknown hook type: {self.hook_type}")
                return self._continue()
                
        except Exception as e:
            with open('/tmp/claude-mpm-hook.log', 'a') as f:
                f.write(f"[{datetime.now().isoformat()}] Hook handler error: {e}\n")
                import traceback
                f.write(traceback.format_exc())
            if logger:
                logger.error(f"Hook handler error: {e}")
            return self._continue()
    
    def _log_event(self):
        """Log the event details if DEBUG logging is enabled.
        
        This method provides visibility into the hook system's operation.
        It logs at different levels:
        - INFO: Basic event occurrence (always logged)
        - DEBUG: Full event details (only when DEBUG is enabled)
        
        The method handles different event types specially to avoid
        logging sensitive information or overly verbose data.
        """
        global logger
        if not logger:
            return
            
        # Check if DEBUG logging is enabled
        # logger.level might be an int or LogLevel enum
        try:
            if hasattr(logger.level, 'value'):
                debug_enabled = logger.level.value <= LogLevel.DEBUG.value
            else:
                # It's an int, compare with the DEBUG level value (10)
                debug_enabled = logger.level <= 10
        except:
            # If comparison fails, assume debug is disabled
            debug_enabled = False
            
        # Always log hook events at INFO level so they appear in the logs
        session_id = self.event.get('session_id', 'unknown')
        cwd = self.event.get('cwd', 'unknown')
        
        logger.info(f"Claude Code hook event: {self.hook_type} (session: {session_id[:8] if session_id != 'unknown' else 'unknown'})")
        
        if debug_enabled:
            logger.debug(f"Event in directory: {cwd}")
            logger.debug(f"Event data: {json.dumps(self.event, indent=2)}")
            
        # Log specific details based on hook type
        if self.hook_type == 'UserPromptSubmit':
            prompt = self.event.get('prompt', '')
            # Don't log full agent system prompts
            if prompt.startswith('You are Claude Code running in Claude MPM'):
                logger.info("UserPromptSubmit: System prompt for agent delegation")
            else:
                logger.info(f"UserPromptSubmit: {prompt[:100]}..." if len(prompt) > 100 else f"UserPromptSubmit: {prompt}")
        elif self.hook_type == 'PreToolUse':
            tool_name = self.event.get('tool_name', '')
            logger.info(f"PreToolUse: {tool_name}")
            if debug_enabled:
                tool_input = self.event.get('tool_input', {})
                logger.debug(f"Tool input: {json.dumps(tool_input, indent=2)}")
        elif self.hook_type == 'PostToolUse':
            tool_name = self.event.get('tool_name', '')
            exit_code = self.event.get('exit_code', 'N/A')
            logger.info(f"PostToolUse: {tool_name} (exit code: {exit_code})")
            if debug_enabled:
                tool_output = self.event.get('tool_output', '')
                logger.debug(f"Tool output: {tool_output[:200]}..." if len(str(tool_output)) > 200 else f"Tool output: {tool_output}")
        elif self.hook_type == 'Stop':
            reason = self.event.get('reason', 'unknown')
            timestamp = datetime.now().isoformat()
            logger.info(f"Stop event: reason={reason} at {timestamp}")
        elif self.hook_type == 'SubagentStop':
            agent_type = self.event.get('agent_type', 'unknown')
            agent_id = self.event.get('agent_id', 'unknown')
            reason = self.event.get('reason', 'unknown')
            timestamp = datetime.now().isoformat()
            logger.info(f"SubagentStop: agent_type={agent_type}, agent_id={agent_id}, reason={reason} at {timestamp}")
    
    def _handle_user_prompt_submit(self):
        """Handle UserPromptSubmit events.
        
        This is the most important handler as it intercepts user prompts
        before they reach the LLM. It can:
        - Detect and handle /mpm commands
        - Modify prompts before processing
        - Block prompts from reaching the LLM
        
        Returns:
            - Calls _continue() to let prompt pass through
            - Exits with code 2 to block LLM processing (for /mpm commands)
        
        Command Processing:
        The method checks if the prompt starts with '/mpm' and routes
        to the appropriate command handler. This allows claude-mpm to
        provide an in-IDE command interface.
        """
        try:
            prompt = self.event.get('prompt', '').strip()
            
            # Debug log
            with open('/tmp/claude-mpm-hook.log', 'a') as f:
                f.write(f"[{datetime.now().isoformat()}] UserPromptSubmit - Checking prompt: '{prompt}'\n")
            
            # Check if this is the /mpm command
            if prompt == '/mpm' or prompt.startswith('/mpm '):
                # Parse arguments
                parts = prompt.split(maxsplit=1)
                arg = parts[1] if len(parts) > 1 else ''
                
                with open('/tmp/claude-mpm-hook.log', 'a') as f:
                    f.write(f"[{datetime.now().isoformat()}] MPM command detected, arg: '{arg}'\n")
                
                # Route based on argument
                if arg == 'status' or arg.startswith('status '):
                    # Extract status args if any
                    status_args = arg[6:].strip() if arg.startswith('status ') else ''
                    return self._handle_mpm_status(status_args)
                elif arg == 'agents' or arg.startswith('agents '):
                    # Handle agents command
                    return self._handle_mpm_agents()
                else:
                    # Show help for empty or unknown argument
                    return self._handle_mpm_help(arg)
                    
        except Exception as e:
            with open('/tmp/claude-mpm-hook.log', 'a') as f:
                f.write(f"[{datetime.now().isoformat()}] Error in _handle_user_prompt_submit: {e}\n")
                import traceback
                f.write(traceback.format_exc())
        
        # For now, let everything else pass through
        return self._continue()
    
    def _handle_pre_tool_use(self):
        """Handle PreToolUse events.
        
        This handler is called before Claude executes any tool. It implements
        security policies by:
        - Checking for path traversal attempts
        - Ensuring file operations stay within the working directory
        - Blocking dangerous operations
        
        Security Design:
        - Fail-secure: Block suspicious operations
        - Clear error messages to help users understand restrictions
        - Log security events for auditing
        
        Returns:
            - JSON response with action="continue" to allow the tool
            - JSON response with action="block" and error message to prevent execution
        """
        tool_name = self.event.get('tool_name', '')
        tool_input = self.event.get('tool_input', {})
        
        # List of tools that perform write operations
        # These tools need special security checks to prevent
        # writing outside the project directory
        write_tools = ['Write', 'Edit', 'MultiEdit', 'NotebookEdit']
        
        # Check if this is a write operation
        if tool_name in write_tools:
            # Get the working directory from the event
            working_dir = Path(self.event.get('cwd', os.getcwd())).resolve()
            
            # Extract file path based on tool type
            file_path = None
            if tool_name in ['Write', 'Edit', 'NotebookEdit']:
                file_path = tool_input.get('file_path')
                if tool_name == 'NotebookEdit':
                    file_path = tool_input.get('notebook_path')
            elif tool_name == 'MultiEdit':
                file_path = tool_input.get('file_path')
            
            if file_path:
                # First check for path traversal attempts before resolving
                if '..' in str(file_path):
                    if logger:
                        logger.warning(f"Security: Potential path traversal attempt in {tool_name}: {file_path}")
                    response = {
                        "action": "block",
                        "error": f"Security Policy: Path traversal attempts are not allowed.\n\n"
                               f"The path '{file_path}' contains '..' which could be used to escape the working directory.\n"
                               f"Please use absolute paths or paths relative to the working directory without '..'."
                    }
                    print(json.dumps(response))
                    sys.exit(0)
                    return
                
                try:
                    # Resolve the file path to absolute path
                    target_path = Path(file_path).resolve()
                    
                    # Check if the target path is within the working directory
                    try:
                        target_path.relative_to(working_dir)
                    except ValueError:
                        # Path is outside working directory
                        if logger:
                            logger.warning(f"Security: Blocked {tool_name} operation outside working directory: {file_path}")
                        
                        # Return block action with helpful error message
                        response = {
                            "action": "block",
                            "error": f"Security Policy: Cannot write to files outside the working directory.\n\n"
                                   f"Working directory: {working_dir}\n"
                                   f"Attempted path: {file_path}\n\n"
                                   f"Please ensure all file operations are within the project directory."
                        }
                        print(json.dumps(response))
                        sys.exit(0)
                        return
                    
                        
                except Exception as e:
                    if logger:
                        logger.error(f"Error validating path in {tool_name}: {e}")
                    # In case of error, err on the side of caution and block
                    response = {
                        "action": "block",
                        "error": f"Error validating file path: {str(e)}\n\n"
                               f"Please ensure the path is valid and accessible."
                    }
                    print(json.dumps(response))
                    sys.exit(0)
                    return
        
        # For read operations and other tools, continue normally
        return self._continue()
    
    def _handle_post_tool_use(self):
        """Handle PostToolUse events.
        
        Called after a tool has been executed. Currently used for:
        - Logging tool execution results
        - Monitoring tool usage patterns
        - Future: Could modify tool outputs or trigger follow-up actions
        
        This handler always continues as it's for observation only.
        """
        # For now, just log and continue
        # Future enhancements could include:
        # - Modifying tool outputs
        # - Triggering notifications on certain conditions
        # - Collecting metrics on tool usage
        return self._continue()
    
    def _handle_stop(self):
        """Handle Stop events.
        
        Called when a Claude Code session or task ends. Useful for:
        - Cleanup operations
        - Final logging
        - Session statistics
        
        Currently just logs the event for monitoring purposes.
        """
        # Log the stop event and continue
        # Future: Could trigger cleanup or summary generation
        return self._continue()
    
    def _handle_subagent_stop(self):
        """Handle SubagentStop events.
        
        Called when a subagent completes its task. Provides:
        - Agent type and ID for tracking
        - Completion reason
        - Timing information
        
        This is particularly useful for multi-agent workflows to track
        which agents were involved and how they performed.
        """
        # Log the subagent stop event and continue
        # Future: Could aggregate subagent performance metrics
        return self._continue()
    
    def _handle_mpm_status(self, args=None):
        """Handle the /mpm status command.
        
        Displays comprehensive status information about the claude-mpm system.
        This helps users verify their installation and troubleshoot issues.
        
        Args:
            args: Optional arguments like --verbose for detailed output
        
        The method collects information about:
        - Version information
        - Python environment
        - Logging configuration
        - Hook system status
        
        Uses ANSI colors for better readability in the terminal.
        """
        # Parse arguments if provided
        verbose = False
        if args:
            verbose = '--verbose' in args or '-v' in args
        
        # Gather system information
        # Handle logger.level which might be int or LogLevel enum
        if hasattr(logger.level, 'name'):
            log_level_name = logger.level.name
        else:
            # It's an int, map it to name
            level_map = {
                0: 'NOTSET',
                10: 'DEBUG',
                20: 'INFO',
                30: 'WARNING',
                40: 'ERROR',
                50: 'CRITICAL'
            }
            log_level_name = level_map.get(logger.level, f"CUSTOM({logger.level})")
        
        status_info = {
            'claude_mpm_version': self._get_version(),
            'python_version': sys.version.split()[0],
            'project_root': str(project_root) if project_root.name != 'src' else str(project_root.parent),
            'logging_level': log_level_name,
            'hook_handler': 'claude_mpm.hooks.claude_hooks.hook_handler',
            'environment': {
                'CLAUDE_PROJECT_DIR': os.environ.get('CLAUDE_PROJECT_DIR', 'not set'),
                'PYTHONPATH': os.environ.get('PYTHONPATH', 'not set'),
            }
        }
        
        # Add verbose information if requested
        if verbose:
            status_info['hooks_configured'] = {
                'UserPromptSubmit': 'Active',
                'PreToolUse': 'Active',
                'PostToolUse': 'Active'
            }
            status_info['available_arguments'] = list(self.mpm_args.keys())
        
        # Format output
        output = self._format_status_output(status_info, verbose)
        
        # Block LLM processing and return our output
        print(output, file=sys.stderr)
        sys.exit(2)
    
    def _get_version(self):
        """Get claude-mpm version."""
        try:
            # First try to read from VERSION file in project root
            version_file = project_root.parent / 'VERSION'
            if not version_file.exists():
                # Try one more level up
                version_file = project_root.parent.parent / 'VERSION'
            
            if version_file.exists():
                with open(version_file, 'r') as f:
                    version = f.read().strip()
                    # Return just the base version for cleaner display
                    # e.g., "1.0.2.dev1+g4ecadd4.d20250726" -> "1.0.2.dev1"
                    if '+' in version:
                        version = version.split('+')[0]
                    return version
        except Exception:
            pass
        
        try:
            # Fallback to trying import
            from claude_mpm import __version__
            return __version__
        except:
            pass
        
        return 'unknown'
    
    def _format_status_output(self, info, verbose=False):
        """Format status information for display."""
        # Use same colors as help screen
        CYAN = '\033[96m'  # Bright cyan
        GREEN = '\033[92m'  # Green (works in help)
        BOLD = '\033[1m'
        RESET = '\033[0m'
        DIM = '\033[2m'
        
        output = f"\n{DIM}{'─' * 60}{RESET}\n"
        output += f"{CYAN}{BOLD}🔧 Claude MPM Status{RESET}\n"
        output += f"{DIM}{'─' * 60}{RESET}\n\n"
        
        output += f"{GREEN}Version:{RESET} {info['claude_mpm_version']}\n"
        output += f"{GREEN}Python:{RESET} {info['python_version']}\n"
        output += f"{GREEN}Project Root:{RESET} {info['project_root']}\n"  
        output += f"{GREEN}Logging Level:{RESET} {info['logging_level']}\n"
        output += f"{GREEN}Hook Handler:{RESET} {info['hook_handler']}\n"
        
        output += f"\n{CYAN}{BOLD}Environment:{RESET}\n"
        for key, value in info['environment'].items():
            output += f"{GREEN}  {key}: {value}{RESET}\n"
        
        if verbose:
            output += f"\n{CYAN}{BOLD}Hooks Configured:{RESET}\n"
            for hook, status in info.get('hooks_configured', {}).items():
                output += f"{GREEN}  {hook}: {status}{RESET}\n"
            
            output += f"\n{CYAN}{BOLD}Available Arguments:{RESET}\n"
            for arg in info.get('available_arguments', []):
                output += f"{GREEN}  /mpm {arg}{RESET}\n"
        
        output += f"\n{DIM}{'─' * 60}{RESET}"
        
        return output
    
    def _handle_mpm_agents(self):
        """Handle the /mpm agents command to display deployed agent versions.
        
        This command provides users with a quick way to check deployed agent versions
        directly from within Claude Code, maintaining consistency with the CLI
        and startup display functionality.
        
        Design Philosophy:
        - Reuse existing CLI functionality for consistency
        - Display agent versions in the same format as CLI startup
        - Graceful error handling with helpful messages
        
        The method imports and reuses the CLI's agent version display function
        to ensure consistent formatting across all interfaces.
        """
        try:
            # Import the agent version display function
            from claude_mpm.cli import _get_agent_versions_display
            
            # Get the formatted agent versions
            agent_versions = _get_agent_versions_display()
            
            if agent_versions:
                # Display the agent versions
                print(agent_versions, file=sys.stderr)
            else:
                # No agents found
                output = "\nNo deployed agents found\n"
                output += "\nTo deploy agents, run: claude-mpm --mpm:agents deploy\n"
                print(output, file=sys.stderr)
                
        except Exception as e:
            # Handle any errors gracefully
            output = f"\nError getting agent versions: {e}\n"
            output += "\nPlease check your claude-mpm installation.\n"
            print(output, file=sys.stderr)
            
            # Log the error for debugging
            if logger:
                logger.error(f"Error in _handle_mpm_agents: {e}")
        
        # Block LLM processing since we've handled the command
        sys.exit(2)
    
    def _handle_mpm_help(self, unknown_arg=None):
        """Show help for MPM commands.
        
        Displays a formatted help screen with available commands.
        This serves as the primary documentation for in-IDE commands.
        
        Args:
            unknown_arg: If provided, shows an error for unknown command
        
        Design:
        - Uses ANSI colors that work in Claude Code's output
        - Lists all registered commands from self.mpm_args
        - Provides examples for common use cases
        - Extensible: New commands automatically appear in help
        """
        # ANSI colors
        CYAN = '\033[96m'
        RED = '\033[91m'
        GREEN = '\033[92m'
        DIM = '\033[2m'
        RESET = '\033[0m'
        BOLD = '\033[1m'
        
        output = f"\n{DIM}{'─' * 60}{RESET}\n"
        output += f"{CYAN}{BOLD}🔧 Claude MPM Management{RESET}\n"
        output += f"{DIM}{'─' * 60}{RESET}\n\n"
        
        if unknown_arg:
            output += f"{RED}Unknown argument: {unknown_arg}{RESET}\n\n"
        
        output += f"{GREEN}Usage:{RESET} /mpm [argument]\n\n"
        output += f"{GREEN}Available arguments:{RESET}\n"
        for arg, desc in self.mpm_args.items():
            output += f"  {arg:<12} - {desc}\n"
        
        output += f"\n{GREEN}Examples:{RESET}\n"
        output += f"  /mpm         - Show this help\n"
        output += f"  /mpm status  - Show system status\n"
        output += f"  /mpm status --verbose - Show detailed status\n"
        output += f"  /mpm agents  - Show deployed agent versions\n"
        
        output += f"\n{DIM}{'─' * 60}{RESET}"
        
        # Block LLM processing and return our output
        print(output, file=sys.stderr)
        sys.exit(2)
    
    def _continue(self):
        """Return continue response to let prompt pass through.
        
        This is the default response for most hooks. It tells Claude Code
        to continue with normal processing.
        
        Response Format:
        - {"action": "continue"}: Process normally
        - Exit code 0: Success
        
        This method ensures consistent response formatting across all handlers.
        """
        response = {"action": "continue"}
        print(json.dumps(response))
        sys.exit(0)


def main():
    """Main entry point.
    
    Creates a new handler instance and processes the current event.
    Each hook invocation is independent - no state is maintained
    between calls. This ensures reliability and prevents memory leaks.
    """
    handler = ClaudeHookHandler()
    handler.handle()


if __name__ == "__main__":
    main()