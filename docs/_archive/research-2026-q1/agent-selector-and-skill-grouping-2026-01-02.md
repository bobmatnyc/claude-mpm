# Agent Selector and Skill Structure Research
**Research Date:** 2026-01-02
**Researcher:** Claude (Research Agent)
**Purpose:** Understand agent selector implementation and skill structure for topic-based skill grouping feature

---

## Executive Summary

This research analyzes Claude MPM's agent selection UI and skill metadata structure to inform the design of a topic-based skill grouping feature for the agent selector.

**Key Findings:**
1. **Agent Selector:** Interactive questionary-based UI with arrow-key navigation in `agent_wizard.py`
2. **Skill Structure:** Well-organized manifest with tags, toolchain, and framework metadata
3. **Agent Frontmatter:** Uses `skills:` field listing skill names as YAML array
4. **Grouping Potential:** Skills already have `toolchain` and `framework` fields for topic-based grouping

---

## 1. Agent Selector Implementation

### File Location
**Primary File:** `/Users/masa/Projects/claude-mpm/src/claude_mpm/cli/interactive/agent_wizard.py`

### UI/UX Pattern
The agent wizard uses **questionary** library for interactive selection with arrow-key navigation:

```python
# Line 13-14: Import questionary for interactive prompts
import questionary
from questionary import Style

# Line 26-34: Custom cyan-themed style matching Rich output
QUESTIONARY_STYLE = Style(
    [
        ("selected", "fg:cyan bold"),
        ("pointer", "fg:cyan bold"),
        ("highlighted", "fg:cyan"),
        ("question", "fg:cyan bold"),
    ]
)

# Example usage (Line 384-388):
choice = questionary.select(
    "Agent Management Menu:",
    choices=menu_choices,
    style=QUESTIONARY_STYLE,
).ask()
```

### Selection/Deselection Pattern

**Current Implementation (Single-Select):**
```python
# Line 1202-1204: Agent deployment selection
choice = questionary.select(
    "Select agent to deploy:",
    choices=agent_choices,
    style=QUESTIONARY_STYLE
).ask()
```

**Multi-Select Pattern (Not Currently Used for Agents):**
Questionary supports `checkbox` for multi-select:
```python
# NOT IN CODEBASE - Reference pattern
selected = questionary.checkbox(
    "Select skills to deploy:",
    choices=skill_choices
).ask()
```

### Grouping Logic

**Category-Based Filtering (Line 1332-1360):**
```python
categories = [
    "engineer/backend",
    "engineer/frontend",
    "qa",
    "ops",
    "documentation",
    "universal",
]

# Arrow-key selection of category
cat_choice = questionary.select(
    "Select category:",
    choices=cat_choices,
    style=QUESTIONARY_STYLE
).ask()

# Filter agents by category prefix
filtered_agents = [
    a for a in all_agents
    if a.get("category", "").startswith(category)
]
```

**Key UI Elements:**
- Arrow-key navigation with questionary.select()
- Cyan color scheme for consistency with Rich output
- "N. Description" format for numbered choices
- ESC key cancellation support
- Back to menu navigation

---

## 2. Skill Structure and Storage

### Storage Location
**System Skills Cache:** `~/.claude-mpm/cache/skills/system/`

**Directory Structure:**
```
~/.claude-mpm/cache/skills/system/
├── manifest.json                    # Central skill registry
├── .bundles/                        # Bundled skill groups
├── .github/                         # GitHub metadata
├── docs/                            # Skill documentation
├── examples/                        # Example implementations
├── scripts/                         # Utility scripts
├── toolchains/                      # Toolchain-specific skills
│   ├── python/
│   ├── typescript/
│   ├── rust/
│   └── ...
└── universal/                       # Universal skills (all languages)
    ├── collaboration/
    ├── data/
    ├── main/
    ├── testing/
    ├── verification/
    └── web/
```

### Skill Manifest Structure

**Manifest Location:** `~/.claude-mpm/cache/skills/system/manifest.json`

