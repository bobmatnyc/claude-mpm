# MCP Gateway Configuration Reference

## Overview

The MCP Gateway supports flexible configuration through multiple sources including YAML files, environment variables, and programmatic configuration. This document provides comprehensive configuration options and examples.

## Configuration Sources

Configuration is loaded in the following priority order (highest to lowest):

1. **Programmatic Configuration** - Passed directly to gateway constructor
2. **Environment Variables** - Runtime environment settings
3. **YAML Configuration File** - `.claude-mpm/mcp_config.yaml`
4. **Default Configuration** - Built-in sensible defaults

## Configuration File Format

### Basic Configuration

```yaml
# .claude-mpm/mcp_config.yaml
mcp:
  server:
    name: "claude-mpm-gateway"
    version: "1.0.0"
    description: "Claude MPM MCP Gateway"
  
  tools:
    enabled: true
    timeout: 30.0
    categories:
      - builtin
      - user
      - custom
  
  logging:
    level: "INFO"
    format: "structured"
    file: null
```

### Advanced Configuration

```yaml
mcp:
  server:
    name: "my-custom-gateway"
    version: "2.0.0"
    description: "Custom MCP Gateway"
    capabilities:
      tools: true
      resources: false
      prompts: false
  
  tools:
    enabled: true
    timeout: 60.0
    max_concurrent: 10
    categories:
      - builtin
      - user
      - custom
      - external
    
    # Tool-specific configuration
    builtin:
      echo:
        enabled: true
        max_message_length: 1000
      calculator:
        enabled: true
        precision: 10
      system_info:
        enabled: true
        allowed_info_types:
          - platform
          - python
          - memory
    
    # Custom tool configuration
    custom:
      weather:
        enabled: true
        api_key: "${WEATHER_API_KEY}"
        timeout: 15.0
      database:
        enabled: false
        connection_string: "${DB_CONNECTION_STRING}"
  
  performance:
    cache:
      enabled: true
      ttl: 300
      max_size: 1000
    
    monitoring:
      enabled: true
      metrics_interval: 60
      health_check_interval: 30
  
  logging:
    level: "INFO"
    format: "structured"
    file: "/var/log/claude-mpm/mcp-gateway.log"
    rotation:
      max_size: "10MB"
      backup_count: 5
    
    # Component-specific logging
    components:
      gateway: "INFO"
      registry: "DEBUG"
      tools: "INFO"
      performance: "WARNING"
  
  security:
    input_validation:
      strict: true
      max_parameter_size: 1048576  # 1MB
      allowed_types:
        - string
        - number
        - boolean
        - array
        - object
    
    rate_limiting:
      enabled: false
      requests_per_minute: 100
      burst_size: 10
```

## Environment Variables

### Server Configuration

```bash
# Server settings
export CLAUDE_MPM_MCP_SERVER_NAME="my-gateway"
export CLAUDE_MPM_MCP_SERVER_VERSION="1.0.0"
export CLAUDE_MPM_MCP_SERVER_DESCRIPTION="My Custom Gateway"

# Capabilities
export CLAUDE_MPM_MCP_CAPABILITIES_TOOLS="true"
export CLAUDE_MPM_MCP_CAPABILITIES_RESOURCES="false"
export CLAUDE_MPM_MCP_CAPABILITIES_PROMPTS="false"
```

### Tool Configuration

```bash
# Tool settings
export CLAUDE_MPM_MCP_TOOLS_ENABLED="true"
export CLAUDE_MPM_MCP_TOOLS_TIMEOUT="30.0"
export CLAUDE_MPM_MCP_TOOLS_MAX_CONCURRENT="5"
export CLAUDE_MPM_MCP_TOOLS_CATEGORIES="builtin,user,custom"

# Built-in tool settings
export CLAUDE_MPM_MCP_TOOL_ECHO_ENABLED="true"
export CLAUDE_MPM_MCP_TOOL_CALCULATOR_ENABLED="true"
export CLAUDE_MPM_MCP_TOOL_SYSTEM_INFO_ENABLED="true"

# Custom tool settings
export WEATHER_API_KEY="your-api-key-here"
export DB_CONNECTION_STRING="postgresql://user:pass@localhost/db"
```

### Performance Configuration

```bash
# Cache settings
export CLAUDE_MPM_MCP_CACHE_ENABLED="true"
export CLAUDE_MPM_MCP_CACHE_TTL="300"
export CLAUDE_MPM_MCP_CACHE_MAX_SIZE="1000"

# Monitoring settings
export CLAUDE_MPM_MCP_MONITORING_ENABLED="true"
export CLAUDE_MPM_MCP_METRICS_INTERVAL="60"
export CLAUDE_MPM_MCP_HEALTH_CHECK_INTERVAL="30"
```

