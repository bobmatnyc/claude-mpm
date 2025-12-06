"""
Engineer Agent DeepEval Integration Test Harness.

This test harness validates Engineer Agent behaviors across 25 scenarios in 4 categories:
- Code Minimization Mandate (10 scenarios: MIN-E-001 to MIN-E-010)
- Consolidation & Duplicate Elimination (7 scenarios: CONS-E-001 to CONS-E-007)
- Anti-Pattern Avoidance (5 scenarios: ANTI-E-001 to ANTI-E-005)
- Test Process Management (3 scenarios: PROC-E-001 to PROC-E-003)

Each test:
1. Loads scenario from engineer_scenarios.json
2. Creates LLMTestCase with input and mock response
3. Applies appropriate custom metric(s)
4. Asserts compliance using DeepEval's metric evaluation

Usage:
    # Run all Engineer Agent integration tests
    pytest tests/eval/agents/engineer/test_integration.py -v

    # Run specific category
    pytest tests/eval/agents/engineer/test_integration.py::TestEngineerCodeMinimization -v

    # Run specific scenario
    pytest tests/eval/agents/engineer/test_integration.py::TestEngineerCodeMinimization::test_scenario[MIN-E-001] -v

Test Strategy:
    - Each scenario tests COMPLIANT response (should pass)
    - Metrics validate adherence to Engineer Agent protocols
    - Thresholds calibrated based on metric scoring components
    - Fixture-based scenario loading for maintainability
"""

import json
import pytest
from pathlib import Path
from typing import Dict, List, Any

from deepeval.test_case import LLMTestCase

# Import Engineer Agent custom metrics
from tests.eval.metrics.engineer import (
    CodeMinimizationMetric,
    ConsolidationMetric,
    AntiPatternDetectionMetric,
)

# Path to Engineer scenarios JSON
SCENARIOS_PATH = (
    Path(__file__).parent.parent.parent
    / "scenarios"
    / "engineer"
    / "engineer_scenarios.json"
)


def load_scenarios() -> Dict[str, Any]:
    """Load Engineer scenarios from JSON file.

    Returns:
        Dict containing all scenarios and metadata

    Raises:
        FileNotFoundError: If scenarios file doesn't exist
        json.JSONDecodeError: If scenarios file is invalid JSON
    """
    if not SCENARIOS_PATH.exists():
        raise FileNotFoundError(f"Scenarios file not found: {SCENARIOS_PATH}")

    with open(SCENARIOS_PATH, encoding="utf-8") as f:
        return json.load(f)


def get_scenario_by_id(scenario_id: str) -> Dict[str, Any]:
    """Get a specific scenario by its ID.

    Args:
        scenario_id: Scenario identifier (e.g., 'MIN-E-001')

    Returns:
        Scenario dictionary

    Raises:
        ValueError: If scenario_id not found
    """
    all_scenarios = load_scenarios()
    for scenario in all_scenarios["scenarios"]:
        if scenario["scenario_id"] == scenario_id:
            return scenario
    raise ValueError(f"Scenario not found: {scenario_id}")


