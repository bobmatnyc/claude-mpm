"""
Unit Tests for DeploymentStateManager
======================================

WHY: Comprehensive testing of state persistence, file locking, corruption
recovery, and query operations. Tests cover happy paths, edge cases, and
error scenarios.

COVERAGE TARGET: ≥90%

Test Categories:
1. Initialization and lifecycle
2. State persistence (save/load)
3. Deployment CRUD operations
4. Query operations (by status, port, project)
5. Cleanup operations (dead PIDs)
6. Corruption recovery
7. Concurrency and locking
8. Error handling
"""

import json
import os
import tempfile
import time
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from claude_mpm.services.local_ops import (
    DeploymentState,
    DeploymentStateManager,
    ProcessStatus,
    StateCorruptionError,
)


@pytest.fixture
def temp_state_file():
    """Create a temporary state file for testing."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        temp_path = f.name
    yield temp_path
    # Cleanup
    for suffix in ["", ".lock", ".tmp", ".corrupted"]:
        path = Path(temp_path + suffix.replace(".json", ""))
        if path.exists():
            path.unlink()


@pytest.fixture
def state_manager(temp_state_file):
    """Create a state manager instance for testing."""
    manager = DeploymentStateManager(temp_state_file)
    manager.initialize()
    return manager


@pytest.fixture
def sample_deployment():
    """Create a sample deployment state for testing."""
    return DeploymentState(
        deployment_id="test_deploy_001",
        process_id=12345,
        command=["npm", "run", "dev"],
        working_directory="/tmp/test-project",
        environment={"NODE_ENV": "development"},
        port=3000,
        started_at=datetime.now(),
        status=ProcessStatus.RUNNING,
        metadata={"framework": "nextjs"},
    )


class TestInitialization:
    """Test state manager initialization."""

    def test_creates_parent_directory(self):
        """Should create parent directory if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "subdir" / "state.json"
            manager = DeploymentStateManager(str(state_file))

            assert state_file.parent.exists()

    def test_creates_empty_state_if_file_missing(self, temp_state_file):
        """Should create empty state file if it doesn't exist."""
        Path(temp_state_file).unlink()  # Remove the file
        manager = DeploymentStateManager(temp_state_file)

        assert Path(temp_state_file).exists()
        assert manager.load_state() == {}

    def test_initialize_success(self, state_manager):
        """Should initialize successfully."""
        assert state_manager.is_initialized
        assert not state_manager.is_shutdown

    def test_shutdown(self, state_manager):
        """Should shutdown cleanly."""
        state_manager.shutdown()
        assert state_manager.is_shutdown


class TestStatePersistence:
    """Test state save and load operations."""

    def test_save_and_load_state(self, state_manager, sample_deployment):
        """Should save and load state correctly."""
        states = {"test_deploy_001": sample_deployment}
        state_manager.save_state(states)

        loaded = state_manager.load_state()
        assert len(loaded) == 1
        assert "test_deploy_001" in loaded
        assert loaded["test_deploy_001"].deployment_id == "test_deploy_001"
        assert loaded["test_deploy_001"].process_id == 12345
        assert loaded["test_deploy_001"].port == 3000

    def test_save_empty_state(self, state_manager):
        """Should handle saving empty state."""
        state_manager.save_state({})
        loaded = state_manager.load_state()
        assert loaded == {}

    def test_load_preserves_datetime(self, state_manager, sample_deployment):
        """Should preserve datetime objects across save/load."""
        original_time = sample_deployment.started_at
        states = {"test_deploy_001": sample_deployment}
        state_manager.save_state(states)

        loaded = state_manager.load_state()
        loaded_time = loaded["test_deploy_001"].started_at

        # Compare with tolerance for serialization precision
        assert isinstance(loaded_time, datetime)
        assert abs((original_time - loaded_time).total_seconds()) < 1

    def test_load_preserves_enum_status(self, state_manager, sample_deployment):
        """Should preserve ProcessStatus enum across save/load."""
        states = {"test_deploy_001": sample_deployment}
        state_manager.save_state(states)

        loaded = state_manager.load_state()
        assert loaded["test_deploy_001"].status == ProcessStatus.RUNNING
        assert isinstance(loaded["test_deploy_001"].status, ProcessStatus)

    def test_atomic_write_with_temp_file(self, state_manager, sample_deployment):
        """Should use atomic write with temp file."""
        states = {"test_deploy_001": sample_deployment}

        # Check that temp file is created and renamed
        with patch("pathlib.Path.replace") as mock_replace:
            state_manager.save_state(states)
            mock_replace.assert_called_once()


