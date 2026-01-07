# Skill Selection/Display Issues Research
**Date:** 2025-01-02
**Researcher:** Claude Code (Research Agent)
**Project:** Claude MPM

## Executive Summary

The skill display system in `configure.py` is using an **outdated registry** that only loads bundled skills from local `.md` files. It's missing the entire catalog of community skills that are fetched from Git repositories and cached in `~/.claude-mpm/cache/skills/`.

### Key Findings

1. **Dual Registry Problem**: Two separate skill loading systems exist
   - Old: `SkillsRegistry` (registry.py) - loads bundled `.md` files only
   - New: `GitSkillSourceManager` + `SkillDiscoveryService` - loads from Git cache with metadata.json

2. **Missing Skills**: Configure UI only shows ~33 bundled skills, missing 200+ community skills

3. **Missing Metadata**: No category/toolchain grouping in old registry system

4. **Inconsistent Display**: Skills table doesn't match agents table quality

---

## Problem 1: Where Skills Table is Displayed

### Location
File: `/Users/masa/Projects/claude-mpm/src/claude_mpm/cli/commands/configure.py`
Function: `_display_skills_table()` (line 860-906)

### Current Implementation
```python
def _display_skills_table(self, registry) -> None:
    """Display skills in a table format like agents."""
    # ...
    all_skills = self._get_all_skills_sorted(registry)
    deployed_ids = self._get_deployed_skill_ids()

    table = Table(show_header=True, header_style="bold cyan", box=box.ROUNDED)
    table.add_column("#", style="bright_black", width=6)
    table.add_column("Skill ID", style="bright_black", overflow="ellipsis")
    table.add_column("Name", style="bright_cyan", overflow="ellipsis")
    table.add_column("Source", style="bright_yellow")
    table.add_column("Status", style="bright_black")
```

### What's Wrong
1. **Uses old registry** via `self._get_all_skills_sorted(registry)`
2. **No Category/Toolchain columns** - metadata not available in old Skill dataclass
3. **Source is hardcoded** to "bundled/user/project" - doesn't show actual repo source
4. **No dynamic width calculation** like agents table has

---

## Problem 2: Where Skills List Comes From

### Current Flow (BROKEN)
```
configure.py:_manage_skills()
  ↓
get_registry() → SkillsRegistry() (registry.py)
  ↓
_load_bundled_skills() - scans src/claude_mpm/skills/bundled/*.md
_load_user_skills() - scans ~/.claude/skills/*.md
_load_project_skills() - scans .claude/skills/*.md
  ↓
list_skills(source="bundled") → Only ~33 bundled skills returned
```

### Problems
1. **Ignores Git cache**: Doesn't read from `~/.claude-mpm/cache/skills/`
2. **No metadata.json support**: Only parses YAML frontmatter from .md files
3. **Missing 200+ skills**: Community skills in Git repos not loaded
4. **No category/toolchain**: Old Skill dataclass doesn't have these fields

### Correct Flow (SHOULD BE)
```
configure.py:_manage_skills()
  ↓
GitSkillSourceManager.get_all_skills()
  ↓
For each enabled source in config/skill_sources.yaml:
  - Load from ~/.claude-mpm/cache/skills/{source_id}/
  - Use SkillDiscoveryService.discover_skills()
  - Parse metadata.json for each skill
  - Apply priority resolution
  ↓
Returns 200+ skills with full metadata:
  - skill_id, name, description
  - category, toolchain, tags
  - source_id, version
```

---

## Problem 3: Installed Skills Detection

### Location
File: `/Users/masa/Projects/claude-mpm/src/claude_mpm/cli/commands/configure.py`
Function: `_get_deployed_skill_ids()` (line 924-938)

### Current Implementation
```python
def _get_deployed_skill_ids(self) -> set:
    """Get set of deployed skill IDs from .claude/skills/ directory."""
    skills_dir = Path.cwd() / ".claude" / "skills"
    if not skills_dir.exists():
        return set()

    deployed_ids = set()
    for skill_dir in skills_dir.iterdir():
        if skill_dir.is_dir() and not skill_dir.name.startswith("."):
            deployed_ids.add(skill_dir.name)

    return deployed_ids
```

### What's Correct
✅ Correctly scans `.claude/skills/` directory
✅ Returns skill IDs as directory names (e.g., "universal-collaboration-git-workflow")
✅ Filters out hidden directories

### What's Wrong
⚠️ Works fine for detection, but **mismatch with registry skill_ids**
  - Deployed: `"universal-collaboration-git-workflow"` (from metadata.json)
  - Registry: `"git-workflow"` (from YAML frontmatter in .md files)
  - **IDs don't match** → Status shows "Available" even when installed

