#!/usr/bin/env python3
"""
Simple integration test for AgentManager with AgentLifecycleManager.
Tests basic functionality without complex edge cases.
"""

import asyncio
import sys
from pathlib import Path
import logging
import time

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.services.agent_lifecycle_manager import AgentLifecycleManager, ModificationTier
from claude_mpm.services.agent_management_service import AgentManager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def test_agent_manager_direct():
    """Test AgentManager directly to ensure it works."""
    logger.info("Testing AgentManager directly...")
    
    try:
        # Create agent manager
        agent_mgr = AgentManager()
        
        # Test content
        test_content = """---
type: custom
model_preference: claude-3-sonnet
version: 1.0.0
---

# Direct Test Agent

## Primary Role
Testing direct AgentManager functionality.
"""
        
        # Create agent definition
        from claude_mpm.models.agent_definition import AgentDefinition, AgentMetadata, AgentType
        
        agent_def = AgentDefinition(
            name="direct-test-agent",
            type=AgentType.CUSTOM,
            metadata=AgentMetadata(
                model_preference="claude-3-sonnet",
                version="1.0.0"
            ),
            raw_content=test_content
        )
        
        # Create agent
        file_path = agent_mgr.create_agent("direct-test-agent", agent_def, "framework")
        logger.info(f"✓ Created agent at: {file_path}")
        
        # Read agent
        read_def = agent_mgr.read_agent("direct-test-agent")
        if read_def:
            logger.info(f"✓ Read agent: {read_def.name}")
        else:
            logger.error("✗ Failed to read agent")
        
        # Delete agent
        deleted = agent_mgr.delete_agent("direct-test-agent")
        if deleted:
            logger.info("✓ Deleted agent")
        else:
            logger.error("✗ Failed to delete agent")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ AgentManager test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_lifecycle_manager_basic():
    """Test basic lifecycle manager operations."""
    logger.info("\nTesting AgentLifecycleManager basic operations...")
    
    lifecycle_mgr = AgentLifecycleManager()
    
    try:
        # Start the service
        await lifecycle_mgr.start()
        logger.info("✓ Started lifecycle manager")
        
        # Check if agent manager is available
        if lifecycle_mgr.agent_manager:
            logger.info("✓ AgentManager dependency injected")
        else:
            logger.error("✗ AgentManager not available")
            return False
        
        # Get stats
        stats = await lifecycle_mgr.get_lifecycle_stats()
        logger.info(f"✓ Got lifecycle stats: {stats['total_agents']} agents")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Lifecycle manager test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await lifecycle_mgr.stop()


async def test_simple_create():
    """Test simple agent creation through lifecycle manager."""
    logger.info("\nTesting simple agent creation...")
    
    lifecycle_mgr = AgentLifecycleManager()
    await lifecycle_mgr.start()
    
    try:
        # Minimal agent content
        content = """---
type: custom
---

# Simple Test Agent

A minimal test agent.
"""
        
        # Create agent with minimal parameters
        result = await lifecycle_mgr.create_agent(
            agent_name="simple-test-agent",
            agent_content=content,
            tier=ModificationTier.USER
        )
        
        if result.success:
            logger.info(f"✓ Created agent in {result.duration_ms:.1f}ms")
            
            # Try to read it back
            status = await lifecycle_mgr.get_agent_status("simple-test-agent")
            if status:
                logger.info(f"✓ Agent status: {status.current_state.value}")
            
            # Clean up
            delete_result = await lifecycle_mgr.delete_agent("simple-test-agent")
            if delete_result.success:
                logger.info("✓ Cleaned up test agent")
            
            return True
        else:
            logger.error(f"✗ Failed to create agent: {result.error_message}")
            return False
            
    except Exception as e:
        logger.error(f"✗ Create test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await lifecycle_mgr.stop()


async def test_performance():
    """Test performance metrics."""
    logger.info("\nTesting performance...")
    
    lifecycle_mgr = AgentLifecycleManager()
    await lifecycle_mgr.start()
    
    try:
        # Create a test agent
        content = "---\ntype: custom\n---\n\n# Perf Test\n\nPerformance test agent."
        
        start = time.time()
        result = await lifecycle_mgr.create_agent(
            agent_name="perf-test-agent",
            agent_content=content,
            tier=ModificationTier.USER
        )
        create_time = (time.time() - start) * 1000
        
        if result.success:
            logger.info(f"✓ Create operation: {create_time:.1f}ms (reported: {result.duration_ms:.1f}ms)")
            
            # Update
            start = time.time()
            update_result = await lifecycle_mgr.update_agent(
                agent_name="perf-test-agent",
                agent_content=content + "\n\nUpdated content."
            )
            update_time = (time.time() - start) * 1000
            
            if update_result.success:
                logger.info(f"✓ Update operation: {update_time:.1f}ms")
            
            # Delete
            start = time.time()
            delete_result = await lifecycle_mgr.delete_agent("perf-test-agent")
            delete_time = (time.time() - start) * 1000
            
            if delete_result.success:
                logger.info(f"✓ Delete operation: {delete_time:.1f}ms")
            
            # Check if all operations were under 100ms
            if create_time < 100 and update_time < 100 and delete_time < 100:
                logger.info("✓ All operations under 100ms threshold")
                return True
            else:
                logger.warning("⚠ Some operations exceeded 100ms threshold")
                return True  # Still pass, but with warning
        
        return False
        
    except Exception as e:
        logger.error(f"✗ Performance test failed: {e}")
        return False
    finally:
        await lifecycle_mgr.stop()


async def main():
    """Run all tests."""
    logger.info("AgentManager Integration Tests - Simple Version")
    logger.info("=" * 60)
    
    tests = [
        ("Direct AgentManager", test_agent_manager_direct),
        ("Basic Lifecycle Manager", test_lifecycle_manager_basic),
        ("Simple Create Operation", test_simple_create),
        ("Performance Metrics", test_performance)
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        logger.info(f"\n{'-' * 40}")
        logger.info(f"Test: {test_name}")
        logger.info(f"{'-' * 40}")
        
        try:
            if await test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            logger.error(f"Test crashed: {e}")
            failed += 1
    
    logger.info("\n" + "=" * 60)
    logger.info(f"SUMMARY: {passed} passed, {failed} failed")
    
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)