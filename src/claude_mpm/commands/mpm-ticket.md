# /mpm-ticket - Ticketing Workflow Management

Orchestrate ticketing agent for comprehensive project management workflows.

## Usage

```
/mpm-ticket <subcommand> [options]
```

## Description

This command provides high-level ticketing workflows that delegate ALL operations to the **ticketing agent**. The PM never directly uses MCP ticketing tools - all ticketing work is delegated to the specialized ticketing agent.

## Subcommands

### /mpm-ticket organize

Review all open tickets, transition states, update priorities, and document completed work.

**Purpose**: Comprehensive ticket board organization and status updates.

**PM Delegation Pattern**:
```
PM delegates to ticketing agent:
"Organize project tickets:
1. List all open tickets
2. Transition completed tickets to 'Done' or 'UAT'
3. Update priorities based on current project context
4. Add status comments documenting completed work
5. Identify stale or blocked tickets
6. Report organization results with summary"
```

**MCP Tools Used** (by ticketing agent):
- `mcp__mcp-ticketer__ticket_list` - List all open tickets
- `mcp__mcp-ticketer__ticket_read` - Read ticket details
- `mcp__mcp-ticketer__ticket_comment` - Read comments for context
- `mcp__mcp-ticketer__ticket_transition` - Change ticket states
- `mcp__mcp-ticketer__ticket_update` - Update priorities
- `mcp__mcp-ticketer__ticket_find_stale` - Find stale tickets

**Expected Output**:
```
Ticket Organization Complete
============================

Tickets Transitioned (5):
✅ TICKET-123: Feature implementation → Done
✅ TICKET-124: Bug fix → UAT (ready for testing)
✅ TICKET-125: Research task → In Review

Priorities Updated (3):
🔴 TICKET-130: Critical security bug → High priority
🟡 TICKET-131: Performance optimization → Medium priority

Stale Tickets Identified (2):
⚠️ TICKET-140: No activity for 30 days
⚠️ TICKET-141: Blocked on external dependency

Next Actions:
- Review TICKET-140, TICKET-141 for closure
- Validate UAT tickets with user
- Monitor high-priority security ticket
```

**Example Usage**:
```
User: "/mpm-ticket organize"
PM: "I'll have ticketing organize the project board..."
[PM delegates to ticketing agent with organization tasks]
PM: [Presents ticketing agent's organization summary]
```

---

### /mpm-ticket proceed

Analyze project board and recommend next actionable steps based on ticket priorities and dependencies.

**Purpose**: Intelligent "what should I work on next?" analysis.

**PM Delegation Pattern**:
```
PM delegates to ticketing agent:
"Analyze project board for next actions:
1. Get project status and health metrics
2. List open tickets by priority
3. Identify unblocked, high-priority work
4. Check for critical dependencies
5. Recommend top 3 tickets to start next
6. Explain reasoning for recommendations"
```

**MCP Tools Used** (by ticketing agent):
- `mcp__mcp-ticketer__project_status` - Get project health and metrics
- `mcp__mcp-ticketer__ticket_list` - List open tickets
- `mcp__mcp-ticketer__ticket_search` - Search for priority work
- `mcp__mcp-ticketer__epic_issues` - Check epic progress
- `mcp__mcp-ticketer__get_available_transitions` - Check workflow options

**Expected Output**:
```
Project Status Analysis
=======================

Project Health: AT_RISK
- 15 open tickets
- 3 high-priority items
- 1 critical blocker

Recommended Next Actions:

1. 🔴 TICKET-177: Fix authentication blocker (CRITICAL)
   - Priority: High
   - Blocks: 2 other tickets
   - Estimated effort: 2-3 hours
   - Reason: Unblocks entire authentication epic

2. 🟡 TICKET-180: Complete OAuth2 implementation
   - Priority: Medium
   - Status: In Progress (70% complete)
   - Estimated effort: 4 hours
   - Reason: Close to completion, high impact

3. 🟢 TICKET-185: Add error handling tests
   - Priority: Medium
   - Dependencies: None
   - Estimated effort: 2 hours
   - Reason: No blockers, improves stability

Blockers Requiring Attention:
⚠️ TICKET-175: Waiting for API credentials (3 days)
```

**Example Usage**:
```
User: "/mpm-ticket proceed"
PM: "I'll have ticketing analyze the board for next steps..."
[PM delegates to ticketing agent for analysis]
PM: [Presents ticketing agent's recommendations]
```

---

### /mpm-ticket project <url>

Set project URL for ticket context and future operations.

**Purpose**: Configure project context for Linear, GitHub, or JIRA.

**PM Delegation Pattern**:
```
PM delegates to ticketing agent:
"Set project context:
1. Parse project URL (Linear/GitHub/JIRA)
2. Extract project identifier
3. Verify project access
4. Store project context for future operations
5. Confirm project details"
```

**MCP Tools Used** (by ticketing agent):
- `mcp__mcp-ticketer__config_set_default_project` - Set default project
- `mcp__mcp-ticketer__epic_get` - Verify project access
- `mcp__mcp-ticketer__config_get` - Confirm configuration

