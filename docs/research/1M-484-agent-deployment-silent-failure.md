# Agent Deployment Silent Failure Investigation (1M-484)

**Date**: 2025-12-01
**Researcher**: Research Agent
**Ticket**: 1M-484 - Agent deployment shows success but writes 0 files
**Status**: Root cause identified

## Executive Summary

Agent deployment shows "86/86 (100%)" success but writes **0 files** to `~/.claude/agents/`. Root cause: **Type mismatch between remote agent format (Markdown) and deployment expectations (JSON templates)**.

**Critical Finding**: The deployment process attempts to parse Markdown files with YAML frontmatter as JSON, causing silent JSON parsing failures that prevent file writes.

## Problem Description

### Observed Behavior

1. **Progress bar**: Shows "86/86 (100%)" correctly
2. **Agent discovery**: Finds 86 `.md` files in `~/.claude-mpm/cache/remote-agents/`
3. **Deployment target**: `~/.claude/agents/` is EMPTY (0 files)
4. **Deployment service**: Reports success but files aren't written

### User Impact

- Agents appear to deploy successfully but are not available
- No error messages visible to user
- System appears functional but agent delegation fails

## Root Cause Analysis

### Deployment Flow Trace

```
1. startup.py:324 → deployment_service.deploy_agents()
   ├── force_rebuild=False
   └── deployment_mode="update"

2. agent_deployment.py:888-899 → multi_source_service.get_agents_for_deployment()
   ├── Discovers agents from 4 tiers (system, user, remote, project)
   ├── Remote tier: ~/.claude-mpm/cache/remote-agents/ (86 .md files)
   └── Returns: agents_to_deploy dict with .md file paths

3. agent_deployment.py:902-907 → multi_source_service.compare_deployed_versions()
   ├── agents_dir.exists() = TRUE (empty directory exists)
   ├── Compares template versions with deployed versions
   └── Returns: all 86 as "new_agents" (deployed dir empty)

4. agent_deployment.py:910-948 → Filter agents based on comparison
   ├── force_rebuild=False
   ├── agents_needing_update = set of 86 agent names
   └── filtered_agents = 86 .md file paths

5. agent_deployment.py:472-502 → Loop through template_files
   └── Calls: single_agent_deployer.deploy_single_agent()

6. single_agent_deployer.py:91-93 → Build agent content
   └── template_builder.build_agent_markdown(template_file, ...)

7. agent_template_builder.py:256-258 → Parse template
   ├── template_content = template_path.read_text()  # Reads Markdown
   └── template_data = json.loads(template_content)  # ❌ FAILS!
```

### The Critical Failure Point

**File**: `agent_template_builder.py`
**Lines**: 256-258
**Issue**: Attempts to parse Markdown as JSON

```python
template_content = template_path.read_text()
template_data = json.loads(template_content)  # JSONDecodeError!
```

**What it receives**:
```markdown
---
name: agent_manager
description: System agent for comprehensive agent lifecycle management
version: 2.0.2
model: sonnet
---

# Agent Manager

This agent manages the agent lifecycle...
```

**What it expects**: JSON template format
```json
{
  "agent_id": "agent-manager",
  "metadata": {
    "name": "Agent Manager",
    "version": "2.0.2"
  },
  "instructions": "..."
}
```

### Why Silent Failure?

Looking at `single_agent_deployer.py` lines 112-120:

```python
except AgentDeploymentError as e:
    # Re-raise our custom exceptions
    self.logger.error(str(e))
    results["errors"].append(str(e))
except Exception as e:
    # Wrap generic exceptions with context
    error_msg = f"Failed to build {template_file.name}: {e}"
    self.logger.error(error_msg)
    results["errors"].append(error_msg)
```

**Why errors aren't visible**:
1. `JSONDecodeError` is caught by generic `Exception` handler
2. Error is logged and appended to `results["errors"]`
3. Loop continues to next agent
4. **Progress bar continues incrementing** (already at 86/86)
5. Final summary shows "0 deployed, 0 updated, 0 skipped, 86 errors"
6. **But user only sees "Complete: 86/86"**

