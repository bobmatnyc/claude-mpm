# Claude Code Hooks Technical Implementation Guide

## Understanding Claude Code hooks fundamentally

Claude Code hooks are user-defined shell commands that execute automatically at specific points in Claude Code's lifecycle, transforming probabilistic AI assistance into deterministic, repeatable workflows. They provide programmatic control over Claude's behavior, ensuring critical actions always happen rather than relying on the AI to remember or choose to execute them.

### Technical architecture and execution model

The hooks system operates through an event-driven architecture where lifecycle events trigger parallel execution of matching commands. When Claude Code starts, it captures a snapshot of hook configurations from hierarchical settings files (enterprise → user → project → local), preventing mid-session modifications for security. Each hook runs in a separate shell process with full access to Claude Code's environment, executing within a **60-second default timeout** that's configurable per command.

Hook execution follows this flow: Event Trigger → Matcher Evaluation → Parallel Execution → Result Processing → Flow Control. All matching hooks run simultaneously in the current project directory, inheriting environment variables like `$CLAUDE_PROJECT_DIR` (absolute project path), `$CLAUDE_TOOL_NAME`, and `$CLAUDE_FILE_PATHS`. The system processes exit codes to determine execution flow - exit code 0 indicates success, exit code 2 blocks operations and feeds stderr to Claude, while other codes represent non-blocking errors.

### Available hook types and events

Claude Code provides six core hook events, each firing at specific lifecycle points:

**UserPromptSubmit** fires immediately when users submit prompts, before Claude processes them. This hook uniquely injects stdout directly into Claude's context, enabling prompt enhancement, validation, and security filtering. It can block prompts entirely with exit code 2.

**PreToolUse** executes after Claude creates tool parameters but before tool execution. It supports pattern matching for tool names (Write, Edit, Bash) and can prevent dangerous operations. This is your primary security enforcement point.

**PostToolUse** triggers after successful tool completion with full access to tool inputs and responses. While it cannot prevent already-executed tools, it provides feedback to Claude and enables automated cleanup, formatting, and validation workflows.

**Notification** fires when Claude sends notifications like "waiting for input." It's commonly used for custom alerts, logging, and desktop notifications without blocking Claude's workflow.

**Stop** and **SubagentStop** events occur when Claude or subagents finish responding. These hooks can force continuation by returning `{"decision": "block", "reason": "explanation"}`, though this risks infinite loops if not carefully controlled.

## Implementing hooks programmatically

### Basic hello world examples

Start with a simple logging hook to understand the basics:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "echo 'PreToolUse triggered for tool: $CLAUDE_TOOL_NAME' >> ~/.claude/hooks.log"
          }
        ]
      }
    ]
  }
}
```

For Python hooks using UV single-file scripts:

```python
#!/usr/bin/env python3
# /// script
# dependencies = ["json"]
# ///

import json
import sys

try:
    # Read JSON input from stdin
    input_data = json.load(sys.stdin)
    tool_name = input_data.get("tool_name", "Unknown")
    
    print(f"Processing {tool_name} tool")
    sys.exit(0)  # Success
    
except Exception as e:
    print(f"Hook error: {e}", file=sys.stderr)
    sys.exit(1)  # Non-blocking error
```

### Security validation hook

Implement comprehensive security checks for PreToolUse:

```python
#!/usr/bin/env python3
# /// script
# dependencies = ["re"]
# ///

import json
import re
import sys

def is_dangerous_command(command):
    dangerous_patterns = [
        r'rm\s+.*-[rf]',      # rm -rf variants
        r'sudo\s+rm',         # sudo rm commands
        r'chmod\s+777',       # Dangerous permissions
        r'>\s*/etc/',         # Writing to system directories
        r'curl.*\|.*bash',    # Curl pipe to bash
    ]
    
    for pattern in dangerous_patterns:
        if re.search(pattern, command, re.IGNORECASE):
            return True
    return False

def check_sensitive_files(file_path):
    sensitive_patterns = ['.env', '.git/', 'id_rsa', 'credentials']
    return any(pattern in file_path for pattern in sensitive_patterns)

