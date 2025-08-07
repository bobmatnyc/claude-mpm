# Project Reorganization Migration Guide

**Version**: 3.4.5  
**Date**: 2025-08-07

## Overview

Version 3.4.5 includes a major project reorganization to improve maintainability and follow standard project structure conventions. This guide documents the changes and any necessary migration steps.

## Changes Made

### File Movements

1. **Test Files Reorganization**
   - **Moved**: 458+ test files from `/scripts/` to `/tests/`
   - **Reason**: Test files belong in the dedicated `/tests/` directory per Python conventions
   - **Impact**: No impact on functionality - tests still work the same way

2. **Dashboard Consolidation**
   - **Moved**: Web-related files consolidated into `/src/claude_mpm/dashboard/`
   - **Previous**: Various locations for dashboard files
   - **Impact**: Cleaner organization, no functional changes

### New Directory Structure

3. **Documentation Organization**
   - **Added**: `/docs/archive/` - Historical documentation and QA reports
   - **Added**: `/docs/assets/` - Documentation assets (images, logos)
   - **Added**: `/docs/developer/` - Developer-focused documentation
   - **Added**: `/docs/user/` - End-user documentation

4. **Test Organization**
   - **Added**: `/tests/fixtures/` - Centralized test data
   - **Added**: `/tests/test-reports/` - Test execution reports
   - **Added**: `/tests/agents/` - Agent-specific tests
   - **Added**: `/tests/integration/` - Integration tests
   - **Added**: `/tests/services/` - Service layer tests

## Backward Compatibility

### Ticket Functionality

For any code that imported ticket functionality from the old location:

**Issue**: Code that imported from `src/claude_mpm/ticket.py` would break after reorganization.

**Solution**: Added `src/claude_mpm/ticket_wrapper.py` as a compatibility layer.

```python
# ticket_wrapper.py provides backward compatibility
import sys
import os
from pathlib import Path

# Add scripts directory to path so we can import the ticket module
scripts_dir = Path(__file__).parent.parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))

# Import and re-export the main function
try:
    from ticket import main
except ImportError:
    # Fallback if direct import fails
    import importlib.util
    ticket_path = scripts_dir / "ticket.py"
    spec = importlib.util.spec_from_file_location("ticket", ticket_path)
    ticket_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ticket_module)
    main = ticket_module.main
```

**Usage**: Any existing imports will continue to work without modification.

## Migration Steps

### For Developers

1. **No Action Required**: All existing functionality continues to work
2. **Test Scripts**: Use existing test commands - paths are automatically resolved
3. **Documentation**: Refer to the updated structure in `docs/STRUCTURE.md`

### For Contributors

1. **New Test Files**: Place in appropriate subdirectory under `/tests/`
2. **Documentation**: Use the new organized structure in `/docs/`
3. **Assets**: Place images and other assets in `/docs/assets/`

## Verification

To verify the migration was successful:

```bash
# Verify tests still work
./scripts/run_e2e_tests.sh

# Verify documentation structure
ls docs/

# Verify backward compatibility
python -c "from claude_mpm.ticket_wrapper import main; print('Ticket wrapper working')"
```

## Impact Assessment

- ✅ **No Breaking Changes**: All existing functionality preserved
- ✅ **Backward Compatibility**: `ticket_wrapper.py` maintains old import paths
- ✅ **Improved Organization**: Better separation of concerns
- ✅ **Standard Conventions**: Follows Python project layout best practices

## Rollback Plan

If issues are discovered:

1. The reorganization can be reverted by moving files back to original locations
2. Remove `ticket_wrapper.py` if reverting ticket functionality
3. Update `docs/STRUCTURE.md` to reflect original structure

## Related Documentation

- [Project Structure](../../STRUCTURE.md) - Updated project layout
- [CHANGELOG.md](../../../CHANGELOG.md) - Detailed change log for v3.4.5
- [Testing Guide](../../03-development/testing.md) - Updated testing procedures