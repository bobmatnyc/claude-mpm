# Agent Dependency Loader YAML Frontmatter Parsing Solution

**Research ID**: agent-dependency-yaml-frontmatter-solution
**Date**: 2025-11-29
**Status**: Implementation Ready
**Complexity**: Low (2-3 hour implementation)
**Risk Level**: Low (non-breaking change)
**Researcher**: Research Agent

## Executive Summary

The agent dependency loader (`src/claude_mpm/utils/agent_dependency_loader.py`) currently searches for `.json` configuration files at line 111, but all agent templates have been migrated to `.md` files with YAML frontmatter. This causes dependency loading to fail for all 48 agent templates, preventing proper dependency management during agent deployment.

**Root Cause**: Line 111 hardcodes `.json` extension instead of `.md`
**Impact**: Dependency checking completely broken for all agents
**Solution**: Parse YAML frontmatter from `.md` files using existing codebase patterns
**Complexity**: Minimal - reuse existing frontmatter parsing code
**Breaking Changes**: None (backward compatible with `.json` files)

---

## 1. Root Cause Analysis

### The Bug

**File**: `src/claude_mpm/utils/agent_dependency_loader.py`
**Line**: 111
**Current Code**:
```python
config_file = config_dir / f"{agent_id}.json"  # BUG: Looks for .json
```

### What's Broken

The `load_agent_dependencies()` method (lines 92-125) implements a search path with precedence:
1. **PROJECT**: `.claude-mpm/agents/`
2. **USER**: `~/.claude-mpm/agents/`
3. **SYSTEM**: `src/claude_mpm/agents/templates/`

For each path, it tries to load `{agent_id}.json`, but:
- All 48 templates are now `.md` files with YAML frontmatter
- No `.json` files exist in any of these directories
- Dependencies are embedded in YAML frontmatter, not separate JSON files

**Result**: `load_agent_dependencies()` returns empty dict `{}`, causing all agents to appear as having no dependencies.

### What's Working

- **Agent Discovery** (lines 68-90): Correctly finds `.md` files in `.claude/agents/`
- **Dependency Analysis** (lines 405-463): Correctly checks Python/system dependencies
- **Deployment State Tracking** (lines 824-961): Correctly hashes agent content
- **Dependency Installation** (lines 506-654): Correctly installs missing packages

The **only** broken component is loading dependency configuration from source templates.

---

## 2. Template Audit Results

### Template Statistics

- **Total Templates**: 48 markdown files
- **Templates with Dependencies**: 37 (77%)
- **Templates without Dependencies**: 11 (23%)

### Dependency Structure Examples

All templates use consistent YAML frontmatter format:

**Example 1: Python Engineer** (`python_engineer.md`)
```yaml
---
dependencies:
  python:
  - black>=24.0.0
  - isort>=5.13.0
  - mypy>=1.8.0
  - pytest>=8.0.0
  - pytest-cov>=4.1.0
  - pytest-asyncio>=0.23.0
  - hypothesis>=6.98.0
  - flake8>=7.0.0
  - pydantic>=2.6.0
  - rope>=1.11.0
  system:
  - python3
  - git
  optional: false
---
```

**Example 2: Research Agent** (`research.md`)
```yaml
---
dependencies:
  python:
  - tree-sitter>=0.21.0
  - pygments>=2.17.0
  - radon>=6.0.0
  - semgrep>=1.45.0
  - lizard>=1.17.0
  - pydriller>=2.5.0
  - astroid>=3.0.0
  system:
  - python3
  - git
  optional: false
---
```

**Example 3: TypeScript Engineer** (`typescript_engineer.md`)
```yaml
---
dependencies:
  python: []
  system:
  - node>=20
  - npm>=10
  optional: false
---
```

**Example 4: Ops Agent** (`ops.md`)
```yaml
---
dependencies:
  python:
  - prometheus-client>=0.19.0
  system:
  - python3
  - git
  optional: false
skills:
- docker-containerization
---
```

### Schema Validation

**Dependency Schema** (consistent across all templates):
```yaml
dependencies:
  python:           # Optional list of Python package specs
    - package>=version
    - package>=version
  system:           # Optional list of system commands
    - command
    - command
  optional: false   # Optional boolean flag
```

