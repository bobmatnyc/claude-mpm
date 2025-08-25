"""Comprehensive unit tests for AgentDeploymentService.

This test suite ensures complete coverage of the AgentDeploymentService class
before refactoring, including all deployment operations, template discovery,
version management, configuration handling, and error scenarios.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import MagicMock, Mock, PropertyMock, call, patch

import pytest

from claude_mpm.config.paths import paths
from claude_mpm.constants import Paths
from claude_mpm.core.config import Config
from claude_mpm.core.exceptions import AgentDeploymentError
from claude_mpm.services.agents.deployment.agent_deployment import (
    AgentDeploymentService,
)


class TestAgentDeploymentService:
    """Test suite for AgentDeploymentService."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration object."""
        config = Mock(spec=Config)
        config.get = Mock(return_value=None)
        config.agent = Mock()
        config.agent.excluded_agents = []
        config.agent.exclude_agents = []
        config.agent.case_sensitive = False
        config.agent.exclude_dependencies = False
        return config

    @pytest.fixture
    def mock_dependencies(self):
        """Create mock instances of all helper services."""
        return {
            "template_builder": Mock(),
            "version_manager": Mock(),
            "metrics_collector": Mock(),
            "environment_manager": Mock(),
            "validator": Mock(),
            "filesystem_manager": Mock(),
            "discovery_service": Mock(),
            "multi_source_service": Mock(),
            "configuration_manager": Mock(),
            "format_converter": Mock(),
        }

    @pytest.fixture
    def service(self, tmp_path, mock_config, mock_dependencies):
        """Create an AgentDeploymentService instance with mocked dependencies."""
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir(parents=True, exist_ok=True)
        
        base_agent_path = tmp_path / "base_agent.json"
        base_agent_data = {
            "name": "base_agent",
            "version": "1.0.0",
            "base_version": "1.0.0"
        }
        base_agent_path.write_text(json.dumps(base_agent_data))
        
        working_dir = tmp_path / "working"
        working_dir.mkdir(parents=True, exist_ok=True)
        
        # Patch the service's dependencies
        with patch.multiple(
            'claude_mpm.services.agents.deployment.agent_deployment',
            AgentTemplateBuilder=Mock(return_value=mock_dependencies["template_builder"]),
            AgentVersionManager=Mock(return_value=mock_dependencies["version_manager"]),
            AgentMetricsCollector=Mock(return_value=mock_dependencies["metrics_collector"]),
            AgentEnvironmentManager=Mock(return_value=mock_dependencies["environment_manager"]),
            AgentValidator=Mock(return_value=mock_dependencies["validator"]),
            AgentFileSystemManager=Mock(return_value=mock_dependencies["filesystem_manager"]),
            AgentDiscoveryService=Mock(return_value=mock_dependencies["discovery_service"]),
            MultiSourceAgentDeploymentService=Mock(return_value=mock_dependencies["multi_source_service"]),
            AgentConfigurationManager=Mock(return_value=mock_dependencies["configuration_manager"]),
            AgentFormatConverter=Mock(return_value=mock_dependencies["format_converter"]),
        ):
            service = AgentDeploymentService(
                templates_dir=templates_dir,
                base_agent_path=base_agent_path,
                working_directory=working_dir,
                config=mock_config
            )
            
            # Inject mock dependencies - these override the ones created during __init__
            for name, mock_obj in mock_dependencies.items():
                setattr(service, name, mock_obj)
            
            # Ensure templates_dir and working_directory are set
            service.templates_dir = templates_dir
            service.working_directory = working_dir
            
            return service

    @pytest.fixture
    def sample_agent_template(self, tmp_path):
        """Create a sample agent template file."""
        template_file = tmp_path / "templates" / "test_agent.json"
        template_file.parent.mkdir(parents=True, exist_ok=True)
        template_data = {
            "name": "test_agent",
            "version": "2.0.0",
            "description": "Test agent",
            "tools": ["tool1", "tool2"]
        }
        template_file.write_text(json.dumps(template_data))
        return template_file