try:
    input_data = json.load(sys.stdin)
    tool_name = input_data.get("tool_name")
    tool_input = input_data.get("tool_input", {})
    
    # Check Bash commands
    if tool_name == "Bash":
        command = tool_input.get("command", "")
        if is_dangerous_command(command):
            print("BLOCKED: Dangerous command detected", file=sys.stderr)
            sys.exit(2)  # Block execution
    
    # Check file operations
    elif tool_name in ["Write", "Edit", "MultiEdit"]:
        file_path = tool_input.get("file_path", "")
        if check_sensitive_files(file_path):
            output = {
                "decision": "block",
                "reason": f"Cannot modify sensitive file: {file_path}"
            }
            print(json.dumps(output))
            sys.exit(0)
            
except Exception as e:
    print(f"Security check failed: {e}", file=sys.stderr)
    sys.exit(1)

sys.exit(0)  # Allow execution
```

### Auto-formatting hook

Implement language-specific formatting after file edits:

```bash
#!/bin/bash
# PostToolUse hook for auto-formatting

# Read JSON input
input=$(cat)
tool_name=$(echo "$input" | jq -r '.tool_name')
file_path=$(echo "$input" | jq -r '.tool_input.file_path // empty')

if [[ -n "$file_path" ]]; then
    case "$file_path" in
        *.py)
            # Python formatting
            ruff check --fix "$file_path" 2>/dev/null
            black "$file_path" 2>/dev/null
            echo "✅ Python file formatted"
            ;;
        *.js|*.ts|*.jsx|*.tsx)
            # JavaScript/TypeScript formatting
            npx prettier --write "$file_path" 2>/dev/null
            npx eslint --fix "$file_path" 2>/dev/null
            echo "✅ JavaScript/TypeScript file formatted"
            ;;
        *.go)
            # Go formatting
            gofmt -w "$file_path"
            echo "✅ Go file formatted"
            ;;
        *.rs)
            # Rust formatting
            rustfmt "$file_path"
            echo "✅ Rust file formatted"
            ;;
    esac
fi

exit 0
```

### Configuration and registration methods

Configure hooks through three methods:

**1. Interactive /hooks command:**
```
/hooks → Select event → Choose matcher → Add command → Save location
```

**2. Manual JSON configuration (.claude/settings.json):**
```json
{
  "hooks": {
    "EventName": [
      {
        "matcher": "ToolPattern",
        "hooks": [
          {
            "type": "command",
            "command": "your-command",
            "timeout": 30,
            "run_in_background": false
          }
        ]
      }
    ]
  }
}
```

**3. Programmatic generation:**
```python
import json
import os

def create_hook_config(event, matcher, command, timeout=60):
    config = {
        "hooks": {
            event: [{
                "matcher": matcher,
                "hooks": [{
                    "type": "command",
                    "command": command,
                    "timeout": timeout
                }]
            }]
        }
    }
    
    # Save to project settings
    settings_path = ".claude/settings.json"
    os.makedirs(".claude", exist_ok=True)
    
    with open(settings_path, "w") as f:
        json.dump(config, f, indent=2)
    
    return config

# Example usage
create_hook_config(
    event="PostToolUse",
    matcher="Write|Edit",
    command="python3 .claude/hooks/format_code.py",
    timeout=30
)
```

### Input/output handling and data flow

Hooks receive JSON input via stdin and control flow through exit codes and stdout/stderr:

**Input structure for PreToolUse:**
```json
{
  "session_id": "abc123",
  "transcript_path": "/path/to/session.jsonl",
  "cwd": "/current/directory",
  "hook_event_name": "PreToolUse",
  "tool_name": "Write",
  "tool_input": {
    "file_path": "/src/main.py",
    "content": "print('Hello')"
  }
}
```

**Advanced JSON output control:**
```python
# Return structured responses for fine-grained control
output = {
    "decision": "approve",  # or "block"
    "reason": "File validated successfully",
    "continue": True,
    "suppressOutput": False
}
print(json.dumps(output))
```

## Advanced hook capabilities

### Context manipulation and filtering

Enhance prompts with project context using UserPromptSubmit:

```python
#!/usr/bin/env python3
# /// script
# dependencies = ["datetime", "pathlib"]
# ///

