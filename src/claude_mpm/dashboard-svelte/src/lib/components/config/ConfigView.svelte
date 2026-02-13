<script lang="ts">
	import { onMount } from 'svelte';
	import {
		projectSummary, configLoading, configErrors,
		deployedAgents, availableAgents,
		deployedSkills, availableSkills,
		configSources,
		syncStatus as syncStatusStore,
		fetchAllConfig,
		type ProjectSummary, type LoadingState, type ConfigError,
		type DeployedAgent, type AvailableAgent,
		type DeployedSkill, type AvailableSkill,
		type ConfigSource, type SyncState,
	} from '$lib/stores/config.svelte';
	import AgentsList from './AgentsList.svelte';
	import SkillsList from './SkillsList.svelte';
	import SourcesList from './SourcesList.svelte';
	import SkillLinksView from './SkillLinksView.svelte';
	import ModeSwitch from './ModeSwitch.svelte';
	import AutoConfigPreview from './AutoConfigPreview.svelte';
	import Badge from '$lib/components/Badge.svelte';

	interface Props {
		panelSide: 'left' | 'right';
	}

	let { panelSide }: Props = $props();

	type ConfigSubTab = 'agents' | 'skills' | 'sources' | 'skill-links';
	let subTab = $state<ConfigSubTab>('agents');

	// Selected items for detail view in right panel
	let selectedAgent = $state<DeployedAgent | AvailableAgent | null>(null);
	let selectedSkill = $state<DeployedSkill | AvailableSkill | null>(null);
	let selectedSource = $state<ConfigSource | null>(null);

	// Phase 3: Active session warning
	let showSessionWarning = $state(false);
	let sessionWarningDismissed = $state(false);

	// Phase 3: Modal states
	let showModeSwitch = $state(false);
	let showAutoConfig = $state(false);

	// Store subscriptions (hybrid Svelte 4/5 pattern matching codebase)
	let summaryData = $state<ProjectSummary | null>(null);
	let loadingState = $state<LoadingState>({
		summary: false,
		deployedAgents: false,
		availableAgents: false,
		deployedSkills: false,
		availableSkills: false,
		sources: false,
	});
	let errorsData = $state<ConfigError[]>([]);
	let deployedAgentsData = $state<DeployedAgent[]>([]);
	let availableAgentsData = $state<AvailableAgent[]>([]);
	let deployedSkillsData = $state<DeployedSkill[]>([]);
	let availableSkillsData = $state<AvailableSkill[]>([]);
	let sourcesData = $state<ConfigSource[]>([]);
	let syncStatusData = $state<Record<string, SyncState>>({});

	$effect(() => {
		const unsub = projectSummary.subscribe(v => { summaryData = v; });
		return unsub;
	});
	$effect(() => {
		const unsub = configLoading.subscribe(v => { loadingState = v; });
		return unsub;
	});
	$effect(() => {
		const unsub = configErrors.subscribe(v => { errorsData = v; });
		return unsub;
	});
	$effect(() => {
		const unsub = deployedAgents.subscribe(v => { deployedAgentsData = v; });
		return unsub;
	});
	$effect(() => {
		const unsub = availableAgents.subscribe(v => { availableAgentsData = v; });
		return unsub;
	});
	$effect(() => {
		const unsub = deployedSkills.subscribe(v => { deployedSkillsData = v; });
		return unsub;
	});
	$effect(() => {
		const unsub = availableSkills.subscribe(v => { availableSkillsData = v; });
		return unsub;
	});
	$effect(() => {
		const unsub = configSources.subscribe(v => { sourcesData = v; });
		return unsub;
	});
	$effect(() => {
		const unsub = syncStatusStore.subscribe(v => { syncStatusData = v; });
		return unsub;
	});

	// Clear selections when switching sub-tabs
	$effect(() => {
		// React to subTab changes
		subTab;
		selectedAgent = null;
		selectedSkill = null;
		selectedSource = null;
	});

	let hasFetched = false;

	onMount(() => {
		if (!hasFetched) {
			fetchAllConfig();
			hasFetched = true;
		}
	});

	// Helpers for detail view
	function isDeployedAgent(agent: DeployedAgent | AvailableAgent): agent is DeployedAgent {
		return 'is_core' in agent;
	}

	function isDeployedSkill(skill: DeployedSkill | AvailableSkill): skill is DeployedSkill {
		return 'deploy_mode' in skill;
	}

	function hasSelection(): boolean {
		return selectedAgent !== null || selectedSkill !== null || selectedSource !== null;
	}

	function formatDate(dateStr: string): string {
		if (!dateStr) return 'Unknown';
		try {
			return new Date(dateStr).toLocaleDateString(undefined, {
				year: 'numeric', month: 'short', day: 'numeric',
				hour: '2-digit', minute: '2-digit',
			});
		} catch {
			return dateStr;
		}
	}

	function handleSessionWarning(active: boolean) {
		if (active && !sessionWarningDismissed) {
			showSessionWarning = true;
		}
	}

	function handleModeChanged(newMode: string) {
		showModeSwitch = false;
		// Summary will be refetched by the store
	}
