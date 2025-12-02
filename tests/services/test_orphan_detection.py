#!/usr/bin/env python3
"""
Unit Tests for OrphanDetectionService
=====================================

Tests the orphan process detection and cleanup system.
"""

import json
import subprocess
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import psutil

from claude_mpm.services.orphan_detection import (OrphanDetectionService,
                                                  OrphanInfo, OrphanSeverity,
                                                  OrphanType)


class TestOrphanInfo(unittest.TestCase):
    """Test cases for OrphanInfo class."""

    def test_orphan_info_creation(self):
        """Test creating OrphanInfo instance."""
        orphan = OrphanInfo(
            orphan_type=OrphanType.DEAD_PID,
            severity=OrphanSeverity.LOW,
            description="Test orphan",
            details={"pid": 12345},
            cleanup_action="Remove from state",
        )

        self.assertEqual(orphan.orphan_type, OrphanType.DEAD_PID)
        self.assertEqual(orphan.severity, OrphanSeverity.LOW)
        self.assertEqual(orphan.description, "Test orphan")
        self.assertEqual(orphan.details["pid"], 12345)
        self.assertEqual(orphan.cleanup_action, "Remove from state")
        self.assertIsNotNone(orphan.detected_at)

    def test_orphan_info_to_dict(self):
        """Test converting OrphanInfo to dictionary."""
        orphan = OrphanInfo(
            orphan_type=OrphanType.PM2_ORPHAN,
            severity=OrphanSeverity.HIGH,
            description="PM2 process",
            details={"pm2_name": "test-app"},
        )

        data = orphan.to_dict()

        self.assertEqual(data["type"], "pm2_orphan")
        self.assertEqual(data["severity"], "high")
        self.assertEqual(data["description"], "PM2 process")
        self.assertEqual(data["details"]["pm2_name"], "test-app")
        self.assertIn("detected_at", data)


