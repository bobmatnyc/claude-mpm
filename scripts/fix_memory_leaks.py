#!/usr/bin/env python3
"""
Fix memory leaks in claude-mpm by applying optimizations to prevent unbounded memory growth.

This script addresses the following memory leak issues:
1. Socket.IO client connections not being properly cleaned up
2. Unbounded dictionaries accumulating data over time
3. Git branch cache without proper expiration
4. Multiple handler instances being created

Run this script to apply the memory leak fixes to your claude-mpm installation.
"""

import os
import sys
import shutil
from pathlib import Path
import subprocess
import json


def find_claude_mpm_root():
    """Find the claude-mpm project root directory."""
    current = Path(__file__).parent.parent
    if (current / 'src' / 'claude_mpm').exists():
        return current
    return None


def backup_file(file_path):
    """Create a backup of the original file."""
    backup_path = file_path.with_suffix(file_path.suffix + '.backup')
    if not backup_path.exists():
        shutil.copy2(file_path, backup_path)
        print(f"✅ Created backup: {backup_path}")
        return backup_path
    else:
        print(f"ℹ️  Backup already exists: {backup_path}")
        return backup_path


def apply_hook_handler_fix(root_dir):
    """Apply the memory leak fix to the hook handler."""
    hook_handler_path = root_dir / 'src' / 'claude_mpm' / 'hooks' / 'claude_hooks' / 'hook_handler.py'
    
    if not hook_handler_path.exists():
        print(f"❌ Hook handler not found at {hook_handler_path}")
        return False
    
    print(f"\n📝 Fixing hook handler memory leaks...")
    
    # Backup the original file
    backup_file(hook_handler_path)
    
    # Read the original file
    with open(hook_handler_path, 'r') as f:
        content = f.read()
    
    # Apply fixes
    fixes_applied = []
    
    # Fix 1: Add connection pooling class
    if 'class SocketIOConnectionPool' not in content:
        # Add the connection pool class after imports
        pool_code = '''
class SocketIOConnectionPool:
    """Connection pool for Socket.IO clients to prevent connection leaks."""
    
    def __init__(self, max_connections=3):
        self.max_connections = max_connections
        self.connections = []
        self.last_cleanup = time.time()
        
    def get_connection(self, port):
        """Get or create a connection to the specified port."""
        if time.time() - self.last_cleanup > 60:
            self._cleanup_dead_connections()
            self.last_cleanup = time.time()
        
        for conn in self.connections:
            if conn.get('port') == port and conn.get('client'):
                client = conn['client']
                if self._is_connection_alive(client):
                    return client
                else:
                    self.connections.remove(conn)
        
        if len(self.connections) < self.max_connections:
            client = self._create_connection(port)
            if client:
                self.connections.append({
                    'port': port,
                    'client': client,
                    'created': time.time()
                })
                return client
        
        if self.connections:
            oldest = min(self.connections, key=lambda x: x['created'])
            self._close_connection(oldest['client'])
            oldest['client'] = self._create_connection(port)
            oldest['port'] = port
            oldest['created'] = time.time()
            return oldest['client']
        
        return None
    
    def _create_connection(self, port):
        """Create a new Socket.IO connection."""
        if not SOCKETIO_AVAILABLE:
            return None
        try:
            client = socketio.Client(
                reconnection=False,  # Disable auto-reconnect
                logger=False,
                engineio_logger=False
            )
            client.connect(f'http://localhost:{port}', 
                          wait=True, 
                          wait_timeout=NetworkConfig.SOCKET_WAIT_TIMEOUT)
            if client.connected:
                return client
        except Exception:
            pass
        return None
    
    def _is_connection_alive(self, client):
        """Check if a connection is still alive."""
        try:
            return client and client.connected
        except:
            return False
    
    def _close_connection(self, client):
        """Safely close a connection."""
        try:
            if client:
                client.disconnect()
        except:
            pass
    
    def _cleanup_dead_connections(self):
        """Remove dead connections from the pool."""
        self.connections = [
            conn for conn in self.connections 
            if self._is_connection_alive(conn.get('client'))
        ]
    
    def close_all(self):
        """Close all connections in the pool."""
        for conn in self.connections:
            self._close_connection(conn.get('client'))
        self.connections.clear()


# Global singleton handler instance
_global_handler = None
_handler_lock = threading.Lock()

'''
        # Find where to insert the pool class
        insert_pos = content.find('class ClaudeHookHandler:')
        if insert_pos > 0:
            content = content[:insert_pos] + pool_code + '\n' + content[insert_pos:]
            fixes_applied.append("Added SocketIOConnectionPool class")
    
    # Fix 2: Replace sio_client with connection_pool in __init__
    if 'self.sio_client = None' in content:
        content = content.replace(
            'self.sio_client = None\n        self.sio_connected = False',
            'self.connection_pool = SocketIOConnectionPool(max_connections=3)'
        )
        fixes_applied.append("Replaced sio_client with connection_pool")
    
    # Fix 3: Add cleanup tracking
    if 'self.events_processed = 0' not in content:
        # Add after connection_pool initialization
        init_additions = '''
        # Track events for periodic cleanup
        self.events_processed = 0
        self.last_cleanup = time.time()
        
        # Maximum sizes for tracking
        self.MAX_DELEGATION_TRACKING = 200
        self.MAX_PROMPT_TRACKING = 100
        self.MAX_CACHE_AGE_SECONDS = 300
        self.CLEANUP_INTERVAL_EVENTS = 100
'''
        content = content.replace(
            'self.connection_pool = SocketIOConnectionPool(max_connections=3)',
            'self.connection_pool = SocketIOConnectionPool(max_connections=3)' + init_additions
        )
        fixes_applied.append("Added cleanup tracking variables")
    
    # Fix 4: Add cleanup method
    if 'def _cleanup_old_entries(self):' not in content:
        cleanup_method = '''
    def _cleanup_old_entries(self):
        """Clean up old entries to prevent memory growth."""
        cutoff_time = datetime.now().timestamp() - self.MAX_CACHE_AGE_SECONDS
        
        # Clean up delegation tracking dictionaries
        for storage in [self.active_delegations, self.delegation_requests]:
            if len(storage) > self.MAX_DELEGATION_TRACKING:
                # Keep only the most recent entries
                sorted_keys = sorted(storage.keys())
                excess = len(storage) - self.MAX_DELEGATION_TRACKING
                for key in sorted_keys[:excess]:
                    del storage[key]
        
        # Clean up pending prompts
        if len(self.pending_prompts) > self.MAX_PROMPT_TRACKING:
            sorted_keys = sorted(self.pending_prompts.keys())
            excess = len(self.pending_prompts) - self.MAX_PROMPT_TRACKING
            for key in sorted_keys[:excess]:
                del self.pending_prompts[key]
        
        # Clean up git branch cache
        expired_keys = [
            key for key, cache_time in self._git_branch_cache_time.items()
            if datetime.now().timestamp() - cache_time > self.MAX_CACHE_AGE_SECONDS
        ]
        for key in expired_keys:
            self._git_branch_cache.pop(key, None)
            self._git_branch_cache_time.pop(key, None)
'''
        # Insert after _track_delegation method
        pos = content.find('def _get_delegation_agent_type(self')
        if pos > 0:
            content = content[:pos] + cleanup_method + '\n    ' + content[pos:]
            fixes_applied.append("Added _cleanup_old_entries method")
    
    # Fix 5: Add periodic cleanup to handle method
    if 'self.events_processed' not in content or 'CLEANUP_INTERVAL_EVENTS' not in content:
        cleanup_code = '''
            # Increment event counter and perform periodic cleanup
            self.events_processed += 1
            if self.events_processed % self.CLEANUP_INTERVAL_EVENTS == 0:
                self._cleanup_old_entries()
                if DEBUG:
                    print(f"🧹 Performed cleanup after {self.events_processed} events", file=sys.stderr)
            
'''
        # Find handle method and add cleanup
        handle_pos = content.find('def handle(self):')
        if handle_pos > 0:
            # Find where to insert (after event reading)
            insert_after = 'if not event:'
            insert_pos = content.find(insert_after, handle_pos)
            if insert_pos > 0:
                # Find the end of the if block
                next_line_pos = content.find('\n', insert_pos)
                next_line_pos = content.find('\n', next_line_pos + 1)
                content = content[:next_line_pos] + '\n' + cleanup_code + content[next_line_pos:]
                fixes_applied.append("Added periodic cleanup to handle method")
    
    # Fix 6: Update _emit_socketio_event to use connection pool
    if '_get_socketio_client()' in content:
        content = content.replace(
            'client = self._get_socketio_client()',
            '''port = int(os.environ.get('CLAUDE_MPM_SOCKETIO_PORT', '8765'))
        client = self.connection_pool.get_connection(port)'''
        )
        fixes_applied.append("Updated _emit_socketio_event to use connection pool")
    
    # Fix 7: Update main() to use singleton pattern
    main_old = '''def main():
    """Entry point with comprehensive error handling."""
    try:
        handler = ClaudeHookHandler()
        handler.handle()'''
    
    main_new = '''def main():
    """Entry point with singleton pattern to prevent multiple instances."""
    global _global_handler
    
    try:
        # Use singleton pattern to prevent creating multiple instances
        with _handler_lock:
            if _global_handler is None:
                _global_handler = ClaudeHookHandler()
                if DEBUG:
                    print(f"✅ Created new ClaudeHookHandler singleton (pid: {os.getpid()})", file=sys.stderr)
            else:
                if DEBUG:
                    print(f"♻️ Reusing existing ClaudeHookHandler singleton (pid: {os.getpid()})", file=sys.stderr)
            
            handler = _global_handler
        
        handler.handle()'''
    
    if main_old in content:
        content = content.replace(main_old, main_new)
        fixes_applied.append("Updated main() to use singleton pattern")
    
    # Fix 8: Add import for threading if not present
    if 'import threading' not in content:
        content = content.replace(
            'from collections import deque',
            'from collections import deque\nimport threading'
        )
        fixes_applied.append("Added threading import")
    
    # Write the fixed content
    with open(hook_handler_path, 'w') as f:
        f.write(content)
    
    print(f"✅ Applied {len(fixes_applied)} fixes to hook handler:")
    for fix in fixes_applied:
        print(f"   - {fix}")
    
    return True


