<script lang="ts">
	import type { DeployedSkill, AvailableSkill, LoadingState } from '$lib/stores/config.svelte';
	import { deploySkill, undeploySkill, checkActiveSessions } from '$lib/stores/config.svelte';
	import { toastStore } from '$lib/stores/toast.svelte';
	import Badge from '$lib/components/Badge.svelte';
	import SearchInput from '$lib/components/SearchInput.svelte';
	import ConfirmDialog from '$lib/components/shared/ConfirmDialog.svelte';

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

	// Deploy/undeploy state
	let deployingSkills = $state<Set<string>>(new Set());
	let undeployingSkills = $state<Set<string>>(new Set());

	// Confirm dialog state
	let showUndeployConfirm = $state(false);
	let undeployTarget = $state<DeployedSkill | null>(null);

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

	// Step 7: Token formatting helper
	function formatTokens(count: number): string {
		if (!count || count === 0) return '';
		if (count >= 1000) return `${(count / 1000).toFixed(1)}k tok`;
		return `${count} tok`;
	}

	let filteredDeployed = $derived(
		sortItems(
			searchQuery
				? deployedSkills.filter(s => s.name.toLowerCase().includes(searchQuery.toLowerCase()))
				: deployedSkills,
			sortBy,
			() => '',
			() => true
		)
	);

	let filteredAvailable = $derived(
		sortItems(
			searchQuery
				? availableSkills.filter(s =>
					s.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
					(s.description ?? '').toLowerCase().includes(searchQuery.toLowerCase()) ||
					(s.tags ?? []).some(t => t.toLowerCase().includes(searchQuery.toLowerCase()))
				)
				: availableSkills,
			sortBy,
			(s) => (s as AvailableSkill).version ?? '',
			(s) => (s as AvailableSkill).is_deployed
		)
	);

	// Step 3: Toolchain grouping
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
			// Normalize: falsy values and any case of "universal" -> 'Universal'
			// Capitalize all other toolchain names at grouping time to prevent
			// capitalization collisions producing duplicate keys
			const raw = skill.toolchain?.trim() || '';
			const key = (!raw || raw.toLowerCase() === 'universal')
				? 'Universal'
				: raw.charAt(0).toUpperCase() + raw.slice(1);
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
	<!-- Mode badge + Search + Sort -->
	<div class="p-3 border-b border-slate-200 dark:border-slate-700 space-y-2">
		<!-- Deployment mode header -->
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

		<SearchInput
			value={searchQuery}
			placeholder="Search skills..."
			onInput={(v) => searchQuery = v}
		/>

		<!-- Sort + Group controls -->
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
		</div>
	</div>

	<div class="flex-1 overflow-y-auto">
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
						{searchQuery ? 'No deployed skills match your search' : 'No deployed skills found'}
					</div>
				{:else}
					<div class="divide-y divide-slate-100 dark:divide-slate-700/50">
						{#each filteredDeployed as skill (skill.name)}
							{@const immutable = isImmutableSkill(skill)}
							{@const isUndeploying = undeployingSkills.has(skill.name)}
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
										<span class="font-medium text-slate-900 dark:text-slate-100 truncate">{skill.name}</span>
										{#if immutable}
											<Badge text="System" variant="danger" />
										{/if}
										{#if skill.category}
											<Badge text={skill.category} variant="default" />
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
						{searchQuery ? 'No available skills match your search' : 'No available skills found'}
					</div>
				{:else}
					<!-- Step 3: Grouped rendering -->
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
											<span class="font-medium text-slate-900 dark:text-slate-100 truncate">{skill.name}</span>
											{#if skill.is_deployed}
												<svg class="w-4 h-4 text-green-500 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
													<path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd" />
												</svg>
											{/if}
											<!-- Step 5: Version + Toolchain badges -->
											{#if skill.version}
												<Badge text="v{skill.version}" variant="default" />
											{/if}
											{#if skill.toolchain}
												<Badge text={skill.toolchain} variant="info" />
											{:else if skill.category}
												<Badge text={skill.category} variant="default" />
											{/if}
										</div>
										{#if skill.description}
											<p class="mt-0.5 text-xs text-slate-500 dark:text-slate-400 truncate">{skill.description}</p>
										{/if}
										<!-- Step 6: Tags + Step 7: Token count -->
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
