#!/usr/bin/env python3
"""
Demonstration of the smart dependency checking system.

This script showcases how the smart dependency checking works in practice,
demonstrating the key features:
- Only checks when agents change
- Caches results for efficiency
- Prompts only in interactive environments
- Respects CI/Docker contexts
"""

import sys
import os
import json
import tempfile
import shutil
import time
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.utils.environment_context import EnvironmentContext
from claude_mpm.utils.agent_dependency_loader import AgentDependencyLoader
from claude_mpm.utils.dependency_cache import SmartDependencyChecker


def demo_scenario_1():
    """Scenario 1: First run with new agents."""
    print("\n" + "=" * 80)
    print("SCENARIO 1: First Run with New Agents")
    print("=" * 80)
    print("\nContext: User just deployed new agents and runs claude-mpm for the first time")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        agents_dir, cleanup = setup_demo_environment(tmpdir)
        try:
            loader = AgentDependencyLoader()
            smart_checker = SmartDependencyChecker()
            
            print("\n🔍 Checking if agents have changed...")
            has_changed, deployment_hash = loader.has_agents_changed()
            print(f"   → Agents changed: {has_changed} (first run, no previous state)")
            
            print("\n📦 Checking dependencies...")
            results, was_cached = smart_checker.get_or_check_dependencies(loader)
            print(f"   → Used cache: {was_cached}")
            print(f"   → Found {results['summary']['total_agents']} agents")
            print(f"   → Missing dependencies: {len(results['summary'].get('missing_python', []))}")
            
            print("\n💾 State saved for next run")
            print("   → Deployment hash cached")
            print("   → Dependency results cached")
        finally:
            cleanup()


def demo_scenario_2():
    """Scenario 2: Second run with no changes."""
    print("\n" + "=" * 80)
    print("SCENARIO 2: Second Run with No Changes")
    print("=" * 80)
    print("\nContext: User runs claude-mpm again without changing any agents")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        agents_dir, cleanup = setup_demo_environment(tmpdir)
        try:
            loader = AgentDependencyLoader()
            smart_checker = SmartDependencyChecker()
            
            # First run to establish baseline
            print("\n📝 Initial run to establish baseline...")
            loader.has_agents_changed()
            results1, _ = smart_checker.get_or_check_dependencies(loader)
            
            # Second run - should use cache
            print("\n🔄 Running again (no changes)...")
            print("\n🔍 Checking if agents have changed...")
            has_changed, deployment_hash = loader.has_agents_changed()
            print(f"   → Agents changed: {has_changed}")
            
            if not has_changed:
                print("\n✨ No changes detected - using cached results")
                cached_results = smart_checker.cache.get(deployment_hash)
                if cached_results:
                    print("   → Skipping dependency check (cache hit)")
                    print("   → Startup time improved! ⚡")
        finally:
            cleanup()


def demo_scenario_3():
    """Scenario 3: Agent modification triggers recheck."""
    print("\n" + "=" * 80)
    print("SCENARIO 3: Agent Modification Triggers Recheck")
    print("=" * 80)
    print("\nContext: User modifies an agent file")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        agents_dir, cleanup = setup_demo_environment(tmpdir)
        try:
            loader = AgentDependencyLoader()
            smart_checker = SmartDependencyChecker()
            
            # Initial check
            print("\n📝 Initial check...")
            has_changed1, hash1 = loader.has_agents_changed()
            smart_checker.get_or_check_dependencies(loader)
            
            # Modify an agent
            print("\n✏️  Modifying agent file...")
            agent_file = agents_dir / "research.md"
            agent_file.write_text("# Research Agent\n\nModified content with new capabilities")
            
            # Check again
            print("\n🔍 Checking after modification...")
            has_changed2, hash2 = loader.has_agents_changed()
            print(f"   → Agents changed: {has_changed2}")
            print(f"   → Hash changed: {hash1[:8]}... → {hash2[:8]}...")
            
            if has_changed2:
                print("\n📦 Re-checking dependencies due to changes...")
                results, was_cached = smart_checker.get_or_check_dependencies(loader)
                print(f"   → Fresh check performed (cached: {was_cached})")
        finally:
            cleanup()


def demo_scenario_4():
    """Scenario 4: Environment-aware prompting."""
    print("\n" + "=" * 80)
    print("SCENARIO 4: Environment-Aware Prompting")
    print("=" * 80)
    print("\nContext: Different behavior in different environments")
    
    # Current environment
    context = EnvironmentContext.detect_execution_context()
    can_prompt, reason = EnvironmentContext.should_prompt_for_dependencies()
    
    print(f"\n🖥️  Current Environment:")
    print(f"   → TTY: {context['is_tty']}")
    print(f"   → CI: {context['is_ci']}")
    print(f"   → Docker: {context['is_docker']}")
    print(f"   → Interactive: {context['is_interactive']}")
    
    print(f"\n💬 Prompting Decision:")
    print(f"   → Will prompt: {can_prompt}")
    print(f"   → Reason: {reason}")
    
    # Simulate different environments
    print("\n🔬 Simulating Different Environments:")
    
    # CI environment
    os.environ['CI'] = 'true'
    can_prompt_ci, reason_ci = EnvironmentContext.should_prompt_for_dependencies()
    print(f"\n   In CI Environment:")
    print(f"   → Will prompt: {can_prompt_ci}")
    print(f"   → Reason: {reason_ci}")
    del os.environ['CI']
    
    # Force prompt
    can_prompt_force, reason_force = EnvironmentContext.should_prompt_for_dependencies(force_prompt=True)
    print(f"\n   With --force-prompt flag:")
    print(f"   → Will prompt: {can_prompt_force}")
    print(f"   → Reason: {reason_force}")


