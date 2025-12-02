#!/usr/bin/env python3
"""
Memory System Demo - Shows how PM interacts with the memory management system
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.core.config import Config
from claude_mpm.core.framework_loader import FrameworkLoader
from claude_mpm.services.agents.memory.agent_memory_manager import \
    AgentMemoryManager


def demo_memory_system():
    """Demonstrate how the PM would use the memory system."""
    print("🧠 Memory Management System Demo")
    print("=" * 50)

    # 1. Show how framework loader loads MEMORY.md instructions
    print("\n1. Framework Loading Order")
    print("-" * 30)

    loader = FrameworkLoader()
    instructions = loader.get_framework_instructions()

    # Check loading order
    workflow_pos = instructions.find("PM Workflow Configuration")
    memory_pos = instructions.find("Static Memory Management Protocol")

    if workflow_pos != -1 and memory_pos != -1:
        print(f"✅ WORKFLOW.md loaded at position: {workflow_pos}")
        print(f"✅ MEMORY.md loaded at position: {memory_pos}")
        print(
            f"✅ MEMORY.md correctly loads AFTER WORKFLOW.md: {memory_pos > workflow_pos}"
        )
    else:
        print("❌ Could not find both sections in instructions")

    # 2. Show memory limits configuration
    print("\n2. Memory Limits Configuration")
    print("-" * 30)

    config = Config()
    memory_manager = AgentMemoryManager(config)

    default_limits = memory_manager.memory_limits
    research_limits = memory_manager._get_agent_limits("research")

    print(
        f"✅ Default memory limit: {default_limits['max_file_size_kb']}KB (~{default_limits['max_file_size_kb'] * 250} tokens)"
    )
    print(
        f"✅ Research agent override: {research_limits['max_file_size_kb']}KB (~{research_limits['max_file_size_kb'] * 250} tokens)"
    )

    # 3. Show PM memory workflow
    print("\n3. PM Memory Update Workflow")
    print("-" * 30)

    # Simulate PM detecting memory indicators
    user_feedback = "Remember to always validate input data before processing. This pattern should be applied to all data ingestion endpoints."

    print(f"📝 User feedback: '{user_feedback}'")
    print("\n🤔 PM Analysis:")

    # Memory trigger detection
    triggers = ["remember", "always", "pattern", "should be applied"]
    detected = [trigger for trigger in triggers if trigger in user_feedback.lower()]
    print(f"   ✅ Memory triggers detected: {detected}")

    # Agent routing
    print("   🎯 Agent routing: Data Engineer (data validation/ingestion)")

    # Memory update simulation
    agent_id = "data-engineer"
    current_memory = (
        memory_manager.load_memory(agent_id)
        or "# Data Engineer Agent Memory\n\n## Implementation Guidelines\n- Standard data processing patterns\n"
    )

    print(f"   📖 Current memory size: {len(current_memory)} chars")

    # PM would consolidate new knowledge
    new_knowledge = (
        "\n- Always validate input data before processing in data ingestion endpoints"
    )
    updated_memory = current_memory + new_knowledge

    print(f"   💾 Updated memory size: {len(updated_memory)} chars")
    print(f"   ✅ Memory update would be saved to: .claude-mpm/memories/{agent_id}.md")

    # 4. Show single-line fact format
    print("\n4. Memory File Format")
    print("-" * 30)

    sample_memory = """# Engineer Agent Memory

## Project Architecture
- Uses Django REST API framework with PostgreSQL database
- Frontend built with React and TypeScript
- Deployed on AWS ECS with RDS

## Implementation Guidelines
- Follow PEP 8 style guide for Python code
- Use type hints for all function parameters and returns
- Write unit tests with pytest for all new features

## Common Mistakes to Avoid
- Don't hardcode database credentials in source code
- Always handle exceptions in API endpoints
- Never skip input validation on user data

## Current Technical Context
- Working on user authentication microservice
- Using JWT tokens for session management
- Database migrations pending for user profile fields
"""

    print("✅ Sample memory file format:")
    print(sample_memory)

    # Validate format
    lines = sample_memory.split("\n")
    fact_lines = [line for line in lines if line.startswith("- ")]
    single_line_facts = all(len(line.strip()) < 200 for line in fact_lines)

    print(f"✅ Single-line facts maintained: {single_line_facts}")
    print(f"✅ Total fact lines: {len(fact_lines)}")

    print("\n" + "=" * 50)
    print("🎉 Memory system demo completed successfully!")
    print("The PM can now effectively manage agent memory using:")
    print("- Memory trigger word detection")
    print("- Agent-specific routing")
    print("- File size limits and validation")
    print("- Project-specific override support")


if __name__ == "__main__":
    demo_memory_system()
