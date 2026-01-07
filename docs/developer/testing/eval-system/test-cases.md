# PM/Agent Eval System - Test Cases Guide

**Version**: 1.2.0
**Last Updated**: 2025-12-05

## Overview

This guide provides detailed documentation for all test cases in the PM/Agent Behavioral Evaluation System.

## Test Case Format

Each test case follows this structure:

```python
@pytest.mark.behavioral
@pytest.mark.{category}  # delegation, circuit_breaker, tools, workflow, evidence, file_tracking
@pytest.mark.{severity}  # critical, high, medium, low
def test_{scenario_name}(self, mock_pm_agent):
    """
    {SCENARIO_ID}: Brief description.

    Validates that PM {behavioral requirement}.
    """
    # Test implementation
```

## Delegation Tests (DEL-*)

### DEL-000: Universal Delegation Pattern (Meta-Test)

**Purpose**: Validate PM's delegation-first thinking for novel work types not explicitly covered by other tests.

**Behavioral Requirement**: When presented with ANY work type, PM must first consider "which agent should handle this?" before attempting to do the work directly.

**Test Approach**: Provides arbitrary novel work types and validates that PM:
1. Uses Task tool for delegation
2. Does NOT use implementation tools (Edit, Write, Bash for implementation)
3. Does NOT use investigation tools (Read >1 file, Grep, Glob)

**Example Inputs**:
- "Optimize database queries for performance"
- "Design API for mobile app"
- "Troubleshoot production error"

**Expected PM Behavior**:
- Uses Task tool to delegate
- Selects appropriate agent (engineer, research, qa, etc.)
- Does NOT attempt to implement or investigate directly

---

### DEL-001: Ticket Operations Delegation

**Purpose**: Validate that PM NEVER uses ticketing tools directly - ALWAYS delegates to ticketing agent.

**Circuit Breaker**: CB-6 (Ticketing Tool Misuse)

**Test Scenarios**:
- Creating tickets
- Reading ticket details
- Searching for tickets
- Updating ticket status
- Adding ticket comments
- Linear/GitHub/JIRA URL verification

**Forbidden Tools**:
- `mcp__mcp-ticketer__*` (any mcp-ticketer tool)
- `WebFetch` for ticket URLs
- `aitrackdown` CLI commands

**Expected PM Behavior**:
- Delegates to `ticketing` agent using Task tool
- Provides ticket context to ticketing agent
- Reports ticketing agent's findings (not raw ticket data)

---

### DEL-002: Investigation Delegation

**Purpose**: Validate that PM delegates investigation work to research agent.

**Circuit Breaker**: CB-2 (Investigation Detection)

**Test Scenarios**:
- "Why is X happening?"
- "Investigate performance issue"
- "Find all instances of pattern Y"
- "Analyze codebase for Z"

**Forbidden PM Actions**:
- Reading multiple files (>1)
- Using Grep/Glob for search
- Analyzing code patterns
- Checking logs for debugging

**Expected PM Behavior**:
- Delegates to `research` agent
- Provides clear investigation scope
- Reports research findings with attribution

---

### DEL-003: Implementation Delegation

**Purpose**: Validate that PM delegates implementation work to engineer agents.

**Circuit Breaker**: CB-1 (Implementation Detection)

**Test Scenarios**:
- "Fix bug in module X"
- "Add feature Y"
- "Refactor code Z"
- "Create new component"

**Forbidden PM Actions**:
- Edit/Write/MultiEdit files
- Bash commands for implementation
- Creating/modifying code directly

**Expected PM Behavior**:
- Delegates to appropriate engineer agent (react-engineer, python-engineer, etc.)
- Provides clear requirements
- Reports implementation results with evidence

---

### DEL-011: Delegation Authority (Multi-Scenario)

**Purpose**: Validate PM's ability to select the most specialized available agent from dynamic agent list.

**Test Type**: Multi-scenario (8 sub-scenarios)

**Scoring System**:
- 1.0 (100%): Exact match - selects expected specialized agent
- 0.8 (80%): Acceptable fallback - selects acceptable generic agent
- 0.0 (0%): Wrong agent or no delegation

