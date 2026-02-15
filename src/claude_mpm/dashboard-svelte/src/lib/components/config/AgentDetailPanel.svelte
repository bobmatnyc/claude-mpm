<script lang="ts">
	import { fetchAgentDetail, type AgentDetailData, type DeployedAgent, type AvailableAgent, type DeployedSkill } from '$lib/stores/config.svelte';
	import { deployedSkills } from '$lib/stores/config.svelte';
	import Badge from '$lib/components/Badge.svelte';
	import CollapsibleSection from '$lib/components/shared/CollapsibleSection.svelte';
	import MetadataGrid from '$lib/components/shared/MetadataGrid.svelte';
	import ColorDot from '$lib/components/shared/ColorDot.svelte';
	import SkillChipWithStatus from './SkillChipWithStatus.svelte';
	import { FEATURES } from '$lib/config/features';

	interface Props {
		agent: DeployedAgent | AvailableAgent;
		onNavigateToSkill?: (skillName: string) => void;
		onNavigateToAgent?: (agentName: string) => void;
		allAgentNames?: string[];
		onDeploy?: (name: string) => void;
		onUndeploy?: (name: string) => void;
	}

	let { agent, onNavigateToSkill, onNavigateToAgent, allAgentNames = [], onDeploy, onUndeploy }: Props = $props();

	let detailData = $state<AgentDetailData | null>(null);
	let loading = $state(false);
	let error = $state<string | null>(null);
	let is404 = $state(false);

	// Subscribe to deployed skills for status checking
	let deployedSkillNames = $state<Set<string>>(new Set());
	$effect(() => {
		const unsub = deployedSkills.subscribe(skills => {
			deployedSkillNames = new Set(skills.map(s => s.name));
		});
		return unsub;
	});

	// Suffix-matching helper: agent frontmatter uses short names (e.g. "git-workflow")
	// but deployed skills use full directory names (e.g. "universal-collaboration-git-workflow")
	function isSkillDeployed(shortName: string): boolean {
		// Exact match first
		if (deployedSkillNames.has(shortName)) return true;
		// Suffix match: check if any deployed skill ends with -{shortName}
		const suffix = `-${shortName}`;
		for (const deployed of deployedSkillNames) {
			if (deployed.endsWith(suffix)) return true;
		}
		return false;
	}

	function isDeployedAgent(a: DeployedAgent | AvailableAgent): a is DeployedAgent {
		return 'is_core' in a;
	}

	let agentName = $derived(
		isDeployedAgent(agent) ? agent.name : (agent as AvailableAgent).name
	);

	// Immediate data from list-level prop
	let listDescription = $derived(
		isDeployedAgent(agent) ? agent.description : (agent as AvailableAgent).description
	);
	let listVersion = $derived(agent.version);
	let listColor = $derived(isDeployedAgent(agent) ? agent.color : undefined);
	let listCategory = $derived(
		isDeployedAgent(agent) ? agent.category : (agent as AvailableAgent).category
	);
	let listTags = $derived(
		isDeployedAgent(agent) ? (agent.tags ?? []) : ((agent as AvailableAgent).tags ?? [])
	);
	let listResourceTier = $derived(isDeployedAgent(agent) ? agent.resource_tier : undefined);
	let listNetworkAccess = $derived(isDeployedAgent(agent) ? agent.network_access : undefined);

	// Determine deployment status from prop
	let isDeployed = $derived(
		isDeployedAgent(agent) || (agent as AvailableAgent).is_deployed
	);
	let isCore = $derived(isDeployedAgent(agent) ? agent.is_core : false);

	// Immediate metadata grid from list data (before detail loads)
	let listMetadataItems = $derived.by(() => {
		const items: { label: string; value: string }[] = [];
		const cat = listCategory;
		if (cat) items.push({ label: 'Category', value: cat });
		const rt = listResourceTier;
		if (rt) items.push({ label: 'Resource Tier', value: rt });
		if (listNetworkAccess !== null && listNetworkAccess !== undefined) {
			items.push({ label: 'Network', value: listNetworkAccess ? 'Enabled' : 'Disabled' });
		}
		return items;
	});

	// Temperature semantic label
	function temperatureLabel(temp: number | null | undefined): string {
		if (temp === null || temp === undefined) return '';
		if (temp === 0) return 'precise';
		if (temp <= 0.3) return 'focused';
		if (temp <= 0.7) return 'balanced';
		return 'creative';
	}

	// Fetch detail whenever the agent changes
	$effect(() => {
		const name = agentName;
		if (!name) return;

		let cancelled = false;
		loading = true;
		error = null;
		is404 = false;
		detailData = null;

		fetchAgentDetail(name).then((data) => {
			if (cancelled) return;
			detailData = data;
			if (!data) {
				is404 = true;
				error = 'Extended details unavailable for this agent';
			}
		}).catch((e) => {
			if (cancelled) return;
			if (e?.status === 404 || e?.message?.includes('404')) {
				is404 = true;
				error = 'Extended details unavailable for this agent';
			} else {
				error = e?.message || 'Failed to load agent details';
			}
		}).finally(() => {
			if (cancelled) return;
			loading = false;
		});

		return () => { cancelled = true; };
	});

	function formatDependencies(deps: Record<string, string[]>): { category: string; items: string[] }[] {
		return Object.entries(deps).map(([category, items]) => ({
			category,
			items: Array.isArray(items) ? items : [],
		}));
	}

	// Metadata grid items (full detail, replaces list-level when available)
	let metadataItems = $derived.by(() => {
		if (!detailData) return listMetadataItems;
		const items: { label: string; value: string; icon?: string }[] = [];
		if (detailData.category) items.push({ label: 'Category', value: detailData.category });
		if (detailData.resource_tier) items.push({ label: 'Resource Tier', value: detailData.resource_tier });
		if (detailData.network_access !== null && detailData.network_access !== undefined) {
			items.push({ label: 'Network', value: detailData.network_access ? 'Enabled' : 'Disabled' });
		}
		return items;
	});

	// Count helpers for sections
	let expertiseCount = $derived((detailData?.knowledge?.domain_expertise ?? []).length);
	let skillsCount = $derived((detailData?.skills ?? []).length);
	let depEntries = $derived(formatDependencies(detailData?.dependencies ?? {}));
	let depCount = $derived(depEntries.length);
	let constraintsCount = $derived((detailData?.knowledge?.constraints ?? []).length);
	let bestPracticesCount = $derived((detailData?.knowledge?.best_practices ?? []).length);

	// Handoff agents: filter out self-references
	let filteredHandoffAgents = $derived(
		(detailData?.handoff_agents ?? []).filter(ha => ha !== agentName)
	);
	let handoffCount = $derived(filteredHandoffAgents.length);

	// Count undeployed skills for warning
	let undeployedSkillCount = $derived(
		(detailData?.skills ?? []).filter(s => !isSkillDeployed(s)).length
	);

	// Set of all known agent names for navigability checking
	let allAgentNamesSet = $derived(new Set(allAgentNames));
	function isAgentNavigable(name: string): boolean {
		return allAgentNamesSet.has(name);
	}

	// Use best available data for display
	let displayName = $derived(detailData?.name ?? agentName);
	let displayDescription = $derived(detailData?.description ?? listDescription);
	let displayVersion = $derived(detailData?.version ?? listVersion);
	let displayColor = $derived(detailData?.color ?? listColor);
	let displayTags = $derived(detailData?.tags ?? listTags);
