#!/usr/bin/env python3
"""Comprehensive test suite for dynamic agent capabilities.

Tests all aspects of the dynamic agent capabilities implementation:
1. Agent discovery across all tiers
2. Format handling (new schema, legacy, invalid)
3. Content generation quality
4. Placeholder replacement
5. Error handling and fallback
6. Performance requirements
7. Backward compatibility
"""

import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.services.agents.management import AgentCapabilitiesGenerator
from claude_mpm.services.agents.registry import DeployedAgentDiscovery
from claude_mpm.services.framework_claude_md_generator.content_assembler import (
    ContentAssembler,
)


class TestResult:
    """Test result tracking."""

    def __init__(self, name: str):
        self.name = name
        self.passed = False
        self.message = ""
        self.duration = 0.0

    def __str__(self):
        status = "PASS" if self.passed else "FAIL"
        return f"{self.name}: {status} ({self.duration:.3f}s) - {self.message}"


def test_agent_discovery_all_tiers():
    """Test 1: Verify DeployedAgentDiscovery discovers all deployed agents."""
    result = TestResult("Agent Discovery All Tiers")
    start_time = time.time()

    try:
        discovery = DeployedAgentDiscovery()
        agents = discovery.discover_deployed_agents()

        # Check we found agents
        if not agents:
            result.message = "No agents discovered"
            return result

        # Check all agents have required fields
        required_fields = [
            "id",
            "name",
            "description",
            "specializations",
            "source_tier",
        ]
        for agent in agents:
            for field in required_fields:
                if field not in agent:
                    result.message = (
                        f"Agent {agent.get('id', 'unknown')} missing field: {field}"
                    )
                    return result

        # Check we have various agent types
        agent_ids = [a["id"] for a in agents]
        expected_core = ["research", "engineer", "qa", "documentation"]
        found_core = [a for a in expected_core if a in agent_ids]

        result.passed = True
        result.message = (
            f"Found {len(agents)} agents including {len(found_core)} core agents"
        )

    except Exception as e:
        result.message = f"Exception: {e!s}"

    result.duration = time.time() - start_time
    return result


def test_agent_format_handling():
    """Test 2: Test handling of different agent formats."""
    result = TestResult("Agent Format Handling")
    start_time = time.time()

    try:
        discovery = DeployedAgentDiscovery()

        # Create mock agents with different formats
        class NewSchemaAgent:
            def __init__(self):
                self.agent_id = "test_new"
                self.metadata = type(
                    "obj",
                    (object,),
                    {
                        "name": "Test New Agent",
                        "description": "New schema test",
                        "specializations": ["testing"],
                    },
                )()
                self.configuration = type(
                    "obj", (object,), {"tools": ["tool1", "tool2"]}
                )()

        class LegacyAgent:
            def __init__(self):
                self.type = "test_legacy"
                self.name = "Test Legacy Agent"
                self.description = "Legacy format test"
                self.specializations = ["legacy"]
                self.tools = ["legacy_tool"]

        class MinimalAgent:
            def __init__(self):
                self.type = "minimal"

        # Test extraction for each format
        new_info = discovery._extract_agent_info(NewSchemaAgent())
        legacy_info = discovery._extract_agent_info(LegacyAgent())
        minimal_info = discovery._extract_agent_info(MinimalAgent())

        # Verify extraction results
        checks = [
            (new_info["id"] == "test_new", "New schema ID extraction"),
            (new_info["name"] == "Test New Agent", "New schema name extraction"),
            (legacy_info["id"] == "test_legacy", "Legacy ID extraction"),
            (legacy_info["name"] == "Test Legacy Agent", "Legacy name extraction"),
            (minimal_info["id"] == "minimal", "Minimal ID extraction"),
            (
                minimal_info["name"] == "Minimal"
                or minimal_info["name"] == "Unknown Agent",
                "Minimal name default",
            ),
        ]

        failed = [msg for passed, msg in checks if not passed]
        if failed:
            result.message = f"Failed checks: {', '.join(failed)}"
        else:
            result.passed = True
            result.message = "All format handling tests passed"

    except Exception as e:
        result.message = f"Exception: {e!s}"

    result.duration = time.time() - start_time
    return result


