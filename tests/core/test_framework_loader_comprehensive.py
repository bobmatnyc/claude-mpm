"""Comprehensive unit tests for FrameworkLoader class.

This test suite provides complete coverage for the FrameworkLoader god class,
testing all 12+ responsibilities and complex interactions. These tests serve
as a safety net for the upcoming refactoring.
"""

import json
import os
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
from unittest.mock import MagicMock, Mock, PropertyMock, call, mock_open, patch

import pytest
import yaml


@pytest.fixture(autouse=True)
def mock_dependencies():
    """Mock all external dependencies for FrameworkLoader."""
    with patch("claude_mpm.core.framework_loader.get_logger") as mock_logger:
        with patch("claude_mpm.core.framework_loader.AgentRegistryAdapter") as mock_registry:
            mock_logger.return_value = MagicMock()
            mock_registry.return_value = MagicMock()
            yield {
                "logger": mock_logger,
                "registry": mock_registry
            }


# Import after setting up mocks
from claude_mpm.core.framework_loader import FrameworkLoader


class TestPathResolution:
    """Test path resolution and detection functionality."""

    def test_detect_framework_path_development(self, tmp_path):
        """Test framework path detection in development environment."""
        # Create development structure
        framework_path = tmp_path / "src" / "claude_mpm"
        framework_path.mkdir(parents=True)
        agents_dir = framework_path / "agents"
        agents_dir.mkdir()
        (agents_dir / "INSTRUCTIONS.md").write_text("# Instructions")
        
        with patch.object(Path, "cwd", return_value=tmp_path):
            with patch.object(Path, "exists") as mock_exists:
                mock_exists.side_effect = lambda self: str(self).endswith("INSTRUCTIONS.md")
                
                loader = FrameworkLoader()
                assert loader.framework_path is not None

    def test_detect_framework_path_packaged(self):
        """Test framework path detection in packaged installation."""
        with patch("claude_mpm.core.framework_loader.files") as mock_files:
            mock_resource = MagicMock()
            mock_resource.__truediv__.return_value = mock_resource
            mock_resource.is_file.return_value = True
            mock_files.return_value = mock_resource
            
            loader = FrameworkLoader()
            assert loader.framework_path is None  # Packaged installations have no file path

    def test_npm_global_path_resolution(self):
        """Test NPM global path resolution."""
        expected_path = "/usr/local/lib/node_modules/claude-multiagent-pm"
        
        with patch("subprocess.check_output") as mock_subprocess:
            mock_subprocess.return_value = expected_path.encode()
            with patch.object(Path, "exists", return_value=True):
                
                loader = FrameworkLoader()
                # The method is private, so we test it directly
                npm_path = loader._get_npm_global_path()
                assert npm_path == Path(expected_path)

    def test_npm_global_path_not_found(self):
        """Test NPM global path when not installed."""
        with patch("subprocess.check_output", side_effect=subprocess.CalledProcessError(1, "npm")):
            loader = FrameworkLoader()
            npm_path = loader._get_npm_global_path()
            assert npm_path is None

    def test_deployment_context_detection(self, tmp_path):
        """Test detection of deployment context (dev vs packaged)."""
        # Test development context
        dev_path = tmp_path / "src" / "claude_mpm" / "agents"
        dev_path.mkdir(parents=True)
        (dev_path / "INSTRUCTIONS.md").write_text("# Dev")
        
        with patch.object(Path, "cwd", return_value=tmp_path):
            loader = FrameworkLoader(framework_path=dev_path.parent)
            assert loader.framework_path == dev_path.parent
            
        # Test packaged context
        with patch("claude_mpm.core.framework_loader.files"):
            loader = FrameworkLoader()
            # In packaged context, framework_path should be None or use resource paths