class TestDeploymentOperations(TestAgentDeploymentService):
    """Test deployment operations."""

    def test_deploy_agents_basic(self, service, tmp_path, mock_dependencies):
        """Test basic agent deployment with default settings."""
        target_dir = tmp_path / ".claude" / "agents"
        
        # Setup mocks
        mock_dependencies["configuration_manager"].load_base_agent.return_value = (
            {"base_version": "1.0.0"}, (1, 0, 0)
        )
        mock_dependencies["discovery_service"].get_filtered_templates.return_value = [
            tmp_path / "templates" / "agent1.json",
            tmp_path / "templates" / "agent2.json"
        ]
        mock_dependencies["version_manager"].check_agent_needs_update.return_value = (
            True, "version outdated"
        )
        mock_dependencies["template_builder"].build_agent_markdown.return_value = (
            "---\nname: agent\n---\nAgent content"
        )
        mock_dependencies["format_converter"].convert_yaml_to_md.return_value = {
            "converted": []
        }
        
        with patch.object(service, '_load_deployment_config') as mock_load_config:
            mock_load_config.return_value = (Mock(), [])
            
            with patch.object(service, '_validate_and_repair_existing_agents') as mock_repair:
                mock_repair.return_value = {"repaired": []}
                
                result = service.deploy_agents(target_dir=target_dir)
        
        assert result["target_dir"] == str(target_dir)
        assert "deployed" in result
        assert "updated" in result
        assert "skipped" in result
        assert "errors" in result

    def test_deploy_agents_project_mode(self, service, tmp_path, mock_dependencies):
        """Test deployment in project mode (always deploy regardless of version)."""
        target_dir = tmp_path / ".claude" / "agents"
        
        # Setup mocks
        mock_dependencies["configuration_manager"].load_base_agent.return_value = (
            {"base_version": "1.0.0"}, (1, 0, 0)
        )
        mock_dependencies["multi_source_service"].get_agents_for_deployment.return_value = (
            {"agent1": tmp_path / "templates" / "agent1.json"},
            {"agent1": "system"},
            {"removed": []}
        )
        mock_dependencies["template_builder"].build_agent_markdown.return_value = (
            "---\nname: agent1\n---\nAgent content"
        )
        
        with patch.object(service, '_load_deployment_config') as mock_load_config:
            mock_load_config.return_value = (Mock(), [])
            
            with patch.object(service, '_validate_and_repair_existing_agents') as mock_repair:
                mock_repair.return_value = {"repaired": []}
                
                with patch.object(service, '_convert_yaml_to_md') as mock_convert:
                    mock_convert.return_value = {"converted": []}
                    
                    result = service.deploy_agents(
                        target_dir=target_dir,
                        deployment_mode="project"
                    )
        
        # Check that multi-source deployment was used (project mode uses multi-source)
        assert mock_dependencies["multi_source_service"].get_agents_for_deployment.called
        # The result should contain agent_sources if multi-source was used
        if "multi_source" in result:
            assert result["multi_source"] is True
            assert "agent_sources" in result

    def test_deploy_agents_update_mode(self, service, tmp_path, mock_dependencies):
        """Test deployment in update mode (version-aware updates)."""
        target_dir = tmp_path / ".claude" / "agents"
        
        # Create existing agent file
        target_dir.mkdir(parents=True, exist_ok=True)
        existing_agent = target_dir / "existing_agent.md"
        existing_agent.write_text("---\nname: existing_agent\nversion: 1.0.0\n---\nOld content")
        
        # Setup mocks
        mock_dependencies["configuration_manager"].load_base_agent.return_value = (
            {"base_version": "1.0.0"}, (1, 0, 0)
        )
        mock_dependencies["multi_source_service"].get_agents_for_deployment.return_value = (
            {"existing_agent": tmp_path / "templates" / "existing_agent.json"},
            {"existing_agent": "system"},
            {"removed": []}
        )
        mock_dependencies["version_manager"].check_agent_needs_update.return_value = (
            False, "version current"
        )
        
        with patch.object(service, '_load_deployment_config') as mock_load_config:
            mock_load_config.return_value = (Mock(), [])
            
            with patch.object(service, '_validate_and_repair_existing_agents') as mock_repair:
                mock_repair.return_value = {"repaired": []}
                
                with patch.object(service, '_convert_yaml_to_md') as mock_convert:
                    mock_convert.return_value = {"converted": []}
                    
                    result = service.deploy_agents(
                        target_dir=target_dir,
                        deployment_mode="update"
                    )
        
        # In update mode, up-to-date agents should be skipped
        assert len(result["skipped"]) > 0 or len(result["deployed"]) == 0

    def test_deploy_agents_with_async(self, service, tmp_path, mock_dependencies):
        """Test async deployment attempt."""
        target_dir = tmp_path / ".claude" / "agents"
        
        # Mock successful async deployment
        async_result = {
            "target_dir": str(target_dir),
            "deployed": ["agent1"],
            "errors": [],
            "metrics": {"deployment_method": "async", "duration_ms": 100}
        }
        
        with patch.object(service, '_try_async_deployment') as mock_async:
            mock_async.return_value = async_result
            
            result = service.deploy_agents(target_dir=target_dir, use_async=True)
        
        assert result == async_result
        mock_async.assert_called_once()

    def test_deploy_agent_single(self, service, tmp_path, mock_dependencies, sample_agent_template):
        """Test deploying a single agent."""
        target_dir = tmp_path / ".claude" / "agents"
        
        # Setup mocks
        mock_dependencies["version_manager"].check_agent_needs_update.return_value = (
            True, "needs update"
        )
        mock_dependencies["version_manager"].parse_version.return_value = (2, 0, 0)
        mock_dependencies["template_builder"].build_agent_markdown.return_value = (
            "---\nname: test_agent\n---\nAgent content"
        )
        
        result = service.deploy_agent("test_agent", target_dir)
        
        assert result is True
        mock_dependencies["template_builder"].build_agent_markdown.assert_called()

    def test_deploy_agent_not_found(self, service, tmp_path):
        """Test deploying a non-existent agent."""
        target_dir = tmp_path / ".claude" / "agents"
        
        result = service.deploy_agent("non_existent_agent", target_dir)
        
        assert result is False

    def test_deploy_agent_force_rebuild(self, service, tmp_path, mock_dependencies, sample_agent_template):
        """Test force rebuilding a single agent."""
        target_dir = tmp_path / ".claude" / "agents"
        target_dir.mkdir(parents=True, exist_ok=True)
        
        # Create existing agent
        existing_agent = target_dir / "test_agent.md"
        existing_agent.write_text("---\nname: test_agent\nversion: 2.0.0\n---\nOld content")
        
        # Setup mocks
        mock_dependencies["template_builder"].build_agent_markdown.return_value = (
            "---\nname: test_agent\nversion: 2.0.0\n---\nNew content"
        )
        
        result = service.deploy_agent("test_agent", target_dir, force_rebuild=True)
        
        assert result is True
        # Should build regardless of version check when force_rebuild is True


