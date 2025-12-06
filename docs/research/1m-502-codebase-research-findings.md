# Research Findings: 1M-502 Agent/Skill Configuration UX Enhancements

**Ticket:** 1M-502
**Date:** 2025-12-06
**Research Focus:** Enhance agent/skill configuration UX with auto-discovery and improved navigation

## Executive Summary

This research identifies the code locations and implementations for enhancing agent/skill configuration UX per ticket 1M-502. The framework already has questionary integration (from 1M-493/v5.0.2) and BASE_AGENT filtering utilities. Key findings:

1. **BASE_AGENT filtering** exists in `/src/claude_mpm/utils/agent_filters.py` with comprehensive detection
2. **Questionary** is already integrated in both agent and skill wizards with arrow-key navigation
3. **Agent displays** happen in multiple locations with different filtering needs
4. **Skills configuration** has separate interactive and CLI paths
5. **Window-size aware displays** not currently implemented (opportunity for enhancement)

## Requirements Analysis

### Requirement 1: Filter BASE_AGENT from Displays

**Status:** ✅ Partially Implemented

**Current Implementation:**
- `/src/claude_mpm/utils/agent_filters.py` (lines 23-53)
  - `is_base_agent(agent_id)` - Detects BASE_AGENT (case-insensitive, path-aware)
  - `filter_base_agents(agents)` - Removes BASE_AGENT from lists
  - `apply_all_filters()` - Convenience function with filter_base flag

**Already Filtering:**
- `configure.py` line 362: `agents = self._filter_agent_configs(agents, filter_deployed=False)`
- `configure.py` line 589: `agents = self._filter_agent_configs(agents, filter_deployed=False)`
- `configure.py` line 657: `agents = self._filter_agent_configs(agents, filter_deployed=False)`
- `configure.py` line 790: `agents = self._filter_agent_configs(agents, filter_deployed=False)`
- `agent_wizard.py` line 226: `return apply_all_filters(agent_list, filter_base=True)`

**Needs Filtering Added:**
- Skills wizard displays (no BASE_AGENT currently, but good practice)
- Any new agent listing code

### Requirement 2: Show Only Undeployed Agents

**Status:** ⚠️ Partially Implemented with Issues

**Current Implementation:**
- `/src/claude_mpm/utils/agent_filters.py` (lines 83-202)
  - `get_deployed_agent_ids()` - Detects deployed agents via:
    1. Virtual deployment state (`.mpm_deployment_state`)
    2. Physical .md files (`.claude-mpm/agents/`, `.claude/agents/`)
  - `filter_deployed_agents()` - Removes deployed agents
  - `apply_all_filters()` - Can filter deployed when `filter_deployed=True`

**Usage Locations:**
```python
# configure.py line 1044 - Unified deployment interface
agents = filter_base_agents([...])  # Only filters BASE, keeps deployed visible

# configure.py line 1107 - Deploy agent interactive
deployable = apply_all_filters(
    available_agents, filter_base=True, filter_deployed=True
)
```

**Issue:** Checkbox interface (line 1044) shows ALL agents for unified install/remove, which is correct. But individual "deploy agent" option needs undeployed-only filtering.

### Requirement 3: Arrow-Key Navigation

**Status:** ✅ Implemented (v5.0.2)

**Questionary Integration:**
- `/src/claude_mpm/cli/commands/configure.py` (lines 47-60)
  - `QUESTIONARY_STYLE` - WCAG AAA compliant dark terminal theme
  - Gold pointer, light gray text, green checkboxes

**Usage Examples:**
```python
# configure.py line 380 - Agent management menu
choice = questionary.select(
    "Agent Management:",
    choices=[...],
    style=self.QUESTIONARY_STYLE,
).ask()

# configure.py line 1120 - Checkbox with pre-selection
selected_agent_ids = questionary.checkbox(
    "Agents:",
    choices=agent_choices,  # Choice objects with checked=True for pre-selection
    style=self.QUESTIONARY_STYLE
).ask()

# agent_wizard.py line 309 - Agent wizard menu navigation
choice = questionary.select(
    "Agent Management Menu:",
    choices=menu_choices,
    style=QUESTIONARY_STYLE,
).ask()
```

**Locations Already Using Questionary:**
1. `configure.py` - Agent management, deployment confirmation, action selection
2. `agent_wizard.py` - Agent browsing, filtering, deployment selection
3. `skills.py` - Skills configuration (line 957-1060)

### Requirement 4: Window-Size Aware Displays with Scrolling

