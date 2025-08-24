from pathlib import Path

#!/usr/bin/env python3
"""
Agent Modification Tracker - Consolidated Service
=================================================

Comprehensive agent modification tracking and persistence system for monitoring
agent changes across the three-tier hierarchy with real-time detection and
intelligent persistence management.

Key Features:
- Real-time file system monitoring for agent changes
- Modification history and version tracking
- Agent backup and restore functionality
- Modification validation and conflict detection
- SharedPromptCache invalidation integration
- Persistence storage in hierarchy-appropriate locations
- Change classification (create, modify, delete, move)

This is a consolidated version of the agent_modification_tracker service,
combining all functionality into a single module for better maintainability.
"""

import asyncio
import hashlib
import json
import logging
import shutil
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from claude_mpm.core.base_service import BaseService
from claude_mpm.core.unified_agent_registry import UnifiedAgentRegistry as AgentRegistry
from claude_mpm.core.unified_paths import get_path_manager
from claude_mpm.services.memory.cache.shared_prompt_cache import SharedPromptCache

# ============================================================================
# Data Models
# ============================================================================


class ModificationType(Enum):
    """Types of agent modifications."""

    CREATE = "create"
    MODIFY = "modify"
    DELETE = "delete"
    MOVE = "move"
    RESTORE = "restore"


class ModificationTier(Enum):
    """Agent hierarchy tiers for modification tracking."""

    PROJECT = "project"
    USER = "user"
    SYSTEM = "system"


@dataclass
class AgentModification:
    """Agent modification record with comprehensive metadata."""

    modification_id: str
    agent_name: str
    modification_type: ModificationType
    tier: ModificationTier
    file_path: str
    timestamp: float
    user_id: Optional[str] = None
    modification_details: Dict[str, Any] = field(default_factory=dict)
    file_hash_before: Optional[str] = None
    file_hash_after: Optional[str] = None
    file_size_before: Optional[int] = None
    file_size_after: Optional[int] = None
    backup_path: Optional[str] = None
    validation_status: str = "pending"
    validation_errors: List[str] = field(default_factory=list)
    related_modifications: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def modification_datetime(self) -> datetime:
        """Get modification timestamp as datetime."""
        return datetime.fromtimestamp(self.timestamp)

    @property
    def age_seconds(self) -> float:
        """Get age of modification in seconds."""
        return time.time() - self.timestamp

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data["modification_type"] = self.modification_type.value
        data["tier"] = self.tier.value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentModification":
        """Create from dictionary."""
        data["modification_type"] = ModificationType(data["modification_type"])
        data["tier"] = ModificationTier(data["tier"])
        return cls(**data)


@dataclass
class ModificationHistory:
    """Complete modification history for an agent."""

    agent_name: str
    modifications: List[AgentModification] = field(default_factory=list)
    current_version: Optional[str] = None
    total_modifications: int = 0
    first_seen: Optional[float] = None
    last_modified: Optional[float] = None

    def add_modification(self, modification: AgentModification) -> None:
        """Add a modification to history."""
        self.modifications.append(modification)
        self.total_modifications += 1
        self.last_modified = modification.timestamp

        if self.first_seen is None:
            self.first_seen = modification.timestamp

    def get_recent_modifications(self, hours: int = 24) -> List[AgentModification]:
        """Get modifications within specified hours."""
        cutoff = time.time() - (hours * 3600)
        return [mod for mod in self.modifications if mod.timestamp >= cutoff]

    def get_modifications_by_type(
        self, mod_type: ModificationType
    ) -> List[AgentModification]:
        """Get modifications by type."""
        return [mod for mod in self.modifications if mod.modification_type == mod_type]


# ============================================================================
# File System Monitoring
# ============================================================================