**JSON Schema:**
```json
{
  "version": "1.0.0",
  "repository": "https://github.com/bobmatnyc/claude-mpm-skills",
  "updated": "2026-01-02",
  "description": "Curated collection of Claude Code skills...",
  "skills": {
    "universal": [
      {
        "name": "api-design-patterns",
        "version": "1.0.0",
        "category": "universal",
        "toolchain": null,              // ← KEY FOR GROUPING
        "framework": null,              // ← KEY FOR GROUPING
        "tags": [                       // ← RICH METADATA
          "api", "rest", "graphql", "grpc",
          "architecture", "web", "design-patterns",
          "oauth", "jwt", "authentication"
        ],
        "entry_point_tokens": 85,
        "full_tokens": 34968,
        "requires": [],                 // ← Skill dependencies
        "author": "Claude MPM Skills",
        "updated": "2025-12-31",
        "source_path": "universal/web/api-design-patterns/SKILL.md",
        "has_references": true,
        "reference_files": [
          "authentication.md",
          "graphql-patterns.md"
        ]
      }
    ],
    "python": [...],
    "typescript": [...],
    "rust": [...]
  }
}
```

### Skill Metadata Fields

**Core Identification:**
- `name`: Skill identifier (e.g., "api-design-patterns")
- `version`: Semantic version (e.g., "1.0.0")
- `category`: Top-level category ("universal", "python", "typescript", etc.)

**Grouping Fields (CRITICAL FOR TOPIC FEATURE):**
- `toolchain`: Language/platform (e.g., "python", "typescript", "rust", null for universal)
- `framework`: Specific framework (e.g., "fastapi", "nextjs", "react", null)
- `tags`: Array of descriptive tags for fine-grained filtering

**Content Metrics:**
- `entry_point_tokens`: Skill.md size (lightweight metadata)
- `full_tokens`: Total tokens including reference files
- `has_references`: Boolean indicating additional documentation
- `reference_files`: Array of reference doc filenames

**Dependencies:**
- `requires`: Array of skill names this skill depends on
  - Example: `["universal-debugging-systematic-debugging"]`
  - Flat string array format (not hierarchical)

**Metadata:**
- `author`: Maintainer/author name
- `updated`: ISO date (YYYY-MM-DD format)
- `source_path`: Relative path to SKILL.md file

---

## 3. Agent Frontmatter for Skill Dependencies

### Frontmatter Format

**Location:** Agent markdown files use YAML frontmatter to specify skill dependencies

**Example (from `~/.claude-mpm/cache/remote-agents/documentation/documentation.md`):**
```yaml
---
name: Documentation
description: 'Technical documentation specialist...'
version: 1.0.0
schema_version: 1.3.0
agent_id: documentation
agent_type: documentation
resource_tier: standard
tags:
  - documentation
  - technical-writing
skills:                              # ← SKILL DEPENDENCY FIELD
  - brainstorming                    # Skill names as YAML array
  - dispatching-parallel-agents
  - git-workflow
  - requesting-code-review
  - writing-plans
mcp:
  - name: filesystem
    required: true
  - name: git
    optional: false
---
```

### Skill Dependency Field Details

**Field Name:** `skills:`
**Format:** YAML array of skill names (kebab-case strings)
**Validation:** Skill names must exist in manifest.json
**Optional:** Empty array `[]` if no skill dependencies

**Examples from Codebase:**

1. **QA Agent** (Line 39-44 of `qa/qa.md`):
```yaml
skills:
  - pr-quality-checklist
  - brainstorming
  - dispatching-parallel-agents
  - git-workflow
  - requesting-code-review
```

2. **Security Agent** (Line 38-43 of `security/security.md`):
```yaml
skills:
  - dependency-audit
  - api-security-review
  - brainstorming
  - dispatching-parallel-agents
  - git-workflow
```

3. **Web QA Agent** (Line 58-63 of `qa/web-qa.md`):
```yaml
skills:
  - playwright                       # Framework-specific skill
  - brainstorming
  - dispatching-parallel-agents
  - git-workflow
  - requesting-code-review
```

4. **Research Agent** (Line 52-57 of `universal/research.md`):
```yaml
skills:
  - dspy                             # AI framework skills
  - langchain
  - langgraph
  - mcp
  - anthropic-sdk
```

### Skill Dependency Resolution

**Service:** `SkillsService` in `src/claude_mpm/skills/skills_service.py`

**Method Pattern (from Line 124-149 of skills.py):**
```python
def get_skills_for_agent(self, agent_name: str) -> List[str]:
    """Get skills required by an agent.

    Args:
        agent_name: Agent identifier

    Returns:
        List of skill names required by the agent
    """
    # Read agent frontmatter
    # Parse skills: field
    # Return list of skill names
```

