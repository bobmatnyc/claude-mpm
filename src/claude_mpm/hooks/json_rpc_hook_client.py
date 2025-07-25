"""JSON-RPC based client for executing hooks without HTTP server."""

import importlib.util
import inspect
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from claude_mpm.hooks.base_hook import (
    BaseHook, HookType,
    SubmitHook, PreDelegationHook, PostDelegationHook, TicketExtractionHook
)
from claude_mpm.hooks.json_rpc_executor import JSONRPCHookExecutor, JSONRPCError
from claude_mpm.core.logger import get_logger

logger = get_logger(__name__)


class JSONRPCHookClient:
    """Client for executing hooks via JSON-RPC subprocess calls."""
    
    def __init__(self, timeout: int = 30):
        """Initialize JSON-RPC hook client.
        
        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = timeout
        self.executor = JSONRPCHookExecutor(timeout=timeout)
        self._hook_registry = {}
        self._hook_types = {}
        self._discover_hooks()
        
    def _discover_hooks(self):
        """Discover available hooks from builtin directory."""
        hooks_dir = Path(__file__).parent / 'builtin'
        if not hooks_dir.exists():
            logger.warning(f"Builtin hooks directory not found: {hooks_dir}")
            return
            
        for hook_file in hooks_dir.glob('*.py'):
            if hook_file.name.startswith('_'):
                continue
                
            try:
                # Load the module to discover hooks
                module_name = hook_file.stem
                spec = importlib.util.spec_from_file_location(module_name, hook_file)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    # Find hook classes (don't instantiate, just register)
                    for name, obj in inspect.getmembers(module):
                        if (inspect.isclass(obj) and 
                            issubclass(obj, BaseHook) and 
                            obj not in [BaseHook, SubmitHook, PreDelegationHook, 
                                       PostDelegationHook, TicketExtractionHook] and
                            not name.startswith('_')):
                            # Create temporary instance to get name
                            temp_instance = obj()
                            hook_name = temp_instance.name
                            
                            # Determine hook type
                            if isinstance(temp_instance, SubmitHook):
                                hook_type = HookType.SUBMIT
                            elif isinstance(temp_instance, PreDelegationHook):
                                hook_type = HookType.PRE_DELEGATION
                            elif isinstance(temp_instance, PostDelegationHook):
                                hook_type = HookType.POST_DELEGATION
                            elif isinstance(temp_instance, TicketExtractionHook):
                                hook_type = HookType.TICKET_EXTRACTION
                            else:
                                hook_type = HookType.CUSTOM
                                
                            self._hook_registry[hook_name] = {
                                'name': hook_name,
                                'type': hook_type,
                                'priority': temp_instance.priority,
                                'class': name,
                                'module': module_name
                            }
                            self._hook_types[hook_type] = self._hook_types.get(hook_type, [])
                            self._hook_types[hook_type].append(hook_name)
                            
                            logger.debug(f"Discovered hook '{hook_name}' of type {hook_type.value}")
                            
            except Exception as e:
                logger.error(f"Failed to discover hooks from {hook_file}: {e}")
                
    def health_check(self) -> Dict[str, Any]:
        """Check health of hook system.
        
        Returns:
            Health status dictionary
        """
        try:
            hook_count = len(self._hook_registry)
            return {
                'status': 'healthy',
                'hook_count': hook_count,
                'executor': 'json-rpc',
                'discovered_hooks': list(self._hook_registry.keys())
            }
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
        hooks_by_type = {}
        
        for hook_type in HookType:
            hooks_by_type[hook_type.value] = []
            
        for hook_name, hook_info in self._hook_registry.items():
            hook_type = hook_info['type']
            hooks_by_type[hook_type.value].append({
                'name': hook_name,
                'priority': hook_info['priority'],
                'enabled': True  # All discovered hooks are enabled
            })
            
        # Sort by priority
        for hook_list in hooks_by_type.values():
            hook_list.sort(key=lambda x: x['priority'])
            
        return hooks_by_type
        
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
            if specific_hook:
                # Execute specific hook
                if specific_hook not in self._hook_registry:
                    logger.error(f"Hook '{specific_hook}' not found")
                    return [{
                        'hook_name': specific_hook,
                        'success': False,
                        'error': f"Hook '{specific_hook}' not found"
                    }]
                    
                try:
                    result = self.executor.execute_hook(
                        hook_name=specific_hook,
                        hook_type=hook_type,
                        context_data=context_data,
                        metadata=metadata
                    )
                    return [result]
                except JSONRPCError as e:
                    return [{
                        'hook_name': specific_hook,
                        'success': False,
                        'error': e.message,
                        'error_code': e.code
                    }]
                    
            else:
                # Execute all hooks of the given type
                hook_names = self._hook_types.get(hook_type, [])
                if not hook_names:
                    logger.debug(f"No hooks registered for type {hook_type.value}")
                    return []
                    
                # Sort by priority
                sorted_hooks = sorted(
                    hook_names,
                    key=lambda name: self._hook_registry[name]['priority']
                )
                
                return self.executor.execute_hooks(
                    hook_type=hook_type,
                    hook_names=sorted_hooks,
                    context_data=context_data,
                    metadata=metadata
                )
                
        except Exception as e:
            logger.error(f"Failed to execute hooks: {e}")
            return [{
                'success': False,
                'error': str(e)
            }]
            
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


# Update the convenience function to use JSON-RPC client
def get_hook_client(base_url: Optional[str] = None) -> JSONRPCHookClient:
    """Get a hook client instance.
    
    Args:
        base_url: Ignored for JSON-RPC client (kept for compatibility)
        
    Returns:
        JSONRPCHookClient instance
    """
    return JSONRPCHookClient()