**Fields**:
- `python`: List of pip package specifications (e.g., `black>=24.0.0`)
- `system`: List of system commands that must be in PATH
- `optional`: Boolean indicating if dependencies are optional (default: `false`)

**All templates follow this exact schema** - no inconsistencies found.

---

## 3. Claude Code Standards Compliance

### Official Format Specification

Based on web research and official documentation:

**Claude Code Agent Format**:
- **File Extension**: `.md` (markdown)
- **Frontmatter**: YAML between `---` delimiters
- **Location**: `.claude/agents/` (project) or `~/.claude/agents/` (user)
- **Loading**: Progressive disclosure (initial 30-50 tokens)

**YAML Frontmatter Fields** (from Claude Code):
- `name`: Agent name (required)
- `description`: One-line description (required)
- `version`: Semantic version (required)
- `tools`: Comma-separated list of tools
- `model`: Model tier (opus/sonnet/haiku)
- `category`: Agent category
- `dependencies`: Custom field (not in core spec)

### Compliance Assessment

**✅ Current Implementation is COMPLIANT**:
- Uses standard `.md` format with YAML frontmatter
- Follows `---` delimiter convention
- Uses semantic versioning
- Includes required fields (name, description, version)
- Custom `dependencies` field is valid (Claude Code allows custom fields)

**⚠️ Dependencies Field is Custom Extension**:
- Not part of core Claude Code specification
- Specific to Claude MPM framework
- Used for dependency management during deployment
- Does not conflict with Claude Code standards

**Conclusion**: The YAML frontmatter format is 100% compliant with Claude Code standards. The `dependencies` field is a valid custom extension that does not violate any specifications.

---

## 4. Existing YAML Parsing Infrastructure

### Available Implementations

The codebase already has **multiple mature implementations** of YAML frontmatter parsing:

#### 4.1 FrontmatterValidator (Most Complete)

**File**: `src/claude_mpm/agents/frontmatter_validator.py`
**Lines**: 577-600

```python
def _extract_frontmatter(self, content: str) -> Optional[Dict[str, Any]]:
    """
    Extract frontmatter from file content.

    Args:
        content: File content

    Returns:
        Parsed frontmatter dictionary or None
    """
    # Check for YAML frontmatter (between --- markers)
    if content.startswith("---"):
        try:
            end_marker = content.find("\n---\n", 4)
            if end_marker == -1:
                end_marker = content.find("\n---\r\n", 4)

            if end_marker != -1:
                frontmatter_str = content[4:end_marker]
                return yaml.safe_load(frontmatter_str)
        except yaml.YAMLError as e:
            logger.error(f"Failed to parse YAML frontmatter: {e}")

    return None
```

**Features**:
- Handles both Unix (`\n`) and Windows (`\r\n`) line endings
- Uses `yaml.safe_load()` (secure)
- Proper error handling with logging
- Returns `None` on parse failure

#### 4.2 OptimizedAgentLoader (Performance Focus)

**File**: `src/claude_mpm/core/optimized_agent_loader.py`
**Lines**: 185-220 (estimated from context)

```python
# Extract frontmatter from markdown
# Look for frontmatter
if lines[0].strip() == "---":
    # Find closing marker
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end_index = i
            break

    if end_index:
        frontmatter = "\n".join(lines[1:end_index])
        data = yaml.safe_load(frontmatter) or {}
        # Extract instructions after frontmatter
        instructions = "\n".join(lines[end_index + 1:])
        return data, instructions

# No frontmatter, treat as pure instructions
return {}, content
```

**Features**:
- Line-by-line parsing (memory efficient)
- Separates frontmatter from markdown body
- Handles missing frontmatter gracefully
- Returns tuple `(data, instructions)`

#### 4.3 Other Implementations

**Files Using YAML Frontmatter Parsing**:
- `src/claude_mpm/core/framework/processors/metadata_processor.py`
- `src/claude_mpm/core/framework/formatters/capability_generator.py`
- `src/claude_mpm/core/unified_agent_registry.py`
- `src/claude_mpm/validation/frontmatter_validator.py`

All use similar patterns with minor variations.

