---
skill_id: nextjs-local-dev
skill_version: 0.1.0
description: Managing Next.js development servers effectively, including direct dev server usage, PM2 for production deployments, and troubleshooting.
updated_at: 2025-10-30T17:00:00Z
tags: [nextjs, react, development, server]
---

# Next.js Local Development Server

## Overview

Next.js is a React framework for building full-stack web applications with built-in optimizations, routing, and rendering strategies. This skill focuses on managing Next.js development servers effectively, including direct dev server usage, PM2 for production deployments, and troubleshooting common development issues.

## When to Use This Skill

- Setting up Next.js development environment
- Configuring Turbopack for faster development
- Troubleshooting server startup and HMR issues
- Configuring PM2 for Next.js production deployments
- Resolving port conflicts and process management
- Optimizing development server performance
- Managing environment variables and configuration

## Quick Start

### Development Server

**Standard Development (Node.js):**
```bash
npm run dev
# or
yarn dev
# or
pnpm dev
```

**With Turbopack (Next.js 13+):**
```bash
npm run dev -- --turbo
# or add to package.json
```

**Custom Port:**
```bash
npm run dev -- -p 3001
# or
PORT=3001 npm run dev
```

### With PM2 (Production Only)

**Important:** PM2 should ONLY be used for production builds, NOT development servers. The dev server needs direct process control for HMR and file watching.

```bash
# Build first
npm run build

# Start with PM2
pm2 start npm --name "nextjs-app" -- start
```

### With Docker

```dockerfile
# Development Dockerfile
FROM node:18-alpine

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

EXPOSE 3000

CMD ["npm", "run", "dev"]
```

**Docker Compose:**
```yaml
version: '3.8'
services:
  nextjs:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    volumes:
      - .:/app
      - /app/node_modules
      - /app/.next
    environment:
      - NODE_ENV=development
```

## Configuration Patterns

### Recommended PM2 Config (Production Only)

```javascript
// ecosystem.config.js
module.exports = {
  apps: [{
    name: 'nextjs-prod',
    script: 'npm',
    args: 'start',
    instances: 'max',
    exec_mode: 'cluster',
    env: {
      NODE_ENV: 'production',
      PORT: 3000
    },
    error_file: './logs/pm2-error.log',
    out_file: './logs/pm2-out.log',
    log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
    merge_logs: true,
    autorestart: true,
    max_memory_restart: '1G',
    // NO watch mode for production
    watch: false
  }]
};
```

### Port Management

**Method 1: CLI Flag (Highest Priority)**
```bash
npm run dev -- -p 3001
```

**Method 2: Environment Variable**
```bash
# .env.local
PORT=3001
```

```bash
# Command line
PORT=3001 npm run dev
```

**Method 3: Package.json Script**
```json
{
  "scripts": {
    "dev": "next dev -p 3001",
    "dev:turbo": "next dev --turbo -p 3001"
  }
}
```

**Method 4: Next.js Config**
```javascript
// next.config.js
module.exports = {
  // Note: Port must still be set via CLI or env var
  // This config doesn't control dev server port
  serverRuntimeConfig: {
    port: process.env.PORT || 3000
  }
};
```

### Environment Variables

**Development Variables (.env.local):**
```bash
# Server Configuration
PORT=3000
NODE_ENV=development

# Turbopack Configuration
NEXT_TURBOPACK_TRACING=1

# API Configuration
NEXT_PUBLIC_API_URL=http://localhost:4000
API_SECRET_KEY=your-secret-key

# Database
DATABASE_URL=postgresql://localhost:5432/mydb

# Feature Flags
NEXT_PUBLIC_ENABLE_FEATURE_X=true
```

**Load Order (Highest to Lowest Priority):**
1. `.env.local` (all environments, ignored by git)
2. `.env.development` or `.env.production` (environment-specific)
3. `.env` (all environments, checked into git)

**Public vs Private Variables:**
- Prefix with `NEXT_PUBLIC_` for browser access
- No prefix = server-side only
- Never expose secrets with `NEXT_PUBLIC_` prefix

## Framework-Specific Best Practices

### Turbopack Configuration (Next.js 13+)

