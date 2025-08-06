# Memory System Configuration Guide

Complete configuration reference for the Claude MPM Agent Memory System.

## Configuration Files

The memory system reads configuration from multiple sources with the following precedence:

1. **Project-specific**: `.claude-mpm/config.yml` (highest priority)
2. **User-specific**: `~/.claude-mpm/config.yml`
3. **System defaults**: Built-in configuration values

## Basic Configuration

### Minimal Configuration

```yaml
# .claude-mpm/config.yml
memory:
  enabled: true
```

### Complete Configuration Example

```yaml
# .claude-mpm/config.yml
memory:
  # Core settings
  enabled: true                    # Enable/disable memory system
  auto_learning: true             # Enable automatic learning extraction
  
  # File and size limits
  limits:
    default_size_kb: 8            # Default memory file size limit (KB)
    max_sections: 10              # Maximum sections per memory file
    max_items_per_section: 15     # Maximum items per section
    max_line_length: 120          # Maximum characters per line item
  
  # Agent-specific overrides
  agent_overrides:
    engineer:
      size_kb: 12                 # Engineer agent gets 12KB
      auto_learning: true         # Enable auto-learning for engineer
      max_sections: 12            # Custom section limit
      
    research:
      size_kb: 16                 # Research agent gets 16KB
      auto_learning: true
      max_items_per_section: 20   # More items per section
      
    qa:
      size_kb: 8                  # Standard size
      auto_learning: false        # Manual learning only
      
    documentation:
      size_kb: 16                 # Large memory for docs
      max_sections: 15            # More sections for organization
      
    data_engineer:
      size_kb: 14                 # Larger for complex data patterns
      auto_learning: true
      
    test_integration:
      size_kb: 10                 # Medium size for test patterns
      auto_learning: true
  
  # Optimization settings
  optimization:
    auto_optimize: true           # Enable automatic optimization
    similarity_threshold: 0.85    # Threshold for duplicate detection
    consolidation_threshold: 0.70 # Threshold for item consolidation
    
  # Project analysis
  project_analysis:
    enabled: true                 # Enable project analysis
    cache_duration: 3600          # Cache analysis for 1 hour
    force_refresh_on_config_change: true
    
  # Memory building from documentation
  documentation_processing:
    enabled: true                 # Enable doc processing
    file_patterns:                # Files to process
      - "README.md"
      - "CONTRIBUTING.md"
      - "docs/**/*.md"
      - "*.md"
    exclude_patterns:             # Files to ignore
      - "node_modules/**"
      - ".git/**"
      - "dist/**"
      - "build/**"

# Hook integration
hooks:
  memory_integration: true        # Enable memory hooks
  
  # Memory-specific hooks
  pre_delegation_hooks:
    - name: "memory_injection"
      enabled: true
      priority: 20
      
  post_delegation_hooks:
    - name: "memory_extraction"
      enabled: true
      priority: 80
      condition: "auto_learning_enabled"
```

## Configuration Options Reference

### Core Settings

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `enabled` | boolean | `true` | Enable/disable the entire memory system |
| `auto_learning` | boolean | `true` | Enable automatic learning extraction from agent outputs |

### Size and Limit Settings

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `limits.default_size_kb` | integer | `8` | Default memory file size limit in KB (~2000 tokens) |
| `limits.max_sections` | integer | `10` | Maximum number of sections per memory file |
| `limits.max_items_per_section` | integer | `15` | Maximum items allowed per section |
| `limits.max_line_length` | integer | `120` | Maximum characters per memory line item |

### Agent Override Settings

Each agent can have custom settings that override the defaults:

```yaml
memory:
  agent_overrides:
    agent_name:
      size_kb: 12                 # Custom size limit
      auto_learning: true         # Agent-specific auto-learning
      max_sections: 12            # Custom section limit
      max_items_per_section: 20   # Custom item limit
      max_line_length: 150        # Custom line length
```

**Supported Agent Names:**
- `engineer`
- `research` 
- `qa`
- `documentation`
- `security`
- `pm`
- `data_engineer`
- `test_integration`
- `ops`
- `version_control`