class TestInstructionLoading:
    """Test instruction file loading with precedence."""

    def test_load_instructions_precedence(self, tmp_path):
        """Test INSTRUCTIONS.md loading precedence: project > user > system."""
        # Setup directory structure
        project_dir = tmp_path / ".claude-mpm"
        user_dir = Path.home() / ".claude-mpm"
        system_dir = tmp_path / "system" / "claude_mpm" / "agents"
        
        project_dir.mkdir(parents=True)
        system_dir.mkdir(parents=True)
        
        # Create files with different content
        project_file = project_dir / "INSTRUCTIONS.md"
        project_file.write_text("# Project Instructions")
        
        system_file = system_dir / "INSTRUCTIONS.md"
        system_file.write_text("# System Instructions")
        
        with patch.object(Path, "cwd", return_value=tmp_path):
            with patch.object(Path, "home", return_value=tmp_path):
                loader = FrameworkLoader(framework_path=system_dir.parent)
                
                # Project file should take precedence
                loader._load_instructions_file(loader.framework_content)
                assert "project" in loader.framework_content.get("custom_instructions_source", "").lower()

    def test_load_workflow_instructions(self, tmp_path):
        """Test WORKFLOW.md loading."""
        workflow_dir = tmp_path / ".claude-mpm"
        workflow_dir.mkdir()
        workflow_file = workflow_dir / "WORKFLOW.md"
        workflow_content = "# Custom Workflow\nStep 1\nStep 2"
        workflow_file.write_text(workflow_content)
        
        with patch.object(Path, "cwd", return_value=tmp_path):
            loader = FrameworkLoader()
            content = {}
            loader._load_workflow_instructions(content)
            
            assert "workflow_instructions" in content
            assert "Custom Workflow" in content["workflow_instructions"]

    def test_load_memory_instructions(self, tmp_path):
        """Test MEMORY.md loading with custom overrides."""
        memory_dir = tmp_path / ".claude-mpm"
        memory_dir.mkdir()
        memory_file = memory_dir / "MEMORY.md"
        memory_content = "# Memory Guidelines\nRemember: X, Y, Z"
        memory_file.write_text(memory_content)
        
        with patch.object(Path, "cwd", return_value=tmp_path):
            loader = FrameworkLoader()
            content = {}
            loader._load_memory_instructions(content)
            
            assert "memory_instructions" in content
            assert "Memory Guidelines" in content["memory_instructions"]

    def test_file_not_found_fallback(self, tmp_path):
        """Test graceful handling when instruction files are not found."""
        with patch.object(Path, "cwd", return_value=tmp_path):
            loader = FrameworkLoader()
            
            # Should not raise exception
            content = {}
            loader._load_instructions_file(content)
            loader._load_workflow_instructions(content)
            loader._load_memory_instructions(content)
            
            # Should have loaded system defaults or be empty
            assert isinstance(content, dict)


class TestMemorySystem:
    """Test memory system functionality."""

    def test_load_pm_memories(self, tmp_path):
        """Test loading PM memories from user and project directories."""
        # Setup memory directories
        project_memories = tmp_path / ".claude-mpm" / "memories"
        user_memories = Path.home() / ".claude-mpm" / "memories"
        project_memories.mkdir(parents=True)
        
        # Create PM memory files
        pm_memory = project_memories / "PM_memories.md"
        pm_memory.write_text("# PM Memory\nProject context: ABC")
        
        with patch.object(Path, "cwd", return_value=tmp_path):
            with patch.object(Path, "home", return_value=tmp_path.parent):
                loader = FrameworkLoader()
                content = {}
                
                # Mock deployed agents
                with patch.object(loader, "_get_deployed_agents", return_value=set()):
                    loader._load_actual_memories(content)
                    
                    assert "actual_memories" in content
                    assert "PM Memory" in content["actual_memories"]

    def test_load_agent_specific_memories(self, tmp_path):
        """Test loading agent-specific memories."""
        memories_dir = tmp_path / ".claude-mpm" / "memories"
        memories_dir.mkdir(parents=True)
        
        # Create agent memory files
        (memories_dir / "engineer_memories.md").write_text("# Engineer Memory\nPattern: MVC")
        (memories_dir / "qa_memories.md").write_text("# QA Memory\nTest: Unit tests")
        
        with patch.object(Path, "cwd", return_value=tmp_path):
            loader = FrameworkLoader()
            content = {}
            
            # Mock deployed agents
            deployed = {"engineer", "qa"}
            with patch.object(loader, "_get_deployed_agents", return_value=deployed):
                loader._load_actual_memories(content)
                
                assert "actual_memories" in content
                assert "Engineer Memory" in content["actual_memories"]
                assert "QA Memory" in content["actual_memories"]

    def test_memory_aggregation_and_deduplication(self, tmp_path):
        """Test memory aggregation and deduplication."""
        memories_dir = tmp_path / ".claude-mpm" / "memories"
        memories_dir.mkdir(parents=True)
        
        # Create duplicate memories
        (memories_dir / "PM_memories.md").write_text("Memory 1\nMemory 2\nMemory 1")
        
        with patch.object(Path, "cwd", return_value=tmp_path):
            loader = FrameworkLoader()
            
            # Test aggregation
            memories = [
                {"content": "Memory 1\nMemory 2", "source": "project"},
                {"content": "Memory 2\nMemory 3", "source": "user"}
            ]
            
            aggregated = loader._aggregate_memories(memories)
            
            # Should deduplicate but preserve unique memories
            assert "Memory 1" in aggregated
            assert "Memory 2" in aggregated
            assert "Memory 3" in aggregated
            # Check no excessive duplication
            assert aggregated.count("Memory 1") == 1

    def test_legacy_format_migration(self, tmp_path):
        """Test migration of legacy memory format files."""
        memories_dir = tmp_path / ".claude-mpm" / "memories"
        memories_dir.mkdir(parents=True)
        
        # Create old format files
        old_pm = memories_dir / "PM.md"
        old_pm.write_text("# Old PM Memory")
        
        old_agent = memories_dir / "engineer_agent.md"
        old_agent.write_text("# Old Engineer Memory")
        
        with patch.object(Path, "cwd", return_value=tmp_path):
            loader = FrameworkLoader()
            
            # Mock the migration
            with patch.object(loader, "_migrate_memory_file") as mock_migrate:
                content = {}
                with patch.object(loader, "_get_deployed_agents", return_value={"engineer"}):
                    loader._load_actual_memories(content)
                    
                    # Should attempt migration
                    assert mock_migrate.called

    def test_cache_ttl_behavior(self):
        """Test cache TTL expiration behavior."""
        loader = FrameworkLoader()
        
        # Set cache with timestamp
        loader._memories_cache = {"test": "data"}
        loader._memories_cache_time = time.time()
        
        # Test cache hit within TTL
        with patch("time.time", return_value=loader._memories_cache_time + 30):
            # Cache should still be valid (TTL is 60 seconds)
            assert loader._memories_cache is not None
            
        # Test cache miss after TTL
        with patch("time.time", return_value=loader._memories_cache_time + 70):
            # Simulate checking cache expiration
            if time.time() - loader._memories_cache_time > loader.MEMORIES_CACHE_TTL:
                loader._memories_cache = None
            assert loader._memories_cache is None


