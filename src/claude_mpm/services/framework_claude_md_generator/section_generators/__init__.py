"""
Section generators for framework CLAUDE.md template.

This module provides base classes and registry for section generators.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, Optional


class BaseSectionGenerator(ABC):
    """Base class for all section generators."""

    def __init__(self, framework_version: str):
        """
        Initialize section generator.

        Args:
            framework_version: Current framework version
        """
        self.framework_version = framework_version

    @abstractmethod
    def generate(self, data: Dict[str, Any]) -> str:
        """
        Generate section content.

        Args:
            data: Section-specific data

        Returns:
            str: Generated section content
        """

    def get_timestamp(self) -> str:
        """Get current UTC timestamp."""
        return datetime.utcnow().isoformat()


class SectionGeneratorRegistry:
    """Registry for section generators."""

    def __init__(self):
        """Initialize registry."""
        self._generators = {}

    def register(self, name: str, generator_class: type):
        """
        Register a section generator.

        Args:
            name: Section name
            generator_class: Generator class
        """
        self._generators[name] = generator_class

    def get(self, name: str) -> Optional[type]:
        """
        Get a section generator class.

        Args:
            name: Section name

        Returns:
            Generator class or None
        """
        return self._generators.get(name)

    def list_sections(self) -> list:
        """Get list of registered section names."""
        return list(self._generators.keys())


# Global registry instance
section_registry = SectionGeneratorRegistry()

from .agents import AgentsGenerator
from .claude_pm_init import ClaudePmInitGenerator
from .core_responsibilities import CoreResponsibilitiesGenerator
from .delegation_constraints import DelegationConstraintsGenerator
from .environment_config import EnvironmentConfigGenerator
from .footer import FooterGenerator

# Import and register all section generators
from .header import HeaderGenerator
from .orchestration_principles import OrchestrationPrinciplesGenerator
from .role_designation import RoleDesignationGenerator
from .subprocess_validation import SubprocessValidationGenerator
from .todo_task_tools import TodoTaskToolsGenerator
from .troubleshooting import TroubleshootingGenerator

# Register all generators
section_registry.register("header", HeaderGenerator)
section_registry.register("role_designation", RoleDesignationGenerator)
section_registry.register("agents", AgentsGenerator)
section_registry.register("todo_task_tools", TodoTaskToolsGenerator)
section_registry.register("claude_pm_init", ClaudePmInitGenerator)
section_registry.register("orchestration_principles", OrchestrationPrinciplesGenerator)
section_registry.register("subprocess_validation", SubprocessValidationGenerator)
section_registry.register("delegation_constraints", DelegationConstraintsGenerator)
section_registry.register("environment_config", EnvironmentConfigGenerator)
section_registry.register("troubleshooting", TroubleshootingGenerator)
section_registry.register("core_responsibilities", CoreResponsibilitiesGenerator)
section_registry.register("footer", FooterGenerator)
