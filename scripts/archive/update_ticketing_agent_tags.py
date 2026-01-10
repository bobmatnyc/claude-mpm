#!/usr/bin/env python3
"""
Update ticketing agent instructions to preserve PM-specified tags.

This script:
1. Adds TAG PRESERVATION PROTOCOL section at the top
2. Updates Scope-Aware Tagging System to show tag merging
3. Updates all code examples to extract and merge PM tags
4. Adds validation function for tag handling
"""

import json
import re
from pathlib import Path

# Tag preservation protocol to insert
TAG_PRESERVATION_PROTOCOL = r"""## 🏷️ TAG PRESERVATION PROTOCOL (MANDATORY)

**CRITICAL**: PM-specified tags have ABSOLUTE PRIORITY and must NEVER be replaced or overridden.

### Tag Handling Rules:

1. **ALWAYS check for PM-provided tags first**:
   ```python
   pm_tags = delegation_context.get('tags', [])
   ```

2. **MERGE tags, NEVER replace**:
   ```python
   # ✅ CORRECT: Merge PM tags with scope tags
   final_tags = pm_tags + scope_tags

   # ❌ WRONG: Replace PM tags
   tags = ["hardcoded", "scope-tags"]  # VIOLATION
   ```

3. **Disable auto-detection when PM provides tags**:
   ```python
   auto_detect_labels = False if pm_tags else True
   ```

4. **Tag Priority Matrix**:
   - **Highest Priority**: PM-specified tags (ALWAYS preserve)
   - **Medium Priority**: Scope tags (merge with PM tags)
   - **Lowest Priority**: Auto-detected tags (ONLY if PM provides none)

### Enforcement:

❌ **VIOLATIONS** (immediate failure):
- Replacing PM tags with hardcoded tags
- Enabling auto_detect_labels when PM provides tags
- Ignoring PM-specified tags
- Overriding PM tags with scope tags

✅ **CORRECT PATTERN**:
```python
pm_tags = delegation.get('tags', [])
scope_tags = ["in-scope", "subtask"] if is_in_scope else []
final_tags = pm_tags + scope_tags  # Merge, don't replace
auto_detect = False if pm_tags else True
```

### Pre-Creation Validation Function:

Before creating ANY ticket, validate tag handling:

```python
def validate_tags(pm_tags, final_tags, auto_detect):
    \"\"\"Ensure PM tags are preserved correctly\"\"\"

    # Check 1: All PM tags must be in final tags
    for tag in pm_tags:
        assert tag in final_tags, f"PM tag '{tag}' was dropped!"

    # Check 2: Auto-detection must be disabled if PM provided tags
    if pm_tags:
        assert auto_detect == False, "Auto-detection enabled with PM tags!"

    # Check 3: Final tags must not be empty if PM provided tags
    if pm_tags:
        assert len(final_tags) > 0, "Final tags empty despite PM tags!"

    return True
```

"""

# Updated Scope-Aware Tagging System
UPDATED_SCOPE_TAGGING = r"""### Scope-Aware Tagging System

**CRITICAL**: These scope tags MERGE with PM tags, they do NOT replace them.

**For subtasks (in-scope)**:
```python
# MANDATORY: Preserve PM tags first
pm_tags = delegation.get("tags", [])

# Add scope tags (merge, don't replace)
scope_tags = ["in-scope", "required-for-parent", "subtask"]
final_tags = pm_tags + scope_tags

# Disable auto-detection if PM provided tags
auto_detect_labels = False if pm_tags else True

# Create subtask with merged tags
subtask_id = mcp__mcp-ticketer__task_create(
    title=item.title,
    description=item.description,
    issue_id=parent_ticket_id,
    priority=item.priority,
    tags=final_tags,  # ← Merged tags
    auto_detect_labels=auto_detect_labels
)
```
- Parent link: Set via `issue_id` parameter
- Relationship: Child of parent ticket

**For related tickets (scope-adjacent)**:
```python
pm_tags = delegation.get("tags", [])
scope_tags = ["scope:adjacent", f"related-to-{PARENT_ID}", "enhancement"]
final_tags = pm_tags + scope_tags

# Create ticket with merged tags
ticket_id = mcp__mcp-ticketer__issue_create(
    title=item.title,
    tags=final_tags,
    auto_detect_labels=False if pm_tags else True
)
```
- Parent link: None (sibling relationship)
- Comment: Reference to parent ticket in description

**For separate tickets (out-of-scope)**:
```python
pm_tags = delegation.get("tags", [])
scope_tags = ["scope:separate", "discovered-during-work"]
final_tags = pm_tags + scope_tags

# Create separate ticket with merged tags
separate_ticket_id = mcp__mcp-ticketer__issue_create(
    title=item.title,
    tags=final_tags,
    auto_detect_labels=False if pm_tags else True
)
```
- Parent link: None (separate initiative)
- Comment: Discovery context added to parent ticket"""


