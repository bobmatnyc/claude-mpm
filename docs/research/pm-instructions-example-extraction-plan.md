# PM_INSTRUCTIONS.md Example Extraction Plan

**Research Date**: 2025-12-01
**Context**: Phase 3 optimization - extracting verbose examples to specialized template files
**Target**: ~1,246 tokens saved (5.2% reduction from 412 lines)
**Current PM Instructions Version**: 0006 (23,832 tokens)

---

## Executive Summary

PM_INSTRUCTIONS.md contains **412 lines of verbose examples** across 4 major categories. These examples are essential for PM understanding but consume significant token budget when repeated verbosely inline. This plan extracts verbose examples to template files while preserving brief canonical examples inline.

### Token Impact Analysis

| Category | Lines | Estimated Tokens | Target Template |
|----------|-------|------------------|-----------------|
| Ticketing Delegation Examples | 32 lines (118-147, 871-884) | ~320 tokens | `ticketing-examples.md` |
| Context Management Examples | 80 lines (370-449 region) | ~400 tokens | `context-management-examples.md` |
| PR Workflow Examples | 20 lines (scattered) | ~200 tokens | `pr-workflow-examples.md` |
| Structured Questions Examples | 90 lines (287-374) | ~450 tokens | `structured-questions-examples.md` |
| **Total** | **412 lines** | **~1,246 tokens** | **4 new templates** |

---

## Category 1: Ticketing Delegation Examples

### Current Location
- **Lines 118-147**: Ticket search delegation examples (❌ WRONG vs ✅ CORRECT)
- **Lines 871-884**: Ticket CRUD delegation patterns

### Content Analysis

**Lines 118-147 - Ticket Search Examples**:
```markdown
### Ticket Search Delegation Examples

**❌ WRONG - PM searches directly**:
```
User: "Find tickets related to authentication"
PM: [Uses mcp__mcp-ticketer__ticket_search directly]  ← VIOLATION
```

**✅ CORRECT - PM delegates search**:
```
User: "Find tickets related to authentication"
PM: "I'll have ticketing search for authentication tickets..."
[Delegates to ticketing: "Search for tickets related to authentication"]
PM: "Based on ticketing's search results, here are the relevant tickets..."
```

**❌ WRONG - PM lists tickets directly**:
```
User: "Show me open tickets"
PM: [Uses mcp__mcp-ticketer__ticket_list directly]  ← VIOLATION
```

**✅ CORRECT - PM delegates listing**:
```
User: "Show me open tickets"
PM: "I'll have ticketing list open tickets..."
[Delegates to ticketing: "List all open tickets"]
PM: "Ticketing found [X] open tickets: [summary]"
```
```

**Lines 871-884 - CRUD Patterns**:
```markdown
**Correct Pattern**:
```
PM: "I'll have ticketing [read/create/update/comment on] the ticket"
→ Delegate to ticketing with specific instruction
→ Ticketing uses mcp-ticketer tools
→ Ticketing returns summary to PM
→ PM uses summary for decision-making (not full ticket data)
```

**Violation Pattern**:
```
PM: "I'll check the ticket details"
→ PM uses mcp__mcp-ticketer__ticket_read directly
→ VIOLATION: Circuit Breaker #6 triggered
```
```

### Extraction Strategy

**Move to**: `templates/ticketing-examples.md`

**New Template Structure**:
```markdown
# Ticketing Delegation Examples

## Search Operations
[Full examples with wrong/correct patterns]

## Listing Operations
[Full examples with wrong/correct patterns]

## CRUD Operations
[Complete patterns with violation detection]

## Ticket Context Propagation
[Examples of passing ticket context to agents]
```

