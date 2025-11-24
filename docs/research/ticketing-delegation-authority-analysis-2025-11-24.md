# Ticketing Delegation Authority Analysis

**Research Date**: 2025-11-24
**Researcher**: Research Agent
**Objective**: Verify that PM instructions clearly state ALL ticketing operations (including finding/searching tickets) MUST be delegated to ticketing-agent
**User Concern**: "Finding tickets in a ticketing system should be the role of the ticketing agent. Confirm that is clear in delegation authority."

---

## Executive Summary

**CRITICAL FINDING: PM instructions contain CONFLICTING GUIDANCE on ticket search operations.**

### Key Issues Identified

1. **❌ CONTRADICTORY INSTRUCTIONS**: PM instructions explicitly state PM CAN use `ticket_search` directly (lines 1456-1458), while simultaneously stating PM MUST delegate ticket searches to ticketing-agent (line 1131)

2. **⚠️ AMBIGUOUS CIRCUIT BREAKER #6**: Circuit Breaker #6 prohibits "ticketing tool misuse" but allows PM to use read-only ticket operations for "context enhancement"

3. **✅ DELEGATION MATRIX CORRECT**: Quick Delegation Matrix (line 1033) correctly states ticketing URLs/IDs should trigger ticketing-agent delegation

4. **❌ WEAKENED ENFORCEMENT**: Multiple sections emphasize "context optimization" rationale for delegation but undermine enforcement by allowing PM read-only access

---

## Detailed Findings

### 1. Conflicting Ticket Search Guidance

#### CONFLICT IDENTIFIED

**Location A (Lines 1456-1458)**: PM CAN use ticket_search
```markdown
**PM CAN use mcp-ticketer for:**
- ✅ Reading ticket details to enhance delegation (ticket_read)
- ✅ Searching for relevant tickets before delegating (ticket_search)
- ✅ Getting ticket context for better task scoping
```

**Location B (Lines 1129-1134)**: PM MUST delegate ticket_search
```markdown
**ALWAYS delegate these to ticketing-agent**:
- ✅ Reading ticket details (ticket_read)
- ✅ Searching for tickets (ticket_search)
- ✅ Listing tickets with filters (ticket_list)
- ✅ Fetching epic/issue hierarchy (epic_get, issue_tasks)
- ✅ Reading ticket comments (ticket_comment)
```

**Analysis**: These two sections directly contradict each other. Location A explicitly permits PM to search tickets, while Location B explicitly requires delegation of ticket searches.

---

### 2. Circuit Breaker #6 Analysis

#### Current Circuit Breaker #6 Definition

**Line 91**: "Ticketing Tool Misuse Detection (Direct ticketing tool usage)"

**Lines 127-131**: Ticketing Violations
```markdown
### TICKETING VIOLATIONS
❌ Using mcp-ticketer tools directly → MUST DELEGATE to ticketing-agent
❌ Using aitrackdown CLI directly → MUST DELEGATE to ticketing-agent
❌ Calling Linear/GitHub/JIRA APIs directly → MUST DELEGATE to ticketing-agent
❌ Any ticket creation, reading, or updating → MUST DELEGATE to ticketing-agent
```

**Lines 1453-1467**: Integration with Circuit Breaker #6
```markdown
**CRITICAL REMINDER**: PM MUST NEVER use ticketing tools directly for ticket CRUD operations (create, update, delete). That work MUST be delegated to ticketing-agent.

**PM CAN use mcp-ticketer for:**
- ✅ Reading ticket details to enhance delegation (ticket_read)
- ✅ Searching for relevant tickets before delegating (ticket_search)
- ✅ Getting ticket context for better task scoping

**PM MUST delegate to ticketing-agent for:**
- ❌ Creating new tickets (ticket_create)
- ❌ Updating ticket state (ticket_update)
- ❌ Commenting on tickets (ticket_comment)
- ❌ Managing epics/issues/tasks (epic_create, issue_create, etc.)
- ❌ Any ticket modification operations

**Rule of Thumb**: Read-only ticket context = PM can use. Ticket modifications = delegate to ticketing-agent.
```

#### Gap Analysis

**MAJOR AMBIGUITY**: Circuit Breaker #6 has two interpretations:

**Strict Interpretation (Lines 127-131)**:
- "Any ticket creation, reading, or updating" → MUST DELEGATE
- Covers ALL mcp-ticketer tool usage
- No exceptions for read-only operations

