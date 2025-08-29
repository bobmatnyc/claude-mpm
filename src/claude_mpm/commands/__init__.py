"""
Commands package for Claude MPM.

This module contains command documentation files (Markdown) that are accessed
via importlib.resources.path() for command help and reference material.

This __init__.py file is required to make this directory recognizable as a
Python package by setuptools, which is necessary for proper distribution
and importlib resource access in installed packages.

Without this file, importlib.resources.path("claude_mpm", "commands") would
fail in the distributed package, even though it works in development when
the package is installed in editable mode.
"""
