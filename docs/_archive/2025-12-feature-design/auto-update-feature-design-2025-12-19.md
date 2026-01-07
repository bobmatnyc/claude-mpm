# Auto-Update Feature Design for Claude MPM

**Research Date**: 2025-12-19
**Status**: Design Complete
**Priority**: High (User Experience Enhancement)
**Complexity**: Medium (Requires careful install method detection)

---

## Executive Summary

This document outlines the design for an auto-update feature in claude-mpm that:

1. Checks PyPI for newer versions on startup (non-blocking)
2. Detects the installation method (pip, pipx, uv tool, brew, editable)
3. Offers to auto-update using the correct method
4. Integrates seamlessly with existing version checking infrastructure

The design leverages existing components and patterns from the codebase:

- **Existing**: `SelfUpgradeService` with pip/pipx/npm detection
- **Existing**: `PackageVersionChecker` for PyPI API integration
- **Existing**: `check_for_updates_async()` in startup.py (lines 1140-1238)
- **New**: UV tool and Homebrew detection logic
- **New**: Enhanced installation method detection

---

## Current State Analysis

### Existing Version Checking Infrastructure

**File**: `src/claude_mpm/services/self_upgrade_service.py`

**Current Capabilities**:
- ✅ PyPI version checking via `PackageVersionChecker`
- ✅ Installation method detection: pip, pipx, npm, editable
- ✅ Async startup checks (non-blocking)
- ✅ Claude Code compatibility checking
- ✅ Cached version checks (24-hour TTL)
- ✅ User prompts for upgrade confirmation
- ✅ Automatic restart after upgrade

**Current Limitations**:
- ❌ No UV tool detection
- ❌ No Homebrew detection
- ❌ No auto-upgrade option (requires manual confirmation)
- ❌ Limited integration with startup flow

### Installation Method Detection

**File**: `src/claude_mpm/core/unified_paths.py`

**Current Detection Logic** (lines 55-283):

```python
class DeploymentContext(Enum):
    DEVELOPMENT = "development"
    EDITABLE_INSTALL = "editable_install"
    PIP_INSTALL = "pip_install"
    PIPX_INSTALL = "pipx_install"
    SYSTEM_PACKAGE = "system_package"
```

**Detection Strategy**:
- Checks for editable install (pyproject.toml + src/ structure)
- Detects pipx via path patterns (`pipx` in module path)
- Detects system packages (`dist-packages` in path)
- Defaults to pip install for `site-packages`

**Gap**: No UV tool or Homebrew detection in `unified_paths.py`

### Existing Startup Hook

**File**: `src/claude_mpm/cli/startup.py` (lines 1140-1238)

**Function**: `check_for_updates_async()`

**Current Behavior**:
- Runs in background thread (non-blocking)
- Checks configuration for update settings
- Skips editable installs
- Calls `SelfUpgradeService.check_and_prompt_on_startup()`
- Displays update notifications (non-interactive)

**Configuration Keys**:
```python
updates_config = {
    "check_enabled": True,          # Enable/disable checks
    "check_frequency": "daily",     # daily, weekly, never
    "auto_upgrade": False,          # Auto-upgrade without prompt
    "check_claude_code": True       # Also check Claude Code version
}
```

---

## PyPI API Integration

### API Endpoint

**URL**: `https://pypi.org/pypi/{package_name}/json`

**Response Format**:
```json
{
  "info": {
    "name": "claude-mpm",
    "version": "5.4.8",
    "summary": "...",
    "home_page": "...",
    "author": "...",
    "license": "..."
  },
  "releases": {
    "5.4.8": [...],
    "5.4.7": [...]
  }
}
```

**Implementation**: `PackageVersionChecker` (archived in mcp_gateway)

**Key Features**:
- Async HTTP requests with 5-second timeout
- 24-hour cache TTL
- Version comparison using `packaging.version`
- Graceful failure handling

---

## Enhanced Installation Method Detection

### Installation Method Enumeration

**Extend**: `src/claude_mpm/services/self_upgrade_service.py`

```python
class InstallationMethod:
    """Installation method enumeration."""

    PIP = "pip"
    PIPX = "pipx"
    NPM = "npm"
    UV_TOOL = "uv_tool"      # NEW
    HOMEBREW = "homebrew"    # NEW
    EDITABLE = "editable"
    UNKNOWN = "unknown"
```

### Detection Strategy

**Priority Order** (highest to lowest):

