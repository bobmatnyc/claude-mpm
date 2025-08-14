# Enhanced Version Parsing System

## Overview

The Claude MPM project includes a robust version parsing system that retrieves version information from multiple sources with intelligent fallback mechanisms. This system ensures version information is always available, even when certain sources are unavailable or corrupted.

## Architecture

### Multi-Source Version Detection

The enhanced version parser (`version_parser.py`) implements a priority-based source system:

1. **Git Tags** (Primary Source - Most Reliable)
   - Authoritative source for release versions
   - Includes commit metadata and release dates
   - Supports annotated tags with messages

2. **CHANGELOG.md** (Secondary Source)
   - Provides version history with release notes
   - Extracts changes and release dates
   - Supports multiple changelog formats

3. **VERSION File** (Current Version)
   - Simple text file with version number
   - Quick access without git dependency
   - Synchronized with releases

4. **package.json** (NPM Packages)
   - Standard for JavaScript/Node.js projects
   - Includes package metadata

5. **pyproject.toml** (Python Projects)
   - Modern Python packaging standard
   - Supports both [project] and [tool.poetry] sections

### Fallback Mechanism

The system implements intelligent fallback:

```python
# Priority order for version sources
PRIORITY_ORDER = [
    GIT_TAGS,        # Most reliable
    CHANGELOG,       # Historical context
    VERSION_FILE,    # Simple fallback
    PACKAGE_JSON,    # Language-specific
    PYPROJECT_TOML,  # Language-specific
    SETUP_PY         # Legacy Python
]
```

If the primary source (git tags) is unavailable, the system automatically falls back to the next available source.

## Usage

### Basic Usage

```python
from claude_mpm.services.version_control.version_parser import EnhancedVersionParser

# Create parser instance
parser = EnhancedVersionParser()

# Get current version from best available source
current = parser.get_current_version()
print(f"Current version: {current.version} from {current.source}")

# Get complete version history
history = parser.get_version_history()
for version in history:
    print(f"{version.version} - {version.release_date}")
```

### Integration with Semantic Versioning

The enhanced parser seamlessly integrates with the existing `SemanticVersionManager`:

```python
from claude_mpm.services.version_control.semantic_versioning import SemanticVersionManager

manager = SemanticVersionManager(project_root, logger)

# Automatically uses enhanced parser with fallback
current_version = manager.get_current_version()
version_history = manager.get_version_history()
```

### Version Consistency Validation

Check version consistency across all sources:

```python
parser = EnhancedVersionParser()
consistency = parser.validate_version_consistency()

for source, version in consistency.items():
    print(f"{source}: {version}")

# Identify inconsistencies
if len(set(consistency.values())) > 1:
    print("Warning: Version mismatch detected across sources!")
```

## Features

### 1. Performance Optimization

- **Caching**: Results are cached with configurable TTL (default: 5 minutes)
- **Lazy Loading**: Sources are only queried when needed
- **Compiled Regex**: Patterns are compiled once for efficiency

### 2. Pre-release Filtering

```python
# Exclude pre-release versions
stable_versions = parser.get_version_history(include_prereleases=False)

# Include all versions
all_versions = parser.get_version_history(include_prereleases=True)
```

### 3. Metadata Extraction

Each version includes rich metadata:

```python
class VersionMetadata:
    version: str          # Semantic version string
    source: str          # Source it was retrieved from
    release_date: datetime  # When released
    commit_hash: str     # Git commit (if available)
    author: str          # Release author
    message: str         # Release message
    changes: List[str]   # List of changes
```

### 4. Error Handling

The system gracefully handles various failure scenarios:

- Missing git installation
- Corrupted version files
- Invalid JSON/TOML syntax
- Network failures
- File permission issues

## Configuration

### Cache Settings

```python
# Configure cache TTL (in seconds)
parser = EnhancedVersionParser(cache_ttl=300)  # 5 minutes

# Disable caching
parser = EnhancedVersionParser(cache_ttl=0)
```

### Project Root

```python
# Specify project root directory
from pathlib import Path
parser = EnhancedVersionParser(project_root=Path('/path/to/project'))
```

