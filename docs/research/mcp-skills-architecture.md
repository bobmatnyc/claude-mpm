# MCP-Skills Architecture Design

**Project**: mcp-skills - Standalone Python PyPI app for vector + KG RAG skills service via MCP
**Author**: Research Agent
**Date**: 2025-11-21
**Status**: Architecture Design Document

---

## Executive Summary

**mcp-skills** is a standalone Python application that provides dynamic, context-aware skills to code assistants via the Model Context Protocol (MCP). Unlike Claude Code's static skills (loaded at startup), mcp-skills uses hybrid RAG (vector + knowledge graph) to enable runtime skill discovery, intelligent recommendations, and dynamic loading based on project context.

**Key Differentiators**:
- **Dynamic**: Skills loaded on-demand, not at startup
- **Intelligent**: Toolchain detection auto-recommends relevant skills
- **Hybrid RAG**: Vector similarity + KG relationships for better discovery
- **Zero Config**: `mcp-skills setup` handles everything automatically
- **Multi-Source**: Pulls skills from multiple git repositories
- **PyPI Installable**: `pip install mcp-skills` in any codebase

---

## System Architecture

```
╔══════════════════════════════════════════════════════════════════════════════╗
║                           MCP-SKILLS ARCHITECTURE                             ║
╚══════════════════════════════════════════════════════════════════════════════╝

┌─────────────────────────────────────────────────────────────────────────────┐
│                         CODE ASSISTANT (Claude Code)                         │
│                              ↓ MCP Protocol ↓                                │
└─────────────────────────────────────────────────────────────────────────────┘
                                      ↓
╔═════════════════════════════════════════════════════════════════════════════╗
║                          MCP-SKILLS SERVER (Python)                          ║
╠═════════════════════════════════════════════════════════════════════════════╣
║  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   ║
║  │   MCP Server │  │    Skill     │  │   Indexing   │  │  Toolchain   │   ║
║  │   Interface  │──│   Manager    │──│    Engine    │──│   Detector   │   ║
║  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘   ║
║         ↓                 ↓                  ↓                  ↓            ║
║  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   ║
║  │   Protocol   │  │   Dynamic    │  │   Hybrid     │  │   Pattern    │   ║
║  │   Handler    │  │   Loader     │  │  RAG Store   │  │   Matcher    │   ║
║  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘   ║
╚═════════════════════════════════════════════════════════════════════════════╝
           ↓                 ↓                  ↓
╔══════════════════╗  ╔═══════════════╗  ╔════════════════════════════╗
║   Vector Store   ║  ║  Graph Store  ║  ║   Skills Repository        ║
║   (Chroma/Qdrant)║  ║  (NetworkX/   ║  ║   (~/.mcp-skills/repos/)   ║
║                  ║  ║   Neo4j Lite) ║  ║   - anthropics/skills      ║
║   Embeddings:    ║  ║               ║  ║   - obra/superpowers       ║
║   - Skill desc   ║  ║   Relations:  ║  ║   - custom repos           ║
║   - Instructions ║  ║   - Depends   ║  ║                            ║
║   - Examples     ║  ║   - Relates   ║  ║   Metadata DB (SQLite)     ║
║   - Patterns     ║  ║   - Category  ║  ║   - Skill index            ║
╚══════════════════╝  ╚═══════════════╝  ╚════════════════════════════╝

DATA FLOW:
──────────
1. Setup:    mcp-skills setup → Detect toolchain → Pull skills → Index
2. Query:    Assistant request → MCP → Skill search (vector+KG) → Load skill
3. Execution: Skill instructions → Assistant → Execute → Return result
```

---

## Component Breakdown

### 1. MCP Server Interface

**Purpose**: Expose skills to code assistants via Model Context Protocol

**Responsibilities**:
- Implement MCP server specification (using Python SDK)
- Handle tool discovery requests
- Serve skill content on-demand
- Manage client connections
- Protocol versioning and compatibility

**Key Classes**:
```python
class MCPSkillsServer:
    """Main MCP server implementation"""

    async def list_tools(self) -> List[Tool]:
        """Return available skills as MCP tools"""

    async def call_tool(self, name: str, arguments: dict) -> Any:
        """Execute skill and return result"""

    async def list_resources(self) -> List[Resource]:
        """Provide skill documentation as resources"""
```

**MCP Integration**:
- Uses `@modelcontextprotocol/python-sdk`
- Implements stdio transport for local communication
- Supports both SSE and stdio transports
- Handles graceful shutdown and error recovery

---

### 2. Skill Manager

