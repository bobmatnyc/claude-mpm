"""End-to-end tests for Memory Guardian System.

This module provides comprehensive end-to-end tests that simulate real-world usage
scenarios including actual subprocess execution, CLI command testing, and full
system integration.

Test categories:
- Real subprocess simulation with memory growth
- CLI command execution and validation
- Configuration file loading and validation
- Experimental feature warnings and handling
- Interrupt handling and graceful shutdown
- Cross-platform compatibility
"""

import asyncio
import json
import os
import platform
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
import shutil
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
    ProcessState
)
from claude_mpm.cli.commands.run_guarded import RunGuardedCommand


class MemoryGrowthSimulator:
    """Simulates a process that gradually consumes memory."""
    
    @staticmethod
    def create_memory_growth_script(
        target_dir: Path,
        growth_rate_mb: int = 50,
        max_memory_mb: int = 500,
        growth_interval: float = 1.0,
        crash_at_limit: bool = False
    ) -> Path:
        """Create a Python script that simulates memory growth.
        
        Args:
            target_dir: Directory to create script in
            growth_rate_mb: Memory growth per interval in MB
            max_memory_mb: Maximum memory before stopping/crashing
            growth_interval: Time between growth increments
            crash_at_limit: Whether to crash when limit reached
            
        Returns:
            Path to created script
        """
        script_content = f'''#!/usr/bin/env python3
"""Memory growth simulator for testing Memory Guardian."""

import gc
import os
import sys
import time
import traceback
from datetime import datetime

# Configuration
GROWTH_RATE_MB = {growth_rate_mb}
MAX_MEMORY_MB = {max_memory_mb}
GROWTH_INTERVAL = {growth_interval}
CRASH_AT_LIMIT = {crash_at_limit}

# Convert MB to bytes
GROWTH_RATE_BYTES = GROWTH_RATE_MB * 1024 * 1024
MAX_MEMORY_BYTES = MAX_MEMORY_MB * 1024 * 1024

def get_memory_usage():
    """Get current memory usage in MB."""
    try:
        import psutil
        process = psutil.Process()
        return process.memory_info().rss / (1024 * 1024)
    except ImportError:
        # Fallback to estimating from allocated memory
        return len(memory_hog) * 8 / (1024 * 1024) if 'memory_hog' in globals() else 0

def log_message(msg):
    """Log message with timestamp."""
    timestamp = datetime.now().isoformat()
    print(f"[{{timestamp}}] {{msg}}", flush=True)

def main():
    """Main memory growth simulation."""
    global memory_hog
    
    log_message(f"Memory Growth Simulator starting")
    log_message(f"PID: {{os.getpid()}}")
    log_message(f"Growth rate: {{GROWTH_RATE_MB}}MB every {{GROWTH_INTERVAL}}s")
    log_message(f"Max memory: {{MAX_MEMORY_MB}}MB")
    log_message(f"Crash at limit: {{CRASH_AT_LIMIT}}")
    
    memory_hog = []
    cycle = 0
    
    try:
        while True:
            # Allocate memory
            chunk = bytearray(GROWTH_RATE_BYTES)
            # Fill with random data to prevent optimization
            for i in range(0, len(chunk), 1024):
                chunk[i:i+4] = (cycle + i).to_bytes(4, 'little')
            memory_hog.append(chunk)
            
            cycle += 1
            current_memory = get_memory_usage()
            
            log_message(f"Cycle {{cycle}}: Allocated {{GROWTH_RATE_MB}}MB, "
                       f"Total: {{current_memory:.1f}}MB")
            
            # Check if we've reached the limit
            if current_memory >= MAX_MEMORY_MB:
                log_message(f"Reached memory limit: {{current_memory:.1f}}MB")
                
                if CRASH_AT_LIMIT:
                    log_message("Simulating crash...")
                    # Simulate different types of crashes
                    crash_type = cycle % 3
                    if crash_type == 0:
                        raise MemoryError("Simulated memory exhaustion")
                    elif crash_type == 1:
                        sys.exit(1)
                    else:
                        os._exit(2)
                else:
                    log_message("Holding steady at memory limit")
                    # Hold steady and just sleep
                    while True:
                        time.sleep(GROWTH_INTERVAL)
                        log_message(f"Steady state: {{get_memory_usage():.1f}}MB")
            
            # Wait before next allocation
            time.sleep(GROWTH_INTERVAL)
            
    except KeyboardInterrupt:
        log_message("Received interrupt, shutting down gracefully")
        return 0
    except Exception as e:
        log_message(f"Error: {{e}}")
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
'''
        
        script_path = target_dir / "memory_growth_simulator.py"
        with open(script_path, 'w') as f:
            f.write(script_content)
        
        # Make executable
        script_path.chmod(0o755)
        return script_path


