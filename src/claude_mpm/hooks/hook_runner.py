"""Hook runner subprocess entry point for JSON-RPC execution."""

import importlib.util
import inspect
import json
import logging
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from claude_mpm.hooks.base_hook import (
    BaseHook, HookContext, HookResult, HookType,
    SubmitHook, PreDelegationHook, PostDelegationHook, TicketExtractionHook
)

# Configure logging to stderr so it doesn't interfere with stdout JSON-RPC
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)


class HookLoader:
    """Loads and manages hook instances."""
    
    def __init__(self):
        """Initialize hook loader."""
        self._hooks: Dict[str, BaseHook] = {}
        self._hook_types: Dict[str, HookType] = {}
        self._load_builtin_hooks()
        
    def _load_builtin_hooks(self):
        """Load built-in hooks from hooks/builtin directory."""
        hooks_dir = Path(__file__).parent / 'builtin'
        if not hooks_dir.exists():
            logger.warning(f"Builtin hooks directory not found: {hooks_dir}")
            return
            
        for hook_file in hooks_dir.glob('*.py'):
            if hook_file.name.startswith('_'):
                continue
                
            try:
                # Load the module
                module_name = hook_file.stem
                spec = importlib.util.spec_from_file_location(module_name, hook_file)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    # Find and instantiate hook classes
                    for name, obj in inspect.getmembers(module):
                        if (inspect.isclass(obj) and 
                            issubclass(obj, BaseHook) and 
                            obj not in [BaseHook, SubmitHook, PreDelegationHook, 
                                       PostDelegationHook, TicketExtractionHook] and
                            not name.startswith('_')):
                            # Instantiate the hook
                            hook_instance = obj()
                            self._hooks[hook_instance.name] = hook_instance
                            
                            # Determine hook type
                            if isinstance(hook_instance, SubmitHook):
                                self._hook_types[hook_instance.name] = HookType.SUBMIT
                            elif isinstance(hook_instance, PreDelegationHook):
                                self._hook_types[hook_instance.name] = HookType.PRE_DELEGATION
                            elif isinstance(hook_instance, PostDelegationHook):
                                self._hook_types[hook_instance.name] = HookType.POST_DELEGATION
                            elif isinstance(hook_instance, TicketExtractionHook):
                                self._hook_types[hook_instance.name] = HookType.TICKET_EXTRACTION
                            else:
                                self._hook_types[hook_instance.name] = HookType.CUSTOM
                                
                            logger.info(f"Loaded hook '{hook_instance.name}' from {hook_file}")
                            
            except Exception as e:
                logger.error(f"Failed to load hooks from {hook_file}: {e}")
                logger.error(traceback.format_exc())
                
    def get_hook(self, hook_name: str) -> Optional[BaseHook]:
        """Get a hook by name.
        
        Args:
            hook_name: Name of the hook
            
        Returns:
            Hook instance or None if not found
        """
        return self._hooks.get(hook_name)
        
    def get_hook_type(self, hook_name: str) -> Optional[HookType]:
        """Get the type of a hook by name.
        
        Args:
            hook_name: Name of the hook
            
        Returns:
            Hook type or None if not found
        """
        return self._hook_types.get(hook_name)