**CLI Fallback** (if MCP unavailable):
```bash
# Store in .claude-mpm/ticket-config.json
echo '{"project_url": "https://linear.app/team/project/abc-123"}' > .claude-mpm/ticket-config.json
```

**Expected Output**:
```
Project Context Configured
==========================

Platform: Linear
Project ID: abc-123-def-456
Project Name: Q4 Roadmap Implementation
Team: Engineering

Configuration Saved:
✅ Default project set
✅ Access verified
✅ Future ticket operations will use this project

Project Summary:
- 42 total issues
- 15 open, 10 in progress, 17 done
- Health: ON_TRACK
```

**Example Usage**:
```
User: "/mpm-ticket project https://linear.app/team/project/abc-123"
PM: "I'll have ticketing configure project context..."
[PM delegates to ticketing agent with URL]
PM: [Presents ticketing agent's confirmation]
```

---

### /mpm-ticket status

Generate comprehensive status report covering all work, tickets, and project health.

**Purpose**: Executive summary of project state and ticket status.

**PM Delegation Pattern**:
```
PM delegates to ticketing agent:
"Generate comprehensive status report:
1. Get project health metrics
2. Summarize ticket counts by state
3. List high-priority open tickets
4. Identify blockers and risks
5. Show recent activity (last 7 days)
6. Calculate completion percentage
7. Provide actionable insights"
```

**MCP Tools Used** (by ticketing agent):
- `mcp__mcp-ticketer__project_status` - Project health analysis
- `mcp__mcp-ticketer__ticket_list` - List tickets by status
- `mcp__mcp-ticketer__ticket_search` - Find priority tickets
- `mcp__mcp-ticketer__ticket_find_stale` - Identify stale work
- `mcp__mcp-ticketer__get_my_tickets` - User's assigned tickets

**Expected Output**:
```
Comprehensive Project Status Report
===================================

Project Health: ON_TRACK ✅

Ticket Summary:
- Total: 42 tickets
- Open: 8 (19%)
- In Progress: 5 (12%)
- In Review: 3 (7%)
- Done: 26 (62%)

Completion Rate: 62% (26/42 tickets)

High-Priority Open Work (3):
🔴 TICKET-190: Critical security patch
🔴 TICKET-192: Performance degradation fix
🟡 TICKET-195: OAuth2 token refresh

Blockers (2):
⚠️ TICKET-188: Waiting for external API approval (5 days)
⚠️ TICKET-189: Blocked by infrastructure deployment

Recent Activity (Last 7 Days):
- 8 tickets completed
- 4 new tickets created
- 12 status transitions
- 3 tickets moved to review

Risk Assessment:
⚠️ 2 blocked tickets need escalation
⚠️ 3 high-priority items require immediate attention
✅ Overall velocity is healthy
✅ No stale tickets (>30 days inactive)

Recommended Actions:
1. Escalate blocked tickets (TICKET-188, TICKET-189)
2. Prioritize critical security patch (TICKET-190)
3. Review 3 tickets in UAT for completion
```

**Example Usage**:
```
User: "/mpm-ticket status"
PM: "I'll have ticketing generate a comprehensive status report..."
[PM delegates to ticketing agent for full analysis]
PM: [Presents ticketing agent's status report]
```

---

### /mpm-ticket update

Create project status update (Linear ProjectUpdate or platform equivalent).

**Purpose**: Document sprint/project progress for stakeholders.

**PM Delegation Pattern**:
```
PM delegates to ticketing agent:
"Create project status update:
1. Analyze project progress since last update
2. Calculate completion metrics
3. Identify key accomplishments
4. Note blockers or risks
5. Set health indicator (on_track/at_risk/off_track)
6. Create ProjectUpdate with summary
7. Return update link"
```

**MCP Tools Used** (by ticketing agent):
- `mcp__mcp-ticketer__project_status` - Get project metrics
- `mcp__mcp-ticketer__project_update_create` - Create update
- `mcp__mcp-ticketer__project_update_list` - View previous updates
- `mcp__mcp-ticketer__ticket_list` - Recent completions

**Expected Output**:
```
Project Update Created
======================

Update ID: UPDATE-2025-11-29
Project: Q4 Roadmap Implementation
Health: ON_TRACK ✅

Summary:
Sprint completed with strong momentum. 8 tickets completed this week,
including critical security patches and OAuth2 implementation. 2 blockers
identified requiring stakeholder escalation.

Key Accomplishments:
✅ OAuth2 implementation complete (TICKET-180)
✅ Security patches deployed (TICKET-190)
✅ Performance optimization delivered (TICKET-192)

Metrics:
- Completion: 62% (26/42 tickets)
- Velocity: +8 tickets this week
- Blockers: 2 (down from 4 last week)

Risks:
⚠️ External API approval delayed 5 days
⚠️ Infrastructure deployment blocked

Next Sprint Focus:
- Resolve 2 blocked tickets
- Complete 3 in-review tickets
- Begin authentication epic

Update Published:
🔗 https://linear.app/team/updates/UPDATE-2025-11-29
```

