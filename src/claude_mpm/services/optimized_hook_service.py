"""
Optimized Hook Service with Caching and Async Processing

High-performance hook service that minimizes overhead through:
- Hook configuration caching at startup
- Lazy loading of hook implementations
- Singleton pattern for efficient memory usage
- Async hook processing for non-blocking execution
"""

import asyncio
import time
import importlib
import inspect
from typing import List, Optional, Dict, Any, Type, Callable, Set
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock
from concurrent.futures import ThreadPoolExecutor, Future
import logging

from claude_mpm.core.config import Config
from claude_mpm.core.logger import get_logger
from claude_mpm.hooks.base_hook import (
    BaseHook,
    PreDelegationHook,
    PostDelegationHook,
    HookContext,
    HookResult,
    HookType
)


@dataclass
class HookConfig:
    """Cached hook configuration."""
    name: str
    module_path: str
    class_name: str
    priority: int = 50
    enabled: bool = True
    params: Dict[str, Any] = field(default_factory=dict)
    loaded_instance: Optional[BaseHook] = None


@dataclass
class HookExecutionMetrics:
    """Metrics for hook execution performance."""
    execution_count: int = 0
    total_time_ms: float = 0.0
    avg_time_ms: float = 0.0
    max_time_ms: float = 0.0
    min_time_ms: float = float('inf')
    error_count: int = 0
    last_execution: Optional[float] = None


