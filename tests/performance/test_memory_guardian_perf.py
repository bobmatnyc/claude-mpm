"""Enhanced performance benchmarks for Memory Guardian System.

This module provides comprehensive performance testing for the Memory Guardian system,
measuring monitoring overhead, state serialization timing, restart cycle performance,
and resource usage profiling under various conditions.

Performance categories:
- Memory monitoring overhead measurement
- State serialization/deserialization timing
- Restart cycle performance analysis
- Resource usage profiling (CPU, memory, disk)
- Scalability testing under load
- Cache effectiveness evaluation
- Platform-specific performance characteristics
"""

import asyncio
import gc
import json
import os
import platform
import psutil
import resource
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
from unittest.mock import MagicMock, patch, AsyncMock
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
    MemoryStats
)
from claude_mpm.services.infrastructure.restart_protection import RestartProtection
from claude_mpm.services.infrastructure.state_manager import StateManager
from claude_mpm.services.infrastructure.memory_dashboard import MemoryDashboard
from claude_mpm.services.infrastructure.health_monitor import HealthMonitor
from claude_mpm.services.infrastructure.graceful_degradation import GracefulDegradation


class PerformanceProfiler:
    """Performance measurement utilities."""
    
    def __init__(self):
        self.measurements = {}
        self.baseline_metrics = None
    
    def start_measurement(self, name: str) -> Dict[str, Any]:
        """Start performance measurement."""
        process = psutil.Process()
        
        # Force garbage collection for consistent measurements
        gc.collect()
        
        start_metrics = {
            'timestamp': time.perf_counter(),
            'cpu_percent': process.cpu_percent(),
            'memory_rss': process.memory_info().rss,
            'memory_vms': process.memory_info().vms,
            'threads': process.num_threads(),
            'open_files': len(process.open_files()) if hasattr(process, 'open_files') else 0,
            'connections': len(process.connections()) if hasattr(process, 'connections') else 0
        }
        
        self.measurements[name] = {'start': start_metrics}
        return start_metrics
    
    def end_measurement(self, name: str) -> Dict[str, Any]:
        """End performance measurement and calculate deltas."""
        if name not in self.measurements:
            raise ValueError(f"No measurement started for {name}")
        
        process = psutil.Process()
        
        end_metrics = {
            'timestamp': time.perf_counter(),
            'cpu_percent': process.cpu_percent(),
            'memory_rss': process.memory_info().rss,
            'memory_vms': process.memory_info().vms,
            'threads': process.num_threads(),
            'open_files': len(process.open_files()) if hasattr(process, 'open_files') else 0,
            'connections': len(process.connections()) if hasattr(process, 'connections') else 0
        }
        
        start_metrics = self.measurements[name]['start']
        
        deltas = {
            'duration': end_metrics['timestamp'] - start_metrics['timestamp'],
            'cpu_delta': end_metrics['cpu_percent'] - start_metrics['cpu_percent'],
            'memory_rss_delta': end_metrics['memory_rss'] - start_metrics['memory_rss'],
            'memory_vms_delta': end_metrics['memory_vms'] - start_metrics['memory_vms'],
            'threads_delta': end_metrics['threads'] - start_metrics['threads'],
            'open_files_delta': end_metrics['open_files'] - start_metrics['open_files'],
            'connections_delta': end_metrics['connections'] - start_metrics['connections']
        }
        
        self.measurements[name]['end'] = end_metrics
        self.measurements[name]['deltas'] = deltas
        
        return deltas
    
    def get_measurement(self, name: str) -> Optional[Dict[str, Any]]:
        """Get measurement results."""
        return self.measurements.get(name)
    
    def set_baseline(self):
        """Set current state as baseline for comparisons."""
        process = psutil.Process()
        gc.collect()
        
        self.baseline_metrics = {
            'timestamp': time.perf_counter(),
            'cpu_percent': process.cpu_percent(interval=0.1),
            'memory_rss': process.memory_info().rss,
            'memory_vms': process.memory_info().vms,
            'threads': process.num_threads()
        }
    
    def compare_to_baseline(self) -> Dict[str, Any]:
        """Compare current state to baseline."""
        if not self.baseline_metrics:
            raise ValueError("No baseline set")
        
        process = psutil.Process()
        current = {
            'timestamp': time.perf_counter(),
            'cpu_percent': process.cpu_percent(interval=0.1),
            'memory_rss': process.memory_info().rss,
            'memory_vms': process.memory_info().vms,
            'threads': process.num_threads()
        }
        
        return {
            'duration_since_baseline': current['timestamp'] - self.baseline_metrics['timestamp'],
            'cpu_delta': current['cpu_percent'] - self.baseline_metrics['cpu_percent'],
            'memory_rss_delta_mb': (current['memory_rss'] - self.baseline_metrics['memory_rss']) / (1024 * 1024),
            'memory_vms_delta_mb': (current['memory_vms'] - self.baseline_metrics['memory_vms']) / (1024 * 1024),
            'threads_delta': current['threads'] - self.baseline_metrics['threads']
        }


