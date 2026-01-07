# Agent Memory Injection Investigation

**Research Date:** 2025-12-20
**Researcher:** Claude Research Agent
**Status:** COMPLETE - Root cause identified

## Executive Summary

ALL agent memories (engineer.md, qa.md, research.md, etc.) are being incorrectly embedded into PM_INSTRUCTIONS.md. This is wrong - each agent's memory should only be appended to THAT agent's instructions when the agent is spawned via the Task tool.

**Root Cause:** The `MemoryProcessor` and `ContentFormatter` classes are injecting ALL agent memories into the PM instructions during framework loading, rather than injecting agent-specific memories only when individual agents are loaded.

## Current Problem

### Evidence

1. **PM_INSTRUCTIONS.md contains ALL agent memories:**
```bash
$ grep -n "## Agent Memories" .claude-mpm/PM_INSTRUCTIONS.md
2062:## Agent Memories
```

2. **Memory files exist for multiple agents:**
```bash
.claude-mpm/memories/
├── engineer.md
├── engineer_memories.md
├── ops.md
├── ops_memories.md
├── qa_memories.md
├── research_memories.md
├── security_memories.md
└── version_control_memories.md
```

3. **All memories are embedded in PM instructions:**
```markdown
## Agent Memories

**The following are accumulated memories from specialized agents:**

### Documentation Agent Memory
# Agent Memory: documentation

### Engineer Agent Memory
# Agent Memory: engineer

### Ops Agent Memory
# Agent Memory: ops

### Qa Agent Memory
# Agent Memory: qa

### Research Agent Memory
# Agent Memory: research

### Security Agent Memory
# Agent Memory: security
```

## Code Flow Analysis

### Memory Injection Path (WRONG - Current Behavior)

```
FrameworkLoader.__init__()
└── _load_framework_content()
    └── _load_actual_memories(content)
        └── MemoryManager.load_memories()
            └── MemoryProcessor.load_agent_memories(deployed_agents)
                ├── Loads ALL agent memory files from .claude-mpm/memories/
                └── Returns: {"agent_memories": {"engineer": "...", "qa": "...", ...}}

FrameworkLoader.get_framework_instructions()
└── _format_full_framework()
    └── ContentFormatter.format_full_framework(framework_content, ...)
        └── Injects ALL agent_memories into PM instructions
            ```python
            # Line 103-115 in content_formatter.py
            if framework_content.get("agent_memories"):
                agent_memories = framework_content["agent_memories"]
                if agent_memories:
                    instructions += "\n\n## Agent Memories\n\n"
                    instructions += "**The following are accumulated memories from specialized agents:**\n\n"

                    for agent_name in sorted(agent_memories.keys()):
                        memory_content = agent_memories[agent_name]
                        if memory_content:
                            instructions += f"### {agent_name.replace('_', ' ').title()} Agent Memory\n\n"
                            instructions += memory_content
                            instructions += "\n\n"
            ```
```

### Where PM_INSTRUCTIONS.md is Generated

**File:** `src/claude_mpm/core/framework_loader.py`

```python
# Line 316-329
def get_framework_instructions(self) -> str:
    """Get formatted framework instructions for injection."""
    self._log_system_prompt()

    if self.framework_content["loaded"]:
        return self._format_full_framework()  # ← PROBLEM HERE
    return self._format_minimal_framework()

def _format_full_framework(self) -> str:
    """Format full framework instructions using modular components."""
    # ... generates capabilities and context sections ...

    # Format the complete framework
    return self.content_formatter.format_full_framework(
        self.framework_content,  # ← Contains ALL agent_memories
        capabilities_section,
        context_section,
        inject_output_style,
        output_style_content,
    )
```

### Memory Loading (WRONG - Loads ALL Memories)

**File:** `src/claude_mpm/core/framework/processors/memory_processor.py`