class TestOrphanDetectionService(unittest.TestCase):
    """Test cases for OrphanDetectionService."""

    def setUp(self):
        """Set up test environment."""
        # Create temporary directory
        self.temp_dir = tempfile.mkdtemp()
        self.project_root = Path(self.temp_dir) / "test_project"
        self.project_root.mkdir(parents=True)

        # Create service
        self.service = OrphanDetectionService(project_root=self.project_root)
        self.service.initialize()

        # Create state directory
        self.state_dir = self.project_root / ".claude-mpm"
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = self.state_dir / "deployment-state.json"

    def tearDown(self):
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_initialization(self):
        """Test service initialization."""
        self.assertTrue(self.service.is_initialized)
        self.assertFalse(self.service.is_shutdown)

    def test_is_protected_process(self):
        """Test protected process detection."""
        # Protected patterns
        self.assertTrue(self.service._is_protected_process("python claude-mpm monitor"))
        self.assertTrue(self.service._is_protected_process("socketio_daemon.py"))
        self.assertTrue(self.service._is_protected_process("mcp-server start"))
        self.assertTrue(
            self.service._is_protected_process("/path/to/claude_mpm/service")
        )

        # Non-protected patterns
        self.assertFalse(self.service._is_protected_process("npm run dev"))
        self.assertFalse(self.service._is_protected_process("python app.py"))

    def test_is_protected_port(self):
        """Test protected port detection."""
        # Claude MPM ports
        self.assertTrue(self.service._is_protected_port(8765))
        self.assertTrue(self.service._is_protected_port(8775))
        self.assertTrue(self.service._is_protected_port(8785))

        # User ports
        self.assertFalse(self.service._is_protected_port(3000))
        self.assertFalse(self.service._is_protected_port(8000))

    @patch("psutil.Process")
    def test_get_process_age(self, mock_process_class):
        """Test getting process age."""
        # Mock process
        mock_process = MagicMock()
        mock_process.create_time.return_value = time.time() - 120  # 2 minutes old
        mock_process_class.return_value = mock_process

        age = self.service._get_process_age(12345)

        self.assertIsNotNone(age)
        self.assertGreater(age, 100)  # At least 100 seconds
        self.assertLess(age, 150)  # Less than 150 seconds

    @patch("psutil.Process")
    def test_get_process_age_no_access(self, mock_process_class):
        """Test getting process age when access denied."""
        mock_process_class.side_effect = psutil.AccessDenied()

        age = self.service._get_process_age(12345)
        self.assertIsNone(age)

    @patch("psutil.Process")
    def test_is_process_safe_to_kill_protected(self, mock_process_class):
        """Test safety check rejects protected processes."""
        mock_process = MagicMock()
        mock_process.create_time.return_value = time.time() - 120
        mock_process_class.return_value = mock_process

        is_safe, reason = self.service._is_process_safe_to_kill(
            12345, "python claude-mpm monitor"
        )

        self.assertFalse(is_safe)
        self.assertIn("Protected", reason)

    @patch("psutil.Process")
    def test_is_process_safe_to_kill_too_young(self, mock_process_class):
        """Test safety check rejects young processes."""
        mock_process = MagicMock()
        mock_process.create_time.return_value = time.time() - 30  # Only 30 seconds
        mock_process_class.return_value = mock_process

        is_safe, reason = self.service._is_process_safe_to_kill(12345, "npm run dev")

        self.assertFalse(is_safe)
        self.assertIn("too young", reason)

    @patch("psutil.Process")
    def test_is_process_safe_to_kill_safe(self, mock_process_class):
        """Test safety check allows safe processes."""
        mock_process = MagicMock()
        mock_process.create_time.return_value = time.time() - 120  # 2 minutes
        mock_process_class.return_value = mock_process

        is_safe, reason = self.service._is_process_safe_to_kill(12345, "npm run dev")

        self.assertTrue(is_safe)
        self.assertIn("Safe", reason)

    @patch("psutil.pid_exists")
    def test_scan_dead_pids(self, mock_pid_exists):
        """Test scanning for dead PIDs in state file."""
        # Create state file with dead PID
        state = {
            "deployments": {
                "main": {
                    "pid": 12345,
                    "port": 3000,
                },
                "api": {
                    "pid": 12346,
                    "port": 3001,
                },
            }
        }

        with self.state_file.open("w") as f:
            json.dump(state, f)

        # Mock that first PID is dead, second is alive
        def pid_exists_side_effect(pid):
            return pid == 12346

        mock_pid_exists.side_effect = pid_exists_side_effect

        # Scan for dead PIDs
        orphans = self.service.scan_dead_pids()

        # Should find one dead PID
        self.assertEqual(len(orphans), 1)
        self.assertEqual(orphans[0].orphan_type, OrphanType.DEAD_PID)
        self.assertEqual(orphans[0].severity, OrphanSeverity.LOW)
        self.assertEqual(orphans[0].details["pid"], 12345)

    def test_scan_dead_pids_no_state_file(self):
        """Test scanning when state file doesn't exist."""
        orphans = self.service.scan_dead_pids()
        self.assertEqual(len(orphans), 0)

    def test_scan_deleted_projects(self):
        """Test scanning for deleted projects."""
        # Create global registry
        deleted_project = Path(self.temp_dir) / "deleted_project"

        registry = {
            "allocations": {
                "3000": {
                    "project_path": str(deleted_project),
                    "service_name": "main",
                },
                "3001": {
                    "project_path": str(self.project_root),  # Exists
                    "service_name": "main",
                },
            }
        }

        global_registry_file = self.service.global_registry_file
        global_registry_file.parent.mkdir(parents=True, exist_ok=True)

        with global_registry_file.open("w") as f:
            json.dump(registry, f)

        # Scan for deleted projects
        orphans = self.service.scan_deleted_projects()

        # Should find one deleted project
        self.assertEqual(len(orphans), 1)
        self.assertEqual(orphans[0].orphan_type, OrphanType.DELETED_PROJECT)
        self.assertEqual(orphans[0].severity, OrphanSeverity.MEDIUM)
        self.assertEqual(orphans[0].details["port"], 3000)

    @patch("psutil.net_connections")
    @patch("psutil.Process")
    def test_scan_untracked_processes(self, mock_process_class, mock_net_connections):
        """Test scanning for untracked processes."""
        # Mock network connection
        mock_conn = MagicMock()
        mock_conn.status = "LISTEN"
        mock_conn.laddr.port = 3000
        mock_conn.pid = 12345

        mock_net_connections.return_value = [mock_conn]

        # Mock process
        mock_process = MagicMock()
        mock_process.name.return_value = "node"
        mock_process.cmdline.return_value = ["node", "server.js"]
        mock_process_class.return_value = mock_process

        # Create empty global registry (port 3000 not tracked)
        global_registry_file = self.service.global_registry_file
        global_registry_file.parent.mkdir(parents=True, exist_ok=True)

        with global_registry_file.open("w") as f:
            json.dump({"allocations": {}}, f)

        # Scan for untracked processes
        orphans = self.service.scan_untracked_processes()

        # Should find one untracked process
        self.assertEqual(len(orphans), 1)
        self.assertEqual(orphans[0].orphan_type, OrphanType.UNTRACKED_PROCESS)
        self.assertEqual(orphans[0].severity, OrphanSeverity.MEDIUM)
        self.assertEqual(orphans[0].details["port"], 3000)

    @patch("subprocess.run")
    def test_scan_pm2_orphans(self, mock_run):
        """Test scanning for orphaned PM2 processes."""
        # Mock PM2 output
        pm2_output = [
            {"name": "tracked-app", "pid": 12345, "pm2_env": {"status": "online"}},
            {
                "name": "orphan-app",
                "pid": 12346,
                "pm2_env": {"status": "online", "restart_time": 2},
            },
        ]

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps(pm2_output)
        mock_run.return_value = mock_result

        # Create state file tracking only first app
        state = {
            "deployments": {
                "main": {
                    "method": "pm2",
                    "process_name": "tracked-app",
                }
            }
        }

        with self.state_file.open("w") as f:
            json.dump(state, f)

        # Scan for PM2 orphans
        orphans = self.service.scan_pm2_orphans()

        # Should find one orphan
        self.assertEqual(len(orphans), 1)
        self.assertEqual(orphans[0].orphan_type, OrphanType.PM2_ORPHAN)
        self.assertEqual(orphans[0].severity, OrphanSeverity.HIGH)
        self.assertEqual(orphans[0].details["pm2_name"], "orphan-app")

    @patch("subprocess.run")
    def test_scan_pm2_orphans_no_pm2(self, mock_run):
        """Test scanning when PM2 is not available."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_run.return_value = mock_result

        orphans = self.service.scan_pm2_orphans()
        self.assertEqual(len(orphans), 0)

    @patch("subprocess.run")
    def test_scan_docker_orphans(self, mock_run):
        """Test scanning for orphaned Docker containers."""
        # Mock Docker output
        docker_output = [
            '{"ID": "abc123", "Names": "tracked-container", "Image": "node:latest", "Status": "Up"}',
            '{"ID": "def456", "Names": "orphan-container", "Image": "node:latest", "Status": "Up"}',
        ]

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "\n".join(docker_output) + "\n"
        mock_run.return_value = mock_result

        # Create state file tracking only first container
        state = {
            "deployments": {
                "main": {
                    "method": "docker",
                    "container_id": "abc123",
                }
            }
        }

        with self.state_file.open("w") as f:
            json.dump(state, f)

        # Scan for Docker orphans
        orphans = self.service.scan_docker_orphans()

        # Should find one orphan
        self.assertEqual(len(orphans), 1)
        self.assertEqual(orphans[0].orphan_type, OrphanType.DOCKER_ORPHAN)
        self.assertEqual(orphans[0].severity, OrphanSeverity.HIGH)
        self.assertEqual(orphans[0].details["container_id"], "def456")

    @patch("subprocess.run")
    def test_scan_docker_orphans_no_docker(self, mock_run):
        """Test scanning when Docker is not available."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_run.return_value = mock_result

        orphans = self.service.scan_docker_orphans()
        self.assertEqual(len(orphans), 0)

    @patch("psutil.pid_exists")
    @patch("psutil.net_connections")
    @patch("subprocess.run")
    def test_scan_all_orphans(self, mock_run, mock_net_connections, mock_pid_exists):
        """Test comprehensive orphan scan."""
        # Mock dead PID
        mock_pid_exists.return_value = False

        # Create state file with dead PID
        state = {"deployments": {"main": {"pid": 12345, "port": 3000}}}
        with self.state_file.open("w") as f:
            json.dump(state, f)

        # Mock PM2 not available
        mock_run.return_value = MagicMock(returncode=1)

        # Mock no network connections
        mock_net_connections.return_value = []

        # Scan all orphans
        results = self.service.scan_all_orphans()

        # Should have results for all scan types
        self.assertIn("dead_pids", results)
        self.assertIn("deleted_projects", results)
        self.assertIn("untracked_processes", results)
        self.assertIn("pm2_orphans", results)
        self.assertIn("docker_orphans", results)

        # Should have found at least the dead PID
        self.assertGreater(len(results["dead_pids"]), 0)

    def test_cleanup_dead_pid(self):
        """Test cleaning up dead PID entry."""
        # Create state file
        state = {"deployments": {"main": {"pid": 12345, "port": 3000}}}
        with self.state_file.open("w") as f:
            json.dump(state, f)

        # Create orphan
        orphan = OrphanInfo(
            orphan_type=OrphanType.DEAD_PID,
            severity=OrphanSeverity.LOW,
            description="Dead PID",
            details={"service_name": "main", "pid": 12345},
        )

        # Cleanup
        success, message = self.service.cleanup_orphan(orphan)

        self.assertTrue(success)
        self.assertIn("Removed", message)

        # Verify removal
        with self.state_file.open() as f:
            updated_state = json.load(f)

        self.assertNotIn("main", updated_state.get("deployments", {}))

    def test_cleanup_deleted_project(self):
        """Test cleaning up deleted project entry."""
        # Create global registry
        registry = {
            "allocations": {
                "3000": {
                    "project_path": "/nonexistent",
                    "service_name": "main",
                }
            }
        }

        global_registry_file = self.service.global_registry_file
        global_registry_file.parent.mkdir(parents=True, exist_ok=True)

        with global_registry_file.open("w") as f:
            json.dump(registry, f)

        # Create orphan
        orphan = OrphanInfo(
            orphan_type=OrphanType.DELETED_PROJECT,
            severity=OrphanSeverity.MEDIUM,
            description="Deleted project",
            details={"port": 3000},
        )

        # Cleanup
        success, message = self.service.cleanup_orphan(orphan)

        self.assertTrue(success)
        self.assertIn("Removed", message)

        # Verify removal
        with global_registry_file.open() as f:
            updated_registry = json.load(f)

        self.assertNotIn("3000", updated_registry.get("allocations", {}))

    def test_cleanup_high_severity_requires_force(self):
        """Test high severity cleanup requires force flag."""
        orphan = OrphanInfo(
            orphan_type=OrphanType.PM2_ORPHAN,
            severity=OrphanSeverity.HIGH,
            description="PM2 orphan",
            details={"pm2_name": "test-app"},
        )

        # Try cleanup without force
        success, message = self.service.cleanup_orphan(orphan, force=False)

        self.assertFalse(success)
        self.assertIn("force=True", message)

    @patch("subprocess.run")
    def test_cleanup_pm2_orphan(self, mock_run):
        """Test cleaning up PM2 orphan."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        orphan = OrphanInfo(
            orphan_type=OrphanType.PM2_ORPHAN,
            severity=OrphanSeverity.HIGH,
            description="PM2 orphan",
            details={"pm2_name": "test-app"},
        )

        # Cleanup with force
        success, message = self.service.cleanup_orphan(orphan, force=True)

        self.assertTrue(success)
        self.assertIn("Deleted", message)
        mock_run.assert_called_once()

    @patch("subprocess.run")
    def test_cleanup_docker_orphan(self, mock_run):
        """Test cleaning up Docker orphan."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        orphan = OrphanInfo(
            orphan_type=OrphanType.DOCKER_ORPHAN,
            severity=OrphanSeverity.HIGH,
            description="Docker orphan",
            details={"container_id": "abc123"},
        )

        # Cleanup with force
        success, message = self.service.cleanup_orphan(orphan, force=True)

        self.assertTrue(success)
        self.assertIn("Stopped", message)
        mock_run.assert_called_once()

    def test_shutdown(self):
        """Test service shutdown."""
        self.service.shutdown()
        self.assertTrue(self.service.is_shutdown)


