# Ticketing Delegation Workflow

**Version**: 1.0.0
**Last Updated**: 2025-11-21
**Status**: Active - Enforced via Circuit Breaker #6

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [MCP-First Priority](#mcp-first-priority)
4. [PM Enforcement Rules](#pm-enforcement-rules)
5. [Examples](#examples)
6. [Ticketing Agent Capabilities](#ticketing-agent-capabilities)
7. [When API Access is Acceptable](#when-api-access-is-acceptable)
8. [Testing the Workflow](#testing-the-workflow)
9. [Troubleshooting](#troubleshooting)
10. [References](#references)

---

## Overview

### Mandatory Ticketing Delegation Requirement

**CRITICAL**: PM (Project Manager agent) MUST ALWAYS delegate ALL ticketing operations to the ticketing-agent. PM is NEVER permitted to use ticketing tools directly.

This is enforced by **Circuit Breaker #6: Ticketing Tool Misuse Detection**.

### Why PM Must Always Delegate to Ticketing-Agent

**ticketing-agent provides critical functionality that PM lacks:**

1. **MCP-First Routing**: Automatically detects and uses `mcp-ticketer` MCP tools when available
2. **Graceful Fallback**: Falls back to `aitrackdown` CLI when MCP tools unavailable
3. **Ticket Management Expertise**: PM lacks specialized ticket management knowledge
4. **Error Handling**: Provides proper error messages with setup instructions
5. **Consistency**: Ensures consistent ticket operations across all PM sessions

**PM's role is coordination, not ticket management.** PM should focus on delegation and verification, not implementation details.

### Benefits of MCP-First Architecture

The ticketing delegation workflow uses an **MCP-first architecture** that provides:

- **Tool Abstraction**: Single interface (`ticketing-agent`) works across multiple ticket systems
- **Automatic Detection**: MCP server presence detected automatically
- **Zero Configuration**: Works out-of-box when MCP server installed
- **Backward Compatibility**: Falls back to CLI when MCP unavailable
- **Better Error Messages**: Clear guidance when neither MCP nor CLI available

---

## Architecture

### Flow Diagram

```
┌──────────┐
│   User   │ "Create ticket for this bug"
└─────┬────┘
      │
      v
┌─────────────────┐
│   PM Agent      │ "I'll delegate to ticketing-agent"
│                 │ [Uses Task tool with subagent_type="ticketing"]
└─────┬───────────┘
      │
      v
┌──────────────────────────────────────────────────┐
│           ticketing-agent                        │
│  ┌────────────────────────────────────────┐     │
│  │ 1. Detect MCP tools availability       │     │
│  │    - Check for mcp__mcp-ticketer__*    │     │
│  └─────────────┬──────────────────────────┘     │
│                │                                  │
│                v                                  │
│    ┌──────────────────────┐                      │
│    │ MCP Available?       │                      │
│    └──────┬───────────────┘                      │
│           │                                       │
│     YES ──┘           NO ──┐                     │
│      │                     │                      │
│      v                     v                      │
│  ┌─────────────────┐  ┌──────────────────────┐  │
│  │ Use MCP Tools   │  │ Use aitrackdown CLI  │  │
│  │ mcp-ticketer    │  │ $ aitrackdown create │  │
│  └─────────────────┘  └──────────────────────┘  │
│           │                     │                 │
│           └──────────┬──────────┘                │
│                      v                            │
│            ┌──────────────────┐                  │
│            │ Execute Operation│                  │
│            │ (Create/Read/    │                  │
│            │  Update/Delete)  │                  │
│            └──────────────────┘                  │
└──────────────────────────────────────────────────┘
      │
      v
┌─────────────────┐
│ Ticket Created  │ ISS-0042
│ Return Results  │
└─────────────────┘
```

### Component Responsibilities

#### User
- Makes ticketing requests using natural language
- May reference ticket systems (Linear, JIRA, GitHub Issues)

#### PM Agent
- **ONLY DELEGATES** - Never uses ticketing tools directly
- Detects ticketing keywords in user requests
- Routes ALL ticketing operations to ticketing-agent via Task tool
- Verifies ticketing-agent results and reports back to user

#### ticketing-agent
- **Ticket Management Specialist** - Handles all ticketing operations
- **MCP Detection** - Automatically detects mcp-ticketer availability
- **Tool Selection** - Uses MCP when available, falls back to CLI
- **Error Handling** - Provides setup instructions when tools unavailable
- **CRUD Operations** - Create, Read, Update, Delete tickets
- **Hierarchy Management** - Handles Epic → Issue → Task relationships
- **State Transitions** - Manages ticket workflow states
- **Label Detection** - Automatically applies relevant labels/tags

---

## MCP-First Priority

### What mcp-ticketer Provides

**mcp-ticketer** is an MCP (Model Context Protocol) server that provides:

1. **Unified Interface**: Single API for multiple ticket systems
   - Linear (GraphQL API)
   - GitHub Issues (REST API)
   - JIRA (REST API v3)
   - File-based tracking (aitrackdown backend)

2. **Rich Functionality**:
   - `mcp__mcp-ticketer__ticket_create` - Create tickets
   - `mcp__mcp-ticketer__ticket_read` - Read ticket details
   - `mcp__mcp-ticketer__ticket_update` - Update tickets
   - `mcp__mcp-ticketer__ticket_list` - List tickets with filters
   - `mcp__mcp-ticketer__ticket_search` - Search tickets
   - `mcp__mcp-ticketer__ticket_comment` - Add comments
   - `mcp__mcp-ticketer__ticket_attach` - Attach files
   - `mcp__mcp-ticketer__ticket_transition` - State transitions
   - `mcp__mcp-ticketer__epic_create` - Create epics
   - `mcp__mcp-ticketer__issue_create` - Create issues
   - `mcp__mcp-ticketer__task_create` - Create tasks

3. **Better Error Handling**:
   - Validation before submission
   - Clear error messages
   - Automatic retry logic
   - Connection status checks

### When to Use MCP Tools vs CLI Fallback

**Decision Tree:**

```
┌──────────────────────────────────────┐
│ ticketing-agent receives request    │
└─────────────┬────────────────────────┘
              │
              v
┌─────────────────────────────────────────────────┐
│ Check: Are mcp-ticketer tools available?       │
│ (Look for tools prefixed mcp__mcp-ticketer__*) │
└─────────────┬───────────────────────────────────┘
              │
       YES ───┴─── NO
        │           │
        v           v
┌─────────────┐  ┌──────────────────┐
│ USE MCP     │  │ CHECK CLI        │
│ TOOLS       │  │ (aitrackdown)    │
└─────────────┘  └────┬─────────────┘
                      │
               YES ───┴─── NO
                │           │
                v           v
         ┌─────────────┐  ┌─────────────────────┐
         │ USE CLI     │  │ REPORT ERROR        │
         │ FALLBACK    │  │ Provide setup guide │
         └─────────────┘  └─────────────────────┘
```

### Automatic Detection Mechanism

ticketing-agent uses the following detection logic:

```python
# Conceptual detection (ticketing-agent does this internally)

# Step 1: Check MCP tool availability
mcp_available = "mcp__mcp-ticketer__ticket_create" in available_tools

# Step 2: If MCP not available, check CLI
if not mcp_available:
    cli_available = bash("which aitrackdown") returns successfully

# Step 3: Choose integration
if mcp_available:
    use_mcp_tools()
elif cli_available:
    use_cli_fallback()
else:
    report_error_with_setup_instructions()
```

### Graceful Degradation Path

The ticketing workflow degrades gracefully:

1. **Optimal Path**: MCP tools available → Use mcp-ticketer
2. **Fallback Path**: MCP unavailable, CLI available → Use aitrackdown
3. **Error Path**: Both unavailable → Provide setup instructions

**No ticket operations fail silently.** User always gets actionable feedback.

---

## PM Enforcement Rules

### Circuit Breaker #6 Explained

**Circuit Breaker #6** is an automatic violation detection mechanism that prevents PM from using ticketing tools directly.

**Full Definition**: See [Circuit Breaker #6](../../src/claude_mpm/agents/circuit-breakers.md#circuit-breaker-6-ticketing-tool-misuse-detection)

**Purpose**: Enforce mandatory delegation of ALL ticketing operations to ticketing-agent

**Trigger Conditions**:
- PM uses any `mcp__mcp-ticketer__*` tool
- PM runs `aitrackdown` CLI commands
- PM accesses Linear/GitHub/JIRA APIs directly
- PM reads/writes ticket data without delegating

**Violation Response**:
```
❌ [VIOLATION #6] PM attempted ticketing tool usage - Must delegate to ticketing-agent
```

**Escalation**:
- **Violation #1**: Warning displayed to user
- **Violation #2**: Requires user acknowledgment to continue
- **Violation #3+**: Session reset with delegation reminder

### Forbidden PM Actions (Direct Tool Usage)

**PM is NEVER permitted to:**

❌ Call `mcp__mcp-ticketer__ticket_create()` directly
❌ Call `mcp__mcp-ticketer__ticket_read()` directly
❌ Call `mcp__mcp-ticketer__ticket_update()` directly
❌ Run `aitrackdown create issue "..."` via Bash
❌ Run `aitrackdown show TICKET-123` via Bash
❌ Run `aitrackdown transition ...` via Bash
❌ Make `curl` requests to Linear/GitHub/JIRA APIs
❌ Read ticket files directly from `.aitrackdown/` directory
❌ Edit ticket YAML files manually

**All of the above are VIOLATIONS.**

### Required PM Responses for Ticketing Keywords

**When PM detects ticketing keywords in user request:**

**Ticketing Keywords:**
- "ticket", "epic", "issue", "task"
- "Linear", "GitHub Issues", "JIRA", "aitrackdown"
- "create ticket", "update ticket", "read ticket", "list tickets"
- "track this", "file a ticket", "log this"
- Any ticket ID reference (e.g., "ISS-0042", "MPM-101", "PROJ-123")

**Required PM Response Pattern:**

```
User: [Message with ticketing keywords]
PM: "I'll delegate to ticketing-agent for [operation]"
[Uses Task tool with subagent_type="ticketing"]
```

**Example:**
```
User: "Create a ticket for this bug"
PM: "I'll delegate to ticketing-agent for ticket creation"
Task(
    agent="ticketing",
    subagent_type="ticketing",
    task="Create ticket: Bug in authentication flow..."
)
```

### Violation Detection and Tracking

**How violations are detected:**

1. **Tool Call Monitoring**: System monitors PM's tool calls
2. **Pattern Matching**: Detects `mcp__mcp-ticketer__*` or `aitrackdown` usage
3. **Immediate Stop**: Circuit breaker triggers before tool executes
4. **Violation Logged**: Recorded in session violation log
5. **User Notification**: Warning displayed to user
6. **Escalation**: Repeated violations escalate (warning → acknowledgment → reset)

**Violation Log Format:**
```
[2025-11-21 10:33:42] VIOLATION #6: PM used mcp__mcp-ticketer__ticket_create
  - User request: "Create a ticket for this bug"
  - PM action: Called mcp__mcp-ticketer__ticket_create() directly
  - Required action: Use Task tool to delegate to ticketing-agent
  - Status: VIOLATION LOGGED
```

---

## Examples

### Correct Pattern

#### Example 1: Create Ticket
```
User: "Create a ticket for the authentication bug we just found"

PM: "I'll delegate to ticketing-agent for ticket creation"

[PM uses Task tool:]
Task(
    agent="ticketing",
    subagent_type="ticketing",
    task="Create issue ticket: Bug - Authentication fails for users with special characters in password. Priority: high. Tags: bug, authentication, frontend"
)

[ticketing-agent executes:]
- Checks for mcp-ticketer tools
- IF available: Uses mcp__mcp-ticketer__ticket_create()
- ELSE: Uses aitrackdown CLI: `aitrackdown create issue "Bug - Authentication fails..." --priority high --tag bug --tag authentication --tag frontend`
- Returns: ISS-0042 created

PM: "Ticket created: ISS-0042 - Bug: Authentication fails for users with special characters"
```

#### Example 2: Read Ticket
```
User: "What's the status of ticket ISS-0042?"

PM: "I'll have ticketing-agent retrieve the ticket details"

[PM uses Task tool:]
Task(
    agent="ticketing",
    subagent_type="ticketing",
    task="Read ticket ISS-0042 and report status, assignee, and description"
)

[ticketing-agent executes:]
- Uses mcp__mcp-ticketer__ticket_read(ticket_id="ISS-0042") if available
- Else: Uses `aitrackdown show ISS-0042`
- Returns ticket details

PM: "Ticket ISS-0042 status: in_progress
- Title: Bug - Authentication fails for special characters
- Assignee: user@example.com
- Priority: high
- Last updated: 2025-11-21"
```

#### Example 3: Update Ticket State
```
User: "Mark ISS-0042 as ready for testing"

PM: "I'll delegate to ticketing-agent to update the ticket state"

[PM uses Task tool:]
Task(
    agent="ticketing",
    subagent_type="ticketing",
    task="Transition ticket ISS-0042 to 'ready' state with comment 'Bug fix complete, ready for QA testing'"
)

[ticketing-agent executes:]
- Uses mcp__mcp-ticketer__ticket_transition() or aitrackdown CLI
- Updates state and adds comment

PM: "Ticket ISS-0042 updated to 'ready' state with QA comment"
```

### Violation Pattern

#### ❌ WRONG: PM Using MCP Tools Directly

```
User: "Create a ticket for this bug"

PM: [Calls mcp__mcp-ticketer__ticket_create(...) directly]  ← VIOLATION

❌ [VIOLATION #6] PM attempted ticketing tool usage - Must delegate to ticketing-agent
```

**What should happen instead:**
```
User: "Create a ticket for this bug"

PM: "I'll delegate to ticketing-agent for ticket creation"
Task(agent="ticketing", ...)  ← CORRECT
```

#### ❌ WRONG: PM Using CLI Directly

```
User: "What's the status of ISS-0042?"

PM: Bash("aitrackdown show ISS-0042")  ← VIOLATION

❌ [VIOLATION #6] PM attempted ticketing CLI usage - Must delegate to ticketing-agent
```

**What should happen instead:**
```
User: "What's the status of ISS-0042?"

PM: "I'll have ticketing-agent retrieve ticket ISS-0042"
Task(agent="ticketing", ...)  ← CORRECT
```

#### ❌ WRONG: PM Accessing APIs Directly

```
User: "Get my Linear tickets"

PM: Bash('curl -H "Authorization: Bearer $LINEAR_API_KEY" ...')  ← VIOLATION

❌ [VIOLATION #6] PM attempted direct API access - Must delegate to ticketing-agent
```

**What should happen instead:**
```
User: "Get my Linear tickets"

PM: "I'll delegate to ticketing-agent to retrieve your Linear tickets"
Task(agent="ticketing", ...)  ← CORRECT
```

### Real-World Example from User's Issue

**❌ WRONG (PM doing ticketing directly):**

```
User: "continue with 1M-75"

PM: [Determines 1M-75 is a Linear ticket ID]
PM: Bash('curl -s -H "Authorization: Bearer $LINEAR_API_KEY" \
    -H "Content-Type: application/json" \
    -d "{\"query\":\"query { issue(id:\\\"1M-75\\\") { ... } }\"}" \
    https://api.linear.app/graphql')  ← VIOLATION

❌ [VIOLATION #6] PM attempted direct Linear API access
```

**✅ CORRECT (PM delegates to ticketing-agent):**

```
User: "continue with 1M-75"

PM: [Recognizes 1M-75 as Linear ticket]
PM: "I'll have ticketing-agent retrieve Linear ticket 1M-75"

Task(
    agent="ticketing",
    subagent_type="ticketing",
    task="Read Linear ticket 1M-75 and provide full details including title, description, status, and acceptance criteria"
)

[ticketing-agent executes:]
- Checks for mcp-ticketer availability
- Uses mcp__mcp-ticketer__ticket_read(ticket_id="1M-75") if available
- Ticket system automatically detects Linear backend
- Returns ticket details

PM: "Retrieved Linear ticket 1M-75:
- Title: Implement OAuth2 authentication
- Status: in_progress
- Description: Add OAuth2 support for Google and GitHub providers
- Acceptance Criteria: [lists criteria]"
```

---

## Ticketing Agent Capabilities

### What ticketing-agent Handles

ticketing-agent is the **single source of truth** for all ticketing operations.

**Ticket CRUD Operations:**
- ✅ Create tickets (epics, issues, tasks)
- ✅ Read ticket details and status
- ✅ Update ticket metadata (title, description, priority)
- ✅ Delete/close tickets
- ✅ Search and filter tickets

**Hierarchy Management:**
- ✅ Create Epic → Issue → Task hierarchies
- ✅ Link child tickets to parents
- ✅ Maintain parent-child relationships
- ✅ Query hierarchy trees

**Workflow Operations:**
- ✅ Transition tickets through states (open → in_progress → ready → tested → done)
- ✅ Add comments to tickets
- ✅ Attach files to tickets
- ✅ Apply labels/tags
- ✅ Assign tickets to users

**Integration Support:**
- ✅ Linear (via mcp-ticketer or GraphQL API)
- ✅ GitHub Issues (via mcp-ticketer or REST API)
- ✅ JIRA (via mcp-ticketer or REST API v3)
- ✅ aitrackdown (file-based tracking)

### MCP Tool Detection

ticketing-agent automatically detects MCP tool availability:

**Detection Steps:**
1. **Tool Enumeration**: Check available tools list
2. **Prefix Matching**: Look for `mcp__mcp-ticketer__*` tools
3. **Tool Presence**: If found, use MCP tools
4. **Fallback Check**: If not found, check CLI availability

**Detection Code (Conceptual):**
```python
def detect_mcp_availability(available_tools: list) -> bool:
    """Check if mcp-ticketer tools are available."""
    mcp_tools = [
        "mcp__mcp-ticketer__ticket_create",
        "mcp__mcp-ticketer__ticket_read",
        "mcp__mcp-ticketer__ticket_update",
        # ... other mcp-ticketer tools
    ]
    return any(tool in available_tools for tool in mcp_tools)
```

**No manual configuration required.** Detection is automatic.

### CLI Fallback Behavior

When MCP tools unavailable, ticketing-agent falls back to CLI:

**Fallback Operations:**

| Operation | MCP Tool | CLI Fallback |
|-----------|----------|--------------|
| Create Epic | `mcp__mcp-ticketer__epic_create()` | `aitrackdown create epic "Title" --description "..."` |
| Create Issue | `mcp__mcp-ticketer__issue_create()` | `aitrackdown create issue "Title" --priority high` |
| Create Task | `mcp__mcp-ticketer__task_create()` | `aitrackdown create task "Title" --issue ISS-001` |
| Read Ticket | `mcp__mcp-ticketer__ticket_read()` | `aitrackdown show ISS-001` |
| Update State | `mcp__mcp-ticketer__ticket_transition()` | `aitrackdown transition ISS-001 in-progress` |
| List Tickets | `mcp__mcp-ticketer__ticket_list()` | `aitrackdown status tasks` |
| Search | `mcp__mcp-ticketer__ticket_search()` | `aitrackdown search tasks "keyword"` |
| Add Comment | `mcp__mcp-ticketer__ticket_comment()` | `aitrackdown comment ISS-001 "Comment text"` |

**CLI commands are executed via Bash tool with proper error handling.**

### Error Handling and User Guidance

ticketing-agent provides helpful error messages:

**When MCP and CLI both unavailable:**
```
Error: No ticket integration available

To use ticketing features, install one of:

Option 1: mcp-ticketer (Recommended)
  - Unified interface for Linear, GitHub Issues, JIRA
  - Installation: npm install -g @modelcontextprotocol/mcp-ticketer
  - Configuration: Add to MCP servers in Claude Desktop

Option 2: aitrackdown CLI (Fallback)
  - File-based ticket tracking
  - Installation: pip install aitrackdown
  - Initialization: Run `aitrackdown init` in project directory

Visit docs for setup instructions:
  - MCP setup: https://docs.claude-mpm.com/ticketing/mcp-setup
  - CLI setup: https://docs.claude-mpm.com/ticketing/cli-setup
```

**When invalid ticket ID provided:**
```
Error: Ticket not found: ISS-0999

Possible issues:
  - Ticket ID does not exist
  - Incorrect ticket system (are you using Linear vs aitrackdown?)
  - Typo in ticket ID

To list all tickets: Use "list all open tickets" command
```

---

## When API Access is Acceptable

### Exceptions to Delegation Rule

**API access is acceptable ONLY when:**

1. **No Adapter Available**
   - System not supported by mcp-ticketer
   - System not supported by aitrackdown CLI
   - Example: Proprietary internal ticket system

2. **Custom/Proprietary Ticketing Systems**
   - Company-specific ticket platforms
   - Legacy internal tools
   - Custom-built issue trackers

3. **Both Conditions Apply:**
   - System requires direct API access
   - AND must still be delegated to ticketing-agent (not PM!)

**IMPORTANT**: Even when direct API access is required, PM must still delegate to ticketing-agent. PM never makes API calls directly.

### Delegation Pattern for Custom Systems

```
User: "Create ticket in our custom InternalTracker system"

PM: "I'll delegate to ticketing-agent for InternalTracker ticket creation"

Task(
    agent="ticketing",
    subagent_type="ticketing",
    task="Create ticket in InternalTracker system using direct API: [details]"
)

[ticketing-agent executes:]
- Recognizes custom system requirement
- Uses Bash to make API call
- Handles authentication
- Parses response
- Returns ticket details in standardized format
```

### Why ticketing-agent Makes API Calls (Not PM)

**ticketing-agent has specialized knowledge:**
- API authentication patterns
- Request/response formatting
- Error handling for API failures
- Ticket data structure understanding
- System-specific quirks and workarounds

**PM lacks this expertise** and should never attempt direct API access.

---

## Testing the Workflow

### How to Verify MCP Tools are Available

**Method 1: Check Available Tools**
Ask Claude to list available tools and look for `mcp__mcp-ticketer__*` prefix:

```
User: "What ticketing tools do you have available?"

Expected Response:
- mcp__mcp-ticketer__ticket_create
- mcp__mcp-ticketer__ticket_read
- mcp__mcp-ticketer__ticket_update
- [etc...]
```

**Method 2: Check MCP Configuration**
```bash
# Check if mcp-ticketer is configured
cat ~/.config/claude-desktop/config.json | grep mcp-ticketer

# Expected output:
"mcp-ticketer": {
  "command": "npx",
  "args": ["-y", "@modelcontextprotocol/mcp-ticketer"]
}
```

**Method 3: Request Test Operation**
```
User: "Create a test ticket to verify ticketing integration"

Expected:
- ticketing-agent detects MCP tools
- Uses mcp-ticketer if available
- Falls back to CLI if not
- Reports which integration was used
```

### How to Test Delegation

**Test Case 1: Basic Ticket Creation**
```
User: "Create a ticket for testing"

Expected PM Behavior:
1. PM recognizes ticketing keyword
2. PM says "I'll delegate to ticketing-agent"
3. PM uses Task tool with agent="ticketing"
4. ticketing-agent creates ticket
5. PM reports result: "Ticket created: ISS-XXXX"

Expected Violation (if PM does it directly):
❌ PM calls mcp__mcp-ticketer__ticket_create() → VIOLATION
```

**Test Case 2: Ticket Reading**
```
User: "What's the status of ISS-0042?"

Expected PM Behavior:
1. PM recognizes ticket ID reference
2. PM delegates to ticketing-agent
3. ticketing-agent retrieves ticket
4. PM reports status to user

Expected Violation (if PM does it directly):
❌ PM runs `aitrackdown show ISS-0042` → VIOLATION
```

**Test Case 3: Linear/JIRA/GitHub References**
```
User: "Get my Linear tickets"

Expected PM Behavior:
1. PM recognizes "Linear" keyword
2. PM delegates to ticketing-agent
3. ticketing-agent handles Linear integration
4. PM reports results

Expected Violation (if PM does it directly):
❌ PM makes curl request to Linear API → VIOLATION
```

### Expected Behavior Patterns

**✅ Correct Behavior:**
- PM always says "I'll delegate to ticketing-agent"
- PM always uses Task tool for ticketing operations
- ticketing-agent handles MCP/CLI detection automatically
- User sees ticket IDs and status updates

**❌ Violation Indicators:**
- PM calls `mcp__mcp-ticketer__*` tools directly
- PM runs `aitrackdown` commands via Bash
- PM makes API calls to Linear/GitHub/JIRA
- PM reads/writes ticket files directly
- Error: "VIOLATION #6: PM attempted ticketing tool usage"

---

## Troubleshooting

### MCP Tools Not Detected

**Symptom**: ticketing-agent always uses CLI, never MCP tools

**Diagnosis:**
```bash
# Check MCP server configuration
cat ~/.config/claude-desktop/config.json | grep mcp-ticketer

# Verify mcp-ticketer installation
npx -y @modelcontextprotocol/mcp-ticketer --version
```

**Solution:**
1. Install mcp-ticketer: `npm install -g @modelcontextprotocol/mcp-ticketer`
2. Add to Claude Desktop config:
   ```json
   {
     "mcpServers": {
       "mcp-ticketer": {
         "command": "npx",
         "args": ["-y", "@modelcontextprotocol/mcp-ticketer"]
       }
     }
   }
   ```
3. Restart Claude Desktop
4. Verify tools available: "What ticketing tools do you have?"

### CLI Not Available

**Symptom**: Error message "aitrackdown command not found"

**Diagnosis:**
```bash
# Check if aitrackdown installed
which aitrackdown

# Expected: /path/to/aitrackdown
# Not found: command not found
```

**Solution:**
```bash
# Install aitrackdown
pip install aitrackdown

# Initialize in project directory
cd /path/to/project
aitrackdown init

# Verify installation
aitrackdown --version
```

### Both Unavailable

**Symptom**: Error message "No ticket integration available"

**Diagnosis**: Neither MCP nor CLI installed

**Solution**: Install one of:

**Option 1: mcp-ticketer (Recommended)**
```bash
npm install -g @modelcontextprotocol/mcp-ticketer
# Add to Claude Desktop config
```

**Option 2: aitrackdown CLI**
```bash
pip install aitrackdown
cd /path/to/project
aitrackdown init
```

### PM Violating Delegation

**Symptom**: PM using ticketing tools directly

**Diagnosis**: Circuit Breaker #6 should trigger but PM still attempts violations

**Solution:**
1. Check PM instructions are up-to-date
2. Verify Circuit Breaker #6 is active
3. Review [circuit-breakers.md](../../src/claude_mpm/agents/circuit-breakers.md#circuit-breaker-6-ticketing-tool-misuse-detection)
4. Report issue if Circuit Breaker not triggering

**Expected Circuit Breaker Response:**
```
❌ [VIOLATION #6] PM attempted mcp__mcp-ticketer__ticket_create
  - Required action: Use Task tool to delegate to ticketing-agent
  - Violations logged: 1 (WARNING level)
```

### Integration Errors

**Symptom**: Ticket operations fail with API errors

**Diagnosis**: Credentials or configuration issues

**Linear Errors:**
```
Error: Linear API authentication failed
```
**Solution**: Set `LINEAR_API_KEY` environment variable

**GitHub Errors:**
```
Error: GitHub API authentication failed
```
**Solution**: Set `GITHUB_TOKEN` or `GH_TOKEN` environment variable

**JIRA Errors:**
```
Error: JIRA authentication failed
```
**Solution**: Set `JIRA_API_TOKEN` and `JIRA_EMAIL` environment variables

---

## References

### Internal Documentation

**Circuit Breaker #6 Definition:**
[Circuit Breakers Reference](../../src/claude_mpm/agents/circuit-breakers.md#circuit-breaker-6-ticketing-tool-misuse-detection)

**PM Delegation Matrix:**
[PM Instructions](../reference/pm-instructions.md)

**ticketing-agent Reference:**
[Agent Capabilities Reference](../../docs/agents/agent-capabilities-reference.md) - See ticketing agent capabilities and workflow

**PM Workflow Documentation:**
[docs/agents/pm-workflow.md](../agents/pm-workflow.md)

### External Documentation

**mcp-ticketer Documentation:**
- GitHub: https://github.com/modelcontextprotocol/servers/tree/main/ticketer
- MCP Specification: https://modelcontextprotocol.io
- Installation: `npm install -g @modelcontextprotocol/mcp-ticketer`

**aitrackdown CLI Documentation:**
- GitHub: https://github.com/bobmatnyc/aitrackdown
- PyPI: https://pypi.org/project/aitrackdown/
- Installation: `pip install aitrackdown`

**Linear API Documentation:**
- GraphQL API: https://developers.linear.app/docs/graphql/working-with-the-graphql-api
- Authentication: https://developers.linear.app/docs/oauth/authentication

**GitHub Issues API:**
- REST API: https://docs.github.com/en/rest/issues
- Authentication: https://docs.github.com/en/authentication

**JIRA REST API:**
- API v3: https://developer.atlassian.com/cloud/jira/platform/rest/v3/intro/
- Authentication: https://developer.atlassian.com/cloud/jira/platform/authentication/

---

## Quick Reference

### PM Ticketing Keywords Detection

**When user message contains any of:**
- "ticket", "epic", "issue", "task"
- "Linear", "GitHub Issues", "JIRA", "aitrackdown"
- "create ticket", "update ticket", "read ticket", "list tickets"
- "track this", "file a ticket", "log this"
- Ticket ID patterns: `ISS-XXXX`, `EP-XXXX`, `TSK-XXXX`, `MPM-XXX`, `PROJ-XXX`

**PM MUST respond with:**
```
"I'll delegate to ticketing-agent for [operation]"
[Uses Task tool with agent="ticketing"]
```

### ticketing-agent Workflow

```
1. Receive delegation from PM
2. Detect MCP tool availability
3. IF mcp-ticketer available:
     Use MCP tools (mcp__mcp-ticketer__*)
   ELSE IF aitrackdown CLI available:
     Use CLI commands (aitrackdown ...)
   ELSE:
     Report error with setup instructions
4. Execute ticket operation
5. Return standardized results to PM
6. PM reports to user
```

### Violation Quick Check

**Is PM doing this?**
- ❌ Calling `mcp__mcp-ticketer__*` tools → VIOLATION
- ❌ Running `aitrackdown` commands → VIOLATION
- ❌ Making API calls to ticket systems → VIOLATION
- ✅ Using Task tool to delegate to ticketing-agent → CORRECT

---

**Document Status**: Active
**Last Review**: 2025-11-21
**Next Review**: 2025-12-21
**Maintained By**: Claude MPM Team
