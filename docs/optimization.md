# MPM Optimization Guide

## Model Tiering

SDK mode defaults PM and subagents to Sonnet. Override per-session:

| Method | Scope | Example |
|--------|-------|---------|
| `--model opus` | PM model for this session | `claude-mpm run --sdk --model opus` |
| `CLAUDE_MPM_PM_MODEL=opus` | PM model (env var) | Export before starting |
| `CLAUDE_CODE_SUBAGENT_MODEL=claude-sonnet-4-6` | All subagents | Add to `~/.claude/settings.json` env |

Claude Code bug: agent frontmatter `model:` is ignored (anthropics/claude-code#44385). `updatedInput` hooks also don't work for Agent tool (#44412). Only explicit `model` param or env var works.

## Adaptive Thinking

Do NOT set `CLAUDE_CODE_DISABLE_ADAPTIVE_THINKING=1`.

The "thinking degradation" analysis was flawed (confirmed by Claude Code team). The `redact-thinking-2026-02-12` header hides thinking from UI/transcripts but does NOT reduce actual thinking. When Claude analyzes transcripts and sees no thinking, it incorrectly concludes thinking was reduced.

Use `/effort high` for specific turns if needed. Adaptive thinking manages its own budget.

## Token Optimization Summary

| Component | Before | After | Reduction |
|-----------|--------|-------|-----------|
| PM_INSTRUCTIONS.md | 1142 lines | ~295 lines | 74% |
| BASE_AGENT.md | 485 lines | 127 lines | 74% |
| BASE_ENGINEER.md | 838 lines | ~280 lines | 67% |
| Delegation count | 20+ per session | 5-7 target | 65-75% |
| Model cost (SDK) | $3.61 (Opus) | $1.32 (Sonnet) | 63% |

## References

- PR #425 — caveman prompt compression
- Issue #444 — model tiering
- Issue #445 — model tiering in non-interactive mode
- `docs/caveman/` — compression techniques and style guide
