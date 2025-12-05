"""
Delegation Correctness Metric for PM Agent Evaluation.

This metric evaluates whether the PM agent correctly delegates work
to specialized agents instead of performing work directly.

Key checks:
- Task tool usage for delegation
- Correct agent routing (ticketing, QA, Engineer, etc.)
- No forbidden tool usage patterns
- Proper delegation context and acceptance criteria
"""

from typing import Any, Dict, List, Optional

from deepeval.metrics import BaseMetric
from deepeval.test_case import LLMTestCase

from ..utils.pm_response_parser import DelegationEvent, PMResponseParser


class DelegationCorrectnessMetric(BaseMetric):
    """
    Custom DeepEval metric for PM delegation correctness.

    Evaluates:
    1. Task tool usage (primary delegation method)
    2. Correct agent selection for task type
    3. Absence of PM doing work directly
    4. Quality of delegation context

    Scoring:
    - 1.0: Perfect delegation to correct agent
    - 0.7-0.99: Delegation occurred but wrong agent or missing context
    - 0.3-0.69: Partial delegation with some direct work
    - 0.0-0.29: No delegation, PM did work directly
    """

    # Agent specialization mapping
    AGENT_SPECIALIZATION = {
        "ticketing": ["ticket", "issue", "epic", "linear", "github issue", "jira"],
        "engineer": ["implement", "code", "fix", "refactor", "develop"],
        "research": ["investigate", "analyze", "explore", "understand", "document"],
        "qa": ["test", "verify", "validate", "check", "confirm"],
        "ops": ["deploy", "start", "stop", "configure", "setup"],
        "local-ops-agent": ["localhost", "pm2", "local server", "dev server"],
    }

    def __init__(
        self,
        threshold: float = 0.9,
        expected_agent: Optional[str] = None,
        require_context: bool = True,
    ):
        """
        Initialize DelegationCorrectnessMetric.

        Args:
            threshold: Minimum score to pass
            expected_agent: Expected agent for delegation (optional constraint)
            require_context: Whether to require delegation context
        """
        self.threshold = threshold
        self.expected_agent = expected_agent
        self.require_context = require_context
        self.parser = PMResponseParser()

    @property
    def __name__(self) -> str:
        return "Delegation Correctness"

    def measure(self, test_case: LLMTestCase) -> float:
        """
        Measure delegation correctness score.

        Args:
            test_case: DeepEval test case with input and actual_output

        Returns:
            Score from 0.0 to 1.0
        """
        # Parse PM response
        analysis = self.parser.parse(test_case.actual_output)

        # Check for delegation
        if not analysis.delegations:
            # No delegation occurred - check if PM did work directly
            if self._pm_did_work_directly(analysis):
                self.score = 0.0
                self.reason = "PM performed work directly without delegation"
                self.success = False
                return 0.0
            # No work needed, no delegation needed
            self.score = 1.0
            self.reason = "No delegation required for this task"
            self.success = True
            return 1.0

        # Delegation occurred - evaluate quality
        delegation_score = self._score_delegations(
            delegations=analysis.delegations,
            input_text=test_case.input,
            tools_used=analysis.tools_used,
        )

        # Check for expected agent constraint
        if self.expected_agent:
            has_expected = any(
                d.agent_name.lower() == self.expected_agent.lower()
                for d in analysis.delegations
            )
            if not has_expected:
                delegation_score *= 0.5  # Major penalty for wrong agent

        # Penalty for PM also doing direct work
        if self._pm_did_work_directly(analysis):
            delegation_score *= 0.6  # Delegated but also did work

        self.score = delegation_score
        self.reason = self._generate_reason(analysis, delegation_score)
        self.success = delegation_score >= self.threshold

        return delegation_score

    def _pm_did_work_directly(self, analysis) -> bool:
        """Check if PM performed work directly (violation)."""
        forbidden_tools = {"Edit", "Write", "mcp_ticketer", "Grep", "Glob"}
        return any(t.tool_name in forbidden_tools for t in analysis.tools_used)

    def _score_delegations(
        self, delegations: List[DelegationEvent], input_text: str, tools_used: List
    ) -> float:
        """
        Score delegation quality.

        Considers:
        - Agent selection appropriateness
        - Delegation context quality
        - Multiple delegations (coordination)
        """
        if not delegations:
            return 0.0

        # Check if delegated to appropriate agent
        agent_score = self._score_agent_selection(delegations, input_text)

        # Check delegation context quality
        context_score = self._score_delegation_context(delegations)

        # Check if Task tool was used properly
        has_task_tool = any(t.tool_name == "Task" for t in tools_used)
        task_tool_score = 1.0 if has_task_tool else 0.5

        # Weighted average
        return agent_score * 0.5 + context_score * 0.3 + task_tool_score * 0.2

    def _score_agent_selection(
        self, delegations: List[DelegationEvent], input_text: str
    ) -> float:
        """
        Score whether correct agent was selected for task.

        Uses keyword matching against agent specialization mapping.
        """
        input_lower = input_text.lower()

        for delegation in delegations:
            agent_name = delegation.agent_name.lower()

            # Get specialization keywords for this agent
            agent_keywords = self.AGENT_SPECIALIZATION.get(agent_name, [])

            # Check if input matches agent specialization
            if any(keyword in input_lower for keyword in agent_keywords):
                return 1.0  # Correct agent selected

        # Delegation occurred but agent may not match input
        return 0.7

    def _score_delegation_context(self, delegations: List[DelegationEvent]) -> float:
        """
        Score quality of delegation context.

        Checks:
        - Task description length/detail
        - Context provided
        - Acceptance criteria defined
        """
        if not delegations:
            return 0.0

        # Evaluate first delegation (primary task)
        delegation = delegations[0]

        score = 0.0

        # Task description quality
        if delegation.task_description and len(delegation.task_description) > 20:
            score += 0.4
        elif delegation.task_description:
            score += 0.2

        # Context provided
        if delegation.context and len(delegation.context) > 10:
            score += 0.3

        # Acceptance criteria
        if delegation.acceptance_criteria and len(delegation.acceptance_criteria) > 0:
            score += 0.3

        return min(1.0, score)

    def _generate_reason(self, analysis, score: float) -> str:
        """Generate human-readable reason for the score."""
        if score >= 0.9:
            agent_names = [d.agent_name for d in analysis.delegations]
            return f"Correct delegation to {', '.join(agent_names)}"

        reasons = []

        if not analysis.delegations:
            reasons.append("No delegation occurred")
        else:
            agent_names = [d.agent_name for d in analysis.delegations]
            reasons.append(f"Delegated to: {', '.join(agent_names)}")

        if self._pm_did_work_directly(analysis):
            forbidden_tools = [
                t.tool_name
                for t in analysis.tools_used
                if t.tool_name in {"Edit", "Write", "mcp_ticketer"}
            ]
            reasons.append(f"PM used forbidden tools: {', '.join(forbidden_tools)}")

        if self.expected_agent:
            has_expected = any(
                d.agent_name.lower() == self.expected_agent.lower()
                for d in analysis.delegations
            )
            if not has_expected:
                reasons.append(
                    f"Expected delegation to '{self.expected_agent}' not found"
                )

        return "; ".join(reasons) if reasons else "Unknown delegation issue"

    def is_successful(self) -> bool:
        """Check if metric passes threshold."""
        return self.success

    async def a_measure(self, test_case: LLMTestCase) -> float:
        """Async version of measure."""
        return self.measure(test_case)


