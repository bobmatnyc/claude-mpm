<script lang="ts">
	import { socketStore } from '$lib/stores/socket.svelte';
	import { themeStore } from '$lib/stores/theme.svelte';
	import { derived } from 'svelte/store';

	// Use store subscriptions with $ prefix (auto-subscription)
	const { isConnected, error, streams, streamMetadata, selectedStream } = socketStore;

	// Convert Set to Array for dropdown options and include metadata
	const streamOptions = derived(
		[streams, streamMetadata],
		([$streams, $metadata]) => {
			return Array.from($streams).map(streamId => {
				const meta = $metadata.get(streamId);
				const projectName = meta?.projectName || 'Unknown Project';
				// Format: "ProjectName (session-id)"
				const displayName = `${projectName} (${streamId})`;
				return {
					id: streamId,
					displayName: displayName,
					projectPath: meta?.projectPath || null
				};
			});
		}
	);
</script>

<header class="bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700 px-6 py-4 transition-colors">
	<div class="flex items-center justify-between">
		<div>
			<h1 class="text-2xl font-bold text-slate-900 dark:text-white">Claude MPM Monitor</h1>
			<p class="text-sm text-slate-700 dark:text-slate-300 mt-1">Real-time multi-agent orchestration dashboard</p>
		</div>

		<div class="flex items-center gap-3">
			<!-- Stream Filter Dropdown -->
			<div class="flex items-center gap-2">
				<label for="stream-filter" class="text-sm text-slate-700 dark:text-slate-300">Stream:</label>
				<select
					id="stream-filter"
					bind:value={$selectedStream}
					class="px-3 py-1.5 text-sm text-slate-900 dark:text-slate-100 bg-slate-100 dark:bg-slate-700 border border-slate-300 dark:border-slate-600 rounded hover:bg-slate-200 dark:hover:bg-slate-600 focus:outline-none focus:ring-2 focus:ring-cyan-500 transition-colors"
					title={$streamOptions.find(s => s.id === $selectedStream)?.projectPath || ''}
					disabled={$streamOptions.length === 0}
				>
					{#if $streamOptions.length === 0}
						<option value="" disabled>Waiting for streams...</option>
					{:else}
						<option value="">All Streams</option>
						{#each $streamOptions as stream}
							<option value={stream.id} title={stream.projectPath || stream.id}>
								{stream.displayName}
							</option>
						{/each}
					{/if}
				</select>
			</div>

			<!-- Theme Toggle Button -->
			<button
				onclick={() => themeStore.toggle()}
				class="p-2 bg-slate-100 dark:bg-slate-700 hover:bg-slate-200 dark:hover:bg-slate-600 rounded transition-colors focus:outline-none focus:ring-2 focus:ring-cyan-500"
				title={themeStore.current === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
			>
				{#if themeStore.current === 'dark'}
					<!-- Moon icon (dark mode active) -->
					<svg class="w-5 h-5 text-slate-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
					</svg>
				{:else}
					<!-- Sun icon (light mode active) -->
					<svg class="w-5 h-5 text-amber-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
					</svg>
				{/if}
			</button>

			<div class="flex items-center gap-2">
				<div
					class="w-3 h-3 rounded-full transition-colors"
					class:bg-green-500={$isConnected}
					class:bg-red-500={!$isConnected}
				></div>
				<span class="text-sm font-medium text-slate-900 dark:text-slate-100">
					{$isConnected ? 'Connected' : 'Disconnected'}
				</span>
			</div>

			{#if $error}
				<div class="text-xs text-red-600 dark:text-red-400 max-w-xs truncate" title={$error}>
					Error: {$error}
				</div>
			{/if}
		</div>
	</div>
</header>
