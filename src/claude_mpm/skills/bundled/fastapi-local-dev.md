---
skill_id: fastapi-local-dev
skill_version: 0.1.0
description: Running FastAPI development servers effectively using Uvicorn, managing production deployments with Gunicorn, and avoiding common pitfalls.
updated_at: 2025-10-30T17:00:00Z
tags: [fastapi, python, development, server, api]
---

# FastAPI Local Development Server

## Overview

FastAPI is a modern, high-performance Python web framework for building APIs with automatic OpenAPI documentation, type hints, and async support. This skill covers running FastAPI development servers effectively using Uvicorn, managing production deployments with Gunicorn, and avoiding common pitfalls with process managers like PM2.

## When to Use This Skill

- Setting up FastAPI development environment with auto-reload
- Configuring Uvicorn for development and production
- Troubleshooting file watching and auto-reload issues
- Managing FastAPI with systemd vs PM2
- Resolving virtual environment and dependency issues
- Optimizing worker processes for production
- Debugging reload failures and import errors

## Quick Start

### Development Server

**Basic Uvicorn Development:**
```bash
# Direct uvicorn
uvicorn main:app --reload

# With custom host and port
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# With log level
uvicorn main:app --reload --log-level debug
```

**Using Python Module:**
```bash
# From project root
python -m uvicorn app.main:app --reload

# With path specification
PYTHONPATH=. uvicorn app.main:app --reload
```

**In Python Code:**
```python
# main.py
import uvicorn
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Hello World"}

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=["./app"]
    )
```

### With Gunicorn (Production)

**Gunicorn + Uvicorn Workers:**
```bash
# Production server with 4 workers
gunicorn app.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --timeout 120 \
  --graceful-timeout 30
```

**Gunicorn Configuration File:**
```python
# gunicorn_conf.py
import multiprocessing

# Server socket
bind = "0.0.0.0:8000"
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
timeout = 120
keepalive = 5
graceful_timeout = 30

# Logging
accesslog = "./logs/access.log"
errorlog = "./logs/error.log"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = "fastapi-app"

# Server mechanics
daemon = False
pidfile = "./gunicorn.pid"
preload_app = True

# Worker lifecycle
max_requests = 1000
max_requests_jitter = 50
```

Run with config:
```bash
gunicorn -c gunicorn_conf.py app.main:app
```

### With Docker

**Development Dockerfile:**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Development: auto-reload enabled
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

