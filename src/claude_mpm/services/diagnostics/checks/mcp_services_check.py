"""
Check MCP external services installation and health.

WHY: Verify that MCP services (mcp-vector-search, mcp-browser, mcp-ticketer, kuzu-memory)
are properly installed and accessible for enhanced Claude Code capabilities.
"""

import asyncio
import json
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from claude_mpm.core.logger import get_logger

from ....core.enums import OperationResult, ValidationSeverity
from ..models import DiagnosticResult
from .base_check import BaseDiagnosticCheck


class MCPServicesCheck(BaseDiagnosticCheck):
    """Check MCP external services installation and health."""

    def __init__(self, verbose: bool = False):
        """Initialize the MCP services check."""
        super().__init__(verbose)
        self.logger = get_logger(self.__class__.__name__)

    # Define MCP services to check
    MCP_SERVICES = {
        "mcp-vector-search": {
            "package": "mcp-vector-search",
            "command": [
                "mcp-vector-search",
                "--version",
            ],  # Use --version for proper check
            "description": "Vector search for semantic code navigation",
            "check_health": True,
            "health_command": ["mcp-vector-search", "--version"],
            "pipx_run_command": ["pipx", "run", "mcp-vector-search", "--version"],
            "mcp_command": [
                "python",
                "-m",
                "mcp_vector_search.mcp.server",
            ],  # Command to run as MCP server
            "pipx_mcp_command": [
                "pipx",
                "run",
                "--spec",
                "mcp-vector-search",
                "python",
                "-m",
                "mcp_vector_search.mcp.server",
            ],
        },
        "mcp-browser": {
            "package": "mcp-browser",
            "command": ["mcp-browser", "--version"],  # Use --version for proper check
            "description": "Browser automation and web interaction",
            "check_health": True,
            "health_command": ["mcp-browser", "--version"],
            "pipx_run_command": ["pipx", "run", "mcp-browser", "--version"],
            "mcp_command": ["mcp-browser", "mcp"],  # Command to run as MCP server
        },
        "mcp-ticketer": {
            "package": "mcp-ticketer",
            "command": ["mcp-ticketer", "--version"],  # Use --version for proper check
            "description": "Ticket and task management",
            "check_health": True,
            "health_command": ["mcp-ticketer", "--version"],
            "pipx_run_command": ["pipx", "run", "mcp-ticketer", "--version"],
            "mcp_command": ["mcp-ticketer", "mcp"],  # Command to run as MCP server
        },
        "kuzu-memory": {
            "package": "kuzu-memory",
            "command": ["kuzu-memory", "--version"],  # Use --version for proper check
            "description": "Graph-based memory system",
            "check_health": True,  # v1.1.0+ has version command
            "health_command": ["kuzu-memory", "--version"],
            "pipx_run_command": ["pipx", "run", "kuzu-memory", "--version"],
            "mcp_command": [
                "kuzu-memory",
                "mcp",
                "serve",
            ],  # v1.1.0+ uses 'mcp serve' args
        },
    }

    @property
    def name(self) -> str:
        return "mcp_services_check"

    @property
    def category(self) -> str:
        return "MCP Services"

    def run(self) -> DiagnosticResult:
        """Run MCP services diagnostics."""
        try:
            details = {}
            sub_results = []
            services_status = {}

            # Use MCPConfigManager to detect and fix corrupted installations
            from claude_mpm.services.mcp_config_manager import MCPConfigManager

            mcp_manager = MCPConfigManager()

            # Run comprehensive fix for all MCP service issues
            fix_success, fix_message = mcp_manager.fix_mcp_service_issues()
            if (
                fix_message
                and fix_message != "All MCP services are functioning correctly"
            ):
                # Create diagnostic result for the fixes
                fix_result = DiagnosticResult(
                    category="MCP Service Fixes",
                    status=(
                        OperationResult.SUCCESS
                        if fix_success
                        else ValidationSeverity.WARNING
                    ),
                    message=fix_message,
                    details={"auto_fix_applied": True},
                )
                sub_results.append(fix_result)

            # Check if MCP services are available (read-only check)
            available, availability_message = mcp_manager.check_mcp_services_available()
            if not available:
                # Services not configured - provide installation instructions
                config_result = DiagnosticResult(
                    category="MCP Service Availability",
                    status=ValidationSeverity.WARNING,
                    message=availability_message,
                    details={"auto_config_applied": True},
                )
                sub_results.append(config_result)

            # Check for kuzu-memory configuration issues and offer auto-fix
            kuzu_config_result = self._check_and_fix_kuzu_memory_config()
            if kuzu_config_result:
                sub_results.append(kuzu_config_result)

            # Check each MCP service
            for service_name, service_config in self.MCP_SERVICES.items():
                service_result = self._check_service(service_name, service_config)
                sub_results.append(service_result)

                # Extract connection test info if available
                connection_test = service_result.details.get("connection_test", {})

                services_status[service_name] = {
                    "status": service_result.status.value,
                    "installed": service_result.details.get("installed", False),
                    "accessible": service_result.details.get("accessible", False),
                    "version": service_result.details.get("version"),
                    "connection_tested": bool(connection_test),
                    "connected": connection_test.get("connected", False),
                    "response_time_ms": connection_test.get("response_time_ms"),
                    "tools_discovered": connection_test.get("tools_discovered", 0),
                    "connection_error": connection_test.get("error"),
                }

            # Check MCP gateway configuration for services
            gateway_result = self._check_gateway_configuration()
            sub_results.append(gateway_result)

            # Count service statuses
            installed_count = sum(1 for s in services_status.values() if s["installed"])
            accessible_count = sum(
                1 for s in services_status.values() if s["accessible"]
            )
            connected_count = sum(1 for s in services_status.values() if s["connected"])
            total_services = len(self.MCP_SERVICES)

            # Calculate total tools discovered
            total_tools = sum(
                s.get("tools_discovered", 0) for s in services_status.values()
            )

            details["services"] = services_status
            details["installed_count"] = installed_count
            details["accessible_count"] = accessible_count
            details["connected_count"] = connected_count
            details["total_services"] = total_services
            details["total_tools_discovered"] = total_tools
            details["gateway_configured"] = (
                gateway_result.status == OperationResult.SUCCESS
            )

            # Determine overall status
            errors = [r for r in sub_results if r.status == ValidationSeverity.ERROR]
            [r for r in sub_results if r.status == ValidationSeverity.WARNING]

            if errors:
                status = ValidationSeverity.ERROR
                message = f"Critical issues with {len(errors)} MCP service(s)"
            elif installed_count == 0:
                status = ValidationSeverity.WARNING
                message = "No MCP services installed"
            elif connected_count == total_services:
                status = OperationResult.SUCCESS
                message = f"All {total_services} MCP services connected ({total_tools} tools available)"
            elif connected_count > 0:
                status = ValidationSeverity.WARNING
                message = f"{connected_count}/{total_services} MCP services connected, {installed_count} installed"
            elif accessible_count < installed_count:
                status = ValidationSeverity.WARNING
                message = f"{installed_count}/{total_services} services installed, {accessible_count} accessible"
            elif installed_count < total_services:
                status = ValidationSeverity.WARNING
                message = f"{installed_count}/{total_services} MCP services installed"
            else:
                status = ValidationSeverity.WARNING
                message = f"All {total_services} MCP services installed but connections not tested"

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
                message=f"MCP services check failed: {e!s}",
                details={"error": str(e)},
            )

    async def _test_mcp_connection(self, service_name: str, command: List[str]) -> Dict:
        """Test MCP server connection by sending JSON-RPC requests."""
        result = {
            "connected": False,
            "response_time": None,
            "tools_count": 0,
            "tools": [],
            "error": None,
        }

        process = None
        try:
            # Start the MCP server process
            start_time = time.time()
            process = await asyncio.create_subprocess_exec(
                *command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            # Give the server a moment to initialize
            await asyncio.sleep(0.1)

            # Prepare initialize request
            init_request = {
                "jsonrpc": "2.0",
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "mpm-doctor", "version": "1.0.0"},
                },
                "id": 1,
            }

            # Send initialize request
            request_line = json.dumps(init_request) + "\n"
            process.stdin.write(request_line.encode())
            await process.stdin.drain()

            # Read response with timeout
            try:
                response_line = await asyncio.wait_for(
                    process.stdout.readline(), timeout=5.0
                )
                response_time = time.time() - start_time

                if response_line:
                    # Some MCP servers may output non-JSON before the actual response
                    # Try to find JSON in the response
                    response_text = response_line.decode().strip()

                    # Skip empty lines or non-JSON lines
                    while response_text and not response_text.startswith("{"):
                        # Try to read the next line
                        try:
                            response_line = await asyncio.wait_for(
                                process.stdout.readline(), timeout=1.0
                            )
                            if response_line:
                                response_text = response_line.decode().strip()
                            else:
                                break
                        except asyncio.TimeoutError:
                            break

                    if not response_text or not response_text.startswith("{"):
                        result["error"] = "No valid JSON response received"
                        return result

                    response = json.loads(response_text)

                    # Check for valid JSON-RPC response
                    if "result" in response and response.get("id") == 1:
                        result["connected"] = True
                        result["response_time"] = round(response_time * 1000, 2)  # ms

                        # Send tools/list request
                        tools_request = {
                            "jsonrpc": "2.0",
                            "method": "tools/list",
                            "params": {},
                            "id": 2,
                        }

                        request_line = json.dumps(tools_request) + "\n"
                        process.stdin.write(request_line.encode())
                        await process.stdin.drain()

                        # Read tools response
                        try:
                            tools_response_line = await asyncio.wait_for(
                                process.stdout.readline(), timeout=3.0
                            )

                            if tools_response_line:
                                tools_response = json.loads(
                                    tools_response_line.decode()
                                )
                                if "result" in tools_response:
                                    tools = tools_response["result"].get("tools", [])
                                    result["tools_count"] = len(tools)
                                    # Store first 5 tool names for display
                                    result["tools"] = [
                                        tool.get("name", "unknown")
                                        for tool in tools[:5]
                                    ]
                        except asyncio.TimeoutError:
                            # Connection successful but tools query timed out
                            pass
                        except (json.JSONDecodeError, KeyError):
                            # Connection successful but tools response invalid
                            pass

                    elif "error" in response:
                        result["error"] = (
                            f"MCP error: {response['error'].get('message', 'Unknown error')}"
                        )
                    else:
                        result["error"] = "Invalid JSON-RPC response format"

            except asyncio.TimeoutError:
                # Try to get any error output from stderr
                stderr_output = ""
                if process and process.stderr:
                    try:
                        stderr_data = await asyncio.wait_for(
                            process.stderr.read(1000), timeout=0.5
                        )
                        if stderr_data:
                            stderr_output = stderr_data.decode(
                                "utf-8", errors="ignore"
                            )[:200]
                    except (asyncio.TimeoutError, OSError):
                        pass

                if stderr_output:
                    result["error"] = (
                        f"Connection timeout (5s). Server output: {stderr_output}"
                    )
                else:
                    result["error"] = "Connection timeout (5s)"

            except json.JSONDecodeError as e:
                # Try to get stderr for more context
                stderr_output = ""
                if process and process.stderr:
                    try:
                        stderr_data = await asyncio.wait_for(
                            process.stderr.read(1000), timeout=0.5
                        )
                        if stderr_data:
                            stderr_output = stderr_data.decode(
                                "utf-8", errors="ignore"
                            )[:200]
                    except (asyncio.TimeoutError, OSError):
                        pass

                if stderr_output:
                    result["error"] = (
                        f"Invalid JSON response: {e!s}. Server error: {stderr_output}"
                    )
                else:
                    result["error"] = f"Invalid JSON response: {e!s}"

        except FileNotFoundError:
            result["error"] = f"Command not found: {command[0]}"
        except PermissionError:
            result["error"] = f"Permission denied: {command[0]}"
        except Exception as e:
            result["error"] = f"Connection failed: {e!s}"
        finally:
            # Clean up process
            if process:
                try:
                    process.terminate()
                    await asyncio.wait_for(process.wait(), timeout=2.0)
                except asyncio.TimeoutError:
                    process.kill()
                    await process.wait()
                except Exception:
                    pass

        return result

    def _check_service(self, service_name: str, config: Dict) -> DiagnosticResult:
        """Check a specific MCP service."""
        details = {"service": service_name}

        # Check if installed via pipx
        pipx_installed, pipx_path = self._check_pipx_installation(config["package"])
        details["pipx_installed"] = pipx_installed
        if pipx_path:
            details["pipx_path"] = pipx_path

        # Special check for mcp-ticketer: ensure gql dependency
        if service_name == "mcp-ticketer" and pipx_installed:
            gql_fixed = self._ensure_mcp_ticketer_gql_dependency()
            if gql_fixed:
                details["gql_dependency_fixed"] = True

        # Check if accessible in PATH
        accessible, command_path = self._check_command_accessible(config["command"])
        details["accessible"] = accessible
        if command_path:
            details["command_path"] = command_path

        # If not directly accessible, try pipx run command
        if (
            not accessible
            and "pipx_run_command" in config
            and self._verify_command_works(config["pipx_run_command"])
        ):
            accessible = True
            details["accessible_via_pipx_run"] = True
            details["pipx_run_available"] = True

        # Check for installation in various locations
        if not pipx_installed and not accessible:
            # Try common installation locations
            alt_installed, alt_path = self._check_alternative_installations(
                service_name
            )
            if alt_installed:
                details["alternative_installation"] = alt_path
                accessible = alt_installed

        details["installed"] = pipx_installed or accessible

        # Check service health/version if accessible
        if accessible and config.get("check_health"):
            # Try different version commands in order of preference
            version_commands = []
            if details.get("accessible_via_pipx_run") and "pipx_run_command" in config:
                version_commands.append(config["pipx_run_command"])
            if "health_command" in config:
                version_commands.append(config["health_command"])
            version_commands.append(config["command"])

            for cmd in version_commands:
                version = self._get_service_version(cmd)
                if version:
                    details["version"] = version
                    break

        # Test MCP connection if installed (accessible or pipx) and has mcp_command
        if (accessible or pipx_installed) and "mcp_command" in config:
            # Determine which command to use for MCP connection test
            mcp_command = None
            if pipx_installed and not accessible:
                # Service is installed via pipx but not in PATH
                if "pipx_mcp_command" in config:
                    # Use special pipx MCP command if available (e.g., for mcp-vector-search)
                    mcp_command = config["pipx_mcp_command"]
                else:
                    # Build pipx run command based on package
                    base_cmd = config["mcp_command"]
                    if len(base_cmd) > 0 and base_cmd[0] == config["package"]:
                        # Simple case where first command is the package name
                        mcp_command = ["pipx", "run", config["package"], *base_cmd[1:]]
                    else:
                        # Complex case - just try running the package with mcp arg
                        mcp_command = ["pipx", "run", config["package"], "mcp"]
            elif details.get("accessible_via_pipx_run"):
                # Use pipx run for the MCP command
                if "pipx_mcp_command" in config:
                    # Use special pipx MCP command if available (e.g., for mcp-vector-search)
                    mcp_command = config["pipx_mcp_command"]
                else:
                    # Build pipx run command
                    base_cmd = config["mcp_command"]
                    if service_name == "kuzu-memory":
                        # Special case for kuzu-memory with args
                        mcp_command = ["pipx", "run", base_cmd[0], *base_cmd[1:]]
                    else:
                        mcp_command = ["pipx", "run", *base_cmd]
            else:
                mcp_command = config["mcp_command"]

            if mcp_command:
                # Run async connection test
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    connection_result = loop.run_until_complete(
                        self._test_mcp_connection(service_name, mcp_command)
                    )
                    loop.close()

                    # Add connection test results to details
                    details["connection_test"] = {
                        "connected": connection_result["connected"],
                        "response_time_ms": connection_result["response_time"],
                        "tools_discovered": connection_result["tools_count"],
                        "tools_sample": connection_result["tools"],
                        "error": connection_result["error"],
                    }
                except Exception as e:
                    details["connection_test"] = {
                        "connected": False,
                        "error": f"Test failed: {e!s}",
                    }

        # Determine status
        if not (pipx_installed or accessible):
            return DiagnosticResult(
                category=f"MCP Service: {service_name}",
                status=ValidationSeverity.WARNING,
                message=f"Not installed: {config['description']}",
                details=details,
                fix_command=f"pipx install {config['package']}",
                fix_description=f"Install {service_name} for {config['description']}",
            )

        if pipx_installed and not accessible:
            # Check if pipx run works
            if details.get("pipx_run_available"):
                # Include connection test info if available
                connection_info = details.get("connection_test", {})
                if connection_info.get("connected"):
                    message = f"Installed via pipx, connection OK ({connection_info.get('tools_discovered', 0)} tools)"
                elif connection_info.get("error"):
                    message = f"Installed via pipx, connection failed: {connection_info['error']}"
                else:
                    message = "Installed via pipx (use 'pipx run' to execute)"

                return DiagnosticResult(
                    category=f"MCP Service: {service_name}",
                    status=(
                        OperationResult.SUCCESS
                        if connection_info.get("connected")
                        else ValidationSeverity.WARNING
                    ),
                    message=message,
                    details=details,
                )
            return DiagnosticResult(
                category=f"MCP Service: {service_name}",
                status=ValidationSeverity.WARNING,
                message="Installed via pipx but not in PATH",
                details=details,
                fix_command="pipx ensurepath",
                fix_description="Ensure pipx bin directory is in PATH",
            )

        # Service is accessible - check connection test results
        connection_info = details.get("connection_test", {})
        if connection_info:
            if connection_info.get("connected"):
                response_time = connection_info.get("response_time_ms")
                tools_count = connection_info.get("tools_discovered", 0)
                message = f"Installed, accessible, connection OK ({tools_count} tools, {response_time}ms)"
                status = OperationResult.SUCCESS
            else:
                error = connection_info.get("error", "Unknown error")
                message = f"Installed but connection failed: {error}"
                status = ValidationSeverity.WARNING
        else:
            message = "Installed and accessible"
            status = OperationResult.SUCCESS

        return DiagnosticResult(
            category=f"MCP Service: {service_name}",
            status=status,
            message=message,
            details=details,
        )

    def _check_pipx_installation(self, package_name: str) -> Tuple[bool, Optional[str]]:
        """Check if a package is installed via pipx."""
        try:
            result = subprocess.run(
                ["pipx", "list", "--json"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )

            if result.returncode == 0:
                try:
                    data = json.loads(result.stdout)
                    venvs = data.get("venvs", {})

                    if package_name in venvs:
                        venv_info = venvs[package_name]
                        # Get the main app path
                        apps = (
                            venv_info.get("metadata", {})
                            .get("main_package", {})
                            .get("apps", [])
                        )
                        if apps:
                            app_path = (
                                venv_info.get("metadata", {})
                                .get("main_package", {})
                                .get("app_paths", [])
                            )
                            if app_path:
                                return True, app_path[0]
                        return True, None
                except json.JSONDecodeError:
                    pass
        except (subprocess.SubprocessError, FileNotFoundError):
            pass

        return False, None

    def _check_command_accessible(
        self, command: List[str]
    ) -> Tuple[bool, Optional[str]]:
        """Check if a command is accessible in PATH."""
        try:
            # Use 'which' on Unix-like systems
            result = subprocess.run(
                ["which", command[0]],
                capture_output=True,
                text=True,
                timeout=2,
                check=False,
            )

            if result.returncode == 0:
                path = result.stdout.strip()
                # Verify the command actually works with --version
                if self._verify_command_works(command):
                    return True, path
                return False, path
        except (subprocess.SubprocessError, FileNotFoundError):
            pass

        # Try direct execution with --version
        if self._verify_command_works(command):
            return True, None

        return False, None

    def _verify_command_works(self, command: List[str]) -> bool:
        """Verify a command actually works by checking its --version output."""
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )

            # Check for successful execution or version output
            # Don't accept error messages containing "help" or "usage" as success
            if result.returncode == 0:
                # Look for actual version information
                output = (result.stdout + result.stderr).lower()
                # Check for version indicators
                if any(
                    keyword in output
                    for keyword in ["version", "v1.", "v0.", "1.", "0."]
                ) and not any(
                    error in output
                    for error in [
                        "error",
                        "not found",
                        "no such",
                        "command not found",
                    ]
                ):
                    return True

            # For some tools, non-zero return code is OK if version is shown
            elif "--version" in command or "--help" in command:
                output = (result.stdout + result.stderr).lower()
                # Must have version info and no error indicators
                if (
                    "version" in output or "v1." in output or "v0." in output
                ) and not any(
                    error in output
                    for error in [
                        "error",
                        "not found",
                        "no such",
                        "command not found",
                        "traceback",
                    ]
                ):
                    return True

        except (subprocess.SubprocessError, FileNotFoundError, OSError):
            pass

        return False

    def _check_alternative_installations(
        self, service_name: str
    ) -> Tuple[bool, Optional[str]]:
        """Check for alternative installation locations."""
        # Common installation paths
        paths_to_check = [
            Path.home() / ".local" / "bin" / service_name,
            Path("/usr/local/bin") / service_name,
            Path("/opt") / service_name / "bin" / service_name,
            Path.home() / ".npm" / "bin" / service_name,  # For npm-based services
            Path.home() / ".cargo" / "bin" / service_name,  # For Rust-based services
        ]

        for path in paths_to_check:
            if path.exists():
                return True, str(path)

        return False, None

    def _get_service_version(self, command: List[str]) -> Optional[str]:
        """Get version information for a service."""
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=2,
                check=False,
            )

            if result.returncode == 0:
                output = result.stdout.strip()
                # Try to extract version from output
                lines = output.split("\n")
                for line in lines:
                    if "version" in line.lower() or "v" in line.lower():
                        return line.strip()
                # Return first line if no version line found
                if lines:
                    return lines[0].strip()
        except (subprocess.SubprocessError, FileNotFoundError):
            pass

        return None

    def _check_and_fix_kuzu_memory_config(self) -> Optional[DiagnosticResult]:
        """Check for incorrect kuzu-memory configuration in .claude.json and offer auto-fix."""
        claude_config_path = Path.home() / ".claude.json"

        if not claude_config_path.exists():
            return None

        try:
            with claude_config_path.open() as f:
                config = json.load(f)

            mcp_servers = config.get("mcpServers", {})
            kuzu_config = mcp_servers.get("kuzu-memory")

            if not kuzu_config:
                return None

            # Check if kuzu-memory has incorrect args
            args = kuzu_config.get("args", [])
            needs_fix = False
            fix_reason = ""
            # The correct args for kuzu-memory v1.1.0+ are ["mcp", "serve"]
            correct_args = ["mcp", "serve"]

            # Check for any configuration that is NOT the correct one
            if args != correct_args:
                needs_fix = True
                # Identify the specific issue
                if args == ["claude", "mcp-server"]:
                    fix_reason = "Outdated 'claude mcp-server' format (pre-v1.1.0)"
                elif args == ["serve"]:
                    fix_reason = "Legacy 'serve' format"
                elif args == ["mcp-server"]:
                    fix_reason = "Incorrect 'mcp-server' format"
                elif args == []:
                    fix_reason = "Empty args list"
                else:
                    fix_reason = f"Incorrect args format: {args}"

            if needs_fix:
                # Log the issue for debugging
                self.logger.warning(
                    f"Found incorrect kuzu-memory configuration: {fix_reason}. "
                    f"Current args: {args}, should be: {correct_args}"
                )

                # Auto-fix the configuration
                fixed = self._fix_kuzu_memory_args(
                    claude_config_path, config, correct_args
                )

                if fixed:
                    return DiagnosticResult(
                        category="kuzu-memory Configuration Fix",
                        status=OperationResult.SUCCESS,
                        message="Fixed kuzu-memory configuration to use correct args",
                        details={
                            "old_args": args,
                            "new_args": correct_args,
                            "reason": fix_reason,
                            "auto_fixed": True,
                        },
                    )
                return DiagnosticResult(
                    category="kuzu-memory Configuration",
                    status=ValidationSeverity.WARNING,
                    message="kuzu-memory has incorrect configuration",
                    details={
                        "current_args": args,
                        "correct_args": correct_args,
                        "reason": fix_reason,
                        "auto_fix_failed": True,
                    },
                    fix_command="claude-mpm configure --mcp --fix-kuzu",
                    fix_description="Fix kuzu-memory configuration manually",
                )

            # Configuration is correct - args match ["mcp", "serve"]
            return None

        except (json.JSONDecodeError, Exception) as e:
            self.logger.debug(f"Could not check kuzu-memory config: {e}")
            return None

    def _fix_kuzu_memory_args(
        self, config_path: Path, config: Dict, new_args: List[str]
    ) -> bool:
        """Fix kuzu-memory args in the configuration."""
        try:
            # Save old args before updating
            old_args = config["mcpServers"]["kuzu-memory"].get("args", [])

            # Log the exact change we're about to make
            self.logger.debug(
                f"Fixing kuzu-memory args: old={old_args}, new={new_args}"
            )

            # Create backup
            backup_path = config_path.with_suffix(".json.backup")
            with backup_path.open("w") as f:
                json.dump(config, f, indent=2)

            # Update the configuration - ensure we're setting the exact new_args
            config["mcpServers"]["kuzu-memory"]["args"] = new_args

            # Verify the update in memory before writing
            if config["mcpServers"]["kuzu-memory"]["args"] != new_args:
                self.logger.error(
                    f"Failed to update args in memory! "
                    f"Expected {new_args}, got {config['mcpServers']['kuzu-memory']['args']}"
                )
                return False

            # Write updated configuration
            with config_path.open("w") as f:
                json.dump(config, f, indent=2)

            # Verify the file was written correctly
            with config_path.open() as f:
                verify_config = json.load(f)
                verify_args = (
                    verify_config.get("mcpServers", {})
                    .get("kuzu-memory", {})
                    .get("args", [])
                )

                if verify_args != new_args:
                    self.logger.error(
                        f"Configuration write verification failed! "
                        f"Expected {new_args}, got {verify_args}"
                    )
                    # Restore backup
                    with backup_path.open() as bf:
                        backup_config = json.load(bf)
                    with config_path.open("w") as f:
                        json.dump(backup_config, f, indent=2)
                    return False

            self.logger.info(
                f"✅ Fixed kuzu-memory configuration in {config_path}\n"
                f"   Changed args from {old_args} to {new_args}\n"
                f"   Backup saved to {backup_path}"
            )

            return True

        except Exception as e:
            self.logger.error(f"Failed to fix kuzu-memory configuration: {e}")
            return False

    def _check_gateway_configuration(self) -> DiagnosticResult:
        """Check if MCP services are configured in the gateway."""
        try:
            # Check Claude config file (the correct location for Claude Code)
            config_file = Path.home() / ".claude.json"

            if not config_file.exists():
                return DiagnosticResult(
                    category="MCP Gateway Configuration",
                    status=ValidationSeverity.WARNING,
                    message="Claude configuration file not found",
                    details={"config_path": str(config_file), "exists": False},
                    fix_command="claude-mpm configure --mcp",
                    fix_description="Initialize Claude configuration",
                )

            with config_file.open() as f:
                config = json.load(f)

            # Get the current project configuration
            from pathlib import Path

            current_project = str(Path.cwd())

            # Check if current project has MCP servers configured
            projects = config.get("projects", {})
            if current_project not in projects:
                return DiagnosticResult(
                    category="MCP Gateway Configuration",
                    status=ValidationSeverity.WARNING,
                    message="Current project not configured in Claude",
                    details={
                        "config_path": str(config_file),
                        "project": current_project,
                    },
                    fix_command="claude-mpm configure --mcp",
                    fix_description="Configure MCP services for current project",
                )

            project_config = projects[current_project]
            mcp_servers = project_config.get("mcpServers", {})

            configured_services = []
            missing_services = []

            for service_name in self.MCP_SERVICES:
                if service_name in mcp_servers:
                    configured_services.append(service_name)
                else:
                    missing_services.append(service_name)

            details = {
                "config_path": str(config_file),
                "configured_services": configured_services,
                "missing_services": missing_services,
            }

            if not configured_services:
                return DiagnosticResult(
                    category="MCP Gateway Configuration",
                    status=ValidationSeverity.WARNING,
                    message="No MCP services configured in gateway",
                    details=details,
                    fix_command="claude-mpm configure --mcp --add-services",
                    fix_description="Add MCP services to gateway configuration",
                )

            if missing_services:
                return DiagnosticResult(
                    category="MCP Gateway Configuration",
                    status=ValidationSeverity.WARNING,
                    message=f"{len(configured_services)} services configured, {len(missing_services)} missing",
                    details=details,
                )

            return DiagnosticResult(
                category="MCP Gateway Configuration",
                status=OperationResult.SUCCESS,
                message=f"All {len(configured_services)} services configured",
                details=details,
            )

        except json.JSONDecodeError as e:
            return DiagnosticResult(
                category="MCP Gateway Configuration",
                status=ValidationSeverity.ERROR,
                message="Invalid JSON in MCP configuration",
                details={"error": str(e)},
            )
        except Exception as e:
            return DiagnosticResult(
                category="MCP Gateway Configuration",
                status=ValidationSeverity.WARNING,
                message=f"Could not check configuration: {e!s}",
                details={"error": str(e)},
            )

    def _ensure_mcp_ticketer_gql_dependency(self) -> bool:
        """Ensure mcp-ticketer has the gql dependency injected."""
        try:
            # First check if mcp-ticketer can import gql
            result = subprocess.run(
                ["pipx", "run", "--spec", "mcp-ticketer", "python", "-c", "import gql"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )

            # If import fails, inject the dependency
            if result.returncode != 0:
                self.logger.info("🔧 mcp-ticketer missing gql dependency, fixing...")

                inject_result = subprocess.run(
                    ["pipx", "inject", "mcp-ticketer", "gql"],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    check=False,
                )

                if inject_result.returncode == 0:
                    self.logger.info(
                        "✅ Successfully injected gql dependency into mcp-ticketer"
                    )
                    return True
                self.logger.warning(
                    f"Failed to inject gql dependency: {inject_result.stderr}"
                )
                return False

            # Dependency already present
            return False

        except Exception as e:
            self.logger.debug(f"Could not check/fix mcp-ticketer gql dependency: {e}")
            return False
