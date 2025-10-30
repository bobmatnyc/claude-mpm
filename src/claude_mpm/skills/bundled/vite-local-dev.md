---
skill_id: vite-local-dev
skill_version: 0.1.0
description: Maximizing Vite's development server performance, managing HMR effectively, and avoiding process management pitfalls.
updated_at: 2025-10-30T17:00:00Z
tags: [vite, development, hmr, frontend, build-tool]
---

# Vite Local Development Server

## Overview

Vite is a next-generation frontend build tool that provides blazing-fast Hot Module Replacement (HMR) and optimized builds. It leverages native ES modules during development and Rollup for production builds. This skill focuses on maximizing Vite's development server performance, managing HMR effectively, and avoiding process management pitfalls.

## When to Use This Skill

- Setting up Vite development environment
- Optimizing HMR and development server performance
- Troubleshooting HMR connection issues
- Configuring Vite for different frontend frameworks (React, Vue, Svelte)
- Managing proxy configuration for API backends
- Resolving WebSocket and CORS issues
- Understanding when NOT to use PM2 with Vite dev server

## Quick Start

### Development Server

**Basic Vite Development:**
```bash
# Start dev server
npm run dev
# or
yarn dev
# or
pnpm dev
```

**Custom Port and Host:**
```bash
# CLI flags
npm run dev -- --port 3001 --host 0.0.0.0

# Or set in package.json
```

**Force Optimization:**
```bash
# Force dependency pre-bundling
npm run dev -- --force
```

**Open in Browser:**
```bash
# Automatically open browser
npm run dev -- --open
```

### Basic Vite Config

```javascript
// vite.config.js
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    host: true, // Listen on all addresses
    open: true, // Auto-open browser
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
  },
});
```

### With Docker

**Development Dockerfile:**
```dockerfile
FROM node:18-alpine

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
```

**Docker Compose:**
```yaml
version: '3.8'

services:
  vite-app:
    build: .
    ports:
      - "5173:5173"
    volumes:
      - .:/app
      - /app/node_modules
    environment:
      - NODE_ENV=development
      - CHOKIDAR_USEPOLLING=false
    command: npm run dev -- --host 0.0.0.0
```

## Configuration Patterns

### HMR Configuration and Optimization

**Vite HMR Settings:**
```javascript
// vite.config.js
export default defineConfig({
  server: {
    hmr: {
      protocol: 'ws',
      host: 'localhost',
      port: 5173,
      // For Docker or reverse proxy
      clientPort: 5173,
    },
  },
});
```

**HMR with Reverse Proxy:**
```javascript
// vite.config.js
export default defineConfig({
  server: {
    hmr: {
      protocol: 'wss', // Use secure WebSocket
      host: 'your-domain.com',
      clientPort: 443,
    },
  },
});
```

**HMR Overlay Configuration:**
```javascript
// vite.config.js
export default defineConfig({
  server: {
    hmr: {
      overlay: true, // Show error overlay
    },
  },
});
```

**Disable HMR (Not Recommended):**
```javascript
// Only for debugging HMR issues
export default defineConfig({
  server: {
    hmr: false,
  },
});
```

### WebSocket Proxy Setup

**API Proxy Configuration:**
```javascript
// vite.config.js
export default defineConfig({
  server: {
    proxy: {
      // Proxy API requests
      '/api': {
        target: 'http://localhost:4000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
      // Proxy WebSocket connections
      '/ws': {
        target: 'ws://localhost:4000',
        ws: true,
      },
    },
  },
});
```

**Advanced Proxy with Custom Logic:**
```javascript
// vite.config.js
export default defineConfig({
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:4000',
        changeOrigin: true,
        secure: false,
        configure: (proxy, options) => {
          // Custom proxy configuration
          proxy.on('error', (err, req, res) => {
            console.log('proxy error', err);
          });
          proxy.on('proxyReq', (proxyReq, req, res) => {
            console.log('Sending Request:', req.method, req.url);
          });
          proxy.on('proxyRes', (proxyRes, req, res) => {
            console.log('Received Response:', proxyRes.statusCode, req.url);
          });
        },
      },
    },
  },
});
```

