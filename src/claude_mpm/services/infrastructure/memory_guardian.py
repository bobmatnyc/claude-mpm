"""Memory Guardian service for monitoring and managing Claude Code memory usage.

This service monitors a subprocess (Claude Code) for memory consumption and
performs automatic restarts when memory thresholds are exceeded.

Design Principles:
- Subprocess lifecycle management with graceful shutdown
- Multi-threshold memory monitoring (warning, critical, emergency)
- Platform-agnostic memory monitoring with fallbacks
- Configurable restart policies with cooldown periods
- State preservation hooks for future enhancement
"""

import asyncio
import json
import logging
import os
import platform
import signal
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Optional, Dict, Any, List, Callable, Tuple

from claude_mpm.services.core.base import BaseService
from claude_mpm.config.memory_guardian_config import (
    MemoryGuardianConfig,
    get_default_config
)
from claude_mpm.utils.platform_memory import (
    get_process_memory,
    get_system_memory,
    check_memory_pressure,
    MemoryInfo
)
from claude_mpm.services.infrastructure.state_manager import StateManager
from claude_mpm.services.infrastructure.restart_protection import RestartProtection
from claude_mpm.services.infrastructure.health_monitor import HealthMonitor
from claude_mpm.services.infrastructure.graceful_degradation import GracefulDegradation


class MemoryState(Enum):
    """Memory usage state levels."""
    NORMAL = "normal"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class ProcessState(Enum):
    """Process lifecycle states."""
    NOT_STARTED = "not_started"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    RESTARTING = "restarting"
    FAILED = "failed"


@dataclass
class RestartAttempt:
    """Record of a restart attempt."""
    timestamp: float
    reason: str
    memory_mb: float
    success: bool
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'timestamp': self.timestamp,
            'timestamp_iso': datetime.fromtimestamp(self.timestamp).isoformat(),
            'reason': self.reason,
            'memory_mb': self.memory_mb,
            'success': self.success
        }


@dataclass
class MemoryStats:
    """Memory usage statistics."""
    current_mb: float = 0.0
    peak_mb: float = 0.0
    average_mb: float = 0.0
    samples: int = 0
    last_check: float = 0.0
    state: MemoryState = MemoryState.NORMAL
    
    def update(self, memory_mb: float) -> None:
        """Update statistics with new memory reading."""
        self.current_mb = memory_mb
        self.peak_mb = max(self.peak_mb, memory_mb)
        
        # Update running average
        if self.samples == 0:
            self.average_mb = memory_mb
        else:
            self.average_mb = ((self.average_mb * self.samples) + memory_mb) / (self.samples + 1)
        
        self.samples += 1
        self.last_check = time.time()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'current_mb': round(self.current_mb, 2),
            'peak_mb': round(self.peak_mb, 2),
            'average_mb': round(self.average_mb, 2),
            'samples': self.samples,
            'last_check': self.last_check,
            'last_check_iso': datetime.fromtimestamp(self.last_check).isoformat() if self.last_check > 0 else None,
            'state': self.state.value
        }


