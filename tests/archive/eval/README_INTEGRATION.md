# Integration Testing Guide for DeepEval PM Evaluation

This guide explains how to use the real integration testing framework for evaluating PM agent responses against PM instructions.

## Overview

The integration testing framework supports three execution modes:

1. **Integration Mode**: Tests with real PM agent (captures actual responses)
2. **Replay Mode**: Tests with captured responses (no PM agent needed)
3. **Unit Mode**: Tests with mock responses (fast, no dependencies)

## Quick Start

### Run Integration Tests (with real PM agent)

```bash
# Run integration tests with response capture
pytest tests/eval/test_cases/integration_ticketing.py -m integration --capture-responses -v

# Set PM agent endpoint (if not localhost)
pytest tests/eval/test_cases/integration_ticketing.py -m integration \
  --pm-endpoint=http://pm-agent:8000 \
  --capture-responses -v
```

### Run Replay Tests (no PM agent needed)

```bash
# Run tests using captured responses
pytest tests/eval/test_cases/integration_ticketing.py --replay-mode -v

# Run regression tests specifically
pytest tests/eval/test_cases/integration_ticketing.py -m regression -v
```

### Run Unit Tests (fast, mock responses)

```bash
# Run unit tests only (excludes integration tests)
pytest tests/eval/test_cases/ -m "not integration" -v
```

### Run Performance Benchmarks

```bash
# Run performance tests
pytest tests/eval/test_cases/performance.py -m performance -v

# Generate performance report
pytest tests/eval/test_cases/performance.py -m performance -v --tb=short
```

## Architecture

### Directory Structure

```
tests/eval/
├── responses/              # Captured PM responses
│   ├── ticketing/         # Ticketing-related responses
│   ├── circuit_breakers/  # Circuit breaker test responses
│   └── performance/       # Performance test responses
├── golden_responses/       # Known-good baseline responses
│   ├── ticketing/
│   └── circuit_breakers/
├── test_cases/
│   ├── integration_ticketing.py      # Integration tests for ticketing
│   ├── ticketing_delegation.py       # Unit tests (existing)
│   ├── circuit_breakers.py           # Circuit breaker tests
│   └── performance.py                # Performance benchmarks
├── utils/
│   ├── pm_response_capture.py        # Response capture utilities
│   └── response_replay.py            # Replay and comparison utilities
├── conftest.py             # Pytest fixtures and configuration
└── README_INTEGRATION.md   # This file
```

### Response Capture Format

Captured responses are stored as JSON with metadata:

```json
{
  "scenario_id": "url_linear",
  "timestamp": "2025-12-05T17:30:00Z",
  "pm_version": "5.0.9",
  "input": "verify https://linear.app/1m-hyperdev/issue/JJF-62",
  "response": {
    "content": "I'll delegate to ticketing agent...",
    "tools_used": ["Task"],
    "delegations": [{"agent": "ticketing", "task": "..."}]
  },
  "metrics": {
    "ticketing_delegation": 1.0,
    "instruction_faithfulness": 0.95
  }
}
```

## Usage Examples

### Capture Responses from PM Agent

```python
import pytest
from tests.eval.utils.pm_response_capture import PMResponseCapture

@pytest.mark.integration
async def test_with_capture(pm_agent, pm_response_capture):
    """Test that captures PM response."""
    # Get PM response
    pm_response = await pm_agent.process_request(
        "Create ticket for authentication bug"
    )

    # Capture response
    captured = pm_response_capture.capture_response(
        scenario_id="auth_bug_ticket",
        input_text="Create ticket for authentication bug",
        pm_response=pm_response,
        category="ticketing"
    )

    # Response is saved to tests/eval/responses/ticketing/
    assert captured.metadata.scenario_id == "auth_bug_ticket"
```

### Compare with Golden Response

```python
from tests.eval.utils.response_replay import ResponseReplay

def test_regression(response_replay):
    """Test for regression against golden response."""
    # Load current response
    current = response_replay.capture.load_response(
        "auth_bug_ticket",
        category="ticketing"
    )

    # Compare with golden
    comparison = response_replay.compare_response(
        scenario_id="auth_bug_ticket",
        current_response=current,
        category="ticketing"
    )

    # Check for regression
    assert not comparison.regression_detected, (
        f"Regression: {comparison.differences}"
    )
    assert comparison.match_score >= 0.85
```

### Update Golden Responses

```bash
# Run tests and update golden responses for regressions
pytest tests/eval/test_cases/integration_ticketing.py --update-golden -v

# This will update golden responses when regression detected
```

