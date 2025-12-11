import { io, type Socket } from 'socket.io-client';
import type { ClaudeEvent } from '$lib/types/events';

class SocketStore {
	socket = $state<Socket | null>(null);
	isConnected = $state(false);
	events = $state<ClaudeEvent[]>([]);
	error = $state<string | null>(null);

	connect(url: string = 'http://localhost:8765') {
		if (this.socket?.connected) {
			return;
		}

		this.socket = io(url, {
			transports: ['websocket', 'polling'],
			reconnection: true,
			reconnectionDelay: 1000,
			reconnectionAttempts: 5
		});

		this.socket.on('connect', () => {
			this.isConnected = true;
			this.error = null;
			console.log('Socket.IO connected');
		});

		this.socket.on('disconnect', () => {
			this.isConnected = false;
			console.log('Socket.IO disconnected');
		});

		this.socket.on('connect_error', (err) => {
			this.error = err.message;
			console.error('Socket.IO connection error:', err);
		});

		this.socket.on('claude_event', (data: ClaudeEvent) => {
			this.events = [...this.events, data];
		});

		this.socket.on('agent_event', (data: unknown) => {
			console.log('Agent event:', data);
		});
	}

	disconnect() {
		if (this.socket) {
			this.socket.disconnect();
			this.socket = null;
			this.isConnected = false;
		}
	}

	clearEvents() {
		this.events = [];
	}
}

export const socketStore = new SocketStore();
