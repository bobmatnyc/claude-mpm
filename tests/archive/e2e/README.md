# E2E Tests for Claude MPM Agent System

This directory contains comprehensive end-to-end tests for the Claude MPM agent system.

## Overview

The E2E tests validate the complete agent system lifecycle including:
- Agent discovery and loading
- Multi-agent deployment and interactions
- Real file operations (not mocked)
- Performance under concurrent operations
- Integration with the hook system

## Test Suite Contents

### `test_agent_system_e2e.py`

Contains the following test scenarios:

1. **`test_agent_discovery_and_loading`** ✅
   - Tests agent discovery from template directory
   - Validates schema validation during loading
   - Verifies registry population
   - Tests error handling for invalid agents

2. **`test_agent_prompt_caching_and_performance`**
   - Tests cache miss on first access
   - Validates cache hit on subsequent access
   - Tests force reload functionality
   - Measures performance improvement with caching

3. **`test_multi_agent_deployment_lifecycle`**
   - Tests agent template to YAML conversion
   - Validates deployment to .claude/agents directory
   - Tests version tracking and updates
   - Verifies cleanup operations

4. **`test_concurrent_agent_operations`**
   - Tests thread safety of agent loading
   - Validates cache consistency under concurrent access
   - Measures performance under parallel operations
   - Ensures no race conditions or deadlocks

5. **`test_agent_lifecycle_manager_integration`** (Skipped - missing dependencies)
   - Tests agent versioning and updates
   - Validates migration between versions
   - Tests rollback capabilities
   - Ensures state consistency

6. **`test_agent_discovery_service_integration`**
   - Tests discovery of deployed agents
   - Validates agent metadata extraction
   - Tests filtering and search capabilities
   - Measures performance with many agents

7. **`test_error_handling_and_recovery`**
   - Tests graceful handling of corrupted agents
   - Validates recovery from partial deployments
   - Ensures proper error logging
   - Tests system stability under errors

8. **`test_agent_handoff_simulation`**
   - Simulates multi-agent workflow patterns
   - Tests state preservation during handoffs
   - Measures performance of multi-agent workflows
   - Validates agent communication patterns

9. **`test_memory_and_resource_usage`**
   - Tests memory efficiency with many agents
   - Validates cache memory management
   - Tests resource cleanup
   - Important for production deployments

10. **`test_production_readiness_checks`**
    - Tests system stability over time
    - Validates error recovery mechanisms
    - Tests performance consistency
    - Ensures logging and monitoring work correctly

11. **`test_hook_system_integration`**
    - Tests integration between agent system and hook system
    - Validates hook system can discover deployed agents
    - Tests agent commands work through hooks
    - Measures performance impact of hook integration

## Running the Tests

### Run all E2E tests:
```bash
python -m pytest tests/e2e/test_agent_system_e2e.py -v
```

### Run a specific test:
```bash
python -m pytest tests/e2e/test_agent_system_e2e.py::TestAgentSystemE2E::test_agent_discovery_and_loading -v
```

### Run with detailed output:
```bash
python -m pytest tests/e2e/test_agent_system_e2e.py -v -s
```

## Test Design Principles

1. **No Mocking**: Tests use real file operations to catch actual I/O issues
2. **Isolation**: Each test creates its own temporary environment
3. **Performance Validation**: Includes concurrent operation tests
4. **Full Lifecycle Coverage**: Tests complete workflows from discovery to cleanup

## Known Issues

Some tests may fail due to:
- Missing dependencies (e.g., AgentLifecycleManager requires agent_persistence_service)
- Schema validation requirements changing
- Environment-specific issues

## Metrics Tracked

The tests collect various performance metrics:
- Agent discovery and loading times
- Cache hit rates during operations
- Memory usage patterns
- Concurrent operation performance
- Error rates and types

These metrics help identify performance bottlenecks and optimization opportunities.

## Future Improvements

1. Add tests for agent hot-reloading
2. Test agent system under resource constraints
3. Add tests for agent system monitoring/observability
4. Test disaster recovery scenarios
5. Add performance benchmarks with baseline comparisons