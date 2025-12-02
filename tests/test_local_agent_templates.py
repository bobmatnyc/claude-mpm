"""Tests for local agent template support in Claude MPM."""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from claude_mpm.services.agents.deployment.local_template_deployment import (
    LocalTemplateDeploymentService,
)
from claude_mpm.services.agents.local_template_manager import (
    LocalAgentTemplate,
    LocalAgentTemplateManager,
)


class TestLocalAgentTemplate:
    """Test LocalAgentTemplate model."""

    def test_template_creation_with_defaults(self):
        """Test creating a template with default values."""
        template = LocalAgentTemplate(
            agent_id="test_agent", instructions="Test instructions"
        )

        assert template.agent_id == "test_agent"
        assert template.schema_version == "1.3.0"
        assert template.agent_version == "1.0.0"
        assert template.tier == "project"
        assert template.priority == 1000
        assert template.is_local is True
        assert template.metadata["name"] == "Test Agent"
        assert template.capabilities["model"] == "sonnet"

    def test_template_to_json(self):
        """Test converting template to JSON."""
        template = LocalAgentTemplate(
            agent_id="test_agent",
            agent_version="2.0.0",
            author="test_project",
            instructions="Custom instructions",
        )

        json_data = template.to_json()

        assert json_data["agent_id"] == "test_agent"
        assert json_data["agent_version"] == "2.0.0"
        assert json_data["author"] == "test_project"
        assert json_data["instructions"] == "Custom instructions"
        assert json_data["priority"] == 1000

    def test_template_from_json(self):
        """Test creating template from JSON data."""
        json_data = {
            "agent_id": "custom_agent",
            "agent_version": "1.5.0",
            "author": "my_project",
            "metadata": {
                "name": "Custom Agent",
                "description": "A custom test agent",
                "tags": ["custom", "test"],
            },
            "capabilities": {"model": "opus", "tools": "file,search"},
            "instructions": "Do custom things",
            "priority": 2000,
        }

        template = LocalAgentTemplate.from_json(json_data)

        assert template.agent_id == "custom_agent"
        assert template.agent_version == "1.5.0"
        assert template.author == "my_project"
        assert template.metadata["name"] == "Custom Agent"
        assert template.capabilities["model"] == "opus"
        assert template.priority == 2000


