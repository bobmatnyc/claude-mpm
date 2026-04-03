"""
Structure Policy — directory constants and requirement rules.
=============================================================

Pure data + pure policy with zero I/O.  All class attributes were previously
inlined inside ProjectOrganizer; they now live here so they can be reused by
StructureVerifier, DirectoryCreator, and the thin coordinator without coupling
those modules to the coordinator itself.
"""

from typing import ClassVar


class StructurePolicy:
    """Provides project-structure constants and requirement rules.

    No I/O.  No side-effects.  Safe to instantiate as many times as needed.
    """

    # Standard directory structure for Claude MPM projects
    STANDARD_DIRECTORIES: ClassVar[dict[str, str]] = {
        "tmp": "Temporary files, test outputs, and experiments",
        "scripts": "Project scripts and automation tools",
        "docs": "Project documentation",
        "docs/_archive": "Archived documentation versions",
        "tests": "Test suites and test fixtures",
        ".claude-mpm": "Claude MPM configuration and data",
        ".claude-mpm/memories": "Agent memory storage",
        ".claude/agents": "Deployed agent configurations",
        "src": "Source code (for libraries/packages)",
    }

    # Project type specific structures
    PROJECT_STRUCTURES: ClassVar[dict[str, list[str]]] = {
        "web": ["public", "src/components", "src/pages", "src/styles"],
        "api": ["src/routes", "src/models", "src/middleware", "src/services"],
        "cli": ["src/commands", "src/utils", "src/config"],
        "library": ["src", "examples", "benchmarks"],
        "mobile": ["src/screens", "src/components", "src/services", "assets"],
        "fullstack": ["frontend", "backend", "shared", "infrastructure"],
    }

    def is_required_directory(self, dir_name: str, project_type: str | None) -> bool:
        """Return True when *dir_name* is required for *project_type*."""
        always_required = {"tmp", "scripts", "docs"}
        if dir_name in always_required:
            return True

        if project_type:
            if project_type in ("library", "package") and dir_name == "src":
                return True
            if project_type in ("web", "api", "fullstack") and dir_name == "tests":
                return True

        return False
