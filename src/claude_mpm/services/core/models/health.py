"""
Health Monitoring Data Models for Claude MPM Framework
=======================================================

WHY: This module defines data structures for health monitoring operations,
including health status, check results, and deployment health aggregations.

DESIGN DECISION: Uses dataclasses for immutability and type safety. Provides
clear health status enum and structured check results.

ARCHITECTURE:
- HealthStatus: Enum of health states (HEALTHY, DEGRADED, UNHEALTHY, UNKNOWN)
- HealthCheckResult: Result of a single health check
- DeploymentHealth: Aggregated health status for a deployment
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List

from ....core.enums import HealthStatus


@dataclass
class HealthCheckResult:
    """
    Result of a single health check.

    WHY: Contains all information about a specific health check execution,
    enabling detailed analysis and debugging of health issues.

    Attributes:
        status: HealthStatus of the check
        check_type: Type of health check (http, process, resource)
        message: Human-readable description of the result
        details: Additional check-specific data
        checked_at: Timestamp when check was performed
    """

    status: HealthStatus
    check_type: str
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    checked_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for JSON serialization.

        Returns:
            Dictionary representation with datetime converted to ISO format
        """
        data = asdict(self)
        data["status"] = self.status.value
        data["checked_at"] = self.checked_at.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HealthCheckResult":
        """
        Create HealthCheckResult from dictionary.

        Args:
            data: Dictionary from JSON deserialization

        Returns:
            HealthCheckResult instance
        """
        # Convert ISO string to datetime
        if isinstance(data.get("checked_at"), str):
            data["checked_at"] = datetime.fromisoformat(data["checked_at"])

        # Convert status string to enum
        if isinstance(data.get("status"), str):
            data["status"] = HealthStatus(data["status"])

        return cls(**data)


@dataclass
class DeploymentHealth:
    """
    Aggregated health status for a deployment.

    WHY: Combines results from multiple health checks to provide a
    comprehensive health assessment of a deployment.

    Attributes:
        deployment_id: Unique deployment identifier
        overall_status: Aggregated health status
        checks: List of individual health check results
        last_check: Timestamp of the most recent health check
    """

    deployment_id: str
    overall_status: HealthStatus
    checks: List[HealthCheckResult] = field(default_factory=list)
    last_check: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for JSON serialization.

        Returns:
            Dictionary representation
        """
        return {
            "deployment_id": self.deployment_id,
            "overall_status": self.overall_status.value,
            "checks": [check.to_dict() for check in self.checks],
            "last_check": self.last_check.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DeploymentHealth":
        """
        Create DeploymentHealth from dictionary.

        Args:
            data: Dictionary from JSON deserialization

        Returns:
            DeploymentHealth instance
        """
        # Convert ISO string to datetime
        if isinstance(data.get("last_check"), str):
            data["last_check"] = datetime.fromisoformat(data["last_check"])

        # Convert status string to enum
        if isinstance(data.get("overall_status"), str):
            data["overall_status"] = HealthStatus(data["overall_status"])

        # Convert check dicts to HealthCheckResult objects
        if isinstance(data.get("checks"), list):
            data["checks"] = [
                HealthCheckResult.from_dict(check) if isinstance(check, dict) else check
                for check in data["checks"]
            ]

        return cls(**data)

    def get_check_by_type(self, check_type: str) -> HealthCheckResult | None:
        """
        Get the result of a specific check type.

        Args:
            check_type: Type of health check to retrieve

        Returns:
            HealthCheckResult if found, None otherwise
        """
        for check in self.checks:
            if check.check_type == check_type:
                return check
        return None


__all__ = [
    "DeploymentHealth",
    "HealthCheckResult",
    "HealthStatus",
]