**Purpose**: Orchestrate skill lifecycle - discovery, loading, execution

**Responsibilities**:
- Load skills from filesystem
- Parse SKILL.md metadata (YAML frontmatter)
- Validate skill structure and dependencies
- Cache loaded skills in memory
- Track skill usage statistics
- Handle skill updates and versioning

**Key Classes**:
```python
class SkillManager:
    """Manages skill lifecycle"""

    def discover_skills(self, repos_dir: Path) -> List[Skill]:
        """Scan repositories for skills"""

    def load_skill(self, skill_id: str) -> Skill:
        """Load skill from disk with caching"""

    def get_skill_metadata(self, skill_id: str) -> SkillMetadata:
        """Extract metadata from SKILL.md"""

    def validate_skill(self, skill: Skill) -> ValidationResult:
        """Check skill structure and dependencies"""

class Skill:
    """Skill data model"""
    id: str
    name: str
    description: str
    instructions: str
    category: str
    tags: List[str]
    dependencies: List[str]
    examples: List[str]
```

**Skill Format** (SKILL.md):
```markdown
---
name: skill-name
description: What this skill does
category: testing|debugging|refactoring|...
tags: [python, pytest, tdd]
dependencies: []
---

# Skill Instructions

Detailed instructions for Claude...
```

---

### 3. Indexing Engine

**Purpose**: Build and maintain vector + KG indices for skill discovery

**Responsibilities**:
- Generate embeddings for skill content
- Build knowledge graph of skill relationships
- Update indices incrementally
- Optimize for fast retrieval
- Handle index versioning and migrations

**Key Classes**:
```python
class IndexingEngine:
    """Hybrid RAG indexing"""

    def index_skill(self, skill: Skill) -> None:
        """Add skill to vector + KG stores"""

    def build_embeddings(self, skill: Skill) -> np.ndarray:
        """Generate embeddings from skill content"""

    def extract_relationships(self, skill: Skill) -> List[Relation]:
        """Identify skill dependencies and relationships"""

    def reindex_all(self, force: bool = False) -> IndexStats:
        """Rebuild indices from scratch"""

class HybridRAG:
    """Combines vector and graph search"""

    def search(
        self,
        query: str,
        toolchain: Optional[str] = None,
        top_k: int = 10
    ) -> List[ScoredSkill]:
        """Search skills using vector similarity + KG"""

    def get_related_skills(self, skill_id: str) -> List[Skill]:
        """Find related skills via knowledge graph"""
```

**Indexing Strategy**:

**Vector Store** (Chroma/Qdrant):
- Embed: name + description + instructions + examples
- Model: sentence-transformers/all-MiniLM-L6-v2 (lightweight)
- Metadata: category, tags, toolchain, repo_url
- Collection: skills_v1

**Knowledge Graph** (NetworkX or Neo4j Lite):
- Nodes: Skills, Categories, Toolchains, Tags
- Edges:
  - DEPENDS_ON (skill dependencies)
  - BELONGS_TO (category membership)
  - RELATED_TO (semantic similarity)
  - SUITABLE_FOR (toolchain compatibility)
  - TAGGED_WITH (tag relationships)

**Example Graph**:
```
(pytest-skill)-[:DEPENDS_ON]->(test-driven-development)
(pytest-skill)-[:SUITABLE_FOR]->(Python)
(pytest-skill)-[:BELONGS_TO]->(Testing)
(pytest-skill)-[:TAGGED_WITH]->(tdd)
```

---

### 4. Toolchain Detector

**Purpose**: Automatically identify project technology stack

**Responsibilities**:
- Scan project directory for toolchain markers
- Detect primary and secondary languages
- Identify frameworks and build tools
- Recommend relevant skills based on detection
- Cache detection results per project

**Key Classes**:
```python
class ToolchainDetector:
    """Detect project technology stack"""

    def detect(self, project_dir: Path) -> ToolchainInfo:
        """Analyze project and return toolchain info"""

    def detect_languages(self, project_dir: Path) -> List[str]:
        """Identify programming languages"""

    def detect_frameworks(self, project_dir: Path) -> List[str]:
        """Identify frameworks (Flask, React, etc)"""

    def recommend_skills(self, toolchain: ToolchainInfo) -> List[Skill]:
        """Suggest skills based on toolchain"""

@dataclass
class ToolchainInfo:
    """Detected toolchain information"""
    primary_language: str
    secondary_languages: List[str]
    frameworks: List[str]
    build_tools: List[str]
    package_managers: List[str]
    test_frameworks: List[str]
    confidence: float
```