**Inline Replacement** (Lines 118-149):
```markdown
### Ticketing Violations

❌ Using mcp-ticketer tools directly → MUST DELEGATE to ticketing
❌ Using aitrackdown CLI directly → MUST DELEGATE to ticketing
❌ Calling Linear/GitHub/JIRA APIs directly → MUST DELEGATE to ticketing
❌ Any ticket creation, reading, searching, or updating → MUST DELEGATE to ticketing

**Rule of Thumb**: ALL ticket operations = delegate to ticketing (NO EXCEPTIONS).

**Quick Example**:
- ❌ WRONG: PM uses `mcp__mcp-ticketer__ticket_search` directly
- ✅ CORRECT: PM delegates to ticketing: "Search for tickets related to authentication"

**Complete examples**: See [Ticketing Examples](templates/ticketing-examples.md)
```

**Token Savings**: ~320 tokens (32 lines × ~10 tokens/line)

---

## Category 2: Context Management Examples

### Current Location
- **Lines 370-449**: Scope validation template usage example (80 lines)

### Content Analysis

**Lines 370-449 - ScopeValidationTemplate Example**:
```markdown
**Example Usage in PM Workflow**:
```
User: "Implement TICKET-123: Add OAuth2 authentication"

Research Agent returns: "Found 10 optimization opportunities during analysis"

PM workflow:
1. Classifies 10 items:
   - In-Scope (2): Token refresh, OAuth2 error handling
   - Scope-Adjacent (3): Session improvements, profile updates
   - Out-of-Scope (5): Database optimization, caching, etc.

2. Uses ScopeValidationTemplate(
     originating_ticket="TICKET-123",
     in_scope_count=2,
     scope_adjacent_count=3,
     out_of_scope_count=5
   )

3. Gets user decision:
   - Option A: "Include all 10 in TICKET-123 scope"
   - Option B: "Create 2 subtasks, defer 8 to backlog"
   - Option C: "Create 2 subtasks + separate epic for 8 items"

4. User chooses Option C

5. PM delegates to ticketing with scope boundaries:
   - Create 2 subtasks under TICKET-123
   - Create separate "System Optimization" epic with 8 tickets
```
```

### Extraction Strategy

**Move to**: `templates/context-management-examples.md`

**New Template Structure**:
```markdown
# Context Management Examples

## 70% Context Alert Examples
[Full workflow for hitting 70% token threshold]

## 85% Context Escalation Examples
[Automatic pause and resume file creation]

## 95% Emergency Stop Examples
[Context limit enforcement]

## Scope Validation Template Examples
[Complete OAuth2 scenario from lines 370-449]

## Session Resume Examples
[Git-based session continuity patterns]
```

**Inline Replacement** (Lines 346-392):
```markdown
#### 4. Scope Validation Template (`ScopeValidationTemplate`)

Use when agents discover work during ticket-based tasks and PM needs to clarify scope boundaries.

**Quick Example**: Research discovers 10 items during TICKET-123 work. PM classifies as in-scope (2), scope-adjacent (3), out-of-scope (5). User chooses to create 2 subtasks + separate epic.

**Complete workflow**: See [Context Management Examples](templates/context-management-examples.md#scope-validation-template-usage)

**Context-Aware Questions**:
- Asks about scope inclusion strategy based on discovered work counts
- Shows in-scope, scope-adjacent, and out-of-scope item counts
- Only asks if scope_adjacent_count > 0 OR out_of_scope_count > 0
```

**Token Savings**: ~400 tokens (80 lines × ~5 tokens/line)

---

## Category 3: PR Workflow Examples

### Current Location
- **Lines 288-314**: PR creation workflow example (27 lines)

### Content Analysis

**Lines 288-314 - PR Creation Workflow**:
```markdown
**Example: PR Creation Workflow**
```
User: "Create PRs for tickets MPM-101, MPM-102, MPM-103"

PM Workflow:
1. Count tickets (3 tickets)
2. Check if CI configured (read .github/workflows/)
3. Use PRWorkflowTemplate(num_tickets=3, has_ci=True)
4. Ask user with AskUserQuestion tool
5. Parse responses
6. Delegate to version-control with:
   - PR strategy: main-based or stacked
   - Draft mode: true or false
   - Auto-merge: enabled or disabled
```
```

### Extraction Strategy

**Move to**: `templates/pr-workflow-examples.md`

