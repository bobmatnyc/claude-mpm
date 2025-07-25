# Memory Protection

Claude MPM's memory protection features help manage context limits, prevent token overflow, and ensure stable long-running sessions.

## Understanding Context Limits

### What Are Context Limits?

Claude has a maximum context window - the total amount of text it can process in a conversation:

- **Claude 3 Opus**: ~200k tokens
- **Claude 3 Sonnet**: ~200k tokens  
- **Claude 3 Haiku**: ~200k tokens

One token ≈ 4 characters in English.

### Why Memory Protection Matters

Without protection:
- ❌ Context overflow errors
- ❌ Lost conversation history
- ❌ Abrupt session termination
- ❌ Incomplete responses

With Claude MPM protection:
- ✅ Early warnings
- ✅ Automatic optimization
- ✅ Graceful degradation
- ✅ Session continuity

## Memory Monitoring

### Real-Time Tracking

Claude MPM monitors context usage:

```
[System] Context usage: 45,230 tokens (22.6% of limit)
[System] Warning: Context usage at 150,000 tokens (75% of limit)
[System] Critical: Context near limit (190,000 tokens)
```

### Usage Indicators

| Level | Usage | Action |
|-------|-------|--------|
| Normal | <50% | Continue normally |
| Caution | 50-75% | Monitor closely |
| Warning | 75-90% | Consider optimization |
| Critical | >90% | Immediate action needed |

## Protection Mechanisms

### 1. Early Warning System

```
You: [Long prompt with lots of context]

[System Warning] Context usage high (165,000 tokens).
Consider:
- Starting a new session
- Summarizing previous work
- Removing unnecessary context
```

### 2. Automatic Summarization

When approaching limits:

```
[System] Auto-summarizing conversation to preserve context...

Previous discussion covered:
- Implemented user authentication
- Created REST API endpoints
- Added database models
- Wrote initial tests

Continuing from this point...
```

### 3. Context Optimization

Claude MPM automatically:
- Removes redundant information
- Compresses verbose sections
- Preserves critical context
- Maintains conversation flow

### 4. Subprocess Isolation

With subprocess orchestration:

```bash
# Each agent gets fresh context
claude-mpm run --subprocess -i "Complex multi-agent task"

[Each subprocess starts with minimal context]
Engineer: Fresh 200k token window
QA: Fresh 200k token window
Docs: Fresh 200k token window
```

## Memory Management Strategies

### 1. Session Segmentation

Break long tasks into sessions:

```bash
# Session 1: Planning
claude-mpm run -i "Plan the architecture" --session-name arch-planning

# Session 2: Implementation (fresh context)
claude-mpm run -i "Implement the planned architecture" --session-name implementation

# Session 3: Testing (fresh context)
claude-mpm run -i "Test the implementation" --session-name testing
```

### 2. Context Windowing

Focus on relevant context:

```
You: Let's focus on just the authentication module now.
     You can forget about the UI discussions.

Claude: I'll focus specifically on the authentication module,
        setting aside the UI-related context.
```

### 3. Explicit Summarization

Request summaries before hitting limits:

```
You: Before we continue, can you summarize what we've 
     accomplished so far in bullet points?

Claude: Here's our progress summary:
        • Designed user authentication flow
        • Implemented JWT tokens
        • Created user model
        • Added password hashing
        [Condensed from 50k tokens to 1k tokens]
```

### 4. Checkpoint Creation

Save state at key points:

```bash
# Save current state
claude-mpm save-checkpoint "auth-system-complete"

# Resume from checkpoint with fresh context
claude-mpm resume-checkpoint "auth-system-complete"
```

## Configuration Options

### Memory Limits

Configure warning thresholds:

```python
# In configuration
MEMORY_PROTECTION = {
    "warning_threshold": 0.75,  # Warn at 75%
    "critical_threshold": 0.90,  # Critical at 90%
    "auto_summarize": True,     # Enable auto-summary
    "preserve_tickets": True    # Always keep ticket context
}
```

### Per-Model Settings

```python
MODEL_LIMITS = {
    "opus": {
        "max_tokens": 200000,
        "warning_at": 150000,
        "summarize_at": 180000
    },
    "sonnet": {
        "max_tokens": 200000,
        "warning_at": 150000,
        "summarize_at": 180000
    }
}
```

## Monitoring Tools

### Check Current Usage

```bash
# In interactive mode
You: /status

Claude MPM Status:
- Model: claude-3-opus
- Context: 45,230 / 200,000 tokens (22.6%)
- Session Duration: 25 minutes
- Tickets Created: 5
```

### Memory Usage Logs

```bash
# View memory usage over time
grep "Context usage" ~/.claude-mpm/sessions/latest.log

# Graph usage pattern
grep "Context usage" ~/.claude-mpm/sessions/latest.log | \
  awk '{print $4}' | \
  gnuplot -p -e "plot '-' with lines"
```

