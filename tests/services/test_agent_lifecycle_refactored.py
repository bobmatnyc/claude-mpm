#!/usr/bin/env python3
"""
Comprehensive Unit Tests for Agent Lifecycle Manager Refactoring
================================================================

Tests for the refactored AgentLifecycleManager with extracted services.
Covers all lifecycle operations, state transitions, and service interactions.

Test Coverage:
- Agent creation, update, deletion, restoration
- State transitions and lifecycle tracking
- Service interactions and dependency injection
- Performance metrics and health checks
- Error handling and recovery
- Backward compatibility
"""

import asyncio
import json
import time
from pathlib import Path
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from claude_mpm.services.agents.deployment.agent_lifecycle_manager_refactored import (
    AgentLifecycleManager,
    AgentLifecycleRecord,
    LifecycleOperation,
    LifecycleOperationResult,
    LifecycleState,
)
from claude_mpm.services.agents.registry.modification_tracker import (
    AgentModification,
    ModificationTier,
    ModificationType,
)


class TestAgentLifecycleManager:
    """Test suite for AgentLifecycleManager."""

    @pytest.fixture
    def mock_config(self) -> Dict[str, Any]:
        """Mock configuration for testing."""
        return {
            "enable_auto_backup": True,
            "enable_auto_validation": True,
            "enable_cache_invalidation": True,
            "enable_registry_sync": True,
            "default_persistence_strategy": "USER_OVERRIDE",
        }

    @pytest.fixture
    def mock_dependencies(self):
        """Mock all external dependencies."""
        with patch(
            "claude_mpm.services.agents.deployment.agent_lifecycle_manager.SharedPromptCache"
        ) as mock_cache, patch(
            "claude_mpm.services.agents.deployment.agent_lifecycle_manager.AgentRegistry"
        ) as mock_registry, patch(
            "claude_mpm.services.agents.deployment.agent_lifecycle_manager.AgentModificationTracker"
        ) as mock_tracker, patch(
            "claude_mpm.services.agents.deployment.agent_lifecycle_manager.AgentPersistenceService"
        ) as mock_persistence, patch(
            "claude_mpm.services.agents.deployment.agent_lifecycle_manager.AgentManager"
        ) as mock_manager, patch(
            "claude_mpm.services.agents.deployment.agent_lifecycle_manager.ConfigurationManager"
        ) as mock_config_mgr:

            # Setup mock cache
            mock_cache_instance = Mock()
            mock_cache_instance.invalidate = Mock(return_value=True)
            mock_cache.get_instance.return_value = mock_cache_instance

            # Setup mock registry
            mock_registry_instance = Mock()
            mock_registry_instance.discover_agents = Mock()
            mock_registry_instance.list_agents = Mock(return_value=[])

            # Setup mock tracker
            mock_tracker_instance = Mock()
            mock_tracker_instance.start = AsyncMock()
            mock_tracker_instance.stop = AsyncMock()
            mock_tracker_instance.track_modification = AsyncMock()
            mock_tracker_instance.register_modification_callback = Mock()

            # Setup mock persistence
            mock_persistence_instance = Mock()
            mock_persistence_instance.start = AsyncMock()
            mock_persistence_instance.stop = AsyncMock()

            # Setup mock manager
            mock_manager_instance = Mock()
            mock_manager_instance.create_agent = Mock(return_value="/path/to/agent.py")
            mock_manager_instance.read_agent = Mock(return_value=None)
            mock_manager_instance.update_agent = Mock(return_value=None)
            mock_manager_instance.delete_agent = Mock(return_value=True)

            # Setup mock config manager
            mock_config_mgr_instance = Mock()
            mock_config_mgr_instance.load_json = Mock(return_value={})

            yield {
                "cache": mock_cache_instance,
                "cache_class": mock_cache,
                "registry": mock_registry_instance,
                "registry_class": mock_registry,
                "tracker": mock_tracker_instance,
                "tracker_class": mock_tracker,
                "persistence": mock_persistence_instance,
                "persistence_class": mock_persistence,
                "manager": mock_manager_instance,
                "manager_class": mock_manager,
                "config_mgr": mock_config_mgr_instance,
                "config_mgr_class": mock_config_mgr,
            }

    @pytest.fixture
    async def lifecycle_manager(self, mock_config, mock_dependencies):
        """Create a lifecycle manager instance for testing."""
        manager = AgentLifecycleManager(mock_config)

        # Inject mocked dependencies
        manager.shared_cache = mock_dependencies["cache"]
        manager.agent_registry = mock_dependencies["registry"]()
        manager.modification_tracker = mock_dependencies["tracker"]()
        manager.persistence_service = mock_dependencies["persistence"]()
        manager.agent_manager = mock_dependencies["manager"]()
        manager.config_mgr = mock_dependencies["config_mgr"]()

        return manager

    # Test 1: Agent Creation
    @pytest.mark.asyncio
    async def test_create_agent_success(self, lifecycle_manager, mock_dependencies):
        """Test successful agent creation."""
        # Setup mock modification
        mock_modification = AgentModification(
            modification_id="mod_123",
            agent_name="test_agent",
            modification_type=ModificationType.CREATE,
            file_path="/path/to/agent.py",
            tier=ModificationTier.USER,
            timestamp=time.time(),
        )
        mock_dependencies["tracker"].track_modification.return_value = mock_modification

        # Execute creation
        result = await lifecycle_manager.create_agent(
            agent_name="test_agent",
            agent_content="# Test Agent Content",
            tier=ModificationTier.USER,
            agent_type="custom",
        )

        # Verify result
        assert result.success is True
        assert result.operation == LifecycleOperation.CREATE
        assert result.agent_name == "test_agent"
        assert result.modification_id == "mod_123"
        assert result.duration_ms > 0

        # Verify lifecycle record created
        assert "test_agent" in lifecycle_manager.agent_records
        record = lifecycle_manager.agent_records["test_agent"]
        assert record.current_state == LifecycleState.ACTIVE
        assert record.tier == ModificationTier.USER

    # Test 2: Agent Creation - Already Exists
    @pytest.mark.asyncio
    async def test_create_agent_already_exists(self, lifecycle_manager):
        """Test agent creation when agent already exists."""
        # Add existing agent record
        lifecycle_manager.agent_records["existing_agent"] = AgentLifecycleRecord(
            agent_name="existing_agent",
            current_state=LifecycleState.ACTIVE,
            tier=ModificationTier.USER,
            file_path="/path/to/existing.py",
            created_at=time.time(),
            last_modified=time.time(),
            version="1.0.0",
        )

        # Attempt to create duplicate
        result = await lifecycle_manager.create_agent(
            agent_name="existing_agent",
            agent_content="# Duplicate Content",
        )

        # Verify failure
        assert result.success is False
        assert result.error_message == "Agent already exists"

    # Test 3: Agent Update
    @pytest.mark.asyncio
    async def test_update_agent_success(self, lifecycle_manager, mock_dependencies):
        """Test successful agent update."""
        # Add existing agent record
        lifecycle_manager.agent_records["update_agent"] = AgentLifecycleRecord(
            agent_name="update_agent",
            current_state=LifecycleState.ACTIVE,
            tier=ModificationTier.USER,
            file_path="/path/to/update.py",
            created_at=time.time(),
            last_modified=time.time(),
            version="1.0.0",
        )

        # Setup mock modification
        mock_modification = AgentModification(
            modification_id="mod_456",
            agent_name="update_agent",
            modification_type=ModificationType.MODIFY,
            file_path="/path/to/update.py",
            tier=ModificationTier.USER,
            timestamp=time.time(),
        )
        mock_dependencies["tracker"].track_modification.return_value = mock_modification

        # Execute update
        result = await lifecycle_manager.update_agent(
            agent_name="update_agent",
            agent_content="# Updated Content",
        )

        # Verify result
        assert result.success is True
        assert result.operation == LifecycleOperation.UPDATE
        assert result.modification_id == "mod_456"

        # Verify record updated
        record = lifecycle_manager.agent_records["update_agent"]
        assert record.current_state == LifecycleState.MODIFIED
        assert record.version == "1.0.1"  # Version incremented

    # Test 4: Agent Update - Not Found
    @pytest.mark.asyncio
    async def test_update_agent_not_found(self, lifecycle_manager):
        """Test agent update when agent doesn't exist."""
        result = await lifecycle_manager.update_agent(
            agent_name="nonexistent_agent",
            agent_content="# Content",
        )

        assert result.success is False
        assert result.error_message == "Agent not found"

    # Test 5: Agent Deletion
    @pytest.mark.asyncio
    async def test_delete_agent_success(self, lifecycle_manager, mock_dependencies):
        """Test successful agent deletion."""
        # Add existing agent record
        lifecycle_manager.agent_records["delete_agent"] = AgentLifecycleRecord(
            agent_name="delete_agent",
            current_state=LifecycleState.ACTIVE,
            tier=ModificationTier.USER,
            file_path="/path/to/delete.py",
            created_at=time.time(),
            last_modified=time.time(),
            version="1.0.0",
        )

        # Setup mock modification
        mock_modification = AgentModification(
            modification_id="mod_789",
            agent_name="delete_agent",
            modification_type=ModificationType.DELETE,
            file_path="/path/to/delete.py",
            tier=ModificationTier.USER,
            timestamp=time.time(),
        )
        mock_dependencies["tracker"].track_modification.return_value = mock_modification

        # Execute deletion
        result = await lifecycle_manager.delete_agent(agent_name="delete_agent")

        # Verify result
        assert result.success is True
        assert result.operation == LifecycleOperation.DELETE
        assert result.modification_id == "mod_789"

        # Verify record updated
        record = lifecycle_manager.agent_records["delete_agent"]
        assert record.current_state == LifecycleState.DELETED

    # Test 6: Agent Deletion - Not Found
    @pytest.mark.asyncio
    async def test_delete_agent_not_found(self, lifecycle_manager):
        """Test agent deletion when agent doesn't exist."""
        result = await lifecycle_manager.delete_agent(agent_name="nonexistent_agent")

        assert result.success is False
        assert result.error_message == "Agent not found"

    # Test 7: State Transitions
    @pytest.mark.asyncio
    async def test_state_transitions(self, lifecycle_manager, mock_dependencies):
        """Test agent state transitions through lifecycle."""
        # Setup mocks
        mock_modification = AgentModification(
            modification_id="mod_state",
            agent_name="state_agent",
            modification_type=ModificationType.CREATE,
            file_path="/path/to/state.py",
            tier=ModificationTier.USER,
            timestamp=time.time(),
        )
        mock_dependencies["tracker"].track_modification.return_value = mock_modification

        # Create agent (ACTIVE state)
        await lifecycle_manager.create_agent(
            agent_name="state_agent",
            agent_content="# State Test",
        )
        record = lifecycle_manager.agent_records["state_agent"]
        assert record.current_state == LifecycleState.ACTIVE

        # Update agent (MODIFIED state)
        mock_modification.modification_type = ModificationType.MODIFY
        await lifecycle_manager.update_agent(
            agent_name="state_agent",
            agent_content="# Modified",
        )
        assert record.current_state == LifecycleState.MODIFIED

        # Delete agent (DELETED state)
        mock_modification.modification_type = ModificationType.DELETE
        await lifecycle_manager.delete_agent(agent_name="state_agent")
        assert record.current_state == LifecycleState.DELETED

    # Test 8: Cache Invalidation
    @pytest.mark.asyncio
    async def test_cache_invalidation(self, lifecycle_manager):
        """Test cache invalidation during operations."""
        lifecycle_manager.enable_cache_invalidation = True

        # Test cache invalidation
        result = await lifecycle_manager._invalidate_agent_cache("test_agent")
        assert result is True

        # Verify cache invalidate was called
        lifecycle_manager.shared_cache.invalidate.assert_called()

    # Test 9: Registry Synchronization
    @pytest.mark.asyncio
    async def test_registry_sync(self, lifecycle_manager):
        """Test registry synchronization."""
        lifecycle_manager.enable_registry_sync = True

        # Test registry update
        result = await lifecycle_manager._update_registry("test_agent")
        assert result is True

        # Verify registry discover was called
        lifecycle_manager.agent_registry.discover_agents.assert_called()

    # Test 10: Performance Metrics
    @pytest.mark.asyncio
    async def test_performance_metrics_tracking(self, lifecycle_manager):
        """Test performance metrics are tracked correctly."""
        # Create successful operation result
        result = LifecycleOperationResult(
            operation=LifecycleOperation.CREATE,
            agent_name="metrics_agent",
            success=True,
            duration_ms=100.5,
        )

        # Update metrics
        await lifecycle_manager._update_performance_metrics(result)

        # Verify metrics updated
        metrics = lifecycle_manager.performance_metrics
        assert metrics["total_operations"] > 0
        assert metrics["successful_operations"] > 0

    # Test 11: Concurrent Operations
    @pytest.mark.asyncio
    async def test_concurrent_operations_locking(
        self, lifecycle_manager, mock_dependencies
    ):
        """Test that concurrent operations are properly serialized."""
        # Setup mock
        mock_modification = AgentModification(
            modification_id="mod_concurrent",
            agent_name="concurrent_agent",
            modification_type=ModificationType.CREATE,
            file_path="/path/to/concurrent.py",
            tier=ModificationTier.USER,
            timestamp=time.time(),
        )
        mock_dependencies["tracker"].track_modification.return_value = mock_modification

        # Create multiple concurrent operations
        tasks = [
            lifecycle_manager.create_agent(f"agent_{i}", f"# Content {i}")
            for i in range(5)
        ]

        # Execute concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Verify all completed without exceptions
        for result in results:
            assert not isinstance(result, Exception)

    # Test 12: Get Agent Status
    @pytest.mark.asyncio
    async def test_get_agent_status(self, lifecycle_manager):
        """Test retrieving agent status."""
        # Add test record
        test_record = AgentLifecycleRecord(
            agent_name="status_agent",
            current_state=LifecycleState.ACTIVE,
            tier=ModificationTier.USER,
            file_path="/path/to/status.py",
            created_at=time.time(),
            last_modified=time.time(),
            version="1.0.0",
        )
        lifecycle_manager.agent_records["status_agent"] = test_record

        # Get status
        status = await lifecycle_manager.get_agent_status("status_agent")
        assert status == test_record

        # Get non-existent status
        status = await lifecycle_manager.get_agent_status("nonexistent")
        assert status is None

    # Test 13: List Agents with Filtering
    @pytest.mark.asyncio
    async def test_list_agents_with_filter(self, lifecycle_manager):
        """Test listing agents with state filtering."""
        # Add test records with different states
        lifecycle_manager.agent_records = {
            "active1": AgentLifecycleRecord(
                agent_name="active1",
                current_state=LifecycleState.ACTIVE,
                tier=ModificationTier.USER,
                file_path="/path/1.py",
                created_at=time.time(),
                last_modified=time.time(),
                version="1.0.0",
            ),
            "modified1": AgentLifecycleRecord(
                agent_name="modified1",
                current_state=LifecycleState.MODIFIED,
                tier=ModificationTier.USER,
                file_path="/path/2.py",
                created_at=time.time(),
                last_modified=time.time() + 1,
                version="1.0.1",
            ),
            "deleted1": AgentLifecycleRecord(
                agent_name="deleted1",
                current_state=LifecycleState.DELETED,
                tier=ModificationTier.USER,
                file_path="/path/3.py",
                created_at=time.time(),
                last_modified=time.time() + 2,
                version="1.0.0",
            ),
        }

        # List all agents
        all_agents = await lifecycle_manager.list_agents()
        assert len(all_agents) == 3

        # List only active agents
        active_agents = await lifecycle_manager.list_agents(LifecycleState.ACTIVE)
        assert len(active_agents) == 1
        assert active_agents[0].agent_name == "active1"

        # List only deleted agents
        deleted_agents = await lifecycle_manager.list_agents(LifecycleState.DELETED)
        assert len(deleted_agents) == 1
        assert deleted_agents[0].agent_name == "deleted1"

    # Test 14: Operation History
    @pytest.mark.asyncio
    async def test_operation_history(self, lifecycle_manager):
        """Test retrieving operation history."""
        # Add test operations
        lifecycle_manager.operation_history = [
            LifecycleOperationResult(
                operation=LifecycleOperation.CREATE,
                agent_name="agent1",
                success=True,
                duration_ms=50.0,
            ),
            LifecycleOperationResult(
                operation=LifecycleOperation.UPDATE,
                agent_name="agent1",
                success=True,
                duration_ms=30.0,
            ),
            LifecycleOperationResult(
                operation=LifecycleOperation.DELETE,
                agent_name="agent2",
                success=False,
                duration_ms=100.0,
                error_message="Failed",
            ),
        ]

        # Get all history
        history = await lifecycle_manager.get_operation_history()
        assert len(history) == 3

        # Get history for specific agent
        agent1_history = await lifecycle_manager.get_operation_history("agent1")
        assert len(agent1_history) == 2

        # Get limited history
        limited = await lifecycle_manager.get_operation_history(limit=2)
        assert len(limited) == 2

    # Test 15: Lifecycle Statistics
    @pytest.mark.asyncio
    async def test_lifecycle_statistics(self, lifecycle_manager):
        """Test lifecycle statistics generation."""
        # Setup test data
        lifecycle_manager.agent_records = {
            "agent1": AgentLifecycleRecord(
                agent_name="agent1",
                current_state=LifecycleState.ACTIVE,
                tier=ModificationTier.USER,
                file_path="/path/1.py",
                created_at=time.time(),
                last_modified=time.time(),
                version="1.0.0",
            ),
            "agent2": AgentLifecycleRecord(
                agent_name="agent2",
                current_state=LifecycleState.MODIFIED,
                tier=ModificationTier.PROJECT,
                file_path="/path/2.py",
                created_at=time.time(),
                last_modified=time.time(),
                version="1.0.1",
            ),
        }

        lifecycle_manager.operation_history = [
            LifecycleOperationResult(
                operation=LifecycleOperation.CREATE,
                agent_name="agent1",
                success=True,
                duration_ms=50.0,
            ),
        ]

        # Get statistics
        stats = await lifecycle_manager.get_lifecycle_stats()

        # Verify statistics
        assert stats["total_agents"] == 2
        assert stats["agents_by_state"]["active"] == 1
        assert stats["agents_by_state"]["modified"] == 1
        assert stats["agents_by_tier"]["user"] == 1
        assert stats["agents_by_tier"]["project"] == 1

    # Test 16: Auto-Backup on Deletion
    @pytest.mark.asyncio
    async def test_auto_backup_on_deletion(self, lifecycle_manager, mock_dependencies):
        """Test automatic backup creation during deletion."""
        with patch("claude_mpm.utils.path_operations.path_ops") as mock_path_ops:
            mock_path_ops.validate_exists.return_value = True
            mock_path_ops.safe_copy.return_value = None

            lifecycle_manager.enable_auto_backup = True

            # Add agent record
            lifecycle_manager.agent_records["backup_agent"] = AgentLifecycleRecord(
                agent_name="backup_agent",
                current_state=LifecycleState.ACTIVE,
                tier=ModificationTier.USER,
                file_path="/path/to/backup.py",
                created_at=time.time(),
                last_modified=time.time(),
                version="1.0.0",
            )

            # Setup mock modification
            mock_modification = AgentModification(
                modification_id="mod_backup",
                agent_name="backup_agent",
                modification_type=ModificationType.DELETE,
                file_path="/path/to/backup.py",
                tier=ModificationTier.USER,
                timestamp=time.time(),
            )
            mock_dependencies["tracker"].track_modification.return_value = (
                mock_modification
            )

            # Delete agent
            await lifecycle_manager.delete_agent("backup_agent")

            # Verify backup was attempted
            mock_path_ops.safe_copy.assert_called()

    # Test 17: Error Handling - Service Initialization
    @pytest.mark.asyncio
    async def test_error_handling_service_init(self, mock_config):
        """Test error handling during service initialization."""
        with patch(
            "claude_mpm.services.agents.deployment.agent_lifecycle_manager.SharedPromptCache"
        ) as mock_cache:
            mock_cache.get_instance.side_effect = Exception("Cache init failed")

            manager = AgentLifecycleManager(mock_config)

            # Initialize should handle the error gracefully
            with pytest.raises(Exception, match="Cache init failed"):
                await manager._initialize_core_services()

    # Test 18: Modification Event Handling
    @pytest.mark.asyncio
    async def test_modification_event_handling(self, lifecycle_manager):
        """Test handling of modification events from tracker."""
        # Add agent record
        lifecycle_manager.agent_records["event_agent"] = AgentLifecycleRecord(
            agent_name="event_agent",
            current_state=LifecycleState.ACTIVE,
            tier=ModificationTier.USER,
            file_path="/path/to/event.py",
            created_at=time.time(),
            last_modified=time.time(),
            version="1.0.0",
        )

        # Create modification event
        modification = AgentModification(
            modification_id="mod_event",
            agent_name="event_agent",
            modification_type=ModificationType.MODIFY,
            file_path="/path/to/event.py",
            tier=ModificationTier.USER,
            timestamp=time.time() + 100,
        )

        # Handle event
        await lifecycle_manager._handle_modification_event(modification)

        # Verify record updated
        record = lifecycle_manager.agent_records["event_agent"]
        assert record.current_state == LifecycleState.MODIFIED
        assert record.last_modified == modification.timestamp
        assert "mod_event" in record.modifications

    # Test 19: Tier-Based File Path Resolution
    @pytest.mark.asyncio
    async def test_tier_based_file_path_resolution(self, lifecycle_manager):
        """Test file path determination based on tier."""
        with patch("claude_mpm.core.unified_paths.get_path_manager") as mock_path_mgr:
            mock_manager_instance = Mock()
            mock_manager_instance.get_user_agents_dir.return_value = Path(
                "/user/agents"
            )
            mock_manager_instance.get_project_agents_dir.return_value = Path(
                "/project/agents"
            )
            mock_path_mgr.return_value = mock_manager_instance

            # Test USER tier
            user_path = await lifecycle_manager._determine_agent_file_path(
                "test_agent", ModificationTier.USER
            )
            assert str(user_path) == "/user/agents/test_agent_agent.py"

            # Test PROJECT tier
            project_path = await lifecycle_manager._determine_agent_file_path(
                "test_agent", ModificationTier.PROJECT
            )
            assert str(project_path) == "/project/agents/test_agent_agent.py"

            # Test SYSTEM tier
            system_path = await lifecycle_manager._determine_agent_file_path(
                "test_agent", ModificationTier.SYSTEM
            )
            assert "claude_pm/agents" in str(system_path)

    # Test 20: Persistence and Storage
    @pytest.mark.asyncio
    async def test_persistence_storage(self, lifecycle_manager):
        """Test saving and loading agent records."""
        with patch("claude_mpm.core.unified_paths.get_path_manager") as mock_path_mgr:
            # Setup mock path manager
            mock_manager_instance = Mock()
            mock_tracking_dir = Path("/tracking")
            mock_manager_instance.get_tracking_dir.return_value = mock_tracking_dir
            mock_path_mgr.return_value = mock_manager_instance

            # Add test records
            lifecycle_manager.agent_records = {
                "persist_agent": AgentLifecycleRecord(
                    agent_name="persist_agent",
                    current_state=LifecycleState.ACTIVE,
                    tier=ModificationTier.USER,
                    file_path="/path/to/persist.py",
                    created_at=time.time(),
                    last_modified=time.time(),
                    version="1.0.0",
                )
            }

            # Mock file operations
            with patch("builtins.open", create=True) as mock_open:
                mock_file = MagicMock()
                mock_open.return_value.__enter__.return_value = mock_file

                # Save records
                await lifecycle_manager._save_agent_records()

                # Verify write was called
                mock_file.write.assert_called()

                # Verify JSON format
                written_data = mock_file.write.call_args[0][0]
                parsed = json.loads(written_data)
                assert "persist_agent" in parsed
                assert parsed["persist_agent"]["current_state"] == "active"

    # Test 21: Service Integration Setup
    @pytest.mark.asyncio
    async def test_service_integration_setup(self, lifecycle_manager):
        """Test service integration setup and callbacks."""
        # Verify modification callback registered
        lifecycle_manager.modification_tracker.register_modification_callback.assert_called_with(
            lifecycle_manager._handle_modification_event
        )

    # Test 22: Health Check Integration
    @pytest.mark.asyncio
    async def test_health_check_integration(self, lifecycle_manager):
        """Test health check functionality."""
        with patch(
            "claude_mpm.services.agents.deployment.agent_lifecycle_manager.LifecycleHealthChecker"
        ) as mock_checker:
            mock_checker_instance = Mock()
            mock_checker_instance.perform_health_check = AsyncMock(
                return_value={"status": "healthy"}
            )
            mock_checker.return_value = mock_checker_instance

            # Perform health check
            health = await lifecycle_manager._health_check()

            # Verify health check called
            assert health == {"status": "healthy"}
            mock_checker_instance.perform_health_check.assert_called_once()

    # Test 23: Agent Restoration
    @pytest.mark.asyncio
    async def test_agent_restoration(self, lifecycle_manager):
        """Test agent restoration from backup."""
        with patch(
            "claude_mpm.services.agents.deployment.agent_lifecycle_manager.AgentRestoreHandler"
        ) as mock_handler:
            mock_handler_instance = Mock()
            mock_handler_instance.restore_agent = AsyncMock(
                return_value=LifecycleOperationResult(
                    operation=LifecycleOperation.RESTORE,
                    agent_name="restored_agent",
                    success=True,
                    duration_ms=100.0,
                )
            )
            mock_handler.return_value = mock_handler_instance

            # Restore agent
            result = await lifecycle_manager.restore_agent(
                "restored_agent", "/backup/path.py"
            )

            # Verify restoration
            assert result.success is True
            assert result.operation == LifecycleOperation.RESTORE
            mock_handler_instance.restore_agent.assert_called_with(
                "restored_agent", "/backup/path.py"
            )

    # Test 24: Version Management
    @pytest.mark.asyncio
    async def test_version_management(self, lifecycle_manager, mock_dependencies):
        """Test version tracking and incrementing."""
        # Add agent with initial version
        lifecycle_manager.agent_records["version_agent"] = AgentLifecycleRecord(
            agent_name="version_agent",
            current_state=LifecycleState.ACTIVE,
            tier=ModificationTier.USER,
            file_path="/path/to/version.py",
            created_at=time.time(),
            last_modified=time.time(),
            version="1.2.3",
        )

        # Setup mock modification
        mock_modification = AgentModification(
            modification_id="mod_version",
            agent_name="version_agent",
            modification_type=ModificationType.MODIFY,
            file_path="/path/to/version.py",
            tier=ModificationTier.USER,
            timestamp=time.time(),
        )
        mock_dependencies["tracker"].track_modification.return_value = mock_modification

        # Update agent multiple times
        for i in range(3):
            await lifecycle_manager.update_agent(
                agent_name="version_agent",
                agent_content=f"# Version {i}",
            )

        # Verify version incremented correctly
        record = lifecycle_manager.agent_records["version_agent"]
        assert record.version == "1.2.6"  # Incremented 3 times

    # Test 25: Cleanup and Resource Management
    @pytest.mark.asyncio
    async def test_cleanup_resource_management(self, lifecycle_manager):
        """Test proper cleanup of resources."""
        # Add some test data
        lifecycle_manager.agent_records = {"test": Mock()}
        lifecycle_manager.operation_history = [Mock()]

        # Mock save method
        lifecycle_manager._save_agent_records = AsyncMock()

        # Perform cleanup
        await lifecycle_manager._cleanup()

        # Verify services stopped
        lifecycle_manager.modification_tracker.stop.assert_called_once()
        lifecycle_manager.persistence_service.stop.assert_called_once()

        # Verify records saved
        lifecycle_manager._save_agent_records.assert_called_once()


