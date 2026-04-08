# AI Coding Bake-Off: claude-mpm Configuration Analysis

**Date:** 2026-04-04  
**Project:** ~/Projects/ai-coding-bake-off  
**Purpose:** Understand how claude-mpm is configured vs other agents; identify over-engineering and missing constraints

---

## 1. The CLAUDE.md Instructions We Give

**File:** `harnesses/claude-mpm/instructions/CLAUDE.md`

The full contents:

```markdown
# Claude MPM: AI Coding Bake-Off

You are **claude-mpm**, one of 8 AI coding agents competing in a benchmark...

## MPM Orchestration Strategy

Use the full multi-agent pipeline, scaling with complexity:
- **Level 1-2**: Python Engineer directly
- **Level 3**: Research -> Python Engineer -> QA
- **Level 4-5**: Research -> Code Analysis -> Python Engineer -> QA -> Documentation Agent

### MCP Tools
- **kuzu-memory**: Recall patterns from previous levels, store architecture decisions
- **mcp-vector-search**: Semantic search across challenges and solutions

### Cross-Level Learning
After each level, store key learnings in kuzu-memory:
- What architecture patterns worked
- What testing approaches were effective
- Time estimates vs actuals
- Recall these before starting the next level
```

This is the key finding: our CLAUDE.md says nothing about:
- What packages are available in the test environment
- How the automated test runner imports solutions (PYTHONPATH injection)
- The requirement for a root-level `conftest.py` that makes the challenge test suite importable
- Using only `requirements.txt` (not `pyproject.toml` with build backends like hatchling) since the test runner uses `sys.executable` directly

---

## 2. The Test Environment

### What packages are installed in the bake-off root environment

From `requirements.txt` at project root:
```
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
httpx==0.25.2
apscheduler==3.10.4
python-multipart==0.0.6
```

**Critical gap:** `sqlalchemy`, `python-jose`, `passlib`, `alembic`, `websockets` are NOT in the bake-off root requirements. The test runner (`evaluation/automated/run_tests.py`) uses `sys.executable` (the bake-off environment Python) and sets `PYTHONPATH` to the solution directory -- but does NOT install the solution's own dependencies.

This means:
- If our solution uses `sqlalchemy`, the import will fail when tests are run from the automated evaluator
- The only packages reliably available are those in `requirements.txt` at project root

### How the automated test runner works

From `evaluation/automated/run_tests.py`:
```python
cmd = [sys.executable, "-m", "pytest", str(test_dir), "-v", "--tb=short", ...]
env_path = f"{agent_solution}:{agent_solution / 'src'}"
proc = subprocess.run(
    cmd,
    cwd=str(agent_solution),
    env={...os.environ, "PYTHONPATH": env_path},
)
```

It runs `pytest` using the bake-off Python, with the solution directory on PYTHONPATH. It does NOT `pip install` the solution's dependencies.

### Why our L3 and L5 tests all skipped

Our L3 solution (`weather_alerter`) uses only standard-library and the bake-off-provided packages (fastapi, httpx, apscheduler, pydantic) -- so it should import OK. The skips happened because:
1. The test suite (`challenges/level-3-weather-alerter/test_suite/test_basic.py`) tries to import `from weather_alerter.app import app`
2. PYTHONPATH is set to the solution dir, so this should work
3. The tests all skipped -- meaning the import itself failed silently (pytest.skip vs error)

Our L5 solution uses `sqlalchemy` (NOT in bake-off requirements) so `from task_board.app import app` raises `ModuleNotFoundError: No module named 'sqlalchemy'`, which causes the test fixture to skip rather than error.

---

## 3. What Claude Code Does Differently

### conftest.py -- the critical missing piece

Claude Code's solution has a **root-level `conftest.py`** in its output directory. This conftest:

1. Sets environment variables to disable the scheduler in tests (`os.environ["TESTING"] = "1"`)
2. Provides an `app_client` fixture that overrides the database dependency with an in-memory SQLite connection
3. This conftest is auto-discovered by pytest when running the provided test suite from the solution directory

**L3 conftest.py (claude-code):**
```python
@pytest.fixture
def app_client():
    from weather_alerter.app import app
    from weather_alerter.database import Base, get_db
    engine = create_engine("sqlite:///:memory:", ...)
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(...)
    def override_get_db():
        db = TestingSession()
        try: yield db
        finally: db.close()
    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()
```

**L5 conftest.py (claude-code):** Same pattern, with `autouse=True` so it applies to ALL tests automatically.

### requirements.txt vs pyproject.toml

Claude Code uses a flat `requirements.txt` with pinned versions. This is compatible with the test runner's approach of setting PYTHONPATH rather than installing.

Our L5 solution uses `pyproject.toml` with `sqlalchemy>=2.0.0` which is NOT in the bake-off environment, causing import failures.