import json
import sys
from datetime import datetime
from pathlib import Path

def inject_project_context(prompt):
    # Read project configuration
    project_config = Path(".claude/project.json")
    if project_config.exists():
        config = json.loads(project_config.read_text())
    else:
        config = {}
    
    context = f"""
Project Context (Updated: {datetime.now().isoformat()}):
- Architecture: {config.get('architecture', 'microservices')}
- Language: {config.get('language', 'TypeScript')}
- Standards: {config.get('standards', 'REST API, OpenAPI 3.0')}
- Testing: {config.get('testing', 'Jest, 80% coverage required')}

User Request: {prompt}
"""
    return context

try:
    input_data = json.load(sys.stdin)
    original_prompt = input_data.get("prompt", "")
    
    # Inject context
    enhanced_prompt = inject_project_context(original_prompt)
    print(enhanced_prompt)  # This prepends to user's prompt
    
except Exception as e:
    # Don't block on errors
    print(original_prompt)
    
sys.exit(0)
```

### Permission control and tool interception

Implement granular permission systems:

```python
#!/usr/bin/env python3
# /// script
# dependencies = ["fnmatch", "json"]
# ///

import json
import sys
import fnmatch
from pathlib import Path

class PermissionController:
    def __init__(self):
        self.rules = {
            "protected_paths": [
                "/.git/*",
                "*.env",
                "/etc/*",
                "~/.ssh/*"
            ],
            "allowed_commands": [
                "ls", "cat", "grep", "find", "echo"
            ],
            "blocked_patterns": [
                "rm -rf",
                "chmod 777",
                "curl * | bash"
            ]
        }
    
    def check_file_permission(self, file_path):
        for pattern in self.rules["protected_paths"]:
            if fnmatch.fnmatch(file_path, pattern):
                return False, f"Protected path: {pattern}"
        return True, None
    
    def check_command_permission(self, command):
        # Check if command starts with allowed commands
        cmd_parts = command.split()
        if cmd_parts and cmd_parts[0] not in self.rules["allowed_commands"]:
            # Check for blocked patterns
            for pattern in self.rules["blocked_patterns"]:
                if pattern in command:
                    return False, f"Blocked pattern: {pattern}"
        return True, None

controller = PermissionController()

try:
    input_data = json.load(sys.stdin)
    tool_name = input_data.get("tool_name")
    tool_input = input_data.get("tool_input", {})
    
    if tool_name in ["Write", "Edit"]:
        file_path = tool_input.get("file_path", "")
        allowed, reason = controller.check_file_permission(file_path)
        if not allowed:
            print(json.dumps({
                "decision": "block",
                "reason": reason
            }))
            sys.exit(0)
    
    elif tool_name == "Bash":
        command = tool_input.get("command", "")
        allowed, reason = controller.check_command_permission(command)
        if not allowed:
            print(f"BLOCKED: {reason}", file=sys.stderr)
            sys.exit(2)
            
except Exception as e:
    print(f"Permission check error: {e}", file=sys.stderr)
    sys.exit(1)

sys.exit(0)
```

### Subagent interaction and control

Control subagent execution flow:

```python
#!/usr/bin/env python3
# /// script  
# dependencies = ["json"]
# ///

import json
import sys

def should_continue_subagent(session_data):
    """Determine if subagent should continue based on completion criteria"""
    # Check if required tasks are complete
    required_tasks = [
        "tests_written",
        "code_reviewed", 
        "documentation_updated"
    ]
    
    # In real implementation, check actual task status
    completed_tasks = session_data.get("completed_tasks", [])
    
    for task in required_tasks:
        if task not in completed_tasks:
            return True, f"Task incomplete: {task}"
    
    return False, "All tasks completed"

