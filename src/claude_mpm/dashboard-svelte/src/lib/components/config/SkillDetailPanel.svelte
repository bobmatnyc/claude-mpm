<script lang="ts">
	import { fetchSkillDetail, type SkillDetailData, type DeployedSkill, type AvailableSkill } from '$lib/stores/config.svelte';
	import Badge from '$lib/components/Badge.svelte';
	import CollapsibleSection from '$lib/components/shared/CollapsibleSection.svelte';
	import MetadataGrid from '$lib/components/shared/MetadataGrid.svelte';
	import MarkdownViewer from '$lib/components/MarkdownViewer.svelte';

	interface Props {
		skill: DeployedSkill | AvailableSkill;
		onNavigateToAgent?: (agentName: string) => void;
		onDeploy?: (name: string) => void;
		onUndeploy?: (name: string) => void;
	}

	let { skill, onNavigateToAgent, onDeploy, onUndeploy }: Props = $props();

	let detailData = $state<SkillDetailData | null>(null);
	let loading = $state(false);
	let error = $state<string | null>(null);
	let is404 = $state(false);

	// Immutable skill collections
	const IMMUTABLE_COLLECTIONS = ['PM_CORE_SKILLS', 'CORE_SKILLS'];

	function isDeployedSkill(s: DeployedSkill | AvailableSkill): s is DeployedSkill {
		return 'deploy_mode' in s;
	}

	function isSystemSkill(s: DeployedSkill | AvailableSkill): boolean {
		if (isDeployedSkill(s)) {
			return IMMUTABLE_COLLECTIONS.includes(s.collection);
		}
		return false;
	}

	function formatTokens(count?: number): string {
		if (!count || count === 0) return '';
		if (count >= 1000) return `${(count / 1000).toFixed(1)}k`;
		return `${count}`;
	}

	function formatDate(dateStr?: string): string {
		if (!dateStr) return '\u2014';
		try {
			return new Date(dateStr).toLocaleDateString(undefined, {
				year: 'numeric', month: 'short', day: 'numeric',
			});
		} catch {
			return dateStr;
		}
	}

	let skillName = $derived(skill.name);

	// Immediate data from list-level prop
	let listDescription = $derived(skill.description);
	let listVersion = $derived(skill.version);
	let listTags = $derived(skill.tags ?? []);
	let isSystem = $derived(isSystemSkill(skill));
	let isDeployed = $derived(
		isDeployedSkill(skill) || (skill as AvailableSkill).is_deployed
	);
	let isUserRequested = $derived(isDeployedSkill(skill) ? skill.is_user_requested : false);

	// Immediate metadata from list data
	let listMetadataItems = $derived.by(() => {
		const items: { label: string; value: string }[] = [];
		const tc = isDeployedSkill(skill) ? skill.toolchain : (skill as AvailableSkill).toolchain;
		items.push({ label: 'Toolchain', value: tc || 'Universal' });
		const ft = isDeployedSkill(skill) ? skill.full_tokens : (skill as AvailableSkill).full_tokens;
		if (ft && ft > 0) {
			items.push({ label: 'Full Tokens', value: `${formatTokens(ft)} tokens` });
		}
		const ept = isDeployedSkill(skill) ? skill.entry_point_tokens : (skill as AvailableSkill).entry_point_tokens;
		if (ept && ept > 0) {
			items.push({ label: 'Entry Tokens', value: `${formatTokens(ept)} tokens` });
		}
		const fw = isDeployedSkill(skill) ? skill.framework : (skill as AvailableSkill).framework;
		if (fw) {
			items.push({ label: 'Framework', value: fw });
		}
		return items;
	});

	// Fetch detail whenever the skill changes
	$effect(() => {
		const name = skillName;
		if (!name) return;

		let cancelled = false;
		loading = true;
		error = null;
		is404 = false;
		detailData = null;

		fetchSkillDetail(name).then((data) => {
			if (cancelled) return;
			detailData = data;
			if (!data) {
				is404 = true;
				error = 'Extended details unavailable for this skill';
			}
		}).catch((e) => {
			if (cancelled) return;
			if (e?.status === 404 || e?.message?.includes('404')) {
				is404 = true;
				error = 'Extended details unavailable for this skill';
			} else {
				error = e?.message || 'Failed to load skill details';
			}
		}).finally(() => {
			if (cancelled) return;
			loading = false;
		});

		return () => { cancelled = true; };
	});

	// MetadataGrid items (upgraded when detail loads)
	let metadataItems = $derived.by(() => {
		if (!detailData) return listMetadataItems;
		const items: { label: string; value: string }[] = [];
		items.push({ label: 'Toolchain', value: detailData.toolchain || 'Universal' });
		if (detailData.full_tokens && detailData.full_tokens > 0) {
			items.push({ label: 'Full Tokens', value: `${formatTokens(detailData.full_tokens)} tokens` });
		}
		if (detailData.entry_point_tokens && detailData.entry_point_tokens > 0) {
			items.push({ label: 'Entry Tokens', value: `${formatTokens(detailData.entry_point_tokens)} tokens` });
		}
		if (detailData.updated) {
			items.push({ label: 'Updated', value: formatDate(detailData.updated) });
		}
		if (detailData.framework) {
			items.push({ label: 'Framework', value: detailData.framework });
		}
		return items;
	});

	// Count helpers
	let usedByCount = $derived(detailData?.used_by_agents?.length ?? 0);
	let requiresCount = $derived(detailData?.requires?.length ?? 0);
	let referencesCount = $derived(detailData?.references?.length ?? 0);

	// Use best available data for display
	let displayName = $derived(detailData?.frontmatter_name || detailData?.name || skillName);
	let displayDescription = $derived(
		detailData
			? (detailData.description || detailData.when_to_use || 'No description available')
			: (listDescription || 'No description available')
	);
	let displayVersion = $derived(detailData?.version ?? listVersion);
	let displayTags = $derived.by(() => {
		if (detailData) {
			return [...new Set([...(detailData.tags ?? []), ...(detailData.frontmatter_tags ?? [])])];
		}
		return listTags;
	});
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
		{#if isSystem}
			<svg class="w-4 h-4 text-slate-400 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20" title="System skill">
				<path fill-rule="evenodd" d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z" clip-rule="evenodd" />
			</svg>
		{/if}
		<h2 class="text-lg font-bold text-slate-900 dark:text-slate-100">{displayName}</h2>
		{#if displayVersion}
			<Badge text="v{displayVersion}" variant="default" />
		{/if}
		{#if isDeployed}
			<Badge text="Deployed" variant="success" />
		{:else}
			<Badge text="Available" variant="default" />
		{/if}
		{#if isUserRequested}
			<Badge text="User Requested" variant="warning" />
		{/if}
	</div>

	<!-- Description: ALWAYS rendered immediately with fallback chain -->
	<div class="mb-4">
		<p class="text-sm {displayDescription === 'No description available' ? 'text-slate-400 dark:text-slate-500 italic' : 'text-slate-700 dark:text-slate-300'}">{displayDescription}</p>
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

	<!-- Summary (from detail only, show when available) -->
	{#if detailData?.summary}
		<div class="mb-4">
			<h3 class="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-1">Summary</h3>
			<p class="text-sm text-slate-700 dark:text-slate-300">{detailData.summary}</p>
		</div>
	{/if}

	<!-- Collapsible sections: skeleton while loading, real content when detail loaded -->
	{#if loading}
		<div class="animate-pulse space-y-2">
			<div class="h-10 bg-slate-100 dark:bg-slate-800 rounded-lg"></div>
			<div class="h-10 bg-slate-100 dark:bg-slate-800 rounded-lg"></div>
		</div>
	{:else if detailData}
		<div class="space-y-2">
			<!-- When to Use -->
			{#if detailData.when_to_use}
				<CollapsibleSection title="When to Use" defaultExpanded={true}>
					<p class="text-sm text-slate-700 dark:text-slate-300">{detailData.when_to_use}</p>
				</CollapsibleSection>
			{/if}

			<!-- Used By Agents -->
			<CollapsibleSection title="Used By" count={detailData.agent_count ?? usedByCount} defaultExpanded={true}>
				{#if usedByCount > 0}
					<div class="flex flex-wrap gap-1.5">
						{#each detailData.used_by_agents ?? [] as agentName}
							{#if onNavigateToAgent}
								<button
									onclick={() => onNavigateToAgent?.(agentName)}
									class="px-2 py-0.5 text-xs rounded-full bg-slate-100 dark:bg-slate-800 text-blue-600 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/30 hover:underline transition-colors cursor-pointer"
									title="View agent: {agentName}"
								>
									{agentName}
								</button>
							{:else}
								<span class="px-2 py-0.5 text-xs rounded-full bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400">
									{agentName}
								</span>
							{/if}
						{/each}
					</div>
				{:else}
					<p class="text-xs text-slate-400 dark:text-slate-500 italic">Not referenced by any agents</p>
				{/if}
			</CollapsibleSection>

			<!-- Dependencies / Requires -->
			{#if requiresCount > 0}
				<CollapsibleSection title="Dependencies" count={requiresCount}>
					<div class="flex flex-wrap gap-1.5">
						{#each detailData.requires ?? [] as dep}
							<Badge text={dep} variant="default" />
						{/each}
					</div>
				</CollapsibleSection>
			{/if}

			<!-- References -->
			{#if referencesCount > 0}
				<CollapsibleSection title="References" count={referencesCount}>
					<div class="space-y-1.5">
						{#each detailData.references ?? [] as ref}
							<div class="flex items-start gap-2 text-sm">
								<span class="font-mono text-xs text-slate-600 dark:text-slate-400 bg-slate-100 dark:bg-slate-800 px-1.5 py-0.5 rounded shrink-0 break-all">{ref.path}</span>
								{#if ref.purpose}
									<span class="text-xs text-slate-500 dark:text-slate-400">{ref.purpose}</span>
								{/if}
							</div>
						{/each}
					</div>
				</CollapsibleSection>
			{/if}

			<!-- Full Skill Content -->
			{#if detailData.content}
				<CollapsibleSection
					title="Skill Content"
					defaultExpanded={true}
				>
					<div class="max-h-[600px] overflow-y-auto rounded border border-slate-200 dark:border-slate-700 p-4">
						<MarkdownViewer content={detailData.content} />
					</div>
					{#if detailData.content_size && detailData.content_size > 20000}
						<p class="mt-1 text-xs text-slate-400 dark:text-slate-500 italic">
							Large skill ({Math.round(detailData.content_size / 1024)} KB) - scroll to see full content
						</p>
					{/if}
				</CollapsibleSection>
			{/if}
		</div>

		<!-- Footer: author, updated, languages, source path -->
		<div class="mt-6 pt-4 border-t border-slate-200 dark:border-slate-700">
			<div class="grid grid-cols-2 gap-3 text-xs">
				{#if detailData.author}
					<div>
						<span class="text-slate-500 dark:text-slate-400">Author:</span>
						<span class="ml-1 text-slate-700 dark:text-slate-300">{detailData.author}</span>
					</div>
				{/if}
				{#if detailData.updated}
					<div>
						<span class="text-slate-500 dark:text-slate-400">Updated:</span>
						<span class="ml-1 text-slate-700 dark:text-slate-300">{formatDate(detailData.updated)}</span>
					</div>
				{/if}
				{#if detailData.languages}
					<div>
						<span class="text-slate-500 dark:text-slate-400">Languages:</span>
						<span class="ml-1 text-slate-700 dark:text-slate-300">{detailData.languages}</span>
					</div>
				{/if}
				{#if detailData.source_path}
					<div class="col-span-2">
						<span class="text-slate-500 dark:text-slate-400">Source:</span>
						<span class="ml-1 text-slate-700 dark:text-slate-300 font-mono break-all">{detailData.source_path}</span>
					</div>
				{/if}
			</div>
		</div>
	{/if}

	<!-- Deploy/Undeploy action button -->
	{#if onDeploy || onUndeploy}
		<div class="mt-6 pt-4 border-t border-slate-200 dark:border-slate-700">
			{#if isDeployed && !isSystem && onUndeploy}
				<button
					onclick={() => onUndeploy?.(skillName)}
					class="w-full px-4 py-2 text-sm font-medium text-red-400 bg-red-500/10 hover:bg-red-500/20 rounded-lg transition-colors flex items-center justify-center gap-2"
				>
					<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
					</svg>
					Undeploy Skill
				</button>
			{:else if isSystem}
				<div class="flex items-center gap-2 text-xs text-slate-400 dark:text-slate-500 justify-center">
					<svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
						<path fill-rule="evenodd" d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z" clip-rule="evenodd" />
					</svg>
					System skill - cannot be undeployed
				</div>
			{:else if !isDeployed && onDeploy}
				<button
					onclick={() => onDeploy?.(skillName)}
					class="w-full px-4 py-2 text-sm font-medium text-white bg-cyan-600 hover:bg-cyan-700 rounded-lg transition-colors flex items-center justify-center gap-2"
				>
					<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
					</svg>
					Deploy Skill
				</button>
			{/if}
		</div>
	{/if}
</div>