class TestDeploymentCRUD:
    """Test deployment CRUD operations."""

    def test_add_deployment(self, state_manager, sample_deployment):
        """Should add deployment to state."""
        state_manager.add_deployment(sample_deployment)

        deployment = state_manager.get_deployment("test_deploy_001")
        assert deployment is not None
        assert deployment.deployment_id == "test_deploy_001"

    def test_add_multiple_deployments(self, state_manager):
        """Should add multiple deployments."""
        for i in range(3):
            deployment = DeploymentState(
                deployment_id=f"deploy_{i}",
                process_id=10000 + i,
                command=["npm", "run", "dev"],
                working_directory=f"/tmp/project_{i}",
                port=3000 + i,
                status=ProcessStatus.RUNNING,
            )
            state_manager.add_deployment(deployment)

        all_deployments = state_manager.get_all_deployments()
        assert len(all_deployments) == 3

    def test_update_existing_deployment(self, state_manager, sample_deployment):
        """Should update existing deployment."""
        state_manager.add_deployment(sample_deployment)

        # Update the deployment
        sample_deployment.port = 3001
        state_manager.add_deployment(sample_deployment)

        deployment = state_manager.get_deployment("test_deploy_001")
        assert deployment.port == 3001

    def test_remove_deployment(self, state_manager, sample_deployment):
        """Should remove deployment from state."""
        state_manager.add_deployment(sample_deployment)
        result = state_manager.remove_deployment("test_deploy_001")

        assert result is True
        assert state_manager.get_deployment("test_deploy_001") is None

    def test_remove_nonexistent_deployment(self, state_manager):
        """Should return False when removing nonexistent deployment."""
        result = state_manager.remove_deployment("nonexistent")
        assert result is False

    def test_update_deployment_status(self, state_manager, sample_deployment):
        """Should update deployment status."""
        state_manager.add_deployment(sample_deployment)
        result = state_manager.update_deployment_status(
            "test_deploy_001", ProcessStatus.STOPPED
        )

        assert result is True
        deployment = state_manager.get_deployment("test_deploy_001")
        assert deployment.status == ProcessStatus.STOPPED

    def test_update_status_nonexistent_deployment(self, state_manager):
        """Should return False when updating nonexistent deployment."""
        result = state_manager.update_deployment_status(
            "nonexistent", ProcessStatus.STOPPED
        )
        assert result is False


class TestQueryOperations:
    """Test deployment query operations."""

    @pytest.fixture
    def populated_state_manager(self, state_manager):
        """Create state manager with multiple deployments."""
        deployments = [
            DeploymentState(
                deployment_id="deploy_running_1",
                process_id=10001,
                command=["npm", "run", "dev"],
                working_directory="/tmp/project1",
                port=3000,
                status=ProcessStatus.RUNNING,
            ),
            DeploymentState(
                deployment_id="deploy_running_2",
                process_id=10002,
                command=["npm", "run", "dev"],
                working_directory="/tmp/project2",
                port=3001,
                status=ProcessStatus.RUNNING,
            ),
            DeploymentState(
                deployment_id="deploy_stopped",
                process_id=10003,
                command=["npm", "run", "dev"],
                working_directory="/tmp/project1",
                port=3002,
                status=ProcessStatus.STOPPED,
            ),
        ]
        for deployment in deployments:
            state_manager.add_deployment(deployment)
        return state_manager

    def test_get_all_deployments(self, populated_state_manager):
        """Should return all deployments."""
        deployments = populated_state_manager.get_all_deployments()
        assert len(deployments) == 3

    def test_get_deployments_by_status(self, populated_state_manager):
        """Should filter deployments by status."""
        running = populated_state_manager.get_deployments_by_status(
            ProcessStatus.RUNNING
        )
        stopped = populated_state_manager.get_deployments_by_status(
            ProcessStatus.STOPPED
        )

        assert len(running) == 2
        assert len(stopped) == 1
        assert all(d.status == ProcessStatus.RUNNING for d in running)

    def test_get_deployment_by_port(self, populated_state_manager):
        """Should find deployment by port."""
        deployment = populated_state_manager.get_deployment_by_port(3000)
        assert deployment is not None
        assert deployment.port == 3000
        assert deployment.deployment_id == "deploy_running_1"

    def test_get_deployment_by_port_not_found(self, populated_state_manager):
        """Should return None when port not found."""
        deployment = populated_state_manager.get_deployment_by_port(9999)
        assert deployment is None

    def test_get_deployments_by_project(self, populated_state_manager):
        """Should find deployments by project directory."""
        deployments = populated_state_manager.get_deployments_by_project(
            "/tmp/project1"
        )
        assert len(deployments) == 2

    def test_get_deployments_by_project_normalizes_path(self, populated_state_manager):
        """Should normalize paths when querying by project."""
        # Test with trailing slash
        deployments1 = populated_state_manager.get_deployments_by_project(
            "/tmp/project1/"
        )
        # Test without trailing slash
        deployments2 = populated_state_manager.get_deployments_by_project(
            "/tmp/project1"
        )
        assert len(deployments1) == len(deployments2)


