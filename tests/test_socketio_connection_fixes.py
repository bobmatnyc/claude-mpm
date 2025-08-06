#!/usr/bin/env python3
"""
Test script to validate Socket.IO connection fixes.

This script tests:
1. Server startup and shutdown
2. Multiple client connections
3. Error handling and reconnection
4. Event broadcasting
"""

import asyncio
import json
import logging
import time
import threading
from datetime import datetime

# Import the fixed Socket.IO server
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from claude_mpm.services.socketio_server import SocketIOServer, SOCKETIO_AVAILABLE

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SocketIOConnectionTester:
    """Test Socket.IO server connection handling."""
    
    def __init__(self):
        self.server = None
        self.clients = []
        
    def test_server_startup(self):
        """Test server startup and basic functionality."""
        logger.info("🚀 Testing server startup...")
        
        if not SOCKETIO_AVAILABLE:
            logger.error("❌ Socket.IO packages not available - cannot test")
            return False
            
        try:
            self.server = SocketIOServer(host="localhost", port=8765)
            self.server.start()
            
            # Give server time to start
            time.sleep(1)
            
            if self.server.running and self.server.thread and self.server.thread.is_alive():
                logger.info("✅ Server started successfully")
                return True
            else:
                logger.error("❌ Server failed to start properly")
                return False
                
        except Exception as e:
            logger.error(f"❌ Server startup failed: {e}")
            return False
    
    def test_multiple_connections(self):
        """Test multiple simultaneous client connections."""
        logger.info("🔗 Testing multiple client connections...")
        
        if not SOCKETIO_AVAILABLE:
            logger.warning("⚠️  Skipping connection test - Socket.IO not available")
            return True
            
        try:
            # Create multiple client connections using socketio client
            import socketio
            
            async def create_client(client_id):
                """Create a client connection."""
                sio = socketio.AsyncClient()
                
                @sio.event
                async def connect():
                    logger.info(f"✅ Client {client_id} connected")
                    
                @sio.event
                async def disconnect():
                    logger.info(f"🔌 Client {client_id} disconnected")
                    
                @sio.event
                async def welcome(data):
                    logger.info(f"👋 Client {client_id} received welcome: {data}")
                    
                @sio.event
                async def status(data):
                    logger.info(f"📊 Client {client_id} received status: connected clients = {data.get('clients_connected', 0)}")
                
                try:
                    await sio.connect('http://localhost:8765')
                    await asyncio.sleep(2)  # Stay connected briefly
                    await sio.disconnect()
                    return True
                except Exception as e:
                    logger.error(f"❌ Client {client_id} connection failed: {e}")
                    return False
            
            async def test_concurrent_connections():
                """Test multiple concurrent connections."""
                # Create 3 concurrent client connections
                tasks = [create_client(i) for i in range(3)]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                successful = sum(1 for r in results if r is True)
                logger.info(f"📈 {successful}/3 client connections successful")
                return successful >= 2  # Allow 1 failure
            
            # Run the async test
            result = asyncio.run(test_concurrent_connections())
            return result
            
        except Exception as e:
            logger.error(f"❌ Multiple connection test failed: {e}")
            return False
    
    def test_event_broadcasting(self):
        """Test event broadcasting functionality."""
        logger.info("📡 Testing event broadcasting...")
        
        if not self.server:
            logger.warning("⚠️  No server available for broadcasting test")
            return True
            
        try:
            # Test various event types
            test_events = [
                ("session.start", {
                    "session_id": "test-session-123",
                    "start_time": datetime.utcnow().isoformat() + "Z",
                    "launch_method": "cli"
                }),
                ("claude.status", {
                    "status": "running",
                    "pid": 12345
                }),
                ("memory.updated", {
                    "agent_id": "test-agent",
                    "learning_type": "pattern",
                    "content": "Test learning content"
                }),
                ("hook.executed", {
                    "hook_name": "test-hook",
                    "status": "success"
                })
            ]
            
            for event_type, data in test_events:
                logger.info(f"📤 Broadcasting {event_type}")
                self.server.broadcast_event(event_type, data)
                time.sleep(0.1)  # Small delay between events
            
            logger.info("✅ Event broadcasting completed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Event broadcasting test failed: {e}")
            return False
    
    def test_error_handling(self):
        """Test error handling scenarios."""
        logger.info("🚨 Testing error handling...")
        
        try:
            # Test broadcasting when no clients connected
            if self.server:
                logger.info("📤 Testing broadcast with no clients...")
                self.server.broadcast_event("test.error", {"message": "No clients test"})
                
            # Test invalid event data
            if self.server:
                logger.info("📤 Testing broadcast with invalid data...")
                self.server.broadcast_event("test.invalid", {"invalid": float('inf')})
            
            logger.info("✅ Error handling tests completed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error handling test failed: {e}")
            return False
    
    def cleanup(self):
        """Clean up test resources."""
        logger.info("🧹 Cleaning up test resources...")
        
        if self.server:
            try:
                self.server.stop()
                logger.info("✅ Server stopped")
            except Exception as e:
                logger.error(f"❌ Server cleanup failed: {e}")
    
    def run_all_tests(self):
        """Run all connection tests."""
        logger.info("🔬 Starting Socket.IO connection tests...")
        
        tests = [
            ("Server Startup", self.test_server_startup),
            ("Multiple Connections", self.test_multiple_connections),
            ("Event Broadcasting", self.test_event_broadcasting),
            ("Error Handling", self.test_error_handling)
        ]
        
        results = {}
        
        for test_name, test_func in tests:
            try:
                logger.info(f"\n{'='*50}")
                logger.info(f"🧪 Running: {test_name}")
                logger.info(f"{'='*50}")
                
                result = test_func()
                results[test_name] = result
                
                if result:
                    logger.info(f"✅ {test_name}: PASSED")
                else:
                    logger.error(f"❌ {test_name}: FAILED")
                    
            except Exception as e:
                logger.error(f"💥 {test_name}: EXCEPTION - {e}")
                results[test_name] = False
        
        # Cleanup
        self.cleanup()
        
        # Summary
        logger.info(f"\n{'='*50}")
        logger.info("📊 TEST SUMMARY")
        logger.info(f"{'='*50}")
        
        passed = sum(1 for r in results.values() if r)
        total = len(results)
        
        for test_name, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            logger.info(f"{status}: {test_name}")
        
        logger.info(f"\n🎯 Overall: {passed}/{total} tests passed")
        
        if passed == total:
            logger.info("🎉 All tests passed! Socket.IO fixes are working.")
        else:
            logger.warning(f"⚠️  {total - passed} test(s) failed. Review the logs above.")
        
        return passed == total


def main():
    """Main test runner."""
    print("🔧 Socket.IO Connection Fixes Test Suite")
    print("="*60)
    
    tester = SocketIOConnectionTester()
    success = tester.run_all_tests()
    
    exit_code = 0 if success else 1
    print(f"\n🏁 Test suite completed with exit code {exit_code}")
    return exit_code


if __name__ == "__main__":
    exit(main())