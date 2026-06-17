"""Mutation testing framework service.

WHAT: Public surface for the mutation testing service — re-exports the mutmut
      runner and its result dataclasses.
WHY:  Phase 1 de-risking slice. The mutmut interface is the riskiest component
      (mutmut 2.5.1 has two Python 3.13 bugs), so it ships as a standalone,
      importable runner before any CLI command, parser, or agent wiring.

References
----------
LINK: none  (feature introduced in this PR, tracked in GitHub issue #853)
"""

from __future__ import annotations

from claude_mpm.services.mutation.runner import (
    MutantSurvivor,
    MutationResult,
    run_mutation,
)

__all__ = ["MutantSurvivor", "MutationResult", "run_mutation"]
