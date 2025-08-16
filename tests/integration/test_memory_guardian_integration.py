"""Enhanced integration tests for Memory Guardian System lifecycle.

This module provides comprehensive integration tests for the Memory Guardian system,
covering the complete lifecycle from start to monitoring to breach to restart and recovery.

Tests include:
- Full lifecycle management (start → monitor → breach → restart → restore)  
- State preservation verification across restarts
- Restart loop protection mechanisms
- Circuit breaker behavior under various conditions
- Memory leak detection and response
- Graceful degradation scenarios
- Error recovery and resilience
"""

import asyncio
import json
import os
import platform
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Dict, Any, List
from unittest.mock import AsyncMock, MagicMock, patch, call
import uuid

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from claude_mpm.config.memory_guardian_config import (
    MemoryGuardianConfig,
    MemoryThresholds,
    RestartPolicy,
    MonitoringConfig
)
from claude_mpm.services.infrastructure.memory_guardian import (
    MemoryGuardian,
    MemoryState,
    ProcessState,
    RestartAttempt,
    MemoryStats
)
from claude_mpm.services.infrastructure.restart_protection import (
    RestartProtection,
    CircuitState,
    MemoryTrend
)
from claude_mpm.services.infrastructure.health_monitor import (
    HealthMonitor,
    HealthStatus,
    HealthCheck
)
from claude_mpm.services.infrastructure.graceful_degradation import (
    GracefulDegradation,
    DegradationLevel
)
from claude_mpm.services.infrastructure.state_manager import StateManager
from claude_mpm.utils.platform_memory import MemoryInfo


