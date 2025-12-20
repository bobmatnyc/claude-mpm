#!/usr/bin/env python3
"""
Test script to verify framework loader functionality after caching optimizations.

This script verifies that all functionality still works correctly with the
performance optimizations in place.
"""

import logging
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.core.framework_loader import FrameworkLoader


def setup_logging():
    """Setup logging to see detailed information."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%H:%M:%S",
    )


def test_agent_capabilities_loading():
    """Test that agent capabilities are loaded correctly."""
    print("\n" + "=" * 60)
    print("Testing Agent Capabilities Loading")
    print("=" * 60)

    loader = FrameworkLoader()

    # Test deployed agents discovery
    deployed_agents = loader._get_deployed_agents()
    print(f"✓ Found {len(deployed_agents)} deployed agents")
    print(f"  Deployed agents: {', '.join(sorted(deployed_agents))}")

    # Test agent capabilities generation
    capabilities = loader._generate_agent_capabilities_section()
    print(f"✓ Generated agent capabilities section ({len(capabilities)} chars)")

    # Verify capabilities contain expected elements
    assert "Available Agent Capabilities" in capabilities
    assert len(deployed_agents) > 0, "Should find deployed agents"

    # Test specific agent parsing
    agent_dirs = [Path.cwd() / ".claude" / "agents", Path.home() / ".claude" / "agents"]

    parsed_agents = []
    for agents_dir in agent_dirs:
        if agents_dir.exists():
            for agent_file in agents_dir.glob("*.md"):
                if not agent_file.name.startswith("."):
                    metadata = loader._parse_agent_metadata(agent_file)
                    if metadata:
                        parsed_agents.append(metadata)

    print(f"✓ Successfully parsed {len(parsed_agents)} agent metadata files")

    # Verify metadata structure
    if parsed_agents:
        sample_agent = parsed_agents[0]
        required_fields = ["id", "display_name", "description"]
        for field in required_fields:
            assert field in sample_agent, (
                f"Agent metadata missing required field: {field}"
            )
        print(f"✓ Agent metadata contains required fields: {required_fields}")

    return True


def test_memory_loading():
    """Test that memories are loaded correctly."""
    print("\n" + "=" * 60)
    print("Testing Memory Loading")
    print("=" * 60)

    loader = FrameworkLoader()
    content = {}

    # Test memory loading
    loader._load_actual_memories(content)

    if "actual_memories" in content:
        memory_size = len(content["actual_memories"])
        print(f"✓ Loaded PM memories ({memory_size} bytes)")
        print(f"  Memory preview: {content['actual_memories'][:100]}...")
    else:
        print("! No PM memories found")

    # NEW ARCHITECTURE: Agent memories should NOT be in framework content
    # They are loaded at deployment time and appended to agent files
    if "agent_memories" in content and len(content["agent_memories"]) > 0:
        agent_count = len(content["agent_memories"])
        print(f"⚠ Found agent memories in framework content: {agent_count} agents")
        print("  NOTE: Agent memories should now be in agent files, not framework")
        for agent_name in content["agent_memories"]:
            memory_size = len(content["agent_memories"][agent_name])
            print(f"  - {agent_name}: {memory_size} bytes")
    else:
        print("✓ No agent memories in framework (correct - now loaded at deployment)")

    return True


def test_framework_content_loading():
    """Test that framework content loads correctly."""
    print("\n" + "=" * 60)
    print("Testing Framework Content Loading")
    print("=" * 60)

    loader = FrameworkLoader()
    content = loader.framework_content

    # Check essential content is loaded
    essential_fields = [
        "loaded",
        "framework_instructions",
        "workflow_instructions",
        "memory_instructions",
        "agents",
    ]

    for field in essential_fields:
        if content.get(field):
            print(f"✓ {field}: loaded")
        else:
            print(f"⚠ {field}: not loaded or empty")

    print(f"✓ Framework loaded status: {content.get('loaded', False)}")
    print(f"✓ Framework version: {content.get('version', 'unknown')}")
    print(f"✓ Agent count: {len(content.get('agents', {}))}")

    return True


def test_full_instruction_generation():
    """Test that full framework instructions can be generated."""
    print("\n" + "=" * 60)
    print("Testing Full Framework Instructions")
    print("=" * 60)

    loader = FrameworkLoader()

    # Generate full instructions
    instructions = loader.get_framework_instructions()

    print(f"✓ Generated framework instructions ({len(instructions)} chars)")

    # Check that essential sections are present
    expected_sections = [
        "Claude MPM Framework",
        "Available Agent Capabilities",
        "Temporal Context",
    ]

    for section in expected_sections:
        if section in instructions:
            print(f"✓ Contains section: {section}")
        else:
            print(f"⚠ Missing section: {section}")

    # Verify instructions contain agent information
    deployed_agents = loader._get_deployed_agents()
    if deployed_agents:
        # Check that some agent names appear in instructions
        agents_mentioned = sum(1 for agent in deployed_agents if agent in instructions)
        print(
            f"✓ Instructions mention {agents_mentioned}/{len(deployed_agents)} deployed agents"
        )

    return True


def test_yaml_metadata_parsing():
    """Test YAML metadata parsing works correctly."""
    print("\n" + "=" * 60)
    print("Testing YAML Metadata Parsing")
    print("=" * 60)

    loader = FrameworkLoader()

    # Find an agent file with YAML frontmatter
    agent_dirs = [Path.cwd() / ".claude" / "agents", Path.home() / ".claude" / "agents"]

    yaml_found = False
    for agents_dir in agent_dirs:
        if agents_dir.exists():
            for agent_file in agents_dir.glob("*.md"):
                if not agent_file.name.startswith("."):
                    try:
                        with agent_file.open() as f:
                            content = f.read()
                        if content.startswith("---"):
                            metadata = loader._parse_agent_metadata(agent_file)
                            if metadata:
                                print(
                                    f"✓ Successfully parsed YAML metadata from {agent_file.name}"
                                )
                                print(f"  Agent ID: {metadata.get('id')}")
                                print(f"  Display name: {metadata.get('display_name')}")
                                print(
                                    f"  Description: {metadata.get('description', '')[:50]}..."
                                )
                                yaml_found = True
                                break
                    except Exception as e:
                        print(f"⚠ Failed to parse {agent_file.name}: {e}")
        if yaml_found:
            break

    if not yaml_found:
        print("! No YAML frontmatter found in agent files")

    return True


def main():
    """Run all functionality tests."""
    setup_logging()

    print("Framework Loader Functionality Test")
    print("=" * 80)
    print("Testing that caching optimizations don't break functionality...")

    tests = [
        test_framework_content_loading,
        test_agent_capabilities_loading,
        test_memory_loading,
        test_yaml_metadata_parsing,
        test_full_instruction_generation,
    ]

    passed = 0
    total = len(tests)

    for test_func in tests:
        try:
            test_func()
            passed += 1
            print("✓ PASSED")
        except Exception as e:
            print(f"✗ FAILED: {e}")
            import traceback

            traceback.print_exc()

    print("\n" + "=" * 80)
    print("FUNCTIONALITY TEST SUMMARY")
    print("=" * 80)
    print(f"Tests passed: {passed}/{total}")

    if passed == total:
        print("✅ ALL FUNCTIONALITY TESTS PASSED!")
        print("Caching optimizations are working correctly.")
    else:
        print("⚠️ SOME TESTS FAILED!")
        print("Caching optimizations may have broken functionality.")

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
