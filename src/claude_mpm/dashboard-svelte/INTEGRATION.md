# Svelte Dashboard Integration

## Overview

The Svelte dashboard is a modern, reactive UI built with SvelteKit 2.0 and Svelte 5. It integrates with the existing Claude MPM Socket.IO server to provide real-time monitoring of Claude Code sessions.

## Architecture

### Build Configuration

**Location**: `src/claude_mpm/dashboard-svelte/`

**Build Output**: `src/claude_mpm/dashboard/static/svelte-build/`

**Key Files**:
- `svelte.config.js` - SvelteKit configuration with static adapter
- `vite.config.ts` - Vite build configuration
- `package.json` - Dependencies and build scripts

### Server Integration

**Server Location**: `src/claude_mpm/services/socketio/server/core.py`

**How it works**:

1. **Static File Serving** (lines 713-740):
   - Svelte build output is detected at startup
   - Route `/svelte` serves the SvelteKit `index.html`
   - Route `/_app/` serves compiled JavaScript and CSS assets

2. **URL Structure**:
   ```
   http://localhost:8765/svelte     → Svelte dashboard (new)
   http://localhost:8765/           → Legacy HTML dashboard
   http://localhost:8765/dashboard  → Full dashboard template
   ```

3. **Socket.IO Connection**:
   - Both dashboards connect to same Socket.IO server on port 8765
   - Svelte dashboard uses `socket.io-client` library
   - Shares same event streams as legacy dashboard

## Development Workflow

### Initial Setup

```bash
cd src/claude_mpm/dashboard-svelte
npm install
```

### Development Mode

Run Vite dev server with hot reload:

```bash
cd src/claude_mpm/dashboard-svelte
npm run dev
```

This starts Vite on `http://localhost:5173` with:
- Hot module replacement (HMR)
- Instant updates on file changes
- Proxy to Socket.IO server (configure if needed)

### Production Build

Build and deploy to Python server:

```bash
# From project root
./scripts/build-svelte-dashboard.sh

# Or manually
cd src/claude_mpm/dashboard-svelte
npm run build
```

**Build Process**:
1. SvelteKit builds app with `@sveltejs/adapter-static`
2. Output written to `../dashboard/static/svelte-build/`
3. Python server detects build at startup
4. Dashboard available at `/svelte` route

### Testing Integration

1. **Build the dashboard**:
   ```bash
   ./scripts/build-svelte-dashboard.sh
   ```

2. **Start Socket.IO server**:
   ```bash
   claude-mpm monitor start
   ```

3. **Open in browser**:
   ```
   http://localhost:8765/svelte
   ```

4. **Verify Socket.IO connection**:
   - Check browser console for connection messages
   - Trigger Claude Code events (use `claude-mpm run` or hooks)
   - Verify events appear in dashboard

## Technical Details

### SvelteKit Static Adapter

**Configuration** (`svelte.config.js`):

```javascript
adapter: adapter({
    pages: '../dashboard/static/svelte-build',
    assets: '../dashboard/static/svelte-build',
    fallback: 'index.html',
    precompress: false,
    strict: true
})
```

**Why these settings**:
- `pages` / `assets`: Output to Python server's static directory
- `fallback: 'index.html'`: SPA mode (all routes → index.html)
- `precompress: false`: Disable pre-compression (aiohttp handles this)
- `strict: true`: Fail build on errors

### Asset Path Resolution

**SvelteKit generates**:
```html
<script src="/_app/immutable/entry/start.CXMFOxlI.js"></script>
```

**Python server routes**:
```python
# Serve /_app/ from svelte-build/_app/
self.app.router.add_static("/_app/", svelte_app_path, name="svelte_app")
```

**Result**: Absolute paths like `/_app/...` resolve correctly when served from `/svelte`.

### Socket.IO Client Integration

**Connection code** (in Svelte components):