### Use PM Test Helper

The `pm_test_helper` fixture provides a unified interface:

```python
@pytest.mark.integration
async def test_with_helper(pm_test_helper):
    """Test using helper fixture."""
    result = await pm_test_helper.run_test(
        scenario_id="create_ticket",
        input_text="Create ticket for bug",
        category="ticketing"
    )

    # Automatically handles:
    # - PM agent interaction (if integration mode)
    # - Response capture (if --capture-responses)
    # - Replay (if --replay-mode)
    # - Golden comparison
    # - Golden update (if --update-golden)

    if result.get("comparison"):
        assert not result["comparison"].regression_detected
```

## Configuration

### Environment Variables

```bash
# PM agent endpoint
export PM_AGENT_ENDPOINT=http://localhost:8000

# PM agent API key (if required)
export PM_AGENT_API_KEY=your_api_key_here

# Response directories
export EVAL_RESPONSES_DIR=tests/eval/responses/
export EVAL_GOLDEN_DIR=tests/eval/golden_responses/
```

### Command Line Options

```bash
# Capture responses during test run
--capture-responses

# Use replay mode (no PM agent)
--replay-mode

# Update golden responses
--update-golden

# Set PM endpoint
--pm-endpoint=http://localhost:8000

# Set API key
--pm-api-key=xxx
```

## Test Markers

Use pytest markers to organize tests:

```python
@pytest.mark.integration    # Requires PM agent
@pytest.mark.regression     # Regression test (uses replay)
@pytest.mark.performance    # Performance benchmark
@pytest.mark.capture_responses  # Should capture responses
```

### Run Specific Test Categories

```bash
# Integration tests only
pytest -m integration -v

# Regression tests only
pytest -m regression -v

# Performance tests only
pytest -m performance -v

# Exclude integration tests (fast unit tests)
pytest -m "not integration" -v
```

## Workflow Examples

### Scenario 1: Capture Initial Responses

```bash
# 1. Start PM agent (if not running)
# (Your PM agent setup here)

# 2. Run integration tests with capture
pytest tests/eval/test_cases/integration_ticketing.py \
  -m integration \
  --capture-responses \
  -v

# 3. Responses saved to tests/eval/responses/ticketing/
ls tests/eval/responses/ticketing/

# 4. Review captured responses
cat tests/eval/responses/ticketing/url_linear_*.json
```

### Scenario 2: Create Golden Responses

```bash
# 1. Capture responses (from Scenario 1)

# 2. Review responses to ensure they're correct
# (Manual review of JSON files)

# 3. Promote responses to golden
python -c "
from tests.eval.utils.response_replay import ResponseReplay
replay = ResponseReplay()
response = replay.capture.load_response('url_linear', 'ticketing')
replay.save_as_golden(response, 'ticketing')
"

# 4. Golden response saved to tests/eval/golden_responses/ticketing/
```

### Scenario 3: Regression Testing

```bash
# 1. Run tests in replay mode (uses golden responses)
pytest tests/eval/test_cases/integration_ticketing.py \
  -m regression \
  --replay-mode \
  -v

# 2. If regressions detected, investigate differences
# Check test output for comparison details

# 3. If new behavior is correct, update golden
pytest tests/eval/test_cases/integration_ticketing.py \
  --update-golden \
  -v
```

### Scenario 4: CI/CD Integration

```yaml
# .github/workflows/eval-tests.yml
name: Evaluation Tests

on: [push, pull_request]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run unit tests
        run: pytest tests/eval/test_cases/ -m "not integration" -v

  regression-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run regression tests
        run: pytest tests/eval/test_cases/ -m regression --replay-mode -v

  integration-tests:
    runs-on: ubuntu-latest
    if: github.event_name == 'schedule'  # Run nightly
    steps:
      - uses: actions/checkout@v3
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Start PM agent
        run: docker-compose up -d pm-agent
      - name: Run integration tests
        run: |
          pytest tests/eval/test_cases/ -m integration \
            --pm-endpoint=http://localhost:8000 \
            --capture-responses \
            -v
      - name: Upload captured responses
        uses: actions/upload-artifact@v3
        with:
          name: captured-responses
          path: tests/eval/responses/
```

## Performance Benchmarking

### Run Performance Tests

```bash
# Run all performance tests
pytest tests/eval/test_cases/performance.py -m performance -v

# Generate performance report
pytest tests/eval/test_cases/performance.py -m performance -v --tb=short

# View performance history
cat tests/eval/performance_history.json
```

