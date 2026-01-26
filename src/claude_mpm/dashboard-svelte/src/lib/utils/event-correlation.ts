/**
 * Event Correlation Utility
 *
 * Provides reusable correlation logic for matching pre/post tool events.
 * Supports correlation by correlation_id with fallback matching strategies.
 */

import type { StreamEvent } from '$lib/types/events';

/**
 * Correlates pre-tool and post-tool events based on correlation_id
 *
 * @param events - Array of stream events to correlate
 * @returns Map of correlation_id to { pre, post } event pairs
 */
export function correlateToolEvents(events: StreamEvent[]): Map<
  string,
  { pre: StreamEvent; post?: StreamEvent }
> {
  const correlations = new Map<string, { pre: StreamEvent; post?: StreamEvent }>();

  for (const event of events) {
    // Check for correlation_id at top level first (normalized events), then in data
    const data = event.data && typeof event.data === 'object' ? event.data as Record<string, unknown> : null;
    const correlationId = (event as any).correlation_id || data?.correlation_id as string | undefined;

    if (!correlationId) continue;

    if (event.event === 'pre-tool') {
      // Initialize or update pre-event
      if (!correlations.has(correlationId)) {
        correlations.set(correlationId, { pre: event });
      } else {
        const existing = correlations.get(correlationId)!;
        correlations.set(correlationId, { ...existing, pre: event });
      }
    } else if (event.event === 'post-tool') {
      // Add post-event to existing correlation or create new entry
      if (!correlations.has(correlationId)) {
        // Orphaned post-tool (pre-tool not seen yet or missing)
        // Create entry with placeholder pre-event
        correlations.set(correlationId, {
          pre: { ...event, event: 'pre-tool' },
          post: event
        });
      } else {
        const existing = correlations.get(correlationId)!;
        correlations.set(correlationId, { ...existing, post: event });
      }
    }
  }

  return correlations;
}

/**
 * Extracts tool name from event data
 */
export function getToolName(event: StreamEvent): string {
  if (!event.data || typeof event.data !== 'object') return 'Unknown';
  const data = event.data as Record<string, unknown>;
  return (data.tool_name as string) || 'Unknown';
}

/**
 * Extracts correlation ID from event (checks top-level first, then data)
 */
export function getCorrelationId(event: StreamEvent): string | undefined {
  // Check top-level first (normalized events have correlation_id at root)
  if ((event as any).correlation_id) {
    return (event as any).correlation_id as string;
  }
  // Fall back to checking in data
  if (!event.data || typeof event.data !== 'object') return undefined;
  const data = event.data as Record<string, unknown>;
  return data.correlation_id as string | undefined;
}

/**
 * Checks if event is a pre-tool event
 */
export function isPreToolEvent(event: StreamEvent): boolean {
  return event.event === 'pre-tool';
}

/**
 * Checks if event is a post-tool event
 */
export function isPostToolEvent(event: StreamEvent): boolean {
  return event.event === 'post-tool';
}

/**
 * Filters events by session ID
 */
export function filterBySession(events: StreamEvent[], sessionId: string | null): StreamEvent[] {
  if (!sessionId) return events;
  return events.filter(e => e.session_id === sessionId);
}
