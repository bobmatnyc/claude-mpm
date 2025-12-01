# Progress Bar Implementation Analysis
**Date**: 2025-12-01
**Research Focus**: Existing progress bar implementation for "Launching Claude..." indicator
**Status**: ✅ Complete

## Executive Summary

The project uses a custom `ProgressBar` class located in `/Users/masa/Projects/claude-mpm/src/claude_mpm/utils/progress.py` for all agent/skill sync operations. This provides a consistent, terminal-aware progress indicator that can be reused for the "Launching Claude..." startup message.

**Key Findings**:
- ✅ Custom `ProgressBar` class (not tqdm/rich) - zero dependencies
- ✅ TTY-aware with graceful degradation (no progress bar in pipes/CI)
- ✅ Unicode block characters (█ filled, ░ empty)
- ✅ Configurable prefix, percentage, counter, bar width
- ✅ Context manager support for automatic cleanup
- ✅ Throttled updates (10 Hz) to prevent output flooding
- ✅ Terminal width detection to prevent overflow

**Recommendation**: Use existing `ProgressBar` class with indeterminate mode for "Launching Claude..." indicator.

---

## 1. Progress Bar Class Location

**File**: `/Users/masa/Projects/claude-mpm/src/claude_mpm/utils/progress.py`
**Lines**: 1-366
**Class**: `ProgressBar`

**Design Philosophy**:
- Pure Python, no external dependencies (rejected tqdm as overkill)
- Terminal-aware with TTY detection
- ASCII/Unicode hybrid for compatibility
- Throttled updates for performance

---

## 2. Current Usage Examples

### Agent Sync Progress Bar (startup.py:338-343)

```python
deploy_progress = ProgressBar(
    total=agent_count,
    prefix="Deploying agents",
    show_percentage=True,
    show_counter=True,
)
```

**Output Example**:
```
Deploying agents [████████████░░░░░░░░] 60% (30/50) research.md
```

### Skills Sync Progress Bar (startup.py:488-493)

```python
sync_progress = ProgressBar(
    total=total_file_count if total_file_count > 0 else 1,
    prefix="Syncing skills",
    show_percentage=True,
    show_counter=True,
)
```

**Output Example**:
```
Syncing skills [███████████████████░] 95% (142/150)
```

---

## 3. Progress Bar Features

### Core Features

| Feature | Description | Default |
|---------|-------------|---------|
| **Prefix** | Message before bar (e.g., "Syncing agents") | `"Progress"` |
| **Bar Width** | Character width of progress bar | `20` |
| **Percentage** | Show percentage complete | `True` |
| **Counter** | Show current/total (e.g., "45/50") | `True` |
| **TTY Detection** | Auto-disable in non-TTY environments | Auto-detect |
| **Throttling** | Update frequency limit (10 Hz) | `0.1s` |
| **Terminal Width** | Auto-detect to prevent overflow | `80` fallback |

### Unicode Characters

```python
bar = "█" * filled + "░" * (self.bar_width - filled)
```

- **Filled**: `█` (U+2588 FULL BLOCK)
- **Empty**: `░` (U+2591 LIGHT SHADE)
- **Rationale**: Better visual clarity than ASCII chars (`#`, `-`)

### TTY Detection Logic

```python
def _is_tty(self) -> bool:
    """Check if stdout is a TTY (interactive terminal)."""
    try:
        return sys.stdout.isatty()
    except AttributeError:
        return False
```

**Behavior**:
- **TTY (interactive)**: Animated progress bar with `\r` overwriting
- **Non-TTY (CI/logs)**: Milestone logging (0%, 25%, 50%, 75%, 100%)
- **Piped/redirected**: No progress bar, only milestones

---

## 4. Progress Bar API

### Constructor Signature

```python
ProgressBar(
    total: int,
    prefix: str = "Progress",
    bar_width: int = 20,
    show_percentage: bool = True,
    show_counter: bool = True,
    enabled: Optional[bool] = None,  # Override TTY detection
)
```

### Key Methods

#### `update(current: int, message: str = "")`
Update progress to specific value with optional message.

```python
pb.update(50, message="agent.md")
# Output: Syncing agents [████████████░░░░░░░░] 50% (50/100) agent.md
```

#### `finish(message: str = "Complete")`
Complete progress bar and print final message with newline.

```python
pb.finish(message="Complete: 45 agents deployed")
# Output: Syncing agents [████████████████████] 100% (45/45) Complete: 45 agents deployed
```

#### Context Manager Support

```python
with ProgressBar(100, prefix="Processing") as pb:
    for i in range(100):
        pb.update(i + 1)
# Automatically calls finish() on exit
```

---

## 5. Integration Points in startup.py

### Current Startup Flow (startup.py:580-608)