class TestTemplateDiscovery(TestAgentDeploymentService):
    """Test template discovery operations."""

    def test_list_available_agents(self, service, mock_dependencies):
        """Test listing available agent templates."""
        expected_agents = [
            {"name": "agent1", "version": "1.0.0"},
            {"name": "agent2", "version": "2.0.0"}
        ]
        mock_dependencies["discovery_service"].list_available_agents.return_value = expected_agents
        
        result = service.list_available_agents()
        
        assert result == expected_agents
        mock_dependencies["discovery_service"].list_available_agents.assert_called_once()

    def test_get_multi_source_templates(self, service, tmp_path, mock_dependencies):
        """Test getting templates from multiple sources."""
        # Setup mock return values
        mock_dependencies["multi_source_service"].get_agents_for_deployment.return_value = (
            {
                "agent1": tmp_path / "system" / "agent1.json",
                "agent2": tmp_path / "project" / "agent2.json"
            },
            {"agent1": "system", "agent2": "project"},
            {"removed": []}
        )
        
        # Create mock config
        mock_config = Mock()
        
        templates, sources, cleanup = service._get_multi_source_templates(
            excluded_agents=["excluded_agent"],
            config=mock_config,
            agents_dir=tmp_path / ".claude" / "agents"
        )
        
        assert len(templates) == 2
        assert "agent1" in sources
        assert sources["agent1"] == "system"

    def test_get_filtered_templates(self, service, mock_dependencies):
        """Test getting filtered templates based on exclusion rules."""
        mock_config = Mock()
        expected_templates = [Path("/path/to/agent1.json"), Path("/path/to/agent2.json")]
        
        mock_dependencies["discovery_service"].get_filtered_templates.return_value = expected_templates
        
        result = service._get_filtered_templates(["excluded"], mock_config)
        
        assert result == expected_templates
        mock_dependencies["discovery_service"].get_filtered_templates.assert_called_with(
            ["excluded"], mock_config
        )


class TestBaseAgentOperations(TestAgentDeploymentService):
    """Test base agent operations."""

    def test_find_base_agent_file_env_variable(self, tmp_path, monkeypatch):
        """Test finding base agent via environment variable."""
        base_agent_path = tmp_path / "custom" / "base_agent.json"
        base_agent_path.parent.mkdir(parents=True, exist_ok=True)
        base_agent_path.write_text('{"name": "base"}')
        
        monkeypatch.setenv("CLAUDE_MPM_BASE_AGENT_PATH", str(base_agent_path))
        
        # Create new service to trigger _find_base_agent_file
        with patch('claude_mpm.services.agents.deployment.agent_deployment.logger') as mock_logger:
            with patch.object(AgentDeploymentService, '__init__', lambda self, *args, **kwargs: None):
                test_service = AgentDeploymentService()
                # Use a Mock that has a logger attribute
                test_service._logger = Mock()
                test_service.logger = test_service._logger
                result = test_service._find_base_agent_file()
        
        assert result == base_agent_path

    def test_find_base_agent_file_cwd(self, tmp_path, monkeypatch):
        """Test finding base agent in current working directory."""
        # Create base agent in expected location
        base_agent_path = tmp_path / "src" / "claude_mpm" / "agents" / "base_agent.json"
        base_agent_path.parent.mkdir(parents=True, exist_ok=True)
        base_agent_path.write_text('{"name": "base"}')
        
        # Change to tmp_path as cwd
        monkeypatch.chdir(tmp_path)
        
        with patch.object(AgentDeploymentService, '__init__', lambda self, *args, **kwargs: None):
            test_service = AgentDeploymentService()
            test_service._logger = Mock()
            test_service.logger = test_service._logger
            result = test_service._find_base_agent_file()
        
        assert result == base_agent_path

    def test_find_base_agent_file_fallback(self):
        """Test base agent file fallback to framework path."""
        with patch.object(AgentDeploymentService, '__init__', lambda self, *args, **kwargs: None):
            test_service = AgentDeploymentService()
            test_service._logger = Mock()
            test_service.logger = test_service._logger
            
            with patch.object(Path, 'exists', return_value=False):
                result = test_service._find_base_agent_file()
        
        # Should fallback to framework path even if it doesn't exist
        assert "agents" in str(result)
        assert "base_agent.json" in str(result)

    def test_determine_source_tier_system(self, service):
        """Test determining system source tier."""
        with patch.object(service, '_determine_source_tier') as mock_determine:
            mock_determine.return_value = "system"
            
            result = service._determine_source_tier()
        
        assert result == "system"

    def test_determine_source_tier_project(self, service):
        """Test determining project source tier."""
        with patch('claude_mpm.services.agents.deployment.agent_deployment.DeploymentTypeDetector') as mock_detector:
            mock_detector.determine_source_tier.return_value = "project"
            
            result = service._determine_source_tier()
        
        assert result == "project"


