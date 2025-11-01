#!/usr/bin/env python3
"""
Agent Record Service - Persistence and History Management
=========================================================

Handles agent record persistence, history tracking, and data management.
Extracted from AgentLifecycleManager to follow Single Responsibility Principle.

Key Responsibilities:
- Save and load agent lifecycle records
- Manage operation history
- Handle data serialization
- Provide record queries and statistics
"""

import json
import time
from pathlib import Path
from typing import Any, Dict, List

from claude_mpm.core.base_service import BaseService
from claude_mpm.core.unified_paths import get_path_manager
from claude_mpm.services.agents.deployment.agent_state_service import (
    AgentLifecycleRecord,
    LifecycleState,
)
from claude_mpm.services.agents.registry.modification_tracker import ModificationTier
from claude_mpm.utils.config_manager import ConfigurationManager
from claude_mpm.utils.path_operations import path_ops


class AgentRecordService(BaseService):
    """
    Service for managing agent lifecycle records and persistence.

    Responsibilities:
    - Persist agent records to disk
    - Load records on startup
    - Manage operation history
    - Provide record queries
    """

    def __init__(self):
        """Initialize the record service."""
        super().__init__("agent_record_service")

        # Configuration manager for JSON operations
        self.config_mgr = ConfigurationManager(cache_enabled=True)

        # Storage paths
        self.records_file = (
            get_path_manager().get_tracking_dir() / "lifecycle_records.json"
        )
        self.history_file = (
            get_path_manager().get_tracking_dir() / "operation_history.json"
        )

        # Ensure tracking directory exists
        path_ops.ensure_dir(self.records_file.parent)

        self.logger.info("AgentRecordService initialized")

    async def save_records(self, records: Dict[str, AgentLifecycleRecord]) -> bool:
        """
        Save agent lifecycle records to disk.

        Args:
            records: Dictionary of agent records

        Returns:
            True if successful, False otherwise
        """
        try:
            data = {}
            for agent_name, record in records.items():
                record_dict = self._serialize_record(record)
                data[agent_name] = record_dict

            # Write to file with proper formatting
            json_str = json.dumps(data, indent=2, default=str)
            self.records_file.parent.mkdir(parents=True, exist_ok=True)

            with self.records_file.open("w", encoding="utf-8") as f:
                f.write(json_str)

            self.logger.debug(f"Saved {len(records)} agent records")
            return True

        except Exception as e:
            self.logger.error(f"Failed to save agent records: {e}")
            return False

    async def load_records(self) -> Dict[str, AgentLifecycleRecord]:
        """
        Load agent lifecycle records from disk.

        Returns:
            Dictionary of agent records
        """
        records = {}

        try:
            if path_ops.validate_exists(self.records_file):
                data = self.config_mgr.load_json(self.records_file)

                for agent_name, record_data in data.items():
                    record = self._deserialize_record(record_data)
                    records[agent_name] = record

                self.logger.debug(f"Loaded {len(records)} agent records")
            else:
                self.logger.debug("No existing records file found")

        except Exception as e:
            self.logger.warning(f"Failed to load agent records: {e}")

        return records

    async def save_history(self, history: List[Any]) -> bool:
        """
        Save operation history to disk.

        Args:
            history: List of operation results

        Returns:
            True if successful, False otherwise
        """
        try:
            # Convert operation results to dictionaries
            data = []
            for result in history:
                result_dict = {
                    "operation": result.operation.value,
                    "agent_name": result.agent_name,
                    "success": result.success,
                    "duration_ms": result.duration_ms,
                    "error_message": result.error_message,
                    "modification_id": result.modification_id,
                    "persistence_id": result.persistence_id,
                    "cache_invalidated": result.cache_invalidated,
                    "registry_updated": result.registry_updated,
                    "metadata": result.metadata,
                    "timestamp": time.time(),
                }
                data.append(result_dict)

            # Write to file
            json_str = json.dumps(data, indent=2, default=str)
            self.history_file.parent.mkdir(parents=True, exist_ok=True)

            with self.history_file.open("w", encoding="utf-8") as f:
                f.write(json_str)

            self.logger.debug(f"Saved {len(history)} operation history entries")
            return True

        except Exception as e:
            self.logger.error(f"Failed to save operation history: {e}")
            return False

    async def load_history(self) -> List[Dict[str, Any]]:
        """
        Load operation history from disk.

        Returns:
            List of operation history entries
        """
        history = []

        try:
            if path_ops.validate_exists(self.history_file):
                data = self.config_mgr.load_json(self.history_file)
                history = data
                self.logger.info(f"Loaded {len(history)} operation history entries")
            else:
                self.logger.debug("No existing history file found")

        except Exception as e:
            self.logger.warning(f"Failed to load operation history: {e}")

        return history

    def _serialize_record(self, record: AgentLifecycleRecord) -> Dict[str, Any]:
        """
        Serialize an AgentLifecycleRecord to dictionary.

        Args:
            record: The record to serialize

        Returns:
            Serialized dictionary
        """
        return {
            "agent_name": record.agent_name,
            "current_state": record.current_state.value,
            "tier": record.tier.value,
            "file_path": record.file_path,
            "created_at": record.created_at,
            "last_modified": record.last_modified,
            "version": record.version,
            "modifications": record.modifications,
            "persistence_operations": record.persistence_operations,
            "backup_paths": record.backup_paths,
            "validation_status": record.validation_status,
            "validation_errors": record.validation_errors,
            "metadata": record.metadata,
        }

    def _deserialize_record(self, data: Dict[str, Any]) -> AgentLifecycleRecord:
        """
        Deserialize a dictionary to AgentLifecycleRecord.

        Args:
            data: Dictionary to deserialize

        Returns:
            Deserialized AgentLifecycleRecord
        """
        return AgentLifecycleRecord(
            agent_name=data["agent_name"],
            current_state=LifecycleState(data["current_state"]),
            tier=ModificationTier(data["tier"]),
            file_path=data["file_path"],
            created_at=data["created_at"],
            last_modified=data["last_modified"],
            version=data["version"],
            modifications=data.get("modifications", []),
            persistence_operations=data.get("persistence_operations", []),
            backup_paths=data.get("backup_paths", []),
            validation_status=data.get("validation_status", "valid"),
            validation_errors=data.get("validation_errors", []),
            metadata=data.get("metadata", {}),
        )

    async def export_records(self, output_path: Path, format: str = "json") -> bool:
        """
        Export records to a file.

        Args:
            output_path: Path to export to
            format: Export format (json, csv)

        Returns:
            True if successful, False otherwise
        """
        try:
            if format == "json":
                # Load current records
                records = await self.load_records()
                data = {
                    name: self._serialize_record(record)
                    for name, record in records.items()
                }

                # Write to output path
                json_str = json.dumps(data, indent=2, default=str)
                with output_path.open("w", encoding="utf-8") as f:
                    f.write(json_str)

            elif format == "csv":
                # TODO: Implement CSV export
                self.logger.warning("CSV export not yet implemented")
                return False

            self.logger.info(f"Exported records to {output_path}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to export records: {e}")
            return False

    async def import_records(
        self, input_path: Path, merge: bool = False
    ) -> Dict[str, AgentLifecycleRecord]:
        """
        Import records from a file.

        Args:
            input_path: Path to import from
            merge: Whether to merge with existing records

        Returns:
            Imported records
        """
        imported = {}

        try:
            if not path_ops.validate_exists(input_path):
                self.logger.error(f"Import file not found: {input_path}")
                return imported

            # Load data from file
            data = self.config_mgr.load_json(input_path)

            # Deserialize records
            for agent_name, record_data in data.items():
                record = self._deserialize_record(record_data)
                imported[agent_name] = record

            # Optionally merge with existing
            if merge:
                existing = await self.load_records()
                existing.update(imported)
                await self.save_records(existing)
            else:
                await self.save_records(imported)

            self.logger.info(f"Imported {len(imported)} records from {input_path}")

        except Exception as e:
            self.logger.error(f"Failed to import records: {e}")

        return imported

    async def cleanup_old_records(self, days_threshold: int = 30) -> int:
        """
        Remove records older than threshold.

        Args:
            days_threshold: Age threshold in days

        Returns:
            Number of records removed
        """
        try:
            records = await self.load_records()
            original_count = len(records)

            # Filter out old records
            current_time = time.time()
            threshold_seconds = days_threshold * 24 * 3600

            filtered = {
                name: record
                for name, record in records.items()
                if (current_time - record.created_at) < threshold_seconds
            }

            removed_count = original_count - len(filtered)

            if removed_count > 0:
                await self.save_records(filtered)
                self.logger.info(f"Removed {removed_count} old records")

            return removed_count

        except Exception as e:
            self.logger.error(f"Failed to cleanup old records: {e}")
            return 0

    async def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about stored records.

        Returns:
            Statistics dictionary
        """
        try:
            records = await self.load_records()
            history = await self.load_history()

            # Calculate statistics
            stats = {
                "total_records": len(records),
                "total_history_entries": len(history),
                "records_by_state": {},
                "records_by_tier": {},
                "average_age_days": 0.0,
                "newest_record": None,
                "oldest_record": None,
            }

            if records:
                # Count by state
                for record in records.values():
                    state = record.current_state.value
                    stats["records_by_state"][state] = (
                        stats["records_by_state"].get(state, 0) + 1
                    )

                    # Count by tier
                    tier = record.tier.value
                    stats["records_by_tier"][tier] = (
                        stats["records_by_tier"].get(tier, 0) + 1
                    )

                # Calculate age statistics
                ages = [record.age_days for record in records.values()]
                stats["average_age_days"] = sum(ages) / len(ages)

                # Find newest and oldest
                sorted_records = sorted(records.values(), key=lambda r: r.created_at)
                stats["oldest_record"] = sorted_records[0].agent_name
                stats["newest_record"] = sorted_records[-1].agent_name

            return stats

        except Exception as e:
            self.logger.error(f"Failed to get statistics: {e}")
            return {}

    async def _initialize(self) -> None:
        """Initialize the record service."""
        # Ensure storage directories exist
        path_ops.ensure_dir(self.records_file.parent)
        self.logger.info("AgentRecordService initialized")

    async def _cleanup(self) -> None:
        """Cleanup the record service."""
        self.logger.info("AgentRecordService cleaned up")

    async def _health_check(self) -> Dict[str, bool]:
        """Perform health check."""
        return {
            "storage_accessible": path_ops.validate_exists(self.records_file.parent),
            "config_manager_ready": self.config_mgr is not None,
        }
