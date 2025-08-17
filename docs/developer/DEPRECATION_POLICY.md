# Deprecation Policy

This document outlines the formal deprecation policy for the claude-mpm project, including procedures for removing obsolete code, documentation, and maintaining a clean codebase.

## Overview

The claude-mpm project follows a structured approach to deprecating and removing obsolete code to maintain a clean, maintainable codebase while ensuring backward compatibility during transition periods.

## Deprecation Lifecycle

### Phase 1: Deprecation Warning (3 months)
- Mark code/features as deprecated with clear warnings
- Add deprecation notices in documentation
- Provide migration paths and alternatives
- Continue full functionality

### Phase 2: Deprecation Notice (6 months)
- Increase visibility of deprecation warnings
- Update documentation to emphasize alternatives
- Begin removing from examples and tutorials
- Functionality remains but may have reduced support

### Phase 3: Removal (12 months)
- Remove deprecated code/features
- Update all documentation
- Ensure migration tools are available
- Breaking change with major version bump

## Deprecation Categories

### 1. Code Deprecation

#### Experimental Code
- **Location**: `src/claude_mpm/experimental/`
- **Policy**: Experimental code may be removed without full deprecation cycle
- **Notice Period**: 1 month minimum
- **Examples**: 
  - `cli_enhancements.py` - Alternative CLI implementation
  - Prototype features and proof-of-concepts

#### Legacy Modules
- **Policy**: Full 12-month deprecation cycle
- **Examples**:
  - `cli_module/` - Old CLI architecture patterns
  - Legacy service implementations

#### Obsolete Files
- **Policy**: Immediate removal if no longer referenced
- **Examples**:
  - Backup files (`*.bak`, `*_original.py`)
  - Empty or minimal files with no functionality
  - Duplicate implementations

### 2. API Deprecation

#### Function/Method Deprecation
```python
import warnings
from typing import Optional

def deprecated_function(param: str) -> str:
    """
    This function is deprecated and will be removed in version 4.0.0.
    Use new_function() instead.
    
    Args:
        param: Parameter description
        
    Returns:
        Return value description
        
    Deprecated:
        Since version 3.9.0. Use new_function() instead.
        Will be removed in version 4.0.0.
    """
    warnings.warn(
        "deprecated_function() is deprecated and will be removed in version 4.0.0. "
        "Use new_function() instead.",
        DeprecationWarning,
        stacklevel=2
    )
    return new_function(param)
```

#### Class Deprecation
```python
import warnings

class DeprecatedClass:
    """
    This class is deprecated and will be removed in version 4.0.0.
    Use NewClass instead.
    
    Deprecated:
        Since version 3.9.0. Use NewClass instead.
        Will be removed in version 4.0.0.
    """
    
    def __init__(self):
        warnings.warn(
            "DeprecatedClass is deprecated and will be removed in version 4.0.0. "
            "Use NewClass instead.",
            DeprecationWarning,
            stacklevel=2
        )
```

### 3. Configuration Deprecation

#### Environment Variables
- Old variables continue to work with warnings
- New variables take precedence
- Clear migration documentation provided

#### Configuration Files
- Old format supported with warnings
- Migration tools provided
- Clear upgrade paths documented

### 4. Documentation Deprecation

#### Obsolete Documentation
- **Policy**: Remove immediately if content is outdated
- **Examples**:
  - Old API documentation
  - Outdated tutorials
  - Superseded guides

#### Legacy Documentation
- **Policy**: Mark as deprecated, provide alternatives
- **Timeline**: Remove after 6 months

## Identification Process

### Automated Detection

#### 1. Obsolete File Scanner
```bash
# Run the obsolete files scanner
python cleanup_obsolete_files.py

# Review the generated report
cat obsolete_files_report.txt
```

#### 2. Code Analysis
- Use static analysis tools to find unused code
- Identify duplicate implementations
- Detect deprecated patterns

#### 3. Documentation Audit
```bash
# Run documentation audit
python tools/dev/audit_documentation.py

# Check for deprecated patterns
grep -r "deprecated\|obsolete\|legacy" docs/
```

