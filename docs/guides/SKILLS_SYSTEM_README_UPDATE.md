# Suggested README.md Update for Skills System

## Location
After line 28 (after "Remote Agent Sync" feature), add:

```markdown
- 🎯 **Skills System**: Git-based skill discovery and management for extending agent capabilities
  - **Priority-Based Resolution**: Manage conflicts with configurable priorities
  - **Automatic Caching**: Skills cached locally for performance
  - **Built-in Diagnostics**: Health checks via `claude-mpm doctor`
  - **System Repository**: Curated skills from https://github.com/bobmatnyc/claude-mpm-skills
```

## Alternative (More Detailed)

If you want to expand the existing "Skills System" line (line 18):

**Current:**
```markdown
- 🎯 **Skills System**: 21 bundled skills with auto-linking, three-tier organization (bundled/user/project), and interactive configuration
```

**Suggested Update:**
```markdown
- 🎯 **Skills System**: Git-based skill discovery with priority-based resolution
  - **Multiple Sources**: System repository + custom Git repositories
  - **Priority Resolution**: Configure which skills override others
  - **Automatic Sync**: ETag-based caching with incremental updates
  - **Built-in Diagnostics**: `claude-mpm doctor` validates configuration
  - **21+ Bundled Skills**: Auto-linked skills for agents (bundled/user/project organization)
```

## New Section: Skills System Quick Start

Add after "Quick Installation" section (around line 150):

```markdown
## Skills System Quick Start

Claude MPM includes a Git-based skills system for extending agent capabilities.

### List Skill Sources

```bash
# View configured skill repositories
claude-mpm skill-source list
```

### Add Custom Skills

```bash
# Add your organization's skill repository
claude-mpm skill-source add https://github.com/myorg/skills --priority 50

# Sync skills from all repositories
claude-mpm skill-source update
```

### Verify Skills

```bash
# Check skill sources health
claude-mpm doctor

# View cached skills
ls -la ~/.claude-mpm/cache/skills/
```

**Learn More:**
- 📖 [Skills System User Guide](docs/guides/skills-system.md)
- 🔧 [Skills API Reference](docs/reference/skills-api.md)
```

## Features Section Enhancement

If you want to add more detail to the Features section, update line 18:

**Current:**
```markdown
- 🎯 **Skills System**: 21 bundled skills with auto-linking, three-tier organization (bundled/user/project), and interactive configuration
```

**Enhanced:**
```markdown
- 🎯 **Skills System**: Extend agent capabilities through Git-based skill repositories
  - **System Repository**: 25+ curated skills from claude-mpm-skills
  - **Custom Sources**: Add organization/team skill repositories
  - **Priority Resolution**: Lower priority = higher precedence (0-1000)
  - **Auto-Sync**: ETag-based caching for efficient updates
  - **Doctor Integration**: 8 diagnostic checks for skill sources
```

## Choose One Approach

**Recommendation**: Use the "Alternative (More Detailed)" update on line 18 + add the "Skills System Quick Start" section. This provides:
1. Clear feature description in the main list
2. Practical quick start guide for users
3. Links to detailed documentation

**Minimal Approach**: Just add the brief update to line 28 in the features list.

---

**Note**: The existing line 18 mentions "21 bundled skills" which appears to be a different system (bundled skills vs. Git-based skills system). You may want to clarify or consolidate these descriptions.
