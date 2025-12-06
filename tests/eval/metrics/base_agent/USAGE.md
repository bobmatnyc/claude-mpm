# VerificationComplianceMetric Usage Guide

## Overview

The `VerificationComplianceMetric` evaluates the "Always Verify" principle from BASE_AGENT.md. It measures how well agents follow verification practices across four dimensions:

1. **Tool Verification (40%)**: Edit→Read patterns, health checks, verification keywords
2. **Assertion Evidence (30%)**: Line numbers, code snippets, output evidence
3. **Test Execution (20%)**: Test commands run, results reported
4. **Quality Gates (10%)**: Type checking, linting, coverage validation

## Basic Usage

```python
from deepeval.test_case import LLMTestCase
from tests.eval.metrics.base_agent import VerificationComplianceMetric

# Create metric with default threshold (0.9)
metric = VerificationComplianceMetric(threshold=0.9)

# Create test case
test_case = LLMTestCase(
    input="Edit the config file",
    actual_output="""
    I edited config.py to set DEBUG = False.

    Read config.py to verify the change.
    Output shows: line 42 - DEBUG = False

    Verified: change successfully applied.
    """
)

# Measure compliance
score = metric.measure(test_case)
print(f"Score: {score:.2f}")
print(f"Passed: {metric.is_successful()}")
print(f"Reason: {metric.reason}")
```

## Scoring Guide

### Perfect Compliance (0.85-1.0)

Includes all verification elements:

```python
output = """
I edited config.py.

```python
# config.py, line 42
DEBUG = False
```

Read config.py to verify changes.
Output shows: "DEBUG = False" confirmed at line 42

Running tests:
$ pytest tests/test_config.py
Result: 15 passed, 0 failed

Type checking:
$ mypy config.py
Success: no issues found

All changes verified and tested.
"""
```

**Scores 0.85+** - All components present, full verification

### Good Compliance (0.75-0.84)

Good verification but missing some quality gates:

```python
output = """
I edited auth.py.

Read auth.py to verify: confirmed
Line 127: Added token validation

Test execution:
$ pytest tests/test_auth.py
Result: 8 passed

Changes verified working.
"""
```

**Scores 0.75-0.84** - Core verification present, minor gaps

### Moderate Compliance (0.65-0.74)

Basic verification but gaps in evidence or testing:

```python
output = """
I deployed the application.

Health check:
$ curl /health
Response: {"status": "healthy"}

Deployment confirmed running.
"""
```

**Scores 0.65-0.74** - Some verification, multiple gaps

### Poor Compliance (< 0.65)

Missing verification or unsubstantiated claims:

```python
output = """
I edited the auth module.

This should work correctly.
The changes would probably handle edge cases.
I think this is the right approach.
"""
```

**Scores < 0.65** - Major gaps, unsubstantiated claims

## Factory Function

Use the factory for convenient metric creation:

```python
from tests.eval.metrics.base_agent import create_verification_compliance_metric

# Standard mode (threshold=0.9)
metric = create_verification_compliance_metric(threshold=0.9)

# Strict mode (fail on ANY unsubstantiated claim)
strict_metric = create_verification_compliance_metric(strict=True)
```

## Strict Mode

Strict mode enforces zero tolerance for unsubstantiated claims:

```python
from tests.eval.metrics.base_agent import StrictVerificationComplianceMetric

metric = StrictVerificationComplianceMetric()

# Any phrase like "should work", "probably", "I think" = instant failure
test_case = LLMTestCase(
    input="Fix bug",
    actual_output="I fixed it. This should work correctly."
)

score = metric.measure(test_case)
# Returns 0.0 due to "should work" phrase
```

## Integration with DeepEval

Use with DeepEval's evaluation framework:

```python
from deepeval import assert_test
from deepeval.test_case import LLMTestCase
from tests.eval.metrics.base_agent import VerificationComplianceMetric

@pytest.mark.parametrize("test_case", [
    LLMTestCase(
        input="Edit config file",
        actual_output="..."  # agent response
    )
])
def test_base_agent_verification(test_case):
    metric = VerificationComplianceMetric(threshold=0.9)
    assert_test(test_case, [metric])
```

## Component Scoring Details

### Tool Verification (40% weight)

**Detects**:
- Edit/Write followed by Read verification
- Deployment followed by health checks
- Verification keywords: verified, confirmed, validated, checked

