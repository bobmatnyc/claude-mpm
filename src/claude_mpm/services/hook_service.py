"""Centralized hook service for claude-mpm."""

import asyncio
import json
import logging
import os
import sys
import time
import traceback
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Type, Union

from flask import Flask, jsonify, request
from flask_cors import CORS

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from claude_mpm.hooks.base_hook import (
    BaseHook, HookContext, HookResult, HookType,
    SubmitHook, PreDelegationHook, PostDelegationHook, TicketExtractionHook
)
from claude_mpm.utils.logger import get_logger

logger = get_logger(__name__)


class HookRegistry:
    """Registry for managing hooks."""
    
    def __init__(self):
        """Initialize empty hook registry."""
        self._hooks: Dict[HookType, List[BaseHook]] = defaultdict(list)
        self._hook_instances: Dict[str, BaseHook] = {}
        self._lock = asyncio.Lock()
        
    def register(self, hook: BaseHook, hook_type: Optional[HookType] = None) -> bool:
        """Register a hook instance.
        
        Args:
            hook: Hook instance to register
            hook_type: Optional hook type override
            
        Returns:
            True if registered successfully
        """
        try:
            # Determine hook type
            if hook_type is None:
                if isinstance(hook, SubmitHook):
                    hook_type = HookType.SUBMIT
                elif isinstance(hook, PreDelegationHook):
                    hook_type = HookType.PRE_DELEGATION
                elif isinstance(hook, PostDelegationHook):
                    hook_type = HookType.POST_DELEGATION
                elif isinstance(hook, TicketExtractionHook):
                    hook_type = HookType.TICKET_EXTRACTION
                else:
                    hook_type = HookType.CUSTOM
                    
            # Check for duplicate names
            if hook.name in self._hook_instances:
                logger.warning(f"Hook '{hook.name}' already registered, replacing")
                self.unregister(hook.name)
                
            # Register hook
            self._hooks[hook_type].append(hook)
            self._hook_instances[hook.name] = hook
            
            # Sort by priority
            self._hooks[hook_type].sort()
            
            logger.info(f"Registered hook '{hook.name}' for type {hook_type.value}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register hook '{hook.name}': {e}")
            return False
            
    def unregister(self, hook_name: str) -> bool:
        """Unregister a hook by name.
        
        Args:
            hook_name: Name of hook to unregister
            
        Returns:
            True if unregistered successfully
        """
        try:
            if hook_name not in self._hook_instances:
                logger.warning(f"Hook '{hook_name}' not found")
                return False
                
            hook = self._hook_instances[hook_name]
            
            # Remove from type list
            for hook_list in self._hooks.values():
                if hook in hook_list:
                    hook_list.remove(hook)
                    
            # Remove from instances
            del self._hook_instances[hook_name]
            
            logger.info(f"Unregistered hook '{hook_name}'")
            return True
            
        except Exception as e:
            logger.error(f"Failed to unregister hook '{hook_name}': {e}")
            return False
            
    def get_hooks(self, hook_type: HookType) -> List[BaseHook]:
        """Get all hooks for a given type.
        
        Args:
            hook_type: Type of hooks to retrieve
            
        Returns:
            List of hooks sorted by priority
        """
        return [h for h in self._hooks[hook_type] if h.enabled]
        
    def get_hook(self, hook_name: str) -> Optional[BaseHook]:
        """Get a specific hook by name.
        
        Args:
            hook_name: Name of hook to retrieve
            
        Returns:
            Hook instance or None if not found
        """
        return self._hook_instances.get(hook_name)
        
    def list_hooks(self) -> Dict[str, List[Dict[str, Any]]]:
        """List all registered hooks.
        
        Returns:
            Dictionary mapping hook types to hook info
        """
        result = {}
        for hook_type, hooks in self._hooks.items():
            result[hook_type.value] = [
                {
                    'name': h.name,
                    'priority': h.priority,
                    'enabled': h.enabled,
                    'class': h.__class__.__name__
                }
                for h in hooks
            ]
        return result