---

## Problem 4: Skill Grouping/Categories

### Missing Features
1. **No category field** in old Skill dataclass (registry.py line 15-44)
2. **No toolchain field** in old Skill dataclass
3. **No grouping logic** in `_display_skills_table()`

### Metadata Available (But Not Used)
From deployed skill's metadata.json:
```json
{
  "name": "git-workflow",
  "category": "universal",
  "toolchain": null,
  "tags": ["performance", "api", "security", "testing", "debugging"],
  "source": "https://github.com/bobmatnyc/claude-mpm"
}
```

### What Should Be Shown
```
Category: Universal Skills
  - Git Workflow
  - Systematic Debugging
  - Test-Driven Development

Category: Python Skills
  - FastAPI Local Dev
  - Async Testing

Category: JavaScript Skills
  - Express Local Dev
  - React Patterns
```

---

## Problem 5: Comparison with Agents Table

### Agents Table (GOOD EXAMPLE)
File: `/Users/masa/Projects/claude-mpm/src/claude_mpm/cli/commands/configure.py`
Function: `_display_agents_with_source_info()` (line 1300-1449)

**Features:**
- ✅ Dynamic column width calculation
- ✅ Shows Agent ID (technical) + Display Name (human-readable)
- ✅ Source shows repo name (e.g., "MPM Agents", "bobmatnyc/repo")
- ✅ Status correctly matches deployed IDs
- ✅ Recommendation indicators (*)
- ✅ Summary shows detected languages/frameworks

### Skills Table (CURRENT - BROKEN)
**Missing:**
- ❌ Static column widths (no dynamic calculation)
- ❌ Shows Skill ID only (no separate display name)
- ❌ Source is generic ("MPM Skills", "User Skills")
- ❌ Status doesn't match (ID mismatch issue)
- ❌ No category/toolchain grouping
- ❌ No recommendations based on project detection

---

## Root Cause Analysis

### Why This Happened
1. **Old code not updated**: `configure.py` still uses legacy `SkillsRegistry`
2. **New system not integrated**: `GitSkillSourceManager` exists but isn't used by configure UI
3. **Dataclass mismatch**: Old `Skill` class vs. new skill dicts with metadata
4. **Migration incomplete**: Git skills system added, but UI not refactored

### Evidence
```python
# configure.py line 661-666 (OLD CODE)
from ...skills.registry import get_registry
registry = get_registry()  # ← Uses old registry

# Should be (NEW CODE):
from ...services.skills.git_skill_source_manager import GitSkillSourceManager
from ...config.skill_sources import SkillSourceConfiguration
config = SkillSourceConfiguration()
manager = GitSkillSourceManager(config)
skills = manager.get_all_skills()  # ← Returns 200+ skills with metadata
```

---

## Detailed File Analysis

### File: `/Users/masa/Projects/claude-mpm/src/claude_mpm/skills/registry.py`

**Purpose:** Legacy skill loader (bundled skills only)
**Lines 78-120:** `_load_bundled_skills()` - scans `bundled/*.md` files
**Lines 122-167:** `_load_user_skills()` - scans `~/.claude/skills/*.md` files
**Lines 169-214:** `_load_project_skills()` - scans `.claude/skills/*.md` files

**Dataclass (line 15-44):**
```python
@dataclass
class Skill:
    name: str
    path: Path
    content: str
    source: str  # 'bundled', 'user', or 'project'
    version: str = "0.1.0"
    skill_id: str = ""
    description: str = ""
    agent_types: List[str] = None
    updated_at: Optional[str] = None
    tags: List[str] = None
    # ❌ Missing: category, toolchain, framework, author, repository
```

**Problem:** Designed for local .md files, not Git cache structure.

### File: `/Users/masa/Projects/claude-mpm/src/claude_mpm/services/skills/git_skill_source_manager.py`

**Purpose:** New Git-based skill manager (multi-repo support)
**Lines 247-314:** `get_all_skills()` - loads from cache with priority resolution

**Returns (lines 251-263):**
```python
{
    "skill_id": str,           # e.g., "universal-collaboration-git-workflow"
    "name": str,               # e.g., "git-workflow"
    "description": str,
    "version": str,
    "tags": List[str],
    "agent_types": List[str],
    "content": str,            # Full skill markdown
    "source_id": str,          # e.g., "claude-mpm-skills"
    "source_priority": int,
    "source_file": str,
    "category": str,           # ✅ Available!
    "toolchain": str,          # ✅ Available!
    "framework": str           # ✅ Available!
}
```

