"""
Unit tests for agent configuration data models.

Tests validation logic, property methods, and data integrity
for all agent configuration-related models.

Part of TSK-0054: Auto-Configuration Feature - Phase 1
"""

import pytest

from claude_mpm.services.core.models.agent_config import (
    AgentCapabilities,
    AgentRecommendation,
    AgentSpecialization,
    ConfigurationPreview,
    ConfigurationResult,
    ConfigurationStatus,
    ValidationIssue,
    ValidationResult,
    ValidationSeverity,
)


class TestAgentSpecialization:
    """Tests for AgentSpecialization enum."""

    def test_all_specializations_exist(self):
        """Test that all specializations are defined."""
        assert AgentSpecialization.GENERAL == "general"
        assert AgentSpecialization.LANGUAGE_SPECIFIC == "language_specific"
        assert AgentSpecialization.FRAMEWORK_SPECIFIC == "framework_specific"
        assert AgentSpecialization.DEVOPS == "devops"
        assert AgentSpecialization.SECURITY == "security"
        assert AgentSpecialization.TESTING == "testing"
        assert AgentSpecialization.DOCUMENTATION == "documentation"
        assert AgentSpecialization.PERFORMANCE == "performance"


class TestAgentCapabilities:
    """Tests for AgentCapabilities dataclass."""

    def test_valid_capabilities(self):
        """Test creating valid agent capabilities."""
        capabilities = AgentCapabilities(
            agent_id="python-engineer",
            agent_name="Python Engineer",
            specializations=[AgentSpecialization.LANGUAGE_SPECIFIC],
            supported_languages=["Python", "JavaScript"],
            supported_frameworks=["Django", "Flask"],
            required_tools=["pip", "pytest"],
            description="Python development specialist",
        )
        assert capabilities.agent_id == "python-engineer"
        assert capabilities.agent_name == "Python Engineer"
        assert len(capabilities.supported_languages) == 2

    def test_supports_language_method(self):
        """Test supports_language method."""
        capabilities = AgentCapabilities(
            agent_id="test",
            agent_name="Test",
            supported_languages=["Python", "JavaScript"],
        )
        assert capabilities.supports_language("Python") is True
        assert capabilities.supports_language("python") is True  # Case-insensitive
        assert capabilities.supports_language("Ruby") is False

    def test_supports_framework_method(self):
        """Test supports_framework method."""
        capabilities = AgentCapabilities(
            agent_id="test", agent_name="Test", supported_frameworks=["Django", "Flask"]
        )
        assert capabilities.supports_framework("Django") is True
        assert capabilities.supports_framework("django") is True  # Case-insensitive
        assert capabilities.supports_framework("Rails") is False

    def test_has_specialization_method(self):
        """Test has_specialization method."""
        capabilities = AgentCapabilities(
            agent_id="test",
            agent_name="Test",
            specializations=[AgentSpecialization.DEVOPS, AgentSpecialization.SECURITY],
        )
        assert capabilities.has_specialization(AgentSpecialization.DEVOPS) is True
        assert capabilities.has_specialization(AgentSpecialization.TESTING) is False

    def test_empty_agent_id_raises_error(self):
        """Test that empty agent ID raises ValueError."""
        with pytest.raises(ValueError, match="Agent ID cannot be empty"):
            AgentCapabilities(agent_id="", agent_name="Test")

    def test_empty_agent_name_raises_error(self):
        """Test that empty agent name raises ValueError."""
        with pytest.raises(ValueError, match="Agent name cannot be empty"):
            AgentCapabilities(agent_id="test", agent_name="")


