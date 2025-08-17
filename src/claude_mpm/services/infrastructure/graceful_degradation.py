from pathlib import Path

"""Graceful degradation service for Memory Guardian system.

Implements fallback strategies when monitoring components fail, ensuring
the system continues to function even with reduced capabilities.
"""

import asyncio
import logging
import os
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

from claude_mpm.services.core.base import BaseService


class DegradationLevel(Enum):
    """System degradation levels."""

    NORMAL = "normal"  # Full functionality
    MINOR = "minor"  # Some features disabled
    MODERATE = "moderate"  # Running with reduced capabilities
    SEVERE = "severe"  # Minimal functionality
    EMERGENCY = "emergency"  # Emergency mode only


class FeatureState(Enum):
    """Feature availability state."""

    AVAILABLE = "available"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"


@dataclass
class Feature:
    """System feature definition."""

    name: str
    state: FeatureState
    fallback_mode: Optional[str]
    reason: Optional[str]
    degraded_at: Optional[float]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "state": self.state.value,
            "fallback_mode": self.fallback_mode,
            "reason": self.reason,
            "degraded_at": self.degraded_at,
            "degraded_at_iso": (
                datetime.fromtimestamp(self.degraded_at).isoformat()
                if self.degraded_at
                else None
            ),
        }


@dataclass
class DegradationStatus:
    """System degradation status."""

    level: DegradationLevel
    features: List[Feature]
    active_fallbacks: List[str]
    notifications: List[str]
    timestamp: float

    @property
    def available_features(self) -> int:
        """Count of available features."""
        return sum(1 for f in self.features if f.state == FeatureState.AVAILABLE)

    @property
    def degraded_features(self) -> int:
        """Count of degraded features."""
        return sum(1 for f in self.features if f.state == FeatureState.DEGRADED)

    @property
    def unavailable_features(self) -> int:
        """Count of unavailable features."""
        return sum(1 for f in self.features if f.state == FeatureState.UNAVAILABLE)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "level": self.level.value,
            "available_features": self.available_features,
            "degraded_features": self.degraded_features,
            "unavailable_features": self.unavailable_features,
            "features": [f.to_dict() for f in self.features],
            "active_fallbacks": self.active_fallbacks,
            "notifications": self.notifications,
            "timestamp": self.timestamp,
            "timestamp_iso": datetime.fromtimestamp(self.timestamp).isoformat(),
        }


