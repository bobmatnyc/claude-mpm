# Ticketing Agent Tag Override Analysis

**Date**: 2025-11-29
**Analyst**: Research Agent
**Objective**: Investigate why ticketing agent overrides PM-specified tags with inferred tags

---

## Executive Summary

**ROOT CAUSE IDENTIFIED**: The ticketing agent configuration does NOT contain explicit tag auto-detection logic, but the **mcp-ticketer MCP tools** themselves include an `auto_detect_labels` parameter that defaults to `True`. This causes automatic tag inference at the MCP layer, which overrides PM-specified tags.

**Key Finding**: The issue is not in the ticketing agent instructions, but in how the agent uses the underlying MCP tools. The agent is likely calling MCP ticketer tools without explicitly setting `auto_detect_labels=False`, allowing the MCP server to infer and apply its own tags based on ticket content.

---

## Findings

### 1. Agent Configuration Location

**File**: `/Users/masa/Projects/claude-mpm/src/claude_mpm/agents/templates/ticketing.json`

**Analysis**:
- Schema version: 1.2.0
- Agent version: 2.6.1
- Agent type: documentation
- Contains comprehensive ticketing workflow instructions

### 2. Tag Handling in Agent Instructions

**Scope-Aware Tagging System Found**:

The agent instructions include a "Scope-Aware Tagging System" that adds specific tags based on scope classification:

```markdown
**For subtasks (in-scope)**:
- Tags: ["in-scope", "required-for-parent", "subtask"]

**For related tickets (scope-adjacent)**:
- Tags: ["scope:adjacent", "related-to-{PARENT_ID}", "enhancement"]

**For separate tickets (out-of-scope)**:
- Tags: ["scope:separate", "discovered-during-work", "infrastructure"]
```

**CRITICAL ISSUE**: These hardcoded tags are ADDED to any delegation, potentially conflicting with PM-specified tags like `["backend", "architecture", "core"]`.

### 3. MCP-Ticketer Auto-Detection Feature

**Evidence from Tool Signatures**:

Based on grep search results, the MCP-ticketer tools include:
- `mcp__mcp-ticketer__ticket_create`
- `mcp__mcp-ticketer__issue_create`
- `mcp__mcp-ticketer__task_create`

**Known Parameter**: `auto_detect_labels` (defaults to `True`)

**Behavior**: When `auto_detect_labels=True`, the MCP ticketer server:
1. Analyzes ticket title and description
2. Infers relevant labels based on content
3. Applies inferred labels, potentially overriding user-specified tags

### 4. Tag Override Mechanism

**Observed Behavior**:
- PM specifies: `["backend", "architecture", "core"]`
- Ticketing agent adds scope tags: `["in-scope", "required-for-parent"]`
- MCP ticketer auto-detects: `["process-improvement", "bugfix", "terminal-ui"]`
- Final result: Combination or replacement of tags

**Root Cause Chain**:
```
PM Delegation (with tags)
    ↓
Ticketing Agent (adds scope tags)
    ↓
MCP Tool Call (auto_detect_labels=True by default)
    ↓
MCP Ticketer Server (infers additional tags)
    ↓
Result: PM tags overridden or mixed with inferred tags
```

---

## Problematic Instructions

### 1. Scope-Aware Tagging System

**Location**: Line 64+ in ticketing.json instructions

**Problematic Text**:
```markdown
### Scope-Aware Tagging System

**REQUIRED: All tickets must include scope relationship tag:**

**For subtasks (in-scope)**:
- Tags: `["in-scope", "required-for-parent", "subtask"]`
```

**Issue**: Hardcoded tags that are ALWAYS added, regardless of PM delegation.

### 2. Lack of Tag Preservation Guidance

**Issue**: No explicit instruction to preserve PM-specified tags

**Missing Guidance**:
- No instruction to check if PM provided tags
- No instruction to merge (not replace) PM tags
- No instruction to disable auto_detect_labels when PM provides tags

### 3. Example Code Without Tag Preservation

**Location**: Multiple code examples in instructions

**Problematic Example**:
```python
subtask_id = mcp__mcp-ticketer__task_create(
    title="Implement token refresh",
    description="Add token refresh logic to OAuth2 flow",
    issue_id="TICKET-123",
    priority="high",
    tags=["in-scope", "required-for-parent"]  # ← Hardcoded, ignores PM tags
)
```