**Production Dockerfile:**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Production: Gunicorn with Uvicorn workers
CMD ["gunicorn", "app.main:app", \
     "--workers", "4", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--bind", "0.0.0.0:8000"]
```

**Docker Compose:**
```yaml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - .:/app
    environment:
      - PYTHONUNBUFFERED=1
      - DATABASE_URL=postgresql://user:pass@db:5432/dbname
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    depends_on:
      - db

  db:
    image: postgres:15-alpine
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
      - POSTGRES_DB=dbname
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

## Configuration Patterns

### Uvicorn Auto-Reload Configuration

**Command Line Options:**
```bash
uvicorn main:app \
  --reload \                          # Enable auto-reload
  --reload-dir ./app \                # Watch specific directory
  --reload-exclude ./tests \          # Exclude directory
  --reload-include '*.py' \           # Watch specific patterns
  --host 0.0.0.0 \                    # Listen on all interfaces
  --port 8000 \                       # Port
  --log-level info \                  # Logging level
  --access-log \                      # Enable access logs
  --use-colors                        # Colored output
```

**Programmatic Configuration:**
```python
# main.py
import uvicorn
from fastapi import FastAPI

app = FastAPI()

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=["./app", "./config"],
        reload_excludes=["./tests", "./docs"],
        reload_includes=["*.py", "*.yaml"],
        log_level="info",
        access_log=True,
        workers=1  # Must be 1 for reload mode
    )
```

### systemd vs PM2 Comparison

**systemd (Recommended for Linux Production):**

Advantages:
- Native OS-level process management
- Automatic restart on failure
- System resource limits (CPU, memory)
- Integrated logging with journald
- No additional dependencies
- Better security controls

Example systemd service:
```ini
# /etc/systemd/system/fastapi.service
[Unit]
Description=FastAPI Application
After=network.target

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=/opt/fastapi-app
Environment="PATH=/opt/fastapi-app/venv/bin"
ExecStart=/opt/fastapi-app/venv/bin/gunicorn \
  -c /opt/fastapi-app/gunicorn_conf.py \
  app.main:app

Restart=always
RestartSec=10

# Security
NoNewPrivileges=true
PrivateTmp=true

# Resource limits
LimitNOFILE=65536
MemoryLimit=2G

[Install]
WantedBy=multi-user.target
```

Commands:
```bash
sudo systemctl start fastapi
sudo systemctl enable fastapi
sudo systemctl status fastapi
sudo journalctl -u fastapi -f
```

**PM2 (Cross-Platform Alternative):**

Advantages:
- Works on Windows, macOS, Linux
- Built-in load balancer
- Easy monitoring dashboard
- Simple deployment workflow

Disadvantages for Python:
- Watch mode can break Python imports
- Less efficient than systemd on Linux
- Additional Node.js dependency
- More complex setup for Python

**Critical Warning: Never use PM2 watch mode with Python FastAPI applications.**

### PM2 Configuration (Without Watch Mode)

```javascript
// ecosystem.config.js
module.exports = {
  apps: [{
    name: 'fastapi-app',
    script: '/opt/fastapi-app/venv/bin/gunicorn',
    args: '-c gunicorn_conf.py app.main:app',
    cwd: '/opt/fastapi-app',
    instances: 1,
    exec_mode: 'fork',  // NOT cluster for Python
    autorestart: true,
    max_memory_restart: '1G',

    // CRITICAL: No watch mode for Python
    watch: false,

    env: {
      NODE_ENV: 'production',
      PYTHONUNBUFFERED: '1'
    },

    error_file: './logs/pm2-error.log',
    out_file: './logs/pm2-out.log',
    log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
    merge_logs: true,

    // Graceful shutdown
    kill_timeout: 5000,
    wait_ready: true,
    listen_timeout: 10000
  }]
};
```

**Start with PM2:**
```bash
pm2 start ecosystem.config.js
pm2 save
pm2 startup  # Enable auto-start on boot
```

### Virtual Environment Handling

**Activate Virtual Environment:**
```bash
# Create venv
python -m venv venv

# Activate
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Run server
uvicorn main:app --reload
```

**Direct Execution (Without Activation):**
```bash
# Use full path to venv python
./venv/bin/python -m uvicorn main:app --reload

# Or venv uvicorn directly
./venv/bin/uvicorn main:app --reload
```

**In Scripts:**
```bash
#!/bin/bash
# start-dev.sh

# Activate venv and run
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Environment Variables for Imports:**
```bash
# Set PYTHONPATH for imports
PYTHONPATH=/opt/fastapi-app ./venv/bin/uvicorn app.main:app --reload
```

### WSL WATCHFILES_FORCE_POLLING

**Problem:** File watching doesn't work in WSL (Windows Subsystem for Linux) due to filesystem event limitations.

**Solution:** Force polling mode for file changes.

```bash
# Set environment variable
export WATCHFILES_FORCE_POLLING=true

# Run uvicorn
uvicorn main:app --reload

# Or inline
WATCHFILES_FORCE_POLLING=true uvicorn main:app --reload
```

**Permanent Configuration (.bashrc or .zshrc):**
```bash
# Add to shell config
echo 'export WATCHFILES_FORCE_POLLING=true' >> ~/.bashrc
source ~/.bashrc
```

**In Python Code:**
```python
import os
os.environ['WATCHFILES_FORCE_POLLING'] = 'true'

import uvicorn

if __name__ == "__main__":
    uvicorn.run("main:app", reload=True)
```

### Reload Directory Configuration

**Watch Specific Directories:**
```bash
# Single directory
uvicorn main:app --reload --reload-dir ./app

# Multiple directories
uvicorn main:app --reload \
  --reload-dir ./app \
  --reload-dir ./config \
  --reload-dir ./models
```

**Exclude Directories:**
```bash
uvicorn main:app --reload \
  --reload-dir ./app \
  --reload-exclude ./app/tests \
  --reload-exclude ./app/migrations
```

**Include Specific File Patterns:**
```bash
uvicorn main:app --reload \
  --reload-include '*.py' \
  --reload-include '*.yaml' \
  --reload-include '*.json'
```

**In Code:**
```python
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        reload=True,
        reload_dirs=["./app", "./config"],
        reload_excludes=["./tests", "./migrations"],
        reload_includes=["*.py", "*.yaml"]
    )
