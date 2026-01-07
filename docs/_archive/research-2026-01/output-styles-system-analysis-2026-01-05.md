---
title: Claude MPM Output Styles System Analysis
date: 2026-01-05
researcher: Claude Code Research Agent
status: Completed
tags: [output-styles, architecture, claude-code, founders-style]
purpose: Comprehensive analysis of output styles system for creating new "founders" style
---

# Claude MPM Output Styles System Analysis

## Executive Summary

The Claude MPM output styles system provides a flexible framework for defining custom communication styles that Claude Code uses when responding. This research documents the complete architecture, file formats, and implementation patterns needed to create a new "founders" output style.

**Key Findings:**
- Output styles are Markdown files with YAML frontmatter stored in `~/.claude/output-styles/`
- Two existing styles: `professional` (Claude MPM) and `teaching` (Claude MPM Teacher)
- Activation managed via `~/.claude/settings.json` with `activeOutputStyle` field
- Recommended size: under 10,000 characters (~2,857 tokens) for optimal performance
- Complete automated deployment system handles version detection and activation

---

## 1. Output Style File Locations

### Source Files (Package)

Located in: `/Users/masa/Projects/claude-mpm/src/claude_mpm/agents/`

```
CLAUDE_MPM_OUTPUT_STYLE.md          # Professional mode (12KB, 4,174 chars)
CLAUDE_MPM_TEACHER_OUTPUT_STYLE.md  # Teaching mode (condensed, 4,796 chars)
```

### Deployment Target (User-Level)

Located in: `~/.claude/output-styles/`

```
claude-mpm.md          # Deployed professional style
claude-mpm-teacher.md  # Deployed teaching style
```

**Why User-Level?** Claude Code reads output styles from `~/.claude/output-styles/` directory, making them available globally across all projects.

---

## 2. Output Style Format & Structure

### YAML Frontmatter (Required)

```yaml
---
name: Claude MPM
description: Multi-Agent Project Manager orchestration mode with mandatory delegation
---
```

**Required Fields:**
- `name`: Display name shown in Claude Code UI (matches `activeOutputStyle` in settings.json)
- `description`: Brief explanation of the style's purpose

**Optional Fields:**
- `keep-coding-instructions: true` - Include Claude Code's default coding instructions
- Custom metadata fields (not used by Claude Code but can be informative)

### Content Structure

The Markdown content after the frontmatter defines the communication style and behavior guidelines.

**Professional Style (claude-mpm.md) Structure:**
```markdown
# Claude Multi-Agent PM

## 🔴 PRIMARY DIRECTIVE - MANDATORY DELEGATION
[Core rules and constraints]

## Core Rules
[Numbered list of essential behaviors]

## Allowed Tools
[Tool usage guidelines]

## Communication
[Tone, language, and response format]

## Error Handling
[3-attempt process with escalation]

## Standard Operating Procedure
[5-phase workflow]

## TodoWrite Framework
[Task tracking conventions]

## PM Response Format
[Structured JSON summary template]

## Detailed Workflows
[References to PM skills for complex patterns]
```

**Key Structural Patterns:**
1. **Clear Hierarchy**: Use headers (`##`, `###`) for organization
2. **Visual Markers**: Emojis or symbols for emphasis (🔴, ✅, ❌)
3. **Lists**: Bullet points and numbered lists for clarity
4. **Code Blocks**: Examples in triple backticks
5. **References**: Link to external skills/docs for detailed content

---

## 3. Output Style Manager Architecture

### Core Class: `OutputStyleManager`

**File**: `/Users/masa/Projects/claude-mpm/src/claude_mpm/core/output_style_manager.py`

```python
class OutputStyleManager:
    """Manages output style deployment and version-based handling.

    Supports two output styles:
    - professional: Default Claude MPM style (claude-mpm.md)
    - teaching: Adaptive teaching mode (claude-mpm-teacher.md)
    """

    def __init__(self):
        self.output_style_dir = Path.home() / ".claude" / "output-styles"
        self.settings_file = Path.home() / ".claude" / "settings.json"

        # Style definitions
        self.styles: Dict[str, StyleConfig] = {
            "professional": StyleConfig(
                source=Path(__file__).parent.parent / "agents" / "CLAUDE_MPM_OUTPUT_STYLE.md",
                target=self.output_style_dir / "claude-mpm.md",
                name="Claude MPM",
            ),
            "teaching": StyleConfig(
                source=Path(__file__).parent.parent / "agents" / "CLAUDE_MPM_TEACHER_OUTPUT_STYLE.md",
                target=self.output_style_dir / "claude-mpm-teacher.md",
                name="Claude MPM Teacher",
            ),
        }
```

