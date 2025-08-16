"""Memory Guardian configuration for managing Claude Code memory usage.

This module provides configuration management for the MemoryGuardian service
that monitors and manages Claude Code subprocess memory consumption.

Design Principles:
- Platform-agnostic configuration with OS-specific overrides
- Environment-based configuration for different deployment scenarios
- Flexible thresholds for memory monitoring
- Support for both psutil and fallback monitoring methods
"""

import os
import platform
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, Optional, List


@dataclass
class MemoryThresholds:
    """Memory threshold configuration in MB."""
    
    # Memory thresholds in MB (defaults for 24GB system)
    warning: int = 12288  # 12GB - Start monitoring closely
    critical: int = 15360  # 15GB - Consider restart
    emergency: int = 18432  # 18GB - Force restart
    
    # Percentage-based thresholds (as fallback when system memory is detected)
    warning_percent: float = 50.0  # 50% of system memory
    critical_percent: float = 65.0  # 65% of system memory
    emergency_percent: float = 75.0  # 75% of system memory
    
    def adjust_for_system_memory(self, total_memory_mb: int) -> None:
        """Adjust thresholds based on available system memory."""
        if total_memory_mb > 0:
            self.warning = int(total_memory_mb * (self.warning_percent / 100))
            self.critical = int(total_memory_mb * (self.critical_percent / 100))
            self.emergency = int(total_memory_mb * (self.emergency_percent / 100))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert thresholds to dictionary."""
        return {
            'warning_mb': self.warning,
            'critical_mb': self.critical,
            'emergency_mb': self.emergency,
            'warning_percent': self.warning_percent,
            'critical_percent': self.critical_percent,
            'emergency_percent': self.emergency_percent
        }


@dataclass
class RestartPolicy:
    """Configuration for process restart behavior."""
    
    # Restart attempts
    max_attempts: int = 3  # Maximum restart attempts before giving up
    attempt_window: int = 3600  # Window in seconds to count attempts (1 hour)
    
    # Cooldown periods
    initial_cooldown: int = 30  # Initial cooldown after restart (seconds)
    max_cooldown: int = 300  # Maximum cooldown period (5 minutes)
    cooldown_multiplier: float = 2.0  # Multiply cooldown on each retry
    
    # Graceful shutdown
    graceful_timeout: int = 30  # Time to wait for graceful shutdown (seconds)
    force_kill_timeout: int = 10  # Time to wait before SIGKILL after SIGTERM
    
    def get_cooldown(self, attempt: int) -> int:
        """Calculate cooldown period for given attempt number."""
        cooldown = self.initial_cooldown * (self.cooldown_multiplier ** (attempt - 1))
        return min(int(cooldown), self.max_cooldown)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert restart policy to dictionary."""
        return {
            'max_attempts': self.max_attempts,
            'attempt_window': self.attempt_window,
            'initial_cooldown': self.initial_cooldown,
            'max_cooldown': self.max_cooldown,
            'cooldown_multiplier': self.cooldown_multiplier,
            'graceful_timeout': self.graceful_timeout,
            'force_kill_timeout': self.force_kill_timeout
        }


