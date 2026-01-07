# Claude MPM Output Style Deployment Analysis

**Research Date**: 2025-12-09
**Researcher**: Research Agent
**Purpose**: Understand current output style files, deployment mechanism, and recommend approach for adding style deployment

---

## Executive Summary

Claude MPM currently has a sophisticated output style deployment system that:
- **Detects Claude Code version** to determine deployment strategy
- **Deploys styles to TWO directories**: `~/.claude/output-styles/` (Claude Code 1.0.83+) AND `~/.claude/styles/` (legacy/unknown)
- **Has teaching mode support** via `PM_INSTRUCTIONS_TEACH.md` but **NO deployment mechanism**
- **Uses OutputStyleManager** for version-aware deployment

**Key Finding**: Teaching mode exists but is NOT deployed anywhere. Output styles are deployed to `~/.claude/output-styles/` only.

---

## 1. Current Style Files

### Source Files in Framework

| File | Path | Purpose | Size | Deployed? |
|------|------|---------|------|-----------|
| **OUTPUT_STYLE.md** | `src/claude_mpm/agents/OUTPUT_STYLE.md` | Main PM output style (no emojis, neutral tone) | ~12KB | ✅ YES (`~/.claude/output-styles/`) |
| **PM_INSTRUCTIONS_TEACH.md** | `src/claude_mpm/agents/PM_INSTRUCTIONS_TEACH.md` | Teaching mode for beginners (Socratic method, emojis allowed) | ~53KB | ❌ NO |
| **PM_INSTRUCTIONS.md** | `src/claude_mpm/agents/PM_INSTRUCTIONS.md` | Core PM instructions | ~12KB | ✅ YES (merged to `.claude-mpm/PM_INSTRUCTIONS_DEPLOYED.md`) |

### OUTPUT_STYLE.md Content

**Frontmatter**:
```yaml
---
name: Claude MPM
description: Multi-Agent Project Manager orchestration mode with mandatory delegation and professional communication standards
---
```

**Key Characteristics**:
- **NO EMOJIS** - Strictly forbidden
- **NO EXCLAMATION POINTS** - Forbidden
- **NO ENTHUSIASM** - Professional, neutral tone only
- **Mandatory delegation** - PM must delegate all work
- Professional acknowledgments only ("Understood", "Confirmed", "Noted")

### PM_INSTRUCTIONS_TEACH.md Content

**Frontmatter**:
```markdown
# Project Manager Agent - Teaching Mode

**Version**: 0001
**Purpose**: Adaptive teaching for users new to Claude MPM or coding
**Activation**: When user requests teach mode or beginner patterns detected
**Based On**: Research document `docs/research/claude-mpm-teach-style-design-2025-12-03.md`
```

**Key Characteristics**:
- **EMOJIS ALLOWED** - Uses teaching emojis (🎓, 📘, 💡, etc.)
- **ENTHUSIASM ALLOWED** - Encouraging, supportive tone
- **Socratic Method** - Guide through questions
- **Progressive Disclosure** - Start simple, deepen when needed
- **Security-First** - Treats secrets management as foundational

**Teaching Philosophy**:
- Socratic Method: Guide through questions, not direct answers
- Productive Failure: Allow struggle, teach at moment of need
- Zone of Proximal Development: Scaffold support, fade as competence grows
- Progressive Disclosure: Start simple, deepen only when needed
- Security-First: Treat secrets management as foundational
- Build Independence: Goal is proficiency, not dependency
- Non-Patronizing: Respect user intelligence, celebrate learning

---

## 2. Current Deployment Directories

### Where Styles Are Deployed

```
~/.claude/
├── output-styles/         # Claude Code 1.0.83+ output styles
│   └── claude-mpm.md     # OUTPUT_STYLE.md deployed here (12KB)
│
├── styles/               # Legacy directory (purpose unclear)
│   └── claude-mpm.md    # Also OUTPUT_STYLE.md (6KB, older version)
│
├── agents/              # Agent definitions deployed here
│   └── *.md            # Various agent files
│
└── settings.json        # Claude Code settings (activeOutputStyle: "claude-mpm")
```