try:
    input_data = json.load(sys.stdin)
    stop_hook_active = input_data.get("stop_hook_active", False)
    
    if not stop_hook_active:
        should_continue, reason = should_continue_subagent(input_data)
        
        if should_continue:
            output = {
                "decision": "block",
                "reason": reason
            }
            print(json.dumps(output))
        
except Exception as e:
    print(f"Subagent control error: {e}", file=sys.stderr)

sys.exit(0)
```

### Integration with external systems

Connect to CI/CD, monitoring, and notification services:

```python
#!/usr/bin/env python3
# /// script
# dependencies = ["requests", "subprocess"]
# ///

import json
import sys
import requests
import subprocess
import os

class ExternalIntegration:
    def __init__(self):
        self.slack_webhook = os.getenv("SLACK_WEBHOOK_URL")
        self.github_token = os.getenv("GITHUB_TOKEN")
        
    def notify_slack(self, message, level="info"):
        if not self.slack_webhook:
            return
            
        color = {"info": "good", "warning": "warning", "error": "danger"}
        
        payload = {
            "attachments": [{
                "color": color.get(level, "good"),
                "text": message,
                "footer": "Claude Code Hook"
            }]
        }
        
        requests.post(self.slack_webhook, json=payload)
    
    def create_github_issue(self, title, body):
        if not self.github_token:
            return
            
        # Get repo info from git remote
        repo_url = subprocess.check_output(
            ["git", "remote", "get-url", "origin"], 
            text=True
        ).strip()
        
        # Extract owner/repo from URL
        import re
        match = re.search(r'github\.com[:/]([^/]+)/(.+?)(?:\.git)?$', repo_url)
        if match:
            owner, repo = match.groups()
            
            url = f"https://api.github.com/repos/{owner}/{repo}/issues"
            headers = {
                "Authorization": f"token {self.github_token}",
                "Accept": "application/vnd.github.v3+json"
            }
            
            data = {"title": title, "body": body}
            response = requests.post(url, headers=headers, json=data)
            return response.json()
    
    def trigger_ci_build(self, branch="main"):
        # Example: Trigger GitHub Actions workflow
        workflow_dispatch_url = "https://api.github.com/repos/owner/repo/actions/workflows/ci.yml/dispatches"
        
        headers = {
            "Authorization": f"token {self.github_token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        data = {
            "ref": branch,
            "inputs": {
                "triggered_by": "claude_code_hook"
            }
        }
        
        requests.post(workflow_dispatch_url, headers=headers, json=data)

# Usage in hook
integrations = ExternalIntegration()

try:
    input_data = json.load(sys.stdin)
    tool_name = input_data.get("tool_name")
    
    if tool_name == "Write" and "test_" in input_data.get("tool_input", {}).get("file_path", ""):
        integrations.notify_slack(
            f"New test file created: {input_data['tool_input']['file_path']}", 
            level="info"
        )
        
except Exception as e:
    print(f"Integration error: {e}", file=sys.stderr)

sys.exit(0)
```

## Real-world use cases and implementation examples

### Automated code review pipeline

Implement comprehensive code review automation:

```python
#!/usr/bin/env python3
# /// script
# dependencies = ["subprocess", "pathlib", "anthropic"]
# ///

import json
import sys
import subprocess
from pathlib import Path

