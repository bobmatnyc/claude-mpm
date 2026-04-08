# AI Coding Bake-Off: claude-mpm L5 and L3 Failure Analysis

**Date:** 2026-04-04
**Research Type:** Comparative failure analysis
**Subject:** claude-mpm vs auggie on Level 3 (Weather Alerter) and Level 5 (Task Board)

---

## Executive Summary

Both failures are **environment-dependent missing dependency issues**, not application logic bugs. The code is functionally correct and passes all 7 tests when run in a Python environment that has the required packages installed.

- **L5 "1/7 passed"**: The "1/7" was observed with a stale SQLite database from a prior run. With a clean DB and correct Python, all 7 pass. The actual production failure is that the `python3` in the test environment lacks `sqlalchemy` (and optionally `bcrypt`/`python-jose`).
- **L3 "5 skipped"**: The app cannot be imported because `apscheduler` is listed as a dependency but not installed in the test environment's Python. 5 of 7 tests use `app_client` which silently skips when import fails. 2 pure-logic tests (`check_threshold`) pass regardless.

---

## Part 1: L5 Task Board — Detailed Analysis

### Test File Expectations

`challenges/level-5-task-board/test_suite/test_basic.py` expects:

| Route | Method | Expected Status |
|-------|--------|----------------|
| `/api/auth/register` | POST | 200 or 201 |
| `/api/auth/login` | POST | 200 |
| `/api/users/me` | GET | 401 or 403 (unauthenticated) |
| `/api/boards` | POST | 200 or 201 |
| `/api/boards` | GET | 200 |
| `/api/boards/{id}` | GET | 200 |
| `/api/boards/{board_id}/columns` | POST | 200 or 201 |
| `/api/tasks` | POST | 200 or 201 |
| `/api/boards/{board_id}/activity` | GET | 200 |

### claude-mpm's App Structure

**app.py** registers:
```python
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(users.router, prefix="/api/users", tags=["users"])
app.include_router(boards.router, prefix="/api/boards", tags=["boards"])
app.include_router(columns.router, prefix="/api", tags=["columns"])
app.include_router(tasks.router, prefix="/api/tasks", tags=["tasks"])
app.include_router(activity.router, prefix="/api/activity", tags=["activity"])
```

**Route paths are correct.** `/api/auth/register`, `/api/auth/login`, `/api/users/me`, `/api/boards`, `/api/tasks` all match test expectations.

### Root Cause 1: Missing SQLAlchemy in Test Environment

```
ImportError: No module named 'sqlalchemy'
```

When run with `python3` pointing to the claude-mpm project venv (Python 3.12), sqlalchemy is not installed. The `task_board/app.py` imports `from task_board.database import engine` at module level, which imports `from sqlalchemy import create_engine`. The entire import fails before the app is constructed.

The `app_client` fixture catches this silently:
```python
try:
    from task_board.app import app
except ImportError:
    pass
# ... tries Flask, Django, then:
pytest.skip("Could not create test client")
```

Result: All 7 tests skip (not even "1/7 passed").

### Root Cause 2: Stale SQLite Database

When running with `python3.11` (which has sqlalchemy), all 7 tests pass on a clean run. But on subsequent runs without deleting `task_board.db`:

**Test order:** `test_register_user` runs FIRST. But the `auth_headers` fixture (used by board/task tests that run after) has already registered `test@example.com`, `logintest@example.com`, and `newuser@example.com` from previous runs. When `test_register_user` tries to register `newuser@example.com` again:

```python
# task_board/routes/auth.py line 16
if db.query(User).filter(User.email == data.email).first():
    raise HTTPException(status_code=400, detail="Email already registered")
```

Result: 400 Bad Request → test fails → **1/7 passed** (the first test fails, remaining 6 pass because `auth_headers` succeeds using existing data).

**Why doesn't the conftest fix it?**

