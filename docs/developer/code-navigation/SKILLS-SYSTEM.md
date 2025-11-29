# Skills System Documentation

## Skills System Overview

Claude MPM's skills system provides reusable guidance modules that:
- **Reduce redundancy** - Common patterns extracted once
- **Enable consistency** - Same guidance across agents
- **Allow customization** - Project/user/bundled hierarchy
- **Support auto-linking** - Skills matched to agent types

## Skills Directory Structure

```
src/claude_mpm/skills/
├── __init__.py              # Package exports
├── skill_manager.py         # Core skill management
├── skills_service.py        # Skills service
├── skills_registry.py       # Registry operations
├── agent_skills_injector.py # Skill injection
├── registry.py              # Skill dataclass, registry
└── bundled/                 # Bundled skills
    ├── git-workflow.md
    ├── tdd.md
    ├── code-review.md
    ├── systematic-debugging.md
    ├── api-documentation.md
    ├── refactoring-patterns.md
    ├── performance-profiling.md
    ├── docker-workflow.md
    ├── database-migrations.md
    ├── security-scanning.md
    ├── json-handling.md
    ├── pdf-handling.md
    ├── xlsx-handling.md
    ├── async-testing.md
    ├── imagemagick.md
    ├── nextjs-local-dev.md
    ├── fastapi-local-dev.md
    ├── vite-local-dev.md
    ├── express-local-dev.md
    └── web-performance-optimization.md
```

## Skills Hierarchy

### Three-Tier Precedence
1. **Project** - `.claude-mpm/skills/` - Highest priority
2. **User** - `~/.claude/skills/` - Personal skills
3. **Bundled** - `src/claude_mpm/skills/bundled/` - Defaults

### Discovery Order
```python
# skills/skill_manager.py
class SkillManager:
    def discover_skills(self) -> Dict[str, Skill]:
        skills = {}
        # Load bundled skills first (lowest priority)
        skills.update(self._load_bundled_skills())
        # User skills override bundled
        skills.update(self._load_user_skills())
        # Project skills have highest priority
        skills.update(self._load_project_skills())
        return skills
```

## Skill Format

### Skill File Structure
```markdown
---
name: Git Workflow
version: 0.1.0
description: Best practices for Git operations
categories:
  - version-control
  - workflow
agent_types:
  - engineer
  - ops
  - version_control
---

# Git Workflow Skill

## Commit Guidelines
...

## Branch Strategy
...

## Code Review
...
```

### Skill Dataclass
```python
# skills/registry.py
@dataclass
class Skill:
    name: str
    version: str
    description: str
    content: str
    path: Path
    tier: str  # "project", "user", "bundled"
    categories: List[str] = field(default_factory=list)
    agent_types: List[str] = field(default_factory=list)
    enabled: bool = True
```

## Core Components

### Skills Service
```python
# skills/skills_service.py
class SkillsService:
    """Primary service for skill operations"""
    
    def __init__(self, container: DIContainer):
        self._manager = SkillManager()
        self._registry = SkillsRegistry()
    
    def get_skill(self, name: str) -> Optional[Skill]:
        """Get skill by name"""
    
    def list_skills(
        self,
        category: Optional[str] = None,
        agent_type: Optional[str] = None
    ) -> List[Skill]:
        """List skills with optional filtering"""
    
    def enable_skill(self, name: str) -> bool:
        """Enable a skill"""
    
    def disable_skill(self, name: str) -> bool:
        """Disable a skill"""
    
    def get_skills_for_agent(self, agent_type: str) -> List[Skill]:
        """Get skills linked to agent type"""
```

### Skill Manager
```python
# skills/skill_manager.py
class SkillManager:
    """Low-level skill management"""
    
    def discover_skills(self) -> Dict[str, Skill]:
        """Discover all available skills"""
    
    def load_skill(self, path: Path) -> Optional[Skill]:
        """Load skill from file"""
    
    def validate_skill(self, skill: Skill) -> Tuple[bool, List[str]]:
        """Validate skill structure"""
    
    def get_skill_content(self, name: str) -> Optional[str]:
        """Get skill content for injection"""
```

