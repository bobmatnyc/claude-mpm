# Plan Writing Best Practices

## Core Principles

### DRY (Don't Repeat Yourself)
- Extract common patterns into utilities
- Reuse existing functions and classes
- Create shared helpers for repeated logic
- Never copy-paste code in the plan

### YAGNI (You Aren't Gonna Need It)
- Build only what's required by the design
- No speculative features
- No "future-proofing" unless explicitly required
- Start simple, extend when needed

### TDD (Test-Driven Development)
- Write test first, always
- Watch it fail before implementing
- Implement minimal code to pass
- Refactor after green

### Frequent Commits
- Commit after each passing test
- One feature per commit
- Clear, descriptive commit messages
- Never commit broken code

## Writing for Zero-Context Engineers

### Assume They Know
- Core programming concepts
- The programming language syntax
- Basic development tools (git, pytest, npm)
- General software patterns

### Assume They DON'T Know
- Your specific codebase structure
- Domain-specific terminology
- Project conventions and patterns
- Where files should go
- Which existing utilities to use
- Your testing strategy

### Therefore, Always Specify
- **Exact file paths** - not "in the user module" but "`src/models/user.py`"
- **Complete code** - not "add validation" but show the validation code
- **Exact commands** - not "run tests" but "`pytest tests/models/test_user.py -v`"
- **Expected output** - what should happen when they run the command
- **Line numbers** for modifications - "`src/config.py:45-52`"

## Complete Code, Not Instructions

❌ **Bad (vague instructions):**
```markdown
**Step 3: Add validation**

Add email validation to the User model.
Make sure to check for valid format.
```

✅ **Good (complete code):**
```markdown
**Step 3: Add validation to User model**

In `src/models/user.py`, add this method after line 12:
```python
def __post_init__(self):
    if not validate_email(self.email):
        raise ValueError(f"Invalid email: {self.email}")
    if self.created_at is None:
        self.created_at = datetime.utcnow()
```
```

## Exact Commands with Expected Output

❌ **Bad (vague):**
```markdown
**Step 2: Run the test**

Run the test and make sure it fails.
```

✅ **Good (specific):**
```markdown
**Step 2: Run test to verify it fails**

Run: `pytest tests/models/test_user.py::test_user_creation -v`
Expected output:
```
FAILED tests/models/test_user.py::test_user_creation - ModuleNotFoundError: No module named 'models.user'
```

This is expected! We haven't created the module yet.
```

## File Path Precision

### For New Files
```markdown
**Files:**
- Create: `src/api/handlers/users.py`
- Create: `tests/api/test_users.py`
```

### For Modifications
```markdown
**Files:**
- Modify: `src/api/routes.py:15` (add import)
- Modify: `src/api/routes.py:45` (add route registration)
- Modify: `src/config.py:12-18` (update database config)
```

### For Referenced Files
```markdown
**Documentation to check:**
- See: `docs/api-design.md` (endpoint specification)
- Reference: `src/api/handlers/auth.py:25-40` (similar pattern)
```

## Test Design for Zero-Context Engineers

Many engineers struggle with test design. Help them by:

### Show What to Test
```markdown
**Test coverage needed:**
1. Happy path (valid input → expected output)
2. Invalid input (error handling)
3. Edge cases (empty, null, boundary values)
4. Integration (does it work with real dependencies?)
```

### Provide Complete Test Examples
```python
# Happy path
def test_create_user_success():
    user = create_user("alice", "alice@example.com")
    assert user.username == "alice"
    assert user.email == "alice@example.com"

# Invalid input
def test_create_user_invalid_email():
    with pytest.raises(ValueError, match="Invalid email"):
        create_user("alice", "not-an-email")

# Edge case
def test_create_user_empty_username():
    with pytest.raises(ValueError, match="Username cannot be empty"):
        create_user("", "alice@example.com")
```

### Explain Test Strategy
```markdown
**Why these tests:**
- `test_create_user_success`: Verifies basic functionality works
- `test_create_user_invalid_email`: Ensures we reject bad data
- `test_create_user_empty_username`: Prevents edge case bugs
```

