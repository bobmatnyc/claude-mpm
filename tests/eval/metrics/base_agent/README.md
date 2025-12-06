# BASE_AGENT Metrics

This directory contains DeepEval metrics for evaluating BASE_AGENT compliance with core principles from BASE_AGENT.md.

## Available Metrics

### VerificationComplianceMetric

**Purpose**: Validates the "Always Verify" principle from BASE_AGENT.md

**What it measures**:
- Tool verification patterns (Edit→Read, Deploy→Health Check)
- Evidence-based assertions (line numbers, code snippets, output)
- Test execution and result reporting
- Quality gates (type checking, linting, coverage)

**Threshold**: 0.9 (90% compliance recommended)

**Quick Start**:
```python
from tests.eval.metrics.base_agent import VerificationComplianceMetric
from deepeval.test_case import LLMTestCase

metric = VerificationComplianceMetric(threshold=0.9)
test_case = LLMTestCase(
    input="Edit config file",
    actual_output=agent_response
)
score = metric.measure(test_case)
```

See [USAGE.md](./USAGE.md) for detailed documentation.

## Files

- **verification_compliance.py**: Core metric implementation
- **test_verification_compliance.py**: Comprehensive test suite
- **demo_verification_metric.py**: Interactive demo script
- **USAGE.md**: Detailed usage documentation
- **README.md**: This file

## Running Tests

```bash
# Run all tests
pytest tests/eval/metrics/base_agent/test_verification_compliance.py -v

# Run demo
python tests/eval/metrics/base_agent/demo_verification_metric.py
```

## Scoring Algorithm

The metric uses a weighted scoring system:

| Component | Weight | What it checks |
|-----------|--------|----------------|
| Tool Verification | 40% | Edit→Read patterns, health checks, verification keywords |
| Assertion Evidence | 30% | Line numbers, code snippets, output evidence |
| Test Execution | 20% | Test commands run, results reported |
| Quality Gates | 10% | Type checking, linting, coverage |

**Adaptive Scoring**: Components adapt to context:
- No edits → Tool verification gets full score (not needed)
- No code changes → Test execution gets full score (not needed)
- No code changes → Quality gates get full score (not needed)

This ensures agents aren't penalized for read-only operations.

## Score Ranges

| Range | Interpretation | Typical Cause |
|-------|---------------|---------------|
| 0.85-1.0 | Perfect compliance | All verification elements present |
| 0.75-0.84 | Good compliance | Core verification present, minor gaps |
| 0.65-0.74 | Moderate compliance | Some verification, multiple gaps |
| < 0.65 | Poor compliance | Major gaps, unsubstantiated claims |

## Strict Mode

For critical compliance checks, use strict mode:

```python
from tests.eval.metrics.base_agent import StrictVerificationComplianceMetric

metric = StrictVerificationComplianceMetric()
# Fails immediately on ANY unsubstantiated claim
```

Strict mode returns 0.0 for any:
- "should/would/could work"
- "probably/likely/seems to"
- "I think/believe/assume"

## Integration with Agent Tests

This metric integrates with the agent testing framework:

```python
from tests.eval.agents.shared import BaseAgentTest
from tests.eval.metrics.base_agent import VerificationComplianceMetric

class TestEngineerAgent(BaseAgentTest):
    agent_type = AgentType.ENGINEER

    def test_code_changes_verified(self, mock_agent):
        response = self.invoke_agent(
            mock_agent,
            "Implement JWT validation"
        )

        # Create test case
        test_case = self.create_test_case(
            "Implement JWT validation",
            response.raw_output
        )

        # Measure verification compliance
        metric = VerificationComplianceMetric(threshold=0.85)
        score = metric.measure(test_case)

        assert score >= 0.85, f"Verification compliance: {metric.reason}"
```

## DeepEval Phase 2 Integration

Part of Issue #107 - DeepEval Phase 2 agent testing framework:

1. **Metrics Layer**: VerificationComplianceMetric (this implementation)
2. **Test Cases Layer**: BASE_AGENT test scenarios
3. **Evaluation Layer**: Automated agent compliance testing
4. **Reporting Layer**: Detailed compliance reports

## Design Decisions

### Why adaptive scoring?

Read-only operations don't require tests or quality gates. The metric adapts to avoid penalizing agents for operations that don't need verification.

### Why weighted components?

Different verification aspects have different importance:
- Tool verification (40%): Core "Always Verify" principle
- Evidence (30%): Prevents unsubstantiated claims
- Tests (20%): Validates changes work
- Quality gates (10%): Nice-to-have but not always critical

### Why regex-based detection?

Simple, fast, and effective for pattern matching. Future versions may add:
- AST-based code analysis
- LLM-based semantic analysis
- Custom pattern plugins

## Known Limitations

1. **Pattern matching limitations**: May miss complex verification patterns
2. **Language-specific**: Better detection for Python/JavaScript than others
3. **No semantic understanding**: Relies on keywords and patterns
4. **False positives**: Verification keywords in planning context may score

See USAGE.md "Future Enhancements" section for planned improvements.

## Contributing

When adding new verification patterns:

1. Add pattern to class constants (e.g., `VERIFICATION_KEYWORDS`)
2. Update scoring method (e.g., `_score_tool_verification`)
3. Add test case in `test_verification_compliance.py`
4. Update USAGE.md with examples
5. Run full test suite to verify no regressions

## Related Documentation

- [BASE_AGENT.md](../../../../src/claude_mpm/agents/BASE_AGENT.md): Core principles
- [DeepEval Phase 2 Research](../../../../docs/research/deepeval-phase-2-agent-testing-evaluation-framework.md): Testing framework design
- [Agent Testing Infrastructure](../../agents/shared/): Shared testing utilities

## License

Part of Claude MPM framework - same license as parent project.
