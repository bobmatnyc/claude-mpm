import { writable, derived, get } from 'svelte/store';
import { io, type Socket } from 'socket.io-client';
import type { ClaudeEvent } from '$lib/types/events';

let eventCounter = 0;

// Use traditional Svelte stores - compatible with static adapter + SSR
function createSocketStore() {
	const socket = writable<Socket | null>(null);
	const isConnected = writable(false);
	const events = writable<ClaudeEvent[]>([]);
	const streams = writable<Set<string>>(new Set());
	const streamMetadata = writable<Map<string, { projectPath: string; projectName: string }>>(new Map());
	const error = writable<string | null>(null);
	const selectedStream = writable<string>('');

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
		const streamId =
			data.session_id ||
			data.sessionId ||
			data.data?.session_id ||
			data.data?.sessionId ||
			data.source;

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

				// Auto-select first stream if no stream selected and this is the first stream
				const currentSelected = get(selectedStream);
				if (prevSize === 0 && newStreams.size === 1 && (currentSelected === '' || currentSelected === 'all')) {
					console.log('Socket store: Auto-selecting first stream:', streamId);
					selectedStream.set(streamId);
				}

				return newStreams;
			});

			// Extract and store project path information
			// Check multiple possible locations for working directory/cwd
			const projectPath =
				data.cwd ||
				data.data?.working_directory ||
				data.data?.cwd ||
				data.metadata?.working_directory ||
				data.metadata?.cwd;

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