class TestLifecycleRecordDataClass:
    """Test AgentLifecycleRecord dataclass functionality."""

    def test_lifecycle_record_age_calculation(self):
        """Test age calculation in days."""
        created_time = time.time() - (3 * 24 * 3600)  # 3 days ago
        record = AgentLifecycleRecord(
            agent_name="test",
            current_state=LifecycleState.ACTIVE,
            tier=ModificationTier.USER,
            file_path="/test.py",
            created_at=created_time,
            last_modified=time.time(),
            version="1.0.0",
        )

        assert 2.9 < record.age_days < 3.1  # Allow for small time differences

    def test_lifecycle_record_datetime_conversion(self):
        """Test datetime conversion."""
        current_time = time.time()
        record = AgentLifecycleRecord(
            agent_name="test",
            current_state=LifecycleState.ACTIVE,
            tier=ModificationTier.USER,
            file_path="/test.py",
            created_at=current_time,
            last_modified=current_time,
            version="1.0.0",
        )

        dt = record.last_modified_datetime
        assert dt.timestamp() == pytest.approx(current_time, rel=1e-3)


class TestLifecycleOperationResult:
    """Test LifecycleOperationResult dataclass."""

    def test_operation_result_success(self):
        """Test successful operation result."""
        result = LifecycleOperationResult(
            operation=LifecycleOperation.CREATE,
            agent_name="test",
            success=True,
            duration_ms=50.5,
            modification_id="mod_123",
            persistence_id="persist_123",
            cache_invalidated=True,
            registry_updated=True,
        )

        assert result.success is True
        assert result.error_message is None
        assert result.duration_ms == 50.5

    def test_operation_result_failure(self):
        """Test failed operation result."""
        result = LifecycleOperationResult(
            operation=LifecycleOperation.DELETE,
            agent_name="test",
            success=False,
            duration_ms=10.0,
            error_message="Permission denied",
        )

        assert result.success is False
        assert result.error_message == "Permission denied"
        assert result.modification_id is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
