#!/usr/bin/env python3
"""
Test script to verify that PM instructions are loading correctly,
specifically checking for TodoWrite format patterns.
"""

import sys
import os
from pathlib import Path

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from claude_mpm.core.framework_loader import FrameworkLoader


def test_pm_loader():
    """Test that PM instructions load correctly with TodoWrite formats."""
    
    print("=" * 60)
    print("Testing PM Instructions Loader")
    print("=" * 60)
    
    try:
        # Create FrameworkLoader instance
        loader = FrameworkLoader()
        print("✓ FrameworkLoader instance created successfully")
        
        # Debug: Check what's loaded
        print(f"\nDebug Info:")
        print(f"  Framework path: {loader.framework_path}")
        print(f"  Framework content keys: {loader.framework_content.keys() if loader.framework_content else 'None'}")
        if loader.framework_content:
            if 'base_pm_instructions' in loader.framework_content:
                print(f"  BASE_PM.md loaded: {len(loader.framework_content['base_pm_instructions'])} chars")
            else:
                print(f"  BASE_PM.md NOT in framework_content")
            if 'instructions' in loader.framework_content:
                print(f"  INSTRUCTIONS.md loaded: {len(loader.framework_content['instructions'])} chars")
            else:
                print(f"  INSTRUCTIONS.md NOT in framework_content")
        
        # Load PM instructions
        instructions = loader.get_framework_instructions()
        print(f"✓ Instructions loaded successfully")
        print(f"  Total length: {len(instructions)} characters")
        
        # Check for key TodoWrite format patterns
        patterns_to_check = [
            # Basic TodoWrite format
            "[<assigned agent>]: <task>",
            
            # Specific examples from BASE_PM.md (using actual text)
            "[Research] Analyze authentication patterns in codebase",
            "[Engineer] Implement user registration endpoint",
            "[QA] Test payment flow with edge cases",
            "[Documentation] Update API docs after QA sign-off",
            "[Security] Audit JWT implementation for vulnerabilities",
            "[Ops] Configure CI/CD pipeline for staging",
            
            # Error format examples
            "[Agent] Task (ERROR - Attempt 1/3)",
            "[Agent] Task (ERROR - Attempt 2/3)",
            "[Agent] Task (BLOCKED - requires user input)",
            
            # TodoWrite section headers (check actual headers)
            "## TodoWrite Framework Requirements",
            "### TodoWrite Best Practices",
            "### Mandatory [Agent] Prefix Rules",
            
            # Key TodoWrite instructions
            "ALWAYS use [Agent] prefix for delegated tasks",
            "prefix format: [<assigned agent>]",
            "Status: pending → in_progress → completed"
        ]
        
        print("\n" + "=" * 60)
        print("Checking for TodoWrite Format Patterns:")
        print("=" * 60)
        
        found_patterns = []
        missing_patterns = []
        
        for pattern in patterns_to_check:
            if pattern in instructions:
                found_patterns.append(pattern)
                print(f"✓ Found: '{pattern[:50]}{'...' if len(pattern) > 50 else ''}'")
            else:
                missing_patterns.append(pattern)
                print(f"✗ Missing: '{pattern[:50]}{'...' if len(pattern) > 50 else ''}'")
        
        # Check for BASE_PM.md content inclusion
        print("\n" + "=" * 60)
        print("Checking BASE_PM.md Content Inclusion:")
        print("=" * 60)
        
        base_pm_indicators = [
            "Multi-Agent Project Manager Framework",
            "Agent Orchestration System",
            "Agent Response Format",
            "Memory-Conscious Implementation",
            "Standard Workflow",
            "Communication Standards"
        ]
        
        for indicator in base_pm_indicators:
            if indicator in instructions:
                print(f"✓ Found BASE_PM.md content: '{indicator}'")
            else:
                print(f"✗ Missing BASE_PM.md content: '{indicator}'")
        
        # Extract and display TodoWrite section if found
        print("\n" + "=" * 60)
        print("TodoWrite Section Extract:")
        print("=" * 60)
        
        # Try to find and extract TodoWrite section
        todowrite_start = instructions.find("## TodoWrite")
        if todowrite_start != -1:
            # Find the next section (## ) or take 2000 chars
            next_section = instructions.find("\n## ", todowrite_start + 1)
            if next_section == -1:
                todowrite_section = instructions[todowrite_start:todowrite_start + 2000]
            else:
                todowrite_section = instructions[todowrite_start:next_section]
            
            # Print first 1000 chars of TodoWrite section
            print(todowrite_section[:1000])
            if len(todowrite_section) > 1000:
                print("\n... (section continues)")
        else:
            print("✗ TodoWrite section not found in instructions")
        
        # Summary
        print("\n" + "=" * 60)
        print("Summary:")
        print("=" * 60)
        print(f"✓ Instructions loaded: {len(instructions)} characters")
        print(f"✓ Patterns found: {len(found_patterns)}/{len(patterns_to_check)}")
        
        if missing_patterns:
            print(f"\n⚠️  Missing patterns ({len(missing_patterns)}):")
            for pattern in missing_patterns[:5]:  # Show first 5 missing
                print(f"  - {pattern}")
            if len(missing_patterns) > 5:
                print(f"  ... and {len(missing_patterns) - 5} more")
        
        # Overall status
        if len(found_patterns) >= len(patterns_to_check) * 0.7:  # 70% threshold
            print("\n✅ PM Instructions are loading correctly with TodoWrite format!")
            return True
        else:
            print("\n⚠️  PM Instructions may not be loading completely.")
            print("   Some TodoWrite patterns are missing.")
            return False
            
    except Exception as e:
        print(f"\n❌ Error loading PM instructions: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_pm_loader()
    sys.exit(0 if success else 1)