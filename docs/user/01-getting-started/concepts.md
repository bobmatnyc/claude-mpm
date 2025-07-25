# Core Concepts

Understanding these core concepts will help you use Claude MPM effectively.

## What is Claude MPM?

Claude MPM (Multi-Agent Project Manager) is an **orchestration layer** that sits between you and Claude. Think of it as a smart wrapper that enhances Claude with project management capabilities.

```
You → Claude MPM → Claude
         ↓
    [Enhancement Layer]
    - Ticket extraction
    - Agent delegation  
    - Session logging
    - Memory protection
```

## Key Concepts

### 1. Subprocess Orchestration

Unlike traditional Claude usage, Claude MPM runs Claude as a **subprocess**:

- **Traditional**: You interact directly with Claude
- **Claude MPM**: You interact with Claude MPM, which manages Claude

Benefits:
- Full control over inputs/outputs
- Real-time monitoring and interception
- Dynamic instruction injection
- Process-level resource management

### 2. Framework Injection

Claude MPM automatically injects a comprehensive framework that teaches Claude:
- How to work with tickets
- When to delegate to specialized agents
- How to structure responses
- Project management best practices

This happens transparently - you don't need to manage any framework files.

### 3. Agents

Agents are specialized personas that handle specific types of tasks:

| Agent | Specialization | Triggered By |
|-------|---------------|--------------|
| PM (Project Manager) | Default coordinator | All requests |
| Engineer | Code implementation | "implement", "create", "build" |
| QA | Testing and quality | "test", "verify", "check" |
| Documentation | Docs and guides | "document", "explain" |
| Research | Information gathering | "research", "investigate" |
| Security | Security analysis | "security", "vulnerability" |

### 4. Automatic Ticket Extraction

Claude MPM monitors conversations for ticket patterns:

```
TODO: Implement user authentication
TASK: Refactor database queries  
BUG: Login page shows 404 error
FEATURE: Add dark mode support
```

These are automatically extracted and saved as tickets with:
- Unique IDs (TSK-0001, TSK-0002, etc.)
- Timestamps
- Status tracking
- Priority levels

### 5. Session Management

Every interaction is a **session**:

- **Session Start**: When you run claude-mpm
- **Session Content**: All inputs, outputs, and metadata
- **Session End**: When the command completes
- **Session Log**: Saved to `~/.claude-mpm/sessions/`

### 6. Memory Protection

Claude has context limits. Claude MPM helps by:
- Monitoring context usage
- Warning before limits
- Suggesting context optimization
- Preventing overflow errors

## How It All Works Together

### Example Flow

1. **You type**: 
   ```bash
   claude-mpm run -i "TODO: Create a REST API for user management"
   ```

2. **Claude MPM**:
   - Detects the TODO pattern
   - Creates ticket TSK-0001
   - Injects framework instructions
   - Passes to Claude

3. **Claude (PM Agent)**:
   - Recognizes this needs engineering
   - Delegates to Engineer Agent
   - Provides structured response

4. **Claude MPM**:
   - Captures the response
   - Logs everything
   - Shows you the result

### The Framework

The framework is a set of instructions that teaches Claude:

```markdown
You are working with Claude MPM, which provides:
- Automatic ticket management
- Multi-agent delegation
- Session tracking
- And more...

When you see "TODO:", create a ticket...
When engineering is needed, delegate to Engineer...
```

This is injected automatically - you never see or manage it.

## Orchestration Modes

### 1. Direct Mode
Default interactive mode where Claude handles its own I/O:
```bash
claude-mpm  # Launches Claude directly
```

### 2. Subprocess Mode
Full subprocess control with monitoring:
```bash
claude-mpm run --subprocess -i "prompt"
```

### 3. Non-Interactive Mode
Single command execution:
```bash
claude-mpm run -i "prompt" --non-interactive
```

## Ticket Lifecycle

1. **Creation**: Detected from patterns or created manually
2. **Assignment**: Linked to appropriate agent
3. **Status Updates**: pending → in_progress → completed
4. **Closure**: Marked as done or cancelled

## Agent Delegation

Delegation happens automatically based on:
- Keywords in the request
- Task type detection
- Explicit delegation syntax

Example triggers:
- "Research Python best practices" → Research Agent
- "Write tests for this function" → QA Agent
- "Document the API endpoints" → Documentation Agent

## Benefits Over Standard Claude

| Feature | Standard Claude | Claude MPM |
|---------|----------------|------------|
| Ticket Management | Manual | Automatic |
| Task Delegation | Manual | Automatic |
| Session History | Limited | Comprehensive |
| Context Management | Manual | Assisted |
| Process Control | None | Full |
| Framework Loading | CLAUDE.md files | Dynamic injection |

## Important Directories

Claude MPM uses these locations:

```
~/.claude-mpm/
├── sessions/          # Session logs
├── logs/             # Debug logs
└── config/           # Configuration

./tickets/            # Project tickets
├── tasks/           # Task tickets
└── epics/          # Epic tickets
```

## Configuration Concepts

### Models
Claude MPM supports all Claude models:
- `opus` - Most capable (default)
- `sonnet` - Balanced
- `haiku` - Fastest

### Flags
Key command-line flags:
- `--non-interactive` - Exit after response
- `--no-tickets` - Disable ticket creation
- `--subprocess` - Use subprocess orchestration
- `--debug` - Enable debug logging

## Best Practices

1. **Use Clear Patterns**: TODO, TASK, BUG, FEATURE for automatic tickets
2. **Leverage Agents**: Let Claude MPM delegate appropriately
3. **Review Sessions**: Check logs to understand what happened
4. **Manage Context**: Be aware of conversation length
5. **Organize Tickets**: Use the ticket system for project management

## Common Misconceptions

### "I need CLAUDE.md files"
No! Claude MPM injects instructions dynamically. Your projects stay clean.

### "It's just a wrapper"
It's an orchestration layer with intelligent monitoring and enhancement.

### "I lose control"
You gain control - full process management and monitoring.

### "It's complicated"
The complexity is hidden. Use it like regular Claude with extra benefits.

## Next Steps

Now that you understand the concepts:

1. Explore [Basic Usage](../02-guides/basic-usage.md)
2. Learn [Ticket Management](../02-guides/ticket-management.md)
3. Master [Interactive Mode](../02-guides/interactive-mode.md)
4. Understand [Features](../03-features/README.md) in depth