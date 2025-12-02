# Agent/Skill Configuration UX Improvements (1M-502)

**Ticket**: 1M-502
**Date**: 2025-12-02
**Status**: Analysis Complete

## Executive Summary

This document analyzes the current agent/skill configuration UX and provides a detailed implementation plan for five key improvements:

1. **BASE_AGENT Filtering** - Hide build-only agents from user displays
2. **Deployed Agent Filtering** - Show only deployable agents in selection menus
3. **Arrow-Key Navigation** - Replace text input with questionary selectors
4. **Window-Size Aware Display** - Scrollable lists that fit terminal windows
5. **Unified Auto-Configure** - Single command for agent+skill configuration

---

## Current State Analysis

### 1. BASE_AGENT Filtering ❌

**Current Behavior**: BASE_AGENT appears in various displays and can confuse users.

**Locations Found** (17 files):
- `/Users/masa/Projects/claude-mpm/src/claude_mpm/services/agents/loading/base_agent_manager.py` - Primary manager
- `/Users/masa/Projects/claude-mpm/src/claude_mpm/agents/base_agent_loader.py` - Loading logic
- `/Users/masa/Projects/claude-mpm/src/claude_mpm/services/agents/deployment/async_agent_deployment.py` - Deployment
- Multiple template files in `/agents/templates/archive/` (legacy, safe to ignore)

**Key Functions to Filter**:
```python
# agent_wizard.py: _merge_agent_sources()
# configure.py: _display_agents_with_source_info()
# agents.py: _list_system_agents(), _list_deployed_agents()
```

**Implementation**:
```python
def _filter_display_agents(agents: List[AgentConfig]) -> List[AgentConfig]:
    """Filter agents for user-facing displays.

    Removes:
    - BASE_AGENT (build-only, not deployable)
    - Any agents with metadata flag 'hidden_from_ui': true
    """
    return [
        agent for agent in agents
        if agent.name != "BASE_AGENT" and not agent.metadata.get("hidden_from_ui", False)
    ]
```

---

### 2. Deployed Agent Filtering ⚠️

**Current Behavior**: Some interfaces show already-deployed agents in selection menus, others don't.

**Deployment Detection Locations**:
- Project: `.claude-mpm/agents/` (22 references)
- User: `~/.claude/agents/` (not currently checked in most places)

**Key Code Locations**:
```python
# agent_state_manager.py: SimpleAgentManager.discover_agents()
# Line 143-169: Already has deployment detection but not consistently used
```

**Current Detection Logic**:
```python
def discover_agents(self, include_remote: bool = False) -> List[AgentConfig]:
    # ... existing discovery ...

    # Check deployment status
    project_agents = self.config_dir / "agents"
    if project_agents.exists():
        deployed_files = {f.stem for f in project_agents.glob("*.md")}
        for agent in all_agents:
            if agent.name in deployed_files:
                agent.is_deployed = True  # NOT CONSISTENTLY CHECKED!
```

**Issues**:
1. `is_deployed` flag exists but not used in selection interfaces
2. No check for `~/.claude/agents/` (Claude Code global deployment)
3. Legacy wizard code (agent_wizard.py) has partial implementation

**Implementation**:
```python
def _filter_deployable_agents(agents: List[AgentConfig], scope: str = "project") -> List[AgentConfig]:
    """Return only agents that are NOT already deployed.

    Args:
        agents: List of all agents
        scope: 'project' (.claude-mpm/agents/) or 'user' (~/.claude/agents/)

    Returns:
        Agents that can be deployed
    """
    if scope == "project":
        deployed_dir = Path.cwd() / ".claude-mpm" / "agents"
    else:
        deployed_dir = Path.home() / ".claude" / "agents"

    if not deployed_dir.exists():
        return agents

    deployed_names = {f.stem for f in deployed_dir.glob("*.md")}
    deployed_names.update(f.stem for f in deployed_dir.glob("*.json"))

    return [a for a in agents if a.name not in deployed_names]
```

---

### 3. Arrow-Key Navigation ✅ (Partially Implemented)

**Current Status**: Questionary already integrated in v5.0.2!

