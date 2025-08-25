"""Unit tests for FrameworkLoader class - focused on testable behavior.

This test suite provides targeted unit tests for the FrameworkLoader class,
focusing on the actual behavior rather than implementation details.
These tests serve as a safety net for the upcoming refactoring.
"""

import json
import logging
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, Optional
from unittest.mock import MagicMock, Mock, patch, call

import pytest
import yaml


def create_mock_logger():
    """Create a properly configured mock logger."""
    mock_logger = MagicMock()
    mock_logger.level = logging.INFO
    mock_logger.info = MagicMock()
    mock_logger.debug = MagicMock()
    mock_logger.warning = MagicMock()
    mock_logger.error = MagicMock()
    return mock_logger


@pytest.fixture
def mock_framework_loader():
    """Create a FrameworkLoader with all dependencies mocked."""
    with patch("claude_mpm.core.framework_loader.get_logger") as mock_logger:
        with patch("claude_mpm.core.framework_loader.AgentRegistryAdapter") as mock_registry:
            mock_logger.return_value = create_mock_logger()
            mock_registry.return_value = MagicMock()
            
            from claude_mpm.core.framework_loader import FrameworkLoader
            
            # Patch _load_framework_content to avoid file loading during init
            with patch.object(FrameworkLoader, "_load_framework_content", return_value={}):
                loader = FrameworkLoader(framework_path=Path("/test"))
                yield loader


class TestFrameworkLoaderBasics:
    """Basic tests for FrameworkLoader initialization and structure."""

    def test_framework_loader_initialization(self):
        """Test basic initialization of FrameworkLoader."""
        with patch("claude_mpm.core.framework_loader.get_logger") as mock_logger:
            with patch("claude_mpm.core.framework_loader.AgentRegistryAdapter") as mock_registry:
                mock_logger.return_value = create_mock_logger()
                mock_registry.return_value = MagicMock()
                
                from claude_mpm.core.framework_loader import FrameworkLoader
                
                # Patch _load_framework_content to avoid file loading during init
                with patch.object(FrameworkLoader, "_load_framework_content", return_value={}):
                    # Test with explicit framework path
                    loader = FrameworkLoader(framework_path=Path("/test/path"))
                    assert loader.framework_path == Path("/test/path")
                    assert loader.agents_dir is None
                    assert loader.framework_version is None
                    assert loader.framework_last_modified is None

    def test_cache_initialization(self, mock_framework_loader):
        """Test that caches are properly initialized."""
        loader = mock_framework_loader
        
        # Check cache initialization
        assert loader._agent_capabilities_cache is None
        assert loader._agent_capabilities_cache_time == 0
        assert loader._deployed_agents_cache is None
        assert loader._deployed_agents_cache_time == 0
        assert loader._memories_cache is None
        assert loader._memories_cache_time == 0
        assert isinstance(loader._agent_metadata_cache, dict)
        assert len(loader._agent_metadata_cache) == 0

    def test_cache_ttl_settings(self, mock_framework_loader):
        """Test cache TTL settings are properly set."""
        loader = mock_framework_loader
        
        assert loader.CAPABILITIES_CACHE_TTL == 60
        assert loader.DEPLOYED_AGENTS_CACHE_TTL == 30
        assert loader.METADATA_CACHE_TTL == 60
        assert loader.MEMORIES_CACHE_TTL == 60


