# Release Notes - v4.1.11

## 🚀 New Features

### MPM-Init Command
Introducing the new `claude-mpm mpm-init` command that revolutionizes project initialization for optimal AI agent collaboration!

**What it does:**
- Automatically sets up projects for maximum success with Claude Code and Claude MPM
- Delegates to the Agentic Coder Optimizer agent for comprehensive configuration
- Creates CLAUDE.md documentation optimized for AI understanding
- Establishes **ONE way to do ANYTHING** - removing ambiguity from workflows

**Key capabilities:**
- 🎯 Support for multiple project types (web, api, cli, library, mobile, desktop, fullstack)
- 🛠️ Framework-specific optimization (React, Vue, Django, FastAPI, Express, etc.)
- 🔄 Automatic fallback to Python venv when mamba/conda environments fail
- 📝 Comprehensive documentation generation
- 🧠 Memory system initialization for project knowledge retention
- ⚙️ Development tool configuration (linting, formatting, testing)

**Usage:**
```bash
# Basic initialization
claude-mpm mpm-init

# With project type
claude-mpm mpm-init --project-type web --framework react

# Force venv usage (bypass mamba)
claude-mpm mpm-init --use-venv
```

### Git Branding Customization
Claude MPM now automatically customizes git commits and PRs with proper branding!

**Features:**
- 🤖👥 New emoji representing AI orchestrating a team of agents
- Automatic replacement of Claude Code references with Claude MPM
- Updated repository URLs point to your GitHub project
- Custom git hooks and wrapper scripts

**The new signature:**
```
🤖👥 Generated with [Claude MPM](https://github.com/bobmatnyc/claude-mpm)

Co-Authored-By: Claude <noreply@anthropic.com>
```

## 🎨 Dashboard Enhancements

### Code Tree Visualization
- Enhanced code tree component with improved file navigation
- Security fixes for path validation preventing directory traversal
- Better event handling and filtering
- Optimized performance for large codebases

## 🐛 Bug Fixes

### Environment Handling
- Fixed mamba/conda environment dependency issues
- Added automatic fallback mechanisms for environment failures
- Improved error messages and recovery strategies

### Command Construction
- Corrected argument ordering for CLI commands
- Fixed "filename too long" errors by using temporary files
- Removed invalid --agent flag usage

## 📚 Documentation

- New comprehensive guide for mpm-init command: `docs/user/commands/mpm-init.md`
- Git branding customization guide: `docs/user/claude-mpm-branding.md`
- Updated examples and troubleshooting sections

## 🔧 Technical Improvements

- Better subprocess handling and error recovery
- Enhanced structure linting and auto-fixing
- Improved test coverage for new features
- Code quality improvements across the codebase

## 📦 Installation

```bash
# Update via pip
pip install --upgrade claude-mpm

# Or with npm
npm install -g claude-mpm@latest
```

## 🙏 Acknowledgments

This release includes contributions from the Claude MPM community and improvements driven by user feedback. Special thanks to all who reported issues and suggested enhancements!

## 🔮 What's Next

- Dynamic agent memory management improvements
- Enhanced dashboard real-time features
- More project templates for mpm-init
- Expanded framework support

---

**Full Changelog**: https://github.com/bobmatnyc/claude-mpm/compare/v4.1.10...v4.1.11