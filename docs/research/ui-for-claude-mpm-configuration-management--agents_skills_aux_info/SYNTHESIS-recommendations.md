# SYNTHESIS: Agents & Skills UI Enhancement Recommendations

**Date**: 2026-02-14
**Status**: Final Synthesis
**Sources**: Agent Definitions Research, Skill Definitions Research, Dashboard UI Research, Devil's Advocate Review
**Purpose**: Definitive reference for implementing agents/skills display improvements in the claude-mpm dashboard

---

## A. Executive Summary

### Key Takeaways

1. **The frontend is throwing away data the backend already provides.** The `AvailableSkill` TypeScript interface uses only 5 of the 12+ fields the API returns. Seven fields (version, toolchain, framework, tags, token counts, requires, author, updated, source_path) can be surfaced immediately with zero backend work.

2. **Deployed agents are severely under-described.** The deployed agents endpoint returns only 7 fields (name, location, path, version, type, specializations, is_core) — fewer than available agents (10+ fields). Users get LESS information about agents they're actively running than about ones they haven't deployed. The most critical missing field is `description`.

3. **Rich metadata exists but is buried.** Agent definitions contain 20+ metadata fields (color, skills, dependencies, expertise, handoff agents, resource tier, network access). Skill definitions have a 3-layer metadata architecture (manifest, metadata.json, SKILL.md frontmatter). The API exposes roughly 30% of available agent metadata and the frontend uses even less of what's sent.

4. **The skill `category` field is misleading for filtering.** The manifest's `category` is a binary `"universal"` vs `"toolchains"` split — useless for user-facing filtering. The `toolchain` field (ai, python, javascript, etc.) is the real grouping dimension, with `"Universal"` as a catch-all for skills where `toolchain` is null.

5. **Agent handoff relationships are far richer than initially reported.** The `handoff_agents` field exists in 78% of agents (39/50), not just QA agents. This enables a comprehensive collaboration graph, though rendering 39 interconnected agents requires careful UX design.

### The Single Most Important Finding

**Half the skill metadata "gaps" require only frontend TypeScript interface updates — no backend changes.** The API already sends `version`, `toolchain`, `framework`, `tags`, `entry_point_tokens`, `full_tokens`, `requires`, `author`, `updated`, and `source_path` for available skills. The frontend `AvailableSkill` interface ignores all of them. This is the highest-ROI improvement: update the TypeScript interface and render data that's already flowing.

---

## B. Data Architecture Summary

### B.1 Agent Metadata

**Source**: Agent definitions are Markdown files with YAML frontmatter, stored in the `claude-mpm-agents` repository. ~45 agent definitions organized by category (engineer, ops, qa, security, universal, claude-mpm, documentation) with sub-categorization (backend, frontend, data, mobile, specialized for engineers).

**Key data structures**:
- `AgentDefinition` dataclass — full structured representation with 15+ fields
- `AgentMetadata` in registry — name, type, tier, path, format, description, specializations, tags, etc.
- `RemoteAgentMetadata` — discovery-focused with routing keywords and priorities

**Agent metadata field inventory**:

| Field | Source | In Deployed API? | In Available API? | Recommended for UI? |
|-------|--------|:-:|:-:|:-:|
| `name` | Frontmatter | Yes | Yes | Yes (list + detail) |
| `description` | Frontmatter | **NO** | Yes | **Yes — CRITICAL** |
| `agent_id` | Frontmatter | No (name used) | Yes | Yes (internal key) |
| `version` | Frontmatter | Yes | Yes | Yes (list badge) |
| `agent_type` | Frontmatter | Yes (as `type`) | No | Yes (detail) |
| `category` | Frontmatter | **NO** | Yes | **Yes — grouping** |
| `color` | Frontmatter | **NO** | **NO** | **Yes — visual indicator** |
| `tags` | Frontmatter | **NO** | Yes | Yes (search + detail) |
| `resource_tier` | Frontmatter | **NO** | Partial | Yes (list indicator) |
| `network_access` | Capabilities block | **NO** | **NO** | **Yes — security indicator** |
| `skills` | Frontmatter | **NO** | **NO** | Yes (detail panel) |
| `dependencies` | Frontmatter | **NO** | **NO** | Yes (detail panel) |
| `knowledge.domain_expertise` | Frontmatter | **NO** | **NO** | Yes (detail panel) |
| `knowledge.constraints` | Frontmatter | **NO** | **NO** | Yes (detail panel) |
| `interactions.handoff_agents` | Frontmatter | **NO** | **NO** | Yes (detail panel) |
| `temperature` | Frontmatter | **NO** | **NO** | Yes (detail, as label) |
| `timeout` | Frontmatter | **NO** | **NO** | Optional (detail) |
| `max_tokens` | Frontmatter | **NO** | **NO** | No (confusing to users) |
| `capabilities.memory_limit` | Frontmatter | **NO** | **NO** | No (noise) |
| `capabilities.cpu_limit` | Frontmatter | **NO** | **NO** | No (noise) |
| `schema_version` | Frontmatter | **NO** | **NO** | No (internal) |
| `template_version` | Frontmatter | **NO** | **NO** | No (low value) |
| `template_changelog` | Frontmatter | **NO** | **NO** | No (low value) |
| `memory_routing` | Frontmatter | **NO** | **NO** | No (internal plumbing) |
| `interactions.output_format` | Frontmatter | **NO** | **NO** | No (implementation detail) |
| `author` | Frontmatter | **NO** | Yes (in metadata) | Optional |
| `source` / `source_url` | Registry | No | Yes | Yes (detail footer) |
| `location` | Registry | Yes | No | Yes (deployed detail) |
| `path` | Registry | Yes | No | Optional (power user) |
| `specializations` | Registry | Yes | No | Yes (detail) |
| `is_core` | Registry | Yes | No | Yes (lock icon) |
| `is_deployed` | Cross-ref | No | Yes | Yes (status badge) |
| `priority` | Registry | No | Yes | No (internal routing) |

