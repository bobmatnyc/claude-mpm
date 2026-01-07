# Dashboard Event Model Research: Hierarchical Agents Tab

**Research Date**: 2025-12-23
**Objective**: Understand the claude-mpm dashboard event model to build a hierarchical Agents tab showing PM → sub-agents → tool calls → todos
**Status**: Complete

## Executive Summary

The claude-mpm dashboard has a comprehensive event capture system via Socket.IO that can support a hierarchical Agents tab. Key findings:

1. **Agent hierarchy CAN be determined** from existing event data using `session_id`, delegation tracking, and correlation IDs
2. **No explicit parent_id field** - hierarchy must be inferred from event timing and delegation patterns
3. **Rich event metadata** available including agent type, session correlation, tool parameters, and TodoWrite activities
4. **Event correlation infrastructure** already exists for pre/post tool events using `correlation_id`

---

## 1. Event Structure & Available Fields

### Core Event Schema (`ClaudeEvent`)
**File**: `/src/claude_mpm/dashboard-svelte/src/lib/types/events.ts`

```typescript
export interface ClaudeEvent {
  id: string;
  event?: string;              // Socket event name (claude_event, hook_event, etc.)
  type: string;                // Event type (hook, tool_call, etc.)
  timestamp: string | number;
  data: unknown;               // Event-specific payload
  agent?: string;              // ⚠️ NOT consistently populated
  sessionId?: string;          // TypeScript format (camelCase)
  session_id?: string;         // Python format (snake_case)
  subtype?: string;            // Event subtype (pre_tool, post_tool, etc.)
  source?: string;             // Event source identifier
  metadata?: unknown;
  cwd?: string;               // Working directory
  correlation_id?: string;    // For correlating pre/post tool events
}
```

### Event Sources
**File**: `/src/claude_mpm/hooks/claude_hooks/services/connection_manager.py:188-189`

Events are emitted through 6 channels:
- `claude_event` - Claude-specific events
- `hook_event` - Hook lifecycle events
- `cli_event` - CLI command events
- `system_event` - System-level events
- `agent_event` - Agent-specific events
- `build_event` - Build/compilation events

---

## 2. Agent Identification

### How to Identify Which Agent Made a Tool Call

**GOOD NEWS**: Agent type is tracked but NOT in the `agent` field directly. Instead:

1. **For Task (delegation) events**:
   ```typescript
   event.subtype === 'pre_tool'
   event.data.tool_name === 'Task'
   event.data.delegation_details.agent_type  // ✅ Normalized agent name
   event.data.delegation_details.original_agent_type  // Raw input
   ```

2. **For regular tool calls**:
   ```typescript
   // Agent type must be inferred from session_id correlation
   // When pre_tool event is emitted, session_id links to parent delegation
   event.session_id  // Links to SubagentStart event
   ```

3. **Agent Session Tracking**:
   **File**: `/src/claude_mpm/core/agent_session_manager.py:73-99`

   Each agent type gets dedicated sessions:
   ```python
   session_data = {
       "id": session_id,
       "agent_type": agent_type,  # "engineer", "qa", "research", etc.
       "created_at": timestamp,
       "tasks_completed": []
   }
   ```

### Agent Name Normalization
**File**: `/src/claude_mpm/hooks/claude_hooks/event_handlers.py:199-218`

Agent types are normalized to lowercase with hyphens:
- Raw input: `"Research"`, `"Engineer"`, `"QA"`
- Normalized: `"research"`, `"engineer"`, `"qa"`

Known agent types:
- `pm` (Project Manager - root)
- `engineer` (Code implementation)
- `research` (Investigation & analysis)
- `qa` (Testing & quality)
- `documentation` (Docs creation)
- `security` (Security analysis)
- `ops` (Deployment & operations)
- `data_engineer` (Data management)
- `version_control` (Git operations)

---

## 3. Delegation Detection

### How PM Delegates to Sub-Agents

**File**: `/src/claude_mpm/hooks/claude_hooks/event_handlers.py:188-290`

When PM uses the `Task` tool, the system emits:

**1. Pre-Tool Event** (`pre_tool`):
```typescript
{
  subtype: "pre_tool",
  data: {
    tool_name: "Task",
    operation_type: "delegation",
    is_delegation: true,
    delegation_details: {
      agent_type: "research",           // ✅ Target agent
      original_agent_type: "Research",  // Raw input
      prompt: "Research OAuth2 patterns",
      description: "Investigation task",
      task_preview: "Research OAuth2..."  // First 100 chars
    },
    session_id: "parent-session-id",
    correlation_id: "uuid-for-correlation"
  }
}
```

**2. SubagentStart Event** (`subagent_start`):
```typescript
{
  subtype: "subagent_start",
  data: {
    agent_type: "research",
    agent_id: "research_child-session-id",
    session_id: "child-session-id",     // ✅ New session for sub-agent
    prompt: "Research OAuth2 patterns",
    description: "Investigation task",
    timestamp: "2025-12-23T10:00:00Z",
    hook_event_name: "SubagentStart"
  }
}
```

**3. SubagentStop Event** (`subagent_stop`):
**File**: `/src/claude_mpm/hooks/claude_hooks/services/subagent_processor.py:331-374`

