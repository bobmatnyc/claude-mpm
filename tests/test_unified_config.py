"""
Test the Unified Configuration System
Verifies the Phase 3 consolidation implementation
"""

import json
import tempfile
from pathlib import Path

import pytest
import yaml

from claude_mpm.services.unified.config_strategies import (
    ConfigContext,
    ConfigFormat,
    ContextScope,
    ErrorCategory,
    ErrorContext,
    ErrorSeverity,
    SchemaBuilder,
    UnifiedConfigService,
    ValidationRule,
    ValidationType,
)


class TestUnifiedConfigService:
    """Test the unified configuration service"""

    def setup_method(self):
        """Setup test environment"""
        self.service = UnifiedConfigService()
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """Cleanup test environment"""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_load_json_config(self):
        """Test loading JSON configuration"""
        # Create test JSON file
        config_data = {
            "database": {"host": "localhost", "port": 5432, "name": "testdb"},
            "logging": {"level": "INFO"},
        }

        json_path = Path(self.temp_dir) / "config.json"
        json_path.write_text(json.dumps(config_data, indent=2))

        # Load configuration
        loaded = self.service.load(
            str(json_path), context=ConfigContext.PROJECT, format=ConfigFormat.JSON
        )

        assert loaded == config_data
        assert self.service.get("database.host") == "localhost"
        assert self.service.get("logging.level") == "INFO"

    def test_load_yaml_config(self):
        """Test loading YAML configuration"""
        config_data = {
            "api": {"base_url": "https://api.example.com", "timeout": 30, "retry": 3}
        }

        yaml_path = Path(self.temp_dir) / "config.yaml"
        yaml_path.write_text(yaml.dump(config_data))

        # Load configuration
        loaded = self.service.load(
            str(yaml_path), context=ConfigContext.SERVICE, format=ConfigFormat.YAML
        )

        assert loaded == config_data
        assert self.service.get("api.timeout") == 30

    def test_validation(self):
        """Test configuration validation"""
        # Create schema
        schema = {
            "required": ["host", "port"],
            "properties": {
                "host": {"type": "string"},
                "port": {"type": "integer", "minimum": 1, "maximum": 65535},
            },
        }

        # Valid config
        valid_config = {"host": "localhost", "port": 8080}
        assert self.service.validate(valid_config, schema)

        # Invalid config - missing required field
        invalid_config = {"host": "localhost"}
        assert not self.service.validate(invalid_config, schema)

        # Invalid config - wrong type
        invalid_config2 = {"host": "localhost", "port": "invalid"}
        assert not self.service.validate(invalid_config2, schema)

    def test_merge_configs(self):
        """Test configuration merging"""
        base = {
            "database": {"host": "localhost", "port": 5432},
            "logging": {"level": "INFO"},
        }

        override = {"database": {"port": 3306, "user": "admin"}, "api": {"timeout": 30}}

        merged = self.service.merge(base, override, strategy="deep")

        assert merged["database"]["host"] == "localhost"
        assert merged["database"]["port"] == 3306
        assert merged["database"]["user"] == "admin"
        assert merged["logging"]["level"] == "INFO"
        assert merged["api"]["timeout"] == 30

    def test_context_management(self):
        """Test context-based configuration"""
        # Set global config
        self.service.set("global_key", "global_value", ConfigContext.GLOBAL)

        # Set project config
        self.service.set("project_key", "project_value", ConfigContext.PROJECT)

        # Get values
        assert self.service.get("global_key") == "global_value"
        assert self.service.get("project_key") == "project_value"

    def test_hot_reload(self):
        """Test configuration hot reload"""
        config_path = Path(self.temp_dir) / "dynamic.json"
        config_path.write_text('{"version": 1}')

        # Load with hot reload disabled (default)
        loaded = self.service.load(str(config_path), hot_reload=False)
        assert loaded["version"] == 1

        # Update file
        config_path.write_text('{"version": 2}')

        # Reload should get new value
        self.service.reload()
        # Since hot_reload was False, manual reload is needed
        reloaded = self.service.load(str(config_path))
        assert reloaded["version"] == 2

    def test_error_handling(self):
        """Test error handling during load"""
        # Non-existent file
        result = self.service.load(
            "/nonexistent/config.json", context=ConfigContext.RUNTIME
        )

        # Should return empty dict on error
        assert result == {}

    def test_schema_builder(self):
        """Test schema builder"""
        schema = (
            SchemaBuilder("Test Schema")
            .string("name", required=True)
            .integer("age", minimum=0, maximum=150)
            .boolean("active", default=True)
            .array("tags", min_items=1)
            .build()
        )

        assert schema.title == "Test Schema"
        assert "name" in schema.required
        assert schema.properties["age"].minimum == 0
        assert schema.properties["active"].default

    def test_performance_caching(self):
        """Test caching performance"""
        config_data = {"cached": "value"}
        json_path = Path(self.temp_dir) / "cached.json"
        json_path.write_text(json.dumps(config_data))

        # First load - should cache
        loaded1 = self.service.load(str(json_path))

        # Second load - should use cache
        loaded2 = self.service.load(str(json_path))

        assert loaded1 == loaded2
        assert loaded1 == config_data

        # Check cache statistics
        stats = self.service.get_statistics()
        assert stats["total_configs"] > 0


