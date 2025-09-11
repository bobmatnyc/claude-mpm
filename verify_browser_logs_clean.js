#!/usr/bin/env node
/**
 * Script to verify that Browser Logs tab contains no hook events
 * Run this after triggering some hook events to confirm isolation
 */

const { chromium } = require('playwright');

async function verifyBrowserLogsClean() {
    console.log('🧪 Verifying Browser Logs tab is clean of hook events...\n');
    
    const browser = await chromium.launch({ 
        headless: false, // Set to true for CI
        slowMo: 100 // Slow down for visibility
    });
    
    const page = await browser.newPage();
    
    try {
        // Navigate to dashboard
        console.log('📍 Navigating to dashboard...');
        await page.goto('http://localhost:8765');
        await page.waitForLoadState('networkidle');
        
        // Click on Browser Logs tab
        console.log('🖱️ Clicking Browser Logs tab...');
        await page.click('button:has-text("Browser Logs")');
        await page.waitForTimeout(1000);
        
        // Check content of Browser Logs tab
        const browserLogsContent = await page.locator('#browser-logs-tab').textContent();
        console.log('\n📋 Browser Logs tab content:');
        console.log('-'.repeat(50));
        console.log(browserLogsContent.trim());
        console.log('-'.repeat(50));
        
        // Check for hook events
        const hasHookEvents = browserLogsContent.includes('[hook]') || 
                             browserLogsContent.includes('hook.pre_tool') ||
                             browserLogsContent.includes('hook.post_tool') ||
                             browserLogsContent.includes('hook.user_prompt');
        
        if (hasHookEvents) {
            console.log('\n❌ FAIL: Hook events found in Browser Logs tab!');
            
            // Take screenshot for evidence
            await page.screenshot({ 
                path: 'browser_logs_contamination.png',
                fullPage: true 
            });
            console.log('📸 Screenshot saved as browser_logs_contamination.png');
            
            return false;
        } else {
            console.log('\n✅ PASS: No hook events in Browser Logs tab!');
            
            // Check if it shows the correct empty state
            if (browserLogsContent.includes('No browser console logs yet')) {
                console.log('✅ Shows correct empty state message');
            }
            
            return true;
        }
        
    } catch (error) {
        console.error('❌ Error during verification:', error);
        return false;
    } finally {
        await browser.close();
    }
}

// For manual testing - can be run directly
if (require.main === module) {
    verifyBrowserLogsClean().then(success => {
        process.exit(success ? 0 : 1);
    });
}

module.exports = { verifyBrowserLogsClean };