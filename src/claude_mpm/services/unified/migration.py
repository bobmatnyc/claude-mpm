"""
Migration Utilities for Service Consolidation
=============================================

This module provides utilities for migrating from the existing 314 service files
to the consolidated unified service architecture. It includes service mapping,
backward compatibility wrappers, and feature flags for gradual rollout.

Key Components:
1. ServiceMapper: Maps legacy services to unified services
2. Compatibility wrappers: Maintain backward compatibility
3. Feature flags: Control gradual migration rollout
4. Migration status tracking: Monitor migration progress

Migration Strategy:
- Phase 1: Create unified interfaces and strategies
- Phase 2: Implement unified services with strategy pattern
- Phase 3: Create compatibility wrappers for legacy code
- Phase 4: Gradually migrate consumers to unified services
- Phase 5: Deprecate and remove legacy services
"""

import inspect
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Type, TypeVar

from claude_mpm.core.logging_utils import get_logger

logger = get_logger(__name__)

# Type variables
T = TypeVar("T")
ServiceType = TypeVar("ServiceType")


class MigrationStatus(Enum):
    """Status of service migration."""

    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    TESTING = "testing"
    COMPLETED = "completed"
    DEPRECATED = "deprecated"
    REMOVED = "removed"


class FeatureFlag(Enum):
    """Feature flags for controlling migration rollout."""

    USE_UNIFIED_DEPLOYMENT = "use_unified_deployment"
    USE_UNIFIED_ANALYZER = "use_unified_analyzer"
    USE_UNIFIED_CONFIG = "use_unified_config"
    ENABLE_COMPATIBILITY_MODE = "enable_compatibility_mode"
    LOG_MIGRATION_WARNINGS = "log_migration_warnings"
    ENFORCE_NEW_INTERFACES = "enforce_new_interfaces"
    ALLOW_LEGACY_FALLBACK = "allow_legacy_fallback"


@dataclass
class ServiceMapping:
    """
    Mapping between legacy service and unified service.

    Attributes:
        legacy_path: Path to legacy service module
        legacy_class: Legacy service class name
        unified_service: Unified service class
        unified_strategy: Strategy to use in unified service
        status: Migration status
        compatibility_wrapper: Optional compatibility wrapper class
        notes: Migration notes and considerations
    """

    legacy_path: str
    legacy_class: str
    unified_service: str
    unified_strategy: Optional[str] = None
    status: MigrationStatus = MigrationStatus.NOT_STARTED
    compatibility_wrapper: Optional[str] = None
    notes: str = ""


@dataclass
class MigrationMetrics:
    """
    Metrics for tracking migration progress.

    Attributes:
        total_services: Total number of services to migrate
        migrated_services: Number of successfully migrated services
        in_progress: Number of services currently being migrated
        deprecated_services: Number of deprecated services
        removed_services: Number of removed services
        migration_errors: Count of migration errors
        start_date: Migration start date
        target_date: Target completion date
    """

    total_services: int = 314  # Current service count
    migrated_services: int = 0
    in_progress: int = 0
    deprecated_services: int = 0
    removed_services: int = 0
    migration_errors: int = 0
    start_date: str = ""
    target_date: str = ""

    @property
    def completion_percentage(self) -> float:
        """Calculate migration completion percentage."""
        if self.total_services == 0:
            return 0.0
        return (self.migrated_services / self.total_services) * 100

    @property
    def remaining_services(self) -> int:
        """Calculate remaining services to migrate."""
        return self.total_services - self.migrated_services - self.removed_services


