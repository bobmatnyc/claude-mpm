"""Tests for MemoryGuardian service.

This module tests the MemoryGuardian service including:
- Process lifecycle management
- Memory monitoring and thresholds
- Restart policies and cooldowns
- Platform-specific memory monitoring
- State persistence
"""

import asyncio
import os
import platform
import sys
import time
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, AsyncMock
import pytest
import pytest_asyncio

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / 'src'))

from claude_mpm.services.infrastructure.memory_guardian import (
    MemoryGuardian,
    MemoryState,
    ProcessState,
    RestartAttempt,
    MemoryStats
)
from claude_mpm.config.memory_guardian_config import (
    MemoryGuardianConfig,
    MemoryThresholds,
    RestartPolicy,
    MonitoringConfig
)
from claude_mpm.utils.platform_memory import MemoryInfo


class TestMemoryGuardian:
    """Test suite for MemoryGuardian service."""
    
    @pytest.fixture
    def config(self):
        """Create test configuration."""
        config = MemoryGuardianConfig()
        config.thresholds.warning = 1000  # 1GB for testing
        config.thresholds.critical = 1500  # 1.5GB
        config.thresholds.emergency = 2000  # 2GB
        config.monitoring.normal_interval = 1  # Fast for testing
        config.process_command = ['python', '-c', 'import time; time.sleep(100)']
        return config
    
    @pytest_asyncio.fixture
    async def guardian(self, config):
        """Create MemoryGuardian instance."""
        guardian = MemoryGuardian(config)
        yield guardian
        # Cleanup
        if guardian.process:
            await guardian.terminate_process()
    
    @pytest.mark.asyncio
    async def test_initialization(self, config):
        """Test MemoryGuardian initialization."""
        guardian = MemoryGuardian(config)
        
        assert guardian.config == config
        assert guardian.process_state == ProcessState.NOT_STARTED
        assert guardian.memory_state == MemoryState.NORMAL
        assert guardian.total_restarts == 0
        assert not guardian.monitoring
    
    @pytest.mark.asyncio
    async def test_start_process(self, guardian):
        """Test starting a subprocess."""
        # Use a simple Python command that sleeps
        guardian.config.process_command = [
            sys.executable, '-c', 'import time; time.sleep(10)'
        ]
        
        success = await guardian.start_process()
        assert success
        assert guardian.process is not None
        assert guardian.process_state == ProcessState.RUNNING
        assert guardian.process_pid is not None
        
        # Cleanup
        await guardian.terminate_process()
    
    @pytest.mark.asyncio
    async def test_terminate_process(self, guardian):
        """Test terminating a subprocess."""
        # Start a process
        guardian.config.process_command = [
            sys.executable, '-c', 'import time; time.sleep(10)'
        ]
        await guardian.start_process()
        
        # Terminate it
        success = await guardian.terminate_process(timeout=5)
        assert success
        assert guardian.process is None
        assert guardian.process_state == ProcessState.STOPPED
    
    @pytest.mark.asyncio
    async def test_memory_monitoring(self, guardian):
        """Test memory monitoring logic."""
        # Mock process and memory reading
        guardian.process = MagicMock()
        guardian.process.poll.return_value = None  # Process is running
        guardian.process_pid = os.getpid()  # Use current process for testing
        guardian.process_state = ProcessState.RUNNING
        
        # Mock get_memory_usage to return specific values
        with patch.object(guardian, 'get_memory_usage') as mock_memory:
            # Test normal state
            mock_memory.return_value = 500.0  # 500MB
            await guardian.monitor_memory()
            assert guardian.memory_state == MemoryState.NORMAL
            
            # Test warning state
            mock_memory.return_value = 1200.0  # 1.2GB
            await guardian.monitor_memory()
            assert guardian.memory_state == MemoryState.WARNING
            
            # Test critical state
            mock_memory.return_value = 1700.0  # 1.7GB
            await guardian.monitor_memory()
            assert guardian.memory_state == MemoryState.CRITICAL
            
            # Test emergency state (should trigger restart)
            with patch.object(guardian, 'restart_process') as mock_restart:
                mock_restart.return_value = True
                mock_memory.return_value = 2100.0  # 2.1GB
                await guardian.monitor_memory()
                assert guardian.memory_state == MemoryState.EMERGENCY
                mock_restart.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_restart_policy(self, guardian):
        """Test restart policy enforcement."""
        guardian.config.restart_policy.max_attempts = 3
        guardian.config.restart_policy.attempt_window = 60  # 1 minute window
        
        # Add some restart attempts
        current_time = time.time()
        guardian.restart_attempts = [
            RestartAttempt(current_time - 10, "Test", 1000, True),
            RestartAttempt(current_time - 5, "Test", 1000, True),
        ]
        
        # Should allow restart (under limit)
        assert guardian._can_restart()
        
        # Add one more to reach limit
        guardian.restart_attempts.append(
            RestartAttempt(current_time - 2, "Test", 1000, True)
        )
        
        # Should not allow restart (at limit)
        assert not guardian._can_restart()
        
        # Old attempts shouldn't count
        guardian.restart_attempts = [
            RestartAttempt(current_time - 120, "Test", 1000, True),  # Outside window
            RestartAttempt(current_time - 10, "Test", 1000, True),
        ]
        assert guardian._can_restart()
    
    @pytest.mark.asyncio
    async def test_cooldown_calculation(self, guardian):
        """Test restart cooldown calculation."""
        guardian.config.restart_policy.initial_cooldown = 10
        guardian.config.restart_policy.cooldown_multiplier = 2.0
        guardian.config.restart_policy.max_cooldown = 60
        
        # First attempt - no cooldown
        guardian.consecutive_failures = 0
        assert guardian._get_restart_cooldown() == 0
        
        # After failures - increasing cooldown
        guardian.consecutive_failures = 1
        guardian.restart_attempts = [RestartAttempt(time.time(), "Test", 1000, False)]
        assert guardian._get_restart_cooldown() == 20  # 10 * 2^1
        
        guardian.consecutive_failures = 2
        assert guardian._get_restart_cooldown() == 40  # 10 * 2^2
        
        guardian.consecutive_failures = 3
        assert guardian._get_restart_cooldown() == 60  # Capped at max_cooldown
    
    @pytest.mark.asyncio
    async def test_memory_stats_tracking(self, guardian):
        """Test memory statistics tracking."""
        stats = MemoryStats()
        
        # Update with readings
        stats.update(100.0)
        assert stats.current_mb == 100.0
        assert stats.peak_mb == 100.0
        assert stats.average_mb == 100.0
        assert stats.samples == 1
        
        stats.update(200.0)
        assert stats.current_mb == 200.0
        assert stats.peak_mb == 200.0
        assert stats.average_mb == 150.0
        assert stats.samples == 2
        
        stats.update(50.0)
        assert stats.current_mb == 50.0
        assert stats.peak_mb == 200.0  # Peak unchanged
        assert stats.average_mb == 350.0 / 3
        assert stats.samples == 3
    
    @pytest.mark.asyncio
    async def test_state_persistence(self, guardian):
        """Test state save and load functionality."""
        # Setup state file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            state_file = f.name
        
        try:
            guardian.config.state_file = state_file
            
            # Set some state
            guardian.total_restarts = 5
            guardian.memory_stats.peak_mb = 1500.0
            guardian.restart_attempts = [
                RestartAttempt(time.time(), "Test", 1000, True)
            ]
            
            # Save state
            guardian._save_state()
            
            # Create new guardian and load state
            new_guardian = MemoryGuardian(guardian.config)
            new_guardian._load_state()
            
            # Verify state was restored
            assert new_guardian.total_restarts == 5
            assert new_guardian.memory_stats.peak_mb == 1500.0
            assert len(new_guardian.restart_attempts) == 1
            
        finally:
            # Cleanup
            Path(state_file).unlink(missing_ok=True)
    
    @pytest.mark.asyncio
    async def test_monitoring_loop(self, guardian):
        """Test continuous monitoring loop."""
        # Mock monitor_memory to track calls
        call_count = 0
        
        async def mock_monitor():
            nonlocal call_count
            call_count += 1
            if call_count >= 3:
                guardian.monitoring = False  # Stop after 3 iterations
        
        guardian.monitor_memory = mock_monitor
        guardian.config.monitoring.normal_interval = 0.1  # Fast for testing
        
        # Start monitoring
        guardian.start_monitoring()
        assert guardian.monitoring
        assert guardian.monitor_task is not None
        
        # Wait for monitoring to complete
        await guardian.monitor_task
        
        # Verify monitoring ran
        assert call_count >= 3
        assert not guardian.monitoring
    
    @pytest.mark.asyncio
    async def test_state_hooks(self, guardian):
        """Test state save and restore hooks."""
        save_called = False
        restore_called = False
        saved_state = None
        
        def save_hook(state):
            nonlocal save_called, saved_state
            save_called = True
            saved_state = state
        
        def restore_hook(state):
            nonlocal restore_called
            restore_called = True
        
        guardian.add_state_save_hook(save_hook)
        guardian.add_state_restore_hook(restore_hook)
        
        # Trigger hooks
        await guardian._trigger_state_save()
        assert save_called
        assert saved_state is not None
        assert 'process_state' in saved_state
        
        await guardian._trigger_state_restore()
        assert restore_called
    
    @pytest.mark.asyncio
    async def test_process_exit_handling(self, guardian):
        """Test handling of process exit."""
        # Start a process that exits quickly
        guardian.config.process_command = [
            sys.executable, '-c', 'import sys; sys.exit(0)'
        ]
        guardian.config.auto_start = True
        
        await guardian.start_process()
        await asyncio.sleep(1)  # Let process exit
        
        # Mock restart to track if called
        with patch.object(guardian, 'restart_process') as mock_restart:
            mock_restart.return_value = True
            await guardian.monitor_memory()
            
            # Should detect process exit and restart
            mock_restart.assert_called_once()
    
    def test_get_status(self, guardian):
        """Test status reporting."""
        guardian.process_pid = 12345
        guardian.process_state = ProcessState.RUNNING
        guardian.memory_stats.current_mb = 1000.0
        guardian.memory_stats.peak_mb = 1500.0
        guardian.total_restarts = 2
        guardian.monitoring = True
        
        status = guardian.get_status()
        
        assert status['enabled'] == guardian.config.enabled
        assert status['process']['pid'] == 12345
        assert status['process']['state'] == 'running'
        assert status['memory']['current_mb'] == 1000.0
        assert status['memory']['peak_mb'] == 1500.0
        assert status['restarts']['total'] == 2
        assert status['monitoring']['active'] is True
    
    def test_config_validation(self):
        """Test configuration validation."""
        config = MemoryGuardianConfig()
        
        # Valid config
        issues = config.validate()
        assert len(issues) == 0
        
        # Invalid thresholds
        config.thresholds.warning = 2000
        config.thresholds.critical = 1500
        config.thresholds.emergency = 1000
        issues = config.validate()
        assert len(issues) > 0
        assert any('threshold' in issue.lower() for issue in issues)
        
        # Invalid intervals
        config = MemoryGuardianConfig()
        config.monitoring.normal_interval = -1
        issues = config.validate()
        assert len(issues) > 0
        assert any('interval' in issue.lower() for issue in issues)
    
    def test_threshold_adjustment(self):
        """Test memory threshold adjustment for system memory."""
        thresholds = MemoryThresholds()
        
        # Adjust for 16GB system
        thresholds.adjust_for_system_memory(16384)  # 16GB in MB
        
        assert thresholds.warning == int(16384 * 0.5)  # 50% = 8GB
        assert thresholds.critical == int(16384 * 0.65)  # 65% = ~10.6GB
        assert thresholds.emergency == int(16384 * 0.75)  # 75% = 12GB


