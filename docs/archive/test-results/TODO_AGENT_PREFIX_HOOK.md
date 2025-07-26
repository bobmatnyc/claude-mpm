# TodoAgentPrefixHook Integration

## Overview

The TodoAgentPrefixHook has been integrated into the claude-mpm orchestrator system to automatically enforce agent prefixes on TodoWrite tool calls. This ensures that all todo items are properly attributed to the appropriate specialized agent.

## Implementation Details

### Hook Location
- **Main Hook**: `/src/claude_mpm/hooks/builtin/todo_agent_prefix_hook.py`
- **Tool Interceptor**: `/src/claude_mpm/hooks/tool_call_interceptor.py`

### Features
1. **Automatic Prefix Detection**: Detects if a todo item already has an agent prefix
2. **Smart Agent Suggestion**: Analyzes todo content to suggest appropriate agent
3. **Prefix Formats Supported**:
   - Bracketed: `[Engineer]`, `[QA]`, `[Research]`, etc.
   - Unbracketed: `Engineer:`, `QA:`, `Research:`, etc.

### Agent Mapping
The hook automatically suggests agents based on keywords:
- **Engineer**: code, implement, refactor, fix, debug, develop, function, class, api
- **Research**: analyze, investigate, research, explore, study, compare, evaluate
- **Documentation**: document, explain, describe, guide, readme, tutorial
- **QA**: test, validate, verify, check, quality, coverage
- **Security**: security, vulnerability, auth, encrypt, permission, audit
- **Ops**: deploy, infrastructure, server, docker, kubernetes, ci/cd
- **Data Engineer**: data, database, pipeline, etl, api, integration
- **Version Control**: git, commit, merge, branch, repository

## Integration Points

### 1. Hook Service Auto-Discovery
The hook is automatically discovered and loaded by:
- `JSONRPCHookClient._discover_hooks()` in `/src/claude_mpm/hooks/json_rpc_hook_client.py`
- `HookLoader._load_builtin_hooks()` in `/src/claude_mpm/hooks/hook_runner.py`

### 2. Framework Instructions
The TodoWrite usage instructions have been updated in:
- `/src/claude_mpm/services/framework_claude_md_generator.py` (generate_todo_task_tools method)
- Emphasizes the CRITICAL requirement to always use [Agent] prefixes

### 3. Agent Instructions
The main orchestrator instructions at `/src/claude_mpm/agents/INSTRUCTIONS.md` already include:
- "TODO TRACKING RULE: When using TodoWrite, ALWAYS prefix each task with [Agent]"

## Testing

A test script is available at `/scripts/test_todo_hook.py` to verify the hook functionality:

```bash
python scripts/test_todo_hook.py
```

## Architecture Notes

### Limitation
Claude-mpm runs Claude CLI as a subprocess and cannot intercept tool calls in real-time. The hook system is designed to:
1. Be loaded and available via JSON-RPC
2. Provide guidance through updated instructions
3. Could be integrated if claude-mpm adds tool call interception in the future

### Future Enhancement Opportunities
1. **Real-time Interception**: If claude-mpm adds a proxy layer for Claude API calls
2. **Post-Processing**: Hook could be called after Claude generates responses
3. **Validation Reports**: Generate reports on todo compliance

## Usage

The hook is automatically active when claude-mpm is run. It will:
1. Monitor TodoWrite tool calls (when interception is available)
2. Add agent prefixes to todos missing them
3. Preserve existing valid prefixes
4. Default to "Engineer:" for unclear content

No additional configuration is required - the hook works out of the box with sensible defaults.