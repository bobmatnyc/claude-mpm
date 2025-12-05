# DeepEval Framework for Claude MPM Evaluation

Automated evaluation system for testing PM agent instruction compliance using DeepEval.

## Overview

This framework provides comprehensive testing for PM agent behavior, focusing on:

- **Ticketing Delegation**: Circuit Breaker #6 compliance (MUST delegate to ticketing agent)
- **Circuit Breaker Violations**: All 7 circuit breakers from PM instructions
- **Instruction Faithfulness**: Overall PM instruction compliance scoring
- **Delegation Correctness**: Proper agent routing and task delegation

## Directory Structure

```
tests/eval/
├── __init__.py              # Package initialization
├── conftest.py              # Pytest fixtures and test configuration
├── README.md                # This file
├── test_cases/              # Test case definitions
│   ├── __init__.py
│   ├── ticketing_delegation.py    # Ticketing delegation tests
│   └── circuit_breakers.py        # Circuit breaker violation tests
├── metrics/                 # Custom DeepEval metrics
│   ├── __init__.py
│   ├── instruction_faithfulness.py    # Instruction compliance metric
│   └── delegation_correctness.py      # Delegation quality metric
├── scenarios/               # Test scenario data (JSON)
│   ├── __init__.py
│   ├── ticketing_scenarios.json       # Ticketing test cases
│   └── circuit_breaker_scenarios.json # Circuit breaker test cases
└── utils/                   # Helper utilities
    ├── __init__.py
    └── pm_response_parser.py          # PM response analysis
```

## Installation

### Install Evaluation Dependencies

```bash
# Install evaluation extras
pip install -e ".[eval]"

# Or with uv
uv pip install -e ".[eval]"
```

### Required Dependencies

- `deepeval>=1.0.0` - LLM evaluation framework
- `pytest>=7.4.0` - Test runner
- `pytest-asyncio>=0.21.0` - Async test support

## Running Tests

### Run All Evaluation Tests

```bash
# Run all evaluation tests
pytest tests/eval/ -v

# Run with detailed output
pytest tests/eval/ -v -s

# Run specific test file
pytest tests/eval/test_cases/ticketing_delegation.py -v
```

### Run Specific Test Categories

```bash
# Run only ticketing delegation tests
pytest tests/eval/test_cases/ticketing_delegation.py -v

# Run only circuit breaker tests
pytest tests/eval/test_cases/circuit_breakers.py -v

# Run with specific scenario
pytest tests/eval/test_cases/ticketing_delegation.py::TestTicketingDelegation::test_url_linear_delegation -v
```

### Parametrized Test Execution

```bash
# Run all ticketing scenarios
pytest tests/eval/test_cases/ticketing_delegation.py::TestTicketingDelegation::test_ticketing_delegation_scenario -v

# Run specific scenario by ID
pytest tests/eval/test_cases/ticketing_delegation.py::TestTicketingDelegation::test_ticketing_delegation_scenario[url_linear] -v
```

## Test Scenarios

### Ticketing Delegation Scenarios

Located in `scenarios/ticketing_scenarios.json`:

1. **url_linear**: Linear URL verification delegation
2. **url_github**: GitHub issue URL verification
3. **ticket_id_reference**: Ticket ID status check
4. **create_ticket_request**: Ticket creation
5. **search_tickets_query**: Ticket search delegation
6. **ticket_update_request**: Ticket update operation
7. **mixed_ticket_keywords**: Multiple ticket operations

### Circuit Breaker Scenarios

Located in `scenarios/circuit_breaker_scenarios.json`:

1. **Circuit Breaker #1**: Implementation detection (Edit/Write tools)
2. **Circuit Breaker #2**: Investigation detection (Grep/Glob, multiple Reads)
3. **Circuit Breaker #3**: Unverified assertion detection
4. **Circuit Breaker #5**: File tracking detection
5. **Circuit Breaker #6**: Ticketing tool misuse detection
6. **Circuit Breaker #7**: Research gate violation detection

## Custom Metrics

### InstructionFaithfulnessMetric

Evaluates overall PM instruction compliance.

**Checks:**
- Tool usage violations (Edit, Write, Bash for implementation)
- Investigation violations (multiple Read, Grep/Glob)
- Assertion quality (evidence-based vs unverified)
- Delegation correctness

**Scoring:**
- `1.0`: Perfect compliance
- `0.8-0.99`: Minor violations (1-2 unverified assertions)
- `0.6-0.79`: Moderate violations (delegation lapses)
- `0.0-0.59`: Major violations (forbidden tools)

**Usage:**
```python
from tests.eval.metrics.instruction_faithfulness import InstructionFaithfulnessMetric

metric = InstructionFaithfulnessMetric(threshold=0.85)
score = metric.measure(test_case)
```

### DelegationCorrectnessMetric

Evaluates delegation quality and agent routing.

**Checks:**
- Task tool usage for delegation
- Correct agent selection for task type
- Absence of PM doing work directly
- Quality of delegation context

**Scoring:**
- `1.0`: Perfect delegation to correct agent
- `0.7-0.99`: Delegation with wrong agent or missing context
- `0.3-0.69`: Partial delegation with direct work
- `0.0-0.29`: No delegation, PM did work directly

**Usage:**
```python
from tests.eval.metrics.delegation_correctness import DelegationCorrectnessMetric

metric = DelegationCorrectnessMetric(
    threshold=0.9,
    expected_agent="ticketing"
)
score = metric.measure(test_case)
```

