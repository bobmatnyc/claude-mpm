#!/usr/bin/env python3
"""Test that memory injection only loads memories for deployed agents."""

import logging
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.core.framework_loader import FrameworkLoader


def test_memory_deployment_check():
    """Test that memories are only loaded for deployed agents."""
    
    # Set up logging to capture messages
    logging.basicConfig(level=logging.DEBUG)
    
    # Create framework loader
    loader = FrameworkLoader()
    
    # Get deployed agents
    deployed = loader._get_deployed_agents()
    print(f"\n=== Deployed Agents Found ===")
    print(f"Total: {len(deployed)}")
    for agent in sorted(deployed):
        print(f"  - {agent}")
    
    # Check memory files
    print(f"\n=== Memory Files Analysis ===")
    
    # Check user memories
    user_memories_dir = Path.home() / ".claude-mpm" / "memories"
    if user_memories_dir.exists():
        print(f"\nUser memories in {user_memories_dir}:")
        for memory_file in user_memories_dir.glob("*_memories.md"):
            if memory_file.name == "PM_memories.md":
                print(f"  ✓ {memory_file.name} - PM (always loaded)")
                continue
            
            # Extract agent name (remove "_memories" suffix)
            agent_name = memory_file.stem[:-9]
            
            if agent_name in deployed:
                print(f"  ✓ {memory_file.name} - Agent '{agent_name}' is deployed")
            else:
                print(f"  ✗ {memory_file.name} - Agent '{agent_name}' NOT deployed (should be skipped)")
    
    # Check project memories
    project_memories_dir = Path.cwd() / ".claude-mpm" / "memories"
    if project_memories_dir.exists():
        print(f"\nProject memories in {project_memories_dir}:")
        for memory_file in project_memories_dir.glob("*_memories.md"):
            if memory_file.name == "PM_memories.md":
                print(f"  ✓ {memory_file.name} - PM (always loaded)")
                continue
            
            # Extract agent name (remove "_memories" suffix)
            agent_name = memory_file.stem[:-9]
            
            if agent_name in deployed:
                print(f"  ✓ {memory_file.name} - Agent '{agent_name}' is deployed")
            else:
                print(f"  ✗ {memory_file.name} - Agent '{agent_name}' NOT deployed (should be skipped)")
    
    # Now test actual loading with mock content
    print(f"\n=== Testing Actual Load Process ===")
    
    # Mock the PM instructions to avoid loading the full framework
    content = {
        "instructions": "Test instructions"
    }
    
    # Capture log messages
    log_messages = []
    
    class LogCapture:
        def __init__(self, original_logger):
            self.original = original_logger
            
        def info(self, msg):
            log_messages.append(("INFO", msg))
            self.original.info(msg)
            
        def debug(self, msg):
            log_messages.append(("DEBUG", msg))
            self.original.debug(msg)
            
        def error(self, msg):
            log_messages.append(("ERROR", msg))
            self.original.error(msg)
    
    # Wrap the logger
    original_logger = loader.logger
    loader.logger = LogCapture(original_logger)
    
    # Load memories
    loader._load_memory_files(content)
    
    # Analyze log messages
    print("\n=== Log Analysis ===")
    skipped_messages = [msg for level, msg in log_messages if "Skipped" in msg]
    loaded_messages = [msg for level, msg in log_messages if "Loaded" in msg and "memory" in msg.lower()]
    
    print(f"\nSkipped memories ({len(skipped_messages)}):")
    for msg in skipped_messages:
        print(f"  - {msg}")
    
    print(f"\nLoaded memories ({len(loaded_messages)}):")
    for msg in loaded_messages:
        print(f"  - {msg}")
    
    # Verify specific cases
    print(f"\n=== Verification ===")
    
    # Check that non-deployed agents are skipped
    non_deployed_found = False
    for memory_file in list(user_memories_dir.glob("*_memories.md")) + list(project_memories_dir.glob("*_memories.md")):
        if memory_file.name == "PM_memories.md":
            continue
        agent_name = memory_file.stem[:-9]
        if agent_name not in deployed:
            non_deployed_found = True
            # Check that there's a skip message for this agent
            expected_skip = f"{memory_file.name} (agent not deployed)"
            if any(expected_skip in msg for level, msg in log_messages if level == "INFO"):
                print(f"✓ Correctly skipped non-deployed agent: {agent_name}")
            else:
                print(f"✗ Missing skip message for non-deployed agent: {agent_name}")
    
    if not non_deployed_found:
        print("✓ All memory files are for deployed agents (no skipping needed)")
    
    # Check that PM memories are always loaded
    pm_loaded = any("PM memory" in msg for level, msg in log_messages if "Loaded" in msg)
    if pm_loaded:
        print("✓ PM memories were loaded")
    else:
        print("✗ PM memories were NOT loaded (should always be loaded)")
    
    # Check actual content
    if "actual_memories" in content:
        print(f"✓ PM memories injected into content ({len(content['actual_memories'])} bytes)")
    
    if "agent_memories" in content:
        print(f"✓ Agent memories injected into content:")
        for agent_name in content["agent_memories"]:
            print(f"  - {agent_name}: {len(content['agent_memories'][agent_name])} bytes")
    
    print("\n=== Test Complete ===")


if __name__ == "__main__":
    test_memory_deployment_check()