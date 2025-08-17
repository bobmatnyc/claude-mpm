#!/usr/bin/env python3
"""
Demonstration of the unified ticket tool API.

WHY: This script demonstrates how the unified ticket tool provides a cleaner,
more intuitive API compared to having 5 separate tools.

DESIGN DECISIONS:
- Shows the before (5 tools) vs after (1 tool) comparison
- Demonstrates the simplicity of the unified interface
- Highlights better discoverability and mental model alignment
"""

import json

def demo_old_api():
    """Demonstrate the old API with 5 separate tools."""
    print("OLD API - 5 Separate Tools")
    print("=" * 50)
    
    tools = [
        {
            "name": "ticket_create",
            "description": "Create a new ticket",
            "parameters": ["type", "title", "description", "priority", "tags"]
        },
        {
            "name": "ticket_list",
            "description": "List tickets with filters",
            "parameters": ["limit", "type", "status", "priority"]
        },
        {
            "name": "ticket_update",
            "description": "Update ticket status or priority",
            "parameters": ["ticket_id", "status", "priority", "comment"]
        },
        {
            "name": "ticket_view",
            "description": "View ticket details",
            "parameters": ["ticket_id", "format"]
        },
        {
            "name": "ticket_search",
            "description": "Search tickets by keywords",
            "parameters": ["query", "limit", "type"]
        }
    ]
    
    print("\nAvailable tools:")
    for tool in tools:
        print(f"  • {tool['name']}: {tool['description']}")
    
    print("\nExample usage:")
    print("  Tool: ticket_create")
    print("  Parameters: {")
    print('    "type": "task",')
    print('    "title": "Fix login bug",')
    print('    "priority": "high"')
    print("  }")
    print()
    print("  Tool: ticket_list")
    print("  Parameters: {")
    print('    "status": "open",')
    print('    "limit": 10')
    print("  }")
    
    print("\n❌ Problems with this approach:")
    print("  • Need to remember 5 different tool names")
    print("  • Each tool has different parameter sets to learn")
    print("  • Mental overhead of choosing the right tool")
    print("  • More complex MCP configuration")
    print("  • Harder to discover all ticket operations")


def demo_new_api():
    """Demonstrate the new unified API."""
    print("\nNEW API - Single Unified Tool")
    print("=" * 50)
    
    tool = {
        "name": "ticket",
        "description": "Unified ticket management tool for all operations",
        "operations": ["create", "list", "update", "view", "search"],
        "parameters": {
            "operation": "required - the operation to perform",
            "common": ["limit", "type", "status", "priority"],
            "create": ["title", "description", "tags", "parent_issue"],
            "update": ["ticket_id", "comment"],
            "view": ["ticket_id", "format"],
            "search": ["query"]
        }
    }
    
    print("\nAvailable tool:")
    print(f"  • {tool['name']}: {tool['description']}")
    print(f"    Operations: {', '.join(tool['operations'])}")
    
    print("\nExample usage:")
    print("  Tool: ticket")
    print("  Parameters: {")
    print('    "operation": "create",')
    print('    "type": "task",')
    print('    "title": "Fix login bug",')
    print('    "priority": "high"')
    print("  }")
    print()
    print("  Tool: ticket")
    print("  Parameters: {")
    print('    "operation": "list",')
    print('    "status": "open",')
    print('    "limit": 10')
    print("  }")
    
    print("\n✅ Benefits of this approach:")
    print("  • Single tool name to remember: 'ticket'")
    print("  • Intuitive operation parameter matches mental model")
    print("  • All ticket operations discoverable in one place")
    print("  • Cleaner MCP configuration")
    print("  • Easier to extend with new operations")
    print("  • Better alignment with RESTful/CRUD patterns")


def show_mcp_config_comparison():
    """Show the MCP configuration difference."""
    print("\nMCP Configuration Comparison")
    print("=" * 50)
    
    print("\nOLD - Multiple tools in MCP config:")
    old_config = {
        "tools": [
            {"name": "ticket_create"},
            {"name": "ticket_list"},
            {"name": "ticket_update"},
            {"name": "ticket_view"},
            {"name": "ticket_search"}
        ]
    }
    print(json.dumps(old_config, indent=2))
    
    print("\nNEW - Single tool in MCP config:")
    new_config = {
        "tools": [
            {"name": "ticket"}
        ]
    }
    print(json.dumps(new_config, indent=2))
    
    print("\n📊 Reduction: 5 tools → 1 tool (80% reduction in tool count)")


def show_usage_examples():
    """Show practical usage examples."""
    print("\nPractical Usage Examples")
    print("=" * 50)
    
    examples = [
        {
            "scenario": "Creating a bug report",
            "old": 'Use tool "ticket_create" with type="issue"',
            "new": 'Use tool "ticket" with operation="create", type="issue"'
        },
        {
            "scenario": "Finding high priority tasks",
            "old": 'Use tool "ticket_search" or "ticket_list" (which one?)',
            "new": 'Use tool "ticket" with operation="list", priority="high"'
        },
        {
            "scenario": "Updating ticket status",
            "old": 'Use tool "ticket_update" with status parameter',
            "new": 'Use tool "ticket" with operation="update", status="done"'
        },
        {
            "scenario": "Viewing ticket details",
            "old": 'Use tool "ticket_view" with ticket_id',
            "new": 'Use tool "ticket" with operation="view", ticket_id="TSK-001"'
        }
    ]
    
    for i, example in enumerate(examples, 1):
        print(f"\n{i}. {example['scenario']}:")
        print(f"   OLD: {example['old']}")
        print(f"   NEW: {example['new']}")


def main():
    """Run the demonstration."""
    print("\n" + "=" * 70)
    print(" UNIFIED TICKET TOOL API DEMONSTRATION")
    print("=" * 70)
    
    demo_old_api()
    demo_new_api()
    show_mcp_config_comparison()
    show_usage_examples()
    
    print("\n" + "=" * 70)
    print(" SUMMARY")
    print("=" * 70)
    print("""
The unified ticket tool provides a cleaner, more intuitive interface
by consolidating 5 separate tools into 1 tool with an operation parameter.

Key improvements:
• Simpler API - just one tool to learn and use
• Better mental model - "ticket" + operation is intuitive
• Easier discovery - all operations in one place
• Cleaner configuration - less clutter in MCP config
• More extensible - easy to add new operations

This follows the principle of "operations on resources" rather than
"separate tools for each action", similar to RESTful API design.
""")


if __name__ == "__main__":
    main()