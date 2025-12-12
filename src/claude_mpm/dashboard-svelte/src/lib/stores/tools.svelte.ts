import { writable, derived, get } from 'svelte/store';
import type { ClaudeEvent, Tool } from '$lib/types/events';

function createToolsStore(eventsStore: ReturnType<typeof writable<ClaudeEvent[]>>) {
	const tools = derived(eventsStore, ($events) => {
		const toolMap = new Map<string, Tool>();

		// Process all events to build tool map
		$events.forEach(event => {
			// Extract subtype from multiple possible locations
			// Check both top-level event.subtype AND nested event.data.subtype
			const data = event.data as Record<string, unknown> | null;
			const eventSubtype = event.subtype || (data?.subtype as string);

			// Only process pre_tool and post_tool events
			if (eventSubtype !== 'pre_tool' && eventSubtype !== 'post_tool') {
				return;
			}

			// Extract correlation_id from multiple possible locations
			const correlationId =
				event.correlation_id ||
				(data?.correlation_id as string) ||
				(data?.tool_call_id as string);

			// Generate fallback ID if no correlation_id found
			// Use session_id + tool_name + timestamp for basic grouping
			const sessionId = event.session_id || event.sessionId || (data?.session_id as string) || 'unknown';
			const toolName = (data?.tool_name as string) || 'Unknown';
			const timestamp = typeof event.timestamp === 'string' ? event.timestamp : new Date(event.timestamp).toISOString();

			const id = correlationId || `${sessionId}_${toolName}_${timestamp}`;

			// Debug logging to see what events are being processed
			console.log(`[Tools Store] Processing ${eventSubtype} event:`, {
				correlationId,
				generatedId: id,
				toolName,
				sessionId,
				hasCorrelationId: !!correlationId,
				eventData: data
			});

			if (eventSubtype === 'pre_tool') {
				// Create or update tool entry
				const existingTool = toolMap.get(id);

				// Extract operation description from tool input
				const operation = extractOperation(toolName, data);

				if (existingTool) {
					// Update existing tool with pre_tool data
					existingTool.preToolEvent = event;
					existingTool.toolName = toolName;
					existingTool.operation = operation;
					existingTool.timestamp = event.timestamp;
				} else {
					// Create new tool entry
					toolMap.set(id, {
						id: id,
						toolName,
						operation,
						status: 'pending',
						duration: null,
						preToolEvent: event,
						postToolEvent: null,
						timestamp: event.timestamp
					});
				}
			} else if (eventSubtype === 'post_tool') {
				// Try to match with pre_tool event using correlation_id first
				// If no correlation_id, try to find by session + tool + time window
				let existingTool = toolMap.get(id);

				// If using fallback ID, try to find pre_tool within 30 seconds
				if (!correlationId && !existingTool) {
					const postTime = typeof event.timestamp === 'string'
						? new Date(event.timestamp).getTime()
						: event.timestamp;

					// Search for matching pre_tool event
					for (const [toolId, tool] of toolMap.entries()) {
						if (tool.toolName === toolName && !tool.postToolEvent) {
							const preTime = typeof tool.timestamp === 'string'
								? new Date(tool.timestamp).getTime()
								: tool.timestamp;

							// Match if within 30 seconds
							if (Math.abs(postTime - preTime) < 30000) {
								existingTool = tool;
								break;
							}
						}
					}
				}

				if (existingTool) {
					existingTool.postToolEvent = event;

					// Determine success/error status
					const postData = event.data as Record<string, unknown> | null;
					const hasError = postData?.error || postData?.is_error;
					existingTool.status = hasError ? 'error' : 'success';

					// Calculate duration
					const preTime = typeof existingTool.preToolEvent.timestamp === 'string'
						? new Date(existingTool.preToolEvent.timestamp).getTime()
						: existingTool.preToolEvent.timestamp;
					const postTime = typeof event.timestamp === 'string'
						? new Date(event.timestamp).getTime()
						: event.timestamp;
					existingTool.duration = postTime - preTime;
				} else {
					// Post event arrived before pre event (shouldn't happen, but handle it)
					const operation = extractOperation(toolName, data);
					toolMap.set(id, {
						id: id,
						toolName,
						operation,
						status: data?.error || data?.is_error ? 'error' : 'success',
						duration: null,
						preToolEvent: event, // Use post as placeholder
						postToolEvent: event,
						timestamp: event.timestamp
					});
				}
			}
		});

		// Convert map to sorted array (newest first)
		return Array.from(toolMap.values()).sort((a, b) => {
			const aTime = typeof a.timestamp === 'string'
				? new Date(a.timestamp).getTime()
				: a.timestamp;
			const bTime = typeof b.timestamp === 'string'
				? new Date(b.timestamp).getTime()
				: b.timestamp;
			return bTime - aTime;
		});
	});

	return tools;
}

function extractOperation(toolName: string, data: Record<string, unknown> | null): string {
	if (!data) return 'No details';

	switch (toolName) {
		case 'Bash':
			const command = data.command as string;
			return command ? truncate(command, 40) : 'No command';

		case 'Read':
			const filePath = data.file_path as string;
			return filePath ? `Read ${truncate(filePath, 35)}` : 'Read file';

		case 'Edit':
			const editPath = data.file_path as string;
			return editPath ? `Edit ${truncate(editPath, 35)}` : 'Edit file';

		case 'Write':
			const writePath = data.file_path as string;
			return writePath ? `Write ${truncate(writePath, 35)}` : 'Write file';

		case 'Grep':
			const pattern = data.pattern as string;
			return pattern ? `Search: ${truncate(pattern, 30)}` : 'Search';

		case 'Glob':
			const globPattern = data.pattern as string;
			return globPattern ? `Find: ${truncate(globPattern, 30)}` : 'Find files';

		default:
			// Try to extract a meaningful description from data
			if (data.description) {
				return truncate(data.description as string, 40);
			}
			if (data.action) {
				return truncate(data.action as string, 40);
			}
			if (data.query) {
				return truncate(data.query as string, 40);
			}
			return 'Tool execution';
	}
}

function truncate(str: string, maxLen: number): string {
	if (str.length <= maxLen) return str;
	return str.slice(0, maxLen - 3) + '...';
}

export { createToolsStore };
