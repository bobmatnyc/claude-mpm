# Documentation Agent Memory - claude-mpm

<!-- MEMORY LIMITS: 8KB max | 10 sections max | 15 items per section -->
<!-- Last Updated: 2025-08-05 21:02:19 | Auto-updated by: system -->

## Project Context
claude-mpm: python (with node_js, python) web application
- Main modules: claude_mpm, claude_mpm/ui, claude_mpm/experimental, claude_mpm/core
- Uses: flask
- Testing: Tests in /tests/ directory
- Key patterns: Unit Testing, Object Oriented

## Project Architecture
- Code includes docstrings with WHY explanations for architectural decisions
- Include WHY and DESIGN DECISION comments in code for architectural context
- Use markdown format with clear headings and code examples
- Documentation follows structured format: README.md, docs/STRUCTURE.md, docs/QA.md, etc.
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
- Use conventional commits for automatic versioning: feat:, fix:, feat!:
- Always refer to docs/STRUCTURE.md when documenting file placement
- Use npm for dependency management
- Follow tests in /tests/ directory
- Follow python unittest pattern
- Key config files: package.json, requirements.txt, pyproject.toml

## Domain-Specific Knowledge
<!-- Agent-specific knowledge for claude-mpm domain -->
- Key project terms: experimental, security, terminal, wrapper

## Effective Strategies
<!-- Successful approaches discovered through experience -->

## Common Mistakes to Avoid
- Avoid creating README files or markdown documentation without explicit user request
- Never create documentation files without explicit request from user
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
- Memory system builds documentation from project analysis automatically
- Tech stack: python
- API patterns: REST API
- Key dependencies: ai-trackdown-pytools, pyyaml, python-dotenv, rich
- Documentation: README.md, CHANGELOG.md, docs/VERSIONING.md

## Recent Learnings
<!-- Most recent discoveries and insights -->
