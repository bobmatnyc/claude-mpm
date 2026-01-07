# PM Instruction Improvements Analysis

**Date**: 2025-12-22
**Researcher**: Research Agent
**Objective**: Identify optimal location for new PM imperatives and conduct holistic review of instruction files

---

## Executive Summary

The Claude MPM project uses a hierarchical instruction system with:
- **PM Instructions**: `src/claude_mpm/agents/PM_INSTRUCTIONS.md` (1716 lines, version 0007)
- **Workflow Instructions**: `src/claude_mpm/agents/WORKFLOW.md` (360 lines)
- **Base Agent Instructions**: Appended to all agent files via deployment system
- **42 Deployed Agents**: In `.claude/agents/` with individual instructions

**Key Finding**: New imperatives should be added to the **BASE-AGENT.md** section that gets appended to all agents (found at the end of deployed agent files), NOT to PM_INSTRUCTIONS.md, to ensure consistency across all agent types.

---

## Instruction File Inventory

### 1. Primary PM Instructions

**File**: `/Users/masa/Projects/claude-mpm/src/claude_mpm/agents/PM_INSTRUCTIONS.md`

**Size**: 1716 lines
**Version**: 0007
**Purpose**: Claude 4.5 optimized PM instructions with delegation principles

**Current Structure**:
```
- Role and Core Principle (lines 6-32)
- Core Workflow: Do the Work, Then Report (lines 34-67)
- PM Responsibilities (lines 69-81)
- Tool Usage Guide (lines 83-462)
  - Task Tool (Primary)
  - TodoWrite Tool
  - Read Tool (with strict limits)
  - Bash Tool (navigation/git only)
  - Vector Search Tools
  - FORBIDDEN MCP Tools
  - Browser State Verification (MANDATORY)
- Circuit Breaker #7: Verification Command Detection (lines 463-500)
- Ops Agent Routing (MANDATORY) (lines 501-520)
- When to Delegate to Each Agent (lines 521-621)
- Research Gate Protocol (lines 623-678)
- QA Verification Gate Protocol (MANDATORY) (lines 679-714)
- Verification Requirements (lines 716-802)
- Workflow Pipeline (lines 804-907)
- PM VERIFICATION MANDATE (CRITICAL) (lines 910-1145)
- Git File Tracking Protocol (lines 1149-1218)
- Common Delegation Patterns (lines 1220-1248)
- Documentation Routing Protocol (lines 1250-1301)
- Ticketing Integration (lines 1303-1329)
- TICKET-DRIVEN DEVELOPMENT PROTOCOL (TkDD) (lines 1331-1400)
- PR Workflow Delegation (lines 1402-1442)
- Structured Questions for User Input (lines 1444-1481)
- Auto-Configuration Feature (lines 1483-1513)
- Proactive Architecture Improvement Suggestions (lines 1515-1551)
- PM Examples: Correct Delegation Patterns (lines 1553-1596)
- Response Format (lines 1598-1623)
- Validation Rules (lines 1625-1656)
- Common User Request Patterns (lines 1658-1676)
- Session Resume Capability (lines 1678-1691)
- Summary: PM as Pure Coordinator (lines 1693-1716)
```

**Strengths**:
- Highly detailed and specific
- Strong focus on delegation over direct action
- Clear circuit breakers and enforcement mechanisms
- Comprehensive tool usage guidance

**Issues Found**:
- Some redundancy in verification sections (lines 679-714 and 910-1145)
- Documentation Routing appears in two places (workflow and dedicated section)
- Ticketing Integration and TkDD could be consolidated

---

### 2. Workflow Instructions

**File**: `/Users/masa/Projects/claude-mpm/src/claude_mpm/agents/WORKFLOW.md`

**Size**: 360 lines
**Purpose**: 5-phase workflow execution details

**Current Structure**:
```
- Mandatory 5-Phase Sequence (lines 6-50)
  - Phase 1: Research
  - Phase 2: Code Analyzer Review
  - Phase 3: Implementation
  - Phase 4: QA
  - Phase 5: Documentation
- Git Security Review (lines 52-66)
- Publish and Release Workflow (lines 68-307)
  - Phase 1: Pre-Release Validation
  - Phase 2: Quality Gate Validation
  - Phase 3: Security Scan (MANDATORY)
  - Phase 4: Version Management
  - Phase 5: Build and Publish
  - Phase 5.5: Update Homebrew Tap
  - Phase 6: Post-Release Verification
- Ticketing Integration (lines 309-340)
- Structural Delegation Format (lines 342-353)
- Override Commands (lines 355-360)
```

