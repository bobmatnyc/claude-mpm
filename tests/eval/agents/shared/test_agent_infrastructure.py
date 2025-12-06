"""
Tests for Agent Test Harness Infrastructure.

Tests the core infrastructure components:
- AgentResponseParser
- AgentTestBase
- Shared metrics
- Shared fixtures

This validates that the Phase 2 infrastructure is working correctly
before implementing agent-specific tests in Issues #107-#113.
"""

import pytest
from deepeval.test_case import LLMTestCase

from .agent_fixtures import (
    mock_base_agent_response,
    mock_engineer_agent_response,
    mock_qa_agent_response,
    mock_research_agent_response,
)
from .agent_metrics import (
    MemoryProtocolMetric,
    ThresholdPresets,
    VerificationComplianceMetric,
    calculate_aggregate_score,
    create_metric_suite,
    extract_violation_summary,
    format_violations,
    generate_metric_report,
    get_threshold_for_severity,
)
from .agent_response_parser import (
    AgentResponseParser,
    AgentType,
    parse_agent_response,
)
from .agent_test_base import (
    BaseAgentTest,
    EngineerAgentTest,
    QAAgentTest,
    ResearchAgentTest,
)


# ============================================================================
# AGENT RESPONSE PARSER TESTS
# ============================================================================


class TestAgentResponseParser:
    """Test AgentResponseParser functionality."""

    def test_parser_initialization(self):
        """Test parser initializes correctly."""
        parser = AgentResponseParser()
        assert parser is not None
        assert parser._compiled_tools
        assert parser._compiled_verification

    def test_parse_base_agent_response(self, mock_base_agent_response):
        """Test parsing BASE_AGENT response."""
        parser = AgentResponseParser()
        response_text = mock_base_agent_response["text"]

        analysis = parser.parse(response_text, AgentType.BASE)

        # Check basic fields
        assert analysis.agent_type == AgentType.BASE
        assert analysis.tools_used
        assert analysis.memory_capture.json_block_present

        # Check verification
        assert analysis.verification_events
        assert analysis.verification_compliance_score > 0

        # Check memory protocol
        assert analysis.memory_protocol_score == 1.0

    def test_parse_research_agent_response(self, mock_research_agent_response):
        """Test parsing Research agent response."""
        parser = AgentResponseParser()
        response_text = mock_research_agent_response["text"]

        analysis = parser.parse(response_text, AgentType.RESEARCH)

        # Check agent-specific data
        data = analysis.agent_specific_data
        assert data["file_size_checks"]
        assert data["document_summarizer_used"]
        assert data["sampling_strategy_used"]

    def test_parse_engineer_agent_response(self, mock_engineer_agent_response):
        """Test parsing Engineer agent response."""
        parser = AgentResponseParser()
        response_text = mock_engineer_agent_response["text"]

        analysis = parser.parse(response_text, AgentType.ENGINEER)

        # Check agent-specific data
        data = analysis.agent_specific_data
        assert data["search_tools_used"] > 0
        assert data["consolidation_mentioned"]
        assert data["loc_delta_mentioned"]

    def test_parse_qa_agent_response(self, mock_qa_agent_response):
        """Test parsing QA agent response."""
        parser = AgentResponseParser()
        response_text = mock_qa_agent_response["text"]

        analysis = parser.parse(response_text, AgentType.QA)

        # Check agent-specific data
        data = analysis.agent_specific_data
        assert data["ci_mode_used"]
        assert not data["watch_mode_detected"]
        assert data["process_cleanup_verified"]

    def test_convenience_function(self, mock_base_agent_response):
        """Test parse_agent_response convenience function."""
        response_text = mock_base_agent_response["text"]

        analysis = parse_agent_response(response_text, AgentType.BASE)

        assert analysis is not None
        assert analysis.agent_type == AgentType.BASE

    def test_extract_tools(self, mock_base_agent_response):
        """Test tool extraction from response."""
        parser = AgentResponseParser()
        response_text = mock_base_agent_response["text"]

        analysis = parser.parse(response_text, AgentType.BASE)

        # Should detect Edit and Read tools
        tool_names = {t.tool_name for t in analysis.tools_used}
        assert "Edit" in tool_names
        assert "Read" in tool_names

    def test_extract_verification_events(self, mock_base_agent_response):
        """Test verification event extraction."""
        parser = AgentResponseParser()
        response_text = mock_base_agent_response["text"]

        analysis = parser.parse(response_text, AgentType.BASE)

        # Should detect file_edit verification
        assert len(analysis.verification_events) > 0
        event = analysis.verification_events[0]
        assert event.verification_type == "file_edit"
        assert event.verified

    def test_extract_memory_capture(self, mock_base_agent_response):
        """Test memory capture extraction."""
        parser = AgentResponseParser()
        response_text = mock_base_agent_response["text"]

        analysis = parser.parse(response_text, AgentType.BASE)

        memory = analysis.memory_capture
        assert memory.json_block_present
        assert memory.task_completed is True
        assert memory.instructions
        assert memory.results
        assert not memory.validation_errors


