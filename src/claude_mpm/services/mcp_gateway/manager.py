"""
MCP Gateway Manager
===================

Manages global MCP gateway instance to ensure single instance per installation.
Similar to hooks service singleton pattern but for MCP gateway coordination.
"""

import os
import sys
import json
import fcntl
import signal
import atexit
from pathlib import Path
from typing import Optional, Dict, Any
from threading import Lock
import tempfile

from claude_mpm.core.logger import get_logger
from .server.mcp_gateway import MCPGateway
from .registry.tool_registry import ToolRegistry
from .config.configuration import MCPConfiguration


class MCPGatewayManager:
    """
    Global MCP Gateway manager ensuring single instance per installation.
    
    WHY: Like the hooks service, we need to ensure only one MCP gateway
    runs per claude-mpm installation to avoid conflicts and resource issues.
    
    DESIGN DECISIONS:
    - Use file-based locking to coordinate across processes
    - Store instance metadata in global location
    - Respect existing running instances
    - Clean shutdown handling
    """
    
    _instance: Optional['MCPGatewayManager'] = None
    _lock = Lock()
    
    def __new__(cls):
        """Singleton pattern implementation."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance
    
    def __init__(self):
        """Initialize manager (only once due to singleton)."""
        if self._initialized:
            return
        self._initialized = True
        
        self.logger = get_logger(self.__class__.__name__)
        
        # Global state directory (similar to hooks)
        self.state_dir = Path.home() / ".claude-mpm" / "mcp"
        self.state_dir.mkdir(parents=True, exist_ok=True)
        
        # Instance tracking
        self.lock_file = self.state_dir / "gateway.lock"
        self.instance_file = self.state_dir / "gateway.json"
        self.lock_fd: Optional[int] = None
        
        # Gateway components
        self.gateway: Optional[MCPGateway] = None
        self.tool_registry: Optional[ToolRegistry] = None
        self.configuration: Optional[MCPConfiguration] = None
        
        # Setup cleanup
        atexit.register(self.cleanup)
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        self.logger.info(f"Received signal {signum}, shutting down gateway manager")
        self.cleanup()
        sys.exit(0)
    
    def acquire_lock(self) -> bool:
        """
        Acquire exclusive lock for gateway instance.
        
        Returns:
            True if lock acquired, False if another instance is running
        """
        try:
            # Open lock file
            self.lock_fd = os.open(self.lock_file, os.O_CREAT | os.O_WRONLY | os.O_TRUNC)
            
            # Try to acquire exclusive lock (non-blocking)
            fcntl.flock(self.lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            
            # Write our PID to the lock file
            os.write(self.lock_fd, str(os.getpid()).encode())
            os.fsync(self.lock_fd)
            
            self.logger.info(f"Acquired MCP gateway lock (PID: {os.getpid()})")
            return True
            
        except (OSError, IOError) as e:
            if self.lock_fd:
                try:
                    os.close(self.lock_fd)
                except:
                    pass
                self.lock_fd = None
            
            # Check if there's an existing instance
            existing_info = self.get_running_instance_info()
            if existing_info:
                self.logger.info(f"MCP gateway already running (PID: {existing_info.get('pid')})")
            else:
                self.logger.warning(f"Failed to acquire gateway lock: {e}")
            
            return False
    
    def release_lock(self):
        """Release the gateway lock."""
        if self.lock_fd:
            try:
                fcntl.flock(self.lock_fd, fcntl.LOCK_UN)
                os.close(self.lock_fd)
                self.lock_fd = None
                
                # Remove lock file
                if self.lock_file.exists():
                    self.lock_file.unlink()
                    
                self.logger.info("Released MCP gateway lock")
            except Exception as e:
                self.logger.warning(f"Error releasing lock: {e}")
    
    def get_running_instance_info(self) -> Optional[Dict[str, Any]]:
        """
        Get information about running gateway instance.
        
        Returns:
            Instance info dict or None if no instance running
        """
        try:
            if not self.instance_file.exists():
                return None
            
            with open(self.instance_file, 'r') as f:
                info = json.load(f)
            
            # Check if PID is still running
            pid = info.get('pid')
            if pid:
                try:
                    os.kill(pid, 0)  # Check if process exists
                    return info
                except ProcessLookupError:
                    # Process no longer exists, clean up stale file
                    self.instance_file.unlink()
                    return None
            
            return None
            
        except Exception as e:
            self.logger.debug(f"Error reading instance info: {e}")
            return None
    
    def save_instance_info(self):
        """Save current instance information."""
        try:
            info = {
                "pid": os.getpid(),
                "gateway_name": self.gateway.gateway_name if self.gateway else "unknown",
                "version": self.gateway.version if self.gateway else "unknown",
                "started_at": str(Path(__file__).stat().st_mtime),  # Approximate start time
                "tools_count": len(self.tool_registry.list_tools()) if self.tool_registry else 0
            }
            
            with open(self.instance_file, 'w') as f:
                json.dump(info, f, indent=2)
                
            self.logger.debug("Saved instance info")
            
        except Exception as e:
            self.logger.warning(f"Error saving instance info: {e}")
    
    async def start_gateway(self, gateway_name: str = "claude-mpm-mcp", version: str = "1.0.0") -> bool:
        """
        Start the MCP gateway if not already running.
        
        Args:
            gateway_name: Name for the gateway
            version: Gateway version
            
        Returns:
            True if gateway started or already running
        """
        # Check for existing instance
        existing_info = self.get_running_instance_info()
        if existing_info:
            self.logger.info(f"MCP gateway already running (PID: {existing_info['pid']})")
            return True
        
        # Try to acquire lock
        if not self.acquire_lock():
            return False
        
        try:
            # Initialize configuration
            self.configuration = MCPConfiguration()
            await self.configuration.initialize()
            
            # Initialize tool registry
            self.tool_registry = ToolRegistry()
            await self.tool_registry.initialize()
            
            # Load default tools
            await self._load_default_tools()
            
            # Create gateway
            self.gateway = MCPGateway(gateway_name=gateway_name, version=version)
            self.gateway.set_tool_registry(self.tool_registry)
            
            # Initialize gateway
            await self.gateway.initialize()
            
            # Save instance info
            self.save_instance_info()
            
            self.logger.info(f"MCP gateway started successfully (PID: {os.getpid()})")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start MCP gateway: {e}")
            self.cleanup()
            return False
    
    async def _load_default_tools(self):
        """Load default tools into registry."""
        try:
            from .tools.base_adapter import (
                EchoToolAdapter,
                CalculatorToolAdapter,
                SystemInfoToolAdapter
            )
            
            tools = [
                EchoToolAdapter(),
                CalculatorToolAdapter(),
                SystemInfoToolAdapter()
            ]
            
            for tool in tools:
                self.tool_registry.register_tool(tool, category="builtin")
                
            self.logger.info(f"Loaded {len(tools)} default tools")
            
        except Exception as e:
            self.logger.warning(f"Error loading default tools: {e}")
    
    async def run_gateway(self):
        """Run the gateway main loop."""
        if not self.gateway:
            raise RuntimeError("Gateway not initialized")
        
        try:
            await self.gateway.run()
        except Exception as e:
            self.logger.error(f"Gateway run error: {e}")
            raise
    
    def cleanup(self):
        """Clean up resources."""
        try:
            # Remove instance file
            if self.instance_file.exists():
                self.instance_file.unlink()
            
            # Release lock
            self.release_lock()
            
            self.logger.debug("Gateway manager cleanup complete")
            
        except Exception as e:
            self.logger.warning(f"Error during cleanup: {e}")


# Global manager instance
_gateway_manager: Optional[MCPGatewayManager] = None


def get_gateway_manager() -> MCPGatewayManager:
    """Get the global gateway manager instance."""
    global _gateway_manager
    if _gateway_manager is None:
        _gateway_manager = MCPGatewayManager()
    return _gateway_manager


async def start_global_gateway(gateway_name: str = "claude-mpm-mcp", version: str = "1.0.0") -> bool:
    """
    Start the global MCP gateway instance.
    
    Args:
        gateway_name: Name for the gateway
        version: Gateway version
        
    Returns:
        True if gateway started successfully
    """
    manager = get_gateway_manager()
    return await manager.start_gateway(gateway_name, version)


async def run_global_gateway():
    """Run the global MCP gateway."""
    manager = get_gateway_manager()
    await manager.run_gateway()


def get_gateway_status() -> Optional[Dict[str, Any]]:
    """Get status of running gateway instance."""
    manager = get_gateway_manager()
    return manager.get_running_instance_info()


def is_gateway_active() -> bool:
    """Check if gateway handler is currently active."""
    return get_gateway_status() is not None


# Backward compatibility alias
is_gateway_running = is_gateway_active
