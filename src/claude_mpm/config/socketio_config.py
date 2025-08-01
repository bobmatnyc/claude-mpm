"""Socket.IO server configuration for different deployment scenarios.

This module provides configuration management for Socket.IO servers
across different deployment environments and installation methods.

WHY configuration management:
- Enables different settings for development vs production
- Supports multiple deployment scenarios (local, PyPI, Docker, etc.)
- Provides environment-specific defaults
- Allows runtime configuration overrides
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, List, Optional


@dataclass
class SocketIOConfig:
    """Configuration for Socket.IO server instances."""
    
    # Server settings
    host: str = "localhost"
    port: int = 8765
    server_id: Optional[str] = None
    
    # Connection settings
    cors_allowed_origins: str = "*"  # Configure properly for production
    ping_timeout: int = 60
    ping_interval: int = 25
    max_http_buffer_size: int = 1000000
    
    # Compatibility settings
    min_client_version: str = "0.7.0"
    max_history_size: int = 10000
    
    # Deployment settings
    deployment_mode: str = "auto"  # auto, standalone, embedded, client
    auto_start: bool = True
    persistent: bool = True
    
    # Logging settings
    log_level: str = "INFO"
    log_to_file: bool = False
    log_file_path: Optional[str] = None
    
    # Health monitoring
    health_check_interval: int = 30
    max_connection_attempts: int = 3
    reconnection_delay: int = 1
    
    @classmethod
    def from_env(cls) -> 'SocketIOConfig':
        """Create configuration from environment variables."""
        return cls(
            host=os.getenv('CLAUDE_MPM_SOCKETIO_HOST', 'localhost'),
            port=int(os.getenv('CLAUDE_MPM_SOCKETIO_PORT', '8765')),
            server_id=os.getenv('CLAUDE_MPM_SOCKETIO_SERVER_ID'),
            cors_allowed_origins=os.getenv('CLAUDE_MPM_SOCKETIO_CORS', '*'),
            ping_timeout=int(os.getenv('CLAUDE_MPM_SOCKETIO_PING_TIMEOUT', '60')),
            ping_interval=int(os.getenv('CLAUDE_MPM_SOCKETIO_PING_INTERVAL', '25')),
            deployment_mode=os.getenv('CLAUDE_MPM_SOCKETIO_MODE', 'auto'),
            auto_start=os.getenv('CLAUDE_MPM_SOCKETIO_AUTO_START', 'true').lower() == 'true',
            persistent=os.getenv('CLAUDE_MPM_SOCKETIO_PERSISTENT', 'true').lower() == 'true',
            log_level=os.getenv('CLAUDE_MPM_SOCKETIO_LOG_LEVEL', 'INFO'),
            max_history_size=int(os.getenv('CLAUDE_MPM_SOCKETIO_HISTORY_SIZE', '10000'))
        )
    
    @classmethod
    def for_development(cls) -> 'SocketIOConfig':
        """Configuration optimized for development."""
        return cls(
            host="localhost",
            port=8765,
            deployment_mode="auto",
            log_level="DEBUG",
            ping_timeout=30,
            ping_interval=10,
            max_history_size=5000
        )
    
    @classmethod
    def for_production(cls) -> 'SocketIOConfig':
        """Configuration optimized for production."""
        return cls(
            host="0.0.0.0",  # Bind to all interfaces in production
            port=8765,
            cors_allowed_origins="https://your-domain.com",  # Restrict CORS
            deployment_mode="standalone",
            persistent=True,
            log_level="INFO",
            log_to_file=True,
            log_file_path="/var/log/claude-mpm-socketio.log",
            ping_timeout=120,
            ping_interval=30,
            max_history_size=20000
        )
    
    @classmethod
    def for_docker(cls) -> 'SocketIOConfig':
        """Configuration optimized for Docker deployment."""
        return cls(
            host="0.0.0.0",
            port=8765,
            deployment_mode="standalone",
            persistent=True,
            log_level="INFO",
            ping_timeout=90,
            ping_interval=25,
            max_history_size=15000
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            'host': self.host,
            'port': self.port,
            'server_id': self.server_id,
            'cors_allowed_origins': self.cors_allowed_origins,
            'ping_timeout': self.ping_timeout,
            'ping_interval': self.ping_interval,
            'max_http_buffer_size': self.max_http_buffer_size,
            'min_client_version': self.min_client_version,
            'max_history_size': self.max_history_size,
            'deployment_mode': self.deployment_mode,
            'auto_start': self.auto_start,
            'persistent': self.persistent,
            'log_level': self.log_level,
            'log_to_file': self.log_to_file,
            'log_file_path': self.log_file_path,
            'health_check_interval': self.health_check_interval,
            'max_connection_attempts': self.max_connection_attempts,
            'reconnection_delay': self.reconnection_delay
        }


class ConfigManager:
    """Manages Socket.IO configuration across different environments."""
    
    def __init__(self):
        self.config_file_name = "socketio_config.json"
        self.config_search_paths = [
            Path.cwd() / self.config_file_name,  # Current directory
            Path.home() / ".claude-mpm" / self.config_file_name,  # User home
            Path("/etc/claude-mpm") / self.config_file_name,  # System config
        ]
    
    def detect_environment(self) -> str:
        """Detect the current deployment environment."""
        # Check for Docker
        if os.path.exists('/.dockerenv') or os.getenv('DOCKER_CONTAINER'):
            return "docker"
        
        # Check for production indicators
        if os.getenv('ENVIRONMENT') == 'production' or os.getenv('NODE_ENV') == 'production':
            return "production"
        
        # Check if running from installed package
        try:
            import claude_mpm
            pkg_path = Path(claude_mpm.__file__).parent
            if 'site-packages' in str(pkg_path) or 'dist-packages' in str(pkg_path):
                return "installed"
        except ImportError:
            pass
        
        # Default to development
        return "development"
    
    def get_config(self, environment: str = None) -> SocketIOConfig:
        """Get configuration for the specified environment."""
        if environment is None:
            environment = self.detect_environment()
        
        # Start with environment-specific defaults
        if environment == "production":
            config = SocketIOConfig.for_production()
        elif environment == "docker":
            config = SocketIOConfig.for_docker()
        elif environment == "development":
            config = SocketIOConfig.for_development()
        else:
            config = SocketIOConfig()
        
        # Override with environment variables
        env_config = SocketIOConfig.from_env()
        for field in config.__dataclass_fields__:
            env_value = getattr(env_config, field)
            if env_value != getattr(SocketIOConfig(), field):  # Only if different from default
                setattr(config, field, env_value)
        
        # Override with config file if available
        config_file_data = self._load_config_file()
        if config_file_data:
            for key, value in config_file_data.items():
                if hasattr(config, key):
                    setattr(config, key, value)
        
        return config
    
    def _load_config_file(self) -> Optional[Dict[str, Any]]:
        """Load configuration from file if available."""
        import json
        
        for config_path in self.config_search_paths:
            if config_path.exists():
                try:
                    with open(config_path, 'r') as f:
                        return json.load(f)
                except Exception as e:
                    print(f"Warning: Failed to load config from {config_path}: {e}")
        
        return None
    
    def save_config(self, config: SocketIOConfig, path: str = None) -> bool:
        """Save configuration to file."""
        import json
        
        if path is None:
            # Use user config directory
            config_dir = Path.home() / ".claude-mpm"
            config_dir.mkdir(exist_ok=True)
            path = config_dir / self.config_file_name
        
        try:
            with open(path, 'w') as f:
                json.dump(config.to_dict(), f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving config to {path}: {e}")
            return False


# Global configuration manager instance
_config_manager = ConfigManager()


def get_config(environment: str = None) -> SocketIOConfig:
    """Get Socket.IO configuration for the current or specified environment."""
    return _config_manager.get_config(environment)


def get_server_ports(config: SocketIOConfig) -> List[int]:
    """Get list of ports to try for server discovery."""
    base_port = config.port
    return [base_port, base_port + 1, base_port + 2, base_port + 3, base_port + 4]


def get_discovery_hosts(config: SocketIOConfig) -> List[str]:
    """Get list of hosts to try for server discovery."""
    if config.host == "0.0.0.0":
        # If server binds to all interfaces, try localhost and 127.0.0.1 for discovery
        return ["localhost", "127.0.0.1"]
    else:
        return [config.host, "localhost", "127.0.0.1"]