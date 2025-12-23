<script lang="ts">
	import { socketStore } from '$lib/stores/socket.svelte';
	import type { ClaudeEvent } from '$lib/types/events';

	let {
		selectedEvent = $bindable(null),
		selectedStream = ''
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

	// Auto-scroll to bottom (newest events) when events change
	let eventListContainer = $state<HTMLDivElement | null>(null);
	let isInitialLoad = $state(true);

	// Helper to check if user is scrolled near bottom
	function isNearBottom(container: HTMLDivElement, threshold = 100): boolean {
		const { scrollTop, scrollHeight, clientHeight } = container;
		return scrollHeight - scrollTop - clientHeight < threshold;
	}

	// Auto-scroll logic: always on initial load, otherwise only if near bottom
	$effect(() => {
		if (events.length > 0 && eventListContainer) {
			const shouldScroll = isInitialLoad || isNearBottom(eventListContainer);

			if (shouldScroll) {
				// Use setTimeout to ensure DOM has updated
				setTimeout(() => {
					if (eventListContainer) {
						eventListContainer.scrollTop = eventListContainer.scrollHeight;
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

	// Activity filter state
	let activityFilter = $state<string>('');

	// Filter events based on selected stream using $derived
	// Empty string means show all events (before first stream is detected)
	// Check multiple field locations for session ID (matches socket store extraction logic)
	let streamFilteredEvents = $derived(
		selectedStream === ''
			? allEvents
			: allEvents.filter(event => {
				// Extract session ID using same logic as socket store (lines 101-106)
				// Safe property access with type guards
				const data = event.data;
				const dataSessionId =
					data && typeof data === 'object' && !Array.isArray(data)
						? (data as Record<string, unknown>).session_id ||
						  (data as Record<string, unknown>).sessionId
						: null;

				const eventStreamId =
					event.session_id ||
					event.sessionId ||
					dataSessionId ||
					event.source;
				return eventStreamId === selectedStream;
			})
	);

	// Apply activity filter on top of stream filter
	let events = $derived(
		activityFilter
			? streamFilteredEvents.filter(e => e.subtype === activityFilter)
			: streamFilteredEvents
	);

	// Extract unique activities (subtypes) from all events for filter dropdown
	let uniqueActivities = $derived(
		Array.from(new Set(streamFilteredEvents.map(e => e.subtype).filter(Boolean))).sort()
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

	// Keyboard navigation
	function handleKeydown(e: KeyboardEvent) {
		if (events.length === 0) return;

		const currentIndex = selectedEvent
			? events.findIndex(evt => evt.id === selectedEvent?.id)
			: -1;

		let newIndex = currentIndex;

		if (e.key === 'ArrowDown') {
			e.preventDefault();
			newIndex = currentIndex < events.length - 1 ? currentIndex + 1 : currentIndex;
		} else if (e.key === 'ArrowUp') {
			e.preventDefault();
			newIndex = currentIndex > 0 ? currentIndex - 1 : 0;
		} else {
			return;
		}

		if (newIndex !== currentIndex && newIndex >= 0 && newIndex < events.length) {
			selectedEvent = events[newIndex];
			// Scroll into view
			const eventElement = eventListContainer?.querySelector(
				`[data-event-id="${selectedEvent.id}"]`
			);
			if (eventElement) {
				eventElement.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
			}
		}
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
		return event.source || event.sessionId || event.session_id || '-';
	}

	// Get activity (subtype field)
	function getActivity(event: ClaudeEvent): string {
		return event.subtype || '-';
	}

	// Get agent name (tool_name or agent_type from data)
	function getAgentName(event: ClaudeEvent): string {
		// Check for user-related events
		if (event.subtype === 'user_prompt' ||
			event.subtype === 'UserPromptSubmit' ||
			event.subtype?.toLowerCase().includes('user')) {
			return 'user';
		}

		// Existing logic for tool_name or agent_type
		if (typeof event.data === 'object' && event.data !== null) {
			const data = event.data as Record<string, unknown>;
			return (data.tool_name as string) || (data.agent_type as string) || '-';
		}
		return '-';
	}

	// Calculate duration for correlated events (pre_tool -> post_tool)
	function getDuration(event: ClaudeEvent): string | null {
		// Only calculate for post_tool events with correlation_id
		if (event.subtype !== 'post_tool' || !event.correlation_id) {
			return null;
		}

		// Find the matching pre_tool event
		const preEvent = allEvents.find(
			e => e.correlation_id === event.correlation_id && e.subtype === 'pre_tool'
		);

		if (!preEvent) {
			return null;
		}

		// Calculate duration in milliseconds
		const eventTime = typeof event.timestamp === 'string'
			? new Date(event.timestamp).getTime()
			: event.timestamp;
		const preEventTime = typeof preEvent.timestamp === 'string'
			? new Date(preEvent.timestamp).getTime()
			: preEvent.timestamp;

		const ms = eventTime - preEventTime;

		// Format duration based on magnitude
		if (ms < 1000) {
			return `${ms}ms`;
		} else if (ms < 60000) {
			return `${(ms / 1000).toFixed(2)}s`;
		} else {
			const minutes = Math.floor(ms / 60000);
			const seconds = ((ms % 60000) / 1000).toFixed(0);
			return `${minutes}m ${seconds}s`;
		}
	}
</script>

<div class="flex flex-col h-full bg-white dark:bg-slate-900">
	<!-- Header with filters -->
	<div class="flex items-center justify-between px-6 py-3 bg-slate-100 dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700 transition-colors">
		<div class="flex items-center gap-3">
			<select
				bind:value={activityFilter}
				class="px-3 py-1 text-xs font-medium bg-white dark:bg-slate-700 hover:bg-slate-50 dark:hover:bg-slate-600 rounded transition-colors border border-slate-300 dark:border-slate-600 text-slate-900 dark:text-slate-200"
			>
				<option value="">All Activities</option>
				{#each uniqueActivities as activity}
					<option value={activity}>{activity}</option>
				{/each}
			</select>
		</div>
		<div class="flex items-center gap-3">
			<span class="text-sm text-slate-700 dark:text-slate-300">{events.length} events</span>
			<button
				onclick={clearEvents}
				class="px-3 py-1 text-xs font-medium bg-white dark:bg-slate-700 hover:bg-slate-50 dark:hover:bg-slate-600 rounded transition-colors border border-slate-300 dark:border-slate-600 text-slate-900 dark:text-slate-200"
			>
				Clear
			</button>
		</div>
	</div>

	<div class="flex-1 overflow-y-auto">
		{#if events.length === 0}
			<div class="text-center py-12 text-slate-600 dark:text-slate-400">
				<svg class="w-16 h-16 mx-auto mb-3 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
				</svg>
				<p class="text-lg mb-2 font-medium">No events yet</p>
				<p class="text-sm text-slate-500 dark:text-slate-500">Waiting for Claude activity...</p>
			</div>
		{:else}
			<!-- Table header -->
			<div class="grid grid-cols-[110px_120px_160px_120px_100px] gap-3 px-4 py-2 bg-slate-50 dark:bg-slate-900 border-b border-slate-200 dark:border-slate-700 text-xs font-semibold text-slate-700 dark:text-slate-300 sticky top-0 transition-colors">
				<div>Event</div>
				<div>Source</div>
				<div>Activity</div>
				<div>Agent</div>
				<div class="text-right">Timestamp</div>
			</div>

			<!-- Event rows - scrollable container -->
			<div
				bind:this={eventListContainer}
				onkeydown={handleKeydown}
				tabindex="0"
				role="list"
				aria-label="Event list - use arrow keys to navigate"
				class="focus:outline-none overflow-y-auto max-h-[calc(100vh-280px)]"
			>
				{#each events as event, i (event.id)}
					<button
						data-event-id={event.id}
						onclick={() => selectEvent(event)}
						class="w-full text-left px-4 py-2.5 transition-colors border-l-4 grid grid-cols-[110px_120px_160px_120px_100px] gap-3 items-center text-xs
							{selectedEvent?.id === event.id
								? 'bg-cyan-50 dark:bg-cyan-500/20 border-l-cyan-500 dark:border-l-cyan-400 ring-1 ring-cyan-300 dark:ring-cyan-500/30'
								: `border-l-transparent ${i % 2 === 0 ? 'bg-slate-50 dark:bg-slate-800/40' : 'bg-white dark:bg-slate-800/20'} hover:bg-slate-100 dark:hover:bg-slate-700/30`}"
					>
						<!-- Event (socket event name) with color coding -->
						<div>
							<span class="font-mono px-2 py-0.5 rounded-md bg-slate-100 dark:bg-black/30 {getEventTypeColor(event.type)} font-medium text-[11px]">
								{event.event || event.type}
							</span>
						</div>

						<!-- Source -->
						<div class="text-slate-700 dark:text-slate-300 truncate font-mono text-[11px]">
							{getEventSource(event)}
						</div>

						<!-- Activity (subtype) with optional duration badge -->
						<div class="text-slate-700 dark:text-slate-300 truncate flex items-center gap-2">
							<span>{getActivity(event)}</span>
							{#if getDuration(event)}
								<span class="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold bg-green-500/20 text-green-600 dark:text-green-400 border border-green-500/30">
									→ {getDuration(event)}
								</span>
							{/if}
						</div>

						<!-- Agent (tool_name or agent_type) -->
						<div class="text-slate-700 dark:text-slate-300 truncate">
							{getAgentName(event)}
						</div>

						<!-- Timestamp (right-aligned) -->
						<div class="text-slate-700 dark:text-slate-300 font-mono text-[11px] text-right">
							{formatTimestamp(event.timestamp)}
						</div>
					</button>
				{/each}
			</div>
		{/if}
	</div>
</div>