### Key Methods

#### 1. `deploy_output_style(content, style, activate)`
Deploys a style file and optionally activates it.

```python
def deploy_output_style(
    self,
    content: Optional[str] = None,
    style: OutputStyleType = "professional",
    activate: bool = True,
) -> bool:
    """Deploy output style to Claude Code if version >= 1.0.83."""
```

#### 2. `_activate_output_style(style_name)`
Updates `~/.claude/settings.json` to activate a style.

```python
def _activate_output_style(self, style_name: str = "Claude MPM") -> bool:
    """Update Claude Code settings to activate a specific output style."""
    settings = {}
    if self.settings_file.exists():
        settings = json.loads(self.settings_file.read_text())

    current_style = settings.get("activeOutputStyle")

    if current_style != style_name:
        settings["activeOutputStyle"] = style_name
        self.settings_file.write_text(json.dumps(settings, indent=2))
        self.logger.info(f"✅ Activated {style_name} output style")
```

#### 3. `deploy_all_styles(activate_default)`
Deploys all configured styles to `~/.claude/output-styles/`.

```python
def deploy_all_styles(self, activate_default: bool = True) -> Dict[str, bool]:
    """Deploy all available output styles to Claude Code."""
```

#### 4. `supports_output_styles()`
Checks if Claude Code version supports output styles (>= 1.0.83).

```python
def supports_output_styles(self) -> bool:
    """Check if Claude Code supports output styles (>= 1.0.83)."""
    if not self.claude_version:
        return False
    return self._compare_versions(self.claude_version, "1.0.83") >= 0
```

---

## 4. Deployment & Activation Flow

### Startup Deployment

**File**: `/Users/masa/Projects/claude-mpm/src/claude_mpm/cli/startup.py`

**Function**: `deploy_output_style_on_startup()` (lines 303-381)

```python
def deploy_output_style_on_startup():
    """Deploy claude-mpm output styles to PROJECT-LEVEL directory on CLI startup.

    Deploys two styles:
    - claude-mpm.md (professional mode)
    - claude-mpm-teacher.md (teaching mode)
    """
    # Source files (in framework package)
    package_dir = Path(__file__).parent.parent / "agents"
    professional_source = package_dir / "CLAUDE_MPM_OUTPUT_STYLE.md"
    teacher_source = package_dir / "CLAUDE_MPM_TEACHER_OUTPUT_STYLE.md"

    # Target directory (USER-LEVEL for global availability)
    output_styles_dir = Path.home() / ".claude" / "output-styles"
    professional_target = output_styles_dir / "claude-mpm.md"
    teacher_target = output_styles_dir / "claude-mpm-teacher.md"

    # Create directory if needed
    output_styles_dir.mkdir(parents=True, exist_ok=True)

    # Check if already deployed and up-to-date (size comparison)
    # ... deployment logic ...
```

**When It Runs:** Every `mpm` command execution via `run_background_services()` (line 1271)

**What It Does:**
1. Copies style files from package to `~/.claude/output-styles/`
2. Checks file sizes to detect updates
3. Prints status: `✓ Output styles ready` or `✓ Output styles deployed (N styles)`

**What It Doesn't Do:** Activate the style (set `activeOutputStyle` in settings.json)

### Interactive Session Deployment

**File**: `/Users/masa/Projects/claude-mpm/src/claude_mpm/core/claude_runner.py`

**Method**: `_deploy_output_style()` (lines 705-789)

```python
def _deploy_output_style(self) -> None:
    """Deploy output style with version-aware logic."""
    # Check if already active
    settings = {}
    if output_style_manager.settings_file.exists():
        settings = json.loads(output_style_manager.settings_file.read_text())

    current_style = settings.get("activeOutputStyle")

    # Early return if already active and file exists
    if (current_style == "Claude MPM" and
        output_style_manager.output_style_path.exists()):
        return

    # Deploy and activate
    deployed = output_style_manager.deploy_output_style(
        output_style_content,
        activate=True  # Activates via _activate_output_style()
    )
```

**When It Runs:** During `ClaudeRunner.__init__()` (line 195) when running `mpm run`