---

## 4. Current Skill Grouping Structure

### Manifest Categorization

**Top-Level Categories (from manifest.json):**
```json
{
  "skills": {
    "universal": [...],      // Cross-language skills
    "python": [...],         // Python-specific skills
    "typescript": [...],     // TypeScript-specific skills
    "javascript": [...],     // JavaScript-specific skills
    "rust": [...],          // Rust-specific skills
    "go": [...],            // Go-specific skills
    ...
  }
}
```

### Grouping Dimensions

**1. By Category (Top-Level)**
- `universal`: Cross-language skills (testing, collaboration, architecture)
- `python`, `typescript`, `rust`, etc.: Language-specific skills

**2. By Toolchain (Skill.toolchain field)**
- `null`: Universal skills
- `"python"`: Python ecosystem skills
- `"typescript"`: TypeScript ecosystem skills
- `"rust"`: Rust ecosystem skills

**3. By Framework (Skill.framework field)**
- `null`: Framework-agnostic
- `"fastapi"`: FastAPI-specific patterns
- `"nextjs"`: Next.js-specific patterns
- `"react"`: React-specific patterns
- `"svelte"`: Svelte-specific patterns

**4. By Tags (Skill.tags array)**
- Semantic tags for fine-grained filtering
- Examples:
  - `["api", "rest", "graphql", "authentication"]`
  - `["testing", "playwright", "e2e"]`
  - `["database", "migration", "schema", "production"]`

### Directory-Based Organization

**Physical Storage Layout:**
```
~/.claude-mpm/cache/skills/system/
├── universal/                       # Universal skills
│   ├── collaboration/              # Team workflows
│   │   ├── brainstorming/
│   │   └── dispatching-parallel-agents/
│   ├── data/                       # Data patterns
│   │   ├── database-migration/
│   │   └── graphql/
│   ├── testing/                    # Testing patterns
│   │   ├── condition-based-waiting/
│   │   └── webapp-testing/
│   └── web/                        # Web patterns
│       ├── api-design-patterns/
│       └── api-documentation/
└── toolchains/                      # Language-specific
    ├── python/
    │   ├── fastapi/
    │   ├── django/
    │   └── async/
    ├── typescript/
    │   ├── nextjs/
    │   ├── react/
    │   └── svelte/
    └── rust/
        ├── tauri/
        └── tokio/
```

---

## 5. Recommended Approach for Topic-Based Skill Grouping

### Proposed UI Flow

**Option 1: Two-Tier Selection (Recommended)**
```
1. Select Topic/Category:
   ├─ 🌐 Universal (All Languages)
   ├─ 🐍 Python
   ├─ 📘 TypeScript
   ├─ ⚙️  Rust
   ├─ 🔵 Go
   └─ ☕ Java

2. Select Skills (Multi-Select):
   [If Universal selected]
   ☐ api-design-patterns        (REST, GraphQL, gRPC patterns)
   ☐ brainstorming              (Team collaboration workflows)
   ☐ database-migration         (Schema evolution strategies)
   ☐ dispatching-parallel-agents (Multi-agent coordination)
   ☑ git-workflow               (Git best practices)

   [If Python selected]
   ☐ fastapi-patterns           (FastAPI-specific patterns)
   ☐ pytest-advanced            (Advanced testing patterns)
   ☑ python-async               (Async/await best practices)
```

**Option 2: Inline Grouping with Separators**
```
Select Skills (Multi-Select):

─── 🌐 Universal Skills ───
☐ api-design-patterns        (REST, GraphQL, gRPC)
☑ git-workflow               (Git best practices)
☐ brainstorming              (Team workflows)

─── 🐍 Python Skills ───
☑ python-async               (Async patterns)
☐ fastapi-patterns           (FastAPI-specific)
☐ pytest-advanced            (Advanced testing)

─── 📘 TypeScript Skills ───
☐ nextjs-patterns            (Next.js best practices)
☐ react-hooks                (React hooks patterns)
```

**Option 3: Filterable List with Tags**
```
Filter by: [All] [Universal] [Python] [TypeScript] [Rust]

Select Skills:
☐ api-design-patterns        [universal] [web]
☑ git-workflow               [universal] [collaboration]
☑ python-async               [python] [async]
☐ fastapi-patterns           [python] [fastapi]
☐ nextjs-patterns            [typescript] [nextjs]
```

