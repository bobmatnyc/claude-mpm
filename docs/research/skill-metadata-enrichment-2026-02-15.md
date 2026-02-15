# Skill Metadata Enrichment Research

**Date:** 2026-02-15
**Scope:** Dashboard Config Tab - Skills sub-tab metadata display and enrichment pipeline
**Branch:** ui-agents-skills-config
**Status:** Research Complete, Verified

---

## Verification Notes

**Verified on:** 2026-02-15
**Verification method:** Independent source code reading, HAR file analysis, and file system inspection

### Summary of Verification Results

The original research is **largely accurate** on its core findings and architectural analysis. However, several claims required corrections and the document had significant omissions. Key findings from verification:

**Claims verified as accurate:**
- `_build_manifest_lookup()` depends on `skills_svc.list_available_skills()` (config_routes.py line 136) -- CONFIRMED
- `list_available_skills()` calls `_download_from_github()` which performs git clone/pull -- CONFIRMED
- Silent failure behavior when manifest call fails (try/except returns empty dict) -- CONFIRMED (line 148-150)
- Detail endpoint returns 22 unique fields and combines 3 data sources -- CONFIRMED
- 19/188 deployed skills (10.1%) have YAML frontmatter -- CONFIRMED
- Frontend `DeployedSkill` interface has optional enrichment fields -- CONFIRMED
- Deployment index file (`.mpm-deployed-skills.json`) does not exist -- CONFIRMED (explains empty collection/deploy_date)

**Claims corrected:**
1. **HAR file had TWO pairs of calls, not one.** The first pair (54,789 bytes deployed, 43 bytes available) shows zero enrichment. The second pair (86,442 bytes deployed, 74,815 bytes available) shows 130/188 skills enriched with manifest data. The research only reported the first pair, presenting an incomplete picture. The intermittent nature of the failure is a critical nuance. (HAR timestamp: both pairs at 2026-02-15T15:28:17, likely two page loads)

2. **Manifest has 160 skills, but metadata says 156.** The manifest's `metadata.total_skills` field says 156 but actual count across the nested structure is 160. The research correctly stated 160 as the actual count but incorrectly showed `"total_skills": 160` in the metadata JSON example. Actual value is 156.

3. **Manifest does NOT have a `description` field.** The research claims fixing manifest enrichment "Fixes ALL enrichment at once - description, category, version, toolchain..." (Section 6, Priority 1). This is **incorrect for descriptions**. The manifest has NO `description` field in any of its 160 skill entries. The code at line 186 does check `manifest_entry.get("description")`, but this will always be None. Descriptions can ONLY come from SKILL.md frontmatter (19 skills) or SKILL.md body text extraction (all 188 skills).

4. **`tags` field is 159/160, not 160/160.** One skill in the manifest has empty tags. The research reported tags as 160/160 (100.0%) but actual count is 159/160 (99.4%).

5. **Deployment index location incorrect.** Research states location as `~/.claude/.mpm-deployed-skills.json`. Actual code looks for it at `{project_skills_dir}/.mpm-deployed-skills.json` where `project_skills_dir = Path.cwd() / ".claude" / "skills"`. For this project, that means `/Users/mac/workspace/claude-mpm-fork/.claude/skills/.mpm-deployed-skills.json`. The file does not exist at either location, which fully explains why all deployment index fields are empty.

6. **Network call characterization.** The research describes `list_available_skills()` as making a "network/GitHub API call" (Section 2.2). More precisely, it calls `_download_from_github()` which runs `git pull` (or `git clone`) as a subprocess. This is a git operation, not an HTTP API call. The distinction matters because: git pull can be slow (subprocess with network I/O), the local clone at `~/.claude/skills/claude-mpm/` already has the manifest on disk, and the git pull can fail due to network issues, git authentication, or timeout (60s limit).

7. **File line counts.** Several line counts are slightly off:
   - SkillsList.svelte: stated 641, actual 640
   - SkillDetailPanel.svelte: stated 365, actual 364
   - config_routes.py: stated ~992, actual 991
   - skills_deployer.py: stated ~1220, actual 1219
   - selective_skill_deployer.py: stated ~870, actual 869
   - config.svelte.ts: stated ~825, actual 824
   - SkillLinksView.svelte: stated ~95, actual 94
   - SkillChip.svelte: stated ~60, actual 59
   - SkillChipList.svelte: stated ~84, actual 83
   These are trivially off-by-one and do not affect the analysis.

8. **Available Skills endpoint pagination parameters.** Research states it supports `page` and `per_page` pagination. Actual code uses `limit`, `cursor`, and `sort` parameters via `extract_pagination_params()` (cursor-based pagination, not page-based).

