# BASE_AGENT Behavioral Testing - Implementation Specification

**Version**: 1.0.0
**Date**: December 6, 2025
**Status**: Design Complete ✅ - Ready for Implementation
**GitHub Issue**: [#107](https://github.com/bobmatnyc/claude-mpm/issues/107)

---

## Overview

This directory contains comprehensive behavioral test specifications for BASE_AGENT evaluation using DeepEval. The specifications define 20 behavioral scenarios, 2 custom metrics, and 5 integration tests to validate BASE_AGENT compliance across all agent types in the Claude MPM framework.

**Scope**: BASE_AGENT_TEMPLATE.md (292 LOC) behavioral validation
**Coverage**: 100% of BASE_AGENT requirements
**Framework**: DeepEval 1.0.0+

---

## Directory Structure

```
tests/eval/agents/base_agent/
├── README.md                    # This file - Implementation guide
├── TEST_SCENARIOS.md            # 20 behavioral scenarios (39KB)
├── METRICS.md                   # 2 custom metrics specs (28KB)
├── INTEGRATION_TESTS.md         # 5 integration tests (25KB)
├── scenarios/                   # JSON scenario definitions (to be created)
│   └── base_agent_scenarios.json
├── test_base_patterns.py        # Verification compliance tests (to be created)
├── test_memory_protocol.py      # Memory protocol tests (to be created)
├── test_response_format.py      # Response format tests (to be created)
├── integration_tests.py         # Integration test suite (to be created)
├── responses/                   # Captured agent responses (to be created)
│   ├── scenario_01_file_edit_verification.json
│   ├── scenario_02_test_execution.json
│   └── ...
└── golden_responses/            # Golden baseline responses (to be created)
    └── base_agent_baseline.json
```

---

## Quick Start

### 1. Review Specifications

**Read in this order**:
1. **TEST_SCENARIOS.md**: Understand the 20 behavioral scenarios
2. **METRICS.md**: Study the 2 custom metrics (VerificationComplianceMetric, MemoryProtocolMetric)
3. **INTEGRATION_TESTS.md**: Review the 5 integration test plans

### 2. Implementation Checklist

**Phase 1: Metrics Implementation** (1 day)
- [ ] Create `tests/eval/metrics/base_agent/` directory
- [ ] Implement `verification_compliance.py` (VerificationComplianceMetric)
- [ ] Implement `memory_protocol_metric.py` (MemoryProtocolMetric)
- [ ] Create unit tests for metrics (`test_verification_compliance.py`, `test_memory_protocol_metric.py`)
- [ ] Calibrate metric thresholds with sample responses

**Phase 2: Scenario Conversion** (1 day)
- [ ] Convert 20 scenarios from TEST_SCENARIOS.md to JSON format
- [ ] Create `scenarios/base_agent_scenarios.json`
- [ ] Validate JSON schema matches test harness requirements
- [ ] Create mock responses for each scenario

**Phase 3: Test Harness** (1 day)
- [ ] Implement `test_base_patterns.py` (Scenarios 1-8: Verification Compliance)
- [ ] Implement `test_memory_protocol.py` (Scenarios 9-15: Memory Protocol)
- [ ] Implement `test_response_format.py` (Scenarios 16-18: Template Merging)
- [ ] Implement `test_tool_orchestration.py` (Scenarios 19-20: Tool Orchestration)

**Phase 4: Integration Tests** (1 day)
- [ ] Implement `integration_tests.py` (5 integration tests)
- [ ] Create test execution framework (Mock/Replay/Integration modes)
- [ ] Set up response capture infrastructure
- [ ] Create golden baseline responses

**Phase 5: Documentation & CI/CD** (0.5 days)
- [ ] Document test execution process
- [ ] Create GitHub Actions workflow
- [ ] Add to main test suite
- [ ] Update project documentation

**Total Estimated Time**: 4.5 days

---

## Test Scenarios Summary

### Category Breakdown

| Category | Scenarios | Priority | Coverage |
|----------|-----------|----------|----------|
| **Verification Compliance** | 8 | Critical/High | File edits, test execution, API calls, assertions, quality gates, error handling, deployment, code review |
| **Memory Protocol** | 6 | Critical/High | JSON format, memory capture triggers, memory quality, consolidation, updates, size limits |
| **Template Merging** | 3 | High/Medium | Base inheritance, specialized override, tool authorization |
| **Tool Orchestration** | 3 | Medium/High | Parallel execution, error recovery, cascading workflows |
| **Total** | **20** | Mixed | **100% BASE_AGENT coverage** |

### Scenario Index

**Verification Compliance** (Scenarios 1-8):
1. File Edit Verification
2. Test Execution Verification
3. API Call Verification
4. Assertion Evidence Validation
5. Quality Gate Compliance
6. Error Handling Verification
7. Deployment Verification
8. Code Review Verification

**Memory Protocol** (Scenarios 9-15):
9. JSON Response Format Compliance
10. Memory Capture Trigger - User Instruction
11. Memory Capture - Undocumented Facts
12. Memory Avoidance - Documented Facts
13. Memory Consolidation
14. Memory Update Pattern
15. Memory Size Limit

**Template Merging** (Scenarios 16-18):
16. Base Template Inheritance
17. Specialized Override
18. Tool Authorization Inheritance

**Tool Orchestration** (Scenarios 19-20):
19. Parallel Tool Execution
20. Error Recovery

---

## Custom Metrics

### Metric 1: VerificationComplianceMetric

**Purpose**: Validates evidence-based reporting and tool verification patterns

**Components** (weighted average):
- Tool Verification (40%): Edit→Read, Deploy→Health Check
- Assertion Evidence (30%): Line numbers, code snippets, output
- Test Execution (20%): Test commands, results, failure handling
- Quality Gates (10%): Type hints, docs, linting

**Scoring**:
- 1.0 = Perfect verification
- 0.7-0.9 = Most verification present
- 0.4-0.6 = Some verification
- 0.0-0.3 = Little or no verification

**Threshold**: 0.9 (90% compliance)

### Metric 2: MemoryProtocolMetric

**Purpose**: Evaluates JSON response format and memory management compliance

**Components** (weighted average):
- JSON Format (30%): Valid JSON block at end
- Required Fields (30%): All fields present with correct types
- Memory Capture (25%): Appropriate capture triggers
- Memory Quality (15%): Concise, specific, actionable

**Scoring**:
- 1.0 = Perfect protocol compliance
- 0.7-0.9 = Minor issues
- 0.4-0.6 = Significant issues
- 0.0-0.3 = Major violations

**Threshold**: 1.0 (strict compliance)

---

## Integration Tests

### Test 1: Template Merge and Inheritance
Validates specialized agents inherit BASE_AGENT behaviors while applying specialized overrides.

**Agents Tested**: Research, Engineer, QA, Ops, Documentation
**Key Validations**: BASE_AGENT inheritance + specialized behaviors

### Test 2: Multi-Tool Workflow with Verification Chain
Validates complex workflows (Fix → Test → Build → Deploy → Verify) with verification at each step.

**Workflow Steps**: 5 steps with verification chain
**Key Validations**: Tool orchestration, verification evidence

### Test 3: Error Recovery and Escalation
Validates error detection, recovery attempts, and escalation when recovery fails.

**Scenarios**: Recovery success, Recovery failure → Escalation
**Key Validations**: Error handling, escalation protocol

### Test 4: Memory Persistence Across Sessions
Validates memory capture, retrieval, and updates across multiple sessions.

**Sessions**: Discovery → Retrieval → Update
**Key Validations**: Memory lifecycle, MEMORIES section

### Test 5: Cross-Agent Behavioral Consistency
Validates all specialized agents maintain consistent BASE_AGENT behaviors.

**Agents Tested**: 5 agent types
**Key Validations**: Consistent compliance across agents

---

## Usage Examples

### Running Scenario Tests

```bash
# Run all BASE_AGENT scenario tests
pytest tests/eval/agents/base_agent/test_base_patterns.py -v

# Run specific category
pytest tests/eval/agents/base_agent/test_memory_protocol.py -v

# Run with detailed output
pytest tests/eval/agents/base_agent/ -v --capture=no
```

### Running Integration Tests

```bash
# Run all integration tests (mock mode)
pytest tests/eval/agents/base_agent/integration_tests.py --mode=mock -v

# Run with captured responses (replay mode)
pytest tests/eval/agents/base_agent/integration_tests.py --mode=replay -v

# Run with real agent invocation (integration mode)
pytest tests/eval/agents/base_agent/integration_tests.py --mode=integration -v
```

### Running Custom Metrics

```python
from deepeval import assert_test
from deepeval.test_case import LLMTestCase
from tests.eval.metrics.base_agent.verification_compliance import VerificationComplianceMetric
from tests.eval.metrics.base_agent.memory_protocol_metric import MemoryProtocolMetric

# Test case
test_case = LLMTestCase(
    input="Update config.py to set DEBUG=False",
    actual_output=agent_response,
    expected_output="Configuration updated with verification"
)

# Run metrics
verification_metric = VerificationComplianceMetric(threshold=0.9)
memory_metric = MemoryProtocolMetric(threshold=1.0)

assert_test(test_case, [verification_metric, memory_metric])
```

---

## Implementation Guidelines

### Metric Implementation

**File**: `tests/eval/metrics/base_agent/verification_compliance.py`

```python
from deepeval.metrics import BaseMetric
from deepeval.test_case import LLMTestCase

class VerificationComplianceMetric(BaseMetric):
    def __init__(self, threshold: float = 0.9):
        self.threshold = threshold
        self.score = 0.0
        self.reason = ""

    @property
    def name(self) -> str:
        return "Verification Compliance"

    def measure(self, test_case: LLMTestCase) -> float:
        # Implementation from METRICS.md
        pass

    def is_successful(self) -> bool:
        return self.success
```

### Scenario JSON Format

**File**: `scenarios/base_agent_scenarios.json`

```json
{
  "scenario_id": "BASE-001",
  "name": "Agent must verify file edits before reporting completion",
  "category": "verification",
  "severity": "critical",
  "instruction_source": "BASE_AGENT_TEMPLATE.md:10-13",
  "behavioral_requirement": "Always verify changes - test functions, APIs, edits",
  "input": "User: Update config.py to add new setting",
  "expected_agent_behavior": {
    "should_do": ["Read config.py after edit", "Verify change applied"],
    "should_not_do": ["Report completion without verification"],
    "required_tools": ["Edit", "Read"],
    "verification_pattern": "Edit.*Read"
  },
  "compliant_response_pattern": "Edit tool used, then Read tool verifies change",
  "violation_response_pattern": "Edit tool used but no verification Read"
}
```

### Test Implementation Pattern

**File**: `test_base_patterns.py`

```python
import pytest
from deepeval import assert_test
from deepeval.test_case import LLMTestCase
from tests.eval.metrics.base_agent.verification_compliance import VerificationComplianceMetric

class TestVerificationCompliance:
    """Test BASE_AGENT verification compliance scenarios."""

    @pytest.fixture
    def verification_metric(self):
        """Fixture for verification compliance metric."""
        return VerificationComplianceMetric(threshold=0.9)

    def test_scenario_01_file_edit_verification(self, verification_metric):
        """Scenario 1: Agent must verify file edits."""
        test_case = LLMTestCase(
            input="Update config.py to set DEBUG=False",
            actual_output=mock_agent_response(),
            expected_output="File edited with verification"
        )

        assert_test(test_case, [verification_metric])
```

---

## Success Criteria

### Deliverables Checklist

- [x] **TEST_SCENARIOS.md**: 20 scenarios fully documented ✅
- [x] **METRICS.md**: 2 custom metrics specified ✅
- [x] **INTEGRATION_TESTS.md**: 5 integration tests planned ✅
- [ ] **Metrics Implementation**: Python files with unit tests
- [ ] **Scenario Conversion**: JSON scenario definitions
- [ ] **Test Harness**: Pytest test files
- [ ] **Integration Tests**: Integration test suite
- [ ] **CI/CD Integration**: GitHub Actions workflow

### Quality Gates

**Code Quality**:
- [ ] All metrics pass unit tests
- [ ] All scenarios pass with compliant responses
- [ ] All integration tests pass in mock mode
- [ ] Type hints for all functions
- [ ] Docstrings for all classes and methods

**Coverage**:
- [ ] 100% BASE_AGENT_TEMPLATE.md coverage
- [ ] All 20 scenarios implemented
- [ ] All 2 metrics implemented
- [ ] All 5 integration tests implemented

**Documentation**:
- [ ] README with usage examples
- [ ] Metric documentation with examples
- [ ] Scenario documentation with expected outputs
- [ ] Integration test documentation

---

## Related Documents

### Phase 1 Implementation (Reference)
- `tests/eval/README.md` - Base DeepEval framework
- `tests/eval/README_INTEGRATION.md` - Integration testing guide
- `tests/eval/PM_BEHAVIORAL_TESTING.md` - PM behavioral testing (template)

### Research Documents
- `docs/research/deepeval-phase2-agent-testing-research.md` - Phase 2 research
- `docs/research/deepeval-complete-implementation-summary.md` - Phase 1 summary

### Agent Templates
- `src/claude_mpm/agents/BASE_AGENT_TEMPLATE.md` - Source template (292 LOC)
- `src/claude_mpm/agents/BASE_RESEARCH.md` - Research specialization
- `src/claude_mpm/agents/BASE_ENGINEER.md` - Engineer specialization
- `src/claude_mpm/agents/BASE_QA.md` - QA specialization

---

## Next Steps

### Immediate (Week 1)
1. ✅ Review specifications (completed)
2. Create metrics implementation plan
3. Set up development environment
4. Begin metrics implementation

### Short-term (Week 2-3)
1. Complete metrics implementation and unit tests
2. Convert scenarios to JSON format
3. Implement test harness
4. Create mock responses for scenarios

### Medium-term (Week 4-5)
1. Implement integration tests
2. Set up response capture infrastructure
3. Create golden baseline responses
4. Integrate with CI/CD

### Long-term (Week 6+)
1. Extend to specialized agents (Research, Engineer, QA, Ops, Documentation)
2. Add performance benchmarking
3. Create comprehensive test suite
4. Production deployment

---

## Contact & Support

**Issue Tracker**: https://github.com/bobmatnyc/claude-mpm/issues/107
**Project Board**: https://github.com/users/bobmatnyc/projects/9
**Documentation**: `tests/eval/agents/base_agent/`

---

## Changelog

### Version 1.0.0 (December 6, 2025)
- Initial design specification complete
- 20 behavioral scenarios documented
- 2 custom metrics specified
- 5 integration tests planned
- Ready for implementation

---

**Document Version**: 1.0.0
**Last Updated**: December 6, 2025
**Status**: Design Complete ✅ - Ready for Implementation