### Implementation Strategy

**1. Data Preparation**
```python
def group_skills_by_topic(manifest: dict) -> dict:
    """Group skills by toolchain/category for UI display.

    Returns:
        {
            "universal": [skill1, skill2, ...],
            "python": [skill3, skill4, ...],
            "typescript": [skill5, skill6, ...],
            ...
        }
    """
    grouped = {}
    for category, skills in manifest["skills"].items():
        for skill in skills:
            toolchain = skill.get("toolchain") or category
            if toolchain not in grouped:
                grouped[toolchain] = []
            grouped[toolchain].append(skill)
    return grouped
```

**2. UI Rendering (Option 1: Two-Tier)**
```python
# Step 1: Topic selection
topics = list(grouped_skills.keys())
topic_choices = [
    f"🌐 Universal (All Languages)" if t == "universal"
    else f"🐍 {t.title()}" for t in topics
]

selected_topic = questionary.select(
    "Select skill topic:",
    choices=topic_choices,
    style=QUESTIONARY_STYLE
).ask()

# Step 2: Skill multi-select
skills_in_topic = grouped_skills[selected_topic]
skill_choices = [
    f"{skill['name']:<30} {skill.get('description', '')[:50]}"
    for skill in skills_in_topic
]

selected_skills = questionary.checkbox(
    f"Select skills from {selected_topic}:",
    choices=skill_choices,
    style=QUESTIONARY_STYLE
).ask()
```

**3. Metadata Enhancement**
- Add emoji icons for visual categorization:
  - 🌐 Universal
  - 🐍 Python
  - 📘 TypeScript
  - ⚙️ Rust
  - 🔵 Go
  - ☕ Java

- Show token counts for large skills:
  - `api-design-patterns (35K tokens)`
  - `database-migration (10K tokens)`

- Display dependencies:
  - `bug-fix-verification → requires: systematic-debugging`

### Edge Cases to Handle

1. **Skills with Multiple Toolchains:**
   - Decision: Show in primary toolchain only (use first in array)
   - Alternative: Allow cross-listing with indicator

2. **Framework-Specific Skills:**
   - Option A: Nest under toolchain (python → fastapi)
   - Option B: Show framework in description
   - Recommended: **Option B** (flatter hierarchy)

3. **Empty Categories:**
   - Hide categories with no skills
   - Or show with "(0 skills)" indicator

4. **Search/Filter:**
   - Add text search across skill names and tags
   - Filter by token count (< 5K, < 20K, > 20K)

---

## 6. Code Examples

### Example 1: Grouping Skills by Toolchain
```python
from pathlib import Path
import json

manifest_path = Path.home() / ".claude-mpm/cache/skills/system/manifest.json"
manifest = json.loads(manifest_path.read_text())

# Group by toolchain
by_toolchain = {}
for category, skills in manifest["skills"].items():
    for skill in skills:
        toolchain = skill.get("toolchain") or category
        by_toolchain.setdefault(toolchain, []).append({
            "name": skill["name"],
            "description": skill.get("tags", [])[:3],  # First 3 tags
            "tokens": skill.get("full_tokens", 0),
            "requires": skill.get("requires", [])
        })

# Output grouped structure
for toolchain, skills in sorted(by_toolchain.items()):
    print(f"\n=== {toolchain.upper()} ({len(skills)} skills) ===")
    for skill in skills[:5]:  # Show first 5
        deps = f" → {', '.join(skill['requires'])}" if skill['requires'] else ""
        print(f"  • {skill['name']}{deps}")
```

### Example 2: Topic-Based Skill Selector
```python
import questionary
from questionary import Style

STYLE = Style([
    ("selected", "fg:cyan bold"),
    ("pointer", "fg:cyan bold"),
])

def select_skills_by_topic(grouped_skills: dict) -> list[str]:
    """Interactive topic-based skill selector.

    Args:
        grouped_skills: Dict mapping toolchain → skills

    Returns:
        List of selected skill names
    """
    # Step 1: Select topic
    topic_icons = {
        "universal": "🌐",
        "python": "🐍",
        "typescript": "📘",
        "rust": "⚙️",
        "go": "🔵",
        "java": "☕"
    }

    topic_choices = [
        f"{topic_icons.get(t, '•')} {t.title()} ({len(skills)} skills)"
        for t, skills in grouped_skills.items()
    ]

    selected_topic_display = questionary.select(
        "Select skill topic:",
        choices=topic_choices,
        style=STYLE
    ).ask()

    if not selected_topic_display:
        return []  # User cancelled

    # Extract toolchain from selection
    selected_topic = selected_topic_display.split()[1].lower()

    # Step 2: Multi-select skills
    skills = grouped_skills[selected_topic]
    skill_choices = [
        f"{s['name']:<35} ({s.get('full_tokens', 0):>5,} tokens)"
        for s in skills
    ]

    selected_skills = questionary.checkbox(
        f"Select skills from {selected_topic}:",
        choices=skill_choices,
        style=STYLE
    ).ask()

    if not selected_skills:
        return []  # User cancelled

    # Extract skill names from selections
    return [choice.split()[0] for choice in selected_skills]
```

