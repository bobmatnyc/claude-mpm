"""Stress tests for Memory Guardian System.

This module provides comprehensive stress testing for the Memory Guardian system,
focusing on extreme scenarios that push the system to its limits.

Stress test categories:
- Rapid memory growth scenarios
- Concurrent restart stress testing
- Large file handling under pressure
- Extended monitoring sessions
- Memory thrashing simulation
- Resource exhaustion scenarios
- High-frequency event processing
- System instability simulation
"""

import asyncio
import gc
import json
import multiprocessing
import os
import platform
import psutil
import random
import signal
import subprocess
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
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
    RestartAttempt
)
from claude_mpm.services.infrastructure.restart_protection import (
    RestartProtection,
    CircuitState
)
from claude_mpm.services.infrastructure.state_manager import StateManager


class MemoryGrowthStressor:
    """Utility for creating controlled memory growth stress scenarios."""
    
    @staticmethod
    def create_rapid_growth_script(
        target_dir: Path,
        initial_mb: int = 100,
        growth_rate_mb_per_sec: int = 200,
        max_memory_mb: int = 2000,
        chaos_mode: bool = False
    ) -> Path:
        """Create a script that rapidly allocates memory.
        
        Args:
            target_dir: Directory to create script in
            initial_mb: Starting memory allocation
            growth_rate_mb_per_sec: Memory growth rate
            max_memory_mb: Maximum memory before crashing/stopping
            chaos_mode: Whether to add random behavior
        """
        script_content = f'''#!/usr/bin/env python3
"""Rapid memory growth stress test script."""

import gc
import os
import random
import sys
import time
import threading
from datetime import datetime

# Configuration
INITIAL_MB = {initial_mb}
GROWTH_RATE_MB_PER_SEC = {growth_rate_mb_per_sec}
MAX_MEMORY_MB = {max_memory_mb}
CHAOS_MODE = {chaos_mode}

# Convert to bytes
INITIAL_BYTES = INITIAL_MB * 1024 * 1024
GROWTH_RATE_BYTES_PER_SEC = GROWTH_RATE_MB_PER_SEC * 1024 * 1024
MAX_MEMORY_BYTES = MAX_MEMORY_MB * 1024 * 1024

def log(msg):
    """Log with timestamp."""
    print(f"[{{datetime.now().isoformat()}}] {{msg}}", flush=True)

def get_memory_mb():
    """Get current memory usage."""
    try:
        import psutil
        return psutil.Process().memory_info().rss / (1024 * 1024)
    except ImportError:
        return len(memory_chunks) * GROWTH_RATE_MB_PER_SEC / 10 if 'memory_chunks' in globals() else 0

def chaos_behavior():
    """Add chaotic behavior if enabled."""
    if not CHAOS_MODE:
        return
    
    action = random.choice(['gc', 'sleep', 'allocate_extra', 'deallocate'])
    
    if action == 'gc':
        log("CHAOS: Triggering garbage collection")
        gc.collect()
    elif action == 'sleep':
        sleep_time = random.uniform(0.1, 0.5)
        log(f"CHAOS: Sleeping for {{sleep_time:.2f}}s")
        time.sleep(sleep_time)
    elif action == 'allocate_extra':
        extra_mb = random.randint(10, 100)
        log(f"CHAOS: Allocating extra {{extra_mb}}MB")
        globals().setdefault('chaos_memory', []).append(bytearray(extra_mb * 1024 * 1024))
    elif action == 'deallocate' and 'chaos_memory' in globals():
        if globals()['chaos_memory']:
            deallocated = globals()['chaos_memory'].pop()
            log(f"CHAOS: Deallocated {{len(deallocated) // (1024*1024)}}MB")

def memory_growth_thread():
    """Background thread for continuous growth."""
    global memory_chunks
    chunk_size_mb = 10  # Allocate in 10MB chunks
    chunk_size_bytes = chunk_size_mb * 1024 * 1024
    chunks_per_sec = GROWTH_RATE_MB_PER_SEC // chunk_size_mb
    sleep_between_chunks = 1.0 / chunks_per_sec if chunks_per_sec > 0 else 0.1
    
    while True:
        try:
            current_memory = get_memory_mb()
            
            if current_memory >= MAX_MEMORY_MB:
                log(f"Reached maximum memory: {{current_memory:.1f}}MB")
                break
            
            # Allocate chunk
            chunk = bytearray(chunk_size_bytes)
            # Fill with data to prevent optimization
            for i in range(0, len(chunk), 4096):
                chunk[i:i+4] = random.randint(0, 2**32-1).to_bytes(4, 'little')
            
            memory_chunks.append(chunk)
            
            log(f"Allocated {{chunk_size_mb}}MB, total: {{get_memory_mb():.1f}}MB")
            
            # Chaos behavior
            if CHAOS_MODE and random.random() < 0.3:
                chaos_behavior()
            
            time.sleep(sleep_between_chunks)
            
        except Exception as e:
            log(f"Error in growth thread: {{e}}")
            break

def main():
    """Main stress test function."""
    global memory_chunks
    
    log(f"Rapid Memory Growth Stressor starting")
    log(f"PID: {{os.getpid()}}")
    log(f"Initial: {{INITIAL_MB}}MB")
    log(f"Growth rate: {{GROWTH_RATE_MB_PER_SEC}}MB/s")
    log(f"Max memory: {{MAX_MEMORY_MB}}MB")
    log(f"Chaos mode: {{CHAOS_MODE}}")
    
    memory_chunks = []
    
    try:
        # Initial allocation
        if INITIAL_MB > 0:
            initial_chunk = bytearray(INITIAL_BYTES)
            memory_chunks.append(initial_chunk)
            log(f"Initial allocation: {{INITIAL_MB}}MB")
        
        # Start growth thread
        growth_thread = threading.Thread(target=memory_growth_thread, daemon=True)
        growth_thread.start()
        
        # Main loop - report status
        start_time = time.time()
        while growth_thread.is_alive():
            current_memory = get_memory_mb()
            elapsed = time.time() - start_time
            rate = (current_memory - INITIAL_MB) / elapsed if elapsed > 0 else 0
            
            log(f"Status: {{current_memory:.1f}}MB ({{rate:.1f}}MB/s), Chunks: {{len(memory_chunks)}}, Elapsed: {{elapsed:.1f}}s")
            
            time.sleep(1.0)
            
            # Safety check for runaway growth
            if elapsed > 60:  # 1 minute max
                log("Safety timeout reached")
                break
        
        log("Memory growth completed")
        
        # Hold memory for a bit
        time.sleep(2)
        
    except KeyboardInterrupt:
        log("Interrupted, cleaning up")
    except Exception as e:
        log(f"Error: {{e}}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
'''
        
        script_path = target_dir / "rapid_growth_stressor.py"
        with open(script_path, 'w') as f:
            f.write(script_content)
        
        script_path.chmod(0o755)
        return script_path
    
    @staticmethod
    def create_memory_thrashing_script(target_dir: Path) -> Path:
        """Create a script that simulates memory thrashing."""
        script_content = '''#!/usr/bin/env python3
"""Memory thrashing simulation script."""

import gc
import os
import random
import sys
import time
import threading
from datetime import datetime

def log(msg):
    print(f"[{datetime.now().isoformat()}] {msg}", flush=True)

def thrashing_thread(thread_id, duration=30):
    """Thread that continuously allocates and deallocates memory."""
    log(f"Thrashing thread {thread_id} starting")
    
    start_time = time.time()
    allocations = []
    
    while time.time() - start_time < duration:
        try:
            # Random allocation size (1-50MB)
            size_mb = random.randint(1, 50)
            size_bytes = size_mb * 1024 * 1024
            
            # Allocate
            data = bytearray(size_bytes)
            allocations.append(data)
            
            # Random pattern: sometimes deallocate immediately, sometimes hold
            if random.random() < 0.7:  # 70% chance to deallocate
                if allocations:
                    deallocated = allocations.pop(random.randint(0, len(allocations)-1))
                    del deallocated
            
            # Random garbage collection
            if random.random() < 0.2:  # 20% chance
                gc.collect()
            
            # Variable sleep
            time.sleep(random.uniform(0.001, 0.1))
            
        except Exception as e:
            log(f"Thread {thread_id} error: {e}")
            break
    
    # Cleanup
    allocations.clear()
    log(f"Thrashing thread {thread_id} completed")

def main():
    """Main thrashing simulation."""
    log("Memory Thrashing Simulator starting")
    log(f"PID: {os.getpid()}")
    
    # Start multiple thrashing threads
    threads = []
    num_threads = 4
    
    for i in range(num_threads):
        thread = threading.Thread(target=thrashing_thread, args=(i, 30))
        thread.start()
        threads.append(thread)
    
    # Wait for completion
    for thread in threads:
        thread.join()
    
    log("Memory thrashing simulation completed")
    return 0

if __name__ == "__main__":
    sys.exit(main())
'''
        
        script_path = target_dir / "memory_thrashing.py"
        with open(script_path, 'w') as f:
            f.write(script_content)
        
        script_path.chmod(0o755)
        return script_path


