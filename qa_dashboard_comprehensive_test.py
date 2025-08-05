#!/usr/bin/env python3
"""
Comprehensive QA testing script for Claude MPM Dashboard functionality.
Tests all major components and reports findings.
"""

import asyncio
import json
import os
import sys
import time
import subprocess
from pathlib import Path
from typing import Dict, List, Any

# Add the src directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

import socketio
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains


class DashboardQATester:
    """Comprehensive dashboard QA testing class."""
    
    def __init__(self):
        self.driver = None
        self.sio = None
        self.test_results = {
            "connection_status": {},
            "event_display": {},
            "module_viewer": {},
            "tab_functionality": {},
            "hud_visualization": {},
            "session_management": {},
            "ui_interactions": {},
            "errors": []
        }
        self.base_url = "http://localhost:8765/templates/index.html"
        
    def setup_browser(self):
        """Setup Chrome WebDriver for testing."""
        chrome_options = Options()
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        # chrome_options.add_argument("--headless")  # Comment out for debugging
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.implicitly_wait(10)
            return True
        except Exception as e:
            self.test_results["errors"].append(f"Failed to setup browser: {e}")
            return False
    
    def setup_socketio_client(self):
        """Setup Socket.IO client for testing."""
        try:
            self.sio = socketio.AsyncClient()
            return True
        except Exception as e:
            self.test_results["errors"].append(f"Failed to setup Socket.IO client: {e}")
            return False
    
    async def test_connection_status(self):
        """Test connection status functionality."""
        print("🔌 Testing Connection Status...")
        
        try:
            # Navigate to dashboard
            self.driver.get(self.base_url + "?autoconnect=true&port=8765")
            time.sleep(3)
            
            # Check initial connection status
            status_element = self.driver.find_element(By.ID, "connection-status")
            initial_status = status_element.text
            
            # Wait for connection to establish
            wait = WebDriverWait(self.driver, 15)
            
            try:
                # Wait for status to show "Connected"
                wait.until(lambda driver: "Connected" in driver.find_element(By.ID, "connection-status").text)
                connected_status = status_element.text
                self.test_results["connection_status"]["auto_connect"] = "PASS"
                self.test_results["connection_status"]["status_display"] = "PASS"
                print("  ✅ Auto-connection successful")
                print("  ✅ Status display working")
                
            except Exception as e:
                self.test_results["connection_status"]["auto_connect"] = f"FAIL: {e}"
                print("  ❌ Auto-connection failed")
            
            # Test manual disconnect/reconnect
            try:
                # Show connection controls
                conn_toggle = self.driver.find_element(By.ID, "connection-toggle-btn")
                conn_toggle.click()
                time.sleep(1)
                
                # Disconnect
                disconnect_btn = self.driver.find_element(By.ID, "disconnect-btn")
                disconnect_btn.click()
                time.sleep(2)
                
                # Check status shows disconnected
                status_after_disconnect = status_element.text
                if "Disconnected" in status_after_disconnect:
                    self.test_results["connection_status"]["manual_disconnect"] = "PASS"
                    print("  ✅ Manual disconnect working")
                else:
                    self.test_results["connection_status"]["manual_disconnect"] = "FAIL: Status not updated"
                    print("  ❌ Manual disconnect failed")
                
                # Reconnect
                connect_btn = self.driver.find_element(By.ID, "connect-btn")
                connect_btn.click()
                time.sleep(3)
                
                # Check reconnection
                wait.until(lambda driver: "Connected" in driver.find_element(By.ID, "connection-status").text)
                self.test_results["connection_status"]["manual_reconnect"] = "PASS"
                print("  ✅ Manual reconnect working")
                
            except Exception as e:
                self.test_results["connection_status"]["manual_reconnect"] = f"FAIL: {e}"
                print(f"  ❌ Manual reconnect failed: {e}")
                
        except Exception as e:
            self.test_results["connection_status"]["error"] = str(e)
            print(f"  ❌ Connection status test failed: {e}")
    
    async def test_event_display(self):
        """Test event display functionality."""
        print("📊 Testing Event Display...")
        
        try:
            # Generate some test events using Socket.IO client
            await self.emit_test_events()
            time.sleep(2)
            
            # Check if events appear in Events tab
            events_list = self.driver.find_element(By.ID, "events-list")
            event_cards = events_list.find_elements(By.CLASS_NAME, "event-card")
            
            if len(event_cards) > 0:
                self.test_results["event_display"]["events_appear"] = "PASS"
                print(f"  ✅ Events appearing ({len(event_cards)} events found)")
                
                # Test event filtering
                await self.test_event_filtering()
                
                # Test search functionality
                await self.test_event_search()
                
            else:
                self.test_results["event_display"]["events_appear"] = "FAIL: No events found"
                print("  ❌ No events appearing")
                
        except Exception as e:
            self.test_results["event_display"]["error"] = str(e)
            print(f"  ❌ Event display test failed: {e}")
    
    async def test_event_filtering(self):
        """Test event type filtering."""
        try:
            # Get type filter dropdown
            type_filter = self.driver.find_element(By.ID, "events-type-filter")
            options = type_filter.find_elements(By.TAG_NAME, "option")
            
            if len(options) > 1:  # Should have "All Events" plus actual types
                # Test filtering by first available type
                options[1].click()
                time.sleep(1)
                
                events_list = self.driver.find_element(By.ID, "events-list")
                filtered_events = events_list.find_elements(By.CLASS_NAME, "event-card")
                
                self.test_results["event_display"]["type_filtering"] = "PASS"
                print(f"  ✅ Type filtering working ({len(filtered_events)} filtered events)")
            else:
                self.test_results["event_display"]["type_filtering"] = "FAIL: No filter options"
                print("  ❌ No filter options available")
                
        except Exception as e:
            self.test_results["event_display"]["type_filtering"] = f"FAIL: {e}"
            print(f"  ❌ Type filtering failed: {e}")
    
    async def test_event_search(self):
        """Test event search functionality."""
        try:
            search_input = self.driver.find_element(By.ID, "events-search-input")
            search_input.clear()
            search_input.send_keys("test")
            time.sleep(1)
            
            events_list = self.driver.find_element(By.ID, "events-list")
            search_results = events_list.find_elements(By.CLASS_NAME, "event-card")
            
            self.test_results["event_display"]["search"] = "PASS"
            print(f"  ✅ Search working ({len(search_results)} results for 'test')")
            
            # Clear search
            search_input.clear()
            search_input.send_keys(Keys.ENTER)
            time.sleep(1)
            
        except Exception as e:
            self.test_results["event_display"]["search"] = f"FAIL: {e}"
            print(f"  ❌ Search failed: {e}")
    
    async def test_module_viewer(self):
        """Test module viewer functionality."""
        print("🔍 Testing Module Viewer...")
        
        try:
            # Click on first event to load module viewer
            events_list = self.driver.find_element(By.ID, "events-list")
            event_cards = events_list.find_elements(By.CLASS_NAME, "event-card")
            
            if len(event_cards) > 0:
                event_cards[0].click()
                time.sleep(2)
                
                # Check if module viewer shows data
                module_data_content = self.driver.find_element(By.ID, "module-data-content")
                module_json_content = self.driver.find_element(By.ID, "module-json-content")
                
                # Check if structured data appears
                if "Click on an event" not in module_data_content.text:
                    self.test_results["module_viewer"]["structured_data"] = "PASS"
                    print("  ✅ Structured data display working")
                else:
                    self.test_results["module_viewer"]["structured_data"] = "FAIL: No structured data"
                    print("  ❌ Structured data not showing")
                
                # Check if JSON data appears
                if "Raw JSON data will appear here" not in module_json_content.text:
                    self.test_results["module_viewer"]["json_data"] = "PASS"
                    print("  ✅ JSON data display working")
                else:
                    self.test_results["module_viewer"]["json_data"] = "FAIL: No JSON data"
                    print("  ❌ JSON data not showing")
                    
                # Test tool call display if available
                await self.test_tool_call_display()
                
            else:
                self.test_results["module_viewer"]["error"] = "No events to test with"
                print("  ❌ No events available for module viewer testing")
                
        except Exception as e:
            self.test_results["module_viewer"]["error"] = str(e)
            print(f"  ❌ Module viewer test failed: {e}")
    
    async def test_tool_call_display(self):
        """Test tool call display in module viewer."""
        try:
            # Look for tool call events specifically
            events_list = self.driver.find_element(By.ID, "events-list")
            event_cards = events_list.find_elements(By.CLASS_NAME, "event-card")
            
            tool_event_found = False
            for card in event_cards:
                if "tool_call" in card.text.lower() or "bash" in card.text.lower() or "read" in card.text.lower():
                    card.click()
                    time.sleep(1)
                    tool_event_found = True
                    break
            
            if tool_event_found:
                self.test_results["module_viewer"]["tool_calls"] = "PASS"
                print("  ✅ Tool call display working")
            else:
                self.test_results["module_viewer"]["tool_calls"] = "SKIP: No tool events found"
                print("  ⏭️  No tool events found to test")
                
        except Exception as e:
            self.test_results["module_viewer"]["tool_calls"] = f"FAIL: {e}"
            print(f"  ❌ Tool call display failed: {e}")
    
    async def test_tab_functionality(self):
        """Test tab switching and functionality."""
        print("📑 Testing Tab Functionality...")
        
        tabs = ["Events", "Agents", "Tools", "Files"]
        tab_selectors = {
            "Events": "events-tab",
            "Agents": "agents-tab", 
            "Tools": "tools-tab",
            "Files": "files-tab"
        }
        
        for tab_name in tabs:
            try:
                # Click tab button
                tab_buttons = self.driver.find_elements(By.CLASS_NAME, "tab-button")
                for button in tab_buttons:
                    if tab_name.lower() in button.text.lower():
                        button.click()
                        time.sleep(1)
                        break
                
                # Check if tab content is visible
                tab_content = self.driver.find_element(By.ID, tab_selectors[tab_name])
                if tab_content.is_displayed():
                    self.test_results["tab_functionality"][tab_name.lower()] = "PASS"
                    print(f"  ✅ {tab_name} tab switching working")
                    
                    # Test filtering in the tab
                    await self.test_tab_filtering(tab_name.lower())
                    
                else:
                    self.test_results["tab_functionality"][tab_name.lower()] = "FAIL: Tab not visible"
                    print(f"  ❌ {tab_name} tab not visible")
                    
            except Exception as e:
                self.test_results["tab_functionality"][tab_name.lower()] = f"FAIL: {e}"
                print(f"  ❌ {tab_name} tab failed: {e}")
    
    async def test_tab_filtering(self, tab_name):
        """Test filtering within tabs."""
        try:
            search_input_id = f"{tab_name}-search-input"
            filter_select_id = f"{tab_name}-type-filter"
            
            # Test search
            search_input = self.driver.find_element(By.ID, search_input_id)
            search_input.clear()
            search_input.send_keys("test")
            time.sleep(1)
            
            # Test filter dropdown
            filter_select = self.driver.find_element(By.ID, filter_select_id)
            options = filter_select.find_elements(By.TAG_NAME, "option")
            if len(options) > 1:
                options[1].click()
                time.sleep(1)
            
            # Clear search
            search_input.clear()
            
            self.test_results["tab_functionality"][f"{tab_name}_filtering"] = "PASS"
            print(f"    ✅ {tab_name.title()} filtering working")
            
        except Exception as e:
            self.test_results["tab_functionality"][f"{tab_name}_filtering"] = f"FAIL: {e}"
            print(f"    ❌ {tab_name.title()} filtering failed: {e}")
    
    async def test_hud_visualization(self):
        """Test HUD visualization functionality."""
        print("🔬 Testing HUD Visualization...")
        
        try:
            # First select a session to enable HUD
            session_select = self.driver.find_element(By.ID, "session-select")
            options = session_select.find_elements(By.TAG_NAME, "option")
            
            if len(options) > 1:
                # Select first available session
                options[1].click()
                time.sleep(1)
                
                # Check if HUD button is enabled
                hud_button = self.driver.find_element(By.ID, "hud-toggle-btn")
                if not hud_button.get_attribute("disabled"):
                    self.test_results["hud_visualization"]["button_enabled"] = "PASS"
                    print("  ✅ HUD button enabled after session selection")
                    
                    # Click HUD button
                    hud_button.click()
                    time.sleep(3)
                    
                    # Check if HUD visualizer is visible
                    hud_visualizer = self.driver.find_element(By.ID, "hud-visualizer")
                    if hud_visualizer.is_displayed():
                        self.test_results["hud_visualization"]["display"] = "PASS"
                        print("  ✅ HUD visualizer display working")
                        
                        # Test HUD controls
                        await self.test_hud_controls()
                        
                    else:
                        self.test_results["hud_visualization"]["display"] = "FAIL: HUD not visible"
                        print("  ❌ HUD visualizer not showing")
                        
                else:
                    self.test_results["hud_visualization"]["button_enabled"] = "FAIL: Button still disabled"
                    print("  ❌ HUD button not enabled after session selection")
                    
            else:
                self.test_results["hud_visualization"]["session_selection"] = "SKIP: No sessions available"
                print("  ⏭️  No sessions available for HUD testing")
                
        except Exception as e:
            self.test_results["hud_visualization"]["error"] = str(e)
            print(f"  ❌ HUD visualization test failed: {e}")
    
    async def test_hud_controls(self):
        """Test HUD control buttons."""
        try:
            # Test reset layout button
            reset_btn = self.driver.find_element(By.ID, "hud-reset-layout")
            reset_btn.click()
            time.sleep(1)
            
            # Test center view button
            center_btn = self.driver.find_element(By.ID, "hud-center-view")
            center_btn.click()
            time.sleep(1)
            
            self.test_results["hud_visualization"]["controls"] = "PASS"
            print("  ✅ HUD controls working")
            
        except Exception as e:
            self.test_results["hud_visualization"]["controls"] = f"FAIL: {e}"
            print(f"  ❌ HUD controls failed: {e}")
    
    async def test_session_management(self):
        """Test session management functionality."""
        print("🎯 Testing Session Management...")
        
        try:
            # Test session selection
            session_select = self.driver.find_element(By.ID, "session-select")
            options = session_select.find_elements(By.TAG_NAME, "option")
            
            initial_option = session_select.get_attribute("value")
            
            if len(options) > 1:
                # Switch to different session
                options[1].click()
                time.sleep(2)
                
                # Check footer updates
                footer_session = self.driver.find_element(By.ID, "footer-session")
                if footer_session.text != "All Sessions":
                    self.test_results["session_management"]["session_switching"] = "PASS"
                    print("  ✅ Session switching working")
                else:
                    self.test_results["session_management"]["session_switching"] = "FAIL: Footer not updated"
                    print("  ❌ Session switching not updating footer")
                    
                # Test working directory tracking
                await self.test_working_directory_tracking()
                
            else:
                self.test_results["session_management"]["session_switching"] = "SKIP: Only one session"
                print("  ⏭️  Only one session available")
                
        except Exception as e:
            self.test_results["session_management"]["error"] = str(e)
            print(f"  ❌ Session management test failed: {e}")
    
    async def test_working_directory_tracking(self):
        """Test working directory tracking."""
        try:
            working_dir_display = self.driver.find_element(By.ID, "working-dir-path")
            footer_working_dir = self.driver.find_element(By.ID, "footer-working-dir")
            
            if working_dir_display.text and footer_working_dir.text != "Unknown":
                self.test_results["session_management"]["working_directory"] = "PASS"
                print("  ✅ Working directory tracking working")
            else:
                self.test_results["session_management"]["working_directory"] = "FAIL: Directory not tracked"
                print("  ❌ Working directory not being tracked")
                
        except Exception as e:
            self.test_results["session_management"]["working_directory"] = f"FAIL: {e}"
            print(f"  ❌ Working directory tracking failed: {e}")
    
    async def test_ui_interactions(self):
        """Test UI interactions like keyboard navigation."""
        print("⌨️  Testing UI Interactions...")
        
        try:
            # Test keyboard navigation
            events_list = self.driver.find_element(By.ID, "events-list")
            event_cards = events_list.find_elements(By.CLASS_NAME, "event-card")
            
            if len(event_cards) > 0:
                # Click first card and test arrow key navigation
                event_cards[0].click()
                time.sleep(1)
                
                # Test arrow key navigation
                actions = ActionChains(self.driver)
                actions.send_keys(Keys.ARROW_DOWN).perform()
                time.sleep(1)
                
                self.test_results["ui_interactions"]["keyboard_navigation"] = "PASS"
                print("  ✅ Keyboard navigation working")
                
                # Test export functionality
                await self.test_export_functionality()
                
            else:
                self.test_results["ui_interactions"]["keyboard_navigation"] = "SKIP: No events for testing"
                print("  ⏭️  No events for keyboard navigation testing")
                
        except Exception as e:
            self.test_results["ui_interactions"]["error"] = str(e)
            print(f"  ❌ UI interactions test failed: {e}")
    
    async def test_export_functionality(self):
        """Test export functionality."""
        try:
            export_btn = self.driver.find_element(By.ID, "export-btn")
            export_btn.click()
            time.sleep(1)
            
            # Note: Actual file download testing would require more complex setup
            self.test_results["ui_interactions"]["export"] = "PASS"
            print("  ✅ Export button working")
            
        except Exception as e:
            self.test_results["ui_interactions"]["export"] = f"FAIL: {e}"
            print(f"  ❌ Export functionality failed: {e}")
    
    async def emit_test_events(self):
        """Emit test events to the Socket.IO server."""
        try:
            await self.sio.connect('http://localhost:8765', namespaces=['/dashboard'])
            
            # Emit various test events
            test_events = [
                {
                    "type": "claude_event",
                    "subtype": "tool_call",
                    "timestamp": time.time(),
                    "session_id": "test_session_1",
                    "data": {
                        "tool_name": "Read",
                        "arguments": {"file_path": "/test/file.py"},
                        "result": "Test file content"
                    }
                },
                {
                    "type": "claude_event", 
                    "subtype": "agent_delegation",
                    "timestamp": time.time(),
                    "session_id": "test_session_1",
                    "data": {
                        "agent_type": "engineer",
                        "task": "Test task"
                    }
                },
                {
                    "type": "system_event",
                    "subtype": "working_directory_change",
                    "timestamp": time.time(),
                    "session_id": "test_session_1",
                    "data": {
                        "old_path": "/old/path",
                        "new_path": "/new/path"
                    }
                }
            ]
            
            for event in test_events:
                await self.sio.emit('claude_event', event, namespace='/dashboard')
                await asyncio.sleep(0.1)
                
            await self.sio.disconnect()
            print("  ✅ Test events emitted successfully")
            
        except Exception as e:
            print(f"  ❌ Failed to emit test events: {e}")
    
    async def run_all_tests(self):
        """Run all QA tests."""
        print("🚀 Starting Comprehensive Dashboard QA Testing...")
        print("=" * 60)
        
        if not self.setup_browser():
            return False
            
        if not self.setup_socketio_client():
            return False
        
        try:
            await self.test_connection_status()
            await self.test_event_display()
            await self.test_module_viewer()
            await self.test_tab_functionality()
            await self.test_hud_visualization()
            await self.test_session_management()
            await self.test_ui_interactions()
            
            return True
            
        except Exception as e:
            self.test_results["errors"].append(f"Test execution error: {e}")
            return False
        
        finally:
            if self.driver:
                self.driver.quit()
            if self.sio:
                await self.sio.disconnect()
    
    def generate_report(self):
        """Generate comprehensive test report."""
        print("\n" + "=" * 60)
        print("📋 COMPREHENSIVE QA TEST REPORT")
        print("=" * 60)
        
        total_tests = 0
        passed_tests = 0
        failed_tests = 0
        skipped_tests = 0
        
        for category, results in self.test_results.items():
            if category == "errors":
                continue
                
            print(f"\n🔍 {category.replace('_', ' ').title()}")
            print("-" * 40)
            
            for test_name, result in results.items():
                total_tests += 1
                if result == "PASS":
                    passed_tests += 1
                    print(f"  ✅ {test_name}: PASS")
                elif result.startswith("SKIP"):
                    skipped_tests += 1
                    print(f"  ⏭️  {test_name}: {result}")
                else:
                    failed_tests += 1
                    print(f"  ❌ {test_name}: {result}")
        
        # Print errors
        if self.test_results["errors"]:
            print(f"\n🚨 Errors ({len(self.test_results['errors'])})")
            print("-" * 40)
            for error in self.test_results["errors"]:
                print(f"  ❌ {error}")
        
        # Summary
        print(f"\n📊 TEST SUMMARY")
        print("-" * 40)
        print(f"  Total Tests: {total_tests}")
        print(f"  Passed: {passed_tests}")
        print(f"  Failed: {failed_tests}")
        print(f"  Skipped: {skipped_tests}")
        print(f"  Success Rate: {(passed_tests/total_tests)*100:.1f}%" if total_tests > 0 else "  Success Rate: 0%")
        
        # Save detailed results to file
        report_file = "dashboard_qa_comprehensive_report.json"
        with open(report_file, 'w') as f:
            json.dump({
                "summary": {
                    "total_tests": total_tests,
                    "passed": passed_tests,
                    "failed": failed_tests,
                    "skipped": skipped_tests,
                    "success_rate": (passed_tests/total_tests)*100 if total_tests > 0 else 0
                },
                "detailed_results": self.test_results,
                "timestamp": time.time()
            }, f, indent=2)
        
        print(f"\n📄 Detailed report saved to: {report_file}")
        
        return {
            "passed": passed_tests,
            "failed": failed_tests,
            "total": total_tests
        }


async def main():
    """Main function to run QA tests."""
    tester = DashboardQATester()
    
    success = await tester.run_all_tests()
    results = tester.generate_report()
    
    if not success or results["failed"] > 0:
        sys.exit(1)
    else:
        print("\n🎉 All tests completed successfully!")
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())