# PM Agent Memory

## Delegation Reinforcement

### STRICT DELEGATION RULE (project-specific override)
In this project, the PM delegates ALL code-related tasks to specialist agents, even small ones.

The "trivial edit < 5 lines" exception in PM instructions does NOT apply here.
The user has explicitly requested stricter delegation.

**ALWAYS delegate:**
- Any file read for the purpose of understanding code (delegate to Research)
- Any code/config edit, regardless of size (delegate to python-engineer or engineer)
- Diagnostic/linting fixes (delegate to python-engineer)
- Dependency investigation (delegate to Research)
- Installation/verification logic changes (delegate to python-engineer)

**PM may do directly (narrow exceptions only):**
- Pure git operations: `git status`, `git add`, `git commit`, `git pull`, `git push`, `git log`
- Single-command operational tasks explicitly listed in CLAUDE.md (e.g., `make test`, `make release-patch`)
- Reading ≤ 2 config/docs files purely for orchestration context (not code understanding)

### Pattern: "Small fix visible in diagnostics"
When Pyright/linter diagnostics appear → delegate to python-engineer, do NOT fix directly.
Even if the fix looks like a 1-line change, the PM should not be making code judgments.

### Pattern: "Investigation + Fix"
Research finds root cause → PM delegates fix to python-engineer.
PM never reads code files to understand them and then fixes inline.

### Pattern: "specific pytest invocation = investigation"
`uv run pytest tests/specific_test.py -v` is NOT a single test command.
Running targeted test files is investigation → delegate to python-engineer.
Only `make test` (or CLAUDE.md-documented shortcuts) are allowed direct test commands.
Never use: `uv run pytest tests/specific*.py`, `pytest -k "pattern"`, `pytest --tb=long`

### Pattern: "pre-commit sequencing"
PM must NOT attempt git commit while known lint/test failures exist.
Correct sequence: Delegate fix → Receive confirmation → git add → git commit.
Wrong sequence (commit, get failure, fix, retry) wastes a round-trip and violates the verification chain.

### Pattern: "make commands are operational, not PM work"
ALL make targets → delegate to Local Ops (including make test, make release-*, make build)
PM never runs make directly, even if documented in CLAUDE.md.

### Pattern: "Bash is for git only"
PM's Bash usage is limited to git operations.
Any non-git Bash command (make, pytest, sed, rm, curl) → delegate.

### Pattern: "Read for code understanding = Research"
Using the Read tool to understand code before taking action → delegate to Research.
PM may only Read ≤2 config/docs files for orchestration context (not code comprehension).
If PM reads a .py file to understand it → Circuit Breaker #2 violation.
