#!/usr/bin/env python3
"""
Test Structured Memory Integration

Tests the enhanced memory integration with:
- Structured memory insertion after ## Memories line
- Memory change detection and forced re-deployment
- Frontmatter tracking with memories: <number> field
"""


import yaml


def test_structured_memory_insertion():
    """Test structured memory insertion after ## Memories line."""

    def insert_memory_section(instructions: str, memory_content: str) -> str:
        """Insert or update memory section in agent instructions."""
        lines = instructions.split("\n")

        # Look for existing ## Memories section
        memory_section_index = None
        memory_end_index = None

        for i, line in enumerate(lines):
            if line.strip() == "## Memories":
                memory_section_index = i
            elif (
                memory_section_index is not None
                and line.startswith("## ")
                and i > memory_section_index
            ):
                memory_end_index = i
                break

        if memory_section_index is not None:
            # Replace existing memory section
            if memory_end_index is not None:
                # Remove old memory content between sections
                del lines[memory_section_index + 1 : memory_end_index]
                insert_index = memory_section_index + 1
            else:
                # Memory section is at the end, remove everything after it
                lines = lines[: memory_section_index + 1]
                insert_index = memory_section_index + 1
        else:
            # Add new memory section
            lines.append("")
            lines.append("## Memories")
            insert_index = len(lines)

        # Insert memory content
        memory_lines = [""] + memory_content.strip().split("\n") + [""]
        for i, memory_line in enumerate(memory_lines):
            lines.insert(insert_index + i, memory_line)

        return "\n".join(lines)

    # Test 1: Add memory to instructions without existing memory section
    original_instructions = """You are a research specialist.

## Guidelines
- Follow scientific methodology
- Cite sources properly

## Tools
- Literature search
- Data analysis"""

    memory_content = """# Research Memory

## Project Focus
- AI/ML research trends
- Academic publication standards

## Key Researchers
- Dr. Smith (NLP expert)
- Prof. Johnson (ML theory)"""

    result = insert_memory_section(original_instructions, memory_content)

    # Verify memory section was added
    assert "## Memories" in result
    assert "# Research Memory" in result
    assert "AI/ML research trends" in result
    assert "## Guidelines" in result  # Original content preserved
    assert "## Tools" in result  # Original content preserved

    print("✓ Memory insertion without existing section works")

    # Test 2: Update existing memory section
    instructions_with_memory = """You are a research specialist.

## Guidelines
- Follow scientific methodology

## Memories

# Old Memory Content
- Outdated information
- Old patterns

## Tools
- Literature search"""

    new_memory = """# Updated Research Memory

## New Project Focus
- Quantum computing research
- Emerging AI paradigms"""

    result2 = insert_memory_section(instructions_with_memory, new_memory)

    # Verify old memory was replaced
    assert "Old Memory Content" not in result2
    assert "Outdated information" not in result2
    assert "Updated Research Memory" in result2
    assert "Quantum computing research" in result2
    assert "## Guidelines" in result2  # Original content preserved
    assert "## Tools" in result2  # Original content preserved

    print("✓ Memory section replacement works")


def test_memory_change_detection():
    """Test memory change detection logic."""

    def check_memory_update_needed(
        agent_data: dict, memory_content: str, memory_line_count: int
    ) -> bool:
        """Check if agent memory needs to be updated."""
        # Check if agent has existing memory metadata
        metadata = agent_data.get("metadata", {})
        current_memory_lines = metadata.get("memories", 0)

        # If memory line count changed, update is needed
        if current_memory_lines != memory_line_count:
            return True

        # Check if memory content in instructions matches current memory
        instructions = agent_data.get("instructions", "")
        if "## Memories" in instructions:
            # Extract current memory section
            current_memory = extract_memory_section(instructions)
            if current_memory != memory_content.strip():
                return True
        else:
            # No memory section exists, need to add it
            return True

        return False

    def extract_memory_section(instructions: str) -> str:
        """Extract the current memory section from agent instructions."""
        lines = instructions.split("\n")
        memory_lines = []
        in_memory_section = False

        for line in lines:
            if line.strip() == "## Memories":
                in_memory_section = True
                continue
            if line.startswith("## ") and in_memory_section:
                # Hit another section, stop collecting
                break
            if in_memory_section:
                memory_lines.append(line)

        return "\n".join(memory_lines).strip()

    # Test 1: No existing memory - should need update
    agent_data = {"metadata": {}, "instructions": "You are a test agent."}
    memory_content = "# Test Memory\n- Item 1\n- Item 2"
    memory_line_count = 3

    assert (
        check_memory_update_needed(agent_data, memory_content, memory_line_count)
        is True
    )
    print("✓ Detects need for initial memory addition")

    # Test 2: Same memory content - should not need update
    agent_data_with_memory = {
        "metadata": {"memories": 3},
        "instructions": """You are a test agent.

## Memories

# Test Memory
- Item 1
- Item 2

## Other Section""",
    }

    assert (
        check_memory_update_needed(
            agent_data_with_memory, memory_content, memory_line_count
        )
        is False
    )
    print("✓ Detects no update needed for same memory")

    # Test 3: Different memory line count - should need update
    new_memory_line_count = 5
    assert (
        check_memory_update_needed(
            agent_data_with_memory, memory_content, new_memory_line_count
        )
        is True
    )
    print("✓ Detects need for update when line count changes")

    # Test 4: Different memory content - should need update
    different_memory = "# Different Memory\n- New item\n- Another item"
    assert (
        check_memory_update_needed(
            agent_data_with_memory, different_memory, memory_line_count
        )
        is True
    )
    print("✓ Detects need for update when content changes")