</script>

{#if panelSide === 'left'}
	<!-- LEFT PANEL: Summary cards + sub-tabs + lists -->
	<div class="flex flex-col h-full bg-white dark:bg-slate-900">
		<!-- Active Session Warning Banner -->
		{#if showSessionWarning && !sessionWarningDismissed}
			<div class="flex items-center gap-2 px-4 py-2 bg-amber-500/10 border-b border-amber-500/30 text-amber-300">
				<svg class="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
				</svg>
				<p class="text-xs flex-1">Active Claude Code sessions detected. Configuration changes will take effect on next session start.</p>
				<button
					onclick={() => sessionWarningDismissed = true}
					class="flex-shrink-0 p-0.5 text-amber-400 hover:text-amber-200 transition-colors"
					aria-label="Dismiss warning"
				>
					<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
					</svg>
				</button>
			</div>
		{/if}

		<!-- Summary Cards Row -->
		<div class="flex items-center gap-4 px-4 py-3 bg-slate-100 dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700 transition-colors">
			{#if loadingState.summary}
				<span class="text-sm text-slate-500 dark:text-slate-400">Loading summary...</span>
			{:else if summaryData}
				<span class="text-sm text-slate-700 dark:text-slate-300">
					<span class="font-semibold">{summaryData.agents.deployed}</span> agents deployed
				</span>
				<span class="text-sm text-slate-700 dark:text-slate-300">
					<span class="font-semibold">{summaryData.agents.available}</span> available
				</span>
				<span class="text-sm text-slate-700 dark:text-slate-300">
					<span class="font-semibold">{summaryData.skills.deployed}</span> skills
				</span>
				<span class="text-sm text-slate-700 dark:text-slate-300">
					<span class="font-semibold">{summaryData.sources.agent_sources + summaryData.sources.skill_sources}</span> sources
				</span>
			{:else}
				<span class="text-sm text-slate-500 dark:text-slate-400">No data loaded</span>
			{/if}

			<!-- Auto-Configure button -->
			<button
				onclick={() => showAutoConfig = true}
				class="ml-auto px-2.5 py-1 text-xs font-medium text-cyan-400 bg-cyan-500/10 hover:bg-cyan-500/20 rounded-lg transition-colors flex items-center gap-1"
				title="Auto-configure project"
			>
				<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
				</svg>
				Auto-Configure
			</button>
		</div>

		<!-- Error Banner -->
		{#if errorsData.length > 0}
			<div class="px-4 py-2 bg-red-50 dark:bg-red-900/20 border-b border-red-200 dark:border-red-800">
				<p class="text-xs text-red-700 dark:text-red-300">
					{errorsData[errorsData.length - 1].message}
				</p>
			</div>
		{/if}

		<!-- Sub-tabs -->
		<div class="flex gap-0 px-3 pt-2 bg-slate-50 dark:bg-slate-800/40 border-b border-slate-200 dark:border-slate-700">
			<button
				onclick={() => subTab = 'agents'}
				class="px-4 py-2 text-xs font-semibold rounded-t-md transition-colors
					{subTab === 'agents'
						? 'bg-white dark:bg-slate-900 text-cyan-700 dark:text-cyan-300 border border-b-0 border-slate-200 dark:border-slate-700'
						: 'text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-300'}"
			>
				Agents
			</button>
			<button
				onclick={() => subTab = 'skills'}
				class="px-4 py-2 text-xs font-semibold rounded-t-md transition-colors
					{subTab === 'skills'
						? 'bg-white dark:bg-slate-900 text-cyan-700 dark:text-cyan-300 border border-b-0 border-slate-200 dark:border-slate-700'
						: 'text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-300'}"
			>
				Skills
			</button>
			<button
				onclick={() => subTab = 'sources'}
				class="px-4 py-2 text-xs font-semibold rounded-t-md transition-colors
					{subTab === 'sources'
						? 'bg-white dark:bg-slate-900 text-cyan-700 dark:text-cyan-300 border border-b-0 border-slate-200 dark:border-slate-700'
						: 'text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-300'}"
			>
				Sources
			</button>
			<button
				onclick={() => subTab = 'skill-links'}
				class="px-4 py-2 text-xs font-semibold rounded-t-md transition-colors
					{subTab === 'skill-links'
						? 'bg-white dark:bg-slate-900 text-cyan-700 dark:text-cyan-300 border border-b-0 border-slate-200 dark:border-slate-700'
						: 'text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-300'}"
				role="tab"
				aria-selected={subTab === 'skill-links'}
			>
				Skill Links
			</button>
		</div>

		<!-- Sub-tab content -->
		<div class="flex-1 min-h-0">
			{#if subTab === 'agents'}
				<AgentsList
					deployedAgents={deployedAgentsData}
					availableAgents={availableAgentsData}
					loading={loadingState}
					onSelect={(agent) => { selectedAgent = agent; selectedSkill = null; selectedSource = null; }}
					{selectedAgent}
					onSessionWarning={handleSessionWarning}
				/>
			{:else if subTab === 'skills'}
				<SkillsList
					deployedSkills={deployedSkillsData}
					availableSkills={availableSkillsData}
					loading={loadingState}
					onSelect={(skill) => { selectedSkill = skill; selectedAgent = null; selectedSource = null; }}
					{selectedSkill}
					deploymentMode={summaryData?.deployment_mode || 'agent_referenced'}
					onSwitchMode={() => showModeSwitch = true}
					onSessionWarning={handleSessionWarning}
				/>
			{:else if subTab === 'sources'}
				<SourcesList
					sources={sourcesData}
					loading={loadingState.sources}
					onSelect={(source) => { selectedSource = source; selectedAgent = null; selectedSkill = null; }}
					{selectedSource}
					syncStatus={syncStatusData}
				/>
			{:else if subTab === 'skill-links'}
				<SkillLinksView />
			{/if}
		</div>
	</div>

{:else}
	<!-- RIGHT PANEL: Detail view -->
	<div class="flex flex-col h-full bg-white dark:bg-slate-900">
		{#if selectedAgent}
			<!-- Agent Detail -->
			<div class="flex-1 overflow-y-auto p-6">
				<div class="flex items-center gap-3 mb-4">
					<h2 class="text-lg font-bold text-slate-900 dark:text-slate-100">{selectedAgent.name}</h2>
					{#if isDeployedAgent(selectedAgent)}
						{#if selectedAgent.is_core}
							<Badge text="Core" variant="primary" />
						{/if}
						<Badge text="Deployed" variant="success" />
					{:else}
						{#if selectedAgent.is_deployed}
							<Badge text="Deployed" variant="success" />
						{:else}
							<Badge text="Available" variant="default" />
						{/if}
					{/if}
				</div>

				<div class="space-y-4">
					{#if !isDeployedAgent(selectedAgent) && selectedAgent.description}
						<div>
							<h3 class="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-1">Description</h3>
							<p class="text-sm text-slate-700 dark:text-slate-300">{selectedAgent.description}</p>
						</div>
					{/if}

					<div class="grid grid-cols-2 gap-4">
						{#if isDeployedAgent(selectedAgent)}
							<div>
								<h3 class="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-1">Version</h3>
								<p class="text-sm text-slate-700 dark:text-slate-300">{selectedAgent.version || 'N/A'}</p>
							</div>
							<div>
								<h3 class="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-1">Type</h3>
								<p class="text-sm text-slate-700 dark:text-slate-300">{selectedAgent.type || 'N/A'}</p>
							</div>
							<div>
								<h3 class="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-1">Location</h3>
								<p class="text-sm text-slate-700 dark:text-slate-300">{selectedAgent.location || 'project'}</p>
							</div>
						{:else}
							<div>
								<h3 class="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-1">Version</h3>
								<p class="text-sm text-slate-700 dark:text-slate-300">{selectedAgent.version || 'N/A'}</p>
							</div>
							<div>
								<h3 class="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-1">Category</h3>
								<p class="text-sm text-slate-700 dark:text-slate-300">{selectedAgent.category || 'N/A'}</p>
							</div>
							<div>
								<h3 class="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-1">Source</h3>
								<p class="text-sm text-slate-700 dark:text-slate-300">{selectedAgent.source || 'N/A'}</p>
							</div>
							<div>
								<h3 class="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-1">Priority</h3>
								<p class="text-sm text-slate-700 dark:text-slate-300">{selectedAgent.priority}</p>
							</div>
						{/if}
					</div>

					{#if isDeployedAgent(selectedAgent) && selectedAgent.path}
						<div>
							<h3 class="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-1">Path</h3>
							<p class="text-sm font-mono text-slate-600 dark:text-slate-400 break-all">{selectedAgent.path}</p>
						</div>
					{/if}

					{#if isDeployedAgent(selectedAgent) && selectedAgent.specializations && selectedAgent.specializations.length > 0}
						<div>
							<h3 class="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-1">Specializations</h3>
							<div class="flex gap-2 flex-wrap mt-1">
								{#each selectedAgent.specializations as spec}
									<Badge text={spec} variant="info" />
								{/each}
							</div>
						</div>
					{/if}

					{#if !isDeployedAgent(selectedAgent) && selectedAgent.tags && selectedAgent.tags.length > 0}
						<div>
							<h3 class="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-1">Tags</h3>
							<div class="flex gap-2 flex-wrap mt-1">
								{#each selectedAgent.tags as tag}
									<Badge text={tag} variant="info" />
								{/each}
							</div>
						</div>
					{/if}

					{#if !isDeployedAgent(selectedAgent) && selectedAgent.source_url}
						<div>
							<h3 class="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-1">Source URL</h3>
							<p class="text-sm font-mono text-slate-600 dark:text-slate-400 break-all">{selectedAgent.source_url}</p>
						</div>
					{/if}
				</div>
			</div>

		{:else if selectedSkill}
			<!-- Skill Detail -->
			<div class="flex-1 overflow-y-auto p-6">
				<div class="flex items-center gap-3 mb-4">
					<h2 class="text-lg font-bold text-slate-900 dark:text-slate-100">{selectedSkill.name}</h2>
					{#if isDeployedSkill(selectedSkill)}
						<Badge text="Deployed" variant="success" />
						{#if selectedSkill.is_user_requested}
							<Badge text="User Requested" variant="warning" />
						{/if}
					{:else}
						{#if selectedSkill.is_deployed}
							<Badge text="Deployed" variant="success" />
						{:else}
							<Badge text="Available" variant="default" />
						{/if}
					{/if}
				</div>

				<div class="space-y-4">
					{#if selectedSkill.description}
						<div>
							<h3 class="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-1">Description</h3>
							<p class="text-sm text-slate-700 dark:text-slate-300">{selectedSkill.description}</p>
						</div>
					{/if}

					<div class="grid grid-cols-2 gap-4">
						{#if selectedSkill.category}
							<div>
								<h3 class="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-1">Category</h3>
								<p class="text-sm text-slate-700 dark:text-slate-300">{selectedSkill.category}</p>
							</div>
						{/if}
						{#if selectedSkill.collection}
							<div>
								<h3 class="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-1">Collection</h3>
								<p class="text-sm text-slate-700 dark:text-slate-300">{selectedSkill.collection}</p>
							</div>
						{/if}
						{#if isDeployedSkill(selectedSkill)}
							<div>
								<h3 class="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-1">Deploy Mode</h3>
								<p class="text-sm text-slate-700 dark:text-slate-300">
									{selectedSkill.deploy_mode === 'user_defined' ? 'User Defined' : 'Agent Referenced'}
								</p>
							</div>
							{#if selectedSkill.deploy_date}
								<div>
									<h3 class="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-1">Deploy Date</h3>
									<p class="text-sm text-slate-700 dark:text-slate-300">{formatDate(selectedSkill.deploy_date)}</p>
								</div>
							{/if}
						{/if}
					</div>

					{#if isDeployedSkill(selectedSkill) && selectedSkill.path}
						<div>
							<h3 class="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-1">Path</h3>
							<p class="text-sm font-mono text-slate-600 dark:text-slate-400 break-all">{selectedSkill.path}</p>
						</div>
					{/if}
				</div>
			</div>

		{:else if selectedSource}
			<!-- Source Detail -->
			<div class="flex-1 overflow-y-auto p-6">
				<div class="flex items-center gap-3 mb-4">
					<h2 class="text-lg font-bold text-slate-900 dark:text-slate-100">{selectedSource.id}</h2>
					<Badge text={selectedSource.type === 'agent' ? 'Agent Source' : 'Skill Source'} variant={selectedSource.type === 'agent' ? 'info' : 'primary'} />
					{#if !selectedSource.enabled}
						<Badge text="Disabled" variant="danger" />
					{/if}
				</div>

				<div class="space-y-4">
					<div>
						<h3 class="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-1">URL</h3>
						<p class="text-sm font-mono text-slate-600 dark:text-slate-400 break-all">{selectedSource.url}</p>
					</div>

					<div class="grid grid-cols-2 gap-4">
						<div>
							<h3 class="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-1">Priority</h3>
							<p class="text-sm text-slate-700 dark:text-slate-300">{selectedSource.priority}</p>
						</div>
						<div>
							<h3 class="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-1">Status</h3>
							<p class="text-sm text-slate-700 dark:text-slate-300">{selectedSource.enabled ? 'Enabled' : 'Disabled'}</p>
						</div>
						{#if selectedSource.branch}
							<div>
								<h3 class="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-1">Branch</h3>
								<p class="text-sm text-slate-700 dark:text-slate-300">{selectedSource.branch}</p>
							</div>
						{/if}
						{#if selectedSource.subdirectory}
							<div>
								<h3 class="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-1">Subdirectory</h3>
								<p class="text-sm text-slate-700 dark:text-slate-300">{selectedSource.subdirectory}</p>
							</div>
						{/if}
					</div>
				</div>
			</div>

		{:else}
			<!-- Empty state -->
			<div class="flex items-center justify-center h-full text-slate-500 dark:text-slate-400">
				<div class="text-center">
					<svg class="w-16 h-16 mx-auto mb-3 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
					</svg>
					<p class="text-lg">Select an item from the list to view details</p>
				</div>
			</div>
		{/if}
	</div>
{/if}

<!-- Mode Switch Modal -->
{#if showModeSwitch}
	<ModeSwitch
		currentMode={summaryData?.deployment_mode || 'agent_referenced'}
		onClose={() => showModeSwitch = false}
		onModeChanged={handleModeChanged}
	/>
{/if}

<!-- Auto-Configure Modal -->
{#if showAutoConfig}
	<AutoConfigPreview onClose={() => showAutoConfig = false} />
{/if}
