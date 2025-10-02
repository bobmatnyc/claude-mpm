"""
Context Strategy - Context-based lifecycle management for configurations
Part of Phase 3 Configuration Consolidation
"""

import threading
import weakref
from abc import ABC, abstractmethod
from collections import OrderedDict
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Union

from claude_mpm.core.logging_utils import get_logger

from .unified_config_service import IConfigStrategy


class ContextScope(Enum):
    """Configuration context scopes"""

    GLOBAL = "global"  # Application-wide
    SESSION = "session"  # User session
    PROJECT = "project"  # Project-specific
    AGENT = "agent"  # Agent-specific
    SERVICE = "service"  # Service-specific
    TRANSACTION = "transaction"  # Transaction-specific
    REQUEST = "request"  # Request-specific
    THREAD = "thread"  # Thread-local
    TEMPORARY = "temporary"  # Temporary context


class ContextLifecycle(Enum):
    """Context lifecycle states"""

    CREATED = "created"
    INITIALIZING = "initializing"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    CLOSING = "closing"
    CLOSED = "closed"


@dataclass
class ContextMetadata:
    """Metadata for context tracking"""

    id: str
    scope: ContextScope
    lifecycle: ContextLifecycle
    created_at: datetime
    updated_at: datetime
    parent_id: Optional[str] = None
    children: List[str] = field(default_factory=list)
    attributes: Dict[str, Any] = field(default_factory=dict)
    ttl: Optional[timedelta] = None
    expires_at: Optional[datetime] = None


@dataclass
class ContextConfig:
    """Configuration within a context"""

    context_id: str
    data: Dict[str, Any]
    overrides: Dict[str, Any] = field(default_factory=dict)
    defaults: Dict[str, Any] = field(default_factory=dict)
    locked_keys: Set[str] = field(default_factory=set)
    watchers: Dict[str, List[Callable]] = field(default_factory=dict)


class BaseContextManager(ABC):
    """Base class for context managers"""

    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
        self.contexts: Dict[str, ContextMetadata] = {}
        self.configs: Dict[str, ContextConfig] = {}
        self._lock = threading.RLock()

    @abstractmethod
    def create_context(self, scope: ContextScope, **kwargs) -> str:
        """Create a new context"""

    @abstractmethod
    def get_context(self, context_id: str) -> Optional[ContextMetadata]:
        """Get context metadata"""

    @abstractmethod
    def close_context(self, context_id: str):
        """Close a context"""