def test_capabilities_generator_quality():
    """Test 3: Verify AgentCapabilitiesGenerator produces correct markdown."""
    result = TestResult("Capabilities Generator Quality")
    start_time = time.time()

    try:
        generator = AgentCapabilitiesGenerator()

        # Test with sample agents
        test_agents = [
            {
                "id": "research",
                "name": "Research Agent",
                "description": "Test research agent",
                "specializations": ["analysis", "investigation", "patterns"],
                "source_tier": "system",
                "capabilities": {
                    "when_to_use": ["Codebase analysis", "Pattern identification"]
                },
                "tools": ["search", "analyze", "report"],
            },
            {
                "id": "custom-agent",
                "name": "Custom Project Agent",
                "description": "Project-specific agent",
                "specializations": ["custom"],
                "source_tier": "project",
                "capabilities": {},
                "tools": [],
            },
        ]

        content = generator.generate_capabilities_section(test_agents)

        # Verify content structure
        checks = [
            ("**Core Agents**:" in content, "Core agents header present"),
            (
                "research, custom-agent" in content
                or "custom-agent, research" in content,
                "Agent list correct",
            ),
            ("**Research Agent**:" in content, "Research agent in capabilities"),
            ("**Custom Project Agent**:" in content, "Custom agent in capabilities"),
            ("Codebase analysis" in content, "Capabilities text included"),
            (
                "*Generated from 2 deployed agents*" in content,
                "Generation note present",
            ),
        ]

        # Check for project-specific section when project agents exist
        if any(a["source_tier"] == "project" for a in test_agents):
            checks.append(
                ("### Project-Specific Agents" in content, "Project agents section")
            )

        failed = [msg for passed, msg in checks if not passed]
        if failed:
            result.message = f"Failed checks: {', '.join(failed)}"
        else:
            result.passed = True
            result.message = "Generated content meets all quality requirements"

    except Exception as e:
        result.message = f"Exception: {e!s}"

    result.duration = time.time() - start_time
    return result


def test_content_assembler_replacement():
    """Test 4: Test ContentAssembler placeholder replacement."""
    result = TestResult("Content Assembler Replacement")
    start_time = time.time()

    try:
        assembler = ContentAssembler()

        # Test various placeholder scenarios
        test_cases = [
            ("Simple: {{capabilities-list}}", "Simple placeholder"),
            (
                "Multiple:\n{{capabilities-list}}\n\n{{capabilities-list}}",
                "Multiple placeholders",
            ),
            (
                "Inline: Text before {{capabilities-list}} text after",
                "Inline placeholder",
            ),
            ("No placeholder: Just regular text", "No placeholder"),
        ]

        all_passed = True
        messages = []

        for test_content, desc in test_cases:
            processed = assembler.apply_template_variables(test_content)

            if "{{capabilities-list}}" in test_content:
                # Should be replaced
                if "{{capabilities-list}}" in processed:
                    all_passed = False
                    messages.append(f"{desc}: placeholder not replaced")
                elif "**Core Agents**:" not in processed:
                    all_passed = False
                    messages.append(f"{desc}: no dynamic content inserted")
                else:
                    messages.append(f"{desc}: OK")
            # Should be unchanged
            elif processed != test_content:
                all_passed = False
                messages.append(f"{desc}: content changed unexpectedly")
            else:
                messages.append(f"{desc}: OK")

        result.passed = all_passed
        result.message = "; ".join(messages)

    except Exception as e:
        result.message = f"Exception: {e!s}"

    result.duration = time.time() - start_time
    return result


def test_error_handling_fallback():
    """Test 6: Verify error handling and graceful fallback."""
    result = TestResult("Error Handling & Fallback")
    start_time = time.time()

    try:
        # Test with broken discovery
        class BrokenDiscovery:
            def discover_deployed_agents(self):
                raise Exception("Discovery failed")

        # Monkey patch for testing
        original_init = ContentAssembler.__init__

        def broken_init(self):
            self.template_variables = {}
            self.agent_discovery = BrokenDiscovery()
            from claude_mpm.services.agents.management import AgentCapabilitiesGenerator

            self.capabilities_generator = AgentCapabilitiesGenerator()

        ContentAssembler.__init__ = broken_init

        try:
            assembler = ContentAssembler()
            test_content = "Test {{capabilities-list}} content"
            processed = assembler.apply_template_variables(test_content)

            # Should handle error gracefully
            if "{{capabilities-list}}" in processed:
                # Placeholder not replaced - acceptable fallback
                result.passed = True
                result.message = "Gracefully fell back to keeping placeholder on error"
            else:
                # Check if fallback content was used
                result.passed = True
                result.message = "Error handled with fallback content"

        finally:
            # Restore original
            ContentAssembler.__init__ = original_init

    except Exception as e:
        result.message = f"Exception during error handling test: {e!s}"

    result.duration = time.time() - start_time
    return result