```typescript
{
  subtype: "subagent_stop",
  data: {
    agent_type: "research",
    agent_id: "research_child-session-id",
    session_id: "child-session-id",
    reason: "completed" | "error" | "timeout",
    is_successful_completion: boolean,
    is_error_termination: boolean,
    has_results: boolean,
    structured_response?: {
      task_completed: boolean,
      instructions: string,
      results: string,
      files_modified: string[],
      tools_used: string[],
      remember: any,
      MEMORIES: any
    },
    hook_event_name: "SubagentStop"
  }
}
```

### Delegation Request Tracking
**File**: `/src/claude_mpm/hooks/claude_hooks/event_handlers.py:239-246`

The system tracks delegation requests in memory:
```python
delegation_requests[child_session_id] = {
    "agent_type": "research",
    "request": {
        "prompt": "Research OAuth2...",
        "description": "Investigation task"
    },
    "timestamp": "2025-12-23T10:00:00Z"
}
```

This enables correlation between Task pre_tool → SubagentStart → SubagentStop.

---

## 4. TodoWrite Events

### How Todos are Captured

**File**: `/src/claude_mpm/hooks/claude_hooks/tool_analysis.py:89-103`

TodoWrite tool calls emit pre_tool events with:

```typescript
{
  subtype: "pre_tool",
  data: {
    tool_name: "TodoWrite",
    operation_type: "task_management",
    tool_parameters: {
      todo_count: 5,
      todos: [
        {
          content: "Implement OAuth2 flow",
          status: "pending" | "in_progress" | "completed",
          activeForm: "Implementing OAuth2 flow",
          priority?: "high" | "medium" | "low"
        },
        // ...
      ],
      todo_summary: {
        total: 5,
        status_counts: {
          pending: 2,
          in_progress: 1,
          completed: 2
        },
        priority_counts: { high: 1, medium: 3, low: 1 },
        summary: "2 completed, 1 in progress, 2 pending"
      },
      has_in_progress: true,
      has_pending: true,
      has_completed: true,
      priorities: ["high", "medium", "low"]
    },
    session_id: "agent-session-id",
    correlation_id: "uuid"
  }
}
```

**Summary Structure** (from `tool_analysis.py:107-138`):
```python
{
    "total": len(todos),
    "status_counts": {"pending": 0, "in_progress": 0, "completed": 0},
    "priority_counts": {"high": 0, "medium": 0, "low": 0},
    "summary": "2 completed, 1 in progress, 2 pending"
}
```

---

## 5. Parent-Child Relationships

### Current State: NO Explicit Parent Field

**Findings**:
- ❌ No `parent_id` field in `ClaudeEvent` interface
- ❌ No `spawned_by` field in event data
- ✅ **Session IDs can be used to infer hierarchy**
- ✅ **Correlation IDs link pre/post tool events**

### Hierarchy Inference Strategy

**Option 1: Session-Based Hierarchy** (Recommended)
```typescript
interface AgentNode {
  agentType: string;           // "pm", "research", "engineer"
  sessionId: string;           // Unique session identifier
  parentSessionId?: string;    // ⚠️ Must be inferred from delegation tracking
  startTime: string;
  endTime?: string;
  status: "active" | "completed" | "error";
  delegations: AgentNode[];    // Child agents
  toolCalls: Tool[];           // Tool executions
  todos: TodoActivity[];       // TodoWrite calls
}
```

**Inference Algorithm**:
```typescript
// 1. Find all SubagentStart events
const starts = events.filter(e => e.subtype === 'subagent_start');

// 2. For each start, find the preceding Task pre_tool event
starts.forEach(start => {
  const taskDelegation = events.find(e =>
    e.subtype === 'pre_tool' &&
    e.data.tool_name === 'Task' &&
    e.data.delegation_details?.agent_type === start.data.agent_type &&
    e.timestamp < start.timestamp &&
    Math.abs(parseTime(start.timestamp) - parseTime(e.timestamp)) < 5000 // 5s window
  );

  if (taskDelegation) {
    start.data.parentSessionId = taskDelegation.session_id;
  }
});

// 3. Build hierarchy tree
const buildTree = (rootSessionId: string) => {
  const children = starts.filter(s => s.data.parentSessionId === rootSessionId);
  return children.map(child => ({
    ...child,
    delegations: buildTree(child.data.session_id)
  }));
};
```

**Option 2: Timing-Based Inference** (Fallback)
If delegation tracking is unreliable:
```typescript
// Assume parent-child relationship if:
// 1. Child SubagentStart occurs shortly after parent Task pre_tool (< 5s)
// 2. Agent types match
// 3. No other delegation in between
```

**Option 3: Backend Enhancement** (Future)
Add `parent_session_id` field to SubagentStart event in backend:
```python
# In event_handlers.py, _handle_task_delegation():
subagent_start_data = {
    "agent_type": agent_type,
    "agent_id": f"{agent_type}_{session_id}",
    "session_id": session_id,  # Child session
    "parent_session_id": parent_session_id,  # ✅ NEW FIELD
    # ...
}
```

---