```python
def run_background_services():
    """Initialize all background services on startup."""
    initialize_project_registry()
    check_mcp_auto_configuration()
    verify_mcp_gateway_startup()
    check_for_updates_async()
    sync_remote_agents_on_startup()  # ← Uses progress bar
    deploy_bundled_skills()
    sync_remote_skills_on_startup()  # ← Uses progress bar
    discover_and_link_runtime_skills()
    deploy_output_style_on_startup()
```

### Proposed Integration Point

**Add "Launching Claude..." before `run_background_services()` in `cli/__init__.py`**

**Current Code** (cli/__init__.py main()):
```python
# Run background services if not skipped
if not skip_background:
    from .startup import run_background_services
    run_background_services()
```

**Proposed Code**:
```python
# Show startup progress indicator
if not skip_background:
    from .utils.progress import ProgressBar
    from .startup import run_background_services

    # Indeterminate progress (spinner-like)
    launch_progress = ProgressBar(
        total=100,
        prefix="Launching Claude",
        show_percentage=False,
        show_counter=False,
    )

    try:
        # Start progress
        launch_progress.update(0)

        # Run background services
        run_background_services()

        # Complete progress
        launch_progress.finish(message="Ready")
    except Exception as e:
        launch_progress.finish(message="Failed")
        raise
```

**Output**:
```
Launching Claude [░░░░░░░░░░░░░░░░░░░░]
[Background services run...]
Launching Claude [████████████████████] Ready
```

---

## 6. Recommended Approach for "Launching Claude..."

### Option 1: Indeterminate Progress (Recommended)

**Use Case**: When total steps are unknown or variable.

**Implementation**:
```python
launch_progress = ProgressBar(
    total=100,
    prefix="Launching Claude",
    show_percentage=False,
    show_counter=False,
    bar_width=30,
)

# Update with phases
launch_progress.update(10, message="Checking MCP")
launch_progress.update(30, message="Syncing agents")
launch_progress.update(60, message="Deploying skills")
launch_progress.update(90, message="Finalizing")
launch_progress.finish(message="Ready")
```

**Output**:
```
Launching Claude [░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░] Checking MCP
Launching Claude [███░░░░░░░░░░░░░░░░░░░░░░░░░░░] Syncing agents
Launching Claude [██████████████████░░░░░░░░░░░░] Deploying skills
Launching Claude [████████████████████████████░░] Finalizing
Launching Claude [██████████████████████████████] Ready
```

### Option 2: Simple Spinner (Alternative)

**Use Case**: When progress tracking is not important.

**Implementation**:
```python
# Show simple spinner without bar
print("Launching Claude...", end="", flush=True)

# Run services
run_background_services()

# Clear and show completion
print("\r" + " " * 30 + "\r✓ Claude ready", flush=True)
```

**Output**:
```
Launching Claude...
✓ Claude ready
```

### Option 3: Phase-Based Progress (Most Detailed)

**Use Case**: When user needs visibility into each startup phase.

**Implementation**:
```python
launch_progress = ProgressBar(
    total=7,  # 7 background services
    prefix="Launching Claude",
    show_percentage=True,
    show_counter=True,
)

# Update after each service
launch_progress.update(1, message="Project registry")
launch_progress.update(2, message="MCP configuration")
launch_progress.update(3, message="Gateway verification")
launch_progress.update(4, message="Update check")
launch_progress.update(5, message="Agent sync")
launch_progress.update(6, message="Skills deployment")
launch_progress.update(7, message="Output style")
launch_progress.finish(message="Complete")
```

**Output**:
```
Launching Claude [█████░░░░░░░░░░░░░░░] 28% (2/7) MCP configuration
Launching Claude [██████████░░░░░░░░░░] 57% (4/7) Update check
Launching Claude [████████████████████] 100% (7/7) Complete
```

---

## 7. Implementation Details

### File Locations

| Component | File | Lines |
|-----------|------|-------|
| ProgressBar class | `/src/claude_mpm/utils/progress.py` | 40-334 |
| Agent sync usage | `/src/claude_mpm/cli/startup.py` | 338-370 |
| Skills sync usage | `/src/claude_mpm/cli/startup.py` | 488-552 |
| Main entry point | `/src/claude_mpm/cli/__init__.py` | TBD |

### Integration Steps

1. **Import ProgressBar in cli/__init__.py**
   ```python
   from claude_mpm.utils.progress import ProgressBar
   ```

2. **Create progress instance before `run_background_services()`**
   ```python
   launch_progress = ProgressBar(
       total=100,
       prefix="Launching Claude",
       show_percentage=False,
       show_counter=False,
   )
   ```

3. **Update progress during startup**
   - Option A: Single update at start, finish at end (simple)
   - Option B: Track each service completion (detailed)
   - Option C: Phases with major milestones (recommended)

