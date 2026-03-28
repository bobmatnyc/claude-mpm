# Complete MCP Server Development Workflow

## Overview

This document provides the complete 4-phase workflow for developing high-quality MCP servers. Follow these steps in order, loading additional reference files as indicated.

**Time Allocation:**
- Phase 1 (Research & Planning): 40%
- Phase 2 (Implementation): 30%
- Phase 3 (Review & Refine): 15%
- Phase 4 (Evaluations): 15%

---

## Phase 1: Deep Research and Planning (40% of effort)

The most critical phase. Insufficient research leads to poor tool design that must be completely rewritten.

### Step 1.1: Understand Agent-Centric Design Principles

**BEFORE writing any code**, understand how to design for AI agents.

**Action:**
- **Read [design_principles.md](./design_principles.md) completely**
- Study the five core principles:
  1. Build for workflows, not API endpoints
  2. Optimize for limited context
  3. Design actionable error messages
  4. Follow natural task subdivisions
  5. Use evaluation-driven development

**Key Takeaways to Internalize:**
- MCP servers serve AI agents, not humans
- Agents have limited context - every token matters
- Agents need workflow tools, not API wrappers
- Error messages must teach correct usage
- Tool names should reflect tasks, not API structure

**Time:** 20-30 minutes of focused reading

**Checkpoint:** Can you explain why wrapping API endpoints directly is insufficient?

### Step 1.2: Study MCP Protocol Documentation

**Action:**
- Use WebFetch to load: `https://modelcontextprotocol.io/llms-full.txt`
- Read the complete MCP specification
- Understand:
  - Tool registration and invocation
  - Input schema requirements (JSON Schema format)
  - Response format (content array with text/image/resource types)
  - Error handling (isError flag in responses)
  - Tool annotations (readOnlyHint, destructiveHint, etc.)
  - Transport options (stdio, SSE, HTTP)

**Key Sections to Focus On:**
- Tools overview and definition structure
- Tool implementation patterns
- Error handling standards
- Security considerations
- Best practices

**Time:** 30-45 minutes

**Checkpoint:** Do you understand how tools are registered and how responses are formatted?

### Step 1.3: Study Framework Documentation

Choose your implementation language and load the corresponding SDK documentation.

#### For Python (FastMCP):

**Action:**
- Use WebFetch to load: `https://raw.githubusercontent.com/modelcontextprotocol/python-sdk/main/README.md`
- Also load: [python_mcp_server.md](./python_mcp_server.md)

**Focus On:**
- FastMCP initialization: `mcp = FastMCP("service_mcp")`
- Tool decorator: `@mcp.tool(name, annotations)`
- Pydantic model integration for input validation
- Context injection for logging/progress
- Resource registration (if needed)
- Lifespan management
- Transport configuration

**Time:** 30-40 minutes

#### For Node/TypeScript (MCP SDK):

**Action:**
- Use WebFetch to load: `https://raw.githubusercontent.com/modelcontextprotocol/typescript-sdk/main/README.md`
- Also load: [node_mcp_server.md](./node_mcp_server.md)

**Focus On:**
- McpServer initialization
- `server.registerTool` pattern
- Zod schema integration
- StdioServerTransport setup
- Type safety requirements
- Build configuration

**Time:** 30-40 minutes

**Checkpoint:** Can you write a skeleton server with one simple tool?

### Step 1.4: Exhaustively Study API Documentation

**This is the most important research step.** Incomplete API knowledge leads to missing critical tools.

**Action:**
- Read **ALL** available API documentation for the service you're integrating
- Use WebSearch and WebFetch to gather comprehensive information
- Parallelize this step if there are multiple documentation sources

**What to Document:**

#### Authentication & Authorization
- Authentication methods (API keys, OAuth, tokens)
- How to obtain credentials
- Where credentials are passed (headers, query params)
- Permission requirements for different operations
- Rate limiting rules and headers

#### Available Endpoints
- List ALL endpoints and their purposes
- HTTP methods (GET, POST, PUT, DELETE, PATCH)
- URL patterns and path parameters
- Query parameters and their constraints
- Request body schemas
- Response schemas and status codes

