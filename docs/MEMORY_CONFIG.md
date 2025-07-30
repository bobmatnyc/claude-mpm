# Agent Memory System Configuration

The Agent Memory System in Claude MPM supports flexible configuration through the project's configuration system. This document describes how to configure memory settings for your agents.

## Configuration Overview

Memory configuration is managed through the `memory` section in your configuration file or programmatically through the Config object.

## Configuration Schema

```yaml
memory:
  enabled: true                    # Master switch for memory system
  auto_learning: false            # Global auto-learning extraction setting
  limits:
    default_size_kb: 8            # Default file size limit in KB
    max_sections: 10              # Maximum sections per memory file
    max_items_per_section: 15     # Maximum items per section
    max_line_length: 120          # Maximum line length for items
  agent_overrides:
    <agent_id>:
      size_kb: 16                 # Override size limit for specific agent
      auto_learning: true         # Override auto-learning for specific agent
```

## Configuration Options

### Global Settings

- **`enabled`**: Master switch to enable/disable the memory system globally
  - Default: `true`
  - When `false`, memory operations become no-ops

- **`auto_learning`**: Enable automatic learning extraction from agent outputs
  - Default: `false`
  - When `true`, agents will automatically extract and save learnings

### Memory Limits

- **`default_size_kb`**: Maximum file size in kilobytes
  - Default: `8` (approximately 2000 tokens)
  - Prevents memory files from growing unbounded

- **`max_sections`**: Maximum number of sections in a memory file
  - Default: `10`
  - Helps maintain organized, focused memories

- **`max_items_per_section`**: Maximum items per section
  - Default: `15`
  - Ensures sections remain readable and manageable

- **`max_line_length`**: Maximum length for individual memory items
  - Default: `120` characters
  - Long items are truncated with ellipsis

### Agent-Specific Overrides

Different agents may have different memory requirements:

```yaml
agent_overrides:
  research:
    size_kb: 16          # Research agents can have larger memory
    auto_learning: true  # Enable auto-learning for research
  qa:
    auto_learning: true  # QA agents learn from test results
  minimal_agent:
    size_kb: 4           # Minimal agents need less memory
```

## Configuration Methods

### 1. YAML Configuration File

Create a `.claude-mpm/config.yml` file:

```yaml
memory:
  enabled: true
  auto_learning: false
  limits:
    default_size_kb: 8
    max_sections: 10
    max_items_per_section: 15
  agent_overrides:
    research:
      size_kb: 16
      auto_learning: true
```

### 2. JSON Configuration File

Create a `.claude-mpm/config.json` file:

```json
{
  "memory": {
    "enabled": true,
    "auto_learning": false,
    "limits": {
      "default_size_kb": 8,
      "max_sections": 10,
      "max_items_per_section": 15
    },
    "agent_overrides": {
      "research": {
        "size_kb": 16,
        "auto_learning": true
      }
    }
  }
}
```

### 3. Programmatic Configuration

```python
from claude_mpm.core.config import Config
from claude_mpm.services.agent_memory_manager import AgentMemoryManager

config = Config({
    'memory': {
        'enabled': True,
        'limits': {
            'default_size_kb': 12
        },
        'agent_overrides': {
            'custom_agent': {
                'size_kb': 20
            }
        }
    }
})

memory_manager = AgentMemoryManager(config)
```

## Default Configuration

If no memory configuration is provided, the following defaults are used:

```yaml
memory:
  enabled: true
  auto_learning: false
  limits:
    default_size_kb: 8
    max_sections: 10
    max_items_per_section: 15
    max_line_length: 120
  agent_overrides:
    research:
      size_kb: 16
      auto_learning: true
    qa:
      auto_learning: true
```

## Use Cases

### Research-Heavy Projects

For projects requiring extensive research:

```yaml
memory:
  limits:
    default_size_kb: 16
    max_sections: 15
  agent_overrides:
    research:
      size_kb: 32
    architecture:
      size_kb: 24
```

### Resource-Constrained Environments

For minimal memory usage:

```yaml
memory:
  limits:
    default_size_kb: 4
    max_sections: 5
    max_items_per_section: 10
```

### Testing and QA Focus

For projects with heavy testing:

```yaml
memory:
  auto_learning: true
  agent_overrides:
    qa:
      size_kb: 16
      auto_learning: true
    test_agent:
      size_kb: 12
      auto_learning: true
```

## Best Practices

1. **Start with defaults**: The default configuration works well for most projects
2. **Monitor memory growth**: Use `claude-mpm memory status` to track memory usage
3. **Increase limits gradually**: Only increase limits when agents consistently hit them
4. **Enable auto-learning selectively**: Start with specific agents rather than globally
5. **Regular cleanup**: Periodically review and clean old memories with `claude-mpm memory clean`

## Troubleshooting

### Memory files not updating
- Check if `memory.enabled` is `true`
- Verify agent has write permissions to `.claude-mpm/memories/`
- Check logs for memory-related errors

### Memory files growing too large
- Reduce `default_size_kb` or agent-specific overrides
- Decrease `max_items_per_section`
- Run `claude-mpm memory clean` to remove old items

### Auto-learning not working
- Verify `auto_learning` is enabled for the specific agent
- Check that agent outputs contain learnable patterns
- Review logs for learning extraction attempts