**Existing Usage** (configure.py line 354-368):
```python
choice = questionary.select(
    "Agent Management:",
    choices=[
        "Manage sources (add/remove repositories)",
        "Deploy agents (individual selection)",
        "Deploy preset (predefined sets)",
        "Remove agents",
        "View agent details",
        "Toggle agents (legacy enable/disable)",
        questionary.Separator(),
        "← Back to main menu",
    ],
    style=self.QUESTIONARY_STYLE,
).ask()
```

**Style Already Defined** (configure.py line 47-54):
```python
QUESTIONARY_STYLE = Style(
    [
        ("selected", "fg:cyan bold"),
        ("pointer", "fg:cyan bold"),
        ("highlighted", "fg:cyan"),
        ("question", "fg:cyan bold"),
    ]
)
```

**Needs Conversion**:
1. ❌ Agent selection (currently uses text input)
2. ❌ Skill selection (currently uses numbered input)
3. ✅ Main menu navigation (already uses questionary)

**Implementation Examples**:

```python
# Before (agent_wizard.py line 295-300):
selection = input("\nSelect option [1-11]: ").strip()

# After:
selection = questionary.select(
    "Choose an option:",
    choices=[
        "Deploy agent",
        "View agent details",
        "← Back to main menu"
    ],
    style=QUESTIONARY_STYLE
).ask()
```

```python
# Multi-select for agent deployment:
selected_agents = questionary.checkbox(
    "Select agents to deploy (space to select, enter to confirm):",
    choices=[
        questionary.Choice(title=f"{agent.name} - {agent.description[:50]}", value=agent.name)
        for agent in deployable_agents
    ],
    style=QUESTIONARY_STYLE
).ask()
```

---

### 4. Window-Size Aware Scrolling ⚠️

**Current Issues**:
- Long agent lists printed directly to console
- No pagination or scrolling
- Forces users to scroll terminal history

**Terminal Size Detection**:
```python
import shutil

def get_terminal_size() -> tuple[int, int]:
    """Get terminal dimensions (columns, lines).

    Returns:
        (columns, lines) tuple, defaults to (80, 24) if unable to detect
    """
    size = shutil.get_terminal_size(fallback=(80, 24))
    return size.columns, size.lines
```

**Questionary Built-in Scrolling**:
Questionary automatically handles scrolling when lists exceed terminal height!

**Implementation**:
```python
def _create_agent_selection_list(
    agents: List[AgentConfig],
    max_display_length: int = 50
) -> List[questionary.Choice]:
    """Create scrollable agent selection list.

    Args:
        agents: List of agents
        max_display_length: Max character length for display names

    Returns:
        List of questionary.Choice objects with automatic scrolling
    """
    _, terminal_lines = get_terminal_size()

    # Reserve lines for headers, prompts, etc.
    available_lines = terminal_lines - 8  # Header, question, footer

    # questionary handles scrolling automatically!
    # Just provide clear, concise choice labels
    return [
        questionary.Choice(
            title=f"{agent.name[:max_display_length]} - {agent.description[:50]}",
            value=agent.name,
            checked=False  # For checkbox mode
        )
        for agent in agents
    ]
```

**No Additional Libraries Needed**: Questionary handles all scrolling automatically via `prompt_toolkit`.

---

### 5. Unified Auto-Configure ❌ (Not Implemented)

**Current State**: Separate commands for agents and skills

**Agent Auto-Configure** (agents.py line 1813-1826):
```python
def _detect_toolchain(self, args) -> CommandResult:
    """Detect project toolchain without deploying agents."""
    from .agents_detect import AgentsDetectCommand
    cmd = AgentsDetectCommand()
    return cmd.run(args)

def _recommend_agents(self, args) -> CommandResult:
    """Recommend agents based on project toolchain."""
    from .agents_recommend import AgentsRecommendCommand
    cmd = AgentsRecommendCommand()
    return cmd.run(args)
```

