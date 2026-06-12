"""Shared constants for WORKFLOW.md lazy-loading.

This module is intentionally minimal — it has no imports from other
claude_mpm subpackages — so that both the core instruction loader and the
services-layer deployer can import it without introducing circular
dependencies.
"""

# Reference stub injected in place of the full system-level WORKFLOW.md.
# Both InstructionLoader (core) and SystemInstructionsDeployer (services)
# must use this *exact* string so the deployed PM_INSTRUCTIONS_DEPLOYED.md
# and the live assembled prompt stay in sync.
WORKFLOW_SYSTEM_REFERENCE = (
    "Full workflow detail: see `src/claude_mpm/agents/WORKFLOW.md` "
    "(also at `docs/workflow/PM_WORKFLOW.md`). "
    "Read on demand only when full phase detail is needed."
)

# Reference stub injected in place of the full system-level MEMORY.md.
# Mirrors WORKFLOW_SYSTEM_REFERENCE: both InstructionLoader (core) and
# SystemInstructionsDeployer (services) must use this *exact* string so the
# deployed PM_INSTRUCTIONS_DEPLOYED.md and the live assembled prompt stay in
# sync.  The stub preserves memory-trigger awareness (trigger phrases +
# categories + storage tool) so the PM never misses a trigger even though the
# full MEMORY.md (~1,776 tokens) is no longer embedded — it can be Read on
# demand.
MEMORY_SYSTEM_REFERENCE = (
    "## Memory System\n\n"
    'On memory triggers ("remember", "note that", "don\'t forget", "always", '
    '"never", "keep in mind", project standards) store the fact via '
    "`mcp__trusty-memory__memory_remember` and/or the static "
    "`.claude-mpm/memories/{agent}_memories.md` files. "
    "Categorise as decisions / gotchas / patterns / environment. "
    "Full detail (file format, trim rules, trusty-memory tagging, dual-system "
    "routing): see `src/claude_mpm/agents/MEMORY.md` — Read on demand."
)