# ============================================================================
# AGENT TEST BASE TESTS
# ============================================================================


class TestAgentTestBase:
    """Test AgentTestBase functionality."""

    def test_base_agent_test_initialization(self):
        """Test BaseAgentTest initializes correctly."""
        test = BaseAgentTest()
        test.setup_class()

        assert test.agent_type == AgentType.BASE
        assert test.parser is not None

    def test_research_agent_test_initialization(self):
        """Test ResearchAgentTest initializes correctly."""
        test = ResearchAgentTest()
        test.setup_class()

        assert test.agent_type == AgentType.RESEARCH

    def test_engineer_agent_test_initialization(self):
        """Test EngineerAgentTest initializes correctly."""
        test = EngineerAgentTest()
        test.setup_class()

        assert test.agent_type == AgentType.ENGINEER

    def test_qa_agent_test_initialization(self):
        """Test QAAgentTest initializes correctly."""
        test = QAAgentTest()
        test.setup_class()

        assert test.agent_type == AgentType.QA

    def test_create_test_case(self):
        """Test LLMTestCase creation."""
        test = BaseAgentTest()
        test.setup_class()

        test_case = test.create_test_case(
            "Test input", "Test output", "Expected output"
        )

        assert isinstance(test_case, LLMTestCase)
        assert test_case.input == "Test input"
        assert test_case.actual_output == "Test output"

    def test_assert_verification_present(self, mock_base_agent_response):
        """Test verification assertion."""
        test = BaseAgentTest()
        test.setup_class()

        parser = AgentResponseParser()
        analysis = parser.parse(mock_base_agent_response["text"], AgentType.BASE)

        # Should pass (response has verification)
        test.assert_verification_present(analysis, min_score=0.9)

    def test_assert_memory_protocol_compliant(self, mock_base_agent_response):
        """Test memory protocol assertion."""
        test = BaseAgentTest()
        test.setup_class()

        parser = AgentResponseParser()
        analysis = parser.parse(mock_base_agent_response["text"], AgentType.BASE)

        # Should pass (response has valid JSON)
        test.assert_memory_protocol_compliant(analysis, strict=True)

    def test_calculate_overall_score(self, mock_base_agent_response):
        """Test overall score calculation."""
        test = BaseAgentTest()
        test.setup_class()

        parser = AgentResponseParser()
        analysis = parser.parse(mock_base_agent_response["text"], AgentType.BASE)

        score = test.calculate_overall_score(analysis)

        assert 0.0 <= score <= 1.0
        assert score > 0.8  # Should be high for good response


# ============================================================================
# AGENT METRICS TESTS
# ============================================================================


