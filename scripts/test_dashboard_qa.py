#!/usr/bin/env python3
"""Comprehensive QA testing for Claude MPM Socket.IO Dashboard.

This script performs systematic testing of all dashboard functionality including:
- Server health and availability
- Dashboard HTML serving 
- Socket.IO connectivity and events
- Error handling and edge cases
- Performance under load
- Security validation
"""

import json
import time
import subprocess
import signal
import sys
import requests
import socketio
import threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Any, Optional
import urllib.parse
import webbrowser
import tempfile
import os

class DashboardQATester:
    """Comprehensive QA tester for the Socket.IO dashboard."""
    
    def __init__(self, port: int = 8766):
        self.port = port
        self.base_url = f"http://localhost:{port}"
        self.sio = None
        self.test_results = {}
        self.server_process = None
        self.events_received = []
        self.connection_status = "disconnected"
        
    def log(self, message: str, level: str = "INFO"):
        """Log test messages with timestamp."""
        timestamp = time.strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")
        
    def test_server_health(self) -> Dict[str, Any]:
        """Test server health endpoints."""
        self.log("Testing server health endpoints...")
        results = {}
        
        try:
            # Test health endpoint
            response = requests.get(f"{self.base_url}/health", timeout=5)
            results["health_endpoint"] = {
                "status": response.status_code,
                "response_time": response.elapsed.total_seconds(),
                "content": response.json() if response.status_code == 200 else None
            }
            
            # Test status endpoint
            response = requests.get(f"{self.base_url}/status", timeout=5)
            results["status_endpoint"] = {
                "status": response.status_code,
                "response_time": response.elapsed.total_seconds(),
                "content": response.json() if response.status_code == 200 else None
            }
            
            self.log("✓ Server health tests completed")
            
        except Exception as e:
            self.log(f"✗ Server health test failed: {e}", "ERROR")
            results["error"] = str(e)
            
        return results
    
    def test_dashboard_serving(self) -> Dict[str, Any]:
        """Test dashboard HTML serving."""
        self.log("Testing dashboard HTML serving...")
        results = {}
        
        try:
            # Test main dashboard endpoint
            response = requests.get(f"{self.base_url}/claude_mpm_socketio_dashboard.html", timeout=5)
            results["dashboard_html"] = {
                "status": response.status_code,
                "response_time": response.elapsed.total_seconds(),
                "content_length": len(response.content),
                "content_type": response.headers.get("content-type", "")
            }
            
            # Test dashboard alias
            response = requests.get(f"{self.base_url}/dashboard", timeout=5)
            results["dashboard_alias"] = {
                "status": response.status_code,
                "response_time": response.elapsed.total_seconds(),
                "content_length": len(response.content)
            }
            
            # Validate HTML content
            if results["dashboard_html"]["status"] == 200:
                html_content = requests.get(f"{self.base_url}/claude_mpm_socketio_dashboard.html").text
                results["html_validation"] = {
                    "has_socket_io_script": "socket.io.min.js" in html_content,
                    "has_dashboard_title": "Claude MPM Socket.IO Dashboard" in html_content,
                    "has_connect_button": "connectSocket()" in html_content,
                    "has_event_filters": "event-type-filter" in html_content,
                    "has_metrics_section": "metric-card" in html_content
                }
            
            self.log("✓ Dashboard serving tests completed")
            
        except Exception as e:
            self.log(f"✗ Dashboard serving test failed: {e}", "ERROR")
            results["error"] = str(e)
            
        return results
    
    def test_socketio_connectivity(self) -> Dict[str, Any]:
        """Test Socket.IO connectivity and basic events."""
        self.log("Testing Socket.IO connectivity...")
        results = {}
        
        try:
            # Create Socket.IO client
            self.sio = socketio.Client()
            
            @self.sio.event
            def connect():
                self.connection_status = "connected"
                self.log("✓ Socket.IO client connected")
            
            @self.sio.event
            def disconnect():
                self.connection_status = "disconnected"
                self.log("Socket.IO client disconnected")
            
            @self.sio.event
            def status(data):
                self.log(f"Received status: {data}")
                results["status_event"] = data
            
            @self.sio.event
            def claude_event(data):
                self.log(f"Received claude_event: {data}")
                self.events_received.append(data)
            
            @self.sio.event
            def history(data):
                self.log(f"Received history: {len(data.get('events', []))} events")
                results["history_event"] = data
            
            # Connect to server
            start_time = time.time()
            self.sio.connect(self.base_url)
            connection_time = time.time() - start_time
            
            results["connection"] = {
                "success": self.connection_status == "connected",
                "connection_time": connection_time,
                "socket_id": self.sio.sid
            }
            
            # Test status request
            if self.connection_status == "connected":
                self.sio.emit("get_status")
                time.sleep(1)  # Wait for response
                
                # Test history request
                self.sio.emit("get_history", {"limit": 10})
                time.sleep(1)  # Wait for response
            
            self.log("✓ Socket.IO connectivity tests completed")
            
        except Exception as e:
            self.log(f"✗ Socket.IO connectivity test failed: {e}", "ERROR")
            results["error"] = str(e)
            
        return results
    
    def test_event_handling(self) -> Dict[str, Any]:
        """Test event handling and broadcasting."""
        self.log("Testing event handling...")
        results = {}
        
        if not self.sio or self.connection_status != "connected":
            self.log("Skipping event handling tests - no Socket.IO connection", "WARN")
            return {"skipped": "No Socket.IO connection"}
        
        try:
            # Clear received events
            self.events_received.clear()
            
            # Emit test events
            test_events = [
                {"type": "session.start", "data": {"session_id": "test-123"}},
                {"type": "agent.loaded", "data": {"agent": "qa_test_agent"}},
                {"type": "hook.pre_run", "data": {"hook": "test_hook"}},
                {"type": "todo.created", "data": {"task": "Test task"}},
                {"type": "memory.stored", "data": {"key": "test_key", "value": "test_value"}},
                {"type": "log.info", "data": {"message": "Test log message"}}
            ]
            
            for event in test_events:
                self.sio.emit("claude_event", event)
                time.sleep(0.1)  # Small delay between events
            
            # Wait for events to be processed
            time.sleep(2)
            
            results["events_sent"] = len(test_events)
            results["events_received"] = len(self.events_received)
            results["event_types_received"] = [e.get("type") for e in self.events_received]
            
            self.log(f"✓ Event handling tests completed: {results['events_received']}/{results['events_sent']} events")
            
        except Exception as e:
            self.log(f"✗ Event handling test failed: {e}", "ERROR")
            results["error"] = str(e)
            
        return results
    
    def test_error_handling(self) -> Dict[str, Any]:
        """Test error handling and edge cases."""
        self.log("Testing error handling...")
        results = {}
        
        try:
            # Test invalid endpoints
            invalid_endpoints = ["/nonexistent", "/admin/invalid", "/api/v1/invalid"]
            for endpoint in invalid_endpoints:
                response = requests.get(f"{self.base_url}{endpoint}", timeout=5)
                results[f"invalid_endpoint_{endpoint.replace('/', '_')}"] = response.status_code
            
            # Test malformed Socket.IO connection
            try:
                bad_sio = socketio.Client()
                bad_sio.connect(f"http://localhost:99999")  # Non-existent port
            except Exception as e:
                results["connection_to_invalid_port"] = "correctly_failed"
            
            # Test with authentication (if enabled)
            # This would test authentication failures
            
            self.log("✓ Error handling tests completed")
            
        except Exception as e:
            self.log(f"✗ Error handling test failed: {e}", "ERROR")
            results["error"] = str(e)
            
        return results
    
    def test_performance(self) -> Dict[str, Any]:
        """Test performance under load."""
        self.log("Testing performance under load...")
        results = {}
        
        if not self.sio or self.connection_status != "connected":
            self.log("Skipping performance tests - no Socket.IO connection", "WARN")
            return {"skipped": "No Socket.IO connection"}
        
        try:
            # Clear received events
            self.events_received.clear()
            
            # Send burst of events
            num_events = 100
            start_time = time.time()
            
            for i in range(num_events):
                event = {
                    "type": f"performance.test_{i % 10}",
                    "data": {"index": i, "timestamp": time.time()},
                    "timestamp": time.time()
                }
                self.sio.emit("claude_event", event)
            
            send_time = time.time() - start_time
            
            # Wait for events to be processed
            time.sleep(5)
            
            results = {
                "events_sent": num_events,
                "send_time": send_time,
                "events_per_second": num_events / send_time,
                "events_received": len(self.events_received),
                "reception_rate": len(self.events_received) / num_events if num_events > 0 else 0
            }
            
            self.log(f"✓ Performance tests completed: {results['events_per_second']:.1f} events/sec")
            
        except Exception as e:
            self.log(f"✗ Performance test failed: {e}", "ERROR")
            results["error"] = str(e)
            
        return results
    
    def test_browser_compatibility(self) -> Dict[str, Any]:
        """Test basic browser compatibility (limited without actual browser)."""
        self.log("Testing browser compatibility...")
        results = {}
        
        try:
            # Test that dashboard HTML uses standard web technologies
            response = requests.get(f"{self.base_url}/claude_mpm_socketio_dashboard.html")
            html_content = response.text
            
            # Check for modern web standards
            results["uses_html5_doctype"] = html_content.startswith("<!DOCTYPE html>")
            results["has_viewport_meta"] = 'name="viewport"' in html_content
            results["uses_modern_css"] = "grid-template-columns" in html_content
            results["uses_es6_features"] = "const " in html_content and "let " in html_content
            results["responsive_design"] = "@media" in html_content
            
            # Check CDN resources
            results["socket_io_cdn"] = "cdn.socket.io" in html_content
            
            self.log("✓ Browser compatibility tests completed")
            
        except Exception as e:
            self.log(f"✗ Browser compatibility test failed: {e}", "ERROR")
            results["error"] = str(e)
            
        return results
    
    def test_security(self) -> Dict[str, Any]:
        """Test basic security aspects."""
        self.log("Testing security aspects...")
        results = {}
        
        try:
            # Test CORS headers
            response = requests.options(self.base_url)
            results["cors_headers"] = dict(response.headers)
            
            # Test for common security headers
            security_headers = [
                "X-Content-Type-Options",
                "X-Frame-Options", 
                "X-XSS-Protection",
                "Strict-Transport-Security"
            ]
            
            for header in security_headers:
                results[f"security_header_{header.lower().replace('-', '_')}"] = header in response.headers
            
            # Test authentication if token is set
            auth_token = os.environ.get("CLAUDE_MPM_SOCKETIO_TOKEN")
            if auth_token:
                results["authentication_enabled"] = True
                # Test connection with wrong token
                try:
                    bad_sio = socketio.Client()
                    bad_sio.connect(self.base_url, auth={"token": "invalid_token"})
                    results["auth_enforcement"] = False
                except Exception:
                    results["auth_enforcement"] = True
            else:
                results["authentication_enabled"] = False
            
            self.log("✓ Security tests completed")
            
        except Exception as e:
            self.log(f"✗ Security test failed: {e}", "ERROR")
            results["error"] = str(e)
            
        return results
    
    def cleanup(self):
        """Clean up test resources."""
        if self.sio and self.sio.connected:
            self.sio.disconnect()
        
    def run_full_qa_suite(self) -> Dict[str, Any]:
        """Run the complete QA test suite."""
        self.log("=" * 60)
        self.log("Starting comprehensive QA testing of Socket.IO Dashboard")
        self.log("=" * 60)
        
        start_time = time.time()
        
        # Run all test categories
        test_categories = [
            ("Server Health", self.test_server_health),
            ("Dashboard Serving", self.test_dashboard_serving),
            ("Socket.IO Connectivity", self.test_socketio_connectivity),
            ("Event Handling", self.test_event_handling),
            ("Error Handling", self.test_error_handling),
            ("Performance", self.test_performance),
            ("Browser Compatibility", self.test_browser_compatibility),
            ("Security", self.test_security)
        ]
        
        all_results = {}
        
        for category_name, test_func in test_categories:
            self.log(f"\n--- {category_name} Tests ---")
            try:
                results = test_func()
                all_results[category_name.lower().replace(" ", "_")] = results
            except Exception as e:
                self.log(f"✗ {category_name} test suite failed: {e}", "ERROR")
                all_results[category_name.lower().replace(" ", "_")] = {"error": str(e)}
        
        total_time = time.time() - start_time
        
        # Cleanup
        self.cleanup()
        
        # Generate summary
        all_results["test_summary"] = {
            "total_time": total_time,
            "categories_tested": len(test_categories),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "port": self.port
        }
        
        self.log("=" * 60)
        self.log(f"QA testing completed in {total_time:.2f} seconds")
        self.log("=" * 60)
        
        return all_results

def main():
    """Main entry point for QA testing."""
    import argparse
    
    parser = argparse.ArgumentParser(description="QA testing for Claude MPM Socket.IO Dashboard")
    parser.add_argument("--port", type=int, default=8766, help="Socket.IO server port")
    parser.add_argument("--output", type=str, help="JSON output file for results")
    parser.add_argument("--quick", action="store_true", help="Run quick tests only")
    
    args = parser.parse_args()
    
    tester = DashboardQATester(port=args.port)
    
    try:
        if args.quick:
            # Quick tests only
            results = {
                "server_health": tester.test_server_health(),
                "dashboard_serving": tester.test_dashboard_serving()
            }
        else:
            # Full test suite
            results = tester.run_full_qa_suite()
        
        # Output results
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            print(f"\nResults saved to: {args.output}")
        else:
            print("\n" + "=" * 60)
            print("QA TEST RESULTS SUMMARY")
            print("=" * 60)
            print(json.dumps(results, indent=2, default=str))
            
    except KeyboardInterrupt:
        print("\n\nQA testing interrupted by user")
    except Exception as e:
        print(f"\nQA testing failed: {e}")
        sys.exit(1)
    finally:
        tester.cleanup()

if __name__ == "__main__":
    main()