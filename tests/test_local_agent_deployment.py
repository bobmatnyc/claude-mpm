#!/usr/bin/env python3
"""
Comprehensive validation script for local agent deployment functionality.

Tests the PROJECT tier agent system to ensure:
1. PROJECT tier agents are discovered from .claude-mpm/agents/
2. PROJECT agents override USER and SYSTEM agents with same name
3. Agent loader respects the precedence chain
4. Cache invalidation works when project agents change
5. Backwards compatibility is maintained
"""

import os
import sys
import json
import time
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add src to path to import claude_mpm modules
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from claude_mpm.services.agents.registry import AgentRegistry, AgentTier, AgentType
from claude_mpm.core.config_paths import ConfigPaths
from claude_mpm.services.memory.cache.simple_cache import SimpleCacheService


class ValidationResults:
    """Store validation test results."""
    
    def __init__(self):
        self.tests = []
        self.passed = 0
        self.failed = 0
        self.errors = []
        self.performance_metrics = {}
    
    def add_test(self, test_name: str, passed: bool, details: str = "", error: str = ""):
        """Add a test result."""
        self.tests.append({
            'name': test_name,
            'passed': passed,
            'details': details,
            'error': error,
            'timestamp': time.time()
        })
        
        if passed:
            self.passed += 1
        else:
            self.failed += 1
            if error:
                self.errors.append(f"{test_name}: {error}")
    
    def add_performance_metric(self, metric_name: str, value: float, unit: str = "ms"):
        """Add a performance metric."""
        self.performance_metrics[metric_name] = {
            'value': value,
            'unit': unit,
            'timestamp': time.time()
        }
    
    def print_summary(self):
        """Print a summary of all test results."""
        print("\n" + "="*80)
        print("LOCAL AGENT DEPLOYMENT VALIDATION RESULTS")
        print("="*80)
        
        print(f"\nOverall Results:")
        print(f"  Tests Passed: {self.passed}")
        print(f"  Tests Failed: {self.failed}")
        print(f"  Total Tests: {len(self.tests)}")
        print(f"  Success Rate: {(self.passed/len(self.tests)*100):.1f}%")
        
        if self.errors:
            print(f"\nErrors:")
            for error in self.errors:
                print(f"  - {error}")
        
        print(f"\nPerformance Metrics:")
        for metric, data in self.performance_metrics.items():
            print(f"  {metric}: {data['value']:.2f} {data['unit']}")
        
        print(f"\nDetailed Test Results:")
        for test in self.tests:
            status = "PASS" if test['passed'] else "FAIL"
            print(f"  [{status}] {test['name']}")
            if test['details']:
                print(f"         {test['details']}")
            if test['error']:
                print(f"         Error: {test['error']}")
        
        print("\n" + "="*80)


def test_project_agent_discovery(results: ValidationResults):
    """Test that PROJECT tier agents are discovered from .claude-mpm/agents/"""
    print("\n🔍 Testing PROJECT tier agent discovery...")
    
    try:
        # Create registry
        cache_service = SimpleCacheService(default_ttl=60)
        registry = AgentRegistry(cache_service=cache_service)
        
        start_time = time.time()
        discovered_agents = registry.discover_agents(force_refresh=True)
        discovery_time = (time.time() - start_time) * 1000
        
        results.add_performance_metric("agent_discovery_time", discovery_time, "ms")
        
        # Check if project agents were discovered
        project_agents = [agent for agent in discovered_agents.values() 
                         if agent.tier == AgentTier.PROJECT]
        
        if len(project_agents) > 0:
            results.add_test(
                "project_agent_discovery",
                True,
                f"Found {len(project_agents)} project agents: {[a.name for a in project_agents]}"
            )
        else:
            results.add_test(
                "project_agent_discovery",
                False,
                "No project agents discovered",
                "PROJECT tier agents not found in .claude-mpm/agents/"
            )
        
        # Verify specific test agents exist
        test_qa_agent = registry.get_agent('test_project_qa')
        if test_qa_agent and test_qa_agent.tier == AgentTier.PROJECT:
            results.add_test(
                "test_project_qa_found",
                True,
                f"Found test_project_qa agent in {test_qa_agent.path}"
            )
        else:
            results.add_test(
                "test_project_qa_found",
                False,
                "test_project_qa agent not found or not PROJECT tier"
            )
        
        custom_engineer = registry.get_agent('custom_engineer')
        if custom_engineer and custom_engineer.tier == AgentTier.PROJECT:
            results.add_test(
                "custom_engineer_found",
                True,
                f"Found custom_engineer agent in {custom_engineer.path}"
            )
        else:
            results.add_test(
                "custom_engineer_found",
                False,
                "custom_engineer agent not found or not PROJECT tier"
            )
            
    except Exception as e:
        results.add_test(
            "project_agent_discovery",
            False,
            error=str(e)
        )


