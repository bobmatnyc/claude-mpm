"""Tool call interceptor for claude-mpm hook system."""

import asyncio
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional

from claude_mpm.core.logger import get_logger
from claude_mpm.hooks.base_hook import BaseHook, HookContext, HookType

logger = get_logger(__name__)


class SimpleHookRunner:
    """Simple hook runner for direct hook execution."""

    def __init__(self):
        """Initialize the simple hook runner."""
        self._hooks: Dict[HookType, List[BaseHook]] = defaultdict(list)
        self._hook_instances: Dict[str, BaseHook] = {}

    def register_hook(self, hook: BaseHook, hook_type: Optional[HookType] = None):
        """Register a hook instance."""
        if hook_type is None:
            hook_type = HookType.CUSTOM

        if hook.name in self._hook_instances:
            # Remove old instance
            for hook_list in self._hooks.values():
                if self._hook_instances[hook.name] in hook_list:
                    hook_list.remove(self._hook_instances[hook.name])

        self._hooks[hook_type].append(hook)
        self._hook_instances[hook.name] = hook
        self._hooks[hook_type].sort()  # Sort by priority

    async def run_hooks(self, context: HookContext) -> List[Dict[str, Any]]:
        """Run all hooks for the given context."""
        hooks = [h for h in self._hooks[context.hook_type] if h.enabled]
        results = []

        for hook in hooks:
            try:
                if hook.validate(context):
                    result = hook.execute(context)
                    results.append(
                        {
                            "hook_name": hook.name,
                            "success": result.success,
                            "data": result.data,
                            "error": result.error,
                            "modified": result.modified,
                            "metadata": result.metadata,
                        }
                    )

                    # Update context if modified
                    if result.modified and result.data:
                        context.data.update(result.data)
            except Exception as e:
                logger.error(f"Hook '{hook.name}' execution failed: {e}")
                results.append(
                    {"hook_name": hook.name, "success": False, "error": str(e)}
                )

        return results


class ToolCallInterceptor:
    """Intercepts and processes tool calls through the hook system."""

    def __init__(self, hook_runner: Optional[SimpleHookRunner] = None):
        """Initialize the tool call interceptor.

        Args:
            hook_runner: Optional hook runner instance. If not provided, creates a new one.
        """
        self.hook_runner = hook_runner or SimpleHookRunner()

    async def intercept_tool_call(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Intercept a tool call and run it through the hook system.

        Args:
            tool_name: Name of the tool being called
            parameters: Parameters being passed to the tool
            metadata: Optional metadata for the tool call

        Returns:
            Dict containing:
                - allowed: Whether the tool call should proceed
                - parameters: Potentially modified parameters
                - error: Error message if not allowed
                - metadata: Additional metadata from hooks
        """
        # Create hook context for tool call interception
        context = HookContext(
            hook_type=HookType.CUSTOM,
            data={
                "tool_name": tool_name,
                "parameters": parameters.copy(),  # Copy to avoid modifying original
            },
            metadata=metadata or {},
            timestamp=datetime.now(),
        )

        # Run hooks
        results = await self.hook_runner.run_hooks(context)

        # Process results
        allowed = True
        modified_params = parameters
        errors = []
        hook_metadata = {}

        for result in results:
            if not result.get("success", True):
                allowed = False
                if result.get("error"):
                    errors.append(
                        f"[{result.get('hook_name', 'Unknown')}] {result.get('error')}"
                    )

            if result.get("modified") and result.get("data"):
                # Update parameters if modified
                if "parameters" in result.get("data", {}):
                    modified_params = result["data"]["parameters"]

            if result.get("metadata"):
                hook_metadata.update(result["metadata"])

        return {
            "allowed": allowed,
            "parameters": modified_params,
            "error": "\n".join(errors) if errors else None,
            "metadata": hook_metadata,
        }

    def intercept_tool_call_sync(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Synchronous version of intercept_tool_call."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(
                self.intercept_tool_call(tool_name, parameters, metadata)
            )
        finally:
            loop.close()


class ToolCallHookIntegration:
    """Integration helper for adding tool call interception to existing systems."""

    @staticmethod
    def wrap_tool_executor(original_executor, interceptor: ToolCallInterceptor):
        """Wrap an existing tool executor with hook interception.

        Args:
            original_executor: The original tool execution function
            interceptor: The tool call interceptor instance

        Returns:
            Wrapped executor function
        """

        async def wrapped_executor(
            tool_name: str, parameters: Dict[str, Any], **kwargs
        ):
            # Intercept the tool call
            interception_result = await interceptor.intercept_tool_call(
                tool_name, parameters, kwargs.get("metadata")
            )

            # Check if allowed
            if not interception_result["allowed"]:
                raise ValueError(f"Tool call blocked: {interception_result['error']}")

            # Execute with potentially modified parameters
            return await original_executor(
                tool_name, interception_result["parameters"], **kwargs
            )

        return wrapped_executor

    @staticmethod
    def create_tool_call_validator(
        valid_tools: List[str], interceptor: ToolCallInterceptor
    ):
        """Create a tool call validator that uses the hook system.

        Args:
            valid_tools: List of valid tool names
            interceptor: The tool call interceptor instance

        Returns:
            Validator function
        """

        def validator(tool_name: str, parameters: Dict[str, Any]) -> bool:
            # Basic validation
            if tool_name not in valid_tools:
                return False

            # Hook-based validation
            result = interceptor.intercept_tool_call_sync(tool_name, parameters)
            return result["allowed"]

        return validator
