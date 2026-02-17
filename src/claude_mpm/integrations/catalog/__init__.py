"""Integration catalog package.

This module provides the catalog of available integrations that can be
installed into projects. Each integration is defined by a YAML manifest
file in a subdirectory of this package.

ISS-0012: Create catalog structure
"""

from pathlib import Path

# Catalog directory path for scanning
CATALOG_DIR = Path(__file__).parent

__all__ = ["CATALOG_DIR"]
