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
        // Hash to tab mapping
        this.hashToTab = {
            '#events': 'events',
            '#agents': 'agents',
            '#tools': 'tools',
            '#files': 'files',
            '#activity': 'activity',
            '#file_tree': 'claude-tree',
            '#browser_logs': 'browser-logs',
            '': 'events', // default
        };

        // Tab to hash mapping (reverse lookup)
        this.tabToHash = {
            'events': '#events',
            'agents': '#agents',
            'tools': '#tools',
            'files': '#files',
            'activity': '#activity',
            'claude-tree': '#file_tree',
            'browser-logs': '#browser_logs'
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
        const tabName = this.hashToTab[hash] || 'events';
        console.log('[Hash Navigation] Switching to tab:', tabName, 'from hash:', hash);
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
        // First check for data-tab attribute
        const dataTab = button.getAttribute('data-tab');
        if (dataTab) return dataTab;
        
        // Fallback to text content matching
        const text = button.textContent.toLowerCase();
        if (text.includes('events')) return 'events';
        if (text.includes('activity')) return 'activity';
        if (text.includes('agents')) return 'agents';
        if (text.includes('tools')) return 'tools';
        if (text.includes('browser')) return 'browser-logs';  // Added browser logs support
        if (text.includes('files')) return 'files';
        if (text.includes('file tree')) return 'claude-tree';
        if (text.includes('code')) return 'code';
        if (text.includes('sessions')) return 'sessions';
        if (text.includes('system')) return 'system';
        return 'events';
    }

    /**
     * Switch to specified tab
     * @param {string} tabName - Name of tab to switch to
     * @param {boolean} updateHash - Whether to update URL hash (default: true)
     */
    switchTab(tabName, updateHash = true) {
        console.log(`[Hash Navigation] switchTab called with tabName: ${tabName}, updateHash: ${updateHash}`);
        
        // Update URL hash if requested (when triggered by user action, not hash change)
        if (updateHash && this.tabToHash[tabName]) {
            const newHash = this.tabToHash[tabName];
            if (window.location.hash !== newHash) {
                console.log(`[Hash Navigation] Updating hash to: ${newHash}`);
                window.location.hash = newHash;
                return; // The hashchange event will trigger switchTab again
            }
        }

        const previousTab = this.currentTab;
        this.currentTab = tabName;

        // Update tab button active states - ensure ALL tabs are deselected first
        const allTabButtons = document.querySelectorAll('.tab-button');
        allTabButtons.forEach(btn => {
            btn.classList.remove('active');
        });
        
        // Now add active class ONLY to the selected tab
        allTabButtons.forEach(btn => {
            const btnTabName = this.getTabNameFromButton(btn);
            if (btnTabName === tabName) {
                btn.classList.add('active');
                console.log(`[DEBUG] Set active on button with data-tab: ${btn.getAttribute('data-tab')}`);
            }
        });

        // Show/hide tab content using CSS classes - ensure ALL are hidden first
        const allTabContents = document.querySelectorAll('.tab-content');
        allTabContents.forEach(content => {
            content.classList.remove('active');
        });

        // Now show ONLY the selected tab content
        const activeTab = document.getElementById(`${tabName}-tab`);
        if (activeTab) {
            activeTab.classList.add('active');
            console.log(`[DEBUG] Set active on content: ${tabName}-tab`);
            
            // Special handling for File Tree tab - ensure it never shows events
            if (tabName === 'claude-tree') {
                const claudeTreeContainer = document.getElementById('claude-tree-container');
                if (claudeTreeContainer) {
                    // Check if events list somehow got into this container
                    const eventsList = claudeTreeContainer.querySelector('#events-list');
                    if (eventsList) {
                        console.warn('[UIStateManager] Found events-list in File Tree container, removing it!');
                        eventsList.remove();
                    }
                    
                    // Check for event items
                    const eventItems = claudeTreeContainer.querySelectorAll('.event-item');
                    if (eventItems.length > 0) {
                        console.warn('[UIStateManager] Found event items in File Tree container, clearing!');
                        eventItems.forEach(item => item.remove());
                    }
                }
            }
        }

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
            
            // EXTREME NUCLEAR HANDLING for Browser Logs tab - FORCE COMPLETE ISOLATION
            if (tabName === 'browser-logs') {
                console.error('[UI-STATE v3 EXTREME] 🚨🚨🚨 SWITCHING TO BROWSER LOGS - EXTREME NUCLEAR MODE');
                console.error('[UI-STATE v3 EXTREME] Stack trace:', new Error().stack);
                
                // EXTREME DIAGNOSTIC: Check what's trying to render
                const container = document.getElementById('browser-logs-container');
                if (container) {
                    console.error('[UI-STATE v3 EXTREME] Container found, current innerHTML length:', container.innerHTML.length);
                    console.error('[UI-STATE v3 EXTREME] Container classes:', container.className);
                    console.error('[UI-STATE v3 EXTREME] Container children count:', container.children.length);
                    
                    // EXTREME: Stop ALL event propagation
                    const stopAllEvents = (e) => {
                        e.stopPropagation();
                        e.stopImmediatePropagation();
                        e.preventDefault();
                    };
                    
                    // EXTREME: Block EventViewer from touching this container
                    if (window.eventViewer) {
                        console.error('[UI-STATE v3 EXTREME] 🚨 EventViewer exists - DISABLING IT');
                        // Temporarily override EventViewer's renderEvents method
                        const originalRender = window.eventViewer.renderEvents;
                        window.eventViewer.renderEvents = function() {
                            const targetEl = document.getElementById('events-list');
                            // Only allow rendering if target is NOT in browser-logs-tab
                            if (targetEl && !targetEl.closest('#browser-logs-tab')) {
                                return originalRender.call(this);
                            }
                            console.error('[UI-STATE v3 EXTREME] BLOCKED EventViewer.renderEvents in Browser Logs tab!');
                        };
                    }
                    
                    // EXTREME CLEAR: Multiple passes to ensure complete clearing
                    for (let i = 0; i < 3; i++) {
                        container.innerHTML = '';
                        container.textContent = '';
                        while (container.firstChild) {
                            container.removeChild(container.firstChild);
                        }
                    }
                    
                    // Reset all attributes and classes
                    container.className = '';
                    container.removeAttribute('data-events');
                    container.removeAttribute('data-component');
                    container.setAttribute('data-component', 'browser-logs-only');
                    container.setAttribute('data-no-events', 'true');
                    
                    // EXTREME: Set a guard flag
                    container.dataset.browserLogsGuard = 'active';
                    
                    // EXTREME: Override container's innerHTML setter temporarily
                    const originalInnerHTML = Object.getOwnPropertyDescriptor(Element.prototype, 'innerHTML');
                    Object.defineProperty(container, 'innerHTML', {
                        set: function(value) {
                            if (value && typeof value === 'string' && 
                                (value.includes('[hook]') || value.includes('event-item') || 
                                 value.includes('hook.pre_tool') || value.includes('hook.post_tool'))) {
                                console.error('[UI-STATE v3 EXTREME] 🚨 BLOCKED CONTAMINATED innerHTML:', value.substring(0, 100));
                                return;
                            }
                            originalInnerHTML.set.call(this, value);
                        },
                        get: function() {
                            return originalInnerHTML.get.call(this);
                        },
                        configurable: true
                    });
                    
                    // Check if BrowserLogViewer exists
                    if (typeof BrowserLogViewer !== 'undefined') {
                        // ALWAYS recreate to ensure clean state
                        if (window.browserLogViewer) {
                            console.error('[UI-STATE v3 EXTREME] Destroying old BrowserLogViewer instance');
                            if (window.browserLogViewer.destroy) {
                                window.browserLogViewer.destroy();
                            }
                            window.browserLogViewer = null;
                        }
                        
                        // Create fresh instance with extreme verification
                        console.error('[UI-STATE v3 EXTREME] Creating NEW BrowserLogViewer v3.0 EXTREME instance');
                        window.browserLogViewer = new BrowserLogViewer(container);
                        console.error('[UI-STATE v3 EXTREME] ✅ BrowserLogViewer v3.0 EXTREME INITIALIZED');
                        
                        // Force immediate render
                        if (window.browserLogViewer.render) {
                            window.browserLogViewer.render();
                        }
                    } else {
                        // Fallback: Show hardcoded message if viewer not loaded
                        console.error('[UI-STATE v3 EXTREME] BrowserLogViewer not found - showing fallback');
                        // Restore innerHTML setter for fallback message
                        Object.defineProperty(container, 'innerHTML', originalInnerHTML);
                        container.innerHTML = `
                            <div style="padding: 20px; text-align: center; background: #f0f0f0; border: 3px solid red;">
                                <h1 style="color: red;">🚨 BROWSER LOGS ONLY 🚨</h1>
                                <h2 style="color: green;">NO HOOK EVENTS ALLOWED</h2>
                                <p style="color: red; font-weight: bold; font-size: 18px;">⚠️ Hook events ([hook]) are FORCEFULLY BLOCKED ⚠️</p>
                                <p>This tab shows ONLY browser console logs.</p>
                                <p style="color: blue;">Browser Log Viewer v3.0 EXTREME is loading...</p>
                            </div>
                        `;
                    }
                    
                    // EXTREME: Multiple contamination checks
                    const checkContamination = () => {
                        const contamination = container.querySelectorAll('.event-item, .events-list, [class*="event"]');
                        if (contamination.length > 0) {
                            console.error(`[UI-STATE v3 EXTREME] 🚨 CONTAMINATION DETECTED (${contamination.length} items) - NUKING!`);
                            contamination.forEach(item => {
                                console.error('[UI-STATE v3 EXTREME] Removing contaminated element:', item.className);
                                item.remove();
                            });
                            if (window.browserLogViewer && window.browserLogViewer.render) {
                                window.browserLogViewer.render();
                            }
                        }
                        
                        // Check text content for hook events
                        if (container.textContent.includes('[hook]') || 
                            container.textContent.includes('hook.pre_tool')) {
                            console.error('[UI-STATE v3 EXTREME] 🚨 TEXT CONTAMINATION DETECTED!');
                            if (window.browserLogViewer) {
                                container.innerHTML = '';
                                window.browserLogViewer.render();
                            }
                        }
                    };
                    
                    // Run contamination checks multiple times
                    setTimeout(checkContamination, 50);
                    setTimeout(checkContamination, 100);
                    setTimeout(checkContamination, 200);
                    setTimeout(checkContamination, 500);
                    
                    // EXTREME: Monitor for mutations
                    const observer = new MutationObserver((mutations) => {
                        for (const mutation of mutations) {
                            if (mutation.type === 'childList') {
                                for (const node of mutation.addedNodes) {
                                    if (node.nodeType === Node.ELEMENT_NODE) {
                                        const element = node;
                                        if (element.classList?.contains('event-item') ||
                                            element.textContent?.includes('[hook]')) {
                                            console.error('[UI-STATE v3 EXTREME] 🚨 MUTATION DETECTED - BLOCKING!');
                                            element.remove();
                                        }
                                    }
                                }
                            }
                        }
                    });
                    
                    observer.observe(container, {
                        childList: true,
                        subtree: true,
                        characterData: true
                    });
                    
                    // Store observer for cleanup
                    container.dataset.mutationObserver = 'active';
                    window.browserLogsMutationObserver = observer;
                } else {
                    console.error('[UI-STATE v3 EXTREME] 🚨 BROWSER LOGS CONTAINER NOT FOUND!');
                }
            }
        }, 100);
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
