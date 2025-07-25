# Dependency Injection in Claude MPM

This guide explains the dependency injection (DI) system implemented in Claude MPM, including patterns, best practices, and examples.

## Overview

Claude MPM uses a lightweight dependency injection container to:
- Reduce coupling between components
- Improve testability
- Simplify configuration management
- Enable better service lifecycle management

## Core Components

### 1. DI Container (`core/container.py`)

The heart of the DI system, providing:
- Service registration and resolution
- Lifetime management (singleton, transient)
- Circular dependency detection
- Factory support

```python
from claude_mpm.core.container import DIContainer, ServiceLifetime

# Create container
container = DIContainer()

# Register services
container.register_singleton(ILogger, ConsoleLogger)
container.register_transient(IRepository, UserRepository)

# Resolve services
logger = container.resolve(ILogger)
```

### 2. Service Registry (`core/service_registry.py`)

Centralized service management:
- Automatic registration of core services
- Service discovery
- Health monitoring
- Lifecycle management

```python
from claude_mpm.core.service_registry import get_service_registry

# Get registry
registry = get_service_registry()

# Get a service
ticket_manager = registry.get_service("ticket_manager")
```

### 3. Injectable Service Base (`core/injectable_service.py`)

Enhanced base class for services with DI support:
- Automatic dependency injection
- Property injection
- Service locator pattern (optional)

```python
from claude_mpm.core.injectable_service import InjectableService
from claude_mpm.core.config import Config

class MyService(InjectableService):
    # Dependencies are injected automatically
    config: Config
    logger: ILogger
    
    async def _initialize(self):
        # Use injected dependencies
        self.logger.info(f"Service initialized with {self.config}")
```

## Patterns and Best Practices

### 1. Constructor Injection

Preferred method for required dependencies:

```python
class EmailService:
    def __init__(self, smtp_client: ISmtpClient, config: Config):
        self.smtp_client = smtp_client
        self.config = config
```

### 2. Interface-Based Design

Use interfaces (abstract base classes) for better testability:

```python
from abc import ABC, abstractmethod

class INotificationService(ABC):
    @abstractmethod
    def send(self, message: str) -> bool:
        pass

class EmailNotificationService(INotificationService):
    def __init__(self, email_service: EmailService):
        self.email_service = email_service
        
    def send(self, message: str) -> bool:
        return self.email_service.send_email(message)
```

### 3. Factory Pattern

For complex object creation:

```python
class DatabaseFactory(ServiceFactory):
    def create(self, container: DIContainer, **kwargs):
        config = container.resolve(Config)
        db_type = config.get('database.type', 'sqlite')
        
        if db_type == 'sqlite':
            return SqliteDatabase(config.get('database.path'))
        elif db_type == 'postgres':
            return PostgresDatabase(
                host=config.get('database.host'),
                port=config.get('database.port')
            )
```

### 4. Service Lifetime Management

Choose appropriate lifetimes:

```python
# Singleton - one instance per container
container.register_singleton(ICache, MemoryCache)

# Transient - new instance per request
container.register_transient(IHttpClient, HttpClient)

# Future: Scoped - one instance per scope
# container.register_scoped(IDbContext, DbContext)
```

## Testing with DI

### 1. Mock Dependencies

Easy to test services in isolation:

```python
def test_user_service():
    # Create mocks
    mock_repo = Mock(spec=IUserRepository)
    mock_logger = Mock(spec=ILogger)
    
    # Inject mocks
    service = UserService(
        repository=mock_repo,
        logger=mock_logger
    )
    
    # Test behavior
    service.create_user("test@example.com")
    
    # Verify interactions
    mock_repo.save.assert_called_once()
```

### 2. Test Containers

Create test-specific containers:

```python
def create_test_container():
    container = DIContainer()
    
    # Register test implementations
    container.register_singleton(IDatabase, InMemoryDatabase)
    container.register_singleton(ICache, MockCache)
    
    return container
```

### 3. Partial Mocking

Mix real and mock dependencies:

```python
def test_with_real_config():
    # Real config
    config = Config({'test': 'value'})
    
    # Mock other dependencies
    mock_db = Mock(spec=IDatabase)
    
    # Create service with mixed dependencies
    service = DataService(config=config, database=mock_db)
```

## Migration Guide

### Converting Existing Services

1. **Identify Dependencies**
   ```python
   # Before
   class OldService:
       def __init__(self):
           self.config = Config()
           self.logger = get_logger()
   ```

2. **Extract Interfaces**
   ```python
   class ILogger(ABC):
       @abstractmethod
       def log(self, message: str): pass
   ```

3. **Use Constructor Injection**
   ```python
   # After
   class NewService:
       def __init__(self, config: Config, logger: ILogger):
           self.config = config
           self.logger = logger
   ```

4. **Register with Container**
   ```python
   container.register_singleton(NewService)
   ```

## Advanced Topics

### 1. Conditional Registration

Register services based on configuration:

```python
if config.get('features.caching_enabled'):
    container.register_singleton(ICache, RedisCache)
else:
    container.register_singleton(ICache, NoOpCache)
```

### 2. Decorator-Based Injection

Future enhancement for cleaner syntax:

```python
@injectable
class MyService:
    @inject
    def __init__(self, config: Config, logger: ILogger):
        self.config = config
        self.logger = logger
```

### 3. Module Registration

Group related services:

```python
class DatabaseModule:
    def register(self, container: DIContainer):
        container.register_singleton(IDatabase, PostgresDatabase)
        container.register_transient(IDbContext, DbContext)
        container.register_singleton(IMigrationRunner, MigrationRunner)
```

## Common Pitfalls

### 1. Service Locator Anti-Pattern

Avoid using the container as a service locator:

```python
# Bad - hides dependencies
class BadService:
    def __init__(self, container: DIContainer):
        self.container = container
        
    def do_work(self):
        db = self.container.resolve(IDatabase)  # Hidden dependency

# Good - explicit dependencies
class GoodService:
    def __init__(self, database: IDatabase):
        self.database = database
```

### 2. Circular Dependencies

Design to avoid circular dependencies:

```python
# Bad - circular dependency
class UserService:
    def __init__(self, order_service: OrderService): ...

class OrderService:
    def __init__(self, user_service: UserService): ...

# Good - use events or mediator
class UserService:
    def __init__(self, event_bus: IEventBus): ...

class OrderService:
    def __init__(self, event_bus: IEventBus): ...
```

### 3. Over-Engineering

Don't create interfaces for everything:

```python
# Unnecessary interface for simple value object
class IConfiguration(ABC):  # Probably overkill
    @abstractmethod
    def get(self, key: str): pass

# Better - use concrete class for simple cases
class Configuration:
    def get(self, key: str): ...
```

## Performance Considerations

1. **Singleton Performance**: Singletons are cached, providing fast access
2. **Transient Overhead**: Creating new instances has minimal overhead
3. **Lazy Loading**: Services are created only when first requested
4. **Container Overhead**: Resolution is O(1) for registered services

## Future Enhancements

1. **Scoped Lifetimes**: For request-scoped services
2. **Auto-Registration**: Scan and register services automatically
3. **Configuration Binding**: Bind configuration sections to services
4. **Interceptors**: AOP-style cross-cutting concerns
5. **Module System**: Better organization of related services