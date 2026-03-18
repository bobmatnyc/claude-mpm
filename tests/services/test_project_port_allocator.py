#!/usr/bin/env python3
"""
Unit Tests for ProjectPortAllocator Service
===========================================

Tests the deterministic hash-based port allocation system.
"""

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from claude_mpm.services.project_port_allocator import ProjectPortAllocator


class TestProjectPortAllocator(unittest.TestCase):
    """Test cases for ProjectPortAllocator service."""

    def setUp(self):
        """Set up test environment."""
        # Create temporary directories for testing
        self.temp_dir = tempfile.mkdtemp()
        self.project_root = Path(self.temp_dir) / "test_project"
        self.project_root.mkdir(parents=True)

        # Create another project for cross-project tests
        self.other_project = Path(self.temp_dir) / "other_project"
        self.other_project.mkdir(parents=True)

        # Create allocator
        self.allocator = ProjectPortAllocator(project_root=self.project_root)
        self.allocator.initialize()

    def tearDown(self):
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_initialization(self):
        """Test service initialization."""
        self.assertTrue(self.allocator.is_initialized)
        self.assertFalse(self.allocator.is_shutdown)
        self.assertTrue(self.allocator.state_dir.exists())
        self.assertTrue(self.allocator.global_registry_dir.exists())

    def test_compute_project_hash(self):
        """Test project hash computation is deterministic."""
        hash1 = self.allocator._compute_project_hash(self.project_root)
        hash2 = self.allocator._compute_project_hash(self.project_root)

        # Same path should produce same hash
        self.assertEqual(hash1, hash2)
        self.assertEqual(len(hash1), 64)  # SHA-256 produces 64 hex chars

    def test_different_projects_different_hashes(self):
        """Test different projects get different hashes."""
        hash1 = self.allocator._compute_project_hash(self.project_root)
        hash2 = self.allocator._compute_project_hash(self.other_project)

        self.assertNotEqual(hash1, hash2)

    def test_hash_to_port(self):
        """Test hash to port conversion."""
        test_hash = "a" * 64  # All 'a's
        port = self.allocator._hash_to_port(test_hash)

        # Port should be in valid range
        self.assertGreaterEqual(port, self.allocator.port_range_start)
        self.assertLessEqual(port, self.allocator.port_range_end)

    def test_hash_to_port_consistency(self):
        """Test same hash always produces same port."""
        test_hash = "abc123" * 10 + "abcd"  # 64 chars
        port1 = self.allocator._hash_to_port(test_hash)
        port2 = self.allocator._hash_to_port(test_hash)

        self.assertEqual(port1, port2)

    @patch("socket.socket")
    def test_is_port_available_true(self, mock_socket):
        """Test port availability check when port is free."""
        # Mock socket that successfully binds
        mock_sock = MagicMock()
        mock_socket.return_value.__enter__ = MagicMock(return_value=mock_sock)
        mock_socket.return_value.__exit__ = MagicMock()

        result = self.allocator._is_port_available(3000)
        self.assertTrue(result)
        mock_sock.bind.assert_called_once()

    @patch("socket.socket")
    def test_is_port_available_false(self, mock_socket):
        """Test port availability check when port is in use."""
        # Mock socket that fails to bind
        mock_sock = MagicMock()
        mock_sock.bind.side_effect = OSError("Address already in use")
        mock_socket.return_value.__enter__ = MagicMock(return_value=mock_sock)
        mock_socket.return_value.__exit__ = MagicMock()

        result = self.allocator._is_port_available(3000)
        self.assertFalse(result)

    def test_is_protected_port(self):
        """Test protected port detection."""
        # Claude MPM ports should be protected
        self.assertTrue(self.allocator._is_protected_port(8765))
        self.assertTrue(self.allocator._is_protected_port(8775))
        self.assertTrue(self.allocator._is_protected_port(8785))

        # User ports should not be protected
        self.assertFalse(self.allocator._is_protected_port(3000))
        self.assertFalse(self.allocator._is_protected_port(5000))

    def test_save_and_load_project_state(self):
        """Test project state persistence."""
        test_state = {
            "project_path": str(self.project_root),
            "project_hash": "abc123",
            "deployments": {
                "main": {
                    "port": 3000,
                    "pid": 12345,
                }
            },
            "port_history": [3000],
        }

        # Save state
        self.allocator._save_project_state(test_state)

        # Load state
        loaded_state = self.allocator._load_project_state()

        self.assertEqual(loaded_state["project_path"], test_state["project_path"])
        self.assertEqual(loaded_state["project_hash"], test_state["project_hash"])
        self.assertEqual(loaded_state["deployments"]["main"]["port"], 3000)

    def test_save_and_load_global_registry(self):
        """Test global registry persistence."""
        test_registry = {
            "allocations": {
                "3000": {
                    "project_path": str(self.project_root),
                    "service_name": "main",
                }
            }
        }

        # Save registry
        self.allocator._save_global_registry(test_registry)

        # Load registry
        loaded_registry = self.allocator._load_global_registry()

        self.assertIn("3000", loaded_registry["allocations"])
        self.assertEqual(
            loaded_registry["allocations"]["3000"]["project_path"],
            str(self.project_root),
        )

    @patch.dict(os.environ, {"PROJECT_PORT": "3500"})
    def test_get_project_port_with_env_override(self):
        """Test environment variable override for port allocation."""
        port = self.allocator.get_project_port()
        self.assertEqual(port, 3500)

    @patch.dict(os.environ, {"PROJECT_PORT": "invalid"})
    @patch("socket.socket")
    def test_get_project_port_with_invalid_env(self, mock_socket):
        """Test invalid environment variable is ignored."""
        # Mock port availability
        mock_sock = MagicMock()
        mock_socket.return_value.__enter__ = MagicMock(return_value=mock_sock)
        mock_socket.return_value.__exit__ = MagicMock()

        port = self.allocator.get_project_port()
        # Should fall back to hash-based allocation
        self.assertIsInstance(port, int)
        self.assertGreaterEqual(port, self.allocator.port_range_start)

    @patch("socket.socket")
    def test_register_port(self, mock_socket):
        """Test port registration."""
        # Mock socket for availability check
        mock_sock = MagicMock()
        mock_socket.return_value.__enter__ = MagicMock(return_value=mock_sock)
        mock_socket.return_value.__exit__ = MagicMock()

        deployment_info = {
            "pid": 12345,
            "framework": "nextjs",
            "method": "pm2",
        }

        self.allocator.register_port(3000, "main", deployment_info)

        # Check project state
        state = self.allocator._load_project_state()
        self.assertIn("main", state["deployments"])
        self.assertEqual(state["deployments"]["main"]["port"], 3000)
        self.assertEqual(state["deployments"]["main"]["pid"], 12345)
        self.assertIn(3000, state["port_history"])

        # Check global registry
        registry = self.allocator._load_global_registry()
        self.assertIn("3000", registry["allocations"])

    def test_release_port(self):
        """Test port release."""
        # First register a port
        self.allocator.register_port(3000, "main", {"pid": 12345})

        # Then release it
        self.allocator.release_port(3000, "main")

        # Check project state
        state = self.allocator._load_project_state()
        self.assertNotIn("main", state.get("deployments", {}))

        # Check global registry
        registry = self.allocator._load_global_registry()
        self.assertNotIn("3000", registry.get("allocations", {}))

    @patch("psutil.pid_exists")
    def test_cleanup_dead_registrations(self, mock_pid_exists):
        """Test cleanup of dead process registrations."""
        # Register a port with a PID
        self.allocator.register_port(3000, "main", {"pid": 12345})

        # Mock that PID is dead
        mock_pid_exists.return_value = False

        # Cleanup
        cleaned = self.allocator.cleanup_dead_registrations()

        # Should have cleaned up two registrations (project state + global registry)
        self.assertEqual(cleaned, 2)

        # Check that deployment was removed
        state = self.allocator._load_project_state()
        self.assertNotIn("main", state.get("deployments", {}))

    @patch("psutil.pid_exists")
    def test_cleanup_preserves_alive_registrations(self, mock_pid_exists):
        """Test cleanup preserves alive process registrations."""
        # Register a port with a PID
        self.allocator.register_port(3000, "main", {"pid": 12345})

        # Mock that PID is alive
        mock_pid_exists.return_value = True

        # Cleanup
        cleaned = self.allocator.cleanup_dead_registrations()

        # Should not have cleaned anything
        self.assertEqual(cleaned, 0)

        # Check that deployment still exists
        state = self.allocator._load_project_state()
        self.assertIn("main", state.get("deployments", {}))

    def test_get_allocation_info(self):
        """Test getting allocation information."""
        # Register a port
        deployment_info = {
            "pid": 12345,
            "framework": "nextjs",
        }
        self.allocator.register_port(3000, "main", deployment_info)

        # Get allocation info
        info = self.allocator.get_allocation_info("main")

        self.assertIsNotNone(info)
        self.assertEqual(info["port"], 3000)
        self.assertEqual(info["pid"], 12345)
        self.assertEqual(info["framework"], "nextjs")

    def test_get_allocation_info_nonexistent(self):
        """Test getting info for nonexistent allocation."""
        info = self.allocator.get_allocation_info("nonexistent")
        self.assertIsNone(info)

    def test_list_project_allocations(self):
        """Test listing all project allocations."""
        # Register multiple ports
        self.allocator.register_port(3000, "main", {"pid": 12345})
        self.allocator.register_port(3001, "api", {"pid": 12346})

        # List allocations
        allocations = self.allocator.list_project_allocations()

        # Use resolve() to handle /private prefix on macOS
        self.assertEqual(
            Path(allocations["project_path"]).resolve(), self.project_root.resolve()
        )
        self.assertIn("main", allocations["deployments"])
        self.assertIn("api", allocations["deployments"])
        self.assertIn(3000, allocations["port_history"])
        self.assertIn(3001, allocations["port_history"])

    def test_list_global_allocations(self):
        """Test listing global allocations."""
        # Register ports in different projects
        allocator1 = ProjectPortAllocator(project_root=self.project_root)
        allocator1.initialize()
        allocator1.register_port(3000, "main", {"pid": 12345})

        allocator2 = ProjectPortAllocator(project_root=self.other_project)
        allocator2.initialize()
        allocator2.register_port(3001, "main", {"pid": 12346})

        # List global allocations
        global_allocs = allocator1.list_global_allocations()

        self.assertIn("3000", global_allocs["allocations"])
        self.assertIn("3001", global_allocs["allocations"])

    @patch("socket.socket")
    def test_find_available_port_linear_probing(self, mock_socket):
        """Test linear probing when base port is unavailable."""
        # Mock socket to make first port unavailable, second available
        mock_sock = MagicMock()
        call_count = [0]

        def bind_side_effect(addr):
            call_count[0] += 1
            if call_count[0] == 1:
                raise OSError("Port in use")
            # Subsequent calls succeed

        mock_sock.bind = MagicMock(side_effect=bind_side_effect)
        mock_socket.return_value.__enter__ = MagicMock(return_value=mock_sock)
        mock_socket.return_value.__exit__ = MagicMock()

        # Should find next available port
        port = self.allocator._find_available_port(3000, self.project_root, "main")

        # Should have found port 3001 (next after 3000)
        self.assertEqual(port, 3001)

    @patch("socket.socket")
    def test_find_available_port_wraps_around(self, mock_socket):
        """Test port allocation wraps around at range end."""
        # Mock socket to make ports available
        mock_sock = MagicMock()
        mock_socket.return_value.__enter__ = MagicMock(return_value=mock_sock)
        mock_socket.return_value.__exit__ = MagicMock()

        # Try to allocate from near the end of range
        start_port = self.allocator.port_range_end
        port = self.allocator._find_available_port(
            start_port, self.project_root, "main"
        )

        # Should wrap to beginning of range
        self.assertGreaterEqual(port, self.allocator.port_range_start)
        self.assertLessEqual(port, self.allocator.port_range_end)

    def test_shutdown(self):
        """Test service shutdown."""
        self.allocator.shutdown()
        self.assertTrue(self.allocator.is_shutdown)