**Problem:** Exists but not used by configure.py UI.

### File: `/Users/masa/Projects/claude-mpm/src/claude_mpm/services/skills/skill_discovery_service.py`

**Purpose:** Discover and parse skills from Git cache
**Lines 113-219:** `discover_skills()` - recursively scans for SKILL.md files
**Lines 221-304:** `_parse_skill_file()` - parses YAML frontmatter + metadata.json

**Metadata Sources (priority order):**
1. metadata.json (if exists) - **preferred for Git skills**
2. YAML frontmatter in SKILL.md - fallback

**Problem:** Great implementation, but configure.py doesn't call it.

---

## How to Fix Each Issue

### Fix 1: Use GitSkillSourceManager Instead of Old Registry

**Location:** `configure.py:_manage_skills()` (line 658-666)

**Current (BROKEN):**
```python
from ...skills.registry import get_registry
registry = get_registry()
all_skills = self._get_all_skills_sorted(registry)
```

**Should Be:**
```python
from ...services.skills.git_skill_source_manager import GitSkillSourceManager
from ...config.skill_sources import SkillSourceConfiguration

config = SkillSourceConfiguration()
manager = GitSkillSourceManager(config)
all_skills = manager.get_all_skills()  # Returns List[Dict] with metadata
```

**Impact:** Loads 200+ skills instead of 33.

---

### Fix 2: Update Skill Table Display

**Location:** `configure.py:_display_skills_table()` (line 860-906)

**Changes Needed:**
1. Accept `List[Dict]` instead of `SkillsRegistry`
2. Add "Category" and "Toolchain" columns
3. Show actual repo source (from source_id)
4. Use dynamic column width calculation
5. Group by category (optional but recommended)

**Example:**
```python
def _display_skills_table(self, skills: List[Dict[str, Any]]) -> None:
    # Calculate widths like agents table
    terminal_width = shutil.get_terminal_size().columns
    min_widths = {
        "#": 4,
        "Skill ID": 25,
        "Name": 20,
        "Category": 12,
        "Toolchain": 12,
        "Source": 15,
        "Status": 10
    }
    widths = self._calculate_column_widths(terminal_width, min_widths)

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("#", width=widths["#"])
    table.add_column("Skill ID", width=widths["Skill ID"])
    table.add_column("Name", width=widths["Name"])
    table.add_column("Category", width=widths["Category"])
    table.add_column("Toolchain", width=widths["Toolchain"])
    table.add_column("Source", width=widths["Source"])
    table.add_column("Status", width=widths["Status"])

    for i, skill in enumerate(skills, 1):
        skill_id = skill.get("skill_id", skill.get("name", "unknown"))
        name = skill.get("name", skill_id)
        category = skill.get("category", "general")
        toolchain = skill.get("toolchain") or "-"
        source_id = skill.get("source_id", "unknown")

        # Map source_id to display label
        source_label = self._get_source_label(source_id)

        # Check deployment status
        is_installed = skill_id in deployed_ids
        status = "[green]Installed[/green]" if is_installed else "Available"

        table.add_row(str(i), skill_id, name, category, toolchain, source_label, status)
```

---

### Fix 3: Fix Skill ID Matching for Status

**Problem:** Deployed skill IDs don't match registry skill IDs

**Example:**
- Deployed dir: `universal-collaboration-git-workflow/`
- Skill dict: `skill_id = "git-workflow"` (from metadata.json name field)

**Solution:** Use deployment_name from skill dict for matching

**Location:** `configure.py:_get_deployed_skill_ids()` - works fine
**But:** Need to match against skill's `deployment_name` not `skill_id`

**Fix in display function:**
```python
# Instead of:
is_installed = skill["skill_id"] in deployed_ids

# Use:
deployment_name = skill.get("deployment_name") or skill["skill_id"]
is_installed = deployment_name in deployed_ids
```

---

### Fix 4: Add Category Grouping (Optional Enhancement)

**Location:** New function `_display_skills_table_grouped()`

**Approach:**
```python
def _display_skills_table_grouped(self, skills: List[Dict[str, Any]]) -> None:
    # Group by category
    by_category = {}
    for skill in skills:
        category = skill.get("category", "general")
        if category not in by_category:
            by_category[category] = []
        by_category[category].append(skill)

    # Display each category
    for category, category_skills in sorted(by_category.items()):
        self.console.print(f"\n[bold cyan]{category.title()} Skills[/bold cyan]")
        self._display_skills_table(category_skills)
```

---

### Fix 5: Add Skill Recommendations (Like Agents)

