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
