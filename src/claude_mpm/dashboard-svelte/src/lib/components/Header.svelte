<script lang="ts">
	import { socketStore } from '$lib/stores/socket.svelte';

	let { isConnected, error } = $derived({
		isConnected: socketStore.isConnected,
		error: socketStore.error
	});
</script>

<header class="bg-slate-800 border-b border-slate-700 px-6 py-4">
	<div class="flex items-center justify-between">
		<div>
			<h1 class="text-2xl font-bold text-white">Claude MPM Monitor</h1>
			<p class="text-sm text-slate-400 mt-1">Real-time multi-agent orchestration dashboard</p>
		</div>

		<div class="flex items-center gap-3">
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
