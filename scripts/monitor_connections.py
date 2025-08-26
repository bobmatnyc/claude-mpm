#!/usr/bin/env python3
"""
Connection Monitor - tracks dashboard connection health from server side
"""
import sys
import time
import requests
import subprocess
sys.path.insert(0, 'src')

def monitor_server():
    """Monitor the server for connection stability."""
    print("🔍 Monitoring Dashboard Server Health")
    print("====================================")
    
    start_time = time.time()
    test_duration = 30 * 60  # 30 minutes
    check_interval = 30  # 30 seconds
    
    checks = 0
    failures = 0
    
    while time.time() - start_time < test_duration:
        checks += 1
        current_time = time.strftime('%H:%M:%S')
        elapsed = int(time.time() - start_time)
        
        try:
            # Test if server is responding
            response = requests.get('http://localhost:8765/', timeout=5)
            if response.status_code == 200:
                print(f"[{current_time}] ✅ Server healthy (check {checks}, elapsed: {elapsed//60}m{elapsed%60}s)")
            else:
                print(f"[{current_time}] ⚠️ Server returned {response.status_code}")
                failures += 1
                
        except requests.exceptions.RequestException as e:
            print(f"[{current_time}] ❌ Server check failed: {e}")
            failures += 1
        
        # Show current port status
        try:
            result = subprocess.run(['netstat', '-an'], capture_output=True, text=True)
            port_8765_lines = [line for line in result.stdout.split('\n') if '8765' in line and 'LISTEN' in line]
            if port_8765_lines:
                print(f"[{current_time}] 📡 Port 8765 listening: {len(port_8765_lines)} sockets")
            else:
                print(f"[{current_time}] ❌ Port 8765 not listening!")
                failures += 1
        except Exception as e:
            print(f"[{current_time}] ⚠️ Could not check port status: {e}")
        
        print()
        time.sleep(check_interval)
    
    # Final report
    print("\n" + "="*50)
    print("📊 30-MINUTE STABILITY TEST RESULTS")
    print("="*50)
    print(f"Total checks: {checks}")
    print(f"Failures: {failures}")
    print(f"Success rate: {((checks-failures)/checks*100):.1f}%")
    print(f"Server uptime verified: {test_duration//60} minutes")
    
    if failures == 0:
        print("✅ Perfect stability - no failures detected!")
    else:
        print(f"⚠️ {failures} failures detected during testing")

if __name__ == "__main__":
    try:
        monitor_server()
    except KeyboardInterrupt:
        print("\n⚠️ Test interrupted by user")