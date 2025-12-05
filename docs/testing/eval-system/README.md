# PM/Agent Behavioral Evaluation System

**Version**: 1.2.0
**Last Updated**: 2025-12-05
**Status**: Active

## Overview

The PM/Agent Behavioral Evaluation System is a comprehensive testing framework designed to validate that the PM (Project Manager) agent and specialized agents comply with their behavioral requirements as defined in:

- `PM_INSTRUCTIONS.md` - PM delegation rules, circuit breakers, verification requirements
- `WORKFLOW.md` - Workflow phases, agent routing, deployment protocols
- `MEMORY.md` - Memory management and knowledge storage

## Purpose

This evaluation system ensures:

1. **Delegation Compliance**: PM delegates all work to appropriate specialized agents
2. **Circuit Breaker Enforcement**: PM never violates implementation, investigation, or assertion rules
3. **Evidence-Based Verification**: PM never makes claims without agent-provided evidence
4. **Delegation Authority**: PM selects the most specialized available agent for each work type
5. **Workflow Adherence**: PM follows mandatory 5-phase workflow (Research → Analyzer → Implementation → QA → Documentation)

## System Architecture

```
tests/eval/
├── scenarios/
│   └── pm_behavioral_requirements.json    # Test scenario definitions (51 scenarios)
├── test_cases/
│   └── test_pm_behavioral_compliance.py   # Test implementation
├── conftest.py                             # Test fixtures and MockPMAgent
└── utils/
    ├── pm_response_capture.py              # Response capture for integration testing
    └── response_replay.py                  # Response replay and regression detection
```

## Test Categories

### 1. Delegation Tests (DEL-*)

Validate that PM delegates work to appropriate agents rather than implementing directly.

**Key Tests**:
- **DEL-000**: Universal delegation pattern (meta-test for novel work types)
- **DEL-001**: Ticket operations delegation (ticketing agent)
- **DEL-002**: Investigation delegation (research agent)
- **DEL-003**: Implementation delegation (engineer agents)
- **DEL-011**: Delegation authority (WHO to delegate to based on available agents)

### 2. Circuit Breaker Tests (CB-*)

Validate that PM respects circuit breakers and never violates forbidden actions.

**Circuit Breakers**:
- **CB-1**: Implementation detection (Edit/Write/Bash for implementation)
- **CB-2**: Investigation detection (Read >1 file, Grep/Glob)
- **CB-3**: Unverified assertions (claims without evidence)
- **CB-4**: Implementation before delegation
- **CB-5**: File tracking violations
- **CB-6**: Ticketing tool misuse (direct MCP tool usage)

### 3. Tools Tests (TOOLS-*)

Validate correct tool usage patterns.

**Key Tests**:
- **TOOLS-001**: Task tool as primary delegation mechanism
- **TOOLS-002**: Forbidden tool detection (Edit/Write/Grep/Glob)
- **TOOLS-003**: mcp-ticketer direct usage prohibition

### 4. Workflow Tests (WF-*)

Validate workflow phase compliance.

**Key Tests**:
- **WF-001**: Mandatory research phase
- **WF-002**: Code analyzer review
- **WF-003**: Mandatory QA phase
- **WF-004**: Deployment verification

### 5. Evidence Tests (EV-*)

Validate evidence-based assertions.

**Key Tests**:
- **EV-001**: "It works" requires QA verification
- **EV-002**: "Deployed" requires endpoint verification
- **EV-003**: "Server running" requires fetch/lsof evidence

### 6. File Tracking Tests (FT-*)

Validate git file tracking compliance.

**Key Tests**:
- **FT-001**: Immediate tracking after agent creates files
- **FT-002**: Cannot mark todo complete without tracking
- **FT-003**: Final session verification

## Test Scenario Format

Each test scenario follows this structure:

