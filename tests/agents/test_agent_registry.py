#!/usr/bin/env python3
"""
Test Agent Registry - Memory Integration Tests

Tests the enhanced agent registry functionality including:
- Basic agent loading from JSON/MD files
- Project memory file integration
- Memory-aware agent creation
- Agent metadata with memory information
"""

import json
import tempfile
import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from claude_mpm.core.unified_agent_registry import AgentRegistry, AgentTier


class TestAgentRegistryMemoryIntegration:
    """Test memory integration in agent registry."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.registry = get_agent_registry()
        
    def teardown_method(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_basic_agent_loading(self):
        """Test basic agent loading without memory."""
        # Create a simple agent file
        agent_dir = self.temp_dir / "agents"
        agent_dir.mkdir()
        
        agent_data = {
            "agent_id": "test_agent",
            "metadata": {
                "name": "Test Agent",
                "description": "A test agent",
                "category": "testing"
            },
            "instructions": "You are a test agent.",
            "model": "claude-sonnet-4-20250514"
        }
        
        agent_file = agent_dir / "test_agent.json"
        agent_file.write_text(json.dumps(agent_data))
        
        # Mock the directory discovery
        with patch.object(self.registry, 'discover_agent_directories') as mock_discover:
            mock_discover.return_value = {AgentTier.SYSTEM: agent_dir}
            
            # Load agents
            self.registry.load_agents()
            
            # Verify agent was loaded
            assert len(self.registry._agent_registry) == 1
            assert "test_agent" in self.registry._agent_registry
            
            loaded_agent = self.registry.get_agent("test_agent")
            assert loaded_agent is not None
            assert loaded_agent["agent_id"] == "test_agent"
            assert loaded_agent["metadata"]["name"] == "Test Agent"
    
    def test_memory_aware_agent_creation(self):
        """Test creation of memory-aware agents from memory files."""
        # Create memory directory and file
        memories_dir = self.temp_dir / "memories"
        memories_dir.mkdir()
        
        memory_content = """# Engineer Agent Memory

## Project Architecture
- Uses microservices architecture
- PostgreSQL database
- Redis for caching

## Implementation Guidelines
- Follow TDD practices
- Use dependency injection
- Write comprehensive tests

## Common Mistakes to Avoid
- Don't hardcode configuration values
- Always validate input parameters
- Handle errors gracefully
"""
        
        memory_file = memories_dir / "engineer_agent.md"
        memory_file.write_text(memory_content)
        
        # Mock get_path_manager() to return our temp directory
        with patch('claude_mpm.agents.core.agent_registry.get_path_manager()') as mock_config:
            mock_config_instance = Mock()
            mock_config_instance.get_project_config_dir.return_value = self.temp_dir
            mock_config.return_value = mock_config_instance
            
            # Mock directory discovery to return empty (no regular agents)
            with patch.object(self.registry, 'discover_agent_directories') as mock_discover:
                mock_discover.return_value = {}
                
                # Load agents (should create memory-aware agent)
                self.registry.load_agents()
                
                # Verify memory-aware agent was created
                assert len(self.registry._agent_registry) == 1
                assert "engineer_agent" in self.registry._agent_registry
                
                agent = self.registry.get_agent("engineer_agent")
                assert agent is not None
                assert agent["agent_id"] == "engineer_agent"
                assert agent["metadata"]["name"] == "Engineer Agent"
                assert "project memories" in agent["metadata"]["description"]
                
                # Verify memory integration
                assert "Project Memory" in agent["instructions"]
                assert "microservices architecture" in agent["instructions"]
                
                # Verify capabilities
                capabilities = agent.get("capabilities", {})
                assert capabilities.get("has_project_memory") is True
                assert capabilities.get("memory_size_kb", 0) > 0
                assert str(memory_file) in capabilities.get("memory_file", "")
                
                # Verify tier is PROJECT
                assert self.registry.get_agent_tier("engineer_agent") == AgentTier.PROJECT
    
    def test_enhance_existing_agent_with_memory(self):
        """Test enhancing existing agent with memory content."""
        # Create agent directory and file
        agent_dir = self.temp_dir / "agents"
        agent_dir.mkdir()
        
        agent_data = {
            "agent_id": "research_agent",
            "metadata": {
                "name": "Research Agent",
                "description": "AI research specialist",
                "category": "research"
            },
            "instructions": "You are a research specialist.",
            "model": "claude-sonnet-4-20250514"
        }
        
        agent_file = agent_dir / "research_agent.json"
        agent_file.write_text(json.dumps(agent_data))
        
        # Create memory directory and file
        memories_dir = self.temp_dir / "memories"
        memories_dir.mkdir()
        
        memory_content = """# Research Agent Memory

