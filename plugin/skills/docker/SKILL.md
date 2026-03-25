---
agent_id: docker
---
# Docker (Dev + Prod)

## Development image (reload)

```dockerfile
FROM python:3.11-slim
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

If reload does not trigger inside containers (common on mounted volumes), set polling:

```yaml
environment:
  - WATCHFILES_FORCE_POLLING=true
```

## Production image (Gunicorn)

```dockerfile
FROM python:3.11-slim
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
CMD ["gunicorn", "app.main:app", "-k", "uvicorn.workers.UvicornWorker", "-w", "4", "--bind", "0.0.0.0:8000"]
```

## docker-compose (dev)

```yaml
services:
  api:
    build: .
    ports: ["8000:8000"]
    volumes: ["./:/app"]
    environment:
      - PYTHONUNBUFFERED=1
      - WATCHFILES_FORCE_POLLING=true
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

