/**
 * UI State Manager Module
 *
 * Manages UI state including tab switching, card selection, keyboard navigation,
 * and visual feedback across the dashboard interface.
 *
 * WHY: Extracted from main dashboard to centralize UI state management and
 * provide better separation between business logic and UI state. This makes
 * the UI behavior more predictable and easier to test.
 *
 * DESIGN DECISION: Maintains centralized state for current tab, selected cards,
 * and navigation context while providing a clean API for other modules to
 * interact with UI state changes.
 */
class UIStateManager {
    constructor() {
        // Switching lock to prevent race conditions
        this._switching = false;

        // Hash to tab mapping
        this.hashToTab = {
            '#events': 'events',
            '#agents': 'agents',
            '#tools': 'tools',
            '#files': 'files',
            '#activity': 'activity',
            '#file_tree': 'claude-tree',
            '': 'events', // default
        };

        // Tab to hash mapping (reverse lookup)
        this.tabToHash = {
            'events': '#events',
            'agents': '#agents',
            'tools': '#tools',
            'files': '#files',
            'activity': '#activity',
            'claude-tree': '#file_tree'
        };

        // Current active tab - will be set based on URL hash
        this.currentTab = this.getTabFromHash();

        // Auto-scroll behavior
        this.autoScroll = true;

        // Selection state - tracks the currently selected card across all tabs
        this.selectedCard = {
            tab: null,        // which tab the selection is in
            index: null,      // index of selected item in that tab
            type: null,       // 'event', 'agent', 'tool', 'file'
            data: null        // the actual data object
        };

        // Navigation state for each tab
        this.tabNavigation = {
            events: { selectedIndex: -1, items: [] },
            agents: { selectedIndex: -1, items: [] },
            tools: { selectedIndex: -1, items: [] },
            files: { selectedIndex: -1, items: [] }
        };

        this.setupEventHandlers();
        console.log('UI state manager initialized with hash navigation');
        
        // Initialize with current hash
        this.handleHashChange();
    }

    /**
     * Get tab name from current URL hash
     * @returns {string} - Tab name based on hash
     */
    getTabFromHash() {
        const hash = window.location.hash || '';
        return this.hashToTab[hash] || 'events';
    }

    /**
     * Set up event handlers for UI interactions
     */
    setupEventHandlers() {
        this.setupHashNavigation();
        this.setupTabClickHandlers(); // Add explicit tab click handlers
        this.setupUnifiedKeyboardNavigation();
    }

    /**
     * Set up hash-based navigation
     */
    setupHashNavigation() {
        // Handle hash changes
        window.addEventListener('hashchange', (e) => {
            console.log('[Hash Navigation] Hash changed from', new URL(e.oldURL).hash, 'to', window.location.hash);
            this.handleHashChange();
        });

        // Handle initial page load
        document.addEventListener('DOMContentLoaded', () => {
            console.log('[Hash Navigation] Initial hash:', window.location.hash);
            this.handleHashChange();
        });
    }

    /**
     * Handle hash change events
     */
    handleHashChange() {
        const hash = window.location.hash || '';
        console.log('[Hash Navigation] DETAILED DEBUG:');
        console.log('[Hash Navigation] - Current hash:', hash);
        console.log('[Hash Navigation] - hashToTab mapping:', this.hashToTab);
        console.log('[Hash Navigation] - Direct lookup result:', this.hashToTab[hash]);
        console.log('[Hash Navigation] - Is hash in mapping?', hash in this.hashToTab);
        console.log('[Hash Navigation] - Hash length:', hash.length);
        console.log('[Hash Navigation] - Hash char codes:', hash.split('').map(c => c.charCodeAt(0)));
        
        const tabName = this.hashToTab[hash] || 'events';
        console.log('[Hash Navigation] Final resolved tab name:', tabName);
        
        // Special logging for File Tree tab
        if (tabName === 'claude-tree' || hash === '#file_tree') {
            console.log('[UIStateManager] FILE TREE TAB SELECTED via hash:', hash);
            console.log('[UIStateManager] Tab name resolved to:', tabName);
        }
        
        this.switchTab(tabName, false); // false = don't update hash (we're responding to hash change)
    }