class MemoryGuardian(BaseService):
    """Service for monitoring and managing subprocess memory usage."""
    
    def __init__(self, config: Optional[MemoryGuardianConfig] = None):
        """Initialize Memory Guardian service.
        
        Args:
            config: Configuration for memory monitoring and management
        """
        super().__init__("MemoryGuardian")
        
        # Configuration
        self.config = config or get_default_config()
        
        # Validate configuration
        issues = self.config.validate()
        if issues:
            for issue in issues:
                self.log_warning(f"Configuration issue: {issue}")
        
        # Process management
        self.process: Optional[subprocess.Popen] = None
        self.process_state = ProcessState.NOT_STARTED
        self.process_pid: Optional[int] = None
        
        # Memory monitoring
        self.memory_stats = MemoryStats()
        self.memory_state = MemoryState.NORMAL
        
        # Restart tracking
        self.restart_attempts: List[RestartAttempt] = []
        self.last_restart_time: float = 0.0
        self.consecutive_failures: int = 0
        
        # Monitoring tasks
        self.monitor_task: Optional[asyncio.Task] = None
        self.monitoring = False
        
        # State preservation hooks (for future implementation)
        self.state_save_hooks: List[Callable[[Dict[str, Any]], None]] = []
        self.state_restore_hooks: List[Callable[[Dict[str, Any]], None]] = []
        
        # State manager integration
        self.state_manager: Optional[StateManager] = None
        
        # Safety services integration
        self.restart_protection: Optional[RestartProtection] = None
        self.health_monitor: Optional[HealthMonitor] = None
        self.graceful_degradation: Optional[GracefulDegradation] = None
        
        # Statistics
        self.start_time = time.time()
        self.total_restarts = 0
        self.total_uptime = 0.0
        
        self.log_info(f"Memory Guardian initialized with thresholds: "
                     f"Warning={self.config.thresholds.warning}MB, "
                     f"Critical={self.config.thresholds.critical}MB, "
                     f"Emergency={self.config.thresholds.emergency}MB")
    
    async def initialize(self) -> bool:
        """Initialize the Memory Guardian service.
        
        Returns:
            True if initialization successful
        """
        try:
            self.log_info("Initializing Memory Guardian service")
            
            # Initialize state manager
            self.state_manager = StateManager()
            await self.state_manager.initialize()
            
            # Initialize safety services
            await self._initialize_safety_services()
            
            # Load persisted state if available
            if self.config.persist_state and self.config.state_file:
                self._load_state()
            
            # Auto-start process if configured
            if self.config.auto_start and self.config.enabled:
                self.log_info("Auto-starting monitored process")
                success = await self.start_process()
                if not success:
                    self.log_warning("Failed to auto-start process")
            
            # Start monitoring if enabled
            if self.config.enabled:
                self.start_monitoring()
            
            self._initialized = True
            self.log_info("Memory Guardian service initialized successfully")
            return True
            
        except Exception as e:
            self.log_error(f"Failed to initialize Memory Guardian: {e}")
            return False
    
    async def shutdown(self) -> None:
        """Shutdown the Memory Guardian service gracefully."""
        try:
            self.log_info("Shutting down Memory Guardian service")
            
            # Stop monitoring
            await self.stop_monitoring()
            
            # Save state if configured
            if self.config.persist_state and self.config.state_file:
                self._save_state()
            
            # Shutdown state manager
            if self.state_manager:
                await self.state_manager.shutdown()
            
            # Shutdown safety services
            if self.restart_protection:
                await self.restart_protection.shutdown()
            if self.health_monitor:
                await self.health_monitor.shutdown()
            if self.graceful_degradation:
                await self.graceful_degradation.shutdown()
            
            # Terminate process if running
            if self.process and self.process_state == ProcessState.RUNNING:
                await self.terminate_process()
            
            self._shutdown = True
            self.log_info("Memory Guardian service shutdown complete")
            
        except Exception as e:
            self.log_error(f"Error during Memory Guardian shutdown: {e}")
    
    async def start_process(self) -> bool:
        """Start the monitored subprocess.
        
        Returns:
            True if process started successfully
        """
        if self.process and self.process_state == ProcessState.RUNNING:
            self.log_warning("Process is already running")
            return True
        
        try:
            self.log_info(f"Starting process: {' '.join(self.config.process_command)}")
            self.process_state = ProcessState.STARTING
            
            # Prepare environment
            env = os.environ.copy()
            env.update(self.config.process_env)
            
            # Build command
            cmd = self.config.process_command + self.config.process_args
            
            # Start subprocess
            self.process = subprocess.Popen(
                cmd,
                env=env,
                cwd=self.config.working_directory,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True  # Create new process group for clean termination
            )
            
            self.process_pid = self.process.pid
            self.process_state = ProcessState.RUNNING
            
            # Update health monitor with new process
            if self.health_monitor:
                self.health_monitor.set_monitored_process(self.process_pid)
            
            # Reset failure counter on successful start
            self.consecutive_failures = 0
            
            self.log_info(f"Process started successfully with PID {self.process_pid}")
            
            # Give process time to initialize
            await asyncio.sleep(2)
            
            # Check if process is still running
            if self.process.poll() is not None:
                self.log_error(f"Process exited immediately with code {self.process.returncode}")
                self.process_state = ProcessState.FAILED
                return False
            
            return True
            
        except FileNotFoundError:
            self.log_error(f"Command not found: {self.config.process_command[0]}")
            self.process_state = ProcessState.FAILED
            return False
        except Exception as e:
            self.log_error(f"Failed to start process: {e}")
            self.process_state = ProcessState.FAILED
            return False
    
    async def restart_process(self, reason: str = "Manual restart") -> bool:
        """Restart the monitored process with cooldown and retry logic.
        
        Args:
            reason: Reason for restart
            
        Returns:
            True if restart successful
        """
        self.log_info(f"Initiating process restart: {reason}")
        
        # Use restart protection if available
        if self.restart_protection:
            allowed, protection_reason = self.restart_protection.should_allow_restart(
                self.memory_stats.current_mb
            )
            if not allowed:
                self.log_error(f"Restart blocked by protection: {protection_reason}")
                
                # Trigger graceful degradation if available
                if self.graceful_degradation:
                    await self.graceful_degradation.disable_feature(
                        "automated_monitoring",
                        f"Restart protection triggered: {protection_reason}"
                    )
                
                self.process_state = ProcessState.FAILED
                return False
            
            # Get backoff from restart protection
            backoff = self.restart_protection.get_backoff_seconds(
                self.restart_protection.statistics.consecutive_failures + 1
            )
            if backoff > 0:
                self.log_info(f"Applying restart backoff of {backoff:.1f} seconds")
                await asyncio.sleep(backoff)
        else:
            # Fallback to original logic
            if not self._can_restart():
                self.log_error("Maximum restart attempts exceeded")
                self.process_state = ProcessState.FAILED
                return False
            
            # Apply cooldown if needed
            cooldown = self._get_restart_cooldown()
            if cooldown > 0:
                self.log_info(f"Applying restart cooldown of {cooldown} seconds")
                await asyncio.sleep(cooldown)
        
        # Record restart attempt
        memory_mb = self.memory_stats.current_mb
        self.process_state = ProcessState.RESTARTING
        
        # Save state before restart using StateManager
        if self.state_manager:
            state = await self.state_manager.capture_state(restart_reason=reason)
            if state:
                await self.state_manager.persist_state(state)
        else:
            # Fallback to hook-based preservation
            await self._trigger_state_save()
        
        # Terminate existing process
        if self.process:
            await self.terminate_process()
        
        # Start new process
        success = await self.start_process()
        
        # Record attempt
        attempt = RestartAttempt(
            timestamp=time.time(),
            reason=reason,
            memory_mb=memory_mb,
            success=success
        )
        self.restart_attempts.append(attempt)
        
        # Record in restart protection service
        if self.restart_protection:
            backoff_applied = self.restart_protection.get_backoff_seconds(
                self.restart_protection.statistics.consecutive_failures + 1
            ) if not success else 0
            self.restart_protection.record_restart(
                reason=reason,
                memory_mb=memory_mb,
                success=success,
                backoff_applied=backoff_applied
            )
        
        if success:
            self.total_restarts += 1
            self.last_restart_time = time.time()
            self.log_info("Process restarted successfully")
            
            # Restore state after restart using StateManager
            if self.state_manager:
                await self.state_manager.restore_state()
            else:
                # Fallback to hook-based restoration
                await self._trigger_state_restore()
        else:
            self.consecutive_failures += 1
            self.log_error("Process restart failed")
        
        return success
    
    async def terminate_process(self, timeout: Optional[int] = None) -> bool:
        """Terminate the monitored process gracefully with escalation.
        
        Args:
            timeout: Override timeout for graceful shutdown
            
        Returns:
            True if process terminated successfully
        """
        if not self.process:
            return True
        
        timeout = timeout or self.config.restart_policy.graceful_timeout
        
        try:
            self.log_info(f"Terminating process {self.process_pid}")
            self.process_state = ProcessState.STOPPING
            
            # Try graceful termination first (SIGTERM)
            if platform.system() != 'Windows':
                self.process.terminate()
            else:
                # On Windows, terminate() is already forceful
                self.process.terminate()
            
            # Wait for graceful shutdown
            try:
                self.log_debug(f"Waiting {timeout}s for graceful shutdown")
                await asyncio.wait_for(
                    asyncio.create_task(self._wait_for_process()),
                    timeout=timeout
                )
                self.log_info("Process terminated gracefully")
                
            except asyncio.TimeoutError:
                # Escalate to SIGKILL
                self.log_warning("Graceful shutdown timeout, forcing termination")
                
                if platform.system() != 'Windows':
                    self.process.kill()
                else:
                    # On Windows, use taskkill /F
                    subprocess.run(
                        ['taskkill', '/F', '/PID', str(self.process_pid)],
                        capture_output=True
                    )
                
                # Wait for forced termination
                try:
                    await asyncio.wait_for(
                        asyncio.create_task(self._wait_for_process()),
                        timeout=self.config.restart_policy.force_kill_timeout
                    )
                    self.log_info("Process terminated forcefully")
                except asyncio.TimeoutError:
                    self.log_error("Failed to terminate process")
                    return False
            
            self.process = None
            self.process_pid = None
            self.process_state = ProcessState.STOPPED
            return True
            
        except Exception as e:
            self.log_error(f"Error terminating process: {e}")
            return False
    
    async def _wait_for_process(self) -> None:
        """Wait for process to exit."""
        while self.process and self.process.poll() is None:
            await asyncio.sleep(0.1)
    
    def get_memory_usage(self) -> Optional[float]:
        """Get current memory usage of monitored process in MB.
        
        Returns:
            Memory usage in MB or None if unable to determine
        """
        if not self.process or self.process_state != ProcessState.RUNNING:
            return None
        
        try:
            # Get memory info using platform utilities
            mem_info = get_process_memory(self.process_pid)
            if mem_info:
                return mem_info.rss_mb
            
            self.log_warning(f"Unable to get memory info for PID {self.process_pid}")
            return None
            
        except Exception as e:
            self.log_error(f"Error getting memory usage: {e}")
            return None
    
    async def monitor_memory(self) -> None:
        """Check memory usage and take action if thresholds exceeded."""
        if not self.process or self.process_state != ProcessState.RUNNING:
            return
        
        # Check if process is still alive
        if self.process.poll() is not None:
            self.log_warning(f"Process exited with code {self.process.returncode}")
            self.process_state = ProcessState.STOPPED
            self.process = None
            self.process_pid = None
            
            # Auto-restart if configured
            if self.config.auto_start:
                await self.restart_process("Process exited unexpectedly")
            return
        
        # Get memory usage
        memory_mb = self.get_memory_usage()
        if memory_mb is None:
            return
        
        # Update statistics
        self.memory_stats.update(memory_mb)
        
        # Record memory sample for trend analysis
        if self.restart_protection:
            self.restart_protection.record_memory_sample(memory_mb)
        
        # Determine memory state
        old_state = self.memory_state
        
        if memory_mb >= self.config.thresholds.emergency:
            self.memory_state = MemoryState.EMERGENCY
        elif memory_mb >= self.config.thresholds.critical:
            self.memory_state = MemoryState.CRITICAL
        elif memory_mb >= self.config.thresholds.warning:
            self.memory_state = MemoryState.WARNING
        else:
            self.memory_state = MemoryState.NORMAL
        
        self.memory_stats.state = self.memory_state
        
        # Log state changes
        if self.memory_state != old_state:
            self.log_info(f"Memory state changed: {old_state.value} -> {self.memory_state.value} "
                         f"(current: {memory_mb:.2f}MB)")
        
        # Take action based on state
        if self.memory_state == MemoryState.EMERGENCY:
            self.log_critical(f"Emergency memory threshold exceeded: {memory_mb:.2f}MB")
            await self.restart_process(f"Emergency memory threshold exceeded ({memory_mb:.2f}MB)")
            
        elif self.memory_state == MemoryState.CRITICAL:
            self.log_warning(f"Critical memory threshold exceeded: {memory_mb:.2f}MB")
            # Check if we've been in critical state for too long
            if self._should_restart_for_critical():
                await self.restart_process(f"Sustained critical memory usage ({memory_mb:.2f}MB)")
        
        elif self.memory_state == MemoryState.WARNING:
            self.log_debug(f"Warning memory threshold exceeded: {memory_mb:.2f}MB")
        
        # Log periodic summary
        if self.config.monitoring.log_memory_stats:
            if time.time() - self.memory_stats.last_check > self.config.monitoring.log_interval:
                self._log_memory_summary()
    
    def start_monitoring(self) -> None:
        """Start continuous memory monitoring."""
        if self.monitoring:
            self.log_warning("Monitoring is already active")
            return
        
        self.monitoring = True
        self.monitor_task = asyncio.create_task(self._monitoring_loop())
        self.log_info("Started memory monitoring")
    
    async def stop_monitoring(self) -> None:
        """Stop continuous memory monitoring."""
        if not self.monitoring:
            return
        
        self.monitoring = False
        
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
            self.monitor_task = None
        
        self.log_info("Stopped memory monitoring")
    
    async def _monitoring_loop(self) -> None:
        """Continuous monitoring loop."""
        try:
            while self.monitoring:
                try:
                    await self.monitor_memory()
                    
                    # Get check interval based on current state
                    interval = self.config.monitoring.get_check_interval(
                        self.memory_state.value
                    )
                    
                    await asyncio.sleep(interval)
                    
                except Exception as e:
                    self.log_error(f"Error in monitoring loop: {e}")
                    await asyncio.sleep(5)  # Brief pause before retry
                    
        except asyncio.CancelledError:
            self.log_debug("Monitoring loop cancelled")
    
    def _can_restart(self) -> bool:
        """Check if restart is allowed based on policy.
        
        Returns:
            True if restart is allowed
        """
        # Check max attempts
        if self.config.restart_policy.max_attempts <= 0:
            return True  # Unlimited restarts
        
        # Count recent attempts
        window_start = time.time() - self.config.restart_policy.attempt_window
        recent_attempts = [
            a for a in self.restart_attempts
            if a.timestamp >= window_start
        ]
        
        return len(recent_attempts) < self.config.restart_policy.max_attempts
    
    def _get_restart_cooldown(self) -> int:
        """Get cooldown period for next restart.
        
        Returns:
            Cooldown period in seconds
        """
        if not self.restart_attempts:
            return 0
        
        # Calculate based on consecutive failures
        return self.config.restart_policy.get_cooldown(self.consecutive_failures + 1)
    
    def _should_restart_for_critical(self) -> bool:
        """Determine if we should restart due to sustained critical memory.
        
        Returns:
            True if restart should be triggered
        """
        # Check how long we've been in critical state
        critical_duration = 60  # seconds
        
        # Look at recent memory samples
        recent_samples = [
            s for s in self.restart_attempts
            if s.timestamp >= time.time() - critical_duration
        ]
        
        # If we've been critical for the duration, restart
        # This is a simplified check - could be enhanced
        return self.memory_state == MemoryState.CRITICAL and len(recent_samples) == 0
    
    async def _trigger_state_save(self) -> None:
        """Trigger state preservation hooks."""
        if not self.state_save_hooks:
            return
        
        state = self.get_state()
        
        for hook in self.state_save_hooks:
            try:
                hook(state)
            except Exception as e:
                self.log_error(f"State save hook failed: {e}")
    
    async def _trigger_state_restore(self) -> None:
        """Trigger state restoration hooks."""
        if not self.state_restore_hooks:
            return
        
        state = self.get_state()
        
        for hook in self.state_restore_hooks:
            try:
                hook(state)
            except Exception as e:
                self.log_error(f"State restore hook failed: {e}")
    
    def _log_memory_summary(self) -> None:
        """Log memory usage summary."""
        uptime = time.time() - self.start_time
        
        self.log_info(
            f"Memory Summary - "
            f"Current: {self.memory_stats.current_mb:.2f}MB, "
            f"Peak: {self.memory_stats.peak_mb:.2f}MB, "
            f"Average: {self.memory_stats.average_mb:.2f}MB, "
            f"State: {self.memory_state.value}, "
            f"Restarts: {self.total_restarts}, "
            f"Uptime: {uptime/3600:.2f}h"
        )
    
    def _save_state(self) -> None:
        """Save service state to file."""
        if not self.config.state_file:
            return
        
        try:
            state = self.get_state()
            state_path = Path(self.config.state_file)
            state_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(state_path, 'w') as f:
                json.dump(state, f, indent=2)
            
            self.log_debug(f"Saved state to {state_path}")
            
        except Exception as e:
            self.log_error(f"Failed to save state: {e}")
    
    def _load_state(self) -> None:
        """Load service state from file."""
        if not self.config.state_file:
            return
        
        try:
            state_path = Path(self.config.state_file)
            if not state_path.exists():
                return
            
            with open(state_path, 'r') as f:
                state = json.load(f)
            
            # Restore relevant state
            self.total_restarts = state.get('total_restarts', 0)
            self.memory_stats.peak_mb = state.get('memory_stats', {}).get('peak_mb', 0.0)
            
            # Restore restart attempts
            attempts = state.get('restart_attempts', [])
            for attempt_data in attempts:
                attempt = RestartAttempt(
                    timestamp=attempt_data['timestamp'],
                    reason=attempt_data['reason'],
                    memory_mb=attempt_data['memory_mb'],
                    success=attempt_data['success']
                )
                self.restart_attempts.append(attempt)
            
            self.log_debug(f"Loaded state from {state_path}")
            
        except Exception as e:
            self.log_error(f"Failed to load state: {e}")
    
    def add_state_save_hook(self, hook: Callable[[Dict[str, Any]], None]) -> None:
        """Add a hook to be called before process restart.
        
        Args:
            hook: Function to call with current state
        """
        self.state_save_hooks.append(hook)
        self.log_debug(f"Added state save hook: {hook.__name__}")
    
    def add_state_restore_hook(self, hook: Callable[[Dict[str, Any]], None]) -> None:
        """Add a hook to be called after process restart.
        
        Args:
            hook: Function to call with saved state
        """
        self.state_restore_hooks.append(hook)
        self.log_debug(f"Added state restore hook: {hook.__name__}")
    
    def set_state_manager(self, state_manager: StateManager) -> None:
        """Set the state manager for state preservation.
        
        Args:
            state_manager: StateManager instance to use
        """
        self.state_manager = state_manager
        self.log_info("State manager configured for Memory Guardian")
    
    def get_state(self) -> Dict[str, Any]:
        """Get current service state.
        
        Returns:
            Dictionary containing service state
        """
        return {
            'process_state': self.process_state.value,
            'process_pid': self.process_pid,
            'memory_state': self.memory_state.value,
            'memory_stats': self.memory_stats.to_dict(),
            'total_restarts': self.total_restarts,
            'consecutive_failures': self.consecutive_failures,
            'restart_attempts': [a.to_dict() for a in self.restart_attempts[-10:]],  # Last 10
            'config': self.config.to_dict(),
            'start_time': self.start_time,
            'monitoring': self.monitoring
        }
    
    async def _initialize_safety_services(self) -> None:
        """Initialize safety and protection services."""
        try:
            # Initialize restart protection
            self.restart_protection = RestartProtection(
                max_restarts_per_hour=5,
                max_consecutive_failures=3,
                base_backoff_seconds=1,
                max_backoff_seconds=60,
                state_file=Path(self.config.state_file).parent / "restart_protection.json" if self.config.state_file else None
            )
            await self.restart_protection.initialize()
            self.log_info("Restart protection service initialized")
            
            # Initialize health monitor
            self.health_monitor = HealthMonitor(
                cpu_threshold_percent=80,
                memory_threshold_percent=90,
                disk_threshold_percent=90,
                min_disk_space_gb=1.0,
                check_interval_seconds=30
            )
            await self.health_monitor.initialize()
            self.log_info("Health monitor service initialized")
            
            # Initialize graceful degradation
            self.graceful_degradation = GracefulDegradation(
                enable_notifications=True,
                log_degradation_events=True,
                state_file=Path(self.config.state_file).parent / "degradation.json" if self.config.state_file else None
            )
            await self.graceful_degradation.initialize()
            self.log_info("Graceful degradation service initialized")
            
            # Check initial health
            valid, message = await self.health_monitor.validate_before_start()
            if not valid:
                self.log_warning(f"System health check warning: {message}")
                await self.graceful_degradation.degrade_feature(
                    "automated_monitoring",
                    message,
                    "reduced monitoring frequency"
                )
            
        except Exception as e:
            self.log_error(f"Failed to initialize safety services: {e}")
            # Continue without safety services - graceful degradation
            self.log_warning("Continuing without safety services")
    
    def set_restart_protection(self, restart_protection: RestartProtection) -> None:
        """Set the restart protection service.
        
        Args:
            restart_protection: RestartProtection instance to use
        """
        self.restart_protection = restart_protection
        self.log_info("Restart protection configured for Memory Guardian")
    
    def set_health_monitor(self, health_monitor: HealthMonitor) -> None:
        """Set the health monitor service.
        
        Args:
            health_monitor: HealthMonitor instance to use
        """
        self.health_monitor = health_monitor
        if self.process_pid:
            self.health_monitor.set_monitored_process(self.process_pid)
        self.log_info("Health monitor configured for Memory Guardian")
    
    def set_graceful_degradation(self, graceful_degradation: GracefulDegradation) -> None:
        """Set the graceful degradation service.
        
        Args:
            graceful_degradation: GracefulDegradation instance to use
        """
        self.graceful_degradation = graceful_degradation
        self.log_info("Graceful degradation configured for Memory Guardian")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current service status.
        
        Returns:
            Dictionary containing service status
        """
        uptime = time.time() - self.start_time if self.process else 0
        
        # Get system memory info
        total_mem, available_mem = get_system_memory()
        
        return {
            'enabled': self.config.enabled,
            'process': {
                'state': self.process_state.value,
                'pid': self.process_pid,
                'uptime_seconds': uptime,
                'uptime_hours': uptime / 3600 if uptime > 0 else 0
            },
            'memory': {
                'current_mb': self.memory_stats.current_mb,
                'peak_mb': self.memory_stats.peak_mb,
                'average_mb': self.memory_stats.average_mb,
                'state': self.memory_state.value,
                'thresholds': {
                    'warning_mb': self.config.thresholds.warning,
                    'critical_mb': self.config.thresholds.critical,
                    'emergency_mb': self.config.thresholds.emergency
                },
                'system': {
                    'total_mb': total_mem / (1024 * 1024) if total_mem > 0 else 0,
                    'available_mb': available_mem / (1024 * 1024) if available_mem > 0 else 0,
                    'pressure': check_memory_pressure()
                }
            },
            'restarts': {
                'total': self.total_restarts,
                'consecutive_failures': self.consecutive_failures,
                'can_restart': self._can_restart(),
                'recent_attempts': [a.to_dict() for a in self.restart_attempts[-5:]]
            },
            'monitoring': {
                'active': self.monitoring,
                'check_interval': self.config.monitoring.get_check_interval(self.memory_state.value),
                'samples': self.memory_stats.samples
            }
        }