# Claude MPM 3.6.2 Release Notes

**Release Date**: August 13, 2025  
**Version**: 3.6.2  
**Previous Version**: 3.5.6

---

## 🎯 Executive Summary

Claude MPM 3.6.2 introduces **three major architectural improvements** that significantly enhance performance, maintainability, and developer experience:

1. **🔧 Dynamic Agent Dependencies** - Smart dependency loading that only checks and installs packages for deployed agents, reducing installation size by up to 90% and improving startup performance
2. **📋 Enhanced PM Instructions** - Separation of framework requirements from customizable PM instructions with structured response formats for better orchestration
3. **🚀 Improved Agent Deployment** - State tracking, dependency caching, and better deployment verification with comprehensive audit tools

These improvements make Claude MPM more efficient, maintainable, and suitable for production environments while preserving the flexibility that makes it adaptable to diverse project needs.

---

## 🤖 New Agents

### Code Analyzer Agent

**New specialized agent for advanced code analysis and quality assessment.**

The Code Analyzer agent brings sophisticated static code analysis capabilities to Claude MPM using AST (Abstract Syntax Tree) parsing for deep structural insights.

#### Key Features
- **AST-Powered Analysis**: Uses tree-sitter for multi-language support and Python's native `ast` module for Python-specific analysis
- **Pattern Detection**: Identifies code quality issues, security vulnerabilities, and performance bottlenecks
- **Structural Analysis**: Detects god objects/functions, circular dependencies, code duplication, and architectural issues
- **Security Scanning**: Finds hardcoded secrets, SQL injection risks, command injection, unsafe deserialization
- **Performance Analysis**: Identifies synchronous I/O in async contexts, nested loops, memory leaks
- **Quality Metrics**: Measures complexity, coupling, cohesion, and generates actionable recommendations

#### Advanced Capabilities
- **Multi-language Support**: Works with Python, JavaScript, TypeScript, Java, C/C++, Go, Rust, and more via tree-sitter
- **Comprehensive Thresholds**: Configurable complexity (>10 high, >20 critical), function length (>50 long, >100 critical), class size limits
- **Dependency Analysis**: Requires tree-sitter>=0.21.0 and tree-sitter-language-pack>=0.8.0 for full functionality
- **Dynamic Script Generation**: Creates analysis scripts on-the-fly for specific codebase needs
- **Prioritized Reporting**: Focuses on actionable issues with specific file:line references and remediation examples

#### Example Use Cases
```bash
# Analyze codebase for quality issues
claude-mpm run -a code_analyzer -i "Analyze the codebase for security vulnerabilities and performance bottlenecks"

# Generate comprehensive code quality report
claude-mpm run -a code_analyzer -i "Create a detailed code analysis report with complexity metrics and improvement recommendations"
```

#### Dependencies
The Code Analyzer agent automatically manages its dependencies through the dynamic dependency system:
- **Python packages**: tree-sitter, tree-sitter-language-pack
- **System requirements**: python3, git
- **Installation**: Dependencies are automatically installed when the agent is first used

This agent is particularly valuable for:
- Code review automation
- Technical debt assessment
- Security vulnerability scanning
- Performance optimization identification
- Architectural quality evaluation
- Refactoring planning and prioritization

---

## 🔧 Major Features

### 1. Dynamic Agent Dependencies System

**Problem Solved**: Previous versions required installing all possible agent dependencies upfront (~500 MB), even if most agents were never used.

**Solution**: Smart dependency loading that only manages dependencies for agents actually deployed to your project.

#### Key Benefits
- **90% smaller installations**: Core installation ~50 MB vs ~500 MB with all dependencies
- **Faster startup**: No need to load unused dependencies, cached checks per session
- **Better compatibility**: Avoid version conflicts from unused agents
- **Environment awareness**: Python 3.13 compatibility checking with helpful warnings

