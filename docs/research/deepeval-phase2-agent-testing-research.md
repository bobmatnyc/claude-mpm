# DeepEval Phase 2: Agent Eval Testing - Research & Design Specification

**Research Date**: December 5, 2025
**Project**: Claude MPM Framework
**GitHub Project**: https://github.com/users/bobmatnyc/projects/9
**Phase**: Phase 2 Design Specification
**Status**: Research Complete ✅

---

## Executive Summary

This research document provides comprehensive analysis of Phase 1 DeepEval implementation and establishes the foundation for Phase 2: Agent Eval Testing. Phase 1 successfully delivered PM agent behavioral testing with 4,092 lines of code, 25+ tests, and complete documentation. Phase 2 will extend this framework to test 6 core agents (Research, Engineer, QA, Ops, Documentation, Ticketing) plus BASE_AGENT foundations.

**Key Findings**:
- Phase 1 achieved 100% PM instruction coverage with robust eval infrastructure
- BASE_AGENT architecture uses hierarchical template merging for agent composition
- 6 core agents identified with distinct behavioral patterns requiring specialized testing
- Integration testing framework provides capture/replay/performance capabilities
- Agent merge process enables testing both BASE_AGENT and specialized behaviors

**Phase 2 Scope**: Extend DeepEval framework to test BASE_AGENT + 6 specialized agents with custom metrics, behavioral scenarios, and integration testing.

---

## Table of Contents

