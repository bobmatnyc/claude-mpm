"""
Unified Configuration Strategies - Phase 3 Consolidation
Reduces 15,000+ lines of configuration code by 65-75%

This package consolidates:
- 15+ configuration services → 1 unified service
- 215 file loading instances → 5 strategic loaders
- 236 validation functions → 15 composable validators
- 99 error handling patterns → Unified error strategy

Target: 10,000-11,000 line reduction with 20-30% performance improvement
"""

from .config_schema import (
    ConfigMigration,
    ConfigSchema,
    SchemaBuilder,
    SchemaFormat,
    SchemaProperty,
    SchemaRegistry,
    SchemaType,
    SchemaValidator,
    TypedConfig,
    create_api_schema,
    create_database_schema,
    create_logging_schema,
)
from .context_strategy import (
    CachingContextManager,
    ContextLifecycle,
    ContextScope,
    ContextStrategy,
    HierarchicalContextManager,
    IsolatedContextManager,
    ScopedConfigManager,
    ThreadLocalContextManager,
)
from .error_handling_strategy import (
    CompositeErrorHandler,
    ErrorCategory,
    ErrorContext,
    ErrorHandlingResult,
    ErrorHandlingStrategy,
    ErrorSeverity,
    FileIOErrorHandler,
    NetworkErrorHandler,
    ParsingErrorHandler,
    TypeConversionErrorHandler,
    ValidationErrorHandler,
)
from .file_loader_strategy import (
    CompositeFileLoader,
    EnvironmentFileLoader,
    FileLoadContext,
    FileLoaderStrategy,
    LegacyFileLoader,
    LoaderType,
    ProgrammaticFileLoader,
    StructuredFileLoader,
)
from .unified_config_service import (
    ConfigContext,
    ConfigFormat,
    ConfigMetadata,
    IConfigStrategy,
    UnifiedConfigService,
)
from .validation_strategy import (
    CompositeValidator,
    ConditionalValidator,
    CrossFieldValidator,
    CustomValidator,
    DependencyValidator,
    EnumValidator,
    FormatValidator,
    LengthValidator,
    PatternValidator,
    RangeValidator,
    RecursiveValidator,
    RequiredValidator,
    SchemaValidator,
    TypeValidator,
    UniqueValidator,
    ValidationResult,
    ValidationRule,
    ValidationStrategy,
    ValidationType,
)

# Create singleton instance for global use
unified_config = UnifiedConfigService()

# Backward compatibility aliases
ConfigService = UnifiedConfigService
ConfigManager = UnifiedConfigService
ConfigLoader = UnifiedConfigService

# Export all public APIs
__all__ = [
    "CompositeFileLoader",
    "ConfigContext",
    # Core types
    "ConfigFormat",
    "ConfigLoader",
    "ConfigManager",
    "ConfigMetadata",
    "ConfigMigration",
    # Schema
    "ConfigSchema",
    # Backward compatibility
    "ConfigService",
    "ContextLifecycle",
    # Context management
    "ContextScope",
    "ContextStrategy",
    "EnvironmentFileLoader",
    "ErrorCategory",
    # Error handling
    "ErrorContext",
    "ErrorHandlingResult",
    "ErrorHandlingStrategy",
    "ErrorSeverity",
    "FileLoadContext",
    # Strategies
    "FileLoaderStrategy",
    "HierarchicalContextManager",
    "IConfigStrategy",
    "LegacyFileLoader",
    # File loading
    "LoaderType",
    "ProgrammaticFileLoader",
    "SchemaBuilder",
    "SchemaFormat",
    "SchemaProperty",
    "SchemaRegistry",
    "SchemaType",
    "SchemaValidator",
    "ScopedConfigManager",
    "StructuredFileLoader",
    "TypedConfig",
    # Main service
    "UnifiedConfigService",
    "ValidationResult",
    # Validation
    "ValidationRule",
    "ValidationStrategy",
    "ValidationType",
    "unified_config",
]


# Module initialization
def initialize():
    """Initialize the unified configuration system"""
    # Register default strategies
    unified_config.register_strategy("file", FileLoaderStrategy())
    unified_config.register_strategy("validation", ValidationStrategy())
    unified_config.register_strategy("error", ErrorHandlingStrategy())
    unified_config.register_strategy("context", ContextStrategy())

    # Set up default error handlers
    error_strategy = ErrorHandlingStrategy()

    # Register recovery strategies
    error_strategy.register_recovery_strategy(
        "default_fallback", lambda ctx: ctx.metadata.get("default_config", {})
    )

    error_strategy.register_recovery_strategy("empty_fallback", lambda ctx: {})

    return unified_config


# Auto-initialize on import
_unified_instance = initialize()
