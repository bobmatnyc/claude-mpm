# Headless Mode

Headless mode enables programmatic use of Claude-MPM for automation, CI/CD pipelines, and orchestration platforms.

## Overview

Headless mode is designed for:

- **Orchestration Platforms**: Vibe Kanban, custom task runners
- **CI/CD Pipelines**: GitHub Actions, GitLab CI, Jenkins
- **Scripting**: Bash scripts, Python automation
- **Integration Testing**: Automated code review and validation

When enabled, headless mode:
- Disables Rich console formatting (no colors, progress bars, or interactive elements)
- Outputs newline-delimited JSON (NDJSON) for easy parsing
- Reads input from stdin or the `--input` flag
- Returns structured results for programmatic consumption

## Basic Usage

### Running with Input

```bash
# From stdin
echo "implement user authentication" | claude-mpm run --headless

# From -i/--input flag
claude-mpm run --headless -i "implement user authentication"

# From a file
claude-mpm run --headless -i @prompt.txt

# Combine with non-interactive mode
claude-mpm run --headless --non-interactive -i "fix the bug in auth.py"
```

### Common Flag Combinations

```bash
# Headless with non-interactive mode (most common for automation)
claude-mpm run --headless --non-interactive -i "your prompt"

# Headless with resume (continue previous session)
claude-mpm run --headless --resume

# Headless with MPM resume (resume specific MPM session)
claude-mpm run --headless --mpm-resume <session_id>

# Headless with monitoring disabled
claude-mpm run --headless --no-hooks

# Headless with specific working directory
claude-mpm run --headless -i "task" -C /path/to/project
```

## Output Format

Headless mode outputs newline-delimited JSON (NDJSON). Each line is a complete JSON object.

### Message Types

#### System Messages

Initialization and lifecycle events:

```json
{"type":"system","subtype":"init","session_id":"abc123","timestamp":"2024-01-15T10:30:00Z"}
{"type":"system","subtype":"ready","session_id":"abc123"}
{"type":"system","subtype":"shutdown","session_id":"abc123"}
```

#### Assistant Messages

Claude's responses during the session:

```json
{"type":"assistant","message":{"content":"I'll implement the feature...","tool_calls":[]},"session_id":"abc123"}
```

#### Tool Messages

Tool execution events:

```json
{"type":"tool","name":"edit_file","status":"started","session_id":"abc123"}
{"type":"tool","name":"edit_file","status":"completed","result":{"success":true},"session_id":"abc123"}
```

#### Result Messages

Final session outcome:

```json
{"type":"result","subtype":"success","session_id":"abc123","summary":"Feature implemented successfully"}
{"type":"result","subtype":"error","session_id":"abc123","error":"Task failed: compilation error"}
```

### Parsing with jq

```bash
# Extract session ID
SESSION_ID=$(claude-mpm run --headless -i "task" | jq -r 'select(.session_id) | .session_id' | head -1)

# Get final result
claude-mpm run --headless -i "task" | jq -s 'map(select(.type == "result")) | last'

# Filter assistant messages
claude-mpm run --headless -i "task" | jq 'select(.type == "assistant")'

# Check for errors
claude-mpm run --headless -i "task" | jq 'select(.type == "result" and .subtype == "error")'
```

### Parsing with Python

```python
import json
import subprocess

def run_claude_mpm(prompt: str) -> dict:
    """Run claude-mpm in headless mode and parse results."""
    result = subprocess.run(
        ["claude-mpm", "run", "--headless", "-i", prompt],
        capture_output=True,
        text=True
    )

    messages = []
    for line in result.stdout.strip().split('\n'):
        if line:
            messages.append(json.loads(line))

    # Get final result
    results = [m for m in messages if m.get('type') == 'result']
    return results[-1] if results else None

# Usage
result = run_claude_mpm("implement hello world function")
if result and result.get('subtype') == 'success':
    print("Task completed successfully")
```

## Session Management

### Resume Previous Session

Claude-MPM supports two resume mechanisms:

#### `--resume` (Claude Code Resume)

Passes the `--resume` flag directly to Claude Code to continue the last conversation:

```bash
# Start a task
claude-mpm run --headless -i "start implementing feature X"

# Continue the same conversation
claude-mpm run --headless --resume
```

#### `--mpm-resume` (MPM Session Resume)

Resumes a specific MPM session with full context:

```bash
# Resume last MPM session
claude-mpm run --headless --mpm-resume

# Resume specific session by ID
claude-mpm run --headless --mpm-resume abc123
```

### Session Workflow Example

```bash
#!/bin/bash
set -e

# Start a new task and capture session ID
OUTPUT=$(claude-mpm run --headless -i "implement user login feature" 2>&1)
SESSION_ID=$(echo "$OUTPUT" | jq -r 'select(.session_id) | .session_id' | head -1)

echo "Started session: $SESSION_ID"

# Check result
RESULT=$(echo "$OUTPUT" | jq -s 'map(select(.type == "result")) | last')
STATUS=$(echo "$RESULT" | jq -r '.subtype')

if [ "$STATUS" = "error" ]; then
    echo "Task failed, attempting to continue..."
    claude-mpm run --headless --resume -i "please continue and fix the error"
fi
```

## Integration Examples

### Vibe Kanban Integration

Vibe Kanban uses headless mode for automated task execution:

```bash
# Execute a ticket task
claude-mpm run --headless --non-interactive \
    -i "$(cat ticket-description.md)" \
    -C /path/to/repo \
    2>&1 | tee session-output.jsonl

# Parse results for ticket status update
jq -s 'map(select(.type == "result")) | last' session-output.jsonl
```

