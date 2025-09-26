# Archive Manager Service - Enhanced Documentation Review & Archival

## Overview

The Archive Manager service provides intelligent documentation review, version tracking, and archival capabilities for Claude MPM projects. It integrates with Git history to detect outdated content, synchronize documentation files, and automatically archive obsolete documentation with detailed metadata.

## Key Features

### 1. Documentation Review with Git Integration

The service analyzes documentation files to detect outdated content using multiple strategies:

- **Git History Analysis**: Tracks when files were last modified in Git
- **Pattern Detection**: Identifies TODO items, deprecated references, and temporary solutions
- **Version Tracking**: Detects old version numbers and mismatched references
- **Synchronization Checks**: Ensures consistency between CLAUDE.md, README.md, and CHANGELOG.md

```python
from claude_mpm.services.project.archive_manager import ArchiveManager

# Initialize the manager
manager = ArchiveManager(project_path)

# Perform comprehensive documentation review
review = manager.review_documentation(check_git=True)

# Display formatted summary
manager.display_review_summary(review)
```

### 2. Intelligent Outdated Content Detection

The service automatically identifies documentation that needs updating:

#### Detection Patterns
- Unresolved TODOs, FIXMEs, and XXX markers
- Deprecated, obsolete, or legacy references
- Future tense content ("coming soon", "upcoming")
- Pre-release indicators (alpha, beta, experimental)
- Temporary workarounds and hacks
- Old version number references

#### Example Output
```
📚 Documentation Review Summary

File           Status          Issues  Last Updated
CLAUDE.md      ⚠️ Needs Review  13      11 days ago
README.md      ⚠️ Needs Review  5       6 days ago
CHANGELOG.md   ✅ OK            0       0 days ago

⚠️ Synchronization Issues:
  • Version mismatch: CLAUDE.md: 4.0.25, README.md: 4.3.3
  • Stale changelog: Last updated 45 days ago

💡 Recommendations:
  📝 Review and update 2 files with outdated content
  🔄 Synchronize version numbers across documentation files
  ✅ Resolve 18 TODO items in documentation
```

### 3. Automatic Archival with Metadata

Archive outdated documentation automatically with rich metadata:

```python
# Auto-detect and archive outdated documentation
result = manager.auto_detect_and_archive_outdated(dry_run=False)

# Archive with custom metadata
manager.archive_file(
    file_path,
    reason="Major refactoring - preserving old version",
    metadata={
        "version": "4.3.20",
        "git_commit": "abc123",
        "author": "Development Team",
        "tags": ["refactoring", "v4-migration"]
    }
)
```

#### Archive Metadata Structure
```json
{
  "original_path": "/path/to/CLAUDE.md",
  "archived_at": "2025-01-26T10:30:00",
  "reason": "Auto-archived: 15 outdated indicators, No updates for 92 days",
  "file_size": 12345,
  "file_hash": "d41d8cd98f00b204e9800998ecf8427e",
  "auto_detection": true,
  "indicators": [
    {"line": 45, "type": "Unresolved TODOs", "content": "TODO: Update this section"},
    {"line": 89, "type": "Deprecated references", "content": "deprecated API call"}
  ]
}
```

### 4. Git History Integration

Track documentation changes through Git history:

```python
# Get file Git history
history = manager.get_file_git_history(file_path, limit=10)

# Get last modification date from Git
last_modified = manager.get_file_last_modified(file_path)

# Review with Git integration
review = manager.review_documentation(check_git=True)
```

### 5. Documentation Synchronization

Automatically synchronize key information across documentation files:

```python
# Sync version numbers and changelog entries
sync_result = manager.sync_with_readme_and_changelog()

# Example sync operations:
# - Update version badges in README.md
# - Add new version section to CHANGELOG.md
# - Ensure consistent project naming
# - Align version references across files
```

### 6. Archive Management Features

#### Compression and Cleanup
- Archives older than 7 days are automatically compressed with gzip
- Archives older than 90 days are automatically deleted
- Maximum of 10 archives kept per file (configurable)

#### Restoration with Review
```python
# Restore with change preview
success, message = manager.restore_from_archive_with_review(
    "CLAUDE.md.2025-01-26T10-30-00.md",
    review_changes=True
)

# Generate diff report
diff = manager.generate_documentation_diff_report(
    current_file,
    archived_file
)
```

### 7. Comprehensive Reporting

Generate detailed reports about archived documentation:

```python
# Create archive report
report = manager.create_archive_report()

# Report includes:
# - Total archives and size
# - Compression statistics
# - Files being tracked
# - Version history per file
# - Oldest and newest archives
```

## Usage Examples

### Basic Documentation Review

