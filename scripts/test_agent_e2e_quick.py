#!/usr/bin/env python3
"""
Quick end-to-end test to verify agent functionality works properly
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src'))

from claude_mpm.agents.agent_loader import AgentLoader

def test_e2e():
    """Run a quick end-to-end test of agent functionality"""
    print("=== Quick Agent E2E Test ===\n")
    
    try:
        # 1. Initialize loader
        print("1. Initializing AgentLoader...")
        loader = AgentLoader()
        print("   ✓ AgentLoader initialized successfully")
        
        # 2. List available agents
        print("\n2. Listing available agents...")
        agents = loader.list_agents()
        print(f"   ✓ Found {len(agents)} agents:")
        for agent in agents[:3]:
            print(f"     - {agent['id']}: {agent['name']}")
        
        # 3. Load a specific agent
        print("\n3. Loading engineer agent...")
        engineer = loader.get_agent("engineer_agent")
        if engineer:
            print(f"   ✓ Loaded engineer agent v{engineer.get('agent_version')}")
            print(f"     - Type: {engineer.get('agent_type')}")
            print(f"     - Metadata: {engineer.get('metadata', {}).get('name')}")
        
        # 4. Get agent prompt
        print("\n4. Getting agent prompt...")
        prompt = loader.get_agent_prompt("engineer_agent")
        if prompt:
            print(f"   ✓ Retrieved prompt ({len(prompt)} characters)")
            print(f"     - First 100 chars: {prompt[:100]}...")
        
        # 5. Test agent metadata retrieval
        print("\n5. Getting agent metadata...")
        metadata = loader.get_agent_metadata("qa_agent")
        if metadata:
            print(f"   ✓ Retrieved metadata for QA agent")
            print(f"     - Name: {metadata.get('name')}")
            desc = metadata.get('description', 'No description')
            print(f"     - Description: {desc[:50] if desc else 'N/A'}...")
        
        # 6. Check metrics
        print("\n6. Checking metrics...")
        metrics = loader.get_metrics()
        print(f"   ✓ Metrics available:")
        print(f"     - Agents loaded: {metrics.get('agents_loaded')}")
        print(f"     - Validation failures: {metrics.get('validation_failures')}")
        print(f"     - Initialization time: {metrics.get('initialization_time_ms'):.2f}ms")
        
        print("\n✓ ALL E2E TESTS PASSED!")
        print("Agent functionality is working correctly.")
        
    except Exception as e:
        print(f"\n✗ E2E TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    success = test_e2e()
    sys.exit(0 if success else 1)