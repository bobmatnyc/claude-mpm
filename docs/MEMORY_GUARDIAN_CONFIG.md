# Memory Guardian Configuration Reference

> ⚠️ **Beta Configuration**
> 
> Memory Guardian is an experimental feature. Configuration options and behavior
> may change in future versions. Test thoroughly before using in production.

## Overview

This document provides comprehensive reference for all Memory Guardian configuration options, including YAML configuration files, environment variables, command-line arguments, and programmatic configuration.

## Configuration Hierarchy

Configuration is applied in the following order (later sources override earlier ones):

1. **Default Values**: Built-in defaults optimized for common scenarios
2. **Platform Adjustments**: Platform-specific optimizations (macOS/Linux/Windows)
3. **System Memory Adjustment**: Automatic adjustment based on available RAM
4. **Configuration File**: YAML configuration file settings
5. **Environment Variables**: Environment-based overrides
6. **Command Line Arguments**: Explicit command-line parameters

## YAML Configuration File

### Complete Configuration Example

```yaml
# ~/.claude-mpm/memory-guardian.yaml
# Complete Memory Guardian configuration

# Core memory thresholds (in MB)
thresholds:
  warning: 12288          # 12GB - Start increased monitoring
  critical: 15360         # 15GB - Primary restart threshold  
  emergency: 18432        # 18GB - Emergency restart threshold
  
  # Percentage-based fallbacks (used when system memory is detected)
  warning_percent: 50.0   # 50% of total system memory
  critical_percent: 65.0  # 65% of total system memory
  emergency_percent: 75.0 # 75% of total system memory

# Monitoring behavior configuration
monitoring:
  # Check intervals in seconds
  normal_interval: 30     # Normal monitoring frequency
  warning_interval: 15    # Frequency when in warning state
  critical_interval: 5    # Frequency when in critical state
  
  # Monitoring method preferences
  prefer_psutil: true     # Use psutil library if available
  fallback_methods:       # Fallback monitoring methods
    - platform_specific   # OS-specific commands (ps, tasklist, etc.)
    - resource_module     # Python resource module
  
  # Logging and reporting
  log_memory_stats: true  # Enable memory statistics logging
  log_interval: 300       # Log summary every 5 minutes
  detailed_logging: false # Enable detailed debug logging

# Restart policy configuration
restart_policy:
  # Attempt limiting
  max_attempts: 3         # Maximum restart attempts
  attempt_window: 3600    # Time window for counting attempts (1 hour)
  
  # Cooldown configuration
  initial_cooldown: 30    # Initial cooldown after restart (seconds)
  max_cooldown: 300       # Maximum cooldown period (5 minutes)
  cooldown_multiplier: 2.0 # Multiply cooldown on each retry
  
  # Graceful shutdown
  graceful_timeout: 30    # Time to wait for graceful shutdown
  force_kill_timeout: 10  # Time before SIGKILL after SIGTERM

# Platform-specific overrides
platform_overrides:
  # macOS specific settings
  macos_use_activity_monitor: false    # Use Activity Monitor data
  macos_memory_pressure_check: true    # Check system memory pressure
  
  # Linux specific settings  
  linux_use_proc: true                 # Use /proc filesystem
  linux_check_oom_score: true          # Monitor OOM killer score
  
  # Windows specific settings
  windows_use_wmi: true                # Use WMI for monitoring
  windows_use_performance_counter: false # Use performance counters

# Process configuration
process_command: ['claude-code']       # Command to execute
process_args: []                       # Additional command arguments
process_env: {}                        # Environment variables for process
working_directory: null                # Working directory (null = current)

# Service configuration
enabled: true                          # Enable Memory Guardian
auto_start: true                       # Auto-start monitored process
persist_state: true                    # Enable state preservation
state_file: null                       # Custom state file path

# Advanced configuration
health_monitoring:
  enable_cpu_monitoring: false         # Monitor CPU usage
  enable_disk_monitoring: false        # Monitor disk usage
  enable_network_monitoring: false     # Monitor network usage
  cpu_threshold_percent: 80.0          # CPU usage threshold
  disk_threshold_percent: 90.0         # Disk usage threshold

# Notification settings
notifications:
  enable_desktop_notifications: false  # Desktop notifications
  enable_email_notifications: false    # Email notifications
  email_recipients: []                 # Email notification recipients
  webhook_url: null                    # Webhook for notifications
```

