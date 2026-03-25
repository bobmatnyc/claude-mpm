---
name: docker
description: Docker containerization for packaging applications with dependencies into isolated, portable units ensuring consistency across development, testing, and production environments.
progressive_disclosure:
  entry_point:
    - summary
    - when_to_use
    - quick_start
  sections:
    - core_concepts
    - dockerfile_basics
    - multi_stage_builds
    - docker_compose
    - development_workflows
    - production_patterns
    - framework_examples
    - orchestration
    - debugging
    - troubleshooting
    - best_practices
---

# Docker Containerization Skill

## Summary
Docker provides containerization for packaging applications with their dependencies into isolated, portable units. Containers ensure consistency across development, testing, and production environments, eliminating "works on my machine" problems.

## When to Use
- **Local Development**: Consistent dev environments across team members
- **CI/CD Pipelines**: Reproducible build and test environments
- **Microservices**: Isolated services with independent scaling
- **Production Deployment**: Portable applications across cloud providers
- **Database/Service Testing**: Ephemeral databases for integration tests
- **Legacy Application Isolation**: Run incompatible dependencies side-by-side

## Quick Start

### 1. Create Dockerfile
```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
EXPOSE 3000
CMD ["node", "server.js"]
```

### 2. Build Image
```bash
docker build -t myapp:1.0 .
```

### 3. Run Container
```bash
docker run -p 3000:3000 myapp:1.0
```

---

## Core Concepts

### Images vs Containers
- **Image**: Read-only template with application code, runtime, and dependencies
- **Container**: Running instance of an image with writable layer
- **Registry**: Storage for images (Docker Hub, GitHub Container Registry)

### Layers and Caching
Each Dockerfile instruction creates a layer. Docker caches unchanged layers for faster builds.

```dockerfile
# GOOD: Dependencies change less frequently than code
FROM python:3.11-slim
COPY requirements.txt .
RUN pip install -r requirements.txt  # Cached unless requirements.txt changes
COPY . .                              # Rebuild only when code changes

# BAD: Invalidates cache on every code change
FROM python:3.11-slim
COPY . .                              # Changes frequently
RUN pip install -r requirements.txt  # Reinstalls on every build
```

### Volumes
Persistent data storage that survives container restarts.

```bash
# Named volume (managed by Docker)
docker run -v mydata:/app/data myapp

# Bind mount (host directory)
docker run -v $(pwd)/data:/app/data myapp

# Anonymous volume (temporary)
docker run -v /app/data myapp
```

### Networks
Containers communicate through Docker networks.

```bash
# Create network
docker network create mynetwork

# Run containers on network
docker run --network mynetwork --name db postgres
docker run --network mynetwork --name app myapp
# App can connect to db using hostname "db"
```

---

## Dockerfile Basics

### Essential Instructions

```dockerfile
# Base image
FROM node:18-alpine

# Metadata
LABEL maintainer="dev@example.com"
LABEL version="1.0"

# Set working directory
WORKDIR /app

# Copy files
COPY package*.json ./
COPY src/ ./src/

# Run commands (creates layer)
RUN npm ci --only=production

# Set environment variables
ENV NODE_ENV=production
ENV PORT=3000

# Expose ports (documentation only)
EXPOSE 3000

# Default command
CMD ["node", "src/server.js"]

# Alternative: ENTRYPOINT (not overridden by docker run args)
ENTRYPOINT ["node"]
CMD ["src/server.js"]  # Default args for ENTRYPOINT
```

### Instruction Order for Cache Efficiency

```dockerfile
# 1. Base image (rarely changes)
FROM python:3.11-slim

# 2. System dependencies (rarely change)
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 3. Application dependencies (change occasionally)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Application code (changes frequently)
COPY . .

# 5. Runtime configuration
ENV PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
```

### .dockerignore
Exclude files from build context (faster builds, smaller images).

```
# .dockerignore
node_modules/
npm-debug.log
.git/
.gitignore
*.md
.env
.vscode/
__pycache__/
*.pyc
.pytest_cache/
coverage/
dist/
build/
```

---

## Multi-Stage Builds

Optimize image size by separating build and runtime stages.

### Node.js TypeScript Example

```dockerfile
# Build stage
FROM node:18-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Production stage
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY --from=builder /app/dist ./dist
EXPOSE 3000
CMD ["node", "dist/server.js"]
```

