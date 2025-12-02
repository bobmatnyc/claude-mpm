#!/usr/bin/env python3
"""Check the size of loaded instructions and content."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.core.framework_loader import FrameworkLoader
from claude_mpm.services.system_instructions_service import SystemInstructionsService


def get_size_mb(obj):
    """Get approximate size of an object in MB."""
    import pickle

    try:
        data = pickle.dumps(obj)
        return len(data) / (1024 * 1024)
    except:
        # Fallback to string representation
        return len(str(obj)) / (1024 * 1024)


# Test FrameworkLoader content
loader = FrameworkLoader()
instructions = loader.get_framework_instructions()
content = loader.framework_content

print("FrameworkLoader Analysis:")
print(f"  Instructions string length: {len(instructions):,} chars")
print(f"  Instructions size: {get_size_mb(instructions):.2f} MB")
print(f"  Framework content size: {get_size_mb(content):.2f} MB")
print()

# Analyze what's in framework_content
print("Framework content keys:")
for key in content:
    if isinstance(content[key], str):
        print(f"  {key}: {len(content[key]):,} chars")
    elif isinstance(content[key], dict):
        print(f"  {key}: {len(content[key])} items")
    else:
        print(f"  {key}: {type(content[key])}")
print()

# Check agent registry
if hasattr(loader, "agent_registry"):
    registry = loader.agent_registry
    print("Agent Registry:")
    if hasattr(registry, "registry"):
        reg = registry.registry
        print(f"  SimpleAgentRegistry agents: {len(reg.agents)} agents")
    if hasattr(registry, "_unified_registry"):
        unified = registry._unified_registry
        if hasattr(unified, "registry"):
            print(f"  UnifiedRegistry agents: {len(unified.registry)} agents")
print()

# Test SystemInstructionsService
service = SystemInstructionsService()
service_instructions = service.load_system_instructions()

print("SystemInstructionsService Analysis:")
print(f"  Instructions length: {len(service_instructions):,} chars")
print(f"  Instructions size: {get_size_mb(service_instructions):.2f} MB")
print(f"  Has cached loader: {service._framework_loader is not None}")
print(f"  Has cached instructions: {service._loaded_instructions is not None}")
