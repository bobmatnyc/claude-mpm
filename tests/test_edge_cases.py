#!/usr/bin/env python3
"""
Test script to verify framework loader performance with edge cases.

This script tests performance with various edge cases like no agents,
many agents, and large memory files.
"""

import logging
import sys
import tempfile
import time
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.core.framework_loader import FrameworkLoader


def setup_logging():
    """Setup logging."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%H:%M:%S",
    )


def test_no_agents_performance():
    """Test performance when no agents are deployed."""
    print("\n" + "=" * 60)
    print("Testing Performance with No Deployed Agents")
    print("=" * 60)

    # Backup existing agents directory
    agents_dir = Path.home() / ".claude" / "agents"
    backup_dir = None

    if agents_dir.exists():
        backup_dir = agents_dir.with_suffix(".backup_test")
        if backup_dir.exists():
            import shutil

            shutil.rmtree(backup_dir)
        agents_dir.rename(backup_dir)
        print(f"Backed up agents to {backup_dir}")

    try:
        # Test with no agents
        print("1. Testing framework loader with no deployed agents...")
        start = time.time()
        loader = FrameworkLoader()
        init_time = time.time() - start

        # Test deployed agents discovery
        start = time.time()
        deployed = loader._get_deployed_agents()
        deployed_time = time.time() - start

        # Test capabilities generation
        start = time.time()
        capabilities = loader._generate_agent_capabilities_section()
        capabilities_time = time.time() - start

        print(f"   Initialization: {init_time:.3f}s")
        print(f"   Deployed agents scan: {deployed_time:.3f}s")
        print(f"   Capabilities generation: {capabilities_time:.3f}s")
        print(f"   Found agents: {len(deployed)}")
        print(f"   Capabilities length: {len(capabilities)} chars")

        # Verify fallback capabilities are used
        assert "Available Agent Capabilities" in capabilities
        print("   ✓ Fallback capabilities working correctly")

        # Test that it's still fast
        total_time = init_time + deployed_time + capabilities_time
        if total_time < 1.0:
            print(f"   ✓ Performance good with no agents: {total_time:.3f}s")
        else:
            print(f"   ⚠ Performance slower than expected: {total_time:.3f}s")

    finally:
        # Restore agents directory
        if backup_dir and backup_dir.exists():
            if agents_dir.exists():
                import shutil

                shutil.rmtree(agents_dir)
            backup_dir.rename(agents_dir)
            print("Restored agents from backup")

    return True


def test_large_memory_performance():
    """Test performance with large memory files."""
    print("\n" + "=" * 60)
    print("Testing Performance with Large Memory Files")
    print("=" * 60)

    # Create temporary large memory file
    project_memory_dir = Path.cwd() / ".claude-mpm" / "memories"
    project_memory_dir.mkdir(parents=True, exist_ok=True)

    large_memory_file = project_memory_dir / "PM_memories_large_test.md"
    backup_file = project_memory_dir / "PM_memories.md.backup"
    original_file = project_memory_dir / "PM_memories.md"

    # Backup original if it exists
    if original_file.exists():
        original_file.rename(backup_file)

    try:
        # Create large memory content (1MB of memory items)
        print("1. Creating large memory file (1MB)...")
        large_content = "# Agent Memory\n"
        large_content += "<!-- Last Updated: 2025-08-22T00:00:00Z -->\n\n"

        # Add many memory items
        for i in range(10000):
            large_content += f"- **Memory item {i:05d}**: This is a detailed memory entry with substantial content that represents realistic memory usage in a large project. It includes technical details, context, and references.\n"

        large_memory_file.write_text(large_content)
        file_size = len(large_content.encode("utf-8"))
        print(f"   Created memory file: {file_size:,} bytes")

        # Rename to active file
        large_memory_file.rename(original_file)

        # Test loading performance
        print("2. Testing loader performance with large memory...")
        start = time.time()
        loader = FrameworkLoader()
        loader.clear_memory_caches()  # Ensure fresh load

        content = {}
        loader._load_actual_memories(content)
        load_time = time.time() - start

        loaded_size = len(content.get("actual_memories", "").encode("utf-8"))
        print(f"   Load time: {load_time:.3f}s")
        print(f"   Loaded size: {loaded_size:,} bytes")

        # Test cached performance
        start = time.time()
        content2 = {}
        loader._load_actual_memories(content2)
        cached_time = time.time() - start

        print(f"   Cached load time: {cached_time:.3f}s")

        speedup = load_time / cached_time if cached_time > 0 else float("inf")
        print(f"   Cache speedup: {speedup:.1f}x")

        # Verify performance is reasonable
        if load_time < 1.0:
            print(f"   ✓ Large memory performance good: {load_time:.3f}s")
        else:
            print(f"   ⚠ Large memory performance slower: {load_time:.3f}s")

    finally:
        # Clean up
        if original_file.exists():
            original_file.unlink()
        if backup_file.exists():
            backup_file.rename(original_file)
        print("   Cleaned up test files")

    return True


def test_many_agents_simulation():
    """Test performance with simulation of many agents."""
    print("\n" + "=" * 60)
    print("Testing Performance with Many Agents Simulation")
    print("=" * 60)

    # We'll test the metadata parsing specifically since that's the bottleneck
    # with many agents
    loader = FrameworkLoader()

    # Create temporary agent files for testing
    temp_dir = Path(tempfile.mkdtemp())
    print(f"1. Creating temporary agents in {temp_dir}")

    try:
        # Create many test agent files
        agent_count = 50
        for i in range(agent_count):
            agent_file = temp_dir / f"test_agent_{i:03d}.md"
            agent_content = f"""---
