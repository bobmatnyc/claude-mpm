<script lang="ts">
	import { socketStore } from '$lib/stores/socket.svelte';

	let { selectedStream = $bindable('all') }: { selectedStream: string } = $props();

	let { isConnected, error, streams } = $derived({
		isConnected: socketStore.isConnected,
		error: socketStore.error,
		streams: socketStore.streams
	});

	let streamOptions = $derived([...streams]);
</script>

<header class="bg-slate-800 border-b border-slate-700 px-6 py-4">
	<div class="flex items-center justify-between">
		<div>
			<h1 class="text-2xl font-bold text-white">Claude MPM Monitor</h1>
			<p class="text-sm text-slate-400 mt-1">Real-time multi-agent orchestration dashboard</p>
		</div>

		<div class="flex items-center gap-3">
			<!-- Stream Filter Dropdown -->
			<div class="flex items-center gap-2">
				<label for="stream-filter" class="text-sm text-slate-400">Stream:</label>
				<select
					id="stream-filter"
					bind:value={selectedStream}
					class="px-3 py-1.5 text-sm bg-slate-700 border border-slate-600 rounded hover:bg-slate-600 focus:outline-none focus:ring-2 focus:ring-cyan-500 transition-colors"
				>
					<option value="all">All Streams</option>
					{#each streamOptions as stream}
						<option value={stream}>{stream}</option>
					{/each}
				</select>
			</div>

			<div class="flex items-center gap-2">
				<div
					class="w-3 h-3 rounded-full transition-colors"
					class:bg-green-500={isConnected}
					class:bg-red-500={!isConnected}
				></div>
				<span class="text-sm font-medium">
					{isConnected ? 'Connected' : 'Disconnected'}
				</span>
			</div>

			{#if error}
				<div class="text-xs text-red-400 max-w-xs truncate" title={error}>
					Error: {error}
				</div>
			{/if}
		</div>
	</div>
</header>
