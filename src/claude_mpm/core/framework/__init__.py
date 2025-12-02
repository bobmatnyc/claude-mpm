"""Framework module for Claude MPM.

This module provides the modular framework loading system with specialized components
for handling different aspects of framework initialization and management.
"""

from .formatters import CapabilityGenerator, ContentFormatter, ContextGenerator
from .loaders import AgentLoader, FileLoader, InstructionLoader, PackagedLoader
from .processors import MemoryProcessor, MetadataProcessor, TemplateProcessor

__all__ = [
    "AgentLoader",
    "CapabilityGenerator",
    # Formatters
    "ContentFormatter",
    "ContextGenerator",
    # Loaders
    "FileLoader",
    "InstructionLoader",
    "MemoryProcessor",
    # Processors
    "MetadataProcessor",
    "PackagedLoader",
    "TemplateProcessor",
]
