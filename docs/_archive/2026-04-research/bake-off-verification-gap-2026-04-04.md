# Bake-Off Verification Gap Analysis: claude-mpm

**Date:** 2026-04-04
**Project:** ~/Projects/ai-coding-bake-off
**Scope:** Understanding why claude-mpm's test results show failures at levels 3 and 5

---

## Executive Summary

The CLAUDE.md instructions DO explicitly tell the agent to run pytest and verify imports. The agent CAN run code. The agent FAILED to catch critical import failures at levels 3 and 5. The verification gap is not "no instruction to verify" — it's that the QA agent or Python Engineer agent ran tests in the wrong environment (their own venv where forbidden packages were installed), not in the bare test harness environment.

---

## 1. What CLAUDE.md Says About Testing and Verification

The CLAUDE.md at `/Users/masa/Projects/ai-coding-bake-off/harnesses/claude-mpm/instructions/CLAUDE.md` is highly explicit about verification. Key passages:

### Direct test execution instructions (line 152-155):
```
4. **After implementation**: Run `PYTHONPATH=. pytest challenges/level-{N}-*/test_suite/test_basic.py -v` and fix all failures before marking done
```

### Pre-Implementation Checklist (lines 188-204):
- "Read the test file first" — before writing implementation
- "Verify package constraints: Every import must be from the available packages list"
- "After implementation: Run `PYTHONPATH=. pytest challenges/level-{N}-*/test_suite/test_basic.py -v` and fix all failures before marking done"

### Import chain validation (lines 124-133):
```
Before declaring done, mentally trace:
app.py → all imports → all sub-imports → must all resolve with available packages
```

### Forbidden packages section (lines 99-110):
Explicitly lists sqlalchemy, python-jose, passlib, bcrypt, alembic, websockets, aiofiles as FORBIDDEN. States these will cause import failures.

**Conclusion: The instruction to run tests is present, explicit, and prominent. The CLAUDE.md says to run pytest AND verify imports.**

---

## 2. Can Agents Execute Code in This Bake-Off?

**Yes, absolutely.** Evidence:

1. The methodology doc states: "Available tools: git, docker, docker-compose, pip, pytest" and "Network access: Unrestricted (agents may install packages, access docs)"

2. The CLAUDE.md itself provides exact pytest commands to run

3. Level-2 output has `.pytest_cache/` directory, `.venv/` directory, and `uv.lock` — the agent clearly ran tests and installed packages

4. The `settings.local.json` shows the Claude Code environment has Bash tool access (the MPM hooks confirm tool execution is enabled)

5. There are no restrictions on code execution anywhere in the bake-off rules or methodology

**Conclusion: Agents are fully expected and able to run pytest, python, and shell commands.**

---

## 3. Actual Test Results — Where claude-mpm Failed

Running the official evaluation harness (`evaluation/automated/run_tests.py`):

| Agent | L1 | L2 | L3 | L4 | L5 |
|-------|----|----|----|----|-----|
| **claude-mpm** | 10/10 | 7/7 | **0/0** | 8/8 | **0/0** |
| auggie | 10/10 | 7/7 | 7/7 | 8/8 | 0/0 |
| warp | 10/10 | 7/7 | 7/7 | 8/8 | 0/0 |
| claude-code | 10/10 | 7/7 | 0/0 | 8/8 | 0/0 |

"0/0" means no tests ran — the app couldn't be imported.

**Level 3 failure:** `weather_alerter/app.py` imports `apscheduler.schedulers.background.BackgroundScheduler`. apscheduler IS in the allowed packages list (line 93 of CLAUDE.md). But the test harness doesn't have it installed in the system Python environment. The agent must have installed it in a local venv, run tests successfully there, and declared done without realizing the bare-environment test harness couldn't import it.

