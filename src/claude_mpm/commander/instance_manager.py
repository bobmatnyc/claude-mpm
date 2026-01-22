"""Manages running Claude Code/MPM instances."""

import asyncio
import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from claude_mpm.commander.adapters import (
    AdapterResponse,
    ClaudeCodeAdapter,
    ClaudeCodeCommunicationAdapter,
)
from claude_mpm.commander.frameworks.base import BaseFramework, InstanceInfo
from claude_mpm.commander.frameworks.claude_code import ClaudeCodeFramework
from claude_mpm.commander.frameworks.mpm import MPMFramework
from claude_mpm.commander.models.events import EventType
from claude_mpm.commander.tmux_orchestrator import TmuxOrchestrator

if TYPE_CHECKING:
    from claude_mpm.commander.events.manager import EventManager

logger = logging.getLogger(__name__)


class InstanceNotFoundError(Exception):
    """Raised when an instance is not found."""

    def __init__(self, name: str):
        super().__init__(f"Instance not found: {name}")
        self.name = name


class FrameworkNotFoundError(Exception):
    """Raised when a framework is not found or not available."""

    def __init__(self, framework: str):
        super().__init__(f"Framework not found or not available: {framework}")
        self.framework = framework


class InstanceAlreadyExistsError(Exception):
    """Raised when trying to start an instance that already exists."""

    def __init__(self, name: str):
        super().__init__(f"Instance already exists: {name}")
        self.name = name