#### New Files Created
- `src/claude_mpm/utils/agent_dependency_loader.py` - Core dynamic loading logic
- `src/claude_mpm/utils/dependency_cache.py` - Intelligent caching system
- `src/claude_mpm/utils/dependency_strategies.py` - Environment-specific strategies
- `docs/DYNAMIC_DEPENDENCIES.md` - Complete user guide

#### State Files
- `.claude/agents/.dependency_cache` - Cached dependency check results
- `.claude/agents/.mpm_deployment_state` - Agent deployment state tracking

#### Usage Examples

```bash
# Check dependencies for deployed agents only
claude-mpm agents deps-check

# Install missing dependencies automatically
claude-mpm agents deps-install

# Export dependencies for requirements.txt
claude-mpm agents deps-list --format pip > agent-requirements.txt
```

#### Smart Caching Logic

```python
# Automatic caching based on deployment hash
loader = AgentDependencyLoader()
has_changed, deployment_hash = loader.has_agents_changed()

if not has_changed:
    # Use cached results - no dependency checks needed
    cached_results = loader.get_cached_check_results()
```

### 2. Enhanced PM Instructions Architecture

**Problem Solved**: PM instructions were monolithic and hard to customize for different projects while maintaining framework integrity.

**Solution**: Separation of non-negotiable framework requirements from customizable project instructions.

#### Architecture Components

1. **BASE_PM.md** - Framework requirements (non-modifiable)
   - TodoWrite prefix rules: `[Agent]` delegation patterns
   - Memory management protocols
   - Structured response format requirements
   - Template variable injection points

2. **INSTRUCTIONS.md** - Customizable instructions (project-specific)
   - Custom workflows and priorities
   - Domain-specific knowledge
   - Communication preferences
   - Project agent configurations

#### Template Variables

```markdown
**Today's Date**: {{current-date}}
Apply date awareness to all time-sensitive tasks and decisions.

{{agent-capabilities}}
# Dynamically generated list of available agents
```

#### Runtime Assembly Process

1. Load custom INSTRUCTIONS.md first
2. Append BASE_PM.md framework requirements (overrides conflicts)
3. Resolve template variables with current system state
4. Inject complete instruction set via `--append-system-prompt`

#### Structured Response Format

PM now provides structured JSON responses for better logging and tracking:

```json
{
  "pm_summary": true,
  "request": "Implement OAuth2 authentication with multiple providers",
  "agents_used": {
    "Research": 1,
    "Engineer": 2, 
    "Security": 1,
    "QA": 1,
    "Documentation": 1
  },
  "tasks_completed": [
    "[Research] Analyzed authentication patterns",
    "[Engineer] Implemented OAuth2 service",
    "[Security] Audited implementation",
    "[QA] Tested all flows",
    "[Documentation] Updated API docs"
  ],
  "files_affected": [
    "src/auth/oauth_service.py",
    "config/oauth_settings.json",
    "tests/test_oauth.py"
  ],
  "next_steps": [
    "Configure OAuth credentials in production",
    "Monitor token refresh performance"
  ]
}
```

### 3. Improved Agent Deployment System

**Problem Solved**: Agent deployment lacked comprehensive verification and audit capabilities.

**Solution**: Enhanced deployment workflow with state tracking, verification, and audit tools.

#### New State Tracking
- **Deployment verification**: Ensures agents are properly converted and deployed
- **Dependency tracking**: Links agents to their dependency requirements
- **Change detection**: Smart detection of when redeployment is needed

#### Comprehensive Audit Script

New `scripts/audit_documentation.py` provides comprehensive documentation analysis:

```bash
# Basic documentation audit  
python scripts/audit_documentation.py

# Detailed analysis with auto-fixes
python scripts/audit_documentation.py --verbose --fix

# CI/CD integration
python scripts/audit_documentation.py --json --strict
```

#### Audit Features
- Validates structure compliance with STRUCTURE.md
- Detects duplicate content across agent files
- Checks naming conventions
- Identifies broken internal links
- Reports misplaced files
- Validates numbered directory README requirements

---

## 🛠 Developer Experience Improvements