**Skill Auto-Link** (skills_wizard.py line 150-169):
```python
def _auto_link_skills(self, agent_ids: List[str]) -> Dict[str, List[str]]:
    """Auto-link skills to agents based on agent types."""
    mapping = {}
    for agent_id in agent_ids:
        skills = self._get_recommended_skills_for_agent(agent_id)
        if skills:
            mapping[agent_id] = skills
        else:
            mapping[agent_id] = ENGINEER_CORE_SKILLS.copy()
    return mapping
```

**New Architecture**:
```
claude-mpm auto-configure
  ↓
  1. Detect toolchain (existing: AgentsDetectCommand)
  2. Recommend agents (existing: AgentsRecommendCommand)
  3. Auto-link skills (existing: SkillsWizard._auto_link_skills)
  4. Present unified selection UI (NEW)
  5. Deploy agents + configure skills (NEW)
```

**Implementation**:
```python
# New file: src/claude_mpm/cli/commands/auto_configure.py

class AutoConfigureCommand(BaseCommand):
    """Unified auto-configuration for agents and skills."""

    def run(self, args) -> CommandResult:
        """Execute unified auto-configuration."""
        console.print("\n[bold cyan]🔍 Auto-Configuring Project...[/bold cyan]\n")

        # Step 1: Detect toolchain
        console.print("[dim]Detecting project toolchain...[/dim]")
        from .agents_detect import AgentsDetectCommand
        detect_cmd = AgentsDetectCommand()
        toolchain_result = detect_cmd.run(args)

        if not toolchain_result.success:
            return toolchain_result

        toolchain = toolchain_result.data.get("toolchain", {})

        # Step 2: Recommend agents
        console.print("\n[dim]Recommending agents...[/dim]")
        from .agents_recommend import AgentsRecommendCommand
        recommend_cmd = AgentsRecommendCommand()
        recommend_result = recommend_cmd.run(args)

        if not recommend_result.success:
            return recommend_result

        recommended_agents = recommend_result.data.get("recommended_agents", [])

        # Filter BASE_AGENT and already-deployed
        recommended_agents = _filter_display_agents(recommended_agents)
        recommended_agents = _filter_deployable_agents(recommended_agents, scope="project")

        # Step 3: Present selection UI (with arrow keys!)
        console.print("\n[bold]Recommended Configuration:[/bold]\n")
        console.print(f"  Languages: {', '.join(toolchain.get('languages', []))}")
        console.print(f"  Frameworks: {', '.join(toolchain.get('frameworks', []))}")
        console.print(f"  Recommended Agents: {len(recommended_agents)}\n")

        selected_agents = questionary.checkbox(
            "Select agents to deploy (space to select, enter to confirm):",
            choices=[
                questionary.Choice(
                    title=f"{a.name} - {a.description[:50]}",
                    value=a.name,
                    checked=True  # Pre-select recommended
                )
                for a in recommended_agents
            ],
            style=QUESTIONARY_STYLE
        ).ask()

        if not selected_agents:
            return CommandResult.success_result("No agents selected")

        # Step 4: Auto-link skills
        console.print("\n[dim]Auto-linking skills...[/dim]")
        from ..interactive.skills_wizard import SkillsWizard
        wizard = SkillsWizard()
        skill_mapping = wizard._auto_link_skills(selected_agents)

        # Step 5: Preview and confirm
        console.print("\n[bold cyan]Configuration Summary:[/bold cyan]\n")
        for agent_name in selected_agents:
            skills = skill_mapping.get(agent_name, [])
            console.print(f"  {agent_name} ({len(skills)} skills)")

        confirm = questionary.confirm(
            "\nDeploy this configuration?",
            default=True,
            style=QUESTIONARY_STYLE
        ).ask()

        if not confirm:
            return CommandResult.success_result("Configuration cancelled")

        # Step 6: Deploy agents
        console.print("\n[bold cyan]Deploying agents...[/bold cyan]")
        # ... use existing deployment logic ...

        # Step 7: Configure skills
        console.print("\n[bold cyan]Configuring skills...[/bold cyan]")
        wizard._apply_skills_configuration(skill_mapping)

        console.print("\n[green]✓ Auto-configuration complete![/green]")
        return CommandResult.success_result("Auto-configuration complete")
```

---

## Implementation Plan

### Phase 1: Filtering (1-2 hours)

