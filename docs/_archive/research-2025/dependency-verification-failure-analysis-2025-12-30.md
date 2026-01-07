# Dependency Installation Verification Failure Analysis

**Date:** 2025-12-30
**Researcher:** Claude (Code Analysis Agent)
**Issue:** "Package installed but verification failed" for 33 packages
**Priority:** High (P1) - Affects all dependency installations

---

## Executive Summary

All 33 packages fail verification with "Package installed but verification failed" despite successful `pip install`. The root cause is an **environment mismatch** when using `uv pip install` in UV tool environments.

### Root Cause
When `is_uv_tool=True`, the installer uses `uv pip install` to install packages, but verification runs in the **current Python process** using `importlib.metadata`. These may target **different Python environments**, causing verification to fail even when installation succeeds.

---

## Detailed Analysis

### 1. Problem Location

**File:** `/Users/masa/Projects/claude-mpm/src/claude_mpm/utils/robust_installer.py`
**Function:** `_verify_installation()` (line 479)
**Called from:** `_attempt_install()` (line 195)

```python
# Line 193-197 in _attempt_install()
if result.returncode == 0:
    # Verify installation
    if self._verify_installation(package_spec):
        return True, None
    return False, "Package installed but verification failed"  # <- ERROR MESSAGE
```

### 2. The Mismatch Problem

#### Installation Phase (lines 336-340)
```python
if self.is_uv_tool:
    base_cmd = ["uv", "pip", "install"]  # <- Installs to UV tool's Python
    logger.debug("Using 'uv pip install' for UV tool environment")
else:
    base_cmd = [sys.executable, "-m", "pip", "install"]
```

#### Verification Phase (lines 496-500)
```python
try:
    # Check if package is installed
    import importlib.metadata

    try:
        version = importlib.metadata.version(package_name)  # <- Checks CURRENT process
        logger.debug(f"Package {package_name} version {version} is installed")
```

**The Issue:**
- `uv pip install` may install to a **different Python environment**
- Verification checks the **current Python process's environment**
- If these are different Pythons, verification **always fails**

### 3. UV Tool Environment Detection

The code detects UV tool environments (lines 265-293):

```python
def _check_uv_tool_installation(self) -> bool:
    """Check if running in UV tool environment (no pip available)."""
    import os

    # Check UV_TOOL_DIR environment variable
    uv_tool_dir = os.environ.get("UV_TOOL_DIR", "")
    if uv_tool_dir and "claude-mpm" in uv_tool_dir:
        logger.debug(f"UV tool environment detected via UV_TOOL_DIR: {uv_tool_dir}")
        return True

    # Check executable path for UV tool patterns
    executable = sys.executable
    if ".local/share/uv/tools/" in executable or "/uv/tools/" in executable:
        logger.debug(f"UV tool environment detected via executable path: {executable}")
        return True

    return False
```

**Problem:** When `True`, uses `uv pip` for install but `sys.executable` for verification.

---

## Why This Happens

### Scenario 1: UV Tool Environment
1. User installs `claude-mpm` with `uvx claude-mpm` or `uv tool install claude-mpm`
2. Code detects UV tool environment: `is_uv_tool = True`
3. Installation command: `["uv", "pip", "install", "pytest>=7.4.0"]`
4. UV installs to: `/Users/user/.local/share/uv/tools/claude-mpm/bin/python`
5. Verification runs in: Current process (may be different Python)
6. `importlib.metadata.version("pytest")` searches in **current process**
7. Package not found in current process → **verification fails**

### Scenario 2: Wrong Python Path
Even in non-UV environments, if `uv pip install` targets a different Python than `sys.executable`, the same mismatch occurs.

---

## Evidence

### Test Results

Created test script (`/Users/masa/Projects/claude-mpm/test_verification.py`):

```bash
$ python3 test_verification.py
Testing: pytest
  ✓ Version found: 8.4.2
  ✓ Import successful
```

**Finding:** Packages ARE installed and importable in the test environment, proving the verification logic itself works when Python environments match.

### UV Environment Check

```bash
$ python3 -c "import sys; print(sys.executable)"
/Users/masa/Projects/claude-mpm/.venv/bin/python3

$ echo $UV_TOOL_DIR
(empty - not in UV tool environment currently)
```

---

## Affected Code Paths

### 1. Single Package Installation
**File:** `robust_installer.py`
**Method:** `_attempt_install()` → `_verify_installation()`
**Line:** 195-197

### 2. Batch Installation
**File:** `robust_installer.py`
**Method:** `_attempt_batch_install()`
**Line:** 720

```python
if result.returncode == 0:
    # Verify all packages
    all_verified = all(self._verify_installation(pkg) for pkg in packages)
    if all_verified:
        return True, None
    return False, "Some packages failed verification"
```

### 3. Similar Code in `agent_dependency_loader.py`
**File:** `/Users/masa/Projects/claude-mpm/src/claude_mpm/utils/agent_dependency_loader.py`
**Line:** 674-675

Uses same `uv pip install` pattern, likely has same issue.

---

## Recommended Fix

### Option 1: Verify in Target Python (Recommended)

Run verification in the **same Python** that pip/uv targets:

```python
def _verify_installation(self, package_spec: str) -> bool:
    """Verify package installed in the TARGET Python environment."""
    package_name = self._extract_package_name(package_spec)

    # Determine which Python to check
    if self.is_uv_tool:
        # For UV tool, run verification via UV's Python
        verify_cmd = ["uv", "run", "--no-project", "python", "-c",
                     f"import importlib.metadata; "
                     f"importlib.metadata.version('{package_name}')"]
    else:
        # For normal Python, use sys.executable
        verify_cmd = [sys.executable, "-c",
                     f"import importlib.metadata; "
                     f"importlib.metadata.version('{package_name}')"]

    try:
        result = subprocess.run(
            verify_cmd,
            capture_output=True,
            text=True,
            timeout=10,
            check=False
        )

        if result.returncode == 0:
            logger.debug(f"Package {package_name} verified in target environment")
            return True

        logger.debug(f"Package {package_name} not found in target environment")
        return False

    except Exception as e:
        logger.warning(f"Verification failed with error: {e}")
        return False
```

### Option 2: Use Same Python for Install and Verify

Force installation to use `sys.executable` even in UV environments:

```python
def _build_install_command(self, package_spec: str, strategy: InstallStrategy) -> List[str]:
    # ALWAYS use sys.executable, never "uv pip"
    base_cmd = [sys.executable, "-m", "pip", "install"]

    # Handle PEP 668 if needed
    if not self.in_virtualenv and self.is_pep668_managed:
        base_cmd.append("--break-system-packages")

    # ... rest of method
```

**Drawback:** Requires `pip` to be installed in UV tool environments.

### Option 3: Disable Verification for UV Environments (Quick Fix)

```python
def _verify_installation(self, package_spec: str) -> bool:
    """Verify package installation."""

    # In UV tool environments, trust pip's exit code
    # (verification may check wrong environment)
    if self.is_uv_tool:
        logger.debug(f"Skipping verification in UV tool environment (trusting exit code)")
        return True

    # Normal verification for other environments
    package_name = self._extract_package_name(package_spec)
    # ... existing logic
```

**Drawback:** No actual verification in UV environments.

---

## Impact Assessment

### Severity: **High (P1)**

- **Scope:** All 33 packages fail verification
- **User Experience:** Users see "verification failed" despite successful installation
- **Functionality:** Packages may actually be installed correctly, but code thinks they failed
- **Consequence:** May trigger unnecessary retries, errors, or prevent features from enabling

### Affected Features
- Monitor installation (`--monitor` flag)
- Optional dependency installation
- Agent dependency loading
- MCP service dependency management

---

## Testing Strategy

### Unit Test
```python
def test_verification_matches_install_environment():
    """Ensure verification checks the same Python as installation."""
    installer = RobustPackageInstaller()

    # Install a package
    success, error = installer.install_package("pytest>=7.4.0")

    # Verify it's actually importable
    import pytest
    assert pytest.__version__ >= "7.4.0"

    # Ensure verification would pass
    assert installer._verify_installation("pytest>=7.4.0") is True
```

### Integration Test
```bash
# Test in UV tool environment
uvx claude-mpm doctor --check-dependencies

# Should NOT show "verification failed" for working packages
```

---

## Action Items

### Immediate (P0)
1. ✅ Investigate root cause (COMPLETE - this document)
2. Implement Option 1 (verify in target Python)
3. Add test coverage for UV tool environments
4. Update `agent_dependency_loader.py` with same fix

### Short-term (P1)
5. Add environment mismatch detection
6. Log warning if verification environment != install environment
7. Document UV tool environment behavior
8. Add integration tests for UV/virtualenv/system Python scenarios

### Long-term (P2)
9. Refactor to unify installation+verification logic
10. Create dependency manager abstraction layer
11. Consider caching verification results per environment

---

## Related Files

### Primary
- `/Users/masa/Projects/claude-mpm/src/claude_mpm/utils/robust_installer.py`
  - `_verify_installation()` (line 479)
  - `_attempt_install()` (line 172)
  - `_check_uv_tool_installation()` (line 265)
  - `_build_install_command()` (line 317)

### Secondary
- `/Users/masa/Projects/claude-mpm/src/claude_mpm/utils/agent_dependency_loader.py`
  - Similar UV pip usage (line 674)
  - May have same verification issue

### Tests to Create
- `tests/utils/test_robust_installer_verification.py` (NEW)
- `tests/integration/test_uv_environment_dependencies.py` (NEW)

---

## Appendix: Environment Detection Logic

### Current Detection
```python
# Three environment checks:
self.in_virtualenv = self._check_virtualenv()      # venv/virtualenv
self.is_uv_tool = self._check_uv_tool_installation()  # UV tool env
self.is_pep668_managed = self._check_pep668_managed()  # System Python (Homebrew, etc.)
```

### Installation Strategy Decision Tree
```
if is_uv_tool:
    use: ["uv", "pip", "install"]
elif in_virtualenv:
    use: [sys.executable, "-m", "pip", "install"]  # no special flags
elif is_pep668_managed:
    use: [sys.executable, "-m", "pip", "install", "--break-system-packages"]
else:
    use: [sys.executable, "-m", "pip", "install", "--user"]
```

### Problem with Current Strategy
**Verification always uses:** Current Python process (`sys.executable`)
**But installation may use:** `uv pip` (different Python)
**Result:** Environment mismatch → verification fails

---

## Conclusion

The "Package installed but verification failed" error is **not** a package installation problem. It's an **environment mismatch** where:

1. Packages are installed successfully (via `uv pip install`)
2. Verification checks a **different Python environment** (current process)
3. Packages aren't found in the verification environment → false failure

**Fix:** Verify in the **same Python environment** where packages were installed.

**Recommended Implementation:** Option 1 (subprocess-based verification in target Python)

**Files to Modify:**
- `src/claude_mpm/utils/robust_installer.py` (primary)
- `src/claude_mpm/utils/agent_dependency_loader.py` (secondary)

**Testing Required:**
- UV tool environment tests
- Virtual environment tests
- System Python tests
- PEP 668 managed environment tests
