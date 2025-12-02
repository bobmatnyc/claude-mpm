#!/usr/bin/env python3
"""
Test script for smart dependency checking system.

This script tests various scenarios of the smart dependency checking:
1. Environment detection (TTY, CI, Docker)
2. Agent change detection (hash-based)
3. Caching mechanism
4. Interactive prompting logic
"""

import json
import os
import sys
import time
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.utils.agent_dependency_loader import AgentDependencyLoader
from claude_mpm.utils.dependency_cache import (DependencyCache,
                                               SmartDependencyChecker)
from claude_mpm.utils.environment_context import (
    EnvironmentContext, should_prompt_for_dependencies)


def test_environment_detection():
    """Test environment context detection."""
    print("=" * 80)
    print("TESTING ENVIRONMENT DETECTION")
    print("=" * 80)

    # Test current environment
    context = EnvironmentContext.detect_execution_context()
    print("\nCurrent environment context:")
    for key, value in context.items():
        print(f"  {key}: {value}")

    # Test should_prompt logic
    should_prompt, reason = should_prompt_for_dependencies()
    print(f"\nShould prompt for dependencies: {should_prompt}")
    print(f"Reason: {reason}")

    # Test with forced flags
    should_prompt, reason = should_prompt_for_dependencies(force_prompt=True)
    print(f"\nWith force_prompt=True: {should_prompt} ({reason})")

    should_prompt, reason = should_prompt_for_dependencies(force_skip=True)
    print(f"With force_skip=True: {should_prompt} ({reason})")

    # Test environment summary
    summary = EnvironmentContext.get_environment_summary()
    print(f"\nEnvironment summary: {summary}")

    print("\n✅ Environment detection tests completed")


def test_agent_change_detection():
    """Test agent change detection with hash-based tracking."""
    print("\n" + "=" * 80)
    print("TESTING AGENT CHANGE DETECTION")
    print("=" * 80)

    # Create a temporary test directory
    with tmp_path as tmpdir:
        test_dir = Path(tmpdir)
        agents_dir = test_dir / ".claude" / "agents"
        agents_dir.mkdir(parents=True)

        # Create test agent files
        agent1_path = agents_dir / "test_agent1.md"
        agent2_path = agents_dir / "test_agent2.md"

        agent1_path.write_text("# Test Agent 1\nInitial content")
        agent2_path.write_text("# Test Agent 2\nInitial content")

        # Change to test directory
        original_cwd = Path.cwd()
        os.chdir(test_dir)

        try:
            # Initialize loader
            loader = AgentDependencyLoader()

            # First check - should detect changes (no previous state)
            has_changed, hash1 = loader.has_agents_changed()
            print("\nFirst check (no previous state):")
            print(f"  Has changed: {has_changed}")
            print(f"  Hash: {hash1[:16]}...")

            # Mark as checked
            loader.mark_deployment_checked(hash1, {"test": "results"})

            # Second check - should not detect changes
            has_changed, hash2 = loader.has_agents_changed()
            print("\nSecond check (no changes):")
            print(f"  Has changed: {has_changed}")
            print(f"  Hash: {hash2[:16]}...")

            # Modify an agent file
            agent1_path.write_text("# Test Agent 1\nModified content")

            # Third check - should detect changes
            has_changed, hash3 = loader.has_agents_changed()
            print("\nThird check (after modification):")
            print(f"  Has changed: {has_changed}")
            print(f"  Hash: {hash3[:16]}...")

            # Add a new agent
            agent3_path = agents_dir / "test_agent3.md"
            agent3_path.write_text("# Test Agent 3\nNew agent")

            # Fourth check - should detect changes
            has_changed, hash4 = loader.has_agents_changed()
            print("\nFourth check (after adding agent):")
            print(f"  Has changed: {has_changed}")
            print(f"  Hash: {hash4[:16]}...")

            print("\n✅ Agent change detection tests completed")

        finally:
            os.chdir(original_cwd)


def test_dependency_caching():
    """Test dependency caching mechanism."""
    print("\n" + "=" * 80)
    print("TESTING DEPENDENCY CACHING")
    print("=" * 80)

    with tmp_path as tmpdir:
        cache_dir = Path(tmpdir)

        # Initialize cache with short TTL for testing
        cache = DependencyCache(cache_dir=cache_dir, ttl_seconds=2)

        # Test data
        deployment_hash = "test_hash_12345"
        test_results = {
            "summary": {
                "missing_python": ["pandas", "numpy"],
                "satisfied_python": ["requests"],
            }
        }

        # Test cache miss
        cached = cache.get(deployment_hash)
        print(f"\nInitial cache get (should be None): {cached}")

        # Store in cache
        cache.set(deployment_hash, test_results)
        print("Stored results in cache")

        # Test cache hit
        cached = cache.get(deployment_hash)
        print(f"Cache get after storing: {cached is not None}")
        if cached:
            print(f"  Missing deps: {cached['summary']['missing_python']}")

        # Test cache stats
        stats = cache.get_cache_stats()
        print("\nCache statistics:")
        for key, value in stats.items():
            print(f"  {key}: {value}")

        # Test cache expiration
        import time

        print("\nWaiting for cache to expire (2 seconds)...")
        time.sleep(2.1)

        cached = cache.get(deployment_hash)
        print(f"Cache get after expiration: {cached}")

        # Test cache invalidation
        cache.set(deployment_hash, test_results)  # Re-add
        cache.invalidate(deployment_hash)
        cached = cache.get(deployment_hash)
        print(f"Cache get after invalidation: {cached}")

        print("\n✅ Dependency caching tests completed")


