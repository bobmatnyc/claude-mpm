# Project Memory Configuration

This project uses KuzuMemory for intelligent context management.

## Project Information
- **Path**: /Users/masa/Projects/claude-mpm
- **Language**: Python
- **Framework**: FastAPI

## Memory Integration

KuzuMemory is configured to enhance all AI interactions with project-specific context.

**Note:** kuzu-memory integration is managed internally by MPM's hook delegation system, not through direct Claude Code hooks.

### Available Commands:
- `kuzu-memory enhance <prompt>` - Enhance prompts with project context
- `kuzu-memory learn <content>` - Store learning from conversations (async)
- `kuzu-memory recall <query>` - Query project memories
- `kuzu-memory stats` - View memory statistics

### MCP Tools Available:
When interacting with Claude Desktop, the following MCP tools are available:
- **kuzu_enhance**: Enhance prompts with project memories
- **kuzu_learn**: Store new learnings asynchronously
- **kuzu_recall**: Query specific memories
- **kuzu_stats**: Get memory system statistics

## Project Context

Claude Multi-Agent Project Manager - Orchestrate Claude with agent delegation and ticket tracking

## Key Technologies
- Python
- Flask
- Flask
- FastAPI

## Development Guidelines
- Use kuzu-memory enhance for all AI interactions
- Store important decisions with kuzu-memory learn
- Query context with kuzu-memory recall when needed
- Keep memories project-specific and relevant

## Memory Guidelines

- Store project decisions and conventions
- Record technical specifications and API details
- Capture user preferences and patterns
- Document error solutions and workarounds