**Enable Turbopack:**
```json
{
  "scripts": {
    "dev": "next dev --turbo"
  }
}
```

**Performance Tracing:**
```bash
# Enable tracing for debugging
NEXT_TURBOPACK_TRACING=1 npm run dev -- --turbo
```

**Benefits:**
- Up to 700x faster updates than Webpack
- Incremental compilation
- Better memory efficiency
- Faster cold starts

**Current Status (2024):**
- Stable for development use
- Most features supported
- Some plugins may not work yet
- Check compatibility: https://nextjs.org/docs/app/api-reference/next-config-js/turbo

### Hot Module Replacement (HMR)

**HMR for Server Components:**

Next.js caches server component renders. Clear cache on changes:

```javascript
// app/components/ServerComponent.js
export const dynamic = 'force-dynamic'; // Disable caching

export default function ServerComponent() {
  return <div>Content</div>;
}
```

**HMR for Client Components:**

```javascript
'use client';

export default function ClientComponent() {
  // HMR works automatically
  return <div>Content</div>;
}
```

**HMR Not Working? Check:**
1. File is in `app/` or `pages/` directory
2. No syntax errors in file
3. WebSocket connection established (check Network tab)
4. Not running through PM2 (breaks HMR)
5. Docker volume mounts correct

### Server Actions and API Routes

**Server Actions (App Router):**
```javascript
// app/actions.js
'use server';

export async function createUser(formData) {
  const name = formData.get('name');
  // Database operations
  return { success: true };
}
```

**API Routes (App Router):**
```javascript
// app/api/users/route.js
export async function GET(request) {
  return Response.json({ users: [] });
}

export async function POST(request) {
  const body = await request.json();
  return Response.json({ success: true });
}
```

**Development Server Auto-Reload:**
- Changes to API routes trigger automatic reload
- Changes to server actions trigger recompilation
- Client-side code uses HMR without full reload

### Memory Management

**Clear Build Cache:**
```bash
rm -rf .next
npm run dev
```

**Monitor Memory Usage:**
```bash
# Check Node.js process memory
ps aux | grep next

# Set max old space size
NODE_OPTIONS='--max-old-space-size=4096' npm run dev
```

**Optimize for Large Projects:**
```javascript
// next.config.js
module.exports = {
  experimental: {
    // Reduce memory usage
    optimizeCss: true,
    optimizePackageImports: ['lodash', 'react-icons']
  }
};
```

## Common Problems & Solutions

### Problem 1: Port Already in Use (EADDRINUSE)

**Symptoms:**
```
Error: listen EADDRINUSE: address already in use :::3000
```

**Root Cause:**
Another process is using port 3000 (previous Next.js instance, other server, or zombie process).

**Solution:**

**Option A: Find and Kill Process**
```bash
# macOS/Linux
lsof -ti:3000 | xargs kill -9

# Windows
netstat -ano | findstr :3000
taskkill /PID <PID> /F
```

**Option B: Use Different Port**
```bash
npm run dev -- -p 3001
```

**Option C: Graceful Cleanup Script**
```json
{
  "scripts": {
    "dev:clean": "kill-port 3000 && npm run dev",
    "predev": "kill-port 3000 || true"
  }
}
```

Install `kill-port`: `npm install -D kill-port`

### Problem 2: Changes Not Reflecting (HMR Broken)

**Symptoms:**
- Code changes don't appear in browser
- Need to manually refresh or restart server
- Console shows "WebSocket connection failed"

**Root Cause:**
Multiple possible causes: PM2 interference, Docker volume issues, WebSocket proxy problems, or caching.

**Solution:**

**Step 1: Verify Direct Dev Server**
```bash
# Stop PM2 if running
pm2 stop all

# Run dev server directly
npm run dev
```

**Step 2: Clear All Caches**
```bash
rm -rf .next
rm -rf node_modules/.cache
npm run dev
```

**Step 3: Check WebSocket Connection**

In browser console, verify:
```
[HMR] connected
```

If not connected, check next.config.js:
```javascript
module.exports = {
  // For proxy/reverse proxy setups
  assetPrefix: process.env.ASSET_PREFIX || '',

  // WebSocket configuration
  experimental: {
    webpackBuildWorker: true
  }
};
```

