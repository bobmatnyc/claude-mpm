# Skills Management UI Analysis - Pattern-Based Grouping

**Date:** 2026-01-02
**Objective:** Understand current skills display/grouping implementation to add pattern detection for related skills (e.g., `digitalocean-*`)

---

## Executive Summary

The skills management UI currently groups skills **by category** (universal, python, typescript, etc.) using a two-tier selection interface. To add pattern-based grouping (e.g., grouping all `digitalocean-*` skills together), we need to:

1. **Enhance grouping logic** in `/Users/masa/Projects/claude-mpm/src/claude_mpm/cli/commands/configure.py` (method `_manage_skill_installation`)
2. **Detect skill name patterns** (e.g., `digitalocean-*`, `aws-*`, `github-*`)
3. **Create visual hierarchy** showing both category and pattern-based groups

---

## Current Implementation

### 1. Skills Display Entry Points

**Primary UI:** `/Users/masa/Projects/claude-mpm/src/claude_mpm/cli/commands/configure.py`
- Method: `_manage_skills()` (lines 658-805)
- Method: `_manage_skill_installation()` (lines 808-975)

**Interactive Selector:** `/Users/masa/Projects/claude-mpm/src/claude_mpm/cli/interactive/skill_selector.py`
- Class: `SkillSelector`
- Method: `select_skills()` (lines 238-279)
- Method: `_select_topic_groups()` (lines 288-317)

**Skills Command:** `/Users/masa/Projects/claude-mpm/src/claude_mpm/cli/commands/skills.py`
- Class: `SkillsManagementCommand`
- Method: `_list_skills()` (lines 121-197)
- Method: `_configure_skills()` (lines 1029-1282)

### 2. Current Grouping Mechanism

**Grouping Strategy:** Category-based (from recent commit `dd7cffb1`)

```python
# Location: configure.py lines 825-846
grouped = {}
for skill in all_skills:
    # Try to get category from tags or use toolchain
    category = None
    tags = skill.get("tags", [])

    # Look for category tag
    for tag in tags:
        if tag in ["universal", "python", "typescript", "javascript", "go", "rust"]:
            category = tag
            break

    # Fallback to toolchain or universal
    if not category:
        category = skill.get("toolchain", "universal")

    if category not in grouped:
        grouped[category] = []
    grouped[category].append(skill)
```

**Current Categories:**
- 🌐 Universal
- 🐍 Python
- 📘 TypeScript
- 📒 JavaScript
- 🔷 Go
- ⚙️ Rust

### 3. Skill Data Structure

**Source:** Skills manifest JSON (loaded from cache or GitHub)

**Key Fields:**
```python
{
    "name": "digitalocean-droplets",           # Skill ID (unique identifier)
    "skill_id": "digitalocean-droplets",       # Alternative identifier
    "deployment_name": "digitalocean-droplets", # Name when deployed
    "description": "Manage DigitalOcean droplets",
    "category": "infrastructure",              # Category for grouping
    "toolchain": ["universal"],                # Toolchain(s)
    "tags": ["cloud", "infrastructure"],       # Additional metadata
    "full_tokens": 15000,                      # Token count
    "framework": null,                         # Framework (optional)
}
```

**Manifest Structure:**
```json
{
  "skills": {
    "universal": [...],
    "toolchains": {
      "python": [...],
      "typescript": [...]
    }
  }
}
```

### 4. Current Selection Flow

**Two-Tier Selection (skill_selector.py):**

1. **Tier 1:** Select topic groups (toolchains)
   - User chooses categories to explore
   - Method: `_select_topic_groups()` (lines 288-317)

2. **Tier 2:** Multi-select skills within group
   - Checkbox selection with spacebar toggle
   - Pre-checks installed skills
   - Method: `_select_skills_from_group()` (lines 319-365)

**Category-Based Selection (configure.py):**

1. **Category Selection:** User picks a category
   - Uses questionary.select()
   - Shows skill count per category

2. **Skill Selection:** Checkbox within category
   - Uses questionary.checkbox()
   - Shows installation status
   - Spacebar toggle, Enter to confirm

---

## Pattern Detection Strategy

### Proposed Enhancement

Add **pattern-based sub-grouping** within categories to group related skills:

**Pattern Examples:**
- `digitalocean-*` → DigitalOcean skills
- `aws-*` → AWS skills
- `github-*` → GitHub skills
- `universal-testing-*` → Testing skills
- `universal-debugging-*` → Debugging skills
- `toolchains-python-*` → Python toolchain skills

### Implementation Approach

**Option 1: Hierarchical Grouping (Category → Pattern)**

```
🌐 Universal (45 skills)
  ├─ 🧪 Testing (universal-testing-*)
  │   ├─ universal-testing-test-driven-development
  │   └─ universal-testing-testing-anti-patterns
  ├─ 🐛 Debugging (universal-debugging-*)
  │   ├─ universal-debugging-systematic-debugging
  │   └─ universal-debugging-verification-before-completion
  └─ Other (ungrouped)
      └─ universal-data-xlsx

📘 TypeScript (20 skills)
  └─ All TypeScript skills...
```

**Option 2: Pattern-First Grouping**

```
🌊 DigitalOcean (digitalocean-*)
  ├─ digitalocean-droplets
  ├─ digitalocean-spaces
  └─ digitalocean-networking

☁️ AWS (aws-*)
  ├─ aws-ec2
  └─ aws-s3

🐍 Python Toolchain (toolchains-python-*)
  ├─ toolchains-python-core
  └─ toolchains-python-testing-pytest
```

### Code Locations to Modify

**Primary Target:** `/Users/masa/Projects/claude-mpm/src/claude_mpm/cli/commands/configure.py`
- Method: `_manage_skill_installation()` (lines 808-975)
- Add pattern detection logic after category grouping
- Enhance display to show pattern-based sub-groups

**Pattern Detection Function (new):**
```python
def _detect_skill_patterns(skills: list) -> dict:
    """Group skills by naming patterns.

    Returns:
        Dict mapping pattern prefixes to skill lists
        Example: {"digitalocean": [...], "aws": [...]}
    """
    patterns = {}
    for skill in skills:
        skill_name = skill.get("name", "")

        # Extract pattern prefix (before first "-")
        parts = skill_name.split("-")
        if len(parts) >= 2:
            # Check for compound prefixes (e.g., "universal-testing")
            prefix = parts[0]
            if len(parts) >= 3 and parts[0] in ["universal", "toolchains"]:
                prefix = f"{parts[0]}-{parts[1]}"

            if prefix not in patterns:
                patterns[prefix] = []
            patterns[prefix].append(skill)

    return patterns
```

**Pattern Icons (new):**
```python
PATTERN_ICONS = {
    "digitalocean": "🌊",
    "aws": "☁️",
    "github": "🐙",
    "universal-testing": "🧪",
    "universal-debugging": "🐛",
    "universal-verification": "✅",
    "toolchains-python": "🐍",
    "toolchains-typescript": "📘",
}
```

---

## Recommended Implementation Plan

### Phase 1: Pattern Detection (Low Risk)

1. **Add pattern detection logic** to `_manage_skill_installation()`
   - Extract common prefixes from skill names
   - Detect multi-segment patterns (e.g., `universal-testing-*`)
   - Group skills with 2+ matches under pattern

2. **Enhance display** to show pattern groups
   - Add visual hierarchy (indentation or sub-headers)
   - Use icons for common patterns
   - Fall back to ungrouped skills

### Phase 2: Pattern Configuration (Medium Risk)

1. **Define pattern rules** in configuration
   - Allow users to customize grouping patterns
   - Support regex-based patterns
   - Priority order for overlapping patterns

2. **Add pattern management UI**
   - View current pattern groups
   - Enable/disable patterns
   - Add custom patterns

### Phase 3: Advanced Grouping (High Value)

1. **Multi-dimensional grouping**
   - Category × Pattern matrix view
   - Filter by both category and pattern
   - Search/filter across all dimensions

2. **Smart recommendations**
   - Suggest related skills based on patterns
   - Auto-select pattern groups
   - Show dependency chains

---

## Related Files

### Core Implementation Files
- `/Users/masa/Projects/claude-mpm/src/claude_mpm/cli/commands/configure.py` - Skills management UI
- `/Users/masa/Projects/claude-mpm/src/claude_mpm/cli/interactive/skill_selector.py` - Interactive selector
- `/Users/masa/Projects/claude-mpm/src/claude_mpm/cli/commands/skills.py` - Skills command