@dataclass
class MonitoringConfig:
    """Configuration for memory monitoring behavior."""
    
    # Check intervals (seconds)
    normal_interval: int = 30  # Normal check interval
    warning_interval: int = 15  # Check interval when in warning state
    critical_interval: int = 5  # Check interval when in critical state
    
    # Monitoring method preferences
    prefer_psutil: bool = True  # Prefer psutil if available
    fallback_methods: List[str] = field(default_factory=lambda: [
        'platform_specific',  # Use OS-specific commands
        'resource_module',    # Use resource module as last resort
    ])
    
    # Logging and reporting
    log_memory_stats: bool = True  # Log memory statistics
    log_interval: int = 300  # Log summary every 5 minutes
    detailed_logging: bool = False  # Enable detailed debug logging
    
    def get_check_interval(self, memory_state: str) -> int:
        """Get check interval based on current memory state."""
        if memory_state == 'critical':
            return self.critical_interval
        elif memory_state == 'warning':
            return self.warning_interval
        else:
            return self.normal_interval
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert monitoring config to dictionary."""
        return {
            'normal_interval': self.normal_interval,
            'warning_interval': self.warning_interval,
            'critical_interval': self.critical_interval,
            'prefer_psutil': self.prefer_psutil,
            'fallback_methods': self.fallback_methods,
            'log_memory_stats': self.log_memory_stats,
            'log_interval': self.log_interval,
            'detailed_logging': self.detailed_logging
        }


@dataclass
class PlatformOverrides:
    """Platform-specific configuration overrides."""
    
    # macOS specific
    macos_use_activity_monitor: bool = False  # Use Activity Monitor data if available
    macos_memory_pressure_check: bool = True  # Check system memory pressure
    
    # Linux specific
    linux_use_proc: bool = True  # Use /proc filesystem
    linux_check_oom_score: bool = True  # Monitor OOM killer score
    
    # Windows specific
    windows_use_wmi: bool = True  # Use WMI for monitoring
    windows_use_performance_counter: bool = False  # Use performance counters
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert platform overrides to dictionary."""
        return {
            'macos_use_activity_monitor': self.macos_use_activity_monitor,
            'macos_memory_pressure_check': self.macos_memory_pressure_check,
            'linux_use_proc': self.linux_use_proc,
            'linux_check_oom_score': self.linux_check_oom_score,
            'windows_use_wmi': self.windows_use_wmi,
            'windows_use_performance_counter': self.windows_use_performance_counter
        }


