---
skill_id: express-local-dev
skill_version: 0.1.0
description: Running Express development servers with auto-reload tools like Nodemon, managing production deployments with PM2 clustering, and implementing graceful shutdown patterns.
updated_at: 2025-10-30T17:00:00Z
tags: [express, nodejs, development, server, backend]
---

# Express Local Development Server

## Overview

Express is a minimal and flexible Node.js web application framework providing a robust set of features for web and mobile applications. This skill covers running Express development servers with auto-reload tools like Nodemon, managing production deployments with PM2 clustering, and implementing graceful shutdown patterns.

## When to Use This Skill

- Setting up Express development environment with auto-reload
- Configuring Nodemon for optimal development workflow
- Troubleshooting file watching and reload issues
- Managing Express production deployment with PM2
- Implementing graceful shutdown handlers
- Configuring zero-downtime reloads
- Coordinating multiple Express instances
- Understanding Nodemon vs PM2 trade-offs

## Quick Start

### Development Server

**Basic Express Server:**
```javascript
// server.js
const express = require('express');
const app = express();
const PORT = process.env.PORT || 3000;

app.get('/', (req, res) => {
  res.json({ message: 'Hello World' });
});

const server = app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});

// Graceful shutdown
process.on('SIGTERM', () => {
  console.log('SIGTERM received, closing server...');
  server.close(() => {
    console.log('Server closed');
    process.exit(0);
  });
});
```

**With Nodemon:**
```bash
# Install nodemon
npm install -D nodemon

# Run with nodemon
npx nodemon server.js

# Or add to package.json
npm run dev
```

**With TypeScript:**
```bash
# Install dependencies
npm install -D typescript @types/express @types/node ts-node nodemon

# Run with nodemon + ts-node
npx nodemon --exec ts-node src/server.ts
```

### With PM2 (Production)

**Basic PM2 Start:**
```bash
# Start Express with PM2
pm2 start server.js --name "express-app"

# With environment variables
pm2 start server.js --name "express-app" --env production

# Cluster mode (multiple instances)
pm2 start server.js -i max
```

**Watch Mode (Use Carefully):**
```bash
# PM2 with watch (development only, not recommended)
pm2 start server.js --watch --ignore-watch="node_modules"
```

### With Docker

**Development Dockerfile:**
```dockerfile
FROM node:18-alpine

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

EXPOSE 3000

CMD ["npm", "run", "dev"]
```

**Production Dockerfile:**
```dockerfile
FROM node:18-alpine

WORKDIR /app

COPY package*.json ./
RUN npm ci --only=production

COPY . .

EXPOSE 3000

CMD ["node", "server.js"]
```

**Docker Compose:**
```yaml
version: '3.8'

services:
  express:
    build: .
    ports:
      - "3000:3000"
    volumes:
      - .:/app
      - /app/node_modules
    environment:
      - NODE_ENV=development
      - PORT=3000
    command: npm run dev

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
```

## Configuration Patterns

### Nodemon Configuration

**nodemon.json:**
```json
{
  "watch": ["src", "config"],
  "ext": "js,json,ts",
  "ignore": ["src/**/*.test.js", "node_modules"],
  "exec": "node server.js",
  "env": {
    "NODE_ENV": "development"
  },
  "delay": 1000,
  "verbose": true,
  "restartable": "rs"
}
```

**Package.json Scripts:**
```json
{
  "scripts": {
    "dev": "nodemon server.js",
    "dev:debug": "nodemon --inspect server.js",
    "dev:ts": "nodemon --exec ts-node src/server.ts",
    "start": "node server.js",
    "start:prod": "NODE_ENV=production node server.js"
  },
  "devDependencies": {
    "nodemon": "^3.0.1"
  }
}
```