#### Data Models
- Key resources (users, projects, tasks, messages, etc.)
- Field names, types, and constraints
- Required vs optional fields
- Relationships between resources
- ID formats and patterns

#### Pagination & Filtering
- Pagination mechanisms (offset/limit, cursor-based, page numbers)
- Default page sizes and maximum limits
- Filter/search capabilities
- Sorting options

#### Error Responses
- Error formats and status codes
- Common error scenarios
- Retry strategies
- Rate limit error handling

**Time:** 1-2 hours (varies by API complexity)

**Checkpoint:** Can you list the 10 most important endpoints and explain what each does?

### Step 1.5: Create a Comprehensive Implementation Plan

Now synthesize all research into a concrete plan.

#### Plan Component 1: Tool Selection

**Identify High-Value Tools:**
- Which endpoints enable the most common workflows?
- What would an agent most frequently need to accomplish?
- Which operations naturally combine into workflow tools?

**Prioritize by Impact:**
1. Search/find tools (agents need to discover resources)
2. Read/get tools (agents need to retrieve information)
3. Create/update tools (agents need to modify state)
4. Workflow tools (combinations of the above)

**Example Tool List:**
```
High Priority (Implement First):
- search_users(query, team, status) - Find users by various criteria
- get_project_status(project_name) - Overview of project metrics
- list_recent_activity(project, limit) - What's been happening

Medium Priority:
- create_task(project, title, assignee, due_date)
- update_task_status(task_id, status, note)
- assign_task(task_id, user)

Low Priority (Nice to Have):
- export_project_data(project, format)
- generate_report(project, date_range)
```

#### Plan Component 2: Shared Utilities and Helpers

**API Request Infrastructure:**
```python
# Python example
async def _make_api_request(endpoint, method="GET", **kwargs):
    """Centralized API calling with auth, timeouts, error handling"""

def _handle_api_error(error):
    """Convert API errors to actionable error messages"""

async def _paginate_results(endpoint, params, max_items):
    """Handle pagination across multiple API calls"""
```

**Response Formatting:**
```python
def _format_as_markdown(data):
    """Convert JSON data to human-readable markdown"""

def _format_as_json(data):
    """Convert to structured JSON with consistent schema"""

def _truncate_if_needed(response):
    """Enforce CHARACTER_LIMIT with helpful truncation message"""
```

**Common Operations:**
```python
async def _resolve_user_id(identifier):
    """Accept name or ID, return ID (for flexible inputs)"""

async def _validate_project_exists(project_name):
    """Check project exists, return helpful error if not"""
```

#### Plan Component 3: Input/Output Design

**For Each Tool, Define:**

**Input Parameters:**
- Required vs optional parameters
- Parameter types and constraints (min/max, patterns, enums)
- Validation rules (Pydantic models or Zod schemas)
- Examples of valid inputs
- Default values

**Example Input Design:**
```python
class SearchUsersInput(BaseModel):
    query: str = Field(..., min_length=2, max_length=200,
                      description="Search string (e.g., 'john', 'marketing', 'active')")
    team: Optional[str] = Field(None,
                               description="Filter by team name")
    status: Optional[str] = Field(None,
                                 description="Filter by status: 'active', 'inactive', 'pending'")
    limit: int = Field(20, ge=1, le=100,
                      description="Max results (1-100)")
    offset: int = Field(0, ge=0,
                       description="Skip N results for pagination")
    response_format: ResponseFormat = Field(ResponseFormat.MARKDOWN,
                                          description="'markdown' or 'json'")
```

**Output Formats:**
- Markdown format (default, human-readable)
- JSON format (optional, machine-readable)
- Character limit strategy (typically 25,000 chars)
- Truncation handling
- Pagination metadata

**Example Output Design:**
```markdown
Markdown format:
# Search Results: "marketing"

Found 47 users (showing 20)

## John Doe (U123)
- Email: john@example.com
- Team: Marketing
- Status: Active

JSON format:
{
  "total": 47,
  "count": 20,
  "offset": 0,
  "users": [
    {"id": "U123", "name": "John Doe", "email": "john@example.com", ...}
  ],
  "has_more": true,
  "next_offset": 20
}
```

#### Plan Component 4: Error Handling Strategy

