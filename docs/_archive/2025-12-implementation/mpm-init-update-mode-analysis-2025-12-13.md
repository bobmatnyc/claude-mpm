# /mpm-init Update Mode Analysis

**Research Date**: 2025-12-13
**Researcher**: Research Agent
**Purpose**: Understand current `/mpm-init` implementation to add intelligent "update mode" for enhancing existing CLAUDE.md files

---

## Executive Summary

The `/mpm-init` command currently supports basic update mode (`--update` flag) that performs smart merging of CLAUDE.md content. This research identifies the implementation structure, available data sources, and recommends an approach for adding an intelligent "update mode" that extracts project knowledge from git history, logs, and existing documentation.

**Key Findings**:
1. `/mpm-init` delegates to Agentic Coder Optimizer agent via subprocess
2. CLAUDE.md template uses priority-based organization (🔴🟡🟢⚪)
3. Rich git history analysis already available via `EnhancedProjectAnalyzer`
4. Session logs and response logs exist in `.claude-mpm/` directory
5. Current update mode preserves custom sections but doesn't intelligently extract project knowledge

---

## 1. /mpm-init Implementation Structure

### 1.1 Command Definition

**Location**: `src/claude_mpm/commands/mpm-init.md`

**Key Capabilities**:
- Standard initialization (creates CLAUDE.md from scratch)
- Update mode (`--update` flag): Smart merge with existing CLAUDE.md
- Quick update mode (`/mpm-init update`): Lightweight git activity-based update
- Context analysis (`/mpm-init context`): Analyzes git history for work resumption
- Catchup mode (`/mpm-init catchup`): Quick commit history display

**Slash Command Processing**:
```bash
/mpm-init                    → Standard initialization (auto-detects existing CLAUDE.md)
/mpm-init update             → Quick update (maps to --quick-update flag)
/mpm-init context --days 14  → Git history analysis (delegates to Research agent)
/mpm-init --update           → Full update with smart merge
```

### 1.2 Core Implementation

**Handler**: `src/claude_mpm/cli/commands/mpm_init_handler.py`
- Entry point for all `/mpm-init` operations
- Routes to different modes based on flags/subcommands

**Command Core**: `src/claude_mpm/cli/commands/mpm_init/core.py`
- `MPMInitCommand` class orchestrates initialization
- Delegates to Agentic Coder Optimizer via subprocess
- Uses `claude-mpm run --non-interactive -i <prompt_file>`

**Supporting Modules**:
- `prompts.py`: Builds initialization and update prompts for agents
- `git_activity.py`: Git history analysis and activity tracking
- `modes.py`: Handles different initialization modes (review, dry-run, quick-update)
- `display.py`: Rich console output formatting

### 1.3 Update Flow (Existing)

**Current Update Mode** (`--update` flag):

1. **Pre-Update Checks**:
   - Analyze existing CLAUDE.md via `DocumentationManager`
   - Archive previous version to `docs/_archive/`
   - Validate project structure

2. **Prompt Generation**:
   - Build update prompt via `prompts.build_update_prompt()`
   - Include doc analysis context (size, sections, custom content)
   - Specify preservation rules

3. **Agent Delegation**:
   - Write prompt to temp file
   - Execute `claude-mpm run --non-interactive -i <prompt_file>`
   - Agentic Coder Optimizer performs smart merge

4. **Post-Processing**:
   - Validate merged content
   - Update metadata (timestamp, version)
   - Display change summary

**Quick Update Mode** (`/mpm-init update`):

1. Analyze git history (last 30 days) via `EnhancedProjectAnalyzer`
2. Generate activity report
3. Append activity notes to CLAUDE.md
4. Export report to `docs/reports/` (optional)

---

## 2. CLAUDE.md Structure and Template

### 2.1 Standard Template Structure

**Template Builder**: `DocumentationManager.create_minimal_template()`

**Standard Sections** (priority-ordered):