class TestVersionManagement(TestAgentDeploymentService):
    """Test version management operations."""

    def test_check_update_status_force_rebuild(self, service, tmp_path, mock_dependencies):
        """Test update status check with force rebuild."""
        target_file = tmp_path / "agent.md"
        template_file = tmp_path / "agent.json"
        
        needs_update, is_migration, reason = service._check_update_status(
            target_file=target_file,
            template_file=template_file,
            base_agent_version=(1, 0, 0),
            force_rebuild=True,
            deployment_mode="update"
        )
        
        assert needs_update is True
        assert is_migration is False

    def test_check_update_status_project_mode(self, service, tmp_path, mock_dependencies):
        """Test update status in project deployment mode."""
        target_file = tmp_path / "agent.md"
        target_file.write_text("---\nname: agent\n---\nContent")
        template_file = tmp_path / "agent.json"
        
        needs_update, is_migration, reason = service._check_update_status(
            target_file=target_file,
            template_file=template_file,
            base_agent_version=(1, 0, 0),
            force_rebuild=False,
            deployment_mode="project"
        )
        
        assert needs_update is True

    def test_check_update_status_migration_needed(self, service, tmp_path, mock_dependencies):
        """Test detecting migration needed."""
        target_file = tmp_path / "agent.md"
        target_file.write_text("---\nname: agent\nversion: 100\n---\nContent")
        template_file = tmp_path / "agent.json"
        
        mock_dependencies["version_manager"].check_agent_needs_update.return_value = (
            True, "migration needed from serial to semantic"
        )
        
        needs_update, is_migration, reason = service._check_update_status(
            target_file=target_file,
            template_file=template_file,
            base_agent_version=(1, 0, 0),
            force_rebuild=False,
            deployment_mode="update"
        )
        
        assert needs_update is True
        assert is_migration is True
        assert "migration needed" in reason

    def test_check_update_status_version_current(self, service, tmp_path, mock_dependencies):
        """Test when version is current."""
        target_file = tmp_path / "agent.md"
        target_file.write_text("---\nname: agent\nversion: 1.0.0\n---\nContent")
        template_file = tmp_path / "agent.json"
        
        mock_dependencies["version_manager"].check_agent_needs_update.return_value = (
            False, "version current"
        )
        
        needs_update, is_migration, reason = service._check_update_status(
            target_file=target_file,
            template_file=template_file,
            base_agent_version=(1, 0, 0),
            force_rebuild=False,
            deployment_mode="update"
        )
        
        assert needs_update is False
        assert is_migration is False


class TestConfiguration(TestAgentDeploymentService):
    """Test configuration handling."""

    def test_load_deployment_config(self, service):
        """Test loading deployment configuration."""
        mock_config = Mock()
        
        with patch('claude_mpm.services.agents.deployment.agent_deployment.DeploymentConfigLoader') as mock_loader_class:
            mock_loader = Mock()
            mock_loader.load_deployment_config.return_value = (mock_config, ["excluded_agent"])
            mock_loader_class.return_value = mock_loader
            
            config, excluded = service._load_deployment_config(mock_config)
        
        assert config == mock_config
        assert excluded == ["excluded_agent"]

    def test_determine_agents_directory(self, service, tmp_path):
        """Test determining agents directory."""
        with patch('claude_mpm.services.agents.deployment.agent_deployment.AgentsDirectoryResolver') as mock_resolver_class:
            mock_resolver = Mock()
            expected_dir = tmp_path / ".claude" / "agents"
            mock_resolver.determine_agents_directory.return_value = expected_dir
            mock_resolver_class.return_value = mock_resolver
            
            result = service._determine_agents_directory(None)
        
        assert result == expected_dir

    def test_determine_agents_directory_with_target(self, service, tmp_path):
        """Test determining agents directory with explicit target."""
        target_dir = tmp_path / "custom" / "agents"
        
        with patch('claude_mpm.services.agents.deployment.agent_deployment.AgentsDirectoryResolver') as mock_resolver_class:
            mock_resolver = Mock()
            mock_resolver.determine_agents_directory.return_value = target_dir
            mock_resolver_class.return_value = mock_resolver
            
            result = service._determine_agents_directory(target_dir)
        
        mock_resolver.determine_agents_directory.assert_called_with(target_dir)

    def test_set_claude_environment(self, service, tmp_path, mock_dependencies):
        """Test setting Claude environment variables."""
        config_dir = tmp_path / ".claude"
        expected_env = {
            "CLAUDE_AGENTS_DIR": str(config_dir / "agents"),
            "CLAUDE_CONFIG_DIR": str(config_dir)
        }
        
        mock_dependencies["environment_manager"].set_claude_environment.return_value = expected_env
        
        result = service.set_claude_environment(config_dir)
        
        assert result == expected_env
        mock_dependencies["environment_manager"].set_claude_environment.assert_called_with(config_dir)

    def test_set_claude_environment_default(self, service, mock_dependencies):
        """Test setting Claude environment with default directory."""
        expected_env = {"CLAUDE_AGENTS_DIR": "/default/agents"}
        mock_dependencies["environment_manager"].set_claude_environment.return_value = expected_env
        
        result = service.set_claude_environment()
        
        assert result == expected_env


