<script>
  import { eventsStore } from '../../stores/events.js';

  // Destructure individual stores from eventsStore
  const { events, count, isEmpty, totalReceived } = eventsStore;

  let expandedEventId = $state(null);
  let scrollContainer = $state(null);
  let previousEventCount = $state(0);

  // $effect at top-level (correct Svelte 5 Runes usage)
  // Effects run during component initialization and re-run when dependencies change
  // The scrollContainer null-check protects against initial undefined state
  $effect(() => {
    // Access the reactive store value
    const currentCount = $count;

    // Only scroll if events were added AND container exists (not on initial load or clear)
    if (scrollContainer && currentCount > 0 && currentCount > previousEventCount) {
      // Use requestAnimationFrame for smooth scrolling
      requestAnimationFrame(() => {
        if (scrollContainer) {
          scrollContainer.scrollTop = 0;
        }
      });
    }

    // Update previous count for next comparison
    previousEventCount = currentCount;
  });

  function toggleExpand(eventId) {
    expandedEventId = expandedEventId === eventId ? null : eventId;
  }

  function getEventColor(event) {
    const sourceColors = {
      'hook': '#3b82f6',
      'system': '#10b981',
      'api': '#f59e0b'
    };
    return sourceColors[event.source] || '#6b7280';
  }

  function formatTimestamp(timestamp) {
    try {
      const date = new Date(timestamp);
      return date.toLocaleTimeString('en-US', {
        hour12: false,
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        fractionalSecondDigits: 3
      });
    } catch {
      return timestamp;
    }
  }

  function formatEventData(data) {
    return JSON.stringify(data, null, 2);
  }

  function getEventSummary(event) {
    // Create a readable summary from event data
    const { type, subtype, data } = event;

    if (subtype) {
      return `${type} → ${subtype}`;
    }

    return type || 'unknown';
  }
</script>

<div class="events-tab">
  <div class="events-header">
    <h2>Events Timeline</h2>
    <div class="stats">
      <span class="stat">
        Total: <strong>{$totalReceived}</strong>
      </span>
      <span class="stat">
        Displayed: <strong>{$count}</strong>
      </span>
      {#if $count > 0}
        <button class="clear-btn" onclick={() => eventsStore.clear()}>
          Clear
        </button>
      {/if}
    </div>
  </div>

  <div class="events-list" bind:this={scrollContainer}>
    {#if $isEmpty}
      <div class="empty-state">
        <div class="empty-icon">📡</div>
        <p>Waiting for events...</p>
        <p class="empty-hint">Events will appear here as they are received from Socket.IO</p>
      </div>
    {:else}
      {#each $events as event (event._id)}
        <div class="event-item">
          <button
            class="event-header"
            onclick={() => toggleExpand(event._id)}
            aria-expanded={expandedEventId === event._id}
          >
            <div class="event-meta">
              <span class="event-time">{formatTimestamp(event.timestamp)}</span>
              <span
                class="event-source"
                style="background: {getEventColor(event)}20; color: {getEventColor(event)}; border-color: {getEventColor(event)}40"
              >
                {event.source || 'unknown'}
              </span>
            </div>
            <div class="event-summary">
              {getEventSummary(event)}
            </div>
            <span class="expand-icon" class:expanded={expandedEventId === event._id}>
              {expandedEventId === event._id ? '▼' : '▶'}
            </span>
          </button>

          {#if expandedEventId === event._id}
            <div class="event-details">
              <pre><code>{formatEventData(event)}</code></pre>
            </div>
          {/if}
        </div>
      {/each}
    {/if}
  </div>
</div>

<style>
  .events-tab {
    display: flex;
    flex-direction: column;
    height: 100%;
    background: var(--bg-primary);
  }

  .events-header {
    padding: 20px 24px;
    border-bottom: 1px solid var(--border-color);
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: var(--bg-secondary);
  }

  h2 {
    font-size: 18px;
    font-weight: 600;
    color: var(--text-primary);
  }

  .stats {
    display: flex;
    gap: 16px;
    align-items: center;
  }

  .stat {
    font-size: 13px;
    color: var(--text-tertiary);
  }

  .stat strong {
    color: var(--text-primary);
    font-weight: 600;
  }

  .clear-btn {
    padding: 6px 12px;
    background: color-mix(in srgb, var(--error-color) 10%, transparent);
    color: var(--error-color);
    border: 1px solid color-mix(in srgb, var(--error-color) 30%, transparent);
    border-radius: 4px;
    font-size: 12px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s ease;
  }

  .clear-btn:hover {
    background: color-mix(in srgb, var(--error-color) 20%, transparent);
    border-color: color-mix(in srgb, var(--error-color) 50%, transparent);
  }

  .events-list {
    flex: 1;
    overflow-y: auto;
    padding: 16px;
  }

  .empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100%;
    color: var(--text-secondary);
    text-align: center;
  }

  .empty-icon {
    font-size: 48px;
    margin-bottom: 16px;
    opacity: 0.5;
  }

  .empty-state p {
    font-size: 14px;
    margin: 4px 0;
  }

  .empty-hint {
    font-size: 12px;
    color: var(--text-tertiary);
  }

  .event-item {
    background: var(--card-bg);
    border: 1px solid var(--border-color);
    border-radius: 8px;
    margin-bottom: 12px;
    overflow: hidden;
    transition: all 0.2s ease;
  }

  .event-item:hover {
    border-color: var(--border-color-light);
    box-shadow: var(--shadow-md);
  }

  .event-header {
    width: 100%;
    padding: 12px 16px;
    display: flex;
    align-items: center;
    gap: 12px;
    cursor: pointer;
    user-select: none;
    background: transparent;
    border: none;
    color: inherit;
    font: inherit;
    text-align: left;
  }

  .event-meta {
    display: flex;
    align-items: center;
    gap: 8px;
    min-width: 200px;
  }

  .event-time {
    font-family: 'Monaco', 'Menlo', monospace;
    font-size: 12px;
    color: var(--text-tertiary);
  }

  .event-source {
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    border: 1px solid;
  }

  .event-summary {
    flex: 1;
    font-size: 13px;
    color: var(--text-primary);
    font-weight: 500;
  }

  .expand-icon {
    width: 24px;
    height: 24px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--text-secondary);
    border-radius: 4px;
    transition: all 0.2s ease;
    font-size: 10px;
  }

  .event-header:hover .expand-icon {
    background: var(--overlay-bg);
    color: var(--text-tertiary);
  }

  .expand-icon.expanded {
    color: var(--accent-color);
  }

  .event-details {
    padding: 16px;
    background: var(--bg-primary);
    border-top: 1px solid var(--border-color);
  }

  .event-details pre {
    margin: 0;
    padding: 12px;
    background: var(--bg-secondary);
    border: 1px solid var(--border-color);
    border-radius: 4px;
    overflow-x: auto;
    font-size: 12px;
    line-height: 1.5;
  }

  .event-details code {
    color: var(--success-color);
    font-family: 'Monaco', 'Menlo', monospace;
  }
</style>
