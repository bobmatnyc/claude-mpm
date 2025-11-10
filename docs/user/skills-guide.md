---
title: Skills System User Guide
version: 1.0.0
last_updated: 2025-11-10
status: current
---

# Skills System User Guide

Complete guide to using and managing skills in Claude MPM.

## Table of Contents

- [Overview](#overview)
- [What Are Skills?](#what-are-skills)
- [Using Bundled Skills](#using-bundled-skills)
- [Skills Catalog](#skills-catalog)
- [Managing Skills](#managing-skills)
- [Creating Custom Skills](#creating-custom-skills)
- [Skills Versioning](#skills-versioning)
- [Skills Configuration](#skills-configuration)
- [Troubleshooting](#troubleshooting)
- [Best Practices](#best-practices)
- [Advanced Topics](#advanced-topics)

## Overview

### What Are Skills?

Skills are reusable knowledge modules that enhance agent capabilities with specialized expertise. Think of them as expert consultants that agents can call upon for specific domains:

- **Bundled Skills**: 17 production-ready skills included with Claude MPM
- **Custom Skills**: Your own project-specific or personal expertise modules
- **Auto-Linking**: Intelligent automatic mapping of skills to compatible agents
- **Three-Tier System**: Organized hierarchy (bundled → user → project)

**Key Benefits:**
- **Eliminate Redundancy**: Share common patterns across multiple agents (~15,000 lines of reusable content)
- **Domain Expertise**: Provide deep knowledge in specific areas (MCP development, testing, debugging)
- **Consistency**: Ensure all agents follow the same best practices
- **Maintainability**: Update expertise in one place, benefits all agents
- **Discoverability**: Rich metadata makes finding the right skill easy

### When to Use Skills vs Agents

**Use Skills When:**
- You need specialized domain knowledge (e.g., "how to build MCP servers")
- Knowledge applies across multiple agents or projects
- Expertise needs regular updates and maintenance
- You want to share patterns and best practices

**Use Agents When:**
- You need a complete workflow executor (e.g., "engineer" that writes code)
- Task requires orchestration of multiple tools and decisions
- You need persistent context and state management
- Role encompasses multiple skills

**Example:** The "engineer" agent uses the "test-driven-development" skill, "git-workflow" skill, and "systematic-debugging" skill to perform its work.

### Version Support

Skills versioning introduced in **v4.15.0**. See [Skills Versioning](#skills-versioning) section for details.

---

## Using Bundled Skills

### Quick Start

Skills are automatically available once Claude MPM is installed. To use them:

1. **Access Skills Management:**
   ```bash
   claude-mpm configure
   # Select option [2] Skills Management
   ```

2. **View Available Skills:**
   ```bash
   # In Skills Management menu
   # Select option [1] View bundled skills
   ```
   This displays all 17 bundled skills with descriptions and categories.

3. **Auto-Link Skills (Recommended):**
   ```bash
   # In Skills Management menu
   # Select option [4] Auto-link skills to agents
   ```
   This intelligently maps skills to compatible agents based on agent type.

### How Auto-Linking Works

Auto-linking analyzes your agents and assigns appropriate skills:

**Core Development Skills → Engineer/Research Agents:**
- `test-driven-development` → Engineer, QA
- `systematic-debugging` → Engineer, Research
- `verification-before-completion` → All development agents

**Collaboration Skills → All Agents:**
- `writing-plans` → Project Manager, Engineer
- `brainstorming` → Research, Documentation
- `requesting-code-review` → Engineer, QA

**Language-Specific Skills → Matching Agents:**
- `rust/desktop-applications` → Rust Engineer
- `php/espocrm-development` → PHP Engineer

**Framework Skills → Project-Detected Agents:**
- Skills for detected frameworks automatically linked when using `claude-mpm auto-configure`

### Manual Skill Assignment

For fine-grained control, manually assign skills to specific agents:

```bash
# In Skills Management menu
# Select option [2] Select skills for an agent
# 1. Choose agent from list
# 2. Select skills to assign (multi-select with space)
# 3. Confirm selection
```

**Example Workflow:**
```bash
claude-mpm configure
# → [2] Skills Management
# → [2] Select skills for an agent
# → Select "engineer"
# → Select: [x] test-driven-development
#          [x] systematic-debugging
#          [x] mcp-builder
# → Confirm
```

Configuration is saved to `.claude-mpm/config.yaml`:

```yaml
skills:
  assignments:
    engineer:
      - test-driven-development
      - systematic-debugging
      - mcp-builder
    qa:
      - test-driven-development
      - testing-anti-patterns
      - webapp-testing
```

### Invoking Skills in Claude Code

Once skills are assigned to agents, they're automatically available. Skills use **progressive disclosure** - agents read skills incrementally to optimize context:

1. **Initial Scan**: Agent reads SKILL.md entry point (~30-50 tokens)
2. **On-Demand Loading**: Agent loads specific reference files when needed
3. **Context Efficiency**: 85% reduction in initial context loading

**You don't need to do anything special** - agents automatically load skills when relevant to the task.

---

## Skills Catalog

### Main Skills (Core Functionality)

#### mcp-builder
**Category:** Development
**Description:** Create high-quality MCP servers that enable LLMs to effectively interact with external services.

**When to Use:**
- Building MCP servers for external API integration
- Adding tools to existing MCP servers
- Creating evaluations to test MCP server effectiveness

**Key Features:**
- Research-driven planning (40% of effort)
- Agent-centric design principles
- Python (FastMCP) and TypeScript (MCP SDK) support
- Comprehensive evaluation framework

**References:**
- Design principles and workflow
- Language-specific implementation guides
- MCP best practices and patterns
- Evaluation and testing strategies

---

#### skill-creator
**Category:** Development
**Description:** Create high-quality, maintainable skills following progressive disclosure patterns.

**When to Use:**
- Creating new skills for personal or project use
- Refactoring existing skills for better organization
- Understanding skill format and best practices

**Key Features:**
- Progressive disclosure organization
- SKILL.md format specification (16 validation rules)
- Reference file organization strategies
- Validation and quality checklist

**References:**
- Format specification and examples
- Best practices and anti-patterns
- Progressive disclosure patterns
- Meta-skill considerations

---

#### artifacts-builder
**Category:** Development
**Description:** Build interactive artifacts (React components, diagrams, documents) for Claude AI.

**When to Use:**
- Creating interactive visualizations or tools
- Building React components for data presentation
- Generating diagrams (Mermaid) or documents

**Key Features:**
- React component patterns
- Mermaid diagram syntax
- SVG and interactive elements
- Best practices for artifact design

---

#### internal-comms
**Category:** Collaboration
**Description:** Structured communication patterns for agent-to-agent and agent-to-user interactions.

**When to Use:**
- Multi-agent workflows requiring coordination
- Standardizing communication formats
- Improving clarity in complex interactions

**Key Features:**
- Message format specifications
- Communication protocols
- Handoff patterns
- Status reporting templates

---

### Collaboration Skills

#### brainstorming
**Category:** Collaboration
**Description:** Structured brainstorming techniques for idea generation and problem-solving.

**When to Use:**
- Exploring solution spaces
- Generating creative alternatives
- Problem decomposition

**Key Techniques:**
- Divergent thinking patterns
- Idea categorization
- Evaluation frameworks
- Convergence strategies

---

#### writing-plans
**Category:** Collaboration
**Description:** Create clear, actionable plans for complex technical work.

**When to Use:**
- Starting new features or refactorings
- Breaking down large projects
- Communicating technical approaches

**Key Patterns:**
- Plan structure templates
- Task breakdown strategies
- Timeline estimation
- Risk identification

---

#### requesting-code-review
**Category:** Collaboration
**Description:** Prepare effective code review requests with clear context and guidance.

**When to Use:**
- Submitting code for review
- Providing review context
- Highlighting areas of concern

**Key Elements:**
- Review request templates
- Context documentation
- Testing evidence
- Areas for reviewer focus

---

#### dispatching-parallel-agents
**Category:** Collaboration
**Description:** Coordinate multiple agents working on independent tasks simultaneously.

**When to Use:**
- Tasks can be parallelized
- Multiple independent subtasks
- Time-critical deliverables

**Key Patterns:**
- Task decomposition for parallelism
- Agent assignment strategies
- Result aggregation
- Conflict resolution

---

### Testing Skills

#### test-driven-development
**Category:** Testing
**Description:** TDD principles, red-green-refactor cycle, and test-first development practices.

**When to Use:**
- Implementing new features
- Refactoring existing code
- Ensuring comprehensive test coverage

**Key Practices:**
- Red-Green-Refactor cycle
- Test case design
- Mocking and stubbing
- Test organization

---

#### testing-anti-patterns
**Category:** Testing
**Description:** Recognize and avoid common testing mistakes and bad practices.

**When to Use:**
- Reviewing test code quality
- Debugging flaky tests
- Improving test maintainability

**Common Anti-Patterns:**
- Brittle tests
- Test interdependence
- Over-mocking
- Unclear assertions

---

#### webapp-testing
**Category:** Testing
**Description:** Comprehensive web application testing strategies (unit, integration, E2E).

**When to Use:**
- Testing web applications
- Setting up testing infrastructure
- Creating comprehensive test suites

**Coverage:**
- Unit testing components
- Integration testing APIs
- E2E testing workflows
- Browser automation

---

#### condition-based-waiting
**Category:** Testing
**Description:** Wait for conditions to be met in tests rather than using arbitrary delays.

**When to Use:**
- Testing async operations
- Waiting for UI state changes
- Integration testing with timing dependencies

**Key Patterns:**
- Polling strategies
- Timeout handling
- Condition predicates
- Retry mechanisms

---

### Debugging Skills

#### systematic-debugging
**Category:** Debugging
**Description:** Scientific method applied to debugging: hypothesize, test, eliminate causes.

**When to Use:**
- Investigating complex bugs
- Understanding system behavior
- Root cause analysis

**Key Process:**
- Reproduce reliably
- Form hypotheses
- Design experiments
- Eliminate causes systematically
- Document findings

---

#### root-cause-tracing
**Category:** Debugging
**Description:** Trace issues back to their fundamental causes, not just symptoms.

**When to Use:**
- Recurring issues
- Complex system failures
- Performance problems

**Techniques:**
- 5 Whys analysis
- Dependency tracing
- Timeline reconstruction
- Evidence gathering

---

#### verification-before-completion
**Category:** Debugging
**Description:** Always verify your work before marking tasks complete.

**When to Use:**
- Before committing code
- Before marking tasks done
- Before claiming "it works"

**Verification Steps:**
- Tests pass
- Build succeeds
- Manual testing
- Documentation updated

---

### Language-Specific Skills

#### rust/desktop-applications
**Category:** Language-Specific (Rust)
**Description:** Build native desktop applications using Rust and Tauri/Slint frameworks.

**When to Use:**
- Building cross-platform desktop apps
- Native performance requirements
- Rust-based UI development

**Key Topics:**
- Tauri framework patterns
- Slint UI framework
- Native integrations
- Build and distribution

---

#### php/espocrm-development
**Category:** Language-Specific (PHP)
**Description:** Develop extensions and customizations for EspoCRM platform.

**When to Use:**
- EspoCRM development
- PHP CRM customization
- Business application development

**Key Topics:**
- EspoCRM architecture
- Entity customization
- Hook system
- Module development

---

### Accessing Individual Skills

**View Skill Details:**
```bash
# Skills are stored in:
# Bundled: <python-site-packages>/claude_mpm/skills/bundled/
# User: ~/.claude/skills/
# Project: .claude/skills/

# Read a skill directly:
cat ~/.local/share/python/site-packages/claude_mpm/skills/bundled/main/mcp-builder/SKILL.md
```

**Or browse via Skills Management:**
```bash
claude-mpm configure
# → [2] Skills Management
# → [1] View bundled skills
# → Select skill to view full details
```

---

## Managing Skills

### Three-Tier Skills System

Claude MPM organizes skills in a three-tier hierarchy with priority override:

```
PROJECT SKILLS (.claude/skills/)
    ↓ overrides
USER SKILLS (~/.claude/skills/)
    ↓ overrides
BUNDLED SKILLS (system installation)
```

**Priority Rules:**
- Project skills override user and bundled skills with the same name
- User skills override bundled skills
- Bundled skills are the fallback

**Example:**
```bash
# You can override bundled "test-driven-development" skill
# by creating your own version:
mkdir -p .claude/skills
cat > .claude/skills/test-driven-development.md << 'EOF'
---
name: test-driven-development
version: 2.0.0
description: Custom TDD approach for this project
---

# Custom Test-Driven Development

Our project-specific TDD workflow...
EOF
```

### Skills Discovery

Skills are automatically discovered when Claude MPM starts:

1. **Scans bundled skills** in installation directory
2. **Scans user skills** in `~/.claude/skills/`
3. **Scans project skills** in `.claude/skills/`
4. **Merges with priority**: PROJECT > USER > BUNDLED

**Force Refresh:**
```bash
# Restart Claude Code session to pick up new skills
# Or reload configuration:
claude-mpm configure
# → [2] Skills Management
# → [5] Reload skills
```

### Listing All Available Skills

**Via CLI:**
```bash
# View all skills and their sources
claude-mpm configure
# → [2] Skills Management
# → [1] View bundled skills
# → [6] View user skills
# → [7] View project skills
```

**Via File System:**
```bash
# List bundled skills
ls -la $(python -c "import claude_mpm.skills.bundled; import os; print(os.path.dirname(claude_mpm.skills.bundled.__file__))")

# List user skills
ls -la ~/.claude/skills/

# List project skills
ls -la .claude/skills/
```

### Unassigning Skills

**Remove skill from specific agent:**
```bash
claude-mpm configure
# → [2] Skills Management
# → [2] Select skills for an agent
# → Choose agent
# → Deselect skills (uncheck with space)
# → Confirm
```

**Or edit configuration directly:**
```bash
# Edit .claude-mpm/config.yaml
nano .claude-mpm/config.yaml

# Remove skills from assignments:
skills:
  assignments:
    engineer:
      - test-driven-development
      # Remove lines for skills you don't want
```

---

## Creating Custom Skills

### Basic Custom Skill

Create a simple custom skill in your project:

```bash
# Create skills directory
mkdir -p .claude/skills

# Create a basic skill
cat > .claude/skills/my-api-patterns.md << 'EOF'
---
name: my-api-patterns
description: Project-specific API development patterns and conventions
version: 1.0.0
category: development
---

# Project API Patterns

## REST API Standards

All REST endpoints in this project follow these conventions:

### Request Format
- Use JSON for request bodies
- Include `Content-Type: application/json` header
- Validate input with Pydantic models

### Response Format
```json
{
  "success": true,
  "data": {...},
  "metadata": {
    "timestamp": "2025-11-10T12:00:00Z",
    "version": "1.0"
  }
}
```

### Error Handling
- Use appropriate HTTP status codes
- Return structured error responses
- Include error codes and messages

## Authentication
- All endpoints require JWT authentication
- Token in `Authorization: Bearer <token>` header
- Refresh tokens before expiry

## Examples

### Creating a Resource
```python
@router.post("/api/resources")
async def create_resource(data: ResourceCreate, user: User = Depends(get_current_user)):
    """Create a new resource."""
    try:
        resource = await resource_service.create(data, user)
        return {"success": True, "data": resource.dict()}
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
```

EOF
```

**Assign to agent:**
```bash
claude-mpm configure
# → [2] Skills Management
# → [2] Select skills for an agent
# → Choose "engineer"
# → Select [x] my-api-patterns
# → Confirm
```

### Advanced: Progressive Disclosure Skill

For more sophisticated skills with reference files:

```bash
# Create skill directory structure
mkdir -p .claude/skills/my-framework-patterns/{references,scripts}

# Create entry point
cat > .claude/skills/my-framework-patterns/SKILL.md << 'EOF'
---
name: my-framework-patterns
description: Framework-specific patterns and best practices
version: 1.0.0
category: development
progressive_disclosure:
  entry_point:
    summary: "Core framework patterns for consistent development"
    when_to_use: "When implementing features using our custom framework"
    quick_start: "1. Review patterns 2. Apply to feature 3. Test thoroughly"
  references:
    - patterns.md
    - examples.md
    - anti-patterns.md
---

# Framework Patterns

## Overview

This skill provides framework-specific patterns and conventions.

## When to Use

- Implementing new features
- Refactoring existing code
- Code review

## Quick Start

1. Review [patterns.md](./references/patterns.md) for approved patterns
2. Check [examples.md](./references/examples.md) for usage examples
3. Avoid [anti-patterns.md](./references/anti-patterns.md)

## Navigation

- **[📋 Patterns](./references/patterns.md)** - Approved architectural patterns
- **[💡 Examples](./references/examples.md)** - Real-world usage examples
- **[⚠️ Anti-Patterns](./references/anti-patterns.md)** - Common mistakes to avoid
EOF

# Create reference files
cat > .claude/skills/my-framework-patterns/references/patterns.md << 'EOF'
# Framework Patterns

## Service Layer Pattern

All business logic lives in service classes...

[150-300 lines of detailed patterns]
EOF

cat > .claude/skills/my-framework-patterns/references/examples.md << 'EOF'
# Pattern Examples

## Service Layer Example

```python
class UserService:
    def __init__(self, db: Database):
        self.db = db

    async def create_user(self, data: UserCreate) -> User:
        ...
```

[150-300 lines of examples]
EOF
```

**Best Practices for Custom Skills:**
- Keep entry point (SKILL.md) under 200 lines
- Move details to reference files (150-300 lines each)
- Use clear navigation with links
- Include when_to_use guidance
- Provide concrete examples
- Version your skills

### Skill Format Specification

For detailed format requirements, see:
- **[SKILL.md Format Specification](/Users/masa/Projects/claude-mpm/docs/design/SKILL-MD-FORMAT-SPECIFICATION.md)** - Complete format specification
- **skill-creator skill** - Use the bundled skill-creator skill for guided skill creation

**Key Requirements:**
1. YAML frontmatter with metadata
2. Entry point under 200 lines
3. Progressive disclosure organization
4. Reference files 150-300 lines
5. Clear navigation section
6. When to use guidance
7. Concrete examples

---

## Skills Versioning

Skills support semantic versioning to track evolution and maintain compatibility.

### Version Format

Skills use **semantic versioning (SemVer)**:

```
MAJOR.MINOR.PATCH
  │     │     │
  │     │     └─ Bug fixes, typos, minor clarifications
  │     └─────── New features, additional guidance
  └───────────── Breaking changes, major rewrites
```

**Examples:**
- `0.1.0` - Initial version (development)
- `1.0.0` - First stable release
- `1.1.0` - Added new reference files or patterns
- `1.1.1` - Fixed typos or clarified examples
- `2.0.0` - Restructured skill, changed format

### Checking Skill Versions

**Via Skills Management:**
```bash
claude-mpm configure
# → [2] Skills Management
# → [1] View bundled skills
# Shows: name, version, description for each skill
```

**Reading Frontmatter:**
```bash
# Check a specific skill's version
head -20 .claude/skills/my-skill.md | grep "version:"
```

**Programmatically:**
```python
import yaml

with open('.claude/skills/my-skill.md') as f:
    content = f.read()
    # Extract YAML frontmatter
    if content.startswith('---'):
        yaml_end = content.find('---', 3)
        frontmatter = yaml.safe_load(content[3:yaml_end])
        print(f"Version: {frontmatter['version']}")
```

### Version Best Practices

**For Skill Creators:**
- Start with `0.1.0` during development
- Release `1.0.0` when stable and tested
- Increment PATCH for fixes (1.0.0 → 1.0.1)
- Increment MINOR for new features (1.0.1 → 1.1.0)
- Increment MAJOR for breaking changes (1.1.0 → 2.0.0)

**For Skill Users:**
- Check versions when skills behave unexpectedly
- Review changelog when versions change
- Pin versions for critical projects (via custom skills)
- Update skills regularly for improvements

### Comprehensive Versioning Guide

For complete versioning documentation, see:
**[Skills Versioning Guide](/Users/masa/Projects/claude-mpm/docs/user/skills-versioning.md)**

Topics covered:
- Detailed version format specification
- Frontmatter metadata fields
- Version upgrade strategies
- Compatibility considerations
- Change documentation
- Version pinning techniques

---

## Skills Configuration

### Configuration File Structure

Skills configuration is stored in `.claude-mpm/config.yaml`:

```yaml
skills:
  # Skill assignments to agents
  assignments:
    engineer:
      - test-driven-development
      - systematic-debugging
      - mcp-builder
    qa:
      - test-driven-development
      - testing-anti-patterns
      - webapp-testing
    research:
      - systematic-debugging
      - brainstorming

  # Skills discovery paths (auto-configured)
  paths:
    bundled: /path/to/site-packages/claude_mpm/skills/bundled
    user: ~/.claude/skills
    project: .claude/skills

  # Auto-linking preferences
  auto_link:
    enabled: true
    exclude_skills: []  # Skills to never auto-link
    exclude_agents: []  # Agents to skip during auto-linking
```

### Skills Discovery Paths

**Bundled Skills:**
```python
# Auto-detected from installation
import claude_mpm.skills.bundled
# Path: <python-site-packages>/claude_mpm/skills/bundled/
```

**User Skills:**
```bash
# Default: ~/.claude/skills/
# Create if it doesn't exist:
mkdir -p ~/.claude/skills
```

**Project Skills:**
```bash
# Default: .claude/skills/ (in project root)
# Create if it doesn't exist:
mkdir -p .claude/skills
```

**Custom Paths:**
```yaml
# Override in .claude-mpm/config.yaml
skills:
  paths:
    user: ~/my-custom-skills-directory
    project: .my-project-skills
```

### Auto-Link Configuration

**Enable/Disable Auto-Linking:**
```yaml
skills:
  auto_link:
    enabled: true  # Set to false to disable
```

**Exclude Specific Skills:**
```yaml
skills:
  auto_link:
    exclude_skills:
      - web-performance-optimization  # Don't auto-link this skill
      - performance-profiling
```

**Exclude Specific Agents:**
```yaml
skills:
  auto_link:
    exclude_agents:
      - documentation  # Don't auto-link skills to documentation agent
```

### Manual Configuration Editing

**Edit configuration directly:**
```bash
# Open in editor
nano .claude-mpm/config.yaml

# Or use your preferred editor
code .claude-mpm/config.yaml
```

**Validate after editing:**
```bash
claude-mpm configure
# → [2] Skills Management
# → [5] Reload skills
# Will report any configuration errors
```

---

## Troubleshooting

### Skills Not Loading

**Symptom:** Skills aren't available in Claude Code sessions

**Solutions:**

1. **Check skills directories exist:**
   ```bash
   ls -la ~/.claude/skills/
   ls -la .claude/skills/
   ```

2. **Verify configuration:**
   ```bash
   claude-mpm configure
   # → [2] Skills Management
   # → [1] View bundled skills
   # Should list all 17 bundled skills
   ```

3. **Reload skills:**
   ```bash
   claude-mpm configure
   # → [2] Skills Management
   # → [5] Reload skills
   ```

4. **Restart Claude Code:**
   - Exit current Claude Code session
   - Start new session: `claude-mpm`
   - Skills load at session start

### Skills Not Appearing in Agent

**Symptom:** Skill is available but agent doesn't use it

**Solutions:**

1. **Verify skill assignment:**
   ```bash
   # Check if skill is assigned to agent
   cat .claude-mpm/config.yaml | grep -A 10 "assignments:"
   ```

2. **Assign skill manually:**
   ```bash
   claude-mpm configure
   # → [2] Skills Management
   # → [2] Select skills for an agent
   # → Select agent and assign skill
   ```

3. **Check agent template:**
   ```bash
   # Verify agent template references skills
   cat .claude-agents/<agent-name>.md
   # Should contain: {SKILLS} or {ALL_SKILLS} placeholder
   ```

### Custom Skill Format Errors

**Symptom:** Custom skill not loading, format validation errors

**Solutions:**

1. **Verify YAML frontmatter:**
   ```yaml
   ---
   name: skill-name  # Required
   description: Description  # Required
   version: 1.0.0  # Required
   category: development  # Required
   ---
   ```

2. **Check required fields:**
   - `name` - Must match filename (without .md extension)
   - `description` - 10-150 characters
   - `version` - Semantic version format
   - `category` - One of: development, testing, debugging, collaboration, infrastructure, documentation

3. **Validate progressive disclosure structure:**
   ```yaml
   progressive_disclosure:
     entry_point:
       summary: "Brief overview"
       when_to_use: "Activation conditions"
       quick_start: "Steps to begin"
     references:  # Optional but recommended
       - reference1.md
       - reference2.md
   ```

4. **Use validation tools:**
   ```bash
   # If using skill-creator skill, it includes validation
   # Or manually validate YAML:
   python -c "import yaml; yaml.safe_load(open('.claude/skills/my-skill.md').read().split('---')[1])"
   ```

### Skills Version Conflicts

**Symptom:** Different versions of same skill in multiple tiers

**Solution:**
- Project skills override user and bundled (by design)
- If you want bundled version, remove project/user version:
  ```bash
  rm .claude/skills/conflicting-skill.md
  rm ~/.claude/skills/conflicting-skill.md
  ```

### Performance Issues with Many Skills

**Symptom:** Slow session startup with many custom skills

**Solutions:**

1. **Reduce skill count:**
   - Remove unused skills from `.claude/skills/`
   - Combine related small skills into larger ones

2. **Optimize skill size:**
   - Keep entry points under 200 lines
   - Move details to reference files
   - Use progressive disclosure

3. **Disable auto-linking if not needed:**
   ```yaml
   skills:
     auto_link:
       enabled: false
   ```

---

## Best Practices

### For Skill Users

**1. Start with Auto-Linking**
```bash
claude-mpm configure
# → [2] Skills Management
# → [4] Auto-link skills to agents
```
Covers 90% of common use cases efficiently.

**2. Add Project Skills for Domain Expertise**
```bash
mkdir -p .claude/skills
# Create project-specific pattern skills
```
Document your project's unique conventions and patterns.

**3. Keep Skills Focused**
- One skill per expertise area
- Don't combine unrelated topics
- Example: Separate "database-patterns" from "api-patterns"

**4. Update Skills as Patterns Evolve**
```bash
# Skills are living documentation
# Update when you learn better approaches
nano .claude/skills/my-patterns.md
# Increment version number
```

**5. Version Critical Skills**
```yaml
# In frontmatter
version: 1.2.0
# Update when making changes
```

**6. Document Why, Not Just What**
```markdown
# Good
## Use Async for I/O Operations
Async/await prevents blocking the event loop during database queries,
improving throughput by ~3x in our testing.

# Bad
## Use Async
Use async/await.
```

### For Skill Creators

**1. Follow Progressive Disclosure**
- Entry point (SKILL.md): 150-200 lines
- Reference files: 150-300 lines each
- Front-load critical information
- Move details to references

**2. Provide Clear When-to-Use Guidance**
```yaml
progressive_disclosure:
  entry_point:
    when_to_use: "When building MCP servers for external API integration"
```

**3. Include Concrete Examples**
```markdown
## Examples

### Creating a User Service

```python
class UserService:
    async def create_user(self, data: UserCreate) -> User:
        user = User(**data.dict())
        await self.db.save(user)
        return user
```
```

**4. Reference Other Skills**
```markdown
## Integration with Other Skills

- **systematic-debugging**: Debug issues methodically
- **test-driven-development**: Write tests first
```

**5. Use Validation**
- Validate YAML frontmatter
- Check required fields
- Verify reference files exist
- Test skill loading

**6. Document Changes**
```markdown
## Changelog

### 1.1.0 (2025-11-10)
- Added section on error handling
- New examples for async patterns
- Updated TypeScript examples to SDK v2

### 1.0.0 (2025-10-15)
- Initial stable release
```

---

## Advanced Topics

### Skills in Multi-Agent Workflows

When using multiple agents with dispatching:

```bash
# Each agent has its own skill assignments
# Share common skills across agents:
skills:
  assignments:
    engineer-backend:
      - test-driven-development
      - systematic-debugging
      - fastapi-local-dev
    engineer-frontend:
      - test-driven-development
      - systematic-debugging
      - nextjs-local-dev
```

**Benefits:**
- Consistent practices across agents
- Reduced redundancy in agent templates
- Easier maintenance

### Creating Skill Collections

Group related skills for specific workflows:

```bash
mkdir -p .claude/skills/collections

cat > .claude/skills/collections/fullstack-web-dev.md << 'EOF'
---
name: fullstack-web-dev
description: Collection of skills for full-stack web development
version: 1.0.0
category: development
---

# Full-Stack Web Development Collection

This collection references multiple skills for full-stack development:

## Backend Development
- See: fastapi-local-dev
- See: database-migration
- See: api-documentation

## Frontend Development
- See: nextjs-local-dev
- See: vite-local-dev
- See: web-performance-optimization

## Common Practices
- See: test-driven-development
- See: systematic-debugging
- See: git-workflow
EOF
```

### Skills for Code Generation

Create skills that include code templates:

```bash
cat > .claude/skills/api-templates.md << 'EOF'
---
name: api-templates
description: Reusable API endpoint templates
version: 1.0.0
category: development
---

# API Templates

## FastAPI CRUD Endpoint Template

```python
from fastapi import APIRouter, Depends, HTTPException
from typing import List

router = APIRouter(prefix="/api/resources", tags=["resources"])

@router.get("/", response_model=List[ResourceRead])
async def list_resources(
    skip: int = 0,
    limit: int = 100,
    user: User = Depends(get_current_user)
):
    """List all resources."""
    return await resource_service.list(skip=skip, limit=limit, user=user)

@router.get("/{resource_id}", response_model=ResourceRead)
async def get_resource(
    resource_id: int,
    user: User = Depends(get_current_user)
):
    """Get a specific resource."""
    resource = await resource_service.get(resource_id, user=user)
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")
    return resource

# ... more endpoints
```

## Usage

1. Copy template
2. Replace "Resource" with your entity name
3. Customize business logic
4. Add validation and error handling
EOF
```

### Skills Development Workflow

**For creating and maintaining high-quality skills:**

1. **Research:** Study existing skills (especially skill-creator)
2. **Plan:** Define scope, category, target users
3. **Create:** Follow SKILL.md format specification
4. **Validate:** Check format, test loading
5. **Document:** Add examples, when-to-use, references
6. **Version:** Start at 0.1.0, increment appropriately
7. **Test:** Assign to agent, verify behavior
8. **Iterate:** Gather feedback, improve
9. **Release:** Version 1.0.0 when stable
10. **Maintain:** Update as patterns evolve

### Integration with Auto-Configure

When using `claude-mpm auto-configure`:

1. **Framework Detection** automatically suggests relevant skills
2. **Skills Auto-Assigned** to framework-appropriate agents
3. **Configuration Saved** to `.claude-mpm/config.yaml`

**Example:**
```bash
# In Next.js project
claude-mpm auto-configure

# Automatically assigns:
# engineer → nextjs-local-dev, test-driven-development, git-workflow
# qa → webapp-testing, test-driven-development
```

---

## Next Steps

### Learning More

- **[Skills Versioning Guide](/Users/masa/Projects/claude-mpm/docs/user/skills-versioning.md)** - Comprehensive versioning documentation
- **[SKILL.md Format Specification](/Users/masa/Projects/claude-mpm/docs/design/SKILL-MD-FORMAT-SPECIFICATION.md)** - Complete format requirements
- **[User Guide](/Users/masa/Projects/claude-mpm/docs/user/user-guide.md)** - Full Claude MPM documentation
- **[Architecture](/Users/masa/Projects/claude-mpm/docs/ARCHITECTURE.md)** - System architecture details

### Using Bundled Skills

**Explore specific skills:**
- **mcp-builder** - Build high-quality MCP servers
- **skill-creator** - Create your own skills
- **test-driven-development** - TDD practices
- **systematic-debugging** - Scientific debugging approach

### Creating Your First Custom Skill

Start with a simple project-specific skill:

```bash
# 1. Create directory
mkdir -p .claude/skills

# 2. Create skill file
cat > .claude/skills/my-first-skill.md << 'EOF'
---
name: my-first-skill
description: My first custom skill
version: 0.1.0
category: development
---

# My First Skill

## Overview
This skill demonstrates basic skill creation.

## When to Use
Use this skill when learning about skills.

## Example
Here's how to use this skill...
EOF

# 3. Assign to agent
claude-mpm configure
# → [2] Skills Management
# → [2] Select skills for an agent
# → Select "engineer" and "my-first-skill"

# 4. Test in Claude Code
claude-mpm
# Ask engineer to use patterns from my-first-skill
```

### Contributing Skills

**Share your skills with the community:**

1. Create high-quality skill following format specification
2. Test thoroughly with multiple agents
3. Document examples and use cases
4. Submit as pull request to Claude MPM repository
5. Include tests and validation

See project repository for contribution guidelines.

---

## Summary

**Skills are powerful knowledge modules that:**
- ✅ Provide specialized domain expertise to agents
- ✅ Eliminate redundancy across agent templates (~15,000 lines saved)
- ✅ Ensure consistency in practices and patterns
- ✅ Support progressive disclosure for context efficiency
- ✅ Enable easy sharing and reuse of expertise
- ✅ Track evolution through semantic versioning

**Quick Start Recap:**
1. `claude-mpm configure` → Skills Management
2. Auto-link skills to agents
3. Create custom skills in `.claude/skills/`
4. Use skills naturally - agents load them automatically

**Get Started Now:**
```bash
claude-mpm configure
# → [2] Skills Management
# → [4] Auto-link skills to agents
# → Done! Skills are now active.
```

For questions or issues, refer to [Troubleshooting](#troubleshooting) or consult the [User Guide](/Users/masa/Projects/claude-mpm/docs/user/user-guide.md).
