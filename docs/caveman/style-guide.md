# Caveman Prompt Style Guide

Rules for writing and editing caveman-style system prompts in Claude MPM.

## Core Principles

1. **Preserve all rules** -- compression removes words, never rules
2. **Tables over prose** -- one row per rule, self-contained
3. **One line per concept** -- no multi-paragraph explanations
4. **Reference, don't repeat** -- use cross-references for shared content
5. **Test after changes** -- measure quality impact, don't assume

## DO

### Use tables for structured information

```
| Phase | Agent | Gate | Skip When |
|-------|-------|------|-----------|
| 1. Research | Research | Findings documented | Simple task |
| 2. Impl | Engineer | Tests pass | -- |
```

### Write one line per rule

```
PM runs full pipeline without stopping. Ask user ONLY if <90% success.
```

### Use standard abbreviations

| Abbreviation | Meaning |
|-------------|---------|
| impl | implementation |
| config | configuration |
| env | environment |
| ops | operations |
| auth | authentication |
| deps | dependencies |
| req(s) | requirement(s) |
| docs | documentation |
| QA | quality assurance |
| PM | project manager |
| CB | circuit breaker |

### Use symbolic references

| Symbol | Meaning |
|--------|---------|
| P1-P12 | Prohibition rule 1-12 |
| CB#N | Circuit Breaker number N |
| [SKILL: name] | Content loaded from skill on demand |
| -> | "delegate to" |
| -- | "not applicable" / separator |
| <=, >=, <, > | Comparison operators for limits |

### Keep exact tool names unchanged

```
CORRECT: mcp__kuzu-memory__kuzu_recall
CORRECT: mcp__mcp-vector-search__search_code
CORRECT: mcp__mcp-ticketer__*

WRONG: kuzu recall tool
WRONG: vector search
WRONG: ticketer tools
```

### Keep trigger conditions precise

Trigger conditions are load-bearing -- they determine when rules fire.
Never compress a trigger into something ambiguous.

```
CORRECT: PM reads >3 files -> CB#2
CORRECT: PM uses Edit/Write any size -> CB#1
CORRECT: "rm", "rmdir" on project files -> CB#7

WRONG: PM reads too many files -> CB#2
WRONG: PM edits stuff -> CB#1
WRONG: PM deletes things -> CB#7
```

### Use pipe-separated inline lists

```
git status/add/commit/log/push/diff/branch/pull/stash
```

Not:
```
git status, git add, git commit, git log, git push, git diff...
```

## DON'T

### Never remove actual rules or constraints

```
WRONG: Removing "No exceptions for trivial commands"
(This is a load-bearing rule, not filler)

WRONG: Removing circuit breaker detection patterns
(These prevent PM from executing forbidden actions)
```

### Never compress tool names or MCP paths

```
WRONG: mcp__kuzu__recall (truncated)
WRONG: kuzu-mem tool (renamed)
WRONG: vector-search (ambiguous)
```

### Never use ambiguous abbreviations

```
WRONG: "auth" when it could mean "authentication" or "authorization"
       (In context, pick one meaning and be consistent)

WRONG: "env" when it could mean "environment" or "envelope"
       (Use "env" only for environment variables/configs)
```

### Never remove the prohibitions table

The canonical prohibitions table (P1-P12) is the single source of truth.
Other sections reference it. Removing or restructuring it breaks the
cross-reference system.

### Never skip A/B testing for MEDIUM-risk changes

If you remove instructions Claude "should already know" (Technique D),
always validate with a comparison run. See [measurement.md](measurement.md).

### Never compress error messages or examples

Error messages need to be human-readable for debugging. Examples in
circuit breaker patterns need to match exact tool names.

```
KEEP AS-IS:
- Edit/Write any size -> CB#1
- curl/lsof/ps/make -> CB#7
- mcp__mcp-ticketer__* -> CB#6
- sed/awk/patch -> CB#14
```

## Template: Adding a New Rule

When adding a new rule to the caveman prompt, use this template:

### For a prohibition

Add a row to the Prohibitions table:

```
| P[N] | [terse forbidden action] | [delegate to agent] | [CB#] |
```

### For a workflow phase

Add a row to the Workflow table:

```
| [N]. [Phase] | [Agent] | [Gate condition] | [Skip condition] |
```

### For a circuit breaker

Add a row to the Circuit Breakers table:

```
| [CB#] | [Name] | [Trigger pattern] | [Action] |
```

### For an agent route

Add a row to the Agent Routing table:

```
| [Agent] | [Trigger keywords] | [Default Model] |
```

### For a new section

Use this structure:

```markdown
## Section Name

[1-2 line summary of purpose]

| Key | Value |
|-----|-------|
| Rule | [terse description] |
| Trigger | [exact condition] |
| Action | [what to do] |
| Reference | [CB# or P# if applicable] |
```

## Editing Checklist

Before committing changes to a caveman prompt:

- [ ] No rules removed (only reworded or relocated)
- [ ] All tool names exact (match MCP registry)
- [ ] All trigger conditions precise (not vague)
- [ ] Cross-references valid (P# and CB# still exist)
- [ ] Tables parse correctly in Markdown
- [ ] Abbreviations from approved list only
- [ ] MEDIUM-risk changes have A/B test plan
- [ ] Token count measured (should decrease or stay flat)

## Token Counting

Estimate tokens for a section:

- **Rule of thumb**: 1 token ~ 4 characters (English text)
- **More precise**: Use `tiktoken` with `cl100k_base` encoding
- **Quick check**: Byte count / 4 gives rough token estimate

```python
# Quick token estimate
import tiktoken
enc = tiktoken.get_encoding("cl100k_base")
tokens = len(enc.encode(text))
```

## Examples of Good Caveman Prompts

### Minimal but complete

```
PM = orchestrator. Delegates ALL work.
DEFAULT: delegate. EXCEPTION: user says "you do it".
```

### Table-driven rules

```
| # | Forbidden | Delegate To | CB# |
|---|-----------|-------------|-----|
| P1 | Edit/Write | Engineer | 1 |
| P2 | Read >3 files | Research | 2 |
```

### Skill reference

```
## PR Workflow
[SKILL: mpm-pr-workflow]
All pushes to main require feature branch + PR. Delegate to Version Control.
```

### Inline condition

```
Ask user ONLY if <90% success probability (ambiguous reqs, missing creds).
```

## Examples of Bad Caveman Prompts

### Too compressed (lost meaning)

```
WRONG: "PM no exec. Del all."
(What is "exec"? What is "del"? Ambiguous.)

BETTER: "PM never executes. Delegates all work to agents."
```

### Lost precision

```
WRONG: "Don't use tools"
(Which tools? All tools? Only certain tools?)

BETTER: "Never use Edit/Write, curl, wget, lsof, make, sed, awk."
```

### Missing cross-reference target

```
WRONG: "See P15" (P15 doesn't exist in the prohibitions table)
WRONG: "CB#20 enforced" (CB#20 doesn't exist)
```