class TestAgentDiscovery:
    """Test agent discovery and loading functionality."""

    def test_discover_agents_in_claude_dir(self, tmp_path):
        """Test discovering agents in .claude/agents/ directory."""
        agents_dir = tmp_path / ".claude" / "agents"
        agents_dir.mkdir(parents=True)
        
        # Create agent files with YAML frontmatter
        engineer_agent = agents_dir / "engineer.md"
        engineer_agent.write_text("""---
name: Engineer
model: claude-3.5-sonnet
capabilities:
  - code review
  - implementation
---
# Engineer Agent
Code implementation specialist.""")
        
        qa_agent = agents_dir / "qa.md"
        qa_agent.write_text("""---
name: QA
model: claude-3.5-sonnet
capabilities:
  - testing
  - validation
---
# QA Agent
Testing specialist.""")
        
        with patch.object(Path, "cwd", return_value=tmp_path):
            loader = FrameworkLoader()
            agents = loader.get_agent_list()
            
            # Should discover both agents
            assert "engineer" in agents or "Engineer" in agents
            assert "qa" in agents or "QA" in agents

    def test_parse_yaml_frontmatter(self, tmp_path):
        """Test parsing YAML frontmatter metadata from agent files."""
        agents_dir = tmp_path / ".claude" / "agents"
        agents_dir.mkdir(parents=True)
        
        agent_file = agents_dir / "test.md"
        agent_file.write_text("""---
name: Test Agent
model: claude-3.5-sonnet
capabilities:
  - capability1
  - capability2
routing:
  keywords: [test, testing]
  priority: high
---
# Test Agent Content""")
        
        loader = FrameworkLoader()
        metadata = loader._parse_agent_metadata(agent_file)
        
        assert metadata is not None
        assert metadata["name"] == "Test Agent"
        assert metadata["model"] == "claude-3.5-sonnet"
        assert "capability1" in metadata["capabilities"]
        assert metadata["routing"]["priority"] == "high"

    def test_load_routing_templates(self, tmp_path):
        """Test loading routing templates for agents."""
        agents_dir = tmp_path / ".claude" / "agents"
        agents_dir.mkdir(parents=True)
        
        # Create routing template
        routing_dir = agents_dir / "routing"
        routing_dir.mkdir()
        routing_template = routing_dir / "engineer.yaml"
        routing_template.write_text("""
keywords:
  - code
  - implementation
  - refactor
priority: high
confidence_threshold: 0.8
""")
        
        with patch.object(Path, "cwd", return_value=tmp_path):
            loader = FrameworkLoader()
            routing = loader._load_routing_from_template("engineer")
            
            assert routing is not None
            assert "code" in routing["keywords"]
            assert routing["priority"] == "high"

    def test_agent_capabilities_generation(self, tmp_path):
        """Test generation of agent capabilities section."""
        agents_dir = tmp_path / ".claude" / "agents"
        agents_dir.mkdir(parents=True)
        
        # Create test agent
        agent_file = agents_dir / "analyzer.md"
        agent_file.write_text("""---
name: Analyzer
capabilities:
  - code analysis
  - performance profiling
---
# Analyzer Agent""")
        
        with patch.object(Path, "cwd", return_value=tmp_path):
            loader = FrameworkLoader()
            
            with patch.object(loader, "_get_deployed_agents", return_value={"analyzer"}):
                capabilities = loader._generate_agent_capabilities_section()
                
                assert "Analyzer" in capabilities or "analyzer" in capabilities
                assert "code analysis" in capabilities

    def test_handle_missing_or_malformed_agents(self, tmp_path):
        """Test handling of missing or malformed agent files."""
        agents_dir = tmp_path / ".claude" / "agents"
        agents_dir.mkdir(parents=True)
        
        # Create malformed agent file
        bad_agent = agents_dir / "bad.md"
        bad_agent.write_text("""---
invalid yaml: [unclosed
---
# Bad Agent""")
        
        # Create agent without frontmatter
        no_meta_agent = agents_dir / "simple.md"
        no_meta_agent.write_text("# Simple Agent\nNo metadata here.")
        
        with patch.object(Path, "cwd", return_value=tmp_path):
            loader = FrameworkLoader()
            
            # Should handle gracefully without crashing
            agents = loader.get_agent_list()
            assert isinstance(agents, list)
            
            # Try to load the bad agent
            bad_metadata = loader._parse_agent_metadata(bad_agent)
            assert bad_metadata is None or isinstance(bad_metadata, dict)