class HierarchicalContextManager(BaseContextManager):
    """Manages hierarchical context relationships"""

    def __init__(self):
        super().__init__()
        self.context_stack = threading.local()
        self.context_hierarchy: Dict[str, List[str]] = {}  # parent -> children

    def create_context(
        self,
        scope: ContextScope,
        parent_id: Optional[str] = None,
        ttl: Optional[timedelta] = None,
        **kwargs,
    ) -> str:
        """Create a new hierarchical context"""
        with self._lock:
            # Generate context ID
            context_id = self._generate_context_id(scope)

            # Use current context as parent if not specified
            if parent_id is None and hasattr(self.context_stack, "stack"):
                if self.context_stack.stack:
                    parent_id = self.context_stack.stack[-1]

            # Create metadata
            metadata = ContextMetadata(
                id=context_id,
                scope=scope,
                lifecycle=ContextLifecycle.CREATED,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                parent_id=parent_id,
                ttl=ttl,
                expires_at=datetime.now(timezone.utc) + ttl if ttl else None,
                attributes=kwargs,
            )

            # Store context
            self.contexts[context_id] = metadata

            # Update hierarchy
            if parent_id and parent_id in self.contexts:
                self.contexts[parent_id].children.append(context_id)
                if parent_id not in self.context_hierarchy:
                    self.context_hierarchy[parent_id] = []
                self.context_hierarchy[parent_id].append(context_id)

            # Initialize context config
            self.configs[context_id] = ContextConfig(context_id=context_id, data={})

            # Set lifecycle to active
            metadata.lifecycle = ContextLifecycle.ACTIVE

            self.logger.debug(f"Created context: {context_id} (scope={scope.value})")
            return context_id

    def get_context(self, context_id: str) -> Optional[ContextMetadata]:
        """Get context metadata"""
        with self._lock:
            context = self.contexts.get(context_id)

            # Check expiration
            if context and context.expires_at:
                if datetime.now(timezone.utc) > context.expires_at:
                    self.close_context(context_id)
                    return None

            return context

    def close_context(self, context_id: str):
        """Close a context and its children"""
        with self._lock:
            if context_id not in self.contexts:
                return

            context = self.contexts[context_id]
            context.lifecycle = ContextLifecycle.CLOSING

            # Close all children first
            for child_id in context.children[:]:
                self.close_context(child_id)

            # Remove from parent's children
            if context.parent_id and context.parent_id in self.contexts:
                parent = self.contexts[context.parent_id]
                if context_id in parent.children:
                    parent.children.remove(context_id)

            # Clean up hierarchy
            if context_id in self.context_hierarchy:
                del self.context_hierarchy[context_id]

            # Remove configs
            if context_id in self.configs:
                del self.configs[context_id]

            # Remove context
            del self.contexts[context_id]

            context.lifecycle = ContextLifecycle.CLOSED
            self.logger.debug(f"Closed context: {context_id}")

    def get_context_chain(self, context_id: str) -> List[str]:
        """Get the chain of contexts from root to specified context"""
        chain = []
        current_id = context_id

        while current_id:
            if current_id in self.contexts:
                chain.insert(0, current_id)
                current_id = self.contexts[current_id].parent_id
            else:
                break

        return chain

    def _generate_context_id(self, scope: ContextScope) -> str:
        """Generate unique context ID"""
        import uuid

        return f"{scope.value}_{uuid.uuid4().hex[:8]}"

    @contextmanager
    def context(self, scope: ContextScope, **kwargs):
        """Context manager for automatic context lifecycle"""
        context_id = self.create_context(scope, **kwargs)

        # Push to thread-local stack
        if not hasattr(self.context_stack, "stack"):
            self.context_stack.stack = []
        self.context_stack.stack.append(context_id)

        try:
            yield context_id
        finally:
            # Pop from stack
            if self.context_stack.stack and self.context_stack.stack[-1] == context_id:
                self.context_stack.stack.pop()

            # Close context
            self.close_context(context_id)


