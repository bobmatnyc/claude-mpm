#!/usr/bin/env python3
"""Debug script to see the actual instructions content"""

import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from claude_mpm.core.framework_loader import FrameworkLoader
import logging

# Suppress most logs
logging.basicConfig(level=logging.ERROR)

def debug_instructions():
    """Debug the instructions content"""
    
    loader = FrameworkLoader()
    instructions = loader.get_framework_instructions()
    
    lines = instructions.split('\n')
    
    print("Looking for sections in instructions...")
    
    # Find all section headers
    for i, line in enumerate(lines):
        if line.startswith("##"):
            print(f"Line {i}: {line}")
    
    print("\nLooking for agent definitions...")
    
    # Find all agent definitions
    in_capabilities = False
    for i, line in enumerate(lines):
        if "Available Agent Capabilities" in line:
            in_capabilities = True
            print(f"Line {i}: Found capabilities section: {line}")
            continue
            
        if in_capabilities and line.startswith("###"):
            print(f"Line {i}: Agent definition: {line}")
            
        if in_capabilities and line.startswith("##") and "Agent Capabilities" not in line:
            print(f"Line {i}: End of capabilities section: {line}")
            break
    
    print("\nLooking specifically for QA...")
    for i, line in enumerate(lines):
        if "qa" in line.lower() and "##" in line:
            print(f"Line {i}: QA header: {line}")

if __name__ == "__main__":
    debug_instructions()