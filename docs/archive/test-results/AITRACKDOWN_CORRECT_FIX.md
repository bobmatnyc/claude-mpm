# AI Trackdown v1.3.x Compatibility Fix for claude-mpm (Corrected)

## Issue Summary

The claude-mpm project correctly follows the ai-trackdown schema structure but uses `tickets/` as the root directory instead of `tasks/`:

```
tickets/          # claude-mpm uses 'tickets' instead of 'tasks'
├── epics/        # 3 epic files (EP-XXXX)
├── issues/       # 11 issue files (ISS-XXXX)  
├── tasks/        # 40 task files (TSK-XXXX)
└── (no prs/ or comments/ yet)
```

However, ai-trackdown v1.3.0's TaskManager is only scanning `tickets/tasks/` subdirectory, missing the `epics/` and `issues/` subdirectories.

## Root Cause

The TaskManager in ai-trackdown v1.3.x has a bug where it doesn't properly scan all subdirectories as specified in the schema. It's only looking for files in the configured tasks directory and the `tasks/` subdirectory within it.

## Correct Solution

Since the directory structure matches the schema (just using `tickets/` instead of `tasks/`), the proper fix is to configure ai-trackdown to scan all subdirectories:

### Option 1: Configure ai-trackdown properly
Update `.aitrackdown-config.yaml`:
```yaml
# AI Trackdown configuration
tasks:
  directory: tickets  # Use tickets as the root
  # The tool should scan tickets/epics/, tickets/issues/, tickets/tasks/, etc.
```

### Option 2: Create symlink (Current Workaround)
Since ai-trackdown v1.3.0 has a bug, use a symlink:
```bash
# Remove the incorrect symlink
rm tasks

# The tickets directory structure is correct - no changes needed
```

### Option 3: Wait for ai-trackdown fix
The issue is a bug in ai-trackdown v1.3.x where it doesn't properly implement the schema's directory structure. This should be fixed in a future version.

## Verification

The ticket files themselves are correctly formatted:
- All issues have `tags: ['issue', ...]` 
- All epics have `tags: ['epic']`
- The frontmatter follows the schema
- The file naming follows the pattern: `{ID}.md` or `{ID}-{title}.md`

## Temporary Workaround

Until ai-trackdown is fixed, you can access tickets directly:
```bash
# List all issues
ls tickets/issues/ISS-*.md

# Count tickets by type
echo "Epics: $(ls tickets/epics/EP-*.md 2>/dev/null | wc -l)"
echo "Issues: $(ls tickets/issues/ISS-*.md 2>/dev/null | wc -l)"
echo "Tasks: $(ls tickets/tasks/TSK-*.md 2>/dev/null | wc -l)"

# Search for issues in an epic
grep -l "epic: EP-0003" tickets/issues/*.md

# View an issue
cat tickets/issues/ISS-0001.md
```

## Conclusion

The claude-mpm project structure is **correct** according to the ai-trackdown schema. The issue is a bug in ai-trackdown v1.3.x where it doesn't properly scan the subdirectory structure defined in the schema. No migration or restructuring is needed - the tool needs to be fixed to properly implement its own schema.