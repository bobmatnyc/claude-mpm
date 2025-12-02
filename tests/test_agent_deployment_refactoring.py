"""Tests for the refactored agent deployment components."""

import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from claude_mpm.core.interfaces import AgentDeploymentInterface
from claude_mpm.services.agents.deployment.config import (
    DeploymentConfig,
    DeploymentConfigManager,
)
from claude_mpm.services.agents.deployment.facade import (
    AsyncDeploymentExecutor,
    DeploymentFacade,
    SyncDeploymentExecutor,
)
from claude_mpm.services.agents.deployment.interface_adapter import (
    AgentDeploymentInterfaceAdapter,
)
from claude_mpm.services.agents.deployment.pipeline import (
    ConfigurationLoadStep,
    DeploymentPipelineBuilder,
    DeploymentPipelineExecutor,
    PipelineContext,
    TargetDirectorySetupStep,
)
from claude_mpm.services.agents.deployment.processors import (
    AgentDeploymentContext,
    AgentDeploymentResult,
    AgentProcessor,
)
from claude_mpm.services.agents.deployment.refactored_agent_deployment_service import (
    RefactoredAgentDeploymentService,
)
from claude_mpm.services.agents.deployment.results import (
    DeploymentMetrics,
    DeploymentResultBuilder,
)
from claude_mpm.services.agents.deployment.strategies import (
    DeploymentContext,
    DeploymentStrategySelector,
    ProjectAgentDeploymentStrategy,
    SystemAgentDeploymentStrategy,
    UserAgentDeploymentStrategy,
)
from claude_mpm.services.agents.deployment.validation import (
    AgentValidator,
    DeploymentValidator,
    TemplateValidator,
    ValidationResult,
)


class TestDeploymentStrategies:
    """Test deployment strategy pattern."""

    def test_system_strategy_can_handle_default_context():
        """Test that system strategy handles default context."""
        strategy = SystemAgentDeploymentStrategy()
        context = DeploymentContext()

        assert strategy.can_handle(context)
        assert strategy.get_deployment_priority() == 100

    def test_project_strategy_can_handle_project_context():
        """Test that project strategy handles project context."""
        strategy = ProjectAgentDeploymentStrategy()
        context = DeploymentContext(
            working_directory=Path("/test/project"), deployment_mode="project"
        )

        assert strategy.can_handle(context)
        assert strategy.get_deployment_priority() == 50

    def test_user_strategy_can_handle_user_context():
        """Test that user strategy handles user context."""
        strategy = UserAgentDeploymentStrategy()

        with patch.dict("os.environ", {"CLAUDE_MPM_USER_PWD": "/test/user"}):
            context = DeploymentContext()
            assert strategy.can_handle(context)

        assert strategy.get_deployment_priority() == 10

    def test_strategy_selector_selects_correct_strategy():
        """Test that strategy selector chooses the right strategy."""
        selector = DeploymentStrategySelector()

        # Test system strategy selection
        context = DeploymentContext()
        strategy = selector.select_strategy(context)
        assert isinstance(strategy, SystemAgentDeploymentStrategy)

        # Test project strategy selection
        context = DeploymentContext(
            deployment_mode="project", working_directory=Path("/test/project")
        )
        strategy = selector.select_strategy(context)
        assert isinstance(strategy, ProjectAgentDeploymentStrategy)