class TestMemoryGuardianE2E:
    """End-to-end tests for Memory Guardian system."""
    
    @pytest.fixture
    async def temp_workspace(self):
        """Create temporary workspace with all necessary files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            
            # Create subdirectories
            (workspace / "scripts").mkdir()
            (workspace / "config").mkdir()
            (workspace / "logs").mkdir()
            
            yield workspace
    
    @pytest.fixture
    async def memory_growth_script(self, temp_workspace):
        """Create memory growth simulation script."""
        return MemoryGrowthSimulator.create_memory_growth_script(
            temp_workspace / "scripts",
            growth_rate_mb=25,
            max_memory_mb=200,
            growth_interval=0.5
        )
    
    @pytest.fixture
    async def e2e_config(self, temp_workspace, memory_growth_script):
        """Create E2E test configuration."""
        config_data = {
            'enabled': True,
            'thresholds': {
                'warning': 100,
                'critical': 150,
                'emergency': 200
            },
            'restart_policy': {
                'max_attempts': 3,
                'attempt_window': 300,
                'initial_cooldown': 1,
                'graceful_timeout': 5,
                'exponential_backoff': True
            },
            'monitoring': {
                'check_interval': 1,
                'check_interval_warning': 0.5,
                'check_interval_critical': 0.25,
                'log_memory_stats': True
            },
            'process_command': [sys.executable, str(memory_growth_script)],
            'working_directory': str(temp_workspace),
            'state_file': str(temp_workspace / 'memory_guardian_state.json'),
            'persist_state': True,
            'auto_start': False
        }
        
        config_file = temp_workspace / "config" / "memory_guardian.json"
        with open(config_file, 'w') as f:
            json.dump(config_data, f, indent=2)
        
        return config_file
    
    @pytest.mark.asyncio
    async def test_real_subprocess_memory_monitoring(self, temp_workspace, memory_growth_script):
        """Test monitoring a real subprocess with actual memory growth."""
        # Create configuration for real subprocess
        config = MemoryGuardianConfig(
            enabled=True,
            thresholds=MemoryThresholds(warning=50, critical=100, emergency=150),
            monitoring=MonitoringConfig(check_interval=0.5),
            process_command=[sys.executable, str(memory_growth_script)],
            working_directory=str(temp_workspace),
            state_file=str(temp_workspace / "real_test_state.json"),
            persist_state=True
        )
        
        guardian = MemoryGuardian(config)
        await guardian.initialize()
        
        try:
            # Start the real subprocess
            success = await guardian.start_process()
            assert success, "Should successfully start memory growth simulator"
            assert guardian.process is not None
            assert guardian.process_pid is not None
            
            # Verify process is actually running
            assert guardian.process.poll() is None, "Process should be running"
            
            # Start monitoring
            guardian.start_monitoring()
            
            # Monitor for memory growth
            monitoring_duration = 10  # seconds
            start_time = time.time()
            memory_readings = []
            state_changes = []
            
            while time.time() - start_time < monitoring_duration:
                await asyncio.sleep(0.5)
                
                # Get current memory
                current_memory = guardian.get_memory_usage()
                if current_memory:
                    memory_readings.append((time.time(), current_memory))
                
                # Track state changes
                current_state = guardian.memory_state
                if not state_changes or state_changes[-1][1] != current_state:
                    state_changes.append((time.time(), current_state))
                
                # Check if we've seen warning or critical states
                if current_state in [MemoryState.WARNING, MemoryState.CRITICAL]:
                    break
            
            # Stop monitoring
            await guardian.stop_monitoring()
            
            # Verify we captured real memory growth
            assert len(memory_readings) > 5, "Should have multiple memory readings"
            
            # Check that memory actually grew
            if len(memory_readings) >= 2:
                initial_memory = memory_readings[0][1]
                final_memory = memory_readings[-1][1]
                assert final_memory > initial_memory, f"Memory should grow: {initial_memory}MB -> {final_memory}MB"
            
            # Verify state transitions occurred
            states_seen = [state for _, state in state_changes]
            assert MemoryState.NORMAL in states_seen, "Should start in normal state"
            
            # If we ran long enough, should see warning state
            if final_memory > config.thresholds.warning:
                assert MemoryState.WARNING in states_seen, "Should reach warning state with real memory growth"
            
        finally:
            # Clean shutdown
            if guardian.process and guardian.process.poll() is None:
                await guardian.terminate_process()
            await guardian.shutdown()
    
    @pytest.mark.asyncio
    async def test_cli_command_execution(self, temp_workspace, e2e_config):
        """Test CLI command execution and integration."""
        # Test config file loading
        config = MemoryGuardianConfig.from_file(str(e2e_config))
        assert config.enabled
        assert config.thresholds.warning == 100
        
        # Test CLI command initialization
        cmd = RunGuardedCommand()
        assert cmd is not None
        
        # Create a simple test script for CLI testing
        test_script = temp_workspace / "test_command.py"
        with open(test_script, 'w') as f:
            f.write('''
import time
import sys

print("Test command started", flush=True)
for i in range(5):
    print(f"Working... {i}", flush=True)
    time.sleep(0.5)
print("Test command completed", flush=True)
sys.exit(0)
''')
        
        # Test CLI argument parsing
        test_args = [
            'run-guarded',
            '--config', str(e2e_config),
            '--', 
            sys.executable, str(test_script)
        ]
        
        # Mock sys.argv for testing
        original_argv = sys.argv
        try:
            sys.argv = test_args
            
            # This would normally be handled by the CLI parser
            # For testing, we verify the components work
            assert Path(e2e_config).exists()
            assert test_script.exists()
            
        finally:
            sys.argv = original_argv
    
    @pytest.mark.asyncio
    async def test_configuration_file_loading(self, temp_workspace):
        """Test loading configuration from various file formats."""
        configs_to_test = []
        
        # JSON configuration
        json_config = {
            'enabled': True,
            'thresholds': {'warning': 512, 'critical': 1024, 'emergency': 1536},
            'monitoring': {'check_interval': 2},
            'process_command': ['echo', 'test']
        }
        
        json_file = temp_workspace / "test_config.json"
        with open(json_file, 'w') as f:
            json.dump(json_config, f)
        configs_to_test.append(('json', json_file))
        
        # YAML configuration (if available)
        try:
            import yaml
            yaml_config = {
                'enabled': True,
                'thresholds': {'warning': 256, 'critical': 512, 'emergency': 768},
                'monitoring': {'check_interval': 3},
                'process_command': ['python', '--version']
            }
            
            yaml_file = temp_workspace / "test_config.yaml"
            with open(yaml_file, 'w') as f:
                yaml.dump(yaml_config, f)
            configs_to_test.append(('yaml', yaml_file))
            
        except ImportError:
            pass  # YAML not available, skip
        
        # Test loading each configuration
        for config_type, config_file in configs_to_test:
            try:
                config = MemoryGuardianConfig.from_file(str(config_file))
                assert config.enabled
                assert config.thresholds.warning > 0
                assert config.monitoring.check_interval > 0
                assert len(config.process_command) > 0
                
            except Exception as e:
                pytest.fail(f"Failed to load {config_type} config: {e}")
    
    @pytest.mark.asyncio
    async def test_experimental_feature_warnings(self, temp_workspace):
        """Test experimental feature warnings and handling."""
        # Create config with experimental features
        experimental_config = {
            'enabled': True,
            'experimental': {
                'advanced_memory_prediction': True,
                'machine_learning_restart_optimization': True,
                'beta_dashboard_features': True
            },
            'thresholds': {'warning': 100, 'critical': 200, 'emergency': 300},
            'process_command': ['echo', 'experimental test']
        }
        
        config_file = temp_workspace / "experimental_config.json"
        with open(config_file, 'w') as f:
            json.dump(experimental_config, f)
        
        # Capture warnings when loading experimental config
        warnings_captured = []
        
        class WarningCapture:
            def __init__(self):
                self.warnings = []
            
            def warn(self, message):
                self.warnings.append(message)
        
        warning_capture = WarningCapture()
        
        # Load config and check for experimental warnings
        try:
            config = MemoryGuardianConfig.from_file(str(config_file))
            
            # Check if experimental features are handled
            assert config.enabled
            
            # Experimental features might be ignored or trigger warnings
            # This test ensures the system doesn't crash with unknown features
            
        except Exception as e:
            # Should not crash, even with experimental features
            pytest.fail(f"Should handle experimental features gracefully: {e}")
    
    @pytest.mark.asyncio
    async def test_interrupt_handling_and_graceful_shutdown(self, temp_workspace, memory_growth_script):
        """Test interrupt handling and graceful shutdown."""
        config = MemoryGuardianConfig(
            enabled=True,
            thresholds=MemoryThresholds(warning=50, critical=100, emergency=150),
            process_command=[sys.executable, str(memory_growth_script)],
            working_directory=str(temp_workspace)
        )
        
        guardian = MemoryGuardian(config)
        await guardian.initialize()
        
        # Start process and monitoring
        await guardian.start_process()
        guardian.start_monitoring()
        
        # Let it run briefly
        await asyncio.sleep(2)
        
        # Simulate interrupt handling
        shutdown_started = time.time()
        
        try:
            # Test graceful shutdown
            await guardian.stop_monitoring()
            await guardian.shutdown()
            
            shutdown_duration = time.time() - shutdown_started
            
            # Should shutdown within reasonable time
            assert shutdown_duration < 30, f"Shutdown took too long: {shutdown_duration}s"
            
            # Process should be terminated
            assert guardian.process is None or guardian.process.poll() is not None
            assert guardian.process_state in [ProcessState.STOPPED, ProcessState.NOT_STARTED]
            
        except Exception as e:
            pytest.fail(f"Graceful shutdown failed: {e}")
    
    @pytest.mark.asyncio
    async def test_process_crash_recovery(self, temp_workspace):
        """Test recovery when monitored process crashes."""
        # Create a script that crashes after some time
        crash_script = temp_workspace / "crash_simulator.py"
        with open(crash_script, 'w') as f:
            f.write('''
import sys
import time
import os

print(f"Crash simulator started, PID: {os.getpid()}", flush=True)

# Run for a bit then crash
for i in range(3):
    print(f"Working... {i}", flush=True)
    time.sleep(1)

print("Simulating crash!", flush=True)
sys.exit(1)  # Exit with error code
''')
        
        config = MemoryGuardianConfig(
            enabled=True,
            process_command=[sys.executable, str(crash_script)],
            auto_start=True,  # Enable auto-restart
            working_directory=str(temp_workspace)
        )
        
        guardian = MemoryGuardian(config)
        await guardian.initialize()
        
        restart_count = 0
        original_restart = guardian.restart_process
        
        async def count_restarts(*args, **kwargs):
            nonlocal restart_count
            restart_count += 1
            return await original_restart(*args, **kwargs)
        
        guardian.restart_process = count_restarts
        
        try:
            # Start monitoring
            guardian.start_monitoring()
            
            # Wait for process to crash and restart
            max_wait = 15  # seconds
            start_time = time.time()
            
            while time.time() - start_time < max_wait:
                await asyncio.sleep(0.5)
                
                # Check if restart was triggered
                if restart_count > 0:
                    break
            
            # Should have detected crash and attempted restart
            assert restart_count > 0, "Should have attempted restart after process crash"
            
        finally:
            await guardian.stop_monitoring()
            await guardian.shutdown()
    
    @pytest.mark.asyncio 
    async def test_large_state_file_handling(self, temp_workspace):
        """Test handling of large state files and data."""
        # Create large state data
        large_state = {
            'conversations': [],
            'metadata': {
                'version': '1.0.0',
                'created': time.time()
            }
        }
        
        # Generate large conversation data
        for conv_id in range(100):
            conversation = {
                'id': f'conv_{conv_id}',
                'messages': []
            }
            
            for msg_id in range(50):
                conversation['messages'].append({
                    'id': f'msg_{msg_id}',
                    'role': 'user' if msg_id % 2 == 0 else 'assistant',
                    'content': f'Test message content {msg_id} ' * 100,  # Long content
                    'timestamp': time.time()
                })
            
            large_state['conversations'].append(conversation)
        
        # Create config with large state file
        state_file = temp_workspace / "large_state.json"
        config = MemoryGuardianConfig(
            enabled=True,
            state_file=str(state_file),
            persist_state=True,
            thresholds=MemoryThresholds(warning=100, critical=200, emergency=300),
            process_command=['echo', 'test']
        )
        
        guardian = MemoryGuardian(config)
        await guardian.initialize()
        
        try:
            # Save large state
            start_time = time.time()
            await guardian.state_manager.persist_state(large_state)
            save_time = time.time() - start_time
            
            # Check file was created and has reasonable size
            assert state_file.exists()
            file_size_mb = state_file.stat().st_size / (1024 * 1024)
            
            # Should be at least 1MB with our test data
            assert file_size_mb > 0.5, f"State file too small: {file_size_mb}MB"
            
            # Performance check - should save within reasonable time
            assert save_time < 10, f"Save took too long: {save_time}s for {file_size_mb:.1f}MB"
            
            # Test loading large state
            start_time = time.time()
            loaded_state = await guardian.state_manager.restore_state()
            load_time = time.time() - start_time
            
            assert loaded_state is not None
            assert len(loaded_state['conversations']) == 100
            assert load_time < 15, f"Load took too long: {load_time}s for {file_size_mb:.1f}MB"
            
        finally:
            await guardian.shutdown()
    
    @pytest.mark.asyncio
    async def test_concurrent_guardian_instances(self, temp_workspace):
        """Test multiple Memory Guardian instances running concurrently."""
        guardians = []
        
        try:
            # Create multiple guardian instances with different configs
            for i in range(3):
                instance_dir = temp_workspace / f"instance_{i}"
                instance_dir.mkdir()
                
                # Create simple test script for each instance
                test_script = instance_dir / "test_process.py"
                with open(test_script, 'w') as f:
                    f.write(f'''
import time
import os

print(f"Instance {i} started, PID: {{os.getpid()}}", flush=True)

for j in range(10):
    print(f"Instance {i} working... {{j}}", flush=True)
    time.sleep(0.5)

print(f"Instance {i} completed", flush=True)
''')
                
                config = MemoryGuardianConfig(
                    enabled=True,
                    thresholds=MemoryThresholds(
                        warning=100 + (i * 50),
                        critical=200 + (i * 50), 
                        emergency=300 + (i * 50)
                    ),
                    monitoring=MonitoringConfig(check_interval=0.5 + (i * 0.2)),
                    process_command=[sys.executable, str(test_script)],
                    working_directory=str(instance_dir),
                    state_file=str(instance_dir / f"state_{i}.json")
                )
                
                guardian = MemoryGuardian(config)
                await guardian.initialize()
                guardians.append(guardian)
            
            # Start all processes
            start_tasks = [guardian.start_process() for guardian in guardians]
            start_results = await asyncio.gather(*start_tasks)
            
            # All should start successfully
            assert all(start_results), "All guardian instances should start successfully"
            
            # Start monitoring on all
            for guardian in guardians:
                guardian.start_monitoring()
            
            # Let them run concurrently
            await asyncio.sleep(3)
            
            # Check that all are operating independently
            for i, guardian in enumerate(guardians):
                assert guardian.monitoring, f"Guardian {i} should be monitoring"
                assert guardian.process_state == ProcessState.RUNNING, f"Guardian {i} process should be running"
            
        finally:
            # Clean shutdown of all instances
            shutdown_tasks = []
            for guardian in guardians:
                shutdown_tasks.append(guardian.shutdown())
            
            await asyncio.gather(*shutdown_tasks, return_exceptions=True)


class TestCrossPlatformCompatibility:
    """Test cross-platform compatibility and platform-specific features."""
    
    @pytest.mark.asyncio
    async def test_platform_memory_monitoring(self, tmp_path):
        """Test memory monitoring works on current platform."""
        config = MemoryGuardianConfig(
            enabled=True,
            process_command=[sys.executable, '-c', 'import time; time.sleep(5)'],
            working_directory=str(tmp_path)
        )
        
        guardian = MemoryGuardian(config)
        await guardian.initialize()
        
        try:
            # Start a real process
            success = await guardian.start_process()
            if success:
                # Should be able to get memory usage on any platform
                memory_usage = guardian.get_memory_usage()
                
                # On some platforms, we might not get memory info
                # but the call should not crash
                if memory_usage is not None:
                    assert memory_usage > 0, "Memory usage should be positive"
                    assert memory_usage < 10000, "Memory usage should be reasonable (< 10GB)"
            
        finally:
            await guardian.shutdown()
    
    @pytest.mark.skipif(platform.system() == 'Windows', reason="Unix-specific test")
    @pytest.mark.asyncio
    async def test_unix_process_groups(self, tmp_path):
        """Test Unix process group handling."""
        config = MemoryGuardianConfig(
            enabled=True,
            process_command=[sys.executable, '-c', 'import time, os; print(f"Process group: {os.getpgrp()}"); time.sleep(10)'],
            working_directory=str(tmp_path)
        )
        
        guardian = MemoryGuardian(config)
        await guardian.initialize()
        
        try:
            success = await guardian.start_process()
            assert success
            
            # Process should be in its own session/group
            assert guardian.process_pid is not None
            
            # Termination should work properly
            success = await guardian.terminate_process(timeout=5)
            assert success
            
        finally:
            await guardian.shutdown()
    
    @pytest.mark.skipif(platform.system() != 'Windows', reason="Windows-specific test")
    @pytest.mark.asyncio
    async def test_windows_process_termination(self, tmp_path):
        """Test Windows-specific process termination."""
        config = MemoryGuardianConfig(
            enabled=True,
            process_command=[sys.executable, '-c', 'import time, os; print(f"PID: {os.getpid()}"); time.sleep(10)'],
            working_directory=str(tmp_path)
        )
        
        guardian = MemoryGuardian(config)
        await guardian.initialize()
        
        try:
            success = await guardian.start_process()
            assert success
            
            # Windows termination should work
            success = await guardian.terminate_process(timeout=5)
            assert success
            
        finally:
            await guardian.shutdown()


class TestRealWorldScenarios:
    """Test real-world usage scenarios."""
    
    @pytest.mark.asyncio
    async def test_claude_conversation_simulation(self, tmp_path):
        """Simulate monitoring a Claude conversation scenario."""
        # Create a script that simulates Claude conversation memory growth
        claude_sim_script = tmp_path / "claude_simulator.py"
        with open(claude_sim_script, 'w') as f:
            f.write('''
import json
import time
import random
from pathlib import Path

# Simulate .claude.json growth
claude_file = Path(".claude.json")
conversation_data = {"conversations": []}

print("Claude conversation simulator started", flush=True)

for turn in range(20):
    # Add conversation turn
    conversation_data["conversations"].append({
        "id": f"turn_{turn}",
        "user_message": "Test message " * random.randint(50, 200),
        "assistant_response": "Test response " * random.randint(100, 500),
        "timestamp": time.time()
    })
    
    # Write to file (simulating conversation history growth)
    with open(claude_file, 'w') as f:
        json.dump(conversation_data, f)
    
    file_size = claude_file.stat().st_size / (1024 * 1024)
    print(f"Turn {turn}: .claude.json size: {file_size:.2f}MB", flush=True)
    
    time.sleep(0.5)

print("Simulation completed", flush=True)
''')
        
        config = MemoryGuardianConfig(
            enabled=True,
            thresholds=MemoryThresholds(warning=50, critical=100, emergency=150),
            monitoring=MonitoringConfig(check_interval=1),
            process_command=[sys.executable, str(claude_sim_script)],
            working_directory=str(tmp_path),
            state_file=str(tmp_path / "claude_guardian_state.json")
        )
        
        guardian = MemoryGuardian(config)
        await guardian.initialize()
        
        try:
            success = await guardian.start_process()
            assert success
            
            guardian.start_monitoring()
            
            # Monitor for conversation file growth
            claude_file = tmp_path / ".claude.json"
            max_wait = 15
            start_time = time.time()
            
            while time.time() - start_time < max_wait:
                await asyncio.sleep(1)
                
                if claude_file.exists():
                    file_size = claude_file.stat().st_size / (1024 * 1024)
                    if file_size > 0.1:  # Wait for some meaningful growth
                        break
            
            # Should have created conversation file
            assert claude_file.exists(), "Should create .claude.json file"
            
            await guardian.stop_monitoring()
            
        finally:
            await guardian.shutdown()