### Minimal Configuration Examples

#### Development Configuration
```yaml
# dev-memory-guardian.yaml
thresholds:
  warning: 8192    # 8GB
  critical: 10240  # 10GB
  emergency: 12288 # 12GB

monitoring:
  normal_interval: 60
  detailed_logging: true

restart_policy:
  max_attempts: 5
```

#### Production Configuration  
```yaml
# prod-memory-guardian.yaml
thresholds:
  warning: 16384   # 16GB
  critical: 20480  # 20GB
  emergency: 24576 # 24GB

monitoring:
  normal_interval: 30
  log_memory_stats: true
  log_interval: 180

restart_policy:
  max_attempts: 10
  initial_cooldown: 60

persist_state: true
```

#### High-Performance Configuration
```yaml
# performance-memory-guardian.yaml
thresholds:
  critical: 30720  # 30GB

monitoring:
  normal_interval: 120  # Check less frequently
  log_memory_stats: false

persist_state: false  # Faster restarts
```

## Environment Variables

### Memory Thresholds
```bash
# Memory thresholds in MB
export CLAUDE_MPM_MEMORY_WARNING_MB=12288
export CLAUDE_MPM_MEMORY_CRITICAL_MB=15360  
export CLAUDE_MPM_MEMORY_EMERGENCY_MB=18432
```

### Restart Policy
```bash
# Restart behavior
export CLAUDE_MPM_RESTART_MAX_ATTEMPTS=3
export CLAUDE_MPM_RESTART_COOLDOWN=30
export CLAUDE_MPM_RESTART_WINDOW=3600
```

### Monitoring Configuration
```bash
# Monitoring intervals and behavior
export CLAUDE_MPM_MONITOR_INTERVAL=30
export CLAUDE_MPM_LOG_INTERVAL=300
export CLAUDE_MPM_DETAILED_LOGGING=false
```

### Service Settings
```bash
# Service configuration
export CLAUDE_MPM_MEMORY_GUARDIAN_ENABLED=true
export CLAUDE_MPM_AUTO_START=true
export CLAUDE_MPM_PERSIST_STATE=true
```

### Process Configuration
```bash
# Process command and environment
export CLAUDE_MPM_PROCESS_COMMAND="claude-code --verbose"
export CLAUDE_MPM_WORKING_DIRECTORY="/path/to/project"
```

### Platform-Specific Settings
```bash
# macOS
export CLAUDE_MPM_MACOS_MEMORY_PRESSURE_CHECK=true

# Linux  
export CLAUDE_MPM_LINUX_USE_PROC=true
export CLAUDE_MPM_LINUX_CHECK_OOM_SCORE=true

# Windows
export CLAUDE_MPM_WINDOWS_USE_WMI=true
```

## Command Line Arguments Reference

### Memory Monitoring Options

#### `--memory-threshold MB`
**Default**: 18000  
**Description**: Primary memory threshold that triggers restart consideration  
**Example**: `--memory-threshold 16000`

#### `--warning-threshold MB`  
**Default**: 80% of memory threshold  
**Description**: Threshold for increased monitoring frequency  
**Example**: `--warning-threshold 12800`

#### `--emergency-threshold MB`
**Default**: 120% of memory threshold  
**Description**: Threshold for immediate restart regardless of other factors  
**Example**: `--emergency-threshold 19200`

#### `--check-interval SECONDS`
**Default**: 30  
**Description**: Frequency of memory checks in normal state  
**Example**: `--check-interval 60`

### Restart Policy Options

#### `--max-restarts COUNT`
**Default**: 3  
**Description**: Maximum automatic restart attempts  
**Example**: `--max-restarts 5`

#### `--restart-cooldown SECONDS`
**Default**: 10  
**Description**: Initial cooldown period between restart attempts  
**Example**: `--restart-cooldown 30`

#### `--graceful-timeout SECONDS`
**Default**: 30  
**Description**: Time to wait for graceful process shutdown  
**Example**: `--graceful-timeout 45`

### State Preservation Options