**Advanced Nodemon Configuration:**
```json
{
  "watch": ["src"],
  "ext": "js,json,graphql",
  "ignore": [
    "src/**/*.test.js",
    "src/**/*.spec.js",
    "node_modules/**/*",
    "dist/**/*"
  ],
  "exec": "node --trace-warnings server.js",
  "env": {
    "NODE_ENV": "development",
    "DEBUG": "express:*"
  },
  "events": {
    "restart": "echo 'App restarted due to file change'"
  },
  "delay": 2000,
  "signal": "SIGTERM",
  "verbose": false
}
```

### PM2 Clustering for Production

**Ecosystem Configuration:**
```javascript
// ecosystem.config.js
module.exports = {
  apps: [{
    name: 'express-app',
    script: './server.js',
    instances: 'max', // Use all CPU cores
    exec_mode: 'cluster',

    // Environment variables
    env: {
      NODE_ENV: 'development',
      PORT: 3000
    },
    env_production: {
      NODE_ENV: 'production',
      PORT: 8080
    },

    // Restart policies
    autorestart: true,
    max_restarts: 10,
    min_uptime: '10s',
    max_memory_restart: '500M',

    // Watch mode (development only, use nodemon instead)
    watch: false,

    // Logging
    error_file: './logs/pm2-error.log',
    out_file: './logs/pm2-out.log',
    log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
    merge_logs: true,

    // Graceful shutdown
    kill_timeout: 5000,
    wait_ready: true,
    listen_timeout: 10000,
  }]
};
```

**Start PM2 Cluster:**
```bash
# Start cluster with config
pm2 start ecosystem.config.js --env production

# Monitor cluster
pm2 monit

# View cluster status
pm2 list

# Reload without downtime
pm2 reload express-app
```

**Manual Clustering Configuration:**
```bash
# Start with 4 instances
pm2 start server.js -i 4

# Use all CPU cores
pm2 start server.js -i max

# Scale up/down
pm2 scale express-app 8
pm2 scale express-app +2
```

### Nodemon vs PM2 Comparison

**Nodemon (Development Recommended):**

Pros:
- Designed for development
- Fast restarts on file changes
- Simple configuration
- Better developer experience
- Automatic detection of file changes
- No cluster complexity in dev

Cons:
- Single instance only
- Not for production
- No advanced process management

**Use Nodemon when:**
- Developing locally
- Need fast feedback on changes
- Testing and debugging
- Single developer workflow

**PM2 (Production Recommended):**

Pros:
- Multi-instance clustering
- Zero-downtime reload
- Process monitoring
- Automatic restarts
- Log management
- Load balancing
- Production-grade features

Cons:
- Watch mode can be unreliable
- More complex configuration
- Slower restarts than Nodemon
- Overkill for development

**Use PM2 when:**
- Production deployment
- Need multiple instances
- Zero-downtime requirements
- System-level process management
- Advanced monitoring needed

**Recommendation:**
- Development: Use Nodemon
- Production: Use PM2 (no watch mode)

### Graceful Shutdown Implementation

**Basic Graceful Shutdown:**
```javascript
const express = require('express');
const app = express();
const PORT = process.env.PORT || 3000;

app.get('/', (req, res) => {
  res.json({ status: 'ok' });
});

const server = app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});

// Graceful shutdown handler
function gracefulShutdown(signal) {
  console.log(`${signal} received, starting graceful shutdown`);

  server.close(() => {
    console.log('HTTP server closed');

    // Close database connections
    // db.close();

    // Close other resources
    // redis.quit();

    console.log('All connections closed, exiting');
    process.exit(0);
  });

  // Force exit after timeout
  setTimeout(() => {
    console.error('Forcing shutdown after timeout');
    process.exit(1);
  }, 10000);
}

// Listen for termination signals
process.on('SIGTERM', () => gracefulShutdown('SIGTERM'));
process.on('SIGINT', () => gracefulShutdown('SIGINT'));
```

