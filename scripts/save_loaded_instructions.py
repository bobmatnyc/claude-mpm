#!/usr/bin/env python3
"""
Save the loaded PM instructions to a file for inspection.
"""

import sys
import os
from pathlib import Path
from datetime import datetime

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from claude_mpm.core.framework_loader import FrameworkLoader


def save_loaded_instructions():
    """Save the loaded PM instructions to a file."""
    
    print("Loading PM instructions...")
    
    # Create FrameworkLoader instance
    loader = FrameworkLoader()
    
    # Get the full instructions
    instructions = loader.get_framework_instructions()
    
    # Save to file with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"/tmp/pm_instructions_{timestamp}.md"
    
    with open(output_file, "w") as f:
        f.write("# Loaded PM Instructions\n\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n")
        f.write(f"Total Length: {len(instructions)} characters\n\n")
        f.write("---\n\n")
        f.write(instructions)
    
    print(f"✓ Instructions saved to: {output_file}")
    print(f"  Total length: {len(instructions)} characters")
    
    # Check for key sections
    sections = [
        "## TodoWrite Framework Requirements",
        "### Mandatory [Agent] Prefix Rules",
        "### TodoWrite Best Practices",
        "## Agent Response Format",
        "## Communication Standards",
        "## Standard Workflow"
    ]
    
    print("\nKey Sections Found:")
    for section in sections:
        if section in instructions:
            print(f"  ✓ {section}")
        else:
            print(f"  ✗ {section}")
    
    # Count TodoWrite examples
    todowrite_examples = [
        "[Research]",
        "[Engineer]",
        "[QA]",
        "[Documentation]",
        "[Security]",
        "[Ops]"
    ]
    
    print("\nTodoWrite Agent Prefixes Found:")
    for prefix in todowrite_examples:
        count = instructions.count(prefix)
        if count > 0:
            print(f"  ✓ {prefix}: {count} occurrences")
        else:
            print(f"  ✗ {prefix}: not found")
    
    return output_file


if __name__ == "__main__":
    output_file = save_loaded_instructions()
    print(f"\nYou can view the full instructions with:")
    print(f"  cat {output_file}")
    print(f"  less {output_file}")
    print(f"  open {output_file}  # (on macOS)")