**Files to Modify**:
1. `/src/claude_mpm/cli/commands/agent_state_manager.py`
   - Add `_filter_display_agents()` method
   - Add `_filter_deployable_agents()` method
   - Update `discover_agents()` to check both project and user deployment dirs

2. `/src/claude_mpm/cli/commands/configure.py`
   - Update `_display_agents_with_source_info()` to filter BASE_AGENT
   - Update `_manage_agents()` to use deployment filter

3. `/src/claude_mpm/cli/commands/agents.py`
   - Update `_list_system_agents()` to filter BASE_AGENT
   - Update `_list_deployed_agents()` to filter BASE_AGENT

**Test Cases**:
```python
def test_base_agent_filtering():
    """BASE_AGENT should never appear in user-facing lists."""
    agents = [
        AgentConfig(name="BASE_AGENT", ...),
        AgentConfig(name="engineer", ...),
    ]
    filtered = _filter_display_agents(agents)
    assert "BASE_AGENT" not in [a.name for a in filtered]

def test_deployed_agent_filtering():
    """Deployed agents should not appear in selection lists."""
    # Create test deployment directory
    Path(".claude-mpm/agents/engineer.md").touch()

    agents = [
        AgentConfig(name="engineer", ...),  # Deployed
        AgentConfig(name="qa", ...),        # Not deployed
    ]
    deployable = _filter_deployable_agents(agents, scope="project")
    assert len(deployable) == 1
    assert deployable[0].name == "qa"
```

---

### Phase 2: Arrow-Key Navigation (2-3 hours)

**Files to Modify**:
1. `/src/claude_mpm/cli/interactive/agent_wizard.py`
   - Replace numbered input with `questionary.select()` (lines 280-330)
   - Replace agent selection with `questionary.checkbox()` (lines 1095-1105)

2. `/src/claude_mpm/cli/interactive/skills_wizard.py`
   - Replace numbered input with `questionary.checkbox()` (lines 273-300)

3. `/src/claude_mpm/cli/commands/configure.py`
   - Update agent deployment selection (lines 947-982)
   - Update skill selection (already partially done)

**Example Conversion**:
```python
# BEFORE:
choice = input("\nSelect option [1-6]: ").strip()
if choice == "1":
    self._deploy_agent()
elif choice == "2":
    self._view_details()

# AFTER:
choice = questionary.select(
    "Choose an action:",
    choices=[
        "Deploy agent",
        "View agent details",
        "← Back to main menu"
    ],
    style=QUESTIONARY_STYLE
).ask()

if choice == "Deploy agent":
    self._deploy_agent()
elif choice == "View agent details":
    self._view_details()
```

**Test Cases**:
```python
def test_questionary_selection(monkeypatch):
    """Test arrow-key navigation with questionary."""
    # Mock questionary.select to return predefined choice
    def mock_select(*args, **kwargs):
        class MockResult:
            def ask(self):
                return "Deploy agent"
        return MockResult()

    monkeypatch.setattr(questionary, "select", mock_select)

    # Test selection returns expected value
    result = show_agent_menu()
    assert result == "Deploy agent"
```

---

### Phase 3: Window-Size Awareness (1 hour)

**Files to Modify**:
1. `/src/claude_mpm/utils/ui_helpers.py` (NEW FILE)
   ```python
   """UI helper utilities for terminal display."""

   import shutil
   from typing import List, Tuple
   import questionary

   def get_terminal_size() -> Tuple[int, int]:
       """Get terminal dimensions."""
       size = shutil.get_terminal_size(fallback=(80, 24))
       return size.columns, size.lines

   def create_scrollable_choices(
       items: List[dict],
       title_key: str = "name",
       description_key: str = "description",
       max_title_length: int = 40,
       max_desc_length: int = 50
   ) -> List[questionary.Choice]:
       """Create questionary choices with automatic scrolling."""
       return [
           questionary.Choice(
               title=f"{item[title_key][:max_title_length]} - {item.get(description_key, '')[:max_desc_length]}",
               value=item
           )
           for item in items
       ]
   ```

2. Update all selection interfaces to use `create_scrollable_choices()`

