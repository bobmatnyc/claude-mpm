# Agent Deployment Warnings Investigation

**Date**: 2025-12-19
**Investigator**: Research Agent
**Status**: Root Cause Identified

## Executive Summary

Two distinct warning issues were identified in the agent deployment system:

1. **YAML Frontmatter Warnings**: `AgentDiscoveryService` incorrectly scans PM instruction template files (`.md`) in `src/claude_mpm/agents/templates/` expecting YAML frontmatter for agent definitions
2. **JSON Template Parse Errors**: `MultiSourceAgentDeploymentService` attempts to read remote agents as JSON files when they are actually Markdown files with YAML frontmatter

Both issues stem from architectural confusion between:
- **PM Instruction Templates** (`.md` files without YAML frontmatter)
- **Legacy JSON Agent Templates** (`.json` files, now deprecated)
- **Remote Markdown Agents** (`.md` files with YAML frontmatter)

## Issue 1: YAML Frontmatter Warnings

### Root Cause

**File**: `src/claude_mpm/services/agents/deployment/agent_discovery_service.py`
**Lines**: 63-76 (in `list_available_agents()`)

```python
# Find all markdown template files with YAML frontmatter
template_files = list(self.templates_dir.glob("*.md"))

for template_file in template_files:
    try:
        agent_info = self._extract_agent_metadata(template_file)
        if agent_info:
            agents.append(agent_info)
```

**Problem**: `AgentDiscoveryService` is instantiated with `templates_dir` pointing to `src/claude_mpm/agents/templates/`, which contains:
- **PM instruction templates** (e.g., `circuit-breakers.md`, `pm-red-flags.md`, `git-file-tracking.md`)
- **Not agent definitions**

These files DO NOT have YAML frontmatter and are NOT agent definitions. They are instructional content for the PM agent.

### Evidence

```bash
$ ls -la /Users/masa/Projects/claude-mpm/src/claude_mpm/agents/templates/
total 496
-rw-r--r--@  1 masa  staff  48780 Dec 11 21:55 circuit-breakers.md
-rw-r--r--@  1 masa  staff  18842 Oct 21 08:20 git-file-tracking.md
-rw-r--r__@  1 masa  staff  13871 Nov 21 10:50 pm-red-flags.md
...
```

**Expected Behavior**: `AgentDiscoveryService` should only scan directories containing actual agent definitions (JSON or Markdown with YAML frontmatter), NOT PM instruction templates.

### Where It's Initialized

**File**: `src/claude_mpm/services/agents/deployment/agent_deployment.py`
**Line**: 164

```python
# Initialize discovery service (after templates_dir is set)
self.discovery_service = AgentDiscoveryService(self.templates_dir)
```

Where `self.templates_dir` is set on line 157:

```python
self.templates_dir = self.get_config_value(
    "templates_dir",
    default=templates_dir or paths.agents_dir / "templates",
)
```

**Resolution**: `paths.agents_dir / "templates"` → `src/claude_mpm/agents/templates/`

### Impact

- **User-facing**: Confusing warnings during agent deployment
- **Functionality**: No functional impact (warnings are cosmetic)
- **Code quality**: Indicates architectural confusion about directory purposes

## Issue 2: JSON Template Parse Errors

### Root Cause

**File**: `src/claude_mpm/services/agents/deployment/multi_source_deployment_service.py`
**Lines**: 830-841 (in `compare_deployed_versions()`)

```python
# Read template version
try:
    template_data = json.loads(template_path.read_text())  # ← PROBLEM
    metadata = template_data.get("metadata", {})
    template_version = self.version_manager.parse_version(
        template_data.get("agent_version")
        or template_data.get("version")
        or metadata.get("version", "0.0.0")
    )
except Exception as e:
    self.logger.warning(f"Error reading template for '{agent_name}': {e}")
```

**Problem**: Code assumes `template_path` points to a JSON file, but remote agents are **Markdown files with YAML frontmatter**.

### Evidence

Remote agents are discovered and stored as Markdown paths:

```python
# multi_source_deployment_service.py:189-192
if source_name == "remote":
    # Remote agents are Markdown, use RemoteAgentDiscoveryService
    remote_service = RemoteAgentDiscoveryService(source_dir)
    agents = remote_service.discover_remote_agents()
```

Remote agent file structure:

```bash
$ head -30 ~/.claude-mpm/cache/remote-agents/bobmatnyc/claude-mpm-agents/agents/qa/qa.md
---
name: QA
description: Memory-efficient testing with strategic sampling
version: 3.5.3
schema_version: 1.3.0
agent_id: qa-agent
agent_type: qa
model: sonnet
...
---
# QA Agent Instructions
...
```

**This is Markdown with YAML frontmatter, NOT JSON.**

### Where the Error Occurs

The error appears when `compare_deployed_versions()` tries to read version information from templates:

1. `discover_agents_from_all_sources()` → Returns remote agents with `.md` paths
2. `get_agents_for_deployment()` → Passes these paths as `agents_to_deploy`
3. `compare_deployed_versions()` → **Incorrectly tries to parse as JSON**

### Impact

