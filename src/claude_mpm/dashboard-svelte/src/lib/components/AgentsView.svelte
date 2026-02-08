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

	function getStatusIcon(status: AgentNode['status']): string {
		switch (status) {
			case 'active':
				return '🔵';
			case 'completed':
				return '✅';
			case 'error':
				return '❌';
			default:
				return '❓';
		}
	}

	function getAgentTypeIcon(agentType: string): string {
		const type = agentType.toLowerCase();
		if (type === 'pm') return '🤖';
		if (type.includes('research')) return '🔍';
		if (type.includes('engineer') || type.includes('svelte')) return '🛠️';
		if (type.includes('qa') || type.includes('test')) return '✅';
		if (type.includes('ops') || type.includes('local')) return '⚙️';
		if (type.includes('security')) return '🔒';
		if (type.includes('data')) return '📊';
		return '👤'; // Default agent icon
	}

	function formatAgentName(agentType: string): string {
		// Convert agent_type to display name (e.g., "svelte-engineer" -> "Svelte Engineer")
		return agentType
			.split(/[-_]/)
			.map(word => word.charAt(0).toUpperCase() + word.slice(1))
			.join(' ');
	}

	function getStatusColor(status: AgentNode['status']): string {
		switch (status) {
			case 'active':
				return 'text-blue-600 dark:text-blue-400';
			case 'completed':
				return 'text-green-600 dark:text-green-400';
			case 'error':
				return 'text-red-600 dark:text-red-400';
			default:
				return 'text-slate-600 dark:text-slate-400';
		}
	}

	function formatDuration(startTime: number, endTime: number | null): string {
		const end = endTime || Date.now();
		const ms = end - startTime;

		if (ms < 1000) {
			return `${ms}ms`;
		} else if (ms < 60000) {
			return `${(ms / 1000).toFixed(1)}s`;
		} else {
			const minutes = Math.floor(ms / 60000);
			const seconds = Math.floor((ms % 60000) / 1000);
			return `${minutes}m ${seconds}s`;
		}
	}

	// Recursive component for rendering tree nodes
	function AgentTreeNode(props: { agent: AgentNode; depth: number }) {
		const { agent, depth } = props;
		const isCollapsed = collapsedNodes.has(agent.id);
		const hasChildren = agent.children.length > 0;
		const indentPx = depth * 24;

		return {
			agent,
			depth,
			isCollapsed,
			hasChildren,
			indentPx
		};
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

	// Count stats for display
	let stats = $derived.by(() => {
		const allNodes = flattenTree(rootAgent, 0);
		const totalAgents = allNodes.length;
		const activeAgents = allNodes.filter(n => n.agent.status === 'active').length;
		const totalTools = allNodes.reduce((sum, n) => sum + n.agent.toolCalls.length, 0);
		const totalTodos = allNodes.reduce((sum, n) => sum + n.agent.todos.length, 0);
		const totalTokens = allNodes.reduce((sum, n) => sum + n.agent.tokenUsage.totalTokens, 0);

		return { totalAgents, activeAgents, totalTools, totalTodos, totalTokens };
	});
</script>

<div class="flex flex-col h-full bg-white dark:bg-slate-900">
	<!-- Header with stats -->
	<div class="flex items-center justify-between px-6 py-3 bg-slate-100 dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700 transition-colors">
		<div class="flex items-center gap-4">
			<span class="text-sm text-slate-700 dark:text-slate-300">
				{stats.totalAgents} agents
			</span>
			<span class="text-sm text-slate-700 dark:text-slate-300">
				{stats.activeAgents} active
			</span>
			<span class="text-sm text-slate-700 dark:text-slate-300">
				{stats.totalTools} tools
			</span>
			<span class="text-sm text-slate-700 dark:text-slate-300">
				{stats.totalTodos} todos
			</span>
			<span class="text-sm text-slate-700 dark:text-slate-300 font-mono font-semibold">
				{stats.totalTokens.toLocaleString()} tokens
			</span>
		</div>
	</div>

	<div class="flex-1 overflow-y-auto">
		{#if rootAgent.children.length === 0}
			<div class="text-center py-12 text-slate-600 dark:text-slate-400">
				<svg class="w-16 h-16 mx-auto mb-3 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
				</svg>
				<p class="text-lg mb-2 font-medium">No agents detected</p>
				<p class="text-sm text-slate-500 dark:text-slate-500">Waiting for agent activity...</p>
			</div>
		{:else}
			<!-- Agent tree -->
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
						class="w-full text-left px-4 py-2.5 transition-colors border-l-4 flex items-center gap-2 text-sm cursor-pointer
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
							<!-- Agent type icon -->
							<span class="text-base" title="{agent.name}">
								{getAgentTypeIcon(agent.name)}
							</span>

							<!-- Status icon -->
							<span class="text-sm">
								{getStatusIcon(agent.status)}
							</span>

							<!-- Agent name -->
							<span class="font-semibold text-slate-900 dark:text-slate-100">
								{formatAgentName(agent.name)}
							</span>

							<!-- Session ID (secondary info) -->
							{#if agent.sessionId !== 'pm' && agent.sessionId !== agent.name}
								<code class="text-xs text-slate-500 dark:text-slate-500 font-mono" title="Session ID: {agent.sessionId}">
									{agent.sessionId.slice(0, 8)}
								</code>
							{/if}

							<!-- Stats badges -->
							<div class="flex items-center gap-2">
								{#if agent.toolCalls.length > 0}
									<span class="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold bg-blue-500/20 text-blue-600 dark:text-blue-400 border border-blue-500/30">
										{agent.toolCalls.length} tools
									</span>
								{/if}

								{#if agent.todos.length > 0}
									<span class="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold bg-purple-500/20 text-purple-600 dark:text-purple-400 border border-purple-500/30">
										{agent.todos.length} todos
									</span>
								{/if}

								{#if agent.children.length > 0}
									<span class="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-500/20 text-slate-600 dark:text-slate-400 border border-slate-500/30">
										{agent.children.length} sub-agents
									</span>
								{/if}
							</div>

							<!-- Duration -->
							<span class="text-xs text-slate-600 dark:text-slate-400 font-mono ml-auto">
								{formatDuration(agent.startTime, agent.endTime)}
							</span>
						</div>
					</div>
				{/each}
			</div>
		{/if}
	</div>
</div>