**Detection Patterns**:
```python
TOOLCHAIN_PATTERNS = {
    "Python": {
        "files": ["pyproject.toml", "setup.py", "requirements.txt", "Pipfile"],
        "dirs": ["venv", ".venv", "__pycache__"],
        "configs": ["pytest.ini", "tox.ini", ".flake8", "mypy.ini"],
        "priority": 1.0
    },
    "TypeScript/JavaScript": {
        "files": ["package.json", "tsconfig.json", "yarn.lock"],
        "dirs": ["node_modules", "dist"],
        "configs": [".eslintrc", ".prettierrc", "jest.config.js"],
        "priority": 1.0
    },
    "Rust": {
        "files": ["Cargo.toml", "Cargo.lock"],
        "dirs": ["target"],
        "priority": 0.9
    },
    "Go": {
        "files": ["go.mod", "go.sum"],
        "dirs": ["vendor"],
        "priority": 0.9
    }
}
```

---

### 5. Dynamic Loader

**Purpose**: Load skills at runtime based on context

**Responsibilities**:
- Monitor skill usage patterns
- Preload frequently used skills
- Lazy load on-demand skills
- Unload unused skills to save memory
- Handle skill hot-reloading during development

**Key Classes**:
```python
class DynamicLoader:
    """Runtime skill loading"""

    def load_on_demand(self, skill_id: str) -> Skill:
        """Load skill when requested"""

    def preload_common(self, toolchain: str) -> None:
        """Preload frequently used skills"""

    def unload_unused(self, threshold: int = 3600) -> None:
        """Unload skills not used in last hour"""

    def watch_for_changes(self, repo_dir: Path) -> None:
        """Auto-reload skills on file changes"""
```

---

### 6. Skills Repository Manager

**Purpose**: Manage git-based skills repositories

**Responsibilities**:
- Clone skills repositories from git URLs
- Update repositories (git pull)
- Handle multiple repository sources
- Manage repository priorities
- Track repository metadata and licenses

**Key Classes**:
```python
class RepositoryManager:
    """Manage skills git repositories"""

    def add_repository(self, url: str, priority: int = 0) -> None:
        """Clone new repository"""

    def update_repository(self, repo_id: str) -> UpdateResult:
        """Pull latest changes"""

    def list_repositories(self) -> List[Repository]:
        """List all configured repositories"""

    def remove_repository(self, repo_id: str) -> None:
        """Remove repository and its skills"""

@dataclass
class Repository:
    """Repository metadata"""
    id: str
    url: str
    local_path: Path
    priority: int
    last_updated: datetime
    skill_count: int
    license: str
```

**Default Repositories**:
```python
DEFAULT_REPOS = [
    {
        "url": "https://github.com/anthropics/skills.git",
        "priority": 100,  # Highest priority
        "license": "Apache-2.0"
    },
    {
        "url": "https://github.com/obra/superpowers.git",
        "priority": 90,
        "license": "MIT"
    },
    {
        "url": "https://github.com/bobmatnyc/claude-mpm-skills.git",
        "priority": 80,
        "license": "MIT"
    }
]
```

---

## Technology Stack Recommendations

### Core Framework
- **Python 3.11+**: Modern async/await, type hints, better performance
- **MCP Python SDK**: `@modelcontextprotocol/python-sdk`
- **FastAPI**: (optional) For HTTP-based MCP transport
- **Pydantic**: Data validation and settings management
- **SQLAlchemy**: Database ORM for metadata storage

### Vector Store Options

**Option 1: ChromaDB** (Recommended for MVP)
- **Pros**: Pure Python, zero config, embedded mode, fast
- **Cons**: Limited scalability (millions of vectors)
- **Use Case**: Solo developers, small-medium projects
```python
import chromadb
client = chromadb.Client()
collection = client.create_collection(name="skills")
```

**Option 2: Qdrant** (Recommended for Production)
- **Pros**: High performance, production-ready, good Python SDK
- **Cons**: Requires separate service (can run in Docker)
- **Use Case**: Teams, large skill collections, production deployment
```python
from qdrant_client import QdrantClient
client = QdrantClient(host="localhost", port=6333)
```

**Option 3: FAISS** (Lightweight Alternative)
- **Pros**: Facebook-backed, very fast, pure Python bindings
- **Cons**: No built-in persistence, manual index management
- **Use Case**: Performance-critical, custom deployments

### Embeddings Model

**Recommended**: `sentence-transformers/all-MiniLM-L6-v2`
- **Size**: 23MB
- **Speed**: Fast (8000 sentences/sec on CPU)
- **Quality**: Good for semantic search
- **License**: Apache-2.0

