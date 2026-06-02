"""
claude_mpm.quality — Code-quality analysis tools.

WHAT: Exposes static analysis utilities that operate on the claude_mpm source
tree without importing it.  The primary entry point is the WWL (WHAT/WHY/LINK)
granularity checker in :mod:`claude_mpm.quality.wwl_checker`.

WHY: Grouping quality tooling under a dedicated sub-package keeps it clearly
separate from runtime code and lets CI, pre-commit hooks, and tests import it
without side effects.
"""