## Research Methodologies
- Use systematic literature reviews
- Apply qualitative analysis techniques
- Validate findings with multiple sources

## Domain Knowledge
- Focus on AI/ML research trends
- Understand academic publication standards
- Know key researchers in the field
"""
        
        memory_file = memories_dir / "research_agent.md"
        memory_file.write_text(memory_content)
        
        # Mock get_path_manager() and directory discovery
        with patch('claude_mpm.agents.core.agent_registry.get_path_manager()') as mock_config:
            mock_config_instance = Mock()
            mock_config_instance.get_project_config_dir.return_value = self.temp_dir
            mock_config.return_value = mock_config_instance
            
            with patch.object(self.registry, 'discover_agent_directories') as mock_discover:
                mock_discover.return_value = {AgentTier.SYSTEM: agent_dir}
                
                # Load agents
                self.registry.load_agents()
                
                # Verify agent was enhanced with memory
                assert len(self.registry._agent_registry) == 1
                agent = self.registry.get_agent("research_agent")
                assert agent is not None
                
                # Verify original content is preserved
                assert "You are a research specialist." in agent["instructions"]
                
                # Verify memory content was added
                assert "Project Memory" in agent["instructions"]
                assert "systematic literature reviews" in agent["instructions"]
                
                # Verify description was updated
                assert "Enhanced with project memories" in agent["metadata"]["description"]
                
                # Verify capabilities
                capabilities = agent.get("capabilities", {})
                assert capabilities.get("has_project_memory") is True
                
                # Verify tier was upgraded to PROJECT
                assert self.registry.get_agent_tier("research_agent") == AgentTier.PROJECT
    
    def test_list_agents_includes_memory_info(self):
        """Test that list_agents includes memory information."""
        # Create memory-aware agent
        memories_dir = self.temp_dir / "memories"
        memories_dir.mkdir()
        
        memory_file = memories_dir / "qa_agent.md"
        memory_file.write_text("# QA Agent Memory\n\n## Testing Strategies\n- Use TDD approach")
        
        with patch('claude_mpm.agents.core.agent_registry.get_path_manager()') as mock_config:
            mock_config_instance = Mock()
            mock_config_instance.get_project_config_dir.return_value = self.temp_dir
            mock_config.return_value = mock_config_instance
            
            with patch.object(self.registry, 'discover_agent_directories') as mock_discover:
                mock_discover.return_value = {}
                
                self.registry.load_agents()
                
                # Get agent list
                agents = self.registry.list_agents()
                assert len(agents) == 1
                
                agent_summary = agents[0]
                assert agent_summary["id"] == "qa_agent"
                assert agent_summary["has_project_memory"] is True
                assert "memory_size_kb" in agent_summary
                assert agent_summary["memory_size_kb"] > 0
                assert "memory_file" in agent_summary
    
    def test_extract_agent_name_from_memory_file(self):
        """Test agent name extraction from memory filenames."""
        # Test various filename formats
        assert self.registry._extract_agent_name_from_memory_file("engineer_agent.md") == "engineer"
        assert self.registry._extract_agent_name_from_memory_file("research.md") == "research"
        assert self.registry._extract_agent_name_from_memory_file("qa_agent.md") == "qa"
        
        # Test invalid formats
        assert self.registry._extract_agent_name_from_memory_file("readme.md") is None
        assert self.registry._extract_agent_name_from_memory_file("index.md") is None
        assert self.registry._extract_agent_name_from_memory_file("template.md") is None
        assert self.registry._extract_agent_name_from_memory_file("config.txt") is None


if __name__ == "__main__":
    pytest.main([__file__])
