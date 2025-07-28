#!/usr/bin/env python3
"""Test backward-compatible agent functions."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.agents import (
    get_documentation_agent_prompt,
    get_engineer_agent_prompt,
    get_research_agent_prompt,
    get_qa_agent_prompt,
    get_ops_agent_prompt,
    get_security_agent_prompt,
    get_version_control_agent_prompt,
    get_data_engineer_agent_prompt
)

def main():
    """Test backward-compatible agent functions."""
    test_functions = [
        ("Documentation", get_documentation_agent_prompt),
        ("Engineer", get_engineer_agent_prompt),
        ("Research", get_research_agent_prompt),
        ("QA", get_qa_agent_prompt),
        ("Ops", get_ops_agent_prompt),
        ("Security", get_security_agent_prompt),
        ("Version Control", get_version_control_agent_prompt),
        ("Data Engineer", get_data_engineer_agent_prompt),
    ]
    
    print("Testing backward-compatible agent functions...\n")
    
    all_passed = True
    for name, func in test_functions:
        try:
            prompt = func()
            print(f"✅ {name} Agent: {len(prompt)} chars")
        except Exception as e:
            print(f"❌ {name} Agent: {e}")
            all_passed = False
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())