# Commander Memory System

Semantic search, storage, and context compression for Claude Code instance conversations.

## Overview

The memory system enables:
- **Conversation Storage**: Persist all Claude Code instance conversations
- **Semantic Search**: Query conversations using natural language
- **Context Compression**: Summarize long conversations for session resumption
- **Entity Extraction**: Extract files, functions, errors from conversations

## Architecture

```
memory/
├── store.py          # ConversationStore - CRUD operations
├── embeddings.py     # EmbeddingService - Generate vectors
├── search.py         # SemanticSearch - Query conversations
├── compression.py    # ContextCompressor - Summarize conversations
├── entities.py       # EntityExtractor - Extract structured data
└── integration.py    # MemoryIntegration - High-level API
```

## Quick Start

### Basic Usage

```python
from claude_mpm.commander.memory import MemoryIntegration

# Initialize (uses local embeddings by default)
memory = MemoryIntegration.create()

# Capture conversation from Project
conversation = await memory.capture_project_conversation(project)

# Search conversations
results = await memory.search_conversations(
    "how did we fix the login bug?",
    project_id="proj-xyz",
    limit=5
)

# Load context for session resumption
context = await memory.load_context_for_session("proj-xyz", max_tokens=4000)
```

### Integration with RuntimeMonitor

Automatically capture conversations when Claude Code output is detected:

```python
from claude_mpm.commander.memory import MemoryIntegration
from claude_mpm.commander.runtime import RuntimeMonitor

# Initialize memory
memory = MemoryIntegration.create()

# In your monitoring loop
async def on_conversation_complete(project: Project, session_id: str):
    """Called when Claude Code session completes."""
    conversation = await memory.capture_project_conversation(
        project,
        instance_name="claude-code-1",
        session_id=session_id
    )
    print(f"Captured conversation {conversation.id} with {len(conversation.messages)} messages")
```

### Integration with Chat CLI

Enable chat interface to query past conversations:

```python
# In chat/cli.py
async def handle_search_command(query: str, project_id: str):
    """Search past conversations."""
    results = await memory.search_conversations(query, project_id, limit=5)

    for i, result in enumerate(results, 1):
        print(f"\n{i}. Score: {result.score:.2f}")
        print(f"   Conversation: {result.conversation.id}")
        print(f"   Updated: {result.conversation.updated_at}")
        print(f"   Snippet: {result.snippet}")
```

### Session Resumption

Load compressed context when resuming a paused session:

```python
async def resume_session(project_id: str):
    """Resume session with historical context."""
    # Load compressed context from past conversations
    context = await memory.load_context_for_session(
        project_id,
        max_tokens=4000,
        limit_conversations=10
    )

    # Inject context into session
    print(f"Loaded {len(context)} chars of context")
    # Pass to Claude Code as initial system message or context
```

## Components

### ConversationStore

Persists conversations to SQLite with vector support.

```python
from claude_mpm.commander.memory import ConversationStore, Conversation

store = ConversationStore()

# Save conversation
await store.save(conversation)

# Load by ID
conv = await store.load("conv-abc123")

# List by project
conversations = await store.list_by_project("proj-xyz", limit=10)

# Text search (fallback when vectors unavailable)
results = await store.search_by_text("login bug", project_id="proj-xyz")

# Delete
await store.delete("conv-abc123")
```

### EmbeddingService

Generate vector embeddings for semantic search.

**Local (Free, Default)**:
```python
from claude_mpm.commander.memory import EmbeddingService

# Uses sentence-transformers (local, no API key needed)
embeddings = EmbeddingService(provider="sentence-transformers")
vector = await embeddings.embed("Fix the login bug")
# Returns 384-dim vector
```

**OpenAI (Best Quality)**:
```python
# Requires OPENAI_API_KEY environment variable
embeddings = EmbeddingService(provider="openai", model="text-embedding-3-small")
vector = await embeddings.embed("Fix the login bug")
# Returns 1536-dim vector
```

