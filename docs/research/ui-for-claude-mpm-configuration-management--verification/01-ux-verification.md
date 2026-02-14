# UX Verification: Svelte Frontend vs Plan Specifications (Phases 1-4a)

**Date**: 2026-02-13
**Branch**: `ui-agents-skills-config`
**Scope**: Verify Svelte dashboard frontend implementation against plan documents for Phases 1, 2, 3, and 4a.

---

## Executive Summary

**Overall Compliance: ~92%**

The Svelte frontend implementation substantially fulfills the plan specifications across all four phases. Core functionality (config tab, CRUD operations, deployment UI, skill links, validation) is fully operational. Minor deviations are largely cosmetic or involve replacing planned standalone components with inline equivalents (e.g., LoadingSpinner replaced by inline SVG spinners, FormInput replaced by direct `<input>` elements in SourceForm). No critical plan requirements are missing.

| Phase | Compliance | Notes |
|-------|-----------|-------|
| Phase 1: Read-Only Visibility | ~90% | Core config tab, stores, navigation all present. Minor shared component naming differences. |
| Phase 2: Source Management | ~93% | Full CRUD + sync + real-time progress. FormInput/Toggle not standalone but functionality present inline. |
| Phase 3: Deployment Operations | ~95% | ModeSwitch, AutoConfigPreview, DeploymentPipeline, ConfirmDialog all match plan closely. Two-step confirmation implemented. |
| Phase 4a: Foundation Infrastructure | ~92% | Vitest setup, pagination, LazyStore, skill links view, validation panel all present. Test coverage is starter-level (1 test file). |

---

## Phase 1: Read-Only Visibility

### Plan Reference
`docs/plans/ui-for-claude-mpm-configuration-management/01-phase-1-read-only-visibility.md`

### Deliverables

| Deliverable | Status | Code Reference | Notes |
|------------|--------|---------------|-------|
| Config tab in dashboard navigation | ✅ Implemented | `+page.svelte:7` - ViewMode type includes `'config'` | Config tab added alongside events, tools, files, agents, tokens |
| ConfigView.svelte main container | ✅ Implemented | `config/ConfigView.svelte` (541 lines) | Implements sub-tabs, dual-panel layout, summary cards |
| AgentsList.svelte | ✅ Implemented | `config/AgentsList.svelte` (367 lines) | Deployed + available agents with search, collapsible sections |
| SkillsList.svelte | ✅ Implemented | `config/SkillsList.svelte` (337 lines) | Deployed + available skills with mode badge, search |
| SourcesList.svelte | ✅ Implemented | `config/SourcesList.svelte` (392 lines) | Sources with type badge, enabled/disabled toggle |
| Config store (configStore) | ✅ Implemented | `stores/config.svelte.ts` (671 lines) | Types, writable stores, fetch functions for all entities |
| Sub-tab navigation | ✅ Implemented | `ConfigView.svelte:27-29` - ConfigSubTab type | `'agents' \| 'skills' \| 'sources' \| 'skill-links'` |
| Badge.svelte shared component | ✅ Implemented | `components/Badge.svelte` (28 lines) | Props: `text`, `variant`, `size`. 6 variants. |
| SearchInput.svelte shared component | ✅ Implemented | `shared/SearchInput.svelte` (61 lines) | Debounced input with clear button, search icon |
| Dark/light mode support | ✅ Implemented | Throughout all components | Tailwind `dark:` prefix classes used consistently |
| Loading states | ✅ Implemented | All list components | Inline SVG spinner pattern with descriptive text |
| Empty states | ✅ Implemented | `shared/EmptyState.svelte` + inline fallbacks | EmptyState component + per-component empty messages |

### Partial / Deviating Items

