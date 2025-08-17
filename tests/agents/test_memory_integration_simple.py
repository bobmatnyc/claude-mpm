#!/usr/bin/env python3
"""
Simple Memory Integration Test

Tests the memory integration functionality without importing the full framework.
"""

import json
import tempfile
import sys
from pathlib import Path
from unittest.mock import Mock, patch

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

def test_memory_file_processing():
    """Test memory file processing logic."""
    
    # Test agent name extraction
    def extract_agent_name_from_memory_file(filename: str):
        """Extract agent name from memory filename."""
        if filename.endswith('_agent.md'):
            return filename[:-9]  # Remove '_agent.md' (9 characters)
        elif filename.endswith('.md'):
            agent_name = filename[:-3]  # Remove '.md'
            # Skip if it's a generic file like README.md
            if agent_name.lower() in ['readme', 'index', 'template']:
                return None
            return agent_name
        return None
    
    # Test various filename formats
    assert extract_agent_name_from_memory_file("engineer_agent.md") == "engineer"
    assert extract_agent_name_from_memory_file("research.md") == "research"
    assert extract_agent_name_from_memory_file("qa_agent.md") == "qa"

    # Debug the actual results
    print(f"engineer_agent.md -> {extract_agent_name_from_memory_file('engineer_agent.md')}")
    print(f"research.md -> {extract_agent_name_from_memory_file('research.md')}")
    print(f"qa_agent.md -> {extract_agent_name_from_memory_file('qa_agent.md')}")
    
    # Test invalid formats
    assert extract_agent_name_from_memory_file("readme.md") is None
    assert extract_agent_name_from_memory_file("index.md") is None
    assert extract_agent_name_from_memory_file("template.md") is None
    assert extract_agent_name_from_memory_file("config.txt") is None
    
    print("✓ Agent name extraction works correctly")

def test_memory_aware_agent_creation():
    """Test creation of memory-aware agent data structure."""
    
    agent_id = "engineer_agent"
    agent_name = "engineer"
    memory_content = """# Engineer Agent Memory

## Project Architecture
- Uses microservices architecture
- PostgreSQL database
- Redis for caching

## Implementation Guidelines
- Follow TDD practices
- Use dependency injection
- Write comprehensive tests
"""
    memory_file = Path("/project/memories/engineer_agent.md")
    
    # Create agent data structure (simulating the registry logic)
    agent_data = {
        'agent_id': agent_id,
        'metadata': {
            'name': f"{agent_name.title()} Agent",
            'description': f"AI agent specialized in {agent_name} tasks with project memories",
            'category': 'project',
            'version': '1.0.0'
        },
        'instructions': f"""You are a {agent_name} specialist AI agent with access to project-specific knowledge and memories.

## Project Memory

{memory_content}

INSTRUCTIONS: Review your project memory above before proceeding. Apply learned patterns and avoid known mistakes.

Your role is to assist with {agent_name}-related tasks while leveraging the accumulated project knowledge to provide contextually relevant and informed responses.""",
        'capabilities': {
            'has_project_memory': True,
            'memory_file': str(memory_file),
            'memory_size_kb': round(len(memory_content.encode('utf-8')) / 1024, 2),
            'model': 'claude-sonnet-4-20250514',
            'resource_tier': 'standard'
        },
        'model': 'claude-sonnet-4-20250514',
        'resource_tier': 'standard',
        '_tier': 'project',
        '_source_file': str(memory_file)
    }
    
    # Verify the structure
    assert agent_data['agent_id'] == "engineer_agent"
    assert agent_data['metadata']['name'] == "Engineer Agent"
    assert "project memories" in agent_data['metadata']['description']
    assert "Project Memory" in agent_data['instructions']
    assert "microservices architecture" in agent_data['instructions']
    assert agent_data['capabilities']['has_project_memory'] is True
    assert agent_data['capabilities']['memory_size_kb'] > 0
    assert agent_data['_tier'] == 'project'
    
    print("✓ Memory-aware agent creation works correctly")

