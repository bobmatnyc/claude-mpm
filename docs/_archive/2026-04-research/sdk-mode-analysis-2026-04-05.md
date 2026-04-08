# SDK Mode Analysis — claude-mpm

**Date:** 2026-04-05
**Scope:** How SDK mode starts, session resume, oneshot/non-interactive mode, and how Claude Code is invoked.

---

## 1. How SDK Mode Currently Starts

**CLI flag:** `--sdk` (boolean, `store_true`, default `False`)

**Parser definition:**
`src/claude_mpm/cli/parsers/base_parser.py:345`
```python
run_group.add_argument(
    "--sdk",
    action="store_true",
    default=False,
    help="Use Agent SDK runtime instead of CLI subprocess (requires claude-agent-sdk)",
)
```

**Startup flow** (`src/claude_mpm/cli/__init__.py:124,172-175`):
1. `--sdk` sets `os.environ["CLAUDE_MPM_RUNTIME"] = "sdk"`.
2. The `ClaudeRunner` is created with `launch_method="sdk"` when that env var is set.
3. `_execute_session()` in `src/claude_mpm/cli/commands/run.py:567-580` calls `runner.run_interactive(context)` (interactive) or `runner.run_oneshot(prompt, context)` (non-interactive).
4. Both delegate to `SessionManagementService`, which eventually calls `InteractiveSession._launch_sdk_mode()` (`src/claude_mpm/core/interactive_session.py:622`).

**SDK mode startup sequence** (in `_launch_sdk_mode`, `interactive_session.py:638-904`):
- Imports `claude_agent_sdk` (fails gracefully if not installed).
- Builds `system_prompt` via `runner._create_system_prompt()`.
- Reads MCP config from `.mcp.json` files (the SDK does not load these automatically).
- Injects GitHub repo context into system prompt.
- Builds `ClaudeAgentOptions(system_prompt, cwd, permission_mode, hooks)`.
- Checks `--resume` in `claude_args` and sets `options.resume = session_id` if found.
- Opens `ClaudeSDKClient(options=options)` as a persistent context manager.
- Runs a `while True:` input loop reading from `input("> ")`.
- Each user message is sent via `await client.query(user_input)`.
- Responses are streamed via `async for message in client.receive_response()`.
- The `ResultMessage.session_id` is captured and stored as `self._sdk_session_id`.

---

## 2. How `claude -p` (Non-Interactive/Oneshot) Mode Works

**Claude Code's flag:** `-p` / `--print`

From `claude --help`:
```
-p, --print    Print response and exit (useful for pipes).
               The workspace trust dialog is skipped in -p mode.
               Only use this flag in directories you trust.
```

The `-p` flag accepts an **inline prompt as a positional argument**:
```
claude -p "your task here"
```

**How claude-mpm uses it** (`src/claude_mpm/core/oneshot_session.py:161`):
```python
cmd = infrastructure["cmd"] + ["--print", full_prompt]
```
The full prompt (optionally prepended with `context`) is passed directly as the argument to `--print`.

**MPM's non-interactive flags** (accessed via `src/claude_mpm/cli/parsers/base_parser.py:401-411`):
- `-i` / `--input`: input text or file path
- `--non-interactive`: run in non-interactive mode (read from stdin or `--input`)

When `non_interactive=True` or `input_arg` is set, `run.py:574-577` calls `runner.run_oneshot(user_input, context)` instead of `runner.run_interactive()`.

---

## 3. How Session Resume Works — What Is Saved/Restored

### MPM Side (CLI `--resume`)

**Parser:** `src/claude_mpm/cli/parsers/base_parser.py` (the `--resume` flag is defined in `run_parser.py`)

**Run command processing** (`src/claude_mpm/cli/commands/run.py:500-512`):
```python
resume_value = getattr(args, "resume", None)
if resume_value is not None and "--resume" not in claude_args:
    if resume_value:
        # Specific session ID → --resume <id> --fork-session
        claude_args = ["--resume", resume_value, "--fork-session", *claude_args]
    else:
        # No session ID → just --resume (resumes last session)
        claude_args.insert(0, "--resume")
```