```

### Worker Management

**Development:** Always use 1 worker with reload.
```bash
uvicorn main:app --reload --workers 1
```

**Production:** Calculate workers based on CPU cores.

**Formula:** `(2 × CPU cores) + 1`

```bash
# 4 CPU cores = 9 workers
gunicorn app.main:app \
  --workers 9 \
  --worker-class uvicorn.workers.UvicornWorker
```

**Dynamic Worker Calculation:**
```python
# gunicorn_conf.py
import multiprocessing

workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "uvicorn.workers.UvicornWorker"
```

**Worker Timeout Configuration:**
```python
# gunicorn_conf.py
timeout = 120           # Worker timeout (seconds)
graceful_timeout = 30   # Graceful shutdown time
keepalive = 5           # Keep-alive seconds
```

## Framework-Specific Best Practices

### Dependency Injection

FastAPI's dependency injection system:

```python
from fastapi import Depends, FastAPI
from sqlalchemy.orm import Session

app = FastAPI()

# Database dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/users/{user_id}")
def read_user(user_id: int, db: Session = Depends(get_db)):
    return db.query(User).filter(User.id == user_id).first()
```

**Benefit for Development:**
- Dependencies are reloaded automatically
- Easy mocking for tests
- Clean separation of concerns

### Async Operations

**Use async for I/O-bound operations:**

```python
from fastapi import FastAPI
import httpx

app = FastAPI()

@app.get("/external")
async def call_external():
    async with httpx.AsyncClient() as client:
        response = await client.get("https://api.example.com")
        return response.json()
```

**Mixed sync/async endpoints:**

```python
# Sync endpoint (blocking)
@app.get("/sync")
def sync_endpoint():
    result = blocking_operation()
    return result

# Async endpoint (non-blocking)
@app.get("/async")
async def async_endpoint():
    result = await async_operation()
    return result
```

**Worker configuration for async:**
```python
# gunicorn_conf.py
# Use UvicornWorker for async support
worker_class = "uvicorn.workers.UvicornWorker"
```

### Lifespan Events

**Startup and shutdown logic:**

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("Starting up...")
    # Initialize database pool, cache connections, etc.
    yield
    # Shutdown
    print("Shutting down...")
    # Close database pool, cleanup resources

app = FastAPI(lifespan=lifespan)
```

**Why important for development:**
- Clean resource management
- Proper connection pooling
- Graceful reload on code changes

### Static Files and Templates

**Serve static files:**

```python
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
```

**Templates with Jinja2:**

```python
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates

app = FastAPI()
templates = Jinja2Templates(directory="templates")

@app.get("/")
def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})
```

**Auto-reload includes templates and static files** when using `--reload-dir`.

## Common Problems & Solutions

### Problem 1: Port Already in Use (EADDRINUSE)

**Symptoms:**
```
ERROR: [Errno 48] error while attempting to bind on address ('0.0.0.0', 8000): address already in use
```

