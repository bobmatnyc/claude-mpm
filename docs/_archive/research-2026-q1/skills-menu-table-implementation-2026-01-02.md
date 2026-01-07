# Skills Management Menu - Table Implementation Research

**Date:** 2026-01-02
**Task:** Find where Skills Management menu is defined and identify code to replicate agents table format

## Executive Summary

The Skills Management menu currently displays a simple text-based list of skills. User wants it to display a Rich table similar to the Agents table format. This research identifies:
1. Where the Skills Management menu is defined
2. What handles the menu selections
3. Where the agents table code exists (to replicate)
4. Location of "memory-manager-legacy" references (for removal)

---

## 1. Skills Management Menu Location

### File: `/Users/masa/Projects/claude-mpm/src/claude_mpm/cli/commands/configure.py`

**Method Definition:**
- **Lines 658-780:** `_manage_skills()` method

**Menu Display:**
- **Lines 670-676:** Skills Management Options menu text

```python
def _manage_skills(self) -> None:
    """Skills management interface."""
    from ...cli.interactive.skills_wizard import SkillsWizard
    from ...skills.skill_manager import get_manager

    wizard = SkillsWizard()
    manager = get_manager()

    while True:
        self.console.clear()
        self._display_header()

        self.console.print("\n[bold]Skills Management Options:[/bold]\n")
        self.console.print("  [1] View Available Skills")
        self.console.print("  [2] Configure Skills for Agents")
        self.console.print("  [3] View Current Skill Mappings")
        self.console.print("  [4] Auto-Link Skills to Agents")
        self.console.print("  [b] Back to Main Menu")
        self.console.print()

        choice = Prompt.ask("[bold blue]Select an option[/bold blue]", default="b")

        if choice == "1":
            # View available skills
            self.console.clear()
            self._display_header()
            wizard.list_available_skills()  # <-- THIS IS WHAT NEEDS TO CHANGE
            Prompt.ask("\nPress Enter to continue")
```

**Called From:**
- **Line 245:** Main menu option `elif choice == "2": self._manage_skills()`

---

## 2. Current Skills Display Implementation

### File: `/Users/masa/Projects/claude-mpm/src/claude_mpm/cli/interactive/skills_wizard.py`

**Method to Replace:**
- **Lines 351-400:** `list_available_skills()` method

**Current Implementation:**
```python
def list_available_skills(self):
    """Display all available skills."""
    print("\n" + "=" * 60)
    print("📚 Available Skills")
    print("=" * 60)

    # Bundled skills
    bundled_skills = self.registry.list_skills(source="bundled")
    if bundled_skills:
        print(f"\n🔹 Bundled Skills ({len(bundled_skills)}):")
        for skill in sorted(bundled_skills, key=lambda s: s.name):
            print(f"   • {skill.name}")
            if skill.description:
                desc = (
                    skill.description[:80] + "..."
                    if len(skill.description) > 80
                    else skill.description
                )
                print(f"     {desc}")
    # ... similar for user_skills and project_skills
```

**Issues:**
- Uses plain `print()` statements instead of Rich console
- No table format
- Not consistent with agents display

---

## 3. Agents Table Code to Replicate

### Primary Reference: `/Users/masa/Projects/claude-mpm/src/claude_mpm/cli/commands/configure.py`

**Method:** `_display_agents_with_source_info()`
- **Lines 1138-1250:** Complete implementation with Rich table

**Key Features:**
```python
def _display_agents_with_source_info(self, agents: List[AgentConfig]) -> None:
    """Display agents table with source information and installation status."""
    from rich.table import Table

    # Get terminal width and calculate dynamic column widths
    terminal_width = shutil.get_terminal_size().columns
    min_widths = {
        "#": 4,
        "Agent ID": 30,
        "Name": 20,
        "Source": 15,
        "Status": 10,
    }
    widths = self._calculate_column_widths(terminal_width, min_widths)

    agents_table = Table(show_header=True, header_style="bold cyan")
    agents_table.add_column(
        "#", style="bright_black", width=widths["#"], no_wrap=True
    )
    agents_table.add_column(
        "Agent ID",
        style="bright_black",
        width=widths["Agent ID"],
        no_wrap=True,
        overflow="ellipsis",
    )
    agents_table.add_column(
        "Name",
        style="bright_cyan",
        width=widths["Name"],
        no_wrap=True,
        overflow="ellipsis",
    )
    agents_table.add_column(
        "Source",
        style="bright_yellow",
        width=widths["Source"],
        no_wrap=True,
    )
    agents_table.add_column(
        "Status", style="bright_black", width=widths["Status"], no_wrap=True
    )

    # Loop through agents and add rows
    for idx, agent in enumerate(agents, 1):
        # ... determine source, status, etc.
        agents_table.add_row(
            str(idx),
            agent_id_display,
            agent.name,
            source_label,
            status
        )

    self.console.print(agents_table)
```