## 6. Tool Call Correlation

### How Tool Events are Linked

**File**: `/src/claude_mpm/dashboard-svelte/src/lib/utils/event-correlation.ts`

The system uses `correlation_id` to pair pre/post tool events:

```typescript
export function correlateToolEvents(events: StreamEvent[]): Map<
  string,
  { pre: StreamEvent; post?: StreamEvent }
> {
  const correlations = new Map();

  for (const event of events) {
    const correlationId = event.data.correlation_id;

    if (event.event === 'pre-tool') {
      correlations.set(correlationId, { pre: event });
    } else if (event.event === 'post-tool') {
      const existing = correlations.get(correlationId);
      correlations.set(correlationId, { ...existing, post: event });
    }
  }

  return correlations;
}
```

**Tool Type** interface:
**File**: `/src/claude_mpm/dashboard-svelte/src/lib/types/events.ts:23-32`

```typescript
export interface Tool {
  id: string;                   // correlation_id
  toolName: string;             // "Bash", "Read", "Task", "TodoWrite"
  operation: string;            // Human-readable description
  status: 'pending' | 'success' | 'error';
  duration: number | null;      // Milliseconds (post_time - pre_time)
  preToolEvent: ClaudeEvent;
  postToolEvent: ClaudeEvent | null;
  timestamp: string | number;
}
```

**Duration Calculation**:
**File**: `/src/claude_mpm/dashboard-svelte/src/lib/stores/tools.svelte.ts:66-73`

```typescript
const preTime = new Date(preEvent.timestamp).getTime();
const postTime = new Date(postEvent.timestamp).getTime();
duration = postTime - preTime;  // milliseconds
```

---

## 7. Existing Dashboard Components

### ToolsView Component
**File**: `/src/claude_mpm/dashboard-svelte/src/lib/components/ToolsView.svelte`

**Features**:
- Displays correlated tool executions (pre/post pairs)
- Filters by stream/session ID
- Shows tool name, operation, status, duration
- Auto-scrolls to newest tools
- Keyboard navigation (arrow keys)

**Tool Extraction**:
```typescript
function extractOperation(toolName: string, data: Record<string, unknown>): string {
  switch (toolName) {
    case 'Bash':
      return data.description || data.command || 'No command';
    case 'Read':
      return `Read ${data.file_path}`;
    case 'Task':  // ✅ Delegation detected here
      return `Delegate to ${data.delegation_details?.agent_type}`;
    case 'TodoWrite':  // ✅ Todo activity
      return `Update todos (${data.tool_parameters?.todo_count} items)`;
    // ...
  }
}
```

### EventStream Component
**File**: `/src/claude_mpm/dashboard-svelte/src/lib/components/EventStream.svelte`

**Features**:
- Displays all events in chronological order
- Filters by activity (subtype)
- Shows event type, source, activity, agent, timestamp
- Calculates durations for correlated events
- Color-coded by event type

**Agent Name Extraction**:
```typescript
function getAgentName(event: ClaudeEvent): string {
  // Check for user-related events
  if (event.subtype === 'user_prompt' ||
      event.subtype === 'UserPromptSubmit') {
    return 'user';
  }

  // Extract from tool_name or agent_type
  const data = event.data as Record<string, unknown>;
  return data.tool_name || data.agent_type || '-';
}
```

**Duration Calculation** (for correlated events):
```typescript
function getDuration(event: ClaudeEvent): string | null {
  if (event.subtype !== 'post_tool' || !event.correlation_id) {
    return null;
  }

  const preEvent = allEvents.find(
    e => e.correlation_id === event.correlation_id &&
         e.subtype === 'pre_tool'
  );

  if (!preEvent) return null;

  const ms = new Date(event.timestamp).getTime() -
             new Date(preEvent.timestamp).getTime();

  // Format: "123ms", "1.23s", "2m 30s"
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(2)}s`;
  const minutes = Math.floor(ms / 60000);
  const seconds = ((ms % 60000) / 1000).toFixed(0);
  return `${minutes}m ${seconds}s`;
}
```

---

## 8. Recommended Data Model for Agents Tab

### AgentHierarchy Data Structure

```typescript
/**
 * Represents a single agent in the hierarchy tree
 */
interface AgentNode {
  // Identity
  agentType: string;              // "pm", "research", "engineer", etc.
  agentId: string;                // "research_abc123..."
  sessionId: string;              // Unique session identifier

  // Hierarchy
  parentSessionId?: string;       // Session ID of parent agent (PM has none)
  depth: number;                  // 0 for PM, 1 for direct children, etc.

  // Lifecycle
  startTime: string;              // SubagentStart timestamp
  endTime?: string;               // SubagentStop timestamp
  status: 'active' | 'completed' | 'error' | 'timeout';

  // Task Context
  prompt: string;                 // Task prompt from delegation
  description: string;            // Task description
  reason?: string;                // Stop reason (from SubagentStop)

  // Results
  hasResults: boolean;            // Whether agent produced results
  structuredResponse?: {          // From SubagentStop
    task_completed: boolean;
    instructions: string;
    results: string;
    files_modified: string[];
    tools_used: string[];
  };

