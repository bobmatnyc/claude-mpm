# cursor-agent and gh copilot: Latency Tests & Daemon Mode Research

**Date**: 2026-04-05
**Repo**: /Users/masa/Projects/claude-mpm

---

## Task 1: cursor-agent Latency Tests

### Environment

- **Tool**: cursor-agent v2026.03.30-a5d3e17
- **Model**: Composer 2 Fast
- **Workspace**: /Users/masa/Projects/claude-mpm
- **Flags**: `--print --output-format stream-json --trust`

### Test Results

| Test | Task | Duration | Model | Quality |
|------|------|----------|-------|---------|
| Test 1 | List 5 most recently modified Python files | **39,769 ms (~40s)** | Composer 2 Fast | High — correct files, used workspace glob index |
| Test 2 | Show last 3 git commits with changed files | **107,504 ms (~108s)** | Composer 2 Fast | Moderate — shell commands blocked, fell back to reading `.git/` files directly |
| Test 3 | "What model are you? Reply in one line." | ~5s (not timed formally) | Composer 2 Fast | Correct: "I'm Composer, a language model built by Cursor." |

### Test 1 Detail

Duration: **39.8 seconds** (from `duration_ms` in stream-json result).

The agent:
1. Attempted a shell `find | xargs stat | sort` pipeline
2. Shell was blocked/rejected (sandbox restriction)
3. Fell back to workspace glob index (`**/*.py` ordered by mtime)
4. Returned correct answer with 5 files

Correct files returned:
1. `src/claude_mpm/services/agents/external_agents.py`
2. `src/claude_mpm/services/agents/cursor_agent.py`
3. `src/claude_mpm/services/agents/copilot_agent.py`
4. `tests/test_copilot_agent.py`
5. `src/claude_mpm/services/hook_installer_service.py`

### Test 2 Detail

Duration: **107.5 seconds (~1m48s)**.

The agent hit a significant hurdle: shell execution was entirely blocked (sandbox mode, no `git` commands allowed). It then:
1. Tried to parse git objects in Python
2. Read `.git/refs/heads/main` and `.git/logs/HEAD` directly
3. Produced the correct commit hashes and subjects
4. Could not reliably list changed files per commit (no `git diff`)

Result was accurate for commit metadata but incomplete for file lists. This inflated latency significantly due to multiple failed attempts and fallback strategies.

### Test 3 Detail