### GitHub Actions

```yaml
name: AI Code Review
on: [pull_request]

jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install Claude MPM
        run: pip install claude-mpm

      - name: Run AI Review
        run: |
          claude-mpm run --headless --non-interactive \
            -i "Review the changes in this PR for code quality and potential bugs" \
            > review-output.jsonl

          # Extract review summary
          jq -s 'map(select(.type == "assistant")) | .[].message.content' review-output.jsonl
```

### GitLab CI

```yaml
ai-review:
  stage: review
  script:
    - pip install claude-mpm
    - |
      claude-mpm run --headless --non-interactive \
        -i "Analyze this codebase for security vulnerabilities" \
        > security-scan.jsonl
    - jq 'select(.type == "result")' security-scan.jsonl
  artifacts:
    paths:
      - security-scan.jsonl
```

### Shell Script Automation

```bash
#!/bin/bash
# automated-task.sh - Run tasks with retry logic

MAX_RETRIES=3
RETRY_COUNT=0

run_task() {
    claude-mpm run --headless --non-interactive -i "$1" 2>&1
}

check_success() {
    echo "$1" | jq -e 'select(.type == "result" and .subtype == "success")' > /dev/null
}

PROMPT="Implement the feature described in TASK.md"

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    OUTPUT=$(run_task "$PROMPT")

    if check_success "$OUTPUT"; then
        echo "Task completed successfully"
        exit 0
    fi

    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo "Attempt $RETRY_COUNT failed, retrying..."

    # On retry, use resume to continue context
    PROMPT="Continue the task and fix any issues"
done

echo "Task failed after $MAX_RETRIES attempts"
exit 1
```

## Error Handling

### Common Error Patterns

```json
{"type":"result","subtype":"error","error":"Rate limit exceeded","retry_after":60}
{"type":"result","subtype":"error","error":"Context window exceeded","session_id":"abc123"}
{"type":"result","subtype":"error","error":"API error: 500","session_id":"abc123"}
```

### Error Handling Script

```bash
#!/bin/bash

OUTPUT=$(claude-mpm run --headless -i "your task" 2>&1)
RESULT=$(echo "$OUTPUT" | jq -s 'map(select(.type == "result")) | last')

case $(echo "$RESULT" | jq -r '.subtype') in
    "success")
        echo "Completed successfully"
        ;;
    "error")
        ERROR=$(echo "$RESULT" | jq -r '.error')
        case "$ERROR" in
            *"Rate limit"*)
                RETRY_AFTER=$(echo "$RESULT" | jq -r '.retry_after // 60')
                echo "Rate limited, waiting ${RETRY_AFTER}s..."
                sleep "$RETRY_AFTER"
                # Retry logic here
                ;;
            *"Context window"*)
                echo "Context too large, consider using --mpm-resume"
                ;;
            *)
                echo "Error: $ERROR"
                exit 1
                ;;
        esac
        ;;
esac
```

## CLI Reference

### Headless-Related Flags

| Flag | Description |
|------|-------------|
| `--headless` | Run in headless mode (disables Rich console, uses stream-json output) |
| `--non-interactive` | Run in non-interactive mode (read from stdin or --input) |
| `-i, --input` | Input text or file path for non-interactive mode |
| `--resume` | Pass --resume flag to Claude Code to resume last conversation |
| `--mpm-resume [ID]` | Resume an MPM session (last if no ID, or specific session ID) |
| `--no-hooks` | Disable hook service |
| `--no-tickets` | Disable automatic ticket creation |

### Full Help

```bash
claude-mpm run --help
```

## Best Practices

### 1. Always Use Non-Interactive Mode

For automation, combine `--headless` with `--non-interactive`:

```bash
claude-mpm run --headless --non-interactive -i "your prompt"
```

### 2. Capture Session IDs

Store session IDs for later resume:

```bash
claude-mpm run --headless -i "task" | tee output.jsonl
SESSION_ID=$(jq -r 'select(.session_id) | .session_id' output.jsonl | head -1)
echo "$SESSION_ID" > .session_id
```

### 3. Parse NDJSON Properly

Use `jq -s` to collect all lines into an array for analysis:

```bash
# Get all messages as array
jq -s '.' output.jsonl

# Get last result
jq -s 'map(select(.type == "result")) | last' output.jsonl
```

### 4. Handle Timeouts

Set appropriate timeouts for long-running tasks:

```bash
timeout 3600 claude-mpm run --headless -i "complex task" || echo "Task timed out"
```

### 5. Log Everything

Always capture both stdout and stderr:

```bash
claude-mpm run --headless -i "task" > output.jsonl 2> error.log
```

## Troubleshooting

### No Output

If you get no output, ensure:
- Input is provided via `-i` or stdin
- Claude Code CLI is installed and authenticated
- You have API access

### Parse Errors

If jq fails to parse:
- Ensure you're reading line-by-line (NDJSON format)
- Check for non-JSON output in stderr
- Separate stdout and stderr: `2>error.log`

### Session Not Resuming

If `--resume` doesn't work:
- Ensure previous session completed (not interrupted)
- Check Claude Code session state
- Try `--mpm-resume` for MPM-level resume

## See Also

- [User Guide](../user/user-guide.md)
- [Session Management](../user/session-quick-reference.md)
- [Resume Logs](../user/resume-logs.md)
- [CI/CD Integration](../deployment/ci-cd.md)