class InstanceManager:
    """Manages lifecycle of Claude instances.

    The InstanceManager coordinates framework selection, instance startup,
    and tracking of running instances across the TmuxOrchestrator.

    Attributes:
        orchestrator: TmuxOrchestrator for managing tmux sessions/panes

    Example:
        >>> orchestrator = TmuxOrchestrator()
        >>> manager = InstanceManager(orchestrator)
        >>> frameworks = manager.list_frameworks()
        >>> print(frameworks)
        ['cc', 'mpm']
        >>> instance = await manager.start_instance(
        ...     "myapp",
        ...     Path("/Users/user/myapp"),
        ...     framework="cc"
        ... )
        >>> print(instance.name, instance.framework)
        myapp cc
    """

    def __init__(self, orchestrator: TmuxOrchestrator):
        """Initialize the instance manager.

        Args:
            orchestrator: TmuxOrchestrator for managing tmux sessions/panes
        """
        self.orchestrator = orchestrator
        self._instances: dict[str, InstanceInfo] = {}
        self._frameworks = self._load_frameworks()
        self._adapters: dict[str, ClaudeCodeCommunicationAdapter] = {}
        self._event_manager: Optional[EventManager] = None

    def set_event_manager(self, event_manager: "EventManager") -> None:
        """Set the event manager for emitting instance events.

        Args:
            event_manager: EventManager instance for event emission

        Example:
            >>> manager = InstanceManager(orchestrator)
            >>> manager.set_event_manager(event_manager)
        """
        self._event_manager = event_manager

    def _load_frameworks(self) -> dict[str, BaseFramework]:
        """Load available frameworks.

        Returns:
            Dict mapping framework name to framework instance

        Example:
            >>> manager = InstanceManager(orchestrator)
            >>> frameworks = manager._load_frameworks()
            >>> print(frameworks.keys())
            dict_keys(['cc', 'mpm'])
        """
        frameworks = {}
        for framework_class in [ClaudeCodeFramework, MPMFramework]:
            framework = framework_class()
            if framework.is_available():
                frameworks[framework.name] = framework
                logger.info(
                    f"Loaded framework: {framework.name} ({framework.display_name})"
                )
            else:
                logger.warning(
                    f"Framework not available: {framework.name} ({framework.display_name})"
                )

        return frameworks

    def list_frameworks(self) -> list[str]:
        """List available framework names.

        Returns:
            List of framework names (e.g., ["cc", "mpm"])

        Example:
            >>> manager = InstanceManager(orchestrator)
            >>> frameworks = manager.list_frameworks()
            >>> print(frameworks)
            ['cc', 'mpm']
        """
        return list(self._frameworks.keys())

    async def start_instance(
        self, name: str, project_path: Path, framework: str = "cc"
    ) -> InstanceInfo:
        """Start a new instance.

        Args:
            name: Instance name (e.g., "myapp")
            project_path: Path to project directory
            framework: Framework to use ("cc" or "mpm")

        Returns:
            InstanceInfo with tmux session details

        Raises:
            FrameworkNotFoundError: If framework is not available
            InstanceAlreadyExistsError: If instance already exists

        Example:
            >>> manager = InstanceManager(orchestrator)
            >>> instance = await manager.start_instance(
            ...     "myapp",
            ...     Path("/Users/user/myapp"),
            ...     framework="cc"
            ... )
            >>> print(instance.name, instance.framework)
            myapp cc
        """
        # Check if instance already exists
        if name in self._instances:
            raise InstanceAlreadyExistsError(name)

        # Get framework
        if framework not in self._frameworks:
            raise FrameworkNotFoundError(framework)

        framework_obj = self._frameworks[framework]

        # Get git info
        git_branch, git_status = framework_obj.get_git_info(project_path)

        # Ensure tmux session exists
        self.orchestrator.create_session()

        # Create pane
        pane_target = self.orchestrator.create_pane(name, str(project_path))

        # Start framework in pane
        startup_cmd = framework_obj.get_startup_command(project_path)
        self.orchestrator.send_keys(pane_target, startup_cmd)

        # Create communication adapter for the instance (only for Claude Code for now)
        # Do this BEFORE creating InstanceInfo so we can set connected=True
        has_adapter = False
        if framework == "cc":
            runtime_adapter = ClaudeCodeAdapter()
            comm_adapter = ClaudeCodeCommunicationAdapter(
                orchestrator=self.orchestrator,
                pane_target=pane_target,
                runtime_adapter=runtime_adapter,
            )
            self._adapters[name] = comm_adapter
            has_adapter = True
            logger.debug(f"Created communication adapter for instance '{name}'")

        # Create instance info
        instance = InstanceInfo(
            name=name,
            project_path=project_path,
            framework=framework,
            tmux_session=self.orchestrator.session_name,
            pane_target=pane_target,
            git_branch=git_branch,
            git_status=git_status,
            connected=has_adapter,
        )

        # Track instance
        self._instances[name] = instance

        logger.info(
            f"Started instance '{name}' with framework '{framework}' at {project_path}"
        )

        # Emit starting event and start background ready detection
        if self._event_manager:
            self._event_manager.create(
                project_id=name,
                event_type=EventType.INSTANCE_STARTING,
                title=f"Starting instance '{name}'",
                content=f"Instance {name} is starting at {project_path}",
                context={"instance_name": name, "working_dir": str(project_path)},
            )
            # Start background ready detection
            asyncio.create_task(self._detect_ready(name, instance))

        return instance

    async def _detect_ready(
        self, name: str, instance_info: InstanceInfo, timeout: int = 30
    ) -> None:
        """Background task to detect when instance is ready.

        Monitors the pane output for patterns indicating the instance
        is ready to accept commands.

        Args:
            name: Instance name
            instance_info: InstanceInfo with pane details
            timeout: Maximum seconds to wait for ready state

        Example:
            >>> # Called internally by start_instance
            >>> asyncio.create_task(self._detect_ready(name, instance))
        """
        ready_patterns = [
            r"^>\s*$",  # Prompt line (just >)
            r"What would you like",
            r"How can I help",
            r"Ready for input",
        ]

        start_time = asyncio.get_event_loop().time()
        while asyncio.get_event_loop().time() - start_time < timeout:
            await asyncio.sleep(1)
            try:
                # Get pane output using capture_output
                output = self.orchestrator.capture_output(
                    instance_info.pane_target, lines=50
                )
                if output:
                    for pattern in ready_patterns:
                        if re.search(pattern, output, re.MULTILINE):
                            # Emit ready event
                            if self._event_manager:
                                self._event_manager.create(
                                    project_id=name,
                                    event_type=EventType.INSTANCE_READY,
                                    title=f"Instance '{name}' ready",
                                    content=f"Instance {name} is ready for commands",
                                    context={"instance_name": name},
                                )
                            logger.info(f"Instance '{name}' is ready")
                            return
            except Exception as e:
                logger.debug(f"Error checking ready state for '{name}': {e}")

        # Timeout - emit ready event anyway since instance might still work
        if self._event_manager:
            self._event_manager.create(
                project_id=name,
                event_type=EventType.INSTANCE_READY,
                title=f"Instance '{name}' started",
                content=f"Instance {name} startup timeout, may be ready",
                context={"instance_name": name, "timeout": True},
            )
        logger.warning(f"Instance '{name}' ready detection timed out after {timeout}s")

    async def stop_instance(self, name: str) -> bool:
        """Stop an instance.

        Args:
            name: Instance name

        Returns:
            True if instance was stopped

        Raises:
            InstanceNotFoundError: If instance not found

        Example:
            >>> manager = InstanceManager(orchestrator)
            >>> await manager.stop_instance("myapp")
            True
        """
        if name not in self._instances:
            raise InstanceNotFoundError(name)

        instance = self._instances[name]

        # Kill tmux pane
        self.orchestrator.kill_pane(instance.pane_target)

        # Remove adapter if exists
        if name in self._adapters:
            del self._adapters[name]
            instance.connected = False
            logger.debug(f"Removed adapter for instance '{name}'")

        # Remove from tracking
        del self._instances[name]

        logger.info(f"Stopped instance '{name}'")

        return True

    def get_instance(self, name: str) -> Optional[InstanceInfo]:
        """Get instance by name.

        Args:
            name: Instance name

        Returns:
            InstanceInfo if found, None otherwise

        Example:
            >>> manager = InstanceManager(orchestrator)
            >>> instance = manager.get_instance("myapp")
            >>> if instance:
            ...     print(instance.name, instance.framework)
            myapp cc
        """
        return self._instances.get(name)

    def list_instances(self) -> list[InstanceInfo]:
        """List all running instances.

        Returns:
            List of InstanceInfo for all running instances

        Example:
            >>> manager = InstanceManager(orchestrator)
            >>> instances = manager.list_instances()
            >>> for instance in instances:
            ...     print(instance.name, instance.framework)
            myapp cc
            otherapp mpm
        """
        return list(self._instances.values())

    async def send_to_instance(
        self, name: str, message: str, wait_for_response: bool = False
    ) -> Optional[AdapterResponse]:
        """Send a message/command to an instance.

        Args:
            name: Instance name
            message: Message to send
            wait_for_response: If True, wait for and return response

        Returns:
            AdapterResponse if wait_for_response=True, None otherwise

        Raises:
            InstanceNotFoundError: If instance not found

        Example:
            >>> manager = InstanceManager(orchestrator)
            >>> # Send without waiting
            >>> await manager.send_to_instance("myapp", "Fix the bug in main.py")
            >>> # Send and wait for response
            >>> response = await manager.send_to_instance(
            ...     "myapp", "Fix the bug", wait_for_response=True
            ... )
            >>> print(response.content)
        """
        if name not in self._instances:
            raise InstanceNotFoundError(name)

        instance = self._instances[name]

        # Use adapter if available
        if name in self._adapters:
            adapter = self._adapters[name]
            await adapter.send(message)
            logger.info(
                f"Sent message via adapter to instance '{name}': {message[:50]}..."
            )

            if wait_for_response:
                return await adapter.receive()
            return None

        # Fallback to direct tmux if no adapter
        self.orchestrator.send_keys(instance.pane_target, message)
        logger.info(f"Sent message to instance '{name}': {message[:50]}...")
        return None

    def get_adapter(self, name: str) -> Optional[ClaudeCodeCommunicationAdapter]:
        """Get communication adapter for an instance.

        Args:
            name: Instance name

        Returns:
            ClaudeCodeCommunicationAdapter if exists, None otherwise

        Example:
            >>> manager = InstanceManager(orchestrator)
            >>> adapter = manager.get_adapter("myapp")
            >>> if adapter:
            ...     await adapter.send("Create a new file")
            ...     async for chunk in adapter.stream_response():
            ...         print(chunk, end='')
        """
        return self._adapters.get(name)

    async def rename_instance(self, old_name: str, new_name: str) -> bool:
        """Rename an instance.

        Args:
            old_name: Current instance name
            new_name: New instance name

        Returns:
            True if renamed successfully

        Raises:
            InstanceNotFoundError: If old_name doesn't exist
            InstanceAlreadyExistsError: If new_name already exists

        Example:
            >>> manager = InstanceManager(orchestrator)
            >>> await manager.rename_instance("myapp", "myapp-v2")
            True
        """
        # Validate old_name exists
        if old_name not in self._instances:
            raise InstanceNotFoundError(old_name)

        # Validate new_name doesn't exist
        if new_name in self._instances:
            raise InstanceAlreadyExistsError(new_name)

        # Get instance and update name
        instance = self._instances[old_name]
        instance.name = new_name

        # Update _instances dict (remove old key, add new)
        del self._instances[old_name]
        self._instances[new_name] = instance

        # Update _adapters dict if exists
        if old_name in self._adapters:
            adapter = self._adapters[old_name]
            del self._adapters[old_name]
            self._adapters[new_name] = adapter
            logger.debug(f"Moved adapter from '{old_name}' to '{new_name}'")

        logger.info(f"Renamed instance from '{old_name}' to '{new_name}'")

        return True

    async def close_instance(self, name: str) -> bool:
        """Close and remove an instance.

        Alias for stop_instance that provides clearer semantics for closing.

        Args:
            name: Instance name to close

        Returns:
            True if closed successfully

        Raises:
            InstanceNotFoundError: If instance not found

        Example:
            >>> manager = InstanceManager(orchestrator)
            >>> await manager.close_instance("myapp")
            True
        """
        return await self.stop_instance(name)

    async def disconnect_instance(self, name: str) -> bool:
        """Disconnect from an instance without closing it.

        The instance keeps running but we stop communication.
        Removes the adapter while keeping the instance tracked.

        Args:
            name: Instance name to disconnect from

        Returns:
            True if disconnected successfully

        Raises:
            InstanceNotFoundError: If instance not found

        Example:
            >>> manager = InstanceManager(orchestrator)
            >>> await manager.disconnect_instance("myapp")
            True
            >>> # Instance still running, but no adapter connection
            >>> adapter = manager.get_adapter("myapp")
            >>> print(adapter)
            None
        """
        # Validate instance exists
        if name not in self._instances:
            raise InstanceNotFoundError(name)

        instance = self._instances[name]

        # Remove adapter if exists (but keep instance)
        if name in self._adapters:
            # Could add cleanup here if adapter has resources to close
            del self._adapters[name]
            instance.connected = False
            logger.info(f"Disconnected from instance '{name}' (instance still running)")
        else:
            logger.debug(f"No adapter to disconnect for instance '{name}'")

        return True
