# AI Coding Bake-Off: Verification Infrastructure Analysis

**Date:** 2026-04-04
**Project:** ~/Projects/ai-coding-bake-off
**Research Focus:** Verification scripts, test structure, scoring methodology, failure causes

---

## 1. How Verification Works

### Primary Tool: pytest

All verification is done via pytest. There are two runner scripts:

**`evaluation/automated/run_verifiers.py`** (canonical runner used for official results)
- Iterates all 8 agents × 5 levels
- For each combo: runs `pytest challenges/level-{N}-*/test_suite/test_basic.py -v --tb=short`
- Sets PYTHONPATH to `harnesses/{agent}/output/level-{N}/` and optionally `src/` subdirectory
- Times each run with 60-second timeout
- Parses pytest output via regex to extract passed/failed/error counts
- Writes `evaluation/results/verification-results.csv` and `VERIFICATION-RESULTS.md`

**`evaluation/automated/run_tests.py`** (secondary runner)
- Same approach but with 120-second timeout
- Writes `evaluation/results/test_results.json`
- Converts pass rate to 1-5 score scale

### Test Discovery Path

```
challenges/level-{N}-{name}/test_suite/test_basic.py
```

The test file is the ONLY automated test run against agent solutions. It uses a single shared fixture file where needed.

### Scoring Scale (run_tests.py)

| Pass Rate | Score |
|-----------|-------|
| >= 95% | 5.0 |
| >= 80% | 4.0 |
| >= 60% | 3.0 |
| >= 40% | 2.0 |
| < 40% | 1.0 |

---

## 2. What "Pass Rate" Means

**"Pass rate" = passed / (passed + failed + errors)**