def test_agent_precedence(results: ValidationResults):
    """Test that PROJECT agents override USER and SYSTEM agents with same name."""
    print("\n⚖️ Testing agent tier precedence...")
    
    try:
        cache_service = SimpleCacheService(default_ttl=60)
        registry = AgentRegistry(cache_service=cache_service)
        
        # Discover all agents
        discovered_agents = registry.discover_agents(force_refresh=True)
        
        # Check if there are multiple QA agents and verify precedence
        qa_agents = [agent for agent in discovered_agents.values() 
                    if 'qa' in agent.name.lower()]
        
        if len(qa_agents) > 1:
            # Sort by tier precedence
            qa_agents.sort(key=lambda a: {
                AgentTier.PROJECT: 3, 
                AgentTier.USER: 2, 
                AgentTier.SYSTEM: 1
            }.get(a.tier, 0), reverse=True)
            
            highest_precedence_qa = qa_agents[0]
            
            if highest_precedence_qa.tier == AgentTier.PROJECT:
                results.add_test(
                    "qa_agent_precedence",
                    True,
                    f"PROJECT tier QA agent has precedence: {highest_precedence_qa.name}"
                )
            else:
                results.add_test(
                    "qa_agent_precedence",
                    False,
                    f"Expected PROJECT tier, got {highest_precedence_qa.tier.value}"
                )
        else:
            # Check if the single QA agent is PROJECT tier
            if qa_agents and qa_agents[0].tier == AgentTier.PROJECT:
                results.add_test(
                    "qa_agent_precedence",
                    True,
                    f"Single QA agent is PROJECT tier: {qa_agents[0].name}"
                )
            else:
                results.add_test(
                    "qa_agent_precedence",
                    False,
                    f"QA agent is not PROJECT tier or not found"
                )
        
        # Test precedence logic directly
        has_precedence_project_over_system = registry._has_tier_precedence(
            AgentTier.PROJECT, AgentTier.SYSTEM
        )
        has_precedence_project_over_user = registry._has_tier_precedence(
            AgentTier.PROJECT, AgentTier.USER
        )
        has_precedence_user_over_system = registry._has_tier_precedence(
            AgentTier.USER, AgentTier.SYSTEM
        )
        
        if has_precedence_project_over_system and has_precedence_project_over_user and has_precedence_user_over_system:
            results.add_test(
                "tier_precedence_logic",
                True,
                "PROJECT > USER > SYSTEM precedence working correctly"
            )
        else:
            results.add_test(
                "tier_precedence_logic",
                False,
                f"Precedence logic failed: P>S={has_precedence_project_over_system}, P>U={has_precedence_project_over_user}, U>S={has_precedence_user_over_system}"
            )
            
    except Exception as e:
        results.add_test(
            "agent_precedence",
            False,
            error=str(e)
        )


