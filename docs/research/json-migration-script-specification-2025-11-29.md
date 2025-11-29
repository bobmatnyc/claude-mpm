# JSON to Markdown Agent Template Migration Script Specification

**Research Date**: 2025-11-29
**Ticket**: 1M-393 - Create one-time migration script for JSON templates
**Parent Issue**: 1M-382
**Priority**: high
**Status**: open

---

## Executive Summary

This research analyzes the current JSON agent template structure and provides a comprehensive specification for building an automated migration script to convert JSON templates to markdown format with YAML frontmatter. The migration affects 40 JSON templates in `/src/claude_mpm/agents/templates/` and must preserve all metadata while generating valid markdown files.

**Key Findings:**
- 40 JSON agent templates need conversion
- All templates follow `agent_schema.json` version 1.3.0
- Existing frontmatter validation infrastructure can be reused
- AgentTemplateBuilder already generates markdown from JSON
- Migration can be non-destructive with dry-run mode

---

## Questions

1. Should the script archive original JSON files or delete them after migration?
2. Should the migration validate output files with existing FrontmatterValidator?
3. Should the script update code references to JSON files automatically?
4. What should the naming convention be for migrated files (agent_id.md vs. current naming)?

---

## Findings

### 1. Current JSON Template Structure

**Location**: `/Users/masa/Projects/claude-mpm/src/claude_mpm/agents/templates/*.json`

**Count**: 40 JSON templates including:
- research.json
- engineer.json
- qa.json
- security.json
- ticketing.json
- Language-specific engineers (python, typescript, rust, etc.)
- Ops agents (gcp_ops, local_ops, vercel_ops, etc.)
- And 30+ more specialized agents

**Schema Version**: 1.3.0 (defined in `/src/claude_mpm/schemas/agent_schema.json`)

**Required Fields** (from schema):
```json
{
  "schema_version": "^\\d+\\.\\d+\\.\\d+$",
  "agent_id": "^[a-z][a-z0-9_-]*$",
  "agent_version": "^\\d+\\.\\d+\\.\\d+$",
  "agent_type": "enum[...]",
  "metadata": {
    "name": "string (3-50 chars)",
    "description": "string (10-250 chars)",
    "tags": ["array of strings"]
  },
  "capabilities": {
    "model": "opus|sonnet|haiku",
    "resource_tier": "basic|standard|intensive|lightweight|high"
  },
  "instructions": "string (10-8000 chars)"
}
```

**Optional Fields** (commonly used):
- `template_version`: Semantic version for template tracking
- `template_changelog`: Array of version history entries
- `dependencies`: Python packages, system tools
- `knowledge`: domain_expertise, best_practices, constraints, examples
- `interactions`: input_format, output_format, handoff_agents, triggers
- `testing`: test_cases, performance_benchmarks
- `memory_routing`: categories, keywords, retention_policy
- `skills`: Array of skill names

**Example Template Structure** (research.json excerpt):
```json
{
  "schema_version": "1.3.0",
  "agent_id": "research-agent",
  "agent_version": "4.9.0",
  "template_version": "2.9.0",
  "template_changelog": [...],
  "agent_type": "research",
  "metadata": {
    "name": "Research Agent",
    "description": "Memory-efficient codebase analysis...",
    "tags": ["research", "memory-efficient", ...],
    "category": "research",
    "color": "purple"
  },
  "capabilities": {
    "model": "sonnet",
    "resource_tier": "high",
    "temperature": 0.2,
    "max_tokens": 16384,
    "timeout": 1800
  },
  "knowledge": {
    "domain_expertise": [...],
    "best_practices": [...],
    "constraints": [...]
  },
  "instructions": "Long markdown text...",
  "memory_routing": {...},
  "dependencies": {...}
}
```

### 2. Target Markdown Format with YAML Frontmatter

Based on existing frontmatter validation (`/src/claude_mpm/agents/frontmatter_validator.py`), the target format is:

```markdown
---
name: Research Agent
description: Memory-efficient codebase analysis with MANDATORY ticket attachment
version: 4.9.0
schema_version: 1.3.0
agent_id: research-agent
agent_type: research
model: sonnet
resource_tier: high
temperature: 0.2
max_tokens: 16384
timeout: 1800
tags:
  - research
  - memory-efficient
  - strategic-sampling
category: research
color: purple
capabilities:
  memory_limit: 4096
  cpu_limit: 80
  network_access: true
dependencies:
  python:
    - tree-sitter>=0.21.0
    - pygments>=2.17.0
  system:
    - python3
    - git
skills:
  - systematic-debugging
---

# Research Agent Instructions

[Agent instructions in markdown format]

## Core Responsibilities

...
```

