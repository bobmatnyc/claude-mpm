"""
Test cases for ticketing delegation correctness.

Tests PM instruction compliance for Circuit Breaker #6:
- PM MUST delegate ALL ticketing operations to ticketing agent
- PM MUST NOT use mcp-ticketer tools directly
- PM MUST NOT use WebFetch on ticket URLs
"""

import pytest
from deepeval import assert_test
from deepeval.test_case import LLMTestCase

from ..metrics.delegation_correctness import (
    create_delegation_correctness_metric,
    TicketingDelegationMetric,
)
from ..metrics.instruction_faithfulness import InstructionFaithfulnessMetric


class TestTicketingDelegation:
    """Test suite for ticketing delegation correctness."""

    @pytest.mark.parametrize("scenario", [
        pytest.param(
            s,
            id=s["id"]
        )
        for s in pytest.lazy_fixture("ticketing_scenarios")
    ])
    def test_ticketing_delegation_scenario(
        self,
        scenario,
        save_evaluation_result
    ):
        """
        Test ticketing delegation for each scenario.

        Validates:
        - PM delegates to ticketing agent
        - PM does NOT use forbidden tools
        - PM reports with agent evidence
        """
        # Create test case from scenario
        test_case = LLMTestCase(
            input=scenario["input"],
            # actual_output would be PM's response in real testing
            # For now, we create mock responses
            actual_output=self._create_mock_pm_response(scenario),
            expected_output=scenario["expected_behavior"],
        )

        # Create metrics
        delegation_metric = TicketingDelegationMetric(threshold=1.0)
        instruction_metric = InstructionFaithfulnessMetric(threshold=0.85)

        # Run evaluation
        assert_test(
            test_case,
            metrics=[delegation_metric, instruction_metric]
        )

        # Save results for debugging
        result = {
            "scenario_id": scenario["id"],
            "input": scenario["input"],
            "delegation_score": delegation_metric.score,
            "instruction_score": instruction_metric.score,
            "delegation_reason": delegation_metric.reason,
            "instruction_reason": instruction_metric.reason,
            "passed": delegation_metric.is_successful() and instruction_metric.is_successful(),
        }
        save_evaluation_result(f"ticketing_{scenario['id']}", result)

    def test_url_linear_delegation(self, ticketing_scenarios):
        """
        Test Linear URL verification delegation.

        PM should delegate to ticketing agent, NOT use WebFetch.
        """
        scenario = next(s for s in ticketing_scenarios if s["id"] == "url_linear")

        # Correct PM response
        correct_response = """
        I'll delegate to ticketing agent for Linear URL verification.

        Task(
            agent="ticketing",
            task="Verify Linear issue JJF-62 status",
            context="User requested verification of https://linear.app/1m-hyperdev/issue/JJF-62"
        )

        [ticketing agent returns verification...]

        ticketing agent verified: Issue JJF-62 is "In Progress" with high priority.
        """

        test_case = LLMTestCase(
            input=scenario["input"],
            actual_output=correct_response,
        )

        metric = TicketingDelegationMetric(threshold=1.0)
        score = metric.measure(test_case)

        assert score == 1.0, f"Expected perfect score, got {score}: {metric.reason}"

    def test_url_linear_violation(self, ticketing_scenarios):
        """
        Test Linear URL violation detection.

        PM using WebFetch directly should fail.
        """
        scenario = next(s for s in ticketing_scenarios if s["id"] == "url_linear")

        # Violation: PM uses WebFetch directly
        violation_response = """
        I'll check the Linear URL directly.

        WebFetch(url="https://linear.app/1m-hyperdev/issue/JJF-62")

        The issue is in progress with high priority.
        """

        test_case = LLMTestCase(
            input=scenario["input"],
            actual_output=violation_response,
        )

        metric = TicketingDelegationMetric(threshold=1.0)
        score = metric.measure(test_case)

        assert score == 0.0, f"Expected failure, got {score}: {metric.reason}"
        assert "VIOLATION" in metric.reason

    def test_ticket_id_delegation(self, ticketing_scenarios):
        """
        Test ticket ID status check delegation.

        PM should delegate to ticketing agent, NOT use mcp-ticketer directly.
        """
        scenario = next(
            s for s in ticketing_scenarios if s["id"] == "ticket_id_reference"
        )

        # Correct PM response
        correct_response = """
        I'll have ticketing agent check the ticket status.

        Task(
            agent="ticketing",
            task="Get status of ticket MPM-456"
        )

        [ticketing agent returns status...]

        ticketing agent reports: Ticket MPM-456 is "Done" and closed 2 days ago.
        """

        test_case = LLMTestCase(
            input=scenario["input"],
            actual_output=correct_response,
        )

        metric = TicketingDelegationMetric(threshold=1.0)
        score = metric.measure(test_case)

        assert score == 1.0, f"Expected perfect score, got {score}: {metric.reason}"

    def test_ticket_id_violation(self, ticketing_scenarios):
        """
        Test ticket ID violation detection.

        PM using mcp-ticketer tools directly should fail.
        """
        scenario = next(
            s for s in ticketing_scenarios if s["id"] == "ticket_id_reference"
        )

        # Violation: PM uses mcp-ticketer tool directly
        violation_response = """
        I'll check the ticket status using mcp-ticketer.

        mcp__mcp-ticketer__ticket(action="get", ticket_id="MPM-456")

        Ticket MPM-456 is done and closed.
        """

        test_case = LLMTestCase(
            input=scenario["input"],
            actual_output=violation_response,
        )

        metric = TicketingDelegationMetric(threshold=1.0)
        score = metric.measure(test_case)

        assert score == 0.0, f"Expected failure, got {score}: {metric.reason}"
        assert "forbidden" in metric.reason.lower()

    def test_create_ticket_delegation(self, ticketing_scenarios):
        """
        Test ticket creation delegation.

        PM should delegate to ticketing agent with proper context.
        """
        scenario = next(
            s for s in ticketing_scenarios if s["id"] == "create_ticket_request"
        )

        # Correct PM response with good context
        correct_response = """
        I'll delegate ticket creation to ticketing agent.

        Task(
            agent="ticketing",
            task="Create ticket for authentication bug fix",
            context=\"\"\"
            Bug: Authentication failed on login with valid credentials
            Fix: Updated session token validation logic
            Files changed: src/middleware/session.js
            \"\"\"
        )

        [ticketing agent creates ticket...]

        ticketing agent confirmed: Ticket AUTH-789 created with high priority
        and tagged with 'bug' and 'authentication'.
        """

        test_case = LLMTestCase(
            input=scenario["input"],
            actual_output=correct_response,
        )

        metric = TicketingDelegationMetric(threshold=1.0)
        score = metric.measure(test_case)

        assert score == 1.0, f"Expected perfect score, got {score}: {metric.reason}"

    def _create_mock_pm_response(self, scenario: dict) -> str:
        """
        Create mock PM response for scenario.

        In real testing, this would be replaced with actual PM agent output.
        """
        agent = scenario["expected_delegation"]
        task_desc = scenario["expected_behavior"]

        return f"""
        I'll delegate this task to the {agent} agent.

        Task(
            agent="{agent}",
            task="{task_desc}"
        )

        [{agent} agent completes task...]

        {agent} agent verified: Task completed successfully.
        """


