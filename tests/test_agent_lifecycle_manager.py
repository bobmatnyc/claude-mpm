#!/usr/bin/env python3
"""
Comprehensive unit tests for AgentLifecycleManager.

This test suite provides complete coverage for the AgentLifecycleManager
functionality including:
- Agent creation, update, and deletion
- Lifecycle state management
- Service integration and dependency management
- Error handling and edge cases
- Performance monitoring
- Cache invalidation and registry synchronization
"""

import asyncio
import time
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest
import pytest_asyncio

# Import the classes we're testing
from claude_mpm.services.agents.deployment.agent_lifecycle_manager import (
    AgentLifecycleManager,
    AgentLifecycleRecord,
    LifecycleOperation,
    LifecycleOperationResult,
    LifecycleState,
)
from claude_mpm.services.agents.registry.modification_tracker import ModificationTier


class TestAgentLifecycleManagerCore:
    """Test core functionality of AgentLifecycleManager."""

    @pytest_asyncio.fixture
    async def lifecycle_manager(self):
        """Create a test lifecycle manager instance."""
        config = {
            "enable_auto_backup": True,
            "enable_auto_validation": True,
            "enable_cache_invalidation": True,
            "enable_registry_sync": True,
        }

        manager = AgentLifecycleManager(config)

        # Mock the core services to avoid external dependencies
        manager.shared_cache = Mock()
        manager.agent_registry = Mock()
        manager.modification_tracker = AsyncMock()
        manager.persistence_service = AsyncMock()
        manager.agent_manager = Mock()

        # Initialize without calling external services
        manager._initialized = True

        yield manager

        # Cleanup
        if hasattr(manager, "_cleanup"):
            await manager._cleanup()

    @pytest.mark.asyncio
    async def test_initialization():
        """Test AgentLifecycleManager initialization."""
        config = {"enable_auto_backup": False, "enable_auto_validation": False}

        manager = AgentLifecycleManager(config)

        # Check configuration is applied
        assert manager.enable_auto_backup is False
        assert manager.enable_auto_validation is False
        assert manager.enable_cache_invalidation is True  # Default
        assert manager.enable_registry_sync is True  # Default

        # Check initial state
        assert manager.agent_records == {}
        assert manager.operation_history == []
        assert manager.active_operations == {}

        # Check performance metrics initialization
        assert manager.performance_metrics["total_operations"] == 0
        assert manager.performance_metrics["successful_operations"] == 0
        assert manager.performance_metrics["failed_operations"] == 0

    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test health check functionality."""
        # Mock the test methods to return True
        self._test_create_capability = AsyncMock(return_value=True)
        self._test_modify_capability = AsyncMock(return_value=True)
        self._test_delete_capability = AsyncMock(return_value=True)

        health_status = await self.health_check()

        assert health_status["healthy"] is True
        assert health_status["checks"]["cache_service"] is True
        assert health_status["checks"]["registry_service"] is True
        assert health_status["checks"]["tracker_service"] is True
        assert health_status["checks"]["persistence_service"] is True
        assert health_status["checks"]["can_create_agents"] is True
        assert health_status["checks"]["can_modify_agents"] is True
        assert health_status["checks"]["can_delete_agents"] is True

    @pytest.mark.asyncio
    async def test_health_check_with_failures(self):
        """Test health check with service failures."""
        # Simulate service failures
        self.shared_cache = None
        self._test_create_capability = AsyncMock(return_value=False)

        health_status = await self.health_check()

        assert health_status["healthy"] is False
        assert health_status["checks"]["cache_service"] is False
        assert health_status["checks"]["can_create_agents"] is False


class TestAgentLifecycleOperations:
    """Test agent lifecycle operations (create, update, delete)."""

    @pytest_asyncio.fixture
    async def lifecycle_manager(self):
        """Create a test lifecycle manager instance with mocked services."""
        manager = AgentLifecycleManager()

        # Mock all external services
        manager.shared_cache = Mock()
        manager.agent_registry = Mock()
        manager.modification_tracker = AsyncMock()
        manager.persistence_service = AsyncMock()
        manager.agent_manager = Mock()

        # Mock helper methods
        manager._determine_agent_file_path = AsyncMock(
            return_value=Path("/test/agent.md")
        )
        manager._create_backup = AsyncMock(return_value="/test/backup.md")
        manager._invalidate_agent_cache = AsyncMock(return_value=True)
        manager._update_registry = AsyncMock(return_value=True)
        manager._run_sync_in_executor = AsyncMock()

        # Initialize
        manager._initialized = True

        yield manager

    @pytest.mark.asyncio
    async def test_create_agent_success(self):
        """Test successful agent creation."""
        # Setup mocks
        mock_modification = Mock()
        mock_modification.modification_id = "mod_123"
        self.modification_tracker.track_modification.return_value = mock_modification

        mock_persistence = Mock()
        mock_persistence.operation_id = "pers_123"
        self.persistence_service.persist_agent.return_value = mock_persistence

        # Mock file path operations
        with patch("claude_mpm.utils.path_operations.path_ops") as mock_path_ops:
            mock_path_ops.ensure_dir = Mock()
            mock_path_ops.safe_write = Mock()

            # Execute create operation
            result = await self.create_agent(
                agent_name="test_agent",
                agent_content="# Test Agent\nThis is a test agent.",
                tier=ModificationTier.USER,
                agent_type="custom",
            )

        # Verify result
        assert result.success is True
        assert result.operation == LifecycleOperation.CREATE
        assert result.agent_name == "test_agent"
        assert result.modification_id == "mod_123"
        assert result.cache_invalidated is True
        assert result.registry_updated is True

        # Verify agent record was created
        assert "test_agent" in self.agent_records
        record = self.agent_records["test_agent"]
        assert record.agent_name == "test_agent"
        assert record.current_state == LifecycleState.ACTIVE
        assert record.tier == ModificationTier.USER
        assert "mod_123" in record.modifications

    @pytest.mark.asyncio
    async def test_create_agent_duplicate(self):
        """Test creating an agent that already exists."""
        # Add existing agent record
        existing_record = AgentLifecycleRecord(
            agent_name="existing_agent",
            current_state=LifecycleState.ACTIVE,
            tier=ModificationTier.USER,
            file_path="/test/existing.md",
            created_at=time.time(),
            last_modified=time.time(),
            version="1.0.0",
        )
        self.agent_records["existing_agent"] = existing_record

        # Try to create duplicate
        result = await self.create_agent(
            agent_name="existing_agent",
            agent_content="# Duplicate Agent",
            tier=ModificationTier.USER,
        )

        # Should fail
        assert result.success is False
        assert "already exists" in result.error_message.lower()
        assert result.operation == LifecycleOperation.CREATE

    @pytest.mark.asyncio
    async def test_update_agent_success(self):
        """Test successful agent update."""
        # Add existing agent record
        existing_record = AgentLifecycleRecord(
            agent_name="update_agent",
            current_state=LifecycleState.ACTIVE,
            tier=ModificationTier.USER,
            file_path="/test/update.md",
            created_at=time.time(),
            last_modified=time.time(),
            version="1.0.0",
        )
        self.agent_records["update_agent"] = existing_record

        # Setup mocks
        mock_modification = Mock()
        mock_modification.modification_id = "mod_456"
        self.modification_tracker.track_modification.return_value = mock_modification

        mock_persistence = Mock()
        mock_persistence.operation_id = "pers_456"
        self.persistence_service.persist_agent.return_value = mock_persistence

        # Mock file operations
        with patch("claude_mpm.utils.path_operations.path_ops") as mock_path_ops:
            mock_path_ops.safe_write = Mock()

            # Execute update operation
            result = await self.update_agent(
                agent_name="update_agent",
                agent_content="# Updated Agent\nThis is an updated agent.",
            )

        # Verify result
        assert result.success is True
        assert result.operation == LifecycleOperation.UPDATE
        assert result.agent_name == "update_agent"
        assert result.modification_id == "mod_456"

        # Verify agent record was updated
        record = self.agent_records["update_agent"]
        assert record.current_state == LifecycleState.MODIFIED
        assert "mod_456" in record.modifications

    @pytest.mark.asyncio
    async def test_update_agent_not_found(self):
        """Test updating an agent that doesn't exist."""
        result = await self.update_agent(
            agent_name="nonexistent_agent", agent_content="# Nonexistent Agent"
        )

        # Should fail
        assert result.success is False
        assert "not found" in result.error_message.lower()
        assert result.operation == LifecycleOperation.UPDATE

    @pytest.mark.asyncio
    async def test_delete_agent_success(self):
        """Test successful agent deletion."""
        # Add existing agent record
        existing_record = AgentLifecycleRecord(
            agent_name="delete_agent",
            current_state=LifecycleState.ACTIVE,
            tier=ModificationTier.USER,
            file_path="/test/delete.md",
            created_at=time.time(),
            last_modified=time.time(),
            version="1.0.0",
        )
        self.agent_records["delete_agent"] = existing_record

        # Setup mocks
        mock_modification = Mock()
        mock_modification.modification_id = "mod_789"
        self.modification_tracker.track_modification.return_value = mock_modification

        self._create_deletion_backup = AsyncMock(return_value="/test/backup.md")

        # Mock file operations
        with patch("claude_mpm.utils.path_operations.path_ops") as mock_path_ops:
            mock_path_ops.safe_delete = Mock()

            # Execute delete operation
            result = await self.delete_agent(agent_name="delete_agent")

        # Verify result
        assert result.success is True
        assert result.operation == LifecycleOperation.DELETE
        assert result.agent_name == "delete_agent"
        assert result.modification_id == "mod_789"

        # Verify agent record was updated
        record = self.agent_records["delete_agent"]
        assert record.current_state == LifecycleState.DELETED
        assert "mod_789" in record.modifications
        assert "/test/backup.md" in record.backup_paths

    @pytest.mark.asyncio
    async def test_delete_agent_not_found(self):
        """Test deleting an agent that doesn't exist."""
        result = await self.delete_agent(agent_name="nonexistent_agent")

        # Should fail
        assert result.success is False
        assert "not found" in result.error_message.lower()
        assert result.operation == LifecycleOperation.DELETE