**Edge cases identified**:
- 3 agents (6%) are missing the `color` field: `code-analyzer`, `local-ops-agent`, `nestjs-engineer` — UI must default to `gray`
- Color distribution is skewed: most engineers are `green`, making color alone a poor differentiator
- Security agent is categorized under `quality` — may confuse users expecting a "security" category
- Agent file sizes range from 2.5KB (local-ops) to 62KB (mpm-skills-manager) — detail views should handle varying complexity

### B.2 Skill Metadata

**Source**: Skills live in the `claude-mpm-skills` repository with a 3-layer metadata architecture. 156 total skills split between universal (37) and toolchains (117).

**Three metadata layers**:

1. **manifest.json** (Central registry — guaranteed, basic): name, version, category, toolchain, framework, tags, token counts, requires, author, updated, source_path
2. **metadata.json** (Per-skill — optional, rich): adds description, key_features, use_cases, related_skills, prerequisites, installation, performance_benchmarks, subcategory, license, created/modified dates
3. **SKILL.md frontmatter** (Content-embedded): name, description, when_to_use, version, languages, progressive_disclosure, tags

**Skill metadata field inventory**:

| Field | Source | In Deployed API? | In Available API? | In Frontend Interface? | Recommended for UI? |
|-------|--------|:-:|:-:|:-:|:-:|
| `name` | All layers | Yes | Yes | Yes | Yes (list + detail) |
| `description` | metadata.json / SKILL.md | Sparse (often empty) | **NO** | Yes (empty) | **Yes — needs enrichment** |
| `version` | manifest | No | **Yes (sent)** | **NO (dropped!)** | **Yes — badge** |
| `category` | manifest | Yes (from index) | Yes | Yes | Partial (see toolchain) |
| `toolchain` | manifest | No | **Yes (sent)** | **NO (dropped!)** | **Yes — primary filter** |
| `framework` | manifest | No | **Yes (sent)** | **NO (dropped!)** | Yes (detail) |
| `tags` | manifest / SKILL.md | No | **Yes (sent)** | **NO (dropped!)** | **Yes — search + detail** |
| `entry_point_tokens` | manifest | No | **Yes (sent)** | **NO (dropped!)** | Yes (size indicator) |
| `full_tokens` | manifest | No | **Yes (sent)** | **NO (dropped!)** | Yes (size indicator) |
| `requires` | manifest | No | **Yes (sent)** | **NO (dropped!)** | Yes (dependencies) |
| `author` | manifest | No | **Yes (sent)** | **NO (dropped!)** | Optional |
| `updated` | manifest | No | **Yes (sent)** | **NO (dropped!)** | Yes (freshness) |
| `source_path` | manifest | No | **Yes (sent)** | **NO (dropped!)** | Yes (breadcrumb) |
| `is_deployed` | Cross-ref | No | Yes | Yes | Yes (status badge) |
| `collection` | Deployment index | Yes | No | Yes | Yes (detail) |
| `deploy_mode` | Deployment index | Yes (agent_ref/user_def) | No | Yes | Yes (detail) |
| `deploy_date` | Deployment index | Yes | No | Yes | Yes (detail) |
| `is_user_requested` | Deployment index | Yes | No | Yes | Yes (badge) |
| `path` | Deployment scan | Yes | No | Yes | Optional (power user) |
| `when_to_use` | SKILL.md frontmatter | No | No | No | Yes (detail - lazy load) |
| `key_features` | metadata.json | No | No | No | Optional (detail - lazy) |
| `use_cases` | metadata.json | No | No | No | Optional (detail - lazy) |
| `related_skills` | metadata.json | No | No | No | Yes (detail - lazy) |
| `prerequisites` | metadata.json | No | No | No | Optional (detail - lazy) |
| `has_references` | manifest | No | No | No | Low (badge) |
| `performance_benchmarks` | metadata.json | No | No | No | No (too sparse) |
| `production_adopters` | metadata.json | No | No | No | No (too sparse) |

