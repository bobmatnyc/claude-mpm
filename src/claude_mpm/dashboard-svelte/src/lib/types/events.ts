export interface ClaudeEvent {
	id: string;
	type: 'tool_call' | 'tool_result' | 'message' | 'error';
	timestamp: string;
	data: unknown;
	agent?: string;
	sessionId?: string;
}

export interface SocketState {
	connected: boolean;
	url: string;
	error?: string;
}