**CORS Configuration:**
```javascript
// vite.config.js
export default defineConfig({
  server: {
    cors: true, // Enable CORS for all origins
    // Or specify origins
    cors: {
      origin: ['http://localhost:3000', 'https://example.com'],
      credentials: true,
    },
  },
});
```

### Pre-bundling Dependencies

**Dependency Optimization:**
```javascript
// vite.config.js
export default defineConfig({
  optimizeDeps: {
    // Include dependencies that should be pre-bundled
    include: ['react', 'react-dom', 'lodash-es'],
    // Exclude dependencies from pre-bundling
    exclude: ['@custom/local-package'],
    // Force pre-bundle even if cached
    force: false,
  },
});
```

**Why Pre-bundling Matters:**
- Converts CommonJS/UMD to ESM
- Reduces network requests by bundling many modules
- Improves initial page load performance

**Clear Pre-bundle Cache:**
```bash
# Delete Vite cache
rm -rf node_modules/.vite

# Restart with force flag
npm run dev -- --force
```

### WSL2 Specific Configuration

**File Watching in WSL2:**

WSL2 has limitations with file system events across Windows-Linux boundary.

**Option 1: Use Polling (Simple but CPU-intensive)**
```javascript
// vite.config.js
export default defineConfig({
  server: {
    watch: {
      usePolling: true,
      interval: 1000, // Check every second
    },
  },
});
```

**Option 2: Project in WSL Filesystem (Recommended)**
```bash
# Store project in Linux filesystem, not /mnt/c/
cd ~/projects
git clone <repo>
npm install
npm run dev
```

**Option 3: Environment Variable**
```bash
# Set polling via environment
CHOKIDAR_USEPOLLING=true npm run dev
```

**Performance Consideration:**
- Polling increases CPU usage
- Native WSL2 filesystem is 10-20x faster
- Avoid crossing Windows-Linux filesystem boundary

### Performance Optimization

**Optimize Large Projects:**
```javascript
// vite.config.js
export default defineConfig({
  server: {
    // Increase file size limit for large files
    fs: {
      strict: false, // Allow serving files outside root
    },
  },
  optimizeDeps: {
    // Pre-bundle heavy dependencies
    include: [
      'react',
      'react-dom',
      'react-router-dom',
      '@mui/material',
      'lodash-es',
    ],
  },
  build: {
    // Production optimizations
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom'],
          ui: ['@mui/material'],
        },
      },
    },
  },
});
```

**Reduce Bundle Size:**
```javascript
// vite.config.js
export default defineConfig({
  build: {
    minify: 'terser',
    terserOptions: {
      compress: {
        drop_console: true, // Remove console.logs in production
      },
    },
    // Chunk size warnings
    chunkSizeWarningLimit: 1000,
  },
});
```

**Tree Shaking Optimization:**

Use named imports for better tree shaking:
```javascript
// Bad - imports entire library
import _ from 'lodash';

// Good - tree-shakeable
import { debounce } from 'lodash-es';

// Best - direct import
import debounce from 'lodash-es/debounce';
```

### Named vs Default Exports for HMR

**Best Practice: Use Named Exports**

Default exports can cause HMR issues in some cases:

```javascript
// Not ideal for HMR
export default function MyComponent() {
  return <div>Hello</div>;
}

// Better for HMR
export function MyComponent() {
  return <div>Hello</div>;
}

// Usage
import { MyComponent } from './MyComponent';
```

**Why Named Exports Are Better:**
- More predictable HMR behavior
- Better tree shaking
- Easier refactoring and IDE support
- Less ambiguity in module imports

**React Fast Refresh Compatibility:**
```javascript
// Component with named export (preferred)
export function Counter() {
  const [count, setCount] = useState(0);
  return <button onClick={() => setCount(count + 1)}>{count}</button>;
}

// With HMR preservation
if (import.meta.hot) {
  import.meta.hot.accept();
}
```

### Environment Variables

**Vite Environment Variables:**

