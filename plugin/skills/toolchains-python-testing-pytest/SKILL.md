---
name: pytest
description: pytest - Python's most powerful testing framework with fixtures, parametrization, plugins, and framework integration for FastAPI, Django, Flask
version: 1.0.0
category: toolchain
author: Claude MPM Team
license: MIT
progressive_disclosure:
  entry_point:
    summary: "Professional Python testing: fixtures, parametrize, markers, async support, FastAPI/Django/Flask integration, coverage, mocking"
    when_to_use: "Writing unit tests, integration tests, API testing, TDD workflow, testing async code, database testing, mocking dependencies"
    quick_start: "1. pip install pytest 2. Create test_*.py files 3. Use fixtures with @pytest.fixture 4. Parametrize with @pytest.mark.parametrize 5. Run: pytest -v"
context_limit: 700
tags:
  - pytest
  - testing
  - python
  - tdd
  - unit-testing
  - fixtures
  - mocking
  - async
  - fastapi
  - django
requires_tools: []
---

# pytest - Professional Python Testing

## Overview

pytest is the industry-standard Python testing framework, offering powerful features like fixtures, parametrization, markers, plugins, and seamless integration with FastAPI, Django, and Flask. It provides a simple, scalable approach to testing from unit tests to complex integration scenarios.

**Key Features**:
- Fixture system for dependency injection
- Parametrization for data-driven tests
- Rich assertion introspection (no need for `self.assertEqual`)
- Plugin ecosystem (pytest-cov, pytest-asyncio, pytest-mock, pytest-django)
- Async/await support
- Parallel test execution with pytest-xdist
- Test discovery and organization
- Detailed failure reporting

**Installation**:
```bash
# Basic pytest
pip install pytest

# With common plugins
pip install pytest pytest-cov pytest-asyncio pytest-mock

# For FastAPI testing
pip install pytest httpx pytest-asyncio

# For Django testing
pip install pytest pytest-django

# For async databases
pip install pytest-asyncio aiosqlite
```

## Basic Testing Patterns

### 1. Simple Test Functions

```python
# test_math.py
def add(a, b):
    return a + b

def test_add():
    assert add(2, 3) == 5
    assert add(-1, 1) == 0
    assert add(0, 0) == 0

def test_add_negative():
    assert add(-2, -3) == -5
```

**Run tests:**
```bash
# Discover and run all tests
pytest

# Verbose output
pytest -v

# Show print statements
pytest -s

# Run specific test file
pytest test_math.py

# Run specific test function
pytest test_math.py::test_add
```

### 2. Test Classes for Organization

```python
# test_calculator.py
class Calculator:
    def add(self, a, b):
        return a + b

    def multiply(self, a, b):
        return a * b

class TestCalculator:
    def test_add(self):
        calc = Calculator()
        assert calc.add(2, 3) == 5

    def test_multiply(self):
        calc = Calculator()
        assert calc.multiply(4, 5) == 20

    def test_add_negative(self):
        calc = Calculator()
        assert calc.add(-1, -1) == -2
```

### 3. Assertions and Expected Failures

```python
import pytest

# Test exception raising
def divide(a, b):
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b

def test_divide_by_zero():
    with pytest.raises(ValueError, match="Cannot divide by zero"):
        divide(10, 0)

def test_divide_success():
    assert divide(10, 2) == 5.0

# Test approximate equality
def test_float_comparison():
    assert 0.1 + 0.2 == pytest.approx(0.3)

# Test containment
def test_list_contains():
    result = [1, 2, 3, 4]
    assert 3 in result
    assert len(result) == 4
```

## Fixtures - Dependency Injection

### Basic Fixtures

```python
# conftest.py
import pytest

@pytest.fixture
def sample_data():
    """Provide sample data for tests."""
    return {"name": "Alice", "age": 30, "email": "alice@example.com"}

@pytest.fixture
def empty_list():
    """Provide an empty list."""
    return []

# test_fixtures.py
def test_sample_data(sample_data):
    assert sample_data["name"] == "Alice"
    assert sample_data["age"] == 30

def test_empty_list(empty_list):
    empty_list.append(1)
    assert len(empty_list) == 1
```

### Fixture Scopes

