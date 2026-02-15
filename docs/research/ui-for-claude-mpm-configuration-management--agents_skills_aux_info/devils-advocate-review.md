# Devil's Advocate Review: Agents & Skills UI Research

**Date**: 2026-02-14
**Reviewer**: Devil's Advocate Agent (Task #1)
**Documents Reviewed**:
1. `agent-definitions-research.md` (Agent Research)
2. `skill-definitions-research.md` (Skill Research)
3. `dashboard-ui-research.md` (Dashboard UI Research)

---

## Part 1: Challenging the Research Findings

### 1.1 The "Color Field is Universally Defined" Claim is FALSE

The agent researcher states (Section 12, Finding #5): *"The color field is universally defined - Ready for immediate UI integration"*

**Verified finding**: 3 out of 50 agents (6%) are **missing** the `color` field entirely:
- `code-analyzer.md` - no color
- `local-ops-agent.md` - no color
- `nestjs-engineer.md` - no color

**Why this matters for UI**: If you design agent cards that rely on `color` as a "guaranteed" field, 6% of agents will render with undefined/fallback behavior. The researcher's confidence could lead to a design that doesn't handle the missing case, causing visual inconsistency. Any UI design MUST treat `color` as optional with a sensible default (e.g., `gray`).

**Deeper challenge**: Even among agents WITH the color field, the distribution is skewed: most engineers are `green`, making color a poor differentiator. If 18 agents are all green, color badges become noise, not signal. Color should supplement grouping, not replace it.

---

### 1.2 The "handoff_agents is QA-only" Claim is WRONG

The agent researcher implies `handoff_agents` is primarily a QA/some-agent feature (Section 10): *"QA ──handoff──> Engineer, QA ──handoff──> Security, (Other agents' handoff data needs to be extracted from agent body text)"*

**Verified finding**: `handoff_agents` exists in **78% of agents** (39/50), not just QA. Examples:
- `python-engineer.md`: hands off to `["engineer", "qa", "data_engineer", "security", "devops"]`
- `documentation-agent.md`: hands off to `["version_control"]`

This is a rich, widely-available dataset that the researcher dismissed as sparse. A handoff relationship graph could be far more complete than suggested. However, this also means building it requires processing 39 agents' data, not just 2-3.

---

### 1.3 The "AgentLoader.get_agent_metadata()" Method DOESN'T EXIST

The agent researcher references `get_agent_metadata()` in Section 5.4 as returning a rich structure. **This method does not exist** in the codebase. The actual code uses:
- `AgentManager.list_agents()` - returns the minimal set
- `AgentDefinition.to_dict()` - returns a rich structure but is NOT used by the dashboard API

This is important because it means the researcher's "gap analysis" incorrectly assumes there's already a ready-to-use rich metadata method. In reality, enriching the API requires either:
1. Calling `to_dict()` in the endpoint handler (exposes more but may be slow)
2. Building a new method that selectively returns UI-relevant fields
3. Cross-referencing deployed agents with cached source definitions

The gap is bigger than the researcher indicated.

---

### 1.4 The AvailableSkill Frontend Interface is DANGEROUSLY Sparse

The dashboard researcher correctly identified that `AvailableSkill` has only 5 fields:
```typescript
interface AvailableSkill {
    name: string;
    description: string;
    category: string;
    collection: string;
    is_deployed: boolean;
}
```

But the **actual API returns 12+ fields** per skill (manifest fields: name, version, category, toolchain, framework, tags, entry_point_tokens, full_tokens, requires, author, updated, source_path, plus is_deployed). The frontend is **throwing away 7+ fields** that the API already provides!

This means some "gaps" identified by the skill researcher don't require backend changes at all - they just require updating the TypeScript interface and rendering the data already being sent. This is a critical finding that changes the implementation priority:

| Field | Backend Change? | Frontend Change? |
|-------|:-:|:-:|
| `version` | No (already sent) | Just add to interface |
| `toolchain` | No (already sent) | Just add to interface |
| `framework` | No (already sent) | Just add to interface |
| `tags` | No (already sent) | Just add to interface |
| `entry_point_tokens` | No (already sent) | Just add to interface |
| `full_tokens` | No (already sent) | Just add to interface |
| `requires` | No (already sent) | Just add to interface |
| `author` | No (already sent) | Just add to interface |
| `updated` | No (already sent) | Just add to interface |
| `source_path` | No (already sent) | Just add to interface |
| `description` (richer) | Yes (metadata.json) | Update interface |
| `key_features` | Yes (metadata.json) | Add to interface |
| `when_to_use` | Yes (SKILL.md parse) | Add to interface |
| `related_skills` | Yes (metadata.json) | Add to interface |

**Bottom line**: Half the skill "gaps" are frontend-only fixes. The researchers made this seem like it was all backend work.

---

### 1.5 Three Metadata Layers for Skills Create Confusion, Not Value

The skill researcher proudly identifies "THREE levels of metadata richness" (manifest, metadata.json, SKILL.md frontmatter). But from a UI design perspective, this is a **problem, not a feature**:

1. **Data inconsistency**: The same field (`description`, `tags`, `name`) can appear in all three sources with potentially different values. Which wins?
2. **metadata.json is NOT consistently structured**: DSPy has 130 lines, brainstorming has 8 lines. Some have `key_features`, most don't. Some have `performance_benchmarks`, most don't. The UI must gracefully handle wildly varying completeness.
3. **metadata.json may not be accessible at runtime**: The skill researcher doesn't address whether metadata.json files are even cached/downloaded by `SkillsDeployerService`. If only SKILL.md and manifest.json are used during deployment, the rich metadata.json data may require an additional GitHub API call per skill - which is expensive and slow for 156 skills.

**Recommendation**: The UI should be designed around the **manifest** as the guaranteed data layer, with metadata.json treated as an optional enrichment loaded lazily on demand (when a user opens a skill's detail panel).

---

### 1.6 The Deployed Agents Endpoint is Worse Than Described

The agent researcher correctly identifies the deployed agents endpoint as "severely under-described," but understates the severity. Looking at the actual code (`config_routes.py:189-232`), the endpoint returns:
- `name`, `location`, `path`, `version`, `type`, `specializations`, `is_core`

That's **7 fields** for a deployed agent. Compare to the **10+ fields** for an available agent. A user looking at their deployed agents gets LESS information than someone browsing agents they haven't deployed yet. This is backwards - deployed agents are the ones you NEED to understand because they're actively running in your system.

The researcher's "cross-reference with source definitions" suggestion is correct but the implementation is non-trivial: it requires loading the deployed .md file's frontmatter at endpoint time, which means YAML parsing for every deployed agent on every API call. For 15-20 deployed agents, this is ~15 file reads + YAML parses per request.

---

### 1.7 The Researchers Contradict Each Other on Skill Categories

- **Skill researcher** (Section 2.1): Skills have `category` which is `"universal"` or `"toolchain"` (2 categories)
- **Dashboard researcher** (Section 6): Shows category badge on deployed skills, implies diverse categories
- **Skill researcher** (Section 4.3): Available API returns `category: "toolchain"` - just the top level

The reality is:
- `category` in manifest = `"universal"` or `"toolchains"` (binary, not useful for filtering)
- `toolchain` = `"ai"`, `"python"`, `"javascript"`, etc. (the ACTUAL useful grouping)
- `subcategory` = only in metadata.json (not reliably available)

So when the skill researcher recommends "category filter" for the UI, which category are they talking about? The manifest's binary universal/toolchain split is useless for filtering. The `toolchain` field is the real filter, but it's only meaningful for toolchain skills (universal skills have `toolchain: null`).

**Better approach**: Use `toolchain` as primary filter with a "Universal" group for skills where `toolchain` is null. Don't pretend `category` is a useful dimension.

---

### 1.8 The "Skill Links" Data May Be Unreliable

The dashboard researcher documents the Skill Links view but doesn't question the data quality. The skill-links API derives its data from:
1. Agent frontmatter `skills:` field (explicit references)
2. Content markers in agent body text
3. Inferred relationships

Problems:
- **Stale references**: Agents reference skill names like `"dspy"` but skills deploy with normalized names like `"toolchains-ai-frameworks-dspy"`. The matching is done by suffix, which could produce false positives.
- **Content markers are fragile**: Inferring skill-agent relationships from text content is pattern-matching, not explicit declaration. It can miss real relationships or create false ones.
- **No validation against actual deployment**: The skill-links data shows what agents WANT, not what's actually deployed and active. A skill could be "linked" but not deployed, creating confusion.

---

## Part 2: What Users ACTUALLY Need

### 2.1 The User's Mental Model

Users interact with agents and skills in this decision flow:

```
1. "What agents are available?" → Browse/discover
2. "What does this agent do?" → Understand capabilities
3. "Should I deploy it?" → Evaluate fit for my project
4. "Is it working?" → Monitor deployment status
5. "What skills does it need?" → Dependency management
```

The current UI supports steps 1, 3 (partially), and 4. Steps 2 and 5 are poorly served.

### 2.2 Information Hierarchy (What Matters for Decision-Making)

**CRITICAL (must see at a glance in list view)**:
| Field | Why | Available Today? |
|-------|-----|:---:|
| Name | Identity | Yes |
| Description (1 line) | Purpose | Available agents only |
| Deployed/Not badge | Status | Yes |
| Category group header | Organization | Frontend-only fix |

**IMPORTANT (should see in list, not just detail)**:
| Field | Why | Available Today? |
|-------|-----|:---:|
| Tags (top 3) | Quick filtering | Available agents only |
| Resource tier | Impact awareness | No |
| Network access | Security awareness | No |
| Skills count | Dependency complexity | No |

**DETAIL VIEW (only when user clicks)**:
| Field | Why | Available Today? |
|-------|-----|:---:|
| Full description | Deep understanding | Partial |
| Domain expertise | Capability assessment | No |
| Dependencies | Setup requirements | No |
| Handoff agents | Collaboration context | No |
| Temperature | Behavior tuning | No |
| Changelog | Maturity assessment | No |
| Constraints | Limitations | No |

**POWER USER (hide behind "Advanced" toggle)**:
| Field | Why |
|-------|-----|
| Memory/CPU limits | Resource planning |
| Schema version | Compatibility |
| Collection/canonical ID | Source tracing |
| Memory routing | System behavior |

### 2.3 What Should NOT Be Shown (Counter to Researcher Recommendations)

The researchers recommend showing everything. I disagree. These fields would **confuse** users:

1. **`max_tokens`**: Users don't understand what 4096 vs 16384 means. It's an internal config, not a user-facing feature. Showing it creates anxiety ("is 4096 enough?") without actionable information.

2. **`cpu_limit`**: A percentage value (10-100) with no user-controllable behavior. Showing 50% CPU limit tells a user nothing actionable.

3. **`memory_limit` (in MB)**: Unless the user is deploying to a resource-constrained environment, this is noise. Most users don't reason in megabytes of memory for AI agents.

4. **`schema_version`**: Internal compatibility tracking. If a schema mismatch causes problems, the validation panel should flag it. Users shouldn't need to mentally track schema versions.

5. **`template_version` + `template_changelog`**: The agent researcher rates this HIGH value, but changelog entries like *"Architecture Enhancement: Added comprehensive guidance..."* are meaningless to a user deciding whether to deploy an agent. Version comparison (2.3.0 vs 2.5.0) tells you nothing without understanding what changed in user-facing terms.

6. **`memory_routing`**: Internal system plumbing. The description "Stores testing strategies, quality standards, and bug patterns" is developer-facing, not user-facing.

7. **`interactions.output_format`**: Whether an agent outputs "markdown" or "structured" is an implementation detail. Users care about what the agent DOES, not what format it outputs.

---

## Part 3: Concrete UI Proposals

### 3.1 Layout: Cards with Progressive Detail (NOT Tables)

**Rationale against tables**: Tables work for homogeneous data with consistent columns. Agents and skills have wildly varying metadata completeness (some have 30 fields, some have 7). A table with mostly-empty columns wastes space and looks broken.

**Rationale against pure cards**: Standard cards show too little in too much space. With 45+ agents, card grids require excessive scrolling.

**Proposed: Compact card list with expandable detail**:

```
┌─────────────────────────────────────────────────────────┐
│ [Search...🔍]  [Category ▾]  [Status ▾]  [Sort ▾]     │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ ── Engineering (12 agents) ──────────────────────────── │
│                                                         │
│ ┌─ 🟢 Python Engineer ──── v2.3.0 ── [Deployed ✓] ──┐ │
│ │  Python 3.12+ specialist: type-safe, async-first... │ │
│ │  ▸ python · async · SOA          🌐 standard       │ │
│ └─────────────────────────────────────────────────────┘ │
│                                                         │
│ ┌─ 🟢 Rust Engineer ────── v2.3.0 ── [Deploy →] ────┐ │
│ │  Rust 2024 edition: memory-safe, zero-cost...       │ │
│ │  ▸ rust · async · tokio          🌐 standard       │ │
│ └─────────────────────────────────────────────────────┘ │
│                                                         │
│ ── Quality (5 agents) ──────────────────────────────── │
│                                                         │
│ ┌─ 🟢 QA ──────────────── v3.5.3 ── [Deployed ✓] ──┐ │
│ │  Memory-efficient testing with strategic sampling.. │ │
│ │  ▸ qa · testing · validation     🔒 standard       │ │
│ └─────────────────────────────────────────────────────┘ │
│                                                         │
│ ┌─ 🔴 Security ─────────── v2.1.0 ── [Deploy →] ────┐ │
│ │  Advanced security scanning with SAST, attack...    │ │
│ │  ▸ security · OWASP · SAST      🌐 standard       │ │
│ └─────────────────────────────────────────────────────┘ │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

Key design decisions:
- **Color dot** (🟢🔴🟣) from agent `color` field replaces boring text badge (falls back to gray if missing)
- **Description visible in list** (truncated to 1 line) - most critical missing feature today
- **Tags shown inline** (max 3, with `...` overflow indicator)
- **🌐/🔒 icon** for network access (security-relevant, immediately visible)
- **Resource tier** shown as text label (standard/intensive/lightweight)
- **Category group headers** with collapsible sections
- **Deployed/Deploy button** is the primary action, right-aligned

### 3.2 Detail Panel (Right Side) Design

When clicking an agent/skill, the right panel should show:

```
┌─────────────────────────────────────────────┐
│ 🟢 Python Engineer                   v2.3.0 │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│                                              │
│ Python 3.12+ development specialist:         │
│ type-safe, async-first, production-ready     │
│ implementations with SOA and DI patterns     │
│                                              │
│ ┌──────────┬──────────┬──────────┐          │
│ │ Category │ Tier     │ Network  │          │
│ │ engineer │ standard │ ✓ Yes    │          │
│ └──────────┴──────────┴──────────┘          │
│                                              │
│ ▸ Expertise (click to expand)               │
│   • Python 3.12-3.13 features               │
│   • Service-oriented architecture            │
│   • Async/await patterns                     │
│                                              │
│ ▸ Skills (18 linked)                        │
│   [pytest] [mypy] [pydantic] [git-workflow]  │
│   [test-driven-development] ...+13           │
│                                              │
│ ▸ Dependencies                              │
│   Python: black, isort, mypy, pytest         │
│   System: python3.12+, git                   │
│                                              │
│ ▸ Collaborates With                         │
│   → qa (handoff)                            │
│   → security (handoff)                      │
│   → data_engineer (handoff)                 │
│                                              │
│ ▸ Constraints                               │
│   • Max 5-10 test files per session          │
│   • Skip files >500KB                        │
│                                              │
│ ─────────────────────────────────────        │
│ Source: bobmatnyc/claude-mpm-agents           │
│ Temperature: 0.2 (precise)                   │
│ Timeout: 900s                                │
│                                              │
│        [Deploy]  or  [Undeploy ⚠]            │
└──────────────────────────────────────────────┘
```

Key decisions:
- **Expandable sections** (expertise, skills, dependencies, collaborators) - don't load everything at once
- **Skills shown as chips** with deployment indicators (green = deployed, gray = not deployed)
- **Collaborators** from handoff_agents - shows who this agent works with
- **Temperature** rendered as semantic label: 0.0 = "precise", 0.1-0.3 = "focused", 0.4-0.7 = "balanced", 0.8-1.0 = "creative"
- **Source and technical details** at bottom (secondary information)

### 3.3 Skills List - Adjusted Design

Skills need different treatment than agents because of the `toolchain` hierarchy:

```
┌─────────────────────────────────────────────────────────┐
│ [Search...🔍]  [Toolchain ▾]  [Status ▾]  Mode: [Sel.] │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ ── Universal (37 skills) ────────────────────────────── │
│                                                         │
│ ┌─ brainstorming ──────── v1.0.0 ── [Deployed ✓] ───┐ │
│ │  Interactive idea refinement using Socratic method  │ │
│ │  ▸ debugging · frontend        649 tokens   🔗 30  │ │
│ └─────────────────────────────────────────────────────┘ │
│                                                         │
│ ── AI (9 skills) ────────────────────────────────────── │
│                                                         │
│ ┌─ dspy ───────────────── v1.0.0 ── [Deploy →] ─────┐ │
│ │  Declarative framework for prompt optimization     │ │
│ │  ▸ ai · llm · rag           10,191 tokens   🔗 5  │ │
│ └─────────────────────────────────────────────────────┘ │
│                                                         │
│ ── Python (10 skills) ───────────────────────────────── │
│ ...                                                     │
└─────────────────────────────────────────────────────────┘
```

Key differences from agents:
- **Toolchain as primary grouping** (not the useless binary `category`)
- **Token count shown** (size indicator: helps users understand impact)
- **🔗 N** = number of agents that reference this skill (from skill-links API)
- **Mode indicator** in header (Selective/Full deployment mode)
- **No color dot** - skills don't have a color field

### 3.4 Search and Filter Design

**Filters that ACTUALLY help users**:

| Filter | Source | Why Useful |
|--------|--------|------------|
| Category (agents) | `category` field | Group by role (engineer, qa, ops) |
| Toolchain (skills) | `toolchain` field | Group by language/platform |
| Deployment status | `is_deployed` | "Show me what I have" vs "what's available" |
| Network access (agents) | `capabilities.network_access` | Security filtering |
| Resource tier (agents) | `resource_tier` | "Show me lightweight agents" |

**Filters that would NOT help**:
- Tag filter: With 15-30 tags per agent, a tag dropdown would have 100+ options and be unusable
- Author filter: Only 2 authors in the entire system (`bobmatnyc`, `Claude MPM Team`)
- Version filter: Version ranges don't make sense for filtering agents
- Schema version: Internal, not user-facing

**Better than tag filter**: Free-text search that searches across name, description, AND tags. Tags improve search relevance without needing their own dedicated filter.

### 3.5 Agent-Skill Relationship Visualization

Instead of the current separate "Skill Links" tab, integrate relationships into both agent and skill detail panels:

**In Agent Detail**: Show skills as chips grouped by link type:
```
Skills (18 total)
  Required: [pytest ✓] [mypy ✓] [pydantic ✗] [git-workflow ✓]
  Inferred: [test-driven-development ✓] [systematic-debugging ✓]

  ✓ = deployed, ✗ = not deployed
  "3 required skills not deployed" warning if applicable
```

**In Skill Detail**: Show agents that reference it:
```
Used by (12 agents)
  python-engineer, java-engineer, rust-engineer, golang-engineer,
  ruby-engineer, php-engineer, typescript-engineer, ...
```

This bidirectional view replaces the need for a separate Skill Links tab entirely.

---

## Part 4: Risks and Pitfalls

### 4.1 Performance: Loading All Metadata for 45+ Agents

**Risk**: If the deployed agents endpoint is enriched to return frontmatter fields (color, description, tags, skills, dependencies, knowledge), every page load triggers:
- 15-20 file reads (deployed agents)
- 15-20 YAML parses
- 45+ manifest lookups (available agents)
- 156 skill lookups (available skills)

**Mitigation**:
1. **Cache frontmatter at deployment time**: When an agent is deployed, extract key frontmatter fields and store them in a `.deployment_index.json` (similar to skills' deployment index). This is a one-time cost at deploy time, not every page load.
2. **Paginate available agents**: Currently no pagination on the agents list. Add it.
3. **Lazy load detail metadata**: Only fetch expertise, changelog, dependencies when a user clicks an agent (not for the list view).

### 4.2 Stale Data Risk

**Risk**: Agent definitions in the repository can change (new version, updated skills list) without the deployed copy being updated. The dashboard could show outdated metadata.

**Mitigation**:
- Show "version mismatch" badge if deployed version differs from latest available
- Never trust deployed file metadata for dynamic fields (skills list may have changed)
- Use source-of-truth hierarchy: available endpoint > deployed file > cached data

### 4.3 Information Overload

**Risk**: The researchers recommend exposing 20+ new fields. Showing all of them turns the UI into a data dump.

**Mitigation**: Strict progressive disclosure:
- **Level 0 (list)**: 5-6 fields max (name, description, status, category, top tags)
- **Level 1 (detail panel)**: 10-12 fields (add expertise, skills, dependencies, collaborators)
- **Level 2 (expandable sections)**: Everything else (changelog, constraints, memory routing)
- **Level 3 (raw view)**: Link to source file for power users

### 4.4 API Changes Impact

**Risk**: Enriching the deployed agents endpoint requires backend changes that could break existing consumers.

**Mitigation**:
- Add new fields alongside existing ones (backward-compatible)
- For the available skills endpoint, the data is ALREADY being sent - just update the frontend interface
- Consider a v2 endpoint pattern if the response shape changes significantly

### 4.5 Edge Cases

| Edge Case | Risk | Handling |
|-----------|------|----------|
| Agent without color | Missing visual indicator | Default to `gray` dot |
| Agent without skills list | Empty skills section | Show "No skills defined" |
| Skill without description | Empty description line | Show `when_to_use` fallback, then "No description" |
| Agent with 31 tags | Tag overflow in UI | Show first 3 + "+N more" |
| Skill with 0 tokens | Invalid token count | Hide token indicator |
| metadata.json not accessible | Missing rich skill data | Degrade to manifest-only data |
| Deployed agent not in available list | Can't cross-reference | Show deployed data only, flag as "unknown source" |
| Circular skill dependencies | `requires` graph cycle | Don't build a graph; just show flat list |
| 156 skills in list view | Performance, scrolling | Virtual scrolling + pagination |

### 4.6 What Could Go Wrong With Each Proposal

| Proposal | What Could Go Wrong |
|----------|-------------------|
| Color dots in list | Users think colors are semantic (red=error) when they're just identifiers |
| Category grouping | Some agents are miscategorized (Security is in "quality") - leads to confusion |
| Token count for skills | Users don't understand tokens; showing "10,191 tokens" is meaningless to most |
| Handoff graph | Graph becomes unreadable with 39 agents having relationships |
| Expandable sections in detail | Users miss important info because it's collapsed |
| Toolchain filter for skills | "Universal" skills don't fit the toolchain mental model |
| Skills count badge on agents | Count changes based on link type; which count to show? |

---

## Part 5: Prioritized Recommendations

### Immediate (Frontend-Only, No Backend Changes)

1. **Update `AvailableSkill` TypeScript interface** to include `version`, `toolchain`, `framework`, `tags`, `entry_point_tokens`, `full_tokens`, `requires`, `author`, `updated`, `source_path` - the API already sends these
2. **Add category grouping** to agents list - data already available for available agents
3. **Add toolchain grouping** to skills list - data already in API response
4. **Add sort controls** - sort by name, version, deployment status
5. **Show description in available agents list** - data already there, just truncated differently

### Short-term (Backend + Frontend)

6. **Enrich deployed agents endpoint** with frontmatter fields: `description`, `category`, `color`, `tags`, `resource_tier`, `network_access`, `skills` (list of names only). Cache at deploy time.
7. **Add `color` field to available agents endpoint** - read from frontmatter during cache scan
8. **Add deployment index for agents** (analogous to skills' `.deployment_index.json`)
9. **Merge Skill Links into agent/skill detail panels** instead of separate tab

### Medium-term (Significant Work)

10. **Build agent detail panel with progressive disclosure** (expertise, skills, dependencies, collaborators)
11. **Add skill detail panel with when_to_use, linked agents, and dependency info**
12. **Implement category/toolchain/status filters**
13. **Add version mismatch detection** between deployed and available
14. **Virtual scrolling** for 45+ agent and 156+ skill lists

### Deferred (Low ROI or High Risk)

15. Agent relationship graph visualization (complex, low user value)
16. Skill dependency graph (few skills have `requires`)
17. Template changelog display (low user value)
18. Performance benchmarks from metadata.json (too sparse, too specialized)

---

## Part 6: Summary of Contradictions and Errors Found

| Issue | Researcher | Finding |
|-------|-----------|---------|
| Color is "universally defined" | Agent Research | FALSE: 3 agents missing color (6%) |
| handoff_agents is QA-specific | Agent Research | FALSE: 78% of agents have it |
| `get_agent_metadata()` exists | Agent Research | FALSE: Method doesn't exist |
| Skill gaps all need backend work | Skill Research | FALSE: 7+ fields already sent by API, just not used by frontend |
| `category` useful for skill filtering | Skill Research | MISLEADING: Binary universal/toolchain split is useless; `toolchain` is the real filter |
| Backend is Flask/FastAPI | CLAUDE.md | FALSE: Backend is aiohttp (dashboard researcher correctly noted this) |
| Two Badge components noted | Dashboard Research | CORRECT: Verified - genuine inconsistency needing resolution |
| Deployed agents "severely under-described" | Agent Research | CORRECT but UNDERSTATED: Gap is worse than described |

---

## Appendix: Quick Reference - What to Show Where

### Agent List Item (5-6 fields)
```
[color-dot] [Name] ─── [version] ─── [Deployed ✓ / Deploy →]
[description truncated to ~80 chars]
[tag] [tag] [tag]       [🌐/🔒] [resource_tier]
```

### Agent Detail Panel (10-12 fields + expandable)
- Name, version, description (full)
- Category, resource tier, network access
- ▸ Expertise (expandable list)
- ▸ Skills (chip list with deploy status)
- ▸ Dependencies (grouped by type)
- ▸ Collaborates With (handoff agents)
- ▸ Constraints (limitations)
- Source, temperature, timeout (footer)

### Skill List Item (5-6 fields)
```
[Name] ─── [version] ─── [Deployed ✓ / Deploy →]
[description or when_to_use]
[tag] [tag] [tag]       [N tokens]  [🔗 M agents]
```

### Skill Detail Panel (8-10 fields + expandable)
- Name, version, description
- Category/toolchain, author, updated date
- ▸ When to Use (trigger condition)
- ▸ Used By (agent list)
- ▸ Dependencies (requires field)
- ▸ Related Skills (if available)
- Token count, source path
- Deploy mode, deploy date (if deployed)