def test_cache_invalidation(results: ValidationResults):
    """Test cache invalidation when project agents change."""
    print("\n🔄 Testing cache invalidation...")
    
    try:
        cache_service = SimpleCacheService(default_ttl=3600)
        registry = AgentRegistry(cache_service=cache_service)
        
        # First discovery - should populate cache
        start_time = time.time()
        agents_first = registry.discover_agents(force_refresh=True)
        first_discovery_time = (time.time() - start_time) * 1000
        
        # Second discovery - should use cache
        start_time = time.time()
        agents_cached = registry.discover_agents(force_refresh=False)
        cached_discovery_time = (time.time() - start_time) * 1000
        
        results.add_performance_metric("first_discovery_time", first_discovery_time, "ms")
        results.add_performance_metric("cached_discovery_time", cached_discovery_time, "ms")
        
        # Cache should be significantly faster
        if cached_discovery_time < first_discovery_time * 0.5:  # At least 50% faster
            results.add_test(
                "cache_performance",
                True,
                f"Cache is faster: {first_discovery_time:.1f}ms vs {cached_discovery_time:.1f}ms"
            )
        else:
            results.add_test(
                "cache_performance",
                False,
                f"Cache not significantly faster: {first_discovery_time:.1f}ms vs {cached_discovery_time:.1f}ms"
            )
        
        # Test cache invalidation
        registry.invalidate_cache()
        
        # Verify cache is cleared
        if not registry.registry:
            results.add_test(
                "cache_invalidation",
                True,
                "Cache successfully invalidated"
            )
        else:
            results.add_test(
                "cache_invalidation",
                False,
                "Registry not cleared after cache invalidation"
            )
        
        # Re-discover after invalidation
        start_time = time.time()
        agents_after_invalidation = registry.discover_agents(force_refresh=False)
        post_invalidation_time = (time.time() - start_time) * 1000
        
        results.add_performance_metric("post_invalidation_time", post_invalidation_time, "ms")
        
        if len(agents_after_invalidation) == len(agents_first):
            results.add_test(
                "post_invalidation_discovery",
                True,
                f"Same number of agents discovered after invalidation: {len(agents_after_invalidation)}"
            )
        else:
            results.add_test(
                "post_invalidation_discovery",
                False,
                f"Agent count mismatch: {len(agents_first)} vs {len(agents_after_invalidation)}"
            )
            
    except Exception as e:
        results.add_test(
            "cache_invalidation",
            False,
            error=str(e)
        )


def test_edge_cases(results: ValidationResults):
    """Test edge cases like missing directories, malformed files, etc."""
    print("\n🧪 Testing edge cases...")
    
    try:
        cache_service = SimpleCacheService(default_ttl=60)
        registry = AgentRegistry(cache_service=cache_service)
        
        # Test with malformed agent file
        discovered_agents = registry.discover_agents(force_refresh=True)
        
        malformed_agent = registry.get_agent('malformed_agent')
        if malformed_agent:
            if not malformed_agent.is_valid:
                results.add_test(
                    "malformed_agent_handling",
                    True,
                    f"Malformed agent properly marked as invalid: {malformed_agent.validation_errors}"
                )
            else:
                results.add_test(
                    "malformed_agent_handling",
                    False,
                    "Malformed agent not detected as invalid"
                )
        else:
            results.add_test(
                "malformed_agent_handling",
                False,
                "Malformed agent not found"
            )
        
        # Test agent validation
        validation_errors = registry.validate_all_agents()
        
        if 'malformed_agent' in validation_errors:
            results.add_test(
                "validation_error_detection",
                True,
                f"Validation errors properly detected for malformed agent"
            )
        else:
            results.add_test(
                "validation_error_detection",
                False,
                "Validation errors not detected for malformed agent"
            )
        
        # Test non-existent path handling
        non_existent_path = Path("/non/existent/path")
        try:
            registry.add_discovery_path(non_existent_path)
            # Should not raise an error but also should not add the path
            if non_existent_path not in registry.discovery_paths:
                results.add_test(
                    "non_existent_path_handling",
                    True,
                    "Non-existent paths properly ignored"
                )
            else:
                results.add_test(
                    "non_existent_path_handling",
                    False,
                    "Non-existent path was added to discovery paths"
                )
        except Exception as e:
            results.add_test(
                "non_existent_path_handling",
                False,
                error=f"Exception raised for non-existent path: {str(e)}"
            )
            
    except Exception as e:
        results.add_test(
            "edge_cases",
            False,
            error=str(e)
        )