@dataclass
class MemoryGuardianConfig:
    """Complete configuration for MemoryGuardian service."""
    
    # Core configurations
    thresholds: MemoryThresholds = field(default_factory=MemoryThresholds)
    restart_policy: RestartPolicy = field(default_factory=RestartPolicy)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    platform_overrides: PlatformOverrides = field(default_factory=PlatformOverrides)
    
    # Process configuration
    process_command: List[str] = field(default_factory=lambda: ['claude-code'])
    process_args: List[str] = field(default_factory=list)
    process_env: Dict[str, str] = field(default_factory=dict)
    working_directory: Optional[str] = None
    
    # Service configuration
    enabled: bool = True  # Enable memory guardian
    auto_start: bool = True  # Auto-start monitored process
    persist_state: bool = True  # Persist state across restarts
    state_file: Optional[str] = None  # State file path
    
    @classmethod
    def from_env(cls) -> 'MemoryGuardianConfig':
        """Create configuration from environment variables."""
        config = cls()
        
        # Memory thresholds
        if warning := os.getenv('CLAUDE_MPM_MEMORY_WARNING_MB'):
            config.thresholds.warning = int(warning)
        if critical := os.getenv('CLAUDE_MPM_MEMORY_CRITICAL_MB'):
            config.thresholds.critical = int(critical)
        if emergency := os.getenv('CLAUDE_MPM_MEMORY_EMERGENCY_MB'):
            config.thresholds.emergency = int(emergency)
        
        # Restart policy
        if max_attempts := os.getenv('CLAUDE_MPM_RESTART_MAX_ATTEMPTS'):
            config.restart_policy.max_attempts = int(max_attempts)
        if cooldown := os.getenv('CLAUDE_MPM_RESTART_COOLDOWN'):
            config.restart_policy.initial_cooldown = int(cooldown)
        
        # Monitoring intervals
        if interval := os.getenv('CLAUDE_MPM_MONITOR_INTERVAL'):
            config.monitoring.normal_interval = int(interval)
        if log_interval := os.getenv('CLAUDE_MPM_LOG_INTERVAL'):
            config.monitoring.log_interval = int(log_interval)
        
        # Service settings
        config.enabled = os.getenv('CLAUDE_MPM_MEMORY_GUARDIAN_ENABLED', 'true').lower() == 'true'
        config.auto_start = os.getenv('CLAUDE_MPM_AUTO_START', 'true').lower() == 'true'
        
        # Process command
        if command := os.getenv('CLAUDE_MPM_PROCESS_COMMAND'):
            config.process_command = command.split()
        
        return config
    
    @classmethod
    def for_development(cls) -> 'MemoryGuardianConfig':
        """Configuration optimized for development."""
        config = cls()
        config.thresholds.warning = 8192  # 8GB for dev machines
        config.thresholds.critical = 10240  # 10GB
        config.thresholds.emergency = 12288  # 12GB
        config.monitoring.normal_interval = 60  # Check less frequently
        config.monitoring.detailed_logging = True
        return config
    
    @classmethod
    def for_production(cls) -> 'MemoryGuardianConfig':
        """Configuration optimized for production."""
        config = cls()
        config.monitoring.normal_interval = 30
        config.monitoring.log_memory_stats = True
        config.persist_state = True
        config.restart_policy.max_attempts = 5
        return config
    
    @classmethod
    def for_platform(cls, platform_name: Optional[str] = None) -> 'MemoryGuardianConfig':
        """Get platform-specific configuration."""
        if platform_name is None:
            platform_name = platform.system().lower()
        
        config = cls()
        
        if platform_name == 'darwin':  # macOS
            config.platform_overrides.macos_memory_pressure_check = True
        elif platform_name == 'linux':
            config.platform_overrides.linux_use_proc = True
            config.platform_overrides.linux_check_oom_score = True
        elif platform_name == 'windows':
            config.platform_overrides.windows_use_wmi = True
        
        return config
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            'thresholds': self.thresholds.to_dict(),
            'restart_policy': self.restart_policy.to_dict(),
            'monitoring': self.monitoring.to_dict(),
            'platform_overrides': self.platform_overrides.to_dict(),
            'process_command': self.process_command,
            'process_args': self.process_args,
            'process_env': self.process_env,
            'working_directory': self.working_directory,
            'enabled': self.enabled,
            'auto_start': self.auto_start,
            'persist_state': self.persist_state,
            'state_file': self.state_file
        }
    
    def validate(self) -> List[str]:
        """Validate configuration and return list of issues."""
        issues = []
        
        # Validate thresholds are in correct order
        if self.thresholds.warning >= self.thresholds.critical:
            issues.append("Warning threshold must be less than critical threshold")
        if self.thresholds.critical >= self.thresholds.emergency:
            issues.append("Critical threshold must be less than emergency threshold")
        
        # Validate intervals
        if self.monitoring.normal_interval <= 0:
            issues.append("Normal monitoring interval must be positive")
        if self.monitoring.warning_interval <= 0:
            issues.append("Warning monitoring interval must be positive")
        if self.monitoring.critical_interval <= 0:
            issues.append("Critical monitoring interval must be positive")
        
        # Validate restart policy
        if self.restart_policy.max_attempts < 0:
            issues.append("Max restart attempts cannot be negative")
        if self.restart_policy.initial_cooldown <= 0:
            issues.append("Initial cooldown must be positive")
        
        # Validate process command
        if not self.process_command:
            issues.append("Process command cannot be empty")
        
        return issues


def get_default_config() -> MemoryGuardianConfig:
    """Get default configuration adjusted for current platform."""
    config = MemoryGuardianConfig.for_platform()
    
    # Try to adjust for available system memory
    try:
        import psutil
        total_memory_mb = psutil.virtual_memory().total // (1024 * 1024)
        config.thresholds.adjust_for_system_memory(total_memory_mb)
    except ImportError:
        # psutil not available, use defaults
        pass
    except Exception:
        # Any other error, use defaults
        pass
    
    # Override with environment variables
    env_config = MemoryGuardianConfig.from_env()
    if env_config.enabled != config.enabled:
        config = env_config
    
    return config