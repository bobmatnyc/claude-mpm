#!/usr/bin/env python3
"""Script to register memory hooks with the hook service.

This demonstrates how memory hooks will be integrated into the system.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.services.hook_service import HookService
from claude_mpm.hooks.memory_integration_hook import (
    MemoryPreDelegationHook,
    MemoryPostDelegationHook
)
from claude_mpm.hooks.base_hook import HookContext, HookType
from claude_mpm.core.config import Config


def register_memory_hooks(hook_service: HookService, config: Config = None):
    """Register memory integration hooks with the hook service.
    
    WHY: To enable automatic memory management, both hooks need to be
    registered with appropriate priorities:
    - Pre-hook runs early (priority 20) to inject memory into context
    - Post-hook runs late (priority 80) to extract learnings after processing
    
    Args:
        hook_service: The HookService instance to register with
        config: Optional configuration (will create default if not provided)
    """
    config = config or Config()
    
    # Only register if memory system is enabled
    if not config.get('memory.enabled', True):
        print("Memory system is disabled in configuration")
        return
    
    # Register pre-delegation hook for memory injection
    pre_hook = MemoryPreDelegationHook(config)
    hook_service.register_hook(pre_hook)
    print(f"✅ Registered memory pre-delegation hook (priority: {pre_hook.priority})")
    
    # Register post-delegation hook for learning extraction
    # Only if auto-learning is enabled
    if config.get('memory.auto_learning', False):
        post_hook = MemoryPostDelegationHook(config)
        hook_service.register_hook(post_hook)
        print(f"✅ Registered memory post-delegation hook (priority: {post_hook.priority})")
    else:
        print("ℹ️  Auto-learning is disabled - skipping post-delegation hook")


def main():
    """Main function to demonstrate hook registration."""
    # Create configuration with memory enabled
    config = Config(config={
        'memory': {
            'enabled': True,
            'auto_learning': True,  # Enable for demonstration
            'limits': {
                'default_size_kb': 8,
                'max_sections': 10,
                'max_items_per_section': 15
            }
        },
        'hooks': {
            'enabled': True
        }
    })
    
    # Create hook service
    hook_service = HookService(config)
    print("🔧 Created HookService")
    
    # Register memory hooks
    register_memory_hooks(hook_service, config)
    
    # Show registered hooks
    print("\n📋 Registered Hooks:")
    pre_hooks = hook_service.pre_delegation_hooks
    post_hooks = hook_service.post_delegation_hooks
    print(f"Pre-delegation hooks: {[h.name for h in pre_hooks]}")
    print(f"Post-delegation hooks: {[h.name for h in post_hooks]}")
    
    # Simulate a delegation with memory
    print("\n🧪 Testing hook execution...")
    
    # Pre-delegation context
    pre_context = HookContext(
        hook_type=HookType.PRE_DELEGATION,
        data={
            'agent': 'research',
            'prompt': 'Analyze the codebase structure',
            'session_id': 'test-123'
        },
        metadata={},
        timestamp=None
    )
    
    # Execute pre-delegation hooks
    pre_result = hook_service.execute_pre_delegation_hooks(pre_context)
    if pre_result.success and pre_result.data and 'agent_memory' in pre_result.data:
        print("✅ Memory injected into context")
        print(f"   Memory preview: {pre_result.data['agent_memory'][:100]}...")
    
    # Simulate agent response
    agent_response = """
    I've analyzed the codebase structure. Discovered pattern: The project uses 
    service-oriented architecture with clear separation of concerns. 
    Best practice: Always use PathResolver for path operations.
    Architecture: Three-tier agent hierarchy provides good modularity.
    """
    
    # Post-delegation context
    post_context = HookContext(
        hook_type=HookType.POST_DELEGATION,
        data={
            'agent': 'research',
            'result': {'content': agent_response},
            'session_id': 'test-123'
        },
        metadata={},
        timestamp=None
    )
    
    # Execute post-delegation hooks
    post_result = hook_service.execute_post_delegation_hooks(post_context)
    print("✅ Post-delegation hooks executed")
    
    # Show statistics
    stats = hook_service.get_stats()
    print(f"\n📊 Hook Statistics:")
    print(f"   Pre-delegation executions: {stats['pre_delegation_executed']}")
    print(f"   Post-delegation executions: {stats['post_delegation_executed']}")
    print(f"   Total errors: {stats['errors']}")


if __name__ == "__main__":
    main()