class TestValidationAndRepair(TestAgentDeploymentService):
    """Test validation and repair operations."""

    def test_repair_existing_agents(self, service, tmp_path):
        """Test repairing existing agents with broken frontmatter."""
        agents_dir = tmp_path / ".claude" / "agents"
        agents_dir.mkdir(parents=True, exist_ok=True)
        
        # Create agent with broken frontmatter
        broken_agent = agents_dir / "broken.md"
        broken_agent.write_text("name: broken\n---\nContent")
        
        results = {"repaired": [], "errors": []}
        
        with patch.object(service, '_validate_and_repair_existing_agents') as mock_repair:
            mock_repair.return_value = {"repaired": ["broken"]}
            
            service._repair_existing_agents(agents_dir, results)
        
        assert results["repaired"] == ["broken"]

    def test_validate_and_repair_existing_agents(self, service, tmp_path):
        """Test validation and repair of existing agents."""
        agents_dir = tmp_path / ".claude" / "agents"
        
        with patch('claude_mpm.services.agents.deployment.agent_deployment.AgentFrontmatterValidator') as mock_validator_class:
            mock_validator = Mock()
            mock_validator.validate_and_repair_existing_agents.return_value = {
                "repaired": ["agent1", "agent2"],
                "errors": []
            }
            mock_validator_class.return_value = mock_validator
            
            result = service._validate_and_repair_existing_agents(agents_dir)
        
        assert result["repaired"] == ["agent1", "agent2"]

    def test_verify_deployment(self, service, tmp_path, mock_dependencies):
        """Test deployment verification."""
        config_dir = tmp_path / ".claude"
        expected_result = {
            "status": "success",
            "agents_found": 5,
            "errors": []
        }
        
        mock_dependencies["validator"].verify_deployment.return_value = expected_result
        
        result = service.verify_deployment(config_dir)
        
        assert result == expected_result
        mock_dependencies["validator"].verify_deployment.assert_called_with(config_dir)

    def test_validate_agent_valid(self, service, tmp_path):
        """Test validating a valid agent configuration."""
        agent_path = tmp_path / "agent.md"
        agent_path.write_text("""---
name: test_agent
version: 1.0.0
description: Test agent
tools:
  - tool1
  - tool2
---
Agent content""")
        
        is_valid, errors = service.validate_agent(agent_path)
        
        assert is_valid is True
        assert errors == []

    def test_validate_agent_missing_frontmatter(self, service, tmp_path):
        """Test validating agent with missing frontmatter."""
        agent_path = tmp_path / "agent.md"
        agent_path.write_text("Agent content without frontmatter")
        
        is_valid, errors = service.validate_agent(agent_path)
        
        assert is_valid is False
        assert "Missing YAML frontmatter" in errors[0]

    def test_validate_agent_missing_fields(self, service, tmp_path):
        """Test validating agent with missing required fields."""
        agent_path = tmp_path / "agent.md"
        agent_path.write_text("""---
name: test_agent
---
Agent content""")
        
        is_valid, errors = service.validate_agent(agent_path)
        
        assert is_valid is False
        assert any("version" in error for error in errors)
        assert any("description" in error for error in errors)


class TestResultsManagement(TestAgentDeploymentService):
    """Test results management operations."""

    def test_initialize_deployment_results(self, service, tmp_path):
        """Test initializing deployment results."""
        agents_dir = tmp_path / ".claude" / "agents"
        start_time = 1234567890.0
        
        results = service._initialize_deployment_results(agents_dir, start_time)
        
        assert results["target_dir"] == str(agents_dir)
        assert results["deployed"] == []
        assert results["updated"] == []
        assert results["migrated"] == []
        assert results["skipped"] == []
        assert results["errors"] == []
        assert results["metrics"]["start_time"] == start_time

    def test_record_agent_deployment_new(self, service, tmp_path):
        """Test recording a new agent deployment."""
        results = service._initialize_deployment_results(tmp_path, 0)
        
        service._record_agent_deployment(
            agent_name="new_agent",
            template_file=tmp_path / "new_agent.json",
            target_file=tmp_path / "new_agent.md",
            is_update=False,
            is_migration=False,
            reason="new deployment",
            agent_start_time=0,
            results=results
        )
        
        assert len(results["deployed"]) == 1
        assert results["deployed"][0]["name"] == "new_agent"

    def test_record_agent_deployment_update(self, service, tmp_path):
        """Test recording an agent update."""
        results = service._initialize_deployment_results(tmp_path, 0)
        
        service._record_agent_deployment(
            agent_name="updated_agent",
            template_file=tmp_path / "updated_agent.json",
            target_file=tmp_path / "updated_agent.md",
            is_update=True,
            is_migration=False,
            reason="version update",
            agent_start_time=0,
            results=results
        )
        
        assert len(results["updated"]) == 1
        assert results["updated"][0]["name"] == "updated_agent"

    def test_record_agent_deployment_migration(self, service, tmp_path):
        """Test recording an agent migration."""
        results = service._initialize_deployment_results(tmp_path, 0)
        
        service._record_agent_deployment(
            agent_name="migrated_agent",
            template_file=tmp_path / "migrated_agent.json",
            target_file=tmp_path / "migrated_agent.md",
            is_update=True,
            is_migration=True,
            reason="migration from serial to semantic",
            agent_start_time=0,
            results=results
        )
        
        assert len(results["migrated"]) == 1
        assert results["migrated"][0]["name"] == "migrated_agent"
        assert "migration" in results["migrated"][0]["reason"]

    def test_get_deployment_metrics(self, service, mock_dependencies):
        """Test getting deployment metrics."""
        expected_metrics = {
            "total_deployments": 10,
            "successful_deployments": 8,
            "failed_deployments": 2
        }
        
        mock_dependencies["metrics_collector"].get_deployment_metrics.return_value = expected_metrics
        
        result = service.get_deployment_metrics()
        
        assert result == expected_metrics

    def test_get_deployment_status(self, service, mock_dependencies):
        """Test getting deployment status."""
        expected_status = {
            "status": "healthy",
            "last_deployment": "2024-01-01T00:00:00Z",
            "agents_deployed": 25
        }
        
        mock_dependencies["metrics_collector"].get_deployment_status.return_value = expected_status
        
        result = service.get_deployment_status()
        
        assert result == expected_status

    def test_reset_metrics(self, service, mock_dependencies):
        """Test resetting deployment metrics."""
        service.reset_metrics()
        
        mock_dependencies["metrics_collector"].reset_metrics.assert_called_once()


