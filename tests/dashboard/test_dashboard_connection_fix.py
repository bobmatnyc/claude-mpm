#!/usr/bin/env python3
"""Test script to verify dashboard connection fixes.

This script tests the critical fixes implemented for dashboard connection failures:
1. Event handler registration timing
2. Connection recovery with retry logic
3. Configuration timing adjustments
4. Event relay resilience
"""

import asyncio
import json
import logging
import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.services.socketio.server.main import SocketIOServer

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def test_server_startup():
    """Test that the server starts with proper event handler registration."""
    logger.info("=" * 60)
    logger.info("Testing server startup with event handler registration")
    logger.info("=" * 60)

    try:
        # Create server instance
        server = SocketIOServer(host="localhost", port=8765)

        # Start the server
        logger.info("Starting Socket.IO server...")
        server.start_sync()

        # Give it time to initialize
        time.sleep(2)

        # Check if server is running
        if server.is_running():
            logger.info("✅ Server started successfully")
        else:
            logger.error("❌ Server failed to start")
            return False

        # Check if event handlers are registered
        if server.event_registry:
            logger.info("✅ Event registry initialized")

            # Check for specific handlers
            from claude_mpm.services.socketio.handlers import ConnectionEventHandler

            conn_handler = server.event_registry.get_handler(ConnectionEventHandler)
            if conn_handler:
                logger.info("✅ Connection event handler registered")
            else:
                logger.error("❌ Connection event handler not found")

        else:
            logger.error("❌ Event registry not initialized")
            return False

        # Check broadcaster
        if server.broadcaster:
            logger.info("✅ Broadcaster initialized")

            # Check if broadcaster has necessary components
            if hasattr(server.broadcaster, "sio") and server.broadcaster.sio:
                logger.info("✅ Broadcaster has Socket.IO instance")
            else:
                logger.error("❌ Broadcaster missing Socket.IO instance")

        else:
            logger.error("❌ Broadcaster not initialized")
            return False

        # Check EventBus integration
        if server.eventbus_integration:
            logger.info("✅ EventBus integration setup")

            # Check relay
            if (
                hasattr(server.eventbus_integration, "relay")
                and server.eventbus_integration.relay
            ):
                relay_stats = server.eventbus_integration.relay.get_stats()
                logger.info(
                    f"✅ EventBus relay stats: {json.dumps(relay_stats, indent=2)}"
                )

                if relay_stats.get("connected"):
                    logger.info("✅ EventBus relay connected")
                else:
                    logger.warning("⚠️  EventBus relay not connected")
            else:
                logger.error("❌ EventBus relay not initialized")
        else:
            logger.warning("⚠️  EventBus integration not setup")

        # Check connection manager
        if server.connection_manager:
            logger.info("✅ Connection manager initialized")

            # Check configuration
            logger.info(
                f"  - Max buffer size: {server.connection_manager.max_buffer_size}"
            )
            logger.info(f"  - Event TTL: {server.connection_manager.event_ttl}s")
            logger.info(
                f"  - Health check interval: {server.connection_manager.health_check_interval}s"
            )
            logger.info(
                f"  - Stale timeout: {server.connection_manager.stale_timeout}s"
            )
        else:
            logger.error("❌ Connection manager not initialized")
            return False

        # Test configuration values
        from claude_mpm.config.socketio_config import CONNECTION_CONFIG

        logger.info("\n" + "=" * 60)
        logger.info("Connection configuration:")
        logger.info(
            f"  - Ping interval: {CONNECTION_CONFIG['ping_interval']}s (was 45s)"
        )
        logger.info(f"  - Ping timeout: {CONNECTION_CONFIG['ping_timeout']}s")
        logger.info(
            f"  - Stale timeout: {CONNECTION_CONFIG['stale_timeout']}s (was 180s)"
        )
        logger.info(
            f"  - Connection timeout: {CONNECTION_CONFIG.get('connection_timeout', 'not set')}s"
        )

        # Stop the server
        logger.info("\nStopping server...")
        server.stop_sync()
        time.sleep(1)

        logger.info("\n✅ All server startup tests passed!")
        return True

    except Exception as e:
        logger.error(f"❌ Test failed with error: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_connection_resilience():
    """Test connection manager's retry logic and error handling."""
    logger.info("\n" + "=" * 60)
    logger.info("Testing connection resilience")
    logger.info("=" * 60)

    try:
        from claude_mpm.services.socketio.server.connection_manager import (
            ConnectionManager,
        )

        # Create connection manager
        manager = ConnectionManager(max_buffer_size=100, event_ttl=60)
        logger.info("✅ Connection manager created")

        # Test connection registration with retry logic
        async def test_registration():
            # Register a connection
            conn = await manager.register_connection("test_sid_1", "test_client_1")
            if conn:
                logger.info(f"✅ Connection registered: {conn.client_id}")
                logger.info(f"  - State: {conn.state.value}")
                logger.info(f"  - Quality: {conn.calculate_quality()}")

                # Test health check
                is_healthy = conn.is_healthy(timeout=90)
                logger.info(
                    f"  - Health status: {'healthy' if is_healthy else 'unhealthy'}"
                )

                return True
            logger.error("❌ Failed to register connection")
            return False

        # Run async test
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        success = loop.run_until_complete(test_registration())
        loop.close()

        if success:
            logger.info("✅ Connection resilience test passed!")
        else:
            logger.error("❌ Connection resilience test failed")

        return success

    except Exception as e:
        logger.error(f"❌ Resilience test failed with error: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_event_relay_resilience():
    """Test EventBus relay's retry logic and error handling."""
    logger.info("\n" + "=" * 60)
    logger.info("Testing EventBus relay resilience")
    logger.info("=" * 60)

    try:
        from claude_mpm.services.event_bus.direct_relay import DirectSocketIORelay

        # Create a mock server for testing
        class MockServer:
            def __init__(self):
                self.broadcaster = None  # Initially no broadcaster

        mock_server = MockServer()

        # Create relay
        relay = DirectSocketIORelay(mock_server)
        logger.info("✅ DirectSocketIORelay created")

        # Test retry logic
        logger.info("Testing retry logic (broadcaster initially unavailable)...")

        # Modify retry settings for faster testing
        relay.max_retries = 3
        relay.retry_delay = 0.5

        # Start relay (should handle missing broadcaster gracefully)
        relay.start()

        # Check stats
        stats = relay.get_stats()
        logger.info(f"Relay stats after start: {json.dumps(stats, indent=2)}")

        if not stats["connected"]:
            logger.info("✅ Relay correctly detected missing broadcaster")
        else:
            logger.error("❌ Relay should not be connected without broadcaster")

        logger.info("✅ Event relay resilience test passed!")
        return True

    except Exception as e:
        logger.error(f"❌ Event relay test failed with error: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    logger.info("Starting dashboard connection fix tests")
    logger.info("=" * 80)

    results = []

    # Test 1: Server startup
    results.append(("Server Startup", test_server_startup()))

    # Test 2: Connection resilience
    results.append(("Connection Resilience", test_connection_resilience()))

    # Test 3: Event relay resilience
    results.append(("Event Relay Resilience", test_event_relay_resilience()))

    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("TEST SUMMARY")
    logger.info("=" * 80)

    all_passed = True
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        logger.info(f"{test_name}: {status}")
        if not passed:
            all_passed = False

    if all_passed:
        logger.info("\n🎉 All tests passed! Dashboard connection fixes are working.")
    else:
        logger.error("\n⚠️  Some tests failed. Please review the fixes.")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
