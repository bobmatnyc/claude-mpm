# Agent-Centric Design Principles for MCP Servers

## Overview

Before implementing any MCP server, understand how to design tools for AI agents. Agents are fundamentally different users than humans - they have limited context, no visual UI, and think in terms of workflows rather than API calls.

**Core Philosophy:** Build thoughtful, high-impact workflow tools, not API endpoint wrappers.

---

## Why Agent-Centric Design Matters

MCP servers expose tools that AI agents use to accomplish tasks. The quality of your server is measured by how effectively agents complete realistic workflows, not by API coverage.

**Key Differences from Human-Oriented Design:**

| Human Users | AI Agents |
|-------------|-----------|
| Visual UI navigation | No visual interface |
| Unlimited attention | Limited context window |
| Can ask clarifying questions | Must work with available information |
| Tolerate verbose responses | Need concise, high-signal data |
| Learn from documentation | Learn from tool descriptions and errors |

---

## The Five Design Principles

### 1. Build for Workflows, Not Just API Endpoints

**The Problem:**
Directly wrapping API endpoints creates tools that are too granular for agents to use effectively. Agents must make many calls to accomplish simple tasks.

**The Solution:**
Consolidate related operations into workflow-oriented tools that accomplish complete tasks.

**Examples:**

❌ **Poor Design (API Wrapper):**
```
check_calendar_availability(date, time)
create_calendar_event(date, time, title, description)
send_notification(user_id, message)
```
Agent must: Check availability → Create event → Send notification (3 separate calls)

✅ **Good Design (Workflow-Oriented):**
```
schedule_event(date, time, title, description, attendees)
  - Checks availability automatically
  - Creates event if slot is free
  - Notifies attendees
  - Returns single consolidated result
```
Agent makes 1 call to complete the workflow.

**Guidelines:**
- Identify common multi-step workflows users perform
- Combine related operations that always happen together
- Provide atomic operations for complex use cases
- Let tools handle internal coordination and error recovery

### 2. Optimize for Limited Context

**The Problem:**
Agents have constrained context windows. Verbose responses waste precious tokens and reduce what agents can accomplish.

**The Solution:**
Return high-signal information by default. Provide options for detail levels.

**Examples:**

❌ **Poor Design (Information Dump):**
```json
{
  "user": {
    "id": "U123456",
    "name": "John Doe",
    "email": "john@example.com",
    "profile": {
      "avatar_urls": {
        "small": "https://...",
        "medium": "https://...",
        "large": "https://...",
        "xlarge": "https://..."
      },
      "bio": "Lorem ipsum...",
      "location": "San Francisco",
      "timezone": "America/Los_Angeles",
      "created_at": 1609459200,
      "updated_at": 1609459200,
      "preferences": {...},
      "settings": {...}
    }
  }
}
```
15+ fields returned when agent only needs name and email.

✅ **Good Design (High-Signal Default):**
```json
{
  "user": {
    "id": "U123456",
    "name": "John Doe",
    "email": "john@example.com"
  }
}
```
Concise by default. Add `detail_level="full"` parameter for complete data when needed.

**Guidelines:**
- Default to concise responses with essential information
- Provide `response_format` parameter: "concise" vs "detailed"
- Use human-readable identifiers (names) over technical codes (IDs) when possible
- Support Markdown for human readability, JSON for programmatic processing
- Implement character limits (typically 25,000) with truncation guidance
- Respect pagination limits strictly - never load all results

### 3. Design Actionable Error Messages

**The Problem:**
Generic error messages tell agents what failed but not how to fix it. Agents get stuck or waste attempts guessing.

**The Solution:**
Every error should guide agents toward correct usage with specific next steps.

**Examples:**

❌ **Poor Design (Diagnostic Only):**
```
"Error: Invalid parameters"
"Error: Request failed"
"Error: Too many results"
```
Tells what failed, not how to fix it.