```markdown
# Project Name - CLAUDE.md

## 🎯 Priority Index
### 🔴 CRITICAL Instructions
- [Critical security and data handling rules]

### 🟡 IMPORTANT Instructions
- [Key architectural decisions and workflows]

## 📋 Project Overview
[Project purpose and goals]

## 🔴 CRITICAL: Security & Data Handling
[Security requirements]

## 🔴 CRITICAL: Core Business Rules
[Business logic constraints]

## 🟡 IMPORTANT: Architecture & Design
[Architectural decisions]

## 🟡 IMPORTANT: Development Workflow
### ONE Way to Build
### ONE Way to Test
### ONE Way to Deploy

## 🟢 STANDARD: Coding Guidelines
[Standard practices]

## 🟢 STANDARD: Common Tasks
[Routine operations]

## 📚 Documentation Links
[Additional resources]

## ⚪ OPTIONAL: Future Enhancements
[Nice-to-have features]

## 📝 Meta: Maintaining This Document
- Last Updated: [timestamp]
- Update Frequency: [when to update]
```

### 2.2 Priority System

**Priority Markers**:
- 🔴 CRITICAL: Security, data handling, breaking changes
- 🟡 IMPORTANT: Key workflows, architecture decisions
- 🟢 STANDARD: Common operations, best practices
- ⚪ OPTIONAL: Future enhancements

**Section Priority Mapping** (DocumentationManager.SECTION_PRIORITY):
```python
{
    "priority_index": 100,
    "critical_security": 95,
    "critical_business": 90,
    "important_architecture": 80,
    "important_workflow": 75,
    "project_overview": 70,
    "standard_coding": 60,
    "standard_tasks": 55,
    "documentation_links": 40,
    "optional_future": 20,
    "meta_maintenance": 10,
}
```

### 2.3 Single-Path Principle

**Core Concept**: ONE clear way to do ANYTHING
- ONE command for building
- ONE command for testing
- ONE command for deployment
- ONE command for linting
- ONE command for formatting

**Example**:
```markdown
## 🟡 IMPORTANT: Development Workflow

### ONE Way to Build
```bash
make build
```

### ONE Way to Test
```bash
make test
```

### ONE Way to Deploy
```bash
make deploy
```
```

---

## 3. Available Data Sources for Project Knowledge

### 3.1 Git History (Primary Source)

**Analyzer**: `EnhancedProjectAnalyzer` (`src/claude_mpm/services/project/enhanced_analyzer.py`)

**Capabilities**:
- Recent commits analysis (configurable days)
- File change frequency tracking
- Author contribution statistics
- Branch information
- Documentation changes detection
- Commit pattern analysis (features, fixes, refactoring, etc.)
- Hot spot identification (frequently changed files)

**Example Usage**:
```python
analyzer = EnhancedProjectAnalyzer(project_path)
git_analysis = analyzer.analyze_git_history(days_back=30)

# Returns:
{
    "git_available": True,
    "recent_commits": [...],  # Last 50 commits
    "changed_files": {
        "total_files": 127,
        "most_changed": {"file.py": 15, ...},
        "recently_added": [...]
    },
    "authors": {
        "total_authors": 3,
        "contributors": {"Author Name": 25, ...}
    },
    "branch_info": {
        "current_branch": "main",
        "branches": [...],
        "has_uncommitted_changes": False
    },
    "patterns": {
        "features": [...],
        "fixes": [...],
        "refactoring": [...],
        "documentation": [...]
    },
    "hot_spots": [
        {"file": "path/to/file.py", "changes": 15, "category": "source"}
    ]
}
```

### 3.2 Session Logs

**Location**: `.claude-mpm/`

**Available Log Types**:

1. **Response Logs** (`responses/*.json`):
   - PM summaries with tasks, files, next steps
   - Stop event data (context thresholds, completions)
   - Session IDs and timestamps
   - Token usage tracking

2. **Resume Logs** (`resume-logs/*.md`):
   - Structured 10k-token summaries
   - Session metadata
   - Work context preservation

3. **Activity Logs** (`activity/`):
   - Agent activity tracking
   - Operation history

4. **Correlation Logs** (`correlations/`):
   - Event correlation data
   - Request/response tracking

5. **Monitor Daemon Logs** (`monitor-daemon-*.log`):
   - Real-time monitoring data
   - System events

**Note**: Session logs provide context about **what was worked on** but may not reflect **committed work** (git history is more reliable for actual changes).

### 3.3 Memory System

**Location**: `.claude-mpm/memories/`

**Purpose**: Project-specific knowledge retention

**Current Status**: Directory exists but structure depends on KuzuMemory integration

### 3.4 Existing Documentation

**Analyzable Sources**:
- Existing CLAUDE.md (via `DocumentationManager`)
- README.md
- docs/ directory contents
- Inline code comments
- Docstrings