  // Activity Tracking
  delegations: AgentNode[];       // Child agents spawned
  toolCalls: AgentToolCall[];     // Tools executed by this agent
  todos: AgentTodoActivity[];     // TodoWrite calls by this agent

  // Metrics
  toolCount: number;              // Total tools executed
  todoCount: number;              // Total todo updates
  duration?: number;              // Total execution time (ms)
}

/**
 * Tool call made by an agent
 */
interface AgentToolCall {
  id: string;                     // correlation_id
  toolName: string;               // "Bash", "Read", "Edit", etc.
  operation: string;              // Human-readable description
  status: 'pending' | 'success' | 'error';
  duration: number | null;        // Execution time (ms)
  timestamp: string;

  // Tool-specific data
  parameters?: Record<string, unknown>;  // From tool_parameters
  results?: unknown;              // From post_tool data

  // Special handling
  isDelegation: boolean;          // true if toolName === "Task"
  isTodoWrite: boolean;           // true if toolName === "TodoWrite"
}

/**
 * TodoWrite activity by an agent
 */
interface AgentTodoActivity {
  id: string;                     // correlation_id
  timestamp: string;
  todoCount: number;              // Number of todos in this update
  todos: TodoItem[];              // Full todo list
  summary: {
    total: number;
    status_counts: {
      pending: number;
      in_progress: number;
      completed: number;
    };
    priority_counts: {
      high: number;
      medium: number;
      low: number;
    };
    summary: string;              // "2 completed, 1 in progress, 2 pending"
  };
}

interface TodoItem {
  content: string;
  status: 'pending' | 'in_progress' | 'completed';
  activeForm: string;
  priority?: 'high' | 'medium' | 'low';
}

/**
 * Complete hierarchy tree with metadata
 */
interface AgentHierarchy {
  rootAgent: AgentNode;           // PM agent (root)
  allAgents: Map<string, AgentNode>;  // sessionId -> agent lookup
  activeAgents: AgentNode[];      // Currently running agents
  completedAgents: AgentNode[];   // Finished agents
  erroredAgents: AgentNode[];     // Failed agents

  // Global metrics
  totalAgents: number;
  totalToolCalls: number;
  totalTodos: number;
  totalDuration: number;          // Sum of all agent durations
}
```

### Data Builder Algorithm

```typescript
/**
 * Build agent hierarchy from event stream
 */