class TestDeploymentPipeline:
    """Test deployment pipeline components."""

    def test_pipeline_context_initialization():
        """Test pipeline context initialization."""
        context = PipelineContext(
            target_dir=Path("/test"), force_rebuild=True, deployment_mode="project"
        )

        assert context.target_dir == Path("/test")
        assert context.force_rebuild is True
        assert context.deployment_mode == "project"
        assert context.errors == []
        assert context.warnings == []

    def test_pipeline_context_error_handling():
        """Test pipeline context error handling."""
        context = PipelineContext()

        context.add_error("Test error")
        context.add_warning("Test warning")

        assert context.has_errors()
        assert context.get_error_count() == 1
        assert context.get_warning_count() == 1
        assert "Test error" in context.errors
        assert "Test warning" in context.warnings

    def test_configuration_load_step():
        """Test configuration loading step."""
        step = ConfigurationLoadStep()
        context = PipelineContext()

        result = step.execute(context)

        assert result.is_success
        assert context.config is not None
        assert isinstance(context.excluded_agents, list)

    def test_target_directory_setup_step():
        """Test target directory setup step."""
        step = TargetDirectorySetupStep()

        with tmp_path as temp_dir:
            context = PipelineContext(target_dir=Path(temp_dir) / "test_agents")

            result = step.execute(context)

            assert result.is_success
            assert context.actual_target_dir is not None
            assert context.actual_target_dir.exists()

    def test_pipeline_builder_creates_standard_pipeline():
        """Test pipeline builder creates standard pipeline."""
        builder = DeploymentPipelineBuilder()
        steps = builder.create_standard_pipeline()

        assert len(steps) >= 2
        assert any(isinstance(step, ConfigurationLoadStep) for step in steps)
        assert any(isinstance(step, TargetDirectorySetupStep) for step in steps)

    def test_pipeline_executor_runs_steps():
        """Test pipeline executor runs steps successfully."""
        executor = DeploymentPipelineExecutor()
        builder = DeploymentPipelineBuilder()

        steps = builder.create_minimal_pipeline()
        context = PipelineContext()

        results = executor.execute(steps, context)

        assert "pipeline_execution" in results
        assert results["pipeline_execution"]["success"] is True
        assert len(results["pipeline_execution"]["executed_steps"]) >= 2


class TestDeploymentConfig:
    """Test deployment configuration management."""

    def test_deployment_config_defaults():
        """Test deployment config default values."""
        config = DeploymentConfig()

        assert config.excluded_agents == []
        assert config.case_sensitive_exclusion is True
        assert config.deployment_mode == "update"
        assert config.force_rebuild is False
        assert config.use_async is False

    def test_deployment_config_exclusion_logic():
        """Test agent exclusion logic."""
        config = DeploymentConfig(
            excluded_agents=["test-agent", "qa-agent"], case_sensitive_exclusion=True
        )

        assert config.should_exclude_agent("test-agent")
        assert not config.should_exclude_agent("Test-Agent")

        config.case_sensitive_exclusion = False
        assert config.should_exclude_agent("Test-Agent")

    def test_deployment_config_manager_loads_config():
        """Test deployment config manager loads configuration."""
        manager = DeploymentConfigManager()

        config = manager.load_deployment_config()

        assert isinstance(config, DeploymentConfig)
        assert config.environment in ["development", "testing", "production"]

    def test_deployment_config_validation():
        """Test deployment config validation."""
        manager = DeploymentConfigManager()

        # Test invalid deployment mode
        with pytest.raises(ValueError, match="Invalid deployment mode"):
            manager.load_deployment_config(deployment_mode="invalid")

        # Test invalid environment
        with pytest.raises(ValueError, match="Invalid environment"):
            manager.load_deployment_config(environment="invalid")


class TestDeploymentResults:
    """Test deployment results management."""

    def test_deployment_metrics_initialization():
        """Test deployment metrics initialization."""
        metrics = DeploymentMetrics()

        assert metrics.total_agents == 0
        assert metrics.deployed_agents == 0
        assert metrics.errors == []
        assert metrics.warnings == []

    def test_deployment_metrics_agent_tracking():
        """Test deployment metrics agent tracking."""
        metrics = DeploymentMetrics()

        metrics.add_deployed_agent("test-agent", 1.5)
        metrics.add_updated_agent("qa-agent", 2.0)
        metrics.add_skipped_agent("security-agent", "excluded")

        assert metrics.deployed_agents == 1
        assert metrics.updated_agents == 1
        assert metrics.skipped_agents == 1
        assert "test-agent" in metrics.deployed_agent_names
        assert "qa-agent" in metrics.updated_agent_names
        assert "security-agent" in metrics.skipped_agent_names

    def test_deployment_result_builder():
        """Test deployment result builder."""
        builder = DeploymentResultBuilder()

        results = (
            builder.initialize(target_dir=Path("/test"), strategy_name="System")
            .set_total_agents(3)
            .add_deployed_agent("test-agent")
            .add_updated_agent("qa-agent")
            .add_skipped_agent("security-agent")
            .build()
        )

        assert results["target_dir"] == "/test"
        assert results["strategy_used"] == "System"
        assert results["total"] == 3
        assert len(results["deployed"]) == 1
        assert len(results["updated"]) == 1
        assert len(results["skipped"]) == 1
        assert "metrics" in results
        assert "detailed_metrics" in results

    def test_deployment_metrics_success_rate():
        """Test deployment metrics success rate calculation."""
        metrics = DeploymentMetrics()
        metrics.total_agents = 4

        metrics.add_deployed_agent("agent1")
        metrics.add_updated_agent("agent2")
        metrics.add_skipped_agent("agent3")
        metrics.add_failed_agent("agent4", "error")

        # 3 successful (deployed + updated + skipped) out of 4 total = 75%
        assert metrics.get_success_rate() == 75.0


