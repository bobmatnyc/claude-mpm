<script lang="ts">
	import { socketStore } from '$lib/stores/socket.svelte';
	import type { ClaudeEvent } from '$lib/types/events';

	let events = $derived(socketStore.events);

	function formatTimestamp(timestamp: string): string {
		return new Date(timestamp).toLocaleTimeString();
	}

	function getEventColor(type: ClaudeEvent['type']): string {
		switch (type) {
			case 'tool_call':
				return 'bg-blue-500/10 border-blue-500/30 text-blue-400';
			case 'tool_result':
				return 'bg-green-500/10 border-green-500/30 text-green-400';
			case 'message':
				return 'bg-purple-500/10 border-purple-500/30 text-purple-400';
			case 'error':
				return 'bg-red-500/10 border-red-500/30 text-red-400';
			default:
				return 'bg-slate-500/10 border-slate-500/30 text-slate-400';
		}
	}

	function clearEvents() {
		socketStore.clearEvents();
	}
</script>

<div class="flex flex-col h-full">
	<div class="flex items-center justify-between px-6 py-3 bg-slate-800 border-b border-slate-700">
		<h2 class="text-lg font-semibold text-white">Event Stream</h2>
		<div class="flex items-center gap-3">
			<span class="text-sm text-slate-400">{events.length} events</span>
			<button
				onclick={clearEvents}
				class="px-3 py-1 text-xs font-medium bg-slate-700 hover:bg-slate-600 rounded transition-colors"
			>
				Clear
			</button>
		</div>
	</div>

	<div class="flex-1 overflow-y-auto p-6 space-y-3">
		{#if events.length === 0}
			<div class="text-center py-12 text-slate-500">
				<p class="text-lg mb-2">No events yet</p>
				<p class="text-sm">Waiting for Claude activity...</p>
			</div>
		{:else}
			{#each events as event (event.id)}
				<div class="border rounded-lg p-4 {getEventColor(event.type)}">
					<div class="flex items-start justify-between mb-2">
						<div class="flex items-center gap-2">
							<span class="font-mono text-xs px-2 py-1 rounded bg-black/20">
								{event.type}
							</span>
							{#if event.agent}
								<span class="text-xs px-2 py-1 rounded bg-black/20">
									{event.agent}
								</span>
							{/if}
						</div>
						<span class="text-xs opacity-60">
							{formatTimestamp(event.timestamp)}
						</span>
					</div>

					<pre class="text-xs overflow-x-auto bg-black/20 rounded p-3 mt-2">
{JSON.stringify(event.data, null, 2)}
					</pre>
				</div>
			{/each}
		{/if}
	</div>
</div>
