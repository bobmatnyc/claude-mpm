"""Hook to intercept and handle /mpm: commands."""

import os
import subprocess
import sys
from pathlib import Path

from claude_mpm.hooks.base_hook import SubmitHook, HookContext, HookResult
from claude_mpm.core.logger import get_logger

logger = get_logger(__name__)


class MpmCommandHook(SubmitHook):
    """Hook that intercepts /mpm commands and routes them to the command router."""
    
    def __init__(self):
        super().__init__(name="mpm_command", priority=1)  # High priority to intercept early
        self.command_prefix = "/mpm "
        self.command_router_path = self._find_command_router()
    
    def _find_command_router(self) -> Path:
        """Find the command router script."""
        # Look for command router relative to project root
        possible_paths = [
            Path(".claude/scripts/command_router.py"),
            Path(__file__).parent.parent.parent.parent.parent / ".claude/scripts/command_router.py"
        ]
        
        for path in possible_paths:
            if path.exists():
                return path.resolve()
        
        # Default path
        return Path(".claude/scripts/command_router.py").resolve()
    
    def execute(self, context: HookContext) -> HookResult:
        """Check for /mpm commands and execute them directly."""
        try:
            prompt = context.data.get('prompt', '').strip()
            
            # Check if this is an /mpm command
            if not prompt.startswith(self.command_prefix):
                # Not our command, pass through
                return HookResult(
                    success=True,
                    data=context.data,
                    modified=False
                )
            
            # Extract command and arguments
            command_line = prompt[len(self.command_prefix):].strip()
            parts = command_line.split()
            
            if not parts:
                return HookResult(
                    success=True,
                    data={
                        'prompt': '',
                        'response': "No command specified. Available commands: test",
                        'skip_llm': True
                    },
                    modified=True,
                    metadata={'command_handled': True}
                )
            
            command = parts[0]
            args = parts[1:]
            
            logger.info(f"Executing /mpm {command} with args: {args}")
            
            # Execute command using command router
            try:
                # Run the command router script
                cmd = [sys.executable, str(self.command_router_path), command] + args
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    check=False
                )
                
                if result.returncode == 0:
                    response = result.stdout.strip()
                else:
                    response = f"Command failed: {result.stderr.strip() or 'Unknown error'}"
                
                logger.info(f"Command result: {response}")
                
                # Return result without going to LLM
                return HookResult(
                    success=True,
                    data={
                        'prompt': '',  # Clear prompt to prevent LLM processing
                        'response': response,
                        'skip_llm': True  # Flag to skip LLM
                    },
                    modified=True,
                    metadata={
                        'command_handled': True,
                        'command': command,
                        'args': args
                    }
                )
                
            except Exception as e:
                logger.error(f"Failed to execute command: {e}")
                return HookResult(
                    success=True,
                    data={
                        'prompt': '',
                        'response': f"Error executing command: {str(e)}",
                        'skip_llm': True
                    },
                    modified=True,
                    metadata={'command_error': str(e)}
                )
                
        except Exception as e:
            logger.error(f"MPM command hook failed: {e}")
            # On error, pass through to normal processing
            return HookResult(
                success=False,
                error=str(e)
            )