"""
Agent Dependency Service
========================

WHY: This service manages all agent dependency operations including checking,
installing, listing, and fixing dependencies with robust retry logic. It provides
a clean interface for the CLI to manage agent dependencies without embedding
complex logic in the command module.

DESIGN DECISIONS:
- Uses AgentDependencyLoader for dependency discovery and analysis
- Integrates RobustPackageInstaller for reliable package installation
- Provides retry logic for network operations to handle transient failures
- Generates detailed dependency reports for user feedback
- Maintains separation between dependency logic and CLI presentation
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple

from ...core.logger import get_logger
from ...utils.agent_dependency_loader import AgentDependencyLoader
from ...utils.robust_installer import RobustPackageInstaller


class IAgentDependencyService(ABC):
    """Interface for agent dependency management operations."""

    @abstractmethod
    def check_dependencies(self, agent_name: Optional[str] = None) -> Dict[str, Any]:
        """Check dependencies for deployed agents."""

    @abstractmethod
    def install_dependencies(
        self, agent_name: Optional[str] = None, dry_run: bool = False
    ) -> Dict[str, Any]:
        """Install missing dependencies for agents."""

    @abstractmethod
    def list_dependencies(self, format_type: str = "text") -> Dict[str, Any]:
        """List all dependencies from deployed agents."""

    @abstractmethod
    def fix_dependencies(
        self, max_retries: int = 3, agent_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Auto-fix dependency issues with retry logic."""

    @abstractmethod
    def validate_compatibility(
        self, packages: List[str]
    ) -> Tuple[List[str], List[str]]:
        """Check version compatibility for packages."""

    @abstractmethod
    def get_dependency_report(self) -> str:
        """Generate a formatted dependency report."""


