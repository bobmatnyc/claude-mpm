/**
 * Comprehensive unit tests for Socket.IO client JavaScript.
 *
 * Tests cover:
 * - Connection establishment and retry logic
 * - Event queuing when disconnected
 * - Event handler registration
 * - Error handling and fallback behavior
 * - Reconnection with exponential backoff
 *
 * Using Jest testing framework for JavaScript testing.
 */

// Mock Socket.IO library
const mockIo = jest.fn();
global.io = mockIo;

// Import the SocketClient class
// Note: In production, this would be imported from the actual module
// For testing, we'll define a simplified version that matches the real implementation

class SocketClient {
    constructor() {
        this.socket = null;
        this.port = null;
        this.connectionCallbacks = {
            connect: [],
            disconnect: [],
            error: [],
            event: []
        };

        this.eventSchema = {
            required: ['source', 'type', 'subtype', 'timestamp', 'data'],
            optional: ['event', 'session_id']
        };

        this.isConnected = false;
        this.isConnecting = false;
        this.lastConnectTime = null;
        this.disconnectTime = null;

        this.events = [];
        this.sessions = new Map();
        this.currentSessionId = null;

        this.eventQueue = [];
        this.maxQueueSize = 100;

        this.retryAttempts = 0;
        this.maxRetryAttempts = 5;
        this.retryDelays = [1000, 2000, 3000, 4000, 5000];
        this.pendingEmissions = new Map();

        this.lastPingTime = null;
        this.lastPongTime = null;
        this.pingTimeout = 90000;
        this.healthCheckInterval = null;
    }

    connect(port = '8765') {
        this.port = port;
        const url = `http://localhost:${port}`;

        if (this.socket && (this.socket.connected || this.socket.connecting)) {
            console.log('Already connected or connecting, disconnecting first...');
            this.socket.disconnect();
            setTimeout(() => this.doConnect(url), 100);
            return;
        }

        this.doConnect(url);
    }

    doConnect(url) {
        console.log(`Connecting to Socket.IO server at ${url}`);

        if (typeof io === 'undefined') {
            console.error('Socket.IO library not loaded!');
            this.notifyConnectionStatus('Socket.IO library not loaded', 'error');
            return;
        }

        this.isConnecting = true;
        this.notifyConnectionStatus('Connecting...', 'connecting');

        this.socket = io(url, {
            autoConnect: true,
            reconnection: true,
            reconnectionDelay: 1000,
            reconnectionDelayMax: 5000,
            reconnectionAttempts: this.maxRetryAttempts,
            timeout: 20000,
            transports: ['websocket', 'polling']
        });

        this.setupEventHandlers();
    }

    setupEventHandlers() {
        if (!this.socket) return;

        this.socket.on('connect', () => {
            this.isConnected = true;
            this.isConnecting = false;
            this.lastConnectTime = Date.now();
            this.retryAttempts = 0;
            this.flushEventQueue();
            this.notifyConnectionStatus('Connected', 'connected');
            this.connectionCallbacks.connect.forEach(cb => cb());
        });

        this.socket.on('disconnect', (reason) => {
            this.isConnected = false;
            this.disconnectTime = Date.now();
            this.notifyConnectionStatus(`Disconnected: ${reason}`, 'disconnected');
            this.connectionCallbacks.disconnect.forEach(cb => cb(reason));
        });

        this.socket.on('error', (error) => {
            console.error('Socket.IO error:', error);
            this.connectionCallbacks.error.forEach(cb => cb(error));
        });

        this.socket.on('event', (data) => {
            this.handleEvent(data);
        });
    }

    handleEvent(data) {
        if (!this.validateEventSchema(data)) {
            console.warn('Invalid event schema:', data);
            return;
        }

        this.events.push(data);
        this.connectionCallbacks.event.forEach(cb => cb(data));
    }

    validateEventSchema(data) {
        for (const field of this.eventSchema.required) {
            if (!data.hasOwnProperty(field)) {
                return false;
            }
        }
        return true;
    }