function buildAgentHierarchy(events: ClaudeEvent[]): AgentHierarchy {
  const allAgents = new Map<string, AgentNode>();

  // Step 1: Extract all SubagentStart events → Create agent nodes
  const startEvents = events.filter(e => e.subtype === 'subagent_start');
  startEvents.forEach(event => {
    const data = event.data as any;
    const agent: AgentNode = {
      agentType: data.agent_type,
      agentId: data.agent_id,
      sessionId: data.session_id,
      depth: 0,  // Will calculate later
      startTime: event.timestamp,
      status: 'active',
      prompt: data.prompt || '',
      description: data.description || '',
      delegations: [],
      toolCalls: [],
      todos: [],
      toolCount: 0,
      todoCount: 0,
      hasResults: false
    };
    allAgents.set(agent.sessionId, agent);
  });

  // Step 2: Find parent-child relationships from Task delegations
  const taskDelegations = events.filter(e =>
    e.subtype === 'pre_tool' &&
    e.data?.tool_name === 'Task'
  );

  taskDelegations.forEach(taskEvent => {
    const parentSessionId = taskEvent.session_id;
    const delegationDetails = taskEvent.data?.delegation_details;

    if (!delegationDetails) return;

    // Find child agent that matches this delegation
    const childAgent = Array.from(allAgents.values()).find(agent =>
      agent.agentType === delegationDetails.agent_type &&
      agent.startTime >= taskEvent.timestamp &&
      // Within 5 second window
      (new Date(agent.startTime).getTime() -
       new Date(taskEvent.timestamp).getTime()) < 5000
    );

    if (childAgent) {
      childAgent.parentSessionId = parentSessionId;

      // Add to parent's delegations
      const parentAgent = allAgents.get(parentSessionId);
      if (parentAgent) {
        parentAgent.delegations.push(childAgent);
      }
    }
  });

  // Step 3: Calculate depth for each agent
  function calculateDepth(agent: AgentNode, depth: number = 0): void {
    agent.depth = depth;
    agent.delegations.forEach(child => calculateDepth(child, depth + 1));
  }

  const rootAgent = Array.from(allAgents.values()).find(a => !a.parentSessionId);
  if (rootAgent) {
    calculateDepth(rootAgent);
  }

  // Step 4: Populate tool calls for each agent
  const toolEvents = events.filter(e => e.subtype === 'pre_tool');
  toolEvents.forEach(event => {
    const sessionId = event.session_id;
    const agent = allAgents.get(sessionId);

    if (!agent) return;

    const toolName = event.data?.tool_name;
    const correlationId = event.data?.correlation_id;

    // Find matching post_tool event
    const postEvent = events.find(e =>
      e.subtype === 'post_tool' &&
      e.data?.correlation_id === correlationId
    );

    const toolCall: AgentToolCall = {
      id: correlationId || event.id,
      toolName: toolName || 'Unknown',
      operation: extractToolOperation(toolName, event.data),
      status: postEvent ? (postEvent.data?.error ? 'error' : 'success') : 'pending',
      duration: postEvent ?
        new Date(postEvent.timestamp).getTime() -
        new Date(event.timestamp).getTime() : null,
      timestamp: event.timestamp,
      parameters: event.data?.tool_parameters,
      results: postEvent?.data,
      isDelegation: toolName === 'Task',
      isTodoWrite: toolName === 'TodoWrite'
    };

    agent.toolCalls.push(toolCall);
    agent.toolCount++;

    // If TodoWrite, extract todo activity
    if (toolName === 'TodoWrite') {
      const todoActivity: AgentTodoActivity = {
        id: correlationId || event.id,
        timestamp: event.timestamp,
        todoCount: event.data?.tool_parameters?.todo_count || 0,
        todos: event.data?.tool_parameters?.todos || [],
        summary: event.data?.tool_parameters?.todo_summary || {}
      };
      agent.todos.push(todoActivity);
      agent.todoCount++;
    }
  });

  // Step 5: Process SubagentStop events
  const stopEvents = events.filter(e => e.subtype === 'subagent_stop');
  stopEvents.forEach(event => {
    const sessionId = event.data?.session_id;
    const agent = allAgents.get(sessionId);

    if (!agent) return;

    agent.endTime = event.timestamp;
    agent.reason = event.data?.reason;
    agent.hasResults = event.data?.has_results || false;
    agent.structuredResponse = event.data?.structured_response;

    // Determine final status
    if (event.data?.is_successful_completion) {
      agent.status = 'completed';
    } else if (event.data?.is_error_termination) {
      agent.status = 'error';
    } else if (event.data?.reason === 'timeout') {
      agent.status = 'timeout';
    }

    // Calculate total duration
    if (agent.endTime) {
      agent.duration =
        new Date(agent.endTime).getTime() -
        new Date(agent.startTime).getTime();
    }
  });

  // Step 6: Build hierarchy structure
  const activeAgents = Array.from(allAgents.values())
    .filter(a => a.status === 'active');
  const completedAgents = Array.from(allAgents.values())
    .filter(a => a.status === 'completed');
  const erroredAgents = Array.from(allAgents.values())
    .filter(a => a.status === 'error' || a.status === 'timeout');

  const totalToolCalls = Array.from(allAgents.values())
    .reduce((sum, a) => sum + a.toolCount, 0);
  const totalTodos = Array.from(allAgents.values())
    .reduce((sum, a) => sum + a.todoCount, 0);
  const totalDuration = Array.from(allAgents.values())
    .reduce((sum, a) => sum + (a.duration || 0), 0);

  return {
    rootAgent: rootAgent!,
    allAgents,
    activeAgents,
    completedAgents,
    erroredAgents,
    totalAgents: allAgents.size,
    totalToolCalls,
    totalTodos,
    totalDuration
  };
}

/**
 * Helper: Extract human-readable operation from tool event
 */
function extractToolOperation(toolName: string, data: any): string {
  const params = data?.tool_parameters;

  switch (toolName) {
    case 'Task':
      return `Delegate to ${params?.agent_type || 'unknown'}`;
    case 'TodoWrite':
      const count = params?.todo_count || 0;
      const summary = params?.todo_summary?.summary || '';
      return `Update todos (${count} items): ${summary}`;
    case 'Bash':
      return params?.command || params?.description || 'Execute command';
    case 'Read':
      return `Read ${params?.file_path || 'file'}`;
    case 'Edit':
      return `Edit ${params?.file_path || 'file'}`;
    case 'Write':
      return `Write ${params?.file_path || 'file'}`;
    default:
      return params?.description || params?.action || 'Tool execution';
  }
}
```

---

## 9. Event Types to Capture for Hierarchy

### Essential Events

| Event Subtype | Purpose | Key Fields |
|---------------|---------|------------|
| `subagent_start` | Agent spawned | `agent_type`, `session_id`, `prompt` |
| `subagent_stop` | Agent completed | `agent_type`, `session_id`, `reason`, `structured_response` |
| `pre_tool` (Task) | Delegation started | `tool_name`, `delegation_details`, `session_id`, `correlation_id` |
| `pre_tool` (TodoWrite) | Todo update | `tool_name`, `tool_parameters.todos`, `session_id`, `correlation_id` |
| `pre_tool` (other) | Tool execution started | `tool_name`, `tool_parameters`, `session_id`, `correlation_id` |
| `post_tool` | Tool execution finished | `correlation_id`, `error`, `results` |

### Event Filtering Strategy

```typescript
// Filter events relevant to agent hierarchy
function filterHierarchyEvents(events: ClaudeEvent[]): ClaudeEvent[] {
  return events.filter(event => {
    // Include all agent lifecycle events
    if (event.subtype === 'subagent_start' ||
        event.subtype === 'subagent_stop') {
      return true;
    }

    // Include all tool events (for activity tracking)
    if (event.subtype === 'pre_tool' ||
        event.subtype === 'post_tool') {
      return true;
    }

    // Include user prompts (for PM root context)
    if (event.subtype === 'user_prompt') {
      return true;
    }

    return false;
  });
}
```

---

## 10. Dependencies Between Agents

### Dependency Types

1. **Sequential Dependency** (PM → Engineer → QA)
   - Detected when SubagentStop of one agent triggers SubagentStart of another
   - Example: Engineer completes → PM delegates to QA

2. **Parallel Execution** (PM → [Research, Engineer])
   - Multiple SubagentStart events from same parent around same time
   - No SubagentStop between delegations

3. **Tool Dependency** (Agent A uses Tool → Agent B needs output)
   - Agent B's prompt references files created by Agent A
   - Detected through file path analysis in prompts

### Dependency Detection Algorithm

```typescript
interface AgentDependency {
  fromAgent: string;        // sessionId
  toAgent: string;          // sessionId
  type: 'sequential' | 'parallel' | 'tool_chain';
  trigger?: string;         // What triggered dependency
  confidence: number;       // 0.0 - 1.0
}