**Benefits**:
- Build dependencies (TypeScript, webpack) excluded from final image
- Final image: ~50MB vs ~500MB with build tools
- Faster deployments and reduced attack surface

### Python Example

```dockerfile
# Build stage
FROM python:3.11 AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Runtime stage
FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY . .
ENV PATH=/root/.local/bin:$PATH
CMD ["python", "app.py"]
```

### Go Example (Smallest Images)

```dockerfile
# Build stage
FROM golang:1.21-alpine AS builder
WORKDIR /app
COPY go.* ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -o server

# Runtime stage (scratch = empty base image)
FROM scratch
COPY --from=builder /app/server /server
EXPOSE 8080
ENTRYPOINT ["/server"]
```

Result: ~10MB final image containing only the compiled binary.

---

## Docker Compose

Define multi-container applications in YAML.

### Basic Structure

```yaml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "3000:3000"
    environment:
      - DATABASE_URL=postgres://db:5432/myapp
    depends_on:
      - db
    volumes:
      - ./src:/app/src  # Hot reload in development

  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_PASSWORD: secret
      POSTGRES_DB: myapp
    volumes:
      - db_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

volumes:
  db_data:
```

### Commands

```bash
# Start all services
docker-compose up

# Start in background
docker-compose up -d

# Rebuild images
docker-compose up --build

# Stop services
docker-compose down

# Stop and remove volumes
docker-compose down -v

# View logs
docker-compose logs -f app

# Run one-off command
docker-compose run app npm test
```

### Full Stack Example

```yaml
version: '3.8'

services:
  # Frontend
  web:
    build:
      context: ./frontend
      dockerfile: Dockerfile.dev
    ports:
      - "3000:3000"
    volumes:
      - ./frontend/src:/app/src
    environment:
      - REACT_APP_API_URL=http://localhost:8000

  # Backend API
  api:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:secret@db:5432/myapp
      - REDIS_URL=redis://redis:6379
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_started
    volumes:
      - ./backend:/app
    command: uvicorn main:app --host 0.0.0.0 --reload

  # Database
  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_PASSWORD: secret
      POSTGRES_DB: myapp
    volumes:
      - db_data:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Cache
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  # Worker (background jobs)
  worker:
    build: ./backend
    command: celery -A tasks worker --loglevel=info
    environment:
      - REDIS_URL=redis://redis:6379
    depends_on:
      - redis
      - db

volumes:
  db_data:
  redis_data:

networks:
  default:
    name: myapp_network
```

---

## Development Workflows

### Hot Reload with Volumes

#### Node.js

```yaml
services:
  app:
    build: .
    volumes:
      - ./src:/app/src        # Sync source code
      - /app/node_modules     # Prevent overwriting container's node_modules
    command: npm run dev
```

```dockerfile
# Dockerfile.dev
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install  # Include dev dependencies
COPY . .
EXPOSE 3000
CMD ["npm", "run", "dev"]
```

#### Python (Django/FastAPI)

```yaml
services:
  web:
    build: .
    volumes:
      - .:/app
    command: python manage.py runserver 0.0.0.0:8000
    # or for FastAPI:
    # command: uvicorn main:app --host 0.0.0.0 --reload
```

### VS Code Dev Containers

`.devcontainer/devcontainer.json`:

```json
{
  "name": "Python Dev Container",
  "dockerComposeFile": "../docker-compose.yml",
  "service": "app",
  "workspaceFolder": "/app",
  "customizations": {
    "vscode": {
      "extensions": [
        "ms-python.python",
        "ms-python.vscode-pylance"
      ],
      "settings": {
        "python.defaultInterpreterPath": "/usr/local/bin/python"
      }
    }
  },
  "postCreateCommand": "pip install -r requirements-dev.txt",
  "remoteUser": "vscode"
}
```

### Local Database Containers

```bash
# PostgreSQL
docker run -d \
  --name dev-postgres \
  -e POSTGRES_PASSWORD=localdev \
  -e POSTGRES_DB=myapp_dev \
  -p 5432:5432 \
  -v pgdata:/var/lib/postgresql/data \
  postgres:15-alpine

# MySQL
docker run -d \
  --name dev-mysql \
  -e MYSQL_ROOT_PASSWORD=localdev \
  -e MYSQL_DATABASE=myapp_dev \
  -p 3306:3306 \
  -v mysqldata:/var/lib/mysql \
  mysql:8

# MongoDB
docker run -d \
  --name dev-mongo \
  -p 27017:27017 \
  -v mongodata:/data/db \
  mongo:7

# Redis
docker run -d \
  --name dev-redis \
  -p 6379:6379 \
  redis:7-alpine
```

