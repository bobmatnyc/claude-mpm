"""Reusable test fixtures for Memory Guardian System.

This module provides comprehensive, reusable test fixtures for Memory Guardian testing,
including mock processes, memory growth simulators, state generators, and platform
command mocks.

Fixture categories:
- Mock Claude process simulations
- Memory growth and pattern simulators
- State file generators (small to very large)
- Platform-specific command mocks
- Configuration builders for various scenarios
- Test data generators
- Performance measurement utilities
"""

import asyncio
import json
import os
import platform
import random
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable, Generator, Tuple
from unittest.mock import MagicMock, AsyncMock, patch
from dataclasses import dataclass
from datetime import datetime, timedelta

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
from claude_mpm.utils.platform_memory import MemoryInfo


@dataclass
class MockProcessConfig:
    """Configuration for mock process behavior."""
    pid: int = 12345
    initial_memory_mb: float = 100.0
    memory_growth_rate: float = 10.0  # MB per second
    max_memory_mb: float = 1000.0
    crash_at_limit: bool = False
    exit_code: int = 0
    startup_delay: float = 0.1
    shutdown_delay: float = 0.1
    memory_pattern: str = 'linear'  # 'linear', 'exponential', 'sawtooth', 'random', 'stable'
    pattern_params: Dict[str, Any] = None


@dataclass
class TestScenario:
    """Test scenario configuration."""
    name: str
    description: str
    config: MemoryGuardianConfig
    expected_behavior: Dict[str, Any]
    test_duration: float = 10.0
    setup_hooks: List[Callable] = None
    teardown_hooks: List[Callable] = None


class MockClaudeProcess:
    """Mock Claude process with realistic memory behavior."""
    
    def __init__(self, config: MockProcessConfig):
        self.config = config
        self.start_time = None
        self.is_running = False
        self.current_memory = config.initial_memory_mb
        self.memory_history = []
        self._lock = threading.Lock()
    
    def start(self) -> bool:
        """Start the mock process."""
        with self._lock:
            if self.is_running:
                return False
            
            time.sleep(self.config.startup_delay)
            self.start_time = time.time()
            self.is_running = True
            self.current_memory = self.config.initial_memory_mb
            return True
    
    def stop(self) -> bool:
        """Stop the mock process."""
        with self._lock:
            if not self.is_running:
                return False
            
            time.sleep(self.config.shutdown_delay)
            self.is_running = False
            return True
    
    def poll(self) -> Optional[int]:
        """Check if process is still running."""
        with self._lock:
            if not self.is_running:
                return self.config.exit_code
            
            # Check if crashed due to memory limit
            if (self.config.crash_at_limit and 
                self.current_memory >= self.config.max_memory_mb):
                self.is_running = False
                return 1  # Crash exit code
            
            return None  # Still running
    
    def get_memory_usage(self) -> float:
        """Get current memory usage."""
        with self._lock:
            if not self.is_running:
                return 0.0
            
            # Update memory based on pattern
            self._update_memory()
            self.memory_history.append((time.time(), self.current_memory))
            
            # Keep history reasonable size
            if len(self.memory_history) > 1000:
                self.memory_history = self.memory_history[-500:]
            
            return self.current_memory
    
    def _update_memory(self):
        """Update memory based on configured pattern."""
        if not self.start_time:
            return
        
        elapsed = time.time() - self.start_time
        pattern = self.config.memory_pattern
        params = self.config.pattern_params or {}
        
        if pattern == 'linear':
            growth = elapsed * self.config.memory_growth_rate
            self.current_memory = min(
                self.config.initial_memory_mb + growth,
                self.config.max_memory_mb
            )
        
        elif pattern == 'exponential':
            base = params.get('base', 1.1)
            self.current_memory = min(
                self.config.initial_memory_mb * (base ** elapsed),
                self.config.max_memory_mb
            )
        
        elif pattern == 'sawtooth':
            period = params.get('period', 10.0)  # seconds
            amplitude = params.get('amplitude', 100.0)  # MB
            phase = (elapsed % period) / period
            sawtooth_value = 2 * abs(phase - 0.5) - 0.5  # -0.5 to 0.5
            self.current_memory = (
                self.config.initial_memory_mb + 
                (amplitude * sawtooth_value)
            )
        
        elif pattern == 'random':
            variance = params.get('variance', 50.0)
            self.current_memory = max(
                10.0,  # Minimum memory
                self.config.initial_memory_mb + random.uniform(-variance, variance)
            )
        
        elif pattern == 'stable':
            noise = params.get('noise', 5.0)
            self.current_memory = (
                self.config.initial_memory_mb + 
                random.uniform(-noise, noise)
            )
        
        # Apply growth rate regardless of pattern
        if pattern != 'stable':
            base_growth = elapsed * (self.config.memory_growth_rate / 10)
            self.current_memory += base_growth
        
        # Ensure bounds
        self.current_memory = max(1.0, min(self.current_memory, self.config.max_memory_mb))
    
    def get_memory_history(self) -> List[Tuple[float, float]]:
        """Get memory usage history."""
        with self._lock:
            return self.memory_history.copy()


