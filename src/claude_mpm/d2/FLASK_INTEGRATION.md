# Flask Integration Guide

## Adding Dashboard2 Route to Flask Server

Add these routes to your Flask application (in `src/claude_mpm/services/monitor/server.py` or appropriate Flask app file):

### Option 1: Add to UnifiedMonitorServer._setup_http_routes()

```python
def _setup_http_routes(self):
    """Setup HTTP routes for the dashboard."""
    try:
        # ... existing routes ...

        # Dashboard2 route
        dashboard2_dir = Path(__file__).parent.parent.parent / "dashboard2" / "dist"

        async def dashboard2_index(request):
            """Serve Dashboard2 Svelte app"""
            index_path = dashboard2_dir / "index.html"
            if index_path.exists():
                with index_path.open() as f:
                    content = f.read()
                return web.Response(text=content, content_type="text/html")
            return web.Response(text="Dashboard2 not found", status=404)

        # Register dashboard2 routes
        self.app.router.add_get("/dashboard2", dashboard2_index)

        # Serve dashboard2 static assets
        if dashboard2_dir.exists():
            async def dashboard2_assets(request):
                """Serve static files for dashboard2"""
                from aiohttp.web_fileresponse import FileResponse

                # Get the relative path from the request
                rel_path = request.match_info["filepath"]
                file_path = dashboard2_dir / rel_path

                if not file_path.exists() or not file_path.is_file():
                    raise web.HTTPNotFound()

                return FileResponse(file_path)

            self.app.router.add_get("/dashboard2/{filepath:.*}", dashboard2_assets)

        # ... rest of routes ...
```

### Option 2: Standalone Flask Route (for testing)

If you want to test with a simple Flask app:

```python
from flask import Flask, send_from_directory
from pathlib import Path

app = Flask(__name__)

DASHBOARD2_DIR = Path(__file__).parent / "dashboard2" / "dist"

@app.route('/dashboard2')
def dashboard2():
    """Serve the Svelte dashboard"""
    return send_from_directory(DASHBOARD2_DIR, 'index.html')

@app.route('/dashboard2/<path:path>')
def dashboard2_assets(path):
    """Serve dashboard2 static assets"""
    return send_from_directory(DASHBOARD2_DIR, path)

if __name__ == '__main__':
    app.run(debug=True, port=8765)
```

## Important Notes

### Base Path Configuration

The Vite build is configured with `base: '/dashboard2/'` which means:
- All asset paths will be prefixed with `/dashboard2/`
- The dashboard expects to be served at `/dashboard2` route
- Assets will load from `/dashboard2/assets/*`

If you need a different base path:
1. Edit `vite.config.js` and change `base: '/your-path/'`
2. Rebuild: `npm run build`
3. Update Flask routes accordingly

### Socket.IO Connection

The dashboard connects to Socket.IO at `http://localhost:8765` by default.

To change the connection settings:
1. Edit `src/stores/socket.svelte.js`
2. Change `DEFAULT_PORT` and `DEFAULT_HOST`
3. Rebuild: `npm run build`

Or you can make it configurable via environment variables or URL parameters in future iterations.

## Testing the Integration

1. **Ensure monitor server is running**:
   ```bash
   # Check if server is running
   curl http://localhost:8765/health
   ```

2. **Access Dashboard2**:
   ```
   http://localhost:8765/dashboard2
   ```

3. **Verify Socket.IO connection**:
   - Check header shows "Connected" status
   - Green indicator appears
   - Port number displays correctly

4. **Test event reception**:
   - Trigger a Claude Code event
   - Event should appear in Events tab
   - Click event to expand JSON details

## Deployment Checklist

- [ ] Build dashboard: `cd dashboard2 && npm run build`
- [ ] Add Flask routes for `/dashboard2` and assets
- [ ] Verify static files are served correctly
- [ ] Test Socket.IO connection
- [ ] Verify events are received and displayed
- [ ] Check console for errors
- [ ] Test on production server

## Troubleshooting

### 404 on Dashboard2 Route
- Verify `dist/` folder exists
- Check Flask route path matches
- Ensure file permissions are correct

### Assets Not Loading (404 on CSS/JS)
- Verify base path in `vite.config.js` matches Flask route
- Check browser DevTools Network tab for failed requests
- Ensure `/dashboard2/assets/*` route is registered

### Socket.IO Connection Failed
- Check monitor server is running on port 8765
- Verify no CORS issues (Socket.IO configured with `cors_allowed_origins="*"`)
- Check browser console for connection errors
- Verify firewall/network allows WebSocket connections

### No Events Appearing
- Check Socket.IO connection status (should be green)
- Verify events are being emitted from server
- Check browser console for incoming events
- Test with: `client.socket.onAny((event, ...args) => console.log(event, args))`
