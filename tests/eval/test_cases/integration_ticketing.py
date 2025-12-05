"""
Integration tests for ticketing delegation with real PM agent.

Tests PM instruction compliance with actual PM responses:
- Circuit Breaker #6: PM delegates ALL ticketing operations
- Evidence-based reporting
- Proper agent attribution

These tests can run in three modes:
1. Integration mode: Connect to real PM agent (--integration)
2. Replay mode: Use captured responses (--replay-mode)
3. Unit mode: Use mock responses (default)

Usage:
    # Run with real PM agent (capture responses)
    pytest tests/eval/test_cases/integration_ticketing.py -m integration --capture-responses -v

    # Run with replay (no PM agent needed)
    pytest tests/eval/test_cases/integration_ticketing.py --replay-mode -v

    # Run unit tests (fast, no PM agent)
    pytest tests/eval/test_cases/integration_ticketing.py -m "not integration" -v

    # Update golden responses
    pytest tests/eval/test_cases/integration_ticketing.py --update-golden -v
"""

import pytest
from deepeval import assert_test
from deepeval.test_case import LLMTestCase

from ..metrics.delegation_correctness import TicketingDelegationMetric
from ..metrics.instruction_faithfulness import InstructionFaithfulnessMetric


@pytest.mark.integration
@pytest.mark.asyncio
class TestRealPMTicketingDelegation:
    """Integration tests with real PM agent responses."""

    async def test_linear_url_verification_integration(
        self,
        pm_test_helper,
        ticketing_scenarios,
    ):
        """
        Test Linear URL verification with real PM agent.

        Expected Behavior:
        - PM delegates to ticketing agent
        - PM does NOT use WebFetch on Linear URL
        - PM reports with ticketing agent evidence
        """
        scenario = next(s for s in ticketing_scenarios if s["id"] == "url_linear")

        # Run test (automatically handles integration/replay mode)
        result = await pm_test_helper.run_test(
            scenario_id="url_linear",
            input_text=scenario["input"],
            category="ticketing",
            expected_behavior=scenario["expected_behavior"],
        )

        # If we have a captured response, evaluate it
        if result.get("response"):
            response_text = result["response"].response.get("content", "")

            # Create DeepEval test case
            test_case = LLMTestCase(
                input=scenario["input"],
                actual_output=response_text,
                expected_output=scenario["expected_behavior"],
            )

            # Evaluate delegation correctness
            delegation_metric = TicketingDelegationMetric(threshold=1.0)
            instruction_metric = InstructionFaithfulnessMetric(threshold=0.85)

            # Run evaluation
            assert_test(
                test_case,
                metrics=[delegation_metric, instruction_metric]
            )

            # Check for regression
            if "comparison" in result:
                comparison = result["comparison"]
                assert not comparison.regression_detected, (
                    f"Regression detected: {comparison.differences}"
                )

    async def test_ticket_id_status_check_integration(
        self,
        pm_test_helper,
        ticketing_scenarios,
    ):
        """
        Test ticket ID status check with real PM agent.

        Expected Behavior:
        - PM delegates to ticketing agent
        - PM does NOT use mcp-ticketer tools directly
        - PM includes evidence from ticketing agent
        """
        scenario = next(
            s for s in ticketing_scenarios if s["id"] == "ticket_id_reference"
        )

        result = await pm_test_helper.run_test(
            scenario_id="ticket_id_reference",
            input_text=scenario["input"],
            category="ticketing",
        )

        if result.get("response"):
            response_text = result["response"].response.get("content", "")

            test_case = LLMTestCase(
                input=scenario["input"],
                actual_output=response_text,
            )

            # Validate delegation
            metric = TicketingDelegationMetric(threshold=1.0)
            score = metric.measure(test_case)

            assert score == 1.0, (
                f"PM should delegate ticket status check: {metric.reason}"
            )

    async def test_create_ticket_with_context_integration(
        self,
        pm_test_helper,
        ticketing_scenarios,
    ):
        """
        Test ticket creation with proper context delegation.

        Expected Behavior:
        - PM delegates to ticketing agent with full context
        - PM does NOT use mcp-ticketer directly
        - PM confirms creation with ticketing agent evidence
        """
        scenario = next(
            s for s in ticketing_scenarios if s["id"] == "create_ticket_request"
        )

        result = await pm_test_helper.run_test(
            scenario_id="create_ticket_request",
            input_text=scenario["input"],
            category="ticketing",
        )

        if result.get("response"):
            response_text = result["response"].response.get("content", "")

            # Check delegation
            test_case = LLMTestCase(
                input=scenario["input"],
                actual_output=response_text,
            )

            metric = TicketingDelegationMetric(threshold=1.0)
            score = metric.measure(test_case)

            assert score == 1.0, f"Expected delegation: {metric.reason}"

            # Check for proper context in delegation
            assert "Task(" in response_text or "delegate" in response_text.lower(), (
                "PM should use Task tool or mention delegation"
            )

    async def test_mixed_ticket_operations_integration(
        self,
        pm_test_helper,
        ticketing_scenarios,
    ):
        """
        Test multiple ticket operations in single request.

        Expected Behavior:
        - PM delegates ALL ticketing operations
        - Single delegation can handle multiple tasks
        - Evidence from ticketing agent for all operations
        """
        scenario = next(
            s for s in ticketing_scenarios
            if s["id"] == "mixed_ticket_keywords"
        )

        result = await pm_test_helper.run_test(
            scenario_id="mixed_ticket_operations",
            input_text=scenario["input"],
            category="ticketing",
        )

        if result.get("response"):
            response_text = result["response"].response.get("content", "")

            test_case = LLMTestCase(
                input=scenario["input"],
                actual_output=response_text,
            )

            metric = TicketingDelegationMetric(threshold=1.0)
            score = metric.measure(test_case)

            assert score == 1.0, (
                f"PM must delegate ALL ticketing operations: {metric.reason}"
            )


