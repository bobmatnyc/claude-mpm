# CLI Help Text Improvement Suggestions

## Current State Analysis

The current CLI help text is **functional and clear**. Below are suggestions for minor improvements to enhance clarity and consistency.

## Suggested Improvements

### 1. Main `skill-source` Command Help

**Current:**
```
positional arguments:
  SUBCOMMAND            Skill source repository commands
```

**Suggested:**
```
positional arguments:
  SUBCOMMAND            Manage Git-based skill source repositories
```

**Rationale**: More descriptive, mentions Git-based nature.

---

### 2. `skill-source add` Help

**Current:**
```
usage: claude-mpm skill-source add [-h] [--branch BRANCH]
                                   [--priority PRIORITY] [--disabled]
                                   url

positional arguments:
  url                  Git repository URL (e.g.,
                       https://github.com/owner/repo)

options:
  -h, --help           show this help message and exit
  --branch BRANCH      Git branch to use (default: main)
  --priority PRIORITY  Priority for conflict resolution (lower = higher
                       precedence, default: 100)
  --disabled           Add repository but keep it disabled
```

**Suggested Improvements:**

1. **Add examples section:**
```
examples:
  # Add with defaults (branch: main, priority: 100, enabled)
  claude-mpm skill-source add https://github.com/myorg/skills

  # Add with custom priority (lower = higher precedence)
  claude-mpm skill-source add https://github.com/myorg/skills --priority 50

  # Add disabled (won't sync until enabled)
  claude-mpm skill-source add https://github.com/myorg/skills --disabled
```

2. **Clarify priority in description:**
```
  --priority PRIORITY  Priority for conflict resolution (default: 100)
                       Lower numbers = higher precedence (0 = highest)
                       Recommended range: 0-1000
```

**Rationale**: Examples help users understand usage patterns. Priority clarification prevents confusion about "lower = higher".

---

### 3. `skill-source list` Help

**Current:**
```
usage: claude-mpm skill-source list [-h] [--by-priority] [--enabled-only]
                                    [--json]

options:
  -h, --help      show this help message and exit
  --by-priority   Sort by priority (lowest first)
  --enabled-only  Show only enabled repositories
  --json          Output as JSON
```

**Suggested Improvements:**

1. **Add description:**
```
List configured skill source repositories.

Shows: ID, URL, branch, priority, enabled status, last update
```

2. **Add examples:**
```
examples:
  # List all sources
  claude-mpm skill-source list

  # List only enabled, sorted by priority
  claude-mpm skill-source list --enabled-only --by-priority

  # Export as JSON for scripting
  claude-mpm skill-source list --json > sources.json
```

**Rationale**: Users understand what information they'll get and how to use filters.

---

### 4. `skill-source update` Help

**Current:** (Assume similar to other commands)

**Suggested:**
```
usage: claude-mpm skill-source update [-h] [--force] [source_id]

Sync skill sources from Git repositories.

positional arguments:
  source_id     Specific source to update (default: all enabled sources)

options:
  -h, --help    show this help message and exit
  --force       Force re-download even if cached (ignores ETags)

examples:
  # Update all enabled sources (incremental via ETags)
  claude-mpm skill-source update

  # Update specific source
  claude-mpm skill-source update system

  # Force full re-download (ignores cache)
  claude-mpm skill-source update --force

what happens:
  - Connects to Git repository via HTTPS
  - Downloads changed files only (ETag-based caching)
  - Updates local cache: ~/.claude-mpm/cache/skills/
  - Discovers skills from new/changed files
  - Applies priority resolution for conflicts
```

**Rationale**: Explains what happens during update, mentions caching benefit, shows cache location.

---

### 5. `skill-source show` Help

**Suggested:**
```
usage: claude-mpm skill-source show [-h] [--verbose] source_id

Show detailed information about a skill source.

positional arguments:
  source_id      ID of source to show

options:
  -h, --help     show this help message and exit
  --verbose, -v  Include list of all discovered skills

examples:
  # Show source configuration and status
  claude-mpm skill-source show system

  # Show with full skill list
  claude-mpm skill-source show system --verbose

output includes:
  - Configuration (ID, URL, branch, priority, enabled)
  - Status (cache location, skills discovered, last sync)
  - Skills list (with --verbose)
```

**Rationale**: Clear explanation of what information is shown.

---

### 6. `skill-source remove` Help

**Suggested:**
```
usage: claude-mpm skill-source remove [-h] [--keep-cache] source_id

Remove a skill source repository.

positional arguments:
  source_id      ID of source to remove

options:
  -h, --help     show this help message and exit
  --keep-cache   Keep cached skills (only remove configuration)

examples:
  # Remove source and its cache
  claude-mpm skill-source remove custom

  # Remove configuration but keep cached skills
  claude-mpm skill-source remove custom --keep-cache

warning:
  Removing a source deletes its cached skills unless --keep-cache is used.
  Configuration can be re-added with 'skill-source add' command.
```