#### `--enable-state-preservation`
**Default**: Enabled  
**Description**: Enable conversation state preservation across restarts  
**Example**: `--enable-state-preservation`

#### `--no-state-preservation`
**Default**: N/A  
**Description**: Disable state preservation for faster restarts  
**Example**: `--no-state-preservation`

#### `--state-dir PATH`
**Default**: `~/.claude-mpm/state`  
**Description**: Directory for storing state files  
**Example**: `--state-dir ~/my-claude-states`

### Display Options

#### `--quiet`
**Default**: N/A  
**Description**: Minimal output, only show critical events  
**Example**: `--quiet`

#### `--verbose`
**Default**: N/A  
**Description**: Detailed monitoring output with debug information  
**Example**: `--verbose`

#### `--show-stats`  
**Default**: N/A  
**Description**: Display periodic memory usage statistics  
**Example**: `--show-stats`

#### `--stats-interval SECONDS`
**Default**: 60  
**Description**: Frequency of statistics display  
**Example**: `--stats-interval 30`

### Configuration File Options

#### `--config PATH`
**Default**: N/A  
**Description**: Path to YAML configuration file  
**Example**: `--config ~/.claude-mpm/memory-guardian.yaml`

### Logging Options

#### `--logging LEVEL`
**Default**: INFO  
**Description**: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)  
**Example**: `--logging DEBUG`

#### `--log-dir PATH`
**Default**: `~/.claude-mpm/logs`  
**Description**: Directory for log files  
**Example**: `--log-dir ~/my-logs`

## Default Values Reference

### Memory Thresholds (MB)
```python
DEFAULT_THRESHOLDS = {
    'warning': 12288,      # 12GB
    'critical': 15360,     # 15GB  
    'emergency': 18432,    # 18GB
    'warning_percent': 50.0,
    'critical_percent': 65.0,
    'emergency_percent': 75.0
}
```

### Monitoring Configuration
```python
DEFAULT_MONITORING = {
    'normal_interval': 30,      # seconds
    'warning_interval': 15,     # seconds
    'critical_interval': 5,     # seconds
    'prefer_psutil': True,
    'log_memory_stats': True,
    'log_interval': 300,        # 5 minutes
    'detailed_logging': False
}
```

### Restart Policy
```python
DEFAULT_RESTART_POLICY = {
    'max_attempts': 3,
    'attempt_window': 3600,     # 1 hour
    'initial_cooldown': 30,     # seconds
    'max_cooldown': 300,        # 5 minutes
    'cooldown_multiplier': 2.0,
    'graceful_timeout': 30,     # seconds
    'force_kill_timeout': 10    # seconds
}
```

### Service Configuration
```python
DEFAULT_SERVICE = {
    'enabled': True,
    'auto_start': True,
    'persist_state': True,
    'process_command': ['claude-code'],
    'process_args': [],
    'process_env': {},
    'working_directory': None
}
```

## Platform-Specific Configurations

### macOS Optimizations
```yaml
platform_overrides:
  macos_use_activity_monitor: false    # Activity Monitor integration
  macos_memory_pressure_check: true    # System memory pressure detection

# Additional macOS-specific settings
monitoring:
  prefer_psutil: true                  # psutil works well on macOS
  fallback_methods:
    - platform_specific               # Use 'ps' command
    - resource_module
```

### Linux Optimizations  
```yaml
platform_overrides:
  linux_use_proc: true                # Use /proc filesystem
  linux_check_oom_score: true         # Monitor OOM killer score

# Additional Linux-specific settings
monitoring:
  prefer_psutil: true                 # psutil excellent on Linux
  fallback_methods:
    - platform_specific              # Use /proc/[pid]/status
    - resource_module
```

### Windows Optimizations
```yaml
platform_overrides:
  windows_use_wmi: true               # WMI for process monitoring
  windows_use_performance_counter: false # Performance counters

# Additional Windows-specific settings  
monitoring:
  prefer_psutil: true                 # psutil handles Windows well
  fallback_methods:
    - platform_specific              # Use tasklist/wmic
    - resource_module
```

## Recommended Settings by Use Case