`conftest.py` deletes `task_board.db` as a session-scoped fixture. But when pytest is invoked against a test file outside the `level-5/` directory (the challenge's `test_basic.py`), pytest's rootdir becomes the bake-off root (where `pyproject.toml` exists), not `level-5/`. The conftest in `level-5/conftest.py` is never loaded.

```
rootdir: /Users/masa/Projects/ai-coding-bake-off   # <-- bake-off root, not level-5
configfile: pyproject.toml
# conftest.py in harnesses/claude-mpm/output/level-5/ is never loaded
```

### auggie's L5 Solution — What It Does Differently

**Database:** Uses SQLite with raw sqlite3 (no SQLAlchemy). `database.py` uses `sqlite3.connect(":memory:")` with `_DB_PATH = os.environ.get("TASK_BOARD_DB", ":memory:")`. In-memory by default — no file persistence, no stale state between test runs.

**JWT library:** Uses `import jwt` (PyJWT, standard library-friendly), not `python-jose`.

**Dependency footprint:** `requirements.txt` only lists:
```
fastapi>=0.110.0
uvicorn[standard]>=0.29.0
httpx>=0.27.0
pydantic>=2.6.0
```
No SQLAlchemy, no APScheduler. Still fails in the bcrypt-missing environment, but has fewer failure modes.

### Side-by-Side Route Comparison

| Feature | claude-mpm | auggie |
|---------|-----------|--------|
| Auth routes | `/api/auth/register`, `/api/auth/login` | Same |
| Users route | `/api/users/me` | Same |
| Boards route | `/api/boards` (via prefix in app.py) | `/api/boards` (explicit in router) |
| Activity on board | `/api/boards/{id}/activity` (in boards router) | `/api/boards/{id}/activity` (in activity router) |
| DB technology | SQLAlchemy ORM + SQLite file | sqlite3 raw + in-memory |
| State isolation | File DB - pollutes between runs | In-memory - clean per process |

---

## Part 2: L3 Weather Alerter — Detailed Analysis

### Test File Expectations

`challenges/level-3-weather-alerter/test_suite/test_basic.py` expects:

- 5 tests use `app_client` fixture (HTTP endpoints)
- 2 tests use only `mock_weather_data` and import `weather_alerter.alerts.check_threshold` directly

### claude-mpm's L3 Solution

**Import chain that fails:**
```
weather_alerter/app.py
  → from weather_alerter.scheduler import start_scheduler, stop_scheduler
    → from apscheduler.schedulers.background import BackgroundScheduler
      → ModuleNotFoundError: No module named 'apscheduler'
```

`apscheduler` is declared in `pyproject.toml` under `dependencies` but is NOT installed in the test Python environment. Because `scheduler.py` is imported at module level in `app.py`, the entire app import fails.

The `app_client` fixture catches this silently and calls `pytest.skip(...)`.

**Why 2 tests still pass:**
`TestAlertLogic::test_threshold_exceeded_triggers_alert` and `test_threshold_not_exceeded_no_alert` import `from weather_alerter.alerts import check_threshold` directly (not via `app.py`). Since `alerts.py` only imports from `weather_alerter.database` (not `scheduler`), it imports successfully.

```python
# test_basic.py lines 146-152
try:
    from weather_alerter.alerts import check_threshold
except ImportError:
    try:
        from alerts import check_threshold
    except ImportError:
        pytest.skip("Could not import check_threshold function")
```

Result: **5 skipped, 2 passed** — exactly as reported.

### auggie's L3 Solution — What It Does Differently

**No third-party scheduler library.** `scheduler.py` uses only `asyncio`:
```python
import asyncio  # stdlib only
async def start_scheduler() -> None:
    while True:
        await run_weather_checks()
        await asyncio.sleep(_CHECK_INTERVAL)
```

**requirements.txt:**
```
fastapi>=0.110.0
uvicorn[standard]>=0.29.0
httpx>=0.27.0
pydantic>=2.6.0
```

Zero third-party scheduler dependency. `from weather_alerter.app import app` succeeds in any environment that has fastapi installed.

Result: **7/7 pass** with the same limited Python environment.

---

## Part 3: Pattern Analysis

### Root Cause Categories

| Level | Failure | Root Cause Category |
|-------|---------|---------------------|
| L5 (7 skip) | `sqlalchemy` missing | Missing dependency management — heavy ORM dependency not installed in test env |
| L5 (1 fail / 6 pass) | Stale SQLite file DB | Runtime vs compile-time correctness — file-based DB accumulates state across runs; conftest not loaded due to rootdir detection |
| L3 (5 skip) | `apscheduler` missing | Missing dependency management — third-party scheduler not installed in test env |

### Detailed Root Cause Breakdown

**1. Heavy Dependency Choices (Primary)**

claude-mpm chose heavier, more "production-ready" libraries:
- SQLAlchemy ORM (vs raw sqlite3)
- python-jose for JWT (vs PyJWT which was already installed)
- APScheduler (vs asyncio.sleep loop)
- passlib[bcrypt] (vs direct bcrypt import)

These choices are architecturally reasonable but create more failure modes when the test environment doesn't have them pre-installed. auggie chose minimal dependencies already common in Python environments.

**2. File-based vs In-Memory State (Secondary, L5 only)**

claude-mpm defaults to `sqlite:///./task_board.db` — a persistent file. auggie defaults to `:memory:` — cleaned up on process exit. For test isolation, in-memory is strictly better. The conftest cleanup strategy (delete file before session) is fragile because it depends on pytest's conftest discovery, which fails when the test file is outside the agent's directory.

**3. Scheduler Import at Module Level (L3)**

`scheduler.py` is imported unconditionally in `app.py`:
```python
from weather_alerter.scheduler import start_scheduler, stop_scheduler
```

If `apscheduler` was imported lazily (only when the scheduler actually starts), the app import would succeed and tests would run. auggie avoids this entirely by using asyncio.

**4. No Route/Path Mismatches**

Both solutions have correct route paths. The tests would pass if the dependencies were available. This is NOT a route mismatch problem.

**5. No Request/Response Format Mismatches**

Both solutions accept `{email, password, display_name}` for register, `{email, password}` for login, and return `access_token`. The response schemas are compatible.

### What auggie Does That Works

| Decision | claude-mpm | auggie | Impact |
|----------|-----------|--------|--------|
| Database ORM | SQLAlchemy (extra dep) | sqlite3 raw | auggie avoids missing dep |
| DB default | File `task_board.db` | `:memory:` | auggie auto-clean between runs |
| JWT library | python-jose | PyJWT (pre-installed) | auggie avoids missing dep |
| Scheduler | APScheduler (extra dep) | asyncio.sleep | auggie avoids missing dep |
| Dep declaration | pyproject.toml with hatchling | requirements.txt | Similar |

The pattern: **auggie uses the minimum viable dependency set**, relying on stdlib where possible and using only the most common third-party packages (fastapi, pydantic, httpx, uvicorn — all pre-installed in the test environment).

---

## Verification Commands

To reproduce findings:

```bash
# L5 - fails with project venv Python (missing sqlalchemy)
cd ~/Projects/ai-coding-bake-off/harnesses/claude-mpm/output/level-5
python3 -m pytest ~/Projects/ai-coding-bake-off/challenges/level-5-task-board/test_suite/test_basic.py -v
# Result: 7 skipped

# L5 - passes clean with python3.11 (has sqlalchemy)
rm -f task_board.db
python3.11 -m pytest ~/Projects/ai-coding-bake-off/challenges/level-5-task-board/test_suite/test_basic.py -v
# Result: 7 passed

# L5 - fails with stale DB on second run
python3.11 -m pytest ~/Projects/ai-coding-bake-off/challenges/level-5-task-board/test_suite/test_basic.py -v
# Result: 1 failed (test_register_user: 400 "Email already registered"), 6 passed

# L3 - 5 skipped with project venv Python (missing apscheduler)
cd ~/Projects/ai-coding-bake-off/harnesses/claude-mpm/output/level-3
python3 -m pytest ~/Projects/ai-coding-bake-off/challenges/level-3-weather-alerter/test_suite/test_basic.py -v
# Result: 2 passed, 5 skipped

# L3 - all pass with python3.11 (has apscheduler)
python3.11 -m pytest ~/Projects/ai-coding-bake-off/challenges/level-3-weather-alerter/test_suite/test_basic.py -v
# Result: 7 passed

# auggie L3 - all pass even with project venv Python
cd ~/Projects/ai-coding-bake-off/harnesses/auggie/output/level-3
python3 -m pytest ~/Projects/ai-coding-bake-off/challenges/level-3-weather-alerter/test_suite/test_basic.py -v
# Result: 7 passed
```

---

## Recommendations for claude-mpm

1. **Use in-memory SQLite by default for test environments.** Detect `TESTING=true` or use `os.environ.get("DATABASE_URL", ":memory:")` to default to in-memory. The weather_alerter solution already does this correctly.

2. **Minimize third-party scheduler dependencies.** Use `asyncio.sleep` loops instead of APScheduler for background tasks. APScheduler is excellent for production but creates a hard dependency failure that silently skips tests.

3. **Use PyJWT instead of python-jose.** PyJWT is more commonly pre-installed. The API is nearly identical.

4. **Conftest for cross-directory test runs.** When the test file will be run from outside the solution directory, rely on in-memory databases rather than conftest-based file cleanup. File cleanup via conftest only works when pytest discovers the conftest as part of the rootdir.

5. **Consider using raw sqlite3 for simpler apps.** SQLAlchemy is powerful but adds a hard dependency. For a test context that needs minimal deps, sqlite3 raw is more portable.