**Rationale**: Clarifies what gets deleted, provides safety option, explains recovery.

---

### 7. `skill-source enable/disable` Help

**Suggested:**
```
usage: claude-mpm skill-source enable [-h] source_id
usage: claude-mpm skill-source disable [-h] source_id

Enable or disable a skill source.

positional arguments:
  source_id   ID of source to enable/disable

options:
  -h, --help  show this help message and exit

examples:
  # Temporarily disable experimental skills
  claude-mpm skill-source disable experimental

  # Re-enable later
  claude-mpm skill-source enable experimental

notes:
  - Disabled sources are not synced during 'update' command
  - Configuration is preserved (not deleted)
  - Cache remains intact (can re-enable anytime)
  - Use 'remove' to completely delete a source
```

**Rationale**: Clarifies temporary vs. permanent removal, explains what persists.

---

## General Improvements Across All Commands

### 1. Consistent Examples Format

Use consistent formatting for examples:
```
examples:
  # Comment describing what example does
  claude-mpm skill-source <command> <args>
```

### 2. Add "Related Commands" Section

For complex workflows:
```
related commands:
  skill-source add      Add new source
  skill-source update   Sync sources
  doctor                Verify configuration
```

### 3. Add "See Also" References

```
see also:
  Documentation: docs/guides/skills-system.md
  API Reference: docs/reference/skills-api.md
  System Skills: https://github.com/bobmatnyc/claude-mpm-skills
```

---

## Implementation Priority

**High Priority:**
1. Add examples to `add`, `list`, `update` commands
2. Clarify priority system in `add` command
3. Add "what happens" section to `update` command

**Medium Priority:**
4. Add descriptions to all commands
5. Add "related commands" sections
6. Clarify enable/disable vs. remove

**Low Priority (Nice to Have):**
7. Add "see also" documentation links
8. Add verbose/quiet mode explanations
9. Add troubleshooting hints in error messages

---

## Example: Complete Improved Help Text

### `claude-mpm skill-source add`

```
usage: claude-mpm skill-source add [-h] [--branch BRANCH]
                                   [--priority PRIORITY] [--disabled]
                                   url

Add a new skill source repository.

Skill sources are Git repositories containing skill files (*.md with YAML
frontmatter). Multiple sources can be configured with priority-based conflict
resolution.

positional arguments:
  url                  Git repository URL
                       Format: https://github.com/owner/repo

options:
  -h, --help           show this help message and exit
  --branch BRANCH      Git branch to use (default: main)
  --priority PRIORITY  Priority for conflict resolution (default: 100)
                       Lower number = higher precedence (0 = highest)
                       Recommended range: 0-1000
  --disabled           Add repository but keep it disabled
                       Use 'skill-source enable <id>' to activate

examples:
  # Add with defaults (branch: main, priority: 100, enabled)
  claude-mpm skill-source add https://github.com/myorg/skills

  # Add with custom priority (higher precedence than default)
  claude-mpm skill-source add https://github.com/myorg/skills --priority 50

  # Add disabled (configure now, sync later)
  claude-mpm skill-source add https://github.com/myorg/skills --disabled

  # Add with specific branch
  claude-mpm skill-source add https://github.com/myorg/skills --branch develop

priority system:
  0         - System repository (highest precedence)
  1-99      - Critical organization-wide skills
  100-199   - Standard team skills (default: 100)
  200-999   - Experimental or optional skills
  1000+     - Not recommended (very low precedence)

related commands:
  skill-source list     View all configured sources
  skill-source update   Sync skills from sources
  skill-source enable   Enable disabled source
  doctor                Verify configuration

see also:
  User Guide: docs/guides/skills-system.md
  API Docs:   docs/reference/skills-api.md
```

---

## Testing Help Text

After implementing improvements, verify:

```bash
# Test all help commands
claude-mpm skill-source --help
claude-mpm skill-source add --help
claude-mpm skill-source list --help
claude-mpm skill-source update --help
claude-mpm skill-source show --help
claude-mpm skill-source remove --help
claude-mpm skill-source enable --help
claude-mpm skill-source disable --help

# Check for consistency
# - Examples format
# - Option descriptions
# - Usage patterns
```

---

## Summary

**Current State**: Help text is functional and covers essential information.

**Suggested Improvements**:
1. Add examples to all commands (highest value)
2. Clarify priority system ("lower = higher")
3. Explain what happens during operations
4. Add "related commands" and "see also" sections
5. Consistent formatting across commands

**Impact**:
- Reduces learning curve for new users
- Provides quick reference without checking docs
- Clarifies complex concepts (priority, caching)
- Improves discoverability of related features

**Recommendation**: Implement high-priority improvements first (examples, priority clarification, update explanation). Medium and low priority improvements can be added iteratively.