class TestAgentProcessor:
    """Test agent processor components."""

    def test_agent_deployment_context_creation():
        """Test agent deployment context creation."""
        template_file = Path("/test/templates/test-agent.json")
        agents_dir = Path("/test/agents")
        base_agent_data = {"version": "1.0.0"}
        base_agent_version = (1, 0, 0)

        context = AgentDeploymentContext.from_template_file(
            template_file=template_file,
            agents_dir=agents_dir,
            base_agent_data=base_agent_data,
            base_agent_version=base_agent_version,
            force_rebuild=True,
            deployment_mode="project",
        )

        assert context.agent_name == "test-agent"
        assert context.template_file == template_file
        assert context.target_file == agents_dir / "test-agent.md"
        assert context.force_rebuild is True
        assert context.deployment_mode == "project"
        assert context.base_agent_data == base_agent_data
        assert context.base_agent_version == base_agent_version
        assert context.is_project_deployment() is True

    def test_agent_deployment_result_creation():
        """Test agent deployment result creation."""
        agent_name = "test-agent"
        template_file = Path("/test/templates/test-agent.json")
        target_file = Path("/test/agents/test-agent.md")

        # Test deployed result
        result = AgentDeploymentResult.deployed(
            agent_name, template_file, target_file, 150.0
        )
        assert result.status.value == "deployed"
        assert result.deployment_time_ms == 150.0
        assert result.is_successful() is True

        # Test updated result
        result = AgentDeploymentResult.updated(
            agent_name, template_file, target_file, 200.0, "version update"
        )
        assert result.status.value == "updated"
        assert result.was_update is True
        assert result.reason == "version update"
        assert result.is_successful() is True

        # Test migrated result
        result = AgentDeploymentResult.migrated(
            agent_name, template_file, target_file, 300.0, "format migration"
        )
        assert result.status.value == "migrated"
        assert result.was_migration is True
        assert result.reason == "format migration"
        assert result.is_successful() is True

        # Test skipped result
        result = AgentDeploymentResult.skipped(
            agent_name, template_file, target_file, "up-to-date"
        )
        assert result.status.value == "skipped"
        assert result.was_skipped is True
        assert result.reason == "up-to-date"
        assert result.is_successful() is True

        # Test failed result
        result = AgentDeploymentResult.failed(
            agent_name, template_file, target_file, "build error", 50.0
        )
        assert result.status.value == "failed"
        assert result.error_message == "build error"
        assert result.is_successful() is False

    def test_agent_deployment_result_to_dict():
        """Test agent deployment result dictionary conversion."""
        agent_name = "test-agent"
        template_file = Path("/test/templates/test-agent.json")
        target_file = Path("/test/agents/test-agent.md")

        result = AgentDeploymentResult.updated(
            agent_name, template_file, target_file, 150.0, "version update"
        )
        result.metadata = {"custom": "data"}

        result_dict = result.to_dict()

        assert result_dict["name"] == agent_name
        assert result_dict["template"] == str(template_file)
        assert result_dict["target"] == str(target_file)
        assert result_dict["status"] == "updated"
        assert result_dict["deployment_time_ms"] == 150.0
        assert result_dict["reason"] == "version update"
        assert result_dict["metadata"] == {"custom": "data"}

    def test_agent_processor_validation():
        """Test agent processor validation."""
        # Mock dependencies
        template_builder = Mock()
        version_manager = Mock()

        processor = AgentProcessor(template_builder, version_manager)

        with tmp_path as temp_dir:
            # Create a valid template file
            template_file = Path(temp_dir) / "test-agent.json"
            template_file.write_text('{"name": "test-agent"}')

            target_file = Path(temp_dir) / "agents" / "test-agent.md"

            context = AgentDeploymentContext(
                agent_name="test-agent",
                template_file=template_file,
                target_file=target_file,
            )

            # Test validation passes for valid template
            assert processor.validate_agent(context) is True

            # Test validation fails for non-existent template
            context.template_file = Path(temp_dir) / "nonexistent.json"
            assert processor.validate_agent(context) is False


