---
title: Ticketing Workflows Guide
version: 1.0.0
last_updated: 2025-11-29
status: current
---

# Ticketing Workflows Guide

Complete guide to using `/mpm-ticket` slash command for comprehensive project management.

## Table of Contents

- [Overview](#overview)
- [Getting Started](#getting-started)
- [Workflow Examples](#workflow-examples)
- [Subcommand Reference](#subcommand-reference)
- [Integration Patterns](#integration-patterns)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

## Overview

The `/mpm-ticket` slash command provides high-level ticketing workflows that delegate ALL operations to the **ticketing agent**. This ensures consistent, reliable ticket management across Linear, GitHub Issues, JIRA, Asana, and AiTrackDown.

### Key Principles

**Delegation Architecture:**
- PM orchestrates workflows, never executes directly
- Ticketing agent is the specialist for all ticket operations
- MCP-first integration with CLI fallback
- Comprehensive reporting and actionable insights

**Supported Platforms:**
- **Linear** (via MCP Ticketer) - Projects, issues, cycles, and updates
- **GitHub Issues** (via MCP Ticketer) - Milestones, issues, and labels
- **JIRA** (via MCP Ticketer) - Epics, issues, and sprints
- **Asana** (via MCP Ticketer) - Projects and tasks
- **AiTrackDown** (CLI fallback) - Local file-based tracking

## Getting Started

### Prerequisites

**For MCP Integration:**
1. MCP Ticketer server configured in Claude Desktop
2. Platform credentials (Linear API key, GitHub token, JIRA API key, etc.)
3. Project/team access configured

**For AiTrackDown Fallback:**
```bash
# Install AiTrackDown
pip install aitrackdown

# Initialize in project
aitrackdown init
```

### Initial Setup

**Set project context:**
```bash
# In Claude Code session
/mpm-ticket project https://linear.app/yourteam/project/abc-123
```

This configures:
- Default project for all ticket operations
- Team context
- Platform-specific settings
- Validation of access

## Workflow Examples

### Daily Standup Workflow

**Goal:** Prepare for standup meeting with current status.

```bash
# Step 1: Get comprehensive status
/mpm-ticket status

# Review output:
# - What you completed yesterday
# - What you're working on today
# - Any blockers or risks
```

**Example Output:**
```
Comprehensive Project Status Report
===================================

Your Assigned Tickets (5):
- 2 In Progress
- 3 Open

Yesterday's Completions:
✅ TICKET-150: OAuth2 implementation
✅ TICKET-151: Error handling tests

Today's Work:
🔄 TICKET-155: Performance optimization (In Progress)
📋 TICKET-160: Security audit (Open - High Priority)

Blockers:
⚠️ TICKET-158: Waiting for API credentials (3 days)
```

### Weekly Cleanup Workflow

**Goal:** Organize board and prepare weekly update for stakeholders.

```bash
# Step 1: Clean up and organize
/mpm-ticket organize

# Step 2: Create status update
/mpm-ticket update

# Step 3: Plan next week
/mpm-ticket proceed
```

**Workflow Flow:**
1. **Organize** - Transitions completed work, updates priorities, identifies stale tickets
2. **Update** - Creates project status update with metrics and accomplishments
3. **Proceed** - Gets recommendations for next sprint/week

### Sprint Planning Workflow

**Goal:** Analyze board and prioritize next sprint work.

```bash
# Step 1: Review project health
/mpm-ticket status

# Step 2: Get prioritized recommendations
/mpm-ticket proceed

# Step 3: Organize based on recommendations
/mpm-ticket organize
```

**Use Case:**
- Identify high-priority unblocked work
- Understand project health and risks
- Transition completed work from previous sprint
- Plan capacity for upcoming sprint

### "What Should I Work On?" Workflow

**Goal:** Quick analysis of next actionable task.

```bash
# Single command for intelligent recommendations
/mpm-ticket proceed
```

**Example Output:**
```
Recommended Next Actions:

1. 🔴 TICKET-177: Fix authentication blocker (CRITICAL)
   - Blocks: 2 other tickets
   - Estimated: 2-3 hours
   - Reason: Unblocks entire authentication epic

2. 🟡 TICKET-180: Complete OAuth2 implementation
   - Status: 70% complete
   - Estimated: 4 hours
   - Reason: Close to completion, high impact

3. 🟢 TICKET-185: Add error handling tests
   - Dependencies: None
   - Estimated: 2 hours
   - Reason: No blockers, improves stability
```

### End-of-Sprint Workflow

**Goal:** Close out sprint and prepare retrospective data.

```bash
# Step 1: Organize and transition completed work
/mpm-ticket organize

# Step 2: Generate comprehensive status
/mpm-ticket status

# Step 3: Create sprint summary update
/mpm-ticket update
```

**Deliverables:**
- All completed tickets transitioned to Done
- Sprint metrics (velocity, completion rate)
- Identified blockers and carryover work
- Executive summary for stakeholders

### New Project Setup Workflow

**Goal:** Configure ticketing for a new project.

```bash
# Step 1: Set project context
/mpm-ticket project https://linear.app/team/project/new-feature

# Step 2: Review initial status
/mpm-ticket status

# Step 3: Get starting recommendations
/mpm-ticket proceed
```

## Subcommand Reference

### /mpm-ticket organize

**Purpose:** Comprehensive ticket board organization.

**When to Use:**
- End of sprint/week
- Before planning meetings
- When board feels cluttered
- Regular maintenance (weekly recommended)

**What It Does:**
1. Lists all open tickets
2. Identifies completed work not marked Done
3. Transitions tickets through workflow states
4. Updates priorities based on current context
5. Documents work with status comments
6. Identifies stale tickets (no activity >30 days)
7. Flags blocked tickets

**Expected Duration:** 2-5 minutes (depending on ticket count)

**PM Interaction:**
```
User: "/mpm-ticket organize"
PM: "I'll have ticketing organize the project board..."
[PM delegates to ticketing agent]
[Ticketing agent processes all tickets]
PM: [Presents organization summary]
```

### /mpm-ticket proceed

**Purpose:** Intelligent next-action recommendations.

**When to Use:**
- Starting new work
- After completing a ticket
- Planning daily work
- Sprint planning
- When priorities are unclear

**What It Does:**
1. Analyzes project health metrics
2. Lists open tickets by priority
3. Identifies unblocked work
4. Checks for critical dependencies
5. Recommends top 3 tickets with reasoning
6. Estimates effort for each recommendation
7. Explains prioritization logic

**Expected Duration:** 1-3 minutes

**Recommendation Criteria:**
- **Priority:** High/Critical tickets ranked first
- **Blockers:** Only unblocked work recommended
- **Dependencies:** Work that unblocks others prioritized
- **Completion:** Near-complete work boosted in priority
- **Effort:** Balanced mix of quick wins and impactful work

### /mpm-ticket status

**Purpose:** Executive summary of project state.

**When to Use:**
- Daily standups
- Status check-ins
- Before meetings
- Weekly reviews
- Stakeholder updates

**What It Does:**
1. Calculates project health (ON_TRACK/AT_RISK/OFF_TRACK)
2. Summarizes ticket counts by state
3. Lists high-priority open work
4. Identifies blockers and risks
5. Shows recent activity (last 7 days)
6. Calculates completion percentage
7. Provides risk assessment
8. Recommends immediate actions

**Expected Duration:** 1-2 minutes

**Health Indicators:**
- **ON_TRACK** ✅ - No critical blockers, healthy velocity
- **AT_RISK** ⚠️ - Some blockers or priority items need attention
- **OFF_TRACK** 🔴 - Multiple critical issues, velocity problems

### /mpm-ticket update

**Purpose:** Create project status update for stakeholders.

**When to Use:**
- End of sprint
- Weekly updates
- Milestone completion
- Stakeholder reporting
- Project reviews

**What It Does:**
1. Analyzes progress since last update
2. Calculates completion metrics
3. Identifies key accomplishments
4. Notes blockers and risks
5. Sets health indicator
6. Creates ProjectUpdate (Linear) or equivalent
7. Returns shareable update link

**Expected Duration:** 2-4 minutes

**Update Format:**
- **Summary:** High-level overview
- **Accomplishments:** Key wins this period
- **Metrics:** Velocity, completion rate, ticket counts
- **Risks:** Blockers and concerns
- **Next Focus:** Upcoming priorities

### /mpm-ticket project <url>

**Purpose:** Configure project context.

**When to Use:**
- New project setup
- Switching between projects
- Reconfiguring after changes
- Initial ticketing setup

**What It Does:**
1. Parses project URL
2. Extracts platform and project ID
3. Verifies access permissions
4. Stores configuration for future operations
5. Displays project summary
6. Confirms setup

**Expected Duration:** 30 seconds

**Supported URL Formats:**
- Linear: `https://linear.app/team/project/PROJECT-ID`
- GitHub: `https://github.com/owner/repo/projects/123`
- JIRA: `https://company.atlassian.net/browse/PROJECT`
- Asana: `https://app.asana.com/0/PROJECT-ID`

## Integration Patterns

### MCP Ticketer Integration

**Primary Integration Method:**

The ticketing agent uses MCP Ticketer tools for all operations:

**Core Tools:**
- `ticket_list` - Query and filter tickets
- `ticket_read` - Get detailed ticket information
- `ticket_transition` - Move tickets through workflow
- `ticket_update` - Modify ticket fields
- `ticket_comment` - Add/read comments
- `project_status` - Get project health metrics
- `project_update_create` - Create status updates
- `get_my_tickets` - Get user's assigned work
- `get_available_transitions` - Get valid state changes

**Automatic Fallback:**

If MCP Ticketer unavailable, ticketing agent uses AiTrackDown CLI:

```bash
# Fallback CLI commands (handled internally by ticketing agent)
aitrackdown status tasks              # List tickets
aitrackdown show TICKET-123           # Read ticket
aitrackdown transition TICKET-123 done  # Update state
aitrackdown comment TICKET-123 "text" # Add comment
```

**No User Intervention Required** - Ticketing agent handles fallback seamlessly.

### Platform-Specific Features

#### Linear Integration

**Unique Features:**
- Project Updates with health indicators
- Cycle/sprint management
- Team-scoped operations
- Rich markdown descriptions

**Example:**
```bash
/mpm-ticket update  # Creates Linear ProjectUpdate
```

#### GitHub Issues Integration

**Unique Features:**
- Milestone tracking
- Label-based organization
- Pull request linking
- Repository context

**Example:**
```bash
/mpm-ticket project https://github.com/owner/repo/projects/1
```

#### JIRA Integration

**Unique Features:**
- Epic hierarchy
- Sprint planning
- Custom field support
- Issue linking

**Example:**
```bash
/mpm-ticket project https://company.atlassian.net/browse/PROJ-123
```

#### Asana Integration

**Unique Features:**
- Project portfolios
- Task dependencies
- Custom sections
- Team collaboration

**Example:**
```bash
/mpm-ticket project https://app.asana.com/0/PROJECT-ID
```

## Best Practices

### Regular Maintenance

**Daily:**
```bash
# Morning routine
/mpm-ticket proceed     # What to work on today

# End of day
/mpm-ticket organize    # Update completed work
```

**Weekly:**
```bash
# Week start
/mpm-ticket status      # Review health
/mpm-ticket proceed     # Plan week

# Week end
/mpm-ticket organize    # Clean up board
/mpm-ticket update      # Create weekly update
```

**Sprint/Milestone:**
```bash
# Sprint planning
/mpm-ticket status      # Review current state
/mpm-ticket proceed     # Prioritize next sprint

# Sprint retrospective
/mpm-ticket organize    # Close completed work
/mpm-ticket update      # Sprint summary
```

### Efficient Workflows

**Combine Commands:**
```bash
# Morning workflow
User: "What should I work on today?"
PM executes:
1. /mpm-ticket status     # Get context
2. /mpm-ticket proceed    # Get recommendations
[PM presents combined analysis]
```

**Context-Aware Requests:**
```bash
# Good: Specific context
"Create weekly update for Q4 roadmap project"

# Better: Use project context
/mpm-ticket project https://linear.app/team/project/q4-roadmap
"Create weekly update"  # Uses configured project
```

### Delegation Understanding

**PM Role:**
- Orchestrates workflow
- Delegates to ticketing agent
- Presents results to user
- Handles errors and escalation

**Ticketing Agent Role:**
- Executes all ticket operations
- Uses MCP tools or CLI fallback
- Analyzes and reports results
- Maintains ticket context

**User Experience:**
```
User request → PM receives → PM delegates → Ticketing agent executes → PM presents results
```

**Never:** PM directly using MCP ticketing tools ❌
**Always:** PM delegates to ticketing agent ✅

## Troubleshooting

### Common Issues

**Issue:** "Project not configured"
```bash
# Solution: Set project context
/mpm-ticket project <your-project-url>
```

**Issue:** "No tickets found"
```bash
# Verify project access
/mpm-ticket status

# Check configured project
# Ask PM: "What project is configured for ticketing?"
```

**Issue:** "MCP Ticketer unavailable"
```bash
# Ticketing agent automatically falls back to AiTrackDown CLI
# Initialize if needed:
aitrackdown init
```

**Issue:** "Ticketing agent not responding"
```bash
# Verify agent deployment
/mpm-agents list

# Redeploy if needed
claude-mpm agents deploy ticketing --force
```

### Verification Steps

**Check Configuration:**
```bash
# Via Claude Code
/mpm-status

# Via CLI
claude-mpm doctor
```

**Validate Ticket Access:**
```bash
# Test with status command
/mpm-ticket status

# Should show project info and ticket counts
# If error, reconfigure project URL
```

**Test MCP Integration:**
```bash
# In Claude Desktop, check MCP servers
# Settings → Advanced → MCP Servers
# Verify mcp-ticketer is running
```

### Getting Help

**Resources:**
- [Ticket Scope Protection Guide](ticket-scope-protection.md)
- [User Guide - Ticketing Workflows](../user/user-guide.md#ticketing-workflows)
- [Troubleshooting Guide](../user/troubleshooting.md)

**Support Channels:**
- GitHub Issues: Report bugs and feature requests
- Documentation: Check latest guides and references
- Community: Share workflows and best practices

## Related Documentation

- **[User Guide](../user/user-guide.md)** - Complete Claude MPM features
- **[Ticket Scope Protection](ticket-scope-protection.md)** - Best practices for ticket management
- **[Slash Command Standards](../developer/SLASH_COMMAND_STANDARDS.md)** - Command design patterns

---

*Last Updated: 2025-11-29*
*Version: 1.0.0*