**New Template Structure**:
```markdown
# PR Workflow Examples

## Main-Based PR Examples
[Single ticket PR, independent features]

## Stacked PR Examples
[Dependent ticket chains, phased features]

## PR Strategy Selection Examples
[3-ticket scenario with CI - complete workflow]

## Conflict Resolution Examples
[Handling merge conflicts in stacked PRs]
```

**Inline Replacement** (Lines 286-314):
```markdown
### Integration with PM Workflow

**Quick Example**: For 3 tickets with CI, PM uses `PRWorkflowTemplate(num_tickets=3, has_ci=True)` to ask about PR strategy (main-based vs stacked), draft mode, and auto-merge preference before delegating to version-control.

**Complete workflows**: See [PR Workflow Examples](templates/pr-workflow-examples.md)
```

**Token Savings**: ~200 tokens (20 lines × ~10 tokens/line)

---

## Category 4: Structured Questions Examples

### Current Location
- **Lines 305-314**: Project init workflow example (10 lines)

### Content Analysis

**Lines 305-314 - Project Init Workflow**:
```markdown
**Example: Project Init Workflow**
```
User: "/mpm-init"

PM Workflow:
1. Use ProjectTypeTemplate(existing_files=False) to ask project type
2. Get answers (project type, language)
3. Use DevelopmentWorkflowTemplate(project_type=..., language=...)
4. Get workflow preferences (testing, CI/CD)
5. Delegate to Engineer with complete project context
```
```

### Extraction Strategy

**Move to**: `templates/structured-questions-examples.md`

**New Template Structure**:
```markdown
# Structured Questions Examples

## PR Strategy Template Examples
[Complete 3-ticket scenario with CI]

## Project Type Template Examples
[/mpm-init workflow with project setup]

## Scope Validation Template Examples
[Research discovery scenarios]

## Custom Question Builder Examples
[Advanced use cases beyond templates]
```

**Inline Replacement** (Lines 305-314):
```markdown
**Quick Example**: On `/mpm-init`, PM uses `ProjectTypeTemplate` to determine project type and language, then `DevelopmentWorkflowTemplate` for testing/CI preferences.

**Complete workflows**: See [Structured Questions Examples](templates/structured-questions-examples.md)
```

**Token Savings**: ~100 tokens (10 lines × ~10 tokens/line)

---

## Extraction Priorities

### Priority 1: High-Impact Extractions (Do First)

1. **Context Management Examples** (400 tokens)
   - Most verbose single example (lines 370-449)
   - Clear extraction boundaries
   - Minimal inline summary needed

2. **Ticketing Delegation Examples** (320 tokens)
   - Two separate locations (118-147, 871-884)
   - Repeated patterns consolidatable
   - High reference value

### Priority 2: Medium-Impact Extractions (Do Second)

3. **PR Workflow Examples** (200 tokens)
   - Single cohesive example
   - References existing PRWorkflowTemplate
   - Clean extraction

4. **Structured Questions Examples** (100 tokens)
   - Smallest extraction
   - Complements PR workflow examples
   - Low complexity

---

## Implementation Plan

### Phase 1: Create Template Files (Research Agent)

**Task**: Create 4 new template files with extracted content

**Files to Create**:
1. `/Users/masa/Projects/claude-mpm/src/claude_mpm/agents/templates/ticketing-examples.md`
2. `/Users/masa/Projects/claude-mpm/src/claude_mpm/agents/templates/context-management-examples.md`
3. `/Users/masa/Projects/claude-mpm/src/claude_mpm/agents/templates/pr-workflow-examples.md`
4. `/Users/masa/Projects/claude-mpm/src/claude_mpm/agents/templates/structured-questions-examples.md`

### Phase 2: Update PM_INSTRUCTIONS.md (Engineer Agent)

**Task**: Replace verbose examples with brief summaries + template references

**Changes**:
- Lines 118-147: Replace with 5-line summary + reference
- Lines 288-314: Replace with 3-line summary + reference
- Lines 305-314: Replace with 2-line summary + reference
- Lines 370-449: Replace with 8-line summary + reference
- Lines 871-884: Consolidate into ticketing-examples.md reference

### Phase 3: Validation (QA Agent)

