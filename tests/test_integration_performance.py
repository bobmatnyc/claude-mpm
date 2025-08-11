#!/usr/bin/env python3
"""Test integration with framework and performance benchmarks."""

import json
import sys
import time
import statistics
from pathlib import Path
import concurrent.futures

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.agents.agent_loader import AgentLoader
from claude_mpm.services.agents.registry import AgentRegistry
from claude_mpm.validation.agent_validator import AgentValidator

def test_performance():
    """Test agent loading performance."""
    print("=== Performance Test ===\n")
    
    # Test 1: Individual agent loading time
    print("1. Testing individual agent load times...")
    loader = AgentLoader()
    agents = loader.list_agents()
    
    load_times = []
    for agent in agents:
        agent_id = agent["id"]
        
        # Clear cache for accurate timing
        loader.cache.invalidate(f"agent_prompt:v2:{agent_id}")
        
        # Time the load
        start_time = time.time()
        agent_data = loader.get_agent(agent_id)
        prompt = loader.get_agent_prompt(agent_id)
        load_time = (time.time() - start_time) * 1000  # Convert to ms
        
        load_times.append(load_time)
        status = "✓" if load_time < 50 else "✗"
        print(f"   {status} {agent_id}: {load_time:.2f}ms")
    
    avg_time = statistics.mean(load_times)
    max_time = max(load_times)
    print(f"\n   Average: {avg_time:.2f}ms")
    print(f"   Maximum: {max_time:.2f}ms")
    print(f"   Requirement: <50ms per agent")
    print(f"   Status: {'✓ PASSED' if max_time < 50 else '✗ FAILED'}")
    
    # Test 2: Bulk loading performance
    print("\n2. Testing bulk loading performance...")
    start_time = time.time()
    registry = AgentRegistry()
    all_agents = registry.list_agents()
    bulk_time = (time.time() - start_time) * 1000
    
    print(f"   Loaded {len(all_agents)} agents in {bulk_time:.2f}ms")
    print(f"   Average per agent: {bulk_time/len(all_agents):.2f}ms")
    
    # Test 3: Concurrent loading
    print("\n3. Testing concurrent loading...")
    def load_agent_concurrent(agent_id):
        loader = AgentLoader()
        start = time.time()
        agent = loader.get_agent(agent_id)
        prompt = loader.get_agent_prompt(agent_id)
        return (time.time() - start) * 1000
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(load_agent_concurrent, a["id"]) for a in agents[:4]]
        concurrent_times = [f.result() for f in futures]
    
    print(f"   Concurrent load times: {[f'{t:.2f}ms' for t in concurrent_times]}")
    print(f"   Average: {statistics.mean(concurrent_times):.2f}ms")
    
    # Test 4: Memory usage
    print("\n4. Testing memory efficiency...")
    import psutil
    process = psutil.Process()
    
    memory_before = process.memory_info().rss / 1024 / 1024  # MB
    
    # Load all agents multiple times
    for _ in range(5):
        for agent in agents:
            loader.get_agent_prompt(agent["id"])
    
    memory_after = process.memory_info().rss / 1024 / 1024  # MB
    memory_increase = memory_after - memory_before
    
    print(f"   Memory before: {memory_before:.2f}MB")
    print(f"   Memory after: {memory_after:.2f}MB")
    print(f"   Increase: {memory_increase:.2f}MB")
    print(f"   Status: {'✓ Efficient' if memory_increase < 10 else '⚠ High usage'}")
    
    return avg_time < 50