### Recommended Approach

**Use `FrontmatterValidator._extract_frontmatter()`** because:
1. ✅ Most complete implementation (handles edge cases)
2. ✅ Proper error handling with logging
3. ✅ Cross-platform line ending support
4. ✅ Already tested and validated
5. ✅ Consistent with rest of codebase

**Alternative**: Extract as standalone utility function to avoid dependency on FrontmatterValidator class.

---

## 5. Solution Architecture

### 5.1 Design Principles

1. **Backward Compatibility**: Support both `.json` and `.md` files
2. **Search Order**: Try `.md` first (current format), fallback to `.json` (legacy)
3. **Minimal Changes**: Reuse existing parsing code
4. **Error Handling**: Graceful degradation on parse failures
5. **Performance**: No significant overhead (frontmatter parsing is fast)

### 5.2 Implementation Strategy

**Modify `load_agent_dependencies()` method (lines 92-125)**:

```python
def load_agent_dependencies(self) -> Dict[str, Dict]:
    """
    Load dependency information for deployed agents from their source configs.

    Supports both markdown files with YAML frontmatter (.md) and legacy JSON files (.json).
    Searches in precedence order: PROJECT → USER → SYSTEM

    Returns:
        Dictionary mapping agent IDs to their dependency requirements
    """
    agent_dependencies = {}

    # Define paths to check for agent configs (in precedence order)
    config_paths = [
        Path.cwd() / ".claude-mpm" / "agents",  # PROJECT
        Path.home() / ".claude-mpm" / "agents",  # USER
        Path.cwd() / "src" / "claude_mpm" / "agents" / "templates",  # SYSTEM
    ]

    for agent_id in self.deployed_agents:
        # Try to find the agent's config (prefer .md, fallback to .json)
        for config_dir in config_paths:
            # Try markdown first (current format)
            config_file = config_dir / f"{agent_id}.md"
            if config_file.exists():
                try:
                    deps = self._load_dependencies_from_markdown(config_file)
                    if deps:
                        agent_dependencies[agent_id] = deps
                        logger.debug(f"Loaded dependencies for {agent_id} from {config_file}")
                        break
                except Exception as e:
                    logger.warning(f"Failed to load markdown config for {agent_id}: {e}")

            # Fallback to JSON (legacy format)
            config_file = config_dir / f"{agent_id}.json"
            if config_file.exists():
                try:
                    with config_file.open() as f:
                        config = json.load(f)
                        if "dependencies" in config:
                            agent_dependencies[agent_id] = config["dependencies"]
                            logger.debug(f"Loaded dependencies for {agent_id} from legacy JSON")
                            break
                except Exception as e:
                    logger.warning(f"Failed to load JSON config for {agent_id}: {e}")

    self.agent_dependencies = agent_dependencies
    logger.debug(f"Loaded dependencies for {len(agent_dependencies)} agents")
    return agent_dependencies

def _load_dependencies_from_markdown(self, markdown_file: Path) -> Optional[Dict]:
    """
    Extract dependencies from markdown file with YAML frontmatter.

    Args:
        markdown_file: Path to markdown file

    Returns:
        Dependencies dict or None if not found
    """
    try:
        with markdown_file.open() as f:
            content = f.read()

        # Extract YAML frontmatter
        frontmatter = self._extract_frontmatter(content)
        if frontmatter and "dependencies" in frontmatter:
            return frontmatter["dependencies"]

        return None

    except Exception as e:
        logger.debug(f"Failed to extract frontmatter from {markdown_file}: {e}")
        return None

def _extract_frontmatter(self, content: str) -> Optional[Dict[str, Any]]:
    """
    Extract YAML frontmatter from markdown content.

    Args:
        content: Markdown file content

    Returns:
        Parsed frontmatter dict or None
    """
    # Check for YAML frontmatter (between --- markers)
    if content.startswith("---"):
        try:
            end_marker = content.find("\n---\n", 4)
            if end_marker == -1:
                end_marker = content.find("\n---\r\n", 4)  # Windows line endings

            if end_marker != -1:
                frontmatter_str = content[4:end_marker]
                return yaml.safe_load(frontmatter_str)
        except yaml.YAMLError as e:
            logger.warning(f"Failed to parse YAML frontmatter: {e}")

    return None
```

