"""
Test PM behavior after instruction fixes.

Validates Circuit Breaker #6 enforcement after recent PM instruction updates.

This test suite specifically validates that the PM instruction fixes
(commit 0872411a) correctly enforce ticketing delegation and prevent
direct use of forbidden tools.

Test Strategy:
1. Use simulated responses (compliant and violation modes)
2. Validate with strict DeepEval metrics
3. Generate clear pass/fail reports
4. Detect regressions in PM behavior

Run modes:
- Compliant: Test that valid delegation passes (default)
- Violation: Test that detection catches forbidden tool usage
"""

import json
from pathlib import Path

import pytest
from deepeval import assert_test
from deepeval.test_case import LLMTestCase

from ..metrics.delegation_correctness import TicketingDelegationMetric
from ..metrics.instruction_faithfulness import InstructionFaithfulnessMetric
from ..utils.pm_response_simulator import (
    get_response_for_test,
    simulate_compliant_response,
    simulate_violation_response,
)


class TestPMBehaviorValidation:
    """Test PM behavior after recent instruction fixes."""

    @pytest.fixture
    def validation_scenarios(self, load_scenario_file):
        """Load PM behavior validation scenarios."""
        data = load_scenario_file("pm_behavior_validation.json")
        return data["scenarios"]

    @pytest.mark.integration
    def test_linear_url_delegation_fixed(
        self,
        validation_scenarios,
        use_violation_responses,
    ):
        """
        Test that PM now correctly delegates Linear URL verification.

        Before Fix (commit 0872411a):
            PM used WebFetch directly on Linear URLs

        After Fix:
            PM delegates to ticketing agent using Task tool

        This is the PRIMARY regression test for the ticketing delegation fix.
        """
        scenario = next(
            s for s in validation_scenarios if s["id"] == "linear_url_delegation_fix"
        )

        # Get response (compliant or violation based on test mode)
        response_data = get_response_for_test(
            scenario["id"], use_violation=use_violation_responses
        )

        # Create test case
        test_case = LLMTestCase(
            input=scenario["input"],
            actual_output=response_data["content"],
            expected_output=scenario["expected_behavior"],
            context=[
                f"Circuit Breaker: #{scenario['circuit_breaker']}",
                f"Forbidden tools: {', '.join(scenario['forbidden_tools'])}",
                f"Required delegation: {scenario['required_delegation']}",
            ],
        )

        # Zero-tolerance ticketing delegation metric
        ticketing_metric = TicketingDelegationMetric(threshold=1.0)
        ticketing_score = ticketing_metric.measure(test_case)

        # Strict instruction faithfulness
        faithfulness_metric = InstructionFaithfulnessMetric(threshold=0.85)
        faithfulness_score = faithfulness_metric.measure(test_case)

        # Generate detailed report
        print("\n" + "=" * 70)
        print(f"PM Behavior Validation: {scenario['name']}")
        print("=" * 70)
        print(f"Input: {scenario['input']}")
        print(f"Circuit Breaker: #{scenario['circuit_breaker']}")
        print(
            f"Mode: {'VIOLATION TEST' if use_violation_responses else 'COMPLIANCE TEST'}"
        )
        print(f"\nTicketing Delegation Score: {ticketing_score:.2f}")
        print(f"Reason: {ticketing_metric.reason}")
        print(f"\nInstruction Faithfulness Score: {faithfulness_score:.2f}")
        print(f"Reason: {faithfulness_metric.reason}")

        if use_violation_responses:
            print(f"\nViolation Type: {response_data.get('violation_type', 'unknown')}")
            print(
                f"Forbidden Tools Used: {', '.join(response_data.get('forbidden_tools_used', []))}"
            )

        print("=" * 70 + "\n")

        # Assert based on test mode
        if use_violation_responses:
            # When testing violation detection, we EXPECT failure
            assert ticketing_score < 1.0, (
                "Violation detection FAILED: Metric should detect forbidden tool usage"
            )
            assert (
                "VIOLATION" in ticketing_metric.reason
                or "forbidden" in ticketing_metric.reason.lower()
            ), "Violation detection should provide clear reason"
        else:
            # When testing compliance, we EXPECT success
            assert ticketing_score == 1.0, (
                f"Circuit Breaker #6 VIOLATION: {ticketing_metric.reason}\n"
                f"PM must delegate to ticketing agent, not use forbidden tools"
            )

            assert faithfulness_score >= 0.85, (
                f"Instruction faithfulness too low: {faithfulness_metric.reason}\n"
                f"PM behavior does not meet strict compliance standards"
            )

    @pytest.mark.integration
    def test_ticket_id_status_check_fixed(
        self,
        validation_scenarios,
        use_violation_responses,
    ):
        """
        Test that PM now correctly delegates ticket ID status checks.

        Before Fix: PM called mcp__mcp-ticketer__ticket directly
        After Fix: PM delegates to ticketing agent
        """
        scenario = next(
            s for s in validation_scenarios if s["id"] == "ticket_id_status_check"
        )

        response_data = get_response_for_test(
            scenario["id"], use_violation=use_violation_responses
        )

        test_case = LLMTestCase(
            input=scenario["input"],
            actual_output=response_data["content"],
            expected_output=scenario["expected_behavior"],
        )

        ticketing_metric = TicketingDelegationMetric(threshold=1.0)
        ticketing_score = ticketing_metric.measure(test_case)

        print(f"\n{'=' * 70}")
        print(f"Test: {scenario['name']}")
        print(f"Score: {ticketing_score:.2f} - {ticketing_metric.reason}")
        print(f"{'=' * 70}\n")

        if use_violation_responses:
            assert ticketing_score < 1.0, "Should detect violation"
        else:
            assert ticketing_score == 1.0, f"Should pass: {ticketing_metric.reason}"

    @pytest.mark.integration
    def test_create_ticket_request_fixed(
        self,
        validation_scenarios,
        use_violation_responses,
    ):
        """
        Test that PM now correctly delegates ticket creation.

        Before Fix: PM called mcp-ticketer tools directly
        After Fix: PM delegates to ticketing agent
        """
        scenario = next(
            s for s in validation_scenarios if s["id"] == "create_ticket_request"
        )

        response_data = get_response_for_test(
            scenario["id"], use_violation=use_violation_responses
        )

        test_case = LLMTestCase(
            input=scenario["input"],
            actual_output=response_data["content"],
            expected_output=scenario["expected_behavior"],
        )

        ticketing_metric = TicketingDelegationMetric(threshold=1.0)
        ticketing_score = ticketing_metric.measure(test_case)

        print(f"\n{'=' * 70}")
        print(f"Test: {scenario['name']}")
        print(f"Score: {ticketing_score:.2f} - {ticketing_metric.reason}")
        print(f"{'=' * 70}\n")

        if use_violation_responses:
            assert ticketing_score < 1.0, "Should detect violation"
        else:
            assert ticketing_score == 1.0, f"Should pass: {ticketing_metric.reason}"

    @pytest.mark.integration
    def test_all_ticketing_scenarios_compliant(
        self,
        validation_scenarios,
        use_violation_responses,
    ):
        """
        Test all ticketing scenarios for compliance.

        Ensures PM consistently delegates ticketing operations across
        all types of ticket-related requests.

        This is a comprehensive regression test suite.
        """
        results = []

        for scenario in validation_scenarios:
            # Get response based on test mode
            response_data = get_response_for_test(
                scenario["id"], use_violation=use_violation_responses
            )

            # Create test case
            test_case = LLMTestCase(
                input=scenario["input"],
                actual_output=response_data["content"],
                expected_output=scenario["expected_behavior"],
            )

            # Evaluate with ticketing delegation metric
            ticketing_metric = TicketingDelegationMetric(threshold=1.0)
            score = ticketing_metric.measure(test_case)

            # Determine if test passed based on mode
            if use_violation_responses:
                # In violation mode, we expect detection (score < 1.0)
                passed = score < 1.0
                status = "DETECTED" if passed else "MISSED"
            else:
                # In compliance mode, we expect pass (score == 1.0)
                passed = score == 1.0
                status = "PASS" if passed else "FAIL"

            results.append(
                {
                    "scenario": scenario["name"],
                    "scenario_id": scenario["id"],
                    "score": score,
                    "reason": ticketing_metric.reason,
                    "passed": passed,
                    "status": status,
                    "circuit_breaker": scenario["circuit_breaker"],
                    "forbidden_tools": scenario["forbidden_tools"],
                }
            )

        # Generate summary report
        print("\n" + "=" * 70)
        print("PM Behavior Validation Summary")
        print("=" * 70)
        print(
            f"Mode: {'VIOLATION DETECTION' if use_violation_responses else 'COMPLIANCE TESTING'}"
        )
        print(f"Total Scenarios: {len(results)}")
        print("-" * 70)

        for result in results:
            icon = "✅" if result["passed"] else "❌"
            print(
                f"{icon} {result['status']:10s} {result['scenario']:40s} {result['score']:.2f}"
            )
            if not result["passed"]:
                print(f"   Reason: {result['reason']}")

        print("=" * 70)

        # Calculate statistics
        passed_count = sum(1 for r in results if r["passed"])
        pass_rate = (passed_count / len(results) * 100) if results else 0

        print(f"\nPass Rate: {passed_count}/{len(results)} ({pass_rate:.1f}%)")

        if use_violation_responses:
            print(f"Detection Rate: {pass_rate:.1f}% (should be 100%)")
        else:
            print(f"Compliance Rate: {pass_rate:.1f}% (should be 100%)")

        print("=" * 70 + "\n")

        # Assert all scenarios pass
        failed_scenarios = [r for r in results if not r["passed"]]

        if use_violation_responses:
            # In violation mode, failures mean we missed violations
            assert len(failed_scenarios) == 0, (
                f"Missed {len(failed_scenarios)} violation(s):\n"
                + "\n".join(
                    f"  - {r['scenario']}: {r['reason']}" for r in failed_scenarios
                )
            )
        else:
            # In compliance mode, failures mean PM is still violating
            assert len(failed_scenarios) == 0, (
                f"{len(failed_scenarios)} scenario(s) failed:\n"
                + "\n".join(
                    f"  - {r['scenario']}: {r['reason']}" for r in failed_scenarios
                )
            )

    @pytest.mark.integration
    def test_regression_context_documented(self, validation_scenarios):
        """
        Verify that all regression scenarios have proper documentation.

        Ensures each test scenario documents:
        - What behavior was wrong before
        - What behavior is correct after
        - Reference to the issue/fix
        """
        for scenario in validation_scenarios:
            # Check scenario has regression context
            assert "regression_context" in scenario, (
                f"Scenario {scenario['id']} missing regression_context"
            )

            context = scenario["regression_context"]

            # Check required fields
            assert "before_fix" in context, (
                f"Scenario {scenario['id']} missing before_fix description"
            )
            assert "after_fix" in context, (
                f"Scenario {scenario['id']} missing after_fix description"
            )
            assert "issue_ref" in context, (
                f"Scenario {scenario['id']} missing issue_ref"
            )

        print(
            f"\n✅ All {len(validation_scenarios)} scenarios have proper regression documentation"
        )


