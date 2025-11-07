# Resume Log System Documentation

## Overview

The Resume Log System enables seamless session continuity when Claude hits token limits. It automatically generates structured markdown logs that preserve context and enable smooth resumption of work.

## Key Features

- **Proactive Threshold Management**: 70%/85%/95% thresholds provide early warnings (60k token buffer at first alert)
- **Automatic Resume Log Generation**: Triggered by API stop reasons or token thresholds
- **Structured Context Preservation**: 10k token maximum, organized into focused sections
- **Human-Readable Format**: Markdown files optimized for both humans and Claude
- **Token Usage Tracking**: Real-time monitoring of context window consumption
- **Session Continuity**: Automatic injection of resume logs on session startup

## Architecture

### Components

1. **ContextMetrics** (`models/resume_log.py`)
   - Data model for token usage and context window metrics
   - Tracks budget, usage, remaining tokens, and stop reasons

2. **ResumeLog** (`models/resume_log.py`)
   - Structured data model for session resume information
   - 10k token budget distributed across 7 key sections
   - Converts to markdown for Claude consumption

3. **ResumeLogGenerator** (`services/infrastructure/resume_log_generator.py`)
   - Service for generating and managing resume logs
   - Handles triggers, generation, storage, and cleanup
   - Supports generation from session state or TODO lists

4. **SessionManager** (`services/session_manager.py`)
   - Extended with token usage tracking
   - Monitors context metrics throughout session
   - Automatically loads resume logs on startup
   - Generates resume logs on session end

5. **Response Tracking** (`hooks/claude_hooks/response_tracking.py`)
   - Extended to capture Claude API `stop_reason` and `usage` data
   - Feeds token metrics to SessionManager

## Token Thresholds

The system uses three graduated thresholds for proactive context management:

| Threshold | Tokens Used | Tokens Free | Action |
|-----------|-------------|-------------|---------|
| **Caution (70%)** | 140,000 | 60,000 | First warning - plan for session transition |
| **Warning (85%)** | 170,000 | 30,000 | Strong warning - complete current tasks |
| **Critical (95%)** | 190,000 | 10,000 | Urgent alert - stop new work, generate resume log |

### Rationale

Previous 90%/95% thresholds were too reactive (only 20k buffer). New 70%/85%/95% thresholds:
- Provide 60k token buffer at first warning
- Allow time to reach natural breakpoints
- Enable proactive planning vs reactive scrambling
- Reduce risk of context window exceeded errors

## Resume Log Structure

Each resume log targets a maximum of 10k tokens, distributed as:

```markdown
# Session Resume Log: {session_id}

## Context Metrics (500 tokens)
- Model, token usage, percentage, stop reason

## Mission Summary (1,000 tokens)
- Overall goal and purpose of the session

## Accomplishments (2,000 tokens)
- What was completed during the session

## Key Findings (2,500 tokens)
- Important discoveries and learnings

## Decisions & Rationale (1,500 tokens)
- Choices made and reasoning behind them

## Next Steps (1,500 tokens)
- What needs to happen next

## Critical Context (1,000 tokens)
- Essential state and data for continuation

## Session Metadata
- Files modified, agents used, errors, warnings
```

## Configuration

Resume logs are configured in `.claude-mpm/configuration.yaml`:

```yaml
context_management:
  enabled: true
  budget_total: 200000

  thresholds:
    caution: 0.70      # 140k used / 60k free
    warning: 0.85      # 170k used / 30k free
    critical: 0.95     # 190k used / 10k free

  resume_logs:
    enabled: true
    auto_generate: true
    max_tokens: 10000
    storage_dir: ".claude-mpm/resume-logs"
    format: "markdown"

    triggers:
      - "model_context_window_exceeded"
      - "max_tokens"
      - "manual_pause"
      - "threshold_critical"
      - "threshold_warning"

    cleanup:
      enabled: true
      keep_count: 10
      auto_cleanup: true
```

## Usage

### Automatic Usage

The system operates automatically:

1. **Token Tracking**: SessionManager tracks cumulative token usage from API responses
2. **Threshold Monitoring**: Warnings triggered at 70%, 85%, and 95%
3. **Auto-Generation**: Resume logs created when thresholds or stop reasons detected
4. **Auto-Loading**: Previous session resume logs loaded on startup if found

### Manual Usage

Generate a resume log programmatically:

```python
from claude_mpm.services.session_manager import get_session_manager
from claude_mpm.services.infrastructure.resume_log_generator import ResumeLogGenerator

# Get session manager
session_mgr = get_session_manager()

# Update token usage
session_mgr.update_token_usage(
    input_tokens=100000,
    output_tokens=40000,
    stop_reason="end_turn"
)

# Check if warning threshold reached
if session_mgr.should_warn_context_limit(threshold=0.70):
    print("Warning: 70% context usage reached")

# Generate resume log
session_state = {
    "mission_summary": "Implementing new feature X",
    "accomplishments": ["Completed task A", "Fixed bug B"],
    "next_steps": ["Deploy to production", "Write documentation"],
}

log_path = session_mgr.generate_resume_log(session_state=session_state)
print(f"Resume log saved to: {log_path}")
```

### Using ResumeLogGenerator Directly

