# Documentation Agent Test Harness

**Sprint 6 (#112)** - DeepEval Phase 2 Integration Tests

## Overview

This test harness validates Documentation Agent behavioral compliance across 12 scenarios in 4 categories using custom DeepEval metrics.

**Agent**: Documentation Agent
**Metrics**: ClarityStandardsMetric, AudienceAwarenessMetric
**Scenarios**: 12 total (4 clarity, 4 audience, 2 maintenance, 2 completeness)
**Workflow Tests**: 3 multi-step integration tests

## Test Structure

```
tests/eval/agents/documentation/
├── test_integration.py          # Main test harness (THIS FILE)
├── README.md                     # Documentation (you are here)
└── __pycache__/                  # Python bytecode cache
```

## Scenario Categories

### 1. Clarity Standards (4 scenarios)

**Tests**: `TestDocumentationClarityStandards`
**Metric**: ClarityStandardsMetric (threshold 0.85)

| Scenario ID | Name | Priority |
|-------------|------|----------|
| DOC-CLARITY-001 | Active Voice Usage | Critical |
| DOC-CLARITY-002 | Jargon Handling and Definitions | High |
| DOC-CLARITY-003 | Code Examples for Complex Concepts | Critical |
| DOC-CLARITY-004 | Concise and Accurate Writing | High |

**Validates**:
- Active voice usage (>90% in instructions)
- Jargon definitions (acronyms defined on first use)
- Code examples (runnable with language hints)
- Conciseness (no redundant phrases like "in order to")

### 2. Audience Awareness (4 scenarios)

**Tests**: `TestDocumentationAudienceAwareness`
**Metric**: AudienceAwarenessMetric (threshold 0.80)

| Scenario ID | Name | Priority |
|-------------|------|----------|
| DOC-AUDIENCE-001 | Developer vs User Documentation | Critical |
| DOC-AUDIENCE-002 | Technical Depth Adaptation | High |
| DOC-AUDIENCE-003 | Context Adaptation (Internal vs Public) | Medium |
| DOC-AUDIENCE-004 | Prerequisite Knowledge Statement | Medium |

**Validates**:
- Clear audience targeting upfront
- Technical depth matches audience (architecture for devs, steps for users)
- Context appropriateness (no internal references in public docs)
- Prerequisites stated with links

### 3. Maintenance Focus (2 scenarios)

**Tests**: `TestDocumentationMaintenance`
**Metric**: AudienceAwarenessMetric with maintenance bonus (threshold 0.80)

| Scenario ID | Name | Priority |
|-------------|------|----------|
| DOC-MAINT-001 | Code Synchronization Verification | Critical |
| DOC-MAINT-002 | Example Update Protocol | High |

**Validates**:
- Code examples match current API (version numbers referenced)
- Breaking changes documented (migration guides, deprecation warnings)
- Last verified timestamps included

### 4. Completeness Requirements (2 scenarios)

**Tests**: `TestDocumentationCompleteness`
**Metric**: ClarityStandardsMetric with completeness bonus (threshold 0.85)

| Scenario ID | Name | Priority |
|-------------|------|----------|
| DOC-COMPLETE-001 | Required Sections Completeness | Critical |
| DOC-COMPLETE-002 | Troubleshooting Coverage | High |

**Validates**:
- All required sections present (Overview, Quick Start, Reference, Troubleshooting, Changelog)
- Troubleshooting section includes 3+ common errors with solutions
- Error codes and HTTP status codes documented

## Running Tests

### Run All Documentation Tests

```bash
pytest tests/eval/agents/documentation/test_integration.py -v
```

### Run Specific Category

```bash
# Clarity Standards (4 tests)
pytest tests/eval/agents/documentation/test_integration.py::TestDocumentationClarityStandards -v

# Audience Awareness (4 tests)
pytest tests/eval/agents/documentation/test_integration.py::TestDocumentationAudienceAwareness -v

# Maintenance Focus (2 tests)
pytest tests/eval/agents/documentation/test_integration.py::TestDocumentationMaintenance -v

# Completeness Requirements (2 tests)
pytest tests/eval/agents/documentation/test_integration.py::TestDocumentationCompleteness -v
```

### Run Specific Scenario

```bash
# Active voice test
pytest tests/eval/agents/documentation/test_integration.py::TestDocumentationClarityStandards::test_scenario[DOC-CLARITY-001] -v

# Developer vs user docs test
pytest tests/eval/agents/documentation/test_integration.py::TestDocumentationAudienceAwareness::test_scenario[DOC-AUDIENCE-001] -v

# Code synchronization test
pytest tests/eval/agents/documentation/test_integration.py::TestDocumentationMaintenance::test_scenario[DOC-MAINT-001] -v

# Required sections test
pytest tests/eval/agents/documentation/test_integration.py::TestDocumentationCompleteness::test_scenario[DOC-COMPLETE-001] -v
```

### Run Workflow Integration Tests

```bash
# All 3 workflow tests
pytest tests/eval/agents/documentation/test_integration.py::TestDocumentationWorkflows -v

# Specific workflow
pytest tests/eval/agents/documentation/test_integration.py::TestDocumentationWorkflows::test_documentation_clarity_workflow -v
pytest tests/eval/agents/documentation/test_integration.py::TestDocumentationWorkflows::test_documentation_audience_workflow -v
pytest tests/eval/agents/documentation/test_integration.py::TestDocumentationWorkflows::test_documentation_maintenance_workflow -v
```

### Run with Coverage

```bash
pytest tests/eval/agents/documentation/test_integration.py --cov=tests.eval.metrics.documentation --cov-report=html
```

### Run in Parallel

```bash
# Requires pytest-xdist
pytest tests/eval/agents/documentation/test_integration.py -n auto
```

## Workflow Integration Tests

### 1. Documentation Clarity Workflow

**Test**: `test_documentation_clarity_workflow`
**Scenarios**: DOC-CLARITY-001 to DOC-CLARITY-004
**Metric**: ClarityStandardsMetric (threshold 0.85)

**Flow**:
1. Draft initial documentation with active voice
2. Add jargon definitions and glossary references
3. Include practical code examples with language hints
4. Review for conciseness, remove redundant phrases

**Success Criteria**:
- Active voice used throughout (>90% of instructions)
- All acronyms defined on first use (JWT, MFA)
- Runnable code examples (bash, typescript, javascript)
- No redundant phrases
- Complete structure with all required sections

### 2. Documentation Audience Workflow

**Test**: `test_documentation_audience_workflow`
**Scenarios**: DOC-AUDIENCE-001 to DOC-AUDIENCE-004
**Metric**: AudienceAwarenessMetric (threshold 0.80)

**Flow**:
1. Identify target audience (senior backend engineers)
2. Adapt technical depth to audience expertise (architecture, design decisions)
3. Include prerequisites and assumed knowledge (RFC 6455, Node.js patterns)
4. Verify context appropriateness (technical depth matches audience)

**Success Criteria**:
- Clear audience targeting upfront (Audience: Senior Engineers)
- Technical depth matches audience (architecture diagrams, Big-O notation)
- No internal references in public docs
- Prerequisites clearly stated with links to RFCs

### 3. Documentation Maintenance Workflow

**Test**: `test_documentation_maintenance_workflow`
**Scenarios**: DOC-MAINT-001, DOC-MAINT-002
**Metrics**: ClarityStandardsMetric (0.85) + AudienceAwarenessMetric (0.80)

**Flow**:
1. Detect breaking API change (endpoint renamed)
2. Search for all affected code examples using Grep
3. Update ALL examples consistently (100% coverage)
4. Add deprecation warnings and migration guide
5. Verify version info and last updated timestamp

**Success Criteria**:
- All code examples updated to new API endpoint (22 examples)
- Deprecation warnings clearly marked (⚠️ BREAKING)
- Migration guide with before/after examples
- Version numbers referenced (v1.x → v2.0)
- Last verified timestamp included (December 6, 2025)
- Changelog entry created

## Metric Thresholds

### ClarityStandardsMetric

**Threshold**: 0.85 (85% compliance)

**Components**:
- Active voice (25%): Direct, imperative instructions
- Jargon handling (20%): Acronym definitions, glossary
- Code examples (30%): Runnable examples with language hints
- Conciseness (25%): No redundant phrases
- Completeness bonus (+15%): All required sections

**Scoring**:
- 1.0+: Perfect (with bonus)
- 0.85-0.99: Pass (excellent)
- 0.70-0.84: Fail (good but below threshold)
- 0.0-0.69: Fail (poor)

### AudienceAwarenessMetric

**Threshold**: 0.80 (80% compliance)

**Components**:
- Audience targeting (35%): Clear audience statements
- Technical depth (30%): Appropriate complexity
- Context adaptation (20%): Public vs internal
- Prerequisites (15%): Required knowledge stated
- Maintenance bonus (+10%): Version info, deprecation warnings

**Scoring**:
- 1.0+: Perfect (with bonus)
- 0.80-0.99: Pass (excellent)
- 0.65-0.79: Fail (good but below threshold)
- 0.0-0.64: Fail (poor)

## Expected Test Results

### Individual Scenario Tests

```
tests/eval/agents/documentation/test_integration.py::TestDocumentationClarityStandards::test_scenario[DOC-CLARITY-001] PASSED
tests/eval/agents/documentation/test_integration.py::TestDocumentationClarityStandards::test_scenario[DOC-CLARITY-002] PASSED
tests/eval/agents/documentation/test_integration.py::TestDocumentationClarityStandards::test_scenario[DOC-CLARITY-003] PASSED
tests/eval/agents/documentation/test_integration.py::TestDocumentationClarityStandards::test_scenario[DOC-CLARITY-004] PASSED

tests/eval/agents/documentation/test_integration.py::TestDocumentationAudienceAwareness::test_scenario[DOC-AUDIENCE-001] PASSED
tests/eval/agents/documentation/test_integration.py::TestDocumentationAudienceAwareness::test_scenario[DOC-AUDIENCE-002] PASSED
tests/eval/agents/documentation/test_integration.py::TestDocumentationAudienceAwareness::test_scenario[DOC-AUDIENCE-003] PASSED
tests/eval/agents/documentation/test_integration.py::TestDocumentationAudienceAwareness::test_scenario[DOC-AUDIENCE-004] PASSED

tests/eval/agents/documentation/test_integration.py::TestDocumentationMaintenance::test_scenario[DOC-MAINT-001] PASSED
tests/eval/agents/documentation/test_integration.py::TestDocumentationMaintenance::test_scenario[DOC-MAINT-002] PASSED

tests/eval/agents/documentation/test_integration.py::TestDocumentationCompleteness::test_scenario[DOC-COMPLETE-001] PASSED
tests/eval/agents/documentation/test_integration.py::TestDocumentationCompleteness::test_scenario[DOC-COMPLETE-002] PASSED
```

**Total**: 12 scenario tests (all should PASS with compliant responses)

### Workflow Tests

```
tests/eval/agents/documentation/test_integration.py::TestDocumentationWorkflows::test_documentation_clarity_workflow PASSED
tests/eval/agents/documentation/test_integration.py::TestDocumentationWorkflows::test_documentation_audience_workflow PASSED
tests/eval/agents/documentation/test_integration.py::TestDocumentationWorkflows::test_documentation_maintenance_workflow PASSED
```

**Total**: 3 workflow tests (all should PASS)

### Scenario File Integrity Tests

```
tests/eval/agents/documentation/test_integration.py::TestScenarioFileIntegrity::test_total_scenario_count PASSED
tests/eval/agents/documentation/test_integration.py::TestScenarioFileIntegrity::test_category_counts PASSED
tests/eval/agents/documentation/test_integration.py::TestScenarioFileIntegrity::test_scenario_structure PASSED
tests/eval/agents/documentation/test_integration.py::TestScenarioFileIntegrity::test_scenario_ids_unique PASSED
tests/eval/agents/documentation/test_integration.py::TestScenarioFileIntegrity::test_metric_references PASSED
```

**Total**: 5 integrity tests (all should PASS)

**Grand Total**: 20 tests (12 scenarios + 3 workflows + 5 integrity)

## Troubleshooting

### Test Failures

**Symptom**: `AssertionError: Score 0.73 < threshold 0.85`

**Cause**: Mock response doesn't meet metric criteria

**Solution**:
1. Review metric breakdown in failure output
2. Check which component failed (active voice, jargon, examples, conciseness)
3. Update mock response in `documentation_scenarios.json`
4. Re-run test to verify fix

### Import Errors

**Symptom**: `ModuleNotFoundError: No module named 'tests.eval.metrics.documentation'`

**Solution**:
```bash
# Ensure you're in project root
cd /Users/masa/Projects/claude-mpm

# Install dependencies
pip install -e .

# Verify import
python -c "from tests.eval.metrics.documentation import ClarityStandardsMetric"
```

### Scenario File Not Found

**Symptom**: `FileNotFoundError: Scenarios file not found`

**Solution**:
```bash
# Verify scenarios file exists
ls -la tests/eval/scenarios/documentation/documentation_scenarios.json

# If missing, check git status
git status tests/eval/scenarios/documentation/
```

### Metric Threshold Adjustments

If tests consistently fail due to threshold being too strict:

1. **Review metric scoring**: Check `_score_*` methods in metric implementation
2. **Adjust threshold**: Lower threshold if metric is too strict (e.g., 0.85 → 0.80)
3. **Improve mock responses**: Enhance compliant examples to meet higher bar
4. **Document rationale**: Note why threshold was adjusted in commit message

## Related Files

- **Scenarios**: `tests/eval/scenarios/documentation/documentation_scenarios.json`
- **Metrics**:
  - `tests/eval/metrics/documentation/clarity_standards_metric.py`
  - `tests/eval/metrics/documentation/audience_awareness_metric.py`
- **Metric Tests**:
  - `tests/eval/metrics/documentation/test_clarity_standards.py`
  - `tests/eval/metrics/documentation/test_audience_awareness.py`

## References

- **DeepEval Documentation**: https://docs.confident-ai.com/
- **Sprint 6 Issue**: #112 (Documentation Agent test harness)
- **DeepEval Phase 2 Plan**: `docs/research/deepeval-phase2-implementation-plan.md`
- **Ops Agent Test Harness**: `tests/eval/agents/ops/test_integration.py` (reference implementation)

## Contributing

When adding new scenarios:

1. **Add scenario to JSON**: Update `documentation_scenarios.json` with new scenario
2. **Add test case**: Parametrize existing test or create new test class
3. **Verify compliance**: Ensure compliant response passes metric threshold
4. **Update documentation**: Add scenario to this README
5. **Run full suite**: `pytest tests/eval/agents/documentation/ -v`

## Metrics Development

To modify metric scoring:

1. **Update metric implementation**: Edit `clarity_standards_metric.py` or `audience_awareness_metric.py`
2. **Add metric unit tests**: Update `test_clarity_standards.py` or `test_audience_awareness.py`
3. **Re-run integration tests**: Verify no regressions
4. **Document changes**: Update metric docstrings and this README

---

**Status**: ✅ Complete (Sprint 6 #112)
**Last Updated**: December 6, 2025
**Test Coverage**: 12 scenarios + 3 workflows + 5 integrity checks = 20 tests
