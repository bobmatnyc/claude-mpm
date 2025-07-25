# Creating Custom Services

This guide explains how to create custom services for Claude MPM to add new functionality or integrate with external systems.

## Overview

Services in Claude MPM provide:
- Business logic and data processing
- Integration with external systems
- Shared functionality across components
- State management and persistence
- Background task processing

## Service Architecture

```python
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

class BaseService(ABC):
    """Base class for all services."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self._initialized = False
    
    @abstractmethod
    async def start(self):
        """Start the service."""
        pass
    
    @abstractmethod
    async def stop(self):
        """Stop the service."""
        pass
    
    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """Check service health."""
        pass
```

## Creating a Simple Service

### Example: Cache Service

```python
import time
from typing import Any, Dict, Optional
from collections import OrderedDict
import asyncio

class CacheService(BaseService):
    """In-memory cache service with TTL support."""
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 300):
        super().__init__()
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self._lock = asyncio.Lock()
        self._cleanup_task = None
    
    async def start(self):
        """Start the cache service."""
        self._initialized = True
        # Start cleanup task
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
    
    async def stop(self):
        """Stop the cache service."""
        self._initialized = False
        # Cancel cleanup task
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
    
    def health_check(self) -> Dict[str, Any]:
        """Check cache health."""
        return {
            "status": "healthy" if self._initialized else "stopped",
            "entries": len(self._cache),
            "max_size": self.max_size,
            "memory_usage": self._estimate_memory_usage()
        }
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        async with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                if time.time() < entry["expires"]:
                    # Move to end (LRU)
                    self._cache.move_to_end(key)
                    return entry["value"]
                else:
                    # Expired
                    del self._cache[key]
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Set value in cache."""
        ttl = ttl or self.default_ttl
        expires = time.time() + ttl
        
        async with self._lock:
            # Remove oldest if at capacity
            if len(self._cache) >= self.max_size and key not in self._cache:
                self._cache.popitem(last=False)
            
            self._cache[key] = {
                "value": value,
                "expires": expires
            }
            self._cache.move_to_end(key)
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False
    
    async def clear(self):
        """Clear all cache entries."""
        async with self._lock:
            self._cache.clear()
    
    async def _cleanup_loop(self):
        """Periodically clean up expired entries."""
        while self._initialized:
            try:
                await asyncio.sleep(60)  # Run every minute
                await self._cleanup_expired()
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Cleanup error: {e}")
    
    async def _cleanup_expired(self):
        """Remove expired entries."""
        current_time = time.time()
        async with self._lock:
            expired_keys = [
                k for k, v in self._cache.items()
                if current_time >= v["expires"]
            ]
            for key in expired_keys:
                del self._cache[key]
    
    def _estimate_memory_usage(self) -> int:
        """Estimate memory usage in bytes."""
        # Simplified estimation
        return len(str(self._cache))
```

## Database Service

```python
import asyncpg
from contextlib import asynccontextmanager

class DatabaseService(BaseService):
    """PostgreSQL database service."""
    
    def __init__(self, dsn: str, pool_size: int = 10):
        super().__init__()
        self.dsn = dsn
        self.pool_size = pool_size
        self._pool = None
    
    async def start(self):
        """Start database service."""
        self._pool = await asyncpg.create_pool(
            self.dsn,
            min_size=2,
            max_size=self.pool_size
        )
        self._initialized = True
        
        # Run migrations
        await self._run_migrations()
    
    async def stop(self):
        """Stop database service."""
        if self._pool:
            await self._pool.close()
        self._initialized = False
    
    def health_check(self) -> Dict[str, Any]:
        """Check database health."""
        if not self._initialized or not self._pool:
            return {"status": "unhealthy", "error": "Not initialized"}
        
        return {
            "status": "healthy",
            "pool_size": self._pool.get_size(),
            "idle_connections": self._pool.get_idle_size(),
            "dsn": self._sanitize_dsn(self.dsn)
        }
    
    @asynccontextmanager
    async def acquire(self):
        """Acquire database connection."""
        async with self._pool.acquire() as conn:
            yield conn
    
    async def execute(self, query: str, *args):
        """Execute a query."""
        async with self.acquire() as conn:
            return await conn.execute(query, *args)
    
    async def fetch(self, query: str, *args):
        """Fetch multiple rows."""
        async with self.acquire() as conn:
            return await conn.fetch(query, *args)
    
    async def fetchrow(self, query: str, *args):
        """Fetch single row."""
        async with self.acquire() as conn:
            return await conn.fetchrow(query, *args)
    
    async def fetchval(self, query: str, *args):
        """Fetch single value."""
        async with self.acquire() as conn:
            return await conn.fetchval(query, *args)
    
    async def _run_migrations(self):
        """Run database migrations."""
        async with self.acquire() as conn:
            # Create migrations table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version INTEGER PRIMARY KEY,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Get applied migrations
            applied = await conn.fetch(
                "SELECT version FROM schema_migrations"
            )
            applied_versions = {row['version'] for row in applied}
            
            # Apply pending migrations
            migrations = self._get_migrations()
            for version, migration in migrations:
                if version not in applied_versions:
                    await conn.execute(migration)
                    await conn.execute(
                        "INSERT INTO schema_migrations (version) VALUES ($1)",
                        version
                    )
    
    def _get_migrations(self):
        """Get migration definitions."""
        return [
            (1, """
                CREATE TABLE IF NOT EXISTS sessions (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    ended_at TIMESTAMP,
                    metadata JSONB
                )
            """),
            (2, """
                CREATE TABLE IF NOT EXISTS tickets (
                    id SERIAL PRIMARY KEY,
                    session_id UUID REFERENCES sessions(id),
                    type VARCHAR(50),
                    title TEXT,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """),
        ]
    
    def _sanitize_dsn(self, dsn: str) -> str:
        """Remove password from DSN for logging."""
        # Simple regex to hide password
        import re
        return re.sub(r':([^@]+)@', ':***@', dsn)
```

