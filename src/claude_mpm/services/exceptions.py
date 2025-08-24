from pathlib import Path

"""Enhanced error classes for daemon conflict and process management in claude-mpm Socket.IO server.

These error classes provide detailed context and actionable guidance for users to resolve
common issues like daemon conflicts, port conflicts, stale processes, and recovery failures.

Design Principles:
1. Clear, actionable error messages with exact commands
2. Process details (PID, port, start time) for debugging
3. Resolution steps with specific troubleshooting guidance
4. Health status information when available
5. Structured error data for programmatic handling
"""

import platform
import time
from datetime import datetime
from typing import Any, Dict, List, Optional


class SocketIOServerError(Exception):
    """Base exception for Socket.IO server errors.

    Provides common functionality for all server-related errors including
    structured error data and detailed context information.
    """

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        """Initialize base server error.

        Args:
            message: Human-readable error message
            error_code: Machine-readable error code for programmatic handling
            context: Additional context data for debugging and resolution
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__.lower()
        self.context = context or {}
        self.timestamp = datetime.utcnow().isoformat() + "Z"

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary format for structured logging/handling."""
        return {
            "error_type": self.__class__.__name__,
            "error_code": self.error_code,
            "message": self.message,
            "context": self.context,
            "timestamp": self.timestamp,
        }


class DaemonConflictError(SocketIOServerError):
    """Error raised when attempting to start server while another instance is already running.

    This error provides detailed information about the conflicting process and
    actionable steps to resolve the conflict.
    """

    def __init__(
        self,
        port: int,
        existing_pid: int,
        existing_server_id: Optional[str] = None,
        process_info: Optional[Dict[str, Any]] = None,
        pidfile_path: Optional[Path] = None,
    ):
        """Initialize daemon conflict error with detailed context.

        Args:
            port: Port number where conflict occurred
            existing_pid: PID of the existing server process
            existing_server_id: Server ID of the existing instance (if available)
            process_info: Detailed process information from psutil or similar
            pidfile_path: Path to the PID file of the existing server
        """
        self.port = port
        self.existing_pid = existing_pid
        self.existing_server_id = existing_server_id or "unknown"
        self.process_info = process_info or {}
        self.pidfile_path = pidfile_path

        # Build detailed error message with resolution steps
        message = self._build_error_message()

        context = {
            "port": port,
            "existing_pid": existing_pid,
            "existing_server_id": self.existing_server_id,
            "process_info": process_info,
            "pidfile_path": str(pidfile_path) if pidfile_path else None,
            "resolution_steps": self._get_resolution_steps(),
        }

        super().__init__(message, "daemon_conflict", context)

    def _build_error_message(self) -> str:
        """Build comprehensive error message with process details."""
        lines = [
            f"🚫 Socket.IO server conflict detected on port {self.port}",
            "",
            "CONFLICT DETAILS:",
            f"  • Existing PID: {self.existing_pid}",
            f"  • Server ID: {self.existing_server_id}",
        ]

        # Add process information if available
        if self.process_info:
            status = self.process_info.get("status", "unknown")
            name = self.process_info.get("name", "unknown")
            create_time = self.process_info.get("create_time")
            memory_info = self.process_info.get("memory_info", {})

            lines.extend(
                [
                    f"  • Process Status: {status}",
                    f"  • Process Name: {name}",
                ]
            )

            if create_time:
                start_time = datetime.fromtimestamp(create_time).strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
                uptime = time.time() - create_time
                lines.append(f"  • Started: {start_time} (uptime: {uptime:.0f}s)")

            if memory_info.get("rss"):
                memory_mb = memory_info["rss"] / (1024 * 1024)
                lines.append(f"  • Memory Usage: {memory_mb:.1f} MB")

        # Add PID file information
        if self.pidfile_path:
            lines.extend(
                [
                    f"  • PID File: {self.pidfile_path}",
                    f"  • File Exists: {self.pidfile_path.exists() if isinstance(self.pidfile_path, Path) else 'unknown'}",
                ]
            )

        lines.extend(
            [
                "",
                "RESOLUTION STEPS:",
            ]
        )

        # Add resolution steps
        for i, step in enumerate(self._get_resolution_steps(), 1):
            lines.append(f"  {i}. {step}")

        return "\n".join(lines)

    def _get_resolution_steps(self) -> List[str]:
        """Get ordered list of resolution steps."""
        steps = [
            f"Check if the existing server is still needed: ps -p {self.existing_pid}",
            f"Stop the existing server gracefully: kill -TERM {self.existing_pid}",
            f"If graceful shutdown fails: kill -KILL {self.existing_pid}",
        ]

        if self.pidfile_path:
            steps.append(f"Remove stale PID file if needed: rm {self.pidfile_path}")

        steps.extend(
            [
                "Wait a few seconds for port cleanup",
                f"Try starting the server again on port {self.port}",
                "Alternative: Use a different port with --port <new_port>",
            ]
        )

        return steps


