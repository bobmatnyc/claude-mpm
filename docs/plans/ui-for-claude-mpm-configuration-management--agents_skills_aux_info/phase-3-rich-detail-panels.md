# Phase 3: Rich Detail Panels & Advanced Features

## Revision History
- **v1 (2026-02-14)**: Initial draft
- **v2 (2026-02-14)**: Revised based on devil's advocate review. Key changes: (1) Replaced collaboration graph (Feature 5) with simpler "Related Agents" list per R5; (2) Removed virtual scrolling (Feature 7) from scope — moved to future optimization per R6; (3) Fixed agent deployment index prerequisite — removed, agents use filesystem presence check per R1; (4) Fixed deployment index naming to `.mpm-deployed-skills.json` per R2; (5) Strengthened all acceptance criteria to be specific and testable per R7; (6) Added Phase 2 → Phase 3 dependency verification; (7) Reduced scope estimates for simplified features.
- **v3 (2026-02-14)**: Amended with Verification Pass 1 findings. Key changes: (1) Added strict deployment ordering requirement — Phase 2 MUST be fully deployed before Phase 3 (VP-1-DEPLOY); (2) Added integration testing requirement with real service instances (VP-1-TEST); (3) Added note about Phase 2 path traversal validation dependency (VP-1-SEC).

> **Agents & Skills UI Enhancement for Claude MPM Dashboard**
>
> Comprehensive implementation plan for progressive-disclosure detail panels,
> filter dropdowns, version mismatch detection, agent collaboration links,
> skill links integration, and search enhancements.
>
> Date: 2026-02-14
> Branch: `ui-agents-skills-config`
> Status: PLANNING
> Depends on: Phase 1 (Frontend Quick Wins), Phase 2 (Backend API Enrichment)

---

## Verification Amendments (Cross-Cutting)

> The following amendments were added after Verification Pass 1 (VP-1) identified HIGH and MODERATE severity issues across the Phase 1-3 plan set. See `docs/research/.../verification-pass-1/` for the full analysis.

### VP-1-DEPLOY: Phase 2 Dependency is STRICT, Not Soft

Phase 3 has a **hard dependency** on Phase 2 being fully deployed. This is not a "nice to have" — Phase 3 will produce 404 errors and broken UI without it.

**Specifically, Phase 3 REQUIRES these Phase 2 deliverables to exist before implementation begins:**

| Phase 3 Feature | Requires Phase 2 Deliverable | Failure Mode if Missing |
|---|---|---|
| Feature 1 (Agent Detail Panel) | `GET /api/config/agents/{name}/detail` (Phase 2 Step 4) | 404 error on every agent click; detail sections empty |
| Feature 2 (Skill Detail Panel) | `GET /api/config/skills/{name}/detail` (Phase 2 Step 5) | 404 error on every skill click; "when to use" missing |
| Feature 1 (Color Dot) | `color` field in deployed agents response (Phase 2 Step 1) | All dots render gray; no visual differentiation |
| Feature 4 (Version Mismatch) | `version` field in deployed skills response (Phase 2 Step 3) | Version comparison returns "unknown" for all items |
| Features 5, 6 (Collaboration, Skill Links) | `handoff_agents`, `skills` in agent detail response (Phase 2 Step 4) | Sections show "No data" or are hidden |
| Feature 6 (Used By) | `used_by_agents` in skill detail response (Phase 2 Step 5) | "Used By" section empty |

**Pre-deployment checklist**: Before starting Phase 3 implementation, verify each Phase 2 endpoint exists and returns the expected fields by making test API calls. The Phase 2 plan's "Phase 2 -> Phase 3 Contract" table lists all deliverables.

### VP-1-SEC: Path Traversal Validation Dependency

Phase 3 detail panels call the Phase 2 detail endpoints (`GET /api/config/agents/{name}/detail`, `GET /api/config/skills/{name}/detail`). These endpoints accept user-supplied `{name}` parameters that are used to construct filesystem paths. Phase 2 Step 4 and Step 5 have been amended (VP-1-SEC, HIGH severity) to include mandatory `validate_safe_name()` calls before any filesystem operation. Phase 3 depends on this validation being in place. If Phase 3 is implemented before Phase 2's path traversal protection, the frontend would send unsanitized user input to unprotected endpoints.

### VP-1-TEST: Integration Testing Requirement

> **MODERATE SEVERITY**: Phase 3 components make `fetch()` calls to Phase 2 endpoints. Testing with mocked fetch responses cannot catch data format mismatches, missing fields, or incorrect response structures.

Phase 3 testing must include:

1. **Component tests (mocked)**: Existing pattern using Vitest + @testing-library/svelte with mocked fetch responses. These test component rendering logic and UI interactions.

2. **Integration tests (real endpoints, NEW requirement)**: At least one test per feature that:
   - Starts a real backend server (or uses a test fixture server)
   - Makes actual API calls to Phase 2 endpoints
   - Verifies the component correctly renders the real response data
   - Tests graceful degradation when endpoints return errors or unexpected data