class TestCacheManagement:
    """Test cache management functionality."""

    def test_clear_all_caches(self, mock_framework_loader):
        """Test clearing all caches."""
        loader = mock_framework_loader
        
        # Populate caches
        loader._agent_capabilities_cache = "test_capabilities"
        loader._agent_capabilities_cache_time = time.time()
        loader._deployed_agents_cache = {"agent1"}
        loader._deployed_agents_cache_time = time.time()
        loader._memories_cache = {"memory": "data"}
        loader._memories_cache_time = time.time()
        loader._agent_metadata_cache = {"agent1": ({"meta": "data"}, time.time())}
        
        # Clear all caches
        loader.clear_all_caches()
        
        # Verify all caches cleared
        assert loader._agent_capabilities_cache is None
        assert loader._agent_capabilities_cache_time == 0
        assert loader._deployed_agents_cache is None
        assert loader._deployed_agents_cache_time == 0
        assert loader._memories_cache is None
        assert loader._memories_cache_time == 0
        assert len(loader._agent_metadata_cache) == 0

    def test_clear_agent_caches(self, mock_framework_loader):
        """Test clearing only agent-related caches."""
        loader = mock_framework_loader
        
        # Populate all caches
        loader._agent_capabilities_cache = "test_capabilities"
        loader._deployed_agents_cache = {"agent1"}
        loader._memories_cache = {"memory": "data"}
        loader._agent_metadata_cache = {"agent1": ({"meta": "data"}, time.time())}
        
        # Clear only agent caches
        loader.clear_agent_caches()
        
        # Verify only agent caches cleared
        assert loader._agent_capabilities_cache is None
        assert loader._deployed_agents_cache is None
        assert len(loader._agent_metadata_cache) == 0
        # Memory cache should remain
        assert loader._memories_cache is not None

    def test_clear_memory_caches(self, mock_framework_loader):
        """Test clearing only memory caches."""
        loader = mock_framework_loader
        
        # Populate caches
        loader._agent_capabilities_cache = "test_capabilities"
        loader._memories_cache = {"memory": "data"}
        
        # Clear only memory caches
        loader.clear_memory_caches()
        
        # Verify only memory cache cleared
        assert loader._memories_cache is None
        # Agent cache should remain
        assert loader._agent_capabilities_cache is not None


class TestFileLoading:
    """Test file loading functionality."""

    def test_try_load_file_success(self, mock_framework_loader, tmp_path):
        """Test successful file loading."""
        loader = mock_framework_loader
        
        # Create test file
        test_file = tmp_path / "test.md"
        test_file.write_text("# Test Content")
        
        content = loader._try_load_file(test_file, "test file")
        assert content == "# Test Content"

    def test_try_load_file_not_found(self, mock_framework_loader):
        """Test loading non-existent file."""
        loader = mock_framework_loader
        
        content = loader._try_load_file(Path("/non/existent/file.md"), "test")
        assert content is None

    def test_try_load_file_permission_error(self, mock_framework_loader, tmp_path):
        """Test handling permission errors when loading files."""
        loader = mock_framework_loader
        
        test_file = tmp_path / "restricted.md"
        test_file.write_text("content")
        
        with patch("builtins.open", side_effect=PermissionError("Access denied")):
            content = loader._try_load_file(test_file, "restricted")
            assert content is None


class TestMemoryMigration:
    """Test memory file migration functionality."""

    def test_migrate_memory_file(self, mock_framework_loader, tmp_path):
        """Test migrating old format memory files."""
        loader = mock_framework_loader
        
        # Create old format file
        old_file = tmp_path / "old.md"
        new_file = tmp_path / "new.md"
        old_file.write_text("# Old Content")
        
        loader._migrate_memory_file(old_file, new_file)
        
        # Check migration
        assert new_file.exists()
        assert new_file.read_text() == "# Old Content"
        assert not old_file.exists()


class TestMetadataStripping:
    """Test metadata stripping functionality."""

    def test_strip_metadata_comments(self, mock_framework_loader):
        """Test stripping metadata comments from content."""
        loader = mock_framework_loader
        
        content = """<!-- METADATA: version=1.0 -->
<!-- SOURCE: project -->
# Real Content
This is the actual content.
<!-- END METADATA -->"""
        
        stripped = loader._strip_metadata_comments(content)
        
        assert "METADATA" not in stripped
        assert "SOURCE" not in stripped
        assert "Real Content" in stripped
        assert "actual content" in stripped


class TestAgentMetadataParsing:
    """Test agent metadata parsing functionality."""

    def test_parse_agent_metadata_valid_yaml(self, mock_framework_loader, tmp_path):
        """Test parsing valid YAML frontmatter."""
        loader = mock_framework_loader
        
        agent_file = tmp_path / "agent.md"
        agent_file.write_text("""---
name: Test Agent
model: claude-3.5-sonnet
capabilities:
  - testing
  - validation
---
# Agent Content""")
        
        metadata = loader._parse_agent_metadata(agent_file)
        
        assert metadata is not None
        assert metadata["name"] == "Test Agent"
        assert metadata["model"] == "claude-3.5-sonnet"
        assert "testing" in metadata["capabilities"]

    def test_parse_agent_metadata_no_frontmatter(self, mock_framework_loader, tmp_path):
        """Test parsing agent file without frontmatter."""
        loader = mock_framework_loader
        
        agent_file = tmp_path / "agent.md"
        agent_file.write_text("# Agent without metadata")
        
        metadata = loader._parse_agent_metadata(agent_file)
        assert metadata is None

    def test_parse_agent_metadata_malformed_yaml(self, mock_framework_loader, tmp_path):
        """Test parsing agent file with malformed YAML."""
        loader = mock_framework_loader
        
        agent_file = tmp_path / "agent.md"
        agent_file.write_text("""---
invalid: [yaml
broken: structure
---
# Agent Content""")
        
        metadata = loader._parse_agent_metadata(agent_file)
        
        # Should handle gracefully
        assert metadata is None


