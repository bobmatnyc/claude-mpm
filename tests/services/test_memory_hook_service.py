"""Test module for MemoryHookService."""

import pytest
from unittest.mock import Mock, MagicMock
from claude_mpm.services.memory_hook_service import MemoryHookService
from claude_mpm.services.core.interfaces import MemoryHookInterface


class TestMemoryHookService:
    """Test cases for MemoryHookService."""

    def test_service_implements_interface(self):
        """Test that MemoryHookService implements MemoryHookInterface."""
        service = MemoryHookService()
        assert isinstance(service, MemoryHookInterface)

    def test_service_instantiation(self):
        """Test that MemoryHookService can be instantiated without errors."""
        service = MemoryHookService()
        assert service is not None
        assert service.name == "memory_hook_service"
        assert service.hook_service is None
        assert service.registered_hooks == []

    def test_service_instantiation_with_hook_service(self):
        """Test instantiation with a hook service."""
        mock_hook_service = Mock()
        service = MemoryHookService(hook_service=mock_hook_service)
        assert service.hook_service == mock_hook_service

    def test_get_hook_status(self):
        """Test get_hook_status method returns correct structure."""
        service = MemoryHookService()
        status = service.get_hook_status()
        
        assert isinstance(status, dict)
        assert "registered_hooks" in status
        assert "hook_service_available" in status
        assert "memory_enabled" in status
        assert "total_hooks" in status
        assert "status" in status
        
        # Check initial values
        assert status["registered_hooks"] == []
        assert status["hook_service_available"] is False
        assert status["memory_enabled"] is False
        assert status["total_hooks"] == 0
        assert status["status"] == "inactive"

    def test_get_hook_status_with_hooks(self):
        """Test get_hook_status with registered hooks."""
        mock_hook_service = Mock()
        service = MemoryHookService(hook_service=mock_hook_service)
        service.registered_hooks = ["memory_load", "memory_save"]
        
        status = service.get_hook_status()
        
        assert status["registered_hooks"] == ["memory_load", "memory_save"]
        assert status["hook_service_available"] is True
        assert status["total_hooks"] == 2
        assert status["status"] == "active"

    def test_get_memory_status(self):
        """Test get_memory_status method."""
        service = MemoryHookService()
        status = service.get_memory_status()
        
        assert isinstance(status, dict)
        assert "enabled" in status
        assert "hooks_registered" in status
        assert "service_available" in status
        
        assert status["enabled"] is False
        assert status["hooks_registered"] is False
        assert status["service_available"] is True

    def test_is_memory_enabled(self):
        """Test is_memory_enabled method."""
        service = MemoryHookService()
        assert service.is_memory_enabled() is False

    def test_register_memory_hooks_without_hook_service(self):
        """Test register_memory_hooks when no hook service is available."""
        service = MemoryHookService()
        service.register_memory_hooks()
        
        # Should not register any hooks
        assert service.registered_hooks == []

    def test_register_memory_hooks_with_hook_service(self):
        """Test register_memory_hooks with a mock hook service."""
        mock_hook_service = Mock()
        mock_hook_service.register_hook = Mock(return_value=True)
        
        service = MemoryHookService(hook_service=mock_hook_service)
        service.register_memory_hooks()
        
        # Should have registered two hooks
        assert mock_hook_service.register_hook.call_count == 2
        assert "memory_load" in service.registered_hooks
        assert "memory_save" in service.registered_hooks

    def test_unregister_memory_hooks(self):
        """Test unregister_memory_hooks method."""
        mock_hook_service = Mock()
        service = MemoryHookService(hook_service=mock_hook_service)
        
        service.unregister_memory_hooks()
        
        # Should attempt to unregister hooks
        assert mock_hook_service.unregister_hook.call_count == 3

    @pytest.mark.asyncio
    async def test_initialize_and_cleanup(self):
        """Test async initialization and cleanup methods."""
        service = MemoryHookService()
        
        # Test initialization
        await service._initialize()
        
        # Test cleanup
        await service._cleanup()
        
        # These are no-op methods but should not raise errors
        assert True

    def test_all_abstract_methods_implemented(self):
        """Verify all abstract methods from MemoryHookInterface are implemented."""
        # Get all abstract methods from the interface
        from abc import ABC
        interface_methods = [
            method for method in dir(MemoryHookInterface)
            if not method.startswith('_') and callable(getattr(MemoryHookInterface, method))
        ]
        
        service = MemoryHookService()
        
        # Check each interface method is implemented
        for method_name in interface_methods:
            assert hasattr(service, method_name), f"Method {method_name} not implemented"
            assert callable(getattr(service, method_name)), f"Method {method_name} is not callable"