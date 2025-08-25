"""
Tests for Dashboard Launcher Service
=====================================

WHY: Tests ensure the DashboardLauncher service correctly manages dashboard
lifecycle, browser launching, port management, and error handling.

DESIGN DECISIONS:
- Mock external dependencies (subprocess, webbrowser, urllib)
- Test interface compliance
- Cover edge cases like port conflicts and browser failures
- Test platform-specific browser launching logic
- Verify error handling and fallback mechanisms
"""

import os
import platform
import socket
import subprocess
import sys
import urllib.error
import webbrowser
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch, call

import pytest

from claude_mpm.services.cli.dashboard_launcher import (
    DashboardLauncher,
    IDashboardLauncher,
)
from claude_mpm.services.port_manager import PortManager


class TestDashboardLauncherInterface:
    """Test IDashboardLauncher interface compliance."""
    
    def test_interface_implementation(self):
        """Test that DashboardLauncher implements IDashboardLauncher interface."""
        launcher = DashboardLauncher()
        assert isinstance(launcher, IDashboardLauncher)
        
    def test_interface_methods_exist(self):
        """Test that all interface methods are implemented."""
        launcher = DashboardLauncher()
        
        # Check all required methods exist
        assert hasattr(launcher, 'launch_dashboard')
        assert hasattr(launcher, 'is_dashboard_running')
        assert hasattr(launcher, 'get_dashboard_url')
        assert hasattr(launcher, 'stop_dashboard')
        assert hasattr(launcher, 'wait_for_dashboard')
        
        # Check they're callable
        assert callable(launcher.launch_dashboard)
        assert callable(launcher.is_dashboard_running)
        assert callable(launcher.get_dashboard_url)
        assert callable(launcher.stop_dashboard)
        assert callable(launcher.wait_for_dashboard)