**For Each Potential Error:**

**Authentication Errors (401):**
```
Error: Invalid API credentials.
Check that EXAMPLE_API_KEY environment variable is set correctly.
Visit https://example.com/settings/api to generate a new key.
```

**Authorization Errors (403):**
```
Error: Permission denied accessing project 'website-redesign'.
You may not have access to this project. Use list_projects() to see
available projects, or contact your admin to request access.
```

**Not Found Errors (404):**
```
Error: Project 'webiste-redesign' not found.
Did you mean 'website-redesign'? Use list_projects() to see exact names.
```

**Rate Limit Errors (429):**
```
Error: Rate limit exceeded (max 100 requests/minute).
Wait 60 seconds before retrying, or reduce request frequency.
```

**Validation Errors:**
```
Error: Date format invalid. Expected YYYY-MM-DD (e.g., '2024-01-15'),
received '01/15/2024'. Please use ISO date format.
```

**Truncation Warnings:**
```
Response truncated from 1,247 items to 50 items (25,000 character limit).
To see more results:
- Add filters: use team='marketing' or status='active'
- Use pagination: set offset=50 to see next page
- Use JSON format: response_format='json' is more compact
```

**Plan Error Handling Code:**
- Create consistent error formatter function
- Map HTTP status codes to actionable messages
- Include suggested next steps in every error
- Reference related tools when helpful

#### Plan Component 5: Document Loading Strategy

**Create a Loading Sequence:**

```
Phase 1.1: Load design_principles.md
  ↓
Phase 1.2: Load MCP protocol docs
  ↓
Phase 1.3: Load Python/TypeScript SDK docs + language guide
  ↓
Phase 1.4: Fetch API documentation exhaustively
  ↓
Phase 1.5: Create this plan
  ↓
Phase 2.1: Begin implementation
  ↓
Phase 2.4: Load mcp_best_practices.md for validation
  ↓
Phase 3.3: Load language-specific checklist
  ↓
Phase 4: Load evaluation.md
```

**Time for Entire Planning Phase:** 3-4 hours

**Deliverable:** Written implementation plan documenting:
- 5-15 high-priority tools with descriptions
- Shared utility functions needed
- Input/output schemas for each tool
- Error handling strategy
- Example tool calls and responses

---

## Phase 2: Implementation (30% of effort)

Now execute your plan systematically.

### Step 2.1: Set Up Project Structure

#### For Python (FastMCP):

**Single File Structure (Simple Servers):**
```
service_mcp.py              # All code in one file
requirements.txt            # Dependencies
README.md                   # Usage instructions
evaluation.xml              # Your evaluations
```

**Multi-File Structure (Complex Servers):**
```
service_mcp/
├── __init__.py
├── server.py              # Main FastMCP initialization
├── tools/
│   ├── search_tools.py    # Search/find operations
│   ├── crud_tools.py      # Create/read/update/delete
│   └── workflow_tools.py  # Combined workflow operations
├── models.py              # Pydantic input models
├── utils.py               # Shared utilities
├── constants.py           # API_URL, CHARACTER_LIMIT, etc.
└── requirements.txt
```

**Initialize:**
```python
# service_mcp.py or server.py
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("service_mcp")

# Constants at module level
API_BASE_URL = "https://api.example.com/v1"
CHARACTER_LIMIT = 25000

if __name__ == "__main__":
    mcp.run()
```

**Dependencies (requirements.txt):**
```
mcp>=1.0.0
pydantic>=2.0.0
httpx>=0.24.0
```

#### For Node/TypeScript (MCP SDK):

**Project Structure:**
```
service-mcp-server/
├── package.json
├── tsconfig.json
├── README.md
├── src/
│   ├── index.ts           # Main entry point
│   ├── types.ts           # TypeScript interfaces
│   ├── tools/             # Tool implementations
│   ├── services/          # API clients
│   ├── schemas/           # Zod schemas
│   └── constants.ts       # Configuration
└── dist/                  # Compiled JavaScript
```

