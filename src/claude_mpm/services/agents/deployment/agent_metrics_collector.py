"""Agent Metrics Collector Service

This service handles the collection, tracking, and reporting of agent deployment metrics.
Provides detailed analytics on deployment performance, success rates, and patterns.

Extracted from AgentDeploymentService as part of the refactoring to improve
maintainability and testability.
"""

import time
from typing import Any, Dict

from claude_mpm.core.logging_config import get_logger


class AgentMetricsCollector:
    """Service for collecting and managing agent deployment metrics.

    This service handles:
    - Deployment timing and performance metrics
    - Success/failure rate tracking
    - Agent type distribution analysis
    - Version migration statistics
    - Error pattern analysis
    """

    def __init__(self):
        """Initialize the metrics collector."""
        self.logger = get_logger(__name__)

        # Initialize metrics storage
        self._deployment_metrics = {
            "total_deployments": 0,
            "successful_deployments": 0,
            "failed_deployments": 0,
            "migrations_performed": 0,
            "average_deployment_time_ms": 0.0,
            "deployment_times": [],  # Keep last 100 for rolling average
            "agent_type_counts": {},  # Track deployments by agent type
            "version_migration_count": 0,
            "template_validation_times": {},  # Track validation performance
            "deployment_errors": {},  # Track error types and frequencies
        }

    def update_deployment_metrics(
        self, duration_ms: float, results: Dict[str, Any]
    ) -> None:
        """
        Update internal deployment metrics with results from a deployment.

        Args:
            duration_ms: Deployment duration in milliseconds
            results: Deployment results dictionary
        """
        # Update basic counters
        self._deployment_metrics["total_deployments"] += 1

        # Track deployment success/failure
        if results.get("errors"):
            self._deployment_metrics["failed_deployments"] += 1

            # Track error patterns
            for error in results.get("errors", []):
                error_type = self._categorize_error(error)
                self._deployment_metrics["deployment_errors"][error_type] = (
                    self._deployment_metrics["deployment_errors"].get(error_type, 0) + 1
                )
        else:
            self._deployment_metrics["successful_deployments"] += 1

        # Track migrations
        if results.get("migrated"):
            migration_count = len(results["migrated"])
            self._deployment_metrics["migrations_performed"] += migration_count
            self._deployment_metrics["version_migration_count"] += migration_count

        # Track agent types
        for deployment_info in results.get("deployed", []):
            # Extract agent name from deployment info dict
            agent_name = (
                deployment_info.get("name")
                if isinstance(deployment_info, dict)
                else deployment_info
            )
            if agent_name:
                agent_type = self._extract_agent_type(agent_name)
                self._deployment_metrics["agent_type_counts"][agent_type] = (
                    self._deployment_metrics["agent_type_counts"].get(agent_type, 0) + 1
                )

        # Update timing metrics
        self._deployment_metrics["deployment_times"].append(duration_ms)

        # Keep only last 100 deployment times for rolling average
        if len(self._deployment_metrics["deployment_times"]) > 100:
            self._deployment_metrics["deployment_times"] = self._deployment_metrics[
                "deployment_times"
            ][-100:]

        # Calculate rolling average
        if self._deployment_metrics["deployment_times"]:
            self._deployment_metrics["average_deployment_time_ms"] = sum(
                self._deployment_metrics["deployment_times"]
            ) / len(self._deployment_metrics["deployment_times"])

    def get_deployment_metrics(self) -> Dict[str, Any]:
        """
        Get current deployment metrics.

        Returns:
            Dictionary containing comprehensive deployment metrics
        """
        # Calculate success rate
        total = self._deployment_metrics["total_deployments"]
        success_rate = 0.0
        if total > 0:
            success_rate = (
                self._deployment_metrics["successful_deployments"] / total * 100
            )

        return {
            "total_deployments": self._deployment_metrics["total_deployments"],
            "successful_deployments": self._deployment_metrics[
                "successful_deployments"
            ],
            "failed_deployments": self._deployment_metrics["failed_deployments"],
            "success_rate_percent": round(success_rate, 2),
            "average_deployment_time_ms": round(
                self._deployment_metrics["average_deployment_time_ms"], 2
            ),
            "migrations_performed": self._deployment_metrics["migrations_performed"],
            "agent_type_distribution": self._deployment_metrics[
                "agent_type_counts"
            ].copy(),
            "version_migrations": self._deployment_metrics["version_migration_count"],
            "error_distribution": self._deployment_metrics["deployment_errors"].copy(),
            "recent_deployment_times": self._deployment_metrics["deployment_times"][
                -10:
            ],  # Last 10
        }

    def get_deployment_status(self) -> Dict[str, Any]:
        """
        Get comprehensive deployment status including metrics.

        Returns:
            Dictionary with deployment status and metrics
        """
        return {
            "deployment_metrics": self.get_deployment_metrics(),
            "last_updated": time.time(),
            "metrics_collection_active": True,
        }

    def reset_metrics(self) -> None:
        """Reset all deployment metrics to initial state."""
        self._deployment_metrics = {
            "total_deployments": 0,
            "successful_deployments": 0,
            "failed_deployments": 0,
            "migrations_performed": 0,
            "average_deployment_time_ms": 0.0,
            "deployment_times": [],
            "agent_type_counts": {},
            "version_migration_count": 0,
            "template_validation_times": {},
            "deployment_errors": {},
        }
        self.logger.info("Deployment metrics reset")

    def track_validation_time(self, agent_name: str, validation_time_ms: float) -> None:
        """
        Track template validation performance.

        Args:
            agent_name: Name of the agent being validated
            validation_time_ms: Validation time in milliseconds
        """
        self._deployment_metrics["template_validation_times"][agent_name] = (
            validation_time_ms
        )

    def get_performance_summary(self) -> Dict[str, Any]:
        """
        Get performance summary with key metrics.

        Returns:
            Dictionary with performance summary
        """
        metrics = self.get_deployment_metrics()

        # Calculate additional performance metrics
        deployment_times = self._deployment_metrics["deployment_times"]

        return {
            "total_deployments": metrics["total_deployments"],
            "success_rate": metrics["success_rate_percent"],
            "average_time_ms": metrics["average_deployment_time_ms"],
            "fastest_deployment_ms": min(deployment_times) if deployment_times else 0,
            "slowest_deployment_ms": max(deployment_times) if deployment_times else 0,
            "total_migrations": metrics["migrations_performed"],
            "most_common_agent_type": self._get_most_common_agent_type(),
            "error_rate_percent": self._calculate_error_rate(),
        }

    def _categorize_error(self, error: str) -> str:
        """
        Categorize an error message into a type for tracking.

        Args:
            error: Error message

        Returns:
            Error category string
        """
        error_lower = str(error).lower()

        if "json" in error_lower or "parse" in error_lower:
            return "parsing_error"
        if "file" in error_lower or "path" in error_lower:
            return "file_error"
        if "version" in error_lower:
            return "version_error"
        if "template" in error_lower:
            return "template_error"
        if "validation" in error_lower:
            return "validation_error"
        return "other_error"

    def _extract_agent_type(self, agent_name: str) -> str:
        """
        Extract agent type from agent name for categorization.

        Args:
            agent_name: Name of the agent

        Returns:
            Agent type category
        """
        name_lower = agent_name.lower()

        # Common agent type patterns
        if "security" in name_lower:
            return "security"
        if "qa" in name_lower or "test" in name_lower:
            return "qa"
        if "doc" in name_lower:
            return "documentation"
        if "data" in name_lower:
            return "data"
        if "ops" in name_lower:
            return "operations"
        if "research" in name_lower:
            return "research"
        return "general"

    def _get_most_common_agent_type(self) -> str:
        """Get the most commonly deployed agent type."""
        if not self._deployment_metrics["agent_type_counts"]:
            return "none"

        return max(
            self._deployment_metrics["agent_type_counts"].items(), key=lambda x: x[1]
        )[0]

    def _calculate_error_rate(self) -> float:
        """Calculate the current error rate percentage."""
        total = self._deployment_metrics["total_deployments"]
        if total == 0:
            return 0.0

        failed = self._deployment_metrics["failed_deployments"]
        return round((failed / total) * 100, 2)