class ServiceMapper:
    """
    Maps legacy services to unified services and manages migration.

    This class maintains the mapping between old service implementations
    and new unified services, facilitating gradual migration.
    """

    def __init__(self):
        """Initialize service mapper."""
        self._mappings: Dict[str, ServiceMapping] = {}
        self._feature_flags: Dict[FeatureFlag, bool] = dict.fromkeys(FeatureFlag, False)
        self._metrics = MigrationMetrics()
        self._logger = get_logger(f"{__name__}.ServiceMapper")
        self._initialize_mappings()

    def _initialize_mappings(self) -> None:
        """Initialize default service mappings."""
        # Example mappings for deployment services
        self.add_mapping(
            ServiceMapping(
                legacy_path="claude_mpm.services.agent_deployment",
                legacy_class="AgentDeploymentService",
                unified_service="UnifiedDeploymentService",
                unified_strategy="AgentDeploymentStrategy",
                status=MigrationStatus.NOT_STARTED,
                notes="Consolidate with other deployment services",
            )
        )

        # Example mappings for analyzer services
        self.add_mapping(
            ServiceMapping(
                legacy_path="claude_mpm.services.code_analyzer",
                legacy_class="CodeAnalyzer",
                unified_service="UnifiedAnalyzer",
                unified_strategy="CodeAnalysisStrategy",
                status=MigrationStatus.NOT_STARTED,
                notes="Merge with complexity and dependency analyzers",
            )
        )

        # Example mappings for configuration services
        self.add_mapping(
            ServiceMapping(
                legacy_path="claude_mpm.services.project_config",
                legacy_class="ProjectConfigService",
                unified_service="UnifiedConfigManager",
                unified_strategy="ProjectConfigStrategy",
                status=MigrationStatus.NOT_STARTED,
                notes="Consolidate all config services",
            )
        )

    def add_mapping(self, mapping: ServiceMapping) -> None:
        """
        Add a service mapping.

        Args:
            mapping: Service mapping to add
        """
        key = f"{mapping.legacy_path}.{mapping.legacy_class}"
        self._mappings[key] = mapping
        self._logger.debug(f"Added mapping for {key}")

    def get_mapping(self, legacy_service: str) -> Optional[ServiceMapping]:
        """
        Get mapping for a legacy service.

        Args:
            legacy_service: Legacy service identifier

        Returns:
            Optional[ServiceMapping]: Service mapping if found
        """
        return self._mappings.get(legacy_service)

    def get_unified_service(self, legacy_path: str, legacy_class: str) -> Optional[str]:
        """
        Get unified service for a legacy service.

        Args:
            legacy_path: Legacy service module path
            legacy_class: Legacy service class name

        Returns:
            Optional[str]: Unified service name if mapped
        """
        key = f"{legacy_path}.{legacy_class}"
        mapping = self._mappings.get(key)
        return mapping.unified_service if mapping else None

    def update_status(self, legacy_service: str, status: MigrationStatus) -> bool:
        """
        Update migration status for a service.

        Args:
            legacy_service: Legacy service identifier
            status: New migration status

        Returns:
            bool: True if status updated
        """
        mapping = self._mappings.get(legacy_service)
        if not mapping:
            return False

        old_status = mapping.status
        mapping.status = status

        # Update metrics
        if old_status != status:
            if status == MigrationStatus.COMPLETED:
                self._metrics.migrated_services += 1
            elif status == MigrationStatus.IN_PROGRESS:
                self._metrics.in_progress += 1
            elif status == MigrationStatus.DEPRECATED:
                self._metrics.deprecated_services += 1
            elif status == MigrationStatus.REMOVED:
                self._metrics.removed_services += 1

        self._logger.info(f"Updated {legacy_service} status: {old_status} -> {status}")
        return True

    def set_feature_flag(self, flag: FeatureFlag, enabled: bool) -> None:
        """
        Set a feature flag value.

        Args:
            flag: Feature flag to set
            enabled: Whether to enable the flag
        """
        self._feature_flags[flag] = enabled
        self._logger.info(f"Feature flag {flag.value} set to {enabled}")

    def is_feature_enabled(self, flag: FeatureFlag) -> bool:
        """
        Check if a feature flag is enabled.

        Args:
            flag: Feature flag to check

        Returns:
            bool: True if feature is enabled
        """
        return self._feature_flags.get(flag, False)

    def get_metrics(self) -> MigrationMetrics:
        """
        Get migration metrics.

        Returns:
            MigrationMetrics: Current migration metrics
        """
        return self._metrics

    def list_mappings(
        self, status_filter: Optional[MigrationStatus] = None
    ) -> List[ServiceMapping]:
        """
        List all service mappings.

        Args:
            status_filter: Optional filter by migration status

        Returns:
            List[ServiceMapping]: List of service mappings
        """
        mappings = list(self._mappings.values())

        if status_filter:
            mappings = [m for m in mappings if m.status == status_filter]

        return mappings


