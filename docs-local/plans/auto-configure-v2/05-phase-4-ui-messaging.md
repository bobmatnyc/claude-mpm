# Phase 4: Dashboard UI Messaging Improvements

## Objective

Update the dashboard `AutoConfigPreview.svelte` component and the `config.svelte.ts` store to display skill recommendations and restart warnings. Wire up real Socket.IO events to replace the simulated pipeline progress. After this phase, the dashboard provides the same level of information as the CLI's post-deployment summary.

## Prerequisites

- **Phase 2 (Skill Deployment API)** must be complete. The backend must return real `skill_recommendations`, `would_deploy_skills`, and `deployed_skills` data.

## Scope

**IN SCOPE:**
- Updating the `AutoConfigPreview` TypeScript interface with new fields
- Adding skill recommendation display in Step 1 (Detect & Recommend)
- Adding skill deployment preview in Step 2
- Adding restart warning banner after successful apply
- Adding detailed post-apply summary (deployed agents and skills)
- Wiring Socket.IO events to pipeline stage indicators

**NOT IN SCOPE:**
- Detailed diff view of agent changes (simple list is sufficient)
- Scope selector in the UI (project-only for now)
- Editing or removing individual recommendations before apply
- Adding confidence threshold slider (future enhancement)

## Current State

### AutoConfigPreview.svelte (339 lines)

**File:** `src/claude_mpm/dashboard-svelte/src/lib/components/config/AutoConfigPreview.svelte`

The component has a two-step modal:
1. **Step 1: Detect & Recommend** -- Shows toolchain badges, lists recommended agents with confidence scores
2. **Step 2: Review & Apply** -- Shows diff view (agents to deploy, agents skipped), requires typing "apply" to confirm

**Missing elements:**
- No skill recommendations displayed in Step 1
- No skill deployment preview in Step 2
- No restart warning after successful deployment
- No summary of what was deployed

### Pipeline Stages (Simulated)

**Lines 58-87 of AutoConfigPreview.svelte:**
```typescript
pipelineStages = [
    { name: 'Backup', status: 'success' },
    { name: 'Agents', status: 'active' },
    { name: 'Skills', status: 'pending' },
    { name: 'Verify', status: 'pending' },
];
const result = await applyAutoConfig();
// Immediately mark all as success
```

The comment on line 65 acknowledges: "Progress simulation (real progress would come from Socket.IO)". Real `autoconfig_progress` events ARE emitted by the backend but the component does not listen for them.

### AutoConfigPreview Interface

**File:** `src/claude_mpm/dashboard-svelte/src/lib/stores/config.svelte.ts` lines 550-571

```typescript
export interface AutoConfigPreview {
    would_deploy: string[];
    would_skip: string[];
    deployment_count: number;
    estimated_deployment_time: number;
    requires_confirmation: boolean;
    recommendations: {
        agent_id: string;
        agent_name: string;
        confidence_score: number;
        rationale: string;
        match_reasons: string[];
        deployment_priority: string;
    }[];
    validation: { is_valid: boolean; error_count: number; warning_count: number } | null;
    toolchain?: ToolchainResult;
    metadata: Record<string, any>;
}
```

No `skill_recommendations` or `would_deploy_skills` fields exist.

### Post-Apply Store Behavior

**File:** `src/claude_mpm/dashboard-svelte/src/lib/stores/config.svelte.ts` lines 725-735

After `applyAutoConfig()` succeeds:
```typescript
await Promise.all([
    fetchDeployedAgents(),
    fetchAvailableAgents(),
    fetchDeployedSkills(),
    fetchAvailableSkills(),
    fetchProjectSummary()
]);
toastStore.success(result.message || 'Auto-configuration applied');
```

The store already refreshes skill lists after apply -- it was designed to support skill deployment. The toast message is generic and lacks detail.

### Socket.IO Event Listeners

**File:** `src/claude_mpm/dashboard-svelte/src/lib/stores/config.svelte.ts` lines 784-788

