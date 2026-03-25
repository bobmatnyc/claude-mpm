---
name: mypy
description: mypy - Static type checker for Python with gradual typing, strict mode, Protocol support, and framework integration
version: 1.0.0
category: toolchain
author: Claude MPM Team
license: MIT
progressive_disclosure:
  entry_point:
    summary: "Static type checker for Python with gradual typing and strict mode"
    when_to_use: "Adding type safety to Python projects, using type hints in FastAPI/Django, enforcing type checking in CI/CD, refactoring to add type annotations"
    quick_start: "1. pip install mypy 2. Add type hints to your code 3. mypy your_module.py 4. Create mypy.ini for configuration 5. Use --strict for maximum safety"
context_limit: 700
tags:
  - mypy
  - type-checking
  - type-hints
  - static-analysis
  - python
  - fastapi
  - django
requires_tools: []
---

# mypy - Static Type Checking for Python

## Overview

mypy is the standard static type checker for Python, enabling gradual typing with type hints (PEP 484) and comprehensive type safety. It catches type errors before runtime, improves code documentation, and enhances IDE support while maintaining Python's dynamic nature through incremental adoption.

**Key Features**:
- Gradual typing: Add types incrementally to existing code
- Strict mode: Maximum type safety with --strict flag
- Type inference: Automatically infer types from context
- Protocol support: Structural typing (duck typing with types)
- Generic types: TypeVar, Generic, and advanced type patterns
- Framework integration: FastAPI, Django, Pydantic compatibility
- Plugin system: Extend type checking for libraries
- Incremental checking: Fast type checking on large codebases

**Installation**:
```bash
# Basic mypy
pip install mypy

# With common type stubs
pip install mypy types-requests types-PyYAML types-redis

# For FastAPI projects
pip install mypy pydantic

# For Django projects
pip install mypy django-stubs

# Development setup
pip install mypy pre-commit
```

## Type Annotation Basics

### 1. Variable Type Hints

```python
# Basic types
name: str = "Alice"
age: int = 30
height: float = 5.9
is_active: bool = True

# Type inference (mypy infers types)
count = 10  # mypy infers: int
message = "Hello"  # mypy infers: str

# Multiple types with Union
from typing import Union

user_id: Union[int, str] = 123  # Can be int OR str
result: Union[int, None] = None  # Nullable int

# Optional (shorthand for Union[T, None])
from typing import Optional

user_email: Optional[str] = None  # Can be str or None
```

### 2. Function Type Hints

```python
# Basic function typing
def greet(name: str) -> str:
    return f"Hello, {name}"

# Multiple parameters
def add(a: int, b: int) -> int:
    return a + b

# Optional parameters with defaults
def create_user(name: str, age: int = 18) -> dict:
    return {"name": name, "age": age}

# No return value
def log_message(message: str) -> None:
    print(message)

# Functions that never return
from typing import NoReturn

def raise_error() -> NoReturn:
    raise ValueError("Always raises")
```

### 3. Collection Type Hints

```python
from typing import List, Dict, Set, Tuple

# List with element type
numbers: List[int] = [1, 2, 3, 4]
names: List[str] = ["Alice", "Bob", "Charlie"]

# Dict with key and value types
user_ages: Dict[str, int] = {"Alice": 30, "Bob": 25}
config: Dict[str, Union[str, int]] = {"host": "localhost", "port": 8000}

# Set with element type
unique_ids: Set[int] = {1, 2, 3}

# Tuple with fixed types
coordinate: Tuple[float, float] = (10.5, 20.3)
user_record: Tuple[int, str, bool] = (1, "Alice", True)

# Variable-length tuple
numbers: Tuple[int, ...] = (1, 2, 3, 4, 5)

# Modern syntax (Python 3.9+)
numbers: list[int] = [1, 2, 3]
user_ages: dict[str, int] = {"Alice": 30}
```

### 4. Class Type Hints

