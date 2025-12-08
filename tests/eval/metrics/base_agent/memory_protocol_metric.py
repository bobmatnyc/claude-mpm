"""
Memory Protocol Metric for BASE_AGENT Testing.

This metric evaluates JSON response format and memory management compliance:
- Valid JSON structure at end of response
- Required fields with correct types
- Appropriate memory capture triggers
- Memory quality (concise, project-specific, no duplicates)

Scoring Algorithm (weighted):
1. JSON Format (30%): Valid JSON block, proper structure/syntax
2. Required Fields (30%): All 6 fields present with correct types
3. Memory Capture (25%): Appropriate triggers detected, no over-capture
4. Memory Quality (15%): Concise, project-specific, no duplicates

Threshold: 1.0 (strict compliance - 100% required)

Example:
    metric = MemoryProtocolMetric(threshold=1.0)
    test_case = LLMTestCase(
        input="Remember that this project uses pytest for testing",
        actual_output='''I've noted that information.

```json
{
    "task_completed": true,
    "instructions": "Remember testing framework preference",
    "results": "Noted pytest as the testing framework",
    "files_modified": [],
    "tools_used": [],
    "remember": ["Project uses pytest for testing"]
}
```'''
    )
    metric.measure(test_case)
    print(f"Score: {metric.score}, Passed: {metric.is_successful()}")
"""

import json
import re
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from deepeval.metrics import BaseMetric
from deepeval.test_case import LLMTestCase


