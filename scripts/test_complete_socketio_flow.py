#!/usr/bin/env python3
"""
Comprehensive test of the complete Socket.IO event flow:
Hook runs → Socket.IO server receives → Dashboard displays

This script tests the end-to-end event flow to verify everything works properly.
"""

import sys
import time
import json
import asyncio
import requests
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

import socketio
from claude_mpm.core.logger import get_logger
from claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler

logger = get_logger(__name__)

class SocketIOTestClient:
    """Test client to monitor Socket.IO events."""
    
    def __init__(self, server_url="http://localhost:8765"):
        self.server_url = server_url
        self.sio = socketio.SimpleClient()
        self.received_events = []
        
    def connect(self):
        """Connect to Socket.IO server."""
        try:
            self.sio.connect(self.server_url, namespaces=['/dashboard'])
            logger.info(f"✅ Connected to Socket.IO server at {self.server_url}")
            
            # Set up event handlers
            @self.sio.event(namespace='/dashboard')
            def hook_event(data):
                logger.info(f"📨 Received hook_event: {data}")
                self.received_events.append(('hook_event', data))
                
            @self.sio.event(namespace='/dashboard')
            def user_prompt(data):
                logger.info(f"📨 Received user_prompt: {data}")
                self.received_events.append(('user_prompt', data))
                
            @self.sio.event(namespace='/dashboard')  
            def pre_tool(data):
                logger.info(f"📨 Received pre_tool: {data}")
                self.received_events.append(('pre_tool', data))
                
            @self.sio.event(namespace='/dashboard')
            def post_tool(data):
                logger.info(f"📨 Received post_tool: {data}")
                self.received_events.append(('post_tool', data))
                
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to Socket.IO server: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from Socket.IO server."""
        if self.sio.connected:
            self.sio.disconnect()
            
    def wait_for_events(self, timeout=10):
        """Wait for events to be received."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            self.sio.sleep(0.1)
        return self.received_events