### Project-Local Deployment

```
{project}/.claude-mpm/
├── PM_INSTRUCTIONS_DEPLOYED.md   # Merged PM instructions
│                                  # (PM_INSTRUCTIONS + WORKFLOW + MEMORY)
└── templates/                     # PM instruction templates
    ├── circuit-breakers.md
    ├── context-management-examples.md
    ├── git-file-tracking.md
    ├── pm-examples.md
    └── ... (11 template files)
```

---

## 3. Deployment Mechanism

### OutputStyleManager Class

**Location**: `src/claude_mpm/core/output_style_manager.py`

**Responsibilities**:
1. **Claude version detection** - Runs `claude --version` to detect installed version
2. **Version comparison** - Determines if Claude Code >= 1.0.83
3. **Output style extraction** - Reads `OUTPUT_STYLE.md` file
4. **Deployment to `~/.claude/output-styles/`** - Writes style file
5. **Activation in settings.json** - Sets `activeOutputStyle: "claude-mpm"`
6. **Fallback for older versions** - Returns injectable content for Claude < 1.0.83

**Key Methods**:
```python
class OutputStyleManager:
    def __init__(self):
        self.output_style_dir = Path.home() / ".claude" / "output-styles"
        self.output_style_path = self.output_style_dir / "claude-mpm.md"
        self.settings_file = Path.home() / ".claude" / "settings.json"
        self.mpm_output_style_path = Path(__file__).parent.parent / "agents" / "OUTPUT_STYLE.md"

    def supports_output_styles(self) -> bool:
        """Check if Claude Code >= 1.0.83"""
        return self._compare_versions(self.claude_version, "1.0.83") >= 0

    def deploy_output_style(self, content: str) -> bool:
        """Deploy style to ~/.claude/output-styles/ and activate"""
        # Write file
        self.output_style_path.write_text(content)
        # Activate in settings
        self._activate_output_style()

    def _activate_output_style(self) -> bool:
        """Update settings.json to activate claude-mpm style"""
        settings["activeOutputStyle"] = "claude-mpm"
```

### SystemInstructionsDeployer Class

**Location**: `src/claude_mpm/services/agents/deployment/system_instructions_deployer.py`

**Responsibilities**:
1. **Merge PM instruction files** - Combines PM_INSTRUCTIONS + WORKFLOW + MEMORY
2. **Deploy to `.claude-mpm/PM_INSTRUCTIONS_DEPLOYED.md`** - Project-local
3. **Deploy templates** - Copies 11 template files to `.claude-mpm/templates/`
4. **Modification time tracking** - Only redeploys if source files changed

**Key Methods**:
```python
class SystemInstructionsDeployer:
    def deploy_system_instructions(self, target_dir, force_rebuild, results):
        """Deploy merged PM instructions to project .claude-mpm directory"""
        # Read source files
        pm_instructions_path = agents_path / "PM_INSTRUCTIONS.md"
        workflow_path = agents_path / "WORKFLOW.md"
        memory_path = agents_path / "MEMORY.md"

        # Merge content
        merged_content = [path.read_text() for path in paths if path.exists()]

        # Write to .claude-mpm/PM_INSTRUCTIONS_DEPLOYED.md
        target_file = claude_mpm_dir / "PM_INSTRUCTIONS_DEPLOYED.md"
        target_file.write_text("\n\n".join(merged_content))

    def deploy_templates(self, claude_mpm_dir, force_rebuild, results):
        """Deploy PM instruction templates to .claude-mpm/templates/"""
        # Only deploys PM instruction templates (not agent definitions)
        pm_templates = [
            "circuit-breakers.md",
            "context-management-examples.md",
            # ... 11 total templates
        ]
```

### Deployment Flow