**Example Usage**:
```
User: "/mpm-ticket update"
PM: "I'll have ticketing create a project status update..."
[PM delegates to ticketing agent to generate update]
PM: [Presents ticketing agent's update confirmation]
```

---

## Implementation

**CRITICAL DELEGATION PATTERN**: PM must delegate ALL ticketing operations to ticketing agent.

### PM Never Uses MCP Tools Directly

**WRONG** ❌:
```
# PM directly using MCP tools
result = mcp__mcp-ticketer__ticket_list()
result = mcp__mcp-ticketer__project_status()
```

**CORRECT** ✅:
```
# PM delegates to ticketing agent
PM: "I'll have ticketing [organize/analyze/update] tickets..."
[PM constructs delegation prompt for ticketing agent]
[Ticketing agent uses MCP tools]
PM: [Presents ticketing agent's results to user]
```

### Delegation Template

**Standard PM Delegation for Ticketing Work**:
```
PM receives: /mpm-ticket [subcommand]

PM evaluates:
1. Identifies this is ticketing work
2. Constructs delegation prompt
3. Delegates to ticketing agent
4. Waits for ticketing agent response
5. Presents results to user

PM NEVER:
- Calls mcp-ticketer MCP tools directly
- Uses aitrackdown CLI directly
- Reads/writes ticket files directly
- Bypasses ticketing agent
```

### Fallback Strategy

**If mcp-ticketer MCP unavailable**, ticketing agent falls back to aitrackdown CLI:

```bash
# Fallback CLI commands
aitrackdown status tasks              # List tickets
aitrackdown show TICKET-123           # Read ticket
aitrackdown transition TICKET-123 done  # Update state
aitrackdown comment TICKET-123 "text" # Add comment
```

**PM still delegates to ticketing agent** - ticketing agent handles CLI fallback internally.

---

## Examples

### Complete Workflow Example

**User Request**: "Organize my tickets and tell me what to work on next"

**PM Response Flow**:
```
PM: "I'll organize your tickets and analyze next steps..."

[Step 1: Organize tickets]
PM delegates to ticketing: "/mpm-ticket organize"
Ticketing agent:
- Lists open tickets
- Transitions completed work
- Updates priorities
- Reports organization results

[Step 2: Analyze next steps]
PM delegates to ticketing: "/mpm-ticket proceed"
Ticketing agent:
- Gets project status
- Analyzes priorities
- Recommends top 3 actions

PM: [Presents combined results to user]
```

**Expected PM Output**:
```
Ticket organization complete! Here's your status and next steps:

Organization Summary:
✅ 5 tickets transitioned to Done/UAT
✅ 3 priorities updated
⚠️ 2 stale tickets identified

Next Recommended Actions:

1. 🔴 TICKET-177: Fix authentication blocker (CRITICAL)
   - Unblocks 2 other tickets
   - Estimated: 2-3 hours

2. 🟡 TICKET-180: Complete OAuth2 implementation
   - 70% complete, high impact
   - Estimated: 4 hours

3. 🟢 TICKET-185: Add error handling tests
   - No blockers, improves stability
   - Estimated: 2 hours

Would you like me to start work on TICKET-177?
```

---

### Weekly Status Update Example

**User Request**: "Create weekly status update"

**PM Response Flow**:
```
PM: "I'll have ticketing generate this week's status update..."

PM delegates to ticketing: "/mpm-ticket update"
Ticketing agent:
- Analyzes project progress
- Calculates completion metrics
- Identifies accomplishments
- Notes blockers and risks
- Creates ProjectUpdate
- Returns update link

PM: [Presents ticketing agent's update to user]
```

---

### Project Setup Example

**User Request**: "Set up ticketing for https://linear.app/team/project/abc-123"

**PM Response Flow**:
```
PM: "I'll configure project context for Linear..."

PM delegates to ticketing: "/mpm-ticket project https://linear.app/team/project/abc-123"
Ticketing agent:
- Parses Linear URL
- Extracts project ID
- Verifies access
- Stores configuration
- Confirms setup

PM: [Presents ticketing agent's confirmation]
```

---

## Related Commands

- `/mpm-status`: Overall Claude MPM system status
- `/mpm-init`: Initialize or update project documentation
- `/mpm-help`: Show all available MPM commands

---

## Notes

**Agent Delegation Architecture**:
- PM is the **orchestrator**, not the executor
- Ticketing agent is the **specialist** for all ticket operations
- PM delegates ALL ticketing work without exception
- Ticketing agent handles MCP-first with CLI fallback internally

**MCP-First Integration**:
- Ticketing agent prefers mcp-ticketer MCP tools when available
- Automatic fallback to aitrackdown CLI if MCP unavailable
- PM never needs to know which integration is used

**Command Design Philosophy**:
- High-level workflows (organize, proceed, status, update)
- Comprehensive analysis and reporting
- Actionable insights and recommendations
- Single-command operations for common tasks

**Error Handling**:
- If ticketing agent unavailable: PM informs user and provides manual steps
- If MCP and CLI unavailable: Ticketing agent reports integration status
- All errors escalated to PM for user communication