class TestAgentRecommendation:
    """Tests for AgentRecommendation dataclass."""

    def test_valid_recommendation(self):
        """Test creating a valid recommendation."""
        recommendation = AgentRecommendation(
            agent_id="python-engineer",
            agent_name="Python Engineer",
            confidence_score=0.85,
            match_reasons=["Strong Python codebase", "Django framework detected"],
            concerns=["No test coverage found"],
            deployment_priority=1,
        )
        assert recommendation.agent_id == "python-engineer"
        assert recommendation.confidence_score == 0.85
        assert len(recommendation.match_reasons) == 2

    def test_is_high_confidence_property(self):
        """Test is_high_confidence property."""
        high_conf = AgentRecommendation(
            agent_id="test", agent_name="Test", confidence_score=0.85
        )
        assert high_conf.is_high_confidence is True

        low_conf = AgentRecommendation(
            agent_id="test", agent_name="Test", confidence_score=0.7
        )
        assert low_conf.is_high_confidence is False

    def test_is_medium_confidence_property(self):
        """Test is_medium_confidence property."""
        medium_conf = AgentRecommendation(
            agent_id="test", agent_name="Test", confidence_score=0.65
        )
        assert medium_conf.is_medium_confidence is True

        high_conf = AgentRecommendation(
            agent_id="test", agent_name="Test", confidence_score=0.85
        )
        assert high_conf.is_medium_confidence is False

    def test_is_low_confidence_property(self):
        """Test is_low_confidence property."""
        low_conf = AgentRecommendation(
            agent_id="test", agent_name="Test", confidence_score=0.3
        )
        assert low_conf.is_low_confidence is True

        medium_conf = AgentRecommendation(
            agent_id="test", agent_name="Test", confidence_score=0.6
        )
        assert medium_conf.is_low_confidence is False

    def test_has_concerns_property(self):
        """Test has_concerns property."""
        with_concerns = AgentRecommendation(
            agent_id="test",
            agent_name="Test",
            confidence_score=0.8,
            concerns=["Missing tests"],
        )
        assert with_concerns.has_concerns is True

        no_concerns = AgentRecommendation(
            agent_id="test", agent_name="Test", confidence_score=0.8
        )
        assert no_concerns.has_concerns is False

    def test_invalid_confidence_score_raises_error(self):
        """Test that confidence score outside 0.0-1.0 raises ValueError."""
        with pytest.raises(ValueError, match="Confidence score must be 0.0-1.0"):
            AgentRecommendation(
                agent_id="test", agent_name="Test", confidence_score=1.5
            )

        with pytest.raises(ValueError, match="Confidence score must be 0.0-1.0"):
            AgentRecommendation(
                agent_id="test", agent_name="Test", confidence_score=-0.1
            )

    def test_invalid_deployment_priority_raises_error(self):
        """Test that deployment priority < 1 raises ValueError."""
        with pytest.raises(ValueError, match="Deployment priority must be >= 1"):
            AgentRecommendation(
                agent_id="test",
                agent_name="Test",
                confidence_score=0.8,
                deployment_priority=0,
            )

    def test_to_dict_method(self):
        """Test to_dict serialization method."""
        recommendation = AgentRecommendation(
            agent_id="test",
            agent_name="Test Agent",
            confidence_score=0.8,
            match_reasons=["Reason 1"],
            deployment_priority=1,
        )
        result = recommendation.to_dict()

        assert result["agent_id"] == "test"
        assert result["agent_name"] == "Test Agent"
        assert result["confidence_score"] == 0.8
        assert "match_reasons" in result


class TestConfigurationStatus:
    """Tests for ConfigurationStatus enum."""

    def test_all_statuses_exist(self):
        """Test that all statuses are defined."""
        assert ConfigurationStatus.SUCCESS == "success"
        assert ConfigurationStatus.PARTIAL_SUCCESS == "partial_success"
        assert ConfigurationStatus.FAILURE == "failure"
        assert ConfigurationStatus.VALIDATION_ERROR == "validation_error"
        assert ConfigurationStatus.USER_CANCELLED == "user_cancelled"


