# Claude MPM Logging Guide

This guide explains how to enable and use comprehensive logging in Claude MPM to capture full prompt and response history.

## Quick Start

To enable verbose logging that captures all prompts and responses:

```bash
# Enable DEBUG logging (captures everything)
./claude-mpm --logging DEBUG

# Or use it with non-interactive mode
./claude-mpm --logging DEBUG -i "Your task here" --non-interactive
```

## Logging Levels

Claude MPM supports three logging levels:

- **OFF** (default): No logging
- **INFO**: Basic operation logs, statistics only (no prompts/responses)
- **DEBUG**: Full prompts, responses, and detailed traces

## Log Directory Structure

All logs are stored in `.claude-mpm/logs/` within your project directory:

```
.claude-mpm/
└── logs/
    ├── system/         # Framework and orchestration logs
    ├── agents/         # Per-agent execution logs
    │   ├── engineer/
    │   ├── research/
    │   └── ...
    └── sessions/       # Session-based logs
        └── 20250125_143052/  # Timestamp-based session
            ├── system.jsonl
            ├── agent_engineer.jsonl
            ├── delegations.jsonl
            └── session_report.json
```

## What Gets Logged

### INFO Level
- Agent invocation statistics (time, tokens, success)
- Delegation decisions
- System events
- **No prompts or responses**

### DEBUG Level
Everything from INFO plus:
- **Full prompts sent to each agent**
- **Complete agent responses**
- Cached interactions in `cache/prompts/` and `cache/responses/`
- Detailed error traces

## Viewing Logs

### Session Logs
Each run creates a timestamped session directory:

```bash
# View latest session
ls -la .claude-mpm/logs/sessions/

# View agent interactions for a session
cat .claude-mpm/logs/sessions/20250125_143052/agent_engineer.jsonl | jq .
```

### Daily Agent Logs
Agent logs are also organized by date:

```bash
# View today's engineer agent logs
cat .claude-mpm/logs/agents/engineer/20250125.jsonl | jq .
```

### Cached Prompts and Responses
In DEBUG mode, all interactions are cached:

```bash
# View cached prompts
ls .claude-mpm/cache/prompts/

# View a specific prompt
cat .claude-mpm/cache/prompts/engineer_a1b2c3d4.txt
```

## Log Format

Logs are stored in JSON Lines format (`.jsonl`):

```json
{
  "timestamp": "2025-01-25T14:30:52.123456",
  "agent": "engineer",
  "task": "Implement user authentication",
  "execution_time": 12.5,
  "tokens": 2348,
  "success": true,
  "prompt": "Full prompt text here...",
  "response": "Complete agent response here...",
  "metadata": {
    "session_id": "20250125_143052",
    "delegation_format": "subprocess"
  }
}
```

## Statistics and Reports

### Session Report
Each session generates a summary report:

```bash
cat .claude-mpm/logs/sessions/20250125_143052/session_report.json | jq .
```

### Aggregated Statistics
View cumulative statistics:

```bash
cat .claude-mpm/stats/agent_stats.json | jq .
```

## Custom Log Directory

You can specify a custom log directory:

```bash
./claude-mpm --logging DEBUG --log-dir /path/to/logs
```

## Environment Variables

Set default logging behavior:

```bash
# Enable debug logging by default
export CLAUDE_MPM_DEBUG=1
```

## Analyzing Logs

### Find All Engineer Agent Tasks
```bash
jq -r '.task' .claude-mpm/logs/agents/engineer/*.jsonl | sort | uniq
```

### Calculate Average Token Usage
```bash
jq -s 'map(.tokens) | add/length' .claude-mpm/logs/agents/engineer/*.jsonl
```

### Extract Failed Tasks
```bash
jq 'select(.success == false)' .claude-mpm/logs/agents/*/*.jsonl
```

## Hook Integration

Claude MPM can also capture logs through hooks. See [Hook Documentation](./HOOKS.md) for details on:
- Pre-delegation hooks (modify tasks before execution)
- Post-delegation hooks (process results after execution)
- Custom logging hooks

## Privacy and Security

- Logs may contain sensitive information from your codebase
- The `.claude-mpm/` directory includes a `.gitignore` to prevent accidental commits
- Consider rotating or cleaning old logs periodically

## Troubleshooting

### Logs Not Appearing
1. Ensure `--logging DEBUG` or `--logging INFO` is specified
2. Check write permissions in project directory
3. Verify `.claude-mpm/logs/` directory exists

### Performance Impact
- DEBUG logging has minimal performance impact
- Cached interactions use content hashing to avoid duplicates
- Logs are written asynchronously

## Example Usage

### Full Debugging Session
```bash
# Run with full logging
./claude-mpm --logging DEBUG -i "Analyze and optimize the authentication module" --non-interactive

# View the session
SESSION=$(ls -t .claude-mpm/logs/sessions/ | head -1)
echo "Session: $SESSION"

# View PM delegations
jq . .claude-mpm/logs/sessions/$SESSION/delegations.jsonl

# View Research Agent analysis
jq '.prompt, .response' .claude-mpm/logs/sessions/$SESSION/agent_research.jsonl

# View Engineer implementation
jq '.prompt, .response' .claude-mpm/logs/sessions/$SESSION/agent_engineer.jsonl
```

### Quick Statistics Check
```bash
# Today's activity summary
jq '.["2025-01-25"]' .claude-mpm/stats/agent_stats.json
```

## Log Maintenance

### Cleanup Utility
A cleanup script is provided to manage log files:

```bash
# Show log statistics
./scripts/cleanup_logs.py --stats

# Clean empty session directories (dry run)
./scripts/cleanup_logs.py --clean-empty

# Actually clean empty directories
./scripts/cleanup_logs.py --clean-empty --execute

# Archive logs older than 7 days
./scripts/cleanup_logs.py --archive 7 --execute

# Combined operations
./scripts/cleanup_logs.py --clean-empty --archive 30 --stats --execute
```

## Best Practices

1. **Development**: Use `--logging DEBUG` during development
2. **Production**: Use `--logging INFO` for statistics without sensitive data
3. **Debugging**: Check session logs first, then drill down to specific agents
4. **Archival**: Use the cleanup utility to archive old logs: `./scripts/cleanup_logs.py --archive 30 --execute`
5. **Maintenance**: Regularly clean empty sessions: `./scripts/cleanup_logs.py --clean-empty --execute`