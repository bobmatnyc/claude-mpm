#!/usr/bin/env python3
"""Comprehensive verification of Documentation Agent fixes."""

import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.services.agents.deployment.agent_template_builder import AgentTemplateBuilder


def main():
    """Verify both critical Documentation Agent fixes."""
    
    print("=" * 60)
    print("VERIFYING DOCUMENTATION AGENT FIXES")
    print("=" * 60)
    
    template_path = Path(__file__).parent.parent / "src/claude_mpm/agents/templates/documentation.json"
    
    # Load template
    with open(template_path, 'r') as f:
        template_data = json.load(f)
    
    print("\n1. MCP TOOL NAME FIX")
    print("-" * 40)
    
    # Check tools array
    tools = template_data['capabilities']['tools']
    correct_tool = 'mcp__claude-mpm-gateway__document_summarizer'
    incorrect_tool = 'mcp__claude-mpm-gateway__summarize_document'
    
    if correct_tool in tools:
        print(f"✓ Tools array has correct MCP tool: {correct_tool}")
    elif incorrect_tool in tools:
        print(f"✗ Tools array still has incorrect tool: {incorrect_tool}")
    else:
        print("✗ Neither correct nor incorrect MCP tool found in tools array")
    
    # Check instructions
    instructions = template_data['instructions']
    if correct_tool in instructions:
        # Count occurrences
        count = instructions.count(correct_tool)
        print(f"✓ Instructions use correct MCP tool ({count} occurrences)")
    elif incorrect_tool in instructions:
        count = instructions.count(incorrect_tool)
        print(f"✗ Instructions still use incorrect tool ({count} occurrences)")
    else:
        print("? No MCP tool references found in instructions")
    
    print("\n2. COLOR OVERRIDE FIX")
    print("-" * 40)
    
    # Check template color
    template_color = template_data['metadata'].get('color')
    print(f"• Template specifies color: {template_color}")
    
    # Build agent to test color respect
    builder = AgentTemplateBuilder()
    agent_content = builder.build_agent_markdown(
        agent_name="documentation-agent",
        template_path=template_path,
        base_agent_data={'name': 'Documentation Agent', 'version': '1.0.0'},
        source_info='template'
    )
    
    # Check generated color
    for line in agent_content.split('\n'):
        if line.startswith('color:'):
            generated_color = line.replace('color:', '').strip()
            if generated_color == template_color:
                print(f"✓ Generated agent respects template color: {generated_color}")
            else:
                print(f"✗ Generated agent uses '{generated_color}' instead of template color '{template_color}'")
            break
    
    print("\n3. SUMMARY")
    print("-" * 40)
    
    # Overall status
    mcp_fixed = correct_tool in tools and correct_tool in instructions
    color_fixed = template_color in agent_content
    
    if mcp_fixed and color_fixed:
        print("✅ ALL FIXES VERIFIED SUCCESSFULLY!")
        print("\nThe Documentation Agent now:")
        print("• Uses the correct MCP tool name: mcp__claude-mpm-gateway__document_summarizer")
        print("• Respects the template's cyan color instead of hardcoded orange")
    else:
        print("⚠️ SOME ISSUES REMAIN:")
        if not mcp_fixed:
            print("• MCP tool name still needs fixing")
        if not color_fixed:
            print("• Color override still needs fixing")
    
    print("\n" + "=" * 60)
    return 0 if (mcp_fixed and color_fixed) else 1


if __name__ == "__main__":
    exit(main())