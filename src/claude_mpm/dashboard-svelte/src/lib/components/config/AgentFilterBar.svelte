<script lang="ts">
	import type { DeployedAgent, AvailableAgent } from '$lib/stores/config.svelte';
	import FilterBar from '$lib/components/shared/FilterBar.svelte';
	import FilterDropdown from '$lib/components/shared/FilterDropdown.svelte';
	import type { FilterOption } from '$lib/components/shared/FilterDropdown.svelte';

	interface Props {
		deployedAgents: DeployedAgent[];
		availableAgents: AvailableAgent[];
		searchQuery: string;
		onSearchChange: (value: string) => void;
		onFiltersChange: (filters: AgentFilters) => void;
	}

	export interface AgentFilters {
		search: string;
		category: string[];
		status: string[];
		resourceTier: string[];
	}

	let { deployedAgents, availableAgents, searchQuery = $bindable(''), onSearchChange, onFiltersChange }: Props = $props();

	const FILTER_STATE_KEY = 'agent-filters';

	function loadFilters(): AgentFilters {
		try {
			const stored = sessionStorage.getItem(FILTER_STATE_KEY);
			if (stored) {
				const parsed = JSON.parse(stored);
				return {
					search: parsed.search ?? '',
					category: parsed.category ?? [],
					status: parsed.status ?? [],
					resourceTier: parsed.resourceTier ?? [],
				};
			}
		} catch { /* ignore parse errors */ }
		return { search: '', category: [], status: [], resourceTier: [] };
	}

	let savedFilters = loadFilters();
	let categoryFilter = $state<string[]>(savedFilters.category);
	let statusFilter = $state<string[]>(savedFilters.status);
	let resourceTierFilter = $state<string[]>(savedFilters.resourceTier);

	// Persist filter state to sessionStorage
	$effect(() => {
		const filters: AgentFilters = {
			search: searchQuery,
			category: categoryFilter,
			status: statusFilter,
			resourceTier: resourceTierFilter,
		};
		sessionStorage.setItem(FILTER_STATE_KEY, JSON.stringify(filters));
		onFiltersChange(filters);
	});

	// Combine all agents for filter options computation
	let allAgents = $derived([
		...deployedAgents.map(a => ({ ...a, _deployed: true as const })),
		...availableAgents.map(a => ({ ...a, _deployed: a.is_deployed as boolean })),
	]);

	// Category filter options
	let categoryOptions = $derived.by<FilterOption[]>(() => {
		const counts = new Map<string, number>();
		for (const agent of allAgents) {
			const cat = (agent.category || 'Uncategorized');
			counts.set(cat, (counts.get(cat) ?? 0) + 1);
		}
		return [...counts.entries()]
			.sort((a, b) => a[0].localeCompare(b[0]))
			.map(([value, count]) => ({
				value,
				label: value.charAt(0).toUpperCase() + value.slice(1),
				count,
			}));
	});

	// Status filter options
	let statusOptions = $derived.by<FilterOption[]>(() => {
		const deployedCount = deployedAgents.length + availableAgents.filter(a => a.is_deployed).length;
		const availableCount = availableAgents.filter(a => !a.is_deployed).length;
		const opts: FilterOption[] = [];
		if (deployedCount > 0) opts.push({ value: 'deployed', label: 'Deployed', count: deployedCount });
		if (availableCount > 0) opts.push({ value: 'available', label: 'Available', count: availableCount });
		return opts;
	});

	// Resource tier filter options
	let resourceTierOptions = $derived.by<FilterOption[]>(() => {
		const counts = new Map<string, number>();
		for (const agent of allAgents) {
			const tier = ('resource_tier' in agent ? (agent as DeployedAgent).resource_tier : undefined) ?? 'Unknown';
			if (tier !== 'Unknown') {
				counts.set(tier, (counts.get(tier) ?? 0) + 1);
			}
		}
		return [...counts.entries()]
			.sort((a, b) => a[0].localeCompare(b[0]))
			.map(([value, count]) => ({ value, label: value, count }));
	});

	let activeFilterCount = $derived(
		categoryFilter.length +
		statusFilter.length +
		resourceTierFilter.length +
		(searchQuery ? 1 : 0)
	);

	function clearAll() {
		searchQuery = '';
		categoryFilter = [];
		statusFilter = [];
		resourceTierFilter = [];
		onSearchChange('');
	}

	function handleSearch(value: string) {
		searchQuery = value;
		onSearchChange(value);
	}
</script>

<FilterBar
	bind:searchValue={searchQuery}
	searchPlaceholder="Search agents..."
	{activeFilterCount}
	onClear={clearAll}
	onSearchInput={handleSearch}
>
	<FilterDropdown
		label="Category"
		options={categoryOptions}
		bind:selected={categoryFilter}
	/>
	<FilterDropdown
		label="Status"
		options={statusOptions}
		bind:selected={statusFilter}
	/>
	{#if resourceTierOptions.length > 0}
		<FilterDropdown
			label="Resource Tier"
			options={resourceTierOptions}
			bind:selected={resourceTierFilter}
		/>
	{/if}
</FilterBar>
