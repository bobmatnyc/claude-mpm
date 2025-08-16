"""Restart loop protection service for Memory Guardian.

Implements advanced restart loop detection and prevention with exponential backoff,
circuit breaker patterns, and memory leak detection through trend analysis.
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from collections import deque

from claude_mpm.services.core.base import BaseService


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Failures exceeded, blocking restarts
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class RestartRecord:
    """Record of a restart event."""
    timestamp: float
    reason: str
    memory_mb: float
    success: bool
    backoff_seconds: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'timestamp': self.timestamp,
            'timestamp_iso': datetime.fromtimestamp(self.timestamp).isoformat(),
            'reason': self.reason,
            'memory_mb': self.memory_mb,
            'success': self.success,
            'backoff_seconds': self.backoff_seconds
        }


@dataclass
class MemoryTrend:
    """Memory usage trend analysis."""
    slope: float  # MB per minute
    intercept: float
    r_squared: float  # Correlation coefficient
    samples: int
    timespan_minutes: float
    
    @property
    def is_leak_suspected(self) -> bool:
        """Check if memory leak is suspected based on trend."""
        # Suspect leak if:
        # 1. Strong positive correlation (r² > 0.7)
        # 2. Growth rate > 10 MB/minute
        # 3. At least 10 samples over 5 minutes
        return (
            self.r_squared > 0.7 and
            self.slope > 10.0 and
            self.samples >= 10 and
            self.timespan_minutes >= 5
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'slope_mb_per_min': round(self.slope, 2),
            'intercept_mb': round(self.intercept, 2),
            'r_squared': round(self.r_squared, 4),
            'samples': self.samples,
            'timespan_minutes': round(self.timespan_minutes, 2),
            'leak_suspected': self.is_leak_suspected
        }


@dataclass
class RestartStatistics:
    """Restart statistics and diagnostics."""
    total_restarts: int = 0
    successful_restarts: int = 0
    failed_restarts: int = 0
    consecutive_failures: int = 0
    last_restart_time: Optional[float] = None
    average_interval_minutes: float = 0.0
    shortest_interval_minutes: float = float('inf')
    memory_trend: Optional[MemoryTrend] = None
    circuit_state: CircuitState = CircuitState.CLOSED
    circuit_trips: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'total_restarts': self.total_restarts,
            'successful_restarts': self.successful_restarts,
            'failed_restarts': self.failed_restarts,
            'success_rate': (self.successful_restarts / self.total_restarts * 100) if self.total_restarts > 0 else 0,
            'consecutive_failures': self.consecutive_failures,
            'last_restart_time': self.last_restart_time,
            'last_restart_iso': datetime.fromtimestamp(self.last_restart_time).isoformat() if self.last_restart_time else None,
            'average_interval_minutes': round(self.average_interval_minutes, 2),
            'shortest_interval_minutes': round(self.shortest_interval_minutes, 2) if self.shortest_interval_minutes != float('inf') else None,
            'memory_trend': self.memory_trend.to_dict() if self.memory_trend else None,
            'circuit_state': self.circuit_state.value,
            'circuit_trips': self.circuit_trips
        }


class RestartProtection(BaseService):
    """Service for preventing restart loops and detecting memory leaks."""
    
    def __init__(
        self,
        max_restarts_per_hour: int = 5,
        max_consecutive_failures: int = 3,
        base_backoff_seconds: int = 1,
        max_backoff_seconds: int = 300,
        circuit_reset_minutes: int = 30,
        memory_sample_window_minutes: int = 10,
        state_file: Optional[Path] = None
    ):
        """Initialize restart protection service.
        
        Args:
            max_restarts_per_hour: Maximum restarts allowed per hour
            max_consecutive_failures: Failures before circuit breaker opens
            base_backoff_seconds: Base exponential backoff time
            max_backoff_seconds: Maximum backoff time
            circuit_reset_minutes: Time before circuit breaker resets
            memory_sample_window_minutes: Window for memory trend analysis
            state_file: Optional file for persisting state
        """
        super().__init__("RestartProtection")
        
        # Configuration
        self.max_restarts_per_hour = max_restarts_per_hour
        self.max_consecutive_failures = max_consecutive_failures
        self.base_backoff_seconds = base_backoff_seconds
        self.max_backoff_seconds = max_backoff_seconds
        self.circuit_reset_minutes = circuit_reset_minutes
        self.memory_sample_window_minutes = memory_sample_window_minutes
        self.state_file = state_file
        
        # State tracking
        self.restart_history: deque = deque(maxlen=100)  # Last 100 restarts
        self.memory_samples: deque = deque(maxlen=1000)  # Last 1000 memory samples
        self.statistics = RestartStatistics()
        
        # Circuit breaker state
        self.circuit_state = CircuitState.CLOSED
        self.circuit_opened_at: Optional[float] = None
        self.circuit_test_allowed_at: Optional[float] = None
        
        # Load persisted state if available
        if self.state_file:
            self._load_state()
        
        self.log_info(
            f"Restart protection initialized: "
            f"max_restarts={max_restarts_per_hour}/hour, "
            f"max_failures={max_consecutive_failures}, "
            f"backoff={base_backoff_seconds}-{max_backoff_seconds}s"
        )
    
    async def initialize(self) -> bool:
        """Initialize the restart protection service.
        
        Returns:
            True if initialization successful
        """
        try:
            self.log_info("Initializing restart protection service")
            
            # Start background analysis task
            asyncio.create_task(self._periodic_analysis())
            
            self._initialized = True
            self.log_info("Restart protection service initialized successfully")
            return True
            
        except Exception as e:
            self.log_error(f"Failed to initialize restart protection: {e}")
            return False
    
    async def shutdown(self) -> None:
        """Shutdown the restart protection service."""
        try:
            self.log_info("Shutting down restart protection service")
            
            # Save state if configured
            if self.state_file:
                self._save_state()
            
            self._shutdown = True
            self.log_info("Restart protection service shutdown complete")
            
        except Exception as e:
            self.log_error(f"Error during restart protection shutdown: {e}")
    
    def should_allow_restart(self, current_memory_mb: float = 0) -> Tuple[bool, str]:
        """Check if restart should be allowed based on protection rules.
        
        Args:
            current_memory_mb: Current memory usage in MB
            
        Returns:
            Tuple of (allowed, reason)
        """
        # Check circuit breaker state
        circuit_check = self._check_circuit_breaker()
        if not circuit_check[0]:
            return circuit_check
        
        # Check restart frequency
        frequency_check = self._check_restart_frequency()
        if not frequency_check[0]:
            return frequency_check
        
        # Check for memory leak pattern
        if current_memory_mb > 0:
            leak_check = self._check_memory_leak_pattern(current_memory_mb)
            if not leak_check[0]:
                return leak_check
        
        # Check consecutive failures
        if self.statistics.consecutive_failures >= self.max_consecutive_failures:
            return False, f"Too many consecutive failures ({self.statistics.consecutive_failures})"
        
        return True, "Restart allowed"
    
    def record_restart(
        self,
        reason: str,
        memory_mb: float,
        success: bool,
        backoff_applied: float = 0
    ) -> None:
        """Record a restart event.
        
        Args:
            reason: Reason for restart
            memory_mb: Memory usage at restart
            success: Whether restart was successful
            backoff_applied: Backoff time applied (seconds)
        """
        record = RestartRecord(
            timestamp=time.time(),
            reason=reason,
            memory_mb=memory_mb,
            success=success,
            backoff_seconds=backoff_applied
        )
        
        self.restart_history.append(record)
        
        # Update statistics
        self.statistics.total_restarts += 1
        if success:
            self.statistics.successful_restarts += 1
            self.statistics.consecutive_failures = 0
            
            # Update circuit breaker state if in half-open
            if self.circuit_state == CircuitState.HALF_OPEN:
                self._close_circuit_breaker()
        else:
            self.statistics.failed_restarts += 1
            self.statistics.consecutive_failures += 1
            
            # Check if circuit breaker should trip
            if self.statistics.consecutive_failures >= self.max_consecutive_failures:
                self._open_circuit_breaker()
        
        self.statistics.last_restart_time = record.timestamp
        
        # Update interval statistics
        self._update_interval_statistics()
        
        # Add memory sample
        self.record_memory_sample(memory_mb)
        
        self.log_info(
            f"Restart recorded: {reason}, "
            f"memory={memory_mb:.2f}MB, "
            f"success={success}, "
            f"consecutive_failures={self.statistics.consecutive_failures}"
        )
    
    def record_memory_sample(self, memory_mb: float) -> None:
        """Record a memory usage sample for trend analysis.
        
        Args:
            memory_mb: Memory usage in MB
        """
        self.memory_samples.append({
            'timestamp': time.time(),
            'memory_mb': memory_mb
        })
    
    def detect_memory_leak(self) -> Optional[MemoryTrend]:
        """Analyze memory trends to detect potential leaks.
        
        Returns:
            MemoryTrend if analysis possible, None otherwise
        """
        if len(self.memory_samples) < 10:
            return None
        
        # Get samples within analysis window
        cutoff_time = time.time() - (self.memory_sample_window_minutes * 60)
        recent_samples = [
            s for s in self.memory_samples
            if s['timestamp'] >= cutoff_time
        ]
        
        if len(recent_samples) < 10:
            return None
        
        # Perform linear regression to detect trend
        trend = self._calculate_memory_trend(recent_samples)
        
        # Update statistics
        self.statistics.memory_trend = trend
        
        if trend.is_leak_suspected:
            self.log_warning(
                f"Memory leak suspected: "
                f"growth rate={trend.slope:.2f}MB/min, "
                f"correlation={trend.r_squared:.3f}"
            )
        
        return trend
    
    def get_restart_statistics(self) -> RestartStatistics:
        """Get comprehensive restart statistics.
        
        Returns:
            RestartStatistics object
        """
        # Update memory trend
        self.detect_memory_leak()
        
        return self.statistics
    
    def get_backoff_seconds(self, attempt: int) -> float:
        """Calculate exponential backoff time for restart attempt.
        
        Args:
            attempt: Attempt number (1-based)
            
        Returns:
            Backoff time in seconds
        """
        # Exponential backoff: base * 2^(attempt-1)
        backoff = self.base_backoff_seconds * (2 ** (attempt - 1))
        
        # Apply maximum limit
        backoff = min(backoff, self.max_backoff_seconds)
        
        # Add jitter (±10%) to prevent thundering herd
        import random
        jitter = backoff * 0.1 * (2 * random.random() - 1)
        backoff += jitter
        
        return max(0, backoff)
    
    def reset_circuit_breaker(self) -> bool:
        """Manually reset the circuit breaker.
        
        Returns:
            True if reset successful
        """
        if self.circuit_state == CircuitState.CLOSED:
            self.log_info("Circuit breaker is already closed")
            return True
        
        self.log_info("Manually resetting circuit breaker")
        self._close_circuit_breaker()
        
        # Reset consecutive failures
        self.statistics.consecutive_failures = 0
        
        return True
    
    def _check_circuit_breaker(self) -> Tuple[bool, str]:
        """Check circuit breaker state.
        
        Returns:
            Tuple of (allowed, reason)
        """
        if self.circuit_state == CircuitState.CLOSED:
            return True, "Circuit closed"
        
        if self.circuit_state == CircuitState.OPEN:
            # Check if enough time has passed to test
            if self.circuit_test_allowed_at and time.time() >= self.circuit_test_allowed_at:
                self._half_open_circuit_breaker()
                return True, "Circuit half-open, testing recovery"
            else:
                remaining = self.circuit_test_allowed_at - time.time() if self.circuit_test_allowed_at else 0
                return False, f"Circuit breaker open, reset in {remaining:.0f}s"
        
        if self.circuit_state == CircuitState.HALF_OPEN:
            return True, "Circuit half-open, testing recovery"
        
        return False, "Unknown circuit state"
    
    def _check_restart_frequency(self) -> Tuple[bool, str]:
        """Check if restart frequency is within limits.
        
        Returns:
            Tuple of (allowed, reason)
        """
        # Count restarts in last hour
        hour_ago = time.time() - 3600
        recent_restarts = [
            r for r in self.restart_history
            if r.timestamp >= hour_ago
        ]
        
        if len(recent_restarts) >= self.max_restarts_per_hour:
            return False, f"Too many restarts ({len(recent_restarts)}/{self.max_restarts_per_hour} per hour)"
        
        return True, "Frequency within limits"
    
    def _check_memory_leak_pattern(self, current_memory_mb: float) -> Tuple[bool, str]:
        """Check for memory leak pattern.
        
        Args:
            current_memory_mb: Current memory usage
            
        Returns:
            Tuple of (allowed, reason)
        """
        trend = self.detect_memory_leak()
        
        if trend and trend.is_leak_suspected:
            # Check if memory is still growing
            predicted_memory = trend.slope * (time.time() / 60) + trend.intercept
            if current_memory_mb > predicted_memory * 1.1:  # 10% above prediction
                return False, f"Memory leak detected (growth: {trend.slope:.2f}MB/min)"
        
        return True, "No memory leak detected"
    
    def _open_circuit_breaker(self) -> None:
        """Open the circuit breaker."""
        self.circuit_state = CircuitState.OPEN
        self.circuit_opened_at = time.time()
        self.circuit_test_allowed_at = time.time() + (self.circuit_reset_minutes * 60)
        self.statistics.circuit_state = CircuitState.OPEN
        self.statistics.circuit_trips += 1
        
        self.log_warning(
            f"Circuit breaker opened after {self.statistics.consecutive_failures} failures, "
            f"will test recovery in {self.circuit_reset_minutes} minutes"
        )
    
    def _half_open_circuit_breaker(self) -> None:
        """Move circuit breaker to half-open state."""
        self.circuit_state = CircuitState.HALF_OPEN
        self.statistics.circuit_state = CircuitState.HALF_OPEN
        
        self.log_info("Circuit breaker moved to half-open state for testing")
    
    def _close_circuit_breaker(self) -> None:
        """Close the circuit breaker."""
        self.circuit_state = CircuitState.CLOSED
        self.circuit_opened_at = None
        self.circuit_test_allowed_at = None
        self.statistics.circuit_state = CircuitState.CLOSED
        
        self.log_info("Circuit breaker closed, normal operation resumed")
    
    def _update_interval_statistics(self) -> None:
        """Update restart interval statistics."""
        if len(self.restart_history) < 2:
            return
        
        # Calculate intervals between restarts
        intervals = []
        for i in range(1, len(self.restart_history)):
            interval = (self.restart_history[i].timestamp - self.restart_history[i-1].timestamp) / 60
            intervals.append(interval)
        
        if intervals:
            self.statistics.average_interval_minutes = sum(intervals) / len(intervals)
            self.statistics.shortest_interval_minutes = min(intervals)
    
    def _calculate_memory_trend(self, samples: List[Dict[str, float]]) -> MemoryTrend:
        """Calculate memory usage trend using linear regression.
        
        Args:
            samples: List of memory samples
            
        Returns:
            MemoryTrend object
        """
        if not samples:
            return MemoryTrend(0, 0, 0, 0, 0)
        
        # Convert timestamps to minutes from first sample
        base_time = samples[0]['timestamp']
        x_values = [(s['timestamp'] - base_time) / 60 for s in samples]
        y_values = [s['memory_mb'] for s in samples]
        
        # Calculate linear regression
        n = len(samples)
        if n < 2:
            return MemoryTrend(0, y_values[0], 0, n, 0)
        
        sum_x = sum(x_values)
        sum_y = sum(y_values)
        sum_xx = sum(x * x for x in x_values)
        sum_xy = sum(x * y for x, y in zip(x_values, y_values))
        sum_yy = sum(y * y for y in y_values)
        
        # Calculate slope and intercept
        denominator = n * sum_xx - sum_x * sum_x
        if abs(denominator) < 1e-10:
            # All x values are the same
            return MemoryTrend(0, sum_y / n, 0, n, 0)
        
        slope = (n * sum_xy - sum_x * sum_y) / denominator
        intercept = (sum_y - slope * sum_x) / n
        
        # Calculate R-squared
        y_mean = sum_y / n
        ss_tot = sum((y - y_mean) ** 2 for y in y_values)
        
        if ss_tot < 1e-10:
            # No variance in y values
            r_squared = 1.0
        else:
            ss_res = sum((y - (slope * x + intercept)) ** 2 for x, y in zip(x_values, y_values))
            r_squared = 1 - (ss_res / ss_tot)
        
        timespan = x_values[-1] - x_values[0] if len(x_values) > 1 else 0
        
        return MemoryTrend(
            slope=slope,
            intercept=intercept,
            r_squared=max(0, min(1, r_squared)),
            samples=n,
            timespan_minutes=timespan
        )
    
    async def _periodic_analysis(self) -> None:
        """Periodic background analysis task."""
        while not self._shutdown:
            try:
                # Detect memory leaks periodically
                self.detect_memory_leak()
                
                # Check circuit breaker timeout
                if self.circuit_state == CircuitState.OPEN:
                    if self.circuit_test_allowed_at and time.time() >= self.circuit_test_allowed_at:
                        self._half_open_circuit_breaker()
                
                # Save state periodically
                if self.state_file:
                    self._save_state()
                
                await asyncio.sleep(60)  # Run every minute
                
            except Exception as e:
                self.log_error(f"Error in periodic analysis: {e}")
                await asyncio.sleep(60)
    
    def _save_state(self) -> None:
        """Save service state to file."""
        if not self.state_file:
            return
        
        try:
            state = {
                'restart_history': [r.to_dict() for r in self.restart_history],
                'memory_samples': list(self.memory_samples)[-100:],  # Save last 100
                'statistics': self.statistics.to_dict(),
                'circuit_state': self.circuit_state.value,
                'circuit_opened_at': self.circuit_opened_at,
                'circuit_test_allowed_at': self.circuit_test_allowed_at
            }
            
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)
            
            self.log_debug(f"Saved restart protection state to {self.state_file}")
            
        except Exception as e:
            self.log_error(f"Failed to save state: {e}")
    
    def _load_state(self) -> None:
        """Load service state from file."""
        if not self.state_file or not self.state_file.exists():
            return
        
        try:
            with open(self.state_file, 'r') as f:
                state = json.load(f)
            
            # Restore restart history
            for record_data in state.get('restart_history', []):
                record = RestartRecord(
                    timestamp=record_data['timestamp'],
                    reason=record_data['reason'],
                    memory_mb=record_data['memory_mb'],
                    success=record_data['success'],
                    backoff_seconds=record_data.get('backoff_seconds', 0)
                )
                self.restart_history.append(record)
            
            # Restore memory samples
            for sample in state.get('memory_samples', []):
                self.memory_samples.append(sample)
            
            # Restore statistics
            stats_data = state.get('statistics', {})
            self.statistics.total_restarts = stats_data.get('total_restarts', 0)
            self.statistics.successful_restarts = stats_data.get('successful_restarts', 0)
            self.statistics.failed_restarts = stats_data.get('failed_restarts', 0)
            self.statistics.consecutive_failures = stats_data.get('consecutive_failures', 0)
            self.statistics.last_restart_time = stats_data.get('last_restart_time')
            self.statistics.circuit_trips = stats_data.get('circuit_trips', 0)
            
            # Restore circuit breaker state
            circuit_state_value = state.get('circuit_state', 'closed')
            self.circuit_state = CircuitState(circuit_state_value)
            self.statistics.circuit_state = self.circuit_state
            self.circuit_opened_at = state.get('circuit_opened_at')
            self.circuit_test_allowed_at = state.get('circuit_test_allowed_at')
            
            self.log_info(f"Loaded restart protection state from {self.state_file}")
            
        except Exception as e:
            self.log_error(f"Failed to load state: {e}")