**Step 4: Docker Volume Configuration**

Exclude `.next` from volume mounts:
```yaml
volumes:
  - .:/app
  - /app/node_modules
  - /app/.next  # Don't sync build directory
```

**Step 5: WSL2 on Windows**

Enable polling for file watching:
```bash
# Set environment variable
CHOKIDAR_USEPOLLING=true npm run dev
```

### Problem 3: Slow Development Server Startup

**Symptoms:**
- Server takes 30+ seconds to start
- "Compiling..." messages take forever
- High CPU usage during startup

**Root Cause:**
Large dependency tree, unoptimized imports, or lack of Turbopack usage.

**Solution:**

**Step 1: Enable Turbopack**
```bash
npm run dev -- --turbo
```

**Step 2: Optimize Imports**

Bad:
```javascript
import { Button } from '@mui/material';
```

Good:
```javascript
import Button from '@mui/material/Button';
```

**Step 3: Configure Barrel File Optimization**
```javascript
// next.config.js
module.exports = {
  experimental: {
    optimizePackageImports: ['@mui/material', 'lodash', 'react-icons']
  }
};
```

**Step 4: Exclude Unnecessary Files**
```javascript
// next.config.js
module.exports = {
  pageExtensions: ['page.tsx', 'page.ts', 'page.jsx', 'page.js'],
  // This prevents Next.js from treating all files as routes
};
```

**Step 5: Increase Node Memory**
```json
{
  "scripts": {
    "dev": "NODE_OPTIONS='--max-old-space-size=4096' next dev --turbo"
  }
}
```

### Problem 4: PM2 Breaks Development Workflow

**Symptoms:**
- HMR stops working with PM2
- File changes not detected
- Need to restart PM2 after every change

**Root Cause:**
PM2 watch mode interferes with Next.js file watching, causing conflicts and breaking HMR.

**Solution:**

**Never use PM2 for Next.js development. Always use direct process.**

**Development (Correct):**
```bash
npm run dev
```

**Production (Correct):**
```bash
npm run build
pm2 start npm --name "nextjs" -- start
```