class PortConflictError(SocketIOServerError):
    """Error raised when network port is already in use by another process.

    This error helps identify what process is using the port and provides
    steps to resolve the conflict.
    """

    def __init__(
        self,
        port: int,
        host: str = "localhost",
        conflicting_process: Optional[Dict[str, Any]] = None,
    ):
        """Initialize port conflict error.

        Args:
            port: Port number that's in use
            host: Host address where the conflict occurred
            conflicting_process: Information about the process using the port
        """
        self.port = port
        self.host = host
        self.conflicting_process = conflicting_process or {}

        message = self._build_error_message()

        context = {
            "port": port,
            "host": host,
            "conflicting_process": conflicting_process,
            "resolution_steps": self._get_resolution_steps(),
        }

        super().__init__(message, "port_conflict", context)

    def _build_error_message(self) -> str:
        """Build error message with port conflict details."""
        lines = [
            "🔌 Network port conflict detected",
            "",
            "PORT CONFLICT DETAILS:",
            f"  • Port: {self.port}",
            f"  • Host: {self.host}",
            f"  • Address: {self.host}:{self.port}",
        ]

        # Add information about conflicting process if available
        if self.conflicting_process:
            pid = self.conflicting_process.get("pid")
            name = self.conflicting_process.get("name", "unknown")
            cmdline = self.conflicting_process.get("cmdline", [])

            lines.extend(
                [
                    "",
                    "CONFLICTING PROCESS:",
                    f"  • PID: {pid or 'unknown'}",
                    f"  • Name: {name}",
                ]
            )

            if cmdline:
                lines.append(f"  • Command: {' '.join(cmdline)}")

        lines.extend(
            [
                "",
                "RESOLUTION STEPS:",
            ]
        )

        for i, step in enumerate(self._get_resolution_steps(), 1):
            lines.append(f"  {i}. {step}")

        return "\n".join(lines)

    def _get_resolution_steps(self) -> List[str]:
        """Get resolution steps for port conflicts."""
        steps = [f"Check what process is using port {self.port}:"]

        # Add platform-specific commands
        if platform.system() == "Darwin":  # macOS
            steps.extend(
                [f"   • lsof -i :{self.port}", f"   • netstat -an | grep {self.port}"]
            )
        elif platform.system() == "Linux":
            steps.extend(
                [
                    f"   • lsof -i :{self.port}",
                    f"   • netstat -tulpn | grep {self.port}",
                    f"   • ss -tulpn | grep {self.port}",
                ]
            )
        elif platform.system() == "Windows":
            steps.extend(
                [
                    f"   • netstat -ano | findstr {self.port}",
                    '   • tasklist /fi "PID eq <PID_FROM_NETSTAT>"',
                ]
            )

        steps.extend(
            [
                "Stop the conflicting process if it's safe to do so",
                "Wait for port cleanup (may take 30-60 seconds)",
                "Try again with the same port",
                f"Alternative: Use a different port: --port {self.port + 1}",
            ]
        )

        return steps


