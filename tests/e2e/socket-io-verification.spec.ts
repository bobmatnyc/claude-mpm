import { test, expect } from '@playwright/test';

test.describe('Dashboard Socket.IO Event Verification', () => {
  test('should monitor Socket.IO connection and events', async ({ page }) => {
    const consoleMessages: string[] = [];
    const socketEvents: any[] = [];
    const errors: string[] = [];

    // Capture console messages
    page.on('console', msg => {
      const text = msg.text();
      consoleMessages.push(`[${msg.type()}] ${text}`);
      console.log(`[CONSOLE ${msg.type()}]`, text);
    });

    // Capture errors
    page.on('pageerror', error => {
      errors.push(error.message);
      console.log('[PAGE ERROR]', error.message);
    });

    // Navigate to dashboard
    console.log('\n=== Opening Dashboard ===');
    await page.goto('http://localhost:8765');

    // Wait for page to load
    await page.waitForLoadState('networkidle');

    // Inject monitoring script to intercept Socket.IO events
    await page.evaluate(() => {
      // Store original io.on method
      (window as any).__socketEvents = [];

      // Try to hook into Socket.IO if available
      const checkInterval = setInterval(() => {
        const socket = (window as any).socket;
        if (socket) {
          console.log('[MONITOR] Socket.IO instance found!');
          console.log('[MONITOR] Socket connected:', socket.connected);
          console.log('[MONITOR] Socket ID:', socket.id);

          // Monitor all events
          const originalOn = socket.on.bind(socket);
          socket.on = function(event: string, handler: Function) {
            console.log('[MONITOR] Registering listener for event:', event);
            return originalOn(event, function(...args: any[]) {
              console.log('[SOCKET EVENT]', event, 'Data:', JSON.stringify(args));
              (window as any).__socketEvents.push({ event, args, timestamp: Date.now() });
              return handler(...args);
            });
          };

          clearInterval(checkInterval);
        }
      }, 100);

      // Stop checking after 5 seconds
      setTimeout(() => clearInterval(checkInterval), 5000);
    });

    console.log('\n=== Waiting 3 seconds for Socket.IO initialization ===');
    await page.waitForTimeout(3000);

    // Check Socket.IO connection status
    const socketStatus = await page.evaluate(() => {
      const socket = (window as any).socket;
      if (!socket) {
        return { exists: false };
      }
      return {
        exists: true,
        connected: socket.connected,
        id: socket.id,
        transport: socket.io?.engine?.transport?.name
      };
    });

    console.log('\n=== Socket.IO Status ===');
    console.log(JSON.stringify(socketStatus, null, 2));

    // Send test event via HTTP
    console.log('\n=== Sending Test Event via HTTP ===');
    const response = await page.request.post('http://localhost:8765/api/events', {
      headers: {
        'Content-Type': 'application/json'
      },
      data: {
        event: 'claude_event',
        data: {
          type: 'hook',
          subtype: 'pre_tool',
          data: {
            tool_name: 'Read',
            tool_parameters: {
              file_path: '/test/example.py'
            }
          }
        }
      }
    });

    console.log('HTTP Response Status:', response.status());
    const responseBody = await response.text();
    console.log('HTTP Response Body:', responseBody);

    // Wait for event to be received
    console.log('\n=== Waiting 5 seconds for events ===');
    await page.waitForTimeout(5000);

    // Check for received events
    const receivedEvents = await page.evaluate(() => {
      return (window as any).__socketEvents || [];
    });

    console.log('\n=== Received Socket.IO Events ===');
    console.log('Total events:', receivedEvents.length);
    receivedEvents.forEach((evt: any, idx: number) => {
      console.log(`Event ${idx + 1}:`, JSON.stringify(evt, null, 2));
    });

    // Take screenshot
    await page.screenshot({
      path: '/Users/masa/Projects/claude-mpm/test-results/dashboard-socketio-test.png',
      fullPage: true
    });

    // Generate report
    console.log('\n=== VERIFICATION REPORT ===');
    console.log('Dashboard URL:', 'http://localhost:8765');
    console.log('Socket.IO exists:', socketStatus.exists);
    console.log('Socket.IO connected:', socketStatus.connected);
    console.log('Events received:', receivedEvents.length);
    console.log('Console messages:', consoleMessages.length);
    console.log('Errors:', errors.length);

    if (errors.length > 0) {
      console.log('\nErrors detected:');
      errors.forEach(err => console.log(' -', err));
    }

    console.log('\nConsole Messages:');
    consoleMessages.forEach(msg => console.log(' ', msg));

    // Assertions
    expect(socketStatus.exists, 'Socket.IO should be initialized').toBe(true);
    expect(errors.length, 'Should have no page errors').toBe(0);
  });

  test('should send curl test and monitor events', async ({ page }) => {
    console.log('\n=== Setting up event monitoring ===');

    // Navigate to dashboard
    await page.goto('http://localhost:8765');
    await page.waitForLoadState('networkidle');

    // Set up event monitoring
    await page.evaluate(() => {
      (window as any).__receivedEvents = [];
      const socket = (window as any).socket;

      if (socket) {
        console.log('[TEST] Monitoring claude_event');
        socket.on('claude_event', (data: any) => {
          console.log('[RECEIVED] claude_event:', JSON.stringify(data));
          (window as any).__receivedEvents.push({
            event: 'claude_event',
            data,
            timestamp: Date.now()
          });
        });
      }
    });

    console.log('\n=== Dashboard ready, waiting for curl command ===');
    console.log('Run this command in another terminal:');
    console.log('\ncurl -X POST http://localhost:8765/api/events \\');
    console.log('  -H "Content-Type: application/json" \\');
    console.log('  -d \'{"event": "claude_event", "data": {"type": "hook", "subtype": "pre_tool", "data": {"tool_name": "Read", "tool_parameters": {"file_path": "/test/example.py"}}}}\'');
    console.log('\nWaiting 30 seconds...\n');

    // Wait for 30 seconds to allow manual curl testing
    await page.waitForTimeout(30000);

    // Check received events
    const events = await page.evaluate(() => {
      return (window as any).__receivedEvents || [];
    });

    console.log('\n=== Events Received After Curl ===');
    console.log('Total events:', events.length);
    events.forEach((evt: any, idx: number) => {
      console.log(`Event ${idx + 1}:`, JSON.stringify(evt, null, 2));
    });
  });
});
