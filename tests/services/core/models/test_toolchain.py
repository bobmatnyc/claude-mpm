"""
Unit tests for toolchain data models.

Tests validation logic, property methods, and data integrity
for all toolchain-related models.

Part of TSK-0054: Auto-Configuration Feature - Phase 1
"""

from pathlib import Path

import pytest

from claude_mpm.services.core.models.toolchain import (
    ConfidenceLevel,
    DeploymentTarget,
    Framework,
    LanguageDetection,
    ToolchainAnalysis,
    ToolchainComponent,
)


class TestConfidenceLevel:
    """Tests for ConfidenceLevel enum."""

    def test_all_levels_exist(self):
        """Test that all confidence levels are defined."""
        assert ConfidenceLevel.HIGH == "high"
        assert ConfidenceLevel.MEDIUM == "medium"
        assert ConfidenceLevel.LOW == "low"
        assert ConfidenceLevel.VERY_LOW == "very_low"


class TestToolchainComponent:
    """Tests for ToolchainComponent dataclass."""

    def test_valid_component_creation(self):
        """Test creating a valid component."""
        component = ToolchainComponent(
            name="Python",
            version="3.12",
            confidence=ConfidenceLevel.HIGH,
            metadata={"source": "pyproject.toml"},
        )
        assert component.name == "Python"
        assert component.version == "3.12"
        assert component.confidence == ConfidenceLevel.HIGH
        assert component.metadata["source"] == "pyproject.toml"

    def test_component_with_defaults(self):
        """Test component creation with default values."""
        component = ToolchainComponent(name="Node.js")
        assert component.name == "Node.js"
        assert component.version is None
        assert component.confidence == ConfidenceLevel.MEDIUM
        assert component.metadata == {}

    def test_empty_name_raises_error(self):
        """Test that empty component name raises ValueError."""
        with pytest.raises(ValueError, match="Component name cannot be empty"):
            ToolchainComponent(name="")

    def test_whitespace_name_raises_error(self):
        """Test that whitespace-only name raises ValueError."""
        with pytest.raises(ValueError, match="Component name cannot be empty"):
            ToolchainComponent(name="   ")

    def test_empty_version_string_raises_error(self):
        """Test that empty version string raises ValueError."""
        with pytest.raises(
            ValueError, match="Component version cannot be empty string"
        ):
            ToolchainComponent(name="Python", version="")

    def test_frozen_immutability(self):
        """Test that component is immutable (frozen)."""
        component = ToolchainComponent(name="Python")
        with pytest.raises(Exception):  # FrozenInstanceError
            component.name = "JavaScript"


class TestLanguageDetection:
    """Tests for LanguageDetection dataclass."""

    def test_valid_detection(self):
        """Test creating a valid language detection."""
        secondary = [
            ToolchainComponent(name="JavaScript", confidence=ConfidenceLevel.MEDIUM),
            ToolchainComponent(name="Shell", confidence=ConfidenceLevel.LOW),
        ]
        detection = LanguageDetection(
            primary_language="Python",
            primary_version="3.12",
            primary_confidence=ConfidenceLevel.HIGH,
            secondary_languages=secondary,
            language_percentages={"Python": 85.0, "JavaScript": 10.0, "Shell": 5.0},
        )
        assert detection.primary_language == "Python"
        assert detection.primary_version == "3.12"
        assert len(detection.secondary_languages) == 2

    def test_all_languages_property(self):
        """Test all_languages property returns primary + secondary."""
        detection = LanguageDetection(
            primary_language="Python",
            secondary_languages=[
                ToolchainComponent(name="JavaScript"),
                ToolchainComponent(name="Shell"),
            ],
        )
        languages = detection.all_languages
        assert len(languages) == 3
        assert "Python" in languages
        assert "JavaScript" in languages
        assert "Shell" in languages

    def test_high_confidence_languages_property(self):
        """Test high_confidence_languages filters correctly."""
        detection = LanguageDetection(
            primary_language="Python",
            primary_confidence=ConfidenceLevel.HIGH,
            secondary_languages=[
                ToolchainComponent(name="JavaScript", confidence=ConfidenceLevel.HIGH),
                ToolchainComponent(name="Shell", confidence=ConfidenceLevel.LOW),
            ],
        )
        high_conf = detection.high_confidence_languages
        assert len(high_conf) == 2
        assert "Python" in high_conf
        assert "JavaScript" in high_conf
        assert "Shell" not in high_conf

    def test_empty_primary_language_raises_error(self):
        """Test that empty primary language raises ValueError."""
        with pytest.raises(ValueError, match="Primary language cannot be empty"):
            LanguageDetection(primary_language="")

    def test_invalid_percentages_sum_raises_error(self):
        """Test that invalid percentage sum raises ValueError."""
        with pytest.raises(ValueError, match="Language percentages must sum to 100%"):
            LanguageDetection(
                primary_language="Python",
                language_percentages={"Python": 50.0, "JavaScript": 30.0},  # Sum = 80%
            )

    def test_valid_percentages_with_floating_point_error(self):
        """Test that small floating point errors are tolerated."""
        detection = LanguageDetection(
            primary_language="Python",
            language_percentages={"Python": 99.5, "JavaScript": 0.5},  # Sum = 100.0
        )
        assert detection.primary_language == "Python"


