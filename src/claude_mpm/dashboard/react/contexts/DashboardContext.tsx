import React, { createContext, useContext, useReducer, ReactNode } from 'react';

// Types for events
export interface DashboardEvent {
  type: string;
  subtype?: string;
  timestamp: number;
  source: string;
  data: any;
  raw?: any;
}

// Types for connection state
export interface ConnectionState {
  isConnected: boolean;
  isConnecting: boolean;
  connectionCount: number;
  port: number;
}

// Dashboard state interface
export interface DashboardState {
  events: DashboardEvent[];
  connection: ConnectionState;
  stats: {
    totalEvents: number;
    eventsPerSecond: number;
    uniqueTypes: number;
  };
  filters: {
    searchTerm: string;
    typeFilter: string;
  };
  settings: {
    autoScroll: boolean;
    pauseStream: boolean;
    maxEvents: number;
  };
}

// Action types
type DashboardAction =
  | { type: 'ADD_EVENT'; payload: DashboardEvent }
  | { type: 'CLEAR_EVENTS' }
  | { type: 'SET_CONNECTION_STATE'; payload: Partial<ConnectionState> }
  | { type: 'UPDATE_STATS'; payload: Partial<DashboardState['stats']> }
  | { type: 'SET_FILTER'; payload: { key: keyof DashboardState['filters']; value: string } }
  | { type: 'SET_SETTING'; payload: { key: keyof DashboardState['settings']; value: any } };

// Initial state
const initialState: DashboardState = {
  events: [],
  connection: {
    isConnected: false,
    isConnecting: false,
    connectionCount: 0,
    port: 8765
  },
  stats: {
    totalEvents: 0,
    eventsPerSecond: 0,
    uniqueTypes: 0
  },
  filters: {
    searchTerm: '',
    typeFilter: ''
  },
  settings: {
    autoScroll: true,
    pauseStream: false,
    maxEvents: 1000
  }
};

// Reducer function
function dashboardReducer(state: DashboardState, action: DashboardAction): DashboardState {
  switch (action.type) {
    case 'ADD_EVENT':
      if (state.settings.pauseStream) return state;

      const newEvents = [action.payload, ...state.events];
      const trimmedEvents = newEvents.slice(0, state.settings.maxEvents);

      return {
        ...state,
        events: trimmedEvents,
        stats: {
          ...state.stats,
          totalEvents: state.stats.totalEvents + 1
        }
      };

    case 'CLEAR_EVENTS':
      return {
        ...state,
        events: [],
        stats: {
          ...state.stats,
          totalEvents: 0
        }
      };

    case 'SET_CONNECTION_STATE':
      return {
        ...state,
        connection: {
          ...state.connection,
          ...action.payload
        }
      };

    case 'UPDATE_STATS':
      return {
        ...state,
        stats: {
          ...state.stats,
          ...action.payload
        }
      };

    case 'SET_FILTER':
      return {
        ...state,
        filters: {
          ...state.filters,
          [action.payload.key]: action.payload.value
        }
      };

    case 'SET_SETTING':
      return {
        ...state,
        settings: {
          ...state.settings,
          [action.payload.key]: action.payload.value
        }
      };

    default:
      return state;
  }
}

// Context
interface DashboardContextType {
  state: DashboardState;
  dispatch: React.Dispatch<DashboardAction>;
  addEvent: (event: DashboardEvent) => void;
  clearEvents: () => void;
  setConnectionState: (connectionState: Partial<ConnectionState>) => void;
  updateStats: (stats: Partial<DashboardState['stats']>) => void;
  setFilter: (key: keyof DashboardState['filters'], value: string) => void;
  setSetting: (key: keyof DashboardState['settings'], value: any) => void;
}

const DashboardContext = createContext<DashboardContextType | null>(null);

// Provider component
interface DashboardProviderProps {
  children: ReactNode;
}

export function DashboardProvider({ children }: DashboardProviderProps) {
  const [state, dispatch] = useReducer(dashboardReducer, initialState);

  const addEvent = (event: DashboardEvent) => {
    dispatch({ type: 'ADD_EVENT', payload: event });
  };

  const clearEvents = () => {
    dispatch({ type: 'CLEAR_EVENTS' });
  };

  const setConnectionState = (connectionState: Partial<ConnectionState>) => {
    dispatch({ type: 'SET_CONNECTION_STATE', payload: connectionState });
  };

  const updateStats = (stats: Partial<DashboardState['stats']>) => {
    dispatch({ type: 'UPDATE_STATS', payload: stats });
  };

  const setFilter = (key: keyof DashboardState['filters'], value: string) => {
    dispatch({ type: 'SET_FILTER', payload: { key, value } });
  };

  const setSetting = (key: keyof DashboardState['settings'], value: any) => {
    dispatch({ type: 'SET_SETTING', payload: { key, value } });
  };

  const value: DashboardContextType = {
    state,
    dispatch,
    addEvent,
    clearEvents,
    setConnectionState,
    updateStats,
    setFilter,
    setSetting
  };

  return (
    <DashboardContext.Provider value={value}>
      {children}
    </DashboardContext.Provider>
  );
}

// Hook to use dashboard context
export function useDashboard() {
  const context = useContext(DashboardContext);
  if (!context) {
    throw new Error('useDashboard must be used within a DashboardProvider');
  }
  return context;
}