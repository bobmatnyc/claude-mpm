"""Orchestrator factory for creating orchestrators based on mode and configuration."""

import logging
from pathlib import Path
from typing import Optional, Dict, Type, Any
from enum import Enum

from ..core.logger import get_logger
from .orchestrator import MPMOrchestrator
from .system_prompt_orchestrator import SystemPromptOrchestrator
from .subprocess_orchestrator import SubprocessOrchestrator
from .interactive_subprocess_orchestrator import InteractiveSubprocessOrchestrator


class OrchestratorMode(Enum):
    """Available orchestrator modes."""
    SYSTEM_PROMPT = "system_prompt"
    SUBPROCESS = "subprocess"
    INTERACTIVE_SUBPROCESS = "interactive_subprocess"
    DIRECT = "direct"
    PTY = "pty"
    WRAPPER = "wrapper"
    SIMPLE = "simple"


class OrchestratorFactory:
    """Factory for creating orchestrators based on mode and configuration.
    
    This factory simplifies orchestrator selection and reduces complexity
    in the run_session function by centralizing the logic for choosing
    and instantiating the appropriate orchestrator.
    """
    
    # Registry of available orchestrators
    _registry: Dict[OrchestratorMode, Type[MPMOrchestrator]] = {
        OrchestratorMode.SYSTEM_PROMPT: SystemPromptOrchestrator,
        OrchestratorMode.SUBPROCESS: SubprocessOrchestrator,
        OrchestratorMode.INTERACTIVE_SUBPROCESS: InteractiveSubprocessOrchestrator,
    }
    
    def __init__(self):
        """Initialize the orchestrator factory."""
        self.logger = get_logger(self.__class__.__name__)
        self._discover_orchestrators()
    
    def _discover_orchestrators(self):
        """Discover and register additional orchestrators.
        
        This method enables automatic discovery of new orchestrator types
        without modifying the factory code.
        """
        # Try to import optional orchestrators
        try:
            from .direct_orchestrator import DirectOrchestrator
            self._registry[OrchestratorMode.DIRECT] = DirectOrchestrator
            self.logger.debug("Registered DirectOrchestrator")
        except ImportError:
            self.logger.debug("DirectOrchestrator not available")
        
        try:
            from .pty_orchestrator import PTYOrchestrator
            self._registry[OrchestratorMode.PTY] = PTYOrchestrator
            self.logger.debug("Registered PTYOrchestrator")
        except ImportError:
            self.logger.debug("PTYOrchestrator not available")
        
        try:
            from .wrapper_orchestrator import WrapperOrchestrator
            self._registry[OrchestratorMode.WRAPPER] = WrapperOrchestrator
            self.logger.debug("Registered WrapperOrchestrator")
        except ImportError:
            self.logger.debug("WrapperOrchestrator not available")
        
        try:
            from .simple_orchestrator import SimpleOrchestrator
            self._registry[OrchestratorMode.SIMPLE] = SimpleOrchestrator
            self.logger.debug("Registered SimpleOrchestrator")
        except ImportError:
            self.logger.debug("SimpleOrchestrator not available")
    
    def create_orchestrator(
        self,
        mode: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None
    ) -> MPMOrchestrator:
        """Create an orchestrator based on mode and configuration.
        
        Args:
            mode: Orchestrator mode (string or OrchestratorMode enum)
            config: Configuration dictionary containing:
                - framework_path: Path to framework directory
                - agents_dir: Custom agents directory
                - log_level: Logging level (OFF, INFO, DEBUG)
                - log_dir: Custom log directory
                - hook_manager: Hook service manager instance
                - enable_todo_hijacking: Enable TODO hijacking (subprocess mode)
                - subprocess: Use subprocess orchestration
                - interactive_subprocess: Use interactive subprocess
                - Any other orchestrator-specific parameters
        
        Returns:
            Configured orchestrator instance
            
        Raises:
            ValueError: If mode is invalid or orchestrator creation fails
        """
        if config is None:
            config = {}
        
        # Determine orchestrator mode
        orchestrator_mode = self._determine_mode(mode, config)
        
        # Validate mode
        if orchestrator_mode not in self._registry:
            available = ", ".join(m.value for m in self._registry.keys())
            raise ValueError(
                f"Invalid orchestrator mode: {orchestrator_mode.value}. "
                f"Available modes: {available}"
            )
        
        # Get orchestrator class
        orchestrator_class = self._registry[orchestrator_mode]
        
        # Extract common parameters
        common_params = {
            "framework_path": config.get("framework_path"),
            "agents_dir": config.get("agents_dir"),
            "log_level": config.get("log_level", "OFF"),
            "log_dir": config.get("log_dir"),
        }
        
        # Add hook manager if available
        if "hook_manager" in config:
            common_params["hook_manager"] = config["hook_manager"]
        
        # Add mode-specific parameters
        if orchestrator_mode == OrchestratorMode.SUBPROCESS:
            common_params["enable_todo_hijacking"] = config.get("enable_todo_hijacking", False)
        
        try:
            # Create orchestrator instance
            orchestrator = orchestrator_class(**common_params)
            
            # Configure additional settings
            if "no_tickets" in config and config["no_tickets"]:
                orchestrator.ticket_creation_enabled = False
                self.logger.info("Ticket creation disabled for orchestrator")
            
            self.logger.info(
                f"Created {orchestrator_class.__name__} "
                f"(mode: {orchestrator_mode.value})"
            )
            
            return orchestrator
            
        except Exception as e:
            self.logger.error(f"Failed to create orchestrator: {e}")
            raise ValueError(f"Failed to create orchestrator: {e}") from e
    
    def _determine_mode(
        self,
        mode: Optional[str],
        config: Dict[str, Any]
    ) -> OrchestratorMode:
        """Determine orchestrator mode from explicit mode or config flags.
        
        Args:
            mode: Explicit mode string
            config: Configuration dictionary
            
        Returns:
            OrchestratorMode enum value
        """
        # Always use subprocess orchestrator for simplicity
        # This provides consistent behavior in both interactive and non-interactive modes
        return OrchestratorMode.SUBPROCESS
    
    def list_available_modes(self) -> Dict[str, Dict[str, Any]]:
        """List all available orchestrator modes with metadata.
        
        Returns:
            Dictionary mapping mode names to metadata
        """
        modes = {}
        for mode, orchestrator_class in self._registry.items():
            modes[mode.value] = {
                "class": orchestrator_class.__name__,
                "module": orchestrator_class.__module__,
                "description": orchestrator_class.__doc__.strip() if orchestrator_class.__doc__ else "No description",
            }
        return modes
    
    def register_orchestrator(
        self,
        mode: OrchestratorMode,
        orchestrator_class: Type[MPMOrchestrator]
    ):
        """Register a custom orchestrator.
        
        Args:
            mode: Orchestrator mode
            orchestrator_class: Orchestrator class (must inherit from MPMOrchestrator)
            
        Raises:
            ValueError: If orchestrator class is invalid
        """
        if not issubclass(orchestrator_class, MPMOrchestrator):
            raise ValueError(
                f"{orchestrator_class.__name__} must inherit from MPMOrchestrator"
            )
        
        self._registry[mode] = orchestrator_class
        self.logger.info(
            f"Registered {orchestrator_class.__name__} for mode {mode.value}"
        )