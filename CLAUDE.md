# Claude MPM Project

Claude Multi-Agent Project Manager - Orchestrate Claude with agent delegation and ticket tracking.

## Project Information
- **Language**: Python
- **Framework**: FastAPI

## Publishing Workflow

**CRITICAL**: Always use the Makefile targets for releases:

```bash
# 1. Ensure correct GitHub account is active
claude-mpm gh switch  # Switches to bobmatnyc per .gh-account

# 2. Create release (bump version and build)
make release-patch    # For bug fixes (5.9.x → 5.9.y)
make release-minor    # For new features (5.9.x → 5.10.0)
make release-major    # For breaking changes (5.x.x → 6.0.0)

# 3. Publish to all platforms (PyPI, Homebrew, npm, GitHub)
make release-publish
```

## Running Testcases Workflow
**CRITICAL**: Preferably use `-n auto` pytest argument to leverage all available CPU cores for faster test execution when running the full test suite.
Use `-p no:xdist` pytest argument when debugging flaky or order-dependent tests, as parallelization can obscure root causes.
Tests are run via `uv run pytest`, to ensure correct virtual environment activation.

### Run All Tests
This uses uv run pytest with xdist parallelization causing tests to run concurrently.
```bash
make test
```

**DO NOT**:
- Manually edit version files
- Call `./scripts/publish_to_pypi.sh` directly
- Publish with wrong GitHub account (must be bobmatnyc, not bob-duetto)

The Makefile orchestrates the complete release workflow: syncs repositories, publishes to all platforms, creates GitHub releases.