## Event Service

```python
from typing import Callable, List
from collections import defaultdict
import asyncio

class EventService(BaseService):
    """Event bus service for pub/sub communication."""
    
    def __init__(self):
        super().__init__()
        self._subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self._async_subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self._event_queue = asyncio.Queue()
        self._processor_task = None
    
    async def start(self):
        """Start event service."""
        self._initialized = True
        self._processor_task = asyncio.create_task(self._process_events())
    
    async def stop(self):
        """Stop event service."""
        self._initialized = False
        if self._processor_task:
            self._processor_task.cancel()
            try:
                await self._processor_task
            except asyncio.CancelledError:
                pass
    
    def health_check(self) -> Dict[str, Any]:
        """Check event service health."""
        return {
            "status": "healthy" if self._initialized else "stopped",
            "queue_size": self._event_queue.qsize(),
            "topics": list(self._subscribers.keys()),
            "subscriber_count": sum(
                len(subs) for subs in self._subscribers.values()
            )
        }
    
    def subscribe(self, topic: str, handler: Callable):
        """Subscribe to a topic."""
        if asyncio.iscoroutinefunction(handler):
            self._async_subscribers[topic].append(handler)
        else:
            self._subscribers[topic].append(handler)
    
    def unsubscribe(self, topic: str, handler: Callable):
        """Unsubscribe from a topic."""
        if handler in self._subscribers[topic]:
            self._subscribers[topic].remove(handler)
        if handler in self._async_subscribers[topic]:
            self._async_subscribers[topic].remove(handler)
    
    async def publish(self, topic: str, data: Any):
        """Publish event to topic."""
        if not self._initialized:
            raise RuntimeError("Event service not started")
        
        event = {
            "topic": topic,
            "data": data,
            "timestamp": time.time()
        }
        await self._event_queue.put(event)
    
    def publish_sync(self, topic: str, data: Any):
        """Synchronously publish event (for non-async contexts)."""
        asyncio.create_task(self.publish(topic, data))
    
    async def _process_events(self):
        """Process events from queue."""
        while self._initialized:
            try:
                # Get event with timeout to allow cancellation
                event = await asyncio.wait_for(
                    self._event_queue.get(),
                    timeout=1.0
                )
                
                topic = event["topic"]
                data = event["data"]
                
                # Call sync handlers
                for handler in self._subscribers[topic]:
                    try:
                        handler(topic, data)
                    except Exception as e:
                        print(f"Handler error: {e}")
                
                # Call async handlers
                tasks = []
                for handler in self._async_subscribers[topic]:
                    tasks.append(handler(topic, data))
                
                if tasks:
                    results = await asyncio.gather(
                        *tasks, return_exceptions=True
                    )
                    for result in results:
                        if isinstance(result, Exception):
                            print(f"Async handler error: {result}")
                            
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Event processing error: {e}")
```

## Background Task Service

