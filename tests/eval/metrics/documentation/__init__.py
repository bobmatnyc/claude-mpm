"""
Documentation Agent custom DeepEval metrics.

This package provides specialized metrics for evaluating Documentation Agent compliance:
- ClarityStandardsMetric: Active voice, jargon handling, code examples, conciseness
- AudienceAwarenessMetric: Audience targeting, technical depth, context adaptation
"""

from tests.eval.metrics.documentation.audience_awareness_metric import (
    AudienceAwarenessMetric,
    create_audience_awareness_metric,
)
from tests.eval.metrics.documentation.clarity_standards_metric import (
    ClarityStandardsMetric,
    create_clarity_standards_metric,
)

__all__ = [
    "AudienceAwarenessMetric",
    "ClarityStandardsMetric",
    "create_audience_awareness_metric",
    "create_clarity_standards_metric",
]
