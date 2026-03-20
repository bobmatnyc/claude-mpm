# PM Instruction Override System

Claude MPM supports project-level and user-level customization of PM behavior through a layered file system. Override files live in `.claude-mpm/` (project) or `~/.claude-mpm/` (user).

## How to Ask the PM to Customize Itself

The PM understands customization requests and can generate override files for you. Just ask directly in natural language — no need to write the files by hand.

### Prompt examples

**Add project-specific rules:**
```
"Add a project rule that all commits must reference a JIRA ticket (PROJ-XXX format)"
"Remember that this project uses staging.example.com for QA — always verify deployments there"
"For this project, always use python-engineer instead of the generic engineer agent"
```

**Change agent routing:**
```
"Update agent delegation so all frontend work goes to react-engineer and all backend work goes to python-engineer"
"Add a rule: any task mentioning 'database' should go to the data-engineer agent"
```

**Customize workflow:**
```
"Add a security scan phase between implementation and QA in our workflow"
"Remove the documentation phase from the workflow — we maintain docs separately"
"Change our workflow: always run load tests after QA before marking work complete"
```

**Customize memory behavior:**
```
"Always store key architectural decisions in memory after we make them"
"Prefer kuzu-memory for all project knowledge — don't use static memory files"
```

**Reset or inspect:**
```
"Show me the current customization files for this project"
"What agent delegation rules are active right now?"
"Reset the workflow to the MPM default"
```

The PM will create or update the appropriate `.claude-mpm/` file and confirm what changed. Changes take effect at the next session startup (override files are loaded once at startup).

## Override Files

| File | Scope | Semantics | Purpose |
|------|-------|-----------|---------|
| `.claude-mpm/PM_INSTRUCTIONS_DEPLOYED.md` | Project | **Replaces** PM_INSTRUCTIONS.md entirely | Full PM prompt replacement |
| `.claude-mpm/AGENT_DELEGATION.md` | Project > User | **Replaces** default agent routing table | Custom agent assignment rules |
| `.claude-mpm/WORKFLOW.md` | Project > User > System | **Replaces** default workflow | Custom phase sequence |
| `.claude-mpm/MEMORY.md` | Project > User > System | **Replaces** default memory behavior | Custom memory instructions |
| `.claude-mpm/INSTRUCTIONS.md` | Project > User | **Appends** to PM_INSTRUCTIONS.md | Additive project-specific rules |
| `.claude-mpm/memories/PM_memories.md` | Project | **Accumulated** PM knowledge | PM learning, auto-maintained |

## Priority Order (highest → lowest)

```
Project .claude-mpm/   >   User ~/.claude-mpm/   >   System src/claude_mpm/agents/
```

## What Is Always Present (BASE_PM.md)

`BASE_PM.md` is appended **last**, regardless of any overrides. It contains:
- Framework identity (PM role in claude-mpm)
- Absolute prohibitions that cannot be overridden
- Circuit breaker reference

This means even a full `PM_INSTRUCTIONS_DEPLOYED.md` replacement retains the safety floor.

## Assembly Order at Startup

```
1. PM_INSTRUCTIONS.md  (or .claude-mpm/PM_INSTRUCTIONS_DEPLOYED.md if present)
2. + AGENT_DELEGATION.md  (project > user > system default)
3. + INSTRUCTIONS.md  (project/user append — additive)
4. + WORKFLOW.md  (project > user > system)
5. + MEMORY.md  (project > user > system + kuzu-memory auto-injection)
6. + memories/PM_memories.md  (accumulated knowledge)
7. + Agent capabilities  (dynamic, from deployed agents)
8. + Temporal/user context  (date, user, working directory)
9. + BASE_PM.md  (always — framework floor)
```

## kuzu-memory Auto-Detection

If `kuzu-memory` is installed (detected via `~/.local/pipx/venvs/kuzu-memory/` or `PATH`) AND no project-level `.claude-mpm/MEMORY.md` override exists, the memory section is automatically prefixed with kuzu-memory tool instructions:

```markdown
## Memory: kuzu-memory Active
kuzu-memory is installed. Use MCP tools for all memory operations:
- mcp__kuzu-memory__kuzu_recall — query before delegating research
- mcp__kuzu-memory__kuzu_learn — store decisions asynchronously
...
```

To suppress kuzu auto-injection (use default memory behavior instead), create an empty `.claude-mpm/MEMORY.md` or one with your own instructions.

## Common Customization Recipes

### Override agent routing for a project

Create `.claude-mpm/AGENT_DELEGATION.md`:
```markdown
# Agent Delegation — My Project

## Engineering
All code changes go to python-engineer (not generic engineer).
Use typescript-engineer only for frontend/ directory work.

## Routing
| Trigger | Agent |
|---------|-------|
| backend, api, database | python-engineer |
| frontend, ui, component | typescript-engineer |
...
```

### Add project-specific rules without replacing defaults

Create `.claude-mpm/INSTRUCTIONS.md`:
```markdown
## Project-Specific Rules

- All commits must reference a JIRA ticket (e.g. PROJ-123)
- Never modify files in vendor/ directly
- Use the staging environment at https://staging.example.com for QA verification
```

### Override workflow phases

Create `.claude-mpm/WORKFLOW.md` with your full workflow. This **replaces** the default 5-phase sequence entirely — include all phases you want.

### Replace PM entirely (advanced)

Create `.claude-mpm/PM_INSTRUCTIONS_DEPLOYED.md` with complete PM instructions. BASE_PM.md (prohibitions + circuit breakers) will still be appended. The system validates version numbers — if the deployed file is older than the installed PM_INSTRUCTIONS.md, the source version takes precedence.

## File Locations Quick Reference

```
your-project/
└── .claude-mpm/
    ├── AGENT_DELEGATION.md   # custom agent routing (replaces default)
    ├── WORKFLOW.md           # custom workflow phases (replaces default)
    ├── MEMORY.md             # custom memory behavior (replaces default)
    ├── INSTRUCTIONS.md       # additive project rules (appended)
    ├── PM_INSTRUCTIONS_DEPLOYED.md  # full PM replacement (advanced)
    └── memories/
        └── PM_memories.md    # accumulated PM knowledge (auto-maintained)

~/.claude-mpm/
├── AGENT_DELEGATION.md       # user-level agent routing override
├── WORKFLOW.md               # user-level workflow override
├── MEMORY.md                 # user-level memory override
└── INSTRUCTIONS.md           # user-level additive rules
```

## System Default Files

These are the defaults that your overrides replace:

```
src/claude_mpm/agents/
├── PM_INSTRUCTIONS.md        # full PM prompt
├── BASE_PM.md                # framework floor (always appended)
├── AGENT_DELEGATION.md       # default agent routing table
├── WORKFLOW.md               # default 5-phase workflow
└── MEMORY.md                 # default memory instructions
```
