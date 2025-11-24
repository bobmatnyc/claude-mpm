# Research: Current Ticketing Workflow in PM and Ticketing Agent

**Date**: 2025-11-23
**Researcher**: Research Agent
**Related Issue**: N/A
**Status**: Complete

## Executive Summary

This research analyzed the current ticketing workflow implementation in Claude MPM's PM and ticketing agent. The analysis identified clear ticket URL/ID detection patterns in PM (lines 596-620 in PM_INSTRUCTIONS.md), comprehensive ticket context propagation (lines 799-870), and TODO-to-ticket conversion capabilities in the ticketing agent (lines 208-284 in ticketing.json). However, **critical gaps exist in scope protection** - the system lacks mechanisms to prevent work scope expansion beyond the originating ticket's boundaries. The research agent currently has no scope-checking logic, and follow-up work is created without formal scope validation.

## Research Questions

1. Where does ticket URL/ID detection happen in the PM workflow?
2. How does the current scope handling work (if any)?
3. Where does work assignment discovery occur?
4. What are the gaps in scope protection that need to be addressed?

## Methodology

- **Tools used**: Read tool for file analysis, Grep for pattern search
- **Scope**: PM_INSTRUCTIONS.md (1810 lines), ticketing.json template (181 lines)
- **Focus**: Ticket detection patterns, delegation workflows, scope handling mechanisms
- **Limitations**: Did not examine runtime code implementation, focused on instruction-level design

## Findings

### Finding Category 1: Ticket URL/ID Detection (PM Responsibility)

**Location**: `/Users/masa/Projects/claude-mpm/src/claude_mpm/agents/PM_INSTRUCTIONS.md`

**Detection Patterns (Lines 596-620)**:

PM MUST recognize these ticketing patterns:

```
URL Patterns:
- Linear: https://linear.app/[team]/issue/[ID]
- GitHub Issues: https://github.com/[owner]/[repo]/issues/[number]
- Jira: https://[domain].atlassian.net/browse/[KEY]

Ticket ID Patterns:
- PROJECT-### (e.g., MPM-123, TEAM-456)
- [TEAM]-### format (e.g., ENG-789)
- Any alphanumeric ticket identifier

User Phrases:
- "for ticket X"
- "related to issue Y"
- "this epic"
- "from Linear"
- "GitHub issue #123"
```

**PM Detection Protocol (Lines 621-644)**:

1. **Check for mcp-ticketer tools availability**
   - Look for `mcp__mcp-ticketer__ticket_read` in available tools
   - Look for `mcp__mcp-ticketer__ticket_search` in available tools
   - Check if ticketing-agent is deployed

2. **If mcp-ticketer tools available: Fetch ticket context FIRST**
   ```
   PM: "I've detected ticket reference [ID]. Let me fetch the ticket details to better scope this work..."
   [Uses: mcp__mcp-ticketer__ticket_read with ticket_id]
   [PM reviews ticket: title, description, priority, state, assignee, tags]
   PM: "Based on ticket [ID] details, I'll delegate to [Agent] with enhanced context..."
   ```

3. **If ticketing-agent available: Delegate ticket fetch**
   ```
   PM: "I've detected ticket reference [ID]. Let me have ticketing-agent fetch the details..."
   [Delegates to ticketing-agent: "Fetch ticket [ID] details"]
   [PM reviews agent response with ticket context]
   PM: "Based on ticket details from ticketing-agent, I'll delegate to [Agent]..."
   ```

**Key Insight**: PM has TWO paths for ticket detection - direct MCP tool usage (read-only) OR delegation to ticketing-agent. PM prefers MCP tools when available for efficiency.

### Finding Category 2: Ticket Context Propagation (MANDATORY)

**Location**: Lines 799-870 in PM_INSTRUCTIONS.md

**Context Template for ALL Delegations**:

```markdown
Task: {Original user request}

🎫 TICKET CONTEXT (MANDATORY - Do NOT proceed without reading):
- Ticket ID: {TICKET_ID}
- Title: {ticket.title}
- Description: {ticket.description}
- Priority: {ticket.priority}
- Current State: {ticket.state}
- Tags: {ticket.tags}
- Acceptance Criteria: {extracted criteria from ticket description}

🎯 YOUR RESPONSIBILITY:
- ALL work outputs MUST reference this ticket ID
- Research findings MUST attach back to {TICKET_ID}
- Implementation MUST satisfy acceptance criteria
- Follow-up tasks MUST become subtasks of {TICKET_ID}

Requirements: {PM's analysis of what work is needed}
Success Criteria: {How PM will verify work completion}

🔗 Traceability Requirement:
- You MUST report back how your work connects to {TICKET_ID}
```

**PM TODO Tracking** (Line 837-843):

PM MUST include ticket ID in TODO items:
```
[Research] Investigate authentication patterns (TICKET-123)
[Engineer] Implement OAuth2 flow (TICKET-123)
[QA] Verify authentication against acceptance criteria (TICKET-123)
```

**Agent Response Verification** (Lines 846-850):

When agent returns results, PM MUST verify:
- ✅ "Based on agent response, work was linked to {TICKET_ID}"
- ✅ "Research findings attached to {TICKET_ID} as {attachment/comment/subtask}"
- ✅ "Implementation commit references {TICKET_ID}"
- ❌ If agent did NOT link work → PM must follow up: "Please attach your work to {TICKET_ID}"

**User Reporting** (Lines 852-870):

PM MUST include ticket linkage section in final response:
```json
{
  "ticket_linkage_report": {
    "originating_ticket": "TICKET-123",
    "work_captured": [
      "Research findings: docs/research/file.md → attached to TICKET-123",
      "Subtask created: TICKET-124",
      "Implementation: 5 commits with TICKET-123 references",
      "QA verification: Test results attached to TICKET-123"
    ],
    "ticket_status_updates": ["TICKET-123: open → in_progress"],
    "traceability_summary": "All work for this session is traceable via TICKET-123"
  }
}
```

**Key Insight**: PM is responsible for ensuring ALL delegated agents receive ticket context and MUST verify work was properly linked back to originating ticket.

### Finding Category 3: Work Assignment Discovery (Ticketing Agent)

**Location**: `/Users/masa/Projects/claude-mpm/src/claude_mpm/agents/templates/ticketing.json`

**TODO-to-Ticket Conversion** (Lines 208-284):

PM delegates TODO conversion in these scenarios:

1. **Research Agent discovered action items**
   - Research output includes TODO section with implementation tasks
   - PM delegates: "Convert these 5 TODOs from Research into tickets under TICKET-123"

2. **Engineer identified follow-up work**
   - Implementation revealed technical debt or bugs
   - PM delegates: "Create tickets for these 3 follow-up items"

3. **User provides TODO list**
   - User: "Track these action items in Linear: [list of todos]"
   - PM delegates: "Create tickets for user's TODO list"

4. **QA found multiple issues**
   - QA testing discovered 10 bugs
   - PM delegates: "Create tickets for each bug found during testing"

**TODO Conversion Protocol**:

**Input Format** (from PM or agent):
```
Convert these TODOs to tickets under TICKET-123:

1. Implement token refresh mechanism
   - Description: OAuth2 tokens expire after 1 hour, need refresh logic
   - Priority: High
   - Type: Task

2. Add OAuth2 error handling
   - Description: Handle edge cases like expired tokens, invalid scopes
   - Priority: Medium
   - Type: Task
```

**Ticketing Agent Actions**:

1. **Parse TODO Items**: Extract title, description, priority, type
2. **Create Tickets Sequentially**: Use `mcp__mcp-ticketer__task_create`
3. **Report Results**: Markdown summary with ticket IDs and links

**Follow-Up Task Workflow** (Lines 285-395):

**Definition**: Follow-up tasks are work items discovered DURING ticket-based work that need separate tracking.

**Follow-Up Detection Patterns**:

1. **During implementation**: Engineer discovers related bugs
2. **During QA testing**: QA finds edge cases not covered
3. **During research**: Research reveals optimization opportunities
4. **During code review**: Code Analyzer identifies technical debt

