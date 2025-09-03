# Claude MPM Agent Development Guide

**Version**: 4.2.2  
**Last Updated**: September 2, 2025

Complete guide for creating, managing, and deploying AI agents in Claude MPM's three-tier system.

## Table of Contents

- [Quick Start](#quick-start)
- [Agent System Overview](#agent-system-overview)
- [Creating Agents](#creating-agents)
- [Agent Formats](#agent-formats)
- [Agent Management](#agent-management)
- [Deployment System](#deployment-system)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

## Quick Start

### Create Your First Project Agent (3 steps)

```bash
# 1. Create project agents directory
mkdir -p .claude-mpm/agents

# 2. Create a custom engineer agent
cat > .claude-mpm/agents/engineer.md << 'EOF'
---
description: Custom engineer for this project
version: 2.0.0
tools: ["project_linter", "custom_debugger"]
model: claude-sonnet-4-20250514
---

# Project Engineer Agent

You are an expert software engineer with deep knowledge of this project's:
- Architecture: Microservices with event sourcing
- Stack: Python, PostgreSQL, Redis
- Standards: >90% test coverage required
- Tools: Custom logging framework

## Project-Specific Guidelines

- Always use our logging: `from project.utils import logger`
- Follow structured exception patterns
- Run `./scripts/validate.py` before code changes
- All database operations must use transactions

## Testing Requirements

- Unit tests for all business logic
- Integration tests for service boundaries  
- Performance tests for critical paths
EOF

# 3. Deploy and verify
./scripts/claude-mpm agents deploy
./scripts/claude-mpm agents list --by-tier
```

### Verify Agent Hierarchy

```bash
# Check which version is active
./scripts/claude-mpm agents list --by-tier

# View specific agent details
./scripts/claude-mpm agents view engineer
```

## Agent System Overview

### Three-Tier Precedence System

Claude MPM uses a hierarchical system where higher tiers override lower ones:

**PROJECT** > **USER** > **SYSTEM**

#### 1. PROJECT Tier (Highest Precedence)
- **Source**: `.claude-mpm/agents/` in project directory
- **Deploy**: `.claude/agents/` in project directory
- **Purpose**: Project-specific agents and customizations
- **Formats**: `.md`, `.json`, `.yaml`

#### 2. USER Tier (Medium Precedence)  
- **Source**: `~/.claude-mpm/agents/` in user home
- **Deploy**: `.claude/agents/` in project directory
- **Purpose**: User preferences across projects
- **Formats**: `.md`, `.json`, `.yaml`

#### 3. SYSTEM Tier (Lowest Precedence)
- **Source**: Built-in framework agents
- **Deploy**: `.claude/agents/` in project directory  
- **Purpose**: Default framework behaviors
- **Formats**: `.json` (framework managed)

### Available Agents (15 specialists)

**Core Development:**
- `engineer` - Software development and implementation
- `research` - Code analysis and research with AST parsing
- `documentation` - Documentation creation and maintenance
- `qa` - Testing and quality assurance
- `security` - Security analysis and implementation

**Operations:**
- `ops` - Deployment and operations with git commit authority
- `version_control` - Git and version management  
- `data_engineer` - Data pipeline and ETL development

**Web Development:**
- `web_ui` - Frontend and UI development
- `web_qa` - Web testing and E2E validation

**Project Management:**
- `ticketing` - Issue tracking and management
- `project_organizer` - File organization and structure
- `memory_manager` - Project memory and context management

**Code Quality:**
- `refactoring_engineer` - Code refactoring and optimization
- `code_analyzer` - Static analysis with Mermaid visualization

### Deployment Changes (v4.0.32+)

**All agents now deploy to project directory:**
- Before: System/User agents → `~/.claude/agents/`
- After: All agents → `<project>/.claude/agents/`

**Benefits:**
- Consistent agent location per project
- Project isolation (no home directory pollution)
- Portable agent environments
- Simplified debugging and management

## Creating Agents

### Markdown Format (Recommended)

Best for human-readable agents with rich formatting:

```markdown
---
description: Short description
version: 2.0.0
tools: ["tool1", "tool2"]
model: claude-sonnet-4-20250514
specializations: ["python", "testing"]
resource_tier: intensive
---

# Agent Name

Detailed instructions in markdown with full formatting support.

## Specialized Knowledge

- Domain expertise 1
- Domain expertise 2
- Project-specific patterns

## Guidelines

1. Always follow project conventions
2. Validate before suggesting changes  
3. Use project-specific tools and frameworks

## Examples

```python
# Project-specific code example
from project.core import BaseHandler

class MyHandler(BaseHandler):
    def handle(self, request):
        return self.validate_and_process(request)
```

## Quality Standards

- Test coverage >90%
- All public APIs documented
- Performance benchmarks included
```

### JSON Format (Advanced Configuration)

Best for complex configurations and metadata:

```json
{
  "agent_id": "payment_processor",
  "version": "2.0.0",
  "metadata": {
    "name": "Payment Processing Agent",
    "description": "Specialized agent for payment workflows",
    "category": "domain-specific",
    "tags": ["payments", "fintech", "compliance"]
  },
  "capabilities": {
    "model": "claude-sonnet-4-20250514",
    "resource_tier": "standard",
    "tools": ["payment_validator", "compliance_checker", "fraud_detector"],
    "features": ["multi_currency", "pci_compliance", "audit_trail"]
  },
  "knowledge": {
    "domains": ["payments", "financial_regulations", "security"],
    "frameworks": ["stripe", "paypal", "square"],
    "compliance": ["PCI_DSS", "PSD2", "GDPR"]
  },
  "interactions": {
    "tone": "professional", 
    "verbosity": "detailed",
    "code_style": "defensive"
  },
  "dependencies": {
    "python": ["stripe>=5.0.0", "cryptography>=3.0.0"],
    "system": ["git", "openssl"],
    "optional": false
  },
  "instructions": "# Payment Processing Agent\n\nYou are a specialist in payment processing...\n\n## Security Requirements\n\n- All payment data must be tokenized\n- Log all transactions for audit\n- Validate PCI compliance before code changes\n\n## Implementation Guidelines\n\n- Use defensive coding patterns\n- Encrypt all stored payment tokens\n- Never log sensitive payment data"
}
```

### YAML Format (Configuration-Heavy)

Best for structured configurations:

```yaml
agent_id: devops_specialist
version: "2.0.0"
metadata:
  name: DevOps Specialist Agent
  description: Kubernetes and cloud infrastructure expert
  category: operations
  tags:
    - devops
    - kubernetes
    - monitoring

capabilities:
  model: claude-sonnet-4-20250514
  resource_tier: intensive
  tools:
    - kubectl
    - terraform
    - prometheus
    - grafana
  features:
    - cluster_management
    - auto_scaling
    - monitoring

knowledge:
  platforms:
    - kubernetes
    - aws
    - gcp
    - azure
  monitoring:
    - prometheus
    - grafana
    - elk_stack

dependencies:
  python:
    - kubernetes>=25.0.0
    - boto3>=1.26.0
  system:
    - kubectl
    - terraform
    - helm
  optional: false

instructions: |
  # DevOps Specialist Agent
  
  You are an expert in cloud-native infrastructure and deployment.
  
  ## Primary Responsibilities
  
  - Kubernetes cluster management
  - CI/CD pipeline optimization
  - Infrastructure as code (Terraform)
  - Monitoring and observability
  
  ## Guidelines
  
  - Always use infrastructure as code
  - Implement monitoring for all services
  - Follow security best practices
  - Ensure high availability and scalability
```

## Agent Formats

### Format Comparison

| Format | Best For | Pros | Cons |
|--------|----------|------|------|
| **Markdown (.md)** | Human-readable agents | Rich formatting, easy to edit | Limited metadata structure |
| **JSON (.json)** | Complex configurations | Full metadata support | Verbose, harder to read |
| **YAML (.yaml/.yml)** | Configuration-heavy | Clean structure, comments | YAML syntax sensitivity |

### Field Reference

#### Required Fields

- `version`: Semantic version (e.g., "2.0.0")
- `description`: Short description of agent purpose
- `instructions`: Full agent instructions (embedded or via frontmatter)

#### Common Optional Fields

- `model`: Preferred Claude model (claude-sonnet-4-20250514, claude-opus-4-20250514, etc.)
- `tools`: Array of available tools/integrations
- `resource_tier`: Performance tier (lightweight, standard, intensive)
- `specializations`: Array of domain specialties
- `dependencies`: Python packages and system requirements

#### Advanced Fields

- `metadata`: Extended information (name, category, tags, author)
- `capabilities`: Model preferences, features, max concurrent tasks
- `knowledge`: Domain expertise, frameworks, compliance requirements
- `interactions`: Tone, verbosity, code style preferences

### Format Detection

Claude MPM automatically detects agent format:

1. **File Extension**: `.md`, `.json`, `.yaml`, `.yml`
2. **Content Analysis**: Frontmatter presence, JSON/YAML validation
3. **Schema Validation**: Ensures compliance with agent schema

## Agent Management

### CLI Commands

#### List Agents by Tier

```bash
./scripts/claude-mpm agents list --by-tier
```

**Output:**
```
================================================================================
                         AGENT HIERARCHY BY TIER
================================================================================

─────────────────────────── PROJECT TIER ───────────────────────────
  Location: .claude-mpm/agents/

  📄 engineer             [✓ ACTIVE]
     Description: Custom engineer for this project
     File: engineer.md
     Model: claude-sonnet-4-20250514

  📄 payment_processor    [✓ ACTIVE] 
     Description: Payment processing specialist
     File: payment_processor.json
     Tools: payment_validator, compliance_checker

─────────────────────────── USER TIER ───────────────────────────
  Location: ~/.claude-mpm/agents/

  📄 research_agent       [✓ ACTIVE]
     Description: Enhanced research with tree-sitter
     File: research_agent.yaml

─────────────────────────── SYSTEM TIER ───────────────────────────
  Location: Built-in framework agents

  📄 engineer             [⊗ OVERRIDDEN by PROJECT]
     Description: Software engineering specialist
  
  📄 qa                   [✓ ACTIVE]
     Description: Quality assurance specialist
```

#### View Agent Details

```bash
./scripts/claude-mpm agents view engineer
```

**Output:**
```
================================================================================
 AGENT: engineer
================================================================================

📋 BASIC INFORMATION:
  Name: engineer
  Tier: PROJECT
  Path: .claude-mpm/agents/engineer.md
  Description: Custom engineer for this project
  Version: 2.0.0

📝 FRONTMATTER:
  model: claude-sonnet-4-20250514
  tools: [project_linter, custom_debugger]
  specializations: [python, microservices, testing]
  resource_tier: intensive

📖 INSTRUCTIONS PREVIEW (first 500 chars):
  # Project Engineer Agent
  
  You are an expert software engineer with deep knowledge...
  [Truncated - 2.3KB total]

📊 FILE STATS:
  Size: 2,347 bytes
  Last modified: 2025-09-02 14:32:45
```

#### Fix Agent Issues

```bash
# Preview fixes
./scripts/claude-mpm agents fix engineer --dry-run

# Apply fixes
./scripts/claude-mpm agents fix engineer

# Fix all agents
./scripts/claude-mpm agents fix --all
```

**Common Fixes:**
- Add missing required fields (version, description)
- Convert incorrect field formats (string to array)
- Standardize field names (desc → description)
- Remove invalid fields

### Agent Dependencies

Declare Python packages and system requirements:

```json
{
  "agent_id": "data_analyst",
  "dependencies": {
    "python": [
      "pandas>=2.0.0",
      "numpy>=1.24.0", 
      "matplotlib>=3.7.0",
      "jupyter>=1.0.0"
    ],
    "system": ["git", "ripgrep"],
    "optional": false
  }
}
```

**Installation:**
```bash
# Install with agent dependencies
pip install "claude-mpm[agents]"

# View aggregated dependencies
python scripts/aggregate_agent_dependencies.py --dry-run
```

## Deployment System

### Deployment Process (v4.0.32+)

All agents deploy to project-level `.claude/agents/` directory:

```bash
# Deploy all agents from all tiers
./scripts/claude-mpm agents deploy

# Force redeploy (ignores version checks)
./scripts/claude-mpm agents force-deploy

# Deploy to specific target
./scripts/claude-mpm agents deploy --target /path/to/project
```

### Deployment Flow

1. **Discovery**: Scan PROJECT, USER, SYSTEM tiers
2. **Precedence Resolution**: Higher tiers override lower tiers
3. **Format Conversion**: Convert all formats to Markdown with YAML frontmatter
4. **Validation**: Ensure schema compliance
5. **Deployment**: Write to `.claude/agents/` for Claude Code compatibility
6. **Cleanup**: Remove outdated user agents automatically

### Automatic Cleanup (v4.0.32+)

Outdated user agents are automatically removed during deployment:

```bash
INFO: Removing outdated user agent: engineer v1.8.0 (superseded by project v2.5.0)
INFO: Cleanup complete: removed 2 outdated user agents
```

**Disable cleanup:**
```bash
export CLAUDE_MPM_CLEANUP_USER_AGENTS=false
```

### Project Isolation

Each project maintains isolated agent environment:

```
project-a/.claude/agents/    # Project A agents
project-b/.claude/agents/    # Project B agents (independent)
```

**Benefits:**
- No cross-project contamination
- Version consistency per project
- Team collaboration simplified
- Easy project onboarding

## Best Practices

### 1. Agent Design

**Single Responsibility:**
```markdown
# Good: Focused agent
---
description: Payment processing specialist
---
# Payment Processor Agent
Expert in payment workflows, compliance, and fraud detection.

# Avoid: Generic catch-all agent  
---
description: Does everything agent
---
# Universal Agent
Handles payments, deployment, testing, documentation...
```

**Project-Specific Knowledge:**
```markdown
---
description: Engineer for microservices architecture
---
# Project Engineer

## Architecture Knowledge
- Event sourcing patterns with CQRS
- Service mesh communication (Istio)
- Distributed tracing with Jaeger

## Project Standards
- All services must implement health checks
- Use structured logging with correlation IDs
- Database migrations via Flyway
```

### 2. Version Management

Use semantic versioning:

```json
{
  "version": "2.1.0",  // Major.Minor.Patch
  "metadata": {
    "changelog": "Added payment processing capabilities"
  }
}
```

**Version Strategy:**
- **Major**: Breaking changes to agent behavior
- **Minor**: New capabilities or significant improvements
- **Patch**: Bug fixes and small refinements

### 3. Testing Agents

Test before deployment:

```bash
# Validate agent syntax
./scripts/claude-mpm agents fix my_agent --dry-run

# Test loading
python -c "
from claude_mpm.agents.agent_loader import get_agent_prompt
try:
    prompt = get_agent_prompt('my_agent')
    print('✅ Agent loaded successfully')
    print(f'Prompt length: {len(prompt)} characters')
except Exception as e:
    print(f'❌ Agent failed to load: {e}')
"

# Verify deployment
./scripts/claude-mpm agents deploy
./scripts/claude-mpm agents list --deployed
```

### 4. Documentation

Document your project agents:

```markdown
# Project Agents Documentation

## engineer.md
- **Purpose**: Project-specific engineering knowledge
- **Overrides**: System engineer agent
- **Specializations**: Microservices, Python, testing
- **Tools**: project_linter, custom_debugger

## payment_processor.json  
- **Purpose**: Payment workflow specialist
- **Dependencies**: stripe>=5.0.0, cryptography>=3.0.0
- **Compliance**: PCI_DSS, PSD2, GDPR
- **Features**: Multi-currency, fraud detection
```

### 5. Security Considerations

**Sensitive Data:**
```json
{
  "instructions": "Never log API keys or payment data. Use environment variables for secrets: process.env.STRIPE_SECRET_KEY"
}
```

**Access Control:**
```json
{
  "capabilities": {
    "tools": ["read_only_tools"],  // Limit tool access
    "resource_tier": "standard"     // Appropriate resources
  }
}
```

### 6. Performance Optimization

**Resource Tiers:**
```json
{
  "capabilities": {
    "resource_tier": "intensive",    // High-complexity tasks
    "model": "claude-opus-4-20250514"  // Most capable model
  }
}
```

**Caching Strategy:**
- Agents are cached for 1 hour by default
- Cache invalidates on file changes
- Use appropriate TTL for your use case

## Troubleshooting

### Common Issues

#### Agent Not Found

**Problem**: `ValueError: No agent found with name: my_agent`

**Solutions:**
```bash
# Check hierarchy and availability
./scripts/claude-mpm agents list --by-tier

# Verify file exists and has correct name
ls -la .claude-mpm/agents/my_agent.*

# Check for configuration issues
./scripts/claude-mpm agents fix my_agent --dry-run
```

#### Wrong Version Loading

**Problem**: System agent loads instead of project agent

**Solutions:**
```bash  
# Check tier precedence
./scripts/claude-mpm agents list --by-tier

# Verify project agent file naming
ls -la .claude-mpm/agents/

# View which tier is actually loading
./scripts/claude-mpm agents view my_agent
```

#### Schema Validation Errors

**Problem**: Agent behaves unexpectedly

**Solutions:**
```bash
# Fix frontmatter issues automatically
./scripts/claude-mpm agents fix --all --dry-run
./scripts/claude-mpm agents fix --all

# View agent configuration
./scripts/claude-mpm agents view my_agent

# Validate all agents
./scripts/claude-mpm agents list --by-tier
```

#### Cache Issues

**Problem**: Changes not reflected

**Solutions:**
```bash
# Clear specific agent cache
python -c "
from claude_mpm.agents.agent_loader import clear_agent_cache
clear_agent_cache('my_agent')"

# Clear all caches and reload
python -c "
from claude_mpm.agents.agent_loader import reload_agents
reload_agents()"
```

### Debugging Tools

#### Agent Inspector

```python
from claude_mpm.agents.agent_loader import _get_loader

def inspect_agent(name):
    loader = _get_loader()
    agent = loader.get_agent(name)
    if agent:
        print(f"Agent: {name}")
        print(f"Tier: {agent.get('_tier', 'unknown')}")
        print(f"Version: {agent.get('version', 'unknown')}")
        print(f"Model: {agent.get('capabilities', {}).get('model', 'default')}")
    else:
        print(f"Agent '{name}' not found")

inspect_agent("engineer")
```

#### Performance Metrics

```python
from claude_mpm.agents.agent_loader import _get_loader

loader = _get_loader()
metrics = loader.get_metrics()
print(f"Cache hit rate: {metrics['cache_hit_rate_percent']:.1f}%")
print(f"Average load time: {metrics['average_load_time_ms']:.1f}ms")
print(f"Agents loaded: {metrics['agents_loaded']}")
```

### Getting Help

1. **Check Logs**: Look in `.claude-mpm/logs/` for detailed errors
2. **Enable Debug**: Set `CLAUDE_MPM_LOG_LEVEL=DEBUG`  
3. **Validate Environment**: Ensure dependencies are installed
4. **Create Minimal Test**: Isolate issue with simple agent
5. **Report Issues**: Include system info and error details

---

## Related Documentation

- [ARCHITECTURE.md](ARCHITECTURE.md) - System architecture and service layer
- [DEVELOPMENT.md](DEVELOPMENT.md) - Development workflows and patterns
- [API.md](API.md) - API reference documentation
- [DEPLOYMENT.md](DEPLOYMENT.md) - Operations and deployment procedures