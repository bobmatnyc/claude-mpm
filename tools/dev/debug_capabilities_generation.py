#!/usr/bin/env python3
"""Debug the capabilities generation process."""


# Use centralized path management
from claude_mpm.config.paths import paths

paths.ensure_in_path()

from claude_mpm.services.agents.management import AgentCapabilitiesGenerator
from claude_mpm.services.agents.registry import DeployedAgentDiscovery
from claude_mpm.services.framework_claude_md_generator.content_assembler import (
    ContentAssembler,
)


def debug_capabilities_generation():
    """Debug the capabilities generation process step by step."""
    print("Debugging capabilities generation...\n")

    # Test 1: Agent Discovery
    print("1. Testing Agent Discovery:")
    discovery = DeployedAgentDiscovery()
    try:
        agents = discovery.discover_deployed_agents()
        print(f"   ✓ Found {len(agents)} deployed agents:")
        for agent in agents:
            print(f"     - {agent['name']} (v{agent.get('version', 'unknown')})")
    except Exception as e:
        print(f"   ❌ Agent discovery failed: {e}")
        agents = []

    # Test 2: Capabilities Generation
    print("\n2. Testing Capabilities Generation:")
    generator = AgentCapabilitiesGenerator()
    try:
        capabilities = generator.generate_capabilities_section(agents)
        print(f"   ✓ Generated capabilities section ({len(capabilities)} chars)")
        print("\n   Preview:")
        print("-" * 60)
        print(capabilities[:500] + "..." if len(capabilities) > 500 else capabilities)
        print("-" * 60)
    except Exception as e:
        print(f"   ❌ Capabilities generation failed: {e}")
        capabilities = ""

    # Test 3: Content Assembly
    print("\n3. Testing Content Assembly:")
    assembler = ContentAssembler()
    test_content = "Before placeholder\n\n{{capabilities-list}}\n\nAfter placeholder"
    try:
        processed = assembler.apply_template_variables(test_content)
        print("   ✓ Template processing successful")
        if "{{capabilities-list}}" in processed:
            print("   ❌ Placeholder not replaced!")
        else:
            print("   ✓ Placeholder replaced")

        # Show what was inserted
        lines = processed.split("\n")
        start_idx = None
        end_idx = None
        for i, line in enumerate(lines):
            if line == "Before placeholder":
                start_idx = i + 2  # Skip blank line
            elif line == "After placeholder":
                end_idx = i - 1  # Skip blank line
                break

        if start_idx is not None and end_idx is not None:
            inserted_content = "\n".join(lines[start_idx:end_idx])
            print(f"\n   Inserted content ({len(inserted_content)} chars):")
            print("-" * 60)
            print(
                inserted_content[:500] + "..."
                if len(inserted_content) > 500
                else inserted_content
            )
            print("-" * 60)
    except Exception as e:
        print(f"   ❌ Content assembly failed: {e}")

    # Test 4: Full INSTRUCTIONS.md processing
    print("\n4. Testing full INSTRUCTIONS.md processing:")
    instructions_path = paths.agents_dir / "INSTRUCTIONS.md"
    if instructions_path.exists():
        raw_content = instructions_path.read_text()
        print(f"   ✓ Read INSTRUCTIONS.md ({len(raw_content)} chars)")

        try:
            processed = assembler.apply_template_variables(raw_content)
            print(f"   ✓ Processed INSTRUCTIONS.md ({len(processed)} chars)")

            # Check the difference
            size_diff = len(processed) - len(raw_content)
            print(f"   Size difference: {size_diff:+d} chars")

            if "{{capabilities-list}}" in processed:
                print("   ❌ Placeholder still present in processed content!")
            else:
                print("   ✓ Placeholder successfully replaced")

                # Find where the capabilities were inserted
                for i, line in enumerate(processed.split("\n")):
                    if "## Available Specialized Agents" in line:
                        print(f"   ✓ Found capabilities section at line {i+1}")
                        break
                else:
                    print(
                        "   ❌ Could not find '## Available Specialized Agents' header"
                    )
        except Exception as e:
            print(f"   ❌ Processing failed: {e}")
    else:
        print(f"   ❌ INSTRUCTIONS.md not found at {instructions_path}")


if __name__ == "__main__":
    debug_capabilities_generation()
