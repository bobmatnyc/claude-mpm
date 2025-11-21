/**
 * Events Store (Traditional Svelte Stores)
 *
 * Manages incoming Claude Code hook events with:
 * - Event buffering (last 1000 events)
 * - Automatic filtering capability
 * - Event statistics
 *
 * IMPORTANT: This file uses traditional stores instead of Svelte 5 runes
 * because the store is created at module-load time, outside component context.
 * Runes ($state, $derived) can only be used inside components.
 */

import { writable, derived } from 'svelte/store';

const MAX_EVENTS = 1000;

function createEventsStore() {
  // Use writable stores instead of $state
  const events = writable([]);
  const totalReceived = writable(0);

  // Use derived stores instead of $derived
  const count = derived(events, ($events) => $events.length);
  const isEmpty = derived(events, ($events) => $events.length === 0);

  // Event type counts
  const eventTypeCounts = derived(events, ($events) => {
    const counts = {};
    for (const event of $events) {
      const type = event.type || 'unknown';
      counts[type] = (counts[type] || 0) + 1;
    }
    return counts;
  });

  function addEvent(event) {
    events.update(($events) => {
      // Add timestamp if not present
      if (!event.timestamp) {
        event.timestamp = new Date().toISOString();
      }

      // Add internal ID for React key stability
      let currentTotal;
      totalReceived.subscribe((val) => { currentTotal = val; })();
      event._id = `${event.timestamp}-${currentTotal}`;

      // Add to beginning of array (newest first)
      const newEvents = [event, ...$events];

      // Trim to max size
      return newEvents.length > MAX_EVENTS
        ? newEvents.slice(0, MAX_EVENTS)
        : newEvents;
    });

    // Increment total
    totalReceived.update((n) => n + 1);
  }

  function addEvents(newEvents) {
    for (const event of newEvents) {
      addEvent(event);
    }
  }

  function clear() {
    events.set([]);
    totalReceived.set(0);
  }

  function filterByType(type) {
    let result;
    events.subscribe(($events) => {
      result = $events.filter((e) => e.type === type);
    })();
    return result;
  }

  function filterBySource(source) {
    let result;
    events.subscribe(($events) => {
      result = $events.filter((e) => e.source === source);
    })();
    return result;
  }

  function filterBySubtype(subtype) {
    let result;
    events.subscribe(($events) => {
      result = $events.filter((e) => e.subtype === subtype);
    })();
    return result;
  }

  return {
    // Export stores with subscribe method for Svelte auto-subscription
    events: { subscribe: events.subscribe },
    count: { subscribe: count.subscribe },
    isEmpty: { subscribe: isEmpty.subscribe },
    totalReceived: { subscribe: totalReceived.subscribe },
    eventTypeCounts: { subscribe: eventTypeCounts.subscribe },
    // Export methods
    addEvent,
    addEvents,
    clear,
    filterByType,
    filterBySource,
    filterBySubtype
  };
}

export const eventsStore = createEventsStore();