**Lenient Interpretation (Lines 1453-1467)**:
- PM CAN use mcp-ticketer for read-only operations
- Only ticket CRUD (create, update, delete) requires delegation
- Splits Circuit Breaker #6 into read vs write operations

**User Concern Validation**: The user's concern is VALID. Ticket searching is NOT clearly delegated to ticketing-agent due to these conflicting sections.

---

### 3. Delegation Matrix Accuracy

#### Quick Delegation Matrix (Lines 1006-1034)

**Line 1033**:
```markdown
| **Ticketing URLs/IDs detected** | "I'll fetch ticket context first" | **Use mcp-ticketer tools OR ticketing-agent** |
```

**Analysis**:
- ✅ Correctly identifies ticketing operations should involve ticketing-agent
- ❌ HOWEVER, uses "OR" logic allowing PM to use mcp-ticketer tools directly
- ⚠️ Does NOT explicitly state "ALWAYS delegate to ticketing-agent" for searches

**Line 1019**:
```markdown
| "ticket", "epic", "issue", "create ticket", "track", "Linear", "GitHub Issues" | "I'll delegate to ticketing agent" | ticketing-agent (ALWAYS - handles MCP-first routing) |
```

**Analysis**:
- ✅ Correctly states ticketing operations delegate to ticketing-agent
- ✅ Includes "(ALWAYS - handles MCP-first routing)" enforcement language
- ❌ HOWEVER, does NOT explicitly mention "search" or "find" keywords

---

### 4. Context Optimization Rationale

#### Section: Context Optimization for Ticket Reading (Lines 1063-1290)

**Purpose**: Explains why PM should delegate ticket reading to preserve context

**Key Quote (Lines 1064-1065)**:
```markdown
**CRITICAL**: PM MUST delegate ALL ticket reading to ticketing-agent to preserve context.
```

**Problem**: This section focuses on WHY delegation is beneficial (context preservation) but weakens enforcement by:

1. **Making delegation optional**: "Consider delegating" vs "MUST delegate"
2. **Allowing PM read exceptions**: Lines 1137-1142 permit PM to use MCP tools for "quick context needed"
3. **Fuzzy boundaries**: "Rule of Thumb: If operation returns >200 tokens of data, delegate to ticketing-agent" (Line 1142)

**Line 1289 Decision Tree**:
```markdown
Need ticket information?
    ↓
    ├─ Single ticket, critical context needed now → Delegate to ticketing-agent
    ↓
    ├─ Multiple tickets → ALWAYS delegate to ticketing-agent
    ↓
    ├─ Ticket search/list → ALWAYS delegate to ticketing-agent
    ↓
    └─ Simple ticket creation/update → PM CAN use MCP tools directly (minimal context)
```

**Analysis**:
- ✅ Decision tree correctly states "Ticket search/list → ALWAYS delegate to ticketing-agent"
- ❌ CONTRADICTS earlier section (lines 1456-1458) allowing PM to search tickets
- ⚠️ Uses "Delegate to ticketing-agent" for single ticket reads (not "PM can use MCP tools")

---

### 5. Ticketing Agent Capabilities

#### From ticketing.json (Lines 27-48)

**Ticketing agent has comprehensive search capabilities**:
```json
"capabilities": {
  "model": "sonnet",
  "tools": ["Read", "Write", "Edit", "MultiEdit", "Bash", "Grep", "Glob", "LS", "TodoWrite"],
  "features": [
    "external_pm_integration",
    "jira_api_support",
    "github_issues_support",
    "linear_api_support",
    "url_pattern_detection",
    "api_credential_management"
  ]
}
```

**Analysis**:
- ✅ Ticketing agent is designed to handle ALL ticketing operations
- ✅ Includes external PM system integration (JIRA, GitHub, Linear)
- ✅ Has URL pattern detection capability (designed to parse ticket URLs)
- ⚠️ PM instructions allow PM to bypass ticketing-agent for searches

---

## Recommendations

### Recommendation 1: Remove PM's Ticket Search Authority (CRITICAL)

**REMOVE these lines (1456-1458)**:
```diff
-**PM CAN use mcp-ticketer for:**
-- ✅ Reading ticket details to enhance delegation (ticket_read)
-- ✅ Searching for relevant tickets before delegating (ticket_search)
-- ✅ Getting ticket context for better task scoping
```