**Key insight**: Rows marked "**Yes (sent) / NO (dropped!)**" represent the biggest quick win — 10 fields the API already returns that the frontend TypeScript interface doesn't capture.

---

## C. Critical Issues Found

### C.1 Frontend Discarding API Data (HIGHEST PRIORITY)

The `AvailableSkill` TypeScript interface defines only 5 fields:

```typescript
interface AvailableSkill {
    name: string;
    description: string;
    category: string;
    collection: string;
    is_deployed: boolean;
}
```

The API actually returns 12+ fields including `version`, `toolchain`, `framework`, `tags`, `entry_point_tokens`, `full_tokens`, `requires`, `author`, `updated`, `source_path`, and `is_deployed`. **Seven fields are silently dropped.** This means the most impactful improvement requires zero backend work.

### C.2 Deployed Agents Missing Description (HIGH)

The deployed agents endpoint returns only: `name`, `location`, `path`, `version`, `type`, `specializations`, `is_core`. **There is no `description` field.** Users who deploy an agent immediately lose context about what it does. This is backwards — deployed agents are the ones users need to understand most.

The agent researcher referenced a `get_agent_metadata()` method that would provide richer data, but **this method does not exist** in the codebase. The actual enrichment path requires either:
1. Parsing YAML frontmatter from deployed .md files at request time (15-20 file reads + YAML parses per request)
2. Caching frontmatter fields in a deployment index at deploy time (one-time cost, preferred approach)
3. Cross-referencing deployed agents with the available agents endpoint data

### C.3 Color Field Not Universal (MEDIUM)

The agent research claimed color is "universally defined." This is false — 3 out of ~50 agents (6%) lack the `color` field: `code-analyzer`, `local-ops-agent`, `nestjs-engineer`. Additionally, color distribution is heavily skewed (most engineers = `green`), making it supplementary to grouping, not a replacement.

**Implication**: UI must treat `color` as optional with `gray` default. Color dots add visual interest but cannot be the primary differentiator.

### C.4 Skill Category Field is Misleading (MEDIUM)

The manifest `category` field has only two values: `"universal"` and `"toolchains"`. This binary split is useless for filtering 156 skills. The `toolchain` field (`ai`, `python`, `javascript`, `rust`, etc.) is the actual useful grouping dimension. Universal skills (where `toolchain` is null) should be grouped under a "Universal" header.

### C.5 Handoff Agent Data More Complete Than Reported (LOW — Informational)

The `interactions.handoff_agents` field exists in 78% of agents (39/50), not just QA. This is a rich dataset for relationship visualization, but rendering 39 interconnected agents requires careful design to avoid graph complexity overload. Keep as a detail-panel feature, not a list-level one.

### C.6 Skill Metadata Consistency Challenges (MEDIUM)

Skills have 3 metadata layers where the same field (e.g., `description`, `tags`, `name`) can appear with potentially different values. The UI should use manifest data as the guaranteed baseline and metadata.json as optional enrichment loaded lazily. SKILL.md frontmatter data may not be accessible without parsing deployed files.

### C.7 Stale Data Risk (LOW)

Agent definitions in the repository can change without deployed copies being updated. The dashboard could show outdated metadata. A "version mismatch" badge (deployed version vs. latest available) would alert users.

---

## D. Recommended UI Design

### D.1 Design Philosophy

The UI should follow **progressive disclosure** with three information tiers:
- **List view**: 5-6 fields maximum — enough to scan, search, and identify
- **Detail panel**: 10-12 fields — enough to evaluate and decide
- **Expandable sections**: Deep metadata — for power users and specific investigations

### D.2 Agent List View — Compact Card List

```
┌───────────────────────────────────────────────────────────┐
│ [Search...   ]  [Category ]  [Status ]  [Sort ]     │
├───────────────────────────────────────────────────────────┤
│                                                           │
│  Engineering (12 agents)                                  │
│ ─────────────────────────────────────────────────────────│
│                                                           │
│ ┌─ [green dot] Python Engineer ── v2.3.0 ── [Deployed] ─┐│
│ │  Python 3.12+ specialist: type-safe, async-first...    ││
│ │  python  async  SOA             [globe] standard       ││
│ └────────────────────────────────────────────────────────┘│
│                                                           │
│ ┌─ [green dot] Rust Engineer ──── v2.3.0 ── [Deploy ->] ─┐│
│ │  Rust 2024 edition: memory-safe, zero-cost...          ││
│ │  rust  async  tokio             [globe] standard       ││
│ └────────────────────────────────────────────────────────┘│
│                                                           │
│  Quality (5 agents)                                       │
│ ─────────────────────────────────────────────────────────│
│                                                           │
│ ┌─ [red dot] Security ──────── v2.1.0 ── [Deploy ->] ───┐│
│ │  Advanced security scanning with SAST, attack...       ││
│ │  security  OWASP  SAST          [globe] standard       ││
│ └────────────────────────────────────────────────────────┘│
│                                                           │
│  Operations (8 agents)                                    │
│ ─────────────────────────────────────────────────────────│
│ ...                                                       │
└───────────────────────────────────────────────────────────┘
```

