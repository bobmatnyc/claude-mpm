"""Tests for Phase 3: Community & Batch features.

Tests for:
- CatalogIndexGenerator
- BatchRunner
- IntegrationWizard
- CI validation
"""

from __future__ import annotations

import tempfile
from pathlib import Path  # noqa: TC003

import pytest
import yaml

from claude_mpm.integrations.core.batch import BatchContext, BatchResult, BatchRunner
from claude_mpm.integrations.core.index_generator import CatalogIndexGenerator
from claude_mpm.integrations.core.manifest import IntegrationManifest


@pytest.fixture
def temp_catalog(tmp_path: Path) -> Path:
    """Create a temporary catalog with test integrations."""
    catalog = tmp_path / "catalog"
    catalog.mkdir()

    # Create test integration 1
    int1 = catalog / "testapi1"
    int1.mkdir()
    manifest1 = {
        "name": "testapi1",
        "version": "1.0.0",
        "description": "Test API 1",
        "api_type": "rest",
        "base_url": "https://api1.test.com",
        "auth": {"type": "none", "credentials": []},
        "operations": [
            {
                "name": "get_item",
                "description": "Get item",
                "type": "rest_get",
                "endpoint": "/items/{id}",
            }
        ],
    }
    with (int1 / "integration.yaml").open("w") as f:
        yaml.dump(manifest1, f)

    # Create test integration 2
    int2 = catalog / "testapi2"
    int2.mkdir()
    manifest2 = {
        "name": "testapi2",
        "version": "2.0.0",
        "description": "Test API 2",
        "api_type": "rest",
        "base_url": "https://api2.test.com",
        "auth": {"type": "api_key", "credentials": []},
        "operations": [
            {
                "name": "list_users",
                "description": "List users",
                "type": "rest_get",
                "endpoint": "/users",
            }
        ],
    }
    with (int2 / "integration.yaml").open("w") as f:
        yaml.dump(manifest2, f)

    return catalog


class TestCatalogIndexGenerator:
    """Tests for CatalogIndexGenerator."""

    def test_scan_catalog(self, temp_catalog: Path) -> None:
        """Test scanning catalog for integrations."""
        generator = CatalogIndexGenerator()
        integrations = generator.scan_catalog(temp_catalog)

        assert len(integrations) == 2
        names = [i["name"] for i in integrations]
        assert "testapi1" in names
        assert "testapi2" in names

    def test_scan_skips_special_dirs(self, temp_catalog: Path) -> None:
        """Test that special directories are skipped."""
        # Create directories that should be skipped
        (temp_catalog / "_private").mkdir()
        (temp_catalog / ".hidden").mkdir()
        (temp_catalog / "ci").mkdir()

        generator = CatalogIndexGenerator()
        integrations = generator.scan_catalog(temp_catalog)

        # Should still only find the 2 valid integrations
        assert len(integrations) == 2

    def test_generate_index(self, temp_catalog: Path) -> None:
        """Test generating index content."""
        generator = CatalogIndexGenerator()
        content = generator.generate_index(temp_catalog)

        assert "# Auto-generated" in content
        assert "testapi1" in content
        assert "testapi2" in content
        assert "total_count: 2" in content

    def test_write_index(self, temp_catalog: Path) -> None:
        """Test writing _index.yaml file."""
        generator = CatalogIndexGenerator()
        index_path = generator.write_index(temp_catalog)

        assert index_path.exists()
        assert index_path.name == "_index.yaml"

        with index_path.open() as f:
            data = yaml.safe_load(f)

        assert data["total_count"] == 2
        assert len(data["integrations"]) == 2

    def test_verify_index_valid(self, temp_catalog: Path) -> None:
        """Test verifying a valid index."""
        generator = CatalogIndexGenerator()

        # First generate the index
        generator.write_index(temp_catalog)

        # Then verify it
        is_valid, discrepancies = generator.verify_index(temp_catalog)

        assert is_valid is True
        assert len(discrepancies) == 0

    def test_verify_index_missing(self, temp_catalog: Path) -> None:
        """Test verifying when index doesn't exist."""
        generator = CatalogIndexGenerator()
        is_valid, discrepancies = generator.verify_index(temp_catalog)

        assert is_valid is False
        assert "_index.yaml does not exist" in discrepancies[0]

    def test_verify_index_outdated(self, temp_catalog: Path) -> None:
        """Test verifying an outdated index."""
        generator = CatalogIndexGenerator()

        # Generate initial index
        generator.write_index(temp_catalog)

        # Add a new integration
        int3 = temp_catalog / "testapi3"
        int3.mkdir()
        manifest3 = {
            "name": "testapi3",
            "version": "1.0.0",
            "description": "Test API 3",
            "api_type": "rest",
            "base_url": "https://api3.test.com",
            "auth": {"type": "none", "credentials": []},
            "operations": [
                {
                    "name": "ping",
                    "description": "Ping",
                    "type": "rest_get",
                    "endpoint": "/ping",
                }
            ],
        }
        with (int3 / "integration.yaml").open("w") as f:
            yaml.dump(manifest3, f)

        # Verify should fail
        is_valid, discrepancies = generator.verify_index(temp_catalog)

        assert is_valid is False
        assert any("testapi3" in d for d in discrepancies)


