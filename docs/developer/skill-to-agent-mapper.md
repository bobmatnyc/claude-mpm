# SkillToAgentMapper Service

## Overview

The `SkillToAgentMapper` service provides bidirectional mapping between skill paths and agent IDs using a YAML configuration file. It enables progressive skills discovery by determining which agents should receive which skills.

**Key Features**:
- YAML-based skill-to-agent mapping configuration
- ALL_AGENTS marker expansion for universal skills
- Pattern-based inference for unmapped skill paths
- Bidirectional lookup (skill → agents, agent → skills)
- Caching and efficient indexing

## Configuration File

**Location**: `src/claude_mpm/config/skill_to_agent_mapping.yaml`

**Format**:
```yaml
# Explicit skill-to-agent mappings
skill_mappings:
  toolchains/python/frameworks/django:
    - python-engineer
    - data-engineer
    - engineer
    - api-qa

  universal/collaboration/git-workflow: *all_agents  # Expands to all agents

# Pattern-based inference rules
inference_rules:
  language_patterns:
    python: [python-engineer, data-engineer, engineer]
    typescript: [typescript-engineer, javascript-engineer, engineer]

  framework_patterns:
    nextjs: [nextjs-engineer, react-engineer, typescript-engineer]
    django: [python-engineer, engineer]

  domain_patterns:
    testing: [qa, engineer]
    security: [security, ops, engineer]

# ALL_AGENTS expansion list
all_agents_list:
  - engineer
  - python-engineer
  - typescript-engineer
  # ... (41 total agents)
```

## Basic Usage

### Initialize Mapper

```python
from claude_mpm.services.skills import SkillToAgentMapper

# Use default configuration
mapper = SkillToAgentMapper()

# Or specify custom config path
mapper = SkillToAgentMapper(config_path=Path("custom_mapping.yaml"))
```

### Forward Lookup: Skill → Agents

```python
# Get agents for a specific skill path
agents = mapper.get_agents_for_skill('toolchains/python/frameworks/django')
# Returns: ['python-engineer', 'data-engineer', 'engineer', 'api-qa']

# Unmapped skill with inference fallback
agents = mapper.get_agents_for_skill('toolchains/python/new-framework')
# Returns: ['python-engineer', 'data-engineer', 'engineer'] (inferred from 'python' pattern)

# No mapping or inference available
agents = mapper.get_agents_for_skill('unknown/skill/path')
# Returns: []
```

### Inverse Lookup: Agent → Skills

```python
# Get all skills for an agent
skills = mapper.get_skills_for_agent('python-engineer')
# Returns: List of 39 skill paths assigned to python-engineer

# Unmapped agent
skills = mapper.get_skills_for_agent('nonexistent-agent')
# Returns: []
```

### ALL_AGENTS Expansion

Skills marked with `*all_agents` in YAML expand to all agents in `all_agents_list`:

```python
agents = mapper.get_agents_for_skill('universal/collaboration/git-workflow')
# Returns: All 41 agents from all_agents_list
```

## Pattern-based Inference

For skill paths not explicitly mapped, the service can infer agents using pattern matching:

### Language Patterns

```python
agents = mapper.infer_agents_from_pattern('toolchains/python/new-library')
# Matches 'python' language pattern
# Returns: ['python-engineer', 'data-engineer', 'engineer']
```

### Framework Patterns

```python
agents = mapper.infer_agents_from_pattern('toolchains/typescript/frameworks/nextjs-advanced')
# Matches 'nextjs' framework pattern
# Returns: ['nextjs-engineer', 'react-engineer', 'typescript-engineer']
```

### Domain Patterns

```python
agents = mapper.infer_agents_from_pattern('universal/testing/new-test-skill')
# Matches 'testing' domain pattern
# Returns: ['qa', 'engineer']
```

### Multiple Pattern Matches

```python
agents = mapper.infer_agents_from_pattern('toolchains/python/testing/pytest-advanced')
# Matches both 'python' language and 'testing' domain patterns
# Returns: ['python-engineer', 'data-engineer', 'qa', 'engineer'] (deduplicated)
```

## Introspection and Statistics

### Get All Mapped Skills