**YAML Frontmatter Mapping:**

| JSON Field | YAML Field | Transformation |
|------------|------------|----------------|
| `agent_version` | `version` | Direct copy |
| `schema_version` | `schema_version` | Direct copy |
| `agent_id` | `agent_id` | Direct copy |
| `agent_type` | `agent_type` | Direct copy |
| `metadata.name` | `name` | Direct copy |
| `metadata.description` | `description` | Direct copy |
| `metadata.tags` | `tags` | Array format |
| `metadata.category` | `category` | Direct copy |
| `metadata.color` | `color` | Direct copy |
| `capabilities.model` | `model` | Direct copy |
| `capabilities.resource_tier` | `resource_tier` | Direct copy |
| `capabilities.temperature` | `temperature` | Direct copy |
| `capabilities.max_tokens` | `max_tokens` | Direct copy |
| `capabilities.timeout` | `timeout` | Direct copy |
| `capabilities.memory_limit` | `capabilities.memory_limit` | Nested |
| `capabilities.cpu_limit` | `capabilities.cpu_limit` | Nested |
| `capabilities.network_access` | `capabilities.network_access` | Nested |
| `dependencies` | `dependencies` | Nested structure |
| `skills` | `skills` | Array format |
| `instructions` | Body content (not frontmatter) | Extract to markdown body |
| `knowledge` | Extended metadata (optional) | Can be preserved as nested YAML |
| `interactions` | Extended metadata (optional) | Can be preserved as nested YAML |
| `memory_routing` | Extended metadata (optional) | Can be preserved as nested YAML |
| `template_version` | `template_version` | Direct copy |
| `template_changelog` | `template_changelog` | Nested structure |

**Fields to EXCLUDE from frontmatter** (too verbose or redundant):
- `testing`: Test cases are for development, not agent runtime
- `knowledge.examples`: Too verbose for frontmatter
- `interactions.triggers`: Complex nested structures

**Recommended Approach**:
- Core metadata goes in frontmatter (name, description, version, model, etc.)
- Instructions go in markdown body
- Optional: Include `knowledge`, `interactions`, `memory_routing` as nested YAML if needed
- Alternative: Store extended metadata in separate JSON sidecar files

### 3. Template Loading Code Analysis

**Primary Loading Module**: `/src/claude_mpm/services/agents/deployment/agent_template_builder.py`

**Key Class**: `AgentTemplateBuilder`

**Existing JSON → Markdown Conversion**:
The `build_agent_markdown()` method (line 147-165) already performs JSON → Markdown conversion:

```python
def build_agent_markdown(
    self,
    agent_name: str,
    template_path: Path,
    base_agent_data: dict,
    source_info: str = "unknown",
) -> str:
    """Build a complete agent markdown file with YAML frontmatter."""
    template_content = template_path.read_text()
    template_data = json.loads(template_content)
    # ... processes JSON and builds markdown ...
```

**Other Loading Points** (found via grep):
- `local_template_manager.py`: `LocalAgentTemplate.from_json()` - loads JSON templates
- `agent_builder.py`: Iterates `*.json` files in templates directory
- `agent_profile_loader.py`: Supports `.json`, `.md`, `.yaml` formats
- `deployed_agent_discovery.py`: Searches for `.json` agent files

**Code Impact**: After migration, these modules will need updates:
1. Change glob patterns from `*.json` to `*.md`
2. Update file extensions in path construction
3. Switch from `json.load()` to frontmatter parsing
4. FrontmatterValidator already handles validation

### 4. Existing Infrastructure to Reuse

**✅ FrontmatterValidator** (`/src/claude_mpm/agents/frontmatter_validator.py`):
- Already validates YAML frontmatter
- Normalizes model names (opus/sonnet/haiku)
- Corrects tool name casing
- Provides `validate_and_correct()` method
- Returns `ValidationResult` with errors/warnings/corrections

**✅ AgentTemplateBuilder** (`/src/claude_mpm/services/agents/deployment/agent_template_builder.py`):
- Has `build_agent_markdown()` method
- Generates YAML frontmatter from JSON
- Handles tool normalization
- Merges base agent instructions

