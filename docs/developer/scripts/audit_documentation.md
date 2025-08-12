# Documentation Audit Script

The `scripts/audit_documentation.py` script provides comprehensive validation of documentation compliance with Claude MPM's structure requirements defined in `docs/STRUCTURE.md`.

## Purpose

This script ensures that documentation is properly organized, follows naming conventions, and maintains consistency across the project before each release. It helps identify and fix common documentation issues that could impact project maintainability and user experience.

## What the Script Checks

### 1. Directory Structure Compliance
- **Validates expected directories exist**: Checks for required subdirectories under `docs/` as defined in `STRUCTURE.md`
- **Identifies unexpected directories**: Flags directories that don't match the expected structure
- **Suggests corrections**: Provides actionable items for missing directories

**Expected structure:**
```
docs/
├── archive/          # Historical documentation, QA reports
├── assets/           # Documentation assets (images, diagrams)
├── dashboard/        # Dashboard documentation
├── design/           # Design documents and specifications
├── developer/        # Developer documentation (API, internals, guides)
├── examples/         # Usage examples and configurations
├── qa/               # QA reports and test documentation
└── user/             # User-facing documentation
```

### 2. Naming Convention Validation
- **Major documentation files**: Must follow `UPPER_CASE.md` pattern (e.g., `README.md`, `STRUCTURE.md`)
- **Subdirectories**: Must follow `lowercase-with-hyphens` pattern (e.g., `api-reference`, `getting-started`)
- **Numbered directories**: Must follow `##-descriptive-name` pattern (e.g., `01-architecture`, `02-core-components`)

### 3. Numbered Directory README Requirements
- **Validates README.md presence**: Every numbered directory must contain a `README.md` file
- **Auto-creates missing READMEs**: Can automatically generate basic README templates when using `--fix`

### 4. Duplicate Content Detection
- **Content fingerprinting**: Uses MD5 hashes to identify identical content across files
- **Agent documentation analysis**: Special focus on detecting duplicate content in agent-related documentation
- **Similarity detection**: Identifies common sections that appear across multiple documents

### 5. Deprecated Reference Detection
- **Legacy pattern matching**: Searches for outdated references that need updating:
  - `claude-multiagent-pm` (old project name)
  - `CLAUDE.md` (legacy instruction file)
  - `.claude-mpm/agents/templates/` (old template location)
  - `legacy_`, `_old`, `deprecated` patterns
- **Line-by-line analysis**: Provides specific line numbers where deprecated references are found

### 6. Broken Link Validation
- **Internal link checking**: Validates that internal links (relative paths) point to existing files
- **Cross-reference validation**: Ensures documentation cross-references are accurate
- **Link categorization**: Distinguishes between internal and external links

### 7. File Placement Analysis
- **Content-based placement rules**: Uses file naming patterns to suggest optimal directory placement:
  - QA reports → `docs/qa/` or `docs/archive/qa-reports/`
  - API references → `docs/developer/04-api-reference/`
  - User guides → `docs/user/`
  - Installation docs → `docs/user/`
  - Security docs → `docs/developer/09-security/`
- **Misplacement detection**: Identifies files that may be in suboptimal locations

### 8. Redundant Content Analysis
- **Topic overlap detection**: Identifies topics that appear across multiple files
- **Content consolidation suggestions**: Recommends opportunities for reducing redundancy
- **Agent documentation efficiency**: Special focus on reducing duplication in agent-related docs

## Usage Examples

### Basic Audit
```bash
python scripts/audit_documentation.py
```
**Output**: Summary report with issue counts and deployment readiness status.

### Detailed Analysis
```bash
python scripts/audit_documentation.py --verbose
```
**Output**: Real-time feedback during analysis with detailed issue descriptions.

### Auto-Fix Simple Issues
```bash
python scripts/audit_documentation.py --fix --verbose
```
**What gets fixed automatically:**
- Creates missing directories
- Generates basic README.md files for numbered directories
- Renames files to follow naming conventions (conservative approach)