The store recognizes `autoconfig_progress`, `autoconfig_completed`, and `autoconfig_failed` events but delegates to "component-level listeners" which are NOT implemented in `AutoConfigPreview.svelte`.

## Target State

### Step 1: Enhanced Detect & Recommend

After the agent recommendations list, a new "Recommended Skills" section appears:

```
Recommended Skills (5)
  - test-driven-development    (for engineer, python-engineer)
  - python-style               (for python-engineer)
  - systematic-debugging       (for engineer)
  - fastapi-local-dev          (for python-engineer)
  - git-workflow               (for engineer)

Target: ~/.claude/skills/
```

### Step 2: Enhanced Review & Apply

Below the existing agent diff view, a new section appears:

**Skill Deployment Preview:**
```
Skills to Deploy (5)
  - test-driven-development
  - python-style
  - systematic-debugging
  - fastapi-local-dev
  - git-workflow

Target: ~/.claude/skills/
```

### Post-Apply: Detailed Summary with Restart Warning

After successful apply, the success message includes:

```
+---------------------------------------------------+
| Restart Required                                    |
|                                                     |
| Please restart Claude Code to apply changes:        |
|   - Quit Claude Code completely                     |
|   - Relaunch Claude Code                            |
|                                                     |
| Changes applied:                                    |
|   - Deployed 3 agent(s) to .claude/agents/          |
|   - Deployed 5 skill(s) to ~/.claude/skills/        |
+---------------------------------------------------+
```

### Pipeline Stages: Real-Time Updates

Pipeline indicators update based on Socket.IO events:
- `"detecting"` -> Detecting stage active
- `"recommending"` -> Recommending stage active
- `"validating"` -> Backup/Validate stage active
- `"deploying"` -> Agents stage active, shows current agent name
- `"deploying_skills"` -> Skills stage active
- `"verifying"` -> Verify stage active

## Implementation Steps

### Step 1: Update TypeScript interfaces

**Modify:** `src/claude_mpm/dashboard-svelte/src/lib/stores/config.svelte.ts`

Update the `AutoConfigPreview` interface:

```typescript
export interface AutoConfigPreview {
    // Existing fields...
    would_deploy: string[];
    would_skip: string[];
    deployment_count: number;
    estimated_deployment_time: number;
    requires_confirmation: boolean;
    recommendations: {
        agent_id: string;
        agent_name: string;
        confidence_score: number;
        rationale: string;
        match_reasons: string[];
        deployment_priority: string;
    }[];
    validation: { is_valid: boolean; error_count: number; warning_count: number } | null;
    toolchain?: ToolchainResult;
    metadata: Record<string, any>;

    // NEW fields
    skill_recommendations: string[];
    would_deploy_skills: string[];
}
```

Add a new interface for the apply result:

```typescript
export interface AutoConfigResult {
    job_id: string;
    deployed_agents: string[];
    failed_agents: string[];
    deployed_skills: string[];
    skill_errors: string[];
    backup_id: string | null;
    duration_ms: number;
    needs_restart: boolean;
    verification: Record<string, { passed: boolean }>;
}
```

### Step 2: Add skill recommendations section to Step 1

**Modify:** `src/claude_mpm/dashboard-svelte/src/lib/components/config/AutoConfigPreview.svelte`

After the agent recommendations list in Step 1, add:

```svelte
{#if preview?.skill_recommendations?.length}
    <div class="mt-4">
        <h4 class="text-sm font-semibold text-slate-300 mb-2">
            Recommended Skills ({preview.skill_recommendations.length})
        </h4>
        <div class="space-y-1">
            {#each preview.skill_recommendations as skill}
                <div class="flex items-center gap-2 px-2 py-1 bg-slate-800/50 rounded text-xs text-slate-400">
                    <span class="text-blue-400">+</span>
                    <span>{skill}</span>
                </div>
            {/each}
        </div>
        <p class="text-xs text-slate-500 mt-1">
            Target: ~/.claude/skills/
        </p>
    </div>
{/if}
```

