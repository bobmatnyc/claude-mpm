"""
MCP Service Registry Implementation
====================================

Service registry for MCP Gateway components.
Provides service discovery, registration, and dependency resolution.

Part of ISS-0035: MCP Server Implementation - Core Server and Tool Registry
"""

import logging
from threading import RLock
from typing import Any, Dict, List, Optional, Type, TypeVar

from claude_mpm.services.mcp_gateway.core.interfaces import (
    IMCPCommunication,
    IMCPConfiguration,
    IMCPGateway,
    IMCPLifecycle,
    IMCPToolRegistry,
)
from claude_mpm.services.shared import ManagerBase

T = TypeVar("T")


class MCPServiceRegistry(ManagerBase):
    """
    Service registry for MCP Gateway components.

    WHY: We need a centralized registry for managing MCP services,
    enabling dependency injection and service discovery patterns.
    This aligns with the claude-mpm service-oriented architecture.

    DESIGN DECISIONS:
    - Use interface-based registration for loose coupling
    - Support singleton and transient service lifetimes
    - Provide thread-safe service resolution
    - Enable service health monitoring
    - Support service dependency chains
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the service registry."""
        super().__init__("mcp_service_registry", config=config)

        # Thread safety
        self._lock = RLock()

        # Service storage (in addition to base class _items)
        self._services: Dict[Type, Any] = {}
        self._singletons: Dict[Type, Any] = {}
        self._factories: Dict[Type, callable] = {}

        # Service metadata (note: base class has _item_metadata, this is for service-specific metadata)
        self._metadata: Dict[Type, Dict[str, Any]] = {}

        # Service health tracking
        self._health_checks: Dict[Type, callable] = {}

    def register(
        self,
        interface: Type[T],
        implementation: Optional[Type[T]] = None,
        factory: Optional[callable] = None,
        singleton: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Register a service in the registry.

        Args:
            interface: Service interface type
            implementation: Service implementation class
            factory: Factory function to create service instances
            singleton: Whether to create a single instance
            metadata: Additional service metadata

        WHY: We support both direct implementation and factory patterns
        to provide flexibility in service instantiation. Singleton support
        enables efficient resource management.
        """
        with self._lock:
            if implementation is None and factory is None:
                raise ValueError("Either implementation or factory must be provided")

            if implementation and factory:
                raise ValueError("Cannot provide both implementation and factory")

            self.logger.info(f"Registering service: {interface.__name__}")

            # Store service registration
            if implementation:
                self._services[interface] = implementation
            elif factory:
                self._factories[interface] = factory

            # Store metadata
            if metadata:
                self._metadata[interface] = metadata
            else:
                self._metadata[interface] = {"singleton": singleton}

            self._metadata[interface]["singleton"] = singleton

    def register_instance(self, interface: Type[T], instance: T) -> None:
        """
        Register a pre-created service instance.

        Args:
            interface: Service interface type
            instance: Service instance

        WHY: Sometimes we need to register pre-configured instances,
        especially for services with complex initialization.
        """
        with self._lock:
            self.logger.info(f"Registering instance: {interface.__name__}")
            self._singletons[interface] = instance
            self._metadata[interface] = {"singleton": True, "instance": True}

    def resolve(self, interface: Type[T]) -> Optional[T]:
        """
        Resolve a service from the registry.

        Args:
            interface: Service interface type

        Returns:
            Service instance or None if not found

        WHY: We use lazy instantiation for non-singleton services
        and cache singletons for performance.
        """
        with self._lock:
            # Check for existing singleton
            if interface in self._singletons:
                return self._singletons[interface]

            # Check for factory
            if interface in self._factories:
                factory = self._factories[interface]
                instance = factory()

                # Cache if singleton
                if self._metadata.get(interface, {}).get("singleton", False):
                    self._singletons[interface] = instance

                return instance

            # Check for implementation class
            if interface in self._services:
                implementation = self._services[interface]

                # Create instance
                try:
                    instance = implementation()

                    # Cache if singleton
                    if self._metadata.get(interface, {}).get("singleton", True):
                        self._singletons[interface] = instance

                    return instance

                except Exception as e:
                    self.logger.error(
                        f"Failed to create service {interface.__name__}: {e}"
                    )
                    return None

            self.logger.warning(f"Service not found: {interface.__name__}")
            return None

    def resolve_all(self, interface: Type[T]) -> List[T]:
        """
        Resolve all services implementing an interface.

        Args:
            interface: Service interface type

        Returns:
            List of service instances

        WHY: Some scenarios require multiple implementations of
        the same interface (e.g., multiple tool adapters).
        """
        with self._lock:
            instances = []

            # Add singleton if exists
            if interface in self._singletons:
                instances.append(self._singletons[interface])

            # Note: In a full implementation, we'd track multiple
            # registrations per interface

            return instances

    def unregister(self, interface: Type) -> bool:
        """
        Unregister a service from the registry.

        Args:
            interface: Service interface type

        Returns:
            True if unregistration successful
        """
        with self._lock:
            found = False

            if interface in self._services:
                del self._services[interface]
                found = True

            if interface in self._factories:
                del self._factories[interface]
                found = True

            if interface in self._singletons:
                # Shutdown if it's a lifecycle service
                instance = self._singletons[interface]
                if isinstance(instance, IMCPLifecycle):
                    try:
                        import asyncio

                        asyncio.create_task(instance.stop())
                    except Exception as e:
                        self.logger.warning(
                            f"Error stopping service {interface.__name__}: {e}"
                        )

                del self._singletons[interface]
                found = True

            if interface in self._metadata:
                del self._metadata[interface]

            if interface in self._health_checks:
                del self._health_checks[interface]

            if found:
                self.logger.info(f"Unregistered service: {interface.__name__}")

            return found

    def register_health_check(self, interface: Type, health_check: callable) -> None:
        """
        Register a health check for a service.

        Args:
            interface: Service interface type
            health_check: Health check function
        """
        with self._lock:
            self._health_checks[interface] = health_check

    async def check_health(self) -> Dict[str, Any]:
        """
        Check health of all registered services.

        Returns:
            Dictionary of service health statuses
        """
        health_status = {}

        with self._lock:
            # Check singleton services
            for interface, instance in self._singletons.items():
                service_name = interface.__name__

                try:
                    # Use custom health check if available
                    if interface in self._health_checks:
                        health_check = self._health_checks[interface]
                        if asyncio.iscoroutinefunction(health_check):
                            health = await health_check(instance)
                        else:
                            health = health_check(instance)
                        health_status[service_name] = health

                    # Use built-in health check for lifecycle services
                    elif isinstance(instance, IMCPLifecycle):
                        health_status[service_name] = {
                            "healthy": instance.is_healthy(),
                            "state": instance.get_state(),
                            "details": instance.get_health_status(),
                        }

                    # Basic health check
                    else:
                        health_status[service_name] = {
                            "healthy": True,
                            "state": "unknown",
                        }

                except Exception as e:
                    health_status[service_name] = {"healthy": False, "error": str(e)}

        return health_status

    def get_metadata(self, interface: Type) -> Optional[Dict[str, Any]]:
        """
        Get metadata for a service.

        Args:
            interface: Service interface type

        Returns:
            Service metadata or None
        """
        with self._lock:
            return self._metadata.get(interface)

    def list_services(self) -> List[str]:
        """
        List all registered services.

        Returns:
            List of service interface names
        """
        with self._lock:
            services = set()
            services.update(interface.__name__ for interface in self._services)
            services.update(interface.__name__ for interface in self._factories)
            services.update(interface.__name__ for interface in self._singletons)
            return sorted(services)

    def clear(self) -> None:
        """Clear all service registrations."""
        with self._lock:
            # Shutdown lifecycle services
            for instance in self._singletons.values():
                if isinstance(instance, IMCPLifecycle):
                    try:
                        import asyncio

                        asyncio.create_task(instance.stop())
                    except Exception as e:
                        self.logger.warning(f"Error stopping service: {e}")

            # Clear all registrations
            self._services.clear()
            self._factories.clear()
            self._singletons.clear()
            self._metadata.clear()
            self._health_checks.clear()

            self.logger.info("Service registry cleared")

    # Abstract methods required by ManagerBase
    def _do_initialize(self) -> bool:
        """Initialize the service registry."""
        self.logger.info("MCP Service Registry initialized")
        return True

    def _validate_item(self, item_id: str, item: Any) -> bool:
        """Validate a service before registration."""
        # For services, we validate that they implement the expected interface
        return item is not None

    def _do_scan_items(self) -> int:
        """Scan for available services."""
        # For service registry, we don't auto-scan - services are explicitly registered
        return len(self._services)


# Global service registry instance
_service_registry: Optional[MCPServiceRegistry] = None


def get_service_registry() -> MCPServiceRegistry:
    """
    Get the global MCP service registry instance.

    Returns:
        Service registry instance
    """
    global _service_registry
    if _service_registry is None:
        _service_registry = MCPServiceRegistry()
    return _service_registry


def register_mcp_services() -> None:
    """
    Register all default MCP services.

    This function sets up the standard MCP service configuration.
    """
    registry = get_service_registry()

    # Register core services
    # Use the official MCP gateway implementation
    from claude_mpm.services.mcp_gateway.server.mcp_gateway import MCPGateway

    registry.register(IMCPGateway, MCPGateway, singleton=True)

    from claude_mpm.services.mcp_gateway.config.configuration import MCPConfiguration
    from claude_mpm.services.mcp_gateway.registry.tool_registry import ToolRegistry
    from claude_mpm.services.mcp_gateway.server.stdio_handler import StdioHandler

    registry.register(IMCPCommunication, StdioHandler, singleton=True)
    registry.register(IMCPToolRegistry, ToolRegistry, singleton=True)
    registry.register(IMCPConfiguration, MCPConfiguration, singleton=True)

    logging.info("MCP services registered")


import asyncio