### Alternative Reference: `/Users/masa/Projects/claude-mpm/src/claude_mpm/cli/commands/configure_agent_display.py`

**Method:** `display_agents_table()`
- **Lines 56-140:** Simpler table implementation

**Key Features:**
```python
def display_agents_table(self, agents: List[AgentConfig]) -> None:
    """Display a table of available agents with status and metadata."""
    from ...utils.agent_filters import get_deployed_agent_ids

    table = Table(
        title=f"Available Agents ({len(agents)} total)",
        box=ROUNDED,
        show_lines=True,
    )

    table.add_column("ID", style="dim", width=3)
    table.add_column("Name", style="bold blue", width=22)
    table.add_column("Status", width=12)
    table.add_column("Description", style="bold", width=45)
    table.add_column("Model/Tools", style="dim", width=20)

    # Get deployed agent IDs
    deployed_ids = get_deployed_agent_ids()

    for idx, agent in enumerate(agents, 1):
        # ... determine status
        status = "[green]Installed[/green]" if is_deployed else "Available"

        table.add_row(
            str(idx),
            agent.name,
            status,
            agent.description[:45] if agent.description else "",
            tools_display
        )

    self.console.print(table)
```

---

## 4. Skills Data Structure

### File: `/Users/masa/Projects/claude-mpm/src/claude_mpm/skills/registry.py`

**Skill Class:**
- **Lines 16-44:** Skill dataclass definition

**Fields Available:**
```python
@dataclass
class Skill:
    """Represents a skill that can be used by agents."""

    name: str                          # Human-readable name
    path: Path                         # File path
    content: str                       # Markdown content
    source: str                        # 'bundled', 'user', or 'project'

    # Version tracking
    version: str = "0.1.0"
    skill_id: str = ""                 # defaults to name if not provided

    # Metadata
    description: str = ""
    agent_types: List[str] = None      # Which agent types can use this skill
    updated_at: Optional[str] = None
    tags: List[str] = None
```

**Registry Method:**
- **Line 243:** `list_skills(source: Optional[str] = None) -> List[Skill]`

**Usage:**
```python
registry = SkillsRegistry()
bundled_skills = registry.list_skills(source="bundled")
user_skills = registry.list_skills(source="user")
project_skills = registry.list_skills(source="project")
all_skills = registry.list_skills()  # No filter
```

---

## 5. Proposed Table Format for Skills

Based on user's example and agents table format:

```
┃ #      ┃ Skill ID            ┃ Name                ┃ Source     ┃ Status     ┃
│ 1      │ git-workflow        │ Git Workflow        │ MPM Skills │ Installed  │
│ 2      │ pytest              │ Pytest              │ MPM Skills │ Available  │
```

**Recommended Column Mapping:**
1. **#** - Row number (1, 2, 3...)
2. **Skill ID** - `skill.skill_id` or `skill.name` (technical identifier)
3. **Name** - `skill.name` (human-readable display name)
4. **Source** - Map `skill.source`:
   - `"bundled"` → "MPM Skills"
   - `"user"` → "User Skills"
   - `"project"` → "Project"
5. **Status** - Check if skill is "Installed" or "Available"
   - Need to determine how to check if skill is currently active/deployed

---

## 6. "memory-manager-legacy" References

**Search Results:** No matches found in codebase

**Alternative Search Results:**
- **File:** `/Users/masa/Projects/claude-mpm/tests/test_memory_edge_cases.py`
  - **Line 93:** `legacy_memory = manager.load_agent_memory("legacy")`
  - This is a test case using "legacy" as a variable name, NOT "memory-manager-legacy"