```python
class User:
    # Class attributes
    name: str
    age: int
    email: Optional[str]

    def __init__(self, name: str, age: int, email: Optional[str] = None) -> None:
        self.name = name
        self.age = age
        self.email = email

    def get_info(self) -> Dict[str, Union[str, int]]:
        return {
            "name": self.name,
            "age": self.age,
            "email": self.email or "N/A"
        }

    @classmethod
    def from_dict(cls, data: Dict[str, any]) -> "User":
        return cls(
            name=data["name"],
            age=data["age"],
            email=data.get("email")
        )
```

## Advanced Type Hints

### 1. Literal Types

```python
from typing import Literal

# Restrict to specific values
def set_log_level(level: Literal["debug", "info", "warning", "error"]) -> None:
    print(f"Log level: {level}")

# Valid
set_log_level("debug")
set_log_level("error")

# Type error: Argument 1 has incompatible type "verbose"
set_log_level("verbose")

# Multiple literals
Status = Literal["pending", "approved", "rejected"]

def update_status(status: Status) -> None:
    pass
```

### 2. Type Aliases

```python
from typing import Dict, List, Union

# Simple alias
UserId = int
UserName = str

def get_user(user_id: UserId) -> UserName:
    return f"User {user_id}"

# Complex aliases
JSON = Union[Dict[str, "JSON"], List["JSON"], str, int, float, bool, None]
Headers = Dict[str, str]
QueryParams = Dict[str, Union[str, int, List[str]]]

def make_request(
    url: str,
    headers: Headers,
    params: QueryParams
) -> JSON:
    pass

# NewType for distinct types
from typing import NewType

UserId = NewType("UserId", int)
ProductId = NewType("ProductId", int)

def get_user(user_id: UserId) -> str:
    return f"User {user_id}"

user = UserId(123)  # Valid
product = ProductId(456)

get_user(user)  # Valid
get_user(product)  # Type error: ProductId not compatible with UserId
```

### 3. Generics and TypeVar

```python
from typing import TypeVar, Generic, List

# TypeVar for generic functions
T = TypeVar("T")

def first_element(items: List[T]) -> T:
    return items[0]

# Type inference
num = first_element([1, 2, 3])  # mypy infers: int
name = first_element(["Alice", "Bob"])  # mypy infers: str

# Bounded TypeVar
from typing import Union

NumericType = TypeVar("NumericType", int, float)

def add_numbers(a: NumericType, b: NumericType) -> NumericType:
    return a + b

# Generic classes
class Stack(Generic[T]):
    def __init__(self) -> None:
        self._items: List[T] = []

    def push(self, item: T) -> None:
        self._items.append(item)

    def pop(self) -> T:
        return self._items.pop()

    def is_empty(self) -> bool:
        return len(self._items) == 0

# Usage with type inference
int_stack: Stack[int] = Stack()
int_stack.push(42)
int_stack.push("hello")  # Type error: Expected int, got str

str_stack: Stack[str] = Stack()
str_stack.push("hello")  # Valid
```

### 4. Protocol (Structural Typing)

```python
from typing import Protocol

# Define protocol (interface)
class Drawable(Protocol):
    def draw(self) -> str:
        ...

# Any class with draw() method matches
class Circle:
    def draw(self) -> str:
        return "Drawing circle"

class Square:
    def draw(self) -> str:
        return "Drawing square"

# Function accepts any Drawable
def render(obj: Drawable) -> str:
    return obj.draw()

# Both work (duck typing with types)
circle = Circle()
square = Square()
render(circle)  # Valid
render(square)  # Valid

# Runtime checkable protocols
from typing import runtime_checkable

@runtime_checkable
class Closeable(Protocol):
    def close(self) -> None:
        ...

class File:
    def close(self) -> None:
        pass

# Runtime check
f = File()
isinstance(f, Closeable)  # True
```

### 5. Callable Types

```python
from typing import Callable

# Function that takes another function
def apply_twice(func: Callable[[int], int], value: int) -> int:
    return func(func(value))

def double(x: int) -> int:
    return x * 2

result = apply_twice(double, 5)  # Returns 20

# Generic callable
from typing import TypeVar

T = TypeVar("T")
R = TypeVar("R")

def map_values(
    func: Callable[[T], R],
    values: List[T]
) -> List[R]:
    return [func(v) for v in values]

# Callable with multiple arguments
Validator = Callable[[str, int], bool]

def validate_user(name: str, age: int) -> bool:
    return len(name) > 0 and age >= 0

validator: Validator = validate_user
```

