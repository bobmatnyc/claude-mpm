"""Example usage of multi-runtime adapter architecture.

This module demonstrates how to use the adapter registry and
individual adapters for different AI coding runtimes.
"""

import logging
from typing import Optional

from claude_mpm.commander.adapters import (
    AdapterRegistry,
    AuggieAdapter,
    ClaudeCodeAdapter,
    CodexAdapter,
    MPMAdapter,
    RuntimeAdapter,
    RuntimeCapability,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def example_registry_usage() -> None:
    """Demonstrate adapter registry usage."""
    print("\n" + "=" * 60)
    print("ADAPTER REGISTRY USAGE")
    print("=" * 60 + "\n")

    # List all registered adapters
    registered = AdapterRegistry.list_registered()
    print(f"Registered adapters: {registered}")

    # Detect available runtimes on system
    available = AdapterRegistry.detect_available()
    print(f"Available runtimes: {available}")

    # Get default adapter (best available)
    default_adapter = AdapterRegistry.get_default()
    if default_adapter:
        print(f"\nDefault adapter: {default_adapter.name}")
        print(f"Capabilities: {default_adapter.capabilities}")
    else:
        print("\nNo adapters available on this system")

    # Get specific adapter
    mpm_adapter = AdapterRegistry.get("mpm")
    if mpm_adapter:
        print(f"\nMPM adapter available: {mpm_adapter.name}")
    else:
        print("\nMPM adapter not available")

    # Check if specific runtime is available
    if AdapterRegistry.is_available("claude-code"):
        print("\nClaude Code is available")
    else:
        print("\nClaude Code is NOT available")


def example_adapter_capabilities() -> None:
    """Demonstrate checking adapter capabilities."""
    print("\n" + "=" * 60)
    print("ADAPTER CAPABILITIES")
    print("=" * 60 + "\n")

    adapters = [
        ClaudeCodeAdapter(),
        AuggieAdapter(),
        CodexAdapter(),
        MPMAdapter(),
    ]

    for adapter in adapters:
        print(f"\n{adapter.name.upper()} Adapter:")
        print(
            f"  Command: {adapter.runtime_info.command if adapter.runtime_info else 'N/A'}"
        )

        # Check for specific capabilities
        info = adapter.runtime_info
        if info:
            print(f"  Supports agents: {info.supports_agents}")
            print(f"  Instruction file: {info.instruction_file or 'None'}")

            # Check for advanced features
            if RuntimeCapability.AGENT_DELEGATION in info.capabilities:
                print("  ✓ Agent delegation supported")
            else:
                print("  ✗ Agent delegation NOT supported")

            if RuntimeCapability.HOOKS in info.capabilities:
                print("  ✓ Lifecycle hooks supported")
            else:
                print("  ✗ Lifecycle hooks NOT supported")

            if RuntimeCapability.MCP_TOOLS in info.capabilities:
                print("  ✓ MCP tools supported")
            else:
                print("  ✗ MCP tools NOT supported")

            if RuntimeCapability.SKILLS in info.capabilities:
                print("  ✓ Skills supported")
            else:
                print("  ✗ Skills NOT supported")

            if RuntimeCapability.MONITOR in info.capabilities:
                print("  ✓ Real-time monitoring supported")
            else:
                print("  ✗ Real-time monitoring NOT supported")


def example_build_commands() -> None:
    """Demonstrate building launch commands."""
    print("\n" + "=" * 60)
    print("BUILD LAUNCH COMMANDS")
    print("=" * 60 + "\n")

    project_path = "/home/user/my-project"
    agent_prompt = "You are a Python expert specializing in FastAPI and async code."

    adapters = [
        ClaudeCodeAdapter(),
        AuggieAdapter(),
        CodexAdapter(),
        MPMAdapter(),
    ]

    for adapter in adapters:
        print(f"\n{adapter.name.upper()}:")

        # Basic launch command
        cmd = adapter.build_launch_command(project_path)
        print(f"  Basic: {cmd}")

        # With agent prompt
        cmd_with_prompt = adapter.build_launch_command(project_path, agent_prompt)
        print(f"  With prompt: {cmd_with_prompt}")


def example_inject_instructions() -> None:
    """Demonstrate injecting custom instructions."""
    print("\n" + "=" * 60)
    print("INJECT CUSTOM INSTRUCTIONS")
    print("=" * 60 + "\n")

    instructions = """You are a senior Python engineer.
Follow PEP 8 strictly.
Write comprehensive tests for all code.
Use type hints everywhere."""

    adapters = [
        ClaudeCodeAdapter(),
        AuggieAdapter(),
        CodexAdapter(),
        MPMAdapter(),
    ]

    for adapter in adapters:
        print(f"\n{adapter.name.upper()}:")

        cmd = adapter.inject_instructions(instructions)
        if cmd:
            print(f"  Command: {cmd}")
        else:
            print("  Not supported")


def example_inject_agent_context() -> None:
    """Demonstrate injecting agent context."""
    print("\n" + "=" * 60)
    print("INJECT AGENT CONTEXT")
    print("=" * 60 + "\n")

    agent_id = "eng-001"
    context = {
        "role": "Engineer",
        "specialty": "Backend Python",
        "task": "Implement API endpoints",
    }

    adapters = [
        ClaudeCodeAdapter(),
        AuggieAdapter(),
        CodexAdapter(),
        MPMAdapter(),
    ]

    for adapter in adapters:
        print(f"\n{adapter.name.upper()}:")

        cmd = adapter.inject_agent_context(agent_id, context)
        if cmd:
            print(f"  Command: {cmd[:100]}...")
        else:
            print("  Not supported")


def example_parse_response() -> None:
    """Demonstrate parsing runtime output."""
    print("\n" + "=" * 60)
    print("PARSE RUNTIME OUTPUT")
    print("=" * 60 + "\n")

    # Simulate different output scenarios
    outputs = {
        "idle": "File created successfully.\n> ",
        "error": "Error: File not found: config.py\n> ",
        "question": "Should I proceed with the changes? (y/n)?",
        "processing": "Processing your request...",
    }

    adapter = ClaudeCodeAdapter()

    for scenario, output in outputs.items():
        print(f"\n{scenario.upper()}:")
        parsed = adapter.parse_response(output)
        print(f"  Content: {parsed.content[:50]}...")
        print(f"  Is complete: {parsed.is_complete}")
        print(f"  Is error: {parsed.is_error}")
        print(f"  Is question: {parsed.is_question}")
        if parsed.error_message:
            print(f"  Error message: {parsed.error_message}")
        if parsed.question_text:
            print(f"  Question: {parsed.question_text}")


def example_runtime_selection() -> None:
    """Demonstrate selecting runtime based on requirements."""
    print("\n" + "=" * 60)
    print("RUNTIME SELECTION LOGIC")
    print("=" * 60 + "\n")

    def select_runtime(
        needs_agents: bool = False, needs_mcp: bool = False
    ) -> Optional[RuntimeAdapter]:
        """Select appropriate runtime based on requirements."""
        # Get all available adapters
        available = AdapterRegistry.detect_available()

        # Filter by requirements
        for name in available:
            adapter = AdapterRegistry.get(name)
            if not adapter or not adapter.runtime_info:
                continue

            info = adapter.runtime_info

            # Check agent requirement
            if needs_agents and not info.supports_agents:
                continue

            # Check MCP requirement
            if needs_mcp and RuntimeCapability.MCP_TOOLS not in info.capabilities:
                continue

            # Found suitable runtime
            return adapter

        return None

    # Example 1: Need agent delegation
    print("Requirement: Agent delegation")
    adapter = select_runtime(needs_agents=True)
    if adapter:
        print(f"  Selected: {adapter.name}")
    else:
        print("  No suitable runtime found")

    # Example 2: Need MCP tools
    print("\nRequirement: MCP tools")
    adapter = select_runtime(needs_mcp=True)
    if adapter:
        print(f"  Selected: {adapter.name}")
    else:
        print("  No suitable runtime found")

    # Example 3: Need both
    print("\nRequirement: Agent delegation + MCP tools")
    adapter = select_runtime(needs_agents=True, needs_mcp=True)
    if adapter:
        print(f"  Selected: {adapter.name}")
    else:
        print("  No suitable runtime found")


def main() -> None:
    """Run all examples."""
    print("\n" + "#" * 60)
    print("# MULTI-RUNTIME ADAPTER ARCHITECTURE EXAMPLES")
    print("#" * 60)

    # Run all examples
    example_registry_usage()
    example_adapter_capabilities()
    example_build_commands()
    example_inject_instructions()
    example_inject_agent_context()
    example_parse_response()
    example_runtime_selection()

    print("\n" + "#" * 60)
    print("# EXAMPLES COMPLETE")
    print("#" * 60 + "\n")


if __name__ == "__main__":
    main()