class StateDataGenerator:
    """Generator for test state data of various sizes."""
    
    @staticmethod
    def generate_small_state() -> Dict[str, Any]:
        """Generate small state data (~1KB)."""
        return {
            'conversations': [
                {
                    'id': 'conv_1',
                    'created': time.time(),
                    'messages': [
                        {'id': 'msg_1', 'role': 'user', 'content': 'Hello'},
                        {'id': 'msg_2', 'role': 'assistant', 'content': 'Hi there!'}
                    ]
                }
            ],
            'metadata': {
                'version': '1.0.0',
                'created': time.time(),
                'uuid': str(uuid.uuid4())
            }
        }
    
    @staticmethod
    def generate_medium_state() -> Dict[str, Any]:
        """Generate medium state data (~100KB)."""
        conversations = []
        for i in range(10):
            messages = []
            for j in range(20):
                messages.append({
                    'id': f'msg_{j}',
                    'role': 'user' if j % 2 == 0 else 'assistant',
                    'content': f'Test message {j} with content. ' * 50,  # ~1KB per message
                    'timestamp': time.time()
                })
            
            conversations.append({
                'id': f'conv_{i}',
                'created': time.time(),
                'messages': messages
            })
        
        return {
            'conversations': conversations,
            'metadata': {
                'version': '1.0.0',
                'created': time.time(),
                'uuid': str(uuid.uuid4()),
                'large_field': 'x' * 10000  # 10KB padding
            }
        }
    
    @staticmethod
    def generate_large_state() -> Dict[str, Any]:
        """Generate large state data (~10MB)."""
        conversations = []
        for i in range(100):
            messages = []
            for j in range(100):
                messages.append({
                    'id': f'msg_{j}',
                    'role': 'user' if j % 2 == 0 else 'assistant',
                    'content': f'Large test message {j} with substantial content. ' * 200,  # ~10KB per message
                    'timestamp': time.time(),
                    'metadata': {
                        'tokens': random.randint(100, 1000),
                        'processing_time': random.uniform(0.1, 2.0)
                    }
                })
            
            conversations.append({
                'id': f'conv_{i}',
                'created': time.time(),
                'messages': messages,
                'metadata': {
                    'total_tokens': sum(msg['metadata']['tokens'] for msg in messages),
                    'conversation_data': 'y' * 1000  # 1KB per conversation
                }
            })
        
        return {
            'conversations': conversations,
            'metadata': {
                'version': '1.0.0',
                'created': time.time(),
                'uuid': str(uuid.uuid4()),
                'statistics': {
                    'total_conversations': len(conversations),
                    'total_messages': sum(len(conv['messages']) for conv in conversations)
                },
                'large_field': 'z' * 100000  # 100KB padding
            }
        }
    
    @staticmethod
    def generate_huge_state(target_size_mb: int = 50) -> Dict[str, Any]:
        """Generate huge state data (configurable size)."""
        target_bytes = target_size_mb * 1024 * 1024
        conversations = []
        current_size = 0
        conv_count = 0
        
        # Template for size estimation
        template_conv = {
            'id': 'template',
            'created': time.time(),
            'messages': [
                {
                    'id': 'template_msg',
                    'role': 'user',
                    'content': 'Template message content. ' * 100,  # ~2.5KB
                    'timestamp': time.time(),
                    'metadata': {'tokens': 500}
                }
            ] * 50  # 50 messages per conversation
        }
        
        template_size = len(json.dumps(template_conv).encode('utf-8'))
        estimated_convs_needed = target_bytes // template_size
        
        for i in range(max(1, estimated_convs_needed)):
            messages = []
            for j in range(50):  # 50 messages per conversation
                message_content = f'Message {j} content with substantial text. ' * 100
                messages.append({
                    'id': f'msg_{j}',
                    'role': 'user' if j % 2 == 0 else 'assistant',
                    'content': message_content,
                    'timestamp': time.time(),
                    'metadata': {
                        'tokens': len(message_content.split()),
                        'processing_time': random.uniform(0.1, 3.0),
                        'model': 'claude-3-sonnet',
                        'extra_data': 'x' * 100  # 100 bytes padding
                    }
                })
            
            conversation = {
                'id': f'huge_conv_{i}',
                'created': time.time(),
                'messages': messages,
                'metadata': {
                    'total_tokens': sum(msg['metadata']['tokens'] for msg in messages),
                    'conversation_summary': f'Large conversation {i} with many messages.',
                    'padding': 'y' * 1000  # 1KB padding per conversation
                }
            }
            
            conversations.append(conversation)
            conv_count += 1
            
            # Check size periodically
            if conv_count % 10 == 0:
                test_state = {'conversations': conversations}
                current_size = len(json.dumps(test_state).encode('utf-8'))
                if current_size >= target_bytes:
                    break
        
        return {
            'conversations': conversations,
            'metadata': {
                'version': '1.0.0',
                'created': time.time(),
                'uuid': str(uuid.uuid4()),
                'size_info': {
                    'target_size_mb': target_size_mb,
                    'conversation_count': len(conversations),
                    'estimated_size_mb': current_size / (1024 * 1024)
                },
                'large_padding': 'z' * 50000  # 50KB final padding
            }
        }


