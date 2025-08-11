"""
Session Response Logger Hook

Simple hook that logs responses using Claude Code session IDs.
Integrates with the claude_session_logger service.
"""

import logging
from typing import Dict, Any, Optional

from claude_mpm.services.claude_session_logger import get_session_logger

logger = logging.getLogger(__name__)


class SessionResponseLoggerHook:
    """Hook for logging responses to session directories."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the session response logger hook.
        
        Args:
            config: Hook configuration
        """
        self.config = config or {}
        self.enabled = self.config.get('enabled', True)
        self.session_logger = get_session_logger() if self.enabled else None
        
        # Configuration options
        self.log_all_agents = self.config.get('log_all_agents', True)
        self.logged_agents = self.config.get('logged_agents', [])
        self.excluded_agents = self.config.get('excluded_agents', [])
        self.min_response_length = self.config.get('min_response_length', 50)
        
    def on_agent_response(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Hook called after an agent generates a response.
        
        Args:
            event: Event data containing agent response
            
        Returns:
            Original event data (unchanged)
        """
        if not self.enabled or not self.session_logger:
            return event
        
        # Check if logger is enabled (has session ID)
        if not self.session_logger.is_enabled():
            return event
        
        agent_name = event.get('agent_name', 'unknown')
        
        # Check if we should log this agent
        if not self._should_log_agent(agent_name):
            return event
        
        # Get response content
        response = event.get('response', '')
        
        # Check minimum length
        if len(response) < self.min_response_length:
            logger.debug(f"Response too short to log ({len(response)} chars)")
            return event
        
        # Get request summary
        request = event.get('request', '')
        request_summary = self._create_request_summary(request)
        
        # Prepare metadata
        metadata = {
            'agent': agent_name,
            'model': event.get('model'),
            'tokens': event.get('tokens'),
            'tools_used': event.get('tools_used', [])
        }
        
        # Remove None values
        metadata = {k: v for k, v in metadata.items() if v is not None}
        
        # Log the response
        try:
            log_path = self.session_logger.log_response(
                request_summary=request_summary,
                response_content=response,
                metadata=metadata
            )
            
            if log_path:
                logger.info(f"Logged {agent_name} response to {log_path.name}")
                
        except Exception as e:
            logger.error(f"Failed to log response: {e}")
        
        return event
    
    def _should_log_agent(self, agent_name: str) -> bool:
        """
        Check if an agent's responses should be logged.
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            True if agent should be logged
        """
        # Check excluded list first
        if agent_name in self.excluded_agents:
            return False
        
        # If logging all agents, return True
        if self.log_all_agents:
            return True
        
        # Otherwise check the included list
        return agent_name in self.logged_agents
    
    def _create_request_summary(self, request: str, max_length: int = 100) -> str:
        """
        Create a brief summary of the request.
        
        Args:
            request: The full request text
            max_length: Maximum summary length
            
        Returns:
            Brief summary of the request
        """
        if not request:
            return "No request provided"
        
        # Clean up the request
        request = request.strip()
        
        # If short enough, return as is
        if len(request) <= max_length:
            return request
        
        # Otherwise truncate and add ellipsis
        return request[:max_length - 3] + "..."
    
    def on_session_start(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Hook called when a session starts.
        
        Args:
            event: Event data with session info
            
        Returns:
            Original event data
        """
        if not self.enabled or not self.session_logger:
            return event
        
        # Update session ID if provided
        if 'session_id' in event:
            self.session_logger.set_session_id(event['session_id'])
            logger.info(f"Session logger using ID: {event['session_id']}")
        
        return event


def register_hook():
    """Register the session response logger hook."""
    return SessionResponseLoggerHook