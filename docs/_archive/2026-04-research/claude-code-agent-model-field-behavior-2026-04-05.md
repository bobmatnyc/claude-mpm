# Claude Code Agent `model:` Field — Actual Behavior Research

**Date:** 2026-04-05
**Scope:** How Claude Code handles `model:` in agent frontmatter and why `updatedInput` via `PreToolUse` hooks does not work for model overrides on the Agent tool.

---

## Summary

The `model:` frontmatter field IS a documented feature, but it sits at position 3 in a 4-level precedence chain. The `CLAUDE_CODE_SUBAGENT_MODEL` environment variable (position 1) and the per-invocation `model` parameter the calling LLM passes in the Agent tool call (position 2) both override it. The `PreToolUse updatedInput` mechanism does not reliably fix this because the calling LLM frequently passes its own model in the tool call, and even if you try to override via hook, the environment variable takes priority over that too.

---

## 1. Official Model Resolution Order

From the official subagents docs at https://code.claude.com/docs/en/sub-agents:

> When Claude invokes a subagent, it can also pass a `model` parameter for that specific invocation. Claude Code resolves the subagent's model in this order:
>
> 1. The `CLAUDE_CODE_SUBAGENT_MODEL` environment variable, if set
> 2. The per-invocation `model` parameter (passed by the calling LLM in the Agent tool call)
> 3. The subagent definition's `model` frontmatter
> 4. The main conversation's model

**Key implication:** `model:` frontmatter is NOT ignored — it is honored, but only when positions 1 and 2 are absent. In practice, when an Opus session invokes a subagent, the calling LLM frequently mirrors its own model in the tool call (position 2), which overrides the frontmatter (position 3).

---

## 2. Accepted Values for `model:` Frontmatter

Per official docs (field table in the sub-agents page):

- `sonnet` — alias
- `opus` — alias
- `haiku` — alias
- Full model ID (e.g., `claude-opus-4-6`, `claude-sonnet-4-6`)
- `inherit` — explicitly use the same model as the main conversation
- **Omitted** — defaults to `inherit` (as of current docs; earlier docs said it defaulted to `sonnet`)

Note: Earlier versions of the docs claimed the default when omitted was `sonnet`. The current docs say it defaults to `inherit`. Issue #10993 documented this ambiguity.

---

## 3. Why `PreToolUse updatedInput` Does NOT Work for Agent Model

The `updatedInput` mechanism for `PreToolUse` is documented as working for **all tools** including Agent. However, it does not solve the model enforcement problem for the following reason:

**The `CLAUDE_CODE_SUBAGENT_MODEL` env var (position 1) overrides everything.** Even if a `PreToolUse` hook modifies the Agent tool call's `model` parameter via `updatedInput`, the environment variable still takes highest priority.

Additionally, confirmed by GitHub issue #32732 (open as of 2026-04-05):

> "The Agent tool docs confirm this is by design: the tool's `model:` parameter **takes precedence over the agent definition's model frontmatter.**"

The actual mechanism: when a calling LLM (e.g., Opus) invokes the Agent tool, it generates a JSON tool call. If it includes `"model": "opus"` in that call (position 2), the frontmatter's `model: sonnet` (position 3) is silently ignored. This is by design.

**Regarding `updatedInput` specifically:** The documented behavior says `updatedInput` replaces the entire tool input — it must include all fields. So in theory, a `PreToolUse` hook could intercept the Agent tool call and replace `model: opus` with `model: sonnet`. However:
1. This only modifies position 2 (per-invocation parameter), not position 1 (env var).
2. If `CLAUDE_CODE_SUBAGENT_MODEL` is set, position 1 still wins.
3. The hook fires after the LLM has already generated the tool call with the wrong model.

There is no confirmed bug report saying `updatedInput` itself is broken for the Agent tool — the issue is architectural (precedence order), not a bug in hook machinery.

---

## 4. Confirmed GitHub Issues

### Issue #32732 — [FEATURE] Allow agent config `model` field to be non-overridable
- **Status:** OPEN (labeled `stale`, `enhancement`)
- **Problem:** Calling LLM mirrors its own model in the Agent tool call, overriding frontmatter.
- **Proposed fix:** `modelEnforcement: strict` frontmatter field.
- **Anthropic's stated position:** Current behavior (tool call parameter overrides frontmatter) is **by design**.
- **Real-world impact:** In a project with 16 custom agents, 9 out of 27 sessions for one agent ran on Opus despite `model: sonnet` in frontmatter.
- URL: https://github.com/anthropics/claude-code/issues/32732

### Issue #4549 — Model Configuration Support for Sub Agents
- **Status:** CLOSED (implemented — the `model:` field was added)
- The `model:` field was added as a feature. The issue of enforcement came later.
- URL: https://github.com/anthropics/claude-code/issues/4549

### Issue #10993 — Subagent model selection behavior unclear
- **Status:** CLOSED (documentation)
- **Key finding:** `CLAUDE_CODE_SUBAGENT_MODEL` **always overwrites all agents' model** including those with explicit `model:` frontmatter. This contradicts the intuitive expectation that the frontmatter field would take priority when set explicitly.
- **Also found:** `CLAUDE_CODE_SUBAGENT_MODEL` only accepts full model names (e.g., `claude-sonnet-4-5`), not aliases.
- URL: https://github.com/anthropics/claude-code/issues/10993

