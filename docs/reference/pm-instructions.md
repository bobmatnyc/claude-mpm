# PM Agent Instructions Reference

**Last Updated:** 2025-12-23
**Version:** 5.4.23
**Status:** Active
**Audience:** Contributors, Agent Developers

---

## Overview

This document provides a comprehensive reference for the PM (Project Manager) agent instructions. The PM agent is the central orchestrator in Claude MPM, responsible for task delegation, quality assurance, and workflow coordination.

## PM Instructions Structure

The PM agent instructions are defined in `src/claude_mpm/agents/PM_INSTRUCTIONS.md` and follow a consolidated, streamlined structure designed for clarity and efficiency.

### Key Metrics

- **Total Lines**: 1,175 lines (reduced from 1,725 lines in previous versions)
- **Reduction**: 31.9% consolidation
- **Primary Sections**: 8 major sections
- **Sub-sections**: 40+ specialized instruction areas

### Document Structure

```markdown
PM_INSTRUCTIONS.md
├── Core Responsibilities
│   ├── Task Orchestration
│   ├── Quality Assurance
│   └── Workflow Management
│
├── Agent Delegation
│   ├── Delegation Tables (by category)
│   ├── Selection Criteria
│   └── Handoff Protocols
│
├── QA Verification Gate
│   ├── When to Verify
│   ├── Verification Process
│   └── Acceptance Criteria
│
├── Read Tool Hierarchy
│   ├── Tool Selection Rules
│   ├── Performance Guidelines
│   └── Fallback Protocols
│
├── MCP Integration
│   ├── Available Tools
│   ├── Tool Constraints
│   └── Delegation Requirements
│
├── Circuit Breakers
│   ├── Safety Triggers
│   ├── Error Recovery
│   └── Escalation Paths
│
├── Memory Management
│   ├── KuzuMemory Integration
│   └── Context Retention
│
└── Best Practices
    ├── Communication Standards
    ├── Documentation Requirements
    └── Quality Standards
```

## Major Consolidation Changes (v5.4.23)

### 1. QA Verification Consolidated

**Before**: Multiple scattered sections describing verification requirements
**After**: Single comprehensive "QA Verification Gate" section

**Benefits**:
- Clear decision tree for when PM must verify vs delegate to QA
- Consolidated verification criteria
- Single source of truth for QA requirements

### 2. Read Tool Hierarchy Clarified

**Before**: Multiple mentions of Read tool usage across document
**After**: Dedicated "Read Tool Hierarchy" section with clear rules

**Key Rules**:
```
1. MCP Filesystem (preferred for large files)
2. Read tool (fallback for pagination)
3. Bash cat/head/tail (last resort)
```

### 3. Agent Delegation Tables

**Before**: Prose descriptions of agent capabilities and delegation
**After**: Structured tables by category

**Example Table Structure**:
```markdown
| Category | Agent | Use Case | Keywords |
|----------|-------|----------|----------|
| Backend | Python Engineer | Python development | python, fastapi, django |
| Frontend | React Engineer | React apps | react, jsx, components |
| QA | Web QA | Browser testing | selenium, playwright, e2e |
```

**Benefits**:
- Faster agent lookup
- Clear capability boundaries
- Improved LLM parsing

## Verification Testing

The PM instructions are validated through comprehensive DeepEval test suites:

### Test Files

1. **`tests/eval/agents/base_agent/test_pm_verification_gate.py`**
   - **Tests**: 10 test cases
   - **Focus**: QA verification gate behavior
   - **Coverage**:
     - When PM must verify directly
     - When PM must delegate to QA
     - Verification acceptance criteria
     - Error handling in verification

2. **`tests/eval/test_cases/test_pm_behavior_validation.py`**
   - **Tests**: 7 test cases
   - **Focus**: Ticketing delegation and workflows
   - **Coverage**:
     - Proper ticketing integration usage
     - Task delegation patterns
     - Circuit breaker triggers
     - Memory management compliance

### Scoring Methodology

**TicketingDelegationMetric**:
- **Binary Scoring**: Pass (1.0) or Fail (0.0)
- **No Partial Credit**: Ensures strict compliance
- **Criteria**:
  - Correct tool selection (MCP Ticketer vs manual)
  - Proper delegation to specialists
  - Adherence to PM scope boundaries

## BASE_AGENT.md Integration

The PM instructions build on top of `BASE_AGENT.md`, which defines universal agent imperatives. These imperatives apply to PM and all other agents.

### New Imperatives (v5.4.23)

#### 1. Search Before Implementing

**Imperative**: Before creating new code, ALWAYS search for existing implementations.

```bash
# Search pattern
grep -r "relevant_pattern" src/
```

**Expected Reporting**:
- ✅ Found: "Found existing [component] at [path]. Reusing."
- ✅ Not Found: "Verified no existing implementation. Creating new."