**Batch Embeddings**:
```python
vectors = await embeddings.embed_batch([
    "Fix the login bug",
    "Update the README",
    "Add tests for UserService"
])
```

### SemanticSearch

Query conversations semantically with filters.

```python
from claude_mpm.commander.memory import SemanticSearch
from datetime import datetime, timedelta

search = SemanticSearch(store, embeddings)

# Basic search
results = await search.search("login bug fix", project_id="proj-xyz", limit=5)

# With date range
last_week = datetime.now() - timedelta(days=7)
results = await search.search(
    "authentication changes",
    project_id="proj-xyz",
    date_range=(last_week, datetime.now()),
    limit=10
)

# Find similar conversations
similar = await search.find_similar("conv-abc123", limit=5)

# Search by entity
from claude_mpm.commander.memory import EntityType
results = await search.search_by_entities(
    EntityType.FILE,
    "src/auth.py",
    project_id="proj-xyz"
)
```

### ContextCompressor

Summarize conversations for efficient context loading.

```python
from claude_mpm.commander.memory import ContextCompressor
from claude_mpm.commander.llm import OpenRouterClient

client = OpenRouterClient()
compressor = ContextCompressor(client)

# Summarize single conversation
summary = await compressor.summarize(messages)

# Compress multiple conversations into context
context = await compressor.compress_for_context(
    conversations,
    max_tokens=4000,
    prioritize_recent=True
)

# Auto-summarize if needed
summary = await compressor.auto_summarize_conversation(conversation)
if summary:
    conversation.summary = summary
    await store.save(conversation)
```

### EntityExtractor

Extract structured entities from conversation text.

```python
from claude_mpm.commander.memory import EntityExtractor, EntityType

extractor = EntityExtractor()

# Extract all entities
entities = extractor.extract("Fix the login bug in src/auth.py using UserService.authenticate()")

# Filter by type
files = extractor.filter_by_type(entities, EntityType.FILE)
# [Entity(type=FILE, value="src/auth.py")]

functions = extractor.filter_by_type(entities, EntityType.FUNCTION)
# [Entity(type=FUNCTION, value="authenticate")]

# Get unique values
file_paths = extractor.get_unique_values(entities, EntityType.FILE)
# ["src/auth.py"]
```

Supported entity types:
- **FILE**: File paths (e.g., "src/auth.py")
- **FUNCTION**: Function names (e.g., "login()")
- **CLASS**: Class names (e.g., "UserService")
- **ERROR**: Error types (e.g., "ValueError")
- **COMMAND**: Shell commands (e.g., "pytest tests/")
- **URL**: Web URLs (e.g., "https://example.com")
- **PACKAGE**: Package names (e.g., "requests")

## Configuration

### Database Location

Default: `~/.claude-mpm/commander/conversations.db`

```python
from pathlib import Path

store = ConversationStore(db_path=Path("/custom/path/conversations.db"))
```

### Embedding Provider

**Local (Default - No API Key)**:
```python
embeddings = EmbeddingService(provider="sentence-transformers")
# Requires: pip install sentence-transformers
```

**OpenAI (Best Quality)**:
```python
import os
os.environ["OPENAI_API_KEY"] = "sk-..."  # pragma: allowlist secret

embeddings = EmbeddingService(provider="openai")
# Requires: pip install openai
```

### Summarization Model

Uses OpenRouterClient (defaults to `mistral/mistral-small`):

```python
client = OpenRouterClient(model="mistral/mistral-small")
compressor = ContextCompressor(client)
```

### Vector Search

Requires `sqlite-vec` extension:

```bash
pip install sqlite-vec
```

Falls back to text search if unavailable.

## Installation

### Required

```bash
# Core dependencies (already in pyproject.toml)
pip install aiofiles sqlite3
```

### Optional

