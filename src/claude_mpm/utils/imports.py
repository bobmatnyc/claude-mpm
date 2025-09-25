"""Import utilities for handling relative and absolute imports.

This module provides utilities to handle the common pattern of trying
relative imports first and falling back to absolute imports, which is
used throughout the claude_mpm codebase.
"""

import importlib
import logging
from typing import Any, List, Optional, Union


def safe_import(
    module_name: str,
    fallback_name: Optional[str] = None,
    from_list: Optional[List[str]] = None,
    logger: Optional[logging.Logger] = None,
) -> Optional[Any]:
    """
    Safely import a module with fallback support.

    Attempts to import a module using the primary module name first,
    then falls back to the fallback name if provided. This is useful
    for handling both relative and absolute imports.

    Args:
        module_name: Primary module name to import (e.g., '..utils.logger')
        fallback_name: Fallback module name if primary fails (e.g., 'utils.logger')
        from_list: List of names to import from the module (for 'from X import Y' style)
        logger: Optional logger for debugging import attempts

    Returns:
        The imported module or specific attribute(s) if from_list is provided.
        Returns None if all import attempts fail.

    Examples:
        # Import entire module
        logger_module = safe_import('..utils.logger', 'utils.logger')

        # Import specific function (returns the function directly)
        get_logger = safe_import('..utils.logger', 'utils.logger', ['get_logger'])

        # Import multiple items (returns tuple)
        logger, setup = safe_import('..utils.logger', 'utils.logger',
                                   ['get_logger', 'setup_logging'])
    """
    # Try primary import
    try:
        if logger:
            logger.debug(f"Attempting import: {module_name}")

        module = importlib.import_module(module_name)

        if from_list:
            # Handle 'from X import Y' style imports
            results = []
            for name in from_list:
                if hasattr(module, name):
                    results.append(getattr(module, name))
                else:
                    if logger:
                        logger.warning(f"Module {module_name} has no attribute {name}")
                    results.append(None)

            # Return single item if only one requested, otherwise tuple
            if len(results) == 1:
                return results[0]
            return tuple(results)

        return module

    except ImportError as e:
        if logger:
            logger.debug(f"Primary import failed: {e}")

        # Try fallback if provided
        if fallback_name:
            try:
                if logger:
                    logger.debug(f"Attempting fallback import: {fallback_name}")

                module = importlib.import_module(fallback_name)

                if from_list:
                    # Handle 'from X import Y' style imports
                    results = []
                    for name in from_list:
                        if hasattr(module, name):
                            results.append(getattr(module, name))
                        else:
                            if logger:
                                logger.warning(
                                    f"Module {fallback_name} has no attribute {name}"
                                )
                            results.append(None)

                    # Return single item if only one requested, otherwise tuple
                    if len(results) == 1:
                        return results[0]
                    return tuple(results)

                return module

            except ImportError as e2:
                if logger:
                    logger.debug(f"Fallback import also failed: {e2}")

    # All imports failed
    if logger:
        logger.error(
            f"Failed to import {module_name}"
            + (f" or {fallback_name}" if fallback_name else "")
        )

    return None


def safe_import_multiple(
    imports: List[Union[tuple, dict]], logger: Optional[logging.Logger] = None
) -> dict:
    """
    Import multiple modules with fallback support.

    Args:
        imports: List of import specifications. Each can be:
            - tuple: (primary_name, fallback_name, from_list)
            - dict: {'primary': '...', 'fallback': '...', 'from_list': [...], 'as': 'alias'}
        logger: Optional logger for debugging

    Returns:
        Dictionary mapping module/attribute names to imported objects

    Example:
        imports = [
            ('..utils.logger', 'utils.logger', ['get_logger']),
            {'primary': '..core.agent_registry', 'fallback': 'core.agent_registry',
             'from_list': ['AgentRegistry'], 'as': 'registry'}
        ]

        imported = safe_import_multiple(imports)
        # Result: {'get_logger': <function>, 'registry': <class>}
    """
    results = {}

    for spec in imports:
        if isinstance(spec, tuple):
            primary, fallback, from_list = spec
            imported = safe_import(primary, fallback, from_list, logger)

            if imported is not None:
                if from_list and len(from_list) == 1:
                    # Single import gets stored by its name
                    results[from_list[0]] = imported
                elif from_list and len(from_list) > 1:
                    # Multiple imports get unpacked
                    for i, name in enumerate(from_list):
                        if imported[i] is not None:
                            results[name] = imported[i]
                else:
                    # Module import gets stored by last part of module name
                    module_alias = primary.split(".")[-1]
                    results[module_alias] = imported

        elif isinstance(spec, dict):
            primary = spec.get("primary")
            fallback = spec.get("fallback")
            from_list = spec.get("from_list")
            alias = spec.get("as")

            imported = safe_import(primary, fallback, from_list, logger)

            if imported is not None:
                if alias:
                    results[alias] = imported
                elif from_list and len(from_list) == 1:
                    results[from_list[0]] = imported
                elif from_list and len(from_list) > 1:
                    for i, name in enumerate(from_list):
                        if imported[i] is not None:
                            results[name] = imported[i]
                else:
                    module_alias = primary.split(".")[-1]
                    results[module_alias] = imported

    return results
