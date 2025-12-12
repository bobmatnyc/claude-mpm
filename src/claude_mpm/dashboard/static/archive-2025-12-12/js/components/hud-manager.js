/**
 * HUD Manager Module
 *
 * Manages HUD (Heads-Up Display) visualization mode, including toggling between
 * normal and HUD views, processing events for visualization, and coordinating
 * with the HUD visualizer component.
 *
 * WHY: Extracted from main dashboard to isolate HUD-specific functionality
 * and provide better separation between standard event viewing and advanced
 * HUD visualization modes. This improves maintainability of complex visualization logic.
 *
 * DESIGN DECISION: Acts as a coordinator between the dashboard state and the
 * HUD visualizer component, managing mode switching and event processing
 * while maintaining clean separation from core dashboard functionality.
 */
class HUDManager {
    constructor(eventViewer, sessionManager) {
        this.eventViewer = eventViewer;
        this.sessionManager = sessionManager;
        this.hudVisualizer = null;
        this.hudMode = false;
        this.isInitialized = false;

        this.initializeHUDVisualizer();
        this.setupEventHandlers();

        // Initial button state update with a small delay to ensure all components are ready
        setTimeout(() => {
            this.updateHUDButtonState();
        }, 100);

        console.log('HUD manager initialized');
    }

    /**
     * Initialize the HUD visualizer component
     */
    initializeHUDVisualizer() {
        try {
            this.hudVisualizer = new HUDVisualizer();
            window.hudVisualizer = this.hudVisualizer; // Backward compatibility

            // Initialize HUD visualizer
            this.hudVisualizer.initialize();
            this.isInitialized = true;

            console.log('HUD visualizer initialized successfully');
        } catch (error) {
            console.error('Failed to initialize HUD visualizer:', error);
            this.isInitialized = false;
        }
    }

    /**
     * Set up event handlers for HUD functionality
     */
    setupEventHandlers() {
        console.log('[HUD-DEBUG] Setting up HUD event handlers');

        // HUD toggle button
        const hudToggleBtn = document.getElementById('hud-toggle-btn');
        if (hudToggleBtn) {
            console.log('[HUD-DEBUG] HUD toggle button found, adding click listener');
            hudToggleBtn.addEventListener('click', () => {
                console.log('[HUD-DEBUG] HUD toggle button clicked');
                this.toggleHUD();
            });
        } else {
            console.warn('[HUD-DEBUG] HUD toggle button not found during setup');
            // Check if the DOM is ready
            if (document.readyState === 'loading') {
                console.log('[HUD-DEBUG] DOM still loading, will retry after DOMContentLoaded');
                document.addEventListener('DOMContentLoaded', () => {
                    console.log('[HUD-DEBUG] DOM loaded, retrying HUD button setup');
                    this.setupEventHandlers();
                });
                return;
            }
        }

        // Listen for session changes to update HUD button state
        console.log('[HUD-DEBUG] Adding sessionChanged event listener');
        document.addEventListener('sessionChanged', (e) => {
            console.log('[HUD-DEBUG] sessionChanged event received:', e.detail);
            this.updateHUDButtonState();
        });

        // Also listen for sessionFilterChanged for backward compatibility
        console.log('[HUD-DEBUG] Adding sessionFilterChanged event listener');
        document.addEventListener('sessionFilterChanged', (e) => {
            console.log('[HUD-DEBUG] sessionFilterChanged event received:', e.detail);
            this.updateHUDButtonState();
        });
    }

    /**
     * Toggle HUD mode on/off
     */
    toggleHUD() {
        console.log('[HUD-DEBUG] toggleHUD called');

        if (!this.isSessionSelected()) {
            console.log('[HUD-DEBUG] Cannot toggle HUD: No session selected');
            return;
        }

        if (!this.isInitialized) {
            console.error('[HUD-DEBUG] Cannot toggle HUD: HUD visualizer not initialized');
            return;
        }

        const oldMode = this.hudMode;
        this.hudMode = !this.hudMode;
        console.log('[HUD-DEBUG] HUD mode changed from', oldMode, 'to', this.hudMode);

        this.updateHUDDisplay();

        console.log('[HUD-DEBUG] HUD mode toggled:', this.hudMode ? 'ON' : 'OFF');
    }

