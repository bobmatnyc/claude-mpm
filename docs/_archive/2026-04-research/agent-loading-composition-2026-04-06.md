# Agent Loading and Composition Research
Date: 2026-04-06
Topic: How agents are loaded and composed — for implementing progressive disclosure via on-demand skills

---

## Summary

Agents in claude-mpm are composed at **deploy time** (not runtime) by `AgentTemplateBuilder.build_agent_markdown()`. The deployed `.claude/agents/*.md` file is the fully assembled product — frontmatter + agent body + BASE-AGENT.md hierarchy + memory instructions. Skills are NOT inlined into agent body; they are separate directory packages in `.claude/skills/` that Claude Code loads on demand via slash command triggers. The `skills:` list in the frontmatter is used by `SelectiveSkillDeployer` to decide which skill directories to deploy, but the skill content itself stays external.

---

## 1. Agent Loader: `get_agent_prompt()`

**Primary entry point:** `src/claude_mpm/agents/agent_loader.py`

Key functions:
- `get_agent_prompt(agent_name, ...)` (line 793) — public API; normalizes name, calls `load_agent_prompt_from_md()`
- `load_agent_prompt_from_md(agent_name, ...)` (line 615) — calls `AgentLoader.get_agent_prompt()`
- `AgentLoader.get_agent_prompt(agent_id, ...)` (line 255) — reads `.md` file body via `_extract_md_body()`
- `AgentLoader._extract_md_body(content)` (line 314) — strips YAML frontmatter, returns only the markdown body after the closing `---`

Flow: The loader reads the **already-deployed** `.claude/agents/<agent-id>.md` file. It strips the YAML frontmatter and returns the body. The prompt returned is the body text only — not the frontmatter.

**Skills are NOT loaded or inlined here.** Skills exist separately in `.claude/skills/`.

---

## 2. Agent Deployment: How the `.md` File Is Assembled

**Primary assembler:** `src/claude_mpm/services/agents/deployment/agent_template_builder.py`

Key class: `AgentTemplateBuilder`

**`build_agent_markdown(agent_name, template_path, base_agent_data, source_info)`** (line 397)

Assembly order:
1. Parse template (`.md` or `.json` from `~/.claude-mpm/cache/agents/`)
2. Build YAML frontmatter with: `name`, `description`, `model`, `agent_type`, `color`, `version`, `author`, `tags`, **`skills:`** list, `initialPrompt`
3. Get `instructions` from template data (the agent-specific markdown body)
4. **Discover BASE-AGENT.md hierarchy** via `_discover_base_agent_templates(template_path)` — walks up directory tree from agent file, collects all `BASE-AGENT.md` files (closest-first)
5. Compose: `[agent_specific_instructions] + [local BASE-AGENT.md] + [parent BASE-AGENT.md] + ...`
6. Join all parts with `"\n\n---\n\n"` separator
7. If no hierarchical BASE found: fall back to legacy `BASE_{TYPE}.md` file
8. Append memory-update instructions if not already present
9. Return: `frontmatter + content`

**Frontmatter field preservation:** The deployed file gets a **complete copy of the source template frontmatter**, including all fields the caller passes through. Notably, the `AgentTemplateBuilder` only outputs these frontmatter fields (lines 618-677):
```
name, description, model, agent_type, color, category, version, author, created_at, updated_at, tags, skills, initialPrompt
```

**What gets stripped vs preserved:** Looking at the deployed `python-engineer.md` vs source, the file is actually a **direct copy** in the new "simplified architecture" (multi-source deployment). `MultiSourceAgentDeploymentService` selects the highest-version agent file and copies it. `AgentTemplateBuilder.build_agent_markdown()` is only invoked for legacy JSON templates or when explicitly needed.

For markdown-source agents (the new format), the source `.md` file from cache is effectively the deployed file — frontmatter is preserved in full, including `template_changelog`, `dependencies`, `knowledge`, `interactions`, `memory_routing` etc.