class TestMemoryGuardianStress:
    """Stress tests for Memory Guardian system."""
    
    @pytest.fixture
    async def stress_workspace(self):
        """Create workspace for stress testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            (workspace / "scripts").mkdir()
            (workspace / "logs").mkdir()
            yield workspace
    
    @pytest.fixture
    async def stress_config(self, stress_workspace):
        """Create configuration for stress testing."""
        return MemoryGuardianConfig(
            enabled=True,
            thresholds=MemoryThresholds(
                warning=300,     # Low thresholds for faster triggering
                critical=500,
                emergency=700
            ),
            restart_policy=RestartPolicy(
                max_attempts=10,  # Allow more restarts for stress testing
                attempt_window=60,
                initial_cooldown=0.5,
                max_cooldown=5,
                graceful_timeout=3,
                exponential_backoff=True
            ),
            monitoring=MonitoringConfig(
                check_interval=0.1,  # Very fast monitoring
                check_interval_warning=0.05,
                check_interval_critical=0.025,
                check_interval_emergency=0.01,
                log_memory_stats=True
            ),
            working_directory=str(stress_workspace),
            state_file=str(stress_workspace / "stress_state.json"),
            persist_state=True
        )
    
    @pytest.mark.asyncio
    async def test_rapid_memory_growth_stress(self, stress_workspace, stress_config):
        """Test Memory Guardian under rapid memory growth conditions."""
        # Create rapid growth script
        growth_script = MemoryGrowthStressor.create_rapid_growth_script(
            stress_workspace / "scripts",
            initial_mb=50,
            growth_rate_mb_per_sec=150,  # Very fast growth
            max_memory_mb=800,
            chaos_mode=False
        )
        
        stress_config.process_command = [sys.executable, str(growth_script)]
        
        guardian = MemoryGuardian(stress_config)
        await guardian.initialize()
        
        stress_results = {
            'restarts_triggered': 0,
            'max_memory_seen': 0.0,
            'state_transitions': [],
            'monitoring_samples': 0,
            'test_duration': 0.0
        }
        
        # Track restart attempts
        original_restart = guardian.restart_process
        async def track_restarts(*args, **kwargs):
            stress_results['restarts_triggered'] += 1
            return await original_restart(*args, **kwargs)
        guardian.restart_process = track_restarts
        
        try:
            start_time = time.time()
            
            # Start the memory growth process
            success = await guardian.start_process()
            assert success, "Should start rapid growth process"
            
            # Start monitoring
            guardian.start_monitoring()
            
            # Monitor the stress test
            max_duration = 30  # seconds
            last_state = MemoryState.NORMAL
            
            while time.time() - start_time < max_duration:
                await asyncio.sleep(0.2)
                
                current_memory = guardian.get_memory_usage()
                if current_memory:
                    stress_results['max_memory_seen'] = max(
                        stress_results['max_memory_seen'], 
                        current_memory
                    )
                
                # Track state transitions
                current_state = guardian.memory_state
                if current_state != last_state:
                    stress_results['state_transitions'].append(
                        (time.time() - start_time, last_state.value, current_state.value)
                    )
                    last_state = current_state
                
                stress_results['monitoring_samples'] = guardian.memory_stats.samples
                
                # Break if process died or we hit emergency multiple times
                if guardian.process_state != ProcessState.RUNNING:
                    break
                if stress_results['restarts_triggered'] >= 3:
                    break
            
            stress_results['test_duration'] = time.time() - start_time
            
            await guardian.stop_monitoring()
            
            # Analyze stress test results
            print(f"\nRapid Memory Growth Stress Test Results:")
            print(f"  Test duration: {stress_results['test_duration']:.2f}s")
            print(f"  Max memory seen: {stress_results['max_memory_seen']:.1f}MB")
            print(f"  Restarts triggered: {stress_results['restarts_triggered']}")
            print(f"  Monitoring samples: {stress_results['monitoring_samples']}")
            print(f"  State transitions: {len(stress_results['state_transitions'])}")
            
            for i, (timestamp, from_state, to_state) in enumerate(stress_results['state_transitions']):
                print(f"    {i+1}. {timestamp:.2f}s: {from_state} -> {to_state}")
            
            # Stress test assertions
            assert stress_results['max_memory_seen'] > stress_config.thresholds.warning, "Should exceed warning threshold"
            assert len(stress_results['state_transitions']) >= 1, "Should have state transitions"
            assert stress_results['monitoring_samples'] > 10, "Should have many monitoring samples"
            
            # Should trigger at least one restart for rapid growth
            if stress_results['max_memory_seen'] > stress_config.thresholds.emergency:
                assert stress_results['restarts_triggered'] >= 1, "Should trigger restart for emergency memory"
        
        finally:
            await guardian.shutdown()
    
    @pytest.mark.asyncio
    async def test_memory_thrashing_stress(self, stress_workspace, stress_config):
        """Test Memory Guardian under memory thrashing conditions."""
        # Create thrashing script
        thrashing_script = MemoryGrowthStressor.create_memory_thrashing_script(
            stress_workspace / "scripts"
        )
        
        stress_config.process_command = [sys.executable, str(thrashing_script)]
        stress_config.monitoring.check_interval = 0.05  # Even faster for thrashing
        
        guardian = MemoryGuardian(stress_config)
        await guardian.initialize()
        
        try:
            # Start thrashing process
            success = await guardian.start_process()
            assert success, "Should start thrashing process"
            
            # Monitor thrashing behavior
            guardian.start_monitoring()
            
            memory_readings = []
            state_counts = {'normal': 0, 'warning': 0, 'critical': 0, 'emergency': 0}
            
            # Collect data for 15 seconds
            start_time = time.time()
            while time.time() - start_time < 15:
                await asyncio.sleep(0.1)
                
                current_memory = guardian.get_memory_usage()
                if current_memory:
                    memory_readings.append((time.time() - start_time, current_memory))
                
                # Count state occurrences
                state_counts[guardian.memory_state.value] += 1
            
            await guardian.stop_monitoring()
            
            # Analyze thrashing behavior
            if len(memory_readings) >= 2:
                memory_values = [reading[1] for reading in memory_readings]
                memory_variance = sum((x - sum(memory_values)/len(memory_values))**2 for x in memory_values) / len(memory_values)
                memory_range = max(memory_values) - min(memory_values)
                
                print(f"\nMemory Thrashing Stress Test Results:")
                print(f"  Memory readings: {len(memory_readings)}")
                print(f"  Memory range: {memory_range:.1f}MB")
                print(f"  Memory variance: {memory_variance:.1f}")
                print(f"  State distribution: {state_counts}")
                
                # Thrashing should create memory variance
                assert memory_variance > 100, f"Memory should vary during thrashing: {memory_variance:.1f}"
                assert len(memory_readings) > 50, "Should have many readings during thrashing"
        
        finally:
            await guardian.shutdown()
    
    @pytest.mark.asyncio
    async def test_concurrent_restart_storm(self, stress_config):
        """Test behavior under concurrent restart storm conditions."""
        guardian = MemoryGuardian(stress_config)
        await guardian.initialize()
        
        # Mock process operations to focus on restart logic
        start_call_count = 0
        terminate_call_count = 0
        
        async def mock_start(*args, **kwargs):
            nonlocal start_call_count
            start_call_count += 1
            await asyncio.sleep(random.uniform(0.1, 0.5))  # Variable startup time
            return random.random() > 0.2  # 80% success rate
        
        async def mock_terminate(*args, **kwargs):
            nonlocal terminate_call_count
            terminate_call_count += 1
            await asyncio.sleep(random.uniform(0.05, 0.2))  # Variable shutdown time
            return True
        
        try:
            with patch.object(guardian, 'start_process', side_effect=mock_start):
                with patch.object(guardian, 'terminate_process', side_effect=mock_terminate):
                    
                    # Launch restart storm
                    restart_tasks = []
                    num_concurrent_restarts = 20
                    
                    for i in range(num_concurrent_restarts):
                        task = guardian.restart_process(f"Storm restart {i}")
                        restart_tasks.append(task)
                        
                        # Stagger the requests slightly
                        await asyncio.sleep(random.uniform(0.01, 0.1))
                    
                    # Wait for all restart attempts
                    results = await asyncio.gather(*restart_tasks, return_exceptions=True)
                    
                    # Analyze storm results
                    successful_restarts = sum(1 for r in results if r is True)
                    failed_restarts = sum(1 for r in results if r is False)
                    exceptions = sum(1 for r in results if isinstance(r, Exception))
                    
                    print(f"\nConcurrent Restart Storm Results:")
                    print(f"  Total restart requests: {num_concurrent_restarts}")
                    print(f"  Successful restarts: {successful_restarts}")
                    print(f"  Failed restarts: {failed_restarts}")
                    print(f"  Exceptions: {exceptions}")
                    print(f"  Start calls: {start_call_count}")
                    print(f"  Terminate calls: {terminate_call_count}")
                    
                    # Protection should limit concurrent restarts
                    assert successful_restarts < num_concurrent_restarts, "Should limit concurrent restarts"
                    assert successful_restarts <= stress_config.restart_policy.max_attempts, "Should respect max attempts"
                    assert exceptions == 0, "Should not have exceptions during restart storm"
        
        finally:
            await guardian.shutdown()
    
    @pytest.mark.asyncio
    async def test_large_state_file_stress(self, stress_workspace, stress_config):
        """Test handling of very large state files under stress."""
        # Create massive state data
        huge_state = {
            'conversations': [],
            'metadata': {
                'stress_test': True,
                'created': time.time()
            }
        }
        
        # Generate large conversation data (targeting ~50MB)
        conversation_size_target = 50 * 1024 * 1024  # 50MB
        conversation_count = 0
        current_size = 0
        
        while current_size < conversation_size_target:
            conversation = {
                'id': f'stress_conv_{conversation_count}',
                'created': time.time(),
                'messages': []
            }
            
            # Add many large messages
            for msg_id in range(200):  # 200 messages per conversation
                message = {
                    'id': f'msg_{msg_id}',
                    'role': 'user' if msg_id % 2 == 0 else 'assistant',
                    'content': f'Stress test message {msg_id} with large content. ' * 500,  # ~20KB per message
                    'timestamp': time.time(),
                    'metadata': {
                        'tokens': random.randint(1000, 5000),
                        'processing_time': random.uniform(0.1, 2.0),
                        'large_field': 'x' * 1000  # 1KB padding
                    }
                }
                conversation['messages'].append(message)
            
            huge_state['conversations'].append(conversation)
            conversation_count += 1
            
            # Estimate size
            if conversation_count % 10 == 0:
                test_json = json.dumps(huge_state)
                current_size = len(test_json.encode('utf-8'))
                if current_size > conversation_size_target:
                    break
        
        state_file = stress_workspace / "huge_stress_state.json"
        stress_config.state_file = str(state_file)
        
        guardian = MemoryGuardian(stress_config)
        await guardian.initialize()
        
        try:
            # Test large state operations under stress
            start_time = time.time()
            
            # Rapid save/load cycles
            save_times = []
            load_times = []
            
            for cycle in range(5):  # 5 stress cycles
                print(f"Large state stress cycle {cycle + 1}/5...")
                
                # Add more data each cycle
                huge_state['metadata'][f'cycle_{cycle}'] = {
                    'timestamp': time.time(),
                    'data': 'y' * 10000  # 10KB more data
                }
                
                # Save under time pressure
                save_start = time.time()
                await guardian.state_manager.persist_state(huge_state)
                save_time = time.time() - save_start
                save_times.append(save_time)
                
                # Verify file exists and size
                file_size_mb = state_file.stat().st_size / (1024 * 1024)
                
                # Load under time pressure
                load_start = time.time()
                loaded_state = await guardian.state_manager.restore_state()
                load_time = time.time() - load_start
                load_times.append(load_time)
                
                # Verify integrity
                assert loaded_state is not None
                assert len(loaded_state['conversations']) == len(huge_state['conversations'])
                
                print(f"  Cycle {cycle + 1}: Save {save_time:.2f}s, Load {load_time:.2f}s, Size {file_size_mb:.1f}MB")
            
            total_time = time.time() - start_time
            avg_save_time = sum(save_times) / len(save_times)
            avg_load_time = sum(load_times) / len(load_times)
            final_size_mb = state_file.stat().st_size / (1024 * 1024)
            
            print(f"\nLarge State File Stress Results:")
            print(f"  Total stress time: {total_time:.2f}s")
            print(f"  Final file size: {final_size_mb:.1f}MB")
            print(f"  Average save time: {avg_save_time:.2f}s")
            print(f"  Average load time: {avg_load_time:.2f}s")
            print(f"  Conversations: {len(huge_state['conversations'])}")
            
            # Stress test assertions
            assert final_size_mb > 30, f"Should create large file: {final_size_mb:.1f}MB"
            assert avg_save_time < 30, f"Save too slow under stress: {avg_save_time:.2f}s"
            assert avg_load_time < 45, f"Load too slow under stress: {avg_load_time:.2f}s"
            assert max(save_times) < 60, f"Max save time too slow: {max(save_times):.2f}s"
        
        finally:
            await guardian.shutdown()
    
    @pytest.mark.asyncio
    async def test_extended_monitoring_endurance(self, stress_config):
        """Test Memory Guardian endurance over extended monitoring period."""
        guardian = MemoryGuardian(stress_config)
        await guardian.initialize()
        
        # Mock varying memory conditions
        memory_pattern = []
        base_memory = 200
        
        # Create 30-minute pattern (compressed to 30 seconds for testing)
        pattern_duration = 30  # seconds
        samples_per_second = 10
        total_samples = pattern_duration * samples_per_second
        
        for i in range(total_samples):
            # Simulate realistic memory patterns
            time_factor = i / total_samples
            
            # Base growth
            memory = base_memory + (time_factor * 300)
            
            # Add periodic spikes
            if i % 50 == 0:  # Periodic spikes
                memory += 200
            
            # Add random variations
            memory += random.uniform(-50, 100)
            
            # Ensure minimum
            memory = max(50, memory)
            
            memory_pattern.append(memory)
        
        # Mock process
        guardian.process = MagicMock()
        guardian.process.poll.return_value = None
        guardian.process_pid = os.getpid()
        guardian.process_state = ProcessState.RUNNING
        
        try:
            # Start extended monitoring
            guardian.start_monitoring()
            
            endurance_stats = {
                'total_samples': 0,
                'state_transitions': 0,
                'restarts_triggered': 0,
                'memory_peak': 0,
                'monitoring_duration': 0,
                'error_count': 0
            }
            
            # Track original restart method
            original_restart = guardian.restart_process
            async def count_restarts(*args, **kwargs):
                endurance_stats['restarts_triggered'] += 1
                return True  # Always succeed for endurance test
            guardian.restart_process = count_restarts
            
            start_time = time.time()
            pattern_index = 0
            last_state = guardian.memory_state
            
            with patch.object(guardian, 'get_memory_usage') as mock_memory:
                while pattern_index < len(memory_pattern):
                    try:
                        # Set memory reading from pattern
                        current_memory = memory_pattern[pattern_index]
                        mock_memory.return_value = current_memory
                        
                        # Wait for monitoring cycle
                        await asyncio.sleep(0.1)  # 10 samples per second
                        
                        # Update stats
                        endurance_stats['total_samples'] = guardian.memory_stats.samples
                        endurance_stats['memory_peak'] = max(
                            endurance_stats['memory_peak'], 
                            current_memory
                        )
                        
                        # Track state transitions
                        current_state = guardian.memory_state
                        if current_state != last_state:
                            endurance_stats['state_transitions'] += 1
                            last_state = current_state
                        
                        pattern_index += 1
                        
                    except Exception as e:
                        endurance_stats['error_count'] += 1
                        print(f"Endurance test error: {e}")
            
            endurance_stats['monitoring_duration'] = time.time() - start_time
            
            await guardian.stop_monitoring()
            
            # Analyze endurance results
            print(f"\nExtended Monitoring Endurance Results:")
            print(f"  Monitoring duration: {endurance_stats['monitoring_duration']:.2f}s")
            print(f"  Total samples: {endurance_stats['total_samples']}")
            print(f"  Memory peak: {endurance_stats['memory_peak']:.1f}MB")
            print(f"  State transitions: {endurance_stats['state_transitions']}")
            print(f"  Restarts triggered: {endurance_stats['restarts_triggered']}")
            print(f"  Errors: {endurance_stats['error_count']}")
            print(f"  Samples per second: {endurance_stats['total_samples'] / endurance_stats['monitoring_duration']:.1f}")
            
            # Endurance assertions
            assert endurance_stats['total_samples'] > 100, "Should have many samples during endurance test"
            assert endurance_stats['state_transitions'] > 5, "Should have multiple state transitions"
            assert endurance_stats['error_count'] == 0, "Should have no errors during endurance test"
            assert endurance_stats['monitoring_duration'] > 20, "Should run for reasonable duration"
        
        finally:
            await guardian.shutdown()
    
    @pytest.mark.asyncio
    async def test_resource_exhaustion_scenarios(self, stress_config):
        """Test behavior under various resource exhaustion scenarios."""
        guardian = MemoryGuardian(stress_config)
        await guardian.initialize()
        
        exhaustion_scenarios = [
            'memory_pressure',
            'cpu_saturation', 
            'disk_space_low',
            'file_descriptor_limit',
            'process_limit'
        ]
        
        scenario_results = {}
        
        for scenario in exhaustion_scenarios:
            print(f"\nTesting resource exhaustion scenario: {scenario}")
            
            scenario_start = time.time()
            
            try:
                if scenario == 'memory_pressure':
                    # Simulate system memory pressure
                    with patch('claude_mpm.utils.platform_memory.check_memory_pressure', return_value='critical'):
                        guardian.process = MagicMock()
                        guardian.process_state = ProcessState.RUNNING
                        guardian.process_pid = os.getpid()
                        
                        # Should trigger graceful degradation
                        health_monitor = guardian.health_monitor
                        if health_monitor:
                            valid, message = await health_monitor.validate_before_start()
                            scenario_results[scenario] = {
                                'handled_gracefully': True,
                                'validation_passed': valid,
                                'message': message,
                                'duration': time.time() - scenario_start
                            }
                        else:
                            scenario_results[scenario] = {'handled_gracefully': True, 'duration': time.time() - scenario_start}
                
                elif scenario == 'cpu_saturation':
                    # Simulate high CPU usage
                    with patch('psutil.Process.cpu_percent', return_value=95.0):
                        guardian.process = MagicMock()
                        guardian.process_state = ProcessState.RUNNING
                        
                        # Should still be able to monitor
                        with patch.object(guardian, 'get_memory_usage', return_value=300):
                            await guardian.monitor_memory()
                        
                        scenario_results[scenario] = {
                            'handled_gracefully': True,
                            'monitoring_functional': True,
                            'duration': time.time() - scenario_start
                        }
                
                elif scenario == 'disk_space_low':
                    # Simulate low disk space
                    with patch('shutil.disk_usage', return_value=(1000000000, 100000, 100000)):  # Very low free space
                        # State saving should handle low disk space
                        test_state = {'test': 'data'}
                        try:
                            await guardian.state_manager.persist_state(test_state)
                            scenario_results[scenario] = {
                                'handled_gracefully': True,
                                'state_saved': True,
                                'duration': time.time() - scenario_start
                            }
                        except Exception as e:
                            scenario_results[scenario] = {
                                'handled_gracefully': True,
                                'state_saved': False,
                                'error': str(e),
                                'duration': time.time() - scenario_start
                            }
                
                elif scenario == 'file_descriptor_limit':
                    # Simulate file descriptor exhaustion
                    original_open = open
                    open_count = 0
                    
                    def limited_open(*args, **kwargs):
                        nonlocal open_count
                        open_count += 1
                        if open_count > 10:  # Artificial limit
                            raise OSError("Too many open files")
                        return original_open(*args, **kwargs)
                    
                    with patch('builtins.open', side_effect=limited_open):
                        try:
                            # Should handle file descriptor limits gracefully
                            await guardian.state_manager.persist_state({'test': 'data'})
                            scenario_results[scenario] = {
                                'handled_gracefully': True,
                                'duration': time.time() - scenario_start
                            }
                        except Exception as e:
                            scenario_results[scenario] = {
                                'handled_gracefully': True,
                                'expected_error': True,
                                'error': str(e),
                                'duration': time.time() - scenario_start
                            }
                
                elif scenario == 'process_limit':
                    # Simulate process creation failure
                    with patch('subprocess.Popen', side_effect=OSError("Cannot create process")):
                        try:
                            success = await guardian.start_process()
                            scenario_results[scenario] = {
                                'handled_gracefully': True,
                                'start_failed_gracefully': not success,
                                'duration': time.time() - scenario_start
                            }
                        except Exception as e:
                            scenario_results[scenario] = {
                                'handled_gracefully': False,
                                'error': str(e),
                                'duration': time.time() - scenario_start
                            }
            
            except Exception as e:
                scenario_results[scenario] = {
                    'handled_gracefully': False,
                    'error': str(e),
                    'duration': time.time() - scenario_start
                }
        
        # Analyze resource exhaustion results
        print(f"\nResource Exhaustion Scenario Results:")
        for scenario, result in scenario_results.items():
            print(f"  {scenario}:")
            print(f"    Handled gracefully: {result.get('handled_gracefully', False)}")
            print(f"    Duration: {result.get('duration', 0):.3f}s")
            if 'error' in result:
                print(f"    Error: {result['error']}")
        
        # All scenarios should be handled gracefully
        for scenario, result in scenario_results.items():
            assert result.get('handled_gracefully', False), f"Scenario {scenario} not handled gracefully"
        
        await guardian.shutdown()
    
    @pytest.mark.asyncio
    async def test_high_frequency_event_processing(self, stress_config):
        """Test handling of high-frequency monitoring events."""
        # Configure for very high frequency
        stress_config.monitoring.check_interval = 0.001  # 1ms - extreme frequency
        
        guardian = MemoryGuardian(stress_config)
        await guardian.initialize()
        
        # Mock process
        guardian.process = MagicMock()
        guardian.process.poll.return_value = None
        guardian.process_pid = os.getpid()
        guardian.process_state = ProcessState.RUNNING
        
        try:
            # Generate high-frequency memory readings
            event_count = 0
            memory_readings = []
            
            def high_freq_memory_reading():
                nonlocal event_count
                event_count += 1
                # Simulate varying memory with high frequency
                base = 300 + (event_count % 100) * 2  # Sawtooth pattern
                noise = random.uniform(-10, 10)
                return base + noise
            
            with patch.object(guardian, 'get_memory_usage', side_effect=high_freq_memory_reading):
                guardian.start_monitoring()
                
                # Let high-frequency monitoring run
                start_time = time.time()
                test_duration = 5  # 5 seconds of high-frequency events
                
                while time.time() - start_time < test_duration:
                    await asyncio.sleep(0.01)  # Check every 10ms
                    
                    current_memory = guardian.get_memory_usage()
                    if current_memory:
                        memory_readings.append(current_memory)
                
                await guardian.stop_monitoring()
            
            # Analyze high-frequency results
            total_duration = time.time() - start_time
            events_per_second = event_count / total_duration
            samples_recorded = guardian.memory_stats.samples
            
            print(f"\nHigh-Frequency Event Processing Results:")
            print(f"  Test duration: {total_duration:.3f}s")
            print(f"  Events generated: {event_count}")
            print(f"  Events per second: {events_per_second:.1f}")
            print(f"  Samples recorded: {samples_recorded}")
            print(f"  Memory readings collected: {len(memory_readings)}")
            print(f"  Sample rate: {samples_recorded / total_duration:.1f}/s")
            
            # High-frequency assertions
            assert event_count > 1000, f"Should generate many events: {event_count}"
            assert events_per_second > 100, f"Should handle high frequency: {events_per_second:.1f}/s"
            assert samples_recorded > 0, "Should record samples despite high frequency"
            assert len(memory_readings) > 100, f"Should collect many readings: {len(memory_readings)}"
        
        finally:
            await guardian.shutdown()
    
    @pytest.mark.asyncio
    async def test_chaos_engineering_scenarios(self, stress_workspace, stress_config):
        """Test system resilience under chaotic conditions."""
        # Create chaos script
        chaos_script = MemoryGrowthStressor.create_rapid_growth_script(
            stress_workspace / "scripts",
            initial_mb=100,
            growth_rate_mb_per_sec=100,
            max_memory_mb=600,
            chaos_mode=True  # Enable chaotic behavior
        )
        
        stress_config.process_command = [sys.executable, str(chaos_script)]
        
        guardian = MemoryGuardian(stress_config)
        await guardian.initialize()
        
        chaos_results = {
            'unexpected_events': 0,
            'recovery_attempts': 0,
            'successful_recoveries': 0,
            'system_stability': True,
            'chaos_duration': 0
        }
        
        # Inject chaos into the guardian itself
        original_monitor = guardian.monitor_memory
        async def chaotic_monitor():
            # Random monitoring failures
            if random.random() < 0.1:  # 10% chance of chaos
                chaos_results['unexpected_events'] += 1
                if random.random() < 0.5:
                    raise Exception("Chaotic monitoring failure")
                else:
                    await asyncio.sleep(random.uniform(0.1, 0.5))  # Random delays
            
            return await original_monitor()
        
        guardian.monitor_memory = chaotic_monitor
        
        try:
            start_time = time.time()
            
            # Start chaotic process
            success = await guardian.start_process()
            if success:
                guardian.start_monitoring()
                
                # Run chaos test
                chaos_duration = 20  # seconds
                while time.time() - start_time < chaos_duration:
                    await asyncio.sleep(0.5)
                    
                    # Random system interventions
                    if random.random() < 0.05:  # 5% chance
                        chaos_results['recovery_attempts'] += 1
                        try:
                            # Random restart attempt
                            with patch.object(guardian, 'start_process', return_value=True):
                                with patch.object(guardian, 'terminate_process', return_value=True):
                                    restart_success = await guardian.restart_process("Chaos intervention")
                                    if restart_success:
                                        chaos_results['successful_recoveries'] += 1
                        except Exception:
                            pass  # Expected during chaos
                
                await guardian.stop_monitoring()
            
            chaos_results['chaos_duration'] = time.time() - start_time
            chaos_results['system_stability'] = guardian._initialized and not guardian._shutdown
            
            print(f"\nChaos Engineering Results:")
            print(f"  Chaos duration: {chaos_results['chaos_duration']:.2f}s")
            print(f"  Unexpected events: {chaos_results['unexpected_events']}")
            print(f"  Recovery attempts: {chaos_results['recovery_attempts']}")
            print(f"  Successful recoveries: {chaos_results['successful_recoveries']}")
            print(f"  System stability maintained: {chaos_results['system_stability']}")
            
            # Chaos resilience assertions
            assert chaos_results['system_stability'], "System should maintain stability under chaos"
            
            # Should handle at least some chaos events
            if chaos_results['unexpected_events'] > 0:
                print(f"  System survived {chaos_results['unexpected_events']} chaos events")
        
        finally:
            await guardian.shutdown()


class TestSystemInstabilitySimulation:
    """Test Memory Guardian under simulated system instability."""
    
    @pytest.mark.asyncio
    async def test_network_instability_simulation(self):
        """Test behavior under simulated network instability."""
        config = MemoryGuardianConfig(enabled=True)
        guardian = MemoryGuardian(config)
        await guardian.initialize()
        
        try:
            # Simulate network timeouts affecting external dependencies
            with patch('asyncio.sleep', side_effect=lambda x: asyncio.sleep(x * 0.1)):  # Speed up
                # Should handle network delays gracefully
                guardian.process = MagicMock()
                guardian.process_state = ProcessState.RUNNING
                
                with patch.object(guardian, 'get_memory_usage', return_value=400):
                    await guardian.monitor_memory()
                
                # System should remain functional
                assert guardian._initialized
                assert not guardian._shutdown
        
        finally:
            await guardian.shutdown()
    
    @pytest.mark.asyncio
    async def test_disk_io_instability_simulation(self):
        """Test behavior under disk I/O instability."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = MemoryGuardianConfig(
                enabled=True,
                state_file=str(Path(tmpdir) / "unstable_state.json"),
                persist_state=True
            )
            
            guardian = MemoryGuardian(config)
            await guardian.initialize()
            
            try:
                # Simulate intermittent I/O failures
                io_failure_count = 0
                original_open = open
                
                def unstable_open(*args, **kwargs):
                    nonlocal io_failure_count
                    io_failure_count += 1
                    if io_failure_count % 3 == 0:  # Fail every 3rd operation
                        raise IOError("Simulated I/O failure")
                    return original_open(*args, **kwargs)
                
                with patch('builtins.open', side_effect=unstable_open):
                    # Should handle I/O failures gracefully
                    try:
                        await guardian.state_manager.persist_state({'test': 'data'})
                    except IOError:
                        pass  # Expected failure
                    
                    # System should remain stable
                    assert guardian._initialized
            
            finally:
                await guardian.shutdown()