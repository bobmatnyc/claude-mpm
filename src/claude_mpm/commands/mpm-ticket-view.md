---
namespace: mpm/ticket
command: view
aliases: [mpm-ticket-view]
migration_target: /mpm/ticket:view
category: tickets
description: Orchestrate ticketing agent for project management workflows
---
# /mpm-ticket

High-level ticketing workflows delegating to ticketing agent.

## Usage
```
/mpm-ticket <subcommand> [options]
```

**CRITICAL:** PM delegates ALL ticketing operations to ticketing agent. PM NEVER uses MCP tools directly.

## Subcommands

### /mpm-ticket organize
Review, transition states, update priorities, identify stale tickets.

**MCP Tools (ticketing agent uses):**
- ticket_list, ticket_read, ticket_comment
- ticket_transition, ticket_update
- ticket_find_stale

**Output:** Tickets transitioned, priorities updated, stale tickets identified, next actions.

### /mpm-ticket proceed
Analyze project board and recommend next actionable steps.

**MCP Tools (ticketing agent uses):**
- project_status, ticket_list, ticket_search
- epic_issues, get_available_transitions

**Output:** Project health, recommended next actions (top 3), blockers requiring attention.

### /mpm-ticket status
Generate comprehensive status report covering work, tickets, project health.

**MCP Tools (ticketing agent uses):**
- project_status, ticket_list, ticket_search
- ticket_find_stale, get_my_tickets

**Output:** Health metrics, ticket counts, high-priority work, blockers, recent activity, risk assessment.

### /mpm-ticket update
Create project status update (Linear ProjectUpdate).

**MCP Tools (ticketing agent uses):**
- project_status, project_update_create
- project_update_list, ticket_list

**Output:** Update ID, health status, accomplishments, metrics, risks, next sprint focus, published link.

### /mpm-ticket project <url>
Set project URL for context (Linear/GitHub/JIRA).

**MCP Tools (ticketing agent uses):**
- config_set_default_project, epic_get, config_get

**Output:** Project context configured, platform/ID/name, access verified, summary.

## Delegation Pattern

**WRONG ❌:**
```
# PM directly using MCP tools
result = mcp__mcp-ticketer__ticket_list()
```

**CORRECT ✅:**
```
# PM delegates to ticketing agent
PM: "I'll have ticketing organize tickets..."
[PM constructs delegation prompt]
[Ticketing agent uses MCP tools]
PM: [Presents results]
```

## Fallback Strategy

If mcp-ticketer unavailable, ticketing agent falls back to aitrackdown CLI:
```bash
aitrackdown status tasks
aitrackdown show TICKET-123
aitrackdown transition TICKET-123 done
```

**PM still delegates** - ticketing agent handles CLI fallback internally.

## Example Workflows

```bash
# Organize and analyze
/mpm-ticket organize          # Clean up board
/mpm-ticket proceed           # Get next steps

# Weekly update
/mpm-ticket update            # Create status update

# Project setup
/mpm-ticket project https://linear.app/team/project/abc-123
```

See docs/commands/ticket.md for comprehensive documentation.