### Manual Review Process

#### Monthly Review
- Review experimental code for promotion or removal
- Identify unused features
- Check for duplicate implementations
- Update deprecation timelines

#### Quarterly Cleanup
- Remove files past deprecation timeline
- Update documentation
- Clean up test files
- Archive old examples

## Removal Procedures

### 1. Code Removal

#### Pre-removal Checklist
- [ ] Deprecation period completed
- [ ] No active references in codebase
- [ ] Migration documentation available
- [ ] Tests updated
- [ ] Documentation updated

#### Removal Process
1. Create removal branch
2. Remove deprecated code
3. Update imports and references
4. Run full test suite
5. Update documentation
6. Create pull request with detailed changelog

### 2. Safe Removal Script

```bash
#!/bin/bash
# Safe removal script template

echo "Removing deprecated code..."

# 1. Backup current state
git checkout -b "remove-deprecated-$(date +%Y%m%d)"

# 2. Remove files
rm -f src/claude_mpm/experimental/cli_enhancements.py
rm -rf src/claude_mpm/cli_module/

# 3. Update imports (if needed)
# Use automated tools or manual updates

# 4. Run tests
python -m pytest tests/

# 5. Update documentation
# Remove references to deprecated code

echo "Removal complete. Review changes before committing."
```

## Current Deprecation Status

### Scheduled for Removal

#### Immediate (Next Release)
- `cleanup_obsolete_files.py` - One-time cleanup script
- `remove_obsolete_files.sh` - Empty cleanup script
- `remove_duplicate_files.py` - One-time cleanup script

#### Phase 1 (3 months)
- `src/claude_mpm/experimental/cli_enhancements.py` - Experimental CLI
- `src/claude_mpm/cli_module/` - Legacy CLI patterns

#### Phase 2 (6 months)
- Legacy import paths (with compatibility layer)
- Old configuration formats

### Migration Paths

#### CLI Module Migration
- **From**: `src/claude_mpm/cli_module/`
- **To**: `src/claude_mpm/cli/`
- **Migration**: Use new modular CLI structure
- **Documentation**: [CLI Architecture](../cli/README.md)

#### Experimental CLI Migration
- **From**: `src/claude_mpm/experimental/cli_enhancements.py`
- **To**: Integrate useful features into main CLI
- **Migration**: Extract reusable patterns, discard experimental code

## Best Practices

### For Developers

1. **Mark deprecations clearly** with warnings and documentation
2. **Provide migration paths** for all deprecated features
3. **Use semantic versioning** for breaking changes
4. **Test migration paths** to ensure they work
5. **Communicate changes** in release notes and documentation

### For Users

1. **Monitor deprecation warnings** in your code
2. **Plan migrations** during deprecation periods
3. **Test with new versions** before upgrading production
4. **Read release notes** for breaking changes
5. **Report issues** with migration paths

## Tools and Scripts

### Cleanup Tools
- `cleanup_obsolete_files.py` - Identify obsolete files
- `tools/dev/audit_documentation.py` - Documentation audit
- `scripts/setup_pre_commit.sh` - Code quality automation

### Migration Tools
- Automated import path updates
- Configuration migration scripts
- Documentation update tools

## Monitoring and Metrics

### Deprecation Metrics
- Number of deprecated features
- Usage of deprecated APIs
- Migration completion rates
- User feedback on deprecations

### Cleanup Metrics
- Files removed per release
- Code reduction percentage
- Test coverage maintenance
- Documentation accuracy

## Support and Communication

### Deprecation Announcements
- Release notes
- Documentation updates
- GitHub issues for major deprecations
- Migration guides

### Support Channels
- GitHub issues for migration problems
- Documentation for self-service migration
- Examples and tutorials for new patterns

## Review and Updates

This deprecation policy is reviewed quarterly and updated as needed to reflect project evolution and community feedback.

**Last Updated**: 2025-08-17
**Next Review**: 2025-11-17
**Version**: 1.0
