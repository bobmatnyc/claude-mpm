<script lang="ts">
	import type { Tool } from '$lib/types/events';

	let {
		tools,
		selectedTool = $bindable(null),
		selectedStream = ''
	}: {
		tools: Tool[];
		selectedTool: Tool | null;
		selectedStream: string;
	} = $props();

	// Debug: Log what we receive
	$effect(() => {
		console.log('[ToolsView] Props received:', {
			toolsLength: tools.length,
			selectedStream,
			firstTool: tools[0] ? { id: tools[0].id, name: tools[0].toolName } : null
		});
	});

	// Filter tools by selected stream
	let filteredTools = $derived.by(() => {
		const result = selectedStream === ''
			? tools
			: tools.filter(tool => {
				const preEvent = tool.preToolEvent;
				const preEventData = preEvent.data as Record<string, unknown> | null;
				const preEventStreamId =
					preEvent.session_id ||
					preEvent.sessionId ||
					(preEventData?.session_id as string) ||
					preEvent.source;
				return preEventStreamId === selectedStream;
			});
		console.log('[ToolsView] Filtered tools:', {
			inputLength: tools.length,
			outputLength: result.length,
			selectedStream
		});
		return result;
	});

	let toolListContainer = $state<HTMLDivElement | null>(null);
	let isInitialLoad = $state(true);

	// Helper to check if user is scrolled near bottom
	function isNearBottom(container: HTMLDivElement, threshold = 100): boolean {
		const { scrollTop, scrollHeight, clientHeight } = container;
		return scrollHeight - scrollTop - clientHeight < threshold;
	}

	// Auto-scroll logic: always on initial load, otherwise only if near bottom
	$effect(() => {
		if (displayedTools.length > 0 && toolListContainer) {
			const shouldScroll = isInitialLoad || isNearBottom(toolListContainer);

			if (shouldScroll) {
				setTimeout(() => {
					if (toolListContainer) {
						toolListContainer.scrollTop = toolListContainer.scrollHeight;
						isInitialLoad = false; // Clear initial load flag after first scroll
					}
				}, 0);
			}
		}
	});

	// Reset to initial load when stream filter changes (scroll to bottom)
	$effect(() => {
		// Track selectedStream changes
		selectedStream;
		isInitialLoad = true;
	});

	// Tool type filter state
	let toolTypeFilter = $state<string>('');

	// Apply tool type filter on top of stream filter
	let displayedTools = $derived(
		toolTypeFilter
			? filteredTools.filter(t => t.toolName === toolTypeFilter)
			: filteredTools
	);

	// Extract unique tool names from filtered tools for filter dropdown
	let uniqueToolNames = $derived(
		Array.from(new Set(filteredTools.map(t => t.toolName))).sort()
	);

	function selectTool(tool: Tool) {
		selectedTool = tool;
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

	function getStatusIcon(status: Tool['status']): string {
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

	function getStatusColor(status: Tool['status']): string {
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

	// Keyboard navigation
	function handleKeydown(e: KeyboardEvent) {
		if (displayedTools.length === 0) return;

		const currentIndex = selectedTool
			? displayedTools.findIndex(tool => tool.id === selectedTool?.id)
			: -1;

		let newIndex = currentIndex;

		if (e.key === 'ArrowDown') {
			e.preventDefault();
			newIndex = currentIndex < displayedTools.length - 1 ? currentIndex + 1 : currentIndex;
		} else if (e.key === 'ArrowUp') {
			e.preventDefault();
			newIndex = currentIndex > 0 ? currentIndex - 1 : 0;
		} else {
			return;
		}

		if (newIndex !== currentIndex && newIndex >= 0 && newIndex < displayedTools.length) {
			selectedTool = displayedTools[newIndex];
			// Scroll into view
			const toolElement = toolListContainer?.querySelector(
				`[data-tool-id="${selectedTool.id}"]`
			);
			if (toolElement) {
				toolElement.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
			}
		}
	}

	function formatTimestamp(timestamp: string | number): string {
		const date = typeof timestamp === 'string' ? new Date(timestamp) : new Date(timestamp);
		return date.toLocaleTimeString();
	}
</script>

<div class="flex flex-col h-full bg-white dark:bg-slate-900">
	<!-- Header with filters -->
	<div class="flex items-center justify-between px-6 py-3 bg-slate-100 dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700 transition-colors">
		<div class="flex items-center gap-3">
			<select
				bind:value={toolTypeFilter}
				class="px-3 py-1 text-xs font-medium bg-white dark:bg-slate-700 hover:bg-slate-50 dark:hover:bg-slate-600 rounded transition-colors border border-slate-300 dark:border-slate-600 text-slate-900 dark:text-slate-200"
			>
				<option value="">All Tools</option>
				{#each uniqueToolNames as toolName}
					<option value={toolName}>{toolName}</option>
				{/each}
			</select>
		</div>
		<span class="text-sm text-slate-700 dark:text-slate-300">{displayedTools.length} tools</span>
	</div>

	<div class="flex-1 overflow-y-auto">
		{#if displayedTools.length === 0}
			<div class="text-center py-12 text-slate-600 dark:text-slate-400">
				<svg class="w-16 h-16 mx-auto mb-3 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.828 14.828a4 4 0 01-5.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
				</svg>
				<p class="text-lg mb-2 font-medium">No tool executions yet</p>
				<p class="text-sm text-slate-500 dark:text-slate-500">Waiting for Claude to use tools...</p>
			</div>
		{:else}
			<!-- Table header -->
			<div class="grid grid-cols-[140px_1fr_80px_100px] gap-3 px-4 py-2 bg-slate-50 dark:bg-slate-900 border-b border-slate-200 dark:border-slate-700 text-xs font-semibold text-slate-700 dark:text-slate-300 sticky top-0 transition-colors">
				<div>Tool Name</div>
				<div>Operation</div>
				<div class="text-center">Status</div>
				<div class="text-right">Duration</div>
			</div>

			<!-- Tool rows - scrollable container -->
			<div
				bind:this={toolListContainer}
				onkeydown={handleKeydown}
				tabindex="0"
				role="list"
				aria-label="Tool list - use arrow keys to navigate"
				class="focus:outline-none overflow-y-auto max-h-[calc(100vh-280px)]"
			>
				{#each displayedTools as tool, i (tool.id)}
					<button
						data-tool-id={tool.id}
						onclick={() => selectTool(tool)}
						class="w-full text-left px-4 py-2.5 transition-colors border-l-4 grid grid-cols-[140px_1fr_80px_100px] gap-3 items-center text-xs
							{selectedTool?.id === tool.id
								? 'bg-cyan-50 dark:bg-cyan-500/20 border-l-cyan-500 dark:border-l-cyan-400 ring-1 ring-cyan-300 dark:ring-cyan-500/30'
								: `border-l-transparent ${i % 2 === 0 ? 'bg-slate-50 dark:bg-slate-800/40' : 'bg-white dark:bg-slate-800/20'} hover:bg-slate-100 dark:hover:bg-slate-700/30`}"
					>
						<!-- Tool Name -->
						<div>
							<span class="font-mono px-2 py-0.5 rounded-md bg-slate-100 dark:bg-black/30 text-blue-600 dark:text-blue-400 font-medium text-[11px]">
								{tool.toolName}
							</span>
						</div>

						<!-- Operation -->
						<div class="text-slate-700 dark:text-slate-300 truncate">
							{tool.operation}
						</div>

						<!-- Status -->
						<div class="text-center">
							<span class="{getStatusColor(tool.status)} text-base">
								{getStatusIcon(tool.status)}
							</span>
						</div>

						<!-- Duration -->
						<div class="text-slate-700 dark:text-slate-300 font-mono text-[11px] text-right">
							{formatDuration(tool.duration)}
						</div>
					</button>
				{/each}
			</div>
		{/if}
	</div>
</div>