**DocumentationManager Capabilities**:
- Section extraction and analysis
- Custom section detection
- Priority marker identification
- Outdated pattern detection
- Content preview generation

### 3.5 Project Structure

**Analyzer**: `ProjectOrganizer` (`src/claude_mpm/services/project/project_organizer.py`)

**Capabilities**:
- Project structure validation
- Directory organization checking
- File placement analysis
- Structure grading

---

## 4. Current Update Mode vs. Proposed Enhanced Update Mode

### 4.1 Current Update Mode Limitations

**What It Does Well**:
✅ Smart merging of existing CLAUDE.md with new template
✅ Preserves custom sections
✅ Archives previous versions
✅ Reorganizes by priority
✅ Updates metadata timestamps

**What It Lacks**:
❌ No intelligent extraction of project knowledge from git history
❌ Doesn't analyze commit patterns to infer architectural decisions
❌ No detection of new technologies/frameworks added since last update
❌ Doesn't identify common workflows from repeated git operations
❌ No inference of business rules from commit messages
❌ Doesn't suggest priority levels based on change frequency

### 4.2 Proposed Enhanced Update Mode

**Goal**: Intelligently enhance existing CLAUDE.md by extracting project knowledge from all available data sources.

**Workflow**:

1. **Data Collection Phase**:
   - Analyze git history (last 90 days or since last CLAUDE.md update)
   - Extract commit patterns (features, fixes, architectural changes)
   - Identify hot spots (frequently changed files)
   - Detect new dependencies/technologies
   - Review session logs for recent work context
   - Analyze existing CLAUDE.md structure

2. **Knowledge Extraction Phase**:
   - **Architectural Decisions**: Infer from refactoring commits
   - **Common Workflows**: Detect from repeated file change patterns
   - **Security Concerns**: Identify from security-related commits
   - **Technology Stack**: Extract from dependency file changes
   - **Build/Test/Deploy Commands**: Parse from CI/CD config changes
   - **Business Rules**: Infer from feature commits and comments

3. **CLAUDE.md Enhancement Phase**:
   - Merge extracted knowledge with existing content
   - Add missing sections based on git analysis
   - Update priority levels based on change frequency
   - Suggest new CRITICAL/IMPORTANT items
   - Refresh outdated workflows
   - Add links to recently added documentation

4. **Validation Phase**:
   - Ensure single-path principle compliance
   - Validate priority organization
   - Check for contradictory instructions
   - Verify completeness

---

## 5. Recommended Implementation Approach

### 5.1 Add New Flag: `--enhance` or `--intelligent-update`

**Command**:
```bash
/mpm-init --enhance              # Full intelligent enhancement
/mpm-init --enhance --days 90    # Analyze last 90 days
/mpm-init --enhance --review     # Preview changes without applying
```

### 5.2 Implementation Strategy

**Phase 1: Knowledge Extraction Service** (New Module)

**Location**: `src/claude_mpm/services/project/knowledge_extractor.py`

**Responsibilities**:
- Analyze git history via `EnhancedProjectAnalyzer`
- Parse commit messages for patterns
- Detect technology changes from dependency files
- Identify common workflows from file change patterns
- Extract architectural decisions from refactoring commits
- Infer business rules from feature commits

**Example API**:
```python
class ProjectKnowledgeExtractor:
    def __init__(self, project_path: Path):
        self.analyzer = EnhancedProjectAnalyzer(project_path)
        self.doc_manager = DocumentationManager(project_path)

    def extract_knowledge(self, days: int = 90) -> Dict:
        """Extract project knowledge from all available sources."""
        return {
            "architectural_decisions": [...],
            "security_concerns": [...],
            "common_workflows": [...],
            "technology_stack": {...},
            "build_commands": {...},
            "business_rules": [...],
            "hot_spots": [...],
            "suggested_priorities": {...}
        }
```

**Phase 2: Enhanced Prompt Builder** (Extend `prompts.py`)

**New Function**: `build_enhancement_prompt()`

**Responsibilities**:
- Include extracted knowledge in prompt
- Provide structured data to agent
- Specify enhancement guidelines
- Request priority suggestions

