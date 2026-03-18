#!/usr/bin/env python3
"""Test deduplication logic in isolation."""

from claude_mpm.services.agents.memory.content_manager import MemoryContentManager

# Create content manager
content_manager = MemoryContentManager(
    {"max_items_per_section": 15, "max_line_length": 120}
)

# Create initial content
initial_content = """# Agent Memory

## Implementation Guidelines
- Use async/await for all database operations

## Other Section
- Some other content
"""

print("Initial content:")
print(initial_content)
print("\n" + "=" * 60 + "\n")

# Add similar item
updated_content = content_manager.add_item_to_section(
    initial_content,
    "Implementation Guidelines",
    "Use async/await for all database operations and queries",
)

print("After adding similar item:")
print(updated_content)
print("\n" + "=" * 60 + "\n")

# Count items in Implementation Guidelines
lines = updated_content.split("\n")
count = 0
in_section = False
items = []
for line in lines:
    if line.startswith("## Implementation Guidelines"):
        in_section = True
    elif line.startswith("## ") and in_section:
        break
    elif in_section and line.strip().startswith("- "):
        count += 1
        items.append(line.strip())

print(f"Items in Implementation Guidelines: {count}")
for item in items:
    print(f"  {item}")