class TestConfigurationResult:
    """Tests for ConfigurationResult dataclass."""

    def test_valid_result(self):
        """Test creating a valid configuration result."""
        result = ConfigurationResult(
            status=ConfigurationStatus.SUCCESS,
            deployed_agents=["python-engineer", "devops"],
            failed_agents=[],
            validation_warnings=["Consider adding test coverage"],
            message="Successfully configured 2 agents",
        )
        assert result.status == ConfigurationStatus.SUCCESS
        assert len(result.deployed_agents) == 2

    def test_is_successful_property(self):
        """Test is_successful property."""
        success = ConfigurationResult(status=ConfigurationStatus.SUCCESS)
        assert success.is_successful is True

        failure = ConfigurationResult(status=ConfigurationStatus.FAILURE)
        assert failure.is_successful is False

    def test_has_failures_property(self):
        """Test has_failures property."""
        with_failures = ConfigurationResult(
            status=ConfigurationStatus.PARTIAL_SUCCESS, failed_agents=["security"]
        )
        assert with_failures.has_failures is True

        no_failures = ConfigurationResult(
            status=ConfigurationStatus.SUCCESS, failed_agents=[]
        )
        assert no_failures.has_failures is False

    def test_has_warnings_property(self):
        """Test has_warnings property."""
        with_warnings = ConfigurationResult(
            status=ConfigurationStatus.SUCCESS, validation_warnings=["Warning 1"]
        )
        assert with_warnings.has_warnings is True

        no_warnings = ConfigurationResult(status=ConfigurationStatus.SUCCESS)
        assert no_warnings.has_warnings is False

    def test_deployment_count_property(self):
        """Test deployment_count property."""
        result = ConfigurationResult(
            status=ConfigurationStatus.SUCCESS,
            deployed_agents=["agent1", "agent2", "agent3"],
        )
        assert result.deployment_count == 3

    def test_to_dict_method(self):
        """Test to_dict serialization method."""
        result = ConfigurationResult(
            status=ConfigurationStatus.SUCCESS,
            deployed_agents=["agent1"],
            message="Success",
        )
        result_dict = result.to_dict()

        assert result_dict["status"] == "success"
        assert result_dict["deployment_count"] == 1
        assert "deployed_agents" in result_dict


class TestValidationSeverity:
    """Tests for ValidationSeverity enum."""

    def test_all_severities_exist(self):
        """Test that all severities are defined."""
        assert ValidationSeverity.ERROR == "error"
        assert ValidationSeverity.WARNING == "warning"
        assert ValidationSeverity.INFO == "info"


class TestValidationIssue:
    """Tests for ValidationIssue dataclass."""

    def test_valid_issue(self):
        """Test creating a valid validation issue."""
        issue = ValidationIssue(
            severity=ValidationSeverity.ERROR,
            message="Agent configuration is invalid",
            agent_id="python-engineer",
            field="version",
            suggested_fix="Update to version 2.0",
        )
        assert issue.severity == ValidationSeverity.ERROR
        assert issue.message == "Agent configuration is invalid"
        assert issue.agent_id == "python-engineer"

    def test_empty_message_raises_error(self):
        """Test that empty message raises ValueError."""
        with pytest.raises(
            ValueError, match="Validation issue message cannot be empty"
        ):
            ValidationIssue(severity=ValidationSeverity.ERROR, message="")


class TestValidationResult:
    """Tests for ValidationResult dataclass."""

    def test_valid_result(self):
        """Test creating a valid validation result."""
        issues = [
            ValidationIssue(ValidationSeverity.ERROR, "Error 1"),
            ValidationIssue(ValidationSeverity.WARNING, "Warning 1"),
            ValidationIssue(ValidationSeverity.INFO, "Info 1"),
        ]
        result = ValidationResult(
            is_valid=False, issues=issues, validated_agents=["agent1", "agent2"]
        )
        assert result.is_valid is False
        assert len(result.issues) == 3

    def test_errors_property(self):
        """Test errors property filters correctly."""
        issues = [
            ValidationIssue(ValidationSeverity.ERROR, "Error 1"),
            ValidationIssue(ValidationSeverity.WARNING, "Warning 1"),
        ]
        result = ValidationResult(is_valid=False, issues=issues)
        errors = result.errors
        assert len(errors) == 1
        assert errors[0].severity == ValidationSeverity.ERROR

    def test_warnings_property(self):
        """Test warnings property filters correctly."""
        issues = [
            ValidationIssue(ValidationSeverity.ERROR, "Error 1"),
            ValidationIssue(ValidationSeverity.WARNING, "Warning 1"),
            ValidationIssue(ValidationSeverity.WARNING, "Warning 2"),
        ]
        result = ValidationResult(is_valid=False, issues=issues)
        warnings = result.warnings
        assert len(warnings) == 2
        assert all(w.severity == ValidationSeverity.WARNING for w in warnings)

    def test_infos_property(self):
        """Test infos property filters correctly."""
        issues = [
            ValidationIssue(ValidationSeverity.INFO, "Info 1"),
            ValidationIssue(ValidationSeverity.WARNING, "Warning 1"),
        ]
        result = ValidationResult(is_valid=True, issues=issues)
        infos = result.infos
        assert len(infos) == 1
        assert infos[0].severity == ValidationSeverity.INFO

    def test_has_errors_property(self):
        """Test has_errors property."""
        with_errors = ValidationResult(
            is_valid=False, issues=[ValidationIssue(ValidationSeverity.ERROR, "Error")]
        )
        assert with_errors.has_errors is True

        no_errors = ValidationResult(is_valid=True, issues=[])
        assert no_errors.has_errors is False

    def test_error_count_property(self):
        """Test error_count property."""
        result = ValidationResult(
            is_valid=False,
            issues=[
                ValidationIssue(ValidationSeverity.ERROR, "Error 1"),
                ValidationIssue(ValidationSeverity.ERROR, "Error 2"),
                ValidationIssue(ValidationSeverity.WARNING, "Warning"),
            ],
        )
        assert result.error_count == 2

    def test_to_dict_method(self):
        """Test to_dict serialization method."""
        result = ValidationResult(
            is_valid=True,
            issues=[ValidationIssue(ValidationSeverity.INFO, "Info")],
            validated_agents=["agent1"],
        )
        result_dict = result.to_dict()

        assert result_dict["is_valid"] is True
        assert "error_count" in result_dict
        assert "validated_agents" in result_dict