### Enhanced Response Logging

**Default Debug Mode**: Response logging now defaults to debug mode with better configuration management:

```yaml
# .claude-mpm/configuration.yaml
response_logging:
  enabled: true
  use_async: true
  format: json
  debug: true  # New default
```

### Better Error Messages

- **Dependency conflicts**: Clear Python 3.13 compatibility warnings
- **Deployment failures**: Detailed agent deployment error reporting  
- **Configuration issues**: Helpful validation messages for config files

### CI/CD Integration

```yaml
# GitHub Actions example
- name: Verify Agent Dependencies
  run: |
    if ! claude-mpm agents deps-check; then
      claude-mpm agents deps-install --dry-run
      exit 1
    fi

- name: Audit Documentation
  run: python scripts/audit_documentation.py --json --strict
```

---

## ⚡ Performance Enhancements

### Startup Performance
- **Faster dependency checks**: Only check deployed agents, with intelligent caching
- **Reduced memory usage**: No loading of unused agent dependencies
- **Smart cache invalidation**: Change detection avoids unnecessary work

### Installation Size
- **Core installation**: ~50 MB (was ~500 MB with all dependencies)
- **On-demand loading**: Install dependencies only when agents are deployed
- **Selective installation**: Install only for specific agents you use

### Caching Improvements
- **Dependency cache**: 24-hour TTL with deployment hash-based invalidation
- **State persistence**: `.mpm_deployment_state` tracks agent changes
- **Environment-aware**: Cache keys include Python version and platform

---

## 🐛 Bug Fixes

### Agent Deployment
- Fixed duplication issues in agent deployment process
- Resolved path resolution problems in `.claude/agents/` directory
- Corrected agent template variable resolution
- Prevented PM agent from being deployed as subagent

### Configuration Management
- Fixed configuration file validation edge cases
- Resolved YAML parsing issues with special characters
- Improved error handling for missing configuration files

### Memory Management
- Enhanced agent memory routing with clearer error messages
- Fixed memory storage task format inconsistencies
- Improved memory type classification accuracy

### Response Logging
- Resolved hook integration issues causing missed responses
- Fixed structured response format parsing edge cases
- Improved async logging error handling and recovery

### Version Management
- Resolved version numbering discrepancy (corrected from 3.7.1 to 3.6.2)
- Maintained proper semantic versioning sequence

---

## 🔄 Migration Guide

### Upgrading from 3.5.x

1. **Update Installation**
   ```bash
   pip install --upgrade claude-mpm
   # Version should show 3.6.2
   claude-mpm --version
   ```

2. **Check Agent Dependencies**
   ```bash
   # After upgrade, check what dependencies are needed
   claude-mpm agents deps-check
   
   # Install only what's required for your deployed agents
   claude-mpm agents deps-install
   ```

3. **Update Configuration (Optional)**
   ```yaml
   # Add to .claude-mpm/configuration.yaml for enhanced logging
   response_logging:
     enabled: true
     debug: true
     format: json
   ```

4. **Verify Deployment**
   ```bash
   # Ensure agents are properly deployed
   claude-mpm agents deploy
   
   # Run documentation audit
   python scripts/audit_documentation.py
   ```

### Breaking Changes
- **None**: Version 3.6.2 is fully backward compatible
- **Deprecated**: Some internal APIs have been deprecated (will be removed in 4.0.0)

### Configuration Changes
- **Response logging**: Now defaults to debug mode for better development experience
- **Dependency checking**: Automatically enabled at startup (can be disabled)
- **Caching**: Automatically enabled with intelligent invalidation

---

## 📝 Code Examples

### Using Dynamic Dependencies

```python
from claude_mpm.utils.agent_dependency_loader import AgentDependencyLoader

# Check dependencies for deployed agents
loader = AgentDependencyLoader(auto_install=False)
results = loader.load_and_check()

# Print formatted report
report = loader.format_report(results)
print(report)

# Auto-install missing dependencies
auto_loader = AgentDependencyLoader(auto_install=True)
results = auto_loader.load_and_check()
```

