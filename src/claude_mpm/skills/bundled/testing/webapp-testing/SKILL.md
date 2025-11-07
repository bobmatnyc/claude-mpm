---
name: webapp-testing
version: 2.0.0
category: testing
description: Automated webapp testing with Playwright. Server management, UI testing, visual debugging, and reconnaissance-first approach.
license: Complete terms in LICENSE.txt
progressive_disclosure:
  entry_point:
    summary: "Reconnaissance before action: verify server state and page load before testing"
    when_to_use: "When testing web applications with Playwright. Server verification, UI testing, frontend debugging."
    quick_start: "1. Check server with lsof 2. Start with with_server.py 3. Wait for networkidle 4. Screenshot and verify"
  references:
    - playwright-patterns.md
    - server-management.md
    - reconnaissance-pattern.md
    - decision-tree.md
    - troubleshooting.md
---

# Webapp Testing

## Overview

**Core Principle: Reconnaissance Before Action**

Automated webapp testing using Playwright with a focus on verifying system state (server status, page load, element presence) before taking any action. This ensures reliable, debuggable tests that fail for clear reasons.

**Key capabilities:**
- Automated browser testing with Playwright
- Server lifecycle management
- Visual reconnaissance (screenshots, DOM inspection)
- Network monitoring and debugging

## When to Use This Skill

- **Web application testing** - UI behavior, forms, navigation, integration testing
- **Frontend debugging** - Screenshots, DOM inspection, console monitoring
- **Regression testing** - Ensure changes don't break existing functionality
- **Server verification** - Check servers are running and responding

**Not suitable for:** Unit testing (use Jest/pytest), load testing, or API-only testing.

## The Iron Law

**RECONNAISSANCE BEFORE ACTION**

Never execute test actions without first:
1. **Verify server state** - `lsof -i :PORT` and `curl` checks
2. **Wait for page ready** - `page.wait_for_load_state('networkidle')`
3. **Visual confirmation** - Screenshot before actions
4. **Read complete output** - Examine full results before claiming success

**Why:** Tests fail mysteriously when servers aren't ready, selectors break when DOM is still building, and 5 seconds of reconnaissance saves 30 minutes of debugging.

## Quick Start

### Step 1: Verify Server State

```bash
lsof -i :3000 -sTCP:LISTEN  # Check server listening
curl -f http://localhost:3000/health  # Test response
```

### Step 2: Start Server (If Needed)

```bash
# Single server
python scripts/with_server.py --server "npm run dev" --port 5173 -- python test.py

# Multiple servers (backend + frontend)
python scripts/with_server.py \
  --server "cd backend && python server.py" --port 3000 \
  --server "cd frontend && npm run dev" --port 5173 \
  -- python test.py
```

### Step 3: Write Test with Reconnaissance

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    # 1. Navigate and wait
    page.goto('http://localhost:5173')
    page.wait_for_load_state('networkidle')  # CRITICAL

    # 2. Reconnaissance
    page.screenshot(path='/tmp/before.png', full_page=True)
    buttons = page.locator('button').all()
    print(f"Found {len(buttons)} buttons")

    # 3. Execute
    page.click('button.submit')

    # 4. Verify
    page.wait_for_selector('.success-message')
    page.screenshot(path='/tmp/after.png', full_page=True)

    browser.close()
```

### Step 4: Verify Results

Review console output, check for errors, verify state changes, examine screenshots.

## Key Patterns

**Server Management** - Check → Start → Wait → Test → Cleanup
- Use `with_server.py` for automatic lifecycle management
- Check status with `lsof`, test with `curl`
- Automatic cleanup on exit

**Reconnaissance** - Inspect → Understand → Act → Verify
- Screenshot current state
- Inspect DOM for elements
- Act on discovered selectors
- Verify results visually

**Wait Strategy** - Load → Idle → Element → Action
- Always wait for `networkidle` on dynamic apps
- Wait for specific elements before interaction
- Playwright auto-waits but explicit waits prevent race conditions

**Selector Priority** - data-testid > role > text > CSS > XPath
- `[data-testid="submit"]` - most stable
- `role=button[name="Submit"]` - semantic
- `text=Submit` - readable
- `button.submit` - acceptable
- XPath - last resort

## Common Pitfalls

❌ **Testing without server verification** - Always check `lsof` and `curl` first
❌ **Ignoring timeout errors** - TimeoutError means something is wrong, investigate
❌ **Not waiting for networkidle** - Dynamic apps need full page load
❌ **Poor selector strategies** - Use data-testid for stability
❌ **Missing network verification** - Check API responses complete
❌ **Incomplete cleanup** - Close browsers, stop servers properly

## Reference Documentation

**[playwright-patterns.md](playwright-patterns.md)** - Complete Playwright reference
Selectors, waits, interactions, assertions, test organization, network interception, screenshots, debugging

**[server-management.md](server-management.md)** - Server lifecycle and operations
with_server.py usage, manual management, port management, process control, environment config, health checks

**[reconnaissance-pattern.md](reconnaissance-pattern.md)** - Philosophy and practice
Why reconnaissance first, complete process, server checks, network diagnostics, DOM inspection, log analysis

**[decision-tree.md](decision-tree.md)** - Flowcharts for every scenario
New test decisions, server state paths, test failure diagnosis, debugging flows, selector/wait strategies

**[troubleshooting.md](troubleshooting.md)** - Solutions to common problems
Timeout issues, selector problems, server crashes, network errors, environment config, debugging workflow

## Examples and Scripts

**Examples** (`examples/` directory):
- `element_discovery.py` - Discovering page elements
- `static_html_automation.py` - Testing local HTML files
- `console_logging.py` - Capturing console output

**Scripts** (`scripts/` directory):
- `with_server.py` - Server lifecycle management (run with `--help` first)

## Integration with Other Skills

**Mandatory:** verification-before-completion
**Recommended:** systematic-debugging, test-driven-development
**Related:** playwright-testing, selenium-automation

## Bottom Line

1. **Reconnaissance always comes first** - Verify before acting
2. **Never skip server checks** - 5 seconds saves 30 minutes
3. **Wait for networkidle** - Dynamic apps need time
4. **Read complete output** - Verify before claiming success
5. **Screenshot everything** - Visual evidence is invaluable

The reconnaissance-then-action pattern is not optional - it's the foundation of reliable webapp testing.
