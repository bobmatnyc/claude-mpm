# Plan Structure Templates

## Standard Plan Document Header

**Every plan MUST start with this header:**

```markdown
# [Feature Name] Implementation Plan

> **For Claude:** Use `${SUPERPOWERS_SKILLS_ROOT}/skills/collaboration/executing-plans/SKILL.md` to implement this plan task-by-task.

**Goal:** [One sentence describing what this builds]

**Architecture:** [2-3 sentences about approach]

**Tech Stack:** [Key technologies/libraries]

---
```

## Task Template Structure

```markdown
### Task N: [Component Name]

**Files:**
- Create: `exact/path/to/file.py`
- Modify: `exact/path/to/existing.py:123-145`
- Test: `tests/exact/path/to/test.py`

**Step 1: Write the failing test**

```python
def test_specific_behavior():
    result = function(input)
    assert result == expected
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/path/test.py::test_name -v`
Expected: FAIL with "function not defined"

**Step 3: Write minimal implementation**

```python
def function(input):
    return expected
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/path/test.py::test_name -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/path/test.py src/path/file.py
git commit -m "feat: add specific feature"
```
```

## Bite-Sized Task Examples

### Example 1: Database Model

```markdown
### Task 1: User Model and Schema

**Files:**
- Create: `src/models/user.py`
- Create: `tests/models/test_user.py`
- Create: `migrations/001_create_users_table.sql`

**Step 1: Write the failing test**

```python
def test_user_model_creation():
    user = User(username="alice", email="alice@example.com")
    assert user.username == "alice"
    assert user.email == "alice@example.com"
    assert user.created_at is not None
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/models/test_user.py::test_user_model_creation -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'models.user'"

**Step 3: Write minimal implementation**

In `src/models/user.py`:
```python
from datetime import datetime
from dataclasses import dataclass

@dataclass
class User:
    username: str
    email: str
    created_at: datetime = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/models/test_user.py::test_user_model_creation -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/models/user.py tests/models/test_user.py
git commit -m "feat: add User model with basic fields"
```
```

### Example 2: API Endpoint

```markdown
### Task 3: GET /users/:id Endpoint

**Files:**
- Modify: `src/api/routes.py:15` (add route)
- Create: `src/api/handlers/users.py`
- Create: `tests/api/test_users_endpoint.py`

**Step 1: Write the failing test**

```python
def test_get_user_by_id(client, db_with_users):
    response = client.get("/users/1")
    assert response.status_code == 200
    assert response.json["username"] == "alice"
    assert response.json["email"] == "alice@example.com"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/api/test_users_endpoint.py::test_get_user_by_id -v`
Expected: FAIL with "404 Not Found"

**Step 3: Write minimal implementation**

In `src/api/handlers/users.py`:
```python
from flask import jsonify
from src.models.user import User
from src.db import get_db

def get_user(user_id):
    db = get_db()
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify({
        "id": user.id,
        "username": user.username,
        "email": user.email
    })
```

In `src/api/routes.py` at line 15:
```python
from src.api.handlers.users import get_user

# Add this route
app.route("/users/<int:user_id>", methods=["GET"])(get_user)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/api/test_users_endpoint.py::test_get_user_by_id -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/api/handlers/users.py src/api/routes.py tests/api/test_users_endpoint.py
git commit -m "feat: add GET /users/:id endpoint"
```
```

## Granularity Guidelines

**Each step should take 2-5 minutes:**

✅ **Good granularity:**
- "Write the failing test" - single test function
- "Run it to make sure it fails" - one command
- "Implement the minimal code to make the test pass" - focused function
- "Run the tests and make sure they pass" - verify
- "Commit" - checkpoint

❌ **Too large (split these up):**
- "Implement the user authentication system" - needs 10+ tasks
- "Add validation and error handling" - multiple tests/steps
- "Create all the models" - one task per model

❌ **Too small (combine these):**
- "Import the datetime module" - part of implementation step
- "Type the function signature" - part of implementation step
- "Add one line of code" - too granular

## Multi-File Task Structure

When a task involves multiple related files:

```markdown
### Task 4: Email Validation with Helper

**Files:**
- Create: `src/utils/validators.py`
- Create: `tests/utils/test_validators.py`
- Modify: `src/models/user.py:12` (use validator)
- Modify: `tests/models/test_user.py` (add validation tests)

**Step 1: Write failing test for validator**

In `tests/utils/test_validators.py`:
```python
def test_validate_email_valid():
    assert validate_email("alice@example.com") == True

def test_validate_email_invalid():
    assert validate_email("not-an-email") == False
```

**Step 2: Run validator test to verify it fails**

Run: `pytest tests/utils/test_validators.py -v`
Expected: FAIL with "NameError: name 'validate_email' is not defined"

**Step 3: Implement email validator**

In `src/utils/validators.py`:
```python
import re

def validate_email(email: str) -> bool:
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))
```

**Step 4: Run validator test to verify it passes**

Run: `pytest tests/utils/test_validators.py -v`
Expected: PASS (both tests)

**Step 5: Write failing test for User model validation**

In `tests/models/test_user.py`:
```python
def test_user_model_rejects_invalid_email():
    with pytest.raises(ValueError, match="Invalid email"):
        User(username="alice", email="not-an-email")
```

**Step 6: Run User model test to verify it fails**

Run: `pytest tests/models/test_user.py::test_user_model_rejects_invalid_email -v`
Expected: FAIL (no validation yet)

**Step 7: Add validation to User model**

In `src/models/user.py` at line 12:
```python
from src.utils.validators import validate_email

@dataclass
class User:
    username: str
    email: str
    created_at: datetime = None

    def __post_init__(self):
        if not validate_email(self.email):
            raise ValueError(f"Invalid email: {self.email}")
        if self.created_at is None:
            self.created_at = datetime.utcnow()
```

**Step 8: Run User model test to verify it passes**

Run: `pytest tests/models/test_user.py::test_user_model_rejects_invalid_email -v`
Expected: PASS

**Step 9: Run all tests to ensure nothing broke**

Run: `pytest tests/ -v`
Expected: All tests PASS

**Step 10: Commit**

```bash
git add src/utils/validators.py tests/utils/test_validators.py src/models/user.py tests/models/test_user.py
git commit -m "feat: add email validation to User model"
```
```

## Plan File Naming Convention

Save plans to: `docs/plans/YYYY-MM-DD-<feature-name>.md`

**Examples:**
- `docs/plans/2025-01-15-user-authentication.md`
- `docs/plans/2025-01-16-api-rate-limiting.md`
- `docs/plans/2025-01-17-database-migration-users.md`
