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
        // Current active tab
        this.currentTab = 'events';

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
        console.log('UI state manager initialized');
    }

    /**
     * Set up event handlers for UI interactions
     */
    setupEventHandlers() {
        this.setupTabNavigation();
        this.setupUnifiedKeyboardNavigation();
    }

    /**
     * Set up tab navigation event listeners
     */
    setupTabNavigation() {
        // Tab buttons
        document.querySelectorAll('.tab-button').forEach(button => {
            button.addEventListener('click', () => {
                const tabName = this.getTabNameFromButton(button);
                this.switchTab(tabName);
            });
        });
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
        const text = button.textContent.toLowerCase();
        if (text.includes('events')) return 'events';
        if (text.includes('activity')) return 'activity';
        if (text.includes('agents')) return 'agents';
        if (text.includes('tools')) return 'tools';
        if (text.includes('files')) return 'files';
        if (text.includes('code')) return 'code';
        if (text.includes('sessions')) return 'sessions';
        if (text.includes('system')) return 'system';
        return 'events';
    }

    /**
     * Switch to specified tab
     * @param {string} tabName - Name of tab to switch to
     */
    switchTab(tabName) {
        console.log(`[DEBUG] switchTab called with tabName: ${tabName}`);
        const previousTab = this.currentTab;
        this.currentTab = tabName;

        // Update tab button active states
        document.querySelectorAll('.tab-button').forEach(btn => {
            btn.classList.remove('active');
            if (this.getTabNameFromButton(btn) === tabName) {
                btn.classList.add('active');
            }
        });

        // Show/hide tab content using CSS classes
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.remove('active');
        });

        const activeTab = document.getElementById(`${tabName}-tab`);
        if (activeTab) {
            activeTab.classList.add('active');
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