class TestFileLoaderStrategy:
    """Test file loading strategies"""

    def test_structured_loader(self):
        """Test loading structured formats"""
        from claude_mpm.services.unified.config_strategies import StructuredFileLoader

        loader = StructuredFileLoader()
        assert loader.supports(ConfigFormat.JSON)
        assert loader.supports(ConfigFormat.YAML)
        assert loader.supports(ConfigFormat.TOML)

    def test_environment_loader(self):
        """Test loading environment configurations"""
        from claude_mpm.services.unified.config_strategies import EnvironmentFileLoader

        loader = EnvironmentFileLoader()
        assert loader.supports(ConfigFormat.ENV)


class TestValidationStrategy:
    """Test validation strategies"""

    def test_type_validation(self):
        """Test type validator"""
        from claude_mpm.services.unified.config_strategies import TypeValidator

        validator = TypeValidator()
        rule = ValidationRule(type=ValidationType.TYPE, params={"type": "string"})

        result = validator.validate("test", rule, {})
        assert result.valid

        result = validator.validate(123, rule, {})
        assert not result.valid

    def test_range_validation(self):
        """Test range validator"""
        from claude_mpm.services.unified.config_strategies import RangeValidator

        validator = RangeValidator()
        rule = ValidationRule(type=ValidationType.RANGE, params={"min": 1, "max": 10})

        result = validator.validate(5, rule, {})
        assert result.valid

        result = validator.validate(15, rule, {})
        assert not result.valid


class TestErrorHandlingStrategy:
    """Test error handling strategies"""

    def test_file_io_error_handling(self):
        """Test file I/O error handling"""
        from claude_mpm.services.unified.config_strategies import FileIOErrorHandler

        handler = FileIOErrorHandler()
        context = ErrorContext(
            error=FileNotFoundError("test.json"),
            category=ErrorCategory.FILE_IO,
            severity=ErrorSeverity.ERROR,
            source="test.json",
        )

        assert handler.can_handle(context)

        result = handler.handle(context)
        assert result.handled

    def test_parsing_error_handling(self):
        """Test parsing error handling"""
        from claude_mpm.services.unified.config_strategies import ParsingErrorHandler

        handler = ParsingErrorHandler()
        context = ErrorContext(
            error=json.JSONDecodeError("test", "doc", 0),
            category=ErrorCategory.PARSING,
            severity=ErrorSeverity.WARNING,
        )

        assert handler.can_handle(context)


