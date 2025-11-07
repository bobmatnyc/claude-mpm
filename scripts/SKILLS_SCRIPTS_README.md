# Skills Infrastructure Scripts

This directory contains scripts for managing Claude MPM's Skills Integration system.

## Overview

These scripts implement the skills infrastructure for downloading, validating, and bundling Claude Code skills with Claude MPM.

## Scripts

### 1. download_skills_api.py

**Purpose**: Download skills from GitHub repositories using the GitHub API (not git clone).

**Features**:
- GitHub API-based downloading (no git required)
- Authentication via `GITHUB_TOKEN` environment variable
- Rate limiting handling
- Progress reporting
- Dry-run mode
- Category and skill filtering
- SKILL.md validation after download

**Usage**:

```bash
# Download all skills
python scripts/download_skills_api.py

# Download specific category
python scripts/download_skills_api.py --category development

# Download specific skill
python scripts/download_skills_api.py --skill test-driven-development

# Dry run (see what would be downloaded)
python scripts/download_skills_api.py --dry-run

# Use GitHub token for higher rate limits
GITHUB_TOKEN=ghp_xxx python scripts/download_skills_api.py

# Check rate limit
python scripts/download_skills_api.py --check-rate-limit
```

**Environment Variables**:
- `GITHUB_TOKEN` - GitHub personal access token (optional but recommended)
  - Without token: 60 requests/hour
  - With token: 5000 requests/hour

**Configuration**:
- Sources: `config/skills_sources.yaml`
- Output: `src/claude_mpm/skills/bundled/`

### 2. validate_skills.py

**Purpose**: Validate SKILL.md files against the 16 validation rules from the specification.

**Features**:
- All 16 validation rules implemented
- Severity levels: CRITICAL, ERROR, WARNING
- JSON output for CI/CD integration
- Auto-fix for common issues (experimental)
- Colored terminal output
- Batch validation of all skills

**Usage**:

```bash
# Validate single skill
python scripts/validate_skills.py path/to/skill-directory

# Validate all bundled skills
python scripts/validate_skills.py --all

# JSON output for CI/CD
python scripts/validate_skills.py --format json path/to/skill

# Auto-fix common issues
python scripts/validate_skills.py --fix path/to/skill

# Verbose output
python scripts/validate_skills.py --verbose path/to/skill
```

**Exit Codes**:
- `0` - All validations passed
- `1` - Errors or warnings (deployment allowed)
- `2` - Critical failures (deployment blocked)

**Validation Rules**:
1. SKILL.md file presence
2. YAML frontmatter presence
3. Frontmatter delimiter format
4. Entry point line limit (<200 lines)
5. Required fields present
6. Name format validation
7. Name-directory match
8. Description length (10-150 chars)
9. Version format (semver)
10. Category validation
11. Progressive disclosure structure
12. Progressive disclosure entry point fields
13. Progressive disclosure field lengths
14. Reference files exist
15. Reference file line limits (150-300)
16. No circular references

### 3. generate_license_attributions.py

**Purpose**: Generate LICENSE_ATTRIBUTIONS.md for all bundled skills.

**Features**:
- Scans all bundled skills
- Extracts license information from SKILL.md frontmatter
- Groups by license type
- Markdown table format
- Validates all skills have license field
- Includes author, source URL, and description

**Usage**:

```bash
# Generate attribution file
python scripts/generate_license_attributions.py

# Specify custom bundled directory
python scripts/generate_license_attributions.py --bundled-dir path/to/bundled

# Dry run (print instead of writing)
python scripts/generate_license_attributions.py --dry-run

# Validate only (check all skills have licenses)
python scripts/generate_license_attributions.py --validate-only
```

**Output**:
- Default: `src/claude_mpm/skills/bundled/LICENSE_ATTRIBUTIONS.md`

## Configuration

### config/skills_sources.yaml

Defines GitHub repositories and skills to download.

**Structure**:
```yaml
version: 1.0.0
sources:
  superpowers:
    base_url: https://github.com/obra/superpowers-skills/tree/main/skills
    license: MIT
    maintainer: Jesse Vincent
    skills:
      development:
        - git-worktrees
      testing:
        - test-driven-development
      # ...
```