```python
# Line 52-88
def load_agent_memories(self, deployed_agents: Set[str]) -> Dict[str, str]:
    """Load memories for deployed agents.

    Args:
        deployed_agents: Set of deployed agent names

    Returns:
        Dictionary mapping agent names to their memory content
    """
    agent_memories = {}

    # Define memory file search locations
    memory_locations = [
        Path.cwd() / ".claude-mpm" / "memories",  # Project memories
        Path.home() / ".claude-mpm" / "memories",  # User memories
    ]

    for agent_name in deployed_agents:
        memory_filename = f"{agent_name}_memories.md"

        # Search for memory file in each location (project takes precedence)
        for memory_dir in memory_locations:
            memory_file = memory_dir / memory_filename
            if memory_file.exists():
                try:
                    content = memory_file.read_text()
                    agent_memories[agent_name] = content  # ← LOADS ALL
                    self.logger.debug(
                        f"Loaded memories for {agent_name} from {memory_file}"
                    )
                    break  # Use first found (project > user)
                except Exception as e:
                    self.logger.error(
                        f"Failed to load memories for {agent_name}: {e}"
                    )

    return agent_memories  # ← Returns ALL agent memories
```

### Memory Injection into PM Instructions (WRONG)

**File:** `src/claude_mpm/core/framework/formatters/content_formatter.py`

```python
# Line 103-115
# Add agent memories if available
if framework_content.get("agent_memories"):
    agent_memories = framework_content["agent_memories"]
    if agent_memories:
        instructions += "\n\n## Agent Memories\n\n"
        instructions += "**The following are accumulated memories from specialized agents:**\n\n"

        for agent_name in sorted(agent_memories.keys()):
            memory_content = agent_memories[agent_name]
            if memory_content:
                instructions += f"### {agent_name.replace('_', ' ').title()} Agent Memory\n\n"
                instructions += memory_content
                instructions += "\n\n"
```

**PROBLEM:** This code iterates through ALL agent memories and embeds them into the PM instructions.

## Where Agent Instructions Are Loaded (Missing Memory Injection)

### Agent Deployment Process

When agents are deployed to `.claude/agents/`, the agent markdown files are written:

**File:** `src/claude_mpm/core/claude_runner.py` (Line 481-497)

```python
# Build the agent markdown using the pre-initialized service and base agent data
agent_content = (
    project_deployment.template_builder.build_agent_markdown(
        agent_name,
        json_file,
        base_agent_data,
        source_info="project",
    )
)

# Mark as project agent
agent_content = agent_content.replace(
    "author: claude-mpm", "author: claude-mpm-project"
)

# Write the agent file
is_update = target_file.exists()
target_file.write_text(agent_content)  # ← Agent markdown written to .claude/agents/
```

**MISSING:** No agent-specific memory injection happens here!

### Where Task Tool Spawns Agents

Task tool spawns agents by loading their markdown files from `.claude/agents/`:

**Evidence from code comments:**
```python
# From agent_loader.py
def get_deployed_agents(self) -> Set[str]:
    """
    Get a set of deployed agent names from .claude/agents/ directories.

    Returns:
        Set of agent names (file stems) that are deployed
    """
    # Check multiple locations for deployed agents
    agents_dirs = [
        Path.cwd() / ".claude" / "agents",  # Project-specific agents
        Path.home() / ".claude" / "agents",  # User's system agents
    ]
```

**PROBLEM:** When Task tool spawns an agent, it loads the agent markdown from `.claude/agents/`, but this markdown does NOT include the agent's specific memory file.

## Current Memory File Structure

### File Naming Patterns

Two naming patterns observed:
1. **Old format:** `{agent_name}_memories.md` (e.g., `engineer_memories.md`)
2. **New format:** `{agent_name}.md` (e.g., `engineer.md`)

**Files:**
```
.claude-mpm/memories/
├── documentation_memories.md  # Old format
├── engineer.md               # New format ✓
├── engineer_memories.md      # Old format
├── ops.md                    # New format ✓
├── ops_memories.md           # Old format
├── qa_memories.md            # Old format
├── research_memories.md      # Old format
├── security_memories.md      # Old format
└── version_control_memories.md  # Old format
```

**Note:** New format (`engineer.md`, `ops.md`) appears to be the current standard based on file modification times.

## Required Fix

### Solution Architecture

**REMOVE:** Agent memory injection from PM instructions
**ADD:** Agent-specific memory injection when individual agents are loaded