---

## Production Patterns

### Health Checks

```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .

# Health check endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD node healthcheck.js

EXPOSE 3000
CMD ["node", "server.js"]
```

```javascript
// healthcheck.js
const http = require('http');

const options = {
  host: 'localhost',
  port: 3000,
  path: '/health',
  timeout: 2000
};

const request = http.request(options, (res) => {
  if (res.statusCode === 200) {
    process.exit(0);
  } else {
    process.exit(1);
  }
});

request.on('error', () => process.exit(1));
request.end();
```

### Security Best Practices

```dockerfile
FROM python:3.11-slim

# 1. Use non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# 2. Install dependencies as root
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 3. Copy application files
COPY --chown=appuser:appuser . .

# 4. Switch to non-root user
USER appuser

# 5. Drop unnecessary privileges
EXPOSE 8000
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "app:app"]
```

**Additional Security Measures**:
- Use minimal base images (alpine, distroless)
- Scan images for vulnerabilities: `docker scan myapp:latest`
- Don't include secrets in images (use environment variables or secret managers)
- Keep base images updated
- Use read-only root filesystem when possible

### Secrets Management

```bash
# Docker Swarm secrets (production)
echo "db_password_here" | docker secret create db_password -
```

```yaml
version: '3.8'
services:
  app:
    image: myapp
    secrets:
      - db_password
    environment:
      - DB_PASSWORD_FILE=/run/secrets/db_password

secrets:
  db_password:
    external: true
```

**Alternative: Environment Files**

```yaml
# docker-compose.yml
services:
  app:
    env_file:
      - .env.production  # Never commit this file
```

```bash
# .env.production (gitignored)
DATABASE_URL=postgresql://user:pass@db:5432/prod
SECRET_KEY=your-secret-key
```

### Resource Limits

```yaml
services:
  app:
    image: myapp
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 512M
        reservations:
          cpus: '0.5'
          memory: 256M
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3
```

```bash
# Command-line resource limits
docker run -d \
  --memory="512m" \
  --cpus="1.0" \
  --restart=unless-stopped \
  myapp
```

---

## Framework-Specific Examples

### Python: Django

```dockerfile
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Collect static files
RUN python manage.py collectstatic --noinput

# Create non-root user
RUN useradd -m -u 1000 django && chown -R django:django /app
USER django

EXPOSE 8000
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "myproject.wsgi:application"]
```

**docker-compose.yml**:

```yaml
version: '3.8'

services:
  web:
    build: .
    command: python manage.py runserver 0.0.0.0:8000
    volumes:
      - .:/app
    ports:
      - "8000:8000"
    environment:
      - DEBUG=1
      - DATABASE_URL=postgres://postgres:postgres@db:5432/django_dev
    depends_on:
      - db

  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: django_dev
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

### Python: FastAPI

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

### Node.js: Next.js

```dockerfile
# Multi-stage build for Next.js
FROM node:18-alpine AS deps
WORKDIR /app
COPY package*.json ./
RUN npm ci

FROM node:18-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

FROM node:18-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production

RUN addgroup -g 1001 -S nodejs
RUN adduser -S nextjs -u 1001

COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000

CMD ["node", "server.js"]
```

**next.config.js** (required for standalone output):

```javascript
module.exports = {
  output: 'standalone',
}
```

### Node.js: Express

```dockerfile
FROM node:18-alpine

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm ci --only=production

# Copy application
COPY . .

# Create non-root user
RUN addgroup -S appgroup && adduser -S appuser -G appgroup
USER appuser

EXPOSE 3000

CMD ["node", "server.js"]
```

### TypeScript Build

```dockerfile
# Build stage
FROM node:18-alpine AS builder
WORKDIR /app
COPY package*.json tsconfig.json ./
RUN npm ci
COPY src/ ./src/
RUN npm run build

# Production stage
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY --from=builder /app/dist ./dist

EXPOSE 3000
CMD ["node", "dist/index.js"]
```

---

## Container Orchestration Basics

### Docker Swarm (Built-in)

```bash
# Initialize swarm
docker swarm init

# Deploy stack
docker stack deploy -c docker-compose.yml myapp

# Scale service
docker service scale myapp_web=5

# Update service (zero-downtime)
docker service update --image myapp:2.0 myapp_web

