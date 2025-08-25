# Testing Guide

This guide documents the testing strategies, patterns, structure, and best practices for Claude MPM. It covers unit tests, integration tests, end-to-end tests, performance testing, and security testing.

**Last Updated**: 2025-08-14  
**Architecture Version**: 3.8.2  
**Related Documents**: [ARCHITECTURE.md](ARCHITECTURE.md), [SERVICES.md](developer/SERVICES.md), [QA.md](QA.md)

## Table of Contents

- [Overview](#overview)
- [Testing Strategy](#testing-strategy)
- [Test Structure](#test-structure)
- [Testing Patterns](#testing-patterns)
- [Test Categories](#test-categories)
- [Testing Tools and Frameworks](#testing-tools-and-frameworks)
- [Test Execution](#test-execution)
- [Coverage and Metrics](#coverage-and-metrics)
- [Performance Testing](#performance-testing)
- [Security Testing](#security-testing)
- [Best Practices](#best-practices)

## Overview

Claude MPM uses a comprehensive testing strategy with multiple levels of testing to ensure reliability, performance, and security. The testing approach follows industry best practices with automated testing, continuous integration, and quality metrics.

### Testing Philosophy

1. **Test-Driven Development**: Write tests before implementation when feasible
2. **Pyramid Testing**: More unit tests, fewer integration tests, minimal E2E tests
3. **Fast Feedback**: Quick test execution for rapid development cycles
4. **Comprehensive Coverage**: Test all critical paths and edge cases
5. **Realistic Testing**: Use realistic data and scenarios in tests

### Quality Metrics

- **Unit Test Coverage**: > 85% for core services
- **Integration Test Coverage**: > 70% for service interactions
- **E2E Test Coverage**: > 90% for critical user journeys
- **Performance Test Coverage**: All performance-critical operations
- **Security Test Coverage**: All security-sensitive operations

## Testing Strategy

### Testing Pyramid

```
                    /\
                   /  \
                  /E2E \     <- End-to-End Tests (10-20%)
                 /______\
                /        \
               /Integration\ <- Integration Tests (20-30%)
              /__________\
             /            \
            /   Unit Tests  \  <- Unit Tests (50-70%)
           /________________\
```

#### Unit Tests (50-70% of tests)
- Test individual functions and methods in isolation
- Fast execution (< 1ms per test)
- Mock external dependencies
- Focus on business logic and edge cases

#### Integration Tests (20-30% of tests)
- Test component interactions
- Test database operations
- Test API endpoints
- Test service integrations

#### End-to-End Tests (10-20% of tests)
- Test complete user workflows
- Test critical business scenarios
- Test across multiple services
- Slower execution but high confidence

## Test Structure

### Directory Organization

```
tests/
├── __init__.py                 # Test package initialization
├── conftest.py                 # Shared pytest configuration
├── fixtures/                   # Test data and fixtures
│   ├── agent_configs/          # Sample agent configurations
│   ├── test_data/              # Test datasets
│   └── mock_responses/         # Mock API responses
├── unit/                       # Unit tests
│   ├── services/               # Service unit tests
│   ├── core/                   # Core functionality tests
│   ├── utils/                  # Utility function tests
│   └── validation/             # Validation tests
├── integration/                # Integration tests
│   ├── test_agent_deployment.py
│   ├── test_memory_system.py
│   ├── test_socketio_integration.py
│   └── test_service_interactions.py
├── e2e/                        # End-to-end tests
│   ├── test_complete_workflows.py
│   ├── test_agent_lifecycle.py
│   └── test_dashboard_integration.py
├── performance/                # Performance tests
│   ├── test_caching_performance.py
│   ├── test_memory_optimization.py
│   └── test_concurrent_operations.py
├── security/                   # Security tests
│   ├── test_input_validation.py
│   ├── test_path_traversal.py
│   └── test_authentication.py
└── scripts/                    # Test execution scripts
    ├── run_tests.py
    └── generate_coverage.py
```

### Test File Naming Conventions

- **Unit Tests**: `test_{module_name}.py`
- **Integration Tests**: `test_{feature}_integration.py`
- **E2E Tests**: `test_{workflow}_e2e.py`
- **Performance Tests**: `test_{feature}_performance.py`
- **Security Tests**: `test_{feature}_security.py`

## Testing Patterns

### Unit Testing Patterns

#### 1. Service Testing with Mocks

```python
import pytest
from unittest.mock import Mock, patch, MagicMock
from claude_mpm.services.agent.deployment import AgentDeploymentService
from claude_mpm.core.exceptions import AgentDeploymentError


class TestAgentDeploymentService:
    """Unit tests for AgentDeploymentService"""
    
    @pytest.fixture
    def deployment_service(self):
        """Create deployment service with mocked dependencies"""
        with patch('claude_mpm.services.agent.deployment.Path') as mock_path:
            service = AgentDeploymentService()
            service._file_system = Mock()
            service._validator = Mock()
            return service
    
    def test_deploy_agents_success(self, deployment_service):
        """Test successful agent deployment"""
        # Arrange
        mock_agents = ['engineer', 'qa', 'research']
        deployment_service._discover_agents = Mock(return_value=mock_agents)
        deployment_service._deploy_single_agent = Mock(return_value=True)
        
        # Act
        result = deployment_service.deploy_agents()
        
        # Assert
        assert result['success'] is True
        assert result['deployed_count'] == 3
        assert deployment_service._deploy_single_agent.call_count == 3
    
    def test_deploy_agents_partial_failure(self, deployment_service):
        """Test deployment with some failures"""
        # Arrange
        deployment_service._discover_agents = Mock(return_value=['agent1', 'agent2'])
        deployment_service._deploy_single_agent = Mock(side_effect=[True, False])
        
        # Act
        result = deployment_service.deploy_agents()
        
        # Assert
        assert result['success'] is False
        assert result['deployed_count'] == 1
        assert len(result['failed_agents']) == 1
    
    @pytest.mark.parametrize("agent_config,expected_valid", [
        ({"agent_id": "test", "version": "1.0.0"}, True),
        ({"agent_id": "", "version": "1.0.0"}, False),
        ({"agent_id": "test"}, False),  # Missing version
        ({}, False),  # Empty config
    ])
    def test_validate_agent_config(self, deployment_service, agent_config, expected_valid):
        """Test agent configuration validation"""
        result = deployment_service.validate_agent(agent_config)
        assert result[0] == expected_valid
```

#### 2. Interface Testing

```python
import pytest
from claude_mpm.services.core.interfaces import IAgentRegistry, AgentMetadata


class TestAgentRegistryInterface:
    """Test agent registry interface compliance"""
    
    @pytest.fixture
    def registry_implementation(self):
        """Get registry implementation to test"""
        from claude_mpm.services.agent.registry import AgentRegistry
        return AgentRegistry()
    
    @pytest.mark.asyncio
    async def test_discover_agents_returns_dict(self, registry_implementation):
        """Test that discover_agents returns proper structure"""
        result = await registry_implementation.discover_agents()
        
        assert isinstance(result, dict)
        for agent_id, metadata in result.items():
            assert isinstance(agent_id, str)
            assert isinstance(metadata, AgentMetadata)
    
    @pytest.mark.asyncio
    async def test_get_agent_returns_metadata_or_none(self, registry_implementation):
        """Test that get_agent returns AgentMetadata or None"""
        # Test with valid agent
        result = await registry_implementation.get_agent("engineer")
        assert result is None or isinstance(result, AgentMetadata)
        
        # Test with invalid agent
        result = await registry_implementation.get_agent("nonexistent")
        assert result is None
```

### Integration Testing Patterns

#### 1. Service Integration Testing

```python
import pytest
import asyncio
from claude_mpm.services.agent.registry import AgentRegistry
from claude_mpm.services.agent.deployment import AgentDeploymentService
from claude_mpm.services.memory.router import MemoryRouter


class TestServiceIntegration:
    """Integration tests for service interactions"""
    
    @pytest.fixture
    async def integrated_services(self):
        """Setup integrated services for testing"""
        registry = AgentRegistry()
        deployment = AgentDeploymentService()
        memory = MemoryRouter()
        
        # Initialize services
        await registry.initialize()
        await deployment.initialize()
        await memory.initialize()
        
        yield {
            'registry': registry,
            'deployment': deployment,
            'memory': memory
        }
        
        # Cleanup
        await registry.shutdown()
        await deployment.shutdown()
        await memory.shutdown()
    
    @pytest.mark.asyncio
    async def test_agent_deployment_and_discovery(self, integrated_services):
        """Test that deployed agents are discoverable"""
        registry = integrated_services['registry']
        deployment = integrated_services['deployment']
        
        # Deploy agents
        deploy_result = deployment.deploy_agents()
        assert deploy_result['success'] is True
        
        # Discover agents
        agents = await registry.discover_agents(force_refresh=True)
        assert len(agents) > 0
        
        # Verify deployed agents are discoverable
        for agent_id in deploy_result['deployed_agents']:
            assert agent_id in agents
    
    @pytest.mark.asyncio
    async def test_memory_integration_with_agents(self, integrated_services):
        """Test memory system integration with agent operations"""
        registry = integrated_services['registry']
        memory = integrated_services['memory']
        
        # Get test agent
        agents = await registry.discover_agents()
        test_agent = next(iter(agents.keys()))
        
        # Test memory operations
        test_memory = "Test memory content for integration testing"
        save_result = await memory.save_memory(test_agent, test_memory)
        assert save_result is True
        
        # Retrieve memory
        retrieved_memory = await memory.load_memory(test_agent)
        assert test_memory in retrieved_memory
```

#### 2. Database Integration Testing

```python
import pytest
import tempfile
from pathlib import Path
from claude_mpm.services.persistence.database import DatabaseService


class TestDatabaseIntegration:
    """Integration tests for database operations"""
    
    @pytest.fixture
    def temp_database(self):
        """Create temporary database for testing"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test.db"
            db_service = DatabaseService(db_path)
            db_service.initialize()
            yield db_service
            db_service.shutdown()
    
    def test_agent_metadata_persistence(self, temp_database):
        """Test agent metadata storage and retrieval"""
        # Store agent metadata
        metadata = {
            'agent_id': 'test_agent',
            'version': '1.0.0',
            'capabilities': ['testing', 'validation']
        }
        
        result = temp_database.store_agent_metadata(metadata)
        assert result is True
        
        # Retrieve metadata
        retrieved = temp_database.get_agent_metadata('test_agent')
        assert retrieved['agent_id'] == 'test_agent'
        assert retrieved['version'] == '1.0.0'
        assert 'testing' in retrieved['capabilities']
    
    def test_concurrent_database_access(self, temp_database):
        """Test concurrent database operations"""
        import threading
        import time
        
        results = []
        errors = []
        
        def worker(worker_id):
            try:
                for i in range(10):
                    metadata = {
                        'agent_id': f'agent_{worker_id}_{i}',
                        'version': '1.0.0',
                        'timestamp': time.time()
                    }
                    result = temp_database.store_agent_metadata(metadata)
                    results.append(result)
            except Exception as e:
                errors.append(e)
        
        # Start multiple workers
        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Verify results
        assert len(errors) == 0, f"Database errors: {errors}"
        assert all(results), "Some database operations failed"
```

### End-to-End Testing Patterns

#### 1. Complete Workflow Testing

```python
import pytest
import subprocess
import tempfile
from pathlib import Path


class TestE2EWorkflows:
    """End-to-end workflow tests"""
    
    @pytest.fixture
    def clean_environment(self):
        """Setup clean testing environment"""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_env = {
                'CLAUDE_MPM_HOME': temp_dir,
                'PYTHONPATH': str(Path(__file__).parent.parent / 'src')
            }
            yield temp_dir, test_env
    
    def test_complete_agent_deployment_workflow(self, clean_environment):
        """Test complete agent deployment workflow"""
        temp_dir, env = clean_environment
        
        # Run agent deployment command
        result = subprocess.run([
            'python', '-m', 'claude_mpm.cli',
            'agents', 'deploy',
            '--force'
        ], env=env, capture_output=True, text=True, timeout=60)
        
        assert result.returncode == 0, f"Deployment failed: {result.stderr}"
        
        # Verify deployment output
        assert "Successfully deployed" in result.stdout
        
        # Verify agents are deployed
        agents_dir = Path(temp_dir) / '.claude' / 'agents'
        assert agents_dir.exists()
        
        # Check for specific agents
        expected_agents = ['engineer.md', 'qa.md', 'research.md']
        for agent_file in expected_agents:
            agent_path = agents_dir / agent_file
            assert agent_path.exists(), f"Agent {agent_file} not deployed"
    
    def test_interactive_mode_startup(self, clean_environment):
        """Test interactive mode startup and basic functionality"""
        temp_dir, env = clean_environment
        
        # Start interactive mode (with timeout)
        process = subprocess.Popen([
            'python', '-m', 'claude_mpm.cli'
        ], env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE, 
           stderr=subprocess.PIPE, text=True)
        
        try:
            # Send 'help' command
            stdout, stderr = process.communicate(input='help\nexit\n', timeout=30)
            
            # Verify help output
            assert 'Available commands:' in stdout or 'help' in stdout.lower()
            assert process.returncode == 0
            
        except subprocess.TimeoutExpired:
            process.kill()
            pytest.fail("Interactive mode startup timed out")
```

## Test Categories

### 1. Unit Tests

**Purpose**: Test individual components in isolation

**Characteristics**:
- Fast execution (< 1ms each)
- No external dependencies
- Mock all dependencies
- Test business logic and edge cases

**Example Structure**:
```python
class TestAgentValidator:
    """Unit tests for agent validation"""
    
    def test_valid_agent_config(self):
        """Test validation of valid agent configuration"""
        # Test implementation
        pass
    
    def test_invalid_agent_id(self):
        """Test validation fails for invalid agent ID"""
        # Test implementation
        pass
    
    @pytest.mark.parametrize("input,expected", [
        ("valid_id", True),
        ("invalid-id!", False),
        ("", False)
    ])
    def test_agent_id_validation(self, input, expected):
        """Parameterized test for agent ID validation"""
        # Test implementation
        pass
```

### 2. Integration Tests

**Purpose**: Test component interactions and integrations

**Characteristics**:
- Test service interactions
- Use real dependencies where possible
- Test data flow between components
- Verify interface contracts

**Example Structure**:
```python
class TestAgentServiceIntegration:
    """Integration tests for agent services"""
    
    @pytest.fixture
    def services(self):
        """Setup integrated services"""
        # Setup code
        pass
    
    def test_agent_deployment_flow(self, services):
        """Test complete agent deployment flow"""
        # Test implementation
        pass
```

### 3. End-to-End Tests

**Purpose**: Test complete user workflows

**Characteristics**:
- Test from user perspective
- Use real CLI commands
- Test critical business scenarios
- Slower execution but high confidence

**Example Structure**:
```python
class TestE2EUserWorkflows:
    """End-to-end tests for user workflows"""
    
    def test_new_user_setup(self):
        """Test complete new user setup workflow"""
        # Test implementation
        pass
```

## Testing Tools and Frameworks

### Core Testing Framework

```python
# pytest configuration (conftest.py)
import pytest
import asyncio
from pathlib import Path


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_directory():
    """Provide temporary directory for tests"""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def mock_agent_config():
    """Provide mock agent configuration"""
    return {
        "agent_id": "test_agent",
        "version": "1.0.0",
        "metadata": {
            "name": "Test Agent",
            "description": "Agent for testing"
        },
        "capabilities": {
            "tools": ["testing"],
            "model": "claude-sonnet-3-5-20241022"
        },
        "instructions": "Test agent instructions"
    }
```

### Testing Utilities

```python
# tests/utils/test_helpers.py
import json
import time
from pathlib import Path
from typing import Dict, Any


class TestHelpers:
    """Utilities for test setup and assertions"""
    
    @staticmethod
    def create_mock_agent_file(path: Path, config: Dict[str, Any]) -> None:
        """Create mock agent file for testing"""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w') as f:
            json.dump(config, f, indent=2)
    
    @staticmethod
    def wait_for_condition(condition_func, timeout: float = 5.0, interval: float = 0.1) -> bool:
        """Wait for condition to be true with timeout"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            if condition_func():
                return True
            time.sleep(interval)
        return False
    
    @staticmethod
    def assert_agent_deployed(agents_dir: Path, agent_id: str) -> None:
        """Assert that agent is properly deployed"""
        agent_file = agents_dir / f"{agent_id}.md"
        assert agent_file.exists(), f"Agent {agent_id} not deployed"
        
        content = agent_file.read_text()
        assert agent_id in content, f"Agent content missing agent ID"
```

## Test Execution

### Local Test Execution

#### Run All Tests
```bash
# Run complete test suite
./scripts/run_all_tests.sh

# Run specific test categories
pytest tests/unit/ -v                    # Unit tests only
pytest tests/integration/ -v             # Integration tests only
pytest tests/e2e/ -v                     # E2E tests only
```

#### Run Tests with Coverage
```bash
# Generate coverage report
pytest --cov=src/claude_mpm --cov-report=html --cov-report=term

# Coverage with minimum threshold
pytest --cov=src/claude_mpm --cov-fail-under=85
```

#### Run Performance Tests
```bash
# Run performance tests
pytest tests/performance/ -v --benchmark-only

# Performance tests with profiling
pytest tests/performance/ -v --profile
```

### Continuous Integration

```yaml
# .github/workflows/tests.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.8, 3.9, 3.10, 3.11]
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v3
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -e .
        pip install pytest pytest-cov pytest-asyncio
    
    - name: Run unit tests
      run: pytest tests/unit/ -v --cov=src/claude_mpm
    
    - name: Run integration tests
      run: pytest tests/integration/ -v
    
    - name: Run E2E tests
      run: pytest tests/e2e/ -v
    
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
```

## Coverage and Metrics

### Coverage Configuration

```ini
# .coveragerc
[run]
source = src/claude_mpm
omit = 
    */tests/*
    */venv/*
    */__pycache__/*
    */build/*
    */dist/*

[report]
exclude_lines =
    pragma: no cover
    def __repr__
    raise AssertionError
    raise NotImplementedError
    if __name__ == .__main__.:

[html]
directory = htmlcov
```

### Quality Metrics

```python
# scripts/quality_metrics.py
import subprocess
import json
from pathlib import Path


class QualityMetrics:
    """Collect and report quality metrics"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
    
    def get_test_coverage(self) -> float:
        """Get current test coverage percentage"""
        result = subprocess.run([
            'pytest', '--cov=src/claude_mpm', '--cov-report=json'
        ], capture_output=True, text=True, cwd=self.project_root)
        
        if result.returncode == 0:
            with open('coverage.json') as f:
                coverage_data = json.load(f)
            return coverage_data['totals']['percent_covered']
        return 0.0
    
    def get_test_counts(self) -> dict:
        """Get test count statistics"""
        result = subprocess.run([
            'pytest', '--collect-only', '-q'
        ], capture_output=True, text=True, cwd=self.project_root)
        
        lines = result.stdout.split('\n')
        summary_line = [line for line in lines if 'test' in line and 'collected' in line]
        
        if summary_line:
            # Parse test count from summary
            import re
            match = re.search(r'(\d+) tests? collected', summary_line[0])
            if match:
                return {'total_tests': int(match.group(1))}
        
        return {'total_tests': 0}
```

## Performance Testing

### Performance Test Framework

```python
import pytest
import time
import asyncio
from concurrent.futures import ThreadPoolExecutor


class TestPerformance:
    """Performance tests for critical operations"""
    
    @pytest.mark.performance
    def test_agent_discovery_performance(self):
        """Test agent discovery performance"""
        from claude_mpm.services.agent.registry import AgentRegistry
        
        registry = AgentRegistry()
        
        # Measure performance
        start_time = time.time()
        agents = asyncio.run(registry.discover_agents())
        end_time = time.time()
        
        discovery_time = end_time - start_time
        
        # Performance assertions
        assert discovery_time < 0.5, f"Agent discovery too slow: {discovery_time}s"
        assert len(agents) > 0, "No agents discovered"
    
    @pytest.mark.performance
    def test_concurrent_agent_operations(self):
        """Test concurrent agent operations performance"""
        from claude_mpm.services.agent.deployment import AgentDeploymentService
        
        deployment_service = AgentDeploymentService()
        
        def deploy_agent(agent_id):
            return deployment_service.deploy_single_agent(agent_id)
        
        # Test concurrent deployment
        agent_ids = ['test1', 'test2', 'test3', 'test4', 'test5']
        
        start_time = time.time()
        with ThreadPoolExecutor(max_workers=3) as executor:
            results = list(executor.map(deploy_agent, agent_ids))
        end_time = time.time()
        
        concurrent_time = end_time - start_time
        
        # Performance assertions
        assert concurrent_time < 2.0, f"Concurrent deployment too slow: {concurrent_time}s"
        assert all(results), "Some deployments failed"
    
    @pytest.mark.benchmark
    def test_memory_optimization_performance(self, benchmark):
        """Benchmark memory optimization performance"""
        from claude_mpm.services.memory.optimizer import MemoryOptimizer
        
        optimizer = MemoryOptimizer()
        test_memory_content = "Test memory content " * 1000  # Large content
        
        # Benchmark the optimization
        result = benchmark(optimizer.optimize_memory_content, test_memory_content)
        
        assert result is not None
        assert len(result) <= len(test_memory_content)
```

## Security Testing

### Security Test Framework

```python
import pytest
from claude_mpm.validation.agent_validator import AgentValidator
from claude_mpm.utils.path_operations import PathOperations


class TestSecurity:
    """Security tests for input validation and protection"""
    
    def test_path_traversal_protection(self):
        """Test protection against path traversal attacks"""
        path_ops = PathOperations()
        
        # Test malicious paths
        malicious_paths = [
            "../../../etc/passwd",
            "..\\..\\windows\\system32",
            "/etc/passwd",
            "C:\\Windows\\System32",
            ".ssh/id_rsa"
        ]
        
        for malicious_path in malicious_paths:
            with pytest.raises(SecurityError):
                path_ops.validate_secure_path(malicious_path)
    
    def test_agent_config_injection_protection(self):
        """Test protection against configuration injection"""
        validator = AgentValidator()
        
        # Test injection attempts
        malicious_configs = [
            {"agent_id": "<script>alert('xss')</script>"},
            {"instructions": "'; DROP TABLE agents; --"},
            {"metadata": {"name": "{{7*7}}"}},  # Template injection
            {"agent_id": "../../malicious"}
        ]
        
        for config in malicious_configs:
            result = validator.validate_agent(config)
            assert not result.is_valid, f"Malicious config passed validation: {config}"
    
    def test_resource_limit_enforcement(self):
        """Test enforcement of resource limits"""
        validator = AgentValidator()
        
        # Test oversized inputs
        large_config = {
            "agent_id": "test",
            "instructions": "A" * (50_000 + 1),  # Exceeds limit
            "metadata": {
                "description": "B" * (1_000 + 1)  # Exceeds limit
            }
        }
        
        result = validator.validate_agent(large_config)
        assert not result.is_valid
        assert any("too large" in error.lower() for error in result.errors)
    
    @pytest.mark.parametrize("input_data,should_be_safe", [
        ("normal_agent_id", True),
        ("agent-with-dashes", True),
        ("agent_with_underscores", True),
        ("../malicious", False),
        ("agent/with/slashes", False),
        ("agent\\with\\backslashes", False),
        ("", False),
        ("a" * 100, False),  # Too long
    ])
    def test_agent_id_validation(self, input_data, should_be_safe):
        """Test agent ID validation security"""
        validator = AgentValidator()
        
        config = {
            "agent_id": input_data,
            "version": "1.0.0",
            "metadata": {"name": "Test", "description": "Test"},
            "instructions": "Test instructions"
        }
        
        result = validator.validate_agent(config)
        assert result.is_valid == should_be_safe
```

## Best Practices

### 1. Test Writing Best Practices

- **Descriptive Names**: Use clear, descriptive test names
- **Single Responsibility**: Each test should test one thing
- **Arrange-Act-Assert**: Structure tests with clear sections
- **Independent Tests**: Tests should not depend on each other
- **Deterministic Results**: Tests should have predictable outcomes

```python
def test_agent_deployment_success_with_valid_config():
    """Test that agent deployment succeeds with valid configuration"""
    # Arrange
    deployment_service = AgentDeploymentService()
    valid_config = create_valid_agent_config()
    
    # Act
    result = deployment_service.deploy_agent(valid_config)
    
    # Assert
    assert result.success is True
    assert result.agent_id == valid_config['agent_id']
```

### 2. Mock and Fixture Best Practices

- **Mock External Dependencies**: Mock file system, network, and database operations
- **Use Realistic Data**: Test data should resemble production data
- **Shared Fixtures**: Use fixtures for common test setup
- **Clean State**: Ensure each test starts with clean state

```python
@pytest.fixture
def agent_deployment_service():
    """Provide agent deployment service with mocked dependencies"""
    with patch('claude_mpm.services.agent.deployment.Path') as mock_path, \
         patch('claude_mpm.services.agent.deployment.FileSystem') as mock_fs:
        
        service = AgentDeploymentService()
        service._file_system = mock_fs.return_value
        yield service
```

### 3. Performance Testing Best Practices

- **Realistic Load**: Test with realistic data sizes and loads
- **Baseline Metrics**: Establish performance baselines
- **Regular Monitoring**: Run performance tests regularly
- **Environment Consistency**: Use consistent test environments

### 4. Security Testing Best Practices

- **Threat Modeling**: Base tests on threat model
- **Input Fuzzing**: Test with malformed and malicious inputs
- **Boundary Testing**: Test edge cases and limits
- **Regular Updates**: Update security tests as threats evolve

### 5. Test Maintenance Best Practices

- **Regular Review**: Review and update tests regularly
- **Refactor Tests**: Keep test code clean and maintainable
- **Document Test Intent**: Document complex test scenarios
- **Version Test Data**: Version control test data and fixtures

This testing guide provides comprehensive coverage of testing strategies and practices for Claude MPM. Regular testing ensures the framework maintains high quality, reliability, and security standards.