```bash
# .env
VITE_API_URL=http://localhost:4000
VITE_APP_TITLE=My App

# .env.local (not committed)
VITE_SECRET_KEY=super-secret
```

**Access in Code:**
```javascript
// Only VITE_* variables are exposed to client
const apiUrl = import.meta.env.VITE_API_URL;
const mode = import.meta.env.MODE; // 'development' or 'production'
const isDev = import.meta.env.DEV; // boolean
const isProd = import.meta.env.PROD; // boolean
```

**Type Safety with TypeScript:**
```typescript
// vite-env.d.ts
/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL: string;
  readonly VITE_APP_TITLE: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
```

**Load Order:**
1. `.env.local` (highest priority)
2. `.env.[mode].local`
3. `.env.[mode]`
4. `.env`

## Framework-Specific Best Practices

### React with Vite

**Plugin Configuration:**
```javascript
// vite.config.js
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [
    react({
      // Fast Refresh options
      fastRefresh: true,
      // Babel options
      babel: {
        plugins: ['babel-plugin-styled-components'],
      },
    }),
  ],
});
```

**React Fast Refresh Rules:**
- Components must be named functions or arrow functions
- File should export components (named or default)
- Avoid exporting both components and non-component values

```javascript
// Good - Fast Refresh works
export function App() {
  return <div>Hello</div>;
}

// Bad - Fast Refresh breaks
export const data = { foo: 'bar' };
export function App() {
  return <div>Hello</div>;
}
```

### Vue with Vite

**Plugin Configuration:**
```javascript
// vite.config.js
import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';

export default defineConfig({
  plugins: [
    vue({
      // Template compilation options
      template: {
        compilerOptions: {
          isCustomElement: (tag) => tag.startsWith('custom-'),
        },
      },
    }),
  ],
});
```

**Vue SFC HMR:**
- Template changes → HMR update
- Script changes → Full reload (preserves component state when possible)
- Style changes → HMR update

### Svelte with Vite

**Plugin Configuration:**
```javascript
// vite.config.js
import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';

export default defineConfig({
  plugins: [
    svelte({
      hot: true, // Enable HMR
      compilerOptions: {
        dev: true,
      },
    }),
  ],
});
```

## Common Problems & Solutions

### Problem 1: HMR Not Working

**Symptoms:**
- Code changes don't update in browser
- Need manual refresh after every change
- Console shows "WebSocket connection failed"

**Root Cause:**
WebSocket connection broken, PM2 interference, Docker networking, or reverse proxy misconfiguration.

**Solution:**

**Step 1: Verify Direct Dev Server**
```bash
# Stop PM2 if running (PM2 breaks HMR)
pm2 stop all

# Run dev server directly
npm run dev
```

**Step 2: Check WebSocket Connection**

Open browser console and look for:
```
[vite] connected.
```

If not connected, check HMR config:
```javascript
// vite.config.js
export default defineConfig({
  server: {
    hmr: {
      protocol: 'ws',
      host: 'localhost',
    },
  },
});
```

**Step 3: Docker HMR Configuration**

For Docker, expose HMR to host:
```javascript
// vite.config.js
export default defineConfig({
  server: {
    host: '0.0.0.0',
    port: 5173,
    hmr: {
      clientPort: 5173,
    },
    watch: {
      usePolling: true, // If file changes not detected
    },
  },
});
```

**Step 4: Clear Cache and Restart**
```bash
rm -rf node_modules/.vite
npm run dev
```

**Step 5: Check Firewall/Network**
```bash
# Ensure port is accessible
netstat -an | grep 5173
```

### Problem 2: Slow Cold Start

**Symptoms:**
- Initial server startup takes 10+ seconds
- "Optimizing dependencies" runs every time
- High CPU usage during startup

**Root Cause:**
Unoptimized dependencies, missing pre-bundling configuration, or large project with many files.

**Solution:**

**Step 1: Pre-bundle Heavy Dependencies**
```javascript
// vite.config.js
export default defineConfig({
  optimizeDeps: {
    include: [
      'react',
      'react-dom',
      'react-router-dom',
      '@mui/material',
      'lodash-es',
    ],
  },
});
```