## Technical Details

### Remote Agent Discovery (Working Correctly)

`remote_agent_discovery_service.py:203-221` correctly returns agent dictionaries:

```python
return {
    "agent_id": agent_id,
    "metadata": {...},
    "path": str(md_file),  # Points to .md file ✓
    "file_path": str(md_file),
    "version": version,
    "source": "remote"
}
```

### Deployment Expectation Mismatch

`agent_template_builder.py:256-260` expects JSON templates:

```python
try:
    template_content = template_path.read_text()
    template_data = json.loads(template_content)  # Expects JSON!
except json.JSONDecodeError as e:
    self.logger.error(f"Invalid JSON in template {template_path}: {e}")
    raise
```

### File Format Analysis

**Remote agent file structure** (`~/.claude-mpm/cache/remote-agents/*.md`):
- Format: Markdown with YAML frontmatter
- Count: 86 files
- Source: GitHub repository sync
- Valid: Yes (correct format for remote agents)

**Expected template structure** (system templates `*.json`):
- Format: Pure JSON
- Location: `src/claude_mpm/agents/templates/`
- Structure: `{"agent_id": "...", "metadata": {...}, "instructions": "..."}`

## Solution Requirements

### Option 1: Convert Markdown to JSON (RECOMMENDED)

**Where**: Before deployment loop
**Action**: Add conversion step in `get_agents_for_deployment()`

```python
# After line 395 in multi_source_deployment_service.py
if agent_info["source"] == "remote":
    # Convert Markdown to JSON template format
    template_path = self._convert_markdown_to_json_template(template_path)
```

**Trade-offs**:
- ✅ Minimal changes to existing deployment flow
- ✅ Preserves existing error handling
- ✅ Works with current template builder
- ❌ Requires temporary file creation
- ❌ Adds conversion overhead

### Option 2: Detect Format and Handle Both

**Where**: In `build_agent_markdown()`
**Action**: Detect file type and parse accordingly

```python
# In agent_template_builder.py:252-260
if template_path.suffix == ".md":
    # Parse Markdown with YAML frontmatter
    template_data = self._parse_markdown_template(template_path)
else:
    # Parse JSON template
    template_data = json.loads(template_content)
```

**Trade-offs**:
- ✅ Handles both formats natively
- ✅ No temporary files needed
- ✅ More flexible architecture
- ❌ More complex parsing logic
- ❌ Requires YAML parser dependency

### Option 3: Pre-convert Remote Agents During Sync

**Where**: In remote agent sync process
**Action**: Convert at sync time, not deployment time

**Trade-offs**:
- ✅ Deployment flow unchanged
- ✅ One-time conversion cost
- ✅ Simpler deployment logic
- ❌ Requires changes to sync service
- ❌ Increases sync complexity

## Recommended Solution

**Option 2: Detect Format and Handle Both**

**Rationale**:
1. **Architectural correctness**: Remote agents ARE Markdown format
2. **Future-proof**: Supports mixed template formats
3. **Performance**: No temporary file overhead
4. **Maintainability**: Centralized format handling

**Implementation Plan**:

1. Add YAML frontmatter parser to `agent_template_builder.py`:
   ```python
   def _parse_markdown_template(self, md_file: Path) -> dict:
       """Parse Markdown with YAML frontmatter to template dict"""
       content = md_file.read_text()
       # Extract YAML frontmatter
       # Return dict matching JSON template structure
   ```

2. Modify `build_agent_markdown()` to detect format:
   ```python
   if template_path.suffix == ".md":
       template_data = self._parse_markdown_template(template_path)
   else:
       template_data = json.loads(template_content)
   ```

3. Update error messages to distinguish formats

## Error Logging Improvements

**Current Issue**: Errors swallowed by progress bar display