**Status:** ❌ Not Implemented

**Opportunity for Enhancement:**

Current table displays use Rich with fixed column widths but no dynamic window sizing:

```python
# configure.py line 976 - Agent display table
agents_table.add_column("#", style="dim", width=4, no_wrap=True)
agents_table.add_column("Agent ID", style="white", width=35, no_wrap=True, overflow="ellipsis")
agents_table.add_column("Name", style="white", width=25, no_wrap=True, overflow="ellipsis")
```

**Implementation Needed:**
```python
import shutil

# Get terminal dimensions
terminal_width, terminal_height = shutil.get_terminal_size()

# Dynamic column sizing
id_width = min(35, terminal_width // 4)
name_width = min(25, terminal_width // 4)

# Pagination for long lists
if len(agents) > (terminal_height - 10):
    # Show paginated view with questionary or Rich pager
    pass
```

**Files to Modify:**
- `/src/claude_mpm/cli/commands/configure.py` - Agent table displays (lines 976-1030)
- `/src/claude_mpm/cli/interactive/agent_wizard.py` - Agent listing tables (lines 264-281)
- `/src/claude_mpm/cli/commands/skills.py` - Skills table displays (if added)

### Requirement 5: Unified Auto-Configure Command

**Status:** ⚠️ Separate Implementations Exist

**Current State:**

**Agents Auto-Configure:**
- Service: `/src/claude_mpm/services/agents/auto_config_manager.py`
- CLI: `/src/claude_mpm/cli/commands/agents.py` (agent-related commands)
- Command: `claude-mpm agents auto-configure` (likely)

**Skills Auto-Configure:**
- Service: `/src/claude_mpm/services/skills_deployer.py`
- CLI: `/src/claude_mpm/cli/commands/skills.py` (line 955-1202)
- Command: `claude-mpm skills configure` (interactive checkbox interface)

**Unification Opportunity:**

Create unified command that:
1. Auto-detects project toolchain
2. Recommends agents based on stack
3. Recommends skills based on agents selected
4. Deploys both in single workflow

**Proposed Implementation:**
```python
# New file: /src/claude_mpm/cli/commands/auto_configure.py

class AutoConfigureCommand(BaseCommand):
    """Unified auto-configuration for agents and skills."""

    def run(self, args):
        # Step 1: Analyze project
        toolchain = self.toolchain_analyzer.analyze()

        # Step 2: Recommend agents
        agent_recs = self.agent_recommender.recommend(toolchain)

        # Step 3: Recommend skills for agents
        skill_recs = self.skill_recommender.recommend(agent_recs)

        # Step 4: Interactive confirmation with questionary
        confirmed_agents, confirmed_skills = self._confirm_selections(
            agent_recs, skill_recs
        )

        # Step 5: Deploy both
        self._deploy_agents(confirmed_agents)
        self._deploy_skills(confirmed_skills)
```

## Code Locations Reference

### Agent Display/Filtering Code

**Primary File:** `/src/claude_mpm/cli/commands/configure.py`

| Line Range | Function | Purpose |
|------------|----------|---------|
| 304-417 | `_manage_agents()` | Main agent management loop |
| 347-375 | Agent discovery & filtering | Calls `_filter_agent_configs()` to remove BASE_AGENT |
| 935-970 | `_filter_agent_configs()` | Converts AgentConfig to dicts, applies filters, converts back |
| 972-1030 | `_display_agents_with_source_info()` | Rich table display with source labels |
| 1044-1269 | `_deploy_agents_individual()` | Unified checkbox interface for install/remove |

**Secondary File:** `/src/claude_mpm/cli/interactive/agent_wizard.py`

| Line Range | Function | Purpose |
|------------|----------|---------|
| 154-227 | `_merge_agent_sources()` | Combines local + remote agents, filters BASE_AGENT (line 226) |
| 228-369 | `run_interactive_manage()` | Agent management menu with questionary |
| 1099-1214 | `_deploy_agent_interactive()` | Filters deployed agents for deployment menu |

### Skill Display/Configuration Code

**Primary File:** `/src/claude_mpm/cli/commands/skills.py`

| Line Range | Function | Purpose |
|------------|----------|---------|
| 120-196 | `_list_skills()` | List skills by agent/category |
| 955-1202 | `_configure_skills()` | Interactive checkbox interface (matches agent UX) |

**Secondary File:** `/src/claude_mpm/cli/interactive/skills_wizard.py`