class TestAgentLifecycleErrorHandling:
    """Test error handling and edge cases."""

    @pytest_asyncio.fixture
    async def lifecycle_manager(self):
        """Create a test lifecycle manager instance."""
        manager = AgentLifecycleManager()

        # Mock services
        manager.shared_cache = Mock()
        manager.agent_registry = Mock()
        manager.modification_tracker = AsyncMock()
        manager.persistence_service = AsyncMock()
        manager.agent_manager = Mock()

        # Mock helper methods
        manager._determine_agent_file_path = AsyncMock(
            return_value=Path("/test/agent.md")
        )
        manager._create_backup = AsyncMock(return_value="/test/backup.md")
        manager._invalidate_agent_cache = AsyncMock(return_value=True)
        manager._update_registry = AsyncMock(return_value=True)
        manager._run_sync_in_executor = AsyncMock()

        manager._initialized = True
        yield manager

    @pytest.mark.asyncio
    async def test_create_agent_with_tracker_failure(self):
        """Test agent creation when modification tracker fails."""
        # Make modification tracker fail
        self.modification_tracker.track_modification.side_effect = Exception(
            "Tracker failed"
        )

        result = await self.create_agent(
            agent_name="fail_agent",
            agent_content="# Fail Agent",
            tier=ModificationTier.USER,
        )

        # Should fail gracefully
        assert result.success is False
        assert "tracker failed" in result.error_message.lower()
        assert result.operation == LifecycleOperation.CREATE

        # Should not create agent record on failure
        assert "fail_agent" not in self.agent_records

    @pytest.mark.asyncio
    async def test_create_agent_with_persistence_failure(self):
        """Test agent creation when persistence service fails."""
        # Setup successful tracker but failing persistence
        mock_modification = Mock()
        mock_modification.modification_id = "mod_123"
        self.modification_tracker.track_modification.return_value = mock_modification

        self.persistence_service.persist_agent.side_effect = Exception(
            "Persistence failed"
        )

        with patch("claude_mpm.utils.path_operations.path_ops") as mock_path_ops:
            mock_path_ops.ensure_dir = Mock()
            mock_path_ops.safe_write = Mock()

            result = await self.create_agent(
                agent_name="persist_fail_agent",
                agent_content="# Persist Fail Agent",
                tier=ModificationTier.USER,
            )

        # Should fail gracefully
        assert result.success is False
        assert "persistence failed" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_concurrent_operations_on_same_agent(self):
        """Test handling of concurrent operations on the same agent."""
        # Setup mocks for successful operations
        mock_modification = Mock()
        mock_modification.modification_id = "mod_concurrent"
        self.modification_tracker.track_modification.return_value = mock_modification

        mock_persistence = Mock()
        mock_persistence.operation_id = "pers_concurrent"
        self.persistence_service.persist_agent.return_value = mock_persistence

        with patch("claude_mpm.utils.path_operations.path_ops") as mock_path_ops:
            mock_path_ops.ensure_dir = Mock()
            mock_path_ops.safe_write = Mock()

            # Start two concurrent create operations
            task1 = asyncio.create_task(
                self.create_agent(
                    agent_name="concurrent_agent",
                    agent_content="# Concurrent Agent 1",
                    tier=ModificationTier.USER,
                )
            )

            task2 = asyncio.create_task(
                self.create_agent(
                    agent_name="concurrent_agent",
                    agent_content="# Concurrent Agent 2",
                    tier=ModificationTier.USER,
                )
            )

            # Wait for both to complete
            result1, result2 = await asyncio.gather(
                task1, task2, return_exceptions=True
            )

        # One should succeed, one should fail (due to duplicate)
        results = [result1, result2]
        successes = [
            r for r in results if isinstance(r, LifecycleOperationResult) and r.success
        ]
        failures = [
            r
            for r in results
            if isinstance(r, LifecycleOperationResult) and not r.success
        ]

        assert len(successes) == 1
        assert len(failures) == 1
        assert "already exists" in failures[0].error_message.lower()


