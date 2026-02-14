<script lang="ts">
	import type { DeployedAgent, AvailableAgent, LoadingState } from '$lib/stores/config.svelte';
	import { deployAgent, undeployAgent, batchDeployAgents, checkActiveSessions } from '$lib/stores/config.svelte';
	import { toastStore } from '$lib/stores/toast.svelte';
	import Badge from '$lib/components/Badge.svelte';
	import SearchInput from '$lib/components/SearchInput.svelte';
	import ConfirmDialog from '$lib/components/shared/ConfirmDialog.svelte';

	interface Props {
		deployedAgents: DeployedAgent[];
		availableAgents: AvailableAgent[];
		loading: LoadingState;
		onSelect: (agent: DeployedAgent | AvailableAgent) => void;
		selectedAgent: DeployedAgent | AvailableAgent | null;
		onSessionWarning?: (active: boolean) => void;
	}

	let { deployedAgents, availableAgents, loading, onSelect, selectedAgent, onSessionWarning }: Props = $props();

	let deployedExpanded = $state(true);
	let availableExpanded = $state(true);
	let searchQuery = $state('');

	// Step 2: Sort controls
	type SortOption = 'name-asc' | 'name-desc' | 'version' | 'status';
	let sortBy = $state<SortOption>('name-asc');

	// Step 4: Category grouping toggle
	let groupByCategory = $state(true);

	// Deploy/undeploy state
	let deployingAgents = $state<Set<string>>(new Set());
	let undeployingAgents = $state<Set<string>>(new Set());

	// Confirm dialog state
	let showUndeployConfirm = $state(false);
	let undeployTarget = $state<DeployedAgent | null>(null);

	// Force redeploy dialog
	let showForceRedeploy = $state(false);
	let forceRedeployTarget = $state<string>('');

	// Step 2: Sort function
	function sortItems<T extends { name: string }>(items: T[], sort: SortOption, getVersion?: (item: T) => string, getDeployed?: (item: T) => boolean): T[] {
		const sorted = [...items];
		switch (sort) {
			case 'name-asc':
				return sorted.sort((a, b) => a.name.localeCompare(b.name));
			case 'name-desc':
				return sorted.sort((a, b) => b.name.localeCompare(a.name));
			case 'version':
				return sorted.sort((a, b) => (getVersion?.(b) ?? '').localeCompare(getVersion?.(a) ?? ''));
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

	let filteredDeployed = $derived(
		sortItems(
			searchQuery
				? deployedAgents.filter(a => a.name.toLowerCase().includes(searchQuery.toLowerCase()))
				: deployedAgents,
			sortBy,
			(a) => (a as DeployedAgent).version ?? '',
			() => true
		)
	);

	let filteredAvailable = $derived(
		sortItems(
			searchQuery
				? availableAgents.filter(a =>
					a.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
					(a.description ?? '').toLowerCase().includes(searchQuery.toLowerCase()) ||
					(a.tags ?? []).some(t => t.toLowerCase().includes(searchQuery.toLowerCase()))
				)
				: availableAgents,
			sortBy,
			(a) => (a as AvailableAgent).version ?? '',
			(a) => (a as AvailableAgent).is_deployed
		)
	);

	let availableNotDeployed = $derived(
		filteredAvailable.filter(a => !a.is_deployed)
	);

	// Step 4: Category grouping
	interface AgentGroup {
		name: string;
		agents: AvailableAgent[];
	}

	let groupedAvailable = $derived.by<AgentGroup[]>(() => {
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
		const sorted: AgentGroup[] = [];
		// Sort groups alphabetically, but put Uncategorized last
		const entries = [...groups.entries()].sort((a, b) => {
			if (a[0] === 'Uncategorized') return 1;
			if (b[0] === 'Uncategorized') return -1;
			return a[0].localeCompare(b[0]);
		});
		for (const [name, groupAgents] of entries) {
			sorted.push({ name: name.charAt(0).toUpperCase() + name.slice(1), agents: groupAgents });
		}
		return sorted;
	});

	function isDeployedAgent(agent: DeployedAgent | AvailableAgent): agent is DeployedAgent {
		return 'is_core' in agent;
	}

	function getSelectedName(agent: DeployedAgent | AvailableAgent | null): string {
		if (!agent) return '';
		return agent.name;
	}

	function truncate(str: string, maxLen: number): string {
		if (!str) return '';
		if (str.length <= maxLen) return str;
		return str.slice(0, maxLen - 3) + '...';
	}

	async function handleDeploy(agent: AvailableAgent) {
		deployingAgents = new Set([...deployingAgents, agent.name]);
		try {
			await deployAgent(agent.name);
			const sessions = await checkActiveSessions();
			onSessionWarning?.(sessions.active);
		} catch (e: any) {
			if (e.status === 409) {
				forceRedeployTarget = agent.name;
				showForceRedeploy = true;
			}
		} finally {
			deployingAgents = new Set([...deployingAgents].filter(n => n !== agent.name));
		}
	}

	async function handleForceRedeploy() {
		showForceRedeploy = false;
		const name = forceRedeployTarget;
		deployingAgents = new Set([...deployingAgents, name]);
		try {
			await deployAgent(name, undefined, true);
			const sessions = await checkActiveSessions();
			onSessionWarning?.(sessions.active);
		} catch {
			// Error handled by store
		} finally {
			deployingAgents = new Set([...deployingAgents].filter(n => n !== name));
		}
	}

	function openUndeployConfirm(agent: DeployedAgent) {
		undeployTarget = agent;
		showUndeployConfirm = true;
	}

	async function handleUndeploy() {
		if (!undeployTarget) return;
		showUndeployConfirm = false;
		const name = undeployTarget.name;
		undeployingAgents = new Set([...undeployingAgents, name]);
		try {
			await undeployAgent(name);
			const sessions = await checkActiveSessions();
			onSessionWarning?.(sessions.active);
		} catch (e: any) {
			if (e.status === 403) {
				toastStore.error('Cannot undeploy core agent: system protection');
			}
		} finally {
			undeployingAgents = new Set([...undeployingAgents].filter(n => n !== name));
			undeployTarget = null;
		}
	}

	async function handleDeployCollection() {
		const names = availableNotDeployed.map(a => a.name);
		if (names.length === 0) return;
		try {
			await batchDeployAgents(names);
			const sessions = await checkActiveSessions();
			onSessionWarning?.(sessions.active);
		} catch {
			// Error handled by store
		}
	}
</script>

<div class="flex flex-col h-full">
	<!-- Search + Sort -->
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
				aria-label="Sort order"
				class="text-xs bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-md px-2 py-1 text-slate-700 dark:text-slate-300 focus:outline-none focus:ring-1 focus:ring-cyan-500"
			>
				<option value="name-asc">Name (A-Z)</option>
				<option value="name-desc">Name (Z-A)</option>
				<option value="version">Version</option>
				<option value="status">Deploy Status</option>
			</select>

			<button
				onclick={() => groupByCategory = !groupByCategory}
				class="text-xs px-2 py-1 rounded-md transition-colors
					{groupByCategory
						? 'bg-cyan-500/20 text-cyan-400'
						: 'bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-300'}"
				title={groupByCategory ? 'Disable grouping' : 'Group by category'}
				aria-pressed={groupByCategory}
			>
				Group
			</button>
		</div>
	</div>

	<div class="flex-1 overflow-y-auto">
		<!-- Deployed Agents Section -->
		<div>
			<button
				onclick={() => deployedExpanded = !deployedExpanded}
				class="w-full flex items-center justify-between px-4 py-2.5 bg-slate-50 dark:bg-slate-800/60 border-b border-slate-200 dark:border-slate-700 text-sm font-semibold text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700/50 transition-colors"
			>
				<span>Deployed ({filteredDeployed.length})</span>
				<svg class="w-4 h-4 transition-transform {deployedExpanded ? 'rotate-0' : '-rotate-90'}" fill="currentColor" viewBox="0 0 20 20">
					<path fill-rule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clip-rule="evenodd" />
				</svg>
			</button>

			{#if deployedExpanded}
				{#if loading.deployedAgents}
					<div class="flex items-center justify-center py-8 text-slate-500 dark:text-slate-400">
						<svg class="animate-spin w-5 h-5 mr-2" fill="none" viewBox="0 0 24 24">
							<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
							<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
						</svg>
						<span class="text-sm">Loading deployed agents...</span>
					</div>
				{:else if filteredDeployed.length === 0}
					<div class="py-6 text-center text-sm text-slate-500 dark:text-slate-400">
						{searchQuery ? 'No deployed agents match your search' : 'No deployed agents found'}
					</div>
				{:else}
					<div class="divide-y divide-slate-100 dark:divide-slate-700/50">
						{#each filteredDeployed as agent (agent.name)}
							{@const isUndeploying = undeployingAgents.has(agent.name)}
							<div
								class="w-full text-left px-4 py-2.5 flex items-center gap-3 text-sm transition-colors
									{getSelectedName(selectedAgent) === agent.name && isDeployedAgent(selectedAgent!)
										? 'bg-cyan-50 dark:bg-cyan-900/20 border-l-2 border-l-cyan-500'
										: 'hover:bg-slate-50 dark:hover:bg-slate-700/30 border-l-2 border-l-transparent'}"
							>
								<button
									onclick={() => onSelect(agent)}
									class="flex-1 min-w-0 text-left"
								>
									<div class="flex items-center gap-2">
										<span class="font-medium text-slate-900 dark:text-slate-100 truncate">{agent.name}</span>
										{#if agent.is_core}
											<Badge text="Core" variant="primary" />
										{/if}
										{#if agent.version}
											<Badge text="v{agent.version}" variant="default" />
										{/if}
									</div>
									{#if agent.specializations && agent.specializations.length > 0}
										<div class="mt-1 flex gap-1 flex-wrap">
											{#each agent.specializations.slice(0, 3) as spec}
												<span class="text-xs text-slate-500 dark:text-slate-400">{spec}</span>
											{/each}
										</div>
									{/if}
								</button>

								<!-- Undeploy / Lock button -->
								{#if agent.is_core}
									<span title="Core agent required by system" class="flex-shrink-0">
										<svg class="w-4 h-4 text-slate-400" fill="currentColor" viewBox="0 0 20 20">
											<path fill-rule="evenodd" d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z" clip-rule="evenodd" />
										</svg>
									</span>
								{:else}
									<button
										onclick={(e) => { e.stopPropagation(); openUndeployConfirm(agent); }}
										disabled={isUndeploying}
										class="flex-shrink-0 p-1 rounded text-slate-400 hover:text-red-400 transition-colors
											disabled:opacity-50 disabled:cursor-not-allowed"
										title="Undeploy agent"
									>
										{#if isUndeploying}
											<svg class="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
												<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
												<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
											</svg>
										{:else}
											<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
												<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
											</svg>
										{/if}
									</button>
								{/if}
							</div>
						{/each}
					</div>
				{/if}
			{/if}
		</div>

		<!-- Available Agents Section -->
		<div>
			<button
				onclick={() => availableExpanded = !availableExpanded}
				class="w-full flex items-center justify-between px-4 py-2.5 bg-slate-50 dark:bg-slate-800/60 border-b border-slate-200 dark:border-slate-700 text-sm font-semibold text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700/50 transition-colors"
			>
				<span>Available ({filteredAvailable.length})</span>
				<svg class="w-4 h-4 transition-transform {availableExpanded ? 'rotate-0' : '-rotate-90'}" fill="currentColor" viewBox="0 0 20 20">
					<path fill-rule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clip-rule="evenodd" />
				</svg>
			</button>

			{#if availableExpanded}
				<!-- Deploy Collection button -->
				{#if availableNotDeployed.length > 1}
					<div class="px-4 py-2 border-b border-slate-100 dark:border-slate-700/50">
						<button
							onclick={handleDeployCollection}
							class="px-3 py-1.5 text-xs font-medium text-white bg-cyan-600 hover:bg-cyan-700 rounded-lg transition-colors flex items-center gap-1"
						>
							<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
							</svg>
							Deploy All ({availableNotDeployed.length})
						</button>
					</div>
				{/if}

				{#if loading.availableAgents}
					<div class="flex items-center justify-center py-8 text-slate-500 dark:text-slate-400">
						<svg class="animate-spin w-5 h-5 mr-2" fill="none" viewBox="0 0 24 24">
							<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
							<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
						</svg>
						<span class="text-sm">Loading available agents...</span>
					</div>
				{:else if filteredAvailable.length === 0}
					<div class="py-6 text-center text-sm text-slate-500 dark:text-slate-400">
						{searchQuery ? 'No available agents match your search' : 'No available agents found'}
					</div>
				{:else}
					<!-- Step 4: Grouped rendering -->
					{#each groupedAvailable as group (group.name)}
						{#if groupByCategory}
							<div class="px-4 py-1.5 bg-slate-100/50 dark:bg-slate-800/30 border-b border-slate-100 dark:border-slate-700/50">
								<span class="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">
									{group.name} ({group.agents.length})
								</span>
							</div>
						{/if}
						<div class="divide-y divide-slate-100 dark:divide-slate-700/50">
							{#each group.agents as agent (agent.agent_id || agent.name)}
								{@const isDeploying = deployingAgents.has(agent.name)}
								<div
									class="w-full text-left px-4 py-2.5 flex items-center gap-3 text-sm transition-colors
										{getSelectedName(selectedAgent) === agent.name && !isDeployedAgent(selectedAgent!)
											? 'bg-cyan-50 dark:bg-cyan-900/20 border-l-2 border-l-cyan-500'
											: 'hover:bg-slate-50 dark:hover:bg-slate-700/30 border-l-2 border-l-transparent'}"
								>
									<button
										onclick={() => onSelect(agent)}
										class="flex-1 min-w-0 text-left"
									>
										<div class="flex items-center gap-2">
											<span class="font-medium text-slate-900 dark:text-slate-100 truncate">{agent.name}</span>
											{#if agent.is_deployed}
												<svg class="w-4 h-4 text-green-500 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
													<path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd" />
												</svg>
											{/if}
											{#if agent.version}
												<Badge text="v{agent.version}" variant="default" />
											{/if}
											<!-- Step 9: Category badge -->
											{#if agent.category}
												<Badge text={agent.category} variant="info" />
											{/if}
										</div>
										{#if agent.description}
											<p class="mt-0.5 text-xs text-slate-500 dark:text-slate-400 truncate">
												{truncate(agent.description, 80)}
											</p>
										{/if}
										<!-- Step 9: Tags for available agents -->
										{#if (agent.tags ?? []).length > 0}
											<div class="mt-1 flex items-center gap-1 flex-wrap">
												{#each (agent.tags ?? []).slice(0, 3) as tag}
													<span class="text-xs px-1.5 py-0 rounded bg-slate-100 dark:bg-slate-700/50 text-slate-500 dark:text-slate-400">{tag}</span>
												{/each}
												{#if (agent.tags ?? []).length > 3}
													<span class="text-xs text-slate-400 dark:text-slate-500">+{(agent.tags ?? []).length - 3}</span>
												{/if}
											</div>
										{/if}
									</button>

									<!-- Deploy button -->
									{#if !agent.is_deployed}
										<button
											onclick={(e) => { e.stopPropagation(); handleDeploy(agent); }}
											disabled={isDeploying}
											class="flex-shrink-0 px-2.5 py-1 text-xs font-medium rounded-md transition-colors
												text-cyan-400 bg-cyan-500/10 hover:bg-cyan-500/20
												disabled:opacity-50 disabled:cursor-not-allowed
												flex items-center gap-1"
										>
											{#if isDeploying}
												<svg class="animate-spin w-3 h-3" fill="none" viewBox="0 0 24 24">
													<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
													<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
												</svg>
												<span>Deploying...</span>
											{:else}
												<svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
													<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
												</svg>
												<span>Deploy</span>
											{/if}
										</button>
									{/if}
								</div>
							{/each}
						</div>
					{/each}
				{/if}
			{/if}
		</div>
	</div>
</div>

<!-- Undeploy Confirmation Dialog -->
<ConfirmDialog
	bind:open={showUndeployConfirm}
	title="Undeploy Agent"
	description="This will remove the agent from your project. The agent will still be available for redeployment."
	confirmText={undeployTarget?.name || ''}
	confirmLabel="Undeploy"
	destructive={true}
	onConfirm={handleUndeploy}
	onCancel={() => { showUndeployConfirm = false; undeployTarget = null; }}
/>

<!-- Force Redeploy Confirmation -->
<ConfirmDialog
	bind:open={showForceRedeploy}
	title="Agent Already Deployed"
	description="This agent is already deployed. Do you want to force a redeployment? This will overwrite the current deployment."
	confirmLabel="Force Redeploy"
	destructive={false}
	onConfirm={handleForceRedeploy}
	onCancel={() => { showForceRedeploy = false; }}
/>
