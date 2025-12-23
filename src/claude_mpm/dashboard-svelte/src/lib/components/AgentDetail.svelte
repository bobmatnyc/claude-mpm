<script lang="ts">
	import type { AgentNode } from '$lib/stores/agents.svelte';
	import type { ToolCall } from '$lib/stores/agents.svelte';

	let { agent, onToolClick }: { agent: AgentNode | null; onToolClick?: (toolCall: ToolCall) => void } = $props();

	function formatTimestamp(timestamp: number): string {
		return new Date(timestamp).toLocaleTimeString();
	}

	function formatDuration(durationMs: number | null): string {
		if (durationMs === null) return '—';

		if (durationMs < 1000) {
			return `${durationMs}ms`;
		} else if (durationMs < 60000) {
			return `${(durationMs / 1000).toFixed(2)}s`;
		} else {
			const minutes = Math.floor(durationMs / 60000);
			const seconds = ((durationMs % 60000) / 1000).toFixed(0);
			return `${minutes}m ${seconds}s`;
		}
	}

	function getToolStatusIcon(status: 'pending' | 'success' | 'error'): string {
		switch (status) {
			case 'pending':
				return '⏳';
			case 'success':
				return '✅';
			case 'error':
				return '❌';
			default:
				return '❓';
		}
	}

	function getToolStatusColor(status: 'pending' | 'success' | 'error'): string {
		switch (status) {
			case 'pending':
				return 'text-yellow-600 dark:text-yellow-400';
			case 'success':
				return 'text-green-600 dark:text-green-400';
			case 'error':
				return 'text-red-600 dark:text-red-400';
			default:
				return 'text-slate-600 dark:text-slate-400';
		}
	}

	function getTodoStatusIcon(status: 'pending' | 'in_progress' | 'completed'): string {
		switch (status) {
			case 'pending':
				return '⏳';
			case 'in_progress':
				return '🔄';
			case 'completed':
				return '✅';
			default:
				return '❓';
		}
	}

	function getTodoStatusColor(status: 'pending' | 'in_progress' | 'completed'): string {
		switch (status) {
			case 'pending':
				return 'text-slate-600 dark:text-slate-400';
			case 'in_progress':
				return 'text-blue-600 dark:text-blue-400';
			case 'completed':
				return 'text-green-600 dark:text-green-400';
			default:
				return 'text-slate-600 dark:text-slate-400';
		}
	}

	function formatAgentName(agentType: string): string {
		// Convert agent_type to display name (e.g., "svelte-engineer" -> "Svelte Engineer")
		return agentType
			.split(/[-_]/)
			.map(word => word.charAt(0).toUpperCase() + word.slice(1))
			.join(' ');
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

	function truncateText(text: string, maxLength: number = 200): { truncated: string; isTruncated: boolean } {
		if (text.length <= maxLength) {
			return { truncated: text, isTruncated: false };
		}
		return { truncated: text.slice(0, maxLength) + '...', isTruncated: true };
	}

	let expandedSections = $state<Record<string, boolean>>({
		userPrompt: false,
		delegationPrompt: false
	});

	function toggleSection(section: string) {
		expandedSections[section] = !expandedSections[section];
	}

	function getPlanStatusIcon(status: 'draft' | 'approved' | 'completed'): string {
		switch (status) {
			case 'draft':
				return '📝';
			case 'approved':
				return '✅';
			case 'completed':
				return '🎉';
			default:
				return '📋';
		}
	}

	function getPlanStatusColor(status: 'draft' | 'approved' | 'completed'): string {
		switch (status) {
			case 'draft':
				return 'text-slate-600 dark:text-slate-400';
			case 'approved':
				return 'text-green-600 dark:text-green-400';
			case 'completed':
				return 'text-blue-600 dark:text-blue-400';
			default:
				return 'text-slate-600 dark:text-slate-400';
		}
	}
</script>

{#if !agent}
	<div class="flex items-center justify-center h-full text-slate-500 dark:text-slate-400">
		<div class="text-center">
			<svg class="w-16 h-16 mx-auto mb-3 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
			</svg>
			<p class="text-lg">Select an agent to view details</p>
		</div>
	</div>
{:else}
	<div class="flex flex-col h-full bg-white dark:bg-slate-900">
		<!-- Header -->
		<div class="px-6 py-4 bg-slate-100 dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700 transition-colors">
			<h2 class="text-xl font-bold text-slate-900 dark:text-slate-100 mb-2 flex items-center gap-2">
				<span>{getAgentTypeIcon(agent.name)}</span>
				<span>{formatAgentName(agent.name)}</span>
			</h2>
			<div class="flex flex-wrap gap-3 text-sm text-slate-600 dark:text-slate-400">
				<div class="flex items-center gap-2">
					<span class="font-semibold">Session:</span>
					<code class="px-2 py-0.5 rounded bg-slate-200 dark:bg-slate-700 text-[11px] font-mono">
						{agent.sessionId}
					</code>
				</div>
				<div class="flex items-center gap-2">
					<span class="font-semibold">Status:</span>
					<span class="capitalize">{agent.status}</span>
				</div>
				<div class="flex items-center gap-2">
					<span class="font-semibold">Duration:</span>
					<span>{formatDuration(agent.endTime ? agent.endTime - agent.startTime : Date.now() - agent.startTime)}</span>
				</div>
			</div>
		</div>

		<!-- Content - Scrollable -->
		<div class="flex-1 overflow-y-auto p-6">
			<!-- User Prompt Section (PM only) -->
			{#if agent.userPrompt}
				{@const { truncated, isTruncated } = truncateText(agent.userPrompt)}
				<div class="mb-6">
					<h3 class="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-3 flex items-center gap-2">
						📝 User Request
					</h3>
					<div class="p-3 bg-blue-50 dark:bg-blue-900/20 rounded border border-blue-200 dark:border-blue-800">
						<p class="text-sm text-slate-700 dark:text-slate-300 whitespace-pre-wrap">
							{expandedSections.userPrompt || !isTruncated ? agent.userPrompt : truncated}
						</p>
						{#if isTruncated}
							<button
								class="mt-2 text-xs text-blue-600 dark:text-blue-400 hover:underline"
								onclick={() => toggleSection('userPrompt')}
							>
								{expandedSections.userPrompt ? 'Show less' : 'Show more'}
							</button>
						{/if}
					</div>
				</div>
			{/if}

			<!-- Delegation Prompt Section (Sub-agents only) -->
			{#if agent.delegationPrompt}
				{@const { truncated, isTruncated } = truncateText(agent.delegationPrompt)}
				<div class="mb-6">
					<h3 class="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-3 flex items-center gap-2">
						📤 Delegation Prompt
					</h3>
					{#if agent.delegationDescription}
						<p class="text-sm text-slate-600 dark:text-slate-400 mb-2 italic">
							{agent.delegationDescription}
						</p>
					{/if}
					<div class="p-3 bg-purple-50 dark:bg-purple-900/20 rounded border border-purple-200 dark:border-purple-800">
						<p class="text-sm text-slate-700 dark:text-slate-300 whitespace-pre-wrap">
							{expandedSections.delegationPrompt || !isTruncated ? agent.delegationPrompt : truncated}
						</p>
						{#if isTruncated}
							<button
								class="mt-2 text-xs text-purple-600 dark:text-purple-400 hover:underline"
								onclick={() => toggleSection('delegationPrompt')}
							>
								{expandedSections.delegationPrompt ? 'Show less' : 'Show more'}
							</button>
						{/if}
					</div>
				</div>
			{/if}

			<!-- Work Plans Section -->
			{#if agent.plans && agent.plans.length > 0}
				<div class="mb-6">
					<h3 class="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-3 flex items-center gap-2">
						📋 Work Plans
						<span class="text-sm font-normal text-slate-600 dark:text-slate-400">
							({agent.plans.length})
						</span>
					</h3>
					<div class="space-y-3">
						{#each agent.plans as plan, idx (idx)}
							{@const planId = `plan-${plan.timestamp}`}
							{@const { truncated, isTruncated } = truncateText(plan.content, 500)}
							<div class="p-4 bg-amber-50 dark:bg-amber-900/20 rounded border border-amber-200 dark:border-amber-800">
								<div class="flex items-center justify-between mb-3 pb-2 border-b border-amber-200 dark:border-amber-800">
									<div class="flex items-center gap-2">
										<span class="{getPlanStatusColor(plan.status)} text-lg">
											{getPlanStatusIcon(plan.status)}
										</span>
										<span class="text-xs text-slate-600 dark:text-slate-400 font-mono">
											{formatTimestamp(plan.timestamp)}
										</span>
										{#if plan.mode}
											<span class="text-xs px-2 py-0.5 rounded bg-amber-200 dark:bg-amber-700 text-slate-700 dark:text-slate-300">
												{plan.mode === 'entered' ? 'Entered Plan Mode' : 'Exited Plan Mode'}
											</span>
										{/if}
									</div>
									<span class="text-xs capitalize px-2 py-0.5 rounded {getPlanStatusColor(plan.status)}">
										{plan.status}
									</span>
								</div>
								{#if plan.planFile}
									<div class="mb-2 text-xs text-slate-600 dark:text-slate-400 font-mono">
										📄 {plan.planFile}
									</div>
								{/if}
								<div class="text-sm text-slate-700 dark:text-slate-300 whitespace-pre-wrap font-mono bg-slate-50 dark:bg-slate-800/40 p-3 rounded">
									{expandedSections[planId] || !isTruncated ? plan.content : truncated}
								</div>
								{#if isTruncated}
									<button
										class="mt-2 text-xs text-amber-600 dark:text-amber-400 hover:underline"
										onclick={() => toggleSection(planId)}
									>
										{expandedSections[planId] ? 'Show less' : 'Show more'}
									</button>
								{/if}
							</div>
						{/each}
					</div>
				</div>
			{/if}

			<!-- Responses Section -->
			{#if agent.responses && agent.responses.length > 0}
				<div class="mb-6">
					<h3 class="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-3 flex items-center gap-2">
						💬 Responses
						<span class="text-sm font-normal text-slate-600 dark:text-slate-400">
							({agent.responses.length})
						</span>
					</h3>
					<div class="space-y-3">
						{#each agent.responses as response (response.timestamp)}
							{@const responseId = `response-${response.timestamp}`}
							{@const { truncated, isTruncated } = truncateText(response.content)}
							<div class="p-3 bg-slate-50 dark:bg-slate-800/40 rounded border border-slate-200 dark:border-slate-700">
								<div class="flex items-center justify-between mb-2">
									<span class="text-xs text-slate-600 dark:text-slate-400 font-mono">
										{formatTimestamp(response.timestamp)}
									</span>
									<span class="text-xs px-2 py-0.5 rounded bg-slate-200 dark:bg-slate-700 text-slate-600 dark:text-slate-400">
										{response.type}
									</span>
								</div>
								<p class="text-sm text-slate-700 dark:text-slate-300 whitespace-pre-wrap">
									{expandedSections[responseId] || !isTruncated ? response.content : truncated}
								</p>
								{#if isTruncated}
									<button
										class="mt-2 text-xs text-blue-600 dark:text-blue-400 hover:underline"
										onclick={() => toggleSection(responseId)}
									>
										{expandedSections[responseId] ? 'Show less' : 'Show more'}
									</button>
								{/if}
							</div>
						{/each}
					</div>
				</div>
			{/if}

			<!-- Tool Calls Section -->
			<div class="mb-6">
				<h3 class="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-3 flex items-center gap-2">
					Tool Calls
					<span class="text-sm font-normal text-slate-600 dark:text-slate-400">
						({agent.toolCalls.length})
					</span>
				</h3>

				{#if agent.groupedToolCalls.length === 0}
					<p class="text-sm text-slate-500 dark:text-slate-500 italic">No tool calls</p>
				{:else}
					<div class="space-y-2">
						{#each agent.groupedToolCalls as group}
							<button
								class="w-full p-3 bg-slate-50 dark:bg-slate-800/40 rounded border border-slate-200 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-700/50 hover:border-slate-300 dark:hover:border-slate-600 transition-colors cursor-pointer text-left"
								onclick={() => onToolClick?.(group.instances[0])}
								title="Click to view tool details"
							>
								<div class="flex items-start justify-between gap-3 mb-2">
									<div class="flex-1">
										<div class="flex items-center gap-2 mb-1">
											<span class="{getToolStatusColor(group.status)} text-base">
												{getToolStatusIcon(group.status)}
											</span>
											<span class="font-mono text-sm px-2 py-0.5 rounded bg-slate-100 dark:bg-black/30 text-blue-600 dark:text-blue-400 font-medium">
												{group.toolName}
											</span>
											{#if group.count > 1}
												<span class="text-xs px-1.5 py-0.5 rounded bg-slate-200 dark:bg-slate-700 text-slate-600 dark:text-slate-400 font-semibold">
													{group.count} calls
												</span>
											{/if}
											<span class="text-xs text-slate-400 dark:text-slate-500 ml-auto">
												Click to view details →
											</span>
										</div>
										<p class="text-sm text-slate-700 dark:text-slate-300">
											{group.target}
										</p>
									</div>
									<div class="text-right">
										<div class="text-xs text-slate-600 dark:text-slate-400 font-mono">
											{formatTimestamp(group.latestTimestamp)}
										</div>
									</div>
								</div>
							</button>
						{/each}
					</div>
				{/if}
			</div>

			<!-- Todos Section -->
			<div class="mb-6">
				<h3 class="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-3 flex items-center gap-2">
					📋 Todo List
					<span class="text-sm font-normal text-slate-600 dark:text-slate-400">
						({agent.todos.reduce((sum, activity) => sum + activity.todos.length, 0)} total items, {agent.todos.length} updates)
					</span>
				</h3>

				{#if agent.todos.length === 0}
					<p class="text-sm text-slate-500 dark:text-slate-500 italic">No todo updates</p>
				{:else}
					<div class="space-y-4">
						{#each agent.todos as todoActivity (todoActivity.id)}
							<div class="p-4 bg-slate-50 dark:bg-slate-800/40 rounded border border-slate-200 dark:border-slate-700">
								<div class="flex items-center justify-between mb-3 pb-2 border-b border-slate-200 dark:border-slate-700">
									<span class="text-xs text-slate-600 dark:text-slate-400 font-mono">
										Updated: {formatTimestamp(todoActivity.timestamp)}
									</span>
									<span class="text-xs text-slate-500 dark:text-slate-500">
										{todoActivity.todos.length} item{todoActivity.todos.length !== 1 ? 's' : ''}
									</span>
								</div>
								<div class="space-y-2.5">
									{#each todoActivity.todos as todo, idx}
										<div class="flex items-start gap-2.5">
											<span class="{getTodoStatusColor(todo.status)} text-base leading-none mt-0.5" title="{todo.status}">
												{getTodoStatusIcon(todo.status)}
											</span>
											<div class="flex-1 min-w-0">
												<p class="text-sm text-slate-900 dark:text-slate-100 font-medium">
													{todo.content}
												</p>
												{#if todo.activeForm && todo.status === 'in_progress'}
													<p class="text-xs text-blue-600 dark:text-blue-400 mt-1 italic">
														→ {todo.activeForm}
													</p>
												{/if}
											</div>
										</div>
									{/each}
								</div>
							</div>
						{/each}
					</div>
				{/if}
			</div>

			<!-- Child Agents Summary -->
			{#if agent.children.length > 0}
				<div class="mb-6">
					<h3 class="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-3 flex items-center gap-2">
						Delegated Agents
						<span class="text-sm font-normal text-slate-600 dark:text-slate-400">
							({agent.children.length})
						</span>
					</h3>

					<div class="space-y-2">
						{#each agent.children as child (child.id)}
							<div class="p-3 bg-slate-50 dark:bg-slate-800/40 rounded border border-slate-200 dark:border-slate-700">
								<div class="flex items-center justify-between">
									<div class="flex items-center gap-2">
										<span class="text-base">
											{getAgentTypeIcon(child.name)}
										</span>
										<span class="font-semibold text-slate-900 dark:text-slate-100">
											{formatAgentName(child.name)}
										</span>
										<span class="text-sm text-slate-600 dark:text-slate-400">
											({child.toolCalls.length} tools, {child.todos.length} todos)
										</span>
									</div>
									<span class="text-sm text-slate-600 dark:text-slate-400 capitalize">
										{child.status}
									</span>
								</div>
							</div>
						{/each}
					</div>
				</div>
			{/if}
		</div>
	</div>
{/if}