class TestOrphanDetectionIntegration(unittest.TestCase):
    """Integration tests for OrphanDetectionService."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.project_root = Path(self.temp_dir) / "test_project"
        self.project_root.mkdir(parents=True)

        self.service = OrphanDetectionService(project_root=self.project_root)
        self.service.initialize()

        self.state_file = self.project_root / ".claude-mpm" / "deployment-state.json"
        self.state_file.parent.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("psutil.pid_exists")
    def test_full_cleanup_lifecycle(self, mock_pid_exists):
        """Test complete orphan detection and cleanup lifecycle."""
        # Create state with dead PID
        state = {
            "deployments": {
                "main": {
                    "pid": 99999,  # Unlikely to exist
                    "port": 3000,
                    "framework": "nextjs",
                }
            }
        }

        with self.state_file.open("w") as f:
            json.dump(state, f)

        # Mock PID as dead
        mock_pid_exists.return_value = False

        # 1. Scan for orphans
        orphans = self.service.scan_dead_pids()
        self.assertEqual(len(orphans), 1)

        # 2. Cleanup orphan
        success, _message = self.service.cleanup_orphan(orphans[0])
        self.assertTrue(success)

        # 3. Verify cleanup
        orphans_after = self.service.scan_dead_pids()
        self.assertEqual(len(orphans_after), 0)


if __name__ == "__main__":
    unittest.main()
