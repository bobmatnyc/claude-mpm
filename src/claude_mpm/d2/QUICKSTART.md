# Quick Start Guide

Get the Dashboard2 up and running in 5 minutes.

## Prerequisites

- Node.js 18+ installed
- Claude MPM monitor server running on port 8765

## Installation

```bash
# Navigate to dashboard2 directory
cd src/claude_mpm/dashboard2

# Install dependencies
npm install
```

## Development

### Start Dev Server

```bash
npm run dev
```

Dashboard will be available at: **http://localhost:5173**

Features:
- ✅ Hot Module Replacement (instant updates on file changes)
- ✅ Source maps for debugging
- ✅ Fast rebuild times

### Test Socket.IO Connection

1. Make sure Claude MPM monitor server is running:
   ```bash
   curl http://localhost:8765/health
   ```

2. Open Dashboard2 in browser
3. Check connection status in header:
   - 🟢 Green = Connected
   - 🟡 Yellow = Reconnecting
   - 🔴 Red = Disconnected

### Generate Test Events

Open browser console and run:

```javascript
// Get the Socket.IO client
const socket = io('http://localhost:8765');

// Send a test event
socket.emit('claude_event', {
  source: 'hook',
  type: 'test',
  subtype: 'manual_test',
  timestamp: new Date().toISOString(),
  data: {
    message: 'Hello from browser console!',
    test: true
  }
});
```

The event should appear immediately in the Events tab.

## Production Build

```bash
# Build for production
npm run build

# Output will be in dist/
ls -la dist/
```

Built files:
- `dist/index.html` - Main HTML file
- `dist/assets/*.js` - Bundled JavaScript
- `dist/assets/*.css` - Bundled CSS

## Preview Production Build

```bash
# Serve the production build locally
npm run preview
```

This serves the built files at: **http://localhost:4173**

## Common Issues

### Port 5173 already in use

```bash
# Kill process on port 5173
lsof -ti:5173 | xargs kill -9

# Or change port in vite.config.js
```

### Socket.IO connection fails

1. Check server is running:
   ```bash
   curl http://localhost:8765/health
   ```

2. Check port in browser console:
   ```javascript
   console.log('Connecting to:', socketStore.url);
   ```

3. Verify no CORS issues in Network tab

### Events not appearing

1. Check connection status (should be green)
2. Open browser console and look for logs
3. Verify events are being emitted from server
4. Try the test event code above

## Next Steps

- [README.md](README.md) - Full documentation
- [TESTING.md](TESTING.md) - Testing checklist
- [FLASK_INTEGRATION.md](FLASK_INTEGRATION.md) - Flask integration guide

## Project Structure (Quick Reference)

```
dashboard2/
├── src/
│   ├── App.svelte              # Main app
│   ├── components/             # UI components
│   │   ├── Header.svelte
│   │   ├── Sidebar.svelte
│   │   └── tabs/
│   │       └── EventsTab.svelte
│   ├── stores/                 # State management
│   │   ├── socket.svelte.js    # Socket.IO connection
│   │   └── events.svelte.js    # Event buffer
│   └── lib/
│       └── socketio.js         # Socket.IO wrapper
├── package.json                # Dependencies
├── vite.config.js             # Build config
└── index.html                 # HTML template
```

## Key Technologies

- **Svelte 5** - Modern reactive framework with Runes API
- **Vite** - Fast build tool
- **Socket.IO** - Real-time communication

## Svelte 5 Runes Used

- `$state()` - Reactive state
- `$derived()` - Computed values
- `$effect()` - Side effects
- `$bindable()` - Two-way binding

## Development Tips

1. **File watching works automatically** - Just save files and see changes instantly

2. **Check browser console** - All Socket.IO events are logged for debugging

3. **Use Svelte DevTools** - Install browser extension for state inspection

4. **Component hot reload** - Changes to Svelte components reload without full page refresh

5. **CSS changes are instant** - No need to refresh for style changes

## Need Help?

- Check [README.md](README.md) for full documentation
- See [TESTING.md](TESTING.md) for troubleshooting
- Review browser console for errors
- Check Socket.IO connection status

Happy developing! 🚀