---

## 3. Skill Loading: How Skills Get Included

**Key service:** `src/claude_mpm/services/skills/selective_skill_deployer.py`

Skills are **NOT inlined** into agent body content. They are:
- Separate directories in `~/.claude/skills/<skill-name>/` (user-level) or `.claude/skills/<skill-name>/` (project-level)
- Each skill has a `SKILL.md` file that Claude Code reads when triggered by slash command

**How skill requirements are discovered:**
1. `get_required_skills_from_agents(agents_dir)` scans `*.md` files in `.claude/agents/`
2. Source 1: parses `skills:` list from YAML frontmatter via `parse_agent_frontmatter()` + `get_skills_from_agent()`
3. Source 2: scans content body for `[SKILL: skill-name]` inline markers via `extract_skills_from_content()`
4. Combines both sets → deploys matching skill directories

**Skill loading at runtime:** Claude Code itself handles this — when a slash command like `/systematic-debugging` is invoked, Claude Code loads the SKILL.md from `.claude/skills/systematic-debugging/SKILL.md`. The skills are loaded on-demand, not preloaded with the agent.

**`skills:` in frontmatter** = deployment manifest only (tells `SelectiveSkillDeployer` which skills to deploy). It does NOT cause skills to be loaded into agent context at startup.

---

## 4. Current Deployed Agent Sizes

From `wc -c .claude/agents/*.md | sort -n | tail -20`:
```
19,980  javascript-engineer.md
20,060  version-control.md
20,432  vercel-ops.md
21,527  tauri-engineer.md
22,118  data-engineer.md
22,537  react-engineer.md
23,653  content.md
27,084  web-qa.md
30,668  security.md
33,599  product-owner.md
33,624  web-ui-engineer.md / web-ui.md
36,626  nestjs-engineer.md
39,239  mpm-agent-manager.md
44,445  java-engineer.md
45,381  python-engineer.md
49,359  ticketing.md
59,200  research.md
62,175  mpm-skills-manager.md
963,238 total (all agents combined)
```

---

## 5. Frontmatter Fields in Agent Definitions

From `python-engineer.md` analysis:
- **Frontmatter size:** 8,732 bytes (of 45,381 total = 19%)
- **Body size:** 36,578 bytes

Fields present in source (and preserved in deployed file):
```yaml
name, description, version, schema_version, agent_id, agent_type,
resource_tier, tags, category, color, author, temperature, max_tokens,
timeout, capabilities, dependencies, skills, template_version,
template_changelog, knowledge, interactions, memory_routing
```

**Strippable at deploy time (bloat):**

| Field | Size | Notes |
|-------|------|-------|
| `template_changelog` | ~2,003 bytes | 7 changelog entries — only useful for developers, not Claude runtime |
| `dependencies` | ~248 bytes | Python/system package requirements — metadata only, Claude doesn't use these |
| `knowledge` | unknown | Template scaffolding data used only during JSON template build |
| `interactions` | unknown | Trigger patterns — used during agent selection, not runtime |
| `memory_routing` | unknown | Memory system hints |
| `schema_version` | tiny | Version number for template schema |
| `template_version` | tiny | Duplicate of `version` |

**Must preserve:**
- `name`, `description` — Claude Code discovery
- `model` — model selection
- `skills` — selective skill deployment
- `agent_type` — categorization
- `initialPrompt` — auto-start delegation

---

## 6. Where to Strip Frontmatter Bloat

**Point of intervention:** `SingleAgentDeployer.deploy_single_agent()` in `src/claude_mpm/services/agents/deployment/single_agent_deployer.py` (line 96-102)

Currently:
```python
agent_content = self.template_builder.build_agent_markdown(
    agent_name, template_file, base_agent_data, source_info
)
target_file.write_text(agent_content)
```

For `.md`-format source files (the new architecture), the file is copied directly via `MultiSourceAgentDeploymentService`. The copy path is in `src/claude_mpm/services/agents/deployment/agent_merger.py` and friends — the agent content is written without transformation for `.md` files.

