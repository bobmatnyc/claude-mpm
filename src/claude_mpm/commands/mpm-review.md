---
namespace: mpm/dev
command: review
aliases: [mpm-review]
migration_target: /mpm/dev:review
category: dev
description: Run a code review of the current diff or a PR via trusty-review, with graceful fallback
---

# /mpm-review

Run a first-class code review using the `trusty-review` MCP server, with a
graceful fallback to the `openrouter-code-reviewer` agent when trusty-review is
not available this session.

## Usage

```
/mpm-review                       # review the current `git diff` (working tree)
/mpm-review <owner>/<repo>#<PR>    # review an open pull request
```

When no argument is given, the current `git diff` (uncommitted + staged changes)
is reviewed. When an `<owner>/<repo>#<PR>` argument is given, the named pull
request is reviewed instead.

## Behavior (follow this sequence)

1. **Probe health.** Call `mcp__trusty-review__review_health`.

2. **If healthy → review via trusty-review:**
   - **No argument:** capture the current `git diff` and call
     `mcp__trusty-review__review_diff` with that diff.
   - **`<owner>/<repo>#<PR>` argument:** call `mcp__trusty-review__review_pr`
     with the parsed owner, repo, and PR number.

3. **If unhealthy or absent → fall back gracefully.** Do NOT error out. Delegate
   the review to the existing `openrouter-code-reviewer` agent over the same diff
   or PR, and note in the output that trusty-review was unavailable so the result
   came from the fallback reviewer.

4. **Output a structured report** using trusty-review's verdict vocabulary:
   - `APPROVE` — no blocking issues.
   - `APPROVE*` — approve with non-blocking nits/suggestions.
   - `REQUEST_CHANGES` — changes required before merge.
   - `BLOCK` — must not merge (e.g. compile break, security issue).
   - `UNKNOWN` — review could not reach a verdict (e.g. insufficient context).

   Include the verdict, a short rationale, and the per-finding details returned
   by the reviewer.

## Runtime requirements

`trusty-review` is review-on-demand and is auto-wired into `.mcp.json` when the
`trusty-review` binary is detected (entry: `trusty-review serve --stdio`, env
`TRUSTY_REVIEW_AUTH_MODE=cli`). For an authoritative review the following must
be available in the Claude Code process environment:

- **AWS Bedrock credentials** — `trusty-review` runs its LLM pass through
  Bedrock (`AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` / `AWS_SESSION_TOKEN`,
  plus a region). These are inherited from the environment; they are never
  written into `.mcp.json`.
- **trusty-search on `127.0.0.1:7878`** — authoritative review pulls repository
  context from a real trusty-search index. The default index name (`main`) may
  not exist for a given project; set `TRUSTY_SEARCH_INDEX` to the project's
  actual index when needed (it is intentionally NOT hardcoded in the MCP env).
- **`GITHUB_TOKEN` + `TRUSTY_REVIEW_AUTH_MODE=cli`** — required for
  `review_pr` so a local GitHub PAT works in serve mode. `GITHUB_TOKEN` is
  inherited from the environment and is never written into `.mcp.json`.

If trusty-review reports the verdict `UNKNOWN` because it could not reach
trusty-search or a model, surface that to the user along with the missing
prerequisite rather than presenting it as a passing review.
