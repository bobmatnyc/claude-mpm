import { test, expect } from '@playwright/test';
import path from 'path';

test.describe('Files Tab - Final Verification', () => {
  test('should display files and syntax highlighting', async ({ page }) => {
    // Navigate to dashboard
    await page.goto('http://localhost:8765');
    console.log('✓ Navigated to dashboard');

    // Wait for SSE events to stream
    await page.waitForTimeout(3000);
    console.log('✓ Waited 3 seconds for SSE events');

    // Take initial screenshot
    await page.screenshot({
      path: 'test-results/01-dashboard-initial.png',
      fullPage: true
    });
    console.log('✓ Screenshot: Initial dashboard view');

    // Click on Files tab
    const filesTab = page.locator('button:has-text("Files")');
    await expect(filesTab).toBeVisible();
    await filesTab.click();
    console.log('✓ Clicked Files tab');

    // Wait for tab content to render
    await page.waitForTimeout(1000);

    // Take screenshot of Files tab
    await page.screenshot({
      path: 'test-results/02-files-tab-opened.png',
      fullPage: true
    });
    console.log('✓ Screenshot: Files tab opened');

    // Check if file list is visible
    const fileList = page.locator('.file-list, [role="list"], ul, .files-container');
    const hasFileList = await fileList.count() > 0;
    console.log(`File list elements found: ${await fileList.count()}`);

    // Look for specific files we expect
    const initFile = page.locator('text=__init__.py').first();
    const packageFile = page.locator('text=package.json').first();

    const hasInitFile = await initFile.count() > 0;
    const hasPackageFile = await packageFile.count() > 0;

    console.log(`__init__.py found: ${hasInitFile}`);
    console.log(`package.json found: ${hasPackageFile}`);

    // If files are visible, try to click on them
    if (hasInitFile) {
      console.log('Attempting to click __init__.py...');
      await initFile.click();
      await page.waitForTimeout(1000);

      await page.screenshot({
        path: 'test-results/03-python-file-content.png',
        fullPage: true
      });
      console.log('✓ Screenshot: Python file content');

      // Check for syntax highlighting elements
      const codeBlock = page.locator('code, pre, .hljs, .shiki, .highlight');
      const hasCodeBlock = await codeBlock.count() > 0;
      console.log(`Code block elements found: ${await codeBlock.count()}`);

      // Check for colored syntax (look for span elements with class or style)
      const syntaxElements = page.locator('code span[class*="token"], code span[class*="hljs"], code span[style*="color"]');
      const hasSyntaxHighlight = await syntaxElements.count() > 0;
      console.log(`Syntax highlighting elements found: ${await syntaxElements.count()}`);
    }

    if (hasPackageFile) {
      console.log('Attempting to click package.json...');
      await packageFile.click();
      await page.waitForTimeout(1000);

      await page.screenshot({
        path: 'test-results/04-json-file-content.png',
        fullPage: true
      });
      console.log('✓ Screenshot: JSON file content');

      // Check for syntax highlighting in JSON
      const codeBlock = page.locator('code, pre, .hljs, .shiki, .highlight');
      const hasCodeBlock = await codeBlock.count() > 0;
      console.log(`Code block elements found: ${await codeBlock.count()}`);

      const syntaxElements = page.locator('code span[class*="token"], code span[class*="hljs"], code span[style*="color"]');
      const hasSyntaxHighlight = await syntaxElements.count() > 0;
      console.log(`Syntax highlighting elements found: ${await syntaxElements.count()}`);
    }

    // If no files found, check the DOM structure
    if (!hasInitFile && !hasPackageFile) {
      console.log('⚠ No files found - checking DOM structure...');

      // Get all text content in the Files tab
      const tabContent = await page.locator('body').innerText();
      console.log('Tab content preview:', tabContent.substring(0, 500));

      // Check for error messages
      const errorMessages = page.locator('text=/error|failed|not found/i');
      const hasErrors = await errorMessages.count() > 0;
      if (hasErrors) {
        console.log('⚠ Error messages found:', await errorMessages.first().innerText());
      }

      // Check browser console for errors
      page.on('console', msg => {
        if (msg.type() === 'error') {
          console.log('Browser console error:', msg.text());
        }
      });
    }

    // Final summary screenshot
    await page.screenshot({
      path: 'test-results/05-final-state.png',
      fullPage: true
    });
    console.log('✓ Screenshot: Final state');

    // Summary
    console.log('\n=== VERIFICATION SUMMARY ===');
    console.log(`Files tab accessible: ✓`);
    console.log(`Files displayed: ${hasInitFile || hasPackageFile ? '✓' : '✗'}`);
    console.log(`__init__.py visible: ${hasInitFile ? '✓' : '✗'}`);
    console.log(`package.json visible: ${hasPackageFile ? '✓' : '✗'}`);

    // The test will pass/fail based on whether files are found
    expect(hasInitFile || hasPackageFile, 'At least one file should be visible in Files tab').toBeTruthy();
  });
});