```python
from dataclasses import dataclass
from enum import Enum
import uuid

class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class Task:
    id: str
    name: str
    func: Callable
    args: tuple
    kwargs: dict
    status: TaskStatus
    result: Any = None
    error: str = None
    created_at: float = None
    started_at: float = None
    completed_at: float = None

class BackgroundTaskService(BaseService):
    """Service for managing background tasks."""
    
    def __init__(self, max_workers: int = 5):
        super().__init__()
        self.max_workers = max_workers
        self._tasks: Dict[str, Task] = {}
        self._task_queue = asyncio.Queue()
        self._workers = []
    
    async def start(self):
        """Start background task service."""
        self._initialized = True
        
        # Start worker tasks
        for i in range(self.max_workers):
            worker = asyncio.create_task(self._worker(i))
            self._workers.append(worker)
    
    async def stop(self):
        """Stop background task service."""
        self._initialized = False
        
        # Cancel all workers
        for worker in self._workers:
            worker.cancel()
        
        # Wait for workers to finish
        await asyncio.gather(*self._workers, return_exceptions=True)
    
    def health_check(self) -> Dict[str, Any]:
        """Check service health."""
        task_stats = {
            status.value: 0 for status in TaskStatus
        }
        for task in self._tasks.values():
            task_stats[task.status.value] += 1
        
        return {
            "status": "healthy" if self._initialized else "stopped",
            "workers": len(self._workers),
            "queue_size": self._task_queue.qsize(),
            "tasks": task_stats
        }
    
    async def submit_task(
        self,
        func: Callable,
        *args,
        name: str = None,
        **kwargs
    ) -> str:
        """Submit a task for background execution."""
        task_id = str(uuid.uuid4())
        
        task = Task(
            id=task_id,
            name=name or func.__name__,
            func=func,
            args=args,
            kwargs=kwargs,
            status=TaskStatus.PENDING,
            created_at=time.time()
        )
        
        self._tasks[task_id] = task
        await self._task_queue.put(task)
        
        return task_id
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """Get task by ID."""
        return self._tasks.get(task_id)
    
    def list_tasks(
        self,
        status: Optional[TaskStatus] = None,
        limit: int = 100
    ) -> List[Task]:
        """List tasks with optional filtering."""
        tasks = list(self._tasks.values())
        
        if status:
            tasks = [t for t in tasks if t.status == status]
        
        # Sort by created time
        tasks.sort(key=lambda t: t.created_at, reverse=True)
        
        return tasks[:limit]
    
    async def wait_for_task(
        self,
        task_id: str,
        timeout: Optional[float] = None
    ) -> Task:
        """Wait for a task to complete."""
        start_time = time.time()
        
        while True:
            task = self.get_task(task_id)
            if not task:
                raise ValueError(f"Task {task_id} not found")
            
            if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
                return task
            
            if timeout and (time.time() - start_time) > timeout:
                raise asyncio.TimeoutError(f"Task {task_id} timed out")
            
            await asyncio.sleep(0.1)
    
    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a pending task."""
        task = self.get_task(task_id)
        if not task:
            return False
        
        if task.status == TaskStatus.PENDING:
            task.status = TaskStatus.CANCELLED
            return True
        
        return False
    
    async def _worker(self, worker_id: int):
        """Worker coroutine for processing tasks."""
        while self._initialized:
            try:
                # Get task with timeout
                task = await asyncio.wait_for(
                    self._task_queue.get(),
                    timeout=1.0
                )
                
                # Skip cancelled tasks
                if task.status == TaskStatus.CANCELLED:
                    continue
                
                # Execute task
                task.status = TaskStatus.RUNNING
                task.started_at = time.time()
                
                try:
                    if asyncio.iscoroutinefunction(task.func):
                        result = await task.func(*task.args, **task.kwargs)
                    else:
                        result = task.func(*task.args, **task.kwargs)
                    
                    task.result = result
                    task.status = TaskStatus.COMPLETED
                    
                except Exception as e:
                    task.error = str(e)
                    task.status = TaskStatus.FAILED
                
                finally:
                    task.completed_at = time.time()
                    
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Worker {worker_id} error: {e}")
```

## Integration Service Example

```python
import aiohttp
from urllib.parse import urljoin

class GitHubIntegrationService(BaseService):
    """Service for GitHub integration."""
    
    def __init__(self, token: str, org: str, repo: str):
        super().__init__()
        self.token = token
        self.org = org
        self.repo = repo
        self.base_url = "https://api.github.com"
        self._session = None
    
    async def start(self):
        """Start GitHub service."""
        self._session = aiohttp.ClientSession(
            headers={
                "Authorization": f"token {self.token}",
                "Accept": "application/vnd.github.v3+json"
            }
        )
        self._initialized = True
    
    async def stop(self):
        """Stop GitHub service."""
        if self._session:
            await self._session.close()
        self._initialized = False
    
    def health_check(self) -> Dict[str, Any]:
        """Check service health."""
        return {
            "status": "healthy" if self._initialized else "stopped",
            "org": self.org,
            "repo": self.repo
        }
    
    async def create_issue(
        self,
        title: str,
        body: str,
        labels: List[str] = None,
        assignees: List[str] = None
    ) -> Dict[str, Any]:
        """Create a GitHub issue."""
        url = f"/repos/{self.org}/{self.repo}/issues"
        
        data = {
            "title": title,
            "body": body
        }
        
        if labels:
            data["labels"] = labels
        if assignees:
            data["assignees"] = assignees
        
        async with self._session.post(
            urljoin(self.base_url, url),
            json=data
        ) as resp:
            resp.raise_for_status()
            return await resp.json()
    
    async def create_pull_request(
        self,
        title: str,
        body: str,
        head: str,
        base: str = "main"
    ) -> Dict[str, Any]:
        """Create a pull request."""
        url = f"/repos/{self.org}/{self.repo}/pulls"
        
        data = {
            "title": title,
            "body": body,
            "head": head,
            "base": base
        }
        
        async with self._session.post(
            urljoin(self.base_url, url),
            json=data
        ) as resp:
            resp.raise_for_status()
            return await resp.json()
    
    async def get_workflow_runs(
        self,
        workflow_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get workflow runs."""
        url = f"/repos/{self.org}/{self.repo}/actions/runs"
        
        params = {"per_page": limit}
        if workflow_id:
            params["workflow_id"] = workflow_id
        if status:
            params["status"] = status
        
        async with self._session.get(
            urljoin(self.base_url, url),
            params=params
        ) as resp:
            resp.raise_for_status()
            data = await resp.json()
            return data["workflow_runs"]
```