class ConfigurationBuilder:
    """Builder for Memory Guardian configurations for various test scenarios."""
    
    @staticmethod
    def minimal_config() -> MemoryGuardianConfig:
        """Minimal configuration for basic testing."""
        return MemoryGuardianConfig(
            enabled=True,
            thresholds=MemoryThresholds(warning=100, critical=200, emergency=300),
            monitoring=MonitoringConfig(check_interval=1),
            process_command=['echo', 'minimal test'],
            persist_state=False
        )
    
    @staticmethod
    def development_config(workspace: Path) -> MemoryGuardianConfig:
        """Configuration for development/testing environment."""
        return MemoryGuardianConfig(
            enabled=True,
            thresholds=MemoryThresholds(warning=500, critical=1000, emergency=1500),
            restart_policy=RestartPolicy(
                max_attempts=5,
                attempt_window=300,
                initial_cooldown=1,
                graceful_timeout=5
            ),
            monitoring=MonitoringConfig(
                check_interval=1,
                check_interval_warning=0.5,
                check_interval_critical=0.25,
                log_memory_stats=True
            ),
            process_command=['python', '-c', 'import time; time.sleep(60)'],
            working_directory=str(workspace),
            state_file=str(workspace / 'dev_state.json'),
            persist_state=True
        )
    
    @staticmethod
    def production_config(workspace: Path) -> MemoryGuardianConfig:
        """Configuration for production-like environment."""
        return MemoryGuardianConfig(
            enabled=True,
            thresholds=MemoryThresholds(warning=2000, critical=4000, emergency=6000),
            restart_policy=RestartPolicy(
                max_attempts=3,
                attempt_window=600,  # 10 minutes
                initial_cooldown=30,
                max_cooldown=300,
                graceful_timeout=30,
                exponential_backoff=True
            ),
            monitoring=MonitoringConfig(
                check_interval=10,
                check_interval_warning=5,
                check_interval_critical=2,
                check_interval_emergency=1,
                log_memory_stats=True,
                log_interval=60
            ),
            process_command=['python', '-c', 'import time; time.sleep(3600)'],
            working_directory=str(workspace),
            state_file=str(workspace / 'production_state.json'),
            persist_state=True,
            auto_start=True
        )
    
    @staticmethod
    def stress_test_config(workspace: Path) -> MemoryGuardianConfig:
        """Configuration optimized for stress testing."""
        return MemoryGuardianConfig(
            enabled=True,
            thresholds=MemoryThresholds(warning=200, critical=400, emergency=600),
            restart_policy=RestartPolicy(
                max_attempts=10,
                attempt_window=60,
                initial_cooldown=0.5,
                max_cooldown=10,
                graceful_timeout=2,
                exponential_backoff=True
            ),
            monitoring=MonitoringConfig(
                check_interval=0.1,  # Very fast
                check_interval_warning=0.05,
                check_interval_critical=0.025,
                check_interval_emergency=0.01,
                log_memory_stats=False  # Reduce I/O during stress tests
            ),
            process_command=['python', '-c', 'import time; time.sleep(30)'],
            working_directory=str(workspace),
            state_file=str(workspace / 'stress_state.json'),
            persist_state=True
        )
    
    @staticmethod
    def performance_test_config(workspace: Path) -> MemoryGuardianConfig:
        """Configuration optimized for performance testing."""
        return MemoryGuardianConfig(
            enabled=True,
            thresholds=MemoryThresholds(warning=1000, critical=2000, emergency=3000),
            restart_policy=RestartPolicy(
                max_attempts=5,
                graceful_timeout=1,
                initial_cooldown=0.1
            ),
            monitoring=MonitoringConfig(
                check_interval=0.01,  # Extreme frequency for perf testing
                log_memory_stats=False
            ),
            process_command=['python', '-c', 'import time; time.sleep(10)'],
            working_directory=str(workspace),
            persist_state=False  # Reduce I/O for pure performance testing
        )