**Approach:** Detect project type and recommend skills

**Example:**
```python
# Detect Python project
if Path("pyproject.toml").exists():
    recommended_skills = ["python-style-guide", "pytest-patterns"]

# Detect FastAPI
if "fastapi" in dependencies:
    recommended_skills.append("fastapi-local-dev")
```

**Display:** Add (*) indicator to recommended skills in table

---

## Migration Plan

### Phase 1: Quick Fix (1-2 hours)
1. Replace `get_registry()` with `GitSkillSourceManager` in `_manage_skills()`
2. Update `_display_skills_table()` to accept `List[Dict]`
3. Fix skill ID matching for status detection
4. Test with existing skills

### Phase 2: Enhanced Display (2-3 hours)
1. Add Category and Toolchain columns
2. Implement dynamic width calculation
3. Show actual repo source names
4. Add summary stats (like agents table)

### Phase 3: Advanced Features (3-4 hours)
1. Add category grouping view
2. Implement skill recommendations based on project detection
3. Add search/filter by category or toolchain
4. Show skill dependencies (if any)

---

## Test Plan

### Test 1: Verify Skill Count
```bash
# Before fix: ~33 skills
# After fix: 200+ skills
python -m claude_mpm configure
# Select "Skills Management"
# Count rows in table
```

### Test 2: Verify Metadata Display
```bash
# Check table shows:
# - Category column (universal, python, etc.)
# - Toolchain column (python, typescript, etc.)
# - Source shows repo name
```

### Test 3: Verify Status Detection
```bash
# Deploy a skill
python -m claude_mpm skills deploy universal-collaboration-git-workflow

# Check configure UI
# Status should show "[green]Installed[/green]" for that skill
```

### Test 4: Verify Sources
```bash
# Skills from different repos should show different source labels
# MPM Skills: claude-mpm-skills repo
# Community: other repos
```

---

## Related Files Reference

### Primary Files to Modify
1. `src/claude_mpm/cli/commands/configure.py` - lines 658-906
2. `src/claude_mpm/cli/commands/configure.py` - lines 908-922 (_get_all_skills_sorted)

### Files to Understand (Don't Modify)
1. `src/claude_mpm/services/skills/git_skill_source_manager.py` - skill source
2. `src/claude_mpm/services/skills/skill_discovery_service.py` - skill discovery
3. `src/claude_mpm/config/skill_sources.py` - source configuration
4. `src/claude_mpm/skills/registry.py` - legacy (will be deprecated)

### Config Files
1. `config/skill_sources.yaml` - defines skill repositories
2. `~/.claude-mpm/cache/skills/{source_id}/` - cached skill files
3. `.claude/skills/{deployment_name}/metadata.json` - deployed skill metadata

---

## Questions for Implementation

1. **Backward compatibility:** Should we keep supporting bundled skills from `skills/bundled/*.md`?
2. **Migration path:** When to deprecate old `SkillsRegistry`?
3. **User impact:** Will changing skill IDs break existing configurations?
4. **Performance:** Should we cache `get_all_skills()` result or call every time?

---

## Conclusion

The skill display system needs refactoring to use the new Git-based skill infrastructure. The old `SkillsRegistry` only loads ~33 bundled skills from local files, while the new `GitSkillSourceManager` can load 200+ skills from multiple Git repositories with full metadata including category, toolchain, and source information.

**Priority:** HIGH - Users can't see or install community skills
**Effort:** Medium (4-8 hours for complete fix)
**Risk:** Low (new code path, doesn't affect existing functionality)
**Dependencies:** None (all infrastructure already exists)

---

## Appendix: Example Skill Metadata

### From Git Cache (metadata.json)
```json
{
  "name": "git-workflow",
  "version": "1.0.0",
  "category": "universal",
  "toolchain": null,
  "framework": null,
  "tags": ["performance", "api", "security", "testing", "debugging"],
  "entry_point_tokens": 62,
  "full_tokens": 1862,
  "requires": [],
  "author": "bobmatnyc",
  "updated": "2025-11-21",
  "source_path": "git-workflow.md",
  "license": "MIT",
  "source": "https://github.com/bobmatnyc/claude-mpm",
  "repository": "https://github.com/bobmatnyc/claude-mpm-skills"
}
```

### From Bundled (YAML frontmatter)
```yaml
---
skill_id: git-workflow
skill_version: 0.1.0
description: Essential Git patterns for effective version control
updated_at: 2025-10-30T17:00:00Z
tags: [git, version-control, workflow, best-practices]
---
```

**Key Difference:** Git cache has category, toolchain, repository - bundled doesn't.
