# Data Engineer Agent Memory - claude-mpm

<!-- MEMORY LIMITS: 8KB max | 10 sections max | 15 items per section -->
<!-- Last Updated: 2025-08-06 13:38:35 | Auto-updated by: system -->

## Project Context
claude-mpm: python (with node_js, python) web application
- Main modules: claude_mpm, claude_mpm/ui, claude_mpm/experimental, claude_mpm/core
- Uses: flask
- Testing: Python unittest pattern
- Key patterns: Object Oriented, Unit Testing

## Project Architecture
- Web Application with python implementation
- Main directories: src, tests, docs, config
- Core modules: claude_mpm, claude_mpm/ui, claude_mpm/experimental, claude_mpm/core
- Web framework stack: flask

## Coding Patterns Learned
- Python project: use type hints, follow PEP 8 conventions
- Flask patterns: blueprint organization, app factory pattern
- Project uses: Object Oriented
- Project uses: Unit Testing
- Project uses: Async Programming

## Implementation Guidelines
- Use npm for dependency management
- Follow python unittest pattern
- Follow tests in /tests/ directory
- Key config files: package.json, requirements.txt, pyproject.toml

## Domain-Specific Knowledge
<!-- Agent-specific knowledge for claude-mpm domain -->
- Key project terms: security, experimental, terminal, agents
- Focus on implementation patterns, coding standards, and best practices

## Effective Strategies
<!-- Successful approaches discovered through experience -->

## Common Mistakes to Avoid
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
- Tech stack: python
- API patterns: REST API
- Key dependencies: ai-trackdown-pytools, pyyaml, python-dotenv, rich
- Documentation: README.md, CHANGELOG.md, docs/VERSIONING.md

## Recent Learnings
<!-- Most recent discoveries and insights -->

- Updated memory for data_engineer - second entry
- Test memory content for data_engineer agent - operational validation at 2025-08-06T13:38:35.510148