class TestProjectPortAllocatorIntegration(unittest.TestCase):
    """Integration tests for ProjectPortAllocator."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.project_root = Path(self.temp_dir) / "test_project"
        self.project_root.mkdir(parents=True)

        self.allocator = ProjectPortAllocator(project_root=self.project_root)
        self.allocator.initialize()

    def tearDown(self):
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("socket.socket")
    def test_full_allocation_lifecycle(self, mock_socket):
        """Test complete allocation lifecycle."""
        # Mock port availability
        mock_sock = MagicMock()
        mock_socket.return_value.__enter__ = MagicMock(return_value=mock_sock)
        mock_socket.return_value.__exit__ = MagicMock()

        # 1. Allocate port
        port = self.allocator.get_project_port(service_name="main")
        self.assertIsInstance(port, int)

        # 2. Register port
        self.allocator.register_port(
            port,
            "main",
            {
                "pid": 12345,
                "framework": "nextjs",
                "method": "pm2",
            },
        )

        # 3. Verify allocation
        info = self.allocator.get_allocation_info("main")
        self.assertEqual(info["port"], port)

        # 4. Get same port on subsequent call
        port2 = self.allocator.get_project_port(service_name="main")
        self.assertEqual(port, port2)

        # 5. Release port
        self.allocator.release_port(port, "main")

        # 6. Verify release
        info = self.allocator.get_allocation_info("main")
        self.assertIsNone(info)

    @patch("socket.socket")
    def test_multiple_services_same_project(self, mock_socket):
        """Test multiple services in same project.

        Note: Services in the same project get the same base port from hash,
        but can be registered with different ports if needed.
        """
        # Mock port availability
        mock_sock = MagicMock()
        mock_socket.return_value.__enter__ = MagicMock(return_value=mock_sock)
        mock_socket.return_value.__exit__ = MagicMock()

        # Allocate ports for different services
        # All will get same base port since they're from same project
        port_main = self.allocator.get_project_port(service_name="main")
        port_api = self.allocator.get_project_port(service_name="api")
        port_admin = self.allocator.get_project_port(service_name="admin")

        # All should be valid ports
        self.assertGreaterEqual(port_main, self.allocator.port_range_start)
        self.assertGreaterEqual(port_api, self.allocator.port_range_start)
        self.assertGreaterEqual(port_admin, self.allocator.port_range_start)

        # They may be the same (hash-based allocation from same project)
        # To get different ports, services would need to register and mark as unavailable


if __name__ == "__main__":
    unittest.main()
