---
description: Control browser console monitoring for Claude MPM
argument-hint: start|stop|status|logs|clear
---

# Claude MPM Browser Monitor Control

I'll help you control browser console monitoring to capture and analyze browser-side events and errors.

Based on your request: "$ARGUMENTS"

```python
import subprocess
import json
import time
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta

# Configuration
BROWSER_LOG_DIR = Path.home() / ".claude-mpm" / "logs" / "client"
CONFIG_FILE = Path.home() / ".claude-mpm" / "config" / "browser_monitor.json"

def ensure_directories():
    """Ensure required directories exist"""
    BROWSER_LOG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)

def load_config():
    """Load browser monitor configuration"""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            return json.load(f)
    return {"enabled": False, "sessions": [], "started_at": None}

def save_config(config):
    """Save browser monitor configuration"""
    ensure_directories()
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)

def execute_browser_monitor_command(command):
    """Execute browser monitor command"""
    
    if command == "start":
        config = load_config()
        if config["enabled"]:
            print("✅ Browser monitoring is already active")
            if config.get("started_at"):
                print(f"📅 Started at: {config['started_at']}")
            return True
        
        print("🎯 Starting browser console monitoring...")
        ensure_directories()
        
        # Update config
        config["enabled"] = True
        config["started_at"] = datetime.now().isoformat()
        save_config(config)
        
        # Create injection script for browser monitoring
        injection_script = BROWSER_LOG_DIR / "inject.js"
        with open(injection_script, "w") as f:
            f.write("""
// Claude MPM Browser Monitor Injection Script
(function() {
    const browserId = 'browser_' + Date.now();
    const logEndpoint = 'http://localhost:8765/api/browser-log';
    
    // Store original console methods
    const originalLog = console.log;
    const originalError = console.error;
    const originalWarn = console.warn;
    const originalInfo = console.info;
    const originalDebug = console.debug;
    
    function sendLog(level, args) {
        try {
            const message = Array.from(args).map(arg => {
                if (typeof arg === 'object') {
                    return JSON.stringify(arg);
                }
                return String(arg);
            }).join(' ');
            
            // Send to local monitor
            fetch(logEndpoint, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    browser_id: browserId,
                    timestamp: new Date().toISOString(),
                    level: level,
                    message: message,
                    url: window.location.href,
                    userAgent: navigator.userAgent
                })
            }).catch(() => {
                // Silently fail if monitor is not running
            });
            
            // Also save to local storage for persistence
            const logs = JSON.parse(localStorage.getItem('claude_mpm_logs') || '[]');
            logs.push({
                browser_id: browserId,
                timestamp: new Date().toISOString(),
                level: level,
                message: message
            });
            // Keep only last 1000 logs
            if (logs.length > 1000) {
                logs.shift();
            }
            localStorage.setItem('claude_mpm_logs', JSON.stringify(logs));
        } catch (e) {
            // Fail silently
        }
    }
    
    // Override console methods
    console.log = function(...args) {
        sendLog('INFO', args);
        return originalLog.apply(console, args);
    };
    
    console.error = function(...args) {
        sendLog('ERROR', args);
        return originalError.apply(console, args);
    };
    
    console.warn = function(...args) {
        sendLog('WARN', args);
        return originalWarn.apply(console, args);
    };
    
    console.info = function(...args) {
        sendLog('INFO', args);
        return originalInfo.apply(console, args);
    };
    
    console.debug = function(...args) {
        sendLog('DEBUG', args);
        return originalDebug.apply(console, args);
    };
    
    // Monitor window errors
    window.addEventListener('error', function(event) {
        sendLog('ERROR', [`Uncaught Error: ${event.message} at ${event.filename}:${event.lineno}:${event.colno}`]);
    });
    
    // Monitor unhandled promise rejections
    window.addEventListener('unhandledrejection', function(event) {
        sendLog('ERROR', [`Unhandled Promise Rejection: ${event.reason}`]);
    });
    
    console.info('[Claude MPM] Browser monitoring activated - ID: ' + browserId);
})();
            """)
        
        print("✅ Browser monitoring started successfully!")
        print(f"📁 Logs will be saved to: {BROWSER_LOG_DIR}")
        print("\n📝 To inject monitoring into a browser:")
        print("1. Open browser developer console")
        print(f"2. Copy and paste the script from: {injection_script}")
        print("3. Or use browser extension to auto-inject")
        return True
    
    elif command == "stop":
        config = load_config()
        if not config["enabled"]:
            print("ℹ️ Browser monitoring is not active")
            return True
        
        print("🛑 Stopping browser console monitoring...")
        config["enabled"] = False
        config["stopped_at"] = datetime.now().isoformat()
        save_config(config)
        
        print("✅ Browser monitoring stopped")
        print("Note: Existing browser sessions will continue logging until refreshed")
        return True
    
    elif command == "status":
        config = load_config()
        
        print("📊 Browser Monitor Status")
        print("-" * 40)
        
        if config["enabled"]:
            print("✅ Status: ACTIVE")
            if config.get("started_at"):
                print(f"📅 Started: {config['started_at']}")
        else:
            print("❌ Status: INACTIVE")
            if config.get("stopped_at"):
                print(f"📅 Stopped: {config['stopped_at']}")
        
        # Check for log files
        if BROWSER_LOG_DIR.exists():
            log_files = list(BROWSER_LOG_DIR.glob("*.log"))
            if log_files:
                print(f"\n📁 Log Files: {len(log_files)}")
                
                # Show recent sessions
                recent_files = sorted(log_files, key=lambda x: x.stat().st_mtime, reverse=True)[:5]
                if recent_files:
                    print("\n🕐 Recent Sessions:")
                    for f in recent_files:
                        size = f.stat().st_size
                        mtime = datetime.fromtimestamp(f.stat().st_mtime)
                        print(f"   - {f.name}: {size:,} bytes, {mtime.strftime('%Y-%m-%d %H:%M')}")
            else:
                print("\n📁 No log files found")
        
        # Check active sessions
        if config.get("sessions"):
            print(f"\n🌐 Active Sessions: {len(config['sessions'])}")
            for session in config["sessions"][-5:]:
                print(f"   - {session.get('browser_id', 'Unknown')}: {session.get('last_seen', 'Never')}")
        
        return True
    
    elif command == "logs":
        print("📋 Recent Browser Console Logs")
        print("-" * 40)
        
        if not BROWSER_LOG_DIR.exists():
            print("ℹ️ No log directory found")
            return True
        
        # Find recent log files
        log_files = sorted(BROWSER_LOG_DIR.glob("*.log"), key=lambda x: x.stat().st_mtime, reverse=True)
        
        if not log_files:
            print("ℹ️ No log files found")
            print("Run '/mpm-browser-monitor start' and inject the script into a browser")
            return True
        
        # Show logs from most recent file
        recent_file = log_files[0]
        print(f"\n📁 Showing logs from: {recent_file.name}")
        print(f"📅 Last modified: {datetime.fromtimestamp(recent_file.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')}")
        print("-" * 40)
        
        # Read last 50 lines
        try:
            with open(recent_file) as f:
                lines = f.readlines()
                
            # Parse and display last 20 entries
            for line in lines[-20:]:
                try:
                    entry = json.loads(line.strip())
                    timestamp = entry.get("timestamp", "")[:19]  # Trim to seconds
                    level = entry.get("level", "INFO")
                    message = entry.get("message", "")[:100]  # Truncate long messages
                    
                    # Color code by level
                    level_colors = {
                        "ERROR": "🔴",
                        "WARN": "🟡",
                        "INFO": "🔵",
                        "DEBUG": "⚪"
                    }
                    icon = level_colors.get(level, "⚫")
                    
                    print(f"{icon} [{timestamp}] {level:5} | {message}")
                except:
                    print(f"   {line.strip()[:100]}")
                    
        except Exception as e:
            print(f"❌ Error reading log file: {e}")
        
        print("\n💡 Tip: Use the dashboard at http://localhost:8765 for real-time log viewing")
        return True
    
    elif command == "clear":
        print("🧹 Clearing browser console logs...")
        
        if not BROWSER_LOG_DIR.exists():
            print("ℹ️ No log directory found")
            return True
        
        # Count files before clearing
        log_files = list(BROWSER_LOG_DIR.glob("*.log"))
        file_count = len(log_files)
        
        if file_count == 0:
            print("ℹ️ No log files to clear")
            return True
        
        # Calculate total size
        total_size = sum(f.stat().st_size for f in log_files)
        
        # Clear all log files
        for f in log_files:
            try:
                f.unlink()
            except Exception as e:
                print(f"⚠️ Failed to delete {f.name}: {e}")
        
        # Clear sessions from config
        config = load_config()
        config["sessions"] = []
        save_config(config)
        
        print(f"✅ Cleared {file_count} log files ({total_size:,} bytes)")
        return True
    
    else:
        # Show usage
        print("📋 Claude MPM Browser Monitor Control")
        print("\nUsage: /mpm-browser-monitor [command]")
        print("\nAvailable commands:")
        print("  start   - Start browser console monitoring")
        print("  stop    - Stop browser console monitoring")
        print("  status  - Show monitoring status and active sessions")
        print("  logs    - Display recent browser console logs")
        print("  clear   - Clear all browser console logs")
        print("\nExample: /mpm-browser-monitor start")
        print("\n💡 After starting, inject the monitoring script into your browser's console")
        print("   to begin capturing logs from that browser session.")
        return True

# Parse arguments
args = "$ARGUMENTS".strip().lower() if "$ARGUMENTS" else ""

# Execute command
execute_browser_monitor_command(args if args else None)
```