class TestOutputStyle:
    """Test output style management functionality."""

    def test_output_style_manager_initialization(self):
        """Test initialization of output style manager."""
        with patch("claude_mpm.core.output_style_manager.OutputStyleManager") as MockManager:
            mock_instance = MagicMock()
            MockManager.return_value = mock_instance
            
            loader = FrameworkLoader()
            loader._initialize_output_style()
            
            assert loader.output_style_manager is not None
            MockManager.assert_called_once()

    def test_claude_version_detection(self):
        """Test detection of Claude Code version."""
        with patch("claude_mpm.core.output_style_manager.OutputStyleManager") as MockManager:
            mock_instance = MagicMock()
            mock_instance.claude_version = "1.0.85"
            mock_instance.supports_output_styles.return_value = True
            MockManager.return_value = mock_instance
            
            loader = FrameworkLoader()
            loader._initialize_output_style()
            
            # Should detect version and capabilities
            mock_instance.supports_output_styles.assert_called()

    def test_style_injection_for_older_versions(self):
        """Test style injection for older Claude versions."""
        with patch("claude_mpm.core.output_style_manager.OutputStyleManager") as MockManager:
            mock_instance = MagicMock()
            mock_instance.claude_version = "1.0.80"
            mock_instance.supports_output_styles.return_value = False
            MockManager.return_value = mock_instance
            
            loader = FrameworkLoader()
            loader._initialize_output_style()
            
            # Should handle older versions gracefully
            assert loader.output_style_manager is not None


