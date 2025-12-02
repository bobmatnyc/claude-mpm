"""
Base Deployment Strategy
========================

Enhanced base class for all deployment strategies, extending the generic
DeploymentStrategy from the unified strategies module.

This module provides:
- Abstract base class with common deployment operations
- Deployment context and result data structures
- Health check and rollback interfaces
- Validation and pre-flight check framework
- Metrics collection hooks
"""

from abc import abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from claude_mpm.core.logging_utils import get_logger
from claude_mpm.services.unified.strategies import (
    DeploymentStrategy as BaseDeploymentStrategy,
    StrategyContext,
    StrategyMetadata,
    StrategyPriority,
)


class DeploymentStatus(Enum):
    """Deployment status enumeration."""

    PENDING = "pending"
    VALIDATING = "validating"
    PREPARING = "preparing"
    DEPLOYING = "deploying"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class DeploymentType(Enum):
    """Types of deployments."""

    AGENT = "agent"
    CONFIG = "config"
    RESOURCE = "resource"
    TEMPLATE = "template"
    APPLICATION = "application"
    SERVICE = "service"
    INFRASTRUCTURE = "infrastructure"


@dataclass
class DeploymentContext:
    """
    Enhanced context for deployment operations.

    Consolidates context patterns from:
    - agent_deployment.py
    - multi_source_deployment_service.py
    - deployment_config_loader.py
    """

    # Core deployment info
    source: Union[str, Path]
    target: Union[str, Path]
    deployment_type: DeploymentType

    # Configuration
    config: Dict[str, Any] = field(default_factory=dict)
    environment: Dict[str, str] = field(default_factory=dict)

    # Options
    force: bool = False
    dry_run: bool = False
    validate_only: bool = False
    backup_enabled: bool = True

    # Versioning
    version: Optional[str] = None
    previous_version: Optional[str] = None

    # Metadata
    tags: List[str] = field(default_factory=list)
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, Any] = field(default_factory=dict)

    def to_strategy_context(self) -> StrategyContext:
        """Convert to generic strategy context."""
        return StrategyContext(
            target_type=self.deployment_type.value,
            operation="deploy",
            parameters={
                "source": str(self.source),
                "target": str(self.target),
                "config": self.config,
                "force": self.force,
                "dry_run": self.dry_run,
            },
            constraints=self.tags,
            preferences={"environment": self.environment},
        )


@dataclass
class DeploymentResult:
    """
    Result of deployment operation.

    Consolidates result patterns from multiple deployment services.
    """

    # Core result
    success: bool
    status: DeploymentStatus
    message: str = ""

    # Deployment details
    deployment_id: Optional[str] = None
    deployed_path: Optional[Path] = None
    deployment_url: Optional[str] = None

    # Versioning
    version: Optional[str] = None
    previous_version: Optional[str] = None

    # Timing
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None

    # Artifacts
    artifacts: List[Path] = field(default_factory=list)
    logs: List[str] = field(default_factory=list)

    # Rollback info
    rollback_available: bool = False
    rollback_info: Dict[str, Any] = field(default_factory=dict)

    # Metrics
    metrics: Dict[str, Any] = field(default_factory=dict)

    # Errors and warnings
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "success": self.success,
            "status": self.status.value,
            "message": self.message,
            "deployment_id": self.deployment_id,
            "deployed_path": str(self.deployed_path) if self.deployed_path else None,
            "deployment_url": self.deployment_url,
            "version": self.version,
            "previous_version": self.previous_version,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
            "duration_seconds": self.duration_seconds,
            "artifacts": [str(a) for a in self.artifacts],
            "logs": self.logs,
            "rollback_available": self.rollback_available,
            "rollback_info": self.rollback_info,
            "metrics": self.metrics,
            "errors": self.errors,
            "warnings": self.warnings,
        }