# Remove stack
docker stack rm myapp
```

### Kubernetes Comparison

| Feature | Docker Compose | Docker Swarm | Kubernetes |
|---------|---------------|--------------|------------|
| **Complexity** | Low | Medium | High |
| **Use Case** | Local dev | Small clusters | Production at scale |
| **Setup** | Single file | Built-in | Separate installation |
| **Scaling** | Manual | Automatic | Automatic + Advanced |
| **HA** | No | Yes | Yes |
| **Ecosystem** | Limited | Docker | Massive |

**When to use each**:
- **Docker Compose**: Local development, simple deployments
- **Docker Swarm**: Small production clusters, simpler than K8s
- **Kubernetes**: Large-scale production, multi-cloud, advanced orchestration

---

## CI/CD Integration

### GitHub Actions

```yaml
# .github/workflows/docker.yml
name: Build and Push Docker Image

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  build:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write

    steps:
      - uses: actions/checkout@v3

      - name: Log in to Container Registry
        uses: docker/login-action@v2
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v4
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
          tags: |
            type=ref,event=branch
            type=semver,pattern={{version}}
            type=sha

      - name: Build and push
        uses: docker/build-push-action@v4
        with:
          context: .
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

      - name: Run tests
        run: |
          docker run --rm ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }} npm test
```

### GitLab CI

```yaml
# .gitlab-ci.yml
stages:
  - build
  - test
  - deploy

variables:
  DOCKER_DRIVER: overlay2
  IMAGE_TAG: $CI_REGISTRY_IMAGE:$CI_COMMIT_SHORT_SHA

build:
  stage: build
  image: docker:latest
  services:
    - docker:dind
  script:
    - docker login -u $CI_REGISTRY_USER -p $CI_REGISTRY_PASSWORD $CI_REGISTRY
    - docker build -t $IMAGE_TAG .
    - docker push $IMAGE_TAG

test:
  stage: test
  script:
    - docker run --rm $IMAGE_TAG npm test

deploy:
  stage: deploy
  script:
    - docker pull $IMAGE_TAG
    - docker tag $IMAGE_TAG $CI_REGISTRY_IMAGE:latest
    - docker push $CI_REGISTRY_IMAGE:latest
  only:
    - main
```

---

## Debugging Containers

### Viewing Logs

```bash
# Stream logs
docker logs -f container_name

# Last 100 lines
docker logs --tail 100 container_name

# Logs since timestamp
docker logs --since 2024-01-01T10:00:00 container_name

# With timestamps
docker logs -t container_name

# Docker Compose logs
docker-compose logs -f service_name
```

### Execute Commands in Running Container

```bash
# Interactive shell
docker exec -it container_name /bin/sh
# or
docker exec -it container_name /bin/bash

# Run single command
docker exec container_name ls -la /app

# Run as different user
docker exec -u root container_name apt-get update
```

### Inspect Container

```bash
# Full container details
docker inspect container_name

# Specific field (IP address)
docker inspect -f '{{.NetworkSettings.IPAddress}}' container_name

# Environment variables
docker inspect -f '{{.Config.Env}}' container_name

# Mounted volumes
docker inspect -f '{{.Mounts}}' container_name
```

### Resource Usage

```bash
# Real-time stats
docker stats

# Single container
docker stats container_name

# No streaming (single snapshot)
docker stats --no-stream
```

### Network Debugging

```bash
# List networks
docker network ls

# Inspect network
docker network inspect bridge

# Test connectivity between containers
docker exec container1 ping container2

# Check DNS resolution
docker exec container_name nslookup other_container
```

### Debugging Build Issues

```bash
# Build with no cache
docker build --no-cache -t myapp .

# Show build progress
docker build --progress=plain -t myapp .

# Build specific stage
docker build --target builder -t myapp-builder .

