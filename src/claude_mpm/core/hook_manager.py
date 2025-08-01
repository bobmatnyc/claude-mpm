"""Hook manager for manually triggering hook events in PM operations.

This module provides a way for the PM agent to manually trigger hook events
that would normally be handled by Claude Code's hook system. This ensures
consistency between PM operations and regular agent operations.

WHY this is needed:
- PM runs directly in Python, bypassing Claude Code's hook system
- TodoWrite and other PM operations should trigger the same hooks as agent operations
- Ensures consistent event streaming to Socket.IO dashboard
"""

import json
import os
import subprocess
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

from ..core.logger import get_logger
from ..deployment_paths import get_package_root


class HookManager:
    """Manager for manually triggering hook events from PM operations.
    
    WHY this design:
    - Mimics Claude Code's hook event structure exactly
    - Uses the same hook handler that regular agents use
    - Provides session tracking consistent with regular hook events
    - Enables PM operations to appear in Socket.IO dashboard
    """
    
    def __init__(self):
        self.logger = get_logger("hook_manager")
        self.session_id = self._get_or_create_session_id()
        self.hook_handler_path = self._find_hook_handler()
        
    def _get_or_create_session_id(self) -> str:
        """Get or create a session ID for hook events."""
        # Try to get session ID from environment (set by ClaudeRunner)
        session_id = os.environ.get('CLAUDE_MPM_SESSION_ID')
        if not session_id:
            # Generate new session ID
            session_id = str(uuid.uuid4())
            os.environ['CLAUDE_MPM_SESSION_ID'] = session_id
        return session_id
    
    def _find_hook_handler(self) -> Optional[Path]:
        """Find the hook handler script."""
        try:
            # Look for hook handler in the expected location
            hook_handler = get_package_root() / "hooks" / "claude_hooks" / "hook_handler.py"
            
            if hook_handler.exists():
                return hook_handler
            else:
                self.logger.warning(f"Hook handler not found at: {hook_handler}")
                return None
        except Exception as e:
            self.logger.error(f"Error finding hook handler: {e}")
            return None
    
    def trigger_pre_tool_hook(self, tool_name: str, tool_args: Dict[str, Any] = None) -> bool:
        """Trigger PreToolUse hook event.
        
        Args:
            tool_name: Name of the tool being used (e.g., "TodoWrite")
            tool_args: Arguments passed to the tool
            
        Returns:
            bool: True if hook was triggered successfully
        """
        return self._trigger_hook_event("PreToolUse", {
            "tool_name": tool_name,
            "tool_args": tool_args or {},
            "timestamp": datetime.utcnow().isoformat()
        })
    
    def trigger_post_tool_hook(self, tool_name: str, exit_code: int = 0, result: Any = None) -> bool:
        """Trigger PostToolUse hook event.
        
        Args:
            tool_name: Name of the tool that was used
            exit_code: Exit code (0 for success, non-zero for error)
            result: Result returned by the tool
            
        Returns:
            bool: True if hook was triggered successfully
        """
        return self._trigger_hook_event("PostToolUse", {
            "tool_name": tool_name,
            "exit_code": exit_code,
            "result": str(result) if result is not None else None,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    def trigger_user_prompt_hook(self, prompt: str) -> bool:
        """Trigger UserPromptSubmit hook event.
        
        Args:
            prompt: The user prompt
            
        Returns:
            bool: True if hook was triggered successfully
        """
        return self._trigger_hook_event("UserPromptSubmit", {
            "prompt": prompt,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    def _trigger_hook_event(self, hook_type: str, event_data: Dict[str, Any]) -> bool:
        """Trigger a hook event by calling the hook handler.
        
        Args:
            hook_type: Type of hook event
            event_data: Event data
            
        Returns:
            bool: True if hook was triggered successfully
        """
        if not self.hook_handler_path:
            self.logger.debug("Hook handler not available - skipping hook event")
            return False
        
        try:
            # Create the hook event in the same format as Claude Code
            hook_event = {
                "hook_event_name": hook_type,
                "session_id": self.session_id,
                "timestamp": datetime.utcnow().isoformat(),
                **event_data
            }
            
            # Convert to JSON
            event_json = json.dumps(hook_event)
            
            # Call the hook handler
            env = os.environ.copy()
            env['CLAUDE_MPM_HOOK_DEBUG'] = 'true'  # Enable debug logging
            
            result = subprocess.run(
                ["python", str(self.hook_handler_path)],
                input=event_json,
                text=True,
                capture_output=True,
                env=env,
                timeout=5  # 5 second timeout to prevent hanging
            )
            
            if result.returncode == 0:
                self.logger.debug(f"Successfully triggered {hook_type} hook")
                return True
            else:
                self.logger.warning(f"Hook handler returned non-zero exit code: {result.returncode}")
                if result.stderr:
                    self.logger.warning(f"Hook handler stderr: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            self.logger.warning(f"Hook handler timed out for {hook_type}")
            return False
        except Exception as e:
            self.logger.error(f"Error triggering {hook_type} hook: {e}")
            return False


# Global instance
_hook_manager: Optional[HookManager] = None


def get_hook_manager() -> HookManager:
    """Get the global hook manager instance."""
    global _hook_manager
    if _hook_manager is None:
        _hook_manager = HookManager()
    return _hook_manager


def trigger_tool_hooks(tool_name: str, tool_args: Dict[str, Any] = None, result: Any = None, exit_code: int = 0):
    """Convenience function to trigger both pre and post tool hooks.
    
    Args:
        tool_name: Name of the tool
        tool_args: Arguments passed to the tool
        result: Result returned by the tool
        exit_code: Exit code (0 for success)
    """
    manager = get_hook_manager()
    
    # Trigger pre-tool hook
    manager.trigger_pre_tool_hook(tool_name, tool_args)
    
    # Trigger post-tool hook
    manager.trigger_post_tool_hook(tool_name, exit_code, result)