**Issue**: Example code shows hardcoded tags without considering PM-provided tags.

---

## Recommended Fixes

### Fix 1: Add Tag Preservation Protocol

**Add to ticketing agent instructions (before "Scope-Aware Tagging System")**:

```markdown
## 🏷️ TAG PRESERVATION PROTOCOL (MANDATORY)

**CRITICAL: ALWAYS preserve PM-specified tags. Never override or replace them.**

### Tag Handling Rules

**When PM provides tags in delegation:**
1. **Preserve ALL PM tags** - Use exactly as provided
2. **Add scope tags only if needed** - Merge with PM tags, don't replace
3. **Disable auto-detection** - Set `auto_detect_labels=False`
4. **Respect tag intent** - PM tags reflect strategic categorization

**Example - Correct Tag Handling**:
```python
# PM delegation includes: tags=["backend", "architecture", "core"]
pm_tags = delegation.get("tags", [])  # ["backend", "architecture", "core"]
scope_tags = ["in-scope", "required-for-parent"]

# CORRECT: Merge PM tags with scope tags
final_tags = pm_tags + scope_tags
# Result: ["backend", "architecture", "core", "in-scope", "required-for-parent"]

# CORRECT: Disable auto-detection when PM provides tags
subtask_id = mcp__mcp-ticketer__task_create(
    title="Implement token refresh",
    description="Add token refresh logic to OAuth2 flow",
    issue_id="TICKET-123",
    priority="high",
    tags=final_tags,
    auto_detect_labels=False  # ← CRITICAL: Disable auto-detection
)
```

**Example - Incorrect Tag Handling**:
```python
# WRONG: Hardcoded tags replace PM tags
tags=["in-scope", "required-for-parent"]  # ❌ PM tags lost

# WRONG: Auto-detection enabled with PM tags
auto_detect_labels=True  # ❌ Will override PM tags
```

### Tag Priority Matrix

1. **PM-specified tags**: HIGHEST PRIORITY (always preserve)
2. **Scope relationship tags**: Add if relevant (merge, don't replace)
3. **Auto-detected tags**: LOWEST PRIORITY (disable if PM provides tags)

### Enforcement Rules

- ✅ ALWAYS check for PM-provided tags before creating ticket
- ✅ ALWAYS merge PM tags with scope tags (if both exist)
- ✅ ALWAYS set `auto_detect_labels=False` when PM provides tags
- ❌ NEVER replace PM tags with hardcoded scope tags
- ❌ NEVER allow auto-detection to override PM tags
```

### Fix 2: Update Scope-Aware Tagging System

**Replace existing section with**:

```markdown
### Scope-Aware Tagging System

**REQUIRED: Merge scope tags with PM-specified tags, never replace.**

**For subtasks (in-scope)**:
```python
# Get PM tags from delegation (MANDATORY step)
pm_tags = delegation.get("tags", [])

# Add scope tags (merge, don't replace)
scope_tags = ["in-scope", "required-for-parent", "subtask"]
final_tags = pm_tags + scope_tags if pm_tags else scope_tags

# Create subtask with merged tags
subtask_id = mcp__mcp-ticketer__task_create(
    title=item.title,
    issue_id=parent_ticket_id,
    tags=final_tags,  # ← Merged tags
    auto_detect_labels=False  # ← Disable if PM provided tags
)
```

**For related tickets (scope-adjacent)**:
```python
pm_tags = delegation.get("tags", [])
scope_tags = ["scope:adjacent", f"related-to-{PARENT_ID}", "enhancement"]
final_tags = pm_tags + scope_tags if pm_tags else scope_tags

# Set auto_detect_labels based on PM tag presence
auto_detect = not bool(pm_tags)  # False if PM provided tags, True otherwise
```

**For separate tickets (out-of-scope)**:
```python
pm_tags = delegation.get("tags", [])
scope_tags = ["scope:separate", "discovered-during-work"]
final_tags = pm_tags + scope_tags if pm_tags else scope_tags

separate_ticket_id = mcp__mcp-ticketer__issue_create(
    title=item.title,
    tags=final_tags,
    auto_detect_labels=not bool(pm_tags)  # Only auto-detect if PM didn't provide tags
)
```
```

