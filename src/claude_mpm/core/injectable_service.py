"""
Injectable Service Base Class for Claude MPM.

Extends BaseService with enhanced dependency injection support,
making services easier to test and configure.
"""

from abc import ABC
from pathlib import Path
from typing import Any, Dict, Optional, Type, TypeVar, Union

from .base_service import BaseService
from .container import DIContainer
from .logger import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


class InjectableService(BaseService, ABC):
    """
    Enhanced base service with full dependency injection support.

    Features:
    - Automatic dependency resolution from container
    - Property injection support
    - Service locator pattern (optional)
    - Easy testing with mock dependencies
    """

    def __init__(
        self,
        name: str,
        config: Optional[Dict[str, Any]] = None,
        config_path: Optional[Path] = None,
        enable_enhanced_features: bool = True,
        container: Optional[DIContainer] = None,
        **injected_deps,
    ):
        """
        Initialize injectable service.

        Args:
            name: Service name
            config: Configuration dictionary
            config_path: Path to configuration file
            enable_enhanced_features: Enable enhanced features
            container: DI container for dependency resolution
            **injected_deps: Explicitly injected dependencies
        """
        # Store container before calling parent init
        self._di_container = container
        self._injected_deps = injected_deps

        super().__init__(
            name=name,
            config=config,
            config_path=config_path,
            enable_enhanced_features=enable_enhanced_features,
            container=container,
        )

        # Inject dependencies after base initialization
        self._inject_dependencies()

    def _inject_dependencies(self) -> None:
        """Inject dependencies based on class annotations."""
        # Get class annotations for dependency injection
        annotations = getattr(self.__class__, "__annotations__", {})

        for attr_name, attr_type in annotations.items():
            # Skip if already set or is a private attribute
            if hasattr(self, attr_name) or attr_name.startswith("_"):
                continue

            # Check if explicitly injected
            if attr_name in self._injected_deps:
                setattr(self, attr_name, self._injected_deps[attr_name])
                logger.debug(f"Injected {attr_name} from explicit dependencies")
                continue

            # Try to resolve from container
            if self._di_container:
                try:
                    # Handle Optional types
                    if hasattr(attr_type, "__origin__"):
                        if attr_type.__origin__ is Union:
                            # Get the non-None type from Optional
                            args = attr_type.__args__
                            actual_type = next(
                                (arg for arg in args if arg is not type(None)), None
                            )
                            if actual_type:
                                service = self._di_container.resolve_optional(
                                    actual_type
                                )
                                if service:
                                    setattr(self, attr_name, service)
                                    logger.debug(
                                        f"Injected optional {attr_name} from container"
                                    )
                    else:
                        # Direct type resolution
                        service = self._di_container.resolve(attr_type)
                        setattr(self, attr_name, service)
                        logger.debug(f"Injected {attr_name} from container")
                except Exception as e:
                    logger.warning(f"Could not inject {attr_name}: {e}")

    def get_dependency(self, service_type: Type[T]) -> T:
        """
        Get a dependency from the container.

        Service locator pattern - use sparingly, prefer constructor injection.

        Args:
            service_type: Type to resolve

        Returns:
            Resolved service instance
        """
        if not self._di_container:
            raise RuntimeError("No DI container available")

        return self._di_container.resolve(service_type)

    def get_optional_dependency(
        self, service_type: Type[T], default: Optional[T] = None
    ) -> Optional[T]:
        """
        Get an optional dependency from the container.

        Args:
            service_type: Type to resolve
            default: Default value if not found

        Returns:
            Resolved service or default
        """
        if not self._di_container:
            return default

        return self._di_container.resolve_optional(service_type, default)

    def has_dependency(self, service_type: Type) -> bool:
        """Check if a dependency is available in the container."""
        if not self._di_container:
            return False

        return self._di_container.is_registered(service_type)

    def with_dependencies(self, **deps) -> "InjectableService":
        """
        Create a new instance with specific dependencies.

        Useful for testing with mocks.

        Args:
            **deps: Dependencies to inject

        Returns:
            New service instance with injected dependencies
        """
        # Merge with existing config
        config = self.config._config if hasattr(self.config, "_config") else {}

        # Create new instance with dependencies
        return self.__class__(
            name=self.name,
            config=config,
            enable_enhanced_features=self._enable_enhanced,
            container=self._di_container,
            **deps,
        )

    async def _initialize_dependencies(self) -> None:
        """Initialize injected dependencies that need async setup."""
        # Initialize any dependencies that need async initialization
        for attr_name in dir(self):
            if attr_name.startswith("_"):
                continue

            attr = getattr(self, attr_name, None)
            if (
                attr
                and hasattr(attr, "start")
                and hasattr(attr, "running")
                and not attr.running
            ):
                try:
                    await attr.start()
                    logger.debug(f"Started dependency {attr_name}")
                except Exception as e:
                    logger.warning(f"Failed to start dependency {attr_name}: {e}")

    def __repr__(self) -> str:
        """Enhanced string representation showing dependencies."""
        base_repr = super().__repr__()

        # Add dependency information
        deps = []
        annotations = getattr(self.__class__, "__annotations__", {})

        for attr_name, _attr_type in annotations.items():
            if hasattr(self, attr_name) and not attr_name.startswith("_"):
                deps.append(
                    f"{attr_name}={getattr(self, attr_name).__class__.__name__}"
                )

        if deps:
            deps_str = ", ".join(deps)
            return base_repr.replace(")>", f", deps=[{deps_str}])>")

        return base_repr