4. **Handle errors gracefully**
   ```python
   try:
       launch_progress.update(0)
       run_background_services()
       launch_progress.finish(message="Ready")
   except Exception as e:
       launch_progress.finish(message="Failed")
       raise
   ```

---

## 8. Style Consistency

### Current Agent Sync Output

```
Deploying agents [████████████████████] 100% (45/45) Complete: 45 agents deployed
Deploying skills [████████████████████] 100% (150/150) Complete: 150 skills deployed
```

### Proposed "Launching Claude..." Output

**Option 1 (Matches agent sync style)**:
```
Launching Claude [██████████░░░░░░░░░░] 50% (3/6) Syncing agents
```

**Option 2 (Simpler, no counter)**:
```
Launching Claude [██████████░░░░░░░░░░] Syncing agents
```

**Option 3 (Minimal, no bar)**:
```
Launching Claude... Ready
```

**Recommendation**: Use Option 2 (simpler, no counter) to match the agent sync style without overwhelming the user with percentages for a fast operation.

---

## 9. Performance Considerations

### Progress Bar Overhead

| Operation | Time Complexity | Space Complexity | Expected Time |
|-----------|----------------|------------------|---------------|
| `__init__()` | O(1) | O(1) | <1ms |
| `update()` | O(1) | O(1) | <1ms |
| `finish()` | O(1) | O(1) | <1ms |
| TTY detection | O(1) | O(1) | <1ms |
| Terminal width | O(1) | O(1) | <1ms |

**Total Overhead**: Negligible (<5ms for entire startup progress tracking)

### Update Throttling

- **Frequency**: 10 Hz (max 10 updates/second)
- **Purpose**: Prevent terminal flooding
- **Impact**: Smooth animation without performance degradation

---

## 10. Error Handling

### TTY Detection Failure

```python
try:
    return sys.stdout.isatty()
except AttributeError:
    return False  # Graceful degradation to non-TTY mode
```

**Behavior**: Falls back to milestone logging (0%, 25%, 50%, 75%, 100%)

### Terminal Width Detection Failure

```python
try:
    size = os.get_terminal_size()
    return size.columns
except (OSError, AttributeError, ValueError):
    return 80  # Standard terminal width fallback
```

**Behavior**: Uses 80-character fallback, truncates output if needed

### Progress Bar Exception Handling

```python
def __exit__(self, exc_type, exc_val, exc_tb):
    if exc_type is not None:
        self.finish(message="Failed")  # Error message
    else:
        self.finish()  # Normal completion
```

**Behavior**: Always prints newline to prevent terminal corruption

---

## 11. Code Examples

### Current Agent Sync Pattern (startup.py:338-370)

```python
if agent_count > 0:
    # Create progress bar for deployment phase
    deploy_progress = ProgressBar(
        total=agent_count,
        prefix="Deploying agents",
        show_percentage=True,
        show_counter=True,
    )

    # Deploy agents with progress callback
    deploy_target = Path.home() / ".claude" / "agents"
    deployment_result = deployment_service.deploy_agents(
        target_dir=deploy_target,
        force_rebuild=False,
        deployment_mode="update",
    )

    # Update progress bar (single increment since deploy_agents is batch)
    deploy_progress.update(agent_count)

    # Finish deployment progress bar
    deployed = len(deployment_result.get("deployed", []))
    updated = len(deployment_result.get("updated", []))
    skipped = len(deployment_result.get("skipped", []))
    total_available = deployed + updated + skipped

    if deployed > 0 or updated > 0:
        deploy_progress.finish(
            f"Complete: {deployed} deployed, {updated} updated, "
            f"{skipped} already present ({total_available} total)"
        )
    else:
        deploy_progress.finish(
            f"Complete: {total_available} agents ready (all up-to-date)"
        )
```

### Proposed "Launching Claude..." Pattern

```python
def main(argv=None):
    # ... existing setup code ...

    # Show startup progress indicator
    if not skip_background:
        from .utils.progress import ProgressBar
        from .startup import run_background_services

        # Create progress bar with simple prefix
        launch_progress = ProgressBar(
            total=100,
            prefix="Launching Claude",
            show_percentage=False,
            show_counter=False,
            bar_width=25,
        )

        try:
            # Start progress
            launch_progress.update(10)

            # Run background services (existing function)
            run_background_services()

            # Complete progress
            launch_progress.finish(message="Ready")
        except Exception as e:
            # Show failure message
            launch_progress.finish(message="Failed")
            raise

    # ... rest of main() ...
```

---

## 12. Alternatives Considered

### Option A: tqdm Library (Rejected)

**Pros**:
- Well-tested, feature-rich
- Supports nested progress bars
- Automatic rate limiting