### Example 3: Reading Agent Skill Dependencies
```python
import yaml
from pathlib import Path

def get_agent_skills(agent_path: Path) -> list[str]:
    """Extract skill dependencies from agent frontmatter.

    Args:
        agent_path: Path to agent markdown file

    Returns:
        List of skill names required by agent
    """
    content = agent_path.read_text()

    # Split frontmatter from content
    if not content.startswith("---"):
        return []

    parts = content.split("---", 2)
    if len(parts) < 3:
        return []

    frontmatter = yaml.safe_load(parts[1])
    return frontmatter.get("skills", [])

# Example usage
agent_path = Path("~/.claude-mpm/cache/remote-agents/qa/qa.md").expanduser()
skills = get_agent_skills(agent_path)
print(f"QA Agent requires: {', '.join(skills)}")
# Output: QA Agent requires: pr-quality-checklist, brainstorming, ...
```

---

## 7. Integration Points

### Where to Add Topic Grouping

**1. Agent Creation Wizard (agent_wizard.py)**
- **Line 624-668:** `_get_capabilities_configuration()` method
- **Enhancement:** Replace numbered selection with topic-grouped multi-select

**2. Skills Management Command (skills.py)**
- **Line 120-150:** `_list_skills()` method
- **Enhancement:** Add `--by-topic` flag for grouped display

**3. Agent Deployment (agent_wizard.py)**
- **Line 1174-1290:** `_deploy_agent_interactive()` method
- **Enhancement:** Show agent's skill dependencies grouped by topic

### Services to Extend

**1. SkillsService (skills_service.py)**
- Add method: `get_skills_by_toolchain() -> dict[str, list[dict]]`
- Add method: `get_skills_by_framework(framework: str) -> list[dict]`
- Add method: `search_skills(query: str, tags: list[str]) -> list[dict]`

**2. AgentWizard (agent_wizard.py)**
- Add method: `_select_skills_by_topic() -> list[str]`
- Update: `_get_capabilities_configuration()` to use topic grouping

**3. CLI Parsers (skills_parser.py)**
- Add argument: `--topic` for filtering by toolchain
- Add argument: `--framework` for filtering by framework
- Add flag: `--group-by-topic` for grouped display

---

## 8. Testing Considerations

### Test Data Requirements

1. **Manifest with Multiple Toolchains:**
   - Universal skills (toolchain: null)
   - Python skills (toolchain: "python")
   - TypeScript skills (toolchain: "typescript")

2. **Skills with Dependencies:**
   - Skill A requires Skill B (same toolchain)
   - Skill C requires Skill D (different toolchain)

3. **Edge Cases:**
   - Empty category (no skills)
   - Skill with multiple tags
   - Skill with no description

### Test Scenarios

1. **Topic Selection:**
   - Select universal → verify only universal skills shown
   - Select python → verify only python skills shown
   - Cancel topic selection → verify graceful exit

2. **Skill Multi-Select:**
   - Select 0 skills → verify empty list returned
   - Select all skills → verify complete list returned
   - Cancel skill selection → verify previous menu

3. **Dependency Resolution:**
   - Select skill with dependencies → verify dependencies included
   - Select skill depending on cross-toolchain skill → verify both toolchains accessible

---

## 9. Performance Considerations

### Manifest Loading
- **Current:** Loaded from JSON file (~100KB)
- **Optimization:** Cache manifest in memory for session
- **Impact:** < 100ms load time (acceptable)

### Skill Filtering
- **Current:** In-memory filtering with list comprehensions
- **Scaling:** 500+ skills → O(n) linear scan
- **Optimization:** Build toolchain index on manifest load

