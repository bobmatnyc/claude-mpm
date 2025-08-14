"""Event handler registry for Socket.IO server.

WHY: This registry manages the registration of all event handlers,
providing a clean interface for the SocketIOServer to register all
events without knowing the details of each handler.
"""

from typing import List, Type, Optional, TYPE_CHECKING
from logging import Logger
from ....core.logger import get_logger

from .base import BaseEventHandler

if TYPE_CHECKING:
    from ..server import SocketIOServer
from .connection import ConnectionEventHandler
from .project import ProjectEventHandler
from .memory import MemoryEventHandler
from .file import FileEventHandler
from .git import GitEventHandler


class EventHandlerRegistry:
    """Manages registration of Socket.IO event handlers.
    
    WHY: The registry pattern allows us to easily add, remove, or modify
    event handlers without changing the SocketIOServer implementation.
    It provides a single point of configuration for all event handlers.
    """
    
    # Default handler classes in registration order
    DEFAULT_HANDLERS: List[Type[BaseEventHandler]] = [
        ConnectionEventHandler,  # Connection management first
        GitEventHandler,         # Git operations
        FileEventHandler,        # File operations
        ProjectEventHandler,     # Project management (future)
        MemoryEventHandler,      # Memory management (future)
    ]
    
    def __init__(self, server: 'SocketIOServer') -> None:
        """Initialize the registry.
        
        Args:
            server: The SocketIOServer instance
        """
        self.server: 'SocketIOServer' = server
        self.logger: Logger = get_logger("EventHandlerRegistry")
        self.handlers: List[BaseEventHandler] = []
        self._initialized: bool = False
    
    def initialize(self, handler_classes: Optional[List[Type[BaseEventHandler]]] = None) -> None:
        """Initialize all event handlers.
        
        WHY: This creates instances of all handler classes and prepares
        them for event registration. Using a list of classes allows
        customization of which handlers to use.
        
        Args:
            handler_classes: Optional list of handler classes to use.
                           Defaults to DEFAULT_HANDLERS if not provided.
        """
        if self._initialized:
            self.logger.warning("Registry already initialized, skipping re-initialization")
            return
        
        handler_classes = handler_classes or self.DEFAULT_HANDLERS
        
        for handler_class in handler_classes:
            try:
                handler = handler_class(self.server)
                self.handlers.append(handler)
                self.logger.info(f"Initialized handler: {handler_class.__name__}")
            except Exception as e:
                self.logger.error(f"Failed to initialize {handler_class.__name__}: {e}")
                import traceback
                self.logger.error(f"Stack trace: {traceback.format_exc()}")
        
        self._initialized = True
        self.logger.info(f"Registry initialized with {len(self.handlers)} handlers")
    
    def register_all_events(self) -> None:
        """Register all events from all handlers.
        
        WHY: This is the main method called by SocketIOServer to register
        all events. It delegates to each handler's register_events method,
        keeping the server code clean and simple.
        """
        if not self._initialized:
            self.logger.error("Registry not initialized. Call initialize() first.")
            raise RuntimeError("EventHandlerRegistry not initialized")
        
        registered_count = 0
        for handler in self.handlers:
            try:
                handler.register_events()
                registered_count += 1
                self.logger.info(f"Registered events for {handler.__class__.__name__}")
            except NotImplementedError:
                # Handler has no events to register (like ProjectEventHandler)
                self.logger.debug(f"No events to register for {handler.__class__.__name__}")
            except Exception as e:
                self.logger.error(f"Failed to register events for {handler.__class__.__name__}: {e}")
                import traceback
                self.logger.error(f"Stack trace: {traceback.format_exc()}")
        
        self.logger.info(f"Successfully registered events from {registered_count} handlers")
    
    def add_handler(self, handler_class: Type[BaseEventHandler]):
        """Add a custom handler to the registry.
        
        WHY: Allows dynamic addition of custom handlers for specific
        deployments or testing without modifying the default handlers.
        
        Args:
            handler_class: The handler class to add
        """
        if not self._initialized:
            self.logger.error("Registry not initialized. Call initialize() first.")
            raise RuntimeError("EventHandlerRegistry not initialized")
        
        try:
            handler = handler_class(self.server)
            self.handlers.append(handler)
            handler.register_events()
            self.logger.info(f"Added and registered handler: {handler_class.__name__}")
        except Exception as e:
            self.logger.error(f"Failed to add handler {handler_class.__name__}: {e}")
            raise
    
    def get_handler(self, handler_class: Type[BaseEventHandler]) -> BaseEventHandler:
        """Get a specific handler instance by class.
        
        WHY: Useful for testing or when specific handler functionality
        needs to be accessed directly.
        
        Args:
            handler_class: The handler class to find
            
        Returns:
            The handler instance or None if not found
        """
        for handler in self.handlers:
            if isinstance(handler, handler_class):
                return handler
        return None