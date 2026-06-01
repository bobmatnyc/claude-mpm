---
title: Agent Assembly Pipeline
version: 6.5.4
last_updated: 2025-06-01
status: current
---

# Agent Assembly Pipeline

**Architecture reference**: How agent definitions are produced, composed, and delivered to running prompts.

This document explains the complete lifecycle of an agent from source definition through deployment to a running Claude Code session. It clarifies what lands in the PM prompt vs. each subagent prompt, when assembly happens, and the build-vs-runtime boundary.

## Table of Contents

- [Overview](#overview)
- [The PM Prompt Pipeline](#the-pm-prompt-pipeline)
- [The Subagent Prompt Pipeline](#the-subagent-prompt-pipeline)
- [Build-vs-Runtime Boundary](#build-vs-runtime-boundary)
- [Subagent Capability Limits](#subagent-capability-limits)
- [Build → Deploy → Runtime Diagram](#build--deploy--runtime-diagram)
- [BASE_AGENT.md vs base_agent.json](#base_agent_md-vs-base_agent_json)
- [Key Components](#key-components)

---

## Overview

Claude MPM assembles agent prompts in two distinct pipelines:

1. **PM Pipeline** — builds `PM_INSTRUCTIONS_DEPLOYED.md` once per session startup
2. **Subagent Pipeline** — composes individual agent `.md` files at agent deploy time (not runtime)

Neither pipeline re-assembles at runtime. Subagents see their prompt **as deployed**; the PM sees the deployed system instructions file.

**Key Principle**: Build artifacts are _durable_. Agents don't re-merge their frontmatter or BASE instructions on every invocation.

---

## The PM Prompt Pipeline

The PM (project manager) receives a merged system instructions file built once at CLI startup.

### Source Files

Four input blocks are merged into a single `PM_INSTRUCTIONS_DEPLOYED.md`:

1. **PM_INSTRUCTIONS.md** — PM core identity and responsibilities
2. **AGENT_DELEGATION.md** — available agent capabilities and how to invoke them
3. **WORKFLOW.md** — mandatory 5-phase workflow sequence (special lazy-load logic)
4. **MEMORY.md** — static memory management guidance

Each block has a 3-level resolution priority:

```
User override (~/.claude-mpm/<BLOCK>.md)
    + Project override (.claude-mpm/<BLOCK>.md)
    fallback: System default (src/claude_mpm/agents/<BLOCK>.md)
```

If both user and project overrides exist, they are **concatenated together** (additive semantics) and replace the system default. If neither exists, the system default is used.

### Special Case: WORKFLOW.md Lazy-Load Logic

WORKFLOW.md has unique handling to avoid injecting ~1,150 tokens into every PM prompt:

- **User/project override present** → Inline the override verbatim
- **No override (system default only)** → Use `WORKFLOW_SYSTEM_REFERENCE` (compact stub)

This mirrors the behavior of `InstructionLoader.load_workflow_instructions()` so deployed and live assembled prompts stay in sync.

**Location**: `src/claude_mpm/core/framework/loaders/workflow_constants.py` (`WORKFLOW_SYSTEM_REFERENCE`)

### Build Process

**When**: CLI startup (once per session)  
**Component**: `SystemInstructionsDeployer` (`src/claude_mpm/services/agents/deployment/system_instructions_deployer.py`)  
**Output**: `.claude-mpm/PM_INSTRUCTIONS_DEPLOYED.md`

```python
# Pseudocode
deployed = merge(
    resolve_block("PM_INSTRUCTIONS.md"),
    resolve_block("AGENT_DELEGATION.md"),
    resolve_workflow_block("WORKFLOW.md"),  # special lazy-load logic
    resolve_block("MEMORY.md")
)
write(".claude-mpm/PM_INSTRUCTIONS_DEPLOYED.md", deployed)
```

### Deployment Result

The deployed file contains 4 sections separated by `---`:

```markdown
---
# First: PM_INSTRUCTIONS (PM core identity)
## PM Core Identity
...

---
# Second: AGENT_DELEGATION (available capabilities)
## Available Agent Capabilities
...

---
# Third: WORKFLOW (or reference stub)
## Mandatory 5-Phase Sequence
... or ...
[WORKFLOW_SYSTEM_REFERENCE stub]

---
# Fourth: MEMORY (static guidance)
## Static Memory Management
...
```

### PM Prompt Assembly (Runtime)

At runtime, the PM's system instructions come from this deployed file. No re-assembly occurs; the file is read as-is.

---

## The Subagent Prompt Pipeline

Each subagent's prompt is built once at **deploy time**, not at runtime. The prompt is stored in `.claude/agents/<name>.md`.

### Build Source

Subagent prompts come from **agent template files**:

- External sources: agents from bobmatnyc/claude-mpm-agents repo (JSON or Markdown)
- Project-local sources: custom agents in `.claude/agents/` (if defined in templates)

Template discovery: recursive search through `~/.claude-mpm/cache/agents/` and project locations.

### Build Process

**Component**: `AgentTemplateBuilder.build_agent_markdown()` (`src/claude_mpm/services/agents/deployment/agent_template_builder.py`)

The builder:

1. **Parses the template** (JSON or Markdown with YAML frontmatter)
2. **Extracts and normalizes** agent metadata:
   - Tools (default: Read, Write, Edit, Grep, Glob, Bash)
   - Model (mapped to sonnet/haiku/opus)
   - Effort level (injected from resource_tier if missing)
   - Description, type, version, color, etc.
3. **Generates YAML frontmatter** (Claude Code compatible)
4. **Discovers and composes BASE templates**:
   - Hierarchical discovery: searches upward from agent template to repo root
   - Accepts both `BASE-AGENT.md` (external repos) and `BASE_AGENT.md` (framework)
   - Order: agent-specific instructions + local BASE + parent BASE + ... + root BASE
5. **Handles legacy fallback**: if no hierarchical BASE-AGENT.md found, uses `BASE_{TYPE}.md` (e.g., `BASE_ENGINEER.md`)
6. **Returns complete markdown** (frontmatter + composed content)

### BASE Template Composition

BASE templates are discovered hierarchically by walking the directory tree from the agent file location to the repo root:

```
repo/
  BASE_AGENT.md           # Composed last (root)
  engineering/
    BASE_AGENT.md         # Composed second (parent)
    python/
      BASE_AGENT.md       # Composed first (local)
      fastapi-engineer.md # Agent template

# Composed order:
1. Agent-specific instructions (from fastapi-engineer.md)
2. LOCAL BASE: engineering/python/BASE_AGENT.md
3. PARENT BASE: engineering/BASE_AGENT.md
4. ROOT BASE: repo/BASE_AGENT.md
```

All parts are joined with `\n\n---\n\n` separator.

**Why hierarchical**: Allows per-directory or per-subdomain overrides of base instructions (e.g., Python-specific vs. general engineering).

### Deployment Result

After building, the complete markdown is written to `.claude/agents/<name>.md`:

```markdown
---
name: fastapi-engineer
description: |
  Builds FastAPI services with type hints and async patterns.
  
  When to use: REST API development, async endpoint implementation.
model: sonnet
effort: balanced
type: engineer
---

# FastAPI Engineer

[Agent-specific instructions from template]

---

# Base Agent Instructions (Root Level)

[BASE_AGENT.md from engineering/python/]

---

# Engineering Team Standards

[BASE_AGENT.md from engineering/]

---

# Base Agent Instructions (Root Level)

[BASE_AGENT.md from repo root]
```

### Subagent Prompt Assembly (Runtime)

At runtime, Claude Code reads the deployed `.claude/agents/<name>.md` file as-is. No re-composition occurs.

When a subagent is invoked:
1. Claude Code discovers the agent in `.claude/agents/`
2. Reads the frontmatter (name, model, effort, etc.)
3. Reads the markdown body (all composed BASE templates + agent-specific instructions)
4. Creates a subagent session with these instructions

---

## Build-vs-Runtime Boundary

### What Happens at Build Time (Deployment)

- ✅ PM system instructions are merged and written to `.claude-mpm/PM_INSTRUCTIONS_DEPLOYED.md`
- ✅ Each subagent template is parsed, BASE templates discovered, and composed markdown written to `.claude/agents/<name>.md`
- ✅ Frontmatter is generated (YAML: name, model, description, effort, etc.)
- ✅ All override resolution (user, project, system defaults) is performed

### What Happens at Runtime

- ✅ PM reads `.claude-mpm/PM_INSTRUCTIONS_DEPLOYED.md` (already merged)
- ✅ Subagents read their deployed `.claude/agents/<name>.md` files (already composed)
- ❌ No re-merging, re-composition, or override resolution occurs
- ❌ No BASE template discovery or hierarchical walking happens

### Implications

1. **Durability**: Agents see a stable, pre-composed prompt throughout their lifecycle
2. **Performance**: No runtime parsing or file I/O for prompt assembly
3. **Testability**: Build artifacts can be inspected and validated before deployment
4. **Debugging**: "What prompt does the agent see?" → read the deployed file, not logs

---

## Subagent Capability Limits

Subagents **cannot** invoke the `Agent` tool or `Task` tool directly. These are harness-enforced limits, not MPM-code-enforced.

### Allowed Tools

Subagents receive the standard Claude Code tool set:
- File operations: `Read`, `Write`, `Edit`, `Grep`, `Glob`
- Command execution: `Bash`
- Web operations: `WebSearch`, `WebFetch`
- Notebook operations: `NotebookRead`, `NotebookEdit`
- Task management: `TodoWrite`, `ExitPlanMode` (if configured)

### Restricted Tools

Subagents **do not** have:
- `Agent` — cannot spawn other subagents
- `Task` — cannot create or manage tasks
- `Skill` — cannot invoke Duetto skills (project-specific)

These restrictions are enforced by Claude Code's harness, not by MPM configuration.

**Rationale**: Subagents are leaf nodes in the agent tree. Only the PM can delegate to other subagents. This prevents uncontrolled agent proliferation and maintains a clear chain of command.

---

## Build → Deploy → Runtime Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                         BUILD PHASE                         │
│              (CLI startup or explicit rebuild)              │
└─────────────────────────────────────────────────────────────┘

                    PM Prompt Pipeline
                         │
                         ├─→ src/claude_mpm/agents/PM_INSTRUCTIONS.md
                         ├─→ src/claude_mpm/agents/AGENT_DELEGATION.md
                         ├─→ src/claude_mpm/agents/WORKFLOW.md
                         ├─→ src/claude_mpm/agents/MEMORY.md
                         │
                         ├─→ ~/.claude-mpm/*.md (user overrides)
                         ├─→ .claude-mpm/*.md (project overrides)
                         │
    SystemInstructionsDeployer
                         │
                         └─→ .claude-mpm/PM_INSTRUCTIONS_DEPLOYED.md


                  Subagent Pipeline (per agent)
                         │
                  Template Discovery
    ~/.claude-mpm/cache/agents/ or .claude/agents/
                         │
      AgentTemplateBuilder.build_agent_markdown()
                         │
                    Parse Template (JSON or Markdown)
                         │
             Discover BASE-AGENT.md Hierarchy
                         │
             engineering/python/BASE-AGENT.md
             engineering/BASE-AGENT.md
             repo/BASE_AGENT.md
                         │
      Compose: agent-specific + BASE (closest to farthest)
                         │
      Generate YAML Frontmatter (Claude Code compatible)
                         │
      return: complete markdown (frontmatter + content)
                         │
                         └─→ .claude/agents/<name>.md


┌─────────────────────────────────────────────────────────────┐
│                      DEPLOY PHASE                           │
│        (When agent files are written to .claude/agents/)    │
└─────────────────────────────────────────────────────────────┘

            Files exist on disk, durable until next rebuild


┌─────────────────────────────────────────────────────────────┐
│                      RUNTIME PHASE                          │
│          (Claude Code session with deployed agents)         │
└─────────────────────────────────────────────────────────────┘

                    PM Runtime
                         │
         reads .claude-mpm/PM_INSTRUCTIONS_DEPLOYED.md
                    as-is (no re-merge)
                         │
                  [PM session starts]
                    [No re-composition]


                  Subagent Runtime (per invocation)
                         │
    Claude Code discovers .claude/agents/<name>.md
                         │
       Reads frontmatter (name, model, effort, etc.)
                         │
       Reads markdown body (all BASE + agent-specific)
                         │
                [Subagent session starts]
                   [No re-discovery, no re-composition]
                         │
               Subagent sees stable prompt
            (exactly as deployed, including all BASE)
```

---

## BASE_AGENT.md vs base_agent.json

### BASE_AGENT.md

**Status**: Active, the canonical source of truth  
**Location**: `src/claude_mpm/agents/BASE_AGENT.md`  
**Role**: Human-readable markdown containing instructions that are composed into every subagent

**Content includes**:
- Git workflow standards
- Memory routing
- Handoff protocol
- Proactive code quality
- Agent responsibilities
- Verification requirements
- Credential testing policy
- And more...

**How it's used**:
1. Discovered hierarchically during agent template building
2. Read and composed into each agent's final markdown
3. Duplicated across every deployed agent (token cost is N agents × lines in BASE_AGENT.md)

### base_agent.json (Legacy, Removed)

**Status**: Removed  
**Was located**: `src/claude_mpm/agents/base_agent.json`  
**Why removed**: Inert build bloat

The legacy JSON file had a `narrative_fields.instructions` field, but the deployment builder never used it. It only looked for top-level `instructions` or `content` keys, neither of which existed in the JSON. As a result:
- The file was never read during the build
- The `narrative_fields.instructions` were unreachable
- It served no purpose

**Migration**: All content is now in `BASE_AGENT.md` (markdown), which is actually composed.

### NAME NORMALIZATION BUG

There is a known **hyphen/underscore discovery mismatch** in the agent loader:

- **Framework**: `BASE_AGENT.md` (underscore)
- **External repos**: `BASE-AGENT.md` (hyphen)

The `AgentTemplateBuilder._discover_base_agent_templates()` checks for **both**:

```python
for base_name in ("BASE-AGENT.md", "BASE_AGENT.md"):
    base_agent_file = current_dir / base_name
    if base_agent_file.exists():
        base_templates.append(base_agent_file)
        break  # Accept first match, stop looking
```

This is intentional and robust. However, it means:
- `BASE_AGENT.md` and `BASE-AGENT.md` cannot coexist in the same directory
- External repos use `BASE-AGENT.md` (hyphen) by convention
- The framework source (`src/claude_mpm/agents/`) uses `BASE_AGENT.md` (underscore)

**Why not standardize?** The external agents repo (bobmatnyc/claude-mpm-agents) expects hyphenated agent names. Changing the framework source to use hyphens would create unnecessary noise in the codebase.

---

## Key Components

### SystemInstructionsDeployer

**Module**: `src/claude_mpm/services/agents/deployment/system_instructions_deployer.py`

Responsible for:
- Resolving PM instruction blocks with override semantics
- Handling the special lazy-load logic for WORKFLOW.md
- Detecting stale override files (containing content from multiple blocks)
- Writing merged content to `.claude-mpm/PM_INSTRUCTIONS_DEPLOYED.md`
- Watching source files for rebuild triggers

**Key Methods**:
- `deploy_system_instructions()` — main entry point
- `_resolve_block()` — additive override resolution
- `_resolve_workflow_block()` — lazy-load workflow logic
- `_detect_stale_override()` — warn about stale deployed files

### AgentTemplateBuilder

**Module**: `src/claude_mpm/services/agents/deployment/agent_template_builder.py`

Responsible for:
- Parsing agent templates (JSON or Markdown)
- Discovering BASE templates hierarchically
- Composing agent-specific + BASE instructions
- Generating Claude Code compatible YAML frontmatter
- Injecting resource_tier defaults (model/effort)
- Normalizing tools, models, and metadata
- Returning complete agent markdown

**Key Methods**:
- `build_agent_markdown()` — main entry point
- `_discover_base_agent_templates()` — hierarchical discovery
- `_parse_markdown_template()` — parse YAML frontmatter
- `_create_multiline_description()` — format description for Claude Code

### Agent Filters

**Module**: `src/claude_mpm/utils/agent_filters.py`

Responsible for:
- Filtering out BASE_AGENT from user-facing agent lists
- Detecting deployed agents (both virtual and physical)
- Managing local_only agent allow-lists
- Normalizing agent IDs for comparison

**Key Functions**:
- `is_base_agent()` — check if agent is BASE_AGENT (case-insensitive)
- `get_deployed_agent_ids()` — check `.mpm_deployment_state` or physical `.md` files
- `normalize_agent_id()` — canonical kebab-case normalizer
- `is_local_only()` — check if agent is project-managed

---

## See Also

- [Architecture](./ARCHITECTURE.md) — System design and core concepts
- [Subagent Patterns](../CLAUDE.md#-subagent-patterns) — How to invoke subagents
- [Code Contracts](./features/code-contracts.md) — Contract-based testing
- Agent template discovery: `~/.claude-mpm/cache/agents/`
- Framework agents: `src/claude_mpm/agents/`