**Follow-Up Ticket Creation Protocol**:

```python
# For each follow-up item:
for item in follow_up_items:
    ticket_id = mcp__mcp-ticketer__issue_create(
        title=f"Follow-up: {item.title}",
        description=f"""
        **Discovered During**: TICKET-123 (OAuth2 Implementation)

        {item.description}

        **Context**: {item.context}
        **Relationship**: {item.relationship}
        """,
        priority=item.priority,
        tags=["follow-up", "discovered-during-implementation", item.type]
    )

    # Link back to originating ticket
    mcp__mcp-ticketer__ticket_comment(
        ticket_id="TICKET-123",
        operation="add",
        text=f"Follow-up work created: {ticket_id} - {item.title}"
    )
```

**Follow-Up vs. Subtask Decision** (Lines 355-370):

**Create SUBTASK** (child of parent) when:
- Work is PART OF the original ticket scope
- Must complete before parent ticket can close
- Directly contributes to parent ticket acceptance criteria
- Example: TICKET-123 "Add OAuth2" → Subtask: "Implement token refresh"

**Create FOLLOW-UP TICKET** (sibling, not child) when:
- Work is RELATED but NOT required for parent ticket
- Discovered during parent work but separate scope
- Can be completed independently of parent
- Parent ticket can close without this work
- Example: TICKET-123 "Add OAuth2" → Follow-up: "Fix memory leak in auth middleware"

**Key Insight**: Ticketing agent handles TODO conversion and follow-up creation with bidirectional linking, but **lacks formal scope validation** - relies on PM to determine if work is in-scope or out-of-scope.

### Finding Category 4: CRITICAL GAPS IN SCOPE PROTECTION

**🚨 GAP #1: No Scope Validation in Research Agent**

**Problem**: Research agent has NO instructions to check if discovered work is within ticket scope.

**Current Behavior**:
- Research agent discovers 10 optimization opportunities during investigation
- Research agent lists ALL 10 items in TODO section without scope filtering
- PM delegates: "Create tickets for all 10 items" (no scope check)
- Ticketing agent creates 10 follow-up tickets (no scope validation)
- **Result**: Scope creep - original TICKET-123 now has 10 additional tickets attached

**What's Missing**:
- Research agent lacks guidance on distinguishing in-scope vs. out-of-scope findings
- No instructions to flag "This is beyond TICKET-123 scope, suggest separate initiative"
- No mechanism to categorize findings as:
  - ✅ **In-Scope**: Must address for TICKET-123 acceptance criteria
  - ⚠️ **Scope-Adjacent**: Related but not required for TICKET-123
  - ❌ **Out-of-Scope**: Separate initiative, do NOT attach to TICKET-123

**File to Modify**: `/Users/masa/Projects/claude-mpm/src/claude_mpm/agents/templates/research.json`

**Needed Changes**:
- Add scope validation instructions to research agent
- Require research agent to classify findings by scope relationship
- Instruct research agent to ask PM: "Should I include out-of-scope findings in ticket linkage?"

---

**🚨 GAP #2: PM Has No Scope Protection Rules**

**Problem**: PM has instructions to propagate ticket context, but NO instructions to validate work scope.

**Current Behavior**:
- PM receives ticket TICKET-123: "Add OAuth2 authentication"
- Research agent discovers: "Auth middleware has memory leak" (unrelated bug)
- PM delegates: "Create follow-up ticket" (no scope check)
- **Result**: Memory leak ticket becomes linked to OAuth2 ticket (incorrect association)

**What's Missing** (Lines 799-870):
- PM instructions say "Follow-up tasks MUST become subtasks of {TICKET_ID}" (too broad)
- No guidance on WHEN to create subtask vs. WHEN to create separate top-level ticket
- No instructions to ask: "Is this work required for TICKET-123 acceptance criteria?"
- No mechanism to escalate: "This is a critical bug unrelated to TICKET-123, should we create separate priority ticket?"

**File to Modify**: `/Users/masa/Projects/claude-mpm/src/claude_mpm/agents/PM_INSTRUCTIONS.md`

