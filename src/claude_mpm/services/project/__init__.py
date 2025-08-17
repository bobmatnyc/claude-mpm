"""
Project Management Services Module
==================================

This module contains all project-related services including
project analysis and registry management.

Part of TSK-0046: Service Layer Architecture Reorganization

Services:
- ProjectAnalyzer: Analyzes project structure and metadata
- ProjectRegistry: Manages project registration and discovery
"""

from .analyzer import ProjectAnalyzer
from .registry import ProjectRegistry

__all__ = [
    "ProjectAnalyzer",
    "ProjectRegistry",
]