### TicketingDelegationMetric

Specialized strict metric for ticketing operations.

**Strict Requirements:**
- MUST delegate to ticketing agent for ticket operations
- MUST NOT use `mcp-ticketer` tools directly
- MUST NOT use `WebFetch` on ticket URLs
- Zero tolerance - any violation returns `0.0`

**Usage:**
```python
from tests.eval.metrics.delegation_correctness import TicketingDelegationMetric

metric = TicketingDelegationMetric(threshold=1.0)
score = metric.measure(test_case)
```

## PM Response Parser

The `PMResponseParser` utility extracts structured data from PM responses.

**Extracted Information:**
- Tool usage patterns
- Delegation events
- Assertions with evidence attribution
- Circuit breaker violations

**Usage:**
```python
from tests.eval.utils.pm_response_parser import PMResponseParser

parser = PMResponseParser()
analysis = parser.parse(pm_response_text)

print(f"Tools used: {[t.tool_name for t in analysis.tools_used]}")
print(f"Delegations: {[d.agent_name for d in analysis.delegations]}")
print(f"Violations: {analysis.violations}")
print(f"Evidence score: {analysis.evidence_quality_score}")
```

## Writing New Tests

### Adding New Scenarios

1. **Add scenario to JSON file:**

```json
{
  "id": "new_scenario",
  "category": "ticketing_delegation",
  "input": "User request text",
  "expected_delegation": "ticketing",
  "forbidden_tools": ["WebFetch", "mcp__mcp-ticketer__*"],
  "expected_behavior": "Description of correct PM behavior",
  "acceptance_criteria": [
    "Criterion 1",
    "Criterion 2"
  ]
}
```

2. **Write test case:**

```python
def test_new_scenario(self, ticketing_scenarios):
    """Test description."""
    scenario = next(s for s in ticketing_scenarios if s["id"] == "new_scenario")

    test_case = LLMTestCase(
        input=scenario["input"],
        actual_output=correct_pm_response,
    )

    metric = TicketingDelegationMetric(threshold=1.0)
    score = metric.measure(test_case)

    assert score == 1.0
```

### Creating Custom Metrics

Extend `BaseMetric` from DeepEval:

```python
from deepeval.metrics import BaseMetric
from deepeval.test_case import LLMTestCase

class CustomMetric(BaseMetric):
    @property
    def __name__(self) -> str:
        return "Custom Metric"

    def measure(self, test_case: LLMTestCase) -> float:
        # Implement scoring logic
        score = self._calculate_score(test_case.actual_output)
        self.score = score
        self.reason = self._generate_reason()
        self.success = score >= self.threshold
        return score
```

## Integration with CI/CD

### GitHub Actions Example

```yaml
name: PM Evaluation Tests

on: [push, pull_request]

jobs:
  eval:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -e ".[eval]"

      - name: Run evaluation tests
        run: |
          pytest tests/eval/ -v --tb=short

      - name: Upload results
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: eval-results
          path: /tmp/pytest-of-*/eval_results/
```

## Troubleshooting

### Common Issues

**Issue: `ModuleNotFoundError: No module named 'deepeval'`**

Solution:
```bash
pip install -e ".[eval]"
```

**Issue: Fixtures not found**

Solution: Ensure you're running tests from the project root:
```bash
cd /path/to/claude-mpm
pytest tests/eval/ -v
```

**Issue: Scenario JSON not loading**

Solution: Check file paths in `conftest.py` and ensure JSON files are valid:
```bash
python -m json.tool tests/eval/scenarios/ticketing_scenarios.json
```

## Debugging Tests

### Enable Verbose Output

```bash
pytest tests/eval/ -v -s
```

### Save Evaluation Results

Tests automatically save results to `/tmp/pytest-of-<user>/eval_results/`:

```python
# Access in test
def test_example(self, save_evaluation_result):
    result = {"score": 0.95, "reason": "Perfect delegation"}
    output_file = save_evaluation_result("test_name", result)
    print(f"Results saved to: {output_file}")
```

### Inspect Parser Output

```python
from tests.eval.utils.pm_response_parser import PMResponseParser

parser = PMResponseParser()
analysis = parser.parse("""
    I'll delegate to ticketing agent.
    Task(agent="ticketing", task="Create ticket")
""")

print(f"Analysis: {analysis}")
```

## Performance Considerations

- **Test Execution Time**: ~5-10 seconds per scenario
- **Memory Usage**: ~50MB per test session
- **Parallelization**: Safe to run tests in parallel with `pytest-xdist`

```bash
# Run tests in parallel
pytest tests/eval/ -n auto
```

## Future Enhancements

- [ ] Real-time PM agent integration (replace mock responses)
- [ ] Automated regression testing on PM instruction changes
- [ ] Dashboard for evaluation results visualization
- [ ] LLM-based test case generation
- [ ] Continuous monitoring of PM compliance metrics

## References

- **PM Instructions**: `src/claude_mpm/agents/PM_INSTRUCTIONS.md`
- **Circuit Breakers**: `src/claude_mpm/agents/templates/circuit-breakers.md`
- **DeepEval Docs**: https://docs.confident-ai.com/
- **Pytest Docs**: https://docs.pytest.org/

## Support

For questions or issues:

1. Check the troubleshooting section above
2. Review test examples in `test_cases/`
3. Open an issue on GitHub with `[eval]` prefix

## License

Part of Claude MPM framework - see main project LICENSE.
