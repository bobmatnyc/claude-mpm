<script lang="ts">
	import type { DeployedSkill, AvailableSkill, LoadingState } from '$lib/stores/config.svelte';
	import Badge from '$lib/components/Badge.svelte';
	import SearchInput from '$lib/components/SearchInput.svelte';

	interface Props {
		deployedSkills: DeployedSkill[];
		availableSkills: AvailableSkill[];
		loading: LoadingState;
		onSelect: (skill: DeployedSkill | AvailableSkill) => void;
		selectedSkill: DeployedSkill | AvailableSkill | null;
	}

	let { deployedSkills, availableSkills, loading, onSelect, selectedSkill }: Props = $props();

	let deployedExpanded = $state(true);
	let availableExpanded = $state(true);
	let searchQuery = $state('');

	let filteredDeployed = $derived(
		searchQuery
			? deployedSkills.filter(s => s.name.toLowerCase().includes(searchQuery.toLowerCase()))
			: deployedSkills
	);

	let filteredAvailable = $derived(
		searchQuery
			? availableSkills.filter(s =>
				s.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
				(s.description || '').toLowerCase().includes(searchQuery.toLowerCase())
			)
			: availableSkills
	);

	function isDeployedSkill(skill: DeployedSkill | AvailableSkill): skill is DeployedSkill {
		return 'deploy_mode' in skill;
	}

	function getSelectedName(skill: DeployedSkill | AvailableSkill | null): string {
		if (!skill) return '';
		return skill.name;
	}

	function getDeployModeVariant(mode: string): 'info' | 'success' {
		return mode === 'user_defined' ? 'success' : 'info';
	}

	function formatDeployMode(mode: string): string {
		return mode === 'user_defined' ? 'User Defined' : 'Agent Referenced';
	}
</script>

<div class="flex flex-col h-full">
	<!-- Search -->
	<div class="p-3 border-b border-slate-200 dark:border-slate-700">
		<SearchInput
			value={searchQuery}
			placeholder="Search skills..."
			onInput={(v) => searchQuery = v}
		/>
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
							<button
								onclick={() => onSelect(skill)}
								class="w-full text-left px-4 py-2.5 flex items-center gap-3 text-sm transition-colors
									{getSelectedName(selectedSkill) === skill.name && isDeployedSkill(selectedSkill!)
										? 'bg-cyan-50 dark:bg-cyan-900/20 border-l-2 border-l-cyan-500'
										: 'hover:bg-slate-50 dark:hover:bg-slate-700/30 border-l-2 border-l-transparent'}"
							>
								<div class="flex-1 min-w-0">
									<div class="flex items-center gap-2">
										<span class="font-medium text-slate-900 dark:text-slate-100 truncate">{skill.name}</span>
										{#if skill.category}
											<Badge text={skill.category} variant="default" />
										{/if}
									</div>
									<div class="mt-1 flex items-center gap-2">
										<Badge text={formatDeployMode(skill.deploy_mode)} variant={getDeployModeVariant(skill.deploy_mode)} />
										{#if skill.collection}
											<span class="text-xs text-slate-500 dark:text-slate-400">{skill.collection}</span>
										{/if}
									</div>
								</div>
								{#if skill.is_user_requested}
									<span title="User requested">
										<svg class="w-4 h-4 text-amber-500 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
											<path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
										</svg>
									</span>
								{/if}
							</button>
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
					<div class="divide-y divide-slate-100 dark:divide-slate-700/50">
						{#each filteredAvailable as skill (skill.name)}
							<button
								onclick={() => onSelect(skill)}
								class="w-full text-left px-4 py-2.5 flex items-center gap-3 text-sm transition-colors
									{getSelectedName(selectedSkill) === skill.name && !isDeployedSkill(selectedSkill!)
										? 'bg-cyan-50 dark:bg-cyan-900/20 border-l-2 border-l-cyan-500'
										: 'hover:bg-slate-50 dark:hover:bg-slate-700/30 border-l-2 border-l-transparent'}"
							>
								<div class="flex-1 min-w-0">
									<div class="flex items-center gap-2">
										<span class="font-medium text-slate-900 dark:text-slate-100 truncate">{skill.name}</span>
										{#if skill.is_deployed}
											<svg class="w-4 h-4 text-green-500 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
												<path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd" />
											</svg>
										{/if}
										{#if skill.category}
											<Badge text={skill.category} variant="default" />
										{/if}
									</div>
									{#if skill.description}
										<p class="mt-0.5 text-xs text-slate-500 dark:text-slate-400 truncate">{skill.description}</p>
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