class TestAgentMetrics:
    """Test shared agent metrics."""

    def test_verification_compliance_metric(self, mock_base_agent_response):
        """Test VerificationComplianceMetric."""
        metric = VerificationComplianceMetric(threshold=0.9)

        test_case = LLMTestCase(
            input="Test input", actual_output=mock_base_agent_response["text"]
        )

        score = metric.measure(test_case)

        assert 0.0 <= score <= 1.0
        assert metric.is_successful()
        assert metric.reason

    def test_memory_protocol_metric(self, mock_base_agent_response):
        """Test MemoryProtocolMetric."""
        metric = MemoryProtocolMetric(threshold=1.0)

        test_case = LLMTestCase(
            input="Test input", actual_output=mock_base_agent_response["text"]
        )

        score = metric.measure(test_case)

        assert score == 1.0  # Perfect compliance
        assert metric.is_successful()

    def test_create_metric_suite(self):
        """Test metric suite creation."""
        metrics = create_metric_suite(AgentType.BASE, threshold=0.9)

        assert len(metrics) >= 2  # At least verification and memory protocol
        assert all(hasattr(m, "measure") for m in metrics)

    def test_calculate_aggregate_score(self, mock_base_agent_response):
        """Test aggregate score calculation."""
        metrics = create_metric_suite(AgentType.BASE)

        test_case = LLMTestCase(
            input="Test input", actual_output=mock_base_agent_response["text"]
        )

        result = calculate_aggregate_score(metrics, test_case)

        assert "aggregate_score" in result
        assert "individual_scores" in result
        assert "all_passed" in result
        assert result["all_passed"]

    def test_generate_metric_report(self, mock_base_agent_response):
        """Test metric report generation."""
        metrics = create_metric_suite(AgentType.BASE)

        test_case = LLMTestCase(
            input="Test input", actual_output=mock_base_agent_response["text"]
        )

        report = generate_metric_report(metrics, test_case)

        assert "AGENT EVALUATION REPORT" in report
        assert "Overall Score:" in report
        assert "PASS" in report or "FAIL" in report


# ============================================================================
# UTILITY FUNCTION TESTS
# ============================================================================


class TestUtilityFunctions:
    """Test utility functions."""

    def test_threshold_presets(self):
        """Test threshold presets."""
        assert ThresholdPresets.STRICT == 1.0
        assert ThresholdPresets.PRODUCTION == 0.95
        assert ThresholdPresets.STANDARD == 0.9
        assert ThresholdPresets.LENIENT == 0.8

    def test_get_threshold_for_severity(self):
        """Test severity-based threshold selection."""
        assert get_threshold_for_severity("critical") == 1.0
        assert get_threshold_for_severity("high") == 0.95
        assert get_threshold_for_severity("medium") == 0.9
        assert get_threshold_for_severity("low") == 0.8

    def test_extract_violation_summary(self, mock_base_agent_response):
        """Test violation summary extraction."""
        parser = AgentResponseParser()
        analysis = parser.parse(mock_base_agent_response["text"], AgentType.BASE)

        summary = extract_violation_summary(analysis)

        assert "total_violations" in summary
        assert "by_category" in summary
        assert "has_violations" in summary

    def test_format_violations(self, mock_base_agent_response):
        """Test violation formatting."""
        parser = AgentResponseParser()
        analysis = parser.parse(mock_base_agent_response["text"], AgentType.BASE)

        formatted = format_violations(analysis)

        assert isinstance(formatted, str)
        # Good response should have no violations
        assert "No violations" in formatted or "Found" in formatted


# ============================================================================
# INTEGRATION TESTS
# ============================================================================