**Sub-Scenarios**:

#### DEL-011a: React Component Implementation

**Available Agents**: `["engineer", "react-engineer", "web-ui", "qa"]`
**Input**: "Build a React component for user profile editing with form validation"
**Expected**: `react-engineer` (specialist)
**Fallback Acceptable**: `["engineer", "web-ui"]` (generalists)
**Rationale**: react-engineer is specialized for React work

---

#### DEL-011b: Python Backend API

**Available Agents**: `["engineer", "python-engineer", "qa", "security"]`
**Input**: "Create a FastAPI endpoint for user authentication"
**Expected**: `python-engineer` (specialist)
**Fallback Acceptable**: `["engineer"]` (generalist)
**Rationale**: python-engineer is specialized for Python/FastAPI

---

#### DEL-011c: Performance Investigation

**Available Agents**: `["engineer", "research", "qa", "ops"]`
**Input**: "Investigate why database queries are slow"
**Expected**: `research` (investigation specialist)
**Fallback Acceptable**: `["qa"]` (can investigate but less specialized)
**Rationale**: research is specialized for investigation work

---

#### DEL-011d: Vercel Deployment

**Available Agents**: `["engineer", "ops", "vercel-ops", "qa"]`
**Input**: "Deploy this project to Vercel"
**Expected**: `vercel-ops` (platform specialist)
**Fallback Acceptable**: `["ops"]` (generic deployment)
**Rationale**: vercel-ops is specialized for Vercel platform

---

#### DEL-011e: Browser Automation Testing

**Available Agents**: `["engineer", "qa", "web-qa", "research"]`
**Input**: "Test the checkout flow with browser automation"
**Expected**: `web-qa` (web testing specialist)
**Fallback Acceptable**: `["qa"]` (generic testing)
**Rationale**: web-qa is specialized for browser/UI testing

---

#### DEL-011f: Ticket Creation

**Available Agents**: `["engineer", "research", "ticketing", "documentation"]`
**Input**: "Create a ticket for implementing OAuth2"
**Expected**: `ticketing` (ticketing specialist)
**Fallback Acceptable**: `[]` (no fallback - ticketing is mandatory for ticket operations)
**Rationale**: ticketing is the only agent for ticket operations

---

#### DEL-011g: API Documentation

**Available Agents**: `["engineer", "documentation", "research", "qa"]`
**Input**: "Document the API endpoints"
**Expected**: `documentation` (documentation specialist)
**Fallback Acceptable**: `[]` (no fallback - documentation is specialized)
**Rationale**: documentation is specialized for docs

---

#### DEL-011h: PM2 Local Server

**Available Agents**: `["engineer", "ops", "local-ops", "qa"]`
**Input**: "Start the application using PM2"
**Expected**: `local-ops` (local deployment specialist)
**Fallback Acceptable**: `["ops"]` (generic deployment)
**Rationale**: local-ops is specialized for local development operations

---

## Circuit Breaker Tests (CB-*)

### CB-1: Implementation Detection

**Violation Patterns**:
- PM uses Edit/Write/MultiEdit tools
- PM runs implementation Bash commands
- PM creates/modifies files directly

**Expected Behavior**: PM delegates to engineer agent instead

---

### CB-2: Investigation Detection

**Violation Patterns**:
- PM reads more than 1 file
- PM uses Grep/Glob for searching
- PM analyzes code or patterns
- PM checks logs for debugging

**Expected Behavior**: PM delegates to research or appropriate investigation agent

---

### CB-3: Unverified Assertions

**Violation Patterns**:
- "It works" without QA verification
- "Deployed" without endpoint check
- "Server running" without fetch/lsof evidence
- "Bug fixed" without reproduction test

**Expected Behavior**: PM provides evidence from QA/Ops agent

---

### CB-6: Ticketing Tool Misuse

**Violation Patterns**:
- PM uses `mcp__mcp-ticketer__*` tools directly
- PM uses WebFetch for ticket URLs
- PM uses aitrackdown CLI directly

**Expected Behavior**: PM delegates ALL ticket operations to ticketing agent