**What It Does:**
1. Checks if style already active in settings.json
2. If not active, deploys file AND activates it
3. Logs activation: `✅ Activated Claude MPM output style`

---

## 5. Settings File Integration

### Location
`~/.claude/settings.json`

### Key Field: `activeOutputStyle`

```json
{
  "statusLine": { ... },
  "alwaysThinkingEnabled": true,
  "activeOutputStyle": "Claude MPM",  // <-- Output style name
  "permissions": { ... },
  "hooks": { ... }
}
```

**Value:** Must match the `name` field in the style's YAML frontmatter.

**Examples:**
- `"Claude MPM"` → Activates `claude-mpm.md`
- `"Claude MPM Teacher"` → Activates `claude-mpm-teacher.md`
- `"default"` → Uses Claude Code's default style
- `null` or missing → Uses Claude Code's default style

### Activation Logic

```python
# From output_style_manager.py:303-349
current_style = settings.get("activeOutputStyle")

if current_style != style_name:
    settings["activeOutputStyle"] = style_name
    self.settings_file.write_text(json.dumps(settings, indent=2))
    self.logger.info(f"✅ Activated {style_name} output style")
else:
    self.logger.debug(f"{style_name} output style already active")
```

---

## 6. Existing Output Styles as Templates

### Professional Style: `CLAUDE_MPM_OUTPUT_STYLE.md`

**Purpose:** Strict PM delegation mode with mandatory agent routing

**Size:** 4,174 characters (~1,192 tokens)

**Key Sections:**
1. **PRIMARY DIRECTIVE**: Absolute rules with override phrases
2. **Core Rules**: 5 non-negotiable behaviors
3. **Allowed Tools**: Explicit tool allowlist
4. **Communication**: Professional, neutral tone guidelines
5. **Error Handling**: 3-attempt escalation process
6. **Standard Operating Procedure**: 5-phase workflow
7. **TodoWrite Framework**: Task tracking conventions
8. **PM Response Format**: JSON summary template

**Structural Highlights:**
- Heavy use of emojis for visual emphasis (🔴, ✅, ❌)
- Clear hierarchy with headers and subheaders
- Bullet lists for rules
- Code blocks for JSON examples
- References to external PM skills for detailed workflows

**Code Example:**
```markdown
## 🔴 PRIMARY DIRECTIVE - MANDATORY DELEGATION

**YOU ARE STRICTLY FORBIDDEN FROM DOING ANY WORK DIRECTLY.**

You are a PROJECT MANAGER whose SOLE PURPOSE is to delegate work to specialized agents.

**Override phrases** (required for direct action):
- "do this yourself" | "don't delegate" | "implement directly"
```

### Teaching Style: `CLAUDE_MPM_TEACHER_OUTPUT_STYLE.md`

**Purpose:** Adaptive teaching overlay on correct PM workflow

**Size:** 4,796 characters (~1,370 tokens)

**Key Sections:**
1. **Core Philosophy**: Socratic method, progressive disclosure
2. **Experience Detection**: Beginner, intermediate, advanced
3. **Teaching Behaviors**: 5 teaching patterns
4. **Adaptive Responses**: Experience-level adjustments
5. **Error Handling Template**: Teaching moment format
6. **Graduation System**: Proficiency tracking
7. **Communication Style**: Supportive language guidelines
8. **Integration with PM Mode**: Teaching as overlay
9. **Configuration**: YAML config example

**Structural Highlights:**
- Code blocks for templates and examples
- Emoji indicators (🎓, 💡, ✅, 🔍, 🎉)
- Progressive disclosure patterns
- Clear integration instructions
- References to external `pm-teaching-mode` skill

**Code Example:**
```markdown
### 3. "Watch Me Work" Pattern
```
🎓 **Watch Me Work: Delegation**

You asked: "verify auth bug in JJF-62"

**My Analysis**:
1. Need ticket details → Ticketing Agent
2. Auth bugs need code review → Engineer
3. Verification needs QA → QA Agent

**Strategy**: Ticketing → analyze → Engineer → QA verifies
**Circuit Breaker**: Cannot use mcp-ticketer directly. Must delegate.

**Delegating to Ticketing Agent**...
```
```

---

## 7. Size Considerations & Best Practices

### Recommended Sizes

Based on [research findings](claude-code-output-style-limits-2025-12-31.md):