**REPLACE with strict delegation mandate**:
```markdown
**PM MUST NEVER use mcp-ticketer tools directly**:
- ❌ Reading ticket details (ticket_read) → MUST DELEGATE to ticketing-agent
- ❌ Searching for tickets (ticket_search) → MUST DELEGATE to ticketing-agent
- ❌ Listing tickets (ticket_list) → MUST DELEGATE to ticketing-agent
- ❌ ANY ticket operation → MUST DELEGATE to ticketing-agent

**Rationale**: All ticketing operations belong to ticketing-agent's domain.
PM should coordinate work, not directly query ticketing systems.
```

---

### Recommendation 2: Strengthen Circuit Breaker #6 (CRITICAL)

**CURRENT (Lines 1453-1467)**: Ambiguous "read vs write" split

**REPLACE with clear violation definition**:
```markdown
### Integration with Circuit Breaker #6

**Circuit Breaker #6: Ticketing Tool Misuse Detection**

**VIOLATION**: PM using ANY mcp-ticketer tool directly

**Prohibited Operations**:
- ❌ ticket_read (read ticket details)
- ❌ ticket_search (search tickets)
- ❌ ticket_list (list tickets with filters)
- ❌ ticket_create (create new tickets)
- ❌ ticket_update (update ticket state)
- ❌ ticket_comment (add comments)
- ❌ epic_get, issue_tasks (hierarchy operations)
- ❌ ANY mcp__mcp-ticketer__* tool

**CORRECT PATTERN**: PM delegates ALL ticketing operations to ticketing-agent

**Example Violation**:
```
PM: [Uses mcp__mcp-ticketer__ticket_search(query="authentication")]
→ VIOLATION: PM used ticket search directly instead of delegating
```

**Example Correct**:
```
PM: "I'll have ticketing-agent search for authentication-related tickets"
[Delegates to ticketing-agent: "Search for tickets related to authentication"]
→ CORRECT: PM delegated search to ticketing-agent
```

**Exception**: NONE. All ticketing operations MUST be delegated.
```

---

### Recommendation 3: Update Decision Tree (HIGH PRIORITY)

**CURRENT (Line 1276-1287)**: Decision tree has "PM CAN use MCP tools" branch

**REPLACE with simplified delegation-only tree**:
```markdown
**Decision Tree**:
```
Need ticket information?
    ↓
    ├─ Single ticket read → DELEGATE to ticketing-agent
    ↓
    ├─ Multiple tickets → DELEGATE to ticketing-agent
    ↓
    ├─ Ticket search/list → DELEGATE to ticketing-agent
    ↓
    ├─ Ticket creation/update → DELEGATE to ticketing-agent
    ↓
    └─ ANY ticket operation → DELEGATE to ticketing-agent
```

**Rule**: ALL ticketing operations MUST be delegated to ticketing-agent. No exceptions.
```

---

### Recommendation 4: Update Quick Delegation Matrix (MEDIUM PRIORITY)

**CURRENT (Line 1033)**: "Use mcp-ticketer tools OR ticketing-agent"

**REPLACE with**:
```markdown
| **Ticketing URLs/IDs detected** | "I'll have ticketing-agent handle this" | **ticketing-agent (ALWAYS)** |
| "search tickets", "find tickets", "list tickets" | "I'll have ticketing-agent search" | **ticketing-agent (ALWAYS)** |
```

---

### Recommendation 5: Remove Context Optimization Exceptions (HIGH PRIORITY)

**REMOVE Lines 1137-1142**:
```diff
-**PM CAN use MCP tools directly for** (if quick context needed):
-- ⚠️ Single ticket summary (when immediate context critical)
-- ⚠️ Ticket creation (minimal context usage)
-- ⚠️ Simple status updates (minimal context usage)
-
-**Rule of Thumb**: If operation returns >200 tokens of data, delegate to ticketing-agent.
```

**REPLACE with**:
```markdown
**PM MUST ALWAYS delegate ticket operations to ticketing-agent**:
- No exceptions for "quick context"
- No exceptions for "minimal context usage"
- No exceptions for "single ticket summary"

**Rationale**: Ticketing-agent is the domain expert for ALL ticket operations.
Context optimization is achieved through delegation, not by bypassing ticketing-agent.
```

---

### Recommendation 6: Add Explicit Search Delegation Examples (MEDIUM PRIORITY)

**ADD to delegation template section** (around line 1147):