## mypy Configuration

### 1. mypy.ini Configuration

```ini
# mypy.ini
[mypy]
# Python version
python_version = 3.11

# Import discovery
files = src,tests
exclude = build,dist,venv

# Type checking strictness
disallow_untyped_defs = True
disallow_any_unimported = False
no_implicit_optional = True
warn_return_any = True
warn_unused_ignores = True
warn_redundant_casts = True

# Error reporting
show_error_codes = True
show_column_numbers = True
pretty = True

# Incremental type checking
incremental = True
cache_dir = .mypy_cache

# Per-module configuration
[mypy-tests.*]
disallow_untyped_defs = False

[mypy-migrations.*]
ignore_errors = True

# Third-party libraries without stubs
[mypy-redis.*]
ignore_missing_imports = True

[mypy-celery.*]
ignore_missing_imports = True
```

### 2. pyproject.toml Configuration

```toml
# pyproject.toml
[tool.mypy]
python_version = "3.11"
files = ["src", "tests"]
exclude = ["build", "dist", "venv"]

# Strictness
disallow_untyped_defs = true
disallow_any_unimported = false
no_implicit_optional = true
warn_return_any = true
warn_unused_ignores = true
warn_redundant_casts = true
strict_equality = true
strict_concatenate = true

# Error reporting
show_error_codes = true
show_column_numbers = true
pretty = true
color_output = true

# Incremental
incremental = true
cache_dir = ".mypy_cache"

# Per-module overrides
[[tool.mypy.overrides]]
module = "tests.*"
disallow_untyped_defs = false

[[tool.mypy.overrides]]
module = ["redis.*", "celery.*"]
ignore_missing_imports = true
```

### 3. Strict Mode

```bash
# Enable all strict checks
mypy --strict src/

# Strict mode equivalent flags
mypy \
  --disallow-any-unimported \
  --disallow-any-expr \
  --disallow-any-decorated \
  --disallow-any-explicit \
  --disallow-any-generics \
  --disallow-subclassing-any \
  --disallow-untyped-calls \
  --disallow-untyped-defs \
  --disallow-incomplete-defs \
  --check-untyped-defs \
  --disallow-untyped-decorators \
  --no-implicit-optional \
  --warn-redundant-casts \
  --warn-unused-ignores \
  --warn-return-any \
  --warn-unreachable \
  --strict-equality \
  src/
```

```ini
# mypy.ini strict configuration
[mypy]
strict = True

# Relax specific checks if needed
disallow_any_expr = False  # Too strict for most projects
disallow_any_explicit = False  # Allow explicit Any
```

## Incremental Adoption Strategies

### 1. Start with Entry Points

```python
# Start typing from main.py (top-level)
# main.py
from typing import Optional
from app.services import UserService

def main(config_path: Optional[str] = None) -> None:
    """Application entry point."""
    service = UserService()
    service.run()

if __name__ == "__main__":
    main()
```

```bash
# Check only main.py initially
mypy main.py

# Gradually expand scope
mypy main.py app/services.py
mypy src/
```

### 2. Per-Module Strict Mode

```ini
# mypy.ini - Gradually enable strict checking
[mypy]
# Lenient global defaults
ignore_missing_imports = True
disallow_untyped_defs = False

# Strict for new modules
[mypy-app.services.user_service]
disallow_untyped_defs = True
warn_return_any = True

[mypy-app.api.*]
disallow_untyped_defs = True
no_implicit_optional = True

# Still lenient for legacy code
[mypy-app.legacy.*]
ignore_errors = True
```

### 3. Use # type: ignore Strategically

```python
# Suppress specific errors during migration
import legacy_module  # type: ignore[import]

def process_data(data):  # type: ignore[no-untyped-def]
    # TODO: Add type hints
    return data.transform()

# Ignore specific error codes
user_dict = get_user_dict()
user_id = user_dict["id"]  # type: ignore[index]

# Ignore entire line (use sparingly)
result = external_api.call()  # type: ignore
```

