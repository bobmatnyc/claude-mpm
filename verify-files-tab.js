const { chromium } = require('playwright');

(async () => {
  console.log('Starting browser for Files tab verification...');
  const browser = await chromium.launch({ headless: false });
  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 }
  });
  const page = await context.newPage();

  // Track console messages
  const errors = [];
  page.on('console', msg => {
    if (msg.type() === 'error') {
      errors.push(msg.text());
    }
    console.log(`[CONSOLE ${msg.type()}] ${msg.text()}`);
  });

  try {
    console.log('Navigating to dashboard...');
    await page.goto('http://localhost:8765', { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);

    // Click on Files tab
    console.log('Clicking Files tab...');
    const filesTab = await page.$('button:has-text("Files")');
    if (filesTab) {
      await filesTab.click();
      await page.waitForTimeout(2000); // Wait for socket events to be processed
    } else {
      throw new Error('Files tab not found');
    }

    // Take screenshot
    await page.screenshot({ path: 'dashboard_files_panel.png', fullPage: true });
    console.log('Screenshot saved: dashboard_files_panel.png');

    // Check for files in the list
    const bodyText = await page.textContent('body');

    // Look for operation badges
    const hasReadBadge = bodyText.includes('READ') || bodyText.includes('read');
    const hasWriteBadge = bodyText.includes('WRITE') || bodyText.includes('write');
    const hasEditBadge = bodyText.includes('EDIT') || bodyText.includes('edit');

    // Look for specific files
    const hasPackageJson = bodyText.includes('package.json');
    const hasDashboardTest = bodyText.includes('dashboard-test.txt');

    // Count files
    const fileCountMatch = bodyText.match(/(\d+)\s+files?/);
    const fileCount = fileCountMatch ? parseInt(fileCountMatch[1]) : 0;

    console.log('\n=== FILES TAB VERIFICATION RESULTS ===');
    console.log(`File count: ${fileCount}`);
    console.log(`\nOperation badges found:`);
    console.log(`  - READ: ${hasReadBadge ? '✓' : '✗'}`);
    console.log(`  - WRITE: ${hasWriteBadge ? '✓' : '✗'}`);
    console.log(`  - EDIT: ${hasEditBadge ? '✓' : '✗'}`);
    console.log(`\nSpecific files found:`);
    console.log(`  - package.json: ${hasPackageJson ? '✓' : '✗'}`);
    console.log(`  - dashboard-test.txt: ${hasDashboardTest ? '✓' : '✗'}`);
    console.log(`\nConsole errors: ${errors.length}`);

    if (errors.length > 0) {
      console.log('\nErrors:');
      errors.forEach(err => console.log(`  - ${err}`));
    }

    // Try to click on a file if any exist
    if (fileCount > 0) {
      console.log('\nAttempting to click on a file...');
      const fileButton = await page.$('button[class*="border-l-"]');
      if (fileButton) {
        await fileButton.click();
        await page.waitForTimeout(1000);

        // Check if file content appeared
        const hasContent = await page.$('pre') || await page.$('code') || await page.$('[class*="content"]');
        console.log(`File content viewer appeared: ${hasContent ? '✓' : '✗'}`);

        // Take final screenshot
        await page.screenshot({ path: 'dashboard_file_selected.png', fullPage: true });
        console.log('Screenshot with file selected: dashboard_file_selected.png');
      }
    }

    console.log('\nKeeping browser open for 30 seconds for inspection...');
    await page.waitForTimeout(30000);

  } catch (error) {
    console.error('Error:', error);
    await page.screenshot({ path: 'error-files-tab.png', fullPage: true });
  } finally {
    await browser.close();
  }
})();