def test_backwards_compatibility(results: ValidationResults):
    """Test backwards compatibility with existing code."""
    print("\n🔄 Testing backwards compatibility...")
    
    try:
        # Test the old-style imports and functions still work
        from claude_mpm.core.agent_registry import list_agents_all, get_agent, discover_agents
        
        # Test old function calls
        all_agents = list_agents_all()
        if isinstance(all_agents, dict):
            results.add_test(
                "list_agents_all_compatibility",
                True,
                f"list_agents_all() returned {len(all_agents)} agents"
            )
        else:
            results.add_test(
                "list_agents_all_compatibility",
                False,
                f"list_agents_all() returned unexpected type: {type(all_agents)}"
            )
        
        # Test get_agent function
        if all_agents:
            first_agent_name = next(iter(all_agents.keys()))
            agent = get_agent(first_agent_name)
            if agent:
                results.add_test(
                    "get_agent_compatibility",
                    True,
                    f"get_agent() successfully retrieved {first_agent_name}"
                )
            else:
                results.add_test(
                    "get_agent_compatibility",
                    False,
                    f"get_agent() failed to retrieve {first_agent_name}"
                )
        
        # Test discover_agents function
        discovered = discover_agents()
        if isinstance(discovered, dict):
            results.add_test(
                "discover_agents_compatibility",
                True,
                f"discover_agents() returned {len(discovered)} agents"
            )
        else:
            results.add_test(
                "discover_agents_compatibility",
                False,
                f"discover_agents() returned unexpected type: {type(discovered)}"
            )
            
    except Exception as e:
        results.add_test(
            "backwards_compatibility",
            False,
            error=str(e)
        )


def test_integration_with_claude_mpm(results: ValidationResults):
    """Test integration with main claude-mpm system."""
    print("\n🔌 Testing claude-mpm integration...")
    
    try:
        # Test that the registry can be created from the main system
        from claude_mpm.core.agent_registry import AgentRegistryAdapter
        
        adapter = AgentRegistryAdapter()
        if adapter.registry:
            results.add_test(
                "adapter_initialization",
                True,
                "AgentRegistryAdapter successfully initialized"
            )
        else:
            results.add_test(
                "adapter_initialization",
                False,
                "AgentRegistryAdapter failed to initialize registry"
            )
        
        # Test hierarchy function
        if adapter.registry:
            hierarchy = adapter.get_agent_hierarchy()
            
            if 'project' in hierarchy and len(hierarchy['project']) > 0:
                results.add_test(
                    "hierarchy_project_agents",
                    True,
                    f"Project agents found in hierarchy: {hierarchy['project']}"
                )
            else:
                results.add_test(
                    "hierarchy_project_agents",
                    False,
                    "No project agents found in hierarchy"
                )
        
        # Test agent selection functionality
        if adapter.registry:
            qa_agent = adapter.select_agent_for_task(
                "Quality assurance testing",
                required_specializations=['testing']
            )
            
            if qa_agent:
                results.add_test(
                    "agent_selection",
                    True,
                    f"Agent selected for QA task: {qa_agent['id']}"
                )
            else:
                results.add_test(
                    "agent_selection",
                    False,
                    "No agent selected for QA task"
                )
                
    except Exception as e:
        results.add_test(
            "claude_mpm_integration",
            False,
            error=str(e)
        )