class AgentDependencyService(IAgentDependencyService):
    """Service for managing agent dependencies with robust error handling."""

    def __init__(self):
        """Initialize the dependency service."""
        self.logger = get_logger(__name__)
        self.loader = None  # Lazy initialization

    def _get_loader(self, auto_install: bool = False) -> AgentDependencyLoader:
        """Get or create dependency loader instance."""
        if self.loader is None or self.loader.auto_install != auto_install:
            self.loader = AgentDependencyLoader(auto_install=auto_install)
        return self.loader

    def check_dependencies(self, agent_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Check dependencies for deployed agents.

        Args:
            agent_name: Optional specific agent to check

        Returns:
            Dictionary containing check results
        """
        try:
            loader = self._get_loader(auto_install=False)

            # Discover deployed agents
            loader.discover_deployed_agents()

            # Filter to specific agent if requested
            if agent_name:
                if agent_name not in loader.deployed_agents:
                    available = list(loader.deployed_agents.keys())
                    return {
                        "success": False,
                        "error": f"Agent '{agent_name}' is not deployed",
                        "available_agents": available,
                    }
                # Keep only the specified agent
                loader.deployed_agents = {
                    agent_name: loader.deployed_agents[agent_name]
                }

            # Load dependencies and check
            loader.load_agent_dependencies()
            results = loader.analyze_dependencies()

            # Generate report
            report = loader.format_report(results)

            return {
                "success": True,
                "report": report,
                "results": results,
                "agent": agent_name,
            }

        except Exception as e:
            self.logger.error(f"Dependency check failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "agent": agent_name,
            }

    def install_dependencies(
        self, agent_name: Optional[str] = None, dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Install missing dependencies for agents.

        Args:
            agent_name: Optional specific agent to install for
            dry_run: Whether to simulate installation

        Returns:
            Dictionary containing installation results
        """
        try:
            loader = self._get_loader(auto_install=not dry_run)

            # Discover deployed agents
            loader.discover_deployed_agents()

            # Filter to specific agent if requested
            if agent_name:
                if agent_name not in loader.deployed_agents:
                    available = list(loader.deployed_agents.keys())
                    return {
                        "success": False,
                        "error": f"Agent '{agent_name}' is not deployed",
                        "available_agents": available,
                    }
                loader.deployed_agents = {
                    agent_name: loader.deployed_agents[agent_name]
                }

            # Load dependencies
            loader.load_agent_dependencies()
            results = loader.analyze_dependencies()

            missing_deps = results["summary"]["missing_python"]

            if not missing_deps:
                return {
                    "success": True,
                    "message": "All Python dependencies are already installed",
                    "missing_count": 0,
                }

            if dry_run:
                return {
                    "success": True,
                    "dry_run": True,
                    "missing_dependencies": missing_deps,
                    "install_command": f"pip install {' '.join(missing_deps)}",
                }

            # Install missing dependencies
            success, error = loader.install_missing_dependencies(missing_deps)

            if success:
                # Re-check after installation
                loader.checked_packages.clear()
                final_results = loader.analyze_dependencies()
                still_missing = final_results["summary"]["missing_python"]

                return {
                    "success": True,
                    "installed": missing_deps,
                    "still_missing": still_missing,
                    "fully_resolved": len(still_missing) == 0,
                }
            return {
                "success": False,
                "error": error,
                "failed_dependencies": missing_deps,
            }

        except Exception as e:
            self.logger.error(f"Dependency installation failed: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    def list_dependencies(self, format_type: str = "text") -> Dict[str, Any]:
        """
        List all dependencies from deployed agents.

        Args:
            format_type: Output format (text, json, or pip)

        Returns:
            Dictionary containing dependency listing
        """
        try:
            loader = self._get_loader(auto_install=False)

            # Discover and load
            loader.discover_deployed_agents()
            loader.load_agent_dependencies()

            # Collect all unique dependencies
            all_python_deps = set()
            all_system_deps = set()

            for _agent_id, deps in loader.agent_dependencies.items():
                if "python" in deps:
                    all_python_deps.update(deps["python"])
                if "system" in deps:
                    all_system_deps.update(deps["system"])

            # Format result based on requested format
            if format_type == "pip":
                return {
                    "success": True,
                    "format": "pip",
                    "dependencies": sorted(all_python_deps),
                }
            if format_type == "json":
                return {
                    "success": True,
                    "format": "json",
                    "data": {
                        "python": sorted(all_python_deps),
                        "system": sorted(all_system_deps),
                        "agents": loader.agent_dependencies,
                    },
                }
            # text format
            return {
                "success": True,
                "format": "text",
                "python_dependencies": sorted(all_python_deps),
                "system_dependencies": sorted(all_system_deps),
                "per_agent": loader.agent_dependencies,
            }

        except Exception as e:
            self.logger.error(f"Dependency listing failed: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    def fix_dependencies(
        self, max_retries: int = 3, agent_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Auto-fix dependency issues with retry logic.

        Args:
            max_retries: Maximum retry attempts per package
            agent_name: Optional specific agent to fix

        Returns:
            Dictionary containing fix results
        """
        try:
            loader = self._get_loader(auto_install=False)

            # Discover and analyze
            loader.discover_deployed_agents()

            if not loader.deployed_agents:
                return {
                    "success": True,
                    "message": "No deployed agents found",
                }

            # Filter to specific agent if requested
            if agent_name:
                if agent_name not in loader.deployed_agents:
                    return {
                        "success": False,
                        "error": f"Agent '{agent_name}' is not deployed",
                    }
                loader.deployed_agents = {
                    agent_name: loader.deployed_agents[agent_name]
                }

            loader.load_agent_dependencies()
            results = loader.analyze_dependencies()

            missing_python = results["summary"]["missing_python"]
            missing_system = results["summary"]["missing_system"]

            if not missing_python and not missing_system:
                return {
                    "success": True,
                    "message": "All dependencies are already satisfied",
                }

            fix_results = {
                "success": True,
                "missing_python": missing_python,
                "missing_system": missing_system,
                "fixed_python": [],
                "failed_python": [],
                "incompatible": [],
            }

            # Fix Python dependencies with robust installer
            if missing_python:
                # Check compatibility
                compatible, incompatible = loader.check_python_compatibility(
                    missing_python
                )
                fix_results["incompatible"] = incompatible

                if compatible:
                    installer = RobustPackageInstaller(
                        max_retries=max_retries,
                        retry_delay=2.0,
                        timeout=300,
                    )

                    successful, failed, errors = installer.install_packages(compatible)

                    fix_results["fixed_python"] = successful
                    fix_results["failed_python"] = failed
                    fix_results["errors"] = errors

                    # Re-check after fixes
                    loader.checked_packages.clear()
                    final_results = loader.analyze_dependencies()
                    fix_results["still_missing"] = final_results["summary"][
                        "missing_python"
                    ]

            return fix_results

        except Exception as e:
            self.logger.error(f"Dependency fix failed: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    def validate_compatibility(
        self, packages: List[str]
    ) -> Tuple[List[str], List[str]]:
        """
        Check version compatibility for packages.

        Args:
            packages: List of package names to check

        Returns:
            Tuple of (compatible_packages, incompatible_packages)
        """
        try:
            loader = self._get_loader(auto_install=False)
            return loader.check_python_compatibility(packages)
        except Exception as e:
            self.logger.error(f"Compatibility check failed: {e}")
            return [], packages  # Assume all incompatible on error

    def get_dependency_report(self) -> str:
        """
        Generate a formatted dependency report.

        Returns:
            Formatted report string
        """
        try:
            loader = self._get_loader(auto_install=False)
            loader.discover_deployed_agents()
            loader.load_agent_dependencies()
            results = loader.analyze_dependencies()
            return loader.format_report(results)
        except Exception as e:
            self.logger.error(f"Report generation failed: {e}")
            return f"Failed to generate dependency report: {e}"
