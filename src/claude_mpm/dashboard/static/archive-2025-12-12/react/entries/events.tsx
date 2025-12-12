import React from 'react';
import { createRoot } from 'react-dom/client';
import { DashboardProvider } from '../contexts/DashboardContext';
import { EventViewer } from '../components/EventViewer/EventViewer';
import { ConnectionStatus } from '../components/shared/ConnectionStatus';
import { FilterBar } from '../components/shared/FilterBar';
import { useSocket } from '../hooks/useSocket';
import { useDashboard } from '../contexts/DashboardContext';
import { ErrorBoundary } from '../components/ErrorBoundary';

// Extend Window interface for TypeScript
declare global {
  interface Window {
    ClaudeMPMReact?: {
      initializeReactEvents?: () => boolean;
    };
    initializeReactEvents?: () => boolean;
  }
}

function EventsPageApp() {
  // Initialize socket connection
  useSocket();

  const { state } = useDashboard();

  return (
    <div className="react-events-container">
      {/* Statistics Panel */}
      <div className="stats-panel">
        <div className="stat-card">
          <div className="stat-icon">📊</div>
          <div className="stat-info">
            <div className="stat-label">Total Events</div>
            <div className="stat-value">{state.stats.totalEvents}</div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon">⚡</div>
          <div className="stat-info">
            <div className="stat-label">Events/Sec</div>
            <div className="stat-value">{state.stats.eventsPerSecond}</div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon">🔗</div>
          <div className="stat-info">
            <div className="stat-label">Active Connections</div>
            <div className="stat-value">{state.connection.connectionCount}</div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon">📝</div>
          <div className="stat-info">
            <div className="stat-label">Event Types</div>
            <div className="stat-value">{state.stats.uniqueTypes}</div>
          </div>
        </div>
      </div>

      {/* Filter Controls */}
      <FilterBar />

      {/* Event Viewer */}
      <EventViewer />
    </div>
  );
}

function EventsPage() {
  return (
    <ErrorBoundary>
      <DashboardProvider>
        <EventsPageApp />
      </DashboardProvider>
    </ErrorBoundary>
  );
}

// Initialize React app - throws errors instead of graceful fallback
function initializeReactEvents() {
  console.log('Initializing React Events - strict mode (no fallback)');

  // Check for required DOM element
  const container = document.getElementById('react-events-root');
  if (!container) {
    const error = new Error('React initialization failed: Required DOM element \'#react-events-root\' not found');
    console.error(error.message);
    throw error;
  }

  // Check for Socket.IO availability
  if (typeof window !== 'undefined' && typeof (window as any).io === 'undefined') {
    const error = new Error('React initialization failed: Socket.IO dependency not loaded');
    console.error(error.message);
    throw error;
  }

  try {
    const root = createRoot(container);
    root.render(<EventsPage />);
    console.log('React EventViewer initialized successfully');
    return true;
  } catch (error) {
    const initError = new Error(`React initialization failed: Failed to render components - ${error instanceof Error ? error.message : String(error)}`);
    console.error(initError.message);
    throw initError;
  }
}

// Export for module loading
export { initializeReactEvents };

// Expose to window for global access
if (typeof window !== 'undefined') {
  // Create namespace if it doesn't exist
  window.ClaudeMPMReact = window.ClaudeMPMReact || {};
  window.ClaudeMPMReact.initializeReactEvents = initializeReactEvents;

  // Also expose directly on window for easier access
  window.initializeReactEvents = initializeReactEvents;

  console.log('React events initialization function exposed on window');
}

// Auto-initialize if this script is loaded directly - throws errors on failure
if (typeof window !== 'undefined' && document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    // Always attempt initialization - let it throw if it fails
    try {
      initializeReactEvents();
    } catch (error) {
      // Display error to user instead of silent failure
      const container = document.getElementById('react-events-root');
      if (container) {
        container.innerHTML = `
          <div style="padding: 20px; background: rgba(248, 113, 113, 0.1); border: 1px solid #f87171; border-radius: 8px; color: #f87171; font-family: monospace;">
            <h2>React Initialization Error</h2>
            <p><strong>Error:</strong> ${error instanceof Error ? error.message : String(error)}</p>
            <p>The React-based dashboard failed to load. Check the console for detailed error information.</p>
          </div>
        `;
      }
      throw error;
    }
  });
} else if (typeof window !== 'undefined') {
  // Immediate initialization attempt - let it throw if it fails
  try {
    initializeReactEvents();
  } catch (error) {
    // Display error to user instead of silent failure
    const container = document.getElementById('react-events-root');
    if (container) {
      container.innerHTML = `
        <div style="padding: 20px; background: rgba(248, 113, 113, 0.1); border: 1px solid #f87171; border-radius: 8px; color: #f87171; font-family: monospace;">
          <h2>React Initialization Error</h2>
          <p><strong>Error:</strong> ${error instanceof Error ? error.message : String(error)}</p>
          <p>The React-based dashboard failed to load. Check the console for detailed error information.</p>
        </div>
      `;
    }
    throw error;
  }
}