def create_compatibility_wrapper(
    legacy_class: Type[T],
    unified_service: Any,
    method_mappings: Optional[Dict[str, str]] = None,
) -> Type[T]:
    """
    Create a compatibility wrapper for a legacy service.

    This function dynamically creates a wrapper class that maintains the
    legacy interface while delegating to the unified service implementation.

    Args:
        legacy_class: Legacy service class to wrap
        unified_service: Unified service instance
        method_mappings: Optional mapping of legacy to unified method names

    Returns:
        Type[T]: Wrapper class maintaining legacy interface
    """
    method_mappings = method_mappings or {}

    class CompatibilityWrapper:
        """
        Dynamic compatibility wrapper for legacy services.

        This wrapper maintains the legacy interface while delegating
        operations to the unified service implementation.
        """

        def __init__(self, *args, **kwargs):
            """Initialize wrapper with unified service."""
            self._unified_service = unified_service
            self._logger = get_logger(f"{__name__}.{legacy_class.__name__}Wrapper")
            self._logger.debug(
                f"Created compatibility wrapper for {legacy_class.__name__}"
            )

        def __getattr__(self, name: str) -> Any:
            """
            Delegate attribute access to unified service.

            Args:
                name: Attribute name

            Returns:
                Any: Attribute value from unified service

            Raises:
                AttributeError: If attribute not found
            """
            # Check if method is mapped to a different name
            unified_name = method_mappings.get(name, name)

            # Try to get from unified service
            if hasattr(self._unified_service, unified_name):
                attr = getattr(self._unified_service, unified_name)

                # Log deprecation warning if configured
                if ServiceMapper().is_feature_enabled(
                    FeatureFlag.LOG_MIGRATION_WARNINGS
                ):
                    self._logger.warning(
                        f"Using compatibility wrapper for {legacy_class.__name__}.{name}. "
                        f"Please migrate to unified service."
                    )

                return attr

            # Fallback to legacy implementation if allowed
            if ServiceMapper().is_feature_enabled(FeatureFlag.ALLOW_LEGACY_FALLBACK):
                if hasattr(legacy_class, name):
                    self._logger.warning(
                        f"Falling back to legacy implementation for {name}"
                    )
                    return getattr(legacy_class, name)

            raise AttributeError(
                f"'{legacy_class.__name__}' wrapper has no attribute '{name}'"
            )

    # Copy class metadata
    CompatibilityWrapper.__name__ = legacy_class.__name__
    CompatibilityWrapper.__module__ = legacy_class.__module__
    CompatibilityWrapper.__doc__ = (
        f"Compatibility wrapper for {legacy_class.__name__}.\n\n"
        f"This class maintains backward compatibility while delegating to "
        f"the unified service implementation."
    )

    # Copy method signatures for better IDE support
    for name, method in inspect.getmembers(legacy_class, inspect.isfunction):
        if not name.startswith("_"):
            setattr(CompatibilityWrapper, name, method)

    return CompatibilityWrapper


class MigrationValidator:
    """
    Validates migration compatibility and correctness.

    This class ensures that unified services properly implement
    the functionality of the legacy services they replace.
    """

    def __init__(self):
        """Initialize migration validator."""
        self._logger = get_logger(f"{__name__}.MigrationValidator")

    def validate_interface_compatibility(
        self, legacy_class: Type, unified_class: Type
    ) -> List[str]:
        """
        Validate that unified service implements legacy interface.

        Args:
            legacy_class: Legacy service class
            unified_class: Unified service class

        Returns:
            List[str]: List of compatibility issues
        """
        issues = []

        # Get public methods from legacy class
        legacy_methods = {
            name
            for name, _ in inspect.getmembers(legacy_class, inspect.ismethod)
            if not name.startswith("_")
        }

        # Get public methods from unified class
        unified_methods = {
            name
            for name, _ in inspect.getmembers(unified_class, inspect.ismethod)
            if not name.startswith("_")
        }

        # Check for missing methods
        missing = legacy_methods - unified_methods
        if missing:
            issues.append(f"Missing methods in unified service: {', '.join(missing)}")

        # Check method signatures
        for method_name in legacy_methods & unified_methods:
            legacy_sig = inspect.signature(getattr(legacy_class, method_name))
            unified_sig = inspect.signature(getattr(unified_class, method_name))

            if legacy_sig != unified_sig:
                issues.append(
                    f"Method signature mismatch for {method_name}: "
                    f"legacy={legacy_sig}, unified={unified_sig}"
                )

        return issues

    def validate_behavior_compatibility(
        self,
        legacy_instance: Any,
        unified_instance: Any,
        test_cases: List[Dict[str, Any]],
    ) -> List[str]:
        """
        Validate that unified service behavior matches legacy.

        Args:
            legacy_instance: Legacy service instance
            unified_instance: Unified service instance
            test_cases: List of test cases with method, args, kwargs

        Returns:
            List[str]: List of behavior differences
        """
        differences = []

        for test_case in test_cases:
            method_name = test_case["method"]
            args = test_case.get("args", ())
            kwargs = test_case.get("kwargs", {})

            try:
                # Execute on legacy service
                legacy_result = getattr(legacy_instance, method_name)(*args, **kwargs)

                # Execute on unified service
                unified_result = getattr(unified_instance, method_name)(*args, **kwargs)

                # Compare results
                if legacy_result != unified_result:
                    differences.append(
                        f"Different results for {method_name}: "
                        f"legacy={legacy_result}, unified={unified_result}"
                    )

            except Exception as e:
                differences.append(f"Error testing {method_name}: {e!s}")

        return differences


# Global service mapper instance
_global_mapper = ServiceMapper()


def get_service_mapper() -> ServiceMapper:
    """
    Get the global service mapper instance.

    Returns:
        ServiceMapper: Global mapper instance
    """
    return _global_mapper
