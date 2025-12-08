"""
TokenEfficiencyMetric for Prompt-Engineer Agent.

Validates that the agent optimizes prompts for token efficiency:
1. Token reduction (target: 30%+ for verbose prompts)
2. Cache-friendly structure (stable/variable separation)
3. Redundancy elimination
4. Structural optimization (XML tags, markdown formatting)

Scoring based on demonstrated optimization awareness.
"""

import re
from typing import Any

from deepeval.metrics import BaseMetric
from deepeval.test_case import LLMTestCase


class TokenEfficiencyMetric(BaseMetric):
    """
    Metric for evaluating token efficiency in prompt optimization.

    Scoring Components (weighted):
    - Token reduction awareness (0.30): Mentions reduction percentages
    - Cache optimization (0.25): Describes cache-friendly patterns
    - Redundancy elimination (0.25): Identifies and removes duplicates
    - Structural optimization (0.20): Uses efficient structures

    Threshold: 0.80 (strong optimization awareness)
    """

    def __init__(self, threshold: float = 0.80, include_reason: bool = True):
        """Initialize the TokenEfficiencyMetric."""
        self.threshold = threshold
        self.include_reason = include_reason
        self._score: float | None = None
        self._reason: str | None = None

    @property
    def __name__(self) -> str:
        """Return metric name."""
        return "TokenEfficiencyMetric"

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

    def _evaluate_token_reduction(self, output: str) -> tuple[float, list[str]]:
        """
        Evaluate token reduction awareness.

        Returns score and list of issues found.
        """
        issues: list[str] = []
        score = 0.0

        # Patterns indicating token reduction awareness
        reduction_patterns = [
            r"(?:reduc|decreas|cut|lower).*(?:token|length|size|line)",
            r"(?:token|length|size|line).*(?:reduc|decreas|cut|lower)",
            r"\d+%.*(?:reduc|fewer|less|smaller)",
            r"(?:30|40|50|60|70|80)%.*(?:reduc|sav|effici)",
            r"(?:from|reduced)\s+\d+\s+(?:to|lines?|tokens?)",
            r"(?:before|after).*(?:\d+\s*(?:lines?|tokens?))",
            r"(?:original|new).*(?:\d+\s*(?:lines?|tokens?))",
            r"(?:738|700|500).*(?:150|200|300)",
        ]

        reduction_found = any(
            re.search(pattern, output.lower()) for pattern in reduction_patterns
        )

        if reduction_found:
            # Check for specific percentages (bonus)
            percentage_match = re.search(r"(\d+)%", output)
            if percentage_match:
                pct = int(percentage_match.group(1))
                if pct >= 30:
                    score = 1.0
                else:
                    score = 0.8
            else:
                score = 0.9
        else:
            # Check for general optimization language
            optim_patterns = [
                r"optimiz",
                r"streamlin",
                r"efficient",
                r"compact",
            ]
            if any(re.search(p, output.lower()) for p in optim_patterns):
                score = 0.5
                issues.append(
                    "General optimization mentioned but no specific reduction metrics"
                )
            else:
                score = 0.2
                issues.append("No token reduction awareness found")

        return score, issues

    def _evaluate_cache_optimization(self, output: str) -> tuple[float, list[str]]:
        """
        Evaluate cache optimization awareness.

        Returns score and list of issues found.
        """
        issues: list[str] = []
        score = 0.0

        # Patterns indicating cache optimization
        cache_patterns = [
            r"cache[- ]?(?:friendly|efficient|optim|hit)",
            r"(?:stable|static).*(?:separate|section|part)",
            r"(?:variable|dynamic).*(?:separate|section|part)",
            r"(?:90|95|99)%.*cache",
            r"cache.*(?:90|95|99)%",
            r"(?:prefix|system).*(?:stable|static)",
            r"(?:avoid|prevent).*cache.*(?:miss|invalidat)",
        ]

        cache_found = any(
            re.search(pattern, output.lower()) for pattern in cache_patterns
        )

        if cache_found:
            # Check for specific cache hit percentages
            hit_match = re.search(r"(\d+)%.*cache", output.lower())
            if hit_match:
                pct = int(hit_match.group(1))
                if pct >= 90:
                    score = 1.0
                else:
                    score = 0.8
            else:
                score = 0.9
        else:
            # Check for related concepts
            related_patterns = [
                r"performance",
                r"latency",
                r"repeat",
            ]
            if any(re.search(p, output.lower()) for p in related_patterns):
                score = 0.4
                issues.append(
                    "Performance mentioned but no cache optimization specifics"
                )
            else:
                score = 0.2
                issues.append("No cache optimization awareness found")

        return score, issues

    def _evaluate_redundancy_elimination(self, output: str) -> tuple[float, list[str]]:
        """
        Evaluate redundancy elimination.

        Returns score and list of issues found.
        """
        issues: list[str] = []
        score = 0.0

        # Patterns indicating redundancy elimination
        redundancy_patterns = [
            r"redundan(?:t|cy).*(?:remov|eliminat|reduc)",
            r"(?:remov|eliminat|reduc).*redundan",
            r"(?:duplicate|repeat).*(?:remov|eliminat|consolidat)",
            r"(?:remov|eliminat|consolidat).*(?:duplicate|repeat)",
            r"(?:merge|consolidat|combine).*(?:similar|duplicate)",
            r"(?:DRY|don.?t\s+repeat)",
            r"single\s+source\s+of\s+truth",
        ]

        redundancy_found = any(
            re.search(pattern, output.lower()) for pattern in redundancy_patterns
        )

        if redundancy_found:
            score = 1.0
        else:
            # Check for consolidation indicators
            consolidate_patterns = [
                r"consolidat",
                r"simplif",
                r"streamlin",
            ]
            if any(re.search(p, output.lower()) for p in consolidate_patterns):
                score = 0.5
                issues.append(
                    "Simplification mentioned but no redundancy elimination specifics"
                )
            else:
                score = 0.2
                issues.append("No redundancy elimination awareness found")

        return score, issues

    def _evaluate_structural_optimization(self, output: str) -> tuple[float, list[str]]:
        """
        Evaluate structural optimization.

        Returns score and list of issues found.
        """
        issues: list[str] = []
        score = 0.0

        # Patterns indicating structural optimization
        structure_patterns = [
            r"(?:xml|structured).*(?:tag|format)",
            r"markdown.*(?:format|structur)",
            r"(?:hierarch|organiz|structur).*(?:clear|better|improv)",
            r"(?:section|heading).*(?:organiz|structur)",
            r"<\w+>.*</\w+>",  # XML tag pattern
            r"```.*```",  # Code block pattern
            r"##\s+\w+",  # Markdown heading pattern
            r"bullet.*point",
            r"numbered.*list",
        ]

        structure_found = any(
            re.search(pattern, output.lower()) for pattern in structure_patterns
        )

        if structure_found:
            # Check for both XML and markdown awareness
            xml_aware = re.search(r"xml|<\w+>", output.lower())
            md_aware = re.search(r"markdown|##|```", output.lower())
            if xml_aware and md_aware:
                score = 1.0
            else:
                score = 0.8
        else:
            # Check for format awareness
            format_patterns = [
                r"format",
                r"layout",
                r"organiz",
            ]
            if any(re.search(p, output.lower()) for p in format_patterns):
                score = 0.4
                issues.append(
                    "Formatting mentioned but no structural optimization specifics"
                )
            else:
                score = 0.2
                issues.append("No structural optimization awareness found")

        return score, issues

    def measure(self, test_case: LLMTestCase) -> float:
        """
        Measure token efficiency in the response.

        Args:
            test_case: The LLM test case to evaluate

        Returns:
            float: The computed score between 0.0 and 1.0
        """
        output = test_case.actual_output or ""
        all_issues: list[str] = []

        # Component weights
        weights = {
            "reduction": 0.30,
            "cache": 0.25,
            "redundancy": 0.25,
            "structure": 0.20,
        }

        # Calculate component scores
        reduction_score, reduction_issues = self._evaluate_token_reduction(output)
        cache_score, cache_issues = self._evaluate_cache_optimization(output)
        redundancy_score, redundancy_issues = self._evaluate_redundancy_elimination(
            output
        )
        structure_score, structure_issues = self._evaluate_structural_optimization(
            output
        )

        all_issues.extend(reduction_issues)
        all_issues.extend(cache_issues)
        all_issues.extend(redundancy_issues)
        all_issues.extend(structure_issues)

        # Calculate weighted score
        weighted_score = (
            reduction_score * weights["reduction"]
            + cache_score * weights["cache"]
            + redundancy_score * weights["redundancy"]
            + structure_score * weights["structure"]
        )

        self._score = min(1.0, max(0.0, weighted_score))

        # Generate reason
        if self._score >= self.threshold:
            self._reason = (
                f"Strong token efficiency awareness. "
                f"Reduction: {reduction_score:.0%}, Cache: {cache_score:.0%}, "
                f"Redundancy: {redundancy_score:.0%}, Structure: {structure_score:.0%}. "
                f"Score: {self._score:.2f}"
            )
        else:
            issues_text = (
                "; ".join(all_issues) if all_issues else "Optimization incomplete"
            )
            self._reason = (
                f"Token efficiency below threshold ({self.threshold}). "
                f"Issues: {issues_text}. "
                f"Reduction: {reduction_score:.0%}, Cache: {cache_score:.0%}, "
                f"Redundancy: {redundancy_score:.0%}, Structure: {structure_score:.0%}. "
                f"Score: {self._score:.2f}"
            )

        return self._score

    async def a_measure(self, test_case: LLMTestCase) -> float:
        """Async version of measure."""
        return self.measure(test_case)


def create_token_efficiency_metric(threshold: float = 0.80) -> TokenEfficiencyMetric:
    """Factory function to create TokenEfficiencyMetric."""
    return TokenEfficiencyMetric(threshold=threshold)