**Example Prompt Structure**:
```markdown
Please ENHANCE the existing CLAUDE.md with extracted project knowledge.

## Extracted Knowledge from Git History (last 90 days):

### Architectural Decisions Detected:
- Refactor to microservices architecture (15 commits, June 2025)
- Migration from REST to GraphQL (8 commits, July 2025)

### Security Concerns Identified:
- Authentication system overhaul (12 commits, tagged "security")
- GDPR compliance additions (5 commits)

### Common Workflows Detected:
- Build: `npm run build` (detected in 47 commits)
- Test: `npm test` (detected in 52 commits)
- Deploy: `make deploy` (detected in 8 commits)

### Technology Stack Changes:
- Added: React 18, TypeScript 5.0, Vite
- Removed: Webpack, Create React App

### Hot Spots (Frequently Changed):
- src/auth/AuthService.ts (23 changes)
- src/api/graphql/schema.ts (18 changes)

## Enhancement Instructions:

1. Add missing architectural decisions to 🟡 IMPORTANT: Architecture section
2. Update security guidelines based on detected security commits
3. Standardize workflow commands (ensure single-path principle)
4. Update technology stack documentation
5. Add notes about hot spot files (potential refactoring candidates)
6. Suggest new CRITICAL/IMPORTANT priority items based on change frequency
```

**Phase 3: Integration with Existing Update Flow** (Modify `core.py`)

**Add New Initialization Mode**:
```python
def initialize_project(
    self,
    # ... existing parameters ...
    enhance_mode: bool = False,  # NEW
    enhancement_days: int = 90,  # NEW
):
    if enhance_mode:
        return self._run_enhancement_mode(enhancement_days)
    # ... existing logic ...
```

**New Method**:
```python
def _run_enhancement_mode(self, days: int) -> Dict:
    """Run intelligent enhancement mode."""
    from claude_mpm.services.project.knowledge_extractor import (
        ProjectKnowledgeExtractor
    )

    # 1. Extract knowledge
    extractor = ProjectKnowledgeExtractor(self.project_path)
    knowledge = extractor.extract_knowledge(days)

    # 2. Build enhancement prompt
    prompt = prompts.build_enhancement_prompt(
        self.project_path,
        knowledge,
        self.doc_manager.analyze_existing_content()
    )

    # 3. Delegate to agent
    result = self._run_initialization(prompt, verbose=True, update_mode=True)

    # 4. Post-process
    self._handle_enhancement_post_processing(knowledge)

    return result
```

### 5.3 File Organization

**New Files to Create**:

1. `src/claude_mpm/services/project/knowledge_extractor.py`
   - `ProjectKnowledgeExtractor` class
   - Knowledge extraction logic
   - Pattern detection algorithms

2. `src/claude_mpm/cli/commands/mpm_init/enhancement.py`
   - Enhancement mode utilities
   - Knowledge formatting for display
   - Post-processing logic

**Modified Files**:

1. `src/claude_mpm/cli/commands/mpm_init/core.py`
   - Add `enhance_mode` parameter
   - Add `_run_enhancement_mode()` method

2. `src/claude_mpm/cli/commands/mpm_init/prompts.py`
   - Add `build_enhancement_prompt()` function

3. `src/claude_mpm/cli/parsers/mpm_init_parser.py`
   - Add `--enhance` flag
   - Add `--enhancement-days` parameter

4. `src/claude_mpm/commands/mpm-init.md`
   - Document enhancement mode
   - Add usage examples

---

## 6. Knowledge Extraction Algorithms

### 6.1 Architectural Decision Detection

**Strategy**: Analyze refactoring commits and large-scale changes

**Algorithm**:
```python
def detect_architectural_decisions(commits: List[Dict]) -> List[str]:
    """Detect architectural decisions from commits."""
    decisions = []

    for commit in commits:
        msg_lower = commit["message"].lower()

        # Refactoring patterns
        if any(kw in msg_lower for kw in ["refactor", "migrate", "restructure"]):
            if "to" in msg_lower or "from" in msg_lower:
                # Extract migration pattern: "migrate from X to Y"
                decisions.append({
                    "type": "migration",
                    "description": commit["message"],
                    "timestamp": commit["timestamp"],
                    "confidence": "high"
                })

        # Architecture keywords
        if any(kw in msg_lower for kw in ["architecture", "design", "pattern"]):
            decisions.append({
                "type": "architectural_change",
                "description": commit["message"],
                "timestamp": commit["timestamp"],
                "confidence": "medium"
            })

    return decisions
```

