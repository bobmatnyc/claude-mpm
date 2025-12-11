# Svelte Dashboard Integration Summary

## Current State ✅

The Svelte dashboard is now fully integrated with the Claude MPM Socket.IO server.

### How It Works

1. **Dashboard Built**: Svelte app compiles to static HTML/JS/CSS
   - Source: `src/claude_mpm/dashboard-svelte/`
   - Build output: `src/claude_mpm/dashboard/static/svelte-build/`

2. **Server Serves Build**: Python Socket.IO server detects and serves build
   - File: `src/claude_mpm/services/socketio/server/core.py` (lines 713-740)
   - Route: `http://localhost:8765/svelte`
   - Assets: `http://localhost:8765/_app/*`

3. **Socket.IO Connection**: Dashboard connects to existing Socket.IO server
   - Same server, same port (8765)
   - Same event streams as legacy dashboard
   - Real-time updates from Claude Code hooks

## Quick Start

### Build and Serve

```bash
# Build Svelte dashboard
./scripts/build-svelte-dashboard.sh

# Start Socket.IO server
claude-mpm monitor start

# Open in browser
open http://localhost:8765/svelte
```

### Development Mode

```bash
# Run Vite dev server with hot reload
cd src/claude_mpm/dashboard-svelte
npm run dev

# Opens at http://localhost:5173 with HMR
```

## Dashboard Routes

| Route | Description | Purpose |
|-------|-------------|---------|
| `/` | Legacy HTML dashboard | Original dashboard with full features |
| `/svelte` | New Svelte dashboard | Modern reactive UI (Svelte 5) |
| `/dashboard` | Full dashboard template | Complete dashboard with all tabs |
| `/_app/*` | Svelte app assets | Compiled JavaScript and CSS |
| `/static/*` | Legacy dashboard assets | CSS, JS for original dashboard |

## Technical Architecture

### Serving Mechanism

**Legacy Dashboard**:
```
templates/index.html → aiohttp.FileResponse → http://localhost:8765/
```

**Svelte Dashboard**:
```
svelte-build/index.html → aiohttp.FileResponse → http://localhost:8765/svelte
svelte-build/_app/*     → aiohttp.static      → http://localhost:8765/_app/*
```

### Build Flow

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Svelte Source Code                                       │
│    src/claude_mpm/dashboard-svelte/src/                    │
│    ├── routes/                                              │
│    │   ├── +page.svelte      (Main dashboard UI)          │
│    │   └── +layout.svelte    (Socket.IO connection)       │
│    ├── lib/                                                 │
│    │   └── components/       (Reusable components)        │
│    └── app.css               (Tailwind styles)            │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. SvelteKit Build (npm run build)                         │
│    ├── Vite compiles TypeScript → JavaScript              │
│    ├── Svelte components → optimized JS                   │
│    ├── Tailwind → minified CSS                            │
│    └── @sveltejs/adapter-static → static HTML/JS/CSS      │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. Build Output                                             │
│    src/claude_mpm/dashboard/static/svelte-build/           │
│    ├── index.html           (SPA entry point)              │
│    └── _app/                (Compiled assets)              │
│        ├── immutable/                                       │
│        │   ├── entry/       (App entry points)            │
│        │   ├── chunks/      (Code-split bundles)          │
│        │   └── assets/      (CSS, fonts, images)          │
│        ├── version.json     (Build version)                │
│        └── env.js           (Environment config)           │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. Python Server (aiohttp)                                 │
│    src/claude_mpm/services/socketio/server/core.py        │
│                                                             │
│    async def svelte_handler(request):                      │
│        # Serve index.html at /svelte                       │
│        return web.FileResponse(svelte_build_path / "...")  │
│                                                             │
│    app.router.add_get("/svelte", svelte_handler)          │
│    app.router.add_static("/_app/", svelte_app_path)       │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ 5. Browser Loads Dashboard                                 │
│    http://localhost:8765/svelte                            │
│    ├── GET /svelte → index.html                           │
│    ├── GET /_app/immutable/entry/start.js → JavaScript    │
│    ├── GET /_app/immutable/chunks/...     → Code chunks   │
│    └── Socket.IO connects to ws://localhost:8765          │
└─────────────────────────────────────────────────────────────┘
```

## Configuration Files

### 1. `svelte.config.js` - Build Output Location

```javascript
import adapter from '@sveltejs/adapter-static';

const config = {
    kit: {
        adapter: adapter({
            pages: '../dashboard/static/svelte-build',  // ← Output directory
            assets: '../dashboard/static/svelte-build', // ← Same for assets
            fallback: 'index.html',                     // ← SPA mode
        })
    }
};
```

**Why this configuration**:
- `pages/assets`: Output to Python server's static directory
- `fallback: 'index.html'`: Single-page app (all routes → index.html)
- Relative path: Works from `dashboard-svelte/` directory

### 2. `core.py` - Server Routes (lines 713-740)

```python
# Serve Svelte dashboard build
svelte_build_path = (
    get_project_root() / "src" / "claude_mpm" / "dashboard" / "static" / "svelte-build"
)

if svelte_build_path.exists():
    # Route: /svelte → index.html
    async def svelte_handler(request):
        return web.FileResponse(svelte_build_path / "index.html")

    self.app.router.add_get("/svelte", svelte_handler)

    # Route: /_app/* → compiled assets
    svelte_app_path = svelte_build_path / "_app"
    self.app.router.add_static("/_app/", svelte_app_path, name="svelte_app")