**Advanced Graceful Shutdown with Cleanup:**
```javascript
const express = require('express');
const mongoose = require('mongoose');
const redis = require('redis');

const app = express();
const PORT = process.env.PORT || 3000;

// Setup
const redisClient = redis.createClient();
mongoose.connect(process.env.MONGODB_URI);

let isShuttingDown = false;

// Health check endpoint
app.get('/health', (req, res) => {
  if (isShuttingDown) {
    res.status(503).json({ status: 'shutting down' });
  } else {
    res.json({ status: 'ok' });
  }
});

const server = app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);

  // Signal to PM2 that app is ready
  if (process.send) {
    process.send('ready');
  }
});

// Graceful shutdown
async function gracefulShutdown(signal) {
  if (isShuttingDown) return;

  console.log(`${signal} received, starting graceful shutdown`);
  isShuttingDown = true;

  // Stop accepting new connections
  server.close(async () => {
    console.log('HTTP server closed');

    try {
      // Close database connections
      await mongoose.connection.close();
      console.log('MongoDB connection closed');

      // Close Redis connection
      await redisClient.quit();
      console.log('Redis connection closed');

      console.log('Graceful shutdown completed');
      process.exit(0);
    } catch (error) {
      console.error('Error during shutdown:', error);
      process.exit(1);
    }
  });

  // Force exit after 30 seconds
  setTimeout(() => {
    console.error('Forcing shutdown after timeout');
    process.exit(1);
  }, 30000);
}

process.on('SIGTERM', () => gracefulShutdown('SIGTERM'));
process.on('SIGINT', () => gracefulShutdown('SIGINT'));

// Handle uncaught errors
process.on('uncaughtException', (error) => {
  console.error('Uncaught exception:', error);
  gracefulShutdown('uncaughtException');
});

process.on('unhandledRejection', (reason, promise) => {
  console.error('Unhandled rejection at:', promise, 'reason:', reason);
  gracefulShutdown('unhandledRejection');
});
```

**PM2 Integration:**
```javascript
// Send ready signal to PM2
server.listen(PORT, () => {
  console.log(`Server listening on port ${PORT}`);

  if (process.send) {
    process.send('ready');
  }
});

// Handle PM2 shutdown message
process.on('message', (msg) => {
  if (msg === 'shutdown') {
    gracefulShutdown('PM2 shutdown message');
  }
});
```

### Zero-Downtime Reload

**PM2 Reload (Graceful):**
```bash
# Reload all instances gracefully
pm2 reload express-app

# Reload with delay between instances
pm2 reload express-app --update-env

# Force restart (not graceful)
pm2 restart express-app
```

**Ecosystem Config for Zero-Downtime:**
```javascript
module.exports = {
  apps: [{
    name: 'express-app',
    script: './server.js',
    instances: 4,
    exec_mode: 'cluster',

    // Zero-downtime reload settings
    wait_ready: true,        // Wait for ready signal
    listen_timeout: 10000,   // Timeout for ready signal
    kill_timeout: 5000,      // Time to wait for graceful shutdown

    // Restart behavior
    autorestart: true,
    max_restarts: 10,
    min_uptime: '10s',
  }]
};
```

**Application Code for Zero-Downtime:**
```javascript
const express = require('express');
const app = express();
const PORT = process.env.PORT || 3000;

const server = app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);

  // Signal PM2 that app is ready
  if (process.send) {
    process.send('ready');
  }
});

// Graceful shutdown for PM2 reload
process.on('SIGINT', () => {
  console.log('SIGINT received, closing server');

  server.close(() => {
    console.log('Server closed');
    process.exit(0);
  });

  // Timeout fallback
  setTimeout(() => process.exit(1), 10000);
});
```

**Deployment Process:**
```bash
# Deploy new code
git pull origin main
npm install --production

# Reload without downtime
pm2 reload ecosystem.config.js --env production

# Verify instances
pm2 list
pm2 logs express-app --lines 50
```

### Multiple Instance Coordination