| Item | Status | Details |
|------|--------|---------|
| StatusBadge.svelte | ⚠️ Partial | Plan mentioned `StatusBadge.svelte`; implementation uses `Badge.svelte` which serves the same purpose with `variant` prop for status colors. Functionally equivalent. |
| LoadingSpinner.svelte | ⚠️ Partial | Plan mentioned standalone `LoadingSpinner.svelte`; implementation uses inline SVG spinner pattern consistently across all components. No reusable spinner component exists but the pattern is consistent. |
| Overview sub-panel | ⚠️ Not standalone | Plan implied separate overview panel; ConfigView.svelte embeds summary cards directly in the header area rather than a separate component. |
| Toolchain sub-panel | ⚠️ Not standalone | Plan implied separate toolchain panel; toolchain detection is part of AutoConfigPreview.svelte (Phase 3). |

### Architecture Notes

- **State Management Pattern**: Hybrid Svelte 4/5 approach. Uses `writable()` stores from `svelte/store` bridged to Svelte 5 `$state` via `$effect` subscriptions in components. This is a pragmatic choice allowing gradual migration.
  ```typescript
  // In ConfigView.svelte
  $effect(() => {
    const unsub = someStore.subscribe(v => { localState = v; });
    return unsub;
  });
  ```
- **Fetch Pattern**: Each entity type has a dedicated `fetch*` function in `config.svelte.ts` that updates the corresponding writable store. Error handling populates `configError` store.

---

## Phase 2: Source Management (Mutations)

### Plan Reference
`docs/plans/ui-for-claude-mpm-configuration-management/02-phase-2-source-management-mutations.md`

### Deliverables

| Deliverable | Status | Code Reference | Notes |
|------------|--------|---------------|-------|
| addSource() store function | ✅ Implemented | `config.svelte.ts` | POST to `/api/config/sources/` |
| updateSource() store function | ✅ Implemented | `config.svelte.ts` | PUT to `/api/config/sources/{type}/{id}` |
| removeSource() store function | ✅ Implemented | `config.svelte.ts` | DELETE to `/api/config/sources/{type}/{id}` |
| syncSource() store function | ✅ Implemented | `config.svelte.ts` | POST to `/api/config/sources/{type}/{id}/sync` |
| syncAllSources() store function | ✅ Implemented | `config.svelte.ts` | POST to `/api/config/sources/sync-all` |
| SourceForm.svelte | ✅ Implemented | `config/SourceForm.svelte` (279 lines) | Add/edit modes, agent/skill-specific fields, validation |
| SyncProgress.svelte | ✅ Implemented | `config/SyncProgress.svelte` (163 lines) | Per-source sync status, Sync All button, ProgressBar |
| Modal.svelte | ✅ Implemented | `shared/Modal.svelte` (127 lines) | Sizes (sm/md/lg), focus trap, Escape close, backdrop close |
| Toast.svelte | ✅ Implemented | `shared/Toast.svelte` (59 lines) | Fixed bottom-right, 4 types (success/error/warning/info) |
| toastStore | ✅ Implemented | `stores/toast.svelte.ts` (45 lines) | Svelte 5 runes ($state), auto-dismiss, remove method |
| ProgressBar.svelte | ✅ Implemented | `shared/ProgressBar.svelte` (60 lines) | Determinate + indeterminate modes, sm/md sizes |
| ConfirmDialog.svelte | ✅ Implemented | `shared/ConfirmDialog.svelte` (103 lines) | Type-to-confirm, destructive/non-destructive styling |
| Socket.IO config event handling | ✅ Implemented | `config.svelte.ts:handleConfigEvent` + `+page.svelte` | Real-time updates from backend config changes |
| Form validation (inline) | ✅ Implemented | `SourceForm.svelte:36-93` | URL regex, subdirectory path traversal check, priority range, source ID pattern |
| Enabled/disabled toggle | ✅ Implemented | `SourceForm.svelte:246-252` | CSS toggle switch (peer-checked pattern) |
| System source protection (BR-11) | ✅ Implemented | `SourcesList.svelte` | System sources are non-removable |

### Partial / Deviating Items

