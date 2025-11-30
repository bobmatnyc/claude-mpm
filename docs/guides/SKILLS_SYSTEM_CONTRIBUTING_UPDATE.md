# Suggested CONTRIBUTING.md Update for Skills System

## Add New Section: Contributing Skills

Add this section after the testing or code organization sections in CONTRIBUTING.md:

```markdown
## Contributing Skills

Skills extend Claude MPM's agent capabilities without modifying the core codebase. Skills are Markdown files with YAML frontmatter stored in Git repositories.

### Where to Add Skills

**System Skills** (for core functionality):
- Repository: https://github.com/bobmatnyc/claude-mpm-skills
- Process: Submit pull request to system repository
- Review: Requires maintainer approval
- Use Cases: General-purpose skills useful to all users

**User/Organization Skills** (for custom workflows):
- Repository: Your own Git repository
- Process: Create repository, add to Claude MPM via `skill-source add`
- Review: Your team's process
- Use Cases: Organization-specific standards, custom workflows

### Skill File Format

**Location**: `*.md` files in Git repository root or subdirectories

**Structure**:
```markdown
---
skill_id: my-skill-id
name: My Skill Name
description: Brief description (1-2 sentences)
version: "1.0.0"
tags:
  - category1
  - category2
agent_types:
  - research
  - code
author: Your Name
license: MIT
---

# Skill Content

Detailed instructions, workflows, and examples.

## Section 1
...
```

### Required Metadata Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `skill_id` | string | Yes | Unique identifier (kebab-case) |
| `name` | string | Yes | Human-readable name |
| `description` | string | Yes | Brief description (1-2 sentences) |
| `version` | string | Recommended | Semantic version (e.g., "1.0.0") |
| `tags` | list | Recommended | Categorization tags |
| `agent_types` | list | Optional | Which agents can use this |

### Testing Skills Locally

**Method 1: Direct Cache Placement**

```bash
# Place skill in cache for testing
mkdir -p ~/.claude-mpm/cache/skills/test/
cp my-skill.md ~/.claude-mpm/cache/skills/test/

# Verify discovery
claude-mpm doctor
```

**Method 2: Local Git Repository**

```bash
# Create local Git repository
mkdir my-skills
cd my-skills
git init
cp ../my-skill.md .
git add .
git commit -m "Add skill"

# Add to Claude MPM
claude-mpm skill-source add file:///full/path/to/my-skills --priority 100

# Sync
claude-mpm skill-source update
```

**Method 3: Unit Tests**

```python
import pytest
from pathlib import Path
from claude_mpm.services.skills.skill_discovery_service import SkillDiscoveryService

def test_my_skill():
    """Test skill discovery and validation."""
    temp_dir = Path("/tmp/test-skills")
    temp_dir.mkdir(exist_ok=True)

    skill_file = temp_dir / "my-skill.md"
    skill_file.write_text("""---
skill_id: test-skill
name: Test Skill
description: Test skill for validation
---

# Test Content
""")

    discovery = SkillDiscoveryService(temp_dir)
    skills = discovery.discover_skills()

    assert len(skills) == 1
    assert skills[0]['skill_id'] == 'test-skill'
    assert skills[0]['name'] == 'Test Skill'

    # Cleanup
    skill_file.unlink()
    temp_dir.rmdir()
```

### Skill Development Workflow

**1. Create Skill**
```bash
# Create skill file with YAML frontmatter
vim my-skill.md
```

**2. Validate Locally**
```bash
# Test YAML syntax
python -c "import yaml; yaml.safe_load(open('my-skill.md').read().split('---')[1])"

# Place in cache
cp my-skill.md ~/.claude-mpm/cache/skills/test/

# Run doctor
claude-mpm doctor
```

**3. Submit to Repository**
```bash
# For system skills (PR to bobmatnyc/claude-mpm-skills)
git clone https://github.com/bobmatnyc/claude-mpm-skills
cd claude-mpm-skills
cp ../my-skill.md .
git add my-skill.md
git commit -m "Add: my-skill - Brief description"
git push origin feature/my-skill

# Create PR on GitHub
```

**4. Documentation**
- Update skill repository README
- Add entry to CHANGELOG
- Include examples in skill content

### Skill Quality Standards

**Content Requirements:**
- Clear, concise descriptions
- Step-by-step workflows
- Concrete examples
- Troubleshooting section (if applicable)
- Cross-references to related skills

**Metadata Requirements:**
- Unique `skill_id` (no conflicts with existing skills)
- Semantic versioning
- Descriptive tags (3-5 recommended)
- Author attribution
- License specification (MIT recommended)

**Code Quality:**
- Valid YAML frontmatter
- No syntax errors in Markdown
- Tested with real workflows
- Links verified (no broken references)

### Review Process (System Skills)

**Submission Checklist:**
- [ ] YAML frontmatter valid
- [ ] Required fields present
- [ ] `skill_id` is unique
- [ ] Description clear and concise
- [ ] Content follows style guide
- [ ] Examples included
- [ ] Tested locally
- [ ] Documentation updated

**Review Criteria:**
- Skill is generally useful (not org-specific)
- Content is high-quality and well-structured
- Metadata is complete and accurate
- No conflicts with existing skills
- Tests pass (if applicable)

**Approval:**
- Requires approval from 1+ maintainers
- May request changes or improvements
- Merged into main branch once approved
- Released in next sync cycle

### Versioning Skills

Use **Semantic Versioning** for skills:

```yaml
version: "1.0.0"  # Initial release
version: "1.1.0"  # Added new section (backward compatible)
version: "1.1.1"  # Fixed typo/bug (patch)
version: "2.0.0"  # Changed structure (breaking change)
```

**When to Bump:**
- **Major (X.0.0)**: Breaking changes to skill structure
- **Minor (1.X.0)**: New sections/features (backward compatible)
- **Patch (1.1.X)**: Fixes, clarifications, typos

### Best Practices

**DO:**
- ✅ Use kebab-case for `skill_id`
- ✅ Keep descriptions under 2 sentences
- ✅ Include 3-5 relevant tags
- ✅ Version your skills (semantic versioning)
- ✅ Test before submitting
- ✅ Document breaking changes

**DON'T:**
- ❌ Use generic skill IDs ("review", "test")
- ❌ Include organization-specific content in system skills
- ❌ Hardcode paths or credentials
- ❌ Skip required metadata fields
- ❌ Submit untested skills
- ❌ Break backward compatibility without version bump

### Examples

See the [Skills System User Guide](docs/guides/skills-system.md#examples) for complete examples of creating and distributing skills.

### Related Documentation

- **[Skills System User Guide](docs/guides/skills-system.md)** - Complete user guide
- **[Skills API Reference](docs/reference/skills-api.md)** - Technical API docs
- **[System Skills Repository](https://github.com/bobmatnyc/claude-mpm-skills)** - Browse existing skills
```

## Location in CONTRIBUTING.md

**Suggested Placement**: After "Testing Requirements" section or before "Release Process" section.

**Alternative**: Create a dedicated "docs/developer/contributing-skills.md" file and link to it from CONTRIBUTING.md:

```markdown
## Contributing Skills

Skills extend agent capabilities without code changes. See [Contributing Skills Guide](docs/developer/contributing-skills.md) for details on:
- Creating skill files
- Testing locally
- Submitting to system repository
- Quality standards
```

---

**Note**: Choose the approach that best fits your CONTRIBUTING.md structure. The inline approach provides all information in one place, while the linked approach keeps CONTRIBUTING.md concise.