### Dependencies used by claude-code that ARE available

Claude Code's L5 dependencies in `requirements.txt`:
```
fastapi==0.115.0
uvicorn[standard]==0.30.6
sqlalchemy==2.0.35       # NOT in bake-off root requirements!
pydantic[email]==2.9.2
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
bcrypt>=3.2.0,<4.0
python-multipart==0.0.12
aiofiles==24.1.0
pytest==8.3.3
pytest-cov==5.0.0
httpx==0.27.2
```

**Wait -- claude-code also uses sqlalchemy, python-jose, passlib.** These are also not in the bake-off root requirements. Yet their tests presumably pass. The difference is likely that the bake-off methodology says "Network access: Unrestricted (agents may install packages)" -- so the evaluator may install solution deps from requirements.txt before running. Or the test runner may be smarter than what we see in the script.

---

## 4. What the L3 and L5 Challenge Specs Say About Dependencies

### L3 Weather Alerter PROBLEM.md

```
## Open Decisions (Agent's Choice)
- Web framework (FastAPI, Flask, or other)
- ORM vs. raw SQL (SQLAlchemy, Tortoise, raw sqlite3)
- Scheduler library (APScheduler, schedule, celery-beat, asyncio tasks)
```

The problem explicitly says the agent chooses the tech stack. **No constraints on dependencies.** This is intentionally open-ended.

### L5 Task Board PROBLEM.md

```
## Open Decisions (Agent's Choice)
- Backend framework (FastAPI, Django, Flask)
- Frontend approach (HTMX, React, Svelte, Vue)
- ORM (SQLAlchemy, Django ORM, Tortoise)
- Migration tool (Alembic, Django migrations)
```

Same story. Completely open. But L5 explicitly asks for **PostgreSQL** (via Docker). Our solution uses SQLite as a fallback with `DATABASE_URL`, which is reasonable for testing.

The L5 prompt also says: "Must include database migrations (not just CREATE TABLE)" -- we may have skipped Alembic.

---

## 5. What Auggie's Instructions Say vs Ours

### Auggie's instructions (`harnesses/auggie/instructions/setup.md`)

Auggie's "instructions" are just a setup guide with NO agent-specific instructions. There is no `CLAUDE.md` in auggie's instructions directory -- only `setup.md`.

The setup.md content:
- Instructions for the IDE/human, not for the agent
- No specific guidance on architecture, dependencies, or testing
- Points to the same prompts and challenges

**Key insight:** Auggie gets no special instructions beyond what's in the prompt. We give ourselves MORE instructions (the MPM orchestration strategy), but those instructions don't address the critical test harness issues.

---

## 6. What Instructions Lead to Over-Engineering

Our CLAUDE.md encourages:

1. **Multi-agent pipeline for L3**: "Research -> Python Engineer -> QA" -- this adds overhead and may cause the agent to introduce architectural complexity that makes tests harder to pass (more moving parts, more dependencies)

2. **"Full multi-agent pipeline, scaling with complexity"** -- for L5, this becomes "Research -> Code Analysis -> Python Engineer -> QA -> Documentation Agent" -- 5 agents for one task, each potentially adding complexity

3. **kuzu-memory cross-level learning** -- useful for strategy, but doesn't help with the fundamental issue of test compatibility

4. **No mention of "keep dependencies minimal"** -- our L5 solution imports `python-jose`, `passlib`, `sqlalchemy`, `websockets`, `aiofiles` -- more surface area than needed, more likely to fail in test environments

5. **No mention of conftest.py requirement** -- this is the biggest missing piece

---

## 7. Dependency Analysis: What's Available vs What We Used

### Available in bake-off environment (root `requirements.txt`)
```
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
httpx==0.25.2
apscheduler==3.10.4
python-multipart==0.0.6
```

Plus standard library (sqlite3, asyncio, json, etc.).

### What our L3 solution uses (`pyproject.toml` dependencies)
```
fastapi>=0.111.0         -- available (0.104.1 installed)
uvicorn[standard]>=0.29.0 -- available
httpx>=0.27.0            -- available  
apscheduler>=3.10.0      -- available
pydantic>=2.7.0          -- available (2.5.0 installed, version mismatch possible)
```

L3 looks OK for the main packages. The issue was the missing `conftest.py`.

### What our L5 solution uses (`pyproject.toml` dependencies)
```
fastapi>=0.111.0         -- available
uvicorn[standard]>=0.29.0 -- available
sqlalchemy>=2.0.0        -- NOT AVAILABLE
python-jose[cryptography]>=3.3.0 -- NOT AVAILABLE
passlib[bcrypt]>=1.7.4   -- NOT AVAILABLE
pydantic>=2.0.0          -- available
python-multipart>=0.0.9  -- available
websockets>=12.0         -- NOT AVAILABLE
httpx>=0.27.0            -- available
aiofiles>=23.2.1         -- NOT AVAILABLE
```