| Item | Status | Details |
|------|--------|---------|
| FormInput.svelte | ❌ Not separate | Plan mentioned standalone `FormInput.svelte` shared component; form inputs are implemented directly in `SourceForm.svelte` with consistent styling. Functionality is complete but not reusable. |
| Toggle.svelte | ❌ Not separate | Plan mentioned standalone `Toggle.svelte` shared component; toggle is implemented inline in `SourceForm.svelte:247-250` using CSS peer pattern. Works correctly but not reusable. |
| "Config changed externally" banner | ⚠️ Via toast | Plan specified a dismissible banner for external config changes; implementation uses toast notifications via `handleConfigEvent()`. Functionally adequate but less persistent than a banner. |

### Form Validation Details

SourceForm implements comprehensive validation:
- **URL**: Required, must match `^https:\/\/github\.com\/.+\/.+$`
- **Subdirectory**: Optional, no leading `/`, no `..` path traversal
- **Branch**: Required for skill sources
- **Priority**: 0-1000 integer range
- **Source ID**: Required for new skill sources, alphanumeric + hyphens/underscores
- **Token**: Optional, password field, supports `$ENV_VAR` prefix
- **Touched state**: Validation errors only shown after field blur (good UX)

---

## Phase 3: Deployment Operations

### Plan Reference
`docs/plans/ui-for-claude-mpm-configuration-management/03-phase-3-deployment-operations.md`

### Deliverables

| Deliverable | Status | Code Reference | Notes |
|------------|--------|---------------|-------|
| deployAgent() | ✅ Implemented | `config.svelte.ts` | POST to `/api/config/agents/deploy` |
| undeployAgent() | ✅ Implemented | `config.svelte.ts` | POST to `/api/config/agents/undeploy` |
| batchDeployAgents() | ✅ Implemented | `config.svelte.ts` | POST to `/api/config/agents/batch-deploy` |
| deploySkill() | ✅ Implemented | `config.svelte.ts` | POST to `/api/config/skills/deploy` |
| undeploySkill() | ✅ Implemented | `config.svelte.ts` | POST to `/api/config/skills/undeploy` |
| switchDeploymentMode() | ✅ Implemented | `config.svelte.ts` | POST to `/api/config/skills/mode` with preview/confirm |
| detectToolchain() | ✅ Implemented | `config.svelte.ts` | GET `/api/config/toolchain/detect` |
| previewAutoConfig() | ✅ Implemented | `config.svelte.ts` | POST `/api/config/auto-configure/preview` |
| applyAutoConfig() | ✅ Implemented | `config.svelte.ts` | POST `/api/config/auto-configure/apply` |
| checkActiveSessions() | ✅ Implemented | `config.svelte.ts` | GET `/api/config/sessions/active` |
| ModeSwitch.svelte | ✅ Implemented | `config/ModeSwitch.svelte` (234 lines) | Two-step wizard: Preview -> Confirm with type-to-confirm |
| AutoConfigPreview.svelte | ✅ Implemented | `config/AutoConfigPreview.svelte` (333 lines) | Two-step wizard: Detect+Recommend -> Review+Apply |
| DeploymentPipeline.svelte | ✅ Implemented | `config/DeploymentPipeline.svelte` (79 lines) | Visual pipeline: Backup->Agents->Skills->Verify with status states |
| Core agent protection (BR-01) | ✅ Implemented | `AgentsList.svelte` | Lock icon + disabled undeploy for core agents |
| Immutable skill protection | ✅ Implemented | `SkillsList.svelte` | Lock icon for `PM_CORE_SKILLS` and `CORE_SKILLS` collections |
| Active session warning banner | ✅ Implemented | `ConfigView.svelte` | Amber warning banner shown when active sessions detected |
| "Restart Claude Code" banner | ✅ Implemented | `ConfigView.svelte` | Blue info banner after deployment operations |

### Two-Step Confirmation Pattern