### Issue #18784 — Claude ignores agent frontmatter constraints when selecting subagents
- **Status:** CLOSED
- **Problem:** Claude ignores `disallowedProjectGlobs` and `description` when selecting which subagent to invoke — wrong agent selected for wrong task.
- This is a separate issue from model selection but shows a broader pattern: frontmatter fields are not enforced by the runtime; they are suggestions to the calling LLM.
- URL: https://github.com/anthropics/claude-code/issues/18784

### Issue #30703 — Custom agent definitions are silently ignored for team agents
- **Status:** Unknown (referenced in web search)
- When spawning team agents (via `team_name` parameter), all frontmatter fields and markdown body are silently ignored.
- URL: https://github.com/anthropics/claude-code/issues/30703

---

## 5. CLAUDE_CODE_SUBAGENT_MODEL Behavior

- Accepts **full model names only** (e.g., `claude-sonnet-4-5`), not aliases (`sonnet`).
- **Overrides ALL subagents** — including those with an explicit `model:` frontmatter field.
- This is the highest-priority setting and the most reliable way to force a specific model for all subagents.
- Documented at: https://code.claude.com/docs/en/model-config

---

## 6. Available Workarounds

### Option A: `CLAUDE_CODE_SUBAGENT_MODEL` env var (position 1 — highest priority)
Set it to a full model name. This forces ALL subagents onto that model regardless of frontmatter or tool call parameters.
```bash
export CLAUDE_CODE_SUBAGENT_MODEL="claude-sonnet-4-5-20250929"
```
**Limitation:** Applies globally to all subagents; cannot vary by agent.

### Option B: `PreToolUse` hook intercepting Agent tool calls
Write a hook that modifies the `model` field in Agent tool call inputs via `updatedInput`. This can selectively override per-agent-type.
```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "allow",
    "updatedInput": {
      "subagent_type": "my-reviewer",
      "model": "claude-sonnet-4-5",
      "prompt": "..."
    }
  }
}
```
**Limitation:** Only overrides position 2. If `CLAUDE_CODE_SUBAGENT_MODEL` is set (position 1), hook-modified model is still overridden. Hook approach works if position 1 is unset.
**Also:** The calling LLM omits the model field or you must include all original fields in `updatedInput`.

### Option C: Wait for `modelEnforcement: strict` (not yet shipped)
GitHub issue #32732 requests this feature. Not implemented as of 2026-04-05.

### Option D: Use the `--agents` CLI flag with explicit model
Pass the agent definition at session start with `--agents` JSON. This is position 2 (session-level), which has higher priority than file frontmatter.

---

## 7. `updatedInput` — Documented Scope and Behavior

From https://code.claude.com/docs/en/hooks:

- Works for **all tools** including Agent, Bash, Edit, Write, Read, Glob, Grep, WebFetch, WebSearch, AskUserQuestion, ExitPlanMode, and MCP tools.
- **Replaces the entire input object** — unchanged fields must be explicitly included.
- Can be combined with any `permissionDecision` value.
- `AskUserQuestion` requires special handling: must include original `questions` array and add `answers` object.
- Multiple PreToolUse hooks: `deny` > `defer` > `ask` > `allow` precedence.
- Deprecated: top-level `decision` and `reason` fields. Use `hookSpecificOutput.permissionDecision` and `hookSpecificOutput.permissionDecisionReason`.

There is no documented or confirmed bug preventing `updatedInput` from working with the Agent tool. The mechanism works; the issue is that it only controls position 2 in the resolution chain.

---

## 8. Key Takeaways

| Question | Answer |
|---|---|
| Is `model:` in agent frontmatter a documented feature? | Yes, fully documented |
| Is it honored? | Yes, but only as position 3 in a 4-level chain |
| What overrides it? | `CLAUDE_CODE_SUBAGENT_MODEL` env var (always) and the calling LLM's per-invocation `model` parameter (frequently when LLM mirrors its own model) |
| Does `updatedInput` via `PreToolUse` fix model selection? | Partially — modifies position 2, but position 1 (env var) still wins |
| Is `updatedInput` broken for the Agent tool? | Not confirmed as broken; limitation is architectural (precedence order), not a hook bug |
| Is there a way to enforce model hard? | Not natively; workarounds are env var (global) or hook (per-agent-type) |
| Is this behavior by design? | Yes, explicitly confirmed by Anthropic in issue #32732 |

---

## Sources

- [Official subagents docs](https://code.claude.com/docs/en/sub-agents) — model field, precedence order, accepted values
- [Official hooks docs](https://code.claude.com/docs/en/hooks) — updatedInput scope and schema
- [Model config docs](https://code.claude.com/docs/en/model-config) — CLAUDE_CODE_SUBAGENT_MODEL
- [Issue #32732](https://github.com/anthropics/claude-code/issues/32732) — Feature: non-overridable model enforcement (OPEN)
- [Issue #4549](https://github.com/anthropics/claude-code/issues/4549) — Model configuration support (CLOSED/implemented)
- [Issue #10993](https://github.com/anthropics/claude-code/issues/10993) — Model selection behavior unclear (CLOSED/docs)
- [Issue #18784](https://github.com/anthropics/claude-code/issues/18784) — Frontmatter constraints ignored for agent selection (CLOSED)
- [Issue #30703](https://github.com/anthropics/claude-code/issues/30703) — Agent definitions ignored for team agents