def update_ticketing_agent():
    """Update ticketing agent template with tag preservation protocol."""

    template_path = (
        Path(__file__).parent.parent / "src/claude_mpm/agents/templates/ticketing.json"
    )

    print(f"Reading template from: {template_path}")
    with open(template_path) as f:
        template = json.load(f)

    instructions = template["instructions"]

    # Step 1: Add TAG PRESERVATION PROTOCOL after main header
    if "TAG PRESERVATION PROTOCOL" not in instructions:
        print("✓ Adding TAG PRESERVATION PROTOCOL section...")
        instructions = instructions.replace(
            "## 🛡️ SCOPE PROTECTION ENFORCEMENT (MANDATORY)",
            TAG_PRESERVATION_PROTOCOL
            + "\n## 🛡️ SCOPE PROTECTION ENFORCEMENT (MANDATORY)",
        )
    else:
        print("⚠ TAG PRESERVATION PROTOCOL already exists, skipping...")

    # Step 2: Update Scope-Aware Tagging System section
    print("✓ Updating Scope-Aware Tagging System...")
    # Find and replace the old scope-aware tagging section
    old_scope_pattern = r"### Scope-Aware Tagging System\s+\*\*REQUIRED:.*?(?=###|\Z)"
    instructions = re.sub(
        old_scope_pattern, UPDATED_SCOPE_TAGGING + "\n\n", instructions, flags=re.DOTALL
    )

    # Step 3: Update hardcoded tag examples in IN-SCOPE code
    print("✓ Updating IN-SCOPE tag examples...")
    # Find patterns like tags=["in-scope", "required-for-parent"] without pm_tags
    instructions = re.sub(
        r'tags=\["in-scope", "required-for-parent"\]',
        'tags=pm_tags + ["in-scope", "required-for-parent"]  # Merge PM tags',
        instructions,
    )

    # Step 4: Update ticket creation examples to include auto_detect_labels parameter
    print("✓ Adding auto_detect_labels parameter to examples...")
    # Add auto_detect_labels to mcp__mcp-ticketer__task_create calls that don't have it
    task_create_pattern = (
        r'(mcp__mcp-ticketer__task_create\([^)]*priority="[^"]*")\s*\)'
    )
    instructions = re.sub(
        task_create_pattern,
        r"\1,\n    auto_detect_labels=False if pm_tags else True\n)",
        instructions,
    )

    # Step 5: Update version
    template["agent_version"] = "2.7.0"
    template["metadata"]["updated_at"] = "2025-11-29T00:00:00.000000Z"

    # Save updated template
    template["instructions"] = instructions

    print(f"✓ Writing updated template to: {template_path}")
    with open(template_path, "w") as f:
        json.dump(template, f, indent=2, ensure_ascii=False)

    print("\n✅ Tag preservation protocol successfully added!")
    print(f"   Version updated: {template['agent_version']}")
    print(f"   File: {template_path}")
    print("\nNext steps:")
    print(
        "  1. Review changes: git diff src/claude_mpm/agents/templates/ticketing.json"
    )
    print("  2. Test changes: make quality")
    print("  3. Redeploy agent: claude-mpm agents deploy ticketing --force")


if __name__ == "__main__":
    update_ticketing_agent()
