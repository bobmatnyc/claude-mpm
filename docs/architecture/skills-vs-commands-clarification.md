# Skills vs. Slash Commands: Terminology Clarification

**Status:** Active - Architectural Documentation
**Created:** 2026-01-07
**Purpose:** Clarify the distinction between framework skills and user slash commands

## The Problem

The PM and documentation currently conflate two different concepts under the term "skills":

1. **Framework Skills** - Knowledge loaded into agent context
2. **User Slash Commands** - Commands the USER invokes (e.g., `/mpm-init`)

This causes confusion when users ask "what skills do you have?"

## Terminology Definitions

### Framework Skills

**What they are:**
- Markdown files with domain knowledge/workflows
- Located in `.claude/skills/` or bundled in the framework
- Loaded automatically into agent context
- Examples: `systematic-debugging`, `git-workflow`, `json-data-handling`

**How agents use them:**
- Skills are **context** - they enhance agent capabilities
- Agents DO NOT "invoke" skills - skills ARE part of the agent's knowledge
- Listed in agent YAML frontmatter under `skills:` field

**Example:**
```yaml
# In agent definition
skills:
  - systematic-debugging
  - git-workflow
  - verification-before-completion
```

### User Slash Commands (User-Level Skills)

**What they are:**
- Command files in `src/claude_mpm/commands/*.md`
- User-invokable commands like `/mpm-init`, `/mpm-status`, `/mpm-doctor`
- Execute specific framework operations

**How they work:**
- USER types `/mpm-init` in Claude Code
- Framework routes to appropriate handler
- PM can DESCRIBE what they do, but cannot EXECUTE them

**Example:**
```bash
# User types in Claude Code:
/mpm-init update

# PM should respond:
"The /mpm-init command initializes or updates your project. To run it, type '/mpm-init' in the chat."
```

## The Skill Tool Confusion

The `Skill` tool in Claude Code's system prompt shows:

```xml
<available_skills>
<skill>
<name>mpm</name>
<description>Access Claude MPM functionality...</description>
<location>user</location>
</skill>
...
</available_skills>
```

**This is misleading** because:
- These are **user commands**, not "skills" the PM can invoke
- The PM should DESCRIBE these commands, not try to CALL them
- Only the USER can invoke slash commands

## Correct PM Behavior

### When User Asks "What skills do you have?"

**PM should respond:**

> "I have access to several **framework skills** that enhance my capabilities:
>
> **Project Management:**
> - `mpm-delegation-patterns` - How to delegate to specialized agents
> - `mpm-pr-workflow` - Branch protection and PR creation
> - `mpm-verification-protocols` - QA verification requirements
>
> **Development:**
> - `systematic-debugging` - Root cause analysis methodology
> - `git-workflow` - Essential Git patterns
> - `test-driven-development` - TDD workflows
>
> **Toolchains:**
> - `toolchains-python-tooling-mypy` - Python type checking with mypy
> - `toolchains-typescript-core` - Advanced TypeScript patterns
> - `toolchains-javascript-frameworks-svelte` - Svelte 5 development
>
> These skills are loaded into my context automatically and guide how I approach tasks.
>
> Additionally, you can invoke **slash commands** like:
> - `/mpm-init` - Initialize or update project
> - `/mpm-status` - Show system status
> - `/mpm-doctor` - Run diagnostic checks
> - `/mpm-configure` - Interactive configuration
>
> Type any `/mpm-*` command to use Claude MPM features."

### When User Asks About a Slash Command

**Example: "What does /mpm-init do?"**

**PM should respond:**

> "The `/mpm-init` command initializes or intelligently updates your project for Claude Code and Claude MPM.
>
> **Main modes:**
> - Project setup and updates
> - Context analysis from git history
> - Resume from previous sessions
>
> **To use it:**
> ```
> /mpm-init                # Auto-detect mode
> /mpm-init update         # Quick update
> /mpm-init context        # Analyze git history
> /mpm-init resume         # Resume from logs
> ```
>
> Type `/mpm-init` to run it interactively."

**PM should NOT:**
- Try to "invoke" the `/mpm-init` skill
- Call the `Skill` tool with `skill: "mpm-init"`
- Attempt to execute the command on behalf of the user

## Required Changes

### 1. Update PM Instructions

**File:** `.claude/agents/pm.md` (or wherever PM instructions live)

**Add section:**
```markdown
## Understanding Skills vs. Slash Commands

### Framework Skills (You USE These)
Skills listed in your agent definition (like `mpm-delegation-patterns`) are **loaded context** that enhance your capabilities. You don't "invoke" them - they're part of your knowledge base.

### Slash Commands (Users RUN These)
Commands like `/mpm-init`, `/mpm-status`, `/mpm-configure` are **user-invokable commands**. When users ask about them:
- DESCRIBE what they do
- EXPLAIN how to use them
- DO NOT try to invoke them via the Skill tool

**Example:**
- ❌ Bad: "I'll invoke the /mpm-init skill for you"
- ✅ Good: "To initialize your project, type '/mpm-init' in the chat"
```

### 2. Update Skill Tool Description

**File:** Wherever the `Skill` tool is defined in the system prompt

**Current (confusing):**
```
When users ask you to run a "slash command" or reference "/<something>" (e.g., "/commit", "/review-pr"), they are referring to a skill. Use this tool to invoke the corresponding skill.

<available_skills>
<skill>
<name>mpm</name>
...
</skill>
</available_skills>
```

**Proposed (clear):**
```
<skills_instructions>
### Framework Skills (Loaded Context)
Skills provide specialized domain knowledge and workflows that enhance agent capabilities. Agents DO NOT invoke skills - skills ARE part of the agent's context.

When listed in agent definitions (YAML frontmatter), skills like `systematic-debugging` or `git-workflow` are automatically loaded into the agent's knowledge.

### User Commands (Slash Commands)
The skills listed in <available_skills> below are USER-INVOKABLE COMMANDS, not skills you can invoke. When users ask about `/mpm-init`, `/mpm-status`, etc.:

- DESCRIBE what the command does
- EXPLAIN how to use it
- DO NOT try to invoke it

Only the USER can execute slash commands by typing them in Claude Code.

<available_skills>
<skill>
<name>mpm</name>
<description>Access Claude MPM functionality - USER COMMAND, not invokable by agents</description>
<location>user</location>
</skill>
...
</available_skills>
</skills_instructions>
```

### 3. Update Documentation

**File:** `docs/guides/skills-system.md`

**Add section** "Skills vs. Slash Commands" explaining:
- Framework skills = loaded context for agents
- Slash commands = user-invokable MPM operations
- How the PM should describe each

## Implementation Priority

1. **High Priority:** Update PM instructions (immediate fix for user confusion)
2. **Medium Priority:** Update Skill tool description (requires framework change)
3. **Low Priority:** Update documentation (helps future users understand)

## Testing

After implementing changes, test that PM responds correctly to:

1. "What skills do you have?"
   - Should list framework skills, not slash commands
   - Should mention slash commands separately

2. "What is /mpm-init?"
   - Should describe the command
   - Should NOT try to invoke it

3. "Run /mpm-init for me"
   - Should explain that USER must type the command
   - Should NOT call Skill tool

## References

- **Framework Skills Location:** `.claude/skills/` or bundled in `src/claude_mpm/skills/bundled/`
- **Slash Commands Location:** `src/claude_mpm/commands/*.md`
- **Skill Registry:** `src/claude_mpm/skills/registry.py`
- **Command Routing:** `src/claude_mpm/cli/commands/`
