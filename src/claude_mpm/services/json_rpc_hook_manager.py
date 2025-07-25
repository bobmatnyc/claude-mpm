"""JSON-RPC based hook manager that replaces the HTTP service."""

from pathlib import Path
from typing import Optional, Dict, Any

from ..hooks.json_rpc_hook_client import JSONRPCHookClient
from ..core.logger import get_logger


class JSONRPCHookManager:
    """Manager for JSON-RPC based hooks (no HTTP server required)."""
    
    def __init__(self, log_dir: Optional[Path] = None):
        """Initialize JSON-RPC hook manager.
        
        Args:
            log_dir: Log directory (unused but kept for compatibility)
        """
        self.logger = get_logger(self.__class__.__name__)
        self.log_dir = log_dir
        self.client = None
        self._available = False
        
    def start_service(self) -> bool:
        """Initialize the JSON-RPC hook client.
        
        Returns:
            True if initialization successful
        """
        try:
            self.client = JSONRPCHookClient()
            health = self.client.health_check()
            
            if health['status'] == 'healthy':
                self._available = True
                self.logger.info(f"JSON-RPC hook client initialized with {health['hook_count']} hooks")
                return True
            else:
                self.logger.warning(f"JSON-RPC hook client unhealthy: {health.get('error', 'Unknown error')}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to initialize JSON-RPC hook client: {e}")
            return False
            
    def stop_service(self):
        """Stop the hook service (no-op for JSON-RPC)."""
        self._available = False
        self.client = None
        self.logger.info("JSON-RPC hook client stopped")
        
    def is_available(self) -> bool:
        """Check if hook service is available.
        
        Returns:
            True if available
        """
        return self._available and self.client is not None
        
    def get_service_info(self) -> Dict[str, Any]:
        """Get service information.
        
        Returns:
            Service info dictionary
        """
        if not self.is_available():
            return {
                'running': False,
                'type': 'json-rpc'
            }
            
        health = self.client.health_check()
        return {
            'running': True,
            'type': 'json-rpc',
            'hook_count': health.get('hook_count', 0),
            'discovered_hooks': health.get('discovered_hooks', [])
        }
        
    def get_client(self) -> Optional[JSONRPCHookClient]:
        """Get the hook client instance.
        
        Returns:
            Hook client if available, None otherwise
        """
        return self.client if self.is_available() else None
        
    # Compatibility properties for HTTP service
    @property
    def port(self) -> Optional[int]:
        """Compatibility property - always returns None for JSON-RPC."""
        return None