### Step 3: Add skill deployment preview to Step 2

**Modify:** `src/claude_mpm/dashboard-svelte/src/lib/components/config/AutoConfigPreview.svelte`

After the existing agent diff view in Step 2:

```svelte
{#if preview?.would_deploy_skills?.length}
    <div class="mt-4">
        <h4 class="text-sm font-semibold text-slate-300 mb-2">
            Skills to Deploy ({preview.would_deploy_skills.length})
        </h4>
        <div class="space-y-1">
            {#each preview.would_deploy_skills as skill}
                <div class="flex items-center gap-2 px-2 py-1 bg-slate-800/50 rounded text-xs text-slate-400">
                    <span class="text-green-400">+</span>
                    <span>{skill}</span>
                </div>
            {/each}
        </div>
        <p class="text-xs text-slate-500 mt-1">
            Target: ~/.claude/skills/ (available in all projects)
        </p>
    </div>
{/if}
```

### Step 4: Add restart warning banner after apply

**Modify:** `src/claude_mpm/dashboard-svelte/src/lib/components/config/AutoConfigPreview.svelte`

After the apply button handler resolves, show the restart banner and detailed summary:

```svelte
{#if applyResult?.needs_restart}
    <div class="mt-4 px-3 py-2 bg-amber-500/10 border border-amber-500/30 rounded-lg">
        <div class="flex items-center gap-2 mb-1">
            <span class="text-amber-300 font-semibold text-sm">Restart Required</span>
        </div>
        <p class="text-xs text-slate-400">
            Please restart Claude Code to apply the new agents and skills.
            Quit Claude Code completely and relaunch.
        </p>
        <div class="mt-2 space-y-1 text-xs text-slate-400">
            {#if applyResult.deployed_agents?.length}
                <div>Deployed {applyResult.deployed_agents.length} agent(s) to .claude/agents/</div>
            {/if}
            {#if applyResult.deployed_skills?.length}
                <div>Deployed {applyResult.deployed_skills.length} skill(s) to ~/.claude/skills/</div>
            {/if}
        </div>
    </div>
{/if}
```

### Step 5: Wire Socket.IO events for real pipeline progress

**Modify:** `src/claude_mpm/dashboard-svelte/src/lib/components/config/AutoConfigPreview.svelte`

Replace the simulated pipeline with a Socket.IO listener:

```svelte
<script>
    import { onMount, onDestroy } from 'svelte';

    let socketCleanup: (() => void) | null = null;

    // Map backend phase names to pipeline stage indices
    const phaseToStageMap: Record<string, number> = {
        'detecting': 0,
        'recommending': 1,
        'validating': 2,
        'deploying': 3,
        'deploying_skills': 4,
        'verifying': 5,
    };

    function handleProgress(data: any) {
        const phase = data.phase;
        const stageIndex = phaseToStageMap[phase];
        if (stageIndex !== undefined) {
            // Mark all previous stages as success, current as active
            pipelineStages = pipelineStages.map((stage, i) => ({
                ...stage,
                status: i < stageIndex ? 'success' : i === stageIndex ? 'active' : 'pending'
            }));
        }
    }

    onMount(() => {
        // Register Socket.IO listener
        // (implementation depends on the existing Socket.IO setup in the store)
    });

    onDestroy(() => {
        socketCleanup?.();
    });
</script>
```

Update the pipeline stages array to include all phases:

```typescript
pipelineStages = [
    { name: 'Detect', status: 'pending' },
    { name: 'Recommend', status: 'pending' },
    { name: 'Backup', status: 'pending' },
    { name: 'Agents', status: 'pending' },
    { name: 'Skills', status: 'pending' },
    { name: 'Verify', status: 'pending' },
];
```

### Step 6: Replace generic toast with detailed result

**Modify:** `src/claude_mpm/dashboard-svelte/src/lib/stores/config.svelte.ts`