### 4. Reveal Types During Development

```python
from typing import reveal_type

def process_user(user_id: int):
    user = get_user(user_id)
    reveal_type(user)  # mypy will show inferred type

    name = user.name
    reveal_type(name)  # mypy will show: str
```

## FastAPI Integration

### 1. FastAPI with Type Hints

```python
# main.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI()

# Pydantic models (auto-validated)
class User(BaseModel):
    id: int
    name: str
    email: str
    age: Optional[int] = None

class UserCreate(BaseModel):
    name: str
    email: str
    age: Optional[int] = None

# Type-safe endpoints
@app.get("/")
def read_root() -> dict[str, str]:
    return {"message": "Hello World"}

@app.get("/users/{user_id}")
def read_user(user_id: int) -> User:
    if user_id == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return User(id=user_id, name=f"User {user_id}", email="user@example.com")

@app.get("/users")
def list_users(skip: int = 0, limit: int = 10) -> List[User]:
    users = [
        User(id=i, name=f"User {i}", email=f"user{i}@example.com")
        for i in range(skip, skip + limit)
    ]
    return users

@app.post("/users")
def create_user(user: UserCreate) -> User:
    # Pydantic ensures type safety
    return User(id=1, name=user.name, email=user.email, age=user.age)
```

### 2. Async FastAPI Type Checking

```python
from typing import List, Optional
from fastapi import FastAPI, Depends
from sqlalchemy.ext.asyncio import AsyncSession

app = FastAPI()

# Async dependency
async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session

# Async endpoints with types
@app.get("/users/{user_id}")
async def read_user(
    user_id: int,
    db: AsyncSession = Depends(get_db)
) -> User:
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@app.get("/users")
async def list_users(
    skip: int = 0,
    limit: int = 10,
    db: AsyncSession = Depends(get_db)
) -> List[User]:
    result = await db.execute(
        select(User).offset(skip).limit(limit)
    )
    return result.scalars().all()
```

### 3. FastAPI Dependency Injection Types

```python
from typing import Annotated, Optional
from fastapi import FastAPI, Depends, Header, HTTPException

app = FastAPI()

# Typed dependencies
async def get_current_user(
    authorization: Annotated[Optional[str], Header()] = None
) -> User:
    if authorization is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    # Verify token and return user
    return User(id=1, name="Current User", email="user@example.com")

# Use dependency with type annotation
@app.get("/me")
async def read_current_user(
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    return current_user

# Complex dependency chain
class UserService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_user(self, user_id: int) -> Optional[User]:
        return await self.db.get(User, user_id)

def get_user_service(
    db: Annotated[AsyncSession, Depends(get_db)]
) -> UserService:
    return UserService(db)

@app.get("/users/{user_id}")
async def get_user_endpoint(
    user_id: int,
    service: Annotated[UserService, Depends(get_user_service)]
) -> User:
    user = await service.get_user(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user
```

## Django Integration

### 1. Django with django-stubs

```bash
# Install django-stubs
pip install django-stubs mypy

# Generate mypy configuration
python -m mypy --install-types
```

```ini
# mypy.ini
[mypy]
plugins = mypy_django_plugin.main

[mypy.plugins.django-stubs]
django_settings_module = "myproject.settings"
```

### 2. Django Models with Type Hints

```python
# models.py
from django.db import models
from typing import Optional

class User(models.Model):
    email: models.EmailField = models.EmailField(unique=True)
    name: models.CharField = models.CharField(max_length=100)
    age: models.IntegerField = models.IntegerField(null=True, blank=True)
    is_active: models.BooleanField = models.BooleanField(default=True)
    created_at: models.DateTimeField = models.DateTimeField(auto_now_add=True)

    def get_display_name(self) -> str:
        return self.name or self.email

    @classmethod
    def get_active_users(cls) -> models.QuerySet["User"]:
        return cls.objects.filter(is_active=True)
```

