import { writable, derived } from 'svelte/store';
import type { ClaudeEvent, Tool } from '$lib/types/events';
import { correlateToolEvents, getToolName, getCorrelationId } from '$lib/utils/event-correlation';

function createToolsStore(eventsStore: ReturnType<typeof writable<ClaudeEvent[]>>) {
	const tools = derived(eventsStore, ($events) => {
		const toolMap = new Map<string, Tool>();

		// Filter to tool events only
		const toolEvents = $events.filter(event => {
			const data = event.data as Record<string, unknown> | null;
			const eventSubtype = event.subtype || (data?.subtype as string);
			return eventSubtype === 'pre_tool' || eventSubtype === 'post_tool';
		});

		// Correlate pre/post events using utility
		const correlations = correlateToolEvents(
			toolEvents.map(e => ({
				event: e.subtype === 'pre_tool' ? 'pre-tool' : 'post-tool',
				timestamp: e.timestamp,
				session_id: e.session_id,
				data: e.data
			}))
		);

		// Build tool map from correlations
		correlations.forEach((pair, correlationId) => {
			const preEvent = toolEvents.find(e =>
				e.subtype === 'pre_tool' &&
				(getCorrelationId({ event: 'pre-tool', timestamp: e.timestamp, session_id: e.session_id, data: e.data }) === correlationId)
			);

			const postEvent = toolEvents.find(e =>
				e.subtype === 'post_tool' &&
				(getCorrelationId({ event: 'post-tool', timestamp: e.timestamp, session_id: e.session_id, data: e.data }) === correlationId)
			);

			if (!preEvent) return;

			const data = preEvent.data as Record<string, unknown> | null;
			const toolName = getToolName({ event: 'pre-tool', timestamp: preEvent.timestamp, session_id: preEvent.session_id, data: preEvent.data });
			const operation = extractOperation(toolName, data);

			// Determine status
			let status: 'pending' | 'success' | 'error' = 'pending';
			let duration: number | null = null;

			if (postEvent) {
				const postData = postEvent.data as Record<string, unknown> | null;
				const hasError = postData?.error || postData?.is_error;
				status = hasError ? 'error' : 'success';

				// Calculate duration
				const preTime = typeof preEvent.timestamp === 'string'
					? new Date(preEvent.timestamp).getTime()
					: preEvent.timestamp;
				const postTime = typeof postEvent.timestamp === 'string'
					? new Date(postEvent.timestamp).getTime()
					: postEvent.timestamp;
				duration = postTime - preTime;
			}

			toolMap.set(correlationId, {
				id: correlationId,
				toolName,
				operation,
				status,
				duration,
				preToolEvent: preEvent,
				postToolEvent: postEvent || null,
				timestamp: preEvent.timestamp
			});
		});

		// Convert to sorted array (newest first)
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
			const description = data.description as string;
			const command = data.command as string;
			const opType = data.operation_type as string;
			if (description) return truncate(description, 40);
			if (command) return truncate(command, 40);
			return opType || 'No command';

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
