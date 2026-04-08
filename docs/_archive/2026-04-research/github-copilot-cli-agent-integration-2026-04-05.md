# GitHub Copilot CLI — Agent Integration Research

**Date:** 2026-04-05
**Researcher:** Claude Research Agent
**Topic:** GitHub Copilot CLI capabilities for potential integration as an agent in claude-mpm

---

## Executive Summary

The `gh copilot` command has undergone a major architectural shift. It is no longer the simple `suggest`/`explain` tool from 2023-2024. As of version 1.0.x, it is a **full agentic AI CLI** — comparable in scope to Claude Code itself. Integration as a claude-mpm agent is feasible but requires careful design due to its startup overhead, MCP server loading behavior, and JSONL output format.

**Key verdict:** Usable as a non-interactive subprocess agent with `--output-format json -s -p <prompt> --allow-all`. Latency is approximately 10-16 seconds end-to-end per call (dominated by MCP server startup, not LLM inference).

---

## 1. Installation Status

```
Tool:     gh copilot (built-in gh command, NOT an extension)
Version:  GitHub Copilot CLI 1.0.18
gh:       v2.86.0 (2026-01-21)
Location: /opt/homebrew/bin/gh
Binary:   Downloaded on first use to ~/.local/share/gh/copilot/
Auth:     Authenticated as bob-duetto via ~/.copilot/config.json
```

The old `gh copilot suggest` / `gh copilot explain` subcommands **no longer exist**. The entire interface has been redesigned.

---

## 2. Available Commands

### Non-Interactive Mode (Critical for Integration)

```bash
gh copilot -p "<prompt>" [flags]
```

This is the primary integration surface. Key flags:

| Flag | Purpose |
|------|---------|
| `-p / --prompt <text>` | Non-interactive prompt (exits after completion) |
| `--output-format json` | JSONL output (one JSON object per line) |
| `--output-format text` | Plain text output (default) |
| `-s / --silent` | Suppress stats, output only agent response |
| `--allow-all` | Enable all permissions (tools, paths, URLs) |
| `--allow-all-tools` | Auto-approve all tool calls (env: `COPILOT_ALLOW_ALL=1`) |
| `--no-ask-user` | Autonomous mode, no interactive questions |
| `--model <name>` | Select specific model |
| `--allow-tool='shell(cmd)'` | Restrict to specific shell commands |
| `--available-tools=shell` | Restrict to specific tool types |
| `--add-dir <path>` | Grant file system access to directory |
| `--share=<path>` | Save session to markdown after completion |
| `--stream on|off` | Enable/disable streaming |

### Interactive Mode

Full TUI with `/model`, `/fleet`, `/tasks`, `/research`, `/delegate`, `/pr`, `/compact`, `/rewind` commands. Not relevant for programmatic integration.

### Subcommands

```
gh copilot login      # Authenticate
gh copilot init       # Initialize AGENTS.md instructions for repo
gh copilot update     # Download latest version
gh copilot plugin     # Manage plugins
gh copilot version    # Show version
```

---

## 3. Available Models

From the configuration documentation, the following models are available:

**Claude models:**
- `claude-sonnet-4.6` (appears to be default)
- `claude-sonnet-4.5`
- `claude-haiku-4.5`
- `claude-opus-4.6`
- `claude-opus-4.6-fast`
- `claude-opus-4.5`
- `claude-sonnet-4`

**GPT models:**
- `gpt-5.4`
- `gpt-5.3-codex`
- `gpt-5.2-codex`
- `gpt-5.2`
- `gpt-5.1`
- `gpt-5.4-mini`
- `gpt-5-mini`
- `gpt-4.1`

**Default model observed in testing:** `claude-haiku-4.5` (set in local config)

**Plan required:** GitHub Copilot subscription required. The `result` event shows `"premiumRequests": 1` per invocation, confirming these are Copilot-billed requests.

---

## 4. Non-Interactive Usage (Programmatic Integration)

### Basic Pattern

```bash
gh copilot -p "Your prompt here" --allow-all --output-format json -s
```

Returns JSONL to stdout. Exit code 0 on success.

### Environment Variable Alternative

```bash
COPILOT_ALLOW_ALL=1 gh copilot -p "prompt" --output-format json -s
```

### Minimal Working Example

```bash
gh copilot \
  -p "List files in current directory" \
  --allow-tool='shell(ls)' \
  --no-ask-user \
  --output-format json \
  -s
```

---

## 5. JSON Output Format

The `--output-format json` flag produces **JSONL** (newline-delimited JSON). Each line is an independent JSON object with a `type` field.

### Event Types Observed

