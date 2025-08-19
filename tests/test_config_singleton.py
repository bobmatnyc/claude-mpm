#!/usr/bin/env python3
"""Test script to verify Config singleton implementation."""

import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.core.config import Config

# Enable debug logging to see singleton behavior
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_singleton_pattern():
    """Test that Config follows singleton pattern."""
    print("\n=== Testing Config Singleton Pattern ===\n")
    
    # Create first instance
    print("Creating first Config instance...")
    config1 = Config()
    
    # Create second instance
    print("\nCreating second Config instance...")
    config2 = Config()
    
    # Create third instance with different parameters
    print("\nCreating third Config instance with different parameters...")
    config3 = Config(config={"test": "value"})
    
    # Verify they are the same instance
    print("\n=== Verification ===")
    assert config1 is config2, "config1 and config2 should be the same instance"
    assert config2 is config3, "config2 and config3 should be the same instance"
    assert config1 is config2 is config3, "All three should be the same instance"
    print(f"config1 is config2: {config1 is config2}")
    print(f"config2 is config3: {config2 is config3}")
    print(f"All three are same instance: {config1 is config2 is config3}")
    
    # Verify configuration is shared
    config1.set("test_key", "test_value")
    print(f"\nAfter setting test_key in config1:")
    assert config2.get('test_key') == "test_value", "config2 should share config1's data"
    assert config3.get('test_key') == "test_value", "config3 should share config1's data"
    print(f"config2.get('test_key'): {config2.get('test_key')}")
    print(f"config3.get('test_key'): {config3.get('test_key')}")
    
    # Test reset functionality
    print("\n=== Testing Reset ===")
    print("Resetting singleton...")
    Config.reset_singleton()
    
    print("Creating new Config instance after reset...")
    config4 = Config()
    
    assert config4 is not config1, "config4 should be a new instance after reset"
    assert config4.get('test_key') is None, "config4 should not have test_key from previous instance"
    print(f"config4 is config1: {config4 is config1}")
    print(f"config4.get('test_key'): {config4.get('test_key')}")
    
    print("\n=== Test Complete ===")

def test_simulate_service_startup():
    """Simulate how services create Config instances during startup."""
    print("\n=== Simulating Service Startup ===\n")
    
    # Reset to start fresh
    Config.reset_singleton()
    
    # Simulate different services creating Config instances
    print("1. ClaudeRunner creating Config...")
    runner_config = Config()
    
    print("\n2. BaseService creating Config...")
    base_service_config = Config()
    
    print("\n3. InteractiveSession creating Config...")
    interactive_config = Config()
    
    print("\n4. ResponseTracker creating Config...")
    tracker_config = Config()
    
    print("\n5. UnifiedAgentRegistry creating Config...")
    registry_config = Config()
    
    print("\n=== Summary ===")
    assert runner_config is base_service_config, "Runner and BaseService should share config"
    assert base_service_config is interactive_config, "BaseService and Interactive should share config"
    assert interactive_config is tracker_config, "Interactive and Tracker should share config"
    assert tracker_config is registry_config, "Tracker and Registry should share config"
    assert runner_config is base_service_config is interactive_config is tracker_config is registry_config, "All should be same instance"
    print(f"All configs are same instance: {runner_config is base_service_config is interactive_config is tracker_config is registry_config}")
    print("Configuration is now loaded ONCE and shared across all services!")

if __name__ == "__main__":
    try:
        test_singleton_pattern()
        test_simulate_service_startup()
        print("\n✅ All tests passed! Configuration singleton is working correctly.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)