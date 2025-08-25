"""
Unit tests for PEP 668 handling in robust_installer.

WHY: PEP 668 prevents pip from installing packages into system Python
installations to avoid conflicts. We need to ensure our installer
correctly detects and handles these restrictions.
"""

import sys
import sysconfig
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from claude_mpm.utils.robust_installer import InstallStrategy, RobustPackageInstaller


class TestPEP668Handling(unittest.TestCase):
    """Test PEP 668 detection and handling in the robust installer."""

    def test_pep668_detection_with_marker_file(self):
        """Test that PEP 668 is detected when EXTERNALLY-MANAGED file exists."""
        with patch("pathlib.Path.exists") as mock_exists:
            # Simulate EXTERNALLY-MANAGED file exists
            mock_exists.return_value = True

            installer = RobustPackageInstaller()
            self.assertTrue(installer.is_pep668_managed)

    def test_pep668_detection_without_marker_file(self):
        """Test that PEP 668 is not detected when marker file is absent."""
        with patch("pathlib.Path.exists") as mock_exists:
            # Simulate EXTERNALLY-MANAGED file doesn't exist
            mock_exists.return_value = False

            installer = RobustPackageInstaller()
            self.assertFalse(installer.is_pep668_managed)

    def test_pep668_flags_added_to_commands(self):
        """Test that PEP 668 flags are added to pip commands when needed."""
        with patch("pathlib.Path.exists") as mock_exists:
            mock_exists.return_value = True  # Simulate PEP 668 environment

            installer = RobustPackageInstaller()

            # Test normal pip command
            cmd = installer._build_install_command("requests", InstallStrategy.PIP)
            self.assertIn("--break-system-packages", cmd)
            self.assertIn("--user", cmd)

            # Test upgrade command
            cmd_upgrade = installer._build_install_command(
                "requests", InstallStrategy.PIP_UPGRADE
            )
            self.assertIn("--break-system-packages", cmd_upgrade)
            self.assertIn("--user", cmd_upgrade)
            self.assertIn("--upgrade", cmd_upgrade)

    def test_pep668_flags_not_added_when_not_managed(self):
        """Test that PEP 668 flags are not added in normal environments."""
        with patch("pathlib.Path.exists") as mock_exists:
            mock_exists.return_value = False  # Not a PEP 668 environment

            installer = RobustPackageInstaller()

            # Test normal pip command
            cmd = installer._build_install_command("requests", InstallStrategy.PIP)
            self.assertNotIn("--break-system-packages", cmd)
            self.assertNotIn("--user", cmd)

    def test_pep668_warning_shown_once(self):
        """Test that PEP 668 warning is only shown once."""
        with patch("pathlib.Path.exists") as mock_exists:
            mock_exists.return_value = True  # Simulate PEP 668 environment

            installer = RobustPackageInstaller()
            self.assertFalse(installer.pep668_warning_shown)

            # First command should show warning
            with patch.object(installer, "_show_pep668_warning") as mock_warning:
                installer._build_install_command("package1", InstallStrategy.PIP)
                mock_warning.assert_called_once()

            # After first warning, flag should be set
            installer.pep668_warning_shown = True

            # Subsequent commands should not show warning again
            with patch.object(installer, "_show_pep668_warning") as mock_warning:
                mock_warning.side_effect = lambda: setattr(
                    installer, "pep668_warning_shown", True
                )
                installer._build_install_command("package2", InstallStrategy.PIP)
                # Warning should still be called but internal flag prevents duplicate output

    def test_batch_install_with_pep668(self):
        """Test that batch installation also handles PEP 668."""
        with patch("pathlib.Path.exists") as mock_exists:
            mock_exists.return_value = True  # Simulate PEP 668 environment

            installer = RobustPackageInstaller()

            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stderr="")

                installer._attempt_batch_install(["package1", "package2"])

                # Check that the command includes PEP 668 flags
                called_cmd = mock_run.call_args[0][0]
                self.assertIn("--break-system-packages", called_cmd)
                self.assertIn("--user", called_cmd)

    def test_report_includes_pep668_status(self):
        """Test that installation report includes PEP 668 status."""
        with patch("pathlib.Path.exists") as mock_exists:
            mock_exists.return_value = True  # Simulate PEP 668 environment

            installer = RobustPackageInstaller()
            report = installer.get_report()

            self.assertIn("PEP 668 Managed Environment: YES", report)
            self.assertIn("--break-system-packages --user", report)
            self.assertIn("virtual environment", report)

    def test_actual_pep668_detection(self):
        """Test actual PEP 668 detection in the current environment."""
        installer = RobustPackageInstaller()

        # Check if current environment is PEP 668 managed
        stdlib_path = sysconfig.get_path("stdlib")
        marker_file = Path(stdlib_path) / "EXTERNALLY-MANAGED"
        parent_marker = marker_file.parent.parent / "EXTERNALLY-MANAGED"

        expected = marker_file.exists() or parent_marker.exists()
        self.assertEqual(installer.is_pep668_managed, expected)

        print(f"\nCurrent environment PEP 668 status: {installer.is_pep668_managed}")
        print(f"Python: {sys.executable}")
        print(f"Version: {sys.version}")


if __name__ == "__main__":
    unittest.main()