class StaleProcessError(SocketIOServerError):
    """Error raised when dealing with stale processes or PID files.

    This error occurs when a PID file exists but the associated process
    is no longer running, is a zombie, or has been replaced.
    """

    def __init__(
        self,
        pid: int,
        pidfile_path: Optional[Path] = None,
        process_status: str = "not_found",
        validation_errors: Optional[List[str]] = None,
    ):
        """Initialize stale process error.

        Args:
            pid: Process ID that's stale
            pidfile_path: Path to the stale PID file
            process_status: Status of the process (zombie, not_found, invalid, etc.)
            validation_errors: List of validation errors encountered
        """
        self.pid = pid
        self.pidfile_path = pidfile_path
        self.process_status = process_status
        self.validation_errors = validation_errors or []

        message = self._build_error_message()

        context = {
            "pid": pid,
            "pidfile_path": str(pidfile_path) if pidfile_path else None,
            "process_status": process_status,
            "validation_errors": validation_errors,
            "resolution_steps": self._get_resolution_steps(),
        }

        super().__init__(message, "stale_process", context)

    def _build_error_message(self) -> str:
        """Build error message for stale process."""
        status_descriptions = {
            "not_found": "Process no longer exists",
            "zombie": "Process is a zombie (terminated but not reaped)",
            "invalid": "Process exists but is not the expected server",
            "access_denied": "Cannot access process information",
            "stale_pidfile": "PID file is stale or corrupted",
        }

        status_desc = status_descriptions.get(
            self.process_status, f"Process status: {self.process_status}"
        )

        lines = [
            "🧟 Stale process detected",
            "",
            "PROCESS DETAILS:",
            f"  • PID: {self.pid}",
            f"  • Status: {status_desc}",
        ]

        if self.pidfile_path:
            lines.extend(
                [
                    f"  • PID File: {self.pidfile_path}",
                    f"  • File Exists: {self.pidfile_path.exists() if isinstance(self.pidfile_path, Path) else 'unknown'}",
                ]
            )

        if self.validation_errors:
            lines.extend(
                [
                    "",
                    "VALIDATION ERRORS:",
                ]
            )
            for error in self.validation_errors:
                lines.append(f"  • {error}")

        lines.extend(
            [
                "",
                "RESOLUTION STEPS:",
            ]
        )

        for i, step in enumerate(self._get_resolution_steps(), 1):
            lines.append(f"  {i}. {step}")

        return "\n".join(lines)

    def _get_resolution_steps(self) -> List[str]:
        """Get resolution steps for stale processes."""
        steps = []

        if self.process_status == "zombie":
            steps.extend(
                [
                    "Wait for parent process to reap zombie (usually automatic)",
                    f"If zombie persists, check parent process: ps -o ppid= -p {self.pid}",
                    "Restart parent process if necessary",
                ]
            )
        elif self.process_status == "not_found":
            steps.extend([f"Process {self.pid} no longer exists - safe to clean up"])
        elif self.process_status == "invalid":
            steps.extend(
                [
                    f"Verify process {self.pid} is not a legitimate server:",
                    f"   • ps -p {self.pid} -o pid,ppid,cmd",
                    "If it's not your server, it's safe to clean up the PID file",
                ]
            )

        # Common cleanup steps
        if self.pidfile_path:
            steps.append(f"Remove stale PID file: rm {self.pidfile_path}")

        steps.extend(
            [
                "Try starting the server again",
                "If issues persist, check for permission problems or disk space",
            ]
        )

        return steps