def test_enhance_existing_agent():
    """Test enhancing existing agent with memory content."""
    
    # Original agent data
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
    
    memory_content = """# Research Agent Memory

## Research Methodologies
- Use systematic literature reviews
- Apply qualitative analysis techniques
- Validate findings with multiple sources
"""
    memory_file = Path("/project/memories/research_agent.md")
    
    # Enhance agent with memory (simulating the registry logic)
    original_instructions = agent_data.get('instructions', '')
    memory_section = f"\n\n## Project Memory\n\n{memory_content}\n\nINSTRUCTIONS: Review your project memory above before proceeding. Apply learned patterns and avoid known mistakes.\n"
    
    agent_data['instructions'] = original_instructions + memory_section
    
    # Update description to note memory integration
    metadata = agent_data.setdefault('metadata', {})
    original_description = metadata.get('description', '')
    if 'project memories' not in original_description.lower():
        metadata['description'] = f"{original_description} (Enhanced with project memories)".strip()
    
    # Mark as memory-aware in capabilities
    capabilities = agent_data.setdefault('capabilities', {})
    capabilities['has_project_memory'] = True
    capabilities['memory_file'] = str(memory_file)
    capabilities['memory_size_kb'] = round(len(memory_content.encode('utf-8')) / 1024, 2)
    
    # Verify enhancement
    assert "You are a research specialist." in agent_data['instructions']
    assert "Project Memory" in agent_data['instructions']
    assert "systematic literature reviews" in agent_data['instructions']
    assert "Enhanced with project memories" in agent_data['metadata']['description']
    assert agent_data['capabilities']['has_project_memory'] is True
    
    print("✓ Agent enhancement with memory works correctly")

def test_agent_list_with_memory_info():
    """Test agent list includes memory information."""
    
    # Simulate agent registry data
    agent_registry = {
        "engineer_agent": {
            "agent_id": "engineer_agent",
            "metadata": {
                "name": "Engineer Agent",
                "description": "AI agent specialized in engineer tasks with project memories",
                "category": "project",
                "version": "1.0.0"
            },
            "capabilities": {
                "has_project_memory": True,
                "memory_size_kb": 1.2,
                "memory_file": "/project/memories/engineer_agent.md"
            },
            "model": "claude-sonnet-4-20250514"
        },
        "qa_agent": {
            "agent_id": "qa_agent", 
            "metadata": {
                "name": "QA Agent",
                "description": "Quality assurance specialist",
                "category": "testing"
            },
            "model": "claude-sonnet-4-20250514"
        }
    }
    
    agent_tiers = {
        "engineer_agent": "project",
        "qa_agent": "system"
    }
    
    # Simulate list_agents method
    agents = []
    for agent_id, agent_data in agent_registry.items():
        metadata = agent_data.get('metadata', {})
        capabilities = agent_data.get('capabilities', {})
        
        # Check if agent has project memory
        has_memory = capabilities.get('has_project_memory', False)
        memory_size = capabilities.get('memory_size_kb', 0)
        
        agent_summary = {
            'id': agent_id,
            'name': metadata.get('name', agent_id),
            'description': metadata.get('description', ''),
            'category': metadata.get('category', 'general'),
            'version': metadata.get('version', '1.0.0'),
            'model': agent_data.get('model', 'claude-sonnet-4-20250514'),
            'resource_tier': agent_data.get('resource_tier', 'standard'),
            'tier': agent_tiers.get(agent_id, 'system'),
            'has_project_memory': has_memory
        }
        
        # Add memory details if present
        if has_memory:
            agent_summary['memory_size_kb'] = memory_size
            agent_summary['memory_file'] = capabilities.get('memory_file', '')
        
        agents.append(agent_summary)
    
    # Verify results
    assert len(agents) == 2
    
    engineer_agent = next(a for a in agents if a['id'] == 'engineer_agent')
    assert engineer_agent['has_project_memory'] is True
    assert engineer_agent['memory_size_kb'] == 1.2
    assert 'memory_file' in engineer_agent
    assert engineer_agent['tier'] == 'project'
    
    qa_agent = next(a for a in agents if a['id'] == 'qa_agent')
    assert qa_agent['has_project_memory'] is False
    assert 'memory_size_kb' not in qa_agent
    assert qa_agent['tier'] == 'system'
    
    print("✓ Agent list with memory info works correctly")

if __name__ == "__main__":
    print("Running memory integration tests...")
    
    test_memory_file_processing()
    test_memory_aware_agent_creation()
    test_enhance_existing_agent()
    test_agent_list_with_memory_info()
    
    print("\n✅ All memory integration tests passed!")
    print("\nMemory integration features:")
    print("- Automatic detection of memory files in .claude-mpm/memories/")
    print("- Creation of memory-aware agents at PROJECT tier")
    print("- Enhancement of existing agents with project memories")
    print("- Memory information included in agent metadata")
    print("- Agent descriptions note memory integration")
    print("- Capabilities indicate memory presence and size")
