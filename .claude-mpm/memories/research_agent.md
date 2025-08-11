# Research Agent Memory - claude-mpm

<!-- MEMORY LIMITS: 16KB max | 10 sections max | 15 items per section -->
<!-- Last Updated: 2025-08-06 13:38:32 | Auto-updated by: system -->

## Project Architecture

- Agent registry with dynamic discovery and template-based agent definitions
- Agent schemas use JSON Schema validation with agent_schema.json
- Core modules: claude_mpm, claude_mpm/ui, claude_mpm/experimental, claude_mpm/core
- Main directories: src, tests, docs, config
- Memory routing uses keyword analysis and pattern matching for agent selection
- Multi-agent framework with extensible hook system for customization
- ProjectAnalyzer provides intelligent project analysis for context-aware operations
- Tree-sitter integration for AST-level code analysis supporting 41+ languages
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
- Memory system supports cross-referencing and pattern analysis across agents
- Use caching for expensive project analysis operations
- Use npm for dependency management

## Domain-Specific Knowledge
<!-- Agent-specific knowledge for claude-mpm domain -->

- Focus on code analysis, pattern discovery, and architectural insights
- Key project terms: module, agents, terminal, security
- Prioritize documentation analysis for comprehensive understanding

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

- Agent memory files use structured markdown with sections limited to 15 items each
- API patterns: REST API
- Documentation: README.md, CHANGELOG.md, docs/VERSIONING.md
- Framework supports plugin architecture with pre/post delegation hooks
- Key dependencies: ai-trackdown-pytools, pyyaml, python-dotenv, rich
- Key domain terms: agent delegation, hook priorities, memory routing, schema validation
- Tech stack: python

## Recent Learnings
<!-- Most recent discoveries and insights -->

- Updated memory for research - second entry
- Test memory content for research agent - operational validation at 2025-08-06T13:38:32.563019
## Project Context
claude-mpm: python (with c_cpp, node_js) web application

- Key patterns: Unit Testing, Object Oriented
- Main modules: claude_mpm, claude_mpm/ui, claude_mpm/experimental, claude_mpm/core
- Testing: Python unittest pattern
- Uses: flask