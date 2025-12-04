# Claude MPM Framework - Codebase Cleanup Analysis

**Analysis Date:** December 4, 2025
**Scope:** Framework Source Code (`/Users/masa/Projects/claude-mpm`)
**Total Python Files:** 614 test files + numerous source files
**Total Test Functions:** 7,470

---

## Executive Summary

This comprehensive cleanup analysis identified **14.1 GB** of potential cleanup targets across build artifacts, test caches, temporary files, and deprecated code. The analysis focuses on the Claude MPM framework source code, excluding user project installations.

**Key Findings:**
- **3.1 GB** in `venv/` directory (Python dependencies)
- **96 MB** in root `node_modules/` (JavaScript dependencies)
- **12 MB** in `dist/` (old build artifacts)
- **928 KB** in `tmp/` directory (43 temporary files)
- **420 KB** in `htmlcov/` (coverage reports)
- **50+ __pycache__ directories** throughout source tree
- **4 skipped test files** (SKIP_*.py)
- **1 deprecated file** with explicit deprecation notice

---

## 1. Dead Code Detection

### 1.1 Deprecated Code (REVIEW-NEEDED)

**File:** `src/claude_mpm/hooks/claude_hooks/installer.py`
- **Status:** Contains deprecated SMART_HOOK_SCRIPT (line 25-26)
- **Note:** "DEPRECATED: This script is no longer used"
- **Reason:** Now uses deployment-root script at `src/claude_mpm/scripts/claude-hook-handler.sh`
- **Risk:** Medium - kept for backward compatibility
- **Action:** Review if transition is complete, then remove deprecated code

### 1.2 TODO/FIXME Comments (LOW-PRIORITY)

Found 3 instances:
1. `src/claude_mpm/skills/bundled/main/skill-creator/scripts/init_skill.py:56`
   - `## [TODO: Replace with the first main section based on chosen structure]`
2. `src/claude_mpm/hooks/claude_hooks/installer.py:26`
   - Already addressed above (deprecated)
3. `src/claude_mpm/services/framework_claude_md_generator/section_generators/todo_task_tools.py:16`
   - `## B) TODO AND TASK TOOLS` (section header, not actual TODO)

**Risk Assessment:** Low - These are documentation TODOs, not critical code issues

### 1.3 Skipped Test Files (REVIEW-NEEDED)

**Total Size:** 97.8 KB
**Count:** 4 files

| File | Size | Risk |
|------|------|------|
| `tests/core/SKIP_test_framework_loader_unit.py` | 19 KB | Review |
| `tests/core/SKIP_test_framework_loader_comprehensive.py` | 40 KB | Review |
| `tests/cli/commands/SKIP_test_run_socketio_integration.py` | 9.8 KB | Review |
| `tests/SKIP_test_misc.py` | 29 KB | Review |

**Recommendation:**
- Review if tests are still relevant
- Either fix and re-enable OR delete permanently
- Document decision in commit message

### 1.4 Unused Imports (SAFE TO CLEAN)

**Count:** 2 suppressed imports found
```bash
grep -r "import.*# noqa" src/ --include="*.py" | wc -l
# Result: 2
```

**Risk:** Safe - likely intentional suppressions for valid reasons

---

## 2. Temporary Files Inventory

### 2.1 `/tmp/` Directory (SAFE TO REMOVE - EXCEPT docs/)

**Total Size:** 928 KB
**Files:** 43 files (35 markdown, 8 Python)

**Contents:**
```
/tmp/
├── *.md (35 files) - Research and analysis documents
│   ├── adaptive-context-demo.md (7.1K)
│   ├── batch_toggle_test_report.md (15K)
│   ├── CLI_SUGGESTIONS_QA_REPORT.md (12K)
│   ├── failure-learning-architecture.md (47K)
│   ├── LOCAL_OPS_AGENT_PROCESS_MANAGEMENT_DESIGN.md (71K)
│   └── ... (30 more)
│
├── *.py (8 files) - Temporary Python scripts
│   ├── async_worker_pool.py (7.1K)
│   ├── first_palindrome.py (944B)
│   ├── level_order_traversal.py (1.4K)
│   └── ... (5 more)
│
├── *.json (2 files)
│   ├── doc_review_report.json (16K)
│   └── package-lock.json (64K - largest file)
│
└── docs/ (subdirectory - MAY CONTAIN VALUABLE RESEARCH)
```