    /**
     * Check if a session is currently selected
     * @returns {boolean} - True if session is selected
     */
    isSessionSelected() {
        const hasManager = !!this.sessionManager;
        const selectedId = this.sessionManager?.selectedSessionId;
        const isValidSelection = selectedId && selectedId !== 'all' && selectedId !== '';

        console.log('[HUD-DEBUG] isSessionSelected check:', {
            hasManager: hasManager,
            selectedId: selectedId,
            isValidSelection: isValidSelection,
            finalResult: hasManager && isValidSelection
        });

        return hasManager && isValidSelection;
    }

    /**
     * Update HUD display based on current mode
     */
    updateHUDDisplay() {
        console.log('[HUD-DEBUG] updateHUDDisplay called, hudMode:', this.hudMode);

        const eventsWrapper = document.querySelector('.events-wrapper');
        const hudToggleBtn = document.getElementById('hud-toggle-btn');

        console.log('[HUD-DEBUG] DOM elements found:', {
            eventsWrapper: !!eventsWrapper,
            hudToggleBtn: !!hudToggleBtn,
            hudVisualizer: !!this.hudVisualizer
        });

        if (!eventsWrapper || !hudToggleBtn) {
            console.error('[HUD-DEBUG] Missing DOM elements for HUD display update');
            return;
        }

        if (this.hudMode) {
            console.log('[HUD-DEBUG] Switching to HUD mode...');
            // Switch to HUD mode
            eventsWrapper.classList.add('hud-mode');
            hudToggleBtn.classList.add('btn-hud-active');
            hudToggleBtn.textContent = 'Normal View';

            // Activate HUD visualizer and process events
            if (this.hudVisualizer) {
                console.log('[HUD-DEBUG] Activating HUD visualizer...');
                this.hudVisualizer.activate().then(() => {
                    console.log('[HUD-DEBUG] HUD visualizer activated successfully, processing existing events...');

                    // Additional resize attempts after DOM settles
                    setTimeout(() => {
                        console.log('[HUD-DEBUG] Post-activation resize check...');
                        if (this.hudVisualizer && this.hudVisualizer.ensureContainerResize) {
                            this.hudVisualizer.ensureContainerResize();
                        }
                    }, 100);

                    // Process existing events after libraries are loaded
                    this.processExistingEventsForHUD();
                }).catch((error) => {
                    console.error('[HUD-DEBUG] Failed to activate HUD:', error);
                    console.error('[HUD-DEBUG] Error stack:', error.stack);
                    // Optionally revert HUD mode on failure
                    this.hudMode = false;
                    this.updateHUDDisplay();
                });
            } else {
                console.error('[HUD-DEBUG] No HUD visualizer available');
            }
        } else {
            console.log('[HUD-DEBUG] Switching to normal mode...');
            // Switch to normal mode
            eventsWrapper.classList.remove('hud-mode');
            hudToggleBtn.classList.remove('btn-hud-active');
            hudToggleBtn.textContent = 'HUD View';

            // Deactivate HUD visualizer
            if (this.hudVisualizer) {
                console.log('[HUD-DEBUG] Deactivating HUD visualizer...');
                this.hudVisualizer.deactivate();
            }
        }
    }