### Logging Configuration

```bash
# Logging settings
export CLAUDE_MPM_MCP_LOG_LEVEL="INFO"
export CLAUDE_MPM_MCP_LOG_FORMAT="structured"
export CLAUDE_MPM_MCP_LOG_FILE="/var/log/claude-mpm/gateway.log"

# Component-specific logging
export CLAUDE_MPM_MCP_LOG_GATEWAY="INFO"
export CLAUDE_MPM_MCP_LOG_REGISTRY="DEBUG"
export CLAUDE_MPM_MCP_LOG_TOOLS="INFO"
```

## Programmatic Configuration

### Basic Programmatic Setup

```python
from claude_mpm.services.mcp_gateway.server.mcp_gateway import MCPGateway

config = {
    "server": {
        "name": "programmatic-gateway",
        "version": "1.0.0"
    },
    "tools": {
        "enabled": True,
        "timeout": 45.0,
        "categories": ["builtin", "custom"]
    },
    "logging": {
        "level": "DEBUG",
        "format": "json"
    }
}

gateway = MCPGateway(config)
```

### Advanced Programmatic Setup

```python
from claude_mpm.services.mcp_gateway.server.mcp_gateway import MCPGateway
from claude_mpm.services.mcp_gateway.registry.tool_registry import ToolRegistry

# Create custom configuration
config = {
    "server": {
        "name": "advanced-gateway",
        "version": "2.0.0",
        "capabilities": {
            "tools": True,
            "resources": False,
            "prompts": False
        }
    },
    "tools": {
        "enabled": True,
        "timeout": 60.0,
        "max_concurrent": 20,
        "categories": ["builtin", "user", "custom", "external"]
    },
    "performance": {
        "cache": {
            "enabled": True,
            "ttl": 600,
            "max_size": 2000
        },
        "monitoring": {
            "enabled": True,
            "metrics_interval": 30
        }
    },
    "security": {
        "input_validation": {
            "strict": True,
            "max_parameter_size": 2097152  # 2MB
        }
    }
}

# Initialize gateway with custom config
gateway = MCPGateway(config)

# Optionally customize tool registry
registry = ToolRegistry(config.get("tools", {}))
gateway.set_tool_registry(registry)
```

## Configuration Schema

### Server Configuration Schema

```json
{
  "type": "object",
  "properties": {
    "server": {
      "type": "object",
      "properties": {
        "name": {"type": "string", "default": "claude-mpm-gateway"},
        "version": {"type": "string", "default": "1.0.0"},
        "description": {"type": "string", "default": "Claude MPM MCP Gateway"},
        "capabilities": {
          "type": "object",
          "properties": {
            "tools": {"type": "boolean", "default": true},
            "resources": {"type": "boolean", "default": false},
            "prompts": {"type": "boolean", "default": false}
          }
        }
      }
    }
  }
}
```

### Tools Configuration Schema

```json
{
  "type": "object",
  "properties": {
    "tools": {
      "type": "object",
      "properties": {
        "enabled": {"type": "boolean", "default": true},
        "timeout": {"type": "number", "default": 30.0, "minimum": 1.0},
        "max_concurrent": {"type": "integer", "default": 5, "minimum": 1},
        "categories": {
          "type": "array",
          "items": {"type": "string", "enum": ["builtin", "user", "custom", "external"]},
          "default": ["builtin", "user", "custom"]
        },
        "builtin": {
          "type": "object",
          "additionalProperties": {
            "type": "object",
            "properties": {
              "enabled": {"type": "boolean", "default": true}
            }
          }
        },
        "custom": {
          "type": "object",
          "additionalProperties": {
            "type": "object",
            "properties": {
              "enabled": {"type": "boolean", "default": true},
              "timeout": {"type": "number", "minimum": 1.0}
            }
          }
        }
      }
    }
  }
}
```

## Configuration Validation

### Validation Function

```python
import jsonschema
from typing import Dict, Any

def validate_config(config: Dict[str, Any]) -> bool:
    """
    Validate MCP Gateway configuration.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        True if valid, raises ValidationError if invalid
    """
    schema = {
        "type": "object",
        "properties": {
            "server": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "version": {"type": "string"},
                    "description": {"type": "string"}
                },
                "required": ["name"]
            },
            "tools": {
                "type": "object",
                "properties": {
                    "enabled": {"type": "boolean"},
                    "timeout": {"type": "number", "minimum": 1.0},
                    "categories": {
                        "type": "array",
                        "items": {"type": "string"}
                    }
                }
            }
        }
    }
    
    jsonschema.validate(config, schema)
    return True
```

