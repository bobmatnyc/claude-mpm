import { useMemo } from 'react';
import { useDashboard, DashboardEvent } from '../contexts/DashboardContext';

/**
 * Get event type category for styling and filtering
 */
function getEventCategory(eventType?: string): string {
  if (!eventType) return 'info';

  const type = eventType.toLowerCase();

  if (type.includes('agent') || type.includes('subagent')) return 'agent';
  if (type.includes('tool') || type === 'bash' || type === 'edit' || type === 'read' || type === 'write') return 'tool';
  if (type.includes('file') || type.includes('edit') || type.includes('write') || type.includes('read')) return 'file';
  if (type.includes('session') || type === 'start' || type === 'stop') return 'session';
  if (type.includes('error') || type.includes('fail')) return 'error';
  if (type.includes('memory') || type.includes('todo')) return 'info';
  if (type.includes('claude') || type.includes('request') || type.includes('response')) return 'info';

  return 'info';
}

/**
 * Format timestamp consistently
 */
function formatTimestamp(timestamp: number): string {
  if (!timestamp) return 'Unknown';

  const date = new Date(timestamp);
  return date.toLocaleTimeString('en-US', {
    hour12: false,
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    fractionalSecondDigits: 3
  });
}

/**
 * Enhanced event interface with computed properties
 */
export interface EnhancedEvent extends DashboardEvent {
  category: string;
  formattedTime: string;
  displayType: string;
  preview: string;
  size: number;
}

/**
 * Hook for managing and filtering events with computed properties
 */
export function useEvents() {
  const { state, setFilter, setSetting } = useDashboard();

  // Enhanced events with computed properties
  const enhancedEvents = useMemo((): EnhancedEvent[] => {
    return state.events.map(event => {
      const category = getEventCategory(event.type);
      const formattedTime = formatTimestamp(event.timestamp);

      // Build display type
      let displayType = event.type || 'unknown';
      if (event.subtype) {
        displayType += `:${event.subtype}`;
      }

      // Generate preview
      const displayData = event.raw || event.data;
      const preview = JSON.stringify(displayData || {})
        .substring(0, 100)
        .replace(/[\r\n]+/g, ' ');

      // Calculate size
      const size = JSON.stringify(event).length;

      return {
        ...event,
        category,
        formattedTime,
        displayType,
        preview: preview + (JSON.stringify(displayData || {}).length > 100 ? '...' : ''),
        size
      };
    });
  }, [state.events]);

  // Filtered events based on current filters
  const filteredEvents = useMemo((): EnhancedEvent[] => {
    let filtered = [...enhancedEvents];

    // Apply search filter
    if (state.filters.searchTerm) {
      const search = state.filters.searchTerm.toLowerCase();
      filtered = filtered.filter(event =>
        JSON.stringify(event).toLowerCase().includes(search)
      );
    }

    // Apply type filter
    if (state.filters.typeFilter) {
      filtered = filtered.filter(event =>
        event.category === state.filters.typeFilter
      );
    }

    // Sort by timestamp (newest first)
    filtered.sort((a, b) => (b.timestamp || 0) - (a.timestamp || 0));

    return filtered;
  }, [enhancedEvents, state.filters.searchTerm, state.filters.typeFilter]);

  // Statistics for filtered events
  const stats = useMemo(() => {
    const types = new Set(filteredEvents.map(event => event.type));
    const totalSize = filteredEvents.reduce((sum, event) => sum + event.size, 0);

    // Calculate events in last minute
    const now = Date.now();
    const oneMinuteAgo = now - 60000;
    const recentEvents = filteredEvents.filter(e => e.timestamp > oneMinuteAgo);

    return {
      totalFiltered: filteredEvents.length,
      uniqueTypes: types.size,
      eventsPerMinute: recentEvents.length,
      averageSize: filteredEvents.length > 0 ? Math.round(totalSize / filteredEvents.length) : 0,
      totalSize
    };
  }, [filteredEvents]);

  // Event categories for filter dropdown
  const availableCategories = useMemo(() => {
    const categories = new Set(enhancedEvents.map(event => event.category));
    return Array.from(categories).sort();
  }, [enhancedEvents]);

  // Actions
  const setSearchTerm = (term: string) => {
    setFilter('searchTerm', term);
  };

  const setTypeFilter = (type: string) => {
    setFilter('typeFilter', type);
  };

  const toggleAutoScroll = () => {
    setSetting('autoScroll', !state.settings.autoScroll);
  };

  const togglePauseStream = () => {
    setSetting('pauseStream', !state.settings.pauseStream);
  };

  const exportEvents = () => {
    const eventsToExport = filteredEvents.length > 0 ? filteredEvents : enhancedEvents;
    const json = JSON.stringify(eventsToExport, null, 2);
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `events-${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return {
    // Data
    events: filteredEvents,
    allEvents: enhancedEvents,
    stats,
    availableCategories,

    // State
    searchTerm: state.filters.searchTerm,
    typeFilter: state.filters.typeFilter,
    autoScroll: state.settings.autoScroll,
    pauseStream: state.settings.pauseStream,

    // Actions
    setSearchTerm,
    setTypeFilter,
    toggleAutoScroll,
    togglePauseStream,
    exportEvents,

    // Utilities
    getEventCategory,
    formatTimestamp
  };
}