Wait — actually apscheduler IS listed as allowed:
```
apscheduler==3.10.4
```
The import failure `No module named 'apscheduler'` means apscheduler is not installed in the EVALUATION ENVIRONMENT, even though CLAUDE.md says it's available. This suggests CLAUDE.md's list of "available packages" refers to what's installed in the challenge test harness during judging — and the agent ran its tests in a local venv that had more packages, not fewer.

**Level 5 failure:** `task_board/database.py` imports `sqlalchemy.create_engine`. SQLAlchemy is explicitly FORBIDDEN in CLAUDE.md (lines 100-101). The agent used it anyway, indicating it either:
- Ignored the forbidden packages list
- The QA agent ran tests in a venv where sqlalchemy was installed
- The agent confused the level-5 prompt's "PostgreSQL" requirement with needing sqlalchemy

---

## 4. Root Cause: The Environment Mismatch Problem

The core issue is a **two-environment gap**:

1. **Agent's working environment:** Has a venv with uv/pip where forbidden packages CAN be installed. Tests pass here.
2. **Evaluation harness environment:** Uses the system Python with only the specific listed packages. Tests fail here.

Evidence this happened:
- Level-2 output has `.venv/` directory with setuptools, pytest, etc. installed
- Level-3 has `uv.lock` — the agent ran `uv sync` or similar
- Level-5 has `uv.lock` and `pyproject.toml` listing sqlalchemy as a dependency

The agent (likely the Python Engineer sub-agent) created its own virtual environment, installed all needed packages, ran tests in THAT environment, saw them pass, and declared done. The QA agent would also run tests in the same venv. Neither checked if the code would import in a bare environment.

**The verification step was done — but in the wrong environment.**

---

## 5. Comparison: How auggie and warp Avoided This

**auggie at level-3:** Passed all 7 tests. Import check confirms `weather_alerter.app` imports cleanly without apscheduler issues. Auggie's implementation doesn't use BackgroundScheduler at the module level OR uses it in a way that doesn't fail on import.

**warp at level-3:** All tests skipped (app not importable). warp structured their code in `src/` — the test harness uses `PYTHONPATH=harnesses/warp/output/level-3` not `.../level-3/src`.

**Neither auggie, warp, codex, nor claude-code has verification-specific instructions** in their harness instructions (auggie/setup.md, warp/setup.md, codex/AGENTS.md are all minimal — they just say "run pytest" in step 5 of the level instructions, identical to what claude-mpm says). The harness instructions ARE the same for all agents.

The difference: auggie's solution for level-3 simply didn't have the import-time dependency issue. It's architectural, not process-related.

---

## 6. The Level-5 Prompt Conflict

A structural problem exists: the level-5 prompt explicitly says:
```
- [ ] PostgreSQL with migrations and seed data
```

But CLAUDE.md says SQLAlchemy is forbidden. These two instructions are in direct conflict. The agent followed the prompt (SQLAlchemy + PostgreSQL) rather than the package constraint in CLAUDE.md.

This is a **genuine ambiguity** that reasonable agents could fail on. The CLAUDE.md package constraint section was not written with level-5's PostgreSQL requirement in mind — or the intent was to use raw `psycopg2` rather than SQLAlchemy. Almost all agents (auggie, claude-code, warp, codex) also failed level-5.

---

## 7. Was the QA Agent Actually Run?

The AGENT_DELEGATION.md specifies:
- Level 3: Research → Engineer → QA
- Level 4-5: Research → Code Analysis → Engineer → QA → Docs

The correlation file at level-5 contains only one entry (a Bash tool call). No session transcript exists to confirm QA was delegated. However:

- The metadata.json at level-5 lists `sqlalchemy` as a dependency — if QA had run the tests in the bare environment and seen the import fail, the dependency would have been removed
- The presence of `conftest.py` in the output directory (which CLAUDE.md explicitly warns about) suggests the agent added a conftest.py that would NOT be discovered by the harness

