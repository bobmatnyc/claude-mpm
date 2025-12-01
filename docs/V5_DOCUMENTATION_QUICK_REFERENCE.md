# Claude MPM v5.0 Documentation Quick Reference

**Created:** 2025-12-01
**Purpose:** Fast-access reference for documentation work
**See Also:** [V5_DOCUMENTATION_PLAN.md](V5_DOCUMENTATION_PLAN.md)

---

## 🚨 Critical Publishing Blockers (4-6 hours)

These MUST be complete before v5.0 release:

### 1. Auto-Configuration Guide (2-3 hours)
**File:** `docs/user/auto-configuration.md`

**Quick Template:**
```markdown
# Auto-Configuration

## Overview
- What: Automatic project stack detection and agent deployment
- Why: Save time, get best-practice agent configurations
- When: New projects, standardizing teams

## Quick Start
```bash
claude-mpm agents detect
claude-mpm agents recommend
claude-mpm agents auto-configure
```

## Detected Technologies
[List all 8 languages + frameworks]

## Use Cases
[4-5 real scenarios]

## vs Presets vs Manual
[Comparison table]

## Troubleshooting
[6+ common issues]
```

**Must Include:**
- Complete technology detection list
- Confidence threshold explanation
- 5+ workflow examples
- Comparison with presets
- Links to slash command docs

---

### 2. Agent Presets Guide (1-2 hours)
**File:** `docs/user/agent-presets.md`

**Quick Template:**
```markdown
# Agent Presets

## Overview
- What: Pre-configured agent bundles for common stacks
- Why: Instant deployment, best practices included
- When: Known stack, quick setup, team standards

## Quick Start
```bash
claude-mpm agents deploy --preset python-dev
claude-mpm agents deploy --list-presets
```

## All 11 Presets
[Document each preset with agents, use cases, ideal for]

## Choosing a Preset
[Decision matrix]

## vs Auto-Configure
[Comparison table]
```

**Must Include:**
- All 11 presets fully documented
- Use cases for each
- Decision guidance
- Examples for top 5 presets

---

### 3. CLI Reference Update (1 hour)
**File:** `docs/reference/cli-agents.md`

**Add These Commands:**
```bash
# agents detect
claude-mpm agents detect [OPTIONS]
  --path PATH           Project directory
  --output FORMAT       text|json|yaml
  --debug              Debug mode

# agents recommend
claude-mpm agents recommend [OPTIONS]
  --threshold INT       Confidence 0-100
  --preview            Show without deploying
  --output FORMAT      text|json

# agents deploy --preset
claude-mpm agents deploy --preset NAME
  --list-presets       Show available presets
```

**Must Include:**
- All flags explained
- Examples for each command
- Links to user guides

---

### 4. Slash Command Integration (30 minutes)
**File:** `docs/reference/slash-commands.md`

**Add Section:**
```markdown
## Auto-Configuration Commands

### /mpm-agents-detect
Scan project for technologies.
See: [Auto-Configuration Guide](../user/auto-configuration.md)

### /mpm-agents-recommend
Get agent recommendations.
See: [Auto-Configuration Guide](../user/auto-configuration.md)

### /mpm-agents-auto-configure
Full auto-configuration workflow.
See: [Auto-Configuration Guide](../user/auto-configuration.md)

## Detailed Command Docs
- [mpm-agents-detect.md](../../src/claude_mpm/commands/mpm-agents-detect.md)
- [mpm-agents-recommend.md](../../src/claude_mpm/commands/mpm-agents-recommend.md)
```

---

## ⚠️ High-Value Post-Release (Week 1)

### 5. PR Workflow Guide (30 minutes)
**Source:** `docs/research/agent-skill-pr-workflow-2025-12-01.md`
**Target:** `docs/guides/contributing-agents-skills.md`

**Actions:**
1. Copy research doc
2. Remove: Research headers, internal metrics, performance data
3. Keep: PR workflow, contribution guide, testing
4. Add: Quick start for contributors, checklists

