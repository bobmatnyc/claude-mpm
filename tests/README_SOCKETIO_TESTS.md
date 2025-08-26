# Socket.IO System Tests

Comprehensive test suite for the Claude MPM Socket.IO real-time event system.

## Test Coverage

### Python Tests

#### 1. Unit Tests - `test_socketio_service.py`
Tests the Socket.IO service singleton pattern and core functionality:
- **Singleton Pattern**: Ensures only one server instance exists globally
- **Server Lifecycle**: Start, stop, restart operations
- **Event Broadcasting**: Multi-namespace event distribution
- **Connection Pooling**: Efficient connection management
- **Thread Safety**: Concurrent operation safety
- **Error Handling**: Graceful error recovery

#### 2. Daemon Tests - `test_socketio_daemon.py`
Tests the daemon process management:
- **Process Management**: Start, stop, restart daemon processes
- **Port Management**: Dynamic port selection and binding
- **PID File Management**: Process tracking and cleanup
- **Signal Handling**: SIGTERM and SIGINT handling
- **Python Environment**: Virtual environment detection

#### 3. Integration Tests - `test_socketio_integration.py`
End-to-end testing of the complete system:
- **Event Flow**: Hook → Server → Dashboard
- **Multiple Clients**: Concurrent connections
- **Event Ordering**: Delivery guarantees
- **Performance**: Load testing and metrics
- **Graceful Degradation**: Failure recovery

### JavaScript Tests

#### Dashboard Client Tests - `dashboard/test_socket_client.js`
Tests the browser-side Socket.IO client:
- **Connection Management**: Connect, disconnect, reconnect
- **Event Queuing**: Offline event buffering
- **Event Handlers**: Registration and invocation
- **Error Handling**: Network error recovery
- **Retry Logic**: Exponential backoff implementation

## Running the Tests

### Python Tests

```bash
# Run all Socket.IO tests
pytest tests/test_socketio_service.py tests/test_socketio_daemon.py -v

# Run with coverage
pytest tests/test_socketio_service.py tests/test_socketio_daemon.py --cov=claude_mpm.services.socketio --cov-report=html

# Run integration tests (requires socketio package)
pytest tests/integration/test_socketio_integration.py -v

# Run specific test class
pytest tests/test_socketio_service.py::TestServerLifecycle -v

# Run with parallel execution
pytest tests/test_socketio_*.py -n auto
```

### JavaScript Tests

```bash
# Navigate to test directory
cd tests/dashboard

# Install dependencies (first time only)
npm install

# Run all tests
npm test

# Run with watch mode for development
npm run test:watch

# Run with coverage report
npm run test:coverage

# Run specific test file
npx jest test_socket_client.js
```

## Test Environment Setup

### Python Requirements
```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-cov pytest-mock

# For integration tests
pip install python-socketio aiohttp
```

### JavaScript Requirements
```bash
# Install Node.js and npm first, then:
cd tests/dashboard
npm install
```

## Key Test Scenarios

### 1. Singleton Pattern Verification
Ensures that multiple calls to `get_socketio_server()` return the same instance, preventing port conflicts:
```python
def test_singleton_pattern_enforcement():
    server1 = get_socketio_server()
    server2 = get_socketio_server()
    assert server1 is server2
```

### 2. Thread Safety Testing
Verifies safe concurrent operations:
```python
def test_concurrent_event_processing():
    # Multiple threads broadcast events simultaneously
    # Ensures no data corruption or race conditions
```

### 3. Event Buffering
Tests that events are buffered when clients disconnect:
```python
def test_event_buffer_overflow_handling():
    # Events buffered when no clients connected
    # Old events dropped when buffer full
```

### 4. Retry Mechanism
JavaScript client retry with exponential backoff:
```javascript
test('should retry with exponential backoff', () => {
    // First retry: 1000ms
    // Second retry: 2000ms
    // Third retry: 3000ms
    // etc.
});
```

### 5. Connection Health Monitoring
Tests connection health checks and cleanup:
```python
async def test_connection_health_monitoring():
    # Dead connections detected and removed
    # Prevents resource leaks
```

## Performance Benchmarks

The tests include performance assertions:
- **Event Throughput**: >50 events/second minimum
- **Delivery Rate**: >95% event delivery under load
- **Memory Stability**: <10,000 object growth under stress
- **Connection Limit**: Graceful handling at capacity

## Mocking Strategy

### Python Tests
- Uses `unittest.mock` for system calls
- Mocks `os.fork()`, `os.kill()` for safe daemon testing
- Mocks network operations for unit tests
- Real servers for integration tests on non-standard ports

### JavaScript Tests
- Mocks Socket.IO library (`window.io`)
- Mocks browser globals (localStorage, WebSocket)
- Uses Jest fake timers for retry logic testing
- Mocks console to reduce test output noise

## Debugging Failed Tests

### Enable Verbose Output
```bash
# Python
pytest tests/test_socketio_service.py -vvs

# JavaScript
npx jest --verbose --no-coverage
```

### Run Single Test
```bash
# Python
pytest tests/test_socketio_service.py::TestServerLifecycle::test_server_start_sync -vvs

# JavaScript
npx jest -t "should establish connection to specified port"
```

### Check Test Isolation
```bash
# Run tests in random order to detect dependencies
pytest tests/test_socketio_*.py --random-order

# JavaScript
npx jest --randomize
```

## CI/CD Integration

### GitHub Actions Example
```yaml
- name: Run Socket.IO Tests
  run: |
    # Python tests
    pytest tests/test_socketio_*.py --cov=claude_mpm.services.socketio
    
    # JavaScript tests
    cd tests/dashboard
    npm ci
    npm test
```

## Test Maintenance

### Adding New Tests
1. Follow existing test structure and naming conventions
2. Include WHY comments explaining test importance
3. Use appropriate fixtures for test isolation
4. Mock external dependencies appropriately
5. Add performance assertions where relevant

### Updating Tests
When Socket.IO implementation changes:
1. Update mock objects to match new interfaces
2. Verify integration tests still pass
3. Update performance benchmarks if needed
4. Document breaking changes in test comments

## Coverage Goals

- **Unit Tests**: 85%+ coverage of Socket.IO modules
- **Integration Tests**: Cover all major event flows
- **Performance Tests**: Validate under 3x expected load
- **Error Paths**: Test all error handling branches

## Known Issues and Limitations

1. **Port Conflicts**: Integration tests use ports 18765-18775 to avoid conflicts
2. **Async Timing**: Some tests use `asyncio.sleep()` for event propagation
3. **Mock Limitations**: Real Socket.IO behavior may differ from mocks
4. **Platform Differences**: Signal handling tests may behave differently on Windows

## Contributing

When adding Socket.IO features:
1. Write tests FIRST (TDD approach)
2. Ensure all existing tests pass
3. Add integration tests for new event types
4. Update this documentation
5. Run full test suite before committing