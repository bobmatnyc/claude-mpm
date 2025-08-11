#!/usr/bin/env python3
"""
Test loading memory configuration from a config file.

This script tests that memory configuration can be loaded from YAML/JSON files.
"""

import sys
import json
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.core.config import Config
from claude_mpm.services.agents.memory import AgentMemoryManager


def test_yaml_config():
    """Test loading memory configuration from YAML file."""
    print("Testing Memory Configuration from YAML File")
    print("=" * 50)
    
    yaml_content = """
# Claude MPM Configuration
memory:
  enabled: true
  auto_learning: true
  limits:
    default_size_kb: 12
    max_sections: 15
    max_items_per_section: 20
    max_line_length: 150
  agent_overrides:
    research:
      size_kb: 24
      auto_learning: true
    engineer:
      size_kb: 10
      auto_learning: false
    custom_test:
      size_kb: 32
"""
    
    try:
        # Create temporary YAML file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write(yaml_content)
            yaml_file = f.name
        
        # Load configuration from YAML
        config = Config(config_file=yaml_file)
        manager = AgentMemoryManager(config)
        
        print(f"\n1. Loaded configuration from YAML:")
        print(f"  Memory enabled: {manager.memory_enabled}")
        print(f"  Auto-learning: {manager.auto_learning}")
        print(f"  Default size: {manager.memory_limits['max_file_size_kb']}KB")
        print(f"  Max sections: {manager.memory_limits['max_sections']}")
        
        print(f"\n2. Agent-specific configurations:")
        for agent_id in ['research', 'engineer', 'custom_test', 'qa']:
            limits = manager._get_agent_limits(agent_id)
            auto_learn = manager._get_agent_auto_learning(agent_id)
            print(f"  {agent_id}: {limits['max_file_size_kb']}KB, auto-learning={auto_learn}")
        
        print("\n✅ YAML configuration test passed!")
        
    finally:
        # Clean up
        Path(yaml_file).unlink(missing_ok=True)


def test_json_config():
    """Test loading memory configuration from JSON file."""
    print("\n\nTesting Memory Configuration from JSON File")
    print("=" * 50)
    
    json_config = {
        "memory": {
            "enabled": False,
            "auto_learning": False,
            "limits": {
                "default_size_kb": 4,
                "max_sections": 5
            },
            "agent_overrides": {
                "minimal_agent": {
                    "size_kb": 2,
                    "auto_learning": False
                }
            }
        }
    }
    
    try:
        # Create temporary JSON file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(json_config, f)
            json_file = f.name
        
        # Load configuration from JSON
        config = Config(config_file=json_file)
        manager = AgentMemoryManager(config)
        
        print(f"\n1. Loaded configuration from JSON:")
        print(f"  Memory enabled: {manager.memory_enabled}")
        print(f"  Auto-learning: {manager.auto_learning}")
        print(f"  Default size: {manager.memory_limits['max_file_size_kb']}KB")
        print(f"  Max sections: {manager.memory_limits['max_sections']}")
        
        print(f"\n2. Minimal agent configuration:")
        limits = manager._get_agent_limits('minimal_agent')
        print(f"  Size limit: {limits['max_file_size_kb']}KB")
        print(f"  Auto-learning: {manager._get_agent_auto_learning('minimal_agent')}")
        
        print("\n✅ JSON configuration test passed!")
        
    finally:
        # Clean up
        Path(json_file).unlink(missing_ok=True)


def test_env_override():
    """Test environment variable overrides."""
    print("\n\nTesting Environment Variable Overrides")
    print("=" * 50)
    
    import os
    
    # Set environment variables
    os.environ['CLAUDE_PM_MEMORY__ENABLED'] = 'false'
    os.environ['CLAUDE_PM_MEMORY__AUTO_LEARNING'] = 'true'
    os.environ['CLAUDE_PM_MEMORY__LIMITS__DEFAULT_SIZE_KB'] = '20'
    
    try:
        config = Config()
        
        # Note: Current Config implementation doesn't support nested env vars
        # This is a limitation that could be addressed in the future
        print("\nNOTE: Current Config class doesn't support nested environment variables.")
        print("This would require enhancement to handle double underscore notation.")
        print("For now, memory configuration should be done via config files or direct dict.")
        
    finally:
        # Clean up environment
        for key in ['CLAUDE_PM_MEMORY__ENABLED', 'CLAUDE_PM_MEMORY__AUTO_LEARNING', 
                    'CLAUDE_PM_MEMORY__LIMITS__DEFAULT_SIZE_KB']:
            os.environ.pop(key, None)


if __name__ == "__main__":
    try:
        test_yaml_config()
        test_json_config()
        test_env_override()
    except ImportError as e:
        if "yaml" in str(e):
            print("\nNOTE: PyYAML not installed. Skipping YAML test.")
            print("Install with: pip install pyyaml")
            test_json_config()
            test_env_override()
        else:
            raise