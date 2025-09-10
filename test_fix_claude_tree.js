// Debug script to test the Claude Tree tab fix
// Run this in the browser console when the dashboard is open

function debugClaudeTreeTab() {
    console.log('=== Claude Tree Tab Debug ===');
    
    // 1. Check if multiple tabs are active
    const activeTabs = document.querySelectorAll('.tab-content.active');
    console.log('Active tabs:', activeTabs.length);
    activeTabs.forEach(tab => {
        console.log('  - Active tab ID:', tab.id);
    });
    
    // 2. Check the Claude Tree tab specifically
    const claudeTreeTab = document.getElementById('claude-tree-tab');
    console.log('Claude Tree tab found:', !!claudeTreeTab);
    console.log('Claude Tree tab active:', claudeTreeTab?.classList.contains('active'));
    
    // 3. Check the Claude Tree container
    const claudeTreeContainer = document.getElementById('claude-tree-container');
    console.log('Claude Tree container found:', !!claudeTreeContainer);
    if (claudeTreeContainer) {
        console.log('Container parent:', claudeTreeContainer.parentElement?.id);
        console.log('Container HTML (first 500 chars):', claudeTreeContainer.innerHTML.substring(0, 500));
        
        // Check for event items
        const eventItems = claudeTreeContainer.querySelectorAll('.event-item');
        console.log('Event items in container:', eventItems.length);
        
        // Check for tree elements
        const svgElements = claudeTreeContainer.querySelectorAll('svg');
        console.log('SVG elements in container:', svgElements.length);
    }
    
    // 4. Check Events tab
    const eventsTab = document.getElementById('events-tab');
    console.log('Events tab active:', eventsTab?.classList.contains('active'));
    
    // 5. Check if CodeViewer is available
    console.log('CodeViewer available:', !!window.CodeViewer);
    
    // 6. Try to manually trigger CodeViewer
    if (window.CodeViewer) {
        console.log('Manually triggering CodeViewer.show()...');
        window.CodeViewer.show();
        
        // Check after a delay
        setTimeout(() => {
            const container = document.getElementById('claude-tree-container');
            console.log('After show() - Container HTML (first 500 chars):', 
                container?.innerHTML.substring(0, 500));
        }, 1000);
    }
    
    // 7. Check CSS computed styles
    if (claudeTreeTab) {
        const computedStyle = window.getComputedStyle(claudeTreeTab);
        console.log('Claude Tree tab display:', computedStyle.display);
        console.log('Claude Tree tab visibility:', computedStyle.visibility);
        console.log('Claude Tree tab z-index:', computedStyle.zIndex);
    }
    
    // 8. Check for overlapping elements
    if (claudeTreeContainer) {
        const rect = claudeTreeContainer.getBoundingClientRect();
        const elementsAtPoint = document.elementsFromPoint(
            rect.left + rect.width/2, 
            rect.top + rect.height/2
        );
        console.log('Elements at center of Claude Tree container:');
        elementsAtPoint.forEach(el => {
            if (el.id || el.className) {
                console.log('  -', el.tagName, 'id:', el.id, 'class:', el.className);
            }
        });
    }
}

// Run the debug function
debugClaudeTreeTab();

console.log('\n=== Fix Applied ===');
console.log('The CodeViewer has been updated to:');
console.log('1. Clear any event items when show() is called');
console.log('2. Properly render the D3.js tree interface');
console.log('3. Add debug logging to trace the issue');
console.log('\nPlease refresh the page (Ctrl+R or Cmd+R) to load the updated code');
console.log('Then click on the Claude Tree tab to test the fix');