### UI Rendering
- **Questionary Performance:** Handles 100+ items smoothly
- **Limit:** Show top 50 per category, add "Show More" option
- **Grouping Overhead:** Minimal (preprocessing on load)

---

## 10. Future Enhancements

### Phase 1: Basic Topic Grouping (MVP)
- ✅ Group skills by toolchain (universal, python, typescript, etc.)
- ✅ Two-tier selection (topic → skills)
- ✅ Multi-select with questionary.checkbox()

### Phase 2: Advanced Filtering
- 🔲 Framework-based sub-grouping (python → fastapi, django)
- 🔲 Tag-based search/filter
- 🔲 Token count filtering (show only lightweight skills)
- 🔲 Dependency visualization

### Phase 3: Smart Recommendations
- 🔲 Suggest skills based on agent type
- 🔲 Auto-include skill dependencies
- 🔲 Conflict detection (incompatible skills)
- 🔲 Usage analytics (popular skills)

### Phase 4: Custom Collections
- 🔲 Save skill combinations as presets
- 🔲 Import/export skill collections
- 🔲 Share collections with team
- 🔲 Version skill collections

---

## Conclusion

### Summary
Claude MPM has a well-structured foundation for topic-based skill grouping:
- **Agent Selector:** Uses questionary with arrow-key navigation (proven UX pattern)
- **Skill Manifest:** Rich metadata with toolchain, framework, and tags
- **Agent Frontmatter:** Clean YAML array for skill dependencies
- **Grouping Dimensions:** Multiple axes (category, toolchain, framework, tags)

### Recommended Implementation
**Option 1 (Two-Tier Selection)** is the best approach:
1. First select topic/toolchain (universal, python, typescript, etc.)
2. Then multi-select skills from that topic
3. Show dependencies automatically
4. Display token counts for awareness

### Next Steps
1. Implement `get_skills_by_toolchain()` in SkillsService
2. Create `_select_skills_by_topic()` in AgentWizard
3. Update `_get_capabilities_configuration()` to use topic selector
4. Add topic-based display to `skills list` command
5. Add tests for topic grouping and multi-select
6. Update documentation with new workflow

### Code Locations Summary
- **Agent Selector:** `src/claude_mpm/cli/interactive/agent_wizard.py` (Line 384-388)
- **Skills Service:** `src/claude_mpm/skills/skills_service.py` (Line 124-149)
- **Skill Manifest:** `~/.claude-mpm/cache/skills/system/manifest.json`
- **Agent Frontmatter:** `~/.claude-mpm/cache/remote-agents/*/` (skills: field in YAML)
- **UI Library:** questionary (already integrated, Line 13-34 of agent_wizard.py)

---

## Appendices

### Appendix A: Skill Manifest Schema
```typescript
interface SkillManifest {
  version: string;
  repository: string;
  updated: string;
  description: string;
  skills: {
    [category: string]: Skill[];
  };
}

interface Skill {
  name: string;
  version: string;
  category: string;
  toolchain: string | null;      // For grouping
  framework: string | null;      // For sub-grouping
  tags: string[];                // For filtering
  entry_point_tokens: number;
  full_tokens: number;
  requires: string[];            // Dependency names
  author: string;
  updated: string;
  source_path: string;
  has_references?: boolean;
  reference_files?: string[];
}
```

### Appendix B: Agent Frontmatter Schema
```yaml
---
name: string
description: string
version: string
schema_version: string
agent_id: string
agent_type: string
resource_tier: string
tags: string[]
skills: string[]                 # ← Skill dependency field
mcp:
  - name: string
    required: boolean
    optional: boolean
---
```

### Appendix C: Questionary Patterns
```python
# Single select (current agent selector)
choice = questionary.select(
    "Select option:",
    choices=["Option 1", "Option 2", "Option 3"],
    style=QUESTIONARY_STYLE
).ask()

# Multi-select (recommended for skills)
selected = questionary.checkbox(
    "Select skills:",
    choices=skill_choices,
    style=QUESTIONARY_STYLE
).ask()

# Text input with validation
answer = questionary.text(
    "Enter skill name:",
    validate=lambda val: len(val) > 0 or "Cannot be empty"
).ask()

# Confirmation
confirmed = questionary.confirm(
    "Deploy these skills?",
    default=False
).ask()
```

---

**End of Research Report**