class CodeReviewPipeline:
    def __init__(self):
        self.checks = [
            self.security_scan,
            self.style_check,
            self.complexity_analysis,
            self.test_coverage
        ]
    
    def security_scan(self, file_path):
        """Run security scanning tools"""
        if file_path.endswith('.py'):
            result = subprocess.run(
                ['bandit', '-r', file_path], 
                capture_output=True, 
                text=True
            )
            return result.returncode == 0, result.stdout
        return True, "No security scan for file type"
    
    def style_check(self, file_path):
        """Check code style compliance"""
        if file_path.endswith('.py'):
            result = subprocess.run(
                ['ruff', 'check', file_path],
                capture_output=True,
                text=True
            )
            return result.returncode == 0, result.stdout
        return True, "No style check for file type"
    
    def complexity_analysis(self, file_path):
        """Analyze code complexity"""
        if file_path.endswith('.py'):
            result = subprocess.run(
                ['radon', 'cc', file_path, '-s'],
                capture_output=True,
                text=True
            )
            # Check if complexity is acceptable
            if "F " in result.stdout:  # F = very complex
                return False, "High complexity detected"
            return True, result.stdout
        return True, "No complexity check for file type"
    
    def test_coverage(self, file_path):
        """Ensure tests exist for new code"""
        code_path = Path(file_path)
        test_patterns = [
            code_path.parent / f"test_{code_path.name}",
            code_path.parent / "tests" / f"test_{code_path.name}",
        ]
        
        for test_path in test_patterns:
            if test_path.exists():
                return True, f"Tests found: {test_path}"
        
        return False, "No tests found for this file"
    
    def run_pipeline(self, file_path):
        results = []
        for check in self.checks:
            passed, message = check(file_path)
            results.append({
                "check": check.__name__,
                "passed": passed,
                "message": message
            })
            if not passed:
                return False, results
        return True, results

# Execute pipeline
try:
    input_data = json.load(sys.stdin)
    file_path = input_data.get("tool_input", {}).get("file_path", "")
    
    if file_path:
        pipeline = CodeReviewPipeline()
        passed, results = pipeline.run_pipeline(file_path)
        
        if not passed:
            # Format failure message
            failures = [r for r in results if not r["passed"]]
            message = "Code review failed:\n"
            for failure in failures:
                message += f"- {failure['check']}: {failure['message']}\n"
            
            print(message, file=sys.stderr)
            sys.exit(2)
        else:
            print("✅ All code review checks passed")
            
except Exception as e:
    print(f"Review pipeline error: {e}", file=sys.stderr)
    sys.exit(1)

sys.exit(0)
```

### Test-driven development enforcement

Ensure tests are written before implementation:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "python3 .claude/hooks/tdd_guard.py"
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Write",
        "hooks": [
          {
            "type": "command",
            "command": "if [[ \"$CLAUDE_FILE_PATHS\" =~ test_ ]]; then pytest \"$CLAUDE_FILE_PATHS\" -v; fi",
            "run_in_background": true
          }
        ]
      }
    ]
  }
}
```

### Multi-agent observability system

Track and visualize Claude Code activity across sessions:

```python
#!/usr/bin/env python3
# /// script
# dependencies = ["websockets", "asyncio", "json"]
# ///

import json
import sys
import asyncio
import websockets
from datetime import datetime

class ObservabilityClient:
    def __init__(self, ws_url="ws://localhost:8765"):
        self.ws_url = ws_url
        
    async def send_event(self, event_data):
        try:
            async with websockets.connect(self.ws_url) as websocket:
                await websocket.send(json.dumps(event_data))
        except Exception as e:
            print(f"Failed to send event: {e}", file=sys.stderr)
    
    def track_hook_event(self, input_data):
        event = {
            "timestamp": datetime.now().isoformat(),
            "event_type": input_data.get("hook_event_name"),
            "session_id": input_data.get("session_id"),
            "tool_name": input_data.get("tool_name"),
            "details": {
                "file_path": input_data.get("tool_input", {}).get("file_path"),
                "success": True
            }
        }
        
        # Run async event sending
        asyncio.run(self.send_event(event))

# Track all hook events
try:
    input_data = json.load(sys.stdin)
    client = ObservabilityClient()
    client.track_hook_event(input_data)
except Exception:
    pass  # Don't block on tracking errors

sys.exit(0)
```

## Testing and debugging strategies

### Testing hooks in isolation

Create comprehensive test suites for hooks:

```python
import pytest
import subprocess
import json
import tempfile

class TestSecurityHook:
    def test_blocks_dangerous_commands(self):
        dangerous_input = {
            "tool_name": "Bash",
            "tool_input": {"command": "rm -rf /"}
        }
        
        result = subprocess.run(
            ['python3', '.claude/hooks/security.py'],
            input=json.dumps(dangerous_input),
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 2
        assert "BLOCKED" in result.stderr
    
    def test_allows_safe_commands(self):
        safe_input = {
            "tool_name": "Bash",
            "tool_input": {"command": "ls -la"}
        }
        
        result = subprocess.run(
            ['python3', '.claude/hooks/security.py'],
            input=json.dumps(safe_input),
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0
    
    def test_blocks_sensitive_files(self):
        sensitive_input = {
            "tool_name": "Write",
            "tool_input": {"file_path": ".env"}
        }
        
        result = subprocess.run(
            ['python3', '.claude/hooks/security.py'],
            input=json.dumps(sensitive_input),
            capture_output=True,
            text=True
        )
        
        output = json.loads(result.stdout)
        assert output["decision"] == "block"
```

### Debugging with verbose logging

Implement comprehensive logging for debugging:

```python
#!/usr/bin/env python3
# /// script
# dependencies = ["rich", "pathlib"]
# ///

import json
import sys
import logging
from pathlib import Path
from datetime import datetime
from rich.logging import RichHandler
from rich.console import Console

# Setup rich logging
console = Console()
logging.basicConfig(
    level=logging.DEBUG,
    format="%(message)s",
    handlers=[
        RichHandler(console=console, rich_tracebacks=True),
        logging.FileHandler(Path.home() / ".claude/hooks/debug.log")
    ]
)

logger = logging.getLogger(__name__)

def debug_hook_execution():
    try:
        # Log environment
        logger.debug("=== Hook Execution Started ===")
        logger.debug(f"Environment: {dict(os.environ)}")
        
        # Read and log input
        input_data = json.load(sys.stdin)
        logger.debug(f"Input data: {json.dumps(input_data, indent=2)}")
        
        # Your hook logic here
        tool_name = input_data.get("tool_name")
        logger.info(f"Processing {tool_name} tool")
        
        # Log output
        output = {"status": "success"}
        logger.debug(f"Output: {json.dumps(output, indent=2)}")
        
        print(json.dumps(output))
        
    except Exception as e:
        logger.exception("Hook execution failed")
        sys.exit(1)
    finally:
        logger.debug("=== Hook Execution Completed ===\n")

if __name__ == "__main__":
    debug_hook_execution()
```

### Performance profiling

Monitor hook performance:

```python
#!/usr/bin/env python3
# /// script
# dependencies = ["psutil", "time"]
# ///

import json
import sys
import time
import psutil
import functools

def profile_performance(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Start metrics
        start_time = time.time()
        process = psutil.Process()
        start_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Execute function
        result = func(*args, **kwargs)
        
        # End metrics
        end_time = time.time()
        end_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Log performance
        metrics = {
            "function": func.__name__,
            "execution_time": f"{end_time - start_time:.3f}s",
            "memory_used": f"{end_memory - start_memory:.2f}MB",
            "cpu_percent": process.cpu_percent()
        }
        
        with open("/tmp/hook_performance.jsonl", "a") as f:
            f.write(json.dumps(metrics) + "\n")
        
        return result
    return wrapper

@profile_performance
def process_hook():
    input_data = json.load(sys.stdin)
    # Your hook logic here
    time.sleep(0.1)  # Simulate work
    return {"status": "success"}

try:
    result = process_hook()
    print(json.dumps(result))
except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
    sys.exit(1)

sys.exit(0)
```

## Performance considerations and limitations

### Timeout management

Handle long-running operations gracefully:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write",
        "hooks": [
          {
            "type": "command",
            "command": "python3 .claude/hooks/long_running.py",
            "timeout": 300,  // 5 minutes for complex operations
            "run_in_background": true  // Non-blocking execution
          }
        ]
      }
    ]
  }
}
```

### Resource optimization

Implement efficient hook patterns:

```python
# Cache expensive operations
import functools
import pickle
from pathlib import Path

