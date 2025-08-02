"""
Deployment path management for Claude MPM.

WHY: Using relative parent traversal (e.g., Path(__file__).parent.parent.parent) is fragile
and breaks when files are moved or during different deployment scenarios (pip install,
development, packaged distribution). This module provides centralized path resolution
that works across all deployment scenarios.

DESIGN DECISION: We detect the deployment context and provide consistent paths regardless
of how the package is installed or run. This includes:
- Development mode (running from source)
- Pip installed packages
- Packaged distributions
- Test environments
"""

import os
import sys
from pathlib import Path
from typing import Optional, Dict
from functools import lru_cache


class DeploymentPaths:
    """Manages paths for different deployment scenarios."""
    
    def __init__(self):
        self._package_root: Optional[Path] = None
        self._project_root: Optional[Path] = None
        self._scripts_dir: Optional[Path] = None
        self._templates_dir: Optional[Path] = None
        self._static_dir: Optional[Path] = None
        
    @property
    @lru_cache(maxsize=1)
    def package_root(self) -> Path:
        """
        Get the claude_mpm package root directory.
        
        WHY: We need to reliably find the package root regardless of which
        module is calling this function.
        
        Returns:
            Path to the claude_mpm package directory (src/claude_mpm)
        """
        if self._package_root:
            return self._package_root
            
        # Try to find the package root by looking for __init__.py
        current_file = Path(__file__).resolve()
        
        # Walk up until we find the claude_mpm package root
        current = current_file.parent
        while current != current.parent:
            if (current.name == "claude_mpm" and 
                (current / "__init__.py").exists()):
                self._package_root = current
                return current
            current = current.parent
            
        # Fallback: assume we're in claude_mpm already
        self._package_root = current_file.parent
        return self._package_root
        
    @property
    @lru_cache(maxsize=1)
    def project_root(self) -> Path:
        """
        Get the project root directory.
        
        WHY: The project root contains configuration files, scripts directory,
        and other project-level resources that aren't part of the package.
        
        Returns:
            Path to the project root directory
        """
        if self._project_root:
            return self._project_root
            
        # Check if we're in a development environment
        # In development, project root is typically 2 levels up from package root
        package = self.package_root
        
        # Look for indicators of project root
        candidates = [
            package.parent.parent,  # src/claude_mpm -> src -> project_root
            package.parent,         # claude_mpm -> project_root (if no src/)
        ]
        
        for candidate in candidates:
            # Check for project indicators
            if any((candidate / marker).exists() for marker in [
                "pyproject.toml", "setup.py", "setup.cfg", 
                ".git", "README.md", "scripts/claude-mpm"
            ]):
                self._project_root = candidate
                return candidate
                
        # Fallback to package parent
        self._project_root = package.parent
        return self._project_root
        
    @property
    def scripts_dir(self) -> Path:
        """
        Get the scripts directory path.
        
        WHY: Scripts can be in different locations depending on deployment:
        - Development: project_root/scripts
        - Package: claude_mpm/scripts
        
        Returns:
            Path to the scripts directory
        """
        if self._scripts_dir:
            return self._scripts_dir
            
        # First try package scripts (for deployed packages)
        package_scripts = self.package_root / "scripts"
        if package_scripts.exists():
            self._scripts_dir = package_scripts
            return package_scripts
            
        # Then try project scripts (for development)
        project_scripts = self.project_root / "scripts"
        if project_scripts.exists():
            self._scripts_dir = project_scripts
            return project_scripts
            
        # Default to package scripts even if it doesn't exist yet
        self._scripts_dir = package_scripts
        return package_scripts
        
    @property
    def templates_dir(self) -> Path:
        """Get the agent templates directory."""
        if not self._templates_dir:
            self._templates_dir = self.package_root / "agents" / "templates"
        return self._templates_dir
        
    @property
    def static_dir(self) -> Path:
        """Get the static files directory (HTML, CSS, etc)."""
        if not self._static_dir:
            # Static files are in package scripts directory
            self._static_dir = self.package_root / "scripts"
        return self._static_dir
        
    def get_monitor_html_path(self) -> Path:
        """
        Get the path to the monitor HTML file.
        
        WHY: The monitor HTML can be in different locations depending on
        deployment context. We now prioritize the new modular web structure.
        
        Returns:
            Path to the monitor HTML file
        """
        # Try multiple locations in order of preference
        candidates = [
            # New modular structure (preferred)
            self.package_root / "web" / "templates" / "index.html",
            self.package_root / "web" / "templates" / "dashboard.html",  # fallback
            self.package_root / "web" / "index.html",  # root web index
            # Legacy locations (for backward compatibility)
            self.static_dir / "claude_mpm_monitor.html",
            self.scripts_dir / "claude_mpm_monitor.html",
            self.project_root / "scripts" / "claude_mpm_monitor.html",
        ]
        
        for candidate in candidates:
            if candidate.exists():
                return candidate
                
        # Return the preferred new location even if it doesn't exist
        # This allows better error messages and encourages proper structure
        return self.package_root / "web" / "templates" / "index.html"
        
    def get_resource_path(self, resource_type: str, filename: str) -> Path:
        """
        Get path to a resource file.
        
        Args:
            resource_type: Type of resource (scripts, templates, static, etc)
            filename: Name of the file
            
        Returns:
            Path to the resource
        """
        resource_dirs = {
            "scripts": self.scripts_dir,
            "templates": self.templates_dir,
            "static": self.static_dir,
            "agents": self.package_root / "agents",
        }
        
        base_dir = resource_dirs.get(resource_type, self.package_root)
        return base_dir / filename
        
    def resolve_import_path(self, module_path: str) -> Path:
        """
        Resolve a module import path to a file path.
        
        Args:
            module_path: Dot-separated module path (e.g., "claude_mpm.cli.commands.run")
            
        Returns:
            Path to the module file
        """
        parts = module_path.split(".")
        if parts[0] == "claude_mpm":
            parts = parts[1:]  # Remove package name
            
        return self.package_root.joinpath(*parts).with_suffix(".py")
        
    def ensure_directory(self, path: Path) -> Path:
        """Ensure a directory exists, creating it if necessary."""
        path.mkdir(parents=True, exist_ok=True)
        return path
        
    @classmethod
    @lru_cache(maxsize=1)
    def get_instance(cls) -> "DeploymentPaths":
        """Get singleton instance of DeploymentPaths."""
        return cls()


# Convenience functions
def get_deployment_paths() -> DeploymentPaths:
    """Get the deployment paths instance."""
    return DeploymentPaths.get_instance()


def get_package_root() -> Path:
    """Get the claude_mpm package root directory."""
    return get_deployment_paths().package_root


def get_project_root() -> Path:
    """Get the project root directory."""
    return get_deployment_paths().project_root


def get_scripts_dir() -> Path:
    """Get the scripts directory."""
    return get_deployment_paths().scripts_dir


def get_monitor_html_path() -> Path:
    """Get the monitor HTML file path."""
    return get_deployment_paths().get_monitor_html_path()


def get_templates_dir() -> Path:
    """Get the agent templates directory."""
    return get_deployment_paths().templates_dir


def get_resource_path(resource_type: str, filename: str) -> Path:
    """Get path to a resource file."""
    return get_deployment_paths().get_resource_path(resource_type, filename)