class MemoryProtocolMetric(BaseMetric):
    """
    DeepEval metric for BASE_AGENT JSON response and memory protocol compliance.

    Evaluates:
    1. JSON format validity and structure
    2. Required fields presence and type correctness
    3. Memory capture appropriateness (triggered by user requests)
    4. Memory quality (concise, project-specific, no duplicates)

    Scoring:
    - 1.0: Perfect compliance (all checks pass)
    - 0.7-0.99: Minor issues (missing optional checks)
    - 0.4-0.69: Major issues (missing required fields, invalid JSON)
    - 0.0-0.39: Severe violations (no JSON block, wrong structure)
    """

    # Required fields with expected types
    REQUIRED_FIELDS: Dict[str, Union[type, Tuple[type, ...]]] = {
        'task_completed': bool,
        'instructions': str,
        'results': str,
        'files_modified': list,
        'tools_used': list,
        'remember': (list, type(None))  # List[str] or null
    }

    # Memory trigger patterns (MUST capture when present in user input)
    MEMORY_TRIGGERS: List[str] = [
        'remember',
        "don't forget",
        'memorize',
        'note that',
        'keep in mind'
    ]

    # User-specific patterns (SHOULD NOT capture - too personal)
    USER_SPECIFIC_KEYWORDS: List[str] = [
        'i prefer',
        'my style',
        'i like',
        'user preference'
    ]

    # Obvious facts patterns (SHOULD NOT capture - not valuable)
    OBVIOUS_KEYWORDS: List[str] = [
        'code is in',
        'file is located',
        'standard practice',
        'common pattern',
        'well-known'
    ]

    # JSON extraction patterns
    JSON_FENCED_PATTERN = re.compile(
        r'```(?:json)?\s*(\{[^`]*?\})\s*```',
        re.DOTALL | re.IGNORECASE
    )
    JSON_RAW_PATTERN = re.compile(
        r'\{[^{}]*"task_completed"[^{}]*\}',
        re.DOTALL
    )

    def __init__(self, threshold: float = 1.0):
        """
        Initialize MemoryProtocolMetric.

        Args:
            threshold: Minimum score to pass (default: 1.0 for strict compliance)
        """
        self.threshold = threshold
        self._score: Optional[float] = None
        self._reason: Optional[str] = None
        self._success: Optional[bool] = None

    @property
    def __name__(self) -> str:
        return "Memory Protocol"

    @property
    def score(self) -> Optional[float]:
        """Get the computed score."""
        return self._score

    @property
    def reason(self) -> Optional[str]:
        """Get the reason for the score."""
        return self._reason

    def is_successful(self) -> bool:
        """Check if metric passes threshold (with epsilon for floating-point precision)."""
        if self._success is None:
            return False
        return self._success

    def measure(self, test_case: LLMTestCase) -> float:
        """
        Measure memory protocol compliance score.

        Args:
            test_case: DeepEval test case with input and actual_output

        Returns:
            Score from 0.0 to 1.0
        """
        output = test_case.actual_output
        user_input = test_case.input

        # Extract JSON block
        json_data, json_valid = self._extract_json(output)

        # Calculate component scores
        json_format_score = self._score_json_format(output, json_valid)
        required_fields_score = self._score_required_fields(json_data, json_valid)
        memory_capture_score = self._score_memory_capture(
            user_input,
            json_data,
            json_valid
        )
        memory_quality_score = self._score_memory_quality(json_data, json_valid)

        # Weighted average
        final_score = (
            json_format_score * 0.30 +
            required_fields_score * 0.30 +
            memory_capture_score * 0.25 +
            memory_quality_score * 0.15
        )

        # Store results
        self._score = final_score
        self._reason = self._generate_reason(
            json_format_score,
            required_fields_score,
            memory_capture_score,
            memory_quality_score,
            json_data,
            json_valid,
            user_input
        )
        # Use epsilon comparison to handle floating-point precision issues
        epsilon = 1e-9
        self._success = final_score >= (self.threshold - epsilon)

        return final_score

    async def a_measure(self, test_case: LLMTestCase) -> float:
        """Async version of measure (delegates to sync)."""
        return self.measure(test_case)

    # ========================================================================
    # JSON EXTRACTION
    # ========================================================================

    def _extract_json(self, output: str) -> Tuple[Optional[Dict[str, Any]], bool]:
        """
        Extract JSON block from output.

        Looks for JSON in the last 2000 characters of response.
        Supports both fenced (```json) and raw JSON blocks.

        Args:
            output: Agent output text

        Returns:
            Tuple of (parsed_json_dict, is_valid)
        """
        # Search in last 2000 chars (JSON should be at end)
        search_text = output[-2000:]

        # Try fenced block first
        fenced_match = self.JSON_FENCED_PATTERN.search(search_text)
        if fenced_match:
            try:
                json_data = json.loads(fenced_match.group(1))
                return json_data, True
            except json.JSONDecodeError:
                pass

        # Try raw JSON pattern
        raw_match = self.JSON_RAW_PATTERN.search(search_text)
        if raw_match:
            try:
                json_data = json.loads(raw_match.group(0))
                return json_data, True
            except json.JSONDecodeError:
                pass

        # No valid JSON found
        return None, False

    # ========================================================================
    # COMPONENT SCORING METHODS
    # ========================================================================

    def _score_json_format(self, output: str, json_valid: bool) -> float:
        """
        Score JSON format validity (30% weight).

        Checks:
        - Valid JSON block present
        - Located at end of response (last 2000 chars)
        - Proper structure and syntax

        Args:
            output: Agent output text
            json_valid: Whether JSON extraction succeeded

        Returns:
            Score from 0.0 to 1.0
        """
        if not json_valid:
            return 0.0

        # Check if JSON is at the end (good practice)
        search_text = output[-2000:]
        if self.JSON_FENCED_PATTERN.search(search_text) or \
           self.JSON_RAW_PATTERN.search(search_text):
            return 1.0

        return 0.5  # JSON found but not ideally positioned

    def _score_required_fields(
        self,
        json_data: Optional[Dict[str, Any]],
        json_valid: bool
    ) -> float:
        """
        Score required fields presence and type correctness (30% weight).

        Checks:
        - All 6 required fields present
        - Correct types for each field
        - No unexpected extra fields

        Args:
            json_data: Parsed JSON dictionary (or None)
            json_valid: Whether JSON extraction succeeded

        Returns:
            Score from 0.0 to 1.0
        """
        if not json_valid or json_data is None:
            return 0.0

        score = 0.0
        field_count = len(self.REQUIRED_FIELDS)

        for field_name, expected_type in self.REQUIRED_FIELDS.items():
            if field_name not in json_data:
                continue  # Missing field, no points

            value = json_data[field_name]

            # Handle union types (e.g., list or None)
            if isinstance(expected_type, tuple):
                if any(isinstance(value, t) if t is not type(None) else value is None
                       for t in expected_type):
                    score += 1.0 / field_count
            elif isinstance(value, expected_type):
                score += 1.0 / field_count

        return score

    def _score_memory_capture(
        self,
        user_input: str,
        json_data: Optional[Dict[str, Any]],
        json_valid: bool
    ) -> float:
        """
        Score memory capture appropriateness (25% weight).

        Checks:
        - Memory captured when user explicitly requests (triggers)
        - Memory NOT captured for user-specific preferences
        - Memory NOT captured for obvious facts

        Args:
            user_input: User's request
            json_data: Parsed JSON dictionary
            json_valid: Whether JSON extraction succeeded

        Returns:
            Score from 0.0 to 1.0
        """
        if not json_valid or json_data is None:
            return 0.0

        # Check if user input contains memory triggers
        has_trigger = any(
            trigger.lower() in user_input.lower()
            for trigger in self.MEMORY_TRIGGERS
        )

        # Check if user input contains user-specific or obvious keywords
        is_user_specific = any(
            keyword.lower() in user_input.lower()
            for keyword in self.USER_SPECIFIC_KEYWORDS
        )
        is_obvious = any(
            keyword.lower() in user_input.lower()
            for keyword in self.OBVIOUS_KEYWORDS
        )

        remember_field = json_data.get('remember')
        has_memory = remember_field is not None and \
                     isinstance(remember_field, list) and \
                     len(remember_field) > 0

        # Scoring logic
        if has_trigger and not is_user_specific and not is_obvious:
            # MUST capture memory
            return 1.0 if has_memory else 0.0
        if is_user_specific or is_obvious:
            # SHOULD NOT capture memory
            return 0.0 if has_memory else 1.0
        # No trigger, optional memory capture
        # Give partial credit regardless of choice
        return 0.7

    def _score_memory_quality(
        self,
        json_data: Optional[Dict[str, Any]],
        json_valid: bool
    ) -> float:
        """
        Score memory quality (15% weight).

        Checks:
        - Concise entries (<100 chars each)
        - Project-specific (not generic)
        - No duplicates within entries

        Args:
            json_data: Parsed JSON dictionary
            json_valid: Whether JSON extraction succeeded

        Returns:
            Score from 0.0 to 1.0
        """
        if not json_valid or json_data is None:
            return 0.0

        remember_field = json_data.get('remember')

        # If no memory or null, full score (quality N/A)
        if remember_field is None or not isinstance(remember_field, list):
            return 1.0

        if len(remember_field) == 0:
            return 1.0

        # Count passes for each check
        passes = 0
        total_checks = 3
        entries = remember_field

        # Check conciseness
        all_concise = all(
            isinstance(entry, str) and len(entry) < 100
            for entry in entries
        )
        if all_concise:
            passes += 1

        # Check for generic patterns
        generic_patterns = [
            r'(?:always|never|should|must)\s+(?:use|do|be)',
            r'best practice',
            r'general rule',
            r'common approach'
        ]
        has_generic = any(
            any(re.search(pattern, entry, re.IGNORECASE) for pattern in generic_patterns)
            for entry in entries
            if isinstance(entry, str)
        )
        if not has_generic:
            passes += 1

        # Check for duplicates
        unique_entries: Set[str] = set()
        has_duplicates = False
        for entry in entries:
            if isinstance(entry, str):
                normalized = entry.lower().strip()
                if normalized in unique_entries:
                    has_duplicates = True
                    break
                unique_entries.add(normalized)

        if not has_duplicates:
            passes += 1

        # Return fractional score (avoids floating-point precision issues)
        return passes / total_checks

    # ========================================================================
    # HELPER METHODS
    # ========================================================================

    def _generate_reason(
        self,
        json_format_score: float,
        required_fields_score: float,
        memory_capture_score: float,
        memory_quality_score: float,
        json_data: Optional[Dict[str, Any]],
        json_valid: bool,
        user_input: str
    ) -> str:
        """
        Generate human-readable reason for the score.

        Args:
            json_format_score: JSON format score
            required_fields_score: Required fields score
            memory_capture_score: Memory capture score
            memory_quality_score: Memory quality score
            json_data: Parsed JSON data
            json_valid: Whether JSON is valid
            user_input: User's request

        Returns:
            Reason string explaining the score
        """
        reasons = []

        # JSON format issues
        if json_format_score < 1.0:
            if not json_valid:
                reasons.append("No valid JSON block found at end of response")
            else:
                reasons.append("JSON block present but not ideally positioned")

        # Required fields issues
        if required_fields_score < 1.0:
            if json_data is None:
                reasons.append("Cannot validate fields - JSON invalid")
            else:
                missing_fields = [
                    field for field in self.REQUIRED_FIELDS
                    if field not in json_data
                ]
                if missing_fields:
                    reasons.append(f"Missing required fields: {', '.join(missing_fields)}")

                # Check type mismatches
                type_errors = []
                for field_name, expected_type in self.REQUIRED_FIELDS.items():
                    if field_name in json_data:
                        value = json_data[field_name]
                        if isinstance(expected_type, tuple):
                            valid = any(
                                isinstance(value, t) if t is not type(None) else value is None
                                for t in expected_type
                            )
                        else:
                            valid = isinstance(value, expected_type)

                        if not valid:
                            type_errors.append(
                                f"{field_name} (expected {expected_type}, got {type(value).__name__})"
                            )

                if type_errors:
                    reasons.append(f"Type mismatches: {', '.join(type_errors)}")

        # Memory capture issues
        if memory_capture_score < 1.0:
            has_trigger = any(
                trigger.lower() in user_input.lower()
                for trigger in self.MEMORY_TRIGGERS
            )
            remember_field = json_data.get('remember') if json_data else None
            has_memory = remember_field is not None and \
                         isinstance(remember_field, list) and \
                         len(remember_field) > 0

            if has_trigger and not has_memory:
                reasons.append(
                    "Memory trigger detected in user input but no memory captured"
                )
            elif not has_trigger and has_memory:
                is_user_specific = any(
                    keyword.lower() in user_input.lower()
                    for keyword in self.USER_SPECIFIC_KEYWORDS
                )
                if is_user_specific:
                    reasons.append(
                        "Memory captured for user-specific preference (should avoid)"
                    )

        # Memory quality issues
        if memory_quality_score < 1.0 and json_data:
            remember_field = json_data.get('remember')
            if remember_field and isinstance(remember_field, list) and len(remember_field) > 0:
                quality_issues = []

                # Check conciseness
                verbose_entries = [
                    entry for entry in remember_field
                    if isinstance(entry, str) and len(entry) >= 100
                ]
                if verbose_entries:
                    quality_issues.append(
                        f"{len(verbose_entries)} verbose entries (>=100 chars)"
                    )

                # Check for generic patterns
                generic_patterns = [
                    r'(?:always|never|should|must)\s+(?:use|do|be)',
                    r'best practice',
                    r'general rule'
                ]
                generic_count = sum(
                    1 for entry in remember_field
                    if isinstance(entry, str) and any(
                        re.search(pattern, entry, re.IGNORECASE)
                        for pattern in generic_patterns
                    )
                )
                if generic_count > 0:
                    quality_issues.append(
                        f"{generic_count} generic entries (not project-specific)"
                    )

                # Check duplicates
                seen: Set[str] = set()
                duplicates = []
                for entry in remember_field:
                    if isinstance(entry, str):
                        normalized = entry.lower().strip()
                        if normalized in seen:
                            duplicates.append(entry)
                        seen.add(normalized)

                if duplicates:
                    quality_issues.append(
                        f"{len(duplicates)} duplicate entries"
                    )

                if quality_issues:
                    reasons.append(f"Memory quality issues: {'; '.join(quality_issues)}")

        # Success message
        if not reasons:
            return "Perfect memory protocol compliance - all checks passed"

        return "; ".join(reasons)


def create_memory_protocol_metric(threshold: float = 1.0) -> MemoryProtocolMetric:
    """
    Factory function to create memory protocol metric.

    Args:
        threshold: Minimum passing score (default: 1.0)

    Returns:
        Configured metric instance

    Example:
        metric = create_memory_protocol_metric(threshold=1.0)
        test_case = LLMTestCase(...)
        score = metric.measure(test_case)
    """
    return MemoryProtocolMetric(threshold=threshold)