    /**
     * Update HUD button state based on session selection
     */
    updateHUDButtonState() {
        console.log('[HUD-DEBUG] updateHUDButtonState called');

        const hudToggleBtn = document.getElementById('hud-toggle-btn');
        if (!hudToggleBtn) {
            console.warn('[HUD-DEBUG] HUD toggle button not found in DOM');
            // Let's check what buttons do exist
            const allButtons = document.querySelectorAll('button');
            console.log('[HUD-DEBUG] Available buttons:', Array.from(allButtons).map(btn => ({ id: btn.id, className: btn.className, text: btn.textContent })));
            return;
        }

        console.log('[HUD-DEBUG] HUD button found:', {
            id: hudToggleBtn.id,
            className: hudToggleBtn.className,
            disabled: hudToggleBtn.disabled,
            title: hudToggleBtn.title,
            textContent: hudToggleBtn.textContent
        });

        const sessionSelected = this.isSessionSelected();
        const selectedSessionId = this.sessionManager?.selectedSessionId;

        console.log('[HUD-DEBUG] HUD Button State Update:', {
            sessionSelected,
            selectedSessionId,
            currentHudMode: this.hudMode,
            sessionManagerExists: !!this.sessionManager
        });

        if (sessionSelected) {
            hudToggleBtn.disabled = false;
            hudToggleBtn.title = 'Toggle HUD visualization mode';
            console.log('[HUD-DEBUG] HUD button enabled - session selected:', selectedSessionId);
        } else {
            hudToggleBtn.disabled = true;
            hudToggleBtn.title = 'Select a session to enable HUD mode';
            console.log('[HUD-DEBUG] HUD button disabled - no session selected');

            // Disable HUD mode if currently active
            if (this.hudMode) {
                console.log('[HUD-DEBUG] Disabling HUD mode because no session selected');
                this.hudMode = false;
                this.updateHUDDisplay();
            }
        }

        console.log('[HUD-DEBUG] Final HUD button state:', {
            disabled: hudToggleBtn.disabled,
            title: hudToggleBtn.title
        });
    }

    /**
     * Process existing events for HUD visualization
     * Called when HUD mode is activated
     */
    processExistingEventsForHUD() {
        console.log('[HUD-MANAGER-DEBUG] processExistingEventsForHUD called');

        if (!this.hudVisualizer) {
            console.error('[HUD-MANAGER-DEBUG] No HUD visualizer available');
            return;
        }

        if (!this.eventViewer) {
            console.error('[HUD-MANAGER-DEBUG] No event viewer available');
            return;
        }

        console.log('[HUD-MANAGER-DEBUG] 🔄 Processing existing events for HUD visualization...');

        // Clear existing visualization
        this.hudVisualizer.clear();

        // Get all events (not just filtered ones) to build complete tree structure
        const allEvents = this.eventViewer.getAllEvents();
        console.log(`[HUD-MANAGER-DEBUG] Retrieved ${allEvents ? allEvents.length : 0} events from event viewer`);

        if (!allEvents) {
            console.error('[HUD-MANAGER-DEBUG] Event viewer returned null/undefined events');
            return;
        }

        if (!Array.isArray(allEvents)) {
            console.error('[HUD-MANAGER-DEBUG] Event viewer returned non-array:', typeof allEvents);
            return;
        }

        if (allEvents.length === 0) {
            console.log('⚠️ No events available for HUD processing');
            return;
        }

        console.log(`[HUD-MANAGER-DEBUG] 📊 Found ${allEvents.length} total events for HUD processing`);

        // Check if we should filter by selected session
        const selectedSessionId = this.sessionManager?.selectedSessionId;
        console.log(`[HUD-MANAGER-DEBUG] Selected session ID: ${selectedSessionId}`);

        let eventsToProcess = allEvents;

        if (selectedSessionId && selectedSessionId !== '' && selectedSessionId !== 'all') {
            console.log(`[HUD-MANAGER-DEBUG] Filtering events for session: ${selectedSessionId}`);
            eventsToProcess = allEvents.filter(event => {
                const eventSessionId = event.session_id || (event.data && event.data.session_id);
                const matches = eventSessionId === selectedSessionId;
                if (!matches) {
                    console.log(`[HUD-MANAGER-DEBUG] Event ${event.timestamp} session ${eventSessionId} does not match ${selectedSessionId}`);
                }
                return matches;
            });
            console.log(`[HUD-MANAGER-DEBUG] Filtered to ${eventsToProcess.length} events for session ${selectedSessionId}`);
        } else {
            console.log('[HUD-MANAGER-DEBUG] No session filtering - processing all events');
        }

        // Sort events by timestamp to ensure chronological processing
        const sortedEvents = eventsToProcess.slice().sort((a, b) => {
            const timeA = new Date(a.timestamp).getTime();
            const timeB = new Date(b.timestamp).getTime();
            return timeA - timeB;
        });

        console.log(`[HUD-MANAGER-DEBUG] Sorted ${sortedEvents.length} events chronologically`);

        // Process events in chronological order
        console.log(`[HUD-MANAGER-DEBUG] Calling hudVisualizer.processExistingEvents with ${sortedEvents.length} events`);
        this.hudVisualizer.processExistingEvents(sortedEvents);

        console.log(`[HUD-MANAGER-DEBUG] ✅ Processed ${sortedEvents.length} events for HUD visualization`);

        // After processing, check if nodes were created
        setTimeout(() => {
            const nodeCount = this.hudVisualizer?.nodes?.size || 0;
            console.log(`[HUD-MANAGER-DEBUG] HUD visualizer now has ${nodeCount} nodes`);

            if (nodeCount === 0) {
                console.warn(`[HUD-MANAGER-DEBUG] No nodes created! Check event processing logic`);
                console.log(`[HUD-MANAGER-DEBUG] Sample processed events:`, sortedEvents.slice(0, 3));
            } else {
                console.log(`[HUD-MANAGER-DEBUG] Successfully created ${nodeCount} nodes`);
                // List the nodes
                if (this.hudVisualizer.nodes) {
                    this.hudVisualizer.nodes.forEach((nodeData, nodeId) => {
                        console.log(`[HUD-MANAGER-DEBUG]   Node: ${nodeId} - ${nodeData.label} (${nodeData.type})`);
                    });
                }
            }
        }, 100);
    }

