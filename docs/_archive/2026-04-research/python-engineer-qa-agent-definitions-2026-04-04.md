# Python Engineer and QA Agent Definition Research
**Date**: 2026-04-04
**Purpose**: Understand current agent definitions to fix verification behavior

---

## Executive Summary

Both the Python Engineer and QA agents are defined as Markdown files with YAML frontmatter in `.claude/agents/`. These files ARE the authoritative agent definitions used by Claude Code. The source-of-truth for edits is in `.claude/agents/` for the current project, and in `~/.claude-mpm/cache/agents/bobmatnyc/claude-mpm-agents/agents/` for the upstream cache.

The `BASE_AGENT.md` at `src/claude_mpm/agents/BASE_AGENT.md` already contains a full `VERIFICATION BEFORE COMPLETION` section and a `SELF-ACTION IMPERATIVE` section. However, there is a gap: **neither the Python Engineer nor QA agent bodies contain explicit "verify your code runs in a clean environment" language**. The verification instruction in BASE_AGENT.md is about format (include evidence) not about the METHOD of verification (run it in a fresh shell/environment).

---

## 1. Python Engineer Agent

### File Locations

| Location | Path | Purpose |
|----------|------|---------|
| Deployed (active) | `/Users/masa/Projects/claude-mpm/.claude/agents/python-engineer.md` | What Claude Code actually reads |
| Upstream cache source | `~/.claude-mpm/cache/agents/bobmatnyc/claude-mpm-agents/agents/engineer/backend/python-engineer.md` | Synced from GitHub |
| Source (no separate .py file) | The `.claude/agents/` file IS the source for this project | — |

### Current Instructions (Body Content)

The Python Engineer body (after YAML frontmatter) covers:
- **Identity**: Python 3.12-3.13 specialist
- **Search-First Workflow**: WebSearch query templates for various patterns
- **Core Capabilities**: Python features, architecture patterns, type safety, performance
- **DI/SOA Decision Tree**: When to use DI vs simple scripts
- **Async Programming Patterns**: gather, worker pools, retry with backoff, TaskGroup, AsyncWorkerPool
- **Common Algorithm Patterns**: Sliding window, BFS, binary search, hash maps
- **Quality Standards**: Type safety (mypy --strict), testing (90%+ coverage), performance, code quality
- **Anti-Patterns**: 10 specific anti-patterns with correct alternatives
- **Development Workflow**: Quality commands (`black`, `mypy`, `pytest`, `flake8`, profiling)
- **Integration Points**: With QA, DevOps, Data Engineer, Security

### What Python Engineer Says About Verification

**Direct verification instructions in the body**: None explicit about running code in a clean environment.

In `knowledge.best_practices` (YAML frontmatter, informational only):
- "90%+ test coverage with pytest"
- "Implement comprehensive tests (90%+ coverage) for confidence"

Quality commands section:
```bash
pytest --cov=src --cov-report=html --cov-fail-under=90
```

**The `verification-before-completion` skill is listed in the `skills` field** of the frontmatter, meaning Claude Code may load that skill. But this is passive — it requires the skill to be triggered, not mandatory enforcement in the body.

### BASE_AGENT.md Appended Content

The engineer also receives `src/claude_mpm/agents/BASE_ENGINEER.md` appended (legacy fallback), which contains:
- Code Minimization Mandate
- Search-Before-Implement Protocol
- Testing Requirements (90% coverage)
- Code Review Checklist

And the root `src/claude_mpm/agents/BASE_AGENT.md` (via hierarchical discovery from the cache) which contains:
- **VERIFICATION BEFORE COMPLETION** section (lines 326-385): Forbids "should work now" phrases, requires actual command output
- **SELF-ACTION IMPERATIVE** (lines 241-295): Agents must execute commands themselves, not tell users to run them

---

## 2. QA Agent

### File Locations

| Location | Path | Purpose |
|----------|------|---------|
| Deployed (active) | `/Users/masa/Projects/claude-mpm/.claude/agents/qa.md` | What Claude Code actually reads |
| Upstream cache source | `~/.claude-mpm/cache/agents/bobmatnyc/claude-mpm-agents/agents/qa/qa.md` | Synced from GitHub |

### Current Instructions (Body Content)

