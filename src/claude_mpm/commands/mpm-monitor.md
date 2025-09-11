---
description: Control the Claude MPM monitor daemon
argument-hint: start|stop|status|restart
---

# Claude MPM Monitor Control

I'll help you control the Claude MPM monitor daemon for real-time event tracking and visualization.

Based on your request: "$ARGUMENTS"

```python
import subprocess
import requests
import time
import sys
import os

def check_monitor_status():
    """Check if monitor is running"""
    try:
        response = requests.get('http://localhost:8765/health', timeout=2)
        return response.status_code == 200
    except:
        return False

def execute_monitor_command(command):
    """Execute monitor command and handle output"""
    if command == "start":
        if check_monitor_status():
            print("✅ Monitor is already running at http://localhost:8765")
            return True
        
        print("🚀 Starting Claude MPM monitor daemon...")
        result = subprocess.run(
            [sys.executable, "-m", "claude_mpm.cli.main", "monitor", "start"],
            capture_output=True,
            text=True,
            cwd=os.path.expanduser("~/Projects/claude-mpm")
        )
        
        if result.returncode == 0:
            # Give it a moment to start
            time.sleep(2)
            if check_monitor_status():
                print("✅ Monitor started successfully!")
                print("📊 Dashboard available at: http://localhost:8765")
                print("🔍 WebSocket events at: ws://localhost:8765/ws")
                return True
            else:
                print("⚠️ Monitor started but health check failed")
                print("Debug output:", result.stdout)
                return False
        else:
            print("❌ Failed to start monitor")
            print("Error:", result.stderr)
            return False
    
    elif command == "stop":
        if not check_monitor_status():
            print("ℹ️ Monitor is not running")
            return True
        
        print("🛑 Stopping Claude MPM monitor daemon...")
        result = subprocess.run(
            [sys.executable, "-m", "claude_mpm.cli.main", "monitor", "stop"],
            capture_output=True,
            text=True,
            cwd=os.path.expanduser("~/Projects/claude-mpm")
        )
        
        if result.returncode == 0:
            print("✅ Monitor stopped successfully")
            return True
        else:
            print("❌ Failed to stop monitor")
            print("Error:", result.stderr)
            return False
    
    elif command == "status":
        if check_monitor_status():
            print("✅ Monitor is running")
            print("📊 Dashboard: http://localhost:8765")
            print("🔍 WebSocket: ws://localhost:8765/ws")
            print("💚 Health check: http://localhost:8765/health")
            
            # Try to get more info
            try:
                response = requests.get('http://localhost:8765/api/stats', timeout=2)
                if response.status_code == 200:
                    stats = response.json()
                    print(f"📈 Statistics:")
                    print(f"   - Connected clients: {stats.get('connected_clients', 0)}")
                    print(f"   - Total events: {stats.get('total_events', 0)}")
                    print(f"   - Uptime: {stats.get('uptime', 'N/A')}")
            except:
                pass
        else:
            print("❌ Monitor is not running")
            print("Run '/mpm-monitor start' to start the monitor")
        return True
    
    elif command == "restart":
        print("🔄 Restarting Claude MPM monitor daemon...")
        
        # Stop if running
        if check_monitor_status():
            print("Stopping current instance...")
            subprocess.run(
                [sys.executable, "-m", "claude_mpm.cli.main", "monitor", "stop"],
                capture_output=True,
                text=True,
                cwd=os.path.expanduser("~/Projects/claude-mpm")
            )
            time.sleep(2)
        
        # Start fresh
        print("Starting new instance...")
        result = subprocess.run(
            [sys.executable, "-m", "claude_mpm.cli.main", "monitor", "start"],
            capture_output=True,
            text=True,
            cwd=os.path.expanduser("~/Projects/claude-mpm")
        )
        
        if result.returncode == 0:
            time.sleep(2)
            if check_monitor_status():
                print("✅ Monitor restarted successfully!")
                print("📊 Dashboard available at: http://localhost:8765")
                return True
        
        print("❌ Failed to restart monitor")
        return False
    
    else:
        # Show usage
        print("📋 Claude MPM Monitor Control")
        print("\nUsage: /mpm-monitor [command]")
        print("\nAvailable commands:")
        print("  start    - Start the monitor daemon")
        print("  stop     - Stop the monitor daemon")
        print("  status   - Check monitor status")
        print("  restart  - Restart the monitor daemon")
        print("\nExample: /mpm-monitor start")
        return True

# Parse arguments
args = "$ARGUMENTS".strip().lower() if "$ARGUMENTS" else ""

# Execute command
execute_monitor_command(args if args else None)
```

## What the Monitor Provides

The Claude MPM monitor provides real-time visualization and tracking of:

- **Event Stream**: Live WebSocket feed of all MPM events
- **Dashboard**: Web-based interface for monitoring agent activities
- **Statistics**: Track event counts, performance metrics, and system health
- **Browser Monitoring**: Capture and analyze browser console logs
- **Agent Activities**: Monitor agent deployments, tool usage, and responses

## Troubleshooting

If the monitor fails to start:
1. Check if port 8765 is already in use
2. Ensure you have proper permissions
3. Check the logs in `.claude-mpm/logs/monitor.log`
4. Try running with `--debug` flag for more output

## Related Commands

- `/mpm-browser-monitor` - Control browser console monitoring
- `/mpm-stats` - View detailed statistics
- `/mpm-logs` - Access system logs