def add_memory_monitoring_config(root_dir):
    """Add memory monitoring configuration."""
    config_dir = root_dir / '.claude-mpm'
    config_dir.mkdir(exist_ok=True)
    
    monitoring_config = {
        "memory_monitoring": {
            "enabled": True,
            "interval_seconds": 60,
            "alert_threshold_mb": 500,
            "auto_cleanup": True,
            "cleanup_interval_events": 100,
            "max_delegation_tracking": 200,
            "max_prompt_tracking": 100,
            "max_cache_age_seconds": 300
        },
        "socket_io": {
            "connection_pool": {
                "enabled": True,
                "max_connections": 3,
                "cleanup_interval_seconds": 60,
                "reconnection": False
            }
        }
    }
    
    config_file = config_dir / 'memory_config.yaml'
    
    # Write as YAML
    try:
        import yaml
        with open(config_file, 'w') as f:
            yaml.dump(monitoring_config, f, default_flow_style=False)
        print(f"✅ Created memory monitoring config: {config_file}")
    except ImportError:
        # Fallback to JSON if yaml not available
        config_file = config_dir / 'memory_config.json'
        with open(config_file, 'w') as f:
            json.dump(monitoring_config, f, indent=2)
        print(f"✅ Created memory monitoring config: {config_file}")
    
    return True