| Size | Characters | Tokens | Recommendation |
|------|-----------|--------|----------------|
| **Optimal** | < 2,000 | ~571 | Community best practice |
| **Acceptable** | < 10,000 | ~2,857 | Condensed for performance |
| **Large** | 12,000 | ~3,429 | Current professional style |
| **Very Large** | 50,000+ | ~14,286+ | Not recommended |

**Current Styles:**
- Professional: 4,174 chars (~1,192 tokens) - Well optimized ✅
- Teaching: 4,796 chars (~1,370 tokens) - Well optimized ✅

### Why Size Matters

1. **Context Window Consumption**: Every request includes the full output style in the system prompt
2. **Adherence Issues**: Larger styles may be partially ignored by Claude
3. **Performance Impact**: Higher latency and API costs
4. **Maintainability**: Harder to update and understand

### Optimization Strategies

1. **Remove redundant content**: Identify overlapping instructions
2. **Prioritize core functionality**: Keep only essential behaviors
3. **Use concise language**: Eliminate verbose explanations
4. **Reference external docs**: Link to detailed guides instead of including full text
5. **Leverage CLAUDE.md**: Move project-specific context to CLAUDE.md instead of output style

---

## 8. How to Create a New Output Style

### Step 1: Create Source File

**Location:** `/Users/masa/Projects/claude-mpm/src/claude_mpm/agents/CLAUDE_MPM_FOUNDERS_OUTPUT_STYLE.md`

**Template:**
```markdown
---
name: Claude MPM Founders
description: Founders-focused communication style with business context
---

# Claude MPM Founders Mode

## Core Philosophy

[Define the core purpose and principles]

## Communication Style

[Define tone, language, and formatting preferences]

## Decision Framework

[Provide decision-making guidelines]

## Reporting Format

[Define how to structure responses]

## Business Context Integration

[How to incorporate business metrics and strategy]

## Next Steps Format

[How to present actionable next steps]
```

### Step 2: Update OutputStyleManager

**File:** `/Users/masa/Projects/claude-mpm/src/claude_mpm/core/output_style_manager.py`

**Add to `styles` dictionary (line 59-74):**

```python
self.styles: Dict[str, StyleConfig] = {
    "professional": StyleConfig(
        source=Path(__file__).parent.parent / "agents" / "CLAUDE_MPM_OUTPUT_STYLE.md",
        target=self.output_style_dir / "claude-mpm.md",
        name="Claude MPM",
    ),
    "teaching": StyleConfig(
        source=Path(__file__).parent.parent / "agents" / "CLAUDE_MPM_TEACHER_OUTPUT_STYLE.md",
        target=self.output_style_dir / "claude-mpm-teacher.md",
        name="Claude MPM Teacher",
    ),
    "founders": StyleConfig(  # NEW STYLE
        source=Path(__file__).parent.parent / "agents" / "CLAUDE_MPM_FOUNDERS_OUTPUT_STYLE.md",
        target=self.output_style_dir / "claude-mpm-founders.md",
        name="Claude MPM Founders",
    ),
}
```

**Update type hint (line 30):**
```python
OutputStyleType = Literal["professional", "teaching", "founders"]
```

### Step 3: Update Startup Deployment

**File:** `/Users/masa/Projects/claude-mpm/src/claude_mpm/cli/startup.py`

**Modify `deploy_output_style_on_startup()` (lines 303-381):**

```python
def deploy_output_style_on_startup():
    # ... existing code ...

    # Add source file
    founders_source = package_dir / "CLAUDE_MPM_FOUNDERS_OUTPUT_STYLE.md"

    # Add target file
    founders_target = output_styles_dir / "claude-mpm-founders.md"

    # Check if up-to-date
    founders_up_to_date = (
        founders_target.exists()
        and founders_source.exists()
        and founders_target.stat().st_size == founders_source.stat().st_size
    )

    if professional_up_to_date and teacher_up_to_date and founders_up_to_date:
        print("✓ Output styles ready", flush=True)
        return

    # Deploy founders style
    if founders_source.exists():
        shutil.copy2(founders_source, founders_target)
        deployed_count += 1
```

### Step 4: Add Deployment Method (Optional)

**File:** `/Users/masa/Projects/claude-mpm/src/claude_mpm/core/output_style_manager.py`

**Add convenience method:**
```python
def deploy_founders_style(self, activate: bool = False) -> bool:
    """Deploy the founders style specifically.

    Args:
        activate: Whether to activate the founders style after deployment

    Returns:
        True if deployed successfully, False otherwise
    """
    return self.deploy_output_style(style="founders", activate=activate)
```