# Inspect intermediate layers
docker history myapp:latest
```

---

## Local Docker Patterns (mcp-browser, mcp-memory)

### mcp-browser dev compose

- `docker-compose.yml` runs `mcp-server` with a port range `8875-8895` and optional `chrome` profile.
- Code mounts are read-only (`./src:/app/src:ro`) with persistent logs and temp volumes.
- Environment defaults: `MCP_DEBUG=true`, `MCP_LOG_LEVEL=DEBUG`, `MCP_HOST=0.0.0.0`, `MCP_PORT=8875`.
- Optional profiles: `chrome` (browser) and `tools` (dev tools container).

### mcp-browser Dockerfile.dev

- `ARG PYTHON_VERSION=3.11`, install `watchdog` + Playwright Chromium.
- Install package in editable mode and run `python -m src.dev_runner`.
- Non-root user and healthcheck on `/health`.

### mcp-memory production Dockerfile

- Multi-stage build with venv in `/opt/venv` and `python:3.11-slim`.
- Runtime installs `curl` for healthcheck, sets `PYTHONPATH=/app`.
- Uses non-root user and `CMD ["python", "run_api_server.py"]` with `/health` check.

## Troubleshooting

### Common Issues

#### "Port already in use"

```bash
# Find process using port
lsof -i :3000
# or
netstat -tulpn | grep 3000

# Kill process
kill -9 <PID>

# Or use different host port
docker run -p 3001:3000 myapp
```

#### "Cannot connect to Docker daemon"

```bash
# Check Docker is running
docker info

# Restart Docker Desktop (Mac/Windows)
# or
sudo systemctl restart docker  # Linux

# Check permissions (Linux)
sudo usermod -aG docker $USER
# Log out and back in
```

#### "No space left on device"

```bash
# Remove unused containers, images, volumes
docker system prune -a --volumes

# Remove only dangling images
docker image prune

# Remove stopped containers
docker container prune

# Remove unused volumes
docker volume prune

# Check disk usage
docker system df
```

#### "Build context too large"

```bash
# Create .dockerignore
cat > .dockerignore << EOF
node_modules/
.git/
*.log
dist/
coverage/
EOF

# Build with specific context
docker build -f Dockerfile -t myapp ./src
```

#### Container Exits Immediately

```bash
# Check logs
docker logs container_name

# Run with interactive shell to debug
docker run -it myapp /bin/sh

# Override entrypoint
docker run -it --entrypoint /bin/sh myapp

# Check exit code
docker inspect -f '{{.State.ExitCode}}' container_name
```

#### Permission Denied in Container

```bash
# Run as root to debug
docker exec -u root -it container_name /bin/sh

# Fix ownership
docker exec -u root container_name chown -R appuser:appuser /app

# Or rebuild with correct permissions in Dockerfile
```

### Performance Issues

#### Slow Builds

```bash
# Use BuildKit (faster, better caching)
DOCKER_BUILDKIT=1 docker build -t myapp .

# Multi-stage builds to reduce layers
# Order instructions by change frequency
# Use .dockerignore to exclude unnecessary files
```

#### High Memory Usage

```bash
# Set memory limits
docker run -m 512m myapp

# Monitor memory
docker stats container_name

# Check for memory leaks in application
```

#### Slow Volume Mounts (Mac/Windows)

```bash
# Use delegated consistency (Mac)
volumes:
  - ./src:/app/src:delegated

# Or use named volumes instead of bind mounts
volumes:
  - node_modules:/app/node_modules