**✅ Agent Schema** (`/src/claude_mpm/schemas/agent_schema.json`):
- Defines all valid fields
- Provides validation rules
- Documents field types and constraints

**⚠️ Missing Components**:
- Batch conversion logic
- Dry-run preview functionality
- Migration logging/reporting
- Rollback mechanism

---

## Recommendations

### Migration Script Design

**Script Location**: `/Users/masa/Projects/claude-mpm/scripts/migrate_json_to_markdown.py`

**Core Functionality**:

```python
#!/usr/bin/env python3
"""
One-time migration script: JSON agent templates → Markdown with YAML frontmatter

Usage:
    # Dry-run (preview changes)
    python scripts/migrate_json_to_markdown.py --dry-run

    # Convert specific agent
    python scripts/migrate_json_to_markdown.py --agent research

    # Convert all agents
    python scripts/migrate_json_to_markdown.py --all

    # Convert with archive (keeps JSON as backup)
    python scripts/migrate_json_to_markdown.py --all --archive

    # Validate migrated files
    python scripts/migrate_json_to_markdown.py --validate-only
"""
```

**Key Features**:

1. **Dry-Run Mode** (`--dry-run`):
   - Preview changes without writing files
   - Show diff of JSON vs. Markdown
   - Report validation errors/warnings
   - Display file paths for each conversion

2. **Single Agent Mode** (`--agent <name>`):
   - Convert one agent template by ID
   - Useful for testing migration logic
   - Validate output immediately

3. **Batch Mode** (`--all`):
   - Convert all JSON templates in directory
   - Process templates in alphabetical order
   - Generate migration summary report

4. **Archive Mode** (`--archive`):
   - Move JSON files to `templates/archive/` directory
   - Preserve original files as backup
   - Alternative to deletion

5. **Validation Mode** (`--validate-only`):
   - Check existing markdown files against schema
   - Report any validation errors
   - Suggest corrections

**Conversion Algorithm**:

```python
def convert_json_to_markdown(json_path: Path) -> Tuple[str, ValidationResult]:
    """
    Convert JSON template to markdown with YAML frontmatter.

    Returns:
        (markdown_content, validation_result)
    """
    # 1. Load JSON template
    with json_path.open() as f:
        template_data = json.load(f)

    # 2. Extract frontmatter fields
    frontmatter = extract_frontmatter_fields(template_data)

    # 3. Validate and correct frontmatter
    validator = FrontmatterValidator()
    validation = validator.validate_and_correct(frontmatter)

    # 4. Extract instructions (markdown body)
    instructions = template_data.get("instructions", "")

    # 5. Build markdown content
    markdown = build_markdown(validation.corrected_frontmatter, instructions)

    return markdown, validation


def extract_frontmatter_fields(template_data: dict) -> dict:
    """Extract fields suitable for YAML frontmatter."""
    frontmatter = {
        # Core fields (required)
        "name": template_data["metadata"]["name"],
        "description": template_data["metadata"]["description"],
        "version": template_data["agent_version"],
        "schema_version": template_data["schema_version"],
        "agent_id": template_data["agent_id"],
        "agent_type": template_data["agent_type"],
        "model": template_data["capabilities"]["model"],
        "resource_tier": template_data["capabilities"]["resource_tier"],

        # Metadata fields
        "tags": template_data["metadata"].get("tags", []),
        "category": template_data["metadata"].get("category"),
        "color": template_data["metadata"].get("color"),

        # Capabilities
        "temperature": template_data["capabilities"].get("temperature"),
        "max_tokens": template_data["capabilities"].get("max_tokens"),
        "timeout": template_data["capabilities"].get("timeout"),

        # Nested capabilities
        "capabilities": {
            "memory_limit": template_data["capabilities"].get("memory_limit"),
            "cpu_limit": template_data["capabilities"].get("cpu_limit"),
            "network_access": template_data["capabilities"].get("network_access"),
        },

        # Optional fields
        "dependencies": template_data.get("dependencies"),
        "skills": template_data.get("skills"),
        "template_version": template_data.get("template_version"),
        "template_changelog": template_data.get("template_changelog"),
    }

    # Remove None values
    return {k: v for k, v in frontmatter.items() if v is not None}


def build_markdown(frontmatter: dict, instructions: str) -> str:
    """Build final markdown with YAML frontmatter."""
    yaml_content = yaml.dump(frontmatter,
                              default_flow_style=False,
                              allow_unicode=True,
                              sort_keys=False)

    return f"---\n{yaml_content}---\n\n{instructions}"
```

