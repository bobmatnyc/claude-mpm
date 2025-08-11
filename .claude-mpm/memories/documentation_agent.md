# Documentation Agent Memory - claude-mpm

<!-- MEMORY LIMITS: 8KB max | 10 sections max | 15 items per section -->
<!-- Last Updated: 2025-08-06 13:38:32 | Auto-updated by: system -->

## Project Architecture

- Use markdown format with clear headings and code examples
- Code includes docstrings with WHY explanations for architectural decisions
- Core modules: claude_mpm, claude_mpm/ui, claude_mpm/experimental, claude_mpm/core
- Documentation follows structured format: README.md, docs/STRUCTURE.md, docs/QA.md, etc.
- Include WHY and DESIGN DECISION comments in code for architectural context
- Main directories: src, tests, docs, config
- Web Application with python implementation
- Web framework stack: flask

## Coding Patterns Learned

- Python project: use type hints, follow PEP 8 conventions
- Flask patterns: blueprint organization, app factory pattern
- Project uses: Async Programming
- Project uses: Object Oriented
- Project uses: Unit Testing

## Implementation Guidelines

- Always refer to docs/STRUCTURE.md when documenting file placement
- Follow python unittest pattern
- Follow tests in /tests/ directory
- Key config files: package.json, requirements.txt, pyproject.toml
- Use conventional commits for automatic versioning: feat:, fix:, feat!:
- Use npm for dependency management

## Domain-Specific Knowledge
<!-- Agent-specific knowledge for claude-mpm domain -->

- Key project terms: experimental, security, terminal, wrapper

## Effective Strategies
<!-- Successful approaches discovered through experience -->

## Common Mistakes to Avoid

- Don't ignore virtual environment - always activate before work
- Never create documentation files without explicit request from user
- Avoid app context issues - use proper application factory
- Avoid circular imports - use late imports when needed
- Avoid creating README files or markdown documentation without explicit user request

## Integration Points

- flask web framework integration
- REST API integration pattern

## Performance Considerations

- Consider caching for expensive operations
- Implement appropriate caching strategies
- Optimize static asset delivery
- Use list comprehensions over loops where appropriate

## Current Technical Context

- API patterns: REST API
- Documentation: README.md, CHANGELOG.md, docs/VERSIONING.md
- Key dependencies: ai-trackdown-pytools, pyyaml, python-dotenv, rich
- Memory system builds documentation from project analysis automatically
- Tech stack: python

## Recent Learnings
<!-- Most recent discoveries and insights -->

- Updated memory for documentation - second entry
- Test memory content for documentation agent - operational validation at 2025-08-06T13:38:32.563786
## Project Context
claude-mpm: python (with node_js, python) web application

- Key patterns: Unit Testing, Object Oriented
- Main modules: claude_mpm, claude_mpm/ui, claude_mpm/experimental, claude_mpm/core
- Testing: Tests in /tests/ directory
- Uses: flask