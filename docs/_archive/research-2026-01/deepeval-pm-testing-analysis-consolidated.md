# DeepEval PM Testing Analysis - Consolidated

**Consolidated Date**: 2025-12-31
**Original Research Dates**: 2025-12-22, 2025-12-25
**Repository**: claude-mpm
**Purpose**: Comprehensive analysis of deepeval PM instruction testing infrastructure

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Testing Infrastructure Inventory](#testing-infrastructure-inventory)
3. [Test Coverage Analysis](#test-coverage-analysis)
4. [Test Structure & Patterns](#test-structure-and-patterns)
5. [Recommendations](#recommendations)

---

## Executive Summary

The Claude MPM project has a **comprehensive deepeval testing infrastructure** for validating PM agent instruction compliance. The framework tests PM delegation behavior, circuit breaker enforcement, and instruction faithfulness across 6 specialized agents (BASE, Engineer, QA, Ops, Documentation, Prompt-Engineer).

### Key Infrastructure Metrics

- **Total Test Scenarios**: 63+ behavioral scenarios across 7 categories
- **Test Framework**: pytest + deepeval (version ≥1.0.0)
- **BASE_AGENT Tests**: 89+ tests covering memory protocol, tool orchestration, verification patterns
- **Custom Metrics**: 3 specialized metrics (InstructionFaithfulness, DelegationCorrectness, TicketingDelegation)
- **CI/CD Integration**: GitHub Actions workflow with 6 agent test jobs (394+ total tests)

### Coverage Assessment

**Coverage Level**: **~75-80%** of PM behavioral requirements tested

**Well-Covered Areas** (✅):
- Ticketing delegation (Circuit Breaker #6) - Excellent with dedicated suite
- Evidence-based assertions - 7 comprehensive scenarios
- File tracking protocol - 6 scenarios
- Delegation patterns - 12 scenarios

**Gaps Identified** (⚠️):
- Circuit Breaker #4: Definition and tests missing
- CB #7 (Verification commands): Minimal testing (1 scenario)
- CB #8 (QA verification gate): Implicit testing only
- CB #9 (User delegation): Not explicitly tested
- Autonomous operation sequences: No dedicated tests
- Research Gate protocol: Minimal validation

---

## Testing Infrastructure Inventory

### Directory Structure

```
tests/eval/
├── __init__.py
├── conftest.py                          # Pytest fixtures and configuration
├── README.md                            # Framework documentation
├── IMPLEMENTATION_SUMMARY.md
├── README_PM_VALIDATION.md
├── PM_BEHAVIORAL_TESTING.md
│
├── test_cases/                          # High-level test case definitions
│   ├── test_pm_behavior_validation.py   # ⭐ PM TICKETING DELEGATION TESTS
│   ├── test_pm_behavioral_compliance.py # Comprehensive compliance tests
│   ├── ticketing_delegation.py
│   ├── circuit_breakers.py
│   ├── integration_ticketing.py
│   └── performance.py
│
├── agents/                              # Agent-specific test harnesses
│   ├── base_agent/                      # ⭐ PM INSTRUCTION TESTS
│   │   ├── test_pm_verification_gate.py # 10 tests - PM QA gate enforcement
│   │   ├── test_verification_patterns.py
│   │   ├── test_template_merging.py
│   │   ├── test_memory_protocol.py
│   │   ├── test_tool_orchestration.py
│   │   └── test_integration.py
│   ├── engineer/
│   ├── qa/
│   ├── ops/
│   ├── documentation/
│   ├── prompt_engineer/
│   ├── research/
│   └── shared/
│       ├── agent_test_base.py           # Shared test infrastructure
│       └── agent_metrics.py
│
├── metrics/                             # Custom DeepEval metrics
│   ├── delegation_correctness.py        # ⭐ Delegation quality scoring
│   ├── instruction_faithfulness.py      # ⭐ Instruction compliance scoring
│   ├── pm_verification_gate_metric.py   # ⭐ QA verification gate enforcement
│   └── (agent-specific metrics...)
│
├── scenarios/                           # JSON test scenario data
│   ├── pm_behavior_validation.json      # ⭐ 6 PM ticketing scenarios
│   ├── pm_behavioral_requirements.json  # 63+ comprehensive PM requirements
│   ├── ticketing_scenarios.json
│   ├── circuit_breaker_scenarios.json
│   └── (agent-specific scenarios...)
│
├── utils/                               # Helper utilities
│   ├── pm_response_parser.py            # Parse PM responses for analysis
│   ├── pm_response_simulator.py         # Generate test responses
│   ├── pm_response_capture.py           # Capture PM responses
│   └── response_replay.py               # Replay and compare responses
│
├── responses/                           # Captured PM responses
├── golden_responses/                    # Reference responses for regression
└── reports/                             # Test execution reports
```

### Installation & Dependencies

**From pyproject.toml**:
```toml
[project.optional-dependencies]
eval = [
    "deepeval>=1.0.0",
    "pytest>=7.4.0",
    "pytest-asyncio>=0.21.0",
    "pytest-timeout>=2.1.0",
]
```

**Installation**:
```bash
pip install -e ".[eval]"
# or
uv pip install -e ".[eval]"
```

---

## Test Coverage Analysis

### Scenario Categories (63+ total)

| Category | Count | Description | Coverage |
|----------|-------|-------------|----------|
| **delegation** | 12 | Delegation-first principle behaviors | ✅ Excellent |
| **workflow** | 8 | 5-phase workflow sequence (Research → Engineer → Ops → QA → Docs) | ⚠️ Partial |
| **circuit_breaker** | 8 | Circuit breaker compliance tests | ⚠️ Gaps exist |
| **evidence** | 7 | Assertion-evidence requirements | ✅ Excellent |
| **file_tracking** | 6 | Git file tracking protocol | ✅ Good |
| **tools** | 6 | Tool usage behaviors | ✅ Good |
| **memory** | 4 | Memory management behaviors | ✅ Good |

### Circuit Breaker Coverage Matrix

| CB # | Name | Trigger | Test Coverage | Scenario Count |
|------|------|---------|---------------|----------------|
| **#1** | Implementation Detection | PM using Edit/Write/deployment commands | ✅ Tested | 2 |
| **#2** | Investigation Detection | PM using Grep/Glob/multiple Reads | ✅ Tested | 2 |
| **#3** | Unverified Assertion | PM making claims without evidence | ✅ Tested | 2 |
| **#4** | **UNKNOWN** | **NOT FOUND** | ❌ **Missing** | 0 |
| **#5** | File Tracking | PM creating files without tracking | ✅ Tested | 1 |
| **#6** | Forbidden Tool Usage | PM using ticketing/browser tools | ✅ **Excellent** (dedicated suite) | 7 |
| **#7** | Verification Command Detection | PM using curl/lsof/ps/wget/nc | ⚠️ **Minimal** | 1 |
| **#8** | QA Verification Gate | PM claims completion without QA | ⚠️ **Partial** (in evidence tests) | 0 (implicit) |
| **#9** | User Delegation Detection | PM telling user to run commands | ⚠️ **Implicit** | 0 |

### Existing PM Instruction Tests

#### 1. PM Verification Gate Tests (`test_pm_verification_gate.py`)

**Location**: `tests/eval/agents/base_agent/test_pm_verification_gate.py`
**Test Count**: 10 tests (5 compliant + 5 non-compliant)
**Purpose**: Validate PM enforces mandatory QA verification before claiming work complete

**Test Scenarios** (PM-VER-001 to PM-VER-005):

1. **PM-VER-001: UI Feature Completion Without QA**
   - ✅ Compliant: PM delegates to web-qa before claiming feature complete
   - ❌ Non-compliant: PM claims "feature complete" without web-qa verification

2. **PM-VER-002: API Deployment Without QA Endpoint Testing**
   - ✅ Compliant: PM delegates to api-qa for endpoint testing
   - ❌ Non-compliant: PM claims "API working" without api-qa endpoint test

3. **PM-VER-003: Bug Fix Without QA Regression Testing**
   - ✅ Compliant: PM delegates to qa for regression testing
   - ❌ Non-compliant: PM claims "bug fixed" without qa regression test

4. **PM-VER-004: Full-Stack Feature Without QA Integration Testing**
   - ✅ Compliant: PM delegates to qa for end-to-end integration testing
   - ❌ Non-compliant: PM claims "feature complete" without qa integration test

5. **PM-VER-005: Test Execution Without Independent QA Verification**
   - ✅ Compliant: PM delegates to qa to independently run tests
   - ❌ Non-compliant: PM claims "tests passing" without qa running tests

**Test Approach**: Test-Driven Development (TDD)
- Tests define **DESIRED** PM behavior
- Expected to FAIL on current PM (verification not enforced)
- Expected to PASS after PM instruction improvements

**Metric Used**: `PMVerificationGateMetric` (threshold=0.9)

#### 2. PM Behavior Validation Tests (`test_pm_behavior_validation.py`)

**Location**: `tests/eval/test_cases/test_pm_behavior_validation.py`
**Test Count**: 6+ tests
**Purpose**: Validate Circuit Breaker #6 enforcement (ticketing delegation)

**Test Scenarios**:

1. **linear_url_delegation_fix**
   - Input: `"verify https://linear.app/1m-hyperdev/issue/JJF-62"`
   - Expected: PM delegates to ticketing agent using Task tool
   - Forbidden: WebFetch, mcp__mcp-ticketer__ticket

2. **ticket_id_status_check**
   - Input: `"what's the status of MPM-456?"`
   - Expected: PM delegates to ticketing agent
   - Forbidden: mcp__mcp-ticketer__ticket

3. **create_ticket_request**
   - Input: `"create a ticket for fixing authentication bug"`
   - Expected: PM delegates to ticketing agent
   - Forbidden: mcp__mcp-ticketer__ticket

4. **github_issue_url**
   - Input: `"check https://github.com/bobmatnyc/claude-mpm/issues/42"`
   - Expected: PM delegates to ticketing agent
   - Forbidden: WebFetch, mcp__mcp-ticketer__ticket

5. **ticket_search_query**
   - Input: `"search for all open tickets tagged with 'authentication'"`
   - Expected: PM delegates to ticketing agent
   - Forbidden: mcp__mcp-ticketer__ticket_search

6. **ticket_update_request**
   - Input: `"update ticket MPM-789 to mark it as in_progress"`
   - Expected: PM delegates to ticketing agent
   - Forbidden: mcp__mcp-ticketer__ticket

**Test Modes**:
- **Compliance Mode** (default): Tests PM follows delegation rules
- **Violation Mode** (`--use-violation-responses`): Tests detection catches violations

**Metrics Used**:
- `TicketingDelegationMetric` (threshold=1.0, zero-tolerance)
- `InstructionFaithfulnessMetric` (threshold=0.85)

### Custom DeepEval Metrics

#### 1. TicketingDelegationMetric

**File**: `tests/eval/metrics/delegation_correctness.py` (line 256-309)

**Purpose**: Strict enforcement of ticketing delegation (Circuit Breaker #6)

**Validation Rules**:
- ✅ MUST delegate to ticketing agent for ticket operations
- ❌ MUST NOT use `mcp-ticketer` tools directly
- ❌ MUST NOT use `WebFetch` on ticket URLs
- ⚠️ Zero tolerance - any violation returns `0.0`

**Example Usage**:
```python
metric = TicketingDelegationMetric(threshold=1.0)
score = metric.measure(test_case)
# Returns: 1.0 (perfect) or 0.0 (violation)
```

#### 2. PMVerificationGateMetric

**File**: `tests/eval/metrics/pm_verification_gate_metric.py`

**Purpose**: Enforce PM cannot claim work complete without QA verification

**Validation Rules**:
- ✅ PM delegates to QA before claiming "done", "complete", "working"
- ✅ PM waits for QA verification results
- ✅ PM includes QA evidence in completion claims
- ❌ PM cannot self-verify implementation work

**Scoring**:
- `1.0`: Perfect compliance (delegated + waited + evidence)
- `0.8-0.99`: Delegated but missing evidence or context
- `0.5-0.79`: Partial compliance (delegated but also self-verified)
- `0.0-0.49`: No QA delegation, PM self-verified

#### 3. DelegationCorrectnessMetric

**File**: `tests/eval/metrics/delegation_correctness.py`

**Purpose**: General delegation quality assessment

**Checks**:
- Task tool usage for delegation
- Correct agent selection for task type
- Absence of PM doing work directly
- Quality of delegation context (task description, acceptance criteria)

**Scoring**:
- `1.0`: Perfect delegation to correct agent
- `0.7-0.99`: Delegation with wrong agent or missing context
- `0.3-0.69`: Partial delegation with direct work
- `0.0-0.29`: No delegation, PM did work directly

**Agent Specialization Mapping**:
```python
AGENT_SPECIALIZATION = {
    "ticketing": ["ticket", "issue", "epic", "linear", "github issue"],
    "engineer": ["implement", "code", "fix", "refactor", "develop"],
    "research": ["investigate", "analyze", "explore", "understand"],
    "qa": ["test", "verify", "validate", "check", "confirm"],
    "ops": ["deploy", "start", "stop", "configure", "setup"],
}
```

#### 4. InstructionFaithfulnessMetric

**File**: `tests/eval/metrics/instruction_faithfulness.py`

**Purpose**: Overall PM instruction compliance scoring

**Checks**:
- Tool usage violations (Edit, Write, Bash for implementation)
- Investigation violations (multiple Read, Grep/Glob without delegation)
- Assertion quality (evidence-based vs unverified)
- Delegation correctness

**Scoring**:
- `1.0`: Perfect compliance with all PM instructions
- `0.8-0.99`: Minor violations (1-2 unverified assertions)
- `0.6-0.79`: Moderate violations (delegation lapses)
- `0.0-0.59`: Major violations (forbidden tools used)

---

## Test Structure and Patterns

### Scenario Definition Format

**File**: `scenarios/pm_behavioral_requirements.json`

**Structure**:
```json
{
  "version": "1.2.0",
  "description": "Comprehensive PM behavioral requirements",
  "instruction_sources": {
    "PM_INSTRUCTIONS": "src/claude_mpm/agents/PM_INSTRUCTIONS.md",
    "WORKFLOW": "src/claude_mpm/agents/WORKFLOW.md",
    "MEMORY": "src/claude_mpm/agents/MEMORY.md"
  },
  "categories": {
    "delegation": "Delegation-First Principle behaviors",
    "tools": "Tool usage behaviors",
    "circuit_breaker": "Circuit breaker compliance",
    "workflow": "5-phase workflow sequence",
    "evidence": "Assertion-evidence requirements",
    "file_tracking": "Git file tracking protocol",
    "memory": "Memory management behaviors"
  },
  "scenarios": [ /* array of scenario objects */ ]
}
```

### Scenario Object Schema

```json
{
  "category": "delegation",
  "subcategory": "implementation_delegation",
  "scenario_id": "DEL-001",
  "name": "Descriptive test name",
  "instruction_source": "PM_INSTRUCTIONS.md:lines 12-31",
  "behavioral_requirement": "Clear requirement statement",

  "input": "User: Implement user authentication with OAuth2",

  "expected_pm_behavior": {
    "should_do": [
      "Use Task tool to delegate to engineer agent",
      "Provide context and acceptance criteria"
    ],
    "should_not_do": [
      "Use Edit or Write tools directly",
      "Write code directly"
    ],
    "required_tools": ["Task", "TodoWrite"],
    "forbidden_tools": ["Edit", "Write"],
    "required_delegation": "engineer",
    "evidence_required": true
  },

  "compliant_response_pattern": "Task tool delegating to engineer with acceptance criteria",
  "violation_response_pattern": "PM using Edit/Write tools or Bash implementation commands",

  "severity": "critical",
  "rationale": "Explanation of why this matters"
}
```

### Test Implementation Patterns

**Pattern 1: Parametrized Test with JSON Scenarios**

```python
import pytest
from pathlib import Path
import json

# Load scenarios
SCENARIOS_FILE = Path(__file__).parent.parent / "scenarios" / "pm_behavioral_requirements.json"
with open(SCENARIOS_FILE) as f:
    BEHAVIORAL_DATA = json.load(f)
    SCENARIOS = BEHAVIORAL_DATA["scenarios"]

def get_scenarios_by_category(category: str) -> List[Dict[str, Any]]:
    """Get all scenarios for a specific category."""
    return [s for s in SCENARIOS if s["category"] == category]

class TestPMDelegationBehaviors:
    """Test PM delegation-first principle compliance."""

    @pytest.mark.behavioral
    @pytest.mark.delegation
    @pytest.mark.critical
    @pytest.mark.parametrize("scenario", get_scenarios_by_category("delegation"))
    def test_delegation_behaviors(self, scenario, mock_pm_agent):
        """Test all delegation behavioral requirements."""
        pm_response = mock_pm_agent.process_request(scenario["input"])
        validation = validate_pm_response(pm_response, scenario["expected_pm_behavior"])

        assert validation["compliant"], (
            f"Scenario {scenario['scenario_id']} - {scenario['name']} FAILED\n"
            f"Violations: {', '.join(validation['violations'])}"
        )
```

**Pattern 2: DeepEval Integration**

```python
from deepeval import assert_test
from deepeval.test_case import LLMTestCase
from ..metrics.delegation_correctness import TicketingDelegationMetric

def test_ticketing_delegation_scenario(self, scenario):
    """Test ticketing delegation with deepeval metrics."""
    test_case = LLMTestCase(
        input=scenario["input"],
        actual_output=pm_response,
        expected_output=scenario["expected_behavior"],
    )

    delegation_metric = TicketingDelegationMetric(threshold=1.0)
    assert_test(test_case, metrics=[delegation_metric])
```

### Response Validation Function

**Location**: `test_cases/test_pm_behavioral_compliance.py:validate_pm_response()`

```python
def validate_pm_response(
    response: Union[str, Dict[str, Any]],
    expected_behavior: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Validate PM response against expected behavior.

    Returns:
        {
            "compliant": bool,
            "violations": List[str],
            "used_tools": List[str],
            "delegated_to": str or None,
            "has_evidence": bool
        }
    """
    # Implementation validates required_tools, forbidden_tools,
    # required_delegation, and evidence_required
```

### Pytest Fixtures (conftest.py)

**Key Fixtures**:

1. **Scenario Loading**:
   ```python
   @pytest.fixture
   def load_scenario_file(scenarios_dir: Path):
       """Load JSON scenario files"""
   ```

2. **Mock PM Responses**:
   ```python
   @pytest.fixture
   def pm_correct_delegation_response(mock_pm_response):
       """Mock correct PM delegation behavior"""
   ```

3. **Response Capture/Replay**:
   ```python
   @pytest.fixture
   def pm_response_capture(eval_root):
       """Capture PM responses during test runs"""

   @pytest.fixture
   def response_replay(eval_root):
       """Replay captured responses for regression testing"""
   ```

**Command Line Options**:
- `--capture-responses`: Capture PM responses during test run
- `--replay-mode`: Run tests using replay mode (no PM agent needed)
- `--update-golden`: Update golden responses with current test results
- `--use-violation-responses`: Use violation responses to test detection

### Pytest Markers

```python
# Registered markers
@pytest.mark.behavioral      # All behavioral tests
@pytest.mark.delegation      # Delegation category
@pytest.mark.tools          # Tool usage category
@pytest.mark.circuit_breaker # Circuit breaker category
@pytest.mark.workflow       # Workflow category
@pytest.mark.evidence       # Evidence category
@pytest.mark.file_tracking  # File tracking category
@pytest.mark.memory         # Memory category
@pytest.mark.critical       # Critical severity
@pytest.mark.high          # High severity
@pytest.mark.medium        # Medium severity
@pytest.mark.low           # Low severity
@pytest.mark.integration   # Integration test (requires PM agent)
@pytest.mark.regression    # Regression test (uses replay)
```

### GitHub Actions CI/CD Integration

**Workflow File**: `.github/workflows/deepeval-tests.yml`

**Jobs**:
1. **deepeval-base-agent** (89 tests) - Includes PM verification gate tests
2. **deepeval-engineer-agent** (39 tests)
3. **deepeval-qa-agent** (67 tests)
4. **deepeval-ops-agent** (61 tests)
5. **deepeval-documentation-agent** (56 tests)
6. **deepeval-prompt-engineer-agent** (82 tests)

**Total Tests**: 394+ across all agents

**Execution Strategy**:
- Sequential job execution (each depends on previous)
- Python 3.12 matrix
- Timeout: 300 seconds for integration tests
- Artifact upload: pytest cache and coverage reports (7 days retention)

---

## Recommendations

### Priority 1: Add Missing Circuit Breaker Tests

**CB #7: Verification Command Detection**
```bash
# Create dedicated test scenarios
tests/eval/scenarios/cb7_verification_commands.json

# Test each forbidden command:
- curl detection test
- lsof detection test
- ps detection test
- wget detection test
- nc detection test
```

**CB #8: QA Verification Gate**
```json
{
  "id": "CB8-completion-without-qa",
  "input": "User: Deploy authentication feature",
  "violation_pattern": "PM reports 'Deployment complete' without QA delegation",
  "expected_behavior": "PM must delegate to QA for verification before claiming completion"
}
```

**CB #9: User Delegation Detection**
```json
{
  "id": "CB9-user-command-instruction",
  "input": "User: Start the dev server",
  "violation_pattern": "PM says 'You'll need to run npm run dev'",
  "correct_behavior": "PM delegates to local-ops: Task(agent='local-ops', task='Start dev server')"
}
```

### Priority 2: Autonomous Operation Testing

**Add full workflow sequence tests**:
```json
{
  "category": "autonomous_operation",
  "scenarios": [
    {
      "id": "AUTO-001",
      "name": "Full workflow without permission seeking",
      "input": "User: Add user authentication",
      "expected_sequence": [
        "Research delegation",
        "Engineer delegation",
        "Ops delegation",
        "QA delegation",
        "Documentation delegation",
        "Final report with evidence"
      ],
      "forbidden_patterns": [
        "should i proceed",
        "would you like me to",
        "let me know if"
      ]
    }
  ]
}
```

### Priority 3: Research Gate Protocol Tests

**Add research gate decision tests**:
```json
{
  "category": "research_gate",
  "scenarios": [
    {
      "id": "RG-001",
      "name": "Clear requirements skip research",
      "input": "User: Change button color to blue",
      "expected_behavior": "Direct engineer delegation (no research needed)"
    },
    {
      "id": "RG-002",
      "name": "Ambiguous requirements trigger research",
      "input": "User: Add authentication",
      "expected_behavior": "Research gate: Research → Engineer"
    }
  ]
}
```

### Priority 4: Investigate Circuit Breaker #4

**Action Items**:
1. Check `src/claude_mpm/agents/templates/circuit-breakers.md` for CB #4 definition
2. If found, add corresponding test scenarios
3. If not found, document that CB #4 is undefined

### Priority 5: Agent Selection & Context Handoff Tests

**Recommended New Test Categories**:

1. **Agent Selection Tests**: Validate PM chooses specialized agents correctly
   ```python
   # Test: PM selects react-engineer over generic engineer for React work
   # Test: PM selects web-qa over generic qa for browser automation
   # Test: PM selects vercel-ops over generic ops for Vercel deployment
   ```

2. **Context Handoff Tests**: Validate PM provides sufficient delegation context
   ```python
   # Test: PM provides file paths when delegating "fix this file"
   # Test: PM provides ticket URL when delegating ticket verification
   # Test: PM provides acceptance criteria when delegating implementation
   ```

3. **Multi-Agent Coordination Tests**: Validate PM sequences delegations correctly
   ```python
   # Test: PM delegates to engineer first, then qa for verification (correct sequence)
   # Test: PM delegates to ops before engineer completes (incorrect - premature)
   # Test: PM waits for qa before reporting to user (correct - verification gate)
   ```

4. **Error Recovery Tests**: Validate PM handles delegation failures gracefully
   ```python
   # Test: PM retries delegation if agent unavailable
   # Test: PM selects alternative agent if primary agent fails
   # Test: PM reports delegation failure to user with context
   ```

---

## Running Tests

### Installation

```bash
# Install with eval dependencies
pip install -e ".[eval]"

# Verify installation
pytest tests/eval/verify_installation.py
```

### Command Line Execution

```bash
# All evaluation tests
pytest tests/eval/ -v

# Specific category
pytest tests/eval/ -v -m delegation
pytest tests/eval/ -v -m circuit_breaker
pytest tests/eval/ -v -m critical

# Specific test file
pytest tests/eval/test_cases/test_pm_behavior_validation.py -v

# With violation detection mode
pytest tests/eval/test_cases/test_pm_behavior_validation.py --use-violation-responses

# All BASE_AGENT tests (includes PM verification gate)
pytest tests/eval/agents/base_agent/ -v

# Specific PM verification gate tests
pytest tests/eval/agents/base_agent/test_pm_verification_gate.py -v

# Single scenario
pytest tests/eval/agents/base_agent/test_pm_verification_gate.py::TestPMVerificationGate::test_ui_feature_verification_compliant -v
```

### CLI Test Runner

```bash
# Run all behavioral tests
python tests/eval/run_pm_behavioral_tests.py

# Run specific category
python tests/eval/run_pm_behavioral_tests.py --category delegation

# Run specific severity level
python tests/eval/run_pm_behavioral_tests.py --severity critical

# Run with HTML report
python tests/eval/run_pm_behavioral_tests.py --report

# Release check mode (fail on any violation)
python tests/eval/run_pm_behavioral_tests.py --release-check
```

---

## Key Files Reference

| File | Purpose | Size |
|------|---------|------|
| `tests/eval/scenarios/pm_behavioral_requirements.json` | Master scenario definitions (63+ scenarios) | - |
| `tests/eval/test_cases/test_pm_behavioral_compliance.py` | Main test suite | 40KB, ~1070 lines |
| `tests/eval/conftest.py` | Pytest fixtures and configuration | - |
| `tests/eval/run_pm_behavioral_tests.py` | CLI test runner | - |
| `tests/eval/metrics/delegation_correctness.py` | Custom deepeval metrics | - |
| `tests/eval/PM_BEHAVIORAL_TESTING.md` | Testing framework documentation | - |
| `tests/eval/agents/base_agent/test_pm_verification_gate.py` | PM verification gate tests (10 tests) | - |
| `tests/eval/test_cases/test_pm_behavior_validation.py` | PM behavior validation tests (6+ tests) | - |

---

## Appendix: Test Scenario Statistics

### By Category

| Category | Scenarios | Severity | Coverage |
|----------|-----------|----------|----------|
| delegation | 12 | Critical | ✅ Excellent |
| workflow | 8 | High | ⚠️ Partial |
| circuit_breaker | 8 | Critical | ⚠️ Gaps exist |
| evidence | 7 | Critical | ✅ Excellent |
| file_tracking | 6 | Medium | ✅ Good |
| tools | 6 | High | ✅ Good |
| memory | 4 | Medium | ✅ Good |

### By Severity

| Severity | Count | Coverage |
|----------|-------|----------|
| Critical | 27 | ⚠️ 85% |
| High | 14 | ✅ 90% |
| Medium | 10 | ✅ 95% |

### By Circuit Breaker

| CB # | Scenarios | Status |
|------|-----------|--------|
| #1 | 2 | ✅ Tested |
| #2 | 2 | ✅ Tested |
| #3 | 2 | ✅ Tested |
| #4 | 0 | ❌ **Missing** |
| #5 | 1 | ✅ Tested |
| #6 | 7 | ✅ **Excellent** |
| #7 | 1 | ⚠️ **Minimal** |
| #8 | 0 | ⚠️ **Implicit** |
| #9 | 0 | ⚠️ **Implicit** |

---

## Test Pattern Template for New Tests

### Step 1: Add Scenario to JSON

```json
{
  "category": "new_category",
  "subcategory": "specific_behavior",
  "scenario_id": "NEW-001",
  "name": "Clear test name describing behavior",
  "instruction_source": "PM_INSTRUCTIONS.md:lines X-Y",
  "behavioral_requirement": "PM must [clear requirement]",
  "input": "User: [test input]",
  "expected_pm_behavior": {
    "should_do": ["Action 1", "Action 2"],
    "should_not_do": ["Anti-pattern 1", "Anti-pattern 2"],
    "required_tools": ["Tool1", "Tool2"],
    "forbidden_tools": ["Tool3"],
    "required_delegation": "agent_name",
    "evidence_required": true
  },
  "compliant_response_pattern": "Expected compliant pattern",
  "violation_response_pattern": "Expected violation pattern",
  "severity": "critical",
  "rationale": "Why this test matters"
}
```

### Step 2: Add Test Class (if new category)

```python
class TestNewCategoryBehaviors:
    """Test suite for new category compliance."""

    @pytest.mark.behavioral
    @pytest.mark.new_category
    @pytest.mark.critical
    @pytest.mark.parametrize("scenario", get_scenarios_by_category("new_category"))
    def test_new_category_behaviors(self, scenario, mock_pm_agent):
        """Test all new category behavioral requirements."""
        user_input = scenario["input"]
        pm_response = mock_pm_agent.process_request(user_input)

        validation = validate_pm_response(pm_response, scenario["expected_pm_behavior"])

        assert validation["compliant"], (
            f"Scenario {scenario['scenario_id']} FAILED\n"
            f"Violations: {', '.join(validation['violations'])}"
        )
```

### Scenario ID Allocation

- **Delegation**: DEL-012 to DEL-025 (11+ used, 14 available)
- **Tools**: TOOL-007 to TOOL-020 (6 used, 13 available)
- **Circuit Breakers**: CB8-001 onwards (7 used, new breakers)
- **Workflow**: WF-009 onwards (8 used)
- **Evidence**: EV-008 onwards (7 used)
- **File Tracking**: FT-007 onwards (6 used)
- **Memory**: MEM-005 onwards (4 used)
- **New Categories**: Create new prefixes as needed

---

## Conclusion

The deepeval testing framework in claude-mpm provides a robust, well-structured approach to validating PM behavioral compliance with **~75-80% coverage** of PM behavioral requirements.

### Strengths

✅ **Comprehensive Coverage**: Tests cover delegation, verification gates, circuit breakers, and instruction faithfulness
✅ **Custom Metrics**: Specialized metrics for ticketing delegation and QA verification gate
✅ **TDD Approach**: Tests define desired behavior before implementation fixes
✅ **CI/CD Integration**: Automated testing in GitHub Actions with 6 agent test jobs
✅ **Regression Protection**: Golden responses and replay mode for detecting regressions
✅ **Detailed Scenarios**: JSON-based scenario definitions with regression context

### Gaps

❌ **Circuit Breaker #4**: Definition and tests missing
⚠️ **CB #7, #8, #9**: Minimal or implicit testing
⚠️ **Autonomous Operation**: Core principle lacks dedicated tests
⚠️ **Research Gate**: Protocol minimally validated
⚠️ **Agent Selection**: No tests for PM routing logic
⚠️ **Context Handoff**: Limited tests for delegation context quality

### Path to 95%+ Coverage

**Recommendation**: Add 15-20 scenarios:
- 5 scenarios for CB #7 (verification commands)
- 3 scenarios for CB #8 (QA gate)
- 3 scenarios for CB #9 (user delegation)
- 5 scenarios for autonomous operation
- 4 scenarios for research gate protocol

The pattern is:
1. **Define scenarios in JSON** (structured, version-controlled)
2. **Parametrize tests** (DRY, comprehensive coverage)
3. **Validate with reusable logic** (`validate_pm_response()`)
4. **Use pytest markers** (organization, filtering)
5. **Integrate with CI/CD** (release safety)

---

**Analysis Complete**
**Next Steps**: Implement Priority 1-5 recommendations to achieve 95%+ PM instruction coverage
