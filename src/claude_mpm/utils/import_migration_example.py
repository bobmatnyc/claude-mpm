"""Example of how to migrate duplicate import patterns to use safe_import.

This file demonstrates how to replace the common try/except ImportError
pattern with the new safe_import utility.
"""

# BEFORE: The old pattern used throughout the codebase
# -----------------------------------------------------
# try:
#     from ..core.logger import get_logger
# except ImportError:
#     from utils.logger import get_logger
#
# try:
#     from ..core.agent_registry import AgentRegistryAdapter
# except ImportError:
#     from core.agent_registry import AgentRegistryAdapter


# AFTER: Using safe_import utility
# --------------------------------
from claude_mpm.utils.imports import safe_import, safe_import_multiple

# Method 1: Individual imports
get_logger = safe_import('..utils.logger', 'utils.logger', from_list=['get_logger'])
AgentRegistryAdapter = safe_import('..core.agent_registry', 'core.agent_registry', 
                                  from_list=['AgentRegistryAdapter'])

# Method 2: Batch imports (recommended for multiple imports)
imports = safe_import_multiple([
    ('..utils.logger', 'utils.logger', ['get_logger']),
    ('..core.agent_registry', 'core.agent_registry', ['AgentRegistryAdapter']),
])

get_logger = imports.get('get_logger')
AgentRegistryAdapter = imports.get('AgentRegistryAdapter')


# MIGRATION GUIDE
# ---------------
# 1. Add import: from claude_mpm.utils.imports import safe_import
# 
# 2. Replace try/except blocks:
#    FROM:
#      try:
#          from ..module import something
#      except ImportError:
#          from module import something
#    
#    TO:
#      something = safe_import('..module', 'module', from_list=['something'])
#
# 3. For multiple imports from same module:
#    FROM:
#      try:
#          from ..module import foo, bar, baz
#      except ImportError:
#          from module import foo, bar, baz
#    
#    TO:
#      foo, bar, baz = safe_import('..module', 'module', from_list=['foo', 'bar', 'baz'])
#
# 4. For whole module imports:
#    FROM:
#      try:
#          from .. import module
#      except ImportError:
#          import module
#    
#    TO:
#      module = safe_import('..module', 'module')


# BENEFITS
# --------
# 1. Reduces code duplication (97 files can be simplified)
# 2. Centralizes import error handling logic
# 3. Provides optional logging for debugging import issues
# 4. Maintains the same functionality with cleaner code
# 5. Makes the codebase more maintainable