    /**
     * Handle a new event for HUD processing
     * Called when new events arrive via socket
     * @param {Object} event - Event to process
     */
    handleHUDEvent(event) {
        if (this.hudMode && this.hudVisualizer && this.isInitialized) {
            this.hudVisualizer.processEvent(event);
        }
    }

    /**
     * Handle multiple new events for HUD processing
     * @param {Array} events - Events to process
     */
    handleHUDEvents(events) {
        if (this.hudMode && this.hudVisualizer && this.isInitialized && events.length > 0) {
            // Get the most recent event for HUD processing
            const latestEvent = events[events.length - 1];
            this.handleHUDEvent(latestEvent);
        }
    }

    /**
     * Clear HUD visualization
     */
    clearHUD() {
        if (this.hudVisualizer) {
            this.hudVisualizer.clear();
        }
    }

    /**
     * Get current HUD mode state
     * @returns {boolean} - True if HUD mode is active
     */
    isHUDMode() {
        return this.hudMode;
    }

    /**
     * Get HUD visualizer instance
     * @returns {HUDVisualizer|null} - HUD visualizer instance
     */
    getHUDVisualizer() {
        return this.hudVisualizer;
    }

    /**
     * Check if HUD is initialized properly
     * @returns {boolean} - True if initialized
     */
    isHUDInitialized() {
        return this.isInitialized;
    }

    /**
     * Reinitialize HUD visualizer
     * Useful for recovery from errors
     */
    reinitialize() {
        console.log('Reinitializing HUD manager...');
        this.isInitialized = false;
        this.hudMode = false;

        this.initializeHUDVisualizer();
        this.updateHUDDisplay();
        this.updateHUDButtonState();
    }

    /**
     * Debug method to manually test HUD activation
     * Can be called from browser console: window.dashboard.hudManager.debugActivateHUD()
     */
    debugActivateHUD() {
        console.log('[HUD-DEBUG] debugActivateHUD() called manually');
        console.log('[HUD-DEBUG] Current state:', {
            hudMode: this.hudMode,
            isInitialized: this.isInitialized,
            hasHudVisualizer: !!this.hudVisualizer,
            hasEventViewer: !!this.eventViewer,
            hasSessionManager: !!this.sessionManager,
            selectedSessionId: this.sessionManager?.selectedSessionId,
            isSessionSelected: this.isSessionSelected()
        });

        if (!this.isSessionSelected()) {
            console.error('[HUD-DEBUG] Cannot debug HUD: No session selected');
            return;
        }

        // Force HUD mode and call updateHUDDisplay
        this.hudMode = true;
        this.updateHUDDisplay();
    }