class TestAgentLifecyclePerformanceMetrics:
    """Test performance monitoring and metrics collection."""

    @pytest_asyncio.fixture
    async def lifecycle_manager(self):
        """Create a test lifecycle manager instance."""
        manager = AgentLifecycleManager()

        # Mock services
        manager.shared_cache = Mock()
        manager.agent_registry = Mock()
        manager.modification_tracker = AsyncMock()
        manager.persistence_service = AsyncMock()
        manager.agent_manager = Mock()

        # Mock helper methods
        manager._determine_agent_file_path = AsyncMock(
            return_value=Path("/test/agent.md")
        )
        manager._create_backup = AsyncMock(return_value="/test/backup.md")
        manager._invalidate_agent_cache = AsyncMock(return_value=True)
        manager._update_registry = AsyncMock(return_value=True)
        manager._run_sync_in_executor = AsyncMock()

        manager._initialized = True
        yield manager

    @pytest.mark.asyncio
    async def test_performance_metrics_tracking(self):
        """Test that performance metrics are properly tracked."""
        # Setup successful operation mocks
        mock_modification = Mock()
        mock_modification.modification_id = "mod_perf"
        self.modification_tracker.track_modification.return_value = mock_modification

        mock_persistence = Mock()
        mock_persistence.operation_id = "pers_perf"
        self.persistence_service.persist_agent.return_value = mock_persistence

        # Check initial metrics
        initial_total = self.performance_metrics["total_operations"]
        initial_successful = self.performance_metrics["successful_operations"]

        with patch("claude_mpm.utils.path_operations.path_ops") as mock_path_ops:
            mock_path_ops.ensure_dir = Mock()
            mock_path_ops.safe_write = Mock()

            # Perform successful operation
            result = await self.create_agent(
                agent_name="perf_agent",
                agent_content="# Performance Agent",
                tier=ModificationTier.USER,
            )

        # Check metrics were updated
        assert result.success is True
        assert self.performance_metrics["total_operations"] == initial_total + 1
        assert (
            self.performance_metrics["successful_operations"] == initial_successful + 1
        )
        assert result.duration_ms > 0

    @pytest.mark.asyncio
    async def test_failed_operation_metrics(self):
        """Test that failed operations are tracked in metrics."""
        # Make operation fail
        self.modification_tracker.track_modification.side_effect = Exception(
            "Test failure"
        )

        initial_total = self.performance_metrics["total_operations"]
        initial_failed = self.performance_metrics["failed_operations"]

        # Perform failing operation
        result = await self.create_agent(
            agent_name="fail_perf_agent",
            agent_content="# Fail Performance Agent",
            tier=ModificationTier.USER,
        )

        # Check metrics were updated
        assert result.success is False
        assert self.performance_metrics["total_operations"] == initial_total + 1
        assert self.performance_metrics["failed_operations"] == initial_failed + 1