### Skills Registry
```python
# skills/skills_registry.py
class SkillsRegistry:
    """Registry for skill metadata and configuration"""
    
    def __init__(self):
        self._skills: Dict[str, Skill] = {}
        self._config = self._load_config()
    
    def register_skill(self, skill: Skill) -> None:
        """Register a skill"""
    
    def get_enabled_skills(self) -> List[Skill]:
        """Get all enabled skills"""
    
    def get_skill_links(self, agent_type: str) -> List[str]:
        """Get skill names linked to agent type"""
```

### Agent Skills Injector
```python
# skills/agent_skills_injector.py
class AgentSkillsInjector:
    """Inject skills into agent prompts"""
    
    def __init__(self, skill_service: SkillsService):
        self._service = skill_service
    
    def inject_skills(
        self,
        agent_template: Dict,
        skills: Optional[List[str]] = None
    ) -> str:
        """Inject skill content into agent prompt"""
        # Get skills to inject
        skill_names = skills or agent_template.get("skills", [])
        
        # Auto-link based on agent type if no explicit skills
        if not skill_names:
            agent_type = agent_template.get("type", "engineer")
            skill_names = self.get_auto_linked_skills(agent_type)
        
        # Build skill content
        skill_sections = []
        for name in skill_names:
            skill = self._service.get_skill(name)
            if skill and skill.enabled:
                skill_sections.append(self._format_skill(skill))
        
        return "\n\n".join(skill_sections)
    
    def get_auto_linked_skills(self, agent_type: str) -> List[str]:
        """Get auto-linked skills for agent type"""
        return DEFAULT_SKILL_LINKS.get(agent_type, [])
```

## Default Skill Links

```python
# skills/agent_skills_injector.py
DEFAULT_SKILL_LINKS = {
    "engineer": [
        "git-workflow",
        "tdd",
        "code-review",
        "refactoring-patterns"
    ],
    "qa": [
        "tdd",
        "systematic-debugging",
        "async-testing"
    ],
    "ops": [
        "git-workflow",
        "docker-workflow"
    ],
    "security": [
        "security-scanning"
    ],
    "documentation": [
        "api-documentation"
    ],
    "data_engineer": [
        "database-migrations"
    ],
    "web_ui": [
        "web-performance-optimization"
    ],
    "python_engineer": [
        "git-workflow",
        "tdd",
        "async-testing"
    ],
    "nextjs_engineer": [
        "nextjs-local-dev",
        "web-performance-optimization"
    ]
}
```

## Bundled Skills

### Development Workflow
| Skill | Description |
|-------|-------------|
| `git-workflow` | Git best practices, branching, commits |
| `tdd` | Test-driven development patterns |
| `code-review` | Code review guidelines |
| `systematic-debugging` | Debugging methodology |
| `refactoring-patterns` | Refactoring best practices |

### Documentation & APIs
| Skill | Description |
|-------|-------------|
| `api-documentation` | API doc standards |

### Operations
| Skill | Description |
|-------|-------------|
| `docker-workflow` | Containerization practices |
| `database-migrations` | Migration patterns |
| `security-scanning` | Security audit practices |

### File Handling
| Skill | Description |
|-------|-------------|
| `json-handling` | JSON processing patterns |
| `pdf-handling` | PDF manipulation |
| `xlsx-handling` | Excel file handling |

### Testing
| Skill | Description |
|-------|-------------|
| `async-testing` | Async test patterns |

### Local Development
| Skill | Description |
|-------|-------------|
| `nextjs-local-dev` | Next.js development server |
| `fastapi-local-dev` | FastAPI local server |
| `vite-local-dev` | Vite dev server |
| `express-local-dev` | Express.js server |

### Performance
| Skill | Description |
|-------|-------------|
| `web-performance-optimization` | Core Web Vitals, Lighthouse |