### CI/CD Integration
```bash
python scripts/audit_documentation.py --json --strict
```
**Features:**
- JSON output for automated processing
- Exits with error code if deployment-blocking issues found
- Suitable for continuous integration pipelines

### Custom Project Root
```bash
python scripts/audit_documentation.py --project-root /path/to/project
```
**Use case**: Running the script from outside the project directory.

## Understanding the Results

### Issue Severity Levels

1. **ERROR** 🔴
   - **Impact**: Blocks deployment readiness
   - **Examples**: Missing README.md in numbered directories, broken internal links
   - **Action Required**: Must be fixed before release

2. **WARNING** 🟡
   - **Impact**: Affects maintainability but doesn't block deployment
   - **Examples**: Naming convention violations, deprecated references
   - **Action Required**: Should be addressed in current release cycle

3. **INFO** 🔵
   - **Impact**: Optimization opportunities
   - **Examples**: Potential content consolidation, redundant topics
   - **Action Required**: Consider for future improvements

### Sample Output Format

#### Human-Readable Report
```
============================================================
DOCUMENTATION AUDIT REPORT
============================================================
Files Scanned: 127
Issues Found: 8
  - Errors: 2
  - Warnings: 5
  - Info: 1
Fixable Issues: 4
Duration: 1.23s
Deployment Ready: ❌ NO

ISSUES BY CATEGORY:
----------------------------------------

STRUCTURE (2 issues):
  [error] docs/developer/03-development/testing
    Numbered directory missing README.md: testing
    → Create docs/developer/03-development/testing/README.md

NAMING (3 issues):
  [warning] docs/setup-guide.md
    File should follow UPPER_CASE naming: setup-guide.md
    → Rename to SETUP_GUIDE.md
```

#### JSON Output
```json
{
  "summary": {
    "total_files_scanned": 127,
    "issues_found": 8,
    "errors": 2,
    "warnings": 5,
    "info": 1,
    "fixable_issues": 4,
    "deployment_ready": false,
    "duration_seconds": 1.23
  },
  "issues": [
    {
      "category": "structure",
      "severity": "error",
      "file_path": "docs/developer/03-development/testing",
      "line_number": null,
      "message": "Numbered directory missing README.md: testing",
      "suggestion": "Create docs/developer/03-development/testing/README.md",
      "fixable": true
    }
  ]
}
```

## Common Issues and Solutions

### Issue: Missing README.md in Numbered Directories
**Symptom**: Error messages about missing README.md files in directories like `01-architecture`, `02-core-components`

**Solution**: 
```bash
# Auto-fix approach
python scripts/audit_documentation.py --fix

# Manual approach
touch docs/developer/01-architecture/README.md
echo "# Architecture Overview\n\nTODO: Add architecture documentation." > docs/developer/01-architecture/README.md
```

### Issue: Naming Convention Violations
**Symptom**: Warning messages about files not following UPPER_CASE or lowercase-with-hyphens patterns

**Solutions**:
```bash
# Major documentation files should be UPPER_CASE
mv docs/setup-guide.md docs/SETUP_GUIDE.md

# Directory names should be lowercase-with-hyphens
mv docs/API_Reference docs/api-reference

# Auto-fix (conservative)
python scripts/audit_documentation.py --fix
```

### Issue: Deprecated References
**Symptom**: Warning messages about legacy terms or old paths

**Solution**: Update documentation to use current terminology:
```markdown
# ❌ Old reference
See the claude-multiagent-pm documentation...

# ✅ Updated reference  
See the Claude MPM documentation...
```

### Issue: Broken Internal Links
**Symptom**: Error messages about links pointing to non-existent files

**Solutions**:
```markdown
# ❌ Broken link
[See setup guide](./setup.md)

# ✅ Fixed link (update path)
[See setup guide](../user/01-getting-started/installation.md)

# ✅ Fixed link (create missing file)
# Create the missing setup.md file
```