---

### 6. Documentation Index (1-2 hours)
**File:** `docs/INDEX.md`

**Structure:**
```markdown
# Documentation Index

## Getting Started
- [Getting Started](user/getting-started.md)
- [Installation](user/installation.md)
- [Quick Start](user/quickstart.md)

## Core Features (v5.0)
- [Auto-Configuration](user/auto-configuration.md) ✨ NEW
- [Agent Presets](user/agent-presets.md) ✨ NEW
- [Agent Sources](user/agent-sources.md) ✨ NEW
- [Skills Guide](user/skills-guide.md)

## Reference
- [CLI Reference](reference/cli-agents.md)
- [API Reference](reference/agent-sources-api.md)
- [Slash Commands](reference/slash-commands.md)

## Guides
- [Contributing Agents/Skills](guides/contributing-agents-skills.md)
- [Troubleshooting](user/troubleshooting.md)
```

---

### 7. Update Getting Started (1 hour)
**File:** `docs/user/getting-started.md`

**Expand These Sections:**
1. **Auto-Configuration** (currently 13 lines → 50 lines)
   - Detailed examples
   - Expected output
   - Link to guide

2. **Agent Presets** (NEW section, 40 lines)
   - Quick examples
   - All 11 presets listed
   - When to use

3. **What's Next** (update with v5.0 focus)
   - Prioritize auto-configure
   - Suggest presets
   - Link to new guides

---

### 8. README.md Update (30 minutes)
**File:** `README.md` (root)

**Add Sections:**
```markdown
## ✨ New in v5.0
- Auto-Configuration
- Agent Presets (11 bundles)
- Git-Based Sources
- Performance Improvements

## Quick Start
```bash
# Auto-configure
claude-mpm agents auto-configure

# Or use preset
claude-mpm agents deploy --preset python-dev
```
```

---

## Content Standards Cheat Sheet

### User Guide Must Have:
- ✅ Overview (what/why/when) 300-400 words
- ✅ Quick start (<5 minutes)
- ✅ Detailed walkthrough
- ✅ 3-5 use cases
- ✅ Troubleshooting (6+ issues)
- ✅ 5+ working examples
- ✅ Cross-references

### Reference Doc Must Have:
- ✅ Command syntax
- ✅ All parameters explained
- ✅ Examples for each command
- ✅ Error conditions
- ✅ Cross-references

### Example Format:
```markdown
**Scenario:** [What user wants to do]

```bash
[Exact command]
```

**Expected Output:**
```
[Actual or representative output]
```

**Explanation:** [Why it works]

**Variations:** [Alternative approaches]
```

---

## Technology Lists

### Auto-Configuration Detects:

**Languages:**
- Python 3.8+
- JavaScript/TypeScript
- Go
- Rust
- PHP
- Ruby
- Java
- C/C++

**Frameworks:**
- **Python:** FastAPI, Django, Flask
- **JavaScript:** Express.js, Fastify, Koa, Next.js, React, Vue
- **Go:** Gin, Echo
- **Rust:** Actix, Rocket
- **PHP:** Laravel, Symfony
- **Ruby:** Rails

**Tools:**
- Docker, Kubernetes
- PostgreSQL, MongoDB, Redis
- pytest, Jest, Playwright
- Webpack, Vite
- GitHub Actions, CircleCI

---

## Agent Presets (All 11)

1. **minimal** (6 agents) - Any project
2. **python-dev** (8 agents) - Python backend
3. **python-fullstack** (12 agents) - Python + React
4. **javascript-backend** (8 agents) - Node.js
5. **react-dev** (9 agents) - React frontend
6. **nextjs-fullstack** (13 agents) - Next.js
7. **rust-dev** (8 agents) - Rust
8. **golang-dev** (8 agents) - Go
9. **java-dev** (9 agents) - Java/Spring
10. **mobile-flutter** (10 agents) - Flutter
11. **data-eng** (11 agents) - Data pipelines

---

## File Locations Quick Reference