class TestLocalAgentTemplateManager:
    """Test LocalAgentTemplateManager."""

    def test_get_project_name(self):
        """Test getting project name from working directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir) / "test_project"
            project_dir.mkdir()

            manager = LocalAgentTemplateManager(working_directory=project_dir)
            assert manager.get_project_name() == "test_project"

    def test_create_local_template(self):
        """Test creating a new local template."""
        manager = LocalAgentTemplateManager()

        template = manager.create_local_template(
            agent_id="research_custom",
            name="Custom Research Agent",
            description="Specialized research agent",
            instructions="Conduct detailed research",
            model="opus",
            tools=["search", "web"],
            parent_agent="research",
            tier="project",
        )

        assert template.agent_id == "research_custom"
        assert template.metadata["name"] == "Custom Research Agent"
        assert template.metadata["description"] == "Specialized research agent"
        assert template.instructions == "Conduct detailed research"
        assert template.capabilities["model"] == "opus"
        assert template.capabilities["tools"] == "search,web"
        assert template.parent_agent == "research"
        assert template.tier == "project"

    def test_save_and_load_template(self):
        """Test saving and loading a template."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir) / "test_project"
            project_dir.mkdir()

            manager = LocalAgentTemplateManager(working_directory=project_dir)

            # Create and save template
            template = manager.create_local_template(
                agent_id="test_save",
                name="Test Save Agent",
                description="Testing save functionality",
                instructions="Test instructions",
                tier="project",
            )

            saved_path = manager.save_local_template(template)
            assert saved_path.exists()
            assert saved_path.name == "test_save.json"

            # Load template
            loaded_template = manager.get_local_template("test_save")
            assert loaded_template is not None
            assert loaded_template.agent_id == "test_save"
            assert loaded_template.metadata["name"] == "Test Save Agent"

    def test_validate_template(self):
        """Test template validation."""
        manager = LocalAgentTemplateManager()

        # Valid template
        valid_template = LocalAgentTemplate(
            agent_id="valid_agent",
            instructions="Valid instructions",
            metadata={"name": "Valid Agent"},
        )
        is_valid, errors = manager.validate_local_template(valid_template)
        assert is_valid is True
        assert len(errors) == 0

        # Invalid template (missing agent_id)
        invalid_template = LocalAgentTemplate(agent_id="", instructions="Instructions")
        is_valid, errors = manager.validate_local_template(invalid_template)
        assert is_valid is False
        assert "agent_id is required" in errors

        # Invalid template (reserved name)
        reserved_template = LocalAgentTemplate(
            agent_id="pm", instructions="Instructions"
        )
        is_valid, errors = manager.validate_local_template(reserved_template)
        assert is_valid is False
        assert any("Reserved agent ID" in error for error in errors)

    def test_discover_local_templates(self):
        """Test discovering templates from multiple directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir) / "test_project"
            project_dir.mkdir()

            # Create project agents directory
            project_agents_dir = project_dir / ".claude-mpm" / "agents"
            project_agents_dir.mkdir(parents=True)

            # Create a project template
            project_template = {
                "agent_id": "project_agent",
                "metadata": {"name": "Project Agent"},
                "instructions": "Project instructions",
            }
            with open(project_agents_dir / "project_agent.json", "w") as f:
                json.dump(project_template, f)

            # Initialize manager and discover
            manager = LocalAgentTemplateManager(working_directory=project_dir)
            templates = manager.discover_local_templates()

            assert "project_agent" in templates
            assert templates["project_agent"].tier == "project"


class TestLocalTemplateDeploymentService:
    """Test LocalTemplateDeploymentService."""

    def test_convert_to_yaml_format(self):
        """Test converting JSON template to YAML format."""
        service = LocalTemplateDeploymentService()

        template = LocalAgentTemplate(
            agent_id="test_convert",
            agent_version="1.2.0",
            author="test_project",
            metadata={
                "name": "Test Convert Agent",
                "description": "Testing conversion",
                "tags": ["test", "convert"],
            },
            capabilities={"model": "sonnet", "tools": "*"},
            instructions="Test conversion instructions",
            tier="project",
            priority=2000,
        )

        yaml_content = service._convert_to_yaml_format(template)

        assert "---" in yaml_content
        assert "name: Test Convert Agent" in yaml_content
        assert "version: 1.2.0" in yaml_content
        assert "author: test_project" in yaml_content
        assert "is_local: true" in yaml_content
        assert "Test conversion instructions" in yaml_content

    def test_deploy_single_template(self):
        """Test deploying a single template."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir) / "test_project"
            project_dir.mkdir()

            # Create target directory
            target_dir = project_dir / ".claude" / "agents"
            target_dir.mkdir(parents=True)

            service = LocalTemplateDeploymentService(working_directory=project_dir)
            service.target_dir = target_dir

            # Create template
            template = LocalAgentTemplate(
                agent_id="deploy_test",
                metadata={"name": "Deploy Test Agent"},
                instructions="Deploy test instructions",
            )

            # Deploy template
            result = service._deploy_single_template(template, force_rebuild=False)

            assert result == "deployed"
            assert (target_dir / "deploy_test.md").exists()

            # Check content
            content = (target_dir / "deploy_test.md").read_text()
            assert "Deploy Test Agent" in content
            assert "Deploy test instructions" in content

    def test_sync_local_templates(self):
        """Test synchronizing local templates with deployed agents."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir) / "test_project"
            project_dir.mkdir()

            # Create local templates directory
            local_dir = project_dir / ".claude-mpm" / "agents"
            local_dir.mkdir(parents=True)

            # Create target directory
            target_dir = project_dir / ".claude" / "agents"
            target_dir.mkdir(parents=True)

            # Create a local template
            template_data = {
                "agent_id": "sync_test",
                "agent_version": "1.0.0",
                "metadata": {"name": "Sync Test Agent"},
                "instructions": "Sync test",
            }
            with open(local_dir / "sync_test.json", "w") as f:
                json.dump(template_data, f)

            # Initialize services
            service = LocalTemplateDeploymentService(working_directory=project_dir)
            service.target_dir = target_dir

            # Sync templates
            results = service.sync_local_templates()

            assert "sync_test" in results["added"]
            assert (target_dir / "sync_test.md").exists()


@pytest.fixture
def mock_path_manager():
    """Mock path manager for testing."""
    mock = MagicMock()
    mock.project_root = Path("/test/project")
    return mock


def test_unified_registry_discovers_local_templates(mock_path_manager):
    """Test that UnifiedAgentRegistry properly discovers local JSON templates."""
    with patch(
        "claude_mpm.core.unified_agent_registry.get_path_manager"
    ) as mock_get_pm:
        mock_get_pm.return_value = mock_path_manager

        from claude_mpm.core.unified_agent_registry import UnifiedAgentRegistry

        with tempfile.TemporaryDirectory() as tmpdir:
            # Setup test directories
            project_dir = Path(tmpdir) / "project"
            project_dir.mkdir()

            local_agents_dir = project_dir / ".claude-mpm" / "agents"
            local_agents_dir.mkdir(parents=True)

            # Create a local JSON template
            template_data = {
                "agent_id": "custom_research",
                "agent_version": "2.0.0",
                "author": "test_project",
                "metadata": {
                    "name": "Custom Research Agent",
                    "description": "Specialized research",
                    "tags": ["research", "custom", "local"],
                },
                "capabilities": {"model": "opus", "tools": "*"},
                "instructions": "Custom research instructions",
            }

            with open(local_agents_dir / "custom_research.json", "w") as f:
                json.dump(template_data, f)

            # Mock project root to point to our test directory
            mock_path_manager.project_root = project_dir
            mock_path_manager.get_project_agents_dir.return_value = (
                project_dir / ".claude" / "agents"
            )
            mock_path_manager.get_user_agents_dir.return_value = (
                Path.home() / ".claude" / "agents"
            )
            mock_path_manager.get_system_agents_dir.return_value = Path(
                "/system/agents"
            )

            # Initialize registry with our test path
            registry = UnifiedAgentRegistry()

            # Manually add our local path
            registry.add_discovery_path(local_agents_dir)

            # Discover agents
            agents = registry.discover_agents(force_refresh=True)

            # Verify local agent was discovered
            assert "custom_research" in agents
            agent = agents["custom_research"]
            assert agent.name == "custom_research"
            assert agent.version == "2.0.0"
            assert agent.author == "test_project"
            assert "local" in agent.tags


def test_framework_loader_includes_local_agents():
    """Test that FrameworkLoader properly includes local agents in capabilities."""
    from claude_mpm.core.framework_loader import FrameworkLoader

    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir) / "test_project"
        project_dir.mkdir()

        # Create local agents directory
        local_dir = project_dir / ".claude-mpm" / "agents"
        local_dir.mkdir(parents=True)

        # Create a local template
        template_data = {
            "agent_id": "local_test",
            "metadata": {
                "name": "Local Test Agent",
                "description": "Testing local agent in framework",
            },
            "capabilities": {"model": "sonnet", "tools": "*"},
            "instructions": "Local test instructions",
        }

        with open(local_dir / "local_test.json", "w") as f:
            json.dump(template_data, f)

        # Initialize framework loader with mock cache
        with patch("claude_mpm.core.framework_loader.CacheManager") as MockCache:
            mock_cache = MagicMock()
            mock_cache.get_capabilities.return_value = None  # Force regeneration
            MockCache.return_value = mock_cache
            MockCache.__name__ = "CacheManager"  # Fix mock attribute issue

            # Change working directory to our test project
            import os

            original_cwd = os.getcwd()
            try:
                os.chdir(project_dir)

                loader = FrameworkLoader()

                # Generate capabilities
                capabilities = loader._generate_agent_capabilities_section()

                # Verify local agent is included
                assert "local_test" in capabilities
                assert "Local Test Agent" in capabilities
                assert "[LOCAL-PROJECT]" in capabilities or "LOCAL" in capabilities

            finally:
                os.chdir(original_cwd)
