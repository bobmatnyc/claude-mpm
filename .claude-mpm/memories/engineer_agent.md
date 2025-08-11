# Engineer Agent Memory - claude-mpm

<!-- MEMORY LIMITS: 8KB max | 10 sections max | 15 items per section -->
<!-- Last Updated: 2025-08-06 13:38:32 | Auto-updated by: system -->

## Project Architecture

- All imports use full package name: from claude_mpm.module import ...
- Core modules: claude_mpm, claude_mpm/ui, claude_mpm/experimental, claude_mpm/core
- Follow service-oriented architecture - business logic in services/ directory
- Hook system uses priority-based execution: priority 0-100, lower executes first
- Main directories: src, tests, docs, config
- Use CLI modular structure: commands in cli/commands/, main entry in cli/__init__.py
- Use environment variables with CLAUDE_PM_ prefix for configuration
- Use LoggerMixin for consistent logging across services
- Use PathResolver.get_project_root() for consistent path resolution
- Use src/ layout pattern for Python packages - all main modules under src/claude_mpm/
- Web Application with python implementation
- Web framework stack: flask

## Coding Patterns Learned

- Python project: use type hints, follow PEP 8 conventions
- Flask patterns: blueprint organization, app factory pattern
- Project uses: Async Programming
- Project uses: Object Oriented
- Project uses: Unit Testing

## Implementation Guidelines

- Build script 'postinstall': node scripts/postinstall.js
- Configuration uses ConfigurationManager with caching enabled
- Follow python unittest pattern
- Follow tests in /tests/ directory
- Key config files: package.json, requirements.txt, pyproject.toml
- Memory files limited to 8KB with auto-truncation - use concise, actionable items
- Use async/await for I/O operations to improve performance
- Use dataclasses for structured data with @dataclass decorator
- Use npm for dependency management

## Domain-Specific Knowledge
<!-- Agent-specific knowledge for claude-mpm domain -->

- Focus on implementation patterns, coding standards, and best practices
- Key project terms: terminal, wrapper, security, module

## Effective Strategies
<!-- Successful approaches discovered through experience -->

## Common Mistakes to Avoid

- Don't ignore virtual environment - always activate before work
- Never place scripts in project root - all scripts go in /scripts/ directory
- Never place test files outside /tests/ directory
- Never update git config in automated scripts - use read-only git operations
- Avoid app context issues - use proper application factory
- Avoid circular imports - use late imports when needed
- Avoid using search commands like find and grep in bash - use Grep, Glob, or Task tools instead

## Integration Points

- flask web framework integration
- REST API integration pattern

## Performance Considerations

- Consider caching for expensive operations
- Implement appropriate caching strategies
- Optimize static asset delivery
- Use list comprehensions over loops where appropriate

## Current Technical Context

- Python dependencies: ai-trackdown-pytools>=1.4.0, pyyaml>=6.0, python-dotenv>=0.19.0, rich>=13.0.0, click>=8.0.0
- AgentMemoryManager uses ProjectAnalyzer for context-aware memory generation
- API patterns: REST API
- Documentation: README.md, CHANGELOG.md, docs/issue-tracking.md
- Tech stack: python
- Web dashboard uses Socket.IO for real-time memory system monitoring

## Recent Learnings
<!-- Most recent discoveries and insights -->

- Updated memory for engineer - second entry
- Test memory content for engineer agent - operational validation at 2025-08-06T13:38:32.562216
## Project Context
claude-mpm: python (with node_js, c_cpp) web application

- Key patterns: Unit Testing, Object Oriented
- Main modules: claude_mpm, claude_mpm/ui, claude_mpm/experimental, claude_mpm/core
- Testing: Python unittest pattern
- Uses: flask