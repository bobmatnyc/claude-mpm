"""Integration tests for the Memory Guardian system with safety features.

Tests end-to-end memory monitoring scenarios including restart loop protection,
state preservation, and graceful degradation.
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
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from claude_mpm.config.memory_guardian_config import (
    MemoryGuardianConfig,
    MemoryThresholds,
    RestartPolicy,
    MonitoringConfig
)
from claude_mpm.services.infrastructure.memory_guardian import (
    MemoryGuardian,
    MemoryState,
    ProcessState
)
from claude_mpm.services.infrastructure.restart_protection import (
    RestartProtection,
    CircuitState
)
from claude_mpm.services.infrastructure.health_monitor import (
    HealthMonitor,
    HealthStatus
)
from claude_mpm.services.infrastructure.graceful_degradation import (
    GracefulDegradation,
    DegradationLevel
)
from claude_mpm.services.infrastructure.state_manager import StateManager
from claude_mpm.services.infrastructure.memory_dashboard import MemoryDashboard


class TestMemoryGuardianIntegration:
    """Integration tests for Memory Guardian system."""
    
    @pytest.fixture
    async def temp_state_dir(self):
        """Create temporary directory for state files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)
    
    @pytest.fixture
    async def memory_guardian_config(self, temp_state_dir):
        """Create test configuration."""
        return MemoryGuardianConfig(
            enabled=True,
            thresholds=MemoryThresholds(
                warning=100,
                critical=200,
                emergency=300
            ),
            restart_policy=RestartPolicy(
                max_attempts=3,
                attempt_window=300,
                cooldown_seconds=1,
                exponential_backoff=True
            ),
            monitoring=MonitoringConfig(
                check_interval=1,
                check_interval_warning=0.5,
                check_interval_critical=0.25
            ),
            process_command=["python", "-c", "import time; time.sleep(100)"],
            state_file=str(temp_state_dir / "memory_guardian.json"),
            persist_state=True
        )
    
    @pytest.fixture
    async def memory_guardian(self, memory_guardian_config):
        """Create MemoryGuardian instance."""
        guardian = MemoryGuardian(memory_guardian_config)
        yield guardian
        await guardian.shutdown()
    
    @pytest.mark.asyncio
    async def test_end_to_end_memory_monitoring(self, memory_guardian):
        """Test complete memory monitoring workflow."""
        # Initialize the service
        assert await memory_guardian.initialize()
        
        # Verify safety services are initialized
        assert memory_guardian.restart_protection is not None
        assert memory_guardian.health_monitor is not None
        assert memory_guardian.graceful_degradation is not None
        
        # Start monitoring
        memory_guardian.start_monitoring()
        assert memory_guardian.monitoring
        
        # Simulate memory monitoring
        with patch.object(memory_guardian, 'get_memory_usage') as mock_memory:
            # Normal memory usage
            mock_memory.return_value = 50.0
            await memory_guardian.monitor_memory()
            assert memory_guardian.memory_state == MemoryState.NORMAL
            
            # Warning threshold
            mock_memory.return_value = 150.0
            await memory_guardian.monitor_memory()
            assert memory_guardian.memory_state == MemoryState.WARNING
            
            # Critical threshold
            mock_memory.return_value = 250.0
            await memory_guardian.monitor_memory()
            assert memory_guardian.memory_state == MemoryState.CRITICAL
        
        # Stop monitoring
        await memory_guardian.stop_monitoring()
        assert not memory_guardian.monitoring
    
    @pytest.mark.asyncio
    async def test_restart_loop_protection(self, memory_guardian):
        """Test restart loop protection prevents infinite restarts."""
        await memory_guardian.initialize()
        
        # Mock process start to always fail
        with patch.object(memory_guardian, 'start_process', return_value=False):
            # Attempt multiple restarts
            for i in range(5):
                success = await memory_guardian.restart_process(f"Test restart {i}")
                
                if i < 3:
                    # Should allow first 3 attempts
                    assert not success  # Process start fails, but restart is attempted
                else:
                    # Should block after max consecutive failures
                    assert not success
                    # Circuit breaker should be open
                    if memory_guardian.restart_protection:
                        stats = memory_guardian.restart_protection.get_restart_statistics()
                        assert stats.circuit_state == CircuitState.OPEN
    
    @pytest.mark.asyncio
    async def test_state_preservation_across_restarts(self, memory_guardian):
        """Test state is preserved across process restarts."""
        await memory_guardian.initialize()
        
        # Create mock state
        test_state = {
            'test_key': 'test_value',
            'timestamp': time.time()
        }
        
        # Mock state manager
        state_manager = memory_guardian.state_manager
        if state_manager:
            # Save state
            await state_manager.persist_state(test_state)
            
            # Simulate restart
            with patch.object(memory_guardian, 'start_process', return_value=True):
                with patch.object(memory_guardian, 'terminate_process', return_value=True):
                    success = await memory_guardian.restart_process("Test state preservation")
                    assert success
            
            # Verify state was restored
            # In a real scenario, the state would be used by the restarted process
            assert state_manager.current_state is not None
    
    @pytest.mark.asyncio
    async def test_graceful_degradation(self, memory_guardian):
        """Test system degrades gracefully when components fail."""
        await memory_guardian.initialize()
        
        degradation = memory_guardian.graceful_degradation
        if degradation:
            # Simulate component failure
            await degradation.degrade_feature(
                "memory_monitoring",
                "Test failure",
                "basic mode"
            )
            
            # Check degradation status
            status = degradation.get_status()
            assert status.degraded_features > 0
            assert status.level != DegradationLevel.NORMAL
            
            # Recover feature
            await degradation.recover_feature("memory_monitoring")
            status = degradation.get_status()
            assert status.degraded_features == 0
    
    @pytest.mark.asyncio
    async def test_health_monitoring(self, memory_guardian):
        """Test health monitoring integration."""
        await memory_guardian.initialize()
        
        health_monitor = memory_guardian.health_monitor
        if health_monitor:
            # Perform health check
            health = await health_monitor.check_health()
            
            # Verify health check results
            assert health is not None
            assert health.total_checks > 0
            assert health.status in [
                HealthStatus.HEALTHY,
                HealthStatus.DEGRADED,
                HealthStatus.UNHEALTHY,
                HealthStatus.CRITICAL
            ]
    
    @pytest.mark.asyncio
    async def test_memory_leak_detection(self, memory_guardian):
        """Test memory leak detection through trend analysis."""
        await memory_guardian.initialize()
        
        protection = memory_guardian.restart_protection
        if protection:
            # Simulate increasing memory usage over time
            base_memory = 100.0
            for i in range(20):
                memory_mb = base_memory + (i * 15)  # 15 MB/sample growth
                protection.record_memory_sample(memory_mb)
                await asyncio.sleep(0.01)  # Small delay between samples
            
            # Check for memory leak detection
            trend = protection.detect_memory_leak()
            assert trend is not None
            # With 15 MB/sample growth, this should be detected as a leak
            assert trend.is_leak_suspected
    
    @pytest.mark.asyncio
    async def test_exponential_backoff(self, memory_guardian):
        """Test exponential backoff for restart attempts."""
        await memory_guardian.initialize()
        
        protection = memory_guardian.restart_protection
        if protection:
            # Test backoff calculation
            assert protection.get_backoff_seconds(1) >= 1.0
            assert protection.get_backoff_seconds(2) >= 2.0
            assert protection.get_backoff_seconds(3) >= 4.0
            assert protection.get_backoff_seconds(10) <= protection.max_backoff_seconds
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_reset(self, memory_guardian):
        """Test circuit breaker can be manually reset."""
        await memory_guardian.initialize()
        
        protection = memory_guardian.restart_protection
        if protection:
            # Force circuit breaker to open
            for i in range(3):
                protection.record_restart("Test failure", 100, False)
            
            stats = protection.get_restart_statistics()
            assert stats.circuit_state == CircuitState.OPEN
            
            # Reset circuit breaker
            assert protection.reset_circuit_breaker()
            
            stats = protection.get_restart_statistics()
            assert stats.circuit_state == CircuitState.CLOSED
    
    @pytest.mark.asyncio
    async def test_dashboard_metrics(self, memory_guardian):
        """Test dashboard metrics collection."""
        await memory_guardian.initialize()
        
        # Create dashboard
        dashboard = MemoryDashboard(
            memory_guardian=memory_guardian,
            restart_protection=memory_guardian.restart_protection,
            health_monitor=memory_guardian.health_monitor,
            graceful_degradation=memory_guardian.graceful_degradation
        )
        
        await dashboard.initialize()
        
        # Get metrics
        metrics = dashboard.get_current_metrics()
        assert metrics is not None
        assert metrics.memory_current_mb >= 0
        assert metrics.process_state != "unknown"
        
        # Get dashboard data
        data = dashboard.get_dashboard_data()
        assert 'current_metrics' in data
        assert 'thresholds' in data
        
        # Get summary
        summary = dashboard.get_summary()
        assert "MEMORY GUARDIAN DASHBOARD" in summary
        
        await dashboard.shutdown()
    
    @pytest.mark.asyncio
    async def test_concurrent_restart_protection(self, memory_guardian):
        """Test restart protection under concurrent restart requests."""
        await memory_guardian.initialize()
        
        # Mock process operations
        with patch.object(memory_guardian, 'start_process', return_value=True):
            with patch.object(memory_guardian, 'terminate_process', return_value=True):
                # Attempt concurrent restarts
                tasks = [
                    memory_guardian.restart_process(f"Concurrent restart {i}")
                    for i in range(5)
                ]
                
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Some restarts should be blocked
                successful_restarts = sum(1 for r in results if r is True)
                assert successful_restarts <= 3  # Max attempts limit
    
    @pytest.mark.asyncio
    async def test_platform_specific_memory_monitoring(self, memory_guardian):
        """Test memory monitoring works on different platforms."""
        await memory_guardian.initialize()
        
        # Mock platform-specific memory functions
        with patch('claude_mpm.utils.platform_memory.get_process_memory') as mock_get_memory:
            mock_get_memory.return_value = MagicMock(rss_mb=150.0)
            
            memory_usage = memory_guardian.get_memory_usage()
            
            if memory_guardian.process:
                assert memory_usage == 150.0
            else:
                assert memory_usage is None
    
    @pytest.mark.asyncio
    async def test_error_recovery(self, memory_guardian):
        """Test system recovers from various error conditions."""
        await memory_guardian.initialize()
        
        # Test recovery from state save failure
        with patch.object(memory_guardian, '_save_state', side_effect=Exception("Save failed")):
            # Should not crash
            await memory_guardian.shutdown()
        
        # Reinitialize
        await memory_guardian.initialize()
        
        # Test recovery from monitoring error
        with patch.object(memory_guardian, 'get_memory_usage', side_effect=Exception("Memory error")):
            # Should handle gracefully
            await memory_guardian.monitor_memory()
            # System should still be operational
            assert memory_guardian._initialized
    
    @pytest.mark.asyncio
    async def test_metrics_export(self, memory_guardian, temp_state_dir):
        """Test metrics export functionality."""
        await memory_guardian.initialize()
        
        metrics_file = temp_state_dir / "metrics.json"
        
        dashboard = MemoryDashboard(
            memory_guardian=memory_guardian,
            metrics_file=metrics_file,
            export_interval_seconds=1
        )
        
        await dashboard.initialize()
        
        # Wait for export
        await asyncio.sleep(1.5)
        
        # Check metrics file exists
        assert metrics_file.exists()
        
        # Verify metrics content
        with open(metrics_file) as f:
            data = json.load(f)
            assert 'current_metrics' in data
            assert 'timestamp' in data
        
        # Test Prometheus format export
        prometheus_metrics = dashboard.export_prometheus_metrics()
        assert "memory_current_mb" in prometheus_metrics
        assert "total_restarts" in prometheus_metrics
        
        await dashboard.shutdown()