    /**
     * Comprehensive HUD debugging that coordinates with HUD visualizer
     * Can be called from browser console: window.dashboard.hudManager.debugHUDComprehensive()
     */
    debugHUDComprehensive() {
        console.log('[HUD-MANAGER-COMPREHENSIVE-DEBUG] ===============================');
        console.log('[HUD-MANAGER-COMPREHENSIVE-DEBUG] COMPREHENSIVE HUD DEBUG START');
        console.log('[HUD-MANAGER-COMPREHENSIVE-DEBUG] ===============================');

        // 1. Check HUD Manager state
        console.log('[HUD-MANAGER-COMPREHENSIVE-DEBUG] 1. HUD Manager State:');
        const managerState = {
            hudMode: this.hudMode,
            isInitialized: this.isInitialized,
            hasHudVisualizer: !!this.hudVisualizer,
            hasEventViewer: !!this.eventViewer,
            hasSessionManager: !!this.sessionManager,
            selectedSessionId: this.sessionManager?.selectedSessionId,
            isSessionSelected: this.isSessionSelected()
        };
        console.log('[HUD-MANAGER-COMPREHENSIVE-DEBUG]', managerState);

        // 2. Check DOM elements
        console.log('[HUD-MANAGER-COMPREHENSIVE-DEBUG] 2. DOM Elements:');
        const domElements = {
            hudToggleBtn: !!document.getElementById('hud-toggle-btn'),
            hudVisualizer: !!document.getElementById('hud-visualizer'),
            hudCytoscape: !!document.getElementById('hud-cytoscape'),
            eventsWrapper: !!document.querySelector('.events-wrapper'),
            normalView: !!document.getElementById('normal-view')
        };
        console.log('[HUD-MANAGER-COMPREHENSIVE-DEBUG]', domElements);

        // 3. Force activate HUD if not active
        if (!this.hudMode) {
            console.log('[HUD-MANAGER-COMPREHENSIVE-DEBUG] 3. HUD not active, forcing activation...');
            if (!this.isSessionSelected()) {
                console.warn('[HUD-MANAGER-COMPREHENSIVE-DEBUG] No session selected, will use debug mode');
                // Force set a session for debugging
                if (this.sessionManager && this.sessionManager.sessionIds && this.sessionManager.sessionIds.length > 0) {
                    const firstSession = this.sessionManager.sessionIds[0];
                    console.log(`[HUD-MANAGER-COMPREHENSIVE-DEBUG] Setting first available session: ${firstSession}`);
                    this.sessionManager.selectedSessionId = firstSession;
                }
            }

            this.hudMode = true;
            this.updateHUDDisplay();
        } else {
            console.log('[HUD-MANAGER-COMPREHENSIVE-DEBUG] 3. HUD already active');
        }

        // 4. Wait for HUD activation, then run visualizer debug
        setTimeout(() => {
            console.log('[HUD-MANAGER-COMPREHENSIVE-DEBUG] 4. Running HUD Visualizer Debug...');
            if (this.hudVisualizer && this.hudVisualizer.debugBlankScreen) {
                this.hudVisualizer.debugBlankScreen();
            } else {
                console.error('[HUD-MANAGER-COMPREHENSIVE-DEBUG] HUD Visualizer debug method not available');
            }
        }, 1000);

        // 5. Add test events if event viewer has no events
        setTimeout(() => {
            console.log('[HUD-MANAGER-COMPREHENSIVE-DEBUG] 5. Checking event data...');
            const allEvents = this.eventViewer?.getAllEvents();
            console.log(`[HUD-MANAGER-COMPREHENSIVE-DEBUG] Found ${allEvents ? allEvents.length : 0} events`);

            if (!allEvents || allEvents.length === 0) {
                console.log('[HUD-MANAGER-COMPREHENSIVE-DEBUG] No events found, adding test events...');
                this.debugAddTestEvents();
            } else {
                console.log('[HUD-MANAGER-COMPREHENSIVE-DEBUG] Events exist, processing for HUD...');
                this.processExistingEventsForHUD();
            }
        }, 1500);

        console.log('[HUD-MANAGER-COMPREHENSIVE-DEBUG] Comprehensive debug initiated. Check logs above.');
    }