1. **Editable Install Detection** (existing)
   - Check `DeploymentContext.DEVELOPMENT` or `EDITABLE_INSTALL`
   - Verify `pyproject.toml` + `.git` + `src/` structure
   - **Skip auto-update**: User manages manually

2. **UV Tool Detection** (NEW)
   - Check for UV environment variable: `UV_TOOL_DIR`
   - Check executable path: `~/.local/bin/claude-mpm` + `uv tool list` contains claude-mpm
   - Check UV cache: `~/.local/share/uv/tools/claude-mpm`
   - **Upgrade command**: `uv tool upgrade claude-mpm`

3. **Homebrew Detection** (NEW)
   - Check executable path patterns:
     - macOS (Apple Silicon): `/opt/homebrew/bin/claude-mpm`
     - macOS (Intel): `/usr/local/bin/claude-mpm`
   - Verify with `brew list | grep claude-mpm`
   - **Upgrade command**: `brew upgrade claude-mpm`

4. **Pipx Detection** (existing)
   - Check for `pipx` in `sys.executable` path
   - Check pipx venv patterns: `.local/pipx/venvs/claude-mpm`
   - **Upgrade command**: `pipx upgrade claude-mpm`

5. **NPM Detection** (existing)
   - Run `npm list -g claude-mpm`
   - **Upgrade command**: `npm update -g claude-mpm`

6. **Pip Detection** (fallback)
   - Default for `site-packages` installs
   - **Upgrade command**: `python -m pip install --upgrade claude-mpm`

### Implementation Code

**Location**: `src/claude_mpm/services/self_upgrade_service.py`

```python
def _detect_installation_method(self) -> str:
    """
    Detect how claude-mpm was installed.

    Returns:
        Installation method constant
    """
    # 1. Check for editable install (HIGHEST PRIORITY)
    if PathContext.detect_deployment_context().name in [
        "DEVELOPMENT",
        "EDITABLE_INSTALL",
    ]:
        return InstallationMethod.EDITABLE

    # 2. Check for UV tool (NEW)
    uv_check = self._check_uv_tool_installation()
    if uv_check:
        return InstallationMethod.UV_TOOL

    # 3. Check for Homebrew (NEW)
    brew_check = self._check_homebrew_installation()
    if brew_check:
        return InstallationMethod.HOMEBREW

    # 4. Check for pipx (existing)
    executable = sys.executable
    if "pipx" in executable:
        return InstallationMethod.PIPX

    # 5. Check for npm (existing)
    try:
        result = subprocess.run(
            ["npm", "list", "-g", "claude-mpm"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0 and "claude-mpm" in result.stdout:
            return InstallationMethod.NPM
    except Exception:
        pass

    # 6. Default to pip
    return InstallationMethod.PIP


def _check_uv_tool_installation(self) -> bool:
    """
    Check if claude-mpm was installed via uv tool.

    Detection strategy:
    1. Check UV_TOOL_DIR environment variable
    2. Check if executable is in ~/.local/bin/ AND uv tool list contains claude-mpm
    3. Check UV cache directory for claude-mpm

    Returns:
        True if installed via uv tool, False otherwise
    """
    try:
        # Strategy 1: Check environment variable
        if os.environ.get("UV_TOOL_DIR"):
            self.logger.debug("Detected UV_TOOL_DIR environment variable")
            return True

        # Strategy 2: Check executable path + uv tool list
        executable = sys.executable
        if "/.local/bin/" in executable or "/.local/share/uv/" in executable:
            # Verify with uv tool list
            try:
                result = subprocess.run(
                    ["uv", "tool", "list"],
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode == 0 and "claude-mpm" in result.stdout:
                    self.logger.debug("Detected uv tool installation via uv tool list")
                    return True
            except (FileNotFoundError, subprocess.TimeoutExpired):
                pass

        # Strategy 3: Check UV cache directory
        uv_tool_cache = Path.home() / ".local" / "share" / "uv" / "tools" / "claude-mpm"
        if uv_tool_cache.exists():
            self.logger.debug(f"Detected uv tool cache at {uv_tool_cache}")
            return True

    except Exception as e:
        self.logger.debug(f"UV tool detection failed: {e}")

    return False


def _check_homebrew_installation(self) -> bool:
    """
    Check if claude-mpm was installed via Homebrew.

    Detection strategy:
    1. Check executable path patterns (macOS only)
    2. Verify with brew list command

    Returns:
        True if installed via Homebrew, False otherwise
    """
    # Only check on macOS
    if sys.platform != "darwin":
        return False

    try:
        # Strategy 1: Check executable path
        executable = sys.executable
        brew_patterns = [
            "/opt/homebrew/",      # Apple Silicon
            "/usr/local/Cellar/",  # Intel Mac
            "/usr/local/opt/",     # Intel Mac (linked)
        ]

        if any(pattern in executable for pattern in brew_patterns):
            self.logger.debug(f"Detected Homebrew path pattern in {executable}")
            return True

        # Strategy 2: Check brew list
        try:
            result = subprocess.run(
                ["brew", "list"],
                check=False,
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0 and "claude-mpm" in result.stdout:
                self.logger.debug("Detected claude-mpm in brew list")
                return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            # brew not installed or command timed out
            pass

    except Exception as e:
        self.logger.debug(f"Homebrew detection failed: {e}")

    return False
```