class TestDashboardLauncher:
    """Test DashboardLauncher implementation."""
    
    @pytest.fixture
    def launcher(self):
        """Create a DashboardLauncher instance with mocked logger."""
        with patch('claude_mpm.services.cli.dashboard_launcher.get_logger') as mock_logger:
            mock_logger.return_value = MagicMock()
            launcher = DashboardLauncher()
            return launcher
            
    @pytest.fixture
    def mock_dependencies(self):
        """Mock common dependencies."""
        with patch.multiple(
            'claude_mpm.services.cli.dashboard_launcher',
            webbrowser=MagicMock(),
            subprocess=MagicMock(),
        ):
            yield
            
    def test_get_dashboard_url(self, launcher):
        """Test getting dashboard URL."""
        assert launcher.get_dashboard_url(8765) == "http://localhost:8765"
        assert launcher.get_dashboard_url(9000) == "http://localhost:9000"
        
    def test_is_dashboard_running_success(self, launcher):
        """Test checking if dashboard is running when it is."""
        with patch('socket.socket') as mock_socket_class:
            mock_socket = MagicMock()
            mock_socket.__enter__.return_value = mock_socket
            mock_socket.__exit__.return_value = None
            mock_socket.connect_ex.return_value = 0  # Connection successful
            mock_socket_class.return_value = mock_socket
            
            with patch('urllib.request.urlopen') as mock_urlopen:
                mock_response = MagicMock()
                mock_response.getcode.return_value = 200
                mock_urlopen.return_value = mock_response
                
                assert launcher.is_dashboard_running(8765) is True
                mock_socket.connect_ex.assert_called_once_with(("127.0.0.1", 8765))
                mock_urlopen.assert_called_once()
                
    def test_is_dashboard_running_tcp_fails(self, launcher):
        """Test checking if dashboard is running when TCP connection fails."""
        with patch('socket.socket') as mock_socket_class:
            mock_socket = MagicMock()
            mock_socket.__enter__.return_value = mock_socket
            mock_socket.__exit__.return_value = None
            mock_socket.connect_ex.return_value = 1  # Connection failed
            mock_socket_class.return_value = mock_socket
            
            assert launcher.is_dashboard_running(8765) is False
            mock_socket.connect_ex.assert_called_once_with(("127.0.0.1", 8765))
            
    def test_is_dashboard_running_http_fails(self, launcher):
        """Test when TCP succeeds but HTTP health check fails."""
        with patch('socket.socket') as mock_socket_class:
            mock_socket = MagicMock()
            mock_socket.__enter__.return_value = mock_socket
            mock_socket.__exit__.return_value = None
            mock_socket.connect_ex.return_value = 0  # TCP successful
            mock_socket_class.return_value = mock_socket
            
            with patch('urllib.request.urlopen') as mock_urlopen:
                mock_urlopen.side_effect = urllib.error.URLError("Connection refused")
                
                # Should still return True if TCP works (server starting up)
                assert launcher.is_dashboard_running(8765) is True
                
    def test_wait_for_dashboard_success(self, launcher):
        """Test waiting for dashboard to be ready."""
        with patch.object(launcher, 'is_dashboard_running') as mock_is_running:
            mock_is_running.side_effect = [False, False, True]  # Ready on third check
            
            with patch('time.sleep'):
                assert launcher.wait_for_dashboard(8765, timeout=5) is True
                assert mock_is_running.call_count == 3
                
    def test_wait_for_dashboard_timeout(self, launcher):
        """Test waiting for dashboard timeout."""
        with patch.object(launcher, 'is_dashboard_running') as mock_is_running:
            mock_is_running.return_value = False  # Never ready
            
            with patch('time.sleep'):
                with patch('time.time') as mock_time:
                    # Simulate timeout
                    mock_time.side_effect = [0, 0.5, 1, 1.5, 2, 2.5, 3, 3.5]
                    assert launcher.wait_for_dashboard(8765, timeout=3) is False
                    
    def test_launch_dashboard_server_already_running(self, launcher, mock_dependencies):
        """Test launching dashboard when server is already running."""
        launcher.port_manager = MagicMock()
        launcher.port_manager.cleanup_dead_instances = MagicMock()
        launcher.port_manager.list_active_instances = MagicMock(return_value=[
            {"port": 8765, "pid": 12345}
        ])
        
        with patch.object(launcher, 'is_dashboard_running', return_value=True):
            with patch.object(launcher, '_is_browser_suppressed', return_value=False):
                with patch.object(launcher, '_open_browser', return_value=True):
                    success, browser_opened = launcher.launch_dashboard(8765)
                    
                    assert success is True
                    assert browser_opened is True
                    launcher.port_manager.cleanup_dead_instances.assert_called_once()
                    
    def test_launch_dashboard_start_new_server(self, launcher, mock_dependencies):
        """Test launching dashboard when starting new server."""
        launcher.port_manager = MagicMock()
        launcher.port_manager.cleanup_dead_instances = MagicMock()
        launcher.port_manager.list_active_instances = MagicMock(return_value=[])
        
        with patch.object(launcher, 'is_dashboard_running', return_value=False):
            with patch.object(launcher, '_start_dashboard_server', return_value=True):
                with patch.object(launcher, '_is_browser_suppressed', return_value=False):
                    with patch.object(launcher, '_open_browser', return_value=True):
                        success, browser_opened = launcher.launch_dashboard(8765)
                        
                        assert success is True
                        assert browser_opened is True
                        
    def test_launch_dashboard_server_start_fails(self, launcher, mock_dependencies):
        """Test launching dashboard when server fails to start."""
        launcher.port_manager = MagicMock()
        launcher.port_manager.cleanup_dead_instances = MagicMock()
        launcher.port_manager.list_active_instances = MagicMock(return_value=[])
        
        with patch.object(launcher, 'is_dashboard_running', return_value=False):
            with patch.object(launcher, '_start_dashboard_server', return_value=False):
                with patch.object(launcher, '_print_troubleshooting_tips'):
                    success, browser_opened = launcher.launch_dashboard(8765)
                    
                    assert success is False
                    assert browser_opened is False
                    
    def test_launch_dashboard_browser_suppressed(self, launcher, mock_dependencies):
        """Test launching dashboard with browser suppressed."""
        launcher.port_manager = MagicMock()
        launcher.port_manager.cleanup_dead_instances = MagicMock()
        launcher.port_manager.list_active_instances = MagicMock(return_value=[])
        
        with patch.object(launcher, 'is_dashboard_running', return_value=False):
            with patch.object(launcher, '_start_dashboard_server', return_value=True):
                with patch.object(launcher, '_is_browser_suppressed', return_value=True):
                    with patch.object(launcher, '_open_browser') as mock_open:
                        success, browser_opened = launcher.launch_dashboard(8765)
                        
                        assert success is True
                        assert browser_opened is False
                        mock_open.assert_not_called()
                        
    def test_launch_dashboard_socketio_deps_missing(self, launcher):
        """Test launching dashboard when Socket.IO dependencies are missing."""
        with patch.object(launcher, '_verify_socketio_dependencies', return_value=False):
            success, browser_opened = launcher.launch_dashboard(8765, monitor_mode=True)
            
            assert success is False
            assert browser_opened is False
            
    def test_stop_dashboard_success(self, launcher):
        """Test stopping dashboard successfully."""
        with patch('claude_mpm.services.cli.dashboard_launcher.get_package_root') as mock_root:
            mock_root.return_value = Path("/mock/path")
            
            with patch('pathlib.Path.exists', return_value=True):
                with patch('subprocess.run') as mock_run:
                    mock_result = MagicMock()
                    mock_result.returncode = 0
                    mock_run.return_value = mock_result
                    
                    assert launcher.stop_dashboard(8765) is True
                    mock_run.assert_called_once()
                    
    def test_stop_dashboard_script_not_found(self, launcher):
        """Test stopping dashboard when daemon script doesn't exist."""
        with patch('claude_mpm.services.cli.dashboard_launcher.get_package_root') as mock_root:
            mock_root.return_value = Path("/mock/path")
            
            with patch('pathlib.Path.exists', return_value=False):
                assert launcher.stop_dashboard(8765) is False
                
    def test_browser_opening_macos(self, launcher):
        """Test browser opening on macOS."""
        with patch('platform.system', return_value='Darwin'):
            with patch('subprocess.run') as mock_run:
                assert launcher._open_browser("http://localhost:8765") is True
                mock_run.assert_called_once_with(
                    ["open", "-g", "http://localhost:8765"],
                    check=True,
                    timeout=5
                )
                
    def test_browser_opening_linux(self, launcher):
        """Test browser opening on Linux."""
        with patch('platform.system', return_value='Linux'):
            with patch('subprocess.run') as mock_run:
                assert launcher._open_browser("http://localhost:8765") is True
                mock_run.assert_called_once_with(
                    ["xdg-open", "http://localhost:8765"],
                    check=True,
                    timeout=5
                )
                
    def test_browser_opening_windows(self, launcher):
        """Test browser opening on Windows."""
        with patch('platform.system', return_value='Windows'):
            with patch('webbrowser.get') as mock_get:
                mock_browser = MagicMock()
                mock_get.return_value = mock_browser
                
                assert launcher._open_browser("http://localhost:8765") is True
                mock_browser.open.assert_called_once_with(
                    "http://localhost:8765",
                    new=0
                )
                
    def test_browser_opening_fallback(self, launcher):
        """Test browser opening fallback when platform-specific method fails."""
        with patch('platform.system', return_value='Darwin'):
            with patch('subprocess.run', side_effect=Exception("Failed")):
                with patch('webbrowser.open') as mock_open:
                    assert launcher._open_browser("http://localhost:8765") is True
                    mock_open.assert_called()
                    
    def test_determine_server_port_with_active_instances(self, launcher):
        """Test determining server port with active instances."""
        active_instances = [
            {"port": 8766, "pid": 12345},
            {"port": 8765, "pid": 12346},  # Prefer 8765
        ]
        
        # Should prefer port 8765
        port = launcher._determine_server_port(8770, active_instances)
        assert port == 8765
        
    def test_determine_server_port_no_preferred(self, launcher):
        """Test determining server port without preferred port available."""
        active_instances = [
            {"port": 8766, "pid": 12345},
            {"port": 8767, "pid": 12346},
        ]
        
        # Should use first active instance
        port = launcher._determine_server_port(8770, active_instances)
        assert port == 8766
        
    def test_determine_server_port_no_instances(self, launcher):
        """Test determining server port with no active instances."""
        # Should use requested port
        port = launcher._determine_server_port(8770, [])
        assert port == 8770
        
    def test_verify_socketio_dependencies_success(self, launcher):
        """Test verifying Socket.IO dependencies when they exist."""
        with patch.dict('sys.modules', {
            'aiohttp': MagicMock(),
            'engineio': MagicMock(),
            'socketio': MagicMock(),
        }):
            assert launcher._verify_socketio_dependencies() is True
            
    def test_verify_socketio_dependencies_missing(self, launcher):
        """Test verifying Socket.IO dependencies when missing."""
        # Test the actual implementation by mocking the import statement
        import builtins
        real_import = builtins.__import__
        
        def mock_import(name, *args, **kwargs):
            if name in ['aiohttp', 'engineio', 'socketio']:
                raise ImportError(f"No module named '{name}'")
            return real_import(name, *args, **kwargs)
        
        with patch('builtins.__import__', side_effect=mock_import):
            # This should catch the ImportError and return False
            assert launcher._verify_socketio_dependencies() is False
                
    def test_is_browser_suppressed(self, launcher):
        """Test checking if browser is suppressed."""
        with patch.dict(os.environ, {'CLAUDE_MPM_NO_BROWSER': '1'}):
            assert launcher._is_browser_suppressed() is True
            
        with patch.dict(os.environ, {'CLAUDE_MPM_NO_BROWSER': '0'}):
            assert launcher._is_browser_suppressed() is False
            
        with patch.dict(os.environ, {}, clear=True):
            assert launcher._is_browser_suppressed() is False


