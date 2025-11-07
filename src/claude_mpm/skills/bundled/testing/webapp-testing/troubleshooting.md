# Troubleshooting Reference

Complete guide to diagnosing and solving common webapp testing problems.

## Table of Contents

- [Timeout Issues](#timeout-issues)
- [Selector Issues](#selector-issues)
- [Server Issues](#server-issues)
- [Network Issues](#network-issues)
- [Environment Issues](#environment-issues)
- [Playwright-Specific Issues](#playwright-specific-issues)
- [Performance Issues](#performance-issues)
- [Debugging Workflow](#debugging-workflow)

## Timeout Issues

### Symptom: page.goto() Timeout

**Error message:**
```
TimeoutError: page.goto: Timeout 30000ms exceeded
```

**Possible causes and solutions:**

**1. Server not running**
```bash
# Check server status
lsof -i :3000 -sTCP:LISTEN

# If no output, start server
python scripts/with_server.py --server "npm start" --port 3000 -- python test.py
```

**2. Server slow to respond**
```bash
# Check response time
curl -w "Time: %{time_total}s\n" -o /dev/null -s http://localhost:3000

# If slow, increase timeout
page.goto('http://localhost:3000', timeout=60000)  # 60 seconds
```

**3. Network connectivity issue**
```bash
# Test connection
curl http://localhost:3000

# Try different host format
page.goto('http://127.0.0.1:3000')  # Instead of localhost
```

**4. Port incorrect**
```bash
# List all listening ports
lsof -i -sTCP:LISTEN

# Use correct port
page.goto('http://localhost:CORRECT_PORT')
```

### Symptom: wait_for_selector() Timeout

**Error message:**
```
TimeoutError: waiting for selector "button.submit" failed: timeout 30000ms exceeded
```

**Possible causes and solutions:**

**1. Page not fully loaded**
```python
# ❌ BAD: Missing wait
page.goto('http://localhost:3000')
page.click('button.submit')  # Fails

# ✅ GOOD: Wait for networkidle
page.goto('http://localhost:3000')
page.wait_for_load_state('networkidle')
page.click('button.submit')  # Works
```

**2. Selector doesn't match**
```python
# Take screenshot to see actual page
page.screenshot(path='/tmp/debug.png', full_page=True)

# Inspect DOM
content = page.content()
print('button' in content.lower())  # Does 'button' exist?

# Try different selector
page.wait_for_selector('text=Submit')  # Text selector
page.wait_for_selector('role=button')   # Role selector
```

**3. Element conditionally rendered**
```python
# Check if element appears after action
page.click('text=Show Form')
page.wait_for_selector('button.submit')  # Now appears

# Or check application state
page.wait_for_function('() => window.formReady === true')
page.wait_for_selector('button.submit')
```

**4. Element in iframe**
```python
# Regular selector won't work for iframe content
# ❌ page.wait_for_selector('.iframe-button')

# ✅ Access iframe first
frame = page.frame_locator('iframe#myframe')
frame.locator('.iframe-button').wait_for()
```

### Symptom: wait_for_load_state('networkidle') Never Completes

**Error message:**
```
TimeoutError: page.wait_for_load_state: Timeout 30000ms exceeded
```

**Possible causes and solutions:**

**1. Polling API or WebSocket**
```python
# Page constantly makes requests, never idle
# ❌ page.wait_for_load_state('networkidle')

# ✅ Use 'load' instead
page.wait_for_load_state('load')

# Or wait for specific element
page.wait_for_selector('.content')
```

**2. Long-running request**
```python
# Some API call takes very long
# ✅ Wait for specific element instead
page.wait_for_selector('.data-loaded')

# Or increase timeout
page.wait_for_load_state('networkidle', timeout=60000)
```

**3. Failed request keeps retrying**
```python
# Check console for errors
page.on("console", lambda msg: print(f"[{msg.type}] {msg.text}"))

# Check network errors
def handle_response(response):
    if response.status >= 400:
        print(f"Failed: {response.url} - {response.status}")
page.on("response", handle_response)
```

## Selector Issues

### Symptom: Element Not Found

**Error message:**
```
Error: Element not found
```

**Diagnosis and solutions:**

**1. Verify element exists in DOM**
```python
# Get full HTML
content = page.content()

# Search for expected text/class/id
print('submit' in content.lower())
print('class="submit"' in content)
print('id="submit-button"' in content)

# Save HTML for inspection
with open('/tmp/page.html', 'w') as f:
    f.write(content)
```

**2. Try different selector strategies**
```python
# Text selector (most readable)
page.click('text=Submit')

# Role selector (semantic)
page.click('role=button[name="Submit"]')

# CSS selector
page.click('button.submit')
page.click('#submit-button')

# Data attribute (most stable)
page.click('[data-testid="submit"]')

# XPath (last resort)
page.click('xpath=//button[contains(text(), "Submit")]')
```

**3. Count matching elements**
```python
# How many elements match?
elements = page.locator('button').all()
print(f"Found {len(elements)} buttons:")
for i, btn in enumerate(elements):
    text = btn.inner_text() if btn.is_visible() else "[hidden]"
    print(f"  [{i}] {text}")

# If multiple matches, make selector more specific
page.click('form.login >> button.submit')
```

### Symptom: Element Not Visible

**Error message:**
```
Error: Element is not visible
```

**Diagnosis and solutions:**

**1. Check if element exists but hidden**
```python
# Check visibility
element = page.locator('button.submit')
print(f"Exists: {element.count() > 0}")
print(f"Visible: {element.is_visible()}")

# Check CSS
print(f"Display: {element.evaluate('el => getComputedStyle(el).display')}")
print(f"Visibility: {element.evaluate('el => getComputedStyle(el).visibility')}")
```

**2. Scroll element into view**
```python
# Element might be below fold
page.locator('button.submit').scroll_into_view_if_needed()
page.click('button.submit')
```

**3. Wait for element to become visible**
```python
# Element may be hidden initially
page.wait_for_selector('button.submit', state='visible')
page.click('button.submit')
```

**4. Check for overlapping elements**
```python
# Take screenshot to see layout
page.screenshot(path='/tmp/layout.png')

# Check if modal/overlay is blocking
page.wait_for_selector('.modal', state='hidden')
page.click('button.submit')

# Or force click (bypass visibility check)
page.click('button.submit', force=True)
```

### Symptom: Stale Element

**Error message:**
```
Error: Element is not attached to the DOM
```

**Solution:**
```python
# Don't store element references across page changes
# ❌ BAD
button = page.locator('button.submit')
page.goto('http://localhost:3000/other')
button.click()  # Stale element

# ✅ GOOD
page.goto('http://localhost:3000/other')
page.locator('button.submit').click()  # Query again
```

## Server Issues

### Symptom: Port Already in Use

**Error message:**
```
Error: listen EADDRINUSE: address already in use :::3000
```

**Diagnosis and solutions:**

**1. Find process using port**
```bash
# macOS/Linux
lsof -i :3000

# Get PID
lsof -t -i :3000
```

**2. Kill process**
```bash
# Graceful kill
lsof -t -i :3000 | xargs kill

# Force kill if needed
lsof -t -i :3000 | xargs kill -9
```

**3. Use different port**
```bash
# Node.js
PORT=3001 npm start

# Python
python manage.py runserver 3001

# Update test
page.goto('http://localhost:3001')
```

### Symptom: Server Crashes During Test

**Error message:**
```
Error: Connection refused / ECONNREFUSED
```

**Diagnosis and solutions:**

**1. Check if process still running**
```bash
# Check by port
lsof -i :3000

# Check by process name
ps aux | grep node
ps aux | grep python
```

**2. Check server logs**
```bash
# If started with with_server.py, check stderr
python scripts/with_server.py --server "npm start" --port 3000 -- python test.py 2>&1 | tee full.log

# Check application log file
tail -f server.log
tail -f /tmp/server.log
```

**3. Common crash causes**
```python
# Memory leak
# Solution: Restart server between test suites

# Unhandled exception
# Solution: Add error handling in server code

# Database connection lost
# Solution: Implement connection pooling and retry logic

# Port conflict
# Solution: Use unique port for each test run
```

### Symptom: Server Won't Start

**Error message:**
```
RuntimeError: Server failed to start on port 3000 within 30s
```

**Diagnosis and solutions:**

**1. Check startup logs**
```bash
# Start server manually to see errors
npm start
python manage.py runserver

# Look for:
# - Missing dependencies
# - Configuration errors
# - Permission issues
```

**2. Increase timeout**
```bash
# Server might be slow to start
python scripts/with_server.py --server "npm start" --port 3000 --timeout 60 -- python test.py
```

**3. Check dependencies**
```bash
# Node.js
npm install

# Python
pip install -r requirements.txt

# Check for peer dependency warnings
npm ls
```

## Network Issues

### Symptom: CORS Error

**Error in console:**
```
Access to fetch at 'http://localhost:4000/api' from origin 'http://localhost:3000'
has been blocked by CORS policy
```

**Solutions:**

**1. Configure server CORS (development)**
```javascript
// Express.js
const cors = require('cors');
app.use(cors());

// Or specific origin
app.use(cors({
  origin: 'http://localhost:3000'
}));
```

**2. Use proxy in development**
```javascript
// package.json (Create React App)
{
  "proxy": "http://localhost:4000"
}

// Now fetch('/api/data') goes to http://localhost:4000/api/data
```

**3. Start servers on same origin (testing)**
```bash
# Use reverse proxy or configure servers to run on same port with different paths
```

### Symptom: Request Timeout

**Error message:**
```
TimeoutError: waiting for response to **/api/data
```

**Diagnosis and solutions:**

**1. Check API server is running**
```bash
# If using multiple servers
python scripts/with_server.py \
  --server "cd backend && npm start" --port 4000 \
  --server "cd frontend && npm start" --port 3000 \
  -- python test.py
```

**2. Check response time**
```bash
curl -w "Time: %{time_total}s\n" http://localhost:4000/api/data
```

**3. Increase timeout**
```python
# Wait for slow API
with page.expect_response('**/api/data', timeout=60000) as response_info:
    page.click('button.load')
```

**4. Mock slow API**
```python
# Mock API for faster tests
def handle_route(route):
    route.fulfill(
        status=200,
        body='{"data": "mocked"}',
        headers={'Content-Type': 'application/json'}
    )

page.route('**/api/data', handle_route)
```

### Symptom: SSL/TLS Error

**Error message:**
```
Error: certificate not trusted
```

**Solutions:**

**1. Use HTTP for local development**
```python
page.goto('http://localhost:3000')  # Not https://
```

**2. Ignore HTTPS errors (testing only)**
```python
browser = p.chromium.launch(headless=True)
context = browser.new_context(ignore_https_errors=True)
page = context.new_page()
```

## Environment Issues

### Symptom: Missing Environment Variables

**Error in server logs:**
```
Error: DATABASE_URL is not defined
```

**Solutions:**

**1. Create .env file**
```bash
# .env
PORT=3000
NODE_ENV=development
DATABASE_URL=postgresql://localhost/mydb
API_KEY=test123
```

**2. Load environment variables**
```bash
# Node.js with dotenv
npm install dotenv

# In server code
require('dotenv').config();

# Python with python-dotenv
pip install python-dotenv

# In server code
from dotenv import load_dotenv
load_dotenv()
```

**3. Set environment variables before starting**
```bash
# Linux/macOS
export PORT=3000
npm start

# Windows
set PORT=3000
npm start

# Or inline
PORT=3000 npm start
```

### Symptom: Wrong Node/Python Version

**Error message:**
```
SyntaxError: Unexpected token '??' (nullish coalescing)
```

**Solutions:**

**1. Check version**
```bash
node --version
python --version
```

**2. Use correct version**
```bash
# Node.js with nvm
nvm install 18
nvm use 18

# Python with pyenv
pyenv install 3.11
pyenv local 3.11
```

**3. Check project requirements**
```json
// package.json
{
  "engines": {
    "node": ">=18.0.0"
  }
}
```

## Playwright-Specific Issues

### Symptom: Browser Download Failed

**Error message:**
```
Error: Executable doesn't exist at /path/to/browsers/chromium-xxx
```

**Solution:**
```bash
# Install browsers
playwright install chromium

# Or all browsers
playwright install

# With specific version
pip install playwright==1.40.0
playwright install chromium
```

### Symptom: Headless vs Headed Differences

**Issue:** Test passes in headless but fails in headed (or vice versa)

**Solutions:**

**1. Viewport size differences**
```python
# Set consistent viewport
page.set_viewport_size({'width': 1920, 'height': 1080})
```

**2. Timing differences**
```python
# Headed mode is often slower
# Always use wait_for_load_state
page.wait_for_load_state('networkidle')
```

**3. Debug with headed mode**
```python
# Run in headed to see what's happening
browser = p.chromium.launch(headless=False, slow_mo=1000)
```

### Symptom: Element Screenshot is Blank

**Issue:** `element.screenshot()` produces blank image

**Solutions:**

**1. Wait for element to be visible**
```python
element = page.locator('.chart')
element.wait_for()
page.wait_for_timeout(500)  # Wait for rendering
element.screenshot(path='/tmp/chart.png')
```

**2. Check element has size**
```python
box = element.bounding_box()
print(f"Size: {box['width']}x{box['height']}")
```

**3. Capture full page instead**
```python
page.screenshot(path='/tmp/full.png', full_page=True)
```

## Performance Issues

### Symptom: Tests Run Very Slowly

**Diagnosis and solutions:**

**1. Remove unnecessary waits**
```python
# ❌ BAD: Fixed delays
page.click('button')
page.wait_for_timeout(5000)  # Slow!

# ✅ GOOD: Wait for specific condition
page.click('button')
page.wait_for_selector('.result')  # Fast
```

**2. Use networkidle only when needed**
```python
# For static pages or SSR
page.wait_for_load_state('load')  # Faster than networkidle

# For dynamic pages with APIs
page.wait_for_load_state('networkidle')  # Necessary
```

**3. Block unnecessary resources**
```python
# Block images, fonts, stylesheets for faster tests
page.route('**/*.{png,jpg,jpeg,gif,svg,woff,woff2,ttf,css}', lambda route: route.abort())
```

**4. Reuse browser context**
```python
# ❌ Slow: New browser per test
def test_1():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        # ...

# ✅ Fast: Reuse browser
@pytest.fixture(scope="session")
def browser():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        yield browser
```

### Symptom: High Memory Usage

**Solutions:**

**1. Close pages after use**
```python
page = browser.new_page()
# ... test ...
page.close()
```

**2. Clear context between tests**
```python
@pytest.fixture
def context(browser):
    context = browser.new_context()
    yield context
    context.close()
```

**3. Limit parallel tests**
```bash
# Don't run too many in parallel
pytest -n 4  # Limit to 4 workers
```

## Debugging Workflow

### Step 1: Reproduce the Issue

```python
# Create minimal reproduction script
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    # Minimal steps to reproduce
    page.goto('http://localhost:3000')
    page.wait_for_load_state('networkidle')
    page.click('button.submit')  # Fails here

    browser.close()
```

### Step 2: Gather Evidence

```python
# Add reconnaissance
page.goto('http://localhost:3000')
page.wait_for_load_state('networkidle')

# Screenshot
page.screenshot(path='/tmp/before-click.png', full_page=True)

# Console logs
console_logs = []
page.on("console", lambda msg: console_logs.append(f"[{msg.type}] {msg.text}"))

# DOM content
with open('/tmp/dom.html', 'w') as f:
    f.write(page.content())

# Try action
try:
    page.click('button.submit')
except Exception as e:
    print(f"Error: {e}")
    page.screenshot(path='/tmp/error.png', full_page=True)

# Save console logs
with open('/tmp/console.log', 'w') as f:
    f.write('\n'.join(console_logs))
```

### Step 3: Analyze Evidence

```bash
# View screenshots
open /tmp/before-click.png
open /tmp/error.png

# Search DOM
grep -i "submit" /tmp/dom.html
grep -i "button" /tmp/dom.html

# Check console
cat /tmp/console.log | grep -i error
```

### Step 4: Form Hypothesis

Based on evidence:
- Screenshot shows page loaded correctly? → Selector issue
- Screenshot shows blank page? → Loading issue
- Screenshot shows error message? → Server issue
- Console shows errors? → JavaScript issue
- Element exists in DOM but not visible? → CSS issue

### Step 5: Test Hypothesis

```python
# Hypothesis: Selector is wrong
# Test: Try different selectors
page.click('text=Submit')  # Try text
page.click('role=button')  # Try role
page.click('#submit')      # Try ID

# Hypothesis: Need to wait longer
# Test: Add explicit wait
page.wait_for_selector('button.submit', state='visible')
page.click('button.submit')

# Hypothesis: Element obscured
# Test: Force click
page.click('button.submit', force=True)
```

### Step 6: Verify Fix

```python
# Once fixed, verify with full test
page.goto('http://localhost:3000')
page.wait_for_load_state('networkidle')
page.wait_for_selector('button.submit', state='visible')
page.click('button.submit')
page.wait_for_selector('.success-message')
print("✅ Test passed")
```

### Step 7: Prevent Regression

```python
# Add to test suite with proper waits and assertions
def test_submit_button():
    page.goto('http://localhost:3000')
    page.wait_for_load_state('networkidle')

    # Verify button exists and is clickable
    submit_btn = page.locator('button.submit')
    expect(submit_btn).to_be_visible()
    expect(submit_btn).to_be_enabled()

    # Click and verify result
    submit_btn.click()
    expect(page.locator('.success-message')).to_be_visible()
```