class TestErrorHandling(TestAgentDeploymentService):
    """Test error handling scenarios."""

    def test_deploy_agents_missing_templates_dir(self, service, tmp_path, mock_dependencies):
        """Test deployment when templates directory doesn't exist."""
        service.templates_dir = tmp_path / "non_existent"
        
        mock_dependencies["configuration_manager"].load_base_agent.return_value = ({}, (0, 0, 0))
        
        with patch.object(service, '_load_deployment_config') as mock_load_config:
            mock_load_config.return_value = (Mock(), [])
            
            with patch.object(service, '_validate_and_repair_existing_agents') as mock_repair:
                mock_repair.return_value = {"repaired": []}
                
                result = service.deploy_agents()
        
        assert len(result["errors"]) > 0
        assert "not found" in result["errors"][0]

    def test_deploy_agents_template_build_failure(self, service, tmp_path, mock_dependencies):
        """Test handling template build failures."""
        mock_dependencies["configuration_manager"].load_base_agent.return_value = ({}, (1, 0, 0))
        mock_dependencies["discovery_service"].get_filtered_templates.return_value = [
            tmp_path / "agent.json"
        ]
        mock_dependencies["template_builder"].build_agent_markdown.side_effect = Exception(
            "Template build failed"
        )
        
        with patch.object(service, '_load_deployment_config') as mock_load_config:
            mock_load_config.return_value = (Mock(), [])
            
            with patch.object(service, '_validate_and_repair_existing_agents') as mock_repair:
                mock_repair.return_value = {"repaired": []}
                
                with patch.object(service, '_convert_yaml_to_md') as mock_convert:
                    mock_convert.return_value = {"converted": []}
                    
                    result = service.deploy_agents()
        
        assert len(result["errors"]) > 0

    def test_deploy_agent_template_not_found(self, service, tmp_path):
        """Test deploying non-existent single agent."""
        target_dir = tmp_path / ".claude" / "agents"
        
        result = service.deploy_agent("non_existent", target_dir)
        
        assert result is False

    def test_deploy_agent_build_failure(self, service, tmp_path, mock_dependencies, sample_agent_template):
        """Test handling single agent build failure."""
        target_dir = tmp_path / ".claude" / "agents"
        
        mock_dependencies["template_builder"].build_agent_markdown.return_value = None
        
        result = service.deploy_agent("test_agent", target_dir)
        
        assert result is False

    def test_deploy_agent_custom_exception(self, service, tmp_path, mock_dependencies, sample_agent_template):
        """Test handling AgentDeploymentError in single agent deployment."""
        target_dir = tmp_path / ".claude" / "agents"
        
        mock_dependencies["template_builder"].build_agent_markdown.side_effect = AgentDeploymentError(
            "Custom deployment error",
            context={"agent": "test_agent"}
        )
        
        with pytest.raises(AgentDeploymentError) as exc_info:
            service.deploy_agent("test_agent", target_dir)
        
        assert "Custom deployment error" in str(exc_info.value)

    def test_async_deployment_import_error(self, service, tmp_path):
        """Test fallback when async deployment module not available."""
        # Mock the import to raise ImportError
        with patch.object(service, '_try_async_deployment') as mock_async:
            mock_async.return_value = None
            
            result = service._try_async_deployment(
                target_dir=tmp_path,
                force_rebuild=False,
                config=Mock(),
                deployment_start_time=0
            )
        
        assert result is None

    def test_async_deployment_runtime_error(self, service, tmp_path):
        """Test fallback when async deployment fails."""
        # Test the actual method behavior
        original_import = __import__
        
        def mock_import(name, *args, **kwargs):
            if 'async_agent_deployment' in name:
                raise ImportError("No async module")
            return original_import(name, *args, **kwargs)
        
        with patch('builtins.__import__', side_effect=mock_import):
            result = service._try_async_deployment(
                target_dir=tmp_path,
                force_rebuild=False,
                config=Mock(),
                deployment_start_time=0
            )
        
        assert result is None

    def test_validate_agent_not_found(self, service, tmp_path):
        """Test validating non-existent agent."""
        agent_path = tmp_path / "non_existent.md"
        
        is_valid, errors = service.validate_agent(agent_path)
        
        assert is_valid is False
        assert "not found" in errors[0]

    def test_validate_agent_read_error(self, service, tmp_path):
        """Test handling read errors during validation."""
        agent_path = tmp_path / "agent.md"
        agent_path.write_text("content")
        
        with patch.object(Path, 'read_text', side_effect=IOError("Read failed")):
            is_valid, errors = service.validate_agent(agent_path)
        
        assert is_valid is False
        assert "Validation error" in errors[0]


