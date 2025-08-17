#!/usr/bin/env python3
"""Connection and Authentication Diagnostic.

This script specifically tests connection and authentication issues:
1. Tests different authentication scenarios (valid/invalid tokens)
2. Checks timeout and disconnection behavior
3. Tests namespace-specific authentication
4. Monitors connection state changes
5. Tests reconnection behavior

WHY this focused diagnostic:
- Authentication issues are a common cause of silent failures
- Timeout problems can cause events to be lost
- Namespace routing can fail without clear error messages
- Connection state issues can cause intermittent problems
"""

import asyncio
import json
import sys
import time
import threading
from datetime import datetime
from typing import Dict, Any, Optional

try:
    import socketio
    SOCKETIO_AVAILABLE = True
except ImportError:
    print("ERROR: python-socketio package not installed. Run: pip install python-socketio[asyncio_client]")
    sys.exit(1)


class ConnectionAuthDiagnostic:
    """Diagnostic tool for connection and authentication issues."""
    
    def __init__(self, server_url: str = "http://localhost:8765"):
        self.server_url = server_url
        self.test_start = datetime.now()
        self.test_results = []
        self.errors = []
        
        print(f"🔐 CONNECTION & AUTHENTICATION DIAGNOSTIC")
        print(f"🌐 Server URL: {server_url}")
        print(f"📅 Start time: {self.test_start.isoformat()}")
        print("=" * 80)
    
    def log_result(self, test_name: str, status: str, details: str, data: Optional[Dict] = None):
        """Log a test result."""
        result = {
            'test_name': test_name,
            'status': status,
            'details': details,
            'timestamp': datetime.now().isoformat(),
            'data': data
        }
        self.test_results.append(result)
        
        status_symbol = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
        print(f"{status_symbol} {test_name}: {status} - {details}")
        
        if data:
            print(f"   Data: {json.dumps(data, indent=2)[:300]}...")
    
    def test_basic_connection(self):
        """Test basic connection without authentication."""
        print("\n🔌 Testing basic connection...")
        
        try:
            client = socketio.Client(
                reconnection=False,
                logger=True,
                engineio_logger=True
            )
            
            connected = False
            connection_error = None
            
            @client.event
            def connect():
                nonlocal connected
                connected = True
            
            @client.event
            def connect_error(data):
                nonlocal connection_error
                connection_error = data
            
            # Try to connect without auth
            try:
                client.connect(self.server_url, wait=True, wait_timeout=10)
                
                if connected:
                    self.log_result("Basic Connection", "PASS", "Connected without authentication")
                    client.disconnect()
                else:
                    self.log_result("Basic Connection", "FAIL", "Connection failed unexpectedly")
                    
            except Exception as e:
                if connection_error:
                    self.log_result("Basic Connection", "FAIL", f"Connection rejected: {connection_error}")
                else:
                    self.log_result("Basic Connection", "FAIL", f"Connection exception: {e}")
                
        except Exception as e:
            self.log_result("Basic Connection", "FAIL", f"Test setup error: {e}")
    
    def test_valid_authentication(self):
        """Test connection with valid authentication."""
        print("\n🔑 Testing valid authentication...")
        
        try:
            client = socketio.Client(
                reconnection=False,
                logger=False,
                engineio_logger=False
            )
            
            connected = False
            auth_data_received = None
            
            @client.event
            def connect():
                nonlocal connected
                connected = True
            
            @client.event
            def connect_error(data):
                self.log_result("Valid Auth", "FAIL", f"Connection rejected with valid token: {data}")
            
            # Connect with valid auth
            auth_data = {'token': 'dev-token'}
            
            try:
                client.connect(self.server_url, auth=auth_data, wait=True, wait_timeout=10)
                
                if connected:
                    self.log_result("Valid Auth", "PASS", "Connected with valid dev-token", auth_data)
                    client.disconnect()
                else:
                    self.log_result("Valid Auth", "FAIL", "Failed to connect with valid token")
                    
            except Exception as e:
                self.log_result("Valid Auth", "FAIL", f"Connection with valid token failed: {e}")
                
        except Exception as e:
            self.log_result("Valid Auth", "FAIL", f"Test setup error: {e}")
    
    def test_invalid_authentication(self):
        """Test connection with invalid authentication."""
        print("\n🚫 Testing invalid authentication...")
        
        try:
            client = socketio.Client(
                reconnection=False,
                logger=False,
                engineio_logger=False
            )
            
            connected = False
            connection_error = None
            
            @client.event
            def connect():
                nonlocal connected
                connected = True
            
            @client.event
            def connect_error(data):
                nonlocal connection_error
                connection_error = data
            
            # Connect with invalid auth
            auth_data = {'token': 'invalid-token-12345'}
            
            try:
                client.connect(self.server_url, auth=auth_data, wait=True, wait_timeout=10)
                
                if connected:
                    self.log_result("Invalid Auth", "WARN", "Connected with invalid token - security issue!", auth_data)
                    client.disconnect()
                elif connection_error:
                    self.log_result("Invalid Auth", "PASS", f"Correctly rejected invalid token: {connection_error}")
                else:
                    self.log_result("Invalid Auth", "FAIL", "Connection failed without clear error")
                    
            except Exception as e:
                if connection_error:
                    self.log_result("Invalid Auth", "PASS", f"Correctly rejected invalid token: {connection_error}")
                else:
                    self.log_result("Invalid Auth", "FAIL", f"Unexpected exception: {e}")
                
        except Exception as e:
            self.log_result("Invalid Auth", "FAIL", f"Test setup error: {e}")
    
    def test_namespace_authentication(self):
        """Test authentication for specific namespaces."""
        print("\n🏷️ Testing namespace authentication...")
        
        namespaces = ['/system', '/hook', '/session', '/claude', '/agent', '/todo', '/memory', '/log']
        
        for namespace in namespaces:
            try:
                client = socketio.Client(
                    reconnection=False,
                    logger=False,
                    engineio_logger=False
                )
                
                connected = False
                connection_error = None
                
                @client.event
                def connect():
                    nonlocal connected
                    connected = True
                
                @client.event
                def connect_error(data):
                    nonlocal connection_error
                    connection_error = data
                
                # Connect to specific namespace with auth
                auth_data = {'token': 'dev-token'}
                
                try:
                    client.connect(
                        self.server_url + namespace,
                        auth=auth_data,
                        wait=True,
                        wait_timeout=5
                    )
                    
                    if connected:
                        self.log_result(f"Namespace Auth {namespace}", "PASS", f"Connected to {namespace} with auth")
                        client.disconnect()
                    elif connection_error:
                        self.log_result(f"Namespace Auth {namespace}", "FAIL", f"Auth rejected: {connection_error}")
                    else:
                        self.log_result(f"Namespace Auth {namespace}", "FAIL", "Connection failed without error")
                        
                except Exception as e:
                    if connection_error:
                        self.log_result(f"Namespace Auth {namespace}", "FAIL", f"Auth error: {connection_error}")
                    else:
                        self.log_result(f"Namespace Auth {namespace}", "FAIL", f"Connection error: {e}")
                
                time.sleep(0.2)  # Small delay between namespace tests
                
            except Exception as e:
                self.log_result(f"Namespace Auth {namespace}", "FAIL", f"Test setup error: {e}")
    
    def test_connection_timeout(self):
        """Test connection timeout behavior."""
        print("\n⏰ Testing connection timeout...")
        
        # Test with very short timeout
        try:
            client = socketio.Client(
                reconnection=False,
                logger=False,
                engineio_logger=False
            )
            
            auth_data = {'token': 'dev-token'}
            start_time = time.time()
            
            try:
                client.connect(self.server_url, auth=auth_data, wait=True, wait_timeout=0.1)  # Very short timeout
                connect_time = time.time() - start_time
                self.log_result("Connection Timeout", "PASS", f"Connected within short timeout ({connect_time:.3f}s)")
                client.disconnect()
                
            except Exception as e:
                connect_time = time.time() - start_time
                if "timeout" in str(e).lower():
                    self.log_result("Connection Timeout", "WARN", f"Timeout after {connect_time:.3f}s - server may be slow")
                else:
                    self.log_result("Connection Timeout", "FAIL", f"Unexpected error: {e}")
                
        except Exception as e:
            self.log_result("Connection Timeout", "FAIL", f"Test setup error: {e}")
    
    def test_reconnection_behavior(self):
        """Test automatic reconnection behavior."""
        print("\n🔄 Testing reconnection behavior...")
        
        try:
            client = socketio.Client(
                reconnection=True,
                reconnection_attempts=3,
                reconnection_delay=0.5,
                reconnection_delay_max=1,
                logger=False,
                engineio_logger=False
            )
            
            connection_count = 0
            disconnection_count = 0
            
            @client.event
            def connect():
                nonlocal connection_count
                connection_count += 1
                print(f"   Connection #{connection_count}")
            
            @client.event
            def disconnect():
                nonlocal disconnection_count
                disconnection_count += 1
                print(f"   Disconnection #{disconnection_count}")
            
            auth_data = {'token': 'dev-token'}
            
            try:
                # Initial connection
                client.connect(self.server_url, auth=auth_data, wait=True, wait_timeout=10)
                
                if connection_count > 0:
                    # Force disconnect to test reconnection
                    client.disconnect()
                    time.sleep(0.1)
                    
                    # Reconnect
                    client.connect(self.server_url, auth=auth_data, wait=True, wait_timeout=10)
                    
                    if connection_count >= 2:
                        self.log_result("Reconnection", "PASS", f"Reconnection successful ({connection_count} connections)")
                    else:
                        self.log_result("Reconnection", "FAIL", f"Reconnection failed ({connection_count} connections)")
                    
                    client.disconnect()
                else:
                    self.log_result("Reconnection", "FAIL", "Initial connection failed")
                
            except Exception as e:
                self.log_result("Reconnection", "FAIL", f"Reconnection test error: {e}")
                
        except Exception as e:
            self.log_result("Reconnection", "FAIL", f"Test setup error: {e}")
    
    def test_multiple_namespace_connections(self):
        """Test connecting to multiple namespaces simultaneously."""
        print("\n🔗 Testing multiple namespace connections...")
        
        try:
            client = socketio.Client(
                reconnection=False,
                logger=False,
                engineio_logger=False
            )
            
            namespace_connections = {}
            
            def make_connect_handler(namespace):
                def connect():
                    namespace_connections[namespace] = True
                return connect
            
            def make_disconnect_handler(namespace):
                def disconnect():
                    namespace_connections[namespace] = False
                return disconnect
            
            # Setup handlers for multiple namespaces
            namespaces = ['/hook', '/system']
            for namespace in namespaces:
                client.on('connect', make_connect_handler(namespace), namespace=namespace)
                client.on('disconnect', make_disconnect_handler(namespace), namespace=namespace)
            
            auth_data = {'token': 'dev-token'}
            
            try:
                client.connect(
                    self.server_url,
                    auth=auth_data,
                    namespaces=namespaces,
                    wait=True,
                    wait_timeout=10
                )
                
                time.sleep(1)  # Allow time for all namespaces to connect
                
                connected_namespaces = [ns for ns, connected in namespace_connections.items() if connected]
                
                if len(connected_namespaces) == len(namespaces):
                    self.log_result("Multi-Namespace", "PASS", f"Connected to all namespaces: {connected_namespaces}")
                elif len(connected_namespaces) > 0:
                    self.log_result("Multi-Namespace", "WARN", f"Partial connection: {connected_namespaces}")
                else:
                    self.log_result("Multi-Namespace", "FAIL", "Failed to connect to any namespace")
                
                client.disconnect()
                
            except Exception as e:
                self.log_result("Multi-Namespace", "FAIL", f"Multi-namespace connection error: {e}")
                
        except Exception as e:
            self.log_result("Multi-Namespace", "FAIL", f"Test setup error: {e}")
    
    def test_ping_pong_behavior(self):
        """Test ping/pong heartbeat behavior."""
        print("\n💓 Testing ping/pong heartbeat...")
        
        try:
            client = socketio.Client(
                reconnection=False,
                logger=True,  # Enable logging to see ping/pong
                engineio_logger=True
            )
            
            ping_count = 0
            pong_count = 0
            
            @client.event
            def ping():
                nonlocal ping_count
                ping_count += 1
            
            @client.event
            def pong():
                nonlocal pong_count
                pong_count += 1
            
            auth_data = {'token': 'dev-token'}
            
            try:
                client.connect(self.server_url, auth=auth_data, wait=True, wait_timeout=10)
                
                # Wait for some ping/pong cycles
                print("   Waiting for heartbeat activity...")
                time.sleep(5)
                
                if ping_count > 0 or pong_count > 0:
                    self.log_result("Ping/Pong", "PASS", f"Heartbeat active (ping: {ping_count}, pong: {pong_count})")
                else:
                    self.log_result("Ping/Pong", "WARN", "No heartbeat activity detected in 5 seconds")
                
                client.disconnect()
                
            except Exception as e:
                self.log_result("Ping/Pong", "FAIL", f"Heartbeat test error: {e}")
                
        except Exception as e:
            self.log_result("Ping/Pong", "FAIL", f"Test setup error: {e}")
    
    def analyze_results(self):
        """Analyze all test results and provide diagnostic summary."""
        print("\n" + "=" * 80)
        print("📊 CONNECTION & AUTHENTICATION DIAGNOSTIC SUMMARY")
        print("=" * 80)
        
        # Categorize results
        passed = [r for r in self.test_results if r['status'] == 'PASS']
        failed = [r for r in self.test_results if r['status'] == 'FAIL']
        warnings = [r for r in self.test_results if r['status'] == 'WARN']
        
        print(f"📈 TEST RESULTS:")
        print(f"   ✅ Passed: {len(passed)}")
        print(f"   ❌ Failed: {len(failed)}")
        print(f"   ⚠️  Warnings: {len(warnings)}")
        print(f"   📊 Total: {len(self.test_results)}")
        
        # Show failed tests
        if failed:
            print(f"\n❌ FAILED TESTS:")
            for test in failed:
                print(f"   • {test['test_name']}: {test['details']}")
        
        # Show warnings
        if warnings:
            print(f"\n⚠️  WARNINGS:")
            for test in warnings:
                print(f"   • {test['test_name']}: {test['details']}")
        
        # Overall assessment
        print(f"\n🔍 DIAGNOSTIC ASSESSMENT:")
        
        if len(failed) == 0:
            print("   ✅ All connection tests passed")
        else:
            print("   ❌ Some connection tests failed - check server configuration")
        
        # Specific diagnostics
        basic_conn = next((r for r in self.test_results if 'Basic Connection' in r['test_name']), None)
        if basic_conn and basic_conn['status'] == 'FAIL':
            print("   🚨 CRITICAL: Basic connection failing - server may not be running")
        
        valid_auth = next((r for r in self.test_results if 'Valid Auth' in r['test_name']), None)
        if valid_auth and valid_auth['status'] == 'FAIL':
            print("   🚨 CRITICAL: Valid authentication failing - check token configuration")
        
        namespace_tests = [r for r in self.test_results if 'Namespace Auth' in r['test_name']]
        failed_namespaces = [r for r in namespace_tests if r['status'] == 'FAIL']
        if failed_namespaces:
            print(f"   ⚠️  {len(failed_namespaces)} namespace(s) have connection issues")
        
        print(f"\n⏰ Diagnostic completed at: {datetime.now().isoformat()}")
        test_duration = (datetime.now() - self.test_start).total_seconds()
        print(f"🕒 Total diagnostic time: {test_duration:.2f} seconds")
    
    def run_all_tests(self):
        """Run all connection and authentication tests."""
        try:
            self.test_basic_connection()
            time.sleep(0.5)
            
            self.test_valid_authentication()
            time.sleep(0.5)
            
            self.test_invalid_authentication()
            time.sleep(0.5)
            
            self.test_namespace_authentication()
            time.sleep(0.5)
            
            self.test_connection_timeout()
            time.sleep(0.5)
            
            self.test_reconnection_behavior()
            time.sleep(0.5)
            
            self.test_multiple_namespace_connections()
            time.sleep(0.5)
            
            self.test_ping_pong_behavior()
            
            self.analyze_results()
            
            return len([r for r in self.test_results if r['status'] == 'FAIL']) == 0
            
        except KeyboardInterrupt:
            print("\n🛑 Diagnostic interrupted by user")
            return False
        except Exception as e:
            print(f"❌ Diagnostic error: {e}")
            import traceback
            traceback.print_exc()
            return False


def main():
    """Main diagnostic function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Socket.IO Connection & Authentication Diagnostic")
    parser.add_argument('--url', default='http://localhost:8765', help='Socket.IO server URL')
    args = parser.parse_args()
    
    diagnostic = ConnectionAuthDiagnostic(args.url)
    success = diagnostic.run_all_tests()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()