**Needed Changes** (Around Lines 799-870):
- Add scope validation checkpoint before creating follow-up tickets
- Define criteria for in-scope vs. out-of-scope work
- Instruct PM to ask user: "Found unrelated work, should I link to TICKET-123 or create separate ticket?"
- Add scope protection to ticket linkage verification (lines 846-870)

---

**🚨 GAP #3: Ticketing Agent Lacks Scope Classification**

**Problem**: Ticketing agent creates follow-up tickets without validating scope relationship.

**Current Behavior**:
- PM delegates: "Create follow-up tickets for bugs discovered during TICKET-123 work"
- Ticketing agent creates tickets with tags: `["follow-up", "discovered-during-implementation"]`
- **Missing**: No tag or field indicating scope relationship (in-scope vs. out-of-scope)

**What's Missing** (Lines 285-395 in ticketing.json):
- Follow-up ticket creation has no scope classification
- Tags don't distinguish between:
  - `required-for-ticket-123` (in-scope)
  - `related-to-ticket-123` (scope-adjacent)
  - `discovered-during-ticket-123` (potentially out-of-scope)
- No mechanism to create separate "discovered bugs" epic instead of linking to feature ticket

**File to Modify**: `/Users/masa/Projects/claude-mpm/src/claude_mpm/agents/templates/ticketing.json`

**Needed Changes** (Around Lines 285-395):
- Add scope relationship parameter to follow-up ticket creation
- Implement scope-aware tagging:
  - `scope:in-scope` - Required for parent ticket
  - `scope:adjacent` - Related but not required
  - `scope:separate` - Discovered work, separate initiative
- Update follow-up creation protocol to ask: "What is the scope relationship to TICKET-123?"

---

**🚨 GAP #4: No Work Classification Guidance for Agents**

**Problem**: Agents (Research, Engineer, QA) have no instructions on HOW to classify discovered work.

**Current Behavior**:
- Engineer implements TICKET-123, discovers memory leak
- Engineer reports: "Found memory leak in auth middleware"
- PM creates follow-up ticket (default behavior)
- **Missing**: Engineer didn't classify as "Critical bug requiring immediate fix" vs. "Nice-to-have improvement"

**What's Missing** (All agent templates):
- No instructions to classify discovered work by:
  - **Criticality**: Critical, High, Medium, Low
  - **Scope Relationship**: In-scope, Adjacent, Separate
  - **Urgency**: Immediate, This Sprint, Future Backlog
- No guidance on when to escalate: "This is a critical bug, should it block TICKET-123?"

**Files to Modify**:
- `/Users/masa/Projects/claude-mpm/src/claude_mpm/agents/templates/research.json`
- `/Users/masa/Projects/claude-mpm/src/claude_mpm/agents/templates/engineer.json`
- `/Users/masa/Projects/claude-mpm/src/claude_mpm/agents/templates/qa.json`

**Needed Changes**:
- Add work classification instructions to ALL agents
- Require agents to report discovered work with:
  - Scope relationship to originating ticket
  - Criticality assessment
  - Recommended action (block ticket, create subtask, create separate ticket)

---

**🚨 GAP #5: No User Involvement in Scope Decisions**

**Problem**: PM never asks user about scope boundaries - makes scope decisions automatically.

**Current Behavior**:
- Research discovers 10 optimization opportunities
- PM automatically delegates: "Create 10 follow-up tickets"
- User never gets asked: "Do you want these optimizations linked to TICKET-123, or should we create a separate optimization epic?"

**What's Missing** (Lines 192-374 in PM_INSTRUCTIONS.md):
- Structured questions section (lines 192-374) has NO template for scope clarification
- No `ScopeValidationTemplate` to ask user:
  - "Should we include these 5 discovered items in TICKET-123 scope?"
  - "Create separate epic for discovered work?"
  - "Which items are required for TICKET-123 vs. nice-to-have?"

**File to Modify**: `/Users/masa/Projects/claude-mpm/src/claude_mpm/agents/PM_INSTRUCTIONS.md`

