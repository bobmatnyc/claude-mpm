"""
Quick-start demonstration of DeepEval framework.

Run with: pytest tests/eval/test_quickstart_demo.py -v -s
"""

import pytest
from deepeval.test_case import LLMTestCase

from .metrics.instruction_faithfulness import InstructionFaithfulnessMetric
from .metrics.delegation_correctness import (
    DelegationCorrectnessMetric,
    TicketingDelegationMetric,
)
from .utils.pm_response_parser import PMResponseParser


def test_quickstart_correct_delegation():
    """
    Demonstrate correct PM delegation behavior.

    This test shows a PM correctly delegating ticketing work.
    """
    # User request
    user_input = "verify https://linear.app/1m-hyperdev/issue/JJF-62"

    # Correct PM response (delegates to ticketing agent)
    pm_response = """
    I'll delegate this Linear URL verification to the ticketing agent.

    Task(
        agent="ticketing",
        task="Verify Linear issue JJF-62 status and report findings",
        context="User provided URL: https://linear.app/1m-hyperdev/issue/JJF-62"
    )

    [ticketing agent returns verification...]

    ticketing agent verified:
    - Issue: JJF-62
    - Status: In Progress
    - Priority: High
    - Assignee: @developer
    - Updated: 2 days ago
    """

    # Create test case
    test_case = LLMTestCase(
        input=user_input,
        actual_output=pm_response,
    )

    # Evaluate with ticketing delegation metric
    ticketing_metric = TicketingDelegationMetric(threshold=1.0)
    score = ticketing_metric.measure(test_case)

    print(f"\n✅ Ticketing Delegation Score: {score}")
    print(f"   Reason: {ticketing_metric.reason}")
    assert score == 1.0, "Should pass with perfect delegation"


def test_quickstart_violation_detection():
    """
    Demonstrate violation detection.

    This test shows PM using forbidden tools (Circuit Breaker #6).
    """
    # User request
    user_input = "check the status of ticket MPM-456"

    # VIOLATION: PM uses mcp-ticketer tool directly
    pm_response = """
    I'll check the ticket status directly.

    mcp__mcp-ticketer__ticket(action="get", ticket_id="MPM-456")

    Ticket MPM-456 is done and closed 2 days ago.
    """

    # Create test case
    test_case = LLMTestCase(
        input=user_input,
        actual_output=pm_response,
    )

    # Evaluate
    ticketing_metric = TicketingDelegationMetric(threshold=1.0)
    score = ticketing_metric.measure(test_case)

    print(f"\n❌ Violation Detected")
    print(f"   Score: {score}")
    print(f"   Reason: {ticketing_metric.reason}")
    assert score == 0.0, "Should fail with forbidden tool usage"


def test_quickstart_parser_demo():
    """
    Demonstrate PM response parser capabilities.
    """
    pm_response = """
    I'll delegate to engineer for bug fix.

    Task(agent="engineer", task="Fix authentication bug")

    [Engineer completes work...]

    engineer confirmed: Bug fixed in commit abc123.
    Files changed: src/auth.js (+15 -8 lines)

    The fix is complete and working correctly.
    """

    # Parse response
    parser = PMResponseParser()
    analysis = parser.parse(pm_response)

    print(f"\n📊 Parser Analysis:")
    print(f"   Tools used: {[t.tool_name for t in analysis.tools_used]}")
    print(f"   Delegations: {[d.agent_name for d in analysis.delegations]}")
    print(f"   Assertions: {len(analysis.assertions)}")
    print(f"   Violations: {len(analysis.violations)}")
    print(f"   Evidence score: {analysis.evidence_quality_score:.2f}")
    print(f"   Delegation score: {analysis.delegation_correctness_score:.2f}")

    # Verify analysis
    assert len(analysis.tools_used) > 0, "Should detect Task tool"
    assert len(analysis.delegations) == 1, "Should detect one delegation"
    assert analysis.delegations[0].agent_name == "engineer", "Should identify engineer"
    assert analysis.evidence_quality_score > 0.5, "Should have some evidence"


def test_quickstart_multiple_metrics():
    """
    Demonstrate using multiple metrics together.
    """
    user_input = "implement user authentication"
    pm_response = """
    I'll delegate to research agent first to investigate options.

    Task(
        agent="research",
        task="Research authentication approaches for Express.js app"
    )

    [Research returns findings...]

    research agent recommended OAuth2 with Auth0. I'll now delegate implementation.

    Task(
        agent="engineer",
        task="Implement OAuth2 authentication with Auth0",
        context="Based on research findings: OAuth2 recommended for security and scalability"
    )

    [Engineer implements...]

    engineer confirmed: OAuth2 implemented successfully.
    Test results: All 24 authentication tests passing.
    """

    test_case = LLMTestCase(
        input=user_input,
        actual_output=pm_response,
    )

    # Multiple metrics
    instruction_metric = InstructionFaithfulnessMetric(threshold=0.85)
    delegation_metric = DelegationCorrectnessMetric(threshold=0.9)

    instruction_score = instruction_metric.measure(test_case)
    delegation_score = delegation_metric.measure(test_case)

    print(f"\n📈 Multi-Metric Evaluation:")
    print(f"   Instruction Faithfulness: {instruction_score:.2f} - {instruction_metric.reason}")
    print(f"   Delegation Correctness: {delegation_score:.2f} - {delegation_metric.reason}")

    assert instruction_score >= 0.85, "Should pass instruction faithfulness"
    assert delegation_score >= 0.9, "Should pass delegation correctness"
    print("\n✅ All metrics passed!")


if __name__ == "__main__":
    """Run quick demos directly."""
    print("="*60)
    print("DeepEval Framework Quick-Start Demo")
    print("="*60)

    print("\n1. Testing Correct Delegation...")
    test_quickstart_correct_delegation()

    print("\n2. Testing Violation Detection...")
    test_quickstart_violation_detection()

    print("\n3. Testing Parser Demo...")
    test_quickstart_parser_demo()

    print("\n4. Testing Multiple Metrics...")
    test_quickstart_multiple_metrics()

    print("\n" + "="*60)
    print("✅ All demos completed successfully!")
    print("="*60)