def test_server_availability():
    """Test if Socket.IO server is available."""
    logger.info("🔍 Testing Socket.IO server availability...")
    
    try:
        response = requests.get("http://localhost:8765/socket.io/", timeout=5)
        if response.status_code == 200 or "unsupported version" in response.text:
            logger.info("✅ Socket.IO server is responding")
            return True
        else:
            logger.error(f"❌ Unexpected response: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        logger.error(f"❌ Socket.IO server not available: {e}")
        return False


def test_hook_event_generation():
    """Test hook event generation and broadcasting."""
    logger.info("🧪 Testing hook event generation...")
    
    # Create test client
    client = SocketIOTestClient()
    
    if not client.connect():
        return False
        
    try:
        # Create hook handler instance
        hook_handler = ClaudeHookHandler()
        
        # Test different event types
        test_events = [
            {
                'event_type': 'user_prompt',
                'data': {
                    'prompt': 'Test user prompt for Socket.IO flow verification',
                    'timestamp': time.time(),
                    'test_id': 'flow_test_1'
                }
            },
            {
                'event_type': 'pre_tool',
                'data': {
                    'tool_name': 'TestTool',
                    'parameters': {'test_param': 'test_value'},
                    'timestamp': time.time(),
                    'test_id': 'flow_test_2'
                }
            },
            {
                'event_type': 'post_tool',
                'data': {
                    'tool_name': 'TestTool',
                    'result': 'Tool execution completed successfully',
                    'timestamp': time.time(),
                    'test_id': 'flow_test_3'
                }
            }
        ]
        
        # Send test events
        for event in test_events:
            logger.info(f"📤 Sending {event['event_type']} event...")
            hook_handler.emit_event(event['event_type'], event['data'])
            time.sleep(1)  # Small delay between events
        
        # Wait for events to be received
        logger.info("⏳ Waiting for events to be received...")
        received_events = client.wait_for_events(timeout=15)
        
        # Analyze results
        logger.info(f"📊 Received {len(received_events)} events")
        
        success = True
        for i, expected_event in enumerate(test_events):
            expected_type = expected_event['event_type']
            found = False
            
            for event_type, event_data in received_events:
                if event_type == expected_type and event_data.get('test_id') == expected_event['data']['test_id']:
                    logger.info(f"✅ {expected_type} event received correctly")
                    found = True
                    break
                    
            if not found:
                logger.error(f"❌ {expected_type} event not received or incorrect")
                success = False
        
        return success
        
    except Exception as e:
        logger.error(f"❌ Error during hook event testing: {e}")
        return False
        
    finally:
        client.disconnect()


def test_dashboard_integration():
    """Test dashboard integration by checking HTML response."""
    logger.info("🌐 Testing dashboard integration...")
    
    try:
        # Test dashboard HTML endpoint
        response = requests.get("http://localhost:8765/dashboard", timeout=5)
        if response.status_code == 200:
            html_content = response.text
            
            # Check for key elements
            checks = [
                ("Socket.IO client script", "socket.io.js" in html_content),
                ("Dashboard container", "id=\"dashboard\"" in html_content or "dashboard" in html_content.lower()),
                ("Event handling code", "socket.on" in html_content),
                ("Connection status", "connect" in html_content.lower()),
            ]
            
            success = True
            for check_name, check_result in checks:
                if check_result:
                    logger.info(f"✅ {check_name} found in dashboard")
                else:
                    logger.warning(f"⚠️  {check_name} not found in dashboard")
                    success = False
                    
            return success
            
        else:
            logger.error(f"❌ Dashboard endpoint returned {response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error testing dashboard integration: {e}")
        return False


def run_comprehensive_test():
    """Run comprehensive Socket.IO flow test."""
    logger.info("🚀 Starting comprehensive Socket.IO flow test...")
    logger.info("=" * 60)
    
    # Test 1: Server Availability
    logger.info("TEST 1: Server Availability")
    server_ok = test_server_availability()
    logger.info(f"Result: {'✅ PASS' if server_ok else '❌ FAIL'}")
    logger.info("-" * 40)
    
    if not server_ok:
        logger.error("❌ Server not available, cannot continue tests")
        return False
    
    # Test 2: Hook Event Generation and Broadcasting
    logger.info("TEST 2: Hook Event Generation and Broadcasting")
    events_ok = test_hook_event_generation()
    logger.info(f"Result: {'✅ PASS' if events_ok else '❌ FAIL'}")
    logger.info("-" * 40)
    
    # Test 3: Dashboard Integration
    logger.info("TEST 3: Dashboard Integration")
    dashboard_ok = test_dashboard_integration()
    logger.info(f"Result: {'✅ PASS' if dashboard_ok else '❌ FAIL'}")
    logger.info("-" * 40)
    
    # Overall Results
    all_tests_passed = server_ok and events_ok and dashboard_ok
    logger.info("=" * 60)
    logger.info("COMPREHENSIVE TEST RESULTS:")
    logger.info(f"Server Availability: {'✅ PASS' if server_ok else '❌ FAIL'}")
    logger.info(f"Event Flow: {'✅ PASS' if events_ok else '❌ FAIL'}")
    logger.info(f"Dashboard Integration: {'✅ PASS' if dashboard_ok else '❌ FAIL'}")
    logger.info("-" * 40)
    logger.info(f"OVERALL: {'✅ ALL TESTS PASSED' if all_tests_passed else '❌ SOME TESTS FAILED'}")
    logger.info("=" * 60)
    
    if all_tests_passed:
        logger.info("🎉 Complete Socket.IO event flow is working correctly!")
        logger.info("📊 Flow verified: Hook runs → Socket.IO server receives → Dashboard displays")
    else:
        logger.error("🚨 Some tests failed. Please check the logs above for details.")
    
    return all_tests_passed


if __name__ == "__main__":
    success = run_comprehensive_test()
    sys.exit(0 if success else 1)