class OptimizedHookService:
    """
    Optimized hook service with caching and async execution.
    
    Features:
    - Caches hook configurations at startup
    - Lazy loads hook implementations on first use
    - Singleton pattern for memory efficiency
    - Async/parallel hook execution support
    - Detailed performance metrics
    """
    
    _instance: Optional['OptimizedHookService'] = None
    _lock = Lock()
    
    def __new__(cls, *args, **kwargs):
        """Singleton pattern implementation."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
            return cls._instance
    
    def __init__(self, config: Optional[Config] = None):
        """
        Initialize the optimized hook service.
        
        Args:
            config: Optional configuration object
        """
        # Skip re-initialization for singleton
        if hasattr(self, '_initialized'):
            return
        
        self.config = config or Config()
        self.logger = get_logger("optimized_hook_service")
        
        # Hook storage with lazy loading
        self._hook_configs: Dict[str, HookConfig] = {}
        self._pre_hooks_cache: List[HookConfig] = []
        self._post_hooks_cache: List[HookConfig] = []
        
        # Performance metrics
        self._metrics: Dict[str, HookExecutionMetrics] = {}
        
        # Async execution support
        self._executor = ThreadPoolExecutor(
            max_workers=self.config.get("hooks.max_workers", 4),
            thread_name_prefix="HookWorker"
        )
        
        # Load and cache hook configurations
        self._load_hook_configs()
        
        # Mark as initialized
        self._initialized = True
        
        self.logger.info(
            f"Initialized optimized hook service with "
            f"{len(self._pre_hooks_cache)} pre-hooks and "
            f"{len(self._post_hooks_cache)} post-hooks"
        )
    
    def _load_hook_configs(self):
        """Load and cache all hook configurations at startup."""
        # Load from configuration file
        hooks_config = self.config.get("hooks.registered", {})
        
        for hook_name, hook_data in hooks_config.items():
            if not hook_data.get("enabled", True):
                self.logger.debug(f"Skipping disabled hook: {hook_name}")
                continue
            
            config = HookConfig(
                name=hook_name,
                module_path=hook_data.get("module"),
                class_name=hook_data.get("class"),
                priority=hook_data.get("priority", 50),
                enabled=True,
                params=hook_data.get("params", {})
            )
            
            self._hook_configs[hook_name] = config
            
            # Categorize by type (inferred from name or config)
            hook_type = hook_data.get("type", "")
            if "pre" in hook_type.lower() or "before" in hook_name.lower():
                self._pre_hooks_cache.append(config)
            elif "post" in hook_type.lower() or "after" in hook_name.lower():
                self._post_hooks_cache.append(config)
        
        # Sort by priority (lower number = higher priority)
        self._pre_hooks_cache.sort(key=lambda h: h.priority)
        self._post_hooks_cache.sort(key=lambda h: h.priority)
        
        # Also scan for hooks in the hooks directory
        self._scan_hook_directory()
    
    def _scan_hook_directory(self):
        """Scan hooks directory for available hooks."""
        hooks_dir = Path(__file__).parent.parent / "hooks"
        
        if not hooks_dir.exists():
            return
        
        # Look for Python files in hooks directory
        for hook_file in hooks_dir.glob("**/*.py"):
            if hook_file.name.startswith("_"):
                continue
            
            # Convert file path to module path
            relative_path = hook_file.relative_to(hooks_dir.parent.parent)
            module_path = str(relative_path.with_suffix("")).replace("/", ".")
            
            # Skip if already configured
            if any(h.module_path == module_path for h in self._hook_configs.values()):
                continue
            
            # Try to load and inspect the module
            try:
                module = importlib.import_module(module_path)
                
                # Find hook classes in the module
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if issubclass(obj, BaseHook) and obj != BaseHook:
                        # Auto-register discovered hook
                        hook_name = f"auto_{hook_file.stem}_{name}"
                        
                        config = HookConfig(
                            name=hook_name,
                            module_path=module_path,
                            class_name=name,
                            priority=getattr(obj, 'priority', 50),
                            enabled=False  # Disabled by default for auto-discovered
                        )
                        
                        self._hook_configs[hook_name] = config
                        self.logger.debug(f"Discovered hook: {hook_name} (disabled)")
                        
            except Exception as e:
                self.logger.debug(f"Failed to scan {hook_file}: {e}")
    
    def _lazy_load_hook(self, config: HookConfig) -> Optional[BaseHook]:
        """
        Lazy load a hook instance when needed.
        
        Args:
            config: Hook configuration
            
        Returns:
            Loaded hook instance or None if failed
        """
        if config.loaded_instance:
            return config.loaded_instance
        
        try:
            # Import the module
            module = importlib.import_module(config.module_path)
            
            # Get the hook class
            hook_class = getattr(module, config.class_name)
            
            # Instantiate with parameters
            hook_instance = hook_class(**config.params)
            
            # Cache the instance
            config.loaded_instance = hook_instance
            
            # Initialize metrics
            self._metrics[config.name] = HookExecutionMetrics()
            
            self.logger.info(f"Lazy loaded hook: {config.name}")
            return hook_instance
            
        except Exception as e:
            self.logger.error(f"Failed to load hook {config.name}: {e}")
            return None
    
    def register_hook(self, hook: BaseHook) -> bool:
        """
        Register a hook instance directly.
        
        Args:
            hook: The hook to register
            
        Returns:
            True if successfully registered
        """
        try:
            # Create config for the hook
            config = HookConfig(
                name=hook.name,
                module_path=hook.__module__,
                class_name=hook.__class__.__name__,
                priority=hook.priority,
                enabled=hook.enabled,
                loaded_instance=hook
            )
            
            self._hook_configs[hook.name] = config
            
            # Add to appropriate cache
            if isinstance(hook, PreDelegationHook):
                self._pre_hooks_cache.append(config)
                self._pre_hooks_cache.sort(key=lambda h: h.priority)
            elif isinstance(hook, PostDelegationHook):
                self._post_hooks_cache.append(config)
                self._post_hooks_cache.sort(key=lambda h: h.priority)
            
            # Initialize metrics
            self._metrics[hook.name] = HookExecutionMetrics()
            
            self.logger.info(f"Registered hook: {hook.name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to register hook: {e}")
            return False
    
    async def execute_pre_delegation_hooks_async(
        self,
        context: HookContext
    ) -> HookResult:
        """
        Execute pre-delegation hooks asynchronously.
        
        Args:
            context: The hook context
            
        Returns:
            HookResult with processed data
        """
        if not self._are_hooks_enabled("pre_delegation"):
            return HookResult(success=True, data=context.data, modified=False)
        
        working_data = context.data.copy()
        has_modifications = False
        
        # Execute hooks in parallel where possible
        tasks = []
        
        for config in self._pre_hooks_cache:
            if not config.enabled:
                continue
            
            hook = self._lazy_load_hook(config)
            if not hook:
                continue
            
            # Check if hook can run in parallel (no data dependencies)
            if getattr(hook, 'parallel_safe', False):
                task = self._execute_hook_async(hook, context, config.name)
                tasks.append(task)
            else:
                # Execute sequentially for non-parallel-safe hooks
                result = await self._execute_hook_async(hook, context, config.name)
                if result.modified and result.data:
                    working_data.update(result.data)
                    has_modifications = True
        
        # Wait for parallel tasks
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, HookResult):
                    if result.modified and result.data:
                        working_data.update(result.data)
                        has_modifications = True
                elif isinstance(result, Exception):
                    self.logger.error(f"Hook execution error: {result}")
        
        return HookResult(
            success=True,
            data=working_data,
            modified=has_modifications
        )
    
    async def _execute_hook_async(
        self,
        hook: BaseHook,
        context: HookContext,
        hook_name: str
    ) -> HookResult:
        """Execute a single hook asynchronously with metrics."""
        try:
            # Validate hook
            if not hook.validate(context):
                return HookResult(success=False, data={}, modified=False)
            
            # Time execution
            start_time = time.perf_counter()
            
            # Execute hook (wrap synchronous hooks)
            if asyncio.iscoroutinefunction(hook.execute):
                result = await hook.execute(context)
            else:
                # Run synchronous hook in executor
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    self._executor,
                    hook.execute,
                    context
                )
            
            # Update metrics
            execution_time = (time.perf_counter() - start_time) * 1000
            self._update_metrics(hook_name, execution_time, success=True)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Hook {hook_name} failed: {e}")
            self._update_metrics(hook_name, 0, success=False)
            return HookResult(success=False, error=str(e))
    
    def execute_pre_delegation_hooks(self, context: HookContext) -> HookResult:
        """
        Execute pre-delegation hooks synchronously (backward compatible).
        
        Args:
            context: The hook context
            
        Returns:
            HookResult with processed data
        """
        # Run async version in new event loop
        try:
            loop = asyncio.new_event_loop()
            result = loop.run_until_complete(
                self.execute_pre_delegation_hooks_async(context)
            )
            loop.close()
            return result
        except Exception as e:
            self.logger.error(f"Failed to execute hooks: {e}")
            return HookResult(success=False, error=str(e))
    
    def execute_post_delegation_hooks(self, context: HookContext) -> HookResult:
        """
        Execute post-delegation hooks synchronously (backward compatible).
        
        Args:
            context: The hook context
            
        Returns:
            HookResult with processed data
        """
        if not self._are_hooks_enabled("post_delegation"):
            return HookResult(success=True, data=context.data, modified=False)
        
        working_data = context.data.copy()
        has_modifications = False
        
        for config in self._post_hooks_cache:
            if not config.enabled:
                continue
            
            hook = self._lazy_load_hook(config)
            if not hook:
                continue
            
            try:
                if not hook.validate(context):
                    continue
                
                # Time execution
                start_time = time.perf_counter()
                
                # Execute hook
                hook_context = HookContext(
                    hook_type=context.hook_type,
                    data=working_data,
                    metadata=context.metadata,
                    timestamp=context.timestamp,
                    session_id=context.session_id,
                    user_id=context.user_id
                )
                
                result = hook.execute(hook_context)
                
                # Update metrics
                execution_time = (time.perf_counter() - start_time) * 1000
                self._update_metrics(config.name, execution_time, success=result.success)
                
                if result.success and result.modified and result.data:
                    working_data.update(result.data)
                    has_modifications = True
                    
            except Exception as e:
                self.logger.error(f"Hook {config.name} failed: {e}")
                self._update_metrics(config.name, 0, success=False)
        
        return HookResult(
            success=True,
            data=working_data,
            modified=has_modifications
        )
    
    def _update_metrics(self, hook_name: str, execution_time_ms: float, success: bool):
        """Update execution metrics for a hook."""
        if hook_name not in self._metrics:
            self._metrics[hook_name] = HookExecutionMetrics()
        
        metrics = self._metrics[hook_name]
        metrics.execution_count += 1
        metrics.total_time_ms += execution_time_ms
        metrics.avg_time_ms = metrics.total_time_ms / metrics.execution_count
        metrics.max_time_ms = max(metrics.max_time_ms, execution_time_ms)
        metrics.min_time_ms = min(metrics.min_time_ms, execution_time_ms)
        metrics.last_execution = time.time()
        
        if not success:
            metrics.error_count += 1
    
    def _are_hooks_enabled(self, hook_type: str) -> bool:
        """Check if hooks are enabled."""
        if not self.config.get("hooks.enabled", True):
            return False
        
        if not self.config.get(f"hooks.{hook_type}.enabled", True):
            return False
        
        return True
    
    def get_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get performance metrics for all hooks."""
        return {
            name: {
                "execution_count": m.execution_count,
                "avg_time_ms": round(m.avg_time_ms, 2),
                "max_time_ms": round(m.max_time_ms, 2),
                "min_time_ms": round(m.min_time_ms, 2) if m.min_time_ms != float('inf') else 0,
                "error_count": m.error_count,
                "error_rate": round(m.error_count / m.execution_count * 100, 2) if m.execution_count > 0 else 0
            }
            for name, m in self._metrics.items()
        }
    
    def list_hooks(self) -> Dict[str, List[str]]:
        """List all registered hooks."""
        return {
            "pre_delegation": [h.name for h in self._pre_hooks_cache],
            "post_delegation": [h.name for h in self._post_hooks_cache],
            "available": list(self._hook_configs.keys())
        }
    
    def enable_hook(self, hook_name: str) -> bool:
        """Enable a hook by name."""
        if hook_name in self._hook_configs:
            self._hook_configs[hook_name].enabled = True
            return True
        return False
    
    def disable_hook(self, hook_name: str) -> bool:
        """Disable a hook by name."""
        if hook_name in self._hook_configs:
            self._hook_configs[hook_name].enabled = False
            return True
        return False
    
    def shutdown(self):
        """Shutdown the hook service and cleanup resources."""
        self.logger.info("Shutting down hook service")
        self._executor.shutdown(wait=True)


# Global singleton instance
_hook_service: Optional[OptimizedHookService] = None


def get_optimized_hook_service(config: Optional[Config] = None) -> OptimizedHookService:
    """
    Get the singleton optimized hook service instance.
    
    Args:
        config: Optional configuration
        
    Returns:
        The shared OptimizedHookService instance
    """
    global _hook_service
    
    if _hook_service is None:
        _hook_service = OptimizedHookService(config)
    
    return _hook_service