```python
import pytest

# Function scope (default) - runs for each test
@pytest.fixture(scope="function")
def user():
    return {"id": 1, "name": "Alice"}

# Class scope - runs once per test class
@pytest.fixture(scope="class")
def database():
    db = setup_database()
    yield db
    db.close()

# Module scope - runs once per test module
@pytest.fixture(scope="module")
def api_client():
    client = APIClient()
    yield client
    client.shutdown()

# Session scope - runs once for entire test session
@pytest.fixture(scope="session")
def app_config():
    return load_config()
```

### Fixture Setup and Teardown

```python
import pytest
import tempfile
import shutil

@pytest.fixture
def temp_directory():
    """Create a temporary directory for test."""
    temp_dir = tempfile.mkdtemp()
    print(f"
Setup: Created {temp_dir}")

    yield temp_dir  # Provide directory to test

    # Teardown: cleanup after test
    shutil.rmtree(temp_dir)
    print(f"
Teardown: Removed {temp_dir}")

def test_file_creation(temp_directory):
    file_path = f"{temp_directory}/test.txt"
    with open(file_path, "w") as f:
        f.write("test content")

    assert os.path.exists(file_path)
```

### Fixture Dependencies

```python
import pytest

@pytest.fixture
def database_connection():
    """Database connection."""
    conn = connect_to_db()
    yield conn
    conn.close()

@pytest.fixture
def database_session(database_connection):
    """Database session depends on connection."""
    session = create_session(database_connection)
    yield session
    session.rollback()
    session.close()

@pytest.fixture
def user_repository(database_session):
    """User repository depends on session."""
    return UserRepository(database_session)

def test_create_user(user_repository):
    user = user_repository.create(name="Alice", email="alice@example.com")
    assert user.name == "Alice"
```

## Parametrization - Data-Driven Testing

### Basic Parametrization

```python
import pytest

@pytest.mark.parametrize("a,b,expected", [
    (2, 3, 5),
    (5, 7, 12),
    (-1, 1, 0),
    (0, 0, 0),
    (100, 200, 300),
])
def test_add_parametrized(a, b, expected):
    assert add(a, b) == expected
```

### Multiple Parameters

```python
@pytest.mark.parametrize("operation,a,b,expected", [
    ("add", 2, 3, 5),
    ("subtract", 10, 5, 5),
    ("multiply", 4, 5, 20),
    ("divide", 10, 2, 5),
])
def test_calculator_operations(operation, a, b, expected):
    calc = Calculator()
    result = getattr(calc, operation)(a, b)
    assert result == expected
```

### Parametrize with IDs

```python
@pytest.mark.parametrize("input_data,expected", [
    pytest.param({"name": "Alice"}, "Alice", id="valid_name"),
    pytest.param({"name": ""}, None, id="empty_name"),
    pytest.param({}, None, id="missing_name"),
], ids=lambda x: x if isinstance(x, str) else None)
def test_extract_name(input_data, expected):
    result = extract_name(input_data)
    assert result == expected
```

### Indirect Parametrization (Fixtures)

```python
@pytest.fixture
def user_data(request):
    """Create user based on parameter."""
    return {"name": request.param, "email": f"{request.param}@example.com"}

@pytest.mark.parametrize("user_data", ["Alice", "Bob", "Charlie"], indirect=True)
def test_user_creation(user_data):
    assert "@example.com" in user_data["email"]
```

## Test Markers

### Built-in Markers

```python
import pytest

# Skip test
@pytest.mark.skip(reason="Not implemented yet")
def test_future_feature():
    pass

# Skip conditionally
@pytest.mark.skipif(sys.platform == "win32", reason="Unix-only test")
def test_unix_specific():
    pass

# Expected failure
@pytest.mark.xfail(reason="Known bug #123")
def test_known_bug():
    assert False

# Slow test marker
@pytest.mark.slow
def test_expensive_operation():
    time.sleep(5)
    assert True
```

### Custom Markers

```python
# pytest.ini
[pytest]
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    integration: marks tests as integration tests
    unit: marks tests as unit tests
    smoke: marks tests as smoke tests

# test_custom_markers.py
import pytest

@pytest.mark.unit
def test_fast_unit():
    assert True

@pytest.mark.integration
@pytest.mark.slow
def test_slow_integration():
    # Integration test with database
    pass

@pytest.mark.smoke
def test_critical_path():
    # Smoke test for critical functionality
    pass
```

