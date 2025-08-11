#!/usr/bin/env python3
"""
Test script to verify PROJECT tier agent precedence.

This script:
1. Creates a test project agent
2. Verifies it overrides system agents
3. Tests the tier discovery and loading
4. Validates the precedence chain
"""

import os
import sys
import json
import shutil
import tempfile
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from claude_mpm.agents.agent_loader import (
    get_agent_prompt,
    list_agents_by_tier,
    get_agent_tier,
    reload_agents,
    AgentTier
)
from claude_mpm.config.agent_config import (
    AgentConfig,
    get_agent_config,
    set_agent_config,
    reset_agent_config
)
from claude_mpm.core.config_paths import ConfigPaths


def create_test_project_agent(project_dir: Path, agent_name: str = "engineer"):
    """Create a test project agent that overrides the system agent."""
    
    # Create .claude-mpm/agents/templates directory
    agents_dir = project_dir / ConfigPaths.CONFIG_DIR / "agents" / "templates"
    agents_dir.mkdir(parents=True, exist_ok=True)
    
    # Create a custom engineer agent
    agent_data = {
        "agent_id": agent_name,
        "version": "1.0.0",
        "metadata": {
            "name": "Project Engineer Agent",
            "description": "PROJECT OVERRIDE: Custom engineer agent for this project",
            "category": "engineering",
            "tags": ["project", "custom", "override"]
        },
        "capabilities": {
            "model": "claude-sonnet-4-20250514",
            "resource_tier": "standard",
            "tools": ["code_generation", "testing", "debugging"],
            "features": ["project_specific_patterns"]
        },
        "instructions": "# PROJECT ENGINEER AGENT\n\nThis is a PROJECT-level override of the engineer agent.\n\n## Special Instructions\n- This agent is customized for this specific project\n- It has project-specific knowledge and patterns\n- It should take precedence over system and user agents\n\n## Project Context\nYou are working on a specific project with custom requirements.",
        "knowledge": {
            "domains": ["project_specific", "custom_patterns"],
            "context_understanding": "high"
        },
        "interactions": {
            "response_style": "project_optimized",
            "verbosity": "moderate"
        }
    }
    
    agent_file = agents_dir / f"{agent_name}.json"
    with open(agent_file, 'w') as f:
        json.dump(agent_data, f, indent=2)
    
    print(f"✓ Created project agent at: {agent_file}")
    return agent_file