**Fields shown per agent card**:

| Element | Source | Fallback |
|---------|--------|----------|
| Color dot | `color` field | Gray if missing |
| Name | `name` | Always present |
| Version | `version` | Always present |
| Deploy status | `is_deployed` / `is_core` | Always present |
| Description (1 line, ~80 chars) | `description` | "No description available" |
| Tags (max 3) | `tags` | Hide section if none |
| Network icon (globe/lock) | `capabilities.network_access` | Hide if unknown |
| Resource tier label | `resource_tier` | Hide if unknown |

**Category group headers** use the `category` field with collapsible sections. Counts shown in headers.

### D.3 Skill List View — Compact Card List

```
┌───────────────────────────────────────────────────────────┐
│ [Search...   ]  [Toolchain ]  [Status ]  Mode: [Sel.]│
├───────────────────────────────────────────────────────────┤
│                                                           │
│  Universal (37 skills)                                    │
│ ─────────────────────────────────────────────────────────│
│                                                           │
│ ┌─ brainstorming ──────────── v1.0.0 ── [Deployed] ─────┐│
│ │  Interactive idea refinement using Socratic method      ││
│ │  debugging  frontend           649 tok   12 agents     ││
│ └────────────────────────────────────────────────────────┘│
│                                                           │
│  AI (9 skills)                                            │
│ ─────────────────────────────────────────────────────────│
│                                                           │
│ ┌─ dspy ───────────────────── v1.0.0 ── [Deploy ->] ────┐│
│ │  Declarative framework for prompt optimization         ││
│ │  ai  llm  rag               10,191 tok   5 agents     ││
│ └────────────────────────────────────────────────────────┘│
│                                                           │
│  Python (10 skills)                                       │
│ ─────────────────────────────────────────────────────────│
│ ...                                                       │
└───────────────────────────────────────────────────────────┘
```

**Fields shown per skill card**:

| Element | Source | Fallback |
|---------|--------|----------|
| Name | `name` | Always present |
| Version | `version` (manifest) | Always present |
| Deploy status | `is_deployed` + deploy_mode | Always present |
| Description (1 line) | `description` or `when_to_use` | "No description available" |
| Tags (max 3) | `tags` (manifest) | Hide section if none |
| Token count | `full_tokens` | Hide if 0 or missing |
| Agent count | Skill-links API | Hide if unavailable |

**Toolchain as primary grouping**: "Universal" for skills with `toolchain: null`, then `ai`, `python`, `javascript`, etc. for toolchain skills. This replaces the useless binary `category` split.

**Deployment mode indicator** in the header bar (Selective/Full) since this affects what's deployed.

### D.4 Agent Detail Panel (Right Side)

When a user clicks an agent, the right panel shows:

```
┌──────────────────────────────────────────────────┐
│ [green dot]  Python Engineer               v2.3.0│
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│                                                   │
│ Python 3.12+ development specialist: type-safe,   │
│ async-first, production-ready implementations     │
│ with SOA and DI patterns                          │
│                                                   │
│ ┌──────────┬──────────┬────────────┐             │
│ │ Category │ Tier     │ Network    │             │
│ │ engineer │ standard │ Yes [globe]│             │
│ └──────────┴──────────┴────────────┘             │
│                                                   │
│ > Expertise (click to expand)                     │
│   - Python 3.12-3.13 features (JIT, TypeForm)     │
│   - Service-oriented architecture with ABC        │
│   - Async/await patterns with asyncio             │
│                                                   │
│ > Skills (18 linked)                              │
│   [pytest +] [mypy +] [pydantic -] [git-workflow +]│
│   [test-driven-development +] ...+13              │
│   "2 required skills not deployed" [warning]      │
│                                                   │
│ > Dependencies                                    │
│   Python: black, isort, mypy, pytest, pydantic    │
│   System: python3.12+, git                        │
│                                                   │
│ > Collaborates With                               │
│   -> qa  -> security  -> data_engineer  -> devops │
│                                                   │
│ > Constraints                                     │
│   - Maximum 5-10 test files for sampling          │
│   - Skip test files >500KB unless critical        │
│                                                   │
│ ──────────────────────────────────────            │
│ Source: bobmatnyc/claude-mpm-agents                │
│ Temperature: 0.2 (precise)                        │
│ Timeout: 900s                                     │
│                                                   │
│           [Deploy]  or  [Undeploy]                │
└──────────────────────────────────────────────────┘
```

**Progressive disclosure sections** (collapsed by default):

| Section | Source Fields | When Valuable |
|---------|-------------|---------------|
| Expertise | `knowledge.domain_expertise` | Evaluating agent capabilities |
| Skills | `skills` field + skill-links API | Understanding dependencies |
| Dependencies | `dependencies` block | Setup requirements |
| Collaborates With | `interactions.handoff_agents` | Understanding agent ecosystem |
| Constraints | `knowledge.constraints` | Understanding limitations |