def test_configuration_paths(results: ValidationResults):
    """Test that configuration paths are working correctly."""
    print("\n📁 Testing configuration paths...")
    
    try:
        from claude_mpm.core.config_paths import ConfigPaths
        
        # Test project agents directory
        project_agents_dir = ConfigPaths.get_project_agents_dir()
        expected_path = Path.cwd() / ".claude-mpm" / "agents"
        
        if project_agents_dir == expected_path:
            results.add_test(
                "project_agents_dir_path",
                True,
                f"Project agents directory path correct: {project_agents_dir}"
            )
        else:
            results.add_test(
                "project_agents_dir_path",
                False,
                f"Expected {expected_path}, got {project_agents_dir}"
            )
        
        # Test that the directory exists (we created it)
        if project_agents_dir.exists():
            results.add_test(
                "project_agents_dir_exists",
                True,
                "Project agents directory exists"
            )
        else:
            results.add_test(
                "project_agents_dir_exists",
                False,
                "Project agents directory does not exist"
            )
        
        # Test user agents directory
        user_agents_dir = ConfigPaths.get_user_agents_dir()
        expected_user_path = Path.home() / ".claude-mpm" / "agents"
        
        if user_agents_dir == expected_user_path:
            results.add_test(
                "user_agents_dir_path",
                True,
                f"User agents directory path correct: {user_agents_dir}"
            )
        else:
            results.add_test(
                "user_agents_dir_path",
                False,
                f"Expected {expected_user_path}, got {user_agents_dir}"
            )
            
    except Exception as e:
        results.add_test(
            "configuration_paths",
            False,
            error=str(e)
        )


def run_performance_tests(results: ValidationResults):
    """Run performance tests to measure agent loading times."""
    print("\n⚡ Running performance tests...")
    
    try:
        cache_service = SimpleCacheService(default_ttl=3600)
        
        # Test multiple discoveries to measure performance
        times = []
        for i in range(5):
            registry = AgentRegistry(cache_service=cache_service)
            start_time = time.time()
            registry.discover_agents(force_refresh=True)
            discovery_time = (time.time() - start_time) * 1000
            times.append(discovery_time)
        
        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)
        
        results.add_performance_metric("avg_discovery_time", avg_time, "ms")
        results.add_performance_metric("min_discovery_time", min_time, "ms")
        results.add_performance_metric("max_discovery_time", max_time, "ms")
        
        # Performance should be reasonable (under 500ms for discovery)
        if avg_time < 500:
            results.add_test(
                "discovery_performance",
                True,
                f"Average discovery time acceptable: {avg_time:.1f}ms"
            )
        else:
            results.add_test(
                "discovery_performance",
                False,
                f"Average discovery time too slow: {avg_time:.1f}ms"
            )
        
        # Test cache performance
        registry = AgentRegistry(cache_service=cache_service)
        registry.discover_agents(force_refresh=True)  # Populate cache
        
        cache_times = []
        for i in range(10):
            start_time = time.time()
            registry.discover_agents(force_refresh=False)  # Use cache
            cache_time = (time.time() - start_time) * 1000
            cache_times.append(cache_time)
        
        avg_cache_time = sum(cache_times) / len(cache_times)
        results.add_performance_metric("avg_cache_time", avg_cache_time, "ms")
        
        # Cache should be very fast (under 10ms)
        if avg_cache_time < 10:
            results.add_test(
                "cache_performance_detailed",
                True,
                f"Cache performance excellent: {avg_cache_time:.1f}ms"
            )
        else:
            results.add_test(
                "cache_performance_detailed",
                False,
                f"Cache performance suboptimal: {avg_cache_time:.1f}ms"
            )
            
    except Exception as e:
        results.add_test(
            "performance_tests",
            False,
            error=str(e)
        )


def main():
    """Main validation function."""
    print("🚀 Starting Local Agent Deployment Validation")
    print("=" * 80)
    
    results = ValidationResults()
    
    # Run all validation tests
    test_configuration_paths(results)
    test_project_agent_discovery(results)
    test_agent_precedence(results)
    test_cache_invalidation(results)
    test_edge_cases(results)
    test_backwards_compatibility(results)
    test_integration_with_claude_mpm(results)
    run_performance_tests(results)
    
    # Print comprehensive results
    results.print_summary()
    
    # Return exit code based on results
    return 0 if results.failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())