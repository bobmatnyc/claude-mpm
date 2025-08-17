"""Agent deployment result for individual agent processing."""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional


class AgentDeploymentStatus(Enum):
    """Status of agent deployment."""

    DEPLOYED = "deployed"
    UPDATED = "updated"
    MIGRATED = "migrated"
    SKIPPED = "skipped"
    FAILED = "failed"


@dataclass
class AgentDeploymentResult:
    """Result of deploying a single agent.

    This class encapsulates the result of processing and deploying
    a single agent template.
    """

    # Agent identification
    agent_name: str
    template_file: Path
    target_file: Path

    # Deployment status
    status: AgentDeploymentStatus

    # Timing information
    deployment_time_ms: float = 0.0
    start_time: Optional[float] = None
    end_time: Optional[float] = None

    # Status details
    reason: Optional[str] = None
    error_message: Optional[str] = None

    # Flags
    was_update: bool = False
    was_migration: bool = False
    was_skipped: bool = False

    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def deployed(
        cls,
        agent_name: str,
        template_file: Path,
        target_file: Path,
        deployment_time_ms: float = 0.0,
    ) -> "AgentDeploymentResult":
        """Create a deployed result.

        Args:
            agent_name: Name of the agent
            template_file: Template file path
            target_file: Target file path
            deployment_time_ms: Deployment time in milliseconds

        Returns:
            AgentDeploymentResult with deployed status
        """
        return cls(
            agent_name=agent_name,
            template_file=template_file,
            target_file=target_file,
            status=AgentDeploymentStatus.DEPLOYED,
            deployment_time_ms=deployment_time_ms,
        )

    @classmethod
    def updated(
        cls,
        agent_name: str,
        template_file: Path,
        target_file: Path,
        deployment_time_ms: float = 0.0,
        reason: Optional[str] = None,
    ) -> "AgentDeploymentResult":
        """Create an updated result.

        Args:
            agent_name: Name of the agent
            template_file: Template file path
            target_file: Target file path
            deployment_time_ms: Deployment time in milliseconds
            reason: Reason for update

        Returns:
            AgentDeploymentResult with updated status
        """
        return cls(
            agent_name=agent_name,
            template_file=template_file,
            target_file=target_file,
            status=AgentDeploymentStatus.UPDATED,
            deployment_time_ms=deployment_time_ms,
            reason=reason,
            was_update=True,
        )

    @classmethod
    def migrated(
        cls,
        agent_name: str,
        template_file: Path,
        target_file: Path,
        deployment_time_ms: float = 0.0,
        reason: Optional[str] = None,
    ) -> "AgentDeploymentResult":
        """Create a migrated result.

        Args:
            agent_name: Name of the agent
            template_file: Template file path
            target_file: Target file path
            deployment_time_ms: Deployment time in milliseconds
            reason: Reason for migration

        Returns:
            AgentDeploymentResult with migrated status
        """
        return cls(
            agent_name=agent_name,
            template_file=template_file,
            target_file=target_file,
            status=AgentDeploymentStatus.MIGRATED,
            deployment_time_ms=deployment_time_ms,
            reason=reason,
            was_migration=True,
        )

    @classmethod
    def skipped(
        cls,
        agent_name: str,
        template_file: Path,
        target_file: Path,
        reason: Optional[str] = None,
    ) -> "AgentDeploymentResult":
        """Create a skipped result.

        Args:
            agent_name: Name of the agent
            template_file: Template file path
            target_file: Target file path
            reason: Reason for skipping

        Returns:
            AgentDeploymentResult with skipped status
        """
        return cls(
            agent_name=agent_name,
            template_file=template_file,
            target_file=target_file,
            status=AgentDeploymentStatus.SKIPPED,
            reason=reason,
            was_skipped=True,
        )

    @classmethod
    def failed(
        cls,
        agent_name: str,
        template_file: Path,
        target_file: Path,
        error_message: str,
        deployment_time_ms: float = 0.0,
    ) -> "AgentDeploymentResult":
        """Create a failed result.

        Args:
            agent_name: Name of the agent
            template_file: Template file path
            target_file: Target file path
            error_message: Error message
            deployment_time_ms: Deployment time in milliseconds

        Returns:
            AgentDeploymentResult with failed status
        """
        return cls(
            agent_name=agent_name,
            template_file=template_file,
            target_file=target_file,
            status=AgentDeploymentStatus.FAILED,
            deployment_time_ms=deployment_time_ms,
            error_message=error_message,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary.

        Returns:
            Dictionary representation of the result
        """
        result = {
            "name": self.agent_name,
            "template": str(self.template_file),
            "target": str(self.target_file),
            "status": self.status.value,
            "deployment_time_ms": self.deployment_time_ms,
        }

        if self.reason:
            result["reason"] = self.reason

        if self.error_message:
            result["error"] = self.error_message

        if self.metadata:
            result["metadata"] = self.metadata

        return result

    def is_successful(self) -> bool:
        """Check if deployment was successful.

        Returns:
            True if status is deployed, updated, migrated, or skipped
        """
        return self.status in [
            AgentDeploymentStatus.DEPLOYED,
            AgentDeploymentStatus.UPDATED,
            AgentDeploymentStatus.MIGRATED,
            AgentDeploymentStatus.SKIPPED,
        ]
