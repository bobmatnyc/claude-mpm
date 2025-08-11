"""Unit tests for AgentCapabilitiesGenerator service.

This module tests the AgentCapabilitiesGenerator service which dynamically
generates agent capability documentation for inclusion in system instructions.

TEST SCENARIOS COVERED:
1. Successful capability section generation with multiple agents
2. Empty agent list handling
3. Error handling with invalid agent data
4. Agent grouping by source tier (system, project, user)
5. Unknown tier handling with fallback behavior
6. Core agent list generation with alphabetical sorting
7. Detailed capability text generation with various fallback strategies
8. Long text truncation for capability descriptions
9. Fallback content generation when errors occur

TEST FOCUS:
- Validates proper template rendering and content generation
- Ensures graceful handling of missing or invalid data
- Tests tier-based agent organization
- Verifies capability text extraction with multiple fallback options

TEST COVERAGE GAPS:
- No testing of template customization
- No testing of internationalization/localization
- No testing of capability filtering or search
- No performance tests for large agent lists
"""

import pytest
import logging

from claude_mpm.services.agents.management import AgentCapabilitiesGenerator


class TestAgentCapabilitiesGenerator:
    """Test cases for AgentCapabilitiesGenerator service.
    
    Tests focus on the service's ability to generate dynamic documentation
    from deployed agent metadata, with proper error handling and fallbacks.
    """
    
    @pytest.fixture
    def generator(self):
        """Create an AgentCapabilitiesGenerator instance."""
        return AgentCapabilitiesGenerator()
    
    @pytest.fixture
    def sample_agents(self):
        """Create sample agent data for testing."""
        return [
            {
                'id': 'research',
                'name': 'Research Agent',
                'description': 'Analyzes codebases and identifies patterns',
                'specializations': ['codebase analysis', 'pattern detection', 'best practices'],
                'capabilities': {
                    'when_to_use': [
                        'Analyzing code structure',
                        'Finding implementation patterns'
                    ]
                },
                'source_tier': 'system',
                'tools': ['grep', 'find', 'tree', 'ast-parser']
            },
            {
                'id': 'engineer',
                'name': 'Engineer Agent',
                'description': 'Implements features and fixes bugs',
                'specializations': ['implementation', 'refactoring'],
                'capabilities': {},
                'source_tier': 'system',
                'tools': ['edit', 'write', 'test']
            },
            {
                'id': 'custom-analyzer',
                'name': 'Custom Analyzer',
                'description': 'Project-specific analysis tool',
                'specializations': ['custom analysis'],
                'capabilities': {
                    'when_to_use': ['Analyzing project-specific patterns']
                },
                'source_tier': 'project',
                'tools': ['custom-tool']
            }
        ]
    
    def test_generate_capabilities_section_success(self, generator, sample_agents):
        """Test successful generation of capabilities section."""
        content = generator.generate_capabilities_section(sample_agents)
        
        # Verify core agents list
        assert "**Core Agents**: custom-analyzer, engineer, research" in content
        
        # Verify project-specific agents section
        assert "### Project-Specific Agents" in content
        assert "**Custom Analyzer** (custom-analyzer): Project-specific analysis tool" in content
        
        # Verify agent capabilities
        assert "**Research Agent**: Analyzing code structure; Finding implementation patterns" in content
        assert "**Engineer Agent**: implementation, refactoring" in content
        assert "**Custom Analyzer**: Analyzing project-specific patterns" in content
        
        # Verify agent name formats (order is alphabetical by ID)
        assert 'Capitalized: Custom Analyzer", "Engineer Agent", "Research Agent' in content
        assert 'Lowercase-hyphenated: custom-analyzer", "engineer", "research' in content
        
        # Verify footer
        assert "*Generated from 3 deployed agents*" in content
    
    def test_generate_capabilities_section_empty_agents(self, generator):
        """Test generation with empty agent list."""
        content = generator.generate_capabilities_section([])
        
        assert "**Core Agents**: " in content  # Empty list
        assert "*Generated from 0 deployed agents*" in content
    
    def test_generate_capabilities_section_error_handling(self, generator, caplog):
        """Test error handling returns fallback content."""
        # Pass invalid data that will cause template rendering to fail
        invalid_agents = [{'invalid': 'data'}]  # Missing required fields
        
        with caplog.at_level(logging.ERROR):
            content = generator.generate_capabilities_section(invalid_agents)
        
        # Should return fallback content
        assert "Unable to dynamically generate agent list" in content
        assert "research, engineer, qa, documentation" in content
        assert "Failed to generate capabilities section" in caplog.text
    
    def test_group_by_tier(self, generator, sample_agents):
        """Test grouping agents by source tier."""
        grouped = generator._group_by_tier(sample_agents)
        
        assert len(grouped['system']) == 2
        assert len(grouped['project']) == 1
        assert len(grouped['user']) == 0
        
        assert grouped['system'][0]['id'] == 'research'
        assert grouped['system'][1]['id'] == 'engineer'
        assert grouped['project'][0]['id'] == 'custom-analyzer'
    
    def test_group_by_tier_unknown_tier(self, generator, caplog):
        """Test handling of unknown source tiers."""
        agents = [
            {'id': 'test', 'source_tier': 'unknown-tier'}
        ]
        
        with caplog.at_level(logging.WARNING):
            grouped = generator._group_by_tier(agents)
        
        # Should default to system tier
        assert len(grouped['system']) == 1
        assert "Unknown source tier 'unknown-tier'" in caplog.text
    
    def test_generate_core_agent_list(self, generator, sample_agents):
        """Test generation of core agent list."""
        agent_list = generator._generate_core_agent_list(sample_agents)
        
        # Should be sorted alphabetically
        assert agent_list == "custom-analyzer, engineer, research"
    
    def test_generate_detailed_capabilities(self, generator, sample_agents):
        """Test generation of detailed capabilities."""
        capabilities = generator._generate_detailed_capabilities(sample_agents)
        
        assert len(capabilities) == 3
        
        # Verify sorted by ID
        assert capabilities[0]['id'] == 'custom-analyzer'
        assert capabilities[1]['id'] == 'engineer'
        assert capabilities[2]['id'] == 'research'
        
        # Verify capability text generation
        # Should use when_to_use if available
        assert capabilities[2]['capability_text'] == 'Analyzing code structure; Finding implementation patterns'
        
        # Should fall back to specializations
        assert capabilities[1]['capability_text'] == 'implementation, refactoring'
        
        # Verify tools extraction
        assert capabilities[2]['tools'] == 'grep, find, tree, ast-parser'
    
    def test_generate_detailed_capabilities_long_text(self, generator):
        """Test truncation of long capability text."""
        agents = [{
            'id': 'test',
            'name': 'Test Agent',
            'description': 'A' * 150,  # Very long description
            'specializations': [],
            'capabilities': {},
            'tools': []
        }]
        
        capabilities = generator._generate_detailed_capabilities(agents)
        
        # Should truncate to 100 chars with ellipsis
        assert len(capabilities[0]['capability_text']) == 100
        assert capabilities[0]['capability_text'].endswith('...')
    
    def test_generate_detailed_capabilities_fallback_to_description(self, generator):
        """Test fallback to description when no specializations or when_to_use."""
        agents = [{
            'id': 'test',
            'name': 'Test Agent',
            'description': 'General purpose testing agent',
            'specializations': [],
            'capabilities': {},
            'tools': []
        }]
        
        capabilities = generator._generate_detailed_capabilities(agents)
        
        assert capabilities[0]['capability_text'] == 'General purpose testing agent'
    
    def test_generate_detailed_capabilities_no_description(self, generator):
        """Test default text when no description available."""
        agents = [{
            'id': 'test',
            'name': 'Test Agent',
            'specializations': [],
            'capabilities': {},
            'tools': []
        }]
        
        capabilities = generator._generate_detailed_capabilities(agents)
        
        assert capabilities[0]['capability_text'] == 'General purpose agent'
    
    def test_generate_fallback_content(self, generator):
        """Test fallback content generation."""
        content = generator._generate_fallback_content()
        
        # Verify it contains default agents
        assert "research, engineer, qa, documentation" in content
        assert "Unable to dynamically generate agent list" in content
        assert "Research**: Codebase analysis" in content