| Event Type | Description |
|-----------|-------------|
| `session.mcp_server_status_changed` | MCP server connecting (ephemeral) |
| `session.mcp_servers_loaded` | All MCP servers loaded |
| `session.tools_updated` | Model selected, tools ready |
| `user.message` | User prompt echoed back |
| `assistant.turn_start` | LLM turn beginning |
| `assistant.reasoning_delta` | Chain-of-thought tokens (ephemeral) |
| `assistant.reasoning` | Complete reasoning block |
| `assistant.message_delta` | Streaming response tokens (ephemeral) |
| `assistant.message` | Complete response turn |
| `tool.execution_start` | Tool call initiated |
| `tool.execution_complete` | Tool call finished |
| `assistant.turn_end` | LLM turn complete |
| `result` | Session summary with exit code and usage |

### Parsing the Final Response

```python
import subprocess, json

def call_copilot(prompt: str) -> str:
    result = subprocess.run(
        ["gh", "copilot", "-p", prompt, "--allow-all", 
         "--output-format", "json", "-s", "--no-ask-user"],
        capture_output=True, text=True
    )
    
    final_response = ""
    for line in result.stdout.strip().split('\n'):
        try:
            obj = json.loads(line)
            # Last non-empty assistant.message is the final response
            if obj.get('type') == 'assistant.message':
                content = obj['data']['content']
                if content:
                    final_response = content
        except json.JSONDecodeError:
            pass
    
    return final_response

# Usage statistics
def get_usage(stdout: str) -> dict:
    for line in stdout.strip().split('\n'):
        try:
            obj = json.loads(line)
            if obj.get('type') == 'result':
                return obj.get('usage', {})
        except: pass
    return {}
```

### Example result Event

```json
{
  "type": "result",
  "timestamp": "2026-04-06T05:04:15.204Z",
  "sessionId": "886e9585-...",
  "exitCode": 0,
  "usage": {
    "premiumRequests": 1,
    "totalApiDurationMs": 5687,
    "sessionDurationMs": 17521,
    "codeChanges": {
      "linesAdded": 0,
      "linesRemoved": 0,
      "filesModified": []
    }
  }
}
```

---

## 6. Latency Measurements

All tests run on macOS Darwin 25.3.0 with local MCP servers loading.

| Test | Session Duration | API Duration | Notes |
|------|----------------|--------------|-------|
| Simple math ("2+2") | ~17.5s | 5.7s | With all MCP servers (7 servers) |
| Shell command (date) | ~12.9s | 4.8s | With `--allow-tool` (no MCP servers) |
| Disk usage list | ~16.0s | ~5s | Default config |

**Breakdown:**
- MCP server startup: 6-10s (7 servers in local config)
- LLM inference: 3-6s (haiku-4.5)
- Total round-trip: 12-18s

**Optimization options:**
- `--disable-builtin-mcps` reduces startup (removes github-mcp-server)
- Using `--allow-tool` instead of `--allow-all` may bypass some MCP loading
- The local claude-mpm environment has many MCP servers (kuzu-memory, mcp-ticketer, slack-user-proxy, gworkspace-mcp, mpm-messaging, mcp-vector-search) which add significant startup time

**Important finding:** Most of the latency is fixed overhead (process startup + MCP initialization), not inference. For frequent calls, a persistent session (interactive mode via ACP) would be dramatically faster.

---

## 7. Tool Execution Capabilities

The agent can execute tools natively:

### Shell Execution

```bash
# Allow specific commands
--allow-tool='shell(echo)'
--allow-tool='shell(git:*)'    # all git subcommands
--allow-tool='shell(date)'

# Allow all shell
--allow-all-tools

# Deny specific commands
--deny-tool='shell(git push)'
```

**Tested:** Shell execution works. The agent runs the command and reports results. It does NOT just suggest commands — it executes them when tools are allowed.

### File Operations

The agent has read/write file tools. By default, file access is restricted to the current directory. Use `--add-dir` to expand scope.

### No Dry-Run/Suggestion-Only Mode

Unlike the old `gh copilot suggest` command, there is no "suggest only" mode. The agent either runs tools (if permitted) or does not. It cannot return commands for you to run separately in a structured way — it just reports what it did in natural language.

---

## 8. Agent Client Protocol (ACP)

The `--acp` flag starts the CLI as an **Agent Client Protocol server**. This is a stdio-based protocol that allows a host application to communicate with the Copilot agent programmatically.

```bash
gh copilot --acp  # Starts ACP server on stdin/stdout
```

This is the most promising integration mechanism for claude-mpm, but requires implementing the ACP client protocol. The protocol specification is at `https://docs.github.com/copilot/how-tos/copilot-cli`.