</script>

<div class="flex-1 overflow-y-auto p-6">
	<!-- Error banner (non-fatal, show above content) -->
	{#if error && !detailData}
		{#if is404}
			<div class="flex items-start gap-2 px-3 py-2 mb-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
				<svg class="w-4 h-4 text-blue-500 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
				</svg>
				<p class="text-xs text-blue-700 dark:text-blue-300">Extended details unavailable. Showing basic info from list data.</p>
			</div>
		{:else}
			<div class="flex items-start gap-2 px-3 py-2 mb-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
				<svg class="w-4 h-4 text-red-500 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
				</svg>
				<p class="text-xs text-red-700 dark:text-red-300">{error}</p>
			</div>
		{/if}
	{/if}

	<!-- Header: ALWAYS rendered immediately from list data -->
	<div class="flex items-center gap-3 mb-4">
		<ColorDot color={displayColor} size="md" />
		<h2 class="text-lg font-bold text-slate-900 dark:text-slate-100">{displayName}</h2>
		{#if displayVersion}
			<Badge text="v{displayVersion}" variant="default" />
		{/if}
		{#if isCore}
			<Badge text="Core" variant="primary" />
		{/if}
		{#if isDeployed}
			<Badge text="Deployed" variant="success" />
		{:else}
			<Badge text="Available" variant="default" />
		{/if}
	</div>

	<!-- Description: ALWAYS rendered immediately from list data -->
	<div class="mb-4">
		{#if displayDescription}
			<p class="text-sm text-slate-700 dark:text-slate-300">{displayDescription}</p>
		{:else}
			<p class="text-sm text-slate-400 dark:text-slate-500 italic">No description available</p>
		{/if}
	</div>

	<!-- MetadataGrid: rendered immediately from list data, upgraded when detail arrives -->
	{#if metadataItems.length > 0}
		<div class="mb-4">
			<MetadataGrid items={metadataItems} />
		</div>
	{/if}

	<!-- Tags: from list data immediately, upgraded when detail arrives -->
	{#if displayTags.length > 0}
		<div class="mb-4">
			<h3 class="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-1">Tags</h3>
			<div class="flex gap-1.5 flex-wrap">
				{#each displayTags as tag}
					<Badge text={tag} variant="info" />
				{/each}
			</div>
		</div>
	{/if}

	<!-- Collapsible sections: skeleton while loading, real content when detail loaded -->
	{#if loading}
		<div class="animate-pulse space-y-2">
			<div class="h-10 bg-slate-100 dark:bg-slate-800 rounded-lg"></div>
			<div class="h-10 bg-slate-100 dark:bg-slate-800 rounded-lg"></div>
			<div class="h-10 bg-slate-100 dark:bg-slate-800 rounded-lg"></div>
		</div>
	{:else if detailData}
		<div class="space-y-2">
			<!-- Expertise -->
			{#if expertiseCount > 0}
				<CollapsibleSection title="Expertise" count={expertiseCount}>
					<ul class="pl-4 text-sm text-slate-600 dark:text-slate-400 space-y-1 list-disc list-inside">
						{#each detailData.knowledge?.domain_expertise ?? [] as item}
							<li>{item}</li>
						{/each}
					</ul>
				</CollapsibleSection>
			{/if}

			<!-- Skills -->
			<CollapsibleSection title="Skills" count={skillsCount} defaultExpanded={true}>
				{#if skillsCount > 0}
					{#if undeployedSkillCount > 0}
						<div class="flex items-center gap-1.5 mb-2 px-2 py-1.5 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-md">
							<svg class="w-3.5 h-3.5 text-amber-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
							</svg>
							<span class="text-xs text-amber-700 dark:text-amber-300">{undeployedSkillCount} required skill{undeployedSkillCount === 1 ? '' : 's'} not deployed</span>
						</div>
					{/if}
					<div class="flex flex-wrap gap-1.5">
						{#each detailData.skills ?? [] as skill}
							<SkillChipWithStatus
								name={skill}
								isDeployed={isSkillDeployed(skill)}
								onclick={onNavigateToSkill ? () => onNavigateToSkill?.(skill) : undefined}
							/>
						{/each}
					</div>
				{:else}
					<p class="text-xs text-slate-400 dark:text-slate-500 italic">No skills defined</p>
				{/if}
			</CollapsibleSection>

			<!-- Dependencies -->
			{#if depCount > 0}
				<CollapsibleSection title="Dependencies" count={depCount}>
					<div class="space-y-2">
						{#each depEntries as dep}
							<div>
								<p class="text-xs font-medium text-slate-500 dark:text-slate-400 capitalize">{dep.category}</p>
								<div class="flex flex-wrap gap-1 mt-1">
									{#each dep.items as item}
										<span class="px-1.5 py-0 text-xs rounded bg-slate-100 dark:bg-slate-700/50 text-slate-600 dark:text-slate-400 font-mono">
											{item}
										</span>
									{/each}
								</div>
							</div>
						{/each}
					</div>
				</CollapsibleSection>
			{/if}

			<!-- Collaborates With (Handoff Agents) -->
			{#if handoffCount > 0 && FEATURES.COLLABORATION_LINKS}
				<CollapsibleSection title="Collaborates With" count={handoffCount}>
					<div class="space-y-1.5">
						<p class="text-xs font-medium text-slate-500 dark:text-slate-400">Hands off to:</p>
						<div class="flex flex-wrap gap-1.5">
							{#each filteredHandoffAgents as ha}
								{#if isAgentNavigable(ha) && onNavigateToAgent}
									<button
										onclick={() => onNavigateToAgent?.(ha)}
										class="inline-flex items-center gap-1 px-2 py-0.5 text-xs rounded-full bg-slate-100 dark:bg-slate-800 text-blue-600 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/30 hover:underline transition-colors cursor-pointer"
										title="View agent: {ha}"
									>
										<svg class="w-3 h-3 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
											<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 5l7 7m0 0l-7 7m7-7H3" />
										</svg>
										{ha}
									</button>
								{:else}
									<span class="inline-flex items-center gap-1 px-2 py-0.5 text-xs rounded-full bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400">
										<svg class="w-3 h-3 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
											<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 5l7 7m0 0l-7 7m7-7H3" />
										</svg>
										{ha}
									</span>
								{/if}
							{/each}
						</div>
					</div>
				</CollapsibleSection>
			{/if}

			<!-- Constraints -->
			{#if constraintsCount > 0}
				<CollapsibleSection title="Constraints" count={constraintsCount}>
					<ul class="pl-4 text-sm text-slate-600 dark:text-slate-400 space-y-1 list-disc list-inside">
						{#each detailData.knowledge?.constraints ?? [] as item}
							<li>{item}</li>
						{/each}
					</ul>
				</CollapsibleSection>
			{/if}

			<!-- Best Practices -->
			{#if bestPracticesCount > 0}
				<CollapsibleSection title="Best Practices" count={bestPracticesCount}>
					<ul class="pl-4 text-sm text-slate-600 dark:text-slate-400 space-y-1 list-disc list-inside">
						{#each detailData.knowledge?.best_practices ?? [] as item}
							<li>{item}</li>
						{/each}
					</ul>
				</CollapsibleSection>
			{/if}
		</div>

		<!-- Footer: author, temperature, timeout, agent type -->
		<div class="mt-6 pt-4 border-t border-slate-200 dark:border-slate-700">
			<div class="grid grid-cols-2 gap-3 text-xs">
				{#if detailData.author}
					<div>
						<span class="text-slate-500 dark:text-slate-400">Author:</span>
						<span class="ml-1 text-slate-700 dark:text-slate-300">{detailData.author}</span>
					</div>
				{/if}
				{#if detailData.temperature !== null && detailData.temperature !== undefined}
					<div>
						<span class="text-slate-500 dark:text-slate-400">Temperature:</span>
						<span class="ml-1 text-slate-700 dark:text-slate-300">
							{detailData.temperature}
							<span class="text-slate-400 dark:text-slate-500">({temperatureLabel(detailData.temperature)})</span>
						</span>
					</div>
				{/if}
				{#if detailData.timeout !== null && detailData.timeout !== undefined}
					<div>
						<span class="text-slate-500 dark:text-slate-400">Timeout:</span>
						<span class="ml-1 text-slate-700 dark:text-slate-300">{detailData.timeout}s</span>
					</div>
				{/if}
				{#if detailData.agent_type}
					<div>
						<span class="text-slate-500 dark:text-slate-400">Agent Type:</span>
						<span class="ml-1 text-slate-700 dark:text-slate-300">{detailData.agent_type}</span>
					</div>
				{/if}
			</div>
		</div>
	{/if}

	<!-- Deploy/Undeploy action button -->
	{#if onDeploy || onUndeploy}
		<div class="mt-6 pt-4 border-t border-slate-200 dark:border-slate-700">
			{#if isDeployed && !isCore && onUndeploy}
				<button
					onclick={() => onUndeploy?.(agentName)}
					class="w-full px-4 py-2 text-sm font-medium text-red-400 bg-red-500/10 hover:bg-red-500/20 rounded-lg transition-colors flex items-center justify-center gap-2"
				>
					<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
					</svg>
					Undeploy Agent
				</button>
			{:else if isCore}
				<div class="flex items-center gap-2 text-xs text-slate-400 dark:text-slate-500 justify-center">
					<svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
						<path fill-rule="evenodd" d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z" clip-rule="evenodd" />
					</svg>
					Core agent - cannot be undeployed
				</div>
			{:else if !isDeployed && onDeploy}
				<button
					onclick={() => onDeploy?.(agentName)}
					class="w-full px-4 py-2 text-sm font-medium text-white bg-cyan-600 hover:bg-cyan-700 rounded-lg transition-colors flex items-center justify-center gap-2"
				>
					<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
					</svg>
					Deploy Agent
				</button>
			{/if}
		</div>
	{/if}
</div>
