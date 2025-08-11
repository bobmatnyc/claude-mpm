# Pm Agent Memory - claude-mpm

<!-- MEMORY LIMITS: 8KB max | 10 sections max | 15 items per section -->
<!-- Last Updated: 2025-08-06 13:38:35 | Auto-updated by: system -->

## Project Architecture

- Core modules: claude_mpm, claude_mpm/ui, claude_mpm/experimental, claude_mpm/core
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

- Follow python unittest pattern
- Follow tests in /tests/ directory
- Key config files: package.json, requirements.txt, pyproject.toml
- Use npm for dependency management

## Domain-Specific Knowledge
<!-- Agent-specific knowledge for claude-mpm domain -->

- Focus on project coordination, task delegation, and progress tracking
- Key project terms: terminal, wrapper, security, module
- Monitor integration points and cross-component dependencies

## Effective Strategies
<!-- Successful approaches discovered through experience -->

## Common Mistakes to Avoid

- Don't ignore virtual environment - always activate before work
- Avoid app context issues - use proper application factory
- Avoid circular imports - use late imports when needed

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
- Documentation: README.md, CHANGELOG.md, docs/issue-tracking.md
- Key dependencies: ai-trackdown-pytools, pyyaml, python-dotenv, rich
- Tech stack: python

## Recent Learnings
<!-- Most recent discoveries and insights -->

- Updated memory for pm - second entry
- Test memory content for pm agent - operational validation at 2025-08-06T13:38:35.509688
- contain "Helper functions should be pure functions when possible"
- all imports use the full package name: from claudempm
- initialize or use the hook system for memory integration
- now use YAML format for better structure and validation
- use absolute paths for file operations
- use release

## Project Context
claude-mpm: python (with node_js, c_cpp) web application

- Key patterns: Unit Testing, Object Oriented
- Main modules: claude_mpm, claude_mpm/ui, claude_mpm/experimental, claude_mpm/core
- Testing: Python unittest pattern
- Uses: flask