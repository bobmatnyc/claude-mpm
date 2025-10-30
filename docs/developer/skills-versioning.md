# Skills Versioning - Developer Guide

Technical documentation for the skills versioning system implementation.

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Skill Dataclass](#skill-dataclass)
- [Frontmatter Parsing](#frontmatter-parsing)
- [SkillRegistry Implementation](#skillregistry-implementation)
- [VersionService Integration](#versionservice-integration)
- [Backward Compatibility](#backward-compatibility)
- [Testing Strategies](#testing-strategies)
- [Contributing Versioned Skills](#contributing-versioned-skills)
- [Migration Guide](#migration-guide)

## Architecture Overview

### Design Principles

1. **Backward Compatibility**: Skills without frontmatter continue to work
2. **Opt-in Versioning**: Frontmatter is optional
3. **Semantic Versioning**: Standard SemVer format (MAJOR.MINOR.PATCH)
4. **Minimal Overhead**: Parsing only when loading skills
5. **Fail-Safe**: Parsing errors don't break skill loading

### Components

```
┌─────────────────────────────────────────────────────┐
│                 Skills System                        │
├─────────────────────────────────────────────────────┤
│                                                      │
│  ┌────────────────┐         ┌──────────────────┐   │
│  │ SkillRegistry  │────────▶│  Skill Dataclass │   │
│  │                │         │  - skill_id      │   │
│  │ - load_skills()│         │  - skill_version │   │
│  │ - parse_front()│         │  - updated_at    │   │
│  └────────────────┘         │  - tags          │   │
│         │                   └──────────────────┘   │
│         │                                           │
│         ▼                                           │
│  ┌────────────────┐         ┌──────────────────┐   │
│  │ Frontmatter    │────────▶│ VersionService   │   │
│  │ Parser         │         │                  │   │
│  │                │         │ - get_skills_    │   │
│  │ - YAML parsing │         │   versions()     │   │
│  │ - Validation   │         │ - get_version_   │   │
│  └────────────────┘         │   summary()      │   │
│                              └──────────────────┘   │
└─────────────────────────────────────────────────────┘
```

### Data Flow

```
1. Skill File (.md)
   │
   ├─ Has frontmatter? ──YES──▶ Parse YAML
   │                             │
   └─ NO ─────────────────────▶  │
                                 ▼
2. Skill Object Creation
   │
   ├─ skill_id: from frontmatter or filename
   ├─ skill_version: from frontmatter or "unknown"
   ├─ updated_at: from frontmatter or None
   └─ tags: from frontmatter or []
   │
   ▼
3. SkillRegistry Storage
   │
   ├─ Indexed by skill_id
   └─ Available for lookup
   │
   ▼
4. VersionService Query
   │
   ├─ Group by source (bundled/user/project)
   ├─ Sort alphabetically
   └─ Return with counts
```

## Skill Dataclass

### Definition

**File:** `src/claude_mpm/models/skill.py`

```python
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class Skill:
    """Represents a skill with metadata and content."""

    # Core fields
    skill_id: str
    name: str
    content: str
    file_path: str

    # Versioning fields (NEW)
    skill_version: str = "unknown"
    updated_at: Optional[str] = None
    tags: List[str] = None

    def __post_init__(self):
        """Initialize default values for mutable fields."""
        if self.tags is None:
            self.tags = []
```

### Field Descriptions

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `skill_id` | `str` | Yes | - | Unique identifier (kebab-case) |
| `name` | `str` | Yes | - | Display name |
| `content` | `str` | Yes | - | Skill markdown content |
| `file_path` | `str` | Yes | - | Path to skill file |
| `skill_version` | `str` | No | `"unknown"` | Semantic version |
| `updated_at` | `Optional[str]` | No | `None` | Last update date |
| `tags` | `List[str]` | No | `[]` | Categorization tags |

### Design Decisions

**Why `skill_version` defaults to "unknown"?**
- Clear indicator of unversioned skills
- Distinguishes from "0.0.0" or "null"
- Allows filtering/reporting on unversioned skills

**Why Optional fields?**
- Backward compatibility with existing skills
- Opt-in versioning system
- Graceful degradation

**Why tags are List[str]?**
- Simple, extensible structure
- Easy to add/remove tags
- Standard Python collection

## Frontmatter Parsing

### YAML Frontmatter Format

Skills use YAML frontmatter delimited by `---`:

```markdown
---
skill_id: example-skill
skill_version: 1.0.0
updated_at: 2025-10-30
tags:
  - category1
  - category2
---

# Skill Content

Markdown content starts here...
```

### Parsing Implementation

**File:** `src/claude_mpm/services/skill_registry.py`

```python
import re
import yaml
from typing import Dict, Any, Optional

def _parse_frontmatter(self, content: str) -> tuple[Optional[Dict[str, Any]], str]:
    """
    Parse YAML frontmatter from skill content.

    Args:
        content: Raw skill file content

    Returns:
        Tuple of (frontmatter_dict, content_without_frontmatter)
        Returns (None, content) if no frontmatter found
    """
    # Regex pattern for frontmatter: ---\n...\n---
    pattern = r'^---\s*\n(.*?)\n---\s*\n(.*)$'
    match = re.match(pattern, content, re.DOTALL)

    if not match:
        # No frontmatter found
        return None, content

    try:
        # Parse YAML from first capture group
        frontmatter_yaml = match.group(1)
        frontmatter = yaml.safe_load(frontmatter_yaml)

        # Content without frontmatter
        content_without_frontmatter = match.group(2)

        return frontmatter, content_without_frontmatter

    except yaml.YAMLError as e:
        # Log error but don't fail
        self.logger.warning(f"Failed to parse frontmatter: {e}")
        return None, content
```

### Error Handling

**Principle:** Parse errors should never break skill loading.

```python
# Graceful degradation
try:
    frontmatter, content = self._parse_frontmatter(raw_content)
except Exception as e:
    self.logger.warning(f"Frontmatter parsing failed: {e}")
    frontmatter = None
    content = raw_content

# Use defaults for missing frontmatter
skill_version = frontmatter.get("skill_version", "unknown") if frontmatter else "unknown"
updated_at = frontmatter.get("updated_at") if frontmatter else None
tags = frontmatter.get("tags", []) if frontmatter else []
```

### Validation

```python
def _validate_frontmatter(self, frontmatter: Dict[str, Any]) -> bool:
    """
    Validate frontmatter structure.

    Required fields:
    - skill_id: str
    - skill_version: str (semantic version format)

    Optional fields:
    - updated_at: str (YYYY-MM-DD format)
    - tags: list[str]
    """
    if not isinstance(frontmatter, dict):
        return False

    # Check required fields
    if "skill_id" not in frontmatter:
        self.logger.warning("Missing required field: skill_id")
        return False

    if "skill_version" not in frontmatter:
        self.logger.warning("Missing required field: skill_version")
        return False

    # Validate version format (basic check)
    version = frontmatter["skill_version"]
    if not re.match(r'^\d+\.\d+\.\d+$', version):
        self.logger.warning(f"Invalid version format: {version}")
        return False

    # Validate optional fields
    if "updated_at" in frontmatter:
        date_str = frontmatter["updated_at"]
        if not re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
            self.logger.warning(f"Invalid date format: {date_str}")

    if "tags" in frontmatter:
        if not isinstance(frontmatter["tags"], list):
            self.logger.warning("tags must be a list")
            return False

    return True
```

## SkillRegistry Implementation

### Loading Skills with Versions

**File:** `src/claude_mpm/services/skill_registry.py`

```python
def load_skills(self) -> None:
    """Load all skills from bundled, user, and project directories."""

    # Load from each source
    for source_dir, source_type in [
        (self.bundled_skills_dir, "bundled"),
        (self.user_skills_dir, "user"),
        (self.project_skills_dir, "project")
    ]:
        if not source_dir.exists():
            continue

        for skill_file in source_dir.glob("*.md"):
            try:
                # Read file content
                with open(skill_file, 'r', encoding='utf-8') as f:
                    raw_content = f.read()

                # Parse frontmatter
                frontmatter, content = self._parse_frontmatter(raw_content)

                # Extract metadata
                if frontmatter and self._validate_frontmatter(frontmatter):
                    skill_id = frontmatter["skill_id"]
                    skill_version = frontmatter["skill_version"]
                    updated_at = frontmatter.get("updated_at")
                    tags = frontmatter.get("tags", [])
                else:
                    # Fallback to defaults
                    skill_id = skill_file.stem  # filename without extension
                    skill_version = "unknown"
                    updated_at = None
                    tags = []

                # Create skill object
                skill = Skill(
                    skill_id=skill_id,
                    name=skill_id.replace("-", " ").title(),
                    content=content,
                    file_path=str(skill_file),
                    skill_version=skill_version,
                    updated_at=updated_at,
                    tags=tags
                )

                # Register skill
                self._skills[skill_id] = skill

                # Log at DEBUG level (not INFO)
                self.logger.debug(
                    f"Loaded skill: {skill_id} v{skill_version} "
                    f"from {source_type}"
                )

            except Exception as e:
                self.logger.error(f"Failed to load skill {skill_file}: {e}")
                continue
```

### Key Implementation Details

1. **Three-source loading**: bundled → user → project (priority order)
2. **Debug-level logging**: Reduced console noise
3. **Graceful failure**: Individual skill errors don't stop loading
4. **Validation**: Optional but recommended
5. **Defaults**: Always provide fallback values

## VersionService Integration

### New Methods

**File:** `src/claude_mpm/services/version_service.py`

```python
from typing import Dict, List
from dataclasses import dataclass

@dataclass
class AgentsVersions:
    """Grouped agent versions by tier."""
    system: List[tuple[str, str]]  # [(name, version), ...]
    user: List[tuple[str, str]]
    project: List[tuple[str, str]]
    counts: Dict[str, int]  # {"system": 30, "user": 3, "project": 2}

@dataclass
class SkillsVersions:
    """Grouped skill versions by source."""
    bundled: List[tuple[str, str]]  # [(skill_id, version), ...]
    user: List[tuple[str, str]]
    project: List[tuple[str, str]]
    counts: Dict[str, int]  # {"bundled": 20, "user": 2, "project": 1}

class VersionService:
    """Service for managing version information."""

    def get_agents_versions(self) -> AgentsVersions:
        """
        Get all agent versions grouped by tier.

        Returns:
            AgentsVersions with system/user/project lists
        """
        system_agents = []
        user_agents = []
        project_agents = []

        for agent_id, agent in self.agent_registry.get_all_agents().items():
            tier = agent.tier or "system"
            version = agent.agent_version or "unknown"

            if tier == "system":
                system_agents.append((agent_id, version))
            elif tier == "user":
                user_agents.append((agent_id, version))
            else:
                project_agents.append((agent_id, version))

        # Sort alphabetically
        system_agents.sort()
        user_agents.sort()
        project_agents.sort()

        return AgentsVersions(
            system=system_agents,
            user=user_agents,
            project=project_agents,
            counts={
                "system": len(system_agents),
                "user": len(user_agents),
                "project": len(project_agents)
            }
        )

    def get_skills_versions(self) -> SkillsVersions:
        """
        Get all skill versions grouped by source.

        Returns:
            SkillsVersions with bundled/user/project lists
        """
        bundled_skills = []
        user_skills = []
        project_skills = []

        for skill_id, skill in self.skill_registry.get_all_skills().items():
            version = skill.skill_version or "unknown"

            # Determine source from file path
            if "bundled" in skill.file_path:
                bundled_skills.append((skill_id, version))
            elif ".claude/skills" in skill.file_path:
                project_skills.append((skill_id, version))
            else:
                user_skills.append((skill_id, version))

        # Sort alphabetically
        bundled_skills.sort()
        user_skills.sort()
        project_skills.sort()

        return SkillsVersions(
            bundled=bundled_skills,
            user=user_skills,
            project=project_skills,
            counts={
                "bundled": len(bundled_skills),
                "user": len(user_skills),
                "project": len(project_skills)
            }
        )

    def get_version_summary(self) -> Dict[str, Any]:
        """
        Get complete version summary.

        Returns:
            Dictionary with project, agents, and skills version info
        """
        return {
            "project": {
                "version": self.get_project_version(),
                "build": self.get_build_number()
            },
            "agents": self.get_agents_versions(),
            "skills": self.get_skills_versions()
        }
```

### Usage Example

```python
from claude_mpm.services.version_service import VersionService

# Initialize service
service = VersionService()

# Get complete summary
summary = service.get_version_summary()

print(f"Project: {summary['project']['version']}")
print(f"Build: {summary['project']['build']}")
print(f"Total agents: {sum(summary['agents'].counts.values())}")
print(f"Total skills: {sum(summary['skills'].counts.values())}")

# Get skills only
skills = service.get_skills_versions()
print(f"Bundled skills: {skills.counts['bundled']}")
for skill_id, version in skills.bundled:
    print(f"  - {skill_id}: {version}")
```

## Backward Compatibility

### Design Requirements

1. **Existing skills must work** without modification
2. **No breaking changes** to Skill dataclass
3. **Optional frontmatter** - not enforced
4. **Graceful defaults** - "unknown" version if missing
5. **No performance impact** for legacy skills

### Compatibility Matrix

| Skill Format | skill_id | skill_version | Tags | Status |
|--------------|----------|---------------|------|--------|
| With frontmatter | From YAML | From YAML | From YAML | ✅ Full support |
| Without frontmatter | From filename | "unknown" | [] | ✅ Full support |
| Invalid YAML | From filename | "unknown" | [] | ✅ Fallback |
| Partial frontmatter | From YAML/filename | From YAML/"unknown" | From YAML/[] | ✅ Hybrid |

### Migration Strategy

**Phase 1: Add versioning (non-breaking)**
- Add version fields to Skill dataclass with defaults
- Implement frontmatter parsing
- Skills without frontmatter continue to work

**Phase 2: Version bundled skills**
- Add frontmatter to all bundled skills
- Start at 0.1.0 for all
- Document versioning guidelines

**Phase 3: Encourage user adoption**
- Document versioning in user guide
- Show examples in documentation
- Make version info visible in `/mpm-version`

**Phase 4: Optional enforcement**
- Add config option for version requirement
- Warn on unversioned skills (optional)
- Never break loading

## Testing Strategies

### Unit Tests

**Test frontmatter parsing:**

```python
def test_parse_frontmatter_valid():
    """Test parsing valid frontmatter."""
    content = """---
skill_id: test-skill
skill_version: 1.0.0
updated_at: 2025-10-30
tags:
  - testing
  - example
---

# Test Skill

Content here.
"""
    registry = SkillRegistry()
    frontmatter, body = registry._parse_frontmatter(content)

    assert frontmatter is not None
    assert frontmatter["skill_id"] == "test-skill"
    assert frontmatter["skill_version"] == "1.0.0"
    assert frontmatter["updated_at"] == "2025-10-30"
    assert frontmatter["tags"] == ["testing", "example"]
    assert "# Test Skill" in body

def test_parse_frontmatter_missing():
    """Test handling missing frontmatter."""
    content = "# Test Skill\n\nNo frontmatter here."

    registry = SkillRegistry()
    frontmatter, body = registry._parse_frontmatter(content)

    assert frontmatter is None
    assert body == content

def test_parse_frontmatter_invalid_yaml():
    """Test handling invalid YAML."""
    content = """---
skill_id: test-skill
invalid: yaml: syntax:
---

# Test Skill
"""
    registry = SkillRegistry()
    frontmatter, body = registry._parse_frontmatter(content)

    # Should fall back gracefully
    assert frontmatter is None
```

**Test VersionService methods:**

```python
def test_get_skills_versions(version_service, skill_registry):
    """Test getting skills versions."""
    # Create test skills
    skill1 = Skill(
        skill_id="test-skill-1",
        name="Test Skill 1",
        content="Test content",
        file_path="/bundled/test-skill-1.md",
        skill_version="1.0.0"
    )
    skill2 = Skill(
        skill_id="test-skill-2",
        name="Test Skill 2",
        content="Test content",
        file_path="/user/test-skill-2.md",
        skill_version="0.5.0"
    )

    skill_registry._skills = {
        "test-skill-1": skill1,
        "test-skill-2": skill2
    }

    result = version_service.get_skills_versions()

    assert result.counts["bundled"] == 1
    assert result.counts["user"] == 1
    assert result.counts["project"] == 0
    assert ("test-skill-1", "1.0.0") in result.bundled
    assert ("test-skill-2", "0.5.0") in result.user
```

### Integration Tests

```python
def test_load_versioned_skills(tmp_path):
    """Test loading skills with frontmatter."""
    # Create test skill file
    skill_file = tmp_path / "test-skill.md"
    skill_file.write_text("""---
skill_id: integration-test
skill_version: 2.1.0
updated_at: 2025-10-30
tags:
  - integration
  - testing
---

# Integration Test Skill

Test content.
""")

    # Load skills
    registry = SkillRegistry(bundled_skills_dir=tmp_path)
    registry.load_skills()

    # Verify
    skill = registry.get_skill("integration-test")
    assert skill is not None
    assert skill.skill_version == "2.1.0"
    assert skill.updated_at == "2025-10-30"
    assert "integration" in skill.tags
```

### Test Coverage Goals

- ✅ Frontmatter parsing: 100%
- ✅ Version extraction: 100%
- ✅ Backward compatibility: 100%
- ✅ Error handling: 100%
- ✅ VersionService methods: 100%

## Contributing Versioned Skills

### Checklist for New Skills

- [ ] Add YAML frontmatter with all required fields
- [ ] Start with version `0.1.0`
- [ ] Use kebab-case for `skill_id`
- [ ] Add descriptive tags (3-5 recommended)
- [ ] Include `updated_at` field
- [ ] Test parsing with SkillRegistry
- [ ] Verify loading with `/mpm-version`
- [ ] Document version in skill content
- [ ] Add to appropriate directory (bundled/user/project)

### Pull Request Template

```markdown
## Skill Version Information

- **Skill ID**: `my-new-skill`
- **Version**: `0.1.0`
- **Tags**: `[category1, category2, category3]`
- **Location**: `src/claude_mpm/skills/bundled/my-new-skill.md`

## Changes

- [ ] Added YAML frontmatter with version info
- [ ] Validated frontmatter parsing
- [ ] Tested skill loading
- [ ] Updated skills count if needed
- [ ] Added/updated tests

## Testing

\```bash
# Test skill loading
python -m pytest tests/services/test_skill_registry.py -k my_new_skill

# Verify version display
/mpm-version
\```

## Documentation

- [ ] Skill content includes usage examples
- [ ] Version history documented (if updating)
- [ ] Tags are descriptive and relevant
```

## Migration Guide

### Migrating Existing Skills

**Step 1: Backup existing skills**

```bash
cp -r .claude/skills .claude/skills.backup
```

**Step 2: Add frontmatter to each skill**

```bash
# Edit skill file
vim .claude/skills/my-skill.md
```

Add frontmatter at the top:

```markdown
---
skill_id: my-skill
skill_version: 0.1.0
updated_at: 2025-10-30
tags:
  - relevant
  - tags
---

# Existing Skill Content

... rest of skill ...
```

**Step 3: Validate parsing**

```python
from claude_mpm.services.skill_registry import SkillRegistry

registry = SkillRegistry()
registry.load_skills()

skill = registry.get_skill("my-skill")
print(f"Version: {skill.skill_version}")
print(f"Tags: {skill.tags}")
```

**Step 4: Verify with /mpm-version**

```bash
/mpm-version
```

Check that your skill appears with correct version.

### Bulk Migration Script

```python
#!/usr/bin/env python3
"""
Migrate existing skills to versioned format.
"""

import re
from pathlib import Path
from datetime import date

def add_frontmatter(skill_file: Path) -> None:
    """Add frontmatter to skill file."""

    content = skill_file.read_text()

    # Skip if frontmatter already exists
    if content.startswith("---"):
        print(f"Skipping {skill_file.name} (already has frontmatter)")
        return

    # Generate skill_id from filename
    skill_id = skill_file.stem

    # Create frontmatter
    frontmatter = f"""---
skill_id: {skill_id}
skill_version: 0.1.0
updated_at: {date.today().isoformat()}
tags:
  - TODO
---

"""

    # Write updated content
    new_content = frontmatter + content
    skill_file.write_text(new_content)

    print(f"✓ Added frontmatter to {skill_file.name}")

def main():
    """Migrate all skills in directory."""
    skills_dir = Path(".claude/skills")

    for skill_file in skills_dir.glob("*.md"):
        try:
            add_frontmatter(skill_file)
        except Exception as e:
            print(f"✗ Failed to migrate {skill_file.name}: {e}")

if __name__ == "__main__":
    main()
```

Run the script:

```bash
python migrate_skills.py
```

Then edit each file to add proper tags.

## Related Documentation

- **[User Guide](../user/skills-versioning.md)** - User-facing documentation
- **[Architecture](ARCHITECTURE.md)** - System architecture overview
- **[API Reference](api-reference.md)** - Complete API documentation
- **[Extending](extending.md)** - Extension development guide

---

**Next Steps:**
1. Review existing skills for migration
2. Add tests for versioning features
3. Update contributing guidelines
4. Monitor adoption and gather feedback
