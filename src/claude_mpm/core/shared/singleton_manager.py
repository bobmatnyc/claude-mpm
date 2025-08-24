"""
Shared singleton management utilities to reduce duplication.
"""

import threading
from typing import Any, Dict, Type, TypeVar

from ..logger import get_logger

T = TypeVar("T")


class SingletonManager:
    """
    Centralized singleton management utility.

    Reduces duplication by providing thread-safe singleton patterns
    that can be used across different classes.
    """

    _instances: Dict[Type, Any] = {}
    _locks: Dict[Type, threading.Lock] = {}
    _global_lock = threading.Lock()

    @classmethod
    def get_instance(
        cls, singleton_class: Type[T], *args, force_new: bool = False, **kwargs
    ) -> T:
        """
        Get singleton instance of a class.

        Args:
            singleton_class: Class to get singleton instance of
            *args: Arguments for class constructor
            force_new: Force creation of new instance
            **kwargs: Keyword arguments for class constructor

        Returns:
            Singleton instance
        """
        # Get or create lock for this class
        if singleton_class not in cls._locks:
            with cls._global_lock:
                if singleton_class not in cls._locks:
                    cls._locks[singleton_class] = threading.Lock()

        # Get instance with class-specific lock
        with cls._locks[singleton_class]:
            if force_new or singleton_class not in cls._instances:
                logger = get_logger("singleton_manager")
                logger.debug(f"Creating singleton instance: {singleton_class.__name__}")

                instance = singleton_class(*args, **kwargs)
                cls._instances[singleton_class] = instance

                return instance

            return cls._instances[singleton_class]

    @classmethod
    def has_instance(cls, singleton_class: Type) -> bool:
        """
        Check if singleton instance exists.

        Args:
            singleton_class: Class to check

        Returns:
            True if instance exists
        """
        return singleton_class in cls._instances

    @classmethod
    def clear_instance(cls, singleton_class: Type) -> None:
        """
        Clear singleton instance.

        Args:
            singleton_class: Class to clear instance for
        """
        if singleton_class in cls._locks:
            with cls._locks[singleton_class]:
                if singleton_class in cls._instances:
                    logger = get_logger("singleton_manager")
                    logger.debug(
                        f"Clearing singleton instance: {singleton_class.__name__}"
                    )
                    del cls._instances[singleton_class]

    @classmethod
    def clear_all_instances(cls) -> None:
        """Clear all singleton instances."""
        with cls._global_lock:
            logger = get_logger("singleton_manager")
            logger.debug(f"Clearing {len(cls._instances)} singleton instances")
            cls._instances.clear()

    @classmethod
    def get_instance_info(cls) -> Dict[str, Any]:
        """
        Get information about managed instances.

        Returns:
            Dictionary with instance information
        """
        return {
            "instance_count": len(cls._instances),
            "instance_types": [cls_type.__name__ for cls_type in cls._instances],
            "lock_count": len(cls._locks),
        }


class SingletonMixin:
    """
    Mixin class to add singleton behavior to any class.

    Usage:
        class MyService(SingletonMixin):
            def __init__(self):
                super().__init__()
                # Your initialization code
    """

    def __new__(cls, *args, **kwargs):
        """Override __new__ to implement singleton pattern."""
        return SingletonManager.get_instance(cls, *args, **kwargs)

    @classmethod
    def get_instance(cls, *args, **kwargs):
        """Get singleton instance."""
        return SingletonManager.get_instance(cls, *args, **kwargs)

    @classmethod
    def clear_instance(cls):
        """Clear singleton instance."""
        SingletonManager.clear_instance(cls)

    @classmethod
    def has_instance(cls) -> bool:
        """Check if instance exists."""
        return SingletonManager.has_instance(cls)


def singleton(cls: Type[T]) -> Type[T]:
    """
    Decorator to make a class a singleton.

    Usage:
        @singleton
        class MyService:
            def __init__(self):
                # Your initialization code
                pass
    """

    def new_new(cls_inner, *args, **kwargs):
        return SingletonManager.get_instance(cls_inner, *args, **kwargs)

    cls.__new__ = new_new

    # Add convenience methods
    cls.get_instance = classmethod(
        lambda cls_inner, *args, **kwargs: SingletonManager.get_instance(
            cls_inner, *args, **kwargs
        )
    )
    cls.clear_instance = classmethod(
        lambda cls_inner: SingletonManager.clear_instance(cls_inner)
    )
    cls.has_instance = classmethod(
        lambda cls_inner: SingletonManager.has_instance(cls_inner)
    )

    return cls


# Example usage patterns
if __name__ == "__main__":
    # Example 1: Using SingletonMixin
    class ConfigService(SingletonMixin):
        def __init__(self, config_path: str = "default.yaml"):
            self.config_path = config_path
            self.loaded = True

    # Example 2: Using @singleton decorator
    @singleton
    class LoggerService:
        def __init__(self, log_level: str = "INFO"):
            self.log_level = log_level
            self.initialized = True

    # Example 3: Using SingletonManager directly
    class DatabaseService:
        def __init__(self, connection_string: str):
            self.connection_string = connection_string
            self.connected = True

    # Test the patterns
    config1 = ConfigService("config1.yaml")
    config2 = ConfigService("config2.yaml")  # Same instance as config1
    assert config1 is config2
    assert config1.config_path == "config1.yaml"  # First initialization wins

    logger1 = LoggerService("DEBUG")
    logger2 = LoggerService("ERROR")  # Same instance as logger1
    assert logger1 is logger2
    assert logger1.log_level == "DEBUG"  # First initialization wins

    db1 = SingletonManager.get_instance(DatabaseService, "postgres://localhost")
    db2 = SingletonManager.get_instance(
        DatabaseService, "mysql://localhost"
    )  # Same instance
    assert db1 is db2
    assert db1.connection_string == "postgres://localhost"  # First initialization wins