**Root Cause:**
Another process (previous Uvicorn instance, other server, or zombie process) is using port 8000.

**Solution:**

**Option A: Find and Kill Process**
```bash
# Linux/macOS
lsof -ti:8000 | xargs kill -9

# Alternative with fuser
fuser -k 8000/tcp

# Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

**Option B: Use Different Port**
```bash
uvicorn main:app --reload --port 8001
```

**Option C: Cleanup Script**
```bash
#!/bin/bash
# kill-and-start.sh

# Kill any process on port 8000
lsof -ti:8000 | xargs kill -9 2>/dev/null || true

# Wait a moment
sleep 1

# Start server
uvicorn main:app --reload --port 8000
```

**Option D: Dynamic Port Selection**
```python
import uvicorn
import socket

def find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port

if __name__ == "__main__":
    port = find_free_port()
    print(f"Starting server on port {port}")
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
```

### Problem 2: Auto-Reload Not Working

**Symptoms:**
- Code changes don't trigger server restart
- Need to manually restart Uvicorn
- No "Reload detected" messages in console

**Root Cause:**
Multiple causes: file watching disabled, wrong reload directory, WSL filesystem issues, or PM2 interference.

**Solution:**

**Step 1: Verify Reload is Enabled**
```bash
# Ensure --reload flag is present
uvicorn main:app --reload
```

**Step 2: Check Reload Directories**
```bash
# Explicitly set reload directory
uvicorn main:app --reload --reload-dir ./app

