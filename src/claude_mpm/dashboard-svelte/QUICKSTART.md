# Svelte Dashboard - Quick Start

## Build & Run (30 seconds)

```bash
# 1. Build the dashboard
./scripts/build-svelte-dashboard.sh

# 2. Start the server
claude-mpm monitor start

# 3. Open in browser
open http://localhost:8765/svelte
```

## Development Mode

```bash
cd src/claude_mpm/dashboard-svelte
npm run dev
# Opens http://localhost:5173 with hot reload
```

## Routes

| URL | Dashboard |
|-----|-----------|
| http://localhost:8765/ | Legacy HTML dashboard |
| http://localhost:8765/svelte | **New Svelte dashboard** |
| http://localhost:8765/dashboard | Full dashboard template |

## How It Works

1. **Build**: `npm run build` → outputs to `../dashboard/static/svelte-build/`
2. **Serve**: Python server serves at `/svelte` route
3. **Connect**: Socket.IO connection to same server (port 8765)
4. **Stream**: Real-time events from Claude Code hooks

## Verify Integration

```bash
# Build exists
ls src/claude_mpm/dashboard/static/svelte-build/index.html

# Server logs
claude-mpm monitor status

# Test connection
curl http://localhost:8765/svelte
```

## Troubleshooting

**White screen?**
```bash
./scripts/build-svelte-dashboard.sh
claude-mpm monitor restart
```

**404 on /_app/ assets?**
```bash
ls src/claude_mpm/dashboard/static/svelte-build/_app/
```

**Socket.IO not connecting?**
```bash
claude-mpm monitor status
lsof -i :8765
```

---

📖 **Full docs**: See `INTEGRATION.md` for architecture details
