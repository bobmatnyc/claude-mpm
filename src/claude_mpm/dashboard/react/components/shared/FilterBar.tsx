import React from 'react';
import { useEvents } from '../../hooks/useEvents';
import { useDashboard } from '../../contexts/DashboardContext';
import styles from './FilterBar.module.css';

export function FilterBar() {
  const {
    searchTerm,
    typeFilter,
    autoScroll,
    pauseStream,
    availableCategories,
    setSearchTerm,
    setTypeFilter,
    toggleAutoScroll,
    togglePauseStream,
    exportEvents
  } = useEvents();

  const { clearEvents } = useDashboard();

  const handleClearEvents = () => {
    if (confirm('Clear all events?')) {
      clearEvents();
    }
  };

  return (
    <div className={styles.controlsPanel}>
      <div className={styles.controlGroup}>
        <input
          type="text"
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          placeholder="Search events..."
          className={styles.searchBox}
        />
      </div>

      <div className={styles.controlGroup}>
        <label className={styles.controlLabel}>Type:</label>
        <select
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
          className={styles.filterSelect}
        >
          <option value="">All Types</option>
          {availableCategories.map(category => (
            <option key={category} value={category}>
              {category.charAt(0).toUpperCase() + category.slice(1)}
            </option>
          ))}
        </select>
      </div>

      <label className={styles.checkboxLabel}>
        <input
          type="checkbox"
          checked={autoScroll}
          onChange={toggleAutoScroll}
        />
        Auto-scroll
      </label>

      <label className={styles.checkboxLabel}>
        <input
          type="checkbox"
          checked={pauseStream}
          onChange={togglePauseStream}
        />
        Pause
      </label>

      <button
        className={`${styles.btn} ${styles.secondary}`}
        onClick={exportEvents}
      >
        Export JSON
      </button>

      <button
        className={`${styles.btn} ${styles.danger}`}
        onClick={handleClearEvents}
      >
        Clear All
      </button>
    </div>
  );
}