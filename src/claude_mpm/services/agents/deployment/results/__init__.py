"""Deployment results management.

This module provides classes for building and managing deployment results,
including metrics collection and result formatting.
"""

from .deployment_metrics import DeploymentMetrics
from .deployment_result_builder import DeploymentResultBuilder

__all__ = [
    "DeploymentMetrics",
    "DeploymentResultBuilder",
]