**Shared State with Redis:**
```javascript
const express = require('express');
const redis = require('redis');
const session = require('express-session');
const RedisStore = require('connect-redis').default;

const app = express();

// Redis client
const redisClient = redis.createClient({
  host: process.env.REDIS_HOST || 'localhost',
  port: process.env.REDIS_PORT || 6379,
});

redisClient.on('error', (err) => console.error('Redis error:', err));

// Session store with Redis
app.use(session({
  store: new RedisStore({ client: redisClient }),
  secret: process.env.SESSION_SECRET,
  resave: false,
  saveUninitialized: false,
  cookie: {
    secure: process.env.NODE_ENV === 'production',
    maxAge: 1000 * 60 * 60 * 24, // 24 hours
  },
}));
```

**Cluster-Safe In-Memory Caching:**
```javascript
// DON'T: In-memory cache (not shared across instances)
const cache = {};

app.get('/data/:id', (req, res) => {
  const cached = cache[req.params.id]; // Different per instance!
  if (cached) return res.json(cached);

  // Fetch and cache
  const data = fetchData(req.params.id);
  cache[req.params.id] = data;
  res.json(data);
});

// DO: Redis cache (shared across instances)
app.get('/data/:id', async (req, res) => {
  const cached = await redisClient.get(`data:${req.params.id}`);
  if (cached) return res.json(JSON.parse(cached));

  // Fetch and cache in Redis
  const data = await fetchData(req.params.id);
  await redisClient.setEx(`data:${req.params.id}`, 3600, JSON.stringify(data));
  res.json(data);
});
```

**Worker Coordination:**
```javascript
// Use Redis for distributed locks
const Redlock = require('redlock');

const redlock = new Redlock([redisClient], {
  retryCount: 10,
  retryDelay: 200,
});

app.post('/process-job', async (req, res) => {
  const lock = await redlock.acquire(['locks:process-job'], 5000);

  try {
    // Only one instance processes this at a time
    await processJob(req.body);
    res.json({ success: true });
  } finally {
    await lock.release();
  }
});
```

**Socket.IO with PM2 Cluster:**
```javascript
const express = require('express');
const http = require('http');
const socketIO = require('socket.io');
const redis = require('redis');
const { createAdapter } = require('@socket.io/redis-adapter');

const app = express();
const server = http.createServer(app);
const io = socketIO(server);

// Redis adapter for Socket.IO clustering
const pubClient = redis.createClient();
const subClient = pubClient.duplicate();

io.adapter(createAdapter(pubClient, subClient));

io.on('connection', (socket) => {
  console.log('Client connected');

  socket.on('message', (data) => {
    // Broadcast across all instances
    io.emit('message', data);
  });
});

server.listen(3000);
```

## Framework-Specific Best Practices

### Middleware Organization

**Proper Middleware Order:**
```javascript
const express = require('express');
const helmet = require('helmet');
const cors = require('cors');
const compression = require('compression');
const morgan = require('morgan');

const app = express();

// Security middleware (first)
app.use(helmet());
app.use(cors({
  origin: process.env.ALLOWED_ORIGINS?.split(',') || '*',
  credentials: true,
}));

// Request parsing
app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true }));

// Compression
app.use(compression());

// Logging
if (process.env.NODE_ENV !== 'production') {
  app.use(morgan('dev'));
} else {
  app.use(morgan('combined'));
}

// Routes
app.use('/api/users', require('./routes/users'));
app.use('/api/posts', require('./routes/posts'));

// Error handling (last)
app.use((err, req, res, next) => {
  console.error(err.stack);
  res.status(500).json({ error: 'Internal server error' });
});
```

### Error Handling Patterns

**Centralized Error Handler:**
```javascript
// errors/AppError.js
class AppError extends Error {
  constructor(message, statusCode) {
    super(message);
    this.statusCode = statusCode;
    this.isOperational = true;
    Error.captureStackTrace(this, this.constructor);
  }
}

// middleware/errorHandler.js
function errorHandler(err, req, res, next) {
  err.statusCode = err.statusCode || 500;
  err.status = err.status || 'error';

  if (process.env.NODE_ENV === 'development') {
    res.status(err.statusCode).json({
      status: err.status,
      error: err,
      message: err.message,
      stack: err.stack,
    });
  } else {
    // Production: don't leak error details
    if (err.isOperational) {
      res.status(err.statusCode).json({
        status: err.status,
        message: err.message,
      });
    } else {
      console.error('ERROR:', err);
      res.status(500).json({
        status: 'error',
        message: 'Something went wrong',
      });
    }
  }
}

// server.js
app.use(errorHandler);
```