def demo_scenario_5():
    """Scenario 5: Performance comparison."""
    print("\n" + "=" * 80)
    print("SCENARIO 5: Performance Comparison")
    print("=" * 80)
    print("\nContext: Comparing startup time with and without smart checking")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        agents_dir, cleanup = setup_demo_environment(tmpdir, num_agents=10)
        try:
            loader = AgentDependencyLoader()
            smart_checker = SmartDependencyChecker()
            
            # First run - full check
            print("\n⏱️  First Run (Full Check):")
            start_time = time.time()
            loader.discover_deployed_agents()
            loader.load_agent_dependencies()
            results = loader.analyze_dependencies()
            first_run_time = time.time() - start_time
            print(f"   → Time taken: {first_run_time:.3f}s")
            print(f"   → Checked {results['summary']['total_agents']} agents")
            
            # Save state
            deployment_hash = loader.calculate_deployment_hash()
            loader.mark_deployment_checked(deployment_hash, results)
            smart_checker.cache.set(deployment_hash, results)
            
            # Second run - with smart checking
            print("\n⏱️  Second Run (Smart Checking):")
            start_time = time.time()
            
            # Check if we need to run
            has_changed, current_hash = loader.has_agents_changed()
            if not has_changed:
                # Use cached results
                cached = smart_checker.cache.get(current_hash)
                if cached:
                    results = cached
            
            second_run_time = time.time() - start_time
            print(f"   → Time taken: {second_run_time:.3f}s")
            print(f"   → Used cache: {not has_changed and cached is not None}")
            
            if first_run_time > 0:
                speedup = first_run_time / second_run_time
                print(f"\n🚀 Performance Improvement: {speedup:.1f}x faster!")
        finally:
            cleanup()


def setup_demo_environment(tmpdir, num_agents=3):
    """Set up a demo environment with test agents."""
    test_dir = Path(tmpdir)
    
    # Store original directory before any changes
    original_cwd = os.getcwd()
    
    # Create .claude/agents directory
    agents_dir = test_dir / ".claude" / "agents"
    agents_dir.mkdir(parents=True)
    
    # Create .claude-mpm/agents directory
    mpm_agents_dir = test_dir / ".claude-mpm" / "agents"
    mpm_agents_dir.mkdir(parents=True)
    
    # Create test agents
    test_agents = {
        "research": {
            "dependencies": {
                "python": ["beautifulsoup4", "requests", "lxml"],
                "system": ["git"]
            }
        },
        "engineer": {
            "dependencies": {
                "python": ["pytest", "black", "mypy"],
                "system": ["docker", "npm"]
            }
        },
        "qa": {
            "dependencies": {
                "python": ["pytest", "coverage", "tox"],
                "system": ["git"]
            }
        }
    }
    
    # Deploy agents
    for i, (agent_id, config) in enumerate(test_agents.items()):
        if i >= num_agents:
            break
            
        # Create agent config
        agent_config = {
            "agent_id": agent_id,
            "version": "1.0.0",
            "dependencies": config["dependencies"]
        }
        
        config_path = mpm_agents_dir / f"{agent_id}.json"
        config_path.write_text(json.dumps(agent_config, indent=2))
        
        # Deploy agent markdown
        agent_md_path = agents_dir / f"{agent_id}.md"
        agent_md_path.write_text(f"# {agent_id.title()} Agent\n\nDemo agent for testing")
    
    # Change to test directory
    os.chdir(test_dir)
    
    # Return cleanup function to be called after each scenario
    def cleanup():
        try:
            os.chdir(original_cwd)
        except:
            pass
    
    return agents_dir, cleanup


def main():
    """Run all demonstration scenarios."""
    print("\n" + "🎯 " * 20)
    print("    SMART DEPENDENCY CHECKING DEMONSTRATION")
    print("🎯 " * 20)
    
    print("\nThis demonstration shows how the smart dependency checking system:")
    print("• Only checks dependencies when agents change")
    print("• Caches results for improved performance")
    print("• Prompts only in appropriate environments")
    print("• Respects CI/Docker contexts automatically")
    
    try:
        demo_scenario_1()
        demo_scenario_2()
        demo_scenario_3()
        demo_scenario_4()
        demo_scenario_5()
        
        print("\n" + "=" * 80)
        print("DEMONSTRATION COMPLETE ✅")
        print("=" * 80)
        
        print("\n🎉 Key Benefits:")
        print("• Faster startup when agents haven't changed")
        print("• No annoying prompts in CI/Docker environments")
        print("• Intelligent caching reduces redundant checks")
        print("• User-friendly interactive prompts when appropriate")
        print("• Respects user preferences with --no-prompt flag")
        
    except Exception as e:
        print(f"\n❌ DEMO FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()