class MemoryPatternGenerator:
    """Generator for various memory usage patterns."""
    
    @staticmethod
    def linear_growth(duration: float, start_mb: float, end_mb: float, steps: int) -> List[float]:
        """Generate linear memory growth pattern."""
        step_size = (end_mb - start_mb) / steps
        return [start_mb + (i * step_size) for i in range(steps)]
    
    @staticmethod
    def exponential_growth(duration: float, start_mb: float, growth_rate: float, steps: int) -> List[float]:
        """Generate exponential memory growth pattern."""
        return [start_mb * (growth_rate ** (i / steps * duration)) for i in range(steps)]
    
    @staticmethod
    def sawtooth_pattern(duration: float, base_mb: float, amplitude_mb: float, frequency: float, steps: int) -> List[float]:
        """Generate sawtooth memory pattern."""
        pattern = []
        for i in range(steps):
            t = i / steps * duration
            phase = (t * frequency) % 1.0
            sawtooth = 2 * abs(phase - 0.5) - 0.5  # -0.5 to 0.5
            memory = base_mb + (amplitude_mb * sawtooth)
            pattern.append(max(10.0, memory))  # Minimum 10MB
        return pattern
    
    @staticmethod
    def spike_pattern(duration: float, base_mb: float, spike_mb: float, spike_frequency: float, steps: int) -> List[float]:
        """Generate memory pattern with periodic spikes."""
        pattern = []
        spike_interval = int(steps / (duration * spike_frequency))
        
        for i in range(steps):
            if spike_interval > 0 and i % spike_interval == 0:
                memory = base_mb + spike_mb
            else:
                memory = base_mb + random.uniform(-10, 20)  # Small variations
            pattern.append(max(10.0, memory))
        return pattern
    
    @staticmethod
    def random_walk(duration: float, start_mb: float, volatility: float, steps: int) -> List[float]:
        """Generate random walk memory pattern."""
        pattern = [start_mb]
        current = start_mb
        
        for i in range(1, steps):
            change = random.uniform(-volatility, volatility)
            current = max(10.0, current + change)
            pattern.append(current)
        
        return pattern
    
    @staticmethod
    def realistic_claude_pattern(duration: float, steps: int) -> List[float]:
        """Generate realistic Claude conversation memory pattern."""
        base_memory = 150.0  # Base Claude memory usage
        pattern = []
        
        # Simulate conversation turns
        turns_per_minute = 2
        total_turns = int(duration / 60 * turns_per_minute)
        turn_interval = steps // max(1, total_turns)
        
        current_memory = base_memory
        
        for i in range(steps):
            # Gradual growth from conversation history
            growth_rate = 0.5  # MB per step
            current_memory += growth_rate
            
            # Periodic spikes for large responses
            if turn_interval > 0 and i % turn_interval == 0:
                spike_size = random.uniform(50, 200)  # Large response
                current_memory += spike_size
            
            # Occasional GC drops
            if random.random() < 0.05:  # 5% chance
                gc_reduction = random.uniform(20, 100)
                current_memory = max(base_memory, current_memory - gc_reduction)
            
            # Add noise
            noise = random.uniform(-5, 10)
            current_memory = max(base_memory, current_memory + noise)
            
            pattern.append(current_memory)
        
        return pattern


