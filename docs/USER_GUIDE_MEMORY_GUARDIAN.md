# Memory Guardian System - User Guide

> ⚠️ **EXPERIMENTAL FEATURE**
> 
> Memory Guardian is currently in **beta** and is considered an experimental feature.
> 
> - This feature may change significantly in future versions
> - Some functionality may not work as expected in all environments
> - Not recommended for critical production use without thorough testing
> - Please report issues at: https://github.com/bluescreen10/claude-mpm/issues
>
> To suppress this warning, use the `--accept-experimental` flag.

## Overview

The Memory Guardian System is a sophisticated memory monitoring and management solution for Claude Code sessions. It automatically monitors memory usage, provides early warnings, and performs controlled restarts when memory thresholds are exceeded, all while preserving your conversation context and working state.

## Why Memory Guardian?

Claude Code sessions can accumulate significant memory usage over extended conversations, especially when processing large files or complex projects. Without intervention, this can lead to:

- System slowdowns and reduced performance
- Potential crashes due to memory exhaustion
- Loss of conversation context and work progress
- Forced manual restarts with context loss

The Memory Guardian System solves these problems by:

- **Proactive Monitoring**: Continuously tracks memory usage with configurable thresholds
- **Intelligent Restarts**: Performs controlled restarts before critical memory levels
- **State Preservation**: Saves and restores conversation context across restarts
- **Safety Features**: Prevents restart loops and provides graceful degradation

## Quick Start

### Basic Usage

Start Claude with memory monitoring using default settings (18GB threshold):

```bash
claude-mpm run-guarded
```

This enables:
- Memory monitoring every 30 seconds
- Automatic restart at 18GB memory usage
- State preservation across restarts
- Maximum 3 restart attempts

### Common Usage Patterns

**Development Work** (lower threshold for smaller machines):
```bash
claude-mpm run-guarded --memory-threshold 12000
```

**Production Environment** (more restarts allowed):
```bash
claude-mpm run-guarded --max-restarts 10 --quiet
```

**Performance Monitoring** (show statistics):
```bash
claude-mpm run-guarded --show-stats --verbose
```

**Fast Monitoring** (for debugging):
```bash
claude-mpm run-guarded --check-interval 10 --verbose
```

## Memory Thresholds

The Memory Guardian operates with three threshold levels:

### Warning Level (80% of threshold)
- **Default**: 14.4GB (80% of 18GB)
- **Action**: Increased monitoring frequency (every 15 seconds)
- **Purpose**: Early warning to prepare for potential restart

### Critical Level (100% of threshold)
- **Default**: 18GB
- **Action**: Consider restart after sustained high memory
- **Purpose**: Primary restart trigger

### Emergency Level (120% of threshold)
- **Default**: 21.6GB (120% of 18GB)
- **Action**: Immediate restart regardless of other factors
- **Purpose**: Safety net for runaway memory usage

### Setting Custom Thresholds

```bash
# Set main threshold (critical level)
claude-mpm run-guarded --memory-threshold 16000

# Set all thresholds explicitly
claude-mpm run-guarded \
  --warning-threshold 12800 \
  --memory-threshold 16000 \
  --emergency-threshold 19200
```

## Configuration Options

### Command Line Arguments

#### Memory Monitoring
- `--memory-threshold MB`: Main memory threshold (default: 18000MB)
- `--warning-threshold MB`: Warning threshold (default: 80% of main)
- `--emergency-threshold MB`: Emergency threshold (default: 120% of main)
- `--check-interval SECONDS`: Memory check frequency (default: 30)

#### Restart Policy
- `--max-restarts COUNT`: Maximum restart attempts (default: 3)
- `--restart-cooldown SECONDS`: Cooldown between restarts (default: 10)
- `--graceful-timeout SECONDS`: Time for graceful shutdown (default: 30)

#### State Preservation
- `--enable-state-preservation`: Enable state saving (default: enabled)
- `--no-state-preservation`: Disable for faster restarts
- `--state-dir PATH`: Custom directory for state files

#### Display Options
- `--quiet`: Minimal output, only critical events
- `--verbose`: Detailed monitoring information
- `--show-stats`: Display memory statistics periodically
- `--stats-interval SECONDS`: Statistics display frequency (default: 60)

### Configuration File

Create a YAML configuration file for complex setups:

```yaml
# ~/.claude-mpm/memory-guardian.yaml
memory_guardian:
  # Memory thresholds in MB
  thresholds:
    warning: 12288      # 12GB
    critical: 15360     # 15GB
    emergency: 18432    # 18GB
  
  # Monitoring settings
  monitoring:
    normal_interval: 30      # Normal check interval (seconds)
    warning_interval: 15     # Warning state interval
    critical_interval: 5     # Critical state interval
    log_memory_stats: true   # Log periodic statistics
    log_interval: 300        # Statistics log frequency
  
  # Restart policy
  restart_policy:
    max_attempts: 5          # Maximum restart attempts
    attempt_window: 3600     # Time window for attempt counting
    initial_cooldown: 30     # Initial cooldown period
    cooldown_multiplier: 2.0 # Cooldown growth factor
    max_cooldown: 300        # Maximum cooldown period
    graceful_timeout: 30     # Graceful shutdown timeout
  
  # Process settings
  enabled: true
  auto_start: true
  persist_state: true
```