**Assessment:** ACP mode would eliminate the startup overhead since a single long-lived process could handle multiple requests. This is the production-grade integration path.

---

## 9. MCP Server Integration (Interesting Note)

When running in the claude-mpm environment, `gh copilot` automatically picked up the workspace's `.mcp.json` or `mcp-config.json` and connected to all local MCP servers:

```
kuzu-memory: connected
mcp-ticketer: connected
mcp-skillset: FAILED
slack-user-proxy: connected
gworkspace-mcp: connected
mpm-messaging: connected
mcp-vector-search: connected
github-mcp-server: connected (builtin)
```

This means a Copilot CLI agent running within claude-mpm would automatically have access to the same MCP tools! The `--disable-builtin-mcps` flag removes the github-mcp-server and `--disable-mcp-server` removes specific servers.

---

## 10. Model Capabilities and Plan Requirements

| Model | Type | Notes |
|-------|------|-------|
| `claude-haiku-4.5` | Fast/cheap | Default in local config |
| `claude-sonnet-4.6` | Balanced | Recommended for complex tasks |
| `claude-opus-4.6` | Most capable | Highest cost |
| `gpt-5.4` | OpenAI flagship | Available via Copilot |
| `gpt-5.4-mini` | OpenAI fast | Available via Copilot |

**Plan requirements:**
- GitHub Copilot Individual or Team/Enterprise subscription required
- Each `-p` invocation counts as 1 premium request
- `claude-haiku-4.5` is likely lowest-cost model available
- GPT-4o is NOT listed; GPT-5.x models are listed (suggesting this is mid-2025+ Copilot catalog)

---

## 11. Integration Patterns for claude-mpm

### Pattern A: Subprocess Agent (Simple, Works Now)

```python
# agent definition snippet
import subprocess, json

class CopilotAgent:
    def execute(self, prompt: str, model: str = "claude-haiku-4.5") -> str:
        result = subprocess.run(
            [
                "gh", "copilot",
                "-p", prompt,
                "--model", model,
                "--allow-all",
                "--no-ask-user",
                "--output-format", "json",
                "-s",
                "--disable-builtin-mcps",  # faster startup
            ],
            capture_output=True, text=True, timeout=60
        )
        
        final_response = ""
        for line in result.stdout.strip().split('\n'):
            try:
                obj = json.loads(line)
                if obj.get('type') == 'assistant.message' and obj['data']['content']:
                    final_response = obj['data']['content']
            except: pass
        
        return final_response
```

**Pros:** Simple, works immediately, no new protocol to implement
**Cons:** 12-18 second overhead per call due to process startup + MCP loading

### Pattern B: ACP Long-Lived Process (Production)

```python
# Start once, reuse for many requests
process = subprocess.Popen(
    ["gh", "copilot", "--acp", "--allow-all", "--no-ask-user"],
    stdin=subprocess.PIPE, stdout=subprocess.PIPE
)
# Send multiple prompts to same process via ACP protocol
```

**Pros:** Eliminates startup overhead, single auth session
**Cons:** Requires ACP protocol implementation

### Pattern C: Claude-MPM Agent YAML Definition

```yaml
agents:
  - name: "copilot"
    category: "implementation"
    role: "GitHub Copilot AI Agent"
    description: "Delegates tasks to GitHub Copilot CLI for execution"
    
    capabilities:
      - "Execute shell commands with LLM guidance"
      - "GitHub-specific operations (PRs, issues, code review)"
      - "Code generation with GPT-5 and Claude models"
      - "Multi-model task routing"
    
    constraints:
      - "Requires GitHub Copilot subscription"
      - "12-18s latency per call"
      - "Counts as premium Copilot requests"
      - "Cannot run without active GitHub auth"
```

---

## 12. Key Questions Answered

**Can we pipe prompts to `gh copilot` and get structured output?**
Yes. Use `--output-format json -s` to get JSONL. Parse `assistant.message` events for the response and `result` for exit code and usage stats.

**What's the latency like?**
12-18 seconds total per invocation in the claude-mpm environment (dominated by MCP server startup). Pure LLM inference is 3-6 seconds.

**Can it execute commands or only suggest them?**
It executes commands when tools are permitted. There is no "suggest-only" mode in the current version. The old `gh copilot suggest` behavior is gone.

**Is there a `--json` or machine-readable output mode?**
Yes: `--output-format json` produces JSONL. This is well-structured and parseable.

**Can we use it non-interactively (no TTY required)?**
Yes. `-p <prompt> --allow-all --no-ask-user` works without a TTY. Tested successfully in subprocess.