### Development Environment
```yaml
# Optimized for development machines with 16GB+ RAM
thresholds:
  warning: 8192     # 8GB
  critical: 10240   # 10GB
  emergency: 12288  # 12GB

monitoring:
  normal_interval: 60      # Less frequent checks
  detailed_logging: true   # Debug information
  log_memory_stats: true

restart_policy:
  max_attempts: 5          # More attempts for development
  initial_cooldown: 30
```

### Production Environment
```yaml
# Optimized for production servers with 32GB+ RAM
thresholds:
  warning: 16384    # 16GB
  critical: 20480   # 20GB  
  emergency: 24576  # 24GB

monitoring:
  normal_interval: 30      # Regular monitoring
  log_memory_stats: true
  log_interval: 180        # Log every 3 minutes

restart_policy:
  max_attempts: 10         # More restart attempts
  initial_cooldown: 60     # Longer cooldown

persist_state: true        # Always preserve state
```

### CI/CD Environment
```yaml
# Optimized for continuous integration
thresholds:
  critical: 8192          # 8GB - conservative for CI

monitoring:
  normal_interval: 60     # Less frequent monitoring
  log_memory_stats: false # Minimal logging

restart_policy:
  max_attempts: 1         # Single restart attempt
  initial_cooldown: 10    # Fast restart

persist_state: false      # Fast startup without state
```

### High-Memory Workloads
```yaml
# For data processing and large document analysis
thresholds:
  warning: 24576    # 24GB
  critical: 30720   # 30GB
  emergency: 36864  # 36GB

monitoring:
  normal_interval: 120    # Less frequent checks
  warning_interval: 30    # Moderate warning frequency
  critical_interval: 10   # Faster critical monitoring

restart_policy:
  max_attempts: 2         # Fewer attempts for large workloads
  initial_cooldown: 120   # Longer cooldown
```

## Configuration Validation

### Validation Rules

The Memory Guardian validates configuration and reports issues:

1. **Threshold Order**: Warning < Critical < Emergency
2. **Positive Intervals**: All intervals must be > 0
3. **Restart Limits**: Max attempts >= 0
4. **Cooldown Values**: Initial cooldown > 0
5. **Process Command**: Cannot be empty
6. **File Paths**: State directories must be writable

### Example Validation
```python
def validate_config(config: MemoryGuardianConfig) -> List[str]:
    """Validate configuration and return issues."""
    issues = []
    
    # Validate threshold order
    if config.thresholds.warning >= config.thresholds.critical:
        issues.append("Warning threshold must be less than critical")
    
    # Validate intervals
    if config.monitoring.normal_interval <= 0:
        issues.append("Normal interval must be positive")
    
    # Validate restart policy
    if config.restart_policy.max_attempts < 0:
        issues.append("Max attempts cannot be negative")
    
    return issues
```

### Configuration Testing
```bash
# Test configuration file validity
claude-mpm run-guarded --config config.yaml --dry-run

# Validate with verbose output
claude-mpm run-guarded --config config.yaml --verbose --dry-run
```

## Environment-Specific Examples

### Docker Container Configuration
```yaml
# docker-memory-guardian.yaml
thresholds:
  critical: 1024          # 1GB for container limits

monitoring:
  normal_interval: 30
  prefer_psutil: false    # May not be available
  fallback_methods:
    - platform_specific

restart_policy:
  max_attempts: 1         # Container orchestration handles restarts

persist_state: false      # Containers are stateless
```

### Kubernetes Pod Configuration
```yaml
# k8s-memory-guardian.yaml  
thresholds:
  critical: 2048          # 2GB pod limit

monitoring:
  normal_interval: 15     # Faster monitoring in k8s
  log_memory_stats: true

restart_policy:
  max_attempts: 0         # Let k8s handle restarts

notifications:
  webhook_url: "http://alert-manager:9093/api/v1/alerts"
```

### Serverless Environment
```yaml
# serverless-memory-guardian.yaml
thresholds:
  critical: 512           # 512MB function limit

monitoring:
  normal_interval: 10     # Aggressive monitoring
  
restart_policy:
  max_attempts: 0         # Platform handles restarts

persist_state: false      # Stateless functions
```

## Advanced Configuration Patterns

