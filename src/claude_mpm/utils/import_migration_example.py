"""Example of how to migrate duplicate import patterns to use safe_import.

This file demonstrates how to replace the common try/except ImportError
pattern with the new safe_import utility.
"""

# AFTER: Using safe_import utility
# --------------------------------
from claude_mpm.utils.imports import safe_import, safe_import_multiple

# Method 1: Individual imports
get_logger = safe_import("..utils.logger", "utils.logger", from_list=["get_logger"])
AgentRegistryAdapter = safe_import(
    "..core.agent_registry", "core.agent_registry", from_list=["AgentRegistryAdapter"]
)

# Method 2: Batch imports (recommended for multiple imports)
imports = safe_import_multiple(
    [
        ("..utils.logger", "utils.logger", ["get_logger"]),
        ("..core.agent_registry", "core.agent_registry", ["AgentRegistryAdapter"]),
    ]
)

get_logger = imports.get("get_logger")
AgentRegistryAdapter = imports.get("AgentRegistryAdapter")

# MIGRATION GUIDE
# ---------------

# BENEFITS
# --------