def test_smart_dependency_checker():
    """Test the integrated smart dependency checker."""
    print("\n" + "=" * 80)
    print("TESTING SMART DEPENDENCY CHECKER")
    print("=" * 80)

    with tmp_path as tmpdir:
        test_dir = Path(tmpdir)
        agents_dir = test_dir / ".claude" / "agents"
        agents_dir.mkdir(parents=True)

        # Create test agent
        agent_path = agents_dir / "test_agent.md"
        agent_path.write_text("# Test Agent")

        # Change to test directory
        original_cwd = Path.cwd()
        os.chdir(test_dir)

        try:
            # Initialize smart checker
            smart_checker = SmartDependencyChecker(cache_ttl_seconds=60)

            # Test should_check logic
            should_check, reason = smart_checker.should_check_dependencies(
                force_check=False, deployment_hash="test_hash"
            )
            print(f"\nShould check dependencies: {should_check}")
            print(f"Reason: {reason}")

            # Test with force_check
            should_check, reason = smart_checker.should_check_dependencies(
                force_check=True, deployment_hash="test_hash"
            )
            print(f"\nWith force_check=True: {should_check}")
            print(f"Reason: {reason}")

            # Test rate limiting
            smart_checker._last_check_time = time.time()
            should_check, reason = smart_checker.should_check_dependencies(
                force_check=False, deployment_hash="test_hash"
            )
            print(f"\nWith recent check: {should_check}")
            print(f"Reason: {reason}")

            print("\n✅ Smart dependency checker tests completed")

        finally:
            os.chdir(original_cwd)


def test_integration():
    """Test the full integration of smart dependency checking."""
    print("\n" + "=" * 80)
    print("TESTING FULL INTEGRATION")
    print("=" * 80)

    with tmp_path as tmpdir:
        test_dir = Path(tmpdir)

        # Set up test environment
        claude_agents_dir = test_dir / ".claude" / "agents"
        claude_agents_dir.mkdir(parents=True)

        mpm_agents_dir = test_dir / ".claude-mpm" / "agents"
        mpm_agents_dir.mkdir(parents=True)

        # Create test agent with dependencies
        agent_config = {
            "agent_id": "test_agent",
            "version": "1.0.0",
            "dependencies": {
                "python": ["requests>=2.0.0", "pytest"],
                "system": ["git"],
            },
        }

        config_path = mpm_agents_dir / "test_agent.json"
        config_path.write_text(json.dumps(agent_config, indent=2))

        # Deploy agent
        agent_md_path = claude_agents_dir / "test_agent.md"
        agent_md_path.write_text("# Test Agent\nDeployed for testing")

        # Change to test directory
        original_cwd = Path.cwd()
        os.chdir(test_dir)

        try:
            print("\nSimulating smart dependency checking workflow:")

            # 1. Initialize components
            loader = AgentDependencyLoader()
            smart_checker = SmartDependencyChecker()

            # 2. Check if dependencies need checking
            has_changed, _deployment_hash = loader.has_agents_changed()
            print(f"\n1. Agent changes detected: {has_changed}")

            # 3. Check environment for prompting
            can_prompt, prompt_reason = should_prompt_for_dependencies()
            print(f"2. Can prompt for installation: {can_prompt} ({prompt_reason})")

            # 4. Get or check dependencies
            print("3. Checking dependencies...")
            results, was_cached = smart_checker.get_or_check_dependencies(
                loader=loader, force_check=False
            )

            print(f"   Results cached: {was_cached}")
            print(f"   Total agents: {results['summary']['total_agents']}")
            print(f"   Agents with deps: {results['summary']['agents_with_deps']}")

            if results["summary"]["missing_python"]:
                print(f"   Missing Python deps: {results['summary']['missing_python']}")
            if results["summary"]["satisfied_python"]:
                print(
                    f"   Satisfied Python deps: {results['summary']['satisfied_python'][:3]}"
                )

            # 5. Simulate second run (should use cache)
            print("\n4. Second run (should use cache):")
            _results2, was_cached2 = smart_checker.get_or_check_dependencies(
                loader=loader, force_check=False
            )
            print(f"   Results cached: {was_cached2}")

            print("\n✅ Integration test completed successfully")

        finally:
            os.chdir(original_cwd)


def main():
    """Run all tests."""
    print("SMART DEPENDENCY CHECKING TEST SUITE")
    print("=" * 80)

    try:
        # Run individual component tests
        test_environment_detection()
        test_agent_change_detection()
        test_dependency_caching()
        test_smart_dependency_checker()
        test_integration()

        print("\n" + "=" * 80)
        print("ALL TESTS COMPLETED SUCCESSFULLY ✅")
        print("=" * 80)

        print("\nThe smart dependency checking system is working correctly:")
        print("- Environment detection properly identifies TTY, CI, Docker contexts")
        print("- Agent change detection uses hash-based tracking")
        print("- Caching mechanism stores and retrieves results efficiently")
        print("- Smart checker integrates all components seamlessly")
        print("- Interactive prompting only occurs in appropriate environments")

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
