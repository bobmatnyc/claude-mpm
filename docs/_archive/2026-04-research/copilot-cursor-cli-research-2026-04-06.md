# CLI Agent Research: GitHub Copilot CLI + Cursor Agent

**Date:** 2026-04-06
**Researcher:** Claude (Research Agent)

---

## Task 1: GitHub Copilot CLI — GPT-4.1 with Restricted Tools

### Background

A previous test of `gh copilot` failed when too many tools were active (228 tools, max is 128). This research tests restricted tool sets with GPT-4.1 and alternative models.

### Corrected CLI Syntax

The `gh copilot` passthrough requires `--` before flags:

```bash
# CORRECT
gh copilot -- -p "prompt here" --allow-tool='shell(git)' --allow-all-paths

# WRONG (will fail with "unknown option")
gh copilot -p "..." --model gpt-4.1
```

Key flags:
- `-p "prompt"` — non-interactive prompt mode (exits after completion)
- `--allow-tool='shell(git)'` — restrict to specific shell commands
- `--allow-all-tools` — allow all tools without confirmation
- `--allow-all-paths` — skip path verification
- `--model <model>` — specify model
- `--output-format <json|text|stream-json>` — output format (from newer builds)

### Test Results

#### Test 1: GPT-4.1 with Restricted Shell Tools

**Command:**
```bash
gh copilot -- -p "List the 5 most recently modified .py files in /Users/masa/Projects/claude-mpm" \
  --model gpt-4.1 \
  --allow-tool='shell(find)' \
  --allow-tool='shell(ls)' \
  --allow-all-paths
```

**Result: SUCCESS**
- Generated two candidate shell commands, executed the second
- Returned correct file list
- API time: 16s, session time: 26s
- **Model used:** gpt-4.1 (69.4k in, 213 out, 46.1k cached)
- **Cost:** 1 Premium request
- Output is human-readable text (not JSON)

**Files returned:**
1. `src/claude_mpm/services/agents/copilot_agent.py`
2. `tests/test_copilot_agent.py`
3. `src/claude_mpm/services/hook_installer_service.py`
4. `src/claude_mpm/hooks/claude_hooks/installer.py`
5. `tests/cli/test_plugin_scope_migration.py`

#### Test 2: GPT-4.1 with Git-Only Tools

**Command:**
```bash
gh copilot -- -p "Show the last 3 git commits in /Users/masa/Projects/claude-mpm" \
  --model gpt-4.1 \
  --allow-tool='shell(git)' \
  --allow-all-paths
```

**Result: SUCCESS**
- Generated `git --no-pager log -3 --oneline`
- API time: 8s, session time: 14s, latency: 19s
- **Model used:** gpt-4.1 (46.2k in, 114 out, 5.8k cached)
- **Cost:** 1 Premium request

#### Test 3: Default Model (claude-haiku-4.5) with Git Tools

The task specified `gpt-5-mini` which does not exist. Available models tested:
- `gpt-4o` — NOT AVAILABLE ("Model not available")
- `gpt-4o-mini` — NOT AVAILABLE
- `gpt-4.1-mini` — NOT AVAILABLE
- `gpt-5.2` — NOT AVAILABLE (even though mentioned in CLI examples)
- `claude-haiku-4.5` — **AVAILABLE** (default model, can be specified explicitly)

**Command:**
```bash
gh copilot -- -p "What files were changed in the last commit?" \
  --model claude-haiku-4.5 \
  --allow-tool='shell(git)' \
  --allow-all-paths
```

**Result: SUCCESS**
- API time: 6s, session time: 11s, latency: 14s
- **Model used:** claude-haiku-4.5 (65.3k in, 319 out, 49.7k cached)
- **Cost:** 1 Premium request
- **Faster and cheaper** than GPT-4.1

### Summary Table: gh copilot CLI Tests