name: test-agent-{i:03d}
description: Test agent number {i} for performance testing with detailed description that includes multiple lines and comprehensive information about capabilities and responsibilities.
authority: Can perform test operations and simulated work for agent {i}
primary_function: Testing and simulation
tools: Read,Write,Edit,Bash
model: sonnet
---

# Test Agent {i:03d}

This is a test agent created for performance testing purposes.

## Capabilities
- Simulated task execution
- Performance testing
- Load testing scenarios

## Authority
This agent has full authority for test operations.
"""
            agent_file.write_text(agent_content)

        print(f"   Created {agent_count} test agent files")

        # Test parsing performance
        print("2. Testing metadata parsing performance...")
        start = time.time()

        parsed_agents = []
        for agent_file in temp_dir.glob("*.md"):
            metadata = loader._parse_agent_metadata(agent_file)
            if metadata:
                parsed_agents.append(metadata)

        parse_time = time.time() - start

        print(f"   Parsed {len(parsed_agents)} agents in {parse_time:.3f}s")
        print(f"   Average per agent: {parse_time / len(parsed_agents) * 1000:.1f}ms")

        # Test cached parsing
        start = time.time()
        parsed_agents_cached = []
        for agent_file in temp_dir.glob("*.md"):
            metadata = loader._parse_agent_metadata(agent_file)
            if metadata:
                parsed_agents_cached.append(metadata)

        cached_parse_time = time.time() - start

        print(f"   Cached parse: {cached_parse_time:.3f}s")
        speedup = (
            parse_time / cached_parse_time if cached_parse_time > 0 else float("inf")
        )
        print(f"   Cache speedup: {speedup:.1f}x")

        # Verify performance
        if parse_time < 2.0:
            print(
                f"   ✓ Many agents performance good: {parse_time:.3f}s for {agent_count} agents"
            )
        else:
            print(
                f"   ⚠ Many agents performance slower: {parse_time:.3f}s for {agent_count} agents"
            )

    finally:
        # Clean up temporary files
        import shutil

        shutil.rmtree(temp_dir)
        print("   Cleaned up temporary directory")

    return True


def test_concurrent_cache_access():
    """Test concurrent access to caches for thread safety."""
    print("\n" + "=" * 60)
    print("Testing Concurrent Cache Access")
    print("=" * 60)

    import concurrent.futures

    loader = FrameworkLoader()
    loader.clear_all_caches()

    results = []
    errors = []

    def stress_test_worker(worker_id):
        """Worker function that stresses the caching system."""
        try:
            for i in range(10):
                # Mix of cache operations
                loader._get_deployed_agents()
                loader._generate_agent_capabilities_section()
                content = {}
                loader._load_actual_memories(content)

                # Occasional cache clears
                if i % 3 == 0:
                    loader.clear_agent_caches()
                if i % 5 == 0:
                    loader.clear_memory_caches()

            results.append(f"Worker {worker_id}: completed 10 operations")

        except Exception as e:
            errors.append(f"Worker {worker_id}: {e}")

    print("1. Running stress test with 10 concurrent workers...")
    start = time.time()

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(stress_test_worker, i) for i in range(10)]
        concurrent.futures.wait(futures)

    total_time = time.time() - start

    print(f"2. Stress test completed in {total_time:.3f}s")
    print(f"   Successful workers: {len(results)}")
    print(f"   Errors: {len(errors)}")

    if errors:
        for error in errors[:5]:  # Show first 5 errors
            print(f"   Error: {error}")

    if len(errors) == 0:
        print("   ✓ Thread safety confirmed under stress")
    else:
        print(f"   ⚠ Thread safety issues detected: {len(errors)} errors")

    return len(errors) == 0


def main():
    """Run all edge case tests."""
    setup_logging()

    print("Framework Loader Edge Case Performance Test")
    print("=" * 80)
    print("Testing edge cases: no agents, large memories, many agents...")

    tests = [
        test_no_agents_performance,
        test_large_memory_performance,
        test_many_agents_simulation,
        test_concurrent_cache_access,
    ]

    passed = 0
    total = len(tests)

    for test_func in tests:
        try:
            result = test_func()
            if result:
                passed += 1
                print("✓ PASSED")
            else:
                print("✗ FAILED")
        except Exception as e:
            print(f"✗ FAILED: {e}")
            import traceback

            traceback.print_exc()

    print("\n" + "=" * 80)
    print("EDGE CASE TEST SUMMARY")
    print("=" * 80)
    print(f"Tests passed: {passed}/{total}")

    if passed == total:
        print("✅ ALL EDGE CASE TESTS PASSED!")
        print("Performance optimizations handle edge cases correctly.")
    else:
        print("⚠️ SOME EDGE CASE TESTS FAILED!")
        print("Performance optimizations may have issues with edge cases.")

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