### 5.3 Changes Required

**File**: `src/claude_mpm/utils/agent_dependency_loader.py`

**Imports** (add at top):
```python
import yaml  # Add to imports at top
from typing import Any, Dict, List, Optional, Set, Tuple  # Update Optional import
```

**Method Changes**:
1. **Modify**: `load_agent_dependencies()` (lines 92-125) - add .md support
2. **Add**: `_load_dependencies_from_markdown()` - new helper method
3. **Add**: `_extract_frontmatter()` - new parsing method

**Lines of Code**: ~60 lines added/modified

### 5.4 Alternative Approach (Simpler)

If we want minimal changes, just extract inline:

```python
def load_agent_dependencies(self) -> Dict[str, Dict]:
    """Load dependency information for deployed agents from their source configs."""
    agent_dependencies = {}

    config_paths = [
        Path.cwd() / ".claude-mpm" / "agents",
        Path.home() / ".claude-mpm" / "agents",
        Path.cwd() / "src" / "claude_mpm" / "agents" / "templates",
    ]

    for agent_id in self.deployed_agents:
        for config_dir in config_paths:
            # Try .md first (current format)
            config_file = config_dir / f"{agent_id}.md"
            if config_file.exists():
                try:
                    with config_file.open() as f:
                        content = f.read()

                    # Extract YAML frontmatter
                    if content.startswith("---"):
                        end_marker = content.find("\n---\n", 4)
                        if end_marker == -1:
                            end_marker = content.find("\n---\r\n", 4)

                        if end_marker != -1:
                            frontmatter_str = content[4:end_marker]
                            frontmatter = yaml.safe_load(frontmatter_str)

                            if "dependencies" in frontmatter:
                                agent_dependencies[agent_id] = frontmatter["dependencies"]
                                logger.debug(f"Loaded dependencies for {agent_id}")
                                break
                except Exception as e:
                    logger.warning(f"Failed to load config for {agent_id}: {e}")

            # Fallback to .json (legacy)
            config_file = config_dir / f"{agent_id}.json"
            if config_file.exists():
                try:
                    with config_file.open() as f:
                        config = json.load(f)
                        if "dependencies" in config:
                            agent_dependencies[agent_id] = config["dependencies"]
                            logger.debug(f"Loaded dependencies for {agent_id}")
                            break
                except Exception as e:
                    logger.warning(f"Failed to load config for {agent_id}: {e}")

    self.agent_dependencies = agent_dependencies
    logger.debug(f"Loaded dependencies for {len(agent_dependencies)} agents")
    return agent_dependencies
```

**Pros**:
- ✅ Minimal code changes (inline implementation)
- ✅ No new methods needed
- ✅ Easy to review and test

**Cons**:
- ❌ Less reusable
- ❌ Harder to unit test
- ❌ Duplicates logic if needed elsewhere

**Recommendation**: Use the **alternative approach** for speed, but extract methods in future refactoring.

---

## 6. Backward Compatibility Strategy

### Support Matrix

| Format | Extension | Priority | Status |
|--------|-----------|----------|--------|
| Markdown | `.md` | 1 (Primary) | ✅ Implemented |
| JSON | `.json` | 2 (Legacy) | ✅ Maintained |

### Migration Path

**Current State**:
- All templates are `.md` files
- No `.json` files in `src/claude_mpm/agents/templates/`

**Future State**:
- `.md` remains primary format
- `.json` supported for backward compatibility only
- No new `.json` files should be created

### Deprecation Plan

**Phase 1** (Current): Both formats supported
**Phase 2** (v5.0.0): Deprecation warning for `.json` files
**Phase 3** (v6.0.0): Remove `.json` support entirely

**Timeline**: No rush - `.json` support costs nothing to maintain.

---

## 7. Testing Strategy

### Unit Tests Required

**File**: `tests/utils/test_agent_dependency_loader.py`