Model reports itself as **"Composer"** (Cursor's proprietary model, not a third-party LLM). The CLI init message confirms model as `Composer 2 Fast`.

### Observations

- **Cold start overhead is significant**: ~15-40s just for process init + first model call
- **Sandbox mode blocks many shell commands** by default (`find`, `git`, `stat`, etc.)
- The `--trust` flag did not fully disable sandboxing in these tests
- Test 2's 108s duration is partly due to multiple retry strategies after shell blocking
- Model quality is good when tools work; degrades gracefully when blocked

---

## Task 2: Daemon Mode Research

### cursor-agent: No Daemon/Server Mode

**Finding**: cursor-agent has no daemon, server, ACP, or persistent listener mode.

From `cursor-agent --help`:

Commands available:
- `install-shell-integration` / `uninstall-shell-integration`
- `login` / `logout`
- `mcp` (manage MCP servers)
- `status|whoami`
- `models`
- `about`
- `update`
- `create-chat`
- `generate-rule`
- `agent` (the main command)
- `ls` / `resume`

No `server`, `daemon`, `serve`, `acp`, `socket`, or `listen` subcommands exist.

**Grep for daemon/socket keywords**: Only matched `--approve-mcps` (MCP server management), not a process listener.

**Closest equivalent**: The `--continue` and `--resume` flags reuse a prior chat session's context (JSONL transcript), but still spawn a **new process per invocation**. There is no warm persistent process.

**Cursor's actual "background agent" feature**: Runs in a cloud-hosted Ubuntu VM (triggered via `Ctrl+E` in the UI or `&` prefix in CLI messages). This is a cloud execution model, not a local daemon.

### gh copilot: ACP Mode Exists (Public Preview Jan 2026)

**Finding**: `gh copilot` has explicit `--acp` support, which is the closest thing to a daemon/server mode for either tool.

#### What --acp Does

From `gh copilot --help`:
```
--acp    Start as Agent Client Protocol server
```

From official docs (https://docs.github.com/en/copilot/reference/copilot-cli-reference/acp-server):

- **Protocol**: Agent Client Protocol (ACP) — described as "LSP for AI agents"
- **Transport**: NDJSON over stdio (default) or TCP (`--acp --port [number]`)
- **Client API**: JSON-RPC
- **Public Preview**: Announced January 28, 2026

When running with `--acp`, Copilot CLI becomes a **persistent server process** that accepts connections from IDEs, editors, and automation tools. It does not exit after each request — it stays alive and handles multiple sessions.

#### ACP Architecture

```
Client (IDE/tool)  <--NDJSON/stdio or TCP--> gh copilot --acp [server]
                                                 |
                                          Model inference
                                          Tool execution
                                          Session state
```

The process is spawned once:
```
["gh", "copilot", "--acp", "--stdio"]
stdio: ["pipe", "pipe", "inherit"]
```

Then clients send JSON-RPC messages over stdin, receive responses over stdout. Multiple sessions can be created via `newSession()`.

#### ACP Latency Implications

**Does it eliminate startup overhead?** Partially yes, with a caveat:

- The process itself starts once — no per-request process spawn (~saves 2-5s Node.js startup)
- The LLM inference latency (network round-trip to GitHub's model API) remains
- Known limitation: `--acp` mode currently returns `"loadSession": false`, meaning **session state is not persisted/resumed** between ACP sessions (open issue #936). Each new `newSession()` call starts fresh.

No public benchmarks exist for ACP mode latency vs cold start.

#### ACP Ecosystem

ACP is an open standard with 30+ compatible agents including Claude, Gemini CLI, Goose, Cline, Codex, and Copilot. This makes `gh copilot --acp` interoperable with any ACP-compatible client.

Third-party headless ACP client: [acpx](https://github.com/openclaw/acpx) — supports stdin prompts, session history.

### Answer to Key Questions

**1. Can either run as a persistent process that accepts requests over stdin/socket?**

- **cursor-agent**: No. Each invocation is a fresh process. `--continue`/`--resume` reuse context but not the process.
- **gh copilot**: Yes, via `--acp`. Supports stdio or TCP transport. Public preview as of January 2026.

**2. What is ACP? Does copilot support `--acp`?**

ACP (Agent Client Protocol) is a JSON-RPC protocol over stdio/TCP for standardized agent-client communication, analogous to LSP for language servers. Yes, `gh copilot --acp` is supported and in public preview.

**3. Would daemon mode eliminate the 15-26s startup overhead?**

For `gh copilot --acp`: Eliminates process-spawn overhead (Node.js startup ~2-5s). Does **not** eliminate LLM inference latency. Net improvement depends on how much of observed latency is process spawn vs model call.

For cursor-agent: Not applicable — no daemon mode exists.

**4. What's the expected latency in daemon/ACP mode vs cold start?**

No official benchmarks published. Reasonable estimate:
- Cold start overhead (process spawn + auth init): 2-8s
- LLM inference + tool execution: 10-100s depending on task complexity
- ACP warm process savings: ~2-8s per request (eliminates cold start only)

---

## Summary

| Dimension | cursor-agent | gh copilot |
|-----------|-------------|------------|
| Daemon/server mode | None | `--acp` (public preview Jan 2026) |
| Transport | N/A | stdio (default) or TCP |
| Protocol | N/A | ACP (JSON-RPC / NDJSON) |
| Session persistence in daemon | N/A | No (loadSession=false, open issue) |
| Cold start latency observed | ~15-40s per test | Not tested |
| Model | Composer 2 Fast (proprietary) | GitHub Copilot model |
| Sandbox blocks shell commands | Yes (blocks git, find, etc.) | Unknown |

**Recommendation**: For applications needing low-overhead repeated invocations, `gh copilot --acp` is the only option with a persistent process model. cursor-agent has no equivalent today.

---

## Sources

- [Copilot CLI ACP server - GitHub Docs](https://docs.github.com/en/copilot/reference/copilot-cli-reference/acp-server)
- [ACP support in Copilot CLI is now in public preview - GitHub Changelog](https://github.blog/changelog/2026-01-28-acp-support-in-copilot-cli-is-now-in-public-preview/)
- [Support session/load in ACP Mode · Issue #936 · github/copilot-cli](https://github.com/github/copilot-cli/issues/936)
- [CLI Agent Modes and Cloud Handoff · Cursor](https://cursor.com/changelog/cli-jan-16-2026)
- [Cursor Background Agents](https://docs.cursor.com/en/background-agent)
- [acpx: Headless CLI client for stateful ACP sessions](https://github.com/openclaw/acpx)
- [Feature Request: stateful headless mode (daemon/server mode) · gemini-cli](https://github.com/google-gemini/gemini-cli/issues/15338)