```typescript
import { io } from 'socket.io-client';

const socket = io('http://localhost:8765', {
    transports: ['websocket', 'polling'],
    reconnection: true,
    reconnectionDelay: 1000,
    reconnectionAttempts: 5
});

socket.on('claude_event', (event) => {
    // Handle event
});
```

**Event types**:
- `claude_event` - Main event stream (hook events, tool executions, etc.)
- `system_event` - Server heartbeat and status
- `connect` / `disconnect` - Connection lifecycle

## Deployment Considerations

### Production Build Optimization

**Current state** (development-friendly):
- Source maps included
- No minification (readable debugging)
- Uncompressed output

**For production** (update `vite.config.ts`):

```typescript
export default defineConfig({
    plugins: [sveltekit()],
    build: {
        minify: 'terser',
        sourcemap: false,
        rollupOptions: {
            output: {
                manualChunks: {
                    'socket.io': ['socket.io-client']
                }
            }
        }
    }
});
```

### Path Context Awareness

The Python server's `_find_static_path()` method handles multiple deployment contexts:
- **Development**: `project_root/src/claude_mpm/dashboard/static/svelte-build`
- **pip install**: `site-packages/claude_mpm/dashboard/static/svelte-build`
- **pipx**: `~/.local/pipx/venvs/claude-mpm/.../dashboard/static/svelte-build`

Build output location remains the same across contexts.

## Troubleshooting

### Dashboard not loading at /svelte

**Check**:
1. Build exists: `ls src/claude_mpm/dashboard/static/svelte-build/`
2. Server logs: Look for "✅ Svelte dashboard available at /svelte"
3. Browser console: Check for 404 errors on `/_app/` assets

**Fix**:
```bash
./scripts/build-svelte-dashboard.sh
claude-mpm monitor stop
claude-mpm monitor start
```

### Socket.IO not connecting

**Check**:
1. Server running: `claude-mpm monitor status`
2. Port availability: `lsof -i :8765`
3. Browser console: Check WebSocket connection errors

**Fix**:
- Ensure server started before opening dashboard
- Check firewall/security settings
- Verify Socket.IO server logs for connection attempts

### Assets not loading (404 on /_app/)

**Symptoms**: White screen, console errors like:
```
GET http://localhost:8765/_app/immutable/entry/start.js 404
```

**Cause**: Static route not registered or build output missing.

**Fix**:
1. Rebuild: `./scripts/build-svelte-dashboard.sh`
2. Check `_app` directory exists: `ls src/claude_mpm/dashboard/static/svelte-build/_app/`
3. Restart server: `claude-mpm monitor start`

### Hot reload not working in dev mode

**Cause**: Vite dev server (port 5173) not running.

**Fix**:
```bash
cd src/claude_mpm/dashboard-svelte
npm run dev  # Starts Vite on localhost:5173
```

**Note**: Dev mode doesn't serve from Python server. Use `npm run dev` for development, build + Python server for testing integration.

## Future Enhancements

### Router Configuration

To make `/svelte` the default dashboard:

```python
# In core.py _setup_static_files()
self.app.router.add_get("/", svelte_handler)  # Change from legacy handler
```

### Base Path Configuration

To serve from subdirectory (e.g., `/mpm/dashboard`):

**svelte.config.js**:
```javascript
kit: {
    paths: {
        base: '/mpm/dashboard'
    },
    adapter: adapter({...})
}
```

**core.py**:
```python
self.app.router.add_get("/mpm/dashboard", svelte_handler)
```

### WebSocket Proxy in Dev Mode

For development without running Python server:

**vite.config.ts**:
```typescript
export default defineConfig({
    server: {
        proxy: {
            '/socket.io': {
                target: 'http://localhost:8765',
                ws: true
            }
        }
    }
});
```

## References

- [SvelteKit Static Adapter Docs](https://kit.svelte.dev/docs/adapter-static)
- [Socket.IO Client Docs](https://socket.io/docs/v4/client-api/)
- [aiohttp Static Files](https://docs.aiohttp.org/en/stable/web_quickstart.html#static-files)
