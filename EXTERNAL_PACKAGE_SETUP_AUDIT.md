# External Package Setup Audit - Installation Mode Awareness

**Audit Date:** 2026-02-10
**Requirement:** ALL external package installers should detect claude-mpm's installation method and use the same method.

## Summary

| Service | Setup Method | Installation-Mode Aware? | Status | Location |
|---------|--------------|--------------------------|--------|----------|
| **mcp-vector-search** | `_setup_mcp_vector_search()` | ✅ YES | **CORRECT** | `setup.py:883-1051` |
| **kuzu-memory** | `_setup_kuzu_memory()` | ❌ NO | **NEEDS FIX** | `setup.py:645-881` |
| **google-workspace-mcp** | Delegates to OAuth | N/A | Not applicable | `setup.py:1053-1078` |
| **slack** | Bash script | N/A | Not applicable | `setup.py:331-389` |
| **notion** | Credentials only | N/A | Not applicable | `setup.py:448-517` |
| **confluence** | Credentials only | N/A | Not applicable | `setup.py:578-643` |

---

## Detailed Findings

### ✅ mcp-vector-search (CORRECT - Installation-Mode Aware)

**Location:** `src/claude_mpm/cli/commands/setup.py` lines 883-1051

**Code Pattern:**
```python
# Lines 904-929
from ...services.diagnostics.checks.installation_check import InstallationCheck

checker = InstallationCheck()
methods = checker._check_installation_method()

# Determine primary method (priority: pipx > uv > pip)
install_method = None
detected_methods = methods.details.get("methods_detected", [])

if "pipx" in detected_methods:
    install_method = "pipx"
elif any("uv" in str(p) for p in sys.path) or "uv" in sys.executable:
    install_method = "uv"
else:
    install_method = "pip"

# Lines 936-973: Install using detected method
if install_method == "pipx":
    subprocess.run(["pipx", "install", "mcp-vector-search"], ...)
elif install_method == "uv":
    subprocess.run(["uv", "tool", "install", "mcp-vector-search", "--python", "3.13"], ...)
elif install_method == "pip":
    subprocess.run([sys.executable, "-m", "pip", "install", "--user", "mcp-vector-search"], ...)
```

**Why It's Correct:**
- Uses `InstallationCheck` utility to detect how claude-mpm was installed
- Respects priority order: pipx > uv > pip
- Installs mcp-vector-search using the same method

---

### ❌ kuzu-memory (NEEDS FIX - Hardcoded to uv)

**Location:** `src/claude_mpm/cli/commands/setup.py` lines 645-881

**Current Code (INCORRECT):**
```python
# Lines 669-679
install_result = subprocess.run(
    [
        "uv",
        "tool",
        "install",
        "kuzu-memory>=1.6.33",
        "--python",
        "3.13",
    ],
    check=False,
)  # nosec B603 B607
```

**Problem:**
- Hardcoded to use `uv tool install`
- Does NOT detect claude-mpm's installation method
- Will fail if user installed claude-mpm via pip or pipx

**Required Fix:**
Apply the same pattern as mcp-vector-search:

```python
# Detect how claude-mpm was installed
from ...services.diagnostics.checks.installation_check import InstallationCheck

checker = InstallationCheck()
methods = checker._check_installation_method()

# Determine primary method (priority: pipx > uv > pip)
install_method = None
detected_methods = methods.details.get("methods_detected", [])

if "pipx" in detected_methods:
    install_method = "pipx"
elif any("uv" in str(p) for p in sys.path) or "uv" in sys.executable:
    install_method = "uv"
else:
    install_method = "pip"

console.print(f"[dim]Detected: {install_method} installation[/dim]")

# Install using detected method
if install_method == "pipx":
    subprocess.run(
        ["pipx", "install", "kuzu-memory>=1.6.33"],
        check=False,
    )
elif install_method == "uv":
    subprocess.run(
        ["uv", "tool", "install", "kuzu-memory>=1.6.33", "--python", "3.13"],
        check=False,
    )
elif install_method == "pip":
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "--user", "kuzu-memory>=1.6.33"],
        check=False,
    )
```

---

### N/A Services (No Package Installation)

These services do NOT install external packages, so installation-mode awareness is not applicable:

#### google-workspace-mcp
- **Setup:** Delegates to OAuth command (`manage_oauth`)
- **Behavior:** Only handles OAuth authentication, does NOT install packages
- **File:** `setup.py:1053-1078`
- **Note:** google-workspace-mpm package must be pre-installed by user

#### slack
- **Setup:** Runs bash script (`setup-slack-app.sh`)
- **Behavior:** Configures Slack app credentials, does NOT install packages
- **File:** `setup.py:331-389`
- **Note:** slack-user-proxy must be pre-installed by user

#### notion
- **Setup:** Collects API credentials only
- **Behavior:** Saves NOTION_API_KEY to .env.local
- **File:** `setup.py:448-517`
- **Note:** notion-mcp must be pre-installed by user

#### confluence
- **Setup:** Collects API credentials only
- **Behavior:** Saves CONFLUENCE_URL/EMAIL/TOKEN to .env.local
- **File:** `setup.py:578-643`
- **Note:** confluence-mcp must be pre-installed by user

---

## Recommendation

**IMMEDIATE ACTION REQUIRED:**

Fix `_setup_kuzu_memory()` at lines 645-881 in `src/claude_mpm/cli/commands/setup.py`:

1. Import `InstallationCheck` utility
2. Detect claude-mpm's installation method
3. Use the same method to install kuzu-memory
4. Follow the exact pattern from `_setup_mcp_vector_search()` (lines 904-977)

**Code Location to Fix:**
- File: `src/claude_mpm/cli/commands/setup.py`
- Function: `_setup_kuzu_memory`
- Lines: 669-679 (the subprocess.run call)

**Pattern to Replicate:**
Copy the installation detection and method selection logic from `_setup_mcp_vector_search()` lines 904-977.

---

## Verification Checklist

After fixing kuzu-memory setup:

- [ ] Test installation when claude-mpm installed via pip
- [ ] Test installation when claude-mpm installed via pipx
- [ ] Test installation when claude-mpm installed via uv
- [ ] Verify error messages guide users correctly
- [ ] Confirm fallback behavior works if detection fails

---

## Related Files

- `src/claude_mpm/services/diagnostics/checks/installation_check.py` - Detection utility
- `src/claude_mpm/cli/commands/setup.py` - All setup methods
- `src/claude_mpm/cli/commands/mcp_setup_external.py` - External MCP service setup (not used for kuzu-memory)
