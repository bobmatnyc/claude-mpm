"""
RefactoringQualityMetric for Prompt-Engineer Agent.

Validates that the agent produces high-quality prompt refactoring:
1. Before/after comparison (shows improvement)
2. Quality rubric application (8-criteria scoring)
3. Improvement prioritization (by impact)
4. Claude 4.5 alignment (2025 best practices)
5. Evidence-based recommendations

Scoring based on comprehensive refactoring approach.
"""

import re
from typing import Any

from deepeval.metrics import BaseMetric
from deepeval.test_case import LLMTestCase


class RefactoringQualityMetric(BaseMetric):
    """
    Metric for evaluating prompt refactoring quality.

    Scoring Components (weighted):
    - Before/after comparison (0.25): Shows clear improvement
    - Quality rubric (0.20): Uses scoring criteria
    - Improvement prioritization (0.20): Orders by impact
    - Claude 4.5 alignment (0.20): Modern best practices
    - Evidence-based recommendations (0.15): Justifies changes

    Threshold: 0.80 (comprehensive refactoring quality)
    """

    def __init__(self, threshold: float = 0.80, include_reason: bool = True):
        """Initialize the RefactoringQualityMetric."""
        self.threshold = threshold
        self.include_reason = include_reason
        self._score: float | None = None
        self._reason: str | None = None

    @property
    def __name__(self) -> str:
        """Return metric name."""
        return "RefactoringQualityMetric"

    @property
    def score(self) -> float:
        """Return the computed score."""
        return self._score if self._score is not None else 0.0

    @property
    def reason(self) -> str:
        """Return the reason for the score."""
        return self._reason if self._reason is not None else ""

    def is_successful(self) -> bool:
        """Check if the metric passed the threshold."""
        return self._score is not None and self._score >= self.threshold

    def _evaluate_before_after(self, output: str) -> tuple[float, list[str]]:
        """
        Evaluate before/after comparison presence.

        Returns score and list of issues found.
        """
        issues: list[str] = []
        score = 0.0

        # Patterns indicating before/after comparison
        comparison_patterns = [
            r"before[:\s].*after",
            r"original[:\s].*(?:refactor|improv|new)",
            r"(?:was|were)[:\s].*(?:now|is|are)",
            r"(?:old|previous)[:\s].*(?:new|current)",
            r"improvement.*(?:from|to)",
            r"(?:transform|convert).*(?:from|to)",
            r"(?:replaced|changed).*(?:with|to)",
        ]

        comparison_found = any(
            re.search(pattern, output.lower()) for pattern in comparison_patterns
        )

        # Check for quantitative comparison
        quantitative_patterns = [
            r"\d+\s*(?:lines?|tokens?|%).*\d+\s*(?:lines?|tokens?|%)",
            r"(?:from|was)\s+\d+.*(?:to|now)\s+\d+",
            r"(?:reduc|improv).*\d+%",
        ]

        quantitative_found = any(
            re.search(pattern, output.lower()) for pattern in quantitative_patterns
        )

        if comparison_found and quantitative_found:
            score = 1.0
        elif comparison_found:
            score = 0.7
            issues.append("Comparison present but no quantitative metrics")
        elif quantitative_found:
            score = 0.6
            issues.append("Metrics present but no explicit before/after structure")
        else:
            score = 0.2
            issues.append("No before/after comparison found")

        return score, issues

    def _evaluate_quality_rubric(self, output: str) -> tuple[float, list[str]]:
        """
        Evaluate quality rubric application.

        Returns score and list of issues found.
        """
        issues: list[str] = []
        score = 0.0

        # Patterns indicating rubric usage
        rubric_patterns = [
            r"(?:rubric|criteria|score|rating)",
            r"(?:1|2|3|4|5)(?:\s*/\s*5|\s+out\s+of\s+5)",
            r"(?:clarity|specific|measur|actionable|correct|consistent|complet|maintain)",
            r"(?:average|overall).*(?:score|\d+\.\d+)",
            r"(?:evaluat|assess|review).*(?:criteria|rubric)",
            r"(?:8|eight).*criteria",
        ]

        rubric_found = any(
            re.search(pattern, output.lower()) for pattern in rubric_patterns
        )

        # Check for specific criteria mentions
        criteria_patterns = [
            r"clarity",
            r"specific(?:ity)?",
            r"measurable",
            r"actionable",
            r"correct(?:ness)?",
            r"consisten(?:t|cy)",
            r"complete(?:ness)?",
            r"maintain(?:able|ability)",
        ]

        criteria_count = sum(
            1 for p in criteria_patterns if re.search(p, output.lower())
        )

        if rubric_found and criteria_count >= 4:
            score = 1.0
        elif rubric_found or criteria_count >= 3:
            score = 0.7
            if criteria_count < 4:
                issues.append(f"Only {criteria_count}/8 quality criteria mentioned")
        elif criteria_count >= 1:
            score = 0.4
            issues.append("Some criteria mentioned but no formal rubric application")
        else:
            score = 0.2
            issues.append("No quality rubric or criteria application found")

        return score, issues

    def _evaluate_prioritization(self, output: str) -> tuple[float, list[str]]:
        """
        Evaluate improvement prioritization.

        Returns score and list of issues found.
        """
        issues: list[str] = []
        score = 0.0

        # Patterns indicating prioritization
        priority_patterns = [
            r"(?:priorit|order|rank|sort).*(?:impact|import|critic)",
            r"(?:high|medium|low).*(?:impact|priority)",
            r"(?:first|second|third|finally)",
            r"(?:most|least).*import",
            r"(?:1\.|2\.|3\.|\(1\)|\(2\)|\(3\))",
            r"(?:critical|essential|optional)",
            r"(?:must|should|could|nice-to-have)",
        ]

        priority_found = any(
            re.search(pattern, output.lower()) for pattern in priority_patterns
        )

        # Check for structured list format
        list_patterns = [
            r"^\s*[-*]\s+",
            r"^\s*\d+\.\s+",
            r"(?:step\s+\d+|phase\s+\d+)",
        ]

        list_found = any(
            re.search(pattern, output, re.MULTILINE) for pattern in list_patterns
        )

        if priority_found and list_found:
            score = 1.0
        elif priority_found:
            score = 0.7
            issues.append("Prioritization mentioned but not clearly structured")
        elif list_found:
            score = 0.5
            issues.append("Structured list present but no prioritization criteria")
        else:
            score = 0.2
            issues.append("No improvement prioritization found")

        return score, issues

    def _evaluate_claude45_alignment(self, output: str) -> tuple[float, list[str]]:
        """
        Evaluate Claude 4.5 best practices alignment.

        Returns score and list of issues found.
        """
        issues: list[str] = []
        score = 0.0

        # Patterns indicating Claude 4.5 alignment
        claude45_patterns = [
            r"claude\s+4\.?5",
            r"(?:2025|modern|current).*(?:best\s+practice|pattern)",
            r"extended.*think",
            r"parallel.*tool",
            r"structured.*output",
            r"(?:direct|concise).*(?:style|communication)",
            r"(?:no|without|avoid).*emoji",
            r"(?:xml|json).*(?:schema|output)",
        ]

        claude45_count = sum(
            1 for p in claude45_patterns if re.search(p, output.lower())
        )

        if claude45_count >= 4:
            score = 1.0
        elif claude45_count >= 2:
            score = 0.7
            issues.append(f"Only {claude45_count}/8 Claude 4.5 practices mentioned")
        elif claude45_count >= 1:
            score = 0.4
            issues.append("Minimal Claude 4.5 alignment awareness")
        else:
            # Check for general best practices
            general_patterns = [
                r"best\s+practice",
                r"modern",
                r"current",
            ]
            if any(re.search(p, output.lower()) for p in general_patterns):
                score = 0.3
                issues.append("General best practices mentioned but no Claude 4.5 specifics")
            else:
                score = 0.2
                issues.append("No Claude 4.5 alignment awareness found")

        return score, issues

    def _evaluate_evidence_based(self, output: str) -> tuple[float, list[str]]:
        """
        Evaluate evidence-based recommendations.

        Returns score and list of issues found.
        """
        issues: list[str] = []
        score = 0.0

        # Patterns indicating evidence-based recommendations
        evidence_patterns = [
            r"(?:because|since|therefore|thus|hence)",
            r"(?:reason|rationale|justification)",
            r"(?:evidence|data|metric|measurement)",
            r"(?:according\s+to|based\s+on|supported\s+by)",
            r"(?:research|study|analysis)\s+(?:shows?|indicates?|suggests?)",
            r"(?:this|which)\s+(?:leads?\s+to|results?\s+in|improves?)",
            r"\[INSTRUCTION\].*\[REASON\]",
        ]

        evidence_count = sum(
            1 for p in evidence_patterns if re.search(p, output.lower())
        )

        if evidence_count >= 3:
            score = 1.0
        elif evidence_count >= 2:
            score = 0.7
            issues.append("Some justification present but could be more comprehensive")
        elif evidence_count >= 1:
            score = 0.4
            issues.append("Minimal evidence-based reasoning")
        else:
            score = 0.2
            issues.append("No evidence-based recommendations found")

        return score, issues

    def measure(self, test_case: LLMTestCase) -> float:
        """
        Measure refactoring quality in the response.

        Args:
            test_case: The LLM test case to evaluate

        Returns:
            float: The computed score between 0.0 and 1.0
        """
        output = test_case.actual_output or ""
        all_issues: list[str] = []

        # Component weights
        weights = {
            "before_after": 0.25,
            "rubric": 0.20,
            "priority": 0.20,
            "claude45": 0.20,
            "evidence": 0.15,
        }

        # Calculate component scores
        ba_score, ba_issues = self._evaluate_before_after(output)
        rubric_score, rubric_issues = self._evaluate_quality_rubric(output)
        priority_score, priority_issues = self._evaluate_prioritization(output)
        claude45_score, claude45_issues = self._evaluate_claude45_alignment(output)
        evidence_score, evidence_issues = self._evaluate_evidence_based(output)

        all_issues.extend(ba_issues)
        all_issues.extend(rubric_issues)
        all_issues.extend(priority_issues)
        all_issues.extend(claude45_issues)
        all_issues.extend(evidence_issues)

        # Calculate weighted score
        weighted_score = (
            ba_score * weights["before_after"]
            + rubric_score * weights["rubric"]
            + priority_score * weights["priority"]
            + claude45_score * weights["claude45"]
            + evidence_score * weights["evidence"]
        )

        self._score = min(1.0, max(0.0, weighted_score))

        # Generate reason
        if self._score >= self.threshold:
            self._reason = (
                f"Strong refactoring quality. "
                f"Before/After: {ba_score:.0%}, Rubric: {rubric_score:.0%}, "
                f"Priority: {priority_score:.0%}, Claude 4.5: {claude45_score:.0%}, "
                f"Evidence: {evidence_score:.0%}. Score: {self._score:.2f}"
            )
        else:
            issues_text = "; ".join(all_issues) if all_issues else "Quality incomplete"
            self._reason = (
                f"Refactoring quality below threshold ({self.threshold}). "
                f"Issues: {issues_text}. "
                f"Before/After: {ba_score:.0%}, Rubric: {rubric_score:.0%}, "
                f"Priority: {priority_score:.0%}, Claude 4.5: {claude45_score:.0%}, "
                f"Evidence: {evidence_score:.0%}. Score: {self._score:.2f}"
            )

        return self._score

    async def a_measure(self, test_case: LLMTestCase) -> float:
        """Async version of measure."""
        return self.measure(test_case)


def create_refactoring_quality_metric(threshold: float = 0.80) -> RefactoringQualityMetric:
    """Factory function to create RefactoringQualityMetric."""
    return RefactoringQualityMetric(threshold=threshold)