### 6.2 Common Workflow Detection

**Strategy**: Analyze repeated file change patterns and CI/CD configurations

**Algorithm**:
```python
def detect_common_workflows(file_changes: Dict, project_path: Path) -> Dict:
    """Detect common build/test/deploy workflows."""
    workflows = {
        "build": None,
        "test": None,
        "deploy": None,
        "lint": None,
        "format": None
    }

    # Check for CI/CD config
    ci_configs = [
        ".github/workflows/*.yml",
        ".gitlab-ci.yml",
        "Makefile",
        "package.json"
    ]

    for config_pattern in ci_configs:
        for config_file in project_path.glob(config_pattern):
            # Parse config and extract commands
            commands = parse_workflow_file(config_file)
            workflows.update(commands)

    return workflows
```

### 6.3 Technology Stack Detection

**Strategy**: Monitor dependency file changes

**Algorithm**:
```python
def detect_technology_changes(changed_files: Dict, project_path: Path) -> Dict:
    """Detect technology stack changes."""
    dependency_files = {
        "package.json": "npm",
        "pyproject.toml": "python",
        "requirements.txt": "python",
        "Cargo.toml": "rust",
        "go.mod": "go"
    }

    changes = {
        "added": [],
        "removed": [],
        "updated": []
    }

    for dep_file, ecosystem in dependency_files.items():
        if dep_file in changed_files.get("most_changed", {}):
            # Parse dependency file and detect changes
            # (requires git diff analysis)
            diff = get_dependency_diff(project_path / dep_file)
            changes["added"].extend(diff["added"])
            changes["removed"].extend(diff["removed"])

    return changes
```

### 6.4 Priority Suggestion Algorithm

**Strategy**: Use change frequency + file category to suggest priorities

**Algorithm**:
```python
def suggest_priorities(hot_spots: List[Dict], patterns: Dict) -> Dict:
    """Suggest priority levels based on change frequency."""
    suggestions = {
        "critical": [],
        "important": [],
        "standard": []
    }

    # Security-related changes = CRITICAL
    for commit in patterns.get("fixes", []):
        if any(kw in commit.lower() for kw in ["security", "auth", "cve"]):
            suggestions["critical"].append({
                "reason": "Security fix detected",
                "evidence": commit
            })

    # Architectural changes = IMPORTANT
    for commit in patterns.get("refactoring", []):
        suggestions["important"].append({
            "reason": "Architectural change",
            "evidence": commit
        })

    # Hot spots with >10 changes = IMPORTANT (potential refactoring needed)
    for hot_spot in hot_spots:
        if hot_spot["changes"] > 10:
            suggestions["important"].append({
                "reason": f"Hot spot: {hot_spot['file']} ({hot_spot['changes']} changes)",
                "evidence": "Frequently changed file - consider refactoring"
            })

    return suggestions
```

---

## 7. Integration Points

### 7.1 Slash Command Integration

**Update**: `src/claude_mpm/commands/mpm-init.md`

**Add New Usage**:
```markdown
### Enhance Existing Documentation
```bash
/mpm-init --enhance              # Intelligent enhancement mode
/mpm-init --enhance --days 90    # Analyze last 90 days
/mpm-init --enhance --review     # Preview without applying
```

Analyzes git history, session logs, and project structure to intelligently
enhance existing CLAUDE.md with extracted project knowledge.
```

### 7.2 CLI Argument Parser

**Update**: `src/claude_mpm/cli/parsers/mpm_init_parser.py`

**Add Arguments**:
```python
parser.add_argument(
    "--enhance",
    action="store_true",
    help="Intelligent enhancement mode - extract knowledge from git history"
)

parser.add_argument(
    "--enhancement-days",
    type=int,
    default=90,
    help="Days of git history to analyze for enhancement (default: 90)"
)
```

### 7.3 Agent Prompt Templates

**Update**: `src/claude_mpm/cli/commands/mpm_init/prompts.py`

**Add New Function**:
```python
def build_enhancement_prompt(
    project_path: Path,
    extracted_knowledge: Dict,
    doc_analysis: Dict
) -> str:
    """Build enhancement prompt with extracted project knowledge."""
    # ... implementation from section 5.2 ...
```

---

## 8. Testing Strategy

### 8.1 Unit Tests

**Test File**: `tests/unit/test_knowledge_extractor.py`

