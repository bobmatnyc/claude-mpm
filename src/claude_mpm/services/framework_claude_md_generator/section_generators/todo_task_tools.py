"""
Todo and Task Tools section generator for framework CLAUDE.md.
"""

from typing import Any

from . import BaseSectionGenerator

# Baseline agents guaranteed to be in the list even when no .claude/agents/
# directory exists (e.g. in CI or during first-run initialisation).
_BASELINE_AGENTS: list[str] = [
    "research",
    "engineer",
    "qa",
    "documentation",
    "security",
    "ops",
    "version-control",
    "data-engineer",
    "pm",
]


def _get_deployed_agent_stems() -> list[str]:
    """Return sorted hyphen-stem list of currently deployed agents.

    Why: The list of valid ``subagent_type`` values must reflect agents that
    are actually deployed to ``.claude/agents/`` rather than a hardcoded
    snapshot that goes stale.  Using ``get_agent_name_map()`` guarantees the
    PM's instructions always enumerate the real set of available agents.

    What: Calls ``get_agent_name_map()`` (which scans ``.claude/agents/`` and
    the cache directory) and converts each stem to its hyphenated form.
    The result is de-duplicated against legacy ``-agent``-suffixed keys so
    callers see clean, canonical stems only.

    Fallback: If the import or scan fails for any reason, returns
    ``_BASELINE_AGENTS`` so the generator never produces an empty list.

    Test: In a project where ``code-critic.md`` is deployed, this function
    should include ``"code-critic"`` in its return value.
    """
    try:
        from claude_mpm.core.agent_name_registry import get_agent_name_map

        name_map = get_agent_name_map()
        stems: list[str] = []
        seen_names: set[str] = set()
        for stem, display_name in name_map.items():
            # Skip legacy -agent suffixed duplicates; only keep canonical stems.
            if stem.endswith("-agent"):
                continue
            if display_name in seen_names:
                continue
            seen_names.add(display_name)
            stems.append(stem)
        return sorted(stems) if stems else _BASELINE_AGENTS
    except Exception:
        return list(_BASELINE_AGENTS)


class TodoTaskToolsGenerator(BaseSectionGenerator):
    """Generates the Todo and Task Tools section."""

    def generate(self, data: dict[str, Any]) -> str:
        """Generate the todo and task tools section."""
        deployed_stems = _get_deployed_agent_stems()

        # Build the bullet list of valid subagent_type values dynamically.
        stem_bullets = "\n".join(
            f'- `subagent_type="{stem}"`' for stem in deployed_stems
        )

        return f"""
## B) TODO AND TASK TOOLS

### 🚨 MANDATORY: TodoWrite Integration with Task Tool

**Workflow Pattern:**
1. **Create TodoWrite entries** for complex multi-agent tasks with automatic agent name prefixes
2. **Mark todo as in_progress** when delegating via Task Tool
3. **Update todo status** based on subprocess completion
4. **Mark todo as completed** when agent delivers results

### Agent Name Prefix System

**Standard TodoWrite Entry Format:**
- **Research tasks** → `[Research] Analyze patterns and investigate implementation`
- **Documentation tasks** → `[Documentation] Update API reference and user guide`
- **Changelog tasks** → `[Documentation] Generate changelog for version 2.0`
- **QA tasks** → `[QA] Execute test suite and validate functionality`
- **DevOps tasks** → `[Ops] Configure deployment pipeline`
- **Security tasks** → `[Security] Perform vulnerability assessment`
- **Version Control tasks** → `[Version Control] Create feature branch and manage tags`
- **Version Management tasks** → `[Version Control] Apply semantic version bump`
- **Code Implementation tasks** → `[Engineer] Implement authentication system`
- **Data Operations tasks** → `[Data Engineer] Optimize database queries`

### Task Tool Subprocess Naming Conventions

**Task Tool Usage Pattern:**
```
Task(description="[task description]", subagent_type="[agent-type]")
```

**Valid subagent_type values (use lowercase format for Claude Code compatibility):**

**Required format (Claude Code expects these exact values from deployed agent YAML names — lowercase with hyphens):**
{stem_bullets}

**Note:** Claude Code's Task tool requires exact agent names as defined in the deployed agent YAML frontmatter. Per Claude Code's spec, all `name:` values are lowercase with hyphens (no `-agent` suffix, no underscores).

**Examples of Proper Task Tool Usage (must match deployed agent YAML names):**
- ✅ `Task(description="Update framework documentation", subagent_type="documentation")`
- ✅ `Task(description="Execute test suite validation", subagent_type="qa")`
- ✅ `Task(description="Create feature branch and sync", subagent_type="version-control")`
- ✅ `Task(description="Investigate performance patterns", subagent_type="research")`
- ✅ `Task(description="Implement authentication system", subagent_type="engineer")`
- ✅ `Task(description="Configure database and optimize queries", subagent_type="data-engineer")`
- ✅ `Task(description="Coordinate project tasks", subagent_type="pm")`
- ❌ `Task(description="Analyze code patterns", subagent_type="research-agent")` (WRONG - no '-agent' suffix in deployed name)
- ❌ `Task(description="Update API docs", subagent_type="Documentation")` (WRONG - lowercase only)
- ❌ `Task(description="Create release tags", subagent_type="version_control")` (WRONG - should be 'version-control')

### 🚨 MANDATORY: THREE SHORTCUT COMMANDS

#### 1. **"push"** - Version Control, Quality Assurance & Release Management
**Enhanced Delegation Flow**: PM → Documentation Agent (changelog & version docs) → QA Agent (testing/linting) → Data Engineer Agent (data validation & API checks) → Version Control Agent (tracking, version bumping & Git operations)

**Components:**
1. **Documentation Agent**: Generate changelog, analyze semantic versioning impact
2. **QA Agent**: Execute test suite, perform quality validation
3. **Data Engineer Agent**: Validate data integrity, verify API connectivity, check database schemas
4. **Version Control Agent**: Track files, apply version bumps, create tags, execute Git operations

#### 2. **"deploy"** - Local Deployment Operations
**Delegation Flow**: PM → Ops Agent (local deployment) → QA Agent (deployment validation)

#### 3. **"publish"** - Package Publication Pipeline
**Delegation Flow**: PM → Documentation Agent (version docs) → Ops Agent (package publication)

### Multi-Agent Coordination Workflows

**Example Integration:**
```
# TodoWrite entries with proper agent prefixes:
- ☐ [Documentation] Generate changelog and analyze version impact
- ☐ [QA] Execute full test suite and quality validation
- ☐ [Data Engineer] Validate data integrity and verify API connectivity
- ☐ [Version Control] Apply semantic version bump and create release tags

# Corresponding Task Tool delegations (must match deployed agent names):
Task(description="Generate changelog and analyze version impact", subagent_type="documentation")
Task(description="Execute full test suite and quality validation", subagent_type="qa")
Task(description="Validate data integrity and verify API connectivity", subagent_type="data-engineer")
Task(description="Apply semantic version bump and create release tags", subagent_type="version-control")

# Update TodoWrite status based on agent completions
```

---"""