class DeploymentStrategy(BaseDeploymentStrategy):
    """
    Enhanced base class for deployment strategies.

    This class consolidates common deployment patterns from 45+ deployment
    services into a single, reusable base class.

    Subclasses should implement:
    - validate(): Validate deployment configuration
    - prepare(): Prepare deployment artifacts
    - execute(): Execute the actual deployment
    - verify(): Verify deployment success
    - rollback(): Rollback on failure
    - get_health_status(): Check deployment health
    """

    def __init__(self, metadata: Optional[StrategyMetadata] = None):
        """
        Initialize deployment strategy.

        Args:
            metadata: Strategy metadata
        """
        super().__init__(metadata or self._create_metadata())
        self._logger = get_logger(f"{__name__}.{self.__class__.__name__}")
        self._current_deployment: Optional[DeploymentContext] = None
        self._deployment_history: List[DeploymentResult] = []

    def _create_metadata(self) -> StrategyMetadata:
        """Create default metadata for strategy."""
        return StrategyMetadata(
            name=self.__class__.__name__,
            description=self.__doc__ or "Deployment strategy",
            priority=StrategyPriority.NORMAL,
            supported_types=["*"],
            supported_operations=["deploy", "rollback", "verify"],
        )

    # Override base class method
    def deploy(
        self,
        source: Union[str, Path],
        target: Union[str, Path],
        config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Execute deployment (implements base class abstract method).

        Args:
            source: Deployment source
            target: Deployment target
            config: Deployment configuration

        Returns:
            Deployment result dictionary
        """
        context = DeploymentContext(
            source=Path(source),
            target=Path(target),
            deployment_type=self._detect_deployment_type(source, config),
            config=config or {},
        )
        result = self.deploy_with_context(context)
        return result.to_dict()

    def deploy_with_context(self, context: DeploymentContext) -> DeploymentResult:
        """
        Execute deployment with full context.

        This is the main entry point for deployment operations.

        Args:
            context: Deployment context

        Returns:
            Deployment result
        """
        self._current_deployment = context
        result = DeploymentResult(
            success=False,
            status=DeploymentStatus.PENDING,
            started_at=datetime.now(timezone.utc),
        )

        try:
            # Validation phase
            result.status = DeploymentStatus.VALIDATING
            self._logger.info(
                f"Validating deployment: {context.source} -> {context.target}"
            )

            validation_errors = self.validate(context)
            if validation_errors:
                result.errors = validation_errors
                result.message = f"Validation failed: {'; '.join(validation_errors)}"
                result.status = DeploymentStatus.FAILED
                return result

            if context.validate_only:
                result.success = True
                result.status = DeploymentStatus.COMPLETED
                result.message = "Validation successful"
                return result

            # Preparation phase
            result.status = DeploymentStatus.PREPARING
            self._logger.info("Preparing deployment artifacts")

            artifacts = self.prepare(context)
            result.artifacts = artifacts

            # Execution phase
            if not context.dry_run:
                result.status = DeploymentStatus.DEPLOYING
                self._logger.info("Executing deployment")

                deployment_info = self.execute(context, artifacts)
                result.deployment_id = deployment_info.get("deployment_id")
                result.deployed_path = deployment_info.get("deployed_path")
                result.deployment_url = deployment_info.get("deployment_url")
                result.version = context.version
                result.previous_version = context.previous_version

                # Verification phase
                result.status = DeploymentStatus.VERIFYING
                self._logger.info("Verifying deployment")

                if self.verify(context, deployment_info):
                    result.success = True
                    result.status = DeploymentStatus.COMPLETED
                    result.message = "Deployment successful"

                    # Prepare rollback info
                    result.rollback_available = True
                    result.rollback_info = self.prepare_rollback(deployment_info)
                else:
                    raise Exception("Deployment verification failed")
            else:
                result.success = True
                result.status = DeploymentStatus.COMPLETED
                result.message = "Dry run completed successfully"

        except Exception as e:
            self._logger.error(f"Deployment failed: {e!s}")
            result.status = DeploymentStatus.FAILED
            result.message = str(e)
            result.errors.append(str(e))

            # Attempt rollback if not dry run
            if not context.dry_run and context.backup_enabled:
                self._logger.info("Attempting rollback")
                try:
                    self.rollback(context, result)
                    result.status = DeploymentStatus.ROLLED_BACK
                    result.message += " (rolled back)"
                except Exception as rollback_error:
                    self._logger.error(f"Rollback failed: {rollback_error!s}")
                    result.errors.append(f"Rollback failed: {rollback_error!s}")

        finally:
            result.completed_at = datetime.now(timezone.utc)
            if result.started_at:
                result.duration_seconds = (
                    result.completed_at - result.started_at
                ).total_seconds()

            # Store in history
            self._deployment_history.append(result)

            # Collect metrics
            result.metrics = self._collect_metrics(context, result)

        return result

    # Abstract methods to be implemented by subclasses

    @abstractmethod
    def validate(self, context: DeploymentContext) -> List[str]:
        """
        Validate deployment configuration.

        Args:
            context: Deployment context

        Returns:
            List of validation errors (empty if valid)
        """

    @abstractmethod
    def prepare(self, context: DeploymentContext) -> List[Path]:
        """
        Prepare deployment artifacts.

        Args:
            context: Deployment context

        Returns:
            List of prepared artifact paths
        """

    @abstractmethod
    def execute(
        self, context: DeploymentContext, artifacts: List[Path]
    ) -> Dict[str, Any]:
        """
        Execute the deployment.

        Args:
            context: Deployment context
            artifacts: Prepared artifacts

        Returns:
            Deployment information including deployment_id, deployed_path, etc.
        """

    @abstractmethod
    def verify(
        self, context: DeploymentContext, deployment_info: Dict[str, Any]
    ) -> bool:
        """
        Verify deployment success.

        Args:
            context: Deployment context
            deployment_info: Information from execute phase

        Returns:
            True if deployment verified successfully
        """

    @abstractmethod
    def rollback(self, context: DeploymentContext, result: DeploymentResult) -> bool:
        """
        Rollback failed deployment.

        Args:
            context: Deployment context
            result: Current deployment result

        Returns:
            True if rollback successful
        """

    @abstractmethod
    def get_health_status(self, deployment_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get health status of deployment.

        Args:
            deployment_info: Deployment information

        Returns:
            Health status information
        """

    # Helper methods

    def _detect_deployment_type(
        self, source: Union[str, Path], config: Optional[Dict[str, Any]]
    ) -> DeploymentType:
        """
        Detect deployment type from source and config.

        Args:
            source: Deployment source
            config: Deployment configuration

        Returns:
            Detected deployment type
        """
        if config and "type" in config:
            type_str = config["type"].lower()
            try:
                return DeploymentType[type_str.upper()]
            except KeyError:
                pass

        # Detect from source path patterns
        source_path = Path(source)

        if "agent" in source_path.name.lower():
            return DeploymentType.AGENT
        if "config" in source_path.name.lower():
            return DeploymentType.CONFIG
        if "template" in source_path.name.lower():
            return DeploymentType.TEMPLATE
        if source_path.suffix in [".yaml", ".yml", ".json"]:
            return DeploymentType.CONFIG
        return DeploymentType.RESOURCE

    def _collect_metrics(
        self, context: DeploymentContext, result: DeploymentResult
    ) -> Dict[str, Any]:
        """
        Collect deployment metrics.

        Args:
            context: Deployment context
            result: Deployment result

        Returns:
            Collected metrics
        """
        return {
            "deployment_type": context.deployment_type.value,
            "source_size": self._get_size(context.source) if context.source else 0,
            "artifact_count": len(result.artifacts),
            "artifact_total_size": sum(self._get_size(a) for a in result.artifacts),
            "duration_seconds": result.duration_seconds,
            "error_count": len(result.errors),
            "warning_count": len(result.warnings),
        }

    def _get_size(self, path: Union[str, Path]) -> int:
        """Get size of file or directory in bytes."""
        path = Path(path)
        if path.is_file():
            return path.stat().st_size
        if path.is_dir():
            return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
        return 0

    # Implement base class abstract methods

    def can_handle(self, context: StrategyContext) -> bool:
        """Check if strategy can handle the given context."""
        # Check if operation is supported
        if context.operation not in self.metadata.supported_operations:
            return False

        # Check if target type is supported
        if self.metadata.supported_types != ["*"]:
            if context.target_type not in self.metadata.supported_types:
                return False

        return True

    def validate_input(self, input_data: Any) -> List[str]:
        """Validate input data for strategy."""
        errors = []

        if not isinstance(input_data, dict):
            errors.append("Input must be a dictionary")
            return errors

        if "source" not in input_data:
            errors.append("Source is required")

        if "target" not in input_data:
            errors.append("Target is required")

        return errors

    def prepare_rollback(self, deployment_info: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare rollback information."""
        return {
            "deployment_id": deployment_info.get("deployment_id"),
            "deployed_path": str(deployment_info.get("deployed_path")),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "artifacts": deployment_info.get("artifacts", []),
        }

    def cleanup(self, target: Union[str, Path]) -> bool:
        """Clean up deployment artifacts."""
        try:
            target_path = Path(target)
            if target_path.exists():
                if target_path.is_file():
                    target_path.unlink()
                elif target_path.is_dir():
                    import shutil

                    shutil.rmtree(target_path)
            return True
        except Exception as e:
            self._logger.error(f"Cleanup failed: {e!s}")
            return False