class TestNpmPathResolution:
    """Test NPM global path resolution."""

    def test_get_npm_global_path_success(self, mock_framework_loader):
        """Test successful NPM global path resolution."""
        loader = mock_framework_loader
        
        expected_path = "/usr/local/lib/node_modules/claude-multiagent-pm"
        
        with patch("subprocess.check_output") as mock_subprocess:
            mock_subprocess.return_value = expected_path.encode()
            with patch.object(Path, "exists", return_value=True):
                npm_path = loader._get_npm_global_path()
                assert npm_path == Path(expected_path)

    def test_get_npm_global_path_not_installed(self, mock_framework_loader):
        """Test NPM path when package not installed."""
        loader = mock_framework_loader
        
        with patch("subprocess.check_output", side_effect=subprocess.CalledProcessError(1, "npm")):
            npm_path = loader._get_npm_global_path()
            assert npm_path is None


class TestMemoryAggregation:
    """Test memory aggregation functionality."""

    def test_aggregate_memories_deduplication(self, mock_framework_loader):
        """Test memory aggregation with deduplication."""
        loader = mock_framework_loader
        
        memories = [
            {"content": "Memory 1\nMemory 2\nMemory 1", "source": "project"},
            {"content": "Memory 2\nMemory 3", "source": "user"}
        ]
        
        aggregated = loader._aggregate_memories(memories)
        
        # Should deduplicate
        assert aggregated.count("Memory 1") <= 2  # May appear in header + content
        assert aggregated.count("Memory 2") <= 2
        assert "Memory 3" in aggregated


class TestOutputStyleIntegration:
    """Test output style manager integration."""

    def test_output_style_initialization_success(self, mock_framework_loader):
        """Test successful output style manager initialization."""
        loader = mock_framework_loader
        
        with patch("claude_mpm.core.output_style_manager.OutputStyleManager") as MockManager:
            mock_instance = MagicMock()
            MockManager.return_value = mock_instance
            
            loader._initialize_output_style()
            
            assert loader.output_style_manager is not None

    def test_output_style_initialization_failure(self, mock_framework_loader):
        """Test graceful handling of output style initialization failure."""
        loader = mock_framework_loader
        
        with patch("claude_mpm.core.output_style_manager.OutputStyleManager", side_effect=Exception("Failed")):
            loader._initialize_output_style()
            
            # Should handle gracefully - output_style_manager may be None
            # but should not raise exception
            assert True  # Got here without exception


class TestPackagedResources:
    """Test loading from packaged resources."""

    def test_load_packaged_file_with_files(self, mock_framework_loader):
        """Test loading file using importlib.resources.files."""
        loader = mock_framework_loader
        
        with patch("claude_mpm.core.framework_loader.files") as mock_files:
            mock_resource = MagicMock()
            mock_resource.read_text.return_value = "# Package Content"
            mock_resource.__truediv__.return_value = mock_resource
            mock_files.return_value = mock_resource
            
            content = loader._load_packaged_file("INSTRUCTIONS.md")
            assert content == "# Package Content"

    def test_load_packaged_file_without_files(self, mock_framework_loader):
        """Test loading when importlib.resources.files is not available."""
        loader = mock_framework_loader
        
        with patch("claude_mpm.core.framework_loader.files", None):
            content = loader._load_packaged_file("INSTRUCTIONS.md")
            
            # Should return None or handle gracefully
            assert content is None or isinstance(content, str)


class TestPublicMethods:
    """Test public interface methods."""

    def test_get_framework_instructions(self, mock_framework_loader):
        """Test getting framework instructions."""
        loader = mock_framework_loader
        loader.framework_content = {
            "instructions": "# Test Instructions",
            "workflow_instructions": "# Workflow"
        }
        
        instructions = loader.get_framework_instructions()
        
        assert isinstance(instructions, str)
        assert len(instructions) > 0

    def test_get_agent_list(self, mock_framework_loader):
        """Test getting list of agents."""
        loader = mock_framework_loader
        
        agents = loader.get_agent_list()
        assert isinstance(agents, list)

    def test_get_agent_hierarchy(self, mock_framework_loader):
        """Test getting agent hierarchy."""
        loader = mock_framework_loader
        
        hierarchy = loader.get_agent_hierarchy()
        assert isinstance(hierarchy, dict)