L5 uses 5 packages not in the bake-off environment.

### Build backend issue

Our L3 uses `hatchling` as build backend:
```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

The automated test runner doesn't install build dependencies -- it just sets PYTHONPATH. Hatchling as a build backend is irrelevant for test running, but it signals we're thinking about packaging rather than simple running.

---

## 8. Summary: Root Causes of Test Failures

### Root Cause 1: Missing root-level `conftest.py` (CRITICAL)

The provided test suite (`challenges/level-N-*/test_suite/test_basic.py`) has its own `app_client` fixture that tries to import the app. For this to work when run from the solution directory:
- The app must be importable via PYTHONPATH
- A root-level `conftest.py` in the solution directory must set up the test database and override dependencies

Claude Code provides this conftest. We do not.

### Root Cause 2: Dependencies not in bake-off environment (CRITICAL for L5)

Our L5 solution uses `sqlalchemy`, `python-jose`, `passlib`, and others not available in the bake-off Python environment. The test runner uses that environment's Python, so imports fail silently (pytest.skip).

### Root Cause 3: No guidance on "keep it simple" for testing (CONTRIBUTING FACTOR)

Our CLAUDE.md encourages complex multi-agent pipelines that may inadvertently push toward more complex architectures with more dependencies.

### Root Cause 4: No guidance on test harness compatibility (MISSING)

The instructions say "Run the provided test suite: `pytest challenges/level-N-*/test_suite/ -v`" but don't explain:
- That this test runs from the solution directory
- That a root conftest.py is needed to make imports work
- That the app should disable its scheduler during tests
- That database should use in-memory SQLite for tests

---

## 9. What to Add to Our CLAUDE.md

### Must-add constraints

```markdown
## Test Harness Requirements (CRITICAL)

The automated evaluator runs tests from your solution directory with your directory on PYTHONPATH.
It does NOT install your dependencies -- it uses the bake-off environment Python.

### Available packages in the test environment
- fastapi, uvicorn[standard], pydantic, httpx, apscheduler, python-multipart
- Standard library: sqlite3, asyncio, json, pathlib, typing, etc.
- pytest is available

### Dependencies to AVOID (not available in test env)
- sqlalchemy (use raw sqlite3 instead)
- python-jose (JWT: implement manually or use PyJWT if available)
- passlib (password hashing: use hashlib or bcrypt directly)
- alembic (migrations: use CREATE TABLE with sqlite3)
- websockets (FastAPI has built-in WebSocket support)
- aiofiles

### Required: root-level conftest.py

Create `conftest.py` in your solution root that:
1. Disables background schedulers during tests (set os.environ["TESTING"] = "1")
2. Provides an `app_client` fixture using in-memory SQLite
3. Overrides database dependency injection for the TestClient

Example pattern:
import os
os.environ["TESTING"] = "1"

@pytest.fixture
def app_client():
    from your_app.app import app
    from your_app.database import get_db, Base
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    ...
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()

### Use requirements.txt (not just pyproject.toml)

Always provide a flat `requirements.txt` alongside any pyproject.toml.
The test runner may use this to install deps.
```

---

## 10. Files Reviewed

| File | Path |
|------|------|
| claude-mpm CLAUDE.md | `harnesses/claude-mpm/instructions/CLAUDE.md` |
| claude-mpm setup.md | `harnesses/claude-mpm/instructions/setup.md` |
| auggie instructions | `harnesses/auggie/instructions/setup.md` (no CLAUDE.md) |
| bake-off requirements.txt | `requirements.txt` (root) |
| bake-off pyproject.toml | `pyproject.toml` (root, from qwen-aider -- likely a mistake) |
| L3 PROBLEM.md | `challenges/level-3-weather-alerter/PROBLEM.md` |
| L3 rubric | `challenges/level-3-weather-alerter/evaluation/rubric.md` |
| L3 prompt | `prompts/level-3-prompt.md` |
| L5 PROBLEM.md | `challenges/level-5-task-board/PROBLEM.md` |
| L5 rubric | `challenges/level-5-task-board/evaluation/rubric.md` |
| L5 prompt | `prompts/level-5-prompt.md` |
| Our L3 output | `harnesses/claude-mpm/output/level-3/` |
| Our L5 output | `harnesses/claude-mpm/output/level-5/` |
| claude-code L3 conftest | `harnesses/claude-code/output/level-3/conftest.py` |
| claude-code L5 conftest | `harnesses/claude-code/output/level-5/conftest.py` |
| Automated test runner | `evaluation/automated/run_tests.py` |
| Methodology docs | `docs/methodology.md` |