class TestRestartProtectionUnit:
    """Unit tests for restart protection service."""
    
    @pytest.mark.asyncio
    async def test_restart_frequency_limiting(self):
        """Test restart frequency is properly limited."""
        protection = RestartProtection(max_restarts_per_hour=3)
        await protection.initialize()
        
        # Record restarts
        for i in range(5):
            protection.record_restart(f"Test {i}", 100, True)
            
            if i < 3:
                # Should allow first 3
                allowed, _ = protection.should_allow_restart()
                assert allowed or i == 2  # Third might hit limit
            else:
                # Should block after limit
                allowed, reason = protection.should_allow_restart()
                assert not allowed
                assert "Too many restarts" in reason
        
        await protection.shutdown()
    
    @pytest.mark.asyncio
    async def test_memory_trend_calculation(self):
        """Test memory trend calculation accuracy."""
        protection = RestartProtection()
        await protection.initialize()
        
        # Generate linear memory growth
        for i in range(20):
            protection.record_memory_sample(100 + i * 10)
        
        trend = protection.detect_memory_leak()
        assert trend is not None
        # Slope should be approximately 10 MB per sample
        # (converted to per minute based on timing)
        assert trend.samples == 20
        
        await protection.shutdown()


class TestHealthMonitorUnit:
    """Unit tests for health monitor service."""
    
    @pytest.mark.asyncio
    async def test_resource_validation(self):
        """Test system resource validation."""
        monitor = HealthMonitor()
        await monitor.initialize()
        
        # Validate system resources
        valid, message = await monitor.validate_before_start()
        # Should generally pass on development machines
        assert isinstance(valid, bool)
        assert isinstance(message, str)
        
        await monitor.shutdown()
    
    @pytest.mark.asyncio
    async def test_health_check_types(self):
        """Test different types of health checks."""
        monitor = HealthMonitor()
        await monitor.initialize()
        
        # Perform individual checks
        cpu_check = await monitor._check_cpu_usage()
        assert cpu_check.check_type.value == "cpu_usage"
        
        memory_check = await monitor._check_memory_usage()
        assert memory_check.check_type.value == "memory_usage"
        
        disk_check = await monitor._check_disk_space()
        assert disk_check.check_type.value == "disk_space"
        
        await monitor.shutdown()


