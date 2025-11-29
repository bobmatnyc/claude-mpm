# Agent System Documentation

## Agent Architecture Overview

Claude MPM extends Claude Code's native agent system with:
- **Pre-built agents** - 37+ specialized agents for development workflows
- **Three-tier hierarchy** - Project > User > System precedence
- **Skills integration** - Reusable skill modules injected into agents
- **Memory persistence** - Agent learning across sessions

## Agent Directory Structure

```
src/claude_mpm/agents/
├── templates/              # JSON agent templates
│   ├── base_agent.json    # Base configuration
│   ├── engineer.json
│   ├── qa.json
│   ├── research.json
│   ├── documentation.json
│   ├── ops.json
│   ├── security.json
│   └── ... (37+ templates)
├── BASE_AGENT_TEMPLATE.md  # Template documentation
├── BASE_ENGINEER.md        # Engineer base prompt
├── BASE_QA.md              # QA base prompt
├── PM_INSTRUCTIONS.md      # PM orchestration instructions
├── MEMORY.md               # Memory format specification
├── OUTPUT_STYLE.md         # Output format guidelines
├── WORKFLOW.md             # Workflow patterns
├── agent_loader.py         # Template loading
├── agents_metadata.py      # Agent configurations
└── frontmatter_validator.py # Validation
```

## Agent Template Format

### JSON Template Structure
```json
{
  "id": "engineer",
  "name": "Engineer Agent",
  "version": "2.0.0",
  "type": "engineer",
  "tier": "system",
  "description": "Software development and implementation",
  "capabilities": [
    "code_implementation",
    "debugging",
    "testing"
  ],
  "specializations": ["backend", "frontend"],
  "frameworks": ["python", "typescript"],
  "base_template": "BASE_ENGINEER",
  "prompt_components": {
    "role": "You are a software engineer...",
    "instructions": "...",
    "output_format": "..."
  },
  "skills": ["git-workflow", "tdd", "code-review"],
  "model_config": {
    "preferred_model": "claude-sonnet-4-20250514",
    "temperature": 0.7
  }
}
```

### Markdown Agent Format (Deployed)
```markdown
---
name: Engineer Agent
version: 2.0.0
type: engineer
capabilities:
  - code_implementation
  - debugging
skills:
  - git-workflow
  - tdd
---

# Engineer Agent

## Role
You are a software engineer...

## Instructions
...

## Skills
[Skills content injected here]
```

## Agent Loading Flow

```
Agent Request
    │
    ├── 1. agents/agent_loader.py:get_agent_prompt()
    │       └── Load JSON template from templates/
    │
    ├── 2. Apply base template inheritance
    │       └── Merge with BASE_* templates
    │
    ├── 3. skills/agent_skills_injector.py
    │       └── Inject linked skills content
    │
    ├── 4. Memory injection (if enabled)
    │       └── services/agents/memory/
    │
    └── 5. Return final prompt string
```

## Three-Tier Agent Hierarchy

### Precedence Order
1. **PROJECT** - `.claude-mpm/agents/` - Highest priority
2. **USER** - `~/.claude/agents/` - User customizations  
3. **SYSTEM** - `src/claude_mpm/agents/templates/` - Defaults

### Discovery Logic (`services/agents/registry/`)
```python
class DeployedAgentDiscovery:
    def discover_all_agents():
        agents = {}
        # System agents (lowest priority)
        agents.update(self.discover_system_agents())
        # User agents (override system)
        agents.update(self.discover_user_agents())
        # Project agents (highest priority)
        agents.update(self.discover_project_agents())
        return agents
```

## Agent Types

### Core Agents
| Agent | Type | Purpose |
|-------|------|---------|
| `engineer` | engineer | General software development |
| `qa` | qa | Testing and quality assurance |
| `research` | research | Code analysis and research |
| `documentation` | documentation | Documentation creation |
| `ops` | ops | Operations and deployment |
| `security` | security | Security analysis |

### Language Engineers
| Agent | Specialization |
|-------|---------------|
| `python_engineer` | Python, async, SOA patterns |
| `rust_engineer` | Systems programming, memory safety |
| `typescript_engineer` | TypeScript, Node.js |
| `javascript_engineer` | JavaScript, React |
| `golang_engineer` | Go microservices |
| `java_engineer` | Java enterprise |

### Specialized Agents
| Agent | Purpose |
|-------|---------|
| `web_ui` | Frontend development |
| `web_qa` | Web testing, E2E |
| `data_engineer` | Data pipelines, ETL |
| `version_control` | Git workflows |
| `refactoring_engineer` | Code optimization |
| `code_analyzer` | Static analysis |
| `memory_manager` | Context management |
| `ticketing` | Issue tracking |

## Agent Memory System

### Memory Format
```markdown
# Agent Memory: engineer

## Learnings
- Project uses Python 3.11 with type hints
- Follows service-oriented architecture
- Uses pytest for testing

## Patterns
- Error handling uses custom exception hierarchy
- All services implement interfaces

## Context
- Main entry: src/claude_mpm/cli/__main__.py
- Tests in: tests/
```