    /**
     * DEPRECATED: Tab navigation is now handled by hash navigation
     * This method is kept for backward compatibility but does nothing
     */
    setupTabNavigation() {
        console.log('[Hash Navigation] setupTabNavigation is deprecated - using hash navigation instead');
    }

    /**
     * Set up explicit click handlers for tab buttons to ensure proper routing
     * This ensures tab clicks work even if other modules interfere
     */
    setupTabClickHandlers() {
        document.querySelectorAll('.tab-button').forEach(button => {
            button.addEventListener('click', (e) => {
                console.log('[UIStateManager] Tab button clicked:', e.target);
                
                // Prevent default only if we're going to handle it
                const tabName = this.getTabNameFromButton(e.target);
                console.log('[UIStateManager] Resolved tab name:', tabName);
                
                if (tabName) {
                    // Let the href attribute update the hash naturally, which will trigger our hashchange handler
                    // But also explicitly trigger the switch in case href doesn't work
                    setTimeout(() => {
                        const expectedHash = this.tabToHash[tabName];
                        if (window.location.hash !== expectedHash && expectedHash) {
                            console.log('[UIStateManager] Hash not updated, forcing update:', expectedHash);
                            window.location.hash = expectedHash;
                        }
                    }, 10);
                }
            });
        });
        
        console.log('[UIStateManager] Tab click handlers set up for', document.querySelectorAll('.tab-button').length, 'buttons');
    }