class TestDeploymentValidation:
    """Test deployment validation components."""

    def test_validation_result_creation():
        """Test validation result creation and manipulation."""
        result = ValidationResult(is_valid=True)

        assert result.is_valid is True
        assert result.error_count == 0
        assert result.warning_count == 0
        assert result.has_errors is False
        assert result.has_warnings is False

        # Add errors and warnings
        result.add_error("Test error", field_name="test_field")
        result.add_warning("Test warning", field_name="test_field")

        assert result.is_valid is False
        assert result.error_count == 1
        assert result.warning_count == 1
        assert result.has_errors is True
        assert result.has_warnings is True

        # Test string representation
        str_repr = str(result)
        assert "INVALID" in str_repr
        assert "1 errors" in str_repr
        assert "1 warnings" in str_repr

    def test_validation_result_merge():
        """Test merging validation results."""
        result1 = ValidationResult(is_valid=True)
        result1.add_warning("Warning 1")

        result2 = ValidationResult(is_valid=False)
        result2.add_error("Error 1")

        merged = result1.merge(result2)

        assert merged.is_valid is False
        assert merged.error_count == 1
        assert merged.warning_count == 1
        assert len(merged.issues) == 2

    def test_template_validator():
        """Test template validator."""
        validator = TemplateValidator()

        with tmp_path as temp_dir:
            # Create a valid template file
            template_file = Path(temp_dir) / "test-agent.json"
            template_data = {
                "schema_version": "1.2.0",
                "agent_id": "test-agent",
                "agent_version": "1.0.0",
                "agent_type": "qa",
                "metadata": {
                    "name": "Test Agent",
                    "description": "A test agent for validation",
                    "category": "testing",
                    "tags": ["test", "validation"],
                },
                "capabilities": {"model": "sonnet", "tools": ["Read", "Write"]},
                "instructions": {
                    "system_prompt": "You are a test agent for validation purposes."
                },
            }
            template_file.write_text(json.dumps(template_data, indent=2))

            # Test validation passes for valid template
            result = validator.validate_template_file(template_file)
            assert result.is_valid is True
            assert result.error_count == 0

            # Test validation fails for non-existent file
            nonexistent_file = Path(temp_dir) / "nonexistent.json"
            result = validator.validate_template_file(nonexistent_file)
            assert result.is_valid is False
            assert result.error_count > 0

    def test_agent_validator():
        """Test agent validator."""
        validator = AgentValidator()

        with tmp_path as temp_dir:
            # Create a valid agent file
            agent_file = Path(temp_dir) / "test-agent.md"
            agent_content = """---
name: "Test Agent"
description: "A test agent for validation"
author: "claude-mpm"
version: "1.0.0"
model: "sonnet"
tools: ["Read", "Write"]
---

# Test Agent

This is a test agent for validation purposes.
"""
            agent_file.write_text(agent_content)

            # Test validation passes for valid agent
            result = validator.validate_agent_file(agent_file)
            assert result.is_valid is True
            assert result.error_count == 0

            # Test validation fails for non-existent file
            nonexistent_file = Path(temp_dir) / "nonexistent.md"
            result = validator.validate_agent_file(nonexistent_file)
            assert result.is_valid is False
            assert result.error_count > 0

    def test_deployment_validator():
        """Test deployment validator."""
        validator = DeploymentValidator()

        with tmp_path as temp_dir:
            target_dir = Path(temp_dir) / "agents"
            templates_dir = Path(temp_dir) / "templates"
            templates_dir.mkdir()

            # Create a template file
            template_file = templates_dir / "test-agent.json"
            template_data = {
                "schema_version": "1.2.0",
                "agent_id": "test-agent",
                "agent_version": "1.0.0",
                "agent_type": "qa",
                "metadata": {
                    "name": "Test Agent",
                    "description": "A test agent",
                    "category": "testing",
                    "tags": ["test"],
                },
                "capabilities": {"model": "sonnet", "tools": ["Read"]},
                "instructions": {"system_prompt": "Test prompt"},
            }
            template_file.write_text(json.dumps(template_data, indent=2))

            # Test environment validation
            result = validator.validate_deployment_environment(
                target_dir, templates_dir
            )
            assert result.is_valid is True
            assert target_dir.exists()  # Should be created

            # Test template validation
            template_results = validator.validate_template_files([template_file])
            assert len(template_results) == 1
            assert template_results[str(template_file)].is_valid is True

            # Test validation summary
            summary = validator.get_validation_summary(template_results)
            assert summary["total_files"] == 1
            assert summary["valid_files"] == 1
            assert summary["invalid_files"] == 0
            assert summary["success_rate"] == 100.0