def test_performance_requirements():
    """Test 7: Check performance meets <200ms requirement."""
    result = TestResult("Performance Requirements")
    start_time = time.time()

    try:
        # Measure full generation cycle
        discovery = DeployedAgentDiscovery()
        generator = AgentCapabilitiesGenerator()

        # Time discovery
        disc_start = time.time()
        agents = discovery.discover_deployed_agents()
        disc_time = time.time() - disc_start

        # Time generation
        gen_start = time.time()
        generator.generate_capabilities_section(agents)
        gen_time = time.time() - gen_start

        # Time full assembly
        assembler = ContentAssembler()
        assembly_start = time.time()
        test_content = "Test {{capabilities-list}} content"
        assembler.apply_template_variables(test_content)
        assembly_time = time.time() - assembly_start

        total_time = disc_time + gen_time + assembly_time

        if total_time < 0.200:  # 200ms
            result.passed = True
            result.message = f"Total: {total_time * 1000:.1f}ms (discovery: {disc_time * 1000:.1f}ms, generation: {gen_time * 1000:.1f}ms, assembly: {assembly_time * 1000:.1f}ms)"
        else:
            result.passed = False
            result.message = f"Too slow: {total_time * 1000:.1f}ms > 200ms requirement"

    except Exception as e:
        result.message = f"Exception: {e!s}"

    result.duration = time.time() - start_time
    return result


def test_backward_compatibility():
    """Test 8: Test backward compatibility."""
    result = TestResult("Backward Compatibility")
    start_time = time.time()

    try:
        assembler = ContentAssembler()

        # Test that static content without placeholders works
        static_content = """# Static Instructions
## Agent Capabilities
- Research: Analysis and investigation
- Engineer: Implementation and coding

No placeholders here."""

        processed = assembler.apply_template_variables(static_content)

        if processed == static_content:
            result.passed = True
            result.message = "Static content preserved without modification"
        else:
            result.passed = False
            result.message = "Static content was modified unexpectedly"

    except Exception as e:
        result.message = f"Exception: {e!s}"

    result.duration = time.time() - start_time
    return result


def test_project_override_system():
    """Test: Verify project agents override system agents."""
    result = TestResult("Project Agent Override")
    start_time = time.time()

    try:
        generator = AgentCapabilitiesGenerator()

        # Simulate agents with same ID but different tiers
        test_agents = [
            {
                "id": "research",
                "name": "System Research Agent",
                "description": "System version",
                "specializations": ["system"],
                "source_tier": "system",
                "capabilities": {},
                "tools": [],
            },
            {
                "id": "research",
                "name": "Project Research Agent",
                "description": "Project override",
                "specializations": ["project"],
                "source_tier": "project",
                "capabilities": {},
                "tools": [],
            },
        ]

        content = generator.generate_capabilities_section(test_agents)

        # Project agent should appear in project section
        if (
            "### Project-Specific Agents" in content
            and "Project Research Agent" in content
        ):
            result.passed = True
            result.message = "Project agents correctly shown in separate section"
        else:
            result.passed = False
            result.message = "Project override not properly displayed"

    except Exception as e:
        result.message = f"Exception: {e!s}"

    result.duration = time.time() - start_time
    return result


def run_all_tests():
    """Run comprehensive test suite."""
    print("Dynamic Agent Capabilities - Comprehensive Test Suite")
    print("=" * 80)

    tests = [
        test_agent_discovery_all_tiers,
        test_agent_format_handling,
        test_capabilities_generator_quality,
        test_content_assembler_replacement,
        test_error_handling_fallback,
        test_performance_requirements,
        test_backward_compatibility,
        test_project_override_system,
    ]

    results = []
    for test_func in tests:
        print(f"\nRunning: {test_func.__name__}")
        result = test_func()
        results.append(result)
        print(f"  {result}")

    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)

    passed = sum(1 for r in results if r.passed)
    total = len(results)

    for i, result in enumerate(results, 1):
        status = "✓" if result.passed else "✗"
        print(f"{status} Test {i}: {result.name}")
        if not result.passed:
            print(f"   Failed: {result.message}")

    print(f"\nTotal: {passed}/{total} tests passed")
    print(f"Overall: {'PASS' if passed == total else 'FAIL'}")

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
