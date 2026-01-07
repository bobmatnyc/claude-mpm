const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: false });
  const context = await browser.newContext({ viewport: { width: 1280, height: 800 } });
  const page = await context.newPage();

  try {
    console.log('Navigating to dashboard...');
    await page.goto('http://localhost:8765', { waitUntil: 'networkidle' });

    // Wait for the page to be fully loaded
    await page.waitForTimeout(2000);

    // Create directory for screenshots
    const fs = require('fs');
    const screenshotDir = '/Users/masa/Projects/claude-mpm/test-results';
    if (!fs.existsSync(screenshotDir)) {
      fs.mkdirSync(screenshotDir, { recursive: true });
    }

    // 1. Capture Events tab
    console.log('Capturing Events tab...');
    const eventsTab = page.locator('button:has-text("Events")').first();
    await eventsTab.click();
    await page.waitForTimeout(1000);
    await page.screenshot({ path: `${screenshotDir}/events-tab.png`, fullPage: true });
    console.log('Events tab screenshot saved');

    // 2. Capture Tools tab
    console.log('Capturing Tools tab...');
    const toolsTab = page.locator('button:has-text("Tools")').first();
    await toolsTab.click();
    await page.waitForTimeout(1000);
    await page.screenshot({ path: `${screenshotDir}/tools-tab.png`, fullPage: true });
    console.log('Tools tab screenshot saved');

    // 3. Capture Files tab
    console.log('Capturing Files tab...');
    const filesTab = page.locator('button:has-text("Files")').first();
    await filesTab.click();
    await page.waitForTimeout(1000);
    await page.screenshot({ path: `${screenshotDir}/files-tab.png`, fullPage: true });
    console.log('Files tab screenshot saved');

    // 4. Check if Files tab has data and try to open a file
    console.log('Checking Files tab content...');
    const fileRows = await page.locator('tr[data-file-path]').count();
    console.log(`Found ${fileRows} file rows`);

    if (fileRows > 0) {
      console.log('Attempting to open first file...');
      const firstFileRow = page.locator('tr[data-file-path]').first();
      await firstFileRow.click();
      await page.waitForTimeout(1500);

      // Check if modal appeared
      const modal = page.locator('[role="dialog"]');
      const modalVisible = await modal.isVisible().catch(() => false);

      if (modalVisible) {
        console.log('File viewer modal opened successfully');
        await page.screenshot({ path: `${screenshotDir}/file-modal.png`, fullPage: true });
        console.log('File modal screenshot saved');

        // Close modal
        const closeButton = page.locator('button:has-text("Close")').or(page.locator('[aria-label="Close"]'));
        await closeButton.click().catch(() => console.log('No close button found'));
        await page.waitForTimeout(500);
      } else {
        console.log('File viewer modal did not appear');
      }
    } else {
      console.log('No files found in Files tab - empty state');
    }

    // 5. Analyze layout structure for each tab
    console.log('\n=== Layout Analysis ===');

    // Switch to each tab and analyze structure
    for (const tabName of ['Events', 'Tools', 'Files']) {
      const tab = page.locator(`button:has-text("${tabName}")`).first();
      await tab.click();
      await page.waitForTimeout(500);

      console.log(`\n${tabName} Tab Structure:`);

      // Check for header
      const headers = await page.locator('h2, h3').allTextContents();
      console.log(`  Headers: ${headers.join(', ')}`);

      // Check for table
      const hasTable = await page.locator('table').isVisible().catch(() => false);
      console.log(`  Has table: ${hasTable}`);

      // Check for empty state
      const emptyState = await page.locator('text=/no (events|tools|files)/i').isVisible().catch(() => false);
      console.log(`  Empty state: ${emptyState}`);

      // Count rows
      const rowCount = await page.locator('tbody tr').count();
      console.log(`  Row count: ${rowCount}`);
    }

    console.log('\n=== Verification Complete ===');
    console.log('Screenshots saved to test-results/');

  } catch (error) {
    console.error('Error during verification:', error);
  } finally {
    await browser.close();
  }
})();