function detectDependencies(
  hierarchy: AgentHierarchy
): AgentDependency[] {
  const dependencies: AgentDependency[] = [];

  // Sequential dependencies: parent → child delegations
  hierarchy.allAgents.forEach(agent => {
    if (agent.parentSessionId) {
      dependencies.push({
        fromAgent: agent.parentSessionId,
        toAgent: agent.sessionId,
        type: 'sequential',
        trigger: 'delegation',
        confidence: 1.0
      });
    }
  });

  // Parallel dependencies: siblings delegated close in time
  hierarchy.allAgents.forEach(agent => {
    const siblings = agent.delegations;

    for (let i = 0; i < siblings.length - 1; i++) {
      const siblingA = siblings[i];
      const siblingB = siblings[i + 1];

      const timeDiff = Math.abs(
        new Date(siblingA.startTime).getTime() -
        new Date(siblingB.startTime).getTime()
      );

      // If started within 10 seconds → parallel
      if (timeDiff < 10000) {
        dependencies.push({
          fromAgent: siblingA.sessionId,
          toAgent: siblingB.sessionId,
          type: 'parallel',
          trigger: 'concurrent_delegation',
          confidence: 0.8
        });
      }
    }
  });

  // Tool chain dependencies: file creation → file usage
  hierarchy.allAgents.forEach(agentA => {
    const filesCreated = agentA.toolCalls
      .filter(t => t.toolName === 'Write' || t.toolName === 'Edit')
      .map(t => t.parameters?.file_path)
      .filter(Boolean);

    if (filesCreated.length === 0) return;

    hierarchy.allAgents.forEach(agentB => {
      if (agentA.sessionId === agentB.sessionId) return;
      if (agentB.startTime < agentA.endTime) return; // Must start after

      // Check if B's prompt or tool calls reference A's files
      const referencesFiles = filesCreated.some(file =>
        agentB.prompt.includes(file!) ||
        agentB.toolCalls.some(t =>
          JSON.stringify(t.parameters).includes(file!)
        )
      );

      if (referencesFiles) {
        dependencies.push({
          fromAgent: agentA.sessionId,
          toAgent: agentB.sessionId,
          type: 'tool_chain',
          trigger: 'file_dependency',
          confidence: 0.6
        });
      }
    });
  });

  return dependencies;
}
```

---

## 11. Summary & Recommendations

### ✅ What Works Well

1. **Event Correlation**: Existing `correlation_id` system works perfectly for pre/post tool pairing
2. **Session Tracking**: `session_id` provides reliable agent session identification
3. **Rich Metadata**: Events contain comprehensive data (tool params, delegation details, todos)
4. **Delegation Events**: SubagentStart/Stop events clearly mark agent lifecycle
5. **Todo Tracking**: TodoWrite tool parameters include full todo list with summaries

### ⚠️ Limitations

1. **No Explicit Parent ID**: Must infer parent-child relationships from event timing and delegation
2. **Agent Field Not Used**: The `agent` field in `ClaudeEvent` is not consistently populated
3. **PM Detection**: No explicit "PM started" event - must assume PM is root if no parent
4. **Timing Windows**: Parent-child linking relies on 5-second timing windows (fragile)
5. **Fuzzy Matching**: Session ID correlation requires fuzzy matching fallbacks

### 🎯 Recommended Implementation

**Phase 1: Basic Hierarchy** (1-2 days)
- Build agent tree from SubagentStart/Stop events
- Link agents to tool calls via session_id
- Display PM → sub-agents → tools in tree view
- Show TodoWrite activities per agent

**Phase 2: Enhanced Correlation** (2-3 days)
- Implement timing-based parent inference
- Add delegation tracking for parent-child links
- Calculate agent durations and metrics
- Show agent status (active/completed/error)

**Phase 3: Dependencies & Analysis** (3-4 days)
- Detect sequential/parallel/tool-chain dependencies
- Visualize dependency graph
- Add filtering by agent type, status, time range
- Export hierarchy data for analysis

### 🔧 Backend Enhancements (Optional)

If timing-based inference proves unreliable:

```python
# In event_handlers.py, _handle_task_delegation():
subagent_start_data = {
    # ... existing fields ...
    "parent_session_id": parent_session_id,  # ✅ Add explicit parent link
    "parent_agent_type": parent_agent_type,  # ✅ Add for clarity
}
```

This would eliminate the need for fuzzy matching and timing windows.

---

## 12. References

### Key Files Analyzed

**Frontend (TypeScript/Svelte)**:
- `/src/claude_mpm/dashboard-svelte/src/lib/types/events.ts` - Event type definitions
- `/src/claude_mpm/dashboard-svelte/src/lib/stores/socket.svelte.ts` - Event ingestion
- `/src/claude_mpm/dashboard-svelte/src/lib/stores/tools.svelte.ts` - Tool correlation logic
- `/src/claude_mpm/dashboard-svelte/src/lib/utils/event-correlation.ts` - Correlation utilities
- `/src/claude_mpm/dashboard-svelte/src/lib/components/ToolsView.svelte` - Tool display
- `/src/claude_mpm/dashboard-svelte/src/lib/components/EventStream.svelte` - Event display

**Backend (Python)**:
- `/src/claude_mpm/hooks/claude_hooks/services/connection_manager.py` - Event emission
- `/src/claude_mpm/hooks/claude_hooks/event_handlers.py` - Event processing
- `/src/claude_mpm/hooks/claude_hooks/tool_analysis.py` - Tool parameter extraction
- `/src/claude_mpm/hooks/claude_hooks/services/subagent_processor.py` - SubagentStop handling
- `/src/claude_mpm/core/agent_session_manager.py` - Agent session tracking
- `/src/claude_mpm/services/monitor/event_emitter.py` - Event emitter service

### Event Flow

```
User Prompt → PM Agent
    ↓