### Custom PM Instructions

```markdown
# Project-Specific INSTRUCTIONS.md

## E-Commerce Platform Context
Working on high-traffic e-commerce with strict security requirements.

## Custom Workflows  
- All payment tasks require Security agent review
- Performance testing required for checkout changes
- Include load testing results in documentation

## Agent Priorities
1. Security first for payment flows
2. Performance validation for checkout
3. Comprehensive documentation for compliance
```

### Dependency Caching

```python
from claude_mpm.utils.dependency_cache import SmartDependencyChecker

# Smart dependency checking with caching
checker = SmartDependencyChecker()
should_check, reason = checker.should_check_dependencies(deployment_hash)

if should_check:
    results, was_cached = checker.get_or_check_dependencies(loader)
    print(f"Dependencies checked: {not was_cached}")
```

### Documentation Audit Integration

```bash
# Run in CI pipeline
python scripts/audit_documentation.py --json --strict > audit_results.json

# Check exit code
if [ $? -ne 0 ]; then
    echo "Documentation audit failed"
    cat audit_results.json
    exit 1
fi
```

---

## 🔍 Technical Details

### New Dependency Strategy

The dynamic dependency system uses a three-phase approach:

1. **Discovery Phase**: Scan `.claude/agents/` for deployed agents
2. **Resolution Phase**: Load dependency configs from PROJECT → USER → SYSTEM tiers  
3. **Verification Phase**: Check installed packages with version compatibility

### Cache Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│ Deployment Hash │────▶│ Dependency Cache │────▶│ Check Results   │
│ (SHA256)        │     │ (.dependency_    │     │ (JSON)          │
└─────────────────┘     │  cache)          │     └─────────────────┘
                        └──────────────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │   TTL Expiration     │
                    │   (24 hours)         │
                    └──────────────────────┘
```

### PM Instruction Pipeline

```
INSTRUCTIONS.md ──┐
                  ├──▶ Template Resolution ──▶ BASE_PM.md ──▶ Claude API
Template Vars ────┘    {{current-date}}                     
                       {{agent-capabilities}}
```

---

## 🎉 Acknowledgments

We extend our heartfelt gratitude to the members of our WhatsApp support group whose invaluable feedback, thorough testing, and continuous support made Claude MPM 3.6.2 possible:

- **Chris Bunk**
- **Daniel Seltzer**
- **Dirk Liebich**
- **Eddie Hudson**
- **Oliver Anson**

Their dedication to quality assurance, willingness to test beta features, and constructive feedback have been instrumental in shaping this release. The robust architecture and enhanced developer experience in version 3.6.2 are a direct result of their collaborative efforts and commitment to excellence.

---

## 🔗 Additional Resources

- **Dynamic Dependencies Guide**: `docs/DYNAMIC_DEPENDENCIES.md`
- **PM Architecture**: `docs/developer/02-core-components/pm-architecture.md`
- **Response Logging Config**: `docs/RESPONSE_LOGGING_CONFIG.md`  
- **Project Structure**: `docs/STRUCTURE.md`
- **Deployment Guide**: `docs/DEPLOY.md`

---

## 🚀 Roadmap

We're excited to hear what you want to see next! Coming in future releases:

- **Virtual Environment Integration**: Auto-create isolated environments per project
- **Dependency Conflict Resolution**: Interactive resolution of version conflicts  
- **Enhanced Memory System**: Cross-agent memory sharing and synchronization
- **Performance Monitoring**: Built-in performance tracking and optimization suggestions
- **Advanced Audit Tools**: Deeper code quality and security analysis

Share your ideas and feedback with us - your input shapes the future of Claude MPM!

---

**Full Changelog**: [View all changes since v3.5.6](https://github.com/your-repo/claude-mpm/compare/v3.5.6...v3.6.2)

For questions or issues, please visit our [GitHub Issues](https://github.com/your-repo/claude-mpm/issues) page.