"""
Unified Deployment Service Implementation
=========================================

This module implements the unified deployment service that consolidates all
deployment-related services using the strategy pattern. It replaces multiple
specialized deployment services with a single, extensible service.

Consolidates:
- AgentDeploymentService
- ConfigDeploymentService
- ResourceDeploymentService
- TemplateDeploymentService
- And other deployment-related services

Features:
- Strategy-based deployment for different resource types
- Rollback support with versioning
- Batch deployment operations
- Deployment validation and pre-flight checks
- Metrics and monitoring integration
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from claude_mpm.core.enums import OperationResult, ServiceState
from claude_mpm.core.logging_utils import get_logger

from .interfaces import (
    DeploymentResult,
    IDeploymentService,
    IUnifiedService,
    ServiceCapability,
    ServiceMetadata,
)
from .strategies import DeploymentStrategy, StrategyContext, get_strategy_registry


class UnifiedDeploymentService(IDeploymentService, IUnifiedService):
    """
    Unified deployment service using strategy pattern.

    This service consolidates all deployment operations through a
    pluggable strategy system, reducing code duplication and improving
    maintainability.
    """

    def __init__(self):
        """Initialize unified deployment service."""
        self._logger = get_logger(f"{__name__}.UnifiedDeploymentService")
        self._registry = get_strategy_registry()
        self._deployments: Dict[str, Dict[str, Any]] = {}
        self._deployment_counter = 0
        self._metrics = {
            "total_deployments": 0,
            "successful_deployments": 0,
            "failed_deployments": 0,
            "rollbacks": 0,
        }
        self._initialized = False

    def get_metadata(self) -> ServiceMetadata:
        """
        Get service metadata.

        Returns:
            ServiceMetadata: Service metadata
        """
        return ServiceMetadata(
            name="UnifiedDeploymentService",
            version="1.0.0",
            capabilities={
                ServiceCapability.ASYNC_OPERATIONS,
                ServiceCapability.BATCH_PROCESSING,
                ServiceCapability.VALIDATION,
                ServiceCapability.ROLLBACK,
                ServiceCapability.METRICS,
                ServiceCapability.HEALTH_CHECK,
            },
            dependencies=["StrategyRegistry", "LoggingService"],
            description="Unified service for all deployment operations",
            tags={"deployment", "unified", "strategy-pattern"},
            deprecated_services=[
                "AgentDeploymentService",
                "ConfigDeploymentService",
                "ResourceDeploymentService",
                "TemplateDeploymentService",
            ],
        )

    async def initialize(self) -> bool:
        """
        Initialize the service.

        Returns:
            bool: True if initialization successful
        """
        try:
            self._logger.info("Initializing UnifiedDeploymentService")

            # Load deployment history if exists
            await self._load_deployment_history()

            # Register default strategies
            self._register_default_strategies()

            self._initialized = True
            self._logger.info("UnifiedDeploymentService initialized successfully")
            return True

        except Exception as e:
            self._logger.error(f"Failed to initialize: {e!s}")
            return False

    async def shutdown(self) -> None:
        """Gracefully shutdown the service."""
        self._logger.info("Shutting down UnifiedDeploymentService")

        # Save deployment history
        await self._save_deployment_history()

        # Clear deployments
        self._deployments.clear()

        self._initialized = False
        self._logger.info("UnifiedDeploymentService shutdown complete")

    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check.

        Returns:
            Dict[str, Any]: Health status
        """
        strategies = self._registry.list_strategies(DeploymentStrategy)

        return {
            "service": "UnifiedDeploymentService",
            "status": ServiceState.RUNNING if self._initialized else ServiceState.ERROR,
            "initialized": self._initialized,
            "registered_strategies": len(strategies),
            "active_deployments": len(self._deployments),
            "metrics": self.get_metrics(),
        }

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get service metrics.

        Returns:
            Dict[str, Any]: Service metrics
        """
        success_rate = 0.0
        if self._metrics["total_deployments"] > 0:
            success_rate = (
                self._metrics["successful_deployments"]
                / self._metrics["total_deployments"]
            ) * 100

        return {
            **self._metrics,
            "success_rate": success_rate,
            "active_deployments": len(self._deployments),
        }

    def reset(self) -> None:
        """Reset service to initial state."""
        self._logger.info("Resetting UnifiedDeploymentService")
        self._deployments.clear()
        self._deployment_counter = 0
        self._metrics = {
            "total_deployments": 0,
            "successful_deployments": 0,
            "failed_deployments": 0,
            "rollbacks": 0,
        }

    def validate_deployment(
        self, target: Union[str, Path], config: Dict[str, Any]
    ) -> List[str]:
        """
        Validate deployment configuration.

        Args:
            target: Deployment target
            config: Deployment configuration

        Returns:
            List[str]: Validation errors
        """
        errors = []

        # Basic validation
        if not target:
            errors.append("Deployment target is required")

        if not config:
            errors.append("Deployment configuration is required")

        # Get deployment type from config
        deployment_type = config.get("type", "unknown")

        # Select appropriate strategy
        context = StrategyContext(
            target_type=deployment_type,
            operation="validate",
            parameters={"target": target, "config": config},
        )

        strategy = self._registry.select_strategy(DeploymentStrategy, context)

        if not strategy:
            errors.append(
                f"No strategy available for deployment type: {deployment_type}"
            )
        else:
            # Delegate validation to strategy
            strategy_errors = strategy.validate_input(config)
            errors.extend(strategy_errors)

        return errors

    def deploy(
        self,
        source: Union[str, Path],
        target: Union[str, Path],
        config: Optional[Dict[str, Any]] = None,
        force: bool = False,
    ) -> DeploymentResult:
        """
        Execute deployment.

        Args:
            source: Deployment source
            target: Deployment target
            config: Deployment configuration
            force: Force deployment

        Returns:
            DeploymentResult: Deployment result
        """
        config = config or {}
        self._metrics["total_deployments"] += 1

        try:
            # Validate deployment
            errors = self.validate_deployment(target, config)
            if errors and not force:
                self._metrics["failed_deployments"] += 1
                return DeploymentResult(
                    success=False,
                    message=f"Validation failed: {'; '.join(errors)}",
                )

            # Get deployment type
            deployment_type = config.get("type", "generic")

            # Select deployment strategy
            context = StrategyContext(
                target_type=deployment_type,
                operation="deploy",
                parameters={
                    "source": source,
                    "target": target,
                    "config": config,
                    "force": force,
                },
            )

            strategy = self._registry.select_strategy(DeploymentStrategy, context)

            if not strategy:
                self._metrics["failed_deployments"] += 1
                return DeploymentResult(
                    success=False,
                    message=f"No strategy available for deployment type: {deployment_type}",
                )

            # Execute deployment using strategy
            self._logger.info(
                f"Deploying {source} to {target} using {strategy.metadata.name}"
            )

            result = strategy.deploy(source, target, config)

            # Create deployment record
            deployment_id = self._generate_deployment_id()
            rollback_info = strategy.prepare_rollback(result)

            self._deployments[deployment_id] = {
                "id": deployment_id,
                "source": str(source),
                "target": str(target),
                "type": deployment_type,
                "strategy": strategy.metadata.name,
                "config": config,
                "result": result,
                "rollback_info": rollback_info,
                "timestamp": self._get_timestamp(),
            }

            # Update metrics
            if result.get(OperationResult.SUCCESS.value, False):
                self._metrics["successful_deployments"] += 1
                deployed_path = Path(target) / Path(source).name

                return DeploymentResult(
                    success=True,
                    deployed_path=deployed_path,
                    message=f"Successfully deployed using {strategy.metadata.name}",
                    metadata=result,
                    rollback_info=rollback_info,
                )
            self._metrics["failed_deployments"] += 1
            return DeploymentResult(
                success=False,
                message=result.get(OperationResult.ERROR.value, "Deployment failed"),
                metadata=result,
            )

        except Exception as e:
            self._logger.error(f"Deployment error: {e!s}")
            self._metrics["failed_deployments"] += 1
            return DeploymentResult(
                success=False,
                message=f"Deployment failed: {e!s}",
            )

    def rollback(
        self, deployment_id: str, rollback_info: Dict[str, Any]
    ) -> DeploymentResult:
        """
        Rollback deployment.

        Args:
            deployment_id: Deployment to rollback
            rollback_info: Rollback information

        Returns:
            DeploymentResult: Rollback result
        """
        self._metrics["rollbacks"] += 1

        deployment = self._deployments.get(deployment_id)
        if not deployment:
            return DeploymentResult(
                success=False,
                message=f"Deployment {deployment_id} not found",
            )

        try:
            # Get the strategy used for deployment
            strategy_name = deployment["strategy"]
            strategy = self._registry.get_strategy(DeploymentStrategy, strategy_name)

            if not strategy:
                return DeploymentResult(
                    success=False,
                    message=f"Strategy {strategy_name} not available for rollback",
                )

            # Execute rollback
            self._logger.info(f"Rolling back deployment {deployment_id}")

            # Clean up deployed artifacts
            success = strategy.cleanup(deployment["target"])

            if success:
                # Mark deployment as rolled back
                deployment["rolled_back"] = True
                deployment["rollback_timestamp"] = self._get_timestamp()

                return DeploymentResult(
                    success=True,
                    message=f"Successfully rolled back deployment {deployment_id}",
                )
            return DeploymentResult(
                success=False,
                message="Rollback failed",
            )

        except Exception as e:
            self._logger.error(f"Rollback error: {e!s}")
            return DeploymentResult(
                success=False,
                message=f"Rollback failed: {e!s}",
            )

    def list_deployments(
        self, target: Optional[Union[str, Path]] = None
    ) -> List[Dict[str, Any]]:
        """
        List deployments.

        Args:
            target: Optional filter by target

        Returns:
            List[Dict[str, Any]]: Deployment list
        """
        deployments = list(self._deployments.values())

        if target:
            target_str = str(target)
            deployments = [d for d in deployments if d["target"] == target_str]

        return deployments

    def get_deployment_status(self, deployment_id: str) -> Dict[str, Any]:
        """
        Get deployment status.

        Args:
            deployment_id: Deployment identifier

        Returns:
            Dict[str, Any]: Deployment status
        """
        deployment = self._deployments.get(deployment_id)
        if not deployment:
            return {"error": f"Deployment {deployment_id} not found"}

        return {
            "id": deployment_id,
            "status": (
                OperationResult.CANCELLED
                if deployment.get("rolled_back")
                else OperationResult.SUCCESS
            ),
            "type": deployment["type"],
            "strategy": deployment["strategy"],
            "source": deployment["source"],
            "target": deployment["target"],
            "timestamp": deployment["timestamp"],
            "rollback_available": bool(deployment.get("rollback_info")),
        }

    # Private helper methods

    def _register_default_strategies(self) -> None:
        """Register default deployment strategies."""
        # Default strategies would be registered here
        # This would be extended with actual strategy implementations
        self._logger.debug("Default strategies registered")

    async def _load_deployment_history(self) -> None:
        """Load deployment history from persistent storage."""
        # Implementation would load from database or file
        self._logger.debug("Deployment history loaded")

    async def _save_deployment_history(self) -> None:
        """Save deployment history to persistent storage."""
        # Implementation would save to database or file
        self._logger.debug("Deployment history saved")

    def _generate_deployment_id(self) -> str:
        """Generate unique deployment ID."""
        self._deployment_counter += 1
        return f"deploy_{self._deployment_counter:06d}"

    def _get_timestamp(self) -> str:
        """Get current timestamp."""
        from datetime import datetime, timezone

        return datetime.now(timezone.utc).isoformat()
