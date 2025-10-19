# Kuzu-Memory Integration

Claude MPM v4.4.1 introduces seamless integration with kuzu-memory, a powerful knowledge graph system that provides persistent context retention across conversations and sessions.

## Overview

The kuzu-memory integration enables Claude MPM to:
- Store and retrieve conversation memories in a graph database
- Enrich user prompts with relevant historical context
- Build up project-specific knowledge over time
- Provide intelligent context-aware responses

## What is Kuzu-Memory?

Kuzu-memory is a personal knowledge graph system that:
- Uses the Kuzu graph database for efficient storage and retrieval
- Provides semantic search capabilities for finding relevant memories
- Stores memories with tags and relationships for organized knowledge management
- Works with project-specific databases (each project gets its own memory store)

## Installation

Claude MPM now includes kuzu-memory as a required dependency, providing seamless memory integration out of the box:

1. **Automatic Installation**: kuzu-memory is installed automatically with Claude MPM
2. **No Manual Setup**: No additional installation steps required
3. **Built-in Integration**: Memory features are always available and ready to use

## How It Works

### Hook System Integration

The kuzu-memory integration works through Claude MPM's hook system:

1. **Prompt Enrichment** (Priority 10 - executes early):
   - Intercepts user prompts before processing
   - Retrieves relevant memories from the project's knowledge graph
   - Enriches prompts with contextual information
   - Maintains original prompt for reference

2. **Memory Storage** (Post-processing):
   - Extracts important information from conversations
   - Automatically stores learnings and key insights
   - Tags memories for better organization
   - Uses pattern matching to identify valuable content

### Project-Specific Databases

Each project maintains its own kuzu-memory database:
- Databases are stored in the project's working directory
- Memories are isolated between different projects
- Enables project-specific context and knowledge retention

## Available MCP Tools

The PM agent has access to these kuzu-memory tools via the MCP gateway:

### Store Memory
```json
{
  "tool": "kuzu_memory",
  "parameters": {
    "action": "store",
    "content": "Important insight or information to remember",
    "tags": ["technical", "architecture", "debugging"]
  }
}
```

### Recall Memories
```json
{
  "tool": "kuzu_memory",
  "parameters": {
    "action": "recall",
    "query": "search query for relevant memories",
    "limit": 5,
    "tags": ["optional", "tag", "filter"]
  }
}
```

### Search Memories
```json
{
  "tool": "kuzu_memory",
  "parameters": {
    "action": "search",
    "query": "search term",
    "limit": 10
  }
}
```

### Get Context
```json
{
  "tool": "kuzu_memory",
  "parameters": {
    "action": "context",
    "query": "topic for context enrichment",
    "depth": 2
  }
}
```

## Usage Examples

### Automatic Prompt Enrichment

When you ask Claude MPM about something you've discussed before:

**Your prompt:**
```
How should I implement authentication in this project?
```

**Enriched prompt (automatically added):**
```
## RELEVANT MEMORIES FROM KUZU KNOWLEDGE GRAPH

1. Previously decided to use JWT tokens with refresh token rotation [Tags: security, authentication] (Relevance: 0.89)
2. Discussed OAuth2 integration with Google and GitHub providers [Tags: oauth, external-auth] (Relevance: 0.76)
3. Implemented rate limiting for login endpoints to prevent brute force [Tags: security, rate-limiting] (Relevance: 0.65)

## USER REQUEST

How should I implement authentication in this project?

Note: Use the memories above to provide more informed and contextual responses.
```

### Manual Memory Storage

The PM agent can explicitly store important information:

```bash
# The PM agent might use this internally
{
  "tool": "kuzu_memory",
  "parameters": {
    "action": "store",
    "content": "User prefers TypeScript over JavaScript for this project. Uses React with Next.js framework.",
    "tags": ["preferences", "technology-stack", "frontend"]
  }
}
```

### Context Retrieval

When working on complex features, the PM agent can get enriched context:

```bash
{
  "tool": "kuzu_memory",
  "parameters": {
    "action": "context",
    "query": "database schema design decisions",
    "depth": 3
  }
}
```