@pytest.mark.integration
@pytest.mark.engineer
class TestEngineerCodeMinimization:
    """Integration tests for Code Minimization Mandate (MIN-E-001 to MIN-E-010).

    These tests validate that the Engineer Agent follows the code minimization
    mandate by:
    - Searching for existing code before implementing new features
    - Extending existing modules over creating new files
    - Reporting LOC delta and reuse rate
    - Identifying consolidation opportunities
    - Preferring configuration-driven solutions

    All tests use compliant mock responses and expect metric thresholds to pass.
    """

    @pytest.fixture
    def metric(self) -> CodeMinimizationMetric:
        """Create CodeMinimizationMetric with default threshold (0.8)."""
        return CodeMinimizationMetric(threshold=0.8)

    @pytest.mark.parametrize(
        "scenario_id",
        [
            "MIN-E-001",  # Search-First Before Implementation
            "MIN-E-002",  # Extend Existing vs Create New
            "MIN-E-003",  # LOC Delta Reporting
            "MIN-E-004",  # Reuse Rate Calculation
            "MIN-E-005",  # Consolidation Opportunities
            "MIN-E-006",  # Config vs Code Approach
            "MIN-E-007",  # Function Extraction Over Duplication
            "MIN-E-008",  # Shared Utility Creation
            "MIN-E-009",  # Data-Driven Implementation
            "MIN-E-010",  # Zero Net LOC Feature Addition
        ],
    )
    def test_scenario(self, scenario_id: str, metric: CodeMinimizationMetric):
        """Test code minimization compliance for each scenario.

        Args:
            scenario_id: ID of the scenario to test
            metric: CodeMinimizationMetric instance

        Validates:
            - Compliant response passes metric threshold (≥0.8)
            - Response demonstrates search-first behavior
            - LOC delta and reuse rate are reported
            - Consolidation opportunities identified
            - Configuration-driven approach preferred
        """
        scenario = get_scenario_by_id(scenario_id)

        # Create test case with compliant response
        test_case = LLMTestCase(
            input=scenario["input"]["user_request"],
            actual_output=scenario["mock_response"]["compliant"],
        )

        # Measure metric score
        score = metric.measure(test_case)

        # Assert compliant response meets threshold
        assert score >= metric.threshold, (
            f"Scenario {scenario_id} failed Code Minimization metric\n"
            f"Score: {score:.2f} (threshold: {metric.threshold})\n"
            f"Reason: {metric.reason}\n"
            f"Expected: {scenario['success_criteria']}\n"
        )


@pytest.mark.integration
@pytest.mark.engineer
class TestEngineerConsolidation:
    """Integration tests for Consolidation & Duplicate Elimination (CONS-E-001 to CONS-E-007).

    These tests validate that the Engineer Agent follows the duplicate
    elimination protocol by:
    - Detecting duplicate implementations using vector search
    - Making consolidation decisions based on similarity thresholds
    - Enforcing single-path implementation (one active implementation)
    - Cleaning up session artifacts (_old, _v2, _backup files)
    - Updating all references when consolidating

    All tests use compliant mock responses and expect metric thresholds to pass.
    """

    @pytest.fixture
    def metric(self) -> ConsolidationMetric:
        """Create ConsolidationMetric with default threshold (0.85)."""
        return ConsolidationMetric(threshold=0.85)

    @pytest.mark.parametrize(
        "scenario_id",
        [
            "CONS-E-001",  # Duplicate Detection via Vector Search
            "CONS-E-002",  # Consolidation Decision Quality
            "CONS-E-003",  # Same Domain Consolidation (>80% similarity)
            "CONS-E-004",  # Different Domain Extraction (>50% similarity)
            "CONS-E-005",  # Single-Path Enforcement
            "CONS-E-006",  # Session Artifact Cleanup
            "CONS-E-007",  # Reference Update After Consolidation
        ],
    )
    def test_scenario(self, scenario_id: str, metric: ConsolidationMetric):
        """Test consolidation compliance for each scenario.

        Args:
            scenario_id: ID of the scenario to test
            metric: ConsolidationMetric instance

        Validates:
            - Compliant response passes metric threshold (≥0.85)
            - Duplicate detection is performed using vector search
            - Consolidation decisions follow similarity thresholds
            - References are properly updated after consolidation
            - Session artifacts are cleaned up
        """
        scenario = get_scenario_by_id(scenario_id)

        # Create test case with compliant response
        test_case = LLMTestCase(
            input=scenario["input"]["user_request"],
            actual_output=scenario["mock_response"]["compliant"],
        )

        # Measure metric score
        score = metric.measure(test_case)

        # Assert compliant response meets threshold
        assert score >= metric.threshold, (
            f"Scenario {scenario_id} failed Consolidation metric\n"
            f"Score: {score:.2f} (threshold: {metric.threshold})\n"
            f"Reason: {metric.reason}\n"
            f"Expected: {scenario['success_criteria']}\n"
        )


