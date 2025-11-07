# Decision Tree Reference

Complete flowcharts and decision guides for webapp testing scenarios.

## Table of Contents

- [Start Here: New Test Decision Tree](#start-here-new-test-decision-tree)
- [Server State Decision Tree](#server-state-decision-tree)
- [Test Failure Decision Tree](#test-failure-decision-tree)
- [Debugging Decision Tree](#debugging-decision-tree)
- [Selector Strategy Decision Tree](#selector-strategy-decision-tree)
- [Wait Strategy Decision Tree](#wait-strategy-decision-tree)
- [Environment Selection Decision Tree](#environment-selection-decision-tree)
- [Testing Approach Decision Tree](#testing-approach-decision-tree)

## Start Here: New Test Decision Tree

```
User requests webapp testing
        ↓
    Is it a local webapp?
    ├─ No → Ask for deployment URL
    │       ├─ Public URL → Test directly with Playwright
    │       └─ Private URL → Configure authentication first
    │
    └─ Yes → What type of webapp?
            ├─ Static HTML file
            │   ├─ Read HTML source directly
            │   │   ├─ Can identify selectors? → Write test
            │   │   └─ Need to see rendered? → Use file:// URL
            │   └─ Write Playwright script with file:// URL
            │
            ├─ Dynamic webapp (React, Vue, Angular, etc.)
            │   └─ Is server already running?
            │       ├─ Yes → Check server status
            │       │       ├─ lsof -i :PORT shows LISTEN
            │       │       │   └─ curl http://localhost:PORT succeeds
            │       │       │       └─ Write Playwright test
            │       │       └─ Server not responding
            │       │           └─ Restart server
            │       │
            │       └─ No → Need to start server
            │               ├─ Single server
            │               │   └─ Use with_server.py:
            │               │       python scripts/with_server.py \
            │               │         --server "npm start" --port 3000 \
            │               │         -- python test.py
            │               │
            │               └─ Multiple servers (backend + frontend)
            │                   └─ Use with_server.py with multiple --server flags:
            │                       python scripts/with_server.py \
            │                         --server "cd backend && npm start" --port 4000 \
            │                         --server "cd frontend && npm start" --port 3000 \
            │                         -- python test.py
            │
            └─ Server-side rendered (Django, Flask, Rails, etc.)
                └─ Follow dynamic webapp path above
```

## Server State Decision Tree

```
Need to test webapp
        ↓
    Check if server is running
    └─ lsof -i :PORT -sTCP:LISTEN
        ├─ No output (server not running)
        │   └─ Need to start server
        │       ├─ Know server command?
        │       │   ├─ Yes → Use with_server.py
        │       │   └─ No → Check package.json or README
        │       │           ├─ Found start command
        │       │           │   └─ Use with_server.py
        │       │           └─ Can't find command
        │       │               └─ Ask user for startup instructions
        │       │
        │       └─ Port conflict?
        │           ├─ Check: lsof -i :PORT (without LISTEN filter)
        │           │   └─ Shows process using port
        │           │       ├─ Different app using port
        │           │       │   └─ Kill: lsof -t -i :PORT | xargs kill
        │           │       └─ Old instance of same app
        │           │           └─ Kill and restart
        │           └─ Port available
        │               └─ Start server on this port
        │
        └─ Shows server (server running)
            └─ Test HTTP response
                └─ curl -f http://localhost:PORT/health
                    ├─ Success (200 OK)
                    │   └─ Server is healthy
                    │       └─ Proceed with testing
                    │
                    ├─ Connection refused
                    │   └─ Process running but not accepting connections
                    │       ├─ Check logs: tail -f server.log
                    │       ├─ Check if still starting up
                    │       │   └─ Wait 10-30 seconds and retry
                    │       └─ Server may have crashed during startup
                    │           └─ Restart server
                    │
                    ├─ Timeout
                    │   └─ Server responding slowly
                    │       ├─ Check server resource usage
                    │       │   └─ ps -p PID -o %cpu,%mem
                    │       ├─ High CPU/memory?
                    │       │   └─ Server may be overloaded
                    │       └─ Increase timeout or wait longer
                    │
                    └─ 404 or other error
                        └─ Server running but endpoint doesn't exist
                            ├─ Try root: curl http://localhost:PORT/
                            └─ Check server routes/endpoints
```

## Test Failure Decision Tree

```
Playwright test failed
        ↓
    What type of error?
    ├─ TimeoutError: Timeout 30000ms exceeded
    │   └─ What was timing out?
    │       ├─ page.goto() timeout
    │       │   └─ Server issues
    │       │       ├─ Check server is running
    │       │       ├─ Check server response time: curl -w "Time: %{time_total}s\n"
    │       │       ├─ Increase timeout: goto(url, timeout=60000)
    │       │       └─ Check network connectivity
    │       │
    │       ├─ wait_for_selector() timeout
    │       │   └─ Element not appearing
    │       │       ├─ Did you wait for networkidle first?
    │       │       │   └─ No → Add page.wait_for_load_state('networkidle')
    │       │       ├─ Take screenshot to see actual state
    │       │       │   └─ page.screenshot(path='/tmp/debug.png', full_page=True)
    │       │       ├─ Is selector correct?
    │       │       │   └─ Inspect DOM: page.content()
    │       │       └─ Is element conditionally rendered?
    │       │           └─ Check application state
    │       │
    │       ├─ page.click() timeout
    │       │   └─ Element not clickable
    │       │       ├─ Element not visible?
    │       │       │   └─ Check: page.locator(selector).is_visible()
    │       │       ├─ Element disabled?
    │       │       │   └─ Check: page.locator(selector).is_enabled()
    │       │       ├─ Element obscured by another element?
    │       │       │   └─ Try: page.click(selector, force=True)
    │       │       └─ Selector matches multiple elements?
    │       │           └─ Make selector more specific
    │       │
    │       └─ wait_for_load_state() timeout
    │           └─ Page never reaches networkidle
    │               ├─ Polling API?
    │               │   └─ Use 'load' instead of 'networkidle'
    │               ├─ WebSocket connection?
    │               │   └─ Use 'load' instead of 'networkidle'
    │               └─ Long-running requests?
    │                   └─ Wait for specific element instead
    │
    ├─ Error: Element not found
    │   └─ Selector doesn't match
    │       ├─ Wrong selector syntax?
    │       │   ├─ text= for text content
    │       │   ├─ role= for ARIA roles
    │       │   ├─ CSS selector for classes/IDs
    │       │   └─ xpath= for XPath
    │       ├─ Element doesn't exist?
    │       │   └─ Inspect DOM: page.content()
    │       ├─ Element inside iframe?
    │       │   └─ Use: page.frame_locator('iframe').locator(selector)
    │       └─ Element created dynamically?
    │           └─ Wait for element first: page.wait_for_selector(selector)
    │
    ├─ Error: Element is not visible
    │   └─ Element exists but not visible
    │       ├─ Display: none or visibility: hidden?
    │       │   └─ Check CSS properties
    │       ├─ Outside viewport?
    │       │   └─ Scroll to element: page.locator(selector).scroll_into_view_if_needed()
    │       ├─ Hidden by parent?
    │       │   └─ Check parent visibility
    │       └─ Animation in progress?
    │           └─ Wait for animation: page.wait_for_timeout(500)
    │
    ├─ Error: Element is not enabled
    │   └─ Button/input disabled
    │       ├─ Check application state
    │       │   └─ What conditions enable this element?
    │       ├─ Need to fill other fields first?
    │       │   └─ Complete prerequisite steps
    │       └─ Network request must complete first?
    │           └─ Wait for API response
    │
    ├─ Error: Connection refused / ECONNREFUSED
    │   └─ Server not accessible
    │       └─ Follow Server State Decision Tree above
    │
    ├─ JavaScript error in console
    │   └─ Application error
    │       ├─ Capture console logs
    │       │   └─ page.on("console", lambda msg: print(msg.text))
    │       ├─ Check browser console in headed mode
    │       │   └─ launch(headless=False)
    │       └─ Review application code
    │
    └─ Test assertion failed
        └─ Unexpected state
            ├─ Take screenshot: page.screenshot(path='/tmp/actual.png')
            ├─ Compare with expected state
            ├─ Check console for errors
            └─ Review test logic
```

## Debugging Decision Tree

```
Test is failing, need to debug
        ↓
    Start with reconnaissance
    ├─ Server reconnaissance
    │   ├─ lsof -i :PORT -sTCP:LISTEN
    │   ├─ curl http://localhost:PORT/health
    │   └─ tail -f server.log
    │
    ├─ Visual reconnaissance
    │   ├─ page.screenshot(path='/tmp/debug.png', full_page=True)
    │   └─ Open screenshot to see actual state
    │
    ├─ DOM reconnaissance
    │   ├─ content = page.content()
    │   ├─ print(content[:500])
    │   └─ Search for expected elements
    │
    └─ Console reconnaissance
        ├─ page.on("console", handler)
        └─ Check for JavaScript errors
        ↓
    Analyze reconnaissance data
    ├─ Server not running?
    │   └─ Follow Server State Decision Tree
    │
    ├─ Page not loaded correctly?
    │   ├─ Screenshot shows blank page
    │   │   ├─ Network issue?
    │   │   ├─ Server returned error?
    │   │   └─ Wrong URL?
    │   ├─ Screenshot shows loading spinner
    │   │   ├─ Wait longer: wait_for_load_state('networkidle')
    │   │   └─ Check for blocking requests
    │   └─ Screenshot shows error page
    │       └─ Check server logs for errors
    │
    ├─ Element not found?
    │   ├─ Search DOM content for element
    │   │   ├─ Not in DOM → Wait longer or check conditions
    │   │   └─ In DOM → Selector is wrong
    │   └─ Highlight element to verify
    │       └─ page.locator(selector).evaluate('el => el.style.border = "3px solid red"')
    │
    ├─ Console errors?
    │   ├─ JavaScript syntax error
    │   │   └─ Application bug
    │   ├─ Network request failed
    │   │   └─ API server issue
    │   └─ React/Vue error
    │       └─ Component issue
    │
    └─ Still unclear?
        └─ Progressive debugging
            ├─ Run in headed mode: launch(headless=False)
            ├─ Add slow motion: launch(slow_mo=1000)
            ├─ Add pause: page.pause()
            └─ Enable verbose logging: DEBUG=pw:api python test.py
```

## Selector Strategy Decision Tree

```
Need to select an element
        ↓
    What do you know about the element?
    ├─ Has data-testid attribute?
    │   └─ USE: page.click('[data-testid="submit"]')
    │       → Most stable, won't break with UI changes
    │
    ├─ Has unique text content?
    │   └─ USE: page.click('text=Submit Form')
    │       → Readable, but text may change
    │       ├─ Exact match: 'text="Submit"'
    │       └─ Regex: 'text=/submit/i'
    │
    ├─ Has semantic role?
    │   └─ USE: page.click('role=button[name="Submit"]')
    │       → Accessible, semantic, stable
    │       ├─ Common roles: button, link, textbox, checkbox
    │       └─ With name: role=button[name="Submit"]
    │
    ├─ Has unique ID?
    │   └─ USE: page.click('#submit-button')
    │       → Fast, stable if ID doesn't change
    │       └─ Avoid dynamically generated IDs
    │
    ├─ Has unique class?
    │   └─ USE: page.click('.submit-button')
    │       → May break with CSS refactoring
    │       └─ Combine with tag: 'button.submit'
    │
    ├─ Need complex selection?
    │   └─ USE: CSS combinators
    │       ├─ Child: 'form > button'
    │       ├─ Descendant: 'form button'
    │       ├─ Sibling: '.label + input'
    │       └─ Nth child: 'button:nth-child(2)'
    │
    ├─ Nothing else works?
    │   └─ USE: XPath (last resort)
    │       └─ 'xpath=//button[contains(text(), "Submit")]'
    │
    └─ Multiple matches?
        └─ Make selector more specific
            ├─ Chain: page.locator('form').locator('button.submit')
            ├─ Combine: 'button.submit[type="submit"]'
            └─ Use parent context: 'div.modal >> button.submit'
```

## Wait Strategy Decision Tree

```
Need to wait for something
        ↓
    What are you waiting for?
    ├─ Page to load
    │   └─ What type of page?
    │       ├─ Dynamic (React, Vue, Angular)
    │       │   └─ USE: page.wait_for_load_state('networkidle')
    │       │       → Waits for network requests to finish
    │       ├─ Static with images
    │       │   └─ USE: page.wait_for_load_state('load')
    │       │       → Waits for all resources
    │       └─ Server-side rendered
    │           └─ USE: page.wait_for_load_state('domcontentloaded')
    │               → Waits for HTML to parse
    │
    ├─ Specific element
    │   └─ What state?
    │       ├─ Element to appear
    │       │   └─ USE: page.wait_for_selector('.modal', state='visible')
    │       ├─ Element to disappear
    │       │   └─ USE: page.wait_for_selector('.loading', state='hidden')
    │       ├─ Element to exist in DOM
    │       │   └─ USE: page.wait_for_selector('.data', state='attached')
    │       └─ Element to be removed from DOM
    │           └─ USE: page.wait_for_selector('.temp', state='detached')
    │
    ├─ Network request
    │   └─ Specific API call
    │       ├─ Wait for response
    │       │   └─ USE: with page.expect_response('**/api/data'):
    │       ├─ Wait for request
    │       │   └─ USE: with page.expect_request('**/api/data'):
    │       └─ All network idle
    │           └─ USE: page.wait_for_load_state('networkidle')
    │
    ├─ JavaScript condition
    │   └─ Custom condition
    │       ├─ Variable set
    │       │   └─ USE: page.wait_for_function('() => window.appReady')
    │       ├─ Element content
    │       │   └─ USE: page.wait_for_function('() => document.body.innerText.includes("Ready")')
    │       └─ Animation complete
    │           └─ USE: page.wait_for_function('() => !document.querySelector(".animated")')
    │
    ├─ Fixed time (avoid if possible)
    │   └─ Known delay
    │       └─ USE: page.wait_for_timeout(1000)
    │           → Only use when no other option works
    │
    └─ Multiple conditions
        └─ Combine waits
            ├─ Sequential: wait_for_selector() then wait_for_function()
            └─ Parallel: Use Promise.all() in async context
```

## Environment Selection Decision Tree

```
Setting up test environment
        ↓
    What environment do you need?
    ├─ Local development
    │   ├─ Testing during development
    │   │   ├─ Server: npm run dev (hot reload)
    │   │   ├─ Port: 3000 (dev port)
    │   │   └─ Database: Local SQLite/Postgres
    │   └─ Quick iteration cycle
    │
    ├─ CI/CD pipeline
    │   ├─ Automated testing
    │   │   ├─ Server: npm run build && npm start
    │   │   ├─ Port: Any available port
    │   │   ├─ Database: Test database / fixtures
    │   │   └─ Headless: Always true
    │   └─ Environment variables from CI secrets
    │
    ├─ Staging
    │   ├─ Pre-production testing
    │   │   ├─ Server: Remote staging URL
    │   │   ├─ Database: Staging database
    │   │   └─ Real API keys (staging)
    │   └─ Similar to production
    │
    └─ Production (careful!)
        ├─ Read-only tests only
        ├─ No data modification
        └─ Minimal load generation
```

## Testing Approach Decision Tree

```
What kind of test do you need?
        ↓
    ├─ Unit test (single function/component)
    │   └─ NOT this skill
    │       → Use testing framework (Jest, pytest)
    │
    ├─ Integration test (multiple components)
    │   └─ Do components interact via UI?
    │       ├─ Yes → Use this skill (Playwright)
    │       └─ No → Use API testing or unit tests
    │
    ├─ End-to-end test (full user flow)
    │   └─ USE THIS SKILL
    │       ├─ Start server(s) with with_server.py
    │       ├─ Write Playwright script for user journey
    │       └─ Test complete workflow
    │
    ├─ Visual regression test
    │   └─ USE THIS SKILL + Screenshot comparison
    │       ├─ Capture baseline: page.screenshot()
    │       ├─ Capture current: page.screenshot()
    │       └─ Compare images (external tool)
    │
    ├─ Performance test
    │   └─ What metrics?
    │       ├─ Page load time
    │       │   └─ Measure: page.goto() timing
    │       ├─ API response time
    │       │   └─ Monitor: page.on("response")
    │       └─ Heavy load
    │           → Not this skill, use load testing tool
    │
    └─ Accessibility test
        └─ USE THIS SKILL + axe-core
            ├─ Inject axe: page.evaluate()
            └─ Run audit: Check ARIA, contrast, etc.
```
