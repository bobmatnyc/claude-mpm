"""Tests for the orchestrator factory."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from claude_mpm.orchestration.factory import OrchestratorFactory, OrchestratorMode
from claude_mpm.orchestration.orchestrator import MPMOrchestrator
from claude_mpm.orchestration.system_prompt_orchestrator import SystemPromptOrchestrator
from claude_mpm.orchestration.subprocess_orchestrator import SubprocessOrchestrator
from claude_mpm.orchestration.interactive_subprocess_orchestrator import InteractiveSubprocessOrchestrator


class TestOrchestratorFactory:
    """Test cases for OrchestratorFactory."""
    
    def test_factory_initialization(self):
        """Test factory initializes with core orchestrators."""
        factory = OrchestratorFactory()
        
        # Check core orchestrators are registered
        assert OrchestratorMode.SYSTEM_PROMPT in factory._registry
        assert OrchestratorMode.SUBPROCESS in factory._registry
        assert OrchestratorMode.INTERACTIVE_SUBPROCESS in factory._registry
    
    def test_list_available_modes(self):
        """Test listing available orchestrator modes."""
        factory = OrchestratorFactory()
        modes = factory.list_available_modes()
        
        # Check core modes are present
        assert "system_prompt" in modes
        assert "subprocess" in modes
        assert "interactive_subprocess" in modes
        
        # Check metadata structure
        for mode_name, info in modes.items():
            assert "class" in info
            assert "module" in info
            assert "description" in info
    
    def test_create_default_orchestrator(self):
        """Test creating orchestrator with default settings."""
        factory = OrchestratorFactory()
        
        with patch('claude_mpm.core.framework_loader.FrameworkLoader'):
            orchestrator = factory.create_orchestrator()
            
        assert isinstance(orchestrator, SystemPromptOrchestrator)
        assert orchestrator.ticket_creation_enabled is True
    
    def test_create_subprocess_orchestrator(self):
        """Test creating subprocess orchestrator via config."""
        factory = OrchestratorFactory()
        
        config = {
            "subprocess": True,
            "enable_todo_hijacking": True,
            "log_level": "DEBUG"
        }
        
        with patch('claude_mpm.core.framework_loader.FrameworkLoader'):
            orchestrator = factory.create_orchestrator(config=config)
            
        assert isinstance(orchestrator, SubprocessOrchestrator)
    
    def test_create_interactive_subprocess_orchestrator(self):
        """Test creating interactive subprocess orchestrator."""
        factory = OrchestratorFactory()
        
        config = {
            "interactive_subprocess": True,
            "log_level": "INFO"
        }
        
        with patch('claude_mpm.core.framework_loader.FrameworkLoader'):
            orchestrator = factory.create_orchestrator(config=config)
            
        assert isinstance(orchestrator, InteractiveSubprocessOrchestrator)
    
    def test_create_with_explicit_mode(self):
        """Test creating orchestrator with explicit mode parameter."""
        factory = OrchestratorFactory()
        
        with patch('claude_mpm.core.framework_loader.FrameworkLoader'):
            orchestrator = factory.create_orchestrator(mode="system_prompt")
            
        assert isinstance(orchestrator, SystemPromptOrchestrator)
    
    def test_mode_precedence(self):
        """Test that explicit mode takes precedence over config flags."""
        factory = OrchestratorFactory()
        
        config = {
            "subprocess": True,  # This should be ignored
            "interactive_subprocess": True,  # This should be ignored
        }
        
        with patch('claude_mpm.core.framework_loader.FrameworkLoader'):
            orchestrator = factory.create_orchestrator(
                mode="system_prompt",
                config=config
            )
            
        assert isinstance(orchestrator, SystemPromptOrchestrator)
    
    def test_disable_ticket_creation(self):
        """Test disabling ticket creation via config."""
        factory = OrchestratorFactory()
        
        config = {
            "no_tickets": True,
            "log_level": "OFF"
        }
        
        with patch('claude_mpm.core.framework_loader.FrameworkLoader'):
            orchestrator = factory.create_orchestrator(config=config)
            
        assert orchestrator.ticket_creation_enabled is False
    
    def test_invalid_mode_raises_error(self):
        """Test that invalid mode raises ValueError."""
        factory = OrchestratorFactory()
        
        with pytest.raises(ValueError, match="Invalid orchestrator mode"):
            factory.create_orchestrator(mode="invalid_mode")
    
    def test_register_custom_orchestrator(self):
        """Test registering a custom orchestrator."""
        factory = OrchestratorFactory()
        
        # Create a mock orchestrator class
        class CustomOrchestrator(MPMOrchestrator):
            """Custom test orchestrator."""
            pass
        
        # Register it
        custom_mode = OrchestratorMode.SIMPLE  # Reuse existing enum
        factory.register_orchestrator(custom_mode, CustomOrchestrator)
        
        # Verify it's registered
        assert factory._registry[custom_mode] == CustomOrchestrator
        
        # Create instance
        with patch('claude_mpm.core.framework_loader.FrameworkLoader'):
            orchestrator = factory.create_orchestrator(mode="simple")
            
        assert isinstance(orchestrator, CustomOrchestrator)
    
    def test_register_invalid_orchestrator_raises_error(self):
        """Test that registering non-orchestrator class raises error."""
        factory = OrchestratorFactory()
        
        # Try to register a non-orchestrator class
        class NotAnOrchestrator:
            pass
        
        with pytest.raises(ValueError, match="must inherit from MPMOrchestrator"):
            factory.register_orchestrator(
                OrchestratorMode.SIMPLE,
                NotAnOrchestrator
            )
    
    def test_config_parameters_passed_correctly(self):
        """Test that config parameters are passed to orchestrator."""
        factory = OrchestratorFactory()
        
        config = {
            "framework_path": Path("/test/framework"),
            "agents_dir": Path("/test/agents"),
            "log_level": "DEBUG",
            "log_dir": Path("/test/logs"),
            "hook_manager": Mock(),
        }
        
        with patch('claude_mpm.core.framework_loader.FrameworkLoader'):
            orchestrator = factory.create_orchestrator(config=config)
            
        # Verify parameters were passed (would need to check orchestrator attributes)
        assert orchestrator.log_level == "DEBUG"
    
    def test_orchestrator_creation_error_handling(self):
        """Test error handling when orchestrator creation fails."""
        factory = OrchestratorFactory()
        
        # Mock the orchestrator class to raise an error
        with patch.object(
            factory._registry[OrchestratorMode.SYSTEM_PROMPT],
            '__init__',
            side_effect=Exception("Test error")
        ):
            with pytest.raises(ValueError, match="Failed to create orchestrator"):
                factory.create_orchestrator()
    
    def test_mode_determination_case_insensitive(self):
        """Test that mode determination is case-insensitive."""
        factory = OrchestratorFactory()
        
        with patch('claude_mpm.core.framework_loader.FrameworkLoader'):
            orchestrator1 = factory.create_orchestrator(mode="SYSTEM_PROMPT")
            orchestrator2 = factory.create_orchestrator(mode="system_prompt")
            orchestrator3 = factory.create_orchestrator(mode="System_Prompt")
            
        assert type(orchestrator1) == type(orchestrator2) == type(orchestrator3)