### Multi-Environment Configuration
```yaml
# base-config.yaml
defaults: &defaults
  monitoring:
    prefer_psutil: true
    log_memory_stats: true
  restart_policy:
    graceful_timeout: 30

# Development inherits defaults
development:
  <<: *defaults
  thresholds:
    critical: 8192
  monitoring:
    detailed_logging: true

# Production overrides specific values  
production:
  <<: *defaults
  thresholds:
    critical: 20480
  restart_policy:
    max_attempts: 10
```

### Conditional Configuration
```yaml
# Use environment variables for conditional settings
thresholds:
  critical: ${MEMORY_LIMIT:-15360}

monitoring:
  normal_interval: ${MONITOR_INTERVAL:-30}
  detailed_logging: ${DEBUG_MODE:-false}

restart_policy:
  max_attempts: ${MAX_RESTARTS:-3}
```

### Profile-Based Configuration
```bash
# Load different profiles
claude-mpm run-guarded --config dev-profile.yaml     # Development
claude-mpm run-guarded --config prod-profile.yaml    # Production  
claude-mpm run-guarded --config debug-profile.yaml   # Debugging
```

## Troubleshooting Configuration Issues

### Common Configuration Problems

#### 1. Invalid Threshold Order
```yaml
# WRONG - Warning higher than critical
thresholds:
  warning: 16000
  critical: 12000  # Error: critical < warning

# CORRECT
thresholds:
  warning: 12000
  critical: 16000
```

#### 2. Invalid File Paths
```yaml
# WRONG - Non-existent directory
state_file: "/non/existent/path/state.json"

# CORRECT - Valid directory
state_file: "~/.claude-mpm/state/custom-state.json"
```

#### 3. Conflicting Settings
```yaml
# WRONG - Conflicting state settings
persist_state: true
state_file: null        # Can't persist without location

# CORRECT
persist_state: true
state_file: "~/.claude-mpm/state/state.json"
```

### Configuration Debugging

#### Enable Debug Logging
```bash
claude-mpm run-guarded --config config.yaml --verbose --logging DEBUG
```

#### Validate Configuration
```python
from claude_mpm.config.memory_guardian_config import MemoryGuardianConfig

# Load and validate config
config = MemoryGuardianConfig.from_file("config.yaml")
issues = config.validate()

if issues:
    print("Configuration issues:")
    for issue in issues:
        print(f"  - {issue}")
```

#### Test Configuration  
```bash
# Dry run to test configuration
claude-mpm run-guarded --config config.yaml --dry-run

# Test with minimal memory threshold
claude-mpm run-guarded --memory-threshold 1000 --check-interval 5
```

## Migration and Upgrade Guide

### Migrating from Command Line to Configuration File

1. **Current Command**:
   ```bash
   claude-mpm run-guarded --memory-threshold 16000 --max-restarts 5 --verbose
   ```

2. **Equivalent Configuration File**:
   ```yaml
   # migrated-config.yaml
   thresholds:
     critical: 16000
   
   restart_policy:
     max_attempts: 5
   
   monitoring:
     detailed_logging: true
   ```

3. **New Command**:
   ```bash
   claude-mpm run-guarded --config migrated-config.yaml
   ```

### Version Compatibility

Memory Guardian configuration is versioned for compatibility:

```yaml
# Include version for compatibility checking
version: "1.0"

# Configuration follows...
thresholds:
  critical: 15360
```

## Best Practices

### Configuration Management
1. **Version Control**: Store configuration files in version control
2. **Environment Separation**: Use different configs for dev/staging/production
3. **Documentation**: Comment configuration choices
4. **Validation**: Always validate configurations before deployment

### Security Considerations
1. **File Permissions**: Restrict configuration file access (600)
2. **Sensitive Data**: Avoid storing secrets in configuration files
3. **Path Validation**: Use absolute paths to prevent traversal attacks
4. **Environment Variables**: Use environment variables for sensitive settings

### Performance Optimization
1. **Monitoring Frequency**: Balance responsiveness vs. overhead
2. **State Size**: Monitor state file sizes and enable compression
3. **Log Levels**: Use appropriate log levels for production
4. **Platform Features**: Enable platform-specific optimizations

This comprehensive configuration reference provides all the information needed to effectively configure and customize the Memory Guardian System for any environment or use case.