**Temperature rendered as semantic label**: 0.0 = "precise", 0.1-0.3 = "focused", 0.4-0.7 = "balanced", 0.8-1.0 = "creative". Users understand "precise" better than "0.2".

**Skills shown as chips** with deployment status indicators: `+` (green) = deployed, `-` (red) = not deployed. Warning message if required skills are not deployed.

### D.5 Skill Detail Panel (Right Side)

```
┌──────────────────────────────────────────────────┐
│ dspy                                       v1.0.0│
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│                                                   │
│ Declarative framework for automatic prompt        │
│ optimization treating prompts as code             │
│                                                   │
│ ┌──────────┬──────────┬────────────┐             │
│ │ Toolchain│ Tokens   │ Updated    │             │
│ │ ai       │ 10,191   │ 2025-12-31 │             │
│ └──────────┴──────────┴────────────┘             │
│                                                   │
│ > When to Use                                     │
│   "When building RAG pipelines, classification    │
│    systems, or optimizing prompt performance"     │
│                                                   │
│ > Used By (5 agents)                              │
│   python-engineer, research, java-engineer,       │
│   data-engineer, mpm-skills-manager               │
│                                                   │
│ > Dependencies                                    │
│   Requires: (none)                                │
│                                                   │
│ > Related Skills                                  │
│   anthropic-sdk, langchain, langgraph             │
│                                                   │
│ ──────────────────────────────────────            │
│ Author: claude-mpm-skills                         │
│ Source: toolchains/ai/frameworks/dspy/SKILL.md     │
│ Deploy mode: agent_referenced                     │
│                                                   │
│           [Deploy]  or  [Undeploy]                │
└──────────────────────────────────────────────────┘
```

### D.6 Filtering and Sorting Strategy

**Filters that help users (include)**:

| Filter | Target | Source | Why |
|--------|--------|--------|-----|
| Category | Agents | `category` field | Group by role (engineering, quality, operations, etc.) |
| Toolchain | Skills | `toolchain` field | Group by language (ai, python, javascript, etc.) |
| Deployment status | Both | `is_deployed` | "What I have" vs "what's available" |
| Network access | Agents | `capabilities.network_access` | Security-conscious filtering |
| Resource tier | Agents | `resource_tier` | "Show me lightweight agents" |

**Filters that would NOT help (exclude)**:
- Tag filter — 100+ unique tags across agents, dropdown would be unusable. Instead, integrate tags into free-text search (search matches against name + description + tags).
- Author filter — only 2 authors in the entire system
- Version filter — version ranges don't help users choose agents
- Schema version — internal, not user-facing

**Sort options**: Name (A-Z), version, deployment status, recently updated.

### D.7 Agent-Skill Relationship Visualization

**Replace the separate "Skill Links" tab** with integrated bidirectional views:

**In Agent Detail Panel** — Skills section with deployment status and grouped by link type:
```
Skills (18 total)
  Required:  [pytest +] [mypy +] [pydantic -] [git-workflow +]
  Inferred:  [test-driven-development +] [systematic-debugging +]

  + = deployed, - = not deployed
  "3 required skills not deployed" [warning]
```

**In Skill Detail Panel** — Used By section showing referencing agents:
```
Used by (12 agents)
  python-engineer, java-engineer, rust-engineer, golang-engineer,
  ruby-engineer, php-engineer, typescript-engineer, ...
```

This bidirectional view eliminates the need for a standalone Skill Links tab while providing the same (and better contextualized) information.

### D.8 What NOT to Show (and Why)

| Field | Why Exclude |
|-------|-------------|
| `max_tokens` | Users don't understand what 4096 vs 16384 means; creates anxiety without actionable info |
| `cpu_limit` | A percentage with no user-controllable behavior; not actionable |
| `memory_limit` (MB) | Unless deploying to resource-constrained environments, this is noise |
| `schema_version` | Internal compatibility tracking; validation panel should flag mismatches |
| `template_version` + `template_changelog` | Changelog entries like "Architecture Enhancement" are developer-facing, not user-facing |
| `memory_routing` | Internal system plumbing for memory management |
| `interactions.output_format` | Whether output is "markdown" or "structured" is an implementation detail |
| `performance_benchmarks` (skills) | Too sparse (only a few skills have this data) and too specialized |
| `production_adopters` (skills) | Too sparse and of questionable relevance for deployment decisions |

---

## E. Prioritized Implementation Roadmap

### Tier 1: Quick Wins (Frontend-Only, No API Changes)

These can be implemented immediately by a frontend engineer with no backend coordination.