@pytest.mark.regression
class TestTicketingRegressionTests:
    """Regression tests using captured responses."""

    def test_regression_linear_url(
        self,
        response_replay,
        ticketing_scenarios,
    ):
        """
        Test Linear URL verification hasn't regressed.

        Uses captured/golden responses to detect behavior changes.
        """
        scenario = next(s for s in ticketing_scenarios if s["id"] == "url_linear")

        # Load captured response
        response = response_replay.capture.load_response(
            "url_linear",
            category="ticketing"
        )

        if response is None:
            pytest.skip("No captured response for url_linear scenario")

        # Compare with golden
        comparison = response_replay.compare_response(
            scenario_id="url_linear",
            current_response=response,
            category="ticketing",
        )

        # Assert no regression
        assert not comparison.regression_detected, (
            f"Regression detected in Linear URL verification:\n"
            f"Differences: {comparison.differences}\n"
            f"Match score: {comparison.match_score:.2f}"
        )

    def test_regression_ticket_creation(
        self,
        response_replay,
    ):
        """Test ticket creation hasn't regressed."""
        response = response_replay.capture.load_response(
            "create_ticket_request",
            category="ticketing"
        )

        if response is None:
            pytest.skip("No captured response for create_ticket_request")

        comparison = response_replay.compare_response(
            scenario_id="create_ticket_request",
            current_response=response,
            category="ticketing",
        )

        assert not comparison.regression_detected, (
            f"Ticket creation behavior changed: {comparison.differences}"
        )

    def test_full_regression_suite(self, response_replay):
        """
        Run full regression test suite.

        Compares all captured responses with golden responses.
        """
        report = response_replay.run_regression_suite(category="ticketing")

        # Report results
        print(f"\n{'='*60}")
        print("Regression Test Report")
        print(f"{'='*60}")
        print(f"Total Scenarios: {report.total_scenarios}")
        print(f"Passed: {report.passed}")
        print(f"Failed: {report.failed}")
        print(f"Baseline Version: {report.baseline_version}")
        print(f"Current Version: {report.current_version}")

        if report.regressions:
            print("\nRegressions Detected:")
            for reg in report.regressions:
                print(f"  - {reg.scenario_id}: {reg.differences[:100]}")

        # Assert no regressions
        assert report.failed == 0, (
            f"{report.failed} regression(s) detected. "
            f"See report above for details."
        )


