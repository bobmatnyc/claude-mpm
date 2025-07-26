#!/usr/bin/env python3
"""Unified hook handler for Claude Code integration."""

import json
import sys
import os
import re
from datetime import datetime
from pathlib import Path

# Add src to path for imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / 'src'))

from claude_mpm.core.logger import get_logger, LogLevel

logger = get_logger(__name__)


class ClaudeHookHandler:
    """Handler for all Claude Code hook events."""
    
    def __init__(self):
        self.event = None
        self.hook_type = None
        
        # Available MPM arguments
        self.mpm_args = {
            'status': 'Show claude-mpm system status',
            # Add more arguments here as they're implemented
            # 'config': 'Configure claude-mpm settings',
            # 'debug': 'Toggle debug mode',
        }
        
    def handle(self):
        """Main entry point for hook handling."""
        try:
            # Quick debug log to file
            with open('/tmp/claude-mpm-hook.log', 'a') as f:
                f.write(f"[{datetime.now().isoformat()}] Hook called\n")
            
            # Read event from stdin
            event_data = sys.stdin.read()
            self.event = json.loads(event_data)
            self.hook_type = self.event.get('hook_event_name', 'unknown')
            
            # Log the prompt if it's UserPromptSubmit
            if self.hook_type == 'UserPromptSubmit':
                prompt = self.event.get('prompt', '')
                with open('/tmp/claude-mpm-hook.log', 'a') as f:
                    f.write(f"[{datetime.now().isoformat()}] Prompt: {prompt}\n")
            
            # Log the event if DEBUG logging is enabled
            self._log_event()
            
            # Route to appropriate handler
            if self.hook_type == 'UserPromptSubmit':
                with open('/tmp/claude-mpm-hook.log', 'a') as f:
                    f.write(f"[{datetime.now().isoformat()}] About to call _handle_user_prompt_submit\n")
                return self._handle_user_prompt_submit()
            elif self.hook_type == 'PreToolUse':
                return self._handle_pre_tool_use()
            elif self.hook_type == 'PostToolUse':
                return self._handle_post_tool_use()
            else:
                logger.debug(f"Unknown hook type: {self.hook_type}")
                return self._continue()
                
        except Exception as e:
            with open('/tmp/claude-mpm-hook.log', 'a') as f:
                f.write(f"[{datetime.now().isoformat()}] Hook handler error: {e}\n")
                import traceback
                f.write(traceback.format_exc())
            logger.error(f"Hook handler error: {e}")
            return self._continue()
    
    def _log_event(self):
        """Log the event details if DEBUG logging is enabled."""
        # Check if DEBUG logging is enabled
        # logger.level might be an int or LogLevel enum
        try:
            if hasattr(logger.level, 'value'):
                debug_enabled = logger.level.value <= LogLevel.DEBUG.value
            else:
                debug_enabled = logger.level <= LogLevel.DEBUG.value
        except:
            # If comparison fails, assume debug is disabled
            debug_enabled = False
            
        if debug_enabled:
            # Get session info to identify the agent/caller
            session_id = self.event.get('session_id', 'unknown')
            cwd = self.event.get('cwd', 'unknown')
            
            logger.debug(f"Hook event received: {self.hook_type} (session: {session_id[:8]}... in {cwd})")
            logger.debug(f"Event data: {json.dumps(self.event, indent=2)}")
            
            # Log specific details based on hook type
            if self.hook_type == 'UserPromptSubmit':
                prompt = self.event.get('prompt', '')
                logger.debug(f"User prompt: {prompt[:100]}..." if len(prompt) > 100 else f"User prompt: {prompt}")
            elif self.hook_type == 'PreToolUse':
                tool_name = self.event.get('tool_name', '')
                tool_input = self.event.get('tool_input', {})
                logger.debug(f"PreToolUse - Tool: {tool_name}")
                logger.debug(f"Tool input: {json.dumps(tool_input, indent=2)}")
            elif self.hook_type == 'PostToolUse':
                tool_name = self.event.get('tool_name', '')
                tool_output = self.event.get('tool_output', '')
                exit_code = self.event.get('exit_code', 'N/A')
                logger.debug(f"PostToolUse - Tool: {tool_name} (exit code: {exit_code})")
                logger.debug(f"Tool output: {tool_output[:200]}..." if len(str(tool_output)) > 200 else f"Tool output: {tool_output}")
    
    def _handle_user_prompt_submit(self):
        """Handle UserPromptSubmit events."""
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
        """Handle PreToolUse events."""
        # For now, just log and continue
        return self._continue()
    
    def _handle_post_tool_use(self):
        """Handle PostToolUse events."""
        # For now, just log and continue
        return self._continue()
    
    def _handle_mpm_status(self, args=None):
        """Handle the /mpm:status command."""
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
    
    def _handle_mpm_help(self, unknown_arg=None):
        """Show help for MPM commands."""
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
        
        output += f"\n{DIM}{'─' * 60}{RESET}"
        
        # Block LLM processing and return our output
        print(output, file=sys.stderr)
        sys.exit(2)
    
    def _continue(self):
        """Return continue response to let prompt pass through."""
        response = {"action": "continue"}
        print(json.dumps(response))
        sys.exit(0)


def main():
    """Main entry point."""
    handler = ClaudeHookHandler()
    handler.handle()


if __name__ == "__main__":
    main()