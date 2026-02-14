# Skills Count Discrepancy: Dashboard (60) vs CLI (188)

**Date:** 2026-02-14
**Status:** Root Cause Identified
**Severity:** Medium (data inconsistency, not data loss)
**Investigators:** HAR Analyst, Backend Analyst, Frontend Analyst, Devil's Advocate Reviewer

---

## Executive Summary

The dashboard UI displays 60 deployed skills while the CLI startup reports 188 deployed skills. The root cause is a **directory path mismatch** between two independent skill deployment systems: the CLI startup deploys skills to the **project-level** directory (`$CWD/.claude/skills/`, 188 skills), while the dashboard API reads from the **user-level** directory (`~/.claude/skills/`, 60 skills). Both numbers are independently correct for their respective directories, but the dashboard should reflect the project-level count to match what the CLI reports and what Claude Code actually loads.

## Problem Statement

| Metric | Source | Count | Directory |
|--------|--------|-------|-----------|
| Dashboard "Deployed" | API: `/api/config/skills/deployed` | **60** | `~/.claude/skills/` |
| CLI Startup | `show_skill_summary()` | **188** | `$CWD/.claude/skills/` |
| Available (API) | API: `/api/config/skills/available` | 158 | GitHub manifest |
| Cached (filesystem) | `~/.claude-mpm/cache/skills/` | 333 | Cache directory |

The user sees "188 deployed / 0 cached" in the CLI terminal but only 60 skills listed in the dashboard's Skills tab.

## Investigation Findings

### 1. HAR File Evidence

The HAR file (`/Users/mac/Downloads/localhost.har`) captured two calls to each skills endpoint:

**`GET /api/config/skills/deployed`** (called twice, identical responses):
- Status: 200
- Response: `{"success": true, "skills": [...], "total": 60, "claude_skills_dir": "/Users/mac/.claude/skills"}`
- The `claude_skills_dir` field explicitly confirms the API reads from **`/Users/mac/.claude/skills`** (user-level, `Path.home()`)
- All 60 skills have `deploy_mode: "agent_referenced"` and `category: "unknown"`

**`GET /api/config/skills/available`** (called twice, identical responses):
- Status: 200
- Response: `{"success": true, "skills": [...], "total": 158}`
- All 158 skills have `is_deployed: false` (a secondary bug: name mismatch prevents deployed-status detection)

**Key HAR finding:** The API response data is consistent and correct *for the directory it scans*. The 60 count is not a truncation, pagination artifact, or frontend filtering issue. The backend genuinely finds only 60 skills in `~/.claude/skills/`.

### 2. Backend Code Analysis

#### Two Independent Skill Deployment Systems

The codebase contains **two completely separate skill deployment pipelines** that target **different directories**:

**Pipeline A: `GitSkillSourceManager.deploy_skills()`** (used by CLI startup)
- File: `src/claude_mpm/services/skills/git_skill_source_manager.py:1086`
- Default target: `Path.home() / ".claude" / "skills"` (user-level)
- BUT: Startup overrides target to `Path.cwd() / ".claude" / "skills"` (project-level)
- Called from: `sync_remote_skills_on_startup()` at `src/claude_mpm/cli/startup.py:1148`
  ```python
  deployment_result = manager.deploy_skills(
      target_dir=Path.cwd() / ".claude" / "skills",  # PROJECT-LEVEL
      ...
  )
  ```
- Deploys **188 skills** (all agent-referenced skills from Git sources)

**Pipeline B: `SkillsDeployerService.check_deployed_skills()`** (used by dashboard API)
- File: `src/claude_mpm/services/skills_deployer.py:508`
- Hardcoded target: `CLAUDE_SKILLS_DIR = Path.home() / ".claude" / "skills"` (user-level)
- Called from: `handle_skills_deployed()` at `src/claude_mpm/services/monitor/config_routes.py:309`
- Finds **60 skills** (from collection-based git clone deployment)

#### CLI Skill Summary

The `show_skill_summary()` function (`startup.py:1340`) counts from `Path.cwd() / ".claude" / "skills"`:
```python
project_skills_dir = Path.cwd() / ".claude" / "skills"
skill_dirs = [
    d for d in project_skills_dir.iterdir()
    if d.is_dir()
    and (d / "SKILL.md").exists()
    and not (d / ".git").exists()
]
deployed_count = len(skill_dirs)  # = 188
```