class TestDeploymentFacade:
    """Test deployment facade components."""

    def test_sync_deployment_executor():
        """Test sync deployment executor."""
        # Mock dependencies
        pipeline_builder = Mock()
        pipeline_executor = Mock()

        # Mock pipeline and context
        mock_pipeline = Mock()
        pipeline_builder.build_standard_pipeline.return_value = mock_pipeline

        mock_pipeline_result = Mock()
        mock_pipeline_result.is_successful.return_value = True
        mock_pipeline_result.step_results = []
        mock_pipeline_result.total_execution_time = 1.5
        pipeline_executor.execute_pipeline.return_value = mock_pipeline_result

        executor = SyncDeploymentExecutor(pipeline_builder, pipeline_executor)

        # Test executor properties
        assert executor.is_available() is True
        assert executor.get_executor_name() == "sync"

        # Test performance characteristics
        perf = executor.get_performance_characteristics()
        assert perf["name"] == "sync"
        assert perf["available"] is True
        assert perf["estimated_speedup"] == 1.0

    def test_async_deployment_executor():
        """Test async deployment executor."""
        executor = AsyncDeploymentExecutor()

        # Test executor properties
        assert executor.get_executor_name() == "async"

        # Test performance characteristics
        perf = executor.get_performance_characteristics()
        assert perf["name"] == "async"
        assert perf["estimated_speedup"] == 1.6
        assert perf["memory_usage"] == "higher"

    def test_deployment_facade_executor_selection():
        """Test deployment facade executor selection."""
        # Mock dependencies
        pipeline_builder = Mock()
        pipeline_executor = Mock()

        facade = DeploymentFacade(pipeline_builder, pipeline_executor)

        # Test sync executor selection
        sync_executor = facade._select_executor(
            use_async=False, preferred_executor=None
        )
        assert sync_executor.get_executor_name() == "sync"

        # Test preferred executor selection
        sync_executor = facade._select_executor(
            use_async=True, preferred_executor="sync"
        )
        assert sync_executor.get_executor_name() == "sync"

        # Test async selection (if available)
        if facade.async_executor.is_available():
            async_executor = facade._select_executor(
                use_async=True, preferred_executor=None
            )
            assert async_executor.get_executor_name() == "async"

    def test_deployment_facade_available_executors():
        """Test getting available executors."""
        # Mock dependencies
        pipeline_builder = Mock()
        pipeline_executor = Mock()

        facade = DeploymentFacade(pipeline_builder, pipeline_executor)

        available = facade.get_available_executors()
        assert len(available) >= 1  # At least sync should be available

        # Check that sync is always available
        sync_available = any(exec_info["name"] == "sync" for exec_info in available)
        assert sync_available is True

    def test_deployment_facade_recommendations():
        """Test executor recommendations."""
        # Mock dependencies
        pipeline_builder = Mock()
        pipeline_executor = Mock()

        facade = DeploymentFacade(pipeline_builder, pipeline_executor)

        # Small deployment should recommend sync
        recommendation = facade.get_recommended_executor(agent_count=2)
        assert recommendation == "sync"

        # Large deployment should recommend async if available, otherwise sync
        recommendation = facade.get_recommended_executor(agent_count=10)
        if facade.async_executor.is_available():
            assert recommendation == "async"
        else:
            assert recommendation == "sync"