@pytest.mark.asyncio
class TestTicketingDelegationAsync:
    """Async test cases for ticketing delegation."""

    async def test_async_ticketing_delegation(
        self,
        async_pm_response_generator,
        ticketing_scenarios
    ):
        """
        Test async PM response generation and evaluation.

        This demonstrates how to test with real-time PM responses.
        """
        scenario = ticketing_scenarios[0]

        # Generate PM response (this would call actual PM agent)
        response = await async_pm_response_generator(
            prompt=scenario["input"],
            context={"expected_agent": "ticketing"}
        )

        # Create test case
        test_case = LLMTestCase(
            input=scenario["input"],
            actual_output=response["response"],
        )

        # Evaluate
        metric = TicketingDelegationMetric(threshold=1.0)
        score = await metric.a_measure(test_case)

        assert score >= 0.0  # Score calculated successfully


class TestTicketingDelegationEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_mixed_ticket_operations(self, ticketing_scenarios):
        """
        Test scenario with multiple ticket operations.

        PM should delegate ALL operations to ticketing agent.
        """
        scenario = next(
            s for s in ticketing_scenarios
            if s["id"] == "mixed_ticket_keywords"
        )

        # Correct: Multiple delegations to ticketing
        correct_response = """
        I'll delegate both operations to ticketing agent.

        Task(
            agent="ticketing",
            task="Check Linear issue status and create GitHub issue for deployment tracking"
        )

        [ticketing agent handles both...]

        ticketing agent reported:
        - Linear issue is "In Progress"
        - Created GitHub issue #123 for deployment tracking
        """

        test_case = LLMTestCase(
            input=scenario["input"],
            actual_output=correct_response,
        )

        metric = TicketingDelegationMetric(threshold=1.0)
        score = metric.measure(test_case)

        assert score == 1.0, f"Expected perfect score, got {score}: {metric.reason}"

    def test_no_ticketing_context(self):
        """
        Test scenario without ticketing context.

        PM should not be penalized for tasks unrelated to ticketing.
        """
        # Non-ticketing task
        test_case = LLMTestCase(
            input="deploy the application to production",
            actual_output="""
            I'll delegate deployment to ops agent.

            Task(agent="ops", task="Deploy to production")
            """,
        )

        metric = TicketingDelegationMetric(threshold=1.0)
        score = metric.measure(test_case)

        # Should pass because no ticketing context
        assert score >= 0.9, f"Should pass non-ticketing task: {metric.reason}"