```python
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('all-MiniLM-L6-v2')
embeddings = model.encode(["skill description here"])
```

**Alternative**: `OpenAI text-embedding-3-small` (if API key available)
- **Quality**: Better semantic understanding
- **Cost**: ~$0.02 per 1M tokens
- **Use Case**: When quality > cost

### Knowledge Graph Options

**Option 1: NetworkX** (Recommended for MVP)
- **Pros**: Pure Python, simple API, built-in algorithms
- **Cons**: In-memory only (need custom persistence)
- **Use Case**: <10K skills, development, testing
```python
import networkx as nx
G = nx.DiGraph()
G.add_edge("pytest-skill", "tdd-skill", relation="depends_on")
```

**Option 2: Neo4j Lite / Memgraph** (Recommended for Production)
- **Pros**: Native graph DB, Cypher query language, scalable
- **Cons**: Requires separate service
- **Use Case**: >10K skills, complex queries, production
```python
from neo4j import GraphDatabase
driver = GraphDatabase.driver("bolt://localhost:7687")
```

**Option 3: SQLite with Graph Extension** (Balanced Option)
- **Pros**: Single file, no separate service, good performance
- **Cons**: Limited graph query capabilities
- **Use Case**: Medium projects, hybrid SQL+graph queries

### Metadata Storage

**SQLite** (Recommended)
- Skills index (id, name, description, repo, path)
- Repository metadata (url, last_updated, skill_count)
- Usage statistics (skill_id, access_count, last_used)
- Toolchain cache (project_path, detected_toolchain, timestamp)

```sql
CREATE TABLE skills (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    category TEXT,
    tags TEXT,  -- JSON array
    repo_id TEXT,
    file_path TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE TABLE repositories (
    id TEXT PRIMARY KEY,
    url TEXT UNIQUE,
    local_path TEXT,
    priority INTEGER,
    last_updated TIMESTAMP,
    skill_count INTEGER
);
```

### Additional Libraries

```toml
[project.dependencies]
# Core
anthropic-mcp-sdk = ">=0.1.0"
pydantic = ">=2.0"
pydantic-settings = ">=2.0"
click = ">=8.0"  # CLI

# Vector/Embeddings
chromadb = ">=0.4.0"
sentence-transformers = ">=2.2.0"

# Graph
networkx = ">=3.0"

# Storage
sqlalchemy = ">=2.0"
alembic = ">=1.12.0"  # Migrations

# Git operations
gitpython = ">=3.1.0"

# Utilities
pyyaml = ">=6.0"
python-frontmatter = ">=1.0.0"  # Parse SKILL.md
watchdog = ">=3.0.0"  # File watching
rich = ">=13.0.0"  # CLI formatting
```

---

## Setup Workflow: `mcp-skills setup`

**Goal**: Zero-config setup that handles everything automatically

### Phase 1: Environment Detection
```bash
mcp-skills setup
```

**Actions**:
1. Check if `~/.mcp-skills/` exists, create if not
2. Detect current project directory
3. Run toolchain detection
4. Display detected toolchain and ask for confirmation

**Output**:
```
🔍 Detecting project toolchain...
✓ Detected: Python 3.11 (Flask, pytest, SQLAlchemy)
✓ Detected: TypeScript (React, Next.js)

📦 Recommended skills repositories:
  1. anthropics/skills (Official Anthropic)
  2. obra/superpowers (Best practices)
  3. bobmatnyc/claude-mpm-skills (MPM integration)

Continue with setup? [Y/n]
```

### Phase 2: Repository Cloning
**Actions**:
1. Clone default repositories to `~/.mcp-skills/repos/`
2. Show progress for each repository
3. Validate repository structure

**Output**:
```
📥 Cloning skills repositories...
  ✓ anthropics/skills (16 skills)
  ✓ obra/superpowers (24 skills)
  ✓ bobmatnyc/claude-mpm-skills (35 skills)

Total: 75 skills available
```

### Phase 3: Indexing
**Actions**:
1. Scan all SKILL.md files
2. Generate embeddings (show progress)
3. Build knowledge graph
4. Create SQLite metadata DB
5. Store toolchain detection results

**Output**:
```
🔨 Building indices...
  ✓ Scanning skills (75 found)
  ✓ Generating embeddings (all-MiniLM-L6-v2)
  ✓ Building knowledge graph (250 relationships)
  ✓ Creating metadata database

Index size: 12.3 MB
```