class AgentFileSystemHandler(FileSystemEventHandler):
    """Handles file system events for agent files."""

    def __init__(self, tracker: "AgentModificationTracker"):
        self.tracker = tracker
        self.logger = logging.getLogger(__name__)

    def on_created(self, event: FileSystemEvent) -> None:
        """Handle file creation events."""
        if not event.is_directory and event.src_path.endswith(
            (".md", ".json", ".yaml")
        ):
            asyncio.create_task(
                self.tracker._handle_file_modification(
                    event.src_path, ModificationType.CREATE
                )
            )

    def on_modified(self, event: FileSystemEvent) -> None:
        """Handle file modification events."""
        if not event.is_directory and event.src_path.endswith(
            (".md", ".json", ".yaml")
        ):
            asyncio.create_task(
                self.tracker._handle_file_modification(
                    event.src_path, ModificationType.MODIFY
                )
            )

    def on_deleted(self, event: FileSystemEvent) -> None:
        """Handle file deletion events."""
        if not event.is_directory and event.src_path.endswith(
            (".md", ".json", ".yaml")
        ):
            asyncio.create_task(
                self.tracker._handle_file_modification(
                    event.src_path, ModificationType.DELETE
                )
            )

    def on_moved(self, event: FileSystemEvent) -> None:
        """Handle file move events."""
        if not event.is_directory and event.src_path.endswith(
            (".md", ".json", ".yaml")
        ):
            asyncio.create_task(
                self.tracker._handle_file_move(event.src_path, event.dest_path)
            )


# ============================================================================
# Main Service Class
# ============================================================================