    /**
     * Set up unified keyboard navigation across all tabs
     */
    setupUnifiedKeyboardNavigation() {
        document.addEventListener('keydown', (e) => {
            // Only handle if not in an input field
            if (document.activeElement &&
                ['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement.tagName)) {
                return;
            }

            if (e.key === 'ArrowUp' || e.key === 'ArrowDown') {
                e.preventDefault();
                this.handleUnifiedArrowNavigation(e.key === 'ArrowDown' ? 1 : -1);
            } else if (e.key === 'Enter') {
                e.preventDefault();
                this.handleUnifiedEnterKey();
            } else if (e.key === 'Escape') {
                this.clearUnifiedSelection();
            }
        });
    }

    /**
     * Get tab name from button element
     * @param {HTMLElement} button - Tab button element
     * @returns {string} - Tab name
     */
    getTabNameFromButton(button) {
        console.log('[getTabNameFromButton] DEBUG: button object:', button);
        console.log('[getTabNameFromButton] DEBUG: button.nodeType:', button.nodeType);
        console.log('[getTabNameFromButton] DEBUG: button.tagName:', button.tagName);
        
        // CRITICAL FIX: Make sure we're dealing with the actual button element
        // Sometimes the click target might be a child element (like the emoji icon)
        let targetButton = button;
        if (button && button.closest && button.closest('.tab-button')) {
            targetButton = button.closest('.tab-button');
            console.log('[getTabNameFromButton] DEBUG: Used closest() to find actual button');
        }
        
        // First check for data-tab attribute
        const dataTab = targetButton ? targetButton.getAttribute('data-tab') : null;
        console.log('[getTabNameFromButton] DEBUG: data-tab attribute:', dataTab);
        console.log('[getTabNameFromButton] DEBUG: dataTab truthy:', !!dataTab);
        
        // CRITICAL: Specifically handle the File Tree case
        if (dataTab === 'claude-tree') {
            console.log('[getTabNameFromButton] DEBUG: Found claude-tree data-tab, returning it');
            return 'claude-tree';
        }
        
        if (dataTab) {
            console.log('[getTabNameFromButton] DEBUG: Returning dataTab:', dataTab);
            return dataTab;
        }
        
        // Fallback to text content matching
        const text = targetButton ? targetButton.textContent.toLowerCase() : '';
        console.log('[getTabNameFromButton] DEBUG: text content:', text);
        console.log('[getTabNameFromButton] DEBUG: text includes file tree:', text.includes('file tree'));
        console.log('[getTabNameFromButton] DEBUG: text includes events:', text.includes('events'));
        
        // CRITICAL: Check File Tree FIRST since it's the problematic one
        if (text.includes('file tree') || text.includes('📝')) {
            console.log('[getTabNameFromButton] DEBUG: Matched file tree, returning claude-tree');
            return 'claude-tree';
        }
        if (text.includes('activity') || text.includes('🌳')) return 'activity';
        if (text.includes('agents') || text.includes('🤖')) return 'agents';
        if (text.includes('tools') || text.includes('🔧')) return 'tools';
        if (text.includes('files') || text.includes('📁')) return 'files';
        if (text.includes('code')) return 'code';
        if (text.includes('sessions')) return 'sessions';
        if (text.includes('system')) return 'system';
        if (text.includes('events') || text.includes('📊')) return 'events';
        
        console.log('[getTabNameFromButton] DEBUG: No match, falling back to events');
        return 'events';
    }

    /**
     * Switch to specified tab - BULLETPROOF VERSION
     * @param {string} tabName - Name of tab to switch to
     * @param {boolean} updateHash - Whether to update URL hash (default: true)
     */
    switchTab(tabName, updateHash = true) {
        // CRITICAL: Prevent race conditions by using a switching lock
        if (this._switching) {
            console.log(`[UIStateManager] Tab switch already in progress, queuing: ${tabName}`);
            setTimeout(() => this.switchTab(tabName, updateHash), 50);
            return;
        }
        this._switching = true;

        console.log(`[UIStateManager] BULLETPROOF switchTab: ${tabName}, updateHash: ${updateHash}`);

        try {
            // Extra logging for File Tree debugging
            if (tabName === 'claude-tree') {
                console.log('[UIStateManager] SWITCHING TO FILE TREE TAB');
                console.log('[UIStateManager] Current tab before switch:', this.currentTab);
            }

            // Update URL hash if requested (when triggered by user action, not hash change)
            if (updateHash && this.tabToHash[tabName]) {
                const newHash = this.tabToHash[tabName];
                if (window.location.hash !== newHash) {
                    console.log(`[UIStateManager] Updating hash to: ${newHash}`);
                    this._switching = false; // Release lock before hash change
                    window.location.hash = newHash;
                    return; // The hashchange event will trigger switchTab again
                }
            }

            const previousTab = this.currentTab;
            this.currentTab = tabName;

            // STEP 1: NUCLEAR RESET - Remove ALL active states unconditionally
            this._removeAllActiveStates();

            // STEP 2: Set the ONE correct tab as active
            this._setActiveTab(tabName);

            // STEP 3: Show ONLY the correct content
            this._showTabContent(tabName);

            // STEP 4: Cleanup and validation
            this._validateTabState(tabName);

            // Clear previous selections when switching tabs
            this.clearUnifiedSelection();

            // Trigger tab change event for other modules
            document.dispatchEvent(new CustomEvent('tabChanged', {
                detail: {
                    newTab: tabName,
                    previousTab: previousTab
                }
            }));

            // Auto-scroll to bottom after a brief delay to ensure content is rendered
            setTimeout(() => {
                if (this.autoScroll) {
                    this.scrollCurrentTabToBottom();
                }

                // Special handling for File Tree tab - trigger the tree render
                // But DON'T let it manipulate tabs itself
                if (tabName === 'claude-tree' && window.CodeViewer) {
                    // Call a new method that only renders content, not tab switching
                    if (window.CodeViewer.renderContent) {
                        window.CodeViewer.renderContent();
                    } else {
                        // Fallback to show() but it should be fixed to not switch tabs
                        window.CodeViewer.show();
                    }
                }
            }, 100);

        } finally {
            // ALWAYS release the lock
            setTimeout(() => {
                this._switching = false;
            }, 200);
        }
    }

    /**
     * NUCLEAR RESET: Remove ALL active states from ALL elements
     * This ensures no stale states remain
     */
    _removeAllActiveStates() {
        // Remove active class from ALL tab buttons
        document.querySelectorAll('.tab-button').forEach(btn => {
            btn.classList.remove('active');
            // Also remove any inline styling that might interfere
            btn.style.removeProperty('border-bottom');
            btn.style.removeProperty('color');
        });

        // Remove active class from ALL tab content
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.remove('active');
            // Clear any inline display styles
            content.style.removeProperty('display');

            // CRITICAL: Clean leaked content in non-events tabs
            if (content.id !== 'events-tab') {
                this._cleanLeakedEventContent(content);
            }
        });