## What Browser Monitoring Provides

Browser console monitoring captures:

- **Console Logs**: All console.log, console.error, console.warn, console.info, console.debug calls
- **JavaScript Errors**: Uncaught exceptions and syntax errors
- **Promise Rejections**: Unhandled promise rejection events
- **Network Errors**: Failed resource loads and AJAX errors
- **Performance Metrics**: Page load times and resource timings

## How to Use

1. **Start Monitoring**: Run `/mpm-browser-monitor start`
2. **Inject Script**: Copy the generated script into your browser's console
3. **View Logs**: Check logs with `/mpm-browser-monitor logs` or use the dashboard
4. **Analyze**: Filter and search logs in the dashboard's Browser Monitor tab

## Integration with Dashboard

When the monitor is running (http://localhost:8765), the Browser Monitor Log tab provides:
- Real-time log streaming
- Color-coded log levels
- Filtering by browser ID and log level
- Export capabilities

## Troubleshooting

If logs are not appearing:
1. Ensure the monitor daemon is running (`/mpm-monitor status`)
2. Check that the injection script was properly executed in the browser
3. Verify browser allows console overrides (some extensions may block)
4. Check browser's security settings for localhost connections

## Related Commands

- `/mpm-monitor` - Control the main monitor daemon
- `/mpm-logs` - View system logs
- `/mpm-stats` - View monitoring statistics