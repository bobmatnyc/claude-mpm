const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: false });
  const context = await browser.newContext({ viewport: { width: 1920, height: 1080 } });
  const page = await context.newPage();

  page.on('console', msg => console.log(`[CONSOLE] ${msg.text()}`));

  try {
    await page.goto('http://localhost:8765', { waitUntil: 'networkidle' });
    await page.waitForTimeout(3000);

    // Click on the first pre_tool event
    const eventRow = await page.$('tr:has-text("pre_tool")');
    if (eventRow) {
      console.log('Clicking on pre_tool event...');
      await eventRow.click();
      await page.waitForTimeout(1000);

      // Get the JSON from the right panel
      const jsonContent = await page.textContent('body');

      // Try to extract tool_name
      const toolNameMatch = jsonContent.match(/"tool_name":\s*"([^"]+)"/);
      if (toolNameMatch) {
        console.log(`\nTool name found: "${toolNameMatch[1]}"`);
      }

      // Take screenshot showing the event details
      await page.screenshot({ path: 'event-detail.png', fullPage: true });
      console.log('Screenshot saved: event-detail.png');
    } else {
      console.log('No pre_tool event found');
    }

    await page.waitForTimeout(5000);
  } catch (error) {
    console.error('Error:', error);
  } finally {
    await browser.close();
  }
})();