### Supporting Services
- `/Users/masa/Projects/claude-mpm/src/claude_mpm/services/skills_deployer.py` - Skill deployment
- `/Users/masa/Projects/claude-mpm/src/claude_mpm/services/skills/selective_skill_deployer.py` - Selective deployment
- `/Users/masa/Projects/claude-mpm/src/claude_mpm/skills/skill_manager.py` - Skill manager

### Data Structures
- `/Users/masa/Projects/claude-mpm/src/claude_mpm/cli/interactive/skill_selector.py` lines 51-67 - `SkillInfo` dataclass

---

## Key Insights

### Strengths of Current System
✅ Clean two-tier selection (category → skills)
✅ Checkbox selection with spacebar toggle
✅ Shows installation status in real-time
✅ Processes install/uninstall in single transaction
✅ Consistent with agent selection UX

### Opportunities for Pattern Grouping
🎯 Reduce cognitive load when browsing 45+ universal skills
🎯 Make related skills discoverable (all DigitalOcean skills together)
🎯 Enable bulk operations on pattern groups
🎯 Support vendor/ecosystem-specific skill sets

### Technical Considerations
⚠️ Pattern detection should be fast (no significant UI lag)
⚠️ Avoid over-grouping (patterns need 2+ skills to be useful)
⚠️ Maintain backward compatibility with category-only grouping
⚠️ Consider pattern naming conflicts (e.g., `aws` vs `aws-cdk`)

---

## Example Pattern Detection Output

**Input Skills:**
```
digitalocean-droplets
digitalocean-spaces
digitalocean-networking
aws-ec2
aws-s3
universal-testing-test-driven-development
universal-testing-testing-anti-patterns
universal-debugging-systematic-debugging
random-skill
```

**Detected Patterns:**
```python
{
    "digitalocean": [
        {"name": "digitalocean-droplets", ...},
        {"name": "digitalocean-spaces", ...},
        {"name": "digitalocean-networking", ...}
    ],
    "aws": [
        {"name": "aws-ec2", ...},
        {"name": "aws-s3", ...}
    ],
    "universal-testing": [
        {"name": "universal-testing-test-driven-development", ...},
        {"name": "universal-testing-testing-anti-patterns", ...}
    ],
    "_ungrouped": [
        {"name": "universal-debugging-systematic-debugging", ...},
        {"name": "random-skill", ...}
    ]
}
```

**Display:**
```
🌐 Universal (8 skills)

  🧪 Testing (2 skills)
    □ universal-testing-test-driven-development
    □ universal-testing-testing-anti-patterns

  Other (2 skills)
    □ universal-debugging-systematic-debugging
    □ random-skill

🌊 DigitalOcean (3 skills)
  □ digitalocean-droplets - Manage DigitalOcean droplets
  □ digitalocean-spaces - S3-compatible object storage
  □ digitalocean-networking - VPC and networking

☁️ AWS (2 skills)
  □ aws-ec2 - EC2 instance management
  □ aws-s3 - S3 bucket operations
```

---

## Next Steps

1. **Prototype pattern detection** in `configure.py`
   - Add `_detect_skill_patterns()` method
   - Test with existing skill names
   - Verify performance with 100+ skills

2. **Update display logic** to show patterns
   - Add visual hierarchy (indentation or sections)
   - Include pattern icons
   - Show skill counts per pattern

3. **Test with real data**
   - Load skills from GitHub manifest
   - Verify grouping makes sense
   - Gather user feedback on UX

4. **Iterate on grouping rules**
   - Adjust pattern detection thresholds
   - Add configuration for custom patterns
   - Handle edge cases (single-skill patterns, overlaps)

---

## Conclusion

The skills management UI is well-structured with clean separation between:
- **Data loading** (skills_deployer.py)
- **Selection UI** (configure.py, skill_selector.py)
- **Deployment logic** (selective_skill_deployer.py)

Adding pattern-based grouping is straightforward:
1. Detect patterns from skill names
2. Group skills by detected patterns
3. Enhance display with hierarchical structure

This will significantly improve UX when browsing large skill sets (45+ universal skills → organized into 5-7 pattern groups).