class TestFramework:
    """Tests for Framework dataclass."""

    def test_valid_framework(self):
        """Test creating a valid framework."""
        framework = Framework(
            name="Django",
            version="5.0",
            framework_type="web",
            confidence=ConfidenceLevel.HIGH,
            is_dev_dependency=False,
            popularity_score=0.9,
        )
        assert framework.name == "Django"
        assert framework.version == "5.0"
        assert framework.framework_type == "web"
        assert framework.popularity_score == 0.9

    def test_display_name_with_version(self):
        """Test display_name property with version."""
        framework = Framework(name="Django", version="5.0")
        assert framework.display_name == "Django 5.0"

    def test_display_name_without_version(self):
        """Test display_name property without version."""
        framework = Framework(name="Django")
        assert framework.display_name == "Django"

    def test_empty_framework_name_raises_error(self):
        """Test that empty framework name raises ValueError."""
        with pytest.raises(ValueError, match="Framework name cannot be empty"):
            Framework(name="")

    def test_invalid_popularity_score_raises_error(self):
        """Test that popularity score outside 0.0-1.0 raises ValueError."""
        with pytest.raises(ValueError, match="Popularity score must be 0.0-1.0"):
            Framework(name="Django", popularity_score=1.5)

        with pytest.raises(ValueError, match="Popularity score must be 0.0-1.0"):
            Framework(name="Django", popularity_score=-0.1)


class TestDeploymentTarget:
    """Tests for DeploymentTarget dataclass."""

    def test_valid_deployment_target(self):
        """Test creating a valid deployment target."""
        target = DeploymentTarget(
            target_type="cloud",
            platform="aws",
            configuration={"region": "us-east-1"},
            confidence=ConfidenceLevel.HIGH,
            requires_ops_agent=True,
        )
        assert target.target_type == "cloud"
        assert target.platform == "aws"
        assert target.requires_ops_agent is True

    def test_display_name_with_platform(self):
        """Test display_name property with platform."""
        target = DeploymentTarget(target_type="cloud", platform="aws")
        assert target.display_name == "cloud (aws)"

    def test_display_name_without_platform(self):
        """Test display_name property without platform."""
        target = DeploymentTarget(target_type="on-premise")
        assert target.display_name == "on-premise"

    def test_invalid_target_type_raises_error(self):
        """Test that invalid target type raises ValueError."""
        with pytest.raises(ValueError, match="Invalid target_type"):
            DeploymentTarget(target_type="invalid")

    def test_all_valid_target_types(self):
        """Test that all valid target types are accepted."""
        valid_types = ["cloud", "container", "serverless", "on-premise", "edge"]
        for target_type in valid_types:
            target = DeploymentTarget(target_type=target_type)
            assert target.target_type == target_type


