"""Manages running Claude Code/MPM instances."""

import logging
from pathlib import Path
from typing import Optional

from claude_mpm.commander.adapters import (
    AdapterResponse,
    ClaudeCodeAdapter,
    ClaudeCodeCommunicationAdapter,
)
from claude_mpm.commander.frameworks.base import BaseFramework, InstanceInfo
from claude_mpm.commander.frameworks.claude_code import ClaudeCodeFramework
from claude_mpm.commander.frameworks.mpm import MPMFramework
from claude_mpm.commander.tmux_orchestrator import TmuxOrchestrator

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

        # Create instance info
        instance = InstanceInfo(
            name=name,
            project_path=project_path,
            framework=framework,
            tmux_session=self.orchestrator.session_name,
            pane_target=pane_target,
            git_branch=git_branch,
            git_status=git_status,
        )

        # Track instance
        self._instances[name] = instance

        # Create communication adapter for the instance (only for Claude Code for now)
        if framework == "cc":
            runtime_adapter = ClaudeCodeAdapter()
            comm_adapter = ClaudeCodeCommunicationAdapter(
                orchestrator=self.orchestrator,
                pane_target=pane_target,
                runtime_adapter=runtime_adapter,
            )
            self._adapters[name] = comm_adapter
            logger.debug(f"Created communication adapter for instance '{name}'")

        logger.info(
            f"Started instance '{name}' with framework '{framework}' at {project_path}"
        )

        return instance

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