---

## Upgrade Command Mapping

**Location**: `src/claude_mpm/services/self_upgrade_service.py`

**Method**: `_get_upgrade_command()`

```python
def _get_upgrade_command(self) -> str:
    """
    Get the appropriate upgrade command for current installation method.

    Returns:
        Shell command string to upgrade claude-mpm
    """
    if self.installation_method == InstallationMethod.UV_TOOL:
        return "uv tool upgrade claude-mpm"

    if self.installation_method == InstallationMethod.HOMEBREW:
        return "brew upgrade claude-mpm"

    if self.installation_method == InstallationMethod.PIPX:
        return "pipx upgrade claude-mpm"

    if self.installation_method == InstallationMethod.NPM:
        return "npm update -g claude-mpm"

    if self.installation_method == InstallationMethod.PIP:
        return f"{sys.executable} -m pip install --upgrade claude-mpm"

    if self.installation_method == InstallationMethod.EDITABLE:
        return "git pull && pip install -e ."

    return "pip install --upgrade claude-mpm"
```

---

## Auto-Update Workflow

### Startup Integration

**File**: `src/claude_mpm/cli/startup.py`

**Function**: `check_for_updates_async()` (lines 1140-1238)

**Enhanced Workflow**:

```
1. Check configuration
   ├─ updates.check_enabled = False → Skip
   ├─ updates.check_frequency = "never" → Skip
   └─ Continue

2. Detect installation method
   ├─ Editable install → Skip (developer manages)
   └─ Continue

3. Check PyPI for updates (async)
   ├─ Cached result (< 24h) → Use cache
   ├─ Network timeout → Fail gracefully
   └─ Fetch version from PyPI API

4. Compare versions
   ├─ No update available → End
   └─ Update available → Continue

5. Auto-upgrade decision
   ├─ updates.auto_upgrade = True → Upgrade immediately
   └─ updates.auto_upgrade = False → Display notification only

6. Execute upgrade command
   ├─ Run installation-specific upgrade command
   ├─ Capture output/errors
   └─ Handle failures gracefully

7. Restart (optional)
   ├─ Successful upgrade → Offer restart
   └─ Failed upgrade → Log error, continue
```

### Configuration Schema

**File**: `~/.claude-mpm/config.json` (user-level) or `.claude-mpm/config.json` (project-level)

```json
{
  "updates": {
    "check_enabled": true,
    "check_frequency": "daily",
    "auto_upgrade": false,
    "check_claude_code": true,
    "last_check_timestamp": "2025-12-19T10:00:00Z"
  }
}
```

**Configuration Keys**:

- `check_enabled` (bool): Enable/disable update checks (default: `true`)
- `check_frequency` (string): `"daily"`, `"weekly"`, `"never"` (default: `"daily"`)
- `auto_upgrade` (bool): Auto-upgrade without user confirmation (default: `false`)
- `check_claude_code` (bool): Also check Claude Code version (default: `true`)
- `last_check_timestamp` (ISO 8601): Timestamp of last check (for frequency control)

---

## Implementation Plan

### Phase 1: Enhanced Detection (Priority: High)

**File**: `src/claude_mpm/services/self_upgrade_service.py`

**Tasks**:
1. ✅ Add `UV_TOOL` and `HOMEBREW` to `InstallationMethod` enum
2. ✅ Implement `_check_uv_tool_installation()` method
3. ✅ Implement `_check_homebrew_installation()` method
4. ✅ Update `_detect_installation_method()` with new checks
5. ✅ Update `_get_upgrade_command()` with new commands
6. ✅ Add unit tests for new detection logic