**Initialize (package.json):**
```json
{
  "name": "service-mcp-server",
  "version": "1.0.0",
  "type": "module",
  "main": "dist/index.js",
  "scripts": {
    "build": "tsc",
    "start": "node dist/index.js"
  },
  "dependencies": {
    "@modelcontextprotocol/sdk": "^1.6.1",
    "axios": "^1.7.9",
    "zod": "^3.23.8"
  }
}
```

**Initialize (src/index.ts):**
```typescript
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";

const server = new McpServer({
  name: "service-mcp-server",
  version: "1.0.0"
});

// Constants
export const API_BASE_URL = "https://api.example.com/v1";
export const CHARACTER_LIMIT = 25000;

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("Service MCP server running via stdio");
}

main().catch(console.error);
```

### Step 2.2: Implement Core Infrastructure First

**DO NOT start with tools.** Build shared utilities first.

#### Shared API Request Function

**Python:**
```python
async def _make_api_request(
    endpoint: str,
    method: str = "GET",
    data: Optional[dict] = None,
    params: Optional[dict] = None
) -> dict:
    """Centralized API calling with auth, timeouts, retries."""
    async with httpx.AsyncClient() as client:
        response = await client.request(
            method,
            f"{API_BASE_URL}/{endpoint}",
            json=data,
            params=params,
            headers={
                "Authorization": f"Bearer {os.getenv('EXAMPLE_API_KEY')}",
                "Content-Type": "application/json"
            },
            timeout=30.0
        )
        response.raise_for_status()
        return response.json()
```

**TypeScript:**
```typescript
async function makeApiRequest<T>(
  endpoint: string,
  method: "GET" | "POST" | "PUT" | "DELETE" = "GET",
  data?: any,
  params?: any
): Promise<T> {
  const response = await axios({
    method,
    url: `${API_BASE_URL}/${endpoint}`,
    data,
    params,
    headers: {
      "Authorization": `Bearer ${process.env.EXAMPLE_API_KEY}`,
      "Content-Type": "application/json"
    },
    timeout: 30000
  });
  return response.data;
}
```

#### Error Handler

**Python:**
```python
def _handle_api_error(e: Exception) -> str:
    """Convert exceptions to actionable error messages."""
    if isinstance(e, httpx.HTTPStatusError):
        status = e.response.status_code
        if status == 401:
            return "Error: Invalid API credentials. Check EXAMPLE_API_KEY environment variable."
        elif status == 403:
            return "Error: Permission denied. You don't have access to this resource."
        elif status == 404:
            return "Error: Resource not found. Check the ID is correct."
        elif status == 429:
            return "Error: Rate limit exceeded. Wait before making more requests."
        return f"Error: API request failed with status {status}"
    elif isinstance(e, httpx.TimeoutException):
        return "Error: Request timed out. Try again or check network connection."
    return f"Error: Unexpected error: {type(e).__name__}"
```

#### Response Formatters

**Python:**
```python
def _format_as_markdown(data: list, title: str) -> str:
    """Format list of items as readable markdown."""
    lines = [f"# {title}", ""]
    for item in data:
        lines.append(f"## {item['name']} ({item['id']})")
        lines.append(f"- **Status**: {item['status']}")
        lines.append("")
    return "\n".join(lines)

def _format_as_json(data: dict) -> str:
    """Format as pretty-printed JSON."""
    return json.dumps(data, indent=2)

def _check_character_limit(text: str) -> str:
    """Enforce character limit with truncation message."""
    if len(text) > CHARACTER_LIMIT:
        truncated = text[:CHARACTER_LIMIT]
        truncated += "\n\n[Response truncated at 25,000 character limit]"
        return truncated
    return text
```

**Time:** 1-2 hours to build solid infrastructure

### Step 2.3: Implement Tools Systematically

For each tool in your plan, follow this pattern:

#### Step A: Define Input Schema

**Python (Pydantic):**
```python
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum

class ResponseFormat(str, Enum):
    MARKDOWN = "markdown"
    JSON = "json"

class SearchUsersInput(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )

    query: str = Field(
        ...,
        description="Search string to match (e.g., 'john', 'team:marketing')",
        min_length=2,
        max_length=200
    )
    limit: int = Field(
        default=20,
        description="Maximum results to return (1-100)",
        ge=1,
        le=100
    )
    offset: int = Field(
        default=0,
        description="Results to skip for pagination",
        ge=0
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format: 'markdown' or 'json'"
    )
```

