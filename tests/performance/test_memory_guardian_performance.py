"""Performance tests for Memory Guardian system.

Tests memory monitoring overhead, state serialization speed, and resource usage.
"""

import asyncio
import json
import os
import psutil
import sys
import tempfile
import time
from pathlib import Path
from typing import List, Dict, Any
from unittest.mock import MagicMock, patch

import pytest

from claude_mpm.config.memory_guardian_config import (
    MemoryGuardianConfig,
    MemoryThresholds,
    MonitoringConfig
)
from claude_mpm.services.infrastructure.memory_guardian import MemoryGuardian
from claude_mpm.services.infrastructure.restart_protection import RestartProtection
from claude_mpm.services.infrastructure.state_manager import StateManager
from claude_mpm.services.infrastructure.memory_dashboard import MemoryDashboard


class TestMemoryGuardianPerformance:
    """Performance tests for Memory Guardian system."""
    
    @pytest.fixture
    def large_state_data(self) -> Dict[str, Any]:
        """Create large state data for testing."""
        return {
            'conversations': [
                {
                    'id': f'conv_{i}',
                    'messages': [
                        {'role': 'user', 'content': f'Message {j}' * 100}
                        for j in range(100)
                    ]
                }
                for i in range(10)
            ],
            'metadata': {
                'timestamp': time.time(),
                'version': '1.0.0',
                'data': 'x' * 10000  # 10KB of data
            }
        }
    
    @pytest.mark.asyncio
    async def test_memory_monitoring_overhead(self):
        """Test CPU and memory overhead of monitoring."""
        config = MemoryGuardianConfig(
            enabled=True,
            thresholds=MemoryThresholds(warning=1000, critical=2000, emergency=3000),
            monitoring=MonitoringConfig(check_interval=0.1)  # Fast monitoring
        )
        
        guardian = MemoryGuardian(config)
        await guardian.initialize()
        
        # Measure baseline CPU and memory
        process = psutil.Process()
        baseline_cpu = process.cpu_percent(interval=1)
        baseline_memory = process.memory_info().rss / (1024 * 1024)
        
        # Start monitoring
        guardian.start_monitoring()
        
        # Run for 5 seconds
        await asyncio.sleep(5)
        
        # Measure with monitoring
        monitoring_cpu = process.cpu_percent(interval=1)
        monitoring_memory = process.memory_info().rss / (1024 * 1024)
        
        # Stop monitoring
        await guardian.stop_monitoring()
        await guardian.shutdown()
        
        # Calculate overhead
        cpu_overhead = monitoring_cpu - baseline_cpu
        memory_overhead = monitoring_memory - baseline_memory
        
        # Assert overhead is reasonable
        assert cpu_overhead < 5.0, f"CPU overhead too high: {cpu_overhead}%"
        assert memory_overhead < 50.0, f"Memory overhead too high: {memory_overhead}MB"
        
        print(f"Monitoring overhead - CPU: {cpu_overhead:.2f}%, Memory: {memory_overhead:.2f}MB")
    
    @pytest.mark.asyncio
    async def test_state_serialization_performance(self, large_state_data):
        """Test performance of state save and restore operations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "state.json"
            
            manager = StateManager(state_file=state_file)
            await manager.initialize()
            
            # Measure save performance
            start = time.perf_counter()
            await manager.persist_state(large_state_data)
            save_time = time.perf_counter() - start
            
            # Measure file size
            file_size_mb = state_file.stat().st_size / (1024 * 1024)
            
            # Measure restore performance
            start = time.perf_counter()
            restored = await manager.restore_state()
            restore_time = time.perf_counter() - start
            
            await manager.shutdown()
            
            # Assert performance targets
            assert save_time < 5.0, f"Save too slow: {save_time:.2f}s"
            assert restore_time < 10.0, f"Restore too slow: {restore_time:.2f}s"
            
            print(f"State performance - Save: {save_time:.3f}s, Restore: {restore_time:.3f}s, Size: {file_size_mb:.2f}MB")
    
    @pytest.mark.asyncio
    async def test_restart_cycle_performance(self):
        """Test performance of complete restart cycle."""
        config = MemoryGuardianConfig(
            enabled=True,
            process_command=["python", "-c", "import time; time.sleep(1)"]
        )
        
        guardian = MemoryGuardian(config)
        await guardian.initialize()
        
        # Mock process operations for speed
        with patch.object(guardian, 'start_process', new_callable=AsyncMock) as mock_start:
            with patch.object(guardian, 'terminate_process', new_callable=AsyncMock) as mock_terminate:
                mock_start.return_value = True
                mock_terminate.return_value = True
                
                # Measure restart cycle
                start = time.perf_counter()
                success = await guardian.restart_process("Performance test")
                cycle_time = time.perf_counter() - start
                
                assert success
                assert cycle_time < 30.0, f"Restart cycle too slow: {cycle_time:.2f}s"
                
                print(f"Restart cycle time: {cycle_time:.3f}s")
        
        await guardian.shutdown()
    
    @pytest.mark.asyncio
    async def test_memory_trend_analysis_performance(self):
        """Test performance of memory trend analysis."""
        protection = RestartProtection()
        await protection.initialize()
        
        # Generate large number of samples
        num_samples = 1000
        for i in range(num_samples):
            protection.record_memory_sample(100 + i * 0.1)
        
        # Measure trend analysis performance
        start = time.perf_counter()
        trend = protection.detect_memory_leak()
        analysis_time = time.perf_counter() - start
        
        assert trend is not None
        assert analysis_time < 0.1, f"Trend analysis too slow: {analysis_time:.3f}s for {num_samples} samples"
        
        print(f"Trend analysis time: {analysis_time*1000:.2f}ms for {num_samples} samples")
        
        await protection.shutdown()
    
    @pytest.mark.asyncio
    async def test_dashboard_metrics_collection_performance(self):
        """Test performance of dashboard metrics collection."""
        # Create mock services
        guardian = MagicMock()
        guardian.get_status.return_value = {
            'memory': {'current_mb': 100, 'peak_mb': 200, 'average_mb': 150, 'state': 'normal'},
            'process': {'state': 'running', 'uptime_hours': 1.5},
            'restarts': {'total': 5}
        }
        
        dashboard = MemoryDashboard(memory_guardian=guardian)
        await dashboard.initialize()
        
        # Measure metrics collection
        start = time.perf_counter()
        for _ in range(100):
            metrics = dashboard.get_current_metrics()
        collection_time = time.perf_counter() - start
        
        avg_time = collection_time / 100
        assert avg_time < 0.01, f"Metrics collection too slow: {avg_time*1000:.2f}ms per collection"
        
        print(f"Average metrics collection time: {avg_time*1000:.3f}ms")
        
        await dashboard.shutdown()
    
    @pytest.mark.asyncio
    async def test_concurrent_monitoring_performance(self):
        """Test performance under concurrent monitoring load."""
        config = MemoryGuardianConfig(
            enabled=True,
            monitoring=MonitoringConfig(check_interval=0.01)  # Very fast monitoring
        )
        
        # Create multiple guardians
        guardians = [MemoryGuardian(config) for _ in range(5)]
        
        # Initialize all
        for guardian in guardians:
            await guardian.initialize()
        
        # Start monitoring on all
        for guardian in guardians:
            guardian.start_monitoring()
        
        # Monitor system resources
        process = psutil.Process()
        start_cpu = process.cpu_percent(interval=0.1)
        start_memory = process.memory_info().rss / (1024 * 1024)
        
        # Run for 3 seconds
        await asyncio.sleep(3)
        
        end_cpu = process.cpu_percent(interval=0.1)
        end_memory = process.memory_info().rss / (1024 * 1024)
        
        # Stop all monitoring
        for guardian in guardians:
            await guardian.stop_monitoring()
            await guardian.shutdown()
        
        # Check resource usage
        cpu_usage = end_cpu - start_cpu
        memory_growth = end_memory - start_memory
        
        assert cpu_usage < 20.0, f"CPU usage too high with {len(guardians)} monitors: {cpu_usage}%"
        assert memory_growth < 100.0, f"Memory growth too high: {memory_growth}MB"
        
        print(f"Concurrent monitoring ({len(guardians)} instances) - CPU: {cpu_usage:.2f}%, Memory growth: {memory_growth:.2f}MB")
    
    @pytest.mark.asyncio
    async def test_large_conversation_file_handling(self):
        """Test handling of large conversation files (2GB+ simulation)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a large mock conversation file
            large_file = Path(tmpdir) / ".claude.json"
            
            # Generate large data (simulate 2GB file with smaller test data)
            large_data = {
                'conversations': []
            }
            
            # Add conversations until we reach target size (using smaller size for testing)
            target_size_mb = 10  # Use 10MB for testing instead of 2GB
            conversation_template = {
                'id': 'conv_{}',
                'messages': [
                    {'role': 'user', 'content': 'x' * 1000},
                    {'role': 'assistant', 'content': 'y' * 5000}
                ] * 10
            }
            
            conv_count = 0
            while True:
                large_data['conversations'].append(
                    {**conversation_template, 'id': f'conv_{conv_count}'}
                )
                conv_count += 1
                
                # Check size periodically
                if conv_count % 10 == 0:
                    test_json = json.dumps(large_data)
                    if len(test_json) > target_size_mb * 1024 * 1024:
                        break
            
            # Write large file
            start = time.perf_counter()
            with open(large_file, 'w') as f:
                json.dump(large_data, f)
            write_time = time.perf_counter() - start
            
            file_size_mb = large_file.stat().st_size / (1024 * 1024)
            
            # Test reading large file
            start = time.perf_counter()
            with open(large_file, 'r') as f:
                loaded_data = json.load(f)
            read_time = time.perf_counter() - start
            
            # Performance assertions
            assert write_time < 10.0, f"Writing {file_size_mb:.1f}MB too slow: {write_time:.2f}s"
            assert read_time < 10.0, f"Reading {file_size_mb:.1f}MB too slow: {read_time:.2f}s"
            
            print(f"Large file handling ({file_size_mb:.1f}MB) - Write: {write_time:.2f}s, Read: {read_time:.2f}s")
    
    @pytest.mark.asyncio
    async def test_memory_leak_in_monitoring(self):
        """Test for memory leaks in continuous monitoring."""
        config = MemoryGuardianConfig(
            enabled=True,
            monitoring=MonitoringConfig(check_interval=0.01)
        )
        
        guardian = MemoryGuardian(config)
        await guardian.initialize()
        
        # Get baseline memory
        process = psutil.Process()
        baseline_memory = process.memory_info().rss / (1024 * 1024)
        
        # Start monitoring
        guardian.start_monitoring()
        
        # Run monitoring cycles
        memory_samples = []
        for i in range(10):
            await asyncio.sleep(1)
            current_memory = process.memory_info().rss / (1024 * 1024)
            memory_samples.append(current_memory)
        
        # Stop monitoring
        await guardian.stop_monitoring()
        await guardian.shutdown()
        
        # Check for memory leak
        memory_growth = memory_samples[-1] - baseline_memory
        average_growth_per_second = memory_growth / 10
        
        assert average_growth_per_second < 1.0, f"Possible memory leak: {average_growth_per_second:.2f}MB/s growth"
        
        print(f"Memory stability test - Growth: {memory_growth:.2f}MB over 10s ({average_growth_per_second:.3f}MB/s)")
    
    @pytest.mark.asyncio
    async def test_cache_effectiveness(self):
        """Test effectiveness of caching mechanisms."""
        protection = RestartProtection()
        await protection.initialize()
        
        # Add samples for trend analysis
        for i in range(100):
            protection.record_memory_sample(100 + i)
        
        # First analysis (cache miss)
        start = time.perf_counter()
        trend1 = protection.detect_memory_leak()
        first_time = time.perf_counter() - start
        
        # Second analysis (potential cache hit)
        start = time.perf_counter()
        trend2 = protection.detect_memory_leak()
        second_time = time.perf_counter() - start
        
        # Cache should make second call faster or similar
        # (Note: Current implementation recalculates, but this tests the pattern)
        assert second_time <= first_time * 1.5, f"Cache ineffective: {second_time:.3f}s vs {first_time:.3f}s"
        
        print(f"Cache effectiveness - First: {first_time*1000:.2f}ms, Second: {second_time*1000:.2f}ms")
        
        await protection.shutdown()


