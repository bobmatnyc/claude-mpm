#!/usr/bin/env python3
"""Debug QA agent detection"""

import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.core.framework_loader import FrameworkLoader
import logging

# Suppress most logs
logging.basicConfig(level=logging.ERROR)

def debug_qa():
    """Debug QA detection"""
    
    loader = FrameworkLoader()
    instructions = loader.get_framework_instructions()
    
    lines = instructions.split('\n')
    
    print("Debugging QA agent detection...")
    
    in_capabilities_section = False
    qa_found = []
    
    for i, line in enumerate(lines):
        if "## Available Agent Capabilities" in line:
            in_capabilities_section = True
            print(f"Line {i}: STARTED capabilities section: {line}")
            continue
            
        if in_capabilities_section and line.startswith("## ") and "Agent Capabilities" not in line:
            in_capabilities_section = False
            print(f"Line {i}: ENDED capabilities section: {line}")
            continue
            
        if in_capabilities_section:
            if line.startswith("### "):
                print(f"Line {i}: Agent found: {line}")
                if "qa" in line.lower():
                    qa_found.append((i, line))
    
    print(f"\nQA agents found: {len(qa_found)}")
    for i, line in qa_found:
        print(f"  Line {i}: {line}")

if __name__ == "__main__":
    debug_qa()