### 3. Django Views with Type Hints

```python
# views.py
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from typing import Dict, Any
from .models import User

def user_detail(request: HttpRequest, user_id: int) -> JsonResponse:
    user: User = get_object_or_404(User, pk=user_id)
    data: Dict[str, Any] = {
        "id": user.id,
        "name": user.name,
        "email": user.email,
    }
    return JsonResponse(data)

def user_list(request: HttpRequest) -> JsonResponse:
    users = User.get_active_users()
    data = {
        "users": list(users.values("id", "name", "email"))
    }
    return JsonResponse(data)
```

## Type Stubs and Third-Party Libraries

### 1. Installing Type Stubs

```bash
# Install stubs for popular libraries
pip install types-requests
pip install types-PyYAML
pip install types-redis
pip install types-boto3

# Search for available stubs
pip search types-

# Auto-install missing stubs
mypy --install-types
```

### 2. Creating Custom Stubs

```python
# stubs/external_lib.pyi
from typing import Optional, List

class Client:
    def __init__(self, api_key: str) -> None: ...

    def get_user(self, user_id: int) -> Optional[dict]: ...

    def list_users(self, limit: int = 10) -> List[dict]: ...

def connect(host: str, port: int) -> Client: ...
```

```ini
# mypy.ini
[mypy]
mypy_path = stubs
```

### 3. Ignoring Missing Imports

```ini
# mypy.ini
[mypy-external_lib.*]
ignore_missing_imports = True

# For multiple libraries
[mypy-celery.*,redis.*,boto3.*]
ignore_missing_imports = True
```

## CI/CD Integration

### 1. GitHub Actions

```yaml
# .github/workflows/type-check.yml
name: Type Check

on: [push, pull_request]

jobs:
  mypy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install mypy
          pip install -r requirements.txt
          pip install types-requests types-PyYAML

      - name: Run mypy
        run: mypy src/

      - name: Run mypy strict on new code
        run: mypy --strict src/api/
```

### 2. Pre-commit Hook

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.8.0
    hooks:
      - id: mypy
        args: [--strict, --ignore-missing-imports]
        additional_dependencies:
          - types-requests
          - types-PyYAML
```

```bash
# Install pre-commit
pip install pre-commit
pre-commit install

# Run manually
pre-commit run mypy --all-files
```

### 3. Make Target

```makefile
# Makefile
.PHONY: typecheck
typecheck:
	mypy src/

.PHONY: typecheck-strict
typecheck-strict:
	mypy --strict src/

.PHONY: typecheck-report
typecheck-report:
	mypy src/ --html-report mypy-report
	@echo "Report: mypy-report/index.html"

.PHONY: ci
ci: typecheck test lint
```

## Common Patterns and Idioms

### 1. Overload for Multiple Signatures

```python
from typing import overload, Union

@overload
def process(data: str) -> str: ...

@overload
def process(data: int) -> int: ...

@overload
def process(data: list) -> list: ...

def process(data: Union[str, int, list]) -> Union[str, int, list]:
    """Process different data types."""
    if isinstance(data, str):
        return data.upper()
    elif isinstance(data, int):
        return data * 2
    else:
        return [x * 2 for x in data]

# mypy knows return types
result1: str = process("hello")  # Valid
result2: int = process(42)  # Valid
result3: str = process(42)  # Type error
```

### 2. TypedDict for Structured Dicts

```python
from typing import TypedDict, Optional

class UserDict(TypedDict):
    id: int
    name: str
    email: str
    age: Optional[int]

# Type-safe dict usage
def create_user(data: UserDict) -> UserDict:
    return {
        "id": 1,
        "name": data["name"],
        "email": data["email"],
        "age": data.get("age"),
    }

user: UserDict = {
    "id": 1,
    "name": "Alice",
    "email": "alice@example.com",
    "age": 30
}

# Type error: Missing required key "email"
invalid_user: UserDict = {
    "id": 1,
    "name": "Bob",
}
```

### 3. Final and Constant Values

```python
from typing import Final

# Constants that should never change
API_VERSION: Final = "v1"
MAX_RETRIES: Final[int] = 3