**Migration Report Structure**:

```
JSON to Markdown Agent Template Migration Report
================================================
Date: 2025-11-29 14:30:00
Templates Directory: /Users/masa/Projects/claude-mpm/src/claude_mpm/agents/templates

Summary:
--------
Total templates found:      40
Successfully converted:     38
Validation errors:           2
Validation warnings:         5
Archived JSON files:        40

Conversions:
-----------
✅ research.json → research.md (validated, no warnings)
✅ engineer.json → engineer.md (validated, 1 warning: deprecated field 'version')
✅ qa.json → qa.md (validated, no warnings)
❌ broken.json → FAILED (JSON parse error: line 45)
⚠️  security.json → security.md (validated, 2 warnings: missing 'category', unknown field 'custom_field')

Validation Warnings:
-------------------
1. engineer.md: Deprecated field 'version' (use 'agent_version')
2. security.md: Missing recommended field 'category'
3. security.md: Unknown field 'custom_field' (will be preserved)

Validation Errors:
-----------------
1. broken.json: Failed to parse JSON (line 45: unexpected token)

Archive:
--------
Original JSON files moved to: templates/archive/

Next Steps:
----------
1. Review validation warnings
2. Fix validation errors in failed conversions
3. Update code references from *.json to *.md
4. Run test suite to verify agent loading
5. Deploy migrated agents with: claude-mpm agents deploy --all --force
```

**CLI Options**:

```python
import argparse

parser = argparse.ArgumentParser(
    description="Migrate JSON agent templates to Markdown with YAML frontmatter"
)

parser.add_argument(
    "--dry-run",
    action="store_true",
    help="Preview changes without writing files"
)

parser.add_argument(
    "--agent",
    type=str,
    help="Convert specific agent by ID (e.g., 'research')"
)

parser.add_argument(
    "--all",
    action="store_true",
    help="Convert all JSON templates"
)

parser.add_argument(
    "--archive",
    action="store_true",
    help="Archive JSON files instead of deleting them"
)

parser.add_argument(
    "--validate-only",
    action="store_true",
    help="Validate existing markdown files without conversion"
)

parser.add_argument(
    "--output-dir",
    type=Path,
    default=None,
    help="Output directory for migrated files (default: same as input)"
)

parser.add_argument(
    "--verbose",
    "-v",
    action="store_true",
    help="Verbose output with detailed logging"
)
```

**Error Handling**:

```python
class MigrationError(Exception):
    """Base exception for migration errors."""
    pass

class JSONParseError(MigrationError):
    """JSON parsing failed."""
    pass

class ValidationError(MigrationError):
    """Frontmatter validation failed."""
    pass

class FileWriteError(MigrationError):
    """Failed to write markdown file."""
    pass

# Error recovery strategy
def safe_convert(json_path: Path, archive_mode: bool) -> dict:
    """Convert with error handling and rollback."""
    try:
        markdown, validation = convert_json_to_markdown(json_path)

        # Check for critical validation errors
        if validation.errors:
            raise ValidationError(f"Validation failed: {validation.errors}")

        # Write markdown file
        output_path = json_path.with_suffix(".md")
        output_path.write_text(markdown)

        # Archive or delete JSON
        if archive_mode:
            archive_path = json_path.parent / "archive" / json_path.name
            archive_path.parent.mkdir(exist_ok=True)
            json_path.rename(archive_path)
        else:
            json_path.unlink()

        return {
            "status": "success",
            "json_path": str(json_path),
            "md_path": str(output_path),
            "warnings": validation.warnings,
        }

    except JSONParseError as e:
        return {
            "status": "error",
            "json_path": str(json_path),
            "error": f"JSON parse error: {e}",
        }

    except ValidationError as e:
        # Rollback: delete generated markdown if validation failed
        if output_path.exists():
            output_path.unlink()

        return {
            "status": "error",
            "json_path": str(json_path),
            "error": f"Validation error: {e}",
        }

    except Exception as e:
        return {
            "status": "error",
            "json_path": str(json_path),
            "error": f"Unexpected error: {e}",
        }
```

### Testing Strategy

**Unit Tests** (`/tests/test_json_migration_script.py`):