- **File:** `/Users/masa/Projects/claude-mpm/tests/services/core/test_memory_manager.py`
  - **Line 316:** `memory_manager._migrate_legacy_file(old_file, new_file)`
  - This is a migration function test, NOT a "memory-manager-legacy" agent

**Conclusion:** "memory-manager-legacy" does NOT exist in the codebase. No removal needed.

---

## 7. Implementation Plan

### Step 1: Update SkillsWizard.list_available_skills()
**File:** `/Users/masa/Projects/claude-mpm/src/claude_mpm/cli/interactive/skills_wizard.py`
**Lines:** 351-400

**Changes:**
1. Import Rich table components
2. Replace `print()` statements with Rich table
3. Add columns: #, Skill ID, Name, Source, Status
4. Determine "Installed" vs "Available" status
5. Group skills by source OR use single table with source column

### Step 2: Add Helper Method for Skill Status
**Determine:** How to check if a skill is "Installed/Active"
- Check if skill is deployed to agent configs?
- Check if skill is in active agent skill mappings?
- Consult with SkillManager for deployment status

### Step 3: Consider Alternative Display Location
**Option A:** Keep in SkillsWizard.list_available_skills()
**Option B:** Move to configure.py like agent display methods
**Recommendation:** Follow agent pattern - create display method in configure.py

### Step 4: Match Column Widths and Styling
Use same approach as agents table:
- Dynamic column width calculation based on terminal size
- Consistent color scheme (cyan for names, yellow for source, etc.)
- Handle overflow with ellipsis for long names/IDs

---

## 8. Code References Summary

| Component | File | Lines | Description |
|-----------|------|-------|-------------|
| Skills Menu | configure.py | 658-780 | `_manage_skills()` method |
| Menu Display | configure.py | 670-676 | Skills Management Options text |
| Current Skills List | skills_wizard.py | 351-400 | `list_available_skills()` - TEXT FORMAT |
| Agents Table (Source) | configure.py | 1138-1250 | `_display_agents_with_source_info()` - TABLE FORMAT |
| Agents Table (Alt) | configure_agent_display.py | 56-140 | `display_agents_table()` - SIMPLE TABLE |
| Skill Class | registry.py | 16-44 | Skill dataclass definition |
| List Skills Method | registry.py | 243-247 | `list_skills()` registry method |
| Skill Mappings Display | configure.py | 726-751 | Current mappings table (different from skills list) |

---

## 9. Next Steps

1. **Decide on Status Logic:** Determine how to check if skill is "Installed" vs "Available"
   - Check `SkillManager.list_agent_skill_mappings()` for active skills?
   - Check deployed agent configs for skill references?

2. **Create Display Method:** Either:
   - Update `skills_wizard.py:list_available_skills()` to use Rich table
   - OR create new method in `configure.py` like `_display_skills_table()`

3. **Use Agents Table as Template:** Copy structure from:
   - Primary: `configure.py:_display_agents_with_source_info()` (lines 1138-1250)
   - OR Simpler: `configure_agent_display.py:display_agents_table()` (lines 56-140)

4. **Test with Different Skill Sources:** Ensure table works with:
   - Bundled skills (MPM Skills)
   - User skills
   - Project skills
   - Mixed sources in single table

5. **Update Menu Handler:** Ensure option "1" in `_manage_skills()` calls new table display

---

## Appendix: File Paths Quick Reference

```bash
# Skills Management Menu
/Users/masa/Projects/claude-mpm/src/claude_mpm/cli/commands/configure.py

# Current Skills Display (TEXT - needs update)
/Users/masa/Projects/claude-mpm/src/claude_mpm/cli/interactive/skills_wizard.py

# Agents Table Display (TABLE - template to copy)
/Users/masa/Projects/claude-mpm/src/claude_mpm/cli/commands/configure_agent_display.py
/Users/masa/Projects/claude-mpm/src/claude_mpm/cli/commands/configure.py

# Skills Data Model
/Users/masa/Projects/claude-mpm/src/claude_mpm/skills/registry.py

# Skills Manager (for status checking)
/Users/masa/Projects/claude-mpm/src/claude_mpm/skills/skill_manager.py
```

---

**Research Completed:** 2026-01-02
**Researcher:** Claude Code (Research Agent)
