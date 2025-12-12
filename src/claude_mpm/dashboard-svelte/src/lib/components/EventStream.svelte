<script lang="ts">
	import { socketStore } from '$lib/stores/socket.svelte';
	import type { ClaudeEvent } from '$lib/types/events';

	let {
		selectedEvent = $bindable(null),
		selectedStream = 'all'
	}: {
		selectedEvent: ClaudeEvent | null;
		selectedStream: string;
	} = $props();

	// Get store reference
	const { events: allEventsStore } = socketStore;

	// Maintain local state from store subscription using $effect
	let allEvents = $state<ClaudeEvent[]>([]);

	// Subscribe to store changes and update local state
	$effect(() => {
		const unsubscribe = allEventsStore.subscribe(value => {
			allEvents = value;
		});
		return unsubscribe;
	});

	// Filter events based on selected stream using $derived
	let events = $derived(
		selectedStream === 'all'
			? allEvents
			: allEvents.filter(event =>
				event.sessionId === selectedStream ||
				event.session_id === selectedStream ||
				event.source === selectedStream
			)
	);

	function formatTimestamp(timestamp: string): string {
		return new Date(timestamp).toLocaleTimeString();
	}

	function getEventTypeColor(type: ClaudeEvent['type']): string {
		switch (type) {
			case 'tool_call':
				return 'text-blue-400';
			case 'tool_result':
				return 'text-green-400';
			case 'message':
				return 'text-purple-400';
			case 'error':
				return 'text-red-400';
			default:
				return 'text-slate-400';
		}
	}

	function getEventBgColor(type: ClaudeEvent['type']): string {
		switch (type) {
			case 'tool_call':
				return 'bg-blue-500/5 hover:bg-blue-500/10 border-blue-500/20';
			case 'tool_result':
				return 'bg-green-500/5 hover:bg-green-500/10 border-green-500/20';
			case 'message':
				return 'bg-purple-500/5 hover:bg-purple-500/10 border-purple-500/20';
			case 'error':
				return 'bg-red-500/5 hover:bg-red-500/10 border-red-500/20';
			default:
				return 'bg-slate-500/5 hover:bg-slate-500/10 border-slate-500/20';
		}
	}

	function clearEvents() {
		socketStore.clearEvents();
		selectedEvent = null;
	}

	function selectEvent(event: ClaudeEvent) {
		selectedEvent = event;
	}

	function getEventSummary(event: ClaudeEvent): string {
		if (event.type === 'tool_call' && typeof event.data === 'object' && event.data !== null) {
			const data = event.data as Record<string, unknown>;
			return `${data.tool_name || 'Unknown tool'}`;
		}
		if (event.type === 'message' && typeof event.data === 'object' && event.data !== null) {
			const data = event.data as Record<string, unknown>;
			return String(data.content || 'Message').slice(0, 60);
		}
		if (event.type === 'error' && typeof event.data === 'object' && event.data !== null) {
			const data = event.data as Record<string, unknown>;
			return String(data.message || 'Error').slice(0, 60);
		}
		return event.type;
	}

	// Get event source (session_id or source field)
	function getEventSource(event: ClaudeEvent): string {
		return event.sessionId || event.session_id || event.source || '-';
	}

	// Get calling entity (agent name or '-')
	function getCallingEntity(event: ClaudeEvent): string {
		return event.agent || '-';
	}

	// Get activity (tool name, message preview, etc.)
	function getActivity(event: ClaudeEvent): string {
		if (event.type === 'tool_call' && typeof event.data === 'object' && event.data !== null) {
			const data = event.data as Record<string, unknown>;
			return `${data.tool_name || 'Unknown tool'}`;
		}
		if (event.type === 'tool_result' && typeof event.data === 'object' && event.data !== null) {
			const data = event.data as Record<string, unknown>;
			const toolName = data.tool_name || 'Unknown tool';
			return `${toolName} result`;
		}
		if (event.type === 'message' && typeof event.data === 'object' && event.data !== null) {
			const data = event.data as Record<string, unknown>;
			const content = String(data.content || 'Message');
			return content.length > 50 ? content.slice(0, 50) + '...' : content;
		}
		if (event.type === 'error' && typeof event.data === 'object' && event.data !== null) {
			const data = event.data as Record<string, unknown>;
			const message = String(data.message || 'Error');
			return message.length > 50 ? message.slice(0, 50) + '...' : message;
		}
		if (event.subtype) {
			return event.subtype;
		}
		return event.type;
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

	<div class="flex-1 overflow-y-auto">
		{#if events.length === 0}
			<div class="text-center py-12 text-slate-500">
				<svg class="w-16 h-16 mx-auto mb-3 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
				</svg>
				<p class="text-lg mb-2">No events yet</p>
				<p class="text-sm">Waiting for Claude activity...</p>
			</div>
		{:else}
			<div class="divide-y divide-slate-700/50">
				{#each events as event (event.id)}
					<button
						onclick={() => selectEvent(event)}
						class="w-full text-left px-4 py-3 transition-colors border-l-2
							{selectedEvent?.id === event.id
								? 'bg-slate-700/30 border-l-cyan-500'
								: 'border-l-transparent ' + getEventBgColor(event.type)}"
					>
						<!-- Compact grid layout for 5 fields -->
						<div class="grid grid-cols-[auto_1fr_auto] gap-x-3 gap-y-1.5 text-xs">
							<!-- Row 1: Source, Type, Timestamp -->
							<div class="text-slate-500">Source:</div>
							<div class="text-slate-300 truncate font-mono text-[11px]">{getEventSource(event)}</div>
							<div class="text-slate-500 row-span-3 self-start text-right flex-shrink-0">
								{formatTimestamp(event.timestamp)}
							</div>

							<!-- Row 2: Type -->
							<div class="text-slate-500">Type:</div>
							<div class="flex items-center gap-2">
								<span class="font-mono px-2 py-0.5 rounded-md bg-black/30 {getEventTypeColor(event.type)} font-medium">
									{event.type}
								</span>
							</div>

							<!-- Row 3: Agent -->
							<div class="text-slate-500">Agent:</div>
							<div class="text-slate-300 truncate">{getCallingEntity(event)}</div>
						</div>

						<!-- Row 4: Activity (full width) -->
						<div class="mt-1.5 text-xs">
							<span class="text-slate-500">Activity:</span>
							<span class="text-slate-300 ml-2">{getActivity(event)}</span>
						</div>
					</button>
				{/each}
			</div>
		{/if}
	</div>
</div>