#### Dashboard API Skill Count

The `handle_skills_deployed()` handler delegates to `SkillsDeployerService.check_deployed_skills()`:
```python
class SkillsDeployerService:
    CLAUDE_SKILLS_DIR = Path.home() / ".claude" / "skills"  # USER-LEVEL (hardcoded)

    def check_deployed_skills(self):
        for skill_dir in self.CLAUDE_SKILLS_DIR.iterdir():
            if skill_dir.is_dir() and not skill_dir.name.startswith("."):
                if (skill_dir / "SKILL.md").exists():
                    deployed_skills.append(...)  # Finds 60
```

### 3. Frontend Code Analysis

The frontend (SvelteKit) is a **faithful renderer** of backend data:

- **Store:** `config.svelte.ts:182-191` fetches from `/api/config/skills/deployed` and sets `deployedSkills` array directly from `data.skills`
- **Component:** `SkillsList.svelte:37-41` derives `filteredDeployed` from `deployedSkills` with optional search filtering
- **Display:** `SkillsList.svelte:150` shows `Deployed ({filteredDeployed.length})` - direct count
- **No filtering, pagination, or truncation** applied to deployed skills

**Frontend verdict:** The frontend correctly displays all 60 skills the API returns. There is no frontend bug.

### 4. Filesystem Verification

Direct filesystem counts confirm the dual-directory theory:

**User-level (`~/.claude/skills/`):**
| Metric | Count |
|--------|-------|
| Total non-hidden directories | 61 |
| Directories with SKILL.md | 60 |
| Without SKILL.md | 1 (`claude-mpm` - a git repo clone, not a skill) |

**Project-level (`$CWD/.claude/skills/`):**
| Metric | Count |
|--------|-------|
| Total directories | 188 |
| With `SKILL.md` (uppercase) | 22 (bundled PM skills) |
| With `skill.md` (lowercase) | 166 (Git-synced skills) |
| Total with any case `skill.md` | 188 |

**Important macOS note:** The filesystem is case-insensitive (APFS default). Python's `Path("SKILL.md").exists()` returns `True` even when the actual file is `skill.md`. This means both the CLI and API correctly find skills regardless of casing - the discrepancy is purely about *which directory* is scanned.

## Devil's Advocate Challenges

### Challenge 1: "Are we sure 60 is wrong?"

**Challenged assertion:** The dashboard should show 188, not 60.

**Counter-argument tested:** Maybe the dashboard correctly shows "user-level" skills that are globally available, while the CLI shows "project-level" skills specific to this project. Both could be valid views.

**Verdict:** The dashboard claims to show "deployed skills" without qualification. The CLI also says "deployed". Users reasonably expect these to match. Furthermore, `sync_remote_skills_on_startup` is the *primary* deployment mechanism - it runs on every startup and deploys to project-level. The user-level 60 skills are a *legacy artifact* from the collection-based `SkillsDeployerService`. **The 60 is the wrong number to show for the project context.**

### Challenge 2: "Are we sure 188 is right?"

**Challenged assertion:** 188 is the correct deployed count.

**Counter-argument tested:** Maybe the CLI over-counts by including non-skill directories, duplicate skills, or build artifacts.

**Verification:** All 188 directories at project-level contain a `SKILL.md` (or `skill.md`) file. No duplicates exist (each directory has a unique hyphenated name). No build artifacts are included. The CLI's `show_skill_summary()` correctly filters to `is_dir() AND (d / "SKILL.md").exists() AND NOT (d / ".git").exists()`. **188 is the correct count for project-level deployed skills.**

### Challenge 3: "Could both numbers be correct?"

**Challenged assertion:** This is a bug.

**Counter-argument tested:** Maybe both 60 and 188 are correct but measure different things (user-level vs project-level deployment scopes).

**Verdict:** Both numbers ARE technically correct for their respective directories. However, this creates a **confusing user experience** where the CLI says 188 and the dashboard says 60, with no indication that they measure different things. The dashboard should either:
- (a) Show project-level skills (matching CLI), or
- (b) Show both scopes with clear labels

Since the monitor server runs within the context of a specific project (`Path.cwd()`), option (a) is the correct fix.