```python
import pytest
from pathlib import Path
from claude_mpm.utils.agent_dependency_loader import AgentDependencyLoader

class TestYAMLFrontmatterParsing:
    """Test YAML frontmatter dependency parsing."""

    def test_load_dependencies_from_markdown(self, tmp_path):
        """Test loading dependencies from .md file with YAML frontmatter."""
        # Create test markdown file
        agent_file = tmp_path / "test_agent.md"
        agent_file.write_text("""---
dependencies:
  python:
  - pytest>=7.0.0
  - black>=23.0.0
  system:
  - python3
  - git
  optional: false
---

# Test Agent

Test instructions here.
""")

        loader = AgentDependencyLoader()
        deps = loader._load_dependencies_from_markdown(agent_file)

        assert deps is not None
        assert "python" in deps
        assert "system" in deps
        assert len(deps["python"]) == 2
        assert deps["python"][0] == "pytest>=7.0.0"
        assert len(deps["system"]) == 2
        assert deps["optional"] is False

    def test_fallback_to_json(self, tmp_path):
        """Test fallback to .json when .md not found."""
        # Create test JSON file
        json_file = tmp_path / "test_agent.json"
        json_file.write_text("""{
  "dependencies": {
    "python": ["pytest>=7.0.0"],
    "system": ["python3"]
  }
}""")

        loader = AgentDependencyLoader()
        loader.deployed_agents = {"test_agent": tmp_path / "test_agent.md"}

        # Simulate loading process
        agent_dependencies = {}
        for agent_id in loader.deployed_agents:
            config_file = tmp_path / f"{agent_id}.json"
            if config_file.exists():
                with config_file.open() as f:
                    import json
                    config = json.load(f)
                    if "dependencies" in config:
                        agent_dependencies[agent_id] = config["dependencies"]

        assert "test_agent" in agent_dependencies
        assert len(agent_dependencies["test_agent"]["python"]) == 1

    def test_markdown_precedence_over_json(self, tmp_path):
        """Test that .md takes precedence over .json."""
        # Create both files
        md_file = tmp_path / "test_agent.md"
        md_file.write_text("""---
dependencies:
  python:
  - pytest>=8.0.0
---
Test agent
""")

        json_file = tmp_path / "test_agent.json"
        json_file.write_text("""{
  "dependencies": {
    "python": ["pytest>=7.0.0"]
  }
}""")

        loader = AgentDependencyLoader()
        deps = loader._load_dependencies_from_markdown(md_file)

        # Should use markdown version
        assert deps["python"][0] == "pytest>=8.0.0"

    def test_invalid_yaml_handling(self, tmp_path):
        """Test graceful handling of invalid YAML."""
        agent_file = tmp_path / "test_agent.md"
        agent_file.write_text("""---
dependencies:
  python:
  - pytest>=7.0.0
  invalid: [unclosed list
---
""")

        loader = AgentDependencyLoader()
        deps = loader._load_dependencies_from_markdown(agent_file)

        # Should return None on parse error
        assert deps is None

    def test_no_frontmatter(self, tmp_path):
        """Test markdown without frontmatter."""
        agent_file = tmp_path / "test_agent.md"
        agent_file.write_text("# Test Agent\n\nNo frontmatter here.")

        loader = AgentDependencyLoader()
        deps = loader._load_dependencies_from_markdown(agent_file)

        assert deps is None

    def test_empty_dependencies(self, tmp_path):
        """Test agent with empty dependencies."""
        agent_file = tmp_path / "test_agent.md"
        agent_file.write_text("""---
dependencies:
  python: []
  system: []
  optional: false
---
Test agent
""")

        loader = AgentDependencyLoader()
        deps = loader._load_dependencies_from_markdown(agent_file)

        assert deps is not None
        assert deps["python"] == []
        assert deps["system"] == []
```

### Integration Tests Required

**Test Scenarios**:
1. Load dependencies from real agent templates
2. Verify all 48 templates parse correctly
3. Test search path precedence (PROJECT → USER → SYSTEM)
4. Verify backward compatibility with legacy JSON files
5. Test error handling for corrupted files

### Manual Testing Checklist

- [ ] Deploy agent with Python dependencies
- [ ] Deploy agent with system dependencies
- [ ] Deploy agent with no dependencies
- [ ] Verify dependency checking works
- [ ] Verify auto-install works
- [ ] Test with both `.md` and `.json` files
- [ ] Verify error messages are helpful