1. [Phase 1 Analysis](#phase-1-analysis)
2. [Agent Architecture Overview](#agent-architecture-overview)
3. [Project Board Structure](#project-board-structure)
4. [Phase 2 Requirements](#phase-2-requirements)
5. [Test Harness Design](#test-harness-design)
6. [Implementation Roadmap](#implementation-roadmap)
7. [Appendices](#appendices)

---

## Phase 1 Analysis

### Phase 1 Implementation Summary

**Deliverables Completed** (December 5, 2024):

| Component | Files | LOC | Tests | Status |
|-----------|-------|-----|-------|--------|
| Base Framework | 19 | 1,764 | 4 demo | ✅ Complete |
| Integration Testing | 12 | 2,328 | 21 | ✅ Complete |
| Documentation | 6 | 2,600+ | N/A | ✅ Complete |
| **Total** | **31** | **4,092** | **25+** | ✅ Complete |

**Git Commits**:
- `78f2ced0` - Base DeepEval framework (Dec 5, 13:24)
- `9207d931` - Integration testing (Dec 5, 17:00)
- `2641ed89` - PM behavioral testing (Dec 5, 17:00)

### Phase 1 Architecture

```
tests/eval/
├── metrics/                         # Custom DeepEval Metrics
│   ├── instruction_faithfulness.py  # PM instruction compliance (243 LOC)
│   └── delegation_correctness.py    # Delegation quality (369 LOC)
│
├── scenarios/                       # Test Scenario Data (JSON)
│   ├── ticketing_scenarios.json     # 7 ticketing test cases
│   ├── circuit_breaker_scenarios.json # 9 circuit breaker tests
│   └── pm_behavioral_requirements.json # 48 behavioral scenarios
│
├── test_cases/                      # Test Suites
│   ├── ticketing_delegation.py      # Unit tests (358 LOC)
│   ├── circuit_breakers.py          # CB tests (157 LOC)
│   ├── integration_ticketing.py     # Integration tests (500 LOC, 13 tests)
│   ├── performance.py               # Performance tests (549 LOC, 8 tests)
│   └── test_pm_behavioral_compliance.py # Behavioral tests
│
├── utils/                           # Helper Utilities
│   ├── pm_response_parser.py        # PM response analysis (432 LOC)
│   ├── pm_response_capture.py       # Response capture (447 LOC)
│   └── response_replay.py           # Replay/regression (560 LOC)
│
├── responses/                       # Captured PM Responses
├── golden_responses/                # Baseline Responses
├── performance_history.json         # Performance Baselines
└── conftest.py                      # Pytest Fixtures (24 fixtures)
```

### Key Phase 1 Features

**1. Custom DeepEval Metrics**:
- `InstructionFaithfulnessMetric`: Evaluates PM instruction compliance (0.0-1.0 score)
- `DelegationCorrectnessMetric`: Validates proper agent routing
- `TicketingDelegationMetric`: Strict ticketing enforcement (binary 0.0/1.0)
- `CircuitBreakerMetric`: Detects all 7 circuit breaker violations

**2. PM Response Parser**:
- Extracts tool usage patterns (Edit, Write, Read, Task, etc.)
- Identifies delegation events with agent names
- Validates assertion-evidence mapping
- Calculates evidence quality score (0.0-1.0)
- Detects circuit breaker violations

**3. Integration Testing Infrastructure**:
- **Response Capture**: Captures real PM responses with metadata, PII redaction
- **Response Replay**: Regression testing against golden baselines
- **Performance Tracking**: PM response time, throughput, memory usage
- **Three Execution Modes**: Integration (real PM), Replay (cached), Unit (mock)

**4. Test Scenarios**:
- **7 Ticketing Scenarios**: Linear URL, GitHub URL, ticket ID, create, search, update, mixed
- **9 Circuit Breaker Scenarios**: CB#1-CB#7 coverage
- **48 Behavioral Scenarios**: Delegation, tools, workflow, evidence, file tracking, memory

**5. Comprehensive Documentation**:
- `README.md`: Base framework usage (405 lines)
- `README_INTEGRATION.md`: Integration testing guide (600+ lines)
- `PM_BEHAVIORAL_TESTING.md`: Behavioral testing guide (523 lines)
- `INTEGRATION_IMPLEMENTATION.md`: Technical specs (525 lines)
- Research docs: Framework implementation details

### Phase 1 Success Criteria Met ✅

- [x] Complete `tests/eval/` directory structure with all files
- [x] Working test suite that can run with `pytest tests/eval/`
- [x] Custom metrics integrated with DeepEval
- [x] JSON scenario files with 7+ test cases each
- [x] Comprehensive documentation (README.md + guides)
- [x] Type hints for all functions
- [x] Docstrings for classes and methods
- [x] Pytest fixtures for DeepEval setup
- [x] Async test support (pytest-asyncio)
- [x] Mock PM agent responses for testing
- [x] Evidence collection for debugging
- [x] Response capture/replay system
- [x] Performance benchmarking
- [x] Golden baseline management

### Phase 1 Test Coverage

**PM Instruction Coverage**: 100%
- All PM_INSTRUCTIONS.md requirements covered
- All WORKFLOW.md 5-phase workflow tested
- All MEMORY.md memory management tested
- All 7 circuit breakers validated

**Test Execution**:
- Base framework: 4 demo tests (showing capabilities)
- Integration tests: 13 tests (100% pass rate with mock PM)
- Performance tests: 8 tests (7 passing, 1 skipped)
- Behavioral tests: 48 scenarios defined

---

## Agent Architecture Overview

### BASE_AGENT Template System

Claude MPM uses a **hierarchical template merging system** for agent composition:

**Architecture Pattern**:
```
BASE_AGENT_TEMPLATE.md (9,138 bytes, 292 lines)
    ↓ (merged into)
BASE_RESEARCH.md (1,690 bytes, 52 lines)
    ↓ (deployed as)
.claude/agents/research-agent.md
```

**Merge Process** (from `agent_template_builder.py`):
1. **Discovery**: Walk directory tree from agent file to repository root
2. **Collection**: Gather all BASE-AGENT.md files (closest to farthest)
3. **Composition**: Merge templates in hierarchical order
4. **Deployment**: Generate final agent markdown with YAML frontmatter

**Example Discovery Order**:
```
repo/engineering/python/fastapi-engineer.md
  ↓ Searches for:
  1. repo/engineering/python/BASE-AGENT.md (local, highest priority)
  2. repo/engineering/BASE-AGENT.md (parent)
  3. repo/BASE-AGENT.md (root, lowest priority)
```

### BASE_AGENT_TEMPLATE.md Structure

**File**: `src/claude_mpm/agents/BASE_AGENT_TEMPLATE.md` (292 lines)

**Key Sections**:
1. **Essential Operating Rules**: Never assume, always verify, challenge the unexpected
2. **Task Management**: Status indicators (completed, in_progress, pending, blocked)
3. **Response Structure**: Task summary, completed work, findings, follow-up, JSON block
4. **Memory Guidelines**: Project-specific learnings, what to capture vs. ignore
5. **Quick Reference**: Tool usage, escalation triggers, verification requirements

**Memory Protocol** (Lines 64-100):
```json
{
  "task_completed": true/false,
  "instructions": "Original task",
  "results": "What accomplished",
  "files_modified": [...],
  "tools_used": [...],
  "remember": ["Key learnings"] or null
}
```

### 6 Core Agent Specializations

**Agent File Sizes** (LOC):

| Agent | File | LOC | Bytes | Key Focus |
|-------|------|-----|-------|-----------|
| PM | BASE_PM.md | 479 | 16,001 | Delegation, circuit breakers, workflow |
| Engineer | BASE_ENGINEER.md | 657 | 24,434 | Code minimization, anti-patterns, TDD |
| QA | BASE_QA.md | 166 | 5,347 | Test execution, coverage, memory-efficient testing |
| Research | BASE_RESEARCH.md | 52 | 1,690 | Memory management, sampling, pattern extraction |
| Ops | BASE_OPS.md | 218 | 7,636 | Deployment, infrastructure, security |
| Documentation | BASE_DOCUMENTATION.md | 52 | 1,504 | Documentation standards, clarity |
| Prompt Engineer | BASE_PROMPT_ENGINEER.md | 787 | 21,736 | Prompt design, optimization |

**Total Agent LOC**: 2,703 lines across 8 files (including BASE_AGENT_TEMPLATE)

### Agent-Specific Behavioral Patterns

**1. Research Agent (BASE_RESEARCH.md, 52 lines)**:
- **Memory Management Protocol**: Files >20KB use document_summarizer
- **Strategic Sampling**: 3-5 files max, 100-200 lines per sample
- **Discovery Pattern**: grep/glob → sampling → pattern extraction → synthesis
- **Output Requirements**: Executive summary, code examples, patterns, file list

**2. Engineer Agent (BASE_ENGINEER.md, 657 lines)**:
- **Code Minimization Mandate**: Zero net new lines target
- **Anti-Pattern Enforcement**: No mock data, no fallback behavior in production
- **Maturity-Based Thresholds**: <1000 LOC establish, >10k LOC require approval
- **Consolidation Criteria**: >80% similarity consolidate, >50 lines extract common

**3. QA Agent (BASE_QA.md, 166 lines)**:
- **Memory-Efficient Testing**: 3-5 test files max
- **JavaScript Test Process Management**: CRITICAL - avoid Vitest/Jest watch mode
- **Safe Test Execution Protocol**: CI=true npm test, explicit run modes
- **Test Discovery Pattern**: grep for test functions, not full reads

**4. Ops Agent (BASE_OPS.md, 218 lines)**:
- **Deployment Protocol**: Environment validation, rollback preparation
- **Infrastructure Focus**: Docker, Kubernetes, CI/CD, monitoring
- **Security Emphasis**: Secrets management, vulnerability scanning
- **Verification Requirements**: Health checks, smoke tests, rollback testing

**5. Documentation Agent (BASE_DOCUMENTATION.md, 52 lines)**:
- **Documentation Standards**: Clarity, completeness, examples
- **Audience Awareness**: Developer vs. user documentation
- **Maintenance Focus**: Keep docs in sync with code

**6. Prompt Engineer Agent (BASE_PROMPT_ENGINEER.md, 787 lines)**:
- **Prompt Optimization**: Token efficiency, clarity, specificity
- **Testing Requirements**: A/B testing, success metrics
- **Iterative Refinement**: Baseline → test → optimize → validate

### Agent Template Files (src/claude_mpm/agents/templates/)

**Template Count**: 13 markdown files + 1 README

**Key Templates**:
1. **circuit-breakers.md** (36,961 bytes): All 7 circuit breaker definitions
2. **response-format.md** (21,354 bytes): Structured response requirements
3. **research-gate-examples.md** (20,376 bytes): Research delegation patterns
4. **pm-examples.md** (16,804 bytes): PM behavioral examples
5. **git-file-tracking.md** (18,842 bytes): File tracking protocol
6. **validation-templates.md** (13,148 bytes): Validation patterns
7. **ticketing-examples.md** (8,066 bytes): Ticketing delegation examples

**Total Template Size**: ~200KB of agent instruction templates

---

## Project Board Structure

### GitHub Project Overview

**Project**: https://github.com/users/bobmatnyc/projects/9
**Repository**: bobmatnyc/claude-mpm

### Issue Analysis

**Phase 1 Related Issues** (Completed):

**Issue #97**: Implement base DeepEval framework infrastructure
- **Status**: Closed (Dec 5, 2025)
- **Labels**: enhancement, testing, deepeval
- **Deliverables**: 4 custom metrics, PM response parser, 16 scenarios, pytest fixtures
- **Commit**: 78f2ced0
- **Files**: 19 files, 1,764 LOC

**Issue #102**: Create comprehensive eval system documentation
- **Status**: Closed (Dec 5, 2025)
- **Labels**: documentation
- **Deliverables**: Architecture docs, usage guides, test scenarios, metrics docs, CI/CD examples
- **Commit**: e5d8a42c
- **Files**: 4,197 lines documentation

### Labels and Taxonomy

**Phase 1 Labels Used**:
- `enhancement`: New feature or request
- `testing`: Testing related work
- `deepeval`: DeepEval framework specific
- `documentation`: Documentation work

**Naming Conventions Observed**:
- Issue titles: Imperative mood ("Implement X", "Create Y")
- Commit messages: Conventional commits (feat:, docs:, fix:)
- Test files: `test_*.py` pattern
- Scenario files: `*_scenarios.json` pattern

### Milestones and Workflow

**No explicit milestones found** in search results, but clear workflow pattern:

1. **Implementation** → Commit with `feat:` prefix
2. **Documentation** → Commit with `docs:` prefix
3. **Testing** → Validate with pytest
4. **Issue Close** → Mark as completed with commit reference

**State Transitions**:
- Open → In Progress (via assignment) → Closed (via commit)
- No explicit "waiting" or "blocked" states observed
- Quick turnaround: Issues opened and closed same day

---

## Phase 2 Requirements

### Objectives

**Primary Goal**: Extend DeepEval framework to test BASE_AGENT foundations and 6 specialized agents (Research, Engineer, QA, Ops, Documentation, Prompt Engineer).

**Success Criteria**:
1. **BASE_AGENT Testing**: Validate common behavioral patterns across all agents
2. **Agent-Specific Testing**: Custom metrics for each of 6 specialized agents
3. **Integration Testing**: Test agent merge process and composition
4. **Coverage Goal**: 100% behavioral coverage for BASE_AGENT + specialized behaviors
5. **Performance Benchmarking**: Baseline metrics for each agent type

### Scope Definition

**In Scope**:
- BASE_AGENT_TEMPLATE.md behavioral testing (core patterns)
- 6 specialized agent behavioral testing (agent-specific patterns)
- Agent merge process testing (hierarchical composition)
- Custom metrics per agent type
- Integration testing with capture/replay
- Performance benchmarking per agent
- Comprehensive documentation

**Out of Scope**:
- Real agent execution (use mock/capture like Phase 1)
- Ticketing agent testing (covered by PM delegation tests)
- Security agent testing (future phase)
- Multi-agent workflow testing (future phase)
- Production deployment testing (future phase)

### Agent Testing Coverage Targets

| Agent | Behavioral Scenarios | Custom Metrics | Integration Tests | Performance Tests |
|-------|---------------------|----------------|-------------------|-------------------|
| BASE_AGENT | 20 scenarios | 2 metrics | 5 tests | 3 tests |
| Research | 15 scenarios | 2 metrics | 4 tests | 2 tests |
| Engineer | 25 scenarios | 3 metrics | 6 tests | 3 tests |
| QA | 20 scenarios | 3 metrics | 5 tests | 2 tests |
| Ops | 18 scenarios | 2 metrics | 5 tests | 3 tests |
| Documentation | 12 scenarios | 2 metrics | 3 tests | 1 test |
| Prompt Engineer | 15 scenarios | 2 metrics | 4 tests | 2 tests |
| **Total** | **125 scenarios** | **16 metrics** | **32 tests** | **16 tests** |

### Test Harness Requirements

**1. BASE_AGENT Test Harness**:
- Test BASE_AGENT_TEMPLATE.md in isolation
- Validate common patterns: verify, escalate, memory protocol
- Test JSON response format compliance
- Verify task status indicators (completed, pending, blocked)
- Test memory capture triggers and quality

**2. Specialized Agent Test Harness**:
- Test merged agent (BASE_AGENT + specialized)
- Validate agent-specific behavioral patterns
- Test specialized metrics (e.g., code minimization for Engineer)
- Verify tool usage restrictions (e.g., no watch mode for QA)
- Test memory management (e.g., sampling for Research)

**3. Agent Merge Process Testing**:
- Test hierarchical template discovery
- Validate merge order (local → parent → root)
- Test composition correctness
- Verify specialized instructions override base instructions
- Test tool authorization inheritance

**4. Integration Testing Capabilities**:
- Capture agent responses (like PM capture)
- Replay for regression testing
- Golden baseline management per agent
- Performance tracking per agent type
- Three execution modes: Integration, Replay, Unit

---

## Test Harness Design

### Architecture Overview

```
tests/eval/
├── agents/                          # NEW - Agent Testing Directory
│   ├── base_agent/                  # BASE_AGENT Testing
│   │   ├── test_base_patterns.py
│   │   ├── test_memory_protocol.py
│   │   ├── test_response_format.py
│   │   └── scenarios/
│   │       └── base_agent_scenarios.json
│   │
│   ├── research/                    # Research Agent Testing
│   │   ├── test_memory_management.py
│   │   ├── test_sampling_strategy.py
│   │   ├── test_research_patterns.py
│   │   └── scenarios/
│   │       └── research_scenarios.json
│   │
│   ├── engineer/                    # Engineer Agent Testing
│   │   ├── test_code_minimization.py
│   │   ├── test_anti_patterns.py
│   │   ├── test_consolidation.py
│   │   └── scenarios/
│   │       └── engineer_scenarios.json
│   │
│   ├── qa/                          # QA Agent Testing
│   │   ├── test_test_execution.py
│   │   ├── test_process_management.py
│   │   ├── test_coverage_analysis.py
│   │   └── scenarios/
│   │       └── qa_scenarios.json
│   │
│   ├── ops/                         # Ops Agent Testing
│   │   ├── test_deployment_protocol.py
│   │   ├── test_infrastructure.py
│   │   ├── test_security.py
│   │   └── scenarios/
│   │       └── ops_scenarios.json
│   │
│   ├── documentation/               # Documentation Agent Testing
│   │   ├── test_documentation_standards.py
│   │   ├── test_clarity.py
│   │   └── scenarios/
│   │       └── documentation_scenarios.json
│   │
│   └── prompt_engineer/             # Prompt Engineer Testing
│       ├── test_prompt_optimization.py
│       ├── test_token_efficiency.py
│       └── scenarios/
│           └── prompt_engineer_scenarios.json
│
├── metrics/                         # EXTEND - Agent-Specific Metrics
│   ├── base_agent/
│   │   ├── verification_compliance.py
│   │   └── memory_protocol_metric.py
│   ├── research/
│   │   ├── memory_efficiency_metric.py
│   │   └── sampling_strategy_metric.py
│   ├── engineer/
│   │   ├── code_minimization_metric.py
│   │   ├── consolidation_metric.py
│   │   └── anti_pattern_detection.py
│   ├── qa/
│   │   ├── test_execution_safety_metric.py
│   │   ├── coverage_quality_metric.py
│   │   └── process_management_metric.py
│   └── ops/
│       ├── deployment_safety_metric.py
│       └── infrastructure_compliance_metric.py
│
├── utils/                           # EXTEND - Agent Response Utilities
│   ├── agent_response_parser.py     # Generic agent response parser
│   ├── agent_response_capture.py    # Multi-agent capture
│   └── agent_merge_tester.py        # Test merge process
│
└── integration/                     # NEW - Integration Testing
    ├── test_agent_merge_process.py  # Test hierarchical merging
    ├── test_base_agent_integration.py
    └── test_specialized_agent_integration.py
```

### Custom Metrics Design

**BASE_AGENT Metrics**:

1. **VerificationComplianceMetric**:
   - Checks: "Always verify" pattern compliance
   - Detects: Test execution, API calls, file edits verification
   - Scoring: 1.0 = all verification present, 0.0 = no verification
   - Threshold: 0.9 (90% verification compliance)

2. **MemoryProtocolMetric**:
   - Checks: JSON response format, remember field usage
   - Validates: Memory capture triggers (user instruction, undocumented facts)
   - Scoring: 1.0 = perfect protocol, 0.0 = missing JSON block
   - Threshold: 1.0 (strict compliance)

**Research Agent Metrics**:

1. **MemoryEfficiencyMetric**:
   - Checks: File size checks before reading
   - Validates: 3-5 file max, sampling strategy
   - Detects violations: >5 files read, >20KB files without summarizer
   - Scoring: 1.0 = perfect efficiency, 0.0 = memory violations

2. **SamplingStrategyMetric**:
   - Checks: grep/glob used for discovery
   - Validates: Pattern extraction vs. full reads
   - Scoring: 1.0 = strategic sampling, 0.0 = brute force reading

**Engineer Agent Metrics**:

1. **CodeMinimizationMetric**:
   - Checks: Net LOC delta (target ≤0)
   - Validates: Search before create, consolidation opportunities
   - Scoring: 1.0 = negative LOC, 0.5 = zero LOC, 0.0 = positive LOC

2. **ConsolidationMetric**:
   - Checks: >80% similarity consolidation
   - Validates: Common logic extraction (>50 lines)
   - Scoring: Based on consolidation opportunities identified

3. **AntiPatternDetectionMetric**:
   - Checks: No mock data in production
   - Validates: No silent fallbacks, explicit errors
   - Scoring: 1.0 = no anti-patterns, 0.0 = anti-patterns present

**QA Agent Metrics**:

1. **TestExecutionSafetyMetric**:
   - Checks: CI=true usage, no watch mode
   - Validates: Process cleanup (ps aux verification)
   - Scoring: 1.0 = safe execution, 0.0 = watch mode used

2. **CoverageQualityMetric**:
   - Checks: Focus on uncovered critical paths
   - Validates: Representative test sampling
   - Scoring: Based on coverage tool usage vs. manual calculation

3. **ProcessManagementMetric**:
   - Checks: Pre-flight checks (package.json inspection)
   - Validates: Post-execution verification (process cleanup)
   - Scoring: 1.0 = all checks, 0.0 = no checks

**Ops Agent Metrics**:

1. **DeploymentSafetyMetric**:
   - Checks: Environment validation, rollback preparation
   - Validates: Health checks, smoke tests
   - Scoring: 1.0 = all safety checks, 0.0 = no checks

2. **InfrastructureComplianceMetric**:
   - Checks: Docker/Kubernetes best practices
   - Validates: Secrets management, security scanning
   - Scoring: Based on compliance with infrastructure standards

### Test Scenario Templates

**BASE_AGENT Scenario Example**:
```json
{
  "scenario_id": "BASE-001",
  "name": "Agent must verify file edits before reporting completion",
  "category": "verification",
  "severity": "critical",
  "instruction_source": "BASE_AGENT_TEMPLATE.md:lines 5-8",
  "behavioral_requirement": "Always verify changes - test functions, APIs, edits",
  "input": "User: Update config.py to add new setting",
  "expected_agent_behavior": {
    "should_do": ["Read config.py after edit", "Verify change applied", "Report verification evidence"],
    "should_not_do": ["Report completion without verification"],
    "required_tools": ["Edit", "Read"],
    "verification_pattern": "Read.*config\\.py.*after.*Edit"
  },
  "compliant_response_pattern": "Edit tool used, then Read tool verifies change",
  "violation_response_pattern": "Edit tool used but no verification Read"
}
```

**Research Agent Scenario Example**:
```json
{
  "scenario_id": "RES-001",
  "name": "Research must check file size before reading large files",
  "category": "memory_management",
  "severity": "critical",
  "instruction_source": "BASE_RESEARCH.md:lines 7-11",
  "behavioral_requirement": "Files >20KB must use document_summarizer",
  "input": "User: Analyze authentication implementation in auth_service.py (50KB file)",
  "expected_agent_behavior": {
    "should_do": ["Check file size", "Use document_summarizer for 50KB file"],
    "should_not_do": ["Read 50KB file directly"],
    "file_size_threshold": 20000,
    "required_pattern": "document_summarizer|sample.*auth_service"
  },
  "compliant_response_pattern": "File size check → document_summarizer usage",
  "violation_response_pattern": "Direct Read of large file without size check"
}
```

**Engineer Agent Scenario Example**:
```json
{
  "scenario_id": "ENG-001",
  "name": "Engineer must search for existing solutions before creating new code",
  "category": "code_minimization",
  "severity": "high",
  "instruction_source": "BASE_ENGINEER.md:lines 12-16",
  "behavioral_requirement": "Search first (80% time): Vector search + grep for existing solutions",
  "input": "User: Implement JWT token validation",
  "expected_agent_behavior": {
    "should_do": ["Vector search for 'JWT validation'", "Grep for 'jwt.*validate'", "Check existing auth code"],
    "should_not_do": ["Immediately write new JWT validation"],
    "required_tools": ["mcp__mcp-vector-search__search_code", "Grep"],
    "search_before_create": true
  },
  "compliant_response_pattern": "Search tools used before Write/Edit",
  "violation_response_pattern": "Write/Edit without prior search"
}
```

**QA Agent Scenario Example**:
```json
{
  "scenario_id": "QA-001",
  "name": "QA must use CI mode for JavaScript test execution",
  "category": "process_management",
  "severity": "critical",
  "instruction_source": "BASE_QA.md:lines 44-71",
  "behavioral_requirement": "ALWAYS use CI=true npm test or vitest run (never watch mode)",
  "input": "User: Run tests for authentication module",
  "expected_agent_behavior": {
    "should_do": ["Check package.json test script", "Use CI=true npm test", "Verify process cleanup"],
    "should_not_do": ["Run npm test without CI flag", "Use vitest watch mode"],
    "required_bash_pattern": "CI=true.*npm test|vitest run",
    "forbidden_bash_pattern": "vitest(?!.*run)|npm test(?!.*CI)"
  },
  "compliant_response_pattern": "CI=true npm test executed, process cleanup verified",
  "violation_response_pattern": "npm test without CI flag"
}
```

### Agent Response Parser Extensions

**Generic Agent Response Parser** (`utils/agent_response_parser.py`):

```python
class AgentResponseParser:
    """Generic agent response parser for all agent types."""

    def parse(self, response_text: str, agent_type: str) -> AgentResponseAnalysis:
        """Parse agent response based on agent type.

        Args:
            response_text: Raw agent response text
            agent_type: Agent type (base, research, engineer, qa, ops, etc.)

        Returns:
            AgentResponseAnalysis with agent-specific validations
        """
        # Common parsing
        tools_used = self._extract_tools(response_text)
        json_block = self._extract_json_block(response_text)
        memory_data = self._extract_memory(json_block)

        # Agent-specific parsing
        if agent_type == "research":
            return self._parse_research_agent(response_text, tools_used, json_block)
        elif agent_type == "engineer":
            return self._parse_engineer_agent(response_text, tools_used, json_block)
        elif agent_type == "qa":
            return self._parse_qa_agent(response_text, tools_used, json_block)
        # ... etc

        return AgentResponseAnalysis(
            tools_used=tools_used,
            json_block=json_block,
            memory_data=memory_data,
            agent_type=agent_type
        )

    def _parse_research_agent(self, text, tools, json_block):
        """Parse research agent specific patterns."""
        file_size_checks = self._detect_pattern(text, r"file.*size|check.*size")
        files_read = self._count_read_tools(tools)
        sampling_strategy = self._detect_sampling(text)

        return ResearchAgentAnalysis(
            tools_used=tools,
            json_block=json_block,
            file_size_checks=file_size_checks,
            files_read_count=files_read,
            sampling_strategy_used=sampling_strategy
        )
```

### Integration Testing Design

**Agent Merge Process Testing** (`integration/test_agent_merge_process.py`):

```python
class TestAgentMergeProcess:
    """Test hierarchical agent template merging."""

    def test_base_agent_discovery(self):
        """Test BASE-AGENT.md discovery in directory hierarchy."""
        # Create test directory structure
        # Verify correct discovery order (local → parent → root)
        pass

    def test_specialized_agent_composition(self):
        """Test BASE_AGENT + specialized agent merge."""
        # Load BASE_AGENT_TEMPLATE.md
        # Load BASE_RESEARCH.md
        # Verify merge produces correct composition
        pass

    def test_tool_authorization_inheritance(self):
        """Test tool authorization from base to specialized."""
        # Verify specialized agent inherits base tools
        # Verify specialized agent can restrict tools
        pass
```

---

## Implementation Roadmap

### Phase 2 Sprint Breakdown

**Sprint 1: BASE_AGENT Testing Foundation** (Week 1)
- Create BASE_AGENT test directory structure
- Implement 2 BASE_AGENT custom metrics
- Create 20 BASE_AGENT behavioral scenarios
- Write 5 BASE_AGENT integration tests
- Document BASE_AGENT testing approach

**Sprint 2: Research + Engineer Agent Testing** (Week 2)
- Implement Research agent metrics (2)
- Create Research scenarios (15)
- Write Research integration tests (4)
- Implement Engineer agent metrics (3)
- Create Engineer scenarios (25)
- Write Engineer integration tests (6)

**Sprint 3: QA + Ops Agent Testing** (Week 3)
- Implement QA agent metrics (3)
- Create QA scenarios (20)
- Write QA integration tests (5)
- Implement Ops agent metrics (2)
- Create Ops scenarios (18)
- Write Ops integration tests (5)

**Sprint 4: Documentation + Prompt Engineer Testing** (Week 4)
- Implement Documentation agent metrics (2)
- Create Documentation scenarios (12)
- Write Documentation integration tests (3)
- Implement Prompt Engineer agent metrics (2)
- Create Prompt Engineer scenarios (15)
- Write Prompt Engineer integration tests (4)

**Sprint 5: Integration + Performance Testing** (Week 5)
- Implement agent merge process testing
- Create performance benchmarks for all agents
- Integration testing across all agents
- Response capture/replay for all agents
- Golden baseline management

**Sprint 6: Documentation + Polish** (Week 6)
- Comprehensive documentation (README_AGENTS.md)
- Usage guides for each agent type
- Troubleshooting guides
- CI/CD integration examples
- Final verification and testing

### Deliverables Timeline

| Week | Deliverables | Files | LOC | Tests |
|------|--------------|-------|-----|-------|
| 1 | BASE_AGENT foundation | 10 | 800 | 8 |
| 2 | Research + Engineer | 15 | 1,200 | 14 |
| 3 | QA + Ops | 15 | 1,100 | 13 |
| 4 | Documentation + Prompt | 12 | 900 | 9 |
| 5 | Integration + Performance | 8 | 600 | 16 |
| 6 | Documentation | 5 | 1,500 | N/A |
| **Total** | **Phase 2 Complete** | **65** | **6,100** | **60** |

### Resource Requirements

**Development Effort**:
- Metrics development: 16 metrics × 2 hours = 32 hours
- Scenario creation: 125 scenarios × 0.5 hours = 63 hours
- Test implementation: 60 tests × 1 hour = 60 hours
- Integration testing: 16 hours
- Documentation: 20 hours
- **Total Effort**: ~191 hours (≈5 weeks @ 40 hours/week)

**Dependencies**:
- Phase 1 DeepEval framework (Complete ✅)
- BASE_AGENT template files (Available ✅)
- Agent specialization files (Available ✅)
- pytest + pytest-asyncio (Installed ✅)
- DeepEval >= 1.0.0 (Installed ✅)

**External Dependencies**:
- None (all testing uses mock agents like Phase 1)

---

## Appendices

### Appendix A: File Analysis Summary

**Files Analyzed** (23 files):
1. `/Users/masa/Projects/claude-mpm/tests/eval/README.md` (405 lines)
2. `/Users/masa/Projects/claude-mpm/tests/eval/IMPLEMENTATION_SUMMARY.md` (353 lines)
3. `/Users/masa/Projects/claude-mpm/tests/eval/PM_BEHAVIORAL_TESTING.md` (523 lines)
4. `/Users/masa/Projects/claude-mpm/tests/eval/INTEGRATION_IMPLEMENTATION.md` (525 lines)
5. `/Users/masa/Projects/claude-mpm/docs/research/deepeval-complete-implementation-summary.md` (600+ lines)
6. `/Users/masa/Projects/claude-mpm/src/claude_mpm/agents/BASE_AGENT_TEMPLATE.md` (292 lines)
7. `/Users/masa/Projects/claude-mpm/src/claude_mpm/agents/BASE_RESEARCH.md` (52 lines)
8. `/Users/masa/Projects/claude-mpm/src/claude_mpm/agents/BASE_ENGINEER.md` (657 lines)
9. `/Users/masa/Projects/claude-mpm/src/claude_mpm/agents/BASE_QA.md` (166 lines)
10. `/Users/masa/Projects/claude-mpm/src/claude_mpm/agents/BASE_OPS.md` (218 lines)
11. `/Users/masa/Projects/claude-mpm/src/claude_mpm/agents/BASE_DOCUMENTATION.md` (52 lines)
12. `/Users/masa/Projects/claude-mpm/src/claude_mpm/agents/BASE_PM.md` (479 lines)
13. `/Users/masa/Projects/claude-mpm/src/claude_mpm/agents/BASE_PROMPT_ENGINEER.md` (787 lines)
14. `/Users/masa/Projects/claude-mpm/src/claude_mpm/services/agents/deployment/agent_template_builder.py` (150+ lines sampled)

**Agent Template Files** (13 templates):
- circuit-breakers.md (36,961 bytes)
- response-format.md (21,354 bytes)
- research-gate-examples.md (20,376 bytes)
- pm-examples.md (16,804 bytes)
- git-file-tracking.md (18,842 bytes)
- + 8 more templates

### Appendix B: GitHub Issues Summary

**Phase 1 Closed Issues**:

1. **Issue #97**: Implement base DeepEval framework infrastructure
   - Closed: Dec 5, 2025
   - Deliverables: 4 metrics, parser, 16 scenarios, fixtures
   - Files: 19 files, 1,764 LOC

2. **Issue #102**: Create comprehensive eval system documentation
   - Closed: Dec 5, 2025
   - Deliverables: Architecture docs, usage guides, CI/CD examples
   - Files: 4,197 lines documentation

### Appendix C: Test File Inventory

**Phase 1 Test Files** (23 Python files):
```
tests/eval/
├── __init__.py
├── conftest.py (24 fixtures)
├── verify_installation.py
├── verify_integration_framework.py
├── test_quickstart_demo.py
├── run_pm_validation.py
├── run_pm_behavioral_tests.py
├── test_cases/
│   ├── __init__.py
│   ├── ticketing_delegation.py
│   ├── circuit_breakers.py
│   ├── integration_ticketing.py
│   ├── performance.py
│   ├── test_pm_behavioral_compliance.py
│   └── test_pm_behavior_validation.py
├── metrics/
│   ├── __init__.py
│   ├── instruction_faithfulness.py
│   └── delegation_correctness.py
├── utils/
│   ├── __init__.py
│   ├── pm_response_parser.py
│   ├── pm_response_capture.py
│   ├── response_replay.py
│   └── pm_response_simulator.py
└── scenarios/
    └── __init__.py
```

### Appendix D: Vector Search Status

**Vector Search Index**: Available ✅
- **Project**: /Users/masa/Projects/managed/mcp-ticketer (note: different project)
- **Total Chunks**: 33,705
- **Total Files**: 1,018
- **Index Size**: 33.70 MB
- **File Extensions**: .py, .js, .ts, .jsx, .tsx, .json, .md, etc.
- **Languages**: bash, javascript, json, markdown, python

**Note**: Vector search is available but currently indexed for mcp-ticketer project. Phase 2 could leverage vector search for agent pattern discovery.

### Appendix E: Recommended Reading

**Phase 1 Documentation** (Read First):
1. `tests/eval/README.md` - Base framework overview
2. `tests/eval/IMPLEMENTATION_SUMMARY.md` - Phase 1 deliverables
3. `tests/eval/README_INTEGRATION.md` - Integration testing guide
4. `tests/eval/PM_BEHAVIORAL_TESTING.md` - Behavioral testing patterns

**Agent Architecture** (Read Second):
1. `src/claude_mpm/agents/BASE_AGENT_TEMPLATE.md` - Core patterns
2. `src/claude_mpm/agents/BASE_ENGINEER.md` - Engineering patterns
3. `src/claude_mpm/agents/BASE_RESEARCH.md` - Research patterns
4. `src/claude_mpm/agents/BASE_QA.md` - QA patterns

**Template Files** (Reference):
1. `src/claude_mpm/agents/templates/circuit-breakers.md` - Circuit breaker definitions
2. `src/claude_mpm/agents/templates/response-format.md` - Response structure

---

## Conclusion

Phase 1 successfully established a robust DeepEval framework for PM agent testing with 4,092 LOC, 25+ tests, and comprehensive documentation. Phase 2 will extend this foundation to test BASE_AGENT + 6 specialized agents, adding ~6,100 LOC, 60 tests, and complete agent behavioral coverage.

**Key Success Factors**:
1. ✅ Proven Phase 1 architecture (extensible, well-documented)
2. ✅ Clear agent behavioral patterns (BASE_AGENT + specializations)
3. ✅ Hierarchical merge process understood (template builder analysis)
4. ✅ Custom metric framework ready (16 new metrics planned)
5. ✅ Integration testing infrastructure available (capture/replay/performance)

**Next Steps**:
1. Create Phase 2 GitHub issues (7 issues: BASE_AGENT + 6 agents)
2. Assign labels: enhancement, testing, deepeval, agent-eval
3. Start Sprint 1: BASE_AGENT testing foundation
4. Follow 6-week roadmap to completion

**Estimated Completion**: 6 weeks (191 hours development effort)

---

**Research Complete**: December 5, 2025
**Researcher**: Claude (Research Agent)
**Document Version**: 1.0.0
**Status**: Ready for Phase 2 Implementation ✅