### Specific Code Changes Required

#### 1. REMOVE Agent Memories from PM Instructions

**File:** `src/claude_mpm/core/framework/formatters/content_formatter.py`

**Lines to REMOVE:** 103-115

```python
# REMOVE THIS SECTION:
# Add agent memories if available
if framework_content.get("agent_memories"):
    agent_memories = framework_content["agent_memories"]
    if agent_memories:
        instructions += "\n\n## Agent Memories\n\n"
        instructions += "**The following are accumulated memories from specialized agents:**\n\n"

        for agent_name in sorted(agent_memories.keys()):
            memory_content = agent_memories[agent_name]
            if memory_content:
                instructions += f"### {agent_name.replace('_', ' ').title()} Agent Memory\n\n"
                instructions += memory_content
                instructions += "\n\n"
```

#### 2. STOP Loading Agent Memories in FrameworkLoader

**File:** `src/claude_mpm/core/framework_loader.py`

**Option A:** Don't load agent memories at all in `_load_actual_memories()`

```python
# Line 254-261
def _load_actual_memories(self, content: Dict[str, Any]) -> None:
    """Load actual memories using the MemoryManager service."""
    memories = self._memory_manager.load_memories()

    if "actual_memories" in memories:
        content["actual_memories"] = memories["actual_memories"]
    # REMOVE THIS:
    # if "agent_memories" in memories:
    #     content["agent_memories"] = memories["agent_memories"]
```

**Option B:** Keep loading but don't inject into PM instructions (cleaner - allows future use)

Keep the loading code in `FrameworkLoader._load_actual_memories()` but just don't use it in `ContentFormatter.format_full_framework()`.

#### 3. ADD Agent Memory Injection to Agent Loading

**Target File:** `src/claude_mpm/services/agents/deployment/agent_template_builder.py` or similar

**Where to inject:** When agent markdown is built from template

**New Method:**
```python
def append_agent_memory(self, agent_name: str, agent_markdown: str) -> str:
    """Append agent-specific memory to agent markdown.

    Args:
        agent_name: Name of the agent (e.g., "engineer", "qa")
        agent_markdown: Base agent markdown content

    Returns:
        Agent markdown with memory appended
    """
    # Look for memory file in standard locations
    memory_locations = [
        Path.cwd() / ".claude-mpm" / "memories",
        Path.home() / ".claude-mpm" / "memories",
    ]

    # Try new format first (agent_name.md), then old format (agent_name_memories.md)
    memory_filenames = [
        f"{agent_name}.md",
        f"{agent_name}_memories.md",
    ]

    for memory_dir in memory_locations:
        for memory_filename in memory_filenames:
            memory_file = memory_dir / memory_filename
            if memory_file.exists():
                try:
                    memory_content = memory_file.read_text()
                    # Append memory to agent markdown
                    agent_markdown += "\n\n---\n\n"
                    agent_markdown += f"## {agent_name.title()} Agent Memory\n\n"
                    agent_markdown += memory_content
                    agent_markdown += "\n"

                    self.logger.info(f"Appended memory from {memory_file} to {agent_name}")
                    return agent_markdown
                except Exception as e:
                    self.logger.error(f"Failed to load memory for {agent_name}: {e}")

    # No memory found - return agent markdown unchanged
    self.logger.debug(f"No memory file found for {agent_name}")
    return agent_markdown
```

**Integration Point:** In `build_agent_markdown()` method:

```python
def build_agent_markdown(
    self,
    agent_name: str,
    json_file: Path,
    base_agent_data: Dict[str, Any],
    source_info: str = "unknown",
) -> str:
    """Build agent markdown from template."""
    # ... existing code to build agent markdown ...

    agent_content = # ... generated markdown ...

    # NEW: Append agent-specific memory
    agent_content = self.append_agent_memory(agent_name, agent_content)

    return agent_content
```

## Files to Modify

### 1. Remove Agent Memory Injection from PM Instructions

**File:** `src/claude_mpm/core/framework/formatters/content_formatter.py`
- **Lines:** 103-115
- **Action:** REMOVE the agent memories section