### Step 5: Test Deployment

```bash
# 1. Run any mpm command to deploy files
mpm --version

# 2. Check if file was deployed
ls -la ~/.claude/output-styles/claude-mpm-founders.md

# 3. Manually activate the style
# Edit ~/.claude/settings.json
jq '.activeOutputStyle = "Claude MPM Founders"' ~/.claude/settings.json > tmp.json
mv tmp.json ~/.claude/settings.json

# 4. Verify activation
cat ~/.claude/settings.json | jq .activeOutputStyle
# Should output: "Claude MPM Founders"

# 5. Test in Claude Code
# Open Claude Code and observe the communication style
```

### Step 6: Programmatic Activation

If you want to activate the founders style programmatically:

```python
from claude_mpm.core.output_style_manager import OutputStyleManager

manager = OutputStyleManager()
if manager.supports_output_styles():
    # Deploy and activate
    success = manager.deploy_output_style(style="founders", activate=True)
    print(f"Founders style {'activated' if success else 'failed'}")
```

---

## 9. Testing & Verification

### Verification Checklist

- [ ] Source file exists: `src/claude_mpm/agents/CLAUDE_MPM_FOUNDERS_OUTPUT_STYLE.md`
- [ ] File has valid YAML frontmatter with `name` and `description`
- [ ] Content is under 10,000 characters
- [ ] Added to `OutputStyleManager.styles` dictionary
- [ ] Updated `OutputStyleType` type hint
- [ ] Updated `deploy_output_style_on_startup()` function
- [ ] Deployed file exists: `~/.claude/output-styles/claude-mpm-founders.md`
- [ ] Settings file contains: `"activeOutputStyle": "Claude MPM Founders"`
- [ ] Claude Code recognizes the style in UI
- [ ] Communication follows defined style guidelines

### Testing Commands

```bash
# Check version detection
python -c "from claude_mpm.core.output_style_manager import OutputStyleManager; m = OutputStyleManager(); print(f'Version: {m.claude_version}, Supports: {m.supports_output_styles()}')"

# Check style configuration
python -c "from claude_mpm.core.output_style_manager import OutputStyleManager; m = OutputStyleManager(); import json; print(json.dumps(m.list_available_styles(), indent=2))"

# Deploy specific style
python -c "from claude_mpm.core.output_style_manager import OutputStyleManager; m = OutputStyleManager(); success = m.deploy_output_style(style='founders', activate=True); print(f'Success: {success}')"

# Check active style
cat ~/.claude/settings.json | jq .activeOutputStyle
```

### Test Scenarios

1. **Fresh Installation**: Remove `~/.claude/output-styles/` and run `mpm --version`
2. **Update Detection**: Modify source file, run `mpm --version`, verify file updated
3. **Activation**: Manually change `activeOutputStyle`, run `mpm run`, verify re-activation
4. **Style Switching**: Switch between professional, teaching, and founders styles
5. **Communication Verification**: Test Claude Code responses follow style guidelines

---

## 10. Code Examples & Patterns

### Example: Business-Focused Founders Style

```markdown
---
name: Claude MPM Founders
description: Business-focused communication for founders and executives
---

# Claude MPM Founders Mode

## Core Philosophy

You are communicating with founders and business leaders who value:
- **Strategic clarity**: Big picture before details
- **Business impact**: ROI and competitive advantage
- **Time efficiency**: Concise, actionable insights
- **Risk awareness**: Clear trade-offs and mitigations

## Communication Style

### Structure
1. **Executive Summary**: 2-3 sentences (what, why, impact)
2. **Business Context**: Market position, competitive analysis
3. **Recommendations**: Prioritized action items with ROI estimates
4. **Technical Details**: Available on request, not by default
5. **Next Steps**: Clear ownership and timelines

### Language
- **Use**: "revenue impact", "competitive advantage", "time to market"
- **Avoid**: Technical jargon without business translation
- **Format**: Bullet points for scannability
- **Metrics**: Focus on business KPIs (CAC, LTV, churn, conversion)

## Decision Framework

When presenting options:
1. **Business Case**: Expected ROI and timeline
2. **Resource Requirements**: Cost, time, team bandwidth
3. **Risk Assessment**: What could go wrong and impact
4. **Strategic Alignment**: How it supports company goals
5. **Recommendation**: Clear guidance with reasoning

## Reporting Format

```json
{
  "executive_summary": "One-line business impact",
  "recommendations": [
    {
      "action": "Clear next step",
      "business_impact": "Revenue/growth/efficiency gain",
      "effort": "time estimate",
      "priority": "high/medium/low",
      "owner": "role or team"
    }
  ],
  "risks": ["risk 1", "risk 2"],
  "technical_details": "Available in follow-up"
}
```

## Business Context Integration

Always consider:
- **Stage**: Pre-seed, seed, Series A-D, etc.
- **Market**: Industry, competition, trends
- **Constraints**: Budget, team size, runway
- **Goals**: Growth, efficiency, market position

## Next Steps Format

```
## Immediate Actions (This Week)
1. [Action] - Owner: [Role] - Impact: [Business metric]