class TicketingDelegationMetric(DelegationCorrectnessMetric):
    """
    Specialized metric for ticketing delegation correctness.

    Enforces strict requirement:
    - MUST delegate to ticketing agent for ticket operations
    - MUST NOT use mcp-ticketer tools directly
    - MUST NOT use WebFetch on ticket URLs
    """

    def __init__(self, threshold: float = 1.0):
        super().__init__(
            threshold=threshold, expected_agent="ticketing", require_context=True
        )

    def measure(self, test_case: LLMTestCase) -> float:
        """
        Measure ticketing delegation with strict enforcement.

        Zero tolerance for:
        - Direct mcp-ticketer tool usage
        - WebFetch on ticket URLs
        - No delegation to ticketing agent
        """
        analysis = self.parser.parse(test_case.actual_output)

        # Check for forbidden ticketing patterns
        ticketing_context = self.parser.extract_ticketing_context(
            test_case.actual_output
        )

        # STRICT: If ticket context exists, must delegate to ticketing
        if ticketing_context["has_ticketing_context"]:
            if not ticketing_context["delegated_to_ticketing"]:
                self.score = 0.0
                self.reason = (
                    "VIOLATION: Ticket operation detected but no delegation "
                    "to ticketing agent"
                )
                self.success = False
                return 0.0

            # Check for forbidden tool usage
            if ticketing_context["forbidden_tools_used"]:
                self.score = 0.0
                self.reason = (
                    f"VIOLATION: PM used forbidden ticketing tools: "
                    f"{', '.join(ticketing_context['forbidden_tools_used'])}"
                )
                self.success = False
                return 0.0

        # Delegate to parent scoring if no violations
        return super().measure(test_case)


def create_delegation_correctness_metric(
    threshold: float = 0.9,
    expected_agent: Optional[str] = None,
    strict_ticketing: bool = False,
) -> DelegationCorrectnessMetric:
    """
    Factory function to create delegation correctness metric.

    Args:
        threshold: Minimum passing score
        expected_agent: Expected agent for delegation
        strict_ticketing: Use strict ticketing delegation enforcement

    Returns:
        Configured metric instance
    """
    if strict_ticketing:
        return TicketingDelegationMetric(threshold=threshold)

    return DelegationCorrectnessMetric(
        threshold=threshold, expected_agent=expected_agent
    )