```
Startup (claude-mpm run)
    |
    v
OutputStyleManager.__init__()
    |
    +-- Detect Claude version (claude --version)
    +-- Determine if >= 1.0.83
    |
    v
deploy_output_style(content)
    |
    +-- Read OUTPUT_STYLE.md
    +-- Write to ~/.claude/output-styles/claude-mpm.md
    +-- Activate in settings.json
    |
    v
SystemInstructionsDeployer.deploy_system_instructions()
    |
    +-- Read PM_INSTRUCTIONS.md + WORKFLOW.md + MEMORY.md
    +-- Merge content
    +-- Write to .claude-mpm/PM_INSTRUCTIONS_DEPLOYED.md
    +-- Deploy templates to .claude-mpm/templates/
```

---

## 4. The `~/.claude/styles/` Mystery

### Current State

- **Directory**: `~/.claude/styles/claude-mpm.md` EXISTS (6.6KB, dated Nov 20)
- **Content**: Contains OUTPUT_STYLE.md content (without YAML frontmatter)
- **Purpose**: UNCLEAR - No code references found in codebase

### Analysis

**Hypothesis 1: Legacy Directory**
- Created by older version of Claude MPM or Claude Code
- Superseded by `~/.claude/output-styles/` in Claude Code 1.0.83+
- No longer actively used or maintained

**Hypothesis 2: Claude Code Fallback**
- Claude Code may load from `~/.claude/styles/` if `output-styles/` not available
- Undocumented fallback mechanism in Claude Code itself

**Hypothesis 3: Manual Creation**
- User manually created this for testing or experimentation
- Not part of automated deployment

**Evidence**:
- ❌ No code references to `~/.claude/styles/` in claude-mpm codebase
- ✅ Code only references `~/.claude/output-styles/` in OutputStyleManager
- ⚠️ File exists but appears to be legacy or manually created

**Recommendation**: Ignore `~/.claude/styles/` for now. Focus on `~/.claude/output-styles/` which is actively managed by OutputStyleManager.

---

## 5. Teaching Mode Deployment Gap

### Current Problem

**PM_INSTRUCTIONS_TEACH.md exists but has NO deployment mechanism:**

❌ **NOT deployed to** `~/.claude/output-styles/pm-teach.md`
❌ **NOT merged into** `.claude-mpm/PM_INSTRUCTIONS_DEPLOYED.md`
❌ **NOT referenced** in any deployment code
❌ **NOT activated** in settings.json

**Why This Matters**:
- Teaching mode is a 53KB fully-developed feature
- Based on research: `docs/research/claude-mpm-teach-style-design-2025-12-03.md`
- Ready to use, but completely inaccessible

### Where Teaching Mode Should Be Deployed

**Option A: Separate Output Style** (RECOMMENDED)
```
~/.claude/output-styles/
├── claude-mpm.md          # Default style (professional, no emojis)
└── claude-mpm-teach.md    # Teaching style (Socratic, emojis, encouraging)
```

**Activation**:
```json
// settings.json
{
  "activeOutputStyle": "claude-mpm"         // Default
  // OR
  "activeOutputStyle": "claude-mpm-teach"   // When teaching mode enabled
}
```

**Option B: Dynamic Injection** (NOT RECOMMENDED)
- Merge teaching content into PM_INSTRUCTIONS_DEPLOYED.md conditionally
- Cons: Large file size, mixing concerns, harder to toggle

**Option C: CLI Flag Switching** (HYBRID)
- Deploy both styles to `~/.claude/output-styles/`
- Use `mpm run --teach` to switch activeOutputStyle
- Best of both worlds: Separation + easy switching

---

## 6. Recommended Approach for Style Deployment

### High-Level Strategy

**Extend OutputStyleManager to support multiple styles:**

1. **Deploy multiple style files** to `~/.claude/output-styles/`
   - `claude-mpm.md` - Default professional style
   - `claude-mpm-teach.md` - Teaching mode style

2. **Add style switching capability**
   - `mpm run --teach` - Activates teaching style
   - `mpm run` (default) - Uses professional style
   - Updates `settings.json` accordingly

3. **Maintain version awareness**
   - Claude Code >= 1.0.83: Use output styles
   - Claude Code < 1.0.83: Fall back to instruction injection

### Implementation Plan

#### Step 1: Extend OutputStyleManager