Use the configuration file:
```bash
claude-mpm run-guarded --config ~/.claude-mpm/memory-guardian.yaml
```

## State Preservation

The Memory Guardian can preserve your session state across restarts, including:

- **Conversation Context**: Recent messages and context
- **Working Directory**: Current directory and file state
- **Environment Variables**: Relevant environment settings
- **Git State**: Current branch and repository status

### How State Preservation Works

1. **Before Restart**: System captures current state to JSON file
2. **During Restart**: Process terminates gracefully
3. **After Restart**: New process loads saved state
4. **Cleanup**: Old state files (>7 days) are automatically removed

### Controlling State Preservation

```bash
# Enable state preservation (default)
claude-mpm run-guarded --enable-state-preservation

# Disable for faster restarts
claude-mpm run-guarded --no-state-preservation

# Custom state directory
claude-mpm run-guarded --state-dir ~/my-claude-states
```

## Safety Features

### Restart Loop Protection

The system prevents excessive restarts through multiple mechanisms:

- **Attempt Limiting**: Maximum restart attempts (default: 3)
- **Time Windows**: Attempts counted within specific time periods
- **Exponential Backoff**: Increasing cooldown periods between attempts
- **Circuit Breaker**: System disables after excessive failures

### Graceful Degradation

When restart limits are reached:

1. **Warning Mode**: Continue with increased monitoring
2. **Read-Only Mode**: Disable memory-intensive operations
3. **Emergency Mode**: Minimal functionality to preserve stability

### Memory Leak Detection

The system can detect potential memory leaks:

- Monitors memory growth patterns
- Identifies unusual memory accumulation
- Adjusts restart thresholds accordingly
- Logs leak detection for analysis

## Monitoring and Diagnostics

### Real-Time Monitoring

View current memory status:
```bash
claude-mpm run-guarded --verbose --show-stats
```

Output includes:
- Current memory usage
- Peak memory reached
- Average memory over time
- Time since last restart
- Restart attempt count

### Memory Statistics

Enable periodic statistics logging:
```bash
claude-mpm run-guarded --show-stats --stats-interval 30
```

Statistics include:
- Memory usage trends
- Threshold breach history
- Restart success rates
- Performance metrics

### Log Analysis

Memory Guardian logs are written to:
- **Default**: `~/.claude-mpm/logs/memory-guardian.log`
- **Custom**: Use `--log-dir` to specify location

Log levels:
- **INFO**: Normal operations and state changes
- **WARNING**: Memory thresholds exceeded
- **ERROR**: Restart failures and critical issues
- **DEBUG**: Detailed monitoring data (use `--verbose`)

## Troubleshooting

### Common Issues

#### High Memory Usage Warnings
**Symptoms**: Frequent warning threshold alerts
**Solutions**:
- Lower the warning threshold: `--warning-threshold 10000`
- Increase check intervals: `--check-interval 60`
- Enable state preservation to reduce restart impact

#### Restart Loops
**Symptoms**: Continuous restart attempts
**Solutions**:
- Check if threshold is too low for your workload
- Increase restart cooldown: `--restart-cooldown 60`
- Reduce max restart attempts: `--max-restarts 2`
- Examine logs for underlying issues

#### State Preservation Failures
**Symptoms**: Context lost after restart
**Solutions**:
- Verify state directory permissions
- Check disk space in state directory
- Disable state preservation temporarily: `--no-state-preservation`
- Review state files: `ls ~/.claude-mpm/state/`

#### Performance Issues
**Symptoms**: System slowdown during monitoring
**Solutions**:
- Increase check intervals: `--check-interval 60`
- Disable statistics: remove `--show-stats`
- Use quiet mode: `--quiet`

### Diagnostic Commands

Check system memory availability:
```bash
# Linux/macOS
free -h
# macOS specific
vm_stat

# Windows
wmic OS get TotalVisibleMemorySize,FreePhysicalMemory
```

Test memory thresholds:
```bash
# Test with very low threshold
claude-mpm run-guarded --memory-threshold 1000 --check-interval 5
```

Verify configuration:
```bash
# Validate YAML configuration
python -c "import yaml; print(yaml.safe_load(open('config.yaml')))"
```

### Getting Help

If you encounter issues:

1. **Enable verbose logging**:
   ```bash
   claude-mpm run-guarded --verbose --show-stats
   ```