**Strengths**:
- Clear phase-based workflow
- Comprehensive release workflow with verification gates
- Good separation of concerns from PM_INSTRUCTIONS.md

**Issues Found**:
- Ticketing Integration duplicated with PM_INSTRUCTIONS.md
- Could benefit from cross-references to PM_INSTRUCTIONS.md sections

---

### 3. Base Agent Instructions (Appended to All Agents)

**Location**: End of every deployed agent file in `.claude/agents/`

**Example from** `/Users/masa/Projects/claude-mpm/.claude/agents/engineer.md`:

**Current Structure** (appended to all agents):
```
## Git Workflow Standards (for all agents)
## Memory Routing (for all agents)
## Output Format Standards (for all agents)
## Handoff Protocol (for all agents)
## Agent Responsibilities (for all agents)
  - What Agents DO
  - What Agents DO NOT
## Quality Standards (for all agents)
## Communication Standards (for all agents)
## Memory Updates (for all agents)
```

**Key Finding**: This is WHERE new imperatives should be added, as it affects ALL agents universally.

---

### 4. Agent-Specific Instructions

**Location**: `.claude/agents/*.md` (42 agent files)

**Examples**:
- `engineer.md` - Includes BASE_ENGINEER.md principles (code reduction, search-before-implement, SOLID, DI)
- `api-qa.md` - QA-specific testing protocols
- `local-ops.md` - Local development operations
- `mpm-skills-manager.md` - Skill lifecycle management

**Pattern**:
```
---
frontmatter (name, description, model, type, version)
---
[Agent-specific instructions]

---

[BASE-AGENT.md content appended by deployment system]
```

---

## Redundancy Analysis

### Major Redundancies Found

#### 1. Ticketing Integration (3 occurrences)

**Occurrence 1**: `PM_INSTRUCTIONS.md` lines 1303-1329
- Focus: MCP-first routing, URL detection, PM forbidden from using ticketing tools

**Occurrence 2**: `WORKFLOW.md` lines 309-340
- Focus: MCP vs CLI fallback, detection workflow

**Recommendation**: Consolidate into single section in PM_INSTRUCTIONS.md with reference from WORKFLOW.md

#### 2. Verification Requirements (2 occurrences)

**Occurrence 1**: `PM_INSTRUCTIONS.md` lines 716-802 (Verification Requirements)
- Focus: Implementation, Deployment, Bug Fix verification with evidence templates

**Occurrence 2**: `PM_INSTRUCTIONS.md` lines 910-1145 (PM VERIFICATION MANDATE)
- Focus: Same concepts but with work type matrix and forbidden phrases

**Recommendation**: Merge into single comprehensive "Verification Protocol" section with subsections:
- Core Principle
- Evidence Standards
- Work Type Matrix
- Forbidden Phrases
- Violation Detection

#### 3. Git/File Tracking (2 occurrences)

**Occurrence 1**: `PM_INSTRUCTIONS.md` lines 1149-1218 (Git File Tracking Protocol)
- PM-specific file tracking after delegation

**Occurrence 2**: Base Agent Instructions (appended to all agents)
- Git workflow standards for all agents

**Recommendation**: Keep both but add cross-reference. PM version is delegation-focused, agent version is implementation-focused.

---

## Recommendations for New Imperatives

### Target Imperatives to Add

1. **Suggest improvements when issues are seen**
2. **Check codebase for existing libs/components before implementing**
3. **Mimic local patterns/naming conventions (unless bad practices, then suggest improvements)**

---

### Recommended Location: Base Agent Instructions

**Why**: These imperatives apply to ALL agents (engineers, QA, research, ops), not just PM.

**File to Modify**: The base instructions appended to all agents (currently at end of deployed agent files)

**Section to Add**: "Proactive Code Quality Improvements"

**Proposed Addition**:

```markdown
## Proactive Code Quality Improvements

### Suggest Improvements When Issues Are Seen

When you encounter code smells, anti-patterns, or architectural issues during your work:

**DO**:
- Point out the specific issue with file/line references
- Suggest concrete improvement with one-line benefit
- Estimate effort (small/medium/large)
- Ask user if they want the improvement implemented
- Continue with original task if user declines

**DON'T**:
- Skip mentioning issues to "save time"
- Implement improvements without asking (scope creep)
- Make vague suggestions ("this could be better")
- Suggest more than 1-2 improvements per task

**Format**:
```
💡 Improvement Suggestion