class TestPlatformMemory:
    """Test platform-specific memory monitoring."""
    
    @pytest.mark.skipif(not sys.platform.startswith('darwin'), reason="macOS only")
    def test_macos_memory(self):
        """Test macOS memory monitoring."""
        from claude_mpm.utils.platform_memory import get_memory_info_macos
        
        # Test with current process
        info = get_memory_info_macos(os.getpid())
        assert info is not None
        assert info.rss > 0
        assert info.vms > 0
    
    @pytest.mark.skipif(not sys.platform.startswith('linux'), reason="Linux only")
    def test_linux_memory(self):
        """Test Linux memory monitoring."""
        from claude_mpm.utils.platform_memory import get_memory_info_linux
        
        # Test with current process
        info = get_memory_info_linux(os.getpid())
        assert info is not None
        assert info.rss > 0
        assert info.vms > 0
    
    @pytest.mark.skipif(not sys.platform.startswith('win'), reason="Windows only")
    def test_windows_memory(self):
        """Test Windows memory monitoring."""
        from claude_mpm.utils.platform_memory import get_memory_info_windows
        
        # Test with current process
        info = get_memory_info_windows(os.getpid())
        assert info is not None
        assert info.rss > 0
    
    def test_memory_info_conversion(self):
        """Test MemoryInfo conversions."""
        info = MemoryInfo(
            rss=1073741824,  # 1GB in bytes
            vms=2147483648,  # 2GB in bytes
            percent=50.0
        )
        
        assert info.rss_mb == 1024.0
        assert info.vms_mb == 2048.0
        assert info.percent == 50.0
        
        data = info.to_dict()
        assert data['rss_bytes'] == 1073741824
        assert data['rss_mb'] == 1024.0
        assert data['vms_bytes'] == 2147483648
        assert data['vms_mb'] == 2048.0
    
    def test_get_process_memory_auto(self):
        """Test automatic memory monitoring method selection."""
        from claude_mpm.utils.platform_memory import get_process_memory
        
        # Test with current process
        info = get_process_memory(os.getpid())
        assert info is not None
        assert info.rss > 0
        
        # Test with invalid PID
        info = get_process_memory(999999)
        assert info is None
    
    def test_system_memory(self):
        """Test system memory detection."""
        from claude_mpm.utils.platform_memory import get_system_memory
        
        total, available = get_system_memory()
        
        # Should get some values on any platform
        assert total > 0
        assert available > 0
        assert available <= total
    
    def test_memory_pressure(self):
        """Test memory pressure detection."""
        from claude_mpm.utils.platform_memory import check_memory_pressure
        
        pressure = check_memory_pressure()
        assert pressure in ['normal', 'warning', 'critical', 'unknown']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])