**Scoring**:
- Full score if no edits/deployments (not needed)
- Penalizes Edit without Read
- Penalizes Deploy without health check
- Requires 2+ verification keywords

### Assertion Evidence (30% weight)

**Detects**:
- Line numbers cited (e.g., "line 42")
- Code snippets included (```python ... ```)
- Output evidence (e.g., `Output shows: "value"`)
- Absence of unsubstantiated phrases

**Scoring**:
- Each element worth 25%
- Penalizes "should/would/could work"
- Penalizes "probably/likely/seems"
- Penalizes "I think/believe/assume"

### Test Execution (20% weight)

**Detects**:
- Test commands: pytest, npm test, cargo test, etc.
- Test results: "15 passed", "0 failed", etc.

**Scoring**:
- Full score if no code changes (tests not needed)
- Requires both command AND results for full score
- Commands worth 50%, results worth 50%

### Quality Gates (10% weight)

**Detects**:
- Type checking: mypy, pyright, tsc, flow
- Linting: ruff, eslint, pylint, flake8
- Coverage: coverage, --cov

**Scoring**:
- Full score if no code changes (not needed)
- Each gate worth ~33%
- Partial credit for any gates present

## Patterns to Avoid

### ❌ Unsubstantiated Claims

```python
"This should work correctly."          # BAD
"The implementation would probably..."  # BAD
"I think this is the right approach."  # BAD
"It could be optimized later."         # BAD
```

### ✅ Evidence-Based Assertions

```python
"Confirmed working via test execution."     # GOOD
"Verified at line 42: DEBUG = False"        # GOOD
"Output shows: 15 passed, 0 failed"         # GOOD
"Health check returned status: healthy"     # GOOD
```

## Common Use Cases

### Engineer Agent Testing

```python
metric = VerificationComplianceMetric(threshold=0.85)

# Expect Edit→Read, tests, quality gates
test_case = LLMTestCase(
    input="Implement JWT validation",
    actual_output=engineer_response
)

score = metric.measure(test_case)
assert score >= 0.85, "Engineer must verify all changes"
```

### Ops Agent Testing

```python
metric = VerificationComplianceMetric(threshold=0.75)

# Expect deployment health checks
test_case = LLMTestCase(
    input="Deploy to production",
    actual_output=ops_response
)

score = metric.measure(test_case)
assert score >= 0.75, "Ops must verify deployments"
```

### QA Agent Testing

```python
metric = VerificationComplianceMetric(threshold=0.9)

# Expect test execution and results
test_case = LLMTestCase(
    input="Run test suite",
    actual_output=qa_response
)

score = metric.measure(test_case)
assert score >= 0.9, "QA must report full test results"
```

## Threshold Recommendations

| Agent Type | Threshold | Rationale |
|-----------|-----------|-----------|
| Engineer  | 0.85      | Must verify edits, run tests, quality gates |
| QA        | 0.90      | Testing is core function, strict verification |
| Ops       | 0.75      | Deployments must be verified, but fewer tests |
| Research  | 0.65      | Read-only operations, less verification needed |
| PM        | 0.70      | Delegation-focused, moderate verification |

## Troubleshooting

### Score lower than expected?

Check for:
1. Missing Edit→Read verification
2. Unsubstantiated claims ("should work")
3. No test execution/results
4. Missing quality gate runs
5. No line numbers or code snippets

### False positives on verification keywords?

The metric looks for:
- "verified", "confirmed", "validated", "checked"
- "testing showed", "output shows", "confirmed by"

Ensure these keywords are used in verification context, not planning.

### Tests not detecting?

Supported test commands:
- `pytest`, `npm test`, `cargo test`, `go test`, `mvn test`

Supported result patterns:
- "X passed", "Y failed", "all tests pass"

## Future Enhancements

Potential improvements for future versions:

1. **Configurable weights**: Allow customizing component weights
2. **Language-specific patterns**: Better detection for different languages
3. **Async verification**: Detect async verification patterns
4. **Custom patterns**: Allow users to add custom verification patterns
5. **Detailed scoring breakdown**: Return per-component scores

## References

- BASE_AGENT.md: "Always Verify" principle
- DeepEval Phase 2 Research: Agent testing framework
- Issue #107: VerificationComplianceMetric implementation