class PlatformCommandMocks:
    """Platform-specific command mocks for testing."""
    
    @staticmethod
    def mock_memory_commands():
        """Mock platform-specific memory monitoring commands."""
        mocks = {}
        
        if platform.system() == 'Darwin':  # macOS
            mocks['ps'] = MagicMock()
            mocks['ps'].return_value.stdout = "  RSS    VSZ\n12345 67890\n"
            mocks['ps'].return_value.returncode = 0
        
        elif platform.system() == 'Linux':
            mocks['cat'] = MagicMock()
            mocks['cat'].return_value.stdout = "VmRSS:\t12345 kB\nVmSize:\t67890 kB\n"
            mocks['cat'].return_value.returncode = 0
        
        elif platform.system() == 'Windows':
            mocks['tasklist'] = MagicMock()
            mocks['tasklist'].return_value.stdout = "python.exe\t12345\t\t\t12,345 K\n"
            mocks['tasklist'].return_value.returncode = 0
        
        return mocks
    
    @staticmethod
    def mock_process_commands():
        """Mock process management commands."""
        mocks = {}
        
        # Kill/terminate commands
        mocks['kill'] = MagicMock()
        mocks['kill'].return_value.returncode = 0
        
        mocks['taskkill'] = MagicMock()  # Windows
        mocks['taskkill'].return_value.returncode = 0
        
        # Process listing
        mocks['ps'] = MagicMock()
        mocks['ps'].return_value.stdout = "  PID COMMAND\n12345 python\n"
        mocks['ps'].return_value.returncode = 0
        
        return mocks