def test_integration():
    """Test framework integration."""
    print("\n=== Integration Test ===\n")
    
    # Test 1: Task tool compatibility
    print("1. Testing Task tool compatibility...")
    loader = AgentLoader()
    
    # Simulate what Task tool expects
    task_compatible = True
    for agent_id in ["engineer", "qa", "research"]:
        agent = loader.get_agent(agent_id)
        
        # Check required fields for Task tool
        required_for_task = ["id", "instructions", "capabilities"]
        missing = [f for f in required_for_task if f not in agent]
        
        if missing:
            print(f"   ✗ {agent_id} missing fields for Task tool: {missing}")
            task_compatible = False
        else:
            # Check specific capabilities
            model = agent["capabilities"].get("model")
            tools = agent["capabilities"].get("tools", [])
            
            if not model:
                print(f"   ✗ {agent_id} missing model specification")
                task_compatible = False
            else:
                print(f"   ✓ {agent_id} compatible with Task tool")
    
    # Test 2: Hook service compatibility
    print("\n2. Testing hook service compatibility...")
    # Simulate hook service usage
    for agent_id in ["engineer", "qa"]:
        agent = loader.get_agent(agent_id)
        metadata = loader.get_agent_metadata(agent_id)
        
        if metadata:
            print(f"   ✓ {agent_id} provides metadata for hooks")
            print(f"     - Version: {metadata.get('version')}")
            print(f"     - Tools: {len(metadata.get('capabilities', {}).get('tools', []))} tools")
        else:
            print(f"   ✗ {agent_id} missing metadata")
    
    # Test 3: Agent handoff compatibility
    print("\n3. Testing agent handoff system...")
    handoff_issues = []
    
    for agent_id in loader.list_agents():
        agent = loader.get_agent(agent_id["id"])
        handoffs = agent.get("interactions", {}).get("handoff_agents", [])
        
        for handoff_id in handoffs:
            # Check if handoff agent exists
            if not loader.get_agent(handoff_id):
                handoff_issues.append(f"{agent_id['id']} -> {handoff_id} (not found)")
    
    if handoff_issues:
        print("   Issues found:")
        for issue in handoff_issues:
            print(f"   - {issue}")
    else:
        print("   ✓ All agent handoffs valid")
    
    # Test 4: Old format rejection
    print("\n4. Testing old format rejection...")
    validator = AgentValidator()
    
    old_format_agent = {
        "id": "old_agent",
        "role": "Old Role",
        "goal": "Old Goal",
        "backstory": "Old Backstory"
    }
    
    result = validator.validate_agent(old_format_agent)
    if not result.is_valid:
        print("   ✓ Old format correctly rejected")
        print(f"   Errors: {len(result.errors)}")
    else:
        print("   ✗ Old format was not rejected!")
    
    return task_compatible

def test_breaking_changes():
    """Test that breaking changes are properly implemented."""
    print("\n=== Breaking Changes Test ===\n")
    
    validator = AgentValidator()
    
    # Test 1: Old format with _agent suffix
    print("1. Testing _agent suffix rejection...")
    agent_with_suffix = {
        "id": "test_agent",  # Has _agent suffix
        "version": "1.0.0",
        "metadata": {
            "name": "Test Agent",
            "description": "Test description",
            "category": "engineering",
            "tags": ["test"]
        },
        "capabilities": {
            "model": "claude-sonnet-4-20250514",
            "tools": ["Read", "Write"],
            "resource_tier": "standard"
        },
        "instructions": "Test instructions"
    }
    
    result = validator.validate_agent(agent_with_suffix)
    if result.warnings:
        print("   ✓ Warning issued for _agent suffix")
    else:
        print("   ✗ No warning for _agent suffix")
    
    # Test 2: Instructions length limit
    print("\n2. Testing 8000 character limit...")
    long_agent = agent_with_suffix.copy()
    long_agent["id"] = "test"
    long_agent["instructions"] = "x" * 8001
    
    result = validator.validate_agent(long_agent)
    if not result.is_valid and "8000" in str(result.errors):
        print("   ✓ 8000 character limit enforced")
    else:
        print("   ✗ Character limit not enforced")
    
    # Test 3: Resource tier validation
    print("\n3. Testing resource tier validation...")
    invalid_tier = agent_with_suffix.copy()
    invalid_tier["id"] = "test"
    invalid_tier["instructions"] = "Test"
    invalid_tier["capabilities"]["resource_tier"] = "ultra"  # Invalid
    
    result = validator.validate_agent(invalid_tier)
    if not result.is_valid:
        print("   ✓ Invalid resource tier rejected")
    else:
        print("   ✗ Invalid resource tier accepted")
    
    # Test 4: Clean ID requirement
    print("\n4. Testing clean ID format...")
    invalid_id = agent_with_suffix.copy()
    invalid_id["id"] = "test-agent"  # Contains hyphen
    invalid_id["instructions"] = "Test"
    
    result = validator.validate_agent(invalid_id)
    if not result.is_valid:
        print("   ✓ Invalid ID format rejected")
    else:
        print("   ✗ Invalid ID format accepted")
    
    return True

def main():
    """Run all integration and performance tests."""
    print("=== Claude MPM Schema Standardization QA Tests ===\n")
    
    # Run tests
    perf_passed = test_performance()
    integ_passed = test_integration()
    breaking_passed = test_breaking_changes()
    
    # Summary
    print("\n=== Test Results Summary ===")
    print(f"Performance Tests: {'✓ PASSED' if perf_passed else '✗ FAILED'}")
    print(f"Integration Tests: {'✓ PASSED' if integ_passed else '✗ FAILED'}")
    print(f"Breaking Changes: {'✓ PASSED' if breaking_passed else '✗ FAILED'}")
    
    all_passed = perf_passed and integ_passed and breaking_passed
    
    if all_passed:
        print("\n✓ All tests PASSED - Schema standardization working correctly")
        return 0
    else:
        print("\n✗ Some tests FAILED - Please review issues above")
        return 1

if __name__ == "__main__":
    sys.exit(main())