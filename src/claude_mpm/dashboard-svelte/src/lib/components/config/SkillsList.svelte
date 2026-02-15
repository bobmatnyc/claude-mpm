<script lang="ts">
	import type { DeployedSkill, AvailableSkill, LoadingState } from '$lib/stores/config.svelte';
	import { deploySkill, undeploySkill, checkActiveSessions } from '$lib/stores/config.svelte';
	import { toastStore } from '$lib/stores/toast.svelte';
	import Badge from '$lib/components/Badge.svelte';
	import ConfirmDialog from '$lib/components/shared/ConfirmDialog.svelte';
	import SkillFilterBar from './SkillFilterBar.svelte';
	import type { SkillFilters } from './SkillFilterBar.svelte';
	import VersionBadge from '$lib/components/shared/VersionBadge.svelte';
	import HighlightedText from '$lib/components/shared/HighlightedText.svelte';
	import { compareVersions } from '$lib/utils/version';
	import { FEATURES } from '$lib/config/features';

	interface Props {
		deployedSkills: DeployedSkill[];
		availableSkills: AvailableSkill[];
		loading: LoadingState;
		onSelect: (skill: DeployedSkill | AvailableSkill) => void;
		selectedSkill: DeployedSkill | AvailableSkill | null;
		deploymentMode?: string;
		onSwitchMode?: () => void;
		onSessionWarning?: (active: boolean) => void;
	}

	let { deployedSkills, availableSkills, loading, onSelect, selectedSkill, deploymentMode = 'selective', onSwitchMode, onSessionWarning }: Props = $props();

	// Immutable skill collections
	const IMMUTABLE_COLLECTIONS = ['PM_CORE_SKILLS', 'CORE_SKILLS'];

	let deployedExpanded = $state(true);
	let availableExpanded = $state(true);
	let searchQuery = $state('');

	// Step 2: Sort controls
	type SortOption = 'name-asc' | 'name-desc' | 'version' | 'status';
	let sortBy = $state<SortOption>('name-asc');

	// Step 3: Toolchain grouping toggle
	let groupByToolchain = $state(true);

	// Filter state from SkillFilterBar
	let currentFilters = $state<SkillFilters>({ search: '', toolchain: [], status: [] });

	// Deploy/undeploy state
	let deployingSkills = $state<Set<string>>(new Set());
	let undeployingSkills = $state<Set<string>>(new Set());

	// Confirm dialog state
	let showUndeployConfirm = $state(false);
	let undeployTarget = $state<DeployedSkill | null>(null);

	// Multi-field search function
	function matchesSearch(item: { name: string; description?: string; tags?: string[]; toolchain?: string | null; category?: string }, query: string): boolean {
		if (!query) return true;
		const q = query.toLowerCase();
		return item.name.toLowerCase().includes(q) ||
			(item.description ?? '').toLowerCase().includes(q) ||
			(item.tags ?? []).join(' ').toLowerCase().includes(q) ||
			(item.toolchain ?? '').toLowerCase().includes(q) ||
			(item.category ?? '').toLowerCase().includes(q);
	}

	// Sort function
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

	// Token formatting helper
	function formatTokens(count: number): string {
		if (!count || count === 0) return '';
		if (count >= 1000) return `${(count / 1000).toFixed(1)}k tok`;
		return `${count} tok`;
	}

	// Normalize toolchain for filter matching
	function normalizeToolchain(tc: string | null | undefined): string {
		const raw = tc?.trim() || '';
		return (!raw || raw.toLowerCase() === 'universal') ? 'Universal' : raw.charAt(0).toUpperCase() + raw.slice(1);
	}

	// Apply filters to deployed skills
	let filteredDeployed = $derived.by(() => {
		let items = deployedSkills;
		const q = searchQuery;
		const f = currentFilters;

		// Search filter
		if (q) {
			items = items.filter(s => matchesSearch(s, q));
		}

		// Toolchain filter
		if (f.toolchain.length > 0) {
			items = items.filter(s => f.toolchain.includes(normalizeToolchain(s.toolchain)));
		}

		// Status filter: if only "available" is selected, hide deployed section
		if (f.status.length > 0 && !f.status.includes('deployed')) {
			items = [];
		}

		return sortItems(items, sortBy, () => '', () => true);
	});

	// Apply filters to available skills
	let filteredAvailable = $derived.by(() => {
		// Filter out already-deployed skills to prevent duplicates between sections
		let items = availableSkills.filter(s => !s.is_deployed);
		const q = searchQuery;
		const f = currentFilters;

		// Search filter
		if (q) {
			items = items.filter(s => matchesSearch(s, q));
		}

		// Toolchain filter
		if (f.toolchain.length > 0) {
			items = items.filter(s => f.toolchain.includes(normalizeToolchain(s.toolchain)));
		}

		// Status filter
		if (f.status.length > 0) {
			items = items.filter(s => {
				if (f.status.includes('available') && !s.is_deployed) return true;
				return false;
			});
		}

		return sortItems(items, sortBy, (s) => s.version ?? '', (s) => s.is_deployed);
	});

	// Match a deployed skill to its available counterpart by manifest_name with fallback
	function findAvailableForDeployed(deployed: DeployedSkill): AvailableSkill | undefined {
		// Primary: use manifest_name (short name from manifest, e.g. "sveltekit")
		if (deployed.manifest_name) {
			const match = availableSkills.find(s => s.name === deployed.manifest_name);
			if (match) return match;
		}
		// Exact match on deployed name (works when names already align)
		const exact = availableSkills.find(s => s.name === deployed.name);
		if (exact) return exact;
		// Fallback: suffix match (e.g. deployed "toolchains-javascript-frameworks-sveltekit" ends with "-sveltekit")
		return availableSkills.find(s => deployed.name.endsWith('-' + s.name));
	}

	// Version update detection: count skills with outdated versions
	let outdatedCount = $derived.by(() => {
		let count = 0;
		for (const deployed of deployedSkills) {
			if (!deployed.version) continue;
			const available = findAvailableForDeployed(deployed);
			if (available && available.version) {
				if (compareVersions(deployed.version, available.version) === 'outdated') {
					count++;
				}
			}
		}
		return count;
	});

	// Find available version for a deployed skill
	function getAvailableVersion(skill: DeployedSkill): string | undefined {
		return findAvailableForDeployed(skill)?.version;
	}

	// Check if all filters are empty
	let hasActiveFilters = $derived(
		searchQuery !== '' ||
		currentFilters.toolchain.length > 0 ||
		currentFilters.status.length > 0
	);

	let noResults = $derived(
		hasActiveFilters && filteredDeployed.length === 0 && filteredAvailable.length === 0
	);

	// Toolchain grouping
	interface SkillGroup {
		name: string;
		skills: AvailableSkill[];
	}

	let groupedAvailable = $derived.by<SkillGroup[]>(() => {
		const skills = filteredAvailable;
		if (!groupByToolchain) {
			return [{ name: 'All Skills', skills }];
		}
		const groups = new Map<string, AvailableSkill[]>();
		for (const skill of skills) {
			const key = normalizeToolchain(skill.toolchain);
			if (!groups.has(key)) groups.set(key, []);
			groups.get(key)!.push(skill);
		}
		const sorted: SkillGroup[] = [];
		// Always place 'Universal' first if it exists
		if (groups.has('Universal')) {
			sorted.push({ name: 'Universal', skills: groups.get('Universal')! });
			groups.delete('Universal');
		}
		for (const [name, groupSkills] of [...groups.entries()].sort((a, b) => a[0].localeCompare(b[0]))) {
			sorted.push({ name, skills: groupSkills });
		}
		return sorted;
	});

	function isDeployedSkill(skill: DeployedSkill | AvailableSkill): skill is DeployedSkill {
		return 'deploy_mode' in skill;
	}

	function getSelectedName(skill: DeployedSkill | AvailableSkill | null): string {
		if (!skill) return '';
		return skill.name;
	}

	function isImmutableSkill(skill: DeployedSkill): boolean {
		return IMMUTABLE_COLLECTIONS.includes(skill.collection);
	}

	function getDeployModeVariant(mode: string): 'info' | 'success' {
		return (mode === 'user_defined' || mode === 'full') ? 'success' : 'info';
	}

	function formatDeployMode(mode: string): string {
		switch (mode) {
			case 'full': return 'Full';
			case 'selective': return 'Selective';
			case 'user_defined': return 'User Defined';
			default: return 'Agent Referenced';
		}
	}

	function handleFilterChange(filters: SkillFilters) {
		currentFilters = filters;
	}

	function clearFilters() {
		searchQuery = '';
		currentFilters = { search: '', toolchain: [], status: [] };
	}

	async function handleDeploy(skill: AvailableSkill) {
		deployingSkills = new Set([...deployingSkills, skill.name]);
		try {
			await deploySkill(skill.name, true);
			const sessions = await checkActiveSessions();
			onSessionWarning?.(sessions.active);
		} catch {
			// Error handled by store
		} finally {
			deployingSkills = new Set([...deployingSkills].filter(n => n !== skill.name));
		}
	}

	function openUndeployConfirm(skill: DeployedSkill) {
		undeployTarget = skill;
		showUndeployConfirm = true;
	}

	async function handleUndeploy() {
		if (!undeployTarget) return;
		showUndeployConfirm = false;
		const name = undeployTarget.name;
		undeployingSkills = new Set([...undeployingSkills, name]);
		try {
			await undeploySkill(name);
			const sessions = await checkActiveSessions();
			onSessionWarning?.(sessions.active);
		} catch {
			// Error handled by store
		} finally {
			undeployingSkills = new Set([...undeployingSkills].filter(n => n !== name));
			undeployTarget = null;
		}
	}