class AgentModificationTracker(BaseService):
    """
    Agent Modification Tracker - Comprehensive modification tracking and persistence system.

    This consolidated service combines all functionality from the previous multi-file
    implementation into a single, maintainable module.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the agent modification tracker."""
        super().__init__("agent_modification_tracker", config)

        # Configuration
        self.enable_monitoring = self.get_config("enable_monitoring", True)
        self.backup_enabled = self.get_config("backup_enabled", True)
        self.max_history_days = self.get_config("max_history_days", 30)
        self.validation_enabled = self.get_config("validation_enabled", True)
        self.persistence_interval = self.get_config("persistence_interval", 300)

        # Core components
        self.shared_cache: Optional[SharedPromptCache] = None
        self.agent_registry: Optional[AgentRegistry] = None

        # Tracking data structures
        self.modification_history: Dict[str, ModificationHistory] = {}
        self.active_modifications: Dict[str, AgentModification] = {}

        # File monitoring
        self.file_observer: Optional[Observer] = None
        self.watched_paths: Set[Path] = set()

        # Persistence paths
        self.persistence_root = get_path_manager().get_tracking_dir()
        self.backup_root = self.persistence_root / "backups"
        self.history_root = self.persistence_root / "history"

        # Create directories
        self.persistence_root.mkdir(parents=True, exist_ok=True)
        self.backup_root.mkdir(parents=True, exist_ok=True)
        self.history_root.mkdir(parents=True, exist_ok=True)

        # Background tasks
        self._persistence_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None

        # Callbacks
        self.modification_callbacks: List[Callable[[AgentModification], None]] = []

        self.logger.info(
            f"AgentModificationTracker initialized with monitoring="
            f"{'enabled' if self.enable_monitoring else 'disabled'}"
        )

    async def _initialize(self) -> None:
        """Initialize the modification tracker service."""
        self.logger.info("Initializing AgentModificationTracker service...")

        # Initialize cache and registry integration
        await self._initialize_integrations()

        # Load existing modification history
        await self._load_modification_history()

        # Set up file system monitoring
        if self.enable_monitoring:
            await self._setup_file_monitoring()

        # Start background tasks
        self._persistence_task = asyncio.create_task(self._persistence_loop())
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())

        self.logger.info("AgentModificationTracker service initialized successfully")

    async def _cleanup(self) -> None:
        """Cleanup modification tracker resources."""
        self.logger.info("Cleaning up AgentModificationTracker service...")

        # Stop file system monitoring
        if self.enable_monitoring and self.file_observer:
            self.file_observer.stop()
            self.file_observer.join()

        # Cancel background tasks
        if self._persistence_task:
            self._persistence_task.cancel()
        if self._cleanup_task:
            self._cleanup_task.cancel()

        # Save final state
        await self._save_modification_history()

        self.logger.info("AgentModificationTracker service cleaned up")

    async def _health_check(self) -> Dict[str, bool]:
        """Perform modification tracker health checks."""
        checks = {}

        try:
            # Check persistence directories
            checks["persistence_directories"] = all(
                [
                    self.persistence_root.exists(),
                    self.backup_root.exists(),
                    self.history_root.exists(),
                ]
            )

            # Check file system monitoring
            checks["file_monitoring"] = (
                (self.file_observer is not None and self.file_observer.is_alive())
                if self.enable_monitoring
                else True
            )

            # Check integration components
            checks["cache_integration"] = self.shared_cache is not None
            checks["registry_integration"] = self.agent_registry is not None

            # Check background tasks
            checks["persistence_task"] = (
                self._persistence_task is not None and not self._persistence_task.done()
            )
            checks["cleanup_task"] = (
                self._cleanup_task is not None and not self._cleanup_task.done()
            )

            checks["modification_tracking"] = True

        except Exception as e:
            self.logger.error(f"Modification tracker health check failed: {e}")
            checks["health_check_error"] = False

        return checks

    # ========================================================================
    # Core Functionality
    # ========================================================================

    async def track_modification(
        self,
        agent_name: str,
        modification_type: ModificationType,
        file_path: str,
        tier: ModificationTier,
        **kwargs,
    ) -> AgentModification:
        """Track an agent modification with comprehensive metadata collection."""
        # Generate modification ID
        modification_id = (
            f"{agent_name}_{modification_type.value}_{uuid.uuid4().hex[:8]}"
        )

        # Collect file metadata
        file_metadata = await self._collect_file_metadata(file_path, modification_type)

        # Create backup if enabled
        backup_path = None
        if self.backup_enabled and modification_type in [
            ModificationType.MODIFY,
            ModificationType.DELETE,
        ]:
            backup_path = await self._create_backup(file_path, modification_id)

        # Create modification record
        # Only include valid AgentModification fields from file_metadata
        valid_metadata_fields = {"file_hash_after", "file_size_after"}
        filtered_metadata = {
            k: v for k, v in file_metadata.items() if k in valid_metadata_fields
        }

        # Add other metadata to the metadata field
        extra_metadata = {
            k: v for k, v in file_metadata.items() if k not in valid_metadata_fields
        }
        extra_metadata.update(kwargs)

        modification = AgentModification(
            modification_id=modification_id,
            agent_name=agent_name,
            modification_type=modification_type,
            tier=tier,
            file_path=file_path,
            timestamp=time.time(),
            backup_path=backup_path,
            metadata=extra_metadata,
            **filtered_metadata,
        )

        # Validate modification if enabled
        if self.validation_enabled:
            await self._validate_modification(modification)

        # Store in active modifications
        self.active_modifications[modification_id] = modification

        # Add to history
        if agent_name not in self.modification_history:
            self.modification_history[agent_name] = ModificationHistory(
                agent_name=agent_name
            )

        self.modification_history[agent_name].add_modification(modification)

        # Invalidate cache
        if self.shared_cache:
            await self._invalidate_agent_cache(agent_name)

        # Trigger callbacks
        await self._trigger_modification_callbacks(modification)

        self.logger.info(
            f"Tracked {modification_type.value} modification for agent '{agent_name}': {modification_id}"
        )

        return modification

    # ========================================================================
    # Helper Methods
    # ========================================================================

    async def _initialize_integrations(self) -> None:
        """Initialize cache and registry integrations."""
        try:
            self.shared_cache = SharedPromptCache.get_instance()
            self.agent_registry = AgentRegistry(cache_service=self.shared_cache)
            self.logger.info("Successfully initialized cache and registry integrations")
        except Exception as e:
            self.logger.warning(f"Failed to initialize integrations: {e}")

    async def _setup_file_monitoring(self) -> None:
        """Set up file system monitoring for agent files."""
        try:
            self.file_observer = Observer()
            event_handler = AgentFileSystemHandler(self)

            # Monitor standard agent directories
            agent_dirs = [
                Path("agents"),
                Path("src/claude_mpm/agents"),
                get_path_manager().get_user_agents_dir(),
            ]

            for agent_dir in agent_dirs:
                if agent_dir.exists():
                    self.file_observer.schedule(
                        event_handler, str(agent_dir), recursive=True
                    )
                    self.watched_paths.add(agent_dir)
                    self.logger.info(f"Monitoring agent directory: {agent_dir}")

            self.file_observer.start()

        except Exception as e:
            self.logger.error(f"Failed to setup file monitoring: {e}")

    async def _collect_file_metadata(
        self, file_path: str, modification_type: ModificationType
    ) -> Dict[str, Any]:
        """Collect comprehensive file metadata."""
        metadata = {}

        try:
            path = Path(file_path)

            if path.exists() and modification_type != ModificationType.DELETE:
                # File size
                metadata["file_size_after"] = path.stat().st_size

                # File hash
                with open(path, "rb") as f:
                    metadata["file_hash_after"] = hashlib.sha256(f.read()).hexdigest()

                # File type
                metadata["file_type"] = path.suffix

                # Modification time
                metadata["mtime"] = path.stat().st_mtime

        except Exception as e:
            self.logger.error(f"Error collecting file metadata: {e}")

        return metadata

    async def _create_backup(
        self, file_path: str, modification_id: str
    ) -> Optional[str]:
        """Create backup of agent file."""
        try:
            source = Path(file_path)
            if not source.exists():
                return None

            # Create backup directory for this modification
            backup_dir = self.backup_root / modification_id
            backup_dir.mkdir(parents=True, exist_ok=True)

            # Create backup file
            backup_path = backup_dir / source.name
            shutil.copy2(source, backup_path)

            # Save backup metadata
            metadata = {
                "original_path": str(file_path),
                "backup_time": time.time(),
                "modification_id": modification_id,
            }

            metadata_path = backup_dir / "metadata.json"
            with open(metadata_path, "w") as f:
                json.dump(metadata, f, indent=2)

            return str(backup_path)

        except Exception as e:
            self.logger.error(f"Failed to create backup: {e}")
            return None

    async def _validate_modification(self, modification: AgentModification) -> None:
        """Validate agent modification."""
        errors = []

        try:
            # Check for conflicts
            for mod_id, active_mod in self.active_modifications.items():
                if (
                    active_mod.agent_name == modification.agent_name
                    and active_mod.modification_id != modification.modification_id
                    and active_mod.age_seconds < 60
                ):  # Recent modification
                    errors.append(
                        f"Potential conflict with recent modification: {mod_id}"
                    )

            # Validate file path
            if modification.modification_type != ModificationType.DELETE:
                if not Path(modification.file_path).exists():
                    errors.append(f"File does not exist: {modification.file_path}")

            # Update validation status
            modification.validation_status = "failed" if errors else "passed"
            modification.validation_errors = errors

        except Exception as e:
            self.logger.error(f"Validation error: {e}")
            modification.validation_status = "error"
            modification.validation_errors.append(str(e))

    async def _invalidate_agent_cache(self, agent_name: str) -> None:
        """Invalidate cache entries for modified agent."""
        if self.shared_cache:
            try:
                # Invalidate all cache entries for this agent
                await self.shared_cache.invalidate_pattern(f"*{agent_name}*")
                self.logger.debug(f"Invalidated cache for agent: {agent_name}")
            except Exception as e:
                self.logger.error(f"Failed to invalidate cache: {e}")

    async def _handle_file_modification(
        self, file_path: str, modification_type: ModificationType
    ) -> None:
        """Handle file system modification events."""
        try:
            # Extract agent information from path
            agent_info = self._extract_agent_info_from_path(file_path)
            if not agent_info:
                return

            agent_name, tier = agent_info

            # Track the modification
            await self.track_modification(
                agent_name=agent_name,
                modification_type=modification_type,
                file_path=file_path,
                tier=tier,
                source="file_system_monitor",
            )

        except Exception as e:
            self.logger.error(f"Error handling file modification {file_path}: {e}")

    async def _handle_file_move(self, src_path: str, dest_path: str) -> None:
        """Handle file move events."""
        try:
            src_info = self._extract_agent_info_from_path(src_path)

            if src_info:
                agent_name, tier = src_info
                await self.track_modification(
                    agent_name=agent_name,
                    modification_type=ModificationType.MOVE,
                    file_path=dest_path,
                    tier=tier,
                    source="file_system_monitor",
                    move_source=src_path,
                    move_destination=dest_path,
                )

        except Exception as e:
            self.logger.error(
                f"Error handling file move {src_path} -> {dest_path}: {e}"
            )

    def _extract_agent_info_from_path(
        self, file_path: str
    ) -> Optional[Tuple[str, ModificationTier]]:
        """Extract agent name and tier from file path."""
        try:
            path = Path(file_path)

            # Extract agent name from filename
            agent_name = path.stem
            if agent_name.endswith("_agent"):
                agent_name = agent_name[:-6]  # Remove _agent suffix
            elif agent_name.endswith("-agent"):
                agent_name = agent_name[:-6]  # Remove -agent suffix

            # Determine tier based on path
            path_str = str(path).lower()
            if "system" in path_str or "/claude_mpm/agents/" in path_str:
                tier = ModificationTier.SYSTEM
            elif (
                get_path_manager().CONFIG_DIR.lower() in path_str
                or str(Path.home()) in path_str
            ):
                tier = ModificationTier.USER
            else:
                tier = ModificationTier.PROJECT

            return agent_name, tier

        except Exception:
            return None

    async def _trigger_modification_callbacks(
        self, modification: AgentModification
    ) -> None:
        """Trigger registered modification callbacks."""
        for callback in self.modification_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(modification)
                else:
                    callback(modification)
            except Exception as e:
                self.logger.error(f"Modification callback failed: {e}")

    # ========================================================================
    # Persistence Methods
    # ========================================================================

    async def _load_modification_history(self) -> None:
        """Load modification history from disk."""
        try:
            # Load active modifications
            active_path = self.persistence_root / "active_modifications.json"
            if active_path.exists():
                with open(active_path) as f:
                    data = json.load(f)
                    self.active_modifications = {
                        k: AgentModification.from_dict(v) for k, v in data.items()
                    }

            # Load modification history
            for history_file in self.history_root.glob("*.json"):
                with open(history_file) as f:
                    data = json.load(f)
                    agent_name = data["agent_name"]
                    history = ModificationHistory(agent_name=agent_name)

                    # Recreate modifications
                    for mod_data in data.get("modifications", []):
                        history.add_modification(AgentModification.from_dict(mod_data))

                    history.current_version = data.get("current_version")
                    history.first_seen = data.get("first_seen")
                    history.last_modified = data.get("last_modified")

                    self.modification_history[agent_name] = history

            self.logger.info(
                f"Loaded {len(self.active_modifications)} active modifications and "
                f"{len(self.modification_history)} agent histories"
            )

        except Exception as e:
            self.logger.error(f"Failed to load modification history: {e}")

    async def _save_modification_history(self) -> None:
        """Save modification history to disk."""
        try:
            # Save active modifications
            active_data = {k: v.to_dict() for k, v in self.active_modifications.items()}
            active_path = self.persistence_root / "active_modifications.json"

            with open(active_path, "w") as f:
                json.dump(active_data, f, indent=2)

            # Save modification history
            for agent_name, history in self.modification_history.items():
                history_data = {
                    "agent_name": history.agent_name,
                    "modifications": [mod.to_dict() for mod in history.modifications],
                    "current_version": history.current_version,
                    "total_modifications": history.total_modifications,
                    "first_seen": history.first_seen,
                    "last_modified": history.last_modified,
                }

                history_path = self.history_root / f"{agent_name}_history.json"
                with open(history_path, "w") as f:
                    json.dump(history_data, f, indent=2)

            self.logger.debug("Saved modification history to disk")

        except Exception as e:
            self.logger.error(f"Failed to save modification history: {e}")

    async def _persistence_loop(self) -> None:
        """Background task to persist modification history."""
        while not self._stop_event.is_set():
            try:
                await self._save_modification_history()
                await asyncio.sleep(self.persistence_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Persistence loop error: {e}")
                await asyncio.sleep(self.persistence_interval)

    async def _cleanup_loop(self) -> None:
        """Background task to cleanup old modifications and backups."""
        while not self._stop_event.is_set():
            try:
                await self._cleanup_old_data()
                await asyncio.sleep(3600)  # Run every hour
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Cleanup loop error: {e}")
                await asyncio.sleep(3600)

    async def _cleanup_old_data(self) -> None:
        """Clean up old modifications and backups."""
        try:
            cutoff_time = time.time() - (self.max_history_days * 24 * 3600)

            # Clean up old modifications from active list
            old_active = [
                mod_id
                for mod_id, mod in self.active_modifications.items()
                if mod.timestamp < cutoff_time
            ]

            for mod_id in old_active:
                del self.active_modifications[mod_id]

            # Clean up old backups
            backup_count = 0
            for backup_dir in self.backup_root.iterdir():
                if backup_dir.is_dir():
                    metadata_path = backup_dir / "metadata.json"
                    if metadata_path.exists():
                        with open(metadata_path) as f:
                            metadata = json.load(f)
                            if metadata.get("backup_time", 0) < cutoff_time:
                                shutil.rmtree(backup_dir)
                                backup_count += 1

            if old_active or backup_count > 0:
                self.logger.info(
                    f"Cleaned up {len(old_active)} old modifications and {backup_count} old backups"
                )

        except Exception as e:
            self.logger.error(f"Failed to cleanup old data: {e}")

    # ========================================================================
    # Public API Methods
    # ========================================================================

    async def get_modification_history(
        self, agent_name: str
    ) -> Optional[ModificationHistory]:
        """Get modification history for specific agent."""
        return self.modification_history.get(agent_name)

    async def get_recent_modifications(
        self, hours: int = 24
    ) -> List[AgentModification]:
        """Get all recent modifications across all agents."""
        cutoff = time.time() - (hours * 3600)
        recent = []

        for history in self.modification_history.values():
            recent.extend(
                [mod for mod in history.modifications if mod.timestamp >= cutoff]
            )

        return sorted(recent, key=lambda x: x.timestamp, reverse=True)

    async def restore_agent_backup(self, modification_id: str) -> bool:
        """Restore agent from backup."""
        try:
            modification = self.active_modifications.get(modification_id)
            if not modification or not modification.backup_path:
                return False

            # Restore from backup
            backup_path = Path(modification.backup_path)
            if not backup_path.exists():
                return False

            original_path = Path(modification.file_path)
            shutil.copy2(backup_path, original_path)

            # Track restore operation
            await self.track_modification(
                agent_name=modification.agent_name,
                modification_type=ModificationType.RESTORE,
                file_path=modification.file_path,
                tier=modification.tier,
                restored_from=modification_id,
            )

            return True

        except Exception as e:
            self.logger.error(f"Failed to restore agent backup: {e}")
            return False

    async def get_modification_stats(self) -> Dict[str, Any]:
        """Get comprehensive modification statistics."""
        stats = {
            "total_agents_tracked": len(self.modification_history),
            "total_modifications": sum(
                h.total_modifications for h in self.modification_history.values()
            ),
            "active_modifications": len(self.active_modifications),
            "watched_paths": len(self.watched_paths),
            "monitoring_enabled": self.enable_monitoring,
            "backup_enabled": self.backup_enabled,
            "validation_enabled": self.validation_enabled,
        }

        # Modification type breakdown
        type_counts = {}
        for history in self.modification_history.values():
            for mod in history.modifications:
                type_counts[mod.modification_type.value] = (
                    type_counts.get(mod.modification_type.value, 0) + 1
                )

        stats["modifications_by_type"] = type_counts

        # Tier breakdown
        tier_counts = {}
        for history in self.modification_history.values():
            for mod in history.modifications:
                tier_counts[mod.tier.value] = tier_counts.get(mod.tier.value, 0) + 1

        stats["modifications_by_tier"] = tier_counts

        # Recent activity
        recent_24h = await self.get_recent_modifications(24)
        recent_7d = await self.get_recent_modifications(24 * 7)

        stats["recent_activity"] = {
            "last_24_hours": len(recent_24h),
            "last_7_days": len(recent_7d),
        }

        # Validation stats
        validation_stats = {"passed": 0, "failed": 0, "pending": 0, "error": 0}

        for mod in self.active_modifications.values():
            validation_stats[mod.validation_status] = (
                validation_stats.get(mod.validation_status, 0) + 1
            )

        stats["validation_stats"] = validation_stats

        # Backup stats
        backup_stats = {
            "total_backups": len(list(self.backup_root.iterdir())),
            "backup_size_mb": sum(
                f.stat().st_size for f in self.backup_root.rglob("*") if f.is_file()
            )
            / (1024 * 1024),
        }

        stats["backup_stats"] = backup_stats

        return stats

    def register_modification_callback(
        self, callback: Callable[[AgentModification], None]
    ) -> None:
        """Register callback for modification events."""
        self.modification_callbacks.append(callback)

    def unregister_modification_callback(
        self, callback: Callable[[AgentModification], None]
    ) -> None:
        """Unregister modification callback."""
        if callback in self.modification_callbacks:
            self.modification_callbacks.remove(callback)