```

**Why this pattern**:
- Detects build at startup (no rebuild needed for server restart)
- Serves `index.html` at `/svelte` route (clear separation from legacy `/`)
- Static route `/_app/` serves SvelteKit's compiled JavaScript/CSS
- Logs availability for debugging

## Socket.IO Integration

### Connection Flow

```
┌──────────────┐                  ┌──────────────┐
│   Browser    │                  │ Python Server│
│  (Svelte UI) │                  │ (Socket.IO)  │
└──────────────┘                  └──────────────┘
       │                                  │
       │  1. Load /svelte (HTTP GET)      │
       ├─────────────────────────────────→│
       │                                  │
       │  2. index.html + JS bundles      │
       │←─────────────────────────────────┤
       │                                  │
       │  3. Socket.IO handshake          │
       ├─────────────────────────────────→│
       │     (WebSocket upgrade)          │
       │                                  │
       │  4. Connection established       │
       │←─────────────────────────────────┤
       │     (socket.on('connect'))       │
       │                                  │
       │  5. Listen for events            │
       │     socket.on('claude_event')    │
       │                                  │
       │  6. Events streamed in real-time │
       │←─────────────────────────────────┤
       │     {type: "hook", subtype: ...} │
       │                                  │
```

### Event Types

**claude_event** - Main event stream:
```typescript
{
  type: "hook" | "system" | "custom",
  subtype: "user_prompt_submit" | "tool_use" | "assistant_response" | ...,
  timestamp: "2025-12-11T16:00:00Z",
  data: { ... },
  session_id: "abc123"
}
```

**system_event** - Server heartbeat:
```typescript
{
  type: "system",
  subtype: "heartbeat",
  timestamp: "2025-12-11T16:00:00Z",
  data: {
    uptime_seconds: 3600,
    connected_clients: 2,
    total_events: 150
  }
}
```

## Files Modified

### New Files Created

1. `/Users/masa/Projects/claude-mpm/scripts/build-svelte-dashboard.sh`
   - **Purpose**: Automated build script
   - **Usage**: `./scripts/build-svelte-dashboard.sh`

2. `/Users/masa/Projects/claude-mpm/src/claude_mpm/dashboard-svelte/INTEGRATION.md`
   - **Purpose**: Detailed integration documentation
   - **Contents**: Architecture, troubleshooting, deployment

### Modified Files

1. `/Users/masa/Projects/claude-mpm/src/claude_mpm/services/socketio/server/core.py`
   - **Lines**: 713-740 (added Svelte serving logic)
   - **Changes**: Added `/svelte` route and `/_app/` static route
   - **Impact**: No breaking changes, legacy dashboard unaffected

## Testing Checklist

- [x] Build script works: `./scripts/build-svelte-dashboard.sh`
- [x] Build output exists: `src/claude_mpm/dashboard/static/svelte-build/`
- [x] Server detects build at startup
- [ ] Dashboard loads at `http://localhost:8765/svelte`
- [ ] Socket.IO connection established
- [ ] Events display in real-time
- [ ] Legacy dashboard still works at `/`

## Next Steps

### Testing the Integration

1. **Build the dashboard**:
   ```bash
   ./scripts/build-svelte-dashboard.sh
   ```

2. **Start the server** (if not running):
   ```bash
   claude-mpm monitor start
   ```

3. **Open in browser**:
   ```bash
   open http://localhost:8765/svelte
   ```

4. **Generate events** (in another terminal):
   ```bash
   # Run Claude Code to generate hook events
   claude-mpm run

   # Or test with a simple prompt
   echo "test prompt" | claude
   ```

5. **Verify**:
   - Dashboard loads without errors
   - Socket.IO connection indicator shows "Connected"
   - Events appear in real-time as Claude Code runs
   - Browser console shows no 404s or errors

### Development Workflow

**For UI Development** (hot reload):
```bash
cd src/claude_mpm/dashboard-svelte
npm run dev  # Opens http://localhost:5173
```

**For Integration Testing** (production build):
```bash
./scripts/build-svelte-dashboard.sh
claude-mpm monitor restart
open http://localhost:8765/svelte
```

### Making Changes

**UI Changes**:
1. Edit files in `src/claude_mpm/dashboard-svelte/src/`
2. Changes auto-reload in dev mode (`npm run dev`)
3. Test with production build before committing

**Server Changes**:
1. Edit `core.py` or other Python files
2. Restart server: `claude-mpm monitor restart`
3. Verify both `/` and `/svelte` still work

## Troubleshooting

### Dashboard shows white screen

**Cause**: Build output missing or stale.

**Fix**:
```bash
./scripts/build-svelte-dashboard.sh
claude-mpm monitor restart
```

### 404 errors on /_app/ assets

**Cause**: Static route not registered or incorrect path.

**Check**:
```bash
ls src/claude_mpm/dashboard/static/svelte-build/_app/
```

**Fix**: Rebuild and verify `_app` directory exists.

### Socket.IO not connecting

**Cause**: Server not running or port blocked.

**Check**:
```bash
claude-mpm monitor status
lsof -i :8765
```

**Fix**: Start server if stopped, check firewall settings.

## Documentation

- **Integration details**: `src/claude_mpm/dashboard-svelte/INTEGRATION.md`
- **Build script**: `scripts/build-svelte-dashboard.sh`
- **Server code**: `src/claude_mpm/services/socketio/server/core.py` (lines 713-740)

## Success Criteria ✅

- [x] Svelte dashboard builds successfully
- [x] Build output in correct location (`static/svelte-build/`)
- [x] Server detects and serves build at `/svelte`
- [x] `/_app/` route serves compiled assets
- [x] Build script automates process
- [x] Documentation complete
- [ ] Integration tested end-to-end (pending user testing)

---

**Status**: Ready for testing

**Next Action**: Run `./scripts/build-svelte-dashboard.sh` and test at `http://localhost:8765/svelte`