In the `applyAutoConfig()` function (around line 725), replace the generic toast with a result-aware one:

```typescript
const result = await response.json();
const agentCount = result.deployed_agents?.length || 0;
const skillCount = result.deployed_skills?.length || 0;

const parts = [];
if (agentCount) parts.push(`${agentCount} agent(s)`);
if (skillCount) parts.push(`${skillCount} skill(s)`);

toastStore.success(
    parts.length
        ? `Auto-configure complete: deployed ${parts.join(', ')}`
        : result.message || 'Auto-configuration applied'
);
```

## Devil's Advocate Analysis

### "Is a simple banner enough, or do we need a detailed diff view?"

A simple banner with counts is sufficient for the initial implementation. Here is why:
- The preview (Step 2) already shows the detailed list of what WILL be deployed
- After apply, the user already confirmed the changes -- they know what was planned
- A post-apply diff view would duplicate information already shown in the preview
- The restart warning is the most critical new information after apply

If users request more detail post-apply, a collapsible "Details" section can be added later. For now, counts + restart warning cover the essential information gap.

### "The pipeline stages are now 6 instead of 4 -- will they fit visually?"

The original pipeline had 4 stages: Backup, Agents, Skills, Verify. The expanded pipeline has 6: Detect, Recommend, Backup, Agents, Skills, Verify.

**Mitigation:** Use compact stage indicators (small circles/dots with labels below) rather than wide progress bars. Alternatively, group related stages:
- "Analyze" (Detect + Recommend)
- "Deploy" (Backup + Agents + Skills)
- "Verify"

The grouping approach reduces visual complexity while keeping real-time updates. Implementation choice should be made during development based on available horizontal space in the modal.

### "What if the backend returns empty skill_recommendations or would_deploy_skills?"

All new sections use `{#if array?.length}` guards. If the backend returns empty arrays, the sections simply do not render. The UI gracefully degrades to the current experience.

### "The Socket.IO event wiring might not work if the store's listener setup has changed"

The store's Socket.IO setup (lines 784-788) delegates to "component-level listeners". The exact mechanism for registering component listeners needs to be verified by reading the store's implementation. If the delegation pattern is not yet implemented, this step may require more work.

**Fallback:** If Socket.IO wiring is complex, implement a polling fallback: after calling `applyAutoConfig()`, poll a status endpoint every 500ms until completion. This is less elegant but functional.

### "Scope indicator -- should the UI show which directories are targeted?"

Yes. The skill target path (`~/.claude/skills/`) should be displayed in small text below the skill deployment section. This helps users understand what will happen to their file system.

The agent deployment target (`.claude/agents/`) is already implicit in the agent list and does not need a separate callout.

## Acceptance Criteria

1. Step 1 shows skill recommendations list with count when skills are recommended
2. Step 2 shows skill deployment preview with target path
3. Post-apply restart warning banner appears when `needs_restart` is true
4. Post-apply summary shows counts of deployed agents and deployed skills
5. Pipeline stages update in real-time based on Socket.IO events (or fallback to reasonable simulation)
6. Empty `skill_recommendations` and `would_deploy_skills` arrays do not render any extra UI elements
7. Toast message includes specific counts instead of generic "Auto-configuration applied"

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Pipeline does not fit in modal width | Use compact indicators or group stages |
| Socket.IO listener setup is different than expected | Verify store pattern; implement polling fallback |
| Empty arrays cause rendering issues | All sections guarded with `{#if array?.length}` |
| Restart warning is confusing | Include step-by-step instructions: "Quit and relaunch" |

## Estimated Effort

**M (2-4 hours)**

- 30 minutes to update TypeScript interfaces
- 45 minutes to add skill recommendations section (Step 1)
- 45 minutes to add skill deployment preview (Step 2)
- 30 minutes to add restart warning banner
- 45 minutes to wire Socket.IO events for pipeline
- 30 minutes to update toast messages
- 30 minutes for visual testing and adjustments