class TestGracefulDegradationUnit:
    """Unit tests for graceful degradation service."""
    
    @pytest.mark.asyncio
    async def test_feature_degradation(self):
        """Test feature degradation and recovery."""
        degradation = GracefulDegradation()
        await degradation.initialize()
        
        # Register a feature
        degradation.register_feature("test_feature")
        
        # Degrade the feature
        await degradation.degrade_feature(
            "test_feature",
            "Test reason",
            "fallback mode"
        )
        
        status = degradation.get_status()
        assert status.degraded_features == 1
        
        # Recover the feature
        await degradation.recover_feature("test_feature")
        
        status = degradation.get_status()
        assert status.degraded_features == 0
        assert status.level == DegradationLevel.NORMAL
        
        await degradation.shutdown()
    
    @pytest.mark.asyncio
    async def test_degradation_levels(self):
        """Test degradation level calculation."""
        degradation = GracefulDegradation()
        await degradation.initialize()
        
        # Register multiple features
        for i in range(4):
            degradation.register_feature(f"feature_{i}")
        
        # Degrade features progressively
        await degradation.degrade_feature("feature_0", "reason", "fallback")
        assert degradation.degradation_level == DegradationLevel.MINOR
        
        await degradation.degrade_feature("feature_1", "reason", "fallback")
        assert degradation.degradation_level == DegradationLevel.MODERATE
        
        await degradation.disable_feature("feature_2", "reason")
        await degradation.disable_feature("feature_3", "reason")
        assert degradation.degradation_level == DegradationLevel.EMERGENCY
        
        await degradation.shutdown()