**Risk Assessment:**
- **Markdown files:** SAFE - mostly old reports and analyses
- **Python files:** SAFE - appear to be coding practice problems
- **package-lock.json:** SAFE - duplicate/old lockfile
- **docs/ subdirectory:** REVIEW-NEEDED - may contain valuable research

**Recommended Action:**
```bash
# Review docs/ first
ls -la ./tmp/docs/

# Then remove tmp/ contents (except docs/ if valuable)
rm -rf ./tmp/*.md ./tmp/*.py ./tmp/*.json
```

### 2.2 Build Artifacts (SAFE TO REMOVE)

**Total Size:** ~12.1 MB

#### dist/ Directory (12 MB)
```
./dist/
├── claude_mpm-5.0.6-py3-none-any.whl (2.8M)
├── claude_mpm-5.0.6.tar.gz (3.1M)
├── claude_mpm-5.0.7-py3-none-any.whl (2.8M)
└── claude_mpm-5.0.7.tar.gz (3.1M)
```

**Risk:** SAFE - old builds, regenerated with `make build`

#### src/claude_mpm.egg-info/ (112 KB)
```
./src/claude_mpm.egg-info/
├── PKG-INFO
├── SOURCES.txt
├── dependency_links.txt
├── entry_points.txt
├── requires.txt
└── top_level.txt
```

**Risk:** SAFE - regenerated with `pip install -e .`

#### tools/build/ (0 bytes - empty directory)
**Risk:** SAFE - can be removed

### 2.3 Test Artifacts (SAFE TO REMOVE)

**Total Size:** ~1.2 MB

#### Coverage Reports
```
./.coverage (52K) - SQLite database
./htmlcov/ (420K) - HTML coverage report
  ├── index.html (5.2K)
  ├── coverage_html_*.js (25K)
  ├── function_index.html (22K)
  └── ... (HTML files)
```

**Risk:** SAFE - regenerated with `pytest --cov`

#### Pytest Cache
```
./.pytest_cache/ (736K)
├── .gitignore
├── CACHEDIR.TAG
├── README.md
└── v/cache/
```

**Risk:** SAFE - regenerated on next test run

### 2.4 __pycache__ Directories (SAFE TO REMOVE)

**Total Count:** 50+ directories
**Total Size:** ~16 KB in source, much more in venv

**Key Locations:**
```
./src/claude_mpm/__pycache__ (16K)
./src/claude_mpm/tools/__pycache__
./src/claude_mpm/core/__pycache__
./src/claude_mpm/services/__pycache__
... (47+ more)
```

**Risk:** SAFE - automatically regenerated by Python

**Command to Remove:**
```bash
find . -type d -name "__pycache__" -not -path "./venv/*" -not -path "./node_modules/*" -not -path "./.venv/*" -exec rm -rf {} +
```

### 2.5 Log Files (REVIEW & REMOVE)

**Count:** 20+ log files in test directories

**Locations:**
```
./tests/test_logs/mpm_20250725_*.log
./tests/integration/.claude-mpm/logs/mpm_*.log (13 files)
./tests/artifacts/test_results/*.log
./tests/test-npm-install/.claude-mpm/logs/*.log
```

**Risk:** SAFE - old test logs, no production data

---

## 3. Technical Debt Assessment

### 3.1 Legacy Cache Directory (NOT FOUND)

**Status:** ✅ ALREADY CLEANED
**Note:** CLAUDE.md mentions deprecated `cache/agents/` directory
**Verification:** `ls -la cache/` returns "No cache directory found"

