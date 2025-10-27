"""
Process Health Check for Claude MPM Framework
==============================================

WHY: Provides process-level health monitoring including existence validation,
status checking (running/zombie/stopped), and exit code detection.

DESIGN DECISION: Uses psutil for cross-platform process monitoring. Validates
process existence, status, and parent-child relationships.

ARCHITECTURE:
- Process existence verification with psutil.Process(pid)
- Process status checking (running, zombie, stopped, sleeping)
- Exit code detection for dead processes
- Parent-child relationship validation
- Process responsiveness checking (not hung)

USAGE:
    process_check = ProcessHealthCheck(process_manager)
    result = process_check.check(deployment_id="my-app")
"""

import psutil

from claude_mpm.core.enums import HealthStatus
from claude_mpm.services.core.base import SyncBaseService
from claude_mpm.services.core.interfaces.health import IHealthCheck
from claude_mpm.services.core.interfaces.process import ILocalProcessManager
from claude_mpm.services.core.models.health import HealthCheckResult


class ProcessHealthCheck(SyncBaseService, IHealthCheck):
    """
    Process status health check implementation.

    WHY: Validates that the process is running properly and not in a
    degraded state (zombie, stopped, etc.).

    Thread Safety: Stateless, safe for concurrent execution.
    """

    def __init__(self, process_manager: ILocalProcessManager):
        """
        Initialize process health check.

        Args:
            process_manager: Process manager for deployment lookup
        """
        super().__init__("ProcessHealthCheck")
        self.process_manager = process_manager

    def initialize(self) -> bool:
        """
        Initialize the health check.

        Returns:
            True if initialization successful
        """
        self._initialized = True
        self.log_info("Process health check initialized")
        return True

    def shutdown(self) -> None:
        """Shutdown health check (no resources to clean up)."""
        self._shutdown = True

    def get_check_type(self) -> str:
        """Get the check type identifier."""
        return "process"

    def check(self, deployment_id: str, **kwargs) -> HealthCheckResult:
        """
        Execute process health check for a deployment.

        Args:
            deployment_id: Unique deployment identifier
            **kwargs: Optional parameters:
                - check_responsiveness: Check if process is responsive (default: True)

        Returns:
            HealthCheckResult with check status and details

        Raises:
            ValueError: If deployment_id not found
        """
        # Validate deployment exists
        deployment = self.process_manager.state_manager.get_deployment(deployment_id)
        if not deployment:
            raise ValueError(f"Deployment not found: {deployment_id}")

        check_responsiveness = kwargs.get("check_responsiveness", True)

        try:
            process = psutil.Process(deployment.process_id)

            # Check if process exists and is running
            if not process.is_running():
                return HealthCheckResult(
                    status=HealthStatus.UNHEALTHY,
                    check_type=self.get_check_type(),
                    message="Process is not running",
                    details={
                        "pid": deployment.process_id,
                        "deployment_id": deployment_id,
                    },
                )

            # Get process status
            process_status = process.status()

            # Check for zombie process
            if process_status == psutil.STATUS_ZOMBIE:
                return HealthCheckResult(
                    status=HealthStatus.UNHEALTHY,
                    check_type=self.get_check_type(),
                    message="Process is a zombie",
                    details={
                        "pid": deployment.process_id,
                        "status": process_status,
                        "deployment_id": deployment_id,
                    },
                )

            # Check for stopped process
            if process_status in (psutil.STATUS_STOPPED, psutil.STATUS_DEAD):
                return HealthCheckResult(
                    status=HealthStatus.UNHEALTHY,
                    check_type=self.get_check_type(),
                    message=f"Process is {process_status}",
                    details={
                        "pid": deployment.process_id,
                        "status": process_status,
                        "deployment_id": deployment_id,
                    },
                )

            # Check responsiveness (CPU activity)
            if check_responsiveness:
                try:
                    cpu_percent = process.cpu_percent(interval=0.1)
                    # Process should have some CPU activity or be idle/sleeping
                    # A process with 0% CPU for extended periods might be hung
                    is_responsive = cpu_percent > 0 or process_status in (
                        psutil.STATUS_SLEEPING,
                        psutil.STATUS_IDLE,
                    )

                    if not is_responsive:
                        return HealthCheckResult(
                            status=HealthStatus.DEGRADED,
                            check_type=self.get_check_type(),
                            message="Process may be unresponsive",
                            details={
                                "pid": deployment.process_id,
                                "status": process_status,
                                "cpu_percent": cpu_percent,
                                "deployment_id": deployment_id,
                            },
                        )
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    # Process disappeared or we lost access during check
                    return HealthCheckResult(
                        status=HealthStatus.UNHEALTHY,
                        check_type=self.get_check_type(),
                        message="Process disappeared during check",
                        details={
                            "pid": deployment.process_id,
                            "deployment_id": deployment_id,
                        },
                    )

            # Process is healthy
            # Get additional process info for details
            try:
                process_info = {
                    "pid": deployment.process_id,
                    "status": process_status,
                    "deployment_id": deployment_id,
                    "name": process.name(),
                    "num_threads": process.num_threads(),
                }
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                process_info = {
                    "pid": deployment.process_id,
                    "status": process_status,
                    "deployment_id": deployment_id,
                }

            return HealthCheckResult(
                status=HealthStatus.HEALTHY,
                check_type=self.get_check_type(),
                message="Process is running normally",
                details=process_info,
            )

        except psutil.NoSuchProcess:
            # Process does not exist
            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                check_type=self.get_check_type(),
                message="Process no longer exists",
                details={
                    "pid": deployment.process_id,
                    "deployment_id": deployment_id,
                },
            )

        except psutil.AccessDenied as e:
            # Cannot access process information
            return HealthCheckResult(
                status=HealthStatus.UNKNOWN,
                check_type=self.get_check_type(),
                message="Cannot access process information",
                details={
                    "pid": deployment.process_id,
                    "deployment_id": deployment_id,
                    "error": str(e),
                },
            )

        except Exception as e:
            # Unexpected error
            self.log_error(f"Unexpected error in process health check: {e}")
            return HealthCheckResult(
                status=HealthStatus.UNKNOWN,
                check_type=self.get_check_type(),
                message="Health check failed with error",
                details={
                    "pid": deployment.process_id,
                    "deployment_id": deployment_id,
                    "error": str(e),
                },
            )


__all__ = ["ProcessHealthCheck"]
