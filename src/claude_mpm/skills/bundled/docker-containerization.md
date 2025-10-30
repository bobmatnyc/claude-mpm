---
skill_id: docker-containerization
skill_version: 0.1.0
description: Essential Docker patterns for containerizing applications.
updated_at: 2025-10-30T17:00:00Z
tags: [docker, containers, deployment, devops]
---

# Docker Containerization

Essential Docker patterns for containerizing applications.

## Basic Dockerfile Structure

```dockerfile
# Use official base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy dependency files first (better caching)
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Run application
CMD ["python", "app.py"]
```

## Multi-Stage Builds

```dockerfile
# Build stage
FROM node:18 AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Production stage
FROM node:18-slim
WORKDIR /app
COPY --from=builder /app/dist ./dist
COPY package*.json ./
RUN npm ci --only=production
EXPOSE 3000
CMD ["node", "dist/server.js"]
```

## Docker Compose

```yaml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://db:5432/myapp
    depends_on:
      - db
    volumes:
      - ./src:/app/src  # Hot reload in dev

  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=myapp
      - POSTGRES_PASSWORD=secret
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

## Best Practices

### ✅ DO
```dockerfile
# Use specific versions
FROM python:3.11-slim

# Non-root user
RUN useradd -m appuser
USER appuser

# Layer caching
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .

# Health check
HEALTHCHECK --interval=30s CMD curl -f http://localhost:8000/health || exit 1
```

### ❌ DON'T
```dockerfile
# Avoid latest tag
FROM python:latest

# Avoid running as root
USER root

# Don't copy unnecessary files
COPY . .  # Includes .git, node_modules, etc.

# Use .dockerignore instead
```

## .dockerignore

```
.git
.gitignore
node_modules
__pycache__
*.pyc
.env
.vscode
README.md
docker-compose.yml
```

## Common Commands

```bash
# Build image
docker build -t myapp:1.0 .

# Run container
docker run -p 8000:8000 myapp:1.0

# Run with environment variables
docker run -e DATABASE_URL=postgresql://... myapp:1.0

# Interactive shell
docker run -it myapp:1.0 /bin/bash

# View logs
docker logs container_id

# Stop container
docker stop container_id

# Remove container
docker rm container_id

# Remove image
docker rmi myapp:1.0

# Prune unused resources
docker system prune -a
```

## Docker Compose Commands

```bash
# Start services
docker-compose up

# Start in background
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Rebuild
docker-compose build

# Run command in service
docker-compose exec web python manage.py migrate
```

## Remember
- Keep images small (use slim/alpine variants)
- Use specific version tags
- Leverage layer caching
- Don't include secrets in images
- Use .dockerignore to exclude files
