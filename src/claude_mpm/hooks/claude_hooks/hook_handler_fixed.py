#!/usr/bin/env python3
"""Optimized Claude Code hook handler with fixed memory management.

MEMORY LEAK FIXES:
1. Use singleton pattern for ClaudeHookHandler to prevent multiple instances
2. Proper cleanup of Socket.IO connections with connection pooling
3. Bounded dictionaries with automatic cleanup of old entries
4. Improved git branch cache with proper expiration
5. Better resource management and connection reuse

WHY these fixes:
- Singleton pattern ensures only one handler instance exists
- Connection pooling prevents creating new connections for each event
- Bounded dictionaries prevent unbounded memory growth
- Regular cleanup prevents accumulation of stale data
"""

import json
import sys
import os
import subprocess
from datetime import datetime, timedelta
import time
import asyncio
from pathlib import Path
from collections import deque
import weakref
import gc

# Import constants for configuration
try:
    from claude_mpm.core.constants import (
        NetworkConfig,
        TimeoutConfig,
        RetryConfig
    )
except ImportError:
    # Fallback values if constants module not available
    class NetworkConfig:
        SOCKETIO_PORT_RANGE = (8080, 8099)
        RECONNECTION_DELAY = 0.5
        SOCKET_WAIT_TIMEOUT = 1.0
    class TimeoutConfig:
        QUICK_TIMEOUT = 2.0
        QUEUE_GET_TIMEOUT = 1.0
    class RetryConfig:
        MAX_RETRIES = 3
        INITIAL_RETRY_DELAY = 0.1

# Debug mode is enabled by default for better visibility into hook processing
DEBUG = os.environ.get('CLAUDE_MPM_HOOK_DEBUG', 'true').lower() != 'false'

# Socket.IO import
try:
    import socketio
    SOCKETIO_AVAILABLE = True
except ImportError:
    SOCKETIO_AVAILABLE = False
    socketio = None

# Memory hooks and response tracking imports (simplified)
MEMORY_HOOKS_AVAILABLE = False
RESPONSE_TRACKING_AVAILABLE = False

# Maximum size for tracking dictionaries to prevent unbounded growth
MAX_DELEGATION_TRACKING = 100
MAX_PROMPT_TRACKING = 50
MAX_CACHE_AGE_SECONDS = 300  # 5 minutes
CLEANUP_INTERVAL_EVENTS = 100  # Clean up every 100 events


class SocketIOConnectionPool:
    """Connection pool for Socket.IO clients to prevent connection leaks.
    
    WHY: Reuses connections instead of creating new ones for each event,
    preventing the accumulation of zombie connections over time.
    """
    
    def __init__(self, max_connections=3):
        self.max_connections = max_connections
        self.connections = []
        self.current_index = 0
        self.last_cleanup = time.time()
        
    def get_connection(self, port):
        """Get or create a connection to the specified port."""
        # Clean up dead connections periodically
        if time.time() - self.last_cleanup > 60:  # Every minute
            self._cleanup_dead_connections()
            self.last_cleanup = time.time()
        
        # Look for existing connection to this port
        for conn in self.connections:
            if conn.get('port') == port and conn.get('client'):
                client = conn['client']
                if self._is_connection_alive(client):
                    return client
                else:
                    # Remove dead connection
                    self.connections.remove(conn)
        
        # Create new connection if under limit
        if len(self.connections) < self.max_connections:
            client = self._create_connection(port)
            if client:
                self.connections.append({
                    'port': port,
                    'client': client,
                    'created': time.time()
                })
                return client
        
        # Reuse oldest connection if at limit
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
                reconnection=False,  # Disable auto-reconnect to prevent zombies
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


