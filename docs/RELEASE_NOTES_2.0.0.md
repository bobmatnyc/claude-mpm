# Claude MPM 2.0.0 Release Summary

## Release Date: 2025-07-27

### Successfully Published To:
- ✅ **PyPI**: https://pypi.org/project/claude-mpm/2.0.0/
- ✅ **npm**: https://www.npmjs.com/package/@bobmatnyc/claude-mpm/v/2.0.0
- ✅ **GitHub Release**: https://github.com/bobmatnyc/claude-mpm/releases/tag/v2.0.0

### Key Changes:
1. **Fixed setuptools-scm configuration** to properly detect version 2.0.0
2. **Built packages** with correct version metadata
3. **Published to PyPI and npm** successfully
4. **Created comprehensive GitHub release** with breaking change notes

### Installation Commands:
```bash
# PyPI
pip install claude-mpm==2.0.0

# npm
npm install -g @bobmatnyc/claude-mpm@2.0.0
```

### Breaking Changes Summary:
- Agent IDs no longer use `_agent` suffix
- Migrated from YAML to JSON format
- Standardized model naming convention
- New resource tier system

### Migration:
Users with custom agents should run:
```bash
python scripts/migrate_agents_to_new_schema.py
```

### Verification:
Both package managers confirmed serving version 2.0.0, and test installation works correctly.