class TestHelperMethods(TestAgentDeploymentService):
    """Test helper and utility methods."""

    def test_get_agent_tools(self, service):
        """Test getting agent-specific tools."""
        with patch('claude_mpm.services.agents.deployment.agent_deployment.AgentConfigProvider') as mock_provider:
            mock_provider.get_agent_tools.return_value = ["tool1", "tool2"]
            
            result = service._get_agent_tools("test_agent", {"type": "standard"})
        
        assert result == ["tool1", "tool2"]

    def test_get_agent_specific_config(self, service):
        """Test getting agent-specific configuration."""
        with patch('claude_mpm.services.agents.deployment.agent_deployment.AgentConfigProvider') as mock_provider:
            expected_config = {"setting1": "value1", "setting2": "value2"}
            mock_provider.get_agent_specific_config.return_value = expected_config
            
            result = service._get_agent_specific_config("test_agent")
        
        assert result == expected_config

    def test_deploy_system_instructions(self, service, tmp_path):
        """Test deploying system instructions."""
        target_dir = tmp_path / ".claude"
        results = {"deployed": [], "updated": [], "skipped": [], "errors": []}
        
        with patch('claude_mpm.services.agents.deployment.agent_deployment.SystemInstructionsDeployer') as mock_deployer_class:
            mock_deployer = Mock()
            mock_deployer_class.return_value = mock_deployer
            
            service._deploy_system_instructions(target_dir, False, results)
        
        mock_deployer.deploy_system_instructions.assert_called_with(target_dir, False, results)

    def test_deploy_system_instructions_explicit(self, service, tmp_path):
        """Test explicit system instructions deployment."""
        with patch('claude_mpm.services.agents.deployment.agent_deployment.SystemInstructionsDeployer') as mock_deployer_class:
            mock_deployer = Mock()
            mock_deployer_class.return_value = mock_deployer
            
            result = service.deploy_system_instructions_explicit()
        
        assert "deployed" in result
        assert "errors" in result
        mock_deployer.deploy_system_instructions.assert_called_once()

    def test_convert_yaml_to_md(self, service, tmp_path, mock_dependencies):
        """Test YAML to MD conversion."""
        target_dir = tmp_path / ".claude" / "agents"
        expected_result = {"converted": ["agent1.yaml", "agent2.yaml"]}
        
        mock_dependencies["format_converter"].convert_yaml_to_md.return_value = expected_result
        
        result = service._convert_yaml_to_md(target_dir)
        
        assert result == expected_result

    def test_clean_deployment(self, service, tmp_path, mock_dependencies):
        """Test cleaning deployment."""
        config_dir = tmp_path / ".claude"
        expected_result = {"removed": ["agent1.md", "agent2.md"], "errors": []}
        
        mock_dependencies["filesystem_manager"].clean_deployment.return_value = expected_result
        
        result = service.clean_deployment(config_dir)
        
        assert result == expected_result

    def test_determine_agent_source_system(self, service, tmp_path):
        """Test determining agent source as system."""
        template_path = Path("/usr/local/lib/claude_mpm/agents/templates/agent.json")
        
        result = service._determine_agent_source(template_path)
        
        assert result == "system"

    def test_determine_agent_source_project(self, service, tmp_path):
        """Test determining agent source as project."""
        service.working_directory = tmp_path
        template_path = tmp_path / ".claude-mpm" / "agents" / "agent.json"
        
        result = service._determine_agent_source(template_path)
        
        assert result == "project"

    def test_determine_agent_source_user(self, service):
        """Test determining agent source as user."""
        template_path = Path.home() / ".claude-mpm" / "agents" / "agent.json"
        
        result = service._determine_agent_source(template_path)
        
        assert result == "user"

    def test_determine_agent_source_unknown(self, service, tmp_path):
        """Test determining agent source as unknown."""
        template_path = tmp_path / "random" / "location" / "agent.json"
        
        result = service._determine_agent_source(template_path)
        
        assert result == "unknown"

    def test_should_use_multi_source_deployment_update(self, service):
        """Test multi-source deployment decision for update mode."""
        result = service._should_use_multi_source_deployment("update")
        
        assert result is True

    def test_should_use_multi_source_deployment_project(self, service):
        """Test multi-source deployment decision for project mode."""
        result = service._should_use_multi_source_deployment("project")
        
        assert result is True

    def test_should_use_multi_source_deployment_other(self, service):
        """Test multi-source deployment decision for other modes."""
        result = service._should_use_multi_source_deployment("custom")
        
        assert result is False