**Async Error Wrapper:**
```javascript
// utils/catchAsync.js
const catchAsync = (fn) => {
  return (req, res, next) => {
    fn(req, res, next).catch(next);
  };
};

// Usage
const getUser = catchAsync(async (req, res) => {
  const user = await User.findById(req.params.id);
  if (!user) throw new AppError('User not found', 404);
  res.json({ user });
});

app.get('/users/:id', getUser);
```

### Environment Configuration

**Configuration Management:**
```javascript
// config/index.js
require('dotenv').config();

module.exports = {
  env: process.env.NODE_ENV || 'development',
  port: parseInt(process.env.PORT, 10) || 3000,
  database: {
    uri: process.env.DATABASE_URL,
    options: {
      useNewUrlParser: true,
      useUnifiedTopology: true,
    },
  },
  redis: {
    host: process.env.REDIS_HOST || 'localhost',
    port: parseInt(process.env.REDIS_PORT, 10) || 6379,
  },
  jwt: {
    secret: process.env.JWT_SECRET,
    expiresIn: process.env.JWT_EXPIRES_IN || '7d',
  },
  cors: {
    origin: process.env.ALLOWED_ORIGINS?.split(',') || '*',
  },
};
```

### Logging Best Practices

**Structured Logging:**
```javascript
const winston = require('winston');

const logger = winston.createLogger({
  level: process.env.LOG_LEVEL || 'info',
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.errors({ stack: true }),
    winston.format.json()
  ),
  transports: [
    new winston.transports.File({ filename: 'logs/error.log', level: 'error' }),
    new winston.transports.File({ filename: 'logs/combined.log' }),
  ],
});

if (process.env.NODE_ENV !== 'production') {
  logger.add(new winston.transports.Console({
    format: winston.format.simple(),
  }));
}

// Usage
logger.info('Server started', { port: 3000 });
logger.error('Database error', { error: err.message });
```

## Common Problems & Solutions

### Problem 1: Port Already in Use

**Symptoms:**
```
Error: listen EADDRINUSE: address already in use :::3000
```

**Root Cause:**
Another process (previous Express instance, other server, or zombie process) is using port 3000.

**Solution:**

**Option A: Kill Process**
```bash
# macOS/Linux
lsof -ti:3000 | xargs kill -9

# Alternative
fuser -k 3000/tcp

# Windows
netstat -ano | findstr :3000
taskkill /PID <PID> /F
```

**Option B: Use Different Port**
```bash
PORT=3001 npm run dev
```

**Option C: Dynamic Port Assignment**
```javascript
const express = require('express');
const app = express();

const PORT = process.env.PORT || 3000;

const server = app.listen(PORT, () => {
  console.log(`Server running on port ${server.address().port}`);
});

// Or find available port
const portfinder = require('portfinder');

portfinder.getPort((err, port) => {
  if (err) throw err;
  app.listen(port, () => {
    console.log(`Server running on port ${port}`);
  });
});
```

**Option D: Cleanup Script**
```json
{
  "scripts": {
    "predev": "kill-port 3000 || true",
    "dev": "nodemon server.js"
  }
}
```

### Problem 2: Nodemon Not Restarting on Changes

**Symptoms:**
- File changes don't trigger restart
- Need to manually stop and start server
- Nodemon seems to be running but not watching

**Root Cause:**
Incorrect watch configuration, file permission issues, or unsupported file system (WSL, network drives).

**Solution:**

