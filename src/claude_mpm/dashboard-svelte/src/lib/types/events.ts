export interface ClaudeEvent {
	id: string;
	event?: string; // Socket event name (claude_event, hook_event, cli_event, etc.)
	type: string; // More flexible - server sends various types like 'hook', 'session.ended', etc.
	timestamp: string | number;
	data: unknown;
	agent?: string;
	sessionId?: string; // TypeScript/client format (camelCase)
	session_id?: string; // Python/server format (snake_case)
	subtype?: string;
	source?: string;
	metadata?: unknown;
	cwd?: string; // Working directory (from Claude Code hooks)
	correlation_id?: string; // For correlating related events (e.g., pre_tool/post_tool pairs)
}

export interface SocketState {
	connected: boolean;
	url: string;
	error?: string;
}

export interface Tool {
	id: string; // correlation_id or generated key
	toolName: string;
	operation: string;
	status: 'pending' | 'success' | 'error';
	duration: number | null; // milliseconds
	preToolEvent: ClaudeEvent;
	postToolEvent: ClaudeEvent | null;
	timestamp: string | number; // From pre_tool event
}

export interface StreamEvent {
	event: string; // Event type (pre-tool, post-tool, etc.)
	timestamp: string | number;
	session_id?: string;
	data: unknown;
}
