<script lang="ts">
	import type { DeployedSkill, AvailableSkill } from '$lib/stores/config.svelte';
	import FilterBar from '$lib/components/shared/FilterBar.svelte';
	import FilterDropdown from '$lib/components/shared/FilterDropdown.svelte';
	import type { FilterOption } from '$lib/components/shared/FilterDropdown.svelte';

	interface Props {
		deployedSkills: DeployedSkill[];
		availableSkills: AvailableSkill[];
		searchQuery: string;
		onSearchChange: (value: string) => void;
		onFiltersChange: (filters: SkillFilters) => void;
	}

	export interface SkillFilters {
		search: string;
		toolchain: string[];
		status: string[];
	}

	let { deployedSkills, availableSkills, searchQuery = $bindable(''), onSearchChange, onFiltersChange }: Props = $props();

	const FILTER_STATE_KEY = 'skill-filters';

	function loadFilters(): SkillFilters {
		try {
			const stored = sessionStorage.getItem(FILTER_STATE_KEY);
			if (stored) {
				const parsed = JSON.parse(stored);
				return {
					search: parsed.search ?? '',
					toolchain: parsed.toolchain ?? [],
					status: parsed.status ?? [],
				};
			}
		} catch { /* ignore parse errors */ }
		return { search: '', toolchain: [], status: [] };
	}

	let savedFilters = loadFilters();
	let toolchainFilter = $state<string[]>(savedFilters.toolchain);
	let statusFilter = $state<string[]>(savedFilters.status);

	// Persist filter state to sessionStorage
	$effect(() => {
		const filters: SkillFilters = {
			search: searchQuery,
			toolchain: toolchainFilter,
			status: statusFilter,
		};
		sessionStorage.setItem(FILTER_STATE_KEY, JSON.stringify(filters));
		onFiltersChange(filters);
	});

	// Combine all skills for filter options computation
	let allSkills = $derived([
		...deployedSkills.map(s => ({ ...s, _deployed: true as const })),
		...availableSkills.map(s => ({ ...s, _deployed: s.is_deployed as boolean })),
	]);

	// Toolchain filter options
	let toolchainOptions = $derived.by<FilterOption[]>(() => {
		const counts = new Map<string, number>();
		for (const skill of allSkills) {
			const tc = skill.toolchain?.trim() || '';
			const key = (!tc || tc.toLowerCase() === 'universal') ? 'Universal' : tc.charAt(0).toUpperCase() + tc.slice(1);
			counts.set(key, (counts.get(key) ?? 0) + 1);
		}
		return [...counts.entries()]
			.sort((a, b) => {
				if (a[0] === 'Universal') return -1;
				if (b[0] === 'Universal') return 1;
				return a[0].localeCompare(b[0]);
			})
			.map(([value, count]) => ({ value, label: value, count }));
	});

	// Status filter options
	let statusOptions = $derived.by<FilterOption[]>(() => {
		const deployedCount = deployedSkills.length + availableSkills.filter(s => s.is_deployed).length;
		const availableCount = availableSkills.filter(s => !s.is_deployed).length;
		const opts: FilterOption[] = [];
		if (deployedCount > 0) opts.push({ value: 'deployed', label: 'Deployed', count: deployedCount });
		if (availableCount > 0) opts.push({ value: 'available', label: 'Available', count: availableCount });
		return opts;
	});

	let activeFilterCount = $derived(
		toolchainFilter.length +
		statusFilter.length +
		(searchQuery ? 1 : 0)
	);

	function clearAll() {
		searchQuery = '';
		toolchainFilter = [];
		statusFilter = [];
		onSearchChange('');
	}

	function handleSearch(value: string) {
		searchQuery = value;
		onSearchChange(value);
	}
</script>

<FilterBar
	bind:searchValue={searchQuery}
	searchPlaceholder="Search skills..."
	{activeFilterCount}
	onClear={clearAll}
	onSearchInput={handleSearch}
>
	<FilterDropdown
		label="Toolchain"
		options={toolchainOptions}
		bind:selected={toolchainFilter}
	/>
	<FilterDropdown
		label="Status"
		options={statusOptions}
		bind:selected={statusFilter}
	/>
</FilterBar>