### Configuration Loading with Validation

```python
import yaml
import os
from pathlib import Path
from typing import Dict, Any, Optional

class ConfigLoader:
    """Configuration loader with validation and environment variable support."""
    
    @staticmethod
    def load_config(config_path: Optional[Path] = None) -> Dict[str, Any]:
        """Load and validate configuration from multiple sources."""
        
        # Start with defaults
        config = ConfigLoader._get_defaults()
        
        # Load from file if exists
        if config_path and config_path.exists():
            with open(config_path, 'r') as f:
                file_config = yaml.safe_load(f)
                config = ConfigLoader._merge_config(config, file_config)
        
        # Override with environment variables
        env_config = ConfigLoader._load_from_env()
        config = ConfigLoader._merge_config(config, env_config)
        
        # Validate final configuration
        validate_config(config)
        
        return config
    
    @staticmethod
    def _get_defaults() -> Dict[str, Any]:
        """Get default configuration."""
        return {
            "server": {
                "name": "claude-mpm-gateway",
                "version": "1.0.0",
                "description": "Claude MPM MCP Gateway"
            },
            "tools": {
                "enabled": True,
                "timeout": 30.0,
                "categories": ["builtin", "user", "custom"]
            },
            "logging": {
                "level": "INFO",
                "format": "structured"
            }
        }
    
    @staticmethod
    def _load_from_env() -> Dict[str, Any]:
        """Load configuration from environment variables."""
        config = {}
        
        # Server configuration
        if os.getenv("CLAUDE_MPM_MCP_SERVER_NAME"):
            config.setdefault("server", {})["name"] = os.getenv("CLAUDE_MPM_MCP_SERVER_NAME")
        
        # Tools configuration
        if os.getenv("CLAUDE_MPM_MCP_TOOLS_ENABLED"):
            config.setdefault("tools", {})["enabled"] = os.getenv("CLAUDE_MPM_MCP_TOOLS_ENABLED").lower() == "true"
        
        if os.getenv("CLAUDE_MPM_MCP_TOOLS_TIMEOUT"):
            config.setdefault("tools", {})["timeout"] = float(os.getenv("CLAUDE_MPM_MCP_TOOLS_TIMEOUT"))
        
        return config
    
    @staticmethod
    def _merge_config(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively merge configuration dictionaries."""
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = ConfigLoader._merge_config(result[key], value)
            else:
                result[key] = value
        
        return result
```

## Configuration Examples

### Development Configuration

```yaml
# Development environment
mcp:
  server:
    name: "dev-gateway"
    version: "dev"
  
  tools:
    enabled: true
    timeout: 10.0
    categories: ["builtin", "user"]
  
  logging:
    level: "DEBUG"
    format: "human"
  
  performance:
    cache:
      enabled: false
    monitoring:
      enabled: false
```

### Production Configuration

```yaml
# Production environment
mcp:
  server:
    name: "prod-gateway"
    version: "1.0.0"
    description: "Production MCP Gateway"
  
  tools:
    enabled: true
    timeout: 30.0
    max_concurrent: 20
    categories: ["builtin", "user", "custom"]
  
  performance:
    cache:
      enabled: true
      ttl: 600
      max_size: 5000
    
    monitoring:
      enabled: true
      metrics_interval: 30
      health_check_interval: 60
  
  logging:
    level: "INFO"
    format: "json"
    file: "/var/log/claude-mpm/gateway.log"
    rotation:
      max_size: "50MB"
      backup_count: 10
  
  security:
    input_validation:
      strict: true
      max_parameter_size: 1048576
    
    rate_limiting:
      enabled: true
      requests_per_minute: 1000
      burst_size: 50
```

### Testing Configuration

```yaml
# Testing environment
mcp:
  server:
    name: "test-gateway"
    version: "test"
  
  tools:
    enabled: true
    timeout: 5.0
    categories: ["builtin"]
  
  logging:
    level: "WARNING"
    format: "human"
  
  performance:
    cache:
      enabled: false
    monitoring:
      enabled: false
```

## Related Documentation

- [MCP Gateway Developer Guide](README.md)
- [MCP Gateway API Reference](../04-api-reference/mcp-gateway-api.md)
- [Tool Development Guide](tool-development.md)
