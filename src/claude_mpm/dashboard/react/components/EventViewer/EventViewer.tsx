import React, { useState, useEffect, useRef, useMemo } from 'react';
import { FixedSizeList as List } from 'react-window';
import { useEvents, EnhancedEvent } from '../../hooks/useEvents';
import { DataInspector } from '../DataInspector/DataInspector';
import styles from './EventViewer.module.css';

interface EventItemProps {
  index: number;
  style: React.CSSProperties;
  data: {
    events: EnhancedEvent[];
    expandedItems: Set<number>;
    onToggleExpand: (index: number) => void;
  };
}

function EventItem({ index, style, data }: EventItemProps) {
  const { events, expandedItems, onToggleExpand } = data;
  const event = events[index];
  const isExpanded = expandedItems.has(index);

  if (!event) return null;

  const handleClick = () => {
    onToggleExpand(index);
  };

  // Determine source indicator
  const sourceIndicator = event.source && event.source !== 'server'
    ? <span className={styles.sourceIndicator}>[{event.source}]</span>
    : null;

  return (
    <div style={style}>
      <div className={`${styles.eventItem} ${isExpanded ? styles.expanded : ''}`}>
        <div className={styles.eventHeader} onClick={handleClick}>
          <div className={styles.eventHeaderRow}>
            <span className={`${styles.eventType} ${styles[event.category]}`}>
              {event.displayType}
            </span>
            <span className={styles.eventTime}>{event.formattedTime}</span>
            {sourceIndicator}
          </div>
          <div className={styles.eventPreview}>
            {event.preview}
          </div>
        </div>

        {isExpanded && (
          <div className={styles.eventDetails}>
            <DataInspector
              data={event.raw || event.data}
              maxHeight="400px"
              searchable={true}
            />
          </div>
        )}
      </div>
    </div>
  );
}

export function EventViewer() {
  const { events, stats } = useEvents();
  const [expandedItems, setExpandedItems] = useState<Set<number>>(new Set());
  const listRef = useRef<List>(null);

  // Auto-scroll to top when new events arrive (if auto-scroll is enabled)
  const { autoScroll } = useEvents();
  useEffect(() => {
    if (autoScroll && events.length > 0 && listRef.current) {
      listRef.current.scrollToItem(0, 'start');
    }
  }, [events.length, autoScroll]);

  const toggleExpand = (index: number) => {
    setExpandedItems(prev => {
      const newSet = new Set(prev);
      if (newSet.has(index)) {
        newSet.delete(index);
      } else {
        newSet.add(index);
      }
      return newSet;
    });
  };

  // Calculate dynamic item height based on whether items are expanded
  const getItemSize = (index: number) => {
    const baseHeight = 80; // Base height for collapsed item
    const expandedHeight = 500; // Height for expanded item
    return expandedItems.has(index) ? expandedHeight : baseHeight;
  };

  // Memoize the data passed to the list
  const listData = useMemo(() => ({
    events,
    expandedItems,
    onToggleExpand: toggleExpand
  }), [events, expandedItems]);

  if (events.length === 0) {
    return (
      <div className={styles.eventsContainer}>
        <div className={styles.eventsHeader}>
          <div className={styles.eventsTitle}>Event Stream</div>
          <div className={styles.eventsInfo}>Showing 0 events</div>
        </div>
        <div className={styles.noEvents}>
          <h3>No Events Yet</h3>
          <p>Waiting for events from the server...</p>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.eventsContainer}>
      <div className={styles.eventsHeader}>
        <div className={styles.eventsTitle}>Event Stream</div>
        <div className={styles.eventsInfo}>
          Showing {stats.totalFiltered} events
          {stats.totalFiltered !== events.length && ` (${events.length} total)`}
        </div>
      </div>

      <div className={styles.eventsList}>
        <List
          ref={listRef}
          height={600}
          itemCount={events.length}
          itemSize={getItemSize}
          itemData={listData}
          overscanCount={5}
        >
          {EventItem}
        </List>
      </div>
    </div>
  );
}