# Core Concepts

Understanding these core concepts will help you use Claude MPM effectively.

## What is Claude MPM?

Claude MPM (Multi-Agent Project Manager) is a **framework** that enhances Claude with multi-agent capabilities and extensible architecture.

```
You → Claude MPM → Services & Agents
         ↓
    [Enhancement Layer]
    - Agent delegation  
    - Hook system
    - Session logging
    - Service architecture
```

## Key Concepts

### 1. Agent System

Claude MPM provides a sophisticated agent system:

- **Specialized Agents**: Different agents for different task types
- **Dynamic Loading**: Agents are loaded based on task requirements
- **Extensible**: Easy to add new agent types

Benefits:
- Task-specific expertise
- Better code organization
- Modular capabilities
- Clear separation of concerns

### 2. Framework Injection

Claude MPM provides a comprehensive framework that includes:
- When to delegate to specialized agents
- How to structure responses
- Project management best practices
- Hook points for customization

The framework is loaded dynamically based on your configuration.

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

### 4. Hook System

Claude MPM provides a powerful hook system for extensibility:

```python
# Example hook
class MyHook(BaseHook):
    def pre_process(self, request):
        # Modify request before processing
        return request
    
    def post_process(self, response):
        # Modify response after processing
        return response
```

Hooks enable:
- Custom processing logic
- Integration with external systems
- Response transformation
- Request validation

### 5. Session Management

Every interaction is a **session**:

- **Session Start**: When you run claude-mpm
- **Session Content**: All inputs, outputs, and metadata
- **Session End**: When the command completes
- **Session Log**: Saved to `~/.claude-mpm/sessions/`

### 6. Service Architecture

Claude MPM uses a service-oriented architecture:
- **Hook Service**: Manages extensibility
- **Agent Service**: Handles agent lifecycle
- **Logging Service**: Comprehensive logging
- **Configuration Service**: Manages settings

## How It All Works Together

### Example Flow

1. **You type**: 
   ```bash
   claude-mpm run -i "Create a REST API for user management"
   ```

2. **Claude MPM**:
   - Loads appropriate framework
   - Initializes services
   - Prepares agent context

3. **Claude (PM Agent)**:
   - Recognizes this needs engineering
   - Delegates to Engineer Agent
   - Provides structured response

4. **Claude MPM**:
   - Processes through hooks
   - Logs everything
   - Returns the result

### The Framework

The framework is a set of instructions that teaches Claude:

```markdown
You are working with Claude MPM, which provides:
- Multi-agent delegation
- Hook system for extensibility
- Session tracking
- Service architecture

When engineering is needed, delegate to Engineer...
When documentation is needed, delegate to Documentation...
```

This is loaded based on your configuration and needs.

## Execution Modes

### 1. Interactive Mode
Default mode for interactive sessions:
```bash
claude-mpm  # Launches interactive session
```

### 2. Non-Interactive Mode
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