| # | Task | Effort | Impact |
|---|------|--------|--------|
| 1.1 | **Update `AvailableSkill` TypeScript interface** to include `version`, `toolchain`, `framework`, `tags`, `entry_point_tokens`, `full_tokens`, `requires`, `author`, `updated`, `source_path` | Small | **HIGH** — unlocks 10 data fields |
| 1.2 | **Render skill `version` badge** in skill list items | Trivial | Medium — version visibility |
| 1.3 | **Add toolchain grouping** to skills list using `toolchain` field (with "Universal" for null) | Medium | **HIGH** — meaningful organization |
| 1.4 | **Add category grouping** to agents list using `category` from available agents | Medium | **HIGH** — meaningful organization |
| 1.5 | **Render skill `tags`** (max 3) in skill list items | Small | Medium — search + context |
| 1.6 | **Render skill token count** (`full_tokens`) as size indicator in list items | Small | Low — information density |
| 1.7 | **Add sort controls** to both agents and skills lists (name, version, status) | Medium | Medium — user control |
| 1.8 | **Show skill `updated` date** in detail panel | Trivial | Low — freshness indicator |
| 1.9 | **Render `source_path`** in skill detail as breadcrumb trail | Small | Low — source context |
| 1.10 | **Consolidate duplicate Badge components** — unify `components/Badge.svelte` and `components/shared/Badge.svelte` into one consistent API | Medium | Medium — technical debt |

### Tier 2: Short-Term (Backend + Frontend)

These require backend API changes plus frontend updates. Estimated 1-2 sprint cycles.

| # | Task | Backend Work | Frontend Work | Impact |
|---|------|-------------|---------------|--------|
| 2.1 | **Enrich deployed agents endpoint** with frontmatter fields: `description`, `category`, `color`, `tags`, `resource_tier`, `network_access`, `skills` (names only) | Cache frontmatter at deploy time in `.deployment_index.json` (like skills already do) | Update `DeployedAgent` interface + render new fields | **CRITICAL** |
| 2.2 | **Add `color` field to available agents endpoint** | Read from frontmatter during discovery cache scan | Add color dot to agent list items | Medium |
| 2.3 | **Add agent deployment index** (`.claude/agents/.deployment_index.json`) analogous to skills' deployment index. Store frontmatter fields at deploy time to avoid runtime YAML parsing | New deployment index creation + update logic | Read from cached index | **HIGH** — performance |
| 2.4 | **Enrich deployed skills with manifest data** — cross-reference deployed skills against cached manifest to fill in `version`, `toolchain`, `tags`, etc. | Match deployed skill names to manifest entries | Update `DeployedSkill` interface | Medium |
| 2.5 | **Add agent count to available skills** — return how many agents reference each skill (from skill-links data) | Compute from skills registry at endpoint time | Show "N agents" badge in skill cards | Medium |
| 2.6 | **Integrate skill-links into detail panels** — when viewing an agent, show linked skills; when viewing a skill, show referencing agents | Ensure skill-links API data is accessible from detail endpoints | Add Skills section to agent detail, Used By section to skill detail | Medium |

### Tier 3: Medium-Term (New Features)

These involve significant new functionality. Estimated 2-4 sprint cycles.

| # | Task | Description | Impact |
|---|------|-------------|--------|
| 3.1 | **Build rich agent detail panel** with progressive disclosure sections (expertise, skills, dependencies, collaborators, constraints) | Requires lazy-loading frontmatter data for detail view; collapsible sections pattern | **HIGH** |
| 3.2 | **Build rich skill detail panel** with when_to_use, linked agents, related skills, and dependency info | Requires lazy-loading metadata.json and SKILL.md frontmatter for detail view | Medium |
| 3.3 | **Implement category/toolchain/status filter dropdowns** in list headers | Requires filter state management and UI filter controls | Medium |
| 3.4 | **Add version mismatch detection** — badge showing when deployed version differs from latest available | Requires cross-referencing deployed + available data | Medium |
| 3.5 | **Virtual scrolling** for 45+ agent and 156+ skill lists | Replace flat list rendering with virtualized list component | Low (performance) |
| 3.6 | **Undeploy protection explanations** — when hovering locked items, show WHY they're protected (PM_CORE_SKILLS, CORE_SKILLS, from source collection) | Tooltip or popover with protection reason | Low |
| 3.7 | **Skills missing warning on agents** — in agent detail panel, highlight required skills that are not deployed and offer one-click deploy | Requires cross-referencing agent.skills with deployed skills | Medium |

### Deferred (Low ROI or High Risk)

| Task | Why Defer |
|------|-----------|
| Full agent relationship graph visualization | Complex to render, unreadable with 39 interconnected agents, low user action value |
| Skill dependency graph | Very few skills have `requires` relationships — too sparse for a graph view |
| Template changelog display | Low user value; changelog entries are developer-facing |
| metadata.json rich fields (benchmarks, adopters) | Too sparse across skills to build reliable UI for |
| Inline skill content preview | Performance-heavy (loading SKILL.md content); low decision-making value |
| Skill Links as separate tab (keep or revamp) | Replace with integrated detail-panel views instead |

---

## F. API Gap Remediation

### F.1 Deployed Agents Endpoint (`GET /api/config/agents/deployed`)

**Current response** (7 fields):
```json
{
  "name": "engineer", "location": "project", "path": "/...",
  "version": "2.5.0", "type": "core", "specializations": [], "is_core": true
}
```