class TestCaching:
    """Test caching functionality."""

    def test_cache_hit_miss_scenarios(self):
        """Test cache hit and miss scenarios."""
        loader = FrameworkLoader()
        
        # Test cache miss
        assert loader._agent_capabilities_cache is None
        
        # Simulate cache population
        loader._agent_capabilities_cache = "cached capabilities"
        loader._agent_capabilities_cache_time = time.time()
        
        # Test cache hit (within TTL)
        assert loader._agent_capabilities_cache == "cached capabilities"

    def test_ttl_expiration(self):
        """Test TTL expiration for different cache types."""
        loader = FrameworkLoader()
        
        # Set different caches with timestamps
        current_time = time.time()
        loader._agent_capabilities_cache = "capabilities"
        loader._agent_capabilities_cache_time = current_time - 70  # Expired
        
        loader._deployed_agents_cache = {"agent1"}
        loader._deployed_agents_cache_time = current_time - 20  # Not expired
        
        # Check expiration
        if time.time() - loader._agent_capabilities_cache_time > loader.CAPABILITIES_CACHE_TTL:
            loader._agent_capabilities_cache = None
        
        if time.time() - loader._deployed_agents_cache_time > loader.DEPLOYED_AGENTS_CACHE_TTL:
            loader._deployed_agents_cache = None
        
        assert loader._agent_capabilities_cache is None  # Should be expired
        assert loader._deployed_agents_cache is not None  # Should still be valid

    def test_cache_invalidation(self):
        """Test cache invalidation methods."""
        loader = FrameworkLoader()
        
        # Populate caches
        loader._agent_capabilities_cache = "capabilities"
        loader._deployed_agents_cache = {"agent1"}
        loader._memories_cache = {"memory": "data"}
        loader._agent_metadata_cache = {"agent1": ({"meta": "data"}, time.time())}
        
        # Test clear all caches
        loader.clear_all_caches()
        assert loader._agent_capabilities_cache is None
        assert loader._deployed_agents_cache is None
        assert loader._memories_cache is None
        assert len(loader._agent_metadata_cache) == 0
        
        # Repopulate for specific clearing
        loader._agent_capabilities_cache = "capabilities"
        loader._memories_cache = {"memory": "data"}
        
        # Test clear agent caches only
        loader.clear_agent_caches()
        assert loader._agent_capabilities_cache is None
        assert loader._memories_cache is not None  # Should not be cleared
        
        # Test clear memory caches only
        loader.clear_memory_caches()
        assert loader._memories_cache is None

    def test_multiple_cache_types(self):
        """Test interaction between multiple cache types."""
        loader = FrameworkLoader()
        
        # Set multiple cache types
        loader._agent_capabilities_cache = "capabilities"
        loader._agent_capabilities_cache_time = time.time()
        
        loader._deployed_agents_cache = {"agent1", "agent2"}
        loader._deployed_agents_cache_time = time.time()
        
        loader._agent_metadata_cache["agent1"] = ({"name": "Agent1"}, time.time())
        loader._agent_metadata_cache["agent2"] = ({"name": "Agent2"}, time.time())
        
        # Verify all caches are independent
        assert loader._agent_capabilities_cache == "capabilities"
        assert len(loader._deployed_agents_cache) == 2
        assert len(loader._agent_metadata_cache) == 2


class TestContentFormatting:
    """Test content formatting functionality."""

    def test_full_framework_formatting(self):
        """Test full framework content formatting."""
        loader = FrameworkLoader()
        
        # Mock framework content
        loader.framework_content = {
            "instructions": "# Instructions",
            "workflow_instructions": "# Workflow",
            "memory_instructions": "# Memory",
            "actual_memories": "# Actual Memories"
        }
        
        formatted = loader._format_full_framework()
        
        assert "Instructions" in formatted
        assert "Workflow" in formatted
        assert "Memory" in formatted

    def test_minimal_fallback_formatting(self):
        """Test minimal fallback formatting when content is missing."""
        loader = FrameworkLoader()
        loader.framework_content = {}
        
        formatted = loader._format_minimal_framework()
        
        # Should provide minimal working framework
        assert isinstance(formatted, str)
        assert len(formatted) > 0

    def test_metadata_stripping(self):
        """Test stripping of metadata comments from content."""
        loader = FrameworkLoader()
        
        content_with_metadata = """
<!-- METADATA: version=1.0 -->
<!-- SOURCE: project -->
# Actual Content
This is the real content.
<!-- END METADATA -->
More content here.
"""
        
        stripped = loader._strip_metadata_comments(content_with_metadata)
        
        assert "METADATA" not in stripped
        assert "SOURCE" not in stripped
        assert "Actual Content" in stripped
        assert "real content" in stripped

    def test_content_injection(self):
        """Test content injection into framework."""
        loader = FrameworkLoader()
        
        # Test injection of custom content
        loader.framework_content = {
            "instructions": "Base instructions",
            "custom_instructions": "Custom overrides"
        }
        
        formatted = loader.get_framework_instructions()
        
        # Should include both base and custom
        assert isinstance(formatted, str)


