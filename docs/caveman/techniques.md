# Compression Techniques

Each technique with concrete before/after examples from actual MPM prompts.
Apply in combination for maximum savings.

## A. Remove Filler and Hedging (~15% savings, LOW risk)

Strip words that add no meaning. LLMs infer intent from content, not politeness.

### Before/After Examples

**1. Role description**
```
BEFORE (49 tokens):
The Project Manager (PM) agent coordinates work across specialized agents
in the Claude MPM framework. The PM's responsibility is orchestration and
quality assurance, not direct execution.

AFTER (14 tokens):
PM = orchestrator + QA coordinator. Delegates ALL work to specialist agents.
```

**2. Delegation principle**
```
BEFORE (42 tokens):
This is the opposite of "delegate when you see trigger keywords." Instead:
DEFAULT action = Delegate to appropriate agent
EXCEPTION = User says "you do it", "don't delegate", "handle this yourself"
When in doubt, delegate. The PM's value is orchestration, not execution.

AFTER (16 tokens):
DEFAULT: delegate. EXCEPTION: user says "you do it" / "don't delegate".
```

**3. Memory tool instructions**
```
BEFORE (58 tokens):
Before delegating to Research or reading files, PM MUST check project
memory tools first:
1. kuzu-memory -- Query mcp__kuzu-memory__kuzu_recall first. Both tools
   are stable and recommended for all projects.
2. mcp-vector-search -- Search mcp__mcp-vector-search__search_code second
   if kuzu-memory is insufficient.
3. Only if neither yields sufficient context -> delegate to Research agent.
These tools are stable and should always be used when the project has them
configured. This is not optional.

AFTER (28 tokens):
Before delegating to Research or reading files:
1. mcp__kuzu-memory__kuzu_recall -- query FIRST
2. mcp__mcp-vector-search__search_code -- if kuzu insufficient
3. Only then delegate to Research agent
Both tools stable, recommended for all projects. Not optional.
```

**4. Exception disclaimer**
```
BEFORE (22 tokens):
No exceptions for "trivial" or "documented" commands. The cost of
delegation ($0.10-$0.50) is always justified by maintaining clean
separation of concerns.

AFTER (9 tokens):
No exceptions for "trivial", "documented", or cost-saving arguments.
```

**5. Autonomous execution**
```
BEFORE (45 tokens):
PM should execute the full pipeline autonomously unless there's genuine
ambiguity that requires user input. Ask the user ONLY when success
probability is below 90%: ambiguous requirements, missing credentials,
critical architecture choices that could go either way.

AFTER (25 tokens):
PM runs full pipeline without stopping. Ask user ONLY if <90% success
probability (ambiguous reqs, missing creds, critical architecture choice).
```

### When to use
Always. Zero risk. Every prompt has filler that can be stripped.

### When NOT to use
Never skip this technique -- it has no downside.


## B. Merge Duplicate Rules (~20% savings, LOW risk)

The verbose PM prompt stated the same prohibitions in **4 separate locations**
(~150 lines total):

1. "ABSOLUTE PROHIBITIONS" section -- numbered list of 7 rules
2. "PM Direct Execution Allowlist" -- negative restatement of same rules
3. "BASE_PM Framework Floor" -- third copy with slightly different wording
4. "Circuit Breakers" -- detection patterns restating the same actions

### Fix Applied

One canonical prohibitions table at the top. All other sections reference it
with "See Prohibitions table" or use CB# identifiers.

**Before (4 locations, ~3,000 tokens):**
```
## ABSOLUTE PROHIBITIONS
PM must NEVER:
1. Investigate, debug, or analyze code in depth - DELEGATE to Research
2. Make ANY code changes (Edit/Write tool) - DELEGATE to Engineer
...

## PM Direct Execution Allowlist
PM MUST delegate everything else, including:
- make targets -> Local Ops
- pytest, npm test -> QA or Engineer
...

## BASE_PM Framework Floor
Enforcement:
- PM NEVER uses Edit/Write tools
- PM NEVER runs curl, wget...
...

## Circuit Breakers
| CB#1 | Large Impl | PM uses Edit/Write | ...
```

**After (1 location, ~800 tokens):**
```
## Prohibitions (CANONICAL -- single source of truth)

All other sections reference this table. Violation = Circuit Breaker triggered.

| # | Forbidden Action | Delegate To | CB# |
|---|-----------------|-------------|-----|
| P1 | Edit/Write tool (any size) | Engineer | 1 |
| P2 | Read >3 files or deep code analysis | Research | 2 |
...
```

### When to use
Any time you find the same rule stated in multiple places. Consolidate to one
canonical location and reference it elsewhere.

### When NOT to use
If rules have genuinely different audiences or contexts that require different
framing. In practice, this is rare.


## C. Tables Instead of Prose (~25% savings, LOW risk)

Convert multi-paragraph explanations into compact tables. LLMs parse tables
efficiently -- each row is a self-contained rule.

### Example 1: Workflow phases

**Before (40+ lines of prose):**
```
## PM Workflow Phases

### Phase 1: Research
The PM delegates investigation to the Research agent. Before proceeding
to implementation, the Research agent must document its findings. The PM
should skip research when the user gives an explicit command, when the
task is simple enough, or when all skip conditions are met...

### Phase 2: Code Analysis
The PM delegates to the Code Analysis agent to review the codebase...
```

