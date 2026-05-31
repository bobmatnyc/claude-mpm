# Terminal Title Feature

Sets the terminal tab/window title to reflect the current Claude session task
so users running many concurrent sessions can tell their tabs apart at a glance.

## What It Does

When enabled, the feature listens for `PostToolUse` events from the tools that
carry plan/task information and emits an OSC 0 escape sequence via the Claude
Code `terminalSequence` hook output channel.  The sequence sets both the *icon
name* (tab label) and the *window title* in one step, which is the most
widely-supported approach.

The title is distilled from the event payload via `distill_title()`:

1. `tool_input.plan_description` (explicit plan field, highest priority)
2. In-progress todo title from `tool_input.todos`
3. First todo title (any status)
4. `output` / `tool_result` field (ExitPlanMode plan text)
5. Tool name + brief context as final fallback

## How to Enable

The feature is **default-off**.  Set the environment variable in your shell
profile to enable it permanently:

```sh
export CLAUDE_MPM_TERMINAL_TITLE=true
```

Accepted truthy values: `true`, `1`, `yes`, `on`.
Accepted falsy values (explicit disable): `false`, `0`, `no`, `off`.

Any other value (including the variable being absent) means **disabled**.

## Optional Env-Var Tuning

| Variable | Default | Description |
|---|---|---|
| `CLAUDE_MPM_TERMINAL_TITLE` | *(unset / disabled)* | Enable the feature (`true`/`1`/`yes`/`on`) |
| `CLAUDE_MPM_TERMINAL_TITLE_MAX_LEN` | `60` | Maximum characters in the distilled title |
| `CLAUDE_MPM_TERMINAL_TITLE_EVENTS` | `TodoWrite,ExitPlanMode` | Comma-separated list of tool names that trigger a title update |

All three variables are read fresh on every hook invocation — no restart
required.

### Example: restrict to TodoWrite only

```sh
export CLAUDE_MPM_TERMINAL_TITLE=true
export CLAUDE_MPM_TERMINAL_TITLE_EVENTS=TodoWrite
```

### Example: longer titles

```sh
export CLAUDE_MPM_TERMINAL_TITLE=true
export CLAUDE_MPM_TERMINAL_TITLE_MAX_LEN=80
```

## OSC Target

The implementation emits **OSC 0** (`\033]0;<title>\007`), which sets both the
icon name and the window/tab title in ANSI-compatible terminals (xterm, iTerm2,
WezTerm, Ghostty, Windows Terminal, etc.).  OSC 0 is on the Claude Code
`terminalSequence` allowlist.

## The `CLAUDE_CODE_DISABLE_TERMINAL_TITLE=1` Caveat

Claude Code itself continuously resets the terminal title with its own OSC
sequence.  If you want your MPM-set title to persist between tool calls, also
set:

```sh
export CLAUDE_CODE_DISABLE_TERMINAL_TITLE=1
```

This tells Claude Code not to override the title.  MPM does not force-set this
variable (it affects the whole shell session); it is the user's responsibility
to set it when desired.

## Implementation Details

| Module | Role |
|---|---|
| `src/claude_mpm/hooks/terminal_title.py` | **Single source of truth**: `distill_title()`, `build_osc_sequence()`, `is_enabled()`, `get_max_length()`, `get_trigger_tools()` |
| `src/claude_mpm/hooks/claude_hooks/handlers/tool_handler.py` | Active dispatch: `_distill_plan_title()`, `_build_terminal_title_sequence()` (uses helpers above) |
| `src/claude_mpm/hooks/claude_hooks/hook_handler.py` | Propagates `terminalSequence` through `_route_event` / `_continue_execution` |

The active hot path is:

```
ToolHandler.handle_post_tool_fast(event)
  → _build_terminal_title_sequence(event)
      → terminal_title.is_enabled()          # env-var check
      → terminal_title.get_trigger_tools()   # event filter
      → _distill_plan_title(raw_text, ...)   # text distillation
      → terminal_title.build_osc_sequence()  # OSC escape
  → {"terminalSequence": "<OSC>"}           # returned to hook_handler
```

All feature-flag and config reads (`CLAUDE_MPM_TERMINAL_TITLE`,
`CLAUDE_MPM_TERMINAL_TITLE_MAX_LEN`, `CLAUDE_MPM_TERMINAL_TITLE_EVENTS`) are
centralised in `terminal_title.py` so there is one place to check.

## Tests

```
tests/hooks/test_terminal_title.py          — unit tests (distill_title,
                                              build_osc_sequence, is_enabled,
                                              get_max_length, get_trigger_tools,
                                              _build_terminal_title_sequence,
                                              end-to-end dispatch)
tests/hooks/test_terminal_title_dispatch.py — dispatch-path tests
                                              (_distill_plan_title,
                                              _build_terminal_title_sequence,
                                              full chain)
```