class TestInfrastructureIntegration:
    """Integration tests for full infrastructure."""

    def test_end_to_end_base_agent(self, mock_base_agent_response):
        """Test complete flow: parse → analyze → evaluate → report."""
        # Parse
        parser = AgentResponseParser()
        analysis = parser.parse(mock_base_agent_response["text"], AgentType.BASE)

        # Create test case
        test_case = LLMTestCase(
            input="Update config.py",
            actual_output=mock_base_agent_response["text"],
        )

        # Evaluate with metrics
        metrics = create_metric_suite(AgentType.BASE)
        result = calculate_aggregate_score(metrics, test_case)

        # Generate report
        report = generate_metric_report(metrics, test_case)

        # Assertions
        assert analysis.verification_compliance_score > 0.9
        assert analysis.memory_protocol_score == 1.0
        assert result["all_passed"]
        assert "PASS" in report

    def test_end_to_end_research_agent(self, mock_research_agent_response):
        """Test complete flow for Research agent."""
        parser = AgentResponseParser()
        analysis = parser.parse(
            mock_research_agent_response["text"], AgentType.RESEARCH
        )

        # Check Research-specific patterns
        data = analysis.agent_specific_data
        assert data["file_size_checks"]
        assert data["document_summarizer_used"]

    def test_end_to_end_engineer_agent(self, mock_engineer_agent_response):
        """Test complete flow for Engineer agent."""
        parser = AgentResponseParser()
        analysis = parser.parse(
            mock_engineer_agent_response["text"], AgentType.ENGINEER
        )

        # Check Engineer-specific patterns
        data = analysis.agent_specific_data
        assert data["search_tools_used"] > 0
        assert data["consolidation_mentioned"]

    def test_end_to_end_qa_agent(self, mock_qa_agent_response):
        """Test complete flow for QA agent."""
        parser = AgentResponseParser()
        analysis = parser.parse(mock_qa_agent_response["text"], AgentType.QA)

        # Check QA-specific patterns
        data = analysis.agent_specific_data
        assert data["ci_mode_used"]
        assert not data["watch_mode_detected"]


# ============================================================================
# FIXTURE TESTS
# ============================================================================


class TestSharedFixtures:
    """Test shared fixtures work correctly."""

    def test_temp_project_dir(self, temp_project_dir):
        """Test temp_project_dir fixture."""
        assert temp_project_dir.exists()
        assert (temp_project_dir / "src").exists()
        assert (temp_project_dir / "tests").exists()

    def test_mock_filesystem(self, mock_filesystem):
        """Test mock_filesystem fixture."""
        assert "root" in mock_filesystem
        assert "files" in mock_filesystem
        assert len(mock_filesystem["files"]) > 0

        # Check large file exists
        auth_file = mock_filesystem["files"]["src/auth.py"]
        assert auth_file["size"] > 20000

    def test_sample_python_files(self, sample_python_files):
        """Test sample_python_files fixture."""
        assert len(sample_python_files) > 0
        assert sample_python_files[0]["language"] == "python"

    def test_sample_javascript_files(self, sample_javascript_files):
        """Test sample_javascript_files fixture."""
        assert len(sample_javascript_files) > 0
        package_json = next(
            f for f in sample_javascript_files if f["filename"] == "package.json"
        )
        assert package_json is not None

    def test_mock_git_repo(self, mock_git_repo):
        """Test mock_git_repo fixture."""
        assert "current_branch" in mock_git_repo
        assert mock_git_repo["current_branch"] == "main"

    def test_mock_deployment_env(self, mock_deployment_env):
        """Test mock_deployment_env fixture."""
        assert "env" in mock_deployment_env
        assert "services" in mock_deployment_env
        assert mock_deployment_env["env"]["NODE_ENV"] == "production"

    def test_agent_templates(
        self,
        base_agent_template,
        research_agent_template,
        engineer_agent_template,
        qa_agent_template,
    ):
        """Test agent template fixtures."""
        assert "content" in base_agent_template
        assert "Always verify" in base_agent_template["content"]

        assert "document_summarizer" in research_agent_template["content"]
        assert "Code Minimization" in engineer_agent_template["content"]
        assert "watch mode" in qa_agent_template["content"]
