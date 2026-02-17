<script lang="ts">
	import type { AgentNode } from '$lib/stores/agents.svelte';

	let {
		rootAgent,
		selectedAgent = $bindable(null),
		selectedStream = ''
	}: {
		rootAgent: AgentNode;
		selectedAgent: AgentNode | null;
		selectedStream: string;
	} = $props();

	// Track collapsed state for each agent
	let collapsedNodes = $state<Set<string>>(new Set());

	function toggleNode(agentId: string) {
		const newSet = new Set(collapsedNodes);
		if (newSet.has(agentId)) {
			newSet.delete(agentId);
		} else {
			newSet.add(agentId);
		}
		collapsedNodes = newSet;
	}

	function selectAgent(agent: AgentNode) {
		selectedAgent = agent;
	}

	function formatAgentName(agentType: string): string {
		return agentType
			.split(/[-_]/)
			.map(word => word.charAt(0).toUpperCase() + word.slice(1))
			.join(' ');
	}

	function formatNumber(num: number): string {
		return num.toLocaleString();
	}

	// Flatten tree for rendering (respecting collapsed state)
	function flattenTree(node: AgentNode, depth: number = 0): Array<{ agent: AgentNode; depth: number }> {
		const result = [{ agent: node, depth }];

		if (!collapsedNodes.has(node.id) && node.children.length > 0) {
			node.children.forEach(child => {
				result.push(...flattenTree(child, depth + 1));
			});
		}

		return result;
	}

	let flatNodes = $derived(flattenTree(rootAgent));

	// Calculate total token stats
	let totalStats = $derived.by(() => {
		const allNodes = flattenTree(rootAgent, 0);
		let totalInput = 0;
		let totalOutput = 0;
		let totalCacheCreation = 0;
		let totalCacheRead = 0;

		allNodes.forEach(({ agent }) => {
			totalInput += agent.tokenUsage.inputTokens;
			totalOutput += agent.tokenUsage.outputTokens;
			totalCacheCreation += agent.tokenUsage.cacheCreationTokens;
			totalCacheRead += agent.tokenUsage.cacheReadTokens;
		});

		const totalTokens = totalInput + totalOutput + totalCacheCreation + totalCacheRead;

		return {
			totalInput,
			totalOutput,
			totalCacheCreation,
			totalCacheRead,
			totalTokens
		};
	});

	// Calculate cache efficiency
	let cacheEfficiency = $derived.by(() => {
		const { totalCacheRead, totalCacheCreation, totalInput, totalOutput } = totalStats;
		const billableTokens = totalInput + totalCacheCreation + (totalCacheRead * 0.1); // Cache reads are 10% cost
		const totalConsumption = totalInput + totalOutput + totalCacheCreation + totalCacheRead;

		if (totalConsumption === 0) return 0;
		return Math.round(((totalConsumption - billableTokens) / totalConsumption) * 100);
	});
</script>