**Best stripping location:** A post-process step after `build_agent_markdown()` (or after source `.md` selection) that parses frontmatter, removes unneeded keys, and rewrites the file.

---

## 7. Progressive Disclosure: Replacing Inline Content with Skill References

**Current state:** Skills are already external (no inlining). The `skills:` field in frontmatter is a list of skill names — those skill directories are deployed and loaded on-demand by Claude Code.

**What does NOT yet exist:**
- No mechanism to have agent body content loaded on-demand — the entire body of the deployed `.md` file is loaded into Claude's context when an agent runs
- The agent body (36KB for python-engineer) is fully loaded as instructions

**How to implement progressive disclosure for agent body:**
1. Agent body sections could reference skills: `**[SKILL: section-name]**` markers
2. Each heavy section (e.g., "AsyncWorkerPool patterns", "Testing Philosophy") becomes a skill file
3. The agent body becomes lightweight references; Claude loads skills on-demand via `/skill-name` or when the topic is triggered

**Existing mechanism:** The `[SKILL: skill-name]` marker pattern is already recognized by `extract_skills_from_content()` for deployment purposes. Claude Code supports loading skills on-demand via slash commands. The infrastructure exists — only the agent authoring conventions need to change.

---

## 8. Key File Paths

| Purpose | Path |
|---------|------|
| Main agent loader | `src/claude_mpm/agents/agent_loader.py` |
| Template builder (assembly) | `src/claude_mpm/services/agents/deployment/agent_template_builder.py` |
| Single agent deployer | `src/claude_mpm/services/agents/deployment/single_agent_deployer.py` |
| Multi-source deployment | `src/claude_mpm/services/agents/deployment/multi_source_deployment_service.py` |
| Selective skill deployer | `src/claude_mpm/services/skills/selective_skill_deployer.py` |
| Profile loader (loading tier) | `src/claude_mpm/services/agents/loading/agent_profile_loader.py` |
| Framework agent loader | `src/claude_mpm/services/agents/loading/framework_agent_loader.py` |
| Agent cache (~cache) | `~/.claude-mpm/cache/agents/github-remote/claude-mpm-agents/agents/` |
| Deployed agents | `.claude/agents/*.md` |
| Deployed skills (user) | `~/.claude/skills/<skill-name>/SKILL.md` |
| Deployed skills (project) | `.claude/skills/<skill-name>/SKILL.md` |

---

## 9. Actionable Recommendations for Progressive Disclosure

**Option A: Strip frontmatter bloat at deploy time**
- Location: Add a `_strip_deploy_frontmatter(content)` step in `SingleAgentDeployer.deploy_single_agent()` (after build, before write)
- Strip: `template_changelog`, `dependencies`, `knowledge`, `interactions`, `memory_routing`, `schema_version`, `template_version`
- Estimated savings: ~2,500 bytes per agent (5-6% of python-engineer), much more on others
- Risk: Low — these fields are not used by Claude runtime

**Option B: Move agent body sections to skills**
- Convert heavy agent body sections into skill packages
- Agent body becomes lightweight with `[SKILL: topic-name]` references
- Skills deployed to `.claude/skills/` and loaded on-demand
- Estimated savings: 50-80% of body size
- Risk: Medium — requires agent template refactoring; skill load latency

**Option C: Progressive frontmatter (lazy fields)**
- Store full metadata in a sidecar file; deploy minimal frontmatter to `.claude/agents/`
- Minimal frontmatter: `name`, `description`, `model`, `skills`, `initialPrompt`
- Full metadata in `.claude-mpm/agent-metadata/<name>.yaml`
- Risk: Low — Claude Code only reads the `.md` file, doesn't need sidecar

**Recommendation:** Start with Option A (strip deploy-time bloat) for quick wins, then pursue Option B for the large agents (research.md at 59KB, mpm-skills-manager.md at 62KB).