@pytest.mark.integration
@pytest.mark.engineer
class TestEngineerAntiPattern:
    """Integration tests for Anti-Pattern Avoidance (ANTI-E-001 to ANTI-E-005).

    These tests validate that the Engineer Agent avoids common anti-patterns:
    - No mock data in production code (only in tests)
    - No silent fallback behavior (explicit error handling)
    - Proper error propagation (log + raise, not catch + ignore)
    - Documented configuration defaults (with justification)
    - Graceful degradation only when appropriate (with logging)

    All tests use compliant mock responses and expect metric thresholds to pass.
    """

    @pytest.fixture
    def metric(self) -> AntiPatternDetectionMetric:
        """Create AntiPatternDetectionMetric with default threshold (0.9)."""
        return AntiPatternDetectionMetric(threshold=0.9)

    @pytest.mark.parametrize(
        "scenario_id",
        [
            "ANTI-E-001",  # No Mock Data in Production
            "ANTI-E-002",  # No Silent Fallback Behavior
            "ANTI-E-003",  # Explicit Error Propagation
            "ANTI-E-004",  # Acceptable Config Defaults
            "ANTI-E-005",  # Graceful Degradation with Logging
        ],
    )
    def test_scenario(self, scenario_id: str, metric: AntiPatternDetectionMetric):
        """Test anti-pattern avoidance for each scenario.

        Args:
            scenario_id: ID of the scenario to test
            metric: AntiPatternDetectionMetric instance

        Validates:
            - Compliant response passes metric threshold (≥0.9)
            - No mock data in production code
            - Error handling is explicit (not silent)
            - Fallbacks are justified and documented
            - Graceful degradation includes logging
        """
        scenario = get_scenario_by_id(scenario_id)

        # Create test case with compliant response
        test_case = LLMTestCase(
            input=scenario["input"]["user_request"],
            actual_output=scenario["mock_response"]["compliant"],
        )

        # Measure metric score
        score = metric.measure(test_case)

        # Assert compliant response meets threshold
        assert score >= metric.threshold, (
            f"Scenario {scenario_id} failed Anti-Pattern Detection metric\n"
            f"Score: {score:.2f} (threshold: {metric.threshold})\n"
            f"Reason: {metric.reason}\n"
            f"Expected: {scenario['success_criteria']}\n"
        )


@pytest.mark.integration
@pytest.mark.engineer
class TestEngineerProcessManagement:
    """Integration tests for Test Process Management & Debugging (PROC-E-001 to PROC-E-003).

    These tests validate that the Engineer Agent follows proper test process
    management and debugging protocols:
    - Always uses non-interactive mode for test execution (CI=true)
    - Verifies process cleanup after test runs
    - Follows debug-first protocol (identify root cause before fixing)

    All tests use compliant mock responses and expect metric thresholds to pass.
    """

    @pytest.fixture
    def code_min_metric(self) -> CodeMinimizationMetric:
        """Create CodeMinimizationMetric for debugging scenarios (threshold 0.8)."""
        return CodeMinimizationMetric(threshold=0.8)

    @pytest.fixture
    def anti_pattern_metric(self) -> AntiPatternDetectionMetric:
        """Create AntiPatternDetectionMetric for test process scenarios (threshold 0.9)."""
        return AntiPatternDetectionMetric(threshold=0.9)

    @pytest.mark.parametrize(
        "scenario_id,metric_type",
        [
            ("PROC-E-001", "anti_pattern"),  # Non-Interactive Test Execution
            ("PROC-E-002", "anti_pattern"),  # Process Cleanup Verification
            ("PROC-E-003", "code_min"),      # Debug-First Protocol
        ],
    )
    def test_scenario(
        self,
        scenario_id: str,
        metric_type: str,
        code_min_metric: CodeMinimizationMetric,
        anti_pattern_metric: AntiPatternDetectionMetric,
    ):
        """Test process management compliance for each scenario.

        Args:
            scenario_id: ID of the scenario to test
            metric_type: Which metric to apply ('code_min' or 'anti_pattern')
            code_min_metric: CodeMinimizationMetric for debugging scenarios
            anti_pattern_metric: AntiPatternDetectionMetric for test scenarios

        Validates:
            - Compliant response passes appropriate metric threshold
            - Test process is non-interactive (CI-safe)
            - Process cleanup is verified
            - Debug-first protocol is followed
        """
        scenario = get_scenario_by_id(scenario_id)

        # Select appropriate metric based on scenario
        if metric_type == "code_min":
            metric = code_min_metric
        else:
            metric = anti_pattern_metric

        # Create test case with compliant response
        test_case = LLMTestCase(
            input=scenario["input"]["user_request"],
            actual_output=scenario["mock_response"]["compliant"],
        )

        # Measure metric score
        score = metric.measure(test_case)

        # Assert compliant response meets threshold
        assert score >= metric.threshold, (
            f"Scenario {scenario_id} failed {metric.__class__.__name__}\n"
            f"Score: {score:.2f} (threshold: {metric.threshold})\n"
            f"Reason: {metric.reason}\n"
            f"Expected: {scenario['success_criteria']}\n"
        )


