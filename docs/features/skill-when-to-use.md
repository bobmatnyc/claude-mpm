# Skill `when_to_use` Field

## Overview

Claude MPM v6.3.2 extracts and exposes the `when_to_use` field from skill definitions, making guidance text available programmatically. This enables enhanced skill routing decisions, better recommendations, and context-aware skill suggestions.

## What Is `when_to_use`?

The `when_to_use` field in a skill's SKILL.md frontmatter provides guidance on **when this skill is most valuable**:

```markdown
---
name: test-driven-development
description: "TDD patterns and practices for all programming languages"
version: 1.0.0
when_to_use: "Apply TDD for new feature implementation, bug fixes, refactoring, API development, and complex business logic"
---

# Test-Driven Development (TDD)

[Skill content...]
```

### Purpose

The `when_to_use` field serves multiple purposes:

1. **User guidance**: When should developers use this skill?
2. **Routing decisions**: Which skills match the current context?
3. **Skill recommendations**: Which skills are relevant for this project/task?
4. **Agent recommendations**: Which skills should be available to this agent?

## Skill Dataclass

The `Skill` dataclass now includes a `when_to_use` field:

### Definition

```python
from dataclasses import dataclass

@dataclass
class Skill:
    """Skill definition with metadata"""
    
    name: str
    description: str
    version: str
    repository: str
    category: str
    
    # New in v6.3.2
    when_to_use: str  # Guidance on when to apply this skill
    
    # Existing fields
    tags: list[str] = None
    dependencies: list[str] = None
    authors: list[str] = None
    created_at: str = None
    updated_at: str = None
```

### Example Usage

```python
from claude_mpm.skills import Skill, SkillLoader

# Load a skill
skill = SkillLoader.load("universal-testing-test-driven-development")

# Access when_to_use
print(skill.when_to_use)
# Output: "Apply TDD for new feature implementation, bug fixes, refactoring..."

# Use in routing logic
if "refactoring" in user_context.lower() and skill.when_to_use:
    if "refactoring" in skill.when_to_use.lower():
        return skill  # This skill is relevant
```

## Extraction Process

### Where It Comes From

The `when_to_use` field is extracted from the skill's SKILL.md frontmatter:

```markdown
---
name: my-skill
description: "Skill description"
version: 1.0.0
when_to_use: "Use this skill when... [detailed guidance]"
---
```

### Extraction Timing

1. **During skill initialization**: Skills are loaded and parsed
2. **Frontmatter parsing**: YAML frontmatter is extracted from SKILL.md
3. **Field mapping**: `when_to_use:` is mapped to `Skill.when_to_use`
4. **Available immediately**: After load, field is programmatically accessible

### Extraction Code

```python
def load_skill_from_file(skill_path: Path) -> Skill:
    """Load skill and extract when_to_use field"""
    
    # Read SKILL.md
    content = skill_path.read_text()
    
    # Extract YAML frontmatter
    frontmatter = extract_frontmatter(content)
    
    # Parse fields
    skill = Skill(
        name=frontmatter.get("name"),
        description=frontmatter.get("description"),
        version=frontmatter.get("version"),
        when_to_use=frontmatter.get("when_to_use", ""),  # Extract when_to_use
        # ... other fields
    )
    
    return skill
```

## Use Cases

### 1. Smart Skill Routing

Route users to relevant skills based on context:

```python
def route_skill(user_context: str) -> Skill:
    """Route user to the most relevant skill"""
    
    # Load all skills
    skills = SkillLoader.load_all()
    
    # Match context to when_to_use guidance
    for skill in skills:
        if skill.when_to_use:
            # Check if user context matches skill guidance
            if matches_context(user_context, skill.when_to_use):
                return skill
    
    return None

def matches_context(context: str, guidance: str) -> bool:
    """Check if context matches skill guidance"""
    # Simple keyword matching (can be enhanced with semantic search)
    context_lower = context.lower()
    guidance_lower = guidance.lower()
    
    keywords = extract_keywords(guidance_lower)
    return any(kw in context_lower for kw in keywords)
```

### 2. Skill Recommendations for Projects

Recommend skills based on project needs:

```python
def recommend_skills_for_project(project_type: str) -> list[Skill]:
    """Recommend skills for a project type"""
    
    skills = SkillLoader.load_all()
    recommendations = []
    
    for skill in skills:
        if skill.when_to_use:
            # Check if skill matches project type
            if project_type.lower() in skill.when_to_use.lower():
                recommendations.append(skill)
    
    return recommendations

# Usage
python_project_skills = recommend_skills_for_project("Python backend")
# Returns: [test-driven-development, flask, django, etc.]
```

### 3. Agent Skill Selection

Select appropriate skills for agent deployments:

```python
def select_skills_for_agent(agent_type: str) -> list[Skill]:
    """Select skills appropriate for agent type"""
    
    skills = SkillLoader.load_all()
    selected = []
    
    for skill in skills:
        if skill.when_to_use:
            # Check if skill is relevant to agent type
            if agent_type in skill.when_to_use:
                selected.append(skill)
    
    return selected

# Usage
qa_agent_skills = select_skills_for_agent("QA")
# Returns: [test-driven-development, systematic-debugging, etc.]
```

### 4. Context-Aware Suggestions

Suggest skills based on current activity:

```python
def suggest_skills(current_task: str) -> list[Skill]:
    """Suggest skills based on current task"""
    
    skills = SkillLoader.load_all()
    suggestions = []
    
    for skill in skills:
        if skill.when_to_use:
            # Use LLM to match task to guidance
            if semantic_match(current_task, skill.when_to_use):
                suggestions.append(skill)
    
    return suggestions

# Usage
if user_is_refactoring():
    suggestions = suggest_skills("refactoring legacy code")
    # Returns: [test-driven-development, systematic-debugging, etc.]
```

## Example Skills

### Test-Driven Development

```markdown
---
name: test-driven-development
description: "TDD patterns and practices for all programming languages"
version: 1.0.0
when_to_use: "Apply TDD for new feature implementation, bug fixes (test the bug first), code refactoring (tests ensure behavior preservation), API development (test contracts), and complex business logic"
tags: [testing, tdd, best-practices]
---
```

### Systematic Debugging

```markdown
---
name: systematic-debugging
description: "Comprehensive debugging methodology for all programming languages"
version: 1.0.0
when_to_use: "Use when investigating bugs, performance issues, or unexpected behavior. Invaluable when: code appears to work but produces wrong results, failures are intermittent or hard to reproduce, you're unfamiliar with the codebase, or you need to understand execution flow"
tags: [debugging, troubleshooting]
---
```

### Git Workflow

```markdown
---
name: universal-collaboration-git-workflow
description: "Essential Git patterns for effective version control"
version: 1.0.0
when_to_use: "Use for all version control workflows including feature branches, commit patterns, conflict resolution, history management, and collaborative development. Essential for teams and open source projects"
tags: [git, version-control, collaboration]
---
```

## API Examples

### Loading a Skill with when_to_use

```python
from claude_mpm.skills import SkillLoader

# Load single skill
skill = SkillLoader.load("test-driven-development")
print(skill.name)          # "test-driven-development"
print(skill.when_to_use)   # "Apply TDD for..."

# Load all skills
all_skills = SkillLoader.load_all()
for skill in all_skills:
    if skill.when_to_use:
        print(f"{skill.name}: {skill.when_to_use}")
```

### Filtering Skills

```python
# Get skills relevant to testing
testing_skills = [
    s for s in SkillLoader.load_all()
    if s.when_to_use and "test" in s.when_to_use.lower()
]

# Get skills for backend development
backend_skills = [
    s for s in SkillLoader.load_all()
    if s.when_to_use and any(
        term in s.when_to_use.lower()
        for term in ["api", "database", "backend"]
    )
]
```

## Best Practices

### Writing Effective when_to_use Guidance

1. **Be specific**: Describe exact scenarios, not vague benefits
   - ✅ "Use for refactoring legacy code, test-driven bug fixes, and API contract testing"
   - ❌ "Use when you need to test things"

2. **Include context**: Mention languages, frameworks, or domains
   - ✅ "Essential for Python/JavaScript backend services and microservices"
   - ❌ "Use for coding"

3. **Highlight unique value**: What makes this skill special?
   - ✅ "Unique capability to detect circular dependencies in import graphs"
   - ❌ "A useful skill"

4. **Keep it concise**: 1-2 sentences for clarity
   - ✅ "Apply TDD for new features and bug fixes. Ensures behavior preservation during refactoring."
   - ❌ "This skill can be used in many ways... [long paragraph]"

## Integration Points

The `when_to_use` field integrates with:

1. **Skill Router**: Routes based on guidance
2. **Skill Recommender**: Recommends relevant skills
3. **Agent Configuration**: Selects skills for agents
4. **CLI Help**: Displays in `claude-mpm skills list` output
5. **Documentation**: Auto-generated skill documentation

## Related Files

- **Skill Dataclass**: `src/claude_mpm/skills/skill.py`
- **Skill Loader**: `src/claude_mpm/skills/loader.py`
- **Skill Router**: `src/claude_mpm/skills/router.py`
- **SKILL.md Format**: `docs/guides/skill-format.md`

## Related Documentation

- [Skills System](../architecture/skills.md)
- [Skill Format Guide](../guides/skill-format.md)
- [Skill Router](../reference/skill-router.md)
