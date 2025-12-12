import { io, type Socket } from 'socket.io-client';
import type { ClaudeEvent } from '$lib/types/events';

let eventCounter = 0;

// Svelte 5 runes MUST be at module scope, not in class instances
function createSocketStore() {
	let socket = $state<Socket | null>(null);
	let isConnected = $state(false);
	let events = $state<ClaudeEvent[]>([]);
	let streams = $state<Set<string>>(new Set());
	let error = $state<string | null>(null);

	function connect(url: string = 'http://localhost:8765') {
		if (socket?.connected) {
			return;
		}

		console.log('Connecting to Socket.IO server:', url);

		socket = io(url, {
			// Use polling first for reliability, then upgrade to websocket
			transports: ['polling', 'websocket'],
			upgrade: true,
			reconnection: true,
			reconnectionDelay: 1000,
			reconnectionAttempts: 10,
			timeout: 20000,
		});

		socket.on('connect', () => {
			isConnected = true;
			error = null;
			console.log('Socket.IO connected, socket id:', socket?.id);
		});

		socket.on('disconnect', (reason) => {
			isConnected = false;
			console.log('Socket.IO disconnected, reason:', reason);
		});

		socket.on('connect_error', (err) => {
			error = err.message;
			console.error('Socket.IO connection error:', err);
		});

		// Listen for claude events
		socket.on('claude_event', (data: ClaudeEvent) => {
			console.log('Received claude_event:', data);
			handleEvent(data);
		});

		// Listen for heartbeat events (server sends these periodically)
		socket.on('heartbeat', (data: unknown) => {
			// Heartbeats confirm connection is alive - don't log to reduce noise
		});

		// Catch-all for debugging
		socket.onAny((eventName, ...args) => {
			if (eventName !== 'heartbeat') {
				console.log('Socket event:', eventName, args);
			}
		});
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
		events = [...events, eventWithId];
		console.log('Socket store: Added event, total events:', events.length);

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
			const prevSize = streams.size;
			console.log('Socket store: Adding stream:', streamId, 'Previous streams:', Array.from(streams));
			streams = new Set([...streams, streamId]);
			console.log('Socket store: Updated streams:', Array.from(streams), 'Size changed:', prevSize, '->', streams.size);
		} else {
			console.log('Socket store: No stream ID found in event:', JSON.stringify(data, null, 2));
		}
	}

	function disconnect() {
		if (socket) {
			socket.disconnect();
			socket = null;
			isConnected = false;
		}
	}

	function clearEvents() {
		events = [];
	}

	return {
		// Expose reactive state as getters
		get socket() { return socket; },
		get isConnected() { return isConnected; },
		get events() { return events; },
		get streams() { return streams; },
		get error() { return error; },
		// Expose methods
		connect,
		disconnect,
		clearEvents
	};
}

export const socketStore = createSocketStore();
