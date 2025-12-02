"""
Unified Local Operations Manager
=================================

WHY: Provides a single, coordinated entry point for all local process management
capabilities. Orchestrates process lifecycle, health monitoring, auto-restart,
stability detection, and resource monitoring into a cohesive service.

DESIGN DECISION: Aggregates all component managers (ProcessManager, HealthCheckManager,
RestartManager, MemoryLeakDetector, LogMonitor, ResourceMonitor) with configuration
loading from YAML. This simplifies integration for both CLI and agents.

ARCHITECTURE:
- Single service that initializes and coordinates all components
- Configuration-driven setup via .claude-mpm/local-ops-config.yaml
- Unified status aggregation across all monitoring dimensions
- Simplified API hiding internal complexity

USAGE:
    from claude_mpm.services.local_ops import UnifiedLocalOpsManager, StartConfig

    # Initialize with project root
    manager = UnifiedLocalOpsManager(
        project_root=Path("/path/to/project")
    )

    # Start a deployment with auto-restart
    config = StartConfig(
        command=["npm", "run", "dev"],
        working_directory="/path/to/project",
        port=3000,
        auto_find_port=True,
    )
    deployment = manager.start_deployment(config, auto_restart=True)

    # Get comprehensive status
    status = manager.get_full_status(deployment.deployment_id)

    # List all deployments
    deployments = manager.list_deployments()
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from claude_mpm.core.enums import ServiceState
from claude_mpm.services.core.base import SyncBaseService
from claude_mpm.services.core.models.health import DeploymentHealth
from claude_mpm.services.core.models.process import (
    DeploymentState,
    ProcessInfo,
    StartConfig,
)
from claude_mpm.services.core.models.restart import RestartConfig, RestartHistory

from .health_manager import HealthCheckManager
from .log_monitor import LogMonitor
from .memory_leak_detector import MemoryLeakDetector
from .process_manager import LocalProcessManager
from .resource_monitor import ResourceMonitor
from .restart_manager import RestartManager
from .state_manager import DeploymentStateManager


class UnifiedLocalOpsManager(SyncBaseService):
    """
    Unified manager that coordinates all local operations services.

    WHY: Provides a single entry point for process management that internally
    coordinates all the individual services. This simplifies usage for both
    CLI commands and agent integration.

    Components:
    - LocalProcessManager: Process lifecycle management
    - HealthCheckManager: Health monitoring
    - RestartManager: Auto-restart orchestration
    - MemoryLeakDetector: Memory leak detection
    - LogMonitor: Error pattern detection
    - ResourceMonitor: Resource exhaustion prevention
    """

    def __init__(
        self,
        project_root: Path,
        config_path: Optional[Path] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize unified local operations manager.

        Args:
            project_root: Root directory of the project
            config_path: Optional path to configuration file
            config: Optional configuration dict (overrides file)
        """
        super().__init__("UnifiedLocalOpsManager")

        self.project_root = project_root
        self.config_path = (
            config_path or project_root / ".claude-mpm" / "local-ops-config.yaml"
        )

        # Load configuration
        self.config = self._load_config(config)

        # Initialize component managers (lazy initialization)
        self._state_manager: Optional[DeploymentStateManager] = None
        self._process_manager: Optional[LocalProcessManager] = None
        self._health_manager: Optional[HealthCheckManager] = None
        self._restart_manager: Optional[RestartManager] = None
        self._memory_detector: Optional[MemoryLeakDetector] = None
        self._log_monitor: Optional[LogMonitor] = None
        self._resource_monitor: Optional[ResourceMonitor] = None

    def initialize(self) -> bool:
        """
        Initialize the unified manager and all components.

        Returns:
            True if initialization successful
        """
        try:
            # Ensure .claude-mpm directory exists
            claude_mpm_dir = self.project_root / ".claude-mpm"
            claude_mpm_dir.mkdir(exist_ok=True)

            # Initialize state manager
            state_file = claude_mpm_dir / "deployment-state.json"
            self._state_manager = DeploymentStateManager(state_file)
            if not self._state_manager.initialize():
                self.log_error("Failed to initialize state manager")
                return False

            # Initialize process manager
            self._process_manager = LocalProcessManager(self._state_manager)
            if not self._process_manager.initialize():
                self.log_error("Failed to initialize process manager")
                return False

            # Initialize health manager
            health_interval = self.config.get("defaults", {}).get(
                "health_check_interval_seconds", 30
            )
            self._health_manager = HealthCheckManager(
                self._process_manager, check_interval=health_interval
            )
            if not self._health_manager.initialize():
                self.log_error("Failed to initialize health manager")
                return False

            # Initialize restart manager
            restart_config = self._create_restart_config()
            self._restart_manager = RestartManager(
                self._process_manager, self._health_manager, restart_config
            )
            if not self._restart_manager.initialize():
                self.log_error("Failed to initialize restart manager")
                return False

            # Initialize stability monitors
            self._memory_detector = MemoryLeakDetector(
                threshold_mb_per_minute=self.config.get("stability", {}).get(
                    "memory_leak_threshold_mb_per_minute", 10.0
                )
            )
            if not self._memory_detector.initialize():
                self.log_error("Failed to initialize memory leak detector")
                return False

            # Initialize log monitor if enabled
            if self.config.get("log_monitoring", {}).get("enabled", True):
                self._log_monitor = LogMonitor(
                    error_patterns=self.config.get("log_monitoring", {}).get(
                        "error_patterns", []
                    )
                )
                if not self._log_monitor.initialize():
                    self.log_error("Failed to initialize log monitor")
                    return False

            # Initialize resource monitor
            stability_config = self.config.get("stability", {})
            self._resource_monitor = ResourceMonitor(
                fd_threshold_percent=stability_config.get("fd_threshold_percent", 0.8),
                thread_threshold=stability_config.get("thread_threshold", 1000),
                connection_threshold=stability_config.get("connection_threshold", 500),
                disk_threshold_mb=stability_config.get("disk_threshold_mb", 100),
            )
            if not self._resource_monitor.initialize():
                self.log_error("Failed to initialize resource monitor")
                return False

            self._initialized = True
            self.log_info(
                f"Unified local ops manager initialized for {self.project_root}"
            )
            return True

        except Exception as e:
            self.log_error(f"Failed to initialize: {e}")
            return False

    def shutdown(self) -> None:
        """Shutdown all component managers."""
        if self._health_manager:
            self._health_manager.shutdown()
        if self._restart_manager:
            self._restart_manager.shutdown()
        if self._memory_detector:
            self._memory_detector.shutdown()
        if self._log_monitor:
            self._log_monitor.shutdown()
        if self._resource_monitor:
            self._resource_monitor.shutdown()
        if self._process_manager:
            self._process_manager.shutdown()
        if self._state_manager:
            self._state_manager.shutdown()

        self._shutdown = True
        self.log_info("Unified local ops manager shutdown complete")

    def start_deployment(
        self,
        config: StartConfig,
        auto_restart: bool = False,
    ) -> DeploymentState:
        """
        Start a new local deployment with full orchestration.

        WHY: Single method that handles process spawning, health monitoring
        setup, and optional auto-restart enablement.

        Args:
            config: Configuration for the deployment
            auto_restart: If True, enable auto-restart for this deployment

        Returns:
            DeploymentState with deployment information

        Raises:
            ProcessSpawnError: If deployment fails to start
        """
        self._ensure_initialized()

        # Start the process
        deployment = self._process_manager.start(config)

        # Start health monitoring for this deployment
        self._health_manager.start_monitoring()

        # Enable auto-restart if requested
        if auto_restart or self.config.get("defaults", {}).get(
            "auto_restart_enabled", False
        ):
            restart_config = self._create_restart_config()
            success = self._restart_manager.enable_auto_restart(
                deployment.deployment_id, restart_config
            )
            if success:
                self.log_info(f"Auto-restart enabled for {deployment.deployment_id}")
            else:
                self.log_warning(
                    f"Failed to enable auto-restart for {deployment.deployment_id}"
                )

        return deployment

    def stop_deployment(
        self,
        deployment_id: str,
        timeout: int = 10,
        force: bool = False,
    ) -> bool:
        """
        Stop a deployment and clean up resources.

        Args:
            deployment_id: Unique deployment identifier
            timeout: Seconds to wait for graceful shutdown
            force: If True, kill immediately without waiting

        Returns:
            True if stopped successfully
        """
        self._ensure_initialized()

        # Disable auto-restart if enabled
        self._restart_manager.disable_auto_restart(deployment_id)

        # Stop the process
        return self._process_manager.stop(deployment_id, timeout=timeout, force=force)

    def restart_deployment(
        self,
        deployment_id: str,
        timeout: int = 10,
    ) -> DeploymentState:
        """
        Restart a deployment.

        Args:
            deployment_id: Unique deployment identifier
            timeout: Seconds to wait for graceful shutdown

        Returns:
            New DeploymentState after restart
        """
        self._ensure_initialized()
        return self._process_manager.restart(deployment_id, timeout=timeout)

    def get_deployment_status(self, deployment_id: str) -> Optional[ProcessInfo]:
        """
        Get current status of a deployment.

        Args:
            deployment_id: Unique deployment identifier

        Returns:
            ProcessInfo with current status, or None if not found
        """
        self._ensure_initialized()
        return self._process_manager.get_status(deployment_id)

    def get_health_status(self, deployment_id: str) -> Optional[DeploymentHealth]:
        """
        Get health status for a deployment.

        Args:
            deployment_id: Unique deployment identifier

        Returns:
            DeploymentHealth with current health, or None if not found
        """
        self._ensure_initialized()
        return self._health_manager.check_health(deployment_id)

    def get_restart_history(self, deployment_id: str) -> Optional[RestartHistory]:
        """
        Get restart history for a deployment.

        Args:
            deployment_id: Unique deployment identifier

        Returns:
            RestartHistory with restart information
        """
        self._ensure_initialized()
        return self._restart_manager.get_restart_history(deployment_id)

    def enable_auto_restart(
        self,
        deployment_id: str,
        config: Optional[RestartConfig] = None,
    ) -> bool:
        """
        Enable auto-restart for a deployment.

        Args:
            deployment_id: Unique deployment identifier
            config: Optional restart configuration

        Returns:
            True if enabled successfully
        """
        self._ensure_initialized()
        restart_config = config or self._create_restart_config()
        return self._restart_manager.enable_auto_restart(deployment_id, restart_config)

    def disable_auto_restart(self, deployment_id: str) -> bool:
        """
        Disable auto-restart for a deployment.

        Args:
            deployment_id: Unique deployment identifier

        Returns:
            True if disabled successfully
        """
        self._ensure_initialized()
        return self._restart_manager.disable_auto_restart(deployment_id)

    def list_deployments(
        self,
        status_filter: Optional[ServiceState] = None,
    ) -> List[DeploymentState]:
        """
        List all deployments.

        Args:
            status_filter: Optional status to filter by

        Returns:
            List of DeploymentState objects
        """
        self._ensure_initialized()

        if status_filter:
            return self._state_manager.get_deployments_by_status(status_filter)
        return self._state_manager.get_all_deployments()

    def get_full_status(self, deployment_id: str) -> Dict[str, Any]:
        """
        Get comprehensive status aggregating all monitoring dimensions.

        WHY: Provides a single view of process state, health, restart history,
        memory trends, and resource usage for complete visibility.

        Args:
            deployment_id: Unique deployment identifier

        Returns:
            Dictionary with all status information
        """
        self._ensure_initialized()

        status: Dict[str, Any] = {
            "deployment_id": deployment_id,
            "process": None,
            "health": None,
            "restart_history": None,
            "memory_trend": None,
            "log_matches": None,
            "resources": None,
        }

        # Get process status
        process_info = self.get_deployment_status(deployment_id)
        if process_info:
            status["process"] = {
                "status": process_info.status.value,
                "pid": process_info.process_id,
                "port": process_info.port,
                "uptime_seconds": process_info.uptime_seconds,
                "memory_mb": process_info.memory_mb,
                "cpu_percent": process_info.cpu_percent,
                "is_responding": process_info.is_responding,
                "error_message": process_info.error_message,
            }

        # Get health status
        health = self.get_health_status(deployment_id)
        if health:
            status["health"] = {
                "status": health.overall_status.value,
                "http_healthy": health.http_healthy,
                "process_healthy": health.process_healthy,
                "resource_healthy": health.resource_healthy,
                "last_check": (
                    health.last_check.isoformat() if health.last_check else None
                ),
                "failure_reason": health.failure_reason,
            }

        # Get restart history
        restart_history = self.get_restart_history(deployment_id)
        if restart_history:
            status["restart_history"] = {
                "total_restarts": restart_history.total_restarts,
                "successful_restarts": restart_history.successful_restarts,
                "failed_restarts": restart_history.failed_restarts,
                "circuit_breaker_state": restart_history.circuit_breaker_state.value,
                "auto_restart_enabled": restart_history.auto_restart_enabled,
                "recent_attempts": [
                    {
                        "timestamp": attempt.timestamp.isoformat(),
                        "success": attempt.success,
                        "reason": attempt.reason,
                        "error_message": attempt.error_message,
                    }
                    for attempt in restart_history.recent_attempts[-5:]  # Last 5
                ],
            }

        # Get memory trend if available
        if self._memory_detector and process_info and process_info.process_id:
            memory_trend = self._memory_detector.detect_leak(process_info.process_id)
            if memory_trend:
                status["memory_trend"] = memory_trend.value

        # Get log matches if log monitor enabled
        if self._log_monitor and process_info:
            deployment = self._state_manager.get_deployment(deployment_id)
            if deployment:
                log_file = Path(deployment.working_directory) / "app.log"
                if log_file.exists():
                    matches = self._log_monitor.check_for_errors(log_file)
                    if matches:
                        status["log_matches"] = [
                            {
                                "pattern": match.pattern,
                                "line": match.matched_line,
                                "line_number": match.line_number,
                                "timestamp": match.timestamp.isoformat(),
                            }
                            for match in matches[:5]  # Last 5
                        ]

        # Get resource status
        if self._resource_monitor and process_info and process_info.process_id:
            resources = self._resource_monitor.check_resources(process_info.process_id)
            if resources:
                status["resources"] = {
                    "file_descriptors": resources.file_descriptors,
                    "fd_limit": resources.fd_limit,
                    "thread_count": resources.thread_count,
                    "connection_count": resources.connection_count,
                    "disk_usage_mb": resources.disk_usage_mb,
                    "warnings": resources.warnings,
                }

        return status

    def _load_config(self, config_override: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Load configuration from file or use provided config.

        Args:
            config_override: Optional configuration dict that overrides file

        Returns:
            Configuration dictionary
        """
        # Use override if provided
        if config_override:
            return config_override

        # Load from file if it exists
        if self.config_path.exists():
            try:
                with self.config_path.open() as f:
                    return yaml.safe_load(f) or {}
            except Exception as e:
                self.log_warning(f"Failed to load config from {self.config_path}: {e}")

        # Return default configuration
        return {
            "version": "1.0",
            "defaults": {
                "health_check_interval_seconds": 30,
                "auto_restart_enabled": False,
            },
            "restart_policy": {
                "max_attempts": 5,
                "initial_backoff_seconds": 2.0,
                "max_backoff_seconds": 300.0,
                "backoff_multiplier": 2.0,
                "circuit_breaker_threshold": 3,
                "circuit_breaker_window_seconds": 300,
                "circuit_breaker_reset_seconds": 600,
            },
            "stability": {
                "memory_leak_threshold_mb_per_minute": 10.0,
                "fd_threshold_percent": 0.8,
                "thread_threshold": 1000,
                "connection_threshold": 500,
                "disk_threshold_mb": 100,
            },
            "log_monitoring": {
                "enabled": True,
                "error_patterns": [
                    "OutOfMemoryError",
                    "Segmentation fault",
                    "Exception:",
                    "Error:",
                    "FATAL",
                ],
            },
        }

    def _create_restart_config(self) -> RestartConfig:
        """Create RestartConfig from loaded configuration."""
        restart_policy = self.config.get("restart_policy", {})
        return RestartConfig(
            max_attempts=restart_policy.get("max_attempts", 5),
            initial_backoff_seconds=restart_policy.get("initial_backoff_seconds", 2.0),
            max_backoff_seconds=restart_policy.get("max_backoff_seconds", 300.0),
            backoff_multiplier=restart_policy.get("backoff_multiplier", 2.0),
            circuit_breaker_threshold=restart_policy.get(
                "circuit_breaker_threshold", 3
            ),
            circuit_breaker_window_seconds=restart_policy.get(
                "circuit_breaker_window_seconds", 300
            ),
            circuit_breaker_reset_seconds=restart_policy.get(
                "circuit_breaker_reset_seconds", 600
            ),
        )

    def _ensure_initialized(self) -> None:
        """Ensure manager is initialized."""
        if not self._initialized:
            raise RuntimeError(
                "UnifiedLocalOpsManager not initialized. Call initialize() first."
            )


__all__ = ["UnifiedLocalOpsManager"]