### Optimization Settings

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `optimization.auto_optimize` | boolean | `false` | Enable automatic optimization |
| `optimization.similarity_threshold` | float | `0.85` | Threshold for duplicate detection (0.0-1.0) |
| `optimization.consolidation_threshold` | float | `0.70` | Threshold for consolidating similar items (0.0-1.0) |

### Project Analysis Settings

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `project_analysis.enabled` | boolean | `true` | Enable project analysis for contextual memory |
| `project_analysis.cache_duration` | integer | `3600` | Cache analysis results for N seconds |
| `project_analysis.force_refresh_on_config_change` | boolean | `true` | Refresh analysis when config changes |

### Documentation Processing Settings

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `documentation_processing.enabled` | boolean | `true` | Enable documentation processing |
| `documentation_processing.file_patterns` | array | `["README.md", "docs/**/*.md"]` | Files to process for memory building |
| `documentation_processing.exclude_patterns` | array | `["node_modules/**", ".git/**"]` | Files to exclude |

## Environment-Specific Configuration

### Development Environment

```yaml
# .claude-mpm/config.yml (development)
memory:
  enabled: true
  auto_learning: true
  
  limits:
    default_size_kb: 4            # Smaller files for faster testing
    
  agent_overrides:
    engineer:
      auto_learning: true
      size_kb: 6
      
    qa:
      auto_learning: true         # Enable for testing
      size_kb: 4

  optimization:
    auto_optimize: false          # Manual optimization in dev
    
  project_analysis:
    cache_duration: 300           # 5-minute cache for faster iteration
```

### Production Environment

```yaml
# .claude-mpm/config.yml (production)
memory:
  enabled: true
  auto_learning: true
  
  limits:
    default_size_kb: 8            # Standard production size
    
  agent_overrides:
    research:
      size_kb: 16                 # Larger for comprehensive research
      
    documentation:
      size_kb: 20                 # Large for extensive documentation
      
  optimization:
    auto_optimize: true           # Enable auto-optimization
    similarity_threshold: 0.90    # Stricter duplicate detection
    
  project_analysis:
    cache_duration: 7200          # 2-hour cache for stability
```

### CI/CD Environment

```yaml
# .claude-mpm/config.yml (CI/CD)
memory:
  enabled: false                  # Disable in CI/CD by default
  
  # OR minimal configuration for testing
  enabled: true
  auto_learning: false            # No learning in CI/CD
  
  limits:
    default_size_kb: 2            # Minimal size
    
  optimization:
    auto_optimize: false          # No optimization in CI/CD
    
  project_analysis:
    enabled: false                # Skip analysis in CI/CD
```

## Advanced Configuration Patterns

### Multi-Project Setup

For projects with multiple sub-projects:

```yaml
# Root .claude-mpm/config.yml
memory:
  enabled: true
  
  # Project-specific overrides based on directory structure
  project_overrides:
    frontend:
      agent_overrides:
        engineer:
          size_kb: 10
        documentation:
          size_kb: 12
          
    backend:
      agent_overrides:
        data_engineer:
          size_kb: 16
        ops:
          size_kb: 14
          
    mobile:
      agent_overrides:
        engineer:
          size_kb: 8
        test_integration:
          size_kb: 12
```

### Role-Based Configuration

Configure memory based on team roles:

```yaml
# Developer-focused configuration
memory:
  agent_overrides:
    engineer:
      size_kb: 16                 # Developers need comprehensive memory
      auto_learning: true
      
    qa:
      size_kb: 12                 # Testing focus
      auto_learning: true
      
    # Minimal memory for non-dev agents
    documentation:
      size_kb: 4
      auto_learning: false

# QA-focused configuration  
memory:
  agent_overrides:
    qa:
      size_kb: 20                 # QA team needs extensive memory
      max_sections: 15
      auto_learning: true
      
    test_integration:
      size_kb: 16
      auto_learning: true
      
    engineer:
      size_kb: 8                  # Minimal for non-QA agents
      auto_learning: false
```