| Line Range | Function | Purpose |
|------------|----------|---------|
| 86-148 | `run_interactive_selection()` | Skills selection wizard |
| 150-169 | `_auto_link_skills()` | Auto-link skills to agents based on type |

### Filtering Utilities

**File:** `/src/claude_mpm/utils/agent_filters.py`

| Line Range | Function | Purpose |
|------------|----------|---------|
| 23-53 | `is_base_agent()` | Detect BASE_AGENT (case-insensitive, path-aware) |
| 56-80 | `filter_base_agents()` | Remove BASE_AGENT from list |
| 83-202 | `get_deployed_agent_ids()` | Detect deployed agents (virtual state + physical files) |
| 205-238 | `filter_deployed_agents()` | Remove deployed agents from list |
| 241-288 | `apply_all_filters()` | Convenience function with configurable filters |

### Auto-Configure Implementations

**Agents:**
- Service: `/src/claude_mpm/services/agents/auto_config_manager.py`
- Full workflow: toolchain analysis → recommendations → validation → deployment

**Skills:**
- Service: `/src/claude_mpm/services/skills_deployer.py`
- Interactive: `/src/claude_mpm/cli/commands/skills.py` line 955-1202

## Implementation Recommendations

### Phase 1: Complete Existing Features

1. **Add Window-Size Awareness** (lines to modify: configure.py 976-1030)
   ```python
   import shutil
   terminal_width, terminal_height = shutil.get_terminal_size()

   # Dynamic column widths
   # Pagination for long lists
   ```

2. **Verify BASE_AGENT Filtering Everywhere**
   - Audit all agent list displays
   - Add filtering to skills wizard (defensive coding)

3. **Test Deployed Agent Detection**
   - Verify checkbox pre-selection works with virtual deployment state
   - Test isolation (project_dir parameter usage)

### Phase 2: Unified Auto-Configure

1. **Create Unified Command**
   - New file: `cli/commands/auto_configure.py`
   - Orchestrates both agent and skill configuration
   - Single questionary flow

2. **Integrate Existing Services**
   - `AutoConfigManagerService` for agents
   - `SkillsDeployerService` for skills
   - Unified progress reporting

3. **Update Documentation**
   - User guide for auto-configure
   - Examples for different project types

### Phase 3: UX Polish

1. **Improve Error Handling**
   - Better feedback when deployment fails
   - Rollback messaging

2. **Add Help Text**
   - Questionary prompts with keyboard shortcuts
   - Context-sensitive help

3. **Performance Optimization**
   - Cache agent/skill metadata
   - Parallel deployment where safe

## Testing Recommendations

### Unit Tests Needed

1. **Agent Filtering:**
   ```python
   # Test BASE_AGENT detection
   assert is_base_agent("BASE_AGENT")
   assert is_base_agent("qa/BASE-AGENT")
   assert not is_base_agent("ENGINEER")

   # Test deployed detection
   deployed = get_deployed_agent_ids(test_project_dir)
   assert "python-engineer" in deployed
   ```

2. **Window Sizing:**
   ```python
   # Test dynamic column widths
   # Test pagination triggers
   ```

### Integration Tests Needed

1. **End-to-End Deployment:**
   - Install agents via checkbox
   - Verify filesystem state
   - Remove agents via checkbox
   - Verify cleanup

2. **Auto-Configure Flow:**
   - Run on sample projects (Python, TypeScript, etc.)
   - Verify correct recommendations
   - Test deployment success

### Manual Testing Checklist

- [ ] Arrow-key navigation works in all menus
- [ ] Checkbox pre-selection shows deployed agents correctly
- [ ] BASE_AGENT never appears in user-facing lists
- [ ] Tables adapt to small terminal windows
- [ ] Long agent lists paginate correctly
- [ ] Deploy/remove actions update state immediately
- [ ] Error messages are clear and actionable

## Related Tickets

- **1M-493:** Questionary integration (completed in v5.0.2)
- **1M-502 Phase 1:** BASE_AGENT filtering (partially complete)
- **1M-486:** Git skill sources (skills deployment architecture)

## Memory Statistics

Files analyzed: 5 key files
Lines reviewed: ~3,500 lines of code
Existing features leveraged: questionary (v5.0.2), agent_filters utilities
New code required: ~200 lines (window sizing + unified auto-configure)

---

**Research conducted by:** Research Agent
**Ticket context:** 1M-502 UX enhancements
**Next steps:** Review findings with PM, prioritize phases for implementation