Both ModeSwitch and AutoConfigPreview implement a consistent two-step wizard pattern:
1. **Step 1 (Preview)**: Shows impact analysis / recommendations with visual step indicator
2. **Step 2 (Confirm)**: Type-to-confirm input + checkbox acknowledgment

This matches the plan's requirement for two-step confirmation on destructive operations.

### ModeSwitch Details (`ModeSwitch.svelte`)
- Step indicator (1: Preview, 2: Confirm)
- Current mode -> target mode visual with Badge components
- Impact preview: `would_remove` (red), `would_keep` (gray)
- Note callout for mode-specific information
- Checkbox: "I understand this will change..."
- Type "switch" to confirm
- Loading/error states throughout

### AutoConfigPreview Details (`AutoConfigPreview.svelte`)
- Step 1: "Analyze Project" button -> detects toolchain + generates preview
- Toolchain display: primary language, frameworks, build tools with confidence badges
- Recommended agents/skills lists with confidence levels
- Step 2: Diff view showing agents/skills to add/remove
- Type "apply" to confirm
- DeploymentPipeline visualization during apply
- Backup ID displayed on success

### DeploymentPipeline Details (`DeploymentPipeline.svelte`)
- Pipeline stages: pending (gray dot) -> active (cyan, pulse+spin) -> success (green check) -> failed (red X)
- Connectors between stages with color matching
- Compact mode available for inline usage
- Exported `PipelineStage` interface: `{ name, status, detail? }`

### Partial / Deviating Items

| Item | Status | Details |
|------|--------|---------|
| Backup/rollback UI | ⚠️ Partial | Backup ID is displayed in AutoConfigPreview success state, but no explicit "Rollback" button exists in the UI. Backend backup_id is captured but rollback action is not user-accessible. |
| Force redeploy dialog | ✅ Implemented | `AgentsList.svelte` includes a separate ConfirmDialog for force redeploy operations |

---

## Phase 4a: Foundation Infrastructure

### Plan Reference
`docs/plans/ui-for-claude-mpm-configuration-management/04a-phase-4a-foundation-infrastructure.md`

### Deliverables

| Deliverable | Status | Code Reference | Notes |
|------------|--------|---------------|-------|
| Vitest config | ✅ Implemented | `vitest.config.ts` (18 lines) | jsdom env, svelte plugin, $lib alias, setup file |
| Test setup file | ✅ Implemented | `test-utils/setup.ts` (1 line) | Imports `@testing-library/jest-dom` |
| SkillChip.test.ts | ✅ Implemented | `config/__tests__/SkillChip.test.ts` (80 lines) | 8 test cases covering rendering, variants, tooltips |
| SkillLinksView.svelte | ✅ Implemented | `config/SkillLinksView.svelte` (84 lines) | Dual-panel layout: agent list + skill chip list, stats bar |
| AgentSkillPanel.svelte | ✅ Implemented | `config/AgentSkillPanel.svelte` (119 lines) | Searchable, paginated agent list with selection |
| SkillChipList.svelte | ✅ Implemented | `config/SkillChipList.svelte` (83 lines) | Grouped skills by source type, EmptyState handling |
| SkillChip.svelte | ✅ Implemented | `config/SkillChip.svelte` (59 lines) | Color-coded by source, auto badge, warning for undeployed |
| ValidationPanel.svelte | ✅ Implemented | `config/ValidationPanel.svelte` (149 lines) | Collapsible, severity badges, auto-fetch on mount |
| ValidationIssueCard.svelte | ✅ Implemented | `config/ValidationIssueCard.svelte` (79 lines) | Severity-colored, expandable suggestion, config path |
| skillLinks.svelte.ts store | ✅ Implemented | `stores/config/skillLinks.svelte.ts` (134 lines) | LazyStore pattern with load-once guard + invalidate |
| PaginationControls.svelte | ✅ Implemented | `shared/PaginationControls.svelte` (71 lines) | Pages + load-more modes, range display, accessible labels |
| pagination.ts utility | ✅ Implemented | `utils/pagination.ts` (54 lines) | State, cursor encode/decode, next/prev/has helpers |
| debounce.ts utility | ✅ Implemented | `utils/debounce.ts` (14 lines) | Generic debounce with TypeScript generics |
| Chip.svelte | ✅ Implemented | `shared/Chip.svelte` (41 lines) | 4 variants, 2 sizes, removable with close button |
| EmptyState.svelte | ✅ Implemented | `shared/EmptyState.svelte` (31 lines) | Snippet-based icon/action slots, default inbox icon |
| Badge.svelte (shared/) | ✅ Implemented | `shared/Badge.svelte` (34 lines) | Snippet children, 5 variants (different from top-level Badge.svelte) |