Found: [specific issue with location]

Consider: [specific improvement] — [one-line benefit]
Effort: [small/medium/large]

Want me to address this while I'm here?
```

**Examples**:
- "Found: Hardcoded database connection in 3 files. Consider: Extract to config module — easier testing and environment management. Effort: Small"
- "Found: API error handling returns raw exceptions to client. Consider: Error normalization middleware — consistent API responses and security. Effort: Medium"

### Check Codebase Before Implementing

Before writing new code, ALWAYS search for existing implementations:

**Search Protocol**:
1. **Use Vector Search** (if available):
   - `mcp__mcp-vector-search__search_code` - Find existing similar code
   - `mcp__mcp-vector-search__search_similar` - Find reusable patterns

2. **Use Grep Patterns**:
   - Search for function/class names
   - Search for similar functionality
   - Check for utility modules

3. **Check Standard Libraries**:
   - Language built-ins (Python: pathlib, typing; JS: Array methods, Promise)
   - Framework features (React hooks, FastAPI dependencies)
   - Already-installed dependencies

**Report Findings**:
```
Search Results:
✅ Found existing implementation: src/utils/validation.py:validateEmail()
Action: Reusing existing function instead of writing new one
Lines saved: ~15
```

**Benefits**:
- Reduces code duplication
- Maintains consistency
- Faster implementation
- Lower maintenance burden

### Mimic Local Patterns and Naming Conventions

When working in an existing codebase, follow established patterns unless they're demonstrably harmful:

**Pattern Detection**:
- **Naming**: camelCase vs snake_case, class names, file naming
- **Structure**: Directory organization, module patterns
- **Error Handling**: Exception patterns, error return types
- **Testing**: Test file naming, assertion styles
- **Comments**: Docstring style, inline comment conventions

**When to Mimic**:
- Patterns are consistent across codebase
- No obvious problems with existing approach
- User hasn't specified different convention
- Following pattern improves consistency

**When to Suggest Change**:
- Pattern violates language best practices
- Security vulnerability in existing pattern
- Performance issue with current approach
- Accessibility problem in UI patterns

**Format When Suggesting Change**:
```
⚠️ Pattern Inconsistency Detected

Current codebase uses: [existing pattern]
Issue: [specific problem - security/performance/best practice]

Recommend: [better pattern] — [specific benefit]

Options:
1. Follow existing pattern (consistency)
2. Update to better pattern (I can refactor existing code too)

Your preference?
```

**Examples**:

**Good - Mimic Pattern**:
```
Detected pattern: This codebase uses snake_case for all function names
Action: Writing new functions in snake_case to match
```

**Good - Suggest Improvement**:
```
⚠️ Pattern Inconsistency Detected

Current codebase uses: Inline SQL strings with string formatting
Issue: SQL injection vulnerability (security)

Recommend: Parameterized queries with ORM — prevents SQL injection

Options:
1. Follow existing pattern (consistency, but unsafe)
2. Update to parameterized queries (I can refactor existing code too)

Your preference?
```

### Integration with Existing Workflows

These imperatives complement existing protocols:

- **Code Analyzer Review**: Proactive suggestions align with analyzer's NEEDS_IMPROVEMENT feedback
- **Research Gate**: "Check codebase first" prevents unnecessary research for existing solutions
- **QA Verification Gate**: Pattern mimicking improves test consistency
- **Git File Tracking**: Reduced code duplication = fewer files to track
```

---

### Alternative Location: PM_INSTRUCTIONS.md Section

**If you want PM-specific focus**, add to PM_INSTRUCTIONS.md after line 1551 (after "Proactive Architecture Improvement Suggestions"):

**Section**: "Delegation Guidelines: Agent Code Quality Standards"

**Content**: Same as above, but framed as "When delegating to agents, ensure they follow these standards"

**Pros**:
- PM-centric view
- Easier to find for PM-focused updates

**Cons**:
- Only affects PM's delegation instructions to agents
- Agents won't see these imperatives directly unless also added to base instructions
- Requires agents to already know these practices

---

## Consistency Issues Found

### 1. Circuit Breaker Numbering

**Issue**: Circuit breakers numbered #2, #3, #6, #7, #8 in PM_INSTRUCTIONS.md

**Missing**: Circuit Breakers #1, #4, #5

**Location**: Likely in other files or deprecated

**Recommendation**:
- Audit all circuit breakers across instruction files
- Renumber sequentially or remove numbering
- Create Circuit Breaker reference table

