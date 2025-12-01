# Upgrading to Claude MPM v5.0 🚀

Welcome to Claude MPM v5.0 - the most significant release since the project's inception! This version represents a fundamental shift in how agents and skills are distributed, making Claude MPM a truly **community-driven ecosystem**.

## What Makes v5.0 Special

Claude MPM v5.0 transforms from a standalone tool into a **platform for sharing and collaboration**. With Git repository integration, the barrier to creating and sharing agents and skills has been completely removed. What started as 4 built-in skills and 10 agents has now grown to:

- **📦 47+ Agents**: Specialized agents for every domain and technology
- **📚 37+ Skills**: Including 14+ official Anthropic skills
- **🌍 Community-Driven**: Anyone can contribute and benefit from shared expertise
- **🎯 Production-Ready**: Thoroughly tested with robust error handling

This release isn't just about features - it's about building a thriving ecosystem where your expertise can help thousands of developers.

---

## 🎯 What's New in v5.0

### Git Repository Integration

The headline feature: **Native Git repository support** for both agents and skills.

**Key Capabilities:**
- **Multi-Repository Support**: Add unlimited agent and skill repositories
- **Automatic Syncing**: Repositories sync on startup with smart caching
- **Hierarchical Organization**: `BASE-AGENT.md` files cascade from parent directories
- **Nested Repository Support**: Automatic flattening for Claude Code compatibility
- **Immediate Testing**: Fail-fast validation with `--test` flag
- **Two-Phase Progress**: Clear visibility into sync and deployment status
- **Priority Control**: Manage which sources win when conflicts occur

**What This Means for You:**
- ✅ Always have the latest agent improvements without manual updates
- ✅ Share your custom agents/skills with teams or the community
- ✅ Contribute improvements back to repositories via pull requests
- ✅ Test repositories before they affect your production workflow
- ✅ Organize agents hierarchically with shared templates

### Default Repositories