# Type error: Cannot assign to final name
API_VERSION = "v2"

# Final class (cannot be subclassed)
from typing import final

@final
class BaseConfig:
    pass

# Type error: Cannot inherit from final class
class AppConfig(BaseConfig):  # Error!
    pass
```

### 4. Self Type for Method Chaining

```python
from typing import Self  # Python 3.11+

class Builder:
    def __init__(self) -> None:
        self._value = 0

    def add(self, value: int) -> Self:
        self._value += value
        return self

    def multiply(self, value: int) -> Self:
        self._value *= value
        return self

    def build(self) -> int:
        return self._value

# Type-safe method chaining
result = Builder().add(5).multiply(2).add(3).build()
```

## mypy vs pyright Comparison

### Feature Comparison

| Feature | mypy | pyright |
|---------|------|---------|
| **Type Checker** | Official Python type checker | Microsoft's type checker |
| **Speed** | Slower on large codebases | Faster, incremental |
| **Strictness** | Configurable strict mode | Very strict by default |
| **IDE Integration** | Good (LSP support) | Excellent (Pylance in VS Code) |
| **Plugin System** | Yes (mypy plugins) | Limited |
| **Error Messages** | Clear, detailed | Very detailed, helpful |
| **Community** | Large, official | Growing, Microsoft-backed |
| **Type Inference** | Good | Excellent |
| **Configuration** | mypy.ini, pyproject.toml | pyrightconfig.json, pyproject.toml |

### When to Use mypy

```bash
# Use mypy for:
# - Official Python type checking standard
# - Plugin ecosystem (Django, SQLAlchemy, Pydantic)
# - Gradual typing with fine-grained control
# - Compatibility with existing mypy configurations
# - CI/CD pipelines (industry standard)
```

### When to Use pyright

```bash
# Use pyright for:
# - VS Code development (Pylance)
# - Faster type checking on large codebases
# - Stricter type checking by default
# - Better type inference
# - Real-time IDE feedback
```

### Using Both

```toml
# pyproject.toml - Configure both
[tool.mypy]
strict = true
files = ["src"]

[tool.pyright]
include = ["src"]
strict = ["src/api"]
reportMissingTypeStubs = false
```

```bash
# Run both in CI
mypy src/
pyright src/
```

## Local mypy Profiles (Your Repos)

Common patterns from your Python projects:

- **Strict default** (edgar, kuzu-memory, mcp-browser):
  `disallow_untyped_defs = true`, `check_untyped_defs = true`, `no_implicit_optional = true`, `warn_return_any = true`, `strict_equality = true`.
- **Relaxed profile** (mcp-ticketer): strict flags disabled temporarily with a `disable_error_code` list for patch releases.
- **Incremental adoption** (mcp-vector-search): `ignore_errors = true` while stabilizing types.
- **Missing imports**: `ignore_missing_imports = true` used in mcp-memory and mcp-ticketer.

Reference: see `pyproject.toml` in `edgar`, `kuzu-memory`, `mcp-vector-search`, and `mcp-ticketer`.

## Best Practices

### 1. Start with Key Modules

```python
# ✅ GOOD: Type critical business logic first
# services/user_service.py
from typing import Optional

class UserService:
    def get_user(self, user_id: int) -> Optional[User]:
        """Retrieve user by ID."""
        return self.db.query(User).get(user_id)

    def create_user(self, data: UserCreate) -> User:
        """Create new user."""
        user = User(**data.dict())
        self.db.add(user)
        self.db.commit()
        return user
```

### 2. Use Type Aliases for Readability

```python
# ✅ GOOD: Clear, reusable type aliases
from typing import Dict, List, Union

JSON = Union[Dict[str, "JSON"], List["JSON"], str, int, float, bool, None]
Headers = Dict[str, str]
UserId = int

def parse_response(data: JSON, headers: Headers) -> UserId:
    pass

# ❌ BAD: Complex inline types
def parse_response(
    data: Union[Dict[str, Union[...]], List[...], str, int, float, bool, None],
    headers: Dict[str, str]
) -> int:
    pass