def create_memory_monitor_script(root_dir):
    """Create a script to monitor memory usage."""
    scripts_dir = root_dir / 'scripts'
    scripts_dir.mkdir(exist_ok=True)
    
    monitor_script = scripts_dir / 'monitor_memory.sh'
    
    script_content = '''#!/bin/bash

# Monitor memory usage of claude-mpm processes

echo "🔍 Monitoring claude-mpm memory usage..."
echo "Press Ctrl+C to stop"
echo ""

while true; do
    clear
    echo "=== Claude MPM Memory Usage ==="
    echo "Time: $(date)"
    echo ""
    
    # Find all Python processes related to claude-mpm
    ps aux | grep -E "(claude[-_]mpm|hook_handler)" | grep -v grep | while read line; do
        PID=$(echo $line | awk '{print $2}')
        RSS_KB=$(echo $line | awk '{print $6}')
        RSS_MB=$((RSS_KB / 1024))
        CMD=$(echo $line | awk '{for(i=11;i<=NF;i++) printf "%s ", $i}')
        
        echo "PID: $PID | Memory: ${RSS_MB}MB | Command: ${CMD:0:80}"
    done
    
    echo ""
    echo "Total Memory Used: $(ps aux | grep -E "(claude[-_]mpm|hook_handler)" | grep -v grep | awk '{sum+=$6} END {printf "%.1f MB", sum/1024}')"
    
    sleep 5
done
'''
    
    with open(monitor_script, 'w') as f:
        f.write(script_content)
    
    # Make executable
    monitor_script.chmod(0o755)
    
    print(f"✅ Created memory monitor script: {monitor_script}")
    return True


def main():
    """Main function to apply all memory leak fixes."""
    print("=" * 60)
    print("Claude MPM Memory Leak Fix Script")
    print("=" * 60)
    
    # Find project root
    root_dir = find_claude_mpm_root()
    if not root_dir:
        print("❌ Could not find claude-mpm project root")
        sys.exit(1)
    
    print(f"📁 Project root: {root_dir}")
    
    # Apply fixes
    success = True
    
    # Fix 1: Hook handler memory leaks
    if not apply_hook_handler_fix(root_dir):
        success = False
    
    # Fix 2: Add memory monitoring configuration
    if not add_memory_monitoring_config(root_dir):
        success = False
    
    # Fix 3: Create memory monitoring script
    if not create_memory_monitor_script(root_dir):
        success = False
    
    print("\n" + "=" * 60)
    if success:
        print("✅ All memory leak fixes applied successfully!")
        print("\nNext steps:")
        print("1. Restart claude-mpm for changes to take effect")
        print("2. Monitor memory usage with: ./scripts/monitor_memory.sh")
        print("3. Check logs for cleanup messages if DEBUG is enabled")
    else:
        print("⚠️  Some fixes could not be applied")
        print("Please check the error messages above")
    
    print("=" * 60)


if __name__ == "__main__":
    main()