class TestBatchRunner:
    """Tests for BatchRunner."""

    def test_batch_context_log_result(self) -> None:
        """Test BatchContext logging results."""
        ctx = BatchContext(
            manifest=None,  # type: ignore
            client=None,  # type: ignore
            credentials=None,  # type: ignore
        )

        ctx.log_result("test_op", {"data": "value"})

        assert len(ctx.results) == 1
        assert ctx.results[0]["operation"] == "test_op"
        assert ctx.results[0]["data"]["data"] == "value"

    def test_batch_context_log_error(self) -> None:
        """Test BatchContext logging errors."""
        ctx = BatchContext(
            manifest=None,  # type: ignore
            client=None,  # type: ignore
            credentials=None,  # type: ignore
        )

        ctx.log_error("Something went wrong")

        assert len(ctx.errors) == 1
        assert ctx.errors[0] == "Something went wrong"

    def test_batch_result_success(self) -> None:
        """Test BatchResult for success case."""
        result = BatchResult(
            success=True,
            results=[{"operation": "test", "data": {}}],
            errors=[],
        )

        assert result.success is True
        assert len(result.results) == 1
        assert len(result.errors) == 0

    def test_batch_result_failure(self) -> None:
        """Test BatchResult for failure case."""
        result = BatchResult(
            success=False,
            results=[],
            errors=["Error 1", "Error 2"],
        )

        assert result.success is False
        assert len(result.errors) == 2


class TestCIValidation:
    """Tests for CI validation scripts."""

    def test_validate_manifest_valid(self, temp_catalog: Path) -> None:
        """Test validating a valid manifest."""
        from claude_mpm.integrations.catalog.ci.validate import validate_manifest

        manifest_path = temp_catalog / "testapi1" / "integration.yaml"
        result = validate_manifest(manifest_path)

        assert result.passed is True
        assert result.name == "testapi1"
        assert len(result.errors) == 0

    def test_validate_manifest_invalid(self, tmp_path: Path) -> None:
        """Test validating an invalid manifest."""
        from claude_mpm.integrations.catalog.ci.validate import validate_manifest

        # Create invalid manifest (missing required fields)
        int_dir = tmp_path / "badapi"
        int_dir.mkdir()
        manifest = {"name": "badapi"}  # Missing required fields

        with (int_dir / "integration.yaml").open("w") as f:
            yaml.dump(manifest, f)

        result = validate_manifest(int_dir / "integration.yaml")

        assert result.passed is False
        assert len(result.errors) > 0

    def test_validate_catalog(self, temp_catalog: Path) -> None:
        """Test validating entire catalog."""
        from claude_mpm.integrations.catalog.ci.validate import validate_catalog

        results = validate_catalog(temp_catalog)

        assert len(results) == 2
        assert all(r.passed for r in results)

    def test_run_all_validations(self, temp_catalog: Path) -> None:
        """Test running all validations."""
        from claude_mpm.integrations.catalog.ci.validate import run_all_validations

        # Generate index first
        generator = CatalogIndexGenerator()
        generator.write_index(temp_catalog)

        all_passed, results = run_all_validations(temp_catalog, check_index=True)

        assert all_passed is True
        # 2 integrations + 1 index check
        assert len(results) == 3