**Run tests by marker:**
```bash
# Run only unit tests
pytest -m unit

# Run all except slow tests
pytest -m "not slow"

# Run integration tests
pytest -m integration

# Run unit AND integration
pytest -m "unit or integration"

# Run smoke tests only
pytest -m smoke
```

## FastAPI Testing

### Basic FastAPI Test Setup

```python
# app/main.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

class Item(BaseModel):
    name: str
    price: float

@app.get("/")
def read_root():
    return {"message": "Hello World"}

@app.get("/items/{item_id}")
def read_item(item_id: int):
    if item_id == 0:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"item_id": item_id, "name": f"Item {item_id}"}

@app.post("/items")
def create_item(item: Item):
    return {"name": item.name, "price": item.price, "id": 123}
```

### FastAPI Test Client

```python
# conftest.py
import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)

# test_api.py
def test_read_root(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello World"}

def test_read_item(client):
    response = client.get("/items/1")
    assert response.status_code == 200
    assert response.json() == {"item_id": 1, "name": "Item 1"}

def test_read_item_not_found(client):
    response = client.get("/items/0")
    assert response.status_code == 404
    assert response.json() == {"detail": "Item not found"}

def test_create_item(client):
    response = client.post(
        "/items",
        json={"name": "Widget", "price": 9.99}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Widget"
    assert data["price"] == 9.99
    assert "id" in data
```

### Async FastAPI Testing

```python
# conftest.py
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.fixture
async def async_client():
    """Async test client for FastAPI."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

# test_async_api.py
import pytest

@pytest.mark.asyncio
async def test_read_root_async(async_client):
    response = await async_client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello World"}

@pytest.mark.asyncio
async def test_create_item_async(async_client):
    response = await async_client.post(
        "/items",
        json={"name": "Gadget", "price": 19.99}
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Gadget"
```

### FastAPI with Database Testing

```python
# conftest.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base, get_db
from app.main import app

# Test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def test_db():
    """Create test database."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def client(test_db):
    """Override database dependency."""
    def override_get_db():
        try:
            db = TestingSessionLocal()
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()

# test_users.py
def test_create_user(client):
    response = client.post(
        "/users",
        json={"email": "test@example.com", "password": "secret"}
    )
    assert response.status_code == 200
    assert response.json()["email"] == "test@example.com"

def test_read_users(client):
    # Create user first
    client.post("/users", json={"email": "user1@example.com", "password": "pass1"})
    client.post("/users", json={"email": "user2@example.com", "password": "pass2"})

    # Read users
    response = client.get("/users")
    assert response.status_code == 200
    assert len(response.json()) == 2
```

## Django Testing

### Django pytest Configuration

```python
# pytest.ini
[pytest]
DJANGO_SETTINGS_MODULE = myproject.settings
python_files = tests.py test_*.py *_tests.py

# conftest.py
import pytest
from django.conf import settings

@pytest.fixture(scope='session')
def django_db_setup():
    settings.DATABASES['default'] = {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
```

### Django Model Testing

```python
# models.py
from django.db import models

class User(models.Model):
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

# test_models.py
import pytest
from myapp.models import User

@pytest.mark.django_db
def test_create_user():
    user = User.objects.create(
        email="test@example.com",
        name="Test User"
    )
    assert user.email == "test@example.com"
    assert user.is_active is True

@pytest.mark.django_db
def test_user_unique_email():
    User.objects.create(email="test@example.com", name="User 1")

    with pytest.raises(Exception):  # IntegrityError
        User.objects.create(email="test@example.com", name="User 2")
```

### Django View Testing

```python
# views.py
from django.http import JsonResponse
from django.views import View

class UserListView(View):
    def get(self, request):
        users = User.objects.all()
        return JsonResponse({
            "users": list(users.values("id", "email", "name"))
        })

# test_views.py
import pytest
from django.test import Client
from myapp.models import User

@pytest.fixture
def client():
    return Client()

@pytest.mark.django_db
def test_user_list_view(client):
    # Create test data
    User.objects.create(email="user1@example.com", name="User 1")
    User.objects.create(email="user2@example.com", name="User 2")

    # Test view
    response = client.get("/users/")
    assert response.status_code == 200

    data = response.json()
    assert len(data["users"]) == 2
```

### Django REST Framework Testing

