# Qa Agent Memory - claude-mpm

<!-- MEMORY LIMITS: 8KB max | 10 sections max | 15 items per section -->
<!-- Last Updated: 2025-08-06 13:38:32 | Auto-updated by: system -->

## Project Architecture

- Core modules: claude_mpm, claude_mpm/ui, claude_mpm/experimental, claude_mpm/core
- E2E tests in tests/e2e/ and integration tests in tests/integration/
- Main directories: src, tests, docs, config
- Tests organized in tests/ directory with test_ prefix for files
- Use mock and patch for unit testing external dependencies
- Use monkeypatch fixture for mocking in pytest
- Use pytest framework with fixtures for testing
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
- Run tests after significant changes using ./scripts/run_all_tests.sh
- Test memory optimization with memory manager's get_memory_status() method
- Use conftest.py for shared fixtures across test modules
- Use npm for dependency management
- Use tmp_path fixture for temporary files in tests

## Domain-Specific Knowledge
<!-- Agent-specific knowledge for claude-mpm domain -->

- Key project terms: experimental, security, claude, module

## Effective Strategies
<!-- Successful approaches discovered through experience -->

## Common Mistakes to Avoid

- Don't ignore virtual environment - always activate before work
- Never run tests in production environment - check config before running
- Avoid app context issues - use proper application factory
- Avoid circular imports - use late imports when needed
- Avoid using interactive git commands like git rebase -i or git add -i in automated tests
- Missing test coverage causes deployment failures - run ./scripts/run_e2e_tests.sh

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
- Memory system supports auto-learning when enabled in config
- Run E2E tests after significant changes using ./scripts/run_e2e_tests.sh
- Tech stack: python

## Recent Learnings
<!-- Most recent discoveries and insights -->

- Updated memory for qa - second entry
- Test memory content for qa agent - operational validation at 2025-08-06T13:38:32.563466
## Project Context
claude-mpm: python (with c_cpp, node_js) web application

- Key patterns: Unit Testing, Object Oriented
- Main modules: claude_mpm, claude_mpm/ui, claude_mpm/experimental, claude_mpm/core
- Testing: Tests in /tests/ directory
- Uses: flask