#!/usr/bin/env python3
"""
Manual dashboard testing script that simulates real usage scenarios.
Generates realistic events and tests dashboard functionality without selenium.
"""

import asyncio
import json
import time
import subprocess
import sys
import webbrowser
from pathlib import Path
from typing import Dict, List, Any

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

import socketio


class ManualDashboardTester:
    """Manual dashboard testing with realistic scenarios."""
    
    def __init__(self):
        self.sio = None
        self.server_url = "http://localhost:8765"
        self.test_scenarios = []
        
    async def setup_client(self):
        """Setup Socket.IO client."""
        try:
            self.sio = socketio.AsyncClient()
            
            @self.sio.event
            async def connect():
                print("✅ Connected to dashboard server")
                
            @self.sio.event
            async def disconnect():
                print("🔌 Disconnected from dashboard server")
            
            @self.sio.on('*')
            async def catch_all(event, data):
                print(f"📥 Server response: {event}")
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to setup client: {e}")
            return False
    
    async def connect_to_server(self):
        """Connect to the Socket.IO server."""
        try:
            await self.sio.connect(self.server_url, wait_timeout=10)
            return True
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return False
    
    def open_dashboard_in_browser(self):
        """Open the dashboard in the default browser."""
        dashboard_url = f"{self.server_url}/templates/index.html?autoconnect=true&port=8765"
        print(f"🌐 Opening dashboard at: {dashboard_url}")
        try:
            webbrowser.open(dashboard_url)
            return True
        except Exception as e:
            print(f"❌ Failed to open browser: {e}")
            return False
    
    def open_qa_test_page(self):
        """Open the QA test page."""
        qa_test_path = Path(__file__).parent / "qa_dashboard_browser_test.html"
        qa_test_url = f"file://{qa_test_path.absolute()}"
        print(f"🧪 Opening QA test page at: {qa_test_url}")
        try:
            webbrowser.open(qa_test_url)
            return True
        except Exception as e:
            print(f"❌ Failed to open QA test page: {e}")
            return False
    
    async def run_realistic_scenario_1(self):
        """Scenario 1: Development workflow simulation."""
        print("\n🎯 Running Scenario 1: Development Workflow")
        print("=" * 50)
        
        events = [
            # Session start
            {
                "type": "session.start",
                "timestamp": time.time(),
                "data": {
                    "session_id": "dev_session_001",
                    "launch_method": "interactive",
                    "working_directory": "/Users/masa/Projects/claude-mpm",
                    "instance_info": {
                        "port": 8765,
                        "host": "localhost"
                    }
                }
            },
            
            # File operations
            {
                "type": "hook.pre_tool",
                "timestamp": time.time() + 1,
                "data": {
                    "tool_name": "Read",
                    "session_id": "dev_session_001",
                    "agent_type": "engineer",
                    "arguments": {
                        "file_path": "/Users/masa/Projects/claude-mpm/src/claude_mpm/web/templates/index.html"
                    }
                }
            },
            {
                "type": "hook.post_tool",
                "timestamp": time.time() + 2,
                "data": {
                    "tool_name": "Read",
                    "session_id": "dev_session_001",
                    "agent_type": "engineer",
                    "result": "HTML content read successfully",
                    "file_path": "/Users/masa/Projects/claude-mpm/src/claude_mpm/web/templates/index.html"
                }
            },
            
            # Agent delegation
            {
                "type": "agent.delegation",
                "timestamp": time.time() + 3,
                "data": {
                    "agent_type": "qa",
                    "task": "Test dashboard functionality",
                    "session_id": "dev_session_001",
                    "status": "started"
                }
            },
            
            # Tool usage
            {
                "type": "hook.pre_tool",
                "timestamp": time.time() + 4,
                "data": {
                    "tool_name": "Bash",
                    "session_id": "dev_session_001",
                    "agent_type": "qa",
                    "arguments": {
                        "command": "python qa_dashboard_socketio_test.py"
                    }
                }
            },
            {
                "type": "hook.post_tool",
                "timestamp": time.time() + 5,
                "data": {
                    "tool_name": "Bash",
                    "session_id": "dev_session_001",
                    "agent_type": "qa",
                    "result": "QA tests completed successfully",
                    "exit_code": 0
                }
            },
            
            # Memory operations
            {
                "type": "memory:updated",
                "timestamp": time.time() + 6,
                "data": {
                    "agent_id": "qa",
                    "learning_type": "testing_protocol",
                    "content": "Dashboard QA testing requires Socket.IO connection validation",
                    "section": "learnings",
                    "session_id": "dev_session_001"
                }
            },
            
            # Todo updates
            {
                "type": "todo.update",
                "timestamp": time.time() + 7,
                "data": {
                    "session_id": "dev_session_001",
                    "todos": [
                        {
                            "id": "qa-dashboard-test",
                            "content": "Complete comprehensive dashboard QA testing",
                            "status": "completed",
                            "priority": "high"
                        },
                        {
                            "id": "qa-report-generation",
                            "content": "Generate QA test report with findings",
                            "status": "in_progress",
                            "priority": "medium"
                        }
                    ]
                }
            }
        ]
        
        for i, event in enumerate(events):
            try:
                await self.sio.emit('claude_event', event)
                print(f"  📤 Sent event {i+1}/{len(events)}: {event['type']}")
                await asyncio.sleep(0.5)
            except Exception as e:
                print(f"  ❌ Failed to send event {i+1}: {e}")
    
    async def run_realistic_scenario_2(self):
        """Scenario 2: Multi-session testing."""
        print("\n🎯 Running Scenario 2: Multi-Session Testing")
        print("=" * 50)
        
        sessions = ["session_alpha", "session_beta", "session_gamma"]
        
        for session_id in sessions:
            events = [
                {
                    "type": "session.start",
                    "timestamp": time.time(),
                    "data": {
                        "session_id": session_id,
                        "launch_method": "non-interactive",
                        "working_directory": f"/Users/masa/Projects/test_{session_id}"
                    }
                },
                {
                    "type": "hook.pre_tool",
                    "timestamp": time.time() + 1,
                    "data": {
                        "tool_name": "Write",
                        "session_id": session_id,
                        "agent_type": "engineer",
                        "arguments": {
                            "file_path": f"/tmp/test_{session_id}.py",
                            "content": f"# Test file for {session_id}\nprint('Hello from {session_id}')\n"
                        }
                    }
                },
                {
                    "type": "hook.post_tool",
                    "timestamp": time.time() + 2,
                    "data": {
                        "tool_name": "Write",
                        "session_id": session_id,
                        "agent_type": "engineer",
                        "result": "File written successfully",
                        "file_path": f"/tmp/test_{session_id}.py"
                    }
                }
            ]
            
            for event in events:
                try:
                    await self.sio.emit('claude_event', event)
                    print(f"  📤 Sent {session_id} event: {event['type']}")
                    await asyncio.sleep(0.2)
                except Exception as e:
                    print(f"  ❌ Failed to send {session_id} event: {e}")
    
    async def run_error_scenario(self):
        """Scenario 3: Error and edge case testing."""
        print("\n🎯 Running Scenario 3: Error and Edge Cases")
        print("=" * 50)
        
        error_events = [
            {
                "type": "claude.error",
                "timestamp": time.time(),
                "data": {
                    "session_id": "error_session",
                    "error_type": "tool_execution_failed",
                    "message": "Tool execution failed: file not found",
                    "tool_name": "Read",
                    "file_path": "/nonexistent/file.txt"
                }
            },
            {
                "type": "hook.pre_tool",
                "timestamp": time.time() + 1,
                "data": {
                    "tool_name": "Edit",
                    "session_id": "edge_case_session",
                    "agent_type": "test",
                    "arguments": {
                        "file_path": "/very/long/path/that/might/cause/display/issues/in/the/dashboard/interface/test_file_with_very_long_name.py",
                        "old_string": "old code",
                        "new_string": "new code with special characters: áéíóú ñ 中文 🚀"
                    }
                }
            },
            {
                "type": "memory:error",
                "timestamp": time.time() + 2,
                "data": {
                    "agent_id": "corrupted_agent",
                    "error": "Memory corruption detected",
                    "session_id": "error_session"
                }
            }
        ]
        
        for event in error_events:
            try:
                await self.sio.emit('claude_event', event)
                print(f"  📤 Sent error event: {event['type']}")
                await asyncio.sleep(0.3)
            except Exception as e:
                print(f"  ❌ Failed to send error event: {e}")
    
    async def run_performance_test(self):
        """Scenario 4: Performance testing with high event volume."""
        print("\n🎯 Running Scenario 4: Performance Testing")
        print("=" * 50)
        
        print("  🔥 Generating high-volume event stream...")
        
        for i in range(50):
            event = {
                "type": "hook.pre_tool",
                "timestamp": time.time(),
                "data": {
                    "tool_name": "Read",
                    "session_id": f"perf_session_{i % 5}",
                    "agent_type": "performance_test",
                    "arguments": {
                        "file_path": f"/test/batch/file_{i:03d}.py"
                    }
                }
            }
            
            try:
                await self.sio.emit('claude_event', event)
                if i % 10 == 0:
                    print(f"  📤 Sent {i+1}/50 performance events")
                await asyncio.sleep(0.05)  # Fast events
            except Exception as e:
                print(f"  ❌ Performance event {i} failed: {e}")
    
    def display_manual_test_instructions(self):
        """Display instructions for manual testing."""
        print("\n" + "=" * 70)
        print("📋 MANUAL TESTING INSTRUCTIONS")
        print("=" * 70)
        print("""
🔍 DASHBOARD TESTING CHECKLIST:

1. CONNECTION STATUS:
   • Verify status shows 'Connected' with green indicator
   • Check that events appear in real-time
   • Test disconnect/reconnect functionality

2. EVENT DISPLAY:
   • Check Events tab shows generated events
   • Test search functionality with keywords
   • Try different type filters (hook, agent, session, etc.)
   • Verify timestamps are correct

3. MODULE VIEWER:
   • Click on different events to see details
   • Verify structured data appears in top pane
   • Check raw JSON appears in bottom pane
   • Test tool call visualization

4. TAB FUNCTIONALITY:
   • Switch between Events, Agents, Tools, Files tabs
   • Verify each tab filters data correctly
   • Test search within each tab

5. SESSION MANAGEMENT:
   • Use session dropdown to filter by session
   • Check working directory tracking
   • Verify footer updates with session info

6. HUD VISUALIZATION:
   • Select a session and enable HUD
   • Check if Cytoscape visualization loads
   • Test HUD controls (reset layout, center view)

7. UI INTERACTIONS:
   • Test keyboard navigation (arrow keys)
   • Verify export functionality
   • Check responsive design on different screen sizes

8. PERFORMANCE:
   • Monitor dashboard with high event volume
   • Check for memory leaks or slowdowns
   • Verify smooth scrolling and interactions

🎯 EXPECTED RESULTS:
   • All events should appear in real-time
   • No JavaScript errors in browser console
   • Smooth interactions and filtering
   • Correct data display in all components
        """)
        print("=" * 70)
    
    async def run_all_scenarios(self):
        """Run all testing scenarios."""
        if not await self.setup_client():
            return False
            
        if not await self.connect_to_server():
            return False
        
        try:
            # Run test scenarios
            await self.run_realistic_scenario_1()
            await asyncio.sleep(2)
            
            await self.run_realistic_scenario_2()
            await asyncio.sleep(2)
            
            await self.run_error_scenario()
            await asyncio.sleep(2)
            
            await self.run_performance_test()
            
            print("\n✅ All test scenarios completed!")
            return True
            
        except Exception as e:
            print(f"❌ Test scenarios failed: {e}")
            return False
        
        finally:
            if self.sio:
                await self.sio.disconnect()
    
    def check_server_status(self):
        """Check if the Socket.IO server is running."""
        try:
            import requests
            response = requests.get(f"{self.server_url}/health", timeout=5)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Server is running: {data.get('server', 'unknown')}")
                print(f"   Clients connected: {data.get('clients_connected', 0)}")
                return True
            else:
                print(f"❌ Server health check failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Server not reachable: {e}")
            return False