class TestConfigurationPreview:
    """Tests for ConfigurationPreview dataclass."""

    def test_valid_preview(self):
        """Test creating a valid configuration preview."""
        recommendations = [
            AgentRecommendation(
                agent_id="agent1", agent_name="Agent 1", confidence_score=0.9
            ),
            AgentRecommendation(
                agent_id="agent2", agent_name="Agent 2", confidence_score=0.7
            ),
        ]
        preview = ConfigurationPreview(
            recommendations=recommendations,
            validation_result=ValidationResult(is_valid=True, issues=[]),
            estimated_deployment_time=30.0,
            would_deploy=["agent1", "agent2"],
            requires_confirmation=True,
        )
        assert len(preview.recommendations) == 2
        assert preview.estimated_deployment_time == 30.0

    def test_deployment_count_property(self):
        """Test deployment_count property."""
        preview = ConfigurationPreview(would_deploy=["agent1", "agent2", "agent3"])
        assert preview.deployment_count == 3

    def test_skip_count_property(self):
        """Test skip_count property."""
        preview = ConfigurationPreview(would_skip=["agent4", "agent5"])
        assert preview.skip_count == 2

    def test_is_valid_property_with_validation_result(self):
        """Test is_valid property with validation result."""
        valid_preview = ConfigurationPreview(
            validation_result=ValidationResult(is_valid=True, issues=[])
        )
        assert valid_preview.is_valid is True

        invalid_preview = ConfigurationPreview(
            validation_result=ValidationResult(is_valid=False, issues=[])
        )
        assert invalid_preview.is_valid is False

    def test_is_valid_property_without_validation_result(self):
        """Test is_valid property when validation result is None."""
        preview = ConfigurationPreview(validation_result=None)
        assert preview.is_valid is True

    def test_high_confidence_count_property(self):
        """Test high_confidence_count property."""
        recommendations = [
            AgentRecommendation(
                agent_id="agent1", agent_name="Agent 1", confidence_score=0.9
            ),
            AgentRecommendation(
                agent_id="agent2", agent_name="Agent 2", confidence_score=0.85
            ),
            AgentRecommendation(
                agent_id="agent3", agent_name="Agent 3", confidence_score=0.6
            ),
        ]
        preview = ConfigurationPreview(recommendations=recommendations)
        assert preview.high_confidence_count == 2

    def test_to_dict_method(self):
        """Test to_dict serialization method."""
        preview = ConfigurationPreview(
            recommendations=[
                AgentRecommendation(
                    agent_id="agent1", agent_name="Agent 1", confidence_score=0.9
                )
            ],
            would_deploy=["agent1"],
            estimated_deployment_time=15.0,
        )
        result = preview.to_dict()

        assert result["deployment_count"] == 1
        assert result["estimated_deployment_time"] == 15.0
        assert "recommendations" in result
