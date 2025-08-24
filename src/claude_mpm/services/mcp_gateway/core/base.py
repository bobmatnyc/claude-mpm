"""
MCP Gateway Base Classes
========================

Base implementations for MCP Gateway services.

Part of ISS-0034: Infrastructure Setup - MCP Gateway Project Foundation
"""

import asyncio
from enum import Enum
from typing import Any, Dict, Optional

from claude_mpm.services.core.base import BaseService


class MCPServiceState(Enum):
    """MCP service lifecycle states."""

    UNINITIALIZED = "uninitialized"
    INITIALIZING = "initializing"
    INITIALIZED = "initialized"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


class BaseMCPService(BaseService):
    """
    Base class for all MCP Gateway services.

    Extends the claude-mpm BaseService with MCP-specific functionality
    including state management, health monitoring, and async lifecycle support.

    WHY: We extend BaseService to maintain consistency with the claude-mpm
    architecture while adding MCP-specific capabilities. This ensures all
    MCP services integrate seamlessly with the existing service container
    and dependency injection system.
    """

    def __init__(
        self,
        service_name: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize MCP service.

        Args:
            service_name: Name of the service for logging
            config: Service-specific configuration
        """
        super().__init__(service_name or "MCPService", config)
        self._state = MCPServiceState.UNINITIALIZED
        self._health_status = {
            "healthy": False,
            "state": self._state.value,
            "last_check": None,
            "details": {},
        }
        self._state_lock = asyncio.Lock()
        self._initialization_task = None
        self._shutdown_task = None

    async def initialize(self) -> bool:
        """
        Initialize the MCP service.

        This method manages state transitions and ensures thread-safe initialization.
        Subclasses should override _do_initialize() for custom initialization logic.

        Returns:
            True if initialization successful, False otherwise
        """
        async with self._state_lock:
            if self._state not in [
                MCPServiceState.UNINITIALIZED,
                MCPServiceState.STOPPED,
            ]:
                self.log_warning(f"Cannot initialize from state {self._state.value}")
                return False

            self._state = MCPServiceState.INITIALIZING
            self.log_info("Initializing MCP service")

        try:
            # Call subclass initialization
            success = await self._do_initialize()

            async with self._state_lock:
                if success:
                    self._state = MCPServiceState.INITIALIZED
                    self._initialized = True
                    self._health_status["healthy"] = True
                    self._health_status["state"] = self._state.value
                    self.log_info("MCP service initialized successfully")
                else:
                    self._state = MCPServiceState.ERROR
                    self._health_status["healthy"] = False
                    self._health_status["state"] = self._state.value
                    self.log_error("MCP service initialization failed")

                return success

        except Exception as e:
            async with self._state_lock:
                self._state = MCPServiceState.ERROR
                self._health_status["healthy"] = False
                self._health_status["state"] = self._state.value
                self._health_status["details"]["error"] = str(e)

            self.log_error(f"Exception during initialization: {e}")
            return False

    async def _do_initialize(self) -> bool:
        """
        Perform actual initialization logic.

        Subclasses should override this method to implement custom initialization.

        Returns:
            True if initialization successful
        """
        # Default implementation - subclasses should override
        return True

    async def start(self) -> bool:
        """
        Start the MCP service.

        Returns:
            True if startup successful
        """
        async with self._state_lock:
            if self._state != MCPServiceState.INITIALIZED:
                self.log_warning(f"Cannot start from state {self._state.value}")
                return False

            self._state = MCPServiceState.STARTING
            self.log_info("Starting MCP service")

        try:
            success = await self._do_start()

            async with self._state_lock:
                if success:
                    self._state = MCPServiceState.RUNNING
                    self._health_status["healthy"] = True
                    self._health_status["state"] = self._state.value
                    self.log_info("MCP service started successfully")
                else:
                    self._state = MCPServiceState.ERROR
                    self._health_status["healthy"] = False
                    self._health_status["state"] = self._state.value
                    self.log_error("MCP service startup failed")

                return success

        except Exception as e:
            async with self._state_lock:
                self._state = MCPServiceState.ERROR
                self._health_status["healthy"] = False
                self._health_status["state"] = self._state.value
                self._health_status["details"]["error"] = str(e)

            self.log_error(f"Exception during startup: {e}")
            return False

    async def _do_start(self) -> bool:
        """
        Perform actual startup logic.

        Subclasses should override this method to implement custom startup.

        Returns:
            True if startup successful
        """
        # Default implementation - subclasses should override
        return True

    async def shutdown(self) -> None:
        """
        Shutdown the MCP service gracefully.

        This method manages state transitions and ensures clean shutdown.
        Subclasses should override _do_shutdown() for custom shutdown logic.
        """
        async with self._state_lock:
            if self._state in [MCPServiceState.STOPPED, MCPServiceState.STOPPING]:
                self.log_warning(f"Already in state {self._state.value}")
                return

            self._state = MCPServiceState.STOPPING
            self.log_info("Shutting down MCP service")

        try:
            await self._do_shutdown()

            async with self._state_lock:
                self._state = MCPServiceState.STOPPED
                self._shutdown = True
                self._health_status["healthy"] = False
                self._health_status["state"] = self._state.value
                self.log_info("MCP service shutdown complete")

        except Exception as e:
            async with self._state_lock:
                self._state = MCPServiceState.ERROR
                self._health_status["healthy"] = False
                self._health_status["state"] = self._state.value
                self._health_status["details"]["error"] = str(e)

            self.log_error(f"Exception during shutdown: {e}")

    async def _do_shutdown(self) -> None:
        """
        Perform actual shutdown logic.

        Subclasses should override this method to implement custom shutdown.
        """
        # Default implementation - subclasses should override

    async def restart(self) -> bool:
        """
        Restart the MCP service.

        Returns:
            True if restart successful
        """
        self.log_info("Restarting MCP service")

        # Shutdown if running
        if self._state == MCPServiceState.RUNNING:
            await self.shutdown()

        # Re-initialize
        if not await self.initialize():
            return False

        # Start again
        return await self.start()

    def get_state(self) -> str:
        """
        Get current service state.

        Returns:
            Service state string
        """
        return self._state.value

    def is_healthy(self) -> bool:
        """
        Check if service is healthy.

        Returns:
            True if service is healthy
        """
        return self._health_status["healthy"]

    def get_health_status(self) -> Dict[str, Any]:
        """
        Get detailed health status.

        Returns:
            Health status information
        """
        return self._health_status.copy()

    def update_health_status(
        self, healthy: bool, details: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Update health status.

        Args:
            healthy: Whether service is healthy
            details: Additional health details
        """
        from datetime import datetime

        self._health_status["healthy"] = healthy
        self._health_status["last_check"] = datetime.now().isoformat()

        if details:
            self._health_status["details"].update(details)

    # Additional logging methods for MCP-specific events
    def log_mcp_event(
        self, event_type: str, data: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log an MCP-specific event.

        Args:
            event_type: Type of MCP event
            data: Event data
        """
        message = f"MCP Event: {event_type}"
        if data:
            message += f" - {data}"
        self.log_info(message)

    def log_tool_invocation(
        self, tool_name: str, success: bool, duration: Optional[float] = None
    ) -> None:
        """
        Log a tool invocation.

        Args:
            tool_name: Name of the tool invoked
            success: Whether invocation was successful
            duration: Execution duration in seconds
        """
        status = "successful" if success else "failed"
        message = f"Tool invocation: {tool_name} {status}"
        if duration:
            message += f" ({duration:.3f}s)"

        if success:
            self.log_info(message)
        else:
            self.log_warning(message)
