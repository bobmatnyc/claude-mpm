<script lang="ts">
	import { onMount } from 'svelte';
	import {
		skillLinksStore, loadSkillLinks,
		type AgentSkillLinks, type SkillLinksData,
	} from '$lib/stores/config/skillLinks.svelte';
	import AgentSkillPanel from './AgentSkillPanel.svelte';
	import SkillChipList from './SkillChipList.svelte';

	let storeState = $state<{
		data: SkillLinksData | null;
		loading: boolean;
		error: string | null;
		loaded: boolean;
	}>({ data: null, loading: false, error: null, loaded: false });

	$effect(() => {
		const unsub = skillLinksStore.subscribe(v => { storeState = v; });
		return unsub;
	});

	let selectedAgent = $state<AgentSkillLinks | null>(null);

	// Stats derived from data
	let totalAgents = $derived(storeState.data?.total_agents ?? 0);
	let totalSkills = $derived(storeState.data?.total_skills ?? 0);
	let agents = $derived(storeState.data?.agents ?? []);
	let avgSkillsPerAgent = $derived(
		totalAgents > 0 ? Math.round((totalSkills / totalAgents) * 10) / 10 : 0
	);

	onMount(() => {
		loadSkillLinks();
	});

	function handleSelectAgent(agent: AgentSkillLinks) {
		selectedAgent = agent;
	}
</script>

<div class="flex flex-col h-full">
	<!-- Stats bar -->
	<div class="flex items-center gap-4 px-4 py-2.5 bg-slate-50 dark:bg-slate-800/60 border-b border-slate-200 dark:border-slate-700">
		{#if storeState.loading}
			<span class="text-xs text-slate-500 dark:text-slate-400">Loading skill links...</span>
		{:else if storeState.error}
			<span class="text-xs text-red-500 dark:text-red-400">{storeState.error}</span>
			<button
				onclick={() => loadSkillLinks()}
				class="text-xs text-cyan-500 hover:text-cyan-400 transition-colors"
			>
				Retry
			</button>
		{:else}
			<span class="text-xs text-slate-600 dark:text-slate-300">
				<span class="font-semibold">{totalAgents}</span> agents
			</span>
			<span class="text-xs text-slate-600 dark:text-slate-300">
				<span class="font-semibold">{totalSkills}</span> skills
			</span>
			<span class="text-xs text-slate-600 dark:text-slate-300">
				<span class="font-semibold">{avgSkillsPerAgent}</span> avg/agent
			</span>
		{/if}
	</div>

	<!-- Dual-panel layout -->
	<div class="flex-1 min-h-0 flex">
		<!-- Left panel: Agent list -->
		<div class="w-1/2 border-r border-slate-200 dark:border-slate-700 flex flex-col min-h-0">
			<AgentSkillPanel
				{agents}
				loading={storeState.loading}
				{selectedAgent}
				onSelect={handleSelectAgent}
			/>
		</div>

		<!-- Right panel: Skills for selected agent -->
		<div class="w-1/2 flex flex-col min-h-0">
			<SkillChipList agent={selectedAgent} />
		</div>
	</div>
</div>
