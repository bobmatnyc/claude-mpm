"""
Response Replay System.

Loads captured PM responses for regression testing, compares new responses
with historical responses, and detects behavior changes over time.

Design Decision: Replay Architecture
- Golden responses stored separately from test responses
- Diff-based comparison for behavior change detection
- Semantic similarity for flexible regression testing
- Version-aware comparison (can compare across PM versions)

Trade-offs:
- Exact match vs. semantic similarity (support both)
- Storage overhead vs. history depth (configurable retention)
- Performance: In-memory cache vs. lazy loading (chose lazy)
"""

import difflib
import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .pm_response_capture import PMResponse, PMResponseCapture, get_golden_responses_dir


@dataclass
class ResponseComparison:
    """Results of comparing two PM responses."""
    scenario_id: str
    current_response: PMResponse
    baseline_response: PMResponse
    match_score: float  # 0.0-1.0, 1.0 = exact match
    differences: List[str]
    semantic_match: bool
    exact_match: bool
    regression_detected: bool


@dataclass
class RegressionReport:
    """Report of regression test results."""
    total_scenarios: int
    passed: int
    failed: int
    regressions: List[ResponseComparison]
    timestamp: str
    baseline_version: str
    current_version: str


class ResponseReplay:
    """
    Replay captured responses for regression testing.

    Supports:
    - Loading responses from storage
    - Comparing with golden responses
    - Detecting behavior changes
    - Regression reporting

    Example:
        >>> replay = ResponseReplay(
        ...     responses_dir="tests/eval/responses",
        ...     golden_dir="tests/eval/golden_responses"
        ... )
        >>> comparison = replay.compare_response(
        ...     scenario_id="url_linear",
        ...     current_response=new_response,
        ...     category="ticketing"
        ... )
        >>> if comparison.regression_detected:
        ...     print(f"Regression: {comparison.differences}")
    """

    def __init__(
        self,
        responses_dir: Optional[str] = None,
        golden_dir: Optional[str] = None,
        similarity_threshold: float = 0.85,
    ):
        """
        Initialize response replay system.

        Args:
            responses_dir: Directory with captured responses
            golden_dir: Directory with golden responses
            similarity_threshold: Threshold for semantic match (0.0-1.0)
        """
        self.capture = PMResponseCapture(
            responses_dir=responses_dir or "tests/eval/responses"
        )
        self.golden_dir = Path(golden_dir or get_golden_responses_dir())
        self.similarity_threshold = similarity_threshold

        # Create golden responses directory structure
        self.golden_dir.mkdir(parents=True, exist_ok=True)
        (self.golden_dir / "ticketing").mkdir(exist_ok=True)
        (self.golden_dir / "circuit_breakers").mkdir(exist_ok=True)

    def compare_response(
        self,
        scenario_id: str,
        current_response: PMResponse,
        category: str = "general",
        baseline_response: Optional[PMResponse] = None,
    ) -> ResponseComparison:
        """
        Compare current response with baseline (golden) response.

        Args:
            scenario_id: Scenario identifier
            current_response: Current PM response to compare
            category: Test category
            baseline_response: Optional baseline to compare against
                             (if None, loads from golden responses)

        Returns:
            ResponseComparison with match scores and differences
        """
        # Load baseline if not provided
        if baseline_response is None:
            baseline_response = self._load_golden_response(scenario_id, category)

        if baseline_response is None:
            # No baseline to compare against
            return ResponseComparison(
                scenario_id=scenario_id,
                current_response=current_response,
                baseline_response=None,
                match_score=1.0,  # No baseline = pass by default
                differences=[],
                semantic_match=True,
                exact_match=False,
                regression_detected=False,
            )

        # Compare responses
        exact_match = self._exact_match(
            current_response.response,
            baseline_response.response
        )

        match_score = self._calculate_similarity(
            current_response.response,
            baseline_response.response
        )

        semantic_match = match_score >= self.similarity_threshold

        differences = self._find_differences(
            current_response.response,
            baseline_response.response
        )

        # Regression detected if semantic match fails
        regression_detected = not semantic_match

        return ResponseComparison(
            scenario_id=scenario_id,
            current_response=current_response,
            baseline_response=baseline_response,
            match_score=match_score,
            differences=differences,
            semantic_match=semantic_match,
            exact_match=exact_match,
            regression_detected=regression_detected,
        )

    def run_regression_suite(
        self,
        category: Optional[str] = None,
        scenario_ids: Optional[List[str]] = None,
    ) -> RegressionReport:
        """
        Run regression tests for multiple scenarios.

        Args:
            category: Optional category filter
            scenario_ids: Optional list of specific scenarios to test

        Returns:
            RegressionReport with test results
        """
        # Load current responses
        current_responses = self.capture.list_responses(
            category=category,
            scenario_id=None,
        )

        # Filter by scenario IDs if provided
        if scenario_ids:
            current_responses = [
                r for r in current_responses
                if r.scenario_id in scenario_ids
            ]

        # Compare each response with golden
        comparisons = []
        passed = 0
        failed = 0
        regressions = []

        for response in current_responses:
            comparison = self.compare_response(
                scenario_id=response.scenario_id,
                current_response=response,
                category=response.metadata.test_category,
            )

            comparisons.append(comparison)

            if comparison.regression_detected:
                failed += 1
                regressions.append(comparison)
            else:
                passed += 1

        # Determine versions
        baseline_version = "unknown"
        if current_responses and regressions:
            if regressions[0].baseline_response:
                baseline_version = regressions[0].baseline_response.metadata.pm_version

        current_version = "unknown"
        if current_responses:
            current_version = current_responses[0].metadata.pm_version

        return RegressionReport(
            total_scenarios=len(comparisons),
            passed=passed,
            failed=failed,
            regressions=regressions,
            timestamp=datetime.now().isoformat(),
            baseline_version=baseline_version,
            current_version=current_version,
        )

    def save_as_golden(
        self,
        response: PMResponse,
        category: str,
        overwrite: bool = False,
    ) -> bool:
        """
        Save response as golden reference.

        Args:
            response: PM response to save as golden
            category: Test category
            overwrite: Allow overwriting existing golden response

        Returns:
            True if saved successfully, False if exists and overwrite=False
        """
        category_dir = self.golden_dir / category
        category_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{response.scenario_id}_golden.json"
        filepath = category_dir / filename

        if filepath.exists() and not overwrite:
            return False

        # Save as golden
        with open(filepath, "w") as f:
            json.dump(response.to_dict(), f, indent=2)

        return True

    def load_golden_response(
        self,
        scenario_id: str,
        category: str = "general",
    ) -> Optional[PMResponse]:
        """
        Load golden response for scenario.

        Public wrapper for _load_golden_response.

        Args:
            scenario_id: Scenario identifier
            category: Test category

        Returns:
            PMResponse if found, None otherwise
        """
        return self._load_golden_response(scenario_id, category)

    def _load_golden_response(
        self,
        scenario_id: str,
        category: str,
    ) -> Optional[PMResponse]:
        """Load golden response from storage."""
        category_dir = self.golden_dir / category
        if not category_dir.exists():
            return None

        filename = f"{scenario_id}_golden.json"
        filepath = category_dir / filename

        if not filepath.exists():
            return None

        with open(filepath) as f:
            data = json.load(f)

        return PMResponse.from_dict(data)

    def _exact_match(self, current: Dict[str, Any], baseline: Dict[str, Any]) -> bool:
        """Check if two responses are exactly the same."""
        return current == baseline

    def _calculate_similarity(
        self,
        current: Dict[str, Any],
        baseline: Dict[str, Any]
    ) -> float:
        """
        Calculate similarity score between responses.

        Uses text-based diff ratio for simplicity.
        Could be enhanced with semantic similarity (embeddings) in future.

        Returns:
            Similarity score 0.0-1.0, where 1.0 is identical
        """
        # Convert to JSON strings for comparison
        current_str = json.dumps(current, sort_keys=True, indent=2)
        baseline_str = json.dumps(baseline, sort_keys=True, indent=2)

        # Calculate diff ratio
        matcher = difflib.SequenceMatcher(None, current_str, baseline_str)
        return matcher.ratio()

    def _find_differences(
        self,
        current: Dict[str, Any],
        baseline: Dict[str, Any]
    ) -> List[str]:
        """
        Find specific differences between responses.

        Returns list of human-readable difference descriptions.
        """
        differences = []

        # Compare keys
        current_keys = set(current.keys())
        baseline_keys = set(baseline.keys())

        missing_keys = baseline_keys - current_keys
        extra_keys = current_keys - baseline_keys

        if missing_keys:
            differences.append(f"Missing keys: {missing_keys}")

        if extra_keys:
            differences.append(f"Extra keys: {extra_keys}")

        # Compare values for common keys
        common_keys = current_keys & baseline_keys
        for key in common_keys:
            current_val = current[key]
            baseline_val = baseline[key]

            if current_val != baseline_val:
                differences.append(
                    f"Key '{key}' differs: {baseline_val} -> {current_val}"
                )

        # If no specific differences found but responses differ
        if not differences and current != baseline:
            differences.append("Responses differ in structure or content")

        return differences

    def cleanup_old_responses(
        self,
        category: Optional[str] = None,
        days_to_keep: int = 30,
    ):
        """
        Remove old captured responses beyond retention period.

        Args:
            category: Optional category filter
            days_to_keep: Number of days to retain responses
        """
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)

        responses = self.capture.list_responses(category=category)

        for response in responses:
            response_time = datetime.fromisoformat(
                response.metadata.timestamp.replace("Z", "+00:00")
            )

            if response_time < cutoff_date:
                # Find and remove file
                category_dir = self.capture.responses_dir / response.metadata.test_category
                filename = f"{response.scenario_id}_{response.metadata.input_hash}.json"
                filepath = category_dir / filename

                if filepath.exists():
                    filepath.unlink()
                    print(f"Removed old response: {filepath}")