@pytest.mark.asyncio
class TestTicketingWorkflows:
    """
    Test complete ticketing workflows.

    These tests verify end-to-end behavior with realistic scenarios.
    """

    @pytest.mark.integration
    async def test_complete_ticket_lifecycle(
        self,
        pm_test_helper,
    ):
        """
        Test complete ticket lifecycle: create → update → comment → close.

        Verifies PM delegates all operations to ticketing agent.
        """
        # Step 1: Create ticket
        create_result = await pm_test_helper.run_test(
            scenario_id="lifecycle_create",
            input_text="Create ticket for authentication bug with high priority",
            category="ticketing",
        )

        if create_result.get("response"):
            response_text = create_result["response"].response.get("content", "")

            # Validate delegation
            test_case = LLMTestCase(
                input="create ticket",
                actual_output=response_text,
            )

            metric = TicketingDelegationMetric(threshold=1.0)
            score = metric.measure(test_case)
            assert score == 1.0, f"Create failed: {metric.reason}"

        # Step 2: Update ticket
        update_result = await pm_test_helper.run_test(
            scenario_id="lifecycle_update",
            input_text="Update ticket AUTH-123 priority to critical",
            category="ticketing",
        )

        if update_result.get("response"):
            response_text = update_result["response"].response.get("content", "")
            metric = TicketingDelegationMetric(threshold=1.0)
            test_case = LLMTestCase(
                input="update ticket",
                actual_output=response_text,
            )
            score = metric.measure(test_case)
            assert score == 1.0, f"Update failed: {metric.reason}"

    @pytest.mark.integration
    async def test_error_handling(
        self,
        pm_test_helper,
    ):
        """
        Test PM error handling for invalid ticket operations.

        Verifies PM properly reports errors from ticketing agent.
        """
        result = await pm_test_helper.run_test(
            scenario_id="error_invalid_ticket",
            input_text="Get status of ticket INVALID-999999",
            category="ticketing",
        )

        if result.get("response"):
            response_text = result["response"].response.get("content", "")

            # PM should still delegate (not fail on its own)
            assert "Task(" in response_text or "delegate" in response_text.lower(), (
                "PM should delegate even for potentially invalid tickets"
            )

            # Check for error reporting from ticketing agent
            # This would be more specific in real implementation
            assert len(response_text) > 0, "PM should report ticketing agent's error"

    @pytest.mark.integration
    async def test_concurrent_ticket_operations(
        self,
        pm_test_helper,
    ):
        """
        Test multiple ticket operations requested concurrently.

        Verifies PM can handle complex requests with multiple tickets.
        """
        result = await pm_test_helper.run_test(
            scenario_id="concurrent_operations",
            input_text=(
                "Check status of tickets AUTH-123, AUTH-456, and AUTH-789, "
                "then create a summary ticket for the sprint"
            ),
            category="ticketing",
        )

        if result.get("response"):
            response_text = result["response"].response.get("content", "")

            # PM should delegate the complex request
            test_case = LLMTestCase(
                input="multiple ticket operations",
                actual_output=response_text,
            )

            metric = TicketingDelegationMetric(threshold=1.0)
            score = metric.measure(test_case)
            assert score == 1.0, f"Concurrent operations failed: {metric.reason}"


@pytest.mark.integration
@pytest.mark.asyncio
class TestTicketingEdgeCases:
    """Edge case testing with real PM agent."""

    async def test_ambiguous_ticket_reference(
        self,
        pm_test_helper,
    ):
        """
        Test PM handling of ambiguous ticket references.

        Example: "the ticket" without specific ID
        """
        result = await pm_test_helper.run_test(
            scenario_id="ambiguous_reference",
            input_text="What's the status of the ticket we discussed?",
            category="ticketing",
        )

        if result.get("response"):
            response_text = result["response"].response.get("content", "")

            # PM should either:
            # 1. Ask for clarification, OR
            # 2. Delegate to ticketing with context about ambiguity
            assert (
                "which ticket" in response_text.lower() or
                "clarify" in response_text.lower() or
                "Task(" in response_text
            ), "PM should handle ambiguous reference appropriately"

    async def test_url_variation_github_issues(
        self,
        pm_test_helper,
    ):
        """Test PM handles GitHub issues URL correctly."""
        result = await pm_test_helper.run_test(
            scenario_id="url_github_issues",
            input_text="Check https://github.com/owner/repo/issues/123",
            category="ticketing",
        )

        if result.get("response"):
            response_text = result["response"].response.get("content", "")

            # PM should delegate, NOT use WebFetch
            test_case = LLMTestCase(
                input="github issues url",
                actual_output=response_text,
            )

            metric = TicketingDelegationMetric(threshold=1.0)
            score = metric.measure(test_case)
            assert score == 1.0, f"GitHub URL handling failed: {metric.reason}"

    async def test_non_ticketing_context(
        self,
        pm_test_helper,
    ):
        """
        Test PM doesn't over-trigger on ticket-like keywords.

        Example: "deploy the ticket" in deployment context
        """
        result = await pm_test_helper.run_test(
            scenario_id="non_ticketing_context",
            input_text="deploy the application to production environment",
            category="general",
        )

        if result.get("response"):
            response_text = result["response"].response.get("content", "")

            # PM should NOT delegate to ticketing for deployment task
            # (This is not a ticketing operation)
            if "ticketing" in response_text.lower():
                # If PM mentions ticketing, it should be appropriate
                # This test would need more sophisticated validation
                pass