**Test Cases**:
- `test_detect_architectural_decisions()`
- `test_detect_common_workflows()`
- `test_detect_technology_changes()`
- `test_suggest_priorities()`
- `test_extract_knowledge_integration()`

### 8.2 Integration Tests

**Test File**: `tests/integration/test_mpm_init_enhance.py`

**Test Cases**:
- `test_enhance_mode_with_git_history()`
- `test_enhance_mode_no_git_history()`
- `test_enhance_mode_preview()`
- `test_enhance_mode_with_custom_sections()`

### 8.3 End-to-End Tests

**Test Scenario**: Real project enhancement

1. Create test project with git history
2. Run `/mpm-init --enhance`
3. Verify CLAUDE.md contains extracted knowledge
4. Verify priority organization
5. Verify single-path principle compliance

---

## 9. Migration Path

### 9.1 Backward Compatibility

**Requirement**: Existing `/mpm-init` commands must continue to work

**Strategy**:
- `--enhance` is a new opt-in flag
- Default behavior unchanged
- Existing `--update` mode preserved
- Quick update (`/mpm-init update`) unaffected

### 9.2 Deprecation Plan (Optional)

**Future Consideration**: Merge `--update` and `--enhance` into single intelligent update mode

**Timeline**:
- v1.0: Introduce `--enhance` as experimental
- v1.1: Promote to stable
- v1.2: Make `--enhance` default for `--update`
- v2.0: Deprecate separate `--update` flag

---

## 10. Risks and Mitigation

### 10.1 Risk: Inaccurate Knowledge Extraction

**Description**: Commit message parsing may misinterpret architectural decisions

**Mitigation**:
- Use confidence scoring
- Provide preview mode (`--enhance --review`)
- Allow manual review before applying
- Include evidence citations in CLAUDE.md

### 10.2 Risk: Performance Impact

**Description**: Analyzing 90 days of git history may be slow

**Mitigation**:
- Configurable `--enhancement-days` parameter
- Cache git analysis results
- Show progress indicators
- Implement timeout thresholds

### 10.3 Risk: Overwriting Custom Content

**Description**: Enhancement may overwrite user's custom sections

**Mitigation**:
- Preserve custom sections (existing behavior)
- Archive before updating (existing behavior)
- Use `--preserve-custom` flag (existing)
- Show diff preview before applying

---

## 11. Success Metrics

### 11.1 Functionality Metrics

**Measure**:
- ✅ Knowledge extraction accuracy (manual review of 10 test projects)
- ✅ CLAUDE.md completeness score (before vs. after enhancement)
- ✅ User satisfaction (survey of early adopters)

### 11.2 Performance Metrics

**Measure**:
- ⏱️ Enhancement time (target: <30 seconds for 90 days of history)
- 📊 Git analysis caching effectiveness
- 💾 Memory usage during enhancement

### 11.3 Adoption Metrics

**Measure**:
- 📈 Usage of `--enhance` flag
- 📉 Reduction in manual CLAUDE.md updates
- 📝 User feedback on extracted knowledge quality

---

## 12. Next Steps

### 12.1 Implementation Roadmap

**Phase 1: Core Knowledge Extraction** (Week 1)
- Create `ProjectKnowledgeExtractor` class
- Implement architectural decision detection
- Implement common workflow detection
- Implement technology stack detection
- Unit tests

**Phase 2: Prompt Enhancement** (Week 1)
- Create `build_enhancement_prompt()` function
- Test prompt with sample extracted knowledge
- Validate agent response quality

**Phase 3: CLI Integration** (Week 2)
- Add `--enhance` flag to parser
- Integrate with `MPMInitCommand`
- Add enhancement mode to handler
- Integration tests

**Phase 4: Documentation and Testing** (Week 2)
- Update `/mpm-init` command documentation
- End-to-end testing
- User acceptance testing
- Performance optimization

**Phase 5: Release** (Week 3)
- Code review
- Beta testing
- Documentation review
- Release to production

### 12.2 Open Questions

1. **Should enhancement be automatic on update?**
   - Pros: Better CLAUDE.md quality by default
   - Cons: Slower, may surprise users
   - Recommendation: Opt-in initially, gather feedback

2. **How much git history to analyze?**
   - Default: 90 days (last quarter)
   - Configurable via `--enhancement-days`
   - Adaptive mode if <25 commits in period?

