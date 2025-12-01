# Ticketing Delegation Examples

**Purpose**: Comprehensive examples of correct PM ticketing delegation patterns
**Usage**: Reference for PM when delegating ticket operations to ticketing agent
**Circuit Breaker**: #6 - PM MUST NEVER use mcp-ticketer tools directly

---

## Search Operations

### Ticket Search Delegation

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

**Why This Matters**:
- PM focuses on orchestration, not ticket system mechanics
- Ticketing agent owns all mcp-ticketer tool expertise
- Reduces PM token load by 31.5% (886 lines of ticketing protocols)
- Maintains separation of concerns (PM = delegation, ticketing = execution)

---

## Listing Operations

### Ticket List Delegation

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

**Delegation Pattern**:
1. PM receives user request for ticket data
2. PM delegates to ticketing with specific query
3. Ticketing uses mcp-ticketer tools to fetch data
4. Ticketing returns summary to PM
5. PM uses summary for decision-making (NOT full ticket data)

---

## CRUD Operations

### Complete CRUD Patterns

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

### Read Operations

**❌ WRONG**:
```
PM: "Let me check ticket PROJ-123"
[Uses mcp__mcp-ticketer__ticket_read("PROJ-123")]
```

**✅ CORRECT**:
```
PM: "I'll have ticketing read PROJ-123"
[Delegates to ticketing: "Read ticket PROJ-123 and return status, priority, and blockers"]
Ticketing: "PROJ-123 is in progress, high priority, blocked by PROJ-122"
PM: "Based on ticketing's report, we need to resolve PROJ-122 first"
```

### Create Operations

**❌ WRONG**:
```
PM: "Creating ticket now..."
[Uses mcp__mcp-ticketer__ticket_create directly]
```

**✅ CORRECT**:
```
PM: "I'll have ticketing create a ticket for this work"
[Delegates to ticketing: "Create ticket: Add authentication with JWT"]
Ticketing: "Created PROJ-124: Add authentication with JWT"
PM: "Ticketing created PROJ-124, now delegating implementation to engineer"
```

### Update Operations

**❌ WRONG**:
```
PM: "Updating ticket status..."
[Uses mcp__mcp-ticketer__ticket_update directly]
```

**✅ CORRECT**:
```
PM: "I'll have ticketing update PROJ-123 status to done"
[Delegates to ticketing: "Update PROJ-123: set state=done, add completion comment"]
Ticketing: "Updated PROJ-123 to done with completion notes"
PM: "PROJ-123 marked complete, moving to next task"
```

### Comment Operations

**❌ WRONG**:
```
PM: "Adding comment to ticket..."
[Uses mcp__mcp-ticketer__ticket_comment directly]
```

**✅ CORRECT**:
```
PM: "I'll have ticketing add a progress update to PROJ-123"
[Delegates to ticketing: "Add comment to PROJ-123: Implementation 60% complete, frontend done"]
Ticketing: "Added progress comment to PROJ-123"
PM: "Ticketing updated stakeholders on progress"
```

---

## Ticket Context Propagation

### Passing Ticket Context to Other Agents

**Pattern**: PM receives ticket info from ticketing → propagates to engineer/research

**Example Workflow**:
```
User: "Implement TICKET-123"

Step 1: PM delegates to ticketing
PM → Ticketing: "Read TICKET-123 and return full details"

Step 2: Ticketing returns summary
Ticketing → PM: {
  "ticket_id": "TICKET-123",
  "title": "Add OAuth2 authentication",
  "description": "Implement OAuth2 flow...",
  "priority": "high",
  "acceptance_criteria": ["Users can login with Google", "Token refresh works"]
}

Step 3: PM propagates to engineer
PM → Engineer: "Implement OAuth2 authentication based on TICKET-123
🎫 TICKET CONTEXT:
- Ticket ID: TICKET-123
- Title: Add OAuth2 authentication
- Priority: high
- Acceptance Criteria: [...]
- Description: [...]"

Step 4: Engineer completes work
Engineer → PM: "OAuth2 implemented, tests passing"

Step 5: PM delegates ticket update
PM → Ticketing: "Update TICKET-123: set state=done, add completion comment"
```

**Key Principle**: PM acts as information router, NOT information consumer. PM receives ticket summaries from ticketing and forwards context to implementation agents, but PM doesn't use ticket data for implementation decisions.

---

## Scope Protection Patterns

### Project Scoping Requirements

**Rule**: ALL ticket operations require project scoping (project_id or default_project configured)

**❌ WRONG - No project context**:
```
PM → Ticketing: "List open tickets"
Ticketing: ⚠️ Project filtering required! Use default_project or specify project_id
```

**✅ CORRECT - Project context included**:
```
PM → Ticketing: "List open tickets for project MYAPP"
Ticketing: "Found 5 open tickets in MYAPP: [...]"
```

**Automatic Protection**:
Ticketing agent automatically validates project scope before executing any ticket operation. If missing, ticketing prompts PM to clarify project context or configure default_project.

---

## Context Optimization

### Compact Mode vs Full Mode

**Compact Mode** (default):
- Returns ~15 tokens per ticket (id, title, state, priority, assignee)
- Use for: listings, searches, bulk operations
- 90% token savings vs full mode

**Full Mode**:
- Returns ~185 tokens per ticket (all fields, descriptions, comments)
- Use for: detailed analysis, single ticket reads
- Only when full context is needed

**Example - Listing 20 Tickets**:
```
Compact mode: 20 tickets × 15 tokens = 300 tokens
Full mode: 20 tickets × 185 tokens = 3,700 tokens
Savings: 3,400 tokens (91% reduction)
```

**PM Delegation Strategy**:
```
# For bulk operations - use compact mode
PM → Ticketing: "List open tickets (compact mode)"
Ticketing: Returns 20 tickets in 300 tokens

# For detailed analysis - use full mode on specific tickets
PM → Ticketing: "Read ticket PROJ-123 (full details)"
Ticketing: Returns 1 ticket in 185 tokens
```

---

## Success Criteria

**PM is delegating correctly if**:
- ✅ PM NEVER uses mcp__mcp-ticketer__* tools directly
- ✅ ALL ticket operations go through ticketing agent
- ✅ PM receives summaries, not full ticket data
- ✅ PM propagates ticket context to other agents
- ✅ Project scoping is always specified or configured

**Red Flags** (Circuit Breaker #6 violations):
- ❌ PM uses mcp__mcp-ticketer__ticket_search directly
- ❌ PM uses mcp__mcp-ticketer__ticket_list directly
- ❌ PM uses mcp__mcp-ticketer__ticket_read directly
- ❌ PM uses mcp__mcp-ticketer__ticket_create directly
- ❌ PM uses mcp__mcp-ticketer__ticket_update directly
- ❌ PM uses any mcp-ticketer tool without delegating first

**Rule of Thumb**: If PM is about to use any tool starting with `mcp__mcp-ticketer__*`, STOP and delegate to ticketing instead.

---

## Related References

- **Circuit Breakers**: See [circuit-breakers.md](circuit-breakers.md#circuit-breaker-6)
- **Ticket Completeness**: See [ticket-completeness-examples.md](ticket-completeness-examples.md)
- **Ticketing Agent Instructions**: See [ticketing.md](ticketing.md)

---

**Last Updated**: 2025-12-01
**Phase**: Phase 3 Optimization - Example Extraction