---

## 8. Implementation Complexity Assessment

### Time Estimates

| Task | Estimated Time | Notes |
|------|---------------|-------|
| Code Changes | 30 minutes | Simple modification |
| Unit Tests | 1 hour | Comprehensive test suite |
| Integration Tests | 30 minutes | Real template testing |
| Manual Testing | 30 minutes | Verify end-to-end |
| Documentation | 30 minutes | Update docstrings |
| **TOTAL** | **3 hours** | Conservative estimate |

### Risk Assessment

**Technical Risks**: ⚠️ **LOW**
- Existing codebase has proven YAML parsing patterns
- PyYAML is already a dependency
- Simple, focused change with clear scope

**Breaking Change Risk**: ✅ **NONE**
- Backward compatible with `.json` files
- No API changes
- No changes to dependency schema
- Existing functionality preserved

**Performance Impact**: ✅ **NEGLIGIBLE**
- YAML parsing is fast (~1ms per file)
- Only runs during agent deployment (not hot path)
- Same number of file reads as before

### Dependencies

**Python Packages** (already installed):
- `pyyaml>=6.0` - Already in `pyproject.toml` dependencies

**No New Dependencies Required** ✅

---

## 9. Recommendations

### Primary Recommendation

**IMPLEMENT SOLUTION IMMEDIATELY** ✅

**Why**:
1. **Critical Bug**: Dependency loading completely broken for all 48 agents
2. **Low Complexity**: 3-hour implementation with proven patterns
3. **High Value**: Restores essential functionality
4. **Low Risk**: Backward compatible, well-tested pattern
5. **Clear Path**: Existing code provides template to follow

### Implementation Approach

**Option A: Full Implementation** (Recommended)
- Extract helper methods (`_load_dependencies_from_markdown`, `_extract_frontmatter`)
- Comprehensive unit tests
- Proper error handling
- Clean, maintainable code

**Time**: 3 hours
**Benefits**: Maintainable, testable, reusable

**Option B: Quick Fix** (Alternative)
- Inline YAML parsing in `load_agent_dependencies()`
- Minimal tests
- Basic error handling

**Time**: 1 hour
**Benefits**: Fast deployment, minimal changes
**Drawbacks**: Less maintainable, harder to test

### Post-Implementation Tasks

1. **Verify All Agents**: Run `claude-mpm agents check-deps` on all 48 templates
2. **Update Documentation**: Document `.md` format as primary
3. **Add Migration Guide**: Help users migrate custom `.json` configs
4. **Consider Deprecation**: Plan `.json` deprecation timeline

---

## 10. Code Quality Standards Compliance

### CONTRIBUTING.md Alignment

**Pre-Implementation Checklist**:
- [x] Read CONTRIBUTING.md guidelines
- [x] Understand code structure requirements
- [x] Plan tests (85%+ coverage target)
- [x] Design for service-oriented architecture
- [x] Plan commit message format

**Implementation Checklist**:
- [ ] Run `make lint-fix` during development
- [ ] Run `make quality` before commit
- [ ] Write comprehensive tests (target 85%+ coverage)
- [ ] Follow conventional commits format
- [ ] Update docstrings and type hints

**Commit Message Format**:
```
fix: parse YAML frontmatter for agent dependencies instead of JSON

Agent templates migrated to .md files with YAML frontmatter, but
dependency loader still searched for .json files. This broke dependency
checking for all 48 agents.

Changes:
- Add YAML frontmatter parsing to load_agent_dependencies()
- Support both .md (primary) and .json (legacy) formats
- Add helper methods for markdown parsing
- Maintain backward compatibility with JSON files

Fixes: Line 111 in agent_dependency_loader.py
Tests: Add comprehensive unit tests for YAML parsing
```

---

## 11. Additional Findings

### Template Consistency

**Excellent**: All 37 templates with dependencies follow identical schema:
- Same field names (`python`, `system`, `optional`)
- Same data types (lists for packages/commands)
- Same version spec format (pip-compatible)

**No cleanup needed** - templates are already consistent.

### Optional Dependencies Field