**TypeScript (Zod):**
```typescript
import { z } from "zod";

enum ResponseFormat {
  MARKDOWN = "markdown",
  JSON = "json"
}

const SearchUsersInputSchema = z.object({
  query: z.string()
    .min(2, "Query must be at least 2 characters")
    .max(200, "Query too long")
    .describe("Search string to match"),
  limit: z.number()
    .int()
    .min(1)
    .max(100)
    .default(20)
    .describe("Maximum results (1-100)"),
  offset: z.number()
    .int()
    .min(0)
    .default(0)
    .describe("Results to skip for pagination"),
  response_format: z.nativeEnum(ResponseFormat)
    .default(ResponseFormat.MARKDOWN)
    .describe("Output format")
}).strict();

type SearchUsersInput = z.infer<typeof SearchUsersInputSchema>;
```

#### Step B: Write Comprehensive Tool Description

**Key Elements:**
1. One-line summary
2. Detailed explanation of functionality
3. Parameter documentation with examples
4. Return value schema
5. Usage examples (when to use, when NOT to use)
6. Error handling documentation

**Example:**
```python
@mcp.tool(
    name="example_search_users",
    annotations={
        "title": "Search Example Users",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
async def example_search_users(params: SearchUsersInput) -> str:
    """Search for users in the Example system by name, email, or team.

    This tool searches across all user profiles, supporting partial matches
    and flexible filtering. It does NOT create or modify users - only searches.

    Args:
        params (SearchUsersInput): Search parameters including:
            - query (str): Search string (e.g., "john", "team:marketing")
            - limit (int): Max results 1-100 (default: 20)
            - offset (int): Pagination offset (default: 0)
            - response_format: 'markdown' or 'json' (default: 'markdown')

    Returns:
        str: Search results formatted as markdown or JSON

        JSON format schema:
        {
            "total": int,              # Total matches found
            "count": int,              # Results in this response
            "offset": int,             # Current offset
            "users": [
                {
                    "id": str,         # User ID (e.g., "U123")
                    "name": str,       # Full name
                    "email": str,      # Email address
                    "team": str,       # Team name (optional)
                    "status": str      # 'active', 'inactive', 'pending'
                }
            ],
            "has_more": bool,          # More results available
            "next_offset": int         # Offset for next page
        }

    Examples:
        - Find marketing team: params with query="team:marketing"
        - Find by name: params with query="john"
        - Get detailed data: params with response_format="json"

    Don't use when:
        - You need to CREATE a user -> use example_create_user instead
        - You have a user ID and need full details -> use example_get_user

    Error Handling:
        - "No users found": Returns empty results with suggestion to broaden search
        - "Rate limit exceeded": Advises waiting before retry
        - "Invalid query": Provides example of valid query format
    """
```

#### Step C: Implement Tool Logic

**Pattern:**
```python
async def example_search_users(params: SearchUsersInput) -> str:
    try:
        # 1. Make API request using shared utilities
        data = await _make_api_request(
            "users/search",
            params={"q": params.query, "limit": params.limit, "offset": params.offset}
        )

        users = data.get("users", [])
        total = data.get("total", 0)

        # 2. Handle empty results
        if not users:
            return f"No users found matching '{params.query}'. Try a broader search term."

        # 3. Format response based on requested format
        if params.response_format == ResponseFormat.MARKDOWN:
            result = _format_users_markdown(users, total, params.query)
        else:
            result = _format_users_json(users, total, params.offset)

        # 4. Enforce character limit
        result = _check_character_limit(result)

        return result

    except Exception as e:
        # 5. Convert errors to actionable messages
        return _handle_api_error(e)
```

#### Step D: Add Tool Annotations

Always include these annotations:

```python
annotations={
    "title": "Human-Readable Tool Name",
    "readOnlyHint": True/False,      # Does it modify state?
    "destructiveHint": True/False,    # Does it delete/destroy data?
    "idempotentHint": True/False,     # Same call twice = same result?
    "openWorldHint": True/False       # Does it interact externally?
}
```

