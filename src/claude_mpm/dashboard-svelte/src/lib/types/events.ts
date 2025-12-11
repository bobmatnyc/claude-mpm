export interface ClaudeEvent {
	id: string;
	type: string; // More flexible - server sends various types like 'hook', 'session.ended', etc.
	timestamp: string | number;
	data: unknown;
	agent?: string;
	sessionId?: string; // TypeScript/client format (camelCase)
	session_id?: string; // Python/server format (snake_case)
	subtype?: string;
	source?: string;
	metadata?: unknown;
}

export interface SocketState {
	connected: boolean;
	url: string;
	error?: string;
}