### 2. Tool Usage Documentation

**Issue**: Tool documentation scattered across PM_INSTRUCTIONS.md

**Current**:
- Read Tool (lines 168-291)
- Bash Tool (lines 292-344)
- Task Tool (lines 86-139)
- Vector Search (lines 362-386)
- SlashCommand Tool (lines 345-361)

**Recommendation**:
- Create "Tool Reference" appendix
- Keep decision guidance in main sections
- Cross-reference from workflow phases

### 3. Agent Names and Routing

**Issue**: Multiple references to agent names with slight variations

**Examples**:
- "research agent" vs "Research Agent" vs "research"
- "local-ops-agent" vs "local-ops" vs "Ops (Local-Ops for Local Development)"

**Recommendation**:
- Create canonical agent name reference
- Use consistent formatting (lowercase with hyphens)
- Add agent routing decision tree

### 4. Verification Evidence Templates

**Issue**: Evidence templates appear in multiple formats

**Locations**:
- Lines 729-739 (Implementation Verification)
- Lines 753-768 (Deployment Verification)
- Lines 781-802 (Bug Fix Verification)
- Lines 937-1097 (Verification by Work Type)

**Recommendation**:
- Create unified evidence template library
- Single source of truth for each work type
- Cross-reference from relevant sections

---

## Proposed File Structure Improvements

### Current Structure
```
src/claude_mpm/agents/
├── PM_INSTRUCTIONS.md (1716 lines - too large)
├── WORKFLOW.md (360 lines)
├── MEMORY.md
├── CLAUDE_MPM_OUTPUT_STYLE.md
├── agent-template.yaml
└── templates/
    ├── pm-examples.md
    ├── pm-red-flags.md
    ├── validation-templates.md
    ├── git-file-tracking.md
    ├── response-format.md
    ├── circuit-breakers.md
    ├── research-gate-examples.md
    ├── ticketing-examples.md
    ├── context-management-examples.md
    ├── pr-workflow-examples.md
    └── structured-questions-examples.md
```

### Recommended Refactoring

**Option A: Modular PM Instructions**

```
src/claude_mpm/agents/
├── PM_INSTRUCTIONS.md (Core principles - 300 lines)
│   ├── Role and responsibilities
│   ├── Delegation-first principle
│   └── Core workflow
├── PM_TOOL_GUIDE.md (Tool usage - 400 lines)
│   ├── Task tool (primary)
│   ├── TodoWrite
│   ├── Read (with limits)
│   ├── Bash (navigation/git)
│   └── Forbidden tools
├── PM_VERIFICATION.md (All verification - 500 lines)
│   ├── Core principles
│   ├── Evidence standards
│   ├── Work type matrix
│   ├── QA Gate protocol
│   └── Violation detection
├── PM_AGENT_ROUTING.md (Delegation matrix - 200 lines)
│   ├── When to delegate to each agent
│   ├── Ops agent routing
│   └── Agent name reference
├── PM_WORKFLOWS.md (merge with WORKFLOW.md - 500 lines)
│   ├── Research gate
│   ├── QA gate
│   ├── Git tracking
│   ├── Ticketing integration
│   └── PR workflow
└── BASE_AGENT.md (Universal agent instructions - 300 lines)
    ├── Git workflow standards
    ├── Proactive code quality (NEW)
    ├── Output format standards
    ├── Handoff protocol
    ├── Agent responsibilities
    └── Communication standards
```

**Benefits**:
- Easier to maintain individual sections
- Clear separation of concerns
- Easier to find specific guidance
- Can version-control sections independently

**Cons**:
- More files to manage
- Need deployment system to compose them
- Cross-references required

**Option B: Keep Current Structure, Add Index**

Keep PM_INSTRUCTIONS.md as single file but add:
1. **Table of Contents** with line number references
2. **Quick Reference Cards** in templates/
3. **Decision Trees** as separate diagrams
4. **Better section markers** for easier navigation

**Benefits**:
- No structural changes needed
- Single source of truth
- Easier for Claude to load entire context

**Cons**:
- File remains very large (1700+ lines)
- Harder to maintain
- Risk of redundancy

---

## Recommended Action Plan

### Immediate Actions (High Priority)

1. **Add New Imperatives to BASE_AGENT.md** (affects all agents)
   - Create "Proactive Code Quality Improvements" section
   - Add after "Agent Responsibilities" section
   - Include all three imperatives with examples