## Memory Extraction Patterns

The system automatically identifies and stores important information using these patterns:

1. **Explicit Memory Markers**:
   - `# Remember: Important decision about X`
   - `# Memorize: Key insight about Y`
   - `# Store: Configuration details`

2. **Important Information**:
   - Lines starting with "Important:", "Note:", "Key point:"
   - Information marked as "Learned:", "Discovered:", "Found that:"

3. **Automatic Tagging**:
   - Technical content → `technical` tag
   - Bug fixes → `debugging` tag
   - Architecture discussions → `architecture` tag
   - Performance topics → `performance` tag
   - Claude MPM specific → `claude-mpm` tag

## Configuration

### Memory Hook Configuration

The kuzu-memory hook is automatically enabled when kuzu-memory is installed. Configuration happens through:

1. **Automatic Detection**: Checks for pipx installation first, then system PATH
2. **Project Isolation**: Each project gets its own memory database
3. **Graceful Handling**: Continues without memory features if unavailable

### Installation Locations

The hook checks these locations in order:
1. `~/.local/pipx/venvs/kuzu-memory/bin/kuzu-memory` (pipx installation)
2. System PATH via `which kuzu-memory`

## Benefits

### Enhanced Productivity
- **Context Continuity**: Maintains context across sessions and conversations
- **Intelligent Responses**: Agents provide more informed answers based on project history
- **Knowledge Building**: Accumulates project knowledge over time

### Better Decision Making
- **Historical Context**: Access to previous decisions and their rationale
- **Pattern Recognition**: Identifies recurring themes and approaches
- **Consistency**: Maintains consistent approaches across the project

### Improved Collaboration
- **Shared Memory**: Project teams benefit from accumulated knowledge
- **Documentation**: Automatic capture of important decisions and insights
- **Knowledge Transfer**: New team members can access project memory

## Troubleshooting

### Memory Hook Not Working

1. **Check Installation**:
   ```bash
   # Verify kuzu-memory is installed
   kuzu-memory --version

   # Install manually if needed
   pipx install kuzu-memory
   ```

2. **Check Logs**: Look for kuzu-memory messages in Claude MPM logs
3. **Manual Installation**: Install pipx first if not available

### Memory Database Issues

1. **Permission Problems**: Ensure write access to project directory
2. **Database Corruption**: Delete `.kuzu_memory/` directory to reset
3. **Performance**: Large memory databases may slow retrieval

### Hook Priority Conflicts

The kuzu-memory hook runs at priority 10 (early execution). If you have custom hooks that conflict:
- Adjust custom hook priorities accordingly
- Ensure memory enrichment happens before other processing

## Command Line Interface

While primarily automatic, you can interact with kuzu-memory directly:

```bash
# Store a memory manually
kuzu-memory remember "Important decision about using PostgreSQL for this project"

# Recall memories
kuzu-memory recall "database decisions" --format json

# Get enriched context
kuzu-memory enhance "authentication implementation" --max-memories 5
```

## Security Considerations

- **Local Storage**: All memories are stored locally in project directories
- **No External Transmission**: Memories never leave your local system
- **Project Isolation**: Each project's memories are completely separate
- **Access Control**: Standard file system permissions apply

## Future Enhancements

Planned improvements for kuzu-memory integration:

- **Memory Sharing**: Optional sharing of memories between related projects
- **Advanced Tagging**: More sophisticated automatic tag inference
- **Memory Analytics**: Insights into knowledge accumulation patterns
- **Export/Import**: Tools for backing up and restoring memory databases
- **Memory Pruning**: Automatic cleanup of outdated or irrelevant memories

## See Also

- [MCP Services Documentation](../../developer/MCP_SERVICES.md) - Technical details about MCP integration
- [Hook System](../../developer/HOOKS.md) - Understanding Claude MPM's hook architecture
- [Memory System](memory-system.md) - Agent memory system documentation
- [Kuzu-Memory GitHub](https://github.com/kuzu-memory/kuzu-memory) - Upstream project documentation