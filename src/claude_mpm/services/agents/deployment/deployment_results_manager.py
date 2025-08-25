"""Deployment results manager for tracking deployment outcomes."""

import logging
import time
from pathlib import Path
from typing import Any, Dict, Optional


class DeploymentResultsManager:
    """Service for managing deployment results and metrics.

    This service handles initialization and updates of deployment
    results dictionaries, ensuring consistent structure across
    all deployment operations.
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize the deployment results manager.

        Args:
            logger: Optional logger instance
        """
        self.logger = logger or logging.getLogger(__name__)

        # Initialize deployment metrics tracking
        self._deployment_metrics = {
            "total_deployments": 0,
            "successful_deployments": 0,
            "failed_deployments": 0,
            "migrations_performed": 0,
            "version_migration_count": 0,
            "agent_type_counts": {},
            "deployment_errors": {},
        }

    def initialize_deployment_results(
        self, agents_dir: Path, deployment_start_time: float
    ) -> Dict[str, Any]:
        """Initialize the deployment results dictionary.

        WHY: Consistent result structure ensures all deployment
        operations return the same format for easier processing.

        Args:
            agents_dir: Target agents directory
            deployment_start_time: Start time for metrics

        Returns:
            Initialized results dictionary
        """
        return {
            "target_dir": str(agents_dir),
            "deployed": [],
            "errors": [],
            "skipped": [],
            "updated": [],
            "migrated": [],  # Track agents migrated from old format
            "converted": [],  # Track YAML to MD conversions
            "repaired": [],  # Track agents with repaired frontmatter
            "total": 0,
            # METRICS: Add detailed timing and performance data to results
            "metrics": {
                "start_time": deployment_start_time,
                "end_time": None,
                "duration_ms": None,
                "agent_timings": {},  # Track individual agent deployment times
                "validation_times": {},  # Track template validation times
                "resource_usage": {},  # Could track memory/CPU if needed
            },
        }

    def record_agent_deployment(
        self,
        agent_name: str,
        template_file: Path,
        target_file: Path,
        is_update: bool,
        is_migration: bool,
        reason: str,
        agent_start_time: float,
        results: Dict[str, Any],
        logger: Optional[logging.Logger] = None,
    ) -> None:
        """Record deployment metrics and update results.

        WHY: Centralized metrics recording ensures consistent tracking
        of deployment performance and statistics.

        Args:
            agent_name: Name of the agent
            template_file: Template file
            target_file: Target file
            is_update: Whether this is an update
            is_migration: Whether this is a migration
            reason: Update/migration reason
            agent_start_time: Start time for this agent
            results: Results dictionary to update
            logger: Optional logger for output
        """
        logger = logger or self.logger

        # METRICS: Record deployment time for this agent
        agent_deployment_time = (time.time() - agent_start_time) * 1000  # Convert to ms
        results["metrics"]["agent_timings"][agent_name] = agent_deployment_time

        # METRICS: Update agent type deployment counts
        self._deployment_metrics["agent_type_counts"][agent_name] = (
            self._deployment_metrics["agent_type_counts"].get(agent_name, 0) + 1
        )

        deployment_info = {
            "name": agent_name,
            "template": str(template_file),
            "target": str(target_file),
            "deployment_time_ms": agent_deployment_time,
        }

        if is_migration:
            deployment_info["reason"] = reason
            results["migrated"].append(deployment_info)
            logger.info(
                f"Successfully migrated agent: {agent_name} to semantic versioning"
            )

            # METRICS: Track migration statistics
            self._deployment_metrics["migrations_performed"] += 1
            self._deployment_metrics["version_migration_count"] += 1

        elif is_update:
            results["updated"].append(deployment_info)
            logger.debug(f"Updated agent: {agent_name}")
        else:
            results["deployed"].append(deployment_info)
            logger.debug(f"Built and deployed agent: {agent_name}")

    def finalize_results(
        self, results: Dict[str, Any], deployment_start_time: float
    ) -> None:
        """Finalize deployment results with end metrics.

        Args:
            results: Results dictionary to finalize
            deployment_start_time: Original start time
        """
        deployment_end_time = time.time()
        deployment_duration = (deployment_end_time - deployment_start_time) * 1000  # ms

        results["metrics"]["end_time"] = deployment_end_time
        results["metrics"]["duration_ms"] = deployment_duration

    def update_deployment_metrics(
        self, success: bool, error_type: Optional[str] = None
    ) -> None:
        """Update internal deployment metrics.

        Args:
            success: Whether deployment succeeded
            error_type: Type of error if failed
        """
        self._deployment_metrics["total_deployments"] += 1

        if success:
            self._deployment_metrics["successful_deployments"] += 1
        else:
            self._deployment_metrics["failed_deployments"] += 1
            if error_type:
                self._deployment_metrics["deployment_errors"][error_type] = (
                    self._deployment_metrics["deployment_errors"].get(error_type, 0) + 1
                )

    def get_deployment_metrics(self) -> Dict[str, Any]:
        """Get current deployment metrics."""
        return self._deployment_metrics.copy()

    def reset_metrics(self) -> None:
        """Reset deployment metrics."""
        self._deployment_metrics = {
            "total_deployments": 0,
            "successful_deployments": 0,
            "failed_deployments": 0,
            "migrations_performed": 0,
            "version_migration_count": 0,
            "agent_type_counts": {},
            "deployment_errors": {},
        }