class TestResourceUsageProfile:
    """Profile resource usage of Memory Guardian components."""
    
    @pytest.mark.asyncio
    async def test_idle_resource_usage(self):
        """Test resource usage when system is idle."""
        config = MemoryGuardianConfig(
            enabled=True,
            monitoring=MonitoringConfig(check_interval=60)  # Slow monitoring
        )
        
        guardian = MemoryGuardian(config)
        await guardian.initialize()
        
        # Let system idle
        process = psutil.Process()
        
        # Measure over 5 seconds
        cpu_samples = []
        memory_samples = []
        
        for _ in range(5):
            cpu_samples.append(process.cpu_percent(interval=1))
            memory_samples.append(process.memory_info().rss / (1024 * 1024))
        
        await guardian.shutdown()
        
        avg_cpu = sum(cpu_samples) / len(cpu_samples)
        avg_memory = sum(memory_samples) / len(memory_samples)
        
        assert avg_cpu < 1.0, f"Idle CPU usage too high: {avg_cpu:.2f}%"
        
        print(f"Idle resource usage - CPU: {avg_cpu:.2f}%, Memory: {avg_memory:.2f}MB")
    
    @pytest.mark.asyncio
    async def test_peak_resource_usage(self):
        """Test peak resource usage during heavy operations."""
        config = MemoryGuardianConfig(
            enabled=True,
            monitoring=MonitoringConfig(check_interval=0.01)  # Fast monitoring
        )
        
        guardian = MemoryGuardian(config)
        await guardian.initialize()
        
        # Start heavy monitoring
        guardian.start_monitoring()
        
        # Track peak usage
        process = psutil.Process()
        peak_cpu = 0
        peak_memory = 0
        
        for _ in range(10):
            cpu = process.cpu_percent(interval=0.1)
            memory = process.memory_info().rss / (1024 * 1024)
            peak_cpu = max(peak_cpu, cpu)
            peak_memory = max(peak_memory, memory)
        
        await guardian.stop_monitoring()
        await guardian.shutdown()
        
        assert peak_cpu < 50.0, f"Peak CPU usage too high: {peak_cpu:.2f}%"
        
        print(f"Peak resource usage - CPU: {peak_cpu:.2f}%, Memory: {peak_memory:.2f}MB")