# Include specific file patterns
uvicorn main:app --reload --reload-include '*.py'
```

**Step 3: WSL Force Polling**
```bash
# For WSL on Windows
WATCHFILES_FORCE_POLLING=true uvicorn main:app --reload
```

**Step 4: Check File Permissions**
```bash
# Ensure files are readable
chmod -R 644 ./app/*.py
```

**Step 5: Disable PM2 Watch**

If using PM2 (not recommended for dev):
```javascript
// ecosystem.config.js
module.exports = {
  apps: [{
    name: 'fastapi',
    script: 'venv/bin/uvicorn',
    args: 'main:app --reload',
    watch: false  // CRITICAL: must be false
  }]
};
```

**Step 6: Verify No Syntax Errors**

Syntax errors can break auto-reload:
```bash
# Test import
python -c "from app.main import app"
```

**Step 7: Check Uvicorn Version**
```bash
# Update uvicorn
pip install --upgrade uvicorn[standard]
```

### Problem 3: Import Errors After Reload

**Symptoms:**
```
ModuleNotFoundError: No module named 'app'
ImportError: attempted relative import with no known parent package
```

**Root Cause:**
Incorrect PYTHONPATH, wrong working directory, or circular imports.

**Solution:**

**Step 1: Set PYTHONPATH**
```bash
# Add current directory to Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
uvicorn app.main:app --reload

# Or inline
PYTHONPATH=. uvicorn app.main:app --reload
```

**Step 2: Use Python Module Execution**
```bash
# Run as module from project root
python -m uvicorn app.main:app --reload
```

**Step 3: Fix Import Paths**

Bad:
```python
# Relative import without parent
from models import User
```

Good:
```python
# Absolute import
from app.models import User

# Or relative with parent
from .models import User
```

**Step 4: Check Directory Structure**
```
fastapi-project/
├── app/
│   ├── __init__.py  ← REQUIRED for package
│   ├── main.py
│   └── models.py
├── requirements.txt
└── main.py (or run from app.main)
```

**Step 5: Avoid Circular Imports**

Bad:
```python
# a.py
from b import function_b

# b.py
from a import function_a  # Circular!
```

Good:
```python
# Use dependency injection or delayed imports
# a.py
def function_a():
    from b import function_b  # Import inside function
    function_b()
```

### Problem 4: PM2 Watch Mode Breaks Application

**Symptoms:**
- Application restarts continuously
- Import errors appear after file changes
- Worker processes crash unexpectedly

**Root Cause:**
PM2 watch mode interferes with Python's import system and virtual environment, causing module resolution failures.

**Solution:**

**NEVER use PM2 watch mode with FastAPI/Python applications.**

**Wrong:**
```javascript
// ecosystem.config.js
module.exports = {
  apps: [{
    name: 'fastapi',
    script: 'venv/bin/uvicorn',
    args: 'main:app --reload',
    watch: true,  // WRONG - Breaks Python
    ignore_watch: ['logs', '.git']
  }]
};
```

**Correct for Development:**

Don't use PM2 at all. Use uvicorn directly:
```bash
uvicorn main:app --reload
```

**Correct for Production:**

Use PM2 without watch mode:
```javascript
// ecosystem.config.js
module.exports = {
  apps: [{
    name: 'fastapi',
    script: 'venv/bin/gunicorn',
    args: '-c gunicorn_conf.py app.main:app',
    watch: false,  // Correct - no watch mode
    autorestart: true
  }]
};
```

**Alternative: Use systemd for production on Linux.**

### Problem 5: Workers Timing Out Under Load

**Symptoms:**
```
[CRITICAL] WORKER TIMEOUT (pid:12345)
Worker with pid 12345 was terminated due to signal 9
```

**Root Cause:**
Worker timeout too short for slow operations, insufficient workers, or blocking operations in async context.

**Solution:**

**Step 1: Increase Timeout**
```python
# gunicorn_conf.py
timeout = 300  # 5 minutes for long operations
graceful_timeout = 60
```

**Step 2: Optimize Worker Count**
```python
# gunicorn_conf.py
import multiprocessing

# Increase workers for CPU-bound tasks
workers = multiprocessing.cpu_count() * 2 + 1

# Or set explicitly
workers = 8
```

**Step 3: Use Async for I/O Operations**

Bad (blocks worker):
```python
import requests

@app.get("/data")
def get_data():
    response = requests.get("https://slow-api.com")  # Blocks!
    return response.json()
```

Good (non-blocking):
```python
import httpx

@app.get("/data")
async def get_data():
    async with httpx.AsyncClient() as client:
        response = await client.get("https://slow-api.com")
        return response.json()
```

**Step 4: Background Tasks**

For long-running operations:
```python
from fastapi import BackgroundTasks

def process_data(data):
    # Long-running task
    pass

@app.post("/process")
async def trigger_process(background_tasks: BackgroundTasks, data: dict):
    background_tasks.add_task(process_data, data)
    return {"status": "processing"}
```

**Step 5: Monitor Worker Health**
```bash
# Check worker status
ps aux | grep gunicorn

# Monitor logs
tail -f logs/error.log
```

## Anti-Patterns

### What NOT to Do

**1. Never Use PM2 Watch Mode with Python**
```javascript
// WRONG
module.exports = {
  apps: [{
    script: 'venv/bin/uvicorn',
    watch: true  // Breaks Python imports
  }]
};
```

Why: PM2 watch triggers restarts that break Python's import system and virtual environment.

**2. Don't Use Multiple Workers with --reload**
```bash
# WRONG - reload requires single worker
uvicorn main:app --reload --workers 4
```

Reload mode only works with 1 worker. Use multiple workers in production without reload.

**3. Don't Run Blocking Operations in Async Endpoints**
```python
# WRONG
@app.get("/data")
async def get_data():
    result = requests.get("https://api.com")  # Blocking in async!
    return result.json()
```

Use `httpx` or `aiohttp` for async HTTP requests.

**4. Don't Forget Virtual Environment in Production**
```bash
# WRONG - uses system Python
uvicorn main:app

# Correct - uses venv
./venv/bin/uvicorn main:app
```

**5. Don't Skip Graceful Shutdown**
```python
# WRONG - abrupt termination
# No cleanup code

# Correct - graceful shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    # Cleanup: close DB, cache connections
    await db_pool.close()
```

**6. Don't Use Development Server in Production**
```bash
# WRONG for production
uvicorn main:app --reload

# Correct for production
gunicorn app.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker
```

**7. Don't Ignore Security Headers**
```python
# WRONG - no security middleware
app = FastAPI()

# Correct - add security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*.example.com"])
```

## Quick Reference

### Commands

```bash
# Development
uvicorn main:app --reload                     # Basic dev server
uvicorn main:app --reload --port 8001         # Custom port
uvicorn main:app --reload --reload-dir ./app  # Watch specific dir
python -m uvicorn app.main:app --reload       # Module execution

# WSL
WATCHFILES_FORCE_POLLING=true uvicorn main:app --reload

# Production
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker
gunicorn -c gunicorn_conf.py app.main:app

# Virtual Environment
python -m venv venv                           # Create venv
source venv/bin/activate                      # Activate (Linux/macOS)
venv\Scripts\activate                         # Activate (Windows)
./venv/bin/uvicorn main:app --reload          # Direct execution

# Process Management
lsof -ti:8000 | xargs kill -9                 # Kill process on port
ps aux | grep uvicorn                         # Find uvicorn processes

# systemd
sudo systemctl start fastapi                  # Start service
sudo systemctl status fastapi                 # Check status
sudo journalctl -u fastapi -f                 # View logs

# PM2 (Production Only)
pm2 start ecosystem.config.js                 # Start with PM2
pm2 logs fastapi                              # View logs
pm2 restart fastapi                           # Restart
```

### Configuration Templates

**requirements.txt:**
```
fastapi==0.104.1
uvicorn[standard]==0.24.0
gunicorn==21.2.0
python-multipart==0.0.6
pydantic==2.5.0
pydantic-settings==2.1.0
```

**Minimal FastAPI App:**
```python
# main.py
from fastapi import FastAPI
import uvicorn

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Hello World"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
```

**Production Gunicorn Config:**
```python
# gunicorn_conf.py
import multiprocessing

bind = "0.0.0.0:8000"
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "uvicorn.workers.UvicornWorker"
timeout = 120
graceful_timeout = 30
keepalive = 5
max_requests = 1000
max_requests_jitter = 50

accesslog = "./logs/access.log"
errorlog = "./logs/error.log"
loglevel = "info"
```

**systemd Service:**
```ini
[Unit]
Description=FastAPI Application
After=network.target

[Service]
Type=notify
User=www-data
WorkingDirectory=/opt/fastapi-app
Environment="PATH=/opt/fastapi-app/venv/bin"
ExecStart=/opt/fastapi-app/venv/bin/gunicorn -c gunicorn_conf.py app.main:app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**PM2 Config (No Watch):**
```javascript
module.exports = {
  apps: [{
    name: 'fastapi',
    script: '/opt/fastapi-app/venv/bin/gunicorn',
    args: '-c gunicorn_conf.py app.main:app',
    cwd: '/opt/fastapi-app',
    instances: 1,
    exec_mode: 'fork',
    autorestart: true,
    watch: false,  // CRITICAL: never true for Python
    max_memory_restart: '1G',
    env: {
      PYTHONUNBUFFERED: '1'
    }
  }]
};
```

## Related Skills

- **docker-containerization** - For containerized FastAPI deployments
- **systematic-debugging** - For complex debugging scenarios
- **express-local-dev** - Similar patterns for Node.js/Express applications
- **nextjs-local-dev** - For full-stack applications with Next.js frontend

---

**FastAPI Version Compatibility:** This skill covers FastAPI 0.100+ and Uvicorn 0.20+. For older versions, consult the official FastAPI documentation.

**Last Updated:** 2024 - Reflects current best practices for FastAPI development and deployment.
