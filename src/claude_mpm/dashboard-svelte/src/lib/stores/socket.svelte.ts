import { writable, derived, get } from 'svelte/store';
import { io, type Socket } from 'socket.io-client';
import type { ClaudeEvent } from '$lib/types/events';

let eventCounter = 0;

// Cache configuration
const CACHE_KEY_PREFIX = 'claude-mpm-events-';
const MAX_CACHED_EVENTS_PER_STREAM = 50;

// Safely check if localStorage is available (returns false in SSR)
function isLocalStorageAvailable(): boolean {
	if (typeof window === 'undefined') return false;
	try {
		const test = '__localStorage_test__';
		localStorage.setItem(test, test);
		localStorage.removeItem(test);
		return true;
	} catch {
		return false;
	}
}

// Load cached events for a specific stream from localStorage
function loadCachedEvents(streamId: string): ClaudeEvent[] {
	if (!isLocalStorageAvailable()) return [];

	try {
		const key = `${CACHE_KEY_PREFIX}${streamId}`;
		const cached = localStorage.getItem(key);
		if (cached) {
			const events = JSON.parse(cached);
			console.log(`[Cache] Loaded ${events.length} cached events for stream ${streamId}`);
			return events;
		}
	} catch (err) {
		console.warn(`[Cache] Failed to load cached events for stream ${streamId}:`, err);
	}
	return [];
}

// Save events for a specific stream to localStorage (keep last 50)
function saveCachedEvents(streamId: string, events: ClaudeEvent[]): void {
	if (!isLocalStorageAvailable()) return;

	try {
		const key = `${CACHE_KEY_PREFIX}${streamId}`;
		// Keep only last 50 events (FIFO)
		const eventsToCache = events.slice(-MAX_CACHED_EVENTS_PER_STREAM);
		localStorage.setItem(key, JSON.stringify(eventsToCache));
		console.log(`[Cache] Saved ${eventsToCache.length} events for stream ${streamId}`);
	} catch (err) {
		console.warn(`[Cache] Failed to save cached events for stream ${streamId}:`, err);
	}
}

// Group events by stream ID
function getStreamId(event: ClaudeEvent): string | null {
	return (
		event.session_id ||
		event.sessionId ||
		(event.data as any)?.session_id ||
		(event.data as any)?.sessionId ||
		event.source ||
		null
	);
}

