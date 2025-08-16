# Memory Guardian Test Suite Documentation

This document provides comprehensive documentation for the Memory Guardian test suite, including test overview, running instructions, performance baselines, and CI/CD integration guidelines.

## Table of Contents

1. [Test Suite Overview](#test-suite-overview)
2. [Test Categories](#test-categories)
3. [Running Tests](#running-tests)
4. [Performance Baselines](#performance-baselines)
5. [Test Configuration](#test-configuration)
6. [CI/CD Integration](#cicd-integration)
7. [Troubleshooting](#troubleshooting)
8. [Contributing](#contributing)

## Test Suite Overview

The Memory Guardian test suite provides comprehensive validation of the Memory Guardian System functionality, ensuring robust memory monitoring, process lifecycle management, and system resilience under various conditions.

### Key Features

- **Comprehensive Coverage**: Unit, integration, E2E, performance, and stress testing
- **Real Subprocess Testing**: Actual process monitoring with memory growth simulation
- **Platform Support**: Cross-platform testing for macOS, Linux, and Windows
- **Performance Benchmarking**: Detailed performance analysis and baseline tracking
- **Stress Testing**: System behavior under extreme conditions
- **Automated Reporting**: Coverage reports, performance metrics, and test summaries

### Test Statistics

| Test Category | Test Count | Coverage | Avg Duration |
|---------------|------------|----------|--------------|
| Unit Tests | 25+ | 90%+ | 2-5 minutes |
| Integration Tests | 15+ | 85%+ | 5-10 minutes |
| E2E Tests | 10+ | 80%+ | 10-15 minutes |
| Performance Tests | 12+ | N/A | 15-30 minutes |
| Stress Tests | 8+ | N/A | 20-45 minutes |

## Test Categories

### 1. Unit Tests (`tests/services/infrastructure/test_memory_guardian.py`)

**Purpose**: Test individual components and methods in isolation.

**Key Test Areas**:
- Memory Guardian initialization and configuration
- Process lifecycle management (start, stop, restart)
- Memory monitoring and threshold detection
- Restart policy enforcement and cooldown logic
- State persistence and restoration
- Platform-specific memory monitoring

**Example Tests**:
```python
def test_memory_guardian_initialization()
def test_process_start_and_stop()
def test_memory_threshold_detection()
def test_restart_policy_enforcement()
def test_state_persistence()
```

### 2. Integration Tests (`tests/integration/test_memory_guardian_integration.py`)

**Purpose**: Test complete system integration and component interactions.

**Key Test Areas**:
- Full lifecycle testing (start → monitor → breach → restart → restore)
- State preservation across restarts
- Restart loop protection and circuit breaker behavior
- Memory leak detection and automated response
- Graceful degradation under system stress
- Health monitoring integration
- Safety service coordination

**Example Tests**:
```python
def test_complete_lifecycle_normal_operation()
def test_memory_threshold_escalation_lifecycle()
def test_restart_with_state_preservation()
def test_restart_loop_protection_circuit_breaker()
def test_memory_leak_detection_and_response()
```

### 3. End-to-End Tests (`tests/e2e/test_memory_guardian_e2e.py`)

**Purpose**: Test real-world scenarios with actual subprocess execution.

**Key Test Areas**:
- Real subprocess monitoring with actual memory growth
- CLI command execution and integration
- Configuration file loading and validation
- Experimental feature handling
- Interrupt handling and graceful shutdown
- Process crash recovery
- Large conversation file simulation

**Example Tests**:
```python
def test_real_subprocess_memory_monitoring()
def test_cli_command_execution()
def test_process_crash_recovery()
def test_large_state_file_handling()
def test_claude_conversation_simulation()
```

### 4. Performance Tests (`tests/performance/test_memory_guardian_perf.py`)

**Purpose**: Measure and validate system performance characteristics.

**Key Test Areas**:
- Memory monitoring overhead measurement
- State serialization/deserialization performance
- Restart cycle timing analysis
- Resource usage profiling
- Scalability testing with multiple instances
- Memory leak detection algorithm performance
- Dashboard metrics collection efficiency

**Example Tests**:
```python
def test_monitoring_overhead_detailed()
def test_state_serialization_performance_comprehensive()
def test_restart_cycle_performance_analysis()
def test_scalability_multiple_instances()
```

### 5. Stress Tests (`tests/stress/test_memory_guardian_stress.py`)

**Purpose**: Validate system behavior under extreme conditions.

**Key Test Areas**:
- Rapid memory growth scenarios
- Memory thrashing simulation
- Concurrent restart storm testing
- Large state file handling under pressure
- Extended monitoring endurance testing
- Resource exhaustion scenarios
- High-frequency event processing
- Chaos engineering scenarios

**Example Tests**:
```python
def test_rapid_memory_growth_stress()
def test_memory_thrashing_stress()
def test_concurrent_restart_storm()
def test_extended_monitoring_endurance()
def test_resource_exhaustion_scenarios()
```

### 6. Test Fixtures (`tests/fixtures/memory_guardian_fixtures.py`)

**Purpose**: Provide reusable test components and utilities.

**Key Components**:
- Mock Claude process simulators
- Memory growth pattern generators
- State data generators (small to huge)
- Configuration builders for various scenarios
- Platform-specific command mocks
- Performance measurement utilities

## Running Tests

### Prerequisites

1. **Python Environment**: Python 3.8+ with claude-mpm installed
2. **Dependencies**: Install test dependencies
   ```bash
   pip install pytest pytest-asyncio pytest-cov pytest-xdist psutil
   ```
3. **System Resources**: At least 2GB RAM and 1GB free disk space
4. **Permissions**: Ability to create and terminate processes

### Quick Start

Run the complete test suite:
```bash
./scripts/test_memory_guardian_suite.sh
```

### Running Specific Test Categories

#### Unit Tests Only
```bash
./scripts/test_memory_guardian_suite.sh --unit-only
```

#### Integration Tests Only
```bash
./scripts/test_memory_guardian_suite.sh --integration-only
```

#### E2E Tests Only
```bash
./scripts/test_memory_guardian_suite.sh --e2e-only
```

#### Performance Tests Only
```bash
./scripts/test_memory_guardian_suite.sh --performance-only
```

#### Stress Tests Only
```bash
./scripts/test_memory_guardian_suite.sh --stress-only
```

### Advanced Options

#### Verbose Output
```bash
./scripts/test_memory_guardian_suite.sh --verbose
```

#### Parallel Execution
```bash
./scripts/test_memory_guardian_suite.sh --parallel 8
```

#### Custom Timeout
```bash
./scripts/test_memory_guardian_suite.sh --timeout 7200  # 2 hours
```

#### Skip Coverage
```bash
./scripts/test_memory_guardian_suite.sh --no-coverage
```

### Manual Test Execution

For development and debugging, you can run tests manually:

```bash
# Unit tests
pytest tests/services/infrastructure/test_memory_guardian.py -v

# Integration tests with coverage
pytest tests/integration/test_memory_guardian_integration.py --cov=claude_mpm.services.infrastructure.memory_guardian -v

# E2E tests
pytest tests/e2e/test_memory_guardian_e2e.py -v -s

# Performance tests (single-threaded)
pytest tests/performance/test_memory_guardian_perf.py -n 1 -v

# Stress tests with timeout
pytest tests/stress/test_memory_guardian_stress.py -n 1 --timeout=3600 -v
```

## Performance Baselines

### System Requirements

**Minimum System Requirements**:
- CPU: 2 cores, 2.0 GHz
- RAM: 4GB
- Disk: 2GB free space
- OS: macOS 10.15+, Ubuntu 18.04+, Windows 10+

**Recommended System Requirements**:
- CPU: 4+ cores, 2.5+ GHz
- RAM: 8GB+
- Disk: 5GB+ free space
- SSD storage for optimal performance

### Performance Baselines

#### Memory Monitoring Overhead

| Monitoring Frequency | CPU Overhead | Memory Overhead | Per-Check Time |
|---------------------|--------------|-----------------|----------------|
| 10s intervals | < 1% | < 5MB | < 1ms |
| 1s intervals | < 3% | < 10MB | < 2ms |
| 0.1s intervals | < 10% | < 20MB | < 5ms |
| 0.01s intervals | < 25% | < 50MB | < 10ms |

#### State Serialization Performance

| State Size | Serialize Time | Deserialize Time | Throughput |
|------------|---------------|------------------|------------|
| Small (1KB) | < 1ms | < 1ms | > 1000 MB/s |
| Medium (100KB) | < 10ms | < 15ms | > 100 MB/s |
| Large (10MB) | < 500ms | < 750ms | > 20 MB/s |
| Huge (50MB) | < 3s | < 5s | > 15 MB/s |

#### Restart Cycle Performance

| Scenario | Restart Time | Success Rate | Recovery Time |
|----------|-------------|--------------|---------------|
| Immediate | < 1s | > 95% | < 2s |
| Normal (1s delay) | < 5s | > 98% | < 10s |
| Graceful (5s timeout) | < 15s | > 99% | < 30s |

#### Scalability Benchmarks

| Concurrent Instances | CPU Usage | Memory Usage | Performance Impact |
|---------------------|-----------|--------------|-------------------|
| 1 instance | Baseline | Baseline | Baseline |
| 5 instances | < 3x | < 5x | < 10% degradation |
| 10 instances | < 6x | < 10x | < 25% degradation |
| 20 instances | < 12x | < 20x | < 50% degradation |

### Platform-Specific Performance

#### macOS Performance

- **Memory Monitoring**: ps command, ~1-2ms per check
- **Process Control**: SIGTERM/SIGKILL, ~100-200ms
- **Expected Overhead**: 5-10% CPU, 10-20MB RAM

#### Linux Performance

- **Memory Monitoring**: /proc filesystem, ~0.5-1ms per check
- **Process Control**: signals, ~50-100ms
- **Expected Overhead**: 3-8% CPU, 8-15MB RAM

#### Windows Performance

- **Memory Monitoring**: tasklist/WMI, ~2-5ms per check
- **Process Control**: taskkill, ~200-500ms
- **Expected Overhead**: 8-15% CPU, 15-30MB RAM

## Test Configuration

### Environment Variables

Configure test behavior with environment variables:

```bash
# Test execution
export MEMORY_GUARDIAN_TEST_TIMEOUT=3600        # Overall test timeout
export MEMORY_GUARDIAN_TEST_PARALLEL=4          # Parallel job count
export MEMORY_GUARDIAN_TEST_VERBOSE=true        # Verbose output

# Test behavior
export MEMORY_GUARDIAN_TEST_SKIP_STRESS=false   # Skip stress tests
export MEMORY_GUARDIAN_TEST_SKIP_E2E=false      # Skip E2E tests
export MEMORY_GUARDIAN_TEST_QUICK_MODE=false    # Reduced test scope

# Performance tuning
export MEMORY_GUARDIAN_TEST_MIN_MEMORY=1024     # Minimum memory (MB)
export MEMORY_GUARDIAN_TEST_MAX_DURATION=1800   # Max test duration per suite
```

### Configuration Files

#### Custom Test Configuration

Create `tests/config/test_config.yaml`:
```yaml
memory_guardian_tests:
  timeouts:
    unit: 300
    integration: 600
    e2e: 900
    performance: 1800
    stress: 3600
  
  thresholds:
    cpu_usage_max: 25.0
    memory_usage_max: 100.0
    restart_time_max: 10.0
  
  parallel:
    unit: 4
    integration: 2
    e2e: 1
    performance: 1
    stress: 1
  
  coverage:
    minimum: 85.0
    target: 90.0
```

#### Platform-Specific Settings

Create `tests/config/platform_config.yaml`:
```yaml
platforms:
  Darwin:  # macOS
    memory_check_interval: 0.1
    process_timeout: 5
    expected_overhead: 10.0
  
  Linux:
    memory_check_interval: 0.05
    process_timeout: 3
    expected_overhead: 8.0
  
  Windows:
    memory_check_interval: 0.2
    process_timeout: 10
    expected_overhead: 15.0
```

## CI/CD Integration

### GitHub Actions

Add to `.github/workflows/memory-guardian-tests.yml`:

```yaml
name: Memory Guardian Tests

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  memory-guardian-tests:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
        python-version: [3.8, 3.9, '3.10', 3.11]
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -e .
        pip install pytest pytest-asyncio pytest-cov pytest-xdist psutil
    
    - name: Run Memory Guardian Tests
      run: |
        chmod +x scripts/test_memory_guardian_suite.sh
        ./scripts/test_memory_guardian_suite.sh --no-stress --timeout 1800
    
    - name: Upload coverage reports
      uses: codecov/codecov-action@v3
      with:
        file: test-results/*/coverage/coverage_*.xml
    
    - name: Upload test results
      uses: actions/upload-artifact@v3
      if: always()
      with:
        name: test-results-${{ matrix.os }}-${{ matrix.python-version }}
        path: test-results/
```

### Jenkins Pipeline

Add to `Jenkinsfile`:

```groovy
pipeline {
    agent any
    
    environment {
        MEMORY_GUARDIAN_TEST_TIMEOUT = '3600'
        MEMORY_GUARDIAN_TEST_PARALLEL = '4'
    }
    
    stages {
        stage('Setup') {
            steps {
                sh 'python -m pip install -e .'
                sh 'pip install pytest pytest-asyncio pytest-cov pytest-xdist psutil'
            }
        }
        
        stage('Memory Guardian Tests') {
            parallel {
                stage('Unit & Integration') {
                    steps {
                        sh './scripts/test_memory_guardian_suite.sh --unit-only --integration-only'
                    }
                }
                stage('E2E Tests') {
                    steps {
                        sh './scripts/test_memory_guardian_suite.sh --e2e-only'
                    }
                }
                stage('Performance Tests') {
                    steps {
                        sh './scripts/test_memory_guardian_suite.sh --performance-only'
                    }
                }
            }
        }
        
        stage('Stress Tests') {
            when {
                branch 'main'
            }
            steps {
                sh './scripts/test_memory_guardian_suite.sh --stress-only --timeout 7200'
            }
        }
    }
    
    post {
        always {
            publishTestResults(
                testResultsPattern: 'test-results/**/*.xml',
                allowEmptyResults: true
            )
            publishHTML([
                allowMissing: false,
                alwaysLinkToLastBuild: true,
                keepAll: true,
                reportDir: 'test-results/',
                reportFiles: '*/test_summary.md',
                reportName: 'Memory Guardian Test Report'
            ])
        }
        failure {
            emailext (
                subject: "Memory Guardian Tests Failed: ${env.JOB_NAME} - ${env.BUILD_NUMBER}",
                body: "Memory Guardian tests failed. Check the build logs for details.",
                to: "${env.CHANGE_AUTHOR_EMAIL}"
            )
        }
    }
}
```

### Docker Testing

Create `tests/docker/Dockerfile.test`:

```dockerfile
FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .
COPY tests/requirements-test.txt .

# Install Python dependencies
RUN pip install -r requirements.txt
RUN pip install -r requirements-test.txt

# Copy source code
COPY src/ src/
COPY tests/ tests/
COPY scripts/ scripts/

# Install package
RUN pip install -e .

# Set environment variables
ENV MEMORY_GUARDIAN_TEST_TIMEOUT=1800
ENV MEMORY_GUARDIAN_TEST_PARALLEL=2

# Run tests
CMD ["./scripts/test_memory_guardian_suite.sh", "--no-stress"]
```

Run Docker tests:
```bash
docker build -f tests/docker/Dockerfile.test -t memory-guardian-tests .
docker run --rm -v $(pwd)/test-results:/app/test-results memory-guardian-tests
```

## Troubleshooting

### Common Issues

#### 1. Tests Timeout

**Symptoms**: Tests hang or timeout
**Solutions**:
- Increase timeout: `--timeout 7200`
- Run single-threaded: `--parallel 1`
- Check system resources
- Skip problematic tests temporarily

#### 2. Memory Tests Fail

**Symptoms**: Memory monitoring tests fail
**Solutions**:
- Check process permissions
- Verify psutil installation
- Run on supported platform
- Check available memory

#### 3. Process Creation Fails

**Symptoms**: Subprocess tests fail to start
**Solutions**:
- Check Python path
- Verify script permissions
- Check available process slots
- Review system limits

#### 4. Coverage Collection Fails

**Symptoms**: Coverage reports missing or incomplete
**Solutions**:
- Install pytest-cov
- Check file permissions
- Verify coverage configuration
- Run with `--no-coverage` temporarily

### Debug Mode

Run tests in debug mode:
```bash
# Enable debug logging
export MEMORY_GUARDIAN_DEBUG=true

# Run with verbose output and no parallel execution
./scripts/test_memory_guardian_suite.sh --verbose --parallel 1

# Run specific failing test
pytest tests/integration/test_memory_guardian_integration.py::TestMemoryGuardianLifecycle::test_complete_lifecycle_normal_operation -v -s --pdb
```

### Performance Issues

#### Slow Test Execution

**Causes**:
- Insufficient system resources
- High parallel job count
- Large state file generation
- Network/disk I/O bottlenecks

**Solutions**:
- Reduce parallel jobs: `--parallel 2`
- Skip stress tests: `--no-stress`
- Use faster storage (SSD)
- Close unnecessary applications

#### High Resource Usage

**Causes**:
- Memory leaks in tests
- Too many concurrent processes
- Large test data generation

**Solutions**:
- Monitor with `top`/`htop`
- Run garbage collection explicitly
- Limit test scope
- Use smaller test data sets

### Platform-Specific Issues

#### macOS

- **Issue**: Permission denied for process monitoring
- **Solution**: Run with appropriate permissions or disable SIP temporarily

#### Linux

- **Issue**: `/proc` filesystem access denied
- **Solution**: Check container permissions or user privileges

#### Windows

- **Issue**: Process termination failures
- **Solution**: Run as administrator or adjust security settings

## Contributing

### Adding New Tests

1. **Choose Test Category**: Determine if test belongs in unit, integration, E2E, performance, or stress
2. **Use Fixtures**: Leverage existing fixtures from `tests/fixtures/memory_guardian_fixtures.py`
3. **Follow Patterns**: Use existing test patterns and naming conventions
4. **Add Documentation**: Document test purpose, setup, and expected behavior
5. **Update Baselines**: Update performance baselines if adding performance tests

### Test Development Guidelines

#### Test Naming
```python
# Good: descriptive and specific
def test_memory_guardian_handles_rapid_growth_with_restart()

# Bad: vague and generic
def test_memory_stuff()
```

#### Test Structure
```python
async def test_example():
    # Arrange: Set up test conditions
    config = ConfigurationBuilder.stress_test_config(workspace)
    guardian = MemoryGuardian(config)
    
    # Act: Perform the action being tested
    await guardian.initialize()
    result = await guardian.start_process()
    
    # Assert: Verify expected outcomes
    assert result is True
    assert guardian.process_state == ProcessState.RUNNING
    
    # Cleanup: Ensure proper cleanup
    await guardian.shutdown()
```

#### Async Test Patterns
```python
@pytest.mark.asyncio
async def test_async_behavior():
    # Use async/await for all async operations
    guardian = MemoryGuardian(config)
    await guardian.initialize()
    
    try:
        # Test async behavior
        result = await guardian.restart_process("test")
        assert result
    finally:
        # Always cleanup in finally block
        await guardian.shutdown()
```

### Performance Test Guidelines

#### Measurement Consistency
```python
def test_performance():
    profiler = PerformanceProfiler()
    
    # Set baseline before test
    profiler.set_baseline()
    
    # Measure specific operation
    profiler.start_measurement('operation')
    # ... perform operation ...
    results = profiler.end_measurement('operation')
    
    # Assert performance expectations
    assert results['duration'] < 1.0  # 1 second max
    assert results['memory_delta'] < 10 * 1024 * 1024  # 10MB max
```

#### Baseline Updates

When performance characteristics change:

1. **Measure Impact**: Run performance tests before and after changes
2. **Document Changes**: Explain why baselines changed
3. **Update Documentation**: Update baseline tables in this README
4. **Review Impact**: Ensure changes don't negatively impact users

### Test Data Management

#### State Data Size Guidelines

- **Small**: < 1KB (fast unit tests)
- **Medium**: 100KB - 1MB (integration tests)
- **Large**: 10MB - 50MB (E2E tests)
- **Huge**: 50MB+ (stress tests only)

#### Cleanup Requirements

All tests must properly clean up:
- Terminate started processes
- Remove temporary files
- Close open file handles
- Release allocated memory

### Review Checklist

Before submitting test changes:

- [ ] Tests pass on local machine
- [ ] Tests follow naming conventions
- [ ] Proper async/await usage
- [ ] Appropriate test category
- [ ] Cleanup in finally blocks
- [ ] Performance baselines updated if needed
- [ ] Documentation updated
- [ ] No hardcoded paths or values
- [ ] Cross-platform compatibility considered
- [ ] Resource usage is reasonable

---

For additional support or questions about the Memory Guardian test suite, please refer to the project documentation or open an issue in the project repository.