**Needed Changes** (Around Lines 268-292):
- Add `ScopeValidationTemplate` to structured questions section
- Instruct PM to ask user when discovered work crosses scope boundaries
- Provide user with options:
  1. Link all discovered work to TICKET-123 (accept scope expansion)
  2. Create separate epic for discovered work (maintain scope boundaries)
  3. Cherry-pick critical items, defer rest to backlog

---

## Analysis

### Current Workflow Strengths

1. **Comprehensive Ticket Detection**: PM has well-defined URL/ID patterns (Linear, GitHub, Jira)
2. **Mandatory Context Propagation**: PM ensures ALL agents receive ticket context
3. **Bidirectional Ticket Linking**: Ticketing agent creates proper parent-child and follow-up relationships
4. **Verification Requirements**: PM must verify work was linked back to originating ticket
5. **TODO Conversion**: Ticketing agent can bulk-convert TODO lists to tickets
6. **Follow-Up Workflows**: Clear distinction between subtasks (in-scope) and follow-ups (adjacent)

### Critical Scope Protection Gaps

1. **No Scope Validation**: Research agent lacks instructions to classify findings by scope
2. **No PM Scope Checkpoints**: PM has no rules to validate work scope before creating follow-up tickets
3. **No Work Classification**: Agents don't categorize discovered work (criticality, scope relationship, urgency)
4. **No User Involvement**: PM makes scope decisions without user input
5. **No Scope-Aware Tagging**: Follow-up tickets don't indicate scope relationship

### Why This Matters

**Without scope protection, ticket-based work experiences uncontrolled scope creep**:

- TICKET-123 "Add OAuth2" ends up with 15 follow-up tickets attached
- Some follow-ups are critical bugs (should be separate priority tickets)
- Some follow-ups are nice-to-have enhancements (should be backlog items)
- User loses control of scope boundaries
- Original ticket becomes a dumping ground for all discovered work

**Example of Current Broken Behavior**:

```
User: "Implement TICKET-123: Add OAuth2 authentication"

[Research agent investigates]
Research: "Found 10 optimization opportunities during analysis"

[PM delegates without scope check]
PM: "Create 10 follow-up tickets for optimizations"

[Ticketing agent creates tickets]
Result: TICKET-123 now has 10 follow-up tickets
- TICKET-124: Optimize database queries (unrelated to OAuth2)
- TICKET-125: Refactor session management (unrelated to OAuth2)
- TICKET-126: Add caching layer (unrelated to OAuth2)
... etc

[User sees ticket explosion]
User: "I just wanted OAuth2, why are there 10 new tickets?"
```

**What SHOULD Happen with Scope Protection**:

```
User: "Implement TICKET-123: Add OAuth2 authentication"

[Research agent investigates with scope awareness]
Research: "Findings classified:
- In-Scope (2 items): Token refresh, OAuth2 error handling
- Scope-Adjacent (3 items): Session management, user profile updates
- Out-of-Scope (5 items): Database optimizations, caching layer, API versioning"

[PM asks user for scope decision]
PM: "Research found 10 items. 2 are required for OAuth2 acceptance criteria.
     3 are related session improvements. 5 are separate optimization opportunities.

     How would you like to proceed?
     1. Include all 10 in TICKET-123 scope (accept expansion)
     2. Create 2 subtasks (in-scope), defer rest to backlog
     3. Create 2 subtasks, create separate 'System Optimization' epic for other 8"

[User chooses option 3]
User: "Option 3 - keep TICKET-123 focused on OAuth2"

[PM delegates with scope boundaries]
PM: "Create 2 subtasks under TICKET-123"
PM: "Create separate epic 'System Optimization' with 8 tickets"

Result:
- TICKET-123 has 2 subtasks (focused scope)
- EP-0042 "System Optimization" has 8 tickets (separate initiative)
- User maintains control of scope boundaries
```

## Recommendations

### High Priority

