"""
Unified Analyzer Service Implementation
=======================================

This module implements the unified analyzer service that consolidates all
analysis-related services using the strategy pattern. It replaces multiple
specialized analyzer services with a single, extensible service.

Consolidates:
- CodeAnalyzer
- ComplexityAnalyzer
- DependencyAnalyzer
- PerformanceAnalyzer
- SecurityAnalyzer
- And other analysis-related services

Features:
- Strategy-based analysis for different target types
- Batch analysis operations
- Comparative analysis
- Metrics extraction and aggregation
- Recommendation generation
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from claude_mpm.core.enums import OperationResult, ServiceState, ValidationSeverity
from claude_mpm.core.logging_utils import get_logger

from .interfaces import (
    AnalysisResult,
    IAnalyzerService,
    IUnifiedService,
    ServiceCapability,
    ServiceMetadata,
)
from .strategies import AnalyzerStrategy, StrategyContext, get_strategy_registry


class UnifiedAnalyzer(IAnalyzerService, IUnifiedService):
    """
    Unified analyzer service using strategy pattern.

    This service consolidates all analysis operations through a
    pluggable strategy system, enabling consistent analysis interfaces
    across different target types.
    """

    def __init__(self):
        """Initialize unified analyzer service."""
        self._logger = get_logger(f"{__name__}.UnifiedAnalyzer")
        self._registry = get_strategy_registry()
        self._analysis_cache: Dict[str, AnalysisResult] = {}
        self._metrics = {
            "total_analyses": 0,
            "cached_hits": 0,
            "analysis_errors": 0,
            "batch_operations": 0,
        }
        self._initialized = False

    def get_metadata(self) -> ServiceMetadata:
        """
        Get service metadata.

        Returns:
            ServiceMetadata: Service metadata
        """
        return ServiceMetadata(
            name="UnifiedAnalyzer",
            version="1.0.0",
            capabilities={
                ServiceCapability.ASYNC_OPERATIONS,
                ServiceCapability.BATCH_PROCESSING,
                ServiceCapability.CACHING,
                ServiceCapability.VALIDATION,
                ServiceCapability.METRICS,
                ServiceCapability.HEALTH_CHECK,
            },
            dependencies=["StrategyRegistry", "LoggingService"],
            description="Unified service for all analysis operations",
            tags={"analysis", "unified", "strategy-pattern"},
            deprecated_services=[
                "CodeAnalyzer",
                "ComplexityAnalyzer",
                "DependencyAnalyzer",
                "PerformanceAnalyzer",
                "SecurityAnalyzer",
            ],
        )

    async def initialize(self) -> bool:
        """
        Initialize the service.

        Returns:
            bool: True if initialization successful
        """
        try:
            self._logger.info("Initializing UnifiedAnalyzer")

            # Register default strategies
            self._register_default_strategies()

            # Initialize analysis cache
            self._analysis_cache.clear()

            self._initialized = True
            self._logger.info("UnifiedAnalyzer initialized successfully")
            return True

        except Exception as e:
            self._logger.error(f"Failed to initialize: {e!s}")
            return False

    async def shutdown(self) -> None:
        """Gracefully shutdown the service."""
        self._logger.info("Shutting down UnifiedAnalyzer")

        # Clear analysis cache
        self._analysis_cache.clear()

        self._initialized = False
        self._logger.info("UnifiedAnalyzer shutdown complete")

    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check.

        Returns:
            Dict[str, Any]: Health status
        """
        strategies = self._registry.list_strategies(AnalyzerStrategy)

        return {
            "service": "UnifiedAnalyzer",
            "status": ServiceState.RUNNING if self._initialized else ServiceState.ERROR,
            "initialized": self._initialized,
            "registered_strategies": len(strategies),
            "cache_size": len(self._analysis_cache),
            "metrics": self.get_metrics(),
        }

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get service metrics.

        Returns:
            Dict[str, Any]: Service metrics
        """
        cache_hit_rate = 0.0
        if self._metrics["total_analyses"] > 0:
            cache_hit_rate = (
                self._metrics["cached_hits"] / self._metrics["total_analyses"]
            ) * 100

        error_rate = 0.0
        if self._metrics["total_analyses"] > 0:
            error_rate = (
                self._metrics["analysis_errors"] / self._metrics["total_analyses"]
            ) * 100

        return {
            **self._metrics,
            "cache_hit_rate": cache_hit_rate,
            "error_rate": error_rate,
            "cache_entries": len(self._analysis_cache),
        }

    def reset(self) -> None:
        """Reset service to initial state."""
        self._logger.info("Resetting UnifiedAnalyzer")
        self._analysis_cache.clear()
        self._metrics = {
            "total_analyses": 0,
            "cached_hits": 0,
            "analysis_errors": 0,
            "batch_operations": 0,
        }

    def analyze(
        self,
        target: Union[str, Path, Any],
        options: Optional[Dict[str, Any]] = None,
    ) -> AnalysisResult:
        """
        Perform analysis on target.

        Args:
            target: Target to analyze
            options: Analysis options

        Returns:
            AnalysisResult: Analysis result
        """
        options = options or {}
        self._metrics["total_analyses"] += 1

        try:
            # Check cache
            cache_key = self._generate_cache_key(target, options)
            if cache_key in self._analysis_cache and not options.get(
                "force_refresh", False
            ):
                self._metrics["cached_hits"] += 1
                self._logger.debug(f"Returning cached analysis for {target}")
                return self._analysis_cache[cache_key]

            # Determine analysis type
            analysis_type = self._determine_analysis_type(target, options)

            # Select analysis strategy
            context = StrategyContext(
                target_type=analysis_type,
                operation="analyze",
                parameters={"target": target, "options": options},
            )

            strategy = self._registry.select_strategy(AnalyzerStrategy, context)

            if not strategy:
                self._metrics["analysis_errors"] += 1
                return AnalysisResult(
                    success=False,
                    summary=f"No strategy available for analysis type: {analysis_type}",
                    severity=ValidationSeverity.ERROR,
                )

            # Execute analysis using strategy
            self._logger.info(f"Analyzing {target} using {strategy.metadata.name}")

            # Validate input
            validation_errors = strategy.validate_input(target)
            if validation_errors:
                self._metrics["analysis_errors"] += 1
                return AnalysisResult(
                    success=False,
                    summary=f"Validation failed: {'; '.join(validation_errors)}",
                    severity=ValidationSeverity.ERROR,
                )

            # Perform analysis
            result_data = strategy.analyze(target, options)

            # Extract metrics
            metrics = strategy.extract_metrics(result_data)

            # Create analysis result
            result = AnalysisResult(
                success=True,
                findings=result_data.get("findings", []),
                metrics=metrics,
                summary=result_data.get("summary", "Analysis completed"),
                severity=result_data.get("severity", ValidationSeverity.INFO),
                recommendations=result_data.get("recommendations", []),
            )

            # Cache result
            self._analysis_cache[cache_key] = result

            return result

        except Exception as e:
            self._logger.error(f"Analysis error: {e!s}")
            self._metrics["analysis_errors"] += 1
            return AnalysisResult(
                success=False,
                summary=f"Analysis failed: {e!s}",
                severity="error",
            )

    def batch_analyze(
        self,
        targets: List[Union[str, Path, Any]],
        options: Optional[Dict[str, Any]] = None,
    ) -> List[AnalysisResult]:
        """
        Perform batch analysis.

        Args:
            targets: List of targets
            options: Analysis options

        Returns:
            List[AnalysisResult]: Results for each target
        """
        self._metrics["batch_operations"] += 1
        results = []

        self._logger.info(f"Starting batch analysis of {len(targets)} targets")

        for target in targets:
            result = self.analyze(target, options)
            results.append(result)

        # Aggregate metrics across all results
        self._aggregate_batch_metrics(results)

        return results

    def get_metrics(self, target: Union[str, Path, Any]) -> Dict[str, Any]:
        """
        Get analysis metrics for target.

        Args:
            target: Target to get metrics for

        Returns:
            Dict[str, Any]: Analysis metrics
        """
        # Check if we have cached analysis
        cache_key = self._generate_cache_key(target, {})
        if cache_key in self._analysis_cache:
            return self._analysis_cache[cache_key].metrics

        # Perform fresh analysis to get metrics
        result = self.analyze(target, {"metrics_only": True})
        return result.metrics if result.success else {}

    def compare(
        self,
        target1: Union[str, Path, Any],
        target2: Union[str, Path, Any],
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Compare two targets.

        Args:
            target1: First target
            target2: Second target
            options: Comparison options

        Returns:
            Dict[str, Any]: Comparison results
        """
        options = options or {}

        try:
            # Analyze both targets
            result1 = self.analyze(target1, options)
            result2 = self.analyze(target2, options)

            if not result1.success or not result2.success:
                return {
                    OperationResult.SUCCESS.value: False,
                    OperationResult.ERROR.value: "Failed to analyze one or both targets",
                }

            # Compare metrics
            metric_diff = self._compare_metrics(result1.metrics, result2.metrics)

            # Compare findings
            finding_diff = self._compare_findings(result1.findings, result2.findings)

            return {
                OperationResult.SUCCESS.value: True,
                "target1": str(target1),
                "target2": str(target2),
                "metric_differences": metric_diff,
                "finding_differences": finding_diff,
                "severity_comparison": {
                    "target1": result1.severity,
                    "target2": result2.severity,
                },
                "recommendation_diff": {
                    "unique_to_target1": list(
                        set(result1.recommendations) - set(result2.recommendations)
                    ),
                    "unique_to_target2": list(
                        set(result2.recommendations) - set(result1.recommendations)
                    ),
                    "common": list(
                        set(result1.recommendations) & set(result2.recommendations)
                    ),
                },
            }

        except Exception as e:
            self._logger.error(f"Comparison error: {e!s}")
            return {
                OperationResult.SUCCESS.value: False,
                OperationResult.ERROR.value: str(e),
            }

    def get_recommendations(
        self, analysis_result: AnalysisResult
    ) -> List[Dict[str, Any]]:
        """
        Get recommendations from analysis.

        Args:
            analysis_result: Analysis result

        Returns:
            List[Dict[str, Any]]: Recommendations
        """
        recommendations = []

        # Basic recommendations from result
        for rec in analysis_result.recommendations:
            recommendations.append(
                {
                    "type": "general",
                    "description": rec,
                    "priority": "medium",
                }
            )

        # Add severity-based recommendations
        if analysis_result.severity == ValidationSeverity.CRITICAL:
            recommendations.insert(
                0,
                {
                    "type": "urgent",
                    "description": "Critical issues found - immediate attention required",
                    "priority": "high",
                },
            )
        elif analysis_result.severity == ValidationSeverity.ERROR:
            recommendations.insert(
                0,
                {
                    "type": "important",
                    "description": "Errors found - should be addressed soon",
                    "priority": "high",
                },
            )

        # Add metric-based recommendations
        if analysis_result.metrics:
            metric_recs = self._generate_metric_recommendations(analysis_result.metrics)
            recommendations.extend(metric_recs)

        return recommendations

    # Private helper methods

    def _register_default_strategies(self) -> None:
        """Register default analyzer strategies."""
        # Default strategies would be registered here
        # This would be extended with actual strategy implementations
        self._logger.debug("Default strategies registered")

    def _determine_analysis_type(self, target: Any, options: Dict[str, Any]) -> str:
        """
        Determine analysis type from target and options.

        Args:
            target: Analysis target
            options: Analysis options

        Returns:
            str: Analysis type
        """
        # Check if type is explicitly specified
        if "type" in options:
            return options["type"]

        # Infer from target type
        if isinstance(target, (Path, str)):
            path = Path(target)
            if path.is_file():
                # Determine by file extension
                if path.suffix in [".py", ".js", ".ts", ".java"]:
                    return "code"
                if path.suffix in [".json", ".yaml", ".yml"]:
                    return "config"
            elif path.is_dir():
                return "project"

        return "generic"

    def _generate_cache_key(self, target: Any, options: Dict[str, Any]) -> str:
        """Generate cache key for analysis."""
        import hashlib
        import json

        key_data = {
            "target": str(target),
            "options": options,
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_str.encode()).hexdigest()

    def _aggregate_batch_metrics(self, results: List[AnalysisResult]) -> None:
        """Aggregate metrics from batch analysis."""
        # Implementation would aggregate metrics across results

    def _compare_metrics(
        self, metrics1: Dict[str, Any], metrics2: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Compare two sets of metrics."""
        diff = {}
        all_keys = set(metrics1.keys()) | set(metrics2.keys())

        for key in all_keys:
            val1 = metrics1.get(key)
            val2 = metrics2.get(key)

            if val1 != val2:
                diff[key] = {"target1": val1, "target2": val2}

        return diff

    def _compare_findings(
        self, findings1: List[Dict[str, Any]], findings2: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Compare two sets of findings."""
        return {
            "target1_count": len(findings1),
            "target2_count": len(findings2),
            "difference": len(findings1) - len(findings2),
        }

    def _generate_metric_recommendations(
        self, metrics: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate recommendations based on metrics."""
        recommendations = []

        # Example metric-based recommendations
        if metrics.get("complexity", 0) > 10:
            recommendations.append(
                {
                    "type": "complexity",
                    "description": "Consider refactoring to reduce complexity",
                    "priority": "medium",
                }
            )

        if metrics.get("code_duplication", 0) > 20:
            recommendations.append(
                {
                    "type": "duplication",
                    "description": "High code duplication detected - consider extracting common functionality",
                    "priority": "medium",
                }
            )

        return recommendations
