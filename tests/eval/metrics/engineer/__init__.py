"""
Engineer Agent Custom DeepEval Metrics.

This module provides specialized metrics for testing Engineer Agent behaviors:

1. CodeMinimizationMetric: Validates code minimization mandate
   - Search-first workflow (vector search/grep before implementation)
   - LOC delta reporting (net lines added/removed)
   - Reuse rate tracking (leveraging existing code)
   - Consolidation opportunities (identifying duplicates)
   - Config vs code approach (configuration-driven solutions)

2. ConsolidationMetric: Validates consolidation protocol
   - Duplicate detection (searching for similar code)
   - Consolidation decision quality (>80% same domain, >50% shared)
   - Implementation quality (merge protocol, reference updates)
   - Single-path enforcement (one implementation per feature)
   - Session artifact cleanup (removing _old, _v2, _backup files)

3. AntiPatternDetectionMetric: Validates anti-pattern avoidance
   - No mock data in production (mock/dummy only in tests)
   - No silent fallbacks (explicit error handling)
   - Explicit error propagation (log + raise)
   - Acceptable fallback justification (config defaults, documented)

Usage:
    from tests.eval.metrics.engineer import (
        CodeMinimizationMetric,
        ConsolidationMetric,
        AntiPatternDetectionMetric
    )

    # Create metrics
    code_min = CodeMinimizationMetric(threshold=0.8)
    consolidation = ConsolidationMetric(threshold=0.85)
    anti_pattern = AntiPatternDetectionMetric(threshold=0.9)

    # Measure against test case
    score = code_min.measure(test_case)
"""

from tests.eval.metrics.engineer.anti_pattern_detection_metric import (
    AntiPatternDetectionMetric,
    create_anti_pattern_detection_metric,
)
from tests.eval.metrics.engineer.code_minimization_metric import (
    CodeMinimizationMetric,
    create_code_minimization_metric,
)
from tests.eval.metrics.engineer.consolidation_metric import (
    ConsolidationMetric,
    create_consolidation_metric,
)

__all__ = [
    "AntiPatternDetectionMetric",
    "CodeMinimizationMetric",
    "ConsolidationMetric",
    "create_anti_pattern_detection_metric",
    "create_code_minimization_metric",
    "create_consolidation_metric",
]
