import React from 'react';
import { useDashboard } from '../../contexts/DashboardContext';
import styles from './ConnectionStatus.module.css';

export function ConnectionStatus() {
  const { state } = useDashboard();
  const { connection, stats } = state;

  return (
    <div className={styles.statusBar}>
      <div className={styles.statusIndicator}>
        <span
          className={`${styles.statusDot} ${connection.isConnected ? styles.connected : styles.disconnected}`}
        />
        <span>
          {connection.isConnected ? 'Connected' : connection.isConnecting ? 'Connecting...' : 'Disconnected'}
        </span>
      </div>

      <div className={styles.statusIndicator}>
        <span>📊</span>
        <span>{stats.totalEvents} events</span>
      </div>

      <div className={styles.statusIndicator}>
        <span>⚡</span>
        <span>{stats.eventsPerSecond}/s</span>
      </div>

      <div className={styles.statusIndicator}>
        <span>🔌</span>
        <span>{connection.connectionCount} active</span>
      </div>
    </div>
  );
}