### Issue: Duplicate Content
**Symptom**: Warning messages about identical or very similar content across files

**Solutions**:
1. **Consolidate**: Merge similar content into a single authoritative source
2. **Reference**: Replace duplicates with references to the main content
3. **Specialize**: Keep similar content but differentiate for specific audiences

```markdown
# ❌ Duplicate installation instructions in multiple files

# ✅ Single source with references
# In main installation doc
## Installation Instructions
[Detailed steps...]

# In other docs
For installation instructions, see [Installation Guide](../user/INSTALL.md).
```

### Issue: File Placement
**Symptom**: Warning messages suggesting files may be in wrong directories

**Solution**: Move files to suggested locations:
```bash
# Move API documentation to appropriate directory
mv docs/api-guide.md docs/developer/04-api-reference/

# Move user guides to user directory
mv docs/getting-started.md docs/user/01-getting-started/
```

## Integration with Release Process

### Pre-Release Checklist
1. **Run full audit**: `python scripts/audit_documentation.py --verbose`
2. **Fix all errors**: Ensure deployment readiness = ✅ YES
3. **Address warnings**: Fix high-impact warnings for current release
4. **Review suggestions**: Consider info-level suggestions for future releases

### CI/CD Integration
Add to your deployment pipeline:
```yaml
# Example GitHub Actions integration
- name: Audit Documentation
  run: |
    python scripts/audit_documentation.py --json --strict
    if [ $? -ne 0 ]; then
      echo "Documentation audit failed. Please fix issues before merging."
      exit 1
    fi
```

### Automated Fixes in CI
For development branches, you might auto-fix simple issues:
```yaml
- name: Auto-fix Documentation Issues
  run: |
    python scripts/audit_documentation.py --fix
    if [ -n "$(git status --porcelain)" ]; then
      git add .
      git commit -m "docs: auto-fix documentation issues"
      git push
    fi
```

## Performance Considerations

- **File scanning**: Script processes all `.md` files under `docs/`
- **Memory usage**: Loads file content into memory for duplicate detection
- **Execution time**: Typically 1-3 seconds for projects with 100-200 documentation files
- **Caching**: No caching implemented; each run performs full analysis

## Limitations

1. **Content quality**: Script focuses on structure and consistency, not content quality or accuracy
2. **External links**: Only validates internal links; external links are not checked
3. **Language detection**: No grammar or spelling validation
4. **Format parsing**: Basic Markdown parsing; may miss complex formatting issues
5. **Context awareness**: Cannot determine if content duplication is intentional

## Future Enhancements

Planned improvements for future versions:
- External link validation
- Content freshness checking (last modified dates)
- Integration with Vale or similar style checkers
- Automated content quality scoring
- Support for additional file formats (YAML, JSON configuration docs)
- Performance optimizations with incremental analysis

## Troubleshooting

### Permission Errors
```bash
chmod +x scripts/audit_documentation.py
```

### Module Import Errors
```bash
# Ensure you're running from project root
cd /path/to/claude-mpm
python scripts/audit_documentation.py

# Or specify project root explicitly
python scripts/audit_documentation.py --project-root /path/to/claude-mpm
```

### False Positives
If the script reports issues that are intentional:
1. Review the specific issue category and message
2. Consider if the current approach aligns with project standards
3. Update the script logic if needed (contribute back to project)
4. Document exceptions in project-specific guidelines

## Contributing

To improve the audit script:
1. Add new validation rules to appropriate `_audit_*()` methods
2. Update `expected_structure` for new directory requirements
3. Add patterns to `deprecated_patterns` for new legacy references
4. Extend `placement_rules` for new file type classifications
5. Test thoroughly with `--verbose` mode
6. Update this documentation with new features

The script is designed to be extensible and maintainable, following the same principles it enforces for documentation.