**Step 1: Verify Nodemon is Watching**
```bash
# Run with verbose output
npx nodemon --verbose server.js
```

**Step 2: Configure Watch Directories**
```json
{
  "watch": ["src", "config"],
  "ext": "js,json",
  "ignore": ["node_modules/**/*", "test/**/*"]
}
```

**Step 3: Force Polling (WSL/Network Drives)**
```json
{
  "watch": ["src"],
  "legacyWatch": true,
  "pollingInterval": 1000
}
```

**Step 4: Check File Permissions**
```bash
# Ensure files are readable
chmod -R 644 src/**/*.js
```

**Step 5: Increase Delay**
```json
{
  "delay": 2000,
  "debounce": 1000
}
```

**Step 6: Manual Restart**
```bash
# Type 'rs' and Enter to manually restart
npx nodemon server.js
rs
```

### Problem 3: PM2 Cluster Instances Crashing

**Symptoms:**
```
[PM2][ERROR] App crashed
PM2 | App [express-app:0] exited with code [1]
```

**Root Cause:**
Unhandled errors, memory leaks, or improper graceful shutdown in cluster mode.

**Solution:**

**Step 1: Check Logs**
```bash
pm2 logs express-app --lines 100
pm2 logs express-app --err
```

**Step 2: Implement Error Handlers**
```javascript
// Catch unhandled errors
process.on('uncaughtException', (error) => {
  console.error('Uncaught exception:', error);
  gracefulShutdown('uncaughtException');
});

process.on('unhandledRejection', (reason, promise) => {
  console.error('Unhandled rejection:', reason);
  gracefulShutdown('unhandledRejection');
});
```

**Step 3: Add Memory Monitoring**
```javascript
// ecosystem.config.js
module.exports = {
  apps: [{
    name: 'express-app',
    script: './server.js',
    max_memory_restart: '500M', // Restart on high memory
    instances: 4,
    exec_mode: 'cluster',
  }]
};
```

**Step 4: Check Minimum Uptime**
```javascript
// ecosystem.config.js
module.exports = {
  apps: [{
    min_uptime: '10s', // App must run 10s to be considered healthy
    max_restarts: 10,  // Max restarts within min_uptime period
  }]
};
```

**Step 5: Test Instance Stability**
```bash
# Start single instance first
pm2 start server.js --name "test" -i 1

# If stable, scale up
pm2 scale test 4
```

### Problem 4: Sessions Not Shared Across Instances

**Symptoms:**
- User logged in but subsequent requests show logged out
- Session data inconsistent between requests
- Works fine with single instance, breaks with cluster

**Root Cause:**
In-memory session store is not shared across PM2 cluster instances.

**Solution:**

**Use Redis for Session Storage:**
```javascript
const express = require('express');
const session = require('express-session');
const RedisStore = require('connect-redis').default;
const redis = require('redis');

const app = express();

// Redis client
const redisClient = redis.createClient({
  host: process.env.REDIS_HOST || 'localhost',
  port: process.env.REDIS_PORT || 6379,
});

redisClient.on('error', (err) => console.error('Redis error:', err));

// Session configuration with Redis store
app.use(session({
  store: new RedisStore({ client: redisClient }),
  secret: process.env.SESSION_SECRET || 'your-secret-key',
  resave: false,
  saveUninitialized: false,
  cookie: {
    secure: process.env.NODE_ENV === 'production', // HTTPS only in prod
    httpOnly: true,
    maxAge: 1000 * 60 * 60 * 24, // 24 hours
  },
}));
```

**Alternative: Use JWT (Stateless):**
```javascript
const jwt = require('jsonwebtoken');

// Generate token on login
app.post('/login', (req, res) => {
  // Verify credentials
  const token = jwt.sign(
    { userId: user.id },
    process.env.JWT_SECRET,
    { expiresIn: '7d' }
  );

  res.json({ token });
});

// Verify token on protected routes
function authMiddleware(req, res, next) {
  const token = req.headers.authorization?.split(' ')[1];

  if (!token) {
    return res.status(401).json({ error: 'No token provided' });
  }

  try {
    const decoded = jwt.verify(token, process.env.JWT_SECRET);
    req.user = decoded;
    next();
  } catch (error) {
    res.status(401).json({ error: 'Invalid token' });
  }
}

app.get('/protected', authMiddleware, (req, res) => {
  res.json({ data: 'secret data', user: req.user });
});
```

