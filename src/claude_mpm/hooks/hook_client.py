"""Client for interacting with the hook service.

DEPRECATED: This HTTP-based hook client is deprecated and will be removed in a future release.
Please use the JSON-RPC implementation from claude_mpm.hooks.json_rpc_hook_client instead.
See /docs/hook_system_migration_guide.md for migration instructions.
"""

import json
import logging
import warnings
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

from claude_mpm.hooks.base_hook import HookType
from claude_mpm.core.logger import get_logger

logger = get_logger(__name__)


class HookServiceClient:
    """Client for interacting with the centralized hook service.
    
    DEPRECATED: Use JSONRPCHookClient from claude_mpm.hooks.json_rpc_hook_client instead.
    """
    
    def __init__(self, base_url: str = "http://localhost:5001", timeout: int = 30):
        """Initialize hook service client.
        
        Args:
            base_url: Base URL of hook service
            timeout: Request timeout in seconds
        """
        warnings.warn(
            "HookServiceClient is deprecated and will be removed in a future release. "
            "Please use JSONRPCHookClient from claude_mpm.hooks.json_rpc_hook_client instead. "
            "See /docs/hook_system_migration_guide.md for migration instructions.",
            DeprecationWarning,
            stacklevel=2
        )
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        
        # Setup session with retry logic
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
    def health_check(self) -> Dict[str, Any]:
        """Check health of hook service.
        
        Returns:
            Health status dictionary
        """
        try:
            response = self.session.get(
                urljoin(self.base_url, '/health'),
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                'status': 'unhealthy',
                'error': str(e)
            }
            
    def list_hooks(self) -> Dict[str, List[Dict[str, Any]]]:
        """List all registered hooks.
        
        Returns:
            Dictionary mapping hook types to hook info
        """
        try:
            response = self.session.get(
                urljoin(self.base_url, '/hooks/list'),
                timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()
            return data.get('hooks', {})
        except Exception as e:
            logger.error(f"Failed to list hooks: {e}")
            return {}
            
    def execute_hook(self, hook_type: HookType, context_data: Dict[str, Any],
                    metadata: Optional[Dict[str, Any]] = None,
                    specific_hook: Optional[str] = None) -> List[Dict[str, Any]]:
        """Execute hooks of a given type.
        
        Args:
            hook_type: Type of hooks to execute
            context_data: Data to pass to hooks
            metadata: Optional metadata
            specific_hook: Optional specific hook name to execute
            
        Returns:
            List of execution results
        """
        try:
            payload = {
                'hook_type': hook_type.value,
                'context': context_data,
                'metadata': metadata or {}
            }
            
            if specific_hook:
                payload['hook_name'] = specific_hook
                
            response = self.session.post(
                urljoin(self.base_url, '/hooks/execute'),
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()
            
            if data.get('status') == 'success':
                return data.get('results', [])
            else:
                logger.error(f"Hook execution failed: {data.get('error')}")
                return []
                
        except Exception as e:
            logger.error(f"Failed to execute hooks: {e}")
            return []
            
    def execute_submit_hook(self, prompt: str, **kwargs) -> List[Dict[str, Any]]:
        """Execute submit hooks on a user prompt.
        
        Args:
            prompt: User prompt to process
            **kwargs: Additional context data
            
        Returns:
            List of execution results
        """
        context_data = {'prompt': prompt}
        context_data.update(kwargs)
        return self.execute_hook(HookType.SUBMIT, context_data)
        
    def execute_pre_delegation_hook(self, agent: str, context: Dict[str, Any],
                                   **kwargs) -> List[Dict[str, Any]]:
        """Execute pre-delegation hooks.
        
        Args:
            agent: Agent being delegated to
            context: Context being passed to agent
            **kwargs: Additional data
            
        Returns:
            List of execution results
        """
        context_data = {
            'agent': agent,
            'context': context
        }
        context_data.update(kwargs)
        return self.execute_hook(HookType.PRE_DELEGATION, context_data)
        
    def execute_post_delegation_hook(self, agent: str, result: Any,
                                    **kwargs) -> List[Dict[str, Any]]:
        """Execute post-delegation hooks.
        
        Args:
            agent: Agent that was delegated to
            result: Result from agent
            **kwargs: Additional data
            
        Returns:
            List of execution results
        """
        context_data = {
            'agent': agent,
            'result': result
        }
        context_data.update(kwargs)
        return self.execute_hook(HookType.POST_DELEGATION, context_data)
        
    def execute_ticket_extraction_hook(self, content: Any,
                                      **kwargs) -> List[Dict[str, Any]]:
        """Execute ticket extraction hooks.
        
        Args:
            content: Content to extract tickets from
            **kwargs: Additional data
            
        Returns:
            List of execution results
        """
        context_data = {'content': content}
        context_data.update(kwargs)
        return self.execute_hook(HookType.TICKET_EXTRACTION, context_data)
        
    def get_modified_data(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract modified data from hook results.
        
        Args:
            results: Hook execution results
            
        Returns:
            Combined modified data from all hooks
        """
        modified_data = {}
        
        for result in results:
            if result.get('modified') and result.get('data'):
                modified_data.update(result['data'])
                
        return modified_data
        
    def get_extracted_tickets(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract tickets from hook results.
        
        Args:
            results: Hook execution results
            
        Returns:
            List of extracted tickets
        """
        all_tickets = []
        
        for result in results:
            if result.get('success') and 'tickets' in result.get('data', {}):
                tickets = result['data']['tickets']
                if isinstance(tickets, list):
                    all_tickets.extend(tickets)
                    
        return all_tickets


# Convenience function for creating a default client
def get_hook_client(base_url: Optional[str] = None) -> 'JSONRPCHookClient':
    """Get a hook client instance.
    
    DEPRECATED: This function now returns a JSONRPCHookClient for compatibility.
    Import directly from claude_mpm.hooks.json_rpc_hook_client instead.
    
    Args:
        base_url: Ignored (kept for backward compatibility)
        
    Returns:
        JSONRPCHookClient instance
    """
    warnings.warn(
        "get_hook_client from hook_client module is deprecated. "
        "Import from claude_mpm.hooks.json_rpc_hook_client instead.",
        DeprecationWarning,
        stacklevel=2
    )
    
    # Import and return JSON-RPC client for compatibility
    from claude_mpm.hooks.json_rpc_hook_client import JSONRPCHookClient
    return JSONRPCHookClient()