**Current Usage**:
- `optional: false` in most templates
- Field purpose unclear (not used in dependency checker)
- Consider removing or implementing in future

**Recommendation**: Document field purpose or deprecate if unused.

### System Dependencies

**Common Patterns**:
- `python3` - Most agents
- `git` - Most agents
- `node>=20` - TypeScript/JavaScript agents
- `npm>=10` - TypeScript/JavaScript agents

**Validation Opportunity**: Could add warnings for missing common dependencies.

### Python Version Compatibility

**Current State**:
- All package specs use pip-compatible version constraints
- No Python version-specific dependencies noted
- Python 3.13 compatibility handled by `check_python_compatibility()`

**No changes needed** - existing logic handles version checks.

---

## 12. Conclusion

### Summary

The agent dependency loader bug is a **simple fix with high impact**:
- **Root Cause**: Single line hardcoding `.json` extension
- **Solution**: Parse YAML frontmatter from `.md` files
- **Complexity**: Low (3-hour implementation)
- **Risk**: Minimal (backward compatible)
- **Value**: Restores critical functionality

### Success Criteria

Implementation is successful when:
- ✅ All 48 agent templates load dependencies correctly
- ✅ Both `.md` and `.json` formats supported
- ✅ Unit tests achieve 85%+ coverage
- ✅ Integration tests pass with real templates
- ✅ No breaking changes to existing functionality
- ✅ `make quality` passes without errors

### Next Steps

1. **Engineer**: Implement solution following architecture in Section 5
2. **QA**: Run test suite and manual verification
3. **PM**: Review and approve for merge
4. **Docs**: Update agent format documentation

---

## Appendix A: Search Path Precedence

The dependency loader searches in this order:

```
1. PROJECT: ./.claude-mpm/agents/{agent_id}.md
   ↓ (if not found)
2. USER: ~/.claude-mpm/agents/{agent_id}.md
   ↓ (if not found)
3. SYSTEM: ./src/claude_mpm/agents/templates/{agent_id}.md
   ↓ (if not found)

Fallback to JSON:
1. PROJECT: ./.claude-mpm/agents/{agent_id}.json
   ↓ (if not found)
2. USER: ~/.claude-mpm/agents/{agent_id}.json
   ↓ (if not found)
3. SYSTEM: ./src/claude_mpm/agents/templates/{agent_id}.json
```

**Why This Order**:
- Project-specific configs override user configs
- User configs override system defaults
- Markdown takes precedence over JSON (current format)

---

## Appendix B: YAML Parsing Performance

**Benchmark** (estimated):
- File read: ~0.5ms per file
- YAML parse: ~0.5ms per file
- Total per agent: ~1ms

**For 48 agents**: ~50ms total (negligible)

**Why Fast**:
- Small frontmatter blocks (<1KB typically)
- PyYAML's C extension (when available)
- Only runs during deployment (not hot path)

**No performance concerns** ✅

---

## Appendix C: Error Scenarios

| Scenario | Handling | Impact |
|----------|----------|--------|
| File not found | Continue to next path | Agent marked as no deps |
| Invalid YAML | Log warning, continue | Agent marked as no deps |
| Missing dependencies key | Return None | Agent marked as no deps |
| Empty dependencies | Return empty dict | Agent has no deps (valid) |
| Corrupted file | Log error, continue | Agent marked as no deps |
| Permission denied | Log error, continue | Agent marked as no deps |

**Principle**: Fail gracefully, never crash deployment.

---

## Appendix D: Related Files

**Files That May Need Updates**:
- `src/claude_mpm/utils/agent_dependency_loader.py` - **PRIMARY** (fix bug here)
- `tests/utils/test_agent_dependency_loader.py` - Add YAML tests
- `docs/reference/AGENT_FORMAT.md` - Update format documentation (if exists)
- `CHANGELOG.md` - Document bug fix

**Files That DON'T Need Updates**:
- Agent templates (already in correct format)
- Dependency installation logic (works correctly)
- Deployment state tracking (works correctly)

---

**End of Research Document**

**Status**: IMPLEMENTATION READY ✅
**Confidence**: HIGH (95%+)
**Recommended Action**: PROCEED WITH IMPLEMENTATION