**Sources**:
- `superpowers` - Jesse Vincent's curated skills
- `anthropic` - Anthropic official skills
- `superpowers-marketplace` - Additional curated content
- `behisecc` - BehiSecc community skills
- `composio` - ComposioHQ community skills

## Workflow

### Initial Setup (Development)

1. **Download Skills**:
   ```bash
   # Download all skills with dry-run first
   python scripts/download_skills_api.py --dry-run

   # Download for real (requires GITHUB_TOKEN for many skills)
   GITHUB_TOKEN=ghp_xxx python scripts/download_skills_api.py
   ```

2. **Validate Skills**:
   ```bash
   # Validate all downloaded skills
   python scripts/validate_skills.py --all
   ```

3. **Generate License Attributions**:
   ```bash
   # Generate LICENSE_ATTRIBUTIONS.md
   python scripts/generate_license_attributions.py
   ```

### Adding New Skills

1. Edit `config/skills_sources.yaml` to add new skill
2. Download: `python scripts/download_skills_api.py --skill new-skill-name`
3. Validate: `python scripts/validate_skills.py path/to/new-skill`
4. Update licenses: `python scripts/generate_license_attributions.py`

### CI/CD Integration

Add to your CI pipeline:

```yaml
# .github/workflows/validate-skills.yml
- name: Validate Skills
  run: |
    python scripts/validate_skills.py --all --format json > validation-results.json
    if [ $? -eq 2 ]; then
      echo "Critical validation failures!"
      exit 1
    fi

- name: Validate Licenses
  run: |
    python scripts/generate_license_attributions.py --validate-only
```

## Dependencies

All scripts use standard library plus:
- `pyyaml` - YAML parsing
- `requests` - GitHub API calls (download script only)

These are already in Claude MPM's dependencies.

## Rate Limiting

### GitHub API Limits

- **Unauthenticated**: 60 requests/hour per IP
- **Authenticated**: 5,000 requests/hour

### Recommendations

- Always use `GITHUB_TOKEN` for development work
- Use dry-run mode first to estimate API calls
- Download during development, bundle with package
- Never download at runtime (bundled skills are pre-downloaded)

### Getting a GitHub Token

1. Go to: https://github.com/settings/tokens
2. Generate new token (classic)
3. Select scopes: `public_repo` (read-only)
4. Copy token and set: `export GITHUB_TOKEN=ghp_xxx`

## Troubleshooting

### Rate Limit Exceeded

```bash
# Check current rate limit
python scripts/download_skills_api.py --check-rate-limit

# Wait or use token
export GITHUB_TOKEN=ghp_xxx
```

### Validation Failures

```bash
# See detailed errors
python scripts/validate_skills.py --verbose path/to/skill

# Try auto-fix (experimental)
python scripts/validate_skills.py --fix path/to/skill
```

### Download Failures

```bash
# Enable verbose output
python scripts/download_skills_api.py --verbose

# Try single skill first
python scripts/download_skills_api.py --skill test-driven-development
```

## File Locations

```
claude-mpm/
├── config/
│   └── skills_sources.yaml          # Source configuration
├── scripts/
│   ├── download_skills_api.py       # Downloader
│   ├── validate_skills.py           # Validator
│   └── generate_license_attributions.py  # License generator
└── src/claude_mpm/skills/
    └── bundled/                      # Downloaded skills
        ├── development/
        ├── testing/
        ├── debugging/
        └── LICENSE_ATTRIBUTIONS.md
```

## Related Documentation

- Design: `docs/design/claude-mpm-skills-integration-design.md`
- Spec: `docs/design/SKILL-MD-FORMAT-SPECIFICATION.md`
- Decisions: `docs/design/mpm-skills-decisions-summary.md`

## Support

For issues or questions:
- GitHub Issues: [claude-mpm issues](https://github.com/bobmatnyc/claude-mpm/issues)
- Design Questions: See documentation in `docs/design/`

---

*Part of Claude MPM Skills Integration v4.15.0+*