**Development with PM2 (Wrong - Don't Do This):**
```bash
# WRONG - Breaks HMR
pm2 start npm --name "nextjs-dev" --watch -- run dev
```

If you need process management in development:
- Use `nodemon` for auto-restart on crashes
- Use terminal multiplexers (`tmux`, `screen`)
- Use IDE run configurations
- NOT PM2

### Problem 5: Environment Variables Not Loading

**Symptoms:**
- `process.env.MY_VAR` is undefined
- Variables work in production but not development
- Public variables not accessible in browser

**Root Cause:**
Incorrect file naming, missing `NEXT_PUBLIC_` prefix, or variables added after server start.

**Solution:**

**Step 1: Correct File Naming**
```
.env.local          ← Use this for development
.env.development    ← Optional, environment-specific
.env                ← Shared defaults, committed to git
```

**Step 2: Restart Server**

Environment variables are loaded on server start:
```bash
# Restart required after .env changes
npm run dev
```

**Step 3: Public vs Private Variables**

Server-side only:
```bash
API_SECRET=secret123
```

Browser accessible:
```bash
NEXT_PUBLIC_API_URL=https://api.example.com
```

**Step 4: Runtime Access**
```javascript
// Server Component or API Route
const secret = process.env.API_SECRET;

// Client Component
const apiUrl = process.env.NEXT_PUBLIC_API_URL;
```

**Step 5: Validate Loading**
```javascript
// pages/api/debug.js
export default function handler(req, res) {
  res.json({
    nodeEnv: process.env.NODE_ENV,
    port: process.env.PORT,
    // Don't expose secrets in real debug endpoints
  });
}
```

## Anti-Patterns

### What NOT to Do

**1. Never Use PM2 for Development Server**
```bash
# WRONG - Breaks HMR and file watching
pm2 start npm --name "dev" --watch -- run dev
```

Why: PM2's watch mode conflicts with Next.js file watching, breaking HMR completely.

**2. Don't Ignore Build Artifacts in Docker**
```yaml
# WRONG - Causes build issues
volumes:
  - .:/app
```

Correct:
```yaml
volumes:
  - .:/app
  - /app/node_modules
  - /app/.next
```

**3. Don't Use Same Port for Multiple Services**
```bash
# WRONG - Causes port conflicts
PORT=3000 npm run dev  # Next.js
PORT=3000 python api.py  # API server
```

Use distinct ports: 3000 (Next.js), 4000 (API), 5432 (Database), etc.

**4. Don't Commit .env.local**
```
# WRONG in .gitignore
# .env.local  ← Should NOT be commented out
```

Correct:
```
# .gitignore
.env.local
.env*.local
```

**5. Don't Skip Production Build**
```bash
# WRONG for production
pm2 start npm --name "prod" -- run dev
```

Correct:
```bash
npm run build
pm2 start npm --name "prod" -- start
```

**6. Don't Use require() for Next.js Config**
```javascript
// WRONG - May cause issues
const withPlugins = require('next-compose-plugins');
```

Prefer ES modules (Next.js 13+):
```javascript
// next.config.mjs
export default {
  // config
};
```

**7. Don't Ignore Memory Limits**
```bash
# WRONG for large projects
npm run dev
```

Correct:
```bash
NODE_OPTIONS='--max-old-space-size=4096' npm run dev
```

## Quick Reference

### Commands

```bash
# Development
npm run dev                              # Start dev server
npm run dev -- -p 3001                   # Custom port
npm run dev -- --turbo                   # With Turbopack
NEXT_TURBOPACK_TRACING=1 npm run dev     # Debug Turbopack

# Production
npm run build                            # Create production build
npm start                                # Start production server
npm start -- -p 3001                     # Production on custom port

# Maintenance
rm -rf .next                             # Clear build cache
rm -rf node_modules/.cache               # Clear dependency cache
lsof -ti:3000 | xargs kill -9            # Kill process on port 3000

# PM2 (Production Only)
pm2 start npm --name "nextjs" -- start   # Start with PM2
pm2 restart nextjs                       # Restart
pm2 stop nextjs                          # Stop
pm2 logs nextjs                          # View logs
pm2 delete nextjs                        # Remove from PM2
```

### Configuration Templates

**Minimal next.config.js:**
```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  swcMinify: true,
};

module.exports = nextConfig;
```

**Development-Optimized next.config.js:**
```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  swcMinify: true,

  experimental: {
    optimizePackageImports: ['lodash', '@mui/material', 'react-icons'],
    webpackBuildWorker: true,
  },

  // For reverse proxy setups
  assetPrefix: process.env.ASSET_PREFIX || '',

  // Logging
  logging: {
    fetches: {
      fullUrl: true,
    },
  },
};

module.exports = nextConfig;
```

**Production PM2 Config:**
```javascript
module.exports = {
  apps: [{
    name: 'nextjs-prod',
    script: 'node_modules/next/dist/bin/next',
    args: 'start',
    instances: 'max',
    exec_mode: 'cluster',
    env: {
      NODE_ENV: 'production',
      PORT: 3000
    },
    max_memory_restart: '1G',
    autorestart: true,
    watch: false,
    error_file: './logs/err.log',
    out_file: './logs/out.log',
    log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
  }]
};
```

**Docker Compose (Full Stack):**
```yaml
version: '3.8'

services:
  nextjs:
    build: .
    ports:
      - "3000:3000"
    environment:
      - NODE_ENV=development
      - DATABASE_URL=postgresql://postgres:password@db:5432/mydb
    volumes:
      - .:/app
      - /app/node_modules
      - /app/.next
    depends_on:
      - db

  db:
    image: postgres:15-alpine
    environment:
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=mydb
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

## Related Skills

- **docker-containerization** - For containerized Next.js deployments
- **systematic-debugging** - For complex debugging scenarios
- **vite-local-dev** - Similar patterns for Vite-based React applications
- **express-local-dev** - For Next.js custom server implementations

---

**Next.js Version Compatibility:** This skill covers Next.js 13+ with App Router and Turbopack. For Pages Router or older versions, some patterns may differ. Always consult official Next.js documentation for version-specific features.

**Last Updated:** 2024 - Reflects stable Turbopack integration and current Next.js best practices.