class TestContextStrategy:
    """Test context management strategies"""

    def test_hierarchical_context(self):
        """Test hierarchical context management"""
        from claude_mpm.services.unified.config_strategies import (
            HierarchicalContextManager,
        )

        manager = HierarchicalContextManager()

        # Create parent context
        parent_id = manager.create_context(ContextScope.PROJECT)
        assert parent_id is not None

        # Create child context
        child_id = manager.create_context(ContextScope.SERVICE, parent_id=parent_id)
        assert child_id is not None

        # Get context chain
        chain = manager.get_context_chain(child_id)
        assert len(chain) == 2
        assert chain[0] == parent_id
        assert chain[1] == child_id

    def test_isolated_context(self):
        """Test isolated context management"""
        from claude_mpm.services.unified.config_strategies import IsolatedContextManager

        manager = IsolatedContextManager()

        # Create isolated context
        context_id = manager.create_isolated_context({"isolated": "value"})
        assert context_id is not None

        # Get config
        config = manager.get_isolated_config(context_id)
        assert config == {"isolated": "value"}


@pytest.mark.skip(reason="scripts.migrate_configs module not available")
def test_migration_stats():
    """Test migration statistics calculation"""
    from scripts.migrate_configs import MigrationStats

    stats = MigrationStats()
    stats.lines_removed = 10000
    stats.lines_added = 1000

    assert stats.net_reduction == 9000

    # Should achieve target reduction
    assert stats.net_reduction >= 5000


class TestMemorySchemaBackendValidation:
    """Tests for memory.backend schema validation — issue #564.

    Verifies that trusty-memory is accepted as a valid backend value, and
    that both legacy values (static, kuzu) still validate, while invalid
    values are rejected.
    """

    def setup_method(self):
        # Import directly from config_schema to get the SchemaValidator that
        # operates on ConfigSchema objects (not the validation_strategy variant).
        from claude_mpm.services.unified.config_strategies.config_schema import (
            SchemaValidator,
            create_memory_schema,
        )

        self.schema = create_memory_schema()
        self.validator = SchemaValidator()

    def _validate_backend(self, backend_value: str) -> bool:
        """Run schema validation against a config with the given backend value."""
        config = {"backend": backend_value}
        return self.validator.validate(config, self.schema)

    def test_trusty_memory_backend_is_valid(self):
        """backend: trusty-memory must pass schema validation (issue #564)."""
        assert self._validate_backend("trusty-memory"), (
            f"trusty-memory backend failed validation: {self.validator.errors}"
        )

    def test_static_backend_is_valid(self):
        """backend: static must remain valid (default passthrough)."""
        assert self._validate_backend("static"), (
            f"static backend failed validation: {self.validator.errors}"
        )

    def test_kuzu_backend_is_valid(self):
        """backend: kuzu must remain valid (deprecated legacy)."""
        assert self._validate_backend("kuzu"), (
            f"kuzu backend failed validation: {self.validator.errors}"
        )

    def test_invalid_backend_is_rejected(self):
        """An unrecognised backend value must be rejected by validation."""
        result = self._validate_backend("invalid-backend")
        assert not result, "Expected validation to fail for 'invalid-backend'"
        assert any("must be one of" in e for e in self.validator.errors), (
            f"Expected 'must be one of' error, got: {self.validator.errors}"
        )

    def test_trusty_memory_enum_present_in_schema(self):
        """trusty-memory must appear in the backend property enum list."""
        # ConfigSchema.properties is keyed by property name
        backend_prop = self.schema.properties.get("backend")
        assert backend_prop is not None, "backend property missing from schema"
        assert backend_prop.enum is not None, "backend property has no enum constraint"
        assert "trusty-memory" in backend_prop.enum, (
            f"trusty-memory not in backend enum: {backend_prop.enum}"
        )
        # Also verify all three expected values are present
        assert "static" in backend_prop.enum
        assert "kuzu" in backend_prop.enum


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