3. **Cross-phase contract tests (NEW requirement)**: Verify that the TypeScript interfaces declared in Phase 3 (`AgentDetailData`, `SkillDetailView`) match the actual JSON response structure from Phase 2 endpoints. This can be automated with a script that fetches the API response and validates it against the TypeScript interface (e.g., using `zod` schema validation or a simple structural check).

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Sub-Phase Ordering](#2-sub-phase-ordering)
3. [Feature 1: Agent Detail Panel with Progressive Disclosure](#3-feature-1-agent-detail-panel)
4. [Feature 2: Skill Detail Panel with Progressive Disclosure](#4-feature-2-skill-detail-panel)
5. [Feature 3: Filter Dropdowns](#5-feature-3-filter-dropdowns)
6. [Feature 4: Version Mismatch Detection](#6-feature-4-version-mismatch-detection)
7. [Feature 5: Agent Collaboration Links](#7-feature-5-agent-collaboration-links)
8. [Feature 6: Merge Skill Links into Detail Panels](#8-feature-6-merge-skill-links-into-detail-panels)
9. [Feature 7: Search Enhancements](#9-feature-7-search-enhancements)
10. [Component Architecture](#10-component-architecture)
11. [State Management Approach](#11-state-management-approach)
12. [Accessibility Considerations](#12-accessibility-considerations)
13. [Performance Targets](#13-performance-targets)
14. [Testing Strategy](#14-testing-strategy)
15. [Rollback Plan](#15-rollback-plan)
16. [Risk Assessment](#16-risk-assessment)
17. [Deferred Features](#17-deferred-features)

---

## 1. Executive Summary

Phase 3 builds rich interactive features on top of the data pipeline established in Phases 1-2. The core deliverables are:

- **Progressive-disclosure detail panels** for agents and skills replacing the current sparse right-panel detail view
- **Filter dropdowns** enabling category/toolchain/status filtering alongside text search
- **Version mismatch detection** alerting users when deployed versions differ from latest available
- **Agent collaboration links** showing handoff relationships as clickable text (78% of agents have handoff_agents)
- **Skill links integration** into detail panels, replacing the standalone Skill Links tab
- **Search enhancements** with multi-field search and result highlighting

> **[REVISED]** Removed from scope: (1) Full collaboration graph visualization (replaced with simpler related-agents list — R5), (2) Virtual scrolling (unnecessary for ~200 items — R6). These are documented in [Deferred Features](#17-deferred-features).

### Key Design Principles

1. **Progressive disclosure**: List view shows 5-6 fields; detail panel shows 10-12; expandable sections show everything else
2. **Graceful degradation**: Every field is optional with sensible fallbacks; the UI never shows empty/broken sections
3. **Lazy loading**: Detail panel sections load on demand (user click), not on initial list render
4. **Svelte 5 Runes**: All new components use `$state`, `$derived`, `$effect`, `$props` - no legacy Svelte 4 patterns
5. **Existing patterns**: Reuse established Badge, Modal, SearchInput, ConfirmDialog components

### Phase 1/2 Prerequisites

> **[REVISED]** Fixed prerequisites to match what Phase 2 actually provides. Removed agent deployment index requirement (R1). Fixed deployment index filename (R2).

| Prerequisite | Phase | Status | Why Needed |
|---|---|---|---|
| `AvailableSkill` interface expanded (10 new fields) | Phase 1 | Required | Skill detail panel needs version, toolchain, tags, tokens, etc. |
| Category grouping in agents list | Phase 1 | Required | Filter dropdowns build on this grouping |
| Toolchain grouping in skills list | Phase 1 | Required | Filter dropdowns build on this grouping |
| Sort controls | Phase 1 | Required | Filter UI extends the sort/filter bar |
| Deployed agents endpoint enriched (description, category, color, tags, skills_count, network_access, resource_tier) | Phase 2 | Required | Agent detail panel needs these fields |
| Deployed skills enriched with manifest data (version, toolchain, tags, tokens) | Phase 2 | Required | Skill detail panel needs consistent data |
| Agent detail endpoint (`GET /api/config/agents/{name}/detail`) | Phase 2 | Required | Lazy-loaded detail sections (expertise, skills, dependencies, handoff) |
| Skill detail endpoint (`GET /api/config/skills/{name}/detail`) | Phase 2 | Required | Lazy-loaded "when to use", agent usage data |
| Agent color field in available endpoint | Phase 2 | Required | Color dot in agent list and detail |
| Skill-links data accessible from detail endpoints | Phase 2 | Required | "Used By" / "Skills" sections in detail panels |
| Agent deployment status via filesystem presence | Phase 2 | Required | `is_deployed` cross-reference (NO deployment index file needed) |

**Removed prerequisites:**
- ~~Agent deployment index (`.claude/agents/.deployment_index.json`)~~ — Agents use filesystem presence check; no index file exists or is needed (see Phase 2 "Agent Deployment Status Strategy" section)

> **Verification Amendment (VP-1-DEPLOY)**: The prerequisites above are not merely "nice to have" — they are hard blockers. Phase 3 features will produce 404 errors and empty sections without them. Before starting Phase 3 implementation, verify ALL Phase 2 endpoints are deployed and returning expected data. See the "Verification Amendments" section at the top of this document for the specific failure modes.
>
> **Verification Amendment (VP-1-SEC)**: The Phase 2 detail endpoints (`GET /api/config/agents/{name}/detail`, `GET /api/config/skills/{name}/detail`) MUST include path traversal validation via `validate_safe_name()` before Phase 3 sends user-derived names to them. This was identified as a HIGH severity issue in VP-1 and has been addressed in the Phase 2 plan amendments.

---

## 2. Sub-Phase Ordering

Phase 3 is divided into three sub-phases based on dependency chains and incremental value delivery:

> **[REVISED]** Reduced from 4 sub-phases to 3. Former sub-phase 3D (Performance & Polish with virtual scrolling) removed. Virtual scrolling deferred to future optimization. Search enhancements moved to 3B.

### Sub-Phase 3A: Detail Panel Foundation (Est. Complexity: Large)
Build the core detail panel components and collapsible section primitives.

| Order | Feature | Depends On |
|---|---|---|
| 3A.1 | CollapsibleSection shared component | None |
| 3A.2 | MetadataGrid shared component | None |
| 3A.3 | Agent detail panel (basic sections) | 3A.1, 3A.2, Phase 2 agent detail endpoint |
| 3A.4 | Skill detail panel (basic sections) | 3A.1, 3A.2, Phase 2 skill enrichment |

### Sub-Phase 3B: Filtering, Search & Version Detection (Est. Complexity: Medium)
Add filter dropdowns, enhanced search, and version mismatch detection.

| Order | Feature | Depends On |
|---|---|---|
| 3B.1 | FilterDropdown shared component | None |
| 3B.2 | Agent filter bar (category, status, resource tier) | 3B.1, Phase 1 category grouping |
| 3B.3 | Skill filter bar (toolchain, status) | 3B.1, Phase 1 toolchain grouping |
| 3B.4 | Multi-field search with highlighting | 3B.2, 3B.3 |
| 3B.5 | Version mismatch detection badges | 3A.3, 3A.4 |

### Sub-Phase 3C: Relationship Integration (Est. Complexity: Medium)
Integrate skill links into detail panels and add agent collaboration links.

| Order | Feature | Depends On |
|---|---|---|
| 3C.1 | Skill chips with deploy status in agent detail | 3A.3, Phase 2 skill-links integration |
| 3C.2 | "Used By" agent list in skill detail | 3A.4, Phase 2 skill-links integration |
| 3C.3 | Agent collaboration links (handoff_agents as clickable text) | 3A.3, Phase 2 agent detail endpoint |
| 3C.4 | Skill Links tab deprecation / redirect | 3C.1, 3C.2 |

---

## 3. Feature 1: Agent Detail Panel

### What
Replace the current sparse agent detail view (right panel of ConfigView) with a rich progressive-disclosure panel showing overview, expertise, skills, dependencies, collaborators, and constraints in expandable sections.

### Where

**New files:**
- `dashboard-svelte/src/lib/components/config/AgentDetailPanel.svelte` - Main agent detail component
- `dashboard-svelte/src/lib/components/shared/CollapsibleSection.svelte` - Reusable expandable section
- `dashboard-svelte/src/lib/components/shared/MetadataGrid.svelte` - Key-value grid display
- `dashboard-svelte/src/lib/components/shared/ColorDot.svelte` - Agent color indicator
- `dashboard-svelte/src/lib/components/config/SkillChipWithStatus.svelte` - Skill chip showing deploy status

**Modified files:**
- `dashboard-svelte/src/lib/components/config/ConfigView.svelte` - Replace inline agent detail with `AgentDetailPanel`
- `dashboard-svelte/src/lib/stores/config.svelte.ts` - Add `AgentDetail` interface, `fetchAgentDetail()` function
- `dashboard-svelte/src/lib/components/config/AgentsList.svelte` - Emit richer selection events

### How

#### 3.1 Data Flow

```
User clicks agent in list
  -> ConfigView.selectedAgent = agent
  -> AgentDetailPanel receives agent prop
  -> $effect: fetch GET /api/config/agents/{name}/detail (lazy load)
  -> Merge list-level data + detail data into unified view
  -> Render sections with progressive disclosure
```

#### 3.2 TypeScript Interfaces

```typescript
// New interface for agent detail endpoint response
interface AgentDetailData {
  name: string;
  description: string;
  version: string;
  category: string;
  color?: string;  // Optional, default 'gray'
  agent_type: string;
  resource_tier: string;
  network_access: boolean;
  temperature?: number;
  timeout?: number;
  tags: string[];
  skills: string[];  // Skill names referenced by this agent
  dependencies: {
    python?: string[];
    system?: string[];
    nodejs?: string[];
    npm?: string[];
  };
  knowledge?: {
    domain_expertise?: string[];
    constraints?: string[];
  };
  handoff_agents?: string[];  // Agent names this agent hands off to
  source?: string;
  source_url?: string;
}
```

#### 3.3 Component Design: `AgentDetailPanel.svelte`

```typescript
interface Props {
  agent: DeployedAgent | AvailableAgent;  // List-level data (already loaded)
}
```

**Internal state:**
```typescript
let detailData = $state<AgentDetailData | null>(null);
let detailLoading = $state(false);
let detailError = $state<string | null>(null);
let expandedSections = $state<Set<string>>(new Set());
```

**Lazy loading with $effect:**
```typescript
$effect(() => {
  const agentName = isDeployedAgent(agent) ? agent.name : agent.agent_id;
  detailLoading = true;
  detailError = null;
  fetchAgentDetail(agentName)
    .then(data => { detailData = data; })
    .catch(err => { detailError = err.message; })
    .finally(() => { detailLoading = false; });
});
```

#### 3.4 Panel Layout

```
+--------------------------------------------------+
| [color-dot]  Agent Name                    v2.3.0 |
| ================================================= |
|                                                    |
| Full description text, wrapping as needed.         |
| Can be multiple lines.                             |
|                                                    |
| +----------+----------+------------+               |
| | Category | Tier     | Network    |               |
| | engineer | standard | Yes [icon] |               |
| +----------+----------+------------+               |
|                                                    |
| > Expertise (N items)                [collapsed]   |
|   - Python 3.12-3.13 features                      |
|   - Service-oriented architecture                   |
|   - Async/await patterns                            |
|                                                    |
| > Skills (N linked)                  [collapsed]   |
|   [pytest +] [mypy +] [pydantic -] [git-workflow +]|
|   "2 required skills not deployed" [warning]        |
|                                                    |
| > Dependencies                       [collapsed]   |
|   Python: black, isort, mypy, pytest                |
|   System: python3.12+, git                          |
|                                                    |
| > Collaborates With (N agents)       [collapsed]   |
|   -> qa (click to view)                             |
|   -> security (click to view)                       |
|   -> data_engineer (click to view)                  |
|                                                    |
| > Constraints (N items)              [collapsed]   |
|   - Maximum 5-10 test files per session             |
|   - Skip files >500KB unless critical               |
|                                                    |
| ──────────────────────────────────                  |
| Source: bobmatnyc/claude-mpm-agents                 |
| Temperature: 0.2 (focused)                          |
| Timeout: 900s                                       |
|                                                    |
|           [Deploy]  or  [Undeploy]                  |
+--------------------------------------------------+
```

#### 3.5 Section Visibility Defaults

| Section | Default State | Rationale |
|---|---|---|
| Header (name, version, color dot) | Always visible | Identity |
| Description | Always visible | Core understanding |
| MetadataGrid (category, tier, network) | Always visible | Quick assessment |
| Expertise | **Collapsed** | Detail-level; 5-23 items can be long |
| Skills | **Collapsed** | Needs deploy status cross-reference; can be 30+ items |
| Dependencies | **Collapsed** | Setup-specific, not always relevant |
| Collaborates With | **Collapsed** | Relationship context, not decision-critical |
| Constraints | **Collapsed** | Limitations, reviewed after deciding to use |
| Footer (source, temperature, timeout) | Always visible | Reference metadata |
| Deploy/Undeploy button | Always visible | Primary action |

#### 3.6 Fields NOT Shown (Per Research)

| Field | Why Excluded |
|---|---|
| `max_tokens` | Users don't understand what 4096 vs 16384 means |
| `cpu_limit` | No user-controllable behavior |
| `memory_limit` | Noise unless deploying to resource-constrained environments |
| `schema_version` | Internal compatibility |
| `template_version` + `template_changelog` | Developer-facing, meaningless for deployment decisions |
| `memory_routing` | Internal system plumbing |
| `interactions.output_format` | Implementation detail |

#### 3.7 Temperature Semantic Labels

```typescript
function temperatureLabel(temp: number): string {
  if (temp === 0) return 'precise';
  if (temp <= 0.3) return 'focused';
  if (temp <= 0.7) return 'balanced';
  return 'creative';
}
// Display: "Temperature: 0.2 (focused)"
```

### Why
- Currently deployed agents show only 7 fields — users can't understand what an agent does
- Rich metadata exists in frontmatter but is invisible to UI users
- Progressive disclosure prevents information overload while making everything accessible

### Edge Cases

| Edge Case | Handling |
|---|---|
| Agent without `color` (3 agents) | Default to `gray` dot via `ColorDot` component |
| Agent without `skills` list | Show "No skills defined" text in collapsed section |
| Agent with 31 tags (Research agent) | Show first 3 tags + "+N more" in list; show all in detail |
| Agent with no `knowledge.domain_expertise` | Hide Expertise section entirely |
| Agent with no `handoff_agents` | Hide Collaborates With section entirely |
| Detail endpoint returns 404 | Show fallback with list-level data only; info banner: "Extended details unavailable" |
| Detail endpoint loading | Show skeleton loading for expandable sections; header renders immediately from list data |

### Acceptance Criteria

> **[REVISED]** Strengthened from vague "Panel renders agent details" to specific, testable criteria.

- [ ] Clicking an agent renders the detail panel header (name, color dot, version) within 200ms using list-level data
- [ ] Detail data lazy-loads within 500ms of click and populates expandable sections
- [ ] Color dot renders the agent's `color` field value as a CSS background; defaults to `#9CA3AF` (gray-400) when color is missing or empty
- [ ] Description text wraps correctly for descriptions up to 500 characters without horizontal overflow
- [ ] MetadataGrid shows exactly 3 cells: category, resource tier, network access (with globe/lock icon)
- [ ] Each CollapsibleSection toggles on click AND on keyboard Enter/Space
- [ ] CollapsibleSection has `aria-expanded` attribute that updates on toggle
- [ ] Skills section shows green checkmark for deployed skills, red X for not-deployed
- [ ] Warning text "N required skills not deployed" appears when applicable, with amber text color
- [ ] Collaborates With section shows handoff agent names as clickable links that navigate to that agent's detail
- [ ] Footer shows temperature with semantic label (e.g., "0.2 (focused)")
- [ ] Deploy/Undeploy button works identically to current implementation
- [ ] When detail endpoint returns 404, panel shows list-level data with info banner

### Dependencies
- Phase 2: Agent detail endpoint (`GET /api/config/agents/{name}/detail`)
- Phase 2: Enriched deployed agents endpoint (description, category, color)
- Phase 2: Skill-links integration for skills section

### Estimated Complexity: **Large**

---

## 4. Feature 2: Skill Detail Panel

### What
Replace the current sparse skill detail view with a rich panel showing overview, "when to use", linked agents, dependencies, related skills, and content metadata.

### Where

**New files:**
- `dashboard-svelte/src/lib/components/config/SkillDetailPanel.svelte` - Main skill detail component

**Modified files:**
- `dashboard-svelte/src/lib/components/config/ConfigView.svelte` - Replace inline skill detail with `SkillDetailPanel`
- `dashboard-svelte/src/lib/stores/config.svelte.ts` - Add `SkillDetailData` interface, `fetchSkillDetail()` function

### How

#### 4.1 Data Flow

```
User clicks skill in list
  -> ConfigView.selectedSkill = skill
  -> SkillDetailPanel receives skill prop
  -> Merge available/deployed data (already loaded from list)
  -> Optionally fetch /api/config/skills/{name}/detail for "when to use" and "used by"
  -> Render sections
```

#### 4.2 TypeScript Interface

```typescript
interface SkillDetailView {
  // From AvailableSkill (Phase 1 expanded interface)
  name: string;
  description: string;
  version: string;
  category: string;
  toolchain: string | null;
  framework: string | null;
  tags: string[];
  entry_point_tokens: number;
  full_tokens: number;
  requires: string[];
  author: string;
  updated: string;
  source_path: string;
  is_deployed: boolean;

  // From DeployedSkill (if deployed - Phase 2 enrichment)
  collection?: string;
  deploy_mode?: 'agent_referenced' | 'user_defined';
  deploy_date?: string;
  is_user_requested?: boolean;

  // Lazy-loaded from skill detail endpoint
  when_to_use?: string;
  summary?: string;
  used_by_agents?: string[];
  agent_count?: number;
}
```

#### 4.3 Panel Layout

```
+--------------------------------------------------+
| skill-name                                 v1.0.0 |
| ================================================= |
|                                                    |
| Description text from manifest or SKILL.md         |
| frontmatter, wrapping as needed.                   |
|                                                    |
| +----------+----------+------------+               |
| | Toolchain| Tokens   | Updated    |               |
| | ai       | 10,191   | 2025-12-31 |               |
| +----------+----------+------------+               |
|                                                    |
| > When to Use                        [collapsed]   |
|   "When building RAG pipelines, classification     |
|    systems, or optimizing prompt performance"       |
|                                                    |
| > Used By (5 agents)                 [collapsed]   |
|   python-engineer, research, java-engineer,         |
|   data-engineer, mpm-skills-manager                 |
|                                                    |
| > Dependencies                       [collapsed]   |
|   Requires: systematic-debugging                    |
|                                                    |
| ──────────────────────────────────                  |
| Author: claude-mpm-skills                           |
| Source: toolchains/ai/frameworks/dspy/SKILL.md       |
| Deploy mode: agent_referenced                        |
|                                                    |
|           [Deploy]  or  [Undeploy]                  |
+--------------------------------------------------+
```

#### 4.4 Section Visibility Defaults

| Section | Default State | Rationale |
|---|---|---|
| Header (name, version) | Always visible | Identity |
| Description | Always visible | Core understanding |
| MetadataGrid (toolchain, tokens, updated) | Always visible | Quick assessment |
| When to Use | **Collapsed** | Trigger condition, useful but secondary |
| Used By (agents) | **Collapsed** | Relationship data, lazy-loaded |
| Dependencies | **Collapsed** | Only shown if `requires` is non-empty |
| Footer (author, source, deploy mode) | Always visible | Reference metadata |

### Why
- Currently deployed skills show only sparse data
- Users need "when to use" context and agent relationship data to make deployment decisions

### Edge Cases

| Edge Case | Handling |
|---|---|
| Skill without description | Use `when_to_use` as fallback, then "No description available" |
| Skill with 0 or missing `full_tokens` | Hide token count from MetadataGrid |
| Skill with empty `requires` array | Hide Dependencies section entirely |
| Skill not in available list (deployed but source removed) | Show deployed data only; info banner: "Source not available" |
| System skill (CORE_SKILLS member) | Show lock icon + tooltip explaining protection |
| Deployed skill not in manifest | Show "custom/unknown source" indicator |

### Acceptance Criteria

> **[REVISED]** Strengthened from vague criteria to specific, testable ones.

- [ ] Clicking a skill renders the detail panel header (name, version badge) within 200ms using list-level data
- [ ] MetadataGrid shows toolchain (or "Universal"), token count formatted as "N.Nk" for 1000+, and updated date
- [ ] "When to Use" section appears only when `when_to_use` is non-empty; text wraps within panel width
- [ ] "Used By" section shows agent count in header and lists agent names as clickable links
- [ ] Clicking an agent name in "Used By" navigates to that agent's detail panel
- [ ] Dependencies section only appears when `requires` array has 1+ items
- [ ] System skills show a lock icon (SVG) with `title` attribute explaining the protection
- [ ] Source path renders as readable text with `break-all` for long paths
- [ ] Deploy/Undeploy button respects system protection rules
- [ ] CollapsibleSection has `aria-expanded` and responds to Enter/Space keyboard events

### Dependencies
- Phase 1: Expanded `AvailableSkill` interface
- Phase 2: Enriched deployed skills
- Phase 2: Skill detail endpoint

### Estimated Complexity: **Medium**

---

## 5. Feature 3: Filter Dropdowns

### What
Add filter dropdowns alongside the existing text search for both agent and skill lists.

### Where

**New files:**
- `dashboard-svelte/src/lib/components/shared/FilterDropdown.svelte`
- `dashboard-svelte/src/lib/components/shared/FilterBar.svelte`
- `dashboard-svelte/src/lib/components/config/AgentFilterBar.svelte`
- `dashboard-svelte/src/lib/components/config/SkillFilterBar.svelte`

**Modified files:**
- `dashboard-svelte/src/lib/components/config/AgentsList.svelte`
- `dashboard-svelte/src/lib/components/config/SkillsList.svelte`

### How

#### 5.1 FilterDropdown Component

```typescript
interface FilterOption {
  value: string;
  label: string;
  count?: number;
}

interface Props {
  label: string;
  options: FilterOption[];
  selected: string[];  // $bindable
  placeholder?: string;
  multiple?: boolean;
}
```

#### 5.2 Agent Filters

| Filter | Source Field | Options (Dynamic) | Default |
|---|---|---|---|
| Category | `category` | engineering, quality, operations, research, specialized, claude-mpm | All |
| Status | `is_deployed` cross-reference | Deployed, Available (not deployed) | All |
| Resource Tier | `resource_tier` | basic, standard, intensive, high | All |

**Filters NOT included:**
- Tag filter: 100+ unique tags, dropdown unusable. Tags participate in free-text search
- Network Access: binary filter with limited usefulness; can be added later if requested

#### 5.3 Skill Filters

| Filter | Source Field | Options (Dynamic) | Default |
|---|---|---|---|
| Toolchain | `toolchain` | Universal (null), ai, python, javascript, etc. (15 values) | All |
| Status | `is_deployed` | Deployed, Available (not deployed) | All |

#### 5.4 Filter Bar Layout

```
+----------------------------------------------------------------+
| [Search...      ]  [Category v]  [Status v]  [Tier v]  [Clear] |
|                    Active: 2 filters                            |
+----------------------------------------------------------------+
```

#### 5.5 Filter State Management

```typescript
let filters = $state({
  search: '',
  category: [] as string[],
  status: [] as string[],
  resourceTier: [] as string[],
});

let activeFilterCount = $derived(
  filters.category.length +
  filters.status.length +
  filters.resourceTier.length +
  (filters.search ? 1 : 0)
);

let filteredAgents = $derived(
  allAgents.filter(agent => {
    if (filters.search && !matchesSearch(agent, filters.search)) return false;
    if (filters.category.length && !filters.category.includes(agent.category)) return false;
    if (filters.status.length) {
      const isDeployed = agent.is_deployed || isDeployedAgent(agent);
      if (!filters.status.includes(isDeployed ? 'deployed' : 'available')) return false;
    }
    if (filters.resourceTier.length && !filters.resourceTier.includes(agent.resource_tier)) return false;
    return true;
  })
);
```

### Why
- Currently only text search is available, inadequate for 45+ agents and 156+ skills
- Category and toolchain are the only useful filter dimensions (confirmed by research)
- Status filter ("show me what I have" vs "what's available") is the most common user need

### Edge Cases

| Edge Case | Handling |
|---|---|
| Filter yields zero results | Show empty state: "No agents match current filters" with "Clear filters" button |
| All options selected = no filter | Treat as "no filter active" |
| Category not available for deployed agents (pre-Phase 2) | Hide category filter, show only status + search |
| Toolchain is null for universal skills | Map to "Universal" option |
| Panel too narrow for all filters inline | Filters wrap to next row; search stays on top |

### Acceptance Criteria

- [ ] Agent list has filter dropdowns for: Category, Status, Resource Tier
- [ ] Skill list has filter dropdowns for: Toolchain, Status
- [ ] Clicking a filter button opens a dropdown with checkbox options and current counts per option
- [ ] Selecting a filter immediately updates the list without an "Apply" button
- [ ] Active filter count badge (e.g., "(2)") appears on filter button when selections are made
- [ ] "Clear all" button resets all filters and search text to defaults
- [ ] Empty state message shown when no items match, with "Clear filters" action
- [ ] Filter state persists within a session (switching tabs and back retains filters)
- [ ] Keyboard: Tab between filters, Enter/Space opens dropdown, Escape closes dropdown
- [ ] Filter dropdown closes when clicking outside of it

### Dependencies
- Phase 1: Category grouping (agents), toolchain grouping (skills)
- Phase 2: Deployed agent enrichment (for resource_tier filter)

### Estimated Complexity: **Medium**

---

## 6. Feature 4: Version Mismatch Detection

### What
Compare deployed agent/skill versions against latest available versions and show visual indicators when an update is available.

### Where

**New files:**
- `dashboard-svelte/src/lib/components/shared/VersionBadge.svelte`
- `dashboard-svelte/src/lib/utils/version.ts`

**Modified files:**
- `AgentsList.svelte`, `SkillsList.svelte`, `AgentDetailPanel.svelte`, `SkillDetailPanel.svelte`

### How

#### 6.1 Version Comparison Logic

```typescript
function compareVersions(deployed: string, available: string): 'current' | 'outdated' | 'unknown' {
  if (!deployed || !available) return 'unknown';
  const [dMajor, dMinor, dPatch] = deployed.split('.').map(Number);
  const [aMajor, aMinor, aPatch] = available.split('.').map(Number);

  if (isNaN(dMajor) || isNaN(aMajor)) return 'unknown';
  if (dMajor === aMajor && dMinor === aMinor && dPatch === aPatch) return 'current';
  if (dMajor < aMajor || (dMajor === aMajor && dMinor < aMinor) ||
      (dMajor === aMajor && dMinor === aMinor && dPatch < aPatch)) return 'outdated';
  return 'current';
}
```

#### 6.2 VersionBadge Component

```typescript
interface Props {
  deployedVersion: string;
  availableVersion?: string;
  status: 'current' | 'outdated' | 'unknown';
}
```

- `current`: Green badge: `v2.3.0`
- `outdated`: Amber badge with arrow: `v2.1.0 → v2.3.0`
- `unknown`: Gray badge: `v2.1.0`

### Why
- Users have no way to know when deployed copies are outdated
- Version mismatch detection directly addresses "stale data risk"

### Edge Cases

| Edge Case | Handling |
|---|---|
| Deployed agent not in available list | Gray "unknown" status |
| Version strings not semver (e.g., "latest") | `isNaN` check → "unknown" status |
| Deployed version newer than available | Treat as "current" |
| Skill name mismatch (deployed uses flattened name) | Use suffix matching |
| All items are current | No mismatch UI shown (clean state) |

### Acceptance Criteria

- [ ] Deployed agents with lower version than available show amber VersionBadge in list
- [ ] Deployed skills with lower version than available show amber VersionBadge in list
- [ ] VersionBadge shows "vX.Y.Z → vA.B.C" format for outdated items
- [ ] VersionBadge has `title` attribute with "Update available: vX.Y.Z → vA.B.C"
- [ ] Items without available counterparts show neutral gray version badge
- [ ] Version comparison handles semver correctly: 2.1.0 < 2.3.0 < 3.0.0
- [ ] Non-semver version strings (e.g., "latest") show gray "unknown" badge without errors
- [ ] Section header shows "N updates available" count when > 0

### Dependencies
- Phase 1: Version shown in skill list items
- Phase 2: Deployed agents have version in enriched endpoint
- Phase 2: Deployed skills have version from manifest cross-reference

### Estimated Complexity: **Small**

---

## 7. Feature 5: Agent Collaboration Links

> **[REVISED]** Previously proposed as "Agent Collaboration Graph" with full graph visualization. Replaced with simpler "Related Agents" clickable text list per devil's advocate recommendation (R5). The full graph was estimated at 45 nodes × ~135 edges — unreadable without a graph layout library, and the library dependency + maintenance burden is unjustified for this use case.

### What
Show agent handoff relationships as clickable text links in the agent detail panel's "Collaborates With" section. 78% of agents (39/50) have `handoff_agents` data.

### Where

**Modified files:**
- `dashboard-svelte/src/lib/components/config/AgentDetailPanel.svelte` - "Collaborates With" section

### How

#### 7.1 Design: Clickable Text Links, Not Graph

In the "Collaborates With" CollapsibleSection of the agent detail panel:

```
> Collaborates With (5 connections)

  Hands off to:
    -> qa (click to view)
    -> security (click to view)
    -> data_engineer (click to view)

  Receives work from:
    <- research (click to view)
    <- product-owner (click to view)
```

Clicking an agent name calls `onSelect(targetAgent)` which updates ConfigView's selection.

#### 7.2 Bidirectional Data (Progressive)

```typescript
let handoffGraph = $derived(() => {
  const graph = new Map<string, { handsOffTo: string[], receivesFrom: string[] }>();

  for (const [name, detail] of agentDetailCache) {
    if (!graph.has(name)) graph.set(name, { handsOffTo: [], receivesFrom: [] });
    for (const target of detail.handoff_agents ?? []) {
      graph.get(name)!.handsOffTo.push(target);
      if (!graph.has(target)) graph.set(target, { handsOffTo: [], receivesFrom: [] });
      graph.get(target)!.receivesFrom.push(name);
    }
  }
  return graph;
});
```

"Receives from" data populates progressively as users browse agents and detail data gets cached.

#### 7.3 Agent Detail Cache

```typescript
let agentDetailCache = $state(new Map<string, AgentDetailData>());

async function fetchAgentDetail(name: string): Promise<AgentDetailData> {
  if (agentDetailCache.has(name)) return agentDetailCache.get(name)!;
  const data = await fetchJSON(`${API_BASE}/agents/${name}/detail`);
  agentDetailCache.set(name, data);
  return data;
}
```

### Why
- 78% of agents have handoff data — valuable relationship information
- Full graph visualization rejected: 45 nodes × ~135 edges is unreadable, requires graph library, hard to maintain/test
- Clickable text links provide the same navigation at 10% of implementation cost
- If users request a visual graph later, it can be added as a separate feature with proper UX research

### Edge Cases

| Edge Case | Handling |
|---|---|
| Agent with no handoff_agents (22% of agents) | Hide "Collaborates With" section entirely |
| Handoff target not in deployed/available list | Show name as plain text (not clickable), gray color |
| Circular handoffs (A -> B -> A) | Display normally; navigation follows clicks |
| Agent hands off to itself | Filter self-references from display |
| Bidirectional data not yet loaded | Show "Hands off to" only; "Receives from" populates as cache builds |

### Acceptance Criteria

- [ ] "Collaborates With" section appears when `handoff_agents` has 1+ entries
- [ ] Section header shows connection count: "Collaborates With (N connections)"
- [ ] "Hands off to" subsection lists target agents with `->` prefix
- [ ] Agent names that exist in deployed/available list are clickable (blue, underline on hover)
- [ ] Clicking a handoff agent name navigates to that agent's detail panel within 200ms
- [ ] Agent names not found in any list render as plain gray text (not clickable)
- [ ] Self-references (agent hands off to itself) are filtered out
- [ ] Section is hidden entirely when `handoff_agents` is empty or undefined

### Dependencies
- Phase 2: Agent detail endpoint returning `handoff_agents`
- Sub-Phase 3A: Agent detail panel with CollapsibleSection

### Estimated Complexity: **Small-Medium**

> **[REVISED]** Reduced from "Medium-Large" to "Small-Medium" since graph visualization was removed.

---

## 8. Feature 6: Merge Skill Links into Detail Panels

### What
Replace the standalone "Skill Links" tab with integrated bidirectional views: agents show their linked skills, skills show their referencing agents.

### Where

**Modified files:**
- `AgentDetailPanel.svelte` - Add "Skills" section with deploy status
- `SkillDetailPanel.svelte` - Add "Used By" section
- `ConfigView.svelte` - Deprecate Skill Links tab
- `skillLinks.svelte.ts` - Reuse existing store

### How

#### 8.1 Agent Detail: Skills Section

```
> Skills (18 linked)

  Required (frontmatter):
    [pytest +] [mypy +] [pydantic -] [git-workflow +]

  Inferred:
    [software-patterns +] [dispatching-parallel-agents +]

  + = deployed    - = not deployed
  ! 2 required skills not deployed
```

#### 8.2 Skill Detail: Used By Section

```
> Used By (12 agents)

  python-engineer, java-engineer, rust-engineer, ...
```

Agent names are clickable, navigating to that agent's detail panel.

#### 8.3 Skill Links Tab Deprecation

Keep tab for one release cycle with notice: "Skill links are now shown in agent and skill detail panels. This tab will be removed in a future update."

### Why
- The Skill Links tab is disconnected from context — users must switch tabs to see relationships
- Integrated views provide the same data with better context
- Missing skills warning helps users understand deployment gaps

### Edge Cases

| Edge Case | Handling |
|---|---|
| Agent with no skill links | "No skills linked" text |
| Skill used by 0 agents | "Not referenced by any agents" text |
| Agent with 30+ skills | Show first 10 with "Show all N" expand link |
| Skill-links API not available | Show loading spinner, then gracefully degrade |

### Acceptance Criteria

- [ ] Agent detail "Skills" section groups skills by link type (Required, Inferred, Content Marker, User Defined)
- [ ] Each skill shows green checkmark if deployed, red X if not deployed
- [ ] Warning text "N required skills not deployed" appears in amber when applicable
- [ ] Skill detail "Used By" section lists agent names as clickable links
- [ ] Clicking agent name navigates to that agent's detail panel
- [ ] Skill Links tab shows deprecation notice banner at top
- [ ] Existing Skill Links tab continues to function during transition
- [ ] Skill chips use `SkillChipWithStatus` component with deploy indicator

### Dependencies
- Phase 2: Skill-links data accessible from detail views
- Sub-Phase 3A: Detail panels with CollapsibleSection

### Estimated Complexity: **Medium**

---

## 9. Feature 7: Search Enhancements

> **[REVISED]** Previously Feature 8. Renumbered after virtual scrolling removal.

### What
Enhance search to match across multiple fields (name + description + tags), highlight matching text in results, and track recent searches.

### Where

**New files:**
- `dashboard-svelte/src/lib/components/shared/HighlightedText.svelte`

**Modified files:**
- `AgentsList.svelte`, `SkillsList.svelte`, `SearchInput.svelte`

### How

#### 9.1 Multi-Field Search

```typescript
function matchesSearch(agent: DeployedAgent | AvailableAgent, query: string): boolean {
  const q = query.toLowerCase();
  return agent.name.toLowerCase().includes(q) ||
         (agent.description ?? '').toLowerCase().includes(q) ||
         (agent.tags ?? []).join(' ').toLowerCase().includes(q) ||
         (agent.category ?? '').toLowerCase().includes(q);
}
```

#### 9.2 HighlightedText Component

```typescript
interface Props {
  text: string;
  query: string;
  maxLength?: number;
}
```

```html
<span>
  {#each segments as segment}
    {#if segment.highlight}
      <mark class="bg-yellow-200 dark:bg-yellow-500/30 text-inherit rounded px-0.5">
        {segment.text}
      </mark>
    {:else}
      {segment.text}
    {/if}
  {/each}
</span>
```

### Why
- Current search only matches name + description, missing tags and category
- Highlighting shows WHY an item matched

### Edge Cases

| Edge Case | Handling |
|---|---|
| Special regex characters in search (e.g., "c++") | Escape regex special characters |
| Empty search query | Show all items, no highlighting |
| Search matches in tag but not name | Item appears; tag badge highlighted |

### Acceptance Criteria

- [ ] Search matches across name, description, tags, category (agents) / toolchain (skills)
- [ ] Matching text segments highlighted with yellow background (`bg-yellow-200 dark:bg-yellow-500/30`)
- [ ] Highlighting works in both light and dark mode with sufficient contrast
- [ ] Special characters in search query (e.g., `c++`, `$state`) don't cause regex errors
- [ ] No visible lag when highlighting across 156+ skill items

### Dependencies
- Sub-Phase 3B: Filter bar integration

### Estimated Complexity: **Small**

---

## 10. Component Architecture

### New Shared Components

| Component | Purpose | Est. Lines |
|---|---|---|
| `CollapsibleSection.svelte` | Expandable section with header, count, content slot | ~60 |
| `MetadataGrid.svelte` | 2-3 column key-value grid | ~40 |
| `ColorDot.svelte` | Small colored circle indicator | ~25 |
| `FilterDropdown.svelte` | Select dropdown with counts | ~120 |
| `FilterBar.svelte` | Container for search + filter dropdowns | ~50 |
| `VersionBadge.svelte` | Version display with update status | ~45 |
| `HighlightedText.svelte` | Text with search highlighting | ~40 |

### New Config Components

| Component | Purpose | Est. Lines |
|---|---|---|
| `AgentDetailPanel.svelte` | Rich agent detail view | ~250 |
| `SkillDetailPanel.svelte` | Rich skill detail view | ~200 |
| `AgentFilterBar.svelte` | Agent-specific filter configuration | ~80 |
| `SkillFilterBar.svelte` | Skill-specific filter configuration | ~70 |
| `SkillChipWithStatus.svelte` | Skill chip with deployment status | ~35 |

### Component Dependency Tree

```
ConfigView.svelte
  +-- AgentsList.svelte
  |   +-- *AgentFilterBar.svelte
  |   |   +-- SearchInput.svelte (enhanced*)
  |   |   +-- *FilterDropdown.svelte
  |   +-- *VersionBadge.svelte
  |   +-- *HighlightedText.svelte
  |   +-- Badge.svelte
  |   +-- ConfirmDialog.svelte
  |
  +-- SkillsList.svelte
  |   +-- *SkillFilterBar.svelte
  |   |   +-- SearchInput.svelte (enhanced*)
  |   |   +-- *FilterDropdown.svelte
  |   +-- *VersionBadge.svelte
  |   +-- *HighlightedText.svelte
  |   +-- Badge.svelte
  |   +-- ConfirmDialog.svelte
  |
  +-- *AgentDetailPanel.svelte (replaces inline agent detail)
  |   +-- *CollapsibleSection.svelte
  |   +-- *MetadataGrid.svelte
  |   +-- *ColorDot.svelte
  |   +-- *SkillChipWithStatus.svelte
  |   +-- *VersionBadge.svelte
  |   +-- Badge.svelte
  |
  +-- *SkillDetailPanel.svelte (replaces inline skill detail)
  |   +-- *CollapsibleSection.svelte
  |   +-- *MetadataGrid.svelte
  |   +-- *VersionBadge.svelte
  |   +-- Badge.svelte
  |
  +-- SkillLinksView.svelte (deprecated*, shows redirect notice)
  +-- SourcesList.svelte (unchanged)
  +-- ValidationPanel.svelte (unchanged)
```

**Total new code: ~1,015 lines estimated** (reduced from ~1,215 after removing VirtualList and AgentCollaborationView graph components)

---

## 11. State Management Approach

### Store Architecture

All new state uses Svelte 5 `$state` locally within components, with stores reserved for cross-component shared data.

#### New Store Additions (config.svelte.ts)

```typescript
export const agentDetailCache = writable<Map<string, AgentDetailData>>(new Map());

export async function fetchAgentDetail(name: string): Promise<AgentDetailData> {
  let cache: Map<string, AgentDetailData>;
  agentDetailCache.subscribe(v => { cache = v; })();

  if (cache.has(name)) return cache.get(name)!;

  const data = await fetchJSON(`${API_BASE}/agents/${encodeURIComponent(name)}/detail`);
  agentDetailCache.update(c => {
    const updated = new Map(c);
    updated.set(name, data);
    return updated;
  });
  return data;
}

function invalidateAgentDetailCache(name: string) {
  agentDetailCache.update(c => {
    const updated = new Map(c);
    updated.delete(name);
    return updated;
  });
}
```

### Filter State Persistence

```typescript
const FILTER_STATE_KEY = 'agent-filters';

$effect(() => {
  sessionStorage.setItem(FILTER_STATE_KEY, JSON.stringify(filters));
});

let filters = $state(
  JSON.parse(sessionStorage.getItem(FILTER_STATE_KEY) ?? '{}')
);
```

---

## 12. Accessibility Considerations

### Keyboard Navigation

| Component | Key | Action |
|---|---|---|
| CollapsibleSection | Enter / Space | Toggle expand/collapse |
| FilterDropdown | Enter / Space | Open/close dropdown |
| FilterDropdown | Arrow Down/Up | Navigate options |
| FilterDropdown | Escape | Close dropdown |
| SkillChipWithStatus | Enter / Space | Navigate to skill detail |
| SearchInput | Escape | Clear search |

### ARIA Attributes

```html
<!-- CollapsibleSection -->
<button role="button" aria-expanded={expanded} aria-controls="section-{id}">
  {title}
</button>
<div id="section-{id}" role="region" aria-labelledby="heading-{id}" aria-hidden={!expanded}>
  {@render children()}
</div>

<!-- FilterDropdown -->
<button aria-haspopup="listbox" aria-expanded={open}>{label}</button>
<ul role="listbox" aria-label="{label} filter options">
  <li role="option" aria-selected={selected}>...</li>
</ul>

<!-- VersionBadge -->
<span role="status" aria-label="Version {version}, {status === 'outdated' ? 'update available' : 'up to date'}">
```

---

## 13. Performance Targets

| Metric | Target | Measurement |
|---|---|---|
| List render (45 agents) | < 50ms | `performance.mark()` |
| List render (156 skills) | < 100ms | `performance.mark()` |
| Detail panel initial render | < 200ms (list-level data) | Time from click to first paint |
| Detail panel lazy load | < 500ms (detail endpoint response) | Network + render time |
| Filter change re-render | < 30ms | Time from filter selection to list update |
| Search debounce | 300ms (existing) | Delay before filtering starts |
| Memory: agent detail cache | < 5MB for 50 agents | `performance.memory` |
| Bundle size increase | < 12KB gzipped total for all new components | Build output analysis |

> **[REVISED]** Reduced bundle size target from 15KB to 12KB (removed VirtualList and graph components).

---

## 14. Testing Strategy

> **Verification Amendment (VP-1-TEST)**: The existing test patterns use mocked services which cannot catch data format mismatches between Phase 2 API responses and Phase 3 TypeScript interfaces. Phase 3 testing must include integration tests with real Phase 2 endpoints.

### Component Tests (Vitest + @testing-library/svelte — Mocked)

| Component | Test Cases |
|---|---|
| `CollapsibleSection` | Renders collapsed by default; expands on click; keyboard toggle; ARIA attributes update |
| `MetadataGrid` | Renders key-value pairs; handles missing values; responsive column count |
| `ColorDot` | Renders correct color class; defaults to gray for unknown/empty colors |
| `FilterDropdown` | Opens on click; selects options; shows counts; closes on Escape; multi-select |
| `VersionBadge` | Shows correct variant for current/outdated/unknown; tooltip content matches |
| `HighlightedText` | Highlights matching text; handles regex special chars; truncation |
| `AgentDetailPanel` | Renders all sections; lazy loads detail data; handles loading/error; section toggle |
| `SkillDetailPanel` | Renders all sections; merges available/deployed data; handles missing fields |

### Integration Tests (Mocked API — existing pattern)

| Scenario | Steps |
|---|---|
| Agent browsing flow | Click agent → detail panel → expand sections → click handoff agent → verify navigation |
| Skill browsing flow | Click skill → detail panel → verify "Used By" → click agent link |
| Filter + search | Set category filter → apply search → verify combined → clear all → verify reset |
| Version mismatch | Verify amber badge on outdated item → check tooltip text |
| Cross-navigation | Agent detail → click linked skill → skill detail → click "Used By" agent → back |

### Integration Tests (Real Endpoints — NEW per VP-1-TEST)

> These tests verify that Phase 3 components work correctly with REAL Phase 2 API responses, catching data format mismatches that mocked tests cannot detect.

| Scenario | What It Tests | How |
|---|---|---|
| Agent detail data contract | `AgentDetailData` TypeScript interface matches Phase 2 `GET /api/config/agents/{name}/detail` response | Fetch real response, validate against zod schema or structural check |
| Skill detail data contract | `SkillDetailView` interface matches Phase 2 `GET /api/config/skills/{name}/detail` response | Same approach |
| AgentDetailPanel with real data | Component renders correctly with actual API response (not mocked) | Start test server, render component, verify all sections populate |
| SkillDetailPanel with real data | Component renders correctly with actual API response | Same approach |
| Graceful degradation | Component handles missing Phase 2 endpoints (404) without crashing | Point to server without Phase 2 routes, verify error banner appears |
| Missing optional fields | Component handles agents/skills with minimal frontmatter | Use real API with fixture agents that have sparse metadata |

---

## 15. Rollback Plan

### Feature Flag Approach

Each Phase 3 feature is wrapped in a feature flag:

```typescript
const FEATURES = {
  RICH_DETAIL_PANELS: true,     // Sub-Phase 3A
  FILTER_DROPDOWNS: true,       // Sub-Phase 3B
  VERSION_MISMATCH: true,       // Sub-Phase 3B
  COLLABORATION_LINKS: true,    // Sub-Phase 3C
  SKILL_LINKS_MERGE: true,      // Sub-Phase 3C
  SEARCH_ENHANCEMENTS: true,    // Sub-Phase 3B
};
```

> **[REVISED]** Removed COLLABORATION_GRAPH and VIRTUAL_SCROLLING feature flags (features removed from scope).

### Data Safety

Phase 3 is entirely **read-only** — no new mutation endpoints, no file writes. Rollback has zero data risk.

---

## 16. Risk Assessment

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| **VP-1-DEPLOY: Phase 2 not deployed before Phase 3** | **Medium** | **HIGH** | **Strict deployment ordering: verify ALL Phase 2 endpoints exist before starting Phase 3. Pre-deployment checklist in Verification Amendments section.** |
| **VP-1-SEC: Phase 2 detail endpoints lack path traversal protection** | **Low (mitigated in Phase 2 v3)** | **HIGH** | **Phase 2 plan v3 adds mandatory `validate_safe_name()`. Verify this is in place before Phase 3 sends user input to these endpoints.** |
| **VP-1-TEST: Data format mismatch between Phase 2 API and Phase 3 interfaces** | **Medium** | **Medium** | **Integration tests with real endpoints (see Testing Strategy). Cross-phase contract tests validate TypeScript interfaces against actual JSON.** |
| Agent detail endpoint not ready (Phase 2 dependency) | Medium | High | Feature flag; detail panel degrades to list-level data only |
| Filter dropdowns overwhelm narrow panels | Medium | Low | Responsive wrapping; collapse to icon-only on narrow widths |
| Agent detail cache grows too large | Low | Low | Cache limited to 50 entries with LRU eviction |
| Skill name matching fails (prefix mismatches) | Medium | Medium | Normalize names before matching; log mismatches |
| Color field missing for some agents | Known (3 agents) | Low | Gray default already handled in Phase 2 |
| Breaking changes to existing Badge during consolidation | Low | Medium | Phase 1 handles Badge consolidation before Phase 3 |

> **[REVISED]** Removed risks for collaboration graph (unreadable at scale) and virtual scrolling (unnecessary complexity). These features are no longer in scope.

---

## 17. Deferred Features

> **[REVISED]** New section documenting features removed from scope with justification and conditions for re-evaluation.

### Virtual Scrolling

**What**: Render only visible list items using a VirtualList component.

**Why deferred**: At 45 agents + 156 skills ≈ 200 items total, virtual scrolling is unnecessary:
- Standard DOM renders 200 `<li>` elements with badges and text in < 5ms on modern browsers
- Virtual scrolling adds complexity: dynamic height calculation, scroll position preservation, accessibility issues (screen readers can't see off-screen items), keyboard navigation complexity
- Svelte 5's `$derived` already handles efficient re-rendering

**When to reconsider**: If item count exceeds 500+ or if performance profiling shows actual rendering bottlenecks on target devices.

### Agent Collaboration Graph

**What**: Full visual graph rendering of all agent handoff relationships.

**Why deferred**: 45 agents × average 3 handoffs = ~135 edges. This creates a dense graph that:
- Is unreadable without careful layout (requires graph layout library like d3-force or vis.js)
- Adds a significant dependency (graph library)
- Is notoriously difficult to maintain and test
- Would require zoom, pan, and filtering controls for usability

**What was implemented instead**: "Related Agents" clickable text list in the detail panel (Feature 5). This provides the same navigation capability at ~10% of the implementation cost.

**When to reconsider**: If user feedback specifically requests visual graph representation AND a UX research study confirms it provides value over text links.

---

## Appendix A: File Inventory

### New Files (12)

> **[REVISED]** Reduced from 15 files (removed VirtualList.svelte, AgentCollaborationView.svelte graph component, version.ts moved inline).

| File | Lines (est.) | Purpose |
|---|---|---|
| `shared/CollapsibleSection.svelte` | ~60 | Expandable section primitive |
| `shared/MetadataGrid.svelte` | ~40 | Key-value grid layout |
| `shared/ColorDot.svelte` | ~25 | Color circle indicator |
| `shared/FilterDropdown.svelte` | ~120 | Dropdown filter with counts |
| `shared/FilterBar.svelte` | ~50 | Filter container layout |
| `shared/VersionBadge.svelte` | ~45 | Version with update status |
| `shared/HighlightedText.svelte` | ~40 | Search term highlighting |
| `config/AgentDetailPanel.svelte` | ~250 | Rich agent detail view |
| `config/SkillDetailPanel.svelte` | ~200 | Rich skill detail view |
| `config/AgentFilterBar.svelte` | ~80 | Agent filter configuration |
| `config/SkillFilterBar.svelte` | ~70 | Skill filter configuration |
| `config/SkillChipWithStatus.svelte` | ~35 | Skill chip with deploy indicator |

**Total new code: ~1,015 lines estimated**

### Modified Files (5)

| File | Changes |
|---|---|
| `config/ConfigView.svelte` | Replace inline detail with new panels; deprecate Skill Links tab |
| `config/AgentsList.svelte` | FilterBar integration, VersionBadge, HighlightedText |
| `config/SkillsList.svelte` | FilterBar integration, VersionBadge, HighlightedText |
| `stores/config.svelte.ts` | New interfaces, fetchAgentDetail, agentDetailCache, version utils |
| `config/SkillLinksView.svelte` | Add deprecation notice banner |

---

*This plan supersedes any prior Phase 3 references in the overview document. Implementation should follow the sub-phase ordering (3A -> 3B -> 3C) with feature flags enabling independent rollback of each feature.*