PM uses Task tool → pre_tool event (delegation_details)
    ↓
SubagentStart event (child session_id)
    ↓
Child Agent executes tools → pre_tool/post_tool events
    ↓
Child Agent uses TodoWrite → pre_tool (tool_parameters.todos)
    ↓
SubagentStop event (structured_response, reason)
    ↓
PM receives results → continues execution
```

### Socket.IO Event Channels

1. `claude_event` - Claude-specific events
2. `hook_event` - Hook lifecycle events (SubagentStart, SubagentStop)
3. `cli_event` - CLI command events
4. `system_event` - System-level events
5. `agent_event` - Agent-specific events
6. `build_event` - Build/compilation events

### Agent Types Normalized

- `pm` - Project Manager (root)
- `research` - Research Agent
- `engineer` - Engineer Agent
- `qa` - QA Agent
- `documentation` - Documentation Agent
- `security` - Security Agent
- `ops` - Ops Agent
- `data_engineer` - Data Engineer Agent
- `version_control` - Version Control Agent

---

## Appendix A: Example Event Sequences

### Example 1: PM → Research Delegation

```json
// 1. User submits prompt
{
  "subtype": "user_prompt",
  "data": {
    "prompt_text": "Research authentication patterns",
    "session_id": "pm-session-123"
  }
}

// 2. PM decides to delegate
{
  "subtype": "pre_tool",
  "data": {
    "tool_name": "Task",
    "operation_type": "delegation",
    "delegation_details": {
      "agent_type": "research",
      "prompt": "Research OAuth2 authentication patterns",
      "description": "Investigate best practices"
    },
    "session_id": "pm-session-123",
    "correlation_id": "task-uuid-1"
  }
}

// 3. Research agent starts
{
  "subtype": "subagent_start",
  "data": {
    "agent_type": "research",
    "agent_id": "research_child-session-456",
    "session_id": "child-session-456",
    "prompt": "Research OAuth2 authentication patterns",
    "timestamp": "2025-12-23T10:00:05Z"
  }
}

// 4. Research agent uses Grep tool
{
  "subtype": "pre_tool",
  "data": {
    "tool_name": "Grep",
    "tool_parameters": {
      "pattern": "OAuth2",
      "path": "./src"
    },
    "session_id": "child-session-456",
    "correlation_id": "grep-uuid-2"
  }
}

// 5. Grep completes
{
  "subtype": "post_tool",
  "data": {
    "correlation_id": "grep-uuid-2",
    "results": "Found 15 matches..."
  }
}

// 6. Research agent completes
{
  "subtype": "subagent_stop",
  "data": {
    "agent_type": "research",
    "session_id": "child-session-456",
    "reason": "completed",
    "is_successful_completion": true,
    "has_results": true,
    "structured_response": {
      "task_completed": true,
      "results": "OAuth2 patterns analysis complete",
      "files_modified": [],
      "tools_used": ["Grep", "Read"]
    }
  }
}

// 7. PM receives results (implicit post_tool for Task)
{
  "subtype": "post_tool",
  "data": {
    "correlation_id": "task-uuid-1",
    "results": "Research complete"
  }
}
```

### Example 2: Engineer with TodoWrite

```json
// 1. PM delegates to Engineer
{
  "subtype": "pre_tool",
  "data": {
    "tool_name": "Task",
    "delegation_details": {
      "agent_type": "engineer",
      "prompt": "Implement OAuth2 login flow"
    },
    "session_id": "pm-session-123",
    "correlation_id": "task-uuid-3"
  }
}

