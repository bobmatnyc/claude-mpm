"""
Check monitoring and SocketIO server status.

WHY: Verify that the monitoring system and SocketIO server are
properly configured and accessible for real-time updates.
"""

import socket

from ....core.enums import OperationResult, ValidationSeverity
from ..models import DiagnosticResult
from .base_check import BaseDiagnosticCheck


class MonitorCheck(BaseDiagnosticCheck):
    """Check monitoring and SocketIO server."""

    @property
    def name(self) -> str:
        return "monitor_check"

    @property
    def category(self) -> str:
        return "Monitor"

    def run(self) -> DiagnosticResult:
        """Run monitor diagnostics."""
        try:
            sub_results = []
            details = {}

            # Check SocketIO availability
            socketio_result = self._check_socketio()
            sub_results.append(socketio_result)
            details["socketio_available"] = (
                socketio_result.status == OperationResult.SUCCESS
            )

            # Check port availability
            port_result = self._check_ports()
            sub_results.append(port_result)
            details["ports"] = port_result.details

            # Check response logging
            logging_result = self._check_response_logging()
            sub_results.append(logging_result)
            details["response_logging"] = logging_result.details.get("enabled", False)

            # Check hook service
            hook_result = self._check_hook_service()
            sub_results.append(hook_result)
            details["hooks_enabled"] = hook_result.status == OperationResult.SUCCESS

            # Determine overall status
            if any(r.status == ValidationSeverity.ERROR for r in sub_results):
                status = ValidationSeverity.ERROR
                message = "Monitoring has critical issues"
            elif any(r.status == ValidationSeverity.WARNING for r in sub_results):
                status = ValidationSeverity.WARNING
                message = "Monitoring has minor issues"
            else:
                status = OperationResult.SUCCESS
                message = "Monitoring properly configured"

            return DiagnosticResult(
                category=self.category,
                status=status,
                message=message,
                details=details,
                sub_results=sub_results if self.verbose else [],
            )

        except Exception as e:
            return DiagnosticResult(
                category=self.category,
                status=ValidationSeverity.ERROR,
                message=f"Monitor check failed: {e!s}",
                details={"error": str(e)},
            )

    def _check_socketio(self) -> DiagnosticResult:
        """Check if SocketIO is available."""
        try:
            import socketio

            return DiagnosticResult(
                category="SocketIO",
                status=OperationResult.SUCCESS,
                message="SocketIO library available",
                details={
                    "available": True,
                    "version": getattr(socketio, "__version__", "unknown"),
                },
            )
        except ImportError:
            return DiagnosticResult(
                category="SocketIO",
                status=ValidationSeverity.WARNING,
                message="SocketIO not installed",
                details={"available": False},
                fix_command="pip install python-socketio[asyncio]",
                fix_description="Install SocketIO for real-time monitoring",
            )

    def _check_ports(self) -> DiagnosticResult:
        """Check port availability for monitoring services."""
        try:
            from ....services.port_manager import PortManager

            PortManager()

            # Check default monitoring port range
            available_ports = []
            blocked_ports = []

            for port in range(8765, 8786):
                if self._is_port_available(port):
                    available_ports.append(port)
                else:
                    blocked_ports.append(port)

            if not available_ports:
                return DiagnosticResult(
                    category="Port Availability",
                    status=ValidationSeverity.ERROR,
                    message="No monitoring ports available (8765-8785)",
                    details={
                        "available": [],
                        "blocked": blocked_ports,
                        "checked_range": "8765-8785",
                    },
                    fix_description="Free up ports in the 8765-8785 range",
                )

            # Check if default port is available
            default_port = 8765
            if default_port not in available_ports:
                return DiagnosticResult(
                    category="Port Availability",
                    status=ValidationSeverity.WARNING,
                    message=f"Default port {default_port} in use, but alternatives available",
                    details={
                        "available": available_ports,
                        "blocked": blocked_ports,
                        "default_port": default_port,
                    },
                )

            return DiagnosticResult(
                category="Port Availability",
                status=OperationResult.SUCCESS,
                message=f"{len(available_ports)} monitoring port(s) available",
                details={
                    "available": available_ports,
                    "blocked": blocked_ports,
                    "default_port": default_port,
                },
            )

        except Exception as e:
            return DiagnosticResult(
                category="Port Availability",
                status=ValidationSeverity.WARNING,
                message=f"Could not check ports: {e!s}",
                details={"error": str(e)},
            )

    def _is_port_available(self, port: int) -> bool:
        """Check if a specific port is available."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.1)
        try:
            result = sock.connect_ex(("localhost", port))
            return result != 0
        finally:
            sock.close()

    def _check_response_logging(self) -> DiagnosticResult:
        """Check response logging configuration."""
        from pathlib import Path

        import yaml

        # Check user config
        config_paths = [
            Path.home() / ".claude" / "claude-mpm.yaml",
            Path.cwd() / ".claude" / "claude-mpm.yaml",
        ]

        response_logging_enabled = False
        log_path = None

        for config_path in config_paths:
            if config_path.exists():
                try:
                    with config_path.open() as f:
                        config = yaml.safe_load(f)
                        if config and isinstance(config, dict):
                            response_config = config.get("response_logging", {})
                            if response_config.get("enabled", False):
                                response_logging_enabled = True
                                log_path = response_config.get(
                                    "path", "~/.claude/responses"
                                )
                                break
                except Exception:
                    pass

        if not response_logging_enabled:
            return DiagnosticResult(
                category="Response Logging",
                status=OperationResult.SUCCESS,
                message="Response logging disabled (default)",
                details={"enabled": False},
            )

        # Check log directory
        log_dir = Path(log_path).expanduser()
        if not log_dir.exists():
            return DiagnosticResult(
                category="Response Logging",
                status=ValidationSeverity.WARNING,
                message="Response logging enabled but directory missing",
                details={"enabled": True, "path": str(log_dir), "exists": False},
                fix_command=f"mkdir -p {log_dir}",
                fix_description="Create response logging directory",
            )

        import os

        if not os.access(log_dir, os.W_OK):
            return DiagnosticResult(
                category="Response Logging",
                status=ValidationSeverity.WARNING,
                message="Response logging directory not writable",
                details={"enabled": True, "path": str(log_dir), "writable": False},
                fix_command=f"chmod 755 {log_dir}",
                fix_description="Fix permissions on logging directory",
            )

        return DiagnosticResult(
            category="Response Logging",
            status=OperationResult.SUCCESS,
            message="Response logging enabled and configured",
            details={
                "enabled": True,
                "path": str(log_dir),
                "exists": True,
                "writable": True,
            },
        )

    def _check_hook_service(self) -> DiagnosticResult:
        """Check hook service configuration."""
        try:
            from ....services.hook_service import HookService

            # Try to create hook service instance
            HookService()

            return DiagnosticResult(
                category="Hook Service",
                status=OperationResult.SUCCESS,
                message="Hook service available",
                details={"available": True},
            )

        except ImportError:
            return DiagnosticResult(
                category="Hook Service",
                status=ValidationSeverity.WARNING,
                message="Hook service not available",
                details={"available": False},
            )
        except Exception as e:
            return DiagnosticResult(
                category="Hook Service",
                status=ValidationSeverity.WARNING,
                message=f"Hook service error: {e!s}",
                details={"available": False, "error": str(e)},
            )
