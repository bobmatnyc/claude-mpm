"""
Shared Metric Utilities for Agent Testing.

This module provides base metric classes and utilities for creating
custom DeepEval metrics for agent evaluation.

Design Decision: Base metric classes with template methods

Rationale: All agent metrics share common patterns (threshold checking,
scoring, reason generation). Using base classes reduces duplication and
ensures consistency.

Trade-offs:
- Inheritance depth: Balance between reuse and complexity
- Customization: Template methods allow agent-specific logic
- Consistency: Base class enforces standard metric interface

Example:
    class CodeMinimizationMetric(AgentMetricBase):
        def calculate_score(self, analysis):
            return 1.0 if analysis.net_loc_delta <= 0 else 0.5
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from deepeval.metrics import BaseMetric
from deepeval.test_case import LLMTestCase

from .agent_response_parser import AgentResponseAnalysis, AgentResponseParser, AgentType


class AgentMetricBase(BaseMetric, ABC):
    """
    Base class for all agent evaluation metrics.

    Provides common functionality:
    - Threshold checking
    - Score calculation framework
    - Reason generation
    - Success determination

    Subclasses must implement:
    - calculate_score(): Agent-specific scoring logic
    - generate_reason(): Human-readable explanation

    Example:
        class VerificationMetric(AgentMetricBase):
            metric_name = "Verification Compliance"

            def calculate_score(self, analysis):
                return analysis.verification_compliance_score

            def generate_reason(self, analysis, score):
                return f"{len(analysis.verification_events)} events, {score:.0%} verified"
    """

    metric_name: str = "Base Agent Metric"
    default_threshold: float = 0.9

    def __init__(
        self,
        threshold: float | None = None,
        agent_type: AgentType = AgentType.BASE,
        strict: bool = True,
    ):
        """
        Initialize agent metric.

        Args:
            threshold: Minimum passing score (default: 0.9)
            agent_type: Agent type for specialized parsing
            strict: Strict compliance mode (default: True)
        """
        self.threshold = threshold if threshold is not None else self.default_threshold
        self.agent_type = agent_type
        self.strict = strict
        self.parser = AgentResponseParser()

    @property
    def __name__(self) -> str:
        return self.metric_name

    def measure(self, test_case: LLMTestCase) -> float:
        """
        Measure metric score for test case.

        Args:
            test_case: DeepEval test case with input and actual_output

        Returns:
            Score from 0.0 to 1.0
        """
        # Parse agent response
        analysis = self.parser.parse(test_case.actual_output, self.agent_type)

        # Calculate score using agent-specific logic
        score = self.calculate_score(analysis, test_case)

        # Generate reason
        reason = self.generate_reason(analysis, score, test_case)

        # Set metric state
        self.score = score
        self.reason = reason
        self.success = score >= self.threshold

        return score

    @abstractmethod
    def calculate_score(
        self, analysis: AgentResponseAnalysis, test_case: LLMTestCase
    ) -> float:
        """
        Calculate metric score.

        Subclasses must implement agent-specific scoring logic.

        Args:
            analysis: Parsed agent response
            test_case: DeepEval test case

        Returns:
            Score from 0.0 to 1.0
        """

    @abstractmethod
    def generate_reason(
        self, analysis: AgentResponseAnalysis, score: float, test_case: LLMTestCase
    ) -> str:
        """
        Generate human-readable reason for score.

        Args:
            analysis: Parsed agent response
            score: Calculated score
            test_case: DeepEval test case

        Returns:
            Explanation string
        """

    def is_successful(self) -> bool:
        """Check if metric passes threshold."""
        return self.success

    async def a_measure(self, test_case: LLMTestCase) -> float:
        """Async version of measure."""
        return self.measure(test_case)


class VerificationComplianceMetric(AgentMetricBase):
    """
    Metric for BASE_AGENT verification compliance.

    Evaluates: "Always verify - test functions, APIs, file edits"

    Scoring:
    - 1.0: All actions verified
    - 0.7-0.99: Most actions verified
    - 0.0-0.69: Many unverified actions
    """

    metric_name = "Verification Compliance"
    default_threshold = 0.9

    def calculate_score(
        self, analysis: AgentResponseAnalysis, test_case: LLMTestCase
    ) -> float:
        """Calculate verification compliance score."""
        return analysis.verification_compliance_score

    def generate_reason(
        self, analysis: AgentResponseAnalysis, score: float, test_case: LLMTestCase
    ) -> str:
        """Generate reason for verification score."""
        events = analysis.verification_events
        verified = sum(1 for e in events if e.verified)

        if not events:
            return "No verifiable actions detected"

        if score >= 0.9:
            return f"Excellent: {verified}/{len(events)} actions verified"

        unverified_types = [e.verification_type for e in events if not e.verified]
        return f"Partial: {verified}/{len(events)} verified. Unverified: {', '.join(unverified_types)}"


class MemoryProtocolMetric(AgentMetricBase):
    """
    Metric for BASE_AGENT memory protocol compliance.

    Evaluates: JSON response format with required fields

    Scoring:
    - 1.0: Perfect compliance (all required fields)
    - 0.5: JSON present but missing fields
    - 0.0: No JSON block
    """

    metric_name = "Memory Protocol"
    default_threshold = 1.0  # Strict: require perfect compliance

    def calculate_score(
        self, analysis: AgentResponseAnalysis, test_case: LLMTestCase
    ) -> float:
        """Calculate memory protocol compliance score."""
        return analysis.memory_protocol_score

    def generate_reason(
        self, analysis: AgentResponseAnalysis, score: float, test_case: LLMTestCase
    ) -> str:
        """Generate reason for memory protocol score."""
        memory = analysis.memory_capture

        if not memory.json_block_present:
            return "VIOLATION: No JSON response block found"

        if memory.validation_errors:
            return f"Partial compliance: {', '.join(memory.validation_errors)}"

        return "Perfect compliance: All required fields present"


# ============================================================================
# METRIC UTILITY FUNCTIONS
# ============================================================================


def create_metric_suite(
    agent_type: AgentType, threshold: float = 0.9
) -> List[AgentMetricBase]:
    """
    Create standard metric suite for agent type.

    Args:
        agent_type: Agent type to create metrics for
        threshold: Default threshold for all metrics

    Returns:
        List of configured metrics

    Example:
        metrics = create_metric_suite(AgentType.RESEARCH, threshold=0.85)
        for metric in metrics:
            score = metric.measure(test_case)
            print(f"{metric.__name__}: {score:.2f}")
    """
    # All agents get BASE_AGENT metrics
    metrics = [
        VerificationComplianceMetric(threshold=threshold, agent_type=agent_type),
        MemoryProtocolMetric(threshold=1.0, agent_type=agent_type),  # Always strict
    ]

    # Add agent-specific metrics (will be implemented in Issue #107-#113)
    # if agent_type == AgentType.RESEARCH:
    #     metrics.extend([
    #         MemoryEfficiencyMetric(threshold=threshold),
    #         SamplingStrategyMetric(threshold=threshold),
    #     ])
    # elif agent_type == AgentType.ENGINEER:
    #     metrics.extend([
    #         CodeMinimizationMetric(threshold=threshold),
    #         ConsolidationMetric(threshold=threshold),
    #         AntiPatternDetectionMetric(threshold=1.0),
    #     ])
    # ... etc

    return metrics


def calculate_aggregate_score(
    metrics: List[AgentMetricBase], test_case: LLMTestCase
) -> Dict[str, Any]:
    """
    Calculate aggregate score across multiple metrics.

    Args:
        metrics: List of metrics to evaluate
        test_case: DeepEval test case

    Returns:
        Dict with aggregate score, individual scores, pass/fail

    Example:
        result = calculate_aggregate_score(metrics, test_case)
        print(f"Overall: {result['aggregate_score']:.2f}")
        print(f"Passed: {result['all_passed']}")
    """
    scores = {}
    reasons = {}

    for metric in metrics:
        score = metric.measure(test_case)
        scores[metric.__name__] = score
        reasons[metric.__name__] = metric.reason

    # Calculate aggregate (average)
    aggregate = sum(scores.values()) / len(scores) if scores else 0.0

    # Check if all passed
    all_passed = all(metric.is_successful() for metric in metrics)

    return {
        "aggregate_score": aggregate,
        "individual_scores": scores,
        "reasons": reasons,
        "all_passed": all_passed,
        "metrics_evaluated": len(metrics),
    }


def generate_metric_report(
    metrics: List[AgentMetricBase], test_case: LLMTestCase
) -> str:
    """
    Generate human-readable metric evaluation report.

    Args:
        metrics: List of metrics to evaluate
        test_case: DeepEval test case

    Returns:
        Formatted report string

    Example:
        report = generate_metric_report(metrics, test_case)
        print(report)
    """
    result = calculate_aggregate_score(metrics, test_case)

    lines = [
        "=" * 70,
        "AGENT EVALUATION REPORT",
        "=" * 70,
        f"Overall Score: {result['aggregate_score']:.2%}",
        f"Status: {'PASS' if result['all_passed'] else 'FAIL'}",
        "",
        "Individual Metrics:",
        "-" * 70,
    ]

    for metric_name, score in result["individual_scores"].items():
        status = "✓" if score >= 0.9 else "✗"
        reason = result["reasons"][metric_name]
        lines.append(f"{status} {metric_name}: {score:.2%}")
        lines.append(f"  {reason}")
        lines.append("")

    lines.append("=" * 70)

    return "\n".join(lines)


# ============================================================================
# THRESHOLD UTILITIES
# ============================================================================


class ThresholdPresets:
    """
    Predefined threshold presets for different testing modes.

    Usage:
        metrics = create_metric_suite(
            AgentType.ENGINEER,
            threshold=ThresholdPresets.STRICT
        )
    """

    STRICT = 1.0  # Perfect compliance required
    PRODUCTION = 0.95  # Near-perfect for production
    STANDARD = 0.9  # Standard testing threshold
    LENIENT = 0.8  # Development/exploratory testing
    PERMISSIVE = 0.7  # Very permissive for initial testing


def get_threshold_for_severity(severity: str) -> float:
    """
    Get threshold based on severity level.

    Args:
        severity: "critical", "high", "medium", "low"

    Returns:
        Appropriate threshold

    Example:
        threshold = get_threshold_for_severity("critical")
        assert threshold == 1.0
    """
    thresholds = {
        "critical": ThresholdPresets.STRICT,
        "high": ThresholdPresets.PRODUCTION,
        "medium": ThresholdPresets.STANDARD,
        "low": ThresholdPresets.LENIENT,
    }

    return thresholds.get(severity.lower(), ThresholdPresets.STANDARD)


# ============================================================================
# VIOLATION UTILITIES
# ============================================================================


def extract_violation_summary(analysis: AgentResponseAnalysis) -> Dict[str, Any]:
    """
    Extract violation summary from analysis.

    Args:
        analysis: Parsed agent response

    Returns:
        Dict with violation counts, types, details

    Example:
        summary = extract_violation_summary(analysis)
        if summary["total_violations"] > 0:
            print(f"Found {summary['total_violations']} violations")
    """
    violations = analysis.violations

    # Categorize violations
    categories = {
        "unverified_assertions": [],
        "memory_protocol": [],
        "agent_specific": [],
    }

    for violation in violations:
        if "Unverified assertion" in violation:
            categories["unverified_assertions"].append(violation)
        elif "JSON" in violation or "memory" in violation.lower():
            categories["memory_protocol"].append(violation)
        else:
            categories["agent_specific"].append(violation)

    return {
        "total_violations": len(violations),
        "by_category": {
            k: len(v) for k, v in categories.items() if v
        },
        "details": categories,
        "has_violations": len(violations) > 0,
    }


def format_violations(analysis: AgentResponseAnalysis) -> str:
    """
    Format violations as human-readable text.

    Args:
        analysis: Parsed agent response

    Returns:
        Formatted violation report

    Example:
        report = format_violations(analysis)
        if report:
            print(report)
    """
    summary = extract_violation_summary(analysis)

    if not summary["has_violations"]:
        return "No violations detected ✓"

    lines = [
        f"Found {summary['total_violations']} violations:",
        "",
    ]

    for category, violations_list in summary["details"].items():
        if violations_list:
            lines.append(f"{category.replace('_', ' ').title()}:")
            for violation in violations_list:
                lines.append(f"  - {violation}")
            lines.append("")

    return "\n".join(lines)