## Referencing Existing Code

### Use @ Syntax for Skills
```markdown
For authentication patterns, see @skills/security/implementing-auth
For API design, reference @skills/api/rest-endpoints
```

### Reference Codebase Files
```markdown
**Similar implementations:**
- `src/api/handlers/auth.py:25-40` - shows JWT validation pattern
- `src/utils/validators.py:10-15` - email validation we can reuse
```

### Point to Documentation
```markdown
**Required reading:**
- `docs/architecture/database-schema.md` - understand our user model
- `docs/api/authentication.md` - see auth requirements
```

## Handling Dependencies and Setup

### External Dependencies
```markdown
**Dependencies needed:**

Add to `requirements.txt`:
```
bcrypt==4.0.1
PyJWT==2.8.0
```

Install:
```bash
pip install -r requirements.txt
```
```

### Configuration Changes
```markdown
**Configuration update:**

In `src/config.py`, add:
```python
JWT_SECRET = os.environ.get("JWT_SECRET", "dev-secret-key")
JWT_EXPIRATION_HOURS = 24
```

In `.env.example`:
```
JWT_SECRET=your-secret-key-here
```
```

## Common Patterns to Include

### Error Handling Pattern
```python
try:
    result = risky_operation()
    return result
except SpecificError as e:
    logger.error(f"Operation failed: {e}")
    raise ValueError(f"Cannot complete operation: {e}")
except Exception as e:
    logger.exception("Unexpected error")
    raise
```

### Resource Cleanup Pattern
```python
def process_file(filepath):
    file_handle = None
    try:
        file_handle = open(filepath, 'r')
        data = file_handle.read()
        return process_data(data)
    finally:
        if file_handle:
            file_handle.close()
```

### Logging Pattern
```python
import logging

logger = logging.getLogger(__name__)

def important_operation():
    logger.info("Starting operation")
    try:
        result = do_work()
        logger.info(f"Operation completed: {result}")
        return result
    except Exception as e:
        logger.error(f"Operation failed: {e}", exc_info=True)
        raise
```

## Documentation in Plans

### When to Include Inline Docs
```markdown
**Step 3: Implement user creation with docstring**

```python
def create_user(username: str, email: str) -> User:
    """
    Create a new user with validation.

    Args:
        username: User's chosen username (must be unique)
        email: User's email address (must be valid format)

    Returns:
        User: The created user object

    Raises:
        ValueError: If username/email invalid or user exists
    """
    if not username:
        raise ValueError("Username cannot be empty")
    if not validate_email(email):
        raise ValueError(f"Invalid email: {email}")

    return User(username=username, email=email)
```
```

### When to Update Separate Docs
```markdown
**Step 10: Update API documentation**

In `docs/api/endpoints.md`, add:
```markdown
### POST /users

Create a new user account.

**Request:**
```json
{
  "username": "alice",
  "email": "alice@example.com"
}
```

**Response:** 201 Created
```json
{
  "id": 1,
  "username": "alice",
  "email": "alice@example.com",
  "created_at": "2025-01-15T10:30:00Z"
}
```
```
```

## Commit Message Guidelines

### Format
```
type: brief description

- Detail 1
- Detail 2
```

### Types
- `feat:` - New feature
- `fix:` - Bug fix
- `test:` - Add/update tests
- `refactor:` - Code restructuring
- `docs:` - Documentation only
- `chore:` - Tooling, dependencies

### Examples
```bash
git commit -m "feat: add user email validation"
git commit -m "test: add edge cases for user creation"
git commit -m "fix: handle empty username in user model"
git commit -m "refactor: extract validation to utils module"
```

## Quality Checklist for Plans

Before saving the plan, verify:

- [ ] All file paths are exact and absolute
- [ ] All code blocks are complete (not pseudocode)
- [ ] All commands include expected output
- [ ] Tests are written before implementation
- [ ] Each step is 2-5 minutes of work
- [ ] Dependencies and setup are documented
- [ ] Error handling is included
- [ ] Commit messages are descriptive
- [ ] Referenced skills use @ syntax
- [ ] Header follows standard template
