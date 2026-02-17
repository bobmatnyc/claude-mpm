"""Catalog index generator (Phase 3).

Generates _index.yaml from catalog integrations for discovery and CI validation.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path  # noqa: TC003 - used at runtime
from typing import Any

import yaml

from .manifest import IntegrationManifest


class CatalogIndexGenerator:
    """Generates _index.yaml from catalog integrations.

    The index provides a machine-readable manifest of all available
    integrations in the catalog, including metadata for discovery.
    """

    def scan_catalog(self, catalog_dir: Path) -> list[dict[str, Any]]:
        """Scan catalog directory for integrations.

        Args:
            catalog_dir: Path to the catalog directory.

        Returns:
            List of integration metadata dictionaries.
        """
        integrations: list[dict[str, Any]] = []

        for item in sorted(catalog_dir.iterdir()):
            # Skip non-directories and special files
            if not item.is_dir():
                continue
            if item.name.startswith(("_", ".", "ci")):
                continue

            manifest_path = item / "integration.yaml"
            if not manifest_path.exists():
                continue

            try:
                manifest = IntegrationManifest.from_yaml(manifest_path)
                integrations.append(
                    {
                        "name": manifest.name,
                        "version": manifest.version,
                        "description": manifest.description,
                        "api_type": manifest.api_type,
                        "auth_type": manifest.auth.type,
                        "operations_count": len(manifest.operations),
                        "author": manifest.author,
                        "repository": manifest.repository,
                    }
                )
            except Exception:  # nosec B112
                # Skip invalid manifests during scan
                continue

        return integrations

    def generate_index(self, catalog_dir: Path) -> str:
        """Generate _index.yaml content.

        Args:
            catalog_dir: Path to the catalog directory.

        Returns:
            YAML string content for _index.yaml.
        """
        integrations = self.scan_catalog(catalog_dir)

        index_data = {
            "# Auto-generated catalog index": None,
            "# DO NOT EDIT - run 'mpm integrate rebuild-index' to regenerate": None,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "version": "1.0",
            "total_count": len(integrations),
            "integrations": integrations,
        }

        # Build YAML with comments at top
        header = (
            "# Auto-generated catalog index\n"
            "# DO NOT EDIT - run 'mpm integrate rebuild-index' to regenerate\n\n"
        )

        # Remove the comment keys from the data
        clean_data = {
            "generated_at": index_data["generated_at"],
            "version": index_data["version"],
            "total_count": index_data["total_count"],
            "integrations": index_data["integrations"],
        }

        return header + yaml.safe_dump(
            clean_data,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
        )

    def write_index(self, catalog_dir: Path) -> Path:
        """Write _index.yaml to catalog directory.

        Args:
            catalog_dir: Path to the catalog directory.

        Returns:
            Path to the written _index.yaml file.
        """
        content = self.generate_index(catalog_dir)
        index_path = catalog_dir / "_index.yaml"

        index_path.write_text(content, encoding="utf-8")
        return index_path

    def verify_index(self, catalog_dir: Path) -> tuple[bool, list[str]]:
        """Verify _index.yaml is up to date with catalog contents.

        Args:
            catalog_dir: Path to the catalog directory.

        Returns:
            Tuple of (is_valid, list of discrepancies).
        """
        index_path = catalog_dir / "_index.yaml"
        discrepancies: list[str] = []

        if not index_path.exists():
            return False, ["_index.yaml does not exist"]

        try:
            with index_path.open(encoding="utf-8") as f:
                existing = yaml.safe_load(f)
        except Exception as e:
            return False, [f"Failed to parse _index.yaml: {e}"]

        # Scan current catalog
        current = self.scan_catalog(catalog_dir)
        existing_integrations = existing.get("integrations", [])

        # Build lookup maps
        current_map = {i["name"]: i for i in current}
        existing_map = {i["name"]: i for i in existing_integrations}

        # Check for missing integrations
        for name in current_map:
            if name not in existing_map:
                discrepancies.append(f"Missing from index: {name}")

        # Check for extra integrations
        for name in existing_map:
            if name not in current_map:
                discrepancies.append(f"Extra in index (no longer in catalog): {name}")

        # Check for version mismatches
        for name, current_info in current_map.items():
            if name in existing_map:
                existing_info = existing_map[name]
                if current_info["version"] != existing_info.get("version"):
                    discrepancies.append(
                        f"Version mismatch for {name}: "
                        f"index={existing_info.get('version')}, "
                        f"actual={current_info['version']}"
                    )

        return len(discrepancies) == 0, discrepancies