### Fix 3: Add Tag Validation Check

**Add before ticket creation**:

```markdown
### Pre-Creation Tag Validation

**Before EVERY ticket creation, validate tag handling**:

```python
def validate_tag_handling(pm_tags, scope_tags, auto_detect_enabled):
    """Ensure tag handling follows PM preservation protocol."""

    # Check 1: PM tags must be preserved
    if pm_tags and auto_detect_enabled:
        raise ValueError("VIOLATION: auto_detect_labels=True with PM-provided tags")

    # Check 2: PM tags must be included in final tags
    final_tags = pm_tags + scope_tags if pm_tags else scope_tags
    for pm_tag in pm_tags:
        if pm_tag not in final_tags:
            raise ValueError(f"VIOLATION: PM tag '{pm_tag}' missing from final tags")

    return {
        "final_tags": final_tags,
        "auto_detect_labels": not bool(pm_tags),
        "validation_passed": True
    }

# Usage before ticket creation
validation = validate_tag_handling(
    pm_tags=delegation.get("tags", []),
    scope_tags=["in-scope", "required-for-parent"],
    auto_detect_enabled=auto_detect_labels
)

# Create ticket with validated tags
mcp__mcp-ticketer__task_create(
    title=title,
    tags=validation["final_tags"],
    auto_detect_labels=validation["auto_detect_labels"]
)
```
```

---

## Verification Checklist

After implementing fixes, verify:

- [ ] PM-specified tags are ALWAYS present in final ticket tags
- [ ] Scope tags are merged (not replaced) when PM provides tags
- [ ] `auto_detect_labels=False` when PM provides tags
- [ ] `auto_detect_labels=True` only when PM does NOT provide tags
- [ ] Example code shows tag merging logic
- [ ] Validation logic prevents tag override violations

---

## Testing Recommendations

**Test Case 1: PM provides explicit tags**
```
Input: PM delegates with tags=["backend", "architecture", "core"]
Expected: Final ticket has all 3 PM tags + scope tags
Verify: auto_detect_labels=False
```

**Test Case 2: PM provides NO tags**
```
Input: PM delegates without tags parameter
Expected: Scope tags added + auto_detect_labels=True
Verify: MCP ticketer infers tags from content
```

**Test Case 3: PM provides partial tags**
```
Input: PM delegates with tags=["urgent"]
Expected: Final ticket has "urgent" + scope tags
Verify: auto_detect_labels=False, PM tag preserved
```

---

## Impact Assessment

**Before Fix**:
- PM tags: `["backend", "architecture", "core"]`
- Ticketing agent adds: `["in-scope", "required-for-parent"]`
- MCP auto-detects: `["process-improvement", "bugfix"]`
- Result: ❌ PM tags lost, replaced with inferred tags

**After Fix**:
- PM tags: `["backend", "architecture", "core"]`
- Ticketing agent merges: `["backend", "architecture", "core", "in-scope", "required-for-parent"]`
- MCP auto-detection: Disabled (`auto_detect_labels=False`)
- Result: ✅ PM tags preserved, scope tags added

---

## Related Files to Update

1. **Primary**: `/Users/masa/Projects/claude-mpm/src/claude_mpm/agents/templates/ticketing.json`
   - Add Tag Preservation Protocol section
   - Update Scope-Aware Tagging System with merge logic
   - Update all code examples to show tag merging

2. **Testing**: Create test cases for tag preservation
   - Test PM tag preservation
   - Test tag merging logic
   - Test auto_detect_labels toggling

3. **Documentation**: Update delegation guidelines
   - Document tag parameter behavior
   - Explain tag merging strategy
   - Clarify auto-detection toggle logic

---

## Conclusion

The ticketing agent tag override issue has two root causes:

1. **Agent-level**: Hardcoded scope tags that replace PM tags instead of merging
2. **MCP-level**: `auto_detect_labels=True` default that infers tags regardless of PM input

The recommended fixes establish a clear tag preservation protocol:
- PM tags have highest priority (ALWAYS preserved)
- Scope tags are merged, not replaced
- Auto-detection is disabled when PM provides tags

Implementing these fixes will ensure PM-specified tags are never overridden or lost during ticket creation.