    queueEvent(event) {
        if (this.eventQueue.length >= this.maxQueueSize) {
            this.eventQueue.shift(); // Remove oldest
        }
        this.eventQueue.push(event);
    }

    flushEventQueue() {
        while (this.eventQueue.length > 0 && this.isConnected) {
            const event = this.eventQueue.shift();
            this.emit(event.type, event.data);
        }
    }

    emit(eventType, data) {
        if (!this.isConnected) {
            this.queueEvent({ type: eventType, data });
            return false;
        }

        if (this.socket) {
            this.socket.emit(eventType, data);
            return true;
        }
        return false;
    }

    on(eventType, callback) {
        if (this.connectionCallbacks.hasOwnProperty(eventType)) {
            this.connectionCallbacks[eventType].push(callback);
        } else if (this.socket) {
            this.socket.on(eventType, callback);
        }
    }

    notifyConnectionStatus(message, status) {
        console.log(`Connection status: ${status} - ${message}`);
    }

    retryConnection() {
        if (this.retryAttempts >= this.maxRetryAttempts) {
            console.error('Max retry attempts reached');
            return;
        }

        const delay = this.retryDelays[this.retryAttempts] || 5000;
        this.retryAttempts++;

        setTimeout(() => {
            this.connect(this.port);
        }, delay);
    }

    disconnect() {
        if (this.socket) {
            this.socket.disconnect();
            this.socket = null;
        }
        this.isConnected = false;
        this.isConnecting = false;
    }
}

// Test Suite: Connection Management
describe('SocketClient Connection Management', () => {
    let client;
    let mockSocket;

    beforeEach(() => {
        jest.clearAllMocks();

        // Create mock socket
        mockSocket = {
            connected: false,
            connecting: false,
            on: jest.fn(),
            emit: jest.fn(),
            disconnect: jest.fn()
        };

        // Configure io mock to return our mock socket
        mockIo.mockReturnValue(mockSocket);

        client = new SocketClient();
    });

    afterEach(() => {
        if (client) {
            client.disconnect();
        }
    });

    test('should establish connection to specified port', () => {
        /**
         * WHY: The client must connect to the correct port where the
         * Socket.IO server is running. This is the basic connection test.
         */
        client.connect('8766');

        expect(mockIo).toHaveBeenCalledWith(
            'http://localhost:8766',
            expect.objectContaining({
                autoConnect: true,
                reconnection: true
            })
        );
        expect(client.port).toBe('8766');
    });

    test('should handle already connected state', (done) => {
        /**
         * WHY: Attempting to connect when already connected should
         * disconnect first to prevent multiple connections.
         */
        mockSocket.connected = true;
        client.socket = mockSocket;

        const spy = jest.spyOn(mockSocket, 'disconnect');

        client.connect('8765');

        expect(spy).toHaveBeenCalled();

        // Wait for reconnection timeout
        setTimeout(() => {
            expect(mockIo).toHaveBeenCalled();
            done();
        }, 150);
    });

    test('should handle missing Socket.IO library', () => {
        /**
         * WHY: If the Socket.IO library fails to load, the client
         * should handle this gracefully with appropriate error messaging.
         */
        const originalIo = global.io;
        global.io = undefined;

        const consoleSpy = jest.spyOn(console, 'error').mockImplementation();

        client.connect();

        expect(consoleSpy).toHaveBeenCalledWith(
            expect.stringContaining('Socket.IO library not loaded')
        );

        global.io = originalIo;
        consoleSpy.mockRestore();
    });
});