```python
skills = mapper.get_all_mapped_skills()
# Returns: Sorted list of all 109 explicitly mapped skill paths
```

### Get All Agents

```python
agents = mapper.get_all_agents()
# Returns: Sorted list of all 41 agent IDs referenced in mappings
```

### Check if Skill is Mapped

```python
is_mapped = mapper.is_skill_mapped('toolchains/python/frameworks/django')
# Returns: True

is_mapped = mapper.is_skill_mapped('toolchains/rust/unknown')
# Returns: False
```

### Get Mapping Statistics

```python
stats = mapper.get_mapping_stats()
# Returns:
# {
#     "total_skills": 109,
#     "total_agents": 41,
#     "avg_agents_per_skill": 7.98,
#     "avg_skills_per_agent": 21.22,
#     "config_path": "/path/to/config.yaml",
#     "config_version": "1.0.0"
# }
```

## Integration with Selective Skills Deployment

The `SkillToAgentMapper` integrates with selective skills deployment:

```python
from claude_mpm.services.skills import SkillToAgentMapper
from claude_mpm.services.skills.selective_skill_deployer import get_required_skills_from_agents

# 1. Get skills referenced by deployed agents
agents_dir = Path(".claude/agents")
required_skills = get_required_skills_from_agents(agents_dir)

# 2. For each required skill, determine which agents need it
mapper = SkillToAgentMapper()
for skill_path in required_skills:
    agents = mapper.get_agents_for_skill(skill_path)
    print(f"{skill_path} → {len(agents)} agents")

    # Deploy skill to these agents
    # ...
```

## Error Handling

### Missing Configuration File

```python
from pathlib import Path

try:
    mapper = SkillToAgentMapper(config_path=Path("missing.yaml"))
except FileNotFoundError as e:
    print(f"Configuration file not found: {e}")
```

### Invalid YAML

```python
import yaml

try:
    mapper = SkillToAgentMapper(config_path=Path("invalid.yaml"))
except yaml.YAMLError as e:
    print(f"Invalid YAML in configuration: {e}")
```

### Missing Required Sections

```python
try:
    mapper = SkillToAgentMapper(config_path=Path("incomplete.yaml"))
except ValueError as e:
    print(f"Configuration validation error: {e}")
```

## Performance Considerations

### Indexing Strategy

The service builds bidirectional indexes on initialization:
- `_skill_to_agents`: Forward index (skill → agents)
- `_agent_to_skills`: Inverse index (agent → skills)

**Trade-offs**:
- **Initialization**: O(n) where n = total mappings
- **Lookup**: O(1) for exact matches (dictionary lookup)
- **Inference**: O(k) where k = number of inference rules
- **Memory**: 2x storage for bidirectional indexes

### Caching

The configuration is loaded once at initialization and cached in memory:

```python
# First mapper: Loads config from disk
mapper1 = SkillToAgentMapper()

# Second mapper: Loads config again (separate instance)
mapper2 = SkillToAgentMapper()
```

**Recommendation**: Reuse a single `SkillToAgentMapper` instance across your application.

### Inference Performance

Pattern-based inference scans all inference rules:
- Language patterns: ~10 patterns
- Framework patterns: ~10 patterns
- Domain patterns: ~8 patterns

**Best practice**: Use explicit mappings for frequently-accessed skills to avoid inference overhead.

## Testing

Comprehensive test suite: `tests/services/skills/test_skill_to_agent_mapper.py`

**Coverage**:
- Initialization (default config, custom config, error handling)
- Forward mapping (exact match, not found, ALL_AGENTS expansion)
- Inverse mapping (single agent, multiple skills)
- Pattern-based inference (language, framework, domain, multiple patterns)
- Introspection (stats, listing, checking)
- Edge cases (empty paths, invalid data types, case sensitivity)
- Integration with default configuration

Run tests:
```bash
pytest tests/services/skills/test_skill_to_agent_mapper.py -v
```

## References

- **Configuration**: `src/claude_mpm/config/skill_to_agent_mapping.yaml`
- **Research**: `docs/research/skill-path-to-agent-mapping-2025-12-16.md`
- **Feature**: Progressive Skills Discovery (#117)
- **Related**: `selective_skill_deployer.py` for agent skill extraction