2. **Check log files**:
   ```bash
   tail -f ~/.claude-mpm/logs/memory-guardian.log
   ```

3. **Test with minimal configuration**:
   ```bash
   claude-mpm run-guarded --memory-threshold 20000 --check-interval 60
   ```

4. **Disable state preservation temporarily**:
   ```bash
   claude-mpm run-guarded --no-state-preservation
   ```

## Advanced Usage

### Environment Variables

Configure Memory Guardian through environment variables:

```bash
# Memory thresholds
export CLAUDE_MPM_MEMORY_WARNING_MB=12288
export CLAUDE_MPM_MEMORY_CRITICAL_MB=15360
export CLAUDE_MPM_MEMORY_EMERGENCY_MB=18432

# Restart policy
export CLAUDE_MPM_RESTART_MAX_ATTEMPTS=5
export CLAUDE_MPM_RESTART_COOLDOWN=30

# Monitoring
export CLAUDE_MPM_MONITOR_INTERVAL=30
export CLAUDE_MPM_LOG_INTERVAL=300

# Service settings
export CLAUDE_MPM_MEMORY_GUARDIAN_ENABLED=true
export CLAUDE_MPM_AUTO_START=true

# Process command
export CLAUDE_MPM_PROCESS_COMMAND="claude-code --verbose"

claude-mpm run-guarded
```

### Integration with CI/CD

For automated environments:
```bash
# Non-interactive mode with strict limits
claude-mpm run-guarded \
  --memory-threshold 8000 \
  --max-restarts 1 \
  --no-state-preservation \
  --quiet \
  --non-interactive
```

### Performance Optimization

For high-performance scenarios:
```bash
# Optimized for minimal overhead
claude-mpm run-guarded \
  --memory-threshold 20000 \
  --check-interval 120 \
  --no-state-preservation \
  --quiet
```

For development scenarios:
```bash
# Optimized for quick feedback
claude-mpm run-guarded \
  --memory-threshold 8000 \
  --check-interval 10 \
  --show-stats \
  --verbose
```

## Best Practices

### Threshold Selection

1. **Know Your System**: Start with 70-80% of available RAM
2. **Monitor Patterns**: Observe typical memory usage over time
3. **Adjust Gradually**: Increase thresholds if restarts are too frequent
4. **Consider Workload**: Adjust for data-intensive vs. text-heavy work

### Configuration Management

1. **Use Configuration Files**: For complex setups and team sharing
2. **Version Control**: Include config files in project repositories
3. **Environment-Specific**: Different configs for dev/staging/production
4. **Document Settings**: Explain threshold choices for team members

### Monitoring Strategy

1. **Start Verbose**: Use `--verbose` initially to understand patterns
2. **Reduce Noise**: Switch to `--quiet` for production use
3. **Enable Statistics**: Use `--show-stats` for performance analysis
4. **Log Rotation**: Ensure log files don't grow indefinitely

### State Management

1. **Enable by Default**: State preservation helps maintain productivity
2. **Disable for Speed**: In performance-critical scenarios
3. **Clean Regularly**: Remove old state files periodically
4. **Backup Important States**: For critical long-running sessions

## FAQ

### Q: How do I know what threshold to set?
**A**: Start with 70-80% of your available RAM. Monitor your typical usage patterns with `--show-stats` and adjust accordingly. For a 32GB system, 18-24GB is usually appropriate.

### Q: Will restarts interrupt my work?
**A**: With state preservation enabled, restarts are designed to be minimally disruptive. Your conversation context and working directory are preserved across restarts.

### Q: How often should I expect restarts?
**A**: This depends on your workload. For typical development tasks, you might see a restart every few hours. For data-intensive work, possibly more frequently.

### Q: Can I disable Memory Guardian temporarily?
**A**: Yes, simply use the regular `claude-mpm run` command instead of `run-guarded`.

### Q: Does Memory Guardian work on all platforms?
**A**: Yes, it supports Windows, macOS, and Linux with platform-specific optimizations for each.

### Q: What happens if Memory Guardian fails?
**A**: The system includes failsafes to continue operation even if monitoring fails. Your Claude session continues normally, just without memory protection.

### Q: Can I customize restart behavior?
**A**: Yes, through configuration files you can control restart timing, cooldown periods, and maximum attempts.

### Q: Is there a performance overhead?
**A**: Minimal. Memory checks typically take microseconds and occur every 30 seconds by default. CPU overhead is negligible.

### Q: How do I migrate from regular `run` to `run-guarded`?
**A**: Simply replace `claude-mpm run` with `claude-mpm run-guarded` in your commands. All regular run options are supported.

### Q: Can I use Memory Guardian with existing sessions?
**A**: Memory Guardian starts fresh sessions. To protect existing sessions, you would need to restart with `run-guarded`.