**Recommended response** (14 fields):
```json
{
  "name": "engineer",
  "location": "project",
  "path": "/path/to/.claude/agents/engineer.md",
  "version": "2.5.0",
  "type": "core",
  "specializations": [],
  "is_core": true,
  "description": "Base engineer agent for general-purpose development",
  "category": "engineering",
  "color": "green",
  "tags": ["engineering", "general-purpose"],
  "resource_tier": "standard",
  "network_access": true,
  "skills_count": 18
}
```

**Implementation approach**: Create an agent deployment index (`.claude/agents/.deployment_index.json`) that stores frontmatter fields when agents are deployed. Read from this cache on API calls instead of parsing YAML at request time. Structure mirrors the existing skill deployment index pattern.

**Performance**: One-time frontmatter extraction at deploy time. No runtime YAML parsing needed.

### F.2 Available Agents Endpoint (`GET /api/config/agents/available`)

**Add `color` field** from frontmatter. This is currently the only high-value field missing from this endpoint — it already returns name, description, version, category, tags, source, priority.

The `color` field should be extracted during the discovery/cache sync process and stored alongside other cached metadata.

### F.3 Deployed Skills Endpoint (`GET /api/config/skills/deployed`)

**Current issue**: Returns sparse data (name, path, description [often empty], category, collection, deploy_mode, deploy_date).

**Recommended enrichment**: Cross-reference deployed skill names against the cached manifest to add: `version`, `toolchain`, `tags`, `full_tokens`, `entry_point_tokens`.

**Implementation**: When returning deployed skills, look up each skill name in the cached manifest data (already available from `list_available_skills()`). This is an in-memory join, not additional I/O.

### F.4 New Endpoint: Agent Detail (`GET /api/config/agents/{name}/detail`)

For the detail panel's lazy-loaded sections, create a new endpoint that returns the full frontmatter for a single agent:

```json
{
  "name": "python-engineer",
  "description": "...",
  "knowledge": {
    "domain_expertise": ["..."],
    "constraints": ["..."]
  },
  "skills": ["pytest", "mypy", "pydantic", ...],
  "dependencies": {
    "python": ["black>=24.0.0", ...],
    "system": ["python3.12+", "git"]
  },
  "handoff_agents": ["qa", "security", "data_engineer"],
  "temperature": 0.2,
  "timeout": 900
}
```

This endpoint parses the full frontmatter for a single agent file — acceptable performance for single-item requests triggered by user click.

### F.5 Performance Considerations

| Concern | Mitigation |
|---------|------------|
| YAML parsing 15-20 deployed agents on every list request | Use deployment index cache — parse once at deploy time |
| Loading 156 skill manifests | Already cached by SkillsDeployerService; no additional I/O needed |
| Loading agent detail frontmatter | Lazy load on click (single file); acceptable latency |
| Loading metadata.json for skill detail | Lazy load on click if available in cache; graceful fallback |
| Frontend rendering 45+ agents or 156+ skills | Add pagination and/or virtual scrolling for lists >50 items |

---

## G. Specific Examples

### G.1 Complex Agent: Research Agent

**List view card**:
```
[purple dot] Research ──────── v5.0.0 ── [Deployed]
  Memory-efficient codebase analysis with required ticket attachment...
  research  ticketing  google-workspace   [globe] high
```

**Detail panel key sections**:
- **Category**: research | **Tier**: high | **Network**: Yes
- **Expertise** (23 items): "Comprehensive codebase exploration", "Architectural analysis", "Security posture evaluation", "Google Workspace integration"...
- **Skills** (25+ linked): dspy, langchain, langgraph, mcp, software-patterns, test-driven-development, systematic-debugging, git-workflow...
- **Dependencies**: Python (tree-sitter, pygments, radon), System (python3, git)
- **Collaborates With**: (from handoff_agents — to be verified per agent)
- **Constraints**: "Maximum 3-5 files per session", "Mandatory use of document summarization for files >20KB"
- **Temperature**: 0.2 (precise) | **Timeout**: 1800s (30 min)

### G.2 Simple Agent: Local Ops

**List view card**:
```
[gray dot] Local Ops ──────── v1.0.0 ── [Deploy ->]
  Local operations specialist for deployment, DevOps, and process management
  ops  deployment  devops              [globe] basic
```

**Detail panel key sections**:
- **Category**: operations | **Tier**: basic | **Network**: Yes
- **Expertise**: (minimal — small agent file at 2.5KB)
- **Skills**: (standard ops skill set)
- **Dependencies**: System (standard tools)
- **Temperature**: (default)

*Note: Gray dot because `local-ops-agent` is one of 3 agents missing the `color` field.*

### G.3 MPM Skills Manager (System Agent)

**List view card**:
```
[purple dot] MPM Skills Manager ── v3.0.0 ── [Deployed] [Core]
  Manages skill lifecycle including discovery, recommendation, deployment...
  claude-mpm  skills  management       [globe] standard
```

**Detail panel key sections**:
- **Category**: claude-mpm | **Tier**: standard | **Network**: Yes
- **Core agent** (lock icon — cannot undeploy)
- **Expertise**: Skill lifecycle management, PR-based improvements
- **Skills**: (MPM-specific skills)
- **Dependencies**: Python (gitpython, pyyaml), System (python3, git, gh)