@functools.lru_cache(maxsize=128)
def get_project_config():
    """Cache project configuration to avoid repeated file reads"""
    config_path = Path(".claude/project.json")
    if config_path.exists():
        return json.loads(config_path.read_text())
    return {}

# Use connection pooling for external services
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

session = requests.Session()
retry = Retry(total=3, backoff_factor=0.3)
adapter = HTTPAdapter(max_retries=retry)
session.mount('http://', adapter)
session.mount('https://', adapter)
```

## Integration with existing development workflows

### IDE integration patterns

Configure multi-IDE workflows:

```bash
# Launch multiple Claude instances for different project areas
#!/bin/bash

# Frontend development
tmux new-session -d -s claude-frontend -c ./frontend 'claude'

# Backend development  
tmux new-session -d -s claude-backend -c ./backend 'claude'

# Testing
tmux new-session -d -s claude-testing -c . 'claude'

# Attach to view all sessions
tmux attach-session -t claude-frontend
```

### CI/CD integration

Implement GitHub Actions integration:

```yaml
name: Claude Code Review

on:
  pull_request:
    types: [opened, synchronize]

jobs:
  claude-review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Claude Code
        run: |
          # Install Claude Code CLI
          curl -fsSL https://claude.ai/install.sh | sh
          
      - name: Configure Hooks
        run: |
          mkdir -p .claude
          echo '{
            "hooks": {
              "PostToolUse": [{
                "matcher": "*",
                "hooks": [{
                  "type": "command",
                  "command": "echo \"::notice::Claude reviewed $CLAUDE_FILE_PATHS\""
                }]
              }]
            }
          }' > .claude/settings.json
          
      - name: Run Claude Review
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: |
          claude -p "Review the changes in this PR for security issues and bugs" \
                 --output-format stream-json
```

### Security best practices

Implement comprehensive security measures:

```python
#!/usr/bin/env python3
# Security-focused hook template

import json
import sys
import os
import hashlib
import hmac

class SecurityValidator:
    def __init__(self):
        self.secret = os.getenv("HOOK_SECRET", "default-secret")
        
    def validate_input(self, data):
        """Validate input data integrity"""
        # Check required fields
        required = ["tool_name", "session_id"]
        for field in required:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")
        
        # Validate session ID format
        session_id = data.get("session_id", "")
        if not session_id or len(session_id) < 10:
            raise ValueError("Invalid session ID")
        
        return True
    
    def sanitize_path(self, path):
        """Prevent path traversal attacks"""
        # Convert to absolute path and check if within project
        abs_path = os.path.abspath(path)
        project_dir = os.getenv("CLAUDE_PROJECT_DIR", os.getcwd())
        
        if not abs_path.startswith(project_dir):
            raise ValueError(f"Path outside project: {path}")
        
        return abs_path
    
    def check_command_injection(self, command):
        """Detect potential command injection"""
        dangerous_chars = [';', '&&', '||', '`', '$', '(', ')']
        for char in dangerous_chars:
            if char in command:
                return False
        return True

# Apply security validation
validator = SecurityValidator()

try:
    input_data = json.load(sys.stdin)
    
    # Validate input
    validator.validate_input(input_data)
    
    # Process based on tool
    tool_name = input_data.get("tool_name")
    
    if tool_name in ["Write", "Edit"]:
        file_path = input_data.get("tool_input", {}).get("file_path", "")
        safe_path = validator.sanitize_path(file_path)
        # Continue with safe path
        
    elif tool_name == "Bash":
        command = input_data.get("tool_input", {}).get("command", "")
        if not validator.check_command_injection(command):
            print("BLOCKED: Potential command injection", file=sys.stderr)
            sys.exit(2)
    
except Exception as e:
    print(f"Security validation failed: {e}", file=sys.stderr)
    sys.exit(1)

sys.exit(0)
```

This comprehensive guide provides everything needed to implement Claude Code hooks effectively, from basic examples to advanced production patterns. The system's power lies in transforming AI assistance into deterministic, automated workflows that enhance development productivity while maintaining security and code quality standards.