class TestDashboardLauncherIntegration:
    """Integration tests for DashboardLauncher."""
    
    @pytest.fixture
    def launcher(self):
        """Create a real DashboardLauncher instance."""
        return DashboardLauncher()
        
    def test_full_launch_cycle_mock(self, launcher):
        """Test full dashboard launch cycle with mocks."""
        with patch.object(launcher.port_manager, 'cleanup_dead_instances'):
            with patch.object(launcher.port_manager, 'list_active_instances', return_value=[]):
                with patch.object(launcher, 'is_dashboard_running', side_effect=[False, True]):
                    with patch.object(launcher, '_start_dashboard_server', return_value=True):
                        with patch.object(launcher, '_open_browser', return_value=True):
                            with patch.dict(os.environ, {}, clear=True):
                                success, browser_opened = launcher.launch_dashboard(8765)
                                
                                assert success is True
                                assert browser_opened is True
                                
    def test_error_handling_in_launch(self, launcher):
        """Test error handling during launch."""
        with patch.object(launcher.port_manager, 'cleanup_dead_instances', side_effect=Exception("Port manager error")):
            success, browser_opened = launcher.launch_dashboard(8765)
            
            assert success is False
            assert browser_opened is False
            
    def test_port_conflict_handling(self, launcher):
        """Test handling port conflicts."""
        # Simulate port in use by another process
        launcher.port_manager = MagicMock()
        launcher.port_manager.cleanup_dead_instances = MagicMock()
        launcher.port_manager.list_active_instances = MagicMock(return_value=[
            {"port": 8765, "pid": 99999}  # Different process
        ])
        
        with patch.object(launcher, 'is_dashboard_running', return_value=True):
            with patch.object(launcher, '_open_browser', return_value=True):
                # Should reuse existing server
                success, browser_opened = launcher.launch_dashboard(8765)
                
                assert success is True
                assert browser_opened is True