1. **Add Scope Validation to Research Agent**
   - File: `/Users/masa/Projects/claude-mpm/src/claude_mpm/agents/templates/research.json`
   - Add instructions to classify findings:
     - ✅ In-Scope (required for ticket acceptance criteria)
     - ⚠️ Scope-Adjacent (related but not required)
     - ❌ Out-of-Scope (separate initiative)
   - Require research agent to ask PM about out-of-scope findings

2. **Add Scope Protection Rules to PM**
   - File: `/Users/masa/Projects/claude-mpm/src/claude_mpm/agents/PM_INSTRUCTIONS.md`
   - Section: Lines 799-870 (Ticket Context Propagation)
   - Add scope validation checkpoint before creating follow-up tickets
   - Define criteria for in-scope vs. out-of-scope work
   - Instruct PM to ask user when scope boundaries are unclear

3. **Add ScopeValidationTemplate to Structured Questions**
   - File: `/Users/masa/Projects/claude-mpm/src/claude_mpm/agents/PM_INSTRUCTIONS.md`
   - Section: Lines 268-292 (Ticket Management Templates)
   - Create new template for scope clarification questions
   - Enable PM to ask user: "Include discovered work in ticket scope?"

### Medium Priority

4. **Add Scope Classification to Ticketing Agent**
   - File: `/Users/masa/Projects/claude-mpm/src/claude_mpm/agents/templates/ticketing.json`
   - Section: Lines 285-395 (Follow-Up Task Workflow)
   - Add scope relationship parameter to follow-up ticket creation
   - Implement scope-aware tagging (scope:in-scope, scope:adjacent, scope:separate)

5. **Add Work Classification Guidance to All Agents**
   - Files: research.json, engineer.json, qa.json
   - Add instructions to classify discovered work by:
     - Criticality (Critical, High, Medium, Low)
     - Scope Relationship (In-scope, Adjacent, Separate)
     - Urgency (Immediate, This Sprint, Future Backlog)

### Low Priority / Future Considerations

6. **Implement Scope Metrics**
   - Track scope expansion per ticket
   - Alert when ticket has >5 follow-up tickets
   - Report scope creep statistics to user

7. **Add Automatic Scope Validation**
   - Use ticket description to automatically determine scope boundaries
   - Flag follow-up work that doesn't match ticket tags/labels
   - Suggest separate epic when >3 out-of-scope items discovered

## Action Items

- [ ] Modify research.json to add scope validation instructions
- [ ] Update PM_INSTRUCTIONS.md section 799-870 with scope protection rules
- [ ] Add ScopeValidationTemplate to structured questions section (lines 268-292)
- [ ] Update ticketing.json follow-up workflow with scope classification
- [ ] Add work classification guidance to engineer.json, qa.json

## References

**Source Files Analyzed**:
- `/Users/masa/Projects/claude-mpm/src/claude_mpm/agents/PM_INSTRUCTIONS.md` (1810 lines)
  - Lines 596-620: Ticket URL/ID detection patterns
  - Lines 621-644: PM protocol when tickets detected
  - Lines 799-870: Ticket context propagation (MANDATORY)
  - Lines 846-870: Agent response verification and user reporting
  - Lines 192-374: Structured questions section (missing ScopeValidationTemplate)
  - Lines 1267-1299: Ticket-based work verification

- `/Users/masa/Projects/claude-mpm/src/claude_mpm/agents/templates/ticketing.json` (181 lines)
  - Lines 18-20: Tags include "todo-conversion", "follow-up-workflows"
  - Lines 208-284: TODO-to-Ticket conversion workflow
  - Lines 285-395: Follow-up task workflow
  - Lines 355-370: Follow-up vs. subtask decision criteria
  - Lines 371-395: Automatic ticket linking rules

**Key Concepts**:
- **Ticket Context Propagation**: PM passes ticket details to ALL delegated agents
- **TODO Conversion**: Ticketing agent converts TODO lists to tracked tickets
- **Follow-Up Workflow**: Work discovered during ticket-based work becomes follow-up tickets
- **Bidirectional Linking**: Follow-up tickets reference originating ticket, originating ticket references follow-ups
- **Scope Creep Risk**: Current system lacks scope validation, leading to uncontrolled ticket expansion

