"""
Base class for manager-style services to reduce duplication.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Set, TypeVar

from .config_service_base import ConfigServiceBase

T = TypeVar("T")


class ManagerBase(ConfigServiceBase, ABC):
    """
    Base class for manager-style services.

    Provides common patterns for services that manage collections of items:
    - Item registration and discovery
    - Lifecycle management
    - Caching and indexing
    - Validation and filtering
    """

    def __init__(
        self,
        manager_name: str,
        config: Optional[Dict[str, Any]] = None,
        config_section: Optional[str] = None,
    ):
        """
        Initialize manager.

        Args:
            manager_name: Name of the manager
            config: Configuration dictionary
            config_section: Configuration section name
        """
        super().__init__(manager_name, config, config_section)

        # Item storage
        self._items: Dict[str, T] = {}
        self._item_metadata: Dict[str, Dict[str, Any]] = {}

        # Indexing
        self._indexes: Dict[str, Dict[Any, Set[str]]] = {}

        # State tracking
        self._initialized = False
        self._last_scan_time: Optional[float] = None

        # Configuration
        self._auto_scan = self.get_config_value("auto_scan", True, config_type=bool)
        self._cache_enabled = self.get_config_value(
            "cache_enabled", True, config_type=bool
        )
        self._max_items = self.get_config_value("max_items", 1000, config_type=int)

    @property
    def item_count(self) -> int:
        """Get number of managed items."""
        return len(self._items)

    @property
    def is_initialized(self) -> bool:
        """Check if manager is initialized."""
        return self._initialized

    def initialize(self) -> bool:
        """
        Initialize the manager.

        Returns:
            True if initialization successful
        """
        if self._initialized:
            self.logger.warning(f"Manager {self.service_name} already initialized")
            return True

        self.logger.info(f"Initializing manager: {self.service_name}")

        try:
            # Manager-specific initialization
            success = self._do_initialize()

            if success:
                # Perform initial scan if auto-scan enabled
                if self._auto_scan:
                    self.scan_items()

                self._initialized = True
                self.logger.info(
                    f"Manager {self.service_name} initialized successfully"
                )
            else:
                self.logger.error(f"Manager {self.service_name} initialization failed")

            return success

        except Exception as e:
            self.logger.error(
                f"Manager {self.service_name} initialization error: {e}", exc_info=True
            )
            return False

    def register_item(
        self, item_id: str, item: T, metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Register an item.

        Args:
            item_id: Unique identifier for the item
            item: The item to register
            metadata: Optional metadata for the item

        Returns:
            True if registration successful
        """
        if not self._initialized:
            self.logger.warning("Manager not initialized")
            return False

        # Check item limit
        if len(self._items) >= self._max_items:
            self.logger.warning(f"Maximum items ({self._max_items}) reached")
            return False

        # Validate item
        if not self._validate_item(item_id, item):
            return False

        # Store item
        self._items[item_id] = item
        self._item_metadata[item_id] = metadata or {}

        # Update indexes
        self._update_indexes(item_id, item, metadata)

        self.logger.debug(f"Registered item: {item_id}")
        return True

    def unregister_item(self, item_id: str) -> bool:
        """
        Unregister an item.

        Args:
            item_id: Identifier of item to unregister

        Returns:
            True if unregistration successful
        """
        if item_id not in self._items:
            self.logger.warning(f"Item not found: {item_id}")
            return False

        # Remove from storage
        item = self._items.pop(item_id)
        metadata = self._item_metadata.pop(item_id, {})

        # Update indexes
        self._remove_from_indexes(item_id, item, metadata)

        self.logger.debug(f"Unregistered item: {item_id}")
        return True

    def get_item(self, item_id: str) -> Optional[T]:
        """Get item by ID."""
        return self._items.get(item_id)

    def get_item_metadata(self, item_id: str) -> Dict[str, Any]:
        """Get item metadata."""
        return self._item_metadata.get(item_id, {})

    def list_items(self, filter_func=None) -> List[str]:
        """
        List item IDs.

        Args:
            filter_func: Optional filter function

        Returns:
            List of item IDs
        """
        if filter_func is None:
            return list(self._items.keys())

        return [
            item_id
            for item_id, item in self._items.items()
            if filter_func(item_id, item, self._item_metadata.get(item_id, {}))
        ]

    def find_items(self, **criteria) -> List[str]:
        """
        Find items by criteria using indexes.

        Args:
            **criteria: Search criteria

        Returns:
            List of matching item IDs
        """
        if not criteria:
            return self.list_items()

        # Use indexes if available
        result_sets = []
        for key, value in criteria.items():
            if key in self._indexes and value in self._indexes[key]:
                result_sets.append(self._indexes[key][value])

        if result_sets:
            # Intersection of all criteria
            result = result_sets[0]
            for result_set in result_sets[1:]:
                result = result.intersection(result_set)
            return list(result)

        # Fallback to linear search
        return self.list_items(
            lambda item_id, item, metadata: all(
                metadata.get(key) == value for key, value in criteria.items()
            )
        )

    def scan_items(self) -> int:
        """
        Scan for items and update registry.

        Returns:
            Number of items found
        """
        import time

        self.logger.info(f"Scanning for items: {self.service_name}")
        start_time = time.time()

        try:
            # Manager-specific scanning
            found_items = self._do_scan_items()

            # Update scan time
            self._last_scan_time = time.time()

            scan_duration = self._last_scan_time - start_time
            self.logger.info(
                f"Scan completed: found {found_items} items in {scan_duration:.2f}s"
            )

            return found_items

        except Exception as e:
            self.logger.error(f"Scan failed: {e}", exc_info=True)
            return 0

    def clear_items(self) -> None:
        """Clear all items."""
        self.logger.info(f"Clearing all items: {self.service_name}")
        self._items.clear()
        self._item_metadata.clear()
        self._indexes.clear()

    def get_status(self) -> Dict[str, Any]:
        """
        Get manager status.

        Returns:
            Status dictionary
        """
        return {
            "manager": self.service_name,
            "initialized": self._initialized,
            "item_count": self.item_count,
            "max_items": self._max_items,
            "auto_scan": self._auto_scan,
            "cache_enabled": self._cache_enabled,
            "last_scan_time": self._last_scan_time,
            "indexes": list(self._indexes.keys()),
        }

    def _create_index(self, index_name: str) -> None:
        """Create an index for fast lookups."""
        if index_name not in self._indexes:
            self._indexes[index_name] = {}
            self.logger.debug(f"Created index: {index_name}")

    def _update_indexes(self, item_id: str, item: T, metadata: Dict[str, Any]) -> None:
        """Update indexes for an item."""
        # Manager-specific index updates
        self._do_update_indexes(item_id, item, metadata)

    def _remove_from_indexes(
        self, item_id: str, item: T, metadata: Dict[str, Any]
    ) -> None:
        """Remove item from indexes."""
        for _index_name, index in self._indexes.items():
            for _value, item_set in index.items():
                item_set.discard(item_id)

    @abstractmethod
    def _do_initialize(self) -> bool:
        """Manager-specific initialization logic."""

    @abstractmethod
    def _validate_item(self, item_id: str, item: T) -> bool:
        """Validate an item before registration."""

    @abstractmethod
    def _do_scan_items(self) -> int:
        """Manager-specific item scanning logic."""

    def _do_update_indexes(
        self, item_id: str, item: T, metadata: Dict[str, Any]
    ) -> None:
        """Manager-specific index update logic."""