### Performance Metrics Tracked

- **PM Response Time**: Simple and complex requests
- **Throughput**: Requests per second
- **Metric Evaluation Time**: Delegation and faithfulness metrics
- **Memory Usage**: Response capture overhead
- **Pipeline Performance**: End-to-end evaluation time

### Performance Thresholds

| Metric | Threshold | Category |
|--------|-----------|----------|
| PM Response (simple) | < 5000ms | PM Agent |
| PM Response (complex) | < 10000ms | PM Agent |
| Delegation Metric | < 100ms | Metrics |
| Instruction Faithfulness | < 200ms | Metrics |
| Full Pipeline | < 500ms | Metrics |

## Troubleshooting

### Issue: No PM agent available

**Solution**: Run tests in replay mode
```bash
pytest --replay-mode -v
```

### Issue: No captured responses found

**Solution**: Run integration tests with capture first
```bash
pytest -m integration --capture-responses -v
```

### Issue: Regression detected but behavior is correct

**Solution**: Update golden responses
```bash
pytest --update-golden -v
```

### Issue: PM agent connection timeout

**Solution**: Check endpoint and increase timeout
```bash
pytest --pm-endpoint=http://correct-host:8000 -v
```

### Issue: Performance regression detected

**Solution**: Review performance history
```bash
cat tests/eval/performance_history.json | jq '.[-5:]'  # Last 5 runs
```

## Best Practices

### 1. Capture Responses Incrementally

- Capture responses for new scenarios as you add them
- Don't try to capture all at once
- Review captured responses before promoting to golden

### 2. Use Replay Mode for Fast Feedback

- Replay mode is fast (no PM agent needed)
- Use for quick validation during development
- Run integration tests less frequently (nightly CI)

### 3. Keep Golden Responses Up to Date

- Review golden responses regularly
- Update when PM behavior legitimately changes
- Document why golden responses changed (git commit message)

### 4. Monitor Performance Trends

- Run performance tests regularly
- Track metrics over time
- Set up alerts for performance regressions

### 5. Test Coverage Strategy

```
Unit Tests (80%)          → Fast feedback, mock responses
Replay Tests (15%)        → Regression detection, no PM agent
Integration Tests (5%)    → Real PM validation, nightly CI
Performance Tests (Ad-hoc) → Benchmark before releases
```

## Advanced Usage

### Custom Response Redaction

```python
from tests.eval.utils.pm_response_capture import PMResponseCapture

def custom_redact(text: str) -> str:
    """Custom PII redaction."""
    # Your redaction logic
    return text.replace("sensitive", "[REDACTED]")

capture = PMResponseCapture(redact_pii=True)
response = capture.capture_response(
    scenario_id="test",
    input_text="input",
    pm_response={"content": "sensitive data"},
    category="general",
    redact_fn=custom_redact
)
```

### Golden Response Approval Workflow

```python
from tests.eval.utils.response_replay import GoldenResponseManager

manager = GoldenResponseManager()

# Propose new golden
manager.propose_golden(
    response=response,
    category="ticketing",
    reason="PM behavior improved delegation clarity"
)

# List pending proposals
pending = manager.list_pending()
for scenario_id, proposal in pending:
    print(f"{scenario_id}: {proposal['reason']}")

# Approve proposal
manager.approve_pending("url_linear")

# Or reject
manager.reject_pending("url_linear")
```

### Response Cleanup

```python
from tests.eval.utils.response_replay import ResponseReplay

replay = ResponseReplay()

# Remove responses older than 30 days
replay.cleanup_old_responses(
    category="ticketing",
    days_to_keep=30
)
```

## Contributing

When adding new integration tests:

1. **Add test scenario** to `scenarios/ticketing_scenarios.json`
2. **Create integration test** in `test_cases/integration_ticketing.py`
3. **Run with capture** to create initial responses
4. **Review responses** to ensure correctness
5. **Promote to golden** if baseline behavior
6. **Add regression test** to verify behavior stays consistent

## Support

For issues or questions:
- Check troubleshooting section above
- Review test output for detailed error messages
- Check `tests/eval/performance_report.txt` for performance issues
- Review captured responses in `tests/eval/responses/`

## Summary

The integration testing framework provides:

✅ Real PM agent testing capability
✅ Response capture and replay for CI/CD
✅ Golden response regression detection
✅ Performance benchmarking and tracking
✅ Flexible test execution modes
✅ Comprehensive documentation and examples

Use integration mode to validate real PM behavior, replay mode for fast regression testing, and performance tests to track metrics over time.