class TestInterfaceCompliance:
    """Test interface compliance components."""

    def test_interface_adapter():
        """Test interface adapter functionality."""
        # Mock deployment service
        mock_service = Mock()
        mock_service.deploy_agents.return_value = {
            "success": True,
            "deployed": ["agent1"],
            "updated": [],
            "migrated": [],
            "skipped": [],
            "errors": [],
        }
        mock_service.validate_agent.return_value = (True, [])
        mock_service.get_deployment_status.return_value = {"status": "ready"}

        # Test adapter
        adapter = AgentDeploymentInterfaceAdapter(mock_service)

        # Test interface compliance
        assert isinstance(adapter, AgentDeploymentInterface)

        # Test deploy_agents method
        result = adapter.deploy_agents(force=True, include_all=False)
        assert result["success"] is True
        assert "interface_version" in result
        assert result["adapter_used"] is True

        # Verify the underlying service was called correctly
        mock_service.deploy_agents.assert_called_once()
        call_args = mock_service.deploy_agents.call_args
        assert call_args[1]["force_rebuild"] is True
        assert call_args[1]["deployment_mode"] == "update"

        # Test validate_agent method
        is_valid, errors = adapter.validate_agent(Path("/test/agent.md"))
        assert is_valid is True
        assert errors == []

        # Test get_deployment_status method
        status = adapter.get_deployment_status()
        assert status["status"] == "ready"
        assert "interface_version" in status
        assert status["adapter_used"] is True

    def test_refactored_service_interface_compliance():
        """Test that refactored service implements the interface correctly."""
        with tmp_path as temp_dir:
            working_dir = Path(temp_dir)
            templates_dir = working_dir / "agents"
            templates_dir.mkdir()
            base_agent_path = working_dir / "base_agent.md"
            base_agent_path.write_text("# Base Agent")

            # Create refactored service
            service = RefactoredAgentDeploymentService(
                templates_dir=templates_dir,
                base_agent_path=base_agent_path,
                working_directory=working_dir,
            )

            # Test interface compliance
            assert isinstance(service, AgentDeploymentInterface)

            # Test deploy_agents method
            result = service.deploy_agents(force=False, include_all=False)
            assert isinstance(result, dict)
            assert "success" in result
            assert "deployed" in result
            assert "updated" in result
            assert "errors" in result

            # Test validate_agent method (with non-existent file)
            is_valid, errors = service.validate_agent(Path("/nonexistent/agent.md"))
            assert is_valid is False
            assert len(errors) > 0

            # Test clean_deployment method
            cleanup_result = service.clean_deployment(preserve_user_agents=True)
            assert isinstance(cleanup_result, bool)

            # Test get_deployment_status method
            status = service.get_deployment_status()
            assert isinstance(status, dict)
            assert "service_version" in status
            assert status["service_version"] == "refactored-1.0.0"

    def test_interface_method_signatures():
        """Test that interface method signatures are correct."""
        # This test ensures the interface methods have the expected signatures

        # Test AgentDeploymentInterface methods exist and have correct signatures
        interface_methods = [
            "deploy_agents",
            "validate_agent",
            "clean_deployment",
            "get_deployment_status",
        ]

        for method_name in interface_methods:
            assert hasattr(AgentDeploymentInterface, method_name)
            method = getattr(AgentDeploymentInterface, method_name)
            assert callable(method)

        # Test that our implementations have the same methods
        with tmp_path as temp_dir:
            service = RefactoredAgentDeploymentService(working_directory=Path(temp_dir))

            for method_name in interface_methods:
                assert hasattr(service, method_name)
                method = getattr(service, method_name)
                assert callable(method)
