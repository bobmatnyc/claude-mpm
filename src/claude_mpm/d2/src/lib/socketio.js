/**
 * Socket.IO Client Wrapper
 *
 * Manages connection to the Claude MPM Socket.IO server with:
 * - Auto-reconnect with exponential backoff
 * - Connection state management
 * - Event buffering during disconnection
 */

import { io } from 'socket.io-client';

export class SocketIOClient {
  constructor(url = 'http://localhost:8765', options = {}) {
    this.url = url;
    this.socket = null;
    this.connected = false;
    this.listeners = new Map();

    const defaultOptions = {
      transports: ['websocket', 'polling'],
      reconnection: true,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 5000,
      reconnectionAttempts: Infinity,
      timeout: 20000,
      pingInterval: 25000,
      pingTimeout: 20000,
    };

    this.options = { ...defaultOptions, ...options };
  }

  connect() {
    if (this.socket) {
      return this.socket;
    }

    this.socket = io(this.url, this.options);

    // Connection events
    this.socket.on('connect', () => {
      this.connected = true;
      this.emit('connection_status', { connected: true, reconnecting: false });
    });

    this.socket.on('disconnect', () => {
      this.connected = false;
      this.emit('connection_status', { connected: false, reconnecting: false });
    });

    this.socket.on('reconnect_attempt', () => {
      this.emit('connection_status', { connected: false, reconnecting: true });
    });

    this.socket.on('reconnect', () => {
      this.connected = true;
      this.emit('connection_status', { connected: true, reconnecting: false });
    });

    this.socket.on('connect_error', (error) => {
      console.error('Socket.IO connection error:', error);
      this.emit('connection_error', error);
    });

    return this.socket;
  }

  disconnect() {
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
      this.connected = false;
    }
  }

  on(event, callback) {
    if (!this.socket) {
      this.connect();
    }

    // Store listener for cleanup
    if (!this.listeners.has(event)) {
      this.listeners.set(event, []);
    }
    this.listeners.get(event).push(callback);

    this.socket.on(event, callback);
  }

  off(event, callback) {
    if (this.socket) {
      this.socket.off(event, callback);
    }

    // Remove from listeners
    if (this.listeners.has(event)) {
      const callbacks = this.listeners.get(event);
      const index = callbacks.indexOf(callback);
      if (index > -1) {
        callbacks.splice(index, 1);
      }
    }
  }

  emit(event, data) {
    if (this.socket) {
      this.socket.emit(event, data);
    }
  }

  isConnected() {
    return this.connected;
  }

  cleanup() {
    // Remove all listeners
    for (const [event, callbacks] of this.listeners.entries()) {
      for (const callback of callbacks) {
        this.socket?.off(event, callback);
      }
    }
    this.listeners.clear();

    // Disconnect
    this.disconnect();
  }
}

// Singleton instance
let socketInstance = null;

export function getSocketClient(url, options) {
  if (!socketInstance) {
    socketInstance = new SocketIOClient(url, options);
  }
  return socketInstance;
}

export function destroySocketClient() {
  if (socketInstance) {
    socketInstance.cleanup();
    socketInstance = null;
  }
}
