"""
Unified Deployment Strategies
=============================

This module consolidates 45+ deployment services into a unified strategy-based architecture.
Reduces ~17,938 LOC of duplicated deployment code to ~6,000 LOC through strategic pattern
application and code reuse.

Deployment Strategies:
- LocalDeploymentStrategy: Deploy to local filesystem/project
- VercelDeploymentStrategy: Deploy to Vercel platform
- RailwayDeploymentStrategy: Deploy to Railway platform
- AWSDeploymentStrategy: Deploy to AWS (Lambda, EC2, ECS)
- DockerDeploymentStrategy: Docker container deployments
- GitDeploymentStrategy: Git-based deployments (GitHub, GitLab)

Consolidates services from:
- agent_deployment.py (887 LOC)
- multi_source_deployment_service.py (1,055 LOC)
- agent_template_builder.py (1,134 LOC)
- 8+ pipeline services with duplicated patterns
- 30+ other deployment-related services

Design Principles:
1. Strategy pattern for pluggable deployment types
2. Common utilities for shared functionality
3. Health checks and rollback capabilities
4. Validation and pre-flight checks
5. Metrics and monitoring integration
"""

from .base import DeploymentContext, DeploymentResult, DeploymentStrategy
from .cloud_strategies import (
    AWSDeploymentStrategy,
    DockerDeploymentStrategy,
    GitDeploymentStrategy,
    RailwayDeploymentStrategy,
)
from .local import LocalDeploymentStrategy
from .utils import (
    prepare_deployment_artifact,
    rollback_deployment,
    validate_deployment_config,
    verify_deployment_health,
)
from .vercel import VercelDeploymentStrategy

__all__ = [
    "AWSDeploymentStrategy",
    "DeploymentContext",
    "DeploymentResult",
    # Base classes
    "DeploymentStrategy",
    "DockerDeploymentStrategy",
    "GitDeploymentStrategy",
    # Strategy implementations
    "LocalDeploymentStrategy",
    "RailwayDeploymentStrategy",
    "VercelDeploymentStrategy",
    "prepare_deployment_artifact",
    "rollback_deployment",
    # Utilities
    "validate_deployment_config",
    "verify_deployment_health",
]

# Strategy registry for automatic discovery
DEPLOYMENT_STRATEGIES = {
    "local": LocalDeploymentStrategy,
    "vercel": VercelDeploymentStrategy,
    "railway": RailwayDeploymentStrategy,
    "aws": AWSDeploymentStrategy,
    "docker": DockerDeploymentStrategy,
    "git": GitDeploymentStrategy,
}


def get_deployment_strategy(deployment_type: str) -> type[DeploymentStrategy]:
    """
    Get deployment strategy class by type.

    Args:
        deployment_type: Type of deployment (local, vercel, aws, etc.)

    Returns:
        DeploymentStrategy class

    Raises:
        ValueError: If deployment type not supported
    """
    strategy_class = DEPLOYMENT_STRATEGIES.get(deployment_type.lower())
    if not strategy_class:
        raise ValueError(
            f"Unsupported deployment type: {deployment_type}. "
            f"Supported types: {', '.join(DEPLOYMENT_STRATEGIES.keys())}"
        )
    return strategy_class