class ScopedConfigManager:
    """Manages configuration within scoped contexts"""

    def __init__(self, context_manager: HierarchicalContextManager):
        self.logger = get_logger(self.__class__.__name__)
        self.context_manager = context_manager
        self._lock = threading.RLock()

    def get_config(
        self, context_id: str, key: Optional[str] = None, inherit: bool = True
    ) -> Any:
        """Get configuration value from context"""
        with self._lock:
            if context_id not in self.context_manager.configs:
                return None

            if inherit:
                # Get merged config from context chain
                config = self._get_inherited_config(context_id)
            else:
                # Get config from this context only
                config = self.context_manager.configs[context_id].data

            if key:
                return self._get_nested_value(config, key)
            return config

    def set_config(
        self,
        context_id: str,
        key: str,
        value: Any,
        override: bool = False,
        lock: bool = False,
    ):
        """Set configuration value in context"""
        with self._lock:
            if context_id not in self.context_manager.configs:
                raise ValueError(f"Context not found: {context_id}")

            config = self.context_manager.configs[context_id]

            # Check if key is locked
            if key in config.locked_keys and not override:
                raise ValueError(f"Configuration key is locked: {key}")

            # Set value
            if override:
                config.overrides[key] = value
            else:
                self._set_nested_value(config.data, key, value)

            # Lock key if requested
            if lock:
                config.locked_keys.add(key)

            # Trigger watchers
            self._trigger_watchers(context_id, key, value)

            # Update context metadata
            if context_id in self.context_manager.contexts:
                self.context_manager.contexts[context_id].updated_at = datetime.now(
                    timezone.utc
                )

    def _get_inherited_config(self, context_id: str) -> Dict[str, Any]:
        """Get merged configuration from context hierarchy"""
        chain = self.context_manager.get_context_chain(context_id)
        merged = {}

        for ctx_id in chain:
            if ctx_id in self.context_manager.configs:
                config = self.context_manager.configs[ctx_id]

                # Apply defaults first
                merged = self._deep_merge(config.defaults, merged)

                # Apply data
                merged = self._deep_merge(merged, config.data)

                # Apply overrides last
                merged = self._deep_merge(merged, config.overrides)

        return merged

    def _deep_merge(self, base: Dict, override: Dict) -> Dict:
        """Deep merge two dictionaries"""
        result = base.copy()

        for key, value in override.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value

        return result

    def _get_nested_value(self, config: Dict, key: str) -> Any:
        """Get nested value using dot notation"""
        parts = key.split(".")
        current = config

        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None

        return current

    def _set_nested_value(self, config: Dict, key: str, value: Any):
        """Set nested value using dot notation"""
        parts = key.split(".")
        current = config

        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]

        current[parts[-1]] = value

    def _trigger_watchers(self, context_id: str, key: str, value: Any):
        """Trigger configuration watchers"""
        if context_id in self.context_manager.configs:
            config = self.context_manager.configs[context_id]

            # Trigger exact match watchers
            if key in config.watchers:
                for watcher in config.watchers[key]:
                    try:
                        watcher(key, value, context_id)
                    except Exception as e:
                        self.logger.error(f"Watcher failed: {e}")

            # Trigger pattern watchers
            for pattern, watchers in config.watchers.items():
                if "*" in pattern or "?" in pattern:
                    import fnmatch

                    if fnmatch.fnmatch(key, pattern):
                        for watcher in watchers:
                            try:
                                watcher(key, value, context_id)
                            except Exception as e:
                                self.logger.error(f"Pattern watcher failed: {e}")


