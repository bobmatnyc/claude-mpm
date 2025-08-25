# Archive Documentation

This directory contains curated archived documentation following the August 2025 documentation reorganization and deep pruning. Files are preserved for historical reference and troubleshooting.

## 📋 Archive History

### August 2025 Reorganization
Claude MPM documentation was reorganized into a cleaner, audience-focused structure:

**Before**: Mixed files in root `/docs/` directory  
**After**: Organized into `/user/`, `/developer/`, `/agents/`, `/reference/` sections

### August 24, 2025 Deep Pruning
The archive was significantly pruned to remove redundant content and optimize storage:

- **Files Reduced**: From ~150+ to 77 files
- **Size Reduction**: 5.2M → 944K (82.7% reduction)
- **Backup Created**: `docs_archive_backup_20250824_133926.tar.gz` (4.3M compressed)
- **Content Removed**: Redundant screenshots, completed implementation docs, outdated test reports

## 📂 Current Archive Structure (Post-Pruning)

The archive now contains only the most valuable historical content:

### `old-versions/` - Historical Release Information
- **`release-notes/`** - Version-specific release notes (v3.6.0 - v4.0.x)
- **`releases/`** - Historical changelogs and version documentation

### `screenshots/dashboard/` - Reference Screenshots  
- **`dashboard_initial.png`** - Original dashboard state (preserved for reference)
- **`dashboard_final.png`** - Final dashboard state (preserved for reference)
- **Note**: 3.7M of redundant screenshots were removed during pruning

### `temporary/` - Important Technical Documentation
High-value implementation summaries and architectural decisions:
- Security enhancements and fixes
- Memory system optimizations  
- Performance improvements
- Critical architectural changes
- Feature implementation guides
- **Note**: Completed/redundant implementation docs (180K) were removed

### `test-reports/` - Critical Test Documentation
Key QA reports and verification results with lasting value:
- Memory system verification reports
- Agent deployment testing
- Critical system fixes validation
- **Note**: Redundant test reports (90K) were removed during pruning

## 🔍 Finding Content After Pruning

**Looking for something that used to be in the archive?**

### Still Available (Preserved)
| Content Type | Location | Description |
|--------------|-----------|-------------|
| Release history | `old-versions/release-notes/` | Version-specific documentation |
| Key architecture docs | `temporary/` | Important design decisions |  
| Critical test reports | `test-reports/` | High-value QA documentation |
| Reference screenshots | `screenshots/dashboard/` | Essential UI references |

### Removed During Pruning
| Content Type | Reason for Removal | Recovery |
|--------------|-------------------|----------|
| Redundant screenshots | Multiple identical test images | Available in backup file |
| Completed implementation docs | No longer relevant | Available in backup file |
| Outdated test reports | Superseded by newer tests | Available in backup file |

### Relocated to Current Docs
| Old Location | New Location | Description |
|--------------|-------------|-------------|
| `docs/ARCHITECTURE.md` | `docs/developer/ARCHITECTURE.md` | System architecture |
| `docs/TESTING.md` | `docs/developer/TESTING.md` | Testing strategies |
| `docs/QA.md` | `docs/developer/QA.md` | Quality assurance |
| `docs/DEPLOY.md` | `docs/reference/DEPLOY.md` | Deployment guide |
| `docs/SECURITY.md` | `docs/reference/SECURITY.md` | Security configuration |
| `docs/MIGRATION.md` | `docs/user/MIGRATION.md` | User migration guide |

## 🎯 Usage Guidelines

**Use archived content for**:
- Understanding historical implementation decisions
- Troubleshooting issues with context from past fixes
- Compliance and audit trails
- Researching how features evolved over time
- Reference for architectural changes and their rationale

**For current documentation**, use the main docs directory:
- [User Documentation](../user/README.md)
- [Developer Documentation](../developer/README.md)
- [Agent Documentation](../agents/README.md)
- [Reference Documentation](../reference/README.md)

## 🗂️ Content Recovery

If you need content that was removed during pruning:

1. **Check the backup**: `docs_archive_backup_20250824_133926.tar.gz`
2. **Review pruning details**: [PRUNING_REPORT_20250824.md](./PRUNING_REPORT_20250824.md)
3. **Consider if current docs**: Content may have been moved to current documentation

## ⚠️ Important Notes

- **Curated content**: Archive now contains only high-value historical documentation
- **No longer maintained**: Content in this archive is not updated
- **Historical accuracy**: Files reflect the state at time of archiving
- **Link integrity**: Internal links may be broken due to reorganization
- **Context matters**: Consider the date context when referencing archived content
- **Pruning benefits**: 82.7% size reduction improves repository performance

---

**Need help finding something?** Check the [main documentation hub](../README.md) or search in the appropriate current section.