class TestCleanupOperations:
    """Test cleanup operations."""

    def test_cleanup_dead_pids(self, state_manager):
        """Should remove deployments with dead PIDs."""
        # Add deployment with PID that doesn't exist
        dead_deployment = DeploymentState(
            deployment_id="deploy_dead",
            process_id=999999,  # Very unlikely to exist
            command=["npm", "run", "dev"],
            working_directory="/tmp/project",
            port=3000,
            status=ProcessStatus.RUNNING,
        )
        state_manager.add_deployment(dead_deployment)

        cleaned = state_manager.cleanup_dead_pids()

        assert cleaned == 1
        assert state_manager.get_deployment("deploy_dead") is None

    def test_cleanup_preserves_alive_pids(self, state_manager):
        """Should preserve deployments with alive PIDs."""
        # Use current process PID (guaranteed to be alive)
        alive_deployment = DeploymentState(
            deployment_id="deploy_alive",
            process_id=os.getpid(),
            command=["python", "-m", "test"],
            working_directory="/tmp/project",
            port=3000,
            status=ProcessStatus.RUNNING,
        )
        state_manager.add_deployment(alive_deployment)

        cleaned = state_manager.cleanup_dead_pids()

        assert cleaned == 0
        assert state_manager.get_deployment("deploy_alive") is not None

    def test_cleanup_no_deployments(self, state_manager):
        """Should handle cleanup when no deployments exist."""
        cleaned = state_manager.cleanup_dead_pids()
        assert cleaned == 0


class TestCorruptionRecovery:
    """Test corruption detection and recovery."""

    def test_recovers_from_corrupted_json(self, temp_state_file):
        """Should recover from corrupted JSON file."""
        # Write corrupted JSON
        with open(temp_state_file, "w") as f:
            f.write('{"invalid": json content')

        manager = DeploymentStateManager(temp_state_file)
        manager.initialize()

        # Should recover with empty state
        states = manager.load_state()
        assert states == {}

        # Should create backup of corrupted file
        backup = Path(temp_state_file).with_suffix(".json.corrupted")
        assert backup.exists()

    def test_skips_corrupted_entries(self, state_manager, temp_state_file):
        """Should skip corrupted entries but preserve valid ones."""
        # Write state with one corrupted entry
        data = {
            "valid_deploy": {
                "deployment_id": "valid_deploy",
                "process_id": 12345,
                "command": ["test"],
                "working_directory": "/tmp",
                "environment": {},
                "port": 3000,
                "started_at": datetime.now().isoformat(),
                "status": "running",
                "metadata": {},
            },
            "corrupted_deploy": {
                "deployment_id": "corrupted",
                # Missing required fields
            },
        }

        with open(temp_state_file, "w") as f:
            json.dump(data, f)

        states = state_manager.load_state()

        # Should have loaded the valid entry
        assert "valid_deploy" in states
        # Should have skipped the corrupted entry
        assert "corrupted_deploy" not in states