    /**
     * Add test events for debugging when no real events exist
     */
    debugAddTestEvents() {
        if (!this.hudVisualizer) {
            console.error('[HUD-MANAGER-COMPREHENSIVE-DEBUG] No HUD visualizer for test events');
            return;
        }

        console.log('[HUD-MANAGER-COMPREHENSIVE-DEBUG] Adding test events...');

        const testEvents = [
            {
                timestamp: new Date().toISOString(),
                hook_event_name: 'session',
                subtype: 'started',
                session_id: 'debug-session-001',
                data: { session_id: 'debug-session-001' }
            },
            {
                timestamp: new Date(Date.now() + 1000).toISOString(),
                hook_event_name: 'hook',
                subtype: 'user_prompt',
                session_id: 'debug-session-001',
                data: {
                    session_id: 'debug-session-001',
                    prompt_preview: 'Debug the HUD rendering issue'
                }
            },
            {
                timestamp: new Date(Date.now() + 2000).toISOString(),
                hook_event_name: 'hook',
                subtype: 'pre_tool',
                session_id: 'debug-session-001',
                data: {
                    session_id: 'debug-session-001',
                    tool_name: 'Read'
                }
            },
            {
                timestamp: new Date(Date.now() + 3000).toISOString(),
                hook_event_name: 'agent',
                subtype: 'activated',
                session_id: 'debug-session-001',
                data: {
                    session_id: 'debug-session-001',
                    agent_type: 'engineer',
                    agent_name: 'Debug Engineer'
                }
            },
            {
                timestamp: new Date(Date.now() + 4000).toISOString(),
                hook_event_name: 'todo',
                subtype: 'updated',
                session_id: 'debug-session-001',
                data: {
                    session_id: 'debug-session-001'
                }
            }
        ];

        console.log(`[HUD-MANAGER-COMPREHENSIVE-DEBUG] Processing ${testEvents.length} test events...`);
        this.hudVisualizer.processExistingEvents(testEvents);

        // Also add to event viewer if it exists
        if (this.eventViewer && this.eventViewer.addEvent) {
            testEvents.forEach(event => {
                this.eventViewer.addEvent(event);
            });
        }
    }

    /**
     * Force HUD container visibility and test canvas rendering
     */
    debugForceHUDVisibility() {
        console.log('[HUD-MANAGER-VISIBILITY-DEBUG] Forcing HUD visibility...');

        // Force HUD mode DOM changes
        const eventsWrapper = document.querySelector('.events-wrapper');
        const hudVisualizer = document.getElementById('hud-visualizer');
        const hudCytoscape = document.getElementById('hud-cytoscape');
        const normalView = document.getElementById('normal-view');

        if (eventsWrapper) {
            eventsWrapper.classList.add('hud-mode');
            console.log('[HUD-MANAGER-VISIBILITY-DEBUG] Added hud-mode class to events-wrapper');
        }

        if (hudVisualizer) {
            hudVisualizer.style.display = 'block';
            hudVisualizer.style.visibility = 'visible';
            hudVisualizer.style.opacity = '1';
            console.log('[HUD-MANAGER-VISIBILITY-DEBUG] Forced HUD visualizer visibility');
        }

        if (hudCytoscape) {
            hudCytoscape.style.width = '100%';
            hudCytoscape.style.height = '500px';
            hudCytoscape.style.backgroundColor = '#f0f0f0';
            hudCytoscape.style.border = '2px solid #007bff';
            console.log('[HUD-MANAGER-VISIBILITY-DEBUG] Forced HUD cytoscape container dimensions and visibility');
        }

        if (normalView) {
            normalView.style.display = 'none';
            console.log('[HUD-MANAGER-VISIBILITY-DEBUG] Hidden normal view');
        }

        // Wait then test canvas
        setTimeout(() => {
            if (this.hudVisualizer && this.hudVisualizer.debugDrawSimpleShape) {
                console.log('[HUD-MANAGER-VISIBILITY-DEBUG] Testing canvas rendering...');
                this.hudVisualizer.debugDrawSimpleShape();
            }
        }, 500);
    }

    /**
     * Cleanup HUD resources
     */
    cleanup() {
        if (this.hudVisualizer) {
            this.hudVisualizer.deactivate();
            this.hudVisualizer.clear();
        }

        this.hudMode = false;
        this.isInitialized = false;

        console.log('HUD manager cleaned up');
    }
}