### Challenge 4: "What if the HAR data is stale?"

**Challenged assertion:** The HAR accurately represents current API behavior.

**Counter-argument tested:** Maybe the HAR was captured at a different time when fewer skills were deployed.

**Verification:** The HAR response includes `"claude_skills_dir": "/Users/mac/.claude/skills"` which is the user-level path. Even if we captured a fresh HAR right now, the same 60 skills would appear because the API is *structurally hardcoded* to scan user-level. The staleness of the HAR is irrelevant - it correctly reveals the path mismatch. **The HAR evidence is valid.**

### Challenge 5: "Is the API enrichment hiding skills?"

**Challenged assertion:** The deployment index enrichment might filter some skills out.

**Counter-argument tested:** In `handle_skills_deployed()` (config_routes.py:306-361), after calling `check_deployed_skills()`, the code reads a `.mpm-deployed-skills.json` index file for metadata enrichment. Could this enrichment step drop skills?

**Verification:** The enrichment loop at line 325 iterates over `deployed.get("skills", [])` - the FULL list from `check_deployed_skills()`. It enriches each skill with metadata (description, category, etc.) but never removes skills. If a skill lacks metadata, it still appears with `category: "unknown"` and empty description. **No skills are dropped during enrichment.** This is confirmed by HAR: all 60 skills have `category: "unknown"`, meaning enrichment found no metadata for them, but they are still included.

### Challenge 6: "Is this a name normalization issue in available skills?"

**Observation during investigation:** The `/api/config/skills/available` endpoint returns 158 skills, ALL with `is_deployed: false`. But some of these ARE deployed - just with different names.

**Evidence:** Available skill name `mcp-builder` vs deployed name `universal-main-mcp-builder`. The deployment check compares `skill.get("name", "")` against `deployed_names` from `check_deployed_skills()`. Since names don't match (short vs path-normalized), `is_deployed` is always false.

**Verdict:** This is a **secondary bug** - the `is_deployed` flag in available skills is unreliable. However, this does NOT affect the deployed skills count (60 vs 188) since that comes from a separate endpoint.

## Root Cause Determination

### Primary Root Cause: Directory Path Mismatch

```
CLI Startup                         Dashboard API
===========                         =============
sync_remote_skills_on_startup()     handle_skills_deployed()
  |                                   |
  v                                   v
GitSkillSourceManager               SkillsDeployerService
.deploy_skills(                     .check_deployed_skills()
  target_dir=Path.cwd()/            CLAUDE_SKILLS_DIR =
  ".claude"/"skills"                Path.home()/".claude"/"skills"
)
  |                                   |
  v                                   v
PROJECT-LEVEL                       USER-LEVEL
$CWD/.claude/skills/                ~/.claude/skills/
188 skills                          60 skills
```

The CLI's primary deployment pipeline (`sync_remote_skills_on_startup`) deploys to the **project-level** directory, but the dashboard API's `SkillsDeployerService` is hardcoded to scan the **user-level** directory.

### Contributing Factor: Dual Deployment Systems

The codebase has two independent skill deployment mechanisms that evolved separately:
1. **`GitSkillSourceManager`** - newer, Git-source-based, deploys to project-level (via startup override)
2. **`SkillsDeployerService`** - older, collection/manifest-based, deploys to user-level (hardcoded)

