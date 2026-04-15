---
description: "Run the test suite"
argument-hint: "[path or pytest flags]"
---

Run the claude-mpm test suite.

If $ARGUMENTS is provided, pass it as additional pytest arguments (e.g., a specific test file path or flags).

Run the tests:
```
uv run pytest -n auto $ARGUMENTS
```

**Tips**:
- Use `-n auto` (default) to parallelize across all CPU cores via pytest-xdist.
- Use `-p no:xdist` instead of `-n auto` when debugging flaky or order-dependent tests.
- Use `-x` to stop on first failure.
- Use `-k "test_name"` to run a specific test by name.
- Use `--cov=src/claude_mpm` to generate a coverage report.

After the run, summarize: total tests, passed, failed, skipped, and any errors.
