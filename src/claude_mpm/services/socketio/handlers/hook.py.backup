"""Hook event handlers for Socket.IO.

WHY: This module handles hook events from Claude to track session information,
agent delegations, and other hook-based activity for the system heartbeat.
"""

from datetime import datetime
from typing import Any, Dict, Optional

from .base import BaseEventHandler


class HookEventHandler(BaseEventHandler):
    """Handles hook events from Claude for session tracking.
    
    WHY: Hook events provide rich information about Claude's activity including
    session starts/stops, agent delegations, and tool usage. This handler
    extracts session information to populate the system heartbeat data.
    """
    
    def register_events(self) -> None:
        """Register hook event handlers."""
        
        @self.sio.event
        async def claude_event(sid, data):
            """Handle claude_event which includes hook events.
            
            WHY: Hook events are sent as claude_event with type 'hook'
            and contain session and agent delegation information.
            """
            if not isinstance(data, dict):
                return
                
            # Check if this is a hook event
            event_type = data.get("type")
            if event_type != "hook":
                return
                
            # Extract hook event details
            hook_event = data.get("event")
            hook_data = data.get("data", {})
            
            # Track sessions based on hook events
            if hook_event == "subagent_start":
                await self._handle_subagent_start(hook_data)
            elif hook_event == "subagent_stop":
                await self._handle_subagent_stop(hook_data)
            elif hook_event == "user_prompt":
                await self._handle_user_prompt(hook_data)
            elif hook_event == "pre_tool":
                await self._handle_pre_tool(hook_data)
                
    async def _handle_subagent_start(self, data: Dict[str, Any]):
        """Handle subagent start events.
        
        WHY: When a subagent starts, we track it as an active session
        with the agent type and start time for the heartbeat.
        """
        session_id = data.get("session_id")
        agent_type = data.get("agent_type", "unknown")
        
        if not session_id:
            return
            
        # Update or create session tracking
        if hasattr(self.server, 'active_sessions'):
            self.server.active_sessions[session_id] = {
                "session_id": session_id,
                "start_time": datetime.now().isoformat(),
                "agent": agent_type,
                "status": "active",
                "prompt": data.get("prompt", "")[:100],  # First 100 chars
                "last_activity": datetime.now().isoformat(),
            }
            
            self.logger.debug(
                f"Tracked subagent start: session={session_id[:8]}..., agent={agent_type}"
            )
            
    async def _handle_subagent_stop(self, data: Dict[str, Any]):
        """Handle subagent stop events.
        
        WHY: When a subagent stops, we update its status or remove it
        from active sessions depending on the stop reason.
        """
        session_id = data.get("session_id")
        
        if not session_id:
            return
            
        # Update session status
        if hasattr(self.server, 'active_sessions'):
            if session_id in self.server.active_sessions:
                # Mark as completed rather than removing immediately
                self.server.active_sessions[session_id]["status"] = "completed"
                self.server.active_sessions[session_id]["last_activity"] = datetime.now().isoformat()
                
                self.logger.debug(
                    f"Marked session completed: session={session_id[:8]}..."
                )
                
    async def _handle_user_prompt(self, data: Dict[str, Any]):
        """Handle user prompt events.
        
        WHY: User prompts indicate the start of a new interaction,
        which we track as a PM session if no delegation occurs.
        """
        session_id = data.get("session_id")
        
        if not session_id:
            return
            
        # Create or update PM session
        if hasattr(self.server, 'active_sessions'):
            if session_id not in self.server.active_sessions:
                self.server.active_sessions[session_id] = {
                    "session_id": session_id,
                    "start_time": datetime.now().isoformat(),
                    "agent": "pm",  # Default to PM
                    "status": "active",
                    "prompt": data.get("prompt_text", "")[:100],
                    "working_directory": data.get("working_directory", ""),
                    "last_activity": datetime.now().isoformat(),
                }
            else:
                # Update last activity
                self.server.active_sessions[session_id]["last_activity"] = datetime.now().isoformat()
                
    async def _handle_pre_tool(self, data: Dict[str, Any]):
        """Handle pre-tool events.
        
        WHY: Pre-tool events with Task delegation indicate agent changes
        that we need to track for accurate session information.
        """
        if data.get("tool_name") != "Task":
            return
            
        session_id = data.get("session_id")
        delegation_details = data.get("delegation_details", {})
        agent_type = delegation_details.get("agent_type", "unknown")
        
        if not session_id:
            return
            
        # Update session with new agent
        if hasattr(self.server, 'active_sessions'):
            if session_id in self.server.active_sessions:
                self.server.active_sessions[session_id]["agent"] = agent_type
                self.server.active_sessions[session_id]["status"] = "delegated"
                self.server.active_sessions[session_id]["last_activity"] = datetime.now().isoformat()
                
                self.logger.debug(
                    f"Updated session delegation: session={session_id[:8]}..., agent={agent_type}"
                )