## Appendix

### Current Workflow Sequence Diagram

```
User provides ticket reference (TICKET-123)
    ↓
PM detects ticket pattern (URL or ID)
    ↓
PM fetches ticket context (via mcp-ticketer OR ticketing-agent)
    ↓
PM propagates ticket context to ALL agents
    ↓
Agent performs work (Research, Engineer, QA, etc.)
    ↓
Agent discovers additional work items
    ↓
Agent reports: "Found 5 optimization opportunities"
    ↓
PM delegates: "Create follow-up tickets for 5 items"  ← NO SCOPE CHECK
    ↓
Ticketing agent creates 5 follow-up tickets
    ↓
Ticketing agent links all 5 to TICKET-123  ← NO SCOPE VALIDATION
    ↓
PM verifies ticket linkage
    ↓
PM reports to user: "Created 5 follow-up tickets"
    ↓
[RESULT: TICKET-123 now has 5 follow-up tickets, scope expanded]
```

### Proposed Workflow with Scope Protection

```
User provides ticket reference (TICKET-123)
    ↓
PM detects ticket pattern (URL or ID)
    ↓
PM fetches ticket context (via mcp-ticketer OR ticketing-agent)
    ↓
PM propagates ticket context + scope boundaries to ALL agents  ← NEW
    ↓
Agent performs work with scope awareness  ← NEW
    ↓
Agent discovers additional work items
    ↓
Agent classifies items by scope relationship:  ← NEW
  - In-Scope (2 items): Required for TICKET-123 acceptance criteria
  - Scope-Adjacent (2 items): Related but not required
  - Out-of-Scope (1 item): Separate initiative
    ↓
Agent reports: "Found 5 items, classified by scope"  ← NEW
    ↓
PM validates scope boundaries  ← NEW
PM asks user: "Include scope-adjacent items in TICKET-123?"  ← NEW
    ↓
User chooses: "Only in-scope items, defer rest to backlog"
    ↓
PM delegates: "Create 2 subtasks (in-scope), add 3 to backlog"  ← NEW
    ↓
Ticketing agent creates:
  - 2 subtasks under TICKET-123 (in-scope)
  - 3 backlog tickets in separate epic (out-of-scope)  ← NEW
    ↓
PM verifies scope was maintained  ← NEW
    ↓
PM reports to user: "Created 2 subtasks, 3 backlog tickets"
    ↓
[RESULT: TICKET-123 scope maintained, user in control]
```

### File Locations for Needed Changes

1. **Research Agent Scope Validation**:
   - File: `/Users/masa/Projects/claude-mpm/src/claude_mpm/agents/templates/research.json`
   - Section: Instructions field (lines 64+, within JSON)
   - Add: Scope classification guidance

2. **PM Scope Protection Rules**:
   - File: `/Users/masa/Projects/claude-mpm/src/claude_mpm/agents/PM_INSTRUCTIONS.md`
   - Section: Lines 799-870 (Ticket Context Propagation)
   - Add: Scope validation checkpoint before follow-up creation

3. **PM Structured Questions Template**:
   - File: `/Users/masa/Projects/claude-mpm/src/claude_mpm/agents/PM_INSTRUCTIONS.md`
   - Section: Lines 268-292 (Ticket Management Templates)
   - Add: `ScopeValidationTemplate` for user scope decisions

4. **Ticketing Agent Scope Classification**:
   - File: `/Users/masa/Projects/claude-mpm/src/claude_mpm/agents/templates/ticketing.json`
   - Section: Lines 285-395 (Follow-Up Task Workflow)
   - Add: Scope relationship parameter and scope-aware tagging

5. **Work Classification for All Agents**:
   - Files:
     - `/Users/masa/Projects/claude-mpm/src/claude_mpm/agents/templates/research.json`
     - `/Users/masa/Projects/claude-mpm/src/claude_mpm/agents/templates/engineer.json`
     - `/Users/masa/Projects/claude-mpm/src/claude_mpm/agents/templates/qa.json`
   - Add: Work classification instructions (criticality, scope, urgency)
