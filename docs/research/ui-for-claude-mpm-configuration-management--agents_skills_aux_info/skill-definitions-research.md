# Skill Definitions Research

**Date**: 2026-02-14
**Task**: Research skill definition structure and metadata for UI dashboard improvements
**Researcher**: Research Agent (Task #5)

---

## 1. Skills Repository Structure (`claude-mpm-skills`)

### 1.1 Top-Level Organization

```
claude-mpm-skills/
├── manifest.json           # Central registry of ALL skills (156 total)
├── manifest-old.json       # Legacy manifest backup
├── manifest-new.json       # New manifest version
├── CLAUDE.md
├── README.md
├── LICENSE
├── scripts/                # Maintenance scripts
├── examples/               # Example skills (2 skills)
├── universal/              # Language-agnostic skills (37 skills)
│   ├── architecture/       # software-patterns
│   ├── collaboration/      # brainstorming, git-workflow, git-worktrees, stacked-prs, etc.
│   ├── data/               # database-migration, json-data-handling, reporting-pipelines, etc.
│   ├── debugging/          # systematic-debugging, root-cause-tracing, etc.
│   ├── infrastructure/     # env-manager, kubernetes, etc.
│   ├── main/               # artifacts-builder, internal-comms, mcp-builder, skill-creator
│   ├── observability/
│   ├── security/           # security-scanning
│   ├── testing/            # condition-based-waiting, test-driven-development, etc.
│   ├── verification/       # bug-fix verification
│   └── web/                # api-design-patterns, api-documentation, web-performance
└── toolchains/             # Language/platform-specific skills (117 skills)
    ├── ai/                 # 9 skills: anthropic-sdk, dspy, langchain, langgraph, etc.
    │   ├── frameworks/
    │   ├── ops/
    │   ├── protocols/
    │   ├── sdks/
    │   ├── services/
    │   ├── techniques/
    │   └── vision/
    ├── databases/          # 1 skill: mongodb
    ├── elixir/             # 4 skills: ecto-patterns, phoenix-*, phoenix-ops
    ├── golang/             # 7 skills: cli, concurrency, data, grpc, etc.
    ├── java/               # 1 skill
    ├── javascript/         # 19 skills: react, svelte, vue, nextjs, playwright, etc.
    ├── nextjs/             # 3 skills: api/validated-handler, core, v16
    ├── php/                # 6 skills: wordpress-*
    ├── platforms/          # 26 skills: auth/better-auth, deployment/vercel, etc.
    ├── python/             # 10 skills: django, fastapi, flask, pydantic, etc.
    ├── rust/               # 4 skills: axum, clap, tauri, desktop-apps
    ├── typescript/         # 14 skills: drizzle, prisma, trpc, vitest, zod, etc.
    ├── ui/                 # 4 skills: daisyui, headlessui, shadcn, tailwind
    ├── universal/          # 9 skills: graphql, dependency-audit, etc.
    └── visualbasic/
```

### 1.2 Individual Skill Directory Structure

Each skill consists of:

```
skill-name/
├── SKILL.md                # Main skill content (YAML frontmatter + markdown body)
├── metadata.json           # Separate metadata file (richer than manifest)
└── references/             # Optional reference documents
    ├── patterns.md
    ├── examples.md
    └── troubleshooting.md
```

Some skills also include: `scripts/`, `assets/`, `QUICK_REFERENCE.md`, `README.md`

---

## 2. Skill Metadata Sources (Three Distinct Layers)

### 2.1 manifest.json (Central Registry - Deployed/Available List)

The manifest is the master index. Every skill has a manifest entry. Fields common across ALL skills:

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `name` | string | Yes | Short skill name | `"dspy"` |
| `version` | string | Yes | Semantic version | `"1.0.0"` |
| `category` | string | Yes | Top-level category | `"universal"` or `"toolchain"` |
| `toolchain` | string/null | No | Language toolchain | `"ai"`, `"python"`, `null` |
| `framework` | string/null | No | Specific framework | `"dspy"`, `"nextjs"`, `null` |
| `tags` | string[] | Yes | Discovery/filtering tags | `["ai", "llm", "rag"]` |
| `entry_point_tokens` | int | Yes | Token count for entry point | `75` |
| `full_tokens` | int | Yes | Token count for full content | `10191` |
| `requires` | string[] | No | Dependency skills | `["universal-debugging-systematic-debugging"]` |
| `author` | string | Yes | Creator name | `"bobmatnyc"`, `"Claude MPM Team"` |
| `updated` | string | Yes | Last update date | `"2025-12-31"` |
| `source_path` | string | Yes | Relative path to SKILL.md | `"toolchains/ai/frameworks/dspy/SKILL.md"` |
| `has_references` | bool | No | Whether references exist | `true` |
| `reference_files` | string[] | No | List of reference filenames | `["patterns.md", "examples.md"]` |

**Manifest metadata section (global stats)**:
```json
{
  "metadata": {
    "total_skills": 156,
    "categories": { "universal": 37, "toolchains": 117, "examples": 2 },
    "toolchains": { "ai": 9, "python": 10, "javascript": 19, ... },
    "last_updated": "2026-01-28",
    "schema_version": "2.0.0"
  }
}
```

### 2.2 metadata.json (Per-Skill Rich Metadata)

Individual `metadata.json` files contain ALL manifest fields PLUS additional fields. This is the richest metadata source.

**Fields found ONLY in metadata.json (not in manifest)**:

| Field | Type | Found In | Description | Example |
|-------|------|----------|-------------|---------|
| `description` | string | DSPy, MCP | Full-text description | `"Declarative framework for..."` |
| `key_features` | string[] | DSPy | Feature list | `["Declarative signatures", ...]` |
| `use_cases` | string[] | DSPy | Usage scenarios | `["RAG pipelines", "Classification"]` |
| `performance_benchmarks` | object | DSPy | Benchmark data | `{"prompt_evaluation": {"baseline": "46.2%", ...}}` |
| `optimizers` | string[] | DSPy | Specialized lists | `["BootstrapFewShot", "MIPROv2"]` |
| `modules` | string[] | DSPy | Module catalog | `["ChainOfThought", "ReAct"]` |
| `production_adopters` | string[] | DSPy | Companies using tech | `["JetBlue", "Databricks"]` |
| `prerequisites` | object | DSPy | Requirements | `{"python": ">=3.9", "packages": ["dspy-ai"]}` |
| `installation` | object | DSPy | Install commands | `{"command": "pip install dspy-ai"}` |
| `related_skills` | string[] | DSPy, MCP, Vercel, BetterAuth | Related skill paths | `["../../sdks/anthropic", "../langchain"]` |
| `sub_skills` | string[] | OpenRouter, MCP | Sub-skill references | `[]` |
| `subcategory` | string | DSPy | Sub-category name | `"frameworks"` |
| `license` | string | All | License type | `"MIT"` |
| `created` | string | Many | Creation date | `"2025-11-30"` |
| `modified` | string | Many | Last modified date | `"2025-11-30"` |
| `maintainer` | string | Many | Maintainer name | `"Claude MPM Team"` |
| `attribution_required` | bool | Many | Attribution needed | `true` |
| `repository` | string | All | Repo URL | `"https://github.com/bobmatnyc/claude-mpm-skills"` |
| `source` | string | Some | Original source URL | `"https://github.com/bobmatnyc/claude-mpm"` |
| `service` | string | OpenRouter | Service name | `"openrouter"` |
| `platform` | string | Vercel, BetterAuth | Platform name | `"deployment"`, `"auth"` |

**Key Insight**: The metadata.json files are MUCH richer than manifest entries. DSPy has 130 lines of metadata vs ~20 lines in the manifest. Many advanced fields (key_features, use_cases, performance_benchmarks, prerequisites, installation) exist ONLY in metadata.json.

### 2.3 SKILL.md Frontmatter (Content-Level Metadata)

The SKILL.md YAML frontmatter is the content-embedded metadata. Fields found here:

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `name` | string | Display name (may differ from dir name) | `"Condition-Based Waiting"` |
| `description` | string | Brief description | `"Replace arbitrary timeouts..."` |
| `when_to_use` | string | Trigger condition | `"when tests have race conditions..."` |
| `version` | string | Content version | `"1.1.0"` |
| `languages` | string | Language applicability | `"all"` |
| `progressive_disclosure` | object | Progressive loading config | (see below) |
| `tags` | string[] | Content tags | `["architecture", "patterns"]` |

**Progressive Disclosure Structure** (found in SKILL.md frontmatter):
```yaml
progressive_disclosure:
  entry_point:
    summary: "Brief description"
    when_to_use: "Trigger condition"
    quick_start: "Step-by-step quickstart"
    core_pattern: "Code example"
  references:
    - path: references/patterns-and-implementation.md
      purpose: "Detailed implementation guide"
      when_to_read: "When implementing or debugging"
```

---

## 3. How claude-mpm Loads/Stores Skills

### 3.1 Skill Dataclass (`skills/registry.py`)

The canonical `Skill` dataclass follows the **agentskills.io specification**:

```python
@dataclass
class Skill:
    # Core spec fields (agentskills.io)
    name: str                              # Required, 1-64 chars
    description: str                       # Required, 1-1024 chars
    license: Optional[str] = None
    compatibility: Optional[str] = None
    metadata: Dict[str, Any] = None        # Arbitrary key-value
    allowed_tools: List[str] = None

    # Internal fields
    path: Path = None
    content: str = ""
    source: str = "bundled"                # 'bundled', 'user', 'project', 'pm'

    # Derived fields
    version: str = "0.1.0"
    skill_id: str = ""
    agent_types: List[str] = None
    updated_at: Optional[str] = None
    tags: List[str] = None

    # Claude-mpm extensions
    category: Optional[str] = None
    toolchain: Optional[str] = None
    progressive_disclosure: Optional[Dict] = None
    user_invocable: bool = False
```

### 3.2 SkillDiscoveryService (`services/skills/skill_discovery_service.py`)

Discovers skills from Git repository cache directories. Key behaviors:
- **Recursive SKILL.md scanning**: Finds `SKILL.md` files recursively in cache dirs
- **Frontmatter parsing**: Extracts YAML frontmatter for metadata
- **Deployment name calculation**: Flattens nested paths to hyphen-separated names
  - e.g., `collaboration/dispatching-parallel-agents/SKILL.md` -> `collaboration-dispatching-parallel-agents`
- **Resource discovery**: Finds bundled resources in `scripts/`, `references/`, `assets/`
- **Output fields**: `skill_id`, `name`, `description`, `skill_version`, `tags`, `content`, `source_file`, `agent_types`, `resources`, `deployment_name`, `relative_path`

### 3.3 SkillsDeployerService (`services/skills_deployer.py`)

Manages downloading and deploying skills from GitHub. Key operations:
- **`deploy_skills()`**: Downloads from GitHub, filters by toolchain/categories, deploys to `~/.claude/skills/`
- **`list_available_skills()`**: Downloads manifest, flattens skills, groups by category/toolchain
- **`check_deployed_skills()`**: Scans skills directory for deployed `SKILL.md` files
- **`_flatten_manifest_skills()`**: Handles both legacy flat and new nested manifest structures

### 3.4 SkillManager (`skills/skill_manager.py`)

Integrates skills with agents:
- **Agent-skill mapping**: Reads from agent JSON templates' `skills` field
- **PM skills loading**: Special PM skills from `.claude/skills/` for PM agent only
- **Agent prompt enhancement**: Appends skills content to agent prompts
- **Skill inference**: Infers agent assignments from skill content/tags

### 3.5 SkillsService (`skills/skills_service.py`)

Manages bundled skill deployment and validation:
- **Bundled skills discovery**: Scans `skills/bundled/` directory
- **Deployment**: Copies to `.claude/skills/` with path traversal protection
- **Validation**: 16 rules including YAML frontmatter, required fields, name format, description length
- **Version checking**: Compares bundled vs deployed versions

### 3.6 SkillsRegistry (`skills/skills_registry.py`)

Read-only helper for the `config/skills_registry.yaml` file:
- **Agent-skill queries**: `get_agent_skills(agent_id)` returns required + optional skills
- **Skill metadata**: `get_skill_metadata(skill_name)` returns category, source, description
- **Category/source filtering**: `get_skills_by_category()`, `get_skills_by_source()`
- **Search**: `search_skills(query)` searches name and description
- **Validation**: `validate_registry()` checks references and completeness

---

## 4. Dashboard API Exposure

### 4.1 Current API Endpoints

| Endpoint | Method | Handler | What it returns |
|----------|--------|---------|-----------------|
| `/api/config/skills/deployed` | GET | `handle_skills_deployed` | Deployed skills list |
| `/api/config/skills/available` | GET | `handle_skills_available` | Available skills from sources |
| `/api/config/skills/deploy` | POST | `deploy_skill` | Deploy a skill |
| `/api/config/skills/{skill_name}` | DELETE | `undeploy_skill` | Undeploy a skill |
| `/api/config/skills/deployment-mode` | GET | `get_deployment_mode` | Current mode + counts |
| `/api/config/skills/deployment-mode` | PUT | `set_deployment_mode` | Switch selective/full mode |
| `/api/config/project/summary` | GET | `handle_project_summary` | Skills count in summary |
| `/api/config/skill-links/` | GET | `handle_skill_links` | Skill-to-agent links |
| `/api/config/skill-links/agent/{name}` | GET | `handle_skill_links_agent` | Skills for specific agent |

### 4.2 Deployed Skills API Response (`/api/config/skills/deployed`)

Returns these fields per skill:

```json
{
  "name": "universal-testing-test-driven-development",
  "path": "/path/to/.claude/skills/universal-testing-test-driven-development",
  "description": "",            // From deployment index (often empty)
  "category": "unknown",        // From deployment index
  "collection": "",             // Collection name
  "is_user_requested": false,   // Boolean flag
  "deploy_mode": "agent_referenced",  // "user_defined" or "agent_referenced"
  "deploy_date": ""             // ISO timestamp or empty
}
```

### 4.3 Available Skills API Response (`/api/config/skills/available`)

Returns manifest fields per skill, plus:

```json
{
  "name": "dspy",
  "version": "1.0.0",
  "category": "toolchain",
  "toolchain": "ai",
  "framework": "dspy",
  "tags": ["dspy", "prompt-optimization", ...],
  "entry_point_tokens": 75,
  "full_tokens": 10191,
  "requires": [],
  "author": "claude-mpm-skills",
  "updated": "2025-12-31",
  "source_path": "toolchains/ai/frameworks/dspy/SKILL.md",
  "is_deployed": true           // Added by API handler
}
```

### 4.4 Deployment Mode API Response

```json
{
  "mode": "selective",
  "counts": {
    "agent_referenced": 12,
    "user_defined": 3,
    "pm_core": 5,
    "core": 8,
    "total_deployed": 28
  },
  "explanation": "selective: Only agent-referenced + user-defined + core skills"
}
```

---

## 5. Gap Analysis

### 5.1 Metadata Available but NOT Exposed via API

| Field | Source | Value for UI | Priority |
|-------|--------|--------------|----------|
| `description` | metadata.json | Show in skill detail panel | **HIGH** |
| `key_features` | metadata.json | Feature highlights in detail view | MEDIUM |
| `use_cases` | metadata.json | Help users understand applicability | MEDIUM |
| `related_skills` | metadata.json | Skill graph / "see also" links | MEDIUM |
| `prerequisites` | metadata.json | Show required setup | MEDIUM |
| `installation` | metadata.json | Install commands for users | MEDIUM |
| `when_to_use` | SKILL.md frontmatter | Quick filtering trigger | **HIGH** |
| `progressive_disclosure` | SKILL.md frontmatter | Show entry point summary | MEDIUM |
| `has_references` | manifest | Badge/indicator for rich skills | LOW |
| `reference_files` | manifest | List supplementary docs | LOW |
| `entry_point_tokens` / `full_tokens` | manifest | Size indicator | LOW |
| `requires` | manifest | Dependency visualization | MEDIUM |
| `subcategory` | metadata.json | Finer categorization (frameworks, ops) | MEDIUM |
| `platform` | metadata.json | Platform grouping (auth, deployment) | LOW |
| `performance_benchmarks` | metadata.json | Data-driven comparison | LOW |
| `production_adopters` | metadata.json | Social proof | LOW |

### 5.2 Key Information Users Would Want

1. **What does this skill do?** - `description` + `when_to_use` (partially exposed)
2. **How big is it?** - `entry_point_tokens` / `full_tokens` (available but not exposed)
3. **What agents use it?** - Partially via skill-links API
4. **What depends on it?** - `requires` field (available but not visualized)
5. **Is it deployed?** - `is_deployed` flag (exposed in available list)
6. **How to deploy it?** - Deploy API exists, but no UI for `user_defined` vs `agent_referenced`
7. **What related skills exist?** - `related_skills` in metadata.json (not exposed)
8. **When was it last updated?** - `updated` in manifest (available but not prominent)

### 5.3 Category/Subcategory Organization

**Universal skills** use a 2-level hierarchy:
```
universal/
├── architecture/    (1 skill)
├── collaboration/   (7 skills)
├── data/            (5 skills)
├── debugging/       (2+ skills)
├── infrastructure/  (2+ skills)
├── main/            (4 skills)
├── observability/
├── security/        (1 skill)
├── testing/         (3+ skills)
├── verification/    (1 skill)
└── web/             (3 skills)
```

**Toolchain skills** use a 3-level hierarchy:
```
toolchains/
├── {language}/           # ai, python, javascript, rust, etc.
│   ├── {subcategory}/    # frameworks, testing, data, cli, ops, etc.
│   │   └── {skill}/      # Actual skill directory
```

**This hierarchy is partially lost** in the API responses - the manifest uses `toolchain` field for grouping but the subcategory path information is only in `source_path`.

### 5.4 Deployment Index Tracking

The `selective_skill_deployer.py` maintains a deployment index at `.claude/skills/.deployment_index.json`:

```json
{
  "deployed_skills": {
    "skill-name": {
      "description": "...",
      "category": "...",
      "collection": "...",
      "deployed_at": "2025-12-22T10:30:00Z"
    }
  },
  "user_requested_skills": ["skill-a", "skill-b"],
  "last_sync": "2025-12-22T10:30:00Z"
}
```

### 5.5 Immutable (Protected) Skills

Two sets of protected skills that cannot be undeployed:
- **PM_CORE_SKILLS**: Framework management skills (mpm-*)
- **CORE_SKILLS**: Essential development skills

---

## 6. Concrete Metadata Examples

### 6.1 Minimal Skill (brainstorming)

**manifest.json entry**:
```json
{
  "name": "brainstorming",
  "version": "1.0.0",
  "category": "universal",
  "toolchain": null,
  "framework": null,
  "tags": ["debugging", "frontend", "testing"],
  "entry_point_tokens": 61,
  "full_tokens": 649,
  "requires": [],
  "author": "bobmatnyc",
  "updated": "2025-12-03",
  "source_path": "universal/collaboration/brainstorming/SKILL.md"
}
```

**metadata.json** (adds 8 extra fields):
```json
{
  "license": "MIT",
  "source": "https://github.com/bobmatnyc/claude-mpm",
  "created": "2025-11-21",
  "modified": "2025-11-21",
  "maintainer": "Claude MPM Team",
  "attribution_required": true,
  "repository": "https://github.com/bobmatnyc/claude-mpm-skills"
}
```

### 6.2 Rich Skill (dspy)

**metadata.json** adds 60+ lines beyond manifest, including:
- `description`: Full description text
- `key_features`: 10 feature items
- `use_cases`: 10 use case items
- `performance_benchmarks`: 5 benchmark entries with baseline/optimized/improvement
- `optimizers`: 6 optimizer names
- `modules`: 5 module names
- `production_adopters`: 7 company names
- `prerequisites`: Python version + packages + optional deps
- `installation`: pip install commands per provider
- `related_skills`: Relative path references
- `subcategory`: "frameworks"

### 6.3 Platform Skill (vercel-overview)

**metadata.json** introduces `platform` field and extensive `related_skills`:
```json
{
  "platform": "deployment",
  "related_skills": [
    "vercel-deployments-builds",
    "vercel-functions-runtime",
    "vercel-storage-data",
    "vercel-networking-domains",
    "vercel-observability",
    "vercel-security-access",
    "vercel-teams-billing",
    "vercel-ai"
  ]
}
```

### 6.4 Skill with Dependencies (bug-fix-verification)

```json
{
  "name": "bug-fix-verification",
  "requires": ["universal-debugging-systematic-debugging"]
}
```

---

## 7. Data Flow Summary

```
                                GitHub Repository
                                      │
                                      ▼
                          ┌──────────────────────┐
                          │   manifest.json       │  (156 skills, basic metadata)
                          │   metadata.json (x N) │  (rich per-skill metadata)
                          │   SKILL.md (x N)      │  (content + frontmatter)
                          └──────────┬───────────┘
                                     │ git clone / download ZIP
                                     ▼
                      ┌──────────────────────────────┐
                      │   SkillsDeployerService       │
                      │   - _flatten_manifest_skills() │  (parses manifest)
                      │   - list_available_skills()    │  (returns manifest data)
                      │   - deploy_skills()            │  (copies SKILL.md + refs)
                      └──────────────┬───────────────┘
                                     │
              ┌──────────────────────┼──────────────────────┐
              │                      │                      │
              ▼                      ▼                      ▼
    ┌──────────────┐    ┌──────────────────┐    ┌──────────────────┐
    │ ~/.claude/   │    │ .claude/skills/  │    │ config/skills_   │
    │ skills/      │    │ (project-level)  │    │ registry.yaml    │
    │ (user-level) │    │ + .deployment_   │    │ (agent mappings) │
    └──────────────┘    │   index.json     │    └──────────────────┘
                        └────────┬─────────┘
                                 │
                                 ▼
                    ┌──────────────────────────┐
                    │   Dashboard API Routes   │
                    │   /api/config/skills/*   │
                    │                          │
                    │ Returns:                 │
                    │ - Deployed: name, path,  │
                    │   deploy_mode, date      │
                    │ - Available: manifest    │
                    │   fields + is_deployed   │
                    └──────────────────────────┘
```

---

## 8. Key Findings for UI Design

### 8.1 Multiple Metadata Richness Levels

Skills have THREE levels of metadata richness:
1. **Basic** (manifest): name, version, category, toolchain, tags (~12 fields)
2. **Standard** (metadata.json adds): license, created, modified, related_skills (~20 fields)
3. **Rich** (metadata.json for complex skills adds): key_features, use_cases, benchmarks, prerequisites, installation (~30+ fields)

The UI should gracefully handle all three levels, showing what's available without requiring all fields.

### 8.2 Hierarchical Organization Not Fully Exploited

The repository has a clear 3-level hierarchy (category/subcategory/skill) but the API flattens this. The `source_path` field encodes the full path (e.g., `toolchains/ai/frameworks/dspy/SKILL.md`) which could be parsed for:
- Tree view navigation
- Breadcrumb trails
- Grouped listings

### 8.3 Deployed vs Available Metadata Asymmetry

- **Available skills**: Rich metadata from manifest (name, version, tags, tokens, etc.)
- **Deployed skills**: Sparse metadata from deployment index (name, path, deploy_mode)

The deployed skills API loses most of the manifest metadata. This could be enriched by cross-referencing with cached manifest data.

### 8.4 Token Counts as Size Indicators

Every skill has `entry_point_tokens` and `full_tokens` counts. These are valuable UI indicators:
- Small skills: <1000 tokens (e.g., brainstorming: 649)
- Medium skills: 1000-5000 tokens
- Large skills: 5000-15000 tokens (e.g., software-patterns: 15814)
- Very large skills: >15000 tokens (e.g., env-manager: 17364, api-design-patterns: 34968)

### 8.5 Dependency and Relationship Graphs

Two types of relationships exist:
- **`requires`**: Hard dependencies (e.g., bug-fix-verification requires systematic-debugging)
- **`related_skills`**: Soft associations (e.g., dspy -> anthropic-sdk, langchain)

Both could power a visual skill graph in the UI.

### 8.6 Deployment Protection System

Skills have deployment protection via immutable sets (PM_CORE_SKILLS, CORE_SKILLS). The UI should:
- Show which skills are protected (with lock icon or similar)
- Prevent undeploy actions for protected skills
- Explain why certain skills can't be removed

### 8.7 Progressive Disclosure in Content

Skills use a progressive disclosure pattern with:
- Entry point summary (loaded first)
- Reference documents (loaded on demand)

This could inform a UI pattern where skill cards show the entry point summary, with expandable sections for reference content.