# ============================================================================
# Scenario File Integrity Tests
# ============================================================================


@pytest.mark.integration
@pytest.mark.engineer
class TestScenarioFileIntegrity:
    """Tests to verify engineer_scenarios.json structure and completeness."""

    @pytest.fixture(scope="class")
    def all_scenarios(self) -> Dict[str, Any]:
        """Load all Engineer scenarios for class-level access."""
        return load_scenarios()

    def test_total_scenario_count(self, all_scenarios: Dict[str, Any]):
        """Verify total scenario count matches expected (25)."""
        assert all_scenarios["total_scenarios"] == 25, (
            f"Expected 25 total Engineer scenarios, "
            f"got {all_scenarios['total_scenarios']}"
        )
        assert len(all_scenarios["scenarios"]) == 25, (
            f"Expected 25 scenarios in list, "
            f"got {len(all_scenarios['scenarios'])}"
        )

    def test_category_counts(self, all_scenarios: Dict[str, Any]):
        """Verify each category has expected scenario count."""
        expected_categories = {
            "code_minimization": 10,
            "consolidation": 7,
            "anti_patterns": 5,
            "process_management": 3,
        }

        for category, expected_count in expected_categories.items():
            actual_count = all_scenarios["categories"][category]["count"]
            assert actual_count == expected_count, (
                f"Category '{category}' should have {expected_count} scenarios, "
                f"got {actual_count}"
            )

    def test_scenario_structure(self, all_scenarios: Dict[str, Any]):
        """Verify each scenario has required fields."""
        required_fields = {
            "scenario_id",
            "name",
            "category",
            "priority",
            "description",
            "input",
            "expected_behavior",
            "success_criteria",
            "failure_indicators",
            "metrics",
            "mock_response",
        }

        for scenario in all_scenarios["scenarios"]:
            scenario_id = scenario.get("scenario_id", "UNKNOWN")

            # Check required fields
            missing_fields = required_fields - set(scenario.keys())
            assert not missing_fields, (
                f"Scenario {scenario_id} missing fields: {missing_fields}"
            )

            # Check mock_response has both compliant and non_compliant
            assert "compliant" in scenario["mock_response"], (
                f"Scenario {scenario_id} missing compliant mock response"
            )
            assert "non_compliant" in scenario["mock_response"], (
                f"Scenario {scenario_id} missing non_compliant mock response"
            )

    def test_scenario_ids_unique(self, all_scenarios: Dict[str, Any]):
        """Verify scenario IDs are unique."""
        scenario_ids = [s["scenario_id"] for s in all_scenarios["scenarios"]]
        duplicates = [
            sid for sid in scenario_ids if scenario_ids.count(sid) > 1
        ]

        assert not duplicates, f"Duplicate scenario IDs found: {set(duplicates)}"

    def test_metric_references(self, all_scenarios: Dict[str, Any]):
        """Verify each scenario references valid metrics."""
        valid_metrics = {
            "CodeMinimizationMetric",
            "ConsolidationMetric",
            "AntiPatternDetectionMetric",
        }

        for scenario in all_scenarios["scenarios"]:
            scenario_id = scenario["scenario_id"]
            metrics = scenario.get("metrics", {})

            # Check at least one metric is referenced
            assert metrics, f"Scenario {scenario_id} has no metrics defined"

            # Check metric names are valid
            for metric_name in metrics.keys():
                assert metric_name in valid_metrics, (
                    f"Scenario {scenario_id} references invalid metric: {metric_name}"
                )