class GracefulDegradation(BaseService):
    """Service for managing graceful degradation of system features."""

    def __init__(
        self,
        enable_notifications: bool = True,
        log_degradation_events: bool = True,
        state_file: Optional[Path] = None,
    ):
        """Initialize graceful degradation service.

        Args:
            enable_notifications: Whether to show user notifications
            log_degradation_events: Whether to log degradation events
            state_file: Optional file for persisting degradation state
        """
        super().__init__("GracefulDegradation")

        # Configuration
        self.enable_notifications = enable_notifications
        self.log_degradation_events = log_degradation_events
        self.state_file = state_file

        # Feature registry
        self.features: Dict[str, Feature] = {}
        self.fallback_handlers: Dict[str, Callable] = {}
        self.recovery_handlers: Dict[str, Callable] = {}

        # State tracking
        self.degradation_level = DegradationLevel.NORMAL
        self.active_fallbacks: Set[str] = set()
        self.pending_notifications: List[str] = []
        self.degradation_history: List[DegradationStatus] = []

        # Initialize core features
        self._initialize_core_features()

        self.log_info("Graceful degradation service initialized")

    async def initialize(self) -> bool:
        """Initialize the graceful degradation service.

        Returns:
            True if initialization successful
        """
        try:
            self.log_info("Initializing graceful degradation service")

            # Check system capabilities
            await self._check_system_capabilities()

            # Start notification handler
            if self.enable_notifications:
                asyncio.create_task(self._notification_handler())

            self._initialized = True
            self.log_info("Graceful degradation service initialized successfully")
            return True

        except Exception as e:
            self.log_error(f"Failed to initialize graceful degradation: {e}")
            return False

    async def shutdown(self) -> None:
        """Shutdown the graceful degradation service."""
        try:
            self.log_info("Shutting down graceful degradation service")

            # Save state if configured
            if self.state_file:
                self._save_state()

            self._shutdown = True
            self.log_info("Graceful degradation service shutdown complete")

        except Exception as e:
            self.log_error(f"Error during graceful degradation shutdown: {e}")

    def register_feature(
        self,
        name: str,
        fallback_handler: Optional[Callable] = None,
        recovery_handler: Optional[Callable] = None,
    ) -> None:
        """Register a system feature with optional fallback/recovery handlers.

        Args:
            name: Feature name
            fallback_handler: Handler to call when feature degrades
            recovery_handler: Handler to call when feature recovers
        """
        self.features[name] = Feature(
            name=name,
            state=FeatureState.AVAILABLE,
            fallback_mode=None,
            reason=None,
            degraded_at=None,
        )

        if fallback_handler:
            self.fallback_handlers[name] = fallback_handler

        if recovery_handler:
            self.recovery_handlers[name] = recovery_handler

        self.log_debug(f"Registered feature: {name}")

    async def degrade_feature(
        self, feature_name: str, reason: str, fallback_mode: Optional[str] = None
    ) -> bool:
        """Degrade a system feature to fallback mode.

        Args:
            feature_name: Name of feature to degrade
            reason: Reason for degradation
            fallback_mode: Optional description of fallback mode

        Returns:
            True if degradation successful
        """
        if feature_name not in self.features:
            self.log_warning(f"Unknown feature: {feature_name}")
            return False

        feature = self.features[feature_name]

        if feature.state == FeatureState.UNAVAILABLE:
            self.log_debug(f"Feature {feature_name} already unavailable")
            return True

        # Update feature state
        old_state = feature.state
        feature.state = FeatureState.DEGRADED
        feature.fallback_mode = fallback_mode or "basic mode"
        feature.reason = reason
        feature.degraded_at = time.time()

        # Log degradation
        if self.log_degradation_events:
            self.log_warning(
                f"Feature degraded: {feature_name} - {reason} "
                f"(fallback: {feature.fallback_mode})"
            )

        # Add notification
        self._add_notification(
            f"System feature '{feature_name}' running in {feature.fallback_mode} due to: {reason}"
        )

        # Execute fallback handler if available
        if feature_name in self.fallback_handlers:
            try:
                await self.fallback_handlers[feature_name](reason)
            except Exception as e:
                self.log_error(f"Fallback handler failed for {feature_name}: {e}")

        # Add to active fallbacks
        self.active_fallbacks.add(feature_name)

        # Update degradation level
        self._update_degradation_level()

        # Record status
        self._record_status()

        return True

    async def disable_feature(self, feature_name: str, reason: str) -> bool:
        """Completely disable a system feature.

        Args:
            feature_name: Name of feature to disable
            reason: Reason for disabling

        Returns:
            True if disable successful
        """
        if feature_name not in self.features:
            self.log_warning(f"Unknown feature: {feature_name}")
            return False

        feature = self.features[feature_name]

        if feature.state == FeatureState.UNAVAILABLE:
            self.log_debug(f"Feature {feature_name} already disabled")
            return True

        # Update feature state
        feature.state = FeatureState.UNAVAILABLE
        feature.fallback_mode = None
        feature.reason = reason
        feature.degraded_at = time.time()

        # Log disable
        if self.log_degradation_events:
            self.log_error(f"Feature disabled: {feature_name} - {reason}")

        # Add notification
        self._add_notification(
            f"System feature '{feature_name}' has been disabled: {reason}"
        )

        # Remove from active fallbacks if present
        self.active_fallbacks.discard(feature_name)

        # Update degradation level
        self._update_degradation_level()

        # Record status
        self._record_status()

        return True

    async def recover_feature(self, feature_name: str) -> bool:
        """Recover a degraded feature to normal operation.

        Args:
            feature_name: Name of feature to recover

        Returns:
            True if recovery successful
        """
        if feature_name not in self.features:
            self.log_warning(f"Unknown feature: {feature_name}")
            return False

        feature = self.features[feature_name]

        if feature.state == FeatureState.AVAILABLE:
            self.log_debug(f"Feature {feature_name} already available")
            return True

        # Update feature state
        old_state = feature.state
        feature.state = FeatureState.AVAILABLE
        feature.fallback_mode = None
        feature.reason = None
        feature.degraded_at = None

        # Log recovery
        self.log_info(f"Feature recovered: {feature_name}")

        # Add notification
        self._add_notification(
            f"System feature '{feature_name}' has been restored to normal operation"
        )

        # Execute recovery handler if available
        if feature_name in self.recovery_handlers:
            try:
                await self.recovery_handlers[feature_name]()
            except Exception as e:
                self.log_error(f"Recovery handler failed for {feature_name}: {e}")

        # Remove from active fallbacks
        self.active_fallbacks.discard(feature_name)

        # Update degradation level
        self._update_degradation_level()

        # Record status
        self._record_status()

        return True

    def get_status(self) -> DegradationStatus:
        """Get current degradation status.

        Returns:
            DegradationStatus object
        """
        return DegradationStatus(
            level=self.degradation_level,
            features=list(self.features.values()),
            active_fallbacks=list(self.active_fallbacks),
            notifications=list(self.pending_notifications),
            timestamp=time.time(),
        )

    def get_feature_state(self, feature_name: str) -> Optional[FeatureState]:
        """Get the state of a specific feature.

        Args:
            feature_name: Name of feature

        Returns:
            FeatureState or None if feature not found
        """
        feature = self.features.get(feature_name)
        return feature.state if feature else None

    def is_degraded(self) -> bool:
        """Check if system is running in degraded mode.

        Returns:
            True if any features are degraded
        """
        return self.degradation_level != DegradationLevel.NORMAL

    async def fallback_to_basic_monitoring(self) -> bool:
        """Fallback to basic memory monitoring without psutil.

        Returns:
            True if fallback successful
        """
        self.log_info("Falling back to basic memory monitoring")

        # Degrade memory monitoring feature
        await self.degrade_feature(
            "memory_monitoring", "psutil unavailable", "basic OS commands"
        )

        # Use platform-specific commands as fallback
        if os.name == "posix":
            # Unix-like systems
            self._add_notification(
                "Using basic memory monitoring via 'ps' command. "
                "Install psutil for full functionality."
            )
        elif os.name == "nt":
            # Windows
            self._add_notification(
                "Using basic memory monitoring via 'wmic' command. "
                "Install psutil for full functionality."
            )

        return True

    async def fallback_to_manual_checks(self) -> bool:
        """Fallback to manual memory checks when automated monitoring fails.

        Returns:
            True if fallback successful
        """
        self.log_info("Falling back to manual memory checks")

        # Degrade automated monitoring
        await self.degrade_feature(
            "automated_monitoring",
            "monitoring service failure",
            "manual periodic checks",
        )

        self._add_notification(
            "Automated memory monitoring disabled. "
            "Manual checks will be performed periodically."
        )

        return True

    async def continue_without_state(self) -> bool:
        """Continue operation without state preservation.

        Returns:
            True if fallback successful
        """
        self.log_info("Continuing without state preservation")

        # Disable state preservation
        await self.disable_feature("state_preservation", "storage failure")

        self._add_notification(
            "State preservation disabled due to storage issues. "
            "System state will not persist across restarts."
        )

        return True

    def _initialize_core_features(self) -> None:
        """Initialize core system features."""
        core_features = [
            "memory_monitoring",
            "automated_monitoring",
            "state_preservation",
            "restart_protection",
            "health_monitoring",
            "process_management",
            "notification_system",
            "logging_system",
        ]

        for feature in core_features:
            self.register_feature(feature)

    async def _check_system_capabilities(self) -> None:
        """Check and degrade features based on system capabilities."""
        # Check for psutil
        try:
            import psutil
        except ImportError:
            await self.fallback_to_basic_monitoring()

        # Check for network connectivity
        try:
            import socket

            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex(("8.8.8.8", 53))
            sock.close()
            if result != 0:
                await self.degrade_feature(
                    "health_monitoring", "no network connectivity", "local checks only"
                )
        except:
            await self.degrade_feature(
                "health_monitoring", "network check failed", "local checks only"
            )

        # Check for storage access
        if self.state_file:
            try:
                self.state_file.parent.mkdir(parents=True, exist_ok=True)
                test_file = self.state_file.parent / ".test"
                test_file.write_text("test")
                test_file.unlink()
            except:
                await self.continue_without_state()

    def _update_degradation_level(self) -> None:
        """Update overall degradation level based on feature states."""
        total_features = len(self.features)
        if total_features == 0:
            self.degradation_level = DegradationLevel.NORMAL
            return

        unavailable_count = sum(
            1 for f in self.features.values() if f.state == FeatureState.UNAVAILABLE
        )
        degraded_count = sum(
            1 for f in self.features.values() if f.state == FeatureState.DEGRADED
        )

        unavailable_ratio = unavailable_count / total_features
        degraded_ratio = degraded_count / total_features

        if unavailable_ratio >= 0.5:
            self.degradation_level = DegradationLevel.EMERGENCY
        elif unavailable_ratio >= 0.25:
            self.degradation_level = DegradationLevel.SEVERE
        elif degraded_ratio >= 0.5:
            self.degradation_level = DegradationLevel.MODERATE
        elif degraded_ratio >= 0.25:
            self.degradation_level = DegradationLevel.MINOR
        else:
            self.degradation_level = DegradationLevel.NORMAL

    def _add_notification(self, message: str) -> None:
        """Add a notification for the user.

        Args:
            message: Notification message
        """
        if self.enable_notifications:
            self.pending_notifications.append(message)
            self.log_info(f"Notification: {message}")

    def _record_status(self) -> None:
        """Record current degradation status."""
        status = self.get_status()
        self.degradation_history.append(status)

        # Trim history
        if len(self.degradation_history) > 100:
            self.degradation_history = self.degradation_history[-100:]

    async def _notification_handler(self) -> None:
        """Background task to handle user notifications."""
        while not self._shutdown:
            try:
                if self.pending_notifications:
                    # Process pending notifications
                    notifications = list(self.pending_notifications)
                    self.pending_notifications.clear()

                    for notification in notifications:
                        # In a real implementation, this would show system notifications
                        # For now, just log them
                        self.log_info(f"USER NOTIFICATION: {notification}")

                await asyncio.sleep(5)  # Check every 5 seconds

            except Exception as e:
                self.log_error(f"Error in notification handler: {e}")
                await asyncio.sleep(5)

    def _save_state(self) -> None:
        """Save degradation state to file."""
        if not self.state_file:
            return

        try:
            import json

            state = {
                "degradation_level": self.degradation_level.value,
                "features": [f.to_dict() for f in self.features.values()],
                "active_fallbacks": list(self.active_fallbacks),
                "history": [s.to_dict() for s in self.degradation_history[-10:]],
            }

            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.state_file, "w") as f:
                json.dump(state, f, indent=2)

            self.log_debug(f"Saved degradation state to {self.state_file}")

        except Exception as e:
            self.log_error(f"Failed to save degradation state: {e}")
