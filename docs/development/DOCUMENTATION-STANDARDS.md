# Documentation Standards

**Version**: 1.0  
**Last Updated**: December 2025  
**Based on**: GitFlow Analytics documentation structure and Claude MPM framework requirements

## 📚 Documentation Philosophy

Our documentation follows a **progressive disclosure** model with clear audience segmentation for the Claude MPM multi-agent orchestration framework:

- **Users** find what they need to get started with Claude Code integration quickly
- **Developers** can dive deep into framework architecture and agent system implementation  
- **Contributors** have clear guidance on agent creation and framework extension
- **Maintainers** have architectural context for multi-agent orchestration decisions

## 🏗️ Directory Structure

```
docs/
├── README.md                    # Documentation hub and navigation
├── DOCUMENTATION-STANDARDS.md  # This file - documentation standards
├── STRUCTURE.md                 # Project structure documentation
├── getting-started/            # User onboarding and quick wins
├── guides/                     # Task-oriented user guides
├── examples/                   # Real-world usage examples
├── reference/                  # Technical reference material
├── developer/                  # Developer and contributor documentation
├── architecture/              # System design and architecture
├── design/                    # Design documents and decisions
├── deployment/                # Operations and deployment
├── configuration/             # Configuration documentation
└── _archive/                  # Historical content and deprecated docs
```

## 🎯 Content Categories

### 1. Getting Started (`getting-started/`)
**Purpose**: Help new users succeed quickly with Claude MPM + Claude Code  
**Audience**: First-time users, evaluators  
**Content**: Installation, auto-configuration, first agent deployment  
**Style**: Step-by-step, minimal prerequisites, Claude Code CLI focused

### 2. Guides (`guides/`)
**Purpose**: Task-oriented how-to documentation  
**Audience**: Regular users, power users  
**Content**: Agent management, multi-agent workflows, troubleshooting  
**Style**: Problem-solution oriented, comprehensive

### 3. Examples (`examples/`)
**Purpose**: Real-world usage scenarios  
**Audience**: All users seeking practical applications  
**Content**: Complete working examples, agent configurations, project setups  
**Style**: Copy-paste ready, well-commented

### 4. Reference (`reference/`)
**Purpose**: Complete technical specifications  
**Audience**: Integrators, advanced users  
**Content**: CLI commands, agent schemas, APIs, slash commands  
**Style**: Comprehensive, searchable, precise

### 5. Developer (`developer/`)
**Purpose**: Support contributors and maintainers  
**Audience**: Contributors, core team  
**Content**: Contributing, development setup, agent creation, framework extension  
**Style**: Technical, detailed, process-oriented

### 6. Architecture (`architecture/`)
**Purpose**: System design and technical decisions  
**Audience**: Architects, senior developers  
**Content**: Multi-agent system design, service architecture, performance patterns  
**Style**: High-level, decision-focused

### 7. Design (`design/`)
**Purpose**: Document design decisions and rationale  
**Audience**: Product managers, architects  
**Content**: Feature designs, agent workflow decisions, UX considerations  
**Style**: Decision-focused, rationale-heavy

### 8. Deployment (`deployment/`)
**Purpose**: Production deployment and operations  
**Audience**: DevOps, system administrators  
**Content**: Installation, monitoring, scaling, Claude Code integration  
**Style**: Operations-focused, security-conscious

## 📋 File Naming Conventions

### Standard Patterns
- Use lowercase with hyphens: `file-name.md`
- Be descriptive but concise: `agent-deployment.md` not `agents.md`
- Use consistent suffixes:
  - `-guide.md` for how-to documentation
  - `-reference.md` for technical specifications
  - `-overview.md` for high-level summaries
  - `-setup.md` for installation/configuration

### Special Files
- `README.md` - Directory index and navigation
- `CHANGELOG.md` - Version history (root only)
- `CONTRIBUTING.md` - Contribution guidelines (root only)
- `SECURITY.md` - Security policy and guidelines

## ✍️ Content Structure Standards

### Document Template
```markdown
# Title

Brief description of what this document covers.

## Prerequisites
- What users should know/have done first
- Required tools or access (Claude Code CLI version, etc.)

## Overview
High-level summary of the topic

## Step-by-Step Instructions
1. Clear, numbered procedures
2. Include expected output
3. Provide troubleshooting for common issues

## Examples
Real-world usage scenarios with complete code

## Troubleshooting
Common issues and solutions

## See Also
- [Related Topic](guides/README.md)
- [External Resource](https://example.com)

## Next Steps
Where to go next in the documentation journey
```

### Writing Style Guidelines

**Voice and Tone**:
- Use active voice: "Deploy the agent" not "The agent should be deployed"
- Be direct and concise
- Use "you" to address the reader
- Maintain a helpful, professional tone

**Technical Writing**:
- Define acronyms on first use (MCP = Model Context Protocol)
- Use consistent terminology throughout (Claude Code CLI, not "Claude CLI")
- Include complete, runnable examples
- Test all code samples before committing

**Shell Command Examples**:
- Always quote package names containing extras or special characters:
  - Correct: `uv tool install "claude-mpm[monitor,data-processing]"`
  - Incorrect: `uv tool install claude-mpm[monitor,data-processing]`
- zsh (the default macOS shell) treats `[`, `]`, `{`, `}`, `*`, and `?` as glob characters — unquoted, they cause silent failures or unexpected behavior
- Documentation code blocks are copy-pasted by users into their terminals, so they must be valid in both bash and zsh
- When in doubt, wrap arguments containing special characters in double quotes