- Skipped tests are EXCLUDED from the denominator
- The VERIFICATION-RESULTS.md documents this explicitly: "passed/collected — skipped tests excluded from denominator"
- This is critical: when claude-mpm gets "2/2" on Level 3, that means 2 passed out of the 2 that actually ran (5 were skipped because the app client couldn't be imported)

**The 83% calculation for claude-mpm:**
- L1: 10/10, L2: 7/7, L3: 2/2, L4: 9/9, L5: 1/7
- Total: 29 passed / 35 run = 83%
- The 5 Level 3 skips are excluded from the 35

---

## 3. Test Structure: What Each Level Tests

### Level 1 - Table Formatter (10 tests)
File: `challenges/level-1-table-formatter/test_suite/test_basic.py`

Tests import `table_formatter` as a Python module and call it via subprocess:
```
python -m table_formatter <csv_path> [--output <file>] [--sort <col>]
```

Tests:
- `TestBasicFormatting`: 4 tests — valid markdown output, column count, data rows, numeric right-alignment
- `TestEdgeCases`: 4 tests — unicode, edge cases, empty CSV, nonexistent file
- `TestCLIOptions`: 2 tests — `--output` flag, `--sort` flag

**What causes FAIL:** Module not importable via PYTHONPATH (qwen-aider hit this: "No module named table_formatter")

### Level 2 - Git Log Analyzer (7 tests)
File: `challenges/level-2-git-analyzer/test_suite/test_basic.py`

Tests import directly from `git_analyzer.parser` and `git_analyzer.metrics`:
- `TestLogParsing`: 4 tests — commit count, author names, dates, insertions/deletions
- `TestMetrics`: 3 tests — author commit counts, bus factor, weekend detection

**What causes FAIL:** Module import errors, wrong data parsing logic. Tests use a fixed fixture file (`fixtures/sample_git_log.txt`) with 10 known commits and 4 known authors.

### Level 3 - Weather Alerter (7 tests, but 5 can skip)
File: `challenges/level-3-weather-alerter/test_suite/test_basic.py`

Two separate test categories:
1. **API tests (5 tests)**: Require an importable `app_client` fixture — tries FastAPI `TestClient` then Flask `test_client`. If import fails, **silently skips** with "Could not create test client."
   - `TestHealthCheck`, `TestCityCRUD` (3), `TestThresholds` (1)

2. **Logic tests (2 tests)**: Import `weather_alerter.alerts.check_threshold` directly — no app needed
   - `TestAlertLogic`: threshold exceeded/not exceeded

**What causes PARTIAL (2/2 with 5 skipped):** App not importable — likely missing dependencies (sqlalchemy, etc.) not installed in the test environment.

### Level 4 - Document Pipeline (9 tests, codex got 2 skipped)
File: `challenges/level-4-doc-pipeline/test_suite/test_basic.py`

Tests import from `doc_pipeline.*`:
- `TestTextExtraction`: 3 tests — `.txt`, `.pdf`, unsupported type
- `TestNLPProcessing`: 3 tests — entity extraction, key phrases, summary
- `TestPipelineArchitecture`: 2 tests — `PipelineStage` interface, `Pipeline.process()`
- `TestSearchIndexing`: 1 test — `SearchIndex` add + search

Several tests use `pytest.skip` if their target module doesn't exist, making them "gracefully skip."

### Level 5 - Task Board (7 tests)
File: `challenges/level-5-task-board/test_suite/test_basic.py`

All 7 tests require an importable app:
- `app_client` fixture: tries `from task_board.app import app` (FastAPI), then `create_app` (Flask), then Django Client. If all fail, `pytest.skip()`.
- `auth_headers` fixture: depends on `app_client` — registers + logs in a user, returns JWT headers.

Tests:
- `TestAuth`: 3 tests — register, login (token), protected endpoint
- `TestBoardCRUD`: 2 tests — create board, list boards
- `TestTaskCRUD`: 1 test — create task
- `TestActivityLog`: 1 test — activity log on board creation

**Critical note:** `auth_headers` calls `app_client.post("/api/auth/register", ...)` then `post("/api/auth/login", ...)`. If auth fails, the `auth_headers` fixture fails, which causes ALL tests depending on it to ERROR (shown as "setup errors" for claude-code L5).

---

## 4. How claude-mpm Is Configured

### Harness Location
`harnesses/claude-mpm/instructions/CLAUDE.md`

### Instructions Summary
The agent is given a CLAUDE.md system-prompt with:
- Role: "claude-mpm, one of 8 AI coding agents competing in a benchmark"
- Phase 1: Solve 5 challenges in order (read prompt, read problem, read rubric, build solution, run tests)
- Phase 2: Cross-review all other agents' solutions
- Output directory: `harnesses/claude-mpm/output/level-{N}/`
- Rules: challenges/ is READ-ONLY, Python 3.12+, type hints, tests, docstrings
- Record timing in `metadata.json`

### MPM Orchestration Strategy (from CLAUDE.md)
- Level 1-2: Python Engineer directly
- Level 3: Research → Python Engineer → QA
- Level 4-5: Research → Code Analysis → Python Engineer → QA → Documentation Agent
- MCP tools: kuzu-memory for cross-level learning, mcp-vector-search for semantic search

### No Special System Prompt Beyond CLAUDE.md
The instructions are delivered via the standard CLAUDE.md project instructions mechanism. No additional system prompt file was found. The `harnesses/claude-mpm/instructions/setup.md` exists but is configuration/setup notes.

---

## 5. What Causes Test FAILURES

### Failure Categories

**Category A: Module Import Failure (worst)**
- Symptom: All tests skip OR all tests fail with ModuleNotFoundError
- Cause: Agent puts code in wrong directory structure, or uses a package name the test doesn't expect
- Example: qwen-aider L1 — "No module named table_formatter"
- The test runner sets PYTHONPATH to the solution root and `src/` subdirectory only

**Category B: Missing Dependency (partially imported)**
- Symptom: Some tests skip (those needing app client), but logic tests pass
- Cause: App needs `sqlalchemy`, `fastapi`, etc. not installed in the TEST environment
- Example: claude-mpm L3 — 5 API tests skip, 2 logic tests pass
- Example: claude-mpm L5 — ALL 7 tests skip (sqlalchemy not installed → can't import app)

**Category C: Logic/Implementation Error**
- Symptom: Tests run but assert fails
- Cause: Wrong calculation, wrong field name, wrong HTTP response code
- Example: deepseek-aider L2 — pydantic ValidationError (int_type) in AuthorStats
- Example: warp L5 — 409 Conflict on register (duplicate user from previous test state)

**Category D: Setup/Fixture Error**
- Symptom: Test errors (not failures), shown as "4 setup errors"
- Cause: `auth_headers` fixture fails (auth broken) → all dependent tests error
- Example: claude-code L5 — auth tests fail, then Board/Task/Activity tests all error

### claude-mpm Specific Failures

**Level 3 (2/2, 5 skipped):**
Root cause: The weather_alerter app cannot be imported because dependencies (fastapi, sqlalchemy, or similar) are not installed in the test execution environment. The test runner does NOT install dependencies; it just sets PYTHONPATH. The 2 logic tests (TestAlertLogic) pass because they only import `weather_alerter.alerts.check_threshold` which has lighter dependencies.

**Level 5 (1/7, 6 failed):**
From verification-results.csv notes: "Auth+BoardCRUD+TaskCRUD+ActivityLog failed"
Root cause: The app imports sqlalchemy (`from sqlalchemy import...`) which isn't in the test environment. BUT the result shows 1 passed (not all skipped) — meaning the app DID import somehow, and `test_protected_endpoint_requires_auth` passed (which only checks for 401/403 on `/api/users/me`), but the auth register/login tests fail.

Wait — on fresh run today, all 7 skip. The 1/7 in the CSV was from the official run on 2026-04-03. The conftest.py in the level-5 directory cleans the DB. The current skip state may be due to missing dependencies in the current environment.

**The documented official results (from VERIFICATION-RESULTS.md):**
- L5 claude-mpm: 1 passed (`test_protected_endpoint_requires_auth`), 6 failed (Auth register, Auth login, Board CRUD, Task CRUD, Activity Log)
- This means the app DID import on the official run, but auth endpoints were broken

---

## 6. Scoring Methodology

### Two-Part Scoring System

**Part 1: Automated Verification (this document's focus)**
- pytest pass rate, per level
- Reported as raw counts: passed/total
- NOT directly weighted into the "83% pass rate" article headline — that's a separate calculation

**Part 2: Cross-Agent Peer Review (subjective, 1-5 scale)**
- Each agent reviews all other agents' solutions (blind)
- 8 criteria: Functionality, Correctness, Best Practices, Architecture, Code Reuse/DRY, Testing, Error Handling, Documentation
- Reviews stored as markdown in `evaluation/results/{reviewer}-reviews-{subject}-level-{N}.md`
- 225 total review files parsed
- Aggregated in `evaluation/aggregate_scores.py` → `AGGREGATE-SCORES.md`

### The 83% Pass Rate

**This is the automated test pass rate:**
- claude-mpm: 29 passed out of 35 run (skips excluded)
- 29/35 = 82.8% ≈ 83%

**The 4.74/5.0 score** is the cross-agent peer review average — NOT the automated test score.

### Final Rankings

The article's ranking is based on the **peer review score (4.74)**, not the automated pass rate. The pass rate is a data point used by reviewers to inform their "Correctness" criterion scores.

---

## 7. Key Files

| File | Purpose |
|------|---------|
| `evaluation/automated/run_verifiers.py` | Official verification runner |
| `evaluation/automated/run_tests.py` | Alternative runner with JSON output |
| `challenges/level-{N}-*/test_suite/test_basic.py` | The actual tests (READ-ONLY) |
| `evaluation/results/verification-results.csv` | Official results data |
| `evaluation/results/VERIFICATION-RESULTS.md` | Human-readable results matrix |
| `evaluation/results/AGGREGATE-SCORES.md` | Peer review score aggregation |
| `evaluation/results/RANKING.md` | Final rankings |
| `evaluation/aggregate_scores.py` | Peer review aggregation script |
| `harnesses/claude-mpm/instructions/CLAUDE.md` | Agent system instructions |
| `harnesses/claude-mpm/output/level-{N}/` | Agent solution outputs |

---

## 8. Why We're Losing Points

### Automated Tests: 83% (29/35)

The 6 L5 failures and 5 L3 skips are the problem. The root cause pattern:

**L3 and L5 failures are dependency/import issues**, not logic errors:
- The test runner does not `pip install` dependencies before running tests
- Agents that got full scores (auggie, claude-code, warp on L3; auggie, codex on L5) must have used lighter-dependency implementations OR their dependencies happened to be pre-installed
- claude-mpm used sqlalchemy for L5 and appears to have used heavier deps for L3's app layer

**L5 official run: auth endpoints failed** (not just import errors)
- `test_register_user` failed → `auth_headers` fixture failed → 5 dependent tests cascaded
- Only `test_protected_endpoint_requires_auth` passed (doesn't need auth_headers)

### Peer Review: 4.74/5.0 (Rank 1)

Despite the automated test issues, claude-mpm ranked #1 in peer review due to top scores in Architecture (4.96) and Best Practices (4.87). The Documentation score (4.14) is the biggest gap vs. peers.

---

## 9. Summary

The bake-off uses pytest as the sole automated verification tool. "Pass" means pytest exits with the test assertion passing. "Fail" means assertion failed, import error, or timeout. "Skip" means the test's fixture couldn't be created (usually missing app client). Pass rate = passed/(passed+failed+errors), skips excluded.

The 83% score for claude-mpm comes from 6 L5 failures (auth + CRUD endpoints broken) plus 5 L3 skips (app client not importable). The actual scoring that produced the #1 ranking is the cross-agent peer review (4.74/5.0), which is separate from automated test pass rate.