```python
from pathlib import Path
from claude_mpm.services.project.archive_manager import ArchiveManager

# Initialize
project_path = Path.cwd()
manager = ArchiveManager(project_path)

# Review documentation
review = manager.review_documentation()

# Check for issues
if review["synchronization_issues"]:
    print("Documentation needs synchronization!")

if review["outdated_sections"]:
    print(f"Found {len(review['outdated_sections'])} files with outdated content")

# Get recommendations
for recommendation in review["recommendations"]:
    print(recommendation)
```

### Automated Archival Workflow

```python
# 1. Review documentation
review = manager.review_documentation()

# 2. Auto-detect outdated files (dry run first)
dry_run_result = manager.auto_detect_and_archive_outdated(dry_run=True)
print(f"Would archive: {dry_run_result['skipped_files']}")

# 3. Perform actual archival
archive_result = manager.auto_detect_and_archive_outdated(dry_run=False)
print(f"Archived: {archive_result['archived_files']}")

# 4. Sync documentation
sync_result = manager.sync_with_readme_and_changelog()
print(f"Synced: {sync_result['changes']}")
```

### Archive Restoration

```python
# List available archives
archives = manager.list_archives("CLAUDE.md", include_metadata=True)

# Get latest archive
latest = manager.get_latest_archive("CLAUDE.md")

# Compare with current
comparison = manager.compare_with_archive(
    Path("CLAUDE.md"),
    latest.name
)

# Restore if needed
if comparison["lines_added"] < -50:  # Lost significant content
    success, msg = manager.restore_archive(latest.name)
```

## Configuration

The Archive Manager can be configured through class attributes:

```python
class ArchiveManager:
    ARCHIVE_DIR = "docs/_archive"        # Archive directory location
    MAX_ARCHIVES = 10                    # Max archives per file
    COMPRESS_AFTER_DAYS = 7              # Compress after N days
    DELETE_AFTER_DAYS = 90               # Delete after N days
```

## Integration with Claude MPM

The Archive Manager integrates seamlessly with Claude MPM's initialization process:

```python
# In mpm_init.py
from claude_mpm.services.project.archive_manager import ArchiveManager

def init_claude_instructions(args):
    # ... initialization code ...

    # Archive before update if configured
    if args.archive:
        archive_manager = ArchiveManager(project_path)
        archive_manager.auto_archive_before_update(
            claude_path,
            update_reason="MPM initialization"
        )

    # Perform update
    update_claude_instructions(...)

    # Sync documentation
    if args.sync_docs:
        archive_manager.sync_with_readme_and_changelog()
```

## Best Practices

1. **Regular Reviews**: Run documentation reviews weekly to catch outdated content early
2. **Dry Run First**: Always use `dry_run=True` before auto-archiving to preview changes
3. **Git Integration**: Enable Git checks for accurate last-modified tracking
4. **Metadata Rich**: Include comprehensive metadata when manually archiving
5. **Sync After Updates**: Run sync after version bumps to keep docs consistent
6. **Archive Before Major Changes**: Always archive before refactoring documentation

## API Reference

### Core Methods

#### `review_documentation(check_git=True) -> Dict`
Performs comprehensive documentation review with outdated content detection.

#### `auto_detect_and_archive_outdated(dry_run=False) -> Dict`
Automatically detects and archives outdated documentation files.

#### `sync_with_readme_and_changelog() -> Dict`
Synchronizes version numbers and key information across documentation files.

#### `archive_file(file_path, reason=None, metadata=None) -> Optional[Path]`
Archives a file with optional reason and metadata.

#### `restore_archive(archive_name, target_path=None) -> Tuple[bool, str]`
Restores an archived file to its original or specified location.

#### `get_file_git_history(file_path, limit=10) -> List[Dict]`
Retrieves Git commit history for a specific file.

### Display Methods

#### `display_review_summary(review: Dict) -> None`
Displays a formatted summary of the documentation review.

#### `generate_documentation_diff_report(file1, file2=None) -> str`
Generates a unified diff between two documentation versions.

#### `create_archive_report() -> Dict`
Creates a comprehensive report of all archives.

## Future Enhancements

- **AI-Powered Review**: Use LLM to suggest documentation improvements
- **Cross-Reference Checking**: Verify links and references across docs
- **Template Updates**: Auto-update documentation from templates
- **Change Impact Analysis**: Assess impact of code changes on documentation
- **Multi-Language Support**: Review documentation in multiple languages
- **Documentation Coverage**: Track which code areas lack documentation

## Conclusion

The Enhanced Archive Manager provides a comprehensive solution for documentation lifecycle management in Claude MPM projects. By combining Git history analysis, intelligent content detection, and automated archival, it helps maintain high-quality, up-to-date documentation while preserving historical versions for reference.