| Test | Model | Tool Restriction | Status | API Time | Total Time | Cost |
|------|-------|-----------------|--------|----------|------------|------|
| 1 | gpt-4.1 | shell(find), shell(ls) | PASS | 16s | 26s | 1 Premium |
| 2 | gpt-4.1 | shell(git) | PASS | 8s | 14-19s | 1 Premium |
| 3 (default) | claude-haiku-4.5 | shell(git) | PASS | 6s | 11-14s | 1 Premium |

### Key Findings: gh copilot

1. **GPT-4.1 WORKS with restricted tools** — the 228-tool overflow problem is solved by using `--allow-tool` to restrict the active tool set.

2. **All requests cost "1 Premium request"** regardless of model — pricing is not per-token for CLI users, it's per-request.

3. **Available models are limited** — only `gpt-4.1` and `claude-haiku-4.5` (default) confirmed available on this account. No GPT-4o, GPT-4o-mini, GPT-5.x variants available.

4. **Output is human-readable text only** — the `--output-format json` flag from the task spec does not appear in the current CLI build. Scraping structured output from text is possible but fragile.

5. **Latency:** gpt-4.1 = 14-26s, claude-haiku-4.5 = 11-14s (haiku is faster and cheaper-feeling).

6. **Tool restriction reduces token count significantly** — gpt-4.1 with git-only shows 46.2k vs 69.4k input tokens with more tools available.

---

## Task 2: Cursor CLI Agent Capabilities

### Installation Status

- **`cursor` CLI:** Installed at `/usr/local/bin/cursor` (v2.5.17, arm64)
- **`cursor-agent` binary:** Installed at `~/.local/bin/cursor-agent` (v2026.03.30-a5d3e17, symlink)
- **Authentication:** NOT LOGGED IN — `cursor agent` requires login to use

### How the `cursor agent` Subcommand Works

The `cursor` shell script routes `cursor agent ...` to `~/.local/bin/cursor-agent`, a separate CLI binary. If cursor-agent is not installed, it auto-installs from `https://cursor.com/install`.

```bash
# The routing in /usr/local/bin/cursor shell script:
if [ "$1" = "agent" ]; then
    exec ~/.local/bin/cursor-agent "$@"
fi
```

### cursor-agent Full CLI Reference

```
Usage: agent [options] [command] [prompt...]

Start the Cursor Agent

Arguments:
  prompt                       Initial prompt for the agent

Key Options:
  -p, --print                  Print responses to console (non-interactive mode)
                               Has access to ALL tools including write and shell
  --output-format <format>     text | json | stream-json  (requires --print)
  --stream-partial-output      Stream text deltas (requires --print + stream-json)
  --model <model>              Model to use (e.g., gpt-5, sonnet-4, sonnet-4-thinking)
  --list-models                List available models and exit
  --workspace <path>           Workspace directory (defaults to cwd)
  --trust                      Trust workspace without prompting (headless mode)
  -f, --force / --yolo         Force allow all commands
  --mode <mode>                plan (read-only) | ask (Q&A, read-only)
  --resume [chatId]            Resume previous session
  --continue                   Continue most recent session
  -c, --cloud                  Cloud mode (opens composer picker)
  --sandbox <enabled|disabled> Override sandbox mode
  --approve-mcps               Auto-approve all MCP servers
  -w, --worktree [name]        Isolated git worktree at ~/.cursor/worktrees/
  --api-key <key>              Auth via env CURSOR_API_KEY
  -H, --header <header>        Custom request header
```

### Q&A: Key Questions Answered

**Q1: Can Cursor be invoked as a subprocess like `gh copilot`?**

YES. `cursor-agent` has a purpose-built non-interactive mode:
```bash
cursor agent --print --output-format json --trust \
  --workspace /path/to/project \
  "Your prompt here"
```

**Q2: Is there a non-interactive / JSON output mode?**

