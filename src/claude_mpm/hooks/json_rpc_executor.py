"""JSON-RPC based hook executor that runs hooks as subprocess calls."""

import json
import logging
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from claude_mpm.hooks.base_hook import HookContext, HookResult, HookType
from claude_mpm.core.logger import get_logger

logger = get_logger(__name__)


class JSONRPCError(Exception):
    """JSON-RPC error exception."""
    
    def __init__(self, code: int, message: str, data: Optional[Any] = None):
        """Initialize JSON-RPC error.
        
        Args:
            code: Error code
            message: Error message
            data: Optional error data
        """
        super().__init__(message)
        self.code = code
        self.message = message
        self.data = data


class JSONRPCHookExecutor:
    """Executes hooks via JSON-RPC subprocess calls."""
    
    # JSON-RPC error codes
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603
    
    def __init__(self, timeout: int = 30):
        """Initialize JSON-RPC hook executor.
        
        Args:
            timeout: Timeout for hook execution in seconds
        """
        self.timeout = timeout
        self._hook_runner_path = Path(__file__).parent / "hook_runner.py"
        
    def execute_hook(self, hook_name: str, hook_type: HookType,
                    context_data: Dict[str, Any],
                    metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute a hook via JSON-RPC subprocess.
        
        Args:
            hook_name: Name of the hook to execute
            hook_type: Type of hook
            context_data: Context data for the hook
            metadata: Optional metadata
            
        Returns:
            Execution result dictionary
            
        Raises:
            JSONRPCError: If JSON-RPC call fails
        """
        # Create JSON-RPC request
        request = {
            "jsonrpc": "2.0",
            "method": "execute_hook",
            "params": {
                "hook_name": hook_name,
                "hook_type": hook_type.value,
                "context_data": context_data,
                "metadata": metadata or {}
            },
            "id": f"{hook_name}_{int(time.time()*1000)}"
        }
        
        try:
            # Execute hook runner subprocess
            result = subprocess.run(
                [sys.executable, str(self._hook_runner_path)],
                input=json.dumps(request),
                capture_output=True,
                text=True,
                timeout=self.timeout
            )
            
            if result.returncode != 0:
                logger.error(f"Hook runner failed with code {result.returncode}: {result.stderr}")
                raise JSONRPCError(
                    self.INTERNAL_ERROR,
                    f"Hook runner process failed: {result.stderr}"
                )
                
            # Parse JSON-RPC response
            try:
                response = json.loads(result.stdout)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse hook runner output: {result.stdout}")
                raise JSONRPCError(
                    self.PARSE_ERROR,
                    f"Invalid JSON response: {str(e)}"
                )
                
            # Check for JSON-RPC error
            if "error" in response:
                error = response["error"]
                raise JSONRPCError(
                    error.get("code", self.INTERNAL_ERROR),
                    error.get("message", "Unknown error"),
                    error.get("data")
                )
                
            # Extract result
            if "result" not in response:
                raise JSONRPCError(
                    self.INVALID_REQUEST,
                    "Missing result in response"
                )
                
            return response["result"]
            
        except subprocess.TimeoutExpired:
            logger.error(f"Hook execution timed out after {self.timeout}s")
            raise JSONRPCError(
                self.INTERNAL_ERROR,
                f"Hook execution timed out after {self.timeout} seconds"
            )
        except Exception as e:
            if isinstance(e, JSONRPCError):
                raise
            logger.error(f"Unexpected error executing hook: {e}")
            raise JSONRPCError(
                self.INTERNAL_ERROR,
                f"Unexpected error: {str(e)}"
            )
            
    def execute_hooks(self, hook_type: HookType, hook_names: List[str],
                     context_data: Dict[str, Any],
                     metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute multiple hooks of the same type.
        
        Args:
            hook_type: Type of hooks to execute
            hook_names: List of hook names to execute
            context_data: Context data for the hooks
            metadata: Optional metadata
            
        Returns:
            List of execution results
        """
        results = []
        
        for hook_name in hook_names:
            try:
                result = self.execute_hook(
                    hook_name=hook_name,
                    hook_type=hook_type,
                    context_data=context_data,
                    metadata=metadata
                )
                results.append(result)
            except JSONRPCError as e:
                # Include error in results but continue with other hooks
                results.append({
                    "hook_name": hook_name,
                    "success": False,
                    "error": e.message,
                    "error_code": e.code,
                    "error_data": e.data
                })
                logger.error(f"Hook '{hook_name}' failed: {e.message}")
            except Exception as e:
                # Unexpected errors
                results.append({
                    "hook_name": hook_name,
                    "success": False,
                    "error": str(e)
                })
                logger.error(f"Unexpected error in hook '{hook_name}': {e}")
                
        return results
        
    def batch_execute(self, requests: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Execute multiple hook requests in batch.
        
        Args:
            requests: List of hook execution requests
            
        Returns:
            List of execution results
        """
        # Create JSON-RPC batch request
        batch_request = []
        for i, req in enumerate(requests):
            batch_request.append({
                "jsonrpc": "2.0",
                "method": "execute_hook",
                "params": req,
                "id": f"batch_{i}_{int(time.time()*1000)}"
            })
            
        try:
            # Execute hook runner with batch request
            result = subprocess.run(
                [sys.executable, str(self._hook_runner_path), "--batch"],
                input=json.dumps(batch_request),
                capture_output=True,
                text=True,
                timeout=self.timeout * len(requests)  # Scale timeout with batch size
            )
            
            if result.returncode != 0:
                logger.error(f"Batch hook runner failed: {result.stderr}")
                return [{
                    "success": False,
                    "error": f"Batch execution failed: {result.stderr}"
                } for _ in requests]
                
            # Parse batch response
            try:
                responses = json.loads(result.stdout)
            except json.JSONDecodeError:
                logger.error(f"Failed to parse batch response: {result.stdout}")
                return [{
                    "success": False,
                    "error": "Invalid JSON response from batch execution"
                } for _ in requests]
                
            # Extract results
            results = []
            for response in responses:
                if "error" in response:
                    results.append({
                        "success": False,
                        "error": response["error"].get("message", "Unknown error")
                    })
                else:
                    results.append(response.get("result", {"success": False}))
                    
            return results
            
        except subprocess.TimeoutExpired:
            logger.error(f"Batch execution timed out")
            return [{
                "success": False,
                "error": "Batch execution timed out"
            } for _ in requests]
        except Exception as e:
            logger.error(f"Unexpected error in batch execution: {e}")
            return [{
                "success": False,
                "error": f"Unexpected error: {str(e)}"
            } for _ in requests]