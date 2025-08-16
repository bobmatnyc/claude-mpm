"""Memory-aware Claude runner with automatic restart capabilities.

This runner extends ClaudeRunner to add memory monitoring and automatic
restart capabilities when memory thresholds are exceeded.

Design Principles:
- Seamless integration with existing ClaudeRunner
- State preservation across restarts
- Configurable memory thresholds and policies
- Minimal overhead when monitoring is disabled
"""

import asyncio
import json
import os
import sys
import time
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

from claude_mpm.core.claude_runner import ClaudeRunner
from claude_mpm.core.logging_config import get_logger
from claude_mpm.services.infrastructure.memory_guardian import MemoryGuardian
from claude_mpm.services.infrastructure.state_manager import StateManager
from claude_mpm.config.memory_guardian_config import (
    MemoryGuardianConfig,
    MemoryThresholds,
    RestartPolicy,
    MonitoringConfig,
    get_default_config
)


class MemoryAwareClaudeRunner(ClaudeRunner):
    """Claude runner with memory monitoring and automatic restart capabilities.
    
    This class extends ClaudeRunner to add memory monitoring through the
    MemoryGuardian service. When memory thresholds are exceeded, it can
    automatically restart Claude Code while preserving conversation state.
    
    WHY: Large conversation histories in .claude.json can consume 2GB+ of memory,
    causing system instability. This runner monitors memory usage and performs
    controlled restarts with state preservation.
    
    DESIGN DECISION: We extend ClaudeRunner rather than wrap it to maintain
    full compatibility with existing code while adding new capabilities.
    """
    
    def __init__(
        self,
        enable_tickets: bool = True,
        log_level: str = "OFF",
        claude_args: Optional[list] = None,
        launch_method: str = "subprocess",  # Default to subprocess for monitoring
        enable_websocket: bool = False,
        websocket_port: int = 8765,
        memory_config: Optional[MemoryGuardianConfig] = None,
        enable_monitoring: bool = True,
        state_dir: Optional[Path] = None
    ):
        """Initialize memory-aware Claude runner.
        
        Args:
            enable_tickets: Enable ticket extraction
            log_level: Logging level
            claude_args: Additional arguments for Claude
            launch_method: Launch method (subprocess required for monitoring)
            enable_websocket: Enable WebSocket server
            websocket_port: WebSocket server port
            memory_config: Memory guardian configuration
            enable_monitoring: Enable memory monitoring
            state_dir: Directory for state preservation
        """
        # Force subprocess mode if monitoring is enabled
        if enable_monitoring and launch_method == "exec":
            launch_method = "subprocess"
            get_logger(__name__).info(
                "Switching to subprocess launch method for memory monitoring"
            )
        
        # Initialize parent
        super().__init__(
            enable_tickets=enable_tickets,
            log_level=log_level,
            claude_args=claude_args,
            launch_method=launch_method,
            enable_websocket=enable_websocket,
            websocket_port=websocket_port
        )
        
        # Memory monitoring configuration
        self.enable_monitoring = enable_monitoring
        self.memory_config = memory_config or get_default_config()
        self.memory_config.enabled = enable_monitoring
        
        # State management
        self.state_dir = state_dir or Path.home() / ".claude-mpm" / "state"
        self.state_manager: Optional[StateManager] = None
        self.memory_guardian: Optional[MemoryGuardian] = None
        
        # Monitoring state
        self.monitoring_task: Optional[asyncio.Task] = None
        self.restart_count = 0
        self.max_restarts = 3  # Default max restarts
        
        self.logger.info(f"Memory-aware runner initialized with monitoring: {enable_monitoring}")
    
    def run_interactive_with_monitoring(
        self,
        initial_context: Optional[str] = None,
        memory_threshold: Optional[float] = None,
        check_interval: Optional[int] = None,
        max_restarts: Optional[int] = None,
        enable_state_preservation: bool = True
    ):
        """Run Claude in interactive mode with memory monitoring.
        
        This method wraps the standard interactive session with memory monitoring
        and automatic restart capabilities.
        
        Args:
            initial_context: Optional initial context
            memory_threshold: Override memory threshold in MB
            check_interval: Override check interval in seconds
            max_restarts: Maximum number of automatic restarts
            enable_state_preservation: Enable state preservation across restarts
        """
        if not self.enable_monitoring:
            # Fall back to standard interactive mode
            self.logger.info("Memory monitoring disabled, using standard interactive mode")
            return self.run_interactive(initial_context)
        
        # Update configuration with overrides
        if memory_threshold:
            self.memory_config.thresholds.critical = memory_threshold
            self.memory_config.thresholds.emergency = memory_threshold * 1.2
        
        if check_interval:
            self.memory_config.monitoring.normal_interval = check_interval
        
        if max_restarts is not None:
            self.max_restarts = max_restarts
            self.memory_config.restart_policy.max_attempts = max_restarts
        
        # Run async monitoring loop
        try:
            asyncio.run(self._run_with_monitoring_async(
                initial_context,
                enable_state_preservation
            ))
        except KeyboardInterrupt:
            self.logger.info("Interactive session interrupted by user")
        except Exception as e:
            self.logger.error(f"Error in monitored session: {e}")
            raise
    
    async def _run_with_monitoring_async(
        self,
        initial_context: Optional[str],
        enable_state_preservation: bool
    ):
        """Async implementation of monitored interactive session.
        
        This method sets up the memory monitoring infrastructure and manages
        the Claude subprocess lifecycle with automatic restarts.
        """
        try:
            # Initialize services
            await self._initialize_monitoring_services(enable_state_preservation)
            
            # Display monitoring information
            self._display_monitoring_info()
            
            # Start monitoring loop
            while self.restart_count <= self.max_restarts:
                try:
                    # Run Claude subprocess
                    await self._run_monitored_subprocess(initial_context)
                    
                    # If we exit normally, break the loop
                    break
                    
                except MemoryThresholdExceeded as e:
                    self.logger.warning(f"Memory threshold exceeded: {e}")
                    
                    if self.restart_count >= self.max_restarts:
                        self.logger.error("Maximum restart attempts reached")
                        break
                    
                    # Perform controlled restart
                    await self._perform_controlled_restart()
                    self.restart_count += 1
                    
                    # Clear initial context after first run
                    initial_context = None
                    
                except Exception as e:
                    self.logger.error(f"Unexpected error in monitored session: {e}")
                    break
            
        finally:
            # Cleanup
            await self._cleanup_monitoring_services()
    
    async def _initialize_monitoring_services(self, enable_state_preservation: bool):
        """Initialize memory guardian and state manager services."""
        self.logger.info("Initializing monitoring services")
        
        # Initialize state manager if enabled
        if enable_state_preservation:
            self.state_manager = StateManager(self.state_dir)
            await self.state_manager.initialize()
            self.logger.info("State preservation enabled")
        
        # Initialize memory guardian
        self.memory_guardian = MemoryGuardian(self.memory_config)
        if self.state_manager:
            self.memory_guardian.set_state_manager(self.state_manager)
        await self.memory_guardian.initialize()
        
        self.logger.info("Monitoring services initialized")
    
    async def _cleanup_monitoring_services(self):
        """Cleanup monitoring services."""
        self.logger.info("Cleaning up monitoring services")
        
        if self.memory_guardian:
            await self.memory_guardian.shutdown()
        
        if self.state_manager:
            await self.state_manager.shutdown()
    
    async def _run_monitored_subprocess(self, initial_context: Optional[str]):
        """Run Claude subprocess with memory monitoring.
        
        This method launches Claude as a subprocess and monitors its memory usage,
        triggering restarts when thresholds are exceeded.
        """
        # Set up the process command
        cmd = self._build_claude_command(initial_context)
        
        # Configure memory guardian with our command
        self.memory_config.process_command = cmd
        self.memory_config.working_directory = os.getcwd()
        
        # Start the process through memory guardian
        success = await self.memory_guardian.start_process()
        if not success:
            raise RuntimeError("Failed to start Claude process")
        
        # Start memory monitoring
        self.memory_guardian.start_monitoring()
        
        # Wait for process to complete or be restarted
        while self.memory_guardian.process_state.value == "running":
            await asyncio.sleep(1)
            
            # Check for memory threshold exceeded
            if self.memory_guardian.memory_state.value in ["critical", "emergency"]:
                raise MemoryThresholdExceeded(
                    f"Memory state: {self.memory_guardian.memory_state.value}, "
                    f"Current: {self.memory_guardian.memory_stats.current_mb:.2f}MB"
                )
    
    async def _perform_controlled_restart(self):
        """Perform a controlled restart with state preservation."""
        self.logger.info(f"Performing controlled restart (attempt {self.restart_count + 1}/{self.max_restarts})")
        
        # Capture state before restart
        if self.state_manager:
            state = await self.state_manager.capture_state(
                restart_reason=f"Memory threshold exceeded (restart {self.restart_count + 1})"
            )
            if state:
                await self.state_manager.persist_state(state)
                self.logger.info("State captured and persisted")
        
        # Restart through memory guardian
        success = await self.memory_guardian.restart_process(
            reason=f"Memory threshold exceeded (automatic restart {self.restart_count + 1})"
        )
        
        if not success:
            raise RuntimeError("Failed to restart Claude process")
        
        # Restore state after restart
        if self.state_manager:
            restored = await self.state_manager.restore_state()
            if restored:
                self.logger.info("State restored successfully")
    
    def _build_claude_command(self, initial_context: Optional[str]) -> List[str]:
        """Build the Claude command line.
        
        Returns:
            List of command arguments
        """
        # Find Claude CLI executable
        claude_cli = "claude"  # Assume it's in PATH
        
        # Build command
        cmd = [claude_cli]
        
        # Add context if provided
        if initial_context:
            # Save context to temp file
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write(initial_context)
                context_file = f.name
            
            cmd.extend(['--context-file', context_file])
        
        # Add any additional Claude arguments
        if self.claude_args:
            cmd.extend(self.claude_args)
        
        return cmd
    
    def _display_monitoring_info(self):
        """Display memory monitoring configuration to user."""
        print("\n" + "="*60)
        print("🛡️  Memory Guardian Active")
        print("="*60)
        print(f"Memory Thresholds:")
        print(f"  • Warning:   {self.memory_config.thresholds.warning:,.0f} MB")
        print(f"  • Critical:  {self.memory_config.thresholds.critical:,.0f} MB")
        print(f"  • Emergency: {self.memory_config.thresholds.emergency:,.0f} MB")
        print(f"Monitoring:")
        print(f"  • Check Interval: {self.memory_config.monitoring.normal_interval} seconds")
        print(f"  • Max Restarts:   {self.max_restarts}")
        print(f"  • State Preservation: {'Enabled' if self.state_manager else 'Disabled'}")
        print("="*60 + "\n")
    
    def get_monitoring_status(self) -> Dict[str, Any]:
        """Get current monitoring status.
        
        Returns:
            Dictionary containing monitoring status
        """
        if not self.memory_guardian:
            return {
                'enabled': False,
                'message': 'Memory monitoring not initialized'
            }
        
        return self.memory_guardian.get_status()


class MemoryThresholdExceeded(Exception):
    """Exception raised when memory threshold is exceeded."""
    pass