### Media
| Skill | Description |
|-------|-------------|
| `imagemagick` | Image processing operations |
| `performance-profiling` | Performance analysis |

## CLI Commands

### List Skills
```bash
# List all skills
claude-mpm skills list

# Filter by category
claude-mpm skills list --category testing

# Filter by agent type
claude-mpm skills list --agent-type engineer

# Show disabled skills
claude-mpm skills list --all
```

### Enable/Disable Skills
```bash
# Enable a skill
claude-mpm skills enable systematic-debugging

# Disable a skill
claude-mpm skills disable performance-profiling

# Batch enable
claude-mpm skills enable tdd code-review git-workflow
```

### Deploy Skills from GitHub
```bash
# Deploy from default collection
claude-mpm skills deploy-github

# Deploy with specific toolchain
claude-mpm skills deploy-github --toolchain python

# Deploy from specific collection
claude-mpm skills deploy-github --collection obra-superpowers

# Deploy specific categories
claude-mpm skills deploy-github --categories testing security
```

### Manage Collections
```bash
# Add collection
claude-mpm skills collection-add obra https://github.com/obra/superpowers

# List collections
claude-mpm skills collection-list

# Disable collection
claude-mpm skills collection-disable claude-mpm

# Set default collection
claude-mpm skills collection-set-default obra-superpowers
```

### Interactive Management
```bash
# Interactive skills wizard
claude-mpm configure
# Select "Skills Management"
```

## Configuration

### Skills Configuration File
```yaml
# ~/.claude-mpm/configuration.yaml
skills:
  enabled: true
  auto_link: true
  
  # Custom skill links override defaults
  custom_links:
    engineer:
      - git-workflow
      - tdd
      - my-custom-skill
    
  # Disabled skills
  disabled:
    - performance-profiling
  
  # Collections
  collections:
    - name: default
      url: https://github.com/anthropics/skills
      enabled: true
    - name: obra-superpowers
      url: https://github.com/obra/superpowers
      enabled: true
```

### Project-Level Configuration
```yaml
# .claude-mpm/configuration.yaml
skills:
  # Project-specific skill links
  custom_links:
    engineer:
      - project-conventions
      - our-testing-patterns
  
  # Force specific skills for this project
  required:
    - project-conventions
```

## Creating Custom Skills

### 1. Create Skill File
```markdown
<!-- ~/.claude/skills/my-custom-skill.md -->
---
name: My Custom Skill
version: 1.0.0
description: Custom guidance for my workflow
categories:
  - custom
  - workflow
agent_types:
  - engineer
  - qa
---

# My Custom Skill

## Guidelines
Your custom guidance here...

## Examples
...
```

### 2. Register Skill (Optional)
```yaml
# ~/.claude-mpm/configuration.yaml
skills:
  custom_links:
    engineer:
      - my-custom-skill
```

### 3. Verify
```bash
# Check skill is discovered
claude-mpm skills list --all

# Verify injection
claude-mpm agents show engineer --with-skills
```

## Skill Versioning

### Version Format
Skills use semantic versioning: `MAJOR.MINOR.PATCH`

### Check Versions
```bash
# Check skill versions
claude-mpm skills list --show-version

# Or using /mpm-version command in Claude Code
/mpm-version
```

### Update Skills
```bash
# Update from GitHub collection
claude-mpm skills deploy-github --update
```

## Performance Considerations

### Skill Loading
- Skills are cached after first load
- Cache invalidated on file changes
- Bundled skills loaded at startup

### Injection Optimization
- Skills injected once per agent instantiation
- Content minified to reduce tokens
- Large skills can be split into sections

### Token Budget
- Average skill: 500-2000 tokens
- Bundled skills total: ~15,000 tokens
- Injection reduces overall template size by ~85%

---
See also:
- [AGENT-SYSTEM.md](AGENT-SYSTEM.md) for agent integration
- [CLI-STRUCTURE.md](CLI-STRUCTURE.md) for CLI commands