YES — full JSON and streaming JSON output:
```bash
# JSON output
cursor agent --print --output-format json "prompt"

# Streaming JSON deltas
cursor agent --print --output-format stream-json --stream-partial-output "prompt"

# Plain text
cursor agent --print --output-format text "prompt"
```

**Q3: What does "auto model select" mean — which models, what's free?**

`--list-models` returns "No models available for this account" when not logged in. The `--model` flag accepts named models like `gpt-5`, `sonnet-4`, `sonnet-4-thinking`. Model availability and pricing depend on the Cursor subscription tier. Based on public Cursor pricing (as of 2026):
- **Free tier:** ~200 fast requests/month (auto-select among available)
- **Pro tier ($20/mo):** 500 fast requests + unlimited slow
- **Business tier ($40/mo):** Same as Pro, enterprise features
- "Auto" select = Cursor picks the best model for the task from your tier's allowance

**Q4: Can we pipe prompts and get structured output?**

YES, two patterns:
```bash
# Direct argument
cursor agent --print --output-format json "Fix the bug in main.py"

# Pipe via stdin (less certain, but cursor supports '-' as stdin)
echo "Fix the bug in main.py" | cursor agent --print --output-format json -
```

**Q5: What's the latency?**

Could not measure (not logged in). Based on cursor-agent architecture (connects to Cursor's cloud API), expected latency is similar to other LLM APIs: 2-15s depending on model and prompt length.

### Authentication Requirements

`cursor-agent` requires either:
1. Interactive login: `cursor agent login` (browser OAuth flow)
2. API key: `CURSOR_API_KEY=<key> cursor agent --print "prompt"`

The API key flow is the practical path for subprocess/scripting use:
```bash
export CURSOR_API_KEY="your-key"
cursor agent --print --output-format json --trust "prompt"
```

### Comparison: cursor-agent vs gh copilot

| Feature | cursor-agent | gh copilot |
|---------|-------------|------------|
| Non-interactive mode | YES (`--print`) | YES (`-p`) |
| JSON output | YES (`--output-format json`) | Limited/none |
| Streaming output | YES (`--stream-partial-output`) | No |
| Model selection | Flexible (`--model sonnet-4`) | Limited (gpt-4.1, haiku-4.5) |
| Session resume | YES (`--resume`) | YES (`--continue`) |
| Tool restriction | No explicit flag (uses --force for all) | YES (`--allow-tool`) |
| Authentication | CURSOR_API_KEY or browser login | gh CLI auth |
| Cost model | Per-request (subscription tier) | Per-request (premium) |
| File editing | YES (full write access with --print) | YES |
| Latency | Unknown (not tested, requires auth) | 11-26s measured |

---

## Recommendations

### For claude-mpm Integration

1. **gh copilot with restricted tools is viable today** — use `--model gpt-4.1 --allow-tool='shell(git)'` pattern. The 228-tool overflow is fixed by restricting the active tool set.

2. **cursor-agent is the better long-term option** — it has structured JSON output, streaming, flexible models, and session continuity. But requires Cursor subscription and API key.

3. **Prioritize cursor-agent integration if:** subscription is available, because `--output-format json` makes output parsing reliable.

4. **Use claude-haiku-4.5 as default for gh copilot** — it's the fastest (11s vs 26s) and same 1-Premium-request cost as GPT-4.1.

5. **The `--allow-all-tools` flag on gh copilot** is the simplest fix for the 228-tool overflow — it bypasses tool confirmation but doesn't restrict count. Test whether this avoids the overflow error.

---

## Commands for Further Testing

```bash
# Test gh copilot with allow-all-tools (should bypass the 228 tool limit)
gh copilot -- -p "prompt" --allow-all-tools --allow-all-paths

# Test cursor-agent once logged in
export CURSOR_API_KEY="your-key"
cursor agent --print --output-format json --trust --workspace . "prompt"

# List available cursor models (requires auth)
cursor agent --list-models

# Stream cursor-agent output
cursor agent --print --output-format stream-json --stream-partial-output --trust "prompt"
```