```python
import pytest
from scripts.migrate_json_to_markdown import (
    convert_json_to_markdown,
    extract_frontmatter_fields,
    build_markdown,
)

def test_extract_frontmatter_minimal():
    """Test extraction with minimal required fields."""
    template_data = {
        "schema_version": "1.3.0",
        "agent_id": "test-agent",
        "agent_version": "1.0.0",
        "agent_type": "engineer",
        "metadata": {
            "name": "Test Agent",
            "description": "Test description",
            "tags": ["test"],
        },
        "capabilities": {
            "model": "sonnet",
            "resource_tier": "standard",
        },
        "instructions": "Test instructions",
    }

    frontmatter = extract_frontmatter_fields(template_data)

    assert frontmatter["name"] == "Test Agent"
    assert frontmatter["agent_id"] == "test-agent"
    assert frontmatter["model"] == "sonnet"

def test_build_markdown_valid_yaml():
    """Test markdown generation with valid YAML."""
    frontmatter = {
        "name": "Test Agent",
        "description": "Test description",
        "version": "1.0.0",
        "model": "sonnet",
    }
    instructions = "# Test Instructions\n\nTest content"

    markdown = build_markdown(frontmatter, instructions)

    assert markdown.startswith("---\n")
    assert "name: Test Agent" in markdown
    assert "# Test Instructions" in markdown

def test_convert_research_json():
    """Test conversion of research.json template."""
    json_path = Path("src/claude_mpm/agents/templates/research.json")
    markdown, validation = convert_json_to_markdown(json_path)

    assert validation.is_valid
    assert "# Research Agent" in markdown or "Research Agent" in markdown
    assert "---" in markdown  # YAML frontmatter delimiters
```

**Integration Tests**:

```python
def test_migration_dry_run(tmp_path):
    """Test dry-run mode doesn't modify files."""
    # Setup: copy test JSON to temp directory
    test_json = tmp_path / "test_agent.json"
    test_json.write_text(json.dumps({...}))

    # Run migration in dry-run mode
    result = run_migration(tmp_path, dry_run=True)

    # Verify: JSON still exists, no .md created
    assert test_json.exists()
    assert not (tmp_path / "test_agent.md").exists()
    assert result["preview_count"] == 1

def test_migration_with_archive(tmp_path):
    """Test archive mode preserves JSON files."""
    test_json = tmp_path / "test_agent.json"
    test_json.write_text(json.dumps({...}))

    run_migration(tmp_path, archive=True)

    # Verify: markdown created, JSON archived
    assert (tmp_path / "test_agent.md").exists()
    assert (tmp_path / "archive" / "test_agent.json").exists()
    assert not test_json.exists()
```

**Sample Test Templates**:
Create `/tests/fixtures/agent_templates/` with:
- `minimal_valid.json`: Minimum required fields
- `full_featured.json`: All optional fields included
- `invalid_schema.json`: Missing required fields
- `invalid_json.json`: Malformed JSON syntax

### Code Integration Points

**Files Requiring Updates After Migration**:

1. **agent_builder.py** (line 288):
   ```python
   # BEFORE
   for template_file in self.templates_dir.glob("*.json"):

   # AFTER
   for template_file in self.templates_dir.glob("*.md"):
   ```

2. **local_template_manager.py** (line 196):
   ```python
   # BEFORE
   for template_file in directory.glob("*.json"):
       data = json.load(f)
       template = LocalAgentTemplate.from_json(data)

   # AFTER
   for template_file in directory.glob("*.md"):
       frontmatter, content = parse_markdown_with_frontmatter(f.read())
       template = LocalAgentTemplate.from_frontmatter(frontmatter, content)
   ```

3. **agent_profile_loader.py** (line 318):
   ```python
   # Already supports .md format, just change search priority
   file_patterns = ["*.md", "*.yaml", "*.yml"]  # Remove "*.json"
   ```

4. **base_agent_locator.py** (lines 56-96):
   ```python
   # Update base_agent.json references to base_agent.md
   # Multiple hardcoded paths need updating
   ```

**Suggested Approach**: Create a follow-up ticket (1M-394?) for code integration updates after successful migration.

---

## Implementation Checklist

### Phase 1: Script Development
- [ ] Create `/scripts/migrate_json_to_markdown.py`
- [ ] Implement `extract_frontmatter_fields()` function
- [ ] Implement `build_markdown()` function
- [ ] Implement `convert_json_to_markdown()` function
- [ ] Add CLI argument parsing (argparse)
- [ ] Implement dry-run mode
- [ ] Implement single-agent mode
- [ ] Implement batch conversion mode
- [ ] Implement archive mode
- [ ] Add error handling and rollback logic

