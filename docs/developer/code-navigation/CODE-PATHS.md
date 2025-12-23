# Code Paths Reference

## Primary Entry Points

### CLI Entry Point
```
bin/claude-mpm
    → src/claude_mpm/cli/__main__.py
        → cli/parser.py (argument parsing)
        → cli/executor.py (command dispatch)
        → cli/commands/<command>.py (specific handler)
```

### Interactive Mode Flow
```
claude-mpm run
    → cli/commands/run.py
        → core/interactive_session.py
            → core/claude_runner.py (Claude Code invocation)
            → hooks/base_hook.py (hook execution)
```

### Agent Loading Flow
```
Agent Request
    → services/agents/registry/agent_registry.py
        → agents/agent_loader.py (agent loading)
        → agents/templates/<agent>.md (Markdown agent file)
        → skills/agent_skills_injector.py (skill injection)
        → Final agent prompt with skills
```

## Critical Code Paths

### 1. Startup Path
```
cli/__main__.py:main()
    ├── cli/startup.py:initialize_startup()
    ├── cli/startup_logging.py:setup_logging()
    ├── core/container.py:get_container()
    └── cli/executor.py:execute_command()
```

### 2. Agent Deployment Path
```
cli/commands/agents.py:deploy()
    ├── services/agents/deployment/deployment_service.py
    │   ├── validate_agent()
    │   ├── prepare_deployment()
    │   └── execute_deployment()
    └── services/agents/registry/agent_registry.py:refresh()
```

### 3. Hook Execution Path
```
core/hook_manager.py:execute_hooks()
    ├── hooks/base_hook.py:BaseHook.pre_execution()
    ├── hooks/kuzu_memory_hook.py (if enabled)
    ├── hooks/kuzu_enrichment_hook.py (if enabled)
    └── hooks/session_resume_hook.py
```

### 4. Monitor Dashboard Path
```
claude-mpm monitor
    → cli/commands/monitor.py
        → services/monitor/server.py:start()
            → services/socketio/dashboard_server.py
            → d2/index.html (Svelte frontend)
```

### 5. MCP Gateway Path
```
claude-mpm mcp
    → cli/commands/mcp.py
        → services/mcp_gateway/main.py
            → services/mcp_gateway/server/mcp_server.py
            → services/mcp_gateway/tools/tool_registry.py
```

## Service Resolution Paths

### DI Container Resolution
```python
# Container initialized in startup
container = get_container()

# Service registration (lazy)
container.register_singleton(IAgentRegistry, AgentRegistry)

# Resolution path
container.get(IAgentRegistry)
    → check _singletons cache
    → if miss: create instance
        → resolve constructor dependencies recursively
        → call initialize() if exists
    → store in _singletons
    → return instance
```

### Configuration Resolution
```python
# Path: config/paths.py → core/unified_config.py
get_config("agents.default_tier")
    → check CLI overrides
    → check .claude-mpm/configuration.yaml
    → check ~/.claude-mpm/configuration.yaml
    → return system default
```

## Event Flow Paths

### Hook Event Flow
```
Pre-Tool Hook Event
    → hooks/base_hook.py:HookContext
        → Enrichment (kuzu_enrichment_hook.py)
        → Memory injection (memory_integration_hook.py)
        → Instruction reinforcement (instruction_reinforcement.py)

Post-Tool Hook Event
    → Response capture
        → Learning extraction (failure_learning/)
        → Memory storage (kuzu_response_hook.py)
```

### SocketIO Event Flow
```
Agent Activity
    → services/event_bus/event_bus.py:publish()
        → services/event_bus/relay.py
            → services/socketio/server/socketio_handlers.py
                → WebSocket broadcast to connected clients
```

## File Operations Paths

### Agent Template Loading
```
src/claude_mpm/agents/templates/
    ├── base_agent.md (base configuration)
    ├── engineer.md
    ├── qa.md
    └── ... (other agent templates)

Loading: agents/agent_loader.py:get_agent_prompt()
    → Load Markdown agent
    → Apply BASE_AGENT.md inheritance
    → Inject skills from skills/
    → Return final prompt string
```

### Skills Loading
```
Skills directories (in order of precedence):
    1. .claude-mpm/skills/ (project)
    2. ~/.claude/skills/ (user)
    3. src/claude_mpm/skills/bundled/ (bundled)

Loading: skills/skill_manager.py:load_skills()
    → Scan all directories
    → Parse skill metadata
    → Build skill registry
```

### Memory Operations
```
Memory read/write path:
    services/agents/memory/memory_manager.py
        → .claude-mpm/memories/<agent>_memory.md (project)
        → ~/.claude-mpm/memories/<agent>_memory.md (user)
```

## Testing Paths

### Unit Test Execution
```
pytest tests/unit/
    → conftest.py (fixtures)
    → tests/services/ (service tests)
    → tests/core/ (core tests)
```

### Integration Test Execution
```
pytest tests/integration/
    → tests/integration/agents/ (agent integration)
    → tests/integration/mcp/ (MCP gateway tests)
    → tests/integration/hooks/ (hook tests)
```

## Debug Trace Points

### Key Logging Locations
```python
# For startup issues
cli/startup.py - "Initializing Claude MPM..."
core/container.py - "Registering service..."

# For agent issues
agents/agent_loader.py - "Loading agent template..."
services/agents/registry/ - "Discovering agents..."

# For hook issues
hooks/base_hook.py - "Executing hook..."
core/hook_manager.py - "Hook execution complete..."

# For SocketIO issues
services/socketio/server/ - "SocketIO connection..."
```

### Environment Variables
```bash
CLAUDE_MPM_DEBUG=1      # Enable debug logging
CLAUDE_MPM_LOG_LEVEL=DEBUG  # Set log level
CLAUDE_MPM_NO_HOOKS=1   # Disable hooks (debugging)
```

## Quick Lookup Table

| Task | Primary File | Secondary Files |
|------|--------------|-----------------|
| Add CLI command | `cli/commands/<name>.py` | `cli/parsers/<name>_parser.py` |
| Add service | `services/<domain>/<name>.py` | `services/core/interfaces.py` |
| Add agent | `agents/templates/<name>.json` | `agents/agents_metadata.py` |
| Add hook | `hooks/<name>_hook.py` | `hooks/__init__.py` |
| Add skill | `skills/bundled/<name>.md` | `skills/skills_registry.py` |
| Modify DI | `core/container.py` | `services/core/interfaces.py` |

---
See also:
- [ARCHITECTURE-OVERVIEW.md](ARCHITECTURE-OVERVIEW.md) for system design
- [SERVICE-LAYER.md](SERVICE-LAYER.md) for service details
