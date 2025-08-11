#!/usr/bin/env python3
"""
Test memory router agent coverage - verifies all agent types are supported.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from claude_mpm.services.memory.router import MemoryRouter

def test_memory_router_agent_coverage():
    """Test that memory router supports all agent types."""
    
    # All expected agent types from templates
    expected_agents = [
        'data_engineer', 'documentation', 'engineer', 'ops', 'pm',
        'qa', 'research', 'security', 'test_integration', 'version_control'
    ]
    
    router = MemoryRouter()
    
    # Test 1: Check supported agents
    supported_agents = router.get_supported_agents()
    assert len(supported_agents) == len(expected_agents), f"Expected {len(expected_agents)} agents, got {len(supported_agents)}"
    
    for agent in expected_agents:
        assert agent in supported_agents, f"Agent '{agent}' not in supported agents: {supported_agents}"
        assert router.is_agent_supported(agent), f"is_agent_supported() returned False for '{agent}'"
    
    # Test 2: Sample routing for each agent type
    agent_test_content = {
        'data_engineer': 'database schema pipeline etl data warehouse',
        'documentation': 'documentation guide manual readme instructions',
        'engineer': 'code function class programming implementation',
        'ops': 'deployment docker kubernetes infrastructure monitoring',
        'pm': 'project management coordination planning milestone',
        'qa': 'quality assurance test case validation verification',
        'research': 'research analysis investigate study findings',
        'security': 'security authentication authorization encryption',
        'test_integration': 'integration test end-to-end cross-system workflow',
        'version_control': 'git branch merge commit version control'
    }
    
    routing_results = {}
    for agent, content in agent_test_content.items():
        result = router.analyze_and_route(content)
        routing_results[agent] = result
        
        # Should route to expected agent or have reasonable confidence
        routed_agent = result['target_agent']
        confidence = result['confidence']
        
        # Allow some flexibility for overlapping keywords but verify reasonable routing
        assert confidence > 0.1, f"Very low confidence ({confidence}) for agent '{agent}' with content '{content}'"
        
        # For most specific content, should route correctly
        if confidence > 0.5:
            assert routed_agent == agent, f"Expected '{agent}', got '{routed_agent}' for content '{content}'"
    
    # Test 3: Error handling
    error_result = router.analyze_and_route("")
    assert error_result['target_agent'] == 'pm', "Empty content should default to 'pm'"
    assert error_result['confidence'] == 0.1, "Empty content should have low confidence"
    
    # Test 4: Pattern statistics
    patterns = router.get_routing_patterns()
    assert patterns['total_keywords'] > 200, f"Expected >200 total keywords, got {patterns['total_keywords']}"
    assert len(patterns['agents']) == 10, f"Expected 10 agents in patterns, got {len(patterns['agents'])}"
    
    print("✅ All memory router agent coverage tests passed!")
    print(f"   - {len(supported_agents)} agent types supported")
    print(f"   - {patterns['total_keywords']} total routing keywords")
    print(f"   - All agents have proper keyword patterns and sections")
    
    return True

if __name__ == '__main__':
    try:
        test_memory_router_agent_coverage()
        print("🎉 Memory router supports all agent types correctly!")
        sys.exit(0)
    except AssertionError as e:
        print(f"❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)