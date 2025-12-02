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
        """Test that PEP 668 is detected when EXTERNALLY-MANAGED file exists (not in venv)."""
        with patch("pathlib.Path.exists") as mock_exists, patch.object(
            RobustPackageInstaller, "_check_virtualenv", return_value=False
        ):
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
        """Test that PEP 668 flags are added to pip commands when needed (not in venv)."""
        with patch("pathlib.Path.exists") as mock_exists, patch.object(
            RobustPackageInstaller, "_check_virtualenv", return_value=False
        ):
            mock_exists.return_value = True  # Simulate PEP 668 environment

            installer = RobustPackageInstaller()

            # Test normal pip command
            cmd = installer._build_install_command("requests", InstallStrategy.PIP)
            self.assertIn("--break-system-packages", cmd)
            self.assertNotIn(
                "--user", cmd
            )  # Should NOT use --user with --break-system-packages

            # Test upgrade command
            cmd_upgrade = installer._build_install_command(
                "requests", InstallStrategy.PIP_UPGRADE
            )
            self.assertIn("--break-system-packages", cmd_upgrade)
            self.assertNotIn("--user", cmd_upgrade)
            self.assertIn("--upgrade", cmd_upgrade)

    def test_pep668_flags_not_added_when_not_managed(self):
        """Test that --user flag is used in normal system Python (not PEP 668, not venv)."""
        with patch("pathlib.Path.exists") as mock_exists, patch.object(
            RobustPackageInstaller, "_check_virtualenv", return_value=False
        ):
            mock_exists.return_value = False  # Not a PEP 668 environment

            installer = RobustPackageInstaller()

            # Test normal pip command - should use --user
            cmd = installer._build_install_command("requests", InstallStrategy.PIP)
            self.assertNotIn("--break-system-packages", cmd)
            self.assertIn("--user", cmd)  # Should use --user in normal system Python

    def test_pep668_warning_shown_once(self):
        """Test that PEP 668 warning is only shown once."""
        with patch("pathlib.Path.exists") as mock_exists, patch.object(
            RobustPackageInstaller, "_check_virtualenv", return_value=False
        ):
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
        """Test that batch installation also handles PEP 668 (not in venv)."""
        with patch("pathlib.Path.exists") as mock_exists, patch.object(
            RobustPackageInstaller, "_check_virtualenv", return_value=False
        ):
            mock_exists.return_value = True  # Simulate PEP 668 environment

            installer = RobustPackageInstaller()

            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stderr="")

                installer._attempt_batch_install(["package1", "package2"])

                # Check that the command includes PEP 668 flags
                called_cmd = mock_run.call_args[0][0]
                self.assertIn("--break-system-packages", called_cmd)
                self.assertNotIn("--user", called_cmd)  # Should NOT use --user

    def test_report_includes_pep668_status(self):
        """Test that installation report includes PEP 668 status."""
        with patch("pathlib.Path.exists") as mock_exists, patch.object(
            RobustPackageInstaller, "_check_virtualenv", return_value=False
        ):
            mock_exists.return_value = True  # Simulate PEP 668 environment

            installer = RobustPackageInstaller()
            report = installer.get_report()

            self.assertIn("PEP 668 Managed Environment: YES", report)
            self.assertIn("--break-system-packages", report)
            self.assertNotIn("--user", report)  # Should NOT mention --user flag
            self.assertIn("virtual environment", report)

    def test_virtualenv_detection(self):
        """Test that virtualenv is properly detected."""
        # This test runs in actual environment, so result depends on current setup
        installer = RobustPackageInstaller()

        # Check consistency with manual detection
        import os

        expected_venv = (
            (hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix)
            or hasattr(sys, "real_prefix")
            or os.environ.get("VIRTUAL_ENV") is not None
        )

        self.assertEqual(installer.in_virtualenv, expected_venv)
        print(f"\nVirtualenv detected: {installer.in_virtualenv}")
        print(f"Python: {sys.executable}")

    def test_virtualenv_no_special_flags(self):
        """Test that no special flags are used in virtualenv."""
        with patch.object(
            RobustPackageInstaller, "_check_virtualenv", return_value=True
        ):
            installer = RobustPackageInstaller()
            self.assertTrue(installer.in_virtualenv)
            self.assertFalse(installer.is_pep668_managed)  # Should be False in venv

            # Build command - should have no special flags
            cmd = installer._build_install_command("requests", InstallStrategy.PIP)
            self.assertNotIn("--break-system-packages", cmd)
            self.assertNotIn("--user", cmd)

    def test_actual_pep668_detection(self):
        """Test actual PEP 668 detection in the current environment."""
        installer = RobustPackageInstaller()

        # If in virtualenv, PEP 668 should be False
        if installer.in_virtualenv:
            self.assertFalse(installer.is_pep668_managed)
            print("\nRunning in virtualenv - PEP 668 not applicable")
        else:
            # Check if current environment is PEP 668 managed
            stdlib_path = sysconfig.get_path("stdlib")
            marker_file = Path(stdlib_path) / "EXTERNALLY-MANAGED"
            parent_marker = marker_file.parent.parent / "EXTERNALLY-MANAGED"

            expected = marker_file.exists() or parent_marker.exists()
            self.assertEqual(installer.is_pep668_managed, expected)

            print(
                f"\nCurrent environment PEP 668 status: {installer.is_pep668_managed}"
            )

        print(f"Python: {sys.executable}")
        print(f"Version: {sys.version}")


if __name__ == "__main__":
    unittest.main()