class TestMemoryGuardianPerformance:
    """Comprehensive performance tests for Memory Guardian system."""
    
    @pytest.fixture
    def profiler(self):
        """Create performance profiler instance."""
        return PerformanceProfiler()
    
    @pytest.fixture
    def performance_config(self):
        """Create configuration optimized for performance testing."""
        return MemoryGuardianConfig(
            enabled=True,
            thresholds=MemoryThresholds(warning=1000, critical=2000, emergency=3000),
            monitoring=MonitoringConfig(
                check_interval=0.1,  # Fast for performance testing
                check_interval_warning=0.05,
                check_interval_critical=0.025,
                log_memory_stats=False  # Reduce I/O during perf tests
            ),
            restart_policy=RestartPolicy(
                max_attempts=10,
                initial_cooldown=0.1,
                graceful_timeout=1
            ),
            process_command=['python', '-c', 'import time; time.sleep(100)'],
            persist_state=False  # Reduce I/O during perf tests
        )
    
    @pytest.mark.asyncio
    async def test_monitoring_overhead_detailed(self, performance_config, profiler):
        """Detailed analysis of memory monitoring overhead."""
        guardian = MemoryGuardian(performance_config)
        await guardian.initialize()
        
        try:
            # Set baseline before monitoring
            profiler.set_baseline()
            
            # Mock process for consistent testing
            guardian.process = MagicMock()
            guardian.process.poll.return_value = None
            guardian.process_pid = os.getpid()
            guardian.process_state = ProcessState.RUNNING
            
            # Mock memory readings for consistent results
            with patch.object(guardian, 'get_memory_usage', return_value=500.0):
                
                # Test different monitoring frequencies
                monitoring_results = {}
                
                for interval_name, interval in [
                    ('slow', 1.0),
                    ('normal', 0.1),
                    ('fast', 0.01),
                    ('extreme', 0.001)
                ]:
                    guardian.config.monitoring.check_interval = interval
                    
                    profiler.start_measurement(f'monitoring_{interval_name}')
                    
                    # Start monitoring
                    guardian.start_monitoring()
                    
                    # Run for measured duration
                    test_duration = 2.0  # seconds
                    await asyncio.sleep(test_duration)
                    
                    # Stop monitoring and measure
                    await guardian.stop_monitoring()
                    results = profiler.end_measurement(f'monitoring_{interval_name}')
                    
                    # Calculate monitoring overhead per check
                    expected_checks = test_duration / interval
                    actual_checks = guardian.memory_stats.samples if guardian.memory_stats.samples > 0 else expected_checks
                    
                    monitoring_results[interval_name] = {
                        'interval': interval,
                        'duration': results['duration'],
                        'expected_checks': expected_checks,
                        'actual_checks': actual_checks,
                        'cpu_overhead': results['cpu_delta'],
                        'memory_overhead_mb': results['memory_rss_delta'] / (1024 * 1024),
                        'overhead_per_check_ms': (results['duration'] / actual_checks * 1000) if actual_checks > 0 else 0
                    }
                    
                    # Brief pause between tests
                    await asyncio.sleep(0.5)
            
            # Analyze results
            for interval_name, result in monitoring_results.items():
                print(f"\nMonitoring overhead ({interval_name}, {result['interval']}s interval):")
                print(f"  Duration: {result['duration']:.3f}s")
                print(f"  Checks: {result['actual_checks']:.0f} (expected: {result['expected_checks']:.0f})")
                print(f"  CPU overhead: {result['cpu_overhead']:.2f}%")
                print(f"  Memory overhead: {result['memory_overhead_mb']:.2f}MB")
                print(f"  Per-check overhead: {result['overhead_per_check_ms']:.3f}ms")
            
            # Performance assertions
            normal_result = monitoring_results['normal']
            assert normal_result['cpu_overhead'] < 10.0, f"CPU overhead too high: {normal_result['cpu_overhead']}%"
            assert normal_result['memory_overhead_mb'] < 10.0, f"Memory overhead too high: {normal_result['memory_overhead_mb']}MB"
            assert normal_result['overhead_per_check_ms'] < 5.0, f"Per-check overhead too high: {normal_result['overhead_per_check_ms']}ms"
        
        finally:
            await guardian.shutdown()
    
    @pytest.mark.asyncio
    async def test_state_serialization_performance_comprehensive(self, profiler):
        """Comprehensive state serialization performance testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "perf_state.json"
            
            manager = StateManager(state_file=state_file)
            await manager.initialize()
            
            try:
                # Test different state sizes
                serialization_results = {}
                
                for size_name, data_generator in [
                    ('small', lambda: self._generate_state_data(1, 10)),
                    ('medium', lambda: self._generate_state_data(10, 100)), 
                    ('large', lambda: self._generate_state_data(100, 1000)),
                    ('huge', lambda: self._generate_state_data(500, 2000))
                ]:
                    state_data = data_generator()
                    
                    # Measure serialization (save)
                    profiler.start_measurement(f'serialize_{size_name}')
                    await manager.persist_state(state_data)
                    serialize_results = profiler.end_measurement(f'serialize_{size_name}')
                    
                    # Get file size
                    file_size_mb = state_file.stat().st_size / (1024 * 1024)
                    
                    # Measure deserialization (load)
                    profiler.start_measurement(f'deserialize_{size_name}')
                    loaded_data = await manager.restore_state()
                    deserialize_results = profiler.end_measurement(f'deserialize_{size_name}')
                    
                    # Verify data integrity
                    assert loaded_data is not None
                    assert len(loaded_data) == len(state_data)
                    
                    serialization_results[size_name] = {
                        'file_size_mb': file_size_mb,
                        'serialize_time': serialize_results['duration'],
                        'deserialize_time': deserialize_results['duration'],
                        'serialize_throughput_mb_s': file_size_mb / serialize_results['duration'],
                        'deserialize_throughput_mb_s': file_size_mb / deserialize_results['duration'],
                        'serialize_memory_delta_mb': serialize_results['memory_rss_delta'] / (1024 * 1024),
                        'deserialize_memory_delta_mb': deserialize_results['memory_rss_delta'] / (1024 * 1024)
                    }
                    
                    print(f"\nSerialization performance ({size_name}, {file_size_mb:.2f}MB):")
                    print(f"  Serialize: {serialize_results['duration']:.3f}s ({serialization_results[size_name]['serialize_throughput_mb_s']:.1f} MB/s)")
                    print(f"  Deserialize: {deserialize_results['duration']:.3f}s ({serialization_results[size_name]['deserialize_throughput_mb_s']:.1f} MB/s)")
                    print(f"  Memory delta: +{serialization_results[size_name]['serialize_memory_delta_mb']:.1f}MB / +{serialization_results[size_name]['deserialize_memory_delta_mb']:.1f}MB")
                
                # Performance assertions
                medium_result = serialization_results['medium']
                assert medium_result['serialize_time'] < 5.0, f"Serialize too slow: {medium_result['serialize_time']}s"
                assert medium_result['deserialize_time'] < 5.0, f"Deserialize too slow: {medium_result['deserialize_time']}s"
                assert medium_result['serialize_throughput_mb_s'] > 1.0, f"Serialize throughput too low: {medium_result['serialize_throughput_mb_s']} MB/s"
            
            finally:
                await manager.shutdown()
    
    def _generate_state_data(self, conv_count: int, msg_per_conv: int) -> Dict[str, Any]:
        """Generate test state data of specified size."""
        return {
            'conversations': [
                {
                    'id': f'conv_{i}',
                    'created': time.time(),
                    'messages': [
                        {
                            'id': f'msg_{j}',
                            'role': 'user' if j % 2 == 0 else 'assistant',
                            'content': f'Test message {j} with some content ' * 50,
                            'timestamp': time.time()
                        }
                        for j in range(msg_per_conv)
                    ]
                }
                for i in range(conv_count)
            ],
            'metadata': {
                'version': '1.0.0',
                'created': time.time(),
                'uuid': str(uuid.uuid4()),
                'large_data': 'x' * 10000  # 10KB padding
            }
        }
    
    @pytest.mark.asyncio
    async def test_restart_cycle_performance_analysis(self, performance_config, profiler):
        """Analyze restart cycle performance under various conditions."""
        guardian = MemoryGuardian(performance_config)
        await guardian.initialize()
        
        try:
            restart_results = {}
            
            # Test different restart scenarios
            scenarios = [
                ('immediate', 0.0),      # Immediate restart
                ('short_delay', 0.1),    # 100ms delay
                ('normal_delay', 1.0),   # 1s delay
                ('long_delay', 5.0)      # 5s delay
            ]
            
            for scenario_name, delay in scenarios:
                # Configure restart timing
                guardian.config.restart_policy.initial_cooldown = delay
                guardian.config.restart_policy.graceful_timeout = max(1, delay)
                
                # Mock process operations for performance testing
                start_call_count = 0
                terminate_call_count = 0
                
                async def mock_start(*args, **kwargs):
                    nonlocal start_call_count
                    start_call_count += 1
                    await asyncio.sleep(0.01)  # Simulate startup time
                    return True
                
                async def mock_terminate(*args, **kwargs):
                    nonlocal terminate_call_count
                    terminate_call_count += 1
                    await asyncio.sleep(delay / 10)  # Simulate shutdown time
                    return True
                
                with patch.object(guardian, 'start_process', side_effect=mock_start):
                    with patch.object(guardian, 'terminate_process', side_effect=mock_terminate):
                        
                        # Measure restart performance
                        profiler.start_measurement(f'restart_{scenario_name}')
                        
                        success = await guardian.restart_process(f"Performance test {scenario_name}")
                        
                        results = profiler.end_measurement(f'restart_{scenario_name}')
                        
                        restart_results[scenario_name] = {
                            'delay': delay,
                            'success': success,
                            'duration': results['duration'],
                            'start_calls': start_call_count,
                            'terminate_calls': terminate_call_count,
                            'memory_delta_mb': results['memory_rss_delta'] / (1024 * 1024),
                            'restart_overhead_ms': results['duration'] * 1000
                        }
                        
                        print(f"\nRestart cycle performance ({scenario_name}, {delay}s delay):")
                        print(f"  Duration: {results['duration']:.3f}s")
                        print(f"  Success: {success}")
                        print(f"  Memory delta: {restart_results[scenario_name]['memory_delta_mb']:.2f}MB")
                        print(f"  Overhead: {restart_results[scenario_name]['restart_overhead_ms']:.1f}ms")
            
            # Performance assertions
            immediate_result = restart_results['immediate']
            assert immediate_result['success'], "Immediate restart should succeed"
            assert immediate_result['duration'] < 1.0, f"Immediate restart too slow: {immediate_result['duration']}s"
            
            normal_result = restart_results['normal_delay']
            assert normal_result['duration'] < 10.0, f"Normal restart too slow: {normal_result['duration']}s"
        
        finally:
            await guardian.shutdown()
    
    @pytest.mark.asyncio
    async def test_resource_usage_profiling(self, performance_config, profiler):
        """Profile resource usage under sustained load."""
        guardian = MemoryGuardian(performance_config)
        await guardian.initialize()
        
        try:
            # Mock process for consistent testing
            guardian.process = MagicMock()
            guardian.process.poll.return_value = None
            guardian.process_pid = os.getpid()
            guardian.process_state = ProcessState.RUNNING
            
            # Profile resource usage over time
            profiler.set_baseline()
            
            resource_samples = []
            memory_values = [100, 200, 500, 800, 1200, 900, 400, 150]  # Varying memory pattern
            
            with patch.object(guardian, 'get_memory_usage') as mock_memory:
                guardian.start_monitoring()
                
                # Sample resource usage over time
                for i, memory_val in enumerate(memory_values):
                    mock_memory.return_value = memory_val
                    
                    # Wait for monitoring cycle
                    await asyncio.sleep(0.2)
                    
                    # Collect resource sample
                    baseline_comparison = profiler.compare_to_baseline()
                    process = psutil.Process()
                    
                    sample = {
                        'timestamp': time.time(),
                        'memory_reading': memory_val,
                        'memory_state': guardian.memory_state.value,
                        'cpu_percent': process.cpu_percent(),
                        'memory_rss_mb': process.memory_info().rss / (1024 * 1024),
                        'memory_delta_from_baseline_mb': baseline_comparison['memory_rss_delta_mb'],
                        'threads': process.num_threads(),
                        'monitoring_samples': guardian.memory_stats.samples
                    }
                    
                    resource_samples.append(sample)
                
                await guardian.stop_monitoring()
            
            # Analyze resource usage patterns
            max_cpu = max(s['cpu_percent'] for s in resource_samples)
            max_memory_delta = max(s['memory_delta_from_baseline_mb'] for s in resource_samples)
            total_samples = resource_samples[-1]['monitoring_samples']
            
            print(f"\nResource usage profiling:")
            print(f"  Samples collected: {len(resource_samples)}")
            print(f"  Monitoring samples: {total_samples}")
            print(f"  Peak CPU: {max_cpu:.2f}%")
            print(f"  Peak memory delta: {max_memory_delta:.2f}MB")
            print(f"  Memory states seen: {set(s['memory_state'] for s in resource_samples)}")
            
            # Performance assertions
            assert max_cpu < 25.0, f"CPU usage too high: {max_cpu}%"
            assert max_memory_delta < 50.0, f"Memory growth too high: {max_memory_delta}MB"
            assert total_samples > len(memory_values), "Should have multiple monitoring samples"
        
        finally:
            await guardian.shutdown()
    
    @pytest.mark.asyncio
    async def test_scalability_multiple_instances(self, profiler):
        """Test performance scalability with multiple Memory Guardian instances."""
        instances = []
        instance_count = 5
        
        try:
            profiler.set_baseline()
            profiler.start_measurement('multi_instance_startup')
            
            # Create multiple instances
            for i in range(instance_count):
                config = MemoryGuardianConfig(
                    enabled=True,
                    thresholds=MemoryThresholds(warning=500, critical=1000, emergency=1500),
                    monitoring=MonitoringConfig(check_interval=0.1 + (i * 0.02)),  # Stagger intervals
                    process_command=['python', '-c', f'import time; time.sleep(10)'],
                    persist_state=False
                )
                
                guardian = MemoryGuardian(config)
                await guardian.initialize()
                instances.append(guardian)
            
            startup_results = profiler.end_measurement('multi_instance_startup')
            
            # Start monitoring on all instances
            profiler.start_measurement('multi_instance_monitoring')
            
            for guardian in instances:
                # Mock process for each instance
                guardian.process = MagicMock()
                guardian.process.poll.return_value = None
                guardian.process_pid = os.getpid() + len(instances)  # Fake different PIDs
                guardian.process_state = ProcessState.RUNNING
                
                guardian.start_monitoring()
            
            # Mock memory readings for all instances
            with patch('claude_mpm.services.infrastructure.memory_guardian.MemoryGuardian.get_memory_usage', return_value=300.0):
                # Let them run concurrently
                await asyncio.sleep(3.0)
            
            # Stop all monitoring
            for guardian in instances:
                await guardian.stop_monitoring()
            
            monitoring_results = profiler.end_measurement('multi_instance_monitoring')
            
            # Analyze scalability
            total_samples = sum(g.memory_stats.samples for g in instances)
            avg_samples_per_instance = total_samples / instance_count
            
            print(f"\nScalability test ({instance_count} instances):")
            print(f"  Startup time: {startup_results['duration']:.3f}s")
            print(f"  Startup memory delta: {startup_results['memory_rss_delta'] / (1024 * 1024):.2f}MB")
            print(f"  Monitoring duration: {monitoring_results['duration']:.3f}s")
            print(f"  Monitoring memory delta: {monitoring_results['memory_rss_delta'] / (1024 * 1024):.2f}MB")
            print(f"  Total monitoring samples: {total_samples}")
            print(f"  Avg samples per instance: {avg_samples_per_instance:.1f}")
            print(f"  CPU delta: {monitoring_results['cpu_delta']:.2f}%")
            
            # Performance assertions
            startup_memory_mb = startup_results['memory_rss_delta'] / (1024 * 1024)
            monitoring_memory_mb = monitoring_results['memory_rss_delta'] / (1024 * 1024)
            
            assert startup_results['duration'] < 10.0, f"Multi-instance startup too slow: {startup_results['duration']}s"
            assert startup_memory_mb < 100.0, f"Startup memory usage too high: {startup_memory_mb}MB"
            assert monitoring_memory_mb < 100.0, f"Monitoring memory usage too high: {monitoring_memory_mb}MB"
            assert monitoring_results['cpu_delta'] < 30.0, f"CPU usage too high: {monitoring_results['cpu_delta']}%"
        
        finally:
            # Cleanup all instances
            for guardian in instances:
                await guardian.shutdown()
    
    @pytest.mark.asyncio
    async def test_memory_leak_detection_performance(self, profiler):
        """Test performance of memory leak detection algorithms."""
        protection = RestartProtection()
        await protection.initialize()
        
        try:
            # Test leak detection with different sample sizes
            leak_detection_results = {}
            
            sample_sizes = [10, 50, 100, 500, 1000, 2000]
            
            for sample_size in sample_sizes:
                # Clear previous samples
                protection.memory_samples.clear()
                
                # Generate memory samples with gradual increase (simulating leak)
                base_memory = 200.0
                leak_rate = 5.0  # MB per sample
                
                profiler.start_measurement(f'leak_detection_{sample_size}')
                
                for i in range(sample_size):
                    memory_mb = base_memory + (i * leak_rate) + (i * 0.1 * (i % 10))  # Add some noise
                    protection.record_memory_sample(memory_mb)
                
                # Detect memory leak
                trend = protection.detect_memory_leak()
                
                results = profiler.end_measurement(f'leak_detection_{sample_size}')
                
                leak_detection_results[sample_size] = {
                    'sample_size': sample_size,
                    'detection_time': results['duration'],
                    'detection_time_ms': results['duration'] * 1000,
                    'memory_delta_mb': results['memory_rss_delta'] / (1024 * 1024),
                    'leak_detected': trend.is_leak_suspected if trend else False,
                    'trend_slope': trend.slope_mb_per_minute if trend else None,
                    'samples_per_ms': sample_size / (results['duration'] * 1000)
                }
                
                print(f"\nLeak detection performance ({sample_size} samples):")
                print(f"  Detection time: {results['duration']*1000:.2f}ms")
                print(f"  Memory delta: {leak_detection_results[sample_size]['memory_delta_mb']:.2f}MB")
                print(f"  Leak detected: {leak_detection_results[sample_size]['leak_detected']}")
                print(f"  Processing rate: {leak_detection_results[sample_size]['samples_per_ms']:.1f} samples/ms")
            
            # Performance assertions
            result_1000 = leak_detection_results[1000]
            assert result_1000['detection_time'] < 0.5, f"Leak detection too slow for 1000 samples: {result_1000['detection_time']}s"
            assert result_1000['samples_per_ms'] > 100, f"Processing rate too low: {result_1000['samples_per_ms']} samples/ms"
        
        finally:
            await protection.shutdown()
    
    @pytest.mark.asyncio
    async def test_dashboard_metrics_performance(self, profiler):
        """Test performance of dashboard metrics collection and export."""
        # Create mock services
        guardian = MagicMock()
        guardian.get_status.return_value = {
            'enabled': True,
            'process': {'state': 'running', 'pid': 12345, 'uptime_hours': 2.5},
            'memory': {
                'current_mb': 500.0,
                'peak_mb': 750.0,
                'average_mb': 400.0,
                'state': 'warning',
                'thresholds': {'warning_mb': 400, 'critical_mb': 800, 'emergency_mb': 1200}
            },
            'restarts': {'total': 3, 'consecutive_failures': 0, 'can_restart': True},
            'monitoring': {'active': True, 'samples': 1500}
        }
        
        restart_protection = MagicMock()
        restart_protection.get_restart_statistics.return_value = MagicMock(
            total_restarts=3,
            consecutive_failures=0,
            circuit_state='closed',
            recent_restart_times=[time.time() - 300, time.time() - 150]
        )
        
        with tempfile.TemporaryDirectory() as tmpdir:
            metrics_file = Path(tmpdir) / "metrics.json"
            
            dashboard = MemoryDashboard(
                memory_guardian=guardian,
                restart_protection=restart_protection,
                metrics_file=metrics_file
            )
            
            await dashboard.initialize()
            
            try:
                # Test metrics collection performance
                profiler.start_measurement('metrics_collection')
                
                metrics_collected = []
                for i in range(100):
                    metrics = dashboard.get_current_metrics()
                    metrics_collected.append(metrics)
                
                collection_results = profiler.end_measurement('metrics_collection')
                
                # Test dashboard data generation
                profiler.start_measurement('dashboard_data')
                
                dashboard_data_generated = []
                for i in range(50):
                    data = dashboard.get_dashboard_data()
                    dashboard_data_generated.append(data)
                
                dashboard_results = profiler.end_measurement('dashboard_data')
                
                # Test Prometheus export
                profiler.start_measurement('prometheus_export')
                
                prometheus_exports = []
                for i in range(20):
                    export = dashboard.export_prometheus_metrics()
                    prometheus_exports.append(export)
                
                prometheus_results = profiler.end_measurement('prometheus_export')
                
                # Analyze performance
                avg_collection_time = collection_results['duration'] / 100
                avg_dashboard_time = dashboard_results['duration'] / 50
                avg_prometheus_time = prometheus_results['duration'] / 20
                
                print(f"\nDashboard performance:")
                print(f"  Metrics collection: {avg_collection_time*1000:.3f}ms avg ({100/collection_results['duration']:.1f} ops/s)")
                print(f"  Dashboard data: {avg_dashboard_time*1000:.3f}ms avg ({50/dashboard_results['duration']:.1f} ops/s)")
                print(f"  Prometheus export: {avg_prometheus_time*1000:.3f}ms avg ({20/prometheus_results['duration']:.1f} ops/s)")
                
                # Verify data quality
                assert len(metrics_collected) == 100
                assert len(dashboard_data_generated) == 50
                assert len(prometheus_exports) == 20
                
                # Performance assertions
                assert avg_collection_time < 0.01, f"Metrics collection too slow: {avg_collection_time*1000:.3f}ms"
                assert avg_dashboard_time < 0.02, f"Dashboard data generation too slow: {avg_dashboard_time*1000:.3f}ms"
                assert avg_prometheus_time < 0.05, f"Prometheus export too slow: {avg_prometheus_time*1000:.3f}ms"
            
            finally:
                await dashboard.shutdown()
    
    @pytest.mark.asyncio
    async def test_concurrent_operations_performance(self, performance_config, profiler):
        """Test performance under concurrent operations."""
        guardian = MemoryGuardian(performance_config)
        await guardian.initialize()
        
        try:
            # Mock process
            guardian.process = MagicMock()
            guardian.process.poll.return_value = None
            guardian.process_pid = os.getpid()
            guardian.process_state = ProcessState.RUNNING
            
            # Test concurrent monitoring and restart operations
            profiler.start_measurement('concurrent_ops')
            
            with patch.object(guardian, 'get_memory_usage', return_value=400.0):
                with patch.object(guardian, 'start_process', return_value=True):
                    with patch.object(guardian, 'terminate_process', return_value=True):
                        
                        # Start monitoring
                        guardian.start_monitoring()
                        
                        # Launch concurrent operations
                        operations = []
                        
                        # Multiple monitoring cycles
                        for _ in range(10):
                            operations.append(guardian.monitor_memory())
                        
                        # Multiple restart attempts (should be serialized)
                        for i in range(3):
                            operations.append(guardian.restart_process(f"Concurrent test {i}"))
                        
                        # Execute all operations concurrently
                        results = await asyncio.gather(*operations, return_exceptions=True)
                        
                        await guardian.stop_monitoring()
            
            concurrent_results = profiler.end_measurement('concurrent_ops')
            
            # Analyze results
            successful_ops = len([r for r in results if not isinstance(r, Exception)])
            restart_results = [r for r in results[-3:] if isinstance(r, bool)]
            successful_restarts = sum(1 for r in restart_results if r is True)
            
            print(f"\nConcurrent operations performance:")
            print(f"  Total duration: {concurrent_results['duration']:.3f}s")
            print(f"  Successful operations: {successful_ops}/{len(operations)}")
            print(f"  Successful restarts: {successful_restarts}/{len(restart_results)}")
            print(f"  Memory delta: {concurrent_results['memory_rss_delta'] / (1024 * 1024):.2f}MB")
            print(f"  CPU delta: {concurrent_results['cpu_delta']:.2f}%")
            
            # Performance assertions
            assert concurrent_results['duration'] < 15.0, f"Concurrent operations too slow: {concurrent_results['duration']}s"
            assert successful_ops >= len(operations) * 0.8, f"Too many operation failures: {successful_ops}/{len(operations)}"
            # Should prevent most concurrent restarts
            assert successful_restarts <= 1, f"Too many concurrent restarts allowed: {successful_restarts}"
        
        finally:
            await guardian.shutdown()


class TestPlatformSpecificPerformance:
    """Test platform-specific performance characteristics."""
    
    @pytest.mark.skipif(platform.system() != 'Darwin', reason="macOS-specific test")
    @pytest.mark.asyncio
    async def test_macos_performance(self):
        """Test macOS-specific performance characteristics."""
        from claude_mpm.utils.platform_memory import get_memory_info_macos
        
        # Test macOS memory monitoring performance
        start_time = time.perf_counter()
        
        memory_readings = []
        for _ in range(100):
            info = get_memory_info_macos(os.getpid())
            if info:
                memory_readings.append(info.rss_mb)
        
        duration = time.perf_counter() - start_time
        avg_time_ms = (duration / 100) * 1000
        
        print(f"\nmacOS memory monitoring performance:")
        print(f"  100 readings in {duration:.3f}s")
        print(f"  Average per reading: {avg_time_ms:.3f}ms")
        print(f"  Readings per second: {100/duration:.1f}")
        
        assert len(memory_readings) == 100
        assert avg_time_ms < 10.0, f"macOS memory reading too slow: {avg_time_ms:.3f}ms"
    
    @pytest.mark.skipif(platform.system() != 'Linux', reason="Linux-specific test")
    @pytest.mark.asyncio
    async def test_linux_performance(self):
        """Test Linux-specific performance characteristics."""
        from claude_mpm.utils.platform_memory import get_memory_info_linux
        
        # Test Linux memory monitoring performance
        start_time = time.perf_counter()
        
        memory_readings = []
        for _ in range(100):
            info = get_memory_info_linux(os.getpid())
            if info:
                memory_readings.append(info.rss_mb)
        
        duration = time.perf_counter() - start_time
        avg_time_ms = (duration / 100) * 1000
        
        print(f"\nLinux memory monitoring performance:")
        print(f"  100 readings in {duration:.3f}s")
        print(f"  Average per reading: {avg_time_ms:.3f}ms")
        print(f"  Readings per second: {100/duration:.1f}")
        
        assert len(memory_readings) == 100
        assert avg_time_ms < 5.0, f"Linux memory reading too slow: {avg_time_ms:.3f}ms"
    
    @pytest.mark.skipif(platform.system() != 'Windows', reason="Windows-specific test")
    @pytest.mark.asyncio
    async def test_windows_performance(self):
        """Test Windows-specific performance characteristics."""
        from claude_mpm.utils.platform_memory import get_memory_info_windows
        
        # Test Windows memory monitoring performance
        start_time = time.perf_counter()
        
        memory_readings = []
        for _ in range(100):
            info = get_memory_info_windows(os.getpid())
            if info:
                memory_readings.append(info.rss_mb)
        
        duration = time.perf_counter() - start_time
        avg_time_ms = (duration / 100) * 1000
        
        print(f"\nWindows memory monitoring performance:")
        print(f"  100 readings in {duration:.3f}s")
        print(f"  Average per reading: {avg_time_ms:.3f}ms")
        print(f"  Readings per second: {100/duration:.1f}")
        
        assert len(memory_readings) == 100
        assert avg_time_ms < 15.0, f"Windows memory reading too slow: {avg_time_ms:.3f}ms"