**After (10 lines):**
```
## Workflow (5-phase)

| Phase | Agent | Gate | Skip When |
|-------|-------|------|-----------|
| 1. Research | Research | Findings documented | Explicit command, simple task |
| 2. Code Analysis | Code Analysis | APPROVED / NEEDS_IMPROVEMENT | -- |
| 3. Implementation | Engineer (per lang) | Tests pass, files tracked | -- |
| 4. QA | Web/API/general QA | All criteria verified | User says "no QA" |
| 5. Documentation | Documentation Agent | Docs updated | No code changes |
```

### Example 2: Verification gates

**Before (25 lines):**
```
When claiming implementation is complete, you MUST have evidence from the
Engineer agent confirming completion, including file paths changed and a
git commit hash. Never use phrases like "should work" or "looks correct"...
```

**After (8 lines):**
```
| Claim | Required Evidence | Forbidden Phrases |
|-------|-------------------|-------------------|
| Impl complete | Engineer confirm, file paths, git hash | "should work" |
| Deployed | Live URL, HTTP status, health check | "appears working" |
| Bug fixed | QA repro, Engineer fix, QA verify | "probably fixed" |
```

### Example 3: Agent routing

**Before (618 lines with boilerplate examples for 56 agents):**
Each agent had 10+ lines including generic usage examples.

**After (60-row table):**
```
| Agent | Triggers | Default Model |
|-------|----------|---------------|
| Research | codebase understanding, investigation | sonnet |
| Engineer (all langs) | code changes, impl, refactor | sonnet |
| Local Ops | localhost, PM2, docker, ports | haiku |
...
```

This single change saved approximately 5,500 tokens.

### When to use
Any multi-paragraph section that describes rules, routing, or conditions.

### When NOT to use
Nuanced explanations where table rows would be ambiguous. Keep prose for
concepts that require context or reasoning chains.


## D. Remove Obvious Instructions (~10% savings, MEDIUM risk)

Claude already knows standard engineering practices. Telling it to "write
clear commit messages" or "handle edge cases" wastes tokens.

### Instructions Removed

- "Use proper error handling"
- "Write clear commit messages"
- "Include documentation"
- "Handle edge cases"
- "Follow best practices"
- "Test your implementation"
- "Use descriptive variable names"
- "Consider performance implications"

### Instructions Kept

- Project-specific conventions (commit message format, branch naming)
- Non-obvious constraints (file size limits, specific tool restrictions)
- Safety-critical rules (prohibitions, circuit breakers)

### Risk: MEDIUM

If you remove an instruction that Claude does NOT inherently follow, quality
may degrade. Always A/B test after removing "obvious" instructions. The pilot
study showed no quality loss, but different domains may differ.

### When to use
For frontier models (Opus, Sonnet) with strong baseline capabilities.

### When NOT to use
- For smaller/less capable models
- For domain-specific practices the model may not know
- For safety-critical instructions


## E. Compress Catalogs (~30% savings for section, LOW risk)

Long reference lists (agent catalogs, tool lists, error codes) compress well
into tables without information loss.

### Agent Catalog Compression

**Before (618 lines, ~8,000 tokens):**
```
### python-engineer
The Python Engineer specializes in Python development with focus on
type-safe, async-first patterns. Use this agent for Python code changes,
refactoring, and implementation.

Example delegation:
"Implement a REST API endpoint for user authentication using FastAPI
with Pydantic validation and pytest tests."
...

### rust-engineer
The Rust Engineer specializes in Rust development with traits, tokio,
and error handling patterns...
```

**After (~60 rows, ~2,500 tokens):**
```
| ID | Type | Specialty | Model |
|---|---|---|---|
| python-engineer | engineer | Python: DI, type hints, pytest | sonnet |
| rust-engineer | engineer | Rust: traits, tokio, thiserror | sonnet |
| typescript-engineer | engineer | TS: strict mode, React, Node | sonnet |
...
```

Savings: ~5,500 tokens. The table preserves all routing-relevant information.
Generic usage examples were removed because Claude can construct appropriate
delegations from the specialty description.

### When to use
Any catalog or reference list where entries follow a consistent structure.

### When NOT to use
If entries have unique, non-tabular information that would be lost.


## F. Symbolic Notation (~5% savings, LOW risk)

Use consistent shorthand and cross-references instead of restating content.

### Conventions Used

| Symbol | Meaning |
|--------|---------|
| CB#N | Circuit Breaker number N |
| P1-P12 | Prohibition rule 1-12 |
| [SKILL: name] | Content loaded from skill on demand |
| -> | "delegate to" |
| -- | "not applicable" or separator |

### Cross-Reference Pattern

Instead of restating a rule in multiple sections:

```
BEFORE:
"PM must never use Edit/Write tools. This is enforced by Circuit Breaker #1
which detects when PM attempts to use Edit or Write tools..."

AFTER:
"See P1. CB#1 enforced."
```

### When to use
Anywhere the same rule is referenced from multiple locations.

### When NOT to use
If the cross-reference target might be removed or relocated. Broken references
are worse than duplication.


## Technique Risk Summary

| Technique | Savings | Risk | A/B Test Needed? |
|-----------|---------|------|-----------------|
| A. Remove filler | ~15% | LOW | No |
| B. Merge duplicates | ~20% | LOW | No |
| C. Tables over prose | ~25% | LOW | Recommended |
| D. Remove obvious | ~10% | MEDIUM | Yes |
| E. Compress catalogs | ~30% | LOW | No |
| F. Symbolic notation | ~5% | LOW | No |

Combined application achieved 77% reduction on PM_INSTRUCTIONS.md with
equal or better quality in pilot testing.