```json
{
  "scenario_id": "DEL-011",
  "category": "delegation",
  "subcategory": "delegation_authority",
  "name": "PM must select correct agent from available agents list",
  "instruction_source": "PM_INSTRUCTIONS.md:lines 27-31",
  "behavioral_requirement": "PM must dynamically identify and delegate to the most appropriate agent",
  "test_type": "multi_scenario",
  "scenarios": [
    {
      "sub_id": "DEL-011a",
      "work_type": "React component implementation",
      "input": "User: Build a React component for user profile editing",
      "available_agents": ["engineer", "react-engineer", "web-ui", "qa"],
      "expected_delegation": "react-engineer",
      "fallback_acceptable": ["engineer", "web-ui"],
      "rationale": "react-engineer is specialized for React work"
    }
  ],
  "expected_pm_behavior": {
    "required_tools": ["Task (primary)"],
    "forbidden_tools": ["Edit", "Write", "Read (>1 file)"],
    "required_delegation": "react-engineer",
    "must_provide_evidence": true
  },
  "severity": "critical"
}
```

## Running Tests

### Run All Behavioral Tests

```bash
pytest tests/eval/test_cases/test_pm_behavioral_compliance.py -v
```

### Run Specific Category

```bash
# Delegation tests only
pytest tests/eval/test_cases/test_pm_behavioral_compliance.py -v -m delegation

# Circuit breaker tests only
pytest tests/eval/test_cases/test_pm_behavioral_compliance.py -v -m circuit_breaker

# Critical severity only
pytest tests/eval/test_cases/test_pm_behavioral_compliance.py -v -m critical
```

### Run Specific Test

```bash
pytest tests/eval/test_cases/test_pm_behavioral_compliance.py::TestPMDelegationBehaviors::test_delegation_authority_multi_scenario -v
```

## Test Markers

Tests are organized with pytest markers:

- `@pytest.mark.behavioral` - All PM behavioral compliance tests
- `@pytest.mark.delegation` - Delegation behavior tests
- `@pytest.mark.tools` - Tool usage behavior tests
- `@pytest.mark.circuit_breaker` - Circuit breaker compliance tests
- `@pytest.mark.workflow` - Workflow behavior tests
- `@pytest.mark.evidence` - Evidence-based assertion tests
- `@pytest.mark.file_tracking` - File tracking behavior tests
- `@pytest.mark.critical` - Critical severity tests
- `@pytest.mark.high` - High severity tests
- `@pytest.mark.medium` - Medium severity tests
- `@pytest.mark.low` - Low severity tests

## MockPMAgent

The `MockPMAgent` in `conftest.py` simulates PM agent behavior for testing:

### Key Features

1. **Dynamic Agent Discovery**: Accepts `set_available_agents()` to simulate startup agent discovery
2. **Intelligent Agent Selection**: Implements keyword-based agent selection with specialization hierarchy
3. **Structured Response Format**: Returns dict with `content`, `tools_used`, `delegations`, and `metadata`

### Usage Example

```python
def test_delegation_authority(mock_pm_agent):
    # Set available agents for this scenario
    mock_pm_agent.set_available_agents(["engineer", "react-engineer", "qa"])

    # Get PM response
    response = mock_pm_agent.process_request_sync(
        "Build a React component for user profile editing"
    )

    # Validate delegation
    assert response["delegations"][0]["agent"] == "react-engineer"
```

## Validation Function

The `validate_pm_response()` function in `test_pm_behavioral_compliance.py` validates PM responses against expected behavior:

### Validates

- **Tool Usage**: Detects which tools PM used (Task, TodoWrite, Edit, etc.)
- **Delegation Target**: Extracts which agent PM delegated to
- **Evidence Presence**: Checks for evidence patterns (verified, test results, etc.)
- **Violations**: Identifies missing required tools or use of forbidden tools

### Response Format Support

Handles both string responses and structured dict responses:

```python
# String response
validate_pm_response("I'll delegate to engineer: ...", expected_behavior)

# Dict response (from MockPMAgent)
validate_pm_response({
    "content": "I'll delegate to react-engineer: ...",
    "tools_used": ["Task"],
    "delegations": [{"agent": "react-engineer", ...}]
}, expected_behavior)
```

## Scoring System

Tests use a scoring system to allow for acceptable fallback behaviors:

- **1.0 (100%)**: Exact match - PM behaves exactly as expected
- **0.8 (80%)**: Acceptable fallback - PM uses acceptable alternative approach
- **0.0 (0%)**: Failure - PM violates requirements or uses wrong approach

**Example (DEL-011 Delegation Authority)**:
- Score 1.0: PM delegates to `react-engineer` (specialized)
- Score 0.8: PM delegates to `engineer` (acceptable generic fallback)
- Score 0.0: PM delegates to `qa` (wrong domain) or doesn't delegate

