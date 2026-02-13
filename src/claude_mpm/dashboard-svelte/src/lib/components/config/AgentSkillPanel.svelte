<script lang="ts">
	import type { AgentSkillLinks } from '$lib/stores/config/skillLinks.svelte';
	import SearchInput from '$lib/components/shared/SearchInput.svelte';
	import Badge from '$lib/components/Badge.svelte';
	import PaginationControls from '$lib/components/shared/PaginationControls.svelte';
	import { createPaginationState, nextPage, previousPage, type PaginationState } from '$lib/utils/pagination';

	interface Props {
		agents: AgentSkillLinks[];
		loading: boolean;
		selectedAgent: AgentSkillLinks | null;
		onSelect: (agent: AgentSkillLinks) => void;
	}

	let { agents, loading, selectedAgent, onSelect }: Props = $props();

	let searchQuery = $state('');
	const PAGE_SIZE = 50;

	let safeAgents = $derived(agents ?? []);

	let filtered = $derived(
		searchQuery
			? safeAgents.filter(a =>
				a.agent_name.toLowerCase().includes(searchQuery.toLowerCase())
			)
			: safeAgents
	);

	let pagination = $state<PaginationState>(createPaginationState(PAGE_SIZE));

	$effect(() => {
		const newTotal = filtered.length;
		if (pagination.total !== newTotal || pagination.offset !== 0) {
			pagination = { ...pagination, total: newTotal, offset: 0 };
		}
	});

	let needsPagination = $derived(filtered.length > PAGE_SIZE);

	let visibleAgents = $derived(
		needsPagination
			? filtered.slice(pagination.offset, pagination.offset + pagination.limit)
			: filtered
	);

	function handleSearch(value: string) {
		searchQuery = value;
	}
</script>

<div class="flex flex-col h-full">
	<!-- Search -->
	<div class="p-3 border-b border-slate-200 dark:border-slate-700">
		<SearchInput
			value={searchQuery}
			placeholder="Search agents..."
			onInput={handleSearch}
		/>
	</div>

	<!-- Agent list -->
	<div class="flex-1 overflow-y-auto">
		{#if loading}
			<div class="flex items-center justify-center py-8 text-slate-500 dark:text-slate-400">
				<svg class="animate-spin w-5 h-5 mr-2" fill="none" viewBox="0 0 24 24">
					<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
					<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
				</svg>
				<span class="text-sm">Loading agents...</span>
			</div>
		{:else if filtered.length === 0}
			<div class="py-6 text-center text-sm text-slate-500 dark:text-slate-400">
				{searchQuery ? 'No agents match your search' : 'No agents found'}
			</div>
		{:else}
			<div class="divide-y divide-slate-100 dark:divide-slate-700/50">
				{#each visibleAgents as agent (agent.agent_name)}
					<button
						onclick={() => onSelect(agent)}
						class="w-full text-left px-4 py-2.5 flex items-center gap-3 text-sm transition-colors
							{selectedAgent?.agent_name === agent.agent_name
								? 'bg-cyan-50 dark:bg-cyan-900/20 border-l-2 border-l-cyan-500'
								: 'hover:bg-slate-50 dark:hover:bg-slate-700/30 border-l-2 border-l-transparent'}"
					>
						<div class="flex-1 min-w-0">
							<div class="flex items-center gap-2">
								<span class="font-medium truncate
									{agent.is_deployed
										? 'text-slate-900 dark:text-slate-100'
										: 'text-slate-400 dark:text-slate-500'}"
								>
									{agent.agent_name}
								</span>
								{#if !agent.is_deployed}
									<span class="text-[10px] text-slate-400 dark:text-slate-500 flex-shrink-0">(not deployed)</span>
								{/if}
							</div>
						</div>
						<Badge
							text={String(agent.skill_count)}
							variant={agent.skill_count > 0 ? 'info' : 'default'}
							size="sm"
						/>
					</button>
				{/each}
			</div>
		{/if}
	</div>

	<!-- Pagination -->
	{#if needsPagination}
		<PaginationControls
			state={pagination}
			onPrevious={() => { pagination = previousPage(pagination); }}
			onNext={() => { pagination = nextPage(pagination); }}
		/>
	{/if}
</div>