## Best Practices

### 1. Start Fresh for New Topics

```bash
# Don't overload a single session
# Bad: One 8-hour session covering everything
# Good: Multiple focused sessions

claude-mpm run -i "Design database schema" --session db-design
claude-mpm run -i "Implement API endpoints" --session api-impl
claude-mpm run -i "Write tests" --session testing
```

### 2. Use Subprocess for Large Tasks

```bash
# Subprocess mode gives each agent fresh context
claude-mpm run --subprocess -i "Build complete application"

# Each agent starts with full context available
```

### 3. Periodically Summarize

```
You: Let's pause and summarize our progress before continuing
     with the next module.

Claude: Here's our condensed progress summary...
        [Reduces context from 100k to 5k tokens]
```

### 4. Remove Unnecessary Context

```
You: We've finished with the authentication module. You can
     forget those implementation details and focus on the 
     payment system now.
```

## Recovery Strategies

### When Hitting Limits

1. **Save and Continue**:
   ```bash
   # Save current session
   cp ~/.claude-mpm/sessions/latest.log ./important-session.log
   
   # Start fresh with summary
   claude-mpm run -i "Continue from: [paste summary]"
   ```

2. **Extract Key Information**:
   ```
   You: Before we hit the limit, please provide:
        1. All created ticket IDs
        2. Key decisions made
        3. Important code snippets
        4. Next steps
   ```

3. **Use Checkpoints**:
   ```bash
   # Create checkpoint before limit
   claude-mpm checkpoint create "pre-limit-state"
   
   # Resume with fresh context
   claude-mpm checkpoint resume "pre-limit-state"
   ```

## Advanced Memory Management

### Dynamic Context Pruning

```python
# Auto-remove old context
PRUNING_RULES = {
    "remove_after": 50000,  # Remove old exchanges after 50k tokens
    "keep_recent": 10,      # Always keep last 10 exchanges
    "preserve": ["TODO", "DECISION", "ticket"]  # Keep important items
}
```

### Context Compression

```python
# Automatic compression settings
COMPRESSION = {
    "enabled": True,
    "algorithm": "summary",  # or "truncate", "semantic"
    "target_ratio": 0.3,     # Compress to 30% of original
}
```

### Memory Pooling

For subprocess orchestration:

```python
# Shared memory pool for agents
MEMORY_POOL = {
    "total_limit": 800000,   # Total for all agents
    "per_agent_limit": 200000,  # Max per agent
    "shared_context": 50000,    # Shared between agents
}
```

## Troubleshooting

### "Context length exceeded" Error

**Immediate Actions**:
```bash
# Start fresh session
claude-mpm run -i "Summary of previous work: [brief summary]"

# Or use subprocess mode
claude-mpm run --subprocess -i "Continue task"
```

### Memory Warnings Not Appearing

**Check configuration**:
```bash
# Verify memory protection is enabled
claude-mpm config get memory_protection.enabled

# Enable if needed
claude-mpm config set memory_protection.enabled true
```

### Slow Performance Near Limits

**Optimize context**:
```
You: Please provide a concise summary of our discussion,
     focusing only on decisions and next steps.
```

## Monitoring Scripts

### Context Usage Monitor

```bash
#!/bin/bash
# monitor_context.sh

while true; do
    usage=$(grep "Context usage" ~/.claude-mpm/sessions/latest.log | tail -1)
    echo "$(date): $usage"
    sleep 60
done
```

### Alert on High Usage

```bash
#!/bin/bash
# context_alert.sh

threshold=150000
current=$(grep "Context usage" ~/.claude-mpm/sessions/latest.log | \
          tail -1 | awk '{print $4}')

if [ "$current" -gt "$threshold" ]; then
    echo "WARNING: Context usage at $current tokens!"
    # Send notification (email, slack, etc)
fi
```

## Integration with Workflows

### CI/CD Considerations

```yaml
# .github/workflows/claude-mpm.yml
- name: Run Claude MPM with memory limits
  run: |
    claude-mpm run \
      --memory-limit 100000 \
      --auto-summarize \
      -i "Review pull request" \
      --non-interactive
```

### Batch Processing

```bash
# Process files with context reset between each
for file in *.py; do
    echo "Processing $file"
    claude-mpm run \
      --reset-context \
      -i "Review $file" \
      --non-interactive
done
```

## Next Steps

- Learn about [Session Logging](session-logging.md) to track memory usage
- Explore [Subprocess Orchestration](../02-guides/subprocess-orchestration.md) for isolation
- See [Configuration](../04-reference/configuration.md) for memory settings
- Check [Troubleshooting](../04-reference/troubleshooting.md) for solutions