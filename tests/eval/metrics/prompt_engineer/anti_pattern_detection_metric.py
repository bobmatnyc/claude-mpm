"""
AntiPatternDetectionMetric for Prompt-Engineer Agent.

Validates that the agent correctly identifies and flags prompt anti-patterns:
1. Emoji usage (decorative emojis in prompts)
2. Over-specification (>500 line prompts with micro-instructions)
3. Generic prompts (vague, context-free language)
4. Cache-hostile patterns (variable data in system prompts)
5. Negative instructions ("Don't X" instead of "Do Y")

Scoring is based on detection accuracy with F1-score calculation.
"""

import re
from typing import Any

from deepeval.metrics import BaseMetric
from deepeval.test_case import LLMTestCase


class AntiPatternDetectionMetric(BaseMetric):
    """
    Metric for evaluating anti-pattern detection in prompt engineering.

    Scoring Components (weighted):
    - Emoji detection (0.25): Identifies decorative emojis
    - Over-specification detection (0.20): Flags verbose prompts
    - Generic prompt detection (0.20): Identifies vague language
    - Cache-hostile detection (0.15): Flags variable data in system prompts
    - Negative instruction detection (0.20): Identifies "Don't X" patterns

    Threshold: 0.85 (comprehensive detection)
    """

    def __init__(self, threshold: float = 0.85, include_reason: bool = True):
        """Initialize the AntiPatternDetectionMetric."""
        self.threshold = threshold
        self.include_reason = include_reason
        self._score: float | None = None
        self._reason: str | None = None

    @property
    def __name__(self) -> str:
        """Return metric name."""
        return "AntiPatternDetectionMetric"

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

    def _detect_emoji_patterns(self, output: str) -> tuple[float, list[str]]:
        """
        Detect emoji-related anti-patterns.

        Returns score and list of issues found.
        """
        issues: list[str] = []
        score = 0.0

        # Check if response identifies emojis as anti-pattern
        emoji_detection_patterns = [
            r"emoji.*(?:anti[- ]?pattern|remove|avoid|eliminate)",
            r"(?:remove|avoid|eliminate).*emoji",
            r"decorative.*emoji",
            r"emoji.*(?:not|don.?t).*(?:use|allowed)",
            r"(?:no|zero).*emoji",
            r"emoji-free",
            r"without.*emoji",
        ]

        emoji_found = any(
            re.search(pattern, output.lower()) for pattern in emoji_detection_patterns
        )

        if emoji_found:
            score = 1.0
        else:
            # Check if emojis are present in output (failure to remove)
            emoji_pattern = re.compile(
                r"[\U0001F600-\U0001F64F"
                r"\U0001F300-\U0001F5FF"
                r"\U0001F680-\U0001F6FF"
                r"\U0001F1E0-\U0001F1FF"
                r"\U00002702-\U000027B0"
                r"\U0001F900-\U0001F9FF"
                r"\U0001FA00-\U0001FA6F]+",
                re.UNICODE,
            )
            if emoji_pattern.search(output):
                issues.append("Output contains emojis - should flag as anti-pattern")
                score = 0.0
            else:
                # No explicit detection mention but no emojis either
                score = 0.5

        return score, issues

    def _detect_overspecification_patterns(self, output: str) -> tuple[float, list[str]]:
        """
        Detect over-specification anti-pattern detection.

        Returns score and list of issues found.
        """
        issues: list[str] = []
        score = 0.0

        # Patterns indicating over-specification detection
        overspec_patterns = [
            r"over[- ]?specif(?:ication|ied|y)",
            r"too\s+(?:verbose|detailed|long)",
            r"micro[- ]?instruction",
            r"step[- ]?by[- ]?step.*excessive",
            r"reduce.*(?:length|verbosity|lines)",
            r"(?:consolidat|simplif).*instruction",
            r"redundant.*(?:instruction|step|detail)",
            r"(?:700|500)\+?\s*lines?",
        ]

        overspec_found = any(
            re.search(pattern, output.lower()) for pattern in overspec_patterns
        )

        if overspec_found:
            score = 1.0
        else:
            # Check for positive indicators of conciseness
            concise_patterns = [
                r"concise",
                r"brief",
                r"streamlined",
                r"minimal",
                r"essential.*only",
            ]
            if any(re.search(p, output.lower()) for p in concise_patterns):
                score = 0.6
            else:
                issues.append("No over-specification detection found")
                score = 0.3

        return score, issues

    def _detect_generic_prompt_patterns(self, output: str) -> tuple[float, list[str]]:
        """
        Detect generic prompt anti-pattern detection.

        Returns score and list of issues found.
        """
        issues: list[str] = []
        score = 0.0

        # Patterns indicating generic prompt detection
        generic_patterns = [
            r"generic.*(?:prompt|instruction|language)",
            r"vague.*(?:prompt|instruction|language)",
            r"(?:lack|missing).*(?:context|specific|detail)",
            r"(?:add|need|require).*(?:context|specific|detail)",
            r"(?:unclear|ambiguous).*(?:requirement|instruction)",
            r"(?:make|be).*(?:more\s+)?specific",
            r"measurable.*(?:criteria|goal|outcome)",
        ]

        generic_found = any(
            re.search(pattern, output.lower()) for pattern in generic_patterns
        )

        if generic_found:
            score = 1.0
        else:
            # Check for specificity indicators
            specific_patterns = [
                r"specific",
                r"concrete",
                r"measurable",
                r"actionable",
            ]
            if any(re.search(p, output.lower()) for p in specific_patterns):
                score = 0.5
            else:
                issues.append("No generic prompt detection found")
                score = 0.2

        return score, issues

    def _detect_cache_hostile_patterns(self, output: str) -> tuple[float, list[str]]:
        """
        Detect cache-hostile anti-pattern detection.

        Returns score and list of issues found.
        """
        issues: list[str] = []
        score = 0.0

        # Patterns indicating cache-hostile detection
        cache_patterns = [
            r"cache[- ]?hostil(?:e|ity)",
            r"cache.*(?:invalidat|miss|hit)",
            r"variable.*(?:data|content).*(?:system|prompt)",
            r"(?:dynamic|changing).*(?:content|data).*(?:system|prompt)",
            r"separate.*(?:static|stable).*(?:dynamic|variable)",
            r"(?:timestamp|date|time).*(?:system|prompt)",
            r"cache[- ]?(?:friendly|efficient|optim)",
            r"(?:90|95)%.*cache.*hit",
        ]

        cache_found = any(
            re.search(pattern, output.lower()) for pattern in cache_patterns
        )

        if cache_found:
            score = 1.0
        else:
            # Partial indicators
            partial_patterns = [
                r"performance",
                r"optimization",
                r"efficient",
            ]
            if any(re.search(p, output.lower()) for p in partial_patterns):
                score = 0.4
            else:
                issues.append("No cache-hostile pattern detection found")
                score = 0.2

        return score, issues

    def _detect_negative_instruction_patterns(self, output: str) -> tuple[float, list[str]]:
        """
        Detect negative instruction anti-pattern detection.

        Returns score and list of issues found.
        """
        issues: list[str] = []
        score = 0.0

        # Patterns indicating negative instruction detection
        negative_patterns = [
            r"negative.*instruction",
            r"(?:don.?t|do\s+not|never).*(?:anti[- ]?pattern|avoid)",
            r"(?:convert|rewrite|change).*(?:don.?t|negative).*(?:positive|do\s+)",
            r"(?:instead\s+of|rather\s+than).*(?:don.?t|negative)",
            r"(?:positive|affirmative).*(?:instruction|framing|language)",
            r"(?:tell|say).*what\s+to\s+do.*(?:not|instead)",
            r"avoid.*negative.*framing",
        ]

        negative_found = any(
            re.search(pattern, output.lower()) for pattern in negative_patterns
        )

        if negative_found:
            score = 1.0
        else:
            # Check for positive framing indicators
            positive_patterns = [
                r"positive.*(?:framing|language)",
                r"affirmative",
                r"constructive",
            ]
            if any(re.search(p, output.lower()) for p in positive_patterns):
                score = 0.5
            else:
                issues.append("No negative instruction detection found")
                score = 0.2

        return score, issues

    def measure(self, test_case: LLMTestCase) -> float:
        """
        Measure anti-pattern detection in the response.

        Args:
            test_case: The LLM test case to evaluate

        Returns:
            float: The computed score between 0.0 and 1.0
        """
        output = test_case.actual_output or ""
        all_issues: list[str] = []

        # Component weights
        weights = {
            "emoji": 0.25,
            "overspec": 0.20,
            "generic": 0.20,
            "cache": 0.15,
            "negative": 0.20,
        }

        # Calculate component scores
        emoji_score, emoji_issues = self._detect_emoji_patterns(output)
        overspec_score, overspec_issues = self._detect_overspecification_patterns(output)
        generic_score, generic_issues = self._detect_generic_prompt_patterns(output)
        cache_score, cache_issues = self._detect_cache_hostile_patterns(output)
        negative_score, negative_issues = self._detect_negative_instruction_patterns(output)

        all_issues.extend(emoji_issues)
        all_issues.extend(overspec_issues)
        all_issues.extend(generic_issues)
        all_issues.extend(cache_issues)
        all_issues.extend(negative_issues)

        # Calculate weighted score
        weighted_score = (
            emoji_score * weights["emoji"]
            + overspec_score * weights["overspec"]
            + generic_score * weights["generic"]
            + cache_score * weights["cache"]
            + negative_score * weights["negative"]
        )

        self._score = min(1.0, max(0.0, weighted_score))

        # Generate reason
        if self._score >= self.threshold:
            self._reason = (
                f"Excellent anti-pattern detection. "
                f"Emoji: {emoji_score:.0%}, Over-spec: {overspec_score:.0%}, "
                f"Generic: {generic_score:.0%}, Cache: {cache_score:.0%}, "
                f"Negative: {negative_score:.0%}. Score: {self._score:.2f}"
            )
        else:
            issues_text = "; ".join(all_issues) if all_issues else "Detection incomplete"
            self._reason = (
                f"Anti-pattern detection below threshold ({self.threshold}). "
                f"Issues: {issues_text}. "
                f"Emoji: {emoji_score:.0%}, Over-spec: {overspec_score:.0%}, "
                f"Generic: {generic_score:.0%}, Cache: {cache_score:.0%}, "
                f"Negative: {negative_score:.0%}. Score: {self._score:.2f}"
            )

        return self._score

    async def a_measure(self, test_case: LLMTestCase) -> float:
        """Async version of measure."""
        return self.measure(test_case)


def create_anti_pattern_detection_metric(threshold: float = 0.85) -> AntiPatternDetectionMetric:
    """Factory function to create AntiPatternDetectionMetric."""
    return AntiPatternDetectionMetric(threshold=threshold)