```python
# serializers.py
from rest_framework import serializers
from myapp.models import User

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'name', 'is_active']

# views.py
from rest_framework import viewsets
from myapp.models import User
from myapp.serializers import UserSerializer

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

# test_api.py
import pytest
from rest_framework.test import APIClient
from myapp.models import User

@pytest.fixture
def api_client():
    return APIClient()

@pytest.mark.django_db
def test_list_users(api_client):
    User.objects.create(email="user1@example.com", name="User 1")
    User.objects.create(email="user2@example.com", name="User 2")

    response = api_client.get("/api/users/")
    assert response.status_code == 200
    assert len(response.data) == 2

@pytest.mark.django_db
def test_create_user(api_client):
    data = {"email": "new@example.com", "name": "New User"}
    response = api_client.post("/api/users/", data)

    assert response.status_code == 201
    assert User.objects.filter(email="new@example.com").exists()
```

## Mocking and Patching

### pytest-mock (pytest.fixture.mocker)

```python
# Install: pip install pytest-mock

# service.py
import requests

def get_user_data(user_id):
    response = requests.get(f"https://api.example.com/users/{user_id}")
    return response.json()

# test_service.py
def test_get_user_data(mocker):
    # Mock requests.get
    mock_response = mocker.Mock()
    mock_response.json.return_value = {"id": 1, "name": "Alice"}

    mocker.patch("requests.get", return_value=mock_response)

    result = get_user_data(1)
    assert result["name"] == "Alice"
```

### Mocking Class Methods

```python
class UserService:
    def get_user(self, user_id):
        # Database call
        return database.fetch_user(user_id)

    def get_user_name(self, user_id):
        user = self.get_user(user_id)
        return user["name"]

def test_get_user_name(mocker):
    service = UserService()

    # Mock the get_user method
    mocker.patch.object(
        service,
        "get_user",
        return_value={"id": 1, "name": "Alice"}
    )

    result = service.get_user_name(1)
    assert result == "Alice"
```

### Mocking with Side Effects

```python
def test_retry_on_failure(mocker):
    # First call fails, second succeeds
    mock_api = mocker.patch("requests.get")
    mock_api.side_effect = [
        requests.exceptions.Timeout(),  # First call
        mocker.Mock(json=lambda: {"status": "ok"})  # Second call
    ]

    result = api_call_with_retry()
    assert result["status"] == "ok"
    assert mock_api.call_count == 2
```

### Spy on Calls

```python
def test_function_called_correctly(mocker):
    spy = mocker.spy(module, "function_name")

    # Call code that uses the function
    module.run_workflow()

    # Verify it was called
    assert spy.call_count == 1
    spy.assert_called_once_with(arg1="value", arg2=42)
```

## Coverage and Reporting

### pytest-cov Configuration

```bash
# Install
pip install pytest-cov

# Run with coverage
pytest --cov=app --cov-report=html --cov-report=term

# Generate coverage report
pytest --cov=app --cov-report=term-missing

# Coverage with minimum threshold
pytest --cov=app --cov-fail-under=80
```

### pytest.ini Coverage Configuration

```ini
# pytest.ini
[pytest]
addopts =
    --cov=app
    --cov-report=html
    --cov-report=term-missing
    --cov-fail-under=80
    -v
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
```

### Coverage Reports

```bash
# HTML report (opens in browser)
pytest --cov=app --cov-report=html
open htmlcov/index.html

# Terminal report with missing lines
pytest --cov=app --cov-report=term-missing

# XML report (for CI/CD)
pytest --cov=app --cov-report=xml

# JSON report
pytest --cov=app --cov-report=json
```

## Async Testing

### pytest-asyncio

```python
# Install: pip install pytest-asyncio

# conftest.py
import pytest

# Enable asyncio mode
pytest_plugins = ('pytest_asyncio',)

# async_service.py
import asyncio
import aiohttp

async def fetch_data(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.json()

# test_async_service.py
import pytest

@pytest.mark.asyncio
async def test_fetch_data(mocker):
    # Mock aiohttp response
    mock_response = mocker.AsyncMock()
    mock_response.json.return_value = {"data": "test"}

    mock_session = mocker.AsyncMock()
    mock_session.__aenter__.return_value.get.return_value.__aenter__.return_value = mock_response

    mocker.patch("aiohttp.ClientSession", return_value=mock_session)

    result = await fetch_data("https://api.example.com/data")
    assert result["data"] == "test"
```

