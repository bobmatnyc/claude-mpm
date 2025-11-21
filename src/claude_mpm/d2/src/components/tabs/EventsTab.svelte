<script>
  import { eventsStore } from '../../stores/events.js';

  let expandedEventId = $state(null);
  let scrollContainer;

  // Auto-scroll to newest events
  $effect(() => {
    if (scrollContainer && $eventsStore.count > 0) {
      // Small delay to ensure DOM update
      setTimeout(() => {
        scrollContainer.scrollTop = 0;
      }, 10);
    }
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
        Total: <strong>{$eventsStore.totalReceived}</strong>
      </span>
      <span class="stat">
        Displayed: <strong>{$eventsStore.count}</strong>
      </span>
      {#if $eventsStore.count > 0}
        <button class="clear-btn" onclick={() => eventsStore.clear()}>
          Clear
        </button>
      {/if}
    </div>
  </div>

  <div class="events-list" bind:this={scrollContainer}>
    {#if $eventsStore.isEmpty}
      <div class="empty-state">
        <div class="empty-icon">📡</div>
        <p>Waiting for events...</p>
        <p class="empty-hint">Events will appear here as they are received from Socket.IO</p>
      </div>
    {:else}
      {#each $eventsStore.events as event (event._id)}
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
    background: #0f0f0f;
  }

  .events-header {
    padding: 20px 24px;
    border-bottom: 1px solid #333;
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: #1a1a1a;
  }

  h2 {
    font-size: 18px;
    font-weight: 600;
    color: #fff;
  }

  .stats {
    display: flex;
    gap: 16px;
    align-items: center;
  }

  .stat {
    font-size: 13px;
    color: #888;
  }

  .stat strong {
    color: #e0e0e0;
    font-weight: 600;
  }

  .clear-btn {
    padding: 6px 12px;
    background: rgba(239, 68, 68, 0.1);
    color: #ef4444;
    border: 1px solid rgba(239, 68, 68, 0.3);
    border-radius: 4px;
    font-size: 12px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s ease;
  }

  .clear-btn:hover {
    background: rgba(239, 68, 68, 0.2);
    border-color: rgba(239, 68, 68, 0.5);
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
    color: #666;
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
    color: #555;
  }

  .event-item {
    background: #1a1a1a;
    border: 1px solid #333;
    border-radius: 8px;
    margin-bottom: 12px;
    overflow: hidden;
    transition: all 0.2s ease;
  }

  .event-item:hover {
    border-color: #444;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
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
    color: #888;
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
    color: #e0e0e0;
    font-weight: 500;
  }

  .expand-icon {
    width: 24px;
    height: 24px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #666;
    border-radius: 4px;
    transition: all 0.2s ease;
    font-size: 10px;
  }

  .event-header:hover .expand-icon {
    background: rgba(255, 255, 255, 0.05);
    color: #888;
  }

  .expand-icon.expanded {
    color: #3b82f6;
  }

  .event-details {
    padding: 16px;
    background: #0f0f0f;
    border-top: 1px solid #333;
  }

  .event-details pre {
    margin: 0;
    padding: 12px;
    background: #000;
    border: 1px solid #222;
    border-radius: 4px;
    overflow-x: auto;
    font-size: 12px;
    line-height: 1.5;
  }

  .event-details code {
    color: #10b981;
    font-family: 'Monaco', 'Menlo', monospace;
  }
</style>
