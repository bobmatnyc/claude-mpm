# Agent Definition Structure & Metadata Research

**Date**: 2026-02-14
**Researcher**: Research Agent (Task #4)
**Purpose**: Comprehensive analysis of agent definitions in the claude-mpm ecosystem to inform dashboard UI improvements

---

## 1. Agent Repository Structure

### Repository Location
`/Users/mac/workspace/claude-mpm-agents/` (GitHub: bobmatnyc/claude-mpm-agents)

### Directory Hierarchy

```
claude-mpm-agents/
├── agents/                          # All agent definitions (Markdown w/ YAML frontmatter)
│   ├── BASE-AGENT.md                # Root-level base agent template
│   ├── .etag-cache.json             # GitHub ETag caching for sync
│   ├── claude-mpm/                  # MPM-specific agents
│   │   ├── BASE-AGENT.md            # Category base agent
│   │   ├── mpm-agent-manager.md     # Agent lifecycle manager
│   │   └── mpm-skills-manager.md    # Skills lifecycle manager
│   ├── documentation/               # Documentation agents
│   │   ├── documentation.md
│   │   └── ticketing.md
│   ├── engineer/                    # Engineering agents (largest category)
│   │   ├── BASE-AGENT.md            # Category base agent
│   │   ├── backend/                 # Backend specialists (10 agents)
│   │   │   ├── python-engineer.md
│   │   │   ├── golang-engineer.md
│   │   │   ├── java-engineer.md
│   │   │   ├── javascript-engineer.md
│   │   │   ├── nestjs-engineer.md
│   │   │   ├── phoenix-engineer.md
│   │   │   ├── php-engineer.md
│   │   │   ├── ruby-engineer.md
│   │   │   ├── rust-engineer.md
│   │   │   └── visual-basic-engineer.md
│   │   ├── core/
│   │   │   └── engineer.md          # Base engineer agent
│   │   ├── data/
│   │   │   ├── data-engineer.md
│   │   │   └── typescript-engineer.md
│   │   ├── frontend/
│   │   │   ├── nextjs-engineer.md
│   │   │   ├── react-engineer.md
│   │   │   ├── svelte-engineer.md
│   │   │   └── web-ui.md
│   │   ├── mobile/
│   │   │   ├── dart-engineer.md
│   │   │   └── tauri-engineer.md
│   │   └── specialized/
│   │       ├── imagemagick.md
│   │       ├── prompt-engineer.md
│   │       └── refactoring-engineer.md
│   ├── ops/                         # Operations agents
│   │   ├── BASE-AGENT.md
│   │   ├── agentic-coder-optimizer.md
│   │   ├── project-organizer.md
│   │   ├── core/
│   │   │   └── ops.md
│   │   ├── platform/
│   │   │   ├── clerk-ops.md
│   │   │   ├── digitalocean-ops.md
│   │   │   ├── gcp-ops.md
│   │   │   ├── local-ops.md
│   │   │   └── vercel-ops.md
│   │   └── tooling/
│   │       ├── tmux-agent.md
│   │       └── version-control.md
│   ├── qa/                          # Quality assurance agents
│   │   ├── BASE-AGENT.md
│   │   ├── api-qa.md
│   │   ├── qa.md
│   │   ├── real-user.md
│   │   └── web-qa.md
│   ├── security/
│   │   └── security.md
│   └── universal/                   # Cross-cutting agents
│       ├── code-analyzer.md
│       ├── content-agent.md
│       ├── memory-manager-agent.md
│       ├── product-owner.md
│       └── research.md
├── templates/                       # Build templates and references
│   ├── AGENT_TEMPLATE_REFERENCE.md
│   ├── BASE-ENGINEER.md
│   ├── circuit-breakers.md
│   ├── PM-INSTRUCTIONS.md
│   ├── base/                        # Base templates by category
│   │   ├── base-engineer.md
│   │   ├── base-ops.md
│   │   ├── base-qa.md
│   │   ├── base-research.md
│   │   ├── base-specialized.md
│   │   ├── INDEX.md
│   │   └── README.md
│   └── ... (response-format, pm-examples, etc.)
├── build-agent.py                   # Agent composition build script
└── AUTO-DEPLOY-INDEX.md             # Auto-deployment categorization index
```

### Key Organizational Patterns

1. **Category-based Hierarchy**: Agents organized by role (engineer, ops, qa, security, universal, claude-mpm, documentation)
2. **Sub-categorization**: Engineer agents further split by backend/frontend/data/mobile/specialized
3. **BASE-AGENT Composition**: Each category has a `BASE-AGENT.md` that gets composed into child agents via `build-agent.py`
4. **~45 agent definitions** in the repository (including category variants)

---

## 2. Agent Definition Format (Markdown with YAML Frontmatter)

All modern agents use Markdown files with YAML frontmatter. The frontmatter contains structured metadata; the markdown body contains the agent's system prompt/instructions.

### Complete Frontmatter Schema

Below is the FULL set of frontmatter fields observed across all agent definitions, with their types and which agents use them:

#### Core Identity Fields (ALL agents)

| Field | Type | Required | Example | Description |
|-------|------|----------|---------|-------------|
| `name` | string | YES | `"Python Engineer"` | Human-readable display name (3-50 chars) |
| `description` | string | YES | `"Python 3.12+ development specialist..."` | Brief purpose description (10-250 chars) |
| `agent_id` | string | YES | `"python-engineer"` | Unique kebab-case identifier |
| `agent_type` | enum | YES | `"engineer"` | Classification: base, engineer, qa, documentation, research, security, ops, data_engineer, version_control, system, refactoring, memory_manager |
| `version` | semver | YES | `"2.3.0"` | Agent template version |
| `schema_version` | semver | YES | `"1.3.0"` | Schema version (1.2.0 or 1.3.0) |

#### Configuration Fields (ALL agents)

| Field | Type | Required | Example | Description |
|-------|------|----------|---------|-------------|
| `resource_tier` | enum | YES | `"standard"` | Resource allocation: basic, standard, intensive, lightweight, high |
| `tags` | string[] | YES | `["python", "async"]` | Discovery/search tags (1-10, unique) |
| `category` | enum | NO | `"engineering"` | UI category: engineering, research, quality, operations, specialized, system, project-management, infrastructure, claude-mpm |
| `color` | enum | NO | `"green"` | Visual identification color: red, blue, green, yellow, purple, orange, pink, cyan, indigo, gray, black, white |
| `author` | string | NO | `"Claude MPM Team"` | Template author |
| `temperature` | float | NO | `0.2` | Model temperature (0.0-1.0) |
| `max_tokens` | int | NO | `4096` | Max response tokens (1000-200000) |
| `timeout` | int | NO | `900` | Operation timeout in seconds (30-3600) |

#### Capabilities Block (ALL agents)

```yaml
capabilities:
  memory_limit: 2048    # Memory limit in MB (512-8192)
  cpu_limit: 50         # CPU limit percentage (10-100)
  network_access: true  # Whether agent needs network
```

#### Dependencies Block (ALL agents)

```yaml
dependencies:
  python:               # Python packages required
  - black>=24.0.0
  - pytest>=8.0.0
  system:               # System commands required
  - python3.12+
  - git
  nodejs:               # Node.js packages (some agents)
  - eslint>=8.0.0
  npm:                  # NPM packages (some agents)
  - vercel@latest
  optional: false       # Whether dependencies are optional
```

Observed dependency categories:
- `python` - Most agents
- `python_optional` - Research, QA agents
- `system` - All agents
- `nodejs` - Refactoring, web-related agents
- `npm` - Vercel ops, web agents

#### Skills Reference (ALL agents)

```yaml
skills:                 # Skill names this agent should have deployed
- brainstorming
- git-workflow
- test-driven-development
- systematic-debugging
```

Skills lists range from 10-30+ entries. These are **skill names** (not full paths), referencing skills from a separate skills repository.

#### Template Versioning (Most agents)

```yaml
template_version: 2.3.0
template_changelog:
- version: 2.3.0
  date: '2025-11-04'
  description: 'Architecture Enhancement: Added comprehensive guidance...'
- version: 2.2.1
  date: '2025-10-18'
  description: 'Async Enhancement: Added comprehensive AsyncWorkerPool pattern...'
```

#### Knowledge Block (Most agents)

```yaml
knowledge:
  domain_expertise:     # Areas of expertise (string[])
  - "Python 3.12-3.13 features (JIT, free-threaded, TypeForm)"
  - "Service-oriented architecture with ABC interfaces"
  best_practices:       # Best practices followed (string[])
  - "100% type coverage with mypy --strict"
  - "Pydantic models for data validation boundaries"
  constraints:          # Operating constraints (string[])
  - "Maximum 5-10 test files for sampling per session"
  - "Skip test files >500KB unless absolutely critical"
  examples:             # Example scenarios (object[])
  - scenario: "Creating type-safe service with DI"
    approach: "..."
```

#### Interactions Block (QA, some agents)

```yaml
interactions:
  input_format:
    required_fields:
    - task
    optional_fields:
    - context
    - constraints
  output_format:
    structure: markdown  # markdown|json|structured|free-form
    includes:
    - analysis
    - recommendations
    - code
  handoff_agents:        # Agents this agent can hand off to
  - engineer
  - security
  triggers: []           # Conditions that trigger actions
```

#### Memory Routing (QA, Research agents)

```yaml
memory_routing:
  description: "Stores testing strategies, quality standards, and bug patterns"
  categories:
  - "Testing strategies and coverage requirements"
  - "Quality standards and acceptance criteria"
  keywords:
  - test
  - quality
  - coverage
  retention_policy: permanent  # permanent|session|temporary
```

---

## 3. JSON Schema Definition

**Location**: `src/claude_mpm/schemas/agent_schema.json` (v1.3.0)

The JSON schema defines the canonical structure with these top-level required fields:
- `schema_version`
- `agent_id`
- `agent_version`
- `agent_type`
- `metadata` (name, description, tags required)
- `capabilities` (resource_tier required)
- `instructions`

And these optional top-level blocks:
- `template_version`, `template_changelog`
- `dependencies` (python, python_optional, system, optional)
- `knowledge` (domain_expertise, best_practices, constraints, examples)
- `interactions` (input_format, output_format, handoff_agents, triggers, protocols, response_format)
- `testing` (test_cases, performance_benchmarks, integration_tests)
- `memory_routing` (description, categories, keywords, retention_policy)
- `hooks` (pre_execution, post_execution)

The schema allows `additionalProperties: true`, so agent definitions can include fields not explicitly defined in the schema.

---

## 4. Agent Data Models in claude-mpm

### 4.1 AgentDefinition Dataclass (`models/agent_definition.py`)

The Python model provides structured representation:

```python
@dataclass
class AgentDefinition:
    # Core identifiers
    name: str
    title: str
    file_path: str

    # Metadata (AgentMetadata dataclass)
    metadata: AgentMetadata  # type, model_preference, version, last_updated,
                              # author, tags, specializations,
                              # collection_id, source_path, canonical_id

    # Behavior definition
    primary_role: str
    when_to_use: Dict[str, List[str]]  # {"select": [...], "do_not_select": [...]}
    capabilities: List[str]
    authority: AgentPermissions  # exclusive_write_access, forbidden_operations, read_access
    workflows: List[AgentWorkflow]  # name, trigger, process, output
    escalation_triggers: List[str]
    kpis: List[str]
    dependencies: List[str]
    tools_commands: str
    raw_content: str
    raw_sections: Dict[str, str]
```

### 4.2 AgentMetadata in Registry (`core/unified_agent_registry.py`)

```python
@dataclass
class AgentMetadata:
    name: str
    agent_type: AgentType     # CORE, SPECIALIZED, USER_DEFINED, PROJECT, MEMORY_AWARE
    tier: AgentTier           # PROJECT, USER, SYSTEM
    path: str
    format: AgentFormat       # MARKDOWN, JSON, YAML
    last_modified: float
    description: str
    specializations: List[str]
    memory_files: List[str]
    dependencies: List[str]
    version: str
    author: str
    tags: List[str]
    collection_id: Optional[str]   # "owner/repo-name"
    source_path: Optional[str]     # Relative path in repo
    canonical_id: Optional[str]    # "collection_id:agent_id"
```

### 4.3 RemoteAgentMetadata (`services/agents/deployment/remote_agent_discovery_service.py`)

```python
@dataclass
class RemoteAgentMetadata:
    name: str
    description: str
    model: str
    routing_keywords: List[str]
    routing_paths: List[str]
    routing_priority: int
    source_file: Path
    version: str
    collection_id: Optional[str]
    source_path: Optional[str]
    canonical_id: Optional[str]
```

---

## 5. Current Dashboard API Exposure

### 5.1 Deployed Agents Endpoint

**`GET /api/config/agents/deployed`**

Returns:
```json
{
  "success": true,
  "agents": [
    {
      "name": "engineer",
      "location": "project",
      "path": "/path/to/.claude/agents/engineer.md",
      "version": "2.5.0",
      "type": "core",
      "specializations": [],
      "is_core": true
    }
  ],
  "total": 15
}
```

**Fields exposed**: name, location, path, version, type, specializations, is_core

### 5.2 Available Agents Endpoint

**`GET /api/config/agents/available`**

Returns (with pagination):
```json
{
  "success": true,
  "agents": [
    {
      "agent_id": "python-engineer",
      "name": "Python Engineer",
      "description": "Python 3.12+ development specialist...",
      "version": "2.3.0",
      "source": "bobmatnyc/claude-mpm-agents",
      "source_url": "https://github.com/bobmatnyc/claude-mpm-agents",
      "priority": 100,
      "category": "engineering",
      "tags": ["python", "async", "SOA"],
      "is_deployed": false,
      "metadata": { ... },
      "repository": "bobmatnyc/claude-mpm-agents/agents"
    }
  ],
  "total": 45,
  "has_more": false
}
```

**Fields exposed**: agent_id, name, description, version, source, source_url, priority, category, tags, is_deployed, metadata (nested), repository

### 5.3 Frontend TypeScript Interfaces

```typescript
// DeployedAgent (what the UI expects for deployed agents)
interface DeployedAgent {
  name: string;
  location: string;
  path: string;
  version: string;
  type: string;
  specializations?: string[];
  is_core: boolean;
}

// AvailableAgent (what the UI expects for available agents)
interface AvailableAgent {
  agent_id: string;
  name: string;
  description: string;
  version: string;
  source: string;
  source_url: string;
  priority: number;
  category: string;
  tags: string[];
  is_deployed: boolean;
}
```

### 5.4 Agent Metadata from AgentLoader

The `get_agent_metadata()` method returns a richer structure:
```python
{
    "agent_id": agent_id,
    "name": metadata.get("name"),
    "description": metadata.get("description"),
    "category": category.value,
    "version": metadata.get("version"),
    "model": agent_data.get("model"),
    "resource_tier": agent_data.get("resource_tier"),
    "tier": tier.value,
    "tools": agent_data.get("tools"),
    "capabilities": capabilities,
    "source_file": agent_data.get("_source_file"),
    "has_project_memory": has_memory,
    "memory_size_kb": ...,  # if has_project_memory
    "memory_file": ...,     # if has_project_memory
    "memory_lines": ...,    # if has_project_memory
}
```

---

## 6. Concrete Agent Definition Examples

### Example 1: Python Engineer (engineer/backend)

```yaml
name: Python Engineer
description: 'Python 3.12+ development specialist: type-safe, async-first, production-ready implementations with SOA and DI patterns'
version: 2.3.0
schema_version: 1.3.0
agent_id: python-engineer
agent_type: engineer
resource_tier: standard
tags: [python, python-3-13, engineering, performance, optimization, SOA, DI, dependency-injection, service-oriented, async, asyncio, pytest, type-hints, mypy, pydantic, clean-code, SOLID, best-practices]
category: engineering
color: green
author: Claude MPM Team
temperature: 0.2
max_tokens: 4096
timeout: 900
capabilities: { memory_limit: 2048, cpu_limit: 50, network_access: true }
dependencies: { python: [black>=24.0.0, isort>=5.13.0, mypy>=1.8.0, pytest>=8.0.0, ...], system: [python3.12+], optional: false }
skills: [dspy, langchain, mcp, pytest, mypy, pydantic, git-workflow, test-driven-development, ...]
template_version: 2.3.0
template_changelog: [...]
knowledge: { domain_expertise: [...], best_practices: [...], constraints: [...], examples: [...] }
```

### Example 2: QA Agent

```yaml
name: QA
description: Memory-efficient testing with strategic sampling, targeted validation, and smart coverage analysis
version: 3.5.3
schema_version: 1.3.0
agent_id: qa-agent
agent_type: qa
resource_tier: standard
tags: [qa, testing, quality, validation, memory-efficient, strategic-sampling, grep-first]
category: quality
color: green
author: Claude MPM Team
temperature: 0.0
max_tokens: 8192
timeout: 600
capabilities: { memory_limit: 3072, cpu_limit: 50, network_access: false }
dependencies: { python: [pytest>=7.4.0, hypothesis>=6.92.0, ...], system: [python3, git] }
skills: [test-driven-development, test-quality-inspector, testing-anti-patterns, webapp-testing, ...]
template_version: 2.1.0
template_changelog: [...]
knowledge: { domain_expertise: [...], best_practices: [...], constraints: [...], examples: [] }
interactions: { input_format: {...}, output_format: {...}, handoff_agents: [engineer, security] }
memory_routing: { description: "...", categories: [...], keywords: [...] }
```

### Example 3: Research Agent (most complex)

```yaml
name: Research
description: Memory-efficient codebase analysis with required ticket attachment...
version: 5.0.0
schema_version: 1.3.0
agent_id: research-agent
agent_type: research
resource_tier: high
tags: [research, memory-efficient, ticketing-integration, google-workspace, ...] # 31 tags!
category: research
color: purple
temperature: 0.2
max_tokens: 16384
timeout: 1800
capabilities: { memory_limit: 4096, cpu_limit: 80, network_access: true }
dependencies: { python: [tree-sitter>=0.21.0, pygments>=2.17.0, radon>=6.0.0, ...], system: [python3, git] }
skills: [dspy, langchain, langgraph, mcp, software-patterns, test-driven-development, ...]
template_version: 3.0.0
template_changelog: [...] # 12 changelog entries spanning months of evolution
knowledge: { domain_expertise: [23 items], best_practices: [30+ items], constraints: [...] }
```

### Example 4: Refactoring Engineer

```yaml
name: Refactoring Engineer
agent_id: refactoring-engineer
agent_type: refactoring
resource_tier: intensive           # One of few "intensive" agents
color: green
temperature: 0.1
max_tokens: 12288                  # Higher than most
timeout: 1800
capabilities: { memory_limit: 6144, cpu_limit: 80, network_access: false }
dependencies:
  python: [rope>=1.11.0, black>=23.0.0, radon>=6.0.0, ...]
  nodejs: [eslint>=8.0.0, prettier>=3.0.0, typescript>=5.0.0]  # Cross-language!
  system: [git, python3, node]
```

### Example 5: Security Agent

```yaml
name: Security
agent_id: security-agent
agent_type: security
resource_tier: standard
category: quality                  # Classified under quality!
color: red                         # Distinct color for security
temperature: 0.0                   # Zero randomness for security
capabilities: { network_access: true }
dependencies: { python: [bandit>=1.7.5, detect-secrets>=1.4.0, semgrep>=1.0.0, ...] }
knowledge:
  domain_expertise: [OWASP, SQL injection, XSS, CSRF, XXE, ...]
  best_practices: [Input validation, secure auth flows, ...]
  constraints: []
```

### Example 6: MPM Agent Manager (system agent)

```yaml
name: mpm_agent_manager
agent_id: mpm-agent-manager
agent_type: system                 # System type (not user-facing)
category: claude-mpm               # MPM-specific category
color: purple
max_tokens: 16384
timeout: 1800
capabilities: { network_access: true }
dependencies: { python: [gitpython>=3.1.0, pyyaml>=6.0.0], system: [python3, git, gh] }
```

---

## 7. Gap Analysis: Rich Data Available vs. Currently Exposed

### 7.1 Fields Available But NOT Exposed via API

| Field | Available In | Missing From API | UI Value |
|-------|-------------|-----------------|----------|
| `color` | Frontmatter | Both endpoints | **HIGH** - Visual identification in agent cards/lists |
| `temperature` | Frontmatter | Both endpoints | **MEDIUM** - Shows agent "personality" (creative vs. precise) |
| `max_tokens` | Frontmatter | Both endpoints | **MEDIUM** - Shows response capacity |
| `timeout` | Frontmatter | Both endpoints | **MEDIUM** - Shows execution time limits |
| `capabilities.memory_limit` | Frontmatter | Both endpoints | **MEDIUM** - Resource requirements |
| `capabilities.cpu_limit` | Frontmatter | Both endpoints | **LOW** - Technical detail |
| `capabilities.network_access` | Frontmatter | Both endpoints | **HIGH** - Security-relevant: can it access internet? |
| `dependencies` | Frontmatter | Both endpoints | **HIGH** - What tools/packages needed |
| `skills` | Frontmatter | Both endpoints | **HIGH** - Shows skill relationships |
| `template_version` | Frontmatter | Both endpoints | **LOW** - Template tracking |
| `template_changelog` | Frontmatter | Both endpoints | **HIGH** - Shows evolution history |
| `knowledge.domain_expertise` | Frontmatter | Both endpoints | **HIGH** - What the agent knows |
| `knowledge.best_practices` | Frontmatter | Both endpoints | **MEDIUM** - How agent operates |
| `knowledge.constraints` | Frontmatter | Both endpoints | **HIGH** - Agent limitations |
| `interactions.handoff_agents` | Frontmatter | Both endpoints | **HIGH** - Agent relationships/graph |
| `interactions.output_format` | Frontmatter | Both endpoints | **MEDIUM** - Expected output type |
| `memory_routing` | Frontmatter | Both endpoints | **MEDIUM** - Memory behavior |
| `author` | Frontmatter | Available only | **LOW** - Attribution |
| `schema_version` | Frontmatter | Both endpoints | **LOW** - Technical compatibility |
| `resource_tier` | Frontmatter | Available only (partial) | **MEDIUM** - Resource classification |

### 7.2 DeployedAgent Gaps (Most Severe)

The deployed agents endpoint returns ONLY:
- `name`, `location`, `path`, `version`, `type`, `specializations`, `is_core`

Missing critical fields:
- **No description** - Users can't see what an agent does
- **No category** - Can't group/filter deployed agents
- **No tags** - Can't search deployed agents
- **No color** - Can't visually distinguish agents
- **No skills** - Can't see what skills are linked
- **No dependencies** - Can't see what's required
- **No knowledge/expertise** - Can't see agent capabilities

### 7.3 AvailableAgent Gaps (Moderate)

The available agents endpoint returns a reasonable set but misses:
- **No color** - Can't preview visual identity
- **No skills** - Can't see skill relationships before deploying
- **No dependencies** - Can't assess installation requirements
- **No knowledge** - Can't evaluate agent expertise
- **No template_changelog** - Can't see maturity/evolution
- **No temperature** - Can't assess agent behavior characteristics
- **No capabilities block** - Can't see resource requirements

### 7.4 Data Transformation Issues

1. **Inconsistent field naming**: Frontmatter uses `agent_id`, API promotes `name` from nested `metadata.name` to root level
2. **Metadata nesting**: Discovery returns metadata nested under `metadata` key; API endpoint manually promotes fields to root
3. **Missing enrichment**: Deployed agents don't get enriched with data from the source definition (they only report from the deployed .md file which may have been stripped)
4. **No cross-referencing**: Deployed agents don't cross-reference with available agents to fill in metadata gaps

---

## 8. Agent File Size Distribution

Based on file sizes, agents vary dramatically in complexity:

| Agent | File Size | Relative Complexity |
|-------|-----------|-------------------|
| research.md | 59,200 bytes | Extremely complex |
| mpm-skills-manager.md | 62,175 bytes | Extremely complex |
| python-engineer.md | 44,668 bytes | Very complex |
| java-engineer.md | 44,445 bytes | Very complex |
| web-ui.md | 33,624 bytes | Complex |
| product-owner.md | 33,599 bytes | Complex |
| security.md | 30,668 bytes | Complex |
| qa.md | 8,533 bytes | Moderate |
| phoenix-engineer.md | 3,454 bytes | Simple |
| prompt-engineer.md | 3,130 bytes | Simple |
| local-ops.md | 2,549 bytes | Minimal |

---

## 9. Value-Add Fields for UI Dashboard

### Tier 1: Must-Have for Agent Cards/Lists

1. **`color`** - Visual badge/indicator for quick identification
2. **`description`** (for deployed agents) - Currently missing entirely
3. **`category`** - Enable grouping and filtering
4. **`tags`** - Enable search/filter
5. **`skills`** count and list - Show skill relationships
6. **`network_access`** - Security indicator (icon: globe/locked)
7. **`resource_tier`** - Resource indicator (lightweight/standard/intensive)

### Tier 2: Detail View / Expanded Panel

8. **`knowledge.domain_expertise`** - Show what the agent knows
9. **`knowledge.constraints`** - Show agent limitations
10. **`dependencies`** - Show required tools/packages
11. **`interactions.handoff_agents`** - Show agent collaboration graph
12. **`temperature`** - Personality indicator (precise vs creative)
13. **`max_tokens`** / **`timeout`** - Performance characteristics
14. **`template_changelog`** - Maturity/evolution timeline

### Tier 3: Advanced/Power User

15. **`capabilities.memory_limit`** / **`cpu_limit`** - Resource details
16. **`interactions.output_format`** - Expected output type
17. **`memory_routing`** - Memory behavior
18. **`schema_version`** - Compatibility tracking
19. **`collection_id`** / **`canonical_id`** - Source traceability

---

## 10. Agent Relationship Patterns

### Handoff Graph (from `interactions.handoff_agents`)

```
QA ──handoff──> Engineer
QA ──handoff──> Security
(Other agents' handoff data needs to be extracted from agent body text)
```

### Skill-Agent Mapping (from `skills` field)

Common skills shared by most agents:
- `brainstorming` - 30+ agents
- `git-workflow` - 30+ agents
- `test-driven-development` - 30+ agents
- `systematic-debugging` - 25+ agents
- `dispatching-parallel-agents` - 25+ agents

Specialized skills:
- `dspy`, `langchain`, `mcp` - Python/Research only
- `vercel-overview` - Vercel Ops only
- `api-security-review` - Security only
- `playwright` - Web QA only

### Category Distribution

| Category | Count | Examples |
|----------|-------|---------|
| engineering | ~18 | python-engineer, react-engineer, rust-engineer |
| operations | ~8 | ops, vercel-ops, digitalocean-ops |
| quality | ~5 | qa, web-qa, api-qa, security |
| research | 1 | research |
| specialized | ~5 | documentation, imagemagick, content-agent |
| claude-mpm | ~3 | mpm-agent-manager, mpm-skills-manager |
| system | ~2 | agent-manager, skills-manager |

---

## 11. Recommendations for Dashboard UI

### A. Immediate: Enrich Both API Endpoints

**Deployed agents** need the most enrichment - cross-reference with source definitions to add:
- description, category, tags, color, skills, dependencies, knowledge

**Available agents** need moderate enrichment:
- color, skills count, dependencies summary, resource_tier, network_access

### B. Near-term: Agent Detail Panel

Create a rich detail view that shows:
- Full metadata with color-coded header
- Expertise areas (knowledge.domain_expertise)
- Skills list with deployment status
- Dependencies with installation status
- Changelog/version history
- Agent relationship graph (handoffs)

### C. Filtering and Search

Leverage the rich metadata for:
- Category filter (engineering, quality, operations, etc.)
- Tag-based search
- Resource tier filter (lightweight vs intensive)
- Network access filter (for security-conscious users)
- Skill-based discovery ("find agents that use pytest")

### D. Visual Differentiation

Use the `color` field already defined in agent definitions:
- Green: Most engineers
- Red: Security
- Purple: Research, MPM agents
- Orange: Ops
- Cyan: Documentation
- Black: Vercel Ops

---

## 12. Summary of Findings

1. **Agent definitions are rich** - 20+ metadata fields per agent, with deep knowledge, capability, and relationship data
2. **The API only exposes ~30% of available metadata** - Major gap between what's defined and what's served
3. **Deployed agents are severely under-described** - Missing description, category, tags, color, skills
4. **Relationship data exists but isn't surfaced** - Skills links, handoff agents, dependency chains
5. **The color field is universally defined** - Ready for immediate UI integration
6. **Agents vary dramatically in complexity** - From 2.5KB to 62KB, which should inform how detail views are structured
7. **Category hierarchy is well-structured** - Can directly map to navigation/grouping in UI
8. **Template changelog provides maturity signal** - Agents with many changelog entries are more battle-tested