- **User-facing**: Warning spam for all 41 remote agents
- **Functionality**: Version comparison fails for remote agents (they skip the comparison)
- **Code quality**: Architectural inconsistency between discovery and deployment stages

## Root Architectural Issues

### Directory Purpose Confusion

The codebase has three distinct types of directories that are being confused:

1. **PM Instruction Templates** (`src/claude_mpm/agents/templates/`)
   - Purpose: Instructional content for PM agent
   - Format: Markdown WITHOUT YAML frontmatter
   - Examples: `circuit-breakers.md`, `pm-red-flags.md`
   - Should NOT be scanned by `AgentDiscoveryService`

2. **Legacy JSON Agent Templates** (`src/claude_mpm/agents/templates/archive/`)
   - Purpose: Deprecated agent definitions
   - Format: JSON files
   - Examples: `engineer.json`, `qa.json`
   - Should be handled by legacy code paths

3. **Remote Markdown Agents** (`~/.claude-mpm/cache/remote-agents/`)
   - Purpose: Active agent definitions from GitHub
   - Format: Markdown with YAML frontmatter
   - Examples: `qa/qa.md`, `engineer/python.md`
   - Should be handled by `RemoteAgentDiscoveryService`

### Format Inconsistency

Two different agent formats are used:

1. **JSON Format** (legacy)
   ```json
   {
     "agent_id": "qa-agent",
     "version": "3.5.3",
     "metadata": { ... },
     "instructions": "..."
   }
   ```

2. **Markdown with YAML Format** (current)
   ```markdown
   ---
   name: QA
   version: 3.5.3
   agent_id: qa-agent
   ---
   # Instructions
   ```

**Problem**: Code in `compare_deployed_versions()` assumes JSON format for all sources, including remote agents.

## Recommended Fixes

### Fix 1: Exclude PM Instruction Templates from Agent Discovery

**File**: `src/claude_mpm/services/agents/deployment/agent_deployment.py`
**Line**: 164

**Current**:
```python
self.discovery_service = AgentDiscoveryService(self.templates_dir)
```

**Problem**: `self.templates_dir` points to `src/claude_mpm/agents/templates/` which contains PM instructions, not agents.

**Option A - Create Separate Directory for JSON Agent Templates**:

```python
# Create a dedicated directory for JSON agent templates
json_templates_dir = paths.agents_dir / "json_templates"
self.discovery_service = AgentDiscoveryService(json_templates_dir)
```

Then move any remaining JSON templates from `templates/` to `json_templates/`.

**Option B - Filter PM Instruction Files in AgentDiscoveryService**:

Add filtering logic to skip files without YAML frontmatter:

```python
# agent_discovery_service.py:63-76
template_files = list(self.templates_dir.glob("*.md"))

for template_file in template_files:
    try:
        agent_info = self._extract_agent_metadata(template_file)
        if agent_info:
            agents.append(agent_info)
        # If _extract_agent_metadata returns None (no frontmatter), skip silently
    except Exception as e:
        # Only log actual errors, not missing frontmatter
        if "frontmatter" not in str(e).lower():
            self.logger.error(f"Failed to process template {template_file.name}: {e}")
```

**Recommendation**: Use Option A to maintain clear separation of concerns.

### Fix 2: Handle Markdown Templates in Version Comparison

**File**: `src/claude_mpm/services/agents/deployment/multi_source_deployment_service.py`
**Lines**: 830-841

**Current**:
```python
# Read template version
try:
    template_data = json.loads(template_path.read_text())
    metadata = template_data.get("metadata", {})
    template_version = self.version_manager.parse_version(...)
except Exception as e:
    self.logger.warning(f"Error reading template for '{agent_name}': {e}")
    continue
```

**Fixed**:
```python
# Read template version (handle both JSON and Markdown formats)
try:
    template_content = template_path.read_text()

    # Check if this is a Markdown file with YAML frontmatter
    if template_path.suffix == ".md" and template_content.strip().startswith("---"):
        # Parse YAML frontmatter
        from .agent_version_manager import AgentVersionManager
        version_manager = AgentVersionManager()
        template_version, _, _ = version_manager.extract_version_from_frontmatter(
            template_content
        )
    else:
        # Parse JSON format
        template_data = json.loads(template_content)
        metadata = template_data.get("metadata", {})
        template_version = self.version_manager.parse_version(
            template_data.get("agent_version")
            or template_data.get("version")
            or metadata.get("version", "0.0.0")
        )
except json.JSONDecodeError as e:
    self.logger.warning(
        f"Error parsing JSON template for '{agent_name}': {e}"
    )
    continue
except Exception as e:
    self.logger.warning(
        f"Error reading template for '{agent_name}': {e}"
    )
    continue
```

**Alternative**: Extract this logic into a helper method:

```python
def _read_template_version(self, template_path: Path) -> Tuple[int, int, int]:
    """Read version from either JSON or Markdown template format.

    Args:
        template_path: Path to template file

    Returns:
        Version tuple (major, minor, patch)

    Raises:
        ValueError: If version cannot be extracted
    """
    content = template_path.read_text()

    if template_path.suffix == ".md" and content.strip().startswith("---"):
        # Markdown with YAML frontmatter
        version_tuple, _, _ = self.version_manager.extract_version_from_frontmatter(content)
        return version_tuple
    else:
        # JSON format
        template_data = json.loads(content)
        metadata = template_data.get("metadata", {})
        version_str = (
            template_data.get("agent_version")
            or template_data.get("version")
            or metadata.get("version", "0.0.0")
        )
        return self.version_manager.parse_version(version_str)
```

Then use it:

```python
# Read template version
try:
    template_version = self._read_template_version(template_path)
except Exception as e:
    self.logger.warning(f"Error reading template for '{agent_name}': {e}")
    continue
```

## Testing Strategy

### Test Case 1: PM Instructions Not Scanned

**Objective**: Verify PM instruction templates are not treated as agent definitions

**Steps**:
1. Run `claude-mpm agents deploy`
2. Check logs for warnings about PM instruction files
3. Expected: No warnings about `circuit-breakers.md`, `pm-red-flags.md`, etc.

**Validation**:
```bash
grep -i "No valid YAML frontmatter" logs/deployment.log
# Should return 0 results for PM instruction templates
```

### Test Case 2: Remote Agent Version Comparison

**Objective**: Verify version comparison works for Markdown remote agents

**Steps**:
1. Deploy remote agents
2. Update a remote agent version
3. Run `claude-mpm agents deploy` again
4. Expected: Version upgrade detected and logged

**Validation**:
```bash
grep -i "Error reading template" logs/deployment.log
# Should return 0 results
```

### Test Case 3: Mixed Format Support

**Objective**: Verify both JSON and Markdown templates are handled

**Setup**:
- Keep one JSON template in system templates (if any remain)
- Keep remote Markdown agents

**Steps**:
1. Run deployment
2. Check both formats are processed correctly

**Expected**:
- No JSON parse errors
- No YAML frontmatter warnings
- Version comparison works for both formats

## Migration Path

### Phase 1: Immediate Fixes (Non-Breaking)

1. **Suppress PM Instruction Warnings**
   - Modify `_extract_agent_metadata()` to return `None` silently for files without frontmatter
   - Remove warning log for missing frontmatter in PM instruction files

2. **Add Markdown Support to Version Comparison**
   - Implement `_read_template_version()` helper method
   - Update `compare_deployed_versions()` to use it

### Phase 2: Architectural Cleanup (Breaking)

1. **Separate PM Instructions from Agent Templates**
   - Move PM instructions to `src/claude_mpm/agents/pm_instructions/`
   - Create `src/claude_mpm/agents/json_templates/` for any remaining JSON templates
   - Update `paths.py` configuration

2. **Deprecate JSON Agent Format**
   - Add deprecation warnings for JSON templates
   - Migrate all remaining JSON agents to Markdown format
   - Remove JSON support in v5.0.0

### Phase 3: Unified Agent Format (Future)

1. **Single Source of Truth**
   - All agents use Markdown with YAML frontmatter
   - Remove JSON parsing code paths
   - Simplify deployment service

## Files Requiring Modification

### Priority 1 (Immediate Fixes)

1. **src/claude_mpm/services/agents/deployment/agent_discovery_service.py**
   - Line 218-221: Suppress warning for missing frontmatter
   - Make `_extract_agent_metadata()` return `None` silently

2. **src/claude_mpm/services/agents/deployment/multi_source_deployment_service.py**
   - Line 830-841: Add Markdown template support
   - Add `_read_template_version()` helper method

### Priority 2 (Architectural Cleanup)

3. **src/claude_mpm/services/agents/deployment/agent_deployment.py**
   - Line 157-164: Update templates_dir to point to JSON-only directory
   - Separate PM instructions from agent templates

4. **src/claude_mpm/config/paths.py**
   - Add new path configurations for separated directories

### Priority 3 (Testing)

5. **tests/unit/services/agents/deployment/test_agent_discovery_service.py**
   - Add test for PM instruction files (should be skipped)
   - Add test for files without YAML frontmatter

6. **tests/unit/services/agents/deployment/test_multi_source_deployment_service.py**
   - Add test for Markdown template version reading
   - Add test for mixed JSON/Markdown templates

## Related Tickets

- None currently exist
- Recommend creating:
  - **TICKET-001**: Fix YAML frontmatter warnings for PM instruction templates
  - **TICKET-002**: Add Markdown template support to version comparison
  - **TICKET-003**: Separate PM instructions from agent templates directory

## Conclusion

Both issues stem from architectural confusion between three different directory purposes and two different agent formats. The immediate fixes are straightforward and non-breaking. The longer-term solution involves clear separation of concerns and migration to a single agent format (Markdown with YAML frontmatter).

**Immediate Action Items**:
1. Suppress false-positive warnings for PM instruction templates
2. Add Markdown template support to version comparison logic
3. Document directory purposes clearly
4. Plan architectural cleanup for v5.0.0

**Estimated Effort**:
- Priority 1 fixes: 2-4 hours
- Priority 2 cleanup: 4-8 hours
- Priority 3 testing: 2-4 hours
- **Total**: 8-16 hours