### LazyStore Pattern (`skillLinks.svelte.ts`)

The LazyStore pattern is correctly implemented:
```typescript
// Load guard: only fetches once
export async function loadSkillLinks(): Promise<void> {
  if (currentState.loaded && currentState.data) return;
  // ... fetch logic
}

// Invalidation: resets to initial state, forcing next load to re-fetch
export function invalidateSkillLinks(): void {
  skillLinksStore.set(initialState);
}
```

Backend response is transformed from flat `by_agent` array to frontend `AgentSkillLinks[]` shape, handling frontmatter vs content_marker skill sources.

### Pagination Infrastructure

- **State model**: `{ offset, limit, total }` - offset-based pagination
- **Cursor encoding**: `encodeCursor()` / `decodeCursor()` using Base64-encoded JSON
- **UI**: PaginationControls supports both traditional "pages" mode (prev/next buttons + range) and "load-more" mode
- **Integration**: AgentSkillPanel uses 50-item page size with automatic pagination when filtered list exceeds threshold

### Validation Panel Integration

- Fetches from `GET /api/config/validate` on mount
- Displays severity counts as colored badges (red for errors, amber for warnings, blue for info)
- Collapsible: click to expand/collapse issue list
- Issues sorted by severity (errors first)
- Each ValidationIssueCard shows: icon, message, config path, expandable suggestion
- Dark/light mode support throughout
- Retry button on fetch failure

### Test Coverage Assessment

| Test Area | Status | Notes |
|-----------|--------|-------|
| SkillChip.test.ts | ✅ 8 tests | Rendering, auto badge, source colors, warnings, tooltips |
| Other component tests | ❌ Not found | Only 1 test file exists (SkillChip). Plan implied more comprehensive test coverage. |
| Store tests | ❌ Not found | No unit tests for config store or skillLinks store |
| Utility tests | ❌ Not found | No unit tests for pagination.ts or debounce.ts |

### Partial / Deviating Items

| Item | Status | Details |
|------|--------|---------|
| Test coverage | ⚠️ Starter-level | Only `SkillChip.test.ts` exists (8 tests). Plan 4a emphasized "Testing Foundation" but coverage is minimal. Vitest infrastructure is correctly set up, so adding tests is straightforward. |
| Cursor-based pagination | ⚠️ Hybrid | Plan mentioned "cursor-based" pagination; implementation uses offset-based pagination with cursor encode/decode utilities available but not used by UI. AgentSkillPanel uses offset+limit slicing. |
| Accessibility (a11y) | ⚠️ Partial | Some ARIA attributes present (role="dialog", aria-expanded, aria-label on buttons), but not comprehensive. ValidationPanel and Modal have good a11y; other components could use improvement. |

---

## Cross-Phase Observations

### Dual Badge Pattern

Two Badge components exist:
1. **`components/Badge.svelte`** (28 lines): Props-based (`text`, `variant`, `size`). Used by ModeSwitch, AutoConfigPreview, AgentSkillPanel.
2. **`shared/Badge.svelte`** (34 lines): Snippet-based (`children` slot, `variant`, `size`). Used by SyncProgress.