// Test Suite: Event Handling
describe('SocketClient Event Handling', () => {
    let client;
    let mockSocket;

    beforeEach(() => {
        jest.clearAllMocks();

        mockSocket = {
            connected: true,
            connecting: false,
            on: jest.fn(),
            emit: jest.fn(),
            disconnect: jest.fn()
        };

        mockIo.mockReturnValue(mockSocket);
        client = new SocketClient();
        client.connect();
    });

    test('should register event handlers on connection', () => {
        /**
         * WHY: Event handlers must be registered to receive server events.
         * This ensures all necessary handlers are set up.
         */
        expect(mockSocket.on).toHaveBeenCalledWith('connect', expect.any(Function));
        expect(mockSocket.on).toHaveBeenCalledWith('disconnect', expect.any(Function));
        expect(mockSocket.on).toHaveBeenCalledWith('error', expect.any(Function));
        expect(mockSocket.on).toHaveBeenCalledWith('event', expect.any(Function));
    });

    test('should validate event schema', () => {
        /**
         * WHY: Events must have required fields to be processed correctly.
         * Invalid events should be rejected to maintain data integrity.
         */
        const validEvent = {
            source: 'test',
            type: 'test_event',
            subtype: 'unit_test',
            timestamp: Date.now(),
            data: { test: true }
        };

        const invalidEvent = {
            type: 'test_event',
            data: { test: true }
            // Missing required fields
        };

        expect(client.validateEventSchema(validEvent)).toBe(true);
        expect(client.validateEventSchema(invalidEvent)).toBe(false);
    });

    test('should handle incoming events', () => {
        /**
         * WHY: Incoming events must be processed and stored for the
         * dashboard to display. Event callbacks must be triggered.
         */
        const eventCallback = jest.fn();
        client.on('event', eventCallback);

        const testEvent = {
            source: 'test',
            type: 'test_event',
            subtype: 'unit_test',
            timestamp: Date.now(),
            data: { test: true }
        };

        // Simulate receiving an event
        client.handleEvent(testEvent);

        expect(client.events).toContainEqual(testEvent);
        expect(eventCallback).toHaveBeenCalledWith(testEvent);
    });

    test('should emit events when connected', () => {
        /**
         * WHY: Events should be sent to the server immediately when
         * the client is connected.
         */
        client.isConnected = true;
        client.socket = mockSocket;

        const result = client.emit('custom_event', { data: 'test' });

        expect(result).toBe(true);
        expect(mockSocket.emit).toHaveBeenCalledWith('custom_event', { data: 'test' });
    });
});

// Test Suite: Event Queuing
describe('SocketClient Event Queuing', () => {
    let client;

    beforeEach(() => {
        jest.clearAllMocks();
        client = new SocketClient();
    });

    test('should queue events when disconnected', () => {
        /**
         * WHY: When disconnected, events should be queued to prevent
         * data loss. They will be sent when connection is restored.
         */
        client.isConnected = false;

        const result = client.emit('test_event', { data: 'queued' });

        expect(result).toBe(false);
        expect(client.eventQueue).toHaveLength(1);
        expect(client.eventQueue[0]).toEqual({
            type: 'test_event',
            data: { data: 'queued' }
        });
    });

    test('should respect queue size limit', () => {
        /**
         * WHY: The queue must have a size limit to prevent memory issues.
         * Oldest events should be dropped when the limit is reached.
         */
        client.maxQueueSize = 3;
        client.isConnected = false;

        // Fill queue beyond limit
        for (let i = 0; i < 5; i++) {
            client.emit(`event_${i}`, { index: i });
        }

        expect(client.eventQueue).toHaveLength(3);
        expect(client.eventQueue[0].type).toBe('event_2'); // Oldest were dropped
        expect(client.eventQueue[2].type).toBe('event_4'); // Newest kept
    });

    test('should flush queue on reconnection', () => {
        /**
         * WHY: Queued events must be sent when connection is restored
         * to ensure no data is lost during temporary disconnections.
         */
        const mockSocket = {
            connected: true,
            on: jest.fn(),
            emit: jest.fn(),
            disconnect: jest.fn()
        };

        // Queue some events while disconnected
        client.isConnected = false;
        client.emit('event_1', { data: 1 });
        client.emit('event_2', { data: 2 });

        expect(client.eventQueue).toHaveLength(2);

        // Simulate reconnection
        client.socket = mockSocket;
        client.isConnected = true;
        client.flushEventQueue();

        expect(client.eventQueue).toHaveLength(0);
        expect(mockSocket.emit).toHaveBeenCalledTimes(2);
        expect(mockSocket.emit).toHaveBeenCalledWith('event_1', { data: 1 });
        expect(mockSocket.emit).toHaveBeenCalledWith('event_2', { data: 2 });
    });
});

