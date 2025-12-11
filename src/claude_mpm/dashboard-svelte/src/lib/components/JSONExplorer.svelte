<script lang="ts">
	import type { ClaudeEvent } from '$lib/types/events';

	let { event }: { event: ClaudeEvent | null } = $props();

	interface TreeNode {
		key: string;
		value: unknown;
		type: string;
		expanded: boolean;
		children?: TreeNode[];
	}

	function buildTree(obj: unknown, parentKey = ''): TreeNode[] {
		if (obj === null || obj === undefined) {
			return [];
		}

		if (Array.isArray(obj)) {
			return obj.map((item, index) => ({
				key: `[${index}]`,
				value: item,
				type: typeof item === 'object' && item !== null ? 'object' : typeof item,
				expanded: false,
				children: typeof item === 'object' && item !== null ? buildTree(item) : undefined
			}));
		}

		if (typeof obj === 'object') {
			return Object.entries(obj).map(([key, value]) => ({
				key,
				value,
				type: Array.isArray(value) ? 'array' : typeof value === 'object' && value !== null ? 'object' : typeof value,
				expanded: false,
				children: typeof value === 'object' && value !== null ? buildTree(value) : undefined
			}));
		}

		return [];
	}

	let tree = $state<TreeNode[]>([]);
	let expandedPaths = $state<Set<string>>(new Set());

	$effect(() => {
		if (event) {
			tree = buildTree(event);
			// Auto-expand root level
			expandedPaths = new Set(tree.map((_, i) => `${i}`));
		} else {
			tree = [];
			expandedPaths = new Set();
		}
	});

	function toggleExpand(path: string) {
		if (expandedPaths.has(path)) {
			expandedPaths.delete(path);
		} else {
			expandedPaths.add(path);
		}
		expandedPaths = new Set(expandedPaths);
	}

	function isExpanded(path: string): boolean {
		return expandedPaths.has(path);
	}

	function formatValue(value: unknown, type: string): string {
		if (value === null) return 'null';
		if (value === undefined) return 'undefined';
		if (type === 'string') return `"${value}"`;
		if (type === 'boolean' || type === 'number') return String(value);
		return '';
	}

	function getValueColor(type: string): string {
		switch (type) {
			case 'string':
				return 'text-green-400';
			case 'number':
				return 'text-blue-400';
			case 'boolean':
				return 'text-purple-400';
			case 'null':
				return 'text-slate-500';
			default:
				return 'text-slate-300';
		}
	}

	function renderNode(node: TreeNode, path: string, depth: number): void {}
</script>

<div class="flex flex-col h-full bg-slate-900 border-r border-slate-700">
	<div class="px-4 py-3 bg-slate-800 border-b border-slate-700">
		<h3 class="text-sm font-semibold text-white">JSON Data Explorer</h3>
	</div>

	<div class="flex-1 overflow-y-auto p-4">
		{#if !event}
			<div class="text-center py-12 text-slate-500">
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
				<p class="text-sm">Select an event to view details</p>
			</div>
		{:else}
			<div class="font-mono text-xs">
				{#each tree as node, index}
					{@const path = `${index}`}
					<div class="mb-1">
						{#if node.children && node.children.length > 0}
							<button
								onclick={() => toggleExpand(path)}
								class="inline-flex items-center hover:bg-slate-800 rounded px-1 -ml-1"
							>
								<svg
									class="w-3 h-3 mr-1 transition-transform {isExpanded(path)
										? 'rotate-90'
										: ''}"
									fill="currentColor"
									viewBox="0 0 20 20"
								>
									<path
										fill-rule="evenodd"
										d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z"
										clip-rule="evenodd"
									/>
								</svg>
								<span class="text-cyan-400">{node.key}</span>
								<span class="text-slate-500 ml-1"
									>{node.type === 'array' ? '[]' : '{}'}</span
								>
							</button>

							{#if isExpanded(path)}
								{#each node.children as child, childIndex}
									{@const childPath = `${path}.${childIndex}`}
									<div class="ml-4 mb-1">
										{#if child.children && child.children.length > 0}
											<button
												onclick={() => toggleExpand(childPath)}
												class="inline-flex items-center hover:bg-slate-800 rounded px-1 -ml-1"
											>
												<svg
													class="w-3 h-3 mr-1 transition-transform {isExpanded(
														childPath
													)
														? 'rotate-90'
														: ''}"
													fill="currentColor"
													viewBox="0 0 20 20"
												>
													<path
														fill-rule="evenodd"
														d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z"
														clip-rule="evenodd"
													/>
												</svg>
												<span class="text-cyan-400">{child.key}</span>
												<span class="text-slate-500 ml-1"
													>{child.type === 'array' ? '[]' : '{}'}</span
												>
											</button>

											{#if isExpanded(childPath) && child.children}
												{#each child.children as grandchild}
													<div class="ml-4">
														<span class="text-cyan-400">{grandchild.key}:</span>
														<span class="{getValueColor(grandchild.type)} ml-1"
															>{formatValue(grandchild.value, grandchild.type)}</span
														>
													</div>
												{/each}
											{/if}
										{:else}
											<span class="text-cyan-400">{child.key}:</span>
											<span class="{getValueColor(child.type)} ml-1"
												>{formatValue(child.value, child.type)}</span
											>
										{/if}
									</div>
								{/each}
							{/if}
						{:else}
							<span class="text-cyan-400">{node.key}:</span>
							<span class="{getValueColor(node.type)} ml-1"
								>{formatValue(node.value, node.type)}</span
							>
						{/if}
					</div>
				{/each}
			</div>
		{/if}
	</div>
</div>
