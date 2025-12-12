<script lang="ts">
	import type { ClaudeEvent, Tool } from '$lib/types/events';

	let {
		event,
		tool
	}: {
		event: ClaudeEvent | null;
		tool?: Tool | null;
	} = $props();

	const MAX_ITEMS = 50; // Max items to show per level
	const MAX_DEPTH = 5; // Max depth to render inline

	let expandedPaths = $state<Set<string>>(new Set());

	// Reset when event or tool changes and auto-expand "data" key
	$effect(() => {
		if (event || tool) {
			expandedPaths = new Set(['root', 'root.data', 'root.preToolEvent', 'root.postToolEvent']); // Expand root and data by default
		} else {
			expandedPaths = new Set();
		}
	});

	function toggleExpand(path: string) {
		const newSet = new Set(expandedPaths);
		if (newSet.has(path)) {
			newSet.delete(path);
		} else {
			newSet.add(path);
		}
		expandedPaths = newSet;
	}

	function getType(value: unknown): string {
		if (value === null) return 'null';
		if (Array.isArray(value)) return 'array';
		return typeof value;
	}

	function formatValue(value: unknown): string {
		if (value === null) return 'null';
		if (value === undefined) return 'undefined';
		if (typeof value === 'string') {
			return value.length > 80 ? `"${value.slice(0, 80)}..."` : `"${value}"`;
		}
		if (typeof value === 'boolean' || typeof value === 'number') return String(value);
		return '';
	}

	function getEntries(value: unknown): [string, unknown][] {
		if (Array.isArray(value)) {
			return value.slice(0, MAX_ITEMS).map((v, i) => [`[${i}]`, v]);
		}
		if (typeof value === 'object' && value !== null) {
			return Object.entries(value).slice(0, MAX_ITEMS);
		}
		return [];
	}

	function isExpandable(value: unknown): boolean {
		return typeof value === 'object' && value !== null;
	}

	function getValueColor(type: string): string {
		switch (type) {
			case 'string':
				return 'text-green-600 dark:text-green-400';
			case 'number':
				return 'text-blue-600 dark:text-blue-400';
			case 'boolean':
				return 'text-purple-600 dark:text-purple-400';
			case 'null':
				return 'text-slate-400 dark:text-slate-500';
			default:
				return 'text-slate-700 dark:text-slate-300';
		}
	}
</script>

{#snippet renderValue(value: unknown, path: string, depth: number)}
	{#if depth >= MAX_DEPTH}
		<div class="text-yellow-600 dark:text-yellow-400 text-xs">
			<span>... (max depth {MAX_DEPTH} reached)</span>
		</div>
	{:else}
		{@const type = getType(value)}
		{@const expandable = isExpandable(value)}
		{@const expanded = expandedPaths.has(path)}

		{#if expandable}
			<div class="mb-1">
				<button
					onclick={() => toggleExpand(path)}
					class="inline-flex items-center hover:bg-slate-100 dark:hover:bg-slate-800 rounded px-1 -ml-1 transition-colors"
				>
					<svg
						class="w-3 h-3 mr-1 transition-transform {expanded ? 'rotate-90' : ''} text-slate-600 dark:text-slate-400"
						fill="currentColor"
						viewBox="0 0 20 20"
					>
						<path
							fill-rule="evenodd"
							d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z"
							clip-rule="evenodd"
						/>
					</svg>
					<span class="text-slate-400 dark:text-slate-500">{type === 'array' ? '[...]' : '{...}'}</span>
				</button>

				{#if expanded}
					{@const entries = getEntries(value)}
					{#each entries as [key, childValue]}
						<div class="ml-4">
							<span class="text-cyan-600 dark:text-cyan-400">{key}:</span>
							{@render renderValue(childValue, `${path}.${key}`, depth + 1)}
						</div>
					{/each}
					{#if Array.isArray(value) && value.length > MAX_ITEMS}
						<div class="ml-4 text-slate-400 dark:text-slate-500 text-xs">
							... and {value.length - MAX_ITEMS} more items
						</div>
					{/if}
					{#if !Array.isArray(value) && typeof value === 'object' && value !== null && Object.keys(value).length > MAX_ITEMS}
						<div class="ml-4 text-slate-400 dark:text-slate-500 text-xs">
							... and {Object.keys(value).length - MAX_ITEMS} more properties
						</div>
					{/if}
				{/if}
			</div>
		{:else}
			<span class="{getValueColor(type)} ml-1">{formatValue(value)}</span>
		{/if}
	{/if}
{/snippet}

<div class="flex flex-col h-full bg-white dark:bg-slate-900 border-r border-slate-200 dark:border-slate-700 transition-colors">
	<div class="px-4 py-3 bg-slate-100 dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700 transition-colors">
		<h3 class="text-sm font-semibold text-slate-900 dark:text-white">JSON Data Explorer</h3>
	</div>

	<div class="flex-1 overflow-y-auto p-4">
		{#if !event && !tool}
			<div class="text-center py-12 text-slate-400 dark:text-slate-500">
				<svg
					class="w-12 h-12 mx-auto mb-3 opacity-50"
					fill="none"
					stroke="currentColor"
					viewBox="0 0 24 24"
				>
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="2"
						d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
					/>
				</svg>
				<p class="text-sm">Select an event or tool to view details</p>
			</div>
		{:else if tool}
			<!-- Tool view: Show pre-tool and post-tool events separately -->
			<div class="font-mono text-xs space-y-6">
				<!-- PRE-TOOL Section -->
				<div>
					<div class="text-sm font-bold text-slate-700 dark:text-slate-300 mb-3 pb-2 border-b border-slate-300 dark:border-slate-600">
						=== PRE-TOOL ===
					</div>
					{#each getEntries(tool.preToolEvent) as [key, value]}
						<div class="mb-1">
							<span class="text-cyan-600 dark:text-cyan-400">{key}:</span>
							{@render renderValue(value, `root.${key}`, 0)}
						</div>
					{/each}
				</div>

				<!-- POST-TOOL Section -->
				<div>
					<div class="text-sm font-bold text-slate-700 dark:text-slate-300 mb-3 pb-2 border-b border-slate-300 dark:border-slate-600">
						=== POST-TOOL ===
					</div>
					{#if tool.postToolEvent}
						{#each getEntries(tool.postToolEvent) as [key, value]}
							<div class="mb-1">
								<span class="text-cyan-600 dark:text-cyan-400">{key}:</span>
								{@render renderValue(value, `root.${key}`, 0)}
							</div>
						{/each}
					{:else}
						<div class="text-slate-400 dark:text-slate-500 italic">
							Waiting for result...
						</div>
					{/if}
				</div>
			</div>
		{:else if event}
			<div class="font-mono text-xs">
				{#each getEntries(event) as [key, value]}
					<div class="mb-1">
						<span class="text-cyan-600 dark:text-cyan-400">{key}:</span>
						{@render renderValue(value, `root.${key}`, 0)}
					</div>
				{/each}
			</div>
		{/if}
	</div>
</div>