**Step 2: Use Dependency Caching**

Vite caches pre-bundled dependencies. If cache is rebuilt frequently:
```javascript
// vite.config.js
export default defineConfig({
  optimizeDeps: {
    force: false, // Don't force rebuild
  },
  cacheDir: 'node_modules/.vite', // Explicit cache location
});
```

**Step 3: Optimize Imports**

Use direct imports for tree shaking:
```javascript
// Slow - imports entire library
import { Button } from '@mui/material';

// Fast - direct import
import Button from '@mui/material/Button';
```

**Step 4: Reduce Watched Files**

Exclude unnecessary directories:
```javascript
// vite.config.js
export default defineConfig({
  server: {
    watch: {
      ignored: ['**/node_modules/**', '**/dist/**', '**/.git/**'],
    },
  },
});
```

**Step 5: Use SSD for node_modules**

If project is on network drive or slow disk, move node_modules:
```bash
# Use local disk for node_modules
npm config set cache /path/to/fast/disk/.npm
```

### Problem 3: Port Already in Use

**Symptoms:**
```
Port 5173 is in use, trying another one...
# or
Error: listen EADDRINUSE: address already in use :::5173
```

**Root Cause:**
Previous Vite instance, another dev server, or zombie process using the port.

**Solution:**

**Option A: Kill Process**
```bash
# macOS/Linux
lsof -ti:5173 | xargs kill -9

# Windows
netstat -ano | findstr :5173
taskkill /PID <PID> /F
```

**Option B: Use Different Port**
```bash
npm run dev -- --port 3001
```

**Option C: Auto-increment Port**

Vite automatically tries next port if default is taken:
```javascript
// vite.config.js
export default defineConfig({
  server: {
    port: 5173,
    strictPort: false, // Try next available port
  },
});
```

**Option D: Cleanup Script**
```json
{
  "scripts": {
    "predev": "kill-port 5173 || true",
    "dev": "vite"
  }
}
```

### Problem 4: PM2 Breaks HMR

**Symptoms:**
- HMR works without PM2 but fails with PM2
- WebSocket connections drop
- Page doesn't update on file changes

**Root Cause:**
PM2's process management interferes with Vite's HMR WebSocket connections.

**Solution:**

**NEVER use PM2 for Vite development server.**

**Wrong:**
```bash
# Don't do this
pm2 start npm --name "vite-dev" -- run dev
```

**Correct:**
```bash
# Run Vite directly
npm run dev
```

**Why PM2 Breaks Vite HMR:**
- PM2 wraps the process, breaking WebSocket connections
- Process restarts disconnect HMR clients
- Watch mode conflicts with Vite's file watching

**For Production:**

Build static files, serve with any static server:
```bash
# Build
npm run build

# Serve with simple HTTP server (not PM2)
npx serve -s dist -p 5173

# Or use nginx, Apache, or CDN
```

**PM2 is for backend servers, not frontend build tools.**

### Problem 5: WSL2 File Watching Issues

**Symptoms:**
- Changes in Windows files not detected by Vite in WSL2
- Need to manually restart server
- High CPU usage with polling

**Root Cause:**
File system events don't cross Windows-Linux boundary efficiently.

**Solution:**

**Option 1: Move Project to WSL2 Filesystem (Best)**
```bash
# Move to WSL2 native filesystem
cd ~
mkdir projects
cd projects
git clone <repo>
npm install
npm run dev
```

**Option 2: Enable Polling (Fallback)**
```javascript
// vite.config.js
export default defineConfig({
  server: {
    watch: {
      usePolling: true,
      interval: 1000,
    },
  },
});
```

**Option 3: Environment Variable**
```bash
CHOKIDAR_USEPOLLING=true npm run dev
```

**Performance Comparison:**
- Native WSL2 filesystem: Fast, low CPU
- Polling from /mnt/c/: Slow, high CPU
- Native file watching from /mnt/c/: Doesn't work