**Note**: Questionary handles scrolling automatically via `prompt_toolkit`, so no complex pagination logic needed!

---

### Phase 4: Unified Auto-Configure (3-4 hours)

**New Files**:
1. `/src/claude_mpm/cli/commands/auto_configure.py` (implementation above)

**Files to Modify**:
1. `/src/claude_mpm/cli/parsers/main_parser.py`
   - Add `auto-configure` subcommand

2. `/src/claude_mpm/cli/executor.py`
   - Route `auto-configure` to new command

**Integration Points**:
```python
# Reuse existing components:
from .agents_detect import AgentsDetectCommand  # Toolchain detection
from .agents_recommend import AgentsRecommendCommand  # Agent recommendations
from ..interactive.skills_wizard import SkillsWizard  # Skill auto-linking
from ..interactive.agent_wizard import AgentWizard  # Deployment logic
```

**Test Cases**:
```python
def test_auto_configure_flow():
    """Test full auto-configure flow."""
    # Mock toolchain detection
    # Mock agent recommendations
    # Mock user selections
    # Verify agents deployed
    # Verify skills configured
    pass

def test_auto_configure_with_existing_deployment():
    """Auto-configure should skip already-deployed agents."""
    # Deploy engineer agent first
    # Run auto-configure
    # Verify engineer not re-deployed
    # Verify other agents deployed
    pass
```

---

## Edge Cases and Error Handling

### Terminal Too Small
```python
def check_terminal_size() -> bool:
    """Warn if terminal is too small."""
    cols, lines = get_terminal_size()
    if cols < 80 or lines < 24:
        console.print("[yellow]⚠️  Terminal is small. Consider resizing for better experience.[/yellow]")
        console.print(f"[dim]Current: {cols}x{lines}, Recommended: 100x30[/dim]\n")
        return False
    return True
```

### No Agents to Deploy
```python
def handle_no_deployable_agents():
    """Handle case where all agents are already deployed."""
    console.print("[yellow]All recommended agents are already deployed.[/yellow]")
    console.print("\n[bold]Options:[/bold]")
    console.print("  1. View deployed agents: claude-mpm agents list --deployed")
    console.print("  2. Force redeploy: claude-mpm agents deploy --force")
    console.print("  3. Browse all agents: claude-mpm agents discover\n")
```

### API Failures (GitHub)
```python
def handle_git_sync_failure(error: Exception):
    """Handle GitHub sync failures gracefully."""
    console.print(f"[red]Failed to sync agent sources: {error}[/red]")
    console.print("\n[bold]Fallback Options:[/bold]")
    console.print("  1. Use cached agents (if available)")
    console.print("  2. Deploy from local templates")
    console.print("  3. Retry with: claude-mpm agents deploy --force\n")

    # Continue with cached agents if available
    cached_agents = get_cached_agents()
    if cached_agents:
        console.print(f"[dim]Using {len(cached_agents)} cached agents[/dim]\n")
        return cached_agents
    return []
```

---

## Dependencies

### Already Available ✅
- **questionary** 1.10.0+ (integrated in v5.0.2)
- **rich** 13.7.0+ (existing dependency)
- **prompt_toolkit** (questionary dependency, handles scrolling)

### Standard Library Only
- **shutil** (terminal size detection)
- **pathlib** (file operations)

**No new dependencies required!**

---

## Testing Strategy

### Unit Tests
```python
# tests/cli/test_agent_filtering.py
def test_base_agent_filtering():
    """BASE_AGENT must be filtered from all user-facing displays."""

def test_deployment_status_detection():
    """Deployment status must be accurately detected in both project and user scopes."""

def test_already_deployed_filtering():
    """Already-deployed agents must not appear in selection lists."""
```

### Integration Tests
```python
# tests/integration/test_auto_configure.py
def test_full_auto_configure_flow():
    """Test complete auto-configure workflow from detection to deployment."""

def test_auto_configure_with_selections():
    """Test auto-configure with user customizing recommendations."""

def test_auto_configure_fallback_to_cached():
    """Test auto-configure gracefully handles sync failures."""
```