# Pytest fixtures
@pytest.fixture
def temp_workspace():
    """Create temporary workspace for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        (workspace / 'scripts').mkdir()
        (workspace / 'logs').mkdir()
        (workspace / 'state').mkdir()
        yield workspace


@pytest.fixture
def mock_claude_process():
    """Create mock Claude process with default configuration."""
    config = MockProcessConfig()
    return MockClaudeProcess(config)


@pytest.fixture
def mock_claude_process_growing():
    """Create mock Claude process with growing memory."""
    config = MockProcessConfig(
        initial_memory_mb=100,
        memory_growth_rate=50,  # 50 MB/s
        max_memory_mb=1000,
        memory_pattern='linear'
    )
    return MockClaudeProcess(config)


@pytest.fixture
def mock_claude_process_chaotic():
    """Create mock Claude process with chaotic memory behavior."""
    config = MockProcessConfig(
        initial_memory_mb=200,
        memory_pattern='random',
        pattern_params={'variance': 100}
    )
    return MockClaudeProcess(config)


@pytest.fixture
def small_state_data():
    """Generate small test state data."""
    return StateDataGenerator.generate_small_state()


@pytest.fixture
def medium_state_data():
    """Generate medium test state data."""
    return StateDataGenerator.generate_medium_state()


@pytest.fixture
def large_state_data():
    """Generate large test state data."""
    return StateDataGenerator.generate_large_state()


@pytest.fixture
def minimal_config():
    """Minimal Memory Guardian configuration."""
    return ConfigurationBuilder.minimal_config()


@pytest.fixture
def development_config(temp_workspace):
    """Development Memory Guardian configuration."""
    return ConfigurationBuilder.development_config(temp_workspace)


@pytest.fixture
def production_config(temp_workspace):
    """Production Memory Guardian configuration."""
    return ConfigurationBuilder.production_config(temp_workspace)


@pytest.fixture
def stress_test_config(temp_workspace):
    """Stress test Memory Guardian configuration."""
    return ConfigurationBuilder.stress_test_config(temp_workspace)


@pytest.fixture
def performance_test_config(temp_workspace):
    """Performance test Memory Guardian configuration."""
    return ConfigurationBuilder.performance_test_config(temp_workspace)


@pytest.fixture
def memory_pattern_linear():
    """Linear memory growth pattern."""
    return MemoryPatternGenerator.linear_growth(
        duration=30,
        start_mb=100,
        end_mb=800,
        steps=100
    )


@pytest.fixture
def memory_pattern_realistic():
    """Realistic Claude memory pattern."""
    return MemoryPatternGenerator.realistic_claude_pattern(
        duration=300,  # 5 minutes
        steps=150
    )


@pytest.fixture
def platform_mocks():
    """Platform-specific command mocks."""
    return {
        'memory': PlatformCommandMocks.mock_memory_commands(),
        'process': PlatformCommandMocks.mock_process_commands()
    }


# Test scenario fixtures
@pytest.fixture
def normal_operation_scenario(development_config):
    """Normal operation test scenario."""
    return TestScenario(
        name="normal_operation",
        description="Test normal operation with gradual memory growth",
        config=development_config,
        expected_behavior={
            'max_restarts': 0,
            'final_state': ProcessState.RUNNING,
            'memory_states_seen': [MemoryState.NORMAL, MemoryState.WARNING]
        },
        test_duration=10.0
    )


@pytest.fixture
def memory_pressure_scenario(stress_test_config):
    """Memory pressure test scenario."""
    return TestScenario(
        name="memory_pressure",
        description="Test behavior under memory pressure leading to restarts",
        config=stress_test_config,
        expected_behavior={
            'min_restarts': 1,
            'final_state': ProcessState.RUNNING,
            'memory_states_seen': [MemoryState.WARNING, MemoryState.CRITICAL, MemoryState.EMERGENCY]
        },
        test_duration=15.0
    )


@pytest.fixture
def rapid_growth_scenario(stress_test_config):
    """Rapid memory growth test scenario."""
    return TestScenario(
        name="rapid_growth",
        description="Test rapid memory growth requiring immediate intervention",
        config=stress_test_config,
        expected_behavior={
            'min_restarts': 2,
            'memory_states_seen': [MemoryState.EMERGENCY],
            'restart_protection_triggered': True
        },
        test_duration=20.0
    )


# Helper functions
def create_memory_growth_script(
    workspace: Path,
    growth_rate_mb: int = 50,
    max_memory_mb: int = 500,
    duration_seconds: int = 30
) -> Path:
    """Create a script that simulates memory growth."""
    script_content = f'''#!/usr/bin/env python3
import gc
import os
import sys
import time
from datetime import datetime

def log(msg):
    print(f"[{{datetime.now().isoformat()}}] {{msg}}", flush=True)

def main():
    log(f"Memory growth script starting, PID: {{os.getpid()}}")
    
    memory_chunks = []
    chunk_size_mb = 10
    chunk_size_bytes = chunk_size_mb * 1024 * 1024
    
    start_time = time.time()
    target_duration = {duration_seconds}
    
    while time.time() - start_time < target_duration:
        # Allocate memory
        chunk = bytearray(chunk_size_bytes)
        memory_chunks.append(chunk)
        
        current_memory = len(memory_chunks) * chunk_size_mb
        log(f"Allocated {{chunk_size_mb}}MB, total: {{current_memory}}MB")
        
        if current_memory >= {max_memory_mb}:
            log(f"Reached target memory: {{current_memory}}MB")
            break
        
        time.sleep({60 / growth_rate_mb})  # Sleep to achieve target growth rate
    
    log("Memory growth script completed")
    time.sleep(5)  # Hold memory briefly

if __name__ == "__main__":
    main()
'''
    
    script_path = workspace / "scripts" / "memory_growth.py"
    with open(script_path, 'w') as f:
        f.write(script_content)
    
    script_path.chmod(0o755)
    return script_path


def create_test_claude_simulator(workspace: Path) -> Path:
    """Create a Claude conversation simulator script."""
    script_content = '''#!/usr/bin/env python3
import json
import os
import random
import time
from pathlib import Path
from datetime import datetime

def log(msg):
    print(f"[{datetime.now().isoformat()}] {msg}", flush=True)

def main():
    log(f"Claude conversation simulator starting, PID: {os.getpid()}")
    
    # Simulate .claude.json file growth
    claude_file = Path(".claude.json")
    
    conversation_data = {
        "conversations": [],
        "metadata": {
            "created": time.time(),
            "version": "test-simulator"
        }
    }
    
    for turn in range(50):  # 50 conversation turns
        # Simulate user message
        user_msg = f"User message {turn}: " + ("test content " * random.randint(20, 100))
        
        # Simulate assistant response
        assistant_msg = f"Assistant response {turn}: " + ("response content " * random.randint(50, 200))
        
        conversation_data["conversations"].append({
            "id": f"turn_{turn}",
            "timestamp": time.time(),
            "user_message": user_msg,
            "assistant_response": assistant_msg
        })
        
        # Write to file
        with open(claude_file, 'w') as f:
            json.dump(conversation_data, f, indent=2)
        
        file_size = claude_file.stat().st_size / (1024 * 1024)
        log(f"Turn {turn}: .claude.json size: {file_size:.2f}MB")
        
        time.sleep(0.5)  # Pause between turns
    
    log("Claude conversation simulation completed")
    time.sleep(10)  # Keep running for monitoring

if __name__ == "__main__":
    main()
'''
    
    script_path = workspace / "scripts" / "claude_simulator.py"
    with open(script_path, 'w') as f:
        f.write(script_content)
    
    script_path.chmod(0o755)
    return script_path


# Assertion helpers
def assert_memory_guardian_health(guardian: MemoryGuardian):
    """Assert that Memory Guardian is in healthy state."""
    assert guardian._initialized, "Guardian should be initialized"
    assert not guardian._shutdown, "Guardian should not be shutdown"
    
    status = guardian.get_status()
    assert status is not None, "Should be able to get status"
    assert status['enabled'], "Guardian should be enabled"


def assert_monitoring_activity(guardian: MemoryGuardian, min_samples: int = 1):
    """Assert that monitoring has been active."""
    assert guardian.memory_stats.samples >= min_samples, f"Should have at least {min_samples} memory samples"
    assert guardian.memory_stats.last_check > 0, "Should have recorded memory checks"


def assert_state_transitions(guardian: MemoryGuardian, expected_states: List[MemoryState]):
    """Assert that expected memory state transitions occurred."""
    # This would need to be enhanced with actual state tracking
    # For now, just check current state is reasonable
    assert guardian.memory_state in expected_states, f"Memory state {guardian.memory_state} not in expected states {expected_states}"


def assert_restart_behavior(guardian: MemoryGuardian, expected_restarts: int = None, max_restarts: int = None):
    """Assert restart behavior meets expectations."""
    actual_restarts = len(guardian.restart_attempts)
    
    if expected_restarts is not None:
        assert actual_restarts == expected_restarts, f"Expected {expected_restarts} restarts, got {actual_restarts}"
    
    if max_restarts is not None:
        assert actual_restarts <= max_restarts, f"Too many restarts: {actual_restarts} > {max_restarts}"