class RecoveryFailedError(SocketIOServerError):
    """Error raised when automatic recovery mechanisms fail.

    This error occurs when the health monitoring and recovery system
    cannot automatically resolve server issues.
    """

    def __init__(
        self,
        recovery_action: str,
        failure_reason: str,
        attempt_count: int = 1,
        health_status: Optional[Dict[str, Any]] = None,
        last_successful_recovery: Optional[str] = None,
    ):
        """Initialize recovery failure error.

        Args:
            recovery_action: The recovery action that failed (e.g., 'restart', 'cleanup')
            failure_reason: Why the recovery failed
            attempt_count: Number of recovery attempts made
            health_status: Current health status information
            last_successful_recovery: Timestamp of last successful recovery
        """
        self.recovery_action = recovery_action
        self.failure_reason = failure_reason
        self.attempt_count = attempt_count
        self.health_status = health_status or {}
        self.last_successful_recovery = last_successful_recovery

        message = self._build_error_message()

        context = {
            "recovery_action": recovery_action,
            "failure_reason": failure_reason,
            "attempt_count": attempt_count,
            "health_status": health_status,
            "last_successful_recovery": last_successful_recovery,
            "resolution_steps": self._get_resolution_steps(),
        }

        super().__init__(message, "recovery_failed", context)

    def _build_error_message(self) -> str:
        """Build error message for recovery failure."""
        lines = [
            "🚨 Automatic recovery failed",
            "",
            "RECOVERY DETAILS:",
            f"  • Failed Action: {self.recovery_action}",
            f"  • Failure Reason: {self.failure_reason}",
            f"  • Attempt Count: {self.attempt_count}",
        ]

        if self.last_successful_recovery:
            lines.append(
                f"  • Last Successful Recovery: {self.last_successful_recovery}"
            )

        # Add health status information
        if self.health_status:
            lines.extend(
                [
                    "",
                    "CURRENT HEALTH STATUS:",
                ]
            )

            # Common health metrics
            for key, value in self.health_status.items():
                if key in [
                    "status",
                    "uptime",
                    "clients_connected",
                    "events_processed",
                    "errors",
                ]:
                    lines.append(f"  • {key.replace('_', ' ').title()}: {value}")

        lines.extend(
            [
                "",
                "MANUAL RESOLUTION REQUIRED:",
            ]
        )

        for i, step in enumerate(self._get_resolution_steps(), 1):
            lines.append(f"  {i}. {step}")

        return "\n".join(lines)

    def _get_resolution_steps(self) -> List[str]:
        """Get manual resolution steps for recovery failures."""
        steps = [
            "Check server logs for detailed error information",
            "Verify system resources (CPU, memory, disk space)",
            "Check network connectivity and port availability",
        ]

        if self.recovery_action == "restart":
            steps.extend(
                [
                    "Manually stop the server process",
                    "Wait for complete shutdown (check process list)",
                    "Remove any stale PID files",
                    "Restart the server manually",
                ]
            )
        elif self.recovery_action == "cleanup":
            steps.extend(
                [
                    "Manually identify and clean up stale resources",
                    "Check for zombie processes",
                    "Clear temporary files and logs if needed",
                ]
            )
        elif self.recovery_action == "port_reset":
            steps.extend(
                [
                    "Check what's using the required port",
                    "Stop conflicting processes",
                    "Wait for port cleanup",
                    "Consider using a different port temporarily",
                ]
            )

        steps.extend(
            [
                "Review health monitoring configuration",
                "Consider adjusting recovery thresholds if appropriate",
                "Monitor server stability after manual intervention",
            ]
        )

        return steps