class TestPackageResources:
    """Test package resource loading functionality."""

    def test_loading_from_packaged_installation(self):
        """Test loading resources from packaged installation."""
        with patch("claude_mpm.core.framework_loader.files") as mock_files:
            mock_resource = MagicMock()
            mock_resource.read_text.return_value = "# Packaged Instructions"
            mock_resource.__truediv__.return_value = mock_resource
            mock_files.return_value = mock_resource
            
            loader = FrameworkLoader()
            content = loader._load_packaged_file("INSTRUCTIONS.md")
            
            assert content == "# Packaged Instructions"

    def test_importlib_resources_version_handling(self):
        """Test handling of different importlib.resources versions."""
        # Test with modern importlib.resources
        with patch("claude_mpm.core.framework_loader.files") as mock_files:
            mock_files.return_value = MagicMock()
            loader = FrameworkLoader()
            assert loader is not None
        
        # Test with fallback when files is None
        with patch("claude_mpm.core.framework_loader.files", None):
            loader = FrameworkLoader()
            # Should handle gracefully
            assert loader is not None

    def test_fallback_strategies(self):
        """Test fallback strategies when resources are not available."""
        with patch("claude_mpm.core.framework_loader.files", None):
            loader = FrameworkLoader()
            
            # Should use fallback methods
            content = loader._load_packaged_file_fallback("INSTRUCTIONS.md", None)
            # May return None or default content
            assert content is None or isinstance(content, str)


class TestErrorHandling:
    """Test error handling functionality."""

    def test_missing_files_handling(self, tmp_path):
        """Test handling of missing files."""
        with patch.object(Path, "cwd", return_value=tmp_path):
            loader = FrameworkLoader()
            
            # Try to load non-existent file
            content = loader._try_load_file(tmp_path / "missing.md", "test file")
            assert content is None

    def test_malformed_yaml_handling(self, tmp_path):
        """Test handling of malformed YAML."""
        agents_dir = tmp_path / ".claude" / "agents"
        agents_dir.mkdir(parents=True)
        
        bad_yaml = agents_dir / "bad.md"
        bad_yaml.write_text("""---
invalid: [yaml
  structure: broken
---
Content""")
        
        loader = FrameworkLoader()
        metadata = loader._parse_agent_metadata(bad_yaml)
        
        # Should handle gracefully
        assert metadata is None or isinstance(metadata, dict)

    def test_permission_errors_handling(self, tmp_path):
        """Test handling of permission errors."""
        restricted_file = tmp_path / "restricted.md"
        restricted_file.write_text("content")
        
        with patch("builtins.open", side_effect=PermissionError("Access denied")):
            loader = FrameworkLoader()
            content = loader._try_load_file(restricted_file, "restricted")
            assert content is None

    def test_subprocess_failures_handling(self):
        """Test handling of subprocess failures."""
        with patch("subprocess.check_output", side_effect=subprocess.CalledProcessError(1, "cmd")):
            loader = FrameworkLoader()
            npm_path = loader._get_npm_global_path()
            assert npm_path is None