**What model does it use? Is GPT-4o included?**
Default appears to be `claude-haiku-4.5` (per local config). Available models include Claude Sonnet/Haiku/Opus and GPT-5.x series. GPT-4o is NOT listed — the catalog appears to be 2025 models.

---

## 13. Risks and Limitations

1. **Copilot subscription required:** Every call consumes Copilot premium requests. Integrating as a general-purpose claude-mpm agent would incur costs.

2. **Startup latency:** 12-18s per call is high for interactive workflows. Best suited for async/background tasks.

3. **No streaming to parent process:** The `--output-format json` mode buffers all output; the `-s` flag means you get nothing until completion.

4. **Auth dependency:** Requires `bob-duetto` GitHub account to be authenticated. Will fail in CI without credentials.

5. **MCP server conflict:** Running gh copilot within claude-mpm will pick up the claude-mpm workspace MCP servers, which could cause unexpected behavior or slow startup.

6. **Tool approval interactivity:** Without `--allow-all` or `--no-ask-user`, the process will pause waiting for interactive approval — hanging indefinitely in subprocess mode.

7. **Model cost unpredictability:** Different models consume different amounts of Copilot quota. Opus models may exhaust quotas quickly.

---

## 14. Recommendations

**For immediate integration (low effort):**
- Create a `CopilotSubprocessAgent` that wraps `gh copilot -p ... --allow-all --no-ask-user --output-format json -s`
- Use for async/background tasks where latency is acceptable
- Add `--disable-builtin-mcps` flag to reduce startup by ~2s
- Consider `--model claude-haiku-4.5` for cost efficiency

**For production integration (medium effort):**
- Implement ACP (Agent Client Protocol) client to maintain persistent connection
- This would reduce per-call latency to ~3-6s (inference only)
- Reference: https://docs.github.com/copilot/how-tos/copilot-cli

**Use cases where Copilot CLI adds unique value:**
- GitHub-specific operations (PR creation, code review, issue triage) — the builtin `github-mcp-server` gives direct GitHub API access
- Multi-model routing (when you want GPT-5.x for specific tasks)
- Delegating to `/research` mode for deep GitHub codebase searches

**Use cases where Copilot CLI is NOT advantageous:**
- General coding tasks (claude-mpm already does this better natively)
- High-frequency/low-latency tasks (too slow)
- Tasks that don't need GitHub API access

---

## 15. Command Syntax Reference

```bash
# Basic non-interactive call
gh copilot -p "prompt" --allow-all --output-format json -s

# With model selection
gh copilot -p "prompt" --model claude-sonnet-4.6 --allow-all --output-format json -s

# Minimal shell task (fastest, avoids MCP loading)
gh copilot -p "prompt" --allow-tool='shell(cmd)' --no-ask-user --output-format json -s

# With env var (no --allow-all flag needed)
COPILOT_ALLOW_ALL=1 gh copilot -p "prompt" --output-format json -s

# ACP server mode (long-lived process)
gh copilot --acp --allow-all --no-ask-user

# Save session to file
gh copilot -p "prompt" --allow-all --share=./session.md

# Restrict to specific tools
gh copilot -p "prompt" --allow-tool='shell(git:*)' --deny-tool='shell(git push)'

# Fastest startup (no MCP servers at all)
gh copilot -p "prompt" --allow-all --disable-builtin-mcps --no-ask-user --output-format json -s
```

---

## Appendix: JSON Stream Sample

```jsonl
{"type":"session.tools_updated","data":{"model":"claude-haiku-4.5"}}
{"type":"user.message","data":{"content":"Run: echo TEST_OUTPUT_123",...}}
{"type":"assistant.turn_start","data":{"turnId":"0","interactionId":"..."}}
{"type":"assistant.message","data":{"messageId":"...","content":"","toolRequests":[{"toolCallId":"...","name":"bash","arguments":{"command":"echo TEST_OUTPUT_123"}}],...}}
{"type":"tool.execution_start","data":{"toolCallId":"...","toolName":"bash","arguments":{"command":"echo TEST_OUTPUT_123","description":"..."}}}
{"type":"tool.execution_complete","data":{"toolCallId":"...","model":"claude-haiku-4.5","success":true,...}}
{"type":"assistant.turn_end","data":{"turnId":"0"}}
{"type":"assistant.turn_start","data":{"turnId":"1",...}}
{"type":"assistant.message","data":{"messageId":"...","content":"Done. Output: `TEST_OUTPUT_123`","toolRequests":[],...}}
{"type":"assistant.turn_end","data":{"turnId":"1"}}
{"type":"result","exitCode":0,"usage":{"premiumRequests":1,"totalApiDurationMs":4797,"sessionDurationMs":12902,...}}
```
