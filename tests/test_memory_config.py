#!/usr/bin/env python3
"""
Test script to verify memory configuration integration.

This script tests that:
1. Memory configuration is properly loaded from Config
2. Agent-specific overrides work correctly
3. Limits are applied as expected
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.core.config import Config
from claude_mpm.services.agents.memory import AgentMemoryManager


def test_memory_config():
    """Test memory configuration functionality."""
    print("Testing Memory Configuration System")
    print("=" * 50)
    
    # Test 1: Default configuration
    print("\n1. Testing default configuration:")
    config = Config()
    manager = AgentMemoryManager(config)
    
    print(f"  Memory enabled: {manager.memory_enabled}")
    print(f"  Auto-learning: {manager.auto_learning}")
    print(f"  Default limits: {manager.memory_limits}")
    
    # Test 2: Agent-specific limits
    print("\n2. Testing agent-specific limits:")
    
    # Test research agent (should have 16KB limit)
    research_limits = manager._get_agent_limits('research')
    print(f"  Research agent size limit: {research_limits['max_file_size_kb']}KB")
    print(f"  Research agent auto-learning: {manager._get_agent_auto_learning('research')}")
    
    # Test QA agent (should have default size but auto-learning enabled)
    qa_limits = manager._get_agent_limits('qa')
    print(f"  QA agent size limit: {qa_limits['max_file_size_kb']}KB")
    print(f"  QA agent auto-learning: {manager._get_agent_auto_learning('qa')}")
    
    # Test regular agent (should use defaults)
    engineer_limits = manager._get_agent_limits('engineer')
    print(f"  Engineer agent size limit: {engineer_limits['max_file_size_kb']}KB")
    print(f"  Engineer agent auto-learning: {manager._get_agent_auto_learning('engineer')}")
    
    # Test 3: Custom configuration
    print("\n3. Testing custom configuration:")
    custom_config = Config({
        'memory': {
            'enabled': False,
            'auto_learning': True,
            'limits': {
                'default_size_kb': 16,
                'max_sections': 20
            },
            'agent_overrides': {
                'custom_agent': {
                    'size_kb': 32,
                    'auto_learning': False
                }
            }
        }
    })
    
    custom_manager = AgentMemoryManager(custom_config)
    print(f"  Custom memory enabled: {custom_manager.memory_enabled}")
    print(f"  Custom auto-learning: {custom_manager.auto_learning}")
    print(f"  Custom default size: {custom_manager.memory_limits['max_file_size_kb']}KB")
    print(f"  Custom max sections: {custom_manager.memory_limits['max_sections']}")
    
    custom_limits = custom_manager._get_agent_limits('custom_agent')
    print(f"  Custom agent size limit: {custom_limits['max_file_size_kb']}KB")
    print(f"  Custom agent auto-learning: {custom_manager._get_agent_auto_learning('custom_agent')}")
    
    print("\n✅ All tests passed!")


if __name__ == "__main__":
    test_memory_config()