**Inference:** QA likely ran tests in the agent's venv and saw them pass. QA did NOT run the exact command specified in CLAUDE.md (`PYTHONPATH=. pytest challenges/level-{N}-*/test_suite/test_basic.py -v` from the project root).

---

## 8. Key Findings

### What the instructions say:
- Run pytest with the exact PYTHONPATH command from the project root
- Verify import chains before declaring done
- Use only the listed packages (sqlalchemy, python-jose, passlib are FORBIDDEN)

### What actually happened:
1. **Levels 1, 2, 4:** Verification worked correctly. All tests pass.
2. **Level 3:** Agent ran tests in its own venv, not the bare evaluation environment. Tests passed locally. Import fails in evaluation (apscheduler not installed system-wide, OR the package is available but the test harness module-level import has a different issue).
3. **Level 5:** Agent used forbidden packages (sqlalchemy, python-jose, passlib). Either ignored the constraint or the level-5 "PostgreSQL" requirement in the prompt overrode the package constraint.

### Why the agent CAN run pytest but still got it wrong:
The agent ran pytest — just not the RIGHT pytest command. It ran tests in its local project directory with its own venv, not from the project root with `PYTHONPATH=harnesses/claude-mpm/output/level-N`. This is the critical distinction the CLAUDE.md tries to enforce but the agent missed.

---

## 9. Recommendations for Fixing the Gap

1. **Add explicit environment isolation check to CLAUDE.md**: Require testing with `python3 -c "import sys; sys.path.insert(0, 'harnesses/claude-mpm/output/level-N'); from package.app import app"` before declaring done.

2. **Add a verification script**: Create `harnesses/claude-mpm/scripts/verify.sh` that runs all tests exactly as the evaluation harness does.

3. **Clarify the level-5 PostgreSQL vs. SQLAlchemy conflict**: Either update the level-5 prompt to say "SQLite (not PostgreSQL)" or add a note in CLAUDE.md that level-5 should use raw `sqlite3` despite the "PostgreSQL" language in the prompt.

4. **Add QA agent instruction to test in bare environment**: "Run tests WITHOUT activating any venv, using the system Python from the project root."

5. **Flag forbidden package usage in QA checklist**: Before running tests, grep the source for `import sqlalchemy`, `import jose`, `import passlib`, etc.

---

## 10. Answer to the Key Question

**Can our agent run pytest or python during the challenge to verify its own work?**
**Yes, fully and without restriction.**

**Why isn't it doing that correctly?**
The agent IS running pytest — but in the wrong environment (its own venv) rather than the bare system environment that the evaluation harness uses. The CLAUDE.md instructions tell it to run the right command (`PYTHONPATH=. pytest challenges/...`) but the QA agent or Python Engineer ran tests in a local `uv` environment instead.

For level-5 specifically, the agent also violated the forbidden packages constraint (sqlalchemy), likely because the level-5 prompt explicitly says "PostgreSQL" and the agent prioritized the prompt over the CLAUDE.md constraint.

---

## Files Referenced

- `/Users/masa/Projects/ai-coding-bake-off/harnesses/claude-mpm/instructions/CLAUDE.md`
- `/Users/masa/Projects/ai-coding-bake-off/harnesses/claude-mpm/instructions/.claude-mpm/AGENT_DELEGATION.md`
- `/Users/masa/Projects/ai-coding-bake-off/harnesses/claude-mpm/output/level-3/weather_alerter/app.py`
- `/Users/masa/Projects/ai-coding-bake-off/harnesses/claude-mpm/output/level-5/task_board/database.py`
- `/Users/masa/Projects/ai-coding-bake-off/evaluation/automated/run_tests.py`
- `/Users/masa/Projects/ai-coding-bake-off/evaluation/results/AGGREGATE-SCORES.md`
- `/Users/masa/Projects/ai-coding-bake-off/docs/methodology.md`
- `/Users/masa/Projects/ai-coding-bake-off/prompts/level-5-prompt.md`