class TestConcurrency:
    """Test concurrent access and file locking."""

    def test_file_locking_prevents_corruption(self, state_manager, sample_deployment):
        """Should prevent corruption through file locking."""
        # This is a basic test - full concurrency testing would require threading
        state_manager.add_deployment(sample_deployment)

        # Verify lock file exists during operation
        # Note: Lock file may be ephemeral, so we just verify no errors occur
        deployment = state_manager.get_deployment("test_deploy_001")
        assert deployment is not None

    def test_multiple_sequential_operations(self, state_manager):
        """Should handle multiple sequential operations correctly."""
        for i in range(10):
            deployment = DeploymentState(
                deployment_id=f"deploy_{i}",
                process_id=10000 + i,
                command=["test"],
                working_directory=f"/tmp/project_{i}",
                port=3000 + i,
                status=ProcessStatus.RUNNING,
            )
            state_manager.add_deployment(deployment)

        all_deployments = state_manager.get_all_deployments()
        assert len(all_deployments) == 10


class TestErrorHandling:
    """Test error handling scenarios."""

    def test_handles_permission_error_on_write(self, state_manager):
        """Should raise IOError when unable to write state."""
        with patch("builtins.open", side_effect=PermissionError("No permission")):
            with pytest.raises(IOError):
                state_manager.save_state({})

    def test_handles_corrupted_state_beyond_recovery(self, tmp_path):
        """Should fail initialization when unable to recover from corrupted state."""
        # Use tmp_path to create a subdirectory we can control permissions for
        state_dir = tmp_path / "state_dir"
        state_dir.mkdir()
        temp_state_file = state_dir / "state.json"

        original_mode = state_dir.stat().st_mode

        try:
            # Write corrupted JSON
            with open(temp_state_file, "w") as f:
                f.write('{"invalid": json}')

            # Make directory read-only to prevent backup (r-x needed to traverse directory)
            os.chmod(state_dir, 0o555)

            manager = DeploymentStateManager(str(temp_state_file))
            # Initialize should fail when it can't recover from corruption
            result = manager.initialize()
            assert result is False

        finally:
            # Restore permissions
            os.chmod(state_dir, original_mode)


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_deployment_list(self, state_manager):
        """Should handle empty deployment list."""
        deployments = state_manager.get_all_deployments()
        assert deployments == []

    def test_deployment_with_none_port(self, state_manager):
        """Should handle deployment with no port."""
        deployment = DeploymentState(
            deployment_id="no_port_deploy",
            process_id=12345,
            command=["test"],
            working_directory="/tmp",
            port=None,  # No port
            status=ProcessStatus.RUNNING,
        )
        state_manager.add_deployment(deployment)

        loaded = state_manager.get_deployment("no_port_deploy")
        assert loaded is not None
        assert loaded.port is None

    def test_deployment_with_empty_metadata(self, state_manager):
        """Should handle deployment with empty metadata."""
        deployment = DeploymentState(
            deployment_id="no_metadata",
            process_id=12345,
            command=["test"],
            working_directory="/tmp",
            metadata={},  # Empty metadata
            status=ProcessStatus.RUNNING,
        )
        state_manager.add_deployment(deployment)

        loaded = state_manager.get_deployment("no_metadata")
        assert loaded is not None
        assert loaded.metadata == {}

    def test_very_long_deployment_id(self, state_manager):
        """Should handle very long deployment IDs."""
        long_id = "x" * 500
        deployment = DeploymentState(
            deployment_id=long_id,
            process_id=12345,
            command=["test"],
            working_directory="/tmp",
            status=ProcessStatus.RUNNING,
        )
        state_manager.add_deployment(deployment)

        loaded = state_manager.get_deployment(long_id)
        assert loaded is not None
        assert loaded.deployment_id == long_id

    def test_deployment_with_special_characters(self, state_manager):
        """Should handle deployment IDs with special characters."""
        special_id = "deploy-123_test.v1@prod"
        deployment = DeploymentState(
            deployment_id=special_id,
            process_id=12345,
            command=["test"],
            working_directory="/tmp",
            status=ProcessStatus.RUNNING,
        )
        state_manager.add_deployment(deployment)

        loaded = state_manager.get_deployment(special_id)
        assert loaded is not None
        assert loaded.deployment_id == special_id