This is a minor inconsistency. Both serve similar purposes with slightly different APIs. The props-based Badge is simpler; the snippet-based Badge is more flexible. Consolidating to one pattern would improve consistency.

### Consistent UI Patterns

The implementation demonstrates strong pattern consistency:
- **Loading**: Inline SVG spinner + descriptive text (consistent across all components)
- **Error**: Red-tinted error messages with Retry button (consistent)
- **Empty**: EmptyState component or inline "No X found" messages
- **Confirmation**: ConfirmDialog with type-to-confirm for destructive ops
- **Modal**: Shared Modal.svelte with focus trap, Escape close, backdrop dismiss
- **Toast**: Non-blocking notifications for operation results
- **Color scheme**: Cyan accent, emerald success, red danger, amber warning (consistent)

### Dark Mode Coverage

All components use Tailwind `dark:` variant classes. Key patterns:
- Text: `text-slate-900 dark:text-slate-100`
- Backgrounds: `bg-white dark:bg-slate-800`
- Borders: `border-slate-200 dark:border-slate-700`
- Badges: `bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200`

Coverage appears comprehensive - every component handles both modes.

### State Management Architecture

The hybrid Svelte 4/5 approach is used consistently:
- **Stores**: `writable()` from `svelte/store` (Svelte 4 pattern)
- **Components**: Svelte 5 runes (`$state`, `$derived`, `$effect`, `$props`)
- **Bridge**: `$effect(() => { const unsub = store.subscribe(...); return unsub; })` in each component

This is a pragmatic pattern during the Svelte 4->5 migration. The toast store is the exception - it uses pure Svelte 5 runes (`$state`).

---

## Component Inventory Summary

### Config Components (12 total)

| Component | Lines | Phase | Purpose |
|-----------|-------|-------|---------|
| ConfigView.svelte | 541 | 1 | Main config container with sub-tabs |
| AgentsList.svelte | 367 | 1 | Agent list with deploy/undeploy |
| SkillsList.svelte | 337 | 1 | Skill list with deploy/undeploy |
| SourcesList.svelte | 392 | 2 | Source CRUD with sync |
| SourceForm.svelte | 279 | 2 | Source add/edit form with validation |
| SyncProgress.svelte | 163 | 2 | Per-source sync status |
| ModeSwitch.svelte | 234 | 3 | Two-step mode switch wizard |
| AutoConfigPreview.svelte | 333 | 3 | Two-step auto-configure wizard |
| DeploymentPipeline.svelte | 79 | 3 | Visual pipeline progress |
| SkillLinksView.svelte | 84 | 4a | Dual-panel skill links browser |
| AgentSkillPanel.svelte | 119 | 4a | Searchable/paginated agent list |
| SkillChipList.svelte | 83 | 4a | Grouped skill chips display |

### Shared Components (9 total)

| Component | Lines | Phase | Purpose |
|-----------|-------|-------|---------|
| Modal.svelte | 127 | 2 | Reusable modal with focus trap |
| Toast.svelte | 59 | 2 | Toast notification renderer |
| ConfirmDialog.svelte | 103 | 2 | Destructive action confirmation |
| ProgressBar.svelte | 60 | 2 | Determinate/indeterminate progress |
| Badge.svelte (shared/) | 34 | 4a | Snippet-based badge |
| EmptyState.svelte | 31 | 4a | Empty state with icon/action slots |
| Chip.svelte | 41 | 4a | Removable tag/chip |
| PaginationControls.svelte | 71 | 4a | Prev/next + load-more pagination |
| SearchInput.svelte | 61 | 1 | Debounced search with clear |

### Additional Components

| Component | Lines | Phase | Purpose |
|-----------|-------|-------|---------|
| Badge.svelte (top-level) | 28 | 1 | Props-based badge (separate from shared/) |
| SkillChip.svelte | 59 | 4a | Color-coded skill chip |
| ValidationPanel.svelte | 149 | 4a | Collapsible validation results |
| ValidationIssueCard.svelte | 79 | 4a | Individual validation issue |