// 2. Engineer starts
{
  "subtype": "subagent_start",
  "data": {
    "agent_type": "engineer",
    "session_id": "engineer-session-789",
    "prompt": "Implement OAuth2 login flow"
  }
}

// 3. Engineer creates todo list
{
  "subtype": "pre_tool",
  "data": {
    "tool_name": "TodoWrite",
    "tool_parameters": {
      "todo_count": 3,
      "todos": [
        {
          "content": "Create OAuth2 config",
          "status": "in_progress",
          "activeForm": "Creating OAuth2 config",
          "priority": "high"
        },
        {
          "content": "Implement login endpoint",
          "status": "pending",
          "activeForm": "Implementing login endpoint"
        },
        {
          "content": "Add error handling",
          "status": "pending",
          "activeForm": "Adding error handling"
        }
      ],
      "todo_summary": {
        "total": 3,
        "status_counts": {
          "pending": 2,
          "in_progress": 1,
          "completed": 0
        },
        "summary": "1 in progress, 2 pending"
      }
    },
    "session_id": "engineer-session-789",
    "correlation_id": "todo-uuid-4"
  }
}

// 4. TodoWrite completes
{
  "subtype": "post_tool",
  "data": {
    "correlation_id": "todo-uuid-4"
  }
}

// 5. Engineer writes files
{
  "subtype": "pre_tool",
  "data": {
    "tool_name": "Write",
    "tool_parameters": {
      "file_path": "./src/auth/oauth2.py",
      "content_length": 1500
    },
    "session_id": "engineer-session-789",
    "correlation_id": "write-uuid-5"
  }
}

// 6. Write completes
{
  "subtype": "post_tool",
  "data": {
    "correlation_id": "write-uuid-5"
  }
}

// 7. Engineer updates todos (marks first as complete)
{
  "subtype": "pre_tool",
  "data": {
    "tool_name": "TodoWrite",
    "tool_parameters": {
      "todo_count": 3,
      "todos": [
        {
          "content": "Create OAuth2 config",
          "status": "completed",
          "activeForm": "Creating OAuth2 config"
        },
        {
          "content": "Implement login endpoint",
          "status": "in_progress",
          "activeForm": "Implementing login endpoint"
        },
        {
          "content": "Add error handling",
          "status": "pending",
          "activeForm": "Adding error handling"
        }
      ],
      "todo_summary": {
        "summary": "1 completed, 1 in progress, 1 pending"
      }
    },
    "session_id": "engineer-session-789"
  }
}

// 8. Engineer completes
{
  "subtype": "subagent_stop",
  "data": {
    "agent_type": "engineer",
    "session_id": "engineer-session-789",
    "reason": "completed",
    "structured_response": {
      "task_completed": true,
      "files_modified": ["./src/auth/oauth2.py"],
      "tools_used": ["TodoWrite", "Write", "Edit"]
    }
  }
}
```

---

## Appendix B: Hierarchy Visualization Ideas

### Tree View (Recommended)

```
📊 Agent Hierarchy - Session ABC123
────────────────────────────────────────
└─ 👔 PM (pm-session-123) [Completed] ⏱️ 2m 30s
   │
   ├─ 🔍 Research (child-456) [Completed] ⏱️ 45s
   │  ├─ 🔧 Grep: OAuth2 patterns [Success] ⏱️ 120ms
   │  ├─ 📄 Read: ./docs/auth.md [Success] ⏱️ 80ms
   │  └─ 📝 TodoWrite: 2 items [Success] ⏱️ 50ms
   │
   └─ 💻 Engineer (child-789) [Active] ⏱️ 1m 15s...
      ├─ 📝 TodoWrite: 3 items → 1 completed, 1 in progress, 1 pending [Success]
      ├─ ✍️ Write: ./src/auth/oauth2.py [Success] ⏱️ 250ms
      └─ ✏️ Edit: ./src/auth/oauth2.py [Pending]...
```

### Swimlane Timeline

```
Time →
        0s        30s       60s       90s       120s
PM      |━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━|
        │
        └─→ Research |━━━━━━━━━|
                     │ Grep Read TodoWrite
        │
        └─→ Engineer      |━━━━━━━━━━━━━━━━━━━━|
                          │ TodoWrite Write Edit
```

### Dependency Graph

```
    ┌────────┐
    │   PM   │
    └───┬────┘
        │ delegates
        ├────────────┬────────────┐
        ▼            ▼            ▼
    ┌────────┐  ┌────────┐  ┌────────┐
    │Research│  │Engineer│  │   QA   │
    └────┬───┘  └────┬───┘  └────┬───┘
         │           │           │
         │ creates   │           │
         │ files     │ uses      │ tests
         └───────────┼───────────┘
                     │
                     ▼
              (file dependencies)
```

---

**Research Complete**: 2025-12-23
**Next Steps**:
1. Implement `buildAgentHierarchy()` function in dashboard
2. Create `AgentsView.svelte` component with tree visualization
3. Add agent metrics and filtering
4. Consider backend enhancement for explicit parent_session_id
