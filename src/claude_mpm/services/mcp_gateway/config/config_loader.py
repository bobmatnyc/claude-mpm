"""
MCP Gateway Configuration Loader
================================

Handles loading and discovery of MCP configuration files.

Part of ISS-0034: Infrastructure Setup - MCP Gateway Project Foundation
"""

import os
from pathlib import Path
from typing import Optional, List
import yaml

from claude_mpm.core.logger import get_logger


class MCPConfigLoader:
    """
    Configuration loader for MCP Gateway.
    
    This class handles discovering and loading configuration files from
    standard locations, supporting both user and system configurations.
    
    WHY: We separate configuration loading from the main configuration
    service to support multiple configuration sources and provide a clean
    abstraction for configuration discovery.
    """
    
    # Standard configuration file search paths
    CONFIG_SEARCH_PATHS = [
        # User-specific configurations
        Path("~/.claude/mcp/config.yaml"),
        Path("~/.claude/mcp_gateway.yaml"),
        Path("~/.config/claude-mpm/mcp_gateway.yaml"),
        
        # Project-specific configurations
        Path("./mcp_gateway.yaml"),
        Path("./config/mcp_gateway.yaml"),
        Path("./.claude/mcp_gateway.yaml"),
        
        # System-wide configurations
        Path("/etc/claude-mpm/mcp_gateway.yaml"),
    ]
    
    def __init__(self):
        """Initialize configuration loader."""
        self.logger = get_logger("MCPConfigLoader")
    
    def find_config_file(self) -> Optional[Path]:
        """
        Find the first available configuration file.
        
        Searches through standard locations and returns the first
        existing configuration file.
        
        Returns:
            Path to configuration file if found, None otherwise
        """
        for config_path in self.CONFIG_SEARCH_PATHS:
            expanded_path = config_path.expanduser()
            if expanded_path.exists() and expanded_path.is_file():
                self.logger.info(f"Found configuration file: {expanded_path}")
                return expanded_path
        
        self.logger.debug("No configuration file found in standard locations")
        return None
    
    def load_from_file(self, config_path: Path) -> Optional[dict]:
        """
        Load configuration from a specific file.
        
        Args:
            config_path: Path to configuration file
            
        Returns:
            Configuration dictionary if successful, None otherwise
        """
        try:
            expanded_path = config_path.expanduser()
            
            if not expanded_path.exists():
                self.logger.error(f"Configuration file not found: {expanded_path}")
                return None
            
            with open(expanded_path, 'r') as f:
                config = yaml.safe_load(f)
            
            self.logger.info(f"Configuration loaded from {expanded_path}")
            return config or {}
            
        except yaml.YAMLError as e:
            self.logger.error(f"Failed to parse YAML configuration: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")
            return None
    
    def load_from_env(self) -> dict:
        """
        Load configuration from environment variables.
        
        Environment variables follow the pattern: MCP_GATEWAY_<SECTION>_<KEY>
        
        Returns:
            Configuration dictionary built from environment variables
        """
        config = {}
        prefix = "MCP_GATEWAY_"
        
        for env_key, env_value in os.environ.items():
            if not env_key.startswith(prefix):
                continue
            
            # Parse environment variable into configuration path
            config_path = env_key[len(prefix):].lower().split('_')
            
            # Build nested configuration structure
            current = config
            for part in config_path[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]
            
            # Set the value
            key = config_path[-1]
            try:
                # Try to parse as JSON for complex types
                import json
                current[key] = json.loads(env_value)
            except:
                # Fall back to string value
                current[key] = env_value
            
            self.logger.debug(f"Loaded from environment: {env_key}")
        
        return config
    
    def load(self, config_path: Optional[Path] = None) -> dict:
        """
        Load configuration from all sources.
        
        Loads configuration in the following priority order:
        1. Default configuration
        2. File configuration (if found or specified)
        3. Environment variable overrides
        
        Args:
            config_path: Optional specific configuration file path
            
        Returns:
            Merged configuration dictionary
        """
        from .configuration import MCPConfiguration
        
        # Start with defaults
        config = MCPConfiguration.DEFAULT_CONFIG.copy()
        
        # Load from file
        file_path = config_path or self.find_config_file()
        if file_path:
            file_config = self.load_from_file(file_path)
            if file_config:
                config = self._merge_configs(config, file_config)
        
        # Apply environment overrides
        env_config = self.load_from_env()
        if env_config:
            config = self._merge_configs(config, env_config)
        
        return config
    
    def _merge_configs(self, base: dict, overlay: dict) -> dict:
        """
        Recursively merge two configuration dictionaries.
        
        Args:
            base: Base configuration
            overlay: Configuration to merge in
            
        Returns:
            Merged configuration
        """
        result = base.copy()
        
        for key, value in overlay.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def create_default_config(self, path: Path) -> bool:
        """
        Create a default configuration file.
        
        Args:
            path: Path where to create the configuration file
            
        Returns:
            True if file created successfully
        """
        from .configuration import MCPConfiguration
        
        try:
            expanded_path = path.expanduser()
            expanded_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(expanded_path, 'w') as f:
                yaml.dump(
                    MCPConfiguration.DEFAULT_CONFIG,
                    f,
                    default_flow_style=False,
                    sort_keys=True
                )
            
            self.logger.info(f"Created default configuration at {expanded_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create default configuration: {e}")
            return False
    
    def list_config_locations(self) -> List[str]:
        """
        List all configuration file search locations.
        
        Returns:
            List of configuration file paths (as strings)
        """
        return [str(path.expanduser()) for path in self.CONFIG_SEARCH_PATHS]