### Performance-Optimized Configuration

For systems with performance constraints:

```yaml
memory:
  enabled: true
  
  limits:
    default_size_kb: 4            # Smaller default
    max_sections: 6               # Fewer sections
    max_items_per_section: 10     # Fewer items
    
  agent_overrides:
    # Only enable memory for most critical agents
    engineer:
      size_kb: 6
      auto_learning: true
      
    qa:
      size_kb: 4
      auto_learning: false        # Manual learning only
      
  optimization:
    auto_optimize: true           # Regular optimization
    similarity_threshold: 0.95    # Aggressive duplicate removal
    
  project_analysis:
    cache_duration: 7200          # Long cache to reduce overhead
```

## Configuration Validation

### Validating Configuration

Use the CLI to validate your memory configuration:

```bash
# Check current configuration
claude-mpm memory status

# Validate configuration file
claude-mpm config validate

# Test memory system with current config
claude-mpm memory route --content "test content"
```

### Configuration Errors

Common configuration errors and solutions:

**Invalid size limits:**
```yaml
# ❌ Incorrect
memory:
  limits:
    default_size_kb: 0            # Must be > 0
    max_sections: -1              # Must be > 0

# ✅ Correct  
memory:
  limits:
    default_size_kb: 4            # Minimum recommended
    max_sections: 5               # Reasonable minimum
```

**Invalid agent names:**
```yaml
# ❌ Incorrect
memory:
  agent_overrides:
    invalid_agent:                # Unknown agent type
      size_kb: 8

# ✅ Correct
memory:
  agent_overrides:
    engineer:                     # Valid agent type
      size_kb: 8
```

**Conflicting settings:**
```yaml
# ❌ Problematic
memory:
  enabled: false
  auto_learning: true             # Conflicting - memory disabled but learning enabled

# ✅ Correct
memory:
  enabled: true
  auto_learning: true
```

## Migration Guide

### Upgrading Configuration

When upgrading to newer versions with configuration changes:

1. **Backup current configuration:**
   ```bash
   cp .claude-mpm/config.yml .claude-mpm/config.yml.backup
   ```

2. **Check for breaking changes:**
   ```bash
   claude-mpm config check-compatibility
   ```

3. **Migrate configuration:**
   ```bash
   claude-mpm config migrate
   ```

### Configuration Schema Evolution

**Version 2.0.x → 2.1.x:**
- Added `data_engineer` and `test_integration` agent support
- Enhanced optimization settings
- New project analysis options

**Version 1.x → 2.0.x:**
- Moved from single `memory_enabled` to structured `memory` section
- Added agent-specific overrides
- Introduced optimization configuration

## Troubleshooting Configuration

### Common Issues

**Memory system not working:**
```yaml
# Check these settings
memory:
  enabled: true                   # Must be explicitly true
  
# Also check file permissions
# Ensure .claude-mpm directory is writable
```

**Agent-specific settings not applied:**
```yaml
# Ensure correct agent name
memory:
  agent_overrides:
    engineer:                     # Correct: matches agent routing patterns
      size_kb: 12
      
    # Not: Engineering, engineer_agent, etc.
```

**High memory usage:**
```yaml
# Reduce limits
memory:
  limits:
    default_size_kb: 4            # Reduce from default 8KB
    max_sections: 6               # Reduce from default 10
    
  optimization:
    auto_optimize: true           # Enable automatic cleanup
    similarity_threshold: 0.90    # More aggressive deduplication
```

### Debug Configuration

Enable debug logging for configuration issues:

```python
import logging
logging.getLogger('claude_mpm.core.config').setLevel(logging.DEBUG)
logging.getLogger('claude_mpm.services.agent_memory_manager').setLevel(logging.DEBUG)
```

Or via environment variable:
```bash
export CLAUDE_MPM_LOG_LEVEL=DEBUG
claude-mpm memory status
```

This configuration guide provides comprehensive coverage of all memory system configuration options and common patterns for different use cases.