The `--resume` flag (with or without a session ID) is passed through to the underlying `claude` CLI process or SDK options.

**What MPM tracks** (`src/claude_mpm/core/interactive_session.py:879-880`):
- The `ResultMessage.session_id` returned by the SDK is captured: `self._sdk_session_id = message.session_id`.
- MPM's own session manager (`src/claude_mpm/core/session_manager.py`) stores additional metadata (last_used, use_count, etc.).

### Claude Code Side

From `claude --help`:
```
-r, --resume [value]    Resume a conversation by session ID, or open interactive
                        picker with optional search term
-c, --continue          Continue the most recent conversation in current directory
--fork-session          When resuming, create a new session ID instead of reusing
                        the original (use with --resume or --continue)
--no-session-persistence  Disable session persistence (only works with --print)
--session-id <uuid>     Use a specific session ID for the conversation
```

Claude Code **saves sessions to disk** automatically. The session ID (UUID) returned in `ResultMessage.session_id` (from the SDK) can be used with `--resume <session-id>` to restore the full conversation history.

---

## 4. Claude Code's `-p` Flag Behavior (Direct)

From `claude --help` (full relevant section):
```
-p, --print             Print response and exit (useful for pipes).
--input-format <format> Input format (only with --print): "text" (default) or
                        "stream-json"
--output-format <format> Output format (only with --print): "text" (default),
                        "json", or "stream-json"
--include-partial-messages  Include partial chunks (only with --print and stream-json)
--max-budget-usd <amount>   Max spend cap (only with --print)
--no-session-persistence    Disable session saving (only with --print)
--fallback-model <model>    Auto-fallback model when overloaded (only with --print)
```

**Key behavior:** `-p` accepts the prompt as a positional argument (not a named flag):
```bash
claude -p "initial prompt here"
```
This makes claude run to completion and exit. A session ID IS still saved to disk unless `--no-session-persistence` is given.

---

## 5. Session Resume / Continuation Flags in Claude Code

```
-r, --resume [value]     Resume by session ID or open picker
-c, --continue           Continue most recent session in current directory
--fork-session           Branch from a session (creates new session ID)
--from-pr [value]        Resume session linked to a PR
```

**There IS a `--resume <session-id>` capability.** Claude Code saves sessions to disk after each `-p` run (unless `--no-session-persistence`). The session ID from that run can be passed to a subsequent `--resume <session-id>` invocation.

---

## 6. How claude-mpm Invokes Claude Code in SDK Mode

There are **three distinct launch paths** in claude-mpm:

### Path A: `exec` mode (default for interactive)
`src/claude_mpm/core/interactive_session.py:211` → `_launch_exec_mode(cmd, env)`
- Calls `os.execvpe("claude", cmd, env)` — replaces the current process with `claude`.
- The `cmd` is built by `_build_claude_command()` which includes `--dangerously-skip-permissions` and any `claude_args`.

### Path B: `subprocess` mode
`src/claude_mpm/core/interactive_session.py:208` → `_launch_subprocess_mode(cmd, env)`
- Uses `subprocess.run()` or `subprocess.Popen()`.

### Path C: `sdk` mode (when `--sdk` flag used)
`src/claude_mpm/core/interactive_session.py:209-210` → `_launch_sdk_mode()`
- Does NOT invoke the `claude` CLI at all.
- Uses `claude_agent_sdk.ClaudeSDKClient` (Python library) directly.
- Communicates in-process via `await client.query(prompt)` / `async for msg in client.receive_response()`.
- The SDK internally communicates with Claude AI (not by spawning a subprocess).