class HookService:
    """Centralized service for managing and executing hooks."""
    
    def __init__(self, port: int = 5001):
        """Initialize hook service.
        
        Args:
            port: Port to run service on
        """
        self.port = port
        self.registry = HookRegistry()
        self.app = Flask(__name__)
        CORS(self.app)
        self._setup_routes()
        self._load_builtin_hooks()
        
    def _setup_routes(self):
        """Setup Flask routes for hook service."""
        
        @self.app.route('/health', methods=['GET'])
        def health():
            """Health check endpoint."""
            return jsonify({
                'status': 'healthy',
                'timestamp': datetime.now().isoformat(),
                'hooks_count': sum(len(h) for h in self.registry._hooks.values())
            })
            
        @self.app.route('/hooks/list', methods=['GET'])
        def list_hooks():
            """List all registered hooks."""
            return jsonify({
                'status': 'success',
                'hooks': self.registry.list_hooks()
            })
            
        @self.app.route('/hooks/execute', methods=['POST'])
        def execute_hook():
            """Execute a specific hook or all hooks of a type."""
            try:
                data = request.json
                hook_type = HookType(data.get('hook_type'))
                context_data = data.get('context', {})
                metadata = data.get('metadata', {})
                specific_hook = data.get('hook_name')
                
                # Create context
                context = HookContext(
                    hook_type=hook_type,
                    data=context_data,
                    metadata=metadata,
                    timestamp=datetime.now()
                )
                
                # Execute hooks
                if specific_hook:
                    hook = self.registry.get_hook(specific_hook)
                    if not hook:
                        return jsonify({
                            'status': 'error',
                            'error': f"Hook '{specific_hook}' not found"
                        }), 404
                    results = [self._execute_single_hook(hook, context)]
                else:
                    results = self._execute_hooks(hook_type, context)
                    
                return jsonify({
                    'status': 'success',
                    'results': results
                })
                
            except Exception as e:
                logger.error(f"Hook execution error: {e}")
                return jsonify({
                    'status': 'error',
                    'error': str(e)
                }), 500
                
        @self.app.route('/hooks/register', methods=['POST'])
        def register_hook():
            """Register a new hook (for dynamic registration)."""
            try:
                data = request.json
                # This would need to dynamically create hook instances
                # For now, return not implemented
                return jsonify({
                    'status': 'error',
                    'error': 'Dynamic registration not yet implemented'
                }), 501
                
            except Exception as e:
                logger.error(f"Hook registration error: {e}")
                return jsonify({
                    'status': 'error',
                    'error': str(e)
                }), 500
                
    def _load_builtin_hooks(self):
        """Load built-in hooks from hooks directory."""
        import importlib.util
        import inspect
        
        hooks_dir = Path(__file__).parent.parent / 'hooks' / 'builtin'
        if hooks_dir.exists():
            for hook_file in hooks_dir.glob('*.py'):
                if hook_file.name.startswith('_'):
                    continue
                try:
                    # Load the module
                    module_name = hook_file.stem
                    spec = importlib.util.spec_from_file_location(module_name, hook_file)
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    # Find and instantiate hook classes
                    for name, obj in inspect.getmembers(module):
                        if (inspect.isclass(obj) and 
                            issubclass(obj, BaseHook) and 
                            obj is not BaseHook and
                            not name.startswith('_')):
                            # Instantiate and register the hook
                            hook_instance = obj()
                            self.registry.register(hook_instance)
                            logger.info(f"Loaded hook '{hook_instance.name}' from {hook_file}")
                            
                except Exception as e:
                    logger.error(f"Failed to load hook from {hook_file}: {e}")
                    
    def _execute_single_hook(self, hook: BaseHook, context: HookContext) -> Dict[str, Any]:
        """Execute a single hook.
        
        Args:
            hook: Hook to execute
            context: Context for execution
            
        Returns:
            Execution result dictionary
        """
        start_time = time.time()
        try:
            # Validate hook
            if not hook.validate(context):
                return {
                    'hook_name': hook.name,
                    'success': False,
                    'error': 'Validation failed',
                    'execution_time_ms': 0
                }
                
            # Execute hook
            if hasattr(hook, '_async') and hook._async:
                # Run async hook
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(hook.async_execute(context))
                loop.close()
            else:
                result = hook.execute(context)
                
            # Add execution time
            execution_time = (time.time() - start_time) * 1000
            result.execution_time_ms = execution_time
            
            return {
                'hook_name': hook.name,
                'success': result.success,
                'data': result.data,
                'error': result.error,
                'modified': result.modified,
                'metadata': result.metadata,
                'execution_time_ms': execution_time
            }
            
        except Exception as e:
            logger.error(f"Hook '{hook.name}' execution failed: {e}")
            return {
                'hook_name': hook.name,
                'success': False,
                'error': str(e),
                'traceback': traceback.format_exc(),
                'execution_time_ms': (time.time() - start_time) * 1000
            }
            
    def _execute_hooks(self, hook_type: HookType, context: HookContext) -> List[Dict[str, Any]]:
        """Execute all hooks of a given type.
        
        Args:
            hook_type: Type of hooks to execute
            context: Context for execution
            
        Returns:
            List of execution results
        """
        hooks = self.registry.get_hooks(hook_type)
        results = []
        
        for hook in hooks:
            result = self._execute_single_hook(hook, context)
            results.append(result)
            
            # If hook modified data, update context for next hook
            if result.get('modified') and result.get('data'):
                context.data.update(result['data'])
                
        return results
        
    def run(self):
        """Run the hook service."""
        logger.info(f"Starting hook service on port {self.port}")
        self.app.run(host='0.0.0.0', port=self.port, debug=False)


def main():
    """Main entry point for hook service."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Claude MPM Hook Service')
    parser.add_argument('--port', type=int, default=5001, help='Port to run service on')
    parser.add_argument('--log-level', default='INFO', help='Logging level')
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create and run service
    service = HookService(port=args.port)
    service.run()


if __name__ == '__main__':
    main()