## Short-Term (This Month)
1. [Action] - Owner: [Role] - Impact: [Business metric]

## Strategic (This Quarter)
1. [Action] - Owner: [Role] - Impact: [Business metric]
```
```

### Example: CLI Command Integration

```python
# Add CLI command to switch styles
# File: src/claude_mpm/cli/commands/style.py

import click
from claude_mpm.core.output_style_manager import OutputStyleManager

@click.command()
@click.argument('style', type=click.Choice(['professional', 'teaching', 'founders']))
@click.option('--activate/--no-activate', default=True, help='Activate after deployment')
def style(style, activate):
    """Deploy and optionally activate an output style."""
    manager = OutputStyleManager()

    if not manager.supports_output_styles():
        click.echo("⚠️  Claude Code version < 1.0.83 does not support output styles")
        return

    click.echo(f"Deploying {style} style...")
    success = manager.deploy_output_style(style=style, activate=activate)

    if success:
        if activate:
            click.echo(f"✅ {style.capitalize()} style deployed and activated")
        else:
            click.echo(f"✅ {style.capitalize()} style deployed")
    else:
        click.echo(f"❌ Failed to deploy {style} style")
```

---

## 11. Related Files & Dependencies

### Core Files
- `/Users/masa/Projects/claude-mpm/src/claude_mpm/core/output_style_manager.py` - Main manager class
- `/Users/masa/Projects/claude-mpm/src/claude_mpm/cli/startup.py` - Startup deployment
- `/Users/masa/Projects/claude-mpm/src/claude_mpm/core/claude_runner.py` - Interactive session deployment
- `/Users/masa/Projects/claude-mpm/src/claude_mpm/agents/CLAUDE_MPM_OUTPUT_STYLE.md` - Professional style source
- `/Users/masa/Projects/claude-mpm/src/claude_mpm/agents/CLAUDE_MPM_TEACHER_OUTPUT_STYLE.md` - Teaching style source

### Configuration Files
- `~/.claude/settings.json` - Claude Code settings with `activeOutputStyle`
- `~/.claude/output-styles/` - Deployed output style files

### Test Files
- `/Users/masa/Projects/claude-mpm/tests/test_output_style_enforcement.py`
- `/Users/masa/Projects/claude-mpm/tests/test_output_style_simplified.py`
- `/Users/masa/Projects/claude-mpm/tests/test_output_style_system.py`
- `/Users/masa/Projects/claude-mpm/tests/test_output_style_display.py`

### Documentation
- `/Users/masa/Projects/claude-mpm/docs/_archive/research-2025/output-style-configuration-analysis-2025-01-05.md`
- `/Users/masa/Projects/claude-mpm/docs/_archive/research-2025/claude-code-output-style-limits-2025-12-31.md`

---

## 12. Recommendations for "Founders" Style

### Content Guidelines

1. **Executive Summary First**: Lead with business impact
2. **Business Metrics**: Use ROI, CAC, LTV, churn, conversion
3. **Strategic Context**: Market position, competitive landscape
4. **Risk Assessment**: Clear trade-offs and mitigations
5. **Action Items**: Prioritized with ownership and timelines

### Size Target

- **Optimal**: 4,000-6,000 characters (~1,143-1,714 tokens)
- **Maximum**: 10,000 characters (~2,857 tokens)

### Structural Elements

```markdown
# Claude MPM Founders Mode

## Core Philosophy [300 chars]
[Define purpose and principles]

## Communication Style [600 chars]
[Structure, language, formatting]

## Decision Framework [500 chars]
[How to present options and recommendations]

## Reporting Format [800 chars]
[JSON template with business-focused fields]

## Business Context Integration [400 chars]
[Stage, market, constraints, goals]

## Next Steps Format [400 chars]
[Immediate, short-term, strategic actions]
```