**Recommendation:** Always develop in WSL2 native filesystem (`~/projects`), not in `/mnt/c/`.

## Anti-Patterns

### What NOT to Do

**1. Never Use PM2 for Vite Dev Server**
```bash
# WRONG - Breaks HMR completely
pm2 start npm --name "vite-dev" -- run dev
```

Why: PM2 breaks WebSocket connections required for HMR.

**2. Don't Use Vite Dev Server in Production**
```bash
# WRONG for production
npm run dev
```

Correct:
```bash
npm run build
npx serve -s dist
```

**3. Don't Ignore Pre-bundling Optimization**
```javascript
// WRONG - misses optimization opportunity
// No optimizeDeps configuration
```

Correct:
```javascript
// Pre-bundle heavy dependencies
export default defineConfig({
  optimizeDeps: {
    include: ['react', 'react-dom', 'lodash-es'],
  },
});
```

**4. Don't Use Polling in Native Filesystem**
```javascript
// WRONG - unnecessary CPU usage
export default defineConfig({
  server: {
    watch: {
      usePolling: true, // Only needed for WSL/Docker
    },
  },
});
```

Use polling only in WSL2 or Docker where native watching doesn't work.

**5. Don't Mix Default and Named Exports**
```javascript
// WRONG - confuses HMR
export default function App() {}
export const utils = {};
```

Stick to named exports for components:
```javascript
// Better
export function App() {}
```

**6. Don't Import Entire Libraries**
```javascript
// WRONG - imports everything
import _ from 'lodash';
import * as MaterialUI from '@mui/material';
```

Use tree-shakeable imports:
```javascript
// Correct
import { debounce } from 'lodash-es';
import Button from '@mui/material/Button';
```

**7. Don't Expose Secrets via VITE_ Prefix**
```bash
# WRONG - exposed to client
VITE_API_SECRET=super-secret-key
```

VITE_ prefixed variables are in client bundle. Use backend for secrets.

## Quick Reference

### Commands

```bash
# Development
npm run dev                           # Start dev server
npm run dev -- --port 3001            # Custom port
npm run dev -- --host 0.0.0.0         # Listen on all interfaces
npm run dev -- --open                 # Auto-open browser
npm run dev -- --force                # Force dependency pre-bundling

# Production
npm run build                         # Build for production
npm run preview                       # Preview production build
npx serve -s dist                     # Serve built files

# Maintenance
rm -rf node_modules/.vite             # Clear Vite cache
rm -rf dist                           # Clear build output
lsof -ti:5173 | xargs kill -9         # Kill process on port

# WSL2
CHOKIDAR_USEPOLLING=true npm run dev  # Enable polling
```

### Configuration Templates

**Minimal vite.config.js:**
```javascript
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    open: true,
  },
});
```

**Optimized vite.config.js:**
```javascript
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: true,
    open: true,
    hmr: {
      overlay: true,
    },
    proxy: {
      '/api': {
        target: 'http://localhost:4000',
        changeOrigin: true,
      },
    },
  },
  optimizeDeps: {
    include: ['react', 'react-dom', 'react-router-dom'],
  },
  build: {
    sourcemap: true,
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom'],
        },
      },
    },
  },
});
```

**WSL2/Docker vite.config.js:**
```javascript
export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    hmr: {
      clientPort: 5173,
    },
    watch: {
      usePolling: true,
      interval: 1000,
    },
  },
});
```

**Full Stack with API Proxy:**
```javascript
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:4000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
      '/ws': {
        target: 'ws://localhost:4000',
        ws: true,
      },
    },
  },
});
```

## Related Skills

- **nextjs-local-dev** - For Next.js with similar HMR patterns
- **docker-containerization** - For containerized Vite applications
- **systematic-debugging** - For complex debugging scenarios
- **express-local-dev** - For full-stack applications with Express backend

---

**Vite Version Compatibility:** This skill covers Vite 4.0+ and Vite 5.0+. Most patterns are stable across versions.

**Last Updated:** 2024 - Reflects current Vite best practices and HMR optimization techniques.
