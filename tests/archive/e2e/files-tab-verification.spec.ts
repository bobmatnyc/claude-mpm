import { test, expect } from '@playwright/test';

test.describe('Files Tab Verification', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the dashboard
    await page.goto('http://localhost:8765');
    await page.waitForLoadState('networkidle');
  });

  test('should display files in Files tab', async ({ page }) => {
    // Click on Files tab
    await page.click('text=Files');

    // Wait for the Files tab content to be visible
    await page.waitForTimeout(1000);

    // Take screenshot of the Files tab
    await page.screenshot({
      path: 'test-results/files-tab-initial.png',
      fullPage: true
    });

    // Check if files are listed
    const fileList = page.locator('[data-testid="file-list"], .file-list, ul li, .file-item');
    const fileCount = await fileList.count();

    console.log(`Found ${fileCount} file elements in the list`);

    // Look for specific files
    const pythonFile = page.locator('text=__init__.py');
    const jsonFile = page.locator('text=package.json');
    const markdownFile = page.locator('text=README.md');

    const hasPythonFile = await pythonFile.isVisible().catch(() => false);
    const hasJsonFile = await jsonFile.isVisible().catch(() => false);
    const hasMarkdownFile = await markdownFile.isVisible().catch(() => false);

    console.log('File visibility:');
    console.log(`- __init__.py: ${hasPythonFile}`);
    console.log(`- package.json: ${hasJsonFile}`);
    console.log(`- README.md: ${hasMarkdownFile}`);
  });

  test('should display Python file content with syntax highlighting', async ({ page }) => {
    await page.click('text=Files');
    await page.waitForTimeout(500);

    // Try to click on __init__.py
    const pythonFile = page.locator('text=__init__.py').first();
    const isVisible = await pythonFile.isVisible().catch(() => false);

    if (isVisible) {
      await pythonFile.click();
      await page.waitForTimeout(1000);

      // Take screenshot of Python file content
      await page.screenshot({
        path: 'test-results/python-file-content.png',
        fullPage: true
      });

      // Check for syntax highlighting elements
      const codeBlock = page.locator('pre, code, .hljs, .shiki, [class*="highlight"]');
      const hasCodeBlock = await codeBlock.isVisible().catch(() => false);
      console.log(`Python syntax highlighting present: ${hasCodeBlock}`);

      if (hasCodeBlock) {
        const html = await codeBlock.first().innerHTML();
        console.log('Code block HTML preview:', html.substring(0, 200));
      }
    } else {
      console.log('Python file not found in the list');
      await page.screenshot({
        path: 'test-results/python-file-not-found.png',
        fullPage: true
      });
    }
  });

  test('should display JSON file content with syntax highlighting', async ({ page }) => {
    await page.click('text=Files');
    await page.waitForTimeout(500);

    // Try to click on package.json
    const jsonFile = page.locator('text=package.json').first();
    const isVisible = await jsonFile.isVisible().catch(() => false);

    if (isVisible) {
      await jsonFile.click();
      await page.waitForTimeout(1000);

      // Take screenshot of JSON file content
      await page.screenshot({
        path: 'test-results/json-file-content.png',
        fullPage: true
      });

      // Check for syntax highlighting
      const codeBlock = page.locator('pre, code, .hljs, .shiki, [class*="highlight"]');
      const hasCodeBlock = await codeBlock.isVisible().catch(() => false);
      console.log(`JSON syntax highlighting present: ${hasCodeBlock}`);

      if (hasCodeBlock) {
        const html = await codeBlock.first().innerHTML();
        console.log('Code block HTML preview:', html.substring(0, 200));
      }
    } else {
      console.log('JSON file not found in the list');
      await page.screenshot({
        path: 'test-results/json-file-not-found.png',
        fullPage: true
      });
    }
  });

  test('should display Markdown file content', async ({ page }) => {
    await page.click('text=Files');
    await page.waitForTimeout(500);

    // Try to click on README.md
    const markdownFile = page.locator('text=README.md').first();
    const isVisible = await markdownFile.isVisible().catch(() => false);

    if (isVisible) {
      await markdownFile.click();
      await page.waitForTimeout(1000);

      // Take screenshot of Markdown file content
      await page.screenshot({
        path: 'test-results/markdown-file-content.png',
        fullPage: true
      });

      // Check for content display
      const contentArea = page.locator('pre, code, .markdown, [class*="content"]');
      const hasContent = await contentArea.isVisible().catch(() => false);
      console.log(`Markdown content present: ${hasContent}`);
    } else {
      console.log('Markdown file not found in the list');
      await page.screenshot({
        path: 'test-results/markdown-file-not-found.png',
        fullPage: true
      });
    }
  });

  test('comprehensive Files tab inspection', async ({ page }) => {
    await page.click('text=Files');
    await page.waitForTimeout(1000);

    // Get the entire page content
    const bodyHTML = await page.content();

    // Take full page screenshot
    await page.screenshot({
      path: 'test-results/files-tab-full-page.png',
      fullPage: true
    });

    // Check for any text indicating files
    const pageText = await page.textContent('body');
    console.log('\n=== Files Tab Content Analysis ===');
    console.log('Page contains "__init__.py":', pageText?.includes('__init__.py'));
    console.log('Page contains "package.json":', pageText?.includes('package.json'));
    console.log('Page contains "README.md":', pageText?.includes('README.md'));
    console.log('Page contains "No files":', pageText?.includes('No files'));
    console.log('Page contains "empty":', pageText?.includes('empty'));

    // Save HTML for manual inspection
    const fs = require('fs');
    const path = require('path');
    const resultsDir = path.join(process.cwd(), 'test-results');
    if (!fs.existsSync(resultsDir)) {
      fs.mkdirSync(resultsDir, { recursive: true });
    }
    fs.writeFileSync(
      path.join(resultsDir, 'files-tab-content.html'),
      bodyHTML
    );
    console.log('HTML content saved to test-results/files-tab-content.html');
  });
});
