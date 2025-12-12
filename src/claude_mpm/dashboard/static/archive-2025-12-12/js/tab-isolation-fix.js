/**
 * BULLETPROOF FILE TREE TAB ISOLATION FIX
 *
 * This is a surgical fix to resolve the File Tree tab isolation issue
 * without requiring changes to the complex build system or existing dashboard.
 *
 * This script can be loaded independently and will override any existing
 * problematic tab switching behavior.
 */

console.log('[TAB-FIX] Bulletproof File Tree tab isolation fix loaded');

// Wait for DOM to be ready
function whenReady(callback) {
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', callback);
    } else {
        callback();
    }
}

function implementTabFix() {
    console.log('[TAB-FIX] Implementing bulletproof tab switching...');

    let tabSwitchingInProgress = false;

    function switchToTab(tabName) {
        if (tabSwitchingInProgress) {
            console.log('[TAB-FIX] Tab switching already in progress, queuing...');
            setTimeout(() => switchToTab(tabName), 100);
            return;
        }

        tabSwitchingInProgress = true;
        console.log(`[TAB-FIX] Switching to tab: ${tabName}`);

        try {
            // STEP 1: Remove ALL active states
            document.querySelectorAll('.tab-button').forEach(btn => {
                btn.classList.remove('active');
            });

            document.querySelectorAll('.tab-content').forEach(content => {
                content.classList.remove('active');
            });

            // STEP 2: Add active to the correct tab button
            const targetButton = document.querySelector(`[data-tab="${tabName}"]`);
            if (targetButton) {
                targetButton.classList.add('active');
                console.log(`[TAB-FIX] Activated tab button: ${tabName}`);
            } else {
                console.warn(`[TAB-FIX] Tab button not found: ${tabName}`);
            }

            // STEP 3: Add active to the correct content
            const targetContent = document.getElementById(`${tabName}-tab`);
            if (targetContent) {
                targetContent.classList.add('active');
                console.log(`[TAB-FIX] Activated tab content: ${tabName}-tab`);

                // STEP 4: Special handling for File Tree
                if (tabName === 'claude-tree') {
                    // Ensure File Tree content is clean
                    const eventsInFileTree = targetContent.querySelectorAll('.event-item');
                    if (eventsInFileTree.length > 0) {
                        console.warn(`[TAB-FIX] Found ${eventsInFileTree.length} event items in File Tree, removing...`);
                        eventsInFileTree.forEach(item => item.remove());
                    }

                    // Trigger CodeViewer if available
                    if (window.CodeViewer && typeof window.CodeViewer.show === 'function') {
                        setTimeout(() => {
                            window.CodeViewer.show();
                        }, 100);
                    }
                }
            } else {
                console.warn(`[TAB-FIX] Tab content not found: ${tabName}-tab`);
            }

        } finally {
            setTimeout(() => {
                tabSwitchingInProgress = false;
            }, 200);
        }
    }

    // Override any existing tab switching
    function setupTabClickHandlers() {
        console.log('[TAB-FIX] Setting up click handlers...');

        document.querySelectorAll('.tab-button').forEach(button => {
            // Remove any existing listeners by cloning the element
            const newButton = button.cloneNode(true);
            button.parentNode.replaceChild(newButton, button);

            // Add our handler
            newButton.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();

                const tabName = this.getAttribute('data-tab');
                if (tabName) {
                    console.log(`[TAB-FIX] Tab clicked: ${tabName}`);
                    switchToTab(tabName);

                    // Update hash
                    const hashMap = {
                        'events': '#events',
                        'agents': '#agents',
                        'tools': '#tools',
                        'files': '#files',
                        'activity': '#activity',
                        'claude-tree': '#file_tree'
                    };
                    if (hashMap[tabName]) {
                        history.replaceState(null, null, hashMap[tabName]);
                    }
                } else {
                    console.warn('[TAB-FIX] No data-tab attribute found on button');
                }
            });
        });

        console.log(`[TAB-FIX] Set up handlers for ${document.querySelectorAll('.tab-button').length} tab buttons`);
    }

    // Handle hash navigation
    function handleHashNavigation() {
        const hash = window.location.hash;
        const hashToTab = {
            '#events': 'events',
            '#agents': 'agents',
            '#tools': 'tools',
            '#files': 'files',
            '#activity': 'activity',
            '#file_tree': 'claude-tree',
            '': 'events'
        };

        const tabName = hashToTab[hash] || 'events';
        console.log(`[TAB-FIX] Hash navigation: ${hash} -> ${tabName}`);
        switchToTab(tabName);
    }

    // Wait for tabs to be available
    function waitForTabsAndSetup() {
        const tabs = document.querySelectorAll('.tab-button');
        if (tabs.length > 0) {
            console.log(`[TAB-FIX] Found ${tabs.length} tabs, setting up handlers...`);
            setupTabClickHandlers();

            // Set up hash navigation
            window.addEventListener('hashchange', handleHashNavigation);

            // Handle initial hash
            setTimeout(handleHashNavigation, 100);

            console.log('[TAB-FIX] Bulletproof tab fix fully activated!');
        } else {
            console.log('[TAB-FIX] Tabs not ready yet, retrying in 500ms...');
            setTimeout(waitForTabsAndSetup, 500);
        }
    }

    // Start the setup process
    waitForTabsAndSetup();
}

// Export functions for global access
window.TabFix = {
    implement: implementTabFix,
    switchToTab: function(tabName) {
        // This will be available after implementTabFix is called
        const event = new CustomEvent('tabfix-switch', { detail: { tabName } });
        document.dispatchEvent(event);
    }
};

// Auto-implement when ready
whenReady(() => {
    console.log('[TAB-FIX] DOM ready, waiting 3 seconds for other scripts to load...');
    setTimeout(implementTabFix, 3000);
});