### Phase 4: MCP Configuration
**Actions**:
1. Detect if Claude Code is installed
2. Auto-configure `~/.config/claude/mcp_settings.json`
3. Generate server start command
4. Test MCP connection

**Output**:
```
⚙️  Configuring MCP integration...
  ✓ Detected Claude Code
  ✓ Updated MCP configuration
  ✓ Server configured at: ~/.mcp-skills/server

🚀 Setup complete! Start the server:
  mcp-skills serve

Or test the integration:
  mcp-skills test-connection
```

**Auto-Generated MCP Config**:
```json
{
  "mcpServers": {
    "mcp-skills": {
      "command": "mcp-skills",
      "args": ["serve"],
      "env": {
        "MCP_SKILLS_DIR": "${HOME}/.mcp-skills",
        "MCP_SKILLS_LOG_LEVEL": "info"
      }
    }
  }
}
```

### Phase 5: Validation
**Actions**:
1. Verify all components initialized
2. Test vector search
3. Test graph queries
4. Test skill loading

**Output**:
```
✅ All systems operational
  ✓ Vector search ready (75 skills indexed)
  ✓ Knowledge graph ready (250 relationships)
  ✓ MCP server configured

Try it out:
  Ask Claude: "What testing skills are available?"
```

---

## Integration with Code Assistants

### MCP Server Startup

```bash
# Start server (stdio mode for Claude Code)
mcp-skills serve

# Start with HTTP transport (for web clients)
mcp-skills serve --transport http --port 8000

# Start in development mode (auto-reload)
mcp-skills serve --dev
```

### Available MCP Tools

The server exposes these tools to code assistants:

**1. search_skills**
```python
{
  "name": "search_skills",
  "description": "Search for skills using natural language query",
  "input_schema": {
    "query": "string",  # e.g., "testing skills for Python"
    "toolchain": "string?",  # Filter by detected toolchain
    "category": "string?",  # Filter by category
    "limit": "integer?"  # Max results (default: 10)
  }
}
```

**2. get_skill**
```python
{
  "name": "get_skill",
  "description": "Load full skill instructions by ID",
  "input_schema": {
    "skill_id": "string"  # e.g., "pytest-skill"
  }
}
```

**3. recommend_skills**
```python
{
  "name": "recommend_skills",
  "description": "Get skill recommendations for current project",
  "input_schema": {
    "context": "string?"  # Additional context about task
  }
}
```

**4. list_categories**
```python
{
  "name": "list_categories",
  "description": "List all skill categories",
  "input_schema": {}
}
```

**5. update_repositories**
```python
{
  "name": "update_repositories",
  "description": "Pull latest skills from git repositories",
  "input_schema": {
    "repo_id": "string?"  # Update specific repo or all if omitted
  }
}
```

### Usage Examples

**Example 1: Assistant searches for testing skills**
```
User: "I need to add tests to my Flask API"

Claude: [calls search_skills with query="testing Flask API"]
Response: [
  {
    "id": "pytest-skill",
    "name": "pytest",
    "description": "Professional pytest testing for Python",
    "relevance": 0.92
  },
  {
    "id": "test-driven-development",
    "name": "TDD Workflow",
    "description": "RED-GREEN-REFACTOR cycle",
    "relevance": 0.87
  }
]

Claude: [calls get_skill with skill_id="pytest-skill"]
Response: {full skill instructions}

Claude: "I'll help you add pytest tests. Based on the pytest-skill
       guidelines, we should..."
```

**Example 2: Automatic recommendations on project open**
```
User: Opens project in Claude Code

Claude: [MCP server detects toolchain via file watch]
        [calls recommend_skills with detected toolchain]

Response: [
  "systematic-debugging",
  "test-driven-development",
  "python-best-practices"
]

Claude: "I've detected this is a Python/Flask project. I've loaded
       skills for testing, debugging, and best practices."
```

---

## Comparison: Claude Code Skills vs MCP-Skills

| Feature | Claude Code Skills | MCP-Skills |
|---------|-------------------|------------|
| **Loading** | Static (startup only) | Dynamic (runtime) |
| **Discovery** | Manual browsing | Vector + KG search |
| **Context Aware** | No | Yes (toolchain detection) |
| **Updates** | Manual reinstall | Auto-update via git pull |
| **Storage** | `~/.claude/skills/` | `~/.mcp-skills/` |
| **Distribution** | Git clone | PyPI package |
| **Recommendations** | None | AI-powered based on context |
| **Multi-Project** | Global only | Per-project + global |
| **RAG Search** | None | Vector + KG hybrid |
| **Relationships** | None | Dependency graph |
| **API Access** | Skills API | MCP protocol |
| **Performance** | All loaded upfront | Lazy loading |
| **Memory** | High (all skills) | Low (on-demand) |