### 2. Stop Loading Agent Memories for PM

**File:** `src/claude_mpm/core/framework_loader.py`
- **Lines:** 254-261 (in `_load_actual_memories()`)
- **Action:** Comment out or remove agent_memories loading

### 3. Add Agent Memory Injection to Agent Loading

**File:** `src/claude_mpm/services/agents/deployment/agent_template_builder.py`
- **Action:** ADD new method `append_agent_memory()`
- **Action:** MODIFY `build_agent_markdown()` to call `append_agent_memory()`

### 4. Update MemoryProcessor (Optional - for clarity)

**File:** `src/claude_mpm/core/framework/processors/memory_processor.py`
- **Action:** Add docstring clarifying that `load_agent_memories()` is NOT for PM injection
- **Or:** Move this method to agent deployment context where it's actually needed

## Testing Strategy

### Verification Steps

1. **Before Fix:**
```bash
# Check PM instructions contain agent memories
grep -A 20 "## Agent Memories" .claude-mpm/PM_INSTRUCTIONS.md
# Should show ALL agent memories
```

2. **After Fix:**
```bash
# Check PM instructions do NOT contain agent memories
grep "## Agent Memories" .claude-mpm/PM_INSTRUCTIONS.md
# Should return nothing

# Check individual agent files contain their specific memories
grep "## Engineer Agent Memory" .claude/agents/engineer.md
# Should show engineer memory only
```

3. **Integration Test:**
- Deploy agents: `claude-mpm agents deploy`
- Check PM_INSTRUCTIONS.md has NO agent memories
- Check `.claude/agents/engineer.md` has engineer memory appended
- Check `.claude/agents/qa.md` has qa memory appended
- Verify each agent file has ONLY its own memory

## Related Files and Context

### Memory Loading Architecture

```
FrameworkLoader (PM context)
├── Loads PM memories: .claude-mpm/memories/PM.md ✓
└── Should NOT load agent memories ✗ (current bug)

AgentTemplateBuilder (Agent deployment context)
└── Should load agent-specific memory ✗ (missing feature)
```

### Agent Deployment Flow

```
claude-mpm agents deploy
└── AgentDeploymentService
    └── deploy_project_agents()
        └── template_builder.build_agent_markdown()
            ├── Reads agent JSON template
            ├── Builds agent markdown
            └── MISSING: Append agent memory ← FIX HERE
```

### Task Tool Agent Spawning

When PM delegates to an agent via Task tool:
1. Task tool reads agent markdown from `.claude/agents/{agent_name}.md`
2. Uses that markdown as the agent's instructions
3. **Expected:** Agent markdown should include agent-specific memory
4. **Current:** Agent markdown does NOT include memory (missing)

## Memory File Naming Convention

Based on file investigation:

**Standard Format:** `{agent_name}.md`
- `engineer.md`
- `ops.md`
- `qa.md`
- `research.md`

**Legacy Format:** `{agent_name}_memories.md`
- Still exists for backward compatibility
- Should support both formats in agent memory loading

## Summary

### Root Cause

Agent memories are being loaded and injected at the WRONG scope:
- **Current:** All agent memories → PM instructions (WRONG)
- **Correct:** Each agent memory → That agent's instructions (MISSING)

### Fix Strategy

1. **REMOVE** agent memory injection from `ContentFormatter.format_full_framework()`
2. **ADD** agent memory injection to `AgentTemplateBuilder.build_agent_markdown()`
3. **VERIFY** PM_INSTRUCTIONS.md has NO agent memories
4. **VERIFY** Each agent file in `.claude/agents/` has its own memory appended

### Impact

- PM instructions will be smaller (less token usage)
- Each agent will have access to its own memories when spawned
- Memories will be properly scoped to their respective agents
- No cross-agent memory pollution in PM context

## Next Steps

1. **Engineer Agent:** Implement the fix based on this research
2. **QA Agent:** Verify the fix with integration tests
3. **PM:** Coordinate deployment and validation

---

**Research Status:** COMPLETE
**Confidence Level:** HIGH (direct code analysis and file inspection)
**Recommended Action:** Proceed with implementation of proposed fix