```

### 3. Prefer Explicit Over Implicit

```python
# ✅ GOOD: Explicit types for public APIs
def get_user(user_id: int) -> Optional[User]:
    return db.query(User).get(user_id)

# ❌ ACCEPTABLE: Type inference for internal helpers
def _format_name(first, last):  # mypy infers str -> str
    return f"{first} {last}"
```

### 4. Use reveal_type for Debugging

```python
# During development, check inferred types
from typing import reveal_type

def process_data(data):
    result = transform(data)
    reveal_type(result)  # mypy: Revealed type is "int"
    return result * 2
```

### 5. Document Type Ignores

```python
# ✅ GOOD: Document why type checking is disabled
import legacy_module  # type: ignore[import]  # TODO: Add type stubs

# ❌ BAD: No explanation
import legacy_module  # type: ignore
```

## Common Pitfalls

### ❌ Anti-Pattern 1: Using Any Everywhere

```python
# WRONG: Defeats purpose of type checking
from typing import Any

def process(data: Any) -> Any:
    return data.transform()
```

**Correct:**
```python
from typing import Union, Protocol

class Transformable(Protocol):
    def transform(self) -> dict: ...

def process(data: Transformable) -> dict:
    return data.transform()
```

### ❌ Anti-Pattern 2: Ignoring Type Errors Globally

```ini
# WRONG: Disables type checking
[mypy]
ignore_errors = True
```

**Correct:**
```ini
# Ignore specific modules only
[mypy-legacy.*]
ignore_errors = True

[mypy]
strict = True
```

### ❌ Anti-Pattern 3: Not Using Optional

```python
# WRONG: Nullable without Optional
def get_user(user_id: int) -> User:
    user = db.get(user_id)  # Can be None!
    return user  # Runtime error if None
```

**Correct:**
```python
from typing import Optional

def get_user(user_id: int) -> Optional[User]:
    return db.get(user_id)

# Handle None explicitly
user = get_user(123)
if user is not None:
    print(user.name)
```

## Quick Reference

### Common Commands

```bash
# Basic type checking
mypy main.py
mypy src/

# Strict mode
mypy --strict src/

# Install missing type stubs
mypy --install-types

# Generate HTML report
mypy src/ --html-report mypy-report

# Check specific error codes
mypy --show-error-codes src/

# Ignore missing imports
mypy --ignore-missing-imports src/

# Follow imports
mypy --follow-imports=silent src/

# Incremental mode (faster)
mypy --incremental src/

# Verbose output
mypy --verbose src/
```

### Error Code Reference

```bash
# Common error codes
[attr-defined]      # Attribute not defined
[arg-type]          # Argument type mismatch
[return-value]      # Return type mismatch
[assignment]        # Assignment type mismatch
[call-overload]     # No matching overload
[index]             # Invalid index operation
[operator]          # Unsupported operand type
[import]            # Cannot find import
[misc]              # Miscellaneous type error
[no-untyped-def]    # Function missing type annotation
[var-annotated]     # Variable needs type annotation
```

## Resources

- **Official Documentation**: https://mypy.readthedocs.io/
- **Type Hints PEP**: https://peps.python.org/pep-0484/
- **typing Module**: https://docs.python.org/3/library/typing.html
- **mypy GitHub**: https://github.com/python/mypy
- **Type Stubs**: https://github.com/python/typeshed
- **django-stubs**: https://github.com/typeddjango/django-stubs
- **FastAPI + mypy**: https://fastapi.tiangolo.com/tutorial/type-hints/

## Related Skills

When using mypy, consider these complementary skills (available in the skill library):

- **pytest**: Type-safe testing with mypy - integrates type checking into your test suite for comprehensive type coverage
- **fastapi-local-dev**: FastAPI with full type safety - combines FastAPI's runtime validation with mypy's static checking
- **pydantic**: Runtime type validation with mypy support - validates data at runtime while mypy validates at compile time

---

**mypy Version Compatibility:** This skill covers mypy 1.8+ and reflects current best practices for Python type checking in 2025.