The QA agent body (241 lines total in deployed file) is a generic QA methodology text covering:
- Core Responsibilities: test strategy, automation, quality metrics, risk assessment, performance validation, security testing
- Quality Assurance Methodology (5 steps): Analyze Requirements, Design Test Strategy, Implement Test Solutions, Validate Quality, Monitor and Report
- Testing Excellence: memory-efficient discovery, strategic sampling, pattern-based analysis
- Quality Focus Areas: Functional Testing, Non-Functional Testing, Test Automation
- Communication Style and Continuous Improvement

### What QA Agent Says About Verification

**The QA agent body contains no specific instructions about HOW to verify that code runs correctly**, about clean environments, about actually executing tests versus describing how to execute them, or about what constitutes a valid verification run.

The `knowledge.best_practices` YAML (informational) mentions:
- "Execute targeted test validation on critical paths"
- "Check package.json test configuration before running JavaScript/TypeScript tests"
- "Use CI=true npm test or explicit --run/--ci flags to prevent watch mode"
- "Verify test process termination after execution"
- "Monitor for orphaned test processes"

The `skills` field includes `verification-before-completion` and `bug-fix-verification` and `pre-merge-verification`.

---

## 3. BASE_AGENT.md

### File Location
`/Users/masa/Projects/claude-mpm/src/claude_mpm/agents/BASE_AGENT.md`

This file is automatically appended to ALL agent definitions when they are built/deployed. It is the universal instruction layer.

### Relevant Sections for Verification

**VERIFICATION BEFORE COMPLETION** (lines 326-385):

```
Forbidden phrases: "This should work now", "The fix has been applied",
"I've updated the code", "The issue should be resolved", etc.

Required Completion Format:
  ## Verification Results
  ### What was changed
  - [Specific file:line changes]
  ### Verification performed
  - [Command executed]: [Actual output]
  - [Test run]: [Pass/fail with numbers]
  - [Manual check]: [What was verified]
  ### Status: VERIFIED WORKING / NEEDS ATTENTION
```

**SELF-ACTION IMPERATIVE** (lines 241-295):
- Agents must run commands themselves and report actual output
- Forbidden: "You'll need to run...", "Please run this command..."

**What is MISSING from BASE_AGENT.md**:
- No instruction about running in a clean/fresh environment (no `venv`, no leftover state)
- No instruction about verifying imports work from scratch
- No instruction about running the full test suite (not just the changed test file)
- No instruction about checking for environment-specific assumptions

---

## 4. How Agents Get Their Instructions: The Mechanism

### Build-Time Composition (not runtime)

Agents are NOT built at delegation time. They are **deployed as static `.md` files** into `.claude/agents/` and Claude Code reads them when the subagent is spawned.

### Composition Process (in `agent_template_builder.py`)

```python
# Order of content composition:
content_parts = [agent_specific_instructions]  # Body from .md file

# Hierarchical BASE-AGENT.md discovery (walks up directory tree)
base_templates = self._discover_base_agent_templates(template_path)
for base_template_path in base_templates:
    content_parts.append(base_template_path.read_text())

# Fallback: legacy BASE_{TYPE}.md if no hierarchical templates found
if len(content_parts) == 1:
    legacy_base_instructions = self._load_base_agent_instructions(agent_type)
    content_parts.append(legacy_base_instructions)

# Join all with --- separator
content = "\n\n---\n\n".join(content_parts)
```

**Hierarchy for python-engineer (from cache)**:
1. `~/.../agents/engineer/backend/python-engineer.md` body
2. `~/.../agents/engineer/BASE-AGENT.md` (engineer-level)
3. `~/.../agents/BASE-AGENT.md` (root-level)

**For the project's `.claude/agents/python-engineer.md`**:
The file IS already fully composed — it is the merged output. The `.claude/agents/` files are the final deployed form including all composed content.

### PM Delegation

The PM does NOT inject agent instructions at delegation time. Instead, when the PM spawns a subagent via the Agent tool, Claude Code looks up the pre-deployed `.md` file from `.claude/agents/` and provides those instructions as the system prompt to the subagent instance.

The PM does pass task-specific context via the delegation prompt (the `prompt` parameter of the Agent tool call), but the agent's base behavior is entirely determined by its `.md` file.

---

## 5. Where to Add "Verify Code Runs in Clean Environment" Behavior

### Option A: Modify `BASE_AGENT.md` (affects ALL agents)

**File**: `/Users/masa/Projects/claude-mpm/src/claude_mpm/agents/BASE_AGENT.md`