```python
from claude_mpm.models.resume_log import ContextMetrics, ResumeLog
from claude_mpm.services.infrastructure.resume_log_generator import ResumeLogGenerator

# Initialize generator
generator = ResumeLogGenerator()

# Create from session state
session_state = {
    "context_metrics": {
        "total_budget": 200000,
        "used_tokens": 170000,
        "percentage_used": 85.0,
    },
    "mission_summary": "Feature implementation",
    "accomplishments": ["Task 1", "Task 2"],
    "next_steps": ["Task 3"],
}

resume_log = generator.generate_from_session_state(
    session_id="20251101_115000",
    session_state=session_state,
    stop_reason="end_turn"
)

# Save
file_path = generator.save_resume_log(resume_log)

# List all resume logs
logs = generator.list_resume_logs()

# Cleanup old logs (keep last 10)
deleted = generator.cleanup_old_logs(keep_count=10)
```

## Storage

Resume logs are stored in `.claude-mpm/resume-logs/`:

```
.claude-mpm/resume-logs/
├── session-20251101_115000.md    # Markdown format (primary)
├── session-20251101_115000.json  # JSON format (metadata)
├── session-20251101_120000.md
├── session-20251101_120000.json
└── .gitignore                     # Prevents committing session logs
```

## Integration Points

### Hook Integration

Response tracking hooks capture API metadata:

```python
# In claude_hooks/response_tracking.py
def track_stop_response(self, event, session_id, metadata, pending_prompts):
    # Capture stop_reason
    if "stop_reason" in event:
        metadata["stop_reason"] = event["stop_reason"]

    # Capture usage data
    if "usage" in event:
        metadata["usage"] = {
            "input_tokens": usage_data.get("input_tokens", 0),
            "output_tokens": usage_data.get("output_tokens", 0),
            # ... cache metrics
        }
```

### Session Manager Integration

SessionManager maintains cumulative token usage:

```python
# In services/session_manager.py
class SessionManager:
    def update_token_usage(self, input_tokens, output_tokens, stop_reason):
        self._cumulative_tokens += input_tokens + output_tokens
        self._context_metrics["percentage_used"] = (
            self._cumulative_tokens / self._total_budget
        ) * 100
        # ... update metrics
```

### PM Integration

BASE_PM.md updated with new thresholds and instructions:

```markdown
### When context usage reaches 70%:
⚠️ Context Usage Caution: 70% capacity reached
60,000 tokens remaining - consider planning for session transition.
```

## Testing

Comprehensive test suite in `tests/test_resume_log_system.py`:

```bash
# Run all resume log tests
python -m pytest tests/test_resume_log_system.py -v

# Run specific test class
python -m pytest tests/test_resume_log_system.py::TestResumeLogGenerator -v

# Run with coverage
python -m pytest tests/test_resume_log_system.py --cov=claude_mpm.models.resume_log --cov=claude_mpm.services.infrastructure.resume_log_generator
```

Test coverage includes:
- ✅ ContextMetrics data model
- ✅ ResumeLog creation and markdown generation
- ✅ File save/load operations
- ✅ ResumeLogGenerator triggers and generation
- ✅ SessionManager token tracking
- ✅ Threshold warnings
- ✅ Configuration loading

## Best Practices

### For PM Agents

1. **Monitor context usage** after each major delegation
2. **Warn at 70%** - First proactive notification
3. **Recommend transition at 85%** - Strong suggestion to wrap up
4. **Stop new work at 95%** - Generate resume log and pause

### For Session Management

1. **Check resume logs on startup** - Restore context from previous session
2. **Track token usage continuously** - Update after each API response
3. **Generate logs proactively** - Don't wait for context exceeded
4. **Clean up old logs** - Keep last 10 to prevent clutter

### For Resume Log Content

1. **Be concise** - Target 10k tokens total
2. **Focus on "why" not "what"** - Rationale over implementation details
3. **Prioritize actionable info** - Next steps should be immediately executable
4. **Preserve critical context** - State, IDs, paths needed for continuation
5. **Include metadata** - Files modified, agents used, errors encountered

## Troubleshooting

### Resume log not generated

Check configuration:
```python
from claude_mpm.services.infrastructure.resume_log_generator import ResumeLogGenerator
generator = ResumeLogGenerator()
stats = generator.get_stats()
print(stats)  # Check if enabled and auto_generate are True
```

### Token usage not tracking

Verify response tracking is capturing usage data:
```bash
# Check if response tracking is enabled
cat .claude-mpm/configuration.yaml | grep -A 5 "response_tracking:"

# Check hook logs for usage capture
tail -f .claude-mpm/logs/hooks.log | grep "Captured usage"
```

### Resume log not loading on startup

Check file permissions and location:
```bash
ls -la .claude-mpm/resume-logs/
# Should show session-*.md files with read permissions
```

## Future Enhancements

Potential improvements:
- [ ] Automatic TODO list extraction from conversations
- [ ] Smart content prioritization (ML-based token budget allocation)
- [ ] Resume log compression for large sessions
- [ ] Cross-session learning (patterns from previous resume logs)
- [ ] Integration with project memory systems
- [ ] Visual resume log viewer in dashboard
- [ ] Resume log quality metrics and feedback

## Related Documentation

- [Session Management](./session-management.md)
- [Response Tracking](./response-tracking.md)
- [Configuration Guide](./configuration.md)
- [BASE_PM Instructions](../src/claude_mpm/agents/BASE_PM.md)

## References

- Claude API Documentation: stop_reason values
- Token counting best practices
- Context window management strategies