### Async Fixtures

```python
@pytest.fixture
async def async_db_session():
    """Async database session."""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSession(async_engine) as session:
        yield session

    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.mark.asyncio
async def test_create_user_async(async_db_session):
    user = User(email="test@example.com", name="Test")
    async_db_session.add(user)
    await async_db_session.commit()

    result = await async_db_session.execute(
        select(User).where(User.email == "test@example.com")
    )
    assert result.scalar_one().name == "Test"
```

## Local pytest Profiles (Your Repos)

Common settings from your projects' `pyproject.toml`:

- `asyncio_mode = "auto"` (default in mcp-browser, mcp-memory, claude-mpm, edgar)
- `addopts` includes `--strict-markers` and `--strict-config` for CI consistency
- Coverage flags: `--cov=<package>`, `--cov-report=term-missing`, `--cov-report=xml`
- Selective ignores (mcp-vector-search): `--ignore=tests/manual`, `--ignore=tests/e2e`
- `pythonpath = ["src"]` for editable import resolution (mcp-ticketer)

Typical markers:

- `unit`, `integration`, `e2e`
- `slow`, `benchmark`, `performance`
- `requires_api` (edgar)

Reference: see `pyproject.toml` in `claude-mpm`, `edgar`, `mcp-vector-search`, `mcp-ticketer`, and `kuzu-memory` for full lists.

## Best Practices

### 1. Test Organization

```
project/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── models.py
│   └── services.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py          # Shared fixtures
│   ├── test_models.py       # Model tests
│   ├── test_services.py     # Service tests
│   ├── test_api.py          # API tests
│   └── integration/
│       ├── __init__.py
│       └── test_workflows.py
└── pytest.ini
```

### 2. Naming Conventions

```python
# ✅ GOOD: Clear test names
def test_user_creation_with_valid_email():
    pass

def test_user_creation_raises_error_for_duplicate_email():
    pass

# ❌ BAD: Vague names
def test_user1():
    pass

def test_case2():
    pass
```

### 3. Arrange-Act-Assert Pattern

```python
def test_user_service_creates_user():
    # Arrange: Setup test data and dependencies
    service = UserService(database=mock_db)
    user_data = {"email": "test@example.com", "name": "Test"}

    # Act: Perform the action being tested
    result = service.create_user(user_data)

    # Assert: Verify the outcome
    assert result.email == "test@example.com"
    assert result.id is not None
```

### 4. Use Fixtures for Common Setup

```python
# ❌ BAD: Repeated setup
def test_user_creation():
    db = setup_database()
    user = create_user(db)
    assert user.id is not None
    db.close()

def test_user_deletion():
    db = setup_database()
    user = create_user(db)
    delete_user(db, user.id)
    db.close()

# ✅ GOOD: Fixture-based setup
@pytest.fixture
def db():
    database = setup_database()
    yield database
    database.close()

@pytest.fixture
def user(db):
    return create_user(db)

def test_user_creation(user):
    assert user.id is not None

def test_user_deletion(db, user):
    delete_user(db, user.id)
    assert not user_exists(db, user.id)
```

### 5. Parametrize Similar Tests

```python
# ❌ BAD: Duplicate test code
def test_add_positive():
    assert add(2, 3) == 5

def test_add_negative():
    assert add(-2, -3) == -5

def test_add_zero():
    assert add(0, 0) == 0

# ✅ GOOD: Parametrized tests
@pytest.mark.parametrize("a,b,expected", [
    (2, 3, 5),
    (-2, -3, -5),
    (0, 0, 0),
])
def test_add(a, b, expected):
    assert add(a, b) == expected
```

### 6. Test One Thing Per Test

```python
# ❌ BAD: Testing multiple things
def test_user_workflow():
    user = create_user()
    assert user.id is not None

    updated = update_user(user.id, name="New Name")
    assert updated.name == "New Name"

    deleted = delete_user(user.id)
    assert deleted is True

# ✅ GOOD: Separate tests
def test_user_creation():
    user = create_user()
    assert user.id is not None

def test_user_update():
    user = create_user()
    updated = update_user(user.id, name="New Name")
    assert updated.name == "New Name"

def test_user_deletion():
    user = create_user()
    result = delete_user(user.id)
    assert result is True
```