class TestToolchainAnalysis:
    """Tests for ToolchainAnalysis dataclass."""

    @pytest.fixture
    def temp_project_dir(self, tmp_path):
        """Create a temporary project directory."""
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()
        return project_dir

    @pytest.fixture
    def sample_language_detection(self):
        """Create a sample language detection."""
        return LanguageDetection(
            primary_language="Python",
            primary_version="3.12",
            primary_confidence=ConfidenceLevel.HIGH,
        )

    def test_valid_analysis(self, temp_project_dir, sample_language_detection):
        """Test creating a valid toolchain analysis."""
        analysis = ToolchainAnalysis(
            project_path=temp_project_dir,
            language_detection=sample_language_detection,
            frameworks=[Framework(name="Django", version="5.0", framework_type="web")],
            overall_confidence=ConfidenceLevel.HIGH,
        )
        assert analysis.project_path == temp_project_dir
        assert analysis.primary_language == "Python"
        assert len(analysis.frameworks) == 1

    def test_nonexistent_path_raises_error(self, sample_language_detection):
        """Test that non-existent path raises ValueError."""
        with pytest.raises(ValueError, match="Project path does not exist"):
            ToolchainAnalysis(
                project_path=Path("/nonexistent/path"),
                language_detection=sample_language_detection,
            )

    def test_file_path_raises_error(self, tmp_path, sample_language_detection):
        """Test that file path (not directory) raises ValueError."""
        file_path = tmp_path / "test_file.txt"
        file_path.touch()
        with pytest.raises(ValueError, match="Project path is not a directory"):
            ToolchainAnalysis(
                project_path=file_path, language_detection=sample_language_detection
            )

    def test_has_framework_method(self, temp_project_dir, sample_language_detection):
        """Test has_framework method."""
        analysis = ToolchainAnalysis(
            project_path=temp_project_dir,
            language_detection=sample_language_detection,
            frameworks=[
                Framework(name="Django", framework_type="web"),
                Framework(name="pytest", framework_type="testing"),
            ],
        )
        assert analysis.has_framework("Django") is True
        assert analysis.has_framework("django") is True  # Case-insensitive
        assert analysis.has_framework("Flask") is False

    def test_get_framework_method(self, temp_project_dir, sample_language_detection):
        """Test get_framework method."""
        django_fw = Framework(name="Django", version="5.0", framework_type="web")
        analysis = ToolchainAnalysis(
            project_path=temp_project_dir,
            language_detection=sample_language_detection,
            frameworks=[django_fw],
        )
        found = analysis.get_framework("Django")
        assert found is not None
        assert found.name == "Django"
        assert found.version == "5.0"

        not_found = analysis.get_framework("Flask")
        assert not_found is None

    def test_get_frameworks_by_type(self, temp_project_dir, sample_language_detection):
        """Test get_frameworks_by_type method."""
        analysis = ToolchainAnalysis(
            project_path=temp_project_dir,
            language_detection=sample_language_detection,
            frameworks=[
                Framework(name="Django", framework_type="web"),
                Framework(name="Flask", framework_type="web"),
                Framework(name="pytest", framework_type="testing"),
            ],
        )
        web_frameworks = analysis.get_frameworks_by_type("web")
        assert len(web_frameworks) == 2
        assert all(fw.framework_type == "web" for fw in web_frameworks)

    def test_web_frameworks_property(self, temp_project_dir, sample_language_detection):
        """Test web_frameworks property."""
        analysis = ToolchainAnalysis(
            project_path=temp_project_dir,
            language_detection=sample_language_detection,
            frameworks=[
                Framework(name="Django", framework_type="web"),
                Framework(name="pytest", framework_type="testing"),
            ],
        )
        web_fws = analysis.web_frameworks
        assert len(web_fws) == 1
        assert web_fws[0].name == "Django"

    def test_is_web_project_property(self, temp_project_dir, sample_language_detection):
        """Test is_web_project property."""
        analysis_with_web = ToolchainAnalysis(
            project_path=temp_project_dir,
            language_detection=sample_language_detection,
            frameworks=[Framework(name="Django", framework_type="web")],
        )
        assert analysis_with_web.is_web_project is True

        analysis_without_web = ToolchainAnalysis(
            project_path=temp_project_dir,
            language_detection=sample_language_detection,
            frameworks=[Framework(name="pytest", framework_type="testing")],
        )
        assert analysis_without_web.is_web_project is False

    def test_requires_devops_agent_from_deployment_target(
        self, temp_project_dir, sample_language_detection
    ):
        """Test requires_devops_agent based on deployment target."""
        analysis = ToolchainAnalysis(
            project_path=temp_project_dir,
            language_detection=sample_language_detection,
            deployment_target=DeploymentTarget(
                target_type="cloud", platform="aws", requires_ops_agent=True
            ),
        )
        assert analysis.requires_devops_agent is True

    def test_requires_devops_agent_from_tools(
        self, temp_project_dir, sample_language_detection
    ):
        """Test requires_devops_agent based on development tools."""
        analysis = ToolchainAnalysis(
            project_path=temp_project_dir,
            language_detection=sample_language_detection,
            development_tools=[
                ToolchainComponent(name="Docker"),
                ToolchainComponent(name="Make"),
            ],
        )
        assert analysis.requires_devops_agent is True

    def test_to_dict_method(self, temp_project_dir, sample_language_detection):
        """Test to_dict serialization method."""
        analysis = ToolchainAnalysis(
            project_path=temp_project_dir,
            language_detection=sample_language_detection,
            frameworks=[Framework(name="Django", version="5.0", framework_type="web")],
            overall_confidence=ConfidenceLevel.HIGH,
        )
        result = analysis.to_dict()

        assert "project_path" in result
        assert "language_detection" in result
        assert "frameworks" in result
        assert result["language_detection"]["primary_language"] == "Python"
        assert len(result["frameworks"]) == 1
        assert result["frameworks"][0]["name"] == "Django"