**Estimated Effort**: 4-6 hours

### Phase 2: Auto-Upgrade Logic (Priority: High)

**File**: `src/claude_mpm/services/self_upgrade_service.py`

**Tasks**:
1. ✅ Enhance `perform_upgrade()` to support all install methods
2. ✅ Add upgrade command validation before execution
3. ✅ Improve error handling and user feedback
4. ✅ Add rollback mechanism for failed upgrades (optional)

**Estimated Effort**: 3-4 hours

### Phase 3: Startup Integration (Priority: Medium)

**File**: `src/claude_mpm/cli/startup.py`

**Tasks**:
1. ✅ Update `check_for_updates_async()` with enhanced logic
2. ✅ Add frequency-based check control (daily/weekly)
3. ✅ Integrate auto-upgrade configuration flag
4. ✅ Add user notification improvements

**Estimated Effort**: 2-3 hours

### Phase 4: Configuration & Testing (Priority: Medium)

**Tasks**:
1. ✅ Add `updates` section to default config schema
2. ✅ Create configuration migration for existing users
3. ✅ Write integration tests for all install methods
4. ✅ Test upgrade workflow end-to-end
5. ✅ Document configuration options in user guide

**Estimated Effort**: 4-5 hours

---

## Testing Strategy

### Unit Tests

**File**: `tests/services/test_self_upgrade_service.py`

**Test Cases**:
1. ✅ `test_detect_uv_tool_installation()`
   - Mock UV environment variable
   - Mock UV tool list output
   - Mock UV cache directory

2. ✅ `test_detect_homebrew_installation()`
   - Mock macOS platform
   - Mock brew list output
   - Mock executable paths

3. ✅ `test_get_upgrade_command_all_methods()`
   - Verify correct command for each install method
   - Edge cases (unknown method)

4. ✅ `test_version_comparison()`
   - Current = Latest → No update
   - Current < Latest → Update available
   - Current > Latest → No update (dev build)

### Integration Tests

**File**: `tests/integration/test_auto_update_flow.py`

**Test Scenarios**:
1. ✅ End-to-end update check with mock PyPI response
2. ✅ Auto-upgrade disabled → Display notification only
3. ✅ Auto-upgrade enabled → Execute upgrade command
4. ✅ Network timeout → Graceful failure
5. ✅ Editable install → Skip update check

### Manual Testing Checklist

**Installation Method Testing**:
- [ ] Test on pip install (virtualenv)
- [ ] Test on pipx install
- [ ] Test on UV tool install
- [ ] Test on Homebrew install (macOS)
- [ ] Test on editable install (dev mode)

**Configuration Testing**:
- [ ] Verify `check_enabled = false` skips checks
- [ ] Verify `check_frequency = "weekly"` respects interval
- [ ] Verify `auto_upgrade = true` upgrades without prompt
- [ ] Verify `check_claude_code = true` includes Claude Code check

**Edge Cases**:
- [ ] No internet connection → Graceful failure
- [ ] PyPI API timeout → Use cached version
- [ ] Upgrade command fails → Display error, continue
- [ ] Multiple install methods detected → Prioritize correctly

---

## User Experience Design

### Update Notification (Non-Interactive)

**Displayed When**: Update available, `auto_upgrade = false`

**Format**:
```
ℹ️  Update available: v5.4.8 → v5.5.0
   Run: uv tool upgrade claude-mpm
   Release notes: https://github.com/bobmatnyc/claude-mpm/releases/tag/v5.5.0
```