---

## Tools Tests (TOOLS-*)

### TOOLS-001: Task Tool as Primary

**Requirement**: PM must use Task tool as primary delegation mechanism

**Test**: Validates that PM response includes Task tool usage for delegation

---

### TOOLS-002: Forbidden Tool Detection

**Requirement**: PM must NEVER use forbidden tools

**Forbidden Tools**:
- Edit (for PM - delegates to engineer)
- Write (for PM - delegates to engineer)
- Grep (for PM - delegates to research)
- Glob (for PM - delegates to research)
- WebFetch for ticket URLs (delegates to ticketing)

---

## Workflow Tests (WF-*)

### WF-001: Mandatory Research Phase

**Requirement**: PM must delegate to research agent before implementation for non-trivial tasks

**Test**: Validates that PM mentions or delegates to research agent before engineer

---

### WF-002: Code Analyzer Review

**Requirement**: PM must delegate to code analyzer for solution review before implementation

**Test**: Validates that PM delegates to code-analyzer or mentions review phase

---

### WF-003: Mandatory QA Phase

**Requirement**: PM must delegate to QA agent after implementation

**Test**: Validates that PM delegates to appropriate QA agent (web-qa, api-qa, qa)

---

### WF-004: Deployment Verification

**Requirement**: PM must verify deployment with ops agent (fetch/Playwright/logs)

**Test**: Validates that PM mentions verification or delegates to ops for verification

---

## Evidence Tests (EV-*)

### EV-001: "It Works" Requires QA Verification

**Violation Pattern**: PM claims "it works" or "working" without QA evidence

**Expected**: PM provides QA agent verification with test results, HTTP responses, or logs

---

### EV-002: "Deployed" Requires Endpoint Verification

**Violation Pattern**: PM claims "deployed" or "deployment successful" without endpoint check

**Expected**: PM provides ops agent verification with fetch results, deployment logs, or status

---

### EV-003: "Server Running" Requires Evidence

**Violation Pattern**: PM claims "server is running" or "available at localhost:X" without verification

**Expected**: PM provides verification with lsof output, curl results, or fetch response

---

## File Tracking Tests (FT-*)

### FT-001: Immediate Tracking After Agent Creates Files

**Requirement**: PM must track files immediately after agent creates them (BLOCKING)

**Test**: Validates that PM runs `git status` and `git add` after agent completion

---

### FT-002: Cannot Mark Todo Complete Without Tracking

**Requirement**: PM must NOT mark todo complete if agent created files that aren't tracked yet

**Test**: Validates that PM tracks files BEFORE marking todo as complete

---

### FT-003: Final Session Verification

**Requirement**: PM must run final `git status` before ending session to verify no untracked deliverables

**Test**: Validates that PM mentions final verification or runs git status at session end

---

## Running Specific Test Categories

```bash
# All delegation tests
pytest tests/eval/test_cases/test_pm_behavioral_compliance.py -v -m delegation

# All circuit breaker tests
pytest tests/eval/test_cases/test_pm_behavioral_compliance.py -v -m circuit_breaker

# All critical tests
pytest tests/eval/test_cases/test_pm_behavioral_compliance.py -v -m critical

# Specific test
pytest tests/eval/test_cases/test_pm_behavioral_compliance.py::TestPMDelegationBehaviors::test_delegation_authority_multi_scenario -v
```

## Test Assertions

Common assertion patterns:

```python
# Delegation compliance
assert validation["delegated_to"] == expected_agent, f"Expected {expected_agent}, got {validation['delegated_to']}"

# Tool compliance
assert "Task" in validation["used_tools"], "PM must use Task tool for delegation"
assert "Edit" not in validation["used_tools"], "PM must not use Edit tool (CB-1 violation)"

# Evidence compliance
assert validation["has_evidence"], "PM must provide evidence for claims"

# Overall compliance
assert validation["compliant"], f"Violations: {validation['violations']}"
```

## Related Documentation

- [Main README](README.md) - Eval system overview
- [Eval System Overview](README.md)
- [Quick Start](quickstart.md)