<div class="flex flex-col h-full bg-white dark:bg-slate-900">
	<!-- Header with total stats -->
	<div class="flex flex-col gap-4 px-6 py-4 bg-slate-100 dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700 transition-colors">
		<div class="grid grid-cols-2 gap-4">
			<div class="flex flex-col">
				<span class="text-xs text-slate-600 dark:text-slate-400 font-semibold uppercase">Total Tokens</span>
				<span class="text-2xl font-bold text-slate-900 dark:text-slate-100 font-mono">
					{formatNumber(totalStats.totalTokens)}
				</span>
			</div>
			<div class="flex flex-col">
				<span class="text-xs text-slate-600 dark:text-slate-400 font-semibold uppercase">Cache Efficiency</span>
				<span class="text-2xl font-bold text-green-600 dark:text-green-400 font-mono">
					{cacheEfficiency}%
				</span>
			</div>
		</div>

		<!-- Breakdown grid -->
		<div class="grid grid-cols-4 gap-3">
			<div class="bg-white dark:bg-slate-700/50 rounded px-3 py-2">
				<span class="text-xs text-slate-600 dark:text-slate-400 font-semibold">Input</span>
				<div class="text-lg font-bold text-blue-600 dark:text-blue-400 font-mono">
					{formatNumber(totalStats.totalInput)}
				</div>
			</div>
			<div class="bg-white dark:bg-slate-700/50 rounded px-3 py-2">
				<span class="text-xs text-slate-600 dark:text-slate-400 font-semibold">Output</span>
				<div class="text-lg font-bold text-cyan-600 dark:text-cyan-400 font-mono">
					{formatNumber(totalStats.totalOutput)}
				</div>
			</div>
			<div class="bg-white dark:bg-slate-700/50 rounded px-3 py-2">
				<span class="text-xs text-slate-600 dark:text-slate-400 font-semibold">Cache Write</span>
				<div class="text-lg font-bold text-purple-600 dark:text-purple-400 font-mono">
					{formatNumber(totalStats.totalCacheCreation)}
				</div>
			</div>
			<div class="bg-white dark:bg-slate-700/50 rounded px-3 py-2">
				<span class="text-xs text-slate-600 dark:text-slate-400 font-semibold">Cache Read</span>
				<div class="text-lg font-bold text-green-600 dark:text-green-400 font-mono">
					{formatNumber(totalStats.totalCacheRead)}
				</div>
			</div>
		</div>
	</div>

	<!-- Agent token list -->
	<div class="flex-1 overflow-y-auto">
		{#if rootAgent.children.length === 0}
			<div class="text-center py-12 text-slate-600 dark:text-slate-400">
				<svg class="w-16 h-16 mx-auto mb-3 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
				</svg>
				<p class="text-lg mb-2 font-medium">No token data</p>
				<p class="text-sm text-slate-500 dark:text-slate-500">Token usage will appear as agents run...</p>
			</div>
		{:else}
			<!-- Token breakdown by agent -->
			<div class="py-2">
				{#each flatNodes as { agent, depth }, i (agent.id)}
					<div
						onclick={() => selectAgent(agent)}
						role="button"
						tabindex="0"
						onkeydown={(e) => {
							if (e.key === 'Enter' || e.key === ' ') {
								e.preventDefault();
								selectAgent(agent);
							}
						}}
						class="w-full text-left px-4 py-2.5 transition-colors border-l-4 flex items-center gap-3 text-sm cursor-pointer
							{selectedAgent?.id === agent.id
								? 'bg-cyan-50 dark:bg-cyan-500/20 border-l-cyan-500 dark:border-l-cyan-400 ring-1 ring-cyan-300 dark:ring-cyan-500/30'
								: `border-l-transparent ${i % 2 === 0 ? 'bg-slate-50 dark:bg-slate-800/40' : 'bg-white dark:bg-slate-800/20'} hover:bg-slate-100 dark:hover:bg-slate-700/30`}"
						style="padding-left: {depth * 24 + 16}px"
					>
						<!-- Expand/collapse button -->
						{#if agent.children.length > 0}
							<div
								onclick={(e) => {
									e.stopPropagation();
									toggleNode(agent.id);
								}}
								role="button"
								tabindex="0"
								onkeydown={(e) => {
									if (e.key === 'Enter' || e.key === ' ') {
										e.preventDefault();
										e.stopPropagation();
										toggleNode(agent.id);
									}
								}}
								class="flex-shrink-0 w-4 h-4 flex items-center justify-center text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 cursor-pointer"
							>
								{#if collapsedNodes.has(agent.id)}
									<svg class="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
										<path fill-rule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clip-rule="evenodd" />
									</svg>
								{:else}
									<svg class="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
										<path fill-rule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clip-rule="evenodd" />
									</svg>
								{/if}
							</div>
						{:else}
							<div class="w-4"></div>
						{/if}

						<!-- Agent info -->
						<div class="flex-1 flex items-center gap-3">
							<!-- Agent name -->
							<span class="font-semibold text-slate-900 dark:text-slate-100">
								{formatAgentName(agent.name)}
							</span>

							<!-- Token stats badges -->
							<div class="flex items-center gap-2">
								{#if agent.tokenUsage.inputTokens > 0}
									<span class="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold bg-blue-500/20 text-blue-600 dark:text-blue-400 border border-blue-500/30">
										In: {formatNumber(agent.tokenUsage.inputTokens)}
									</span>
								{/if}

								{#if agent.tokenUsage.outputTokens > 0}
									<span class="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold bg-cyan-500/20 text-cyan-600 dark:text-cyan-400 border border-cyan-500/30">
										Out: {formatNumber(agent.tokenUsage.outputTokens)}
									</span>
								{/if}

								{#if agent.tokenUsage.cacheCreationTokens > 0}
									<span class="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold bg-purple-500/20 text-purple-600 dark:text-purple-400 border border-purple-500/30">
										CW: {formatNumber(agent.tokenUsage.cacheCreationTokens)}
									</span>
								{/if}

								{#if agent.tokenUsage.cacheReadTokens > 0}
									<span class="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold bg-green-500/20 text-green-600 dark:text-green-400 border border-green-500/30">
										CR: {formatNumber(agent.tokenUsage.cacheReadTokens)}
									</span>
								{/if}
							</div>

							<!-- Total tokens -->
							<span class="text-sm font-bold text-slate-900 dark:text-slate-100 font-mono ml-auto">
								{formatNumber(agent.tokenUsage.totalTokens)}
							</span>
						</div>
					</div>
				{/each}
			</div>
		{/if}
	</div>
</div>