### Phase 2: Validation Integration
- [ ] Import and use `FrontmatterValidator`
- [ ] Validate all generated markdown files
- [ ] Report validation errors/warnings
- [ ] Implement validation-only mode

### Phase 3: Reporting
- [ ] Generate migration summary report
- [ ] Log each conversion (success/failure/warnings)
- [ ] Create detailed error messages
- [ ] Export report to file (optional)

### Phase 4: Testing
- [ ] Create test fixtures (minimal, full, invalid JSON)
- [ ] Write unit tests for extraction functions
- [ ] Write unit tests for markdown building
- [ ] Write integration tests for dry-run
- [ ] Write integration tests for archive mode
- [ ] Test with actual research.json template
- [ ] Test with all 40 templates

### Phase 5: Documentation
- [ ] Add usage examples to script docstring
- [ ] Document CLI options
- [ ] Create migration guide in docs/
- [ ] Document rollback procedure

### Phase 6: Execution
- [ ] Run migration in dry-run mode
- [ ] Review preview and validate output
- [ ] Run migration with --archive flag
- [ ] Verify all 40 templates converted
- [ ] Check for validation errors/warnings
- [ ] Run test suite with migrated templates

### Phase 7: Code Integration (Follow-up Ticket)
- [ ] Update glob patterns (*.json → *.md)
- [ ] Update file path construction
- [ ] Add frontmatter parsing logic
- [ ] Update base_agent references
- [ ] Run full test suite
- [ ] Deploy agents with new format

---

## YAML Frontmatter Structure Reference

**Core Fields** (always included):
```yaml
name: string
description: string
version: semver
schema_version: semver
agent_id: kebab-case-id
agent_type: enum
model: opus|sonnet|haiku
resource_tier: enum
```

**Metadata Fields** (recommended):
```yaml
tags:
  - tag1
  - tag2
category: enum
color: enum
```

**Capabilities** (optional, nested):
```yaml
temperature: float
max_tokens: integer
timeout: integer
capabilities:
  memory_limit: integer
  cpu_limit: integer
  network_access: boolean
```

**Extended Metadata** (optional, preserves JSON structure):
```yaml
dependencies:
  python:
    - package>=version
  system:
    - command
skills:
  - skill-name
template_version: semver
template_changelog:
  - version: semver
    date: YYYY-MM-DD
    description: string
```

**Not Included in Frontmatter** (too verbose):
- `knowledge`: Use separate knowledge base files
- `interactions`: Use separate interaction specs
- `testing`: Keep in test files
- `memory_routing`: Runtime configuration

---

## References

### Files Analyzed
- `/Users/masa/Projects/claude-mpm/src/claude_mpm/agents/templates/research.json`
- `/Users/masa/Projects/claude-mpm/src/claude_mpm/agents/templates/engineer.json`
- `/Users/masa/Projects/claude-mpm/src/claude_mpm/schemas/agent_schema.json`
- `/Users/masa/Projects/claude-mpm/src/claude_mpm/agents/frontmatter_validator.py`
- `/Users/masa/Projects/claude-mpm/src/claude_mpm/services/agents/deployment/agent_template_builder.py`
- `/Users/masa/Projects/claude-mpm/src/claude_mpm/services/agents/local_template_manager.py`

### Ticket References
- **1M-393**: Create one-time migration script for JSON templates (THIS TICKET)
- **1M-382**: Parent issue for JSON → Markdown migration
- **Suggested 1M-394**: Update code to use markdown templates (follow-up)

### Related Documentation
- Agent Schema Documentation: `/src/claude_mpm/schemas/agent_schema.json`
- FrontmatterValidator: `/src/claude_mpm/agents/frontmatter_validator.py`
- Existing Scripts: `/scripts/*.py` (44+ existing migration/management scripts)

---

## Memory Usage Statistics

**Files Read**: 3 (research.json, engineer.json, agent_schema.json, frontmatter_validator.py excerpt)
**Total Size**: ~95KB
**Search Operations**: 3 (Glob for templates, Grep for loading code, Grep for frontmatter)
**Memory Efficiency**: Used search tools to avoid loading all 40 templates into memory

---

**Research completed**: 2025-11-29
**Ticket**: 1M-393
**Next Action**: Implement migration script in `/scripts/migrate_json_to_markdown.py`
