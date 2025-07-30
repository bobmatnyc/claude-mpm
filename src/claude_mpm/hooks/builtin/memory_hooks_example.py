"""Example of how to register memory integration hooks.

WHY: This demonstrates how to register the memory hooks with the HookService
for automatic memory injection and learning extraction.
"""

from claude_mpm.hooks.memory_integration_hook import (
    MemoryPreDelegationHook,
    MemoryPostDelegationHook
)
from claude_mpm.services.hook_service import HookService
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
        return
    
    # Register pre-delegation hook for memory injection
    pre_hook = MemoryPreDelegationHook(config)
    hook_service.register_hook(pre_hook)
    
    # Register post-delegation hook for learning extraction
    # Only if auto-learning is enabled
    if config.get('memory.auto_learning', False):
        post_hook = MemoryPostDelegationHook(config)
        hook_service.register_hook(post_hook)


# Example usage:
if __name__ == "__main__":
    # This would typically be done during application initialization
    config = Config(config={
        'memory': {
            'enabled': True,
            'auto_learning': True,
            'limits': {
                'default_size_kb': 8,
                'max_items_per_section': 20
            }
        }
    })
    
    # Create hook service (normally this would be passed from main app)
    from claude_mpm.services.hook_service import HookService
    hook_service = HookService(config)
    
    # Register memory hooks
    register_memory_hooks(hook_service, config)
    
    print("Memory hooks registered successfully!")
    print(f"Pre-delegation hook: {hook_service.get_hooks('pre_delegation')}")
    print(f"Post-delegation hook: {hook_service.get_hooks('post_delegation')}")