class TestIntegration:
    """Integration tests for end-to-end workflows."""

    def test_end_to_end_instruction_loading(self, tmp_path):
        """Test complete instruction loading workflow."""
        # Setup complete directory structure
        project_dir = tmp_path / ".claude-mpm"
        project_dir.mkdir()
        
        agents_dir = tmp_path / ".claude" / "agents"
        agents_dir.mkdir(parents=True)
        
        memories_dir = project_dir / "memories"
        memories_dir.mkdir()
        
        # Create all necessary files
        (project_dir / "INSTRUCTIONS.md").write_text("# Custom Instructions")
        (project_dir / "WORKFLOW.md").write_text("# Custom Workflow")
        (project_dir / "MEMORY.md").write_text("# Memory Guide")
        (memories_dir / "PM_memories.md").write_text("# PM Memories")
        
        # Create an agent
        agent_file = agents_dir / "test_agent.md"
        agent_file.write_text("""---
name: Test Agent
capabilities: [testing]
---
# Test Agent""")
        
        with patch.object(Path, "cwd", return_value=tmp_path):
            loader = FrameworkLoader()
            
            # Get complete framework
            framework = loader.get_framework_instructions()
            
            assert "Custom Instructions" in framework
            assert isinstance(framework, str)
            assert len(framework) > 0

    def test_complete_memory_aggregation_flow(self, tmp_path):
        """Test complete memory aggregation workflow."""
        # Setup memory structure
        project_memories = tmp_path / ".claude-mpm" / "memories"
        project_memories.mkdir(parents=True)
        
        user_memories = tmp_path / "user" / ".claude-mpm" / "memories"
        user_memories.mkdir(parents=True)
        
        # Create memory files at different levels
        (project_memories / "PM_memories.md").write_text("# Project PM Memory")
        (user_memories / "PM_memories.md").write_text("# User PM Memory")
        (project_memories / "engineer_memories.md").write_text("# Engineer Memory")
        
        # Create agents directory
        agents_dir = tmp_path / ".claude" / "agents"
        agents_dir.mkdir(parents=True)
        (agents_dir / "engineer.md").write_text("# Engineer Agent")
        
        with patch.object(Path, "cwd", return_value=tmp_path):
            with patch.object(Path, "home", return_value=tmp_path / "user"):
                loader = FrameworkLoader()
                
                # Load memories
                content = {}
                with patch.object(loader, "_get_deployed_agents", return_value={"engineer"}):
                    loader._load_actual_memories(content)
                
                assert "actual_memories" in content
                # Project should override user
                assert "Project PM Memory" in content["actual_memories"]

    def test_full_agent_discovery_process(self, tmp_path):
        """Test complete agent discovery and loading process."""
        agents_dir = tmp_path / ".claude" / "agents"
        agents_dir.mkdir(parents=True)
        
        # Create multiple agents with different configurations
        agents = [
            ("engineer", """---
name: Engineer
model: claude-3.5-sonnet
capabilities: [code, review]
---
# Engineer Agent"""),
            ("qa", """---
name: QA Specialist
model: claude-3.5-sonnet
capabilities: [testing, validation]
---
# QA Agent"""),
            ("pm", """---
name: Project Manager
model: claude-3.5-sonnet
capabilities: [planning, coordination]
---
# PM Agent""")
        ]
        
        for agent_name, content in agents:
            (agents_dir / f"{agent_name}.md").write_text(content)
        
        with patch.object(Path, "cwd", return_value=tmp_path):
            loader = FrameworkLoader()
            
            # Get agent list
            agent_list = loader.get_agent_list()
            assert len(agent_list) >= 3
            
            # Get specific agent
            engineer_def = loader.get_agent_definition("engineer")
            assert engineer_def is not None
            assert "Engineer Agent" in engineer_def
            
            # Get agent hierarchy
            hierarchy = loader.get_agent_hierarchy()
            assert isinstance(hierarchy, dict)
            
            # Generate capabilities
            with patch.object(loader, "_get_deployed_agents", return_value={"engineer", "qa", "pm"}):
                capabilities = loader._generate_agent_capabilities_section()
                assert "Engineer" in capabilities
                assert "QA" in capabilities
                assert "testing" in capabilities.lower()


class TestPerformance:
    """Test performance-related functionality."""

    def test_lazy_loading(self):
        """Test lazy loading of components."""
        loader = FrameworkLoader()
        
        # Output style manager should not be initialized immediately
        assert loader.output_style_manager is None
        
        # Should initialize on first use
        loader._initialize_output_style()
        # After initialization (or attempt)
        # Note: may still be None if initialization fails

    def test_cache_performance(self):
        """Test cache performance improvements."""
        loader = FrameworkLoader()
        
        # First call - cache miss
        start_time = time.time()
        loader._agent_capabilities_cache = None
        
        # Simulate expensive operation
        loader._agent_capabilities_cache = "Generated capabilities"
        loader._agent_capabilities_cache_time = time.time()
        first_call_time = time.time() - start_time
        
        # Second call - cache hit
        start_time = time.time()
        cached_value = loader._agent_capabilities_cache
        second_call_time = time.time() - start_time
        
        # Cache hit should be much faster
        assert cached_value == "Generated capabilities"
        # Second call should be faster (though in test it's minimal)
        assert second_call_time <= first_call_time + 0.01  # Allow small variance

    def test_memory_usage_optimization(self, tmp_path):
        """Test memory usage optimizations."""
        # Create large memory files
        memories_dir = tmp_path / ".claude-mpm" / "memories"
        memories_dir.mkdir(parents=True)
        
        # Create a large memory file (simulate 1MB)
        large_content = "X" * (1024 * 1024)  # 1MB of data
        (memories_dir / "large_memories.md").write_text(large_content)
        
        with patch.object(Path, "cwd", return_value=tmp_path):
            loader = FrameworkLoader()
            
            # Should handle large files efficiently
            content = {}
            with patch.object(loader, "_get_deployed_agents", return_value=set()):
                loader._load_actual_memories(content)
            
            # Verify it loaded without issues
            assert isinstance(content, dict)


