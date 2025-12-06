"""
Base Test Class for Agent Evaluation.

This module provides a base test class that all agent tests should extend.
It handles common setup/teardown, agent invocation, result validation,
and metric calculation.

Design Decision: Single base class with template methods

Rationale: All agent tests share common patterns (setup, invoke, validate, teardown).
Using template method pattern allows customization while maintaining consistent structure.

Trade-offs:
- Inheritance vs. Composition: Inheritance simpler for test classes
- Shared state: Managed through pytest fixtures instead of instance variables
- Extensibility: Subclasses override specific methods for agent-specific behavior

Example:
    class TestEngineerAgent(AgentTestBase):
        agent_type = AgentType.ENGINEER

        def test_code_minimization(self, mock_agent):
            response = self.invoke_agent(
                mock_agent,
                "Implement JWT validation"
            )
            self.assert_search_before_create(response)
            self.assert_net_loc_delta_reported(response)
"""

from typing import Any, Dict, List, Optional

import pytest
from deepeval.test_case import LLMTestCase

from .agent_response_parser import (
    AgentResponseAnalysis,
    AgentResponseParser,
    AgentType,
    MemoryCapture,
    VerificationEvent,
)


class AgentTestBase:
    """
    Base test class for agent evaluation.

    Provides common functionality for testing BASE_AGENT and specialized agents:
    - Agent invocation helpers
    - Response validation
    - Metric calculation
    - Common assertions

    Subclasses should:
    1. Set `agent_type` class attribute
    2. Override `setup_agent_context()` for agent-specific setup
    3. Add agent-specific assertion methods

    Example:
        class TestResearchAgent(AgentTestBase):
            agent_type = AgentType.RESEARCH

            def test_memory_management(self, mock_agent):
                response = self.invoke_agent(
                    mock_agent,
                    "Analyze authentication code (50KB file)"
                )
                self.assert_file_size_checked(response)
                self.assert_document_summarizer_used(response)
    """

    agent_type: AgentType = AgentType.BASE
    parser: AgentResponseParser

    @classmethod
    def setup_class(cls):
        """Setup parser for all tests in this class."""
        cls.parser = AgentResponseParser()

    def setup_method(self, method):
        """Setup before each test method."""
        self.agent_context = self.setup_agent_context()

    def teardown_method(self, method):
        """Cleanup after each test method."""
        self.teardown_agent_context()

    def setup_agent_context(self) -> Dict[str, Any]:
        """
        Setup agent-specific context.

        Override in subclasses to provide agent-specific setup.

        Returns:
            Dict with agent context (tools available, constraints, etc.)
        """
        return {
            "agent_type": self.agent_type,
            "tools_available": self.get_default_tools(),
            "constraints": self.get_default_constraints(),
        }

    def teardown_agent_context(self):
        """
        Cleanup agent-specific context.

        Override in subclasses for agent-specific cleanup.
        """
        pass

    def get_default_tools(self) -> List[str]:
        """Get default tools available to all agents."""
        return [
            "Read",
            "Write",
            "Edit",
            "Bash",
            "Grep",
            "Glob",
            "WebFetch",
            "WebSearch",
            "Task",
            "Skill",
            "SlashCommand",
        ]

    def get_default_constraints(self) -> Dict[str, Any]:
        """Get default constraints for all agents."""
        return {
            "must_verify": True,
            "must_use_json_format": True,
            "max_unverified_assertions": 0,
        }

    # ========================================================================
    # AGENT INVOCATION HELPERS
    # ========================================================================

    def invoke_agent(
        self,
        mock_agent: Any,
        input_text: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> AgentResponseAnalysis:
        """
        Invoke agent and parse response.

        Args:
            mock_agent: Mock agent fixture (async or sync)
            input_text: User input/instruction
            context: Optional context for agent

        Returns:
            Parsed AgentResponseAnalysis

        Example:
            response = self.invoke_agent(
                mock_agent,
                "Fix authentication bug",
                context={"files": ["auth.py"]}
            )
        """
        # Get raw response from mock agent
        if hasattr(mock_agent, "process_request"):
            # Async agent
            import asyncio

            loop = asyncio.get_event_loop()
            raw_response = loop.run_until_complete(
                mock_agent.process_request(input_text, context or self.agent_context)
            )
        else:
            # Sync agent
            raw_response = mock_agent.process_request_sync(input_text, context or self.agent_context)

        # Extract response text
        response_text = raw_response.get("content", "")

        # Parse with agent-specific parser
        return self.parser.parse(response_text, self.agent_type)

    def create_test_case(
        self, input_text: str, actual_output: str, expected_output: Optional[str] = None
    ) -> LLMTestCase:
        """
        Create DeepEval LLMTestCase for metric evaluation.

        Args:
            input_text: User input
            actual_output: Agent's actual response
            expected_output: Expected response (optional)

        Returns:
            LLMTestCase ready for metric evaluation

        Example:
            test_case = self.create_test_case(
                "Implement feature X",
                agent_response,
                "Search for existing implementation..."
            )
            assert metric.measure(test_case) >= 0.9
        """
        return LLMTestCase(
            input=input_text,
            actual_output=actual_output,
            expected_output=expected_output,
        )

    # ========================================================================
    # COMMON ASSERTIONS (BASE_AGENT)
    # ========================================================================

    def assert_verification_present(
        self, analysis: AgentResponseAnalysis, min_score: float = 0.9
    ):
        """
        Assert that verification compliance meets threshold.

        BASE_AGENT requirement: "Always verify - test functions, APIs, file edits"

        Args:
            analysis: Parsed agent response
            min_score: Minimum verification score (default: 0.9)

        Raises:
            AssertionError: If verification score below threshold
        """
        assert analysis.verification_compliance_score >= min_score, (
            f"Verification compliance score {analysis.verification_compliance_score:.2f} "
            f"below threshold {min_score}. "
            f"Verified: {sum(1 for e in analysis.verification_events if e.verified)}/"
            f"{len(analysis.verification_events)} events"
        )

    def assert_memory_protocol_compliant(
        self, analysis: AgentResponseAnalysis, strict: bool = True
    ):
        """
        Assert that memory protocol is compliant.

        BASE_AGENT requirement: JSON block with task_completed, instructions, results

        Args:
            analysis: Parsed agent response
            strict: If True, require perfect compliance (default: True)

        Raises:
            AssertionError: If memory protocol not compliant
        """
        memory = analysis.memory_capture

        if not memory.json_block_present:
            pytest.fail("No JSON response block found (BASE_AGENT requirement)")

        if strict and memory.validation_errors:
            pytest.fail(
                f"Memory protocol validation errors: {', '.join(memory.validation_errors)}"
            )

        if not strict and analysis.memory_protocol_score < 0.5:
            pytest.fail(
                f"Memory protocol score {analysis.memory_protocol_score:.2f} too low"
            )

    def assert_no_unverified_claims(self, analysis: AgentResponseAnalysis):
        """
        Assert no unverified assertions/claims in response.

        BASE_AGENT requirement: "Never assume, always verify"

        Args:
            analysis: Parsed agent response

        Raises:
            AssertionError: If unverified assertions found
        """
        unverified_violations = [
            v for v in analysis.violations if "Unverified assertion" in v
        ]

        assert not unverified_violations, (
            f"Found {len(unverified_violations)} unverified assertions:\n"
            + "\n".join(f"  - {v}" for v in unverified_violations)
        )

    def assert_json_format_valid(self, analysis: AgentResponseAnalysis):
        """
        Assert JSON response format is valid.

        Args:
            analysis: Parsed agent response

        Raises:
            AssertionError: If JSON format invalid
        """
        memory = analysis.memory_capture

        assert memory.json_block_present, "No JSON block in response"
        assert not memory.validation_errors, (
            f"JSON validation errors: {', '.join(memory.validation_errors)}"
        )

    def assert_tools_used(
        self, analysis: AgentResponseAnalysis, required_tools: List[str]
    ):
        """
        Assert specific tools were used.

        Args:
            analysis: Parsed agent response
            required_tools: List of tool names that must be used

        Raises:
            AssertionError: If required tools not used
        """
        tools_used = {t.tool_name for t in analysis.tools_used}

        for tool in required_tools:
            assert tool in tools_used, (
                f"Required tool '{tool}' not used. "
                f"Tools used: {', '.join(tools_used)}"
            )

    def assert_tools_not_used(
        self, analysis: AgentResponseAnalysis, forbidden_tools: List[str]
    ):
        """
        Assert specific tools were NOT used.

        Args:
            analysis: Parsed agent response
            forbidden_tools: List of tool names that must NOT be used

        Raises:
            AssertionError: If forbidden tools used
        """
        tools_used = {t.tool_name for t in analysis.tools_used}

        for tool in forbidden_tools:
            assert tool not in tools_used, (
                f"Forbidden tool '{tool}' was used. "
                f"Tools used: {', '.join(tools_used)}"
            )

    # ========================================================================
    # RESULT VALIDATION HELPERS
    # ========================================================================

    def validate_response_structure(self, analysis: AgentResponseAnalysis) -> bool:
        """
        Validate complete response structure.

        Returns:
            True if valid, False otherwise
        """
        # Check JSON block present
        if not analysis.memory_capture.json_block_present:
            return False

        # Check no validation errors (for strict compliance)
        if analysis.memory_capture.validation_errors:
            return False

        # Check verification compliance
        if analysis.verification_compliance_score < 0.9:
            return False

        return True

    def get_violation_summary(self, analysis: AgentResponseAnalysis) -> str:
        """
        Get human-readable violation summary.

        Returns:
            Summary string of all violations
        """
        if not analysis.violations:
            return "No violations detected"

        return "\n".join(f"  - {v}" for v in analysis.violations)

    def calculate_overall_score(self, analysis: AgentResponseAnalysis) -> float:
        """
        Calculate overall agent compliance score.

        Combines:
        - Verification compliance (40%)
        - Memory protocol compliance (30%)
        - No violations (30%)

        Returns:
            Score from 0.0 to 1.0
        """
        verification_score = analysis.verification_compliance_score * 0.4
        memory_score = analysis.memory_protocol_score * 0.3
        violation_score = (1.0 if not analysis.violations else 0.0) * 0.3

        return verification_score + memory_score + violation_score


class BaseAgentTest(AgentTestBase):
    """Specialized test class for BASE_AGENT testing."""

    agent_type = AgentType.BASE


class ResearchAgentTest(AgentTestBase):
    """Specialized test class for Research agent testing."""

    agent_type = AgentType.RESEARCH

    def assert_file_size_checked(self, analysis: AgentResponseAnalysis):
        """Assert file size was checked before reading large files."""
        data = analysis.agent_specific_data
        assert data.get("file_size_checks"), "File size check not detected"

    def assert_document_summarizer_used(self, analysis: AgentResponseAnalysis):
        """Assert document_summarizer was used for large files."""
        data = analysis.agent_specific_data
        assert data.get("document_summarizer_used"), "document_summarizer not used"

    def assert_max_files_respected(self, analysis: AgentResponseAnalysis, max_files: int = 5):
        """Assert agent didn't read too many files."""
        data = analysis.agent_specific_data
        files_read = data.get("files_read_count", 0)
        assert files_read <= max_files, (
            f"Read {files_read} files (max: {max_files})"
        )


class EngineerAgentTest(AgentTestBase):
    """Specialized test class for Engineer agent testing."""

    agent_type = AgentType.ENGINEER

    def assert_search_before_create(self, analysis: AgentResponseAnalysis):
        """Assert search tools used before Write/Edit."""
        data = analysis.agent_specific_data
        search_count = data.get("search_tools_used", 0)
        write_count = data.get("write_tools_used", 0)

        if write_count > 0:
            assert search_count > 0, "Write/Edit without prior search (search-first violation)"

    def assert_net_loc_delta_reported(self, analysis: AgentResponseAnalysis):
        """Assert engineer reported LOC impact."""
        data = analysis.agent_specific_data
        assert data.get("loc_delta_mentioned"), "LOC delta not reported"

    def assert_no_mock_data(self, analysis: AgentResponseAnalysis):
        """Assert no mock data in production code."""
        data = analysis.agent_specific_data
        assert not data.get("mock_data_detected"), "Mock data detected in production code"


class QAAgentTest(AgentTestBase):
    """Specialized test class for QA agent testing."""

    agent_type = AgentType.QA

    def assert_ci_mode_used(self, analysis: AgentResponseAnalysis):
        """Assert CI mode used for test execution."""
        data = analysis.agent_specific_data
        if data.get("test_execution_count", 0) > 0:
            assert data.get("ci_mode_used"), "Test execution without CI mode"

    def assert_no_watch_mode(self, analysis: AgentResponseAnalysis):
        """Assert watch mode NOT used (critical violation)."""
        data = analysis.agent_specific_data
        assert not data.get("watch_mode_detected"), "CRITICAL: Watch mode detected"

    def assert_process_cleanup_verified(self, analysis: AgentResponseAnalysis):
        """Assert process cleanup was verified."""
        data = analysis.agent_specific_data
        assert data.get("process_cleanup_verified"), "Process cleanup not verified"


class OpsAgentTest(AgentTestBase):
    """Specialized test class for Ops agent testing."""

    agent_type = AgentType.OPS

    def assert_environment_validated(self, analysis: AgentResponseAnalysis):
        """Assert environment validation performed."""
        data = analysis.agent_specific_data
        assert data.get("environment_validation"), "Environment validation not performed"

    def assert_rollback_prepared(self, analysis: AgentResponseAnalysis):
        """Assert rollback plan mentioned."""
        data = analysis.agent_specific_data
        assert data.get("rollback_mentioned"), "Rollback plan not mentioned"

    def assert_health_checks_present(self, analysis: AgentResponseAnalysis):
        """Assert health checks mentioned."""
        data = analysis.agent_specific_data
        assert data.get("health_checks"), "Health checks not mentioned"