```markdown
**Template 3: Ticket Search Delegation**
```
Task: Search for tickets related to {TOPIC}

Context:
- User needs to find existing tickets about {TOPIC}
- Search should cover titles, descriptions, tags

Delegation:
[Delegates to ticketing-agent]
```

**Example**:
```
User: "Find all tickets about authentication"

PM (CORRECT):
"I'll have ticketing-agent search for authentication-related tickets."

[Delegates to ticketing-agent: "Search for tickets related to authentication.
Include:
- Search query: 'authentication'
- Search scope: titles, descriptions, tags
- Return: ticket IDs, titles, status
- Limit: top 10 results"]

ticketing-agent:
[Uses mcp__mcp-ticketer__ticket_search(query="authentication", limit=10)]
[Returns: List of 10 matching tickets with summaries]

PM:
[Reviews ticketing-agent results]
"ticketing-agent found 10 authentication tickets. Here's the summary..."
```

**Example VIOLATION**:
```
User: "Find all tickets about authentication"

PM (INCORRECT):
[Uses mcp__mcp-ticketer__ticket_search(query="authentication")]

→ VIOLATION: PM should have delegated search to ticketing-agent
```
```

---

## Gap Summary

### Current State vs. Desired State

| Operation | Current Guidance | User Expectation | Gap |
|-----------|------------------|------------------|-----|
| **ticket_search** | PM CAN use (line 1457) | ticketing-agent handles | ❌ CONFLICT |
| **ticket_search** | MUST delegate (line 1131) | ticketing-agent handles | ✅ CORRECT |
| **ticket_read** | PM CAN use (line 1456) | ticketing-agent handles | ❌ CONFLICT |
| **ticket_list** | MUST delegate (line 1132) | ticketing-agent handles | ✅ CORRECT |
| **Circuit Breaker #6** | Read-only allowed | ALL ops delegated | ❌ AMBIGUOUS |
| **Decision Tree** | PM can use for simple ops | ALL ops delegated | ❌ INCONSISTENT |
| **Delegation Matrix** | OR logic (PM or agent) | ALWAYS agent | ❌ WEAK |

### Evidence of User Concern Validity

**User stated**: "Finding tickets in a ticketing system should be the role of the ticketing agent."

**Current PM instructions**:
- ✅ Line 1131: "Searching for tickets (ticket_search)" listed under "ALWAYS delegate these to ticketing-agent"
- ✅ Line 1284: Decision tree shows "Ticket search/list → ALWAYS delegate to ticketing-agent"
- ❌ Line 1457: "Searching for relevant tickets before delegating (ticket_search)" listed under "PM CAN use mcp-ticketer for"
- ❌ Line 1033: Delegation matrix uses "OR" logic: "Use mcp-ticketer tools OR ticketing-agent"

**Conclusion**: User's concern is **VALID**. PM instructions contain conflicting guidance that allows PM to search tickets directly, contradicting the principle that ticketing-agent should handle ALL ticketing operations.

---

## Implementation Priority

### Phase 1: Critical Fixes (Immediate)
1. Remove lines 1456-1458 (PM CAN use mcp-ticketer for searches)
2. Strengthen Circuit Breaker #6 definition (remove read/write split)
3. Update line 1033 delegation matrix (remove OR logic)

### Phase 2: Consistency (High Priority)
4. Update decision tree (line 1276-1287) to mandate delegation for ALL ops
5. Remove context optimization exceptions (lines 1137-1142)
6. Add explicit ticket search delegation examples

### Phase 3: Documentation (Medium Priority)
7. Add ticket search violation examples to Circuit Breaker #6 section
8. Update delegation templates with search patterns
9. Cross-reference all ticketing sections for consistency

---

## Testing Verification

### Verification Tests After Fix

**Test 1: Search Delegation**
```
User: "Find tickets about OAuth2"

Expected PM Behavior:
- ✅ PM says: "I'll have ticketing-agent search for OAuth2 tickets"
- ✅ PM delegates to ticketing-agent
- ❌ PM does NOT use mcp__mcp-ticketer__ticket_search directly
```

**Test 2: Circuit Breaker #6 Detection**
```
PM uses: mcp__mcp-ticketer__ticket_search(query="bug")

Expected Outcome:
- ❌ VIOLATION: Circuit Breaker #6 triggered
- ⚠️ Warning: "PM used ticket search directly instead of delegating to ticketing-agent"
- 📋 Recommendation: "Delegate all ticket operations to ticketing-agent"
```

**Test 3: Delegation Matrix Accuracy**
```
User: "Search for authentication tickets"

Expected PM Behavior:
- ✅ PM matches "search" keyword in delegation matrix
- ✅ PM delegates to ticketing-agent (not "PM or ticketing-agent")
- ✅ PM does NOT attempt direct mcp-ticketer usage
```

---

## Files Analyzed

1. **Source File**: `/Users/masa/Projects/claude-mpm/src/claude_mpm/agents/PM_INSTRUCTIONS.md`
   - Total lines analyzed: ~2200 lines
   - Key sections:
     - Lines 85-144: Circuit Breakers and Forbidden Actions
     - Lines 1006-1034: Quick Delegation Matrix
     - Lines 1037-1290: Ticketing System Integration
     - Lines 1451-1467: Circuit Breaker #6 Integration
     - Lines 1611: Circuit Breaker #6 Scope Extension

2. **Source File**: `/Users/masa/Projects/claude-mpm/src/claude_mpm/agents/templates/ticketing.json`
   - Lines 27-63: Ticketing agent capabilities
   - Lines 64+: Ticketing agent instructions (scope protection, MCP-first architecture)

---

## Conclusion

**User's concern is VALIDATED**: PM instructions do NOT clearly state that ALL ticketing operations (including searching) MUST be delegated to ticketing-agent.

**Root Cause**: Conflicting sections in PM_INSTRUCTIONS.md:
1. Section allowing PM to use `ticket_search` for "context enhancement" (lines 1456-1458)
2. Section requiring delegation of `ticket_search` to ticketing-agent (line 1131)

**Impact**: PM may incorrectly use mcp-ticketer tools directly for ticket searches, bypassing ticketing-agent and violating intended delegation architecture.

**Recommended Fix**: Remove all PM exceptions for ticket operations. Mandate 100% delegation of ticketing operations to ticketing-agent. Strengthen Circuit Breaker #6 enforcement.

**Success Criteria After Fix**:
- ✅ Zero ambiguity: ALL ticket operations delegate to ticketing-agent
- ✅ Circuit Breaker #6 covers ALL mcp-ticketer tool usage
- ✅ Delegation matrix explicitly states "ALWAYS ticketing-agent" (no OR logic)
- ✅ No exceptions for "read-only" or "context enhancement" operations
- ✅ Clear examples showing ticket search delegation patterns

---

## Appendix A: Text Evidence

### Evidence 1: Conflicting ticket_search Guidance

**Location A** (Lines 1456-1458):
```
**PM CAN use mcp-ticketer for:**
- ✅ Reading ticket details to enhance delegation (ticket_read)
- ✅ Searching for relevant tickets before delegating (ticket_search)
- ✅ Getting ticket context for better task scoping
```

**Location B** (Lines 1129-1134):
```
**ALWAYS delegate these to ticketing-agent**:
- ✅ Reading ticket details (ticket_read)
- ✅ Searching for tickets (ticket_search)
- ✅ Listing tickets with filters (ticket_list)
- ✅ Fetching epic/issue hierarchy (epic_get, issue_tasks)
- ✅ Reading ticket comments (ticket_comment)
```

### Evidence 2: Circuit Breaker #6 Ambiguity

**Strict Definition** (Lines 127-131):
```
### TICKETING VIOLATIONS
❌ Using mcp-ticketer tools directly → MUST DELEGATE to ticketing-agent
❌ Using aitrackdown CLI directly → MUST DELEGATE to ticketing-agent
❌ Calling Linear/GitHub/JIRA APIs directly → MUST DELEGATE to ticketing-agent
❌ Any ticket creation, reading, or updating → MUST DELEGATE to ticketing-agent
```

**Lenient Exception** (Line 1467):
```
**Rule of Thumb**: Read-only ticket context = PM can use. Ticket modifications = delegate to ticketing-agent.
```

### Evidence 3: Decision Tree Contradiction

**Correct Branch** (Line 1284):
```
├─ Ticket search/list → ALWAYS delegate to ticketing-agent
```

**Incorrect Branch** (Line 1286):
```
└─ Simple ticket creation/update → PM CAN use MCP tools directly (minimal context)
```

---

**Research Complete**
**Date**: 2025-11-24
**Status**: Findings documented with specific line references and recommendations