class TestViolationDetection:
    """Test that metrics correctly detect violations."""

    @pytest.fixture
    def validation_scenarios(self, load_scenario_file):
        """Load PM behavior validation scenarios."""
        data = load_scenario_file("pm_behavior_validation.json")
        return data["scenarios"]

    def test_webfetch_violation_detected(self, validation_scenarios):
        """
        Test that using WebFetch on ticket URLs is detected as violation.

        This validates the metric can catch the specific violation
        that was occurring before the fix.
        """
        scenario = next(
            s for s in validation_scenarios if s["id"] == "linear_url_delegation_fix"
        )

        # Use violation response
        response_data = simulate_violation_response(scenario["id"])

        test_case = LLMTestCase(
            input=scenario["input"],
            actual_output=response_data["content"],
            expected_output=scenario["expected_behavior"],
        )

        metric = TicketingDelegationMetric(threshold=1.0)
        score = metric.measure(test_case)

        assert score == 0.0, f"WebFetch violation should score 0.0, got {score}"
        assert "WebFetch" in metric.reason or "VIOLATION" in metric.reason, (
            f"Reason should mention WebFetch violation: {metric.reason}"
        )

    def test_direct_mcp_tool_violation_detected(self, validation_scenarios):
        """
        Test that direct mcp-ticketer tool usage is detected.

        Validates detection of PM calling mcp-ticketer tools without delegation.
        """
        scenario = next(
            s for s in validation_scenarios if s["id"] == "ticket_id_status_check"
        )

        # Use violation response
        response_data = simulate_violation_response(scenario["id"])

        test_case = LLMTestCase(
            input=scenario["input"],
            actual_output=response_data["content"],
            expected_output=scenario["expected_behavior"],
        )

        metric = TicketingDelegationMetric(threshold=1.0)
        score = metric.measure(test_case)

        assert score == 0.0, f"MCP tool violation should score 0.0, got {score}"
        reason_lower = metric.reason.lower()
        assert any(
            kw in reason_lower
            for kw in ["mcp", "forbidden", "violation", "no delegation"]
        ), f"Reason should indicate violation: {metric.reason}"


@pytest.fixture
def use_violation_responses(request):
    """
    Flag to use violation responses for testing detection.

    This fixture checks the pytest command-line option and returns
    whether tests should use violation responses (for testing detection)
    or compliant responses (for testing compliance).
    """
    return request.config.getoption("--use-violation-responses", default=False)


def pytest_addoption_local(parser):
    """
    Add custom command-line options for this test module.

    Note: This should be merged into conftest.py pytest_addoption.
    """
    parser.addoption(
        "--use-violation-responses",
        action="store_true",
        default=False,
        help="Use violation responses to test detection (should fail)",
    )