### Memory Operations
```python
# services/agents/memory/memory_manager.py
class AgentMemoryManager:
    def load_memory(agent_id: str) -> Optional[str]:
        """Load memory from .claude-mpm/memories/<agent>_memory.md"""
    
    def save_memory(agent_id: str, content: str) -> bool:
        """Save memory content"""
    
    def update_memory(agent_id: str, learnings: List[str]) -> bool:
        """Append new learnings"""
    
    def optimize_memory(agent_id: str) -> bool:
        """Remove duplicates, consolidate"""
```

### Memory Update via Response
Agents can update memory using JSON response fields:
```json
{
  "response": "...",
  "remember": ["New learning to add"],
  "MEMORIES": "Complete replacement of memories"
}
```

## Skills Integration

### Skill Linking
```python
# skills/agent_skills_injector.py
class AgentSkillsInjector:
    def inject_skills(agent_template: dict) -> str:
        """Inject skill content into agent prompt"""
        skills = agent_template.get("skills", [])
        skill_content = []
        for skill_name in skills:
            content = self.load_skill(skill_name)
            skill_content.append(content)
        return "\n".join(skill_content)
```

### Auto-Linking
Skills are auto-linked based on agent type:
```python
DEFAULT_SKILL_LINKS = {
    "engineer": ["git-workflow", "tdd", "code-review"],
    "qa": ["tdd", "systematic-debugging"],
    "ops": ["git-workflow", "docker-workflow"],
    "security": ["security-scanning"]
}
```

## Agent Deployment

### Deployment Service
```python
# services/agents/deployment/deployment_service.py
class AgentDeploymentService:
    def deploy_agents(force=False, include_all=False):
        """Deploy agents to ~/.claude/agents/"""
        for agent in self.get_deployable_agents():
            self.validate_agent(agent)
            self.prepare_deployment(agent)
            self.write_agent_file(agent)
    
    def validate_agent(agent_path: Path) -> Tuple[bool, List[str]]:
        """Validate agent structure and content"""
```

### CLI Commands
```bash
# Deploy all agents
claude-mpm agents deploy

# Deploy specific agent
claude-mpm agents deploy engineer

# Force redeploy
claude-mpm agents deploy --force

# List deployed agents
claude-mpm agents list

# Check agent status
claude-mpm agents status engineer
```

## Agent Metadata (`agents_metadata.py`)

```python
ENGINEER_CONFIG = {
    "name": "Engineer",
    "agent_type": "engineer",
    "capabilities": [
        "code_implementation",
        "debugging", 
        "testing",
        "refactoring"
    ],
    "specializations": ["backend", "frontend"],
    "model_preferences": {
        "complex_tasks": "claude-sonnet-4-20250514",
        "simple_tasks": "claude-haiku-4-20250514"
    }
}

ALL_AGENT_CONFIGS = {
    "engineer": ENGINEER_CONFIG,
    "qa": QA_CONFIG,
    "research": RESEARCH_CONFIG,
    # ...
}
```

## Agent Validation

### Frontmatter Validation
```python
# agents/frontmatter_validator.py
class FrontmatterValidator:
    def validate(content: str) -> Tuple[bool, List[str]]:
        """Validate agent frontmatter"""
        # Check required fields
        # Validate version format
        # Check capability references
        # Verify skill existence
```

### Schema Validation
```json
// schemas/agent_schema.json
{
  "type": "object",
  "required": ["id", "name", "type", "version"],
  "properties": {
    "id": {"type": "string"},
    "name": {"type": "string"},
    "type": {"enum": ["engineer", "qa", "ops", ...]},
    "version": {"pattern": "^\\d+\\.\\d+\\.\\d+$"}
  }
}
```

## Creating New Agents

### 1. Create Template
```json
// agents/templates/my_agent.json
{
  "id": "my_agent",
  "name": "My Custom Agent",
  "version": "1.0.0",
  "type": "engineer",
  "capabilities": ["custom_capability"],
  "base_template": "BASE_ENGINEER",
  "prompt_components": {
    "role": "You are a specialized agent for...",
    "instructions": "..."
  },
  "skills": ["relevant-skill"]
}
```

### 2. Update Metadata
```python
# agents/agents_metadata.py
MY_AGENT_CONFIG = {
    "name": "My Agent",
    "agent_type": "my_agent",
    "capabilities": ["custom_capability"]
}

ALL_AGENT_CONFIGS["my_agent"] = MY_AGENT_CONFIG
```

### 3. Deploy
```bash
claude-mpm agents deploy my_agent
```

## Agent Best Practices

1. **Keep prompts focused** - Single responsibility per agent
2. **Use skill linking** - Avoid duplicating guidance in prompts
3. **Version properly** - Use semantic versioning
4. **Test thoroughly** - Validate before deployment
5. **Document capabilities** - Clear capability definitions
6. **Memory hygiene** - Periodically optimize memories

---
See also:
- [SKILLS-SYSTEM.md](SKILLS-SYSTEM.md) for skills documentation
- [SERVICE-LAYER.md](SERVICE-LAYER.md) for agent services