### 7. Use Markers for Test Organization

```python
@pytest.mark.unit
def test_pure_function():
    pass

@pytest.mark.integration
@pytest.mark.slow
def test_database_integration():
    pass

@pytest.mark.smoke
def test_critical_path():
    pass
```

### 8. Mock External Dependencies

```python
# ✅ GOOD: Mock external API
def test_fetch_user_data(mocker):
    mocker.patch("requests.get", return_value=mock_response)
    result = fetch_user_data(user_id=1)
    assert result["name"] == "Alice"

# ❌ BAD: Real API call in test
def test_fetch_user_data():
    result = fetch_user_data(user_id=1)  # Real HTTP request!
    assert result["name"] == "Alice"
```

## Common Pitfalls

### ❌ Anti-Pattern 1: Test Depends on Execution Order

```python
# WRONG: Tests should be independent
class TestUserWorkflow:
    user_id = None

    def test_create_user(self):
        user = create_user()
        TestUserWorkflow.user_id = user.id

    def test_update_user(self):
        # Fails if test_create_user didn't run first!
        update_user(TestUserWorkflow.user_id, name="New")
```

**Correct:**
```python
@pytest.fixture
def created_user():
    return create_user()

def test_create_user(created_user):
    assert created_user.id is not None

def test_update_user(created_user):
    update_user(created_user.id, name="New")
```

### ❌ Anti-Pattern 2: Not Cleaning Up Resources

```python
# WRONG: Database not cleaned up
def test_user_creation():
    db = setup_database()
    user = create_user(db)
    assert user.id is not None
    # Database connection not closed!
```

**Correct:**
```python
@pytest.fixture
def db():
    database = setup_database()
    yield database
    database.close()  # Cleanup
```

### ❌ Anti-Pattern 3: Testing Implementation Details

```python
# WRONG: Testing internal implementation
def test_user_service_uses_cache():
    service = UserService()
    service.get_user(1)
    assert service._cache.has_key(1)  # Testing internal cache!
```

**Correct:**
```python
# Test behavior, not implementation
def test_user_service_returns_user():
    service = UserService()
    user = service.get_user(1)
    assert user.id == 1
```

### ❌ Anti-Pattern 4: Not Using pytest Features

```python
# WRONG: Using unittest assertions
import unittest

def test_addition():
    result = add(2, 3)
    unittest.TestCase().assertEqual(result, 5)
```

**Correct:**
```python
# Use pytest's rich assertions
def test_addition():
    assert add(2, 3) == 5
```

### ❌ Anti-Pattern 5: Overly Complex Fixtures

```python
# WRONG: Fixture does too much
@pytest.fixture
def everything():
    db = setup_db()
    user = create_user(db)
    session = login(user)
    cache = setup_cache()
    # ... too many things!
    return {"db": db, "user": user, "session": session, "cache": cache}
```

**Correct:**
```python
# Separate, composable fixtures
@pytest.fixture
def db():
    return setup_db()

@pytest.fixture
def user(db):
    return create_user(db)

@pytest.fixture
def session(user):
    return login(user)
```

## Quick Reference

### Common Commands

```bash
# Run all tests
pytest

# Verbose output
pytest -v

# Show print statements
pytest -s

# Run specific file
pytest tests/test_api.py

# Run specific test
pytest tests/test_api.py::test_create_user

# Run by marker
pytest -m unit
pytest -m "not slow"

# Run with coverage
pytest --cov=app --cov-report=html

# Parallel execution
pytest -n auto  # Requires pytest-xdist

# Stop on first failure
pytest -x

# Show local variables on failure
pytest -l

# Run last failed tests
pytest --lf

# Run failed tests first
pytest --ff
```

### pytest.ini Template

```ini
[pytest]
# Minimum pytest version
minversion = 7.0

# Test discovery patterns
python_files = test_*.py *_test.py
python_classes = Test*
python_functions = test_*

# Test paths
testpaths = tests

# Command line options
addopts =
    -v
    --strict-markers
    --cov=app
    --cov-report=html
    --cov-report=term-missing
    --cov-fail-under=80

# Markers
markers =
    unit: Unit tests
    integration: Integration tests
    slow: Slow-running tests
    smoke: Smoke tests for critical paths

# Django settings (if using Django)
DJANGO_SETTINGS_MODULE = myproject.settings

# Asyncio mode
asyncio_mode = auto
```