**When to use Claude Code Skills**:
- Simple setups with few skills
- No need for dynamic discovery
- Prefer official Anthropic integration

**When to use MCP-Skills**:
- Large skill collections (50+ skills)
- Multiple projects with different toolchains
- Need intelligent skill recommendations
- Want automatic skill updates
- Building custom skill pipelines

---

## Advanced Features (Future Enhancements)

### 1. Skill Analytics
```python
class SkillAnalytics:
    """Track skill usage and effectiveness"""

    def record_usage(self, skill_id: str, context: dict) -> None:
        """Log skill usage with context"""

    def get_popular_skills(self, toolchain: str) -> List[str]:
        """Most used skills for given toolchain"""

    def suggest_skill_combinations(self) -> List[List[str]]:
        """Skills commonly used together"""
```

### 2. Custom Skill Templates
```bash
# Generate new skill from template
mcp-skills create-skill --name my-custom-skill --category testing

# Validate custom skill
mcp-skills validate-skill ./my-skill/SKILL.md

# Publish to personal repo
mcp-skills publish-skill --repo https://github.com/user/my-skills.git
```

### 3. Skill Dependencies
```yaml
---
name: advanced-testing-skill
dependencies:
  - pytest-skill
  - test-driven-development
auto_load_dependencies: true
---
```

### 4. Multi-Tenant Support
```python
# Per-project skill overrides
~/.mcp-skills/
  repos/          # Global skills
  projects/
    project-a/
      config.yaml # Project-specific config
      skills/     # Project-only skills
```

### 5. Skill Execution Hooks
```python
class SkillHooks:
    """Pre/post skill execution hooks"""

    async def before_skill_load(self, skill: Skill) -> None:
        """Called before loading skill"""

    async def after_skill_execute(self, result: Any) -> None:
        """Called after skill execution"""
```

---

## Implementation Phases

### Phase 1: MVP (Weeks 1-2)
- ✅ Basic MCP server implementation
- ✅ Skill loading from local filesystem
- ✅ Simple vector search (ChromaDB)
- ✅ Toolchain detection (Python, TypeScript)
- ✅ CLI: `setup`, `serve`, `search`
- ✅ SQLite metadata storage

### Phase 2: Core Features (Weeks 3-4)
- ✅ Knowledge graph (NetworkX)
- ✅ Hybrid RAG search (vector + KG)
- ✅ Repository management (git clone/pull)
- ✅ Dynamic skill loading
- ✅ MCP auto-configuration
- ✅ Skill recommendations

### Phase 3: Polish (Weeks 5-6)
- ✅ Usage analytics
- ✅ Skill validation framework
- ✅ Performance optimization
- ✅ Comprehensive documentation
- ✅ Testing (unit + integration)
- ✅ PyPI packaging and release

### Phase 4: Advanced (Future)
- Custom skill templates
- Multi-tenant support
- Skill execution hooks
- Web UI for skill management
- Cloud synchronization
- Team collaboration features

---

## Project Structure

```
mcp-skills/
├── src/
│   └── mcp_skills/
│       ├── __init__.py
│       ├── __main__.py          # CLI entry point
│       ├── server/
│       │   ├── __init__.py
│       │   ├── mcp_server.py    # MCP server implementation
│       │   ├── protocol.py      # Protocol handlers
│       │   └── transport.py     # Stdio/HTTP transports
│       ├── core/
│       │   ├── __init__.py
│       │   ├── skill.py         # Skill data models
│       │   ├── manager.py       # SkillManager
│       │   ├── loader.py        # DynamicLoader
│       │   └── validator.py     # Skill validation
│       ├── indexing/
│       │   ├── __init__.py
│       │   ├── engine.py        # IndexingEngine
│       │   ├── vector.py        # Vector store abstraction
│       │   ├── graph.py         # Knowledge graph
│       │   └── hybrid.py        # Hybrid RAG
│       ├── detection/
│       │   ├── __init__.py
│       │   ├── detector.py      # ToolchainDetector
│       │   └── patterns.py      # Detection patterns
│       ├── repository/
│       │   ├── __init__.py
│       │   ├── manager.py       # RepositoryManager
│       │   └── defaults.py      # Default repos config
│       ├── storage/
│       │   ├── __init__.py
│       │   ├── database.py      # SQLAlchemy models
│       │   └── migrations/      # Alembic migrations
│       ├── cli/
│       │   ├── __init__.py
│       │   ├── commands.py      # Click commands
│       │   └── setup.py         # Setup workflow
│       └── config.py            # Settings (Pydantic)
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
├── docs/
│   ├── architecture.md
│   ├── api.md
│   ├── user-guide.md
│   └── contributing.md
├── examples/
│   └── custom-skills/
├── pyproject.toml
├── README.md
└── LICENSE
```

