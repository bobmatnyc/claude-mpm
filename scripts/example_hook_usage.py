#!/usr/bin/env python3
"""Example of using the HookService with memory integration hooks.

WHY: This demonstrates how to integrate the HookService with the memory
integration hooks to automatically inject and extract agent memory.

USAGE: python scripts/example_hook_usage.py
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.services.hook_service import HookService
from claude_mpm.hooks.memory_integration_hook import (
    MemoryPreDelegationHook,
    MemoryPostDelegationHook
)
from claude_mpm.core.config import Config
from claude_mpm.core.logger import setup_logging, get_logger
from claude_mpm.hooks.base_hook import HookContext, HookType
from datetime import datetime

# Set up logging
setup_logging()
logger = get_logger(__name__)


def main():
    """Demonstrate HookService usage with memory hooks."""
    
    # Create configuration with memory enabled
    config = Config({
        "memory": {
            "enabled": True,
            "storage_path": "agent_memory"
        },
        "hooks": {
            "enabled": True
        }
    })
    
    # Create HookService
    hook_service = HookService(config)
    logger.info("Created HookService")
    
    # Create and register memory hooks
    pre_memory_hook = MemoryPreDelegationHook(config)
    post_memory_hook = MemoryPostDelegationHook(config)
    
    hook_service.register_hook(pre_memory_hook)
    hook_service.register_hook(post_memory_hook)
    
    logger.info("Registered memory integration hooks")
    
    # List registered hooks
    hooks = hook_service.list_hooks()
    logger.info(f"Registered hooks: {hooks}")
    
    # Simulate a delegation context
    delegation_context = HookContext(
        hook_type=HookType.PRE_DELEGATION,
        data={
            "agent": "research",
            "prompt": "Analyze the authentication system",
            "user_context": "Working on security improvements"
        },
        metadata={},
        timestamp=datetime.now(),
        session_id="test_session_123"
    )
    
    logger.info("Executing pre-delegation hooks...")
    
    # Execute pre-delegation hooks (this will inject memory)
    pre_result = hook_service.execute_pre_delegation_hooks(delegation_context)
    
    # Check if memory was injected
    if pre_result.success and pre_result.data and "agent_memory" in pre_result.data:
        logger.info("Memory successfully injected into context")
        logger.info(f"Memory preview: {str(pre_result.data['agent_memory'])[:200]}...")
    else:
        logger.info("No memory found for agent (this is normal for first run)")
    
    # Simulate agent execution result context
    agent_result_data = {
        "result": """
        I've analyzed the authentication system and found:
        
        1. The system uses JWT tokens with bcrypt password hashing
        2. Token expiration is set to 24 hours
        3. Refresh tokens are stored in Redis
        
        LEARNED: The authentication flow follows OAuth2 standards with 
        custom extensions for multi-factor authentication.
        
        PATTERN: All API endpoints require Bearer token authentication
        except for /auth/login and /auth/refresh.
        
        DISCOVERED: The bcrypt cost factor is set to 12, which provides
        good security while maintaining reasonable performance.
        """,
        "agent": "research",
        "success": True,
        "execution_time": 5.2
    }
    
    # Create post-delegation context
    post_context = HookContext(
        hook_type=HookType.POST_DELEGATION,
        data=agent_result_data,
        metadata={},
        timestamp=datetime.now(),
        session_id="test_session_123"
    )
    
    logger.info("Executing post-delegation hooks...")
    
    # Execute post-delegation hooks (this will extract learnings)
    post_result = hook_service.execute_post_delegation_hooks(post_context)
    
    # Check if learnings were extracted
    if post_result.success and post_result.data and "extracted_learnings" in post_result.data:
        logger.info("Learnings successfully extracted:")
        for learning in post_result.data["extracted_learnings"]:
            logger.info(f"  - {learning}")
    
    # Show execution statistics
    stats = hook_service.get_stats()
    logger.info(f"Execution statistics: {stats}")
    
    # Demonstrate error handling by disabling hooks
    logger.info("\nDemonstrating configuration-based disabling...")
    
    # Disable hooks via config
    config._config["hooks"]["enabled"] = False
    
    # Try executing again
    test_context = HookContext(
        hook_type=HookType.PRE_DELEGATION,
        data={"agent": "test"},
        metadata={},
        timestamp=datetime.now()
    )
    result = hook_service.execute_pre_delegation_hooks(test_context)
    logger.info("Hooks disabled - no execution should occur")
    
    # Re-enable and test memory-specific disabling
    config._config["hooks"]["enabled"] = True
    config._config["memory"]["enabled"] = False
    
    result = hook_service.execute_pre_delegation_hooks(test_context)
    logger.info("Memory disabled - memory hooks should not execute")
    
    # Show final stats
    final_stats = hook_service.get_stats()
    logger.info(f"Final statistics: {final_stats}")


if __name__ == "__main__":
    main()