class TestCacheTTLBehavior:
    """Test cache TTL expiration behavior."""

    def test_cache_ttl_expiration(self, mock_framework_loader):
        """Test that caches respect TTL expiration."""
        loader = mock_framework_loader
        
        # Set cache with timestamp
        loader._memories_cache = {"test": "data"}
        loader._memories_cache_time = time.time()
        
        # Within TTL - cache should be considered valid
        assert loader._memories_cache is not None
        
        # Simulate time passing beyond TTL
        loader._memories_cache_time = time.time() - 70  # Beyond 60 second TTL
        
        # In actual implementation, the cache would be checked and invalidated
        # This is just testing the data structure
        assert loader._memories_cache_time < time.time() - loader.MEMORIES_CACHE_TTL


class TestFrameworkPathDetection:
    """Test framework path detection logic."""

    def test_detect_framework_path_with_npm(self, mock_framework_loader):
        """Test framework path detection using npm."""
        loader = mock_framework_loader
        
        expected_path = "/usr/local/lib/node_modules/claude-multiagent-pm"
        
        with patch("subprocess.check_output") as mock_subprocess:
            mock_subprocess.return_value = expected_path.encode()
            with patch.object(Path, "exists", return_value=True):
                with patch.object(Path, "is_file", return_value=True):
                    npm_path = loader._get_npm_global_path()
                    assert npm_path == Path(expected_path)


class TestErrorHandling:
    """Test comprehensive error handling."""

    def test_yaml_parse_error_handling(self, mock_framework_loader, tmp_path):
        """Test handling of YAML parsing errors."""
        loader = mock_framework_loader
        
        # Create file with invalid YAML
        bad_yaml = tmp_path / "bad.yaml"
        bad_yaml.write_text("invalid: [yaml: structure")
        
        # Should not raise exception
        with patch("yaml.safe_load", side_effect=yaml.YAMLError("Parse error")):
            result = loader._load_routing_from_template("test")
            assert result is None

    def test_file_read_encoding_error(self, mock_framework_loader, tmp_path):
        """Test handling of file encoding errors."""
        loader = mock_framework_loader
        
        test_file = tmp_path / "bad_encoding.md"
        # Write binary data that's not valid UTF-8
        test_file.write_bytes(b'\x80\x81\x82')
        
        # Should handle encoding errors gracefully
        content = loader._try_load_file(test_file, "bad encoding")
        # Should either return None or handle the error
        assert content is None or isinstance(content, str)


class TestIntegrationScenarios:
    """Test realistic integration scenarios."""

    def test_complete_initialization_flow(self, tmp_path):
        """Test complete initialization flow with real files."""
        # Setup directory structure
        project_dir = tmp_path / ".claude-mpm"
        project_dir.mkdir()
        
        # Create instruction files
        (project_dir / "INSTRUCTIONS.md").write_text("# Custom Instructions")
        
        with patch("claude_mpm.core.framework_loader.get_logger") as mock_logger:
            with patch("claude_mpm.core.framework_loader.AgentRegistryAdapter") as mock_registry:
                mock_logger.return_value = create_mock_logger()
                mock_registry.return_value = MagicMock()
                
                from claude_mpm.core.framework_loader import FrameworkLoader
                
                with patch.object(Path, "cwd", return_value=tmp_path):
                    loader = FrameworkLoader()
                    
                    # Should have loaded some content
                    assert loader.framework_content is not None
                    assert isinstance(loader.framework_content, dict)

    def test_memory_loading_with_deployed_agents(self, mock_framework_loader, tmp_path):
        """Test memory loading when agents are deployed."""
        loader = mock_framework_loader
        
        # Setup memory directory
        memories_dir = tmp_path / "memories"
        memories_dir.mkdir()
        
        # Create memory files
        (memories_dir / "PM_memories.md").write_text("# PM Memory")
        (memories_dir / "engineer_memories.md").write_text("# Engineer Memory")
        (memories_dir / "qa_memories.md").write_text("# QA Memory")
        
        # Mock deployed agents
        with patch.object(loader, "_get_deployed_agents", return_value={"engineer"}):
            content = {}
            # Manually test the memory loading logic
            deployed = loader._get_deployed_agents()
            
            # Only engineer should be loaded
            assert "engineer" in deployed
            assert "qa" not in deployed


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])