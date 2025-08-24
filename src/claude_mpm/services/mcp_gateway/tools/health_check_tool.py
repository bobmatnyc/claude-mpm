"""
Health Check Tool for MCP Gateway
=================================

Provides comprehensive health checking and diagnostic capabilities for the
MCP Gateway and claude-mpm system.

WHY: A dedicated health check tool provides centralized diagnostics for
troubleshooting and system monitoring, essential for maintaining a reliable
MCP gateway service.

DESIGN DECISIONS:
- Comprehensive system checks (gateway, tools, configuration)
- Structured output for easy parsing
- Non-blocking checks with timeouts
- Detailed error reporting for troubleshooting
"""

import asyncio
import os
import platform
import sys
from datetime import datetime
from typing import Any, Dict

import psutil

from claude_mpm.config.paths import paths
from claude_mpm.core.logger import get_logger
from claude_mpm.services.mcp_gateway.core.interfaces import (
    MCPToolDefinition,
    MCPToolInvocation,
    MCPToolResult,
)
from claude_mpm.services.mcp_gateway.tools.base_adapter import BaseToolAdapter


class HealthCheckTool(BaseToolAdapter):
    """
    Comprehensive health check tool for MCP Gateway diagnostics.

    Provides system health, gateway status, tool availability, and
    configuration validation checks.
    """

    def __init__(self):
        """Initialize the health check tool."""
        definition = MCPToolDefinition(
            name="health_check",
            description="Comprehensive health check and diagnostics for MCP Gateway and claude-mpm system",
            input_schema={
                "type": "object",
                "properties": {
                    "check_type": {
                        "type": "string",
                        "enum": ["all", "system", "gateway", "tools", "config"],
                        "description": "Type of health check to perform",
                        "default": "all",
                    },
                    "detailed": {
                        "type": "boolean",
                        "description": "Include detailed diagnostic information",
                        "default": False,
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Timeout for checks in seconds",
                        "default": 30,
                        "minimum": 5,
                        "maximum": 120,
                    },
                },
                "required": [],
            },
        )
        super().__init__(definition)
        self.logger = get_logger("HealthCheckTool")

    async def invoke(self, invocation: MCPToolInvocation) -> MCPToolResult:
        """
        Perform health checks based on the requested type.

        Args:
            invocation: Tool invocation request

        Returns:
            Tool execution result with health check results
        """
        start_time = datetime.now()

        try:
            # Get parameters
            check_type = invocation.parameters.get("check_type", "all")
            detailed = invocation.parameters.get("detailed", False)
            timeout = invocation.parameters.get("timeout", 30)

            # Perform health checks
            results = await self._perform_health_checks(check_type, detailed, timeout)

            # Calculate execution time
            execution_time = (datetime.now() - start_time).total_seconds()

            # Update metrics
            self._update_metrics(True, execution_time)

            return MCPToolResult(
                success=True,
                data=results,
                execution_time=execution_time,
                metadata={
                    "tool": "health_check",
                    "check_type": check_type,
                    "detailed": detailed,
                },
            )

        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            self._update_metrics(False, execution_time)

            return MCPToolResult(
                success=False,
                error=f"Health check failed: {e!s}",
                execution_time=execution_time,
                metadata={"tool": "health_check", "error": str(e)},
            )

    async def _perform_health_checks(
        self, check_type: str, detailed: bool, timeout: int
    ) -> Dict[str, Any]:
        """Perform the requested health checks."""
        results = {
            "timestamp": datetime.now().isoformat(),
            "check_type": check_type,
            "detailed": detailed,
            "overall_status": "unknown",
            "checks": {},
            "summary": {},
        }

        # Determine which checks to run
        checks_to_run = []
        if check_type == "all":
            checks_to_run = ["system", "gateway", "tools", "config"]
        else:
            checks_to_run = [check_type]

        # Run checks with timeout
        try:
            check_tasks = []
            for check in checks_to_run:
                if check == "system":
                    check_tasks.append(self._check_system_health(detailed))
                elif check == "gateway":
                    check_tasks.append(self._check_gateway_health(detailed))
                elif check == "tools":
                    check_tasks.append(self._check_tools_health(detailed))
                elif check == "config":
                    check_tasks.append(self._check_config_health(detailed))

            # Run all checks concurrently with timeout
            check_results = await asyncio.wait_for(
                asyncio.gather(*check_tasks, return_exceptions=True), timeout=timeout
            )

            # Process results
            for i, check_name in enumerate(checks_to_run):
                if i < len(check_results):
                    if isinstance(check_results[i], Exception):
                        results["checks"][check_name] = {
                            "status": "error",
                            "error": str(check_results[i]),
                        }
                    else:
                        results["checks"][check_name] = check_results[i]
                else:
                    results["checks"][check_name] = {
                        "status": "timeout",
                        "error": "Check timed out",
                    }

        except asyncio.TimeoutError:
            results["checks"]["timeout"] = {
                "status": "error",
                "error": f"Health checks timed out after {timeout} seconds",
            }

        # Calculate overall status and summary
        results["overall_status"] = self._calculate_overall_status(results["checks"])
        results["summary"] = self._generate_summary(results["checks"])

        return results

    async def _check_system_health(self, detailed: bool) -> Dict[str, Any]:
        """Check system health (CPU, memory, disk, etc.)."""
        check_result = {
            "status": "healthy",
            "checks": {},
            "warnings": [],
            "errors": [],
        }

        try:
            # Basic system info
            check_result["checks"]["platform"] = {
                "system": platform.system(),
                "release": platform.release(),
                "python_version": sys.version,
            }

            # Memory check
            memory = psutil.virtual_memory()
            memory_usage = memory.percent
            check_result["checks"]["memory"] = {
                "usage_percent": memory_usage,
                "available_gb": round(memory.available / (1024**3), 2),
                "total_gb": round(memory.total / (1024**3), 2),
            }

            if memory_usage > 90:
                check_result["errors"].append("High memory usage detected")
                check_result["status"] = "unhealthy"
            elif memory_usage > 80:
                check_result["warnings"].append("Elevated memory usage")

            # CPU check
            cpu_usage = psutil.cpu_percent(interval=1)
            check_result["checks"]["cpu"] = {
                "usage_percent": cpu_usage,
                "count": psutil.cpu_count(),
            }

            if cpu_usage > 95:
                check_result["errors"].append("High CPU usage detected")
                check_result["status"] = "unhealthy"
            elif cpu_usage > 80:
                check_result["warnings"].append("Elevated CPU usage")

            # Disk check for claude-mpm data directory
            if paths.data_dir.exists():
                disk_usage = psutil.disk_usage(str(paths.data_dir))
                disk_usage_percent = (disk_usage.used / disk_usage.total) * 100
                check_result["checks"]["disk"] = {
                    "usage_percent": round(disk_usage_percent, 2),
                    "free_gb": round(disk_usage.free / (1024**3), 2),
                    "total_gb": round(disk_usage.total / (1024**3), 2),
                }

                if disk_usage_percent > 95:
                    check_result["errors"].append("Disk space critically low")
                    check_result["status"] = "unhealthy"
                elif disk_usage_percent > 85:
                    check_result["warnings"].append("Disk space running low")

            # Process check
            current_process = psutil.Process()
            check_result["checks"]["process"] = {
                "pid": current_process.pid,
                "memory_mb": round(current_process.memory_info().rss / (1024**2), 2),
                "cpu_percent": current_process.cpu_percent(),
                "threads": current_process.num_threads(),
            }

        except Exception as e:
            check_result["status"] = "error"
            check_result["errors"].append(f"System health check failed: {e}")

        return check_result

    async def _check_gateway_health(self, detailed: bool) -> Dict[str, Any]:
        """Check MCP Gateway health."""
        check_result = {
            "status": "healthy",
            "checks": {},
            "warnings": [],
            "errors": [],
        }

        try:
            # Check singleton manager
            from ..core.singleton_manager import get_gateway_manager, is_gateway_running

            manager = get_gateway_manager()
            check_result["checks"]["singleton_manager"] = {
                "available": True,
                "gateway_running": is_gateway_running(),
            }

            # Check gateway instance info
            instance_info = manager.get_running_instance_info()
            if instance_info:
                check_result["checks"]["instance"] = instance_info
            else:
                check_result["warnings"].append("No gateway instance currently running")

            # Check MCP directories
            mcp_dir = paths.data_dir / "mcp"
            check_result["checks"]["directories"] = {
                "mcp_dir_exists": mcp_dir.exists(),
                "mcp_dir_writable": mcp_dir.exists() and os.access(mcp_dir, os.W_OK),
            }

            if not mcp_dir.exists():
                check_result["errors"].append("MCP directory does not exist")
                check_result["status"] = "unhealthy"

        except Exception as e:
            check_result["status"] = "error"
            check_result["errors"].append(f"Gateway health check failed: {e}")

        return check_result

    async def _check_tools_health(self, detailed: bool) -> Dict[str, Any]:
        """Check MCP tools health."""
        check_result = {
            "status": "healthy",
            "checks": {},
            "warnings": [],
            "errors": [],
        }

        try:
            # Try to import and check tool registry
            from ..registry.tool_registry import ToolRegistry

            registry = ToolRegistry()
            await registry.initialize()

            # Get tool list
            tools = registry.list_tools()
            check_result["checks"]["tool_count"] = len(tools)
            check_result["checks"]["tools"] = [tool.name for tool in tools]

            # Check essential tools
            essential_tools = ["echo", "calculator", "system_info"]
            available_essential = []
            missing_essential = []

            for tool_name in essential_tools:
                if registry.get_tool(tool_name):
                    available_essential.append(tool_name)
                else:
                    missing_essential.append(tool_name)

            check_result["checks"]["essential_tools"] = {
                "available": available_essential,
                "missing": missing_essential,
            }

            if missing_essential:
                check_result["warnings"].append(
                    f"Missing essential tools: {missing_essential}"
                )

            if len(available_essential) == 0:
                check_result["status"] = "unhealthy"
                check_result["errors"].append("No essential tools available")

        except Exception as e:
            check_result["status"] = "error"
            check_result["errors"].append(f"Tools health check failed: {e}")

        return check_result

    async def _check_config_health(self, detailed: bool) -> Dict[str, Any]:
        """Check configuration health."""
        check_result = {
            "status": "healthy",
            "checks": {},
            "warnings": [],
            "errors": [],
        }

        try:
            # Check configuration files
            config_dir = paths.data_dir / "mcp"
            config_file = config_dir / "gateway_config.json"

            check_result["checks"]["config_dir"] = config_dir.exists()
            check_result["checks"]["config_file"] = config_file.exists()

            if config_file.exists():
                # Try to load configuration
                import json

                with open(config_file) as f:
                    config_data = json.load(f)

                check_result["checks"]["config_valid"] = True
                if detailed:
                    check_result["checks"]["config_content"] = config_data
            else:
                check_result["warnings"].append("Gateway configuration file not found")

            # Check paths
            check_result["checks"]["paths"] = {
                "data_dir": str(paths.data_dir),
                "logs_dir": str(paths.logs_dir),
                "data_dir_exists": paths.data_dir.exists(),
                "logs_dir_exists": paths.logs_dir.exists(),
            }

        except Exception as e:
            check_result["status"] = "error"
            check_result["errors"].append(f"Config health check failed: {e}")

        return check_result

    def _calculate_overall_status(self, checks: Dict[str, Any]) -> str:
        """Calculate overall health status from individual checks."""
        if not checks:
            return "unknown"

        statuses = [check.get("status", "unknown") for check in checks.values()]

        if "error" in statuses:
            return "error"
        if "unhealthy" in statuses:
            return "unhealthy"
        if "warning" in statuses:
            return "warning"
        if all(status == "healthy" for status in statuses):
            return "healthy"
        return "unknown"

    def _generate_summary(self, checks: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a summary of health check results."""
        summary = {
            "total_checks": len(checks),
            "healthy": 0,
            "warnings": 0,
            "errors": 0,
            "issues": [],
        }

        for check_name, check_result in checks.items():
            status = check_result.get("status", "unknown")

            if status == "healthy":
                summary["healthy"] += 1
            elif status in ["warning", "unhealthy"]:
                summary["warnings"] += 1
                # Collect warning messages
                warnings = check_result.get("warnings", [])
                for warning in warnings:
                    summary["issues"].append(f"{check_name}: {warning}")
            elif status == "error":
                summary["errors"] += 1
                # Collect error messages
                errors = check_result.get("errors", [])
                for error in errors:
                    summary["issues"].append(f"{check_name}: {error}")

        return summary