---

## Configuration

### User Configuration (`~/.mcp-skills/config.yaml`)
```yaml
# Default repositories
repositories:
  - url: https://github.com/anthropics/skills.git
    priority: 100
    auto_update: true
  - url: https://github.com/obra/superpowers.git
    priority: 90
    auto_update: true

# Vector store settings
vector_store:
  backend: chromadb  # or qdrant, faiss
  embedding_model: all-MiniLM-L6-v2
  collection_name: skills_v1

# Knowledge graph settings
knowledge_graph:
  backend: networkx  # or neo4j
  persist_path: ~/.mcp-skills/graph.pkl

# Server settings
server:
  transport: stdio  # or http
  port: 8000
  log_level: info

# Toolchain detection
toolchain:
  cache_duration: 3600  # seconds
  auto_recommend: true

# Performance
performance:
  max_loaded_skills: 50
  preload_common: true
  lazy_load_threshold: 100  # KB
```

### Project Configuration (`.mcp-skills.yaml`)
```yaml
# Project-specific overrides
project:
  name: my-awesome-project
  toolchain:
    primary: Python
    frameworks: [Flask, SQLAlchemy]

# Additional skill repositories
repositories:
  - url: https://github.com/myorg/custom-skills.git
    priority: 110  # Higher than defaults

# Disabled skills for this project
disabled_skills:
  - some-incompatible-skill

# Auto-load these skills
auto_load:
  - systematic-debugging
  - test-driven-development
```

---

## Testing Strategy

### Unit Tests
```python
# tests/unit/test_skill_manager.py
def test_load_skill_from_disk():
    manager = SkillManager()
    skill = manager.load_skill("pytest-skill")
    assert skill.name == "pytest"
    assert "pytest" in skill.tags

# tests/unit/test_toolchain_detector.py
def test_detect_python_project(tmp_path):
    (tmp_path / "pyproject.toml").write_text("")
    detector = ToolchainDetector()
    info = detector.detect(tmp_path)
    assert info.primary_language == "Python"
```

### Integration Tests
```python
# tests/integration/test_hybrid_rag.py
@pytest.mark.integration
async def test_hybrid_search():
    engine = IndexingEngine()
    await engine.index_all_skills()

    rag = HybridRAG(engine.vector_store, engine.graph_store)
    results = await rag.search("python testing", toolchain="Python")

    assert len(results) > 0
    assert results[0].skill_id == "pytest-skill"
```

### E2E Tests
```python
# tests/e2e/test_mcp_server.py
@pytest.mark.e2e
async def test_full_workflow():
    # Start MCP server
    server = MCPSkillsServer()
    await server.start()

    # Client searches for skills
    response = await server.call_tool(
        "search_skills",
        {"query": "debugging", "limit": 5}
    )

    assert len(response["skills"]) == 5

    # Load specific skill
    skill = await server.call_tool(
        "get_skill",
        {"skill_id": response["skills"][0]["id"]}
    )

    assert skill["instructions"]
```

---

## Security Considerations

### 1. Repository Trust
- Verify git repository signatures
- Whitelist trusted repositories
- Scan for malicious code patterns
- License validation

### 2. Skill Sandboxing
- Skills are instructions only (no code execution)
- Validate skill metadata schema
- Prevent path traversal in file references
- Rate limiting on skill loads

### 3. MCP Security
- Stdio transport is process-local (secure)
- HTTP transport requires authentication
- No direct filesystem access from skills
- Audit logging of skill usage

### 4. Data Privacy
- No telemetry by default
- Local-only storage (no cloud sync)
- Optional analytics (opt-in)
- No API key storage in skills

---

## Performance Optimization

### 1. Caching Strategy
```python
# Multi-level caching
L1: In-memory skill cache (LRU, max 50 skills)
L2: Embeddings cache (avoid recomputation)
L3: Toolchain detection cache (per project)
```

### 2. Lazy Loading
- Only load skill metadata initially (~100 tokens)
- Load full instructions on-demand
- Unload unused skills after threshold

### 3. Indexing Optimization
- Incremental indexing (only new/changed skills)
- Batch embedding generation
- Background index updates
- Index versioning for migrations

