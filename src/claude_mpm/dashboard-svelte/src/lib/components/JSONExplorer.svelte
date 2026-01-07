<script lang="ts">
	import type { ClaudeEvent, Tool } from '$lib/types/events';
	import CopyButton from './CopyButton.svelte';

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

	// Helper function to format timestamp
	function formatTimestamp(timestamp: string | number): string {
		const date = typeof timestamp === 'string' ? new Date(timestamp) : new Date(timestamp);
		return date.toLocaleString();
	}

	// Helper function to safely get nested property
	function getNestedValue(obj: any, path: string, defaultValue: string = 'N/A'): string {
		const value = path.split('.').reduce((acc, part) => acc?.[part], obj);
		if (value === null || value === undefined) return defaultValue;
		if (typeof value === 'boolean') return value ? 'Yes' : 'No';
		return String(value);
	}

	// Extract pre-tool data for table display
	function extractPreToolData(tool: Tool) {
		const preData = tool.preToolEvent?.data as Record<string, any> || {};
		const toolParams = preData.tool_parameters || {};
		const paramKeys = preData.param_keys || [];

		return {
			toolName: tool.toolName,
			operationType: preData.operation_type || 'N/A',
			sessionId: tool.preToolEvent?.session_id || preData.session_id || 'N/A',
			workingDirectory: preData.working_directory || preData.cwd || 'N/A',
			gitBranch: preData.git_branch || 'N/A',
			timestamp: tool.preToolEvent?.timestamp ? formatTimestamp(tool.preToolEvent.timestamp) : 'N/A',
			parameterCount: Object.keys(toolParams).length,
			securityRisk: preData.security_risk || 'None',
			correlationId: tool.id,
			toolParameters: toolParams,
			paramKeys: Array.isArray(paramKeys) ? paramKeys : []
		};
	}

	// Extract post-tool data for table display
	function extractPostToolData(tool: Tool) {
		if (!tool.postToolEvent) return null;
		const postData = tool.postToolEvent?.data as Record<string, any> || {};

		return {
			exitCode: postData.exit_code ?? 'N/A',
			success: postData.success !== undefined ? (postData.success ? 'Yes' : 'No') : 'N/A',
			status: postData.status || tool.status || 'N/A',
			duration: tool.duration !== null ? `${tool.duration}ms` : 'N/A',
			hasOutput: postData.output || postData.result ? 'Yes' : 'No',
			hasError: postData.error || postData.is_error ? 'Yes' : 'No',
			outputSize: postData.output ? String(postData.output).length + ' chars' : 'N/A',
			correlationId: tool.id,
			output: postData.output || postData.result || null,
			error: postData.error || null
		};
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
		<h3 class="text-sm font-semibold text-slate-900 dark:text-white">
			{tool ? 'Tool Details' : 'JSON Data Explorer'}
		</h3>
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
			<!-- Tool view: Show pre-tool and post-tool as tables -->
			{@const preData = extractPreToolData(tool)}
			{@const postData = extractPostToolData(tool)}

			<div class="space-y-6">
				<!-- PRE-TOOL Section -->
				<div>
					<h4 class="text-sm font-bold text-slate-700 dark:text-slate-300 mb-3 pb-2 border-b border-slate-300 dark:border-slate-600">
						Tool Invocation
					</h4>
					<table class="w-full text-sm">
						<tbody class="divide-y divide-slate-200 dark:divide-slate-700">
							<tr class="hover:bg-slate-50 dark:hover:bg-slate-800">
								<td class="py-2 px-3 font-semibold text-slate-600 dark:text-slate-400 w-1/3">Tool Name</td>
								<td class="py-2 px-3 text-slate-900 dark:text-slate-100">{preData.toolName}</td>
							</tr>
							<tr class="hover:bg-slate-50 dark:hover:bg-slate-800">
								<td class="py-2 px-3 font-semibold text-slate-600 dark:text-slate-400">Operation Type</td>
								<td class="py-2 px-3 text-slate-900 dark:text-slate-100">{preData.operationType}</td>
							</tr>
							<tr class="hover:bg-slate-50 dark:hover:bg-slate-800">
								<td class="py-2 px-3 font-semibold text-slate-600 dark:text-slate-400">Session ID</td>
								<td class="py-2 px-3">
									<div class="flex items-center gap-2">
										<span class="text-slate-900 dark:text-slate-100 font-mono text-xs">{preData.sessionId}</span>
										<CopyButton text={preData.sessionId} size="sm" />
									</div>
								</td>
							</tr>
							<tr class="hover:bg-slate-50 dark:hover:bg-slate-800">
								<td class="py-2 px-3 font-semibold text-slate-600 dark:text-slate-400">Working Directory</td>
								<td class="py-2 px-3">
									<div class="flex items-center gap-2">
										<span class="text-slate-900 dark:text-slate-100 font-mono text-xs break-all">{preData.workingDirectory}</span>
										{#if preData.workingDirectory !== 'N/A'}
											<CopyButton text={preData.workingDirectory} size="sm" />
										{/if}
									</div>
								</td>
							</tr>
							<tr class="hover:bg-slate-50 dark:hover:bg-slate-800">
								<td class="py-2 px-3 font-semibold text-slate-600 dark:text-slate-400">Git Branch</td>
								<td class="py-2 px-3 text-slate-900 dark:text-slate-100">{preData.gitBranch}</td>
							</tr>
							<tr class="hover:bg-slate-50 dark:hover:bg-slate-800">
								<td class="py-2 px-3 font-semibold text-slate-600 dark:text-slate-400">Timestamp</td>
								<td class="py-2 px-3 text-slate-900 dark:text-slate-100">{preData.timestamp}</td>
							</tr>
							<tr class="hover:bg-slate-50 dark:hover:bg-slate-800">
								<td class="py-2 px-3 font-semibold text-slate-600 dark:text-slate-400">Parameter Count</td>
								<td class="py-2 px-3 text-slate-900 dark:text-slate-100">{preData.parameterCount}</td>
							</tr>
							<tr class="hover:bg-slate-50 dark:hover:bg-slate-800">
								<td class="py-2 px-3 font-semibold text-slate-600 dark:text-slate-400">Security Risk</td>
								<td class="py-2 px-3 text-slate-900 dark:text-slate-100">{preData.securityRisk}</td>
							</tr>
							<tr class="hover:bg-slate-50 dark:hover:bg-slate-800">
								<td class="py-2 px-3 font-semibold text-slate-600 dark:text-slate-400">Correlation ID</td>
								<td class="py-2 px-3">
									<div class="flex items-center gap-2">
										<span class="text-slate-900 dark:text-slate-100 font-mono text-xs break-all">{preData.correlationId}</span>
										<CopyButton text={preData.correlationId} size="sm" />
									</div>
								</td>
							</tr>
						</tbody>
					</table>

					<!-- Tool Parameters -->
					{#if Object.keys(preData.toolParameters).length > 0}
						<div class="mt-4">
							<h5 class="text-sm font-semibold text-slate-600 dark:text-slate-400 mb-2">Tool Parameters</h5>
							<table class="w-full text-sm bg-slate-50 dark:bg-slate-800/50 rounded">
								<tbody class="divide-y divide-slate-200 dark:divide-slate-700">
									{#each Object.entries(preData.toolParameters) as [key, value]}
										<tr class="hover:bg-slate-100 dark:hover:bg-slate-700">
											<td class="py-2 px-3 font-mono text-xs text-cyan-600 dark:text-cyan-400 w-1/3">{key}</td>
											<td class="py-2 px-3">
												<div class="flex items-center gap-2">
													<span class="text-slate-900 dark:text-slate-100 font-mono text-xs break-all flex-1">
														{typeof value === 'object' ? JSON.stringify(value, null, 2) : String(value)}
													</span>
													<CopyButton text={typeof value === 'object' ? JSON.stringify(value, null, 2) : String(value)} size="sm" />
												</div>
											</td>
										</tr>
									{/each}
								</tbody>
							</table>
						</div>
					{/if}

					<!-- Parameter Keys -->
					{#if preData.paramKeys.length > 0}
						<div class="mt-4">
							<h5 class="text-sm font-semibold text-slate-600 dark:text-slate-400 mb-2">Parameter Keys</h5>
							<div class="bg-slate-50 dark:bg-slate-800/50 rounded p-3">
								<span class="text-slate-900 dark:text-slate-100 font-mono text-xs">
									{preData.paramKeys.join(', ')}
								</span>
							</div>
						</div>
					{/if}
				</div>

				<!-- POST-TOOL Section -->
				<div>
					<h4 class="text-sm font-bold text-slate-700 dark:text-slate-300 mb-3 pb-2 border-b border-slate-300 dark:border-slate-600">
						Tool Result
					</h4>
					{#if postData}
						<table class="w-full text-sm">
							<tbody class="divide-y divide-slate-200 dark:divide-slate-700">
								<tr class="hover:bg-slate-50 dark:hover:bg-slate-800">
									<td class="py-2 px-3 font-semibold text-slate-600 dark:text-slate-400 w-1/3">Exit Code</td>
									<td class="py-2 px-3 text-slate-900 dark:text-slate-100">{postData.exitCode}</td>
								</tr>
								<tr class="hover:bg-slate-50 dark:hover:bg-slate-800">
									<td class="py-2 px-3 font-semibold text-slate-600 dark:text-slate-400">Success</td>
									<td class="py-2 px-3">
										<span class="px-2 py-1 rounded text-xs font-semibold {postData.success === 'Yes' ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' : postData.success === 'No' ? 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200' : 'bg-slate-100 text-slate-800 dark:bg-slate-700 dark:text-slate-300'}">
											{postData.success}
										</span>
									</td>
								</tr>
								<tr class="hover:bg-slate-50 dark:hover:bg-slate-800">
									<td class="py-2 px-3 font-semibold text-slate-600 dark:text-slate-400">Status</td>
									<td class="py-2 px-3 text-slate-900 dark:text-slate-100">{postData.status}</td>
								</tr>
								<tr class="hover:bg-slate-50 dark:hover:bg-slate-800">
									<td class="py-2 px-3 font-semibold text-slate-600 dark:text-slate-400">Duration</td>
									<td class="py-2 px-3 text-slate-900 dark:text-slate-100">{postData.duration}</td>
								</tr>
								<tr class="hover:bg-slate-50 dark:hover:bg-slate-800">
									<td class="py-2 px-3 font-semibold text-slate-600 dark:text-slate-400">Has Output</td>
									<td class="py-2 px-3 text-slate-900 dark:text-slate-100">{postData.hasOutput}</td>
								</tr>
								<tr class="hover:bg-slate-50 dark:hover:bg-slate-800">
									<td class="py-2 px-3 font-semibold text-slate-600 dark:text-slate-400">Has Error</td>
									<td class="py-2 px-3 text-slate-900 dark:text-slate-100">{postData.hasError}</td>
								</tr>
								<tr class="hover:bg-slate-50 dark:hover:bg-slate-800">
									<td class="py-2 px-3 font-semibold text-slate-600 dark:text-slate-400">Output Size</td>
									<td class="py-2 px-3 text-slate-900 dark:text-slate-100">{postData.outputSize}</td>
								</tr>
								<tr class="hover:bg-slate-50 dark:hover:bg-slate-800">
									<td class="py-2 px-3 font-semibold text-slate-600 dark:text-slate-400">Correlation ID</td>
									<td class="py-2 px-3 text-slate-900 dark:text-slate-100 font-mono text-xs break-all">{postData.correlationId}</td>
								</tr>
							</tbody>
						</table>

						<!-- Output -->
						{#if postData.output}
							<div class="mt-4">
								<div class="flex items-center justify-between mb-2">
									<h5 class="text-sm font-semibold text-slate-600 dark:text-slate-400">Output</h5>
									<CopyButton text={String(postData.output)} label="Copy" size="sm" />
								</div>
								<pre class="bg-slate-50 dark:bg-slate-800/50 rounded p-3 text-xs font-mono overflow-x-auto text-slate-900 dark:text-slate-100">{String(postData.output)}</pre>
							</div>
						{/if}

						<!-- Error -->
						{#if postData.error}
							<div class="mt-4">
								<div class="flex items-center justify-between mb-2">
									<h5 class="text-sm font-semibold text-red-600 dark:text-red-400">Error</h5>
									<CopyButton text={String(postData.error)} label="Copy" size="sm" />
								</div>
								<pre class="bg-red-50 dark:bg-red-900/20 rounded p-3 text-xs font-mono overflow-x-auto text-red-900 dark:text-red-100">{String(postData.error)}</pre>
							</div>
						{/if}
					{:else}
						<div class="text-slate-400 dark:text-slate-500 italic py-4 text-center">
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