### G.4 Universal Skill: Test-Driven Development

**List view card**:
```
test-driven-development ──── v1.0.0 ── [Deployed] [System]
  Comprehensive TDD patterns and practices for all programming languages
  testing  tdd  quality             3,200 tok   30+ agents
```

**Detail panel key sections**:
- **Toolchain**: Universal | **Tokens**: 3,200 | **Updated**: 2025-12-15
- **When to Use**: "When writing tests, implementing test-first methodology, or establishing testing patterns"
- **Used By** (30+ agents): python-engineer, java-engineer, rust-engineer, qa, web-qa, api-qa, golang-engineer, ruby-engineer, php-engineer...
- **Dependencies**: (none)
- **Related Skills**: testing-anti-patterns, condition-based-waiting, webapp-testing
- **Deploy Mode**: agent_referenced | **System** (lock icon — PM_CORE or CORE skill, cannot undeploy)

### G.5 Toolchain Skill: Playwright

**List view card**:
```
playwright ──────────────── v1.0.0 ── [Deployed]
  Modern end-to-end testing framework with cross-browser automation
  testing  e2e  browser             8,500 tok   3 agents
```

**Detail panel key sections**:
- **Toolchain**: javascript | **Tokens**: 8,500 | **Updated**: 2025-12-20
- **When to Use**: "When implementing end-to-end tests, browser automation, or cross-browser testing"
- **Used By** (3 agents): web-qa, svelte-engineer, nextjs-engineer
- **Dependencies**: (none in `requires`)
- **Related Skills**: webapp-testing, condition-based-waiting
- **Deploy Mode**: agent_referenced

### G.6 Toolchain Skill: Docker

**List view card**:
```
docker ──────────────────── v1.0.0 ── [Deploy ->]
  Docker containerization for packaging applications with dependencies
  infrastructure  containers         5,200 tok   8 agents
```

**Detail panel key sections**:
- **Toolchain**: universal (infrastructure category) | **Tokens**: 5,200
- **When to Use**: "When containerizing applications, creating Dockerfiles, or managing multi-container environments"
- **Used By** (8 agents): ops, local-ops, vercel-ops, digitalocean-ops, gcp-ops, project-organizer, agentic-coder-optimizer, python-engineer
- **Dependencies**: (none)
- **Tags**: infrastructure, containers, docker, devops

---

## H. Implementation Quick Reference

### Frontend TypeScript Interface Changes Needed

**AvailableSkill** (update existing — no backend change):
```typescript
interface AvailableSkill {
    name: string;
    description: string;
    category: string;
    collection: string;
    is_deployed: boolean;
    // ADD THESE — API already sends them:
    version: string;
    toolchain: string | null;
    framework: string | null;
    tags: string[];
    entry_point_tokens: number;
    full_tokens: number;
    requires: string[];
    author: string;
    updated: string;
    source_path: string;
}
```

**DeployedAgent** (update after backend enrichment — Tier 2):
```typescript
interface DeployedAgent {
    name: string;
    location: string;
    path: string;
    version: string;
    type: string;
    specializations?: string[];
    is_core: boolean;
    // ADD THESE — requires backend deployment index:
    description?: string;
    category?: string;
    color?: string;
    tags?: string[];
    resource_tier?: string;
    network_access?: boolean;
    skills_count?: number;
}
```

**DeployedSkill** (update after backend enrichment — Tier 2):
```typescript
interface DeployedSkill {
    name: string;
    path: string;
    description: string;
    category: string;
    collection: string;
    is_user_requested: boolean;
    deploy_mode: 'agent_referenced' | 'user_defined';
    deploy_date: string;
    // ADD THESE — requires manifest cross-reference:
    version?: string;
    toolchain?: string | null;
    tags?: string[];
    full_tokens?: number;
}
```

### Edge Case Handling Checklist

| Edge Case | Handling |
|-----------|----------|
| Agent without `color` field (3 agents) | Default to `gray` dot |
| Agent without `skills` list | Show "No skills defined" in detail panel |
| Skill without `description` | Show `when_to_use` from SKILL.md as fallback, then "No description" |
| Agent with 31 tags | Show first 3 tags + "+N more" overflow |
| Skill with 0 or missing `full_tokens` | Hide token count indicator |
| metadata.json not accessible for skill | Degrade gracefully to manifest-only data |
| Deployed agent not in available list | Show deployed data only, no enrichment from available; flag as "custom/unknown source" |
| Security agent categorized as "quality" | Accept current categorization; don't override in UI |
| Circular skill dependencies (if `requires` forms cycle) | Show flat dependency list, don't build/render a graph |
| 156 skills in single list view | Add pagination (50 per page) or virtual scrolling |

---

*This document supersedes the individual research reports. Implementation should follow the tiered roadmap in Section E, starting with Tier 1 frontend-only changes that can be deployed independently.*