### Stores (3 total)

| Store | Lines | Phase | Purpose |
|-------|-------|-------|---------|
| config.svelte.ts | 671 | 1-3 | Main config store with all CRUD/deploy functions |
| toast.svelte.ts | 45 | 2 | Toast notification state (pure Svelte 5 runes) |
| skillLinks.svelte.ts | 134 | 4a | LazyStore for skill links data |

### Utilities (2 total)

| Utility | Lines | Phase | Purpose |
|---------|-------|-------|---------|
| pagination.ts | 54 | 4a | Pagination state helpers + cursor encode/decode |
| debounce.ts | 14 | 4a | Generic debounce function |

---

## Recommendations

### High Priority

1. **Expand test coverage**: Only SkillChip.test.ts exists with 8 tests. Priority test targets:
   - `config.svelte.ts` store functions (mock fetch, verify state transitions)
   - `pagination.ts` utility (pure functions, easy to test)
   - `ConfirmDialog.svelte` (critical UX for destructive operations)
   - `ModeSwitch.svelte` (complex multi-step flow)

2. **Consolidate Badge components**: Two Badge components (`Badge.svelte` and `shared/Badge.svelte`) with different APIs. Choose one approach (props-based or snippet-based) and consolidate.

### Medium Priority

3. **Extract FormInput.svelte**: The form input pattern in `SourceForm.svelte` (label + input + error message + touched state) is repeated 6 times. Extracting a reusable `FormInput` component would reduce duplication and ensure consistent validation UX.

4. **Add rollback UI**: The backend captures `backup_id` during auto-configure, but there's no user-facing rollback button. Consider adding a "Rollback" action accessible from a recent operations history.

5. **Improve accessibility**: Add `aria-live="polite"` to toast container, ensure all interactive elements have visible focus indicators, add `aria-describedby` to form inputs linking to error messages.

### Low Priority

6. **Extract LoadingSpinner.svelte**: The SVG spinner pattern is copy-pasted across ~10 components. A shared `LoadingSpinner.svelte` with size prop would reduce code duplication.

7. **Cursor-based pagination**: The `encodeCursor()` / `decodeCursor()` utilities exist but aren't used. Either integrate them with the backend's pagination API or remove them to avoid dead code.

8. **TypeScript strictness**: Some components use `any` type (e.g., `applyResult = $state<any>(null)` in AutoConfigPreview). Consider adding proper types for API response shapes.

---

## Edge Cases & Issues Found

1. **Reactive loop guard in AgentSkillPanel** (`AgentSkillPanel.svelte:32-37`): The `$effect` that resets pagination when filtered list changes includes a guard `if (pagination.total !== newTotal || pagination.offset !== 0)` to prevent infinite reactive loops. This was likely a bug fix (matches commit `a41cc063`).

2. **Null guards on .length** (`config.svelte.ts` and various components): Multiple places use `(array ?? []).length` or `array?.length ?? 0` patterns, suggesting backend responses can return null/undefined for array fields. This was addressed in commit `29f0ef2d`.

3. **Dual Badge import confusion**: `SyncProgress.svelte:4` imports `import SharedBadge from '$lib/components/shared/Badge.svelte'` with alias to avoid collision. This aliasing is a code smell indicating the two Badge components should be consolidated.

4. **ModeSwitch loadPreview on mount**: `ModeSwitch.svelte:78-80` uses `$effect(() => { loadPreview(); })` which triggers the API call immediately. If the modal is opened and closed rapidly, there's no abort controller to cancel the in-flight request.

5. **No request cancellation**: Store functions (`config.svelte.ts`) don't use `AbortController` for fetch requests. Rapid UI interactions (fast open/close of modals, rapid deploy/undeploy clicks) could cause race conditions with overlapping API calls.
