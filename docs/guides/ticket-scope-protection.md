# Ticket-Scoped Work Protection

**Version**: 1.0
**Status**: Active
**Audience**: End Users

## Table of Contents

1. [Overview](#overview)
2. [How It Works](#how-it-works)
3. [User Workflow Examples](#user-workflow-examples)
4. [Best Practices](#best-practices)
5. [FAQ](#faq)
6. [Configuration](#configuration)

---

## Overview

### What is Scope Protection?

Scope protection is Claude MPM's intelligent system that prevents **uncontrolled scope creep** during ticket-based work. When you provide a ticket URL or ID, the PM automatically enforces work boundaries to keep your project focused and organized.

**Think of scope as your "working directory"**:
- Just like a directory contains specific files, a ticket contains specific acceptance criteria
- Work that doesn't fit the ticket's scope belongs in a different "directory" (ticket)
- Scope protection prevents accidentally mixing unrelated work into a single ticket

### Why Does It Matter?

**Without Scope Protection**:
- You request: "Add OAuth2 authentication" (TICKET-123)
- Research discovers: 15 optimization opportunities during analysis
- Result: TICKET-123 becomes a dumping ground for ALL discovered work
- Critical bugs get buried as "follow-ups" instead of separate priorities
- Original 2-day ticket becomes a 2-week mega-ticket

**With Scope Protection**:
- You request: "Add OAuth2 authentication" (TICKET-123)
- Research discovers: 15 optimization opportunities
- PM asks: "Which items are truly required for OAuth2 acceptance criteria?"
- Result: 2 in-scope subtasks, 3 enhancement tickets, 10 backlog items
- Each item gets appropriate priority and tracking

### Benefits for Users

✅ **Controlled Expansion**: You explicitly approve scope changes
✅ **Clear Priorities**: Critical bugs get separate tickets with proper urgency
✅ **Focused Work**: Original ticket scope stays clean and achievable
✅ **Better Estimates**: Accurate effort tracking when scope is protected
✅ **Organized Backlog**: Related but separate work properly categorized

---

## How It Works

### Scope as "Working Directory" Analogy

```
Your Ticket (TICKET-123):
├── In-Scope/              # Required for acceptance criteria
│   ├── token_refresh.py   # Must implement
│   └── error_handling.py  # Must implement
│
├── Scope-Adjacent/        # Related enhancements (optional)
│   ├── session_mgmt.py    # Nice to have
│   └── profile_updates.py # Enhancement
│
└── Out-of-Scope/          # Separate concerns (different tickets)
    ├── database_optimize.sql  # Separate refactoring
    ├── api_rate_limit.py      # Separate feature
    └── memory_leak_fix.py     # Separate bug
```

### Three Classification Types

#### 1. IN-SCOPE (Required)

**Definition**: Work directly required to satisfy the ticket's acceptance criteria.

**Examples** (for "Add OAuth2 authentication" ticket):
- ✅ OAuth2 token exchange implementation
- ✅ Token refresh mechanism
- ✅ OAuth2 error handling
- ✅ User authentication flow

**Outcome**: Created as **subtasks** under the originating ticket

---

#### 2. SCOPE-ADJACENT (Related but Optional)

**Definition**: Related work that enhances the ticket but isn't blocking acceptance.

**Examples** (for "Add OAuth2 authentication" ticket):
- ⚠️ Session management improvements
- ⚠️ User profile updates
- ⚠️ Remember-me functionality
- ⚠️ OAuth2 provider configuration UI

**Outcome**: PM **asks user** whether to:
- Expand ticket scope to include these
- Create separate enhancement tickets
- Defer to backlog

---

#### 3. OUT-OF-SCOPE (Separate Initiative)

**Definition**: Separate work discovered during ticket implementation but unrelated to acceptance criteria.

**Examples** (for "Add OAuth2 authentication" ticket):
- ❌ Database query optimizations
- ❌ API rate limiting
- ❌ Caching layer implementation
- ❌ Memory leak in unrelated middleware
- ❌ API versioning strategy

**Outcome**: Created as **separate tickets** or **epic**, NOT linked to originating ticket

---

### PM Workflow When Scope Detected

**Step 1: User Provides Ticket**
```
User: "Implement https://linear.app/acme/issue/ENG-456"
```

**Step 2: PM Fetches Ticket Context**
```
PM: "I've detected ticket ENG-456. Let me fetch the details..."
[PM uses mcp-ticketer to read ticket]
[PM extracts: title, description, acceptance criteria, priority]
```

**Step 3: PM Delegates with Scope Boundaries**
```
PM: "Delegating to Engineer with ticket context..."

Task: Implement OAuth2 authentication (ENG-456)

🎫 TICKET CONTEXT:
- Acceptance Criteria: [from ticket description]
- Priority: High
- Tags: [authentication, security]

🛡️ SCOPE BOUNDARIES:
- IN-SCOPE: OAuth2 flow, token handling, error handling
- Ask before adding: Enhancements beyond acceptance criteria
```

**Step 4: Agent Discovers Additional Work**
```
Research Agent: "Found 10 optimization opportunities during analysis"
```

**Step 5: PM Classifies Discovered Work**
```
PM classifies 10 items:
- IN-SCOPE (2): Token refresh, OAuth2 error handling
- SCOPE-ADJACENT (3): Session improvements, profile updates, remember-me
- OUT-OF-SCOPE (5): Database optimization, caching, memory leak, etc.
```

**Step 6: PM Asks User for Scope Decision**
```
PM: "Agent discovered 10 items during ENG-456 work:

In-Scope (2 items - required for acceptance criteria):
- Token refresh mechanism
- OAuth2 error handling

Scope-Adjacent (3 items - related enhancements):
- Session management improvements
- User profile updates
- Remember-me functionality

Out-of-Scope (5 items - separate concerns):
- Database query optimizations
- API rate limiting
- Caching layer implementation
- Memory leak in unrelated middleware
- API versioning strategy

How would you like to proceed?
1. Include all 10 in ENG-456 scope (accept scope expansion)
2. Create 2 subtasks (in-scope only), defer rest to backlog
3. Create 2 subtasks + separate 'System Optimization' epic for other 8 items"
```

**Step 7: User Makes Decision**
```
User: "Option 3 - keep ENG-456 focused, create separate epic for optimizations"
```

**Step 8: PM Delegates with Scope Boundaries**
```
PM to ticketing-agent: "Create 2 subtasks under ENG-456:
- ENG-457: Token refresh mechanism (in-scope)
- ENG-458: OAuth2 error handling (in-scope)

Create separate epic 'System Optimization' with 8 tickets:
- Tag all 8 as 'discovered-during-eng-456' but NOT as children
- Epic description: 'Optimization opportunities discovered during OAuth2 implementation'
- Link back to ENG-456 in epic description for context"
```

---

## User Workflow Examples

### Example 1: Providing Ticket URL Triggers Scope Protection

**Scenario**: You want PM to implement a feature from your ticketing system.

**Your Action**:
```
You: "Implement the feature in https://linear.app/acme/issue/ENG-456"
```

**What PM Does Automatically**:

1. **Detects ticket URL** → Recognizes Linear URL pattern
2. **Fetches ticket context** → Uses mcp-ticketer to read ENG-456
3. **Extracts scope boundaries** → Identifies acceptance criteria
4. **Delegates with scope** → Passes ticket context to all agents
5. **Monitors for scope drift** → Watches for discovered work outside scope

**What You'll See**:
```
PM: "I've detected Linear ticket ENG-456. Let me fetch the details to better scope this work...

Based on ticket ENG-456 (Add dark mode toggle), I'll delegate to Engineer with enhanced context:

Ticket Context:
- Title: Add dark mode toggle
- Priority: Medium
- Acceptance Criteria: Toggle switches themes, preference saved, WCAG compliant

🛡️ Scope Protection Active: Work will be validated against ticket's acceptance criteria."
```

---

### Example 2: PM Asks Scope Questions During Work

**Scenario**: Research agent discovers additional work during ticket-based task.

**Timeline**:

**T+0**: You provide ticket
```
You: "Fix the bug in MPM-789"
```

**T+2**: PM delegates to Research
```
PM: "Delegating to Research Agent to investigate MPM-789...

🎫 Ticket Context: MPM-789 - Memory leak in session handler
Acceptance Criteria: Fix leak, verify memory stable under load

🛡️ Scope Protection Active"
```

**T+10**: Research discovers additional issues
```
Research Agent: "I've identified 8 issues during investigation:
1. Memory leak in session handler (original issue)
2. Related leak in auth middleware
3. Session cleanup not running
4. Database connection pool leak
5. Inefficient query patterns
6. Missing cache layer
7. API rate limiting needed
8. Logging overhead"
```

**T+11**: PM classifies and asks you
```
PM: "Research discovered 8 items during MPM-789 work:

In-Scope (3 items - required to fix memory leak):
- Memory leak in session handler (original bug)
- Related leak in auth middleware (same root cause)
- Session cleanup not running (contributing factor)

Scope-Adjacent (2 items - related improvements):
- Database connection pool leak (similar issue, different subsystem)
- Inefficient query patterns (memory pressure)

Out-of-Scope (3 items - separate initiatives):
- Missing cache layer (performance optimization)
- API rate limiting (separate feature)
- Logging overhead (separate optimization)

How would you like to proceed?
1. Expand MPM-789 to include all 8 items
2. Fix 3 in-scope items, create separate bugs for leaks, defer rest
3. Fix 3 in-scope items, create 2 bug tickets + 1 optimization epic for rest"
```

**T+12**: You make decision
```
You: "Option 3 - keep bug fix focused, track other leaks separately"
```

**T+13**: PM delegates with boundaries
```
PM: "Understood. I'll:
1. Keep MPM-789 focused on original session memory leak (3 subtasks)
2. Create 2 separate bug tickets for connection pool leak and query patterns
3. Create 'System Optimization' epic for cache, rate limiting, and logging

Delegating to Engineer to fix MPM-789 with clear scope boundaries..."
```

---

### Example 3: Making Scope Decisions

**Scenario**: You need to decide how to handle discovered scope-adjacent work.

**Question Types You'll See**:

#### Option A: Accept Scope Expansion
```
"Include all items in current ticket scope"

✅ Use when: Related work is tightly coupled
⚠️ Warning: Ticket effort will increase significantly
```

#### Option B: Focus on In-Scope Only
```
"Create subtasks for in-scope items, defer rest to backlog"

✅ Use when: Want to stay focused on original acceptance criteria
✅ Benefit: Original ticket remains small and achievable
```

#### Option C: Create Separate Epic
```
"Create subtasks for in-scope + separate epic for related work"

✅ Use when: Discovered work is valuable but separate initiative
✅ Benefit: Proper prioritization and organization
```

**Example Decision Matrix**:

| Discovered Work | Classification | Your Decision | Outcome |
|----------------|----------------|---------------|---------|
| OAuth2 token refresh | IN-SCOPE | ✅ Subtask | Required for acceptance |
| OAuth2 error handling | IN-SCOPE | ✅ Subtask | Required for acceptance |
| Session improvements | SCOPE-ADJACENT | 🤔 Ask me | Related enhancement |
| Profile updates | SCOPE-ADJACENT | 🤔 Ask me | Related enhancement |
| Database optimization | OUT-OF-SCOPE | 📋 Separate ticket | Unrelated refactoring |
| API rate limiting | OUT-OF-SCOPE | 📋 Separate ticket | Unrelated feature |

---

## Best Practices

### When to Use Ticket URLs

**✅ Always Provide Ticket URL/ID When**:
- Working on existing tickets from your tracking system
- Implementing features with defined acceptance criteria
- Fixing bugs tracked in Linear, GitHub Issues, or Jira
- Following sprint plans or roadmap items

**Example**:
```bash
# Good - includes ticket reference
"Implement https://linear.app/team/issue/ENG-456"
"Fix bug MPM-789"
"Complete TEAM-123 from our sprint"

# Acceptable - ad-hoc work without ticket
"Add logging to the auth service"
"Refactor user model for clarity"
```

**Benefits of Providing Ticket URLs**:
- ✅ PM automatically fetches context (saves you explaining)
- ✅ Scope protection prevents uncontrolled expansion
- ✅ All work properly linked back to ticket
- ✅ Progress automatically tracked in your ticketing system

---

### How to Structure Ticket Scope

**Write Clear Acceptance Criteria in Your Tickets**:

```markdown
# ✅ Good Ticket Structure (ENG-456: Add OAuth2 Authentication)

## Acceptance Criteria
1. Users can authenticate via OAuth2 providers (Google, GitHub)
2. OAuth2 token exchange implemented with error handling
3. Token refresh mechanism prevents session expiration
4. User session persists across browser restarts
5. Authentication flow meets WCAG accessibility standards

## Out of Scope
- User profile management (separate ticket)
- Multi-factor authentication (future epic)
- Session analytics (separate feature)
```

**Why This Helps**:
- PM can accurately classify discovered work
- Clear boundaries reduce scope questions
- Agents know exactly what's required vs. optional

**❌ Poor Ticket Structure**:
```markdown
# Bad Example (ENG-456: Add Authentication)

Implement authentication. Make it secure and user-friendly.
```

**Problems**:
- Vague acceptance criteria
- No clear scope boundaries
- PM can't distinguish in-scope from scope-adjacent work

---

### Managing Scope-Adjacent Work

**When PM Asks About Scope-Adjacent Items**:

**Option 1: Expand Scope (Accept into current ticket)**
```
✅ Use when:
- Work is tightly coupled with acceptance criteria
- Effort increase is manageable (<50% original estimate)
- All work has same priority

⚠️ Warning: Ticket effort increases, may delay completion
```

**Option 2: Defer to Backlog**
```
✅ Use when:
- Enhancements can wait
- Current ticket should stay focused
- Limited time/resources

📋 Result: Items tracked but not actively worked
```

**Option 3: Create Separate Tickets/Epic**
```
✅ Use when:
- Discovered work is valuable but separate concern
- Different priorities than original ticket
- Want proper tracking and planning

📋 Result: Proper ticket hierarchy, clear priorities
```

**Example Decision Process**:

```
PM: "Found 3 scope-adjacent items during ENG-456 (OAuth2 implementation):
1. Session management improvements
2. User profile updates
3. Remember-me functionality

How would you like to proceed?"

Your thought process:
- Session improvements: Tightly coupled with OAuth2 → Expand scope (Option 1)
- Profile updates: Nice to have, not urgent → Defer to backlog (Option 2)
- Remember-me: Separate feature, needs UX design → Separate ticket (Option 3)

Your response:
"Include session improvements in ENG-456. Defer profile updates to backlog.
Create separate ticket for remember-me with UX design requirements."
```

---

## FAQ

### What happens if I want to expand scope?

**Answer**: You have full control! When PM detects scope-adjacent work, you can choose to expand scope:

```
PM: "Found 3 scope-adjacent items. How would you like to proceed?
1. Include all 3 in ENG-456 scope (accept expansion)
2. Create subtasks for in-scope only
3. Create subtasks + separate epic"

You: "Option 1 - include all in ENG-456"

PM: "Understood. Expanding ENG-456 scope to include all 3 items.
Delegating to Engineer with updated requirements..."
```

**Effect**: Original ticket scope expands to include the additional work. Estimate and completion time will increase accordingly.

---

### Can I disable scope protection?

**Answer**: Scope protection is **automatic when you provide a ticket URL or ID**. It's a core feature to prevent uncontrolled scope creep.

**However, you can work without tickets**:

```bash
# With ticket (scope protection active)
"Implement https://linear.app/team/issue/ENG-456"

# Without ticket (ad-hoc work, no scope protection)
"Add OAuth2 authentication to the app"
```

**Why No Disable Option?**:
- Scope protection prevents common project management issues
- Only activates when ticket context is present
- Minimal overhead (just asks when scope boundaries unclear)
- Critical for maintaining organized ticket tracking

**If you find scope questions disruptive**, consider:
1. Write clearer acceptance criteria in tickets
2. Use "in-scope only" as default choice
3. Provide ad-hoc work requests without ticket URLs

---

### How do I track discovered work outside scope?

**Answer**: PM automatically creates proper tickets/epics based on your scope decision.

**Example Flow**:

```
PM: "Research discovered 10 items during TICKET-123 work:
- In-Scope: 2 items
- Scope-Adjacent: 3 items
- Out-of-Scope: 5 items

How would you like to proceed?"

You: "Create subtasks for in-scope, separate epic for the rest"

PM: "Delegating to ticketing-agent to:
1. Create 2 subtasks under TICKET-123 (in-scope work)
2. Create 'System Optimization' epic with 8 tickets (other items)
3. Link epic back to TICKET-123 for context"

[ticketing-agent creates tickets automatically]

PM: "Work tracked:
- TICKET-124: Token refresh (subtask of TICKET-123)
- TICKET-125: Error handling (subtask of TICKET-123)
- EPIC-10: System Optimization (8 tickets)
  - TICKET-126: Database optimization
  - TICKET-127: API rate limiting
  - ... (6 more tickets)

All work is now properly tracked in your ticketing system."
```

**Tracking Options**:

| Classification | Tracking Option | Priority | Visibility |
|----------------|----------------|----------|------------|
| IN-SCOPE | Subtask under original ticket | Inherited from parent | Blocks parent ticket |
| SCOPE-ADJACENT | Separate ticket or backlog | User decides | Independent tracking |
| OUT-OF-SCOPE | Separate ticket/epic | User decides | Proper prioritization |

---

### What if I disagree with PM's scope classification?

**Answer**: **You have final say!** PM's classification is a recommendation. You can override it.

**Example**:

```
PM: "I've classified 'user profile updates' as SCOPE-ADJACENT for TICKET-123
(OAuth2 authentication). Would you like to include it?"

You: "No, that's actually IN-SCOPE because OAuth2 needs profile data."

PM: "Understood. Reclassifying 'user profile updates' as IN-SCOPE.
Creating as subtask of TICKET-123..."
```

**How to Override**:
- Clearly state your scope decision
- Explain why if classification seems wrong
- PM will adjust and proceed with your guidance

---

### Does scope protection work with all ticketing systems?

**Answer**: Yes! Scope protection works with any ticketing system supported by `mcp-ticketer`:

**Supported Platforms**:
- ✅ **Linear** (https://linear.app)
- ✅ **GitHub Issues** (https://github.com)
- ✅ **Jira** (Atlassian)
- ✅ **Asana**
- ✅ **AiTrackDown** (local file-based)

**URL Detection Examples**:
```bash
# Linear
"Implement https://linear.app/acme/issue/ENG-456"

# GitHub Issues
"Fix https://github.com/owner/repo/issues/123"

# Jira
"Complete https://company.atlassian.net/browse/PROJ-456"

# Ticket ID (uses default adapter)
"Work on TICKET-123"
```

**Configuration Required**:
- Install: `pipx install mcp-ticketer`
- Configure in Claude Desktop MCP settings
- PM automatically detects and uses available ticketing tools

See [MCP Ticketer Documentation](https://github.com/bobmatnyc/mcp-ticketer) for setup instructions.

---

### What if PM can't access my ticketing system?

**Answer**: Scope protection gracefully degrades. PM will still enforce scope boundaries based on your description.

**With Ticketing Access** (Ideal):
```
You: "Implement https://linear.app/team/issue/ENG-456"
PM: [Automatically fetches ticket details]
PM: [Extracts acceptance criteria]
PM: [Enforces scope protection based on ticket]
```

**Without Ticketing Access** (Graceful Degradation):
```
You: "Implement the OAuth2 feature from ENG-456"
PM: "I've detected ticket reference ENG-456, but mcp-ticketer tools
are not currently available.

I'll proceed with delegation based on your request. Please provide
the acceptance criteria from ENG-456 so I can enforce scope boundaries."

You: "Acceptance criteria: OAuth2 token exchange, refresh mechanism,
error handling"

PM: "Thank you. Delegating to Engineer with scope boundaries based
on provided criteria..."
```

**Key Points**:
- ✅ Scope protection still works (based on your criteria)
- ✅ PM proceeds without blocking on missing tools
- ✅ You provide ticket context manually
- ⚠️ Manual ticket updates required after work completes

---

## Configuration

### Prerequisites

**Required for Full Scope Protection**:
1. **mcp-ticketer** installed and configured
2. **Ticketing system credentials** (Linear API key, GitHub token, etc.)
3. **Claude MPM** 5.4.68+

**Installation**:
```bash
# Install mcp-ticketer
pipx install mcp-ticketer

# Configure in Claude Desktop
# Add to ~/Library/Application Support/Claude/claude_desktop_config.json
{
  "mcpServers": {
    "mcp-ticketer": {
      "command": "mcp-ticketer",
      "env": {
        "LINEAR_API_KEY": "your-linear-api-key",
        "GITHUB_TOKEN": "your-github-token"
      }
    }
  }
}
```

See [MCP Ticketer Setup Guide](https://github.com/bobmatnyc/mcp-ticketer#setup) for detailed instructions.

---

### No Configuration Needed for Basic Usage

**Scope protection is automatic** when:
- ✅ You provide ticket URL in request
- ✅ mcp-ticketer is available (Claude Desktop MCP)
- ✅ PM detects ticket patterns (URL or ID format)

**No Claude MPM configuration changes required**:
- Scope protection is built into PM agent
- Activates automatically on ticket detection
- No feature flags or settings to enable

---

### Customizing Scope Behavior (Advanced)

**Adjusting Scope Thresholds** (PM_INSTRUCTIONS.md):

By default, PM asks about scope when **>3 items discovered**. You can adjust by modifying PM instructions:

```yaml
# Not user-configurable via configuration.yaml
# Requires PM agent instruction updates (advanced)

Scope Violation Detection:
  high_risk_threshold: 3  # items before scope validation required
  critical_keywords: ["critical", "bug", "security"]  # triggers out-of-scope
```

**Most users don't need this** - default thresholds work well for most projects.

---

### Deploying Agent Updates with Scope Protection

**If You've Customized PM Agent**:

Scope protection is built into PM v0006+ instructions. To ensure you have latest scope protection:

```bash
# Check PM agent version
grep "PM_INSTRUCTIONS_VERSION" ~/.claude/agents/pm.md

# Redeploy PM agent (if version < 0006)
claude-mpm agents deploy pm --force

# Verify scope protection instructions present
grep "SCOPE PROTECTION PROTOCOL" ~/.claude/agents/pm.md
```

**Expected Output**:
```
<!-- PM_INSTRUCTIONS_VERSION: 0006 -->
...
🛡️ SCOPE PROTECTION PROTOCOL (MANDATORY)
```

If version is 0006+, scope protection is active. No further configuration needed.

---

## Related Documentation

- **[PM Agent Instructions](../reference/pm-instructions.md)** - Complete PM workflow reference
- **[Agent Capabilities Reference](../agents/agent-capabilities-reference.md)** - Ticketing agent capabilities
- **[MCP Ticketer](https://github.com/bobmatnyc/mcp-ticketer)** - Ticketing system integration
- **[Structured Questions](structured-questions.md)** - How PM asks scope validation questions

---

## Feedback

Scope protection is an active feature designed to prevent common project management issues. If you have feedback or suggestions:

- **GitHub Issues**: [claude-mpm/issues](https://github.com/bobmatnyc/claude-mpm/issues)
- **Feature Requests**: Tag with `scope-protection` label
- **Bug Reports**: Include ticket URL and PM's scope classification

---

**Last Updated**: 2025-11-23
**PM Agent Version**: 0006+
**Feature Status**: Active (Automatic)