Add to the existing `VERIFICATION BEFORE COMPLETION` section:

```markdown
### Clean Environment Verification (Code Changes)

When code is written or modified:
- Run tests in a fresh shell session (not reusing interpreter state)
- Verify imports resolve: `python -c "import <module>"` before claiming success
- Run the FULL test suite, not just the changed test file
- Check for environment assumptions: avoid `os.getenv()` silently returning None
```

**Impact**: All agents inherit this. Would also affect non-engineer agents like Research.

### Option B: Modify `BASE_ENGINEER.md` (affects all engineer agents)

**File**: `/Users/masa/Projects/claude-mpm/src/claude_mpm/agents/BASE_ENGINEER.md`

Add to the Code Review Checklist or Testing Requirements section:

```markdown
### Verification Protocol for Code Changes
- [ ] Tests run with `uv run pytest` (project-standard runner)
- [ ] Imports verified in fresh shell: `python -c "from module import Thing"`
- [ ] Full test suite passes, not just affected tests
- [ ] No environment state leftover from previous runs affecting results
```

**Impact**: All engineer agents (Python, TypeScript, Go, etc.) get this.

### Option C: Modify the Python Engineer directly (most targeted)

**File**: `/Users/masa/Projects/claude-mpm/.claude/agents/python-engineer.md`

Add a verification section to the body. This file is the deployed, ready-to-use agent. Changes here take effect immediately without rebuilding.

### Option D: Modify the cache source and redeploy

**File**: `~/.claude-mpm/cache/agents/bobmatnyc/claude-mpm-agents/agents/engineer/backend/python-engineer.md`

Modify the source, then run `claude-mpm deploy` or equivalent to rebuild `.claude/agents/python-engineer.md`.

### Recommendation

**For immediate effect**: Edit the deployed files directly:
- `/Users/masa/Projects/claude-mpm/.claude/agents/python-engineer.md`
- `/Users/masa/Projects/claude-mpm/.claude/agents/qa.md`

**For durable fix that propagates**: Edit `BASE_ENGINEER.md` and `BASE_AGENT.md` in the source directory, then redeploy. The `BASE_ENGINEER.md` additions flow to all engineer agents; `BASE_AGENT.md` changes flow to QA as well.

The most impactful single change would be to `BASE_AGENT.md` to strengthen the VERIFICATION BEFORE COMPLETION section with clean-environment language, since it applies universally.

---

## 6. Key Finding: The Gap

The current verification instruction in `BASE_AGENT.md` focuses on **format** (you must show actual command output) but not on **method** (you must run in clean state, full suite, no cached state).

An engineer can technically comply with the current rule by running `pytest tests/test_myfile.py` and pasting the output — but that might:
- Use a dirty interpreter with cached imports
- Skip tests in other files that are now broken
- Miss an import error that only appears in a fresh `python -m` invocation
- Use an active virtualenv with extra packages not in requirements

The missing instruction is: **"Run the full test suite using the project's standard runner (`uv run pytest`) in a clean shell, and verify the module imports correctly from scratch before claiming the work is complete."**

---

## Files Referenced

| File | Role |
|------|------|
| `/Users/masa/Projects/claude-mpm/.claude/agents/python-engineer.md` | Deployed Python Engineer agent (1373 lines) |
| `/Users/masa/Projects/claude-mpm/.claude/agents/qa.md` | Deployed QA agent (241 lines) |
| `/Users/masa/Projects/claude-mpm/src/claude_mpm/agents/BASE_AGENT.md` | Universal base for all agents (420 lines) |
| `/Users/masa/Projects/claude-mpm/src/claude_mpm/agents/BASE_ENGINEER.md` | Base for all engineer agents (~80 lines) |
| `~/.claude-mpm/cache/agents/bobmatnyc/claude-mpm-agents/agents/BASE-AGENT.md` | Cache-level root base |
| `~/.claude-mpm/cache/agents/bobmatnyc/claude-mpm-agents/agents/engineer/BASE-AGENT.md` | Cache-level engineer base |
| `/Users/masa/Projects/claude-mpm/src/claude_mpm/services/agents/deployment/agent_template_builder.py` | Build mechanism that composes agent files |
| `/Users/masa/Projects/claude-mpm/src/claude_mpm/agents/base_agent.json` | Legacy JSON base agent with task decomposition and clarification protocols |