### Problem 5: Nodemon vs PM2 Watch Confusion

**Symptoms:**
- Using PM2 watch mode for development
- Slow restarts or unexpected behavior
- File changes trigger multiple restarts

**Root Cause:**
PM2 watch mode is not designed for active development and has limitations compared to Nodemon.

**Solution:**

**Use Nodemon for Development:**
```json
{
  "scripts": {
    "dev": "nodemon server.js",
    "start": "node server.js",
    "prod": "pm2 start ecosystem.config.js --env production"
  }
}
```

**Configure Nodemon Properly:**
```json
{
  "watch": ["src"],
  "ext": "js,json",
  "ignore": ["src/**/*.test.js"],
  "exec": "node server.js",
  "delay": 1000
}
```

**Use PM2 for Production (No Watch):**
```javascript
// ecosystem.config.js
module.exports = {
  apps: [{
    name: 'express-app',
    script: './server.js',
    instances: 'max',
    exec_mode: 'cluster',
    watch: false, // NEVER true in production
    autorestart: true,
    env_production: {
      NODE_ENV: 'production'
    }
  }]
};
```

**Development Workflow:**
```bash
# Development: Nodemon
npm run dev

# Production: PM2
pm2 start ecosystem.config.js --env production
```

## Anti-Patterns

### What NOT to Do

**1. Don't Use PM2 Watch for Development**
```javascript
// WRONG
module.exports = {
  apps: [{
    name: 'express-dev',
    script: './server.js',
    watch: true, // Use nodemon instead
  }]
};
```

Use Nodemon for development, PM2 for production.

**2. Don't Store Sessions In-Memory with Clustering**
```javascript
// WRONG with PM2 cluster mode
const session = require('express-session');
app.use(session({
  secret: 'secret',
  resave: false,
  saveUninitialized: false,
  // No store specified = in-memory (breaks clustering)
}));
```

Use Redis or other shared store for sessions.

**3. Don't Forget Graceful Shutdown**
```javascript
// WRONG - abrupt termination
app.listen(3000);
// No shutdown handlers

// CORRECT
const server = app.listen(3000);
process.on('SIGTERM', () => {
  server.close(() => process.exit(0));
});
```

**4. Don't Block the Event Loop**
```javascript
// WRONG - blocks event loop
app.get('/compute', (req, res) => {
  const result = heavyComputation(); // Synchronous!
  res.json({ result });
});

// CORRECT - offload to worker
const { Worker } = require('worker_threads');
app.get('/compute', (req, res) => {
  const worker = new Worker('./worker.js');
  worker.on('message', (result) => {
    res.json({ result });
  });
});
```

**5. Don't Expose Detailed Errors in Production**
```javascript
// WRONG
app.use((err, req, res, next) => {
  res.status(500).json({ error: err.stack }); // Leaks info
});

// CORRECT
app.use((err, req, res, next) => {
  if (process.env.NODE_ENV === 'production') {
    res.status(500).json({ error: 'Internal server error' });
  } else {
    res.status(500).json({ error: err.message, stack: err.stack });
  }
});
```

**6. Don't Use Synchronous File Operations**
```javascript
// WRONG
const data = fs.readFileSync('./data.json'); // Blocks!

// CORRECT
const data = await fs.promises.readFile('./data.json');
```

