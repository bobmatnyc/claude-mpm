#!/usr/bin/env python3
"""Demo script for JSON-RPC hook system."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from claude_mpm.hooks.json_rpc_hook_client import get_hook_client
from claude_mpm.hooks.base_hook import HookType


def main():
    """Demonstrate JSON-RPC hook system."""
    print("JSON-RPC Hook System Demo")
    print("=" * 50)
    
    # Get hook client (uses JSON-RPC by default)
    client = get_hook_client()
    
    # 1. Health check
    print("\n1. Health Check:")
    health = client.health_check()
    print(f"   Status: {health['status']}")
    print(f"   Executor: {health['executor']}")
    print(f"   Hook count: {health['hook_count']}")
    print(f"   Discovered hooks: {', '.join(health['discovered_hooks'])}")
    
    # 2. List available hooks
    print("\n2. Available Hooks:")
    hooks = client.list_hooks()
    for hook_type, hook_list in hooks.items():
        if hook_list:
            print(f"   {hook_type}:")
            for hook in hook_list:
                print(f"     - {hook['name']} (priority: {hook['priority']})")
    
    # 3. Execute submit hooks
    print("\n3. Execute Submit Hooks:")
    prompt = "Please fix TSK-123 and BUG-456 urgently!"
    print(f"   Prompt: '{prompt}'")
    
    results = client.execute_submit_hook(prompt)
    print(f"   Executed {len(results)} hooks")
    
    for result in results:
        print(f"\n   Hook: {result['hook_name']}")
        print(f"   Success: {result['success']}")
        if result.get('error'):
            print(f"   Error: {result['error']}")
        else:
            print(f"   Modified: {result.get('modified', False)}")
            if result.get('data'):
                print(f"   Data: {result['data']}")
            if result.get('execution_time_ms'):
                print(f"   Execution time: {result['execution_time_ms']:.2f}ms")
    
    # 4. Extract tickets from results
    print("\n4. Extract Tickets:")
    tickets = client.get_extracted_tickets(results)
    if tickets:
        print(f"   Found tickets: {tickets}")
    else:
        print("   No tickets found")
    
    # 5. Get modified data
    print("\n5. Modified Data:")
    modified_data = client.get_modified_data(results)
    if modified_data:
        for key, value in modified_data.items():
            print(f"   {key}: {value}")
    else:
        print("   No data was modified")
    
    # 6. Execute a specific hook
    print("\n6. Execute Specific Hook:")
    specific_results = client.execute_hook(
        hook_type=HookType.SUBMIT,
        context_data={"prompt": "Another test"},
        specific_hook="priority_detection"
    )
    
    if specific_results:
        result = specific_results[0]
        print(f"   Hook: {result['hook_name']}")
        print(f"   Success: {result['success']}")
        if result.get('data', {}).get('priority'):
            print(f"   Detected priority: {result['data']['priority']}")
    
    # 7. Demonstrate error handling
    print("\n7. Error Handling:")
    error_results = client.execute_hook(
        hook_type=HookType.SUBMIT,
        context_data={"prompt": "test"},
        specific_hook="nonexistent_hook"
    )
    
    if error_results:
        result = error_results[0]
        print(f"   Success: {result['success']}")
        print(f"   Error: {result.get('error', 'Unknown error')}")
    
    print("\n" + "=" * 50)
    print("Demo completed successfully!")


if __name__ == "__main__":
    main()