**Framework-Specific Guidelines**:
- Always distinguish between FRAMEWORK (this repo) and PROJECT (user installations)
- Specify Claude Code CLI version requirements
- Include agent deployment examples
- Reference multi-agent orchestration patterns

## 🔗 Cross-Referencing Standards

### Internal Links
- Use relative paths: `[Configuration Reference](configuration/reference.md)`
- Link to specific sections: `[Installation](getting-started/installation.md#requirements)`
- Include "See Also" sections for related topics

### External Links
- Use full URLs for external resources
- Include link text that describes the destination
- Verify links regularly for accuracy

### Navigation Aids
- Each directory must have a `README.md` index
- Include breadcrumb navigation in complex documents
- Provide clear "Next Steps" guidance

## 📊 Quality Standards

### Content Quality
- All examples must be tested and working
- Include expected output when helpful
- Update documentation with each release
- Maintain accuracy through regular reviews

### Accessibility
- Use descriptive link text
- Include alt text for images
- Maintain logical heading hierarchy
- Ensure good contrast in screenshots

### Maintenance
- Review quarterly for accuracy
- Update broken links promptly
- Archive outdated content to `_archive/`
- Keep examples current with latest version

## 🗂️ Archive Policy

### What to Archive
- Outdated documentation versions
- Deprecated feature documentation
- Historical reports and analysis
- Temporary documentation files
- Session logs and implementation reports

### Archive Structure
```
_archive/
├── old-versions/     # Previous documentation versions
├── deprecated/       # Deprecated feature docs
├── temp-files/       # Temporary documentation
├── reports/          # Historical reports and analysis
└── sessions/         # Session logs and summaries
```

### Archive Process
1. Move outdated content to appropriate `_archive/` subdirectory
2. Add date suffix to archived files: `old-guide-20241201.md`
3. Update any links pointing to archived content
4. Add entry to archive index if needed

## 🚀 Implementation Guidelines

### For New Documentation
1. Determine appropriate category and directory
2. Follow naming conventions
3. Use standard document template
4. Include in directory README.md index
5. Test all examples and links

### For Existing Documentation
1. Review against these standards
2. Reorganize if in wrong category
3. Update format to match template
4. Fix broken links and outdated content
5. Archive if no longer relevant

### For Major Changes
1. Update this standards document first
2. Communicate changes to team
3. Update existing docs gradually
4. Maintain backward compatibility where possible

## 🤖 Claude MPM-Specific Standards

### Framework vs Project Distinction
Always clarify context when writing documentation:

**FRAMEWORK Documentation** (this repository):
- Location: `/Users/masa/Projects/claude-mpm`
- Purpose: Develop and maintain the Claude MPM framework
- Audience: Framework developers, contributors
- Focus: Architecture, agent templates, core services

**PROJECT Documentation** (user installations):
- Location: Any directory where `mpm-init` has been run
- Purpose: Use Claude MPM for multi-agent orchestration
- Audience: End users, project teams
- Focus: Usage, configuration, workflows

### Agent System Documentation
- **Agent Templates**: Document in `reference/` with schema validation
- **Agent Workflows**: Document in `guides/` with practical examples
- **Agent Creation**: Document in `developer/` with step-by-step instructions
- **Agent Deployment**: Document in `deployment/` with operational guidance

### Multi-Agent Orchestration Patterns
- Document delegation patterns between PM and specialist agents
- Include complete workflow examples with expected interactions
- Show error handling and circuit breaker patterns
- Provide troubleshooting for common orchestration issues

### Claude Code Integration
- Always specify minimum Claude Code CLI version requirements
- Include setup verification steps
- Document MCP integration patterns
- Provide troubleshooting for Claude Code-specific issues

### Version Management
- Document agent versioning and compatibility
- Include migration guides for breaking changes
- Maintain compatibility matrices
- Archive deprecated agent versions

## 📈 Documentation Metrics

### Coverage Requirements
- ✅ Installation and setup (Claude Code + Claude MPM)
- ✅ Core features and multi-agent workflows
- ✅ Agent system architecture and patterns
- ✅ Troubleshooting and FAQ
- ✅ Developer guides and contribution workflows
- ✅ API reference and CLI documentation
- ✅ Deployment and operations
- ✅ Configuration and customization

### Quality Metrics
- All code examples tested with current versions
- All links validated monthly
- All screenshots current (within 6 months)
- All agent examples deployable and functional
- All CLI commands verified with latest version

## 🔄 Maintenance Schedule

### Weekly
- Review new GitHub issues for documentation gaps
- Update any changed CLI commands or APIs
- Verify agent deployment examples still work

### Monthly
- Full link validation across all documentation
- Update version numbers and compatibility matrices
- Review and archive outdated session documents
- Update screenshots and visual examples

### Quarterly
- Comprehensive documentation audit
- Consolidate overlapping content
- Update examples with latest best practices
- Review archive retention policy

### Release Cycle
- Update all version references
- Test all getting-started workflows
- Update troubleshooting with new known issues
- Verify all cross-references are accurate

---

**Maintainers**: Update this document when changing documentation organization or standards.

**Contributors**: Follow these standards for all documentation contributions.

**Framework Developers**: Ensure all agent templates and core services are documented according to these standards.