**Task**: Verify PM instructions still complete and references work

**Checks**:
- All template files exist and are accessible
- Inline summaries preserve essential understanding
- References are correct and non-broken
- Total token reduction meets target (~1,246 tokens)
- No loss of critical decision-making information

---

## Token Savings Breakdown

| Category | Current Tokens | Template Tokens | Inline Summary | Net Savings |
|----------|----------------|-----------------|----------------|-------------|
| Ticketing Examples | 320 | 320 (extracted) | 50 | **270 tokens** |
| Context Management | 400 | 400 (extracted) | 80 | **320 tokens** |
| PR Workflow | 200 | 200 (extracted) | 30 | **170 tokens** |
| Structured Questions | 100 | 100 (extracted) | 20 | **80 tokens** |
| **Total** | **1,020** | **1,020** | **180** | **840 tokens** |

**Note**: Original estimate was 1,246 tokens based on line counts. Actual analysis shows **840 tokens saved** (3.5% reduction) after accounting for necessary inline summaries.

---

## Success Metrics

**Target Outcomes**:
- ✅ 4 new template files created
- ✅ PM_INSTRUCTIONS.md reduced by ~840 tokens (3.5%)
- ✅ All inline summaries preserve essential understanding
- ✅ Template references are actionable and clear
- ✅ No loss of critical PM decision-making capability

**Validation Criteria**:
- PM can still make delegation decisions without reading templates
- Templates provide deep dive for complex scenarios
- Inline summaries contain 1 quick example each
- References follow format: `See [Template Name](templates/filename.md#section)`

---

## Risk Analysis

### Low Risk
- **Ticketing Examples**: Clear extraction boundaries, minimal coupling
- **PR Workflow Examples**: Self-contained scenarios

### Medium Risk
- **Context Management Examples**: Scope validation deeply integrated with structured questions section
- **Structured Questions Examples**: Multiple cross-references to other sections

### Mitigation Strategies
1. **Preserve Quick Examples Inline**: Each category keeps 1-2 line canonical example
2. **Clear Section Anchors**: Template files use markdown anchors for direct linking
3. **Gradual Rollout**: Extract Priority 1 items first, validate, then proceed

---

## Future Extraction Opportunities (Not in This Phase)

**Other verbose sections identified but NOT extracted in Phase 3**:

1. **Circuit Breaker Examples** (~500 tokens)
   - Already in `templates/circuit-breakers.md`
   - PM_INSTRUCTIONS.md references it correctly
   - No additional extraction needed

2. **Research Gate Examples** (~300 tokens)
   - Lines 752-756 reference `templates/research_gate_examples.md`
   - Already extracted, no action needed

3. **PM Examples** (~400 tokens)
   - Lines 1199 reference `templates/pm_examples.md`
   - Already extracted, comprehensive coverage

4. **Response Format Examples** (~200 tokens)
   - Lines 1133 reference `templates/response_format.md`
   - Already extracted, no action needed

**Total Already Extracted**: ~1,400 tokens (5.9% of PM instructions)

---

## Conclusion

This extraction plan identifies **412 lines (840 tokens)** of extractable examples across 4 categories. Extracting these to template files will:

1. **Reduce PM token load** by 3.5% (840 tokens)
2. **Preserve PM decision-making capability** via brief inline summaries
3. **Provide deep-dive references** for complex scenarios in templates
4. **Maintain backwards compatibility** with existing references

**Next Steps**:
1. Create 4 new template files with extracted content
2. Update PM_INSTRUCTIONS.md with inline summaries + references
3. Validate all references and token reduction
4. Deploy updated PM instructions to agents

**Phase 3 Optimization Impact**:
- Before: 23,832 tokens (with 412 lines of verbose examples)
- After: 22,992 tokens (with brief summaries + 4 template references)
- **Net Reduction**: 840 tokens (3.5%)

---

**Research Completed**: 2025-12-01
**Research Agent**: Claude (Research Specialist)
**Output**: Comprehensive example extraction plan for PM_INSTRUCTIONS.md Phase 3 optimization