async def main():
    """Main function."""
    print("🚀 Claude MPM Dashboard Manual Testing Suite")
    print("=" * 70)
    
    tester = ManualDashboardTester()
    
    # Check server status
    if not tester.check_server_status():
        print("\n❌ Socket.IO server is not running!")
        print("   Please start the server first:")
        print("   ./scripts/start_persistent_socketio_server.py")
        return False
    
    print("\n🌐 Opening dashboard and QA test pages...")
    
    # Open dashboard in browser
    dashboard_opened = tester.open_dashboard_in_browser()
    
    # Open QA test page
    qa_opened = tester.open_qa_test_page()
    
    if dashboard_opened:
        print("✅ Dashboard opened in browser")
    if qa_opened:
        print("✅ QA test page opened in browser")
    
    print("\n⏳ Waiting 3 seconds for browser to load...")
    await asyncio.sleep(3)
    
    # Run test scenarios to generate events
    print("\n📤 Generating test events...")
    success = await tester.run_all_scenarios()
    
    if success:
        # Display manual testing instructions
        tester.display_manual_test_instructions()
        
        print("\n🎉 Test data generation completed!")
        print("   Now perform manual testing using the opened browser windows.")
        print("   Check both the main dashboard and the QA test page.")
        
        return True
    else:
        print("\n❌ Test data generation failed!")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)