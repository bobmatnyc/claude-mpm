# Reconnaissance-Then-Action Pattern

Complete guide to the reconnaissance-before-action philosophy for webapp testing.

## Table of Contents

- [The Philosophy](#the-philosophy)
- [Why Reconnaissance First](#why-reconnaissance-first)
- [The Reconnaissance Process](#the-reconnaissance-process)
- [Server Status Checks](#server-status-checks)
- [Network Diagnostics](#network-diagnostics)
- [DOM Inspection](#dom-inspection)
- [Log Analysis](#log-analysis)
- [Performance Reconnaissance](#performance-reconnaissance)
- [Security Reconnaissance](#security-reconnaissance)
- [Reconnaissance Checklist](#reconnaissance-checklist)
- [Common Failures](#common-failures)

## The Philosophy

**Reconnaissance-Then-Action** is the core principle of webapp testing:

1. **Observe** the current state before acting
2. **Understand** what you're working with
3. **Plan** your actions based on reconnaissance
4. **Execute** with confidence
5. **Verify** the results completely

**The Iron Law:**
> Never test a webapp without first verifying the server state and waiting for the page to be fully loaded.

**Why this matters:**
- Tests fail mysteriously when servers aren't ready
- Actions fail when pages haven't finished loading
- Selectors break when DOM is still being built
- Network requests fail when services aren't available
- Time is wasted debugging problems that don't exist

## Why Reconnaissance First

### The Cost of Skipping Reconnaissance

**Without reconnaissance:**
```python
# ❌ BAD: Jump straight to testing
page.goto('http://localhost:3000')
page.click('button.submit')  # Fails - element not ready
# Error: Timeout 30000ms exceeded
```

**With reconnaissance:**
```python
# ✅ GOOD: Check state first
page.goto('http://localhost:3000')
page.wait_for_load_state('networkidle')  # Wait for page ready
page.screenshot(path='/tmp/before.png')   # Verify what we see
page.click('button.submit')               # Succeeds - page is ready
```

### Real-World Benefits

**Time saved:**
- 5 seconds of reconnaissance saves 30 minutes of debugging
- One screenshot reveals problems that take hours to diagnose
- Server check prevents entire test suite failures

**Confidence gained:**
- Know exactly what state the system is in
- Understand why tests pass or fail
- Debug issues 10x faster with visual evidence

**Reliability improved:**
- Tests pass consistently
- Fewer false negatives
- Clear failure messages when problems occur

## The Reconnaissance Process

### Step 1: Verify Server State

**Check if server is running:**
```bash
# Using lsof (most reliable)
lsof -i :3000 -sTCP:LISTEN

# Using curl (checks HTTP response)
curl -f http://localhost:3000/health
```

**What to look for:**
- Is the port listening?
- Is the process alive?
- Does it respond to HTTP requests?
- What's the response time?

**Example output analysis:**
```bash
$ lsof -i :3000 -sTCP:LISTEN
COMMAND   PID  USER   FD   TYPE DEVICE SIZE/OFF NODE NAME
node    12345  user   20u  IPv4 0x1234      0t0  TCP *:3000 (LISTEN)

# Good signs:
# ✅ Process is running (PID 12345)
# ✅ Listening on correct port (3000)
# ✅ Protocol is TCP
# ✅ State is LISTEN
```

### Step 2: Navigate and Wait

**Always wait for network idle on dynamic apps:**
```python
page.goto('http://localhost:3000')
page.wait_for_load_state('networkidle')  # CRITICAL
```

**Why networkidle is essential:**
- JavaScript frameworks need time to initialize
- API calls must complete before DOM is ready
- Components may render multiple times
- Dynamic content loads asynchronously

**Wait hierarchy:**
1. `domcontentloaded` - HTML parsed (too early for most apps)
2. `load` - Resources loaded (images, CSS)
3. `networkidle` - Network requests finished (best for testing)

### Step 3: Visual Reconnaissance

**Take screenshots before acting:**
```python
# Full page screenshot
page.screenshot(path='/tmp/reconnaissance.png', full_page=True)

# Element-specific screenshot
page.locator('.modal').screenshot(path='/tmp/modal.png')

# Custom viewport
page.set_viewport_size({'width': 1920, 'height': 1080})
page.screenshot(path='/tmp/desktop.png')
```

**What screenshots reveal:**
- Is the page actually loaded?
- Are elements visible where expected?
- Is layout correct?
- Are there error messages?
- Is content what you expect?

### Step 4: DOM Inspection

**Discover what's actually on the page:**
```python
# Get full HTML
content = page.content()
print(content[:500])  # First 500 chars

# Find all buttons
buttons = page.locator('button').all()
print(f"Found {len(buttons)} buttons:")
for i, btn in enumerate(buttons):
    text = btn.inner_text() if btn.is_visible() else "[hidden]"
    print(f"  [{i}] {text}")

# Find all links
links = page.locator('a[href]').all()
for link in links[:5]:
    print(f"  - {link.inner_text()} -> {link.get_attribute('href')}")

# Find all inputs
inputs = page.locator('input, textarea, select').all()
for inp in inputs:
    name = inp.get_attribute('name') or inp.get_attribute('id') or "[unnamed]"
    print(f"  - {name}")
```

**Example reconnaissance script:**
```python
from playwright.sync_api import sync_playwright

def reconnaissance(url):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Navigate and wait
        page.goto(url)
        page.wait_for_load_state('networkidle')

        # Visual reconnaissance
        page.screenshot(path='/tmp/recon.png', full_page=True)
        print("Screenshot saved: /tmp/recon.png")

        # Element reconnaissance
        print("\nButtons:")
        for i, btn in enumerate(page.locator('button').all()):
            print(f"  [{i}] {btn.inner_text()}")

        print("\nLinks:")
        for link in page.locator('a[href]').all()[:10]:
            print(f"  - {link.inner_text()}")

        print("\nInputs:")
        for inp in page.locator('input').all():
            name = inp.get_attribute('name') or '[unnamed]'
            print(f"  - {name}")

        browser.close()

reconnaissance('http://localhost:3000')
```

### Step 5: Console Log Reconnaissance

**Capture console output:**
```python
console_logs = []

def handle_console(msg):
    console_logs.append(f"[{msg.type}] {msg.text}")
    print(f"Console: [{msg.type}] {msg.text}")

page.on("console", handle_console)
page.goto('http://localhost:3000')
page.wait_for_load_state('networkidle')

# Save logs
with open('/tmp/console.log', 'w') as f:
    f.write('\n'.join(console_logs))
```

**What console logs reveal:**
- JavaScript errors
- API failures
- Warning messages
- Debug output
- Performance timing

## Server Status Checks

### Using lsof (macOS/Linux)

**Basic check:**
```bash
lsof -i :3000
```

**Check if listening:**
```bash
lsof -i :3000 -sTCP:LISTEN
```

**Get just PID:**
```bash
lsof -t -i :3000
```

**Detailed output:**
```bash
lsof -i :3000 -P -n
# -P: Don't resolve port names
# -n: Don't resolve hostnames
```

### Using ps (Process Status)

**Check if process is running:**
```bash
ps aux | grep node
ps aux | grep python
ps aux | grep "npm.*start"
```

**Check CPU and memory:**
```bash
ps aux | grep 12345  # PID from lsof
```

### Using curl (HTTP Check)

**Basic health check:**
```bash
curl http://localhost:3000
```

**Check specific endpoint:**
```bash
curl http://localhost:3000/health
```

**Check with timeout:**
```bash
curl --max-time 5 http://localhost:3000
```

**Check and show response time:**
```bash
curl -w "\nTime: %{time_total}s\n" http://localhost:3000
```

**Silent success check:**
```bash
if curl -f -s http://localhost:3000/health > /dev/null; then
    echo "Server is healthy"
else
    echo "Server is not responding"
fi
```

### Using netstat

**Check listening ports:**
```bash
netstat -an | grep LISTEN | grep 3000
```

**Show all TCP connections:**
```bash
netstat -an | grep tcp
```

## Network Diagnostics

### Using curl for Diagnostics

**Verbose output:**
```bash
curl -v http://localhost:3000
```

**Show response headers:**
```bash
curl -I http://localhost:3000
```

**Follow redirects:**
```bash
curl -L http://localhost:3000
```

**Save response:**
```bash
curl -o response.html http://localhost:3000
```

**Test POST request:**
```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{"test":"data"}' \
  http://localhost:3000/api/endpoint
```

### Network Timing

**Measure response time:**
```bash
curl -w "@curl-format.txt" -o /dev/null -s http://localhost:3000
```

**curl-format.txt:**
```
time_namelookup:  %{time_namelookup}s\n
time_connect:     %{time_connect}s\n
time_appconnect:  %{time_appconnect}s\n
time_pretransfer: %{time_pretransfer}s\n
time_redirect:    %{time_redirect}s\n
time_starttransfer: %{time_starttransfer}s\n
----------\n
time_total:       %{time_total}s\n
```

### Using tcpdump (Advanced)

**Capture HTTP traffic:**
```bash
sudo tcpdump -i lo0 -A -s 0 'tcp port 3000'
```

**Save to file:**
```bash
sudo tcpdump -i lo0 -w capture.pcap 'tcp port 3000'
```

## DOM Inspection

### Element Discovery Pattern

**Find interactive elements:**
```python
# Buttons
buttons = page.locator('button, input[type="button"], input[type="submit"]').all()

# Links
links = page.locator('a[href]').all()

# Form inputs
inputs = page.locator('input, textarea, select').all()

# Clickable elements
clickable = page.locator('[onclick], [role="button"]').all()
```

### Check Element State

**Visibility:**
```python
element = page.locator('button.submit')
print(f"Visible: {element.is_visible()}")
print(f"Enabled: {element.is_enabled()}")
print(f"Editable: {element.is_editable()}")
```

**Attributes:**
```python
print(f"Text: {element.inner_text()}")
print(f"HTML: {element.inner_html()}")
print(f"Class: {element.get_attribute('class')}")
print(f"ID: {element.get_attribute('id')}")
```

### Find Selectors

**Test different selector strategies:**
```python
# Try text selector
try:
    page.locator('text=Submit').is_visible()
    print("✅ Text selector works: 'text=Submit'")
except:
    print("❌ Text selector failed")

# Try role selector
try:
    page.locator('role=button[name="Submit"]').is_visible()
    print("✅ Role selector works: 'role=button[name=\"Submit\"]'")
except:
    print("❌ Role selector failed")

# Try CSS selector
try:
    page.locator('button.submit').is_visible()
    print("✅ CSS selector works: 'button.submit'")
except:
    print("❌ CSS selector failed")
```

## Log Analysis

### Server Logs

**Node.js console output:**
```bash
npm start > server.log 2>&1 &
tail -f server.log
```

**Look for:**
- Startup messages
- Port binding confirmation
- Error messages
- Warning messages
- Request logs

### Application Logs

**Grep for errors:**
```bash
grep -i error server.log
grep -i warning server.log
grep -i exception server.log
```

**Filter by timestamp:**
```bash
grep "2024-01-15 14:" server.log
```

**Count errors:**
```bash
grep -c "ERROR" server.log
```

## Performance Reconnaissance

### Response Time Checks

**Measure with curl:**
```bash
curl -w "Time: %{time_total}s\n" -o /dev/null -s http://localhost:3000
```

**Measure with Playwright:**
```python
import time

start = time.time()
page.goto('http://localhost:3000')
page.wait_for_load_state('networkidle')
elapsed = time.time() - start

print(f"Page load time: {elapsed:.2f}s")
```

### Resource Usage

**Check CPU and memory:**
```bash
pid=$(lsof -t -i :3000)
ps -p $pid -o %cpu,%mem,rss,vsz
```

**Monitor continuously:**
```bash
watch -n 1 'ps -p $(lsof -t -i :3000) -o %cpu,%mem,rss'
```

## Security Reconnaissance

### Port Scanning

**Check open ports:**
```bash
nmap localhost
```

**Specific port:**
```bash
nmap -p 3000 localhost
```

### SSL/TLS Check

**Test HTTPS:**
```bash
curl -k https://localhost:3000
```

**Check certificate:**
```bash
openssl s_client -connect localhost:3000
```

### Header Analysis

**Check security headers:**
```bash
curl -I http://localhost:3000 | grep -i "security\|cors\|content-security"
```

## Reconnaissance Checklist

### Pre-Test Checklist

- [ ] Server is running (lsof check)
- [ ] Port is accessible (curl check)
- [ ] Server responds to health check
- [ ] Response time is reasonable (< 2s)
- [ ] No errors in server logs
- [ ] Environment variables are set
- [ ] Dependencies are installed

### During-Test Checklist

- [ ] Page navigation successful
- [ ] Waited for networkidle
- [ ] Screenshot captured
- [ ] Console logs captured
- [ ] Expected elements are visible
- [ ] No JavaScript errors
- [ ] Form fields are editable
- [ ] Buttons are clickable

### Post-Action Checklist

- [ ] Action completed without errors
- [ ] Expected state change occurred
- [ ] No new console errors
- [ ] Screenshot shows expected result
- [ ] Server still responding
- [ ] No memory leaks (check server resources)

## Common Failures

### Failure: Server Not Running

**Symptoms:**
- Connection refused errors
- Timeout errors
- lsof returns no results

**Reconnaissance steps:**
```bash
# Check if server is running
lsof -i :3000

# Check if process exists
ps aux | grep node

# Check server logs
cat server.log | tail -20
```

**Solution:**
- Start server manually
- Use with_server.py script
- Check for port conflicts
- Review startup errors

### Failure: Page Not Fully Loaded

**Symptoms:**
- Element not found errors
- Stale element errors
- Timeout waiting for selector

**Reconnaissance steps:**
```python
# Take screenshot to see what's actually loaded
page.screenshot(path='/tmp/debug.png', full_page=True)

# Check network state
page.wait_for_load_state('networkidle')

# Check for loading indicators
loading = page.locator('.loading, .spinner').is_visible()
print(f"Still loading: {loading}")
```

**Solution:**
- Always wait for networkidle
- Wait for specific elements
- Check for loading indicators
- Increase timeouts if needed

### Failure: Wrong Element Selected

**Symptoms:**
- Action has no effect
- Wrong element is clicked
- Unexpected behavior

**Reconnaissance steps:**
```python
# Find all matching elements
elements = page.locator('button').all()
print(f"Found {len(elements)} buttons")
for i, el in enumerate(elements):
    print(f"[{i}] {el.inner_text()}")

# Highlight element before clicking
page.locator('button.submit').evaluate('el => el.style.border = "3px solid red"')
page.screenshot(path='/tmp/highlighted.png')
```

**Solution:**
- Use more specific selectors
- Use data-testid attributes
- Verify element before clicking
- Check element count

### Failure: Network Request Failed

**Symptoms:**
- API errors in console
- Empty data
- Timeout errors

**Reconnaissance steps:**
```python
# Monitor network requests
def handle_response(response):
    print(f"Response: {response.url} - {response.status}")

page.on("response", handle_response)

# Wait for specific API call
with page.expect_response('**/api/data') as response_info:
    page.click('button.load')
response = response_info.value
print(f"Status: {response.status}")
```

**Solution:**
- Check API server is running
- Verify CORS configuration
- Check network timeouts
- Mock API responses if needed
