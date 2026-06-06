# PM Instruction Files: Roles and Ownership

Two auto-generated files appear in `~/.claude-mpm/` (or `.claude-mpm/` inside a
project).  They are **intentionally created by claude-mpm** and carry an
`AUTO-GENERATED — DO NOT EDIT` banner at the top.  Editing them by hand is
futile: they are overwritten on every startup.

---

## PM_INSTRUCTIONS_DEPLOYED.md

| Property | Detail |
|---|---|
| **Written by** | `SystemInstructionsDeployer.deploy_system_instructions()` in `src/claude_mpm/services/agents/deployment/system_instructions_deployer.py` |
| **When** | Rebuilt on **every startup** (`_rebuild_pm_instructions_deployed` in the agent deployment service) |
| **Location** | `.claude-mpm/PM_INSTRUCTIONS_DEPLOYED.md` (project-local) |
| **Used in** | Dev / filesystem mode (when the package is not installed from PyPI) |
| **Contents** | Merged composition of four framework blocks, in order: `PM_INSTRUCTIONS.md`, `AGENT_DELEGATION.md`, `WORKFLOW.md`, `MEMORY.md` |

### How the blocks are resolved

Each block is resolved with additive override semantics:

1. User override (`~/.claude-mpm/<BLOCK>.md`) — highest priority
2. Project override (`.claude-mpm/<BLOCK>.md`) — appended after user override
3. System default (`src/claude_mpm/agents/<BLOCK>.md`) — used only when neither override exists

`WORKFLOW.md` uses a lazy-load variant: the system default is represented by a
compact reference stub (`WORKFLOW_SYSTEM_REFERENCE`) rather than inlining the
full ~1,150-token file; user/project overrides are always inlined verbatim.

### How to customise

Edit the **source** files, not the deployed file:

```
~/.claude-mpm/PM_INSTRUCTIONS.md   # user-level override
.claude-mpm/PM_INSTRUCTIONS.md     # project-level override
```

See also `src/claude_mpm/agents/BASE_PM.md` for the full customisation table
and `docs/customization/pm-override-system.md` for detailed instructions.

---

## PM_INSTRUCTIONS.md (the launcher cache)

| Property | Detail |
|---|---|
| **Written by** | `InstructionCacheService.update_cache()` in `src/claude_mpm/services/instructions/instruction_cache_service.py` |
| **When** | Rebuilt when the assembled instruction content changes (SHA-256 hash-based invalidation) |
| **Location** | `.claude-mpm/PM_INSTRUCTIONS.md` (project-local) |
| **Used in** | All launch modes — the launcher reads this file instead of passing the full prompt on the CLI (avoids Linux `ARG_MAX` limits for ~450 KB payloads) |
| **Contents** | Full assembled prompt: `BASE_PM.md` + `PM_INSTRUCTIONS.md` (source block) + `WORKFLOW.md` + agent capabilities section + temporal/session context |

### Hash-based invalidation

The cache service hashes only the **caller-supplied instruction content** (the
assembled body without the banner).  The banner is prepended to the file on
disk but is deliberately excluded from the hash, so the banner never causes
spurious cache rewrites on repeated startups with identical content.

The metadata file (`.claude-mpm/PM_INSTRUCTIONS.md.meta`) stores the SHA-256
hash, content size, component list, and a `cached_at` timestamp.

### How to customise

The launcher cache reflects whatever the assembler produces.  To change the
final prompt, edit the **source instruction blocks** (`BASE_PM.md`,
`PM_INSTRUCTIONS.md`, etc.) rather than this file.  The cache will be
automatically invalidated and rebuilt on the next startup.

---

## Side-by-side comparison

| | `PM_INSTRUCTIONS_DEPLOYED.md` | `PM_INSTRUCTIONS.md` (cache) |
|---|---|---|
| Role | Merged framework composition | Final assembled launcher cache |
| Contains temporal context | No | Yes |
| Rebuilt | Every startup | When content hash changes |
| Read by | Dev / filesystem mode | All launch modes |
| Source files | 4 framework blocks | `BASE_PM` + blocks + capabilities + context |
| Should hand-edit? | **No** | **No** |

---

## If you see these files and are confused

They are working as intended.  The `AUTO-GENERATED` banner at the top of each
file explains this.  If you want to influence what ends up in either file,
edit the source `.md` files listed above — changes take effect at the next
session startup.