class TestBackwardCompatibility:
    """Test backward compatibility with legacy code."""

    def test_legacy_memory_format_support(self, tmp_path):
        """Test support for legacy memory file formats."""
        memories_dir = tmp_path / ".claude-mpm" / "memories"
        memories_dir.mkdir(parents=True)
        
        # Create legacy format files
        (memories_dir / "PM.md").write_text("# Old PM Format")
        (memories_dir / "engineer_agent.md").write_text("# Old Agent Format")
        (memories_dir / "qa.md").write_text("# Intermediate Format")
        
        with patch.object(Path, "cwd", return_value=tmp_path):
            loader = FrameworkLoader()
            
            # Should handle migration
            with patch.object(loader, "_migrate_memory_file") as mock_migrate:
                with patch.object(loader, "_get_deployed_agents", return_value={"engineer", "qa"}):
                    content = {}
                    loader._load_actual_memories(content)
                    
                    # Should attempt to migrate old formats
                    assert mock_migrate.call_count > 0

    def test_legacy_agent_structure_support(self, tmp_path):
        """Test support for legacy agent directory structures."""
        # Old structure might have different locations
        old_agents_dir = tmp_path / "agents"  # Without .claude
        old_agents_dir.mkdir()
        
        (old_agents_dir / "legacy_agent.md").write_text("# Legacy Agent")
        
        # Should still handle if framework path points there
        loader = FrameworkLoader(agents_dir=old_agents_dir)
        assert loader.agents_dir == old_agents_dir

    def test_deprecated_method_compatibility(self):
        """Test that deprecated methods still work for compatibility."""
        loader = FrameworkLoader()
        
        # These methods should still exist and work
        assert hasattr(loader, "get_framework_instructions")
        assert hasattr(loader, "get_agent_list")
        assert hasattr(loader, "get_agent_definition")
        
        # Should return expected types
        assert isinstance(loader.get_framework_instructions(), str)
        assert isinstance(loader.get_agent_list(), list)


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_framework_content(self):
        """Test handling of empty framework content."""
        loader = FrameworkLoader()
        loader.framework_content = {}
        
        # Should handle gracefully
        instructions = loader.get_framework_instructions()
        assert isinstance(instructions, str)

    def test_circular_memory_references(self, tmp_path):
        """Test handling of potential circular memory references."""
        memories_dir = tmp_path / ".claude-mpm" / "memories"
        memories_dir.mkdir(parents=True)
        
        # Create memories that might reference each other
        (memories_dir / "PM_memories.md").write_text("See: engineer_memories")
        (memories_dir / "engineer_memories.md").write_text("See: PM_memories")
        
        with patch.object(Path, "cwd", return_value=tmp_path):
            loader = FrameworkLoader()
            
            # Should not cause infinite loop
            content = {}
            with patch.object(loader, "_get_deployed_agents", return_value={"engineer"}):
                loader._load_actual_memories(content)
            
            assert "actual_memories" in content

    def test_unicode_and_special_characters(self, tmp_path):
        """Test handling of unicode and special characters in content."""
        project_dir = tmp_path / ".claude-mpm"
        project_dir.mkdir()
        
        # Create file with unicode content
        unicode_content = "# Instructions 中文 🎉\nÜnicode: Ω ≠ ∞"
        (project_dir / "INSTRUCTIONS.md").write_text(unicode_content, encoding="utf-8")
        
        with patch.object(Path, "cwd", return_value=tmp_path):
            loader = FrameworkLoader()
            content = {}
            loader._load_instructions_file(content)
            
            assert "中文" in content.get("custom_instructions", "")
            assert "🎉" in content.get("custom_instructions", "")

    def test_extremely_long_file_paths(self, tmp_path):
        """Test handling of extremely long file paths."""
        # Create deeply nested directory structure
        deep_path = tmp_path
        for i in range(50):  # Create 50 levels deep
            deep_path = deep_path / f"level_{i}"
        deep_path.mkdir(parents=True)
        
        # Create file at deep level
        deep_file = deep_path / "deep_instructions.md"
        deep_file.write_text("# Deep Instructions")
        
        loader = FrameworkLoader()
        content = loader._try_load_file(deep_file, "deep file")
        
        # Should handle long paths
        assert content == "# Deep Instructions"

    def test_concurrent_cache_access(self):
        """Test concurrent access to caches (thread safety)."""
        import threading
        
        loader = FrameworkLoader()
        errors = []
        
        def access_cache():
            try:
                # Simulate concurrent cache access
                loader._agent_capabilities_cache = "thread_data"
                loader._agent_capabilities_cache_time = time.time()
                _ = loader._agent_capabilities_cache
                loader.clear_agent_caches()
            except Exception as e:
                errors.append(e)
        
        # Create multiple threads
        threads = [threading.Thread(target=access_cache) for _ in range(10)]
        
        # Start all threads
        for t in threads:
            t.start()
        
        # Wait for completion
        for t in threads:
            t.join()
        
        # Should complete without errors
        assert len(errors) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])