**Cons**:
- External dependency (adds ~500KB)
- Overkill for simple progress bars
- Complexity not needed for use case

**Decision**: Rejected in favor of custom implementation

### Option B: rich Library (Rejected)

**Pros**:
- Beautiful terminal output
- Spinner support
- Layout management

**Cons**:
- Large dependency (~2MB)
- Too heavyweight for CLI tool
- May conflict with terminal compatibility

**Decision**: Rejected in favor of lightweight custom solution

### Option C: Simple Print Statements (Rejected)

**Pros**:
- Zero dependencies
- Minimal code

**Cons**:
- No progress indication
- Poor user experience
- Inconsistent with rest of codebase

**Decision**: Rejected in favor of consistent progress bar

---

## 13. Recommendations

### For "Launching Claude..." Indicator

**Use existing `ProgressBar` class with simple configuration:**

```python
launch_progress = ProgressBar(
    total=100,
    prefix="Launching Claude",
    show_percentage=False,
    show_counter=False,
    bar_width=25,
)

# Simple update pattern
launch_progress.update(10)  # Start
run_background_services()
launch_progress.finish(message="Ready")
```

**Rationale**:
- ✅ Consistent with existing agent/skill sync style
- ✅ Zero new dependencies
- ✅ TTY-aware with graceful degradation
- ✅ Minimal code changes required
- ✅ Professional appearance

### Integration Approach

1. **Minimal Changes**: Add progress bar wrapper around `run_background_services()` call
2. **No Refactoring**: Don't modify `run_background_services()` internals
3. **Error Handling**: Use try/except to show "Failed" on errors
4. **Consistency**: Match existing progress bar style (prefix, bar width, unicode chars)

### Output Style

**Recommended**:
```
Launching Claude [█████░░░░░░░░░░░░░░░░░░░]
[Services run in background...]
Launching Claude [█████████████████████████] Ready
```

**Alternative (more minimal)**:
```
Launching Claude... Ready
```

---

## 14. Next Steps

1. **Locate main() entry point** in `/src/claude_mpm/cli/__init__.py`
2. **Add ProgressBar import**: `from claude_mpm.utils.progress import ProgressBar`
3. **Wrap `run_background_services()` call** with progress bar
4. **Test TTY and non-TTY modes** to ensure graceful degradation
5. **Verify output consistency** with existing agent/skill sync messages
6. **Add error handling** to show "Failed" message on exceptions

---

## 15. References

### Source Files

- **ProgressBar Implementation**: `/Users/masa/Projects/claude-mpm/src/claude_mpm/utils/progress.py`
- **Agent Sync Usage**: `/Users/masa/Projects/claude-mpm/src/claude_mpm/cli/startup.py` (lines 338-370)
- **Skills Sync Usage**: `/Users/masa/Projects/claude-mpm/src/claude_mpm/cli/startup.py` (lines 488-552)
- **Startup Flow**: `/Users/masa/Projects/claude-mpm/src/claude_mpm/cli/startup.py` (lines 580-608)

### Key Classes

- `ProgressBar` (lines 40-334)
- `run_background_services()` (lines 580-608)
- `sync_remote_agents_on_startup()` (lines 255-417)
- `sync_remote_skills_on_startup()` (lines 419-578)

### Unicode Characters

- U+2588 FULL BLOCK (█): Filled progress
- U+2591 LIGHT SHADE (░): Empty progress

---

## Appendix A: Full ProgressBar Class Signature

```python
class ProgressBar:
    def __init__(
        self,
        total: int,
        prefix: str = "Progress",
        bar_width: int = 20,
        show_percentage: bool = True,
        show_counter: bool = True,
        enabled: Optional[bool] = None,
    ):
        """Initialize progress bar."""

    def update(self, current: int, message: str = "") -> None:
        """Update progress bar to current position."""

    def finish(self, message: str = "Complete") -> None:
        """Complete progress bar and print final message."""

    def __enter__(self) -> "ProgressBar":
        """Context manager entry."""

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit - ensures finish() is called."""
```

---

## Appendix B: Terminal Output Examples

### TTY Mode (Interactive Terminal)

```
Launching Claude [█████░░░░░░░░░░░░░░░░░░░]
Launching Claude [██████████░░░░░░░░░░░░░░]
Launching Claude [███████████████░░░░░░░░░]
Launching Claude [████████████████████░░░░]
Launching Claude [█████████████████████████] Ready
```

### Non-TTY Mode (Logs/CI)

```
Launching Claude: 0/100 (0%)
Launching Claude: 25/100 (25%)
Launching Claude: 50/100 (50%)
Launching Claude: 75/100 (75%)
Launching Claude: 100/100 (100%) - Ready
```

---

**End of Research Report**