class JSONRPCHookRunner:
    """Runs hooks in response to JSON-RPC requests."""
    
    def __init__(self):
        """Initialize hook runner."""
        self.loader = HookLoader()
        
    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a single JSON-RPC request.
        
        Args:
            request: JSON-RPC request object
            
        Returns:
            JSON-RPC response object
        """
        # Validate request
        if not isinstance(request, dict):
            return self._error_response(
                -32600, "Invalid Request", None,
                "Request must be an object"
            )
            
        if request.get("jsonrpc") != "2.0":
            return self._error_response(
                -32600, "Invalid Request", 
                request.get("id"),
                "Must specify jsonrpc: '2.0'"
            )
            
        request_id = request.get("id")
        method = request.get("method")
        params = request.get("params", {})
        
        if not method:
            return self._error_response(
                -32600, "Invalid Request", request_id,
                "Missing method"
            )
            
        # Route to method handler
        if method == "execute_hook":
            return self._execute_hook(params, request_id)
        else:
            return self._error_response(
                -32601, "Method not found", request_id,
                f"Unknown method: {method}"
            )
            
    def _execute_hook(self, params: Dict[str, Any], request_id: Any) -> Dict[str, Any]:
        """Execute a hook based on parameters.
        
        Args:
            params: Hook execution parameters
            request_id: JSON-RPC request ID
            
        Returns:
            JSON-RPC response
        """
        try:
            # Extract parameters
            hook_name = params.get("hook_name")
            hook_type_str = params.get("hook_type")
            context_data = params.get("context_data", {})
            metadata = params.get("metadata", {})
            
            if not hook_name:
                return self._error_response(
                    -32602, "Invalid params", request_id,
                    "Missing hook_name parameter"
                )
                
            # Get hook instance
            hook = self.loader.get_hook(hook_name)
            if not hook:
                return self._error_response(
                    -32602, "Invalid params", request_id,
                    f"Hook '{hook_name}' not found"
                )
                
            # Create hook context
            try:
                hook_type = HookType(hook_type_str) if hook_type_str else self.loader.get_hook_type(hook_name)
            except ValueError:
                return self._error_response(
                    -32602, "Invalid params", request_id,
                    f"Invalid hook type: {hook_type_str}"
                )
                
            context = HookContext(
                hook_type=hook_type,
                data=context_data,
                metadata=metadata,
                timestamp=datetime.now()
            )
            
            # Validate hook can run
            if not hook.validate(context):
                return self._success_response({
                    "hook_name": hook_name,
                    "success": False,
                    "error": "Hook validation failed",
                    "skipped": True
                }, request_id)
                
            # Execute hook
            import time
            start_time = time.time()
            
            try:
                result = hook.execute(context)
                execution_time = (time.time() - start_time) * 1000  # ms
                
                # Convert HookResult to dict
                return self._success_response({
                    "hook_name": hook_name,
                    "success": result.success,
                    "data": result.data,
                    "error": result.error,
                    "modified": result.modified,
                    "metadata": result.metadata,
                    "execution_time_ms": execution_time
                }, request_id)
                
            except Exception as e:
                logger.error(f"Hook execution error: {e}")
                logger.error(traceback.format_exc())
                execution_time = (time.time() - start_time) * 1000
                
                return self._success_response({
                    "hook_name": hook_name,
                    "success": False,
                    "error": str(e),
                    "execution_time_ms": execution_time
                }, request_id)
                
        except Exception as e:
            logger.error(f"Unexpected error in _execute_hook: {e}")
            logger.error(traceback.format_exc())
            return self._error_response(
                -32603, "Internal error", request_id,
                str(e)
            )
            
    def _success_response(self, result: Any, request_id: Any) -> Dict[str, Any]:
        """Create a successful JSON-RPC response.
        
        Args:
            result: Result data
            request_id: Request ID
            
        Returns:
            JSON-RPC response object
        """
        return {
            "jsonrpc": "2.0",
            "result": result,
            "id": request_id
        }
        
    def _error_response(self, code: int, message: str, 
                       request_id: Any, data: Optional[Any] = None) -> Dict[str, Any]:
        """Create an error JSON-RPC response.
        
        Args:
            code: Error code
            message: Error message
            request_id: Request ID
            data: Optional error data
            
        Returns:
            JSON-RPC error response object
        """
        error = {
            "code": code,
            "message": message
        }
        if data is not None:
            error["data"] = data
            
        return {
            "jsonrpc": "2.0",
            "error": error,
            "id": request_id
        }
        
    def handle_batch(self, requests: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Handle a batch of JSON-RPC requests.
        
        Args:
            requests: List of JSON-RPC requests
            
        Returns:
            List of JSON-RPC responses
        """
        if not isinstance(requests, list) or not requests:
            return [self._error_response(
                -32600, "Invalid Request", None,
                "Batch must be a non-empty array"
            )]
            
        responses = []
        for request in requests:
            response = self.handle_request(request)
            responses.append(response)
            
        return responses


def main():
    """Main entry point for hook runner subprocess."""
    runner = JSONRPCHookRunner()
    
    try:
        # Check for batch mode
        batch_mode = "--batch" in sys.argv
        
        # Read JSON-RPC request from stdin
        input_data = sys.stdin.read()
        
        try:
            if batch_mode:
                requests = json.loads(input_data)
                responses = runner.handle_batch(requests)
                print(json.dumps(responses))
            else:
                request = json.loads(input_data)
                response = runner.handle_request(request)
                print(json.dumps(response))
                
        except json.JSONDecodeError as e:
            error_response = {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32700,
                    "message": "Parse error",
                    "data": str(e)
                },
                "id": None
            }
            print(json.dumps(error_response))
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Fatal error in hook runner: {e}")
        logger.error(traceback.format_exc())
        error_response = {
            "jsonrpc": "2.0",
            "error": {
                "code": -32603,
                "message": "Internal error",
                "data": str(e)
            },
            "id": None
        }
        print(json.dumps(error_response))
        sys.exit(1)


if __name__ == "__main__":
    main()