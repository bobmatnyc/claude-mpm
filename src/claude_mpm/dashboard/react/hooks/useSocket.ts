import { useEffect, useRef } from 'react';
import { useDashboard } from '../contexts/DashboardContext';
import { DashboardEvent } from '../contexts/DashboardContext';

// Extend window interface to include our globals
declare global {
  interface Window {
    io?: any;
    socket?: any;
    SocketManager?: any;
    socketClient?: any;
  }
}

/**
 * Hook to manage Socket.IO connection and integrate with React state
 * Preserves compatibility with existing SocketManager infrastructure
 */
export function useSocket() {
  const { state, addEvent, setConnectionState, updateStats } = useDashboard();
  const socketRef = useRef<any>(null);
  const eventRateHistoryRef = useRef<Array<{ time: number; count: number }>>([]);
  const lastEventCountRef = useRef(0);

  useEffect(() => {
    // Initialize Socket.IO connection - throws errors instead of graceful fallback
    const initializeSocket = () => {
      if (!window.io) {
        const error = new Error('WebSocket connection required but failed: Socket.IO dependency not loaded');
        console.error(error.message);
        throw error;
      }

      // Create direct socket connection similar to existing events.html
      const socket = window.io('http://localhost:8765', {
        transports: ['polling', 'websocket'],
        reconnection: true,
        reconnectionDelay: 1000,
        reconnectionDelayMax: 5000,
        reconnectionAttempts: Infinity
      });

      socketRef.current = socket;

      // Connection handlers
      socket.on('connect', () => {
        console.log('React Socket: Connected to Socket.IO server:', socket.id);
        setConnectionState({
          isConnected: true,
          isConnecting: false,
          connectionCount: 1
        });

        // Request event history
        socket.emit('get_history', { limit: 100 });
      });

      socket.on('disconnect', () => {
        console.log('React Socket: Disconnected from Socket.IO server');
        setConnectionState({
          isConnected: false,
          isConnecting: false,
          connectionCount: 0
        });
      });

      socket.on('connect_error', (error: any) => {
        const connectionError = new Error(`WebSocket connection required but failed: ${error.message || 'Unknown connection error'}`);
        console.error('React Socket: Connection error:', connectionError.message);
        setConnectionState({
          isConnected: false,
          isConnecting: false,
          connectionCount: 0
        });
        // Throw error after updating state
        throw connectionError;
      });

      // Primary event handler - matches existing events.html pattern
      socket.on('claude_event', (data: any) => {
        console.log('React Socket: Received claude_event:', data);

        const event: DashboardEvent = {
          type: data.type || data.event_type || 'unknown',
          subtype: data.subtype || data.event_subtype || '',
          timestamp: data.timestamp || Date.now(),
          source: data.source || 'server',
          data: data.data || data,
          raw: data
        };

        if (!state.settings.pauseStream) {
          addEvent(event);
        }
      });

      // History response handler
      socket.on('history', (data: any) => {
        console.log('React Socket: Received history:', data);
        if (data && data.events && Array.isArray(data.events)) {
          data.events.forEach((evt: any) => {
            const event: DashboardEvent = {
              type: evt.type || evt.event_type || 'historical',
              subtype: evt.subtype || evt.event_subtype || '',
              timestamp: evt.timestamp || Date.now(),
              data: evt.data || evt,
              source: 'history'
            };
            addEvent(event);
          });
        }
      });

      // Specific event handlers - matches existing pattern
      const specificEvents = [
        'heartbeat', 'system.status',
        'session.started', 'session.ended',
        'claude.request', 'claude.response',
        'agent.loaded', 'agent.executed',
        'todo.updated', 'memory.operation',
        'log.entry', 'test_event'
      ];

      specificEvents.forEach(eventType => {
        socket.on(eventType, (data: any) => {
          console.log(`React Socket: Received specific event ${eventType}:`, data);
          const event: DashboardEvent = {
            type: eventType,
            timestamp: data.timestamp || Date.now(),
            data: data,
            source: 'specific'
          };
          if (!state.settings.pauseStream) {
            addEvent(event);
          }
        });
      });
    };

    // Check if Socket.IO is available - strict mode with error throwing
    if (typeof window !== 'undefined') {
      if (window.io) {
        try {
          initializeSocket();
        } catch (error) {
          console.error('Socket initialization failed:', error);
          throw error;
        }
      } else {
        // Wait for Socket.IO to load with timeout
        let attempts = 0;
        const maxAttempts = 50; // 5 seconds with 100ms intervals

        const checkInterval = setInterval(() => {
          attempts++;
          if (window.io) {
            clearInterval(checkInterval);
            try {
              initializeSocket();
            } catch (error) {
              console.error('Delayed socket initialization failed:', error);
              throw error;
            }
          } else if (attempts >= maxAttempts) {
            clearInterval(checkInterval);
            const timeoutError = new Error('WebSocket connection required but failed: Timeout waiting for Socket.IO to load (5 seconds)');
            console.error(timeoutError.message);
            throw timeoutError;
          }
        }, 100);
      }
    } else {
      const windowError = new Error('WebSocket connection required but failed: Window object not available');
      console.error(windowError.message);
      throw windowError;
    }

    return () => {
      if (socketRef.current) {
        socketRef.current.disconnect();
        socketRef.current = null;
      }
    };
  }, []); // Empty dependency array - only run once on mount

  // Calculate event rate
  useEffect(() => {
    const calculateEventRate = () => {
      const now = Date.now();
      const currentCount = state.stats.totalEvents;
      const newEvents = currentCount - lastEventCountRef.current;

      eventRateHistoryRef.current.push({ time: now, count: newEvents });
      lastEventCountRef.current = currentCount;

      // Keep only last 10 seconds
      eventRateHistoryRef.current = eventRateHistoryRef.current.filter(h => h.time > now - 10000);

      // Calculate average rate
      const totalNewEvents = eventRateHistoryRef.current.reduce((sum, h) => sum + h.count, 0);
      const timeSpan = eventRateHistoryRef.current.length > 0 ?
        (now - eventRateHistoryRef.current[0].time) / 1000 : 1;

      const rate = Math.round(totalNewEvents / Math.max(timeSpan, 1));

      updateStats({ eventsPerSecond: rate });
    };

    const interval = setInterval(calculateEventRate, 1000);
    return () => clearInterval(interval);
  }, [state.stats.totalEvents, updateStats]);

  // Calculate unique types
  useEffect(() => {
    const types = new Set(state.events.map(event => event.type));
    updateStats({ uniqueTypes: types.size });
  }, [state.events, updateStats]);

  return {
    socket: socketRef.current,
    isConnected: state.connection.isConnected,
    isConnecting: state.connection.isConnecting,
    connectionCount: state.connection.connectionCount
  };
}