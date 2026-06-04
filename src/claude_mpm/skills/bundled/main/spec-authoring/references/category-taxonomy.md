# Subsystem Taxonomy (Information Architecture)

How specs are organized into files, the existing subsystems, and the rule for deciding whether
new behavior is a **section** in an existing subsystem or a **new subsystem** (a new file).
This is the agent-facing copy of [`docs/specs/AUTHORING.md` §4](../../../../../../../docs/specs/AUTHORING.md).

> Terminology: in the spec ID grammar `SPEC-{SUBSYSTEM}-{NN}~{rev}`, the `{SUBSYSTEM}` token is
> the organizing unit. One subsystem = one file = one token. (Earlier drafts called this a
> "category"; the canonical word is **subsystem**, matching `docs/specs/README.md` §4.)

---

## 1. Two levels only

The information architecture is intentionally flat:

```
Subsystem (file)  →  numbered Sections (governed SPEC IDs)
```

- **Subsystem** = one bounded subsystem or domain = one file `docs/specs/{subsystem}.md`.
  The uppercased name is the `{SUBSYSTEM}` token in every ID declared in that file.
- **Section** = one governed `SPEC-{SUBSYSTEM}-{NN}~{rev}` unit, numbered sequentially within
  the file.

There is **no third level**. If a section seems to need its own sub-sections with their own
contracts, that is a signal to split it into sibling sections — not to nest.

---

## 2. claude-mpm's existing subsystems

The reference instantiation governs seven subsystems, one file each. New work should usually
land as a **section** in one of these:

| File | Token | Domain | Typical behaviors |
|------|-------|--------|-------------------|
| [`agents.md`](../../../../../../../docs/specs/agents.md) | `AGENTS` | Agent templates, assembly, deployment | Template assembly, frontmatter merge, deploy pipeline |
| [`cli.md`](../../../../../../../docs/specs/cli.md) | `CLI` | Click commands and interactive wizards | Command parsing, wizard flows, output formatting |
| [`hooks.md`](../../../../../../../docs/specs/hooks.md) | `HOOKS` | Hook handlers and enforcement | PreToolUse/PostToolUse, Stop, model-tier enforcement |
| [`integrations.md`](../../../../../../../docs/specs/integrations.md) | `INTEGRATIONS` | MCP servers, external services | MCP server contracts, external API adapters |
| [`manifest.md`](../../../../../../../docs/specs/manifest.md) | `MANIFEST` | Manifest, presets, model routing | Preset resolution, model-tier routing |
| [`sessions.md`](../../../../../../../docs/specs/sessions.md) | `SESSIONS` | Session lifecycle, runtime, persistence | Session start/resume/pause, state persistence |
| [`skills.md`](../../../../../../../docs/specs/skills.md) | `SKILLS` | Skill definitions, discovery, deployment | Discovery, validation, selective deployment |

When in doubt, open the candidate file and read its **Purpose & Scope**. If your behavior fits
that boundary statement, it is a section there.

---

## 3. Add a section vs. add a subsystem

### Default: add a section

Adding a numbered section to an existing subsystem file is the **common case**. Do this when the
new behavior belongs to a subsystem that already has a file. It costs nothing structurally:
append a `## {Title} {#SPEC-{SUBSYSTEM}-{NN+1}~1}` section and add a ToC row.

### Add a new subsystem only when ALL of these hold

1. **Bounded domain.** The behavior forms a cohesive subsystem with a clear boundary — not a
   feature of an existing one.
2. **Independent ownership / lifecycle.** It can be specced, reviewed, and versioned without
   churning an existing file.
3. **Several sections' worth.** It will hold more than one or two IDs. A single behavior is a
   *section*, never a subsystem.

If even one fails, prefer a section. **Subsystems are cheap to read but expensive to split
later** — IDs are stable and cannot be renamed without a supersession chain.

### Decision flow

```
New behavior to spec
        │
        ▼
Does an existing subsystem's Purpose & Scope cover it? ──yes──▶ add a SECTION there
        │ no
        ▼
Is it a bounded domain with independent lifecycle AND ≥3 sections' worth? ──no──▶ add a SECTION
        │ yes                                                                       to the nearest fit
        ▼
   add a NEW SUBSYSTEM file docs/specs/{subsystem}.md
```

---

## 4. Naming a subsystem

- **Token:** UPPERCASE alpha, hyphens allowed — `HOOKS`, `INTEGRATIONS`, a hypothetical
  `MODEL-ROUTING`. Matches the `{SUBSYSTEM}` slot in
  [`README.md` §4](../../../../../../../docs/specs/README.md).
- **File name:** the lowercase form of the token: `model-routing.md` ↔ `SPEC-MODEL-ROUTING-01~1`.
- **Durability:** the token appears in **every** ID and **every** docstring `References` line.
  Renaming it is a breaking change across the whole traceability graph. Choose a name you will
  not want to change.
- **Brevity:** keep it short. `SPEC-MODEL-ROUTING-01~1` is fine; `SPEC-MODEL-ROUTING-AND-PRESET-SELECTION-01~1`
  is a smell that you are bundling two subsystems.

---

## 5. Mapping product AREAs to engineering SUBSYSTEMs

PRDs are organized by product **AREA** (`PRD-{AREA}-{NN}`); specs are organized by engineering
**SUBSYSTEM** (`SPEC-{SUBSYSTEM}-{NN}~{rev}`). **These do not have to match 1:1** — and usually
do not:

- One product AREA (e.g. `PRD-SEARCH`) may be realized by several subsystems
  (`SPEC-INTEGRATIONS`, `SPEC-SESSIONS`).
- One subsystem (e.g. `SPEC-HOOKS`) may serve several product AREAs.

Organize specs by the **engineering boundary** (what changes together, what one team owns), not
by the product feature. Record the cross-mapping via the bidirectional links: the spec cites the
`PRD-{AREA}-{NN}` it realizes; the PRD lists the `SPEC-…` IDs in its *Linked Specs* table. See
[`docs/prd/README.md`](../../../../../../../docs/prd/README.md).

---

## 6. Common mistakes

| Mistake | Fix |
|---------|-----|
| Creating a new subsystem for a single behavior | Make it a section in the nearest existing subsystem. |
| Naming a subsystem after a product feature | Name it after the engineering boundary; link to the PRD AREA instead. |
| Renaming an existing token to "clean it up" | Don't. Renames break every docstring reference. Supersede instead. |
| Nesting sub-subsystems inside one file | Split into sibling sections, or a new subsystem if it meets all three criteria. |

---

## See also

- [`spec-template.md`](spec-template.md) — the per-section template once you have chosen the file.
- [`granularity-guide.md`](granularity-guide.md) — within a subsystem, how many IDs.
- [`docs/specs/AUTHORING.md` §4](../../../../../../../docs/specs/AUTHORING.md) — the authoritative IA rules.