**Agents** (47+ agents available):
- **System Repository**: [`bobmatnyc/claude-mpm-agents`](https://github.com/bobmatnyc/claude-mpm-agents)
  - Engineers: Python, Rust, Go, JavaScript, TypeScript, Java, C++, etc.
  - Specialists: Security, DevOps, QA, Database, API, Infrastructure
  - Domain Experts: Healthcare, Legal, Finance, Education
  - Workflow Agents: Documentation, Project Manager, Research

**Skills** (37+ skills available):
- **Community Skills**: [`bobmatnyc/claude-mpm-skills`](https://github.com/bobmatnyc/claude-mpm-skills)
  - Development: Git workflows, testing utilities, code analysis
  - Operations: Deployment automation, monitoring, CI/CD
  - Utilities: File processing, data transformation, API clients
- **Official Anthropic Skills**: [`anthropics/skills`](https://github.com/anthropics/skills)
  - Time tools, brave search, filesystem operations, and more

**Automatic Setup:**
- First run automatically clones and deploys all repositories
- Startup sync keeps everything up-to-date (with smart caching)
- ETag-based caching reduces bandwidth by 95%+

### Hierarchical BASE-AGENT.md Inheritance

Organize agents with shared templates that cascade from parent directories:

```
your-agents/
  BASE-AGENT.md              # Root: Shared across ALL agents
  engineering/
    BASE-AGENT.md            # Engineering: Shared across engineering/*
    python/
      BASE-AGENT.md          # Python: Shared across engineering/python/*
      fastapi-engineer.md    # Inherits all three BASE files
      django-engineer.md     # Inherits all three BASE files
    rust/
      BASE-AGENT.md          # Rust: Shared across engineering/rust/*
      actix-engineer.md      # Inherits rust, engineering, and root BASE files
```

**Composition Example** (for `fastapi-engineer.md`):
```
Final Agent Content =
  fastapi-engineer.md content
  + engineering/python/BASE-AGENT.md content
  + engineering/BASE-AGENT.md content
  + BASE-AGENT.md content (root)
```

See [docs/features/hierarchical-base-agents.md](docs/features/hierarchical-base-agents.md) for complete guide.

### Two-Phase Progress Bars

Get clear visibility into repository sync and deployment:

**Phase 1: Repository Sync**
```
Agent Sources Sync
└─ bobmatnyc/claude-mpm-agents ████████████████████ 100% (1.2s)
```

**Phase 2: Agent Deployment**
```
Deploying Agents
└─ 47/47 agents ████████████████████ 100% (0.8s)
```

**Benefits:**
- Understand exactly what's happening during startup
- Identify slow repositories or network issues
- Track deployment progress for large agent sets

### Immediate Repository Testing

Validate repositories before they cause startup issues:

```bash
# Test repository without adding it
claude-mpm agent-source add https://github.com/your-org/agents --test

# Output shows validation results:
✓ Repository is accessible
✓ Found 12 agent files
✓ All agents validated successfully
```

**What Gets Tested:**
- Repository accessibility (network/permissions)
- Agent file discovery and count
- JSON/Markdown format validation
- Required field presence
- Syntax validation

**Fail-Fast Design:**
- Broken repositories are rejected immediately
- Clear error messages guide resolution
- No impact on existing configuration
- Test mode leaves no traces

---

## 🤝 Community Contribution Goals

**Our Vision:** Build the world's largest library of Claude agents and skills, maintained by the community.

We're inviting the community to contribute in two ways:

### Type 1: Improving Existing Agents & Skills

Help make existing agents and skills better:

**Enhancement Opportunities:**
- **Documentation**: Add examples, use cases, troubleshooting guides
- **Capabilities**: Add new features or routing keywords
- **Error Handling**: Improve resilience and error messages
- **Performance**: Optimize instruction caching, reduce token usage
- **Test Coverage**: Add validation and edge case handling
- **Specialization**: Narrow focus for specific frameworks/platforms

**Example Improvements:**
- Add FastAPI-specific patterns to `python-engineer.md`
- Enhance `security-agent.md` with OWASP testing guidelines
- Add Kubernetes deployment skills to `devops-engineer.md`
- Document common pitfalls in `qa-engineer.md`
- Add integration examples to skills

### Type 2: Creating New Agents & Skills

Contribute new capabilities the community needs:

**High-Value Agent Categories:**
- **Domain Specialists**: Healthcare, legal, finance, education, scientific
- **Language Engineers**: Kotlin, Swift, Scala, Elixir, Clojure, F#
- **Platform Specialists**: AWS, Azure, GCP, Kubernetes, Terraform
- **Framework Experts**: Django, Rails, Laravel, Spring Boot, Next.js
- **Workflow Agents**: Code review, migration, refactoring, optimization

**High-Value Skill Categories:**
- **Data Processing**: CSV/JSON/XML parsing, data transformation
- **API Integration**: Popular APIs (Stripe, Twilio, SendGrid, etc.)
- **DevOps Automation**: Deployment, monitoring, logging, alerting
- **Testing Utilities**: Load testing, security scanning, accessibility
- **Code Analysis**: Complexity metrics, dependency analysis, security audits

**What Makes a Great Contribution:**
- **Clear Use Case**: Solve a specific, well-defined problem
- **Comprehensive Documentation**: Examples, error handling, edge cases
- **Tested Thoroughly**: Works reliably across different scenarios
- **Follows Patterns**: Consistent with existing agents/skills
- **Community Value**: Benefits many users, not just one project

---

## 📚 How to Contribute

### Quick Start: Fork and Test Locally

**For Agents:**

```bash
# 1. Fork the repository
# Visit: https://github.com/bobmatnyc/claude-mpm-agents
# Click "Fork" to create your copy

# 2. Clone your fork
git clone https://github.com/YOUR-USERNAME/claude-mpm-agents
cd claude-mpm-agents

# 3. Create your agent (see template below)
cd agents
mkdir -p domain-specific
vim domain-specific/healthcare-agent.md

# 4. Test locally with Claude MPM
claude-mpm agent-source add https://github.com/YOUR-USERNAME/claude-mpm-agents --test

# 5. If test passes, add it for real
claude-mpm agent-source add https://github.com/YOUR-USERNAME/claude-mpm-agents

# 6. Deploy and test your agent
claude-mpm agents deploy healthcare-agent
claude-mpm  # Test in interactive mode

# 7. Submit pull request to main repository
git add agents/domain-specific/healthcare-agent.md
git commit -m "feat: add healthcare-agent for medical coding assistance"
git push origin main
# Create PR on GitHub
```

**For Skills:**

```bash
# 1. Fork the repository
# Visit: https://github.com/bobmatnyc/claude-mpm-skills
# Click "Fork" to create your copy

# 2. Clone your fork
git clone https://github.com/YOUR-USERNAME/claude-mpm-skills
cd claude-mpm-skills

# 3. Create your skill (see template below)
mkdir -p data-processing/csv-analyzer
cd data-processing/csv-analyzer
vim SKILL.md
# Add any helper files (scripts, configs, examples)

# 4. Test locally with Claude MPM
claude-mpm skill-source add https://github.com/YOUR-USERNAME/claude-mpm-skills --test

# 5. If test passes, add it for real
claude-mpm skill-source add https://github.com/YOUR-USERNAME/claude-mpm-skills

# 6. Test your skill
claude-mpm  # Start interactive mode
# Try using your skill

# 7. Submit pull request to main repository
git add data-processing/csv-analyzer/
git commit -m "feat: add CSV analyzer skill for data quality checks"
git push origin main
# Create PR on GitHub
```

### Agent Contribution Guidelines

**Agent Template Structure (JSON Format):**

```json
{
  "id": "healthcare-agent",
  "name": "Healthcare Agent",
  "description": "Specialized agent for healthcare software development, HIPAA compliance, and medical coding standards",
  "instructions": "You are a healthcare software development specialist...\n\n## Expertise\n- HIPAA compliance and security\n- HL7/FHIR standards\n- Medical coding (ICD-10, CPT, SNOMED)\n- Healthcare data privacy\n\n## Guidelines\n- Always consider patient privacy\n- Validate against healthcare standards\n- Document compliance requirements",
  "model": "claude-sonnet-4-5-20250929",
  "routing": {
    "keywords": [
      "healthcare",
      "medical",
      "hipaa",
      "hl7",
      "fhir",
      "patient",
      "clinical",
      "emr",
      "ehr"
    ]
  }
}
```

**Required Fields:**
- `id`: Unique identifier (kebab-case)
- `name`: Human-readable name
- `description`: One-sentence summary
- `instructions`: Complete agent instructions
- `model`: Claude model to use

**Optional Fields:**
- `routing.keywords`: Keywords for automatic agent selection
- `routing.paths`: File patterns for automatic agent selection
- `memory_routing`: Memory configuration (advanced)

**Agent Instructions Best Practices:**
- Start with a clear role definition
- List specific areas of expertise
- Provide concrete guidelines and examples
- Include error handling patterns
- Document common edge cases
- Reference relevant standards/frameworks
- Use markdown formatting for readability

**Using BASE-AGENT.md for Shared Content:**

Create `BASE-AGENT.md` files in parent directories to share content:

```markdown
# Engineering Best Practices

## Code Quality Standards
- Follow SOLID principles
- Write comprehensive tests (85%+ coverage)
- Document complex logic and edge cases
- Use meaningful variable and function names

## Development Workflow
- Make small, focused commits
- Write clear commit messages
- Request code review before merging
- Update documentation with code changes
```

All agents in subdirectories automatically inherit this content.

### Skill Contribution Guidelines

**Skill Template Structure (Markdown Format):**

```markdown
# CSV Analyzer Skill

## Description
Analyze CSV files for data quality issues, schema validation, and statistical summaries.

## Use Cases
- Detect missing values, duplicates, and outliers
- Validate column types and constraints
- Generate statistical summaries
- Identify data quality issues

## Usage

### Basic Analysis
Ask Claude: "Analyze the data quality of sales.csv"

### Schema Validation
Ask Claude: "Validate customer.csv against the expected schema"

### Statistical Summary
Ask Claude: "Generate a statistical summary of metrics.csv"

## Capabilities
- Missing value detection and reporting
- Duplicate row identification
- Outlier detection using IQR method
- Type inference and validation
- Statistical summaries (mean, median, std, percentiles)
- Column correlation analysis

## Example

**User:** Analyze data quality of sales_data.csv

**Claude (using this skill):**
- Reads CSV file
- Checks for missing values: 5% in 'revenue' column
- Detects 12 duplicate rows
- Identifies 3 outliers in 'quantity' column
- Validates data types match expected schema
- Generates statistical summary

## Implementation Notes
- Handles large files via chunking (10K rows at a time)
- Supports custom delimiter detection
- Works with compressed CSV files (.csv.gz)
- Provides actionable recommendations

## Error Handling
- Invalid CSV format: Suggests corrections
- Missing file: Clear error message with path check
- Encoding issues: Auto-detect and convert
- Memory limits: Streams large files

## Dependencies
None - uses only Claude's built-in capabilities

## Author
@yourname - Expert in data quality and analysis

## Version
1.0.0 - Initial release
```

**Required Sections:**
- **Title and Description**: Clear, concise overview
- **Use Cases**: When to use this skill
- **Usage**: How to invoke the skill
- **Capabilities**: What the skill can do
- **Example**: Concrete usage example

**Optional Sections:**
- **Implementation Notes**: Technical details
- **Error Handling**: How errors are handled
- **Dependencies**: External requirements
- **Author/Version**: Attribution and versioning

**Helper Files:**
Skills can include helper files in the same directory:
- Scripts: `analyze.py`, `validator.js`
- Configurations: `schema.json`, `rules.yaml`
- Examples: `sample-input.csv`, `expected-output.json`
- Documentation: `ADVANCED_USAGE.md`, `TROUBLESHOOTING.md`

**Self-Contained Requirement:**
All referenced materials must be in the same directory or subdirectories. The skill must work without external dependencies.

---

## 🎯 Quality Standards

All contributions must meet these standards:

### Documentation
- **Clear Description**: One-sentence summary of purpose
- **Use Cases**: When and why to use this agent/skill
- **Examples**: Concrete usage examples with expected outcomes
- **Error Handling**: How errors are handled and communicated
- **Edge Cases**: Document known limitations or special cases

### Testing
- **Validated Locally**: Test with `claude-mpm --test` before submitting
- **Multiple Scenarios**: Test common use cases and edge cases
- **Error Paths**: Verify error handling works as documented
- **Integration**: Ensure works with other agents/skills

### Consistency
- **Follow Patterns**: Match existing agent/skill structure
- **Naming Conventions**: Use kebab-case for IDs, descriptive names
- **File Organization**: Place in appropriate directory hierarchy
- **Markdown/JSON Format**: Use correct syntax and formatting

### Completeness
- **All Required Fields**: No missing required metadata
- **Comprehensive Instructions**: Cover all capabilities and guidelines
- **Referenced Files**: Include all helper files in same directory
- **Version Information**: Include author and version metadata

---

## 🚀 Getting Started Examples

### Example 1: Add a Custom Agent Repository

```bash
# Scenario: Your company wants to share internal agents

# 1. Create a repository (GitHub, GitLab, Bitbucket)
mkdir my-company-agents
cd my-company-agents
git init
mkdir agents

# 2. Create a company-wide BASE-AGENT.md
cat > agents/BASE-AGENT.md << 'EOF'
# Company Engineering Standards

## Code Style
- Follow company style guide: https://company.com/style
- Use company approved libraries only
- All code must pass security scanning

## Communication
- Professional, clear, concise
- Reference company policies when relevant
- Escalate security issues to security team
EOF

# 3. Create a specialized agent
cat > agents/company-api-engineer.md << 'EOF'
You are a specialist in our company's API framework...

## Expertise
- Company API framework v2.0
- Internal authentication system
- Company-specific microservices patterns

## Guidelines
- Always use company API templates
- Follow internal service mesh patterns
- Reference internal documentation
EOF

# 4. Commit and push to GitHub
git add agents/
git commit -m "feat: add company API engineer"
git push origin main

# 5. Add to Claude MPM with high priority
claude-mpm agent-source add https://github.com/mycompany/agents --priority 10

# 6. Deploy and use
claude-mpm agents deploy company-api-engineer
```

### Example 2: Hierarchical Agent Organization

```bash
# Scenario: Create a well-organized agent repository

# Directory structure:
agents/
  BASE-AGENT.md                    # Root: All agents
  engineering/
    BASE-AGENT.md                  # Engineering: All engineers
    backend/
      BASE-AGENT.md                # Backend: All backend engineers
      python/
        BASE-AGENT.md              # Python: All Python engineers
        fastapi-engineer.md        # Specific agent
        django-engineer.md         # Specific agent
      rust/
        actix-engineer.md
        rocket-engineer.md
    frontend/
      react-engineer.md
      vue-engineer.md

# Example composition for fastapi-engineer.md:
# Final content includes:
# - fastapi-engineer.md (specific agent)
# - engineering/backend/python/BASE-AGENT.md
# - engineering/backend/BASE-AGENT.md
# - engineering/BASE-AGENT.md
# - BASE-AGENT.md (root)

# Each level adds more specific guidelines
# Root: Company values, communication style
# Engineering: Code quality, testing standards
# Backend: API design, database patterns
# Python: Python-specific best practices
# FastAPI: Framework-specific guidelines
```

### Example 3: Simple Agent Template

**File:** `agents/kotlin-engineer.md`

```json
{
  "id": "kotlin-engineer",
  "name": "Kotlin Engineer",
  "description": "Specialized Kotlin development agent for Android and server-side applications",
  "instructions": "You are an expert Kotlin developer with deep knowledge of both Android development and server-side Kotlin.\n\n## Expertise\n- Modern Kotlin language features (coroutines, flows, sealed classes)\n- Android app development (Jetpack Compose, MVVM, Clean Architecture)\n- Server-side Kotlin (Ktor, Spring Boot)\n- Kotlin multiplatform (KMP)\n- Testing with JUnit, Mockk, Kotest\n\n## Development Guidelines\n- Prefer Kotlin idioms over Java-style code\n- Use coroutines for async operations, avoid callbacks\n- Leverage sealed classes for state management\n- Follow SOLID principles and clean architecture\n- Write comprehensive tests with descriptive names\n- Use inline classes for type-safe primitives\n\n## Code Style\n- Follow official Kotlin coding conventions\n- Use meaningful variable names (no abbreviations)\n- Prefer immutability (val over var)\n- Use expression bodies for simple functions\n- Group related functions with visibility modifiers\n\n## Common Patterns\n- Repository pattern for data access\n- MVVM or MVI for Android presentation layer\n- Sealed classes for API responses and UI states\n- Extension functions for utility methods\n- Scope functions (let, run, apply, also) appropriately\n\n## Error Handling\n- Use Result type for operations that can fail\n- Sealed classes for domain-specific errors\n- Descriptive error messages with context\n- Proper exception handling in coroutines\n\n## Testing\n- Unit tests for business logic (85%+ coverage)\n- Integration tests for repositories\n- UI tests for critical user flows\n- Use Mockk for mocking, Turbine for Flow testing",
  "model": "claude-sonnet-4-5-20250929",
  "routing": {
    "keywords": [
      "kotlin",
      "android",
      "jetpack",
      "compose",
      "ktor",
      "coroutines"
    ],
    "paths": [
      "**/*.kt",
      "**/*.kts",
      "**/build.gradle.kts"
    ]
  }
}
```

### Example 4: Simple Skill Template

**File:** `api-testing/rest-api-validator/SKILL.md`

```markdown
# REST API Validator

## Description
Validate REST API responses against OpenAPI/Swagger specifications, ensuring API contracts are maintained.

## Use Cases
- Validate API responses match schema definitions
- Test API endpoint availability and response times
- Verify authentication and authorization
- Check HTTP status codes and headers
- Generate API test reports

## Usage

### Basic Validation
Ask Claude: "Validate the /users endpoint against openapi.yaml"

### Full API Test
Ask Claude: "Test all endpoints in openapi.yaml and generate a report"

### Contract Testing
Ask Claude: "Check if current API responses match the v2.0 schema"

## Capabilities
- **Schema Validation**: Verify responses match OpenAPI definitions
- **Status Code Checking**: Ensure correct HTTP status codes
- **Authentication Testing**: Test various auth scenarios
- **Response Time Monitoring**: Track API performance
- **Header Validation**: Verify required headers present
- **Report Generation**: Create detailed test reports

## Example

**User:** Validate the /api/v1/users endpoint

**Claude (using this skill):**
1. Loads OpenAPI specification
2. Makes GET request to /api/v1/users
3. Validates response schema matches spec
4. Checks status code (expected: 200)
5. Verifies required headers (Content-Type, etc.)
6. Reports any discrepancies

**Output:**
```
✓ Status code: 200 (expected: 200)
✓ Content-Type: application/json
✓ Response schema valid
✗ Missing field: 'created_at' in user object
✗ Field 'email' should be string, got null
```

## Implementation Notes
- Supports OpenAPI 3.0 and Swagger 2.0
- Handles authentication (Bearer, API Key, OAuth)
- Configurable timeouts and retry logic
- Works with both JSON and XML responses

## Error Handling
- **Invalid Spec**: Clear error with line number
- **Network Errors**: Retry with exponential backoff
- **Timeout**: Configurable timeout with clear message
- **Auth Failure**: Specific auth error guidance

## Dependencies
- OpenAPI specification file (YAML or JSON)
- API endpoint must be accessible

## Example OpenAPI Spec

See `example-spec.yaml` in this directory for a sample OpenAPI specification.

## Author
@apiexpert - 10+ years API development and testing

## Version
1.0.0 - Initial release
```

**File:** `api-testing/rest-api-validator/example-spec.yaml`

```yaml
openapi: 3.0.0
info:
  title: User API
  version: 1.0.0
paths:
  /api/v1/users:
    get:
      summary: List users
      responses:
        '200':
          description: Successful response
          content:
            application/json:
              schema:
                type: array
                items:
                  type: object
                  required:
                    - id
                    - email
                    - created_at
                  properties:
                    id:
                      type: integer
                    email:
                      type: string
                    name:
                      type: string
                    created_at:
                      type: string
                      format: date-time
```

---

## 🔗 Repository Links

### Agent Repositories

**Official Repository:**
- **URL**: https://github.com/bobmatnyc/claude-mpm-agents
- **Content**: 47+ curated agents (engineers, specialists, domain experts)
- **How to Contribute**: Fork → Add/Improve → Test → Submit PR

**Your Custom Repository:**
```bash
# Create your own agent repository
# 1. Fork bobmatnyc/claude-mpm-agents OR create new repo
# 2. Add your agents following the template
# 3. Test locally: claude-mpm agent-source add <your-fork-url> --test
# 4. Submit PR to main repository for community benefit
```

### Skill Repositories

**Community Skills:**
- **URL**: https://github.com/bobmatnyc/claude-mpm-skills
- **Content**: Community-contributed skills (development, ops, utilities)
- **How to Contribute**: Fork → Add/Improve → Test → Submit PR

**Official Anthropic Skills:**
- **URL**: https://github.com/anthropics/skills
- **Content**: 14+ official skills from Anthropic
- **Read-Only**: Submit improvements via Anthropic's contribution process

**Your Custom Repository:**
```bash
# Create your own skill repository
# 1. Fork bobmatnyc/claude-mpm-skills OR create new repo
# 2. Add your skills following SKILL.md format
# 3. Test locally: claude-mpm skill-source add <your-fork-url> --test
# 4. Submit PR to main repository for community benefit
```

### Testing Your Fork

```bash
# Test without affecting configuration
claude-mpm agent-source add https://github.com/YOUR-USERNAME/claude-mpm-agents --test

# If successful, add for real
claude-mpm agent-source add https://github.com/YOUR-USERNAME/claude-mpm-agents

# Deploy and test your agent
claude-mpm agents deploy your-new-agent
claude-mpm  # Test interactively
```

---

## 📦 Migration from v4.x

### Automatic Migration

**Good news:** Migration happens automatically on first startup of v5.0!

**What Gets Migrated:**
- Skills move from `~/.claude-mpm/skills/` → `~/.claude/skills/`
- Configuration files are updated to v5.0 format
- Agent sources configuration created if missing
- Skill sources configuration created with defaults

### Breaking Changes

#### 1. Skills Location Changed

**Before (v4.x):**
```
Project: .claude-mpm/skills/
User: ~/.claude-mpm/skills/
```

**After (v5.0):**
```
Global: ~/.claude/skills/ (all skills, flat structure)
Configuration: ~/.claude-mpm/config/skill_sources.yaml
```

**Why?** Claude Code requires skills in `~/.claude/skills/` with flat directory structure.

**Migration:** Automatic - skills are redeployed to new location on first run.

#### 2. New Configuration Files

**Agent Sources:**
```
~/.claude-mpm/config/agent_sources.yaml
```

**Skill Sources:**
```
~/.claude-mpm/config/skill_sources.yaml
```

These files are created automatically with default repositories on first run.

#### 3. Repository Caching

**New Cache Locations:**
```
~/.claude-mpm/agent-sources/<source-id>/
~/.claude-mpm/skill-sources/<source-id>/
```

Git repositories are cloned here and synced on startup.

### Manual Migration Steps (If Needed)

If automatic migration doesn't work:

```bash
# 1. Backup existing configuration
cp -r ~/.claude-mpm ~/.claude-mpm.backup

# 2. Remove old configuration (will be recreated)
rm ~/.claude-mpm/config/agent_sources.yaml
rm ~/.claude-mpm/config/skill_sources.yaml

# 3. Start Claude MPM (creates new configuration)
claude-mpm

# 4. Verify migration
claude-mpm doctor

# 5. Check agents and skills
claude-mpm agents list
ls ~/.claude/skills/
```

### Verification

After migration, verify everything works:

```bash
# 1. Check health
claude-mpm doctor --checks all

# 2. Verify agent sources
claude-mpm agent-source list
# Should show: bobmatnyc/claude-mpm-agents

# 3. Verify skill sources
claude-mpm skill-source list
# Should show: bobmatnyc/claude-mpm-skills, anthropics/skills

# 4. Count agents
claude-mpm agents list | wc -l
# Should show: 47+ agents

# 5. Count skills
ls ~/.claude/skills/ | wc -l
# Should show: 37+ skills

# 6. Test interactive mode
claude-mpm
# Should start normally with all agents available
```

---

## 🎉 Call to Action

### Join the Claude MPM Ecosystem

**We're building something special** - a community-driven library of Claude agents and skills that will benefit thousands of developers. Your contributions, whether improving existing agents or creating new ones, make a real difference.

### Why Contribute?

**For You:**
- **Recognition**: Your name on agents/skills used by thousands
- **Learning**: Master Claude prompt engineering and agent design
- **Portfolio**: Showcase your expertise to potential employers/clients
- **Community**: Join a growing community of AI enthusiasts

**For Everyone:**
- **Shared Knowledge**: Your expertise helps developers worldwide
- **Higher Quality**: Community review improves all contributions
- **Faster Progress**: Build on each other's work
- **Open Source**: Free for all, improved by all

### Get Started Today

**Quick Contribution Path:**

1. **Choose Your Path:**
   - **Beginner**: Improve documentation, add examples to existing agents
   - **Intermediate**: Enhance existing agents with new capabilities
   - **Advanced**: Create new domain-specific agents or complex skills

2. **Fork Repository:**
   - Agents: https://github.com/bobmatnyc/claude-mpm-agents
   - Skills: https://github.com/bobmatnyc/claude-mpm-skills

3. **Make Your Change:**
   - Follow templates and quality standards
   - Test thoroughly with `--test` flag
   - Document clearly with examples

4. **Submit Pull Request:**
   - Clear title: `feat: add healthcare agent` or `docs: improve python-engineer examples`
   - Description explaining value and use cases
   - Tag maintainers for review

5. **Celebrate:**
   - Your contribution helps thousands of developers
   - You're now part of the Claude MPM ecosystem
   - Your expertise is shared with the world

### What to Contribute

**High-Priority Needs:**
- Domain-specific agents (healthcare, legal, finance, education)
- Language engineers (Kotlin, Swift, Scala, Elixir, Haskell)
- Platform specialists (AWS, Azure, Kubernetes, Terraform)
- Framework experts (Django, Rails, Laravel, Spring Boot)
- Testing and QA utilities
- DevOps automation skills
- API integration skills

**Don't see your expertise listed?** We need it! Every domain has unique challenges that Claude can help solve.

### Resources for Contributors

**Documentation:**
- Agent Template Guide: [docs/features/hierarchical-base-agents.md](docs/features/hierarchical-base-agents.md)
- Agent Sources Guide: [docs/user/agent-sources.md](docs/user/agent-sources.md)
- CLI Reference: [docs/reference/cli-agent-source.md](docs/reference/cli-agent-source.md)
- Quality Standards: [CONTRIBUTING.md](CONTRIBUTING.md)

**Community:**
- GitHub Discussions: Ask questions, share ideas
- Issue Tracker: Report bugs, request features
- Pull Requests: Submit contributions

**Support:**
- Run `claude-mpm doctor` for diagnostics
- Check troubleshooting guides in [docs/user/troubleshooting.md](docs/user/troubleshooting.md)
- Open GitHub issue for help

### Next Steps

**Ready to contribute?**

```bash
# 1. Fork the repository (agents or skills)
# GitHub: Click "Fork" button

# 2. Clone your fork
git clone https://github.com/YOUR-USERNAME/claude-mpm-agents
cd claude-mpm-agents

# 3. Create your contribution
# ... add your agent/skill ...

# 4. Test locally
claude-mpm agent-source add https://github.com/YOUR-USERNAME/claude-mpm-agents --test

# 5. Commit and push
git add .
git commit -m "feat: add your contribution"
git push origin main

# 6. Submit pull request on GitHub
# Visit your fork and click "Pull Request"

# 7. Join the community!
```

---

## 📞 Support and Community

### Getting Help

**Documentation:**
- User Guide: [docs/user/user-guide.md](docs/user/user-guide.md)
- Troubleshooting: [docs/user/troubleshooting.md](docs/user/troubleshooting.md)
- FAQ: [docs/user/faq.md](docs/user/faq.md)

**Community:**
- GitHub Issues: Bug reports and feature requests
- GitHub Discussions: Questions and community support
- Pull Requests: Code contributions and improvements

**Tools:**
- `claude-mpm doctor`: Automated diagnostics
- `claude-mpm agent-source list`: Show configured sources
- `claude-mpm --help`: Command reference

### Frequently Asked Questions

**Q: Can I use my own private repositories?**
Yes! Claude MPM supports private repositories. Use SSH URLs or configure Git credentials.

**Q: How do I prioritize my custom agents over defaults?**
Use `--priority` when adding sources. Lower numbers = higher precedence:
```bash
claude-mpm agent-source add <your-repo> --priority 10
```

**Q: Can I disable default repositories?**
Yes:
```bash
claude-mpm agent-source disable bobmatnyc/claude-mpm-agents
```

**Q: How often do repositories sync?**
Automatically on startup with smart caching (ETag-based). Force sync:
```bash
claude-mpm agent-source update
```

**Q: What if I'm offline?**
Claude MPM uses cached repositories. You can work offline after initial sync.

**Q: How do I update to latest agents/skills?**
They update automatically on startup. Force update:
```bash
claude-mpm agent-source update
claude-mpm agents deploy --all --force
```

---

## 🎊 Thank You!

Thank you for being part of the Claude MPM journey. Version 5.0 represents hundreds of hours of development, testing, and refinement - all to create a platform where your expertise can help thousands of developers.

**Every contribution matters** - whether it's fixing a typo, adding an example, or creating a new specialized agent. Together, we're building the world's most comprehensive library of Claude agents and skills.

**Welcome to v5.0. Welcome to the Claude MPM ecosystem. Let's build something amazing together!** 🚀

---

*Last Updated: 2025-11-30*
*Version: 5.0.0*
*Maintained by the Claude MPM Community*