```bash
# For local embeddings (recommended)
pip install sentence-transformers

# For vector search (recommended)
pip install sqlite-vec

# For OpenAI embeddings (optional)
pip install openai
```

## Performance

### Storage

- **SQLite**: Local, lightweight, no external dependencies
- **Embeddings**: 384 dims (sentence-transformers) or 1536 dims (OpenAI)
- **Disk Usage**: ~1KB per message, ~100KB per conversation (with embeddings)

### Search

- **Vector Search**: O(n) scan (can be optimized with KNN in future)
- **Text Search**: SQLite LIKE query (fast for small datasets)
- **Recommendation**: Use vector search for semantic queries, text search for exact matches

### Embeddings

**Local (sentence-transformers)**:
- Speed: ~100 texts/sec on CPU
- Cost: Free
- Quality: Good for general queries

**OpenAI (text-embedding-3-small)**:
- Speed: ~1000 texts/sec (API limited)
- Cost: $0.02 per 1M tokens
- Quality: Excellent

## Examples

### Example 1: Capture and Search

```python
from claude_mpm.commander.memory import MemoryIntegration

# Initialize
memory = MemoryIntegration.create()

# Capture conversation
conversation = await memory.capture_project_conversation(project)
print(f"Captured: {conversation.id}")
print(f"Messages: {len(conversation.messages)}")
print(f"Summary: {conversation.summary}")

# Search
results = await memory.search_conversations("login bug", project_id=project.id)
for result in results:
    print(f"Score: {result.score:.2f}")
    print(f"Snippet: {result.snippet}")
```

### Example 2: Session Resumption

```python
# Load context from past conversations
context = await memory.load_context_for_session("proj-xyz", max_tokens=4000)

# Inject into new session
system_message = f"""You are resuming a session for this project.

Here is the context from past conversations:

{context}

Use this context to understand what has been done previously."""
```

### Example 3: Entity-Based Search

```python
from claude_mpm.commander.memory import EntityType

# Find all conversations that mention a specific file
results = await memory.search.search_by_entities(
    EntityType.FILE,
    "src/auth.py",
    project_id="proj-xyz"
)

for result in results:
    print(f"Conversation: {result.conversation.id}")
    print(f"Updated: {result.conversation.updated_at}")
    print(f"Entities: {result.matched_entities}")
```

## Roadmap

### Phase 1: Foundation (Current)
- ✅ SQLite storage with vector support
- ✅ Local embeddings (sentence-transformers)
- ✅ Semantic search
- ✅ Context compression
- ✅ Entity extraction

### Phase 2: Optimization
- [ ] KNN vector search in SQL
- [ ] FTS5 full-text search
- [ ] Incremental summarization
- [ ] Conversation threading (link related conversations)

### Phase 3: Advanced Features
- [ ] Multi-modal support (code snippets, images)
- [ ] Conversation clustering (group similar conversations)
- [ ] Temporal analysis (track evolution of codebase)
- [ ] Export/import conversations (backup, migration)

## Troubleshooting

### "sqlite-vec extension not found"

Install the extension:
```bash
pip install sqlite-vec
```

Or disable vector search:
```python
store = ConversationStore(enable_vector=False)
```

### "sentence-transformers not installed"

Install for local embeddings:
```bash
pip install sentence-transformers
```

Or use OpenAI:
```python
embeddings = EmbeddingService(provider="openai")
```

### Slow embedding generation

**Local**: Run on GPU if available:
```python
# sentence-transformers will auto-detect CUDA
embeddings = EmbeddingService(provider="sentence-transformers")
```

**OpenAI**: Use batch embeddings:
```python
vectors = await embeddings.embed_batch(texts)  # More efficient
```

## Testing

```bash
# Run memory system tests
pytest tests/commander/memory/

# Run with coverage
pytest tests/commander/memory/ --cov=src/claude_mpm/commander/memory
```

## License

Elastic-2.0 (same as claude-mpm)