#### 2. Mimic Local Patterns

**Imperative**: Follow established project patterns unless demonstrably harmful.

**Pattern Detection**:
- Naming conventions (camelCase vs snake_case)
- File structure
- Error handling approaches
- Testing patterns

**Exception Handling**:
```
⚠️ Pattern Concern: [issue]
Suggestion: [improvement]
Implement current pattern or improved version?
```

#### 3. Suggest Improvements

**Imperative**: Proactively identify and suggest improvements discovered during work.

**Format**:
```
💡 Improvement Suggestion
Found: [specific issue with file:line]
Impact: [security/performance/maintainability/etc.]
Suggestion: [concrete fix]
Effort: [Small/Medium/Large]
```

**Scope Limits**:
- Maximum 1-2 suggestions per task
- Exception: Critical security/data loss issues

**Ask Permission**: "Want me to fix this while I'm here?"

## PM-Specific Constraints

### Forbidden Actions

The PM agent **MUST NOT**:
1. Use Chrome DevTools MCP tools directly (delegate to web-qa)
2. Implement features outside delegation scope
3. Skip QA verification when criteria require it
4. Use Read tool when MCP Filesystem is available
5. Create tickets manually when MCP Ticketer is available

### Required Behaviors

The PM agent **MUST**:
1. Verify work meets acceptance criteria before completion
2. Delegate to specialized agents for domain-specific tasks
3. Use MCP Ticketer for all ticketing operations
4. Follow Read Tool Hierarchy for file operations
5. Trigger circuit breakers when detecting violations

## Circuit Breaker Reference

Circuit breakers are safety mechanisms that halt execution when constraints are violated.

### Circuit Breaker #6: Browser Testing

**Trigger Conditions**:
- PM uses Chrome DevTools MCP tools directly
- PM attempts browser automation without web-qa delegation
- PM bypasses verification requirements for web features

**Recovery**:
1. Halt current operation
2. Delegate to web-qa agent
3. Await verification results
4. Resume with QA approval

## Usage Guidelines

### For PM Agent Users

When interacting with the PM agent:
1. **Be Specific**: Provide clear task descriptions
2. **Trust Delegation**: PM will route to appropriate specialists
3. **Expect Verification**: PM will verify critical work
4. **Review Suggestions**: PM may propose improvements

### For Agent Developers

When modifying PM instructions:
1. **Run Tests**: Execute DeepEval test suites
2. **Maintain Structure**: Follow consolidated organization
3. **Update Tables**: Keep delegation tables current
4. **Document Changes**: Update this reference

### For Framework Contributors

When contributing to PM agent system:
1. **Preserve Consolidation**: Don't duplicate content
2. **Extend Tables**: Add new agents to delegation tables
3. **Test Thoroughly**: Ensure test coverage for new behaviors
4. **Update Metrics**: Track line count and complexity

## Migration Notes

### From Pre-v5.4.23

If you're familiar with older PM instructions:

**Key Changes**:
- QA verification now in single dedicated section
- Agent delegation uses tables instead of prose
- Read tool hierarchy explicitly defined
- BASE_AGENT imperatives now mandatory

**Action Required**:
- Review new delegation tables for agent selection
- Update any custom PM instructions to follow new structure
- Re-run DeepEval tests to ensure compliance

## Related Documentation

- [BASE_AGENT.md](../../src/claude_mpm/agents/BASE_AGENT.md) - Universal agent imperatives
- [PM_INSTRUCTIONS.md](../../src/claude_mpm/agents/PM_INSTRUCTIONS.md) - Full PM instructions
- [Agent Capabilities Reference](../agents/agent-capabilities-reference.md) - Agent capabilities matrix
- [QA Verification Guide](./QA.md) - Quality assurance protocols
- [Memory Integration](./MEMORY.md) - KuzuMemory usage

## Testing Resources

- [PM Verification Gate Tests](../../tests/eval/agents/base_agent/test_pm_verification_gate.py)
- [PM Behavior Validation Tests](../../tests/eval/test_cases/test_pm_behavior_validation.py)
- [Test Pyramid Progress](../developer/TEST_PYRAMID_PROGRESS.md)

## Summary

The PM instructions provide a comprehensive, consolidated guide for the Project Manager agent. The v5.4.23 consolidation reduced complexity by 31.9% while improving clarity and testability. All changes are validated through extensive DeepEval test suites ensuring strict compliance with defined behaviors.

Key improvements:
- ✅ Single QA verification section
- ✅ Tabular agent delegation
- ✅ Clear Read tool hierarchy
- ✅ BASE_AGENT imperative integration
- ✅ Comprehensive test coverage (17 tests)

---

**Last Review**: 2025-12-23
**Next Review**: When PM instructions are modified
**Maintainer**: Framework Core Team
