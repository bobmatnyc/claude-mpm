<script lang="ts">
	import type { DeployedAgent, AvailableAgent, LoadingState } from '$lib/stores/config.svelte';
	import Badge from '$lib/components/Badge.svelte';
	import SearchInput from '$lib/components/SearchInput.svelte';

	interface Props {
		deployedAgents: DeployedAgent[];
		availableAgents: AvailableAgent[];
		loading: LoadingState;
		onSelect: (agent: DeployedAgent | AvailableAgent) => void;
		selectedAgent: DeployedAgent | AvailableAgent | null;
	}

	let { deployedAgents, availableAgents, loading, onSelect, selectedAgent }: Props = $props();

	let deployedExpanded = $state(true);
	let availableExpanded = $state(true);
	let searchQuery = $state('');

	let filteredDeployed = $derived(
		searchQuery
			? deployedAgents.filter(a => a.name.toLowerCase().includes(searchQuery.toLowerCase()))
			: deployedAgents
	);

	let filteredAvailable = $derived(
		searchQuery
			? availableAgents.filter(a =>
				a.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
				(a.description || '').toLowerCase().includes(searchQuery.toLowerCase())
			)
			: availableAgents
	);

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
</script>

<div class="flex flex-col h-full">
	<!-- Search -->
	<div class="p-3 border-b border-slate-200 dark:border-slate-700">
		<SearchInput
			value={searchQuery}
			placeholder="Search agents..."
			onInput={(v) => searchQuery = v}
		/>
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
							<button
								onclick={() => onSelect(agent)}
								class="w-full text-left px-4 py-2.5 flex items-center gap-3 text-sm transition-colors
									{getSelectedName(selectedAgent) === agent.name && isDeployedAgent(selectedAgent!)
										? 'bg-cyan-50 dark:bg-cyan-900/20 border-l-2 border-l-cyan-500'
										: 'hover:bg-slate-50 dark:hover:bg-slate-700/30 border-l-2 border-l-transparent'}"
							>
								<div class="flex-1 min-w-0">
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
								</div>
								{#if agent.is_core}
									<svg class="w-4 h-4 text-slate-400 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
										<path fill-rule="evenodd" d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z" clip-rule="evenodd" />
									</svg>
								{/if}
							</button>
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
					<div class="divide-y divide-slate-100 dark:divide-slate-700/50">
						{#each filteredAvailable as agent (agent.agent_id || agent.name)}
							<button
								onclick={() => onSelect(agent)}
								class="w-full text-left px-4 py-2.5 flex items-center gap-3 text-sm transition-colors
									{getSelectedName(selectedAgent) === agent.name && !isDeployedAgent(selectedAgent!)
										? 'bg-cyan-50 dark:bg-cyan-900/20 border-l-2 border-l-cyan-500'
										: 'hover:bg-slate-50 dark:hover:bg-slate-700/30 border-l-2 border-l-transparent'}"
							>
								<div class="flex-1 min-w-0">
									<div class="flex items-center gap-2">
										<span class="font-medium text-slate-900 dark:text-slate-100 truncate">{agent.name}</span>
										{#if agent.is_deployed}
											<svg class="w-4 h-4 text-green-500 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
												<path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd" />
											</svg>
										{/if}
										{#if agent.source}
											<Badge text={agent.source.split('/').pop() || agent.source} variant="default" />
										{/if}
									</div>
									{#if agent.description}
										<p class="mt-0.5 text-xs text-slate-500 dark:text-slate-400 truncate">
											{truncate(agent.description, 80)}
										</p>
									{/if}
								</div>
							</button>
						{/each}
					</div>
				{/if}
			{/if}
		</div>
	</div>
</div>