### Oneshot (non-interactive) always uses subprocess
`src/claude_mpm/core/oneshot_session.py:220-240` — `_run_subprocess()`:
```python
result = subprocess.run(cmd, capture_output=True, text=True, env=env, check=False)
```
The command is: `["claude", "--dangerously-skip-permissions", ...claude_args, "--print", full_prompt]`

---

## Key Answers to the Research Questions

### Can we pass `-p "initial prompt"` to start SDK mode with a task?

**SDK mode does not support this natively in the current implementation.**

In the current SDK mode (`_launch_sdk_mode`), there is no mechanism to inject an initial prompt before the REPL loop starts. The `ClaudeSDKClient` is opened and then `input("> ")` is called immediately. To auto-start with a task, you would need to either:
1. Call `await client.query(initial_prompt)` before entering the loop.
2. Use oneshot/non-interactive mode (`--non-interactive` / `-i`) which bypasses SDK mode and uses `subprocess.run` with `claude --print`.

**However:** The `SDKAgentRunner` class (`src/claude_mpm/services/agents/sdk_runtime.py:412-435`) DOES support one-shot via `await runner.run(prompt)` which uses `sdk_query(prompt=prompt, options=options)`. This is the programmatic API for oneshot SDK execution.

### Does Claude Code return a session ID that can be resumed?

**Yes.** The `ResultMessage` from the SDK (and from `claude --print --output-format=json`) contains `session_id`. MPM captures this in SDK mode at `interactive_session.py:879-880`:
```python
if message.session_id:
    self._sdk_session_id = message.session_id
```

### Is there a `claude --resume <session-id>` capability?

**Yes.** Claude Code has `-r` / `--resume [session-id]`. MPM plumbs this through at `run.py:506-512` and in SDK mode at `interactive_session.py:782-789` by setting `options.resume = session_id`.

### How to make SDK mode run to completion then exit (oneshot)?

Two approaches:
1. **Use non-interactive mode** (`claude-mpm --non-interactive -i "task"` or `--input "task"`): This calls `runner.run_oneshot()` → `OneshotSession.execute_command()` → `subprocess.run(["claude", "--print", prompt, ...])`. No SDK involved.
2. **Use `SDKAgentRunner.run(prompt)`** programmatically: This calls `sdk_query()` which is one-shot — fires the prompt, collects all messages, returns. No interactive loop.

The current `--sdk` flag only activates the persistent interactive loop. There is no `--sdk --print` combination that does SDK-based oneshot — that would require new code.

---

## File Paths Summary

| Topic | File |
|-------|------|
| `--sdk` flag definition | `src/claude_mpm/cli/parsers/base_parser.py:344-348` |
| SDK runtime env var set | `src/claude_mpm/cli/__init__.py:172-175` |
| launch_method="sdk" set | `src/claude_mpm/cli/commands/run.py:487-490` |
| `_launch_sdk_mode()` implementation | `src/claude_mpm/core/interactive_session.py:622-904` |
| `SDKAgentRunner` (programmatic SDK API) | `src/claude_mpm/services/agents/sdk_runtime.py` |
| `SDKAgentRunner.run()` (oneshot) | `src/claude_mpm/services/agents/sdk_runtime.py:412-435` |
| `SDKAgentRunner.resume()` | `src/claude_mpm/services/agents/sdk_runtime.py:535-555` |
| `SDKAgentRunner.fork()` | `src/claude_mpm/services/agents/sdk_runtime.py:557-577` |
| `--resume` plumbing in run command | `src/claude_mpm/cli/commands/run.py:500-512` |
| `--resume` in SDK options | `src/claude_mpm/core/interactive_session.py:782-789` |
| Oneshot subprocess execution | `src/claude_mpm/core/oneshot_session.py:220-248` |
| `--print` added to oneshot cmd | `src/claude_mpm/core/oneshot_session.py:161` |
| Session ID capture from SDK | `src/claude_mpm/core/interactive_session.py:879-880` |
| Non-interactive flag | `src/claude_mpm/cli/parsers/base_parser.py:407-411` |
