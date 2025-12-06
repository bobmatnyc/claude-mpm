# Engineer Agent Testing Specifications for Sprint 3 (#109)

**Research Date**: December 6, 2025
**Project**: Claude MPM Framework - DeepEval Phase 2
**GitHub Issue**: #109 (Engineer Agent Testing)
**Status**: Ready for Implementation
**Researcher**: Claude (Research Agent)

---

## Executive Summary

This research document provides comprehensive specifications for implementing Engineer Agent testing as part of DeepEval Phase 2, Sprint 3 (Issue #109). The Engineer Agent has unique behavioral requirements focused on **code minimization**, **anti-pattern detection**, and **consolidation**, requiring specialized metrics and test scenarios.

**Key Findings**:
- **BASE_ENGINEER.md**: 657 LOC of behavioral specifications (most complex agent)
- **Required Deliverables**: 3 custom metrics, 25 scenarios (4 categories), 6 integration tests
- **Existing Patterns**: BASE_AGENT and Research Agent implementations provide clear templates
- **Implementation Estimate**: 32 hours (4 days) based on complexity analysis
- **Unique Challenges**: Quantitative metrics (LOC delta, consolidation rate) require code analysis

---

## Table of Contents

1. [Current Implementation Status](#current-implementation-status)
2. [Engineer Agent Behavioral Specifications](#engineer-agent-behavioral-specifications)
3. [Required Custom Metrics (3)](#required-custom-metrics-3)
4. [Scenario Categories (25 scenarios)](#scenario-categories-25-scenarios)
5. [Integration Tests (6 tests)](#integration-tests-6-tests)
6. [Implementation Patterns from Existing Agents](#implementation-patterns-from-existing-agents)
7. [Recommended Implementation Approach](#recommended-implementation-approach)
8. [Gaps and Missing Information](#gaps-and-missing-information)

---

## Current Implementation Status

### DeepEval Infrastructure (Issue #106)

**Status**: ✅ 100% Complete (Dec 6, 2025)

**Available Infrastructure**:
- `tests/eval/agents/shared/agent_response_parser.py` (688 LOC)
  - Generic parser with Engineer-specific methods already implemented
  - `parse_engineer_patterns()`: Search tool usage, consolidation mentions, LOC delta, mock data detection
- `tests/eval/agents/shared/agent_test_base.py` (379 LOC)
  - `EngineerAgentTest` base class ready to use
  - Common assertions: `assert_search_before_create()`, `assert_no_mock_data()`
- `tests/eval/agents/shared/agent_fixtures.py` (674 LOC)
  - Engineer-specific fixtures: `engineer_agent_template`, `mock_engineer_agent_response`
  - Sample code files for testing consolidation patterns
- `tests/eval/conftest.py` (674 LOC)
  - Pytest configuration for agent testing

### BASE_AGENT Testing (Issue #107)

**Status**: ✅ Implementation Complete (Dec 6, 2025)

**Completed Deliverables**:
- 5 test files implemented (`test_verification_patterns.py`, `test_memory_protocol.py`, etc.)
- 2 custom metrics (VerificationComplianceMetric, MemoryProtocolMetric)
- 20 scenarios across 4 categories
- 5 integration tests
- Provides **complete pattern template** for Engineer Agent testing

### Research Agent Testing (Issue #108)

**Status**: ✅ Implementation Complete (Dec 6, 2025)

**Completed Deliverables**:
- 4 test files implemented (`test_memory_protocol.py`, `test_discovery_patterns.py`, etc.)
- 2 custom metrics (MemoryEfficiencyMetric, SamplingStrategyMetric)
- 15 scenarios across 3 categories
- 4 integration tests
- Demonstrates **specialized metric patterns** for behavioral testing

### Engineer Agent Testing (Issue #109)

**Status**: ❌ Not Started - Directory skeleton only

**Current State**:
```
tests/eval/agents/engineer/
└── __init__.py (23 LOC)
```

**Missing Components**:
- Custom metrics (3): CodeMinimizationMetric, ConsolidationMetric, AntiPatternDetectionMetric
- Scenario JSON files (4 categories, 25 total scenarios)
- Test harness files (4-5 test files)
- Integration tests (6 tests)
- conftest.py with Engineer-specific fixtures

---

## Engineer Agent Behavioral Specifications

### Source Document Analysis

**File**: `src/claude_mpm/agents/BASE_ENGINEER.md`
**Size**: 657 LOC (largest agent specification)
**Complexity**: High - Quantitative metrics and code analysis requirements

### Core Behavioral Categories

#### 1. **Code Minimization Mandate** (Lines 7-30)

**Primary Objective**: Zero Net New Lines (≤0 LOC delta per feature)

**Key Requirements**:
- Pre-Implementation Protocol:
  1. Search First (80% time): Vector search + grep for existing solutions
  2. Enhance vs Create: Extend existing code before writing new
  3. Configure vs Code: Solve through data/config when possible
  4. Consolidate Opportunities: Identify code to DELETE while implementing

- **Maturity-Based Thresholds**:
  - `< 1000 LOC`: Establish reusable foundations
  - `1000-10k LOC`: Active consolidation (target: 50%+ reuse rate)
  - `> 10k LOC`: Require approval for net positive LOC
  - Legacy: Mandatory negative LOC impact

- **Falsifiable Consolidation Criteria**:
  - Consolidate functions with >80% code similarity (Levenshtein distance <20%)
  - Extract common logic when shared blocks >50 lines
  - Require approval for any PR with net positive LOC in mature projects
  - Merge implementations when same domain AND >80% similarity
  - Extract abstractions when different domains AND >50% similarity

**Testing Implications**:
- Need **quantitative metrics** to measure LOC delta
- Must detect **search-first patterns** in responses
- Validate **reuse rate calculations** in agent output
- Check for **consolidation mentions** before new code creation

#### 2. **Anti-Pattern: Mock Data and Fallback Behavior** (Lines 31-114)

**Critical Rule**: Mock data and fallbacks are engineering anti-patterns

**Mock Data Restrictions**:
- Default: Mock data is ONLY for testing purposes
- Production Code: NEVER use mock/dummy data in production code
- Exception: ONLY when explicitly requested by user
- Testing: Mock data belongs in test files, not implementation

**Fallback Behavior Prohibition**:
- Default: Fallback behavior is terrible engineering practice
- Banned Pattern: Don't silently fall back to defaults when operations fail
- Correct Approach: Fail explicitly, log errors, propagate exceptions
- Exception Cases (very limited):
  - Configuration with documented defaults (e.g., port numbers, timeouts)
  - Graceful degradation in user-facing features (with explicit logging)
  - Feature flags for A/B testing (with measurement)

**Examples of Violations** (Lines 57-108):
```python
# ❌ WRONG - Silent Fallback
def get_user_data(user_id):
    try:
        return database.fetch_user(user_id)
    except Exception:
        return {"id": user_id, "name": "Unknown"}  # TERRIBLE!

# ✅ CORRECT - Explicit Error
def get_user_data(user_id):
    try:
        return database.fetch_user(user_id)
    except DatabaseError as e:
        logger.error(f"Failed to fetch user {user_id}: {e}")
        raise  # Propagate the error
```

**Testing Implications**:
- Must detect **mock data patterns** in code responses
- Identify **silent exception handling** (try/except without logging/propagation)
- Validate **explicit error handling** with logging
- Distinguish **acceptable fallbacks** (documented defaults) from violations

#### 3. **Duplicate Elimination Protocol** (Lines 115-203)

**MANDATORY**: Before ANY implementation, actively search for duplicate code

**Critical Principles**:
- Single Source of Truth: Every feature must have ONE active implementation path
- Duplicate Elimination: Previous session artifacts must be detected and consolidated
- Search-First Implementation: Use vector search and grep tools to find existing implementations
- Consolidate or Remove: Never leave duplicate code paths in production

**Pre-Implementation Detection Protocol** (Lines 126-138):
1. Vector Search First: Use `mcp__mcp-vector-search__search_code`
2. Grep for Patterns: Search for function names, class definitions
3. Check Multiple Locations: Look in common directories where duplicates accumulate
4. Identify Session Artifacts: Numbered suffixes, timestamp-based names, `_old`, `_backup`, `_temp`

**Consolidation Decision Tree** (Lines 140-153):
- **Same Domain + >80% Similarity** → CONSOLIDATE (create shared utility)
- **Different Domains + >50% Similarity** → EXTRACT COMMON (create abstraction)
- **Different Domains + <50% Similarity** → LEAVE SEPARATE (document why)

**When NOT to Consolidate** (Lines 148-153):
- Cross-domain logic with different business rules
- Performance hotspots with different optimization needs
- Code with different change frequencies (stable vs. rapidly evolving)
- Test code vs. production code (keep test duplicates for clarity)

**Testing Implications**:
- Must detect **vector search usage** before implementation
- Validate **consolidation mentions** when similar code exists
- Check for **duplicate detection patterns** (grep, search tools)
- Identify **session artifact cleanup** (removal of `_old`, `_v2` files)

#### 4. **Debugging and Problem-Solving Methodology** (Lines 204-247)

**Debug First Protocol (MANDATORY)**:
Before writing ANY fix or optimization:
1. Check System Outputs: Review logs, network requests, error messages
2. Identify Root Cause: Investigate actual failure point, not symptoms
3. Implement Simplest Fix: Solve root cause with minimal code change
4. Test Core Functionality: Verify fix works WITHOUT optimization layers
5. Optimize If Measured: Add performance improvements only after metrics prove need

**Problem-Solving Principles**:
- Root Cause Over Symptoms
- Simplicity Before Complexity
- Correctness Before Performance
- Visibility Into Hidden States
- Measurement Before Assumption

**Testing Implications**:
- Detect **root cause analysis** in debugging responses
- Validate **measurement/profiling** before optimization
- Check for **simplicity-first solutions** vs. complex patterns
- Identify **optimization justification** with profiling data

#### 5. **Test Process Management** (Lines 604-649)

**CRITICAL**: Never use watch mode during agent operations (causes memory leaks)

**Non-Interactive Mode Requirements**:
```bash
# CORRECT - CI-safe test execution
CI=true npm test
npx vitest run --reporter=verbose
npx jest --ci --no-watch

# WRONG - Causes memory leaks
npm test  # May trigger watch mode
npm test -- --watch  # Never terminates
vitest  # Default may be watch mode
```

**Process Cleanup Requirements**:
- Check for hanging test processes after running tests
- Kill orphaned processes if found (pkill -f "vitest" || pkill -f "jest")
- Verify process termination before continuing

**Testing Implications**:
- Detect **CI mode flags** in test commands (CI=true, --ci, --no-watch, run)
- Validate **process cleanup mentions** after test execution
- Check for **watch mode avoidance** patterns
- Identify **package.json test script validation** before running

#### 6. **Engineering Quality Documentation Standards** (Lines 265-549)

**MANDATORY Documentation Requirements**:
- Design Decision Documentation
- Alternatives Considered
- Trade-offs Analysis
- Future Extensibility
- Performance Analysis (RECOMMENDED)
- Optimization Suggestions (RECOMMENDED)
- Error Case Documentation (MANDATORY)
- Usage Examples (RECOMMENDED)

**Testing Implications**:
- Not directly testable with automated metrics
- Could use **documentation presence checks** in responses
- Validate **design rationale mentions** for significant implementations

---

## Required Custom Metrics (3)

Based on BASE_ENGINEER.md analysis and existing metric patterns (Research Agent), three custom metrics are required:

### Metric 1: CodeMinimizationMetric

**Purpose**: Evaluate Engineer Agent compliance with code minimization mandate

**Scoring Components** (weighted average):
1. **Search-First Evidence (30%)**: Detection of vector search or grep usage before implementation
   - Patterns: `mcp__mcp-vector-search__search_code`, `grep`, `searching for existing`
   - Score: 1.0 if search detected, 0.0 if no search

2. **LOC Delta Reporting (25%)**: Mentions net lines added/removed
   - Patterns: `+X/-Y lines`, `net LOC: -15`, `removed 50 lines, added 30`
   - Score: 1.0 if reported, 0.5 if partial, 0.0 if missing

3. **Reuse Rate (20%)**: References leveraging existing code
   - Patterns: `reused 60% existing`, `extended existing utility`, `no new code needed`
   - Score: Based on reuse percentage (>50% = 1.0, 25-50% = 0.5, <25% = 0.0)

4. **Consolidation Mentions (15%)**: Identifies opportunities to delete code
   - Patterns: `consolidated X functions`, `removed duplicate`, `merged implementations`
   - Score: 1.0 if consolidation performed, 0.5 if mentioned, 0.0 if ignored

5. **Config vs Code (10%)**: Solves through configuration/data when possible
   - Patterns: `added to config`, `data-driven approach`, `configuration change`
   - Score: 1.0 if config-based, 0.5 if mixed, 0.0 if pure code

**Thresholds**:
- **1.0**: Perfect code minimization (search-first, negative LOC, high reuse)
- **0.8-0.99**: Good minimization (most principles followed)
- **0.6-0.79**: Acceptable (some minimization, but room for improvement)
- **0.0-0.59**: Poor (code bloat, no search, low reuse)

**Pass Threshold**: 0.8 (80% compliance)

**Similar Pattern**: Research Agent's `MemoryEfficiencyMetric` (5 weighted components, 0.9 threshold)

---

### Metric 2: ConsolidationMetric

**Purpose**: Evaluate duplicate detection and consolidation compliance

**Scoring Components** (weighted average):
1. **Duplicate Detection (35%)**: Evidence of searching for duplicates before implementation
   - Patterns: `searching for similar`, `checking for duplicates`, `found existing implementation`
   - Tools: Vector search, grep for function names, file similarity checks
   - Score: 1.0 if detection performed, 0.0 if skipped

2. **Consolidation Decision (30%)**: Correct decision-making for found duplicates
   - Same Domain + >80% Similarity → Consolidate (Score: 1.0)
   - Different Domains + >50% Similarity → Extract Common (Score: 1.0)
   - Different Domains + <50% Similarity → Leave Separate (Score: 1.0)
   - Wrong decision (Score: 0.0)

3. **Implementation Quality (20%)**: When consolidating, follows proper protocol
   - Patterns: `merged best features`, `updated all references`, `removed obsolete`
   - Score: 1.0 if all steps followed, 0.5 if partial, 0.0 if incorrect

4. **Single-Path Enforcement (10%)**: Ensures only ONE implementation path
   - Patterns: `single source of truth`, `removed duplicate path`, `canonical implementation`
   - Score: 1.0 if enforced, 0.0 if multiple paths remain

5. **Session Artifact Cleanup (5%)**: Removes old versions and backups
   - Patterns: `removed _old files`, `deleted backup`, `cleaned up _v2`
   - Score: 1.0 if cleanup performed, 0.5 if mentioned, 0.0 if ignored

**Thresholds**:
- **1.0**: Perfect consolidation (detects duplicates, correct decisions, cleanup)
- **0.8-0.99**: Good consolidation (most duplicates handled)
- **0.6-0.79**: Acceptable (some duplicate detection, but missed opportunities)
- **0.0-0.59**: Poor (no duplicate detection, multiple implementations remain)

**Pass Threshold**: 0.85 (85% compliance)

**Similar Pattern**: Research Agent's `SamplingStrategyMetric` (5 weighted components, 0.85 threshold)

---

### Metric 3: AntiPatternDetectionMetric

**Purpose**: Evaluate avoidance of mock data and silent fallbacks

**Scoring Components** (weighted average):
1. **No Mock Data in Production (40%)**: Ensures no mock/dummy data in production code
   - Anti-patterns: `"mock_key"`, `{"id": 1, "name": "Test"}`, `dummy_data`, `fake_response`
   - Exceptions: Test files (acceptable), explicit user request (acceptable)
   - Score: 1.0 if no violations, 0.0 if mock data found in production

2. **No Silent Fallbacks (30%)**: Ensures explicit error handling
   - Anti-patterns: `except: return default`, `except: pass`, `except: return {}`
   - Correct: `except as e: logger.error(); raise`, `except: log and fail`
   - Score: 1.0 if no silent fallbacks, 0.5 if partial logging, 0.0 if silent

3. **Explicit Error Propagation (20%)**: Validates errors are logged and raised
   - Required: `logger.error()`, `raise`, `propagate exception`
   - Score: 1.0 if explicit, 0.5 if logged but not raised, 0.0 if suppressed

4. **Acceptable Fallback Justification (10%)**: When fallbacks exist, are they justified?
   - Acceptable: Documented defaults (ports, timeouts), graceful degradation with logging
   - Required: Comments explaining why fallback is acceptable
   - Score: 1.0 if justified, 0.5 if partial, 0.0 if unjustified

**Thresholds**:
- **1.0**: Perfect anti-pattern avoidance (no mock data, explicit errors)
- **0.9-0.99**: Minor issues (one acceptable fallback)
- **0.7-0.89**: Some violations (silent error handling)
- **0.0-0.69**: Major violations (mock data in production, silent failures)

**Pass Threshold**: 0.9 (90% compliance - strict due to production impact)

**Similar Pattern**: BASE_AGENT's `VerificationComplianceMetric` (4 weighted components, 0.9 threshold)

---

## Scenario Categories (25 scenarios)

Based on BASE_ENGINEER.md behavioral requirements, 25 scenarios across 4 categories:

### Category 1: Code Minimization (10 scenarios)

**Priority**: Critical/High
**Scenario ID Pattern**: `MIN-E-001` to `MIN-E-010`

**Scenarios**:

1. **MIN-E-001: Search-First Before Implementation**
   - Input: User asks to implement feature
   - Expected: Vector search or grep for existing implementations BEFORE coding
   - Success: Search detected, reuse identified
   - Failure: Immediately starts coding without search

2. **MIN-E-002: Extend Existing vs. Create New**
   - Input: Feature request that could extend existing module
   - Expected: Identifies existing module, proposes extension over new file
   - Success: Extension approach chosen, justification provided
   - Failure: Creates new file without considering existing modules

3. **MIN-E-003: Configuration Over Code**
   - Input: Request for feature that could be data-driven
   - Expected: Proposes config/data approach before code implementation
   - Success: Config-based solution, minimal code changes
   - Failure: Implements feature entirely in code

4. **MIN-E-004: LOC Delta Reporting**
   - Input: Complete implementation task
   - Expected: Reports net LOC impact (+X/-Y lines)
   - Success: Clear LOC delta reported with justification
   - Failure: No LOC metrics mentioned

5. **MIN-E-005: Reuse Rate Calculation**
   - Input: Feature implementation
   - Expected: Reports percentage of existing code leveraged
   - Success: Reuse rate reported (e.g., "60% existing code reused")
   - Failure: No reuse metrics, all new code

6. **MIN-E-006: Maturity Threshold Compliance (<1000 LOC)**
   - Input: Small codebase (800 LOC), feature request
   - Expected: Establishes reusable foundations (abstractions, utilities)
   - Success: Foundations created for future reuse
   - Failure: Point solution with no reusability

7. **MIN-E-007: Maturity Threshold Compliance (1000-10k LOC)**
   - Input: Medium codebase (5000 LOC), feature request
   - Expected: Active consolidation, targets 50%+ reuse rate
   - Success: Consolidation performed, high reuse rate achieved
   - Failure: Pure addition without consolidation

8. **MIN-E-008: Maturity Threshold Compliance (>10k LOC)**
   - Input: Large codebase (15000 LOC), feature request
   - Expected: Requires approval for net positive LOC, prefers negative LOC
   - Success: Negative LOC impact OR explicit approval request
   - Failure: Net positive LOC without approval or justification

9. **MIN-E-009: Consolidation Opportunity Identification**
   - Input: Implementation task in codebase with similar existing code
   - Expected: Identifies consolidation opportunity, deletes old code while implementing
   - Success: Old code removed, new implementation consolidated
   - Failure: Adds new code without removing similar old code

10. **MIN-E-010: Zero Net New Lines Victory**
    - Input: Complex feature request
    - Expected: Achieves feature implementation with ≤0 LOC delta
    - Success: Feature complete with negative or zero LOC impact
    - Failure: Feature complete but with significant LOC increase

**Metrics Used**: CodeMinimizationMetric (threshold: 0.8)

---

### Category 2: Consolidation & Duplicate Elimination (7 scenarios)

**Priority**: High/Medium
**Scenario ID Pattern**: `CONS-E-001` to `CONS-E-007`

**Scenarios**:

1. **CONS-E-001: Duplicate Detection with Vector Search**
   - Input: Implementation request
   - Expected: Uses `mcp__mcp-vector-search__search_code` to find similar code
   - Success: Vector search performed, duplicates identified
   - Failure: No search, duplicates undetected

2. **CONS-E-002: Consolidation Decision (Same Domain, >80% Similarity)**
   - Input: Found duplicate function in same domain with 85% similarity
   - Expected: Consolidates into shared utility
   - Success: Consolidation performed, references updated
   - Failure: Leaves duplicate OR wrong consolidation approach

3. **CONS-E-003: Extract Common Pattern (Different Domains, >50% Similarity)**
   - Input: Found similar logic in different domains with 60% similarity
   - Expected: Extracts common abstraction
   - Success: Abstraction created, both domains use it
   - Failure: Leaves duplicated OR consolidates incorrectly

4. **CONS-E-004: Leave Separate (Different Domains, <50% Similarity)**
   - Input: Found similar-looking code in different domains with 40% similarity
   - Expected: Leaves separate with documentation explaining why
   - Success: Left separate, rationale documented
   - Failure: Attempts consolidation OR no documentation

5. **CONS-E-005: Session Artifact Cleanup**
   - Input: Codebase with `_old`, `_v2`, `_backup` files
   - Expected: Identifies session artifacts, removes obsolete versions
   - Success: Artifacts removed, single source of truth established
   - Failure: Artifacts remain, multiple implementations coexist

6. **CONS-E-006: Single-Path Enforcement**
   - Input: Feature with two competing implementations
   - Expected: Chooses superior implementation, removes inferior one
   - Success: Single path established, inferior removed with justification
   - Failure: Both paths remain OR wrong implementation chosen

7. **CONS-E-007: A/B Test Exception Handling**
   - Input: Feature with two implementations for A/B testing
   - Expected: Recognizes A/B test, validates measurement and sunset plan
   - Success: A/B test preserved with tracking, sunset plan documented
   - Failure: Incorrectly removes A/B test OR allows untracked duplicates

**Metrics Used**: ConsolidationMetric (threshold: 0.85)

---

### Category 3: Anti-Pattern Avoidance (5 scenarios)

**Priority**: Critical
**Scenario ID Pattern**: `ANTI-E-001` to `ANTI-E-005`

**Scenarios**:

1. **ANTI-E-001: No Mock Data in Production Code**
   - Input: Implementation requiring external API
   - Expected: Fails explicitly if API unavailable, no mock data fallback
   - Success: Explicit error handling, no mock data
   - Failure: Returns `{"api_key": "mock_key_12345"}` or similar

2. **ANTI-E-002: No Silent Fallback Behavior**
   - Input: Implementation with potential failure point
   - Expected: Logs error and propagates exception
   - Success: `except as e: logger.error(); raise`
   - Failure: `except: return default_value` (silent fallback)

3. **ANTI-E-003: Acceptable Fallback with Justification (Config Defaults)**
   - Input: Configuration value with acceptable default
   - Expected: Uses default with documentation (e.g., `PORT=8000`)
   - Success: Fallback used, explicitly documented as acceptable
   - Failure: Undocumented fallback OR inappropriate default

4. **ANTI-E-004: Graceful Degradation with Logging**
   - Input: Non-critical feature that can degrade gracefully
   - Expected: Logs degradation explicitly, continues with reduced functionality
   - Success: `logger.warning("CDN unavailable, using default")` + fallback
   - Failure: Silent degradation without logging

5. **ANTI-E-005: Mock Data Restricted to Test Files**
   - Input: Writing tests for feature
   - Expected: Mock data used in test files, not in production code
   - Success: Mock data only in `tests/` directory
   - Failure: Mock data in production code paths

**Metrics Used**: AntiPatternDetectionMetric (threshold: 0.9)

---

### Category 4: Test Process Management & Debugging (3 scenarios)

**Priority**: High
**Scenario ID Pattern**: `PROC-E-001` to `PROC-E-003`

**Scenarios**:

1. **PROC-E-001: CI-Safe Test Execution**
   - Input: Request to run tests in JavaScript/TypeScript project
   - Expected: Uses CI mode (CI=true npm test, vitest run, jest --ci)
   - Success: CI flags detected, no watch mode
   - Failure: Uses `npm test` without checking for watch mode

2. **PROC-E-002: Process Cleanup After Tests**
   - Input: After running tests
   - Expected: Checks for orphaned processes (ps aux | grep vitest)
   - Success: Process cleanup performed, orphans killed
   - Failure: Doesn't check for orphaned processes

3. **PROC-E-003: Root Cause Analysis Before Optimization**
   - Input: Performance issue reported
   - Expected: Profiles/measures before optimizing, identifies root cause
   - Success: Profiling data used, root cause addressed, simplest fix applied
   - Failure: Immediately applies complex optimization without measurement

**Metrics Used**: CodeMinimizationMetric (debugging), AntiPatternDetectionMetric (process management)

---

## Integration Tests (6 tests)

Based on Engineer Agent workflows and BASE_AGENT/Research Agent integration test patterns:

### Integration Test 1: Full Code Minimization Workflow

**Test Name**: `test_code_minimization_full_workflow`

**Scenario**:
1. User requests feature implementation
2. Engineer searches for existing implementations (vector search + grep)
3. Identifies opportunity to extend existing module
4. Proposes consolidation of similar code
5. Implements feature with negative LOC delta
6. Reports metrics (LOC delta, reuse rate, consolidation count)

**Expected Tools**:
- `mcp__mcp-vector-search__search_code`
- `Grep` (for pattern searching)
- `Read` (to review existing code)
- `Edit` (to implement changes)
- `Bash` (to run tests, verify behavior)

**Validation**:
- CodeMinimizationMetric score ≥ 0.8
- ConsolidationMetric score ≥ 0.85
- Verification evidence present (Edit → Read → Test)
- Memory protocol compliance (JSON response with metrics)

**Similar Pattern**: BASE_AGENT `test_template_merge_and_inheritance`, Research Agent `test_full_research_workflow`

---

### Integration Test 2: Duplicate Detection and Consolidation

**Test Name**: `test_duplicate_detection_and_consolidation`

**Scenario**:
1. User requests implementation of authentication helper
2. Engineer detects similar authentication utilities exist (vector search)
3. Analyzes similarity (>80% same domain)
4. Decides to consolidate into shared utility
5. Merges best features from all versions
6. Updates all references to new consolidated utility
7. Removes obsolete implementations
8. Documents decision

**Expected Tools**:
- `mcp__mcp-vector-search__search_code`
- `mcp__mcp-vector-search__search_similar`
- `Grep` (to find all references)
- `Edit` (to consolidate and update references)
- `Bash` (to run tests)

**Validation**:
- ConsolidationMetric score ≥ 0.85
- Duplicate detection evidence present
- Consolidation decision justified
- All references updated
- Obsolete code removed

**Similar Pattern**: Research Agent `test_file_size_check_and_summarizer`

---

### Integration Test 3: Anti-Pattern Prevention (Mock Data)

**Test Name**: `test_anti_pattern_prevention_mock_data`

**Scenario**:
1. User requests feature requiring external API integration
2. Engineer implements without mock data fallbacks
3. Adds explicit error handling (log + raise)
4. Writes tests with mock data in test files (acceptable)
5. Ensures production code has no mock data

**Expected Tools**:
- `Edit` (to implement feature)
- `Write` (to create test files)
- `Bash` (to run tests)
- `Read` (to verify implementation)

**Validation**:
- AntiPatternDetectionMetric score ≥ 0.9
- No mock data in production code
- Mock data present only in test files
- Explicit error handling (logger + raise)

**Similar Pattern**: BASE_AGENT `test_error_recovery_and_escalation`

---

### Integration Test 4: Test Process Management

**Test Name**: `test_safe_test_execution_with_cleanup`

**Scenario**:
1. User requests running tests in TypeScript project
2. Engineer checks package.json for test script configuration
3. Detects watch mode risk
4. Uses CI-safe command (CI=true npm test OR vitest run)
5. Runs tests in non-interactive mode
6. Checks for orphaned processes after tests
7. Kills orphans if found

**Expected Tools**:
- `Read` (to check package.json)
- `Bash` (to run tests: CI=true npm test)
- `Bash` (to check processes: ps aux | grep vitest)
- `Bash` (to cleanup: pkill -f vitest)

**Validation**:
- CI mode flags present (CI=true, --ci, run, --no-watch)
- Process cleanup performed
- No watch mode usage
- Memory-safe test execution

**Similar Pattern**: Research Agent `test_memory_protocol_integration`

---

### Integration Test 5: Debugging with Root Cause Analysis

**Test Name**: `test_debugging_root_cause_first`

**Scenario**:
1. User reports performance issue ("endpoint slow")
2. Engineer checks system outputs (logs, network requests)
3. Profiles/measures actual performance bottleneck
4. Identifies root cause (N+1 query problem)
5. Implements simplest fix (eager loading)
6. Tests fix without optimization layers
7. Verifies performance improvement
8. Only then considers additional optimizations if needed

**Expected Tools**:
- `Grep` (to search logs)
- `Read` (to review code)
- `Bash` (to run profiling: python -m cProfile)
- `Edit` (to implement fix)
- `Bash` (to run tests and verify)

**Validation**:
- CodeMinimizationMetric score ≥ 0.8 (simplest fix)
- Evidence of profiling/measurement
- Root cause addressed (not symptoms)
- Simplicity before complexity

**Similar Pattern**: BASE_AGENT `test_multi_tool_workflow_with_verification_chain`

---

### Integration Test 6: Cross-Agent Consolidation Consistency

**Test Name**: `test_cross_agent_consolidation_consistency`

**Scenario**:
Test Engineer Agent behavioral consistency when delegated by PM across 3 different implementation requests:
1. Simple feature (small codebase)
2. Complex feature (large codebase with duplicates)
3. Refactoring request (consolidation opportunity)

**Expected**:
- All 3 requests show search-first behavior
- All 3 requests report LOC delta
- Consolidation performed when applicable
- Consistent metric reporting format

**Validation**:
- CodeMinimizationMetric ≥ 0.8 for all 3 requests
- ConsolidationMetric ≥ 0.85 when duplicates exist
- AntiPatternDetectionMetric ≥ 0.9 for all 3 requests
- Memory protocol compliance across all requests

**Similar Pattern**: BASE_AGENT `test_cross_agent_behavioral_consistency`

---

## Implementation Patterns from Existing Agents

### BASE_AGENT Testing Pattern (Issue #107)

**File Structure**:
```
tests/eval/agents/base_agent/
├── conftest.py (fixtures for scenarios)
├── test_verification_patterns.py (Scenarios 1-8)
├── test_memory_protocol.py (Scenarios 9-15)
├── test_template_merging.py (Scenarios 16-18)
├── test_tool_orchestration.py (Scenarios 19-20)
└── test_integration.py (5 integration tests)
```

**Test File Pattern**:
```python
# tests/eval/agents/base_agent/test_verification_patterns.py
import pytest
from deepeval import assert_test
from deepeval.test_case import LLMTestCase

from tests.eval.metrics.base_agent.verification_compliance import VerificationComplianceMetric
from tests.eval.agents.shared.agent_test_base import BaseAgentTest


class TestVerificationPatterns(BaseAgentTest):
    """Test BASE_AGENT verification compliance (Scenarios 1-8)."""

    def test_scenario_01_file_edit_verification(self, base_agent_template):
        """VER-B-001: File Edit Must Be Verified with Read"""
        # Arrange
        test_case = LLMTestCase(
            input="Edit config.py to add new setting",
            actual_output="""I'll edit the config file and verify the change.

            Using Edit tool to add setting...
            Now reading back to verify: [shows file content with new setting]
            Verified: Setting successfully added.""",
            context=[base_agent_template]
        )
        metric = VerificationComplianceMetric(threshold=0.9)

        # Act
        metric.measure(test_case)

        # Assert
        assert metric.score >= 0.9, f"Expected ≥0.9, got {metric.score}"
        assert metric.is_successful()
        self.assert_verification_present(test_case.actual_output, ["Edit", "Read"])
```

**Key Patterns**:
- Uses `BaseAgentTest` from shared infrastructure
- Loads fixtures from conftest.py
- Uses DeepEval's `LLMTestCase` and `assert_test`
- Calls custom metrics for scoring
- Includes descriptive test names with scenario IDs

---

### Research Agent Testing Pattern (Issue #108)

**File Structure**:
```
tests/eval/agents/research/
├── conftest.py (scenario loading fixtures)
├── test_memory_protocol.py (MEM-R-001 to MEM-R-006)
├── test_discovery_patterns.py (DSC-R-001 to DSC-R-005)
├── test_output_requirements.py (OUT-R-001 to OUT-R-004)
└── test_integration.py (4 integration tests)
```

**Scenario JSON Pattern**:
```json
// tests/eval/scenarios/research/memory_scenarios.json
{
  "category": "memory",
  "description": "Memory Management Protocol scenarios for Research Agent",
  "total_scenarios": 6,
  "scenarios": [
    {
      "scenario_id": "MEM-R-001",
      "name": "File Size Check Before Reading",
      "category": "memory",
      "priority": "critical",
      "description": "Research must check file size before reading files >20KB...",
      "input": {
        "user_request": "Research how authentication works in this codebase",
        "context": "Large codebase with auth.py (45KB), middleware.py (12KB)...",
        "files": ["src/auth.py", "src/middleware.py"]
      },
      "expected_behavior": {
        "should_do": [
          "Check file sizes using Glob or file info tools",
          "Use document summarizer for auth.py (>20KB)"
        ],
        "should_not_do": [
          "Read auth.py (45KB) without size check"
        ],
        "required_tools": ["Glob", "Read", "DocumentSummarizer"]
      },
      "success_criteria": [
        "File size check performed before reading",
        "Summarizer used for auth.py (>20KB)"
      ],
      "metrics": {
        "MemoryEfficiencyMetric": {"threshold": 0.9}
      }
    }
  ]
}
```

**Metric Implementation Pattern**:
```python
# tests/eval/metrics/research/memory_efficiency_metric.py
from deepeval.metrics import BaseMetric
from deepeval.test_case import LLMTestCase


class MemoryEfficiencyMetric(BaseMetric):
    """DeepEval metric for Research Agent memory efficiency compliance."""

    SIZE_CHECK_PATTERNS = [
        r'file\s+size\s*[:\-]?\s*\d+',
        r'(\d+)\s*(KB|MB|bytes)',
        r'checking\s+size'
    ]

    SUMMARIZER_PATTERNS = [
        r'document_summarizer',
        r'summariz(?:e|ing|ed)'
    ]

    def __init__(self, threshold: float = 0.9):
        self.threshold = threshold
        self.score = 0.0
        self.reason = ""

    def measure(self, test_case: LLMTestCase):
        output = test_case.actual_output.lower()

        # 1. File Size Check (25%)
        size_check_score = self._check_file_size_patterns(output)

        # 2. Summarizer Usage (25%)
        summarizer_score = self._check_summarizer_patterns(output)

        # 3. File Limit Compliance (20%)
        file_limit_score = self._check_file_limits(output)

        # 4. Strategic Sampling (20%)
        sampling_score = self._check_sampling_patterns(output)

        # 5. No Brute Force (10%)
        brute_force_score = self._check_no_brute_force(output)

        # Weighted average
        self.score = (
            size_check_score * 0.25 +
            summarizer_score * 0.25 +
            file_limit_score * 0.20 +
            sampling_score * 0.20 +
            brute_force_score * 0.10
        )

        self.reason = self._generate_reason()
        return self.score

    def is_successful(self) -> bool:
        return self.score >= self.threshold

    # ... helper methods for pattern detection
```

**Key Patterns**:
- Scenario JSON files with detailed specifications
- Custom metrics extending `BaseMetric` from DeepEval
- Weighted scoring with multiple components (5 components for Research)
- Pattern-based detection using regex
- Clear success/failure criteria

---

## Recommended Implementation Approach

Based on existing patterns (BASE_AGENT and Research Agent) and Engineer Agent complexity:

### Phase 1: Custom Metrics Implementation (8-10 hours)

**Directory**: `tests/eval/metrics/engineer/`

**Files to Create**:
1. `__init__.py` - Metric exports
2. `code_minimization_metric.py` - CodeMinimizationMetric implementation
3. `consolidation_metric.py` - ConsolidationMetric implementation
4. `anti_pattern_detection_metric.py` - AntiPatternDetectionMetric implementation
5. `test_code_minimization.py` - Unit tests for CodeMinimizationMetric
6. `test_consolidation.py` - Unit tests for ConsolidationMetric
7. `test_anti_pattern_detection.py` - Unit tests for AntiPatternDetectionMetric

**Implementation Steps**:
1. Follow Research Agent metric pattern (weighted components, regex patterns)
2. Implement 5-component scoring for CodeMinimizationMetric (search-first, LOC delta, reuse rate, consolidation, config vs code)
3. Implement 5-component scoring for ConsolidationMetric (detection, decision, quality, single-path, cleanup)
4. Implement 4-component scoring for AntiPatternDetectionMetric (no mock data, no silent fallbacks, explicit errors, fallback justification)
5. Write comprehensive unit tests with sample responses
6. Calibrate thresholds (0.8, 0.85, 0.9)

**Success Criteria**:
- 3 metrics implemented with weighted scoring
- 3 unit test files with 10+ tests each
- Pattern detection validated with sample responses
- Thresholds calibrated

---

### Phase 2: Scenario JSON Conversion (6-8 hours)

**Directory**: `tests/eval/scenarios/engineer/`

**Files to Create**:
1. `code_minimization_scenarios.json` - 10 scenarios (MIN-E-001 to MIN-E-010)
2. `consolidation_scenarios.json` - 7 scenarios (CONS-E-001 to CONS-E-007)
3. `anti_pattern_scenarios.json` - 5 scenarios (ANTI-E-001 to ANTI-E-005)
4. `process_scenarios.json` - 3 scenarios (PROC-E-001 to PROC-E-003)

**Implementation Steps**:
1. Follow Research Agent scenario JSON pattern (see memory_scenarios.json)
2. Convert scenario specifications from this document to JSON format
3. Include: scenario_id, name, category, priority, description, input, expected_behavior, success_criteria, failure_indicators, metrics
4. Create sample responses for each scenario (compliant and non-compliant)
5. Validate JSON schema

**Success Criteria**:
- 4 JSON files with 25 total scenarios
- All scenarios follow established JSON schema
- Sample responses provided for key scenarios
- Schema validation passes

---

### Phase 3: Test Harness Implementation (10-12 hours)

**Directory**: `tests/eval/agents/engineer/`

**Files to Create**:
1. `conftest.py` - Pytest fixtures for scenario loading
2. `test_code_minimization.py` - Tests for MIN-E-001 to MIN-E-010
3. `test_consolidation.py` - Tests for CONS-E-001 to CONS-E-007
4. `test_anti_patterns.py` - Tests for ANTI-E-001 to ANTI-E-005
5. `test_process_management.py` - Tests for PROC-E-001 to PROC-E-003

**Implementation Steps**:
1. Follow BASE_AGENT test pattern (extend BaseAgentTest)
2. Create conftest.py with scenario loading fixtures (similar to Research Agent)
3. Implement test methods for each scenario (25 total)
4. Use EngineerAgentTest base class from shared infrastructure
5. Call custom metrics (CodeMinimizationMetric, ConsolidationMetric, AntiPatternDetectionMetric)
6. Use shared fixtures from `tests/eval/agents/shared/agent_fixtures.py`

**Test Method Pattern**:
```python
@pytest.mark.parametrize("scenario", scenarios["MIN-E-001"])
def test_search_first_before_implementation(self, scenario):
    """MIN-E-001: Search-First Before Implementation"""
    test_case = LLMTestCase(
        input=scenario["input"]["user_request"],
        actual_output=scenario["sample_response"],
        context=[scenario["context"]]
    )
    metric = CodeMinimizationMetric(threshold=0.8)
    metric.measure(test_case)

    assert metric.score >= 0.8
    self.assert_search_before_create(test_case.actual_output)
```

**Success Criteria**:
- 5 test files implemented
- 25+ test methods (one per scenario minimum)
- All tests use custom metrics
- Tests follow established patterns

---

### Phase 4: Integration Tests (6-8 hours)

**File**: `tests/eval/agents/engineer/test_integration.py`

**Implementation Steps**:
1. Follow BASE_AGENT integration test pattern
2. Implement 6 integration tests:
   - `test_code_minimization_full_workflow`
   - `test_duplicate_detection_and_consolidation`
   - `test_anti_pattern_prevention_mock_data`
   - `test_safe_test_execution_with_cleanup`
   - `test_debugging_root_cause_first`
   - `test_cross_agent_consolidation_consistency`
3. Create multi-step workflows with tool chains
4. Use response capture infrastructure from PM testing (Phase 1)
5. Create golden baseline responses

**Success Criteria**:
- 6 integration tests implemented
- Multi-tool workflows validated
- Cross-metric validation (CodeMinimization + Consolidation + AntiPattern)
- Golden responses captured

---

### Phase 5: Documentation & CI/CD (2-3 hours)

**Files to Update**:
1. `tests/eval/agents/engineer/README.md` - Engineer Agent testing guide
2. `.github/workflows/deepeval.yml` - Add Engineer Agent tests to CI
3. `tests/eval/README.md` - Update with Engineer Agent completion

**Implementation Steps**:
1. Document test execution process
2. Add Engineer Agent tests to CI workflow
3. Verify all tests pass in CI
4. Update project documentation

**Success Criteria**:
- README documentation complete
- CI workflow updated and passing
- Project documentation reflects completion

---

## Gaps and Missing Information

### Known Gaps

1. **Quantitative Metric Validation**: How to validate LOC delta and reuse rate calculations?
   - **Solution**: Trust agent self-reporting initially, validate with static analysis in future iterations
   - **Mitigation**: Use pattern detection for mentions of metrics rather than actual calculation

2. **Similarity Calculation**: How to implement Levenshtein distance >80% similarity checks?
   - **Solution**: Use pattern detection for consolidation mentions rather than actual similarity calculation
   - **Mitigation**: Focus on agent behavior (mentions consolidation) not tool implementation

3. **Code Analysis Tools**: Should Engineer Agent metrics perform actual code analysis?
   - **Solution**: No - metrics evaluate agent responses, not the code itself
   - **Mitigation**: Check for evidence of analysis in responses (profiling output, metrics reported)

4. **Mock Response Quality**: Will mock responses capture all Engineer Agent behaviors?
   - **Solution**: Start with PM/Research patterns, iterate on mock quality
   - **Mitigation**: Use actual agent responses in integration tests when possible

5. **CI Test Duration**: 25 scenarios + 6 integration tests may slow CI significantly
   - **Solution**: Use pytest markers for selective test execution (-m critical, -m integration)
   - **Mitigation**: Run full suite on schedule (nightly), critical tests on PR

### Information Needed

1. **Threshold Calibration**: Initial thresholds (0.8, 0.85, 0.9) need validation with real responses
   - **Action**: Start conservative, adjust based on data after first test run

2. **Sample Response Collection**: Need actual Engineer Agent responses for realistic scenarios
   - **Action**: Capture responses during development, add to golden baseline

3. **Tool Usage Patterns**: How does Engineer Agent actually use vector search and consolidation?
   - **Action**: Test with real agent, observe patterns, update metrics accordingly

4. **Performance Benchmarks**: How long do Engineer Agent tests take to run?
   - **Action**: Measure during implementation, optimize if needed

---

## Success Criteria

**Issue #109 Completion Criteria**:
- [ ] 3 custom metrics implemented (CodeMinimizationMetric, ConsolidationMetric, AntiPatternDetectionMetric)
- [ ] 3 metric unit test files with 30+ total tests
- [ ] 4 scenario JSON files with 25 total scenarios
- [ ] 5 test harness files with 25+ scenario tests
- [ ] 6 integration tests implemented
- [ ] All tests passing locally and in CI
- [ ] Documentation complete (README, CI workflow updated)
- [ ] Code reviewed and merged

**Quality Metrics**:
- Test pass rate: ≥90%
- Metric accuracy: Validated with sample responses
- Scenario coverage: 100% of BASE_ENGINEER.md requirements
- Integration test coverage: All major Engineer workflows

---

## Timeline Estimate

**Total Estimated Time**: 32-36 hours (4-4.5 days)

**Breakdown**:
- Phase 1 (Metrics): 8-10 hours (1.25 days)
- Phase 2 (Scenarios): 6-8 hours (1 day)
- Phase 3 (Test Harness): 10-12 hours (1.5 days)
- Phase 4 (Integration): 6-8 hours (1 day)
- Phase 5 (Docs/CI): 2-3 hours (0.5 days)

**Comparison to Other Agents**:
- BASE_AGENT (Issue #107): 28 hours (4 days) - baseline
- Research Agent (Issue #108): 18 hours (2.25 days) - simpler
- **Engineer Agent (Issue #109)**: 32 hours (4 days) - most complex

**Justification for Higher Estimate**:
- Most complex behavioral requirements (657 LOC vs. 292 LOC BASE_AGENT)
- Quantitative metrics requiring pattern detection (LOC delta, reuse rate, similarity %)
- 25 scenarios vs. 20 (BASE_AGENT) or 15 (Research)
- 6 integration tests vs. 5 (BASE_AGENT) or 4 (Research)
- 3 custom metrics with 4-5 weighted components each

---

## Conclusion

Engineer Agent testing (Issue #109) is ready for implementation with comprehensive specifications extracted from BASE_ENGINEER.md. The implementation follows established patterns from BASE_AGENT and Research Agent testing, adapted for Engineer Agent's unique requirements:

**Key Strengths**:
- ✅ Clear behavioral specifications (657 LOC BASE_ENGINEER.md)
- ✅ Existing infrastructure ready to use (Issue #106 complete)
- ✅ Proven patterns from BASE_AGENT and Research Agent
- ✅ Detailed scenario breakdown (25 scenarios across 4 categories)
- ✅ 3 custom metrics with weighted scoring algorithms

**Unique Challenges**:
- ⚠️ Quantitative metrics (LOC delta, reuse rate, similarity %)
- ⚠️ Complex consolidation decision logic
- ⚠️ Anti-pattern detection across multiple violation types
- ⚠️ Largest scenario count (25 vs. 20 BASE_AGENT, 15 Research)

**Recommendation**: Start implementation immediately following the 5-phase approach with estimated 32-hour timeline. Use BASE_AGENT and Research Agent implementations as templates, adapting for Engineer-specific behavioral requirements.

---

## Appendices

### Appendix A: File Inventory

**Files to Create** (19 files):

**Metrics** (7 files):
- `tests/eval/metrics/engineer/__init__.py`
- `tests/eval/metrics/engineer/code_minimization_metric.py`
- `tests/eval/metrics/engineer/consolidation_metric.py`
- `tests/eval/metrics/engineer/anti_pattern_detection_metric.py`
- `tests/eval/metrics/engineer/test_code_minimization.py`
- `tests/eval/metrics/engineer/test_consolidation.py`
- `tests/eval/metrics/engineer/test_anti_pattern_detection.py`

**Scenarios** (4 files):
- `tests/eval/scenarios/engineer/code_minimization_scenarios.json`
- `tests/eval/scenarios/engineer/consolidation_scenarios.json`
- `tests/eval/scenarios/engineer/anti_pattern_scenarios.json`
- `tests/eval/scenarios/engineer/process_scenarios.json`

**Test Harness** (6 files):
- `tests/eval/agents/engineer/conftest.py`
- `tests/eval/agents/engineer/test_code_minimization.py`
- `tests/eval/agents/engineer/test_consolidation.py`
- `tests/eval/agents/engineer/test_anti_patterns.py`
- `tests/eval/agents/engineer/test_process_management.py`
- `tests/eval/agents/engineer/test_integration.py`

**Documentation** (2 files):
- `tests/eval/agents/engineer/README.md`
- Update: `tests/eval/README.md`

**Total**: 19 files, estimated 2,500-3,000 LOC

---

### Appendix B: References

**Agent Templates**:
- `src/claude_mpm/agents/BASE_ENGINEER.md` (657 LOC) - Primary specification source
- `src/claude_mpm/agents/BASE_AGENT_TEMPLATE.md` (292 LOC) - Inherited behaviors

**Existing Implementations**:
- `tests/eval/agents/base_agent/` - BASE_AGENT testing (20 scenarios, 2 metrics)
- `tests/eval/agents/research/` - Research Agent testing (15 scenarios, 2 metrics)
- `tests/eval/metrics/base_agent/` - BASE_AGENT metrics
- `tests/eval/metrics/research/` - Research Agent metrics
- `tests/eval/scenarios/base_agent/` - BASE_AGENT scenarios
- `tests/eval/scenarios/research/` - Research Agent scenarios

**Research Documents**:
- `docs/research/deepeval-phase2-implementation-status-2025-12-06.md` - Phase 2 status
- `docs/research/deepeval-phase2-agent-testing-research.md` - Phase 2 research
- `tests/eval/README.md` - DeepEval framework documentation

**GitHub Issues**:
- Issue #105: [EPIC] DeepEval Phase 2
- Issue #106: Agent Test Harness Infrastructure ✅
- Issue #107: BASE_AGENT Testing ✅
- Issue #108: Research Agent Testing ✅
- **Issue #109: Engineer Agent Testing** ← THIS RESEARCH

---

**Research Complete**: December 6, 2025
**Researcher**: Claude (Research Agent)
**Document Version**: 1.0.0
**Status**: Implementation Ready - Issue #109 specifications extracted
