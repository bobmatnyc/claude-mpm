import pytest

#!/usr/bin/env python3
"""
Test script for AgentManager integration with AgentLifecycleManager.

WHY: This script verifies that the integration between AgentManager and
AgentLifecycleManager works correctly, ensuring backward compatibility
while leveraging the new content management capabilities.

USAGE: python scripts/test_agent_manager_integration.py
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.services.agents.deployment import AgentLifecycleManager
from claude_mpm.services.agents.registry.modification_tracker import ModificationTier

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@pytest.mark.asyncio
async def test_create_agent():
    """Test creating an agent through the lifecycle manager."""
    logger.info("Testing agent creation...")

    lifecycle_mgr = AgentLifecycleManager()
    await lifecycle_mgr.start()

    try:
        # Test agent content
        agent_content = """---
type: custom
model_preference: claude-3-sonnet
version: 1.0.0
---

# Test Agent

## 🎯 Primary Role
This is a test agent for verifying the integration.

## 🎯 When to Use This Agent

**Select this agent when:**
- Testing the integration
- Verifying functionality

**Do NOT select for:**
- Production use
- Real tasks

## 🔧 Core Capabilities
- Testing integration
- Verifying functionality

## 🔑 Authority & Permissions

### ✅ Exclusive Write Access
- Test files

### ❌ Forbidden Operations
- Production operations
"""

        # Create agent
        result = await lifecycle_mgr.create_agent(
            agent_name="test-integration-agent",
            agent_content=agent_content,
            tier=ModificationTier.USER,
            agent_type="custom",
            author="test-script",
            tags=["test", "integration"],
        )

        logger.info(
            f"Create result: success={result.success}, duration={result.duration_ms:.1f}ms"
        )

        if result.success:
            logger.info(f"Agent created at: {result.metadata.get('file_path')}")
        else:
            logger.error(f"Failed to create agent: {result.error_message}")

        return result.success

    finally:
        await lifecycle_mgr.stop()


@pytest.mark.asyncio
async def test_update_agent():
    """Test updating an agent through the lifecycle manager."""
    logger.info("Testing agent update...")

    lifecycle_mgr = AgentLifecycleManager()
    await lifecycle_mgr.start()

    try:
        # Updated content
        updated_content = """---
type: custom
model_preference: claude-3-opus
version: 1.0.1
---

# Test Agent (Updated)

## 🎯 Primary Role
This is an updated test agent for verifying the integration.

## 🎯 When to Use This Agent

**Select this agent when:**
- Testing the integration (updated)
- Verifying functionality (updated)

**Do NOT select for:**
- Production use
- Real tasks

## 🔧 Core Capabilities
- Testing integration (enhanced)
- Verifying functionality (enhanced)
- New capability added

## 🔑 Authority & Permissions

### ✅ Exclusive Write Access
- Test files
- Test directories

### ❌ Forbidden Operations
- Production operations
- System modifications
"""

        # Update agent
        result = await lifecycle_mgr.update_agent(
            agent_name="test-integration-agent",
            agent_content=updated_content,
            model_preference="claude-3-opus",
        )

        logger.info(
            f"Update result: success={result.success}, duration={result.duration_ms:.1f}ms"
        )

        if result.success:
            logger.info(
                f"Agent updated to version: {result.metadata.get('new_version')}"
            )
        else:
            logger.error(f"Failed to update agent: {result.error_message}")

        return result.success

    finally:
        await lifecycle_mgr.stop()


@pytest.mark.asyncio
async def test_read_agent():
    """Test reading an agent through the lifecycle manager."""
    logger.info("Testing agent read...")

    lifecycle_mgr = AgentLifecycleManager()
    await lifecycle_mgr.start()

    try:
        # Get agent status
        record = await lifecycle_mgr.get_agent_status("test-integration-agent")

        if record:
            logger.info(f"Agent found: {record.agent_name}")
            logger.info(f"  State: {record.current_state.value}")
            logger.info(f"  Version: {record.version}")
            logger.info(f"  Tier: {record.tier.value}")
            logger.info(f"  Last modified: {record.last_modified_datetime}")
            return True
        logger.error("Agent not found in lifecycle records")
        return False

    finally:
        await lifecycle_mgr.stop()


@pytest.mark.asyncio
async def test_delete_agent():
    """Test deleting an agent through the lifecycle manager."""
    logger.info("Testing agent deletion...")

    lifecycle_mgr = AgentLifecycleManager()
    await lifecycle_mgr.start()

    try:
        # Delete agent
        result = await lifecycle_mgr.delete_agent("test-integration-agent")

        logger.info(
            f"Delete result: success={result.success}, duration={result.duration_ms:.1f}ms"
        )

        if result.success:
            logger.info(
                f"Agent deleted, backup at: {result.metadata.get('backup_path')}"
            )
        else:
            logger.error(f"Failed to delete agent: {result.error_message}")

        return result.success

    finally:
        await lifecycle_mgr.stop()


@pytest.mark.asyncio
async def test_lifecycle_stats():
    """Test getting lifecycle statistics."""
    logger.info("Testing lifecycle statistics...")

    lifecycle_mgr = AgentLifecycleManager()
    await lifecycle_mgr.start()

    try:
        stats = await lifecycle_mgr.get_lifecycle_stats()

        logger.info("Lifecycle Statistics:")
        logger.info(f"  Total agents: {stats['total_agents']}")
        logger.info(f"  Active operations: {stats['active_operations']}")
        logger.info(f"  Agents by state: {stats['agents_by_state']}")
        logger.info(f"  Agents by tier: {stats['agents_by_tier']}")
        logger.info(f"  Recent operations: {stats['recent_operations']}")

        # Performance metrics
        perf = stats["performance_metrics"]
        logger.info("  Performance:")
        logger.info(f"    Total operations: {perf['total_operations']}")
        logger.info(f"    Successful: {perf['successful_operations']}")
        logger.info(f"    Failed: {perf['failed_operations']}")
        logger.info(f"    Average duration: {perf['average_duration_ms']:.1f}ms")

        return True

    finally:
        await lifecycle_mgr.stop()


async def main():
    """Run all integration tests."""
    logger.info("Starting AgentManager integration tests...")

    all_passed = True

    # Test sequence
    tests = [
        ("Create Agent", test_create_agent),
        ("Read Agent", test_read_agent),
        ("Update Agent", test_update_agent),
        ("Delete Agent", test_delete_agent),
        ("Lifecycle Stats", test_lifecycle_stats),
    ]

    for test_name, test_func in tests:
        try:
            logger.info(f"\n{'=' * 50}")
            logger.info(f"Running: {test_name}")
            logger.info(f"{'=' * 50}")

            passed = await test_func()

            if passed:
                logger.info(f"✓ {test_name} PASSED")
            else:
                logger.error(f"✗ {test_name} FAILED")
                all_passed = False

        except Exception as e:
            logger.error(f"✗ {test_name} FAILED with exception: {e}")
            import traceback

            traceback.print_exc()
            all_passed = False

    logger.info(f"\n{'=' * 50}")
    if all_passed:
        logger.info("✓ All integration tests PASSED")
        return 0
    logger.error("✗ Some integration tests FAILED")
    return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