### Source Files (read from here):
- Preset definitions: `/Users/masa/Projects/claude-mpm/src/claude_mpm/config/agent_presets.py`
- Slash commands: `/Users/masa/Projects/claude-mpm/src/claude_mpm/commands/*.md`
- Auto-config impl: `/Users/masa/Projects/claude-mpm/src/claude_mpm/services/agents/auto_config_manager.py`

### Target Documentation Files (write to here):
- Auto-config guide: `/Users/masa/Projects/claude-mpm/docs/user/auto-configuration.md` (NEW)
- Presets guide: `/Users/masa/Projects/claude-mpm/docs/user/agent-presets.md` (NEW)
- CLI reference: `/Users/masa/Projects/claude-mpm/docs/reference/cli-agents.md` (UPDATE)
- Slash commands: `/Users/masa/Projects/claude-mpm/docs/reference/slash-commands.md` (UPDATE)
- Getting started: `/Users/masa/Projects/claude-mpm/docs/user/getting-started.md` (UPDATE)
- README: `/Users/masa/Projects/claude-mpm/README.md` (UPDATE)
- Index: `/Users/masa/Projects/claude-mpm/docs/INDEX.md` (NEW)

### Research to Promote:
- PR workflow: `/Users/masa/Projects/claude-mpm/docs/research/agent-skill-pr-workflow-2025-12-01.md`
  → `/Users/masa/Projects/claude-mpm/docs/guides/contributing-agents-skills.md`

---

## Validation Commands

```bash
# Check file sizes
ls -lh docs/user/*.md

# Find broken links
find docs -name "*.md" -exec grep -l "\[.*\](.*\.md)" {} \;

# Count examples in file
grep -c "```bash" docs/user/auto-configuration.md

# List all cross-references
grep -n "See:" docs/user/*.md
```

---

## Time Estimates by Task

| Task | Time | Priority |
|------|------|----------|
| Auto-configuration guide | 2-3h | 🚨 CRITICAL |
| Agent presets guide | 1-2h | 🚨 CRITICAL |
| CLI reference update | 1h | 🚨 CRITICAL |
| Slash command integration | 30m | 🚨 CRITICAL |
| PR workflow promotion | 30m | ⚠️ HIGH |
| Documentation index | 1-2h | ⚠️ HIGH |
| Getting started update | 1h | ⚠️ HIGH |
| README update | 30m | ⚠️ HIGH |

**Total Critical Path:** 4-6 hours
**Total High Priority:** 4-6 hours

---

## Quality Checklist

Before marking a document complete:

**Content:**
- [ ] All sections present
- [ ] Examples tested
- [ ] Cross-references added
- [ ] Troubleshooting complete

**Quality:**
- [ ] Clear writing
- [ ] Active voice
- [ ] Consistent terms
- [ ] Proper headings

**Integration:**
- [ ] Links work
- [ ] Navigation clear
- [ ] Version info current

---

## Publishing Decision

**Ready to Publish When:**
- ✅ Auto-configuration guide complete (Section 1.1)
- ✅ Agent presets guide complete (Section 1.2)
- ✅ CLI reference updated (Section 1.3)
- ✅ Slash commands integrated (Section 1.4)
- ✅ All examples tested
- ✅ All links working
- ✅ Peer review passed

**Can Wait Until Post-Release:**
- ⚠️ PR workflow guide
- ⚠️ Documentation index
- ⚠️ Getting started expansion
- ⚠️ Research doc promotions
- ⚠️ Cross-linking audit
- ⚠️ Example gallery

---

## Contact

**For Questions:**
- Technical: Engineer Agents
- Content: Documentation Agent
- Review: PM Agent

**Related Plans:**
- Complete plan: [V5_DOCUMENTATION_PLAN.md](V5_DOCUMENTATION_PLAN.md)
- Research audit: [research/v5-documentation-audit-2025-12-01.md](research/v5-documentation-audit-2025-12-01.md)

---

**End of Quick Reference**
