# Engineer Agent Memory - claude-mpm

<!-- MEMORY LIMITS: 8KB max | 10 sections max | 15 items per section -->
<!-- Last Updated: 2025-08-05 21:02:35 | Auto-updated by: system -->

## Project Context
claude-mpm: python (with node_js, c_cpp) web application
- Main modules: claude_mpm, claude_mpm/ui, claude_mpm/experimental, claude_mpm/core
- Uses: flask
- Testing: Python unittest pattern
- Key patterns: Unit Testing, Object Oriented

## Project Architecture
- Use environment variables with CLAUDE_PM_ prefix for configuration
- Use PathResolver.get_project_root() for consistent path resolution
- Use LoggerMixin for consistent logging across services
- Hook system uses priority-based execution: priority 0-100, lower executes first
- Use CLI modular structure: commands in cli/commands/, main entry in cli/__init__.py
- All imports use full package name: from claude_mpm.module import ...
- Follow service-oriented architecture - business logic in services/ directory
- Use src/ layout pattern for Python packages - all main modules under src/claude_mpm/
- Web Application with python implementation
- Main directories: src, tests, docs, config
- Core modules: claude_mpm, claude_mpm/ui, claude_mpm/experimental, claude_mpm/core
- Web framework stack: flask

## Coding Patterns Learned
- Python project: use type hints, follow PEP 8 conventions
- Flask patterns: blueprint organization, app factory pattern
- Project uses: Unit Testing
- Project uses: Object Oriented
- Project uses: Async Programming

## Implementation Guidelines
- Use async/await for I/O operations to improve performance
- Configuration uses ConfigurationManager with caching enabled
- Memory files limited to 8KB with auto-truncation - use concise, actionable items
- Use dataclasses for structured data with @dataclass decorator
- Build script 'postinstall': node scripts/postinstall.js
- Use npm for dependency management
- Follow python unittest pattern
- Follow tests in /tests/ directory
- Key config files: package.json, requirements.txt, pyproject.toml

## Domain-Specific Knowledge
<!-- Agent-specific knowledge for claude-mpm domain -->
- Key project terms: terminal, wrapper, security, module
- Focus on implementation patterns, coding standards, and best practices

## Effective Strategies
<!-- Successful approaches discovered through experience -->

## Common Mistakes to Avoid
- Avoid using search commands like find and grep in bash - use Grep, Glob, or Task tools instead
- Never update git config in automated scripts - use read-only git operations
- Never place test files outside /tests/ directory
- Never place scripts in project root - all scripts go in /scripts/ directory
- Avoid circular imports - use late imports when needed
- Don't ignore virtual environment - always activate before work
- Avoid app context issues - use proper application factory

## Integration Points
- flask web framework integration
- REST API integration pattern

## Performance Considerations
- Use list comprehensions over loops where appropriate
- Consider caching for expensive operations
- Implement appropriate caching strategies
- Optimize static asset delivery

## Current Technical Context
- Web dashboard uses Socket.IO for real-time memory system monitoring
- AgentMemoryManager uses ProjectAnalyzer for context-aware memory generation
- Python dependencies: ai-trackdown-pytools>=1.4.0, pyyaml>=6.0, python-dotenv>=0.19.0, rich>=13.0.0, click>=8.0.0
- Tech stack: python
- API patterns: REST API
- Key dependencies: ai-trackdown-pytools, pyyaml, python-dotenv, rich
- Documentation: README.md, CHANGELOG.md, docs/issue-tracking.md

## Recent Learnings
<!-- Most recent discoveries and insights -->