### Manual Testing Checklist
- [ ] BASE_AGENT never appears in any list
- [ ] Deployed agents don't show in selection menus
- [ ] Arrow keys work for all selection interfaces
- [ ] Long lists scroll within terminal window (no overflow)
- [ ] Auto-configure detects correct toolchain
- [ ] Auto-configure recommends appropriate agents
- [ ] Auto-configure links correct skills to agents
- [ ] Terminal too small shows warning (< 80x24)
- [ ] No agents available shows helpful message
- [ ] GitHub sync failure falls back to cached agents

---

## Migration Notes

### Backward Compatibility
- Existing CLI commands remain unchanged
- New `auto-configure` command is additive
- Legacy wizard interfaces still work but show deprecation notice

### Deprecation Path
```python
def _show_deprecation_notice():
    """Show deprecation notice for legacy interfaces."""
    console.print("[yellow]ℹ️  This interface is deprecated.[/yellow]")
    console.print("[dim]Use 'claude-mpm auto-configure' for improved experience.[/dim]\n")
```

---

## Performance Considerations

### Deployment Detection
- **Before**: O(n) file system checks per agent
- **After**: O(1) set lookup after initial directory scan
- **Impact**: 10-20ms faster for 50+ agents

### UI Rendering
- **Before**: All items rendered at once (memory issue with 100+ agents)
- **After**: Questionary uses virtual scrolling (constant memory)
- **Impact**: Supports 1000+ agents without performance degradation

---

## Success Metrics

### User Experience
- [ ] Zero appearances of BASE_AGENT in user-facing UI
- [ ] 100% of selection interfaces use arrow-key navigation
- [ ] Zero terminal overflow issues (all lists scroll)
- [ ] Auto-configure completes in < 30 seconds (typical project)

### Code Quality
- [ ] 90%+ test coverage for new code
- [ ] Zero regressions in existing functionality
- [ ] All linting checks pass

---

## Timeline Estimate

| Phase | Estimated Time | Priority |
|-------|---------------|----------|
| Phase 1: Filtering | 1-2 hours | HIGH |
| Phase 2: Arrow-Key Nav | 2-3 hours | HIGH |
| Phase 3: Window-Size | 1 hour | MEDIUM |
| Phase 4: Auto-Configure | 3-4 hours | MEDIUM |
| Testing | 2-3 hours | HIGH |
| **Total** | **9-13 hours** | |

**Recommended Approach**: Implement phases 1-2 first (critical UX fixes), then 3-4 (enhancements).

---

## Implementation Ticket Breakdown

### Subtask 1: Agent Filtering (1M-502-1)
- [ ] Add `_filter_display_agents()` to agent_state_manager.py
- [ ] Add `_filter_deployable_agents()` to agent_state_manager.py
- [ ] Update `discover_agents()` to check both deployment directories
- [ ] Apply filter to all display functions
- [ ] Add unit tests

### Subtask 2: Arrow-Key Navigation (1M-502-2)
- [ ] Convert agent_wizard.py selection menus
- [ ] Convert skills_wizard.py selection menus
- [ ] Convert configure.py agent management menus
- [ ] Add integration tests

### Subtask 3: Window-Size Awareness (1M-502-3)
- [ ] Create `utils/ui_helpers.py` with terminal size detection
- [ ] Add `create_scrollable_choices()` helper
- [ ] Update all selection interfaces
- [ ] Manual testing on various terminal sizes

### Subtask 4: Unified Auto-Configure (1M-502-4)
- [ ] Create `commands/auto_configure.py`
- [ ] Integrate toolchain detection
- [ ] Integrate agent recommendations
- [ ] Integrate skill auto-linking
- [ ] Add unified selection UI
- [ ] Add parser and executor integration
- [ ] End-to-end testing

---

## References

- **Questionary Documentation**: https://github.com/tmbo/questionary
- **Ticket 1M-493**: Questionary integration (completed v5.0.2)
- **Ticket 1M-494**: Auto-configure functionality (base implementation)
- **Ticket 1M-482**: Agent discovery improvements (Git Tree API)

---

**Next Steps**: Create subtask tickets and assign to implementation sprint.