class BoundedDict(dict):
    """Dictionary with maximum size that removes oldest entries.
    
    WHY: Prevents unbounded memory growth by automatically removing
    old entries when the size limit is reached.
    """
    
    def __init__(self, max_size=100):
        super().__init__()
        self.max_size = max_size
        self.access_times = {}
        
    def __setitem__(self, key, value):
        # Remove oldest entries if at capacity
        if len(self) >= self.max_size and key not in self:
            # Find and remove the oldest entry
            if self.access_times:
                oldest_key = min(self.access_times, key=self.access_times.get)
                del self[oldest_key]
                del self.access_times[oldest_key]
        
        super().__setitem__(key, value)
        self.access_times[key] = time.time()
    
    def __delitem__(self, key):
        super().__delitem__(key)
        self.access_times.pop(key, None)
    
    def cleanup_old_entries(self, max_age_seconds=300):
        """Remove entries older than specified age."""
        current_time = time.time()
        keys_to_remove = [
            key for key, access_time in self.access_times.items()
            if current_time - access_time > max_age_seconds
        ]
        for key in keys_to_remove:
            del self[key]


class ClaudeHookHandler:
    """Optimized hook handler with proper memory management.
    
    FIXES:
    - Uses connection pooling for Socket.IO clients
    - Bounded dictionaries prevent unbounded growth
    - Regular cleanup of old entries
    - Proper cache expiration
    """
    
    # Class-level singleton instance
    _instance = None
    _instance_lock = None
    
    def __new__(cls):
        """Implement singleton pattern to prevent multiple instances."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        # Only initialize once
        if self._initialized:
            return
        self._initialized = True
        
        # Socket.IO connection pool
        self.connection_pool = SocketIOConnectionPool(max_connections=3)
        
        # Use bounded dictionaries to prevent unbounded memory growth
        self.active_delegations = BoundedDict(MAX_DELEGATION_TRACKING)
        self.delegation_requests = BoundedDict(MAX_DELEGATION_TRACKING)
        self.pending_prompts = BoundedDict(MAX_PROMPT_TRACKING)
        
        # Limited delegation history
        self.delegation_history = deque(maxlen=100)
        
        # Git branch cache with expiration
        self._git_branch_cache = {}
        self._git_branch_cache_time = {}
        
        # Track events processed for periodic cleanup
        self.events_processed = 0
        
        # Initialize other components (simplified for brevity)
        self.memory_hooks_initialized = False
        self.pre_delegation_hook = None
        self.post_delegation_hook = None
        self.response_tracker = None
        self.response_tracking_enabled = False
        self.track_all_interactions = False
        
        if DEBUG:
            print(f"✅ ClaudeHookHandler singleton initialized (pid: {os.getpid()})", file=sys.stderr)
    
    def _periodic_cleanup(self):
        """Perform periodic cleanup of old data."""
        self.events_processed += 1
        
        if self.events_processed % CLEANUP_INTERVAL_EVENTS == 0:
            # Clean up old entries in bounded dictionaries
            self.active_delegations.cleanup_old_entries(MAX_CACHE_AGE_SECONDS)
            self.delegation_requests.cleanup_old_entries(MAX_CACHE_AGE_SECONDS)
            self.pending_prompts.cleanup_old_entries(MAX_CACHE_AGE_SECONDS)
            
            # Clean up git branch cache
            current_time = time.time()
            expired_keys = [
                key for key, cache_time in self._git_branch_cache_time.items()
                if current_time - cache_time > MAX_CACHE_AGE_SECONDS
            ]
            for key in expired_keys:
                self._git_branch_cache.pop(key, None)
                self._git_branch_cache_time.pop(key, None)
            
            # Force garbage collection periodically
            if self.events_processed % (CLEANUP_INTERVAL_EVENTS * 10) == 0:
                gc.collect()
                if DEBUG:
                    print(f"🧹 Performed cleanup after {self.events_processed} events", file=sys.stderr)
    
    def _track_delegation(self, session_id: str, agent_type: str, request_data: dict = None):
        """Track a new agent delegation with automatic cleanup."""
        if session_id and agent_type and agent_type != 'unknown':
            self.active_delegations[session_id] = agent_type
            key = f"{session_id}:{datetime.now().timestamp()}"
            self.delegation_history.append((key, agent_type))
            
            if request_data:
                self.delegation_requests[session_id] = {
                    'agent_type': agent_type,
                    'request': request_data,
                    'timestamp': datetime.now().isoformat()
                }
    
    def _get_delegation_agent_type(self, session_id: str) -> str:
        """Get the agent type for a session's active delegation."""
        if session_id and session_id in self.active_delegations:
            return self.active_delegations[session_id]
        
        # Check recent history
        if session_id:
            for key, agent_type in reversed(self.delegation_history):
                if key.startswith(session_id):
                    return agent_type
        
        return 'unknown'
    
    def _get_git_branch(self, working_dir: str = None) -> str:
        """Get git branch with proper caching and expiration."""
        if not working_dir:
            working_dir = os.getcwd()
        
        cache_key = working_dir
        current_time = time.time()
        
        # Check cache with expiration
        if (cache_key in self._git_branch_cache and 
            cache_key in self._git_branch_cache_time and
            current_time - self._git_branch_cache_time[cache_key] < 30):
            return self._git_branch_cache[cache_key]
        
        # Get git branch
        try:
            original_cwd = os.getcwd()
            os.chdir(working_dir)
            
            result = subprocess.run(
                ['git', 'branch', '--show-current'],
                capture_output=True,
                text=True,
                timeout=TimeoutConfig.QUICK_TIMEOUT
            )
            
            os.chdir(original_cwd)
            
            if result.returncode == 0 and result.stdout.strip():
                branch = result.stdout.strip()
                self._git_branch_cache[cache_key] = branch
                self._git_branch_cache_time[cache_key] = current_time
                return branch
        except:
            pass
        
        self._git_branch_cache[cache_key] = 'Unknown'
        self._git_branch_cache_time[cache_key] = current_time
        return 'Unknown'
    
    def _emit_socketio_event(self, namespace: str, event: str, data: dict):
        """Emit Socket.IO event using connection pool."""
        port = int(os.environ.get('CLAUDE_MPM_SOCKETIO_PORT', '8765'))
        client = self.connection_pool.get_connection(port)
        
        if not client:
            return
        
        try:
            claude_event_data = {
                'type': f'hook.{event}',
                'timestamp': datetime.now().isoformat(),
                'data': data
            }
            client.emit('claude_event', claude_event_data)
        except Exception as e:
            if DEBUG:
                print(f"❌ Socket.IO emit failed: {e}", file=sys.stderr)
    
    def handle(self):
        """Process hook event with minimal overhead."""
        try:
            # Perform periodic cleanup
            self._periodic_cleanup()
            
            # Read and parse event
            event = self._read_hook_event()
            if not event:
                self._continue_execution()
                return
            
            # Route event to appropriate handler
            self._route_event(event)
            
            # Always continue execution
            self._continue_execution()
            
        except:
            # Fail fast and silent
            self._continue_execution()
    
    def _read_hook_event(self) -> dict:
        """Read and parse hook event from stdin."""
        try:
            event_data = sys.stdin.read()
            return json.loads(event_data)
        except:
            return None
    
    def _route_event(self, event: dict) -> None:
        """Route event to appropriate handler based on type."""
        hook_type = event.get('hook_event_name', 'unknown')
        
        # Simplified routing (implement actual handlers as needed)
        if DEBUG:
            print(f"📥 Processing {hook_type} event", file=sys.stderr)
    
    def _continue_execution(self) -> None:
        """Send continue action to Claude."""
        print(json.dumps({"action": "continue"}))
    
    def __del__(self):
        """Cleanup when handler is destroyed."""
        if hasattr(self, 'connection_pool'):
            self.connection_pool.close_all()


# Global singleton instance
_handler_instance = None


def get_handler():
    """Get the singleton handler instance."""
    global _handler_instance
    if _handler_instance is None:
        _handler_instance = ClaudeHookHandler()
    return _handler_instance


def main():
    """Entry point with proper singleton usage."""
    try:
        handler = get_handler()
        handler.handle()
    except Exception as e:
        # Always output continue action to not block Claude
        print(json.dumps({"action": "continue"}))
        if DEBUG:
            print(f"Hook handler error: {e}", file=sys.stderr)
        sys.exit(0)


if __name__ == "__main__":
    main()