        console.log('[UIStateManager] NUCLEAR: All active states removed');
    }

    /**
     * Set ONLY the specified tab as active
     */
    _setActiveTab(tabName) {
        const targetTab = document.querySelector(`[data-tab="${tabName}"]`);
        if (targetTab) {
            targetTab.classList.add('active');
            console.log(`[UIStateManager] Set active: ${tabName}`);
        } else {
            console.error(`[UIStateManager] Could not find tab button for: ${tabName}`);
        }
    }

    /**
     * Show ONLY the specified tab content
     */
    _showTabContent(tabName) {
        const targetContent = document.getElementById(`${tabName}-tab`);
        if (targetContent) {
            targetContent.classList.add('active');
            console.log(`[UIStateManager] Showing content: ${tabName}-tab`);

            // Special handling for File Tree tab
            if (tabName === 'claude-tree') {
                this._prepareFileTreeContent(targetContent);
            }
        } else {
            console.error(`[UIStateManager] Could not find content for: ${tabName}`);
        }
    }

    /**
     * Clean any leaked event content from non-event tabs
     */
    _cleanLeakedEventContent(contentElement) {
        // Remove any event items that may have leaked
        const leakedEventItems = contentElement.querySelectorAll('.event-item');
        if (leakedEventItems.length > 0) {
            console.warn(`[UIStateManager] Found ${leakedEventItems.length} leaked event items in ${contentElement.id}, removing...`);
            leakedEventItems.forEach(item => item.remove());
        }

        // Remove any events-list elements
        const leakedEventsList = contentElement.querySelectorAll('#events-list, .events-list');
        if (leakedEventsList.length > 0) {
            console.warn(`[UIStateManager] Found leaked events-list in ${contentElement.id}, removing...`);
            leakedEventsList.forEach(list => list.remove());
        }
    }

    /**
     * Prepare File Tree content area
     */
    _prepareFileTreeContent(fileTreeContent) {
        const claudeTreeContainer = document.getElementById('claude-tree-container');
        if (claudeTreeContainer) {
            // Final cleanup check
            this._cleanLeakedEventContent(claudeTreeContainer);

            // Ensure container is properly marked for CodeViewer
            claudeTreeContainer.setAttribute('data-owner', 'code-viewer');
            claudeTreeContainer.setAttribute('data-component', 'CodeViewer');

            console.log('[UIStateManager] File Tree container prepared');
        }
    }

    /**
     * Validate that tab state is correct after switching
     */
    _validateTabState(expectedTab) {
        setTimeout(() => {
            const activeTabs = document.querySelectorAll('.tab-button.active');
            const activeContents = document.querySelectorAll('.tab-content.active');

            if (activeTabs.length !== 1) {
                console.error(`[UIStateManager] VALIDATION FAILED: Expected 1 active tab, found ${activeTabs.length}`);
                activeTabs.forEach((tab, idx) => {
                    console.error(`  - Active tab ${idx + 1}: ${tab.textContent.trim()} (${tab.getAttribute('data-tab')})`);
                });
                // Force fix
                this._removeAllActiveStates();
                this._setActiveTab(expectedTab);
            }

            if (activeContents.length !== 1) {
                console.error(`[UIStateManager] VALIDATION FAILED: Expected 1 active content, found ${activeContents.length}`);
                activeContents.forEach((content, idx) => {
                    console.error(`  - Active content ${idx + 1}: ${content.id}`);
                });
                // Force fix
                this._removeAllActiveStates();
                this._showTabContent(expectedTab);
            }

            console.log(`[UIStateManager] Tab state validated for: ${expectedTab}`);
        }, 50);
    }

    /**
     * Handle unified arrow navigation across tabs
     * @param {number} direction - Navigation direction (1 for down, -1 for up)
     */
    handleUnifiedArrowNavigation(direction) {
        const tabNav = this.tabNavigation[this.currentTab];
        if (!tabNav) return;

        let newIndex = tabNav.selectedIndex + direction;

        // Handle bounds
        if (tabNav.items.length === 0) return;

        if (newIndex < 0) {
            newIndex = tabNav.items.length - 1;
        } else if (newIndex >= tabNav.items.length) {
            newIndex = 0;
        }

        this.selectCardByIndex(this.currentTab, newIndex);
    }

    /**
     * Handle unified Enter key across all tabs
     */
    handleUnifiedEnterKey() {
        const tabNav = this.tabNavigation[this.currentTab];
        if (!tabNav || tabNav.selectedIndex === -1) return;

        const selectedElement = tabNav.items[tabNav.selectedIndex];
        if (selectedElement && selectedElement.onclick) {
            selectedElement.onclick();
        }
    }

    /**
     * Clear all unified selection states
     */
    clearUnifiedSelection() {
        // Clear all tab navigation states
        Object.keys(this.tabNavigation).forEach(tabName => {
            this.tabNavigation[tabName].selectedIndex = -1;
        });

        // Clear card selection
        this.clearCardSelection();
    }

    /**
     * Update tab navigation items for current tab
     * Should be called after tab content is rendered
     */
    updateTabNavigationItems() {
        const tabNav = this.tabNavigation[this.currentTab];
        if (!tabNav) return;

        let containerSelector;
        switch (this.currentTab) {
            case 'events':
                containerSelector = '#events-list .event-item';
                break;
            case 'agents':
                containerSelector = '#agents-list .event-item';
                break;
            case 'tools':
                containerSelector = '#tools-list .event-item';
                break;
            case 'files':
                containerSelector = '#files-list .event-item';
                break;
        }

        if (containerSelector) {
            tabNav.items = Array.from(document.querySelectorAll(containerSelector));
        }
    }

    /**
     * Select card by index for specified tab
     * @param {string} tabName - Tab name
     * @param {number} index - Index of item to select
     */
    selectCardByIndex(tabName, index) {
        const tabNav = this.tabNavigation[tabName];
        if (!tabNav || index < 0 || index >= tabNav.items.length) return;

        // Update navigation state
        tabNav.selectedIndex = index;

        // Update visual selection
        this.updateUnifiedSelectionUI();

        // If this is a different tab selection, record the card selection
        const selectedElement = tabNav.items[index];
        if (selectedElement) {
            // Extract data from the element to populate selectedCard
            this.selectCard(tabName, index, this.getCardType(tabName), index);
        }

        // Show details for the selected item
        this.showCardDetails(tabName, index);
    }

    /**
     * Update visual selection UI for unified navigation
     */
    updateUnifiedSelectionUI() {
        // Clear all existing selections
        document.querySelectorAll('.event-item.keyboard-selected').forEach(el => {
            el.classList.remove('keyboard-selected');
        });

        // Apply selection to current tab's selected item
        const tabNav = this.tabNavigation[this.currentTab];
        if (tabNav && tabNav.selectedIndex !== -1 && tabNav.items[tabNav.selectedIndex]) {
            tabNav.items[tabNav.selectedIndex].classList.add('keyboard-selected');
        }
    }

    /**
     * Show card details for specified tab and index
     * @param {string} tabName - Tab name
     * @param {number} index - Item index
     */
    showCardDetails(tabName, index) {
        // Dispatch event for other modules to handle
        document.dispatchEvent(new CustomEvent('showCardDetails', {
            detail: {
                tabName: tabName,
                index: index
            }
        }));
    }

    /**
     * Select a specific card
     * @param {string} tabName - Tab name
     * @param {number} index - Item index
     * @param {string} type - Item type
     * @param {*} data - Item data
     */
    selectCard(tabName, index, type, data) {
        // Clear previous selection
        this.clearCardSelection();

        // Update selection state
        this.selectedCard = {
            tab: tabName,
            index: index,
            type: type,
            data: data
        };

        this.updateCardSelectionUI();

        console.log('Card selected:', this.selectedCard);
    }

    /**
     * Clear card selection
     */
    clearCardSelection() {
        // Clear visual selection from all tabs
        document.querySelectorAll('.event-item.selected, .file-item.selected').forEach(el => {
            el.classList.remove('selected');
        });

        // Reset selection state
        this.selectedCard = {
            tab: null,
            index: null,
            type: null,
            data: null
        };
    }

    /**
     * Update card selection UI
     */
    updateCardSelectionUI() {
        if (!this.selectedCard.tab || this.selectedCard.index === null) return;

        // Get the list container for the selected tab
        let listContainer;
        switch (this.selectedCard.tab) {
            case 'events':
                listContainer = document.getElementById('events-list');
                break;
            case 'agents':
                listContainer = document.getElementById('agents-list');
                break;
            case 'tools':
                listContainer = document.getElementById('tools-list');
                break;
            case 'files':
                listContainer = document.getElementById('files-list');
                break;
        }

        if (listContainer) {
            const items = listContainer.querySelectorAll('.event-item, .file-item');
            if (items[this.selectedCard.index]) {
                items[this.selectedCard.index].classList.add('selected');
            }
        }
    }

    /**
     * Get card type based on tab name
     * @param {string} tabName - Tab name
     * @returns {string} - Card type
     */
    getCardType(tabName) {
        switch (tabName) {
            case 'events': return 'event';
            case 'agents': return 'agent';
            case 'tools': return 'tool';
            case 'files': return 'file';
            default: return 'unknown';
        }
    }

    /**
     * Scroll current tab to bottom
     */
    scrollCurrentTabToBottom() {
        const tabId = `${this.currentTab}-list`;
        const element = document.getElementById(tabId);
        if (element && this.autoScroll) {
            element.scrollTop = element.scrollHeight;
        }
    }

    /**
     * Clear selection for cleanup
     */
    clearSelection() {
        this.clearCardSelection();
        this.clearUnifiedSelection();
    }

    /**
     * Get current tab name
     * @returns {string} - Current tab name
     */
    getCurrentTab() {
        return this.currentTab;
    }

    /**
     * Get selected card info
     * @returns {Object} - Selected card state
     */
    getSelectedCard() {
        return { ...this.selectedCard };
    }

    /**
     * Get tab navigation state
     * @returns {Object} - Tab navigation state
     */
    getTabNavigation() {
        return { ...this.tabNavigation };
    }

    /**
     * Set auto-scroll behavior
     * @param {boolean} enabled - Whether to enable auto-scroll
     */
    setAutoScroll(enabled) {
        this.autoScroll = enabled;
    }

    /**
     * Get auto-scroll state
     * @returns {boolean} - Auto-scroll enabled state
     */
    getAutoScroll() {
        return this.autoScroll;
    }
}
// ES6 Module export
export { UIStateManager };
export default UIStateManager;

// Make UIStateManager globally available for dist/dashboard.js
window.UIStateManager = UIStateManager;
