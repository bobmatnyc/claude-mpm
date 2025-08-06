#!/usr/bin/env python3
"""
Simple Socket.IO flow test that actually triggers the hook system.

This script:
1. Monitors Socket.IO events from a client perspective
2. Triggers actual MPM commands to generate hook events
3. Verifies the complete flow works end-to-end
"""

import sys
import time
import json
import subprocess
import threading
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

import socketio
from claude_mpm.core.logger import get_logger

logger = get_logger(__name__)

class EventMonitor:
    """Monitor Socket.IO events from the dashboard namespace."""
    
    def __init__(self, server_url="http://localhost:8765"):
        self.server_url = server_url
        self.sio = socketio.SimpleClient()
        self.received_events = []
        self.connected = False
        
    def connect(self):
        """Connect to Socket.IO server."""
        try:
            # Set up event handlers BEFORE connecting
            def hook_event_handler(data):
                logger.info(f"📨 Received hook_event: {json.dumps(data, indent=2)}")
                self.received_events.append(('hook_event', data))
                
            def user_prompt_handler(data):
                logger.info(f"📨 Received user_prompt: {json.dumps(data, indent=2)}")
                self.received_events.append(('user_prompt', data))
                
            def pre_tool_handler(data):
                logger.info(f"📨 Received pre_tool: {json.dumps(data, indent=2)}")
                self.received_events.append(('pre_tool', data))
                
            def post_tool_handler(data):
                logger.info(f"📨 Received post_tool: {json.dumps(data, indent=2)}")
                self.received_events.append(('post_tool', data))
                
            def connect_handler():
                logger.info("📡 Connected to Socket.IO server /hook namespace")
                
            def disconnect_handler():
                logger.info("📡 Disconnected from Socket.IO server /hook namespace")
            
            # For SimpleClient, we use the @sio.event decorator pattern
            @self.sio.event(namespace='/hook')
            def hook_event(data):
                logger.info(f"📨 Received hook_event: {json.dumps(data, indent=2)}")
                self.received_events.append(('hook_event', data))
                
            @self.sio.event(namespace='/hook')
            def user_prompt(data):
                logger.info(f"📨 Received user_prompt: {json.dumps(data, indent=2)}")
                self.received_events.append(('user_prompt', data))
                
            @self.sio.event(namespace='/hook')
            def pre_tool(data):
                logger.info(f"📨 Received pre_tool: {json.dumps(data, indent=2)}")
                self.received_events.append(('pre_tool', data))
                
            @self.sio.event(namespace='/hook')
            def post_tool(data):
                logger.info(f"📨 Received post_tool: {json.dumps(data, indent=2)}")
                self.received_events.append(('post_tool', data))
                
            @self.sio.event(namespace='/hook')    
            def connect():
                logger.info("📡 Connected to Socket.IO server /hook namespace")
                
            @self.sio.event(namespace='/hook')
            def disconnect():
                logger.info("📡 Disconnected from Socket.IO server /hook namespace")
            
            # Connect to hook namespace where hook events are broadcast
            self.sio.connect(self.server_url, namespace='/hook')
                
            self.connected = True
            logger.info(f"✅ Connected to Socket.IO server at {self.server_url}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to Socket.IO server: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from Socket.IO server."""
        if self.connected and self.sio.connected:
            self.sio.disconnect()
            self.connected = False
            
    def monitor_events(self, duration=30):
        """Monitor events for specified duration."""
        logger.info(f"👁️  Monitoring events for {duration} seconds...")
        start_time = time.time()
        
        while time.time() - start_time < duration and self.connected:
            self.sio.sleep(0.5)
            
        return self.received_events


def run_mpm_command_async(command_args):
    """Run MPM command in background to generate hook events."""
    def run_command():
        try:
            logger.info(f"🚀 Running command: {' '.join(command_args)}")
            result = subprocess.run(
                command_args,
                cwd=project_root,
                capture_output=True,
                text=True,
                timeout=20
            )
            if result.returncode == 0:
                logger.info(f"✅ Command completed successfully")
            else:
                logger.warning(f"⚠️ Command returned code {result.returncode}")
                logger.warning(f"STDERR: {result.stderr}")
        except subprocess.TimeoutExpired:
            logger.warning("⏰ Command timed out")
        except Exception as e:
            logger.error(f"❌ Command failed: {e}")
    
    thread = threading.Thread(target=run_command)
    thread.daemon = True
    thread.start()
    return thread


def test_dashboard_html():
    """Test if dashboard HTML is properly served."""
    import requests
    
    logger.info("🌐 Testing dashboard HTML...")
    try:
        response = requests.get("http://localhost:8765/dashboard", timeout=5)
        if response.status_code == 200:
            html = response.text
            
            # Check for key elements
            checks = [
                ("Socket.IO script", "socket.io" in html),
                ("Dashboard elements", "dashboard" in html.lower()),
                ("Event handling", "socket.on" in html or "addEventListener" in html),
                ("Connection code", "connect" in html),
            ]
            
            all_good = True
            for check_name, result in checks:
                if result:
                    logger.info(f"✅ {check_name}: Found")
                else:
                    logger.warning(f"⚠️ {check_name}: Not found")
                    all_good = False
                    
            return all_good
            
        else:
            logger.error(f"❌ Dashboard returned {response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Failed to fetch dashboard: {e}")
        return False


def main():
    """Run comprehensive Socket.IO flow test."""
    logger.info("🚀 Starting Socket.IO flow verification...")
    logger.info("=" * 60)
    
    # Test 1: Dashboard HTML
    logger.info("TEST 1: Dashboard HTML Content")
    dashboard_ok = test_dashboard_html()
    logger.info(f"Result: {'✅ PASS' if dashboard_ok else '❌ FAIL'}")
    logger.info("-" * 40)
    
    # Test 2: Socket.IO Connection and Event Monitoring
    logger.info("TEST 2: Socket.IO Event Flow")
    
    # Create event monitor
    monitor = EventMonitor()
    
    if not monitor.connect():
        logger.error("❌ Cannot connect to Socket.IO server")
        return False
    
    try:
        # Start monitoring in background
        logger.info("👁️  Starting event monitoring...")
        
        # Wait a moment for connection to stabilize
        time.sleep(2)
        
        # Trigger MPM command that should generate hook events
        logger.info("🎯 Triggering MPM command to generate hook events...")
        
        # Use a simple command that will generate hooks
        command_thread = run_mpm_command_async([
            "python", "-m", "claude_mpm.cli.main", 
            "run", "-i", "Generate a test file with current timestamp", 
            "--non-interactive"
        ])
        
        # Monitor events for 20 seconds
        events = monitor.monitor_events(duration=20)
        
        # Wait for command to complete
        command_thread.join(timeout=5)
        
        # Analyze results
        logger.info(f"📊 Total events received: {len(events)}")
        
        if events:
            logger.info("📋 Event Summary:")
            event_types = {}
            for event_type, event_data in events:
                event_types[event_type] = event_types.get(event_type, 0) + 1
                
            for event_type, count in event_types.items():
                logger.info(f"  - {event_type}: {count} events")
                
            logger.info("✅ Socket.IO event flow is working!")
            flow_ok = True
        else:
            logger.warning("⚠️ No events received - this could indicate:")
            logger.warning("  - Hook system not properly connected")
            logger.warning("  - Events not being broadcast to /dashboard namespace")
            logger.warning("  - MPM command didn't trigger hooks")
            flow_ok = False
            
    finally:
        monitor.disconnect()
    
    logger.info(f"Result: {'✅ PASS' if flow_ok else '⚠️ PARTIAL/FAIL'}")
    logger.info("-" * 40)
    
    # Final Summary
    all_tests_passed = dashboard_ok and flow_ok
    logger.info("=" * 60)
    logger.info("COMPREHENSIVE TEST RESULTS:")
    logger.info(f"Dashboard HTML: {'✅ PASS' if dashboard_ok else '❌ FAIL'}")
    logger.info(f"Event Flow: {'✅ PASS' if flow_ok else '⚠️ PARTIAL/FAIL'}")
    logger.info("-" * 40)
    logger.info(f"OVERALL: {'✅ ALL TESTS PASSED' if all_tests_passed else '⚠️ SOME ISSUES DETECTED'}")
    
    if all_tests_passed:
        logger.info("🎉 Complete Socket.IO event flow verified!")
        logger.info("📊 Flow: Hook runs → Socket.IO server receives → Dashboard can display")
        logger.info("🌐 Dashboard URL: http://localhost:8765/dashboard")
    else:
        logger.warning("🔍 Some issues detected. Check logs above for details.")
        
    logger.info("=" * 60)
    
    return all_tests_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)