class IsolatedContextManager:
    """Manages isolated configuration contexts"""

    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
        self.isolated_contexts: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()

    def create_isolated_context(
        self, base_config: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create an isolated context with no inheritance"""
        import uuid

        context_id = f"isolated_{uuid.uuid4().hex[:8]}"

        with self._lock:
            self.isolated_contexts[context_id] = base_config or {}
            self.logger.debug(f"Created isolated context: {context_id}")

        return context_id

    def get_isolated_config(self, context_id: str) -> Dict[str, Any]:
        """Get configuration from isolated context"""
        with self._lock:
            return self.isolated_contexts.get(context_id, {}).copy()

    def update_isolated_config(self, context_id: str, updates: Dict[str, Any]):
        """Update isolated context configuration"""
        with self._lock:
            if context_id in self.isolated_contexts:
                self.isolated_contexts[context_id].update(updates)

    def close_isolated_context(self, context_id: str):
        """Close isolated context"""
        with self._lock:
            if context_id in self.isolated_contexts:
                del self.isolated_contexts[context_id]
                self.logger.debug(f"Closed isolated context: {context_id}")


class ThreadLocalContextManager:
    """Manages thread-local configuration contexts"""

    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
        self.thread_contexts = threading.local()
        self._global_registry: weakref.WeakValueDictionary = (
            weakref.WeakValueDictionary()
        )

    def get_thread_context(self) -> Optional[Dict[str, Any]]:
        """Get current thread's context"""
        if hasattr(self.thread_contexts, "config"):
            return self.thread_contexts.config
        return None

    def set_thread_context(self, config: Dict[str, Any]):
        """Set current thread's context"""
        self.thread_contexts.config = config
        self._global_registry[threading.current_thread().ident] = config

    def clear_thread_context(self):
        """Clear current thread's context"""
        if hasattr(self.thread_contexts, "config"):
            delattr(self.thread_contexts, "config")

    @contextmanager
    def thread_context(self, config: Dict[str, Any]):
        """Context manager for thread-local configuration"""
        old_config = self.get_thread_context()
        self.set_thread_context(config)

        try:
            yield config
        finally:
            if old_config is not None:
                self.set_thread_context(old_config)
            else:
                self.clear_thread_context()


class CachingContextManager:
    """Manages context-aware configuration caching"""

    def __init__(self, max_size: int = 1000):
        self.logger = get_logger(self.__class__.__name__)
        self.cache: OrderedDict = OrderedDict()
        self.max_size = max_size
        self._lock = threading.RLock()
        self.hit_count = 0
        self.miss_count = 0

    def get_cached(self, context_id: str, key: str) -> Optional[Any]:
        """Get cached value for context"""
        cache_key = f"{context_id}:{key}"

        with self._lock:
            if cache_key in self.cache:
                # Move to end (LRU)
                self.cache.move_to_end(cache_key)
                self.hit_count += 1
                return self.cache[cache_key]

            self.miss_count += 1
            return None

    def set_cached(self, context_id: str, key: str, value: Any):
        """Cache value for context"""
        cache_key = f"{context_id}:{key}"

        with self._lock:
            # Remove oldest if at capacity
            if len(self.cache) >= self.max_size:
                self.cache.popitem(last=False)

            self.cache[cache_key] = value

    def invalidate_context(self, context_id: str):
        """Invalidate all cached values for context"""
        with self._lock:
            keys_to_remove = [k for k in self.cache if k.startswith(f"{context_id}:")]

            for key in keys_to_remove:
                del self.cache[key]

    def get_statistics(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_requests = self.hit_count + self.miss_count

        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "hit_count": self.hit_count,
            "miss_count": self.miss_count,
            "hit_rate": (
                (self.hit_count / total_requests * 100) if total_requests > 0 else 0
            ),
            "utilization": (
                (len(self.cache) / self.max_size * 100) if self.max_size > 0 else 0
            ),
        }


class ContextStrategy(IConfigStrategy):
    """
    Main context strategy for configuration lifecycle management
    Provides context-based configuration with hierarchy, isolation, and caching
    """

    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
        self.hierarchy_manager = HierarchicalContextManager()
        self.scoped_manager = ScopedConfigManager(self.hierarchy_manager)
        self.isolated_manager = IsolatedContextManager()
        self.thread_manager = ThreadLocalContextManager()
        self.cache_manager = CachingContextManager()

    def can_handle(self, source: Union[str, Path, Dict]) -> bool:
        """Context strategy handles dictionary configurations"""
        return isinstance(source, dict)

    def load(self, source: Any, **kwargs) -> Dict[str, Any]:
        """Load configuration into context"""
        context_scope = kwargs.get("context_scope", ContextScope.TEMPORARY)
        context_id = kwargs.get("context_id")

        if not context_id:
            # Create new context
            context_id = self.hierarchy_manager.create_context(
                context_scope, ttl=kwargs.get("ttl")
            )

        # Load config into context
        if isinstance(source, dict):
            for key, value in source.items():
                self.scoped_manager.set_config(context_id, key, value)

        return self.scoped_manager.get_config(context_id)

    def validate(self, config: Dict[str, Any], schema: Optional[Dict] = None) -> bool:
        """Validate configuration in context"""
        return True

    def transform(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Transform configuration based on context"""
        # Apply context-specific transformations
        context = self.get_current_context()

        if context:
            # Apply context-specific overrides
            overrides = self.scoped_manager.get_config(
                context, "transformations.overrides", inherit=True
            )

            if overrides:
                config = self._apply_overrides(config, overrides)

        return config

    def create_context(
        self,
        scope: ContextScope = ContextScope.TEMPORARY,
        parent: Optional[str] = None,
        isolated: bool = False,
        **kwargs,
    ) -> str:
        """Create a new configuration context"""
        if isolated:
            return self.isolated_manager.create_isolated_context(
                kwargs.get("base_config")
            )
        return self.hierarchy_manager.create_context(scope, parent_id=parent, **kwargs)

    def get_current_context(self) -> Optional[str]:
        """Get current active context"""
        # Check thread-local stack
        if hasattr(self.hierarchy_manager.context_stack, "stack"):
            stack = self.hierarchy_manager.context_stack.stack
            if stack:
                return stack[-1]

        # Check for global context
        for ctx_id, metadata in self.hierarchy_manager.contexts.items():
            if (
                metadata.scope == ContextScope.GLOBAL
                and metadata.lifecycle == ContextLifecycle.ACTIVE
            ):
                return ctx_id

        return None

    def with_context(self, context_id: str, operation: Callable) -> Any:
        """Execute operation within specified context"""
        # Push context
        if not hasattr(self.hierarchy_manager.context_stack, "stack"):
            self.hierarchy_manager.context_stack.stack = []

        self.hierarchy_manager.context_stack.stack.append(context_id)

        try:
            return operation()
        finally:
            # Pop context
            if self.hierarchy_manager.context_stack.stack:
                self.hierarchy_manager.context_stack.stack.pop()

    @contextmanager
    def context(self, scope: ContextScope = ContextScope.TEMPORARY, **kwargs):
        """Context manager for configuration contexts"""
        with self.hierarchy_manager.context(scope, **kwargs) as context_id:
            yield context_id

    def get_config(
        self,
        key: Optional[str] = None,
        context: Optional[str] = None,
        default: Any = None,
    ) -> Any:
        """Get configuration value from context"""
        context_id = context or self.get_current_context()

        if not context_id:
            return default

        # Check cache first
        if key:
            cached = self.cache_manager.get_cached(context_id, key)
            if cached is not None:
                return cached

        # Get from context
        value = self.scoped_manager.get_config(context_id, key)

        # Cache result
        if key and value is not None:
            self.cache_manager.set_cached(context_id, key, value)

        return value if value is not None else default

    def set_config(self, key: str, value: Any, context: Optional[str] = None, **kwargs):
        """Set configuration value in context"""
        context_id = context or self.get_current_context()

        if not context_id:
            # Create temporary context
            context_id = self.create_context(ContextScope.TEMPORARY)

        self.scoped_manager.set_config(context_id, key, value, **kwargs)

        # Invalidate cache
        self.cache_manager.invalidate_context(context_id)

    def close_context(self, context_id: str):
        """Close a configuration context"""
        # Invalidate cache
        self.cache_manager.invalidate_context(context_id)

        # Close context
        if context_id.startswith("isolated_"):
            self.isolated_manager.close_isolated_context(context_id)
        else:
            self.hierarchy_manager.close_context(context_id)

    def _apply_overrides(self, config: Dict, overrides: Dict) -> Dict:
        """Apply context overrides to configuration"""
        result = config.copy()

        for key, value in overrides.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = self._apply_overrides(result[key], value)
            else:
                result[key] = value

        return result

    def get_statistics(self) -> Dict[str, Any]:
        """Get context strategy statistics"""
        return {
            "active_contexts": len(self.hierarchy_manager.contexts),
            "isolated_contexts": len(self.isolated_manager.isolated_contexts),
            "cache_stats": self.cache_manager.get_statistics(),
            "contexts_by_scope": self._count_by_scope(),
            "contexts_by_lifecycle": self._count_by_lifecycle(),
        }

    def _count_by_scope(self) -> Dict[str, int]:
        """Count contexts by scope"""
        counts = {}
        for metadata in self.hierarchy_manager.contexts.values():
            scope = metadata.scope.value
            counts[scope] = counts.get(scope, 0) + 1
        return counts

    def _count_by_lifecycle(self) -> Dict[str, int]:
        """Count contexts by lifecycle state"""
        counts = {}
        for metadata in self.hierarchy_manager.contexts.values():
            state = metadata.lifecycle.value
            counts[state] = counts.get(state, 0) + 1
        return counts


# Export main components
__all__ = [
    "ContextLifecycle",
    "ContextScope",
    "ContextStrategy",
    "HierarchicalContextManager",
    "ScopedConfigManager",
]