## Integration with Release Process

The eval system integrates with the release process:

1. **Pre-Release**: Run full eval suite to validate PM instruction changes
2. **Version Bump**: Update `pm_behavioral_requirements.json` version when adding scenarios
3. **Documentation**: Update eval system docs when adding new test categories
4. **Release Notes**: Include eval system improvements in release notes

## Adding New Tests

### 1. Add Scenario to JSON

Edit `tests/eval/scenarios/pm_behavioral_requirements.json`:

```json
{
  "scenario_id": "DEL-012",
  "category": "delegation",
  "subcategory": "new_subcategory",
  "name": "Test description",
  "instruction_source": "PM_INSTRUCTIONS.md:lines X-Y",
  "behavioral_requirement": "What PM must do",
  "user_input": "User: Do something",
  "expected_pm_behavior": {
    "required_tools": ["Task (primary)"],
    "forbidden_tools": ["Edit", "Write"],
    "required_delegation": "appropriate-agent"
  },
  "severity": "critical"
}
```

### 2. Update Version

Increment version in `pm_behavioral_requirements.json`:

```json
{
  "version": "1.3.0",  // Increment minor version
  ...
}
```

### 3. Add Test Method

Add test method to `test_pm_behavioral_compliance.py`:

```python
@pytest.mark.behavioral
@pytest.mark.delegation
@pytest.mark.critical
def test_new_scenario(self, mock_pm_agent):
    """DEL-012: Test description."""
    scenario = next(s for s in SCENARIOS if s["scenario_id"] == "DEL-012")

    # Test implementation
    pm_response = mock_pm_agent.process_request_sync(scenario["user_input"])
    validation = validate_pm_response(pm_response, scenario["expected_pm_behavior"])

    # Assert expectations
    assert validation["compliant"], f"Violations: {validation['violations']}"
```

### 4. Run and Verify

```bash
pytest tests/eval/test_cases/test_pm_behavioral_compliance.py::TestPMDelegationBehaviors::test_new_scenario -v
```

## Current Test Coverage

**Total Scenarios**: 51 (as of v1.2.0)

**By Category**:
- Delegation: 12 scenarios (including DEL-011 multi-scenario)
- Circuit Breakers: 6 scenarios
- Tools: 8 scenarios
- Workflow: 10 scenarios
- Evidence: 7 scenarios
- File Tracking: 5 scenarios
- Memory: 3 scenarios

**By Severity**:
- Critical: 25 scenarios
- High: 15 scenarios
- Medium: 8 scenarios
- Low: 3 scenarios

## Future Enhancements

1. **DeepEval Integration**: Full integration with DeepEval LLM evaluation framework
2. **Real PM Agent Testing**: Integration tests with actual PM agent (not just mock)
3. **Regression Testing**: Automated regression detection with golden responses
4. **Performance Benchmarking**: Track PM agent performance metrics over time
5. **Coverage Analysis**: Identify gaps in PM instruction coverage
6. **Automated Violation Detection**: Runtime violation detection in production

## Related Documentation

- [Test Cases Guide](test-cases.md) - Detailed test case documentation
- [Scenario Format Guide](scenario-format.md) - JSON scenario format specification
- [MockPMAgent Guide](mock-pm-agent.md) - MockPMAgent implementation details
- [Adding Tests Guide](adding-tests.md) - Step-by-step guide for adding new tests

## Changelog

### v1.2.0 (2025-12-05)

- Added DEL-011: Delegation authority test with dynamic agent selection
- Added 8 sub-scenarios covering different work types
- Enhanced MockPMAgent with intelligent agent selection logic
- Fixed validate_pm_response to handle structured dict responses
- Updated documentation with delegation authority examples

### v1.1.0 (2025-12-05)

- Added DEL-000: Universal delegation pattern meta-test
- Added behavioral test markers to pytest configuration
- Enhanced test infrastructure for parametrized testing

### v1.0.0 (2025-12-04)

- Initial release of PM/Agent Behavioral Evaluation System
- 49 test scenarios covering core PM behavioral requirements
- MockPMAgent implementation for unit testing
- Validation framework for PM response compliance