### conftest.py Template

```python
# conftest.py
import pytest
from fastapi.testclient import TestClient
from app.main import app

# FastAPI client fixture
@pytest.fixture
def client():
    return TestClient(app)

# Database fixture
@pytest.fixture(scope="function")
def db():
    database = setup_test_database()
    yield database
    database.close()

# Mock user fixture
@pytest.fixture
def mock_user():
    return {"id": 1, "email": "test@example.com", "name": "Test User"}

# Custom pytest configuration
def pytest_configure(config):
    config.addinivalue_line("markers", "api: API tests")
    config.addinivalue_line("markers", "db: Database tests")
```

## Resources

- **Official Documentation**: https://docs.pytest.org/
- **pytest-asyncio**: https://pytest-asyncio.readthedocs.io/
- **pytest-cov**: https://pytest-cov.readthedocs.io/
- **pytest-mock**: https://pytest-mock.readthedocs.io/
- **pytest-django**: https://pytest-django.readthedocs.io/
- **FastAPI Testing**: https://fastapi.tiangolo.com/tutorial/testing/

## Related Skills

When using pytest, consider these complementary skills:

- **fastapi-local-dev**: FastAPI development server patterns and test fixtures
- **test-driven-development**: Complete TDD workflow (RED/GREEN/REFACTOR cycle)
- **systematic-debugging**: Root cause investigation for failing tests

### Quick TDD Workflow Reference (Inlined for Standalone Use)

**RED → GREEN → REFACTOR Cycle:**

1. **RED Phase: Write Failing Test**
   ```python
   def test_should_authenticate_user_when_credentials_valid():
       # Test that describes desired behavior
       user = User(username='alice', password='secret123')
       result = authenticate(user)
       assert result.is_authenticated is True
       # This test will fail because authenticate() doesn't exist yet
   ```

2. **GREEN Phase: Make It Pass**
   ```python
   def authenticate(user):
       # Minimum code to pass the test
       if user.username == 'alice' and user.password == 'secret123':
           return AuthResult(is_authenticated=True)
       return AuthResult(is_authenticated=False)
   ```

3. **REFACTOR Phase: Improve Code**
   ```python
   def authenticate(user):
       # Clean up while keeping tests green
       hashed_password = hash_password(user.password)
       stored_user = database.get_user(user.username)
       return AuthResult(
           is_authenticated=(stored_user.password_hash == hashed_password)
       )
   ```

**Test Structure: Arrange-Act-Assert (AAA)**
```python
def test_user_creation():
    # Arrange: Set up test data
    user_data = {'username': 'alice', 'email': 'alice@example.com'}

    # Act: Perform the action
    user = create_user(user_data)

    # Assert: Verify outcome
    assert user.username == 'alice'
    assert user.email == 'alice@example.com'
```

### Quick Debugging Reference (Inlined for Standalone Use)

**Phase 1: Root Cause Investigation**
- Read error messages completely (stack traces, line numbers)
- Reproduce consistently (document exact steps)
- Check recent changes (git log, git diff)
- Understand what changed and why it might cause failure

**Phase 2: Isolate the Problem**
```python
# Use pytest's built-in debugging
pytest tests/test_auth.py -vv --pdb  # Drop into debugger on failure
pytest tests/test_auth.py -x         # Stop on first failure
pytest tests/test_auth.py -k "auth"  # Run only auth-related tests

# Add strategic print/logging
def test_complex_workflow():
    user = create_user({'username': 'test'})
    print(f"DEBUG: Created user {user.id}")  # Visible with pytest -s
    result = process_user(user)
    print(f"DEBUG: Result status {result.status}")
    assert result.success
```

**Phase 3: Fix Root Cause**
- Fix the underlying problem, not symptoms
- Add regression test to prevent recurrence
- Verify fix doesn't break other tests

**Phase 4: Verify Solution**
```bash
# Run full test suite
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Verify specific test patterns
pytest -k "auth or login" -v
```

[Full TDD and debugging workflows available in respective skills if deployed together]

---

**pytest Version Compatibility:** This skill covers pytest 7.0+ and reflects current best practices for Python testing in 2025.
