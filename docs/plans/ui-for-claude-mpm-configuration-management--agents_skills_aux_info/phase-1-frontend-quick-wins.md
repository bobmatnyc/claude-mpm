# Phase 1: Frontend-Only Quick Wins — Implementation Plan

## Revision History
- **v1 (2026-02-14)**: Initial draft
- **v2 (2026-02-14)**: Revised based on devil's advocate review. Key changes: added fallback defaults for missing/malformed fields (R8), strengthened dark mode audit criteria (R12), added `category` vs `collection` clarification (R11), added edge case handling for `tags: []` vs `undefined`, added performance and accessibility acceptance criteria.

**Date**: 2026-02-14
**Status**: Implementation-Ready
**Scope**: Frontend-only changes to the SvelteKit dashboard — zero backend modifications
**Target Files**: All under `src/claude_mpm/dashboard-svelte/src/lib/`
**Branch**: `ui-agents-skills-config`

---

## Verification Amendments (Cross-Cutting)

> The following amendments were added after Verification Pass 1 (VP-1) identified HIGH and MODERATE severity issues across the Phase 1-3 plan set. See `docs/research/.../verification-pass-1/` for the full analysis.

### VP-1-A: Deployment Ordering

Phase 1 can be deployed independently of Phases 2 and 3. However, Phase 1 expands TypeScript interfaces (e.g., `AvailableSkill` from 5 to 15 fields, `DeployedAgent` with optional enrichment fields) that will contain `undefined` values until Phase 2 backend enrichment is deployed. All frontend code in Phase 1 **MUST** handle `undefined`/missing fields gracefully using:

- Nullish coalescing (`??`, `|| ''`, `|| []`, `|| 0`)
- Optional chaining (`?.`)
- Explicit `{#if field}` guards in Svelte templates
- The `?:` (optional) modifier on all new TypeScript interface fields

Svelte 5 `$derived` computations that consume these fields (e.g., sort-by-version, group-by-toolchain, tag-based search) must NOT crash or produce incorrect results when fields are `undefined`. Specifically:
- `sortItems()` version comparator must treat `undefined`/`''` versions as sorting to the end
- `groupedAvailable` toolchain grouping must treat `undefined` toolchain the same as `null` (group under "Universal")
- Tag-based search filters must guard with `(skill.tags ?? [])` not just `skill.tags || []`

### VP-1-B: Integration Testing Requirement

> **Verification Amendment (VP-1)**: Mocked tests in `tests/test_config_routes.py` use `unittest.mock.MagicMock` for ALL services, which cannot catch type mismatches or data flow errors between the backend and frontend interfaces. Phase 1 must include verification against real API responses, not just TypeScript compilation.

For each step, add this to the testing checklist:
1. **API response verification**: With the dev server running, use browser DevTools or `curl` to fetch the actual API response from `/api/config/skills/available` and `/api/config/agents/available`. Confirm that the fields declared in the expanded TypeScript interfaces are present in the JSON with expected types and non-null values.
2. **Store data verification**: In browser console, inspect the Svelte store values after fetch to confirm new fields propagate correctly through the store layer.
3. **Graceful degradation check**: Temporarily remove a field from the API response (e.g., simulate Phase 2 not yet deployed) and verify the frontend does not crash or show broken UI.

---

## Prerequisites and Assumptions

### Prerequisites
1. Node.js environment for building the SvelteKit dashboard (`dashboard-svelte/`)
2. The built output is copied to `dashboard/static/svelte-build/` for the Python server to serve
3. Familiarity with **Svelte 5 Runes API** (`$state`, `$derived`, `$effect`, `$props`) — the codebase uses this exclusively
4. Familiarity with **Tailwind CSS** — all styling uses Tailwind utility classes

### Assumptions
1. The available skills API (`GET /api/config/skills/available`) already returns 12+ fields per skill (verified via research). The frontend `AvailableSkill` interface simply ignores 7+ of them.
2. The available agents API (`GET /api/config/agents/available`) already returns `category` and `tags` fields that can be used for grouping.
3. No backend changes are needed for any step in this plan.
4. The existing Svelte 4/5 bridge pattern (`$effect(() => store.subscribe(...))`) will be maintained for consistency.

### Key File Paths

| File | Purpose |
|------|---------|
| `src/lib/stores/config.svelte.ts` | TypeScript interfaces + Svelte stores + fetch functions |
| `src/lib/components/config/AgentsList.svelte` | Agent list component (deployed + available sections) |
| `src/lib/components/config/SkillsList.svelte` | Skill list component (deployed + available sections) |
| `src/lib/components/config/ConfigView.svelte` | Master config view with detail panel rendering |
| `src/lib/components/Badge.svelte` | Text-prop Badge (used in Config tab) |
| `src/lib/components/shared/Badge.svelte` | Snippet-children Badge (used elsewhere) |
| `src/lib/components/SearchInput.svelte` | Debounced search input |

All paths below are relative to `src/claude_mpm/dashboard-svelte/`.

---

## Step 1: Update `AvailableSkill` TypeScript Interface

### What
Expand the `AvailableSkill` interface from 5 fields to 15 fields to capture all data the API already sends but the frontend currently discards.

### Where
`src/lib/stores/config.svelte.ts` — lines 47-53

### How

1. Open `src/lib/stores/config.svelte.ts`
2. Locate the `AvailableSkill` interface (currently lines 47-53)
3. Replace with the expanded interface:

```typescript
export interface AvailableSkill {
    name: string;
    description: string;
    category: string;
    collection: string;
    is_deployed: boolean;
    // Fields the API already sends but were previously ignored:
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

4. No changes needed to `fetchAvailableSkills()` — it already calls `availableSkills.set(data.skills)` which will automatically include the new fields since TypeScript interfaces are structural.

### Why
The API sends 12+ fields per skill. The frontend TypeScript interface only captures 5, silently discarding `version`, `toolchain`, `framework`, `tags`, `entry_point_tokens`, `full_tokens`, `requires`, `author`, `updated`, and `source_path`. This is the single highest-ROI change identified in the research — it unlocks 10 data fields with zero backend work.

### Edge Cases

> **[REVISED]** Added explicit fallback defaults for every new field to address R8 (missing/malformed metadata handling).

- **Missing fields in API response**: Some fields may be `null` or missing for edge-case skills. Use `string | null` for `toolchain` and `framework` since universal skills have `null` for both. Arrays like `tags` and `requires` may be empty `[]` but should never be undefined (manifest guarantees them).
- **Fallback defaults for each new field**:
  | Field | Fallback | Reasoning |
  |-------|----------|-----------|
  | `version` | `""` | Guard with `{#if skill.version}` in templates |
  | `toolchain` | `null` | Universal skills have `null`; show "Universal" label |
  | `framework` | `null` | Same as toolchain |
  | `tags` | `[]` | Empty array; hide tags section |
  | `entry_point_tokens` | `0` | Hide token indicator when 0 |
  | `full_tokens` | `0` | Hide token indicator when 0 |
  | `requires` | `[]` | Hide dependencies section |
  | `author` | `""` | Hide author field |
  | `updated` | `""` | Hide updated field |
  | `source_path` | `""` | Hide source path field |
- **Backward compatibility**: Adding optional fields to an interface is backward-compatible — existing code that only reads the original 5 fields will continue to work unchanged.

### Acceptance Criteria
- [ ] `AvailableSkill` interface has all 15 fields
- [ ] TypeScript compiles without errors
- [ ] Available skills data in the store includes the new fields when inspected in browser DevTools
- [ ] Existing skill list rendering is unchanged (no visual regressions)
- [ ] All new fields have documented fallback defaults (see table above)

### Dependencies
None — this is the foundational step that all subsequent skill-related steps depend on.

### Estimated Complexity
**Small** — Interface-only change, no rendering logic.

---

## Step 2: Add Sort Controls to AgentsList and SkillsList

### What
Add a sort dropdown to both the agents and skills lists, allowing users to sort by name (A-Z, Z-A), version, or deployment status.

### Where
- `src/lib/components/config/AgentsList.svelte`
- `src/lib/components/config/SkillsList.svelte`

### How

1. **Add sort state and logic to AgentsList.svelte**:

   After the `searchQuery` state declaration (line 22), add:
   ```typescript
   type SortOption = 'name-asc' | 'name-desc' | 'version' | 'status';
   let sortBy = $state<SortOption>('name-asc');

   function sortItems<T extends { name: string }>(items: T[], sort: SortOption, getVersion?: (item: T) => string, getDeployed?: (item: T) => boolean): T[] {
       const sorted = [...items];
       switch (sort) {
           case 'name-asc':
               return sorted.sort((a, b) => a.name.localeCompare(b.name));
           case 'name-desc':
               return sorted.sort((a, b) => b.name.localeCompare(a.name));
           case 'version':
               return sorted.sort((a, b) => (getVersion?.(b) || '').localeCompare(getVersion?.(a) || ''));
           case 'status':
               return sorted.sort((a, b) => {
                   const aDeployed = getDeployed?.(a) ? 1 : 0;
                   const bDeployed = getDeployed?.(b) ? 1 : 0;
                   return bDeployed - aDeployed;
               });
           default:
               return sorted;
       }
   }
   ```

2. **Update `filteredDeployed` and `filteredAvailable` derived values** to apply sorting after filtering:

   ```typescript
   let filteredDeployed = $derived(
       sortItems(
           searchQuery
               ? deployedAgents.filter(a => a.name.toLowerCase().includes(searchQuery.toLowerCase()))
               : deployedAgents,
           sortBy,
           (a) => a.version
       )
   );

   let filteredAvailable = $derived(
       sortItems(
           searchQuery
               ? availableAgents.filter(a =>
                   a.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                   (a.description || '').toLowerCase().includes(searchQuery.toLowerCase())
               )
               : availableAgents,
           sortBy,
           (a) => a.version,
           (a) => a.is_deployed
       )
   );
   ```

3. **Add sort dropdown UI** in the search bar area. Place it next to the `SearchInput` in the top `div`:

   ```svelte
   <div class="p-3 border-b border-slate-200 dark:border-slate-700 space-y-2">
       <SearchInput
           value={searchQuery}
           placeholder="Search agents..."
           onInput={(v) => searchQuery = v}
       />
       <div class="flex items-center gap-2">
           <span class="text-xs text-slate-500 dark:text-slate-400">Sort:</span>
           <select
               bind:value={sortBy}
               class="text-xs bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-md px-2 py-1 text-slate-700 dark:text-slate-300 focus:outline-none focus:ring-1 focus:ring-cyan-500"
           >
               <option value="name-asc">Name (A-Z)</option>
               <option value="name-desc">Name (Z-A)</option>
               <option value="version">Version</option>
               <option value="status">Deploy Status</option>
           </select>
       </div>
   </div>
   ```

4. **Repeat the same pattern for SkillsList.svelte** with the same sort types. For skills, add the sort dropdown between the mode header and search input.

5. For SkillsList, also include tags in the search filter now that the interface has them:

   ```typescript
   let filteredAvailable = $derived(
       sortItems(
           searchQuery
               ? availableSkills.filter(s =>
                   s.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                   (s.description || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
                   (s.tags || []).some(t => t.toLowerCase().includes(searchQuery.toLowerCase()))
               )
               : availableSkills,
           sortBy,
           (s) => s.version,
           (s) => s.is_deployed
       )
   );
   ```

### Why
Research finding: "Neither agents nor skills lists have sort controls. Items are displayed in the order returned by the API with no client-side sorting options." With 45+ agents and 156+ skills, sorting is essential for finding items.

### Edge Cases
- **Null versions**: Some items may have empty or missing version strings. The `localeCompare` handles empty strings gracefully (sorts to beginning).
- **Same name across deployed/available**: Sort applies independently to each section (deployed and available are separate lists).
- **Sort persistence**: Sort resets on component re-render. This is acceptable for Phase 1; persistent sort could be added later via localStorage.

### Acceptance Criteria
- [ ] Both AgentsList and SkillsList have a sort dropdown
- [ ] Sort dropdown has options: Name (A-Z), Name (Z-A), Version, Deploy Status
- [ ] Selecting a sort option immediately re-orders the list
- [ ] Sort applies independently to both Deployed and Available sections
- [ ] Default sort is Name (A-Z)
- [ ] Sort dropdown matches existing Tailwind dark mode styling
- [ ] Sort dropdown has `aria-label="Sort order"` for screen readers

### Dependencies
Step 1 (for skill `version` field in sort-by-version)

### Estimated Complexity
**Medium** — Same pattern applied twice, requires UI and logic changes.

---

## Step 3: Add Toolchain Grouping to SkillsList

### What
Group available skills by their `toolchain` field instead of the binary `category` field. Skills with `toolchain: null` (universal skills) are grouped under "Universal". Toolchain skills are grouped under their toolchain name (ai, python, javascript, etc.).

> **[REVISED]** Previously proposed grouping by `category`, changed to `toolchain` because the `category` field is binary (`universal` vs `toolchains`) and useless for grouping 156 skills (R11). The `toolchain` field provides 15+ distinct values.

### Where
`src/lib/components/config/SkillsList.svelte`

### How

1. **Add a grouping toggle state** after the sort state:

   ```typescript
   let groupByToolchain = $state(true);
   ```

2. **Create a derived grouped structure** for available skills:

   ```typescript
   interface SkillGroup {
       name: string;
       skills: AvailableSkill[];
   }

   let groupedAvailable = $derived<SkillGroup[]>(() => {
       const skills = filteredAvailable;
       if (!groupByToolchain) {
           return [{ name: 'All Skills', skills }];
       }

       const groups = new Map<string, AvailableSkill[]>();
       for (const skill of skills) {
           const key = skill.toolchain || 'Universal';
           if (!groups.has(key)) groups.set(key, []);
           groups.get(key)!.push(skill);
       }

       // Sort groups: "Universal" first, then alphabetically
       const sorted: SkillGroup[] = [];
       if (groups.has('Universal')) {
           sorted.push({ name: 'Universal', skills: groups.get('Universal')! });
           groups.delete('Universal');
       }
       for (const [name, skills] of [...groups.entries()].sort((a, b) => a[0].localeCompare(b[0]))) {
           sorted.push({ name: name.charAt(0).toUpperCase() + name.slice(1), skills });
       }
       return sorted;
   });
   ```

3. **Update the Available Skills section rendering** to iterate over groups:

   Replace the flat `{#each filteredAvailable as skill}` block in the Available section with:

   ```svelte
   {#each groupedAvailable as group (group.name)}
       <!-- Group header -->
       <div class="px-4 py-1.5 bg-slate-100/50 dark:bg-slate-800/30 border-b border-slate-100 dark:border-slate-700/50">
           <span class="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">
               {group.name} ({group.skills.length})
           </span>
       </div>
       {#each group.skills as skill (skill.name)}
           <!-- existing skill item rendering, unchanged -->
       {/each}
   {/each}
   ```

4. **Add a grouping toggle button** next to the sort dropdown:

   ```svelte
   <button
       onclick={() => groupByToolchain = !groupByToolchain}
       class="text-xs px-2 py-1 rounded-md transition-colors
           {groupByToolchain
               ? 'bg-cyan-500/20 text-cyan-400'
               : 'bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-300'}"
       title={groupByToolchain ? 'Disable grouping' : 'Group by toolchain'}
       aria-pressed={groupByToolchain}
   >
       Group
   </button>
   ```

### Why
Research finding: "The manifest `category` field has only two values: `'universal'` and `'toolchains'`. This binary split is useless for filtering 156 skills. The `toolchain` field (`ai`, `python`, `javascript`, `rust`, etc.) is the actual useful grouping dimension."

The `toolchain` field is now available in the `AvailableSkill` interface (from Step 1) and provides 15+ distinct values for meaningful grouping.

### Edge Cases
- **`toolchain: null`**: Universal skills have `toolchain: null`. These are grouped under "Universal" header.
- **Search + grouping**: When searching, groups may become empty. Empty groups should be automatically excluded since they'd have 0 matching skills.
- **Single-item groups**: Some toolchains (e.g., `databases`) may have only 1 skill. This is fine — the group header still provides useful context.
- **Sort within groups**: Items within each group respect the active sort order.
- **`collection` field vs `category` field**: Use `toolchain` for grouping (not `collection` or `category`). `collection` identifies the source repo, not a semantic group.

### Acceptance Criteria
- [ ] Available skills are grouped by toolchain with section headers showing group name and count
- [ ] "Universal" group appears first, then alphabetically
- [ ] A "Group" toggle button exists to enable/disable grouping
- [ ] Grouping is enabled by default
- [ ] Search works correctly with grouping (filters across all groups, hides empty groups)
- [ ] Group headers use consistent styling with existing Deployed/Available section headers but visually subordinate (slightly lighter)

### Dependencies
Step 1 (requires `toolchain` field in `AvailableSkill`)

### Estimated Complexity
**Medium** — Requires derived grouping logic and template restructuring.

---

## Step 4: Add Category Grouping to AgentsList

### What
Group available agents by their `category` field (engineering, quality, operations, etc.) with collapsible group headers showing counts.

### Where
`src/lib/components/config/AgentsList.svelte`

### How

1. **Add grouping state and derived structure** (same pattern as Step 3):

   ```typescript
   let groupByCategory = $state(true);

   interface AgentGroup {
       name: string;
       agents: AvailableAgent[];
   }

   let groupedAvailable = $derived<AgentGroup[]>(() => {
       const agents = filteredAvailable;
       if (!groupByCategory) {
           return [{ name: 'All Agents', agents }];
       }

       const groups = new Map<string, AvailableAgent[]>();
       for (const agent of agents) {
           const key = agent.category || 'Uncategorized';
           if (!groups.has(key)) groups.set(key, []);
           groups.get(key)!.push(agent);
       }

       // Sort groups alphabetically, capitalize first letter
       return [...groups.entries()]
           .sort((a, b) => a[0].localeCompare(b[0]))
           .map(([name, agents]) => ({
               name: name.charAt(0).toUpperCase() + name.slice(1),
               agents,
           }));
   });
   ```

2. **Update Available section rendering** to iterate over groups (same pattern as Step 3's skill groups but for agents).

3. **Add "Group" toggle button** in the search/sort bar.

### Why
Research finding: "No Filtering by Category/Tag: Available agents have `category` and `tags` fields... None of these have filter UI." The `category` field for agents provides meaningful grouping (engineering, quality, operations, etc.) with 7 distinct values.

### Edge Cases
- **Missing category**: Very unlikely for available agents (the API includes category from frontmatter), but if it happens, group under "Uncategorized".
- **Security agent miscategorized**: The Security agent has `category: "quality"`. This is a data issue, not a UI issue — the UI correctly displays what the API returns.
- **"claude-mpm" category**: System agents (mpm-agent-manager, mpm-skills-manager) have `category: "claude-mpm"`. This will display as "Claude-mpm" which is acceptable.

### Acceptance Criteria
- [ ] Available agents are grouped by category with section headers
- [ ] Groups are sorted alphabetically
- [ ] Each group header shows category name and agent count
- [ ] A "Group" toggle exists to enable/disable
- [ ] Grouping is enabled by default
- [ ] Existing search and sort work correctly with grouping

### Dependencies
Step 2 (sort controls should be in place)

### Estimated Complexity
**Medium** — Mirrors Step 3's pattern for agents.

---

## Step 5: Display Version Badge in Available Skills List

### What
Show a version badge (e.g., "v1.0.0") next to each available skill name in the list view.

### Where
`src/lib/components/config/SkillsList.svelte` — Available skills section item rendering (~line 278)

### How

1. In the available skill item rendering, after the deployed checkmark and category badge, add a version badge:

   ```svelte
   <div class="flex items-center gap-2">
       <span class="font-medium text-slate-900 dark:text-slate-100 truncate">{skill.name}</span>
       {#if skill.is_deployed}
           <svg class="w-4 h-4 text-green-500 flex-shrink-0" ...>...</svg>
       {/if}
       {#if skill.version}
           <Badge text="v{skill.version}" variant="default" />
       {/if}
       {#if skill.toolchain}
           <Badge text={skill.toolchain} variant="info" />
       {:else if skill.category}
           <Badge text={skill.category} variant="default" />
       {/if}
   </div>
   ```

   > **[REVISED]** Replace `category` badge with `toolchain` badge when available, since `category` only shows "universal" or "toolchains" (useless binary value per R11).

### Why
Version visibility helps users understand skill maturity and track updates. The data is already available from Step 1's interface expansion.

### Edge Cases
- **All skills are v1.0.0**: Currently true for all skills in the manifest. The badge still provides value as a visual indicator and will become useful as skills evolve to v1.1.0+.
- **Missing version**: Extremely unlikely (manifest guarantees it), but guard with `{#if skill.version}`.
- **Long semver strings**: "1.0.0-beta.2+build.123" — Badge truncates naturally via CSS; consider limiting display to major.minor.patch only.

### Acceptance Criteria
- [ ] Each available skill shows a "vX.Y.Z" badge in the list
- [ ] Badge uses the existing `default` variant styling
- [ ] Toolchain badge shown instead of category badge where `toolchain` is non-null
- [ ] Version badge does not cause layout overflow for long skill names (use `truncate` on name)

### Dependencies
Step 1 (requires `version` and `toolchain` in `AvailableSkill`)

### Estimated Complexity
**Small** — Adding a Badge component to an existing template.

---

## Step 6: Display Tags in Available Skills List

### What
Show up to 3 tags as small text labels below the skill description in the available skills list view.

### Where
`src/lib/components/config/SkillsList.svelte` — Available skills section

### How

1. After the description `<p>` in the available skill item, add tags:

   ```svelte
   <button onclick={() => onSelect(skill)} class="flex-1 min-w-0 text-left">
       <div class="flex items-center gap-2">
           <span class="font-medium text-slate-900 dark:text-slate-100 truncate">{skill.name}</span>
           <!-- version badge, toolchain badge, deployed check -->
       </div>
       {#if skill.description}
           <p class="mt-0.5 text-xs text-slate-500 dark:text-slate-400 truncate">{skill.description}</p>
       {/if}
       {#if skill.tags && skill.tags.length > 0}
           <div class="mt-1 flex items-center gap-1 flex-wrap">
               {#each skill.tags.slice(0, 3) as tag}
                   <span class="text-xs px-1.5 py-0 rounded bg-slate-100 dark:bg-slate-700/50 text-slate-500 dark:text-slate-400">{tag}</span>
               {/each}
               {#if skill.tags.length > 3}
                   <span class="text-xs text-slate-400 dark:text-slate-500">+{skill.tags.length - 3}</span>
               {/if}
           </div>
       {/if}
   </button>
   ```

2. Use simple inline `<span>` elements rather than Badge components to keep visual weight low — tags are supplementary info, not primary metadata.

### Why
Tags improve scannability and enable mental filtering. Research finding: "Tags (max 3) in skill list items — Medium impact for search + context." Tags also improve the free-text search relevance (already handled in Step 2's search filter update).

### Edge Cases

> **[REVISED]** Added explicit handling for `tags: []` vs `tags: undefined` vs missing entirely, per devil's advocate edge case #1.

- **`tags: undefined` (field missing)**: The `{#if skill.tags && skill.tags.length > 0}` guard handles this — section hidden.
- **`tags: []` (empty array)**: Same guard handles it — `[].length > 0` is false.
- **Skills with many tags (10+)**: Capped at 3 visible + "+N more" overflow indicator.
- **Long tag names**: Tags like "prompt-optimization" may be long. Using `flex-wrap` ensures they wrap cleanly rather than overflowing.

### Acceptance Criteria
- [ ] Up to 3 tags displayed below skill description
- [ ] Tags use low-visual-weight styling (small text, subtle background)
- [ ] "+N more" shown when more than 3 tags exist
- [ ] Tags hidden entirely when the `tags` array is empty, undefined, or missing
- [ ] Tags don't cause horizontal overflow

### Dependencies
Step 1 (requires `tags` in `AvailableSkill`)

### Estimated Complexity
**Small** — Template addition with simple slicing logic.

---

## Step 7: Display Token Count in Available Skills List

### What
Show a token count indicator for each available skill (e.g., "649 tok") to give users a sense of skill size/complexity.

### Where
`src/lib/components/config/SkillsList.svelte` — Available skills section

### How

1. Add a token count display at the end of the tags row (or on a new line if no tags):

   ```typescript
   function formatTokens(count: number): string {
       if (!count || count === 0) return '';
       if (count >= 1000) return `${(count / 1000).toFixed(1)}k tok`;
       return `${count} tok`;
   }
   ```

2. In the template, add after/beside tags:

   ```svelte
   {#if skill.tags && skill.tags.length > 0}
       <div class="mt-1 flex items-center gap-1 flex-wrap">
           {#each skill.tags.slice(0, 3) as tag}
               <span class="text-xs px-1.5 py-0 rounded bg-slate-100 dark:bg-slate-700/50 text-slate-500 dark:text-slate-400">{tag}</span>
           {/each}
           {#if skill.tags.length > 3}
               <span class="text-xs text-slate-400 dark:text-slate-500">+{skill.tags.length - 3}</span>
           {/if}
           {#if skill.full_tokens > 0}
               <span class="text-xs text-slate-400 dark:text-slate-500 ml-auto">{formatTokens(skill.full_tokens)}</span>
           {/if}
       </div>
   {:else if skill.full_tokens > 0}
       <div class="mt-1">
           <span class="text-xs text-slate-400 dark:text-slate-500">{formatTokens(skill.full_tokens)}</span>
       </div>
   {/if}
   ```

### Why
Token counts help users understand skill complexity at a glance. Small skills (649 tok) load fast and are lightweight. Large skills (15k+ tok) consume significant context window. Research notes: "Token counts as size indicators — every skill has `entry_point_tokens` and `full_tokens` counts."

### Edge Cases
- **Zero or missing tokens**: Hide the token indicator. Guard with `{#if skill.full_tokens > 0}`.
- **Very large token counts**: Format as "15.8k tok" for readability.
- **Token count of exactly 0**: Hidden — `formatTokens(0)` returns `''`.

### Acceptance Criteria
- [ ] Token count shows as "N tok" or "N.Nk tok" for each skill
- [ ] Token count is right-aligned on the tags row via `ml-auto`
- [ ] Hidden when `full_tokens` is 0 or missing
- [ ] Uses subtle muted text styling (slate-400)

### Dependencies
Step 1 (requires `full_tokens` in `AvailableSkill`), Step 6 (tags row layout)

### Estimated Complexity
**Small** — Formatting function + template addition.

---

## Step 8: Show Additional Fields in Available Skills Detail Panel

### What
Enhance the right-panel detail view for available skills to show the newly-captured fields: version, toolchain, framework, tags, token counts, author, updated date, source_path, and requires.

### Where
`src/lib/components/config/ConfigView.svelte` — Skill detail section (lines ~406-469)

### How

1. **Add version badge to the skill detail header** (next to the name):

   ```svelte
   <div class="flex items-center gap-3 mb-4">
       <h2 class="text-lg font-bold text-slate-900 dark:text-slate-100">{selectedSkill.name}</h2>
       {#if !isDeployedSkill(selectedSkill) && selectedSkill.version}
           <Badge text="v{selectedSkill.version}" variant="default" />
       {/if}
       <!-- existing deployed/available badges -->
   </div>
   ```

2. **Expand the metadata grid** for available skills. Currently the detail panel shows category and collection. Add toolchain, framework, author, updated:

   ```svelte
   <div class="grid grid-cols-2 gap-4">
       {#if selectedSkill.category}
           <div>
               <h3 class="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-1">Category</h3>
               <p class="text-sm text-slate-700 dark:text-slate-300">{selectedSkill.category}</p>
           </div>
       {/if}
       {#if !isDeployedSkill(selectedSkill) && selectedSkill.toolchain}
           <div>
               <h3 class="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-1">Toolchain</h3>
               <p class="text-sm text-slate-700 dark:text-slate-300">{selectedSkill.toolchain}</p>
           </div>
       {/if}
       {#if !isDeployedSkill(selectedSkill) && selectedSkill.framework}
           <div>
               <h3 class="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-1">Framework</h3>
               <p class="text-sm text-slate-700 dark:text-slate-300">{selectedSkill.framework}</p>
           </div>
       {/if}
       {#if selectedSkill.collection}
           <div>
               <h3 class="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-1">Collection</h3>
               <p class="text-sm text-slate-700 dark:text-slate-300">{selectedSkill.collection}</p>
           </div>
       {/if}
       <!-- existing deploy_mode and deploy_date for deployed skills -->
   </div>
   ```

3. **Add tags section** after the grid:

   ```svelte
   {#if !isDeployedSkill(selectedSkill) && selectedSkill.tags && selectedSkill.tags.length > 0}
       <div>
           <h3 class="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-1">Tags</h3>
           <div class="flex gap-2 flex-wrap mt-1">
               {#each selectedSkill.tags as tag}
                   <Badge text={tag} variant="info" />
               {/each}
           </div>
       </div>
   {/if}
   ```

4. **Add token counts, updated, author, source_path, and requires** sections:

   ```svelte
   {#if !isDeployedSkill(selectedSkill)}
       {#if selectedSkill.full_tokens > 0}
           <div>
               <h3 class="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-1">Size</h3>
               <p class="text-sm text-slate-700 dark:text-slate-300">
                   {formatTokens(selectedSkill.full_tokens)} total
                   {#if selectedSkill.entry_point_tokens > 0}
                       ({formatTokens(selectedSkill.entry_point_tokens)} entry point)
                   {/if}
               </p>
           </div>
       {/if}
       {#if selectedSkill.updated}
           <div>
               <h3 class="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-1">Last Updated</h3>
               <p class="text-sm text-slate-700 dark:text-slate-300">{selectedSkill.updated}</p>
           </div>
       {/if}
       {#if selectedSkill.requires && selectedSkill.requires.length > 0}
           <div>
               <h3 class="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-1">Dependencies</h3>
               <div class="flex gap-2 flex-wrap mt-1">
                   {#each selectedSkill.requires as req}
                       <Badge text={req} variant="default" />
                   {/each}
               </div>
           </div>
       {/if}
       {#if selectedSkill.source_path}
           <div>
               <h3 class="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-1">Source Path</h3>
               <p class="text-sm font-mono text-slate-600 dark:text-slate-400 break-all">{selectedSkill.source_path}</p>
           </div>
       {/if}
       {#if selectedSkill.author}
           <div>
               <h3 class="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-1">Author</h3>
               <p class="text-sm text-slate-700 dark:text-slate-300">{selectedSkill.author}</p>
           </div>
       {/if}
   {/if}
   ```

5. **Add `formatTokens` helper** to ConfigView (or import from a shared utils file):

   ```typescript
   function formatTokens(count: number): string {
       if (!count || count === 0) return '';
       if (count >= 1000) return `${(count / 1000).toFixed(1)}k tokens`;
       return `${count} tokens`;
   }
   ```

### Why
The right-panel detail view currently shows very sparse information for available skills (just description, category, collection). With the expanded interface, we can show much richer context without requiring backend changes.

### Edge Cases
- **Type guard**: All new fields are guarded by `!isDeployedSkill(selectedSkill)` since deployed skills don't have these fields (their interface hasn't changed).
- **Null framework/toolchain**: Only shown when non-null. Universal skills won't show toolchain/framework sections.
- **Empty requires array**: Most skills have `requires: []`. The section is hidden when empty.
- **Long source_path**: Uses `break-all` and `font-mono` for clean wrapping.
- **Collection names with special characters**: Rendered as plain text — no HTML injection risk since Svelte auto-escapes.

### Acceptance Criteria
- [ ] Available skill detail panel shows: version badge, toolchain, framework, tags, token counts, updated date, source_path, author, requires
- [ ] Each section is conditionally rendered only when data exists
- [ ] Deployed skill detail panel is unchanged
- [ ] Layout is clean and follows the existing grid/section pattern

### Dependencies
Step 1 (requires expanded `AvailableSkill` interface)

### Estimated Complexity
**Medium** — Multiple template sections added to ConfigView.

---

## Step 9: Improve Available Agents List Information Density

### What
Show tags (up to 3) and category badge in the available agents list items to increase information density without cluttering.

### Where
`src/lib/components/config/AgentsList.svelte` — Available agents section

### How

1. **Add category badge and tags** to the available agent item rendering (after description):

   ```svelte
   <button onclick={() => onSelect(agent)} class="flex-1 min-w-0 text-left">
       <div class="flex items-center gap-2">
           <span class="font-medium text-slate-900 dark:text-slate-100 truncate">{agent.name}</span>
           {#if agent.is_deployed}
               <svg class="w-4 h-4 text-green-500 flex-shrink-0" ...>...</svg>
           {/if}
           {#if agent.source}
               <Badge text={agent.source.split('/').pop() || agent.source} variant="default" />
           {/if}
           {#if agent.category}
               <Badge text={agent.category} variant="info" />
           {/if}
       </div>
       {#if agent.description}
           <p class="mt-0.5 text-xs text-slate-500 dark:text-slate-400 truncate">
               {truncate(agent.description, 80)}
           </p>
       {/if}
       {#if agent.tags && agent.tags.length > 0}
           <div class="mt-1 flex items-center gap-1 flex-wrap">
               {#each agent.tags.slice(0, 3) as tag}
                   <span class="text-xs px-1.5 py-0 rounded bg-slate-100 dark:bg-slate-700/50 text-slate-500 dark:text-slate-400">{tag}</span>
               {/each}
               {#if agent.tags.length > 3}
                   <span class="text-xs text-slate-400 dark:text-slate-500">+{agent.tags.length - 3}</span>
               {/if}
           </div>
       {/if}
   </button>
   ```

2. **Update search filter** to include tags:

   ```typescript
   let filteredAvailable = $derived(
       sortItems(
           searchQuery
               ? availableAgents.filter(a =>
                   a.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                   (a.description || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
                   (a.tags || []).some(t => t.toLowerCase().includes(searchQuery.toLowerCase()))
               )
               : availableAgents,
           sortBy,
           (a) => a.version,
           (a) => a.is_deployed
       )
   );
   ```

### Why
Research finding: "Limited Metadata Display in Lists: The list items show minimal information. Key metadata (description, tags, category) is only visible in the right-panel detail view." Available agents already have `tags` and `category` in the `AvailableAgent` interface — they're just not rendered in the list.

### Edge Cases
- **Agents with 31 tags (Research agent)**: Capped at 3 + "+28 more" overflow.
- **Badge overflow with long agent names**: Using `truncate` on the name prevents overflow. Badges use `flex-shrink-0`.
- **Category + source badges**: Two badges in the header row. The `gap-2` flex ensures they don't collide.

### Acceptance Criteria
- [ ] Available agents show category badge in the header row
- [ ] Up to 3 tags shown below description
- [ ] "+N more" overflow for agents with >3 tags
- [ ] Tags included in free-text search matching
- [ ] No layout overflow or clipping issues

### Dependencies
Step 2 (sort controls and search integration), Step 4 (category grouping — should coordinate visual weight)

### Estimated Complexity
**Small** — Template additions using existing component patterns.

---

## Step 10: Consolidate Duplicate Badge Components

### What
Unify the two Badge components into one that supports both text-prop and snippet-children APIs.

### Where
- `src/lib/components/Badge.svelte` (text-prop version, used in Config tab)
- `src/lib/components/shared/Badge.svelte` (snippet-children version, used elsewhere)

### How

1. **Update `components/Badge.svelte`** to support both APIs:

   ```svelte
   <script lang="ts">
       import type { Snippet } from 'svelte';

       interface Props {
           text?: string;
           variant?: 'default' | 'primary' | 'success' | 'warning' | 'danger' | 'error' | 'info';
           size?: 'sm' | 'md';
           children?: Snippet;
       }

       let { text, variant = 'default', size = 'sm', children }: Props = $props();

       const variantClasses: Record<string, string> = {
           default: 'bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-300',
           primary: 'bg-cyan-100 text-cyan-800 dark:bg-cyan-900 dark:text-cyan-200',
           success: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
           warning: 'bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200',
           danger: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
           error: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',  // alias for danger
           info: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
       };

       const sizeClasses: Record<string, string> = {
           sm: 'px-2 py-0.5 text-xs',
           md: 'px-2.5 py-1 text-sm',
       };
   </script>

   <span class="inline-flex items-center rounded-full font-medium {variantClasses[variant] || variantClasses.default} {sizeClasses[size]}">
       {#if children}
           {@render children()}
       {:else if text}
           {text}
       {/if}
   </span>
   ```

2. **Update `shared/Badge.svelte` imports** throughout the codebase to point to the unified version. Search for all imports of `shared/Badge.svelte` and replace with `Badge.svelte`:

   - Files currently importing `shared/Badge.svelte`: Check with grep for `from.*shared/Badge` or `from.*shared/Badge.svelte`
   - Update import paths to use the unified `$lib/components/Badge.svelte`

3. **Delete `shared/Badge.svelte`** after migrating all usages.

4. **Verify color consistency**: The current `shared/Badge.svelte` uses darker, more transparent colors (e.g., `bg-emerald-500/10 text-emerald-400`). The config tab's `Badge.svelte` uses lighter, more opaque colors (e.g., `bg-green-100 text-green-800`). The unified component should use the config tab's colors since they have better contrast for both light and dark mode (the `shared` version's colors only work in dark mode).

### Why
Research finding: "Duplicate Badge Components: Two `Badge.svelte` files exist with different APIs... This creates confusion and inconsistent styling across the app." The two components have different variant names (`danger` vs `error`), different color schemes, and different APIs (text prop vs snippet children).

### Edge Cases
- **Different color schemes**: Consumers of the `shared/Badge.svelte` (which used darker transparent colors) may look slightly different after migration. Visually verify all Badge usage sites.
- **Missing variant**: `variantClasses[variant] || variantClasses.default` provides fallback for any unknown variant.
- **Components using snippet children**: The unified Badge supports both `text` prop and `children` snippet. Code using `<Badge>Custom content</Badge>` should work via the `children` snippet.

### Acceptance Criteria
- [ ] Single `Badge.svelte` component at `components/Badge.svelte`
- [ ] Supports both `text` prop and `children` snippet
- [ ] Supports all variant names from both originals: `default`, `primary`, `success`, `warning`, `danger`, `error`, `info`
- [ ] `shared/Badge.svelte` is deleted
- [ ] All imports updated
- [ ] No visual regressions in any view that uses Badge
- [ ] TypeScript compiles without errors

### Dependencies
None — can be done in parallel with other steps, but should be done early to avoid confusion during subsequent steps.

### Estimated Complexity
**Medium** — Requires careful import migration and visual verification across multiple files.

---

## Step 11: Dark Mode Audit

> **[REVISED]** Previously Step 10 vaguely stated "Audit all new/modified components for dark mode." Now specifies exact components and Tailwind classes to verify (R12).

### What
Verify all new and modified components render correctly in dark mode.

### Where
All files modified in Steps 1-10.

### How

**Specific components to audit:**

| Component | Dark Mode Classes to Verify |
|-----------|---------------------------|
| Sort dropdown (Steps 2) | `dark:bg-slate-800`, `dark:border-slate-700`, `dark:text-slate-300` |
| Group headers (Steps 3, 4) | `dark:bg-slate-800/30`, `dark:border-slate-700/50`, `dark:text-slate-400` |
| Tag spans (Steps 6, 9) | `dark:bg-slate-700/50`, `dark:text-slate-400` |
| Token count (Step 7) | `dark:text-slate-500` |
| Detail panel metadata headers (Step 8) | `dark:text-slate-400` (headers), `dark:text-slate-300` (values) |
| Detail panel source path (Step 8) | `dark:text-slate-400` with `font-mono` |
| Unified Badge (Step 10) | All variant `dark:` classes in variantClasses map |
| Group toggle button (Steps 3, 4) | Active: `bg-cyan-500/20 text-cyan-400`, Inactive: `dark:bg-slate-800 dark:text-slate-400` |

**Audit procedure:**
1. Toggle dark mode in the dashboard
2. Navigate to Config > Agents and Config > Skills tabs
3. Verify each component listed above has proper contrast and readability
4. Verify no hard-coded `bg-white` or `text-black` without corresponding `dark:` variants

### Acceptance Criteria
- [ ] All sort dropdowns readable in dark mode
- [ ] All group headers visible with proper contrast in dark mode
- [ ] All tag spans have sufficient contrast against dark backgrounds
- [ ] Unified Badge component renders all variants correctly in dark mode
- [ ] No white-on-white or black-on-black text in any component

### Dependencies
Steps 2-10 (all must be complete)

### Estimated Complexity
**Small** — Visual verification only, fixes are class additions.

---

## Testing Strategy

### Per-Step Verification

For each step, verify:

1. **TypeScript compilation**: Run `npm run check` (or `npx svelte-check`) in the `dashboard-svelte/` directory to verify no type errors.
2. **Build**: Run `npm run build` to verify the SvelteKit app builds successfully.
3. **Visual verification**: Start the Python backend (`python -m claude_mpm.dashboard` or equivalent), navigate to the Config tab, and verify:
   - Agents sub-tab: list rendering, search, sort, grouping
   - Skills sub-tab: list rendering, search, sort, grouping
   - Right-panel detail: click items and verify expanded metadata
4. **Dark mode**: Toggle dark mode and verify all new UI elements have proper dark mode styling.
5. **Edge cases**: Verify with empty lists, long names, missing fields.

### Integration Test Approach

> **Verification Amendment (VP-1)**: The existing test suite (`tests/test_config_routes.py`) uses `unittest.mock.MagicMock` for ALL backend services. Mocked tests cannot catch type mismatches, missing fields, or enrichment errors in the real data pipeline. Phase 1 testing must include live verification against real API responses, not just mocked unit tests.

1. **API data verification**: Open browser DevTools Network tab, inspect the actual API responses for `/api/config/skills/available` and `/api/config/agents/available` to confirm the new fields are present in the JSON.
2. **Store verification**: In browser console, import and inspect the Svelte store values to verify new fields are captured.
3. **Cross-tab navigation**: After changes, verify that clicking items in the list correctly updates the right-panel detail view.
4. **Graceful degradation test**: Simulate Phase 2 not yet deployed by temporarily removing enrichment fields from the API response. Verify no crashes, no "undefined" text rendered, and no broken sort/group/filter operations. This validates the VP-1-A deployment ordering requirement.

### Performance Criteria

> **[REVISED]** Added specific performance criteria per devil's advocate feedback.

- Rendering 156 skills with new fields (version, tags, tokens): < 200ms initial render
- Sort operation on 156 items: < 50ms (verify no visible lag)
- Group toggle: < 100ms re-render

### Build and Deploy

```bash
cd src/claude_mpm/dashboard-svelte
npm run build
# Built output goes to ../dashboard/static/svelte-build/
```

Verify the built output is served correctly by the Python backend.

---

## Rollback Plan

Each step is independently revertable via `git checkout -- <file>` for the specific files modified:

| Step | Files Modified | Revert Command |
|------|---------------|----------------|
| 1 | `stores/config.svelte.ts` | `git checkout -- src/lib/stores/config.svelte.ts` |
| 2 | `AgentsList.svelte`, `SkillsList.svelte` | `git checkout -- src/lib/components/config/AgentsList.svelte src/lib/components/config/SkillsList.svelte` |
| 3 | `SkillsList.svelte` | `git checkout -- src/lib/components/config/SkillsList.svelte` |
| 4 | `AgentsList.svelte` | `git checkout -- src/lib/components/config/AgentsList.svelte` |
| 5 | `SkillsList.svelte` | `git checkout -- src/lib/components/config/SkillsList.svelte` |
| 6 | `SkillsList.svelte` | `git checkout -- src/lib/components/config/SkillsList.svelte` |
| 7 | `SkillsList.svelte` | `git checkout -- src/lib/components/config/SkillsList.svelte` |
| 8 | `ConfigView.svelte` | `git checkout -- src/lib/components/config/ConfigView.svelte` |
| 9 | `AgentsList.svelte` | `git checkout -- src/lib/components/config/AgentsList.svelte` |
| 10 | `Badge.svelte`, `shared/Badge.svelte`, imports | Requires restoring deleted file + reverting imports |

**Recommended commit strategy**: One commit per step (or per logical group: Steps 1-2, Steps 3-4, Steps 5-7, Step 8, Step 9, Step 10). This enables `git revert` for any individual change.

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| API response doesn't include expected fields | Low (verified via research) | High — Steps 1-8 depend on this | Verify in browser DevTools before coding; all new fields use conditional rendering |
| Sort/group state causes performance issues with 156 skills | Low | Medium — UI lag | `$derived` values are memoized; sorting 156 items is negligible |
| Badge consolidation breaks existing views | Medium | Medium — visual regression | Test all views that use Badge before and after migration |
| Toolchain grouping produces too many groups | Low | Low — visual clutter | 15 groups is manageable; can add collapse-all/expand-all later |
| Dark mode styling issues with new elements | Low | Low — cosmetic | All new elements use existing Tailwind dark: prefixed classes; explicit audit in Step 11 |
| Sort controls take space away from search on narrow panels | Medium | Low — UX | Sort dropdown is on a separate row below search; panel has min-width constraint |
| `collection` used for grouping instead of `toolchain` | n/a | n/a | Clarified: `toolchain` for skills grouping, `category` for agents grouping (R11) |

---

## Implementation Order (Recommended)

```
Step 1: Update AvailableSkill interface        (FOUNDATION — do first)
    ↓
Step 10: Consolidate Badge components          (TECH DEBT — do early)
    ↓
Step 2: Add sort controls                      (BOTH LISTS)
    ↓
Step 5: Show version badge in skills list      (QUICK — builds on Step 1)
    ↓
Step 6: Show tags in skills list               (QUICK — builds on Step 1)
    ↓
Step 7: Show token count in skills list        (QUICK — builds on Steps 1, 6)
    ↓
Step 3: Add toolchain grouping to skills       (MEDIUM — builds on Step 1)
    ↓
Step 4: Add category grouping to agents        (MEDIUM — mirrors Step 3)
    ↓
Step 9: Improve agent list info density        (QUICK — adds tags/category)
    ↓
Step 8: Enhance skill detail panel             (MEDIUM — builds on Step 1)
    ↓
Step 11: Dark mode audit                       (FINAL — all changes in place)
```

**Parallelization opportunities**:
- Steps 3 and 4 can be done in parallel (different files)
- Steps 5, 6, 7 can be done as one atomic change (same file)
- Step 10 can be done independently at any point
- Steps 8 and 9 can be done in parallel (different files)

---

## Phase 1 → Phase 2 Interface Contract

> **[REVISED]** Added explicit interface alignment section to ensure cross-phase consistency.

Phase 1 establishes these TypeScript interfaces that Phase 2 must align with:

| Interface | Fields Added in Phase 1 | Phase 2 Must Provide |
|-----------|------------------------|---------------------|
| `AvailableSkill` | version, toolchain, framework, tags, entry_point_tokens, full_tokens, requires, author, updated, source_path | Already provided by API — no Phase 2 change needed |
| `AvailableAgent` | (no changes — already has category, tags) | Phase 2 adds color, resource_tier, network_access to API response |
| `DeployedAgent` | (no changes in Phase 1) | Phase 2 adds description, category, color, tags, resource_tier, network_access, skills_count |
| `DeployedSkill` | (no changes in Phase 1) | Phase 2 adds version, toolchain, framework, tags, full_tokens, entry_point_tokens |

> **Verification Amendment (VP-1)**: All new fields added to TypeScript interfaces in Phase 1 MUST use the optional modifier (`?:`) so that Phase 1 frontend works correctly even when Phase 2 backend has not yet been deployed. Fields that Phase 2 will enrich but that are `undefined` before Phase 2 deploys must render as empty/hidden in the UI, never as "undefined" text or broken layout. See VP-1-A above for specific guidance on `$derived` computations that consume these fields.

---

## Summary

| Step | What | Complexity | Key File(s) |
|------|------|-----------|-------------|
| 1 | Expand `AvailableSkill` interface (5 → 15 fields) | Small | `config.svelte.ts` |
| 2 | Add sort controls to both lists | Medium | `AgentsList.svelte`, `SkillsList.svelte` |
| 3 | Add toolchain grouping to skills | Medium | `SkillsList.svelte` |
| 4 | Add category grouping to agents | Medium | `AgentsList.svelte` |
| 5 | Show version badge in skills list | Small | `SkillsList.svelte` |
| 6 | Show tags in skills list | Small | `SkillsList.svelte` |
| 7 | Show token count in skills list | Small | `SkillsList.svelte` |
| 8 | Enhance skill detail panel with new fields | Medium | `ConfigView.svelte` |
| 9 | Improve agent list info density (tags, category) | Small | `AgentsList.svelte` |
| 10 | Consolidate duplicate Badge components | Medium | `Badge.svelte`, `shared/Badge.svelte` |
| 11 | Dark mode audit | Small | All modified files |

**Total estimated effort**: 11 steps, 6 Small + 5 Medium = approximately 1-2 focused implementation sessions for a single Svelte Engineer agent.
