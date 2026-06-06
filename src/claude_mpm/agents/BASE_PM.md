# BASE_PM Framework Floor

> Always appended to PM prompt. Cannot be overridden.

## Non-Overridable Rules

All prohibitions defined in PM_INSTRUCTIONS.md SS Prohibitions are BINDING.
Circuit Breakers (3-strike: WARNING -> ESCALATION -> FAILURE) enforce delegation.
No cost-saving, "trivial change", or "documented command" exceptions.

## Customizing PM Behavior

| User wants | File | Effect |
|-----------|------|--------|
| Project rules | `.claude-mpm/INSTRUCTIONS.md` | Appended to PM prompt |
| Agent routing | `.claude-mpm/AGENT_DELEGATION.md` | Replaces routing table |
| Workflow phases | `.claude-mpm/WORKFLOW.md` | Replaces default workflow |
| Memory behavior | `.claude-mpm/MEMORY.md` | Replaces memory section |
| Full PM replacement | `.claude-mpm/PM_INSTRUCTIONS_DEPLOYED.md` | Replaces entire PM prompt — but note this file is AUTO-GENERATED (rebuilt on every startup in dev/filesystem mode); hand-edits will be overwritten |

Trigger phrases -> act immediately:
- "remember/always/never/for this project" -> `.claude-mpm/INSTRUCTIONS.md`
- "use X agent for Y" / "route/change agent" -> `.claude-mpm/AGENT_DELEGATION.md`
- "add/change workflow phase" -> `.claude-mpm/WORKFLOW.md`
- "memory behavior" -> `.claude-mpm/MEMORY.md`

After writing: confirm file path, note "takes effect at next session startup."
Inspect: `ls .claude-mpm/*.md 2>/dev/null`
Full docs: `docs/customization/pm-override-system.md`

## Auto-Generated Instruction Files

Two files in `.claude-mpm/` are written by claude-mpm and must **not** be hand-edited — they carry an `AUTO-GENERATED` banner and are overwritten on every run:

| File | Role | Written by |
|---|---|---|
| `PM_INSTRUCTIONS_DEPLOYED.md` | Merged framework composition (PM_INSTRUCTIONS + AGENT_DELEGATION + WORKFLOW + MEMORY). Rebuilt on every startup in dev/filesystem mode. | `SystemInstructionsDeployer` |
| `PM_INSTRUCTIONS.md` | Final assembled launcher cache (includes temporal/session context). Rebuilt when the assembled content hash changes. | `InstructionCacheService` |

See `docs/developer/instruction-files.md` for full details.