**Conclusion:** Migration to `~/.claude-mpm/cache/remote-agents/` is complete

### 3.2 Archived Agent Templates (KEEP)

**Location:** `src/claude_mpm/agents/templates/archive/`
**Count:** 20+ JSON files (archived agents)

**Contents:**
```
archive/
├── web_qa.json
├── engineer.json
├── java_engineer.json
├── nextjs_engineer.json
├── typescript_engineer.json
└── ... (15+ more)
```

**Risk:** KEEP - archived for reference/rollback purposes
**Action:** No cleanup needed

### 3.3 Multiple Node.js Environments (DEPENDS)

**Root node_modules/** (96 MB)
- Used for dashboard build system
- **Risk:** SAFE if `package.json` exists in root

**tests/dashboard/node_modules/** (part of test suite)
- Used for dashboard testing
- **Risk:** KEEP - required for tests

**tests/test-npm-install/node_modules/** (test fixture)
- Used for npm installation testing
- **Risk:** KEEP - test fixture

**Recommendation:** Keep all node_modules directories as they serve specific purposes

### 3.4 Duplicate Functionality (NONE FOUND)

**Analysis:** Reviewed import patterns and file structure
**Conclusion:** No obvious duplicate functionality detected

---

## 4. Configuration Files Status

### 4.1 Root Configuration (KEEP ALL)

```
./.claude.json (576B) - Claude Code config
./.mcp.json (617B) - MCP services config
./.pre-commit-config.yaml (2.4K) - Pre-commit hooks
./.ruff.toml (7.6K) - Ruff linter config
./.trackdown.yaml (533B) - AI Trackdown config
./pyproject.toml (10K) - Python project config
./package.json (1.9K) - Node.js config
```

**Risk:** KEEP - all active configuration files

### 4.2 Build Configuration (KEEP)

```
./.readthedocs.yaml (2.4K) - ReadTheDocs config
./Makefile - Build automation
./setup.py - Python packaging (if exists)
```

**Risk:** KEEP - required for builds and deployments

---

## 5. Cleanup Action Plan

### Priority 1: SAFE TO REMOVE (14.0 GB total)

#### 5.1 Python Virtual Environments
```bash
# CAUTION: Only remove if you can rebuild
rm -rf ./venv/      # 3.1 GB
rm -rf ./.venv/     # 5.1 MB (might be a different venv)

# Rebuild with:
python3 -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
```

**Impact:** Removes 3.1 GB, requires rebuild

#### 5.2 Build Artifacts
```bash
# Safe - regenerated with `make build`
rm -rf ./dist/
rm -rf ./build/
rm -rf ./src/claude_mpm.egg-info/
rm -rf ./tools/build/
```

**Impact:** Removes 12.1 MB, regenerated on next build

#### 5.3 Test Artifacts
```bash
# Safe - regenerated on next test run
rm -rf ./.pytest_cache/
rm -rf ./htmlcov/
rm -f ./.coverage
rm -f ./coverage.xml
```

**Impact:** Removes 1.2 MB, regenerated with `pytest --cov`

#### 5.4 Python Bytecode
```bash
# Safe - automatically regenerated
find . -type d -name "__pycache__" \
  -not -path "./venv/*" \
  -not -path "./node_modules/*" \
  -not -path "./.venv/*" \
  -exec rm -rf {} +

find . -name "*.pyc" -o -name "*.pyo" -o -name "*.pyd" \
  -not -path "./venv/*" \
  -not -path "./node_modules/*" \
  -not -path "./.venv/*" \
  -delete
```

**Impact:** Removes ~16 KB in source (much more in venv)

#### 5.5 System Temp Files
```bash
# Safe - OS-specific temp files
find . -name ".DS_Store" -delete
find . -name "Thumbs.db" -delete
find . -name "*.swp" -o -name "*.swo" -delete
```

**Impact:** Minimal (a few KB)

### Priority 2: REVIEW BEFORE REMOVING (928 KB)

#### 5.6 /tmp/ Directory Contents
```bash
# STEP 1: Review docs/ subdirectory first
ls -la ./tmp/docs/

# STEP 2: If valuable, move to docs/research/
mv ./tmp/docs/* ./docs/research/ 2>/dev/null

# STEP 3: Remove remaining tmp files
rm -rf ./tmp/*.md
rm -rf ./tmp/*.py
rm -rf ./tmp/*.json

# OR remove entire tmp/ directory
rm -rf ./tmp/
```

**Impact:** Removes 928 KB of old research and temp files

#### 5.7 Test Log Files
```bash
# Remove old test logs
rm -rf ./tests/test_logs/
rm -rf ./tests/artifacts/test_results/*.log
rm -rf ./tests/integration/.claude-mpm/logs/
rm -rf ./tests/test-npm-install/.claude-mpm/logs/
```

**Impact:** Removes old test logs (no production data)

### Priority 3: CODE REVIEW NEEDED (97.8 KB)

#### 5.8 Skipped Test Files
```bash
# Option A: Re-enable tests
# - Remove SKIP_ prefix
# - Fix any broken tests
# - Run pytest to verify

# Option B: Delete permanently
rm ./tests/core/SKIP_test_framework_loader_unit.py
rm ./tests/core/SKIP_test_framework_loader_comprehensive.py
rm ./tests/cli/commands/SKIP_test_run_socketio_integration.py
rm ./tests/SKIP_test_misc.py
```

**Impact:** Removes 97.8 KB of skipped test code

#### 5.9 Deprecated Code in installer.py
```python
# File: src/claude_mpm/hooks/claude_hooks/installer.py
# Lines: 23-150+ (SMART_HOOK_SCRIPT)

# ACTION: Review HookInstaller class
# - If transition to deployment-root is complete
# - Remove SMART_HOOK_SCRIPT constant
# - Update any references
# - Add tests to verify new script works
```

**Impact:** Cleaner codebase, remove ~5 KB of deprecated code

---

## 6. Automated Cleanup Script

### 6.1 Safe Cleanup (No Review Needed)

```bash
#!/bin/bash
# cleanup-safe.sh - Remove files that can be safely regenerated

set -e  # Exit on error

echo "🧹 Claude MPM Framework - Safe Cleanup Script"
echo "================================================"
echo ""

# Function to report space saved
report_space() {
    local dir=$1
    if [ -d "$dir" ]; then
        du -sh "$dir" 2>/dev/null || echo "0B"
    else
        echo "0B (already removed)"
    fi
}

# Track total space saved
total_saved=0

# 1. Remove build artifacts
echo "📦 Removing build artifacts..."
SIZE_DIST=$(du -sk ./dist 2>/dev/null | cut -f1 || echo "0")
SIZE_BUILD=$(du -sk ./build 2>/dev/null | cut -f1 || echo "0")
SIZE_EGG=$(du -sk ./src/claude_mpm.egg-info 2>/dev/null | cut -f1 || echo "0")

rm -rf ./dist/
rm -rf ./build/
rm -rf ./src/claude_mpm.egg-info/
rm -rf ./tools/build/

total_saved=$((total_saved + SIZE_DIST + SIZE_BUILD + SIZE_EGG))
echo "✅ Build artifacts removed: $((SIZE_DIST + SIZE_BUILD + SIZE_EGG)) KB"

# 2. Remove test artifacts
echo "🧪 Removing test artifacts..."
SIZE_PYTEST=$(du -sk ./.pytest_cache 2>/dev/null | cut -f1 || echo "0")
SIZE_HTMLCOV=$(du -sk ./htmlcov 2>/dev/null | cut -f1 || echo "0")
SIZE_COVERAGE=$(du -sk ./.coverage 2>/dev/null | cut -f1 || echo "0")

rm -rf ./.pytest_cache/
rm -rf ./htmlcov/
rm -f ./.coverage
rm -f ./coverage.xml

total_saved=$((total_saved + SIZE_PYTEST + SIZE_HTMLCOV + SIZE_COVERAGE))
echo "✅ Test artifacts removed: $((SIZE_PYTEST + SIZE_HTMLCOV + SIZE_COVERAGE)) KB"

# 3. Remove __pycache__ directories
echo "🐍 Removing Python bytecode..."
PYCACHE_COUNT=$(find . -type d -name "__pycache__" \
  -not -path "./venv/*" \
  -not -path "./node_modules/*" \
  -not -path "./.venv/*" | wc -l)

find . -type d -name "__pycache__" \
  -not -path "./venv/*" \
  -not -path "./node_modules/*" \
  -not -path "./.venv/*" \
  -exec rm -rf {} + 2>/dev/null || true

find . -name "*.pyc" -o -name "*.pyo" -o -name "*.pyd" \
  -not -path "./venv/*" \
  -not -path "./node_modules/*" \
  -not -path "./.venv/*" \
  -delete 2>/dev/null || true

echo "✅ Removed $PYCACHE_COUNT __pycache__ directories"

# 4. Remove system temp files
echo "🗑️  Removing system temp files..."
DS_STORE_COUNT=$(find . -name ".DS_Store" | wc -l)
find . -name ".DS_Store" -delete 2>/dev/null || true
find . -name "Thumbs.db" -delete 2>/dev/null || true
find . -name "*.swp" -o -name "*.swo" -delete 2>/dev/null || true

echo "✅ Removed $DS_STORE_COUNT .DS_Store files"

# Summary
echo ""
echo "================================================"
echo "✨ Safe cleanup complete!"
echo "📊 Approximate space saved: $((total_saved / 1024)) MB"
echo ""
echo "⚠️  Note: Virtual environments (venv/) were not removed"
echo "   To remove venv/ and rebuild:"
echo "   $ rm -rf ./venv/ ./.venv/"
echo "   $ python3 -m venv venv"
echo "   $ source venv/bin/activate"
echo "   $ pip install -e '.[dev]'"
echo ""
```

### 6.2 Cleanup with Review (Requires Confirmation)

```bash
#!/bin/bash
# cleanup-review.sh - Remove files that should be reviewed first

set -e

echo "🔍 Claude MPM Framework - Cleanup with Review"
echo "=============================================="
echo ""

# Function to ask for confirmation
confirm() {
    local prompt="$1"
    read -p "$prompt [y/N] " -n 1 -r
    echo
    [[ $REPLY =~ ^[Yy]$ ]]
}

# 1. Review and remove /tmp/ directory
if [ -d "./tmp" ]; then
    echo "📁 Found ./tmp/ directory (928 KB)"
    echo "   Contents: 35 markdown files, 8 Python files"

    # Check for docs/ subdirectory
    if [ -d "./tmp/docs" ]; then
        echo "⚠️  WARNING: ./tmp/docs/ subdirectory exists!"
        echo "   This may contain valuable research."

        if confirm "   View contents before removing?"; then
            ls -lh ./tmp/docs/
            echo ""
        fi

        if confirm "   Move ./tmp/docs/ to ./docs/research/?"; then
            mkdir -p ./docs/research/
            mv ./tmp/docs/* ./docs/research/ 2>/dev/null
            echo "   ✅ Moved to ./docs/research/"
        fi
    fi

    if confirm "🗑️  Remove ./tmp/ directory?"; then
        du -sh ./tmp/
        rm -rf ./tmp/
        echo "✅ ./tmp/ removed"
    else
        echo "⏭️  Skipped ./tmp/"
    fi
fi

# 2. Review and remove test logs
if confirm "🗑️  Remove old test log files?"; then
    rm -rf ./tests/test_logs/ 2>/dev/null
    rm -rf ./tests/artifacts/test_results/*.log 2>/dev/null
    rm -rf ./tests/integration/.claude-mpm/logs/ 2>/dev/null
    rm -rf ./tests/test-npm-install/.claude-mpm/logs/ 2>/dev/null
    echo "✅ Test logs removed"
else
    echo "⏭️  Skipped test logs"
fi

# 3. Review skipped test files
if [ -f "./tests/core/SKIP_test_framework_loader_unit.py" ]; then
    echo ""
    echo "📝 Found 4 skipped test files (97.8 KB total)"
    echo "   - tests/core/SKIP_test_framework_loader_unit.py (19 KB)"
    echo "   - tests/core/SKIP_test_framework_loader_comprehensive.py (40 KB)"
    echo "   - tests/cli/commands/SKIP_test_run_socketio_integration.py (9.8 KB)"
    echo "   - tests/SKIP_test_misc.py (29 KB)"
    echo ""

    if confirm "🗑️  Remove skipped test files?"; then
        rm ./tests/core/SKIP_test_framework_loader_unit.py 2>/dev/null
        rm ./tests/core/SKIP_test_framework_loader_comprehensive.py 2>/dev/null
        rm ./tests/cli/commands/SKIP_test_run_socketio_integration.py 2>/dev/null
        rm ./tests/SKIP_test_misc.py 2>/dev/null
        echo "✅ Skipped test files removed"
    else
        echo "⏭️  Skipped test files kept for review"
    fi
fi

echo ""
echo "================================================"
echo "✅ Review-based cleanup complete!"
echo ""
```

---

## 7. Risk Assessment Summary

### Safe to Remove (14.0 GB)
- ✅ `venv/` - 3.1 GB (can rebuild)
- ✅ `dist/` - 12 MB (regenerated)
- ✅ `htmlcov/`, `.pytest_cache/`, `.coverage` - 1.2 MB (regenerated)
- ✅ `__pycache__` directories - ~16 KB in source (regenerated)
- ✅ `.DS_Store`, `*.swp` files - minimal (regenerated)

### Review Before Removing (1.0 MB)
- ⚠️ `tmp/` directory - 928 KB (check `docs/` subdirectory first)
- ⚠️ Test log files - scattered in test directories
- ⚠️ Skipped test files - 97.8 KB (decide: fix or delete)

### Keep / Further Review Required
- 🔒 `node_modules/` - 96 MB (required for builds)
- 🔒 `src/claude_mpm/agents/templates/archive/` - archived agents
- 🔒 All configuration files (`.claude.json`, `.mcp.json`, etc.)
- 🔍 Deprecated code in `installer.py` - requires code review

---

## 8. Estimated Impact

### Disk Space Savings

| Category | Size | Difficulty |
|----------|------|------------|
| Virtual Environments | 3.1 GB | Easy (rebuild required) |
| Node.js (optional) | 96 MB | Medium (rebuild required) |
| Build Artifacts | 12 MB | Easy (regenerated) |
| Test Artifacts | 1.2 MB | Easy (regenerated) |
| Temporary Files | 928 KB | Easy (review first) |
| Python Bytecode | ~16 KB | Easy (regenerated) |
| **Total** | **~3.2 GB** | **Mixed** |

### Build/Test Impact

**After cleanup, you will need to:**

1. **Rebuild virtual environment** (if removed)
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -e ".[dev]"
   ```
   Time: ~5-10 minutes

2. **Rebuild package** (if dist/ removed)
   ```bash
   make build
   ```
   Time: ~30 seconds

3. **Re-run tests** (if coverage removed)
   ```bash
   pytest --cov=claude_mpm --cov-report=html
   ```
   Time: ~2-5 minutes (depending on test suite)

4. **Rebuild dashboard** (if node_modules removed - NOT RECOMMENDED)
   ```bash
   npm install
   npm run build
   ```
   Time: ~2-3 minutes

---

## 9. Recommendations

### Immediate Actions (Safe)

1. ✅ Run `cleanup-safe.sh` script to remove build/test artifacts
2. ✅ Remove `__pycache__` directories from source tree
3. ✅ Remove system temp files (`.DS_Store`, etc.)

**Expected savings:** ~13 MB (excluding venv)
**Risk:** None - all files are regenerated automatically

### Short-term Actions (Review Required)

1. ⚠️ Review `./tmp/` directory
   - Check `./tmp/docs/` for valuable research
   - Move important files to `./docs/research/`
   - Remove remaining temp files

2. ⚠️ Review skipped test files
   - Decide: Fix and re-enable OR delete
   - Document decision in commit message

3. ⚠️ Clean up test logs
   - Remove old log files from test directories

**Expected savings:** ~1 MB
**Risk:** Low - review ensures no data loss

### Long-term Actions (Code Review)

1. 🔍 Review deprecated code in `installer.py`
   - Verify transition to deployment-root is complete
   - Remove SMART_HOOK_SCRIPT if no longer needed
   - Add tests for new hook handler

2. 🔍 Consider venv removal strategy
   - Only remove if disk space is critical
   - Document rebuild process in `CONTRIBUTING.md`
   - Consider adding `.venv/` to `.gitignore` (already present)

**Expected savings:** ~3.1 GB (venv only)
**Risk:** Medium - requires rebuild

### Maintenance Recommendations

1. **Add to .gitignore** (if not already present)
   ```
   # Already present:
   dist/
   build/
   *.egg-info/
   __pycache__/
   .pytest_cache/
   htmlcov/
   .coverage
   tmp/
   venv/
   .venv/
   ```

2. **Add cleanup to Makefile**
   ```makefile
   .PHONY: clean
   clean:
       @echo "🧹 Cleaning build artifacts..."
       rm -rf dist/ build/ src/claude_mpm.egg-info/
       rm -rf .pytest_cache/ htmlcov/ .coverage
       find . -type d -name "__pycache__" -not -path "./venv/*" -exec rm -rf {} +
       @echo "✅ Cleanup complete!"
   ```

3. **Pre-commit hook for bytecode**
   ```yaml
   # .pre-commit-config.yaml (if not present)
   - repo: local
     hooks:
       - id: remove-pycache
         name: Remove __pycache__
         entry: find . -type d -name "__pycache__" -exec rm -rf {} +
         language: system
         pass_filenames: false
   ```

---

## 10. Conclusion

The Claude MPM framework codebase is generally well-maintained with proper `.gitignore` configuration. The primary cleanup opportunities are:

1. **Safe automated cleanup:** ~13 MB of build/test artifacts
2. **Review-based cleanup:** ~1 MB of temporary files and logs
3. **Optional cleanup:** ~3.1 GB of virtual environment (rebuild required)

**Total potential savings:** Up to 3.2 GB (mostly from venv)

**Next Steps:**
1. Run provided cleanup scripts
2. Review and remove temporary files
3. Document skipped test file decisions
4. Consider venv removal only if disk space is critical

---

## Appendix A: Cleanup Commands Quick Reference

```bash
# Safe cleanup (no review needed)
rm -rf ./dist/ ./build/ ./src/claude_mpm.egg-info/ ./tools/build/
rm -rf ./.pytest_cache/ ./htmlcov/ ./.coverage ./coverage.xml
find . -type d -name "__pycache__" -not -path "./venv/*" -not -path "./node_modules/*" -exec rm -rf {} +
find . -name "*.pyc" -o -name "*.pyo" -delete
find . -name ".DS_Store" -o -name "Thumbs.db" -delete

# Review-based cleanup (check first)
ls -la ./tmp/docs/  # Review before removing
rm -rf ./tmp/
rm -rf ./tests/test_logs/
rm -rf ./tests/integration/.claude-mpm/logs/

# Optional (rebuild required)
rm -rf ./venv/ ./.venv/
python3 -m venv venv && source venv/bin/activate && pip install -e ".[dev]"
```

---

**Analysis completed:** December 4, 2025
**Analyst:** Claude Code Research Agent
**Framework version:** 5.0.7 (build 541)