**Total: ~3,000 characters** (leaves room for examples and details)

### Differentiation from Professional Style

| Aspect | Professional | Founders |
|--------|-------------|----------|
| **Audience** | Technical PM | Business leaders |
| **Focus** | Agent delegation | Business impact |
| **Language** | Engineering terms | Business metrics |
| **Structure** | Workflow phases | Executive summary first |
| **Details** | Technical accuracy | Strategic clarity |
| **Metrics** | Task completion | ROI, market impact |

---

## 13. Next Steps

### Implementation Plan

1. **Draft Content** (2-3 hours)
   - Write CLAUDE_MPM_FOUNDERS_OUTPUT_STYLE.md
   - Use professional style as structural template
   - Focus on business-centric language and metrics
   - Target 4,000-6,000 characters

2. **Update Code** (30 minutes)
   - Add to OutputStyleManager.styles dictionary
   - Update OutputStyleType type hint
   - Modify deploy_output_style_on_startup()
   - Add deploy_founders_style() method (optional)

3. **Test Deployment** (15 minutes)
   - Run `mpm --version` to deploy files
   - Verify file in `~/.claude/output-styles/`
   - Check available styles with list_available_styles()

4. **Manual Activation** (5 minutes)
   - Edit `~/.claude/settings.json`
   - Set `activeOutputStyle` to `"Claude MPM Founders"`
   - Verify in Claude Code UI

5. **Validation** (30 minutes)
   - Test Claude Code responses follow style
   - Compare with professional style behavior
   - Adjust content based on observations

6. **Documentation** (15 minutes)
   - Update README or docs with new style
   - Document when to use founders style
   - Provide activation instructions

### Success Criteria

- [ ] Source file < 10,000 characters
- [ ] Valid YAML frontmatter
- [ ] Deploys automatically on `mpm` commands
- [ ] Activates correctly via settings.json
- [ ] Claude Code recognizes style
- [ ] Responses follow business-focused guidelines
- [ ] Users can switch between styles
- [ ] Style persists across Claude Code restarts

---

## 14. Conclusion

The Claude MPM output styles system provides a robust, flexible framework for defining custom communication styles. Key takeaways:

1. **Simple Format**: Markdown with YAML frontmatter
2. **Automated Deployment**: Handled by startup and interactive session flows
3. **Version-Aware**: Detects Claude Code version and adapts
4. **Easy to Extend**: Add new styles by creating file and updating config
5. **Size Matters**: Keep under 10,000 characters for optimal performance
6. **Activation is Key**: Must set `activeOutputStyle` in settings.json

**For Founders Style Specifically:**
- Focus on business impact and strategic clarity
- Use executive summary structure
- Include business metrics (ROI, CAC, LTV)
- Provide clear action items with ownership
- Target 4,000-6,000 characters
- Follow the patterns established by professional and teaching styles

The existing professional and teaching styles provide excellent templates for structure, formatting, and tone. The founders style should maintain the same technical quality while shifting focus to business value and strategic decision-making.

---

## Appendix: Quick Reference

### File Paths
```
Source: src/claude_mpm/agents/CLAUDE_MPM_FOUNDERS_OUTPUT_STYLE.md
Target: ~/.claude/output-styles/claude-mpm-founders.md
Settings: ~/.claude/settings.json
Manager: src/claude_mpm/core/output_style_manager.py
Startup: src/claude_mpm/cli/startup.py
```

### Key Commands
```bash
# Deploy styles
mpm --version

# Check active style
cat ~/.claude/settings.json | jq .activeOutputStyle

# List available styles
python -c "from claude_mpm.core.output_style_manager import OutputStyleManager; m = OutputStyleManager(); print(m.list_available_styles())"

# Activate founders style
jq '.activeOutputStyle = "Claude MPM Founders"' ~/.claude/settings.json > tmp.json && mv tmp.json ~/.claude/settings.json
```

### Configuration Example
```python
"founders": StyleConfig(
    source=Path(__file__).parent.parent / "agents" / "CLAUDE_MPM_FOUNDERS_OUTPUT_STYLE.md",
    target=self.output_style_dir / "claude-mpm-founders.md",
    name="Claude MPM Founders",
)
```

---

**Research Complete** | Ready for implementation of founders output style.