// Use traditional Svelte stores - compatible with static adapter + SSR
function createSocketStore() {
	const socket = writable<Socket | null>(null);
	const isConnected = writable(false);
	const events = writable<ClaudeEvent[]>([]);
	const streams = writable<Set<string>>(new Set());
	const streamMetadata = writable<Map<string, { projectPath: string; projectName: string }>>(new Map());
	const error = writable<string | null>(null);
	const selectedStream = writable<string>('');

	// Load cached events on initialization (client-side only)
	if (typeof window !== 'undefined') {
		// This will be called after initial page load
		setTimeout(() => {
			const cachedStreams = getAllCachedStreams();
			if (cachedStreams.length > 0) {
				console.log(`[Cache] Found ${cachedStreams.length} cached streams`);

				// Load events from all cached streams
				const allCachedEvents: ClaudeEvent[] = [];
				const cachedStreamSet = new Set<string>();

				cachedStreams.forEach(streamId => {
					const streamEvents = loadCachedEvents(streamId);
					allCachedEvents.push(...streamEvents);
					if (streamEvents.length > 0) {
						cachedStreamSet.add(streamId);
					}
				});

				// Update stores with cached data
				if (allCachedEvents.length > 0) {
					events.set(allCachedEvents);
					streams.set(cachedStreamSet);
					console.log(`[Cache] Restored ${allCachedEvents.length} total cached events from ${cachedStreamSet.size} streams`);

					// Extract metadata from cached events
					const metadataMap = new Map<string, { projectPath: string; projectName: string }>();
					allCachedEvents.forEach(event => {
						const streamId = getStreamId(event);
						if (streamId && !metadataMap.has(streamId)) {
							// Try to extract working directory from event
							const projectPath =
								event.cwd ||
								event.working_directory ||
								(event.data as any)?.working_directory ||
								(event.data as any)?.cwd ||
								(event.metadata as any)?.working_directory ||
								(event.metadata as any)?.cwd;

							if (projectPath && typeof projectPath === 'string') {
								const projectName = projectPath.split('/').filter(Boolean).pop() || projectPath;
								metadataMap.set(streamId, { projectPath, projectName });
							}
						}
					});

					if (metadataMap.size > 0) {
						streamMetadata.set(metadataMap);
						console.log(`[Cache] Extracted metadata for ${metadataMap.size} streams`);
					}
				}
			}
		}, 0);
	}

	// Helper to get all cached stream IDs
	function getAllCachedStreams(): string[] {
		if (!isLocalStorageAvailable()) return [];

		const streamIds: string[] = [];
		try {
			for (let i = 0; i < localStorage.length; i++) {
				const key = localStorage.key(i);
				if (key?.startsWith(CACHE_KEY_PREFIX)) {
					streamIds.push(key.substring(CACHE_KEY_PREFIX.length));
				}
			}
		} catch (err) {
			console.warn('[Cache] Failed to enumerate cached streams:', err);
		}
		return streamIds;
	}

	function connect(url: string = 'http://localhost:8765') {
		const currentSocket = get(socket);
		if (currentSocket?.connected) {
			return;
		}

		console.log('Connecting to Socket.IO server:', url);

		const newSocket = io(url, {
			// Use polling first for reliability, then upgrade to websocket
			transports: ['polling', 'websocket'],
			upgrade: true,
			reconnection: true,
			reconnectionDelay: 1000,
			reconnectionAttempts: 10,
			timeout: 20000,
		});

		newSocket.on('connect', () => {
			isConnected.set(true);
			error.set(null);
			console.log('Socket.IO connected, socket id:', newSocket.id);
		});

		newSocket.on('disconnect', (reason) => {
			isConnected.set(false);
			console.log('Socket.IO disconnected, reason:', reason);
		});

		newSocket.on('connect_error', (err) => {
			error.set(err.message);
			console.error('Socket.IO connection error:', err);
		});

		// Listen for all event types from backend
		// Backend categorizes events as: claude_event, hook_event, cli_event, system_event, agent_event, build_event
		const eventTypes = ['claude_event', 'hook_event', 'cli_event', 'system_event', 'agent_event', 'build_event'];

		eventTypes.forEach(eventType => {
			newSocket.on(eventType, (data: ClaudeEvent) => {
				console.log(`Received ${eventType}:`, data);
				// Add the socket event name to the data
				handleEvent({ ...data, event: eventType });
			});
		});

		// Listen for historical events sent on connection
		newSocket.on('history', (data: { events: ClaudeEvent[], count: number, total_available: number }) => {
			console.log('Received event history:', data.count, 'events');
			if (data.events && Array.isArray(data.events)) {
				data.events.forEach(event => handleEvent(event));
			}
		});

		// Listen for heartbeat events (server sends these periodically)
		newSocket.on('heartbeat', (data: unknown) => {
			// Heartbeats confirm connection is alive - don't log to reduce noise
		});

		// Listen for hot reload events (server sends when files change in dev mode)
		newSocket.on('reload', (data: any) => {
			console.log('Hot reload triggered by server:', data);
			// Reload the page to get latest changes
			window.location.reload();
		});

		// Catch-all for debugging
		newSocket.onAny((eventName, ...args) => {
			if (eventName !== 'heartbeat') {
				console.log('Socket event:', eventName, args);
			}
		});

		socket.set(newSocket);
	}

	function handleEvent(data: any) {
		console.log('Socket store: handleEvent called with:', data);

		// Ensure event has an ID (generate one if missing)
		const eventWithId: ClaudeEvent = {
			...data,
			id: data.id || `evt_${Date.now()}_${++eventCounter}`,
			// Normalize timestamp
			timestamp: data.timestamp || new Date().toISOString(),
		};

		// Add event to list - triggers reactivity
		events.update(e => [...e, eventWithId]);
		console.log('Socket store: Added event, total events:', get(events).length);

		// Track unique streams
		// Check multiple possible field names for session/stream ID
		const streamId = getStreamId(eventWithId);

		console.log('Socket store: Extracted stream ID:', streamId);
		console.log('Socket store: Checked fields:', {
			session_id: data.session_id,
			sessionId: data.sessionId,
			data_session_id: data.data?.session_id,
			data_sessionId: data.data?.sessionId,
			source: data.source
		});

		if (streamId) {
			streams.update(s => {
				const prevSize = s.size;
				console.log('Socket store: Adding stream:', streamId, 'Previous streams:', Array.from(s));
				const newStreams = new Set([...s, streamId]);
				console.log('Socket store: Updated streams:', Array.from(newStreams), 'Size changed:', prevSize, '->', newStreams.size);

				// Auto-select stream based on priority:
				// 1. If this is the first stream detected, auto-select it
				// 2. If no stream is currently selected (empty string), auto-select this new stream (most recent)
				const currentSelected = get(selectedStream);
				if (prevSize === 0 || currentSelected === '') {
					console.log('Socket store: Auto-selecting stream:', streamId, 'Reason:', prevSize === 0 ? 'first stream' : 'no stream selected');
					selectedStream.set(streamId);
				}

				return newStreams;
			});

			// Extract and store project path information
			// Check multiple possible locations for working directory/cwd
			// Events can have various structures depending on their type:
			// - Hook events: data.cwd (from ConnectionManager line 148)
			// - Other events: data.working_directory, data.data.working_directory, etc.
			const projectPath =
				data.cwd ||                            // Direct cwd field (from hook events)
				data.working_directory ||              // Direct working_directory field
				data.data?.working_directory ||        // Nested in data object
				data.data?.cwd ||                      // Nested in data object as cwd
				data.metadata?.working_directory ||    // Nested in metadata object
				data.metadata?.cwd;                    // Nested in metadata as cwd

			if (projectPath) {
				// Extract project name from path (last directory component)
				const projectName = projectPath.split('/').filter(Boolean).pop() || projectPath;

				streamMetadata.update(m => {
					const newMap = new Map(m);
					newMap.set(streamId, { projectPath, projectName });
					console.log('Socket store: Updated metadata for stream:', streamId, { projectPath, projectName });
					return newMap;
				});
			}

			// Cache events for this stream (keep last 50)
			const allEvents = get(events);
			const streamEvents = allEvents.filter(e => getStreamId(e) === streamId);
			saveCachedEvents(streamId, streamEvents);
		} else {
			console.log('Socket store: No stream ID found in event:', JSON.stringify(data, null, 2));
		}
	}

	function disconnect() {
		const currentSocket = get(socket);
		if (currentSocket) {
			currentSocket.disconnect();
			socket.set(null);
			isConnected.set(false);
		}
	}

	function clearEvents() {
		events.set([]);
	}

	function setSelectedStream(streamId: string) {
		selectedStream.set(streamId);
	}

	return {
		socket,
		isConnected,
		events,
		streams,
		streamMetadata,
		error,
		selectedStream,
		connect,
		disconnect,
		clearEvents,
		setSelectedStream
	};
}

export const socketStore = createSocketStore();