**Missing considerations added (see new Section 3.6 and revised Section 6):**
- Separate `~/.claude-mpm/cache/skills/` system with `GitSkillSourceManager` and `SkillDiscoveryService`
- Additional manifest at `~/.claude-mpm/cache/skills/system/manifest.json`
- `SkillRecommendationEngine` that loads manifest from cache independently
- `SkillDiscoveryService` which parses SKILL.md frontmatter for descriptions and can extract them
- The intermittent nature of the enrichment failure (sometimes works, sometimes doesn't)
- The fact that even when enrichment works, 58/188 skills remain un-enriched (no manifest match)
- Description field is absent from manifest entirely -- this fundamentally changes Priority 1 impact assessment

### Logical Consistency Check

- **Field counts are consistent** throughout the document (after corrections)
- **Recommendations align with findings** (after correcting Priority 1 impact on descriptions)
- **Prioritization is well-justified** (Priority 1 remains the highest-impact fix, just with corrected scope)
- **No contradictions found** in the architectural analysis

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Current State Analysis](#current-state-analysis)
3. [Available Metadata Sources](#available-metadata-sources)
4. [Frontend Component Architecture](#frontend-component-architecture)
5. [Gap Analysis](#gap-analysis)
6. [Recommended Enrichment Additions](#recommended-enrichment-additions)
7. [Implementation Notes](#implementation-notes)

---

## Executive Summary

The dashboard Skills tab has a **significant metadata enrichment gap**: despite rich skill metadata existing across multiple data sources (manifest, SKILL.md frontmatter, deployment index, skills cache system), the deployed skills list endpoint returns almost entirely empty fields. HAR capture evidence shows two distinct behaviors: one page load with ALL 188 deployed skills returning empty descriptions, "unknown" categories, and zero manifest enrichment; and a second page load where 130/188 skills received manifest enrichment but descriptions remained empty throughout.

The root cause is that `_build_manifest_lookup()` depends on `skills_svc.list_available_skills()`, which requires a `git pull` operation (via `_download_from_github()` in `skills_deployer.py`). When this git operation fails, times out (60s limit), or encounters errors, the manifest lookup table is empty, and all enrichment silently produces no results. The failure is **intermittent** -- the HAR file proves it sometimes works and sometimes does not.

A secondary root cause is that the **manifest does not contain a `description` field** at all. Even when manifest enrichment succeeds fully, descriptions remain empty because neither the manifest nor the deployment index store skill descriptions. Descriptions can only come from SKILL.md frontmatter (19/188 skills) or SKILL.md body text extraction (not currently implemented for the list endpoint).

The skill detail endpoint (`/api/config/skills/{name}/detail`) has substantially richer data, but requires a per-skill API call and is only triggered when a user clicks a specific skill.

**Key finding:** Rich metadata EXISTS in the system across multiple sources. The problems are: (1) a brittle enrichment pipeline with intermittent failure on network-dependent git operations, (2) missing description data in the manifest schema, and (3) a non-existent deployment index file.

---

## Current State Analysis

### 2.1 HAR File Evidence

**Source:** `/Users/mac/Downloads/localhost.har`

**CORRECTED:** The HAR file contains TWO pairs of skill-related API calls, not one. Both pairs were captured at 2026-02-15T15:28:17Z, likely from two page loads or tab switches:

**Pair 1 (no manifest enrichment):**

| Endpoint | Response Size | Status | Enrichment |
|---|---|---|---|
| `/api/config/skills/deployed` | 54,789 bytes | 200 | None (8 base fields only) |
| `/api/config/skills/available` | 43 bytes | 200 | Empty array |

**Pair 2 (partial manifest enrichment):**

| Endpoint | Response Size | Status | Enrichment |
|---|---|---|---|
| `/api/config/skills/deployed` | 86,442 bytes | 200 | 130/188 skills enriched |
| `/api/config/skills/available` | 74,815 bytes | 200 | 158 skills returned |

**Deployed skills response structure (unenriched, Pair 1):**
```json
{
  "name": "universal-testing-test-driven-development",
  "path": "/Users/mac/.claude/skills/universal-testing-test-driven-development",
  "description": "",
  "category": "unknown",
  "collection": "",
  "is_user_requested": false,
  "deploy_mode": "agent_referenced",
  "deploy_date": ""
}
```

**Deployed skills response structure (enriched, Pair 2):**
```json
{
  "name": "toolchains-python-frameworks-django",
  "path": "/Users/mac/workspace/claude-mpm-fork/.claude/skills/toolchains-python-frameworks-django",
  "description": "",
  "category": "unknown",
  "collection": "",
  "is_user_requested": false,
  "deploy_mode": "agent_referenced",
  "deploy_date": "",
  "manifest_name": "django",
  "version": "1.0.0",
  "toolchain": "python",
  "framework": "django",
  "tags": ["web-framework", "django", "orm", "rest-api", "admin"],
  "full_tokens": 7995,
  "entry_point_tokens": 85
}
```

**Critical observations from the HAR data:**
- **Pair 1:** ALL 188 deployed skills have empty descriptions, "unknown" categories, no enrichment fields
- **Pair 2:** 130/188 skills have manifest enrichment (version, toolchain, tags, etc.), but ALL 188 still have `description: ""`, `category: "unknown"`, `collection: ""`, `deploy_date: ""`
- Descriptions remain empty **even when manifest enrichment succeeds** because the manifest has no `description` field
- Category remains "unknown" even with enrichment because category in the deployment index is always empty (the deployment index file does not exist)
- 58/188 skills have no manifest match even when enrichment works (these are likely from a different collection or have naming mismatches)
- The available skills endpoint returns 158 skills in Pair 2 (vs. 160 in manifest -- 2 may have been filtered)

### 2.2 Deployed Skills Endpoint Analysis

**File:** `src/claude_mpm/services/monitor/config_routes.py`
**Handler:** `handle_skills_deployed()` (lines 378-443)

The handler performs enrichment in two stages:

**Stage 1 - Deployment Index Enrichment (lines 389-420):**
Reads `.mpm-deployed-skills.json` from `{project_skills_dir}` and merges:
- `description` - from deployment index meta (always empty -- index file does not exist)
- `category` - from deployment index meta (defaults to "unknown")
- `collection` - which GitHub collection the skill came from
- `deploy_date` - ISO timestamp of deployment (`deployed_at` field)
- `is_user_requested` - boolean (from `user_requested_skills` list)
- `deploy_mode` - "agent_referenced" or "user_defined" (derived from `is_user_requested`)

**Stage 2 - Manifest Enrichment via `_enrich_skill_from_manifest()` (lines 422-425):**
Calls `_build_manifest_lookup()` which depends on `skills_svc.list_available_skills()`.
When manifest data is available, adds:
- `manifest_name`, `version`, `toolchain`, `framework`
- `tags`, `full_tokens`, `entry_point_tokens`
- `description` (fallback from manifest -- but manifest has no description field, so this never provides data)

**Why enrichment fails intermittently:** `_build_manifest_lookup()` (lines 128-150) calls `skills_svc.list_available_skills()` which calls `_download_from_github()` (skills_deployer.py line 444). This performs a `git pull` subprocess call with a 60-second timeout. If the git pull fails, times out, or encounters authentication errors, the exception is caught (line 148) and an empty dict is returned with only a warning log. The local clone at `~/.claude/skills/claude-mpm/` already has the manifest on disk but is never read directly.

### 2.3 Skill Detail Endpoint Analysis

**Handler:** `handle_skill_detail()` (lines 749-873)

This endpoint is significantly richer, combining THREE sources:

1. **SKILL.md Frontmatter Parsing (lines 779-809):** Extracts `when_to_use`, `languages`, `progressive_disclosure` (with `summary` and `quick_start`), `references`, `frontmatter_name`, `frontmatter_tags`, `description`
2. **Manifest Cross-reference (lines 812-835):** Adds `manifest_name`, `version`, `toolchain`, `framework`, `tags`, `full_tokens`, `entry_point_tokens`, `requires`, `author`, `updated`, `source_path`. Also attempts description fallback from manifest (line 832-833), but this is ineffective since manifest lacks the field.
3. **Skill-to-Agent Links (lines 837-860):** via `SkillToAgentMapper` service, adds `used_by_agents` (list of agent names), `agent_count`

**Full detail response fields (22 unique):**
```
agent_count, author, description, entry_point_tokens, framework,
frontmatter_name, frontmatter_tags, full_tokens, languages, manifest_name,
name, quick_start, references, requires, source_path, summary, tags,
toolchain, updated, used_by_agents, version, when_to_use
```

**IMPORTANT:** The detail endpoint suffers from the same manifest enrichment brittleness. If the git pull fails at the time of the detail request, manifest-derived fields (version, toolchain, tags, etc.) will also be empty in the detail response. Only frontmatter-derived and skill-links-derived fields are network-independent.

### 2.4 Available Skills Endpoint Analysis

**Handler:** `handle_skills_available()` (lines 446-554)

Returns skills from the manifest that can be deployed. Supports:
- Cursor-based pagination (`limit`, `cursor`, `sort` via `extract_pagination_params()`)
- Collection filtering
- Category enrichment (adds category from nested dict key for nested manifest structures, line 496)
- Agent count enrichment from skill-links (lines 502-526)
- Cache-Control header: `private, max-age=120` (line 547)

Returns empty when the manifest download (`list_available_skills()` -> `_download_from_github()`) fails. The HAR shows this endpoint succeeded in Pair 2 (158 skills) but failed in Pair 1 (empty array).

---

## Available Metadata Sources

### 3.1 Source 1: Manifest (`manifest.json`)

**Location:** `~/.claude/skills/claude-mpm/manifest.json` (cloned git repository)
**Origin:** Git clone/pull from GitHub collection repository (default: `bobmatnyc/claude-mpm-skills`)
**Total skills indexed:** 160 (actual count from nested structure; ~~metadata says 160~~ metadata says 156 -- discrepancy)

**Structure:** Nested dict with categories containing subcategories:
```
skills.universal: 37 skills (flat list)
skills.toolchains: 15 subcategories (ai:9, databases:1, elixir:4, golang:7, java:1,
  javascript:19, nextjs:3, php:6, platforms:26, python:10, rust:4, typescript:14,
  ui:4, universal:9, visualbasic:4)
skills.examples: 2 skills (flat list)
```

**Fields per skill in manifest (14 fields):**

| Field | Populated Count (of 160) | Description |
|---|---|---|
| `name` | 160 | Skill identifier |
| `version` | 160 | Semantic version (e.g., "1.0.0") |
| `category` | 160 | Hierarchical category (e.g., "testing", "debugging") |
| `toolchain` | 121 (null for 39) | Language/platform grouping (e.g., "python", "javascript") |
| `framework` | 37 (null for 123) | Specific framework (e.g., "react", "django", "fastapi") |
| `tags` | ~~160~~ 159 | Array of descriptive tags (1 skill has empty tags) |
| `entry_point_tokens` | 160 | Token count for SKILL.md entry point |
| `full_tokens` | 160 | Total token count including references |
| `requires` | 21 (empty array for 139) | Array of skill dependencies |
| `author` | 160 | Attribution string |
| `updated` | 160 | Last update timestamp |
| `source_path` | 160 | Path within collection repository |
| `has_references` | 35 (field absent for 125) | Boolean - whether skill has reference files |
| `reference_files` | 35 (field absent for 125) | Array of reference file paths and metadata |

**CRITICAL: No `description` field exists in the manifest.** The code at line 186 of config_routes.py attempts `manifest_entry.get("description")` but this will always return None because the manifest schema does not include descriptions.

**Manifest top-level metadata:**
```json
{
  "version": "2.0",
  "repository": "bobmatnyc/claude-mpm-skills",
  "updated": "2025-06-07T...",
  "description": "Claude MPM Skills Collection - Curated skills...",
  "metadata": {
    "total_skills": 156,
    "categories": {"universal": 37, "toolchains": 117, "examples": 2},
    "toolchains": {"ai": 9, "databases": 1, ...},
    "last_updated": "2026-01-28",
    "schema_version": "2.0.0"
  },
  "provenance": {
    "generated_by": "...",
    "commit": "..."
  }
}
```

**Note:** `metadata.total_skills` says 156 but actual skill count is 160 (4 skill discrepancy, likely a manifest generation bug).

### 3.2 Source 2: SKILL.md Frontmatter

**Location:** `{project}/.claude/skills/{skill-name}/SKILL.md` (YAML frontmatter block)
**Coverage:** Only 19 of 188 deployed skills (10.1%) have frontmatter

**Frontmatter fields discovered across deployed skills:**

| Field | Count (of 19) | Description |
|---|---|---|
| `name` | 19 | Skill display name |
| `description` | 19 | Short description |
| `version` | 19 | Version string |
| `category` | 19 | Category classification |
| `tags` | 19 | Array of tags |
| `user-invocable` | 10 | Boolean - can user invoke directly |
| `when_to_use` | 8 | Usage guidance string |
| `author` | 1 | Author attribution |
| `license` | 1 | License identifier |
| `progressive_disclosure` | 1 | Structure with summary/quick_start |
| `context_limit` | 1 | Token budget hint |
| `requires_tools` | 1 | Array of required tool names |

**Key limitation:** 169 of 188 deployed skills (89.9%) have NO frontmatter at all. Frontmatter-only enrichment will miss the vast majority of skills.

### 3.3 Source 3: Deployment Index (`.mpm-deployed-skills.json`)

**Expected location:** `{project_skills_dir}/.mpm-deployed-skills.json`
**For this project:** `/Users/mac/workspace/claude-mpm-fork/.claude/skills/.mpm-deployed-skills.json`
**Managed by:** `SelectiveSkillDeployer` in `src/claude_mpm/services/skills/selective_skill_deployer.py`
**Constant:** `DEPLOYED_INDEX_FILE = ".mpm-deployed-skills.json"` (line 51)

**VERIFIED: This file does not exist.** The `load_deployment_index()` function (line 413) handles this gracefully by returning `{"deployed_skills": {}, "user_requested_skills": [], "last_sync": None}`. This fully explains why all deployment index fields (`collection`, `deploy_date`, `description`, `category`) are empty.

~~**Location:** `~/.claude/.mpm-deployed-skills.json`~~ **CORRECTED:** The research incorrectly stated the location. The code uses `project_skills_dir / DEPLOYED_INDEX_FILE` where `project_skills_dir = Path.cwd() / ".claude" / "skills"` (config_routes.py line 396).

**Fields tracked (when file exists):**

| Field | Description |
|---|---|
| `deployed_skills` | Dict mapping skill name to `{collection, deployed_at}` |
| `user_requested_skills` | List of skill names explicitly requested by user |
| `last_sync` | ISO timestamp of last sync operation |

**Per-skill deployment record:**
```json
{
  "collection": "claude-mpm",
  "deployed_at": "2025-06-07T12:00:00Z"
}
```

**Note:** The deployment record does NOT contain `description` or `category` fields. The handler at line 409 does `meta.get("description", "")` and `meta.get("category", "unknown")`, but the deployment index schema only stores `collection` and `deployed_at`. This means even if the file existed, descriptions and categories would still be empty from this source.

### 3.4 Source 4: Skill-to-Agent Links

**Service:** `SkillToAgentMapper` (used by detail and available-skills endpoints)
**Data source:** Scans agent frontmatter `skills:` arrays and agent body content markers

**Link types:**
- `frontmatter` - Skill listed in agent YAML frontmatter `skills:` field
- `content_marker` - Skill name appears in agent body text (e.g., `@skill-name`)
- `user_defined` - Manually assigned by user
- `inferred` - System-inferred relationship

**Derived metrics:**
- `agent_count` - Number of agents referencing this skill
- `used_by_agents` - List of agent names using this skill

### 3.5 Source 5: Skill File System Structure

**Location:** `{project}/.claude/skills/{skill-name}/`
**Observed across 188 deployed skills:**

| Content | Count | Notes |
|---|---|---|
| `SKILL.md` | 188 | Always present (required) |
| `references/` directory | 1 | Only `toolchains-rust-desktop-applications` |
| `metadata.json` | 1 | Only `toolchains-rust-desktop-applications` |
| `scripts/` directory | 0 | None observed |
| `assets/` directory | 0 | None observed |

### 3.6 Source 6: Skills Cache System (NEW - Missing from original research)

**ADDED IN VERIFICATION:** The project has a separate skill caching system at `~/.claude-mpm/cache/skills/` managed by `GitSkillSourceManager` (`src/claude_mpm/services/skills/git_skill_source_manager.py`). This was not covered in the original research.

**Cache locations discovered:**
- `~/.claude-mpm/cache/skills/system/manifest.json` (110,783 bytes, same content as collection manifest)
- `~/.claude-mpm/cache/skills/claude-mpm-skills/manifest.json` (108,149 bytes, slightly older)
- `~/.claude-mpm/cache/skills/anthropic-official/skills/` (16 skill directories from Anthropic)

**Related services not covered in original research:**
- `SkillDiscoveryService` (`src/claude_mpm/services/skills/skill_discovery_service.py`) - Parses SKILL.md frontmatter including descriptions; requires both `name` and `description` fields for valid parsing (lines 318-324)
- `SkillRecommendationEngine` (`src/claude_mpm/services/skills/skill_recommendation_engine.py`) - Loads manifest independently from `~/.claude-mpm/cache/skills/system/manifest.json` (line 110)
- `GitSkillSourceManager` - Manages two-phase deployment: cache sync (git clone/pull) then deploy from cache to project

**Relevance to enrichment:** The `~/.claude-mpm/cache/skills/system/manifest.json` is another local manifest copy that could serve as a fallback for `_build_manifest_lookup()`, eliminating the need for the git pull network call entirely. However, this manifest also has NO `description` field.

---

## Frontend Component Architecture

### 4.1 TypeScript Type Definitions

**File:** `src/claude_mpm/dashboard-svelte/src/lib/stores/config.svelte.ts`

**`DeployedSkill` interface (list-level data):**
```typescript
export interface DeployedSkill {
  name: string;
  path: string;
  description: string;
  category: string;
  collection: string;
  is_user_requested: boolean;
  deploy_mode: 'agent_referenced' | 'user_defined';
  deploy_date: string;
  // Phase 2 enrichment fields (optional for backward compatibility)
  version?: string;
  toolchain?: string | null;
  framework?: string | null;
  tags?: string[];
  full_tokens?: number;
  entry_point_tokens?: number;
  manifest_name?: string;
}
```

**`AvailableSkill` interface:**
```typescript
export interface AvailableSkill {
  name: string;
  description: string;
  category: string;
  collection: string;
  is_deployed: boolean;
  // Extended fields from API (optional for VP-1-A graceful degradation)
  version?: string;
  toolchain?: string | null;
  framework?: string | null;
  tags?: string[];
  entry_point_tokens?: number;
  full_tokens?: number;
  requires?: string[];
  author?: string;
  updated?: string;
  source_path?: string;
  agent_count?: number;
}
```

**`SkillDetailData` interface (detail-level data):**
```typescript
export interface SkillDetailData {
  name: string;
  description?: string;
  version?: string;
  toolchain?: string | null;
  framework?: string | null;
  tags?: string[];
  full_tokens?: number;
  entry_point_tokens?: number;
  requires?: string[];
  author?: string;
  updated?: string;
  source_path?: string;
  when_to_use?: string;
  languages?: string;
  summary?: string;
  quick_start?: string;
  frontmatter_name?: string;
  frontmatter_tags?: string[];
  references?: { path: string; purpose: string }[];
  used_by_agents?: string[];
  agent_count?: number;
}
```

### 4.2 Component Hierarchy

```
ConfigView.svelte
  +-- SkillFilterBar.svelte       (search + filter controls)
  +-- SkillsList.svelte           (main list - deployed + available sections)
  |     +-- [per skill row]       (inline badges and metadata)
  +-- SkillDetailPanel.svelte     (right panel - rich detail on selection)
  +-- SkillLinksView.svelte       (deprecated sub-tab)
        +-- AgentSkillPanel.svelte
        +-- SkillChipList.svelte
              +-- SkillChip.svelte
```

### 4.3 SkillsList.svelte - List View Display

**File:** `src/claude_mpm/dashboard-svelte/src/lib/components/config/SkillsList.svelte` (640 lines)

**Currently displays per skill row:**
- Skill name (formatted: strips toolchain prefix for display)
- Version badge (if available from manifest enrichment)
- Toolchain badge (color-coded, if available)
- Deploy mode badge ("agent_referenced" or "user_defined")
- `is_user_requested` indicator badge
- Collection name
- Tags (first 3, with "+N more" overflow)
- Token count (`full_tokens`)

**Features:**
- Search: Multi-field search across name, description, category, toolchain, tags, collection
- Sort: By name, version, or status
- Grouping: By toolchain (collapsible groups with counts)
- Filter bar: Toolchain filter, status filter (deployed/available)
- Session-persisted filter state
- Deploy/undeploy buttons with confirmation dialogs

**What is NOT shown in list view:**
- Description (field exists but always empty per HAR)
- Category (field exists but always "unknown" per HAR)
- Framework
- Author
- Updated date
- Entry point tokens (only full_tokens shown)
- Dependencies/requires
- Agent usage count

### 4.4 SkillDetailPanel.svelte - Detail Panel Display

**File:** `src/claude_mpm/dashboard-svelte/src/lib/components/config/SkillDetailPanel.svelte` (364 lines)

**Displays (when detail API data loads):**

**Header section:**
- Name, version badge, deployed/available status badge

**Description section:**
- `description` text (from frontmatter)

**Metadata grid:**
- Toolchain
- Token counts (full_tokens, entry_point_tokens)
- Framework
- Updated date (formatted relative)

**Tags section:**
- All tags displayed as chips

**Collapsible sections:**
- "When to Use" - shows `when_to_use` text
- "Used By" - lists agents with clickable navigation to agent detail
- "Dependencies" - shows `requires` array as chips
- "References" - lists reference files with path and purpose

**Footer:**
- Author, updated date, languages, source_path

**Progressive loading pattern:**
- Shows list-level data immediately (from `DeployedSkill`/`AvailableSkill`)
- Fetches detail from `/api/config/skills/{name}/detail` on selection
- Upgrades display with richer fields when detail response arrives
- LRU cache (max 50 entries) prevents redundant API calls

### 4.5 SkillFilterBar.svelte

**File:** `src/claude_mpm/dashboard-svelte/src/lib/components/config/SkillFilterBar.svelte` (124 lines)

**Filter dimensions:**
- Search text (multi-field)
- Toolchain (multi-select dropdown with counts)
- Status (deployed/available toggle)

**State persistence:** Filters saved to `sessionStorage` with key `skill-filters`

### 4.6 Skill Links Components

**SkillLinksView.svelte** (94 lines) - Deprecated dual-panel view showing agent-to-skill mappings
- Shows total agents, total skills, average skills per agent
- Left panel: Agent list with skill counts
- Right panel: Skills for selected agent grouped by source type

**SkillChip.svelte** (59 lines) - Color-coded chip showing skill link with source type indicator
- Source type colors: blue (frontmatter), purple (content_marker), green (user_defined), gray (inferred)
- Warning state for undeployed skills

**SkillChipList.svelte** (83 lines) - Groups skill chips by source type

### 4.7 Data Flow

```
[Backend API]                      [Frontend Store]           [Components]

/skills/deployed ──────> fetchDeployedSkills() ──> deployedSkills store ──> SkillsList.svelte
                         (8-14 fields,                                     (shows name, badges)
                          intermittent enrichment)

/skills/available ─────> fetchAvailableSkills() ─> availableSkills store ─> SkillsList.svelte
                         (sometimes empty,                                 (available section)
                          sometimes 158 skills)

/skills/{name}/detail ─> fetchSkillDetail() ────> skillDetailCache ──────> SkillDetailPanel.svelte
                         (22 fields, rich data)    (LRU, max 50)           (rich detail view)

/skill-links/ ─────────> loadSkillLinks() ──────> skillLinksStore ───────> SkillLinksView.svelte
                         (agent-skill mappings)                            (deprecated tab)
```

---

## Gap Analysis

### 5.1 List-Level Enrichment Gap (Critical)

The deployed skills list endpoint returns 8 base fields, with up to 7 additional manifest enrichment fields when the git pull succeeds:

| Field | Expected | Actual (HAR Pair 1) | Actual (HAR Pair 2) | Root Cause |
|---|---|---|---|---|
| `name` | Populated | Populated | Populated | OK |
| `path` | Populated | Populated | Populated | OK |
| `description` | From manifest/frontmatter | Empty string | Empty string | **Manifest has no description field; deployment index file missing** |
| `category` | From deployment index | "unknown" | "unknown" | **Deployment index file does not exist** |
| `collection` | From deployment index | Empty string | Empty string | **Deployment index file does not exist** |
| `is_user_requested` | Boolean | false (all) | false (all) | Correct (no user_requested list in absent index) |
| `deploy_mode` | From deployment index | "agent_referenced" (all) | "agent_referenced" (all) | Correct (derived from empty user_requested list) |
| `deploy_date` | From deployment index | Empty string | Empty string | **Deployment index file does not exist** |
| `version` | From manifest | Missing | 130/188 populated | **Intermittent git pull failure** |
| `toolchain` | From manifest | Missing | 93/188 populated | **Intermittent + 39 are null in manifest** |
| `framework` | From manifest | Missing | Partial | **Intermittent + 123 are null in manifest** |
| `tags` | From manifest | Missing | 129/188 populated | **Intermittent git pull failure** |
| `full_tokens` | From manifest | Missing | 130/188 populated | **Intermittent git pull failure** |
| `entry_point_tokens` | From manifest | Missing | 130/188 populated | **Intermittent git pull failure** |

### 5.2 Available Skills Gap

The available skills endpoint returns intermittently:
- **When git pull fails:** Empty array (Pair 1 in HAR)
- **When git pull succeeds:** 158 skills with metadata but no descriptions (Pair 2 in HAR)

When empty:
- Users cannot browse skills available for deployment
- The "Available" section in SkillsList.svelte is always empty
- Deploy functionality for new skills is non-functional through the UI

### 5.3 Deployment Index Enrichment Gap

The deployment index file (`.mpm-deployed-skills.json`) **does not exist** at the expected location (`{project}/.claude/skills/.mpm-deployed-skills.json`). This is the definitive root cause for empty `collection`, `deploy_date`, `description`, and `category` fields.

~~This suggests either:~~
~~1. The deployment index file does not exist or is empty~~
~~2. The enrichment code path for deployment index data has a bug~~
~~3. Skills were deployed before the tracking system was implemented~~

**CORRECTED:** The deployment index file simply does not exist. Skills in this project were likely deployed via direct file copy or an older deployment mechanism that predates the `SelectiveSkillDeployer` tracking system. Furthermore, even if the file existed, it would only contain `collection` and `deployed_at` per skill -- it does NOT store `description` or `category` fields, so the handler's `meta.get("description", "")` and `meta.get("category", "unknown")` at lines 409-410 would still return empty/default values.

### 5.4 Metadata That EXISTS But Is NOT Surfaced

**Available in manifest but NOT in list endpoint (even when manifest works):**
- `requires` (skill dependencies) - only in detail endpoint
- `author` - only in detail endpoint
- `updated` - only in detail endpoint
- `source_path` - only in detail endpoint
- `has_references` - not surfaced anywhere in list
- `reference_files` - only in detail endpoint

**Available from SKILL.md but NOT in list endpoint:**
- `when_to_use` - only in detail endpoint
- `languages` - only in detail endpoint
- `user-invocable` - not surfaced at all
- `context_limit` - not surfaced at all
- `requires_tools` - not surfaced at all

**Derivable from skill-links but NOT in list endpoint:**
- `agent_count` - only in detail endpoint and available skills endpoint
- `used_by_agents` - only in detail endpoint

### 5.5 Description Gap (NEW - Added in verification)

**Descriptions are empty across ALL sources used by the list endpoint:**
1. Manifest: No `description` field exists (0/160 skills)
2. Deployment index: No `description` field in schema, plus file does not exist
3. SKILL.md frontmatter: Only parsed in the detail endpoint, not the list endpoint

**Descriptions DO exist in:**
1. SKILL.md frontmatter (19/188 skills have `description` in frontmatter)
2. SKILL.md body text (all 188 skills have markdown content that could be parsed)
3. `SkillDiscoveryService` (parses frontmatter descriptions from cached skills, but is not used by the list endpoint)

---

## Recommended Enrichment Additions

### Priority 1: Fix Manifest Enrichment Pipeline (Critical)

**Problem:** `_build_manifest_lookup()` silently returns empty when `list_available_skills()` fails due to git pull network errors.

**Recommended approach:**
1. **Read local manifest cache first.** The manifest is already on disk at `~/.claude/skills/claude-mpm/manifest.json` (and also at `~/.claude-mpm/cache/skills/system/manifest.json`). Read it directly from disk instead of requiring a git pull through `list_available_skills()`.
2. **Add fallback chain:** Local manifest files -> network download -> empty (with warning log).
3. **Add logging:** Log when manifest lookup produces zero matches so failures are visible.
4. **Handle nested structure:** The manifest uses a nested dict structure (categories containing subcategories). The existing `_flatten_manifest_skills()` in skills_deployer.py handles this.

**Impact:** Fixes manifest-derived enrichment reliably: ~~description,~~ category (from manifest category field), version, toolchain, framework, tags, tokens all become available in the list view. **NOTE: This does NOT fix descriptions** because the manifest has no description field. It DOES fix category, since each skill in the manifest has a `category` field (100% populated).

**Implementation location:** `config_routes.py`, `_build_manifest_lookup()` function (lines 128-150)

**IMPORTANT NUANCE:** Even with this fix, 58/188 deployed skills may not match any manifest entry (based on HAR Pair 2 showing only 130/188 enriched). The `_find_manifest_entry()` function (lines 153-166) tries exact match then suffix match, but naming mismatches between deployed skill directory names and manifest skill names may leave some skills unenriched.

### Priority 2: Surface `description` from SKILL.md Content (Elevated from Priority 3)

**Problem:** Descriptions are empty EVERYWHERE -- manifest has no description field, deployment index has no description field, and SKILL.md frontmatter parsing only happens in the detail endpoint. ~~Only 19/188 skills have frontmatter descriptions.~~

**ELEVATED PRIORITY:** Since Priority 1 does NOT fix descriptions (as originally claimed), this becomes the most impactful change for user-visible description display.

**Recommendation:**
1. Parse SKILL.md frontmatter for `description` in the list endpoint (addresses 19 skills)
2. Fallback: Extract first non-heading paragraph from SKILL.md body (addresses remaining 169 skills)
3. Fallback: Use manifest `name` field as formatted display name

**Implementation:** Add a `_extract_skill_description()` helper that reads SKILL.md and extracts the first meaningful paragraph. Consider leveraging `SkillDiscoveryService._parse_skill_file()` which already handles frontmatter parsing including description extraction (skill_discovery_service.py lines 317-328).

**Performance consideration:** Reading 188 SKILL.md files at list-endpoint time could be slow. Consider caching descriptions at server startup or on first request.

### Priority 3: Add `agent_count` to List Endpoint (was Priority 2)

**Currently:** Agent count is only available in the detail endpoint and available skills endpoint.
**Recommendation:** Add `agent_count` to the deployed skills list response by querying the `SkillToAgentMapper` during list enrichment.
**Benefit:** Users can immediately see which skills are widely used vs. single-agent without clicking each one.
**Complexity:** Low - the `SkillToAgentMapper` is already initialized and used in other endpoints.

### Priority 4: Create or Populate Deployment Index

**Problem:** The `.mpm-deployed-skills.json` file does not exist, causing all deployment tracking fields to be empty.

**Recommendation:**
1. Generate the deployment index file by scanning current deployed skills and inferring metadata
2. Populate `collection` by matching deployed skill names against known collection manifests
3. Set `deployed_at` to the file modification time of each skill's SKILL.md as a best-effort timestamp
4. Hook into future deploy/undeploy operations to maintain the index going forward

**Note:** This is a one-time data migration task plus ongoing maintenance.

### Priority 5: Add `category` Fallback (was Priority 5)

**Problem:** Category is "unknown" because the deployment index has no category field and the manifest enrichment is intermittent.

**Recommendation:**
1. Primary: Fix manifest enrichment (Priority 1) -- the manifest DOES have category (100% populated)
2. Fallback: Derive category from skill name prefix convention (e.g., `universal-testing-*` -> "testing", `toolchains-python-*` -> "python toolchain")
3. The naming convention `{toolchain}-{category}-{name}` is consistent across the collection

### Priority 6: Enrich Filter Bar with Category

**Currently:** SkillFilterBar only filters by toolchain and status.
**Recommendation:** Add category as a third filter dimension once category data is populated.
**Benefit:** Users can filter by functional area (testing, debugging, security, etc.)

### Priority 7: Add `requires` to List View

**Currently:** Skill dependencies only visible in detail panel.
**Recommendation:** Show dependency count badge in list view (e.g., "3 deps") with tooltip listing them.
**Benefit:** Users can see dependency complexity at a glance.

### Priority 8: Surface `user-invocable` Flag

**Problem:** 10 skills have `user-invocable: true` in frontmatter but this is never surfaced.
**Recommendation:** Add a small badge or indicator in both list and detail views.
**Benefit:** Users know which skills they can invoke directly vs. agent-only skills.

---

## Implementation Notes

### 7.1 Architecture for Local Manifest Reading

The most impactful fix is reading the cached manifest from disk. Here is the data flow:

```
Current (intermittently broken):
  _build_manifest_lookup()
    -> skills_svc.list_available_skills()    # Network-dependent
      -> _download_from_github()             # git pull subprocess, 60s timeout
        -> Reads manifest.json from cloned repo
      -> Flattens skills, groups by category/toolchain
    -> Builds lookup dict from flattened skills
    -> OR: Returns empty dict on any exception  # Silent failure

Proposed (resilient):
  _build_manifest_lookup()
    -> Try: Read ~/.claude/skills/claude-mpm/manifest.json from disk
      -> Parse nested skills dict
      -> Flatten using existing _flatten_manifest_skills() logic
      -> Build name -> metadata lookup
    -> Fallback: Read ~/.claude-mpm/cache/skills/system/manifest.json
    -> Fallback: skills_svc.list_available_skills()  # Network call
    -> Fallback: Return empty dict + log warning
```

**Key files to modify:**
- `src/claude_mpm/services/monitor/config_routes.py` - `_build_manifest_lookup()` (lines 128-150)

**Manifest parsing logic already exists** in `skills_deployer.py` via `_flatten_manifest_skills()` which handles both flat list and nested dict structures.

**Local manifest files available (verified to exist on disk):**
1. `~/.claude/skills/claude-mpm/manifest.json` (110,783 bytes, updated 2026-02-13)
2. `~/.claude-mpm/cache/skills/system/manifest.json` (110,783 bytes, updated 2026-02-12)
3. `~/.claude-mpm/cache/skills/claude-mpm-skills/manifest.json` (108,149 bytes, updated 2026-02-04)

### 7.2 TypeScript Interface Extensions

The frontend `DeployedSkill` interface already has optional fields for manifest enrichment data (`version?`, `toolchain?`, `framework?`, `tags?`, `full_tokens?`, `entry_point_tokens?`). No frontend type changes needed for Priority 1 fix.

For Priority 3 (`agent_count`), add to `DeployedSkill`:
```typescript
agent_count?: number;
```

For Priority 8 (`user_invocable`), add to both `DeployedSkill` and `SkillDetailData`:
```typescript
user_invocable?: boolean;
```

### 7.3 Component Display Locations

| New Data Field | List View (SkillsList) | Detail Panel (SkillDetailPanel) |
|---|---|---|
| `description` (new extraction) | Below name, truncated | Full text in header area |
| `category` (fixed via manifest) | Used in grouping option | Metadata grid |
| `agent_count` (new) | Badge next to name | Already in "Used By" section |
| `user_invocable` (new) | Small badge | Badge in header |
| `requires` count (new) | Badge with count | Already in "Dependencies" section |

### 7.4 Caching Considerations

- The detail endpoint already uses an LRU cache (max 50 entries) on the frontend
- Manifest data should be cached on the backend with a configurable TTL
- The local manifest file can be read once per server startup and held in memory
- Invalidation: Re-read manifest after any skill sync/deploy operation
- Description extraction from SKILL.md files should also be cached (reading 188 files is expensive)

### 7.5 Backward Compatibility

All new fields should be added as optional (with `?` in TypeScript interfaces) to maintain backward compatibility. The frontend already handles missing fields gracefully with conditional rendering (`{#if skill.version}` patterns throughout SkillsList.svelte and SkillDetailPanel.svelte).

### 7.6 Testing Considerations

- Verify enrichment with both cached and uncached manifest states
- Test with skills that have frontmatter vs. those without
- Test the description extraction fallback chain
- Verify filter bar updates when new filter dimensions are added
- Test detail panel progressive loading with enriched list data
- **NEW:** Test behavior when deployment index file does not exist (current state)
- **NEW:** Test manifest reading from multiple fallback locations
- **NEW:** Test with skills that have no manifest match (58/188 in current data)
- **NEW:** Test performance impact of reading 188 SKILL.md files for description extraction

---

## Appendix A: File Reference

| File | Purpose | Lines |
|---|---|---|
| `src/claude_mpm/services/monitor/config_routes.py` | Backend API route handlers | 991 |
| `src/claude_mpm/services/skills_deployer.py` | Skill download/deploy from GitHub | 1219 |
| `src/claude_mpm/services/skills/selective_skill_deployer.py` | Selective deployment + tracking | 869 |
| `src/claude_mpm/services/skills/skill_discovery_service.py` | Skill file parsing from cache (NEW) | N/A |
| `src/claude_mpm/services/skills/skill_recommendation_engine.py` | Skill recommendation engine (NEW) | N/A |
| `src/claude_mpm/services/skills/git_skill_source_manager.py` | Git-based skill source management (NEW) | N/A |
| `src/claude_mpm/dashboard-svelte/src/lib/stores/config.svelte.ts` | Frontend stores + type definitions | 824 |
| `src/claude_mpm/dashboard-svelte/src/lib/stores/config/skillLinks.svelte.ts` | Skill-to-agent link store | ~135 |
| `src/claude_mpm/dashboard-svelte/src/lib/components/config/SkillsList.svelte` | Main skills list component | 640 |
| `src/claude_mpm/dashboard-svelte/src/lib/components/config/SkillDetailPanel.svelte` | Skill detail panel | 364 |
| `src/claude_mpm/dashboard-svelte/src/lib/components/config/SkillFilterBar.svelte` | Filter bar component | 124 |
| `src/claude_mpm/dashboard-svelte/src/lib/components/config/SkillLinksView.svelte` | Deprecated skill links view | 94 |
| `src/claude_mpm/dashboard-svelte/src/lib/components/config/SkillChip.svelte` | Skill link chip component | 59 |
| `src/claude_mpm/dashboard-svelte/src/lib/components/config/SkillChipList.svelte` | Grouped skill chips | 83 |
| `~/.claude/skills/claude-mpm/manifest.json` | Cached skill collection manifest (git repo) | N/A |
| `~/.claude-mpm/cache/skills/system/manifest.json` | Skills cache manifest copy (NEW) | N/A |
| `{project}/.claude/skills/.mpm-deployed-skills.json` | Deployment tracking index (DOES NOT EXIST) | N/A |

## Appendix B: Manifest Field Coverage

Distribution of manifest fields across 160 indexed skills:

```
Field                 Populated    Percentage
----                  ---------    ----------
name                  160/160      100.0%
version               160/160      100.0%
category              160/160      100.0%
tags                  159/160       99.4%    (CORRECTED: was 160/160)
entry_point_tokens    160/160      100.0%
full_tokens           160/160      100.0%
author                160/160      100.0%
updated               160/160      100.0%
source_path           160/160      100.0%
toolchain             121/160       75.6%
framework              37/160       23.1%
has_references         35/160       21.9%    (field absent for remaining 125)
reference_files        35/160       21.9%    (field absent for remaining 125)
requires               21/160       13.1%    (empty array for remaining 139)
description             0/160        0.0%    (ADDED: field does not exist in manifest)
```

**Note:** `metadata.total_skills` reports 156 but actual count is 160 (discrepancy).

## Appendix C: SKILL.md Frontmatter Coverage

Distribution of frontmatter fields across 188 deployed skills:

```
Status                Count    Percentage
------                -----    ----------
Has frontmatter        19      10.1%
No frontmatter        169      89.9%

Frontmatter Fields (of 19 with frontmatter):
name                   19/19   100.0%
description            19/19   100.0%
version                19/19   100.0%
category               19/19   100.0%
tags                   19/19   100.0%
user-invocable         10/19    52.6%
when_to_use             8/19    42.1%
author                  1/19     5.3%
license                 1/19     5.3%
progressive_disclosure  1/19     5.3%
context_limit           1/19     5.3%
requires_tools          1/19     5.3%
```

## Appendix D: HAR Evidence Summary (NEW)

The HAR file at `/Users/mac/Downloads/localhost.har` contains two pairs of skill API calls at the same timestamp (2026-02-15T15:28:17Z):

```
Pair 1 (manifest enrichment FAILED):
  /skills/deployed:  54,789 bytes | 188 skills | 0 enriched | 0 descriptions
  /skills/available:     43 bytes | 0 skills   | empty array

Pair 2 (manifest enrichment SUCCEEDED):
  /skills/deployed:  86,442 bytes | 188 skills | 130 enriched | 0 descriptions
  /skills/available: 74,815 bytes | 158 skills | full metadata | 0 descriptions

Key insight: Descriptions remain empty in BOTH cases because the manifest
has no description field and the deployment index does not exist.
```
