# Research Agent Memory - claude-mpm

<!-- MEMORY LIMITS: 16KB max | 10 sections max | 15 items per section -->
<!-- Last Updated: 2025-08-05 21:02:32 | Auto-updated by: system -->

## Project Context
claude-mpm: python (with c_cpp, node_js) web application
- Main modules: claude_mpm, claude_mpm/ui, claude_mpm/experimental, claude_mpm/core
- Uses: flask
- Testing: Python unittest pattern
- Key patterns: Unit Testing, Object Oriented

## Project Architecture
- Memory routing uses keyword analysis and pattern matching for agent selection
- Agent schemas use JSON Schema validation with agent_schema.json
- ProjectAnalyzer provides intelligent project analysis for context-aware operations
- Tree-sitter integration for AST-level code analysis supporting 41+ languages
- Agent registry with dynamic discovery and template-based agent definitions
- Multi-agent framework with extensible hook system for customization
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
- Memory system supports cross-referencing and pattern analysis across agents
- Use caching for expensive project analysis operations
- Use npm for dependency management
- Follow python unittest pattern
- Follow tests in /tests/ directory
- Key config files: package.json, requirements.txt, pyproject.toml

## Domain-Specific Knowledge
<!-- Agent-specific knowledge for claude-mpm domain -->
- Key project terms: module, agents, terminal, security
- Focus on code analysis, pattern discovery, and architectural insights
- Prioritize documentation analysis for comprehensive understanding

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
- Agent memory files use structured markdown with sections limited to 15 items each
- Key domain terms: agent delegation, hook priorities, memory routing, schema validation
- Framework supports plugin architecture with pre/post delegation hooks
- Tech stack: python
- API patterns: REST API
- Key dependencies: ai-trackdown-pytools, pyyaml, python-dotenv, rich
- Documentation: README.md, CHANGELOG.md, docs/VERSIONING.md

## Recent Learnings
<!-- Most recent discoveries and insights -->