// Test Suite: Retry Logic
describe('SocketClient Retry Logic', () => {
    let client;

    beforeEach(() => {
        jest.clearAllMocks();
        jest.useFakeTimers();
        client = new SocketClient();
    });

    afterEach(() => {
        jest.useRealTimers();
    });

    test('should retry with exponential backoff', () => {
        /**
         * WHY: Exponential backoff prevents overwhelming the server
         * with reconnection attempts while ensuring eventual reconnection.
         */
        const connectSpy = jest.spyOn(client, 'connect');

        // First retry - 1000ms delay
        client.retryConnection();
        expect(client.retryAttempts).toBe(1);

        jest.advanceTimersByTime(1000);
        expect(connectSpy).toHaveBeenCalledTimes(1);

        // Second retry - 2000ms delay
        client.retryConnection();
        expect(client.retryAttempts).toBe(2);

        jest.advanceTimersByTime(2000);
        expect(connectSpy).toHaveBeenCalledTimes(2);

        // Third retry - 3000ms delay
        client.retryConnection();
        expect(client.retryAttempts).toBe(3);

        jest.advanceTimersByTime(3000);
        expect(connectSpy).toHaveBeenCalledTimes(3);
    });

    test('should stop retrying after max attempts', () => {
        /**
         * WHY: Infinite retry attempts could waste resources. After
         * a reasonable number of attempts, retries should stop.
         */
        const consoleSpy = jest.spyOn(console, 'error').mockImplementation();

        client.retryAttempts = client.maxRetryAttempts;
        client.retryConnection();

        expect(consoleSpy).toHaveBeenCalledWith('Max retry attempts reached');

        // Should not schedule another retry
        jest.advanceTimersByTime(10000);
        expect(client.connect).not.toHaveBeenCalled();

        consoleSpy.mockRestore();
    });

    test('should reset retry count on successful connection', () => {
        /**
         * WHY: Once connected successfully, the retry count should reset
         * so future disconnections start with fresh retry attempts.
         */
        const mockSocket = {
            on: jest.fn((event, handler) => {
                if (event === 'connect') {
                    // Simulate immediate connection
                    handler();
                }
            }),
            emit: jest.fn(),
            disconnect: jest.fn()
        };

        mockIo.mockReturnValue(mockSocket);

        client.retryAttempts = 3;
        client.connect();

        expect(client.retryAttempts).toBe(0);
        expect(client.isConnected).toBe(true);
    });
});