```

---

## Best Practices

### Layer Optimization

1. **Order by Change Frequency**: Least frequently changed first
2. **Combine RUN Commands**: Reduce layers
3. **Clean Up in Same Layer**: Remove temp files immediately

```dockerfile
# GOOD
RUN apt-get update && apt-get install -y \
    package1 \
    package2 \
    && rm -rf /var/lib/apt/lists/*

# BAD (creates 3 layers, apt cache remains in layer 2)
RUN apt-get update
RUN apt-get install -y package1 package2
RUN rm -rf /var/lib/apt/lists/*
```

### Image Size Reduction

1. **Use Alpine Images**: 5MB vs 100MB+ for full Linux
2. **Multi-Stage Builds**: Exclude build tools from final image
3. **Remove Unnecessary Files**: Docs, examples, tests
4. **Use .dockerignore**: Exclude development files

```dockerfile
# Before: 800MB
FROM node:18
COPY . .
RUN npm install
CMD ["node", "server.js"]

# After: 120MB
FROM node:18-alpine
COPY package*.json ./
RUN npm ci --only=production
COPY server.js .
CMD ["node", "server.js"]
```

### Security Checklist

- [ ] Use official base images from trusted sources
- [ ] Specify exact image versions (not `latest`)
- [ ] Run as non-root user
- [ ] Scan images for vulnerabilities
- [ ] Keep base images updated
- [ ] Don't embed secrets in images
- [ ] Use read-only root filesystem when possible
- [ ] Minimize attack surface (alpine, distroless)
- [ ] Enable Docker Content Trust (image signing)

### Development vs Production

**Development**:
```dockerfile
FROM node:18
WORKDIR /app
COPY package*.json ./
RUN npm install  # Include dev dependencies
COPY . .
CMD ["npm", "run", "dev"]
```

**Production**:
```dockerfile
FROM node:18-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY --from=builder /app/dist ./dist
USER node
CMD ["node", "dist/server.js"]
```

### Logging Best Practices

```dockerfile
# Log to stdout/stderr (Docker captures these)
CMD ["node", "server.js"]  # Good

# Don't log to files (lost when container stops)
CMD ["node", "server.js", ">", "app.log"]  # Bad
```

```javascript
// Application logging
console.log('Info message');   // stdout
console.error('Error message'); // stderr

// Use structured logging
console.log(JSON.stringify({
  level: 'info',
  timestamp: new Date().toISOString(),
  message: 'Request processed',
  requestId: '123'
}));
```

### Environment Configuration

```dockerfile
# Use ARG for build-time variables
ARG NODE_ENV=production
ENV NODE_ENV=$NODE_ENV

# Use ENV for runtime variables
ENV PORT=3000
ENV LOG_LEVEL=info

# Override at runtime
# docker run -e PORT=8080 -e LOG_LEVEL=debug myapp
```

### Health Checks

```dockerfile
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:3000/health || exit 1
```

```yaml
# docker-compose.yml
services:
  app:
    image: myapp
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/health"]
      interval: 30s
      timeout: 3s
      retries: 3
      start_period: 40s
```

### Graceful Shutdown

```javascript
// Node.js example
process.on('SIGTERM', () => {
  console.log('SIGTERM received, closing server...');
  server.close(() => {
    console.log('Server closed');
    process.exit(0);
  });
});
```

```dockerfile
# Use exec form to properly handle signals
CMD ["node", "server.js"]  # Good
CMD node server.js          # Bad (wrapped in /bin/sh, signals not forwarded)
```

---

## Quick Reference

### Essential Commands

```bash
# Images
docker build -t name:tag .
docker pull image:tag
docker push image:tag
docker images
docker rmi image:tag

# Containers
docker run -d --name container image
docker ps                    # Running containers
docker ps -a                 # All containers
docker stop container
docker start container
docker restart container
docker rm container
docker logs -f container
docker exec -it container /bin/sh

# Cleanup
docker system prune -a       # Remove all unused resources
docker container prune       # Remove stopped containers
docker image prune          # Remove dangling images
docker volume prune         # Remove unused volumes

# Compose
docker-compose up -d
docker-compose down
docker-compose logs -f
docker-compose exec service /bin/sh
docker-compose build
```

### Common Flags

```bash
# docker run flags
-d              # Detached (background)
-it             # Interactive with TTY
-p 8080:80      # Port mapping (host:container)
--name myapp    # Container name
-e VAR=value    # Environment variable
-v /host:/container  # Volume mount
--network name  # Connect to network
--rm            # Remove container on exit
-m 512m         # Memory limit
--cpus 1.0      # CPU limit
```

### Dockerfile Instructions

```dockerfile
FROM image:tag           # Base image
WORKDIR /path            # Set working directory
COPY src dst             # Copy files
ADD src dst              # Copy (with URL/tar support)
RUN command              # Execute command
ENV KEY=value            # Environment variable
EXPOSE port              # Document port
CMD ["executable"]       # Default command
ENTRYPOINT ["exec"]      # Command prefix
VOLUME /path             # Create mount point
USER username            # Set user
ARG name=default         # Build argument
LABEL key=value          # Metadata
HEALTHCHECK CMD command  # Health check
```

---

## Summary

Docker containerization provides:
- **Consistency**: Identical environments from dev to production
- **Isolation**: Dependencies don't conflict between applications
- **Portability**: Run anywhere Docker runs (cloud, local, CI)
- **Efficiency**: Lightweight compared to VMs, fast startup
- **Scalability**: Easy horizontal scaling with orchestration

**Key Workflows**:
1. **Development**: docker-compose with hot reload volumes
2. **CI/CD**: Build, test, push images to registry
3. **Production**: Pull images, run with resource limits and health checks

**Next Steps**:
- Master multi-stage builds for optimal image sizes
- Implement health checks and graceful shutdown
- Set up docker-compose for local development
- Integrate Docker into CI/CD pipelines
- Explore orchestration (Swarm or Kubernetes) for production scale
