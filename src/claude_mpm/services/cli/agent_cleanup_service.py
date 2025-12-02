"""
Agent Cleanup Service
=====================

WHY: This service manages agent cleanup operations including removing deployed agents
and cleaning up orphaned agents. It provides a clean interface for the CLI to perform
cleanup operations with dry-run support and progress reporting.

DESIGN DECISIONS:
- Separates cleanup logic from CLI command implementation
- Provides dry-run mode for safe preview of changes
- Identifies orphaned agents (deployed without templates)
- Validates cleanup operations before execution
- Generates detailed cleanup reports for user feedback
- Maintains backward compatibility with existing deployment service
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional

from ...core.logger import get_logger


class IAgentCleanupService(ABC):
    """Interface for agent cleanup operations."""

    @abstractmethod
    def clean_deployed_agents(
        self, agents_dir: Optional[Path] = None
    ) -> Dict[str, Any]:
        """Clean up deployed agents while preserving user-created agents."""

    @abstractmethod
    def clean_orphaned_agents(
        self, agents_dir: Optional[Path] = None, dry_run: bool = True
    ) -> Dict[str, Any]:
        """Clean up orphaned agents that don't have templates."""

    @abstractmethod
    def get_orphaned_agents(
        self, agents_dir: Optional[Path] = None
    ) -> List[Dict[str, Any]]:
        """Find orphaned agents (deployed without templates)."""

    @abstractmethod
    def perform_cleanup(
        self,
        agents_dir: Optional[Path] = None,
        cleanup_type: str = "all",
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Execute cleanup with specified options."""

    @abstractmethod
    def validate_cleanup(self, agents_dir: Optional[Path] = None) -> Dict[str, Any]:
        """Verify cleanup operation safety before execution."""


class AgentCleanupService(IAgentCleanupService):
    """Service for managing agent cleanup operations with robust error handling."""

    def __init__(self, deployment_service=None):
        """
        Initialize the cleanup service.

        Args:
            deployment_service: Optional deployment service for cleanup operations
        """
        self.logger = get_logger(__name__)
        self._deployment_service = deployment_service
        self._multi_source_service = None

    def _get_deployment_service(self):
        """Get or create deployment service instance."""
        if self._deployment_service is None:
            from ...services.agents.deployment.agent_deployment import (
                AgentDeploymentService,
            )

            self._deployment_service = AgentDeploymentService()
        return self._deployment_service

    def _get_multi_source_service(self):
        """Get or create multi-source deployment service instance."""
        if self._multi_source_service is None:
            from ...services.agents.deployment.multi_source_deployment_service import (
                MultiSourceAgentDeploymentService,
            )

            self._multi_source_service = MultiSourceAgentDeploymentService()
        return self._multi_source_service

    def _determine_agents_dir(self, agents_dir: Optional[Path] = None) -> Path:
        """
        Determine the agents directory to use.

        Args:
            agents_dir: Optional explicit agents directory

        Returns:
            Path to agents directory
        """
        if agents_dir:
            return agents_dir

        # Check for project-level .claude/agents first
        project_agents_dir = Path.cwd() / ".claude" / "agents"
        if project_agents_dir.exists():
            return project_agents_dir

        # Fall back to user home directory
        return Path.home() / ".claude" / "agents"

    def clean_deployed_agents(
        self, agents_dir: Optional[Path] = None
    ) -> Dict[str, Any]:
        """
        Clean up deployed agents while preserving user-created agents.

        This removes system-deployed agents (authored by claude-mpm) while
        preserving any user-created agents in the directory.

        Args:
            agents_dir: Optional agents directory to clean

        Returns:
            Dictionary containing cleanup results
        """
        try:
            deployment_service = self._get_deployment_service()

            # Use deployment service's clean_deployment method
            if hasattr(deployment_service, "clean_deployment"):
                result = deployment_service.clean_deployment()

                # Ensure consistent result format
                if not isinstance(result, dict):
                    result = {"success": bool(result)}

                # Add success flag based on whether there were errors
                if "success" not in result:
                    # Consider it successful if no errors occurred
                    result["success"] = not bool(result.get("errors"))

                # Add cleaned_count for backward compatibility
                if "cleaned_count" not in result:
                    removed_count = len(result.get("removed", []))
                    result["cleaned_count"] = removed_count

                return result
            # Fallback if method doesn't exist
            return {
                "success": False,
                "error": "Deployment service does not support cleanup",
                "cleaned_count": 0,
            }

        except Exception as e:
            self.logger.error(f"Error cleaning deployed agents: {e}", exc_info=True)
            return {"success": False, "error": str(e), "cleaned_count": 0}

    def clean_orphaned_agents(
        self, agents_dir: Optional[Path] = None, dry_run: bool = True
    ) -> Dict[str, Any]:
        """
        Clean up orphaned agents that don't have templates.

        Orphaned agents are deployed agents that no longer have corresponding
        templates in the codebase. This method identifies and optionally removes them.

        Args:
            agents_dir: Optional agents directory to clean
            dry_run: If True, only report what would be removed

        Returns:
            Dictionary containing cleanup results
        """
        try:
            agents_dir = self._determine_agents_dir(agents_dir)

            if not agents_dir.exists():
                return {
                    "success": True,
                    "message": f"Agents directory not found: {agents_dir}",
                    "orphaned": [],
                    "removed": [],
                    "errors": [],
                }

            multi_source_service = self._get_multi_source_service()

            # Perform cleanup using multi-source service
            results = multi_source_service.cleanup_orphaned_agents(
                agents_dir, dry_run=dry_run
            )

            # Add success flag for consistent interface
            if "success" not in results:
                results["success"] = not bool(results.get("errors"))

            return results

        except Exception as e:
            self.logger.error(f"Error cleaning orphaned agents: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "orphaned": [],
                "removed": [],
                "errors": [str(e)],
            }

    def get_orphaned_agents(
        self, agents_dir: Optional[Path] = None
    ) -> List[Dict[str, Any]]:
        """
        Find orphaned agents (deployed without templates).

        This method identifies deployed agents that no longer have corresponding
        templates in the codebase without removing them.

        Args:
            agents_dir: Optional agents directory to check

        Returns:
            List of orphaned agent information dictionaries
        """
        try:
            agents_dir = self._determine_agents_dir(agents_dir)

            if not agents_dir.exists():
                return []

            multi_source_service = self._get_multi_source_service()

            # Discover all available agents from all sources
            all_agents = multi_source_service.discover_agents_from_all_sources()

            # Detect orphaned agents
            return multi_source_service.detect_orphaned_agents(agents_dir, all_agents)

        except Exception as e:
            self.logger.error(f"Error finding orphaned agents: {e}", exc_info=True)
            return []

    def perform_cleanup(
        self,
        agents_dir: Optional[Path] = None,
        cleanup_type: str = "all",
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """
        Execute cleanup with specified options.

        This method provides a unified interface for different cleanup operations.

        Args:
            agents_dir: Optional agents directory to clean
            cleanup_type: Type of cleanup ("all", "deployed", "orphaned")
            dry_run: If True, only preview changes without executing

        Returns:
            Dictionary containing cleanup results
        """
        try:
            results = {
                "success": True,
                "cleanup_type": cleanup_type,
                "dry_run": dry_run,
                "operations": [],
            }

            if cleanup_type in ["all", "deployed"]:
                # Clean deployed agents
                deployed_result = self.clean_deployed_agents(agents_dir)
                results["operations"].append(
                    {"type": "deployed", "result": deployed_result}
                )
                if not deployed_result.get("success", False):
                    results["success"] = False

            if cleanup_type in ["all", "orphaned"]:
                # Clean orphaned agents
                orphaned_result = self.clean_orphaned_agents(
                    agents_dir, dry_run=dry_run
                )
                results["operations"].append(
                    {"type": "orphaned", "result": orphaned_result}
                )
                if not orphaned_result.get("success", False):
                    results["success"] = False

            # Calculate totals
            total_cleaned = 0
            total_errors = 0
            for op in results["operations"]:
                result = op["result"]
                if op["type"] == "deployed":
                    total_cleaned += result.get("cleaned_count", 0)
                elif op["type"] == "orphaned":
                    if dry_run:
                        total_cleaned += len(result.get("orphaned", []))
                    else:
                        total_cleaned += len(result.get("removed", []))
                total_errors += len(result.get("errors", []))

            results["total_cleaned"] = total_cleaned
            results["total_errors"] = total_errors

            return results

        except Exception as e:
            self.logger.error(f"Error performing cleanup: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "cleanup_type": cleanup_type,
                "dry_run": dry_run,
                "operations": [],
            }

    def validate_cleanup(self, agents_dir: Optional[Path] = None) -> Dict[str, Any]:
        """
        Verify cleanup operation safety before execution.

        This method checks for potential issues that might occur during cleanup
        and provides warnings about what will be removed.

        Args:
            agents_dir: Optional agents directory to validate

        Returns:
            Dictionary containing validation results
        """
        try:
            agents_dir = self._determine_agents_dir(agents_dir)

            validation = {
                "success": True,
                "agents_dir": str(agents_dir),
                "exists": agents_dir.exists(),
                "warnings": [],
                "info": [],
            }

            if not agents_dir.exists():
                validation["info"].append(
                    f"Agents directory does not exist: {agents_dir}"
                )
                return validation

            # Count deployed agents
            deployed_count = 0
            user_created_count = 0

            for agent_file in agents_dir.glob("*.md"):
                try:
                    content = agent_file.read_text()
                    if "author: claude-mpm" in content.lower():
                        deployed_count += 1
                    else:
                        user_created_count += 1
                except Exception as e:
                    validation["warnings"].append(
                        f"Could not read {agent_file.name}: {e}"
                    )

            validation["deployed_count"] = deployed_count
            validation["user_created_count"] = user_created_count

            # Check for orphaned agents
            orphaned = self.get_orphaned_agents(agents_dir)
            validation["orphaned_count"] = len(orphaned)

            if orphaned:
                validation["orphaned_agents"] = [
                    {"name": agent["name"], "version": agent.get("version", "unknown")}
                    for agent in orphaned
                ]

            # Add informational messages
            if deployed_count > 0:
                validation["info"].append(
                    f"Found {deployed_count} system-deployed agent(s) that can be cleaned"
                )

            if user_created_count > 0:
                validation["info"].append(
                    f"Found {user_created_count} user-created agent(s) that will be preserved"
                )

            if orphaned:
                validation["warnings"].append(
                    f"Found {len(orphaned)} orphaned agent(s) without templates"
                )

            return validation

        except Exception as e:
            self.logger.error(f"Error validating cleanup: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "agents_dir": str(agents_dir) if agents_dir else "unknown",
                "warnings": [str(e)],
                "info": [],
            }