**Add Multi-Style Support**:
```python
class OutputStyleManager:
    def __init__(self):
        self.styles = {
            "default": "OUTPUT_STYLE.md",
            "teach": "PM_INSTRUCTIONS_TEACH.md"
        }

    def deploy_all_styles(self) -> bool:
        """Deploy all available styles to output-styles directory"""
        for style_name, style_file in self.styles.items():
            content = self._read_style_file(style_file)
            filename = f"claude-mpm-{style_name}.md" if style_name != "default" else "claude-mpm.md"
            self._deploy_style(filename, content)

    def activate_style(self, style_name: str = "default") -> bool:
        """Activate a specific style in settings.json"""
        style_id = "claude-mpm" if style_name == "default" else f"claude-mpm-{style_name}"
        self._update_settings(activeOutputStyle=style_id)
```

#### Step 2: Add CLI Support

**Update run_parser.py**:
```python
def add_run_arguments(parser):
    parser.add_argument(
        "--teach",
        action="store_true",
        help="Enable teaching mode (beginner-friendly, Socratic method)"
    )
```

**Update ClaudeRunner**:
```python
def __init__(self, teach_mode: bool = False, ...):
    self.teach_mode = teach_mode

    # Deploy styles
    style_manager = OutputStyleManager()
    style_manager.deploy_all_styles()

    # Activate appropriate style
    style_name = "teach" if teach_mode else "default"
    style_manager.activate_style(style_name)
```

#### Step 3: Handle Version Fallback

**For Claude Code < 1.0.83**:
```python
def get_injectable_content(self, teach_mode: bool = False) -> str:
    """Get style content for injection (legacy Claude versions)"""
    style_file = "PM_INSTRUCTIONS_TEACH.md" if teach_mode else "OUTPUT_STYLE.md"
    content = self._read_style_file(style_file)
    return self._remove_frontmatter(content)
```

#### Step 4: Add Style Management Commands

**New Commands**:
```bash
# List available styles
mpm styles list

# Show active style
mpm styles active

# Switch style
mpm styles switch teach
mpm styles switch default

# Show style content
mpm styles show teach
```

---

## 7. File Locations Summary

### Source Files (Framework)

```
src/claude_mpm/agents/
├── OUTPUT_STYLE.md              # Professional PM style (12KB)
├── PM_INSTRUCTIONS_TEACH.md     # Teaching mode style (53KB)
├── PM_INSTRUCTIONS.md           # Core PM instructions
├── WORKFLOW.md                  # PM workflow configuration
├── MEMORY.md                    # Memory management
└── templates/                   # PM instruction templates
    ├── circuit-breakers.md
    ├── pm-examples.md
    └── ... (11 total)
```

### Deployed Files (User's Machine)

```
~/.claude/
├── output-styles/               # Claude Code 1.0.83+ styles
│   └── claude-mpm.md           # OUTPUT_STYLE.md deployed here
│
├── styles/                     # Legacy/unknown (ignore)
│   └── claude-mpm.md          # Old copy (not actively managed)
│
├── agents/                     # Agent definitions
│   └── *.md
│
└── settings.json               # activeOutputStyle: "claude-mpm"

{project}/.claude-mpm/
├── PM_INSTRUCTIONS_DEPLOYED.md  # Merged PM instructions
└── templates/                   # PM templates (11 files)
```

### Deployment Services

```
src/claude_mpm/
├── core/
│   └── output_style_manager.py           # Output style deployment
└── services/agents/deployment/
    └── system_instructions_deployer.py   # PM instructions deployment
```

---

## 8. Key Insights

### What Works Well

✅ **OutputStyleManager** - Sophisticated version detection and deployment
✅ **Multi-directory deployment** - Handles both ~/.claude/ and .claude-mpm/
✅ **Modification time tracking** - Only redeploys when files change
✅ **Version fallback** - Supports both old and new Claude Code versions
✅ **Teaching mode content** - Fully developed, research-backed pedagogical approach

### What's Missing