**Examples:**
- Search tool: readOnly=True, destructive=False, idempotent=True, openWorld=True
- Create tool: readOnly=False, destructive=False, idempotent=False, openWorld=True
- Delete tool: readOnly=False, destructive=True, idempotent=True, openWorld=True

**Repeat for Each Tool in Your Plan**

**Time:** 30-60 minutes per tool (5-10 tools = 3-6 hours)

### Step 2.4: Follow Language-Specific Best Practices

Before finalizing implementation:

#### For Python:
- Load [python_mcp_server.md](./python_mcp_server.md)
- Verify using Pydantic v2 with `model_config`
- Check all async/await patterns
- Confirm type hints throughout
- Review quality checklist

#### For TypeScript:
- Load [node_mcp_server.md](./node_mcp_server.md)
- Verify Zod schemas use `.strict()`
- Check TypeScript strict mode enabled
- Confirm no `any` types
- Review quality checklist
- Run `npm run build` to verify

**Time:** 1 hour

---

## Phase 3: Review and Refine (15% of effort)

### Step 3.1: Code Quality Review

**DRY Principle (Don't Repeat Yourself):**
- [ ] No duplicated code between tools
- [ ] Common operations extracted to utility functions
- [ ] API request logic centralized
- [ ] Error handling consistent

**Composability:**
- [ ] Shared utilities can be combined flexibly
- [ ] Tools use shared formatters
- [ ] Validation logic is reusable

**Consistency:**
- [ ] Similar operations return similar formats
- [ ] Tool names follow same patterns
- [ ] Error messages have consistent structure
- [ ] Pagination handled identically across tools

**Error Handling:**
- [ ] All external API calls wrapped in try/catch
- [ ] Every error returns actionable message
- [ ] Timeout scenarios handled
- [ ] Authentication errors caught

**Type Safety:**
- [ ] Python: Type hints on all functions
- [ ] TypeScript: No `any` types
- [ ] Input validation via Pydantic/Zod
- [ ] Output types documented

**Documentation:**
- [ ] Every tool has comprehensive docstring
- [ ] Return schemas fully documented
- [ ] Usage examples provided
- [ ] Error scenarios explained

**Time:** 1-2 hours

### Step 3.2: Test and Build

**IMPORTANT:** MCP servers are long-running processes. Never run them directly:
- ❌ `python server.py` - WILL HANG FOREVER
- ❌ `node dist/index.js` - WILL HANG FOREVER

**Safe Testing Options:**

#### Option 1: Use Evaluation Harness (Recommended)
```bash
python scripts/evaluation.py \
  -t stdio \
  -c python \
  -a your_server.py \
  evaluation.xml
```
The harness manages the server process for you.

#### Option 2: Run in tmux
```bash
# Terminal 1
tmux new -s mcp-server
python your_server.py
# Detach with Ctrl+B then D

# Terminal 2
# Test with evaluation harness or manual testing
```

#### For Python:

**Verify Syntax:**
```bash
python -m py_compile your_server.py
```

**Check Imports:**
Read through the file to verify:
- All imports are valid
- Pydantic models defined before use
- No circular dependencies

**Test Pattern:**
```bash
# In tmux or use evaluation harness
timeout 5s python your_server.py
# Should timeout (proving it's listening)
```

#### For TypeScript:

**Build:**
```bash
npm run build
```
**MUST complete without errors.**

**Verify Output:**
```bash
ls dist/index.js  # Must exist
```

**Test Pattern:**
```bash
# In tmux or use evaluation harness
timeout 5s node dist/index.js
# Should timeout (proving it's listening)
```

**Time:** 30 minutes

### Step 3.3: Use Quality Checklist

#### Python Checklist:
Load the "Quality Checklist" section from [python_mcp_server.md](./python_mcp_server.md)

Key items:
- [ ] Server name format: `{service}_mcp`
- [ ] All tools use `@mcp.tool` decorator
- [ ] Pydantic models for all inputs
- [ ] Annotations on all tools
- [ ] Async/await throughout
- [ ] CHARACTER_LIMIT enforced
- [ ] Pagination implemented
- [ ] Shared utilities used

#### TypeScript Checklist:
Load the "Quality Checklist" section from [node_mcp_server.md](./node_mcp_server.md)

Key items:
- [ ] Server name format: `{service}-mcp-server`
- [ ] `npm run build` succeeds
- [ ] dist/index.js exists
- [ ] Zod schemas with `.strict()`
- [ ] TypeScript strict mode
- [ ] No `any` types
- [ ] CHARACTER_LIMIT enforced
- [ ] Pagination implemented

**Time:** 30 minutes

---

## Phase 4: Create Evaluations (15% of effort)

### Step 4.1: Load Evaluation Guide

**Action:**
- Load [evaluation.md](./evaluation.md) completely
- Understand evaluation purpose and requirements

**Key Points:**
- Evaluations test if agents can answer realistic questions
- Questions must be read-only, independent, complex
- Answers must be single verifiable values
- Create 10 questions that require multiple tool calls

### Step 4.2: Understand Evaluation Requirements

**Each Question Must Be:**
- Independent (not dependent on other questions)
- Read-only (no state modifications required)
- Complex (requiring multiple tool calls, potentially dozens)
- Realistic (based on actual use cases)
- Verifiable (single clear answer via string comparison)
- Stable (answer won't change over time)

**Each Answer Must Be:**
- Single value (not a list or complex object)
- Verifiable via direct string comparison
- Human-readable when possible (names over IDs)
- Stable over time (based on historical data)

### Step 4.3: Create Evaluation Process

**Step 1: Tool Inspection**
```python
# List your implemented tools
tools = [
    "example_search_users",
    "example_get_project_status",
    "example_list_recent_activity",
    # ... etc
]

# Understand capabilities
for tool in tools:
    print(f"{tool}: {tool_description}")
```

**Step 2: Content Exploration**
- Use READ-ONLY tools to explore available data
- Identify specific users, projects, tasks for questions
- Find historical data that won't change
- Use `limit=10` to avoid overwhelming context

**Step 3: Generate Questions**
Create 10 questions that:
- Require understanding your API's data
- Test multiple tools working together
- Challenge agents with realistic complexity
- Have stable, verifiable answers

**Example Questions:**
```xml
<qa_pair>
  <question>Find the project that was completed in Q3 2023 and had the highest number of tasks marked as 'critical' priority. What was the project manager's email address?</question>
  <answer>sarah.johnson@example.com</answer>
</qa_pair>

<qa_pair>
  <question>Among all users in the Engineering team who joined before January 2024, which user has closed the most bug reports? Provide their full name.</question>
  <answer>Michael Chen</answer>
</qa_pair>
```

**Step 4: Verify Answers**
- Solve each question yourself using the MCP server tools
- Verify the answer is stable (won't change)
- Confirm answer can be found with available tools
- Adjust questions if too easy or impossible

### Step 4.4: Create evaluation.xml File

```xml
<evaluation>
  <qa_pair>
    <question>Your first question here</question>
    <answer>verifiable answer</answer>
  </qa_pair>
  <qa_pair>
    <question>Your second question here</question>
    <answer>verifiable answer</answer>
  </qa_pair>
  <!-- 8 more qa_pairs -->
</evaluation>
```

### Step 4.5: Run Evaluation

```bash
# Install dependencies
pip install anthropic mcp

# Set API key
export ANTHROPIC_API_KEY=your_key

# Run evaluation
python scripts/evaluation.py \
  -t stdio \
  -c python \
  -a your_server.py \
  -e EXAMPLE_API_KEY=your_api_key \
  -o report.md \
  evaluation.xml
```

**Review Results:**
- Which questions passed/failed?
- What was the agent's feedback on your tools?
- Where did agents struggle?
- What improvements are suggested?

### Step 4.6: Iterate Based on Results

**If Accuracy < 80%:**
- Review failed questions
- Read agent feedback carefully
- Identify patterns in failures
- Improve tools based on feedback
- Re-run evaluations

**Common Improvements:**
- Add better search/filter capabilities
- Improve error messages with examples
- Reduce response verbosity
- Add missing workflow tools
- Improve tool descriptions

**Time:** 2-3 hours

---

## Workflow Decision Tree

```
START: Building MCP Server
  ↓
Have you read design_principles.md?
  No → Read design_principles.md first
  Yes → Continue
  ↓
Have you loaded MCP protocol docs?
  No → Load https://modelcontextprotocol.io/llms-full.txt
  Yes → Continue
  ↓
Have you loaded SDK docs for your language?
  No → Load Python or TypeScript SDK + guide
  Yes → Continue
  ↓
Have you studied ALL API documentation?
  No → Exhaustively research API (1-2 hours)
  Yes → Continue
  ↓
Have you created implementation plan?
  No → Document tools, utilities, I/O, errors
  Yes → Begin Phase 2
  ↓
Have you built shared utilities?
  No → Build API client, error handler, formatters
  Yes → Continue
  ↓
Have you implemented tools with validation?
  No → Implement each tool systematically
  Yes → Continue
  ↓
Does `python server.py` or `npm run build` work?
  No → Fix syntax/build errors
  Yes → Continue
  ↓
Have you reviewed code quality?
  No → Check DRY, composability, consistency
  Yes → Continue
  ↓
Have you created 10 evaluation questions?
  No → Load evaluation.md and create evaluations
  Yes → Continue
  ↓
Does evaluation show 80%+ accuracy?
  No → Iterate on tools based on feedback
  Yes → SUCCESS - Server is ready!
```

---

## Common Pitfalls and Solutions

### Pitfall 1: Starting Implementation Too Early
**Symptom:** Building tools without understanding agent needs
**Solution:** Complete Phase 1 research thoroughly (40% of time)

### Pitfall 2: API Wrapper Mentality
**Symptom:** One tool per API endpoint
**Solution:** Review design_principles.md - build workflow tools

### Pitfall 3: Verbose Responses
**Symptom:** Agents run out of context
**Solution:** Default to concise, offer detailed option, enforce CHARACTER_LIMIT

### Pitfall 4: Generic Error Messages
**Symptom:** Agents get stuck on errors
**Solution:** Every error must include specific next steps

### Pitfall 5: Skipping Evaluations
**Symptom:** Tools seem good but agents fail in practice
**Solution:** Create evaluations in Phase 4, iterate based on results

### Pitfall 6: Running Server Directly
**Symptom:** `python server.py` hangs forever
**Solution:** Use evaluation harness or tmux, never run directly

### Pitfall 7: Incomplete API Research
**Symptom:** Missing important tools
**Solution:** Exhaustively study API docs in Phase 1.4

### Pitfall 8: Duplicated Code
**Symptom:** Similar logic across multiple tools
**Solution:** Extract shared utilities in Phase 2.2

---

## Time Estimates by Phase

**Small Server (5-8 tools):**
- Phase 1: 3-4 hours
- Phase 2: 3-4 hours
- Phase 3: 1-2 hours
- Phase 4: 2-3 hours
- **Total: 9-13 hours**

**Medium Server (10-15 tools):**
- Phase 1: 4-5 hours
- Phase 2: 6-8 hours
- Phase 3: 2-3 hours
- Phase 4: 3-4 hours
- **Total: 15-20 hours**

**Large Server (20+ tools):**
- Phase 1: 5-6 hours
- Phase 2: 10-12 hours
- Phase 3: 3-4 hours
- Phase 4: 4-5 hours
- **Total: 22-27 hours**

---

## Success Criteria

Your MCP server is ready when:

- [ ] All reference documentation has been loaded and studied
- [ ] Implementation plan documents tools, I/O, and error handling
- [ ] Shared utilities are implemented and reused across tools
- [ ] All tools have comprehensive descriptions and examples
- [ ] Input validation uses Pydantic (Python) or Zod (TypeScript)
- [ ] Error messages are actionable with specific guidance
- [ ] CHARACTER_LIMIT is enforced with truncation messages
- [ ] Pagination is implemented where applicable
- [ ] Code follows language-specific best practices
- [ ] Build/syntax check succeeds
- [ ] Quality checklist is complete
- [ ] 10 evaluation questions created
- [ ] Evaluation shows 80%+ agent success rate
- [ ] Agent feedback is positive and specific

---

**Next:** Return to [SKILL.md](../SKILL.md) for navigation to other reference files.