**Design Goals**:
- ✅ Non-blocking (doesn't interrupt workflow)
- ✅ Clear upgrade command for user's install method
- ✅ Link to release notes for transparency
- ✅ Single-line notification (minimal distraction)

### Auto-Upgrade Notification (Interactive)

**Displayed When**: Update available, `auto_upgrade = true`, first check

**Format**:
```
======================================================================
📢 Auto-Upgrade Available for claude-mpm
======================================================================
   Current: v5.4.8
   Latest:  v5.5.0
   Method:  uv tool

   Upgrade: uv tool upgrade claude-mpm
   Release: https://github.com/bobmatnyc/claude-mpm/releases/tag/v5.5.0
======================================================================

Would you like to upgrade now? [y/N]:
```

**Design Goals**:
- ✅ Clear visual separation (box formatting)
- ✅ Shows installation method context
- ✅ User confirmation required (safety)
- ✅ Link to release notes for review

### Post-Upgrade Messages

**Success**:
```
✅ Successfully upgraded to v5.5.0

🔄 Restart claude-mpm to use the new version.
   Run: claude-mpm --version
```

**Failure**:
```
❌ Upgrade failed: Command 'uv tool upgrade claude-mpm' returned non-zero exit status 1

Please try upgrading manually:
   uv tool upgrade claude-mpm

Or report this issue at:
   https://github.com/bobmatnyc/claude-mpm/issues
```

---

## Security Considerations

### Command Injection Prevention

**Risk**: User input in upgrade commands

**Mitigation**:
- ✅ Use hardcoded upgrade commands (no user input interpolation)
- ✅ Use `subprocess.run()` with `shell=False` when possible
- ✅ Validate version strings match semver format before comparison

### Update Source Verification

**Risk**: Man-in-the-middle attacks on PyPI API

**Mitigation**:
- ✅ Use HTTPS for all PyPI API requests
- ✅ Verify TLS certificates (aiohttp default behavior)
- ✅ Optional: Verify package signatures (future enhancement)

### Configuration Validation

**Risk**: Malicious configuration injection

**Mitigation**:
- ✅ Validate configuration schema on load
- ✅ Use boolean/enum types (not arbitrary strings)
- ✅ Reject unknown configuration keys

---

## Performance Considerations

### Startup Impact

**Current Overhead**:
- Version check: ~5 seconds (with 5s timeout)
- Cache check: ~1ms (local file read)
- Detection logic: ~10ms (subprocess calls)

**Optimization Strategies**:
1. ✅ **Cache First**: Read cache before network request (existing)
2. ✅ **Background Thread**: Run in daemon thread (existing)
3. ✅ **Short Timeout**: 5-second PyPI API timeout (existing)
4. ✅ **Frequency Control**: Respect `check_frequency` setting (new)

**Target Overhead**: < 50ms (when cached), < 5s (when checking network)

### Memory Impact

**Estimated Memory Usage**:
- Version checker: ~500KB (HTTP client + JSON parsing)
- Cached data: ~1KB per package
- Thread overhead: ~8MB (Python thread stack)

**Total Impact**: ~10MB (negligible for CLI application)

---

## Documentation Updates

### User Documentation

**File**: `docs/user/auto-updates.md` (NEW)

**Sections**:
1. Overview of auto-update feature
2. Configuration options
3. Install method detection
4. Manual upgrade commands
5. Troubleshooting guide

**File**: `docs/getting-started/installation.md` (UPDATE)

**Updates**:
- Add auto-update behavior note for each install method
- Explain how to disable auto-updates
- Link to auto-updates.md for details

### Developer Documentation

**File**: `docs/developer/architecture.md` (UPDATE)

**Updates**:
- Document `SelfUpgradeService` architecture
- Explain installation method detection logic
- Document PyPI API integration

**File**: `CHANGELOG.md` (UPDATE)

**Entry**:
```markdown
## [5.5.0] - 2025-12-XX

### Added
- Auto-update feature with install method detection (pip, pipx, uv tool, brew)
- Configuration options for update frequency and auto-upgrade
- Enhanced installation method detection for UV tool and Homebrew
- Non-blocking startup version checks with 24-hour cache

### Changed
- `SelfUpgradeService` now supports UV tool and Homebrew installs
- `check_for_updates_async()` respects `check_frequency` configuration
- Update notifications include install method context

### Fixed
- Installation method detection false positives
- PyPI API timeout handling
```

---

## Rollout Strategy

### Beta Testing (Week 1)

**Target**: Internal testing + Early adopters

**Tasks**:
1. Deploy with `auto_upgrade = false` by default
2. Test on all supported install methods
3. Gather user feedback on notifications
4. Fix critical bugs

### Gradual Rollout (Week 2-3)

**Target**: All users

**Tasks**:
1. Release with feature documentation
2. Monitor error rates via telemetry (if enabled)
3. Update FAQ based on support tickets
4. Fine-tune notification messaging

### Full Deployment (Week 4)

**Target**: General availability

**Tasks**:
1. Enable `check_enabled = true` by default
2. Announce feature in release notes
3. Update social media / blog post
4. Monitor adoption rates

---

## Future Enhancements

### Phase 2 Features (Post-Launch)

1. **Selective Dependency Updates**
   - Check for updates to critical dependencies (kuzu-memory, mcp-vector-search)
   - Prompt for dependency upgrades when claude-mpm updates

2. **Changelog Integration**
   - Fetch and display changelog excerpt in update notification
   - Highlight breaking changes or critical fixes

3. **Update Channels**
   - Support beta/canary update channels
   - Allow users to opt into pre-release versions

4. **Rollback Mechanism**
   - Backup current version before upgrade
   - One-command rollback if issues occur

5. **Telemetry Integration**
   - Track upgrade success/failure rates (opt-in)
   - Identify problematic install methods
   - Improve detection heuristics based on real data

---

## Risks and Mitigations

### Risk: Broken Upgrades

**Scenario**: Upgrade command fails, leaving installation in broken state

**Mitigation**:
- ✅ Test upgrade commands before execution
- ✅ Provide clear error messages with manual instructions
- ✅ Document rollback procedure in troubleshooting guide
- 🔮 Future: Implement automatic rollback on failure

**Severity**: Medium
**Likelihood**: Low (tested upgrade commands)

### Risk: Network Dependency

**Scenario**: PyPI API unavailable, update checks fail

**Mitigation**:
- ✅ 24-hour cache prevents repeated failures
- ✅ Graceful failure (log warning, continue execution)
- ✅ User can disable checks with `check_enabled = false`

**Severity**: Low (non-critical feature)
**Likelihood**: Medium (network reliability varies)

### Risk: Install Method Misdetection

**Scenario**: Wrong install method detected, incorrect upgrade command executed

**Mitigation**:
- ✅ Multi-strategy detection with fallbacks
- ✅ Log detection results for debugging
- ✅ User can override via configuration (future enhancement)

**Severity**: High (broken installation)
**Likelihood**: Low (comprehensive detection logic)

---

## Success Metrics

### Key Performance Indicators

1. **Adoption Rate**
   - Target: >70% of users with auto-update enabled after 30 days
   - Measure: Configuration telemetry (opt-in)

2. **Upgrade Success Rate**
   - Target: >95% successful upgrades
   - Measure: Error logs + user reports

3. **Detection Accuracy**
   - Target: >99% correct install method detection
   - Measure: User-reported misdetection rate

4. **User Satisfaction**
   - Target: <5% negative feedback on auto-update feature
   - Measure: GitHub issues + support tickets

5. **Time to Latest Version**
   - Target: Reduce median time from release to user upgrade by 50%
   - Measure: Version distribution telemetry

---

## Recommended File Locations

### Implementation Files

1. **Core Service** (Existing + Enhancements)
   - `src/claude_mpm/services/self_upgrade_service.py`
   - Add UV tool and Homebrew detection methods
   - Enhance upgrade command logic

2. **Startup Integration** (Existing + Enhancements)
   - `src/claude_mpm/cli/startup.py`
   - Update `check_for_updates_async()` function
   - Add frequency control logic

3. **Configuration Schema** (New Section)
   - `src/claude_mpm/config/schema.py` (if exists)
   - Add `updates` configuration section

### Test Files

1. **Unit Tests** (New)
   - `tests/services/test_self_upgrade_service.py`
   - Test detection methods
   - Test upgrade command generation

2. **Integration Tests** (New)
   - `tests/integration/test_auto_update_flow.py`
   - End-to-end update workflow tests

### Documentation Files

1. **User Guide** (New)
   - `docs/user/auto-updates.md`
   - Configuration reference
   - Troubleshooting guide

2. **Developer Guide** (Update)
   - `docs/developer/architecture.md`
   - Document auto-update architecture

---

## Conclusion

This design provides a comprehensive, non-blocking auto-update feature that:

✅ **Respects User Control**: Configurable, opt-in auto-upgrade
✅ **Supports All Install Methods**: pip, pipx, uv tool, brew, editable
✅ **Minimizes Startup Impact**: Background checks with caching
✅ **Fails Gracefully**: Never breaks existing functionality
✅ **Clear User Feedback**: Informative notifications and error messages

The implementation leverages existing infrastructure (`SelfUpgradeService`, `PackageVersionChecker`) while adding targeted enhancements for UV tool and Homebrew support. The design prioritizes stability, user experience, and minimal invasiveness.

**Next Steps**:
1. Review and approve design with maintainers
2. Implement Phase 1 (Enhanced Detection)
3. Create PR with comprehensive tests
4. Begin beta testing with early adopters
5. Iterate based on feedback

---

**Design Status**: ✅ Complete
**Approval Required**: Yes
**Implementation Ready**: Yes
**Estimated Timeline**: 2-3 weeks (design → beta → release)
