# Server Management Reference

Complete guide to server lifecycle management, port management, and process control for webapp testing.

## Table of Contents

- [Server Lifecycle](#server-lifecycle)
- [Port Management](#port-management)
- [Process Management](#process-management)
- [Environment Configuration](#environment-configuration)
- [Health Checks](#health-checks)
- [Graceful Shutdown](#graceful-shutdown)
- [Multi-Server Configurations](#multi-server-configurations)
- [Troubleshooting](#troubleshooting)

## Server Lifecycle

### Using with_server.py Helper Script

The `with_server.py` script manages the complete server lifecycle:
- Starts server(s)
- Waits for server(s) to be ready
- Runs your automation script
- Cleans up server(s) automatically

**Always run with `--help` first:**
```bash
python scripts/with_server.py --help
```

### Single Server Management

**Basic usage:**
```bash
python scripts/with_server.py --server "npm run dev" --port 5173 -- python automation.py
```

**With custom timeout:**
```bash
python scripts/with_server.py --server "npm start" --port 3000 --timeout 60 -- python test.py
```

**Django example:**
```bash
python scripts/with_server.py --server "python manage.py runserver 8000" --port 8000 -- python test.py
```

**Flask example:**
```bash
python scripts/with_server.py --server "flask run --port 5000" --port 5000 -- python test.py
```

**Node.js Express example:**
```bash
python scripts/with_server.py --server "node server.js" --port 3000 -- python test.py
```

### Multiple Server Management

**Frontend + Backend:**
```bash
python scripts/with_server.py \
  --server "cd backend && python server.py" --port 3000 \
  --server "cd frontend && npm run dev" --port 5173 \
  -- python test.py
```

**Microservices:**
```bash
python scripts/with_server.py \
  --server "cd auth-service && npm start" --port 3001 \
  --server "cd api-service && npm start" --port 3002 \
  --server "cd frontend && npm start" --port 3000 \
  -- python test.py
```

**Database + API + Frontend:**
```bash
python scripts/with_server.py \
  --server "docker-compose up db" --port 5432 \
  --server "cd api && npm start" --port 4000 \
  --server "cd web && npm start" --port 3000 \
  -- python test.py
```

### Manual Server Management

When you need more control than `with_server.py` provides:

**Start server in background:**
```bash
# Node.js
npm run dev > /tmp/server.log 2>&1 &
echo $! > /tmp/server.pid

# Python
python manage.py runserver > /tmp/server.log 2>&1 &
echo $! > /tmp/server.pid

# Flask
FLASK_APP=app.py flask run > /tmp/server.log 2>&1 &
echo $! > /tmp/server.pid
```

**Check if server is ready:**
```bash
# Using curl
curl -f http://localhost:3000/health
if [ $? -eq 0 ]; then echo "Server ready"; fi

# Using lsof
lsof -i :3000 -sTCP:LISTEN
```

**Stop server:**
```bash
# Using saved PID
kill $(cat /tmp/server.pid)

# Using port
lsof -t -i :3000 | xargs kill

# Force kill if not responding
lsof -t -i :3000 | xargs kill -9
```

## Port Management

### Check Port Availability

**Using lsof (macOS/Linux):**
```bash
# Check if port is in use
lsof -i :3000

# Check specific protocol
lsof -i TCP:3000
lsof -i UDP:3000

# List all listening ports
lsof -i -sTCP:LISTEN
```

**Using netstat (cross-platform):**
```bash
# Check specific port
netstat -an | grep :3000

# List all listening TCP ports
netstat -an | grep LISTEN
```

**Using nc (netcat):**
```bash
# Check if port is open
nc -zv localhost 3000

# Check range of ports
nc -zv localhost 3000-3010
```

**Python check:**
```python
import socket

def is_port_available(port):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('localhost', port))
            return True
    except OSError:
        return False

print(f"Port 3000 available: {is_port_available(3000)}")
```

### Find Process Using Port

```bash
# Get PID of process using port
lsof -t -i :3000

# Get detailed info
lsof -i :3000

# Output example:
# COMMAND   PID USER   FD   TYPE DEVICE SIZE/OFF NODE NAME
# node    12345 user   20u  IPv4 0x1234      0t0  TCP *:3000 (LISTEN)
```

### Kill Process on Port

```bash
# Kill process (graceful)
lsof -t -i :3000 | xargs kill

# Force kill if not responding
lsof -t -i :3000 | xargs kill -9

# Alternative using port number
kill $(lsof -t -i :3000)
```

### Choose Alternative Port

**Check multiple ports:**
```bash
for port in 3000 3001 3002 3003; do
    if ! lsof -i :$port > /dev/null; then
        echo "Port $port is available"
        break
    fi
done
```

**Python find available port:**
```python
import socket

def find_available_port(start=3000, end=3100):
    for port in range(start, end):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('localhost', port))
                return port
        except OSError:
            continue
    return None

port = find_available_port()
print(f"Available port: {port}")
```

## Process Management

### pm2 (Node.js Process Manager)

**Install pm2:**
```bash
npm install -g pm2
```

**Basic commands:**
```bash
# Start server
pm2 start npm --name "my-app" -- start

# Start with environment
pm2 start npm --name "my-app" -- start --update-env

# List running processes
pm2 list

# Monitor processes
pm2 monit

# Show logs
pm2 logs my-app

# Stop process
pm2 stop my-app

# Restart process
pm2 restart my-app

# Delete process
pm2 delete my-app

# Stop all
pm2 stop all
```

**Ecosystem file (pm2.config.js):**
```javascript
module.exports = {
  apps: [{
    name: 'frontend',
    script: 'npm',
    args: 'start',
    cwd: './frontend',
    env: {
      PORT: 3000,
      NODE_ENV: 'development'
    }
  }, {
    name: 'backend',
    script: 'npm',
    args: 'start',
    cwd: './backend',
    env: {
      PORT: 4000,
      NODE_ENV: 'development'
    }
  }]
}
```

**Start from ecosystem:**
```bash
pm2 start pm2.config.js
```

### systemd (Linux System Service)

**Create service file (/etc/systemd/system/myapp.service):**
```ini
[Unit]
Description=My Web Application
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/var/www/myapp
ExecStart=/usr/bin/node server.js
Restart=on-failure
Environment=NODE_ENV=production
Environment=PORT=3000

[Install]
WantedBy=multi-user.target
```

**Service commands:**
```bash
# Reload systemd
sudo systemctl daemon-reload

# Start service
sudo systemctl start myapp

# Stop service
sudo systemctl stop myapp

# Restart service
sudo systemctl restart myapp

# Enable on boot
sudo systemctl enable myapp

# Check status
sudo systemctl status myapp

# View logs
sudo journalctl -u myapp -f
```

### Docker Container Management

**Run server in container:**
```bash
# Start container
docker run -d -p 3000:3000 --name myapp myapp:latest

# Check if container is running
docker ps | grep myapp

# Stop container
docker stop myapp

# Remove container
docker rm myapp

# View logs
docker logs -f myapp
```

**Docker Compose:**
```yaml
# docker-compose.yml
version: '3'
services:
  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      - NODE_ENV=development

  backend:
    build: ./backend
    ports:
      - "4000:4000"
    environment:
      - NODE_ENV=development
```

**Compose commands:**
```bash
# Start all services
docker-compose up -d

# Stop all services
docker-compose down

# View logs
docker-compose logs -f

# Restart service
docker-compose restart frontend
```

## Environment Configuration

### Environment Variables

**Setting environment variables:**
```bash
# Linux/macOS
export PORT=3000
export NODE_ENV=development

# Windows (cmd)
set PORT=3000
set NODE_ENV=development

# Windows (PowerShell)
$env:PORT=3000
$env:NODE_ENV="development"
```

**Using .env file:**
```bash
# .env
PORT=3000
NODE_ENV=development
DATABASE_URL=postgresql://localhost/mydb
API_KEY=secret123
```

**Load .env in Python:**
```python
from dotenv import load_dotenv
import os

load_dotenv()
port = os.getenv('PORT', 3000)
```

**Load .env in Node.js:**
```javascript
require('dotenv').config();
const port = process.env.PORT || 3000;
```

### Configuration Files

**Package.json scripts:**
```json
{
  "scripts": {
    "start": "node server.js",
    "dev": "nodemon server.js",
    "test": "NODE_ENV=test jest",
    "start:prod": "NODE_ENV=production node server.js"
  }
}
```

**Python settings.py:**
```python
import os

PORT = int(os.getenv('PORT', 8000))
DEBUG = os.getenv('DEBUG', 'False') == 'True'
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///db.sqlite3')
```

## Health Checks

### Implementing Health Check Endpoint

**Express.js:**
```javascript
app.get('/health', (req, res) => {
  res.status(200).json({
    status: 'ok',
    timestamp: new Date().toISOString(),
    uptime: process.uptime()
  });
});
```

**Flask:**
```python
@app.route('/health')
def health():
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat()
    })
```

**Django:**
```python
from django.http import JsonResponse
from datetime import datetime

def health_check(request):
    return JsonResponse({
        'status': 'ok',
        'timestamp': datetime.now().isoformat()
    })
```

### Checking Health from Tests

**Using curl:**
```bash
curl -f http://localhost:3000/health
```

**Using Python requests:**
```python
import requests

def wait_for_server(url, timeout=30):
    start = time.time()
    while time.time() - start < timeout:
        try:
            response = requests.get(f"{url}/health", timeout=1)
            if response.status_code == 200:
                return True
        except requests.RequestException:
            time.sleep(0.5)
    return False

if wait_for_server('http://localhost:3000'):
    print("Server is ready")
```

**Using Playwright:**
```python
def wait_for_server_ready(page, url, timeout=30000):
    page.goto(f"{url}/health", timeout=timeout)
    response = page.wait_for_response(f"{url}/health")
    return response.status == 200
```

## Graceful Shutdown

### Signal Handling

**Node.js graceful shutdown:**
```javascript
const server = app.listen(3000);

process.on('SIGTERM', () => {
  console.log('SIGTERM received, closing server...');
  server.close(() => {
    console.log('Server closed');
    process.exit(0);
  });
});

process.on('SIGINT', () => {
  console.log('SIGINT received, closing server...');
  server.close(() => {
    console.log('Server closed');
    process.exit(0);
  });
});
```

**Python graceful shutdown:**
```python
import signal
import sys

def signal_handler(sig, frame):
    print('Shutting down gracefully...')
    # Clean up resources
    sys.exit(0)

signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)
```

### Cleanup Tasks

**Close database connections:**
```javascript
process.on('SIGTERM', async () => {
  await db.close();
  await cache.disconnect();
  server.close(() => process.exit(0));
});
```

**Finish in-flight requests:**
```javascript
server.close(() => {
  console.log('All requests finished');
  process.exit(0);
});

// Force exit after timeout
setTimeout(() => {
  console.error('Forcing shutdown');
  process.exit(1);
}, 10000);
```

## Multi-Server Configurations

### Development Stack

**Full-stack development:**
```bash
# Terminal 1: Database
docker run -d -p 5432:5432 postgres

# Terminal 2: Backend API
cd backend && npm run dev

# Terminal 3: Frontend
cd frontend && npm start

# Or use with_server.py for all at once
python scripts/with_server.py \
  --server "docker run -p 5432:5432 postgres" --port 5432 \
  --server "cd backend && npm run dev" --port 4000 \
  --server "cd frontend && npm start" --port 3000 \
  -- python test.py
```

### Microservices Testing

**Multiple independent services:**
```bash
python scripts/with_server.py \
  --server "cd auth-service && npm start" --port 3001 \
  --server "cd user-service && npm start" --port 3002 \
  --server "cd payment-service && npm start" --port 3003 \
  --server "cd gateway && npm start" --port 3000 \
  -- python integration_test.py
```

### Reverse Proxy Setup

**Nginx configuration:**
```nginx
server {
    listen 80;

    location /api {
        proxy_pass http://localhost:4000;
    }

    location / {
        proxy_pass http://localhost:3000;
    }
}
```

## Troubleshooting

### Server Won't Start

**Port already in use:**
```bash
# Find what's using the port
lsof -i :3000

# Kill the process
lsof -t -i :3000 | xargs kill
```

**Permission denied:**
```bash
# Ports < 1024 require root (avoid if possible)
sudo node server.js  # NOT RECOMMENDED

# Use port >= 1024 instead
PORT=3000 node server.js
```

**Missing dependencies:**
```bash
# Node.js
npm install

# Python
pip install -r requirements.txt

# Check for errors
npm start 2>&1 | tee server.log
```

### Server Crashes During Test

**Check logs:**
```bash
# If using with_server.py, check stderr
python scripts/with_server.py --server "npm start" --port 3000 -- python test.py 2>&1

# Check application logs
tail -f server.log

# Docker logs
docker logs -f container_name
```

**Memory issues:**
```bash
# Increase Node.js memory
NODE_OPTIONS="--max-old-space-size=4096" npm start

# Monitor memory
top -pid $(lsof -t -i :3000)
```

### Server Not Responding

**Check if process is alive:**
```bash
ps aux | grep node
ps aux | grep python
```

**Check network connectivity:**
```bash
# Test localhost
curl http://localhost:3000

# Test network interface
curl http://127.0.0.1:3000

# Check if listening on correct interface
lsof -i -sTCP:LISTEN | grep 3000
```

**Firewall issues:**
```bash
# macOS
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate

# Linux
sudo ufw status
```

### Timeout Issues

**Increase timeout in with_server.py:**
```bash
python scripts/with_server.py --server "npm start" --port 3000 --timeout 60 -- python test.py
```

**Check server startup time:**
```bash
time npm start
```

**Optimize startup:**
- Reduce initial data loading
- Use lazy initialization
- Optimize dependency loading
- Use production builds for testing
