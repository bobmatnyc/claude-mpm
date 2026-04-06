# Agent Communication Protocol

Token-efficient formats for PM-to-agent delegation and agent-to-PM returns.

## Current State

PM currently delegates using verbose natural language:

```
CURRENT (~150-300 tokens per delegation):
"I need you to investigate the authentication module in the project.
Please look at the files src/auth.js and src/middleware/session.js.
Focus on how token validation works, how sessions are stored, and
identify any security concerns. The user is reporting 401 errors
after token refresh. Please provide a summary of your findings
including the specific files and line numbers where issues are found,
along with severity ratings for each issue."
```

## Proposed: HSDF (Hybrid Structured Delegation Format)

YAML-based delegation that separates machine-parseable routing from
human-readable context.

### PM -> Agent Delegation

```yaml
# ~50-80 tokens
task: investigate
domain: auth
scope:
  read: [src/auth.js, src/middleware/session.js]
  find: [token_validation, session_storage, security_concerns]
return:
  format: summary
  include: [files, lines, severity]
context: "User reports 401 errors after token refresh"
```

### Agent -> PM Return

```yaml
# ~100-200 tokens
status: complete
findings:
  - file: src/auth.js:47-62
    issue: token_validation
    severity: high
    detail: "JWT expiry not checked before session write"
  - file: src/middleware/session.js:23
    issue: session_storage
    severity: low
    detail: "Redis TTL matches token expiry correctly"
actions_suggested:
  - "Add jwt.verify() call at auth.js:47"
```

### Format Comparison

| Format | Tokens | Parseability | Nuance | Cache-friendly |
|--------|--------|-------------|--------|----------------|
| Verbose prose | ~120 | Low | High | Low (variable) |
| Caveman prose | ~50 | Low | Medium | Medium |
| JSON | ~65 | High | Low | High |
| YAML (HSDF) | ~55 | High | Medium | High |
| Command DSL | ~30 | High | Low | High |

YAML-based HSDF provides the best balance: token efficient, machine parseable,
and enough room for context strings. JSON is a close second but noisier
(braces, quotes add tokens).

## Per-Agent Communication Templates

### Research Delegation

```yaml
task: investigate | analyze | find
domain: [area of codebase]
scope:
  read: [file1.py, file2.py]
  find: [pattern1, pattern2]
  depth: shallow | deep | exhaustive
return:
  format: summary | detailed | files_only
  include: [files, lines, severity, recommendations]
context: "Brief description of what triggered this investigation"
```

### Engineer Delegation

```yaml
task: implement | refactor | fix
target: [file or module]
requirements:
  - "requirement 1"
  - "requirement 2"
tests: required | optional | skip
return:
  format: diff_summary
  include: [files_changed, tests_added, commit_hash]
context: "What triggered this implementation"
```

### QA Delegation

```yaml
task: verify | test | validate
target: [endpoint, component, or feature]
method: browser | api | unit
assertions:
  - "expected behavior 1"
  - "expected behavior 2"
return:
  format: pass_fail
  include: [evidence, screenshots, errors]
context: "What was changed and needs verification"
```

### Ops Delegation

```yaml
task: deploy | configure | check
target: [service or environment]
commands: [allowed commands]
return:
  format: status
  include: [output, errors, process_status]
context: "Why this operation is needed"
```

## Token Savings

### Per-Delegation

- Current verbose: ~150-300 tokens per task description
- HSDF: ~50-80 tokens per task description
- Savings: **60-70% per delegation message**

### Per-Session (10 delegations)

- Delegation overhead current: ~3,000 tokens (10 x 300)
- Delegation overhead HSDF: ~800 tokens (10 x 80)
- Agent return current: ~5,000 tokens (10 x 500 verbose)
- Agent return HSDF: ~2,000 tokens (10 x 200 structured)
- **Net savings: ~5,200 tokens/session**

### Relative Impact

Delegation compression is ~1% of total optimization potential. The real
token cost is system prompts (540K/session) and prompt caching (30M/session).

Delegation format compression is valuable primarily for:
- **Latency**: Fewer tokens = faster processing
- **Clarity**: Structured format reduces misinterpretation
- **Parseability**: Enables automated result processing

## When to Use Prose vs Structured

### Use HSDF (structured)

- Standard delegation patterns (investigate, implement, verify)
- Routine tasks with clear scope
- When multiple agents run in parallel (consistency helps)
- When results need programmatic processing

### Use Prose

- Novel/unusual tasks requiring nuanced explanation
- Tasks where context is complex and interconnected
- Edge cases not covered by HSDF templates
- First-time instructions to a new agent type

### Hybrid (recommended default)

HSDF header for routing + prose `context` field for nuance:

```yaml
task: investigate
domain: auth
scope:
  read: [src/auth.js]
  find: [token_lifecycle]
context: |
  User reports intermittent 401 errors that only appear after
  the token refresh endpoint is called. The session appears valid
  in Redis but the middleware rejects it. This might be a race
  condition between token refresh and session validation.
```

## What NOT to Compress in Delegation

- Exact tool names (`mcp__kuzu-memory__kuzu_recall`)
- Error messages and diagnostic output
- Security-critical instructions
- File paths and line numbers (precision matters)
- Specific constraint values (timeouts, limits, thresholds)

## Implementation Status

HSDF is currently a **proposed** format. It has not been implemented in the
claude-mpm codebase. Implementation would require:

1. Defining the YAML schema formally
2. Updating PM instructions to use HSDF templates
3. Updating agent definitions to parse/return HSDF
4. A/B testing to validate no quality regression
5. Fallback mechanism for edge cases
