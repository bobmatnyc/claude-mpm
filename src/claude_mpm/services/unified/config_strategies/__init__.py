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

from .unified_config_service import (
    UnifiedConfigService,
    ConfigFormat,
    ConfigContext,
    ConfigMetadata,
    IConfigStrategy
)

from .file_loader_strategy import (
    FileLoaderStrategy,
    LoaderType,
    FileLoadContext,
    StructuredFileLoader,
    EnvironmentFileLoader,
    ProgrammaticFileLoader,
    LegacyFileLoader,
    CompositeFileLoader
)

from .validation_strategy import (
    ValidationStrategy,
    ValidationRule,
    ValidationResult,
    ValidationType,
    TypeValidator,
    RequiredValidator,
    RangeValidator,
    LengthValidator,
    PatternValidator,
    EnumValidator,
    FormatValidator,
    DependencyValidator,
    UniqueValidator,
    CustomValidator,
    ConditionalValidator,
    RecursiveValidator,
    CrossFieldValidator,
    CompositeValidator,
    SchemaValidator
)

from .error_handling_strategy import (
    ErrorHandlingStrategy,
    ErrorContext,
    ErrorHandlingResult,
    ErrorCategory,
    ErrorSeverity,
    FileIOErrorHandler,
    ParsingErrorHandler,
    ValidationErrorHandler,
    NetworkErrorHandler,
    TypeConversionErrorHandler,
    CompositeErrorHandler
)

from .context_strategy import (
    ContextStrategy,
    ContextScope,
    ContextLifecycle,
    HierarchicalContextManager,
    ScopedConfigManager,
    IsolatedContextManager,
    ThreadLocalContextManager,
    CachingContextManager
)

from .config_schema import (
    ConfigSchema,
    SchemaProperty,
    SchemaBuilder,
    SchemaValidator,
    SchemaRegistry,
    ConfigMigration,
    TypedConfig,
    SchemaType,
    SchemaFormat,
    create_database_schema,
    create_api_schema,
    create_logging_schema
)

# Create singleton instance for global use
unified_config = UnifiedConfigService()

# Backward compatibility aliases
ConfigService = UnifiedConfigService
ConfigManager = UnifiedConfigService
ConfigLoader = UnifiedConfigService

# Export all public APIs
__all__ = [
    # Main service
    'UnifiedConfigService',
    'unified_config',

    # Strategies
    'FileLoaderStrategy',
    'ValidationStrategy',
    'ErrorHandlingStrategy',
    'ContextStrategy',

    # Core types
    'ConfigFormat',
    'ConfigContext',
    'ConfigMetadata',
    'IConfigStrategy',

    # File loading
    'LoaderType',
    'FileLoadContext',
    'StructuredFileLoader',
    'EnvironmentFileLoader',
    'ProgrammaticFileLoader',
    'LegacyFileLoader',
    'CompositeFileLoader',

    # Validation
    'ValidationRule',
    'ValidationResult',
    'ValidationType',

    # Error handling
    'ErrorContext',
    'ErrorHandlingResult',
    'ErrorCategory',
    'ErrorSeverity',

    # Context management
    'ContextScope',
    'ContextLifecycle',
    'HierarchicalContextManager',
    'ScopedConfigManager',

    # Schema
    'ConfigSchema',
    'SchemaProperty',
    'SchemaBuilder',
    'SchemaValidator',
    'SchemaRegistry',
    'ConfigMigration',
    'TypedConfig',
    'SchemaType',
    'SchemaFormat',

    # Backward compatibility
    'ConfigService',
    'ConfigManager',
    'ConfigLoader',
]

# Module initialization
def initialize():
    """Initialize the unified configuration system"""
    # Register default strategies
    unified_config.register_strategy('file', FileLoaderStrategy())
    unified_config.register_strategy('validation', ValidationStrategy())
    unified_config.register_strategy('error', ErrorHandlingStrategy())
    unified_config.register_strategy('context', ContextStrategy())

    # Set up default error handlers
    error_strategy = ErrorHandlingStrategy()

    # Register recovery strategies
    error_strategy.register_recovery_strategy(
        'default_fallback',
        lambda ctx: ctx.metadata.get('default_config', {})
    )

    error_strategy.register_recovery_strategy(
        'empty_fallback',
        lambda ctx: {}
    )

    return unified_config

# Auto-initialize on import
_unified_instance = initialize()