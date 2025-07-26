# Claude MPM Scripts

This directory contains executable scripts and tests for Claude MPM.

## Main Scripts

- `claude-mpm` - Main executable wrapper with venv management
- `run_mpm.py` - Python runner that handles imports correctly
- `run_all_tests.sh` - Run all tests in sequence
- `run_e2e_tests.sh` - Run end-to-end tests

## Release Management Scripts

- `release.py` - **Unified release script** (single source of truth for releases)
- `manage_version.py` - Version management with semantic versioning
- `check_version_sync.py` - Verify version synchronization across files

## Test Scripts (scripts/tests/)

- `test_hello_world.py` - Basic test to verify prompt injection
- `test_orchestration.py` - Test orchestration functionality
- `test_agent_integration.py` - Test agent registry integration
- `run_tests.py` - Run pytest suite with coverage
- `run_tests_updated.py` - Updated test runner with proper paths

## Usage

### Release Process

The unified release script handles all aspects of releasing Claude MPM:

```bash
# Dry run to preview changes
./scripts/release.py patch --dry-run

# Release a patch version
./scripts/release.py patch

# Release a minor version
./scripts/release.py minor

# Release a major version
./scripts/release.py major

# Test with TestPyPI first
./scripts/release.py patch --test-pypi
```

The release script will:
1. Run pre-release checks
2. Run tests
3. Bump version
4. Synchronize package.json
5. Build and publish to PyPI
6. Publish to npm
7. Create GitHub release
8. Verify packages

### Check Version Sync

```bash
# Verify all version files are synchronized
./scripts/check_version_sync.py
```

### Run Claude MPM
```bash
# From project root (symlink)
./claude-mpm --debug run

# Or use the script directly
./scripts/claude-mpm --debug run
```

### Run Tests
```bash
# Run all tests
./scripts/run_all_tests.sh

# Run specific test
cd ~/Tests/claude-mpm-test
python3 /path/to/claude-mpm/scripts/tests/test_hello_world.py

# Run unit tests with coverage
python3 scripts/tests/run_tests_updated.py
```

### Hello World Test
The hello world test verifies that:
1. Framework instructions are properly injected
2. Prompts are logged to ~/.claude-mpm/prompts/
3. Session data is saved to ~/.claude-mpm/sessions/
4. The orchestrator can launch Claude as a subprocess

## Directory Structure
```
scripts/
├── README.md              # This file
├── claude-mpm            # Main executable wrapper
├── run_mpm.py           # Python runner
├── run_all_tests.sh     # Run all tests
├── run_e2e_tests.sh     # Run E2E tests
├── release.py           # Unified release script
├── manage_version.py    # Version management
├── check_version_sync.py # Version sync checker
└── tests/               # Test scripts
    ├── test_hello_world.py
    ├── test_orchestration.py
    ├── test_agent_integration.py
    ├── run_tests.py
    └── run_tests_updated.py
```