### 4. Query Optimization
- Vector search: Top-K retrieval with filters
- Graph queries: Bidirectional BFS
- Hybrid reranking: Vector 70% + Graph 30%

---

## Monitoring and Observability

### Metrics
```python
# Server metrics
- skill_loads_total (counter)
- skill_search_duration_seconds (histogram)
- active_skills (gauge)
- index_size_bytes (gauge)

# Usage metrics
- skills_by_category (counter)
- skills_by_toolchain (counter)
- search_queries_total (counter)
- recommendations_accepted (counter)
```

### Logging
```python
import logging

logger = logging.getLogger("mcp_skills")
logger.info("Loaded skill", extra={
    "skill_id": skill.id,
    "category": skill.category,
    "load_time_ms": 45
})
```

### Health Checks
```bash
# Server health
mcp-skills health

# Output:
# ✓ Vector store: OK (75 skills)
# ✓ Knowledge graph: OK (250 edges)
# ✓ SQLite DB: OK
# ✓ Repositories: OK (3 repos)
```

---

## Deployment Options

### 1. Local Installation (Recommended for Solo Developers)
```bash
pip install mcp-skills
mcp-skills setup
mcp-skills serve
```

### 2. Docker Container (Recommended for Teams)
```dockerfile
FROM python:3.11-slim
RUN pip install mcp-skills
EXPOSE 8000
CMD ["mcp-skills", "serve", "--transport", "http", "--port", "8000"]
```

```bash
docker run -p 8000:8000 -v ~/.mcp-skills:/root/.mcp-skills mcp-skills
```

### 3. System Service (Linux/macOS)
```ini
# /etc/systemd/system/mcp-skills.service
[Unit]
Description=MCP Skills Server
After=network.target

[Service]
Type=simple
User=username
ExecStart=/usr/local/bin/mcp-skills serve
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

---

## CLI Reference

```bash
# Setup
mcp-skills setup                    # Interactive setup wizard
mcp-skills setup --auto             # Non-interactive with defaults

# Server
mcp-skills serve                    # Start stdio server
mcp-skills serve --http             # Start HTTP server
mcp-skills serve --port 8001        # Custom port
mcp-skills serve --dev              # Development mode (auto-reload)

# Skills Management
mcp-skills search "testing"         # Search skills
mcp-skills list                     # List all skills
mcp-skills info pytest-skill        # Show skill details
mcp-skills recommend                # Get recommendations for current project

# Repositories
mcp-skills repo add <url>           # Add repository
mcp-skills repo list                # List repositories
mcp-skills repo update [repo-id]    # Update repositories
mcp-skills repo remove <repo-id>    # Remove repository

# Indexing
mcp-skills index                    # Rebuild indices
mcp-skills index --incremental      # Index only new/changed skills

# Utilities
mcp-skills health                   # Health check
mcp-skills stats                    # Usage statistics
mcp-skills validate <skill-path>    # Validate skill
mcp-skills config                   # Show configuration

# Development
mcp-skills create-skill             # Create new skill from template
mcp-skills test-connection          # Test MCP connection
```

---

## Summary

**mcp-skills** provides a production-ready, intelligent skills service that transforms how code assistants discover and use skills:

**Key Innovations**:
1. **Dynamic Loading**: Skills loaded on-demand, not at startup
2. **Hybrid RAG**: Vector similarity + knowledge graph for better discovery
3. **Toolchain Awareness**: Auto-detects project tech stack
4. **Zero Config**: `mcp-skills setup` handles everything
5. **Multi-Source**: Pulls from multiple git repositories
6. **MCP Native**: First-class MCP protocol integration

**Technical Highlights**:
- Python 3.11+ with async/await
- ChromaDB/Qdrant for vector search
- NetworkX/Neo4j for knowledge graph
- SQLite for metadata
- MCP Python SDK for protocol
- sentence-transformers for embeddings

**Use Cases**:
- Solo developers with large skill collections
- Teams needing context-aware skill recommendations
- Projects with multiple toolchains
- Custom skill pipelines and workflows
- Production deployments with scaling requirements

**Next Steps**:
1. Implement Phase 1 MVP (basic MCP server + vector search)
2. Validate with real skill repositories
3. Gather user feedback on toolchain detection
4. Iterate on search quality and performance
5. Package for PyPI release

---

**Status**: Ready for implementation
**Estimated Timeline**: 6 weeks to production-ready v1.0
**Dependencies**: Minimal - all open source components
**Risk**: Low - proven technologies, clear architecture