2. **Consolidate Redundant Sections in PM_INSTRUCTIONS.md**
   - Merge two verification sections (lines 716-802 and 910-1145)
   - Consolidate ticketing integration references
   - Remove duplicate content from WORKFLOW.md

3. **Create Circuit Breaker Reference**
   - Audit all circuit breakers across files
   - Document missing numbers (#1, #4, #5)
   - Create templates/circuit-breakers-reference.md

### Short-Term Actions (Medium Priority)

4. **Standardize Agent Names**
   - Create canonical agent name list
   - Find/replace inconsistent references
   - Add to templates/agent-routing-reference.md

5. **Create Verification Evidence Library**
   - Extract all evidence templates
   - Create templates/verification-evidence.md
   - Cross-reference from main instructions

6. **Add Table of Contents to PM_INSTRUCTIONS.md**
   - Generate with line numbers
   - Add quick navigation links
   - Place at top of file

### Long-Term Actions (Lower Priority)

7. **Consider Modular Refactoring**
   - Evaluate Option A (modular) vs Option B (indexed)
   - Prototype composition system if choosing modular
   - Test with subset of agents

8. **Create Visual Decision Trees**
   - Agent routing flowchart
   - Verification protocol flowchart
   - Tool selection flowchart

9. **Add Cross-References**
   - Link related sections
   - Reference examples from templates/
   - Create glossary of terms

---

## Specific File Recommendations

### 1. Create: `BASE_AGENT.md` (or equivalent in deployment system)

**Location**: `src/claude_mpm/agents/BASE_AGENT.md`

**Content**: Universal agent instructions currently appended to all agents

**New Section to Add**:
```markdown
## Proactive Code Quality Improvements

[Full content from "Proposed Addition" section above]
```

**Placement**: After "Agent Responsibilities", before "Quality Standards"

---

### 2. Update: `PM_INSTRUCTIONS.md`

**Changes**:

**A. Add Table of Contents** (after line 3):
```markdown
# Project Manager Agent Instructions

## Table of Contents
1. [Role and Core Principle](#role-and-core-principle) (lines 6-32)
2. [Core Workflow](#core-workflow) (lines 34-67)
3. [PM Responsibilities](#pm-responsibilities) (lines 69-81)
4. [Tool Usage Guide](#tool-usage-guide) (lines 83-462)
   - [Task Tool](#task-tool-primary)
   - [TodoWrite Tool](#todowrite-tool)
   - [Read Tool](#read-tool-critical-limit)
   - [Bash Tool](#bash-tool)
   - [Forbidden Tools](#forbidden-mcp-tools)
5. [Agent Delegation Matrix](#when-to-delegate-to-each-agent) (lines 521-621)
6. [Verification Protocol](#pm-verification-mandate) (lines 910-1145)
7. [Git File Tracking](#git-file-tracking-protocol) (lines 1149-1218)
8. [Workflow Phases](#workflow-pipeline) (lines 804-907)
9. [Special Protocols](#research-gate-protocol) (lines 623+)
```

**B. Consolidate Verification Sections** (merge 716-802 into 910-1145):

Create single comprehensive section:
```markdown
## Verification Protocol (MANDATORY)

### Core Principle
[Content from lines 913-917]

### Evidence Standards
[Content from lines 806-810]

### Verification by Work Type
[Content from lines 916-1027]

### Verification Workflow
[Content from lines 1029-1044]

### Example Evidence Templates
[Content from lines 729-802 reformatted]

### Forbidden Phrases
[Content from lines 1101-1114]

### Violation Detection
[Content from lines 1120-1130]
```

**C. Consolidate Ticketing Integration** (remove duplicate from WORKFLOW.md):

Keep PM_INSTRUCTIONS.md version (lines 1303-1329), update WORKFLOW.md to reference it:
```markdown
## Ticketing Integration

See PM_INSTRUCTIONS.md "Ticketing Integration" section for complete protocol.

**Summary**: ALL ticket operations delegated to ticketing agent. PM uses MCP-first with CLI fallback.
```

**D. Add Reference to New Base Agent Imperatives** (after line 1551):

```markdown
## Agent Code Quality Standards

All agents follow proactive code quality imperatives defined in BASE_AGENT.md:
- Suggest improvements when issues are seen
- Check codebase for existing implementations before writing new code
- Mimic local patterns and naming conventions (unless harmful)

When delegating, ensure agents have context to follow these standards. If agent doesn't proactively check for existing code, remind them of search-before-implement protocol.
```

---

### 3. Update: `WORKFLOW.md`

**Changes**:

**A. Remove Ticketing Integration Duplication** (lines 309-340):

Replace with:
```markdown
## Ticketing Integration

See PM_INSTRUCTIONS.md "Ticketing Integration" section for complete protocol.

**Key Points for Workflow**:
- All ticket operations delegated to ticketing agent
- Ticket state transitions required at each phase
- Comment on ticket after Research, Implementation, QA phases
```

**B. Add Phase-Specific Quality Checks**:

Update each phase to reference new base agent imperatives:

```markdown
### Phase 3: Implementation
**Agent**: Selected via delegation matrix
**Requirements**:
  - Complete code with error handling
  - Basic test proof
  - **Check for existing implementations before writing new code**
  - **Follow local patterns and naming conventions**
  - **Suggest improvements if issues found**
```

---

## Impact Analysis

### Adding New Imperatives to BASE_AGENT.md

**Affected Components**:
- All 42 deployed agents in `.claude/agents/`
- Agent deployment system
- Agent template composition

**Impact**:
- ✅ Consistent behavior across all agents
- ✅ Engineers, QA, Research all follow same standards
- ✅ Reduces duplicate code project-wide
- ⚠️ Requires redeployment of all agents
- ⚠️ May increase agent instruction length (estimated +50 lines per agent)

**Estimated Effort**:
- Write new section: 2 hours
- Test with sample agents: 2 hours
- Deploy to all agents: 1 hour
- **Total**: ~5 hours

---

### Consolidating Redundancies in PM_INSTRUCTIONS.md

**Affected Components**:
- PM agent instruction loading
- Existing sessions with cached PM instructions
- Documentation referring to specific line numbers

**Impact**:
- ✅ Easier to maintain single source of truth
- ✅ Clearer for Claude to understand (no conflicting info)
- ✅ Reduces file size by ~200 lines
- ⚠️ Need to update cross-references
- ⚠️ Existing documentation may reference old line numbers

**Estimated Effort**:
- Merge verification sections: 3 hours
- Consolidate ticketing: 1 hour
- Update cross-references: 2 hours
- Test PM behavior: 2 hours
- **Total**: ~8 hours

---

## Implementation Priority Matrix

| Action | Impact | Effort | Priority | Estimated Time |
|--------|--------|--------|----------|----------------|
| Add new imperatives to BASE_AGENT.md | High | Medium | **P0 - Critical** | 5 hours |
| Consolidate verification sections | High | Medium | **P1 - High** | 8 hours |
| Create circuit breaker reference | Medium | Low | **P1 - High** | 2 hours |
| Standardize agent names | Medium | Low | **P2 - Medium** | 3 hours |
| Add TOC to PM_INSTRUCTIONS.md | Low | Low | **P2 - Medium** | 1 hour |
| Create verification evidence library | Medium | Medium | **P3 - Low** | 4 hours |
| Modular refactoring | High | High | **P4 - Future** | 20+ hours |

**Recommended First Sprint** (P0 + P1):
1. Add new imperatives to BASE_AGENT.md (5h)
2. Consolidate verification sections in PM_INSTRUCTIONS.md (8h)
3. Create circuit breaker reference (2h)
**Total**: ~15 hours

---

## Conclusion

The Claude MPM instruction system is well-structured but shows signs of organic growth with some redundancy. The new imperatives should be added to **BASE_AGENT.md** (or its equivalent in the deployment system) to ensure consistent behavior across all agent types.

**Key Recommendations**:
1. ✅ Add new imperatives to BASE_AGENT.md section appended to all agents
2. ✅ Consolidate redundant verification sections in PM_INSTRUCTIONS.md
3. ✅ Remove ticketing duplication between PM_INSTRUCTIONS.md and WORKFLOW.md
4. ✅ Create circuit breaker reference document
5. ⏭️ Consider modular refactoring for long-term maintainability

**Files to Modify**:
- `src/claude_mpm/agents/BASE_AGENT.md` (or deployment system equivalent) - **PRIMARY**
- `src/claude_mpm/agents/PM_INSTRUCTIONS.md` - Consolidate redundancies
- `src/claude_mpm/agents/WORKFLOW.md` - Remove duplication
- `src/claude_mpm/agents/templates/circuit-breakers-reference.md` - **NEW**

**Next Steps**:
1. Review this analysis with team
2. Approve location for new imperatives (BASE_AGENT.md recommended)
3. Draft specific wording for new imperatives
4. Implement P0 changes (add imperatives)
5. Test with subset of agents
6. Roll out to all agents
7. Implement P1 changes (consolidation)