def test_agent_precedence():
    """Test that PROJECT agents override SYSTEM agents."""
    
    print("\n" + "="*60)
    print("TESTING PROJECT AGENT PRECEDENCE")
    print("="*60)
    
    # Create a temporary project directory
    with tempfile.TemporaryDirectory() as temp_dir:
        project_dir = Path(temp_dir)
        
        # Save current directory and switch to temp project
        original_cwd = os.getcwd()
        os.chdir(project_dir)
        
        try:
            print(f"\n1. Testing without project agent...")
            print("-" * 40)
            
            # Reset and reload agents
            reset_agent_config()
            reload_agents()
            
            # Load system engineer agent
            system_prompt = get_agent_prompt("engineer")
            system_tier = get_agent_tier("engineer")
            
            print(f"  Loaded engineer agent from tier: {system_tier}")
            print(f"  Prompt preview: {system_prompt[:100]}...")
            
            assert system_tier == "system", f"Expected system tier, got {system_tier}"
            assert "PROJECT ENGINEER AGENT" not in system_prompt
            print("  ✓ System agent loaded correctly")
            
            print(f"\n2. Creating project agent override...")
            print("-" * 40)
            
            # Create project agent
            agent_file = create_test_project_agent(project_dir)
            
            # Reload agents to pick up the new project agent
            reload_agents()
            
            print(f"\n3. Testing with project agent override...")
            print("-" * 40)
            
            # Load engineer agent again - should now be from PROJECT tier
            project_prompt = get_agent_prompt("engineer")
            project_tier = get_agent_tier("engineer")
            
            print(f"  Loaded engineer agent from tier: {project_tier}")
            print(f"  Prompt preview: {project_prompt[:100]}...")
            
            assert project_tier == "project", f"Expected project tier, got {project_tier}"
            assert "PROJECT ENGINEER AGENT" in project_prompt, "Project agent content not found"
            print("  ✓ Project agent override successful!")
            
            print(f"\n4. Checking agent tier listing...")
            print("-" * 40)
            
            # List agents by tier
            agents_by_tier = list_agents_by_tier()
            
            print("  Agents by tier:")
            for tier, agents in agents_by_tier.items():
                if agents:
                    print(f"    {tier}: {', '.join(agents[:5])}" + 
                          (f" ... ({len(agents)} total)" if len(agents) > 5 else ""))
            
            assert "engineer" in agents_by_tier.get("project", []), \
                "Engineer agent not found in project tier"
            print("  ✓ Agent tier listing correct")
            
            print(f"\n5. Testing configuration system...")
            print("-" * 40)
            
            # Test configuration
            config = get_agent_config()
            enabled_tiers = config.get_enabled_tiers()
            
            print(f"  Enabled tiers: {list(enabled_tiers.keys())}")
            print(f"  Project agents enabled: {config.enable_project_agents}")
            print(f"  Precedence mode: {config.precedence_mode.value}")
            
            assert config.enable_project_agents, "Project agents should be enabled"
            assert "project" in enabled_tiers or project_dir / ConfigPaths.CONFIG_DIR / "agents" in config.additional_paths
            print("  ✓ Configuration system working")
            
            print(f"\n6. Testing hot reload...")
            print("-" * 40)
            
            # Modify the project agent
            agent_data = json.loads(agent_file.read_text())
            agent_data["instructions"] += "\n\n## HOT RELOAD TEST\nThis section was added via hot reload."
            agent_file.write_text(json.dumps(agent_data, indent=2))
            
            # Reload and check
            reload_agents()
            reloaded_prompt = get_agent_prompt("engineer", force_reload=True)
            
            assert "HOT RELOAD TEST" in reloaded_prompt, "Hot reload content not found"
            print("  ✓ Hot reload working")
            
            print("\n" + "="*60)
            print("✅ ALL TESTS PASSED!")
            print("="*60)
            
        except AssertionError as e:
            print(f"\n❌ TEST FAILED: {e}")
            return False
        except Exception as e:
            print(f"\n❌ UNEXPECTED ERROR: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            # Restore original directory
            os.chdir(original_cwd)
            # Reset configuration
            reset_agent_config()
            reload_agents()
    
    return True


def test_environment_configuration():
    """Test environment variable configuration."""
    
    print("\n" + "="*60)
    print("TESTING ENVIRONMENT VARIABLE CONFIGURATION")
    print("="*60)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        custom_dir = Path(temp_dir) / "custom_agents"
        custom_dir.mkdir(parents=True)
        
        # Set environment variables
        os.environ['CLAUDE_MPM_PROJECT_AGENTS_DIR'] = str(custom_dir)
        os.environ['CLAUDE_MPM_AGENT_PRECEDENCE'] = 'strict'
        os.environ['CLAUDE_MPM_AGENT_HOT_RELOAD'] = 'false'
        
        try:
            # Reset and get config
            reset_agent_config()
            config = get_agent_config()
            
            print(f"  Project agents dir from env: {config.project_agents_dir}")
            print(f"  Precedence mode from env: {config.precedence_mode.value}")
            print(f"  Hot reload from env: {config.enable_hot_reload}")
            
            assert str(config.project_agents_dir) == str(custom_dir), \
                "Project agents directory not set from environment"
            assert config.precedence_mode.value == 'strict', \
                "Precedence mode not set from environment"
            assert not config.enable_hot_reload, \
                "Hot reload setting not applied from environment"
            
            print("  ✓ Environment configuration working")
            
        finally:
            # Clean up environment
            for key in ['CLAUDE_MPM_PROJECT_AGENTS_DIR', 
                       'CLAUDE_MPM_AGENT_PRECEDENCE',
                       'CLAUDE_MPM_AGENT_HOT_RELOAD']:
                os.environ.pop(key, None)
            reset_agent_config()
    
    return True


if __name__ == "__main__":
    print("Starting PROJECT agent precedence tests...")
    
    success = True
    
    # Run tests
    if not test_agent_precedence():
        success = False
    
    if not test_environment_configuration():
        success = False
    
    # Final result
    if success:
        print("\n✅ All precedence tests passed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed. Please review the output above.")
        sys.exit(1)