class HealthCheckError(SocketIOServerError):
    """Error raised when health monitoring detects critical issues.

    This error provides detailed health status information and guidance
    for addressing system health problems.
    """

    def __init__(
        self,
        check_name: str,
        check_status: str,
        check_details: Optional[Dict[str, Any]] = None,
        threshold_exceeded: Optional[Dict[str, Any]] = None,
    ):
        """Initialize health check error.

        Args:
            check_name: Name of the failed health check
            check_status: Status of the health check (critical, warning, failed)
            check_details: Detailed results from the health check
            threshold_exceeded: Information about exceeded thresholds
        """
        self.check_name = check_name
        self.check_status = check_status
        self.check_details = check_details or {}
        self.threshold_exceeded = threshold_exceeded or {}

        message = self._build_error_message()

        context = {
            "check_name": check_name,
            "check_status": check_status,
            "check_details": check_details,
            "threshold_exceeded": threshold_exceeded,
            "resolution_steps": self._get_resolution_steps(),
        }

        super().__init__(message, "health_check_failed", context)

    def _build_error_message(self) -> str:
        """Build error message for health check failure."""
        status_emoji = {"critical": "🚨", "warning": "⚠️", "failed": "❌"}

        emoji = status_emoji.get(self.check_status, "🔍")

        lines = [
            f"{emoji} Health check failed: {self.check_name}",
            "",
            "CHECK DETAILS:",
            f"  • Check: {self.check_name}",
            f"  • Status: {self.check_status.upper()}",
        ]

        # Add check details
        if self.check_details:
            for key, value in self.check_details.items():
                if key not in ["raw_data", "internal_state"]:  # Skip internal data
                    lines.append(f"  • {key.replace('_', ' ').title()}: {value}")

        # Add threshold information
        if self.threshold_exceeded:
            lines.extend(
                [
                    "",
                    "THRESHOLDS EXCEEDED:",
                ]
            )
            for metric, info in self.threshold_exceeded.items():
                current = info.get("current", "unknown")
                threshold = info.get("threshold", "unknown")
                lines.append(
                    f"  • {metric.title()}: {current} (threshold: {threshold})"
                )

        lines.extend(
            [
                "",
                "RECOMMENDED ACTIONS:",
            ]
        )

        for i, step in enumerate(self._get_resolution_steps(), 1):
            lines.append(f"  {i}. {step}")

        return "\n".join(lines)

    def _get_resolution_steps(self) -> List[str]:
        """Get resolution steps based on health check type."""
        steps = []

        if "cpu" in self.check_name.lower():
            steps.extend(
                [
                    "Check for runaway processes consuming CPU",
                    "Consider adding rate limiting or request throttling",
                    "Monitor CPU usage patterns over time",
                ]
            )
        elif "memory" in self.check_name.lower():
            steps.extend(
                [
                    "Check for memory leaks in the application",
                    "Monitor memory usage trends",
                    "Consider restarting if memory usage is excessive",
                    "Review event history size limits",
                ]
            )
        elif (
            "network" in self.check_name.lower()
            or "connectivity" in self.check_name.lower()
        ):
            steps.extend(
                [
                    "Check network connectivity to required services",
                    "Verify firewall settings and port accessibility",
                    "Test network latency and bandwidth",
                ]
            )
        elif "disk" in self.check_name.lower() or "file" in self.check_name.lower():
            steps.extend(
                [
                    "Check available disk space",
                    "Clean up old log files and temporary data",
                    "Verify file permissions and access",
                ]
            )

        # General steps for all health check failures
        steps.extend(
            [
                "Review recent system changes or deployments",
                "Check system logs for related errors",
                "Consider adjusting health check thresholds if appropriate",
                "Monitor the issue to identify patterns or trends",
            ]
        )

        return steps


def format_troubleshooting_guide(error: SocketIOServerError) -> str:
    """Format a comprehensive troubleshooting guide for any Socket.IO server error.

    Args:
        error: The error instance to create troubleshooting guide for

    Returns:
        Formatted troubleshooting guide as a string
    """
    lines = [
        "═══════════════════════════════════════════════════════════════",
        "🔧 CLAUDE MPM SOCKET.IO SERVER TROUBLESHOOTING GUIDE",
        "═══════════════════════════════════════════════════════════════",
        "",
        f"ERROR TYPE: {error.__class__.__name__}",
        f"ERROR CODE: {error.error_code}",
        f"TIMESTAMP: {error.timestamp}",
        "",
        str(error),
        "",
        "ADDITIONAL TROUBLESHOOTING:",
        "",
        "🔍 DIAGNOSTIC COMMANDS:",
        "  • Check running processes: ps aux | grep socketio",
        f"  • Check port usage: lsof -i :{error.context.get('port', 'PORT')}",
        "  • Check system resources: top or htop",
        "  • Check disk space: df -h",
        "  • Check logs: tail -f /path/to/claude-mpm.log",
        "",
        "🛠️ COMMON SOLUTIONS:",
        "  1. Restart the Socket.IO server completely",
        "  2. Clear any stale PID files",
        "  3. Check for zombie processes and clean them up",
        "  4. Verify network port availability",
        "  5. Check system resource availability (CPU, memory, disk)",
        "  6. Review server configuration and permissions",
        "",
        "📞 GETTING HELP:",
        "  • Check the claude-mpm documentation",
        "  • Review server logs for additional context",
        "  • Report persistent issues with this error information",
        "",
        "🔗 ERROR CONTEXT DATA:",
    ]

    # Add structured context data
    for key, value in error.context.items():
        if key != "resolution_steps":  # Skip resolution steps as they're already shown
            lines.append(f"  • {key}: {value}")

    lines.extend(
        [
            "",
            "═══════════════════════════════════════════════════════════════",
        ]
    )

    return "\n".join(lines)