</script>

<div class="flex flex-col h-full">
	<!-- Mode badge -->
	<div class="px-3 pt-3 pb-1 border-b border-slate-200 dark:border-slate-700">
		<div class="flex items-center justify-between">
			<div class="flex items-center gap-2">
				<span class="text-xs text-slate-500 dark:text-slate-400">Mode:</span>
				<Badge
					text={formatDeployMode(deploymentMode)}
					variant={deploymentMode === 'full' ? 'success' : 'info'}
				/>
			</div>
			{#if onSwitchMode}
				<button
					onclick={onSwitchMode}
					class="px-2 py-1 text-xs font-medium text-cyan-400 hover:text-cyan-300 bg-cyan-500/10 hover:bg-cyan-500/20 rounded transition-colors"
				>
					Switch Mode
				</button>
			{/if}
		</div>
	</div>

	<!-- Filter Bar -->
	{#if FEATURES.FILTER_DROPDOWNS}
		<SkillFilterBar
			{deployedSkills}
			{availableSkills}
			bind:searchQuery={searchQuery}
			onSearchChange={(v) => searchQuery = v}
			onFiltersChange={handleFilterChange}
		/>
	{:else}
		<div class="px-3 py-2 border-b border-slate-200 dark:border-slate-700">
			<input
				type="text"
				placeholder="Search skills..."
				bind:value={searchQuery}
				class="w-full px-3 py-1.5 text-sm bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-md text-slate-700 dark:text-slate-300 placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-cyan-500"
			/>
		</div>
	{/if}

	<!-- Sort + Group controls -->
	<div class="px-3 py-2 border-b border-slate-200 dark:border-slate-700 flex items-center gap-2">
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

		{#if outdatedCount > 0}
			<span class="ml-auto text-xs text-amber-500 dark:text-amber-400 font-medium flex items-center gap-1">
				<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
				</svg>
				{outdatedCount} update{outdatedCount !== 1 ? 's' : ''} available
			</span>
		{/if}
	</div>

	<div class="flex-1 overflow-y-auto">
		<!-- No results empty state -->
		{#if noResults}
			<div class="py-12 text-center">
				<svg class="w-12 h-12 mx-auto mb-3 text-slate-300 dark:text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
				</svg>
				<p class="text-sm text-slate-500 dark:text-slate-400 mb-2">No skills match current filters</p>
				<button
					onclick={clearFilters}
					class="text-xs text-cyan-500 hover:text-cyan-400 font-medium transition-colors"
				>
					Clear filters
				</button>
			</div>
		{:else}
			<!-- Deployed Skills Section -->
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
					{#if loading.deployedSkills}
						<div class="flex items-center justify-center py-8 text-slate-500 dark:text-slate-400">
							<svg class="animate-spin w-5 h-5 mr-2" fill="none" viewBox="0 0 24 24">
								<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
								<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
							</svg>
							<span class="text-sm">Loading deployed skills...</span>
						</div>
					{:else if filteredDeployed.length === 0}
						<div class="py-6 text-center text-sm text-slate-500 dark:text-slate-400">
							{hasActiveFilters ? 'No deployed skills match your filters' : 'No deployed skills found'}
						</div>
					{:else}
						<div class="divide-y divide-slate-100 dark:divide-slate-700/50">
							{#each filteredDeployed as skill (skill.name)}
								{@const immutable = isImmutableSkill(skill)}
								{@const isUndeploying = undeployingSkills.has(skill.name)}
								{@const availVersion = getAvailableVersion(skill)}
								<div
									class="w-full text-left px-4 py-2.5 flex items-center gap-3 text-sm transition-colors
										{getSelectedName(selectedSkill) === skill.name && isDeployedSkill(selectedSkill!)
											? 'bg-cyan-50 dark:bg-cyan-900/20 border-l-2 border-l-cyan-500'
											: 'hover:bg-slate-50 dark:hover:bg-slate-700/30 border-l-2 border-l-transparent'}"
								>
									<button
										onclick={() => onSelect(skill)}
										class="flex-1 min-w-0 text-left"
									>
										<div class="flex items-center gap-2">
											<span class="font-medium text-slate-900 dark:text-slate-100 truncate">
												<HighlightedText text={skill.name} query={searchQuery} />
											</span>
											{#if immutable}
												<Badge text="System" variant="danger" />
											{/if}
											{#if skill.version && FEATURES.VERSION_MISMATCH}
												<VersionBadge deployedVersion={skill.version} availableVersion={availVersion} />
											{:else if skill.version}
												<span class="text-xs text-slate-500 dark:text-slate-400">v{skill.version}</span>
											{/if}
											{#if skill.toolchain}
												<Badge text={skill.toolchain} variant="info" />
											{:else if skill.toolchain === null || skill.toolchain === undefined}
												<Badge text="Universal" variant="default" />
											{/if}
										</div>
										<div class="mt-1 flex items-center gap-2">
											<Badge text={formatDeployMode(skill.deploy_mode)} variant={getDeployModeVariant(skill.deploy_mode)} />
											{#if skill.is_user_requested}
												<Badge text="Requested" variant="warning" />
											{/if}
											{#if skill.collection}
												<span class="text-xs text-slate-500 dark:text-slate-400">{skill.collection}</span>
											{/if}
										</div>
										<!-- Tags + Token count for deployed skills -->
										{#if (skill.tags ?? []).length > 0 || (skill.full_tokens && skill.full_tokens > 0)}
											<div class="mt-1 flex items-center gap-1 flex-wrap">
												{#each (skill.tags ?? []).slice(0, 3) as tag}
													<span class="text-xs px-1.5 py-0 rounded bg-slate-100 dark:bg-slate-700/50 text-slate-500 dark:text-slate-400">{tag}</span>
												{/each}
												{#if (skill.tags ?? []).length > 3}
													<span class="text-xs text-slate-400 dark:text-slate-500">+{(skill.tags ?? []).length - 3}</span>
												{/if}
												{#if skill.full_tokens && skill.full_tokens > 0}
													<span class="ml-auto text-xs text-slate-400 dark:text-slate-500">{formatTokens(skill.full_tokens)}</span>
												{/if}
											</div>
										{/if}
									</button>

									<!-- Undeploy / Lock -->
									{#if immutable}
										<span title="System skill cannot be undeployed" class="flex-shrink-0">
											<svg class="w-4 h-4 text-slate-400" fill="currentColor" viewBox="0 0 20 20">
												<path fill-rule="evenodd" d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z" clip-rule="evenodd" />
											</svg>
										</span>
									{:else}
										<button
											onclick={(e) => { e.stopPropagation(); openUndeployConfirm(skill); }}
											disabled={isUndeploying}
											class="flex-shrink-0 p-1 rounded text-slate-400 hover:text-red-400 transition-colors
												disabled:opacity-50 disabled:cursor-not-allowed"
											title="Undeploy skill"
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

			<!-- Available Skills Section -->
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
					{#if loading.availableSkills}
						<div class="flex items-center justify-center py-8 text-slate-500 dark:text-slate-400">
							<svg class="animate-spin w-5 h-5 mr-2" fill="none" viewBox="0 0 24 24">
								<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
								<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
							</svg>
							<span class="text-sm">Loading available skills from GitHub...</span>
						</div>
					{:else if filteredAvailable.length === 0}
						<div class="py-6 text-center text-sm text-slate-500 dark:text-slate-400">
							{hasActiveFilters ? 'No available skills match your filters' : 'No available skills found'}
						</div>
					{:else}
						<!-- Grouped rendering -->
						{#each groupedAvailable as group (group.name)}
							{#if groupByToolchain}
								<div class="px-4 py-1.5 bg-slate-100/50 dark:bg-slate-800/30 border-b border-slate-100 dark:border-slate-700/50">
									<span class="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">
										{group.name} ({group.skills.length})
									</span>
								</div>
							{/if}
							<div class="divide-y divide-slate-100 dark:divide-slate-700/50">
								{#each group.skills as skill (skill.name)}
									{@const isDeploying = deployingSkills.has(skill.name)}
									<div
										class="w-full text-left px-4 py-2.5 flex items-center gap-3 text-sm transition-colors
											{getSelectedName(selectedSkill) === skill.name && !isDeployedSkill(selectedSkill!)
												? 'bg-cyan-50 dark:bg-cyan-900/20 border-l-2 border-l-cyan-500'
												: 'hover:bg-slate-50 dark:hover:bg-slate-700/30 border-l-2 border-l-transparent'}"
									>
										<button
											onclick={() => onSelect(skill)}
											class="flex-1 min-w-0 text-left"
										>
											<div class="flex items-center gap-2">
												<span class="font-medium text-slate-900 dark:text-slate-100 truncate">
													<HighlightedText text={skill.name} query={searchQuery} />
												</span>
												{#if skill.is_deployed}
													<svg class="w-4 h-4 text-green-500 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
														<path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd" />
													</svg>
												{/if}
												{#if skill.version && FEATURES.VERSION_MISMATCH}
													<VersionBadge deployedVersion={skill.version} />
												{:else if skill.version}
													<span class="text-xs text-slate-500 dark:text-slate-400">v{skill.version}</span>
												{/if}
												{#if skill.toolchain}
													<Badge text={skill.toolchain} variant="info" />
												{:else if skill.category}
													<Badge text={skill.category} variant="default" />
												{/if}
											</div>
											{#if skill.description}
												<p class="mt-0.5 text-xs text-slate-500 dark:text-slate-400 truncate">
													<HighlightedText text={skill.description} query={searchQuery} maxLength={80} />
												</p>
											{/if}
											<!-- Tags + Token count -->
											{#if (skill.tags ?? []).length > 0 || (skill.full_tokens && skill.full_tokens > 0)}
												<div class="mt-1 flex items-center gap-1 flex-wrap">
													{#each (skill.tags ?? []).slice(0, 3) as tag}
														<span class="text-xs px-1.5 py-0 rounded bg-slate-100 dark:bg-slate-700/50 text-slate-500 dark:text-slate-400">{tag}</span>
													{/each}
													{#if (skill.tags ?? []).length > 3}
														<span class="text-xs text-slate-400 dark:text-slate-500">+{(skill.tags ?? []).length - 3}</span>
													{/if}
													{#if skill.full_tokens && skill.full_tokens > 0}
														<span class="ml-auto text-xs text-slate-400 dark:text-slate-500">{formatTokens(skill.full_tokens)}</span>
													{/if}
												</div>
											{/if}
										</button>

										<!-- Deploy button -->
										{#if !skill.is_deployed}
											<button
												onclick={(e) => { e.stopPropagation(); handleDeploy(skill); }}
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
		{/if}
	</div>
</div>

<!-- Undeploy Confirmation Dialog -->
<ConfirmDialog
	bind:open={showUndeployConfirm}
	title="Undeploy Skill"
	description="This will remove the skill from your project. The skill will still be available for redeployment."
	confirmText={undeployTarget?.name || ''}
	confirmLabel="Undeploy"
	destructive={true}
	onConfirm={handleUndeploy}
	onCancel={() => { showUndeployConfirm = false; undeployTarget = null; }}
/>