## Service Manager

Manage multiple services:

```python
class ServiceManager:
    """Manage multiple services."""
    
    def __init__(self):
        self.services: Dict[str, BaseService] = {}
        self._started = False
    
    def register(self, name: str, service: BaseService):
        """Register a service."""
        if self._started:
            raise RuntimeError("Cannot register service after start")
        self.services[name] = service
    
    async def start_all(self):
        """Start all services."""
        for name, service in self.services.items():
            try:
                await service.start()
                print(f"Started service: {name}")
            except Exception as e:
                print(f"Failed to start {name}: {e}")
                # Stop already started services
                await self.stop_all()
                raise
        self._started = True
    
    async def stop_all(self):
        """Stop all services."""
        for name, service in reversed(list(self.services.items())):
            try:
                await service.stop()
                print(f"Stopped service: {name}")
            except Exception as e:
                print(f"Error stopping {name}: {e}")
        self._started = False
    
    def get_service(self, name: str) -> Optional[BaseService]:
        """Get service by name."""
        return self.services.get(name)
    
    def health_check_all(self) -> Dict[str, Dict[str, Any]]:
        """Check health of all services."""
        return {
            name: service.health_check()
            for name, service in self.services.items()
        }

# Usage
async def main():
    manager = ServiceManager()
    
    # Register services
    manager.register("cache", CacheService())
    manager.register("database", DatabaseService("postgresql://..."))
    manager.register("events", EventService())
    manager.register("tasks", BackgroundTaskService())
    manager.register("github", GitHubIntegrationService(
        token="...",
        org="myorg",
        repo="myrepo"
    ))
    
    # Start all
    await manager.start_all()
    
    try:
        # Use services
        cache = manager.get_service("cache")
        await cache.set("key", "value")
        
        events = manager.get_service("events")
        await events.publish("user.login", {"user_id": 123})
        
        # Check health
        health = manager.health_check_all()
        print(json.dumps(health, indent=2))
        
    finally:
        # Stop all
        await manager.stop_all()
```

## Testing Services

```python
import pytest

@pytest.mark.asyncio
async def test_cache_service():
    service = CacheService(max_size=10, default_ttl=60)
    
    await service.start()
    try:
        # Test set/get
        await service.set("key1", "value1")
        value = await service.get("key1")
        assert value == "value1"
        
        # Test expiration
        await service.set("key2", "value2", ttl=0)
        await asyncio.sleep(0.1)
        value = await service.get("key2")
        assert value is None
        
        # Test LRU eviction
        for i in range(12):
            await service.set(f"key{i}", f"value{i}")
        
        # First keys should be evicted
        assert await service.get("key0") is None
        assert await service.get("key11") == "value11"
        
    finally:
        await service.stop()

@pytest.mark.asyncio
async def test_event_service():
    service = EventService()
    await service.start()
    
    received = []
    
    async def handler(topic, data):
        received.append((topic, data))
    
    service.subscribe("test.event", handler)
    
    try:
        await service.publish("test.event", {"message": "hello"})
        await asyncio.sleep(0.1)  # Allow processing
        
        assert len(received) == 1
        assert received[0] == ("test.event", {"message": "hello"})
        
    finally:
        await service.stop()
```

## Best Practices

1. **Lifecycle Management**: Always implement proper start/stop methods
2. **Health Checks**: Provide meaningful health check information
3. **Error Handling**: Handle errors gracefully without crashing
4. **Configuration**: Make services configurable
5. **Logging**: Use appropriate logging levels
6. **Testing**: Write comprehensive tests
7. **Documentation**: Document service API and usage
8. **Resource Cleanup**: Ensure resources are properly released
9. **Async Safety**: Use proper locking for shared state
10. **Monitoring**: Include metrics and monitoring hooks