3. **Should we extract from session logs?**
   - Pros: Captures recent work context
   - Cons: May include incomplete work
   - Recommendation: Use git history as primary, session logs as supplementary

---

## Appendices

### Appendix A: File Locations Reference

**Command Definition**:
- `src/claude_mpm/commands/mpm-init.md`

**Core Implementation**:
- `src/claude_mpm/cli/commands/mpm_init_handler.py`
- `src/claude_mpm/cli/commands/mpm_init/core.py`
- `src/claude_mpm/cli/commands/mpm_init/prompts.py`
- `src/claude_mpm/cli/commands/mpm_init/git_activity.py`
- `src/claude_mpm/cli/commands/mpm_init/modes.py`
- `src/claude_mpm/cli/commands/mpm_init/display.py`

**Documentation Management**:
- `src/claude_mpm/services/project/documentation_manager.py`

**Project Analysis**:
- `src/claude_mpm/services/project/enhanced_analyzer.py`
- `src/claude_mpm/services/project/project_organizer.py`

**Data Directories**:
- `.claude-mpm/responses/` - Response logs
- `.claude-mpm/resume-logs/` - Resume logs
- `.claude-mpm/memories/` - Memory system
- `docs/_archive/` - Archived CLAUDE.md versions

### Appendix B: CLAUDE.md Template (Full)

See `DocumentationManager.create_minimal_template()` for minimal version.

Full template includes:
- Priority Index (🎯)
- Project Overview (📋)
- Critical sections (🔴)
- Important sections (🟡)
- Standard sections (🟢)
- Optional sections (⚪)
- Meta section (📝)

### Appendix C: Git Analysis Data Structure

**Example Output** from `EnhancedProjectAnalyzer.analyze_git_history()`:

```json
{
  "git_available": true,
  "recent_commits": [
    {
      "hash": "abc12345",
      "author": "John Doe",
      "email": "john@example.com",
      "timestamp": "2025-12-01T10:30:00",
      "message": "feat: add user authentication"
    }
  ],
  "changed_files": {
    "total_files": 127,
    "most_changed": {
      "src/auth/AuthService.ts": 23,
      "src/api/schema.ts": 18
    },
    "recently_added": ["src/auth/PasswordReset.ts"]
  },
  "authors": {
    "total_authors": 3,
    "contributors": {
      "John Doe <john@example.com>": 45,
      "Jane Smith <jane@example.com>": 32
    }
  },
  "branch_info": {
    "current_branch": "main",
    "branches": ["main", "develop", "feature/auth"],
    "has_uncommitted_changes": false
  },
  "patterns": {
    "features": [
      "feat: add user authentication",
      "feat: implement password reset"
    ],
    "fixes": [
      "fix: resolve login race condition"
    ],
    "refactoring": [
      "refactor: migrate from REST to GraphQL"
    ],
    "summary": {
      "total_commits": 127,
      "feature_commits": 45,
      "bug_fixes": 12,
      "most_active_type": "features"
    }
  },
  "hot_spots": [
    {
      "file": "src/auth/AuthService.ts",
      "changes": 23,
      "type": ".ts",
      "category": "source"
    }
  ]
}
```

---

## Conclusion

The `/mpm-init` command has a solid foundation for intelligent CLAUDE.md updates. The recommended approach adds a `--enhance` flag that leverages existing git analysis infrastructure (`EnhancedProjectAnalyzer`) to extract project knowledge and enhance documentation.

**Key Advantages**:
- ✅ Builds on existing infrastructure (minimal new code)
- ✅ Backward compatible (opt-in flag)
- ✅ Leverages rich git history data
- ✅ Aligns with existing update workflow
- ✅ Preserves custom content and archives

**Implementation Complexity**: Medium
- New module: `ProjectKnowledgeExtractor` (~300 lines)
- Prompt extension: `build_enhancement_prompt()` (~150 lines)
- CLI integration: ~50 lines
- Tests: ~400 lines
- **Total**: ~900 lines of new code

**Timeline**: 2-3 weeks (includes testing and documentation)

**Return on Investment**: High
- Users get better CLAUDE.md with less manual work
- Extracted knowledge is evidence-based (git commits)
- Reduces documentation debt
- Improves AI agent effectiveness with richer context

---

**Research Complete**: 2025-12-13
**Next Action**: Review findings and approve implementation roadmap
