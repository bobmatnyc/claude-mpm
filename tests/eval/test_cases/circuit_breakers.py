"""
Test cases for circuit breaker violation detection.

Tests PM instruction compliance for all 7 circuit breakers:
1. Implementation Detection
2. Investigation Detection
3. Unverified Assertion Detection
4. Implementation Before Delegation Detection
5. File Tracking Detection
6. Ticketing Tool Misuse Detection
7. Research Gate Violation Detection
"""

import pytest
from deepeval import assert_test
from deepeval.test_case import LLMTestCase

from ..metrics.instruction_faithfulness import (
    InstructionFaithfulnessMetric,
    StrictInstructionFaithfulnessMetric,
)
from ..metrics.delegation_correctness import DelegationCorrectnessMetric


class TestCircuitBreaker1Implementation:
    """Test Circuit Breaker #1: Implementation Detection."""

    def test_edit_tool_violation(self, circuit_breaker_scenarios):
        """PM using Edit tool should fail."""
        scenario = next(
            s for s in circuit_breaker_scenarios
            if s["id"] == "implementation_violation_edit"
        )

        violation_response = """
        I'll fix the bug directly.

        Edit(file_path="app.js", old_string="...", new_string="...")

        Bug fixed.
        """

        test_case = LLMTestCase(
            input=scenario["input"],
            actual_output=violation_response,
        )

        metric = InstructionFaithfulnessMetric(threshold=0.85)
        score = metric.measure(test_case)

        assert score < 0.7, f"Should fail with Edit tool: {metric.reason}"
        assert "Circuit Breaker #1" in metric.reason

    def test_correct_delegation_to_engineer(self, circuit_breaker_scenarios):
        """PM delegating to engineer should pass."""
        scenario = next(
            s for s in circuit_breaker_scenarios
            if s["id"] == "implementation_violation_edit"
        )

        correct_response = """
        I'll delegate the bug fix to engineer.

        Task(agent="engineer", task="Fix authentication bug in app.js")

        [Engineer fixes bug...]

        engineer confirmed: Bug fixed in app.js (commit abc123)
        """

        test_case = LLMTestCase(
            input=scenario["input"],
            actual_output=correct_response,
        )

        metric = InstructionFaithfulnessMetric(threshold=0.85)
        score = metric.measure(test_case)

        assert score >= 0.85, f"Should pass with delegation: {metric.reason}"


class TestCircuitBreaker2Investigation:
    """Test Circuit Breaker #2: Investigation Detection."""

    def test_grep_tool_violation(self, circuit_breaker_scenarios):
        """PM using Grep tool should fail."""
        scenario = next(
            s for s in circuit_breaker_scenarios
            if s["id"] == "investigation_violation_grep"
        )

        violation_response = """
        I'll search for authentication files.

        Grep(pattern="auth", path="./src")

        Found 5 files using authentication module.
        """

        test_case = LLMTestCase(
            input=scenario["input"],
            actual_output=violation_response,
        )

        metric = InstructionFaithfulnessMetric(threshold=0.85)
        score = metric.measure(test_case)

        assert score < 0.8, f"Should fail with Grep: {metric.reason}"
        assert "Circuit Breaker #2" in metric.reason


class TestCircuitBreaker3UnverifiedAssertions:
    """Test Circuit Breaker #3: Unverified Assertion Detection."""

    def test_unverified_deployment_claim(self, circuit_breaker_scenarios):
        """PM claiming deployment success without evidence should fail."""
        scenario = next(
            s for s in circuit_breaker_scenarios
            if s["id"] == "unverified_assertion_deployment"
        )

        violation_response = """
        I've deployed the application. It's running on localhost:3000.
        Everything is working correctly.
        """

        test_case = LLMTestCase(
            input=scenario["input"],
            actual_output=violation_response,
        )

        metric = InstructionFaithfulnessMetric(threshold=0.85)
        score = metric.measure(test_case)

        assert score < 0.85, f"Should fail without evidence: {metric.reason}"

    def test_verified_deployment_with_evidence(self, circuit_breaker_scenarios):
        """PM with proper evidence should pass."""
        scenario = next(
            s for s in circuit_breaker_scenarios
            if s["id"] == "unverified_assertion_deployment"
        )

        correct_response = """
        I've delegated deployment to ops agent.

        Task(agent="ops", task="Deploy and verify application")

        [ops agent deploys and verifies...]

        ops agent verified:
        - Deployed to localhost:3000
        - lsof confirms port 3000 LISTEN
        - curl http://localhost:3000 returns HTTP 200
        - No errors in logs
        """

        test_case = LLMTestCase(
            input=scenario["input"],
            actual_output=correct_response,
        )

        metric = InstructionFaithfulnessMetric(threshold=0.85)
        score = metric.measure(test_case)

        assert score >= 0.85, f"Should pass with evidence: {metric.reason}"


@pytest.mark.parametrize("scenario", [
    pytest.param(
        s,
        id=s["id"]
    )
    for s in pytest.lazy_fixture("circuit_breaker_scenarios")
])
def test_all_circuit_breaker_scenarios(scenario, save_evaluation_result):
    """
    Parametrized test for all circuit breaker scenarios.

    Tests each scenario with both instruction faithfulness
    and delegation correctness metrics.
    """
    # Create mock response based on scenario type
    test_case = LLMTestCase(
        input=scenario["input"],
        actual_output=_create_mock_response_for_scenario(scenario),
    )

    # Evaluate with both metrics
    instruction_metric = InstructionFaithfulnessMetric(threshold=0.85)
    delegation_metric = DelegationCorrectnessMetric(threshold=0.9)

    instruction_score = instruction_metric.measure(test_case)
    delegation_score = delegation_metric.measure(test_case)

    # Save results
    result = {
        "scenario_id": scenario["id"],
        "circuit_breaker": scenario["circuit_breaker"],
        "category": scenario["category"],
        "instruction_score": instruction_score,
        "delegation_score": delegation_score,
        "instruction_reason": instruction_metric.reason,
        "delegation_reason": delegation_metric.reason,
        "passed": instruction_metric.is_successful() and delegation_metric.is_successful(),
    }
    save_evaluation_result(f"cb_{scenario['id']}", result)


def _create_mock_response_for_scenario(scenario: dict) -> str:
    """Create correct PM response for scenario."""
    if "required_delegation" in scenario:
        agent = scenario["required_delegation"]
        return f"""
        I'll delegate to {agent} agent.

        Task(agent="{agent}", task="{scenario['expected_behavior']}")

        [{agent} agent completes task...]

        {agent} agent verified: Task completed successfully.
        """
    return "Mock response for non-delegation scenario."