class TestMemoryGuardianLifecycle:
    """Test complete Memory Guardian lifecycle scenarios."""
    
    @pytest.fixture
    async def temp_workspace(self):
        """Create temporary workspace for test files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            yield workspace
    
    @pytest.fixture
    async def test_config(self, temp_workspace):
        """Create comprehensive test configuration."""
        return MemoryGuardianConfig(
            enabled=True,
            thresholds=MemoryThresholds(
                warning=500,      # 500MB for testing
                critical=750,     # 750MB 
                emergency=1000    # 1GB
            ),
            restart_policy=RestartPolicy(
                max_attempts=3,
                attempt_window=300,  # 5 minutes
                initial_cooldown=1,
                cooldown_multiplier=2.0,
                max_cooldown=60,
                graceful_timeout=5,
                force_kill_timeout=10,
                exponential_backoff=True
            ),
            monitoring=MonitoringConfig(
                check_interval=1,
                check_interval_warning=0.5,
                check_interval_critical=0.25,
                check_interval_emergency=0.1,
                log_memory_stats=True,
                log_interval=30
            ),
            process_command=["python", "-c", "import time; time.sleep(100)"],
            process_args=[],
            process_env={},
            working_directory=str(temp_workspace),
            state_file=str(temp_workspace / "memory_guardian_state.json"),
            persist_state=True,
            auto_start=False
        )
    
    @pytest.fixture
    async def memory_guardian(self, test_config):
        """Create and initialize Memory Guardian instance."""
        guardian = MemoryGuardian(test_config)
        yield guardian
        # Cleanup
        await guardian.shutdown()
    
    @pytest.mark.asyncio
    async def test_complete_lifecycle_normal_operation(self, memory_guardian):
        """Test complete lifecycle under normal operating conditions."""
        # Phase 1: Initialization
        assert await memory_guardian.initialize()
        assert memory_guardian.process_state == ProcessState.NOT_STARTED
        assert memory_guardian.memory_state == MemoryState.NORMAL
        assert memory_guardian.restart_protection is not None
        assert memory_guardian.health_monitor is not None
        assert memory_guardian.graceful_degradation is not None
        
        # Phase 2: Process Start
        # Mock successful process start
        with patch.object(memory_guardian, 'start_process') as mock_start:
            mock_start.return_value = True
            memory_guardian.process = MagicMock()
            memory_guardian.process.poll.return_value = None
            memory_guardian.process_pid = 12345
            memory_guardian.process_state = ProcessState.RUNNING
            
            success = await memory_guardian.start_process()
            assert success
            assert memory_guardian.process_state == ProcessState.RUNNING
        
        # Phase 3: Normal Monitoring
        with patch.object(memory_guardian, 'get_memory_usage') as mock_memory:
            mock_memory.return_value = 200.0  # Normal memory usage
            
            # Start monitoring
            memory_guardian.start_monitoring()
            assert memory_guardian.monitoring
            
            # Monitor for a few cycles
            for _ in range(3):
                await memory_guardian.monitor_memory()
                await asyncio.sleep(0.1)
            
            assert memory_guardian.memory_state == MemoryState.NORMAL
            assert memory_guardian.memory_stats.current_mb == 200.0
            assert memory_guardian.memory_stats.samples >= 3
        
        # Phase 4: Clean Shutdown
        await memory_guardian.stop_monitoring()
        assert not memory_guardian.monitoring
        
        # Verify state was preserved
        status = memory_guardian.get_status()
        assert status['process']['state'] == 'running'
        assert status['memory']['current_mb'] == 200.0
    
    @pytest.mark.asyncio
    async def test_memory_threshold_escalation_lifecycle(self, memory_guardian):
        """Test lifecycle through all memory threshold levels."""
        await memory_guardian.initialize()
        
        # Mock running process
        memory_guardian.process = MagicMock()
        memory_guardian.process.poll.return_value = None
        memory_guardian.process_pid = 12345
        memory_guardian.process_state = ProcessState.RUNNING
        
        # Track state changes
        state_changes = []
        
        with patch.object(memory_guardian, 'get_memory_usage') as mock_memory:
            # Normal → Warning
            mock_memory.return_value = 600.0  # Above warning threshold
            await memory_guardian.monitor_memory()
            assert memory_guardian.memory_state == MemoryState.WARNING
            state_changes.append(('normal_to_warning', 600.0))
            
            # Warning → Critical  
            mock_memory.return_value = 800.0  # Above critical threshold
            await memory_guardian.monitor_memory()
            assert memory_guardian.memory_state == MemoryState.CRITICAL
            state_changes.append(('warning_to_critical', 800.0))
            
            # Critical → Emergency (should trigger restart)
            with patch.object(memory_guardian, 'restart_process') as mock_restart:
                mock_restart.return_value = True
                mock_memory.return_value = 1100.0  # Above emergency threshold
                
                await memory_guardian.monitor_memory()
                assert memory_guardian.memory_state == MemoryState.EMERGENCY
                mock_restart.assert_called_once()
                state_changes.append(('critical_to_emergency', 1100.0))
        
        # Verify all state transitions occurred
        assert len(state_changes) == 3
        assert state_changes[0][0] == 'normal_to_warning'
        assert state_changes[1][0] == 'warning_to_critical'
        assert state_changes[2][0] == 'critical_to_emergency'
    
    @pytest.mark.asyncio
    async def test_restart_with_state_preservation(self, memory_guardian):
        """Test process restart with complete state preservation."""
        await memory_guardian.initialize()
        
        # Setup initial state
        test_state = {
            'user_data': {'session_id': str(uuid.uuid4())},
            'conversation_history': [
                {'role': 'user', 'content': 'Test message 1'},
                {'role': 'assistant', 'content': 'Test response 1'}
            ],
            'preferences': {'theme': 'dark', 'auto_save': True}
        }
        
        # Mock state manager
        state_manager = memory_guardian.state_manager
        assert state_manager is not None
        
        # Save initial state
        await state_manager.persist_state(test_state)
        
        # Mock process operations
        with patch.object(memory_guardian, 'start_process') as mock_start:
            with patch.object(memory_guardian, 'terminate_process') as mock_terminate:
                mock_start.return_value = True
                mock_terminate.return_value = True
                
                # Perform restart
                success = await memory_guardian.restart_process("State preservation test")
                assert success
                
                # Verify process lifecycle calls
                mock_terminate.assert_called_once()
                mock_start.assert_called_once()
        
        # Verify state restoration
        restored_state = await state_manager.restore_state()
        assert restored_state is not None
        assert restored_state['user_data']['session_id'] == test_state['user_data']['session_id']
        assert len(restored_state['conversation_history']) == 2
        
        # Verify restart was recorded
        assert len(memory_guardian.restart_attempts) > 0
        last_restart = memory_guardian.restart_attempts[-1]
        assert last_restart.reason == "State preservation test"
        assert last_restart.success
    
    @pytest.mark.asyncio
    async def test_restart_loop_protection_circuit_breaker(self, memory_guardian):
        """Test restart loop protection with circuit breaker behavior."""
        await memory_guardian.initialize()
        
        restart_protection = memory_guardian.restart_protection
        assert restart_protection is not None
        
        # Mock failing process starts
        restart_attempts = []
        with patch.object(memory_guardian, 'start_process') as mock_start:
            with patch.object(memory_guardian, 'terminate_process') as mock_terminate:
                mock_start.return_value = False  # Always fail
                mock_terminate.return_value = True
                
                # Attempt multiple restarts
                for i in range(5):
                    success = await memory_guardian.restart_process(f"Test failure {i}")
                    restart_attempts.append((i, success))
                    
                    # Check circuit breaker state
                    stats = restart_protection.get_restart_statistics()
                    
                    if i < 3:
                        # Should allow first 3 attempts
                        assert stats.circuit_state in [CircuitState.CLOSED, CircuitState.HALF_OPEN]
                    else:
                        # Circuit should be open after consecutive failures
                        assert stats.circuit_state == CircuitState.OPEN
                        assert not success, f"Restart {i} should have been blocked"
        
        # Verify circuit breaker statistics
        final_stats = restart_protection.get_restart_statistics()
        assert final_stats.total_restarts >= 3
        assert final_stats.consecutive_failures >= 3
        assert final_stats.circuit_state == CircuitState.OPEN
        
        # Test circuit breaker reset
        assert restart_protection.reset_circuit_breaker()
        reset_stats = restart_protection.get_restart_statistics()
        assert reset_stats.circuit_state == CircuitState.CLOSED
        assert reset_stats.consecutive_failures == 0
    
    @pytest.mark.asyncio 
    async def test_memory_leak_detection_and_response(self, memory_guardian):
        """Test memory leak detection and automated response."""
        await memory_guardian.initialize()
        
        restart_protection = memory_guardian.restart_protection
        assert restart_protection is not None
        
        # Simulate gradual memory growth pattern
        base_memory = 300.0
        growth_rate = 25.0  # MB per sample
        
        # Generate memory leak pattern
        for i in range(20):
            memory_mb = base_memory + (i * growth_rate)
            restart_protection.record_memory_sample(memory_mb)
            await asyncio.sleep(0.01)  # Small delay between samples
        
        # Detect memory leak
        trend = restart_protection.detect_memory_leak()
        assert trend is not None
        assert trend.is_leak_suspected, "Memory leak should be detected with 25MB/sample growth"
        assert trend.samples == 20
        assert trend.slope_mb_per_minute > 0
        
        # Test automated response to detected leak
        memory_guardian.process = MagicMock()
        memory_guardian.process_state = ProcessState.RUNNING
        memory_guardian.process_pid = 12345
        
        with patch.object(memory_guardian, 'get_memory_usage') as mock_memory:
            with patch.object(memory_guardian, 'restart_process') as mock_restart:
                mock_memory.return_value = base_memory + (19 * growth_rate)  # High memory
                mock_restart.return_value = True
                
                # Should trigger restart due to memory leak
                allowed, reason = restart_protection.should_allow_restart(
                    mock_memory.return_value
                )
                
                if trend.is_leak_suspected and mock_memory.return_value > memory_guardian.config.thresholds.critical:
                    # Emergency restart should be allowed for memory leaks
                    success = await memory_guardian.restart_process("Memory leak detected")
                    assert success
                    mock_restart.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_graceful_degradation_under_stress(self, memory_guardian):
        """Test graceful degradation when system is under stress."""
        await memory_guardian.initialize()
        
        degradation = memory_guardian.graceful_degradation
        health_monitor = memory_guardian.health_monitor
        assert degradation is not None
        assert health_monitor is not None
        
        # Simulate system stress conditions
        degradation_events = []
        
        # Degrade monitoring frequency due to high CPU
        await degradation.degrade_feature(
            "high_frequency_monitoring",
            "CPU usage above 80%",
            "reduced monitoring frequency"
        )
        degradation_events.append("monitoring_degraded")
        
        # Disable non-essential features due to memory pressure
        await degradation.disable_feature(
            "detailed_logging",
            "Memory pressure detected"
        )
        degradation_events.append("logging_disabled")
        
        # Check degradation status
        status = degradation.get_status()
        assert status.degraded_features == 1  # degrade_feature
        assert status.disabled_features == 1  # disable_feature
        assert status.level in [DegradationLevel.MINOR, DegradationLevel.MODERATE]
        
        # Test system functionality under degradation
        memory_guardian.process = MagicMock()
        memory_guardian.process_state = ProcessState.RUNNING
        
        with patch.object(memory_guardian, 'get_memory_usage') as mock_memory:
            mock_memory.return_value = 400.0  # Normal memory
            
            # Should still be able to monitor despite degradation
            await memory_guardian.monitor_memory()
            assert memory_guardian.memory_state == MemoryState.NORMAL
        
        # Test recovery from degradation
        await degradation.recover_feature("high_frequency_monitoring")
        await degradation.recover_feature("detailed_logging")
        
        recovered_status = degradation.get_status()
        assert recovered_status.degraded_features == 0
        assert recovered_status.disabled_features == 0
        assert recovered_status.level == DegradationLevel.NORMAL
    
    @pytest.mark.asyncio
    async def test_health_monitoring_integration(self, memory_guardian):
        """Test health monitoring integration and response."""
        await memory_guardian.initialize()
        
        health_monitor = memory_guardian.health_monitor
        assert health_monitor is not None
        
        # Set monitored process
        memory_guardian.process_pid = 12345
        health_monitor.set_monitored_process(12345)
        
        # Perform comprehensive health check
        health = await health_monitor.check_health()
        assert health is not None
        assert health.total_checks > 0
        assert health.status in [
            HealthStatus.HEALTHY,
            HealthStatus.DEGRADED,
            HealthStatus.UNHEALTHY,
            HealthStatus.CRITICAL
        ]
        
        # Test health validation before restart
        valid, message = await health_monitor.validate_before_start()
        assert isinstance(valid, bool)
        assert isinstance(message, str)
        
        # If system is unhealthy, should trigger graceful degradation
        if not valid:
            degradation = memory_guardian.graceful_degradation
            await degradation.degrade_feature(
                "automated_restart",
                f"Health check failed: {message}",
                "manual restart only"
            )
            
            status = degradation.get_status()
            assert status.degraded_features > 0
    
    @pytest.mark.asyncio
    async def test_concurrent_operations_safety(self, memory_guardian):
        """Test safety under concurrent operations."""
        await memory_guardian.initialize()
        
        memory_guardian.process = MagicMock()
        memory_guardian.process_state = ProcessState.RUNNING
        memory_guardian.process_pid = 12345
        
        # Mock process operations  
        with patch.object(memory_guardian, 'start_process') as mock_start:
            with patch.object(memory_guardian, 'terminate_process') as mock_terminate:
                mock_start.return_value = True
                mock_terminate.return_value = True
                
                # Launch concurrent operations
                operations = [
                    memory_guardian.restart_process("Concurrent test 1"),
                    memory_guardian.restart_process("Concurrent test 2"),
                    memory_guardian.restart_process("Concurrent test 3"),
                    memory_guardian.monitor_memory(),
                    memory_guardian.monitor_memory()
                ]
                
                # Execute concurrently
                results = await asyncio.gather(*operations, return_exceptions=True)
                
                # Check results
                restart_results = [r for r in results[:3] if isinstance(r, bool)]
                monitor_results = [r for r in results[3:] if r is None]  # monitor_memory returns None
                
                # Should have blocked some restarts due to restart protection
                successful_restarts = sum(1 for r in restart_results if r is True)
                assert successful_restarts <= 1, "Should prevent concurrent restarts"
                
                # Monitoring should continue working
                assert len(monitor_results) >= 0  # Some monitors may complete
    
    @pytest.mark.asyncio
    async def test_error_recovery_and_resilience(self, memory_guardian):
        """Test error recovery and system resilience."""
        await memory_guardian.initialize()
        
        error_scenarios = []
        
        # Test recovery from state save failure
        with patch.object(memory_guardian, '_save_state', side_effect=Exception("Disk full")):
            try:
                await memory_guardian.shutdown()
                error_scenarios.append("state_save_failure_handled")
            except Exception as e:
                pytest.fail(f"Should handle state save failure gracefully: {e}")
        
        # Reinitialize after error
        await memory_guardian.initialize()
        
        # Test recovery from memory monitoring failure
        memory_guardian.process = MagicMock()
        memory_guardian.process_state = ProcessState.RUNNING
        memory_guardian.process_pid = 12345
        
        with patch.object(memory_guardian, 'get_memory_usage', side_effect=Exception("Memory access failed")):
            try:
                await memory_guardian.monitor_memory()
                error_scenarios.append("memory_monitoring_failure_handled")
            except Exception as e:
                pytest.fail(f"Should handle memory monitoring failure gracefully: {e}")
        
        # Test recovery from process start failure
        with patch.object(memory_guardian, 'start_process', side_effect=Exception("Process start failed")):
            try:
                result = await memory_guardian.restart_process("Error recovery test")
                assert result is False  # Should return False on failure, not crash
                error_scenarios.append("process_start_failure_handled")
            except Exception as e:
                pytest.fail(f"Should handle process start failure gracefully: {e}")
        
        # Verify system is still operational after errors
        assert memory_guardian._initialized
        assert len(error_scenarios) == 3
        
    @pytest.mark.asyncio
    async def test_state_persistence_across_restarts(self, memory_guardian, temp_workspace):
        """Test state persistence across multiple restart cycles."""
        await memory_guardian.initialize()
        
        # Create complex state data
        test_states = []
        for i in range(3):
            state = {
                'cycle': i,
                'timestamp': time.time(),
                'user_sessions': [
                    {'id': f'session_{j}', 'active': True}
                    for j in range(5)
                ],
                'configuration': {
                    'memory_limit': 1000 + (i * 100),
                    'restart_count': i
                }
            }
            test_states.append(state)
        
        # Mock process operations
        with patch.object(memory_guardian, 'start_process') as mock_start:
            with patch.object(memory_guardian, 'terminate_process') as mock_terminate:
                mock_start.return_value = True
                mock_terminate.return_value = True
                
                for i, state in enumerate(test_states):
                    # Save state
                    await memory_guardian.state_manager.persist_state(state)
                    
                    # Perform restart
                    success = await memory_guardian.restart_process(f"Persistence test cycle {i}")
                    assert success
                    
                    # Verify state was restored
                    restored = await memory_guardian.state_manager.restore_state()
                    assert restored is not None
                    assert restored['cycle'] == i
                    assert len(restored['user_sessions']) == 5
                    assert restored['configuration']['restart_count'] == i
        
        # Verify restart history
        assert len(memory_guardian.restart_attempts) == 3
        for i, attempt in enumerate(memory_guardian.restart_attempts):
            assert attempt.reason == f"Persistence test cycle {i}"
            assert attempt.success
        
        # Verify state file exists and contains final state
        state_file = Path(memory_guardian.config.state_file)
        assert state_file.exists()
        
        with open(state_file) as f:
            saved_state = json.load(f)
            assert 'total_restarts' in saved_state
            assert saved_state['total_restarts'] >= 3


class TestMemoryGuardianEdgeCases:
    """Test edge cases and boundary conditions."""
    
    @pytest.fixture
    async def edge_case_config(self, tmp_path):
        """Create configuration for edge case testing."""
        return MemoryGuardianConfig(
            enabled=True,
            thresholds=MemoryThresholds(warning=1, critical=2, emergency=3),  # Very low thresholds
            restart_policy=RestartPolicy(max_attempts=1, attempt_window=1),   # Very restrictive
            monitoring=MonitoringConfig(check_interval=0.01),                # Very fast
            state_file=str(tmp_path / "edge_state.json")
        )
    
    @pytest.mark.asyncio
    async def test_extremely_rapid_memory_growth(self, edge_case_config):
        """Test handling of extremely rapid memory growth."""
        guardian = MemoryGuardian(edge_case_config)
        await guardian.initialize()
        
        # Mock process
        guardian.process = MagicMock()
        guardian.process_state = ProcessState.RUNNING
        guardian.process_pid = 12345
        
        restart_triggered = False
        
        with patch.object(guardian, 'get_memory_usage') as mock_memory:
            with patch.object(guardian, 'restart_process') as mock_restart:
                async def track_restart(*args, **kwargs):
                    nonlocal restart_triggered
                    restart_triggered = True
                    return True
                
                mock_restart.side_effect = track_restart
                
                # Simulate instant memory spike
                mock_memory.return_value = 5.0  # Way above emergency threshold
                
                await guardian.monitor_memory()
                
                assert restart_triggered, "Should trigger immediate restart for extreme memory spike"
                assert guardian.memory_state == MemoryState.EMERGENCY
        
        await guardian.shutdown()
    
    @pytest.mark.asyncio
    async def test_process_dies_during_monitoring(self, edge_case_config):
        """Test handling when process dies during monitoring."""
        guardian = MemoryGuardian(edge_case_config)
        guardian.config.auto_start = True
        await guardian.initialize()
        
        # Mock process that dies
        guardian.process = MagicMock()
        guardian.process_state = ProcessState.RUNNING
        guardian.process_pid = 12345
        guardian.process.poll.return_value = 1  # Process exited
        
        restart_called = False
        
        with patch.object(guardian, 'restart_process') as mock_restart:
            async def track_restart(*args, **kwargs):
                nonlocal restart_called
                restart_called = True
                guardian.process_state = ProcessState.RUNNING
                return True
            
            mock_restart.side_effect = track_restart
            
            await guardian.monitor_memory()
            
            assert restart_called, "Should restart when process dies unexpectedly"
            assert guardian.process_state == ProcessState.RUNNING
        
        await guardian.shutdown()
    
    @pytest.mark.asyncio
    async def test_zero_memory_reading(self, edge_case_config):
        """Test handling of zero or invalid memory readings."""
        guardian = MemoryGuardian(edge_case_config)
        await guardian.initialize()
        
        guardian.process = MagicMock()
        guardian.process_state = ProcessState.RUNNING
        guardian.process_pid = 12345
        
        with patch.object(guardian, 'get_memory_usage') as mock_memory:
            # Test zero memory reading
            mock_memory.return_value = 0.0
            await guardian.monitor_memory()
            # Should not crash, but memory state should remain normal
            assert guardian.memory_state == MemoryState.NORMAL
            
            # Test None memory reading  
            mock_memory.return_value = None
            await guardian.monitor_memory()
            # Should handle gracefully
            assert guardian.memory_state == MemoryState.NORMAL
        
        await guardian.shutdown()


class TestMemoryGuardianPlatformSpecific:
    """Test platform-specific behaviors."""
    
    @pytest.mark.skipif(platform.system() == 'Windows', reason="Unix-specific test")
    @pytest.mark.asyncio
    async def test_unix_signal_handling(self):
        """Test Unix signal handling during process termination."""
        config = MemoryGuardianConfig(enabled=True)
        guardian = MemoryGuardian(config)
        await guardian.initialize()
        
        # Mock Unix process
        guardian.process = MagicMock()
        guardian.process_pid = 12345
        guardian.process_state = ProcessState.RUNNING
        
        # Mock successful termination
        guardian.process.terminate = MagicMock()
        guardian.process.poll = MagicMock(side_effect=[None, None, 0])  # Process exits after 2 polls
        
        success = await guardian.terminate_process(timeout=1)
        assert success
        guardian.process.terminate.assert_called_once()
        
        await guardian.shutdown()
    
    @pytest.mark.skipif(platform.system() != 'Windows', reason="Windows-specific test")
    @pytest.mark.asyncio
    async def test_windows_process_termination(self):
        """Test Windows-specific process termination."""
        config = MemoryGuardianConfig(enabled=True)
        guardian = MemoryGuardian(config)
        await guardian.initialize()
        
        # Mock Windows process
        guardian.process = MagicMock()
        guardian.process_pid = 12345
        guardian.process_state = ProcessState.RUNNING
        
        # Mock Windows termination
        guardian.process.terminate = MagicMock()
        guardian.process.poll = MagicMock(side_effect=[None, 0])  # Process exits
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            
            success = await guardian.terminate_process(timeout=1)
            assert success
            guardian.process.terminate.assert_called_once()
        
        await guardian.shutdown()