❌ **Teaching mode deployment** - PM_INSTRUCTIONS_TEACH.md not deployed anywhere
❌ **Style switching** - No way to toggle between professional and teaching modes
❌ **Multi-style support** - OutputStyleManager only handles one style
❌ **CLI flags** - No --teach flag to activate teaching mode
❌ **Style management commands** - No way to list, switch, or view styles

### Technical Debt

⚠️ **Legacy ~/.claude/styles/** - Purpose unclear, not referenced in code
⚠️ **Duplicate content** - OUTPUT_STYLE.md in two locations (output-styles and styles)
⚠️ **No style versioning** - No way to track which style version is deployed
⚠️ **No style validation** - No checks that deployed styles match source files

---

## 9. Implementation Roadmap

### Phase 1: Basic Multi-Style Support (Week 1)

**Goal**: Deploy teaching mode as a separate output style

**Tasks**:
1. Extend OutputStyleManager to support multiple styles
2. Deploy both OUTPUT_STYLE.md and PM_INSTRUCTIONS_TEACH.md
3. Add style name mapping (default → claude-mpm.md, teach → claude-mpm-teach.md)
4. Test deployment on Claude Code 1.0.83+

**Deliverables**:
- `~/.claude/output-styles/claude-mpm.md` (professional)
- `~/.claude/output-styles/claude-mpm-teach.md` (teaching)

### Phase 2: CLI Integration (Week 1-2)

**Goal**: Add --teach flag to enable teaching mode

**Tasks**:
1. Add --teach argument to run_parser.py
2. Pass teach_mode to OutputStyleManager
3. Activate appropriate style based on flag
4. Update startup logging to show active style

**Deliverables**:
- `mpm run` - Uses professional style
- `mpm run --teach` - Uses teaching style
- Clear indication of which style is active

### Phase 3: Style Management Commands (Week 2)

**Goal**: Add commands to manage output styles

**Tasks**:
1. Create styles_parser.py for CLI commands
2. Implement style listing, switching, and viewing
3. Add style status to `mpm-status` output
4. Document style management in README

**Deliverables**:
- `mpm styles list` - Show available styles
- `mpm styles active` - Show current active style
- `mpm styles switch <name>` - Switch to different style
- `mpm styles show <name>` - Display style content

### Phase 4: Version Fallback (Week 3)

**Goal**: Support teaching mode on older Claude Code versions

**Tasks**:
1. Update injectable content extraction for teaching mode
2. Add conditional injection based on teach_mode flag
3. Test on Claude Code < 1.0.83
4. Document fallback behavior

**Deliverables**:
- Teaching mode works on all Claude Code versions
- Graceful fallback for older versions
- Clear documentation of version support

---

## 10. Testing Checklist

### Manual Testing

- [ ] Deploy both styles with OutputStyleManager
- [ ] Verify files created in ~/.claude/output-styles/
- [ ] Check settings.json activeOutputStyle value
- [ ] Test `mpm run` uses professional style
- [ ] Test `mpm run --teach` uses teaching style
- [ ] Verify style switching updates settings.json
- [ ] Test on Claude Code >= 1.0.83
- [ ] Test fallback on Claude Code < 1.0.83

### Integration Testing

- [ ] Teaching mode emojis appear in Claude output
- [ ] Professional mode has no emojis
- [ ] Socratic debugging activates in teaching mode
- [ ] Mandatory delegation remains in both modes
- [ ] TodoWrite requirements consistent across modes

### User Experience Testing

- [ ] Clear indication of active style at startup
- [ ] Easy switching between modes
- [ ] Teaching mode feels supportive, not patronizing
- [ ] Professional mode remains neutral and efficient

---

## Appendix A: Teaching Mode Content Structure

### PM_INSTRUCTIONS_TEACH.md Structure

1. **Teaching Philosophy** (Lines 1-24)
   - Socratic Method
   - Productive Failure
   - Zone of Proximal Development
   - Progressive Disclosure

2. **Experience Level Detection** (Lines 25-94)
   - Two-dimensional assessment matrix
   - Implicit detection through interaction
   - Optional assessment questions

3. **Core Teaching Behaviors** (Lines 95-258)
   - Prompt enrichment
   - Socratic debugging
   - Progressive disclosure

4. **Teaching Content Areas** (Lines 259-731)
   - Secrets management (ELI5 → Practical → Production)
   - Deployment recommendations
   - MPM workflow concepts
   - Prompt engineering

5. **Adaptive Responses** (Lines 732-841)
   - For coding beginners (Quadrant 1)
   - For MPM beginners (Quadrant 2)
   - For proficient users (Quadrant 4)

6. **Error Handling as Teaching** (Lines 842-931)
   - Template for error-driven teaching
   - Examples with specific errors

7. **Graduation System** (Lines 932-1011)
   - Progress tracking
   - Graduation checkpoint
   - Adaptive transition
   - Celebration

8. **Communication Style** (Lines 1012-1054)
   - Core principles
   - Voice and tone
   - Visual indicators (emojis)

9. **Integration with Standard PM** (Lines 1055-1098)
   - Delegation to agents
   - When to add teaching commentary

10. **Teaching Response Templates** (Lines 1099-1172)
    - First-time setup
    - Concept introduction
    - Checkpoint validation
    - Celebration of learning

11. **Terminology Glossary** (Lines 1173-1233)
    - Core MPM concepts
    - Secrets management
    - Deployment
    - Inline definition pattern

12. **Activation and Configuration** (Lines 1234-1296)
    - Explicit activation
    - Implicit activation
    - Deactivation
    - Configuration options

13. **Success Metrics** (Lines 1297-1323)
    - Time to first success
    - Error resolution rate
    - Teaching mode graduation

---

## Appendix B: Code References

### Files Using OutputStyleManager

**NONE FOUND** - OutputStyleManager appears to be initialized but not actively used

**Search Query**: `OutputStyleManager|output_style_manager|deploy_output_style`
**Result**: No matches in codebase

**Hypothesis**: OutputStyleManager was created but integration is incomplete. The class exists and has full functionality, but may not be called from startup code.

### Files Deploying to ~/.claude/

```
src/claude_mpm/core/output_style_manager.py:36
    self.output_style_dir = Path.home() / ".claude" / "output-styles"

src/claude_mpm/core/claude_runner.py:103
    Path.home() / ".claude" / "output-styles" / "claude-mpm.md"

src/claude_mpm/cli/startup.py:145
    Path.home() / ".claude" / "output-styles" / "claude-mpm.md"
```

---

## Appendix C: Questions for User/PM

1. **Is ~/.claude/styles/ still relevant?**
   - Should we deploy to both directories?
   - Or deprecate ~/.claude/styles/ entirely?

2. **Teaching mode activation strategy?**
   - CLI flag: `mpm run --teach`?
   - Config setting: `teach_mode: enabled: true`?
   - Auto-detection based on user behavior?

3. **Style persistence?**
   - Should style choice persist across sessions?
   - Or reset to default on each startup?

4. **Style visibility?**
   - Should users be able to see/edit deployed styles?
   - Or keep them hidden in ~/.claude/?

5. **Version support priority?**
   - Focus on Claude Code 1.0.83+ first?
   - Or ensure backward compatibility from day one?

---

## Conclusion

Claude MPM has a well-architected output style system with **OutputStyleManager** and **SystemInstructionsDeployer** handling deployment. The major gap is **teaching mode deployment** - PM_INSTRUCTIONS_TEACH.md exists but is not deployed anywhere.

**Recommended Next Steps**:
1. Extend OutputStyleManager to support multiple styles
2. Deploy PM_INSTRUCTIONS_TEACH.md as `claude-mpm-teach.md`
3. Add `--teach` CLI flag to activate teaching mode
4. Test on Claude Code 1.0.83+
5. Document style switching for users

**Estimated Effort**: 1-2 weeks for full implementation including CLI integration and testing.

---

**Research Complete**: 2025-12-09
**Files Analyzed**: 8 source files, 3 deployed directories
**Key Services**: OutputStyleManager, SystemInstructionsDeployer
**Major Finding**: Teaching mode exists but has no deployment mechanism