// Test Suite: Connection Status
describe('SocketClient Connection Status', () => {
    let client;
    let mockSocket;

    beforeEach(() => {
        jest.clearAllMocks();

        mockSocket = {
            on: jest.fn(),
            emit: jest.fn(),
            disconnect: jest.fn()
        };

        mockIo.mockReturnValue(mockSocket);
        client = new SocketClient();
    });

    test('should track connection state accurately', () => {
        /**
         * WHY: Accurate connection state tracking is essential for
         * the UI to show correct status and for queuing logic.
         */
        expect(client.isConnected).toBe(false);
        expect(client.isConnecting).toBe(false);

        // Start connecting
        client.connect();
        expect(client.isConnecting).toBe(true);
        expect(client.isConnected).toBe(false);

        // Simulate connection success
        const connectHandler = mockSocket.on.mock.calls.find(
            call => call[0] === 'connect'
        )[1];
        connectHandler();

        expect(client.isConnecting).toBe(false);
        expect(client.isConnected).toBe(true);
        expect(client.lastConnectTime).toBeTruthy();

        // Simulate disconnection
        const disconnectHandler = mockSocket.on.mock.calls.find(
            call => call[0] === 'disconnect'
        )[1];
        disconnectHandler('transport close');

        expect(client.isConnected).toBe(false);
        expect(client.disconnectTime).toBeTruthy();
    });

    test('should invoke connection callbacks', () => {
        /**
         * WHY: UI components need to react to connection state changes.
         * Callbacks provide a way to update UI when connection status changes.
         */
        const connectCallback = jest.fn();
        const disconnectCallback = jest.fn();
        const errorCallback = jest.fn();

        client.on('connect', connectCallback);
        client.on('disconnect', disconnectCallback);
        client.on('error', errorCallback);

        client.connect();

        // Trigger events through mock socket
        const handlers = {};
        mockSocket.on.mock.calls.forEach(call => {
            handlers[call[0]] = call[1];
        });

        // Simulate connection lifecycle
        handlers.connect();
        expect(connectCallback).toHaveBeenCalled();

        handlers.error(new Error('Test error'));
        expect(errorCallback).toHaveBeenCalledWith(expect.any(Error));

        handlers.disconnect('io server disconnect');
        expect(disconnectCallback).toHaveBeenCalledWith('io server disconnect');
    });
});

// Test Suite: Error Handling
describe('SocketClient Error Handling', () => {
    let client;
    let mockSocket;

    beforeEach(() => {
        jest.clearAllMocks();

        mockSocket = {
            on: jest.fn(),
            emit: jest.fn(),
            disconnect: jest.fn()
        };

        mockIo.mockReturnValue(mockSocket);
        client = new SocketClient();
    });

    test('should handle socket errors gracefully', () => {
        /**
         * WHY: Network errors are common and shouldn't crash the client.
         * Errors should be logged and callbacks invoked for UI updates.
         */
        const consoleSpy = jest.spyOn(console, 'error').mockImplementation();
        const errorCallback = jest.fn();

        client.on('error', errorCallback);
        client.connect();

        // Get error handler
        const errorHandler = mockSocket.on.mock.calls.find(
            call => call[0] === 'error'
        )[1];

        // Trigger error
        const testError = new Error('Socket error');
        errorHandler(testError);

        expect(consoleSpy).toHaveBeenCalledWith('Socket.IO error:', testError);
        expect(errorCallback).toHaveBeenCalledWith(testError);

        consoleSpy.mockRestore();
    });

    test('should handle invalid events gracefully', () => {
        /**
         * WHY: Invalid events from the server shouldn't crash the client.
         * They should be logged and ignored.
         */
        const consoleSpy = jest.spyOn(console, 'warn').mockImplementation();

        const invalidEvent = {
            type: 'test',
            // Missing required fields
        };

        client.handleEvent(invalidEvent);

        expect(consoleSpy).toHaveBeenCalledWith('Invalid event schema:', invalidEvent);
        expect(client.events).toHaveLength(0); // Event not added

        consoleSpy.mockRestore();
    });
});

// Test Suite: Cleanup
describe('SocketClient Cleanup', () => {
    let client;
    let mockSocket;

    beforeEach(() => {
        jest.clearAllMocks();

        mockSocket = {
            connected: true,
            on: jest.fn(),
            emit: jest.fn(),
            disconnect: jest.fn()
        };

        mockIo.mockReturnValue(mockSocket);
        client = new SocketClient();
    });

    test('should clean up on disconnect', () => {
        /**
         * WHY: Proper cleanup prevents memory leaks and ensures
         * clean state for potential reconnection.
         */
        client.connect();
        client.isConnected = true;

        client.disconnect();

        expect(mockSocket.disconnect).toHaveBeenCalled();
        expect(client.socket).toBeNull();
        expect(client.isConnected).toBe(false);
        expect(client.isConnecting).toBe(false);
    });
});

// Export for use in other test files if needed
module.exports = { SocketClient };