✅ **Good Design (Actionable Guidance):**
```
"Error: Query too broad - returned 1,247 results. Try adding filters:
use 'team:marketing' to filter by team, or 'status:active'
to filter by status. Or use limit=50 with offset for pagination."

"Error: Date format invalid. Expected YYYY-MM-DD (e.g., '2024-01-15'),
received '01/15/2024'. Please use ISO format."

"Error: Missing required field 'project_id'. To find project IDs,
use list_projects(team='your-team') first."
```
Each error teaches correct usage patterns.

**Guidelines:**
- Explain what's wrong and why
- Suggest specific fixes or alternative parameters
- Reference other tools when needed ("use X tool to find Y first")
- Include examples of correct usage in error messages
- Guide agents through multi-step corrections
- Make errors educational, not just diagnostic

### 4. Follow Natural Task Subdivisions

**The Problem:**
Tool organization that mirrors API structure doesn't match how agents think about tasks.

**The Solution:**
Organize and name tools around natural task categories that align with agent reasoning.

**Examples:**

❌ **Poor Design (API Structure):**
```
api_users_get(id)
api_users_list(filters)
api_users_create(data)
api_projects_get(id)
api_projects_list(filters)
```
Tool names reflect internal API, not user tasks.

✅ **Good Design (Task-Oriented):**
```
search_users(query, team, status)
get_user_details(user_id)
create_user_account(name, email, team)

find_projects(name, status, team)
get_project_info(project_id)
create_project(name, team, deadline)
```
Tool names reflect what agents want to accomplish.

**Guidelines:**
- Use action verbs that describe tasks: search, find, create, update, analyze
- Group related tools with consistent prefixes for discoverability
- Include service prefix to prevent conflicts: `slack_send_message` not `send_message`
- Name tools how humans would describe the task
- Use consistent naming patterns within your server

### 5. Use Evaluation-Driven Development

**The Problem:**
Building without testing against realistic agent use cases leads to tools that seem correct but fail in practice.

**The Solution:**
Create evaluation scenarios early and iterate based on actual agent performance.

**Examples:**

**Evaluation-First Workflow:**
1. **Before Implementation**: Define 10 realistic questions agents should answer
2. **Prototype Quickly**: Build minimal tool set to attempt evaluations
3. **Run Evaluations**: See where agents struggle
4. **Iterate**: Improve tools based on agent feedback
5. **Repeat**: Until agents successfully complete 80%+ of evaluations

**Common Discoveries from Evaluations:**
- Agents couldn't find information → Add search/filter tools
- Agents made too many calls → Consolidate into workflow tools
- Agents got confused → Improve tool descriptions and error messages
- Agents ran out of context → Reduce response verbosity
- Agents used tools incorrectly → Add actionable error guidance

**Guidelines:**
- Write evaluations before implementing all tools
- Use realistic, complex questions requiring multiple tool calls
- Let agent failures drive tool design decisions
- Iterate based on evaluation results, not assumptions
- Aim for 80%+ agent success rate on evaluations

---

## Applying These Principles: A Case Study

**Scenario:** Building an MCP server for a project management API.

### ❌ API Wrapper Approach (Poor)

```python
@mcp.tool()
async def get_task(task_id: str):
    """Get a task by ID."""
    return api.tasks.get(task_id)

@mcp.tool()
async def list_tasks(project_id: str):
    """List all tasks in a project."""
    return api.tasks.list(project_id)

@mcp.tool()
async def get_user(user_id: str):
    """Get user by ID."""
    return api.users.get(user_id)

@mcp.tool()
async def update_task_status(task_id: str, status: str):
    """Update task status."""
    return api.tasks.update(task_id, {"status": status})
```

**Problems:**
- Too granular - agent needs many calls for simple workflows
- Returns all fields - wastes context on unnecessary data
- No guidance on valid statuses or error handling
- Agent must know IDs before making calls
- Mirrors API structure, not task structure

### ✅ Agent-Centric Approach (Good)