The dashboard API uses the older system (#2) while the CLI startup uses the newer system (#1).

### Secondary Bug: Available Skills `is_deployed` Always False

The available skills endpoint compares short skill names against path-normalized deployed names, resulting in zero matches and all 158 skills showing as "not deployed" even when many are.

## Recommendations

### Fix 1: Dashboard API Should Read Project-Level Skills (Priority: HIGH)

**File:** `src/claude_mpm/services/monitor/config_routes.py`
**Function:** `handle_skills_deployed()`

The handler should scan the project-level `.claude/skills/` directory (same as CLI) instead of delegating to `SkillsDeployerService` which uses user-level.

**Option A (Minimal change):** Pass the project directory to `SkillsDeployerService`:
```python
async def handle_skills_deployed(request: web.Request) -> web.Response:
    def _list_deployed_skills():
        # Use project-level skills directory instead of user-level
        project_skills_dir = Path.cwd() / ".claude" / "skills"
        skills_svc = _get_skills_deployer()
        # Override the class-level CLAUDE_SKILLS_DIR
        original_dir = skills_svc.CLAUDE_SKILLS_DIR
        skills_svc.CLAUDE_SKILLS_DIR = project_skills_dir
        deployed = skills_svc.check_deployed_skills()
        skills_svc.CLAUDE_SKILLS_DIR = original_dir
        ...
```

**Option B (Better architecture):** Make `SkillsDeployerService` accept a `skills_dir` parameter:
```python
class SkillsDeployerService:
    def __init__(self, skills_dir=None, ...):
        self.CLAUDE_SKILLS_DIR = skills_dir or Path.home() / ".claude" / "skills"
```

### Fix 2: Fix `is_deployed` in Available Skills (Priority: MEDIUM)

**File:** `src/claude_mpm/services/monitor/config_routes.py`
**Function:** `handle_skills_available()`

The deployed name check should account for path-normalization:
```python
deployed_names = {s.get("name", "") for s in deployed.get("skills", [])}
# Add: also match short names against deployed long names
for skill in flat_skills:
    short_name = skill.get("name", "")
    skill["is_deployed"] = (
        short_name in deployed_names or
        any(dn.endswith(f"-{short_name}") for dn in deployed_names)
    )
```

### Fix 3: Unify Skill Counting in Project Summary (Priority: MEDIUM)

**File:** `src/claude_mpm/services/monitor/config_routes.py`
**Function:** `handle_project_summary()`

The summary endpoint also calls `skills_svc.check_deployed_skills()` which reads user-level. This should be updated to match Fix 1.

### Fix 4: Consider Deprecating Dual Deployment (Priority: LOW)

Long-term, the codebase should standardize on ONE skill deployment pipeline. The `GitSkillSourceManager` (project-level) is the more modern and actively maintained system. The `SkillsDeployerService` collection-based approach should be evaluated for deprecation.

## Appendix: Key Code References

| Component | File | Line(s) | Purpose |
|-----------|------|---------|---------|
| Dashboard API: deployed skills | `services/monitor/config_routes.py` | 304-361 | `handle_skills_deployed()` |
| Dashboard API: available skills | `services/monitor/config_routes.py` | 364-426 | `handle_skills_available()` |
| Dashboard API: project summary | `services/monitor/config_routes.py` | 126-183 | `handle_project_summary()` |
| Backend: SkillsDeployerService | `services/skills_deployer.py` | 39-60 | `CLAUDE_SKILLS_DIR = Path.home() / ".claude" / "skills"` |
| Backend: check_deployed_skills | `services/skills_deployer.py` | 508-539 | Scans user-level `~/.claude/skills/` |
| Backend: GitSkillSourceManager | `services/skills/git_skill_source_manager.py` | 1086-1235 | `deploy_skills()` with target_dir override |
| CLI: sync_remote_skills | `cli/startup.py` | 915-1253 | Deploys to `Path.cwd() / ".claude" / "skills"` |
| CLI: show_skill_summary | `cli/startup.py` | 1340-1412 | Counts from `Path.cwd() / ".claude" / "skills"` |
| Frontend: config store | `dashboard-svelte/.../config.svelte.ts` | 182-206 | Fetches and stores API data |
| Frontend: SkillsList | `dashboard-svelte/.../SkillsList.svelte` | 37-41, 150 | Renders `filteredDeployed.length` |
| Frontend: ConfigView | `dashboard-svelte/.../ConfigView.svelte` | 84-91, 279-289 | Passes data to SkillsList |
| HAR Evidence | `/Users/mac/Downloads/localhost.har` | N/A | API responses captured in browser |

## Appendix: Filesystem Audit

```
~/.claude/skills/           (user-level, read by API)
  ├── 60 skill directories with SKILL.md
  ├── 1 non-skill directory (claude-mpm git repo)
  └── Total: 61 directories

$CWD/.claude/skills/        (project-level, read by CLI)
  ├── 22 directories with SKILL.md (uppercase, bundled PM skills)
  ├── 166 directories with skill.md (lowercase, Git-synced)
  └── Total: 188 directories (all have skill.md case-insensitive)

~/.claude-mpm/cache/skills/ (cache, not directly displayed)
  └── 333 SKILL.md files across nested repository structures
```