class GoldenResponseManager:
    """
    Manage golden responses with approval workflow.

    Example:
        >>> manager = GoldenResponseManager()
        >>> # Review and approve new golden response
        >>> manager.propose_golden(response, category="ticketing")
        >>> if manager.approve_pending(response.scenario_id):
        ...     print("Golden response updated")
    """

    def __init__(self, golden_dir: Optional[str] = None):
        """Initialize golden response manager."""
        self.replay = ResponseReplay(golden_dir=golden_dir)
        self.pending_dir = self.replay.golden_dir / "pending"
        self.pending_dir.mkdir(exist_ok=True)

    def propose_golden(
        self,
        response: PMResponse,
        category: str,
        reason: str = "",
    ):
        """
        Propose response as new golden (requires approval).

        Args:
            response: Response to propose as golden
            category: Test category
            reason: Reason for updating golden response
        """
        # Save to pending directory
        filename = f"{response.scenario_id}_pending.json"
        filepath = self.pending_dir / filename

        proposal_data = {
            "response": response.to_dict(),
            "category": category,
            "reason": reason,
            "proposed_at": datetime.now().isoformat(),
        }

        with open(filepath, "w") as f:
            json.dump(proposal_data, f, indent=2)

        print(f"Proposed golden response: {filepath}")
        print(f"Review and approve with: approve_pending('{response.scenario_id}')")

    def list_pending(self) -> List[Tuple[str, Dict[str, Any]]]:
        """List pending golden response proposals."""
        pending = []

        for filepath in self.pending_dir.glob("*_pending.json"):
            with open(filepath) as f:
                data = json.load(f)

            scenario_id = filepath.stem.replace("_pending", "")
            pending.append((scenario_id, data))

        return pending

    def approve_pending(self, scenario_id: str) -> bool:
        """
        Approve pending golden response.

        Args:
            scenario_id: Scenario ID to approve

        Returns:
            True if approved, False if not found
        """
        filepath = self.pending_dir / f"{scenario_id}_pending.json"

        if not filepath.exists():
            return False

        # Load proposal
        with open(filepath) as f:
            proposal = json.load(f)

        response = PMResponse.from_dict(proposal["response"])
        category = proposal["category"]

        # Save as golden
        self.replay.save_as_golden(response, category, overwrite=True)

        # Remove pending
        filepath.unlink()

        print(f"Approved golden response for: {scenario_id}")
        return True

    def reject_pending(self, scenario_id: str) -> bool:
        """
        Reject pending golden response proposal.

        Args:
            scenario_id: Scenario ID to reject

        Returns:
            True if rejected, False if not found
        """
        filepath = self.pending_dir / f"{scenario_id}_pending.json"

        if not filepath.exists():
            return False

        filepath.unlink()
        print(f"Rejected golden response proposal for: {scenario_id}")
        return True


# Convenience functions
def compare_with_golden(
    scenario_id: str,
    current_response: PMResponse,
    category: str = "general",
    **kwargs
) -> ResponseComparison:
    """
    Convenience function to compare response with golden.

    Example:
        >>> comparison = compare_with_golden(
        ...     scenario_id="url_linear",
        ...     current_response=response,
        ...     category="ticketing"
        ... )
        >>> assert not comparison.regression_detected
    """
    replay = ResponseReplay(**kwargs)
    return replay.compare_response(scenario_id, current_response, category)


def run_regression_tests(
    category: str = "ticketing",
    **kwargs
) -> RegressionReport:
    """
    Convenience function to run regression test suite.

    Example:
        >>> report = run_regression_tests(category="ticketing")
        >>> assert report.failed == 0, f"Regressions: {report.regressions}"
    """
    replay = ResponseReplay(**kwargs)
    return replay.run_regression_suite(category=category)