```python
@mcp.tool()
async def search_tasks(
    query: str,
    project: Optional[str] = None,
    status: Optional[str] = None,
    assignee: Optional[str] = None,
    limit: int = 20,
    response_format: str = "markdown"
) -> str:
    """Search for tasks across projects with flexible filtering.

    Finds tasks by name, description, or tags. Returns concise results
    by default - use response_format='json' for full data.

    Common workflows:
    - Find all bugs: search_tasks(query="bug", status="open")
    - Find your tasks: search_tasks(assignee="your-name")
    - Find by project: search_tasks(project="website-redesign")

    Error guidance:
    - If too many results: Add more filters or use limit parameter
    - If no results: Try broader query or check project name spelling
    - To find project names: Use list_projects() first
    """
    # Implementation with:
    # - Concise markdown by default
    # - Full JSON if requested
    # - Actionable errors with examples
    # - Character limit enforcement

@mcp.tool()
async def complete_task(
    task_id: str,
    completion_note: Optional[str] = None,
    notify_team: bool = True
) -> str:
    """Mark a task complete and optionally notify the team.

    This is a workflow tool that:
    1. Validates task can be completed (not blocked, has assignee)
    2. Updates task status to 'completed'
    3. Adds completion note to task history
    4. Sends notifications to team members (if notify_team=True)
    5. Updates project progress metrics

    Returns: Success message with task name and updated project status

    Error guidance:
    - "Task is blocked": Lists blocking tasks with IDs
    - "Task has no assignee": Suggests using assign_task(task_id, user)
    - "Invalid task_id": Suggests using search_tasks() to find task
    """
    # Implementation handles entire workflow

@mcp.tool()
async def get_project_status(
    project_name: str,
    include_tasks: bool = False
) -> str:
    """Get project overview with completion metrics.

    Returns concise summary by default:
    - Total tasks, completed, in-progress, blocked
    - Recent activity
    - Team members
    - Due date and status

    Use include_tasks=True to also list all tasks (uses more context).

    Error guidance:
    - "Project not found": Lists similar project names
    - "Access denied": Explains permission requirements
    """
    # Returns high-signal summary
```

**Improvements:**
- **Workflow-oriented**: `complete_task` handles entire workflow, not just status update
- **Context-efficient**: Concise by default, detailed on request
- **Actionable errors**: Guides agents to correct usage
- **Natural naming**: Search, complete, get_status (task-oriented, not API-oriented)
- **Flexible search**: One tool handles multiple search scenarios
- **Human-readable**: Uses project names, not just IDs

---

## Pre-Implementation Checklist

Before writing any code, ensure you understand:

- [ ] What workflows will agents actually need to accomplish?
- [ ] What's the minimum information needed for each workflow?
- [ ] What errors will agents encounter and how can I guide them?
- [ ] How can I consolidate related operations into single tools?
- [ ] What evaluation scenarios will test if this works?
- [ ] Are tool names task-oriented or API-oriented?
- [ ] Do tools default to concise responses?
- [ ] Do errors teach correct usage?

---

## Common Anti-Patterns to Avoid

### Anti-Pattern 1: CRUD Over Everything
Creating separate create/read/update/delete tools for every resource.

**Instead:** Create workflow tools that combine operations intelligently.

### Anti-Pattern 2: The Everything Tool
One tool that takes 15+ parameters and tries to do everything.

**Instead:** Multiple focused tools, each solving one clear workflow.

### Anti-Pattern 3: ID-Only Interfaces
Requiring agents to have IDs before calling any tools.

**Instead:** Search/find tools that work with human-readable names.

### Anti-Pattern 4: Silent Truncation
Cutting off results without telling the agent.

**Instead:** Clear truncation messages with guidance on filtering.

### Anti-Pattern 5: Error Code Responses
Returning `ERR_401`, `ERR_404` without explanation.

**Instead:** Actionable error messages with specific next steps.

---

## Next Steps

After understanding these principles:

1. **Review Real Examples**: Look at well-designed MCP servers in the wild
2. **Start Planning**: Create your implementation plan with these principles in mind
3. **Load Workflow Guide**: See [workflow.md](./workflow.md) for step-by-step implementation
4. **Reference Best Practices**: Use [mcp_best_practices.md](./mcp_best_practices.md) for technical details
5. **Create Evaluations Early**: Don't wait until implementation is complete

---

**Remember:** Agents are your users. Design for their constraints, optimize for their workflows, and guide them to success through every interaction.