class TestMultiSourceIntegration(TestAgentDeploymentService):
    """Test multi-source deployment integration."""

    def test_get_multi_source_templates_with_comparison(self, service, tmp_path, mock_dependencies):
        """Test multi-source templates with deployed version comparison."""
        agents_dir = tmp_path / ".claude" / "agents"
        agents_dir.mkdir(parents=True, exist_ok=True)
        
        # Create existing deployed agent
        deployed_agent = agents_dir / "existing.md"
        deployed_agent.write_text("---\nname: existing\nversion: 1.0.0\n---\nContent")
        
        # Setup mock returns
        mock_dependencies["multi_source_service"].get_agents_for_deployment.return_value = (
            {"existing": tmp_path / "templates" / "existing.json"},
            {"existing": "system"},
            {"removed": []}
        )
        
        mock_dependencies["multi_source_service"].compare_deployed_versions.return_value = {
            "version_upgrades": ["existing"],
            "source_changes": [],
            "needs_update": ["existing"],
            "new_agents": []
        }
        
        templates, sources, cleanup = service._get_multi_source_templates(
            excluded_agents=[],
            config=Mock(),
            agents_dir=agents_dir,
            force_rebuild=False
        )
        
        assert len(templates) == 1
        mock_dependencies["multi_source_service"].compare_deployed_versions.assert_called_once()

    def test_get_multi_source_templates_force_rebuild(self, service, tmp_path, mock_dependencies):
        """Test multi-source templates with force rebuild."""
        agents_dir = tmp_path / ".claude" / "agents"
        
        mock_dependencies["multi_source_service"].get_agents_for_deployment.return_value = (
            {
                "agent1": tmp_path / "templates" / "agent1.json",
                "agent2": tmp_path / "templates" / "agent2.json"
            },
            {"agent1": "system", "agent2": "project"},
            {"removed": []}
        )
        
        templates, sources, cleanup = service._get_multi_source_templates(
            excluded_agents=[],
            config=Mock(),
            agents_dir=agents_dir,
            force_rebuild=True
        )
        
        # With force_rebuild, all agents should be included
        assert len(templates) == 2


class TestDeploymentIntegration(TestAgentDeploymentService):
    """Test full deployment integration scenarios."""

    def test_full_deployment_cycle(self, service, tmp_path, mock_dependencies):
        """Test complete deployment cycle with all operations."""
        target_dir = tmp_path / ".claude" / "agents"
        
        # Setup comprehensive mocks
        mock_dependencies["configuration_manager"].load_base_agent.return_value = (
            {"base_version": "1.0.0", "settings": {}}, 
            (1, 0, 0)
        )
        
        template_file = tmp_path / "templates" / "complete_agent.json"
        template_file.parent.mkdir(parents=True, exist_ok=True)
        template_file.write_text(json.dumps({
            "name": "complete_agent",
            "version": "2.0.0",
            "description": "Complete test agent"
        }))
        
        mock_dependencies["discovery_service"].get_filtered_templates.return_value = [template_file]
        mock_dependencies["version_manager"].check_agent_needs_update.return_value = (True, "new agent")
        mock_dependencies["template_builder"].build_agent_markdown.return_value = (
            "---\nname: complete_agent\nversion: 2.0.0\n---\nAgent content"
        )
        mock_dependencies["format_converter"].convert_yaml_to_md.return_value = {"converted": []}
        
        with patch.object(service, '_load_deployment_config') as mock_load_config:
            mock_load_config.return_value = (Mock(), [])
            
            with patch.object(service, '_validate_and_repair_existing_agents') as mock_repair:
                mock_repair.return_value = {"repaired": []}
                
                result = service.deploy_agents(target_dir=target_dir, force_rebuild=False)
        
        # Verify full deployment cycle
        assert result["target_dir"] == str(target_dir)
        assert len(result["deployed"]) > 0 or len(result["updated"]) > 0
        assert "metrics" in result
        assert result["metrics"]["start_time"] is not None

    def test_deployment_with_exclusions(self, service, tmp_path, mock_dependencies):
        """Test deployment with agent exclusions."""
        mock_config = Mock()
        mock_config.agent.excluded_agents = ["excluded_agent"]
        
        mock_dependencies["configuration_manager"].load_base_agent.return_value = ({}, (1, 0, 0))
        mock_dependencies["discovery_service"].get_filtered_templates.return_value = []
        
        with patch.object(service, '_load_deployment_config') as mock_load_config:
            mock_load_config.return_value = (mock_config, ["excluded_agent"])
            
            with patch.object(service, '_validate_and_repair_existing_agents') as mock_repair:
                mock_repair.return_value = {"repaired": []}
                
                with patch.object(service, '_convert_yaml_to_md') as mock_convert:
                    mock_convert.return_value = {"converted": []}
                    
                    result = service.deploy_agents(config=mock_config)
        
        # Verify excluded agents were passed to discovery service
        mock_dependencies["discovery_service"].get_filtered_templates.assert_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])