## Testing

The system includes comprehensive tests covering:

- Multi-source version detection
- Fallback mechanism verification
- Cache behavior validation
- Pre-release filtering
- Version consistency checking
- Error handling scenarios
- Integration with SemanticVersionManager

Run tests:

```bash
python -m pytest tests/test_version_parser.py -v
```

## Migration Guide

### For Existing Projects

The enhanced version parser is backward compatible. Existing code using `SemanticVersionManager` will automatically benefit from the improvements:

```python
# Old code (still works, now enhanced)
manager = SemanticVersionManager(project_root, logger)
version = manager.get_current_version()

# Direct usage of enhanced parser (optional)
from claude_mpm.services.version_control.version_parser import get_version_parser
parser = get_version_parser()
version = parser.get_current_version()
```

### Updating Version Sources

To ensure optimal version detection:

1. **Maintain Git Tags**: Use annotated tags for releases
   ```bash
   git tag -a v3.8.1 -m "Release 3.8.1"
   git push --tags
   ```

2. **Keep VERSION File Updated**: Synchronize with releases
   ```bash
   echo "3.8.1" > VERSION
   ```

3. **Update package.json/pyproject.toml**: Keep version fields current
   ```json
   {
     "version": "3.8.1"
   }
   ```

## Best Practices

1. **Use Git Tags as Primary Source**
   - Most reliable and includes metadata
   - Integrates with CI/CD pipelines
   - Provides historical context

2. **Maintain Changelog**
   - Provides human-readable history
   - Documents changes between versions
   - Useful when git history is unavailable

3. **Synchronize Version Files**
   - Use automation to keep files in sync
   - Run consistency checks in CI
   - Alert on version mismatches

4. **Handle Pre-releases Properly**
   - Use semantic versioning conventions
   - Filter pre-releases for production
   - Document pre-release strategy

## Troubleshooting

### Common Issues

1. **Version Not Found**
   - Check if any version source exists
   - Verify file permissions
   - Ensure git is installed and accessible

2. **Version Mismatch**
   - Run consistency validation
   - Update out-of-sync sources
   - Use git tags as source of truth

3. **Cache Issues**
   - Reduce cache TTL for frequently changing versions
   - Clear cache manually if needed
   - Disable cache for debugging

### Debug Mode

Enable debug logging to troubleshoot issues:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

parser = EnhancedVersionParser()
version = parser.get_current_version()
```

## API Reference

### EnhancedVersionParser

```python
class EnhancedVersionParser:
    def __init__(self, project_root: Optional[Path] = None, cache_ttl: int = 300):
        """Initialize parser with project root and cache settings."""
    
    def get_current_version(self, prefer_source: Optional[str] = None) -> Optional[VersionMetadata]:
        """Get current version from best available source."""
    
    def get_version_history(self, include_prereleases: bool = False, limit: Optional[int] = None) -> List[VersionMetadata]:
        """Get complete version history from all sources."""
    
    def validate_version_consistency(self) -> Dict[str, str]:
        """Check version consistency across all sources."""
    
    def get_version_for_release(self) -> Optional[str]:
        """Get version to use for next release."""
```

### VersionMetadata

```python
class VersionMetadata:
    version: str              # Semantic version string
    source: str              # Source identifier
    release_date: datetime   # Release timestamp
    commit_hash: str         # Git commit hash
    author: str              # Release author
    message: str             # Release message
    changes: List[str]       # List of changes
    
    def to_dict(self) -> Dict:
        """Convert to dictionary format."""
```

## Future Enhancements

Planned improvements for the version parsing system:

1. **Remote Repository Support**
   - Query versions from remote git repositories
   - Support for GitHub/GitLab API integration

2. **Version Prediction**
   - Suggest next version based on changes
   - Automatic version bumping rules

3. **Extended Metadata**
   - Download statistics
   - Dependency changes
   - Breaking change detection

4. **Performance Metrics**
   - Version parsing performance tracking
   - Cache hit rate monitoring
   - Source availability statistics