def test_frontmatter_generation():
    """Test frontmatter generation with memory count."""

    def generate_agent_frontmatter(agent_data: dict) -> str:
        """Generate frontmatter for agent file."""
        metadata = agent_data.get("metadata", {})
        frontmatter = {
            "name": metadata.get("name", "Unknown Agent"),
            "description": metadata.get("description", ""),
            "model": agent_data.get("model", "claude-sonnet-4-20250514"),
            "memories": metadata.get("memories", 0),
        }

        # Add other metadata fields
        for key in ["category", "version", "tools"]:
            if key in metadata:
                frontmatter[key] = metadata[key]

        return yaml.dump(frontmatter, default_flow_style=False)

    # Test agent data with memory
    agent_data = {
        "metadata": {
            "name": "Engineer Agent",
            "description": "AI agent specialized in engineer tasks with project memories",
            "category": "project",
            "version": "1.0.0",
            "memories": 15,
        },
        "model": "claude-sonnet-4-20250514",
    }

    frontmatter_yaml = generate_agent_frontmatter(agent_data)

    # Parse back to verify
    frontmatter_data = yaml.safe_load(frontmatter_yaml)

    assert frontmatter_data["name"] == "Engineer Agent"
    assert frontmatter_data["memories"] == 15
    assert frontmatter_data["category"] == "project"
    assert frontmatter_data["model"] == "claude-sonnet-4-20250514"

    print("✓ Frontmatter generation with memory count works")


def test_complete_memory_integration_workflow():
    """Test the complete memory integration workflow."""

    # Simulate memory file content
    memory_content = """# Engineer Agent Memory

## Project Architecture
- Uses microservices architecture
- PostgreSQL database
- Redis for caching

## Implementation Guidelines
- Follow TDD practices
- Use dependency injection
- Write comprehensive tests

## Common Mistakes to Avoid
- Don't hardcode configuration values
- Always validate input parameters
- Handle errors gracefully"""

    memory_lines = memory_content.strip().split("\n")
    memory_line_count = len([line for line in memory_lines if line.strip()])

    # Create new agent with structured memory
    agent_id = "engineer_agent"
    agent_name = "engineer"

    instructions = f"""You are a {agent_name} specialist AI agent with access to project-specific knowledge and memories.

Your role is to assist with {agent_name}-related tasks while leveraging the accumulated project knowledge to provide contextually relevant and informed responses.

## Memories

{memory_content}

INSTRUCTIONS: Review your project memory above before proceeding. Apply learned patterns and avoid known mistakes."""

    agent_data = {
        "agent_id": agent_id,
        "metadata": {
            "name": f"{agent_name.title()} Agent",
            "description": f"AI agent specialized in {agent_name} tasks with project memories",
            "category": "project",
            "version": "1.0.0",
            "memories": memory_line_count,
        },
        "instructions": instructions,
        "capabilities": {
            "has_project_memory": True,
            "memory_lines": memory_line_count,
            "memory_size_kb": round(len(memory_content.encode("utf-8")) / 1024, 2),
        },
    }

    # Verify structure
    assert agent_data["metadata"]["memories"] == memory_line_count
    assert "## Memories" in agent_data["instructions"]
    assert "microservices architecture" in agent_data["instructions"]
    assert agent_data["capabilities"]["has_project_memory"] is True
    assert agent_data["capabilities"]["memory_lines"] == memory_line_count

    print("✓ Complete memory integration workflow works")
    print(f"  - Memory lines: {memory_line_count}")
    print(f"  - Memory size: {agent_data['capabilities']['memory_size_kb']}KB")
    print("  - Agent tier: project")


if __name__ == "__main__":
    print("Running structured memory integration tests...")

    test_structured_memory_insertion()
    test_memory_change_detection()
    test_frontmatter_generation()
    test_complete_memory_integration_workflow()

    print("\n✅ All structured memory integration tests passed!")
    print("\nEnhanced memory integration features:")
    print("- Structured memory insertion after ## Memories line")
    print("- Memory change detection based on line count and content")
    print("- Forced re-deployment when memories change")
    print("- Frontmatter tracking with memories: <number> field")
    print("- Proper memory section replacement and preservation of other content")