**7. Don't Trust User Input**
```javascript
// WRONG - no validation
app.post('/users', (req, res) => {
  const user = new User(req.body); // Dangerous!
  user.save();
});

// CORRECT
const { body, validationResult } = require('express-validator');

app.post('/users',
  body('email').isEmail(),
  body('name').trim().notEmpty(),
  (req, res) => {
    const errors = validationResult(req);
    if (!errors.isEmpty()) {
      return res.status(400).json({ errors: errors.array() });
    }
    // Process validated input
  }
);
```

## Quick Reference

### Commands

```bash
# Development with Nodemon
npm run dev                              # Start with nodemon
npx nodemon server.js                    # Direct nodemon
npx nodemon --verbose server.js          # Verbose output
npx nodemon --inspect server.js          # Debug mode

# Production with PM2
pm2 start server.js                      # Start app
pm2 start ecosystem.config.js            # Start with config
pm2 start server.js -i max               # Cluster mode (all CPUs)
pm2 reload express-app                   # Zero-downtime reload
pm2 restart express-app                  # Restart
pm2 stop express-app                     # Stop
pm2 delete express-app                   # Remove from PM2
pm2 logs express-app                     # View logs
pm2 monit                                # Monitor dashboard
pm2 list                                 # List processes
pm2 save                                 # Save process list
pm2 startup                              # Enable auto-start

# Process Management
lsof -ti:3000 | xargs kill -9            # Kill process on port
ps aux | grep node                       # Find Node processes
kill -9 <PID>                            # Kill specific process

# Scaling
pm2 scale express-app 4                  # Set to 4 instances
pm2 scale express-app +2                 # Add 2 instances
```

### Configuration Templates

**package.json:**
```json
{
  "scripts": {
    "dev": "nodemon server.js",
    "dev:debug": "nodemon --inspect server.js",
    "start": "node server.js",
    "prod": "pm2 start ecosystem.config.js --env production",
    "reload": "pm2 reload ecosystem.config.js",
    "stop": "pm2 stop ecosystem.config.js"
  },
  "dependencies": {
    "express": "^4.18.2",
    "dotenv": "^16.0.3"
  },
  "devDependencies": {
    "nodemon": "^3.0.1"
  }
}
```

**nodemon.json:**
```json
{
  "watch": ["src"],
  "ext": "js,json",
  "ignore": ["src/**/*.test.js"],
  "exec": "node server.js",
  "env": {
    "NODE_ENV": "development"
  },
  "delay": 1000
}
```

**ecosystem.config.js (Production):**
```javascript
module.exports = {
  apps: [{
    name: 'express-app',
    script: './server.js',
    instances: 'max',
    exec_mode: 'cluster',
    autorestart: true,
    watch: false,
    max_memory_restart: '500M',
    env_production: {
      NODE_ENV: 'production',
      PORT: 8080
    },
    error_file: './logs/pm2-error.log',
    out_file: './logs/pm2-out.log',
    log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
    merge_logs: true,
    kill_timeout: 5000,
    wait_ready: true,
    listen_timeout: 10000,
  }]
};
```

**server.js with Graceful Shutdown:**
```javascript
const express = require('express');
const app = express();
const PORT = process.env.PORT || 3000;

app.get('/health', (req, res) => {
  res.json({ status: 'ok' });
});

const server = app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
  if (process.send) process.send('ready');
});

function gracefulShutdown(signal) {
  console.log(`${signal} received`);
  server.close(() => {
    console.log('Server closed');
    process.exit(0);
  });
  setTimeout(() => process.exit(1), 10000);
}

process.on('SIGTERM', () => gracefulShutdown('SIGTERM'));
process.on('SIGINT', () => gracefulShutdown('SIGINT'));
```

## Related Skills

- **fastapi-local-dev** - Similar patterns for Python/FastAPI applications
- **nextjs-local-dev** - For Next.js with custom Express server
- **docker-containerization** - For containerized Express deployments
- **systematic-debugging** - For complex debugging scenarios

---

**Express Version Compatibility:** This skill covers Express 4.x and PM2 5.x. Most patterns are stable across versions.

**Last Updated:** 2024 - Reflects current Express and PM2 best practices for development and production deployment.