**Recommended Fix**:
```python
# In startup.py:334-343
if errors := deployment_result.get("errors"):
    deploy_progress.finish(f"Failed: {len(errors)} errors")
    console.print("\n[red]Deployment Errors:[/red]")
    for error in errors[:5]:  # Show first 5
        console.print(f"  - {error}")
    if len(errors) > 5:
        console.print(f"  ... and {len(errors) - 5} more")
else:
    deploy_progress.finish(f"Complete: {deployed} deployed, ...")
```

## Testing Requirements

1. **Unit Tests**:
   - Test Markdown format detection
   - Test YAML frontmatter parsing
   - Test JSON template parsing (existing)
   - Test error handling for both formats

2. **Integration Tests**:
   - Deploy from remote agents cache
   - Deploy from JSON templates
   - Deploy mixed formats
   - Verify file writes to disk

3. **Regression Tests**:
   - Existing agent deployment scenarios
   - Version comparison logic
   - Multi-source deployment

## Files Requiring Changes

### Primary Changes

1. **`src/claude_mpm/services/agents/deployment/agent_template_builder.py`**
   - Add `_parse_markdown_template()` method
   - Modify `build_agent_markdown()` to detect format
   - Lines: 229-260 (detection logic)

2. **`src/claude_mpm/cli/startup.py`**
   - Improve error display in deployment results
   - Lines: 334-343 (progress bar completion)

### Supporting Changes

3. **`src/claude_mpm/services/agents/deployment/single_agent_deployer.py`**
   - Enhance error logging
   - Lines: 112-120 (exception handling)

4. **Add tests**:
   - `tests/services/agents/deployment/test_markdown_template_parsing.py`
   - Update `tests/services/agents/deployment/test_agent_template_builder.py`

## Related Issues

- **1M-442**: Agent git sources deployment integration (introduced remote agents)
- **1M-480**: Path field compatibility (attempted to fix path structure)
- **Format assumption**: System assumed all templates are JSON

## Next Steps

1. ✅ **COMPLETED**: Root cause analysis documented
2. **TODO**: Implement Markdown template parser
3. **TODO**: Add format detection logic
4. **TODO**: Enhance error reporting
5. **TODO**: Add comprehensive tests
6. **TODO**: Update documentation

## Appendix

### Sample Remote Agent Format

```markdown
---
name: agent_manager
description: System agent for comprehensive agent lifecycle management
version: 2.0.2
schema_version: 1.3.0
agent_id: agent-manager
model: sonnet
tags:
- system
- management
category: system
author: Claude MPM Team
---

# Agent Manager

This agent manages the agent lifecycle including:
- Deployment orchestration
- Version control
- PM instruction configuration
```

### Expected JSON Template Format

```json
{
  "agent_id": "agent-manager",
  "metadata": {
    "name": "Agent Manager",
    "description": "System agent for comprehensive agent lifecycle management",
    "version": "2.0.2",
    "author": "Claude MPM Team",
    "category": "system",
    "tags": ["system", "management"]
  },
  "model": "sonnet",
  "instructions": "This agent manages the agent lifecycle..."
}
```

### Directory Structure

```
~/.claude-mpm/cache/remote-agents/
├── agent-manager.md (86 total)
├── agentic-coder-optimizer.md
└── ...

~/.claude/agents/
└── (EMPTY - deployment failed)

src/claude_mpm/agents/templates/
├── agent-manager.json (system templates)
├── research.json
└── ...
```

## Memory Updates

```json
{
  "remember": [
    "Agent deployment fails silently when remote Markdown agents are parsed as JSON templates",
    "Remote agents in ~/.claude-mpm/cache/remote-agents/ are Markdown with YAML frontmatter, not JSON",
    "agent_template_builder.py:256-258 assumes all templates are JSON format",
    "Solution: Add Markdown format detection and YAML frontmatter parser to build_agent_markdown()",
    "86 agents discovered but 0 deployed due to JSONDecodeError on every file"
  ]
}
```
